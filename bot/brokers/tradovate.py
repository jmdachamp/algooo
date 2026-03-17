"""Tradovate broker adapter.

Docs: https://api.tradovate.com/

Set these environment variables:
    TRADOVATE_USERNAME
    TRADOVATE_PASSWORD
    TRADOVATE_APP_ID          (from Tradovate developer portal)
    TRADOVATE_APP_VERSION     (e.g. "1.0")
    TRADOVATE_CID             (client id from dev portal)
    TRADOVATE_SECRET          (client secret from dev portal)
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

import httpx

from .base import BrokerBase, OrderResult, OrderSide, Position

logger = logging.getLogger(__name__)

LIVE_BASE = "https://live.tradovateapi.com/v1"
DEMO_BASE = "https://demo.tradovateapi.com/v1"


class TradovateBroker(BrokerBase):
    def __init__(self, paper: bool = True) -> None:
        self._base = DEMO_BASE if paper else LIVE_BASE
        self._token: Optional[str] = None
        self._token_expiry: float = 0.0
        self._client = httpx.AsyncClient(timeout=10)
        self._contract_cache: dict[str, int] = {}

    # ── Auth ─────────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        await self._authenticate()
        logger.info("Tradovate connected (base=%s)", self._base)

    async def disconnect(self) -> None:
        await self._client.aclose()
        logger.info("Tradovate disconnected")

    async def _authenticate(self) -> None:
        payload = {
            "name": os.environ["TRADOVATE_USERNAME"],
            "password": os.environ["TRADOVATE_PASSWORD"],
            "appId": os.environ["TRADOVATE_APP_ID"],
            "appVersion": os.environ.get("TRADOVATE_APP_VERSION", "1.0"),
            "cid": int(os.environ["TRADOVATE_CID"]),
            "sec": os.environ["TRADOVATE_SECRET"],
            "deviceId": "algo-bot-001",
        }
        resp = await self._client.post(f"{self._base}/auth/accesstokenrequest", json=payload)
        resp.raise_for_status()
        data = resp.json()
        self._token = data["accessToken"]
        # Tradovate tokens last 80 minutes; renew 5 min early
        self._token_expiry = time.time() + (data.get("expirationTime", 4800) - 300)
        self._client.headers["Authorization"] = f"Bearer {self._token}"

    async def _ensure_auth(self) -> None:
        if time.time() >= self._token_expiry:
            await self._authenticate()

    # ── Contract lookup ───────────────────────────────────────────────────────

    async def _get_contract_id(self, symbol: str) -> int:
        """Resolve a symbol like 'NQ' to its current front-month contract ID."""
        if symbol in self._contract_cache:
            return self._contract_cache[symbol]
        await self._ensure_auth()
        resp = await self._client.get(
            f"{self._base}/contract/suggest",
            params={"t": symbol, "l": 1},
        )
        resp.raise_for_status()
        items = resp.json()
        if not items:
            raise ValueError(f"No contract found for symbol: {symbol}")
        contract_id = items[0]["id"]
        self._contract_cache[symbol] = contract_id
        logger.debug("Resolved %s → contract id %s", symbol, contract_id)
        return contract_id

    # ── Orders ────────────────────────────────────────────────────────────────

    async def market_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
    ) -> OrderResult:
        await self._ensure_auth()
        contract_id = await self._get_contract_id(symbol)
        action = "Buy" if side == OrderSide.BUY else "Sell"
        payload = {
            "accountSpec": os.environ["TRADOVATE_USERNAME"],
            "accountId": await self._get_account_id(),
            "action": action,
            "symbol": symbol,
            "orderQty": quantity,
            "orderType": "Market",
            "isAutomated": True,
        }
        resp = await self._client.post(f"{self._base}/order/placeorder", json=payload)
        resp.raise_for_status()
        data = resp.json()
        order = data.get("ordStatus", {})
        return OrderResult(
            order_id=str(data.get("orderId", "")),
            symbol=symbol,
            side=side,
            quantity=quantity,
            fill_price=order.get("avgPx"),
            status="filled" if order.get("ordStatus") == "Filled" else "pending",
        )

    async def trailing_stop_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        trail_points: float,
    ) -> OrderResult:
        """Place a native trailing stop on Tradovate.

        Tradovate expects trailPrice in price points (not ticks).
        The side here is the *exit* direction:
          - Long position → closing side is Sell
          - Short position → closing side is Buy
        """
        await self._ensure_auth()
        action = "Buy" if side == OrderSide.BUY else "Sell"
        payload = {
            "accountSpec": os.environ["TRADOVATE_USERNAME"],
            "accountId": await self._get_account_id(),
            "action": action,
            "symbol": symbol,
            "orderQty": quantity,
            "orderType": "TrailingStop",
            "trailPrice": trail_points,
            "isAutomated": True,
        }
        resp = await self._client.post(f"{self._base}/order/placeorder", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return OrderResult(
            order_id=str(data.get("orderId", "")),
            symbol=symbol,
            side=side,
            quantity=quantity,
            fill_price=None,
            status="pending",
        )

    async def cancel_order(self, order_id: str) -> bool:
        await self._ensure_auth()
        resp = await self._client.post(
            f"{self._base}/order/cancelorder",
            json={"orderId": int(order_id)},
        )
        return resp.status_code == 200

    # ── Account / positions ───────────────────────────────────────────────────

    async def get_position(self, symbol: str) -> Optional[Position]:
        await self._ensure_auth()
        account_id = await self._get_account_id()
        resp = await self._client.get(f"{self._base}/position/list")
        resp.raise_for_status()
        for pos in resp.json():
            if pos.get("contractId") and str(pos.get("netPos", 0)) != "0":
                # Match by looking up the contract symbol
                try:
                    cid = await self._get_contract_id(symbol)
                    if pos["contractId"] == cid:
                        net = pos["netPos"]
                        side = OrderSide.BUY if net > 0 else OrderSide.SELL
                        return Position(
                            symbol=symbol,
                            side=side,
                            quantity=abs(net),
                            entry_price=pos.get("openPnl", 0),
                            current_price=0.0,
                            unrealized_pnl=pos.get("openPnl", 0),
                        )
                except Exception:
                    pass
        return None

    async def get_account_balance(self) -> float:
        await self._ensure_auth()
        account_id = await self._get_account_id()
        resp = await self._client.get(f"{self._base}/cashbalance/getcashbalancesnapshot")
        resp.raise_for_status()
        data = resp.json()
        return float(data.get("totalCashValue", 0))

    async def _get_account_id(self) -> int:
        resp = await self._client.get(f"{self._base}/account/list")
        resp.raise_for_status()
        accounts = resp.json()
        if not accounts:
            raise RuntimeError("No Tradovate accounts found")
        return accounts[0]["id"]
