import sys
import os
import argparse
import asyncio
from datetime import datetime, time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from config.settings import settings
from services.engine import QuantExecutionEngine
from services.data_feed import MarketDataFeed
from brokers.fyers_adapter import FyersAdapter
from brokers.paper_broker import PaperBroker

async def main():
    parser = argparse.ArgumentParser(description="Anil Babu Trades Live / Paper Trading Execution Engine")
    parser.add_argument("--mode", type=str, choices=["paper", "live"], default="paper", help="Execution mode: paper or live")
    parser.add_argument("--symbol", type=str, default="NIFTY", help="Target Index / Asset (NIFTY, BANKNIFTY, SENSEX)")
    parser.add_argument("--interval", type=int, default=5, help="Candle interval in minutes")
    parser.add_argument("--iterations", type=int, default=15, help="Number of simulated candles to process (for paper mode)")
    args = parser.parse_args()

    print("=" * 70)
    print("      ANIL BABU TRADES ALGO TRADING SYSTEM — LIVE DESK RUNNER       ")
    print(f"      Mode: {args.mode.upper()} | Target Asset: {args.symbol} | Port: 8000")
    print("=" * 70)

    # Initialize broker and engine
    broker = PaperBroker() if args.mode == "paper" else FyersAdapter()
    engine = QuantExecutionEngine(mode=args.mode, broker=broker)
    data_feed = MarketDataFeed(symbol=args.symbol)

    print(f"\n[INIT] Starting Capital: ₹{settings.STARTING_CAPITAL:,.2f}")
    print(f"[INIT] Risk Guardrails: Max Daily Loss ₹{settings.MAX_DAILY_LOSS} | Max {settings.MAX_TRADES_PER_DAY} Trades/Day | Strict 1 Lot")
    print(f"[INIT] Telegram Desks: VIP Signals (-5117093594) | Macro Desk (-5484599984)")
    print(f"[INIT] Connected Broker: {'Paper Trading Engine (Realistic Slippage)' if args.mode == 'paper' else 'Fyers API v3 (Live)'}\n")

    # Generate initial market session data
    print("[FEED] Initializing 5-minute candle historical buffer...")
    candles_df = data_feed.generate_synthetic_session(n_candles=30, base_price=24500.0)

    # Main execution loop
    print(f"[ENGINE] Starting automated market scanner for {args.symbol}...\n")
    for i in range(args.iterations):
        step_time = datetime.now()
        last_close = candles_df['close'].iloc[-1]
        
        # Synthetic incremental candle
        drift = 14.5 if i == 5 else (1.5 if i % 2 == 0 else -1.0)
        new_close = round(last_close + drift, 2)
        new_high = max(last_close, new_close) + 4.0
        new_low = min(last_close, new_close) - 3.0
        vol = 48000 if i == 5 else 18000

        data_feed.append_candle(
            timestamp=step_time,
            open_=last_close,
            high=new_high,
            low=new_low,
            close=new_close,
            volume=vol
        )

        candles_df = data_feed.candles_df
        result = await engine.process_market_update(candles_df, symbol=args.symbol)

        status = engine.get_system_status()
        pos_str = f"{engine.active_position.symbol} (P&L: ₹{engine.active_position.unrealized_pnl:+.2f})" if engine.active_position else "NO OPEN POSITION"

        print(f"[{step_time.strftime('%H:%M:%S')}] Step {i+1:02d} | LTP: {new_close:,.2f} | Regime: {status.active_regime.value:<16} | Status: {result.get('action', 'IDLE'):<18} | Position: {pos_str}")

        await asyncio.sleep(1.0)  # Brief pause between simulated candles

    # Session close summary
    print("\n" + "=" * 70)
    print("                     3:30 PM SESSION COMPLETED                    ")
    today_stats = engine.db.get_today_stats()
    print(f"Total Trades: {today_stats['trade_count']} | Wins: {today_stats['win_count']} | Net Realized P&L: ₹{today_stats['net_pnl']:+.2f}")
    print(f"Ending Capital: ₹{broker.get_funds()['available_capital']:,.2f}")
    print(f"Permanent Audit Log: {settings.AUDIT_LOG_CSV}")
    print("=" * 70 + "\n")

    # Dispatch 3:30 PM summary to Telegram Desk 1
    await engine.telegram.broadcast_daily_summary(today_stats, broker.get_funds()['available_capital'])

if __name__ == "__main__":
    asyncio.run(main())
