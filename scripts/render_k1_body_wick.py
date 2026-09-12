"""第 5 部(手 1: 実体とヒゲの層別)の表を `body_wick.json` から生成する(手打ちしない)。

    python scripts/render_k1_body_wick.py > /tmp/part5_tables.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
K1 = REPO / "results" / "PHASE2" / "K1"
SRC = K1 / "body_wick.json"
RATIOS = ("[0,0.25)", "[0.25,0.5)", "[0.5,0.75)", "[0.75,1)", "[1,2)", "[2,+)")
WICKS = ("[0,5)", "[5,10)", "[10,19)", "[19,24)", "[24,40)", "[40,70)", "[70,+)")
FEET = (1, 3, 5, 15, 30, 60)
LABEL = {"strong": "強い", "weak": "弱い"}


def star(c):
    lo, hi = c["ci95_bp"]
    return "*" if (lo > 0 or hi < 0) else ""


def fmt(c):
    if not c:
        return "—"
    s = star(c)
    v = f"{c['mean_bp']:+.2f}{s}"
    return f"**{v}**" if s else v


def ratio_marginal(d, gate, h):
    C, B = d["cells"], d["baseline_unconditional"]
    out = [f"| 足 | 強さ | " + " | ".join(RATIOS) + " | 全体 | 相場 |",
           "|---|---|" + "---|" * (len(RATIOS) + 2)]
    for foot in FEET:
        m = B[f"{foot}|{h}"]["mean_fwd_bp"]
        for s in ("strong", "weak"):
            row = [fmt(C.get(f"{gate}|{foot}|*|{r}|{s}|{h}")) for r in RATIOS]
            tot = fmt(C.get(f"{gate}|{foot}|*|*|{s}|{h}"))
            out.append(f"| {foot} 分 | {LABEL[s]} | " + " | ".join(row) + f" | {tot} | {m:+.2f} |")
    return "\n".join(out)


def wick_marginal(d, gate, h):
    C, B = d["cells"], d["baseline_unconditional"]
    out = [f"| 足 | 強さ | " + " | ".join(WICKS) + " | 相場 |",
           "|---|---|" + "---|" * (len(WICKS) + 1)]
    for foot in FEET:
        m = B[f"{foot}|{h}"]["mean_fwd_bp"]
        for s in ("strong", "weak"):
            row = [fmt(C.get(f"{gate}|{foot}|{w}|*|{s}|{h}")) for w in WICKS]
            out.append(f"| {foot} 分 | {LABEL[s]} | " + " | ".join(row) + f" | {m:+.2f} |")
    return "\n".join(out)


def contribution(d, gate, h, s):
    C = d["cells"]
    out = ["| 足 | 全体 n | 全体平均 | 実体>ヒゲ の n | 割合 | 実体>ヒゲ 平均 | 実体<ヒゲ 平均 | 実体>ヒゲ の寄与 | 寄与率 |",
           "|---|---|---|---|---|---|---|---|---|"]
    for foot in FEET:
        tot = C.get(f"{gate}|{foot}|*|*|{s}|{h}")
        big = [C.get(f"{gate}|{foot}|*|{r}|{s}|{h}") for r in ("[1,2)", "[2,+)")]
        big = [b for b in big if b]
        if not tot or not big:
            continue
        nb = sum(b["n"] for b in big)
        sb = sum(b["n"] * b["mean_bp"] for b in big)
        ns = tot["n"] - nb
        ss = tot["n"] * tot["mean_bp"] - sb
        contrib = sb / tot["n"]
        share = f"{100 * contrib / tot['mean_bp']:.0f}%" if tot["mean_bp"] else "—"
        out.append(f"| {foot} 分 | {tot['n']:,} | {tot['mean_bp']:+.2f} | {nb:,} | {100 * nb / tot['n']:.1f}% | "
                   f"{sb / nb:+.2f} | {ss / ns:+.2f} | {contrib:+.2f} | {share} |")
    return "\n".join(out)


def body_only(d, h):
    """実体の色だけ(ヒゲの側を畳む)。符号なし。門 = all。"""
    C, B = d["cells"], d["baseline_unconditional"]
    out = ["| 足 | 色 | " + " | ".join(RATIOS) + " | 相場 |", "|---|---|" + "---|" * (len(RATIOS) + 1)]
    for foot in FEET:
        m = B[f"{foot}|{h}"]["mean_fwd_bp"]
        red, grn = [], []
        for r in RATIOS:
            wk = C.get(f"all|{foot}|*|{r}|weak|{h}")
            st = C.get(f"all|{foot}|*|{r}|strong|{h}")
            if not wk or not st:
                red.append("—")
                grn.append("—")
                continue
            rv = (wk["buy_fwd_bp"] * wk["buy_n"] + st["sell_fwd_bp"] * st["sell_n"]) / (wk["buy_n"] + st["sell_n"])
            gv = (st["buy_fwd_bp"] * st["buy_n"] + wk["sell_fwd_bp"] * wk["sell_n"]) / (st["buy_n"] + wk["sell_n"])
            red.append(f"{rv:+.2f}")
            grn.append(f"{gv:+.2f}")
        out.append(f"| {foot} 分 | 陰線 | " + " | ".join(red) + f" | {m:+.2f} |")
        out.append(f"| {foot} 分 | 陽線 | " + " | ".join(grn) + f" | {m:+.2f} |")
    return "\n".join(out)


def wick_side_diff(d, h):
    """実体の色を固定してヒゲの側だけを変えた差(下ヒゲ − 上ヒゲ)。門 = all。区間は無い。"""
    C = d["cells"]
    cols = ("[0,0.25)", "[1,2)", "[2,+)")
    out = ["| 足 | h | 実体小 `[0,0.25)` 陰線 | 同 陽線 | 実体大 `[1,2)` 陰線 | 同 陽線 | 実体大 `[2,+)` 陰線 | 同 陽線 |",
           "|---|---|---|---|---|---|---|---|"]
    n_small = n_large = n_rows = 0
    for foot in FEET:
        for hh in (1, 2, 3, 5):
            vals = []
            for r in cols:
                wk = C.get(f"all|{foot}|*|{r}|weak|{hh}")
                st = C.get(f"all|{foot}|*|{r}|strong|{hh}")
                if not wk or not st:
                    vals.append(None)
                    continue
                vals.append((wk["buy_fwd_bp"] - st["sell_fwd_bp"], st["buy_fwd_bp"] - wk["sell_fwd_bp"]))
            if any(v is None for v in vals):
                continue
            n_rows += 1
            n_small += vals[0][0] > 0 and vals[0][1] > 0
            n_large += all(x < 0 for v in vals[1:] for x in v)
            out.append(f"| {foot} 分 | {hh} | " + " | ".join(f"{a:+.2f} | {b:+.2f}" for a, b in vals) + " |")
    out.append("")
    out.append(f"**{n_rows} 行中: 実体小で両色とも 差 > 0 が {n_small} 行 / 実体大で 4 つとも 差 < 0 が {n_large} 行。**")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", default=None)
    ap.add_argument("--dir", default=str(K1), help="JSON のあるディレクトリ(--src が無いとき)")
    ap.add_argument("--h", type=int, default=3)
    args = ap.parse_args()
    if args.src is None:
        args.src = str(Path(args.dir) / "body_wick.json")
    d = json.loads(Path(args.src).read_text("utf-8"))
    h = args.h
    rg = d["reproduction_gate"]
    print(f"再現ゲート: {sum(r['ok'] for r in rg)}/{len(rg)} 一致(層を全部合わせた `s19/b24` が "
          f"`signal_horizon.json` と n・平均で一致)\n")
    print(f"### 表 A — 実体比の周辺(ヒゲ長を畳む)。門 `s19/b24`、h={h}\n")
    print(ratio_marginal(d, "s19/b24", h))
    print(f"\n### 表 B — 同、門なし(向きが決まる全足)\n")
    print(ratio_marginal(d, "all", h))
    print(f"\n### 表 C — ヒゲ長の周辺(実体比を畳む)。門なし、h={h}\n")
    print(wick_marginal(d, "all", h))
    print(f"\n### 表 D — 「強い」の負のうち、実体 > ヒゲ の足の寄与。門 `s19/b24`、h={h}\n")
    print(contribution(d, "s19/b24", h, "strong"))
    print(f"\n### 表 E — 実体の色だけ(ヒゲの側を畳む)。符号なしの h={h} 本先、門なし\n")
    print(body_only(d, h))
    print(f"\n### 表 F — 実体の色を固定してヒゲの側だけ変えた差(下ヒゲ − 上ヒゲ、bp)。門なし\n")
    print("**区間は無い**(別セルの平均の差)。一貫性で読む。\n")
    print(wick_side_diff(d, h))


if __name__ == "__main__":
    main()
