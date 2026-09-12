"""第 4 部の**年ごとの表**を `signal_horizon.json` から生成する(手打ちしない)。

規約 `.claude/skills/research-protocol` §1.2「数字は生成であって入力ではない」。
2026-09-09、オーナー「年ごとのデータも表にして見せてください」への対応。

出す表は 2 種類 × 門の数:

    表 1  符号付き平均(年 × ホライズン)。`*` = 95% 区間が 0 を跨がない
    表 2  ある h での年ごとの分解(買い側 / 売り側 / 相場 / 両側の超過が同符号か)

**表 1 は族の全ホライズンを載せる。** 選ばない(2026-09-09 に「代表」と書いて
13 門のうち 6 行しか載せなかった事故の再発防止)。

    python scripts/render_k1_year_tables.py --gates s19/b24 s-/b- --split-h 3
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
K1 = REPO / "results" / "PHASE2" / "K1"
SRC = K1 / "signal_horizon.json"

# 相場の列は BitMEX 2017-2019 の表のために書いたもの。他の `--dir` では出さない(手打ちしない)
MARKET_BITMEX = {"2017": "+1335%", "2018": "**−73%**", "2019": "+94%"}
MARKET = MARKET_BITMEX
LABEL = {"strong": "強い", "weak": "弱い", "both": "両方"}


def years_of(d):
    """年はデータから取る(2017-2019 のハードコードをしない)。"""
    return tuple(sorted({y for c in d["cells"].values() for y in c["per_year"]}))


def fmt(v, digits=2, plus=True):
    if v is None:
        return "—"
    return f"{v:+.{digits}f}" if plus else f"{v:.{digits}f}"


def table1(d, gate, feet, horizons, strengths):
    """符号付き平均。行 = 足 × 強さ × 年、列 = ホライズン。"""
    C = d["cells"]
    out = [f"| 足 | 強さ | 年 | 相場 | n | 日数 | "
           + " | ".join(f"h={h}" for h in horizons) + " |",
           "|---|---|---|---|---|---|" + "---|" * len(horizons)]
    for foot in feet:
        for st in strengths:
            for y in years_of(d):
                key0 = f"{foot}|{gate}|{st}|{horizons[0]}"
                if key0 not in C or y not in C[key0]["per_year"]:
                    continue
                py0 = C[key0]["per_year"][y]
                cells = []
                for h in horizons:
                    c = C.get(f"{foot}|{gate}|{st}|{h}")
                    if not c or y not in c["per_year"]:
                        cells.append("—")
                        continue
                    p = c["per_year"][y]
                    lo, hi = p["ci95_bp"]
                    star = "*" if (lo > 0 or hi < 0) else ""
                    cells.append(f"**{fmt(p['mean_bp'])}{star}**" if star
                                 else fmt(p["mean_bp"]))
                out.append(f"| {foot} 分 | {LABEL[st]} | {y} | {MARKET.get(y, '—')} | "
                           f"{py0['n']:,} | {py0['days']} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def table2(d, gate, feet, h, strengths):
    """年ごとの分解。買い側 / 売り側 は**符号なし**、相場は全足の無条件平均。"""
    C, B = d["cells"], d["baseline_unconditional"]
    out = ["| 足 | 強さ | 年 | 符号付き平均 | 買い側 | 売り側 | 相場 | 買い側超過 | 売り側超過 | 同符号 |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for foot in feet:
        for st in strengths:
            c = C.get(f"{foot}|{gate}|{st}|{h}")
            b = B.get(f"{foot}|{h}")
            if not c or not b:
                continue
            for y in years_of(d):
                if y not in c["per_year"] or y not in b.get("per_year", {}):
                    continue
                p = c["per_year"][y]
                m = b["per_year"][y]["mean_fwd_bp"]
                bf, sf = p["buy_fwd_bp"], p["sell_fwd_bp"]
                if bf is None or sf is None:
                    continue
                eb, es = bf - m, m - sf
                lo, hi = p["ci95_bp"]
                star = "*" if (lo > 0 or hi < 0) else ""
                out.append(
                    f"| {foot} 分 | {LABEL[st]} | {y} | {fmt(p['mean_bp'])}{star} | "
                    f"{fmt(bf)} | {fmt(sf)} | {fmt(m)} | {fmt(eb)} | {fmt(es)} | "
                    f"{'◎' if eb * es > 0 else '×'} |")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", default=None)
    ap.add_argument("--dir", default=str(K1), help="JSON のあるディレクトリ(--src が無いとき)")
    ap.add_argument("--gates", nargs="+", default=["s19/b24", "s-/b-"])
    ap.add_argument("--strengths", nargs="+", default=["strong", "weak"])
    ap.add_argument("--split-h", type=int, default=3)
    args = ap.parse_args()
    if args.src is None:
        args.src = str(Path(args.dir) / "signal_horizon.json")
    global MARKET
    if Path(args.dir).resolve() != K1.resolve():
        MARKET = {}

    d = json.loads(Path(args.src).read_text("utf-8"))
    feet = d["family"]["feet"]
    horizons = d["family"]["horizons"]

    for gate in args.gates:
        name = "当時の規則" if gate == "s19/b24" else "門を課さない"
        print(f"\n### 門 `{gate}`({name})— 符号付き平均 bp\n")
        print("`*` = その年だけで見た 95% 区間が 0 を跨がない"
              "(日単位ブロックブートストラップ、200 回)\n")
        print(table1(d, gate, feet, horizons, args.strengths))
        print(f"\n### 門 `{gate}` — h={args.split_h} での年ごとの分解\n")
        print("買い側・売り側は**符号なし**の先の値動き。"
              "超過 = 買い側 − 相場 / 相場 − 売り側。**◎ = 両側の超過が同符号**\n")
        print(table2(d, gate, feet, args.split_h, args.strengths))


if __name__ == "__main__":
    main()
