"""FastAPI webhook server — receives TradingView alerts and routes them
to the TradeManager.

TradingView alert message format (set this in the TV alert "Message" box):
    {
      "symbol": "{{ticker}}",
      "action": "buy",
      "price": {{close}}
    }

Webhook URL format:
    http(s)://your-server:8000/webhook?token=YOUR_SECRET_TOKEN

Supported actions:
  "buy"   → open a long position
  "sell"  → open a short position
  "exit"  → close any open position for that symbol
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .brokers import IBKRBroker, TradovateBroker
from .brokers.base import BrokerBase
from .config import BotConfig, load_config
from .trade_manager import TradeManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── Global state ──────────────────────────────────────────────────────────────

_config: Optional[BotConfig] = None
_broker: Optional[BrokerBase] = None
_manager: Optional[TradeManager] = None


# ── App lifecycle ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _config, _broker, _manager

    _config = load_config()

    if _config.broker == "tradovate":
        _broker = TradovateBroker(paper=_config.paper_trading)
    elif _config.broker == "ibkr":
        _broker = IBKRBroker(paper=_config.paper_trading)
    else:
        raise RuntimeError(f"Unknown broker: {_config.broker}")

    await _broker.connect()
    _manager = TradeManager(_broker, _config)

    logger.info(
        "Bot started | broker=%s paper=%s",
        _config.broker, _config.paper_trading,
    )
    yield

    if _broker:
        await _broker.disconnect()
    logger.info("Bot stopped")


app = FastAPI(title="TradingView Algo Bot", lifespan=lifespan)


# ── Security ──────────────────────────────────────────────────────────────────

def verify_token(request: Request) -> None:
    expected = _config.webhook.secret_token if _config else ""
    if not expected:
        return  # no token configured → skip check (not recommended for production)
    provided = request.query_params.get("token") or request.headers.get("X-Webhook-Token", "")
    if provided != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")


# ── Schemas ───────────────────────────────────────────────────────────────────

class AlertPayload(BaseModel):
    """JSON body TradingView sends with each alert."""
    symbol: str = Field(..., description="Ticker, e.g. NQ or GC")
    action: str = Field(..., description="buy | sell | exit")
    price: Optional[float] = Field(None, description="{{close}} from TV")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/webhook")
async def receive_alert(
    payload: AlertPayload,
    _: None = Depends(verify_token),
) -> JSONResponse:
    logger.info("Alert received: %s", payload.model_dump())

    if _manager is None:
        raise HTTPException(status_code=503, detail="Bot not ready")

    result = await _manager.handle_signal(
        symbol=payload.symbol,
        action=payload.action,
        source_price=payload.price,
    )

    logger.info("Result: %s", result)
    return JSONResponse({"status": "ok", "message": result})


@app.get("/status")
async def bot_status() -> JSONResponse:
    """Health check + open positions summary."""
    if _manager is None:
        return JSONResponse({"status": "starting"})

    trades = {
        sym: {
            "side": t.side.value,
            "quantity": t.quantity,
            "entry_price": t.entry_price,
            "opened_at": t.opened_at.isoformat(),
            "trail_order_id": t.trail_order_id,
        }
        for sym, t in _manager.open_trades().items()
    }

    balance = await _broker.get_account_balance() if _broker else None

    return JSONResponse({
        "status": "running",
        "broker": _config.broker if _config else None,
        "paper_trading": _config.paper_trading if _config else None,
        "open_trades": trades,
        "account_balance": balance,
    })


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    import uvicorn
    cfg = load_config()
    uvicorn.run(
        "bot.webhook_server:app",
        host=cfg.webhook.host,
        port=cfg.webhook.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
