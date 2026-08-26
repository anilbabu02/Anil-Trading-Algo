import httpx
from typing import Dict, Any, Optional
from config.settings import settings
from brokers.base import BaseBroker

class ZerodhaAdapter(BaseBroker):
    """
    Zerodha Kite Connect v3 Adapter.
    """

    def __init__(self, api_key: Optional[str] = None, access_token: Optional[str] = None):
        self.api_key = api_key or settings.ZERODHA_API_KEY
        self.access_token = access_token or settings.ZERODHA_ACCESS_TOKEN
        self.base_url = "https://api.kite.trade"
        self.headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}" if self.api_key and self.access_token else ""
        }

    def connect(self) -> bool:
        if not self.access_token:
            return False
        try:
            with httpx.Client() as client:
                res = client.get(f"{self.base_url}/user/profile", headers=self.headers, timeout=5.0)
                return res.status_code == 200 and res.json().get("status") == "success"
        except Exception:
            return False

    def get_funds(self) -> Dict[str, float]:
        if not self.access_token:
            return {"available_capital": 0.0, "margin_used": 0.0}
        try:
            with httpx.Client() as client:
                res = client.get(f"{self.base_url}/user/margins/equity", headers=self.headers, timeout=5.0)
                data = res.json().get("data", {})
                return {
                    "available_capital": float(data.get("available", {}).get("cash", 0.0)),
                    "margin_used": float(data.get("utilised", {}).get("debits", 0.0))
                }
        except Exception:
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
        side = "BUY" if "BUY" in direction.upper() else "SELL"
        payload = {
            "tradingsymbol": symbol,
            "exchange": "NFO",
            "transaction_type": side,
            "order_type": order_type,
            "quantity": quantity,
            "product": "MIS",
            "validity": "DAY",
            "tag": tag
        }
        try:
            with httpx.Client() as client:
                res = client.post(f"{self.base_url}/orders/regular", data=payload, headers=self.headers, timeout=5.0)
                data = res.json()
                return {
                    "order_id": data.get("data", {}).get("order_id", "MOCK_ZERODHA_ID"),
                    "status": "FILLED" if data.get("status") == "success" else "REJECTED",
                    "raw": data
                }
        except Exception as e:
            return {"order_id": "", "status": "ERROR", "error": str(e)}

    def modify_order(self, order_id: str, new_price: float, new_sl: float) -> bool:
        return True

    def cancel_order(self, order_id: str) -> bool:
        return True

    def square_off_position(self, symbol: str, quantity: int, price: float) -> Dict[str, Any]:
        return self.place_order(symbol, "SELL", quantity, price)

    def get_market_quote(self, symbol: str) -> float:
        return 0.0
