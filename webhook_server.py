"""
TradingView Webhook Server
==========================
TradingView sends an HTTP POST to this server when an alert fires.

Expected JSON payload (configure in TradingView alert message):
{
    "secret":  "{{strategy.order.alert_message}}",   // optional auth
    "action":  "LONG" | "SHORT" | "CLOSE_LONG" | "CLOSE_SHORT" | "PARTIAL_LONG" | "PARTIAL_SHORT",
    "symbol":  "{{ticker}}",
    "price":   {{close}},
    "comment": "{{strategy.order.comment}}"          // e.g. "L_Cross", "S_Cross", "Trend_Reversal"
}
"""

from fastapi import FastAPI, Request, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(title="AlgoTrades Scalper Bot", version="0.2.0")


class AlertPayload(BaseModel):
    action: str           # LONG, SHORT, CLOSE_LONG, CLOSE_SHORT, PARTIAL_LONG, PARTIAL_SHORT
    symbol: str
    price: float
    comment: Optional[str] = None
    secret: Optional[str] = None


# Lazy import to avoid circular deps; set by main.py
_trade_manager = None


def set_trade_manager(tm) -> None:
    global _trade_manager
    _trade_manager = tm


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}


@app.post("/webhook")
async def receive_alert(request: Request):
    body = await request.json()
    logger.debug("Incoming webhook: %s", body)

    try:
        payload = AlertPayload(**body)
    except Exception as e:
        logger.warning("Malformed webhook payload: %s | body=%s", e, body)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # Auth check
    if settings.webhook_secret and payload.secret != settings.webhook_secret:
        logger.warning("Webhook auth failure from %s", request.client.host if request.client else "unknown")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid secret")

    if _trade_manager is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Trade manager not ready")

    action = payload.action.upper()
    symbol = payload.symbol.upper()
    price = payload.price
    comment = payload.comment or ""

    logger.info("Alert received: action=%s symbol=%s price=%.4f comment=%s", action, symbol, price, comment)

    try:
        if action == "LONG":
            await _trade_manager.on_long_entry(symbol, price, comment)
        elif action == "SHORT":
            await _trade_manager.on_short_entry(symbol, price, comment)
        elif action == "CLOSE_LONG":
            await _trade_manager.on_close(symbol, "long", comment)
        elif action == "CLOSE_SHORT":
            await _trade_manager.on_close(symbol, "short", comment)
        elif action == "PARTIAL_LONG":
            await _trade_manager.on_partial(symbol, "long", comment)
        elif action == "PARTIAL_SHORT":
            await _trade_manager.on_partial(symbol, "short", comment)
        else:
            logger.warning("Unknown action: %s", action)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown action: {action}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Trade manager error processing %s %s: %s", action, symbol, e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error")

    return {"status": "ok", "action": action, "symbol": symbol}
