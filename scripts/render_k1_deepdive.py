"""第 9 部(K1 深掘り)の**要約表**を `robustness.json`(両取引所)から生成する(手打ちしない)。

`render_k1_robustness.py` は 1 取引所の全診断を全部出す(4,000 行超)。ここでは第 9 部の本文が引く
**取引所横並びの要約**だけを出す。数字の出所はすべて `robustness.json` のセル。

    PYTHONPATH=src:scripts python scripts/render_k1_deepdive.py > docs/PHASE2/K1/DEEPDIVE_TABLES.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
K1 = REPO / "docs" / "PHASE2" / "K1"
VENUES = (("BitMEX", K1 / "robustness.json"), ("Binance", K1 / "binance" / "robustness.json"))
FEET = (1, 3, 5, 15, 30, 60)
STRENGTHS = (("strong", "強い"), ("weak", "弱い"))
GATE = "s19/b24"


def load():
    out = []
    for name, path in VENUES:
        if path.exists():
            out.append((name, json.loads(path.read_text("utf-8"))))
    return out


def star(ci):
    return "*" if ci and (ci[0] > 0 or ci[1] < 0) else ""


def f(x, d=2):
    return "—" if x is None else f"{x:+.{d}f}"


def cell(d, foot, st, h):
    return d["cells"].get(f"{foot}|{GATE}|{st}|{h}")


def ratio_labels(d):
    """実体比の層のラベルを JSON の `bootstrap.ratio_bins` から作る(手打ちしない)。"""
    e = d["bootstrap"]["ratio_bins"]
    return [f"[{e[i]:g},{e[i + 1]:g})" for i in range(len(e) - 1)] + [f"[{e[-1]:g},+)"]


def years(d):
    ys = set()
    for c in d["cells"].values():
        ys.update(c["d1"]["per_year"].keys())
    return sorted(ys)


# ---------------------------------------------------------------- T1: D2 ----

def t1(venues, hs=(1, 3, 5)):
    print("### 表 S1 — 区間の頑健性: 日ブロック 200 回で 0 を跨がないセルが、ブロックを変えても跨がないか(門 `s19/b24`、h=1/3/5、足 6 × 強さ 2)\n")
    print("| 取引所 | セル数 | 日 200 で `*` | うち 日 1000 でも | うち 週 200 でも | うち 週 1000 でも | うち 月 200 でも |")
    print("|---|---|---|---|---|---|---|")
    for name, d in venues:
        tot = base = 0
        keep = {"day_1000": 0, "week_200": 0, "week_1000": 0, "month_200": 0}
        for foot in FEET:
            for st, _ in STRENGTHS:
                for h in hs:
                    c = cell(d, foot, st, h)
                    if not c:
                        continue
                    tot += 1
                    if not star(c["d1"]["ci95_bp"]):
                        continue
                    base += 1
                    for k in keep:
                        if star(c["d2"][k]):
                            keep[k] += 1
        print(f"| {name} | {tot} | {base} | {keep['day_1000']} | {keep['week_200']} | {keep['week_1000']} | {keep['month_200']} |")
    print()


# ---------------------------------------------------------------- T2: D3 ----

def t2(venues):
    print("### 表 S2 — 1 本遅らせた入口(D3): `sig × (close[i+h]/close[i+1] − 1)`。左が第 4 部の量、右が遅らせた量。`*` = 日ブロック 200 回の区間が 0 を跨がない\n")
    head = "| 足 | 強さ | " + " | ".join(f"{n} h=3 | {n} h=3 遅らせ | {n} h=5 | {n} h=5 遅らせ" for n, _ in venues) + " |"
    print(head)
    print("|---|---|" + "---|" * (4 * len(venues)))
    for foot in FEET:
        for st, lab in STRENGTHS:
            row = [f"{foot} 分", lab]
            for _, d in venues:
                for h in (3, 5):
                    c = cell(d, foot, st, h)
                    if not c:
                        row += ["—", "—"]
                        continue
                    row.append(f"{f(c['d1']['mean_bp'])}{star(c['d1']['ci95_bp'])}")
                    row.append(f"{f(c['d3']['mean_bp'])}{star(c['d3']['ci95_bp'])}")
            print("| " + " | ".join(row) + " |")
    print()


def t3(venues, foot_list=(5, 15), h=3):
    print(f"### 表 S3 — 1 本遅らせた入口の年別(h={h}): 「第 4 部 → 遅らせ」\n")
    for name, d in venues:
        ys = years(d)
        print(f"**{name}**\n")
        print("| 足 | 強さ | " + " | ".join(ys) + " |")
        print("|---|---|" + "---|" * len(ys))
        for foot in foot_list:
            for st, lab in STRENGTHS:
                c = cell(d, foot, st, h)
                if not c:
                    continue
                row = []
                for y in ys:
                    a = c["d1"]["per_year"].get(y)
                    b = c["d3"]["per_year"].get(y)
                    row.append(f"{f(a['mean_bp'])} → {f(b['mean_bp'])}" if a and b else "—")
                print(f"| {foot} 分 | {lab} | " + " | ".join(row) + " |")
        print()


# ---------------------------------------------------------------- T4: D4 ----

def t4(venues, h=3):
    print(f"### 表 S4 — 古い終値(`close[i] == close[i−1]`)のシグナル足の割合(年別、5 分・強い)と、除いた後の平均の変化(全期間、h={h}、全足 × 強さ の最大変化)\n")
    for name, d in venues:
        ys = years(d)
        c = cell(d, 5, "strong", h)
        shares = " / ".join(f"{y}: {100 * c['d4']['per_year'][y]['stale_share']:.2f}%" if y in c["d4"]["per_year"] else f"{y}: —" for y in ys)
        mx = 0.0
        for foot in FEET:
            for st, _ in STRENGTHS:
                cc = cell(d, foot, st, h)
                if cc:
                    mx = max(mx, abs(cc["d4"]["mean_bp"] - cc["d1"]["mean_bp"]))
        print(f"- **{name}**: {shares}。除外後の平均の変化は全セルで **{mx:.2f} bp 以内**")
    print()


# ---------------------------------------------------------------- T5: D5 ----

def t5(venues, hs=(1, 3, 5)):
    print("### 表 S5 — 年内分割の符号一致(D5): 年ごとに ISO 週の奇偶 / 上下半期で割り、2 つの平均の符号が一致した年の数\n")
    head = "| 足 | 強さ | " + " | ".join(f"{n} 年数 | {n} 週奇偶 h=1/3/5 | {n} 上下半期 h=1/3/5" for n, _ in venues) + " |"
    print(head)
    print("|---|---|" + "---|" * (3 * len(venues)))
    for foot in FEET:
        for st, lab in STRENGTHS:
            row = [f"{foot} 分", lab]
            for _, d in venues:
                cs = [cell(d, foot, st, h) for h in hs]
                if not all(cs):
                    row += ["—", "—", "—"]
                    continue
                py = cs[0]["d5"]["per_year"]
                row.append(str(len(py)))
                row.append("/".join(str(sum(1 for v in c["d5"]["per_year"].values() if v["week_parity"]["same_sign"])) for c in cs))
                row.append("/".join(str(sum(1 for v in c["d5"]["per_year"].values() if v["half"]["same_sign"])) for c in cs))
            print("| " + " | ".join(row) + " |")
    print()


# ---------------------------------------------------------------- T6: D8 ----

def t6(venues, h=3):
    print(f"### 表 S6 — ボラ三分位(D8、直前 100 本の |対数リターン| 平均、先読み無し。h={h})。各マス: 平均 bp (n)。三分位は取引所 × 足ごとの全シグナル足で切る\n")
    head = "| 足 | 強さ | " + " | ".join(f"{n} 低 | {n} 中 | {n} 高 | {n} 三分位の vol bp(低/中/高)" for n, _ in venues) + " |"
    print(head)
    print("|---|---|" + "---|" * (4 * len(venues)))
    for foot in FEET:
        for st, lab in STRENGTHS:
            row = [f"{foot} 分", lab]
            for _, d in venues:
                c = cell(d, foot, st, h)
                if not c:
                    row += ["—"] * 4
                    continue
                b = c["d8"]["bins"]
                for k in ("low", "mid", "high"):
                    row.append(f"{f(b[k]['mean_bp'])}{star(b[k]['ci95_bp'])} ({b[k]['n']:,})")
                row.append(" / ".join(f"{b[k]['mean_vol_prev']:.1f}" for k in ("low", "mid", "high")))
            print("| " + " | ".join(row) + " |")
    print()


def t6y(venues, foot_list=(5, 15), h=3):
    print(f"### 表 S7 — ボラ三分位の年別(h={h}): 「低 / 中 / 高」の平均 bp と (n)\n")
    for name, d in venues:
        ys = years(d)
        print(f"**{name}**\n")
        print("| 足 | 強さ | " + " | ".join(ys) + " |")
        print("|---|---|" + "---|" * len(ys))
        for foot in foot_list:
            for st, lab in STRENGTHS:
                c = cell(d, foot, st, h)
                if not c:
                    continue
                row = []
                for y in ys:
                    p = c["d8"]["per_year"].get(y, {})
                    row.append(" / ".join(f"{f(p[k]['mean_bp'], 1)} ({p[k]['n']})" if k in p else "—" for k in ("low", "mid", "high")))
                print(f"| {foot} 分 | {lab} | " + " | ".join(row) + " |")
        print()


# --------------------------------------------------------------- T7: D9b ----

def t7(venues, h=3):
    print(f"### 表 S8 — 実体比の層(D9b、`|実体| / ヒゲ`、h={h})。各マス: 平均 bp (n)\n")
    for name, d in venues:
        bins = ratio_labels(d)
        print(f"**{name}**\n")
        print("| 足 | 強さ | " + " | ".join(bins) + " |")
        print("|---|---|" + "---|" * len(bins))
        for foot in FEET:
            for st, lab in STRENGTHS:
                c = cell(d, foot, st, h)
                if not c:
                    continue
                b = c["d9b"]["bins"]
                print(f"| {foot} 分 | {lab} | " + " | ".join(
                    f"{f(b[k]['mean_bp'])}{star(b[k]['ci95_bp'])} ({b[k]['n']:,})" if k in b else "—" for k in bins) + " |")
        print()


def t7y(venues, foot_list=(5, 15), h=3):
    print(f"### 表 S9 — 実体比の層の年別(h={h}): 最小の層(実体 < 0.25 ヒゲ)と、上位 2 層(実体 ≥ ヒゲ。n で加重)の平均 bp (n)\n")
    for name, d in venues:
        ys = years(d)
        print(f"**{name}**\n")
        print("| 足 | 強さ | 層 | " + " | ".join(ys) + " |")
        print("|---|---|---|" + "---|" * len(ys))
        for foot in foot_list:
            for st, lab in STRENGTHS:
                c = cell(d, foot, st, h)
                if not c:
                    continue
                py = c["d9b"]["per_year"]
                labels = ratio_labels(d)          # 層のラベルは JSON から(手打ちしない)
                small, big = [], []
                for y in ys:
                    p = py.get(y, {})
                    s = p.get(labels[0])
                    small.append(f"{f(s['mean_bp'], 1)} ({s['n']})" if s else "—")
                    parts = [p[k] for k in labels[-2:] if k in p]
                    n = sum(x["n"] for x in parts)
                    big.append(f"{f(sum(x['mean_bp'] * x['n'] for x in parts) / n, 1)} ({n})" if n else "—")
                print(f"| {foot} 分 | {lab} | 実体 < 0.25 ヒゲ | " + " | ".join(small) + " |")
                print(f"| {foot} 分 | {lab} | 実体 ≥ ヒゲ | " + " | ".join(big) + " |")
        print()


# --------------------------------------------------------------- T8: D10 ----

def t8(venues, foot=5):
    print(f"### 表 S10 — 年の成分表(D10、{foot} 分足、門 `s19/b24`)。**引き算をしない**。realized vol は全足の |bp リターン| の平均\n")
    print("| 取引所 | 年 | 全足数 | realized vol bp | 通過率 | シグナル足の平均ヒゲ bp | 平均 \\|実体\\| bp | 実体 > ヒゲ(強い内) |")
    print("|---|---|---|---|---|---|---|---|")
    for name, d in venues:
        pc = d["per_year_components"].get(f"{foot}|{GATE}", {})
        for y in sorted(pc):
            p = pc[y]
            print(f"| {name} | {y} | {p['n_bars']:,} | {p['realized_vol_bp']:.2f} | {100 * p['signal_share']:.2f}% | "
                  f"{p['mean_wbp']:.1f} | {p['mean_abs_body_bp']:.1f} | {100 * p['strong_body_gt_wick_share']:.1f}% |")
    print()


# --------------------------------------------------------------- T9: D11 ----

def t9(venues, h=3):
    print(f"### 表 S11 — 裾を落とした平均(D11、h={h}): 生の平均 / 両側 1% トリム / 両側 5% トリム\n")
    head = "| 足 | 強さ | " + " | ".join(f"{n} 生 | {n} トリム 1% | {n} トリム 5%" for n, _ in venues) + " |"
    print(head)
    print("|---|---|" + "---|" * (3 * len(venues)))
    for foot in FEET:
        for st, lab in STRENGTHS:
            row = [f"{foot} 分", lab]
            for _, d in venues:
                c = cell(d, foot, st, h)
                if not c:
                    row += ["—"] * 3
                    continue
                x = c["d11"]
                row += [f(x["mean_bp"]), f(x["trim_1pct_bp"]), f(x["trim_5pct_bp"])]
            print("| " + " | ".join(row) + " |")
    print()


# --------------------------------------------------------------- T10: D6 ----

def t10(venues, foot_list=(5, 15), h=3):
    print(f"### 表 S12 — 時間帯(D6、UTC 3 時間 × 8 区分、h={h})。各マス: 平均 bp (n)\n")
    bins = ["00-03", "03-06", "06-09", "09-12", "12-15", "15-18", "18-21", "21-24"]
    for name, d in venues:
        print(f"**{name}**\n")
        print("| 足 | 強さ | " + " | ".join(bins) + " |")
        print("|---|---|" + "---|" * len(bins))
        for foot in foot_list:
            for st, lab in STRENGTHS:
                c = cell(d, foot, st, h)
                if not c:
                    continue
                b = c["d6"]["bins"]
                print(f"| {foot} 分 | {lab} | " + " | ".join(
                    f"{f(b[str(i)]['mean_bp'])}{star(b[str(i)]['ci95_bp'])} ({b[str(i)]['n']:,})" if str(i) in b else "—"
                    for i in range(len(bins))) + " |")
        print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()
    venues = load()
    names = ", ".join(n for n, _ in venues)
    print(f"# K1 深掘り — 第 9 部の要約表(生成物。出所 {names} の `robustness.json`)\n")
    print("`*` = 日ブロックブートストラップ 200 回(セルごとに種を固定)の 95% 区間が 0 を跨がない。単位 bp、経費なし。門は `s19/b24`。\n")
    for name, d in venues:
        rg = d["reproduction_gate"]
        ok = sum(1 for r in rg if r.get("ok"))
        print(f"- {name}: 期間 {d['explore'][0]} 〜 {d['explore'][1]}、D1 の再現ゲート {ok}/{len(rg)} 一致")
    print()
    t1(venues)
    t2(venues)
    t3(venues)
    t4(venues)
    t5(venues)
    t6(venues)
    t6y(venues)
    t7(venues)
    t7y(venues)
    t8(venues)
    t9(venues)
    t10(venues)


if __name__ == "__main__":
    main()
