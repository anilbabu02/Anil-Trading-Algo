from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from core.models import Signal, Position, TradeRecord

class BaseBroker(ABC):
    """
    Unified Abstract Interface for Broker Execution Desks.
    Ensures identical order signatures for Fyers, Kotak Neo, Zerodha, Angel One, and Paper Engine.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Authenticate and establish session with the broker."""
        pass

    @abstractmethod
    def get_funds(self) -> Dict[str, float]:
        """Fetch available margin and balance."""
        pass

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        direction: str,
        quantity: int,
        price: float,
        order_type: str = "MARKET",
        tag: str = "ANIL_BABU_BOT"
    ) -> Dict[str, Any]:
        """Place an order with the broker."""
        pass

    @abstractmethod
    def modify_order(self, order_id: str, new_price: float, new_sl: float) -> bool:
        """Modify open stop loss or limit orders."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        pass

    @abstractmethod
    def square_off_position(self, symbol: str, quantity: int, price: float) -> Dict[str, Any]:
        """Close an active open position."""
        pass

    @abstractmethod
    def get_market_quote(self, symbol: str) -> float:
        """Fetch current LTP for symbol."""
        pass
