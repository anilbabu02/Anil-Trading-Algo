import pytest
from datetime import datetime
from services.news_service import NewsService
from services.option_advisor import OptionAdvisorService
from services.scheduler import AutomatedSchedulerService
from services.fail_safes import ExecutionMicrostructureGuard

def test_news_service():
    news = NewsService()
    items = news.get_latest_news(limit=5)
    assert len(items) > 0
    assert "headline" in items[0]
    assert "sentiment" in items[0]
    
    # Test adding breaking news
    new_item = news.add_simulated_breaking_news()
    assert new_item is not None
    assert "headline" in new_item
    assert new_item["id"].startswith("NEWS_") or new_item["id"].startswith("REAL_")

def test_option_advisor_service():
    advisor = OptionAdvisorService()
    suggestions = advisor.get_all_suggestions()
    assert len(suggestions) >= 3
    
    active = advisor.get_active_suggestions()
    assert len(active) > 0
    
    first = suggestions[0]
    assert "symbol" in first
    assert "entry_price" in first
    assert "stop_loss" in first
    assert "target_1" in first
    assert first["entry_price"] > first["stop_loss"]
    assert first["target_1"] > first["entry_price"]

def test_scheduler_service():
    scheduler = AutomatedSchedulerService()
    status = scheduler.get_schedule_status()
    assert status["status"] == "ACTIVE"
    assert status["daily_morning_time"] == "08:30:00 AM IST"
    assert "next_morning_digest_in" in status

def test_microstructure_guard():
    guard = ExecutionMicrostructureGuard(max_allowed_spread_pts=1.50)
    
    # Normal spread
    ok, reason = guard.verify_bid_ask_spread(bid=120.0, ask=121.0)
    assert ok is True
    assert reason == "SPREAD_OK"
    
    # Wide spread rejection
    ok, reason = guard.verify_bid_ask_spread(bid=120.0, ask=122.50)
    assert ok is False
    assert "SPREAD_TOO_WIDE" in reason
    
    # Pegged limit price
    pegged_buy = guard.calculate_pegged_limit_price(bid=100.0, ask=102.0, direction="BUY")
    assert pegged_buy == 100.50

def test_quant_engine_position_marking():
    import asyncio
    import pandas as pd
    from services.engine import QuantExecutionEngine
    from core.models import Position, StrategyType, SignalDirection
    
    async def _runner():
        engine = QuantExecutionEngine(mode="paper")
        
        # Set active position with entry at 120 and underlying at 24500
        engine.active_position = Position(
            id="POS_UNIT_TEST",
            symbol="NIFTY_24500_CE",
            strategy=StrategyType.SQUEEZE_BREAKOUT,
            direction=SignalDirection.BUY_CE,
            quantity=65,
            entry_price=120.0,
            underlying_entry_price=24500.0,
            current_price=120.0,
            stop_loss=105.0,
            original_stop_loss=105.0,
            target=160.0
        )
        
        # Candle with small spot move of +10 pts (from 24500 to 24510)
        df = pd.DataFrame([{
            "open": 24505.0,
            "high": 24515.0,
            "low": 24500.0,
            "close": 24510.0,
            "volume": 10000,
            "timestamp": datetime(2026, 8, 28, 10, 30)
        }] * 25)
        
        res = await engine.process_market_update(df, symbol="NIFTY")
        assert res is not None
        # Position should still be held with realistic option price (~125.0), not phantom ~12,310.0
        assert engine.active_position is not None
        assert engine.active_position.current_price < 150.0

    asyncio.run(_runner())
