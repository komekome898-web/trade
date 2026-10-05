"""カード 5: 保存済みの measure/default/run.npz から取引の行を作り直す(走らせ直しではない。台本の試験は無い)。
取引 = measure の extra.json の formula と同じ: P のある決定を順に並べ、sign(e) が同じで 0 でない決定がつながった最長の区間。
    entry_t = 最初の決定の約定の足の始まり(= 決定の足の終わり。約定の値段 = その足の始値)
    exit_t  = 最後の決定の出の足(次の決定の約定の足)の始まり(出の値段 = その足の始値)
    signal_t = 最初の決定の足の終わり(合図が分かった時刻。値は終値で決まる)
    pnl_bp = 区間の P_t の和、side = 符号、entry_price = 約定の足の始値
diag_paths.py の決まり(span = 始まりが [entry, exit) の足、close_at(t) = t に終わる足の終値)に合わせた。
    PYTHONPATH=src python3 docs/RESEARCH/cards/c5_tokyo_fix_momentum/redo2_2026-10-05/rebuild_trades.py
出力: このフォルダの trades_rebuilt/trades.csv.gz
"""
import csv
import gzip
import json
import os
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
M = os.path.join(HERE, "..", "measure", "default")


def iso(ns):
    return datetime.fromtimestamp(int(ns) / 1e9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    z = np.load(os.path.join(M, "run.npz"))
    op, ex_all, dec, end_ns, start_ns = (z[k] for k in ("open", "exposure", "decided", "end_ns", "start_ns"))
    d = np.flatnonzero(dec)
    m = len(d) - 2
    bar, fill, ex = d[:m], d[1:m + 1], d[2:m + 2]
    e = ex_all[bar]
    p = e * (op[ex] / op[fill] - 1.0) * 1e4
    s = np.sign(e)
    rows, i = [], 0
    while i < m:
        if s[i] == 0:
            i += 1
            continue
        j = i
        while j + 1 < m and s[j + 1] == s[i]:
            j += 1
        rows.append([iso(end_ns[bar[i]]), iso(start_ns[fill[i]]), iso(start_ns[ex[j]]), int(s[i]), f"{op[fill[i]]:.1f}",
                     f"{p[i:j + 1].sum():.6f}"])
        i = j + 1
    os.makedirs(os.path.join(HERE, "trades_rebuilt"), exist_ok=True)
    with gzip.open(os.path.join(HERE, "trades_rebuilt", "trades.csv.gz"), "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["signal_t", "entry_t", "exit_t", "side", "entry_price", "pnl_bp"])
        w.writerows(rows)
    ext = json.load(open(os.path.join(M, "extra.json")))["trades"]
    print({"trades": len(rows), "sum": sum(float(r[5]) for r in rows), "extra_long_n": ext["long"]["n"],
           "extra_short_n": ext["short"]["n"], "long": sum(1 for r in rows if r[3] > 0)})


if __name__ == "__main__":
    main()
