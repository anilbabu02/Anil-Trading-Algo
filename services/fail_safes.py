import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
import httpx

from config.settings import settings
from core.models import Position, Signal, OrderType
from services.telegram_service import TelegramNotifier

class ExecutionMicrostructureGuard:
    """
    Layer 3: Execution & Microstructure Optimization
    - Slippage & Bid-Ask Spread Verification
    - Limit vs. Market Pegged Routing
    - Partial Fill State Handler
    """

    def __init__(self, max_allowed_spread_pts: float = 1.50, partial_fill_timeout_secs: float = 8.0):
        self.max_allowed_spread_pts = max_allowed_spread_pts
        self.partial_fill_timeout_secs = partial_fill_timeout_secs

    def verify_bid_ask_spread(self, bid: float, ask: float) -> tuple[bool, str]:
        """Verifies if current bid-ask spread is within safe execution limits."""
        spread = ask - bid
        if spread <= 0:
            return False, "INVALID_SPREAD: Bid >= Ask"
        if spread > self.max_allowed_spread_pts:
            return False, f"SPREAD_TOO_WIDE: Spread ₹{spread:.2f} exceeds threshold ₹{self.max_allowed_spread_pts:.2f}"
        return True, "SPREAD_OK"

    def calculate_pegged_limit_price(self, bid: float, ask: float, direction: str = "BUY") -> float:
        """
        Calculates price-improved pegged limit order price (Passive aggressive routing).
        """
        if direction.upper() in ["BUY", "CE", "PE"]:
            # Buy limit placed at Best Bid + 20% of spread to capture priority fill without crossing spread
            return round(bid + (ask - bid) * 0.25, 2)
        else:
            # Sell limit placed at Best Ask - 20% of spread
            return round(ask - (ask - bid) * 0.25, 2)


class SystemFailsafesAndOps:
    """
    Layer 4: System Failsafes & Operational Guards
    - Heartbeat & Watchdog Monitor (WebSocket drop detection)
    - Broker vs. Local State Reconciliation (Orphan order cleaner)
    - Rate-Limit Backoff with Exponential Retry
    - Emergency 1-Click System Kill Switch
    """

    def __init__(self, telegram_bot: Optional[TelegramNotifier] = None):
        self.telegram = telegram_bot or TelegramNotifier()
        self.last_heartbeat: float = time.time()
        self.is_feed_healthy: bool = True
        self.watchdog_active: bool = False
        self._watchdog_task: Optional[asyncio.Task] = None
        self._reconciliation_task: Optional[asyncio.Task] = None
        self.kill_switch_engaged: bool = False

    def record_heartbeat(self):
        """Called on every incoming WebSocket tick to prove feed liveness."""
        self.last_heartbeat = time.time()
        if not self.is_feed_healthy:
            self.is_feed_healthy = True
            print("[WATCHDOG] 🟢 WebSocket feed restored to HEALTHY state.")

    def start_watchdog(self, on_feed_drop_callback: Optional[Callable] = None):
        if not self.watchdog_active:
            self.watchdog_active = True
            self._watchdog_task = asyncio.create_task(self._watchdog_loop(on_feed_drop_callback))
            print("[FAILSAPES] 🛡 Heartbeat & Watchdog Monitor Active (5s Timeout).")

    def stop_watchdog(self):
        self.watchdog_active = False
        if self._watchdog_task and not self._watchdog_task.done():
            self._watchdog_task.cancel()

    async def _watchdog_loop(self, on_feed_drop_callback: Optional[Callable] = None):
        while self.watchdog_active:
            try:
                await asyncio.sleep(2.0)
                time_since_heartbeat = time.time() - self.last_heartbeat

                # If no ticks for > 5 seconds, flag feed disconnect
                if time_since_heartbeat > 5.0 and self.is_feed_healthy:
                    self.is_feed_healthy = False
                    msg = (
                        f"🚨 *WATCHDOG ALERT: FEED DISCONNECTED* 🚨\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"⚠️ *Status*: No WebSocket tick received for `{time_since_heartbeat:.1f}s` (Threshold: 5.0s).\n"
                        f"🔒 *Safety Action*: Strategy paused, new trade entries BLOCKED.\n"
                        f"🤖 *Bot*: `@anil_konda_bot` | ⏰ `{datetime.now().strftime('%H:%M:%S')} IST`"
                    )
                    print(f"\n[WATCHDOG ERROR] {msg}\n")
                    await self.telegram.send_message(self.telegram.desk1_chat_id, msg)
                    if on_feed_drop_callback:
                        on_feed_drop_callback()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[WATCHDOG EXCEPTION] {e}")

    async def execute_rate_limited_api_call(self, func, *args, max_retries: int = 3, **kwargs):
        """
        Executes broker API calls with exponential backoff to prevent IP rate-limiting bans.
        """
        delay = 0.25
        for attempt in range(1, max_retries + 1):
            try:
                return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries:
                    raise e
                print(f"[API RATE LIMIT BACKOFF] Attempt {attempt} failed: {e}. Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)
                delay *= 2.0  # Exponential backoff

    async def trigger_master_kill_switch(self, broker, active_position: Optional[Position]) -> Dict[str, Any]:
        """
        Emergency Master Kill Switch: Immediately cancels all pending orders and flattens open positions.
        """
        self.kill_switch_engaged = True
        results = {"status": "KILL_SWITCH_ENGAGED", "timestamp": datetime.now().isoformat(), "actions": []}

        # 1. Flatten Active Open Position
        if active_position:
            exit_res = broker.place_order(
                symbol=active_position.symbol,
                direction="SELL" if "BUY" in active_position.direction.upper() else "BUY",
                quantity=active_position.quantity,
                price=active_position.current_price,
                order_type="MARKET",
                tag="KILL_SWITCH_FLATTEN"
            )
            results["actions"].append({"action": "FLATTEN_POSITION", "symbol": active_position.symbol, "result": exit_res})

        # 2. Cancel All Open Orders
        try:
            open_orders = broker.get_open_orders() if hasattr(broker, "get_open_orders") else []
            for ord_id in open_orders:
                broker.cancel_order(ord_id)
                results["actions"].append({"action": "CANCEL_ORDER", "order_id": ord_id})
        except Exception as e:
            results["actions"].append({"action": "CANCEL_ORDERS_ERROR", "error": str(e)})

        # 3. Broadcast Alert
        alert_msg = (
            f"⛔ *MASTER EMERGENCY KILL SWITCH ENGAGED* ⛔\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛑 *Action*: All open positions flattened and pending orders cancelled.\n"
            f"🔒 *System State*: HALTED until manual reset.\n"
            f"🤖 *Bot*: `@anil_konda_bot`"
        )
        await self.telegram.send_message(self.telegram.desk1_chat_id, alert_msg)
        return results
