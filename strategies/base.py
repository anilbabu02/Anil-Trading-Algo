from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import pandas as pd
from core.models import Signal, SignalDirection, StrategyType

class BaseStrategy(ABC):
    def __init__(self, name: StrategyType):
        self.name = name

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, current_symbol: str) -> Optional[Signal]:
        """
        Analyze recent OHLCV candle data and return a Signal if entry criteria are met.
        df should contain columns: ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        """
        pass

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high = df['high']
        low = df['low']
        close_prev = df['close'].shift(1)
        tr1 = high - low
        tr2 = (high - close_prev).abs()
        tr3 = (low - close_prev).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    @staticmethod
    def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0):
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        return sma, upper, lower

    @staticmethod
    def calculate_keltner_channels(df: pd.DataFrame, period: int = 20, atr_mult: float = 1.5):
        ema = df['close'].ewm(span=period, adjust=False).mean()
        atr = BaseStrategy.calculate_atr(df, period=period)
        upper = ema + (atr_mult * atr)
        lower = ema - (atr_mult * atr)
        return ema, upper, lower

    @staticmethod
    def calculate_vwap(df: pd.DataFrame) -> pd.Series:
        typical_price = (df['high'] + df['low'] + df['close']) / 3.0
        cum_pv = (typical_price * df['volume']).cumsum()
        cum_vol = df['volume'].cumsum()
        return cum_pv / (cum_vol.replace(0, 1e-9))

    @staticmethod
    def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        plus_dm = df['high'].diff()
        minus_dm = df['low'].diff().abs()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        tr = BaseStrategy.calculate_atr(df, period=period)
        plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / tr.replace(0, 1e-9))
        minus_di = 100 * (minus_dm.ewm(alpha=1/period).mean() / tr.replace(0, 1e-9))

        dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-9) * 100
        adx = dx.ewm(alpha=1/period).mean()
        return adx
