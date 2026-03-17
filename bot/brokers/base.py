"""Abstract broker interface — all brokers must implement this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    fill_price: Optional[float]
    status: str  # "filled" | "pending" | "rejected"


@dataclass
class Position:
    symbol: str
    side: OrderSide
    quantity: int
    entry_price: float
    current_price: float
    unrealized_pnl: float


class BrokerBase(ABC):
    """Minimal interface every broker adapter must implement."""

    # ── Connection ──────────────────────────────────────────────────────────

    @abstractmethod
    async def connect(self) -> None:
        """Authenticate and establish session."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully close the session."""

    # ── Orders ───────────────────────────────────────────────────────────────

    @abstractmethod
    async def market_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
    ) -> OrderResult:
        """Place a market order and return fill details."""

    @abstractmethod
    async def trailing_stop_order(
        self,
        symbol: str,
        side: OrderSide,        # side of the *closing* order (opposite of position)
        quantity: int,
        trail_points: float,    # distance in price points
    ) -> OrderResult:
        """Attach a native trailing stop to protect an open position."""

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order. Returns True if successful."""

    # ── Account / positions ──────────────────────────────────────────────────

    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Return current open position for a symbol, or None."""

    @abstractmethod
    async def get_account_balance(self) -> float:
        """Return available cash / net liquidation value."""
