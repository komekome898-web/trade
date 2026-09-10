"""年ごとの**総損益**(建玉 1 単位、取引ごとの符号付き bp の年内合計)を 4 マスの機構 JSON から生成する(手打ちしない)。

オーナー指示(L-075): 「取引当たりの平均だけでなく年ごとの総損益を出さないといけません。
平均が上がっても総利益が減るなら改良とは呼べません。」

総損益 = 年別 n × 年別平均(JSON の `per_year` から。平均は 3 桁丸めなので合計の誤差は n × 0.0005 bp 以下)。
年は**建てた足の年**(`measure_katsuo_effect.py` の `per_year` と同じ規則)。経費は引いていない。

読むもの(両取引所): `effect.json`(原典)/ `effect_flipbody.json`(H1)/ `effect_noinval.json`(H2a)/ `effect_flip_noinval.json`(H1+H2a)。
出すもの:
    (a) 門 `s19/b24`: 足 × 強さ × 腕 の年別 総損益 bp と (n)、全期間の合計
    (b) 全 13 門 × 足 6、強さ「両方」: 全期間の総損益(4 腕)と、原典より総損益が増えた年の数

    PYTHONPATH=src:scripts python scripts/render_k1_yearly_pnl.py > docs/PHASE2/K1/YEARLY_PNL_TABLES.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
K1 = REPO / "docs" / "PHASE2" / "K1"
VENUES = (("BitMEX", K1), ("Binance", K1 / "binance"))
FEET = (1, 3, 5, 15, 30, 60)
STRENGTHS = (("both", "両方"), ("weak", "弱い"), ("strong", "強い"))
ARMS = (("base", "原典", "effect.json"), ("h1", "H1", "effect_flipbody.json"),
        ("h2", "H2a", "effect_noinval.json"), ("h12", "H1+H2a", "effect_flip_noinval.json"))


def load(dirpath):
    return {key: (json.loads((dirpath / name).read_text("utf-8")) if (dirpath / name).exists() else None)
            for key, _, name in ARMS}


def cell(d, key, ft, g, st):
    return d[key]["cells"].get(f"{ft}|{g}|{st}") if d[key] else None


def total(c, y):
    p = c["per_year"].get(y)
    return (p["n"] * p["mean_bp"], p["n"]) if p else (None, 0)


def fmt(x):
    return "—" if x is None else f"{x:+,.0f}"


def years_of(d):
    return sorted({y for k in d if d[k] for c in d[k]["cells"].values() for y in c["per_year"]})


def t_gate(name, d, gate="s19/b24"):
    ys = years_of(d)
    print(f"### 表 Y-a ({name}) — 門 `{gate}`: 年ごとの総損益 bp(建玉 1 単位、取引の bp の合計)と (取引数)。右端は全期間の合計\n")
    print("| 足 | 強さ | 腕 | " + " | ".join(ys) + " | 合計 |")
    print("|---|---|---|" + "---|" * (len(ys) + 1))
    for ft in FEET:
        for st, lab in STRENGTHS:
            for key, alab, _ in ARMS:
                c = cell(d, key, ft, gate, st)
                if not c:
                    continue
                row, tot, ntot = [], 0.0, 0
                for y in ys:
                    t, n = total(c, y)
                    row.append(f"{fmt(t)} ({n:,})" if t is not None else "—")
                    if t is not None:
                        tot += t
                        ntot += n
                print(f"| {ft} 分 | {lab} | {alab} | " + " | ".join(row) + f" | **{fmt(tot)}** ({ntot:,}) |")
    print()


def t_all_gates(name, d, st="both"):
    ys = years_of(d)
    gates = d["base"]["family"]["gates"]
    print(f"### 表 Y-b ({name}) — 全 13 門 × 足 6、強さ「両方」: 全期間の総損益 bp(4 腕)と、**原典より年の総損益が増えた年の数 / 年数**(H1 / H2a / H1+H2a)\n")
    print("| 門 | 足 | 原典 | H1 | H2a | H1+H2a | 増えた年 H1 | 増えた年 H2a | 増えた年 H1+H2a |")
    print("|---|---|---|---|---|---|---|---|---|")
    for g in gates:
        for ft in FEET:
            cs = {key: cell(d, key, ft, g, st) for key, _, _ in ARMS}
            if not all(cs.values()):
                continue
            tots = {}
            up = {}
            for key in cs:
                tots[key] = sum(total(cs[key], y)[0] or 0.0 for y in ys)
            for key in ("h1", "h2", "h12"):
                k = m = 0
                for y in ys:
                    a, _ = total(cs["base"], y)
                    b, _ = total(cs[key], y)
                    if a is None or b is None:
                        continue
                    m += 1
                    k += b > a
                up[key] = f"{k}/{m}"
            print(f"| `{g}` | {ft} 分 | {fmt(tots['base'])} | {fmt(tots['h1'])} | {fmt(tots['h2'])} | {fmt(tots['h12'])} | {up['h1']} | {up['h2']} | {up['h12']} |")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()
    print("# 年ごとの総損益 — 4 マス {原典, H1, H2a, H1+H2a}(生成物。L-075)\n")
    print("総損益 = 年別 n × 年別平均(bp、建玉 1 単位、経費なし)。年は建てた足の年。`—` = その年に取引なし。BitMEX は探索区間 2017-2019 のみ(封印は開けていない)。\n")
    for name, dirpath in VENUES:
        d = load(dirpath)
        if not all(d.values()):
            print(f"- {name}: 未実行の腕あり {[lab for k, lab, _ in ARMS if not d[k]]}\n")
            continue
        print(f"## {name} — 期間 {d['base']['explore'][0]} 〜 {d['base']['explore'][1]}\n")
        t_gate(name, d)
        t_all_gates(name, d)


if __name__ == "__main__":
    main()
