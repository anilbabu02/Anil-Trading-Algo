import pytest
from datetime import datetime, timedelta
from core.risk_manager import RiskManager
from core.database import DatabaseLedger
from core.models import Signal, Position, StrategyType, SignalDirection
import tempfile
import os

@pytest.fixture
def temp_db():
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_path = temp_file.name
    temp_file.close()
    db = DatabaseLedger(temp_path)
    yield db
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception:
        pass

def test_risk_trailing_sl_activation(temp_db):
    rm = RiskManager(temp_db)
    now = datetime(2026, 8, 23, 10, 0)
    pos = Position(
        id="POS_TEST_01",
        symbol="NIFTY_24500_CE",
        strategy=StrategyType.SQUEEZE_BREAKOUT,
        direction=SignalDirection.BUY_CE,
        quantity=65,
        entry_price=120.0,
        current_price=120.0,
        stop_loss=105.0,
        original_stop_loss=105.0,
        target=155.0,
        entry_time=now
    )

    # Price moves up by +16 pts (>= 15 pts trailing trigger)
    exit_reason, new_sl = rm.update_position_risk(pos, current_price=136.0, current_time=now + timedelta(minutes=10))

    assert pos.trailing_activated is True
    assert pos.stop_loss == 121.0  # Cost (120) + 1 pt
    assert exit_reason is None

def test_risk_stagnation_45min_exit(temp_db):
    rm = RiskManager(temp_db)
    now = datetime(2026, 8, 23, 10, 0)
    pos = Position(
        id="POS_TEST_02",
        symbol="NIFTY_24500_CE",
        strategy=StrategyType.SQUEEZE_BREAKOUT,
        direction=SignalDirection.BUY_CE,
        quantity=65,
        entry_price=120.0,
        current_price=122.0,  # Gain < 5 pts
        stop_loss=105.0,
        original_stop_loss=105.0,
        target=155.0,
        entry_time=now
    )

    # 46 minutes elapsed with no momentum
    exit_reason, _ = rm.update_position_risk(pos, current_price=122.0, current_time=now + timedelta(minutes=46))
    assert exit_reason == "STAGNATION_EXIT_45M"
