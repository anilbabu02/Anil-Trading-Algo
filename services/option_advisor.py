from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

class OptionAdvisorService:
    """
    Quant Option Suggestion Calls Desk:
    - Provides high-conviction algorithmic option trading recommendations
    - Real-time tracking of Entry, LTP, Stop Loss, Target 1, Target 2, Trailing Status, and Greeks
    - Supports 1-Click execution routing directly to the Anil Babu Trades broker engine
    """

    def __init__(self):
        self.suggestions: List[Dict[str, Any]] = [
            {
                "id": "OPT_CALL_01",
                "symbol": "NIFTY 24600 CE",
                "underlying": "NIFTY 50",
                "expiry": "Current Weekly (28-Aug-2026)",
                "strike": 24600,
                "option_type": "CE",
                "action": "BUY",
                "strategy": "Volatility Squeeze Breakout",
                "entry_price": 120.00,
                "current_ltp": 138.50,
                "stop_loss": 105.00,
                "target_1": 155.00,
                "target_2": 180.00,
                "points_pnl": 18.50,
                "pnl_percent": 15.42,
                "risk_reward": "1:2.8",
                "status": "TRAILING_LOCKED",  # ACTIVE | TRAILING_LOCKED | TARGET_HIT | CLOSED
                "trailing_sl": 121.00,
                "lot_size": 65,
                "confidence": 88,
                "delta": 0.54,
                "theta": -11.20,
                "iv": 13.8,
                "timestamp": (datetime.now() - timedelta(minutes=18)).strftime("%H:%M:%S"),
                "reason": "20-period BB compressed inside Keltner Channel with RVOL 1.45x breakout surge above VWAP."
            },
            {
                "id": "OPT_CALL_02",
                "symbol": "BANKNIFTY 52800 CE",
                "underlying": "BANK NIFTY",
                "expiry": "Current Weekly (27-Aug-2026)",
                "strike": 52800,
                "option_type": "CE",
                "action": "BUY",
                "strategy": "15-Min ORB + VWAP Sniper",
                "entry_price": 285.00,
                "current_ltp": 318.00,
                "stop_loss": 255.00,
                "target_1": 360.00,
                "target_2": 410.00,
                "points_pnl": 33.00,
                "pnl_percent": 11.58,
                "risk_reward": "1:2.6",
                "status": "ACTIVE",
                "trailing_sl": 255.00,
                "lot_size": 30,
                "confidence": 84,
                "delta": 0.52,
                "theta": -24.50,
                "iv": 15.2,
                "timestamp": (datetime.now() - timedelta(minutes=35)).strftime("%H:%M:%S"),
                "reason": "Clean 15-min Opening Range Breakout (48 pt range) trading firmly above intraday VWAP."
            },
            {
                "id": "OPT_CALL_03",
                "symbol": "SENSEX 81200 CE",
                "underlying": "BSE SENSEX",
                "expiry": "Current Weekly (29-Aug-2026)",
                "strike": 81200,
                "option_type": "CE",
                "action": "BUY",
                "strategy": "Volatility Squeeze Expansion",
                "entry_price": 210.00,
                "current_ltp": 258.00,
                "stop_loss": 185.00,
                "target_1": 275.00,
                "target_2": 320.00,
                "points_pnl": 48.00,
                "pnl_percent": 22.86,
                "risk_reward": "1:2.8",
                "status": "TARGET_1_REACHED",
                "trailing_sl": 211.00,
                "lot_size": 10,
                "confidence": 91,
                "delta": 0.56,
                "theta": -18.00,
                "iv": 14.1,
                "timestamp": (datetime.now() - timedelta(minutes=55)).strftime("%H:%M:%S"),
                "reason": "Institutional order-flow momentum + FII index long buildup."
            }
        ]

    def get_all_suggestions(self) -> List[Dict[str, Any]]:
        return self.suggestions

    def get_active_suggestions(self) -> List[Dict[str, Any]]:
        return [s for s in self.suggestions if s["status"] in ["ACTIVE", "TRAILING_LOCKED", "TARGET_1_REACHED"]]

    def add_suggestion(self, suggestion_data: Dict[str, Any]) -> Dict[str, Any]:
        self.suggestions.insert(0, suggestion_data)
        return suggestion_data
