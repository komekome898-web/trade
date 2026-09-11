#!/usr/bin/env python3
"""④-1 執行層の経費の床: `docs/PHASE2/EXEC/exec_floor.json` を表 E-a〜E-i の Markdown
(`docs/PHASE2/EXEC/EXEC_FLOOR_TABLES.md`)に整形する。截断なし(EXEC_FLOOR_PREREG.md §8)。

    PYTHONPATH=src:scripts python scripts/render_exec_floor.py
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IN_JSON = REPO / "docs" / "PHASE2" / "EXEC" / "exec_floor.json"
OUT_MD = REPO / "docs" / "PHASE2" / "EXEC" / "EXEC_FLOOR_TABLES.md"

HOUR_LABELS = [f"{h:02d}-{h+3:02d}" for h in range(0, 24, 3)]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
VOL_LABELS = ["low", "mid", "high"]
SIZE_BIN_LABELS = ["<0.01", "0.01-0.05", "0.05-0.1", "0.1-0.5", ">=0.5"]


def fmt(v, nd=3):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def fmt_pct(v, nd=2):
    if v is None:
        return "-"
    return f"{v * 100:.{nd}f}%"


def row(cells):
    return "| " + " | ".join(str(c) for c in cells) + " |"


def table(headers, rows):
    out = [row(headers), row(["---"] * len(headers))]
    out.extend(row(r) for r in rows)
    return "\n".join(out)


def weighted_stat_row(label, st):
    return [label, f"{st.get('n', 0):,}", fmt(st.get("p10_bp")), fmt(st.get("p50_bp")), fmt(st.get("p90_bp"))]


def plain_stat_row(label, st, with_ci=False):
    r = [label, f"{st.get('n', 0):,}", fmt(st.get("mean_bp")), fmt(st.get("p10_bp")),
         fmt(st.get("p50_bp")), fmt(st.get("p90_bp"))]
    if with_ci:
        ci = st.get("ci95_bp") or [None, None]
        r.append(f"[{fmt(ci[0])}, {fmt(ci[1])}]")
    return r


def main() -> None:
    data = json.loads(IN_JSON.read_text(encoding="utf-8"))
    lines = []

    def h(level, text):
        lines.append(f"{'#' * level} {text}")
        lines.append("")

    def p(text):
        lines.append(text)
        lines.append("")

    h(1, "EXEC_FLOOR_TABLES -- ④-1 執行層の経費の床(表 E-a〜E-i)")
    p(f"生成元: `docs/PHASE2/EXEC/exec_floor.json`。{data['note']}")
    dr = data["data_ranges"]
    p(f"データ範囲: ticker/executions {dr['ticker_executions'][0]}〜{dr['ticker_executions'][1]} / "
      f"board_top5 {dr['board_top5'][0]}〜{dr['board_top5'][1]} / "
      f"K1 シグナル重なり {dr['k1_signal_overlap'][0]}〜{dr['k1_signal_overlap'][1]}")
    p(f"局所ボラ三分位の境目(直前100分の\\|close/close-1\\|平均): "
      f"{data['vol_tercile_edges_bp_like']}")

    # -- Data check -----------------------------------------------------
    h(2, "データ検査")
    dc = data["data_check"]
    p(dc["note"])
    p(f"欠測しきい値(ticker ギャップ): {dc['quote_gap_exclude_threshold_sec']} 秒")
    ov = dc["overall"]
    p(f"**全体**: ticker {ov['ticker_rows']:,} 行 / crossed {ov['crossed_count']:,} "
      f"({fmt_pct(ov['crossed_share'])}) / 気配欠測share {fmt_pct(ov['quote_missing_share'])} "
      f"({ov['n_gaps_over_threshold']} 区間、最大 {ov['largest_gaps_sec']} 秒) / "
      f"板 {ov['board_rows']:,} 行 / 非単調 {ov['board_nonmonotone_count']:,} "
      f"({fmt_pct(ov['board_nonmonotone_share'])}) / 約定 {ov['exec_rows']:,} 行 / "
      f"逆行 {ov['exec_regression_count']:,} ({fmt_pct(ov['exec_regression_share'])})")
    rows = []
    for d, e in sorted(dc["per_day"].items()):
        rows.append([d, f"{e['ticker_rows']:,}", e['crossed_count'],
                     fmt_pct(e.get("quote_missing_share")),
                     f"{e.get('board_rows', '-'):,}" if isinstance(e.get("board_rows"), int) else "-",
                     e.get("board_nonmonotone_count", "-"),
                     f"{e['exec_rows']:,}", e["exec_regression_count"]])
    p(table(["日付", "ticker行", "crossed", "気配欠測share", "板行", "板非単調", "約定行", "約定逆行"], rows))

    # -- E-a --------------------------------------------------------------
    h(2, "E-a 気配スプレッド((ask-bid)/mid, bp, 時間加重)")
    ea = data["e_a_quoted_spread"]
    p(ea["note"])
    p(f"除外重みの割合: {fmt_pct(ea['excluded_weight_share'])}")
    rows = [weighted_stat_row("全期間", ea["overall"])]
    p(table(["区分", "n(区間)", "p10", "p50", "p90"], rows))
    p("**UTC 時間帯 8 区分**")
    rows = [weighted_stat_row(lbl, ea["by_hour_utc"][lbl]) for lbl in HOUR_LABELS]
    p(table(["時間帯", "n", "p10", "p50", "p90"], rows))
    p("**曜日**")
    rows = [weighted_stat_row(w, ea["by_weekday"][w]) for w in WEEKDAYS]
    p(table(["曜日", "n", "p10", "p50", "p90"], rows))
    p("**局所ボラ三分位**")
    rows = [weighted_stat_row(v, ea["by_vol_tercile"][v]) for v in VOL_LABELS]
    p(table(["ボラ", "n", "p10", "p50", "p90"], rows))

    # -- E-b --------------------------------------------------------------
    h(2, "E-b 成行の片道コスト(板を歩く。bp vs mid)")
    eb = data["e_b_board_walk_cost"]
    p(eb["note"])
    p(f"有効サンプル {eb['n_samples_valid']:,} / 除外(非単調) {fmt_pct(eb['excluded_share'])}")
    for xs, cell in eb["sizes"].items():
        h(3, f"X = {xs} BTC")
        exh = cell["exhausted_count"]
        exh_sh = cell["exhausted_share_of_valid_samples"]
        p(f"exhausted(板の外): buy {exh['buy']:,} ({fmt_pct(exh_sh['buy'])}) / "
          f"sell {exh['sell']:,} ({fmt_pct(exh_sh['sell'])}) / "
          f"either {exh['either']:,} ({fmt_pct(exh_sh['either'])})")
        rows = []
        for side in ("buy", "sell", "roundtrip"):
            rows.append(plain_stat_row(f"全期間 {side}", cell["overall"][side]))
        p(table(["区分", "n", "mean", "p10", "p50", "p90"], rows))
        p("**時間帯別(roundtrip)**")
        rows = [plain_stat_row(lbl, cell["by_hour_utc"]["roundtrip"][lbl]) for lbl in HOUR_LABELS]
        p(table(["時間帯", "n", "mean", "p10", "p50", "p90"], rows))
        p("**ボラ三分位別(roundtrip)**")
        rows = [plain_stat_row(v, cell["by_vol_tercile"]["roundtrip"][v]) for v in VOL_LABELS]
        p(table(["ボラ", "n", "mean", "p10", "p50", "p90"], rows))

    # -- E-c --------------------------------------------------------------
    h(2, "E-c 実現スプレッド(|価格-直前mid|/mid, bp)")
    ec = data["e_c_realized_spread"]
    p(ec["note"])
    p(f"直前気配欠測で除外: {ec['excluded_count']:,} ({fmt_pct(ec['excluded_share'])})")
    for side in ("ALL", "BUY", "SELL"):
        cell = ec["by_side"][side]
        h(3, f"テイカー側 = {side}")
        rows = [plain_stat_row("全期間", cell["overall"])]
        p(table(["区分", "n", "mean", "p10", "p50", "p90"], rows))
        p("**時間帯別**")
        rows = [plain_stat_row(lbl, cell["by_hour_utc"][lbl]) for lbl in HOUR_LABELS]
        p(table(["時間帯", "n", "mean", "p10", "p50", "p90"], rows))
        p("**ボラ三分位別**")
        rows = [plain_stat_row(v, cell["by_vol_tercile"][v]) for v in VOL_LABELS]
        p(table(["ボラ", "n", "mean", "p10", "p50", "p90"], rows))
        p("**約定サイズビン別**")
        rows = [plain_stat_row(sbin, cell["by_size_bin"][sbin]) for sbin in SIZE_BIN_LABELS]
        p(table(["サイズ", "n", "mean", "p10", "p50", "p90"], rows))

    # -- E-d --------------------------------------------------------------
    h(2, "E-d 逆選択(代理、テイカー方向に符号付き mid 変化、bp)")
    ed = data["e_d_adverse_selection"]
    p(ed["note"])
    for h_key, by_side in ed["by_horizon"].items():
        h(3, f"H = {h_key} 秒")
        excl = ed["excluded_by_horizon"][h_key]
        excl_sh = ed["excluded_share_by_horizon"][h_key]
        p(f"除外(気配欠測): {excl:,} ({fmt_pct(excl_sh)})")
        for side in ("ALL", "BUY", "SELL"):
            cell = by_side[side]
            p(f"**テイカー側 = {side}**")
            rows = [plain_stat_row("全期間", cell["overall"], with_ci=True)]
            p(table(["区分", "n", "mean", "p10", "p50", "p90", "CI95"], rows))
            rows = [plain_stat_row(lbl, cell["by_hour_utc"][lbl], with_ci=True) for lbl in HOUR_LABELS]
            p("時間帯別:")
            p(table(["時間帯", "n", "mean", "p10", "p50", "p90", "CI95"], rows))
            rows = [plain_stat_row(v, cell["by_vol_tercile"][v], with_ci=True) for v in VOL_LABELS]
            p("ボラ三分位別:")
            p(table(["ボラ", "n", "mean", "p10", "p50", "p90", "CI95"], rows))
            rows = [plain_stat_row(sbin, cell["by_size_bin"][sbin], with_ci=True) for sbin in SIZE_BIN_LABELS]
            p("約定サイズビン別:")
            p(table(["サイズ", "n", "mean", "p10", "p50", "p90", "CI95"], rows))

    # -- E-e --------------------------------------------------------------
    h(2, "E-e 指値の代理量(触れられ率・触れられた後の逆選択)")
    ee = data["e_e_maker_proxy"]
    p(ee["note"])
    p(f"開始時気配欠測で除外した分: {ee['excluded_no_quote_minutes']:,}")
    for T, cell in ee["by_T"].items():
        h(3, f"T = {T} 秒")
        ov = cell["overall"]
        rows = [["全期間", f"{ov['n_valid_minutes']:,}", fmt_pct(ov["touched_share_buy"]),
                 fmt_pct(ov["touched_share_sell"]), fmt(ov["post_touch_drift_bp"]["mean_bp"]),
                 fmt(ov["post_touch_drift_bp"]["p50_bp"]),
                 f"[{fmt(ov['post_touch_drift_bp']['ci95_bp'][0])}, {fmt(ov['post_touch_drift_bp']['ci95_bp'][1])}]"]]
        p(table(["区分", "n分", "touched buy", "touched sell", "drift mean", "drift p50", "drift CI95"], rows))
        p("**時間帯別**")
        rows = []
        for lbl in HOUR_LABELS:
            c = cell["by_hour_utc"][lbl]
            rows.append([lbl, f"{c['n_valid_minutes']:,}", fmt_pct(c["touched_share_buy"]),
                         fmt_pct(c["touched_share_sell"]), fmt(c["post_touch_drift_bp"]["mean_bp"]),
                         fmt(c["post_touch_drift_bp"]["p50_bp"]),
                         f"[{fmt(c['post_touch_drift_bp']['ci95_bp'][0])}, {fmt(c['post_touch_drift_bp']['ci95_bp'][1])}]"])
        p(table(["時間帯", "n分", "touched buy", "touched sell", "drift mean", "drift p50", "drift CI95"], rows))
        p("**ボラ三分位別**")
        rows = []
        for v in VOL_LABELS:
            c = cell["by_vol_tercile"][v]
            rows.append([v, f"{c['n_valid_minutes']:,}", fmt_pct(c["touched_share_buy"]),
                         fmt_pct(c["touched_share_sell"]), fmt(c["post_touch_drift_bp"]["mean_bp"]),
                         fmt(c["post_touch_drift_bp"]["p50_bp"]),
                         f"[{fmt(c['post_touch_drift_bp']['ci95_bp'][0])}, {fmt(c['post_touch_drift_bp']['ci95_bp'][1])}]"])
        p(table(["ボラ", "n分", "touched buy", "touched sell", "drift mean", "drift p50", "drift CI95"], rows))

    # -- E-f --------------------------------------------------------------
    h(2, "E-f シグナル分の床(Binance/Bybit K1 デザイン、2026-08-20〜08-31)")
    ef = data["e_f_signal_minute_floor"]
    p(ef["note"])
    for src, feet in ef["sources"].items():
        for foot, info in feet.items():
            p(f"- {src} 足{foot}分: 弱いシグナルバー {info['n_signal_bars_weak']:,} / 全バー {info['n_bars']:,}")
    p("")
    unc = ef["unconditional_same_days"]
    p("**無条件(同じ日、全分)**")
    rows = [["E-a(全分)", f"{unc['e_a_same_days']['n']:,}", fmt(unc['e_a_same_days']['p50_bp']),
             fmt(unc['e_a_same_days']['p90_bp'])],
            ["E-b 0.01BTC roundtrip(板window内の全分)", f"{unc['e_b_001_same_days_board_window']['n']:,}",
             fmt(unc['e_b_001_same_days_board_window']['p50_bp']),
             fmt(unc['e_b_001_same_days_board_window']['p90_bp'])]]
    p(table(["量", "n", "p50", "p90"], rows))
    rows = []
    for T, c in unc["e_e"].items():
        rows.append([f"T={T}s", f"{c['n_valid_minutes']:,}", fmt_pct(c["touched_share_buy"]),
                     fmt_pct(c["touched_share_sell"]), fmt(c["post_touch_drift_bp"]["mean_bp"])])
    p(table(["T", "n分", "touched buy", "touched sell", "drift mean"], rows))

    p("**シグナル分(各セル)**")
    rows = []
    for key, cell in ef["cells"].items():
        rows.append([key, f"{cell['n_signal_minutes']:,}", f"{cell['n_signal_minutes_in_board_window']:,}",
                     fmt(cell["e_a"]["p50_bp"]), fmt(cell["e_a"]["p90_bp"]),
                     fmt(cell["e_b_001"]["p50_bp"]), fmt(cell["e_b_001"]["p90_bp"]),
                     f"{cell['e_b_001']['n']:,}"])
    p(table(["source|foot", "nシグナル分", "n板window内", "E-a p50", "E-a p90",
             "E-b001 p50", "E-b001 p90", "E-b001 n"], rows))
    for key, cell in ef["cells"].items():
        p(f"**{key} の E-e**")
        rows = []
        for T, c in cell["e_e"].items():
            rows.append([f"T={T}s", f"{c['n_valid_minutes']:,}", fmt_pct(c["touched_share_buy"]),
                         fmt_pct(c["touched_share_sell"]), fmt(c["post_touch_drift_bp"]["mean_bp"])])
        p(table(["T", "n分", "touched buy", "touched sell", "drift mean"], rows))

    # -- E-g --------------------------------------------------------------
    h(2, "E-g 資金調達率")
    eg = data["e_g_funding_rate"]
    p(eg["note"])
    rows = [["|rate| p50", fmt(eg["abs_rate_p50"], 6)], ["|rate| p90", fmt(eg["abs_rate_p90"], 6)],
            ["日次換算 p50", fmt(eg["daily_equivalent_p50"], 6)],
            ["日次換算 p90", fmt(eg["daily_equivalent_p90"], 6)],
            ["標本", f"{eg['sample_dates'][0]} 〜 {eg['sample_dates'][1]}({eg['n']} 行)"]]
    p(table(["量", "値"], rows))

    # -- E-h --------------------------------------------------------------
    h(2, "E-h 遅延")
    eh = data["e_h_latency"]
    p(eh["note"])
    rows = [["n", f"{eh['n']:,}"], ["標本範囲", f"{eh['sample_range'][0]} 〜 {eh['sample_range'][1]}"],
            ["delay_s p10", fmt(eh["delay_s_p10"], 6)], ["delay_s p50", fmt(eh["delay_s_p50"], 6)],
            ["delay_s p90", fmt(eh["delay_s_p90"], 6)], ["order-ack latency", eh["order_ack_latency"]]]
    p(table(["量", "値"], rows))

    # -- E-i --------------------------------------------------------------
    h(2, "E-i 床のまとめ")
    ei = data["e_i_floor_summary"]
    p(ei["note"])
    rt = ei["roundtrip_taker_cost_001btc_bp"]
    rows = [["無条件(板7日)", f"{rt['unconditional']['n']:,}", fmt(rt['unconditional']['p50']),
             fmt(rt['unconditional']['p90'])],
            ["高ボラ三分位(板7日)", f"{rt['high_vol_tercile']['n']:,}", fmt(rt['high_vol_tercile']['p50']),
             fmt(rt['high_vol_tercile']['p90'])]]
    for key, c in rt["k1_signal_minutes_by_source_foot"].items():
        rows.append([f"K1シグナル分 {key}", f"{c['n']:,}", fmt(c["p50_bp"]), fmt(c["p90_bp"])])
    p(table(["区分", "n", "p50", "p90"], rows))
    mk = ei["maker_touched_share_and_post_touch_drift"]
    rows = []
    for T in ("T60", "T300"):
        c = mk[T]
        rows.append([T, fmt_pct(c["touched_share_buy"]), fmt_pct(c["touched_share_sell"]),
                     fmt(c["post_touch_drift_bp"]["mean_bp"]),
                     f"[{fmt(c['post_touch_drift_bp']['ci95_bp'][0])}, {fmt(c['post_touch_drift_bp']['ci95_bp'][1])}]"])
    p(table(["T", "touched buy", "touched sell", "drift mean", "drift CI95"], rows))
    k1 = ei["k1_pre_cost_bp_per_trade_RESULT_18_2_not_recomputed"]
    rows = []
    for foot, c in k1.items():
        rows.append([foot, fmt(c["mean_bp"]), f"[{fmt(c['ci95_bp'][0])}, {fmt(c['ci95_bp'][1])}]",
                     f"{c['n']:,}", c["source"]])
    p("K1 経費前の値(RESULT.md §18.2、再計算しない、並べるだけ):")
    p(table(["足", "mean bp", "CI95", "n", "出所"], rows))

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"→ {OUT_MD} ({len(lines)} 行)")


if __name__ == "__main__":
    main()
