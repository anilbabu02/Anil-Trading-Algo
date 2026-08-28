from datetime import datetime, timedelta
import random
from typing import List, Dict, Any

class NewsService:
    """
    Real-Time Institutional Market Wire & News Engine:
    - Provides real-time trade news, RBI macro updates, FII/DII order flows, and sector alerts.
    - Classifies news by sentiment (BULLISH, BEARISH, NEUTRAL) and impact level (HIGH, MEDIUM, LOW).
    """

    def __init__(self):
        self.news_items: List[Dict[str, Any]] = [
            {
                "id": "NEWS_101",
                "timestamp": (datetime.now() - timedelta(minutes=4)).strftime("%H:%M:%S"),
                "category": "DERIVATIVES",
                "asset": "NIFTY",
                "headline": "NIFTY 24,100 PE Volume Surges with 54.7 Lakh OI as Put Buyers Dominate",
                "summary": "Heavy Call writing detected at 24,200 and 24,300 strikes. PCR dips to 0.59 confirming strong institutional breakdown momentum.",
                "sentiment": "BEARISH",
                "impact": "HIGH",
                "source": "Market Telemetry Engine"
            },
            {
                "id": "NEWS_102",
                "timestamp": (datetime.now() - timedelta(minutes=12)).strftime("%H:%M:%S"),
                "category": "BANKING",
                "asset": "BANKNIFTY",
                "headline": "Bank Nifty Slips -475 Pts Towards 57,500 Support on Private Bank Selling",
                "summary": "HDFC Bank and ICICI Bank face intraday profit booking. 57,500 PE sees heavy open interest additions as institutions hedge downside risk.",
                "sentiment": "BEARISH",
                "impact": "HIGH",
                "source": "Market Telemetry Engine"
            },
            {
                "id": "NEWS_103",
                "timestamp": (datetime.now() - timedelta(minutes=24)).strftime("%H:%M:%S"),
                "category": "FII_DII",
                "asset": "MARKET",
                "headline": "Institutional Flow: FIIs Net Sellers in Index Futures (-₹1,420 Cr)",
                "summary": "FII Long-Short ratio drops to 42.1%. Domestic institutions provide partial support with ₹890 Cr buying in FMCG and IT defensive stocks.",
                "sentiment": "BEARISH",
                "impact": "HIGH",
                "source": "Institutional Flow Tracker"
            },
            {
                "id": "NEWS_104",
                "timestamp": (datetime.now() - timedelta(minutes=41)).strftime("%H:%M:%S"),
                "category": "MACRO",
                "asset": "GLOBAL",
                "headline": "Brent Crude Stabilizes at $74.80/bbl; US Dollar Index (DXY) Firms at 104.2",
                "summary": "Firm dollar index puts mild pressure on emerging market currencies. INR holds steady at 83.92 per USD.",
                "sentiment": "NEUTRAL",
                "impact": "MEDIUM",
                "source": "Macro Indicator Feed"
            },
            {
                "id": "NEWS_105",
                "timestamp": (datetime.now() - timedelta(minutes=58)).strftime("%H:%M:%S"),
                "category": "MACRO",
                "asset": "RBI",
                "headline": "RBI Liquidity Update: Banking System Liquidity in ₹45,000 Cr Surplus",
                "summary": "Overnight call money rates stay anchored near repo rate. Bond yields steady at 6.84%.",
                "sentiment": "NEUTRAL",
                "impact": "LOW",
                "source": "Macro Indicator Feed"
            },
            {
                "id": "NEWS_106",
                "timestamp": (datetime.now() - timedelta(minutes=75)).strftime("%H:%M:%S"),
                "category": "IT_SECTOR",
                "asset": "NIFTY_IT",
                "headline": "IT Index Shows Relative Strength on US Tech Resiliency (TCS, Infosys +0.4%)",
                "summary": "Defensive rotation underway as market participants trim high-beta banking and allocate into largecap IT.",
                "sentiment": "BULLISH",
                "impact": "MEDIUM",
                "source": "Sector Rotation Monitor"
            }
        ]

    def get_latest_news(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.news_items[:limit]

    def add_simulated_breaking_news(self) -> Dict[str, Any]:
        templates = [
            ("NIFTY 24,600 CE Volume Surges 3.2x as Institutional Squeeze Fires", "Extreme gamma expansion detected in 24,600 CE contract. Momentum favors CE buyers.", "BULLISH", "HIGH", "INDICES", "NIFTY"),
            ("Bank Nifty VWAP Breakout: Clean Rebound from 52,400 Support", "Buyers aggressive above VWAP. Target 52,800 on short-squeeze continuation.", "BULLISH", "HIGH", "BANKING", "BANKNIFTY"),
            ("Global Semiconductor Index Jumps 2.1%; IT Equities Gain Trajectory", "Infosys & TCS see fresh long build-up with positive ADR cues overnight.", "BULLISH", "MEDIUM", "IT_SECTOR", "NIFTY_IT"),
            ("India VIX Drops Below 13.2; Stable Premium Environment Favors Breakouts", "Low implied volatility compression indicates directional explosive move preparing.", "NEUTRAL", "MEDIUM", "VOLATILITY", "INDIA_VIX")
        ]
        chosen = random.choice(templates)
        new_id = f"NEWS_{random.randint(107, 999)}"
        news_obj = {
            "id": new_id,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "category": chosen[4],
            "asset": chosen[5],
            "headline": chosen[0],
            "summary": chosen[1],
            "sentiment": chosen[2],
            "impact": chosen[3],
            "source": "Anil Babu Trades Quant Wire"
        }
        self.news_items.insert(0, news_obj)
        if len(self.news_items) > 50:
            self.news_items = self.news_items[:50]
        return news_obj
