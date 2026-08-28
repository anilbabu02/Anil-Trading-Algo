import asyncio
import sys
import httpx
from datetime import datetime
from typing import Optional, Dict, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from config.settings import settings
from core.models import Signal, Position, TradeRecord

class TelegramNotifier:
    """
    Dual-Desk Telegram Architecture (@abTradeBot):
    - Desk 1: Trading Signals Desk (AB_Trades | Chat ID -5117093594)
    - Desk 2: Macro & News Desk (AB_Market_Analysis | Chat ID -5484599984)
    """

    def __init__(
        self,
        token: Optional[str] = None,
        desk1_chat_id: Optional[str] = None,
        desk2_chat_id: Optional[str] = None
    ):
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.desk1_chat_id = desk1_chat_id or settings.TELEGRAM_DESK_1_CHAT_ID
        self.desk2_chat_id = desk2_chat_id or settings.TELEGRAM_DESK_2_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    async def send_message(self, chat_id: str, text: str) -> tuple[bool, str]:
        """Sends markdown formatted Telegram alert. Returns (success_bool, status_message)."""
        if not self.token or self.token == "MOCK_TELEGRAM_TOKEN":
            print(f"\n[TELEGRAM DISPATCH -> {chat_id}]\n{text}\n" + "-"*50)
            return True, "Simulated dispatch (Mock token)"

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{self.base_url}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True
                    },
                    timeout=6.0
                )
                if res.status_code == 200:
                    return True, "Message delivered successfully to Telegram."
                else:
                    data = res.json()
                    err_desc = data.get("description", "Unknown Telegram error")
                    print(f"[TELEGRAM ERROR {res.status_code}] {err_desc}")
                    return False, f"Telegram Error {res.status_code}: {err_desc}"
        except Exception as e:
            print(f"[TELEGRAM EXCEPTION] Failed to send message: {e}")
            return False, str(e)

    # ------------------ DESK 1: VIP TRADING SIGNALS ------------------ #
    async def broadcast_trade_entry(self, signal: Signal, qty: int, order_id: str):
        text = (
            f"⚡ *ANIL BABU TRADES VIP SIGNAL* ⚡\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *Strategy*: `{signal.strategy.value}`\n"
            f"📈 *Action*: `{'BUY ' + (signal.option_type or 'EQUITY')}`\n"
            f"🏷 *Symbol*: `{signal.symbol}`\n"
            f"📊 *Index LTP*: `{signal.index_price}`\n"
            f"💵 *Entry Range*: `₹{signal.entry_price:.2f}`\n"
            f"🛑 *Hard SL*: `₹{signal.stop_loss:.2f}`\n"
            f"🎯 *Target*: `₹{signal.target:.2f}` (1:2.8 R:R)\n"
            f"📦 *Position Size*: `{qty} Qty (Strict 1 Lot)`\n"
            f"⚡ *RVOL*: `{signal.rvol:.2f}x` | *ADX*: `{signal.adx:.1f}`\n"
            f"🛡 *Trailing Rule*: Instant SL to Cost (+1 pt) at +15 pts\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱ *Time*: `{signal.timestamp.strftime('%H:%M:%S')}` | Order ID: `{order_id}`"
        )
        await self.send_message(self.desk1_chat_id, text)

    async def broadcast_trailing_sl_hit(self, position: Position, current_price: float):
        text = (
            f"🛡 *TRAILING STOP LOSS ACTIVATED* 🛡\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷 *Symbol*: `{position.symbol}`\n"
            f"📈 *Current Premium*: `₹{current_price:.2f}` (+{current_price - position.entry_price:.1f} pts)\n"
            f"🔒 *New Stop Loss*: `₹{position.stop_loss:.2f}` (Cost + 1 pt)\n"
            f"💰 *Capital Status*: Risk completely eliminated! Position is now risk-free."
        )
        await self.send_message(self.desk1_chat_id, text)

    async def broadcast_trade_exit(self, trade: TradeRecord):
        emoji = "🎉" if trade.net_pnl > 0 else "🛑"
        text = (
            f"{emoji} *TRADE CLOSED — {trade.exit_reason}* {emoji}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷 *Symbol*: `{trade.symbol}`\n"
            f"🎯 *Strategy*: `{trade.strategy.value}`\n"
            f"💵 *Entry*: `₹{trade.entry_price:.2f}` ➔ *Exit*: `₹{trade.exit_price:.2f}`\n"
            f"⏱ *Duration*: `{trade.duration_minutes:.1f} Mins`\n"
            f"📦 *Quantity*: `{trade.quantity}`\n"
            f"💰 *Gross P&L*: `₹{trade.gross_pnl:+.2f}`\n"
            f"🧾 *Statutory Taxes/Brokerage*: `₹{trade.charges:.2f}`\n"
            f"💎 *Net Realized P&L*: `₹{trade.net_pnl:+.2f}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ *Closed At*: `{trade.exit_time.strftime('%H:%M:%S')}`"
        )
        await self.send_message(self.desk1_chat_id, text)

    async def broadcast_daily_summary(self, stats: Dict[str, Any], current_capital: float):
        net_pnl = stats.get("net_pnl", 0.0)
        trades = stats.get("trade_count", 0)
        wins = stats.get("win_count", 0)
        win_rate = (wins / trades * 100) if trades > 0 else 0.0

        text = (
            f"📊 *3:30 PM ANIL BABU TRADES INSTITUTIONAL DAILY SUMMARY* 📊\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 *Date*: `{stats.get('date', datetime.now().strftime('%Y-%m-%d'))}`\n"
            f"💼 *Total Closed Trades*: `{trades}`\n"
            f"🏆 *Win / Loss*: `{wins}W / {trades - wins}L` ({win_rate:.1f}% Win Rate)\n"
            f"💰 *Gross Realized P&L*: `₹{stats.get('gross_pnl', 0.0):+.2f}`\n"
            f"🧾 *Total Statutory Charges*: `₹{stats.get('total_charges', 0.0):.2f}`\n"
            f"💎 *Net Compounded P&L*: `₹{net_pnl:+.2f}`\n"
            f"🏦 *Closing Account Capital*: `₹{current_capital:,.2f}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔒 *Risk Protocol*: 100% Cash overnight (Zero Theta decay risk)."
        )
        await self.send_message(self.desk1_chat_id, text)

    # ------------------ DEDICATED OPTION RECOMMENDATION BROADCAST ------------------ #
    async def broadcast_option_recommendation(self, item: Dict[str, Any], chat_id: Optional[str] = None) -> tuple[bool, str]:
        target_chat = chat_id or self.desk1_chat_id
        is_ce = item.get("option_type") == "CE"
        emoji = "🟢" if is_ce else "🔴"
        action = item.get("action", "BUY")
        reason_clean = str(item.get("reason", "Institutional momentum & VWAP breakout")).replace("_", "-").replace("*", "")

        text = (
            f"⚡ *ANIL BABU TRADES — VIP OPTION CALL* ⚡\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{emoji} *Recommendation*: `{action} {item.get('symbol')}`\n"
            f"🎯 *Strategy*: `{item.get('strategy', 'Volatility Squeeze Breakout')}`\n"
            f"📅 *Expiry*: `{item.get('expiry', 'Current Weekly')}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 *Buy Range*: `₹{item.get('entry_price', 0):.2f}`\n"
            f"🛑 *Hard Stop Loss*: `₹{item.get('stop_loss', 0):.2f}`\n"
            f"🎯 *Target 1*: `₹{item.get('target_1', 0):.2f}` ({item.get('risk_reward', '1:2.8')} R:R)\n"
            f"🚀 *Target 2*: `₹{item.get('target_2', 0):.2f}` (Runner)\n"
            f"📦 *Position Size*: `{item.get('lot_size', 65)} Qty (1 Lot Strict)`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Greeks*: Delta `{item.get('delta', 0.54)}` | Theta `{item.get('theta', -12.0)}`\n"
            f"💡 *Rationale*: {reason_clean}\n"
            f"🛡 *Trailing Rule*: Move SL to Cost (+1 pt) at +15 pts profit\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 *Dispatched via*: `@anil_konda_bot` | ⏰ `{datetime.now().strftime('%H:%M:%S')} IST`"
        )
        return await self.send_message(target_chat, text)

    # ------------------ DEDICATED TRADE NEWS BROADCAST ------------------ #
    async def broadcast_news_bulletin(self, item: Dict[str, Any], chat_id: Optional[str] = None) -> bool:
        target_chat = chat_id or self.desk2_chat_id
        sentiment = item.get("sentiment", "NEUTRAL")
        sent_emoji = "🟢 BULLISH" if sentiment == "BULLISH" else ("🔴 BEARISH" if sentiment == "BEARISH" else "⚪ NEUTRAL")
        impact = item.get("impact", "MEDIUM")
        impact_badge = "🔥 HIGH IMPACT" if impact == "HIGH" else "⚡ MARKET UPDATE"

        text = (
            f"📰 *ANIL BABU TRADES — MARKET WIRE* 📰\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷 *Category*: `[{item.get('category', 'INDICES')}]` | {impact_badge}\n"
            f"📈 *Sentiment*: *{sent_emoji}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📢 *Headline*:\n*{item.get('headline')}*\n\n"
            f"📝 *Institutional Summary*:\n{item.get('summary')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 *Source*: `{item.get('source', 'Institutional Desk')}`\n"
            f"🤖 *Dispatched via*: `@anil_konda_bot` | ⏰ `{item.get('timestamp', datetime.now().strftime('%H:%M:%S'))} IST`"
        )
        return await self.send_message(target_chat, text)

    # ------------------ DESK 2: MACRO & NEWS DESK ------------------ #
    async def broadcast_macro_premarket_digest(self, macro_data: Optional[Dict[str, Any]] = None):
        data = macro_data or {
            "gift_nifty": "+48 pts (24,860.00)",
            "sp500": "+0.45% (5,980.20)",
            "crude_oil": "$74.20 (-0.8%)",
            "fii_cash": "-₹420.50 Cr",
            "dii_cash": "+₹1,180.20 Cr",
            "fii_index_futures": "+3,450 Contracts (Net Long: 58%)",
            "market_bias": "MODERATELY BULLISH ON PULLBACKS"
        }

        text = (
            f"🌐 *08:30 AM INSTITUTIONAL MACRO & FLOW DIGEST* 🌐\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌏 *GIFT Nifty*: `{data['gift_nifty']}`\n"
            f"🇺🇸 *S&P 500*: `{data['sp500']}`\n"
            f"🛢 *Brent Crude*: `{data['crude_oil']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏦 *INSTITUTIONAL ORDER FLOW*:\n"
            f"• *FII Cash*: `{data['fii_cash']}`\n"
            f"• *DII Cash*: `{data['dii_cash']}`\n"
            f"• *FII Index Futures*: `{data['fii_index_futures']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *Daily Synthesized Bias*: *{data['market_bias']}*\n"
            f"🛡 *Execution Plan*: Wait for 9:15-9:30 AM Opening Range & Squeeze Compression."
        )
        await self.send_message(self.desk2_chat_id, text)
