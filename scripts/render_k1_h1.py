"""第 10 部(H1: 実体 ≥ ヒゲ の足は実体を逆張りする)の表を、原典と反転版の JSON から生成する(手打ちしない)。

読むもの(両取引所): `signal_horizon.json` / `signal_horizon_flipbody.json` / `effect.json` / `effect_flipbody.json`。
出すもの(`H1_PREREG.md` §3-3):
    (a) シグナル単体 足 × 門 13 × 強さ 3、h=3、原典 → 反転(全セル)
    (b) 反転した足だけ(`flipped`)の 足 × 門 × h
    (c) 機構 足 × 門 13 × 強さ 3: 原典 → 反転(平均・sd・保有中央値・n)
    (d) 門 `s19/b24` の年別(シグナル単体 h=3 と機構)

    PYTHONPATH=src:scripts python scripts/render_k1_h1.py > results/PHASE2/K1/H1_TABLES.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
K1 = REPO / "results" / "PHASE2" / "K1"
VENUES = (("BitMEX", K1), ("Binance", K1 / "binance"))
FEET = (1, 3, 5, 15, 30, 60)
STRENGTHS = (("strong", "強い"), ("weak", "弱い"), ("both", "両方"))
LABEL = {"strong": "強い", "weak": "弱い", "both": "両方", "flipped": "反転した足"}


def load(dirpath):
    out = {}
    for key, name in (("sh0", "signal_horizon.json"), ("sh1", "signal_horizon_flipbody.json"),
                      ("ef0", "effect.json"), ("ef1", "effect_flipbody.json")):
        p = dirpath / name
        out[key] = json.loads(p.read_text("utf-8")) if p.exists() else None
    return out


def star(ci):
    return "*" if ci and ci[0] == ci[0] and (ci[0] > 0 or ci[1] < 0) else ""


def f(x, d=2):
    return "—" if x is None else f"{x:+.{d}f}"


def fmt_cell(c):
    return "—" if not c else f"{f(c['mean_bp'])}{star(c['ci95_bp'])} ({c['n']:,})"


def t_signal(name, d, h=3):
    sh0, sh1 = d["sh0"], d["sh1"]
    gates = sh0["family"]["gates"]
    print(f"### 表 H-a ({name}) — シグナル単体 h={h}: 原典 → 反転。各マス: 平均 bp (n)。`*` = 日ブロック 200 回の区間が 0 を跨がない。全 13 門 × 足 6 × 強さ 3\n")
    print("| 門 | 強さ | " + " | ".join(f"{ft} 分" for ft in FEET) + " |")
    print("|---|---|" + "---|" * len(FEET))
    for g in gates:
        for st, lab in STRENGTHS:
            row = []
            for ft in FEET:
                c0 = sh0["cells"].get(f"{ft}|{g}|{st}|{h}")
                c1 = sh1["cells"].get(f"{ft}|{g}|{st}|{h}")
                if c0 and c1 and c0["n"] == c1["n"] and c0["mean_bp"] == c1["mean_bp"]:
                    row.append(f"{f(c0['mean_bp'])}{star(c0['ci95_bp'])} (同)")
                else:
                    row.append(f"{f(c0['mean_bp']) if c0 else '—'} → {fmt_cell(c1)}")
            print(f"| `{g}` | {lab} | " + " | ".join(row) + " |")
    print()


def t_flipped(name, d):
    sh1 = d["sh1"]
    gates = [g for g in sh1["family"]["gates"] if not g.endswith("/b-")]
    hs = sh1["family"]["horizons"]
    print(f"### 表 H-b ({name}) — 反転した足だけ(原典と向きが違う足)。各マス: 平均 bp (n)。大門の枝を持つ門のみ(`b-` の門では反転が起きない)\n")
    print("| 門 | 足 | " + " | ".join(f"h={h}" for h in hs) + " |")
    print("|---|---|" + "---|" * len(hs))
    for g in gates:
        for ft in FEET:
            row = [fmt_cell(sh1["cells"].get(f"{ft}|{g}|flipped|{h}")) for h in hs]
            if all(r == "—" for r in row):
                continue
            print(f"| `{g}` | {ft} 分 | " + " | ".join(row) + " |")
    print()


def t_mech(name, d):
    ef0, ef1 = d["ef0"], d["ef1"]
    gates = ef0["family"]["gates"]
    print(f"### 表 H-c ({name}) — 機構(4 分岐 + 決済ルール、建玉 1 単位)。原典 → 反転: 平均 bp [区間] / sd / 保有中央値 / n。全 13 門 × 足 6 × 強さ 3\n")
    print("| 門 | 強さ | 足 | 原典 平均 [区間] | 反転 平均 [区間] | sd 原典 → 反転 | 保有 原典 → 反転 | n 原典 → 反転 |")
    print("|---|---|---|---|---|---|---|---|")
    for g in gates:
        for st, lab in STRENGTHS:
            for ft in FEET:
                c0 = ef0["cells"].get(f"{ft}|{g}|{st}")
                c1 = ef1["cells"].get(f"{ft}|{g}|{st}")
                if not c0 and not c1:
                    continue
                if c0 and c1 and c0["n"] == c1["n"] and c0["mean_bp"] == c1["mean_bp"]:
                    print(f"| `{g}` | {lab} | {ft} 分 | {f(c0['mean_bp'])}{star(c0['ci95_bp'])} [{f(c0['ci95_bp'][0])}, {f(c0['ci95_bp'][1])}] | (同) | {c0['sd_bp']:.1f} | {c0['hold_median']} | {c0['n']:,} |")
                    continue
                a = f"{f(c0['mean_bp'])}{star(c0['ci95_bp'])} [{f(c0['ci95_bp'][0])}, {f(c0['ci95_bp'][1])}]" if c0 else "—"
                b = f"{f(c1['mean_bp'])}{star(c1['ci95_bp'])} [{f(c1['ci95_bp'][0])}, {f(c1['ci95_bp'][1])}]" if c1 else "—"
                sd = f"{c0['sd_bp']:.1f} → {c1['sd_bp']:.1f}" if c0 and c1 else "—"
                hold = f"{c0['hold_median']} → {c1['hold_median']}" if c0 and c1 else "—"
                n = f"{c0['n']:,} → {c1['n']:,}" if c0 and c1 else "—"
                print(f"| `{g}` | {lab} | {ft} 分 | {a} | {b} | {sd} | {hold} | {n} |")
    print()


def t_year(name, d, gate="s19/b24", h=3):
    sh0, sh1, ef0, ef1 = d["sh0"], d["sh1"], d["ef0"], d["ef1"]
    years = sorted({y for c in sh1["cells"].values() for y in c["per_year"]})
    print(f"### 表 H-d ({name}) — 門 `{gate}` の年別。上段: シグナル単体 h={h}(原典 → 反転。`flipped` は反転した足だけ)、下段: 機構(原典 → 反転)\n")
    print("| 量 | 足 | 強さ | " + " | ".join(years) + " |")
    print("|---|---|---|" + "---|" * len(years))
    for ft in FEET:
        for st in ("strong", "weak", "both", "flipped"):
            c0 = sh0["cells"].get(f"{ft}|{gate}|{st}|{h}")
            c1 = sh1["cells"].get(f"{ft}|{gate}|{st}|{h}")
            if not c1:
                continue
            row = []
            for y in years:
                p0 = c0["per_year"].get(y) if c0 else None
                p1 = c1["per_year"].get(y)
                if st == "flipped":
                    row.append(f"{f(p1['mean_bp'])}{star(p1['ci95_bp'])} ({p1['n']:,})" if p1 else "—")
                else:
                    row.append(f"{f(p0['mean_bp']) if p0 else '—'} → {f(p1['mean_bp']) if p1 else '—'}")
            print(f"| シグナル h={h} | {ft} 分 | {LABEL[st]} | " + " | ".join(row) + " |")
    for ft in FEET:
        for st, lab in STRENGTHS:
            if not (ef0 and ef1):
                break
            c0 = ef0["cells"].get(f"{ft}|{gate}|{st}")
            c1 = ef1["cells"].get(f"{ft}|{gate}|{st}")
            if not c1:
                continue
            row = []
            for y in years:
                p0 = c0["per_year"].get(y) if c0 else None
                p1 = c1["per_year"].get(y)
                row.append(f"{f(p0['mean_bp']) if p0 else '—'} → {f(p1['mean_bp']) if p1 else '—'}")
            print(f"| 機構 | {ft} 分 | {lab} | " + " | ".join(row) + " |")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--h", type=int, default=3)
    args = ap.parse_args()
    print("# H1 — 原典 vs 反転(生成物。`H1_PREREG.md` §3)\n")
    print("`*` = 日ブロックブートストラップ 200 回の 95% 区間が 0 を跨がない。単位 bp、経費なし。「(同)」= 原典と n・平均が同一(反転が起きない門)。\n")
    for name, dirpath in VENUES:
        d = load(dirpath)
        if not (d["sh0"] and d["sh1"]):
            print(f"- {name}: `signal_horizon_flipbody.json` が無い(未実行)\n")
            continue
        print(f"## {name} — 期間 {d['sh1']['explore'][0]} 〜 {d['sh1']['explore'][1]}、flip_body={d['sh1'].get('flip_body')}\n")
        t_signal(name, d, args.h)
        t_flipped(name, d)
        if d["ef0"] and d["ef1"]:
            t_mech(name, d)
        else:
            print(f"- {name}: `effect_flipbody.json` が無い(未実行)\n")
        t_year(name, d, h=args.h)


if __name__ == "__main__":
    main()
