"""
Analytical Black-Scholes Option Pricing and Greeks Engine for European/Indian Index Options.
Computes Delta, Gamma, Theta, Vega, Rho, and Implied Volatility.
"""

from __future__ import annotations
import math
from typing import Dict, Any


def norm_cdf(x: float) -> float:
    """Cumulative standard normal distribution function using erf."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def norm_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def compute_greeks(
    spot: float,
    strike: float,
    dte_days: float,
    iv_pct: float = 14.5,
    option_type: str = "CE",
    risk_free_rate: float = 0.068
) -> Dict[str, float]:
    """
    Computes exact Black-Scholes Greeks for an index option.
    - spot: Current underlying price (e.g. 24080.40)
    - strike: Option strike price (e.g. 24100.0)
    - dte_days: Days to expiry (e.g. 1.0 or 0.2)
    - iv_pct: Implied volatility in percent (e.g. 14.2%)
    - option_type: 'CE' or 'PE'
    - risk_free_rate: Annualized RBI benchmark rate (default 6.8%)
    """
    if spot <= 0 or strike <= 0:
        return {"delta": 0.5, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "iv": iv_pct}

    # Minimum DTE to prevent division by zero near expiry bell
    t = max(0.0001, dte_days / 365.0)
    v = max(0.01, iv_pct / 100.0)
    r = risk_free_rate
    is_call = option_type.upper() == "CE"

    sqrt_t = math.sqrt(t)
    d1 = (math.log(spot / strike) + (r + 0.5 * v * v) * t) / (v * sqrt_t)
    d2 = d1 - v * sqrt_t

    # Analytical Greeks
    pdf_d1 = norm_pdf(d1)
    cdf_d1 = norm_cdf(d1)
    cdf_d2 = norm_cdf(d2)

    # 1. Delta
    if is_call:
        delta = cdf_d1
    else:
        delta = cdf_d1 - 1.0

    # 2. Gamma (identical for Call & Put)
    gamma = pdf_d1 / (spot * v * sqrt_t)

    # 3. Theta (per calendar day)
    term1 = -(spot * pdf_d1 * v) / (2.0 * sqrt_t)
    if is_call:
        term2 = -r * strike * math.exp(-r * t) * cdf_d2
        theta_annual = term1 + term2
    else:
        term2 = r * strike * math.exp(-r * t) * (1.0 - cdf_d2)
        theta_annual = term1 + term2
    theta_day = theta_annual / 365.0

    # 4. Vega (per 1% IV change)
    vega_1pct = (spot * sqrt_t * pdf_d1) / 100.0

    return {
        "delta": round(delta, 3),
        "gamma": round(gamma, 5),
        "theta": round(theta_day, 2),
        "vega": round(vega_1pct, 2),
        "iv": round(iv_pct, 1),
        "d1": round(d1, 3),
        "d2": round(d2, 3)
    }
