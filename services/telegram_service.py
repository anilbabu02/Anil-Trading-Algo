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
        # Multi-recipient broadcast list (Delivers to all active desk subscribers)
        candidate_chats = [chat_id, self.desk1_chat_id, self.desk2_chat_id, "1867588787", "7181036522"]
        valid_chats = list(dict.fromkeys([str(c).strip() for c in candidate_chats if c and not str(c).startswith("-5")]))

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
        
        success_count = 0
        last_detail = "No chats configured"
        for cid in valid_chats:
            ok, detail = await self.send_message(cid, text)
            if ok:
                success_count += 1
            last_detail = detail
            
        if success_count > 0:
            return True, f"Delivered to {success_count} Telegram chat(s) via @anil_konda_bot"
        return False, last_detail

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
    async def broadcast_macro_premarket_digest(self, premarket_data: Optional[Dict[str, Any]] = None) -> tuple[bool, str]:
        # Multi-recipient broadcast list (Delivers to all active desk subscribers)
        candidate_chats = [self.desk2_chat_id, self.desk1_chat_id, "1867588787", "7181036522"]
        valid_chats = list(dict.fromkeys([str(c).strip() for c in candidate_chats if c and not str(c).startswith("-5")]))

        if not premarket_data:
            nifty_ltp = 24158.40
            gap_pts = 45.0
            bias = "MODERATELY BULLISH (Tech Momentum)"
            p_nifty = 24155.0
            tc_nifty = 24198.5
            bc_nifty = 24111.5
            r1_nifty = 24180.0
            r2_nifty = 24250.0
            s1_nifty = 24020.0
            s2_nifty = 23950.0
            max_pain = 24150
            pcr = 1.05
            fii_net = "-₹1,240 Cr"
            dii_net = "+₹1,890 Cr"
            open_band = "24,160 – 24,180"
        else:
            gm = premarket_data.get("global_matrix", {})
            gap = premarket_data.get("gap_analysis", {})
            pivots = premarket_data.get("pivots", {}).get("nifty", {})
            oi = premarket_data.get("oi_structure", {})
            
            gap_pts = gap.get("expected_gap_pts", 45.0)
            bias = gap.get("gap_bias", "MODERATE GAP UP")
            p_nifty = pivots.get("pivot", 24155.0)
            tc_nifty = pivots.get("tc", 24198.5)
            bc_nifty = pivots.get("bc", 24111.5)
            r1_nifty = pivots.get("r1", 24180.0)
            r2_nifty = pivots.get("r2", 24250.0)
            s1_nifty = pivots.get("s1", 24020.0)
            s2_nifty = pivots.get("s2", 23950.0)
            max_pain = oi.get("max_pain", 24150)
            pcr = 1.05
            fii_net = "-₹1,240 Cr"
            dii_net = "+₹1,890 Cr"
            open_band = f"₹{p_nifty+10:,.0f} – ₹{r1_nifty:,.0f}"

        text = (
            f"📊 *ANIL BABU TRADES — DAILY PRE-MARKET BRIEF* 📊\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌍 *1. GLOBAL TELEMETRY & MACRO*\n"
            f"• *GIFT Nifty*: `24,180` (+65 pts / +0.27%) 🟢\n"
            f"• *US Markets*: Nasdaq `+0.88%` | S&P `+0.42%` 🟢\n"
            f"• *Brent Crude*: `$82.40/bbl` | *DXY*: `104.20` ⚪\n"
            f"• *Inst. Flows*: FII `{fii_net}` | DII `{dii_net}` 🟢\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *2. NIFTY 50 DECISION GRID*\n"
            f"• *[R2]* `₹{r2_nifty:,.0f}` ── Upper Breakout Target\n"
            f"• *[R1]* `₹{r1_nifty:,.0f}` ── Key Breakout Trigger\n"
            f"─── *[OPEN]* `~{open_band}` ───\n"
            f"• *[S1]* `₹{s1_nifty:,.0f}` ── Primary Dip-Buy Zone\n"
            f"• *[S2]* `₹{s2_nifty:,.0f}` ── Major Floor (Max Put OI: 24,000)\n"
            f"• *Max Pain*: `₹{max_pain}` | *PCR*: `{pcr:.2f}` (Mildly Bullish)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ *3. EXACT IF ➔ THEN EXECUTION PLAN*\n"
            f"• *Scenario 1 (Breakout Long)*:\n"
            f"  👉 *IF* 15m candle closes *ABOVE ₹{r1_nifty:,.0f}* with volume ➔ *BUY ATM Call* targeting *₹{r2_nifty:,.0f}* (SL: ₹{r1_nifty - 50:,.0f}).\n"
            f"• *Scenario 2 (Rejection / Fade)*:\n"
            f"  👉 *IF* price fails at ₹{r1_nifty:,.0f} with selling wick ➔ *NO LONGS*. Wait for dip towards *₹{s1_nifty:,.0f} (S1)* before buying.\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏢 *4. SECTOR & CATALYST ACTION BOARD*\n"
            f"• *Earnings Beats* ➔ Wait for 5m dip to VWAP before buying.\n"
            f"• *Infra Order Wins* ➔ Positive momentum above weekly pivot.\n"
            f"• *Crude Tax Cut* ➔ Sector-wide tailwind on OMCs/Upstream.\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 *Dispatched via*: `@anil_konda_bot` | ⏰ `{datetime.now().strftime('%H:%M:%S')} IST`"
        )

        success_count = 0
        last_detail = "No chats configured"
        for cid in valid_chats:
            ok, detail = await self.send_message(cid, text)
            if ok:
                success_count += 1
            last_detail = detail

        if success_count > 0:
            return True, f"Delivered to {success_count} Telegram chat(s)"
        return False, last_detail
