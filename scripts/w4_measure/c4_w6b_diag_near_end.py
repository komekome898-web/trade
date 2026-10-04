"""診断(封印の前の 6 日だけ): 決まらない足で、良い側・悪い側の道と「始値に近い端が先」の道と本当の順序の関係。"""
import sys, os, collections
sys.path.insert(0, "/home/user/trade/scripts/w4_measure"); sys.path.insert(0, "/home/user/trade/src")
import c4_w6b_order as w
from common import FX_DIR, load_bars, iso
from bot.research.matilda_limit_sim import MatildaLimitSim
days = [w.day_of(n) for n in w.TRADE_FILES]
starts = [w.day_ns(d) for d in days]
inday = lambda ns: any(s <= ns < s + 86400 * 10**9 for s in starts)
minutes = {}
for n in w.TRADE_FILES:
    minutes.update(w.read_trade_minutes(n))
truth = {k: m.order() for k, m in minutes.items()}
logs = {s: [] for s in w.SIDES}
sims = {s: MatildaLimitSim(fill_side=s, undecided_log=logs[s], **w.SIM_KW) for s in w.SIDES}
ohlc = {}
for x, y in ((w.START, "2023-01-01T00:00:00Z"), ("2023-01-01T00:00:00Z", w.END)):
    bars, _, _ = load_bars(FX_DIR, "FX_BTC_JPY", iso(x), iso(y))
    for b in bars:
        st = int(b.start_time_ns)
        if inday(st):
            ohlc[st] = (float(b.open), float(b.high), float(b.low), float(b.close))
        for s in w.SIDES:
            sims[s].feed(b)
def near(st):
    o, h, l, c = ohlc[st]
    return "up" if (h - o) <= (o - l) else "down"   # シミュレーターの near_up と同じ式
# 全部の分(6 日)で: 本当の順序が「始値に近い端が先」と一致する割合
tot = collections.Counter()
for st in ohlc:
    t = truth.get(st)
    if t in ("up", "down"):
        tot["n"] += 1; tot["near"] += (t == near(st))
print("全部の分: 本当の順序が決まった分", tot["n"], " 始値に近い端が先と一致", tot["near"], f"{tot['near']/tot['n']:.3f}")
for s in w.SIDES:
    c = collections.Counter()
    for r in logs[s]:
        st = r["start_ns"]
        if not inday(st) or r["path"] == "same":
            continue
        t = truth.get(st)
        if t not in ("up", "down"):
            continue
        nr = near(st)
        c["n"] += 1
        c["path_is_near"] += (r["path"] == nr)
        c["truth_is_near"] += (t == nr)
        c["match"] += (r["path"] == t)
        c[f"kind_{r['kind']}"] += 1
    print(s, dict(c))
