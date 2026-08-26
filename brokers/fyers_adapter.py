import os
import httpx
from typing import Dict, Any, Optional
from config.settings import settings
from brokers.base import BaseBroker

class FyersAdapter(BaseBroker):
    """
    Fyers API v3 Live Connector.
    Supports REST order execution, funds inquiry, and quote streaming.
    """

    def __init__(self, app_id: Optional[str] = None, access_token: Optional[str] = None):
        self.app_id = app_id or settings.FYERS_APP_ID
        self.access_token = access_token or settings.FYERS_ACCESS_TOKEN
        self.base_url = "https://api-t1.fyers.in/api/v3"
        self.headers = {
            "Authorization": f"{self.app_id}:{self.access_token}" if self.app_id and self.access_token else ""
        }

    def connect(self) -> bool:
        if not self.access_token:
            return False
        try:
            with httpx.Client() as client:
                res = client.get(f"{self.base_url}/profile", headers=self.headers, timeout=5.0)
                return res.status_code == 200 and res.json().get("s") == "ok"
        except Exception:
            return False

    def get_funds(self) -> Dict[str, float]:
        if not self.access_token:
            return {"available_capital": 0.0, "margin_used": 0.0}
        try:
            with httpx.Client() as client:
                res = client.get(f"{self.base_url}/funds", headers=self.headers, timeout=5.0)
                data = res.json()
                fund_limit = data.get("fund_limit", [{}])[0]
                return {
                    "available_capital": float(fund_limit.get("equityAmount", 0.0)),
                    "margin_used": float(fund_limit.get("utilisedAmount", 0.0))
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
        """
        Fyers API v3 Order Placement:
        side: 1 for BUY, -1 for SELL
        type: 1 for Limit, 2 for Market, 3 for SL-M, 4 for SL-L
        productType: 'INTRADAY' or 'MARGIN'
        """
        side = 1 if "BUY" in direction.upper() else -1
        fyers_type = 2 if order_type == "MARKET" else 1

        payload = {
            "symbol": symbol,
            "qty": quantity,
            "type": fyers_type,
            "side": side,
            "productType": "INTRADAY",
            "limitPrice": price if fyers_type == 1 else 0,
            "stopPrice": 0,
            "validity": "DAY",
            "offlineOrder": False,
            "orderTag": tag
        }

        try:
            with httpx.Client() as client:
                res = client.post(f"{self.base_url}/orders/sync", json=payload, headers=self.headers, timeout=5.0)
                data = res.json()
                return {
                    "order_id": data.get("id", "MOCK_FYERS_ID"),
                    "status": "FILLED" if data.get("s") == "ok" else "REJECTED",
                    "raw_response": data
                }
        except Exception as e:
            return {"order_id": "", "status": "ERROR", "error": str(e)}

    def modify_order(self, order_id: str, new_price: float, new_sl: float) -> bool:
        payload = {"id": order_id, "limitPrice": new_price, "stopPrice": new_sl}
        try:
            with httpx.Client() as client:
                res = client.put(f"{self.base_url}/orders/sync", json=payload, headers=self.headers, timeout=5.0)
                return res.json().get("s") == "ok"
        except Exception:
            return False

    def cancel_order(self, order_id: str) -> bool:
        try:
            with httpx.Client() as client:
                res = client.delete(f"{self.base_url}/orders/sync", json={"id": order_id}, headers=self.headers, timeout=5.0)
                return res.json().get("s") == "ok"
        except Exception:
            return False

    def square_off_position(self, symbol: str, quantity: int, price: float) -> Dict[str, Any]:
        return self.place_order(symbol, "SELL", quantity, price)

    def get_market_quote(self, symbol: str) -> float:
        try:
            with httpx.Client() as client:
                res = client.get(f"{self.base_url}/quotes?symbols={symbol}", headers=self.headers, timeout=5.0)
                data = res.json()
                return float(data.get("d", [{}])[0].get("v", {}).get("lp", 0.0))
        except Exception:
            return 0.0
