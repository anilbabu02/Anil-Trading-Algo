from core.tax_calculator import IndianTaxCalculator

def test_option_cost_calculator():
    # Buy 65 qty @ 120, sell @ 155
    res = IndianTaxCalculator.calculate_option_costs(
        buy_price=120.0,
        sell_price=155.0,
        quantity=65,
        brokerage_per_order=20.0
    )

    assert res["gross_pnl"] == (155.0 - 120.0) * 65  # 2275.0
    assert res["brokerage"] == 40.0  # 20 * 2
    assert res["stt"] > 0
    assert res["gst"] > 0
    assert res["total_charges"] > 40.0
    assert res["net_pnl"] == round(res["gross_pnl"] - res["total_charges"], 2)

def test_equity_cost_calculator():
    res = IndianTaxCalculator.calculate_equity_costs(
        buy_price=2500.0,
        sell_price=2550.0,
        quantity=10,
        brokerage_per_order=20.0,
        is_intraday=True
    )
    assert res["gross_pnl"] == 500.0
    assert res["total_charges"] > 0
    assert res["net_pnl"] < 500.0
