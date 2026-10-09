# 注(L-920、2026-10-09): 口座の bp(取引の行の pnl_bp)は廃止した。この台本は廃止前の列・出力を読む調べの記録で、今の出力では動かない。
# リードが書いた。委任・批評家を通していない(数えるだけ)。L-915 の調べ(円 → bp → 円 の往復の影響)。
# 読み口 scripts/analysis/diag_tables.py の D1・D3・D6・D7 を、本ごとに 2 通りで計算して葉ごとに突き合わせる:
#   (a) 今のとおり pnl_bp(= pnl_jpy ÷ 200,000 × 10,000)で計算し、× 20 で円に戻した値
#   (b) 同じ関数に pnl_jpy をそのまま渡して計算した値(往復なし)
# 日の塊の選び直しは種が同じなので、両者の違いは浮動小数の丸めだけのはず。違いの最大と、文書の表示の桁(円の整数・小数 1 桁)で文字が変わる葉の数を出す。
# 使い方(リポジトリの根から): PYTHONPATH=src:scripts/analysis python3 docs/RESEARCH/matilda_main/unit_roundtrip_check.py > docs/RESEARCH/matilda_main/unit_roundtrip_check.out
import csv
import gzip
import os
import sys

sys.path.insert(0, "scripts/analysis")
import diag_tables as dt  # noqa: E402

T = "backtest_runs_shared/matilda_main_trades/"
CUT = "2019-12-09"


def load_yen(d):
    run = dt.load_run(d)  # d0・summary などはそのまま
    rows = []
    with gzip.open(os.path.join(d, "trades.csv.gz"), "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("in_measure", "True") == "False":
                continue
            t = {"entry_ns": dt._iso_ns(r["entry_t"]), "exit_ns": dt._iso_ns(r["exit_t"]), "pnl_bp": float(r["pnl_jpy"])}
            for k in ("exit_reason", "strength", "signal_t"):
                if k in r:
                    t[k] = r[k]
            rows.append(t)
    rows.sort(key=lambda t: (t["entry_ns"], t["exit_ns"]))
    run["trades"] = rows
    return run


def results(run, base):
    daily = dt.daily_series(run)
    out = {"d1": dt.d1(daily, CUT), "d3": dt.d3(run, daily), "d6": dt.d6(run, daily)}
    if base is not None:
        out["d7"] = dt.d7(run, base)
    return out


def leaves(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from leaves(v, f"{path}.{k}")
    elif isinstance(o, (list, tuple)):
        for i, v in enumerate(o):
            yield from leaves(v, f"{path}[{i}]")
    else:
        yield path, o


runs = sorted(x for x in os.listdir(T) if os.path.isdir(T + x))
if len(sys.argv) > 1:  # 本を絞る(字が変わった葉の中身を見るとき)
    runs = sys.argv[1:]
flips = []
base_bp, base_y = dt.load_run(T + "base"), load_yen(T + "base")
tot = {"leaves": 0, "money": 0, "same": 0, "other": 0, "digit0": 0, "digit1": 0, "maxabs": 0.0}
others = []
print("| 本 | 葉 | 円の量 | 倍率 1 の量(数・日・割合) | どちらでもない | 円の最大の差 | 整数の円で字が変わる | 小数 1 桁で字が変わる |")
print("|---|---|---|---|---|---|---|---|")
for n in runs:
    rb = results(dt.load_run(T + n), None if n == "base" else base_bp)
    ry = results(load_yen(T + n), None if n == "base" else base_y)
    lb, ly = dict(leaves(rb)), dict(leaves(ry))
    c = {"leaves": 0, "money": 0, "same": 0, "other": 0, "digit0": 0, "digit1": 0, "maxabs": 0.0}
    for k, vb in lb.items():
        vy = ly.get(k)
        if not isinstance(vb, (int, float)) or isinstance(vb, bool) or vb is None or vy is None:
            continue
        c["leaves"] += 1
        if vb == vy:
            c["same"] += 1
            continue
        if abs(vy - vb * 20) <= 1e-6 * max(1.0, abs(vy)):
            c["money"] += 1
            c["maxabs"] = max(c["maxabs"], abs(vy - vb * 20))
            d0, d1 = f"{vb * 20:+,.0f}" != f"{vy:+,.0f}", f"{vb * 20:+,.1f}" != f"{vy:+,.1f}"
            c["digit0"] += d0
            c["digit1"] += d1
            if d0 or d1:
                flips.append((n, k, vb * 20, vy))
        else:
            c["other"] += 1
            others.append((n, k, vb, vy))
    for k in tot:
        tot[k] = max(tot[k], c[k]) if k == "maxabs" else tot[k] + c[k]
    print(f"| {n} | {c['leaves']:,} | {c['money']:,} | {c['same']:,} | {c['other']:,} | {c['maxabs']:.3g} | {c['digit0']} | {c['digit1']} |")
print(f"| 計 | {tot['leaves']:,} | {tot['money']:,} | {tot['same']:,} | {tot['other']:,} | {tot['maxabs']:.3g} | {tot['digit0']} | {tot['digit1']} |")
print("\nどちらでもない葉(円の量でも倍率 1 の量でもない。中身を見る):")
for n, k, vb, vy in others[:200]:
    print(f"- {n} {k}: bp の計算 {vb!r} / 円の計算 {vy!r} / 比 {vy / vb if vb else float('nan'):.6g}")
print(f"(全 {len(others)} 件)")
print("\n表示の桁で字が変わった葉(bp × 20 / 円から直接):")
for n, k, a, b in flips:
    print(f"- {n} {k}: {a!r} / {b!r}")
print(f"(全 {len(flips)} 件)")
