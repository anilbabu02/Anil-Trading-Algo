import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from core.financial_ml import (
    get_weights_ffd,
    frac_diff_ffd,
    get_cusum_events,
    get_events,
    get_meta_labels,
    compute_bet_size,
    DollarVolumeBarGenerator
)

def test_fixed_width_fractional_differentiation():
    w = get_weights_ffd(d=0.4, thres=1e-4)
    assert len(w) > 0
    assert w[0][0] != 0

    # Test FFD on synthetic price series
    dates = pd.date_range("2026-01-01", periods=100, freq="5min")
    prices = 24000 + np.cumsum(np.random.randn(100) * 10)
    df = pd.DataFrame({"close": prices}, index=dates)
    
    ffd_df = frac_diff_ffd(df, d=0.4, thres=1e-4)
    assert "close" in ffd_df.columns
    assert ffd_df["close"].dropna().shape[0] > 0

def test_cusum_filter_event_sampling():
    dates = pd.date_range("2026-01-01", periods=100, freq="5min")
    # Series with abrupt jump
    prices = np.full(100, 24500.0)
    prices[40:] += 50.0  # Big jump exceeding threshold
    series = pd.Series(prices, index=dates)

    events = get_cusum_events(series, threshold=20.0)
    assert len(events) > 0
    assert dates[40] in events

def test_continuous_bet_sizing():
    # 50% probability -> 0 bet size
    assert compute_bet_size(0.50) == 0.0
    
    # 90% probability -> high positive conviction
    bet_high = compute_bet_size(0.90)
    assert bet_high >= 0.70
    
    # 10% probability -> short conviction
    bet_low = compute_bet_size(0.10)
    assert bet_low <= -0.70

def test_dollar_bars_sampling():
    dates = pd.date_range("2026-01-01", periods=50, freq="5min")
    df = pd.DataFrame({
        "timestamp": dates,
        "open": np.full(50, 24500.0),
        "high": np.full(50, 24520.0),
        "low": np.full(50, 24480.0),
        "close": np.full(50, 24500.0),
        "volume": np.full(50, 2000.0)  # 24500 * 2000 = 4.9 Crore per bar
    })

    generator = DollarVolumeBarGenerator(dollar_threshold=100000000.0)
    dollar_bars = generator.create_dollar_bars(df)
    assert len(dollar_bars) > 0
    assert "dollar_value" in dollar_bars.columns
