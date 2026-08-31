"""
The single in-memory market snapshot. One writer (services.feed_manager), many
readers (every HTTP endpoint and the SSE stream).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from services.market_calendar import now_ist

STALE_AFTER = {
    "spot": 15.0,       # 15s display freshness for spot
    "chain": 30.0,      # option chain
    "candles": 300.0,   # 5-minute candles
}


def _epoch() -> float:
    return now_ist().timestamp()


@dataclass
class Entry:
    """One cached value plus everything a reader needs to judge it."""

    value: Any = None
    fetched_at: float = 0.0
    source: str = "UNAVAILABLE"     # LIVE_BROKER | LIVE_WS | DELAYED_PUBLIC | UNAVAILABLE
    error: Optional[str] = None
    fetch_count: int = 0
    error_count: int = 0

    def age(self) -> float:
        return _epoch() - self.fetched_at if self.fetched_at else float("inf")

    def is_stale(self, kind: str) -> bool:
        return self.age() > STALE_AFTER.get(kind, 10.0)

    def meta(self, kind: str) -> Dict[str, Any]:
        age = self.age()
        return {
            "data_source": self.source,
            "age_seconds": round(age, 2) if age != float("inf") else None,
            "is_stale": self.is_stale(kind),
            "error": self.error,
        }


class MarketStore:
    """Last-known market state. Read by everything, written by the feed only."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._spot: Dict[str, Entry] = {}          # instrument -> Entry(quote dict)
        self._chains: Dict[str, Entry] = {}        # instrument -> Entry(list of rows)
        self._candles: Dict[str, Entry] = {}       # "SYM:res"  -> Entry(list of candles)
        self._atr: Dict[str, float] = {}           # instrument -> ATR(14) in points
        self._request_budget = RequestBudget()
        self._feed_status: Dict[str, Any] = {"running": False, "started_at": None}

    # ------------------------------------------------------------- spot

    def put_spot(self, quotes: Dict[str, Dict[str, Any]], source: str) -> None:
        with self._lock:
            now = _epoch()
            for instrument, q in quotes.items():
                prev = self._spot.get(instrument, Entry())
                self._spot[instrument] = Entry(
                    value=dict(q, data_source=source),
                    fetched_at=now,
                    source=source,
                    fetch_count=prev.fetch_count + 1,
                    error_count=prev.error_count,
                )

    def put_spot_error(self, reason: str) -> None:
        with self._lock:
            for instrument, e in self._spot.items():
                self._spot[instrument] = Entry(
                    value=e.value, fetched_at=e.fetched_at, source=e.source,
                    error=reason, fetch_count=e.fetch_count, error_count=e.error_count + 1,
                )

    def spot(self, instrument: str) -> Entry:
        with self._lock:
            return self._spot.get(instrument.upper(), Entry())

    def all_spot(self) -> Dict[str, Dict[str, Any]]:
        """Quote map in the shape the existing endpoints already return."""
        with self._lock:
            return {k: dict(e.value or {}) for k, e in self._spot.items() if e.value}

    # ------------------------------------------------------------ chains

    def put_chain(self, instrument: str, rows: List[Dict[str, Any]], source: str) -> None:
        with self._lock:
            prev = self._chains.get(instrument.upper(), Entry())
            self._chains[instrument.upper()] = Entry(
                value=rows, fetched_at=_epoch(), source=source,
                fetch_count=prev.fetch_count + 1, error_count=prev.error_count,
            )

    def put_chain_error(self, instrument: str, reason: str) -> None:
        with self._lock:
            prev = self._chains.get(instrument.upper(), Entry())
            self._chains[instrument.upper()] = Entry(
                value=prev.value, fetched_at=prev.fetched_at, source=prev.source,
                error=reason, fetch_count=prev.fetch_count, error_count=prev.error_count + 1,
            )

    def chain(self, instrument: str) -> Entry:
        with self._lock:
            return self._chains.get(instrument.upper(), Entry())

    # ----------------------------------------------------------- candles

    def put_candles(self, symbol: str, resolution: str, candles: List[Dict[str, Any]], source: str) -> None:
        key = f"{symbol}:{resolution}"
        with self._lock:
            prev = self._candles.get(key, Entry())
            self._candles[key] = Entry(
                value=candles, fetched_at=_epoch(), source=source,
                fetch_count=prev.fetch_count + 1, error_count=prev.error_count,
            )

    def put_candles_error(self, symbol: str, resolution: str, reason: str) -> None:
        key = f"{symbol}:{resolution}"
        with self._lock:
            prev = self._candles.get(key, Entry())
            self._candles[key] = Entry(
                value=prev.value, fetched_at=prev.fetched_at, source=prev.source,
                error=reason, fetch_count=prev.fetch_count, error_count=prev.error_count + 1,
            )

    def candles(self, symbol: str, resolution: str = "5") -> Entry:
        with self._lock:
            return self._candles.get(f"{symbol}:{resolution}", Entry())

    # --------------------------------------------------------------- atr

    def put_atr(self, instrument: str, atr_points: float) -> None:
        with self._lock:
            self._atr[instrument.upper()] = round(float(atr_points), 2)

    def atr_map(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._atr)

    # ------------------------------------------------------------ budget

    @property
    def budget(self) -> RequestBudget:
        return self._request_budget

    def set_feed_status(self, **kw: Any) -> None:
        with self._lock:
            self._feed_status.update(kw)

    # ---------------------------------------------------------- snapshot

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            quotes = {}
            for k, e in self._spot.items():
                if not e.value:
                    continue
                quotes[k] = dict(e.value, **e.meta("spot"))

            chains = {
                k: {"rows": len(e.value or []), **e.meta("chain")}
                for k, e in self._chains.items()
            }
            candles = {
                k: {"count": len(e.value or []), **e.meta("candles")}
                for k, e in self._candles.items()
            }

            live_spot = any(
                e.source in ("LIVE_BROKER", "LIVE_WS", "DELAYED_PUBLIC") and not e.is_stale("spot")
                for e in self._spot.values()
            )
            live_chain = any(
                e.source == "LIVE_BROKER" and not e.is_stale("chain")
                for e in self._chains.values()
            )

            return {
                "as_of": now_ist().strftime("%H:%M:%S IST"),
                "epoch": round(_epoch(), 3),
                "spot_live": live_spot,
                "chain_live": live_chain,
                "quotes": quotes,
                "chains": chains,
                "candles": candles,
                "atr": dict(self._atr),
                "feed": dict(self._feed_status),
                "budget": self._request_budget.report(),
            }


class RequestBudget:
    PER_MINUTE = 120
    PER_DAY = 40_000

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._minute_bucket: List[float] = []
        self._day_count = 0
        self._day_stamp = now_ist().date()
        self.throttled_until = 0.0

    def allow(self) -> bool:
        now = _epoch()
        with self._lock:
            today = now_ist().date()
            if today != self._day_stamp:
                self._day_stamp, self._day_count = today, 0
            if now < self.throttled_until:
                return False
            self._minute_bucket = [t for t in self._minute_bucket if now - t < 60.0]
            if len(self._minute_bucket) >= self.PER_MINUTE:
                return False
            if self._day_count >= self.PER_DAY:
                return False
            self._minute_bucket.append(now)
            self._day_count += 1
            return True

    def back_off(self, seconds: float) -> None:
        with self._lock:
            self.throttled_until = max(self.throttled_until, _epoch() + seconds)

    def report(self) -> Dict[str, Any]:
        now = _epoch()
        with self._lock:
            recent = len([t for t in self._minute_bucket if now - t < 60.0])
            return {
                "last_minute": recent,
                "minute_limit": self.PER_MINUTE,
                "today": self._day_count,
                "day_limit": self.PER_DAY,
                "throttled": now < self.throttled_until,
                "throttled_for": round(max(0.0, self.throttled_until - now), 1),
            }


def compute_atr(candles: List[Dict[str, Any]], period: int = 14) -> Optional[float]:
    if not candles or len(candles) < period + 1:
        return None

    trs: List[float] = []
    prev_close = float(candles[0].get("c", 0.0))
    for c in candles[1:]:
        high, low, close = float(c.get("h", 0)), float(c.get("l", 0)), float(c.get("c", 0))
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
        prev_close = close

    if len(trs) < period:
        return None

    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return round(atr, 2)


store = MarketStore()
