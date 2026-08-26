from typing import Dict

class IndianTaxCalculator:
    """
    Computes exact statutory Indian transaction costs & brokerage for
    NSE/BSE Options, Futures, and Intraday Equities.
    Supported Broker Models:
    - Kotak Neo (Trade Free Plan: ₹10 or ₹20/order)
    - Fyers API (₹20 or ₹60/trade standard)
    - Zerodha Kite (₹20/order)
    - Angel One (₹20/order)
    """

    @staticmethod
    def calculate_option_costs(
        buy_price: float,
        sell_price: float,
        quantity: int,
        brokerage_per_order: float = 20.0,
    ) -> Dict[str, float]:
        """
        Calculates full round-trip charges for Indian Index / Stock Options.
        """
        buy_turnover = buy_price * quantity
        sell_turnover = sell_price * quantity
        total_turnover = buy_turnover + sell_turnover

        # 1. Brokerage (Buy order + Sell order)
        brokerage = brokerage_per_order * 2.0

        # 2. STT (Securities Transaction Tax) - 0.1% on sell premium (or 0.0625%)
        # Current Indian STT on option sell side: 0.1% on turnover
        stt = sell_turnover * 0.0010

        # 3. Exchange Turnover Charges (NSE: ~0.0505% on premium turnover)
        exchange_charges = total_turnover * 0.000505

        # 4. GST (18% on Brokerage + Exchange charges + SEBI charges)
        gst = (brokerage + exchange_charges) * 0.18

        # 5. SEBI Turnover Charges (₹10 per crore = 0.000001)
        sebi_charges = total_turnover * 0.000001

        # 6. Stamp Duty (0.003% on buy turnover)
        stamp_duty = buy_turnover * 0.00003

        total_charges = brokerage + stt + exchange_charges + gst + sebi_charges + stamp_duty
        gross_pnl = (sell_price - buy_price) * quantity
        net_pnl = gross_pnl - total_charges

        return {
            "brokerage": round(brokerage, 2),
            "stt": round(stt, 2),
            "exchange_charges": round(exchange_charges, 2),
            "gst": round(gst, 2),
            "sebi_charges": round(sebi_charges, 2),
            "stamp_duty": round(stamp_duty, 2),
            "total_charges": round(total_charges, 2),
            "gross_pnl": round(gross_pnl, 2),
            "net_pnl": round(net_pnl, 2),
        }

    @staticmethod
    def calculate_equity_costs(
        buy_price: float,
        sell_price: float,
        quantity: int,
        brokerage_per_order: float = 20.0,
        is_intraday: bool = True
    ) -> Dict[str, float]:
        """
        Calculates round-trip costs for Cash Equity trades.
        """
        buy_turnover = buy_price * quantity
        sell_turnover = sell_price * quantity
        total_turnover = buy_turnover + sell_turnover

        # Brokerage
        if is_intraday:
            # 0.03% or flat ₹20, whichever is lower
            brokerage = min(total_turnover * 0.0003, brokerage_per_order * 2)
            stt = sell_turnover * 0.00025  # 0.025% on sell side
        else:
            brokerage = 0.0  # Zero delivery brokerage on discount brokers
            stt = total_turnover * 0.001  # 0.1% both sides

        exchange_charges = total_turnover * 0.0000345
        gst = (brokerage + exchange_charges) * 0.18
        sebi_charges = total_turnover * 0.000001
        stamp_duty = buy_turnover * 0.00003

        total_charges = brokerage + stt + exchange_charges + gst + sebi_charges + stamp_duty
        gross_pnl = (sell_price - buy_price) * quantity
        net_pnl = gross_pnl - total_charges

        return {
            "brokerage": round(brokerage, 2),
            "stt": round(stt, 2),
            "exchange_charges": round(exchange_charges, 2),
            "gst": round(gst, 2),
            "sebi_charges": round(sebi_charges, 2),
            "stamp_duty": round(stamp_duty, 2),
            "total_charges": round(total_charges, 2),
            "gross_pnl": round(gross_pnl, 2),
            "net_pnl": round(net_pnl, 2),
        }
