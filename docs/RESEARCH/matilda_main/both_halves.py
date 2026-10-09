"""リードが書いた。委任・批評家を通していない(数えるだけ)。段 1 の 31 本の、基準との同じ日どうしの差の前半・後半(境 2019-12-09、円/日 [区間]。読み口の mean_ci)。相方の break_len_mult D9b の指摘 2。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/both_halves.py > docs/RESEARCH/matilda_main/both_halves.out
"""
import sys, os
sys.path.insert(0, "scripts/analysis")
import diag_tables as dt
T = "backtest_runs_shared/matilda_main_trades/"
CUT = "2019-12-09"
bd = dt.daily_series(dt.load_run(T + "base"))
for n in sorted(os.listdir(T)):
    if n == "base": continue
    rd = dt.daily_series(dt.load_run(T + n))
    c = sorted(set(rd) & set(bd))
    a = dt.mean_ci([rd[x] - bd[x] for x in c if x < CUT]); b = dt.mean_ci([rd[x] - bd[x] for x in c if x >= CUT])
    f = lambda r: f"{r['mean']*20:+.0f} [{r['lo']*20:+.0f}, {r['hi']*20:+.0f}]"
    tag = "両半分 正" if a['lo'] > 0 and b['lo'] > 0 else ("両半分 負" if a['hi'] < 0 and b['hi'] < 0 else "")
    print(n, "| 前半", f(a), "| 後半", f(b), "|", tag)
