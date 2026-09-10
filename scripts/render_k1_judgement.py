"""K1 判定の表(`docs/PHASE2/K1/JUDGEMENT_PREREG.md` §2)を機構 JSON から生成する(手打ちしない)。

読むもの:
    2017-2019(既存。**再計算しない**):
        docs/PHASE2/K1/effect_flip_noinval_delay.json  … 判定の設計(H1+H2a+H3)
        docs/PHASE2/K1/effect_flip_noinval.json        … 参考列(H1+H2a、その足の終値)
    2020-2021(封印を開けて 1 回だけ実行。`docs/PHASE2/K1/judgement/` 配下):
        effect_flip_noinval_delay_2020_2021.json / effect_flip_noinval_2020_2021.json
    Binance(in-sample、参照):
        docs/PHASE2/K1/binance/effect_flip_noinval_delay.json
    ボラ三分位(Deliverable C): vol_terciles_2017_2021.json

**per_year に無い量**(セルごとの区間・sd・分位・保有中央値)は、その JSON が測った
**期間全体で 1 つの値**である(2017-2019 は 3 年合算、2020-2021 は 2 年合算。
`measure_katsuo_effect.py` はブートストラップ区間を年ごとには出していない)。
per_year にある n・mean_bp だけが年ごとの値で、総損益 = n × mean_bp。
**この表はその区別を保ったまま出す**(合算値を年別のふりをしない)。

出すもの: (a) 主統計 2 セル(`s19/b24` の 5 分・15 分・弱い)の判定設計。年別 n・総損益、
期間合算の平均[区間]・sd・p05・保有中央値 (b) 全 78 セル(弱い)の 2020・2021 総損益と符号数
(c) 参考列(その足の終値)の同じ形 (d) 参考: 「両方」「強い」の 2020〜2021
(e) Binance の同じ設計(in-sample)の 2020・2021 を横に (f) ボラ三分位

    PYTHONPATH=src:scripts python scripts/render_k1_judgement.py > docs/PHASE2/K1/judgement/JUDGEMENT_TABLES.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
K1 = REPO / "docs" / "PHASE2" / "K1"
J = K1 / "judgement"

FEET = (1, 3, 5, 15, 30, 60)
MAIN_FEET = (5, 15)
GATE = "s19/b24"


def load(path: Path):
    return json.loads(path.read_text("utf-8")) if path.exists() else None


def cell(d, ft, g, st):
    return d["cells"].get(f"{ft}|{g}|{st}") if d else None


def total_of(c, y):
    p = c["per_year"].get(str(y)) if c else None
    return (round(p["n"] * p["mean_bp"], 1), p["n"]) if p else (None, 0)


def fmt0(x):
    return "—" if x is None else f"{x:+,.0f}"


def f(x, d=2):
    return "—" if x is None else f"{x:+.{d}f}"


def star(ci):
    return "*" if ci and ci[0] is not None and ci[0] == ci[0] and (ci[0] > 0 or ci[1] < 0) else ""


def agg_row(label, c):
    """期間合算(区間・sd・p05・保有・n)。1 行。"""
    if not c:
        return f"| {label} | — | | | | |"
    q = c.get("quantiles_bp", {}).get("p05")
    return (f"| {label} | {f(c['mean_bp'])}{star(c['ci95_bp'])} "
            f"[{f(c['ci95_bp'][0])}, {f(c['ci95_bp'][1])}] | {c['sd_bp']:.1f} | "
            f"{f(q, 1) if q is not None else '—'} | {c['hold_median']} | {c['n']:,} |")


def per_year_row(label, cells_by_year, years):
    """年別 n・総損益。`cells_by_year[y]` は年 y を含む cell(無ければ None)。"""
    parts = []
    tot, ntot = 0.0, 0
    for y in years:
        c = cells_by_year.get(y)
        t, n = total_of(c, y) if c else (None, 0)
        parts.append(f"{fmt0(t)} ({n:,})" if t is not None else "—")
        if t is not None:
            tot += t
            ntot += n
    return f"| {label} | " + " | ".join(parts) + f" | **{fmt0(round(tot, 1))}** ({ntot:,}) |"


def table_a_c(title, note, d_1719, d_2021, feet=MAIN_FEET, strength="weak", strength_label="弱い"):
    """(a)/(c) 共通の形。`d_1719` は 2017-2019(既存)、`d_2021` は 2020-2021(judgement/)。"""
    print(f"### {title}\n")
    print(f"{note}\n")
    years = [2017, 2018, 2019, 2020, 2021]
    for ft in feet:
        c19 = cell(d_1719, ft, GATE, strength)
        c21 = cell(d_2021, ft, GATE, strength)
        print(f"**{ft} 分・{strength_label}**\n")
        print("| 期間(合算) | 平均 [区間] | sd | p05 | 保有中央値 | n |")
        print("|---|---|---|---|---|---|")
        print(agg_row("2017-2019", c19))
        print(agg_row("2020-2021", c21))
        print()
        print("| | " + " | ".join(str(y) for y in years) + " | 合計 |")
        print("|---|" + "---|" * (len(years) + 1))
        by_year = {2017: c19, 2018: c19, 2019: c19, 2020: c21, 2021: c21}
        print(per_year_row("年別 n・総損益(bp)", by_year, years))
        print()


def table_b(d_2021, feet=FEET, strength="weak"):
    gates = d_2021["family"]["gates"]
    print("### 表 (b) — 全 78 セル(足 6 × 門 13、強さ「弱い」)の 2020・2021 総損益と符号\n")
    print("| 門 | 足 | 2020 総損益 (n) | 2021 総損益 (n) | 両年正 |")
    print("|---|---|---|---|---|")
    pos2020 = pos2021 = pos_both = total_cells = 0
    for g in gates:
        for ft in feet:
            c = cell(d_2021, ft, g, strength)
            if not c:
                print(f"| `{g}` | {ft} 分 | — | — | |")
                continue
            t20, n20 = total_of(c, 2020)
            t21, n21 = total_of(c, 2021)
            total_cells += 1
            p20 = t20 is not None and t20 > 0
            p21 = t21 is not None and t21 > 0
            pos2020 += p20
            pos2021 += p21
            pos_both += p20 and p21
            print(f"| `{g}` | {ft} 分 | {fmt0(t20)} ({n20:,}) | {fmt0(t21)} ({n21:,}) | "
                  f"{'○' if p20 and p21 else ''} |")
    print()
    print(f"符号数(78 セル中): 2020 正 = **{pos2020}/{total_cells}**、"
          f"2021 正 = **{pos2021}/{total_cells}**、両年正 = {pos_both}/{total_cells}\n")


def table_d(d_2021, feet=MAIN_FEET):
    print("### 表 (d) — 参考: 「両方」「強い」の 2020〜2021(判定の統計ではない。門 `s19/b24`)\n")
    years = [2020, 2021]
    for ft in feet:
        for st, lab in (("both", "両方"), ("strong", "強い")):
            c = cell(d_2021, ft, GATE, st)
            print(f"**{ft} 分・{lab}**\n")
            print("| 期間(合算) | 平均 [区間] | sd | p05 | 保有中央値 | n |")
            print("|---|---|---|---|---|---|")
            print(agg_row("2020-2021", c))
            print()
            print("| | " + " | ".join(str(y) for y in years) + " | 合計 |")
            print("|---|" + "---|" * (len(years) + 1))
            print(per_year_row("年別 n・総損益(bp)", {2020: c, 2021: c}, years))
            print()


def table_e(d_binance, d_bitmex_2021, feet=MAIN_FEET, strength="weak"):
    print("### 表 (e) — Binance の同じ設計(H1+H2a+H3、弱い、`s19/b24`)2020・2021(**in-sample**、参照。BitMEX の判定 2020-2021 と横に)\n")
    print("| 足 | 取引所 | 2020 n | 2020 平均 bp | 2020 総損益 | 2021 n | 2021 平均 bp | 2021 総損益 |")
    print("|---|---|---|---|---|---|---|---|")
    for ft in feet:
        for name, d in (("BitMEX(判定)", d_bitmex_2021), ("Binance(in-sample)", d_binance)):
            c = cell(d, ft, GATE, strength)
            if not c:
                print(f"| {ft} 分 | {name} | — | — | — | — | — | — |")
                continue
            p20 = c["per_year"].get("2020")
            p21 = c["per_year"].get("2021")
            t20 = round(p20["n"] * p20["mean_bp"], 1) if p20 else None
            t21 = round(p21["n"] * p21["mean_bp"], 1) if p21 else None
            n20 = f"{p20['n']:,}" if p20 else "—"
            m20 = f(p20["mean_bp"]) if p20 else "—"
            n21 = f"{p21['n']:,}" if p21 else "—"
            m21 = f(p21["mean_bp"]) if p21 else "—"
            print(f"| {ft} 分 | {name} | {n20} | {m20} | {fmt0(t20)} | {n21} | {m21} | {fmt0(t21)} |")
    print()


def table_f(d_vol, feet=MAIN_FEET):
    print("### 表 (f) — D8 ボラ三分位を判定区間に当てる(`vol_terciles_2017_2021.json`。"
          "境目は 2017-2019 の判定設計の取引だけから決め、2020-2021 はその境目で分類)\n")
    for ft in feet:
        fd = d_vol["feet"][str(ft)]
        e1, e2 = fd["edges_bp"]
        print(f"**{ft} 分**(境目 = {e1:g} / {e2:g} bp。2017-2019 の入口 vol_prev の 33/66 パーセンタイル。"
              f"vol 無し {fd['n_no_vol']} 件)\n")
        print("| 年 | low n | low 平均 | low 総損益 | mid n | mid 平均 | mid 総損益 | high n | high 平均 | high 総損益 |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        for y in ("2017", "2018", "2019", "2020", "2021"):
            row = fd["per_year"][y]
            cells = []
            for name in ("low", "mid", "high"):
                b = row[name]
                cells += [f"{b['n']:,}", f(b["mean_bp"]) if b["mean_bp"] is not None else "—",
                          fmt0(b["total_bp"])]
            print(f"| {y} | " + " | ".join(cells) + " |")
        print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()

    d_delay_1719 = load(K1 / "effect_flip_noinval_delay.json")
    d_ref_1719 = load(K1 / "effect_flip_noinval.json")
    d_delay_2021 = load(J / "effect_flip_noinval_delay_2020_2021.json")
    d_ref_2021 = load(J / "effect_flip_noinval_2020_2021.json")
    d_binance = load(K1 / "binance" / "effect_flip_noinval_delay.json")
    d_vol = load(J / "vol_terciles_2017_2021.json")

    print("# K1 判定 — 封印 2020〜2021 を開けた結果(生成物。`JUDGEMENT_PREREG.md` §2)\n")
    print("設計は固定(H1+H2a+H3、弱いだけ、門 `s19/b24` が主統計)。**開封は 1 回。この設計で"
          "封印を再利用することはできない。** 帰無・MDE・判定バーは作っていない。経費は引いていない。"
          "単位 bp、建玉 1 単位。`*` = 期間合算のブートストラップ区間が 0 を跨がない。\n")
    print(f"読み込み実績: BitMEX 2017-2019 = {d_delay_1719['load']['rows']:,} 行 "
          f"({d_delay_1719['explore'][0]} 〜 {d_delay_1719['explore'][1]})、"
          f"2020-2021 = {d_delay_2021['load']['rows']:,} 行 "
          f"({d_delay_2021['explore'][0]} 〜 {d_delay_2021['explore'][1]})。\n")

    table_a_c("表 (a) — 主統計: 判定の設計(H1+H2a+H3)、門 `s19/b24`",
              "2017-2019 は `effect_flip_noinval_delay.json`(既存・再計算しない)、"
              "2020-2021 は `judgement/effect_flip_noinval_delay_2020_2021.json`(今回、封印を開けて実行)。",
              d_delay_1719, d_delay_2021)

    table_b(d_delay_2021)

    table_a_c("表 (c) — 参考列: その足の終値で執行(H1+H2a、H3 なし)、門 `s19/b24`",
              "2017-2019 は `effect_flip_noinval.json`、2020-2021 は `judgement/effect_flip_noinval_2020_2021.json`。"
              "同じ設計で執行だけが違う(判定の統計ではなく、②が取れない価格との比較用)。",
              d_ref_1719, d_ref_2021)

    table_d(d_delay_2021)
    table_e(d_binance, d_delay_2021)
    table_f(d_vol)


if __name__ == "__main__":
    main()
