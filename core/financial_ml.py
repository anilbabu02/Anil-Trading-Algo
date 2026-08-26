import math
import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Any, Optional

def standard_normal_cdf(z: float) -> float:
    """Computes standard Normal Cumulative Distribution Function using standard math.erf."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

# =====================================================================
# 1. FIXED-WIDTH FRACTIONAL DIFFERENTIATION (FFD) (Chapter 5)
# Preserves maximum price memory (~90-99% correlation) while achieving stationarity
# =====================================================================

def get_weights_ffd(d: float, thres: float = 1e-3, max_width: int = 50) -> np.ndarray:
    """Generates binomial expansion weights for fractional differentiation."""
    w = [1.0]
    k = 1
    while k < max_width:
        w_ = -w[-1] / k * (d - k + 1)
        if abs(w_) < thres:
            break
        w.append(w_)
        k += 1
    return np.array(w[::-1]).reshape(-1, 1)

def frac_diff_ffd(series: pd.DataFrame, d: float = 0.40, thres: float = 1e-3, max_width: int = 50) -> pd.DataFrame:
    """
    Applies fixed-width fractional differentiation to retain memory while making series stationary.
    """
    w = get_weights_ffd(d, thres, max_width)
    width = len(w) - 1
    df = {}
    for name in series.columns:
        s_f = series[[name]].ffill().dropna()
        res = pd.Series(index=s_f.index, dtype=float)
        if s_f.shape[0] > width:
            for i in range(width, s_f.shape[0]):
                loc0, loc1 = s_f.index[i - width], s_f.index[i]
                if not np.isfinite(s_f.loc[loc1, name]):
                    continue
                res.loc[loc1] = np.dot(w.T, s_f.loc[loc0:loc1])[0, 0]
        else:
            res = s_f[name]
        df[name] = res
    return pd.DataFrame(df)

# =====================================================================
# 2. SYMMETRIC CUSUM FILTER (Event-Driven Sampling) (Chapter 2)
# Filters meaningful structural events instead of arbitrary time bars
# =====================================================================

def get_cusum_events(raw_series: pd.Series, threshold: float) -> pd.DatetimeIndex:
    """
    Symmetric CUSUM Filter: Detects volatility breakouts when cumulative returns exceed dynamic threshold h.
    """
    t_events, s_pos, s_neg = [], 0.0, 0.0
    diff = raw_series.diff().dropna()
    for i in diff.index:
        s_pos = max(0.0, s_pos + diff.loc[i])
        s_neg = min(0.0, s_neg + diff.loc[i])
        if s_neg < -threshold:
            s_neg = 0.0
            t_events.append(i)
        elif s_pos > threshold:
            s_pos = 0.0
            t_events.append(i)
    return pd.DatetimeIndex(t_events)

# =====================================================================
# 3. TRIPLE-BARRIER METHOD & META-LABELING (Chapter 3)
# Decouples Side (Direction) from Size (Conviction)
# =====================================================================

def get_events(
    close: pd.Series,
    t_events: pd.DatetimeIndex,
    pt_sl: List[float],
    trgt: pd.Series,
    min_ret: float = 0.001,
    t1: Optional[pd.Series] = None,
    side: Optional[pd.Series] = None
) -> pd.DataFrame:
    """
    Applies Triple-Barrier Method:
    - Upper Barrier: Profit Taking (pt * volatility)
    - Lower Barrier: Stop Loss (sl * volatility)
    - Vertical Barrier: Expiration time limit t1
    """
    trgt = trgt.loc[trgt.index.intersection(t_events)]
    trgt = trgt[trgt > min_ret]
    if t1 is None:
        t1 = pd.Series(pd.NaT, index=trgt.index)
    if side is None:
        side_ = pd.Series(1.0, index=trgt.index)
        pt_sl_ = [pt_sl[0], pt_sl[0]]
    else:
        side_ = side.loc[trgt.index]
        pt_sl_ = pt_sl[:2]

    events = pd.concat({'t1': t1, 'trgt': trgt, 'side': side_}, axis=1).dropna(subset=['trgt'])
    out = events[['t1']].copy()
    pt = pt_sl_[0] * events['trgt'] if pt_sl_[0] > 0 else pd.Series(index=events.index)
    sl = -pt_sl_[1] * events['trgt'] if pt_sl_[1] > 0 else pd.Series(index=events.index)

    for loc, end_t in events['t1'].fillna(close.index[-1]).items():
        df0 = close[loc:end_t]
        if len(df0) == 0:
            continue
        df0 = (df0 / close[loc] - 1.0) * events.at[loc, 'side']
        out.loc[loc, 'sl'] = df0[df0 < sl[loc]].index.min() if loc in sl else np.nan
        out.loc[loc, 'pt'] = df0[df0 > pt[loc]].index.min() if loc in pt else np.nan

    events['t1'] = out.dropna(how='all').min(axis=1)
    return events

def get_meta_labels(events: pd.DataFrame, close: pd.Series) -> pd.DataFrame:
    """
    Meta-Labeling: Generates binary target labels y in {0, 1} indicating whether the trade achieved profit before stop-loss.
    """
    events_ = events.dropna(subset=['t1'])
    px = events_.index.union(events_['t1'].values).drop_duplicates()
    px = close.reindex(px, method='bfill')
    out = pd.DataFrame(index=events_.index)
    out['ret'] = px.loc[events_['t1'].values].values / px.loc[events_.index] - 1.0
    if 'side' in events_:
        out['ret'] *= events_['side']
    out['bin'] = np.sign(out['ret'])
    if 'side' in events_:
        out.loc[out['ret'] <= 0, 'bin'] = 0
    return out

# =====================================================================
# 4. PURGED K-FOLD CROSS-VALIDATION (Chapters 7 & 9)
# Eliminates data leakage across overlapping financial event windows
# =====================================================================

class PurgedKFold:
    """
    Purged & Embargoed K-Fold Cross-Validation:
    1. Purging: Removes training observations whose lifespan overlaps with the testing set.
    2. Embargoing: Excludes post-test period (1%) to prevent autoregressive feature leakage.
    """
    def __init__(self, n_splits: int = 3, t1: Optional[pd.Series] = None, pct_embargo: float = 0.01):
        self.n_splits = n_splits
        self.t1 = t1
        self.pct_embargo = pct_embargo

    def split(self, X: pd.DataFrame):
        indices = np.arange(X.shape[0])
        mbrg = int(X.shape[0] * self.pct_embargo)
        test_starts = [(s[0], s[-1] + 1) for s in np.array_split(indices, self.n_splits)]
        for i, j in test_starts:
            t0 = self.t1.index[i]
            test_indices = indices[i:j]
            max_t1_idx = self.t1.index.searchsorted(self.t1.iloc[test_indices].max())
            train_indices = self.t1.index.searchsorted(self.t1[self.t1 <= t0].index)
            if max_t1_idx < X.shape[0]:
                train_indices = np.concatenate((train_indices, indices[max_t1_idx + mbrg:]))
            yield train_indices, test_indices

# =====================================================================
# 5. DYNAMIC CONTINUOUS BET SIZING FROM PROBABILITIES (Chapter 10)
# Maps ML classifier probability p to continuous bet size m via standard Normal CDF
# =====================================================================

def compute_bet_size(prob: float, step_size: float = 0.1) -> float:
    """
    López de Prado Bet Sizing:
    z = (p - 0.5) / sqrt(p * (1 - p))
    m = 2 * N(z) - 1 in [-1, 1]
    """
    prob = float(np.clip(prob, 1e-6, 1.0 - 1e-6))
    z = (prob - 0.5) / math.sqrt(prob * (1.0 - prob) + 1e-9)
    signal = 2.0 * standard_normal_cdf(float(z)) - 1.0
    discrete_signal = round(signal / step_size) * step_size
    return float(np.clip(discrete_signal, -1.0, 1.0))

# =====================================================================
# 6. DOLLAR & VOLUME BARS SAMPLING (Chapter 2)
# =====================================================================

class DollarVolumeBarGenerator:
    """
    Converts tick-level or chronological bars into Dollar Bars (Price x Volume) and Volume Bars.
    Eliminates heteroscedasticity and restores return normality.
    """
    def __init__(self, dollar_threshold: float = 5000000.0, volume_threshold: float = 50000.0):
        self.dollar_threshold = dollar_threshold
        self.volume_threshold = volume_threshold

    def create_dollar_bars(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregates dataframe into constant dollar value bars ($ = Close * Volume)."""
        df = df.copy()
        df['dollar_value'] = df['close'] * df['volume']
        df['cum_dollar'] = df['dollar_value'].cumsum()
        df['bar_id'] = (df['cum_dollar'] // self.dollar_threshold).astype(int)

        dollar_bars = df.groupby('bar_id').agg({
            'timestamp': 'last',
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'dollar_value': 'sum'
        }).reset_index(drop=True)

        return dollar_bars
