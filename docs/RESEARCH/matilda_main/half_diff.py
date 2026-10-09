"""族の報告の型の表 3 に足す「基準との日ごとの差」の前半・後半(相方の foot D10 の指摘 1)。
走らせ − 基準 を同じ日で並べ、D1 と同じ分け方(日の並びの半分。diag_tables.d1 と同じ h = 日数 // 2)で前半・後半に分け、
それぞれの 1 日あたり(円)と区間(diag_tables.mean_ci: 日の塊 5・1,000 回・種 20261004)を出す。

    PYTHONPATH=src:scripts/analysis python3 docs/RESEARCH/matilda_main/half_diff.py <run> [<run> ...]
"""
import sys

sys.path.insert(0, "scripts/analysis")
import diag_tables as dt  # noqa: E402

T = "backtest_runs_shared/matilda_main_trades/"
base = dt.daily_series(dt.load_run(T + "base"))


def yen(r):
    f = lambda v: "—" if v is None else "%+.0f" % v
    return "%s [%s, %s](MDE %s)" % (f(r["mean"]), f(r["lo"]), f(r["hi"]),
                                   "—" if r["mde"] is None else "%.0f" % r["mde"])


print("| 本 − base | 前半 | 後半 | 境 |")
print("|---|---|---|---|")
for name in sys.argv[1:]:
    d = dt.daily_series(dt.load_run(T + name))
    days = sorted(set(d) & set(base))
    h = len(days) // 2
    diff = [d[x] - base[x] for x in days]
    a, b = dt.mean_ci(diff[:h]), dt.mean_ci(diff[h:])
    print("| %s | %s | %s | 前半 %s〜%s・後半 %s〜%s |" % (name, yen(a), yen(b), days[0], days[h - 1], days[h], days[-1]))
