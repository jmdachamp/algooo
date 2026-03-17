"""
Trade Manager
=============
Replicates the exit management logic from the AlgoTrades Scalper V0.2 Pine Script.

Responsibilities:
- Calculate position size based on account equity and risk percent
- Place bracket orders on entry signals
- Manage partial exits, breakeven moves, and trailing stops
- Enforce session / time filters
- Enforce max-bars-open limit
"""

import asyncio
import math
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Optional
import pytz

from config import settings
from broker.base import BrokerBase, OrderSide
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TradeState:
    symbol: str
    side: str                    # "long" or "short"
    entry_price: float
    stop_price: float
    target_price: float
    partial1_target: float
    qty: float

    partial1_taken: bool = False
    breakeven_moved: bool = False
    is_trailing: bool = False
    trailing_stop: float = 0.0
    bars_open: int = 0
    entry_time: datetime = field(default_factory=datetime.utcnow)

    @property
    def stop_distance(self) -> float:
        if self.side == "long":
            return self.entry_price - self.stop_price
        return self.stop_price - self.entry_price

    def current_rr(self, current_price: float) -> float:
        if self.stop_distance <= 0:
            return 0.0
        if self.side == "long":
            return (current_price - self.entry_price) / self.stop_distance
        return (self.entry_price - current_price) / self.stop_distance


class TradeManager:
    def __init__(self, broker: BrokerBase):
        self._broker = broker
        self._states: dict[str, TradeState] = {}
        self._tz = pytz.timezone(settings.timezone)
        self._tick_monitor_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------ #
    # Session / time filters                                               #
    # ------------------------------------------------------------------ #
    def _now_local(self) -> datetime:
        return datetime.now(self._tz)

    def _in_session(self) -> bool:
        now = self._now_local()
        t = now.time()
        session_start = time(*map(int, settings.session_start.split(":")))
        session_end = time(*map(int, settings.session_end.split(":")))
        if not (session_start <= t <= session_end):
            return False
        # Lunch filter: 12:15–13:15
        if settings.filter_lunch:
            lunch_start = time(12, 15)
            lunch_end = time(13, 15)
            if lunch_start <= t <= lunch_end:
                return False
        # Prime time filter
        if settings.prime_time_only:
            prime_morning = (time(9, 45) <= t <= time(11, 30))
            prime_afternoon = (time(13, 30) <= t <= time(15, 30))
            if not (prime_morning or prime_afternoon):
                return False
        return True

    # ------------------------------------------------------------------ #
    # Position sizing                                                      #
    # ------------------------------------------------------------------ #
    def _calc_qty(self, stop_distance: float) -> float:
        if stop_distance <= 0:
            return 0
        equity = self._broker.get_account_equity()
        risk_dollars = equity * (settings.account_risk_percent / 100.0)
        qty = risk_dollars / stop_distance
        qty = math.floor(qty)
        qty = max(1, min(qty, settings.max_position_size))
        return float(qty)

    # ------------------------------------------------------------------ #
    # Entry handlers                                                       #
    # ------------------------------------------------------------------ #
    async def on_long_entry(self, symbol: str, price: float, comment: str = "") -> None:
        if not self._in_session():
            logger.info("LONG signal ignored – outside session (%s)", symbol)
            return
        if symbol in self._states:
            logger.info("LONG signal ignored – already in position (%s)", symbol)
            return

        sl = price - settings.stop_loss_distance
        tp = price + settings.stop_loss_distance * settings.risk_reward
        partial1_tp = price + settings.stop_loss_distance * settings.partial1_rr
        qty = self._calc_qty(settings.stop_loss_distance)

        if qty == 0:
            logger.error("Calculated qty=0 for %s, skipping entry", symbol)
            return

        logger.info(
            "LONG entry %s: price=%.4f sl=%.4f tp=%.4f qty=%s comment=%s",
            symbol, price, sl, tp, qty, comment,
        )

        self._broker.bracket_order(
            symbol=symbol,
            side=OrderSide.BUY,
            qty=qty,
            stop_price=sl,
            take_profit_price=tp,
            client_order_id=f"long_entry_{symbol}_{int(price*100)}",
        )

        state = TradeState(
            symbol=symbol,
            side="long",
            entry_price=price,
            stop_price=sl,
            target_price=tp,
            partial1_target=partial1_tp,
            qty=qty,
            trailing_stop=sl,
        )
        self._states[symbol] = state
        self._ensure_monitor()

    async def on_short_entry(self, symbol: str, price: float, comment: str = "") -> None:
        if not self._in_session():
            logger.info("SHORT signal ignored – outside session (%s)", symbol)
            return
        if symbol in self._states:
            logger.info("SHORT signal ignored – already in position (%s)", symbol)
            return

        sl = price + settings.stop_loss_distance
        tp = price - settings.stop_loss_distance * settings.risk_reward
        partial1_tp = price - settings.stop_loss_distance * settings.partial1_rr
        qty = self._calc_qty(settings.stop_loss_distance)

        if qty == 0:
            logger.error("Calculated qty=0 for %s, skipping entry", symbol)
            return

        logger.info(
            "SHORT entry %s: price=%.4f sl=%.4f tp=%.4f qty=%s comment=%s",
            symbol, price, sl, tp, qty, comment,
        )

        self._broker.bracket_order(
            symbol=symbol,
            side=OrderSide.SELL,
            qty=qty,
            stop_price=sl,
            take_profit_price=tp,
            client_order_id=f"short_entry_{symbol}_{int(price*100)}",
        )

        state = TradeState(
            symbol=symbol,
            side="short",
            entry_price=price,
            stop_price=sl,
            target_price=tp,
            partial1_target=partial1_tp,
            qty=qty,
            trailing_stop=sl,
        )
        self._states[symbol] = state
        self._ensure_monitor()

    # ------------------------------------------------------------------ #
    # Exit handlers (called from TradingView "Trend_Reversal" alerts)     #
    # ------------------------------------------------------------------ #
    async def on_close(self, symbol: str, side: str, comment: str = "") -> None:
        if symbol not in self._states:
            logger.debug("on_close: no tracked state for %s", symbol)
        logger.info("Closing %s position in %s (reason: %s)", side, symbol, comment)
        self._broker.cancel_all_orders(symbol)
        self._broker.close_position(symbol, qty_percent=100.0)
        self._states.pop(symbol, None)

    async def on_partial(self, symbol: str, side: str, comment: str = "") -> None:
        state = self._states.get(symbol)
        if state is None:
            logger.warning("on_partial: no tracked state for %s", symbol)
            return
        if state.partial1_taken:
            logger.debug("Partial already taken for %s", symbol)
            return
        pct = settings.partial1_percent
        logger.info("Partial exit %.0f%% for %s", pct, symbol)
        self._broker.close_position(symbol, qty_percent=float(pct))
        state.partial1_taken = True

    # ------------------------------------------------------------------ #
    # Periodic position monitor                                            #
    # ------------------------------------------------------------------ #
    def _ensure_monitor(self) -> None:
        if self._tick_monitor_task is None or self._tick_monitor_task.done():
            self._tick_monitor_task = asyncio.create_task(self._monitor_loop())

    async def _monitor_loop(self) -> None:
        """Poll open positions every ~5 seconds to manage exits."""
        logger.info("Position monitor started")
        while self._states:
            await asyncio.sleep(5)
            for symbol in list(self._states.keys()):
                await self._check_position(symbol)
        logger.info("Position monitor stopped (no open positions)")

    async def _check_position(self, symbol: str) -> None:
        state = self._states.get(symbol)
        if state is None:
            return

        pos = self._broker.get_position(symbol)
        if pos is None:
            # Position closed (stop/target hit)
            logger.info("Position %s appears closed externally, removing state", symbol)
            self._states.pop(symbol, None)
            return

        current_price = pos.current_price
        state.bars_open += 1
        rr = state.current_rr(current_price)

        # Max bars exit
        if state.bars_open >= settings.max_bars_open:
            logger.info("Max bars (%d) reached for %s, closing", settings.max_bars_open, symbol)
            await self.on_close(symbol, state.side, "max_bars")
            return

        # Partial profit
        if settings.enable_partials and not state.partial1_taken:
            if state.side == "long" and current_price >= state.partial1_target:
                await self.on_partial(symbol, state.side, "auto_partial")
            elif state.side == "short" and current_price <= state.partial1_target:
                await self.on_partial(symbol, state.side, "auto_partial")

        # Breakeven move
        if settings.enable_breakeven and not state.breakeven_moved and not state.is_trailing:
            if rr >= settings.breakeven_rr:
                be_stop = (
                    state.entry_price + settings.tick_size
                    if state.side == "long"
                    else state.entry_price - settings.tick_size
                )
                logger.info("Moving stop to breakeven for %s (rr=%.2f)", symbol, rr)
                if self._broker.update_stop(symbol, be_stop):
                    state.stop_price = be_stop
                    state.breakeven_moved = True

        # Trailing stop
        if settings.enable_trailing and rr >= settings.trail_start_rr:
            if state.side == "long":
                new_trail = current_price - settings.trail_distance
                if not state.is_trailing or new_trail > state.trailing_stop:
                    state.trailing_stop = new_trail
                    state.is_trailing = True
                    logger.info("Updating trailing stop %s -> %.4f", symbol, new_trail)
                    self._broker.update_stop(symbol, new_trail)
            else:
                new_trail = current_price + settings.trail_distance
                if not state.is_trailing or new_trail < state.trailing_stop:
                    state.trailing_stop = new_trail
                    state.is_trailing = True
                    logger.info("Updating trailing stop %s -> %.4f", symbol, new_trail)
                    self._broker.update_stop(symbol, new_trail)
