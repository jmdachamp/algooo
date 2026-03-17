"""Interactive Brokers broker adapter using ib_insync.

Requires TWS or IB Gateway running locally with API enabled.

Set these environment variables:
    IBKR_HOST        (default: 127.0.0.1)
    IBKR_PORT        (default: 7497 for TWS paper, 7496 for TWS live,
                               4002 for Gateway paper, 4001 for Gateway live)
    IBKR_CLIENT_ID   (default: 1, must be unique per connection)
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from .base import BrokerBase, OrderResult, OrderSide, Position

logger = logging.getLogger(__name__)


class IBKRBroker(BrokerBase):
    """IBKR adapter via ib_insync.

    Install: pip install ib_insync
    """

    def __init__(self, paper: bool = True) -> None:
        self._paper = paper
        self._ib = None
        self._host = os.environ.get("IBKR_HOST", "127.0.0.1")
        # Paper TWS default port; live is 7496
        default_port = "7497" if paper else "7496"
        self._port = int(os.environ.get("IBKR_PORT", default_port))
        self._client_id = int(os.environ.get("IBKR_CLIENT_ID", "1"))

    # ── Connection ────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        try:
            from ib_insync import IB
        except ImportError:
            raise RuntimeError("ib_insync not installed. Run: pip install ib_insync")

        self._ib = IB()
        await self._ib.connectAsync(self._host, self._port, clientId=self._client_id)
        logger.info(
            "IBKR connected (host=%s port=%s paper=%s)",
            self._host, self._port, self._paper,
        )

    async def disconnect(self) -> None:
        if self._ib:
            self._ib.disconnect()
            logger.info("IBKR disconnected")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_contract(self, symbol: str, exchange: str = "CME", currency: str = "USD"):
        from ib_insync import Future
        exchange_map = {
            "NQ": "CME", "RTY": "CME",
            "YM": "CBOT",
            "GC": "COMEX",
        }
        exch = exchange_map.get(symbol.upper(), exchange)
        return Future(symbol=symbol.upper(), exchange=exch, currency=currency)

    # ── Orders ────────────────────────────────────────────────────────────────

    async def market_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
    ) -> OrderResult:
        from ib_insync import MarketOrder
        contract = self._make_contract(symbol)
        await self._ib.qualifyContractsAsync(contract)
        action = "BUY" if side == OrderSide.BUY else "SELL"
        order = MarketOrder(action, quantity)
        trade = self._ib.placeOrder(contract, order)
        # Wait for fill (up to 10 seconds)
        for _ in range(100):
            await self._ib.sleep(0.1)
            if trade.orderStatus.status in ("Filled", "Submitted"):
                break
        fill_price = trade.orderStatus.avgFillPrice or None
        return OrderResult(
            order_id=str(trade.order.orderId),
            symbol=symbol,
            side=side,
            quantity=quantity,
            fill_price=fill_price,
            status="filled" if trade.orderStatus.status == "Filled" else "pending",
        )

    async def trailing_stop_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        trail_points: float,
    ) -> OrderResult:
        from ib_insync import Order
        contract = self._make_contract(symbol)
        await self._ib.qualifyContractsAsync(contract)
        action = "BUY" if side == OrderSide.BUY else "SELL"
        order = Order(
            action=action,
            totalQuantity=quantity,
            orderType="TRAIL",
            auxPrice=trail_points,  # trail amount in points
        )
        trade = self._ib.placeOrder(contract, order)
        await self._ib.sleep(0.5)
        return OrderResult(
            order_id=str(trade.order.orderId),
            symbol=symbol,
            side=side,
            quantity=quantity,
            fill_price=None,
            status="pending",
        )

    async def cancel_order(self, order_id: str) -> bool:
        from ib_insync import Order
        order = Order(orderId=int(order_id))
        self._ib.cancelOrder(order)
        return True

    async def get_position(self, symbol: str) -> Optional[Position]:
        positions = self._ib.positions()
        for pos in positions:
            if pos.contract.symbol.upper() == symbol.upper():
                qty = pos.position
                side = OrderSide.BUY if qty > 0 else OrderSide.SELL
                return Position(
                    symbol=symbol,
                    side=side,
                    quantity=abs(int(qty)),
                    entry_price=pos.avgCost,
                    current_price=0.0,
                    unrealized_pnl=0.0,
                )
        return None

    async def get_account_balance(self) -> float:
        values = self._ib.accountValues()
        for v in values:
            if v.tag == "NetLiquidation" and v.currency == "USD":
                return float(v.value)
        return 0.0
