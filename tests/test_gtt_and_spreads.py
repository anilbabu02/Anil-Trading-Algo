import pytest
from services.spread_builder import SpreadBuilderService
from services.fyers_totp_auth import FyersTotpAuthService
from services.fyers_websocket_service import FyersWebSocketService
from brokers.fyers_adapter import FyersAdapter

def test_spread_builder_vertical_spreads():
    service = SpreadBuilderService()
    quotes = {
        "NIFTY": {"ltp": 24090.85, "change": -116.90, "change_pct": -0.48},
        "BANKNIFTY": {"ltp": 57509.95, "change": -475.05, "change_pct": -0.82}
    }
    spreads = service.build_spreads_from_spot(quotes)
    assert len(spreads) >= 2
    
    nifty_spread = next((s for s in spreads if s["underlying"] == "NIFTY 50"), None)
    assert nifty_spread is not None
    assert len(nifty_spread["legs"]) == 2
    assert nifty_spread["max_profit"] > 0
    assert nifty_spread["max_risk"] > 0
    assert "Margin" in nifty_spread["margin_benefit_pct"] or "Savings" in nifty_spread["margin_benefit_pct"]

def test_fyers_gtt_order_generation():
    adapter = FyersAdapter()
    res = adapter.place_gtt_order(
        symbol="NSE:NIFTY2690124100PE",
        quantity=65,
        side="SELL",
        trigger_price=35.0,
        price=35.0
    )
    assert "gtt_id" in res
    assert res["trigger_price"] == 35.0

def test_fyers_totp_generation():
    totp_service = FyersTotpAuthService()
    # Test TOTP generator with a valid base32 test key
    test_key = "JBSWY3DPEHPK3PXP"
    code = totp_service.generate_current_totp(test_key)
    assert len(code) == 6
    assert code.isdigit()

def test_fyers_websocket_service():
    ws = FyersWebSocketService()
    status = ws.get_status()
    assert "subscribed_count" in status
    assert status["subscribed_count"] >= 4
    
    # Test callback dispatch
    received = []
    ws.register_callback(lambda t: received.append(t))
    ws.on_tick_message({"symbol": "NSE:NIFTY50-INDEX", "ltp": 24090.85})
    assert len(received) == 1
    assert received[0]["ltp"] == 24090.85
