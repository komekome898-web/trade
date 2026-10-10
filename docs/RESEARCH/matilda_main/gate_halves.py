#!/usr/bin/env python3
"""門の族 3 つの「門で外した合図」と「門を通った合図」の D5 を、前半・後半(境 2019-12-09)と門の値で並べる(持ち越しの 3、L-909)。

入力は読み口 diag_paths の出力(`<族>/blocked_<走らせ>.json`、`regen_paths_cut.sh` で作った)だけ。新しい計算はしない(写して並べるだけ)。
値は合図の向きを掛けた値動き率(bp)、1 合図あたり [区間]。起点 = 建ての時刻(外した合図は基準で建った時刻)。
    python3 docs/RESEARCH/matilda_main/gate_halves.py > docs/RESEARCH/matilda_main/gate_halves.out
"""
import json
import os

M = os.path.dirname(os.path.abspath(__file__))
RUNS = [("range_lo", "range_lo_p10", "幅の下の門 0.1857%"), ("range_lo", "range_lo_p25", "幅の下の門 0.3010%"),
        ("range_lo", "range_lo_p50", "幅の下の門 0.5133%"), ("range_hi", "range_hi_p90", "幅の上の門 1.4995%"),
        ("range_hi", "range_hi_p75", "幅の上の門 0.8844%"), ("vola_gate", "vola_gate_p10", "ボラの門 0.0170%"),
        ("vola_gate", "vola_gate_p25", "ボラの門 0.0276%"), ("vola_gate", "vola_gate_p50", "ボラの門 0.0465%"),
        ("range_lo", "range_lo_none", "幅の下の門 無し(基準より緩い)"), ("range_hi", "range_hi_none", "幅の上の門 無し(基準より緩い)")]


def f(x):
    if x["per_trade"] is None:
        return "—"
    if x["lo"] is None:
        return f"{x['per_trade']:+.2f} [—]"
    return f"{x['per_trade']:+.2f} [{x['lo']:+.2f}, {x['hi']:+.2f}]"


for fam, run, label in RUNS:
    j = json.load(open(os.path.join(M, fam, f"blocked_{run}.json"), encoding="utf-8"))
    ks = list(j["d5"])
    taken = next(k for k in ks if k.startswith("建てた合図(起点 = 建ての"))
    bl = next(k for k in ks if k.startswith("建てなかった") and "で建った時刻" in k)
    print(f"## {label}({run})\n")
    print("| 半分 | 合図の後 | 外した合図の本数 | 外した合図 | 24 時間後 | 24 時間前 | 通った合図の本数 | 通った合図 | 24 時間後 | 24 時間前 |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for part, name in (("first", "前半"), ("second", "後半")):
        for h in ("1", "5", "15", "60"):
            B = j["d5_halves"][bl][part][h]
            T = j["d5_halves"][taken][part][h]
            print(f"| {name} | {h} 分 | {B['signal']['trades']} | {f(B['signal'])} | {f(B['control_24h'])} | {f(B['control_24h_before'])} | "
                  f"{T['signal']['trades']} | {f(T['signal'])} | {f(T['control_24h'])} | {f(T['control_24h_before'])} |")
    print()

# 外した合図の群に混ざる「門の走らせが持ち高を持っていた間の合図」の数(分析のスキル D5 の道具の行)。
# 外した合図 = 基準にあって門の走らせに無い合図の時刻。その時刻が門の走らせの取引の 建て〜出 の間に入る本数を数える。
import bisect  # noqa: E402
import csv  # noqa: E402
import gzip  # noqa: E402
from datetime import datetime  # noqa: E402

T = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(M))), "backtest_runs_shared", "matilda_main_trades")


def _rows(run):
    out = []
    with gzip.open(os.path.join(T, run, "trades.csv.gz"), "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("in_measure", "True") == "False":
                continue
            out.append((r.get("signal_t"), r["entry_t"], r["exit_t"]))
    return out


def _ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


base = _rows("base")
print("## 外した合図の群に混ざる、門の走らせが持ち高を持っていた間の合図\n")
print("| 門 | 外した合図 | 建て ≤ 合図 ≤ 出(出の時刻ちょうどを含む) | 割合 | 建て ≤ 合図 < 出(含まない。批評家の数え方) | 割合 |")
print("|---|---|---|---|---|---|")
for fam, run, label in RUNS[:8]:
    g = _rows(run)
    mine = {s for s, _, _ in g}
    iv = sorted((_ts(e), _ts(x)) for _, e, x in g)
    starts = [a for a, _ in iv]
    bl = [_ts(s) for s, _, _ in base if s and s not in mine]
    held = held_x = 0
    for t in bl:
        i = bisect.bisect_right(starts, t) - 1
        if i >= 0 and iv[i][0] <= t <= iv[i][1]:
            held += 1
        if i >= 0 and iv[i][0] <= t < iv[i][1]:
            held_x += 1
    print(f"| {label} | {len(bl)} | {held} | {held / len(bl):.2%} | {held_x} | {held_x / len(bl):.2%} |")
