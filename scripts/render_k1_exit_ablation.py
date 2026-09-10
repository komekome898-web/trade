"""第 7 部(手 3: 決済ルールのアブレーション)の表を `exit_ablation.json` と
`signal_horizon.json` から生成する(手打ちしない)。

    python scripts/render_k1_exit_ablation.py --gate s19/b24
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
K1 = REPO / "docs" / "PHASE2" / "K1"
LABEL = {"strong": "強い", "weak": "弱い", "both": "両方"}
MODES = ("fixed_h3", "full", "invalid_only", "opposite_only")
MODE_LABEL = {"fixed_h3": "3 本固定", "full": "原典(第 2 部)", "invalid_only": "無効化のみ",
              "opposite_only": "反対シグナルのみ"}


def star(c):
    lo, hi = c["ci95_bp"]
    return "*" if (lo > 0 or hi < 0) else ""


def fmt(c):
    if not c:
        return "—"
    s = star(c)
    v = f"{c['mean_bp']:+.2f}{s}"
    return f"**{v}**" if s else v


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate", default="s19/b24")
    ap.add_argument("--dir", default=str(K1), help="JSON のあるディレクトリ")
    args = ap.parse_args()
    A = json.loads((Path(args.dir) / "exit_ablation.json").read_text("utf-8"))
    S = json.loads((Path(args.dir) / "signal_horizon.json").read_text("utf-8"))["cells"]
    C = A["cells"]
    years = sorted({y for c in C.values() for y in c["per_year"]})   # 年はデータから取る
    rg = A["reproduction_gate"]
    print(f"再現ゲート: {sum(r['ok'] for r in rg)}/{len(rg)} 一致(`full` が `effect.json` の全セルと n・平均で一致)\n")

    print(f"### 表 I — 門 `{args.gate}`: 平均 bp\n")
    print("| 足 | 強さ | 第 4 部 h=3(全シグナル独立) | " + " | ".join(MODE_LABEL[m] for m in MODES) + " |")
    print("|---|---|---|" + "---|" * len(MODES))
    for foot in (1, 3, 5, 15, 30, 60):
        for s in ("strong", "weak", "both"):
            p4 = S.get(f"{foot}|{args.gate}|{s}|3")
            cells = [C.get(f"{m}|{foot}|{args.gate}|{s}") for m in MODES]
            print(f"| {foot} 分 | {LABEL[s]} | {fmt(p4)} | " + " | ".join(fmt(c) for c in cells) + " |")

    print(f"\n### 表 J — 門 `{args.gate}`: 取引数 / 保有本数の中央値\n")
    print("| 足 | 強さ | 第 4 部 n | " + " | ".join(MODE_LABEL[m] for m in MODES) + " |")
    print("|---|---|---|" + "---|" * len(MODES))
    for foot in (1, 3, 5, 15, 30, 60):
        for s in ("strong", "weak", "both"):
            p4 = S.get(f"{foot}|{args.gate}|{s}|3")
            cells = [C.get(f"{m}|{foot}|{args.gate}|{s}") for m in MODES]
            print(f"| {foot} 分 | {LABEL[s]} | {p4['n']:,} | " if p4 else f"| {foot} 分 | {LABEL[s]} | — | ", end="")
            print(" | ".join(f"{c['n']:,} / {c['hold_median']}" if c else "—" for c in cells) + " |")

    print(f"\n### 表 K' — 門 `{args.gate}`: 散らばりと分位(bp)。損切りの無い変種の裾を見る\n")
    print("| 足 | 強さ | 変種 | 平均 | sd | p05 | p50 | p95 | 最小 | 最大 |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for foot in (3, 5, 15, 30):
        for s in ("strong", "weak"):
            for m in MODES:
                c = C.get(f"{m}|{foot}|{args.gate}|{s}")
                if not c or "quantiles_bp" not in c:
                    continue
                q = c["quantiles_bp"]
                print(f"| {foot} 分 | {LABEL[s]} | {MODE_LABEL[m]} | {c['mean_bp']:+.2f} | {c['sd_bp']} | "
                      f"{q['p05']:+.1f} | {q['p50']:+.1f} | {q['p95']:+.1f} | {c['min_bp']:+.0f} | {c['max_bp']:+.0f} |")

    print(f"\n### 表 L — 門 `{args.gate}`: 年ごとの平均({' / '.join(years)})\n")
    print("| 足 | 強さ | 変種 | " + " | ".join(years) + " |")
    print("|---|---|---|" + "---|" * len(years))
    for foot in (3, 5, 15, 30):
        for s in ("strong", "weak"):
            for m in ("full", "opposite_only"):
                c = C.get(f"{m}|{foot}|{args.gate}|{s}")
                if not c:
                    continue
                py = c["per_year"]
                print(f"| {foot} 分 | {LABEL[s]} | {MODE_LABEL[m]} | " + " | ".join(
                    f"{py[y]['mean_bp']:+.2f} (n={py[y]['n']:,})" if y in py else "—" for y in years) + " |")

    print(f"\n### 表 K — 門 `{args.gate}`: 差の分解(bp)\n")
    print("母集団の差 = 3 本固定 − 第 4 部 h=3 / 決済ルールの差 = 原典 − 3 本固定\n")
    print("| 足 | 強さ | 母集団の差 | 決済ルールの差 | 合計(原典 − 第 4 部) |")
    print("|---|---|---|---|---|")
    for foot in (1, 3, 5, 15, 30, 60):
        for s in ("strong", "weak", "both"):
            p4 = S.get(f"{foot}|{args.gate}|{s}|3")
            fx = C.get(f"fixed_h3|{foot}|{args.gate}|{s}")
            fu = C.get(f"full|{foot}|{args.gate}|{s}")
            if not (p4 and fx and fu):
                continue
            a = fx["mean_bp"] - p4["mean_bp"]
            b = fu["mean_bp"] - fx["mean_bp"]
            print(f"| {foot} 分 | {LABEL[s]} | {a:+.2f} | {b:+.2f} | {a + b:+.2f} |")


if __name__ == "__main__":
    main()
