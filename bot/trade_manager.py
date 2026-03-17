"""Trade manager — handles the full lifecycle of a trade.

Flow for a BUY signal:
  1. Check if we already have an open position → skip if yes
  2. Place a market buy order
  3. On fill, attach a native trailing stop (closing Sell)
  4. Log everything and track state

The trailing stop is placed as a native broker order so it persists
even if this process restarts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

from .brokers.base import BrokerBase, OrderResult, OrderSide
from .config import BotConfig, InstrumentConfig

logger = logging.getLogger(__name__)


@dataclass
class OpenTrade:
    symbol: str
    side: OrderSide
    quantity: int
    entry_price: Optional[float]
    entry_order_id: str
    trail_order_id: Optional[str] = None
    opened_at: datetime = field(default_factory=datetime.utcnow)


class TradeManager:
    def __init__(self, broker: BrokerBase, config: BotConfig) -> None:
        self._broker = broker
        self._config = config
        # symbol → OpenTrade
        self._open_trades: Dict[str, OpenTrade] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    async def handle_signal(
        self,
        symbol: str,
        action: str,           # "buy" | "sell" | "exit"
        source_price: Optional[float] = None,
    ) -> str:
        """Process an incoming TradingView signal.

        Returns a human-readable status string.
        """
        symbol = symbol.upper()
        action = action.lower()

        instrument = self._config.get_instrument(symbol)
        if instrument is None:
            msg = f"Symbol {symbol} not in config — ignoring signal"
            logger.warning(msg)
            return msg

        if action in ("buy", "sell"):
            return await self._enter_trade(symbol, action, instrument, source_price)
        elif action == "exit":
            return await self._exit_trade(symbol)
        else:
            msg = f"Unknown action '{action}' — ignoring"
            logger.warning(msg)
            return msg

    # ── Entry ─────────────────────────────────────────────────────────────────

    async def _enter_trade(
        self,
        symbol: str,
        action: str,
        instrument: InstrumentConfig,
        source_price: Optional[float],
    ) -> str:
        # Don't stack positions — one trade per symbol at a time
        if symbol in self._open_trades:
            msg = f"Already in a {symbol} trade — ignoring new {action} signal"
            logger.info(msg)
            return msg

        side = OrderSide.BUY if action == "buy" else OrderSide.SELL

        logger.info(
            "Entering %s %s × %d (trail=%s pts)",
            action.upper(), symbol, instrument.quantity, instrument.trail_points,
        )

        # ── 1. Market entry ──────────────────────────────────────────────────
        try:
            entry_result: OrderResult = await self._broker.market_order(
                symbol=instrument.broker_symbol,
                side=side,
                quantity=instrument.quantity,
            )
        except Exception as exc:
            msg = f"Market order failed for {symbol}: {exc}"
            logger.error(msg)
            return msg

        logger.info(
            "Entry order %s | status=%s | fill=%.2f",
            entry_result.order_id,
            entry_result.status,
            entry_result.fill_price or 0,
        )

        # ── 2. Trailing stop ─────────────────────────────────────────────────
        # Closing side is opposite to entry
        closing_side = OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY
        trail_order_id: Optional[str] = None
        try:
            trail_result: OrderResult = await self._broker.trailing_stop_order(
                symbol=instrument.broker_symbol,
                side=closing_side,
                quantity=instrument.quantity,
                trail_points=instrument.trail_points,
            )
            trail_order_id = trail_result.order_id
            logger.info(
                "Trailing stop order %s placed (%.1f pts)",
                trail_order_id, instrument.trail_points,
            )
        except Exception as exc:
            logger.error("Trailing stop failed for %s: %s", symbol, exc)
            # Don't abort — trade is open, operator should handle manually

        # ── 3. Track state ───────────────────────────────────────────────────
        self._open_trades[symbol] = OpenTrade(
            symbol=symbol,
            side=side,
            quantity=instrument.quantity,
            entry_price=entry_result.fill_price,
            entry_order_id=entry_result.order_id,
            trail_order_id=trail_order_id,
        )

        return (
            f"Entered {action.upper()} {instrument.quantity}× {symbol} "
            f"@ {entry_result.fill_price or 'pending'} | "
            f"trail={instrument.trail_points}pts | order={entry_result.order_id}"
        )

    # ── Exit ──────────────────────────────────────────────────────────────────

    async def _exit_trade(self, symbol: str) -> str:
        if symbol not in self._open_trades:
            msg = f"No open trade for {symbol} — ignoring exit signal"
            logger.info(msg)
            return msg

        trade = self._open_trades[symbol]
        instrument = self._config.get_instrument(symbol)

        # Cancel the trailing stop first to avoid double-fill
        if trade.trail_order_id:
            try:
                await self._broker.cancel_order(trade.trail_order_id)
                logger.info("Cancelled trailing stop %s", trade.trail_order_id)
            except Exception as exc:
                logger.warning("Could not cancel trail order: %s", exc)

        # Flatten with a market order
        closing_side = OrderSide.SELL if trade.side == OrderSide.BUY else OrderSide.BUY
        try:
            exit_result = await self._broker.market_order(
                symbol=instrument.broker_symbol,
                side=closing_side,
                quantity=trade.quantity,
            )
        except Exception as exc:
            msg = f"Exit market order failed for {symbol}: {exc}"
            logger.error(msg)
            return msg

        del self._open_trades[symbol]

        return (
            f"Exited {symbol} | fill={exit_result.fill_price or 'pending'} "
            f"| order={exit_result.order_id}"
        )

    # ── Queries ───────────────────────────────────────────────────────────────

    def open_trades(self) -> Dict[str, OpenTrade]:
        return dict(self._open_trades)
