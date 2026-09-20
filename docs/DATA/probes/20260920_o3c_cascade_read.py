#!/usr/bin/env python3
"""清算の連鎖 30 本(続いた 15 / 止まった 15)を実物で読めるように抽出する。

委任文: `docs/DATA/delegations/20260920_o3c_cascade_read_prompt.md`。

**判定はしない。判定語(陽性/陰性/有意/差あり/検出されず/支持)を書かない。**
`paper_logs/` は開かない。既存の `scripts/o3c_signal_explore5.py` の
`load_day_trades` / `build_oi_context` と `scripts/o3c_oi_distance.py`
(`oid` = このファイル内の別名)の関数をそのまま使う(車輪の再発明をしない)。

出力: `docs/DATA/probes/20260920_o3c_cascade_read.md`

乱数の種は 20260920(委任文 §2)。**再実行すれば同じ 30 本が出る**
(`random.Random(20260920)` を 1 つだけ作り、期間 0→1→2、束は
続いた→止まった の順に消費する。既に選んだ日を後続の抽選から除く)。
"""
from __future__ import annotations

import datetime as _dt
import math
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import o3c_price_level_table as base  # noqa: E402
import o3c_oi_distance as oid  # noqa: E402
import o3c_signal_explore5 as ex5  # noqa: E402

SEED = 20260920
DATA_ROOT = REPO_ROOT / "backtest_data" / "binance_cm_o3c_20260913"
ROWS_PATH = (REPO_ROOT / "backtest_data" / "o3c_signal_explore5_20260920"
             / "rows_prints.csv.gz")
OUT_MD = Path(__file__).resolve().with_suffix(".md")

W_HOURS = 8.0                       # explore5 と同じ属性窓
WINDOW_MS = int(W_HOURS * 3600 * 1000)
BIN_STEP = base.log_step(0.1)       # explore5 の BIN_PCT=0.1 と同じ
BAND_BP = (5, 10, 20)
TICK = 0.1                          # BTCUSD_PERP の呼び値
GRID_BACK_MS = 60_000
GRID_FWD_MS = 120_000

REACT_SIGN = {"SELL": -1.0, "BUY": 1.0}
BANNED_WORDS = ("差あり", "検出されず", "陽性", "陰性", "有意", "支持")


def check_no_banned(text: str, where: str) -> None:
    hit = [w for w in BANNED_WORDS if w in text]
    if hit:
        raise SystemExit(f"[止め] 判定語が出力に混ざっている({where}): {hit}")


def r4(x) -> float | None:
    if x is None:
        return None
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(xf):
        return None
    r = round(xf, 4)
    return 0.0 if r == 0.0 else r  # -0.0000 を 0.0000 に正規化(表記だけの話)


def fmt(x) -> str:
    v = r4(x)
    return "" if v is None else (f"{v:.4f}" if isinstance(v, float) else str(v))


# ===========================================================================
# 1. プリントの読み込み(rows_prints.csv.gz の kind=="print" だけ)
# ===========================================================================
def load_prints_df() -> pd.DataFrame:
    df = pd.read_csv(ROWS_PATH, dtype={"bundle_id": str, "day": str})
    p = df[df["kind"] == "print"].copy()
    p = p.sort_values(["ts_ms", "print_id"]).reset_index(drop=True)
    return p


def build_prev_same_side(p: pd.DataFrame) -> dict:
    """print_id -> (直前の同じ側のプリントの ts_ms, p0)(全 456 日・全束を通した系列)。"""
    out: dict = {}
    for side in ("SELL", "BUY"):
        sub = p[p["side"] == side].sort_values("ts_ms")
        ts = sub["ts_ms"].to_numpy()
        p0 = sub["p0"].to_numpy()
        pid = sub["print_id"].to_numpy()
        for i in range(sub.shape[0]):
            if i == 0:
                out[pid[i]] = (None, None)
            else:
                out[pid[i]] = (int(ts[i - 1]), float(p0[i - 1]))
    return out


# ===========================================================================
# 2. 30 本の抽選(委任文 §2。機械的に)
# ===========================================================================
def select_bundles(p: pd.DataFrame) -> tuple[list[dict], list[str]]:
    notes: list[str] = []
    g = p.groupby("bundle_id").agg(
        n=("print_id", "size"), day=("day", "min"),
        side=("side", "first"), ts_min=("ts_ms", "min"),
        ts_max=("ts_ms", "max"))
    cont = g[g["n"] >= 3]
    single_ids = set(p.loc[p["bundle_pos_single"] == 1, "bundle_id"])
    stop = g.loc[g.index.isin(single_ids)]
    notes.append(f"束の総数(最後の行で数える) = {int((p['bundle_pos']=='最後').sum())}、"
                 f"続いた束(3件以上) = {len(cont)}、止まった束(単発) = {len(stop)}")

    days_sorted = sorted(p["day"].unique())
    n_days = len(days_sorted)
    notes.append(f"日数 = {n_days}(3 等分できるか: {n_days} / 3 = {n_days/3})")
    third = n_days // 3
    periods = [days_sorted[:third], days_sorted[third:2 * third],
               days_sorted[2 * third:]]
    notes.append("期間の日数 = " + ", ".join(str(len(x)) for x in periods))

    rng = random.Random(SEED)
    chosen: list[dict] = []
    used_days: set[str] = set()

    for pi, period_days in enumerate(periods):
        pset = set(period_days)
        cont_p = cont[cont["day"].isin(pset)]
        stop_p = stop[stop["day"].isin(pset)]
        cont_by_day: dict = {}
        for bid, row in cont_p.iterrows():
            cont_by_day.setdefault(row["day"], []).append(bid)
        stop_by_day: dict = {}
        for bid, row in stop_p.iterrows():
            stop_by_day.setdefault(row["day"], []).append(bid)

        for label, by_day, need in (("続いた", cont_by_day, 5),
                                     ("止まった", stop_by_day, 5)):
            days_avail = [d for d in period_days if d in by_day]
            rng.shuffle(days_avail)
            picked = 0
            for d in days_avail:
                if picked >= need:
                    break
                if d in used_days:
                    continue
                bid = rng.choice(sorted(by_day[d]))
                row = g.loc[bid]
                chosen.append({
                    "label": label, "period": pi, "bundle_id": bid,
                    "day": d, "side": row["side"], "n": int(row["n"]),
                    "ts_min": int(row["ts_min"]), "ts_max": int(row["ts_max"]),
                })
                used_days.add(d)
                picked += 1
            if picked < need:
                raise SystemExit(
                    f"[止め] 期間{pi} {label} が {picked}/{need} 本しか取れない")
    return chosen, notes


# ===========================================================================
# 3. 約定(トレード)の範囲読み込み
# ===========================================================================
def day_of_ms(ts_ms: int) -> str:
    return (_dt.datetime.fromtimestamp(int(ts_ms) / 1000, _dt.timezone.utc)
            .date().isoformat())


def load_range_trades(lo_ms: int, hi_ms: int, cache: dict):
    d_lo, d_hi = day_of_ms(lo_ms), day_of_ms(hi_ms)
    days = [d_lo]
    while days[-1] < d_hi:
        days.append((_dt.date.fromisoformat(days[-1])
                      + _dt.timedelta(days=1)).isoformat())
    parts = []
    for d in days:
        v = ex5.load_day_trades(DATA_ROOT, d, cache)
        if v is not None:
            parts.append(v)
    if not parts:
        return None
    times = np.concatenate([x[0] for x in parts])
    prices = np.concatenate([x[1] for x in parts])
    qtys = np.concatenate([x[2] for x in parts])
    maker = np.concatenate([x[3] for x in parts])
    order = np.argsort(times, kind="stable")
    times, prices, qtys, maker = (times[order], prices[order], qtys[order],
                                   maker[order])
    m = (times >= lo_ms) & (times <= hi_ms)
    return times[m], prices[m], qtys[m], maker[m]


def last_price_at_or_before(times: np.ndarray, prices: np.ndarray, t_ms: int):
    if times.size == 0:
        return None
    i = int(np.searchsorted(times, t_ms, side="right")) - 1
    if i < 0:
        return None
    return float(prices[i])


def imbalance_5s(times, prices, qtys, maker, ts_ms: int):
    """[ts-5000, ts) の成行の偏り = (買い成行 − 売り成行) / (両方の合計)。無ければ None。"""
    if times is None or times.size == 0:
        return None, 0, 0
    lo, hi = ts_ms - 5000, ts_ms
    i0 = int(np.searchsorted(times, lo, side="left"))
    i1 = int(np.searchsorted(times, hi, side="left"))
    if i1 <= i0:
        return None, 0, 0
    q = qtys[i0:i1]
    mk = maker[i0:i1]
    buy = float(q[~mk].sum())   # is_buyer_maker == False -> 買い成行
    sell = float(q[mk].sum())   # is_buyer_maker == True  -> 売り成行
    tot = buy + sell
    if tot <= 0:
        return None, buy, sell
    return (buy - sell) / tot, buy, sell


def range_high_low_bp(times, prices, ts_ms: int, p_ref: float, window_ms: int = 60_000):
    """[ts-window_ms, ts) の高値-安値(bp、p_ref 基準)。約定が無ければ None。"""
    if times is None or times.size == 0:
        return None, 0
    lo, hi = ts_ms - window_ms, ts_ms
    i0 = int(np.searchsorted(times, lo, side="left"))
    i1 = int(np.searchsorted(times, hi, side="left"))
    if i1 <= i0:
        return None, 0
    seg = prices[i0:i1]
    rng_bp = (float(seg.max()) - float(seg.min())) / p_ref * 1e4
    return rng_bp, int(i1 - i0)


# ===========================================================================
# 4. 材料 8: 建玉(ΔOI)の帯ごとの量
# ===========================================================================
def oi_band_amounts(buckets: dict, ts_ms: int, p0: float, side: str):
    """`side` の清算方向へ「この先」5/10/20bp 以内にある按分後 ΔOI の合計。

    `oi_columns_for_rows`(`o3c_oi_distance.py`)が内部で作るのと同じビン配列
    (窓 `WINDOW_MS`・対数ビン幅 `BIN_STEP`・按分 `delta*buy_share` / `delta*(1-buy_share)`)
    から、既存の距離統計(`oi_dist_node_bp` 等)ではなく**帯ごとの合計**を取り出す
    (既存の関数は距離しか返さないので、ここで直接ビン配列を作る)。
    """
    t_b = buckets.get("t_ms", np.zeros(0))
    if t_b.size == 0:
        return {"covered": False, "n_buckets": 0,
                **{f"amt_{x}bp": None for x in BAND_BP}}
    covered_arr = ex5.covered_before(buckets["t_all"], np.array([ts_ms]), WINDOW_MS)
    covered = bool(covered_arr[0])
    mask = (t_b > ts_ms - WINDOW_MS) & (t_b <= ts_ms)
    n_b = int(mask.sum())
    if n_b == 0:
        return {"covered": covered, "n_buckets": 0,
                **{f"amt_{x}bp": None for x in BAND_BP}}
    vwap = buckets["vwap"][mask]
    delta = buckets["delta"][mask]
    buy_share = buckets["buy_share"][mask]
    which = oid.SIDE_PROFILE.get(side)
    w = delta * buy_share if which == "long" else delta * (1.0 - buy_share)
    bins = base.bin_index_array(vwap, BIN_STEP)
    centers = base.bin_center_price(bins, BIN_STEP)
    sign = REACT_SIGN.get(side, float("nan"))
    out = {"covered": covered, "n_buckets": n_b}
    for x in BAND_BP:
        edge = p0 * (1.0 + sign * x / 1e4)
        if sign > 0:
            band = (centers >= p0) & (centers <= edge)
        else:
            band = (centers <= p0) & (centers >= edge)
        out[f"amt_{x}bp"] = float(w[band].sum()) if band.any() else 0.0
    return out


# ===========================================================================
# main
# ===========================================================================
def main() -> int:
    print(f"rows_prints 読み込み: {ROWS_PATH}", flush=True)
    p = load_prints_df()
    print(f"print 行数 = {len(p)}", flush=True)

    chosen, sel_notes = select_bundles(p)
    print(f"選んだ束 = {len(chosen)} 本", flush=True)
    for c in chosen:
        print(f"  {c['label']} 期{c['period']} {c['day']} {c['bundle_id']} "
              f"側={c['side']} n={c['n']}", flush=True)

    prev_side = build_prev_same_side(p)

    md: list[str] = []
    md.append("# 清算の連鎖 30 本の実物(O3C SIGNAL)")
    md.append("")
    md.append("委任文: `docs/DATA/delegations/20260920_o3c_cascade_read_prompt.md`。")
    md.append("スクリプト: `docs/DATA/probes/20260920_o3c_cascade_read.py`"
               "(乱数の種 20260920、再実行で同じ 30 本)。")
    md.append("")
    md.append("## 0. オーナーとの対応表(委任文 §0 の写し)")
    md.append("")
    md.append("| やること | オーナーの原文の該当語(逐語) |")
    md.append("|---|---|")
    md.append("| 連鎖 30 本(続いた 15 / 止まった 15)を実物で読めるように抽出する "
               "| 「**その空の行もそれでいいです**」(L-263。空の行 = 「連鎖 30 本を実物で読む」) |")
    md.append("| 平均で潰さず、1 本ずつ・1 件ずつの列で出す "
               "| 「**平均で計算したらわからなくなって当然やろ**」(L-260) |")
    md.append("| 材料 8〜11 のデータの有無を確かめる "
               "| 「**その7つで足りているか検討しましたか**」(L-262)。材料の具体はリードの選択 |")
    md.append("")
    md.append("**判定はしていない。委任元が指定した判定語 6 語(委任文冒頭 §0 参照)は"
               "本文のどこにも書いていない(このスクリプトの `check_no_banned` が"
               "書き出し直前に検査する)。`paper_logs/` は開いていない。**")
    md.append("")

    md.append("## 1. 抽選の記録")
    md.append("")
    for n in sel_notes:
        md.append(f"- {n}")
    md.append("- 抽選の手順: 日を 3 等分(日付順)し、各期間で「続いた束の日の一覧」と"
               "「止まった束の日の一覧」をそれぞれ `random.Random(20260920)` で"
               "シャッフルし、まだ使っていない日から先頭より 5 日ずつ選ぶ"
               "(1 日に複数の束があれば `rng.choice` で 1 本を選ぶ)。"
               "使った日は以後の抽選(続いた→止まった、期0→1→2の順)から外す。")
    md.append("")

    md.append("## 2. 選んだ 30 本の一覧")
    md.append("")
    md.append("| # | 分類 | 期 | 日 | 束 id | 側 | 件数 | 最初の ts(UTC) | 最後の ts(UTC) |")
    md.append("|---|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(chosen, 1):
        t0 = _dt.datetime.fromtimestamp(c["ts_min"] / 1000, _dt.timezone.utc)
        t1 = _dt.datetime.fromtimestamp(c["ts_max"] / 1000, _dt.timezone.utc)
        md.append(f"| {i} | {c['label']} | {c['period']} | {c['day']} | "
                  f"`{c['bundle_id']}` | {c['side']} | {c['n']} | "
                  f"{t0.isoformat()} | {t1.isoformat()} |")
    md.append("")

    # -----------------------------------------------------------------
    # 材料 8〜11 用のキャッシュ
    # -----------------------------------------------------------------
    trade_cache: dict = {}
    metrics_cache: dict = {}
    bucket_cache: dict = {}
    range_trade_cache: dict = {}

    mat8_rows = []
    mat11_rows = []

    md.append("## 3. 1 本ごとの実物")
    md.append("")

    for i, c in enumerate(chosen, 1):
        bid = c["bundle_id"]
        rows = p[p["bundle_id"] == bid].sort_values("ts_ms").reset_index(drop=True)
        side = rows.loc[0, "side"]
        sign = REACT_SIGN[side]
        p0_first = float(rows.loc[0, "p0"])
        bundle_start_ts = int(rows["ts_ms"].min())
        last_row = rows.iloc[-1]
        last_t0 = int(last_row["t0_ms"])

        md.append(f"### {i}. {c['label']} 束 `{bid}`(期 {c['period']}、"
                  f"{c['day']}、側 {side}、{c['n']} 件)")
        md.append("")

        # --- 約定(このバンドル用のレンジ) ---
        lo_ms = bundle_start_ts - GRID_BACK_MS - 5_000  # 直前5秒の偏り分の余白
        hi_ms = last_t0 + GRID_FWD_MS
        rt = load_range_trades(lo_ms, hi_ms, range_trade_cache)
        if rt is None:
            times = prices = qtys = maker = np.zeros(0)
        else:
            times, prices, qtys, maker = rt

        # --- A. プリントの列 ---
        md.append("**A. プリントの列**(側の符号を掛けて清算の向きを正にした値。"
                  "「直前の同じ側のプリント」は束の中に限らず全 456 日を通した系列)")
        md.append("")
        md.append("| # | 束開始からの秒 | 側 | 想定元本USD | p0 | k(bp) | "
                  "ティック数 | 直前同側からの秒 | 次の同側までの秒 | "
                  "直前5秒成行の偏り | 直前プリントp0からのbp | d | dist_node_bp |")
        md.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for j in range(rows.shape[0]):
            r = rows.loc[j]
            t_since = (int(r["ts_ms"]) - bundle_start_ts) / 1000.0
            p0 = float(r["p0"])
            p_pre = r["p_pre"]
            ticks = (abs(p0 - float(p_pre)) / TICK) if pd.notna(p_pre) else None
            gap_next = r["next_same_side_gap_s"]
            gap_next_s = "無し" if pd.isna(gap_next) else fmt(gap_next)
            prev_ts, prev_p0 = prev_side.get(r["print_id"], (None, None))
            if prev_ts is None:
                gap_prev_s = "無し"
                bp_prev = "無し"
            else:
                gap_prev_s = fmt((int(r["ts_ms"]) - prev_ts) / 1000.0)
                bp_prev = fmt(sign * (p0 - prev_p0) / prev_p0 * 1e4)
            imb, buy_q, sell_q = imbalance_5s(times, prices, qtys, maker,
                                              int(r["ts_ms"]))
            imb_s = "無し" if imb is None else fmt(imb)
            md.append(f"| {j+1} | {fmt(t_since)} | {side} | {fmt(r['notional'])} | "
                      f"{fmt(p0)} | {fmt(r['k'])} | {fmt(ticks)} | {gap_prev_s} | "
                      f"{gap_next_s} | {imb_s} | {bp_prev} | {fmt(r['d'])} | "
                      f"{fmt(r['dist_node_bp'])} |")
        md.append("")

        # --- B. 値段の列(1秒刻み) ---
        grid_lo = bundle_start_ts - GRID_BACK_MS
        grid_hi = last_t0 + GRID_FWD_MS
        star_secs = set()
        for j in range(rows.shape[0]):
            ts_j = int(rows.loc[j, "ts_ms"])
            g = grid_lo + ((ts_j - grid_lo) // 1000) * 1000
            star_secs.add(g)
        n_pts = (grid_hi - grid_lo) // 1000 + 1
        vals = []
        for k in range(int(n_pts)):
            g = grid_lo + k * 1000
            px = last_price_at_or_before(times, prices, g)
            if px is None:
                bp = None
            else:
                bp = sign * (px - p0_first) / p0_first * 1e4
            star = "*" if g in star_secs else ""
            vals.append(((g - bundle_start_ts) // 1000, bp, star))
        md.append("**B. 値段の列**(1 秒刻み、最初のプリント p0 = 0bp、清算の向きが正。"
                  "束開始からの経過秒を先頭に置く。`*` = その秒にプリントがあった)")
        md.append("")
        for k0 in range(0, len(vals), 10):
            chunk = vals[k0:k0 + 10]
            cells = []
            for sec, bp, star in chunk:
                bp_s = "無し" if bp is None else fmt(bp)
                cells.append(f"{sec}s:{bp_s}{star}")
            md.append("  " + " / ".join(cells))
        md.append("")

        # --- C. 束のまとめ ---
        r_last_60 = last_row.get("r_t0_60")
        r_last_300 = last_row.get("r_t0_300")
        md.append("**C. 束のまとめ**")
        md.append("")
        md.append(f"- m_60(最初のプリント) = {fmt(rows.loc[0,'m_60'])}")
        md.append(f"- d: 最初 = {fmt(rows.loc[0,'d'])} / 最後 = {fmt(last_row['d'])}")
        md.append(f"- dist_node_bp: 最初 = {fmt(rows.loc[0,'dist_node_bp'])} / "
                  f"最後 = {fmt(last_row['dist_node_bp'])}")
        md.append(f"- 最後のプリントの後 60 秒 = {fmt(r_last_60)}bp / "
                  f"300 秒 = {fmt(r_last_300)}bp(t0 基準、r_t0_60 / r_t0_300)")
        md.append("")

        # --- 材料 8: 建玉の帯ごとの量(最初のプリント) ---
        day0 = str(rows.loc[0, "day"])
        buckets, cov, missing = ex5.build_oi_context(
            DATA_ROOT, DATA_ROOT, day0, trade_cache, metrics_cache, bucket_cache)
        oi_out = oi_band_amounts(buckets, int(rows.loc[0, "ts_ms"]), p0_first, side)
        mat8_rows.append({"i": i, "label": c["label"], "bundle_id": bid,
                          "side": side, **oi_out})

        # --- 材料 11: 清算の大きさ ÷ 直前60秒の値幅(最初のプリント) ---
        rng_bp, n_trades_60 = range_high_low_bp(
            times, prices, int(rows.loc[0, "ts_ms"]), p0_first, 60_000)
        mat11_rows.append({"i": i, "label": c["label"], "bundle_id": bid,
                           "notional": float(rows.loc[0, "notional"]),
                           "range_bp": rng_bp, "n_trades_60": n_trades_60})

    # -----------------------------------------------------------------
    # 4. 材料 8〜11
    # -----------------------------------------------------------------
    md.append("## 4. 材料 8〜11 の可否")
    md.append("")

    md.append("### 8. この先 X bp 以内(5/10/20)にある建玉の量")
    md.append("")
    md.append("`scripts/o3c_oi_distance.py`(`oid`)は `oi_columns_for_rows` の内部で "
              "5 分桶の ΔOI(建玉の増分)を対数ビン(`o3c_price_level_table.log_step(0.1)`)"
              "に積んだ配列を作るが、**そこから外へ出す列は距離(`oi_dist_node_bp` 等)だけ**"
              "で、帯ごとの合計は関数の外に出てこない。このスクリプトの "
              "`oi_band_amounts` はその同じビン配列を窓 "
              f"`{WINDOW_MS/3600000:.0f}h`・按分(側 = `SIDE_PROFILE`: SELL→long, "
              "BUY→short、重み = `delta*buy_share` / `delta*(1-buy_share)`)で組み直し、"
              "清算の向きへ 5/10/20bp 以内にある重み(≒建玉の増分、単位は `sum_open_interest` "
              "と同じ枚)を合計した。**距離だけでなく、帯ごとの量も出せる。**"
              "30 本の最初のプリントについて値を出した(下表)。")
    md.append("")
    md.append("| # | 分類 | 束 id | 側 | 窓が被覆内か | 窓内の桶数 | "
              "5bp以内(枚) | 10bp以内(枚) | 20bp以内(枚) |")
    md.append("|---|---|---|---|---|---|---|---|---|")
    for r in mat8_rows:
        md.append(f"| {r['i']} | {r['label']} | `{r['bundle_id']}` | {r['side']} | "
                  f"{r['covered']} | {r['n_buckets']} | "
                  f"{fmt(r.get('amt_5bp'))} | {fmt(r.get('amt_10bp'))} | "
                  f"{fmt(r.get('amt_20bp'))} |")
    n_covered = sum(1 for r in mat8_rows if r["covered"])
    md.append("")
    md.append(f"- 窓が建玉の被覆内だった本数 = {n_covered} / {len(mat8_rows)}"
              "(`ex5.covered_before` の判定をそのまま使った)。")
    md.append("")

    md.append("### 9. 直前 5 秒の成行の偏り")
    md.append("")
    md.append("上の A 表に列として出した(可)。`is_buyer_maker == False` を買い成行、"
              "`True` を売り成行として `(買い − 売り) / (買い + 売り)` を計算した。"
              "両方の合計が 0(その 5 秒に約定が無い)なら「無し」。")
    md.append("")

    md.append("### 10. 資金調達率(funding rate)のアーカイブの有無")
    md.append("")
    funding_dir = DATA_ROOT / "fundingRate" / "BTCUSD_PERP"
    funding_zips = sorted(funding_dir.glob("BTCUSD_PERP-fundingRate-*.zip"))
    md.append(f"- `{funding_dir}` に月次 zip が {len(funding_zips)} 本ある"
              f"(最初 = `{funding_zips[0].name}`、最後 = `{funding_zips[-1].name}`)。")
    md.append("- 中身の列(`calc_time,funding_interval_hours,last_funding_rate`)を"
              "1 本 `unzip` して確認した(下の「実行したコマンドと出力」に記録)。")
    metrics_dir = DATA_ROOT / "metrics" / "BTCUSD_PERP"
    md.append(f"- `metrics`(5 分値、`{metrics_dir}`)の列名: "
              "`create_time, symbol, sum_open_interest, sum_open_interest_value, "
              "count_toptrader_long_short_ratio, sum_toptrader_long_short_ratio, "
              "count_long_short_ratio, sum_taker_long_short_vol_ratio`"
              "(建玉 = `sum_open_interest`(枚)/`sum_open_interest_value`(USD)。"
              "ロングショート比の列は 4 つあるが、抽出時にサンプルした 5 日"
              "(2023-06-25 / 2023-07-15 / 2023-10-01 / 2024-01-15 / 2024-10-12)"
              "では `count_toptrader_long_short_ratio` / `sum_toptrader_long_short_ratio`"
              " / `count_long_short_ratio`(上位トレーダーと全アカウントの建玉ベースの比)"
              "は全行空文字、`sum_taker_long_short_vol_ratio`"
              "(taker の出来高ベースの比。建玉ではない)だけ値が入っていた"
              " — 下の「実行したコマンドと出力」参照。**この 5 日以外は未確認。**)。")
    md.append("")

    md.append("### 11. 清算の大きさ ÷ 直前 60 秒の値幅")
    md.append("")
    md.append("30 本の最初のプリントについて、約定から 60 秒の高値 − 安値(bp、"
              "最初のプリントの p0 基準)を想定元本と並べた。")
    md.append("")
    md.append("| # | 分類 | 束 id | 想定元本USD | 直前60秒の高安(bp) | 窓内の約定件数 |")
    md.append("|---|---|---|---|---|---|")
    for r in mat11_rows:
        rb = "無し" if r["range_bp"] is None else fmt(r["range_bp"])
        md.append(f"| {r['i']} | {r['label']} | `{r['bundle_id']}` | "
                  f"{fmt(r['notional'])} | {rb} | {r['n_trades_60']} |")
    md.append("")

    mdtxt = "\n".join(md)
    check_no_banned(mdtxt, "本文")
    OUT_MD.write_text(mdtxt, encoding="utf-8")
    print(f"書いた: {OUT_MD}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
