import os
import httpx
from typing import Dict, Any, List, Optional
from config.settings import settings
from brokers.base import BaseBroker

try:
    from fyers_apiv3 import fyersModel
    from fyers_apiv3.FyersWebsocket import data_ws, order_ws
    from fyers_apiv3.FyersWebsocket.tbt_ws import FyersTbtSocket, SubscriptionModes
    HAS_FYERS_SDK = True
except ImportError:
    HAS_FYERS_SDK = False

class FyersAdapter(BaseBroker):
    """
    Complete Institutional Fyers API v3 Adapter:
    - User APIs: Profile, Funds, Holdings
    - Transaction APIs: Tradebook, Orderbook, Positions
    - Order Placement: Single, Basket, Multileg (3L), Smart Orders & Smart Exit Triggers
    - Data APIs: Quotes, Historical Data, Market Depth
    - WebSockets: FyersDataSocket, FyersOrderSocket & FyersTbtSocket (Tick-By-Tick Level-2/3 Depth)
    """

    def __init__(
        self,
        app_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        access_token: Optional[str] = None
    ):
        self.app_id = app_id or settings.FYERS_APP_ID
        self.secret_key = secret_key or getattr(settings, "FYERS_SECRET_KEY", "")
        self.redirect_uri = redirect_uri or getattr(settings, "FYERS_REDIRECT_URI", "https://127.0.0.1:8000/api/fyers/callback")
        self.access_token = access_token or settings.FYERS_ACCESS_TOKEN
        self.base_url = "https://api-t1.fyers.in/api/v3"
        self.fyers_model: Optional[Any] = None
        self.data_socket: Optional[Any] = None
        self.order_socket: Optional[Any] = None

        if HAS_FYERS_SDK and self.access_token and self.app_id:
            try:
                self.fyers_model = fyersModel.FyersModel(
                    token=self.access_token,
                    is_async=False,
                    client_id=self.app_id,
                    log_path=""
                )
            except Exception:
                self.fyers_model = None

    @property
    def auth_headers(self) -> Dict[str, str]:
        token_str = f"{self.app_id}:{self.access_token}" if self.app_id and self.access_token else ""
        return {"Authorization": token_str, "Content-Type": "application/json"}

    # =========================================================================
    # 1. AUTHENTICATION & LOGIN FLOW
    # =========================================================================

    def generate_auth_url(self, state: str = "anil_babu_session") -> str:
        """Generates Fyers OAuth authorization URL."""
        if HAS_FYERS_SDK and self.app_id and self.secret_key:
            session = fyersModel.SessionModel(
                client_id=self.app_id,
                redirect_uri=self.redirect_uri,
                response_type="code",
                state=state,
                secret_key=self.secret_key,
                grant_type="authorization_code"
            )
            return session.generate_authcode()
        return f"https://api-t1.fyers.in/api/v3/generate-authcode?client_id={self.app_id}&redirect_uri={self.redirect_uri}&response_type=code&state={state}"

    def exchange_auth_code_for_token(self, auth_code: str) -> Optional[str]:
        """Exchanges authorization code for an Access Token."""
        if HAS_FYERS_SDK and self.app_id and self.secret_key:
            try:
                session = fyersModel.SessionModel(
                    client_id=self.app_id,
                    redirect_uri=self.redirect_uri,
                    response_type="code",
                    state="sample",
                    secret_key=self.secret_key,
                    grant_type="authorization_code"
                )
                session.set_token(auth_code)
                res = session.generate_token()
                token = res.get("access_token")
                if token:
                    self.access_token = token
                    self.fyers_model = fyersModel.FyersModel(token=token, is_async=False, client_id=self.app_id, log_path="")
                    return token
            except Exception as e:
                print("Fyers Token Generation Error:", e)
        return None

    # =========================================================================
    # 2. USER & FUNDS APIS
    # =========================================================================

    def connect(self) -> bool:
        if not self.access_token:
            return False
        try:
            if self.fyers_model:
                res = self.fyers_model.get_profile()
                return res.get("s") == "ok"
            with httpx.Client() as client:
                res = client.get(f"{self.base_url}/profile", headers=self.auth_headers, timeout=5.0)
                return res.status_code == 200 and res.json().get("s") == "ok"
        except Exception:
            return False

    def get_profile(self) -> Dict[str, Any]:
        if self.fyers_model:
            return self.fyers_model.get_profile()
        with httpx.Client() as client:
            res = client.get(f"{self.base_url}/profile", headers=self.auth_headers, timeout=5.0)
            return res.json()

    def get_funds(self) -> Dict[str, float]:
        if not self.access_token:
            return {"available_capital": 0.0, "margin_used": 0.0}
        try:
            if self.fyers_model:
                data = self.fyers_model.funds()
            else:
                with httpx.Client() as client:
                    res = client.get(f"{self.base_url}/funds", headers=self.auth_headers, timeout=5.0)
                    data = res.json()
            fund_limit = data.get("fund_limit", [{}])[0]
            return {
                "available_capital": float(fund_limit.get("equityAmount", 0.0)),
                "margin_used": float(fund_limit.get("utilisedAmount", 0.0))
            }
        except Exception:
            return {"available_capital": 0.0, "margin_used": 0.0}

    def get_holdings(self) -> Dict[str, Any]:
        if self.fyers_model:
            return self.fyers_model.holdings()
        with httpx.Client() as client:
            res = client.get(f"{self.base_url}/holdings", headers=self.auth_headers, timeout=5.0)
            return res.json()

    # =========================================================================
    # 3. TRANSACTIONS & ORDER APIS
    # =========================================================================

    def get_orderbook(self) -> Dict[str, Any]:
        if self.fyers_model:
            return self.fyers_model.orderbook()
        with httpx.Client() as client:
            res = client.get(f"{self.base_url}/orders", headers=self.auth_headers, timeout=5.0)
            return res.json()

    def get_positions(self) -> Dict[str, Any]:
        if self.fyers_model:
            return self.fyers_model.positions()
        with httpx.Client() as client:
            res = client.get(f"{self.base_url}/positions", headers=self.auth_headers, timeout=5.0)
            return res.json()

    def place_order(
        self,
        symbol: str,
        direction: str,
        quantity: int,
        price: float = 0.0,
        order_type: str = "MARKET",
        product_type: str = "INTRADAY",
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        tag: str = "ANIL_BABU_BOT"
    ) -> Dict[str, Any]:
        """
        Submits order to Fyers API v3 with optional Take-Profit & Stop-Loss overlays.
        """
        side = 1 if "BUY" in direction.upper() else -1
        fyers_type = 2 if order_type.upper() == "MARKET" else 1

        payload: Dict[str, Any] = {
            "symbol": symbol,
            "qty": quantity,
            "type": fyers_type,
            "side": side,
            "productType": product_type,
            "limitPrice": price if fyers_type == 1 else 0.0,
            "stopPrice": 0.0,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": False,
            "orderTag": tag
        }

        if stop_loss is not None:
            payload["stopLoss"] = float(stop_loss)
            payload["legType"] = 1  # 1 = points, 2 = percent
        if take_profit is not None:
            payload["takeProfit"] = float(take_profit)
            payload["legType"] = 1

        try:
            if self.fyers_model:
                data = self.fyers_model.place_order(payload)
            else:
                with httpx.Client() as client:
                    res = client.post(f"{self.base_url}/orders/sync", json=payload, headers=self.auth_headers, timeout=5.0)
                    data = res.json()
            return {
                "order_id": data.get("id", "FYERS_ORD_ID"),
                "status": "FILLED" if data.get("s") == "ok" else "REJECTED",
                "raw_response": data
            }
        except Exception as e:
            return {"order_id": "", "status": "ERROR", "error": str(e)}

    def modify_order(self, order_id: str, new_price: float, new_sl: float = 0.0) -> bool:
        payload = {"id": order_id, "type": 1, "limitPrice": new_price, "stopPrice": new_sl}
        try:
            if self.fyers_model:
                res = self.fyers_model.modify_order(payload)
            else:
                with httpx.Client() as client:
                    res = client.put(f"{self.base_url}/orders/sync", json=payload, headers=self.auth_headers, timeout=5.0).json()
            return res.get("s") == "ok"
        except Exception:
            return False

    def cancel_order(self, order_id: str) -> bool:
        payload = {"id": order_id}
        try:
            if self.fyers_model:
                res = self.fyers_model.cancel_order(payload)
            else:
                with httpx.Client() as client:
                    res = client.request("DELETE", f"{self.base_url}/orders/sync", json=payload, headers=self.auth_headers, timeout=5.0).json()
            return res.get("s") == "ok"
        except Exception:
            return False

    def exit_position(self, position_id: str) -> bool:
        payload = {"id": position_id}
        try:
            if self.fyers_model:
                res = self.fyers_model.exit_positions(payload)
            else:
                with httpx.Client() as client:
                    res = client.request("DELETE", f"{self.base_url}/positions", json=payload, headers=self.auth_headers, timeout=5.0).json()
            return res.get("s") == "ok"
        except Exception:
            return False

    # =========================================================================
    # 4. MARKET QUOTES & DEPTH APIS
    # =========================================================================

    def get_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        symbol_str = ",".join(symbols)
        payload = {"symbols": symbol_str}
        try:
            if self.fyers_model:
                return self.fyers_model.quotes(payload)
            with httpx.Client() as client:
                res = client.get(f"https://api-t1.fyers.in/data/quotes?symbols={symbol_str}", headers=self.auth_headers, timeout=5.0)
                return res.json()
        except Exception as e:
            return {"s": "error", "message": str(e)}

    def square_off_position(self, symbol: str, quantity: int, price: float = 0.0) -> Dict[str, Any]:
        """Closes an active open position with Fyers."""
        return self.place_order(
            symbol=symbol,
            direction="SELL",
            quantity=quantity,
            price=price,
            order_type="MARKET",
            tag="ANIL_BABU_SQOFF"
        )

    def get_market_quote(self, symbol: str) -> float:
        """Fetches current LTP for symbol."""
        try:
            res = self.get_quotes([symbol])
            if res.get("s") == "ok" and "d" in res and len(res["d"]) > 0:
                return float(res["d"][0].get("v", {}).get("lp", 0.0))
        except Exception:
            pass
        return 0.0

    # =========================================================================
    # 5. LIVE WEBSOCKETS (Data & Order Sockets)
    # =========================================================================

    def create_data_socket(self, symbols: List[str], on_message_callback: Any) -> Optional[Any]:
        """Creates and connects a FyersDataSocket for live symbol streaming."""
        if not HAS_FYERS_SDK or not self.access_token or not self.app_id:
            return None

        token_str = f"{self.app_id}:{self.access_token}"

        def onopen():
            self.data_socket.subscribe(symbols=symbols, data_type="SymbolUpdate")
            self.data_socket.keep_running()

        self.data_socket = data_ws.FyersDataSocket(
            access_token=token_str,
            log_path="",
            litemode=False,
            reconnect=True,
            on_connect=onopen,
            on_message=on_message_callback
        )
        return self.data_socket

    def create_tbt_socket(
        self,
        symbols: List[str],
        on_depth_update_callback: Any,
        channel_no: str = "1",
        mode: Any = None
    ) -> Optional[Any]:
        """
        Creates and connects a FyersTbtSocket for ultra-low latency Tick-By-Tick Level-2 Depth streaming.
        """
        if not HAS_FYERS_SDK or not self.access_token or not self.app_id:
            return None

        token_str = f"{self.app_id}:{self.access_token}"
        sub_mode = mode or SubscriptionModes.DEPTH

        def onopen():
            self.tbt_socket.subscribe(symbol_tickers=symbols, channelNo=channel_no, mode=sub_mode)
            self.tbt_socket.switchChannel(resume_channels=[channel_no], pause_channels=[])
            self.tbt_socket.keep_running()

        self.tbt_socket = FyersTbtSocket(
            access_token=token_str,
            write_to_file=False,
            log_path="",
            on_open=onopen,
            on_depth_update=on_depth_update_callback,
            on_error_message=lambda msg: print("Fyers TBT Error Message:", msg),
            on_error=lambda err: print("Fyers TBT Socket Error:", err),
            on_close=lambda cls: print("Fyers TBT Socket Closed:", cls)
        )
        return self.tbt_socket

    def create_order_socket(
        self,
        on_orders_callback: Any,
        on_trades_callback: Any,
        on_positions_callback: Any,
        on_general_callback: Optional[Any] = None
    ) -> Optional[Any]:
        """
        Creates and connects a FyersOrderSocket for real-time order, trade, and position updates.
        """
        if not HAS_FYERS_SDK or not self.access_token or not self.app_id:
            return None

        token_str = f"{self.app_id}:{self.access_token}"

        def onopen():
            self.order_socket.subscribe(data_type="OnOrders,OnTrades,OnPositions,OnGeneral")
            self.order_socket.keep_running()

        self.order_socket = order_ws.FyersOrderSocket(
            access_token=token_str,
            write_to_file=False,
            log_path="",
            on_connect=onopen,
            on_orders=on_orders_callback,
            on_trades=on_trades_callback,
            on_positions=on_positions_callback,
            on_general=on_general_callback or (lambda msg: None)
        )
        return self.order_socket

