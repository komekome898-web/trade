"""S11 signal-fade study — 事前登録(逐語)

================================================================================
【背景】
メインBOT(xborder_momentum k=30, thr=0.8%, exit_pct=0.05%, stop 0.5%)は第22報で
ペーパー棄却された(30取引 net -0.148%、グロス≒-0.02%)。オーナーの新仮説:
「シグナル方向への成行フローがかなりの確率で発生する。ならばシグナルと**逆側の指値**は
約定しやすく、旧損切り(0.5%逆行)が新利確になり収支が反転する」。これを S11 として
定式化する。**注意すべき既知の壁**(報告で必ず定量的に向き合うこと):
(1) 収支の大半はコストであり符号反転しない(第22報 §2.2)、
(2) 逆張り方向の maker 指値は逆選択の敵側(実測 6.2〜9.3bps、KNOWLEDGE §2)、
(3) 執行逆転はレンジ逆張りで全極性負だった(d, j, k)。
本研究はこれらの壁を「シグナル文脈での実測」で更新するものであり、壁を論拠に測定を
省略してはならない。

【データ】
- bitFlyer 約定テープ: `backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz`
  (列 id, exec_date, price, size, side、982,000行、2026-07-23〜08-23)。
  **exec_date < 2026-08-20T08:22:17Z の行のみ使用**(それ以降は他研究の判定用フレッシュ
  領域。1行も読まない)。
- Binance リーダー:
  `https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1m/BTCUSDT-1m-YYYY-MM-DD.zip`
  を必要日数分 scratchpad にダウンロード(リポジトリに保存しない。使用ファイルと日付範囲を
  報告に明記)。**タイムスタンプはマイクロ秒**。プロキシ環境(CA: /root/.ccr/ca-bundle.crt)。
- シグナル再構成の検証(再現ゲート): 8/20〜8/25 の Binance 1m もダウンロードし、
  再構成したシグナル発火時刻が `logs/bot.jsonl` の30ペーパー取引のエントリ時刻(第22報の表)
  と ±3分で一致することを確認する。**この検証で読んでよいのは発火時刻のみ。判定領域の
  損益は読まない。**

【事前登録 — 逸脱禁止】
- シグナル: xborder_momentum の実装と同一(Binance 1m 終値、k=30 の変化率が ±0.8% 交差で
  発火、|momentum|<0.05% で消滅)。実装から定数を import するか逐語再実装し、再現ゲートで
  検証。
- 戦略(フェード): 発火時、シグナルと**逆側**に maker 指値を発火時点の bitFlyer タッチ価格
  (直近プリント価格で代理)に置く。約定判定は **print単位 traded-through(保守則)**:
  反対側の約定が指値を厳密に突き抜けた時のみ約定。指値寿命 = シグナル存続中のみ
  (消滅で取消)。
- 構成ファミリー(**4セル。追加禁止**): TP ∈ {0.3%, 0.5%}(maker 指値、コスト0)×
  時間切れ ∈ {60分, 240分}(taker 3.96bps)。保護ストップは全セル共通 0.8%(taker 3.96bps)。
  同時建玉1、決済後クールダウン = シグナル消滅まで。
- コスト: maker 建て・maker TP = 0bps。taker 決済 = 3.96bps。
- 分割: 探索区間をさらに時系列 60/40 に分け、前半で観察、後半は一度だけ読んでそのまま報告
  (この全体が「汚染済みデータ上の探索」であり採用判断には使えないことを報告冒頭に明記)。
- この探索の実現可能性境界: **4セル全てで後半40%のネットが負なら、族はフィージビリティで
  棄却**(新鮮データでの判定を事前登録しない)。1セルでも正なら、そのセルを凍結し新鮮データ
  判定(バー: n>=30・ネット>=+0.15%/取引・日クラスタCIが0除外・maxDD<10%)を係属登録する
  提案を書く(登録自体はリードが行う)。

【必須報告】
1. 反転の算術表(グロス反転 vs コスト非反転、taker反転・maker反転の理論ネット)
2. 探索区間の全4セル表(n・ネット%/取引・中央値・勝率・日クラスタ t/CI・maxDD・約定率)
3. 逆選択の反実仮想(約定群 vs 取り逃し群の符号付き前方推移 5/30/240分)
4. アブレーション(TP外す/ストップ外す/時間切れのみ)
5. サニティ(ルックアヘッド0・建玉重複0・epoch変換クロスチェック・seed 20260825・
   再実行決定性・再現ゲート)
6. 注意点・限界。陰性なら陰性のまま書く。「惜しい」と書かない。

【制約】
- スクリプトは `scripts/research_signal_fade.py`。read-only・冪等・seed固定。
  ダウンロード以外のネットワークなし。
================================================================================
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys
import zipfile
from dataclasses import dataclass

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- constants --
SEED = 20260825
EPOCH = pd.Timestamp("1970-01-01", tz="UTC")

TAPE = "backtest_data/executions_FX_BTC_JPY_31d_20260823.csv.gz"
CUTOFF = pd.Timestamp("2026-08-20T08:22:17", tz="UTC")   # exclusive; fresh data beyond

# signal constants — verbatim from src/bot/strategy/xborder_momentum.py +
# config/config.yaml (k / thr_pct / exit_pct).
K = 30
THR = 0.8 / 100.0
EXIT_BAND = 0.05 / 100.0

# execution / cost model — .claude/skills/research-protocol §3
TAKER_BPS = 3.96          # burst-regime one-way taker cost
MAKER_BPS = 0.0
STOP_PCT = 0.8 / 100.0    # protective stop, common to all cells
CELLS = [(tp, hor) for tp in (0.3, 0.5) for hor in (60, 240)]  # (TP %, minutes)

FWD_HORIZONS_MIN = (5, 30, 240)
BOOT_N = 10000


# ------------------------------------------------------------------ loaders --
def load_leader(binance_dir: str, verbose: bool = True) -> pd.DataFrame:
    """Binance BTCUSDT 1m klines from data.binance.vision daily zips."""
    files = sorted(glob.glob(os.path.join(binance_dir, "BTCUSDT-1m-*.zip")))
    if not files:
        raise SystemExit(f"no Binance zips in {binance_dir}")
    frames = []
    for f in files:
        with zipfile.ZipFile(f) as z:
            name = z.namelist()[0]
            frames.append(pd.read_csv(
                io.BytesIO(z.read(name)), header=None,
                names=["open_time", "o", "h", "l", "c", "v", "close_time",
                       "qv", "n", "tbv", "tqv", "ig"]))
    d = pd.concat(frames, ignore_index=True)
    d = d.drop_duplicates("open_time").sort_values("open_time").reset_index(drop=True)
    # microsecond epochs -> UTC timestamps (NO .astype("int64") on datetimes;
    # here the source column is an integer count of microseconds).
    ot_us = d["open_time"].to_numpy(dtype="int64")
    ct_us = d["close_time"].to_numpy(dtype="int64")
    d["open_dt"] = EPOCH + pd.to_timedelta(ot_us, unit="us")
    d["close_dt"] = EPOCH + pd.to_timedelta(ct_us, unit="us")
    if verbose:
        print(f"[epoch-xcheck leader] first open_time={ot_us[0]} us -> "
              f"{d['open_dt'].iloc[0]}  last close_time={ct_us[-1]} us -> "
              f"{d['close_dt'].iloc[-1]}  files={len(files)} rows={len(d)}")
        # round trip back to microseconds
        back = ((d["open_dt"] - EPOCH) / pd.Timedelta("1us")).to_numpy(dtype=float)
        assert np.allclose(back, ot_us), "epoch round-trip failed (leader)"
        print(f"[epoch-xcheck leader] round-trip us OK; median bar spacing="
              f"{np.median(np.diff(ot_us)) / 1e6:.1f}s")
    return d


def load_tape(path: str, cutoff: pd.Timestamp, verbose: bool = True) -> dict:
    df = pd.read_csv(path)
    t = pd.to_datetime(df["exec_date"], utc=True, format="ISO8601")
    # bitFlyer emits a small number of side-less prints (daily settlement
    # batches, 284 rows / 0.03%). They carry no aggressor, so they can neither
    # fill a resting limit nor define a touch: dropped.
    sideless = int(df["side"].isna().sum())
    keep = (t < cutoff).to_numpy() & df["side"].notna().to_numpy()
    df = df.loc[keep].reset_index(drop=True)
    t = t.loc[keep].reset_index(drop=True)
    # datetime64 -> float seconds, EPOCH-division idiom (research-protocol §6)
    ts = ((t - EPOCH) / pd.Timedelta("1s")).to_numpy(dtype=float)
    px = df["price"].to_numpy(dtype=float)
    side = df["side"].to_numpy()
    is_buy = (side == "BUY")
    if verbose:
        print(f"[epoch-xcheck tape] rows kept={len(df)} (cutoff {cutoff.isoformat()}, "
              f"side-less prints dropped={sideless}), "
              f"first={t.iloc[0]} ts={ts[0]:.3f}, last={t.iloc[-1]} ts={ts[-1]:.3f}")
        chk = EPOCH + pd.to_timedelta(ts[:3], unit="s")
        print(f"[epoch-xcheck tape] reverse-check first3={list(chk.astype(str))}")
        assert bool(np.all(np.diff(ts) >= 0)), "tape not monotonic"
        assert set(np.unique(side)) <= {"BUY", "SELL"}
    return {"ts": ts, "px": px, "is_buy": is_buy,
            "t0": t.iloc[0], "t1": t.iloc[-1], "n": len(df)}


# ------------------------------------------------------------------ signals --
def momentum(closes: np.ndarray, k: int) -> np.ndarray:
    mom = np.full(len(closes), np.nan)
    if len(closes) > k:
        mom[k:] = np.log(closes[k:] / closes[:-k])
    return mom


@dataclass
class Episode:
    fire_ts: float       # bar close time (s)
    end_ts: float        # signal-death time (s); limit is cancelled here
    direction: int       # +1 leader-long signal, -1 leader-short signal
    mom_pct: float


def build_episodes(leader: pd.DataFrame) -> list[Episode]:
    """State machine identical to XborderMomentumStrategy + main.py entry logic:
    BUY above +thr, SELL below -thr, CLOSE (flat) when |mom| <= exit_band."""
    closes = leader["c"].to_numpy(dtype=float)
    mom = momentum(closes, K)
    bar_ts = ((leader["close_dt"] - EPOCH) / pd.Timedelta("1s")).to_numpy(dtype=float)
    state = 0
    eps: list[Episode] = []
    for i in range(len(mom)):
        m = mom[i]
        if np.isnan(m):
            continue
        if m > THR:
            want = 1
        elif m < -THR:
            want = -1
        elif abs(m) <= EXIT_BAND:
            want = 0
        else:
            continue                      # HOLD band: state unchanged
        if want == state:
            continue
        if state != 0:                    # close the running episode
            eps[-1].end_ts = bar_ts[i]
        state = want
        if want != 0:
            eps.append(Episode(fire_ts=bar_ts[i], end_ts=np.inf,
                               direction=want, mom_pct=m * 100))
    return eps


# --------------------------------------------------------------- simulation --
def last_price_at(ts: np.ndarray, px: np.ndarray, when: float) -> tuple[int, float]:
    """Index/price of the most recent print at or before `when` (no lookahead)."""
    j = int(np.searchsorted(ts, when, side="right")) - 1
    if j < 0:
        return -1, float("nan")
    return j, float(px[j])


def touch_price(ts, px, is_buy, when: float, fade: int, mode: str) -> tuple[int, float]:
    """`mode="last"` = the pre-registered proxy: the most recent print price.

    `mode="quote"` is a NON-PRE-REGISTERED diagnostic used only in the
    limitations block: a resting SELL limit lives at the ask, best proxied by
    the most recent BUY (aggressor-lifts-offer) print; a resting BUY limit
    lives at the bid, proxied by the most recent SELL print. The pre-registered
    proxy silently places half of the limits on the WRONG side of the spread,
    which inflates the fill rate; this variant measures that inflation.
    """
    j = int(np.searchsorted(ts, when, side="right")) - 1
    if j < 0:
        return -1, float("nan")
    if mode == "last":
        return j, float(px[j])
    want_buy = (fade == -1)          # sell limit -> ask -> last BUY print
    k = j
    while k >= 0 and bool(is_buy[k]) != want_buy:
        k -= 1
    if k < 0:
        return -1, float("nan")
    return j, float(px[k])


def simulate_cell(eps: list[Episode], tape: dict, tp_pct: float, horizon_min: int,
                  use_tp: bool = True, use_stop: bool = True,
                  touch_mode: str = "last") -> dict:
    ts, px, is_buy = tape["ts"], tape["px"], tape["is_buy"]
    t_end_tape = ts[-1]
    placed = 0
    skipped_open_position = 0
    skipped_no_touch = 0
    trades = []
    fills = []          # per-placement record for the adverse-selection block
    busy_until = -np.inf

    for ep in eps:
        if ep.fire_ts < ts[0] or ep.fire_ts > t_end_tape:
            continue
        if ep.fire_ts <= busy_until:
            skipped_open_position += 1
            continue
        fade = -ep.direction                    # +1 = we go long, -1 = we go short
        i0, p0 = touch_price(ts, px, is_buy, ep.fire_ts, fade, touch_mode)
        if i0 < 0 or not np.isfinite(p0):
            skipped_no_touch += 1
            continue
        placed += 1
        # ---- fill search: traded-through, strictly, on prints AFTER the fire bar
        life_end = min(ep.end_ts, t_end_tape)
        hi = int(np.searchsorted(ts, life_end, side="right"))
        lo = i0 + 1
        fill_idx = -1
        if hi > lo:
            if fade == -1:                      # our SELL limit at p0
                cond = is_buy[lo:hi] & (px[lo:hi] > p0)
            else:                               # our BUY limit at p0
                cond = (~is_buy[lo:hi]) & (px[lo:hi] < p0)
            if cond.any():
                fill_idx = lo + int(np.argmax(cond))
        rec = {"fire_ts": ep.fire_ts, "dir": ep.direction, "p0": p0,
               "mom_pct": ep.mom_pct, "filled": fill_idx >= 0,
               "life_s": life_end - ep.fire_ts,
               "last_print_is_buy": bool(is_buy[i0]),
               "limit_is_sell": fade == -1,
               "fill_delay_s": (ts[fill_idx] - ep.fire_ts) if fill_idx >= 0 else np.nan}
        fills.append(rec)
        if fill_idx < 0:
            continue

        # ---- position open at p0 (maker, 0 bps)
        fill_ts = ts[fill_idx]
        # lookahead audit: the limit price is set from a print at-or-before the
        # fire bar close, and the fill can only come from a print strictly after.
        assert ts[i0] <= ep.fire_ts, "lookahead: touch print is after the fire bar"
        assert fill_ts > ep.fire_ts, "lookahead: fill print is not after the fire bar"
        if fade == -1:
            tp_price = p0 * (1 - tp_pct / 100.0)
            stop_price = p0 * (1 + STOP_PCT)
        else:
            tp_price = p0 * (1 + tp_pct / 100.0)
            stop_price = p0 * (1 - STOP_PCT)
        deadline = fill_ts + horizon_min * 60.0

        exit_reason, exit_px, exit_cost, exit_ts = None, None, None, None
        j = fill_idx + 1
        n = len(ts)
        while j < n:
            if ts[j] > deadline:
                exit_reason, exit_px, exit_cost, exit_ts = "time", px[j], TAKER_BPS, ts[j]
                break
            p = px[j]
            if use_stop and ((fade == -1 and p >= stop_price) or
                             (fade == 1 and p <= stop_price)):
                exit_reason, exit_px, exit_cost, exit_ts = "stop", p, TAKER_BPS, ts[j]
                break
            if use_tp:
                # maker TP: traded-through by the opposite aggressor, strictly
                if fade == -1 and (not is_buy[j]) and p < tp_price:
                    exit_reason, exit_px, exit_cost, exit_ts = "tp", tp_price, MAKER_BPS, ts[j]
                    break
                if fade == 1 and is_buy[j] and p > tp_price:
                    exit_reason, exit_px, exit_cost, exit_ts = "tp", tp_price, MAKER_BPS, ts[j]
                    break
            j += 1
        if exit_reason is None:                 # tape truncated at the cutoff
            exit_reason, exit_px, exit_cost, exit_ts = "truncated", px[-1], TAKER_BPS, ts[-1]

        assert exit_ts >= fill_ts, "exit before fill"
        gross_pct = ((exit_px - p0) / p0 * 100.0) * fade
        net_pct = gross_pct - exit_cost / 100.0
        trades.append({"fire_ts": ep.fire_ts, "fill_ts": fill_ts, "exit_ts": exit_ts,
                       "dir": ep.direction, "fade": fade, "p0": p0, "exit_px": exit_px,
                       "reason": exit_reason, "gross_pct": gross_pct,
                       "net_pct": net_pct, "hold_min": (exit_ts - fill_ts) / 60.0,
                       "mom_pct": ep.mom_pct})
        busy_until = exit_ts

    return {"trades": pd.DataFrame(trades), "placements": pd.DataFrame(fills),
            "placed": placed, "skipped_open_position": skipped_open_position,
            "skipped_no_touch": skipped_no_touch}


# ------------------------------------------------------------------ metrics --
def bootstrap_day_ci(df: pd.DataFrame, col: str, seed: int = SEED,
                     n: int = BOOT_N) -> tuple[float, float]:
    if df.empty:
        return (np.nan, np.nan)
    day = pd.to_datetime(df["fire_ts"], unit="s", utc=True).dt.floor("1D")
    groups = [g[col].to_numpy(dtype=float) for _, g in df.groupby(day)]
    if len(groups) < 2:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(groups), size=(n, len(groups)))
    means = np.empty(n)
    for i in range(n):
        means[i] = np.concatenate([groups[k] for k in idx[i]]).mean()
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def day_cluster_t(df: pd.DataFrame, col: str) -> tuple[float, int]:
    if df.empty:
        return (np.nan, 0)
    day = pd.to_datetime(df["fire_ts"], unit="s", utc=True).dt.floor("1D")
    dm = df.groupby(day)[col].mean().to_numpy(dtype=float)
    if len(dm) < 2 or dm.std(ddof=1) == 0:
        return (np.nan, len(dm))
    return (float(dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm)))), len(dm))


def max_drawdown_pct(df: pd.DataFrame, col: str = "net_pct") -> float:
    if df.empty:
        return 0.0
    eq = df.sort_values("fill_ts")[col].cumsum().to_numpy(dtype=float)
    peak = np.maximum.accumulate(np.concatenate([[0.0], eq]))
    dd = peak - np.concatenate([[0.0], eq])
    return float(dd.max())


def summarise(trades: pd.DataFrame, placed: int, label: str) -> dict:
    n = len(trades)
    if n == 0:
        return {"label": label, "n": 0, "placed": placed, "fill_rate": 0.0}
    net = trades["net_pct"]
    lo, hi = bootstrap_day_ci(trades, "net_pct")
    t, nd = day_cluster_t(trades, "net_pct")
    return {
        "label": label, "n": n, "placed": placed,
        "fill_rate": n / placed if placed else np.nan,
        "net_mean": float(net.mean()), "net_median": float(net.median()),
        "gross_mean": float(trades["gross_pct"].mean()),
        "win_rate": float((net > 0).mean()),
        "t": t, "n_days": nd, "ci_lo": lo, "ci_hi": hi,
        "maxdd": max_drawdown_pct(trades),
        "hold_med": float(trades["hold_min"].median()),
        "reasons": trades["reason"].value_counts().to_dict(),
        "total_pct": float(net.sum()),
    }


def fmt_row(s: dict) -> str:
    if s["n"] == 0:
        return f"{s['label']:<28} n=0  (placed={s['placed']})"
    return (f"{s['label']:<28} n={s['n']:>4} fill={s['fill_rate']*100:>5.1f}% "
            f"net={s['net_mean']:+.4f}% med={s['net_median']:+.4f}% "
            f"gross={s['gross_mean']:+.4f}% win={s['win_rate']*100:>5.1f}% "
            f"t={s['t'] if s['t'] == s['t'] else float('nan'):+.2f} "
            f"CI=[{s['ci_lo']:+.4f},{s['ci_hi']:+.4f}] maxDD={s['maxdd']:.2f}% "
            f"hold={s['hold_med']:.0f}m {s['reasons']}")


# ------------------------------------------- adverse-selection counterfactual --
def forward_moves(placements: pd.DataFrame, tape: dict) -> pd.DataFrame:
    ts, px = tape["ts"], tape["px"]
    out = placements.copy()
    for h in FWD_HORIZONS_MIN:
        vals = []
        for _, r in placements.iterrows():
            when = r["fire_ts"] + h * 60.0
            if when > ts[-1]:
                vals.append(np.nan)
                continue
            _, p = last_price_at(ts, px, when)
            fade = -r["dir"]
            vals.append((p - r["p0"]) / r["p0"] * 1e4 * fade)
        out[f"fwd_{h}m_bps"] = vals
    return out


# --------------------------------------------------------------------- gate --
PAPER_ENTRIES = [
    # (UTC entry timestamp, side) — the 30 paper trades of report 22.
    # Only ENTRY TIMES are read from the log; no P&L.
    ("2026-08-20T13:37:07", "SELL"), ("2026-08-20T14:08:02", "BUY"),
    ("2026-08-20T15:28:02", "BUY"), ("2026-08-20T23:28:01", "BUY"),
    ("2026-08-21T01:18:03", "BUY"), ("2026-08-21T02:18:03", "SELL"),
    ("2026-08-21T03:01:01", "SELL"), ("2026-08-21T07:16:01", "BUY"),
    ("2026-08-21T08:20:05", "BUY"), ("2026-08-21T09:46:02", "BUY"),
    ("2026-08-21T11:33:03", "SELL"), ("2026-08-21T13:05:05", "BUY"),
    ("2026-08-21T13:51:03", "BUY"), ("2026-08-21T14:20:03", "SELL"),
    ("2026-08-21T14:50:00", "BUY"), ("2026-08-21T16:09:00", "SELL"),
    ("2026-08-21T18:50:03", "SELL"), ("2026-08-21T21:28:01", "BUY"),
    ("2026-08-21T22:10:03", "BUY"), ("2026-08-22T05:10:06", "SELL"),
    ("2026-08-23T05:15:07", "SELL"), ("2026-08-23T14:43:03", "SELL"),
    ("2026-08-23T21:30:01", "BUY"), ("2026-08-24T11:36:19", "BUY"),
    ("2026-08-24T12:43:01", "BUY"), ("2026-08-24T13:41:04", "SELL"),
    ("2026-08-24T14:13:01", "BUY"), ("2026-08-24T16:27:01", "BUY"),
    ("2026-08-24T16:54:03", "SELL"), ("2026-08-25T00:46:03", "BUY"),
    ("2026-08-25T02:18:05", "BUY"),
]


def reproduction_gate(leader: pd.DataFrame, eps: list[Episode],
                      tol_min: float = 3.0) -> None:
    closes = leader["c"].to_numpy(dtype=float)
    mom = momentum(closes, K) * 100
    bar_ts = ((leader["close_dt"] - EPOCH) / pd.Timedelta("1s")).to_numpy(dtype=float)
    have_until = bar_ts[-1]
    fire = np.array([e.fire_ts for e in eps])
    fdir = np.array([e.direction for e in eps])
    ok = miss = skip = 0
    print("\n[reproduction gate] paper entry time -> nearest reconstructed fire")
    for tstr, side in PAPER_ENTRIES:
        t = (pd.Timestamp(tstr, tz="UTC") - EPOCH) / pd.Timedelta("1s")
        if t > have_until:
            skip += 1
            print(f"  {tstr} {side:<4}  SKIP (leader archive ends "
                  f"{pd.Timestamp(have_until, unit='s', tz='UTC')})")
            continue
        want = 1 if side == "BUY" else -1
        same = fire[fdir == want]
        # signal-state check: |mom| beyond thr with the right sign at that minute
        j = int(np.searchsorted(bar_ts, t, side="right")) - 1
        m_at = mom[j] if j >= 0 else np.nan
        if len(same) == 0:
            d = np.inf
        else:
            d = float(np.min(np.abs(same - t)) / 60.0)
        state_ok = (want == 1 and m_at > THR * 100) or (want == -1 and m_at < -THR * 100)
        if d <= tol_min:
            ok += 1
            tag = "OK"
        else:
            miss += 1
            tag = "MISS"
        print(f"  {tstr} {side:<4}  d={d:>7.1f} min  mom_at_entry={m_at:+.3f}% "
              f"signal_active={state_ok}  {tag}")
    tot = ok + miss
    print(f"[reproduction gate] matched {ok}/{tot} within +-{tol_min:.0f} min "
          f"({ok/tot*100:.1f}%), skipped {skip} (no leader archive)")


# --------------------------------------------------------------------- main --
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--binance-dir", required=True)
    ap.add_argument("--tape", default=TAPE)
    args = ap.parse_args()

    np.random.seed(SEED)
    print(f"S11 signal-fade study — seed={SEED}")
    print(f"signal: k={K} thr={THR*100:.2f}% exit_band={EXIT_BAND*100:.2f}%")
    print(f"costs: maker={MAKER_BPS}bps taker={TAKER_BPS}bps stop={STOP_PCT*100:.1f}%")

    leader = load_leader(args.binance_dir)
    tape = load_tape(args.tape, CUTOFF)
    eps_all = build_episodes(leader)
    print(f"\nepisodes reconstructed over the whole leader archive: {len(eps_all)}")

    reproduction_gate(leader, eps_all)

    # ---- exploration region only: fires inside the tape, strictly before cutoff
    cut_s = (CUTOFF - EPOCH) / pd.Timedelta("1s")
    eps = [e for e in eps_all if tape["ts"][0] <= e.fire_ts < cut_s]
    print(f"\nexploration episodes (tape window {tape['t0']} .. {tape['t1']}): {len(eps)}")
    dirs = pd.Series([e.direction for e in eps]).value_counts().to_dict()
    print(f"  direction split (leader-long=+1 / leader-short=-1): {dirs}")

    # 60/40 chronological split by episode order (research-protocol §2)
    n_first = int(round(len(eps) * 0.6))
    split_ts = eps[n_first].fire_ts if n_first < len(eps) else cut_s
    print(f"  60/40 split boundary: episode #{n_first}, "
          f"{pd.Timestamp(split_ts, unit='s', tz='UTC')}")

    results = {}
    print("\n=== 4 cells (pre-registered family; no additions) ===")
    for tp, hor in CELLS:
        sim = simulate_cell(eps, tape, tp, hor)
        tr = sim["trades"]
        # position-overlap sanity
        if not tr.empty:
            s = tr.sort_values("fill_ts")
            assert bool((s["fill_ts"].to_numpy()[1:] >=
                         s["exit_ts"].to_numpy()[:-1]).all()), "position overlap!"
        label = f"TP{tp}%/T{hor}m"
        full = summarise(tr, sim["placed"], label + " FULL")
        a = tr[tr["fire_ts"] < split_ts]
        b = tr[tr["fire_ts"] >= split_ts]
        pa = int((sim["placements"]["fire_ts"] < split_ts).sum())
        pb = int((sim["placements"]["fire_ts"] >= split_ts).sum())
        s_a = summarise(a, pa, label + " first60")
        s_b = summarise(b, pb, label + " last40")
        results[label] = {"full": full, "first60": s_a, "last40": s_b,
                          "skips": sim["skipped_open_position"], "sim": sim}
        print(fmt_row(full))
        print(fmt_row(s_a))
        print(fmt_row(s_b))
        print(f"    (skipped because a position was open: {sim['skipped_open_position']})")

    # ---- feasibility boundary
    neg = [lab for lab, r in results.items()
           if r["last40"]["n"] == 0 or r["last40"]["net_mean"] < 0]
    print(f"\n[feasibility] cells with last-40% net < 0 (or empty): "
          f"{len(neg)}/4 -> {neg}")
    print("[feasibility] VERDICT: "
          + ("REJECT family (all 4 cells negative in the last 40%)"
             if len(neg) == 4 else
             "at least one cell positive -> propose a frozen fresh-data gate"))

    # ---- adverse-selection counterfactual (use the TP0.5/240 placement set;
    #      placements are identical across cells except for overlap skips)
    print("\n=== adverse selection counterfactual (fade direction = positive) ===")
    base = results["TP0.5%/T240m"]["sim"]["placements"]
    fw = forward_moves(base, tape)
    for grp, name in ((fw[fw["filled"]], "FILLED"), (fw[~fw["filled"]], "MISSED")):
        row = [f"{name:<7} n={len(grp):>4}"]
        for h in FWD_HORIZONS_MIN:
            c = grp[f"fwd_{h}m_bps"].dropna()
            row.append(f"{h}m: mean={c.mean():+7.2f} med={c.median():+7.2f} (n={len(c)})")
        print("  " + "  ".join(row))
    print("  --- difference (MISSED - FILLED) = adverse selection ---")
    for h in FWD_HORIZONS_MIN:
        a = fw[fw["filled"]][f"fwd_{h}m_bps"].dropna()
        b = fw[~fw["filled"]][f"fwd_{h}m_bps"].dropna()
        if len(a) and len(b):
            print(f"  {h:>4}m: MISSED {b.mean():+7.2f} - FILLED {a.mean():+7.2f} = "
                  f"{b.mean()-a.mean():+7.2f} bps")

    # ---- ablations
    print("\n=== ablations (full exploration region) ===")
    abl = []
    for tp, hor in CELLS:
        sim = simulate_cell(eps, tape, tp, hor, use_tp=True, use_stop=False)
        abl.append(summarise(sim["trades"], sim["placed"], f"noSTOP TP{tp}/T{hor}m"))
    for hor in (60, 240):
        sim = simulate_cell(eps, tape, 0.0, hor, use_tp=False, use_stop=True)
        abl.append(summarise(sim["trades"], sim["placed"], f"noTP  stop+T{hor}m"))
        sim = simulate_cell(eps, tape, 0.0, hor, use_tp=False, use_stop=False)
        abl.append(summarise(sim["trades"], sim["placed"], f"timeonly  T{hor}m"))
    for s in abl:
        print(fmt_row(s))

    # ---- diagnostics
    print("\n=== diagnostics ===")
    print(f"  placements (TP0.5/240 cell): {len(base)}, filled {int(base['filled'].sum())}")
    print(f"  median signal life (min): {(base['life_s']/60).median():.1f}")
    print(f"  |mom| at fire: mean {base['mom_pct'].abs().mean():.3f}% "
          f"median {base['mom_pct'].abs().median():.3f}%")
    print(f"  fill delay (s): median {base['fill_delay_s'].median():.1f} "
          f"p90 {base['fill_delay_s'].quantile(0.9):.1f}")
    wrong = ((base["limit_is_sell"] & ~base["last_print_is_buy"]) |
             (~base["limit_is_sell"] & base["last_print_is_buy"]))
    print(f"  touch-proxy audit: {int(wrong.sum())}/{len(base)} placements sit on the "
          f"WRONG side of the spread (last print was our own aggressor side) "
          f"-> effectively marketable, fill guaranteed by construction")

    # ---- NON-PRE-REGISTERED limitations block (reported as a limitation only,
    #      never as a candidate configuration).
    print("\n=== [NON-PRE-REGISTERED] touch-proxy sensitivity: limit at the quote "
          "on our own side ===")
    for tp, hor in CELLS:
        sim = simulate_cell(eps, tape, tp, hor, touch_mode="quote")
        print(fmt_row(summarise(sim["trades"], sim["placed"],
                                f"[diag] quote TP{tp}/T{hor}m")))
    simq = simulate_cell(eps, tape, 0.5, 240, touch_mode="quote")
    fwq = forward_moves(simq["placements"], tape)
    print("  adverse selection under the quote placement (fade direction positive):")
    for grp, name in ((fwq[fwq["filled"]], "FILLED"), (fwq[~fwq["filled"]], "MISSED")):
        row = [f"  {name:<7} n={len(grp):>4}"]
        for h in FWD_HORIZONS_MIN:
            c = grp[f"fwd_{h}m_bps"].dropna()
            row.append(f"{h}m: mean={c.mean():+7.2f} med={c.median():+7.2f} (n={len(c)})")
        print("  " + "  ".join(row))
    for h in FWD_HORIZONS_MIN:
        a = fwq[fwq["filled"]][f"fwd_{h}m_bps"].dropna()
        b = fwq[~fwq["filled"]][f"fwd_{h}m_bps"].dropna()
        if len(a) and len(b):
            print(f"    {h:>4}m: MISSED {b.mean():+7.2f} - FILLED {a.mean():+7.2f} = "
                  f"{b.mean()-a.mean():+7.2f} bps")

    # ---- per-trade dump of the pre-registered TP0.5/T240 cell
    print("\n=== per-trade (TP0.5%/T240m, pre-registered proxy) ===")
    tr = results["TP0.5%/T240m"]["sim"]["trades"].copy()
    tr["fire"] = pd.to_datetime(tr["fire_ts"], unit="s", utc=True).dt.strftime(
        "%m-%d %H:%M")
    print(tr[["fire", "dir", "fade", "p0", "exit_px", "reason", "gross_pct",
              "net_pct", "hold_min"]].to_string(index=False,
                                                float_format=lambda v: f"{v:.4f}"))

    payload = {lab: {k: v for k, v in r.items() if k != "sim"}
               for lab, r in results.items()}
    blob = json.dumps(payload, indent=1, default=str, sort_keys=True)
    import hashlib
    print(f"\n[determinism] results digest sha256={hashlib.sha256(blob.encode()).hexdigest()}")
    print(blob)


if __name__ == "__main__":
    main()
