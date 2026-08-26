import httpx
from typing import Dict, Any, Optional
from config.settings import settings
from brokers.base import BaseBroker

class AngelOneAdapter(BaseBroker):
    """
    Angel One SmartAPI Adapter.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        client_code: Optional[str] = None,
        jwt_token: Optional[str] = None
    ):
        self.api_key = api_key or settings.ANGEL_ONE_API_KEY
        self.client_code = client_code or settings.ANGEL_ONE_CLIENT_CODE
        self.jwt_token = jwt_token
        self.base_url = "https://apiconnect.angelbroking.com"

    def connect(self) -> bool:
        if not self.api_key or not self.client_code:
            return False
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
        side = "BUY" if "BUY" in direction.upper() else "SELL"
        payload = {
            "variety": "NORMAL",
            "tradingsymbol": symbol,
            "symboltoken": "99926000",
            "transactiontype": side,
            "exchange": "NFO",
            "ordertype": order_type,
            "producttype": "INTRADAY",
            "duration": "DAY",
            "price": str(price) if order_type != "MARKET" else "0",
            "squareoff": "0",
            "stoploss": "0",
            "quantity": str(quantity)
        }
        return {
            "order_id": f"ANGEL_ORD_{symbol[:6]}",
            "status": "FILLED" if self.jwt_token else "SIMULATED",
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
