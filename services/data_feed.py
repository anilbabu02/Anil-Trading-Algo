import asyncio
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Optional, Callable

class MarketDataFeed:
    """
    Market Data Ingestion and Candle Buffer Manager:
    - Maintains rolling 5-minute OHLCV candles
    - Provides real-time simulated tick replay for testing
    - Ingests live WebSocket quotes from Fyers/Zerodha
    """

    def __init__(self, symbol: str = "NIFTY", timeframe: str = "5m"):
        self.symbol = symbol
        self.timeframe = timeframe
        self.candles_df: pd.DataFrame = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        self.subscribers: List[Callable[[pd.DataFrame, float], Any]] = []
        self.last_price: float = 24500.0

    def subscribe(self, callback: Callable[[pd.DataFrame, float], Any]):
        self.subscribers.append(callback)

    def set_historical_data(self, df: pd.DataFrame):
        self.candles_df = df.copy()
        if not df.empty:
            self.last_price = float(df['close'].iloc[-1])

    def append_candle(self, timestamp: datetime, open_: float, high: float, low: float, close: float, volume: float):
        new_row = pd.DataFrame([{
            'timestamp': timestamp,
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }])
        self.candles_df = pd.concat([self.candles_df, new_row], ignore_index=True)
        # Keep last 150 candles in memory for performance (<200MB RAM)
        if len(self.candles_df) > 150:
            self.candles_df = self.candles_df.iloc[-150:].reset_index(drop=True)
        self.last_price = close

    def generate_synthetic_session(self, n_candles: int = 75, base_price: float = 24500.0) -> pd.DataFrame:
        """
        Generates realistic 5-min Indian market day (75 candles: 09:15 to 15:30)
        with volatility compression and breakout structure.
        """
        records = []
        start_time = datetime.combine(datetime.today(), time(9, 15))
        current_price = base_price

        for i in range(n_candles):
            t = start_time + timedelta(minutes=i * 5)
            # Create a realistic squeeze around candle 15-25, followed by breakout
            if 15 <= i <= 25:
                volatility = 4.0  # Squeeze compression
                volume = random.randint(8000, 15000)
            elif 26 <= i <= 35:
                volatility = 18.0  # Breakout expansion
                volume = random.randint(35000, 70000)  # RVOL surge
                current_price += random.uniform(8.0, 16.0)
            else:
                volatility = 10.0
                volume = random.randint(15000, 30000)

            drift = random.gauss(0.5, volatility)
            open_p = current_price
            close_p = open_p + drift
            high_p = max(open_p, close_p) + abs(random.gauss(0, volatility * 0.4))
            low_p = min(open_p, close_p) - abs(random.gauss(0, volatility * 0.4))
            current_price = close_p

            records.append({
                'timestamp': t,
                'open': round(open_p, 2),
                'high': round(high_p, 2),
                'low': round(low_p, 2),
                'close': round(close_p, 2),
                'volume': volume
            })

        df = pd.DataFrame(records)
        self.set_historical_data(df)
        return df
