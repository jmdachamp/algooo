"""Load and validate bot configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import yaml


@dataclass
class InstrumentConfig:
    broker_symbol: str
    exchange: str
    currency: str
    quantity: int
    trail_points: float
    max_loss_usd: float = 0.0


@dataclass
class WebhookConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    secret_token: str = ""


@dataclass
class BotConfig:
    broker: str
    paper_trading: bool
    webhook: WebhookConfig
    instruments: Dict[str, InstrumentConfig]

    def get_instrument(self, symbol: str) -> Optional[InstrumentConfig]:
        return self.instruments.get(symbol.upper())


def load_config(path: Optional[str] = None) -> BotConfig:
    config_path = path or os.getenv("BOT_CONFIG", "config.yaml")
    raw = yaml.safe_load(Path(config_path).read_text())

    webhook = WebhookConfig(**raw.get("webhook", {}))

    instruments = {
        sym.upper(): InstrumentConfig(**cfg)
        for sym, cfg in raw.get("instruments", {}).items()
    }

    return BotConfig(
        broker=raw["broker"],
        paper_trading=raw.get("paper_trading", True),
        webhook=webhook,
        instruments=instruments,
    )
