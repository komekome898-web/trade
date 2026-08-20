from bot.strategy.base import Signal, SignalType, Strategy
from bot.strategy.ema_cross import EmaCrossStrategy
from bot.strategy.rsi_reversion import RsiReversionStrategy
from bot.strategy.breakout import BreakoutStrategy

STRATEGIES = {
    "ema_cross": EmaCrossStrategy,
    "rsi_reversion": RsiReversionStrategy,
    "breakout": BreakoutStrategy,
}

__all__ = ["Signal", "SignalType", "Strategy", "STRATEGIES",
           "EmaCrossStrategy", "RsiReversionStrategy", "BreakoutStrategy"]
