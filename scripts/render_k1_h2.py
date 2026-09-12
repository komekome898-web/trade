"""第 11 部(H2a、2 × 2)の表を 4 つの機構 JSON から生成する(手打ちしない)。

読むもの(両取引所): `effect.json`(原典)/ `effect_flipbody.json`(H1)/ `effect_noinval.json`(H2a)/
`effect_flip_noinval.json`(H1 + H2a)。`H2_PREREG.md` §3:
    (a) 4 マス横並び 足 × 門 13 × 強さ 3(平均・区間・sd・p05・p50・p95・保有・n)
    (b) 交互作用 = (H1+H2a) − H1 − H2a + 原典(全セル、符号と大きさ。区間なし = 判定に使わない)
    (c) 門 `s19/b24` の年別 4 マス
    (d) 決済理由の内訳(門 `s19/b24`)

    PYTHONPATH=src:scripts python scripts/render_k1_h2.py > results/PHASE2/K1/H2_TABLES.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
K1 = REPO / "results" / "PHASE2" / "K1"
VENUES = (("BitMEX", K1), ("Binance", K1 / "binance"))
FEET = (1, 3, 5, 15, 30, 60)
STRENGTHS = (("both", "両方"), ("weak", "弱い"), ("strong", "強い"))
ARMS = (("base", "原典", "effect.json"), ("h1", "H1", "effect_flipbody.json"),
        ("h2", "H2a", "effect_noinval.json"), ("h12", "H1+H2a", "effect_flip_noinval.json"))


def load(dirpath):
    out = {}
    for key, _lab, name in ARMS:
        p = dirpath / name
        out[key] = json.loads(p.read_text("utf-8")) if p.exists() else None
    return out


def star(ci):
    return "*" if ci and ci[0] == ci[0] and (ci[0] > 0 or ci[1] < 0) else ""


def f(x, d=2):
    return "—" if x is None else f"{x:+.{d}f}"


def cell(d, key, ft, g, st):
    return d[key]["cells"].get(f"{ft}|{g}|{st}") if d[key] else None


def q(c, k):
    return c.get("quantiles_bp", {}).get(k)


def t_grid(name, d):
    gates = d["base"]["family"]["gates"]
    print(f"### 表 J-a ({name}) — 4 マス横並び(機構、建玉 1 単位)。各マス: 平均 bp [区間] / sd / p05 / p50 / p95 / 保有中央値 / n。`*` = 日ブロック 200 回の区間が 0 を跨がない。全 13 門 × 足 6 × 強さ 3\n")
    print("| 門 | 強さ | 足 | 腕 | 平均 [区間] | sd | p05 | p50 | p95 | 保有 | n |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for g in gates:
        for st, lab in STRENGTHS:
            for ft in FEET:
                for key, alab, _ in ARMS:
                    c = cell(d, key, ft, g, st)
                    if not c:
                        print(f"| `{g}` | {lab} | {ft} 分 | {alab} | — | | | | | | |")
                        continue
                    p05, p50, p95 = q(c, "p05"), q(c, "p50"), q(c, "p95")
                    print(f"| `{g}` | {lab} | {ft} 分 | {alab} | {f(c['mean_bp'])}{star(c['ci95_bp'])} [{f(c['ci95_bp'][0])}, {f(c['ci95_bp'][1])}] | {c['sd_bp']:.1f} | "
                          f"{f(p05, 1) if p05 is not None else '(無)'} | {f(p50, 1) if p50 is not None else '(無)'} | {f(p95, 1) if p95 is not None else '(無)'} | {c['hold_median']} | {c['n']:,} |")
    print()
    print("`(無)` = 第 2 部・第 10 部の JSON には分位が無い(本周で足したフィールド)。原典と H1 の分位は `exit_ablation.json`(第 7 部)の `full` にある。\n")


def t_interaction(name, d):
    gates = d["base"]["family"]["gates"]
    print(f"### 表 J-b ({name}) — 交互作用 = (H1+H2a) − H1 − H2a + 原典(平均 bp)。0 なら足し算どおり、正なら相乗、負なら食い合い。**区間は出さない(参考量)**。全 13 門 × 足 6 × 強さ 3\n")
    print("| 門 | 強さ | " + " | ".join(f"{ft} 分" for ft in FEET) + " |")
    print("|---|---|" + "---|" * len(FEET))
    for g in gates:
        for st, lab in STRENGTHS:
            row = []
            for ft in FEET:
                cs = [cell(d, k, ft, g, st) for k, _, _ in ARMS]
                if not all(cs):
                    row.append("—")
                    continue
                base, h1, h2, h12 = (c["mean_bp"] for c in cs)
                inter = h12 - h1 - h2 + base
                row.append(f"{f(inter)}(足し算 {f(h1 + h2 - base)} → 実測 {f(h12)})")
            print(f"| `{g}` | {lab} | " + " | ".join(row) + " |")
    print()


def t_year(name, d, gate="s19/b24"):
    years = sorted({y for c in d["h12"]["cells"].values() for y in c["per_year"]})
    print(f"### 表 J-c ({name}) — 門 `{gate}` の年別、4 マス(平均 bp)\n")
    print("| 足 | 強さ | 腕 | " + " | ".join(years) + " |")
    print("|---|---|---|" + "---|" * len(years))
    for ft in FEET:
        for st, lab in STRENGTHS:
            for key, alab, _ in ARMS:
                c = cell(d, key, ft, gate, st)
                if not c:
                    continue
                print(f"| {ft} 分 | {lab} | {alab} | " + " | ".join(
                    f(c["per_year"][y]["mean_bp"]) if y in c["per_year"] else "—" for y in years) + " |")
    print()


def t_exits(name, d, gate="s19/b24"):
    print(f"### 表 J-d ({name}) — 決済理由の内訳(門 `{gate}`、件数)\n")
    print("| 足 | 強さ | 腕 | invalidated | opposite_weak | reversed |")
    print("|---|---|---|---|---|---|")
    for ft in FEET:
        for st, lab in STRENGTHS:
            for key, alab, _ in ARMS:
                c = cell(d, key, ft, gate, st)
                if not c:
                    continue
                e = c["exit_reasons"]
                print(f"| {ft} 分 | {lab} | {alab} | {e.get('invalidated', 0):,} | {e.get('opposite_weak', 0):,} | {e.get('reversed', 0):,} |")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()
    print("# H2a — 2 × 2 {原典, H1, H2a, H1+H2a}(生成物。`H2_PREREG.md` §3)\n")
    print("`*` = 日ブロックブートストラップ 200 回の 95% 区間が 0 を跨がない(原典・H1 は共有乱数列、H2a・H1+H2a も同じ流儀)。単位 bp、経費なし。\n")
    for name, dirpath in VENUES:
        d = load(dirpath)
        missing = [lab for key, lab, _ in ARMS if not d[key]]
        if missing:
            print(f"- {name}: 未実行の腕 {missing}\n")
            if not (d["base"] and d["h2"]):
                continue
        rg = d["h2"].get("reproduction_gate", []) if d["h2"] else []
        print(f"## {name} — 期間 {d['base']['explore'][0]} 〜 {d['base']['explore'][1]}。H2a 単独の再現ゲート(vs 第 7 部 `opposite_only`) {sum(1 for r in rg if r['ok'])}/{len(rg)} 一致\n")
        t_grid(name, d)
        if all(d[k] for k, _, _ in ARMS):
            t_interaction(name, d)
            t_year(name, d)
            t_exits(name, d)


if __name__ == "__main__":
    main()
