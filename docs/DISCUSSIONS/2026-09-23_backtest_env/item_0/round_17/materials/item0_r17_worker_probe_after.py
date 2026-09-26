"""Round 17 worker probe (after the fix): the same shapes as the before-probe, and deeper."""
import sys, time
from bot.bt.core import values
exec(open(sys.argv[1]).read())  # MK_SRC of the grid: shared(kind, n)
def timed(label, fn):
    s = time.perf_counter()
    try:
        fn(); r = "ok"
    except Exception as e:
        r = type(e).__name__
    print(f"{label}: {r} in {time.perf_counter()-s:.3f} s")
for kind, n in (("tuple", 90), ("list", 90), ("dict", 90), ("FrozenList", 90), ("FrozenDict", 90),
                ("FrozenDict-key", 90), ("frozenset", 45), ("mixed", 90)):
    x = shared(kind, n)
    timed(f"{kind} n={n} freeze", lambda: values.freeze(x))
    timed(f"{kind} n={n} settle", lambda: values.settle(x))
    f = values.freeze(x)
    timed(f"{kind} n={n} renew", lambda: values.renew(f))
    timed(f"{kind} n={n} thaw", lambda: values.thaw(f))
    g = values.freeze(values.FrozenDict({"r": shared(kind, n)}))
    timed(f"{kind} n={n} == of two built apart", lambda: values.freeze(values.FrozenDict({"r": x})) == g)
