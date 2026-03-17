from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # Broker
    alpaca_api_key: str = Field("", env="ALPACA_API_KEY")
    alpaca_api_secret: str = Field("", env="ALPACA_API_SECRET")
    alpaca_paper: bool = Field(True, env="ALPACA_PAPER")

    # Webhook
    webhook_host: str = Field("0.0.0.0", env="WEBHOOK_HOST")
    webhook_port: int = Field(8000, env="WEBHOOK_PORT")
    webhook_secret: Optional[str] = Field(None, env="WEBHOOK_SECRET")

    # EMA settings
    ema_fast: int = Field(9, env="EMA_FAST")
    ema_mid: int = Field(21, env="EMA_MID")
    ema_slow: int = Field(45, env="EMA_SLOW")

    # Volume
    volume_period: int = Field(20, env="VOLUME_PERIOD")
    volume_increase: float = Field(1.05, env="VOLUME_INCREASE")

    # Risk / Stop
    stop_loss_ticks: int = Field(15, env="STOP_LOSS_TICKS")
    risk_reward: float = Field(2.0, env="RISK_REWARD")
    tick_size: float = Field(0.01, env="TICK_SIZE")

    # Position sizing
    account_risk_percent: float = Field(1.0, env="ACCOUNT_RISK_PERCENT")
    max_position_size: int = Field(100, env="MAX_POSITION_SIZE")

    # Entry patterns
    require_engulfing: bool = Field(False, env="REQUIRE_ENGULFING")
    min_body_percent: float = Field(60.0, env="MIN_BODY_PERCENT")
    allow_deep_pullback: bool = Field(False, env="ALLOW_DEEP_PULLBACK")

    # EMA crossover
    enable_crossovers: bool = Field(True, env="ENABLE_CROSSOVERS")
    atr_multiplier: float = Field(1.1, env="ATR_MULTIPLIER")
    atr_period: int = Field(10, env="ATR_PERIOD")
    trail_ticks: int = Field(10, env="TRAIL_TICKS")

    # Exit management
    enable_partials: bool = Field(True, env="ENABLE_PARTIALS")
    partial1_percent: int = Field(50, env="PARTIAL1_PERCENT")
    partial1_rr: float = Field(1.0, env="PARTIAL1_RR")
    enable_breakeven: bool = Field(True, env="ENABLE_BREAKEVEN")
    breakeven_rr: float = Field(0.75, env="BREAKEVEN_RR")
    enable_trailing: bool = Field(True, env="ENABLE_TRAILING")
    trail_start_rr: float = Field(1.0, env="TRAIL_START_RR")

    # Session & time
    session_start: str = Field("09:30", env="SESSION_START")
    session_end: str = Field("15:50", env="SESSION_END")
    filter_lunch: bool = Field(True, env="FILTER_LUNCH")
    prime_time_only: bool = Field(False, env="PRIME_TIME_ONLY")
    max_bars_open: int = Field(15, env="MAX_BARS_OPEN")
    timezone: str = Field("America/New_York", env="TIMEZONE")

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("logs/bot.log", env="LOG_FILE")

    @property
    def stop_loss_distance(self) -> float:
        return self.stop_loss_ticks * self.tick_size

    @property
    def trail_distance(self) -> float:
        return self.trail_ticks * self.tick_size

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
