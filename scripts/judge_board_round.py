#!/usr/bin/env python3
"""# PREREG — 板データ深掘りラウンド(Round 17: BI-deep / VR5 / TP / GMO-cal)

**凍結日: 2026-09-04。以降の変更は「事前登録の破棄」。**
本文書は `data/ws` 板記録(2026-08-20〜、15日・1.0GB・68ファイル)に対する計算を**一切行う前**に凍結した。
KNOWLEDGE.md §10 深掘り台帳 (C)「板データ成熟ラウンドに深掘り予定」の4件を一括で一発判定する。

## 0. 構成(オーナーPCで重い再構成、リード側で判定)

- 板記録は git に載らない。オーナーPCで `scripts/run_board_round.py` を1回実行し、
  **5秒ビンの派生系列** `data/board_round/series_5s.csv.gz`(≈8MB)と `coverage.json` を生成、
  `share_logs.bat` で共有。判定は `scripts/judge_board_round.py` がその系列だけを読んで行う
  (決定性・再現可能。系列は `backtest_data/board_round_<date>/` に恒久保存)。
- 派生系列の列(5秒ビン末尾の状態 + ビン内集計、UTC):
  `ts, mid, spread_bps, best_bid_size, best_ask_size, bid_depth_5bps, ask_depth_5bps,
   imb_top, imb_5bps, n_board_updates, n_trades, vol_buy, vol_sell, n_large, vol_large, max_trade_size`
  (`imb = (bid−ask)/(bid+ask)`、`large` = 1約定 ≥ 0.1 BTC、depth は mid±5bps 内の数量合計)。
  60秒超の記録ギャップはビンを欠測にし、ギャップをまたぐ前方リターンは計算しない。
- コスト: taker 往復 **5.8bps**(確立済み床)。全セルはこのネットで判定。

## 1. BI-deep — 板不均衡 taker の深掘り(6セル)

浅い棄却(g・aa: 0.08〜1.35bps)を、深さ5bps 不均衡 × 時計窓で最後に一度だけ再測する。
- シグナル: `imb_5bps` の十分位(判定窓全体で算出)。**第10分位 = ロング、第1分位 = ショート**。
- 前方リターン: `ln(mid_{t+h}/mid_t)`、h ∈ {30s, 120s, 300s}。標本は h ごとに**非重複**(h 刻み)。
- 条件: {全時間, 時計窓 12:30–15:00 UTC}。
- 判定: 6セルのいずれかで **ネット(粗平均 − 5.8bps)> 0 かつ t ≥ 2.0** → 机上通過(次段 = 新鮮期間の
  再測 PREREG)。いずれも満たさない → **板不均衡 taker を機構水準で最終閉鎖**(効果は実在するがコスト床の
  下、深さ・窓の条件付けでも届かない)。
- 必須報告: 十分位ごとの前方平均(単調性)、top-of-book 版の同表(g との連続性)、粗 bps。

## 2. VR5 — 5秒スケール vr の静穏モード逆張り(4セル)

matilda 固有の 5秒足/30秒窓を初めて原スケールで測る。
- `vr = sd(5秒リターン, 直近30秒) / sd(5秒リターン, 直近300秒)`。**静穏 = vr の下位三分位、騒乱 = 上位三分位**
  (三分位は判定窓全体で算出)。
- トリガ: 直近30秒の mid 変位 |Δ| ≥ 5bps。シグナル = **逆張り**(−sign Δ)。保有 h ∈ {30s, 60s}、taker 往復 5.8bps。
  標本は非重複(トリガ後 h 秒は再トリガしない)。
- セル: 2レジーム × 2保有。判定: いずれかで ネット > 0 かつ t ≥ 2.0 → 机上通過。なければ **5秒 vr を最終閉鎖**
  (1分足でのリフト 1.00 が原スケールでも再現 = 情報なし)。
- 必須報告: 静穏/騒乱それぞれの粗平均・n、レジーム無条件の同セル、次60秒 |変位| の vr 三分位別平均(規模予測の確認)。

## 3. TP — テープスケール嵐予兆(6特徴量・2段階)

分足特徴量は全滅(h)。秒スケールの前兆が存在するかを、**スクリーニング → 新鮮期間で一度だけ確認**の2段で判定する。
- イベント: **バースト発生** = 直近60秒の |mid 変位| ≥ 20bps(S12 と同定義)が **30分以上**の非発生の後に初めて成立した秒 t0。
  時計窓に限定しない(全日)。
- 対照: イベントごとに 3 点、同じ時刻帯(UTC 時)から、±30分にバーストのない時刻を無作為抽出(seed 20260904)。
- 特徴量(前兆窓 **[t0−180s, t0−60s]**。定義区間 [t0−60s, t0] とは重ねない):
  1. 約定件数加速 = 窓内件数 ÷(直前30分の120秒あたり平均件数)
  2. 大口比率 = vol_large ÷ 総出来高
  3. taker 不均衡 = |vol_buy − vol_sell| ÷ (vol_buy + vol_sell)
  4. 平均スプレッド(bps)
  5. 板の薄さ = 窓内 (bid_depth_5bps + ask_depth_5bps) の平均 ÷ 直前30分の中央値
  6. 板更新率 = n_board_updates の窓内合計
- 判定(スクリーニング): 特徴量ごとに AUC(イベント vs 対照)と 2,000回ブートストラップ 95%CI。
  **AUC ≥ 0.65 かつ CI下限 > 0.55** の特徴量が1つ以上 → その特徴量だけを **次の ≥15 記録日**(本系列より後)で
  同じバーで一度だけ確認(第2段)。第2段も通過 → 嵐予兆モジュール設計へ(採用ではない)。
  スクリーニングで 0 特徴 → **テープスケール嵐予兆を機構水準で閉鎖**。
- 必須報告: n_events・n_controls、各特徴量の AUC/CI、イベント時刻表、n<30 なら「判定不能・データ待ち」と明記して
  閉鎖にはしない。

## 4. GMO-cal — 第2ベニュー校正(判定はベニュー記録 14 板日到達後)

- データ: `data/venues/quotes_*.csv.gz`(gmo BTC_JPY、ポーリング)と `trades_gmo_*`、2026-08-27〜。**14 板日
  (2026-09-10 以降の共有)で一度だけ**判定。それまでは「未到達」を表示するのみ。
- 計算: `research_board_calibration.py` と同じ 30秒エポックで f(擬似クオート約定率)・capture・逆選択(5秒)・
  脚間ドリフトを GMO で算出。ポーリング記録の粗さによる f の偏りを必ず併記。
- 判定: GMO でも **ドリフト < 0 かつ |ドリフト| > capture×2** → maker 線閉鎖は市場普遍(監視モード継続)。
  **capture×2 − |ドリフト| ≥ +1.0bps** → GMO maker の新 PREREG を起票(採用ではない)。

## 5. 多重性と読み方

- セル数: BI 6 + VR 4 + TP 6 特徴 + GMO 1 = 17。すべて事前指名、閾値・窓・分位はすべて本文書で固定。
  実装時の自由度は 0(十分位/三分位の境界はデータから機械算出)。
- 汚染: 本系列(08-20〜09-04)は S12 判定の件数集計と第21ラウンド校正(tape 08-20〜27)で約定側だけ閲覧済み。
  板の深さ・5秒粒度は未閲覧。TP の第2段は完全に未来のデータ。
- 通過セルが出ても**採用ではない**。次段は各項の記述どおり(新鮮期間の再測 PREREG)。

署名: リード。実装: `scripts/run_board_round.py`(オーナーPC、再構成のみ、統計を計算しない)、
`scripts/judge_board_round.py`(本文書逐語 docstring、seed 20260904、一度だけ実行しそのまま報告)。

---
IMPLEMENTATION NOTES (not part of the PREREG text above; literal readings
picked where the document is silent, per instructions):

* BI-deep / VR5 non-overlap ("h ごとに非重複" / "トリガ後h秒は再トリガしない"):
  implemented on the absolute 5s-bin grid — a sample at bin b is kept for
  horizon h only if no earlier KEPT sample for that same h lies within
  h seconds of it (a forward walk over time, per h independently).
* BI-deep deciles / VR5 terciles are computed once over the whole judged
  series (all rows with a finite value), never per condition/cut.
* TP feature windows with fewer than half their expected bins present
  (a >60s reconstruction gap inside the window) are treated as
  undersampled and EXCLUDED from that event/control's feature set, since
  a summed count over an admittedly-incomplete window is not the quantity
  the feature intends to measure.
* TP AUC bootstrap resamples at the EVENT level (each event's 1 positive +
  its matched controls move together), consistent with the cluster
  bootstrap convention already used in scripts/research_board_calibration.py.
* GMO-cal "脚間ドリフト" (leg-to-leg drift): computed only within 30s
  epochs where BOTH a synthetic bid-leg and ask-leg fill are detected —
  the signed mid move from the first leg's fill to the second leg's fill,
  positive when favorable to the position taken by the first leg. This
  section cannot be exercised against real data yet (day bar not reached)
  and is documented here for when it can be.
"""
from __future__ import annotations

import argparse
import bisect
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

from bot.monitoring.gates import shared_or_local  # noqa: E402
import research_board_calibration as rbc  # noqa: E402  (reused: epoch_seconds)

SEED = 20260904
TAKER_COST_BPS = 5.8
BIN_SEC = 5.0

# -- section 1: BI-deep --------------------------------------------------
BI_HORIZONS = (30, 120, 300)          # seconds
CLOCK_LO, CLOCK_HI = 12.5, 15.0       # UTC hours, 12:30-15:00
T_BAR = 2.0

# -- section 2: VR5 -------------------------------------------------------
VR_HOLDS = (30, 60)
VR_TRIGGER_BPS = 5.0
VR30_BINS = int(30 / BIN_SEC)
VR300_BINS = int(300 / BIN_SEC)

# -- section 3: TP ---------------------------------------------------------
BURST_BPS = 20.0
BURST_WINDOW_SEC = 60.0
QUIET_SEC = 1800.0
FEATURE_WINDOW = (180, 60)            # [t0-180s, t0-60s)
BASELINE_SEC = 1800.0                 # 30 min immediately before the window
N_CONTROLS_PER_EVENT = 3
AUC_BAR = 0.65
AUC_CI_LOWER_BAR = 0.55
N_EVENTS_MIN = 30
FEATURE_NAMES = [
    "accel", "large_ratio", "taker_imbalance", "avg_spread_bps",
    "book_thinness", "board_update_rate",
]

# -- section 4: GMO-cal ------------------------------------------------------
GMO_DAY_BAR = 14


# ==========================================================================
# reporting
# ==========================================================================
class Reporter:
    def __init__(self) -> None:
        self.buf = io.StringIO()

    def line(self, text: str = "") -> None:
        print(text)
        self.buf.write(text + "\n")

    def header(self, title: str) -> None:
        self.line("")
        self.line("=" * 78)
        self.line(title)
        self.line("=" * 78)

    def sub(self, title: str) -> None:
        self.line("")
        self.line("--- " + title + " " + "-" * max(0, 72 - len(title)))


# ==========================================================================
# series loading
# ==========================================================================
def find_series_path(root: Path) -> Path:
    return shared_or_local(root, "data/board_round/series_5s.csv.gz",
                           shared_name="board_round_series_5s.csv.gz")


def find_coverage_path(root: Path) -> Path:
    return shared_or_local(root, "data/board_round/coverage.json",
                           shared_name="board_round_coverage.json")


def load_series(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.sort_values("ts").reset_index(drop=True)
    # immune to the datetime64 unit trap (astype('int64') silently changes
    # meaning between us/ns resolution depending on pandas' string parsing)
    epoch = ((df["ts"] - pd.Timestamp("1970-01-01", tz="UTC"))
             / pd.Timedelta("1s")).round().astype(np.int64)
    df["bin_idx"] = (epoch // int(BIN_SEC)).astype(np.int64)
    df["hour"] = df["ts"].dt.hour + df["ts"].dt.minute / 60.0
    return df


# ==========================================================================
# shared helpers
# ==========================================================================
def decile_labels(x: np.ndarray) -> np.ndarray:
    """1..10 decile label per finite value; -1 where x is NaN. Edges are the
    10/20/.../90th percentiles of the finite values, computed once."""
    out = np.full(x.shape, -1, dtype=np.int64)
    ok = np.isfinite(x)
    if ok.sum() < 10:
        return out
    edges = np.percentile(x[ok], np.arange(10, 100, 10))
    out[ok] = np.digitize(x[ok], edges) + 1
    return out


def tercile_labels(x: np.ndarray) -> np.ndarray:
    """1/2/3 tercile label; -1 where x is NaN."""
    out = np.full(x.shape, -1, dtype=np.int64)
    ok = np.isfinite(x)
    if ok.sum() < 3:
        return out
    edges = np.percentile(x[ok], [100 / 3, 200 / 3])
    out[ok] = np.digitize(x[ok], edges) + 1
    return out


def forward_value(values: np.ndarray, bin_idx: np.ndarray, offset_bins: int) -> np.ndarray:
    """values[i] looked up at bin_idx[i] + offset_bins; NaN if that bin is
    not present in the series (missing bin / off the end)."""
    s = pd.Series(values, index=bin_idx)
    target = bin_idx + offset_bins
    return s.reindex(target).to_numpy()


def nonoverlap_mask(bin_idx: np.ndarray, candidate: np.ndarray, stride_bins: int) -> np.ndarray:
    """Greedy forward walk: among bins where `candidate` is True (in time
    order), keep one only if it is >= stride_bins after the last KEPT bin."""
    kept = np.zeros(bin_idx.shape, dtype=bool)
    last = -(10**18)
    idx_sorted = np.argsort(bin_idx, kind="stable")
    for i in idx_sorted:
        if not candidate[i]:
            continue
        b = bin_idx[i]
        if b - last >= stride_bins:
            kept[i] = True
            last = b
    return kept


def gross_and_t(x: np.ndarray, cost_bps: float) -> dict:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = x.size
    if n == 0:
        return {"n": 0, "gross": float("nan"), "net": float("nan"), "t": float("nan")}
    gross = float(x.mean())
    net = gross - cost_bps
    if n > 1:
        sd = float(x.std(ddof=1))
        t = (gross - cost_bps) / (sd / np.sqrt(n)) if sd > 0 else float("nan")
    else:
        t = float("nan")
    return {"n": n, "gross": gross, "net": net, "t": t}


def verdict_str(cell: dict) -> str:
    if cell["n"] == 0 or not np.isfinite(cell["t"]):
        return "n/a"
    return "PASS" if (cell["net"] > 0 and cell["t"] >= T_BAR) else "fail"


# ==========================================================================
# section 1: BI-deep
# ==========================================================================
def compute_bi(df: pd.DataFrame, horizons=BI_HORIZONS, cost_bps=TAKER_COST_BPS) -> dict:
    bin_idx = df["bin_idx"].to_numpy()
    mid = df["mid"].to_numpy(float)
    clock_mask = ((df["hour"].to_numpy() >= CLOCK_LO)
                  & (df["hour"].to_numpy() < CLOCK_HI))
    all_mask = np.ones(len(df), dtype=bool)
    conditions = [("all", all_mask), ("clock12:30-15:00", clock_mask)]

    signals = {
        "imb_5bps": decile_labels(df["imb_5bps"].to_numpy(float)),
        "imb_top": decile_labels(df["imb_top"].to_numpy(float)),
    }

    decile_tables: dict[str, dict[int, dict[int, float]]] = {}
    for sig_name, deciles in signals.items():
        decile_tables[sig_name] = {}
        for h in horizons:
            stride = max(1, int(round(h / BIN_SEC)))
            fwd_mid = forward_value(mid, bin_idx, stride)
            fwd_bps = np.log(fwd_mid / mid) * 1e4
            nonoverlap = nonoverlap_mask(bin_idx, all_mask, stride)
            per_decile = {}
            for k in range(1, 11):
                sel = nonoverlap & (deciles == k) & np.isfinite(fwd_bps)
                per_decile[k] = float(np.mean(fwd_bps[sel])) if sel.any() else float("nan")
            decile_tables[sig_name][h] = per_decile

    deciles5 = signals["imb_5bps"]
    cells = []
    for cond_name, cmask in conditions:
        for h in horizons:
            stride = max(1, int(round(h / BIN_SEC)))
            fwd_mid = forward_value(mid, bin_idx, stride)
            fwd_bps = np.log(fwd_mid / mid) * 1e4
            nonoverlap = nonoverlap_mask(bin_idx, cmask, stride)
            long_sel = nonoverlap & (deciles5 == 10) & np.isfinite(fwd_bps)
            short_sel = nonoverlap & (deciles5 == 1) & np.isfinite(fwd_bps)
            pnl = np.concatenate([fwd_bps[long_sel], -fwd_bps[short_sel]])
            stat = gross_and_t(pnl, cost_bps)
            cells.append({"condition": cond_name, "h": h, **stat,
                          "n_long": int(long_sel.sum()), "n_short": int(short_sel.sum())})

    passed = any(c["n"] > 0 and c["net"] > 0 and c["t"] >= T_BAR for c in cells)
    return {"cells": cells, "decile_tables": decile_tables, "passed": passed}


def print_bi(rep: Reporter, res: dict) -> None:
    rep.header("1. BI-DEEP -- board imbalance taker (depth 5bps x clock window)")
    rep.sub("decile-ordered forward mean, bps (monotonicity check) -- imb_5bps")
    for h, table in res["decile_tables"]["imb_5bps"].items():
        row = f"  h={h:>3}s  " + "  ".join(f"d{k}:{table[k]:+6.2f}" for k in range(1, 11))
        rep.line(row)
    rep.sub("decile-ordered forward mean, bps -- top-of-book (imb_top, continuity with g)")
    for h, table in res["decile_tables"]["imb_top"].items():
        row = f"  h={h:>3}s  " + "  ".join(f"d{k}:{table[k]:+6.2f}" for k in range(1, 11))
        rep.line(row)
    rep.sub("6 cells: decile10=long / decile1=short, net = gross - 5.8bps")
    rep.line(f"{'condition':<24}{'h':>6}{'n':>8}{'gross(bps)':>12}{'net(bps)':>10}{'t':>7}  verdict")
    for c in res["cells"]:
        rep.line(f"{c['condition']:<24}{c['h']:>5}s{c['n']:>8}{c['gross']:>12.3f}"
                 f"{c['net']:>10.3f}{c['t']:>7.2f}  {verdict_str(c)}")
    rep.line("")
    if res["passed"]:
        rep.line("VERDICT: at least one BI-deep cell passes (net>0, t>=2.0) -> "
                 "desk pass (next: fresh-period re-measurement PREREG).")
    else:
        rep.line("VERDICT: no BI-deep cell passes -> board imbalance taker CLOSED "
                 "at mechanism level.")


# ==========================================================================
# section 2: VR5
# ==========================================================================
def compute_vr(df: pd.DataFrame, holds=VR_HOLDS, cost_bps=TAKER_COST_BPS) -> dict:
    bin_idx = df["bin_idx"].to_numpy()
    mid = df["mid"].to_numpy(float)
    n = len(df)

    # contiguous-segment id: a new segment starts whenever the bin index does
    # not advance by exactly 1 from the previous row.
    diffs = np.diff(bin_idx, prepend=bin_idx[0] - 2)
    seg_id = np.cumsum(diffs != 1)

    ret = np.full(n, np.nan)
    ret[1:] = np.where(seg_id[1:] == seg_id[:-1],
                       np.log(mid[1:] / mid[:-1]), np.nan)

    ret_s = pd.Series(ret)
    seg_s = pd.Series(seg_id)
    grouped = ret_s.groupby(seg_s)
    sd30 = grouped.rolling(VR30_BINS, min_periods=VR30_BINS).std(ddof=1).reset_index(level=0, drop=True)
    sd300 = grouped.rolling(VR300_BINS, min_periods=VR300_BINS).std(ddof=1).reset_index(level=0, drop=True)
    sd30 = sd30.to_numpy()
    sd300 = sd300.to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        vr = np.where(sd300 > 0, sd30 / sd300, np.nan)

    vr_tercile = tercile_labels(vr)

    mid_prev30 = forward_value(mid, bin_idx, -VR30_BINS)
    # guard against crossing a segment boundary: only valid if every bin in
    # between is actually contiguous (same trick as ret[]).
    same_seg_30 = np.zeros(n, dtype=bool)
    seg_prev = pd.Series(seg_id, index=bin_idx).reindex(bin_idx - VR30_BINS).to_numpy()
    same_seg_30 = (seg_prev == seg_id)
    delta_bps = np.where(same_seg_30, np.log(mid / mid_prev30) * 1e4, np.nan)

    trigger = np.isfinite(delta_bps) & (np.abs(delta_bps) >= VR_TRIGGER_BPS)
    sign_contrarian = -np.sign(delta_bps)

    quiet_mask = vr_tercile == 1
    turbulent_mask = vr_tercile == 3

    cells = []
    unconditional = []
    for h in holds:
        stride = max(1, int(round(h / BIN_SEC)))
        fwd_mid = forward_value(mid, bin_idx, stride)
        fwd_bps = np.log(fwd_mid / mid) * 1e4
        pnl_all = sign_contrarian * fwd_bps
        for regime_name, rmask in (("quiet(vr t1)", quiet_mask), ("turbulent(vr t3)", turbulent_mask)):
            sel = trigger & rmask
            kept = nonoverlap_mask(bin_idx, sel, stride)
            stat = gross_and_t(pnl_all[kept], cost_bps)
            cells.append({"regime": regime_name, "h": h, **stat})
        kept_u = nonoverlap_mask(bin_idx, trigger, stride)
        stat_u = gross_and_t(pnl_all[kept_u], cost_bps)
        unconditional.append({"regime": "unconditional", "h": h, **stat_u})

    # scale-prediction diagnostic: next-60s |displacement| by vr tercile
    fwd60_mid = forward_value(mid, bin_idx, int(round(60 / BIN_SEC)))
    next60_abs_bps = np.abs(np.log(fwd60_mid / mid)) * 1e4
    scale_by_tercile = {}
    for t in (1, 2, 3):
        sel = (vr_tercile == t) & np.isfinite(next60_abs_bps)
        scale_by_tercile[t] = {
            "n": int(sel.sum()),
            "mean_abs_next60_bps": float(np.mean(next60_abs_bps[sel])) if sel.any() else float("nan"),
        }

    passed = any(c["n"] > 0 and c["net"] > 0 and c["t"] >= T_BAR for c in cells)
    return {"cells": cells, "unconditional": unconditional,
            "scale_by_tercile": scale_by_tercile, "passed": passed,
            "n_triggers": int(trigger.sum())}


def print_vr(rep: Reporter, res: dict) -> None:
    rep.header("2. VR5 -- 5-second vr, quiet-mode contrarian")
    rep.line(f"total triggers (|30s displacement| >= {VR_TRIGGER_BPS} bps): {res['n_triggers']:,}")
    rep.sub("4 cells: quiet/turbulent regime x hold, net = gross - 5.8bps")
    rep.line(f"{'regime':<18}{'h':>6}{'n':>8}{'gross(bps)':>12}{'net(bps)':>10}{'t':>7}  verdict")
    for c in res["cells"]:
        rep.line(f"{c['regime']:<18}{c['h']:>5}s{c['n']:>8}{c['gross']:>12.3f}"
                 f"{c['net']:>10.3f}{c['t']:>7.2f}  {verdict_str(c)}")
    rep.sub("regime-unconditional, same cells")
    for c in res["unconditional"]:
        rep.line(f"{c['regime']:<18}{c['h']:>5}s{c['n']:>8}{c['gross']:>12.3f}"
                 f"{c['net']:>10.3f}{c['t']:>7.2f}  {verdict_str(c)}")
    rep.sub("scale prediction: mean |displacement over next 60s| by vr tercile")
    for t, s in res["scale_by_tercile"].items():
        rep.line(f"  tercile {t}  n={s['n']:>8,}  mean|next60s|={s['mean_abs_next60_bps']:.3f} bps")
    rep.line("")
    if res["passed"]:
        rep.line("VERDICT: at least one VR5 cell passes (net>0, t>=2.0) -> "
                 "desk pass (next: fresh-period re-measurement PREREG).")
    else:
        rep.line("VERDICT: no VR5 cell passes -> 5-second vr CLOSED "
                 "at mechanism level (1m-bar 1.00 lift reproduces at native scale).")


# ==========================================================================
# section 3: TP
# ==========================================================================
def detect_burst_and_events(df: pd.DataFrame, burst_bps=BURST_BPS,
                            burst_window_sec=BURST_WINDOW_SEC,
                            quiet_sec=QUIET_SEC):
    """Return (burst boolean array, sorted array of event t0 bin indices)."""
    bin_idx = df["bin_idx"].to_numpy()
    mid = df["mid"].to_numpy(float)
    win_bins = max(1, int(round(burst_window_sec / BIN_SEC)))
    prev_mid = forward_value(mid, bin_idx, -win_bins)
    with np.errstate(invalid="ignore", divide="ignore"):
        disp_bps = np.abs(np.log(mid / prev_mid)) * 1e4
    burst = np.isfinite(disp_bps) & (disp_bps >= burst_bps)

    quiet_bins = int(round(quiet_sec / BIN_SEC))
    order = np.argsort(bin_idx, kind="stable")
    events = []
    last_true_bin = -(10**18)
    for i in order:
        if not burst[i]:
            continue
        b = bin_idx[i]
        if (b - last_true_bin) >= quiet_bins:
            events.append(b)
        last_true_bin = b
    return burst, np.array(sorted(events), dtype=np.int64)


def _window_features(idx_df: pd.DataFrame, t0_bin: int) -> np.ndarray | None:
    """6 features for the pre-event window [t0-180s, t0-60s), or None if the
    window (or its 30-minute baseline) is too sparsely reconstructed."""
    w_start_s, w_end_s = FEATURE_WINDOW
    w_lo = t0_bin - int(round(w_start_s / BIN_SEC))
    w_hi = t0_bin - int(round(w_end_s / BIN_SEC))          # exclusive
    b_lo = w_lo - int(round(BASELINE_SEC / BIN_SEC))
    b_hi = w_lo                                              # exclusive

    win = idx_df.reindex(range(w_lo, w_hi))
    base = idx_df.reindex(range(b_lo, b_hi))
    if win["mid"].notna().mean() < 0.5 or base["mid"].notna().mean() < 0.5:
        return None

    n_win_bins = w_hi - w_lo
    n_base_bins = b_hi - b_lo
    n_base_buckets = max(1, n_base_bins * BIN_SEC / 120.0)

    win_trades = float(win["n_trades"].sum(skipna=True))
    base_trades = float(base["n_trades"].sum(skipna=True))
    accel = (win_trades / (base_trades / n_base_buckets)
            if base_trades > 0 else float("nan"))

    win_vol = float((win["vol_buy"].sum(skipna=True) + win["vol_sell"].sum(skipna=True)))
    win_large = float(win["vol_large"].sum(skipna=True))
    large_ratio = win_large / win_vol if win_vol > 0 else float("nan")

    vbuy = float(win["vol_buy"].sum(skipna=True))
    vsell = float(win["vol_sell"].sum(skipna=True))
    taker_imb = abs(vbuy - vsell) / (vbuy + vsell) if (vbuy + vsell) > 0 else float("nan")

    avg_spread = float(win["spread_bps"].mean(skipna=True))

    depth_sum_win = (win["bid_depth_5bps"] + win["ask_depth_5bps"])
    depth_sum_base = (base["bid_depth_5bps"] + base["ask_depth_5bps"])
    base_med = float(depth_sum_base.median(skipna=True))
    thinness = (float(depth_sum_win.mean(skipna=True)) / base_med
               if base_med and base_med > 0 else float("nan"))

    board_rate = float(win["n_board_updates"].sum(skipna=True))

    return np.array([accel, large_ratio, taker_imb, avg_spread, thinness, board_rate], float)


def sample_controls(df: pd.DataFrame, burst: np.ndarray, events: np.ndarray,
                    rng: np.random.Generator, n_per_event=N_CONTROLS_PER_EVENT,
                    radius_sec=1800.0):
    bin_idx = df["bin_idx"].to_numpy()
    hour = df["hour"].to_numpy()
    hour_bucket = np.floor(hour).astype(int)
    radius_bins = int(round(radius_sec / BIN_SEC))
    burst_bins_sorted = np.sort(bin_idx[burst])

    def near_burst(b: int) -> bool:
        i = bisect.bisect_left(burst_bins_sorted, b)
        for j in (i - 1, i):
            if 0 <= j < len(burst_bins_sorted) and abs(int(burst_bins_sorted[j]) - b) <= radius_bins:
                return True
        return False

    pool_by_hour: dict[int, list[int]] = {}
    for b, hb in zip(bin_idx, hour_bucket):
        if near_burst(int(b)):
            continue
        pool_by_hour.setdefault(int(hb), []).append(int(b))

    controls_by_event = []
    t0_hours = pd.Series(bin_idx).map(dict(zip(bin_idx, hour_bucket)))
    idx_pos = {int(b): i for i, b in enumerate(bin_idx)}
    for t0 in events:
        pos = idx_pos.get(int(t0))
        hb = int(hour_bucket[pos]) if pos is not None else 0
        pool = pool_by_hour.get(hb, [])
        if len(pool) == 0:
            controls_by_event.append(np.array([], dtype=np.int64))
            continue
        k = min(n_per_event, len(pool))
        picked = rng.choice(np.array(pool, dtype=np.int64), size=k, replace=(len(pool) < n_per_event))
        controls_by_event.append(np.asarray(picked, dtype=np.int64))
    return controls_by_event


def auc_score(pos, neg) -> float:
    pos = np.asarray(pos, float)
    neg = np.asarray(neg, float)
    pos = pos[np.isfinite(pos)]
    neg = neg[np.isfinite(neg)]
    n1, n2 = len(pos), len(neg)
    if n1 == 0 or n2 == 0:
        return float("nan")
    all_vals = np.concatenate([pos, neg])
    ranks = pd.Series(all_vals).rank(method="average").to_numpy()
    rank_pos_sum = ranks[:n1].sum()
    return float((rank_pos_sum - n1 * (n1 + 1) / 2.0) / (n1 * n2))


def bootstrap_auc_ci(pos_by_event: list, neg_by_event: list, seed: int, n_boot=2000):
    n_events = len(pos_by_event)
    if n_events == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    aucs = np.full(n_boot, np.nan)
    for b in range(n_boot):
        pick = rng.integers(0, n_events, n_events)
        pos = [pos_by_event[i] for i in pick if np.isfinite(pos_by_event[i])]
        neg = []
        for i in pick:
            neg.extend(v for v in neg_by_event[i] if np.isfinite(v))
        aucs[b] = auc_score(pos, neg)
    aucs = aucs[np.isfinite(aucs)]
    if aucs.size == 0:
        return (float("nan"), float("nan"))
    return (float(np.percentile(aucs, 2.5)), float(np.percentile(aucs, 97.5)))


def compute_tp(df: pd.DataFrame, seed=SEED) -> dict:
    burst, events = detect_burst_and_events(df)
    idx_df = df.set_index("bin_idx")[
        ["mid", "n_trades", "vol_buy", "vol_sell", "n_large", "vol_large",
         "spread_bps", "bid_depth_5bps", "ask_depth_5bps", "n_board_updates"]
    ]
    ctrl_rng = np.random.default_rng(seed)
    controls_by_event = sample_controls(df, burst, events, ctrl_rng)

    event_feats = [_window_features(idx_df, int(t0)) for t0 in events]
    control_feats = [[_window_features(idx_df, int(c)) for c in ctrls]
                     for ctrls in controls_by_event]

    n_events = len(events)
    n_controls = sum(len(c) for c in control_feats)

    features_result = []
    for f_i, f_name in enumerate(FEATURE_NAMES):
        pos_by_event = [ (ev[f_i] if ev is not None else float("nan")) for ev in event_feats ]
        neg_by_event = [ [ (cf[f_i] if cf is not None else float("nan")) for cf in ctrls ]
                        for ctrls in control_feats ]
        pos_all = [v for v in pos_by_event if np.isfinite(v)]
        neg_all = [v for group in neg_by_event for v in group if np.isfinite(v)]
        point_auc = auc_score(pos_all, neg_all)
        ci_lo, ci_hi = bootstrap_auc_ci(pos_by_event, neg_by_event, seed)
        screened = (np.isfinite(point_auc) and point_auc >= AUC_BAR
                   and np.isfinite(ci_lo) and ci_lo > AUC_CI_LOWER_BAR)
        features_result.append({
            "feature": f_name, "n_pos": len(pos_all), "n_neg": len(neg_all),
            "auc": point_auc, "ci_lo": ci_lo, "ci_hi": ci_hi, "screened": screened,
        })

    insufficient = n_events < N_EVENTS_MIN
    any_screened = any(f["screened"] for f in features_result)
    return {
        "n_events": n_events, "n_controls": n_controls,
        "event_ts": [str(pd.Timestamp(int(t0) * BIN_SEC, unit="s", tz="UTC")) for t0 in events],
        "features": features_result,
        "insufficient": insufficient,
        "any_screened": any_screened,
    }


def print_tp(rep: Reporter, res: dict) -> None:
    rep.header("3. TP -- tape-scale storm precursor (screening stage)")
    rep.line(f"n_events={res['n_events']}  n_controls={res['n_controls']}")
    if res["insufficient"]:
        rep.line(f"n_events < {N_EVENTS_MIN} -> 判定不能・データ待ち "
                 "(not a closure; wait for more recorded days).")
    rep.sub("event clock table")
    for t in res["event_ts"]:
        rep.line(f"  {t}")
    rep.sub("per-feature AUC (event vs matched control) + 2,000-draw bootstrap 95% CI")
    rep.line(f"{'feature':<20}{'n_pos':>7}{'n_neg':>7}{'AUC':>8}{'CI_lo':>8}{'CI_hi':>8}  screened")
    for f in res["features"]:
        rep.line(f"{f['feature']:<20}{f['n_pos']:>7}{f['n_neg']:>7}"
                 f"{f['auc']:>8.3f}{f['ci_lo']:>8.3f}{f['ci_hi']:>8.3f}  "
                 f"{'PASS' if f['screened'] else 'fail'}")
    rep.line("")
    if res["insufficient"]:
        rep.line("VERDICT: insufficient events -- no closure, no stage-2 promotion.")
    elif res["any_screened"]:
        passed_names = [f["feature"] for f in res["features"] if f["screened"]]
        rep.line(f"VERDICT: screening PASS for {passed_names} -> confirm on the "
                 ">=15 FUTURE recorded days (stage 2), not run here (data does "
                 "not exist yet). Passing stage 2 -> storm-precursor module "
                 "design (not adoption).")
    else:
        rep.line("VERDICT: 0 features screened -> tape-scale storm precursor "
                 "CLOSED at mechanism level.")


# ==========================================================================
# section 4: GMO-cal
# ==========================================================================
def venues_dir(root: Path) -> Path:
    shared = root / "paper_logs" / "venues"
    local = root / "data" / "venues"
    if shared.is_dir() and any(shared.glob("quotes_*.csv.gz")):
        return shared
    return local


def gmo_day_count(root: Path) -> tuple[int, Path]:
    vdir = venues_dir(root)
    days = set()
    for p in sorted(vdir.glob("quotes_*.csv.gz")):
        stem = p.name[len("quotes_"):-len(".csv.gz")]
        if len(stem) == 8 and stem.isdigit():
            days.add(stem)
    return len(days), vdir


def compute_gmo(root: Path) -> dict:
    day_count, vdir = gmo_day_count(root)
    if day_count < GMO_DAY_BAR:
        return {"reached": False, "day_count": day_count, "dir": str(vdir)}

    quotes_paths = sorted(vdir.glob("quotes_*.csv.gz"))
    trades_paths = sorted(vdir.glob("trades_gmo_btc_jpy_*.csv.gz"))
    q = pd.concat([pd.read_csv(p) for p in quotes_paths], ignore_index=True)
    q = q[(q["venue"] == "gmo") & (q["pair"] == "BTC_JPY")].copy()
    q = q.dropna(subset=["bid", "ask"]).sort_values("ts_utc")
    tks = rbc.epoch_seconds(q["ts_utc"])
    bid = q["bid"].to_numpy(float)
    ask = q["ask"].to_numpy(float)

    tr = pd.concat([pd.read_csv(p) for p in trades_paths], ignore_index=True) if trades_paths else pd.DataFrame(columns=["ts_utc", "price", "size", "side"])
    tex = rbc.epoch_seconds(tr["ts_utc"]) if len(tr) else np.array([])
    px = tr["price"].to_numpy(float) if len(tr) else np.array([])
    buy = (tr["side"].to_numpy() == "BUY") if len(tr) else np.array([], dtype=bool)

    if len(tks) == 0:
        return {"reached": True, "day_count": day_count, "dir": str(vdir), "n_epochs": 0}

    EPOCH = 30.0
    LIFE = 30.0
    k0 = int(np.floor(tks[0] / EPOCH))
    k1 = int(np.floor(tks[-1] / EPOCH))
    grid = (np.arange(k0, k1 + 1)) * EPOCH
    ip = np.searchsorted(tks, grid, "right") - 1
    ok = ip >= 0
    grid, ip = grid[ok], ip[ok]
    gbid, gask = bid[ip], ask[ip]
    gmid = 0.5 * (gbid + gask)

    n_bid_fill = n_ask_fill = 0
    caps, advs, drifts = [], [], []
    for i in range(len(grid)):
        t0 = grid[i]
        lo = np.searchsorted(tex, t0, "right")
        hi = np.searchsorted(tex, t0 + LIFE, "right")
        if hi <= lo:
            continue
        p_s, b_s = px[lo:hi], buy[lo:hi]
        bid_fill_t = ask_fill_t = None
        m_bid = (~b_s) & (p_s <= gbid[i])
        m_ask = b_s & (p_s >= gask[i])
        if m_bid.any():
            n_bid_fill += 1
            k = int(np.argmax(m_bid))
            bid_fill_t = tex[lo:hi][k]
            m_before = np.searchsorted(tks, bid_fill_t, "left") - 1
            m_after = np.searchsorted(tks, bid_fill_t + 5.0, "right") - 1
            if m_before >= 0 and m_after >= 0:
                m0 = 0.5 * (bid[m_before] + ask[m_before])
                m5 = 0.5 * (bid[m_after] + ask[m_after])
                caps.append((m0 - gbid[i]) / m0 * 1e4)
                advs.append((m5 - m0) / m0 * 1e4)
        if m_ask.any():
            n_ask_fill += 1
            k = int(np.argmax(m_ask))
            ask_fill_t = tex[lo:hi][k]
            m_before = np.searchsorted(tks, ask_fill_t, "left") - 1
            m_after = np.searchsorted(tks, ask_fill_t + 5.0, "right") - 1
            if m_before >= 0 and m_after >= 0:
                m0 = 0.5 * (bid[m_before] + ask[m_before])
                m5 = 0.5 * (bid[m_after] + ask[m_after])
                caps.append((gask[i] - m0) / m0 * 1e4)
                advs.append(-(m5 - m0) / m0 * 1e4)
        if bid_fill_t is not None and ask_fill_t is not None:
            m_a = np.searchsorted(tks, min(bid_fill_t, ask_fill_t), "left") - 1
            m_b = np.searchsorted(tks, max(bid_fill_t, ask_fill_t), "left") - 1
            if m_a >= 0 and m_b >= 0:
                m_first = 0.5 * (bid[m_a] + ask[m_a])
                m_second = 0.5 * (bid[m_b] + ask[m_b])
                sign = 1.0 if bid_fill_t <= ask_fill_t else -1.0
                drifts.append(sign * (m_second - m_first) / m_first * 1e4)

    n_epochs = len(grid)
    f_bid = n_bid_fill / n_epochs if n_epochs else float("nan")
    f_ask = n_ask_fill / n_epochs if n_epochs else float("nan")
    capture = float(np.mean(caps)) if caps else float("nan")
    adverse5 = float(np.mean(advs)) if advs else float("nan")
    drift = float(np.mean(drifts)) if drifts else float("nan")

    closed = np.isfinite(drift) and drift < 0 and abs(drift) > capture * 2
    new_prereg = (np.isfinite(drift) and (capture * 2 - abs(drift)) >= 1.0)

    return {
        "reached": True, "day_count": day_count, "dir": str(vdir),
        "n_epochs": n_epochs, "f_bid": f_bid, "f_ask": f_ask,
        "capture": capture, "adverse5": adverse5, "drift": drift,
        "n_drift_pairs": len(drifts), "closed": closed, "new_prereg": new_prereg,
    }


def print_gmo(rep: Reporter, res: dict) -> None:
    rep.header("4. GMO-CAL -- second-venue calibration")
    if not res["reached"]:
        rep.line(f"未到達 (day_count={res['day_count']} of {GMO_DAY_BAR} required, "
                 f"venues dir: {res['dir']})")
        return
    rep.line(f"day_count={res['day_count']}  venues dir: {res['dir']}")
    if res.get("n_epochs", 0) == 0:
        rep.line("no usable 30s epochs -- cannot calibrate yet.")
        return
    rep.line(f"n_epochs={res['n_epochs']:,}  f_bid={res['f_bid']*100:.1f}%  "
             f"f_ask={res['f_ask']*100:.1f}%  "
             "(f is biased by polling coarseness -- reported, not corrected)")
    rep.line(f"capture={res['capture']:+.3f} bps  adverse(5s)={res['adverse5']:+.3f} bps  "
             f"drift={res['drift']:+.3f} bps (n_pairs={res['n_drift_pairs']})")
    rep.line("")
    if res["closed"]:
        rep.line("VERDICT: drift<0 and |drift|>capture*2 on GMO too -> "
                 "maker-line closure looks market-universal (monitoring mode continues).")
    elif res["new_prereg"]:
        rep.line("VERDICT: capture*2 - |drift| >= +1.0bps -> file a new GMO-maker "
                 "PREREG (not adoption).")
    else:
        rep.line("VERDICT: neither GMO decision bar met -- report numbers only.")


# ==========================================================================
# main
# ==========================================================================
def main() -> int:
    ap = argparse.ArgumentParser(description="Judge docs/PREREG_board_round.md, one shot.")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--report", default=None, help="also write the report text to this path")
    args = ap.parse_args()
    root = Path(args.root)

    rep = Reporter()
    rep.line(f"seed={SEED}  taker round-trip cost={TAKER_COST_BPS} bps  root={root}")

    series_path = find_series_path(root)
    if not series_path.exists():
        rep.line(f"no series at {series_path} -- run scripts/run_board_round.py first.")
        _finish(rep, args)
        return 1
    df = load_series(series_path)
    rep.line(f"series: {series_path}  rows={len(df):,}  "
             f"{df['ts'].iloc[0]} .. {df['ts'].iloc[-1]}")

    cov_path = find_coverage_path(root)
    if cov_path.exists():
        cov = json.loads(cov_path.read_text())
        rep.line(f"coverage: {cov.get('missing_bins', '?')} missing of "
                 f"{cov.get('total_bins', '?')} bins, "
                 f"{len(cov.get('gaps_over_60s', []))} gaps > 60s")

    print_bi(rep, compute_bi(df))
    print_vr(rep, compute_vr(df))
    print_tp(rep, compute_tp(df))
    print_gmo(rep, compute_gmo(root))

    _finish(rep, args)
    return 0


def _finish(rep: Reporter, args) -> None:
    if args.report:
        Path(args.report).write_text(rep.buf.getvalue())


if __name__ == "__main__":
    raise SystemExit(main())
