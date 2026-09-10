"""K1 フレッシュ確認 — bitFlyer の表(`FRESH_BITFLYER_PREREG.md` §2)を機構 JSON から生成する(手打ちしない)。

読むもの:
    docs/PHASE2/K1/bitflyer/effect_flip_noinval_delay.json         … 設計(2017-2026、1 回)
    docs/PHASE2/K1/bitflyer/effect_flip_noinval.json               … 参考列(その足の終値)
    docs/PHASE2/K1/bitflyer/effect_flip_noinval_delay_2017_2021.json … 設計・副期間区間(2017-2021 サブ実行)
    docs/PHASE2/K1/bitflyer/effect_flip_noinval_delay_2022_2026.json … 設計・主期間区間(2022-2026 サブ実行)
    docs/PHASE2/K1/bitflyer/vol_terciles.json                      … ボラ三分位(bitFlyer own edges / BitMEX 固定 edges)
    docs/PHASE2/K1/bitflyer/data_check.json                        … データ検査
    docs/PHASE2/K1/effect_flip_noinval_delay.json                  … BitMEX 2017-2019(既存・再計算しない)
    docs/PHASE2/K1/judgement/effect_flip_noinval_delay_2020_2021.json … BitMEX 2020-2021(既存)
    docs/PHASE2/K1/binance/effect_flip_noinval_delay.json          … Binance(in-sample、既存)

per_year にある n・mean_bp だけが年ごとの値で、総損益 = n × mean_bp。
セルごとの区間・sd・分位・保有中央値は測った期間全体で 1 つの値である
(bitFlyer の全期間 2017-2026 実行は 1 つ、2017-2021 と 2022-2026 のサブ実行はそれぞれ 1 つ)。
サブ実行の per_year は全期間実行の per_year と**恒等でなければならない**(assert で確認)。

出すもの(§2、a〜g)。表を手で書き換えない — このスクリプトの出力をそのまま `FRESH_TABLES.md` にする。

    PYTHONPATH=src:scripts python scripts/render_k1_fresh_bitflyer.py > docs/PHASE2/K1/bitflyer/FRESH_TABLES.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
K1 = REPO / "docs" / "PHASE2" / "K1"
BF = K1 / "bitflyer"
J = K1 / "judgement"
BN = K1 / "binance"

FEET = (1, 3, 5, 15, 30, 60)
MAIN_FEET = (5, 15)
GATE = "s19/b24"
YEARS_ALL = list(range(2017, 2027))
YEARS_MAIN = list(range(2022, 2027))
YEARS_SUB = list(range(2017, 2022))


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


def assert_per_year_identity(full, sub, years, label, boundary_year=None):
    """サブ実行(期間を切った再実行)の年別 n・mean_bp が全期間実行と恒等であることを確認する。

    **既知の境界効果(判明・報告する。バグではない)**: H2a(無効化なし)は反対シグナルまで
    ポジションを持ち続けるので、`boundary_year`(サブ実行の端の年)で持ち越し中の建玉は
    全期間実行では後年のデータで最終的に決済されて `boundary_year` の取引として数えられるが、
    サブ実行はデータがそこで切れるため決済されず、その 1 件が欠ける
    (逆にサブ実行が「後ろ側」= 期間の先頭なら、素の pos=0 から始めるので前の建玉の持ち越しが無く、
    最初のシグナルで即座に新規建玉する分が 1 件多くなる)。**この 1 件のずれは `boundary_year` に
    限られ、他の全年は完全に一致する**ことを確認する(それ以外の年で不一致なら本当のバグとして落とす)。
    """
    bad = []
    boundary_diffs = []
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
            if y == boundary_year and pf and ps and abs(pf["n"] - ps["n"]) == 1:
                boundary_diffs.append(f"{ft}分/{y}(既知の境界効果、n 差 1): full={pf} vs sub={ps}")
                continue
            bad.append(f"{ft}分/{y}: full={pf} vs sub={ps}")
    if bad:
        raise SystemExit(f"assert 失敗({label}): per_year がサブ実行と全期間実行で一致しない"
                         f"(境界効果として許容した範囲を超える): {bad}")
    if boundary_diffs:
        print(f"  [{label}] 既知の境界効果(H2a の持ち越し建玉。境界年のみ、取引数の差はちょうど 1):", file=sys.stderr)
        for d in boundary_diffs:
            print(f"    {d}", file=sys.stderr)


def table_a(d_delay, d_sub_2017_2021, d_sub_2022_2026):
    print("### 表 (a) — 主統計: 設計(H1+H2a+H3)、門 `s19/b24`、弱い。年別 2017〜2026\n")
    print("`bitflyer/effect_flip_noinval_delay.json`(2017-2026、1 回)。区間・sd・p05・保有中央値は"
          "サブ実行(`effect_flip_noinval_delay_2017_2021.json` / `_2022_2026.json`)の期間合算値。"
          "年別 n・mean_bp はサブ実行と全期間実行で恒等であることを assert 済み。\n")
    for ft in MAIN_FEET:
        c = cell(d_delay, ft, GATE, "weak")
        c17 = cell(d_sub_2017_2021, ft, GATE, "weak")
        c22 = cell(d_sub_2022_2026, ft, GATE, "weak")
        print(f"**{ft} 分・弱い**\n")
        print("| 年 | n | 平均 bp | 総損益 | 保有中央値 |")
        print("|---|---|---|---|---|")
        for y in YEARS_ALL:
            p = c["per_year"].get(str(y)) if c else None
            if not p:
                print(f"| {y} | — | — | — | |")
                continue
            t = round(p["n"] * p["mean_bp"], 1)
            print(f"| {y} | {p['n']:,} | {f(p['mean_bp'])} | {fmt0(t)} | |")
        print()
        print("| 期間(合算、サブ実行) | 平均 [区間] | sd | p05 | 保有中央値 | n |")
        print("|---|---|---|---|---|---|")
        for label, cc in (("2017-2021", c17), ("2022-2026", c22)):
            if not cc:
                print(f"| {label} | — | | | | |")
                continue
            q = cc.get("quantiles_bp", {}).get("p05")
            print(f"| {label} | {f(cc['mean_bp'])}{star(cc['ci95_bp'])} "
                  f"[{f(cc['ci95_bp'][0])}, {f(cc['ci95_bp'][1])}] | {cc['sd_bp']:.1f} | "
                  f"{f(q, 1) if q is not None else '—'} | {cc['hold_median']} | {cc['n']:,} |")
        print()


def table_b(d_delay, feet=FEET):
    gates = d_delay["family"]["gates"]
    print("### 表 (b) — 全 78 セル(足 6 × 門 13、強さ「弱い」)の年別総損益と符号(2022〜2026)\n")
    for y in YEARS_MAIN:
        print(f"**{y}**\n")
        print("| 門 | 足 | 総損益 (n) | 正 |")
        print("|---|---|---|---|")
        pos = total_cells = 0
        for g in gates:
            for ft in feet:
                c = cell(d_delay, ft, g, "weak")
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


def table_c(d_ref):
    print("### 表 (c) — 参考列: その足の終値で執行(H1+H2a、H3 なし)、門 `s19/b24`、弱い。年別 2017〜2026\n")
    print("`bitflyer/effect_flip_noinval.json`。同じ設計で執行だけが違う(判定の統計ではなく、"
          "②が取れない価格との比較用)。\n")
    for ft in MAIN_FEET:
        c = cell(d_ref, ft, GATE, "weak")
        print(f"**{ft} 分・弱い(参考列)**\n")
        print("| 年 | n | 平均 bp | 総損益 |")
        print("|---|---|---|---|")
        for y in YEARS_ALL:
            p = c["per_year"].get(str(y)) if c else None
            if not p:
                print(f"| {y} | — | — | — |")
                continue
            t = round(p["n"] * p["mean_bp"], 1)
            print(f"| {y} | {p['n']:,} | {f(p['mean_bp'])} | {fmt0(t)} |")
        if c:
            q = c.get("quantiles_bp", {}).get("p05")
            print(f"\n期間合算(2017-2026): 平均 {f(c['mean_bp'])}{star(c['ci95_bp'])} "
                  f"[{f(c['ci95_bp'][0])}, {f(c['ci95_bp'][1])}], sd {c['sd_bp']:.1f}, "
                  f"p05 {f(q, 1) if q is not None else '—'}, 保有中央値 {c['hold_median']}, n {c['n']:,}\n")
        print()


def table_d(d_bf_delay, d_bitmex_1719, d_bitmex_2021, d_binance):
    print("### 表 (d) — 同じ年の取引所比較(門 `s19/b24`、弱い)\n")
    print("2017〜2021: bitFlyer vs BitMEX(2017-2019 は既存 `effect_flip_noinval_delay.json`、"
          "2020-2021 は `judgement/effect_flip_noinval_delay_2020_2021.json`)。"
          "2018〜2026: bitFlyer vs Binance(`binance/effect_flip_noinval_delay.json`、**in-sample**)。\n")
    for ft in MAIN_FEET:
        c_bf = cell(d_bf_delay, ft, GATE, "weak")
        print(f"**{ft} 分・弱い — 2017〜2021 vs BitMEX**\n")
        print("| 年 | bitFlyer n | bitFlyer 平均 | bitFlyer 総損益 | BitMEX n | BitMEX 平均 | BitMEX 総損益 | 平均比(bitFlyer/BitMEX) |")
        print("|---|---|---|---|---|---|---|---|")
        for y in YEARS_SUB:
            d_bm = d_bitmex_1719 if y <= 2019 else d_bitmex_2021
            c_bm = cell(d_bm, ft, GATE, "weak")
            pbf = c_bf["per_year"].get(str(y)) if c_bf else None
            pbm = c_bm["per_year"].get(str(y)) if c_bm else None
            tbf = round(pbf["n"] * pbf["mean_bp"], 1) if pbf else None
            tbm = round(pbm["n"] * pbm["mean_bp"], 1) if pbm else None
            ratio = (pbf["mean_bp"] / pbm["mean_bp"]) if pbf and pbm and pbm["mean_bp"] else None
            nbf = f"{pbf['n']:,}" if pbf else "—"
            mbf = f(pbf["mean_bp"]) if pbf else "—"
            nbm = f"{pbm['n']:,}" if pbm else "—"
            mbm = f(pbm["mean_bp"]) if pbm else "—"
            print(f"| {y} | {nbf} | {mbf} | {fmt0(tbf)} | {nbm} | {mbm} | {fmt0(tbm)} | "
                  f"{f(ratio, 2) if ratio is not None else '—'} |")
        print()
        print(f"**{ft} 分・弱い — 2018〜2026 vs Binance(in-sample)**\n")
        print("| 年 | bitFlyer n | bitFlyer 平均 | bitFlyer 総損益 | Binance n | Binance 平均 | Binance 総損益 |")
        print("|---|---|---|---|---|---|---|")
        for y in range(2018, 2027):
            c_bn = cell(d_binance, ft, GATE, "weak")
            pbf = c_bf["per_year"].get(str(y)) if c_bf else None
            pbn = c_bn["per_year"].get(str(y)) if c_bn else None
            tbf = round(pbf["n"] * pbf["mean_bp"], 1) if pbf else None
            tbn = round(pbn["n"] * pbn["mean_bp"], 1) if pbn else None
            nbf = f"{pbf['n']:,}" if pbf else "—"
            mbf = f(pbf["mean_bp"]) if pbf else "—"
            nbn = f"{pbn['n']:,}" if pbn else "—"
            mbn = f(pbn["mean_bp"]) if pbn else "—"
            print(f"| {y} | {nbf} | {mbf} | {fmt0(tbf)} | {nbn} | {mbn} | {fmt0(tbn)} |")
        print()


def table_e(d_vol):
    print("### 表 (e) — ボラ三分位 × 年(境目: bitFlyer 2017-2019 自前 / BitMEX 固定)\n")
    for ft in MAIN_FEET:
        fd = d_vol["feet"][str(ft)]
        print(f"**{ft} 分**(own edges = {fd['edges_bp_own']} bp、bitmex 固定 edges = {fd['edges_bp_bitmex_fixed']} bp、"
              f"vol 無し {fd['n_no_vol']} 件)\n")
        for edge_key, edge_label in (("per_year_own_edges", "own edges(bitFlyer 2017-2019 で決定)"),
                                      ("per_year_bitmex_fixed_edges", "BitMEX 固定 edges")):
            print(f"_{edge_label}_\n")
            print("| 年 | low n | low 平均 | low 総損益 | mid n | mid 平均 | mid 総損益 | high n | high 平均 | high 総損益 |")
            print("|---|---|---|---|---|---|---|---|---|---|")
            for y in YEARS_ALL:
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


def table_f(d_check):
    print("### 表 (f) — データ検査(年別。閾値: 古い終値 > 10% または欠測 > 5% → `excluded_from_reading`)\n")
    print(f"閾値: {d_check['thresholds']}\n")
    print("| 年 | 実在分 | 期待分 | 欠測 | 古い終値 | 出来高0 | OHLC不整合 | \\|r\\|>1000bp | 門 s19/b24 通過率(5分) | 通過率(15分) | 除外 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for y in range(2017, 2027):
        r = d_check["per_year"].get(str(y))
        if not r:
            print(f"| {y} | — | — | — | — | — | — | — | — | — | — |")
            continue
        g5 = r["gate_s19_b24_pass_rate"].get("5", {})
        g15 = r["gate_s19_b24_pass_rate"].get("15", {})
        zv = r["zero_volume_share"]
        print(f"| {y} | {r['minutes_present']:,} | {r['minutes_expected']:,} | "
              f"{r['missing_share']:.2%} | {r['stale_close_share']:.2%} | "
              f"{'判定不能' if zv is None else f'{zv:.2%}'} | {r['ohlc_inconsistent_count']} | "
              f"{r['extreme_return_gt_1000bp_count']} | "
              f"{f(g5.get('pass_rate'), 4) if g5.get('pass_rate') is not None else '—'} | "
              f"{f(g15.get('pass_rate'), 4) if g15.get('pass_rate') is not None else '—'} | "
              f"{'**除外**' if r['excluded_from_reading'] else ''} |")
    print()


def table_g(d_delay):
    print("### 表 (g) — 参考: 「両方」「強い」の主統計セル、年別 2017〜2026(門 `s19/b24`)\n")
    for ft in MAIN_FEET:
        for st, lab in (("both", "両方"), ("strong", "強い")):
            c = cell(d_delay, ft, GATE, st)
            print(f"**{ft} 分・{lab}**\n")
            print("| 年 | n | 平均 bp | 総損益 |")
            print("|---|---|---|---|")
            for y in YEARS_ALL:
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

    d_delay = load(BF / "effect_flip_noinval_delay.json")
    d_ref = load(BF / "effect_flip_noinval.json")
    d_sub_1721 = load(BF / "effect_flip_noinval_delay_2017_2021.json")
    d_sub_2226 = load(BF / "effect_flip_noinval_delay_2022_2026.json")
    d_vol = load(BF / "vol_terciles.json")
    d_check = load(BF / "data_check.json")
    d_bitmex_1719 = load(K1 / "effect_flip_noinval_delay.json")
    d_bitmex_2021 = load(J / "effect_flip_noinval_delay_2020_2021.json")
    d_binance = load(BN / "effect_flip_noinval_delay.json")

    assert_per_year_identity(d_delay, d_sub_1721, YEARS_SUB, "2017-2021 サブ実行", boundary_year=2021)
    assert_per_year_identity(d_delay, d_sub_2226, YEARS_MAIN, "2022-2026 サブ実行", boundary_year=2022)

    print("# K1 フレッシュ確認 — bitFlyer FX_BTC_JPY 1 分足(生成物。`FRESH_BITFLYER_PREREG.md` §2)\n")
    print("設計は固定(H1+H2a+H3、弱いだけが主統計、門 `s19/b24`)。**一度きり。以後この設計で bitFlyer の"
          "履歴は使えない。** 帰無・MDE・判定バーは作っていない。経費・SFD は引いていない。単位 bp、建玉 1 単位。"
          "`*` = 期間合算のブートストラップ区間が 0 を跨がない。年別の per_year はサブ実行と全期間実行で"
          "恒等であることを assert 済み(このスクリプトが起動時に確認する)。\n")
    print(f"読み込み実績: bitFlyer {d_delay['load']['rows']:,} 行"
          f"(読んだ {d_delay['load']['rows_read']:,} 行のうち null OHLC {d_delay['load']['dropped_null_ohlc']:,} 行を落とす)、"
          f"範囲 {d_delay['explore'][0]} 〜 {d_delay['explore'][1]}。"
          f"時刻の基準: {d_delay['load']['timestamp_basis']}\n")
    print("**逸脱(境界効果、判明・バグではない)**: サブ実行(2017-2021 / 2022-2026)の per_year は"
          "全期間実行(2017-2026)と、境界年(2021 / 2022)を除く全年で完全に一致する(assert 済み)。"
          "境界年だけ主統計セルの n がちょうど 1 件ずれる: H2a は反対シグナルまで建玉を持ち続けるので、"
          "全期間実行では境界をまたいで持ち越した建玉が後年のデータで決済され境界年の取引として数えられるが、"
          "データがそこで終わるサブ実行ではその 1 件が決済されず欠ける(2017-2021 側)、または"
          "サブ実行は pos=0 から始めるため持ち越しが無く最初のシグナルで即座に新規建玉して 1 件多くなる"
          "(2022-2026 側)。表 (a) の年別行はすべて全期間実行の値なので、この境界効果は表の数値には影響しない"
          "(サブ実行は期間合算の区間・sd・p05・保有中央値にのみ使う)。\n")

    table_a(d_delay, d_sub_1721, d_sub_2226)
    table_b(d_delay)
    table_c(d_ref)
    table_d(d_delay, d_bitmex_1719, d_bitmex_2021, d_binance)
    table_e(d_vol)
    table_f(d_check)
    table_g(d_delay)


if __name__ == "__main__":
    main()
