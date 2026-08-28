from datetime import datetime, date
from typing import Optional, Tuple, Dict, Any
from config.settings import settings
from core.models import Position, Signal, MarketRegime
from core.database import DatabaseLedger

class RiskManager:
    """
    Autonomous Risk Engine & Hard Circuit Breaker Guardrails:
    1. ₹1,000 Max Daily Loss Circuit Breaker
    2. Max 2 Closed Trades/Day
    3. Max 1 Open Position
    4. Strict 1 Lot Sizing
    5. Instant Trailing SL to Cost (+1 pt) at +15 pts profit
    6. 45-Minute Theta Decay Stagnation Auto-Exit
    """

    def __init__(self, db: Optional[DatabaseLedger] = None):
        self.db = db or DatabaseLedger(settings.DATABASE_PATH)
        self.current_capital: float = settings.STARTING_CAPITAL
        self.circuit_breaker_tripped: bool = False
        self.circuit_breaker_reason: str = ""
        self.get_current_capital()

    def get_current_capital(self) -> float:
        """Dynamically computes active capital from starting capital and realized ledger PnL."""
        try:
            trades = self.db.get_all_trades(limit=500)
            realized_pnl = sum(t.get("net_pnl", 0.0) for t in trades)
            self.current_capital = round(settings.STARTING_CAPITAL + realized_pnl, 2)
        except Exception:
            self.current_capital = settings.STARTING_CAPITAL
        return self.current_capital

    def evaluate_new_trade_permission(
        self,
        signal: Signal,
        active_position: Optional[Position],
        today_date: Optional[date] = None
    ) -> Tuple[bool, str]:
        """
        Evaluates whether a new trade signal is allowed to execute under institutional risk rules.
        """
        # Refresh current capital
        self.get_current_capital()

        # 1. Check Circuit Breaker Status
        if self.circuit_breaker_tripped:
            return False, f"CIRCUIT_BREAKER_ACTIVE: {self.circuit_breaker_reason}"

        # 2. Check Daily P&L & Trade Count from DB
        stats = self.db.get_today_stats(today_date)
        daily_net_pnl = stats["net_pnl"]
        daily_trades = stats["trade_count"]

        # Check ₹1,000 daily loss circuit breaker
        if daily_net_pnl <= -settings.MAX_DAILY_LOSS:
            self.circuit_breaker_tripped = True
            self.circuit_breaker_reason = f"Max Daily Loss limit reached (-₹{abs(daily_net_pnl):.2f} <= -₹{settings.MAX_DAILY_LOSS:.2f})"
            self.db.log_event("RISK_CIRCUIT_BREAKER", self.circuit_breaker_reason)
            return False, self.circuit_breaker_reason

        # Check Max 2 Trades Per Day
        if daily_trades >= settings.MAX_TRADES_PER_DAY:
            return False, f"MAX_DAILY_TRADES_REACHED: Already executed {daily_trades}/{settings.MAX_TRADES_PER_DAY} trades today."

        # Check Max 1 Open Position
        if active_position is not None:
            return False, f"POSITION_EXISTS: Active position {active_position.symbol} already open."

        # Check Capital Sufficiency
        required_margin = signal.entry_price * self.get_lot_size(signal.symbol)
        if self.current_capital < required_margin and settings.TRADING_MODE == "live":
            return False, f"INSUFFICIENT_CAPITAL: Need ₹{required_margin:.2f}, available ₹{self.current_capital:.2f}"

        # 3. Volatility Gating (ATR upper/lower limits)
        if hasattr(signal, 'atr') and signal.atr is not None:
            if signal.atr < 8.0:
                return False, f"VOLATILITY_TOO_LOW: ATR {signal.atr:.1f} pts is below 8.0 pt minimum (Choppy/Untradable)"
            if signal.atr > 85.0:
                return False, f"VOLATILITY_TOO_HIGH: ATR {signal.atr:.1f} pts exceeds 85.0 pt maximum (Abnormal Tail Risk)"

        # 4. Time Window Discovery & Cutoff Filter
        trade_time = signal.timestamp.time() if hasattr(signal, 'timestamp') and signal.timestamp else datetime.now().time()
        if trade_time < datetime.strptime("09:30:00", "%H:%M:%S").time():
            return False, "TIME_WINDOW_BLOCKED: Opening 15-min discovery period (09:15-09:30 AM). Trades resume at 09:30 AM."
        if trade_time >= datetime.strptime("15:15:00", "%H:%M:%S").time():
            return False, "TIME_WINDOW_BLOCKED: Intraday square-off cutoff (after 03:15 PM). No new positions permitted."

        return True, "APPROVED"

    def calculate_volatility_adjusted_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        account_capital: Optional[float] = None,
        risk_pct: float = 0.02
    ) -> int:
        """
        Calculates position size using the volatility-adjusted formula:
        Position Size = (Account Capital * Risk %) / (Entry Price - Stop Loss Price)
        """
        capital = account_capital or self.get_current_capital()
        risk_amount = capital * risk_pct
        stop_distance = abs(entry_price - stop_loss_price)

        if stop_distance <= 0:
            return settings.NIFTY_LOT_SIZE

        raw_shares = risk_amount / stop_distance
        lot_size = settings.NIFTY_LOT_SIZE
        calculated_lots = max(1, round(raw_shares / lot_size))
        return calculated_lots * lot_size

    def get_lot_size(self, symbol: str) -> int:
        sym_upper = symbol.upper()
        if "BANK" in sym_upper:
            return settings.BANKNIFTY_LOT_SIZE * settings.POSITION_SIZE_LOTS
        elif "SENSEX" in sym_upper:
            return settings.SENSEX_LOT_SIZE * settings.POSITION_SIZE_LOTS
        elif "NIFTY" in sym_upper:
            return settings.NIFTY_LOT_SIZE * settings.POSITION_SIZE_LOTS
        else:
            return 10  # Default equity lot/quantity

    def update_position_risk(
        self,
        position: Position,
        current_price: float,
        current_time: datetime
    ) -> Tuple[Optional[str], float]:
        """
        Evaluates active position for:
        1. Target Hit
        2. Stop Loss Hit
        3. Trailing SL Adjustment (+15 pts profit -> SL to Cost + 1 pt)
        4. 45-Minute Stagnation Auto-Exit
        5. Daily Loss Intraday Circuit Breaker

        Returns: (exit_reason or None, updated_sl_price)
        """
        position.current_price = current_price
        position.last_update_time = current_time

        # Calculate point difference based on direction
        pts_gain = current_price - position.entry_price
        position.unrealized_pnl = pts_gain * position.quantity

        if pts_gain > position.max_favorable_excursion:
            position.max_favorable_excursion = pts_gain

        # Check 1: Target Reached
        if current_price >= position.target:
            return "TARGET_HIT", position.stop_loss

        # Check 2: Stop Loss Reached
        if current_price <= position.stop_loss:
            return "STOP_LOSS_HIT", position.stop_loss

        # Check 3: Instant Trailing Stop Loss Rule
        # "Instant Trailing SL to Cost (+1 pt) at +15 pts profit"
        if pts_gain >= settings.TRAILING_TRIGGER_PTS and not position.trailing_activated:
            position.trailing_activated = True
            new_sl = position.entry_price + settings.TRAILING_COST_OFFSET_PTS
            if new_sl > position.stop_loss:
                position.stop_loss = new_sl
                self.db.log_event(
                    "TRAILING_SL_ACTIVATED",
                    f"Locked in profit for {position.symbol}. Stop Loss moved to Cost+1 ({new_sl:.2f})"
                )

        # Check 4: 45-Minute Stagnation Auto-Exit Rule (Time Decay Shield)
        duration_minutes = (current_time - position.entry_time).total_seconds() / 60.0
        if duration_minutes >= settings.STAGNATION_EXIT_MINUTES and pts_gain < 5.0:
            return "STAGNATION_EXIT_45M", position.stop_loss

        # Check 5: Live Unrealized Daily Loss Breaker
        today_stats = self.db.get_today_stats()
        combined_pnl = today_stats["net_pnl"] + position.unrealized_pnl
        if combined_pnl <= -settings.MAX_DAILY_LOSS:
            self.circuit_breaker_tripped = True
            self.circuit_breaker_reason = f"Combined daily loss breached limit (-₹{abs(combined_pnl):.2f})"
            return "CIRCUIT_BREAKER_TRIGGERED", position.stop_loss

        return None, position.stop_loss

    def reset_daily_limits(self):
        """Called at start of each trading day (09:00 AM)"""
        self.circuit_breaker_tripped = False
        self.circuit_breaker_reason = ""
