"""リードが書いた(L-925、数えるだけ)。分析の文書の「差の出所を保有の帯で分ける」文は、fam_tables.md の丸めた 1 日あたりの差で書いていた。
丸める前の値で差を取り直す。計算は fam_tables.py の「D3 保有 0 分の帯と 0 分超 の前半・後半」と同じ(本ごとの期間の日、取引の無い日は 0 円、
境 2019-12-09、出の時刻の UTC の日)。円/日。
    PYTHONPATH=src python3 docs/RESEARCH/matilda_main/band_diff_exact.py <本> [...] > docs/RESEARCH/matilda_main/band_diff_exact.out
"""
import sys

sys.path.insert(0, "scripts/analysis")
import diag_tables as dt  # noqa: E402

T = "backtest_runs_shared/matilda_main_trades/"
CUT = "2019-12-09"
SEL = (("0 分", lambda t: t["exit_ns"] <= t["entry_ns"]), ("0 分超", lambda t: t["exit_ns"] > t["entry_ns"]))


def bands(n):
    run = dt.load_run(T + n)
    days = dt.period_days(run)
    out = {}
    for grp, sel in SEL:
        d = {x: 0.0 for x in days}
        for t in run["trades"]:
            k = dt.utc_day(t["exit_ns"])
            if sel(t) and k in d:
                d[k] += t["pnl_jpy"]
        for half, keep in (("前半", lambda x: x < CUT), ("後半", lambda x: x >= CUT)):
            v = [d[x] for x in days if keep(x)]
            out[(grp, half)] = sum(v) / len(v)
    return out


base = bands("base")
print("| 本 | 半分 | 0 分 本 | 0 分 基準 | 0 分 差 | 0 分超 本 | 0 分超 基準 | 0 分超 差 | 2 つの帯の差の和 |")
print("|---|---|---|---|---|---|---|---|---|")
for n in sys.argv[1:]:
    b = bands(n)
    for half in ("前半", "後半"):
        z = b[("0 分", half)] - base[("0 分", half)]
        o = b[("0 分超", half)] - base[("0 分超", half)]
        print(f"| {n} | {half} | {b[('0 分', half)]:+.1f} | {base[('0 分', half)]:+.1f} | {z:+.1f} | "
              f"{b[('0 分超', half)]:+.1f} | {base[('0 分超', half)]:+.1f} | {o:+.1f} | {z + o:+.1f} |")
