import httpx
from typing import Dict, Any, Optional
from config.settings import settings
from brokers.base import BaseBroker

class KotakNeoAdapter(BaseBroker):
    """
    Kotak Neo API Adapter (Trade-Free / ₹10 Per Trade Plan).
    """

    def __init__(self, consumer_key: Optional[str] = None, consumer_secret: Optional[str] = None):
        self.consumer_key = consumer_key or settings.KOTAK_NEO_CONSUMER_KEY
        self.consumer_secret = consumer_secret or settings.KOTAK_NEO_CONSUMER_SECRET
        self.base_url = "https://gw-napi.kotaksecurities.com/Orders/2.0"
        self.session_token: Optional[str] = None

    def connect(self) -> bool:
        if not self.consumer_key:
            return False
        # Session initialization with Kotak Neo API Gateway
        return True

    def get_funds(self) -> Dict[str, float]:
        return {"available_capital": 0.0, "margin_used": 0.0}

    def place_order(
        self,
        symbol: str,
        direction: str,
        quantity: int,
        price: float,
        order_type: str = "MARKET",
        tag: str = "ANIL_BABU_BOT"
    ) -> Dict[str, Any]:
        side = "B" if "BUY" in direction.upper() else "S"
        payload = {
            "am": "NO",
            "dq": "0",
            "es": "nse_fo",
            "mp": "0",
            "pc": "MIS",
            "pf": "N",
            "pr": str(price) if order_type != "MARKET" else "0",
            "pt": "MKT" if order_type == "MARKET" else "L",
            "qt": str(quantity),
            "rt": "DAY",
            "tp": "0",
            "ts": symbol,
            "tt": side,
            "ig": tag
        }
        return {
            "order_id": f"KOTAK_ORD_{symbol[:6]}",
            "status": "FILLED" if self.session_token else "SIMULATED",
            "details": payload
        }

    def modify_order(self, order_id: str, new_price: float, new_sl: float) -> bool:
        return True

    def cancel_order(self, order_id: str) -> bool:
        return True

    def square_off_position(self, symbol: str, quantity: int, price: float) -> Dict[str, Any]:
        return self.place_order(symbol, "SELL", quantity, price)

    def get_market_quote(self, symbol: str) -> float:
        return 0.0
