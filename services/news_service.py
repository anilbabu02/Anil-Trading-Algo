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
                "category": "INDICES",
                "asset": "NIFTY",
                "headline": "NIFTY Crosses 24,550 on Heavy Call Unwinding; 24,600 Squeeze Imminent",
                "summary": "Massive short covering seen in 24,500-24,550 CE strikes. Open Interest dropped by 32 lakh shares, giving strong directional breakout momentum.",
                "sentiment": "BULLISH",
                "impact": "HIGH",
                "source": "NSE Derivatives Feed"
            },
            {
                "id": "NEWS_102",
                "timestamp": (datetime.now() - timedelta(minutes=12)).strftime("%H:%M:%S"),
                "category": "FII_DII",
                "asset": "MARKET",
                "headline": "Institutional Flow: FIIs Turn Net Buyers in Index Futures (+3,450 Contracts)",
                "summary": "FII Long-Short ratio improved from 51% to 58.4% today. DIIs pumped ₹1,180 Cr cash in bluechip banking and auto names.",
                "sentiment": "BULLISH",
                "impact": "HIGH",
                "source": "Institutional Flow Wire"
            },
            {
                "id": "NEWS_103",
                "timestamp": (datetime.now() - timedelta(minutes=24)).strftime("%H:%M:%S"),
                "category": "MACRO",
                "asset": "GLOBAL",
                "headline": "Brent Crude Tumbles to $74.20/bbl (-0.8%) on US Inventory Build",
                "summary": "Lower crude prices ease import inflation for India, boosting Paint, Auto, and Oil Marketing Companies (OMCs).",
                "sentiment": "BULLISH",
                "impact": "MEDIUM",
                "source": "Bloomberg Commodity Desk"
            },
            {
                "id": "NEWS_104",
                "timestamp": (datetime.now() - timedelta(minutes=41)).strftime("%H:%M:%S"),
                "category": "BANKING",
                "asset": "BANKNIFTY",
                "headline": "HDFC Bank & ICICI Bank Lead 350-Point Rally in Bank Nifty",
                "summary": "Banking index trades above its 20-day EMA and VWAP. PCR for Bank Nifty weekly series rises to 1.18 indicating strong put writing support.",
                "sentiment": "BULLISH",
                "impact": "HIGH",
                "source": "CNBC-TV18 Live Wire"
            },
            {
                "id": "NEWS_105",
                "timestamp": (datetime.now() - timedelta(minutes=58)).strftime("%H:%M:%S"),
                "category": "MACRO",
                "asset": "RBI",
                "headline": "RBI Liquidity Infusion: ₹50,000 Cr Injected via Overnight VRR Auction",
                "summary": "Interbank liquidity deficit eased, stabilizing overnight MIBOR rates and supporting bond yields.",
                "sentiment": "NEUTRAL",
                "impact": "MEDIUM",
                "source": "RBI Press Release"
            },
            {
                "id": "NEWS_106",
                "timestamp": (datetime.now() - timedelta(minutes=75)).strftime("%H:%M:%S"),
                "category": "GLOBAL",
                "asset": "US_MARKETS",
                "headline": "US S&P 500 Futures Trade Higher (+0.45%); US 10-Yr Yield Cools to 4.18%",
                "summary": "US tech momentum remains resilient. GIFT Nifty indicates a gap-up continuation for Indian equity indices.",
                "sentiment": "BULLISH",
                "impact": "MEDIUM",
                "source": "Reuters Global"
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
