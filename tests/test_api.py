import pytest
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_api_status_endpoint():
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert data["config"]["starting_capital"] == 10800.0
    assert data["config"]["max_daily_loss"] == 1000.0

def test_api_backtest_endpoint():
    res = client.post("/api/backtest/run", json={"start_year": 2021, "end_year": 2026, "starting_capital": 10800.0})
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert data["summary"]["overall_win_rate"] == 64.6
    assert data["summary"]["final_compounded_capital"] == 837624.26
