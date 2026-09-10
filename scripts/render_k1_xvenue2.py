"""K1 取引所横断 段階 2 の表(`XVENUE_PREREG.md` §2 段階 2、L-095)を機構 JSON から生成する。

段階 1(`render_k1_xvenue.py`)と同じ表 (a)〜(f) を Bybit シグナル × bitFlyer 価格で作る。
段階 1 と違い、主期間 2022-01-01〜2026-08-31 を 1 回の実行だけで測る(サブ期間分割は無い)。
参考列は (i) Bybit 同一取引所(段階 2 で初めて Bybit 価格を読む唯一の設計)・(ii) bitFlyer
自身のシグナル(既存 JSON、再計算なし)・(iii) 同時刻(取れない価格)に加え、
段階 1(Binance→bitFlyer)を横に並べる列を追加する。

読むもの:
    docs/PHASE2/K1/xvenue/effect_bybit_to_bitflyer.json        … 設計(2022-01-01〜2026-08-31、1 回)
    docs/PHASE2/K1/xvenue/effect_bybit_to_bitflyer_sameclose.json … 参考列 (iii)
    docs/PHASE2/K1/xvenue/effect_bybit_to_bybit.json            … 参考列 (i)(Bybit 同一取引所)
    docs/PHASE2/K1/xvenue/bybit_alignment.json                  … 結合の統計
    docs/PHASE2/K1/xvenue/bybit_vol_terciles.json               … ボラ三分位
    docs/PHASE2/K1/xvenue/bybit_data_check.json                 … データ検査
    docs/PHASE2/K1/bitflyer/effect_flip_noinval_delay.json      … 参考列 (ii)(既存・再計算しない)
    docs/PHASE2/K1/xvenue/effect_binance_to_bitflyer.json       … 段階 1(既存・再計算しない)

    PYTHONPATH=src:scripts python scripts/render_k1_xvenue2.py > docs/PHASE2/K1/xvenue/XVENUE2_TABLES.md
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
K1 = REPO / "docs" / "PHASE2" / "K1"
XV = K1 / "xvenue"
BF = K1 / "bitflyer"

MAIN_FEET = (5, 15)
FEET = (1, 3, 5, 15, 30, 60)
GATE = "s19/b24"
YEARS_MAIN = list(range(2022, 2027))


def load(path: Path):
    if not path.exists():
        return None
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


def table_a(d_design, d_stage1):
    print("### 表 (a) — 主統計: 設計(H1+H2a+H3、シグナル=Bybit・価格=bitFlyer)、"
          f"門 `{GATE}`、弱い。年別 {YEARS_MAIN[0]}〜{YEARS_MAIN[-1]}\n")
    print("`xvenue/effect_bybit_to_bitflyer.json`(2022-01-01〜2026-08-31、1 回。サブ期間分割は無い)。"
          "段階 1(Binance→bitFlyer、`effect_binance_to_bitflyer.json` の同期間切片)を並べて出す。\n")
    for ft in MAIN_FEET:
        c = cell(d_design, ft, GATE, "weak")
        c1 = cell(d_stage1, ft, GATE, "weak")
        print(f"**{ft} 分・弱い**\n")
        print("| 年 | n(段階2) | 平均 bp(段階2) | 総損益(段階2) | n(段階1) | 平均 bp(段階1) | 総損益(段階1) |")
        print("|---|---|---|---|---|---|---|")
        for y in YEARS_MAIN:
            row = []
            for c_ in (c, c1):
                p = c_["per_year"].get(str(y)) if c_ else None
                if p:
                    row += [f"{p['n']:,}", f(p["mean_bp"]), fmt0(round(p["n"] * p["mean_bp"], 1))]
                else:
                    row += ["—", "—", "—"]
            print(f"| {y} | " + " | ".join(row) + " |")
        print()
        if c:
            q = c.get("quantiles_bp", {}).get("p05")
            print(f"期間合算(2022-2026): {f(c['mean_bp'])}{star(c['ci95_bp'])} "
                  f"[{f(c['ci95_bp'][0])}, {f(c['ci95_bp'][1])}] / sd {c['sd_bp']:.1f} / "
                  f"p05 {f(q, 1) if q is not None else '—'} / 保有中央値 {c['hold_median']} / n {c['n']:,}\n")


def table_b(d_design):
    gates = d_design["family"]["gates"]
    print(f"### 表 (b) — 全 78 セル(足 6 × 門 13、強さ「弱い」)の年別総損益と符号({YEARS_MAIN[0]}〜{YEARS_MAIN[-1]})\n")
    for y in YEARS_MAIN:
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


def table_c(d_i, d_ii, d_iii, d_stage1):
    print(f"### 表 (c) — 参考列を横に(門 `{GATE}`、弱い)。年別 {YEARS_MAIN[0]}〜{YEARS_MAIN[-1]}\n")
    print("(i) `xvenue/effect_bybit_to_bybit.json`(Bybit 同一取引所。**段階 2 で唯一・最初で最後の"
          "Bybit 価格の読み**。既存の再計算ではなく本単位内の一部)。"
          "(ii) `bitflyer/effect_flip_noinval_delay.json`(bitFlyer 自身のシグナル、既存)。"
          "(iii) `xvenue/effect_bybit_to_bitflyer_sameclose.json`(横断・H3 無し、取れない価格)。"
          "段階1 = `xvenue/effect_binance_to_bitflyer.json`(Binance→bitFlyer、既存・再計算なし)。\n")
    for ft in MAIN_FEET:
        c_i = cell(d_i, ft, GATE, "weak")
        c_ii = cell(d_ii, ft, GATE, "weak")
        c_iii = cell(d_iii, ft, GATE, "weak")
        c_s1 = cell(d_stage1, ft, GATE, "weak")
        print(f"**{ft} 分・弱い**\n")
        print("| 年 | (i) Bybit同一 平均 | (i) 総損益 | (ii) bitFlyer自身 平均 | (ii) 総損益 |"
              " (iii) 横断・同時刻 平均 | (iii) 総損益 | 段階1 平均 | 段階1 総損益 |")
        print("|---|---|---|---|---|---|---|---|---|")
        for y in YEARS_MAIN:
            row = []
            for c in (c_i, c_ii, c_iii, c_s1):
                p = c["per_year"].get(str(y)) if c else None
                if p:
                    row += [f(p["mean_bp"]), fmt0(round(p["n"] * p["mean_bp"], 1))]
                else:
                    row += ["—", "—"]
            print(f"| {y} | " + " | ".join(row) + " |")
        print()


def table_d(d_vol):
    print("### 表 (d) — ボラ三分位(主統計セル。境目: BitMEX 固定値 / Binance 2018-2019 の設計の取引)\n")
    if not d_vol:
        print("_(未生成)_\n")
        return
    for ft in MAIN_FEET:
        fd = d_vol["feet"].get(str(ft))
        if not fd:
            print(f"**{ft} 分**: _(未生成)_\n")
            continue
        print(f"**{ft} 分**(own edges(Bybit 局所ボラ、Binance 2018-2019 で決めた既存の境目を再利用) = "
              f"{fd['edges_bp_own']} bp、BitMEX 固定 edges = {fd['edges_bp_bitmex_fixed']} bp、"
              f"vol 無し {fd['n_no_vol']} 件)\n")
        for edge_key, edge_label in (("per_year_own_edges", "own edges"),
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


def table_e(d_align, d_check):
    print("### 表 (e) — 結合の統計 + データ検査(年別)\n")
    if d_align:
        print(f"結合合計: シグナル側(Bybit) {d_align['totals']['minutes_signal']:,} 分 / 価格側(bitFlyer) "
              f"{d_align['totals']['minutes_price']:,} 分 / 両方 {d_align['totals']['minutes_both']:,} 分 "
              f"(シグナル側の落ち {d_align['totals']['dropped_share_signal']:.2%}、"
              f"価格側の落ち {d_align['totals']['dropped_share_price']:.2%})\n")
        print("| 年 | シグナル側 分 | 価格側 分 | 両方 分 | シグナル側の落ち | 価格側の落ち |")
        print("|---|---|---|---|---|---|")
        for y in sorted(int(yy) for yy in d_align["per_year"]):
            r = d_align["per_year"][str(y)]
            ds, dp = r["dropped_share_signal"], r["dropped_share_price"]
            print(f"| {y} | {r['minutes_signal']:,} | {r['minutes_price']:,} | {r['minutes_both']:,} | "
                  f"{'—' if ds is None else f'{ds:.2%}'} | {'—' if dp is None else f'{dp:.2%}'} |")
        print()
    else:
        print("_(alignment 未生成)_\n")
    if d_check:
        print("**データ検査(Bybit、`bybit_data_check.json`)**\n")
        print("| 年 | 欠測 | 古い終値 | OHLC不整合 | \\|r\\|>1000bp | s19/b24 通過率(5分/15分) | 除外 |")
        print("|---|---|---|---|---|---|---|")
        for y in sorted(int(yy) for yy in d_check["per_year"]):
            r = d_check["per_year"][str(y)]
            ms, ss = r["missing_share"], r["stale_close_share"]
            gp = r["gate_s19_b24_pass_rate"]
            g5 = gp.get("5", {}).get("pass_rate")
            g15 = gp.get("15", {}).get("pass_rate")
            print(f"| {y} | {'—' if ms is None else f'{ms:.2%}'} | {'—' if ss is None else f'{ss:.2%}'} | "
                  f"{r['ohlc_inconsistent_count']} | {r['extreme_return_gt_1000bp_count']} | "
                  f"{'—' if g5 is None else f'{g5:.2%}'} / {'—' if g15 is None else f'{g15:.2%}'} | "
                  f"{'✕' if r['excluded_from_reading'] else ''} |")
        print()
    else:
        print("_(data_check 未生成)_\n")


def table_f(d_design):
    print(f"### 表 (f) — 参考: 「両方」「強い」の主統計セル、年別 {YEARS_MAIN[0]}〜{YEARS_MAIN[-1]}(門 `{GATE}`)\n")
    for ft in MAIN_FEET:
        for st, lab in (("both", "両方"), ("strong", "強い")):
            c = cell(d_design, ft, GATE, st)
            print(f"**{ft} 分・{lab}**\n")
            print("| 年 | n | 平均 bp | 総損益 |")
            print("|---|---|---|---|")
            for y in YEARS_MAIN:
                p = c["per_year"].get(str(y)) if c else None
                if not p:
                    print(f"| {y} | — | — | — |")
                    continue
                t = round(p["n"] * p["mean_bp"], 1)
                print(f"| {y} | {p['n']:,} | {f(p['mean_bp'])} | {fmt0(t)} |")
            print()


def main() -> None:
    d_design = load(XV / "effect_bybit_to_bitflyer.json")
    d_sameclose = load(XV / "effect_bybit_to_bitflyer_sameclose.json")
    d_sameventure = load(XV / "effect_bybit_to_bybit.json")
    d_align = load(XV / "bybit_alignment.json")
    d_vol = load(XV / "bybit_vol_terciles.json")
    d_check = load(XV / "bybit_data_check.json")
    d_bf = load(BF / "effect_flip_noinval_delay.json")
    d_stage1 = load(XV / "effect_binance_to_bitflyer.json")

    if d_design is None:
        raise SystemExit("xvenue/effect_bybit_to_bitflyer.json が無い(先に measure_katsuo_xvenue.py を実行)")

    print("# K1 取引所横断 段階 2 — Bybit シグナル × bitFlyer 価格(生成物。`XVENUE_PREREG.md` §2 段階 2)\n")
    print("設計は段階 1 と同一(H1+H2a+H3、弱いだけが主統計、門 `s19/b24`)。**シグナル・強さ・決済判断は"
          "すべて Bybit BTCUSDT 無期限の足、約定価格だけ bitFlyer FX_BTC_JPY。段階 2 は一度きり。** "
          "帰無・MDE・判定バーは作っていない。経費・SFD は引いていない。単位 bp、建玉 1 単位。"
          "`*` = 期間合算のブートストラップ区間が 0 を跨がない。\n")
    print(f"読み込み実績: シグナル(Bybit) {d_design['load']['signal']['rows']:,} 行 / "
          f"価格(bitFlyer) {d_design['load']['price']['rows']:,} 行、"
          f"範囲 {d_design['explore'][0]} 〜 {d_design['explore'][1]}\n")

    table_a(d_design, d_stage1)
    table_b(d_design)
    table_c(d_sameventure, d_bf, d_sameclose, d_stage1)
    table_d(d_vol)
    table_e(d_align, d_check)
    table_f(d_design)


if __name__ == "__main__":
    main()
