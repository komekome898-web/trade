"""カード 5 の D5 の足し: 建てた取引(trades_rebuilt、向きが変わった分)の、約定の値段(約定の足の始値)を起点にした
h 分後(1・5・15・60)の始値までの値動き × 取引の向き、と対照(24 時間後の同じ時刻から同じ向き)。
diag_paths.py の 2 つの起点(合図の時刻・建ての時刻)はどちらも合図の足の終値から測る(このカードでは建ての時刻 = 合図の足の
終わり)ので、終値 → 次の足の始値 の 1 本の中の動きを含む。ここではそれを外す。台本の試験は無い。全期間・前半・後半。
    PYTHONPATH=src python3 docs/RESEARCH/cards/c5_tokyo_fix_momentum/redo2_2026-10-05/d5_entry_open.py
出力: このフォルダの D5_ENTRY_OPEN.md
"""
import collections
import csv
import gzip
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/home/user/trade"
sys.path.insert(0, os.path.join(REPO, "scripts/analysis"))
sys.path.insert(0, os.path.join(REPO, "src"))
import diag_tables as dt  # noqa: E402

NS, MIN = 10**9, 60 * 10**9


def main():
    z = np.load(os.path.join(HERE, "..", "measure", "default", "run.npz"))
    d = np.flatnonzero(z["decided"])
    s_dec, o_dec, c_dec = z["start_ns"][d], z["open"][d], z["close"][d]

    def open_at(ns):
        j = np.searchsorted(s_dec, ns, side="left")
        if j >= len(s_dec) or s_dec[j] - ns >= 5 * MIN:
            return None
        return float(o_dec[j])
    tr = list(csv.DictReader(gzip.open(os.path.join(HERE, "trades_rebuilt", "trades.csv.gz"), "rt")))
    days = sorted(dt.daily_series(dt.load_run(os.path.join(HERE, "trades_rebuilt"))))
    half = len(days) // 2
    parts = {"全期間": days, "前半": days[:half], "後半": days[half:]}
    out = ["# カード 5: 建てた取引の、約定の値段(約定の足の始値)からの値動き × 取引の向き(bp/取引)。対照 = 24 時間後の同じ時刻から", "",
           f"取引 {len(tr):,}。日 = 建ての時刻の UTC の日(diag_tables と同じ)。前半・後半の境 {days[half]}。", "",
           "| h 分 | 期間 | 取引 | 本体 [区間] | 対照 [区間] | 本体 − 対照 [区間] |", "|---|---|---|---|---|---|"]
    for h in (1, 5, 15, 60):
        acc = {k: (collections.defaultdict(float), collections.defaultdict(int)) for k in ("m", "c", "d")}
        for t in tr:
            e = dt._iso_ns(t["entry_t"])
            side = int(t["side"])
            a0, a1 = open_at(e), open_at(e + h * MIN)
            b0, b1 = open_at(e + 86400 * NS), open_at(e + 86400 * NS + h * MIN)
            if None in (a0, a1, b0, b1):
                continue
            mv, cv = side * (a1 / a0 - 1) * 1e4, side * (b1 / b0 - 1) * 1e4
            day = dt.utc_day(e)
            for k, v in (("m", mv), ("c", cv), ("d", mv - cv)):
                acc[k][0][day] += v
                acc[k][1][day] += 1
        for pn, pd in parts.items():
            r = {k: dt.group_ratio_ci(pd, *acc[k]) for k in acc}
            f = lambda q: "—" if q["per_trade"] is None else f"{q['per_trade']:+.3f} [{q['lo']:+.3f}, {q['hi']:+.3f}]"  # noqa: E731
            out.append(f"| {h} | {pn} | {r['m']['trades']:,} | {f(r['m'])} | {f(r['c'])} | {f(r['d'])} |")
    open(os.path.join(HERE, "D5_ENTRY_OPEN.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
