"""P2-08 fast engine — an array/numba re-implementation of the SAME rules as
`bot.research.xborder_p2.simulate`, for the 2,000-draw × 27-configuration null
(PREREG 第 4 稿「帰無の構成」: "実装はベクトル化(numpy、必要なら numba)を前提").

Nothing here changes a rule. The pure-pandas `simulate` stays the reference:
`tests/test_xborder_p2_fast.py` requires the two ledgers to be identical
(trade count, entry/exit timestamps, every money column to 1e-9 bps) on the
known-answer tapes and on real dev-set months. The split is

  * `prepare_grid(bf, ...)`      — once per bitFlyer series (and per
                                   apply_masks): minute grid, misprint
                                   blanking, big gaps, discard window,
                                   settlement instants, day ids;
  * `momentum_on_grid(...)`      — m(t) for one k, reindexed onto the grid
                                   (numerically identical to
                                   `momentum_signal(...).reindex(grid)`);
  * `simulate_fast(grid, mm, ...)` — one configuration: the numba loop plus a
                                   vectorised ledger build; returns the same
                                   DataFrame as `simulate` (same columns,
                                   dtypes, `.attrs` keys);
  * `simulate_arrays(...)`       — the same trades as plain numpy arrays
                                   (no DataFrame) for the null loop;
  * `BlockPermuter`              — `block_permute_log_returns` with the
                                   day-block bookkeeping precomputed once
                                   (bit-identical output for the same rng).

Everything is UTC; percent/bps conventions are those of `xborder_p2`.
"""
from __future__ import annotations

from dataclasses import dataclass

import numba
import numpy as np
import pandas as pd

from bot.research.xborder_p2 import (
    BPS,
    CRYPTO_CFD_START,
    FUNDING_TIMES_UTC_DEFAULT,
    LEDGER_COLUMNS,
    MINUTE,
    OHLC,
    REGIME_CRYPTO_CFD,
    REGIME_LIGHTNING_FX,
    SIZE_BTC_DEFAULT,
    _utc_index,
    big_gaps,
    misprint_mask,
    settlement_instants,
    to_minute_grid,
)

REASON_CODES = {0: "exit", 1: "stop", 2: "end"}
_NS_PER_DAY = 86_400_000_000_000


# ---------------------------------------------------------------------------
# grid preparation (shared across configurations and null draws)
# ---------------------------------------------------------------------------

@dataclass
class Grid:
    idx: pd.DatetimeIndex            # complete UTC minute grid
    o: np.ndarray
    h: np.ndarray
    lo: np.ndarray
    c: np.ndarray
    valid: np.ndarray                # bool
    gap_pa: np.ndarray               # grid positions of t_a (big gaps)
    gap_pb: np.ndarray               # grid positions of t_b
    discard: np.ndarray | None       # bool mask (apply_masks only) else None
    idx64: np.ndarray                # naive datetime64[ns] of idx
    settle64: np.ndarray             # naive datetime64[ns] settlement instants
    day_id: np.ndarray               # int64 UTC day number of every grid minute
    last_valid: int
    apply_masks: bool
    max_gap_min: int
    n_misprint: int

    @property
    def n(self) -> int:
        return len(self.idx)


def prepare_grid(bf: pd.DataFrame, max_gap_min: int = 5, apply_masks: bool = True,
                 funding_times_utc=FUNDING_TIMES_UTC_DEFAULT) -> Grid:
    """Everything `simulate` derives from ``bf`` before the per-configuration
    loop, computed once. Same helper calls, same order, as `simulate`."""
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
    o = np.ascontiguousarray(grid["open"].to_numpy(dtype=float))
    h = np.ascontiguousarray(grid["high"].to_numpy(dtype=float))
    lo = np.ascontiguousarray(grid["low"].to_numpy(dtype=float))
    c = np.ascontiguousarray(grid["close"].to_numpy(dtype=float))
    valid = ~(np.isnan(o) | np.isnan(h) | np.isnan(lo) | np.isnan(c))

    gaps = big_gaps(grid, max_gap_min)
    if len(gaps):
        gap_pa = idx.searchsorted(gaps["t_a"].to_numpy()).astype(np.int64)
        gap_pb = idx.searchsorted(gaps["t_b"].to_numpy()).astype(np.int64)
    else:
        gap_pa = np.array([], dtype=np.int64)
        gap_pb = np.array([], dtype=np.int64)
    discard = None
    if apply_masks and len(gaps):
        discard = np.zeros(n, dtype=bool)
        for pa, pb in zip(gap_pa, gap_pb):
            discard[max(pa - (max_gap_min - 1), 0):pb] = True
    idx64 = idx.tz_localize(None).to_numpy()
    settle64 = settlement_instants(idx[0], idx[-1], funding_times_utc).tz_localize(None).to_numpy()
    day_id = (idx64.astype("datetime64[ns]").astype(np.int64) // _NS_PER_DAY).astype(np.int64)
    last_valid = int(np.flatnonzero(valid)[-1]) if valid.any() else -1
    return Grid(idx=idx, o=o, h=h, lo=lo, c=c, valid=valid, gap_pa=gap_pa, gap_pb=gap_pb,
                discard=discard, idx64=idx64, settle64=settle64, day_id=day_id,
                last_valid=last_valid, apply_masks=bool(apply_masks),
                max_gap_min=max_gap_min, n_misprint=n_misprint)


# ---------------------------------------------------------------------------
# signal on the grid
# ---------------------------------------------------------------------------

def align_to_grid(grid: Grid, series: pd.Series) -> np.ndarray:
    """``series`` (UTC-indexed) reindexed onto the grid as a float array."""
    s_idx = _utc_index(series.index)
    return (pd.Series(series.to_numpy(dtype=float), index=s_idx)
            .reindex(grid.idx).to_numpy(dtype=float))


class BinanceGrid:
    """The leading market's close on ITS OWN complete minute grid, so m(t) for
    any k is a positional shift (identical to `momentum_signal`'s by-time
    lookup) and the reindex onto the bitFlyer grid is a fixed gather."""

    def __init__(self, close: pd.Series, grid: Grid):
        idx = _utc_index(close.index)
        self.src_index = idx
        self.idx = pd.date_range(idx[0], idx[-1], freq="min")
        # source row -> bn grid position (every source minute is on the grid)
        self._src_pos = self.idx.get_indexer(idx)
        self.close = self.to_bn_grid(close.to_numpy(dtype=float))
        # gather positions: bf grid minute -> bn grid position (or -1)
        pos = self.idx.get_indexer(grid.idx)
        self._pos = pos
        self._ok = pos >= 0

    def to_bn_grid(self, close_src: np.ndarray) -> np.ndarray:
        """An array on the SOURCE index (e.g. `BlockPermuter.permute` output)
        placed onto the complete bn minute grid (NaN where absent)."""
        close_src = np.asarray(close_src, dtype=float)
        if len(close_src) != len(self.src_index):
            raise ValueError(f"expected {len(self.src_index)} source rows, got {len(close_src)}")
        out = np.full(len(self.idx), np.nan)
        out[self._src_pos] = close_src
        return out

    def momentum(self, k: int, close_src: np.ndarray | None = None) -> np.ndarray:
        """m(t) = close(t)/close(t−k) − 1 on the bitFlyer grid (NaN outside).
        ``close_src`` (optional) is a replacement close on the SOURCE index —
        the permuted series of a null draw."""
        cl = self.close if close_src is None else self.to_bn_grid(close_src)
        return self.momentum_from_bn_grid(k, cl)

    def momentum_from_bn_grid(self, k: int, cl: np.ndarray) -> np.ndarray:
        """Same as `momentum` for a close already on the bn grid (so the
        three k's of one null draw share a single `to_bn_grid`)."""
        k = int(k)
        if k < 1:
            raise ValueError(f"k must be >= 1, got {k}")
        m = np.full(len(cl), np.nan)
        with np.errstate(divide="ignore", invalid="ignore"):
            m[k:] = cl[k:] / cl[:-k] - 1.0
        out = np.full(len(self._pos), np.nan)
        out[self._ok] = m[self._pos[self._ok]]
        return out


def momentum_on_grid(grid: Grid, close: pd.Series, k: int) -> np.ndarray:
    return BinanceGrid(close, grid).momentum(k)


def build_signals(grid: Grid, mm: np.ndarray, thr: float, exit_: float
                  ) -> tuple[np.ndarray, np.ndarray, int, int]:
    """(sig int8, exit_sig bool, n_entry_signal_bars, n_discarded) exactly as
    `simulate` derives them (discard rule applied when the grid has masks)."""
    for name, v in (("thr", thr), ("exit_", exit_)):
        if not np.isfinite(v) or v < 0:
            raise ValueError(f"{name} must be a finite non-negative percent, got {v!r}")
    thr_f, exit_f = thr / 100.0, exit_ / 100.0
    has_m = ~np.isnan(mm)
    sig = np.zeros(grid.n, dtype=np.int8)
    sig[has_m & (mm > thr_f)] = 1
    sig[has_m & (mm < -thr_f)] = -1
    exit_sig = has_m & (np.abs(mm) < exit_f)
    n_signal_bars = int((sig != 0).sum())
    n_discarded = 0
    if grid.discard is not None:
        n_discarded = int(((sig != 0) & grid.discard).sum())
        sig[grid.discard] = 0
    return sig, exit_sig, n_signal_bars, n_discarded


# ---------------------------------------------------------------------------
# the loop
# ---------------------------------------------------------------------------

@numba.njit(cache=True, nogil=True)
def _core(o, h, lo, c, valid, sig, exit_sig, stop_f, last_valid, cap):
    n = o.shape[0]
    entry_i = np.empty(cap, np.int64)
    exit_i = np.empty(cap, np.int64)
    side = np.empty(cap, np.int64)
    entry_px = np.empty(cap, np.float64)
    exit_px = np.empty(cap, np.float64)
    reason = np.empty(cap, np.int64)
    ndef_e = np.empty(cap, np.int64)
    ndef_x = np.empty(cap, np.int64)
    sig_i = np.empty(cap, np.int64)
    xsig_i = np.empty(cap, np.int64)
    nt = 0

    pos_open = False
    pending = 0          # 0 none, 1 entry, 2 exit
    pend_side = 0
    pend_sig_i = 0
    pend_ndef = 0
    pend_reason = 0
    p_side = 0
    p_entry_px = 0.0
    p_entry_i = 0
    p_sig_i = 0
    p_ndef = 0

    i = 0
    while i < n:
        if pending != 0:
            if not valid[i]:
                pend_ndef += 1
                i += 1
                continue
            if pending == 1:
                pos_open = True
                p_side = pend_side
                p_entry_px = o[i]
                p_entry_i = i
                p_sig_i = pend_sig_i
                p_ndef = pend_ndef
            else:
                entry_i[nt] = p_entry_i
                exit_i[nt] = i
                side[nt] = p_side
                entry_px[nt] = p_entry_px
                exit_px[nt] = o[i]
                reason[nt] = pend_reason
                ndef_e[nt] = p_ndef
                ndef_x[nt] = pend_ndef
                sig_i[nt] = p_sig_i
                xsig_i[nt] = pend_sig_i
                nt += 1
                pos_open = False
            pending = 0
        if not pos_open:
            if sig[i] != 0:
                pending = 1
                pend_side = sig[i]
                pend_sig_i = i
                pend_ndef = 0
            i += 1
            continue
        stop_hit = False
        if valid[i]:
            if p_side == 1:
                stop_hit = lo[i] <= p_entry_px * (1.0 - stop_f)
            else:
                stop_hit = h[i] >= p_entry_px * (1.0 + stop_f)
        if stop_hit:
            pending = 2
            pend_reason = 1
            pend_sig_i = i
            pend_ndef = 0
        elif exit_sig[i]:
            pending = 2
            pend_reason = 0
            pend_sig_i = i
            pend_ndef = 0
        i += 1

    if pos_open and last_valid >= p_entry_i:
        entry_i[nt] = p_entry_i
        exit_i[nt] = last_valid
        side[nt] = p_side
        entry_px[nt] = p_entry_px
        exit_px[nt] = c[last_valid]
        reason[nt] = 2
        ndef_e[nt] = p_ndef
        ndef_x[nt] = pend_ndef if pending != 0 else 0
        sig_i[nt] = p_sig_i
        xsig_i[nt] = pend_sig_i if pending != 0 else last_valid
        nt += 1
    return (nt, entry_i[:nt], exit_i[:nt], side[:nt], entry_px[:nt], exit_px[:nt],
            reason[:nt], ndef_e[:nt], ndef_x[:nt], sig_i[:nt], xsig_i[:nt])


def simulate_arrays(grid: Grid, mm: np.ndarray, thr: float, exit_: float, stop: float,
                    funding_pct_per_settlement: float = 0.02,
                    entry_gate: np.ndarray | None = None) -> dict:
    """One configuration → dict of numpy arrays (one element per trade) plus
    the summary counts. ``gross_bps`` / ``funding_bps`` are cost-free so any
    cost constant can be applied afterwards (net = gross − 2·c − funding).

    ``entry_gate`` (optional, bool per grid minute; P2-08 iteration 1) keeps
    an ENTRY signal only where the gate is True — the state-conditioned
    "建玉可" of the PREREG ladder. It is applied after the discard window
    and touches nothing else: exit signals, stops, deferral, funding and the
    gap exclusion are unchanged. ``None`` (the default) is the unconditioned
    engine, bit-for-bit as before; the returned dict then carries
    ``n_entry_signals_gated`` = 0.
    """
    if not np.isfinite(stop) or stop < 0:
        raise ValueError(f"stop must be a finite non-negative percent, got {stop!r}")
    sig, exit_sig, n_signal_bars, n_discarded = build_signals(grid, mm, thr, exit_)
    n_gated = 0
    if entry_gate is not None:
        gate = np.asarray(entry_gate, dtype=bool)
        if gate.shape != (grid.n,):
            raise ValueError(f"entry_gate must have one bool per grid minute ({grid.n}), got {gate.shape}")
        n_gated = int(((sig != 0) & ~gate).sum())
        sig[~gate] = 0
    cap = int((sig != 0).sum()) + 1
    (nt, entry_i, exit_i, side, entry_px, exit_px, reason, ndef_e, ndef_x,
     sig_i, xsig_i) = _core(grid.o, grid.h, grid.lo, grid.c, grid.valid, sig, exit_sig,
                            stop / 100.0, grid.last_valid, cap)
    gross = side * (exit_px / entry_px - 1.0) * BPS
    ns = (np.searchsorted(grid.settle64, grid.idx64[exit_i], side="right")
          - np.searchsorted(grid.settle64, grid.idx64[entry_i], side="right")).astype(np.int64)
    funding = ns * (float(funding_pct_per_settlement) * 100.0)
    if len(grid.gap_pa):
        kpos = np.searchsorted(grid.gap_pa, entry_i, side="left")
        ok = kpos < len(grid.gap_pa)
        strad = ok & (grid.gap_pb[np.minimum(kpos, len(grid.gap_pa) - 1)] <= exit_i)
    else:
        strad = np.zeros(nt, dtype=bool)
    return {
        "entry_i": entry_i, "exit_i": exit_i, "side": side, "entry_px": entry_px,
        "exit_px": exit_px, "reason": reason, "ndef_e": ndef_e, "ndef_x": ndef_x,
        "sig_i": sig_i, "xsig_i": xsig_i, "gross_bps": gross, "n_settlements": ns,
        "funding_bps": funding, "straddles_gap": strad,
        "excluded_gap": strad & grid.apply_masks,
        "exit_day": grid.day_id[exit_i] if nt else np.array([], dtype=np.int64),
        "n_entry_signal_bars": n_signal_bars, "n_entry_signals_discarded": n_discarded,
        "n_entry_signals_gated": n_gated,
        "n_big_gaps": int(len(grid.gap_pa)), "n_trades": int(nt),
    }


def simulate_fast(grid: Grid, mm: np.ndarray, thr: float, exit_: float, stop: float,
                  cost_one_way_bps: float, funding_pct_per_settlement: float = 0.02,
                  size_btc: float = SIZE_BTC_DEFAULT,
                  entry_gate: np.ndarray | None = None) -> pd.DataFrame:
    """The `simulate` ledger (same columns / dtypes / attrs) for one
    configuration on a prepared grid. ``entry_gate`` as in `simulate_arrays`;
    when given, the attrs gain ``n_entry_signals_gated`` (absent otherwise so
    the ungated attrs stay equal to the reference engine's)."""
    a = simulate_arrays(grid, mm, thr, exit_, stop, funding_pct_per_settlement, entry_gate)
    nt = a["n_trades"]
    cost_bps = 2.0 * float(cost_one_way_bps)
    net = a["gross_bps"] - cost_bps - a["funding_bps"]
    idx = grid.idx
    entry_ts = idx[a["entry_i"]]
    exit_ts = idx[a["exit_i"]]
    ledger = pd.DataFrame({
        "entry_ts": entry_ts, "exit_ts": exit_ts, "side": a["side"].astype(int),
        "entry_px": a["entry_px"], "exit_px": a["exit_px"],
        "gross_bps": a["gross_bps"], "cost_bps": np.full(nt, cost_bps),
        "funding_bps": a["funding_bps"], "net_bps": net,
        "exit_reason": np.array([REASON_CODES[int(r)] for r in a["reason"]], dtype=object),
        "n_deferred": (a["ndef_e"] + a["ndef_x"]).astype(int),
        "n_settlements": a["n_settlements"].astype(int),
        "excluded_gap": a["excluded_gap"].astype(bool),
        "regime": np.where(entry_ts >= CRYPTO_CFD_START, REGIME_CRYPTO_CFD, REGIME_LIGHTNING_FX)
        if nt else np.array([], dtype=object),
        "straddles_gap": a["straddles_gap"].astype(bool),
        "entry_signal_ts": idx[a["sig_i"]], "exit_signal_ts": idx[a["xsig_i"]],
        "n_deferred_entry": a["ndef_e"].astype(int), "n_deferred_exit": a["ndef_x"].astype(int),
        "hold_min": (a["exit_i"] - a["entry_i"]).astype(float),
        "pnl_jpy": net / BPS * a["entry_px"] * size_btc,
    }, columns=LEDGER_COLUMNS)
    if nt == 0:
        ledger = pd.DataFrame(columns=LEDGER_COLUMNS)
    ledger.attrs.update({
        "apply_masks": bool(grid.apply_masks),
        "n_minutes_grid": int(grid.n),
        "n_valid_bars": int(grid.valid.sum()),
        "n_entry_signal_bars": a["n_entry_signal_bars"],
        "n_entry_signals_discarded": a["n_entry_signals_discarded"],
        "n_misprint_rows_blanked": int(grid.n_misprint),
        "n_big_gaps": a["n_big_gaps"],
        "n_trades": int(nt),
        "n_excluded_gap": int(a["excluded_gap"].sum()) if nt else 0,
        "n_straddles_gap": int(a["straddles_gap"].sum()) if nt else 0,
        "n_deferred_total": int((a["ndef_e"] + a["ndef_x"]).sum()) if nt else 0,
    })
    if entry_gate is not None:
        ledger.attrs["n_entry_signals_gated"] = a["n_entry_signals_gated"]
    return ledger


# ---------------------------------------------------------------------------
# aggregation on arrays (matches daily_pnl / sharpe_annual)
# ---------------------------------------------------------------------------

def daily_from_arrays(exit_day: np.ndarray, values: np.ndarray, keep: np.ndarray
                      ) -> np.ndarray:
    """Sum of ``values[keep]`` per UTC day of exit, every calendar day from the
    first to the last kept exit (zeros between) — `daily_pnl` on arrays."""
    d = exit_day[keep]
    v = values[keep]
    if len(d) == 0:
        return np.array([], dtype=float)
    lo = int(d.min())
    return np.bincount(d - lo, weights=v, minlength=int(d.max()) - lo + 1)


def sharpe_from_daily(x: np.ndarray, periods_per_year: int = 365) -> float:
    x = np.asarray(x, dtype=float)
    if len(x) < 2:
        return float("nan")
    sd = float(x.std(ddof=1))
    if sd == 0:
        return float("nan")
    return float(x.mean()) / sd * float(np.sqrt(periods_per_year))


# ---------------------------------------------------------------------------
# block permutation with precomputed blocks
# ---------------------------------------------------------------------------

class BlockPermuter:
    """`block_permute_log_returns(close, rng, block)` with the block layout
    computed once. `permute(rng)` returns the permuted close as a float array
    on the SAME index as ``close`` (NaN kept in place), bit-identical to the
    reference function for the same rng state."""

    def __init__(self, close: pd.Series, block: str = "D"):
        idx = _utc_index(close.index)
        s = pd.Series(close.to_numpy(dtype=float), index=idx)
        ok = s.notna().to_numpy()
        self.index = idx
        self.template = s.to_numpy(dtype=float).copy()
        self.ok_pos = np.flatnonzero(ok)
        sv = s[ok]
        self.logp = np.log(sv.to_numpy())
        self.r = np.diff(self.logp)
        keys = sv.index[1:].floor(block)
        change = np.flatnonzero(keys[1:] != keys[:-1]) + 1
        self.starts = np.concatenate([[0], change]).astype(int)
        self.ends = np.concatenate([change, [len(self.r)]]).astype(int)
        self.first_level = float(sv.iloc[0]) if len(sv) else float("nan")

    @property
    def n_blocks(self) -> int:
        return len(self.starts)

    def permute(self, rng: np.random.Generator) -> np.ndarray:
        if len(self.ok_pos) < 2:
            return self.template.copy()
        order = rng.permutation(len(self.starts))
        r_perm = np.concatenate([self.r[self.starts[b]:self.ends[b]] for b in order])
        levels = np.exp(self.logp[0] + np.cumsum(r_perm))
        out = np.full(len(self.template), np.nan)
        out[self.ok_pos[0]] = self.first_level
        out[self.ok_pos[1:]] = levels
        return out
