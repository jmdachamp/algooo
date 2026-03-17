from typing import Optional
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopOrderRequest,
    StopLimitOrderRequest,
    ReplaceOrderRequest,
    ClosePositionRequest,
)
from alpaca.trading.enums import OrderSide as AlpacaSide, TimeInForce, OrderType as AlpacaOrderType
from alpaca.trading.models import Order

from .base import BrokerBase, OrderSide, OrderType, Position, OrderResult
from utils.logger import get_logger

logger = get_logger(__name__)


def _map_side(side: OrderSide) -> AlpacaSide:
    return AlpacaSide.BUY if side == OrderSide.BUY else AlpacaSide.SELL


def _order_result(order: Order) -> OrderResult:
    return OrderResult(
        order_id=str(order.id),
        symbol=order.symbol,
        side=OrderSide.BUY if order.side == AlpacaSide.BUY else OrderSide.SELL,
        qty=float(order.qty or 0),
        filled_qty=float(order.filled_qty or 0),
        filled_avg_price=float(order.filled_avg_price) if order.filled_avg_price else None,
        status=str(order.status),
        client_order_id=str(order.client_order_id) if order.client_order_id else None,
    )


class AlpacaBroker(BrokerBase):
    def __init__(self, api_key: str, api_secret: str, paper: bool = True):
        self._client = TradingClient(api_key, api_secret, paper=paper)
        self._open_stops: dict[str, str] = {}  # symbol -> stop order_id
        mode = "paper" if paper else "LIVE"
        logger.info("AlpacaBroker initialised (%s)", mode)

    # ------------------------------------------------------------------ #
    # Account                                                              #
    # ------------------------------------------------------------------ #
    def get_account_equity(self) -> float:
        account = self._client.get_account()
        return float(account.equity)

    # ------------------------------------------------------------------ #
    # Positions                                                            #
    # ------------------------------------------------------------------ #
    def get_position(self, symbol: str) -> Optional[Position]:
        try:
            pos = self._client.get_open_position(symbol)
            return Position(
                symbol=pos.symbol,
                side=str(pos.side).lower(),
                qty=float(pos.qty),
                avg_entry_price=float(pos.avg_entry_price),
                current_price=float(pos.current_price),
                unrealized_pl=float(pos.unrealized_pl),
                unrealized_plpc=float(pos.unrealized_plpc),
            )
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    # Orders                                                               #
    # ------------------------------------------------------------------ #
    def market_order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        client_order_id: Optional[str] = None,
    ) -> OrderResult:
        req = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=_map_side(side),
            time_in_force=TimeInForce.DAY,
            client_order_id=client_order_id,
        )
        order = self._client.submit_order(req)
        logger.info("Market order submitted: %s %s x%s -> %s", side, symbol, qty, order.id)
        return _order_result(order)

    def limit_order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        limit_price: float,
        client_order_id: Optional[str] = None,
    ) -> OrderResult:
        req = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            side=_map_side(side),
            time_in_force=TimeInForce.DAY,
            limit_price=round(limit_price, 2),
            client_order_id=client_order_id,
        )
        order = self._client.submit_order(req)
        logger.info("Limit order submitted: %s %s x%s @ %.2f -> %s", side, symbol, qty, limit_price, order.id)
        return _order_result(order)

    def stop_order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        stop_price: float,
        client_order_id: Optional[str] = None,
    ) -> OrderResult:
        req = StopOrderRequest(
            symbol=symbol,
            qty=qty,
            side=_map_side(side),
            time_in_force=TimeInForce.DAY,
            stop_price=round(stop_price, 2),
            client_order_id=client_order_id,
        )
        order = self._client.submit_order(req)
        logger.info("Stop order submitted: %s %s x%s stop=%.2f -> %s", side, symbol, qty, stop_price, order.id)
        self._open_stops[symbol] = str(order.id)
        return _order_result(order)

    def bracket_order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        stop_price: float,
        take_profit_price: float,
        client_order_id: Optional[str] = None,
    ) -> OrderResult:
        """Bracket via market entry + separate stop + limit legs."""
        # Alpaca bracket orders use order_class="bracket"
        from alpaca.trading.requests import MarketOrderRequest as MOReq
        from alpaca.trading.models import OrderRequest

        req = MOReq(
            symbol=symbol,
            qty=qty,
            side=_map_side(side),
            time_in_force=TimeInForce.DAY,
            order_class="bracket",
            stop_loss={"stop_price": round(stop_price, 2)},
            take_profit={"limit_price": round(take_profit_price, 2)},
            client_order_id=client_order_id,
        )
        order = self._client.submit_order(req)
        logger.info(
            "Bracket order: %s %s x%s stop=%.2f tp=%.2f -> %s",
            side, symbol, qty, stop_price, take_profit_price, order.id,
        )
        return _order_result(order)

    def cancel_order(self, order_id: str) -> bool:
        try:
            self._client.cancel_order_by_id(order_id)
            logger.info("Cancelled order %s", order_id)
            return True
        except Exception as e:
            logger.warning("Cancel order %s failed: %s", order_id, e)
            return False

    def cancel_all_orders(self, symbol: str) -> int:
        cancelled = self._client.cancel_orders()
        count = len(cancelled) if cancelled else 0
        logger.info("Cancelled %d orders for %s", count, symbol)
        return count

    def close_position(self, symbol: str, qty_percent: float = 100.0) -> Optional[OrderResult]:
        try:
            if qty_percent >= 100.0:
                order = self._client.close_position(symbol)
            else:
                pos = self.get_position(symbol)
                if not pos:
                    return None
                close_qty = max(1, round(pos.qty * qty_percent / 100.0))
                req = ClosePositionRequest(qty=str(close_qty))
                order = self._client.close_position(symbol, close_options=req)
            logger.info("Closed %.0f%% of %s position", qty_percent, symbol)
            return _order_result(order)
        except Exception as e:
            logger.error("close_position %s failed: %s", symbol, e)
            return None

    def update_stop(self, symbol: str, new_stop: float) -> bool:
        """Cancel existing stop and place a new one at new_stop price."""
        pos = self.get_position(symbol)
        if not pos:
            return False
        # Cancel old stop if tracked
        old_stop_id = self._open_stops.get(symbol)
        if old_stop_id:
            self.cancel_order(old_stop_id)

        exit_side = OrderSide.SELL if pos.side == "long" else OrderSide.BUY
        result = self.stop_order(symbol, exit_side, pos.qty, new_stop)
        self._open_stops[symbol] = result.order_id
        logger.info("Updated stop for %s to %.2f (order %s)", symbol, new_stop, result.order_id)
        return True
