"""Round 17 worker probe (before the fix): where the core's work unfolds a shared value."""
import time
from bot.bt.core import values

def dag(n, mk):
    t = mk(())
    for _ in range(n):
        t = mk((t, t))
    return t

def timed(label, fn):
    s = time.perf_counter()
    try:
        fn(); r = "ok"
    except Exception as e:
        r = type(e).__name__
    print(f"{label}: {r} in {time.perf_counter()-s:.3f} s")

for n in (14, 16, 18):
    t = dag(n, tuple)
    timed(f"n={n} freeze(tuple dag)", lambda: values.freeze(t))
    ft = None
    # FrozenDict built by the public constructor, holding the dag as a value: its hash is made now
    timed(f"n={n} FrozenDict({{'a': dag}}) (public constructor)", lambda: values.FrozenDict({"a": t}))
    timed(f"n={n} freeze({{'a': dag}}) (walk + the FrozenDict's hash)", lambda: values.freeze({"a": t}))
    l = [1]
    for _ in range(n):
        l = [l, l]
    timed(f"n={n} freeze(list dag)", lambda: values.freeze(l))
    f1 = values.freeze(l); f2 = values.freeze(l)
    timed(f"n={n} _plain_equal of two frozen list dags", lambda: values._plain_equal(f1, f2))
    timed(f"n={n} thaw(frozen list dag)", lambda: values.thaw(f1))
    timed(f"n={n} renew(frozen list dag)", lambda: values.renew(f1))
    d = {"x": 1}
    for _ in range(n):
        d = {"a": d, "b": d}
    timed(f"n={n} freeze(dict dag)", lambda: values.freeze(d))
