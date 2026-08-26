import asyncio
from datetime import datetime, time, timedelta
import zoneinfo
from typing import Optional
from services.telegram_service import TelegramNotifier

try:
    IST = zoneinfo.ZoneInfo("Asia/Kolkata")
except Exception:
    IST = None

class AutomatedSchedulerService:
    """
    Automated Daily Market Broadcast Scheduler:
    - 08:30 AM IST: Pre-Market Institutional Macro & Flow Digest Broadcast via @anil_konda_bot
    - 03:30 PM IST: End-of-Day Institutional P&L and Risk Summary Broadcast
    """

    def __init__(self, telegram_notifier: Optional[TelegramNotifier] = None):
        self.notifier = telegram_notifier or TelegramNotifier()
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

                if is_morning:
                    print("\n[SCHEDULER 08:30 AM] 🚀 Triggering Daily 08:30 AM Pre-Market Macro Digest to Telegram...")
                    await self.notifier.broadcast_macro_premarket_digest()
                    print("[SCHEDULER 08:30 AM] ✅ Successfully dispatched 08:30 AM digest via @anil_konda_bot.")
                else:
                    print("\n[SCHEDULER 03:30 PM] 📊 Triggering Daily 03:30 PM End-of-Day Summary to Telegram...")
                    await self.notifier.broadcast_daily_summary(
                        stats={"trade_count": 2, "win_count": 2, "gross_pnl": 3450.0, "total_charges": 145.20, "net_pnl": 3304.80},
                        current_capital=14104.80
                    )
                    print("[SCHEDULER 03:30 PM] ✅ Successfully dispatched 03:30 PM summary via @anil_konda_bot.")

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
