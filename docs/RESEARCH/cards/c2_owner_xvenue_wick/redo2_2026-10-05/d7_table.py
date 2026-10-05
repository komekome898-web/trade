"""カード 2 の D7 の表: d7/*.json(diag_tables --vs の出力)の全期間の差と取引の突き合わせを写し、
同じ日どうしの日ごとの差を D1 と同じ前半・後半(日数で 2 つ)に分けた平均・区間を足す。
区間は diag_tables.mean_ci(日の塊 5 日・1,000 回・種 20261004)。日ごとの系列は diag_tables.load_run・daily_series。
    PYTHONPATH=src python3 docs/RESEARCH/cards/c2_owner_xvenue_wick/redo2_2026-10-05/d7_table.py
出力: このフォルダの D7_TABLE.md(全行)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/trade/scripts/analysis")
import diag_tables as dt  # noqa: E402

RUNS = os.path.join(HERE, "..", "limit_sim", "runs")


def f(r):
    return "—" if r.get("mean") is None or r.get("lo") is None else f"{r['mean']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}]"


def main():
    out = ["# カード 2 の D7: 変種 − 基準(weak_f<足>_close_a)、同じ日どうしの日ごとの差(bp/日)", "",
           "前半・後半は D1 と同じ日数の 2 分け。取引の突き合わせは合図の時刻で(diag_tables)。", "",
           "| 足 | 変種 | 全期間の差 | 前半の差 | 後半の差 | 両方の取引: 本・差の和 | 変種だけ: 本・和 | 基準だけ: 本・和 |",
           "|---|---|---|---|---|---|---|---|"]
    for fn in sorted(os.listdir(os.path.join(HERE, "d7")), key=lambda s: (int(s.split("_")[0][1:]), s)):
        if not fn.endswith(".json"):
            continue
        foot, var = fn[:-5].split("_", 1)
        j = json.load(open(os.path.join(HERE, "d7", fn)))["d7"]
        a = dt.daily_series(dt.load_run(os.path.join(RUNS, f"weak_{foot}_{var}")))
        b = dt.daily_series(dt.load_run(os.path.join(RUNS, f"weak_{foot}_close_a")))
        days = sorted(set(a) & set(b))
        half = len(days) // 2
        d1 = dt.mean_ci([a[d] - b[d] for d in days[:half]])
        d2 = dt.mean_ci([a[d] - b[d] for d in days[half:]])
        m = j.get("match") or {}
        out.append(f"| {foot[1:]} | {var} | {f(j['all'])} | {f(d1)} | {f(d2)} | {m.get('both', '—')}・{m.get('sum_both_a_minus_b', 0):+,.0f} | "
                   f"{m.get('only_a', '—')}・{m.get('sum_only_a', 0):+,.0f} | {m.get('only_b', '—')}・{m.get('sum_only_b', 0):+,.0f} |")
        print(out[-1], flush=True)
    open(os.path.join(HERE, "D7_TABLE.md"), "w").write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
