from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class StrategyType(str, Enum):
    SQUEEZE_BREAKOUT = "SQUEEZE_BREAKOUT"
    ORB_VWAP_SNIPER = "ORB_VWAP_SNIPER"
    CASH_MEAN_REVERSION = "CASH_MEAN_REVERSION"

class MarketRegime(str, Enum):
    TRENDING_BULL = "TRENDING_BULL"
    TRENDING_BEAR = "TRENDING_BEAR"
    CHOPPY_SIDEWAYS = "CHOPPY_SIDEWAYS"
    GAP_OPENING = "GAP_OPENING"
    UNKNOWN = "UNKNOWN"

class SignalDirection(str, Enum):
    BUY_CE = "BUY_CE"
    BUY_PE = "BUY_PE"
    BUY_EQUITY = "BUY_EQUITY"
    SELL_EQUITY = "SELL_EQUITY"
    NO_SIGNAL = "NO_SIGNAL"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    PEGGED_LIMIT = "PEGGED_LIMIT"

class Signal(BaseModel):
    strategy: StrategyType
    symbol: str
    direction: SignalDirection
    timestamp: datetime = Field(default_factory=datetime.now)
    index_price: float
    strike_price: Optional[float] = None
    option_type: Optional[str] = None  # "CE" | "PE"
    entry_price: float
    stop_loss: float
    target: float
    trailing_trigger: float = 15.0
    rvol: float = 1.0
    adx: float = 20.0
    confidence: float = 0.8
    notes: str = ""

class Position(BaseModel):
    id: str
    symbol: str
    strategy: StrategyType
    direction: SignalDirection
    quantity: int
    entry_price: float
    underlying_entry_price: float = 0.0
    current_price: float
    stop_loss: float
    original_stop_loss: float
    target: float
    trailing_activated: bool = False
    entry_time: datetime = Field(default_factory=datetime.now)
    last_update_time: datetime = Field(default_factory=datetime.now)
    unrealized_pnl: float = 0.0
    max_favorable_excursion: float = 0.0  # Max profit reached in points
    broker: str = "PAPER"

class TradeRecord(BaseModel):
    id: str
    symbol: str
    strategy: StrategyType
    direction: SignalDirection
    quantity: int
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    exit_reason: str  # "TARGET", "STOP_LOSS", "TRAILING_SL", "STAGNATION_EXIT", "CIRCUIT_BREAKER", "MANUAL"
    gross_pnl: float
    charges: float
    net_pnl: float
    duration_minutes: float
    broker: str = "PAPER"

class SystemStatus(BaseModel):
    trading_mode: str
    active_regime: MarketRegime
    current_capital: float
    starting_capital: float
    today_realized_pnl: float
    today_unrealized_pnl: float
    today_trade_count: int
    max_trades_per_day: int
    circuit_breaker_tripped: bool
    open_positions_count: int
    bot_connected: bool
    last_tick_time: Optional[datetime] = None
