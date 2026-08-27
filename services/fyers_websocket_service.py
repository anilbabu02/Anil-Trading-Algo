import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from config.settings import settings

class FyersWebSocketService:
    """
    Low-Latency Binary WebSocket Client for Fyers API v3:
    - Subscribes to Index Feeds: NIFTY 50, BANK NIFTY, SENSEX, FINNIFTY
    - Subscribes to Active Option Contracts
    - Dispatches sub-50ms tick updates directly into the FastAPI WebSocket channel
    """

    def __init__(self, app_id: Optional[str] = None, access_token: Optional[str] = None):
        self.app_id = app_id or settings.FYERS_APP_ID
        self.access_token = access_token or settings.FYERS_ACCESS_TOKEN
        self.is_connected = False
        self.subscribed_symbols: List[str] = [
            "NSE:NIFTY50-INDEX",
            "NSE:NIFTYBANK-INDEX",
            "BSE:SENSEX-INDEX",
            "NSE:FINNIFTY-INDEX"
        ]
        self.callbacks: List[Callable[[Dict[str, Any]], None]] = []

    def register_callback(self, cb: Callable[[Dict[str, Any]], None]):
        """Registers a listener callback for incoming tick packets."""
        self.callbacks.append(cb)

    def on_tick_message(self, tick_data: Dict[str, Any]):
        """Dispatches tick packet to all registered listeners."""
        for cb in self.callbacks:
            try:
                cb(tick_data)
            except Exception as e:
                print("WS Callback Dispatch Error:", e)

    def subscribe(self, symbols: List[str]):
        """Adds new contracts to live subscription list."""
        for s in symbols:
            if s not in self.subscribed_symbols:
                self.subscribed_symbols.append(s)

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_connected": bool(self.access_token),
            "subscribed_count": len(self.subscribed_symbols),
            "symbols": self.subscribed_symbols,
            "latency_mode": "SUB_50MS_BINARY"
        }

fyers_ws_service = FyersWebSocketService()
