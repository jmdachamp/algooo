"""
AlgoTrades Scalper Bot V0.2
===========================
Entry point. Initialises the broker, trade manager, and webhook server.

Usage:
    pip install -r requirements.txt
    cp .env.example .env        # fill in your credentials
    python main.py
"""

import asyncio
import uvicorn
from dotenv import load_dotenv

load_dotenv()

from config import settings
from broker.alpaca_broker import AlpacaBroker
from trade_manager import TradeManager
from webhook_server import app, set_trade_manager
from utils.logger import get_logger

logger = get_logger(__name__)


def build_broker() -> AlpacaBroker:
    if not settings.alpaca_api_key or not settings.alpaca_api_secret:
        raise RuntimeError(
            "ALPACA_API_KEY and ALPACA_API_SECRET must be set in your .env file."
        )
    return AlpacaBroker(
        api_key=settings.alpaca_api_key,
        api_secret=settings.alpaca_api_secret,
        paper=settings.alpaca_paper,
    )


async def main() -> None:
    logger.info("=== AlgoTrades Scalper Bot V0.2 starting ===")
    logger.info(
        "Mode: %s | Session: %s–%s | Risk: %.1f%% per trade",
        "PAPER" if settings.alpaca_paper else "LIVE",
        settings.session_start,
        settings.session_end,
        settings.account_risk_percent,
    )

    broker = build_broker()
    equity = broker.get_account_equity()
    logger.info("Account equity: $%.2f", equity)

    tm = TradeManager(broker)
    set_trade_manager(tm)

    server_config = uvicorn.Config(
        app,
        host=settings.webhook_host,
        port=settings.webhook_port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(server_config)

    logger.info(
        "Webhook server listening on http://%s:%d/webhook",
        settings.webhook_host,
        settings.webhook_port,
    )
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
