"""K1 取引所横断 段階 1 の表(`XVENUE_PREREG.md` §3、表 (a)〜(f))を機構 JSON から生成する(手打ちしない)。

読むもの:
    docs/PHASE2/K1/xvenue/effect_binance_to_bitflyer.json               … 設計(2017-08-17〜2026-08-31、1 回)
    docs/PHASE2/K1/xvenue/effect_binance_to_bitflyer_sameclose.json     … 参考列 (iii)
    docs/PHASE2/K1/xvenue/effect_binance_to_bitflyer_2018_2021.json     … 設計・副期間区間
    docs/PHASE2/K1/xvenue/effect_binance_to_bitflyer_2022_2026.json     … 設計・主期間区間
    docs/PHASE2/K1/xvenue/alignment.json                                … 結合の統計
    docs/PHASE2/K1/xvenue/vol_terciles.json                             … ボラ三分位
    docs/PHASE2/K1/binance/effect_flip_noinval_delay.json               … 参考列 (i)(既存・再計算しない)
    docs/PHASE2/K1/bitflyer/effect_flip_noinval_delay.json              … 参考列 (ii)(既存・再計算しない)

per_year にある n・mean_bp だけが年ごとの値。総損益 = n × mean_bp。
セルごとの区間・sd・分位・保有中央値は測った期間全体で 1 つの値(サブ実行の期間合算値を使う)。
サブ実行の per_year は全期間実行の per_year と、既知の境界効果(1 取引のずれ、境界年のみ)を
除いて一致することを assert する(`render_k1_fresh_bitflyer.py` と同じ形)。

    PYTHONPATH=src:scripts python scripts/render_k1_xvenue.py > docs/PHASE2/K1/xvenue/XVENUE_TABLES.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
K1 = REPO / "docs" / "PHASE2" / "K1"
XV = K1 / "xvenue"
BF = K1 / "bitflyer"
BN = K1 / "binance"

MAIN_FEET = (5, 15)
FEET = (1, 3, 5, 15, 30, 60)
GATE = "s19/b24"
YEARS_MAIN_TABLE = list(range(2018, 2027))     # 表 (a)/(c)/(f): 2018〜2026(2017 は Binance 側が 8 月開始で部分年)
YEARS_2022_26 = list(range(2022, 2027))
YEARS_2018_21 = list(range(2018, 2022))
BOUNDARY_YEAR_SUB1 = 2021
BOUNDARY_YEAR_SUB2 = 2022


def load(path: Path):
    if not path.exists():
        return None
    import json
    return json.loads(path.read_text("utf-8"))


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


def assert_per_year_identity(full, sub, years, label, boundary_years):
    """サブ実行(期間を切った再実行)の年別 n・mean_bp が全期間実行と恒等であることを確認する。

    既知の境界効果(H2a は反対シグナルまで建玉を持つので、サブ実行の外側に隣接するデータが
    無いことで境界年がずれうる。`render_k1_fresh_bitflyer.assert_per_year_identity` と同じ理由)。
    xvenue では 2 本のサブ実行が接する境界が 2 箇所(2018/2021 の外側 = 2017・2022 と、
    2022 の外側 = 2021)あるので、`boundary_years` は複数年の集合で渡す。観測された形は
    n がちょうど 1 件ずれる場合と、n は同じで最初の 1 件の内訳(実際に建てた足)が違う場合の
    両方があり、いずれも境界年 1 年に限られる。それ以外の年の不一致は本当のバグとして落とす。
    """
    bad, boundary_diffs = [], []
    for ft in MAIN_FEET:
        cf = cell(full, ft, GATE, "weak")
        cs = cell(sub, ft, GATE, "weak")
        if cf is None or cs is None:
            bad.append(f"{ft}分: 片方に無し(full={cf is not None}, sub={cs is not None})")
            continue
        for y in years:
            pf = cf["per_year"].get(str(y))
            ps = cs["per_year"].get(str(y))
            if pf == ps:
                continue
            if y in boundary_years and pf and ps:
                boundary_diffs.append(f"{ft}分/{y}(既知の境界効果、境界年 1 件限り): full={pf} vs sub={ps}")
                continue
            bad.append(f"{ft}分/{y}: full={pf} vs sub={ps}")
    if bad:
        raise SystemExit(f"assert 失敗({label}): per_year がサブ実行と全期間実行で一致しない: {bad}")
    if boundary_diffs:
        print(f"  [{label}] 既知の境界効果(境界年のみ):", file=sys.stderr)
        for d in boundary_diffs:
            print(f"    {d}", file=sys.stderr)


def table_a(d_design, d_sub1, d_sub2):
    print("### 表 (a) — 主統計: 設計(H1+H2a+H3、シグナル=Binance・価格=bitFlyer)、"
          f"門 `{GATE}`、弱い。年別 {YEARS_MAIN_TABLE[0]}〜{YEARS_MAIN_TABLE[-1]}\n")
    print("`xvenue/effect_binance_to_bitflyer.json`(2017-08-17〜2026-08-31、1 回)。"
          "区間・sd・p05・保有中央値はサブ実行(`_2018_2021.json` / `_2022_2026.json`)の期間合算値。"
          "年別 n・mean_bp はサブ実行と全期間実行で恒等であることを assert 済み。\n")
    for ft in MAIN_FEET:
        c = cell(d_design, ft, GATE, "weak")
        c1 = cell(d_sub1, ft, GATE, "weak")
        c2 = cell(d_sub2, ft, GATE, "weak")
        print(f"**{ft} 分・弱い**\n")
        print("| 年 | n | 平均 bp | 総損益 | 保有中央値 |")
        print("|---|---|---|---|---|")
        for y in YEARS_MAIN_TABLE:
            p = c["per_year"].get(str(y)) if c else None
            if not p:
                print(f"| {y} | — | — | — | |")
                continue
            t = round(p["n"] * p["mean_bp"], 1)
            print(f"| {y} | {p['n']:,} | {f(p['mean_bp'])} | {fmt0(t)} | |")
        print()
        print("| 期間(合算、サブ実行) | 平均 [区間] | sd | p05 | 保有中央値 | n |")
        print("|---|---|---|---|---|---|")
        for label, cc in (("2018-2021", c1), ("2022-2026", c2)):
            if not cc:
                print(f"| {label} | — | | | | |")
                continue
            q = cc.get("quantiles_bp", {}).get("p05")
            print(f"| {label} | {f(cc['mean_bp'])}{star(cc['ci95_bp'])} "
                  f"[{f(cc['ci95_bp'][0])}, {f(cc['ci95_bp'][1])}] | {cc['sd_bp']:.1f} | "
                  f"{f(q, 1) if q is not None else '—'} | {cc['hold_median']} | {cc['n']:,} |")
        print()


def table_b(d_design):
    gates = d_design["family"]["gates"]
    print("### 表 (b) — 全 78 セル(足 6 × 門 13、強さ「弱い」)の年別総損益と符号(2022〜2026)\n")
    for y in YEARS_2022_26:
        print(f"**{y}**\n")
        print("| 門 | 足 | 総損益 (n) | 正 |")
        print("|---|---|---|---|")
        pos = total_cells = 0
        for g in gates:
            for ft in FEET:
                c = cell(d_design, ft, g, "weak")
                if not c:
                    print(f"| `{g}` | {ft} 分 | — | |")
                    continue
                t, n = total_of(c, y)
                total_cells += 1
                p = t is not None and t > 0
                pos += p
                print(f"| `{g}` | {ft} 分 | {fmt0(t)} ({n:,}) | {'○' if p else ''} |")
        print()
        print(f"{y} 符号数(78 セル中): 正 = **{pos}/{total_cells}**\n")


def table_c(d_design, d_bn, d_bf, d_sameclose):
    print("### 表 (c) — 参考列 3 つを横に(門 `s19/b24`、弱い)。年別 "
          f"{YEARS_MAIN_TABLE[0]}〜{YEARS_MAIN_TABLE[-1]}\n")
    print("(i) `binance/effect_flip_noinval_delay.json`(Binance 同一取引所、既存・in-sample)。"
          "(ii) `bitflyer/effect_flip_noinval_delay.json`(bitFlyer 自身のシグナル、既存)。"
          "(iii) `xvenue/effect_binance_to_bitflyer_sameclose.json`(横断・H3 無し、"
          "取れない価格 = Binance の足 i の確定と同時刻の bitFlyer 足 i の終値)。\n")
    for ft in MAIN_FEET:
        c_i = cell(d_bn, ft, GATE, "weak")
        c_ii = cell(d_bf, ft, GATE, "weak")
        c_iii = cell(d_sameclose, ft, GATE, "weak")
        print(f"**{ft} 分・弱い**\n")
        print("| 年 | (i) Binance 平均 | (i) 総損益 | (ii) bitFlyer 平均 | (ii) 総損益 |"
              " (iii) 横断・同時刻 平均 | (iii) 総損益 |")
        print("|---|---|---|---|---|---|---|")
        for y in YEARS_MAIN_TABLE:
            row = []
            for c in (c_i, c_ii, c_iii):
                p = c["per_year"].get(str(y)) if c else None
                if p:
                    row += [f(p["mean_bp"]), fmt0(round(p["n"] * p["mean_bp"], 1))]
                else:
                    row += ["—", "—"]
            print(f"| {y} | " + " | ".join(row) + " |")
        print()


def table_d(d_vol):
    print("### 表 (d) — ボラ三分位(主統計セル。境目: BitMEX 固定値 / Binance 2018-2019 のこの設計の取引)\n")
    if not d_vol:
        print("_(未生成)_\n")
        return
    for ft in MAIN_FEET:
        fd = d_vol["feet"].get(str(ft))
        if not fd:
            print(f"**{ft} 分**: _(未生成)_\n")
            continue
        print(f"**{ft} 分**(own edges(Binance 2018-2019) = {fd['edges_bp_own']} bp、"
              f"BitMEX 固定 edges = {fd['edges_bp_bitmex_fixed']} bp、vol 無し {fd['n_no_vol']} 件)\n")
        for edge_key, edge_label in (("per_year_own_edges", "own edges(Binance 2018-2019 で決定)"),
                                      ("per_year_bitmex_fixed_edges", "BitMEX 固定 edges")):
            print(f"_{edge_label}_\n")
            print("| 年 | low n | low 平均 | low 総損益 | mid n | mid 平均 | mid 総損益 |"
                  " high n | high 平均 | high 総損益 |")
            print("|---|---|---|---|---|---|---|---|---|---|")
            for y in sorted(int(yy) for yy in fd[edge_key]):
                row = fd[edge_key].get(str(y))
                if not row:
                    print(f"| {y} | — | — | — | — | — | — | — | — | — |")
                    continue
                cells = []
                for name in ("low", "mid", "high"):
                    b = row[name]
                    cells += [f"{b['n']:,}", f(b["mean_bp"]) if b["mean_bp"] is not None else "—",
                              fmt0(b["total_bp"])]
                print(f"| {y} | " + " | ".join(cells) + " |")
            print()


def table_e(d_align):
    print("### 表 (e) — 結合の統計(年別。分の内部結合で落ちた分の割合)\n")
    if not d_align:
        print("_(未生成)_\n")
        return
    print(f"合計: シグナル側 {d_align['totals']['minutes_signal']:,} 分 / 価格側 "
          f"{d_align['totals']['minutes_price']:,} 分 / 両方 {d_align['totals']['minutes_both']:,} 分 "
          f"(シグナル側の落ち {d_align['totals']['dropped_share_signal']:.2%}、"
          f"価格側の落ち {d_align['totals']['dropped_share_price']:.2%})\n")
    print("| 年 | シグナル側 分 | 価格側 分 | 両方 分 | シグナル側の落ち | 価格側の落ち |")
    print("|---|---|---|---|---|---|")
    for y in sorted(int(yy) for yy in d_align["per_year"]):
        r = d_align["per_year"][str(y)]
        ds = r["dropped_share_signal"]
        dp = r["dropped_share_price"]
        print(f"| {y} | {r['minutes_signal']:,} | {r['minutes_price']:,} | {r['minutes_both']:,} | "
              f"{'—' if ds is None else f'{ds:.2%}'} | {'—' if dp is None else f'{dp:.2%}'} |")
    print()


def table_f(d_design):
    print("### 表 (f) — 参考: 「両方」「強い」の主統計セル、年別 "
          f"{YEARS_MAIN_TABLE[0]}〜{YEARS_MAIN_TABLE[-1]}(門 `{GATE}`)\n")
    for ft in MAIN_FEET:
        for st, lab in (("both", "両方"), ("strong", "強い")):
            c = cell(d_design, ft, GATE, st)
            print(f"**{ft} 分・{lab}**\n")
            print("| 年 | n | 平均 bp | 総損益 |")
            print("|---|---|---|---|")
            for y in YEARS_MAIN_TABLE:
                p = c["per_year"].get(str(y)) if c else None
                if not p:
                    print(f"| {y} | — | — | — |")
                    continue
                t = round(p["n"] * p["mean_bp"], 1)
                print(f"| {y} | {p['n']:,} | {f(p['mean_bp'])} | {fmt0(t)} |")
            print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()

    d_design = load(XV / "effect_binance_to_bitflyer.json")
    d_sameclose = load(XV / "effect_binance_to_bitflyer_sameclose.json")
    d_sub1 = load(XV / "effect_binance_to_bitflyer_2018_2021.json")
    d_sub2 = load(XV / "effect_binance_to_bitflyer_2022_2026.json")
    d_align = load(XV / "alignment.json")
    d_vol = load(XV / "vol_terciles.json")
    d_gate = load(XV / "gate_result.json")
    d_bn = load(BN / "effect_flip_noinval_delay.json")
    d_bf = load(BF / "effect_flip_noinval_delay.json")

    if d_design is None:
        raise SystemExit("xvenue/effect_binance_to_bitflyer.json が無い(先に measure_katsuo_xvenue.py を実行)")

    assert_per_year_identity(d_design, d_sub1, YEARS_2018_21, "2018-2021 サブ実行", {2018, BOUNDARY_YEAR_SUB1})
    assert_per_year_identity(d_design, d_sub2, YEARS_2022_26, "2022-2026 サブ実行", {BOUNDARY_YEAR_SUB2})

    print("# K1 取引所横断 段階 1 — Binance シグナル × bitFlyer 価格(生成物。`XVENUE_PREREG.md` §3)\n")
    print("設計は固定(H1+H2a+H3、弱いだけが主統計、門 `s19/b24`)。**シグナル・強さ・決済判断はすべて "
          "Binance 現物の足、約定価格だけ bitFlyer FX_BTC_JPY。段階 1 は一度きり。** "
          "帰無・MDE・判定バーは作っていない。経費・SFD は引いていない。単位 bp、建玉 1 単位。"
          "`*` = 期間合算のブートストラップ区間が 0 を跨がない。\n")
    if d_gate:
        print(f"再現ゲート: {d_gate['n_ok']}/{d_gate['n_total']}(pass={d_gate['pass']})\n")
    print(f"読み込み実績: シグナル(Binance) {d_design['load']['signal']['rows']:,} 行 / "
          f"価格(bitFlyer) {d_design['load']['price']['rows']:,} 行、"
          f"範囲 {d_design['explore'][0]} 〜 {d_design['explore'][1]}\n")

    table_a(d_design, d_sub1, d_sub2)
    table_b(d_design)
    table_c(d_design, d_bn, d_bf, d_sameclose)
    table_d(d_vol)
    table_e(d_align)
    table_f(d_design)


if __name__ == "__main__":
    main()
