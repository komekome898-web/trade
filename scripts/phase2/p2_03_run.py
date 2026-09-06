"""P2-03 主検定 反復0 (開発セットのみ) -- docs/PHASE2/P2-03/PREREG.md の凍結手順の実装。

JPX 現物 ETF(TOPIX=1306.T, JPX400=1591.T, グロース250=2516.T, 参照系列=1321.T)の
夜間プレミアム(引成→翌寄成)の事前登録済み主検定を、開発セット(封印外)だけで走らせる。

読み手は `bot.research.sealed.load_unsealed(path, "P2-03")` のみを通す(封印は開けない)。
`load_sealed` はこのスクリプトからは一切呼ばない。

出力:
  backtest_data/phase2_runs/P2-03/iter0_20260906/
    pairs_<SYM>.csv          -- ペアごとの生データ・欠陥フラグ・費用後リターン
    rule_counts.csv          -- 欠陥規則ごとのフラグ件数
    main_indicator.csv       -- 系列 x 費用シナリオ x (除外前/除外後) の平均・CI
    correlation_matrix.csv
    residual_vs_1321.csv
    sign_agreement.csv
    train_val_split.csv
    diagnostics.csv          -- ボラ三分位・曜日・月・年代(記述のみ、選択に使わない)
    controls_sign_shuffle.csv
    controls_vol_tercile.csv -- 対照2(状態内無作為、診断のみ)
    controls_sign_reversal.csv
    controls_individual_stocks.csv -- 対照4(個別株4銘柄、診断のみ)
    band_crossing_1321.csv
    RESULTS.md
    RUN.json

このスクリプトは判定(採用/棄却)を書かない。数値と件数のみ。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from bot.research.sealed import load_unsealed, md5_of  # noqa: E402
from bot.research import overnight as ov  # noqa: E402
from bot.constants import load_constants, require_source  # noqa: E402

UNIT = "P2-03"
SNAPSHOT_DIR = REPO_ROOT / "backtest_data" / "jpx_etf_daily_20260905"
RUNS_BASE_DIR = REPO_ROOT / "backtest_data" / "phase2_runs" / "P2-03"


def default_out_dir(iteration: int) -> Path:
    return RUNS_BASE_DIR / f"iter{iteration}_20260906"

MAIN_SYMBOLS = ["1306.T", "1591.T", "2516.T", "1321.T"]
REFERENCE_SYMBOL = "1321.T"
# 診断専用の対照4(個別株)。同スナップショットの equity 4 銘柄(schema/jpx_etf_daily.json)。
CONTROL4_SYMBOLS = ["7203.T", "6758.T", "8306.T", "9984.T"]

# PREREG.md 表(監査3回目実測)の MDE。判定には使わない(数値の並記のみ)。
MDE_BPS = {"1306.T": 5.10, "1591.T": 5.64, "2516.T": 12.82, "1321.T": 5.26}

TRAIN_END = pd.Timestamp("2019-06-30")
VAL_START = pd.Timestamp("2019-07-01")
VAL_END = pd.Timestamp("2022-03-04")

RUN_SEED = 20260906
BOOT_N = 2000
BOOT_BLOCK = 20
SHUFFLE_N = 1000
CONTROL2_BOOT_N = 1000

# -- 規則1(誤プリント連)のパラメータ(PREREG.md 固定値) -----------------------
BAD_PRINT_DEV_THRESHOLD = 0.30
BAD_PRINT_REVERT_TOLERANCE = 0.05
BAD_PRINT_MAX_K = 3

# -- 規則2(split_candidate)のパラメータ(scripts/data_quality.py と同一) -----
SPLIT_FACTORS = [2, 3, 4, 5, 10, 100]
SPLIT_TOLERANCE = 0.02
SPLIT_PERSIST_TOLERANCE = 0.05


# ===========================================================================
# 呼値の帯(config/constants.yaml jpx_cash_equity.etf_tick_size_yen_by_price_band)
# ===========================================================================

def parse_tick_bands(band_value: dict) -> tuple[list[tuple[float, float]], float]:
    """{'up_to_10000_yen': 1, ..., 'over_50000000_yen': 10000} を
    ([(上限円, 呼値円), ...] 昇順, 最上位帯を超えた場合の呼値) に変換する。"""
    ups: list[tuple[float, float]] = []
    over = None
    for key, val in band_value.items():
        if key.startswith("up_to_") and key.endswith("_yen"):
            bound = float(key[len("up_to_"):-len("_yen")])
            ups.append((bound, float(val)))
        elif key.startswith("over_") and key.endswith("_yen"):
            over = float(val)
    ups.sort(key=lambda t: t[0])
    if over is None:
        over = ups[-1][1] if ups else float("nan")
    return ups, over


def tick_for_price(price: float, bands: tuple[list[tuple[float, float]], float]) -> float:
    """close(t) が属する帯の呼値(円)。境界は「以下」で含む
    (10,000 -> 1円, 10,001 -> 5円, 30,001 -> 10円、既定テスト参照)。"""
    ups, over = bands
    if price is None or not np.isfinite(price):
        return float("nan")
    for bound, tick in ups:
        if price <= bound:
            return tick
    return over


# ===========================================================================
# 反復1: 1306.T の価格水準補正(schema/jpx_etf_daily.json CORRECTION 2026-09-06、
# 一次情報 backtest_data/audit_fetch_1306_split_20260906/)
#
# 1306.T の10:1分割は2026-04-01が実効日(2015年ではない)。CSVの2015-01-05〜
# 2026-03-31 区間はベンダーが分割調整を誤った開始日から適用したため、実勢価格の
# ちょうど1/10になっている(独立系列: 2022-03-04 の実勢終値1,920.5円 vs CSV
# 192.05円)。この区間内では close/open の「比率」(リターン)は補正不要
# (定数倍はリターンに影響しない)だが、価格そのものを使う量(呼値帯の判定、
# 呼値コストのbps換算、想定元本)は実勢価格(CSV値×10)を使わなければならない。
# 2015-01-05 の水準シフト自体は規則2(split_candidate)がそのまま拾う
# (誤プリント同様、跨ぐペアは除外対象のまま変更しない)。
# ===========================================================================
PRICE_LEVEL_CORRECTIONS: dict[str, list[tuple[str, str, float]]] = {
    "1306.T": [("2015-01-05", "2026-03-31", 10.0)],
}


def corrected_price_for_band(
    sym: str, date, raw_price: float,
    corrections: dict[str, list[tuple[str, str, float]]] | None = None,
) -> float:
    """`raw_price`(CSVの値)に、価格水準補正テーブルの倍率を掛けた「実勢価格」を返す。

    呼値帯の判定・呼値コストのbps換算・想定元本など「価格そのもの」を使う量に
    のみ使う。r_night/r_day などのリターン(比率)には絶対に使わない
    -- 区間内は定数倍なので比率は不変であり、区間境界の水準シフトは規則2の
    split_candidate 除外が別途処理する。

    `corrections` を空 dict / None 以外の未設定にすると補正なし(反復0と同じ)。
    """
    if corrections is None:
        corrections = PRICE_LEVEL_CORRECTIONS
    if raw_price is None or not np.isfinite(raw_price):
        return raw_price
    date_ts = pd.Timestamp(date)
    for start, end, factor in corrections.get(sym, []):
        if pd.Timestamp(start) <= date_ts <= pd.Timestamp(end):
            return raw_price * factor
    return raw_price


# ===========================================================================
# 既知欠陥規則
# ===========================================================================

def _finite(x) -> bool:
    return x is not None and np.isfinite(x)


def _matches_round_factor(x: float) -> bool:
    for f in SPLIT_FACTORS:
        if abs(x - f) / f <= SPLIT_TOLERANCE:
            return True
    return False


def _is_split_ratio(ratio: float | None) -> bool:
    if ratio is None or not np.isfinite(ratio) or ratio <= 0:
        return False
    return _matches_round_factor(ratio) or _matches_round_factor(1.0 / ratio)


def detect_split_candidates(closes) -> np.ndarray:
    """規則2: scripts/data_quality.py の split_candidate ロジックの再実装
    (close 列のみ・行の並び順のまま。null 行は None/NaN として自然にスキップされる)。"""
    closes = list(closes)
    n = len(closes)
    mask = np.zeros(n, dtype=bool)
    for i in range(1, n - 1):
        prev_c, cur_c, next_c = closes[i - 1], closes[i], closes[i + 1]
        if not _finite(prev_c) or prev_c == 0 or not _finite(cur_c) or cur_c == 0 or not _finite(next_c):
            continue
        ratio = cur_c / prev_c
        if not _is_split_ratio(ratio):
            continue
        if abs(next_c / cur_c - 1.0) > SPLIT_PERSIST_TOLERANCE:
            continue  # 翌日に戻る = 一日限りの往復(誤プリント側)であり、分割ではない
        if i - 2 >= 0:
            prev2_c = closes[i - 2]
            if _finite(prev2_c) and prev2_c != 0 and abs(prev_c / prev2_c - 1.0) > SPLIT_PERSIST_TOLERANCE:
                continue
        mask[i] = True
    return mask


def detect_bad_print_runs(
    opens: np.ndarray,
    closes: np.ndarray,
    max_k: int = BAD_PRINT_MAX_K,
    dev_threshold: float = BAD_PRINT_DEV_THRESHOLD,
    revert_tolerance: float = BAD_PRINT_REVERT_TOLERANCE,
) -> tuple[np.ndarray, int, list[dict]]:
    """規則1: 連続する k<=max_k 行の open と close が両方とも、直前行の close (c0) から
    dev_threshold 超乖離し、かつ直後行の close が c0 の ±revert_tolerance 以内に戻る場合、
    その k 行を誤プリント行とする(AND は意図的。片方だけの乖離は one_sided として計上)。

    先頭行・末尾行は基準値(c0)または直後の復帰確認行が存在しないため判定対象外
    (規則の対象は interior 行 index 1..n-2 のみ)。

    戻り値: (mask, one_sided_count, events)
    """
    n = len(closes)
    mask = np.zeros(n, dtype=bool)
    events: list[dict] = []
    one_sided = 0

    def far(x: float, c0: float) -> bool:
        return _finite(x) and _finite(c0) and c0 != 0 and abs(x / c0 - 1.0) > dev_threshold

    if n < 3:
        return mask, one_sided, events

    i = 1
    while i <= n - 2:
        c0 = closes[i - 1]
        if not _finite(c0) or c0 == 0:
            i += 1
            continue
        o_far = far(opens[i], c0)
        c_far = far(closes[i], c0)
        if not (o_far and c_far):
            if o_far != c_far and _finite(opens[i]) and _finite(closes[i]):
                one_sided += 1
            i += 1
            continue
        # i は連の先頭候補。k=1..max_k まで延長を試みる。
        run_end = i
        k = 1
        while k < max_k and (run_end + 1) <= n - 2:
            nxt = run_end + 1
            if far(opens[nxt], c0) and far(closes[nxt], c0):
                run_end = nxt
                k += 1
            else:
                break
        revert_idx = run_end + 1
        if revert_idx > n - 1:
            i = run_end + 1
            continue
        revert_close = closes[revert_idx]
        if _finite(revert_close) and abs(revert_close / c0 - 1.0) <= revert_tolerance:
            mask[i:run_end + 1] = True
            events.append({"start": i, "end": run_end, "k": run_end - i + 1, "c0": float(c0)})
            i = revert_idx  # 復帰行から再開(連の内部を再走査しない)
        else:
            i += 1  # 連にならなかった -> 1 行ずつ進める
    return mask, one_sided, events


def detect_ghost_rows(open_, high, low, close, volume) -> np.ndarray:
    """規則5: 出来高0 かつ四本値同一 かつ close が前行と等しい行(P2-02 で発見)。"""
    n = len(close)
    mask = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if not (_finite(volume[i]) and volume[i] == 0):
            continue
        if not (_finite(open_[i]) and _finite(high[i]) and _finite(low[i]) and _finite(close[i])):
            continue
        if not (open_[i] == high[i] == low[i] == close[i]):
            continue
        prev_close = close[i - 1]
        if not _finite(prev_close) or close[i] != prev_close:
            continue
        mask[i] = True
    return mask


# ===========================================================================
# 系列ごとの読み込み・ペア構築
# ===========================================================================

def analyze_series(sym: str, bands, apply_price_correction: bool = False) -> dict:
    csv_path = SNAPSHOT_DIR / f"{sym}.csv"
    df = load_unsealed(csv_path, UNIT)
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    n = len(df)

    open_ = df["open"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float) if "high" in df.columns else np.full(n, np.nan)
    low = df["low"].to_numpy(dtype=float) if "low" in df.columns else np.full(n, np.nan)
    close = df["close"].to_numpy(dtype=float)
    volume = df["volume"].to_numpy(dtype=float) if "volume" in df.columns else np.full(n, np.nan)
    dates = df["date"]

    null_mask = np.isnan(open_) | np.isnan(close)
    ghost_mask = detect_ghost_rows(open_, high, low, close, volume)
    split_mask = detect_split_candidates(close.tolist())
    badprint_mask, one_sided_count, badprint_events = detect_bad_print_runs(open_, close)
    row_flag = null_mask | ghost_mask | split_mask | badprint_mask

    if n < 2:
        raise RuntimeError(f"{sym}: dev set has fewer than 2 rows ({n})")

    date_t = dates.iloc[:-1].reset_index(drop=True)
    date_t1 = dates.iloc[1:].reset_index(drop=True)
    open_t = open_[:-1]
    close_t = close[:-1]
    open_t1 = open_[1:]

    r_night_bps = (open_t1 / close_t - 1.0) * 1e4
    r_day_bps_full = (close / open_ - 1.0) * 1e4
    r_day_bps_t = r_day_bps_full[:-1]

    corrections = PRICE_LEVEL_CORRECTIONS if apply_price_correction else {}
    band_price_t = np.array([
        corrected_price_for_band(sym, d, c, corrections) for d, c in zip(date_t, close_t)
    ])
    ticks = np.array([tick_for_price(p, bands) for p in band_price_t])
    with np.errstate(divide="ignore", invalid="ignore"):
        # bps 換算の分母も実勢価格(band_price_t) -- コストは実勢価格に対する割合
        cost_cons_bps = np.where(np.isfinite(band_price_t) & (band_price_t != 0),
                                  2.0 * ticks / band_price_t * 1e4, np.nan)

    net_opt_bps = r_night_bps.copy()
    net_cons_bps = r_night_bps - cost_cons_bps

    excluded_t = row_flag[:-1] | row_flag[1:]
    valid_raw = np.isfinite(r_night_bps) & np.isfinite(r_day_bps_t)
    clean = valid_raw & (~excluded_t)

    pairs = pd.DataFrame({
        "date_t": date_t, "date_t1": date_t1,
        "open_t": open_t, "close_t": close_t, "open_t1": open_t1,
        "r_day_bps": r_day_bps_t, "r_night_bps": r_night_bps,
        "band_price_t": band_price_t, "tick_yen": ticks, "cost_cons_bps": cost_cons_bps,
        "net_opt_bps": net_opt_bps, "net_cons_bps": net_cons_bps,
        "flag_null_t": null_mask[:-1], "flag_null_t1": null_mask[1:],
        "flag_ghost_t": ghost_mask[:-1], "flag_ghost_t1": ghost_mask[1:],
        "flag_split_t": split_mask[:-1], "flag_split_t1": split_mask[1:],
        "flag_badprint_t": badprint_mask[:-1], "flag_badprint_t1": badprint_mask[1:],
        "excluded": excluded_t, "valid_raw": valid_raw, "clean": clean,
    })

    return {
        "sym": sym,
        "df": df,
        "pairs": pairs,
        "n_rows": n,
        "n_null_rows": int(null_mask.sum()),
        "n_ghost_rows": int(ghost_mask.sum()),
        "n_split_rows": int(split_mask.sum()),
        "n_badprint_rows": int(badprint_mask.sum()),
        "n_one_sided_info": one_sided_count,
        "badprint_events": badprint_events,
    }


# ===========================================================================
# 指標
# ===========================================================================

def _boot_ci(x: np.ndarray, rng: np.random.Generator) -> tuple[float, float]:
    if len(x) == 0:
        return float("nan"), float("nan")
    seed = int(rng.integers(0, 2**31 - 1))
    return ov.block_bootstrap_ci(x, block=BOOT_BLOCK, n_boot=BOOT_N, seed=seed)


def mean_ci(x: np.ndarray, rng: np.random.Generator) -> dict:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {"n": 0, "mean_bps": float("nan"), "ci_lo": float("nan"), "ci_hi": float("nan")}
    lo, hi = _boot_ci(x, rng)
    return {"n": int(len(x)), "mean_bps": float(x.mean()), "ci_lo": lo, "ci_hi": hi}


def sharpe_stats(x_bps: np.ndarray, dates: pd.Series) -> dict:
    x_bps = np.asarray(x_bps, dtype=float)
    mask = np.isfinite(x_bps)
    x_bps = x_bps[mask]
    dates = dates[mask].reset_index(drop=True)
    n = len(x_bps)
    if n < 2 or dates.iloc[-1] <= dates.iloc[0]:
        return {"n": n, "years": float("nan"), "periods_per_year": float("nan"), "sharpe": float("nan")}
    span_days = (dates.iloc[-1] - dates.iloc[0]).days
    years = span_days / 365.25
    periods_per_year = n / years if years > 0 else float("nan")
    frac = x_bps / 1e4
    sigma = frac.std(ddof=1)
    sharpe = float(frac.mean() / sigma * np.sqrt(periods_per_year)) if sigma > 0 else float("nan")
    return {"n": n, "years": float(years), "periods_per_year": float(periods_per_year), "sharpe": sharpe}


def max_drawdown_bps(x_bps: np.ndarray) -> float:
    x_bps = np.asarray(x_bps, dtype=float)
    x_bps = x_bps[np.isfinite(x_bps)]
    if len(x_bps) == 0:
        return float("nan")
    cum = np.cumsum(x_bps)
    running_max = np.maximum.accumulate(cum)
    return float((cum - running_max).min())


def hit_rate(x_bps: np.ndarray) -> float:
    x_bps = np.asarray(x_bps, dtype=float)
    x_bps = x_bps[np.isfinite(x_bps)]
    return float((x_bps > 0).mean()) if len(x_bps) else float("nan")


# ===========================================================================
# 対照(反事実)
# ===========================================================================

def control1_sign_shuffle(x_bps: np.ndarray, rng: np.random.Generator) -> dict:
    x_bps = np.asarray(x_bps, dtype=float)
    x_bps = x_bps[np.isfinite(x_bps)]
    if len(x_bps) == 0:
        return {"n": 0, "observed_mean_bps": float("nan"), "null_p95_bps": float("nan"),
                "null_mean_bps": float("nan")}
    seed = int(rng.integers(0, 2**31 - 1))
    null = ov.sign_shuffle_null(x_bps, n=SHUFFLE_N, seed=seed)
    return {
        "n": int(len(x_bps)),
        "observed_mean_bps": float(x_bps.mean()),
        "null_mean_bps": float(null.mean()),
        "null_p95_bps": float(np.percentile(null, 95)),
    }


def control2_vol_tercile_random_holding(pairs_clean: pd.DataFrame, rng: np.random.Generator) -> list[dict]:
    """対照2(診断のみ): 20日実現ボラ三分位ごとに、同数の無作為保有(全体プールからの
    復元抽出)と実測平均を比較する。選択・判定には使わない。"""
    out: list[dict] = []
    if "vol_tercile" not in pairs_clean.columns or pairs_clean["vol_tercile"].isna().all():
        return out
    full = pairs_clean["r_night_bps"].to_numpy(dtype=float)
    full = full[np.isfinite(full)]
    for tercile, grp in pairs_clean.groupby("vol_tercile", observed=True):
        vals = grp["r_night_bps"].to_numpy(dtype=float)
        vals = vals[np.isfinite(vals)]
        n = len(vals)
        if n == 0 or len(full) == 0:
            continue
        seed = int(rng.integers(0, 2**31 - 1))
        rng2 = np.random.default_rng(seed)
        boot_means = np.array([rng2.choice(full, size=n, replace=True).mean() for _ in range(CONTROL2_BOOT_N)])
        out.append({
            "tercile": str(tercile), "n": n,
            "observed_mean_bps": float(vals.mean()),
            "null_mean_bps": float(boot_means.mean()),
            "null_ci_lo": float(np.percentile(boot_means, 2.5)),
            "null_ci_hi": float(np.percentile(boot_means, 97.5)),
        })
    return out


def control3_sign_reversal(pairs_clean: pd.DataFrame, rng: np.random.Generator) -> dict:
    """対照3: 夜間売り持ち。費用は方向によらず同額(往復1ティック/片側)発生するため
    net_short = -r_night - cost。"""
    r = pairs_clean["r_night_bps"].to_numpy(dtype=float)
    cost = pairs_clean["cost_cons_bps"].to_numpy(dtype=float)
    short_opt = -r
    short_cons = -r - cost
    return {
        "net_short_opt": mean_ci(short_opt, rng),
        "net_short_cons": mean_ci(short_cons, rng),
    }


# ===========================================================================
# 診断(記述のみ)
# ===========================================================================

def add_diagnostic_columns(pairs: pd.DataFrame, df_full: pd.DataFrame) -> pd.DataFrame:
    pairs = pairs.copy()
    pairs["weekday"] = pairs["date_t"].dt.dayofweek  # 0=Mon .. 4=Fri
    pairs["month"] = pairs["date_t"].dt.month

    if len(pairs):
        first, last = pairs["date_t"].min(), pairs["date_t"].max()
        span = (last - first).days
        b1 = first + pd.Timedelta(days=span // 3)
        b2 = first + pd.Timedelta(days=2 * span // 3)
        pairs["era"] = np.select(
            [pairs["date_t"] <= b1, pairs["date_t"] <= b2],
            ["era1", "era2"], default="era3",
        )
    else:
        pairs["era"] = pd.Series(dtype=object)

    # 20日実現ボラ(日中リターンの20日ローリング標準偏差、close(t)日基準)
    r_day_full = (df_full["close"].astype(float) / df_full["open"].astype(float) - 1.0) * 1e4
    vol20 = r_day_full.rolling(20, min_periods=20).std()
    vol_by_date = pd.Series(vol20.to_numpy(), index=df_full["date"].to_numpy())
    pairs["vol20"] = pairs["date_t"].map(vol_by_date)
    try:
        pairs["vol_tercile"] = pd.qcut(pairs["vol20"], 3, labels=["low", "mid", "high"], duplicates="drop")
    except (ValueError, IndexError):
        pairs["vol_tercile"] = pd.NA
    return pairs


def diagnostics_table(sym: str, pairs_clean: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    for dim in ("vol_tercile", "weekday", "month", "era"):
        if dim not in pairs_clean.columns:
            continue
        g = pairs_clean.dropna(subset=[dim]).groupby(dim, observed=True)["r_night_bps"]
        for bucket, s in g:
            s = s[np.isfinite(s)]
            if len(s) == 0:
                continue
            rows.append({"series": sym, "dimension": dim, "bucket": str(bucket),
                         "n": int(len(s)), "mean_r_night_bps": float(s.mean())})
    return rows


# ===========================================================================
# メイン
# ===========================================================================

def git_rev() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "unknown"


def main(out_dir: Path | None = None, iteration: int = 0, apply_price_correction: bool = False) -> Path:
    out_dir = Path(out_dir) if out_dir is not None else default_out_dir(iteration)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(RUN_SEED)

    constants = load_constants(REPO_ROOT)
    tick_const = require_source("jpx_cash_equity.etf_tick_size_yen_by_price_band", constants)
    bands = parse_tick_bands(tick_const.value)
    commission_const = require_source("jpx_cash_equity.sor_commission_yen", constants)
    assert commission_const.value == 0, "手数料が0円想定と食い違う -- コスト式の見直しが必要"

    results: dict[str, dict] = {}
    for sym in MAIN_SYMBOLS:
        res = analyze_series(sym, bands, apply_price_correction=apply_price_correction)
        res["pairs"] = add_diagnostic_columns(res["pairs"], res["df"])
        results[sym] = res

    control4_results: dict[str, dict] = {}
    for sym in CONTROL4_SYMBOLS:
        try:
            # 対照4銘柄は価格水準補正の対象外(補正テーブルは1306.Tのみ)。
            control4_results[sym] = analyze_series(sym, bands, apply_price_correction=apply_price_correction)
        except Exception as exc:  # 診断専用、失敗しても主検定は止めない
            control4_results[sym] = {"error": str(exc)}

    # -- rule_counts.csv --------------------------------------------------
    rule_rows = []
    for sym, res in results.items():
        pairs = res["pairs"]
        rule_rows.append({
            "series": sym,
            "n_rows_dev": res["n_rows"],
            "n_pairs_total": len(pairs),
            "rule1_badprint_rows": res["n_badprint_rows"],
            "rule1_badprint_runs": len(res["badprint_events"]),
            "rule1_one_sided_info_rows": res["n_one_sided_info"],
            "rule2_split_rows": res["n_split_rows"],
            "rule3_null_rows": res["n_null_rows"],
            "rule5_ghost_rows": res["n_ghost_rows"],
            "n_pairs_excluded": int(pairs["excluded"].sum()),
            "n_pairs_valid_raw": int(pairs["valid_raw"].sum()),
            "n_pairs_clean": int(pairs["clean"].sum()),
        })
    pd.DataFrame(rule_rows).to_csv(out_dir / "rule_counts.csv", index=False)

    # -- main_indicator.csv (before/after x optimistic/conservative) ------
    indicator_rows = []
    for sym, res in results.items():
        pairs = res["pairs"]
        for stage, mask_col in (("before_exclusion", "valid_raw"), ("after_exclusion", "clean")):
            sub = pairs.loc[pairs[mask_col]]
            opt = mean_ci(sub["net_opt_bps"].to_numpy(), rng)
            cons = mean_ci(sub["net_cons_bps"].to_numpy(), rng)
            indicator_rows.append({"series": sym, "stage": stage, "cost_scenario": "optimistic", **opt})
            indicator_rows.append({"series": sym, "stage": stage, "cost_scenario": "conservative", **cons})
    indicator_df = pd.DataFrame(indicator_rows)
    indicator_df.to_csv(out_dir / "main_indicator.csv", index=False)

    # -- 系列別サマリ(clean のみ): sharpe / maxdd / hitrate / night-day 差 --
    summary_rows = []
    for sym, res in results.items():
        pairs = res["pairs"]
        clean = pairs.loc[pairs["clean"]]
        gross_ci = mean_ci(clean["r_night_bps"].to_numpy(), rng)
        cons_ci = mean_ci(clean["net_cons_bps"].to_numpy(), rng)
        diff = (clean["r_night_bps"] - clean["r_day_bps"]).to_numpy()
        diff_ci = mean_ci(diff, rng)
        sh_gross = sharpe_stats(clean["r_night_bps"].to_numpy(), clean["date_t"])
        sh_cons = sharpe_stats(clean["net_cons_bps"].to_numpy(), clean["date_t"])
        summary_rows.append({
            "series": sym,
            "n_clean": len(clean),
            "mean_gross_bps": gross_ci["mean_bps"], "gross_ci_lo": gross_ci["ci_lo"], "gross_ci_hi": gross_ci["ci_hi"],
            "mean_net_cons_bps": cons_ci["mean_bps"], "cons_ci_lo": cons_ci["ci_lo"], "cons_ci_hi": cons_ci["ci_hi"],
            "mde_bps": MDE_BPS[sym],
            "gate_cons_mean_gt_mde": bool(cons_ci["mean_bps"] > MDE_BPS[sym]) if np.isfinite(cons_ci["mean_bps"]) else None,
            "mean_day_bps": float(clean["r_day_bps"].mean()) if len(clean) else float("nan"),
            "night_minus_day_mean_bps": diff_ci["mean_bps"], "night_minus_day_ci_lo": diff_ci["ci_lo"],
            "night_minus_day_ci_hi": diff_ci["ci_hi"],
            "sharpe_gross_annualized": sh_gross["sharpe"], "sharpe_gross_n": sh_gross["n"], "sharpe_gross_years": sh_gross["years"],
            "sharpe_cons_annualized": sh_cons["sharpe"], "sharpe_cons_n": sh_cons["n"], "sharpe_cons_years": sh_cons["years"],
            "max_dd_gross_bps": max_drawdown_bps(clean["r_night_bps"].to_numpy()),
            "max_dd_cons_bps": max_drawdown_bps(clean["net_cons_bps"].to_numpy()),
            "hit_rate_gross": hit_rate(clean["r_night_bps"].to_numpy()),
        })
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(out_dir / "summary_by_series.csv", index=False)

    # -- sign agreement (b) vs 1321 (gross r_night, clean) -----------------
    ref_mean = summary_df.loc[summary_df["series"] == REFERENCE_SYMBOL, "mean_gross_bps"].iloc[0]
    sign_rows = []
    for sym in MAIN_SYMBOLS:
        m = summary_df.loc[summary_df["series"] == sym, "mean_gross_bps"].iloc[0]
        sign_rows.append({"series": sym, "mean_gross_bps": m,
                           "sign_matches_1321": bool(np.sign(m) == np.sign(ref_mean)) if np.isfinite(m) and np.isfinite(ref_mean) else None})
    pd.DataFrame(sign_rows).to_csv(out_dir / "sign_agreement.csv", index=False)

    # -- correlation matrix + residual vs 1321 (共通日, clean) -------------
    frames = {}
    for sym, res in results.items():
        p = res["pairs"]
        s = p.loc[p["clean"], ["date_t", "r_night_bps"]].set_index("date_t")["r_night_bps"]
        s.name = sym
        frames[sym] = s
    merged = pd.concat(frames.values(), axis=1, sort=True)
    merged.columns = list(frames.keys())
    merged = merged.sort_index()
    corr = merged.corr()
    corr.to_csv(out_dir / "correlation_matrix.csv")

    residual_rows = []
    ref_series = merged[REFERENCE_SYMBOL]
    for sym in MAIN_SYMBOLS:
        if sym == REFERENCE_SYMBOL:
            continue
        common = pd.concat([merged[sym], ref_series], axis=1).dropna()
        common.columns = ["etf", "ref"]
        resid = (common["etf"] - common["ref"]).to_numpy()
        ci = mean_ci(resid, rng)
        residual_rows.append({"series": sym, "n_common": len(common), **ci})
    pd.DataFrame(residual_rows).to_csv(out_dir / "residual_vs_1321.csv", index=False)

    # -- train / val split --------------------------------------------------
    tv_rows = []
    for sym, res in results.items():
        pairs = res["pairs"]
        clean = pairs.loc[pairs["clean"]]
        train = clean.loc[clean["date_t"] <= TRAIN_END]
        val = clean.loc[(clean["date_t"] >= VAL_START) & (clean["date_t"] <= VAL_END)]
        for split_name, sub in (("train", train), ("val", val)):
            opt = mean_ci(sub["net_opt_bps"].to_numpy(), rng)
            cons = mean_ci(sub["net_cons_bps"].to_numpy(), rng)
            tv_rows.append({"series": sym, "split": split_name,
                             "n": len(sub),
                             "mean_opt_bps": opt["mean_bps"], "opt_ci_lo": opt["ci_lo"], "opt_ci_hi": opt["ci_hi"],
                             "mean_cons_bps": cons["mean_bps"], "cons_ci_lo": cons["ci_lo"], "cons_ci_hi": cons["ci_hi"]})
    pd.DataFrame(tv_rows).to_csv(out_dir / "train_val_split.csv", index=False)

    # -- diagnostics (記述のみ) ---------------------------------------------
    diag_rows = []
    for sym, res in results.items():
        pairs = res["pairs"]
        clean = pairs.loc[pairs["clean"]]
        diag_rows.extend(diagnostics_table(sym, clean))
    pd.DataFrame(diag_rows).to_csv(out_dir / "diagnostics.csv", index=False)

    # -- controls ------------------------------------------------------------
    c1_rows = []
    c2_rows = []
    c3_rows = []
    for sym, res in results.items():
        pairs = res["pairs"]
        clean = pairs.loc[pairs["clean"]]
        c1 = control1_sign_shuffle(clean["r_night_bps"].to_numpy(), rng)
        c1_rows.append({"series": sym, **c1})
        for row in control2_vol_tercile_random_holding(clean, rng):
            c2_rows.append({"series": sym, **row})
        c3 = control3_sign_reversal(clean, rng)
        c3_rows.append({"series": sym,
                         "net_short_opt_mean_bps": c3["net_short_opt"]["mean_bps"],
                         "net_short_opt_ci_lo": c3["net_short_opt"]["ci_lo"],
                         "net_short_opt_ci_hi": c3["net_short_opt"]["ci_hi"],
                         "net_short_cons_mean_bps": c3["net_short_cons"]["mean_bps"],
                         "net_short_cons_ci_lo": c3["net_short_cons"]["ci_lo"],
                         "net_short_cons_ci_hi": c3["net_short_cons"]["ci_hi"]})
    pd.DataFrame(c1_rows).to_csv(out_dir / "controls_sign_shuffle.csv", index=False)
    pd.DataFrame(c2_rows).to_csv(out_dir / "controls_vol_tercile.csv", index=False)
    pd.DataFrame(c3_rows).to_csv(out_dir / "controls_sign_reversal.csv", index=False)

    # -- control 4: 個別株4銘柄(診断のみ) ------------------------------------
    c4_rows = []
    for sym, res in control4_results.items():
        if "error" in res:
            c4_rows.append({"series": sym, "error": res["error"]})
            continue
        clean = res["pairs"].loc[res["pairs"]["clean"]]
        gross_ci = mean_ci(clean["r_night_bps"].to_numpy(), rng)
        c4_rows.append({"series": sym, "n_clean": len(clean), **gross_ci})
    pd.DataFrame(c4_rows).to_csv(out_dir / "controls_individual_stocks.csv", index=False)

    # -- 1321 帯またぎ回数(生の close 系列、全開発セット行) -------------------
    df1321 = results[REFERENCE_SYMBOL]["df"]
    closes_1321 = df1321["close"].to_numpy(dtype=float)
    band_idx = np.array([tick_for_price(c, bands) for c in closes_1321])
    valid = np.isfinite(band_idx)
    crossings = 0
    prev = None
    for v, ok in zip(band_idx, valid):
        if not ok:
            continue
        if prev is not None and v != prev:
            crossings += 1
        prev = v
    pd.DataFrame([{"series": REFERENCE_SYMBOL, "n_rows": int(valid.sum()), "band_crossings": crossings}]).to_csv(
        out_dir / "band_crossing_1321.csv", index=False)

    # -- per-pair raw CSV -----------------------------------------------------
    for sym, res in results.items():
        safe = sym.replace(".", "")
        res["pairs"].to_csv(out_dir / f"pairs_{safe}.csv", index=False)

    # -- RUN.json --------------------------------------------------------------
    md5s = {}
    for sym in MAIN_SYMBOLS + CONTROL4_SYMBOLS:
        p = SNAPSHOT_DIR / f"{sym}.csv"
        if p.is_file():
            md5s[sym] = md5_of(p)

    # -- 反復1(価格水準補正)のときは反復0の出力と突き合わせる ------------------
    iter0_ref = None if iteration == 0 else load_iter0_reference()
    comparison = None
    if iter0_ref is not None:
        comparison = build_iter0_vs_iter1_comparison(iter0_ref, results, summary_df, out_dir)

    run_meta = {
        "unit": UNIT,
        "iteration": iteration,
        "apply_price_correction": apply_price_correction,
        "price_level_corrections": PRICE_LEVEL_CORRECTIONS if apply_price_correction else {},
        "seed": RUN_SEED,
        "git_rev": git_rev(),
        "prereg_path": "docs/PHASE2/P2-03/PREREG.md",
        "snapshot_dir": str(SNAPSHOT_DIR.relative_to(REPO_ROOT)),
        "input_md5": md5s,
        "boot_n": BOOT_N, "boot_block": BOOT_BLOCK, "shuffle_n": SHUFFLE_N,
        "train_end": str(TRAIN_END.date()), "val_start": str(VAL_START.date()), "val_end": str(VAL_END.date()),
        "n_per_step": {
            sym: {
                "n_rows_dev": res["n_rows"],
                "n_pairs_total": len(res["pairs"]),
                "n_null_rows": res["n_null_rows"],
                "n_ghost_rows": res["n_ghost_rows"],
                "n_split_rows": res["n_split_rows"],
                "n_badprint_rows": res["n_badprint_rows"],
                "n_pairs_excluded": int(res["pairs"]["excluded"].sum()),
                "n_pairs_clean": int(res["pairs"]["clean"].sum()),
            }
            for sym, res in results.items()
        },
        "mde_bps": MDE_BPS,
        "iter0_vs_iter1_comparison": comparison,
    }
    (out_dir / "RUN.json").write_text(json.dumps(run_meta, indent=2, ensure_ascii=False), encoding="utf-8")

    extra = {
        "sign_rows": sign_rows,
        "corr": corr,
        "residual_rows": residual_rows,
        "c1_rows": c1_rows,
        "c2_rows": c2_rows,
        "c3_rows": c3_rows,
        "tv_rows": tv_rows,
        "band_crossings": crossings,
        "band_n_rows": int(valid.sum()),
        "diag_rows": diag_rows,
        "comparison": comparison,
    }
    write_results_md(results, summary_df, indicator_df, control4_results, run_meta, rule_rows, extra, out_dir)
    print(f"wrote outputs to {out_dir}")
    return out_dir


def load_iter0_reference() -> dict | None:
    """反復0の出力(backtest_data/phase2_runs/P2-03/iter0_20260906/)を読み込む。
    存在しなければ None(比較セクションを省略)。"""
    ref_dir = default_out_dir(0)
    summary_path = ref_dir / "summary_by_series.csv"
    if not summary_path.is_file():
        return None
    ref_summary = pd.read_csv(summary_path)
    ref_pairs = {}
    for sym in MAIN_SYMBOLS:
        safe = sym.replace(".", "")
        p = ref_dir / f"pairs_{safe}.csv"
        if p.is_file():
            ref_pairs[sym] = pd.read_csv(p)
    return {"dir": ref_dir, "summary": ref_summary, "pairs": ref_pairs}


def build_iter0_vs_iter1_comparison(iter0_ref: dict, results: dict, summary_df: pd.DataFrame,
                                     out_dir: Path) -> dict:
    """1306.T の反復0→反復1比較(保守平均・CI・平均コスト)と、他3系列が
    価格水準補正の影響を受けていないことの diff 確認。

    diff は、反復0側(CSVから読み込み)と同じ土俵で比較するため、反復1側も
    (メモリ上の DataFrame ではなく)このディレクトリに書き出したばかりの
    pairs_<SYM>.csv を読み直して使う -- そうしないと date_t の dtype
    (datetime64 vs CSV読み込みの文字列)のような、値としては同一でも
    dtype が異なるだけの差分が偽陽性になる。"""
    row0 = iter0_ref["summary"].loc[iter0_ref["summary"]["series"] == "1306.T"].iloc[0]
    row1 = summary_df.loc[summary_df["series"] == "1306.T"].iloc[0]

    pairs1 = pd.read_csv(out_dir / "pairs_1306T.csv")
    clean1 = pairs1.loc[pairs1["clean"]]
    mean_cost1 = float(clean1["cost_cons_bps"].mean()) if len(clean1) else float("nan")

    pairs0 = iter0_ref["pairs"].get("1306.T")
    if pairs0 is not None and "clean" in pairs0.columns:
        clean0 = pairs0.loc[pairs0["clean"]]
        mean_cost0 = float(clean0["cost_cons_bps"].mean()) if len(clean0) else float("nan")
    else:
        mean_cost0 = float("nan")

    symbol_1306 = {
        "iter0_mean_cons_bps": float(row0["mean_net_cons_bps"]),
        "iter0_ci_lo": float(row0["cons_ci_lo"]), "iter0_ci_hi": float(row0["cons_ci_hi"]),
        "iter0_mean_cost_bps": mean_cost0,
        "iter1_mean_cons_bps": float(row1["mean_net_cons_bps"]),
        "iter1_ci_lo": float(row1["cons_ci_lo"]), "iter1_ci_hi": float(row1["cons_ci_hi"]),
        "iter1_mean_cost_bps": mean_cost1,
    }

    other_unchanged = {}
    for sym in MAIN_SYMBOLS:
        if sym == "1306.T":
            continue
        p0 = iter0_ref["pairs"].get(sym)
        safe = sym.replace(".", "")
        p1 = pd.read_csv(out_dir / f"pairs_{safe}.csv")
        if p0 is None:
            other_unchanged[sym] = None
            continue
        shared_cols = [c for c in p0.columns if c in p1.columns]
        try:
            eq = p0[shared_cols].reset_index(drop=True).equals(p1[shared_cols].reset_index(drop=True))
        except Exception:
            eq = False
        other_unchanged[sym] = bool(eq)

    return {"symbol_1306": symbol_1306, "other_series_unchanged": other_unchanged}


def write_results_md(results, summary_df, indicator_df, control4_results, run_meta, rule_rows, extra, out_dir: Path) -> None:
    it = run_meta["iteration"]
    lines = []
    lines.append(f"# P2-03 反復{it}(開発セットのみ)結果 -- 数値のみ、判定なし")
    lines.append("")
    lines.append(f"git rev: `{run_meta['git_rev']}` / seed: {run_meta['seed']} / "
                 f"train末={run_meta['train_end']} / val={run_meta['val_start']}..{run_meta['val_end']} / "
                 f"価格水準補正={run_meta['apply_price_correction']}")
    lines.append("")
    if run_meta["apply_price_correction"]:
        lines.append("**反復1: データ補正(仮説変更ではない)**。1306.T の10:1分割は2026-04-01実効(2015年ではない)。"
                     "primary source: `backtest_data/audit_fetch_1306_split_20260906/README.md`、"
                     "`schema/jpx_etf_daily.json` CORRECTION 2026-09-06。"
                     "CSVの2015-01-05〜2026-03-31区間は実勢価格のちょうど1/10"
                     "(独立系列: 2022-03-04実勢終値1,920.5円 vs CSV 192.05円)。"
                     "呼値帯の判定・呼値コストのbps換算にのみ×10を適用し、r_night/r_dayなどのリターン(比率)は"
                     "CSVの値のまま変更していない。2015-01-05の水準シフトを跨ぐペアは規則2(split_candidate)の"
                     "除外対象のまま(変更なし)。")
        lines.append("")
        comp = extra.get("comparison")
        if comp is not None:
            s = comp["symbol_1306"]
            lines.append("## 反復0 → 反復1 比較(1306.T のみ、保守コストシナリオ)")
            lines.append("")
            lines.append("| | 反復0(補正前) | 反復1(補正後) |")
            lines.append("|---|---|---|")
            lines.append(f"| 平均net保守(bps) | {s['iter0_mean_cons_bps']:.2f} | {s['iter1_mean_cons_bps']:.2f} |")
            lines.append(f"| CI | [{s['iter0_ci_lo']:.2f}, {s['iter0_ci_hi']:.2f}] | "
                         f"[{s['iter1_ci_lo']:.2f}, {s['iter1_ci_hi']:.2f}] |")
            lines.append(f"| 平均コスト(bps、往復) | {s['iter0_mean_cost_bps']:.2f} | {s['iter1_mean_cost_bps']:.2f} |")
            lines.append("")
            lines.append("他3系列(1591.T/2516.T/1321.T)は価格水準補正の対象外。反復0のpairs_<SYM>.csvと"
                         "反復1のpairs_<SYM>.csv(共通列)を突き合わせて確認:")
            lines.append("")
            lines.append("| 系列 | 反復0と一致(diff結果) |")
            lines.append("|---|---|")
            for sym, eq in comp["other_series_unchanged"].items():
                lines.append(f"| {sym} | {eq} |")
            lines.append("")
        else:
            lines.append("(反復0の出力 `backtest_data/phase2_runs/P2-03/iter0_20260906/` が見つからなかったため、"
                         "反復0→反復1の比較は省略)")
            lines.append("")

    lines.append("## 欠陥規則の件数(規則1/2/3/5)")
    lines.append("")
    lines.append("| 系列 | 開発セット行数 | ペア数(生) | 規則1誤プリント行 | 規則1連数 | "
                 "規則1片側info | 規則2分割行 | 規則3null行 | 規則5幽霊行 | 除外ペア数 | "
                 "有効ペア(生) | 有効ペア(除外後) |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rule_rows:
        lines.append(f"| {r['series']} | {r['n_rows_dev']} | {r['n_pairs_total']} | "
                     f"{r['rule1_badprint_rows']} | {r['rule1_badprint_runs']} | {r['rule1_one_sided_info_rows']} | "
                     f"{r['rule2_split_rows']} | {r['rule3_null_rows']} | {r['rule5_ghost_rows']} | "
                     f"{r['n_pairs_excluded']} | {r['n_pairs_valid_raw']} | {r['n_pairs_clean']} |")
    lines.append("")
    lines.append("先頭行・末尾行は規則1の判定対象外(基準値または復帰確認行がないため)。")
    lines.append("")

    lines.append("## 主指標: 除外前後 x 楽観/保守(bps/日、95%CI、ブロック・ブートストラップ 20営業日x2000回)")
    lines.append("")
    lines.append("| 系列 | 除外 | 費用 | n | 平均(bps) | CI下 | CI上 |")
    lines.append("|---|---|---|---|---|---|---|")
    for _, row in indicator_df.iterrows():
        lines.append(f"| {row['series']} | {row['stage']} | {row['cost_scenario']} | {row['n']} | "
                     f"{row['mean_bps']:.2f} | {row['ci_lo']:.2f} | {row['ci_hi']:.2f} |")
    lines.append("")

    lines.append("## 系列別サマリ(除外後のみ): 主指標・Sharpe・最大DD・的中率・夜間-日中差")
    lines.append("")
    lines.append("| 系列 | n | 平均gross(bps) | CI | 平均net保守(bps) | CI | MDE(bps) | 保守平均>MDE | "
                 "平均day(bps) | 夜間-日中平均(bps) | CI | Sharpe(gross,年率) | Sharpe(保守,年率) | "
                 "最大DD gross(bps) | 最大DD保守(bps) | 的中率(gross) |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for _, r in summary_df.iterrows():
        lines.append(
            f"| {r['series']} | {r['n_clean']} | {r['mean_gross_bps']:.2f} | "
            f"[{r['gross_ci_lo']:.2f}, {r['gross_ci_hi']:.2f}] | {r['mean_net_cons_bps']:.2f} | "
            f"[{r['cons_ci_lo']:.2f}, {r['cons_ci_hi']:.2f}] | {r['mde_bps']:.2f} | {r['gate_cons_mean_gt_mde']} | "
            f"{r['mean_day_bps']:.2f} | {r['night_minus_day_mean_bps']:.2f} | "
            f"[{r['night_minus_day_ci_lo']:.2f}, {r['night_minus_day_ci_hi']:.2f}] | "
            f"{r['sharpe_gross_annualized']:.3f} | {r['sharpe_cons_annualized']:.3f} | "
            f"{r['max_dd_gross_bps']:.1f} | {r['max_dd_cons_bps']:.1f} | {r['hit_rate_gross']:.3f} |"
        )
    lines.append("")
    lines.append("「保守平均>MDE」は着手前関門の数値並記(PREREG §指標と分母)であり、採用/棄却の判定ではない。")
    lines.append("")

    lines.append("## 「同様の」の判定に使う3条件の数値(判定はしない、数値のみ)")
    lines.append("")
    lines.append("(a) ゼロより有意に大きいか(楽観CIが正か)は上の主指標表(after_exclusion, optimistic)参照。")
    lines.append("")
    lines.append("(b) 1321(日経225 ETF)の r_night 平均(除外後)との符号一致:")
    lines.append("")
    lines.append("| 系列 | 平均gross r_night(bps) | 1321と符号一致 |")
    lines.append("|---|---|---|")
    for r in extra["sign_rows"]:
        lines.append(f"| {r['series']} | {r['mean_gross_bps']:.2f} | {r['sign_matches_1321']} |")
    lines.append("")
    lines.append("(c) 系列間相関(r_night、除外後、共通日、pairwise)。4系列は独立確認とは数えない(株式因子1つ):")
    lines.append("")
    corr = extra["corr"]
    header = "| | " + " | ".join(corr.columns) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (len(corr.columns) + 1))
    for idx, row in corr.iterrows():
        lines.append(f"| {idx} | " + " | ".join(f"{v:.3f}" for v in row) + " |")
    lines.append("")
    lines.append("1321に対する残差(r_night_etf - r_night_1321、共通日平均・CI):")
    lines.append("")
    lines.append("| 系列 | n(共通日) | 残差平均(bps) | CI下 | CI上 |")
    lines.append("|---|---|---|---|---|")
    for r in extra["residual_rows"]:
        lines.append(f"| {r['series']} | {r['n_common']} | {r['mean_bps']:.2f} | {r['ci_lo']:.2f} | {r['ci_hi']:.2f} |")
    lines.append("")

    lines.append("## train/val split(暦日、除外後)")
    lines.append("")
    lines.append(f"train = 開始..{run_meta['train_end']} / val = {run_meta['val_start']}..{run_meta['val_end']}")
    lines.append("")
    lines.append("| 系列 | split | n | 平均net楽観(bps) | CI | 平均net保守(bps) | CI |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in extra["tv_rows"]:
        lines.append(f"| {r['series']} | {r['split']} | {r['n']} | {r['mean_opt_bps']:.2f} | "
                     f"[{r['opt_ci_lo']:.2f}, {r['opt_ci_hi']:.2f}] | {r['mean_cons_bps']:.2f} | "
                     f"[{r['cons_ci_lo']:.2f}, {r['cons_ci_hi']:.2f}] |")
    lines.append("")

    lines.append("## 対照(反事実)")
    lines.append("")
    lines.append("対照1: 符号シャッフル(1,000回、gross r_night、除外後)。観測平均 vs 帰無95点:")
    lines.append("")
    lines.append("| 系列 | n | 観測平均(bps) | 帰無平均(bps) | 帰無95点(bps) |")
    lines.append("|---|---|---|---|---|")
    for r in extra["c1_rows"]:
        lines.append(f"| {r['series']} | {r['n']} | {r['observed_mean_bps']:.2f} | {r['null_mean_bps']:.2f} | "
                     f"{r['null_p95_bps']:.2f} |")
    lines.append("")
    lines.append("対照2(診断のみ、選択に使わない): 20日実現ボラ三分位ごとの実測平均 vs 全体プールからの"
                 "無作為保有(復元抽出1,000回)null 95%区間:")
    lines.append("")
    lines.append("| 系列 | 三分位 | n | 実測平均(bps) | null平均(bps) | null CI |")
    lines.append("|---|---|---|---|---|---|")
    for r in extra["c2_rows"]:
        lines.append(f"| {r['series']} | {r['tercile']} | {r['n']} | {r['observed_mean_bps']:.2f} | "
                     f"{r['null_mean_bps']:.2f} | [{r['null_ci_lo']:.2f}, {r['null_ci_hi']:.2f}] |")
    lines.append("")
    lines.append("対照3: 符号反転(夜間売り持ち、費用は方向によらず同額発生):")
    lines.append("")
    lines.append("| 系列 | net_short楽観(bps) | CI | net_short保守(bps) | CI |")
    lines.append("|---|---|---|---|---|")
    for r in extra["c3_rows"]:
        lines.append(f"| {r['series']} | {r['net_short_opt_mean_bps']:.2f} | "
                     f"[{r['net_short_opt_ci_lo']:.2f}, {r['net_short_opt_ci_hi']:.2f}] | "
                     f"{r['net_short_cons_mean_bps']:.2f} | "
                     f"[{r['net_short_cons_ci_lo']:.2f}, {r['net_short_cons_ci_hi']:.2f}] |")
    lines.append("")

    lines.append("対照4(診断専用、選択には使わない) -- 個別株4銘柄(同スナップショット、"
                 f"使用ファイル: {', '.join(control4_results.keys())}): "
                 "指数ETFに固有か市場全体かの追加対照。")
    lines.append("")
    lines.append("| 銘柄 | n(clean) | 平均r_night(bps) | CI下 | CI上 |")
    lines.append("|---|---|---|---|---|")
    for sym, res in control4_results.items():
        if "error" in res:
            lines.append(f"| {sym} | エラー: {res['error']} | | | |")
            continue
        clean = res["pairs"].loc[res["pairs"]["clean"]]
        m = clean["r_night_bps"].mean() if len(clean) else float("nan")
        s = clean["r_night_bps"].std(ddof=1) if len(clean) > 1 else float("nan")
        se = s / np.sqrt(len(clean)) if len(clean) else float("nan")
        lines.append(f"| {sym} | {len(clean)} | {m:.2f} | {m - 1.96*se:.2f} | {m + 1.96*se:.2f} |")
    lines.append("")

    lines.append("## 1321 帯またぎ回数")
    lines.append("")
    lines.append(f"1321.T の close が呼値の帯(config/constants.yaml)をまたいだ回数: "
                 f"{extra['band_crossings']} 回(有効行数 {extra['band_n_rows']})。")
    lines.append("")

    lines.append("## 診断(記述のみ、選択に使わない): ボラ三分位・曜日・月・年代")
    lines.append("")
    lines.append("全件は diagnostics.csv 参照。系列ごとの次元別バケット数:")
    lines.append("")
    diag_df = pd.DataFrame(extra["diag_rows"])
    if len(diag_df):
        counts = diag_df.groupby(["series", "dimension"]).size().reset_index(name="n_buckets")
        lines.append("| 系列 | 次元 | バケット数 |")
        lines.append("|---|---|---|")
        for _, r in counts.iterrows():
            lines.append(f"| {r['series']} | {r['dimension']} | {r['n_buckets']} |")
    lines.append("")

    lines.append("## 出力ファイル")
    lines.append("")
    lines.append("pairs_<SYM>.csv, rule_counts.csv, main_indicator.csv, summary_by_series.csv, "
                 "correlation_matrix.csv, residual_vs_1321.csv, sign_agreement.csv, train_val_split.csv, "
                 "diagnostics.csv, controls_sign_shuffle.csv, controls_vol_tercile.csv, "
                 "controls_sign_reversal.csv, controls_individual_stocks.csv, band_crossing_1321.csv, RUN.json")
    lines.append("")
    lines.append("本ファイルは判定(採用/棄却)を含まない。数値と件数のみ。")

    (out_dir / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=str, default=None,
                    help="出力ディレクトリ(既定: backtest_data/phase2_runs/P2-03/iter<N>_20260906/)")
    p.add_argument("--iteration", type=int, default=0, help="反復番号(RUN.json/RESULTS.mdのラベル用)")
    p.add_argument("--apply-price-correction", dest="apply_price_correction", action="store_true", default=False,
                    help="1306.T の価格水準補正(反復1)を適用する。既定は適用しない(反復0と同じ挙動)。")
    return p.parse_args(argv)


if __name__ == "__main__":
    _args = parse_args()
    main(out_dir=_args.out, iteration=_args.iteration, apply_price_correction=_args.apply_price_correction)
