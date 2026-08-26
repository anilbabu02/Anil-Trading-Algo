from datetime import datetime, time
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
from core.models import MarketRegime, SignalDirection
from strategies.base import BaseStrategy

class MarketRegimeClassifier:
    """
    Microstructure & Institutional Regime Classifier for Indian Markets:
    - Trending Bull: Price > VWAP, EMA 12 > 26, ADX > 20 -> Only ATM CE allowed.
    - Trending Bear: Price < VWAP, EMA 12 < 26, ADX > 20 -> Only ATM PE allowed.
    - Choppy / Sideways Trap: ADX < 18, 15m Range < 25 pts -> 0 trades (100% Cash Defense).
    - Gap Up / Down (>40 pts): 15-min buffer (wait till 09:30 AM), VWAP continuation vs fade.
    - Expiry Day Mode: Strike rotation to Next-Week contract post 13:30.
    """

    @staticmethod
    def classify_regime(df: pd.DataFrame, prev_day_close: float = 0.0) -> Dict[str, Any]:
        if len(df) < 20:
            return {
                "regime": MarketRegime.UNKNOWN,
                "adx": 0.0,
                "rvol": 1.0,
                "ema_12": 0.0,
                "ema_26": 0.0,
                "vwap": 0.0,
                "allow_ce": False,
                "allow_pe": False,
                "description": "Insufficient candle data"
            }

        # Calculate indicators
        ema_12 = df['close'].ewm(span=12, adjust=False).mean().iloc[-1]
        ema_26 = df['close'].ewm(span=26, adjust=False).mean().iloc[-1]
        vwap_series = BaseStrategy.calculate_vwap(df)
        vwap = vwap_series.iloc[-1]
        adx_series = BaseStrategy.calculate_adx(df, period=14)
        adx = adx_series.iloc[-1] if not adx_series.empty and not np.isnan(adx_series.iloc[-1]) else 20.0

        current_close = df['close'].iloc[-1]
        day_open = df['open'].iloc[0]
        
        # Calculate opening 15m range (first 3 candles)
        orb_candles = df.iloc[:3] if len(df) >= 3 else df
        range_15m = orb_candles['high'].max() - orb_candles['low'].min()

        # Check Gap Opening (> 40 pts relative to previous close)
        gap_pts = abs(day_open - prev_day_close) if prev_day_close > 0 else 0.0
        is_large_gap = gap_pts >= 40.0

        # Check Choppy / Sideways Trap
        if (adx < 18.0) and (range_15m < 25.0):
            return {
                "regime": MarketRegime.CHOPPY_SIDEWAYS,
                "adx": round(adx, 2),
                "rvol": 0.8,
                "ema_12": round(ema_12, 2),
                "ema_26": round(ema_26, 2),
                "vwap": round(vwap, 2),
                "allow_ce": False,
                "allow_pe": False,
                "description": "Choppy Sideways Trap | ADX < 18 & 15m Range < 25pts | Sniper Defense Mode: 0 Trades (100% Cash)"
            }

        # Check Gap Protocol
        if is_large_gap and len(df) <= 3:
            # During 9:15-9:30 AM buffer period
            return {
                "regime": MarketRegime.GAP_OPENING,
                "adx": round(adx, 2),
                "rvol": 1.0,
                "ema_12": round(ema_12, 2),
                "ema_26": round(ema_26, 2),
                "vwap": round(vwap, 2),
                "allow_ce": False,
                "allow_pe": False,
                "description": f"Large Gap Opening ({gap_pts:.1f} pts) | 15-Minute Buffer Active until 09:30 AM"
            }

        # Check Trending Bull Market
        if (current_close > vwap) and (ema_12 > ema_26) and (adx >= 20.0):
            return {
                "regime": MarketRegime.TRENDING_BULL,
                "adx": round(adx, 2),
                "rvol": 1.4,
                "ema_12": round(ema_12, 2),
                "ema_26": round(ema_26, 2),
                "vwap": round(vwap, 2),
                "allow_ce": True,
                "allow_pe": False,
                "description": "Trending Bull Market | Price > VWAP & EMA 12 > 26 & ADX > 20 | CE Buying Enabled, PE Blocked"
            }

        # Check Trending Bear Market
        if (current_close < vwap) and (ema_12 < ema_26) and (adx >= 20.0):
            return {
                "regime": MarketRegime.TRENDING_BEAR,
                "adx": round(adx, 2),
                "rvol": 1.4,
                "ema_12": round(ema_12, 2),
                "ema_26": round(ema_26, 2),
                "vwap": round(vwap, 2),
                "allow_ce": False,
                "allow_pe": True,
                "description": "Trending Bear Market | Price < VWAP & EMA 12 < 26 & ADX > 20 | PE Buying Enabled, CE Blocked"
            }

        # Neutral / Moderate
        return {
            "regime": MarketRegime.UNKNOWN,
            "adx": round(adx, 2),
            "rvol": 1.0,
            "ema_12": round(ema_12, 2),
            "ema_26": round(ema_26, 2),
            "vwap": round(vwap, 2),
            "allow_ce": True,
            "allow_pe": True,
            "description": "Normal Market Conditions | Standard Strategy Rules Active"
        }

    @staticmethod
    def get_expiry_contract_type(current_time: datetime) -> str:
        """
        Expiry Rule: Post 1:30 PM on Expiry day, rotate from Current-Week to Next-Week expiry.
        """
        # Thu (Nifty weekly), Wed (BankNifty weekly), Fri (Sensex weekly)
        weekday = current_time.weekday()
        is_expiry_day = weekday in [2, 3, 4]  # Wed, Thu, Fri
        is_post_1330 = current_time.time() >= time(13, 30)

        if is_expiry_day and is_post_1330:
            return "NEXT_WEEK_EXPIRY"
        return "CURRENT_WEEK_EXPIRY"
