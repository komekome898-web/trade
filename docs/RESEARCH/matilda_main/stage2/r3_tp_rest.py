"""段 2 の読み R3(STAGE2_MATERIALS §9.1、K-376。L-963「1を裏で走らせながら」)。
待ちを短くした本(alert_5・alert_10)で、基準でも本でも利確・段数が同じ・段あたり 1.5 円より大きい(満額側)取引の差
(alert_loosen.out の「同じ」の行、alert_5 で前半 −206,889・後半 −179,688 円)の在処を数える。
見立て(走らせる前に書いた): 本の側で、保有が待ち(5・10 分)を越えた取引は利確の値段が緩む(`_tp_px` の worse、R9)。
緩めた指値が今の値段より不利なら次の足の始値で付き、段あたり 1.5 円を超えて「満額側」に入る。
それなら差は「本の保有 > 待ち」の側に集まり、「本の保有 ≤ 待ち」の側はほぼ 0。
分け方: 本の側の保有の分 = exit_t − entry_t(分)。待ちの分を越えたか(越えた = 時間で緩めた。中心より不利な側の緩め R9 は分けない)。
【試験の無い台本の値】
    python3 docs/RESEARCH/matilda_main/stage2/r3_tp_rest.py > docs/RESEARCH/matilda_main/stage2/r3_tp_rest.out
"""
import pandas as pd

T = "backtest_runs_shared/matilda_main_trades"
CUT = "2019-12-09"


def load(r):
    d = pd.read_csv(f"{T}/{r}/trades.csv.gz", usecols=["signal_t", "entry_t", "exit_t", "pnl_jpy", "exit_reason", "levels"])
    d["half"] = (d.signal_t.str[:10] >= CUT).map({False: "前半", True: "後半"})
    d["hold"] = (pd.to_datetime(d.exit_t) - pd.to_datetime(d.entry_t)).dt.total_seconds() / 60
    x = d.pnl_jpy / d.levels
    d["full"] = (d.exit_reason == "close") & (x > 1.5)
    return d


base = load("base")
for r, a in (("alert_5", 5), ("alert_10", 10)):
    m = base.merge(load(r), on="signal_t", suffixes=("_b", "_a"))
    m = m[m.full_b & m.full_a & (m.levels_b == m.levels_a)].copy()
    m["d"] = m.pnl_jpy_a - m.pnl_jpy_b
    m["over"] = m.hold_a > a
    m["same_exit"] = m.exit_t_a == m.exit_t_b
    print(f"\n## {r}: 基準でも本でも満額側の利確・段数が同じ({len(m):,} 本、差の和 {m.d.sum():+,.0f} 円)\n")
    print("| 半分 | 本の保有 | 出の時刻が同じ | 本 | 差の和(円) | 1 本あたり | 差が 0 の本 |")
    print("|---|---|---|---|---|---|---|")
    for h in ("前半", "後半"):
        for o in (False, True):
            for s in (True, False):
                x = m[(m.half_b == h) & (m.over == o) & (m.same_exit == s)]
                if len(x):
                    print(f"| {h} | {'待ちを越えた' if o else '待ち以内'} | {'同じ' if s else '違う'} | {len(x):,} | {x.d.sum():+,.0f} | {x.d.mean():+.2f} | {(x.d.abs() < 0.005).sum():,} |")
