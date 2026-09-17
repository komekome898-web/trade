#!/usr/bin/env python3
"""O-3c「どのくらい約定から価格が離れると清算が起きるか」の観測表(2026-09-17)。

オーナー逐語(L-194):
  「**約定(建玉)が積み上がった位置から離れた位置で清算が起きるのは当たり前だから結果は納得です。
    レバレッジの大きさによってその距離が近づくと思います。約定のレバレッジは測りにくいので、
    どのくらい約定から価格が離れると清算が起きるのか測れませんか？**」
オーナー決定(L-195): 「**3つとも進めてください**」

既存の観測表(`scripts/o3c_price_level_table.py`、設計 `docs/PHASE2/O3C/PRICE_LEVEL/
DESIGN_2026-09-17.md`、全件 `FULL_2026-09-17.md`)の `process_day` / `profile_stats` を
**そのまま**使って「約定の積み上がり」からの距離を出し、同じ行に

  * **建玉の積み上がり**: 5 分ごとの ΔOI = OI(t) − OI(t−5 分) が正の 5 分だけを、
    その 5 分の aggTrades の VWAP の価格ビンに ΔOI の重みで積んだプロファイル。
    そこから (a) 加重平均価格(平均建値)と (b) 建玉ノード(重みの上位 10% のビン群のうち
    清算価格に一番近いもの)までの距離。
  * **taker の向きによる按分**: 同じ 5 分の aggTrades を `is_buyer_maker == false`(買い taker)
    / `true`(売り taker)の出来高で分け、その比で ΔOI を「ロングの積み上がり」
    「ショートの積み上がり」に割る(**仮定**)。SELL 清算(ロングの清算)にはロング側、
    BUY 清算(ショートの清算)にはショート側のプロファイルからの距離を出す。

を並べる。

**観測表のみ。判定(予測できる/できない、当たる/当たらない、使える/使えない、有効/無効)は
一切書かない。**

使い方:
  python3 scripts/o3c_oi_distance.py --days 2023-06-25,... \
      --data-root <aggTrades と liquidationSnapshot の根> \
      --metrics-root <metrics の根> --window-hours 8 \
      --out-dir backtest_data/o3c_oi_distance_20260917/w8
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import o3c_price_level_table as base  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METRICS_ROOT = REPO_ROOT / "backtest_data" / "binance_cm_o3c_20260913"

BUCKET_MS = 5 * 60 * 1000  # metrics の粒度(5 分)
BUCKETS_PER_DAY = base.MS_PER_DAY // BUCKET_MS  # 288

METRICS_NAMES = [
    "create_time",
    "symbol",
    "sum_open_interest",
    "sum_open_interest_value",
    "count_toptrader_long_short_ratio",
    "sum_toptrader_long_short_ratio",
    "count_long_short_ratio",
    "sum_taker_long_short_vol_ratio",
]

# 建玉側の列(距離はすべて既存と同じ符号の約束: (位置 − p_liq) / p_liq * 1e4)。
OI_COLUMNS = [
    "oi_dist_vwap_bp",       # 建玉の平均建値 − 清算価格
    "oi_dist_node_bp",       # 建玉ノード − 清算価格
    "oi_side_dist_vwap_bp",  # 側別(按分後)の平均建値 − 清算価格
    "oi_side_dist_node_bp",  # 側別(按分後)のノード − 清算価格
    "oi_n_bins",
    "oi_n_buckets",
    "oi_total_delta",
    "oi_side_total_delta",
]

# 「清算の向きに正」に符号を揃えた列。SELL は +1 倍、BUY は −1 倍、対照は NaN。
LIQDIR_SOURCE = [
    ("dist_vwap_bp", "dist_vwap_bp_liqdir"),
    ("dist_node_bp", "dist_node_bp_liqdir"),
    ("oi_dist_vwap_bp", "oi_dist_vwap_bp_liqdir"),
    ("oi_dist_node_bp", "oi_dist_node_bp_liqdir"),
    ("oi_side_dist_vwap_bp", "oi_side_dist_vwap_bp_liqdir"),
    ("oi_side_dist_node_bp", "oi_side_dist_node_bp_liqdir"),
]

LEVERAGE_COLUMNS = ["implied_leverage", "implied_leverage_side"]

COLUMNS = (
    base.COLUMNS
    + OI_COLUMNS
    + [dst for _, dst in LIQDIR_SOURCE]
    + LEVERAGE_COLUMNS
    + ["oi_covered"]
)

# 分位を取る列。
QUANTILE_COLUMNS = [
    "dist_vwap_bp",
    "dist_node_bp",
    "oi_dist_vwap_bp",
    "oi_dist_node_bp",
    "oi_side_dist_vwap_bp",
    "oi_side_dist_node_bp",
    "dist_vwap_bp_liqdir",
    "dist_node_bp_liqdir",
    "oi_dist_vwap_bp_liqdir",
    "oi_dist_node_bp_liqdir",
    "oi_side_dist_vwap_bp_liqdir",
    "oi_side_dist_node_bp_liqdir",
    "implied_leverage",
    "implied_leverage_side",
]

QUANTILES = [10, 25, 50, 75, 90]

# 清算の向き。SELL = ロングの強制決済、BUY = ショートの強制決済(Binance の force order の定義)。
LIQ_SIGN = {"SELL": 1.0, "BUY": -1.0}
# 清算の側 -> 使う按分後のプロファイル。
SIDE_PROFILE = {"SELL": "long", "BUY": "short"}

OWNER_VERBATIM = "3つとも進めてください"
LEAD_ROWS_TEXT = [
    "(1)「積み上がった位置」= 建玉の増分 ΔOI をその 5 分の VWAP に置いたプロファイル"
    "(平均建値 + 建玉のノード)",
    "(2) 約定の積み上がり(VWAP / ノード)も並べて出す",
    "(3) ロング / ショートの建玉を taker の向きで按分する",
]


# --------------------------------------------------------------------------
# 読み込み
# --------------------------------------------------------------------------


def metrics_path(root: Path, day: str) -> Path:
    return root / "metrics" / base.SYMBOL / f"{base.SYMBOL}-metrics-{day}.zip"


def load_agg_trades_with_maker(
    path: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(transact_time[ms], price, quantity, is_buyer_maker) を時刻の昇順で返す。

    `base.load_agg_trades` と同じ読み方に `is_buyer_maker` を足しただけ。
    `is_buyer_maker == True` = 買い手が maker = **売り taker**。
    """
    df = base._zip_csv(
        path,
        ["price", "quantity", "transact_time", "is_buyer_maker"],
        base.AGG_NAMES,
    )
    t = df["transact_time"].to_numpy(dtype=np.int64)
    p = df["price"].to_numpy(dtype=np.float64)
    q = df["quantity"].to_numpy(dtype=np.float64)
    m_raw = df["is_buyer_maker"]
    if m_raw.dtype == object:
        m = m_raw.astype(str).str.strip().str.lower().isin(["true", "1"]).to_numpy()
    else:
        m = m_raw.to_numpy(dtype=bool)
    order = np.argsort(t, kind="stable")
    return t[order], p[order], q[order], m[order]


def bucket_trade_stats(
    day: str,
    times: np.ndarray,
    prices: np.ndarray,
    qtys: np.ndarray,
    is_buyer_maker: np.ndarray,
) -> dict:
    """1 日の aggTrades を 5 分の桶にまとめる。桶 k = [day 00:00 + 5k 分, +5 分)。

    戻り値の配列はどれも長さ 288(`BUCKETS_PER_DAY`)。
      `start_ms` 桶の開始時刻 / `vwap` 桶内の出来高加重平均価格(約定なしは NaN) /
      `buy_share` 買い taker の出来高の割合(約定なしは NaN) / `vol` 桶内の出来高 /
      `n` 桶内の約定件数。
    """
    day_start, day_end = base.day_bounds_ms(day)
    n_b = int(BUCKETS_PER_DAY)
    inside = (times >= day_start) & (times < day_end)
    k = ((times[inside] - day_start) // BUCKET_MS).astype(np.int64)
    q = qtys[inside]
    p = prices[inside]
    m = is_buyer_maker[inside]
    vol = np.bincount(k, weights=q, minlength=n_b)[:n_b]
    pq = np.bincount(k, weights=p * q, minlength=n_b)[:n_b]
    cnt = np.bincount(k, minlength=n_b)[:n_b]
    buy = ~m  # 買い手が taker = 買い taker
    vol_buy = np.bincount(k[buy], weights=q[buy], minlength=n_b)[:n_b]
    with np.errstate(invalid="ignore", divide="ignore"):
        vwap = np.where(vol > 0, pq / np.where(vol > 0, vol, 1.0), np.nan)
        buy_share = np.where(vol > 0, vol_buy / np.where(vol > 0, vol, 1.0), np.nan)
    return {
        "start_ms": day_start + BUCKET_MS * np.arange(n_b, dtype=np.int64),
        "vwap": vwap,
        "buy_share": buy_share,
        "vol": vol,
        "n": cnt,
    }


def load_metrics(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """metrics zip -> (create_time[ms, UTC], sum_open_interest[枚])。時刻の昇順。"""
    with zipfile.ZipFile(path) as z:
        name = z.namelist()[0]
        with z.open(name) as fh:
            head = fh.readline()
        has_header = b"create_time" in head
        with z.open(name) as fh:
            if has_header:
                df = pd.read_csv(fh, usecols=["create_time", "sum_open_interest"])
            else:
                df = pd.read_csv(
                    fh,
                    header=None,
                    names=METRICS_NAMES,
                    usecols=["create_time", "sum_open_interest"],
                )
    # pandas の版によって to_datetime の分解能が ns / us で変わるので、
    # **ms へ明示的に落としてから**整数にする(版に依らず ms になる)。
    t = (
        pd.to_datetime(df["create_time"], utc=True)
        .astype("datetime64[ms, UTC]")
        .astype("int64")
        .to_numpy(dtype=np.int64)
    )
    oi = pd.to_numeric(df["sum_open_interest"], errors="coerce").to_numpy(
        dtype=np.float64
    )
    order = np.argsort(t, kind="stable")
    return t[order], oi[order]


# --------------------------------------------------------------------------
# ΔOI の桶づくり
# --------------------------------------------------------------------------


def build_delta_buckets(
    metrics_days: list[tuple[np.ndarray, np.ndarray]],
    bucket_lookup: dict,
) -> dict:
    """読み込んだ metrics から ΔOI の桶を作る。

    metrics_days: (時刻[ms], OI) の一覧(読めた日だけ。並び順は問わない)。
    bucket_lookup: 桶の開始時刻[ms] -> (vwap, buy_share, vol, n)。

    ΔOI(T) = OI(T) − OI(T − 5 分)。**直前の行がちょうど 5 分前にある行だけ**を使う
    (metrics の行が飛んでいる所では ΔOI を作らない)。
    ΔOI を置く価格は **[T − 5 分, T) の約定の VWAP**(= 桶の開始時刻 T − 5 分の桶)。

    戻り値:
      `t_ms` / `delta` / `vwap` / `buy_share`  … **ΔOI > 0 かつ VWAP が取れた桶だけ**(昇順)
      `t_all`  … ΔOI が作れた行の時刻すべて(符号によらない。被覆の判定に使う)
      `n_delta_rows` / `n_positive` / `n_positive_no_trades` / `n_nonpositive`
    """
    empty = {
        "t_ms": np.zeros(0, dtype=np.int64),
        "delta": np.zeros(0),
        "vwap": np.zeros(0),
        "buy_share": np.zeros(0),
        "t_all": np.zeros(0, dtype=np.int64),
        "n_delta_rows": 0,
        "n_positive": 0,
        "n_positive_no_trades": 0,
        "n_nonpositive": 0,
    }
    if not metrics_days:
        return empty
    t = np.concatenate([d[0] for d in metrics_days])
    oi = np.concatenate([d[1] for d in metrics_days])
    order = np.argsort(t, kind="stable")
    t, oi = t[order], oi[order]
    if t.size < 2:
        return empty
    dt = t[1:] - t[:-1]
    ok = (dt == BUCKET_MS) & np.isfinite(oi[1:]) & np.isfinite(oi[:-1])
    t_end = t[1:][ok]
    delta = (oi[1:] - oi[:-1])[ok]

    pos = delta > 0
    t_pos = t_end[pos]
    d_pos = delta[pos]
    vwap = np.empty(t_pos.size, dtype=np.float64)
    share = np.empty(t_pos.size, dtype=np.float64)
    for i, te in enumerate(t_pos):
        b = bucket_lookup.get(int(te) - BUCKET_MS)
        if b is None or not np.isfinite(b[0]) or b[0] <= 0:
            vwap[i] = np.nan
            share[i] = np.nan
        else:
            vwap[i] = b[0]
            share[i] = b[1]
    keep = np.isfinite(vwap) & np.isfinite(share)
    return {
        "t_ms": t_pos[keep],
        "delta": d_pos[keep],
        "vwap": vwap[keep],
        "buy_share": share[keep],
        "t_all": t_end,
        "n_delta_rows": int(t_end.size),
        "n_positive": int(pos.sum()),
        "n_positive_no_trades": int((~keep).sum()),
        "n_nonpositive": int((~pos).sum()),
    }


def coverage_start_ms(t_all: np.ndarray) -> int | None:
    """末尾から 5 分刻みで連続している区間の先頭時刻。行が無ければ None。

    ΔOI(T) は [T − 5 分, T] の建玉の増減を表すので、この関数が返す T0 に対して
    **T0 − 5 分より後**の窓は建玉で埋まっている。
    """
    if t_all.size == 0:
        return None
    i = t_all.size - 1
    while i > 0 and t_all[i] - t_all[i - 1] == BUCKET_MS:
        i -= 1
    return int(t_all[i])


# --------------------------------------------------------------------------
# 1 日の処理
# --------------------------------------------------------------------------


def _side_stats(
    qty: np.ndarray, lo_bin: int, step: float, p_liq: float, p0: float
) -> dict | None:
    """重みの合計が 0 以下なら None(ノード・平均建値を作らない)。"""
    total = float(np.asarray(qty, dtype=np.float64).sum())
    if not np.isfinite(total) or total <= 0:
        return None
    return base.profile_stats(qty, lo_bin, step, p_liq, p0)


def oi_columns_for_rows(
    rows: list[dict],
    buckets: dict,
    window_ms: int,
    step: float,
    cov_start: int | None,
) -> tuple[list[dict], int]:
    """時刻の昇順に並んだ行に、建玉側の列を付ける。戻り値は (列の一覧, 被覆外の行数)。"""
    n_rows = len(rows)
    out: list[dict] = [dict.fromkeys(OI_COLUMNS, np.nan) for _ in range(n_rows)]
    for o in out:
        o["oi_covered"] = 0
    if n_rows == 0:
        return out, 0
    t_b = buckets["t_ms"]
    if t_b.size == 0 or cov_start is None:
        return out, n_rows

    bins = base.bin_index_array(buckets["vwap"], step)
    gmin = int(bins.min())
    rel = (bins - gmin).astype(np.int64)
    width = int(rel.max()) + 1
    acc_tot = np.zeros(width, dtype=np.float64)
    acc_long = np.zeros(width, dtype=np.float64)
    acc_short = np.zeros(width, dtype=np.float64)
    acc_cnt = np.zeros(width, dtype=np.int64)

    w_long = buckets["delta"] * buckets["buy_share"]
    w_short = buckets["delta"] * (1.0 - buckets["buy_share"])

    lo = hi = 0
    n_uncovered = 0
    for i, r in enumerate(rows):
        t = int(r["time_ms"])
        while hi < t_b.size and t_b[hi] <= t:
            j = rel[hi]
            acc_tot[j] += buckets["delta"][hi]
            acc_long[j] += w_long[hi]
            acc_short[j] += w_short[hi]
            acc_cnt[j] += 1
            hi += 1
        left = t - window_ms
        while lo < hi and t_b[lo] <= left:
            j = rel[lo]
            acc_tot[j] -= buckets["delta"][lo]
            acc_long[j] -= w_long[lo]
            acc_short[j] -= w_short[lo]
            acc_cnt[j] -= 1
            lo += 1
        # 窓の先頭が建玉の被覆に入っているか(入っていなければ建玉側は NaN のまま)。
        if left < cov_start - BUCKET_MS:
            n_uncovered += 1
            continue
        if lo >= hi:
            continue
        nz = np.nonzero(acc_cnt)[0]
        if nz.size == 0:
            continue
        r0, r1 = int(nz[0]), int(nz[-1])
        sub_tot = acc_tot[r0 : r1 + 1].copy()
        sub_long = acc_long[r0 : r1 + 1].copy()
        sub_short = acc_short[r0 : r1 + 1].copy()
        sub_cnt = acc_cnt[r0 : r1 + 1]
        # 足し引きの端数が残らないようにする(既存 `process_day` と同じ処理)。
        sub_tot[sub_cnt == 0] = 0.0
        sub_long[sub_cnt == 0] = 0.0
        sub_short[sub_cnt == 0] = 0.0
        lo_bin = gmin + r0
        p_liq = float(r["p_liq"])
        p0 = float(r["p0"])
        st = _side_stats(sub_tot, lo_bin, step, p_liq, p0)
        o = out[i]
        o["oi_covered"] = 1
        o["oi_n_buckets"] = int(hi - lo)
        if st is not None:
            o["oi_dist_vwap_bp"] = round(st["dist_vwap_bp"], 4)
            o["oi_dist_node_bp"] = round(st["dist_node_bp"], 4)
            o["oi_n_bins"] = st["n_bins"]
            o["oi_total_delta"] = st["total_qty"]
        which = SIDE_PROFILE.get(str(r.get("side") or ""))
        if which is not None:
            sub_side = sub_long if which == "long" else sub_short
            st_s = _side_stats(sub_side, lo_bin, step, p_liq, p0)
            if st_s is not None:
                o["oi_side_dist_vwap_bp"] = round(st_s["dist_vwap_bp"], 4)
                o["oi_side_dist_node_bp"] = round(st_s["dist_node_bp"], 4)
                o["oi_side_total_delta"] = st_s["total_qty"]
    return out, n_uncovered


def _apply_liqdir_and_leverage(row: dict, mmr: float | None) -> None:
    """清算の向きに正へ揃えた列と、レバレッジ換算の列を入れる(その場で書き換える)。"""
    s = LIQ_SIGN.get(str(row.get("side") or ""))
    for src, dst in LIQDIR_SOURCE:
        v = row.get(src)
        if s is None or v is None or (isinstance(v, str) and v == ""):
            row[dst] = np.nan
        else:
            fv = float(v)
            row[dst] = np.nan if not np.isfinite(fv) else round(fv * s, 4)
    row["implied_leverage"] = np.nan
    row["implied_leverage_side"] = np.nan
    if mmr is None:
        return
    for src, dst in (
        ("oi_dist_vwap_bp_liqdir", "implied_leverage"),
        ("oi_side_dist_vwap_bp_liqdir", "implied_leverage_side"),
    ):
        d = row.get(src)
        if d is None or not np.isfinite(float(d)):
            continue
        denom = float(d) / 1e4 + mmr
        if denom <= 0:
            continue
        row[dst] = round(1.0 / denom, 4)


def process_day(
    day: str,
    root: Path,
    metrics_root: Path,
    window_hours: float,
    bin_pct: float,
    seed: int,
    agg_cache: dict,
    bucket_cache: dict,
    metrics_cache: dict,
    mmr: float | None,
    dedup_liq: bool = True,
) -> tuple[list[dict], dict]:
    """1 日分の行(清算 + 対照)を作る。約定側は既存 `process_day` をそのまま呼ぶ。"""
    step = base.log_step(bin_pct)
    window_ms = int(round(window_hours * 3600 * 1000))
    need = base.days_needed(day, window_hours)

    def ensure(d: str) -> None:
        if d in agg_cache:
            return
        p = base.agg_path(root, d)
        if not p.exists():
            return
        t, pr, q, m = load_agg_trades_with_maker(p)
        agg_cache[d] = (t, pr, q)
        bucket_cache[d] = bucket_trade_stats(d, t, pr, q, m)

    for d in need:
        ensure(d)

    # 約定側(既存のコードをそのまま。キャッシュを渡しているので zip は読み直さない)。
    rows, note = base.process_day(
        day, root, window_hours, bin_pct, seed, agg_cache, dedup_liq=dedup_liq
    )

    # 建玉側。
    bucket_lookup: dict[int, tuple[float, float, float, int]] = {}
    for d in need:
        bs = bucket_cache.get(d)
        if bs is None:
            continue
        for k in range(int(BUCKETS_PER_DAY)):
            bucket_lookup[int(bs["start_ms"][k])] = (
                float(bs["vwap"][k]),
                float(bs["buy_share"][k]),
                float(bs["vol"][k]),
                int(bs["n"][k]),
            )

    metrics_days: list[tuple[np.ndarray, np.ndarray]] = []
    metrics_missing: list[str] = []
    for d in need:
        if d not in metrics_cache:
            p = metrics_path(metrics_root, d)
            metrics_cache[d] = load_metrics(p) if p.exists() else None
        md = metrics_cache[d]
        if md is None:
            metrics_missing.append(d)
        else:
            metrics_days.append(md)

    buckets = build_delta_buckets(metrics_days, bucket_lookup)
    cov = coverage_start_ms(buckets["t_all"])
    oi_cols, n_uncovered = oi_columns_for_rows(rows, buckets, window_ms, step, cov)

    for r, o in zip(rows, oi_cols):
        r.update(o)
        _apply_liqdir_and_leverage(r, mmr)

    note.update(
        {
            "metrics_days_required": need,
            "metrics_days_missing": metrics_missing,
            "oi_delta_rows": buckets["n_delta_rows"],
            "oi_delta_positive": buckets["n_positive"],
            "oi_delta_nonpositive": buckets["n_nonpositive"],
            "oi_delta_positive_no_trades": buckets["n_positive_no_trades"],
            "oi_coverage_start_ms": cov,
            "rows_oi_uncovered": int(n_uncovered),
            "rows_oi_filled": int(sum(1 for r in rows if r.get("oi_covered") == 1)),
        }
    )
    return rows, note


# --------------------------------------------------------------------------
# 集計
# --------------------------------------------------------------------------


def _q(s: pd.Series) -> dict | None:
    v = pd.to_numeric(s, errors="coerce").dropna()
    if v.empty:
        return None
    a = v.to_numpy()
    out = {f"q{q}": round(float(np.percentile(a, q)), 4) for q in QUANTILES}
    out["n"] = int(a.size)
    return out


def _quantile_block(df: pd.DataFrame, absolute: bool = False) -> dict:
    out: dict = {}
    for col in QUANTILE_COLUMNS:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        out[col] = _q(s.abs() if absolute else s)
    return out


def build_summary(
    df: pd.DataFrame, notes: list[dict], params: dict, elapsed_sec: float
) -> dict:
    liq = df[df["kind"] == "liq"]
    ctl = df[df["kind"] == "control"]

    nan_counts = {"liq": {}, "control": {}}
    for col in QUANTILE_COLUMNS + ["oi_n_bins", "oi_n_buckets", "oi_total_delta"]:
        if col not in df.columns:
            continue
        nan_counts["liq"][col] = int(
            pd.to_numeric(liq[col], errors="coerce").isna().sum()
        )
        nan_counts["control"][col] = int(
            pd.to_numeric(ctl[col], errors="coerce").isna().sum()
        )

    qty = pd.to_numeric(liq["qty"], errors="coerce")
    qbin: dict = {}
    if not qty.dropna().empty:
        arr = qty.dropna().to_numpy()
        t50 = float(np.percentile(arr, 50))
        t90 = float(np.percentile(arr, 90))
        groups = {
            "lo50": qty <= t50,
            "mid50_90": (qty > t50) & (qty <= t90),
            "top10": qty > t90,
        }
        qbin["thresholds"] = {"q50": t50, "q90": t90}
        qbin["median"] = {}
        for gname, mask in groups.items():
            sub = liq[mask.fillna(False)]
            med: dict = {"n": int(len(sub))}
            for col in QUANTILE_COLUMNS:
                if col not in sub.columns:
                    continue
                v = pd.to_numeric(sub[col], errors="coerce").dropna()
                med[col] = round(float(np.median(v.to_numpy())), 4) if not v.empty else None
            qbin["median"][gname] = med

    return {
        "params": params,
        "owner_verbatim": OWNER_VERBATIM,
        "lead_rows_text": LEAD_ROWS_TEXT,
        "elapsed_sec": round(elapsed_sec, 2),
        "rows_total": int(len(df)),
        "rows_liq": int(len(liq)),
        "rows_control": int(len(ctl)),
        "side_counts": {str(k): int(v) for k, v in liq["side"].value_counts().items()},
        "rows_oi_covered": {
            "liq": int(pd.to_numeric(liq["oi_covered"], errors="coerce").sum()),
            "control": int(pd.to_numeric(ctl["oi_covered"], errors="coerce").sum()),
        },
        "days_metrics_missing": sorted(
            {d for n in notes for d in n.get("metrics_days_missing", [])}
        ),
        "days_with_no_oi_rows": [
            n["day"] for n in notes if int(n.get("rows_oi_filled", 0)) == 0
        ],
        "oi_delta_rows_total": sum(int(n.get("oi_delta_rows", 0)) for n in notes),
        "oi_delta_positive_total": sum(
            int(n.get("oi_delta_positive", 0)) for n in notes
        ),
        "oi_delta_nonpositive_total": sum(
            int(n.get("oi_delta_nonpositive", 0)) for n in notes
        ),
        "oi_delta_positive_no_trades_total": sum(
            int(n.get("oi_delta_positive_no_trades", 0)) for n in notes
        ),
        "nan_counts": nan_counts,
        "quantiles": {
            "liq_all": _quantile_block(liq),
            "liq_SELL": _quantile_block(liq[liq["side"] == "SELL"]),
            "liq_BUY": _quantile_block(liq[liq["side"] == "BUY"]),
            "liq_all_abs": _quantile_block(liq, absolute=True),
            "control": _quantile_block(ctl),
            "control_abs": _quantile_block(ctl, absolute=True),
        },
        "qty_bins": qbin,
        "per_day": notes,
        "notes": [
            "観測表のみ。判定(予測できる/できない、使える/使えない)は書いていない。",
            "dist_* / oi_dist_* は既存と同じ符号 (位置 − p_liq) / p_liq * 1e4。"
            "*_liqdir は清算の向きに正へ揃えた列(SELL は +1 倍、BUY は −1 倍、対照は NaN)。",
            "建玉のプロファイルは ΔOI = OI(T) − OI(T−5 分) が**正の 5 分だけ**を、"
            "[T−5 分, T) の aggTrades の VWAP の価格ビンに ΔOI の重みで積んだもの。",
            "側別は同じ 5 分の買い taker / 売り taker の出来高比で ΔOI を割った(仮定)。"
            "SELL 清算にはロング側、BUY 清算にはショート側を当てている。",
            "implied_leverage = 1 / (d/1e4 + mmr)、d = oi_dist_vwap_bp_liqdir。"
            "--mmr を渡さなければ列は全部 NaN。",
            "建玉の被覆が窓に足りない行(metrics 欠測・窓が欠測にかかる)は建玉側を NaN にした。",
        ],
    }


# --------------------------------------------------------------------------
# 走らせる
# --------------------------------------------------------------------------


def run(
    days: list[str],
    root: Path,
    metrics_root: Path,
    out_dir: Path,
    window_hours: float,
    bin_pct: float,
    seed: int,
    mmr: float | None,
    dedup_liq: bool = True,
) -> dict:
    t0 = time.time()
    agg_cache: dict = {}
    bucket_cache: dict = {}
    metrics_cache: dict = {}
    all_rows: list[dict] = []
    notes: list[dict] = []
    for i_day, day in enumerate(days):
        rows, note = process_day(
            day,
            root,
            metrics_root,
            window_hours,
            bin_pct,
            seed,
            agg_cache,
            bucket_cache,
            metrics_cache,
            mmr,
            dedup_liq=dedup_liq,
        )
        all_rows.extend(rows)
        notes.append(note)
        print(
            f"[{day}] 清算 {note['liq_rows_used']} 件(生 {note['liq_rows_in_file']})"
            f" / 対照 {note['control_points_drawn']} 点 -> 行 {note['rows_written']}"
            f" / 建玉あり {note['rows_oi_filled']}"
            f"(metrics 欠 {','.join(note['metrics_days_missing']) or 'なし'})",
            flush=True,
        )
        keep = set(base.days_needed(day, window_hours))
        if i_day + 1 < len(days):
            keep |= set(base.days_needed(days[i_day + 1], window_hours))
        for c in (agg_cache, bucket_cache, metrics_cache):
            for k in list(c):
                if k not in keep:
                    del c[k]

    df = pd.DataFrame(all_rows, columns=COLUMNS)
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "table.csv", index=False)
    elapsed = time.time() - t0
    params = {
        "days": days,
        "window_hours": window_hours,
        "bin_pct": bin_pct,
        "prev_days_read_per_day": base.required_prev_days(window_hours),
        "seed": seed,
        "mmr": mmr,
        "dedup_liq": dedup_liq,
        "liq_price_field": base.DEFAULT_LIQ_PRICE_FIELD,
        "control_gap_minutes": base.CONTROL_GAP_MS / 60000,
        "oi_bucket_minutes": BUCKET_MS / 60000,
        "data_root": str(root),
        "metrics_root": str(metrics_root),
        "symbol": base.SYMBOL,
        "design": "docs/PHASE2/O3C/PRICE_LEVEL/DESIGN_2026-09-17.md",
        "report": "docs/PHASE2/O3C/PRICE_LEVEL/OI_DISTANCE_2026-09-17.md",
    }
    summary = build_summary(df, notes, params, elapsed)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    base.write_md5sums(out_dir, ["table.csv", "summary.json"])
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", required=True, help="清算を置く日(カンマ区切り、YYYY-MM-DD)")
    ap.add_argument("--window-hours", type=float, default=8.0)
    ap.add_argument("--bin-pct", type=float, default=0.1)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--data-root", default=str(base.DEFAULT_DATA_ROOT))
    ap.add_argument("--metrics-root", default=str(DEFAULT_METRICS_ROOT))
    ap.add_argument(
        "--mmr",
        type=float,
        default=None,
        help=(
            "維持証拠金率(小数)。渡したときだけ implied_leverage を出す。"
            "既定は無し(数を作らない)"
        ),
    )
    ap.add_argument(
        "--no-dedup-liq",
        action="store_true",
        help="清算の全列一致の重複行を一意化しない(既存の表との突き合わせ用)",
    )
    a = ap.parse_args(argv)

    days = [d.strip() for d in a.days.split(",") if d.strip()]
    root = Path(a.data_root)
    metrics_root = Path(a.metrics_root)
    for d in days:
        for p in (base.agg_path(root, d), base.liq_path(root, d)):
            if not p.exists():
                raise SystemExit(f"必要な zip が無い: {p}")

    s = run(
        days,
        root,
        metrics_root,
        Path(a.out_dir),
        a.window_hours,
        a.bin_pct,
        a.seed,
        a.mmr,
        dedup_liq=not a.no_dedup_liq,
    )
    print(
        f"行 {s['rows_total']}(清算 {s['rows_liq']} / 対照 {s['rows_control']})"
        f" 建玉あり 清算 {s['rows_oi_covered']['liq']} / 対照 {s['rows_oi_covered']['control']}"
        f" / W = {a.window_hours}h / 所要 {s['elapsed_sec']} 秒 -> {a.out_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
