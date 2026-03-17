from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


@dataclass
class Position:
    symbol: str
    side: str          # "long" or "short"
    qty: float
    avg_entry_price: float
    current_price: float
    unrealized_pl: float
    unrealized_plpc: float


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: OrderSide
    qty: float
    filled_qty: float
    filled_avg_price: Optional[float]
    status: str
    client_order_id: Optional[str] = None


class BrokerBase(ABC):
    """Abstract base class for broker integrations."""

    @abstractmethod
    def get_account_equity(self) -> float:
        """Return total account equity."""

    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]:
        """Return current position for symbol, or None."""

    @abstractmethod
    def market_order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        client_order_id: Optional[str] = None,
    ) -> OrderResult:
        """Submit a market order."""

    @abstractmethod
    def limit_order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        limit_price: float,
        client_order_id: Optional[str] = None,
    ) -> OrderResult:
        """Submit a limit order."""

    @abstractmethod
    def stop_order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        stop_price: float,
        client_order_id: Optional[str] = None,
    ) -> OrderResult:
        """Submit a stop order."""

    @abstractmethod
    def bracket_order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        stop_price: float,
        take_profit_price: float,
        client_order_id: Optional[str] = None,
    ) -> OrderResult:
        """Submit a bracket (entry + stop + target) order."""

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order by ID."""

    @abstractmethod
    def cancel_all_orders(self, symbol: str) -> int:
        """Cancel all open orders for symbol. Returns count cancelled."""

    @abstractmethod
    def close_position(self, symbol: str, qty_percent: float = 100.0) -> Optional[OrderResult]:
        """Close all or part of a position."""

    @abstractmethod
    def update_stop(self, symbol: str, new_stop: float) -> bool:
        """Replace the existing stop order with a new stop price."""
