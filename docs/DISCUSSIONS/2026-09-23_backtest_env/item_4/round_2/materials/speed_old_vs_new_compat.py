"""Speed of the old engine vs the new compatibility mouth, same synthetic input (1,000 1-minute bars, seeded)."""
import random, time
import pandas as pd
import bot.backtest.engine as OLD
import bot.bt.compat.engine as NEW
from bot.strategy.base import Signal, SignalType, Strategy

rng = random.Random(20260926)
n = 1000
p = 100.0; rows = []
for i in range(n):
    o = p + rng.choice((0, 0.5, -0.5)); c = o + rng.choice((-1, -0.5, 0, 0.5, 1))
    rows.append((o, max(o, c) + rng.choice((0, 0.5, 1)), min(o, c) - rng.choice((0, 0.5, 1)), c)); p = c
df = pd.DataFrame({"open": [r[0] for r in rows], "high": [r[1] for r in rows], "low": [r[2] for r in rows],
                   "close": [r[3] for r in rows], "volume": [1.0] * n},
                  index=pd.date_range("2026-01-05", periods=n, freq="min", tz="UTC"))
sig = [rng.choice(".....BSC") for _ in range(n)]
M = {".": SignalType.HOLD, "B": SignalType.BUY, "S": SignalType.SELL, "C": SignalType.CLOSE}

class S(Strategy):
    def __init__(self): super().__init__({})
    @property
    def min_history(self): return 0
    def on_candles(self, c): return Signal(M[sig[len(c) - 1]])

def run(mod):
    return mod.run_backtest(S(), df, initial_equity_jpy=10000.0, order_notional_jpy=3000.0,
                            costs=mod.CostModel(taker_fee_pct=0.1, maker_fee_pct=0.02, slippage_pct=0.01, spread_pct=0.02),
                            stop_loss_pct=1.0, take_profit_pct=2.0, allow_short=True)

for name, mod in (("old", OLD), ("new_compat", NEW)):
    ts = []
    for _ in range(3):
        t = time.perf_counter(); r = run(mod); ts.append(time.perf_counter() - t)
    print(name, "seconds per run (3 runs):", " ".join(f"{x:.3f}" for x in ts), "| trades:", len(r.trade_pnls))
a, b = run(OLD), run(NEW)
print("same trade_pnls bits:", [float(x) for x in a.trade_pnls] == [float(x) for x in b.trade_pnls])
