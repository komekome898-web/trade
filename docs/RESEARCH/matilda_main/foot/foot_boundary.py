"""足の長さの族の前半・後半の境を 2019-12-10(D1 の読み口)と 2019-12-09(compare_family・scenes の決め打ち)で並べ、
1 日あたり(円)と区間がどれだけ動くかを出す(監査役の関門 ② 1 回目の指摘 10)。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/foot/foot_boundary.py
"""
import sys
sys.path.insert(0, "scripts/analysis")
import diag_tables as dt  # noqa: E402
T = "backtest_runs_shared/matilda_main_trades/"
d = dt.daily_series(dt.load_run(T + "foot_5"))
f = lambda r: "%+.0f [%+.0f, %+.0f]" % (r["mean"], r["lo"], r["hi"])
for cut in ("2019-12-09", "2019-12-10"):
    days = sorted(d)
    a = dt.mean_ci([d[x] for x in days if x < cut]); b = dt.mean_ci([d[x] for x in days if x >= cut])
    print("foot_5 境", cut, "前半", f(a), "後半", f(b))
