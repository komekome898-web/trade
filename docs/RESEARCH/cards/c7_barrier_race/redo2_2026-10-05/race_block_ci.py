"""カード 7: 復元した当たり(races_<窓>.csv.gz)の反転の割合に、日の塊の区間(diag_tables.group_ratio_ci: 循環 5 日・1,000 回・
種 20261004。群の和 ÷ 群の数を日を選び直して作り直す)を付ける。二項の区間(当たりを独立とみた)と並べる。台本の試験は無い。
    PYTHONPATH=src python3 docs/RESEARCH/cards/c7_barrier_race/redo2_2026-10-05/race_block_ci.py
出力: このフォルダの RACE_BLOCK_CI.md
"""
import collections
import csv
import gzip
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/trade/scripts/analysis")
sys.path.insert(0, "/home/user/trade/src")
import diag_tables as dt  # noqa: E402


def main():
    out = ["# カード 7: 反転の割合の日の塊の区間(最初の当たりを除く。日 = 当たりの日本時間の日)", "",
           "| 窓 | 前の当たり | 期間 | 当たり | 反転の割合 [日の塊の区間] |", "|---|---|---|---|---|"]
    for v in ("1h", "1d", "1w"):
        rows = list(csv.DictReader(gzip.open(os.path.join(HERE, f"races_{v}.csv.gz"), "rt")))
        days = sorted(l.split(",")[0] for l in open(os.path.join(HERE, "..", "measure", v, "daily.csv")).read().splitlines()[1:])
        half = len(days) // 2
        parts = {"全期間": days, "前半": days[:half], "後半": days[half:]}
        prev = None
        recs = []
        for r in rows:
            s = int(r["side"])
            if prev is not None:
                recs.append((r["jst_day"], prev, 1.0 if s != prev else 0.0))
            prev = s
        for side_name, sel in (("両方", (1, -1)), ("上", (1,)), ("下", (-1,))):
            for pn, pd in parts.items():
                ps = set(pd)
                su, cn = collections.defaultdict(float), collections.defaultdict(int)
                for d, p_, x in recs:
                    if p_ in sel and d in ps:
                        su[d] += x
                        cn[d] += 1
                q = dt.group_ratio_ci(pd, su, cn)
                out.append(f"| {v} | {side_name} | {pn} | {q['trades']:,} | {q['per_trade']:.3f} [{q['lo']:.3f}, {q['hi']:.3f}] |")
    open(os.path.join(HERE, "RACE_BLOCK_CI.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
