import os
import csv
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from config.settings import settings
from core.models import Signal, Position, TradeRecord, StrategyType, SignalDirection
from core.tax_calculator import IndianTaxCalculator
from core.database import DatabaseLedger
from brokers.base import BaseBroker

class PaperBroker(BaseBroker):
    """
    High-Fidelity Paper Trading Broker Engine:
    - Real-time simulation with realistic slippage
    - Tracks starting capital (₹10,800.00)
    - Records trades permanently to SQLite Ledger and logs/paper_trading_results.csv
    - Full statutory Indian tax deduction modeling
    """

    def __init__(self, db: Optional[DatabaseLedger] = None, csv_path: Optional[str] = None):
        self.db = db or DatabaseLedger(settings.DATABASE_PATH)
        self.csv_path = Path(csv_path or settings.AUDIT_LOG_CSV)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.capital = settings.STARTING_CAPITAL
        self.active_position: Optional[Position] = None
        self._init_csv()

    def _init_csv(self):
        if not self.csv_path.exists():
            with open(self.csv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Trade_ID", "Timestamp", "Symbol", "Strategy", "Direction",
                    "Quantity", "Entry_Price", "Exit_Price", "Duration_Mins",
                    "Exit_Reason", "Gross_PnL", "Charges_Taxes", "Net_PnL",
                    "Compounded_Capital", "Broker"
                ])

    def connect(self) -> bool:
        self.db.log_event("BROKER_CONNECT", "Paper Trading Engine initialized and connected.")
        return True

    def get_funds(self) -> Dict[str, float]:
        return {
            "available_capital": round(self.capital, 2),
            "starting_capital": settings.STARTING_CAPITAL,
            "margin_used": (self.active_position.entry_price * self.active_position.quantity) if self.active_position else 0.0
        }

    def place_order(
        self,
        symbol: str,
        direction: str,
        quantity: int,
        price: float,
        order_type: str = "MARKET",
        tag: str = "ANIL_BABU_BOT"
    ) -> Dict[str, Any]:
        # Realistic execution slippage (0.25 to 0.50 pts for index options)
        slippage = 0.35 if "CE" in symbol or "PE" in symbol else 0.10
        fill_price = round(price + (slippage if "BUY" in direction else -slippage), 2)
        order_id = f"PAPER_ORD_{uuid.uuid4().hex[:8].upper()}"

        self.db.log_event("ORDER_FILLED", f"Filled {direction} {quantity}x {symbol} @ ₹{fill_price} (Slip: ₹{slippage})", {
            "order_id": order_id,
            "symbol": symbol,
            "fill_price": fill_price,
            "quantity": quantity
        })

        return {
            "order_id": order_id,
            "status": "FILLED",
            "symbol": symbol,
            "direction": direction,
            "quantity": quantity,
            "fill_price": fill_price,
            "timestamp": datetime.now().isoformat()
        }

    def modify_order(self, order_id: str, new_price: float, new_sl: float) -> bool:
        self.db.log_event("ORDER_MODIFIED", f"Modified order {order_id} SL to ₹{new_sl:.2f}")
        return True

    def cancel_order(self, order_id: str) -> bool:
        self.db.log_event("ORDER_CANCELLED", f"Cancelled order {order_id}")
        return True

    def square_off_position(self, symbol: str, quantity: int, price: float) -> Dict[str, Any]:
        return self.place_order(symbol, "SELL", quantity, price)

    def close_position(self, position: Position, exit_price: float, exit_time: datetime, exit_reason: str) -> TradeRecord:
        # Calculate taxes and net profit
        is_option = ("CE" in position.symbol) or ("PE" in position.symbol)
        if is_option:
            costs = IndianTaxCalculator.calculate_option_costs(
                buy_price=position.entry_price,
                sell_price=exit_price,
                quantity=position.quantity,
                brokerage_per_order=20.0
            )
        else:
            costs = IndianTaxCalculator.calculate_equity_costs(
                buy_price=position.entry_price,
                sell_price=exit_price,
                quantity=position.quantity,
                brokerage_per_order=20.0
            )

        duration_mins = max(round((exit_time - position.entry_time).total_seconds() / 60.0, 1), 1.0)
        self.capital += costs["net_pnl"]

        trade_record = TradeRecord(
            id=position.id,
            symbol=position.symbol,
            strategy=position.strategy,
            direction=position.direction,
            quantity=position.quantity,
            entry_time=position.entry_time,
            exit_time=exit_time,
            entry_price=position.entry_price,
            exit_price=exit_price,
            exit_reason=exit_reason,
            gross_pnl=costs["gross_pnl"],
            charges=costs["total_charges"],
            net_pnl=costs["net_pnl"],
            duration_minutes=duration_mins,
            broker="PAPER"
        )

        # Write to SQLite Database
        self.db.record_trade(trade_record)

        # Append to CSV audit log
        with open(self.csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                trade_record.id,
                exit_time.strftime("%Y-%m-%d %H:%M:%S"),
                trade_record.symbol,
                trade_record.strategy.value if hasattr(trade_record.strategy, "value") else str(trade_record.strategy),
                trade_record.direction.value if hasattr(trade_record.direction, "value") else str(trade_record.direction),
                trade_record.quantity,
                f"{trade_record.entry_price:.2f}",
                f"{trade_record.exit_price:.2f}",
                trade_record.duration_minutes,
                trade_record.exit_reason,
                f"{trade_record.gross_pnl:.2f}",
                f"{trade_record.charges:.2f}",
                f"{trade_record.net_pnl:.2f}",
                f"{self.capital:.2f}",
                trade_record.broker
            ])

        self.active_position = None
        return trade_record

    def get_market_quote(self, symbol: str) -> float:
        return 120.0  # Simulated default
