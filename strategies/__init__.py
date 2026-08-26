"""Quantitative Strategy Modules for Anil Babu Trades Algo Trading System."""
from .base import BaseStrategy
from .volatility_squeeze import VolatilitySqueezeStrategy
from .orb_vwap_sniper import ORBVWAPSniperStrategy
from .cash_mean_reversion import CashMeanReversionStrategy
from .market_regime import MarketRegimeClassifier

__all__ = [
    "BaseStrategy",
    "VolatilitySqueezeStrategy",
    "ORBVWAPSniperStrategy",
    "CashMeanReversionStrategy",
    "MarketRegimeClassifier"
]
