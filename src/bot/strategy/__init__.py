from bot.strategy.base import Signal, SignalType, Strategy
from bot.strategy.ema_cross import EmaCrossStrategy
from bot.strategy.rsi_reversion import RsiReversionStrategy
from bot.strategy.breakout import BreakoutStrategy
from bot.strategy.xborder_momentum import XborderMomentumStrategy
from bot.strategy.inago import InagoStrategy
from bot.strategy.wick_reversal import WickReversalStrategy
from bot.strategy.range_fade import RangeFadeStrategy
from bot.strategy.composite import CompositeStrategy

STRATEGIES = {
    "ema_cross": EmaCrossStrategy,
    "rsi_reversion": RsiReversionStrategy,
    "breakout": BreakoutStrategy,
    "xborder_momentum": XborderMomentumStrategy,
    "inago": InagoStrategy,
    "wick_reversal": WickReversalStrategy,
    "range_fade": RangeFadeStrategy,
    "composite": CompositeStrategy,
}

__all__ = ["Signal", "SignalType", "Strategy", "STRATEGIES",
           "EmaCrossStrategy", "RsiReversionStrategy", "BreakoutStrategy",
           "XborderMomentumStrategy", "InagoStrategy", "WickReversalStrategy",
           "RangeFadeStrategy", "CompositeStrategy"]
