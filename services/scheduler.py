import asyncio
from datetime import datetime, time, timedelta
import zoneinfo
from typing import Optional
from services.telegram_service import TelegramNotifier

from core.database import DatabaseLedger
from config.settings import settings

try:
    IST = zoneinfo.ZoneInfo("Asia/Kolkata")
except Exception:
    IST = None

class AutomatedSchedulerService:
    """
    Automated Daily Market Broadcast Scheduler:
    - 08:30 AM IST: Pre-Market Institutional Macro & Flow Digest Broadcast
    - 03:30 PM IST: End-of-Day Verified P&L and Risk Summary Broadcast
    """

    def __init__(self, telegram_notifier: Optional[TelegramNotifier] = None, db: Optional[DatabaseLedger] = None):
        self.notifier = telegram_notifier or TelegramNotifier()
        self.db = db or DatabaseLedger(settings.DATABASE_PATH)
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._scheduler_loop())
            print("[SCHEDULER] ⏰ Automated Daily 08:30 AM & 03:30 PM Telegram Broadcast Engine Active.")

    def stop(self):
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()

    def get_seconds_until_target(self, target_hour: int, target_minute: int) -> float:
        now = datetime.now(IST) if IST else datetime.now()
        target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return (target - now).total_seconds()

    async def _scheduler_loop(self):
        while self.is_running:
            try:
                # Calculate sleep duration to next 08:30 AM IST
                secs_to_830 = self.get_seconds_until_target(8, 30)
                secs_to_1530 = self.get_seconds_until_target(15, 30)

                # Next event is whichever is smaller
                next_sleep = min(secs_to_830, secs_to_1530)
                is_morning = next_sleep == secs_to_830

                # Sleep until target time
                await asyncio.sleep(next_sleep)

                now = datetime.now(IST) if IST else datetime.now()
                # Only broadcast on weekdays (Monday=0 to Friday=4)
                if now.weekday() < 5:
                    if is_morning:
                        print("\n[SCHEDULER 08:30 AM] 🚀 Triggering Daily 08:30 AM Pre-Market Macro Digest to Telegram...")
                        await self.notifier.broadcast_macro_premarket_digest()
                        print("[SCHEDULER 08:30 AM] ✅ Successfully dispatched 08:30 AM digest.")
                    else:
                        print("\n[SCHEDULER 03:30 PM] 📊 Triggering Verified End-of-Day Summary to Telegram...")
                        # Query real database ledger
                        today_str = now.strftime("%Y-%m-%d")
                        trades = []
                        if self.db:
                            try:
                                trades = self.db.get_trades_by_date(today_str)
                            except Exception:
                                trades = []

                        trade_count = len(trades)
                        win_count = sum(1 for t in trades if getattr(t, 'net_pnl', 0) > 0)
                        gross_pnl = sum(getattr(t, 'gross_pnl', 0.0) for t in trades)
                        total_charges = sum(getattr(t, 'charges', 0.0) for t in trades)
                        net_pnl = sum(getattr(t, 'net_pnl', 0.0) for t in trades)
                        current_capital = round(settings.STARTING_CAPITAL + net_pnl, 2)

                        stats = {
                            "trade_count": trade_count,
                            "win_count": win_count,
                            "gross_pnl": round(gross_pnl, 2),
                            "total_charges": round(total_charges, 2),
                            "net_pnl": round(net_pnl, 2)
                        }

                        await self.notifier.broadcast_daily_summary(
                            stats=stats,
                            current_capital=current_capital
                        )
                        print("[SCHEDULER 03:30 PM] ✅ Successfully dispatched verified daily summary.")

                # Small delay to prevent immediate re-trigger in same minute
                await asyncio.sleep(65)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[SCHEDULER ERROR] {e}")
                await asyncio.sleep(60)

    def get_schedule_status(self) -> dict:
        secs_830 = self.get_seconds_until_target(8, 30)
        hours = int(secs_830 // 3600)
        mins = int((secs_830 % 3600) // 60)
        return {
            "status": "ACTIVE",
            "daily_morning_time": "08:30:00 AM IST",
            "daily_closing_time": "03:30:00 PM IST",
            "next_morning_digest_in": f"{hours}h {mins}m",
            "bot_handle": "@anil_konda_bot"
        }
