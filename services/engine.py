import asyncio
import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Callable
import pandas as pd
from config.settings import settings
from core.models import Signal, Position, TradeRecord, MarketRegime, StrategyType, SignalDirection, SystemStatus
from core.risk_manager import RiskManager
from core.database import DatabaseLedger
from core.tax_calculator import IndianTaxCalculator
from brokers.base import BaseBroker
from brokers.paper_broker import PaperBroker
from brokers.fyers_adapter import FyersAdapter
from services.telegram_service import TelegramNotifier
from strategies.volatility_squeeze import VolatilitySqueezeStrategy
from strategies.orb_vwap_sniper import ORBVWAPSniperStrategy
from strategies.cash_mean_reversion import CashMeanReversionStrategy
from strategies.market_regime import MarketRegimeClassifier

class QuantExecutionEngine:
    """
    Master Autonomous Execution Orchestrator:
    - Combines 3 Quantitative Strategies + Market Microstructure Regime
    - Enforces Strict Risk Guardrails (Circuit Breaker ₹1,000, Max 2 Trades, 1 Lot)
    - Routes Orders to Paper or Live Brokers
    - Broadcasts Real-Time VIP Signals & Macro Digests to Telegram
    - Updates SQLite Ledger & WebSocket Live Clients
    """

    def __init__(self, mode: str = "paper", broker: Optional[BaseBroker] = None):
        self.mode = mode
        self.db = DatabaseLedger(settings.DATABASE_PATH)
        self.risk_manager = RiskManager(self.db)
        self.telegram = TelegramNotifier()
        self.broker = broker or (PaperBroker(self.db) if mode == "paper" else FyersAdapter())
        self.broker.connect()

        # Quantitative Strategies
        self.strat_squeeze = VolatilitySqueezeStrategy()
        self.strat_orb = ORBVWAPSniperStrategy()
        self.strat_cash = CashMeanReversionStrategy()

        # Engine State
        self.active_position: Optional[Position] = None
        self.current_regime: MarketRegime = MarketRegime.UNKNOWN
        self.regime_info: Dict[str, Any] = {}
        self.last_candle_time: Optional[datetime] = None
        self.ws_subscribers: List[Callable[[Dict[str, Any]], Any]] = []

    def register_ws_listener(self, callback: Callable[[Dict[str, Any]], Any]):
        self.ws_subscribers.append(callback)

    async def _notify_ws(self, event_type: str, data: Dict[str, Any]):
        msg = {"type": event_type, "data": data, "timestamp": datetime.now().isoformat()}
        for cb in self.ws_subscribers:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(msg)
                else:
                    cb(msg)
            except Exception:
                pass

    async def process_market_update(self, df: pd.DataFrame, symbol: str = "NIFTY", simulated_option_ltp: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Main tick/candle processing loop triggered on each 5-min candle update.
        """
        if df.empty or len(df) < 20:
            return None

        current_candle = df.iloc[-1]
        candle_time = current_candle['timestamp'] if 'timestamp' in current_candle else datetime.now()
        index_close = float(current_candle['close'])
        self.last_candle_time = candle_time

        # 1. Classify Market Regime & Microstructure
        prev_day_close = float(df['close'].iloc[0])  # Or previous day reference
        self.regime_info = MarketRegimeClassifier.classify_regime(df, prev_day_close)
        self.current_regime = self.regime_info["regime"]

        # 2. Monitor & Update Active Position (if any)
        if self.active_position is not None:
            # Check real broker quote first if available
            if simulated_option_ltp is not None:
                current_opt_price = simulated_option_ltp
            else:
                real_quote = None
                try:
                    real_quote = self.broker.get_market_quote(self.active_position.symbol)
                except Exception:
                    real_quote = None

                if real_quote and real_quote > 0:
                    current_opt_price = real_quote
                else:
                    # Realistic Delta approximation based on underlying index move from position entry
                    base_underlying = self.active_position.underlying_entry_price if self.active_position.underlying_entry_price > 0 else index_close
                    spot_delta = (index_close - base_underlying) if "CE" in self.active_position.symbol else (base_underlying - index_close)
                    current_opt_price = max(round(self.active_position.entry_price + (spot_delta * 0.50), 2), 0.05)

            # Evaluate Risk & Trailing Rules
            exit_reason, new_sl = self.risk_manager.update_position_risk(
                self.active_position, current_opt_price, candle_time
            )

            # Check if trailing SL was newly hit
            if self.active_position.trailing_activated and new_sl > self.active_position.original_stop_loss:
                await self.telegram.broadcast_trailing_sl_hit(self.active_position, current_opt_price)

            # If exit condition met -> Close position
            if exit_reason:
                trade_record = self._execute_position_close(current_opt_price, candle_time, exit_reason)
                await self.telegram.broadcast_trade_exit(trade_record)
                await self._notify_ws("TRADE_CLOSED", trade_record.model_dump(mode="json"))
                return {"action": "POSITION_CLOSED", "trade": trade_record}

            await self._notify_ws("POSITION_UPDATE", self.active_position.model_dump(mode="json"))
            return {"action": "POSITION_HELD", "position": self.active_position}

        # 3. If No Active Position -> Evaluate Strategies
        # Check Choppy / Sideways Defense Mode
        if self.current_regime == MarketRegime.CHOPPY_SIDEWAYS:
            self.db.log_event("SNIPER_DEFENSE", "Choppy sideways trap detected. Staying 100% in cash.")
            return {"action": "DEFENSE_MODE_HOLD", "reason": self.regime_info["description"]}

        # Strategy 1: Volatility Squeeze Breakout
        signal = self.strat_squeeze.generate_signal(df, symbol)

        # Strategy 2: ORB + VWAP Sniper (if Strategy 1 gave no signal)
        if signal is None:
            signal = self.strat_orb.generate_signal(df, symbol)

        # Strategy 3: Cash Mean Reversion (if cash equity symbol)
        if signal is None and symbol not in ["NIFTY", "BANKNIFTY", "SENSEX"]:
            signal = self.strat_cash.generate_signal(df, symbol)

        # 4. If Signal Generated -> Run Risk Permission Checks
        if signal is not None:
            # Check regime directional filter
            if signal.direction == SignalDirection.BUY_CE and not self.regime_info.get("allow_ce", True):
                self.db.log_event("SIGNAL_BLOCKED", "CE Buy signal blocked by Bearish Regime filter.")
                return {"action": "SIGNAL_BLOCKED", "reason": "Regime Filter Block"}

            if signal.direction == SignalDirection.BUY_PE and not self.regime_info.get("allow_pe", True):
                self.db.log_event("SIGNAL_BLOCKED", "PE Buy signal blocked by Bullish Regime filter.")
                return {"action": "SIGNAL_BLOCKED", "reason": "Regime Filter Block"}

            # Risk Guardrails Check
            allowed, risk_reason = self.risk_manager.evaluate_new_trade_permission(
                signal, self.active_position, candle_time.date()
            )

            if not allowed:
                self.db.log_event("TRADE_REJECTED", f"Risk manager rejected signal: {risk_reason}")
                return {"action": "TRADE_REJECTED", "reason": risk_reason}

            # 5. Execute Order Entry
            qty = self.risk_manager.get_lot_size(signal.symbol)
            order_res = self.broker.place_order(
                symbol=signal.symbol,
                direction="BUY",
                quantity=qty,
                price=signal.entry_price,
                order_type="MARKET"
            )

            fill_price = order_res.get("fill_price", signal.entry_price)
            pos_id = f"POS_{uuid.uuid4().hex[:8].upper()}"

            self.active_position = Position(
                id=pos_id,
                symbol=signal.symbol,
                strategy=signal.strategy,
                direction=signal.direction,
                quantity=qty,
                entry_price=fill_price,
                underlying_entry_price=signal.index_price or index_close,
                current_price=fill_price,
                stop_loss=signal.stop_loss,
                original_stop_loss=signal.stop_loss,
                target=signal.target,
                entry_time=candle_time,
                last_update_time=candle_time,
                broker="PAPER" if self.mode == "paper" else "LIVE_FYERS"
            )

            # Broadcast to Telegram Desk 1 (VIP Signals)
            await self.telegram.broadcast_trade_entry(signal, qty, order_res.get("order_id", "ORD_001"))
            await self._notify_ws("POSITION_OPENED", self.active_position.model_dump(mode="json"))

            return {"action": "POSITION_OPENED", "position": self.active_position, "order": order_res}

        return {"action": "SCANNING", "regime": self.current_regime}

    def _execute_position_close(self, exit_price: float, exit_time: datetime, exit_reason: str) -> TradeRecord:
        if isinstance(self.broker, PaperBroker):
            trade_record = self.broker.close_position(self.active_position, exit_price, exit_time, exit_reason)
        else:
            # Live broker square off
            self.broker.square_off_position(self.active_position.symbol, self.active_position.quantity, exit_price)
            
            # Accurate Indian Tax & Charges Calculation
            calc = IndianTaxCalculator.calculate_option_trade_costs(
                buy_price=self.active_position.entry_price,
                sell_price=exit_price,
                quantity=self.active_position.quantity
            )
            charges = calc.total_tax_and_charges
            gross_pnl = round((exit_price - self.active_position.entry_price) * self.active_position.quantity, 2)
            net_pnl = round(gross_pnl - charges, 2)

            trade_record = TradeRecord(
                id=self.active_position.id,
                symbol=self.active_position.symbol,
                strategy=self.active_position.strategy,
                direction=self.active_position.direction,
                quantity=self.active_position.quantity,
                entry_time=self.active_position.entry_time,
                exit_time=exit_time,
                entry_price=self.active_position.entry_price,
                exit_price=exit_price,
                exit_reason=exit_reason,
                gross_pnl=gross_pnl,
                charges=charges,
                net_pnl=net_pnl,
                duration_minutes=max(round((exit_time - self.active_position.entry_time).total_seconds() / 60.0, 1), 1.0),
                broker="LIVE_FYERS"
            )
            self.db.record_trade(trade_record)

        self.active_position = None
        return trade_record

    async def emergency_square_off(self, reason: str = "MANUAL_EMERGENCY_OVERRIDE") -> Optional[TradeRecord]:
        """Instant square-off of all active positions (Circuit breaker / panic button)."""
        if self.active_position is None:
            return None

        exit_price = self.active_position.current_price
        exit_time = datetime.now()
        trade_record = self._execute_position_close(exit_price, exit_time, reason)
        await self.telegram.broadcast_trade_exit(trade_record)
        await self._notify_ws("EMERGENCY_SQUAREOFF", trade_record.model_dump(mode="json"))
        return trade_record

    def get_system_status(self) -> SystemStatus:
        stats = self.db.get_today_stats()
        current_cap = self.broker.capital if isinstance(self.broker, PaperBroker) else settings.STARTING_CAPITAL

        return SystemStatus(
            trading_mode=self.mode.upper(),
            active_regime=self.current_regime,
            current_capital=round(current_cap, 2),
            starting_capital=settings.STARTING_CAPITAL,
            today_realized_pnl=round(stats.get("net_pnl", 0.0), 2),
            today_unrealized_pnl=round(self.active_position.unrealized_pnl, 2) if self.active_position else 0.0,
            today_trade_count=stats.get("trade_count", 0),
            max_trades_per_day=settings.MAX_TRADES_PER_DAY,
            circuit_breaker_tripped=self.risk_manager.circuit_breaker_tripped,
            open_positions_count=1 if self.active_position else 0,
            bot_connected=True,
            last_tick_time=self.last_candle_time
        )
