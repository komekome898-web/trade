"""第 12 部(H3: 入口を 1 本遅らせる)の表を 4 腕の機構 JSON から生成する(手打ちしない)。

腕: 原典 / H1+H2a(第 2 周の土台)/ ① H3 / ② H1+H2a+H3。`H3_PREREG.md` §3:
    (a) 4 腕横並び 足 × 門 13 × 強さ 3(平均・区間・sd・p05・p50・p95・保有・n)
    (b) 年ごとの総損益と取引数(門 `s19/b24`、4 腕)— L-075
    (c) 全 13 門 × 足 6、強さ「両方」: 全期間の総損益(4 腕)と原典より増えた年の数
    (d) 決済理由(門 `s19/b24`)

    PYTHONPATH=src:scripts python scripts/render_k1_h3.py > results/PHASE2/K1/H3_TABLES.md
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
ARMS = (("base", "原典", "effect.json"), ("h12", "H1+H2a", "effect_flip_noinval.json"),
        ("h3", "H3", "effect_delay.json"), ("h123", "H1+H2a+H3", "effect_flip_noinval_delay.json"))


def load(dirpath):
    return {key: (json.loads((dirpath / name).read_text("utf-8")) if (dirpath / name).exists() else None)
            for key, _, name in ARMS}


def star(ci):
    return "*" if ci and ci[0] == ci[0] and (ci[0] > 0 or ci[1] < 0) else ""


def f(x, d=2):
    return "—" if x is None else f"{x:+.{d}f}"


def fmt0(x):
    return "—" if x is None else f"{x:+,.0f}"


def cell(d, key, ft, g, st):
    return d[key]["cells"].get(f"{ft}|{g}|{st}") if d[key] else None


def q(c, k):
    v = c.get("quantiles_bp", {}).get(k)
    return "(無)" if v is None else f(v, 1)


def years_of(d):
    return sorted({y for k in d if d[k] for c in d[k]["cells"].values() for y in c["per_year"]})


def total(c, y):
    p = c["per_year"].get(y)
    return (p["n"] * p["mean_bp"], p["n"]) if p else (None, 0)


def t_grid(name, d):
    gates = d["base"]["family"]["gates"]
    print(f"### 表 K-a ({name}) — 4 腕横並び(機構)。各マス: 平均 bp [区間] / sd / p05 / p50 / p95 / 保有中央値 / n。全 13 門 × 足 6 × 強さ 3\n")
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
                    print(f"| `{g}` | {lab} | {ft} 分 | {alab} | {f(c['mean_bp'])}{star(c['ci95_bp'])} [{f(c['ci95_bp'][0])}, {f(c['ci95_bp'][1])}] | {c['sd_bp']:.1f} | {q(c, 'p05')} | {q(c, 'p50')} | {q(c, 'p95')} | {c['hold_median']} | {c['n']:,} |")
    print()
    print("`(無)` = 第 2 部の JSON には分位が無い(第 11 部で足したフィールド)。\n")


def t_year_pnl(name, d, gate="s19/b24"):
    ys = years_of(d)
    print(f"### 表 K-b ({name}) — 門 `{gate}`: 年ごとの総損益 bp(建玉 1 単位)と (取引数)、4 腕。右端は全期間の合計\n")
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
                    row.append(f"{fmt0(t)} ({n:,})" if t is not None else "—")
                    if t is not None:
                        tot += t
                        ntot += n
                print(f"| {ft} 分 | {lab} | {alab} | " + " | ".join(row) + f" | **{fmt0(tot)}** ({ntot:,}) |")
    print()


def t_all_gates(name, d, st="both"):
    ys = years_of(d)
    gates = d["base"]["family"]["gates"]
    print(f"### 表 K-c ({name}) — 全 13 門 × 足 6、強さ「両方」: 全期間の総損益 bp と (取引数)、4 腕。右 3 列は原典より年の総損益が増えた年の数 / 年数\n")
    print("| 門 | 足 | 原典 | H1+H2a | H3 | H1+H2a+H3 | 増 H1+H2a | 増 H3 | 増 H1+H2a+H3 |")
    print("|---|---|---|---|---|---|---|---|---|")
    for g in gates:
        for ft in FEET:
            cs = {key: cell(d, key, ft, g, st) for key, _, _ in ARMS}
            if not all(cs.values()):
                continue
            tots = {key: (sum(total(cs[key], y)[0] or 0.0 for y in ys), cs[key]["n"]) for key in cs}
            up = {}
            for key in ("h12", "h3", "h123"):
                k = m = 0
                for y in ys:
                    a, _ = total(cs["base"], y)
                    b, _ = total(cs[key], y)
                    if a is None or b is None:
                        continue
                    m += 1
                    k += b > a
                up[key] = f"{k}/{m}"
            print(f"| `{g}` | {ft} 分 | " + " | ".join(f"{fmt0(tots[k][0])} ({tots[k][1]:,})" for k in ("base", "h12", "h3", "h123"))
                  + f" | {up['h12']} | {up['h3']} | {up['h123']} |")
    print()


def t_exits(name, d, gate="s19/b24"):
    print(f"### 表 K-d ({name}) — 決済理由の内訳(門 `{gate}`、件数)\n")
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
    print("# H3 — 入口を 1 本遅らせる: {原典, H1+H2a, H3, H1+H2a+H3}(生成物。`H3_PREREG.md` §3)\n")
    print("`*` = 日ブロックブートストラップ 200 回の 95% 区間が 0 を跨がない。単位 bp、経費なし。総損益 = 年別 n × 年別平均(建玉 1 単位)。\n")
    for name, dirpath in VENUES:
        d = load(dirpath)
        missing = [lab for key, lab, _ in ARMS if not d[key]]
        if missing:
            print(f"- {name}: 未実行の腕 {missing}\n")
        if not (d["base"] and d["h3"]):
            continue
        print(f"## {name} — 期間 {d['base']['explore'][0]} 〜 {d['base']['explore'][1]}\n")
        t_grid(name, d)
        t_year_pnl(name, d)
        if all(d[k] for k, _, _ in ARMS):
            t_all_gates(name, d)
        t_exits(name, d)


if __name__ == "__main__":
    main()
