"""第 13 部(H3 の分解: 入口の遅れ × 出口の遅れ)の表を JSON から生成する(手打ちしない)。

土台 2 つ(原典 / H1+H2a)× 取引所 2 つ。`H3_DECOMP_PREREG.md` §2:
    (a) 表 L-a: 門 `s19/b24`、足 6 × 強さ 3: 4 腕の平均 [区間] と分解 3 量、DD と第 12 部の機構との差
    (b) 表 L-b: 門 `s19/b24`: 年ごとの総損益 bp(建玉 1 単位)と取引数、4 腕 — L-075
    (c) 表 L-c: 全 13 門 × 足 6、強さ 3: 分解 3 量と全期間の総損益(4 腕)
    (d) 表 L-d: 原典の土台での DD と第 12 部 ①(遅らせた機械)の差 = 経路の効果
    (e) 表 L-e: 門 `s19/b24`: 分解 2 量(入口・出口)の年別(取引数は 4 腕で同じなので、年別平均の差がそのまま年別の分解)

    PYTHONPATH=src:scripts python scripts/render_k1_h3_decomp.py > results/PHASE2/K1/H3_DECOMP_TABLES.md
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
K1 = REPO / "results" / "PHASE2" / "K1"
VENUES = (("BitMEX", K1), ("Binance", K1 / "binance"))
BASES = (("原典", "delay_decomp.json"), ("H1+H2a", "delay_decomp_flip_noinval.json"))
FEET = (1, 3, 5, 15, 30, 60)
STRENGTHS = (("both", "両方"), ("weak", "弱い"), ("strong", "強い"))
ARMS = (("EE", "EE 原典"), ("DE", "DE 入口遅れ"), ("ED", "ED 出口遅れ"), ("DD", "DD 両方遅れ"))


def star(ci):
    return "*" if ci and ci[0] == ci[0] and (ci[0] > 0 or ci[1] < 0) else ""


def f(x, d=2):
    return "—" if x is None else f"{x:+.{d}f}"


def fmt0(x):
    return "—" if x is None else f"{x:+,.0f}"


def years_of(d):
    return sorted({y for c in d["cells"].values() for y in c["arms"]["EE"]["per_year"]})


def total(arm, ys):
    return sum(arm["per_year"][y]["n"] * arm["per_year"][y]["mean_bp"] for y in ys if y in arm["per_year"])


def t_a(name, bl, d, gate="s19/b24"):
    print(f"### 表 L-a ({name}、土台 {bl}) — 門 `{gate}`: 4 腕の平均 bp [区間]、分解 3 量(1 取引ごとの差の平均、区間なし)、DD と第 12 部の機構の差\n")
    print("| 足 | 強さ | n | EE 原典 | DE 入口遅れ | ED 出口遅れ | DD 両方遅れ | 入口の遅れ | 出口の遅れ | 交互 | DE 長さ 0 | 機構 n − n | 機構 − DD |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for ft in FEET:
        for st, lab in STRENGTHS:
            c = d["cells"].get(f"{ft}|{gate}|{st}")
            if not c:
                continue
            a = c["arms"]
            dc = c["decomp_bp"]
            m = c.get("dd_vs_mechanism") or {}
            cols = " | ".join(f"{f(a[k]['mean_bp'])}{star(a[k]['ci95_bp'])} [{f(a[k]['ci95_bp'][0])}, {f(a[k]['ci95_bp'][1])}]" for k, _ in ARMS)
            print(f"| {ft} 分 | {lab} | {c['n']:,} | {cols} | {f(dc['entry_delay'])} | {f(dc['exit_delay'])} | {f(dc['interaction'])} | {c['de_zero_length']:,} | {m.get('dn', '—')} | {f(m.get('dmean_bp'))} |")
    print()


def t_b(name, bl, d, gate="s19/b24"):
    ys = years_of(d)
    print(f"### 表 L-b ({name}、土台 {bl}) — 門 `{gate}`: 年ごとの総損益 bp(建玉 1 単位)と (取引数)、4 腕。右端は全期間の合計\n")
    print("| 足 | 強さ | 腕 | " + " | ".join(ys) + " | 合計 |")
    print("|---|---|---|" + "---|" * (len(ys) + 1))
    for ft in FEET:
        for st, lab in STRENGTHS:
            c = d["cells"].get(f"{ft}|{gate}|{st}")
            if not c:
                continue
            for k, alab in ARMS:
                arm = c["arms"][k]
                row = []
                for y in ys:
                    p = arm["per_year"].get(y)
                    row.append(f"{fmt0(p['n'] * p['mean_bp'])} ({p['n']:,})" if p else "—")
                print(f"| {ft} 分 | {lab} | {alab} | " + " | ".join(row) + f" | **{fmt0(total(arm, ys))}** ({arm['n']:,}) |")
    print()


def t_c(name, bl, d):
    ys = years_of(d)
    gates = d["family"]["gates"]
    print(f"### 表 L-c ({name}、土台 {bl}) — 全 13 門 × 足 6 × 強さ 3: 分解 3 量(bp / 取引)と全期間の総損益 bp(4 腕)、n\n")
    print("| 門 | 足 | 強さ | n | 入口の遅れ | 出口の遅れ | 交互 | 総 EE | 総 DE | 総 ED | 総 DD |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for g in gates:
        for ft in FEET:
            for st, lab in STRENGTHS:
                c = d["cells"].get(f"{ft}|{g}|{st}")
                if not c:
                    continue
                dc = c["decomp_bp"]
                print(f"| `{g}` | {ft} 分 | {lab} | {c['n']:,} | {f(dc['entry_delay'])} | {f(dc['exit_delay'])} | {f(dc['interaction'])} | "
                      + " | ".join(fmt0(total(c["arms"][k], ys)) for k, _ in ARMS) + " |")
    print()


def t_d(name, d):
    print(f"### 表 L-d ({name}、土台 原典) — DD(値付けだけ両方遅らせる)と第 12 部 ①(遅らせた機械)の差 = 経路の効果。全 13 門 × 足 6 × 強さ 3\n")
    print("| 門 | 足 | 強さ | n DD | n ① − n DD | 平均 DD | 平均 ① | ① − DD |")
    print("|---|---|---|---|---|---|---|---|")
    for g in d["family"]["gates"]:
        for ft in FEET:
            for st, lab in STRENGTHS:
                c = d["cells"].get(f"{ft}|{g}|{st}")
                m = (c or {}).get("dd_vs_mechanism")
                if not m:
                    continue
                print(f"| `{g}` | {ft} 分 | {lab} | {c['n']:,} | {m['dn']:+,} | {f(c['arms']['DD']['mean_bp'])} | {f(m['mean_mech_bp'])} | {f(m['dmean_bp'])} |")
    print()


def t_e(name, bl, d, gate="s19/b24"):
    ys = years_of(d)
    print(f"### 表 L-e ({name}、土台 {bl}) — 門 `{gate}`: 入口の遅れ / 出口の遅れ の年別(bp / 取引 = 年別平均 DE − EE / ED − EE)。右端は 2017 を除く全期間(取引数で重み付け)\n")
    print("| 足 | 強さ | 量 | " + " | ".join(ys) + " | 2017 除く |")
    print("|---|---|---|" + "---|" * (len(ys) + 1))
    for ft in FEET:
        for st, lab in STRENGTHS:
            c = d["cells"].get(f"{ft}|{gate}|{st}")
            if not c:
                continue
            a = c["arms"]
            for arm, qlab in (("DE", "入口の遅れ"), ("ED", "出口の遅れ")):
                row, s_ex, n_ex = [], 0.0, 0
                for y in ys:
                    p0, p1 = a["EE"]["per_year"].get(y), a[arm]["per_year"].get(y)
                    if not p0:
                        row.append("—")
                        continue
                    dv = p1["mean_bp"] - p0["mean_bp"]
                    row.append(f(dv))
                    if y != "2017":
                        s_ex += dv * p0["n"]
                        n_ex += p0["n"]
                print(f"| {ft} 分 | {lab} | {qlab} | " + " | ".join(row) + f" | **{f(s_ex / n_ex) if n_ex else '—'}** |")
    print()


def main() -> None:
    print("# H3 の分解 — 入口の遅れ × 出口の遅れ(生成物。`H3_DECOMP_PREREG.md` §2)\n")
    print("`*` = 日ブロックブートストラップ 200 回の 95% 区間が 0 を跨がない(種はセル名 × 腕)。単位 bp、経費なし。"
          "分解 3 量 = 同じ取引の値付け違いの差の平均(入口 = DE − EE、出口 = ED − EE、交互 = DD − DE − ED + EE)。"
          "総損益 = 年別 n × 年別平均(建玉 1 単位)。\n")
    for name, dirpath in VENUES:
        for bl, fn in BASES:
            p = dirpath / fn
            if not p.exists():
                print(f"- {name} 土台 {bl}: 未実行(`{fn}`)\n")
                continue
            d = json.loads(p.read_text("utf-8"))
            print(f"## {name}、土台 {bl} — 期間 {d['explore'][0]} 〜 {d['explore'][1]}"
                  + (f"、再現ゲート {sum(r['ok'] for r in d['reproduction_gate'])}/{len(d['reproduction_gate'])}" if d["reproduction_gate"] else "") + "\n")
            t_a(name, bl, d)
            t_b(name, bl, d)
            t_c(name, bl, d)
            t_e(name, bl, d)
            if bl == "原典":
                t_d(name, d)


if __name__ == "__main__":
    main()
