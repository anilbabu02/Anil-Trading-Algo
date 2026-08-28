import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Trading Environment
    TRADING_MODE: str = Field(default="paper", description="Execution mode: 'paper' or 'live'")
    
    # Capital & Position Sizing Guardrails
    STARTING_CAPITAL: float = Field(default=10800.00, description="Base starting capital in INR")
    MAX_DAILY_LOSS: float = Field(default=1000.00, description="Daily loss circuit breaker limit in INR")
    MAX_TRADES_PER_DAY: int = Field(default=2, description="Max allowed closed trades per day")
    MAX_OPEN_POSITIONS: int = Field(default=1, description="Max concurrent open positions")
    
    # Lot Sizes for Indian Derivative Indices
    NIFTY_LOT_SIZE: int = Field(default=65, description="NSE NIFTY 50 Option/Future lot size")
    BANKNIFTY_LOT_SIZE: int = Field(default=30, description="NSE BANK NIFTY lot size")
    SENSEX_LOT_SIZE: int = Field(default=10, description="BSE SENSEX lot size")
    POSITION_SIZE_LOTS: int = Field(default=1, description="Strict 1 Lot execution policy")

    # Risk & Trailing Guardrails
    TRAILING_TRIGGER_PTS: float = Field(default=15.0, description="Profit points to trigger trailing SL")
    TRAILING_COST_OFFSET_PTS: float = Field(default=1.0, description="Cost offset for trailing SL (+1 pt to cost)")
    STAGNATION_EXIT_MINUTES: int = Field(default=45, description="Stagnation auto-exit threshold in minutes")
    
    # Strategy 1: Volatility Squeeze Parameters
    BB_PERIOD: int = 20
    BB_STDDEV: float = 2.0
    KC_PERIOD: int = 20
    KC_ATR_MULT: float = 1.5
    SQUEEZE_RVOL_THRESHOLD: float = 1.2
    SQUEEZE_SL_ATR_MULT: float = 1.5
    SQUEEZE_TARGET_ATR_MULT: float = 3.5

    # Strategy 2: ORB + VWAP Sniper Parameters
    ORB_START_TIME: str = "09:15"
    ORB_END_TIME: str = "09:30"
    ORB_MIN_RANGE: float = 25.0
    ORB_MAX_RANGE: float = 90.0
    ORB_HARD_SL_PTS: float = 12.0
    ORB_TARGET_PTS: float = 30.0

    # Strategy 3: Cash Mean Reversion Parameters
    RSI_PERIOD: int = 14
    RSI_OVERSOLD: float = 30.0
    RSI_OVERBOUGHT: float = 70.0

    # Telegram Bot Desks
    TELEGRAM_BOT_TOKEN: str = Field(default="", description="Telegram Bot Token")
    TELEGRAM_DESK_1_CHAT_ID: str = Field(default="", description="Desk 1 Chat ID")
    TELEGRAM_DESK_2_CHAT_ID: str = Field(default="", description="Desk 2 Chat ID")

    # Broker Credentials: Fyers API v3
    FYERS_APP_ID: str = ""
    FYERS_SECRET_KEY: str = ""
    FYERS_REDIRECT_URI: str = "http://127.0.0.1:8000/api/fyers/callback"
    FYERS_ACCESS_TOKEN: str = ""

    # Broker Credentials: Kotak Neo
    KOTAK_NEO_CONSUMER_KEY: str = ""
    KOTAK_NEO_CONSUMER_SECRET: str = ""
    KOTAK_NEO_MOBILE: str = ""
    KOTAK_NEO_PASSWORD: str = ""

    # Broker Credentials: Zerodha Kite
    ZERODHA_API_KEY: str = ""
    ZERODHA_API_SECRET: str = ""
    ZERODHA_ACCESS_TOKEN: str = ""

    # Broker Credentials: Angel One SmartAPI
    ANGEL_ONE_API_KEY: str = ""
    ANGEL_ONE_CLIENT_CODE: str = ""
    ANGEL_ONE_PASSWORD: str = ""
    ANGEL_ONE_TOTP_KEY: str = ""

    # Server & Storage Paths
    SERVER_HOST: str = "127.0.0.1"
    SERVER_PORT: int = 8000
    DATABASE_PATH: str = str(BASE_DIR / "data" / "ledger.db")
    AUDIT_LOG_CSV: str = str(BASE_DIR / "logs" / "paper_trading_results.csv")

settings = Settings()
