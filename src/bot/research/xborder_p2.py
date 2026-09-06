"""P2-08 research engine — pure functions, implemented BLIND from
`docs/PHASE2/P2-08/PREREG.md` (第 4 稿) only. Nothing here reads, imports or
imitates the live strategy code; the PREREG's wording is the sole source.

Conventions (read these before calling anything)
------------------------------------------------
* Every timestamp is a tz-aware UTC ``pd.Timestamp``; a bar timestamp is the
  START of its 1-minute bucket.
* ``thr`` / ``exit_`` / ``stop`` are in PERCENT of price (PREREG 探索面の表の
  単位: thr 0.8 = 0.8%), ``funding_pct_per_settlement`` likewise (0.02 = 0.02%);
  ``cost_one_way_bps`` is in bps. The momentum ``m`` itself is a plain
  fraction (close ratio − 1). Ledger money columns are in bps of the entry
  price.
* ``bf`` may contain "empty" minutes (all four OHLC NaN — PREREG 既知欠陥 (1))
  AND may skip rows entirely (時刻の飛び). ``simulate`` first re-indexes the
  frame onto the complete 1-minute grid, so both are the same thing from
  then on: a minute with no valid bar.
* A "big gap" (5 分超の欠損, 既知欠陥 (3)/(7)) is two consecutive VALID bars
  more than ``max_gap_min`` minutes apart — the convention of
  backtest_data/.../gaps_gt5min.txt (06:40 → 06:46 is a 6-minute gap, i.e.
  5 empty minutes). Blank runs shorter than that ("5 分未満の空分") are the
  only ones a fill is deferred across.

Rules implemented (PREREG「信号と執行の定義」/「データ」)
-----------------------------------------------------
* m(t) = close(t)/close(t−k) − 1 on the Binance series, looked up BY TIME
  (t − k minutes), NaN if that minute is absent.
* Entry: m(t) > +thr → long, m(t) < −thr → short, filled at the OPEN of the
  next 1-minute bar plus one-way cost. One position at a time.
* Exit: |m(t)| < exit → market exit at the next bar's open. Protective stop:
  a move of ``stop``% against the entry price, detected on the bar's low
  (long) / high (short), filled at the NEXT bar's open — a gap through the
  level is taken as-is on the adverse side. When a bar triggers both, the
  stop label wins (same fill price either way).
* Deferral (既知欠陥 (1)): if the bar a fill lands on is empty, the fill
  moves to the next valid bar's open; the number of empty bars skipped is
  counted in ``n_deferred`` (entry + exit; also split out).
* Priority rule (第 4 稿「優先順位」, only with ``apply_masks=True``): an ENTRY
  signal raised during a big gap's blank run, or within ``max_gap_min``
  minutes before the run starts (t_a − 4 min .. t_a for max_gap_min = 5), is
  DISCARDED, never deferred. Exit signals are never discarded — the trade
  is instead excluded by the rule below, so they cannot leak into the
  aggregate either way.
* Gap exclusion: a trade whose holding period [entry_ts, exit_ts] contains a
  big gap (entry_ts <= t_a and t_b <= exit_ts) carries ``straddles_gap=True``;
  ``excluded_gap = straddles_gap AND apply_masks``. Excluded trades stay in
  the ledger and are dropped by ``daily_pnl``.
* Misprint mask (既知欠陥 (5), only with ``apply_masks=True``): a valid bar
  whose close moves more than 30% from the previous valid close AND whose
  next valid close is back within 5% of that previous close is blanked
  (OHLC → NaN) before anything else runs. Nothing else is filtered: the
  >10% single-minute moves stay as genuine moves.
* Funding: ``funding_pct_per_settlement`` of the entry notional for every
  settlement instant s (UTC 05:00/13:00/21:00) with entry_ts < s <= exit_ts,
  applied uniformly over the whole history (PREREG: 現行制度を全期間に一様適用).
  A fill happens at (or just after) the bar's start, so an entry filled at
  05:00 is NOT charged for the 05:00 settlement while an exit filled at
  05:00 IS (the position was still open at that instant).
* Regime column (既知欠陥 (4)): ``regime`` = "lightning_fx" for entries before
  2024-03-28 00:00 UTC, "crypto_cfd" from then on (all of the dev set is
  lightning_fx).
* End of data while holding: closed at the last valid bar's CLOSE with
  ``exit_reason="end"`` (no next open exists).
* ``apply_masks=False`` switches OFF the misprint blanking, the discard rule
  and the exclusion flag (fills are then deferred across blanks of any
  length), so the main indicator can be reported before and after the masks.

The returned ledger carries counts in ``ledger.attrs`` (entry-signal bars,
discarded signals, misprint rows, big gaps, ...) for the RESULTS tables.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MINUTE = pd.Timedelta(minutes=1)
BPS = 1e4
SIZE_BTC_DEFAULT = 0.01
FUNDING_TIMES_UTC_DEFAULT = (5, 13, 21)
MISPRINT_JUMP_DEFAULT = 0.30
MISPRINT_REVERT_TOL_DEFAULT = 0.05
CRYPTO_CFD_START = pd.Timestamp("2024-03-28 00:00:00", tz="UTC")
REGIME_LIGHTNING_FX = "lightning_fx"
REGIME_CRYPTO_CFD = "crypto_cfd"

LEDGER_COLUMNS = [
    "entry_ts", "exit_ts", "side", "entry_px", "exit_px",
    "gross_bps", "cost_bps", "funding_bps", "net_bps", "exit_reason",
    "n_deferred", "n_settlements", "excluded_gap", "regime",
    # extras (not in the PREREG column list; descriptive only)
    "straddles_gap", "entry_signal_ts", "exit_signal_ts",
    "n_deferred_entry", "n_deferred_exit", "hold_min", "pnl_jpy",
]
OHLC = ["open", "high", "low", "close"]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _utc_index(index) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(index)
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    else:
        idx = idx.tz_convert("UTC")
    if not idx.is_monotonic_increasing:
        raise ValueError("index must be sorted ascending")
    if idx.has_duplicates:
        raise ValueError("index must not contain duplicate timestamps")
    return idx


def _valid_mask(bf: pd.DataFrame) -> np.ndarray:
    arr = bf[OHLC].to_numpy(dtype=float)
    return ~np.isnan(arr).any(axis=1)


def to_minute_grid(bf: pd.DataFrame) -> pd.DataFrame:
    """``bf`` re-indexed onto every minute from its first to its last
    timestamp (absent rows become all-NaN rows). Only the OHLC columns are
    kept."""
    idx = _utc_index(bf.index)
    out = bf[OHLC].astype(float).copy()
    out.index = idx
    grid = pd.date_range(idx[0], idx[-1], freq="min")
    return out.reindex(grid)


def regime_of(ts) -> str:
    t = pd.Timestamp(ts)
    t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    return REGIME_CRYPTO_CFD if t >= CRYPTO_CFD_START else REGIME_LIGHTNING_FX


def settlement_instants(start, end, funding_times_utc=FUNDING_TIMES_UTC_DEFAULT
                        ) -> pd.DatetimeIndex:
    """Every UTC settlement instant in [start − 1 day, end + 1 day], sorted."""
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)
    start = start.tz_localize("UTC") if start.tzinfo is None else start.tz_convert("UTC")
    end = end.tz_localize("UTC") if end.tzinfo is None else end.tz_convert("UTC")
    days = pd.date_range(start.normalize() - pd.Timedelta(days=1),
                         end.normalize() + pd.Timedelta(days=1), freq="D")
    out = days[:0]
    for hour in funding_times_utc:
        out = out.union(days + pd.Timedelta(hours=float(hour)))
    return out


def count_settlements(entry_ts, exit_ts, funding_times_utc=FUNDING_TIMES_UTC_DEFAULT) -> int:
    """Number of settlement instants s with entry_ts < s <= exit_ts."""
    s = settlement_instants(entry_ts, exit_ts, funding_times_utc)
    e0 = pd.Timestamp(entry_ts)
    e1 = pd.Timestamp(exit_ts)
    return int(((s > e0) & (s <= e1)).sum())


def big_gaps(bf: pd.DataFrame, max_gap_min: int = 5) -> pd.DataFrame:
    """Gaps between consecutive VALID bars longer than ``max_gap_min`` minutes.

    Columns: ``t_a`` (last valid bar before the gap), ``t_b`` (first valid bar
    after), ``gap_min`` (= t_b − t_a in minutes, the gaps_gt5min.txt
    convention), ``missing_min`` (= gap_min − 1, minutes with no valid bar)
    and ``kind`` ("empty_rows" when every missing minute is present as a NaN
    row, "time_jump" when at least one row is absent from ``bf``).
    """
    idx = _utc_index(bf.index)
    valid = _valid_mask(bf)
    tv = idx[valid]
    cols = ["t_a", "t_b", "gap_min", "missing_min", "kind"]
    if len(tv) < 2:
        return pd.DataFrame(columns=cols)
    diff_min = (tv[1:] - tv[:-1]) / MINUTE
    hit = np.flatnonzero(diff_min > max_gap_min)
    t_a = tv[hit]
    t_b = tv[hit + 1]
    pos_a = idx.searchsorted(t_a, side="right")
    pos_b = idx.searchsorted(t_b, side="left")
    rows_between = pos_b - pos_a
    missing = np.rint(diff_min[hit] - 1).astype(int)
    kind = np.where(rows_between == missing, "empty_rows", "time_jump")
    return pd.DataFrame({"t_a": t_a, "t_b": t_b, "gap_min": diff_min[hit].astype(float),
                         "missing_min": missing, "kind": kind}, columns=cols)


def misprint_mask(bf: pd.DataFrame, jump: float = MISPRINT_JUMP_DEFAULT,
                  revert_tol: float = MISPRINT_REVERT_TOL_DEFAULT) -> pd.Series:
    """既知欠陥 (5) の 2 段判定: a valid bar is a misprint when its close is more
    than ``jump`` away from the previous valid close AND the next valid close
    is back within ``revert_tol`` of that previous close. Boolean Series on
    ``bf.index`` (False on empty rows and on the first/last valid bar)."""
    idx = _utc_index(bf.index)
    valid = _valid_mask(bf)
    out = np.zeros(len(idx), dtype=bool)
    pv = np.flatnonzero(valid)
    if len(pv) >= 3:
        cv = bf["close"].to_numpy(dtype=float)[pv]
        prev, cur, nxt = cv[:-2], cv[1:-1], cv[2:]
        hit = (np.abs(cur / prev - 1.0) > jump) & (np.abs(nxt / prev - 1.0) <= revert_tol)
        out[pv[1:-1][hit]] = True
    return pd.Series(out, index=idx, name="misprint")


# ---------------------------------------------------------------------------
# signal
# ---------------------------------------------------------------------------

def momentum_signal(binance_close: pd.Series, k: int) -> pd.Series:
    """m(t) = close(t) / close(t − k minutes) − 1, looked up BY TIME.

    ``binance_close`` is indexed by UTC bar-start timestamps (need not be a
    complete grid). The k-minutes-earlier close is fetched by timestamp, not
    by row position, so a missing minute yields NaN rather than a silent
    shift. Returns a Series on the same index.
    """
    k = int(k)
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    idx = _utc_index(binance_close.index)
    close = pd.Series(binance_close.to_numpy(dtype=float), index=idx)
    prev = close.reindex(idx - k * MINUTE).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        m = close.to_numpy() / prev - 1.0
    return pd.Series(m, index=idx, name=f"m_k{k}")


# ---------------------------------------------------------------------------
# execution simulator
# ---------------------------------------------------------------------------

def simulate(bf: pd.DataFrame, m: pd.Series, thr: float, exit_: float, stop: float,
             cost_one_way_bps: float, funding_pct_per_settlement: float = 0.02,
             funding_times_utc=FUNDING_TIMES_UTC_DEFAULT, max_gap_min: int = 5,
             apply_masks: bool = True, size_btc: float = SIZE_BTC_DEFAULT) -> pd.DataFrame:
    """Run the PREREG execution rules over one bitFlyer bar series.

    Parameters
    ----------
    bf : DataFrame indexed by UTC bar-start timestamps with ``open``/``high``/
        ``low``/``close`` (NaN on empty minutes; rows may be absent).
    m : momentum series (fraction), indexed by UTC timestamps; aligned to
        the minute grid by timestamp. Minutes with no m get no entry and no
        exit signal (the stop is still checked).
    thr, exit_, stop : PERCENT of price (0.8 == 0.8%).
    cost_one_way_bps : one-way taker cost in bps; the ledger charges 2x.
    funding_pct_per_settlement : percent of entry notional per settlement
        instant crossed (0.02 == 0.02%).
    funding_times_utc : UTC hours of the daily settlements.
    max_gap_min : consecutive valid bars more than this many minutes apart
        form a big gap (see module docstring).
    apply_masks : True (default) applies the misprint blanking, the
        signal-discard priority rule and the gap exclusion flag; False runs
        the bare execution rules (deferral across any blank length,
        ``excluded_gap`` all False, ``straddles_gap`` still reported).
    size_btc : position size, only used for the descriptive ``pnl_jpy``.

    Returns the trade ledger (columns ``LEDGER_COLUMNS``), one row per trade
    in chronological order, with summary counts in ``.attrs``. Empty frame
    with the same columns if no trade.
    """
    for name, v in (("thr", thr), ("exit_", exit_), ("stop", stop)):
        if not np.isfinite(v) or v < 0:
            raise ValueError(f"{name} must be a finite non-negative percent, got {v!r}")
    if any(col not in bf.columns for col in OHLC):
        raise ValueError("bf must have open/high/low/close columns")
    max_gap_min = int(max_gap_min)

    grid = to_minute_grid(bf)
    n_misprint = 0
    if apply_masks:
        mp = misprint_mask(grid).to_numpy()
        n_misprint = int(mp.sum())
        if n_misprint:
            grid.loc[mp, OHLC] = np.nan
    idx = grid.index
    n = len(idx)
    o = grid["open"].to_numpy(dtype=float)
    h = grid["high"].to_numpy(dtype=float)
    lo = grid["low"].to_numpy(dtype=float)
    c = grid["close"].to_numpy(dtype=float)
    valid = ~(np.isnan(o) | np.isnan(h) | np.isnan(lo) | np.isnan(c))

    m_idx = _utc_index(m.index)
    mm = pd.Series(m.to_numpy(dtype=float), index=m_idx).reindex(idx).to_numpy(dtype=float)
    thr_f, exit_f, stop_f = thr / 100.0, exit_ / 100.0, stop / 100.0
    has_m = ~np.isnan(mm)
    sig = np.zeros(n, dtype=np.int8)
    sig[has_m & (mm > thr_f)] = 1
    sig[has_m & (mm < -thr_f)] = -1
    exit_sig = has_m & (np.abs(mm) < exit_f)
    n_signal_bars = int((sig != 0).sum())

    # big gaps on the (masked) grid: positions == minutes here
    gaps = big_gaps(grid, max_gap_min)
    gap_pa = idx.searchsorted(gaps["t_a"].to_numpy()) if len(gaps) else np.array([], dtype=int)
    gap_pb = idx.searchsorted(gaps["t_b"].to_numpy()) if len(gaps) else np.array([], dtype=int)

    n_discarded = 0
    if apply_masks and len(gaps):
        discard = np.zeros(n, dtype=bool)
        for pa, pb in zip(gap_pa, gap_pb):
            discard[max(pa - (max_gap_min - 1), 0):pb] = True   # t_a-4 .. t_b-1 (max_gap_min=5)
        n_discarded = int(((sig != 0) & discard).sum())
        sig[discard] = 0

    # next index (>= i) carrying a non-zero signal, for fast skipping while flat
    pos_or_n = np.where(sig != 0, np.arange(n), n)
    next_sig = np.minimum.accumulate(pos_or_n[::-1])[::-1]

    def straddles(entry_i: int, exit_i: int) -> bool:
        if not len(gap_pa):
            return False
        kpos = int(np.searchsorted(gap_pa, entry_i, side="left"))   # first gap with t_a >= entry
        return kpos < len(gap_pa) and gap_pb[kpos] <= exit_i

    idx64 = idx.tz_localize(None).to_numpy()
    settle = settlement_instants(idx[0], idx[-1], funding_times_utc).tz_localize(None).to_numpy()

    def n_settle(entry_i: int, exit_i: int) -> int:
        return int(np.searchsorted(settle, idx64[exit_i], side="right")
                   - np.searchsorted(settle, idx64[entry_i], side="right"))

    cost_bps = 2.0 * float(cost_one_way_bps)
    funding_bps_each = float(funding_pct_per_settlement) * 100.0  # % -> bps

    trades: list[dict] = []
    pos: dict | None = None
    pending: dict | None = None
    last_valid = int(np.flatnonzero(valid)[-1]) if valid.any() else -1

    def close_trade(exit_i: int, exit_px: float, reason: str, n_def_exit: int,
                    exit_sig_i: int) -> None:
        side = pos["side"]
        entry_px = pos["entry_px"]
        gross = side * (exit_px / entry_px - 1.0) * BPS
        ns = n_settle(pos["entry_i"], exit_i)
        funding = ns * funding_bps_each
        net = gross - cost_bps - funding
        strad = straddles(pos["entry_i"], exit_i)
        trades.append({
            "entry_ts": idx[pos["entry_i"]], "exit_ts": idx[exit_i], "side": side,
            "entry_px": entry_px, "exit_px": exit_px,
            "gross_bps": gross, "cost_bps": cost_bps, "funding_bps": funding, "net_bps": net,
            "exit_reason": reason,
            "n_deferred": pos["n_def_entry"] + n_def_exit, "n_settlements": ns,
            "excluded_gap": bool(strad and apply_masks),
            "regime": regime_of(idx[pos["entry_i"]]),
            "straddles_gap": strad,
            "entry_signal_ts": idx[pos["sig_i"]], "exit_signal_ts": idx[exit_sig_i],
            "n_deferred_entry": pos["n_def_entry"], "n_deferred_exit": n_def_exit,
            "hold_min": float((idx[exit_i] - idx[pos["entry_i"]]) / MINUTE),
            "pnl_jpy": net / BPS * entry_px * size_btc,
        })

    i = 0
    while i < n:
        # ---- 1. fills at the open of bar i ---------------------------------
        if pending is not None:
            if not valid[i]:
                pending["n_def"] += 1
                i += 1
                continue
            if pending["kind"] == "entry":
                pos = {"side": pending["side"], "entry_px": o[i], "entry_i": i,
                       "sig_i": pending["sig_i"], "n_def_entry": pending["n_def"]}
            else:
                close_trade(i, o[i], pending["reason"], pending["n_def"], pending["sig_i"])
                pos = None
            pending = None

        # ---- 2. decisions at the close of bar i ----------------------------
        if pos is None:
            if sig[i] != 0:
                pending = {"kind": "entry", "side": int(sig[i]), "sig_i": i, "n_def": 0}
                i += 1
            else:
                i = int(next_sig[i + 1]) if i + 1 < n else n   # nothing happens while flat & signal-less
            continue
        # holding, nothing pending
        stop_hit = False
        if valid[i]:
            if pos["side"] == 1:
                stop_hit = lo[i] <= pos["entry_px"] * (1.0 - stop_f)
            else:
                stop_hit = h[i] >= pos["entry_px"] * (1.0 + stop_f)
        if stop_hit:
            pending = {"kind": "exit", "reason": "stop", "sig_i": i, "n_def": 0}
        elif exit_sig[i]:
            pending = {"kind": "exit", "reason": "exit", "sig_i": i, "n_def": 0}
        i += 1

    # ---- end of data while holding ----------------------------------------
    if pos is not None and last_valid >= pos["entry_i"]:
        n_def_exit = pending["n_def"] if pending is not None else 0
        sig_i = pending["sig_i"] if pending is not None else last_valid
        close_trade(last_valid, c[last_valid], "end", n_def_exit, sig_i)

    ledger = pd.DataFrame(trades, columns=LEDGER_COLUMNS)
    if len(ledger):
        for col in ("side", "n_deferred", "n_settlements", "n_deferred_entry", "n_deferred_exit"):
            ledger[col] = ledger[col].astype(int)
        for col in ("excluded_gap", "straddles_gap"):
            ledger[col] = ledger[col].astype(bool)
    ledger.attrs.update({
        "apply_masks": bool(apply_masks),
        "n_minutes_grid": int(n),
        "n_valid_bars": int(valid.sum()),
        "n_entry_signal_bars": n_signal_bars,
        "n_entry_signals_discarded": n_discarded,
        "n_misprint_rows_blanked": n_misprint,
        "n_big_gaps": int(len(gaps)),
        "n_trades": int(len(ledger)),
        "n_excluded_gap": int(ledger["excluded_gap"].sum()) if len(ledger) else 0,
        "n_straddles_gap": int(ledger["straddles_gap"].sum()) if len(ledger) else 0,
        "n_deferred_total": int(ledger["n_deferred"].sum()) if len(ledger) else 0,
    })
    return ledger


# ---------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------

def daily_pnl(ledger: pd.DataFrame, value: str = "net_bps",
              include_excluded: bool = False) -> pd.Series:
    """Sum of ``value`` per UTC calendar day of the EXIT, over every calendar
    day from the first to the last exit (days without a trade are 0).

    ``excluded_gap`` trades are dropped unless ``include_excluded``. Returns
    an empty float Series if there is nothing to aggregate.
    """
    if not len(ledger):
        return pd.Series(dtype=float)
    df = ledger if include_excluded else ledger[~ledger["excluded_gap"].astype(bool)]
    if not len(df):
        return pd.Series(dtype=float)
    days = pd.DatetimeIndex(pd.to_datetime(df["exit_ts"], utc=True)).normalize()
    s = pd.Series(df[value].to_numpy(dtype=float), index=days).groupby(level=0).sum()
    full = pd.date_range(s.index.min(), s.index.max(), freq="D", tz="UTC")
    return s.reindex(full, fill_value=0.0).rename(value)


def sharpe_annual(daily: pd.Series, periods_per_year: int = 365) -> float:
    """mean / sd(ddof=1) × sqrt(periods_per_year). Crypto CFD trades every
    calendar day, so the default is 365. NaN if fewer than 2 days or sd == 0."""
    x = np.asarray(daily, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return float("nan")
    sd = float(x.std(ddof=1))
    if sd == 0:
        return float("nan")
    return float(x.mean()) / sd * float(np.sqrt(periods_per_year))


# ---------------------------------------------------------------------------
# null: block permutation of the leading market's log returns
# ---------------------------------------------------------------------------

def block_permute_log_returns(close: pd.Series, rng: np.random.Generator,
                              block: str = "D") -> pd.Series:
    """Permute the ORDER of ``block``-sized blocks of log returns and rebuild
    the price level by cumulating them from the (fixed) first level.

    * log returns are diff(log close) over the non-NaN observations; the
      return at t belongs to the block of t (``index.floor(block)``);
    * blocks keep their internal order, only their sequence is shuffled;
    * the total log return and the first level are invariant, and no
      artificial jump is created at a block boundary because levels are
      cumulated, not spliced.

    NaN observations stay NaN at their timestamps. Returns a Series on the
    same index as ``close``.
    """
    idx = _utc_index(close.index)
    s = pd.Series(close.to_numpy(dtype=float), index=idx)
    ok = s.notna().to_numpy()
    if ok.sum() < 2:
        return s.copy()
    sv = s[ok]
    logp = np.log(sv.to_numpy())
    r = np.diff(logp)                                # r[j] belongs to sv.index[j+1]
    keys = sv.index[1:].floor(block)
    change = np.flatnonzero(keys[1:] != keys[:-1]) + 1
    starts = np.concatenate([[0], change]).astype(int)
    ends = np.concatenate([change, [len(r)]]).astype(int)
    order = rng.permutation(len(starts))
    r_perm = np.concatenate([r[starts[b]:ends[b]] for b in order])
    levels = np.exp(logp[0] + np.cumsum(r_perm))
    out = pd.Series(np.nan, index=idx, name=close.name)
    ok_pos = np.flatnonzero(ok)
    out.iloc[ok_pos[0]] = sv.iloc[0]
    out.iloc[ok_pos[1:]] = levels
    return out
