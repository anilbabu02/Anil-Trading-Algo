"""
Unified Background Market Data Feed Engine.
One background daemon thread running in the background.
Reads from Fyers WebSocket / REST and writes to MarketStore.
"""

from __future__ import annotations

import threading
import time
import urllib.request
import json
import logging
from typing import Dict, Any, List

from config.settings import settings
from services.market_calendar import now_ist, is_market_open
from services.market_store import store, compute_atr

logger = logging.getLogger("feed_manager")


class FeedManager:
    """
    Single daemon thread feed:
    - 1s Spot Polling / WebSocket push
    - 3s Option Chains refresh
    - 60s Candle buffer and ATR calculation
    """

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_spot = 0.0
        self._last_chain = 0.0
        self._last_candle = 0.0

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="FeedManagerDaemon", daemon=True)
        self._thread.start()
        store.set_feed_status(running=True, started_at=now_ist().strftime("%H:%M:%S IST"))
        logger.info("FeedManager background daemon started.")

    def stop(self):
        self._stop_event.set()
        store.set_feed_status(running=False)

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                now = time.time()
                # 1. Spot refresh (every 1s)
                if now - self._last_spot >= 1.0:
                    self._refresh_spot()
                    self._last_spot = now

                # 2. Option chains refresh (every 3s)
                if now - self._last_chain >= 3.0:
                    self._refresh_chains()
                    self._last_chain = now

                # 3. Candles & ATR refresh (every 60s)
                if now - self._last_candle >= 60.0:
                    self._refresh_candles()
                    self._last_candle = now

                time.sleep(0.2)
            except Exception as e:
                logger.error(f"Feed loop error: {e}", exc_info=True)
                time.sleep(1.0)

    def _refresh_spot(self):
        if not store.budget.allow():
            return

        symbols = [
            "NSE:NIFTY50-INDEX",
            "NSE:NIFTYBANK-INDEX",
            "BSE:SENSEX-INDEX",
            "BSE:BANKEX-INDEX",
            "NSE:FINNIFTY-INDEX"
        ]
        quotes_map = {}
        source = "UNAVAILABLE"

        # Try Fyers API if authenticated
        if settings.FYERS_ACCESS_TOKEN and settings.FYERS_APP_ID:
            try:
                token_str = f"{settings.FYERS_APP_ID}:{settings.FYERS_ACCESS_TOKEN}"
                headers = {"Authorization": token_str, "User-Agent": "Mozilla/5.0"}
                url = f"https://api-t1.fyers.in/data/quotes?symbols={','.join(symbols)}"
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("s") == "ok" and data.get("d"):
                        source = "LIVE_BROKER"
                        for item in data["d"]:
                            sym = item.get("n", "")
                            v = item.get("v", {})
                            key = "NIFTY"
                            if "NIFTYBANK" in sym: key = "BANKNIFTY"
                            elif "SENSEX" in sym: key = "SENSEX"
                            elif "BANKEX" in sym: key = "BANKEX"
                            elif "FINNIFTY" in sym: key = "FINNIFTY"
                            quotes_map[key] = {
                                "symbol": sym,
                                "ltp": float(v.get("lp", 0.0)),
                                "change": float(v.get("ch", 0.0)),
                                "change_pct": float(v.get("chp", 0.0)),
                                "open": float(v.get("open_price", 0.0)),
                                "high": float(v.get("high_price", 0.0)),
                                "low": float(v.get("low_price", 0.0)),
                                "prev_close": float(v.get("prev_close_price", 0.0))
                            }
            except Exception as e:
                if "429" in str(e):
                    store.budget.back_off(30.0)

        # Fallback to direct exchange stream
        if not quotes_map:
            from backend.app import fetch_external_live_quotes
            quotes_map = fetch_external_live_quotes()
            source = "DELAYED_PUBLIC"

        if quotes_map:
            store.put_spot(quotes_map, source)

    def _refresh_chains(self):
        if not store.budget.allow():
            return

        for sym, name in [("NSE:NIFTY50-INDEX", "NIFTY"), ("NSE:NIFTYBANK-INDEX", "BANKNIFTY"), ("BSE:SENSEX-INDEX", "SENSEX")]:
            rows = []
            source = "UNAVAILABLE"
            if settings.FYERS_ACCESS_TOKEN and settings.FYERS_APP_ID:
                try:
                    token_str = f"{settings.FYERS_APP_ID}:{settings.FYERS_ACCESS_TOKEN}"
                    headers = {"Authorization": token_str, "User-Agent": "Mozilla/5.0"}
                    url = f"https://api-t1.fyers.in/data/options-chain-v3?symbol={sym}&strikecount=10"
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=3.5) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        if data.get("s") == "ok" and isinstance(data.get("data"), dict):
                            rows = data["data"].get("optionsChain", [])
                            source = "LIVE_BROKER"
                except Exception as e:
                    if "429" in str(e):
                        store.budget.back_off(30.0)

            if rows:
                store.put_chain(name, rows, source)

    def _refresh_candles(self):
        if not store.budget.allow():
            return

        for sym, name in [("NSE:NIFTY50-INDEX", "NIFTY"), ("NSE:NIFTYBANK-INDEX", "BANKNIFTY"), ("BSE:SENSEX-INDEX", "SENSEX")]:
            candles = []
            source = "UNAVAILABLE"
            if settings.FYERS_ACCESS_TOKEN and settings.FYERS_APP_ID:
                try:
                    import datetime
                    token_str = f"{settings.FYERS_APP_ID}:{settings.FYERS_ACCESS_TOKEN}"
                    headers = {"Authorization": token_str, "User-Agent": "Mozilla/5.0"}
                    t_now = int(time.time())
                    t_from = t_now - (86400 * 2)
                    url = f"https://api-t1.fyers.in/data/history?symbol={sym}&resolution=5&date_format=0&range_from={t_from}&range_to={t_now}&cont_flag=1"
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=4.0) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        if data.get("s") == "ok" and data.get("candles"):
                            raw = data["candles"]
                            candles = [{"t": c[0], "o": c[1], "h": c[2], "l": c[3], "c": c[4], "v": c[5]} for c in raw]
                            source = "LIVE_BROKER"
                except Exception as e:
                    if "429" in str(e):
                        store.budget.back_off(30.0)

            if candles:
                store.put_candles(name, "5", candles, source)
                atr = compute_atr(candles, 14)
                if atr:
                    store.put_atr(name, atr)


feed = FeedManager()
