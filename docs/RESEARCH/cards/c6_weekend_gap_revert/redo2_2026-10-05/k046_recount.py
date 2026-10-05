"""カード 6: 台帳 K-046 の「窓と同じ向き(広げる向き)42 本」を、K-046 の台本 scripts/w4_measure/round0_decomp.py の定義
(g = 入りの値段 ÷ 入りの時刻より前の最後の日本時間の金曜に始まった bitFlyer の 1 分足の終値 − 1)で数え直す。
入力: 作り直した取引の行(trades_btc/trades.csv.gz、c6_redo.py)と measure/btc/run.npz の足。台本の試験は無い。
    python3 docs/RESEARCH/cards/c6_weekend_gap_revert/redo2_2026-10-05/k046_recount.py
"""
import csv
import gzip
import os
from datetime import datetime

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    z = np.load(os.path.join(HERE, "..", "measure", "btc", "run.npz"))
    d = np.flatnonzero(z["decided"])
    s, c = z["start_ns"][d], z["close"][d]
    jd = (s // 10**9 + 9 * 3600) // 86400
    fri = np.flatnonzero((jd + 3) % 7 == 4)  # 日本時間の金曜(0 = 月曜)
    rows = list(csv.DictReader(gzip.open(os.path.join(HERE, "trades_btc", "trades.csv.gz"), "rt")))
    same = fill = 0
    s_same = s_fill = 0.0
    for r in rows:
        e = int(datetime.fromisoformat(r["entry_t"].replace("Z", "+00:00")).timestamp()) * 10**9
        j = fri[np.searchsorted(s[fri], e, side="left") - 1]
        g = float(r["entry_price"]) / c[j] - 1
        if np.sign(g) == int(r["side"]):
            same += 1
            s_same += float(r["pnl_bp"])
        else:
            fill += 1
            s_fill += float(r["pnl_bp"])
    print(f"取引 {len(rows)}: 広げる向き(g と同じ向き){same} 本・和 {s_same:+,.1f} / 埋める向き {fill} 本・和 {s_fill:+,.1f}")


if __name__ == "__main__":
    main()
