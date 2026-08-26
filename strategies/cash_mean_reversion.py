from datetime import datetime
from typing import Optional
import pandas as pd
import numpy as np
from config.settings import settings
from core.models import Signal, SignalDirection, StrategyType
from strategies.base import BaseStrategy

class CashMeanReversionStrategy(BaseStrategy):
    """
    Strategy 3: Cash Equity Mean Reversion & Swing Engine (Zero Theta Decay)
    - Target: High-liquidity Large-cap Equities (Reliance, Tata Motors, HDFC Bank, Infosys, ICICI Bank).
    - Formula: RSI(14) Oversold (<30) / Overbought (>70) + Lower/Upper Bollinger Band Rejection.
    - Zero theta decay, zero weekly contract expiry risk.
    """

    def __init__(self):
        super().__init__(name=StrategyType.CASH_MEAN_REVERSION)

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0.0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, 1e-9)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_signal(self, df: pd.DataFrame, current_symbol: str) -> Optional[Signal]:
        if len(df) < 25:
            return None

        # 1. Bollinger Bands (20, 2.0)
        sma, bb_upper, bb_lower = self.calculate_bollinger_bands(df, period=20, std_dev=2.0)

        # 2. RSI (14)
        rsi = self.calculate_rsi(df, period=settings.RSI_PERIOD)
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]

        current_close = df['close'].iloc[-1]
        current_low = df['low'].iloc[-1]
        current_high = df['high'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        timestamp = df['timestamp'].iloc[-1] if 'timestamp' in df.columns else datetime.now()

        atr_series = self.calculate_atr(df, period=14)
        current_atr = atr_series.iloc[-1] if not atr_series.empty else (current_close * 0.01)

        # Long Reversal: RSI was oversold (<30), low pierced lower BB, but close bounced back inside
        if (prev_rsi < settings.RSI_OVERSOLD or current_rsi < 35) and (current_low <= bb_lower.iloc[-1]) and (current_close > bb_lower.iloc[-1]) and (current_close > prev_close):
            sl_price = round(current_low - (0.5 * current_atr), 2)
            target_price = round(current_close + (1.5 * current_atr), 2)
            return Signal(
                strategy=self.name,
                symbol=current_symbol,
                direction=SignalDirection.BUY_EQUITY,
                timestamp=timestamp,
                index_price=round(current_close, 2),
                entry_price=round(current_close, 2),
                stop_loss=sl_price,
                target=target_price,
                trailing_trigger=round(current_atr, 2),
                confidence=0.80,
                notes=f"Cash Swing Oversold Rebound | RSI: {current_rsi:.1f} | BB Rejection | Target: {target_price}"
            )

        # Short / Profit-Taking: RSI was overbought (>70), high pierced upper BB, close rejected back inside
        elif (prev_rsi > settings.RSI_OVERBOUGHT or current_rsi > 65) and (current_high >= bb_upper.iloc[-1]) and (current_close < bb_upper.iloc[-1]) and (current_close < prev_close):
            sl_price = round(current_high + (0.5 * current_atr), 2)
            target_price = round(current_close - (1.5 * current_atr), 2)
            return Signal(
                strategy=self.name,
                symbol=current_symbol,
                direction=SignalDirection.SELL_EQUITY,
                timestamp=timestamp,
                index_price=round(current_close, 2),
                entry_price=round(current_close, 2),
                stop_loss=sl_price,
                target=target_price,
                trailing_trigger=round(current_atr, 2),
                confidence=0.80,
                notes=f"Cash Swing Overbought Pullback | RSI: {current_rsi:.1f} | BB Rejection | Target: {target_price}"
            )

        return None
