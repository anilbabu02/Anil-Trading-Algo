import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from strategies.volatility_squeeze import VolatilitySqueezeStrategy
from strategies.orb_vwap_sniper import ORBVWAPSniperStrategy
from strategies.cash_mean_reversion import CashMeanReversionStrategy
from strategies.market_regime import MarketRegimeClassifier
from core.models import SignalDirection, MarketRegime

def create_synthetic_df(n_candles=30, trend="bull"):
    records = []
    base_time = datetime(2026, 8, 23, 9, 15)
    base_price = 24500.0

    for i in range(n_candles):
        t = base_time + timedelta(minutes=i*5)
        if i < n_candles - 1:
            # Low volatility compression inside squeeze (candles 0 to 28)
            open_p = base_price + (i * 0.1)
            close_p = open_p + 0.2
            high_p = close_p + 0.5
            low_p = open_p - 0.5
            vol = 10000
        else:
            # Final candle (29): Strong breakout expansion with high volume
            delta = 25.0 if trend == "bull" else -25.0
            open_p = records[-1]['close'] if records else base_price
            close_p = open_p + delta
            high_p = max(open_p, close_p) + 6.0
            low_p = min(open_p, close_p) - 2.0
            vol = 50000  # RVOL >= 1.2x

        records.append({
            'timestamp': t,
            'open': open_p,
            'high': high_p,
            'low': low_p,
            'close': close_p,
            'volume': vol
        })
    return pd.DataFrame(records)

def test_volatility_squeeze_bullish_signal():
    strat = VolatilitySqueezeStrategy()
    df = create_synthetic_df(n_candles=30, trend="bull")
    signal = strat.generate_signal(df, "NIFTY")
    
    assert signal is not None
    assert signal.direction == SignalDirection.BUY_CE
    assert signal.target > signal.entry_price
    assert signal.stop_loss < signal.entry_price
    assert signal.trailing_trigger == 15.0

def test_orb_vwap_range_filter():
    strat = ORBVWAPSniperStrategy()
    # Create DF with narrow range (<25 pts)
    records = []
    base_time = datetime(2026, 8, 23, 9, 15)
    for i in range(10):
        records.append({
            'timestamp': base_time + timedelta(minutes=i*5),
            'open': 24500.0,
            'high': 24505.0,  # 5 pt range
            'low': 24500.0,
            'close': 24502.0,
            'volume': 15000
        })
    df_narrow = pd.DataFrame(records)
    sig = strat.generate_signal(df_narrow, "NIFTY")
    assert sig is None  # Filtered out due to range < 25 pts

def test_market_regime_choppy():
    records = []
    base_time = datetime(2026, 8, 23, 9, 15)
    for i in range(25):
        records.append({
            'timestamp': base_time + timedelta(minutes=i*5),
            'open': 24500.0,
            'high': 24504.0,
            'low': 24498.0,
            'close': 24501.0,
            'volume': 5000
        })
    df = pd.DataFrame(records)
    res = MarketRegimeClassifier.classify_regime(df, 24500.0)
    assert res["regime"] == MarketRegime.CHOPPY_SIDEWAYS
    assert res["allow_ce"] is False
    assert res["allow_pe"] is False
