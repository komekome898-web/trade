# 注(L-920、2026-10-09): 口座の bp(取引の行の pnl_bp)は廃止した。この台本は廃止前の列・出力を読む調べの記録で、今の出力では動かない。
# リードが書いた。委任・批評家を通していない(数えるだけ)。L-917 の調べ(計算の途中の bp)。
# 族の台本(half_diff.py・both_halves.py・same_bar_daily.py・foot/foot_boundary.py・fam_tables.py の D3 の帯)は、
# 読み口の pnl_bp(= pnl_jpy ÷ 200,000 × 10,000)で日ごとの和・平均・区間・MDE を計算し、表示のときに × 20 する。
# 同じ計算を pnl_jpy(円)のままで行い、× 20 した値と、文書の桁(円の整数・小数 1 桁)で字が変わるかを数える。
# 計算: 32 本それぞれについて (1) 前半・後半(境 2019-12-09 と、本の日の真ん中)の 1 日あたり (2) 基準との日ごとの差の前半・後半
#       (共通の日の真ん中で分ける = half_diff、境 2019-12-09 = both_halves)(3) 保有 0 分 / 0 分超 の帯ごとの前半・後半(fam_tables・same_bar_daily)
#       (4) 境 2019-12-10(foot_boundary)。どれも dt.mean_ci(日の塊の区間・MDE)。
# 使い方(リポジトリの根から): PYTHONPATH=src python3 docs/RESEARCH/matilda_main/calc_path_check.py > docs/RESEARCH/matilda_main/calc_path_check.out
import os
import sys

sys.path.insert(0, "scripts/analysis")
import diag_tables as dt  # noqa: E402
import csv  # noqa: E402
import gzip  # noqa: E402


def load_yen(d):
    """unit_roundtrip_check.py の load_yen と同じ(取り込むと向こうの全体が走るので写した): pnl_bp の欄に pnl_jpy を入れる。"""
    run = dt.load_run(d)
    rows = []
    with gzip.open(os.path.join(d, "trades.csv.gz"), "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("in_measure", "True") == "False":
                continue
            rows.append({"entry_ns": dt._iso_ns(r["entry_t"]), "exit_ns": dt._iso_ns(r["exit_t"]), "pnl_bp": float(r["pnl_jpy"])})
    rows.sort(key=lambda t: (t["entry_ns"], t["exit_ns"]))
    run["trades"] = rows
    return run

T = "backtest_runs_shared/matilda_main_trades/"
runs = sorted(x for x in os.listdir(T) if os.path.isdir(T + x))


def daily(run, sel=None):
    out = {d: 0.0 for d in dt.period_days(run)}
    for t in run["trades"]:
        if sel is None or sel(t):
            k = dt.utc_day(t["exit_ns"])
            if k in out:
                out[k] += t["pnl_bp"]
    return out


SEL = {"全部": None, "0 分": lambda t: t["exit_ns"] <= t["entry_ns"], "0 分超": lambda t: t["exit_ns"] > t["entry_ns"]}


def stats(run, base):
    res = {}
    for sn, sel in SEL.items():
        d = daily(run, sel)
        days = sorted(d)
        for cut in ("2019-12-09", "2019-12-10", "mid"):
            if cut == "mid":
                h = len(days) // 2
                a, b = days[:h], days[h:]
            else:
                a, b = [x for x in days if x < cut], [x for x in days if x >= cut]
            res[(sn, cut, "前半")] = dt.mean_ci([d[x] for x in a])
            res[(sn, cut, "後半")] = dt.mean_ci([d[x] for x in b])
        if base is not None:
            bd = daily(base, sel)
            c = sorted(set(d) & set(bd))
            diff = [d[x] - bd[x] for x in c]
            h = len(c) // 2
            res[(sn, "差 mid", "前半")] = dt.mean_ci(diff[:h])
            res[(sn, "差 mid", "後半")] = dt.mean_ci(diff[h:])
            res[(sn, "差 2019-12-09", "前半")] = dt.mean_ci([d[x] - bd[x] for x in c if x < "2019-12-09"])
            res[(sn, "差 2019-12-09", "後半")] = dt.mean_ci([d[x] - bd[x] for x in c if x >= "2019-12-09"])
    return res


bb, by = dt.load_run(T + "base"), load_yen(T + "base")
tot = {"値": 0, "整数で字が変わる": 0, "小数 1 桁で字が変わる": 0, "最大の差(円)": 0.0}
flips = []
for n in runs:
    rb = stats(dt.load_run(T + n), None if n == "base" else bb)
    ry = stats(load_yen(T + n), None if n == "base" else by)
    for k, vb in rb.items():
        vy = ry[k]
        for f in ("mean", "lo", "hi", "mde"):
            if vb.get(f) is None:
                continue
            a, b = vb[f] * 20, vy[f]
            tot["値"] += 1
            tot["最大の差(円)"] = max(tot["最大の差(円)"], abs(a - b))
            d0, d1 = f"{a:+,.0f}" != f"{b:+,.0f}", f"{a:+,.1f}" != f"{b:+,.1f}"
            tot["整数で字が変わる"] += d0
            tot["小数 1 桁で字が変わる"] += d1
            if d0 or d1:
                flips.append((n, k, f, a, b))
print("| 本の数 | 値 | 整数で字が変わる | 小数 1 桁で字が変わる | 最大の差(円) |\n|---|---|---|---|---|")
print(f"| {len(runs)} | {tot['値']:,} | {tot['整数で字が変わる']} | {tot['小数 1 桁で字が変わる']} | {tot['最大の差(円)']:.3g} |")
print("\n字が変わった値(bp で計算して × 20 / 円のまま計算):")
for x in flips:
    print("-", x)
print(f"(全 {len(flips)} 件)")
