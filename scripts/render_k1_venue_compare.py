"""第 8 部(K1-B: Binance 現物で同条件・同方法)の分析表を生成する(手打ちしない)。

読むもの:
    docs/PHASE2/K1/signal_horizon.json           … BitMEX 2017-2019(第 4 部)
    docs/PHASE2/K1/binance/signal_horizon.json   … Binance 2017-08-17〜2026-08-31
    docs/PHASE2/K1/binance/body_wick.json        … 第 5 部 表 E 相当(あれば)
    docs/PHASE2/K1/binance/exit_ablation.json    … 第 7 部相当(あれば)

出す表:
    表 M  年ごとの有意セルの割合と、強い/弱いの平均効果(§4.4 と同じ量)を **両取引所・全年**で
    表 N  門 s19/b24 の年ごとの符号付き平均(強い/弱い × h=1,2,3,5)を **両取引所横並び**
    表 O  年ごとの n(部分年を隠さない)
    表 P  Binance の実体の色だけの戻り(表 E 相当。body_wick.json に年別が無ければ全期間のみ)
    表 Q  Binance の決済変種の年ごとの平均(exit_ablation.json)

    python scripts/render_k1_venue_compare.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
K1 = REPO / "docs" / "PHASE2" / "K1"
LABEL = {"strong": "強い", "weak": "弱い", "both": "両方"}


def load(path):
    p = Path(path)
    return json.loads(p.read_text("utf-8")) if p.exists() else None


def sig(c):
    lo, hi = c["ci95_bp"]
    return lo > 0 or hi < 0


def fmt(mean, is_sig):
    v = f"{mean:+.2f}{'*' if is_sig else ''}"
    return f"**{v}**" if is_sig else v


def years_of(d):
    ys = set()
    for c in d["cells"].values():
        ys.update(c["per_year"].keys())
    return sorted(ys)


def table_m(venues):
    """年ごとの有意セルの割合(その年だけの区間)と、強い/弱いの平均効果。全門・全足・全 h。"""
    out = ["| 取引所 | 年 | セル数 | 有意 | うち正 | うち負 | 割合 | 強い 平均 | 弱い 平均 |",
           "|---|---|---|---|---|---|---|---|---|"]
    for name, d in venues:
        if not d:
            continue
        for y in years_of(d):
            rows = [(c["strength"], c["per_year"][y]) for c in d["cells"].values() if y in c["per_year"]]
            n = len(rows)
            s = [(st, p) for st, p in rows if p["ci95_bp"][0] > 0 or p["ci95_bp"][1] < 0]
            pos = sum(1 for _st, p in s if p["mean_bp"] > 0)
            st_mean = [p["mean_bp"] for st, p in rows if st == "strong"]
            wk_mean = [p["mean_bp"] for st, p in rows if st == "weak"]
            out.append(f"| {name} | {y} | {n} | {len(s)} | {pos} | {len(s) - pos} | {100 * len(s) / n:.1f}% | "
                       f"{sum(st_mean) / len(st_mean):+.2f} | {sum(wk_mean) / len(wk_mean):+.2f} |")
    return "\n".join(out)


def table_n(venues, gate, feet, hs):
    """門 gate の年ごとの符号付き平均を両取引所横並びで。"""
    all_years = sorted(set().union(*[set(years_of(d)) for _n, d in venues if d]))
    out = ["| 足 | 強さ | h | 取引所 | " + " | ".join(all_years) + " |",
           "|---|---|---|---|" + "---|" * len(all_years)]
    for foot in feet:
        for s in ("strong", "weak"):
            for h in hs:
                for name, d in venues:
                    if not d:
                        continue
                    c = d["cells"].get(f"{foot}|{gate}|{s}|{h}")
                    if not c:
                        continue
                    cells = []
                    for y in all_years:
                        p = c["per_year"].get(y)
                        cells.append(fmt(p["mean_bp"], p["ci95_bp"][0] > 0 or p["ci95_bp"][1] < 0) if p else "—")
                    out.append(f"| {foot} 分 | {LABEL[s]} | {h} | {name} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def table_o(venues, gate, feet):
    all_years = sorted(set().union(*[set(years_of(d)) for _n, d in venues if d]))
    out = ["| 足 | 強さ | 取引所 | " + " | ".join(all_years) + " |", "|---|---|---|" + "---|" * len(all_years)]
    for foot in feet:
        for s in ("strong", "weak"):
            for name, d in venues:
                if not d:
                    continue
                c = d["cells"].get(f"{foot}|{gate}|{s}|1")
                if not c:
                    continue
                out.append(f"| {foot} 分 | {LABEL[s]} | {name} | " + " | ".join(
                    f"{c['per_year'][y]['n']:,}" if y in c["per_year"] else "—" for y in all_years) + " |")
    return "\n".join(out)


def table_p(bw, h=3):
    """実体の色だけ(ヒゲの側を畳む)。符号なし。門 = all。年別があれば年別、無ければ全期間。"""
    if not bw:
        return "(binance/body_wick.json が無い)"
    C, B = bw["cells"], bw["baseline_unconditional"]
    ratios = ("[0,0.25)", "[0.25,0.5)", "[0.5,0.75)", "[0.75,1)", "[1,2)", "[2,+)")
    out = ["| 足 | 色 | " + " | ".join(ratios) + " | 相場 |", "|---|---|" + "---|" * (len(ratios) + 1)]
    for foot in (1, 3, 5, 15, 30, 60):
        b = B.get(f"{foot}|{h}")
        if not b:
            continue
        red, grn = [], []
        for r in ratios:
            wk = C.get(f"all|{foot}|*|{r}|weak|{h}")
            st = C.get(f"all|{foot}|*|{r}|strong|{h}")
            if not wk or not st or not wk["buy_n"] or not st["sell_n"]:
                red.append("—")
                grn.append("—")
                continue
            rv = (wk["buy_fwd_bp"] * wk["buy_n"] + st["sell_fwd_bp"] * st["sell_n"]) / (wk["buy_n"] + st["sell_n"])
            gv = (st["buy_fwd_bp"] * st["buy_n"] + wk["sell_fwd_bp"] * wk["sell_n"]) / (st["buy_n"] + wk["sell_n"])
            red.append(f"{rv:+.2f}")
            grn.append(f"{gv:+.2f}")
        out.append(f"| {foot} 分 | 陰線 | " + " | ".join(red) + f" | {b['mean_fwd_bp']:+.2f} |")
        out.append(f"| {foot} 分 | 陽線 | " + " | ".join(grn) + f" | {b['mean_fwd_bp']:+.2f} |")
    return "\n".join(out)


def table_q(ab, gate):
    if not ab:
        return "(binance/exit_ablation.json が無い)"
    C = ab["cells"]
    years = sorted({y for c in C.values() for y in c["per_year"]})
    label = {"fixed_h3": "3 本固定", "full": "原典", "invalid_only": "無効化のみ", "opposite_only": "反対シグナルのみ"}
    out = ["| 足 | 強さ | 変種 | 全期間 | " + " | ".join(years) + " |", "|---|---|---|---|" + "---|" * len(years)]
    for foot in (3, 5, 15, 30):
        for s in ("strong", "weak"):
            for m in ("full", "opposite_only", "fixed_h3", "invalid_only"):
                c = C.get(f"{m}|{foot}|{gate}|{s}")
                if not c:
                    continue
                out.append(f"| {foot} 分 | {LABEL[s]} | {label[m]} | {fmt(c['mean_bp'], sig(c))} | " + " | ".join(
                    f"{c['per_year'][y]['mean_bp']:+.2f}" if y in c["per_year"] else "—" for y in years) + " |")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate", default="s19/b24")
    args = ap.parse_args()
    bm = load(K1 / "signal_horizon.json")
    bn = load(K1 / "binance" / "signal_horizon.json")
    venues = [("BitMEX", bm), ("Binance", bn)]
    if not bn:
        print("(binance/signal_horizon.json が無い — 実装者の出力待ち)")
    print("### 表 M — 年ごとの有意セルの割合と平均効果(全門・全足・全 h。§4.4 と同じ量)\n")
    print("BitMEX の 2017 は 1 月から、Binance の 2017 は 8/17 から。**2017 は窓が違う。** 2026 は 8/31 まで。\n")
    print(table_m(venues))
    print(f"\n### 表 N — 門 `{args.gate}`: 年ごとの符号付き平均、両取引所横並び\n")
    print("`*` = その年だけで見た 95% 区間が 0 を跨がない。\n")
    print(table_n(venues, args.gate, (1, 3, 5, 15, 30, 60), (1, 2, 3, 5)))
    print(f"\n### 表 O — 門 `{args.gate}`: 年ごとの n(部分年を隠さない)\n")
    print(table_o(venues, args.gate, (1, 3, 5, 15, 30, 60)))
    print("\n### 表 P — Binance: 実体の色だけの戻り(第 5 部 表 E と同じ量。h=3、門なし、全期間)\n")
    print(table_p(load(K1 / "binance" / "body_wick.json")))
    print(f"\n### 表 Q — Binance: 決済変種の年ごとの平均(門 `{args.gate}`)\n")
    print(table_q(load(K1 / "binance" / "exit_ablation.json"), args.gate))


if __name__ == "__main__":
    main()
