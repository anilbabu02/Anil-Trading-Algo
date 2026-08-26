import sys
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from services.telegram_service import TelegramNotifier

async def main():
    print("Synthesizing 08:30 AM Pre-Market Institutional Macro & Flow Digest...")
    notifier = TelegramNotifier()
    await notifier.broadcast_macro_premarket_digest()
    print("Successfully broadcasted to Telegram Desk 2 (AB_Market_Analysis | Chat ID -5484599984).")

if __name__ == "__main__":
    asyncio.run(main())
