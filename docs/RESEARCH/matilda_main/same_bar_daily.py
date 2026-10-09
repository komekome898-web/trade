"""本ごとに、1 段目と同じ足の中で閉じた取引 / 足の後まで持った取引 の日ごとの損益(出の UTC の日、取引の無い日は 0)を作り、
前半・後半(D1 と同じ分け方: 日の並びの半分)の 1 日あたり(円)と 95% 区間(diag_tables.mean_ci: 日の塊 5・1,000 回・種 20261004)を出す。
相方の count D10 の前の指摘 2。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/same_bar_daily.py <本> [...]
"""
import sys
sys.path.insert(0, "scripts/analysis")
import diag_tables as dt  # noqa: E402

T = "backtest_runs_shared/matilda_main_trades/"
f = lambda v: "—" if v is None else "%+.0f" % (v * 20)
print("| 本 | 群 | 前半 1 日あたり 円 [区間] | 後半 | 境(後半の最初の日) |")
print("|---|---|---|---|---|")
for name in sys.argv[1:]:
    run = dt.load_run(T + name)
    days = dt.period_days(run)
    h = len(days) // 2
    for grp, sel in (("同じ足の中", lambda t: t["exit_ns"] <= t["entry_ns"]), ("後まで持った", lambda t: t["exit_ns"] > t["entry_ns"])):
        d = {x: 0.0 for x in days}
        for t in run["trades"]:
            k = dt.utc_day(t["exit_ns"])
            if k in d and sel(t):
                d[k] += t["pnl_bp"]
        a, b = dt.mean_ci([d[x] for x in days[:h]]), dt.mean_ci([d[x] for x in days[h:]])
        print(f"| {name} | {grp} | {f(a['mean'])} [{f(a['lo'])}, {f(a['hi'])}] | {f(b['mean'])} [{f(b['lo'])}, {f(b['hi'])}] | {days[h]} |")
