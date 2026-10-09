# 注(L-920、2026-10-09): 口座の bp(取引の行の pnl_bp)は廃止した。この台本は廃止前の列・出力を読む調べの記録で、今の出力では動かない。
# リードが書いた。委任・批評家を通していない(数えるだけ)。L-916 の調べ(値動きの bp の基準の値段)。
# D4 の MFE・MAE は 1 段目の約定の値段に対する値動きの bp(diag_paths.py:106-112)。2 段以上建った取引では、持ち高全体の平均の値段に対する
# 含みとは基準が違う。その違いが関わる取引が D4 の各群に何本あるかを数える(群の分け方は diag_paths.d4 と同じ。段の数は取引の行の levels)。
# 持ち高全体の含みで分け直した群(影響の大きさ)は測っていない。
# 使い方(リポジトリの根から): PYTHONPATH=src python3 docs/RESEARCH/matilda_main/d4_levels_count.py base > docs/RESEARCH/matilda_main/d4_levels_count.out
import csv
import gzip
import sys

sys.path.insert(0, "scripts/analysis")
import diag_paths as dp  # noqa: E402

T = "backtest_runs_shared/matilda_main_trades/"
for run in sys.argv[1:]:
    trades = dp.read_trades_csv(T + run)
    lv = {}
    with gzip.open(T + run + "/trades.csv.gz", "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("in_measure", "True") == "False":
                continue
            lv[(dp.dt._iso_ns(r["entry_t"]), dp.dt._iso_ns(r["exit_t"]))] = (int(float(r["levels"])), float(r["pnl_jpy"]))
    lo = min(t["entry_ns"] for t in trades) - 2 * dp.MIN
    hi = max(t["exit_ns"] for t in trades) + 2 * dp.MIN
    from common import SEAL, to_ns  # noqa: E402
    bars = dp.load_bitflyer_bars(lo, min(hi, to_ns(SEAL)))
    cnt = {}
    for t in trades:
        r = dp.trade_life(t, bars)
        if r is None:
            continue
        g = "勝った" if t["pnl_bp"] > 0 else ("損益 0" if t["pnl_bp"] == 0 else
                                            ("一度は MFE > 0 だったのに負けた" if r["mfe"] > 0 else "MFE ≤ 0 のまま負けた"))
        n, y = lv[(t["entry_ns"], t["exit_ns"])]
        k = (g, "1 段" if n == 1 else "2 段以上")
        c = cnt.setdefault(k, [0, 0.0])
        c[0] += 1
        c[1] += y
    print(f"## {run}\n\n| 群(1 段目の値段に対する MFE で分けた) | 段の数 | 取引 | 損益の和(円) |\n|---|---|---|---|")
    for k in sorted(cnt):
        print(f"| {k[0]} | {k[1]} | {cnt[k][0]:,} | {cnt[k][1]:+,.0f} |")
    print()
