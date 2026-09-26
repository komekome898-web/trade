"""Round 17 worker: us per bar, 20,000 bars, an order with a small extra every 10 bars (best of 3)."""
import sys, time
from bot.bt.core import BarEvent, CoreEngine, values
from bot.bt.core.api import OrderRequest
from bot.bt.core.interfaces import NullCostModel
from bot.bt.core.testing import ImmediateFillModel, RecordingAccount
T0 = 1_700_000_000_000_000_000
N = 20_000
bars = [BarEvent(received_time_ns=T0 + k * 1000, open=100.0, high=100.0, low=100.0, close=100.0, volume=1.0)
        for k in range(N)]
class S:
    def __init__(self): self.n = 0
    def on_event(self, ev, ctx):
        self.n += 1
        if self.n % 10 == 0:
            ctx.place_order(OrderRequest(side="buy", order_type="market", size=1.0, client_order_id=f"o{self.n}",
                                         extra=(("tag", {"a": [1, 2], "b": (3, "x")}),)))
best = None
for _ in range(3):
    t = time.perf_counter()
    CoreEngine(S(), bars, fill_model=ImmediateFillModel(100.0), account=RecordingAccount(),
               cost_model=NullCostModel()).run()
    d = (time.perf_counter() - t) / N * 1e6
    best = d if best is None else min(best, d)
print(f"{sys.argv[1]}: {best:.2f} us/bar (best of 3) core at {values.__file__}")
