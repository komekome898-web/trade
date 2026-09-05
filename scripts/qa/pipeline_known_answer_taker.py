#!/usr/bin/env python3
"""PIPELINE known-answer test — taker execution (docs/PHASE2_SPEC.md §5).

Not an auditor test: this checks that OUR OWN code paths (src/bot/backtest/
engine.py's run_backtest + src/bot/backtest/metrics.py's compute_metrics,
driven through a minimal strategy) recover a planted mean effect from
synthetic data and correctly report a null effect as null. It is the
"taker" packet PHASE2_GRID.md's bottom table lists as missing before G2/G3
can start (G1's daily/board-auction packet is the sibling script
pipeline_known_answer_daily.py).

Construction (see generate()):
  - 60 days of 1-minute OHLCV on a synthetic FX_BTC_JPY-like instrument,
    GARCH(1,1)-vol-clustered log-return noise (zero drift), seeded.
  - One planted EVENT per day at a fixed clock minute (09:15 UTC): a 3-bar
    move of ~28bps (std 4bps, either sign) is injected on top of the noise,
    reliably tripping a >=20bps/3-bar detector (~98% of days).
  - Following each event, a planted CONTINUATION drift of X bps (spread
    evenly over the next 30 bars, same sign as the event) is added, for
    X in {0, 3, 8} -- three separate tapes sharing the identical background
    noise/event realization so only X differs.
  - Realistic clutter, untouched by anything downstream: a synthetic
    maintenance flat-bar window 19:00-19:10 UTC every day (bitFlyer's real
    window, per scripts/data_quality.py), and a handful of isolated
    single-bar "bad print" dislocations (an OHLC spike that does not
    propagate to the next bar's open) placed well away from any event/hold
    window so they cannot contaminate the measured trades.

Strategy: TakerEventStrategy enters taker (BUY on an up-event, SELL/short
on a down-event, entry_sides via allow_short=True) exactly at the planted
event bar and holds for 30 bars (max_hold_bars=30 -> forced taker exit,
reason="time_exit"), matching "the next 30-minute return".

Cost: config/constants.yaml's `measured` bitFlyer FX_BTC_JPY constants only,
loaded via require_source() (CLAUDE.md §5 / constants.py) --
taker_fee_pct (primary_document, 0%) and realized_round_trip_bps (measured,
[2.0, 2.6]bps -> midpoint used as the modeled round-trip cost). Pulling the
deprecated taker_round_trip_floor_bps_OLD (assumed) is asserted to raise.

Outputs -> backtest_data/qa_pipeline_taker_<date>/:
  candles_qa_taker_X{0,3,8}bps_<date>.csv.gz   (ts,open,high,low,close,volume)
  RESULTS.md                                    (X vs recovered table + findings)
  planted_values_sealed.json                    (ground truth as generated)
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from bot.backtest.engine import CostModel, run_backtest  # noqa: E402
from bot.constants import AssumedConstantError, load_constants, require_source  # noqa: E402
from bot.strategy.base import Signal, SignalType, Strategy  # noqa: E402

SEED = 20260905
DAYS = 60
BAR_MINUTES = 1
BARS_PER_DAY = 24 * 60
PRICE0 = 6_000_000.0

BASE_SIGMA = 0.0003          # ~3bps/min unconditional vol
GARCH_ALPHA, GARCH_BETA = 0.05, 0.90

EVENT_MINUTE_OF_DAY = 9 * 60 + 15     # 09:15 UTC, fixed clock window
EVENT_MOVE_MEAN_BPS = 28.0
EVENT_MOVE_SIGMA_BPS = 4.0
LOOKBACK_BARS = 3
MOVE_THRESHOLD_BPS = 20.0
HOLD_BARS = 30

MAINT_START = (19, 0)
MAINT_END = (19, 10)

N_BAD_PRINTS = 6
BAD_PRINT_MIN_FRAC, BAD_PRINT_MAX_FRAC = 0.10, 0.18

X_VALUES = (0.0, 3.0, 8.0)
ORDER_NOTIONAL_JPY = 1_000_000.0

TS_START = "2026-01-01T00:00:00+00:00"


def garch_returns(rng: np.random.Generator, n: int, base_sigma: float,
                   alpha: float = GARCH_ALPHA, beta: float = GARCH_BETA) -> np.ndarray:
    """GARCH(1,1) vol-clustered zero-drift log returns; unconditional std = base_sigma."""
    omega = base_sigma ** 2 * (1.0 - alpha - beta)
    z = rng.standard_normal(n)
    sigma2 = np.empty(n)
    r = np.empty(n)
    sigma2[0] = base_sigma ** 2
    r[0] = z[0] * np.sqrt(sigma2[0])
    for t in range(1, n):
        sigma2[t] = omega + alpha * r[t - 1] ** 2 + beta * sigma2[t - 1]
        r[t] = z[t] * np.sqrt(sigma2[t])
    return r


def build_base(seed: int, days: int) -> dict:
    """Shared background: noise + planted events, no continuation drift yet."""
    rng = np.random.default_rng(seed)
    n = days * BARS_PER_DAY
    returns = garch_returns(rng, n, BASE_SIGMA)

    events = []
    for day in range(days):
        event_bar = day * BARS_PER_DAY + EVENT_MINUTE_OF_DAY
        if event_bar - LOOKBACK_BARS < 0 or event_bar + HOLD_BARS + 1 >= n:
            continue
        sign = 1.0 if rng.random() < 0.5 else -1.0
        mag_bps = max(1.0, rng.normal(EVENT_MOVE_MEAN_BPS, EVENT_MOVE_SIGMA_BPS))
        # spread the planted move over the LOOKBACK_BARS bars ending at event_bar
        per_bar = sign * (mag_bps / 1e4) / LOOKBACK_BARS
        returns[event_bar - LOOKBACK_BARS + 1: event_bar + 1] += per_bar
        events.append({"day": day, "event_bar": int(event_bar), "sign": sign,
                        "planted_move_bps": round(sign * mag_bps, 4)})

    idx = pd.date_range(TS_START, periods=n, freq="1min", tz="UTC")
    hour, minute = idx.hour.to_numpy(), idx.minute.to_numpy()
    minute_of_day = hour * 60 + minute
    maint_start_mod = MAINT_START[0] * 60 + MAINT_START[1]
    maint_end_mod = MAINT_END[0] * 60 + MAINT_END[1]
    maint_mask = (minute_of_day >= maint_start_mod) & (minute_of_day < maint_end_mod)

    # bad-print placement: far from any event's [event_bar-5, event_bar+HOLD_BARS+5]
    # window and never inside the maintenance window.
    forbidden = np.zeros(n, dtype=bool)
    for ev in events:
        lo = max(0, ev["event_bar"] - 5)
        hi = min(n, ev["event_bar"] + HOLD_BARS + 5)
        forbidden[lo:hi] = True
    forbidden |= maint_mask
    forbidden[0] = True
    candidates = np.flatnonzero(~forbidden)
    bad_idx = rng.choice(candidates, size=min(N_BAD_PRINTS, len(candidates)), replace=False)
    bad_idx.sort()

    return {"rng": rng, "n": n, "idx": idx, "returns": returns, "events": events,
            "maint_mask": maint_mask, "bad_idx": bad_idx.tolist()}


def build_tape(base: dict, x_bps: float) -> pd.DataFrame:
    n, idx, returns = base["n"], base["idx"], base["returns"].copy()
    for ev in base["events"]:
        lo = ev["event_bar"] + 1
        hi = min(n, ev["event_bar"] + 1 + HOLD_BARS)
        returns[lo:hi] += ev["sign"] * (x_bps / 1e4) / HOLD_BARS

    true_close = PRICE0 * np.exp(np.cumsum(returns))

    # maintenance: flat carried-forward bar, chained through consecutive minutes.
    maint_mask = base["maint_mask"]
    disp_close = np.empty(n)
    last_good = PRICE0
    for i in range(n):
        if maint_mask[i]:
            disp_close[i] = last_good
        else:
            disp_close[i] = true_close[i]
            last_good = disp_close[i]

    open_ = np.empty(n)
    open_[0] = PRICE0
    open_[1:] = disp_close[:-1]
    close_ = disp_close.copy()

    rng = base["rng"]
    hi_j = rng.uniform(0.0002, 0.0015, n)
    lo_j = rng.uniform(0.0002, 0.0015, n)
    high = np.maximum(open_, close_) * (1 + hi_j)
    low = np.minimum(open_, close_) * (1 - lo_j)
    volume = rng.lognormal(mean=2.0, sigma=0.7, size=n)
    high[maint_mask] = close_[maint_mask]
    low[maint_mask] = close_[maint_mask]
    open_[maint_mask] = close_[maint_mask]
    volume[maint_mask] = 0.0

    # isolated bad prints: this bar's OHLC dislocates; the NEXT bar's open is
    # built from the already-computed (unglitched) close, so it never propagates.
    for j in base["bad_idx"]:
        ref = close_[j - 1]
        shock = (1.0 if rng.random() < 0.5 else -1.0) * rng.uniform(BAD_PRINT_MIN_FRAC, BAD_PRINT_MAX_FRAC)
        glitched = ref * (1 + shock)
        open_[j] = ref
        close_[j] = glitched
        high[j] = max(ref, glitched) * 1.001
        low[j] = min(ref, glitched) * 0.999
        volume[j] = volume[j] * 0.1  # thin/glitchy prints often carry low reported volume

    df = pd.DataFrame({
        "ts": idx.strftime("%Y-%m-%d %H:%M:%S+00:00"),
        "open": open_, "high": high, "low": low, "close": close_, "volume": volume,
    })
    return df


class TakerEventStrategy(Strategy):
    """Enters taker at the fixed clock-window event bar when the trailing
    LOOKBACK_BARS move exceeds the threshold, holds for HOLD_BARS via the
    engine's max_hold_bars (forced taker exit, reason="time_exit"). Assumes
    the tape starts exactly at 00:00 UTC on a 1-minute grid with no gaps
    (true here by construction), so the clock check is bar-count arithmetic
    rather than timestamp parsing.
    """

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.event_minute = self.params.get("event_minute_of_day", EVENT_MINUTE_OF_DAY)
        self.threshold_bps = self.params.get("move_threshold_bps", MOVE_THRESHOLD_BPS)
        self.lookback = self.params.get("lookback_bars", LOOKBACK_BARS)

    @property
    def min_history(self) -> int:
        return self.lookback + 2

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        i = len(candles) - 1
        if i % BARS_PER_DAY != self.event_minute:
            return Signal(SignalType.HOLD)
        closes = candles["close"].to_numpy()
        if len(closes) <= self.lookback:
            return Signal(SignalType.HOLD)
        move_bps = (closes[-1] / closes[-1 - self.lookback] - 1) * 1e4
        if abs(move_bps) >= self.threshold_bps:
            side = SignalType.BUY if move_bps > 0 else SignalType.SELL
            return Signal(side, reason=f"event_move_bps={move_bps:.2f}")
        return Signal(SignalType.HOLD)


def load_cost_model(root: Path) -> tuple[CostModel, dict]:
    consts = load_constants(root)
    fee_c = require_source("bitflyer_fx_btc_jpy.taker_fee_pct", consts)
    rt_c = require_source("bitflyer_fx_btc_jpy.realized_round_trip_bps", consts)
    rt_val = rt_c.value
    cost_bps = float(np.mean(rt_val)) if isinstance(rt_val, (list, tuple)) else float(rt_val)
    # self-check: an `assumed`/deprecated constant must raise, never silently load.
    try:
        require_source("bitflyer_fx_btc_jpy.taker_round_trip_floor_bps_OLD", consts)
        raise RuntimeError("require_source() failed to reject the deprecated assumed constant")
    except AssumedConstantError:
        pass
    costs = CostModel(taker_fee_pct=float(fee_c.value), spread_pct=cost_bps / 100.0, slippage_pct=0.0)
    provenance = {
        "taker_fee_pct": {"value": fee_c.value, "source_type": fee_c.source_type},
        "realized_round_trip_bps": {"value": rt_c.value, "source_type": rt_c.source_type,
                                     "used_bps": round(cost_bps, 4)},
    }
    return costs, provenance


def trade_net_bps(trade_pnls: list[float]) -> np.ndarray:
    return np.asarray(trade_pnls, dtype=float) / ORDER_NOTIONAL_JPY * 1e4


def mean_se_t(x: np.ndarray) -> tuple[float, float, float]:
    n = len(x)
    m = float(x.mean())
    se = float(x.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    t = m / se if se else float("nan")
    return m, se, t


def generate(out_dir: Path, seed: int = SEED, days: int = DAYS) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    base = build_base(seed, days)
    costs, provenance = load_cost_model(REPO_ROOT)
    cost_bps = provenance["realized_round_trip_bps"]["used_bps"]

    per_x = {}
    tapes = {}
    for x in X_VALUES:
        df = build_tape(base, x)
        strat = TakerEventStrategy()
        result = run_backtest(strat, df, costs=costs, execution="taker", allow_short=True,
                               order_notional_jpy=ORDER_NOTIONAL_JPY, max_hold_bars=HOLD_BARS)
        reasons = [r["reason"] for r in result.trade_log if r["side"].startswith("CLOSE")]
        net_bps = trade_net_bps(result.trade_pnls)
        gross_bps = net_bps + cost_bps
        m_net, se_net, t_net = mean_se_t(net_bps)
        m_gross, se_gross, t_gross = mean_se_t(gross_bps)
        mde = 2.8 * se_net if se_net == se_net else float("nan")  # NaN-safe (n<2 guard)
        planted_net = x - cost_bps
        per_x[x] = {
            "planted_continuation_bps": x,
            "cost_bps_used": cost_bps,
            "planted_net_bps": round(planted_net, 4),
            "n_trades": int(len(net_bps)),
            "n_time_exit": int(sum(1 for r in reasons if r == "time_exit")),
            "n_other_exit_reason": int(sum(1 for r in reasons if r != "time_exit")),
            "recovered_net_bps_mean": round(m_net, 4),
            "recovered_net_bps_se": round(se_net, 4),
            "recovered_net_bps_ci95": [round(m_net - 1.96 * se_net, 4), round(m_net + 1.96 * se_net, 4)],
            "recovered_gross_bps_mean": round(m_gross, 4),
            "gross_t_stat": round(t_gross, 4),
            "mde_bps": round(mde, 4),
            "within_mde": bool(abs(m_net - planted_net) < mde),
        }
        tapes[x] = df

    findings = []
    n_maint = int(base["maint_mask"].sum())
    n_bad = len(base["bad_idx"])
    findings.append(
        "src/bot/backtest/engine.py:run_backtest consumes `candles` verbatim -- no maintenance-"
        f"window or bad-print filtering exists anywhere in the taker path. All {n_maint} synthetic "
        f"maintenance flat-bars and all {n_bad} isolated bad-print bars passed into the backtest "
        "unmodified and unflagged; they did not corrupt the measured trades here only because this "
        "generator deliberately placed them outside every event/hold window -- a real event window "
        "that happened to contain one would be silently traded on."
    )
    for x in X_VALUES:
        r = per_x[x]
        if not r["within_mde"]:
            findings.append(
                f"X={x}bps: recovered net {r['recovered_net_bps_mean']}bps is OUTSIDE the MDE "
                f"({r['mde_bps']}bps) of planted net {r['planted_net_bps']}bps -- pipeline failed "
                "to recover the plant (backtest/engine.py + metrics.py path)."
            )
    zero_t = per_x[0.0]["gross_t_stat"]
    if abs(zero_t) >= 1.96:
        findings.append(
            f"X=0bps tape: gross t-stat={zero_t} is significant at the 5% level -- the pipeline "
            "reported a null as non-null (false positive)."
        )
    for x in X_VALUES:
        if per_x[x]["n_other_exit_reason"]:
            findings.append(
                f"X={x}bps: {per_x[x]['n_other_exit_reason']} trade(s) closed for a reason other "
                "than time_exit (expected: every trade forced-closes at exactly HOLD_BARS) -- "
                "the 30-minute hold assumption behind the known-answer math does not hold cleanly."
            )

    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    files = {}
    for x in X_VALUES:
        xi = int(x)
        fname = f"candles_qa_taker_X{xi}bps_{date_str}.csv.gz"
        with open(out_dir / fname, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as f:
            f.write(tapes[x].to_csv(index=False).encode("utf-8"))
        files[x] = fname

    sealed = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "days": days,
        "bars_per_day": BARS_PER_DAY,
        "event_minute_of_day_utc": EVENT_MINUTE_OF_DAY,
        "event_move_mean_bps": EVENT_MOVE_MEAN_BPS,
        "event_move_sigma_bps": EVENT_MOVE_SIGMA_BPS,
        "move_threshold_bps": MOVE_THRESHOLD_BPS,
        "lookback_bars": LOOKBACK_BARS,
        "hold_bars": HOLD_BARS,
        "n_events_planted": len(base["events"]),
        "maintenance_window_utc": "19:00-19:10 daily",
        "n_maintenance_rows": n_maint,
        "n_bad_prints": n_bad,
        "cost_provenance": provenance,
        "x_values_bps": list(X_VALUES),
        "results_by_x": {str(x): per_x[x] for x in X_VALUES},
        "files": {str(x): files[x] for x in X_VALUES},
        "findings": findings,
    }
    with open(out_dir / "planted_values_sealed.json", "w", encoding="utf-8") as f:
        json.dump(sealed, f, ensure_ascii=False, sort_keys=True, indent=1)

    lines = ["# PIPELINE known-answer test — taker execution", "",
             f"Generated {sealed['generated_utc']}. seed={seed} days={days} "
             f"cost_bps={cost_bps} (source: config/constants.yaml "
             "bitflyer_fx_btc_jpy.realized_round_trip_bps, measured, midpoint of "
             f"{provenance['realized_round_trip_bps']['value']})", "",
             "| X planted (bps) | planted net (X-cost) | recovered net mean | SE | 95% CI | "
             "MDE | within MDE | n trades | gross t-stat |",
             "|---|---|---|---|---|---|---|---|---|"]
    for x in X_VALUES:
        r = per_x[x]
        lines.append(
            f"| {x} | {r['planted_net_bps']} | {r['recovered_net_bps_mean']} | "
            f"{r['recovered_net_bps_se']} | {r['recovered_net_bps_ci95']} | {r['mde_bps']} | "
            f"{'YES' if r['within_mde'] else 'NO'} | {r['n_trades']} | {r['gross_t_stat']} |"
        )
    lines += ["", f"X=0 null-as-null: gross t-stat = {zero_t} "
              f"({'non-significant, OK' if abs(zero_t) < 1.96 else 'SIGNIFICANT -- FAILS'})", "",
              "## パイプラインの欠陥 (findings)", ""]
    if findings:
        for finding in findings:
            lines.append(f"- {finding}")
    else:
        lines.append("- none beyond the documented engine-validity gap above")
    (out_dir / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {"per_x": per_x, "findings": findings, "sealed": sealed, "out_dir": str(out_dir)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--days", type=int, default=DAYS)
    ap.add_argument("--out-dir", type=str, default=None)
    args = ap.parse_args()
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "backtest_data" / f"qa_pipeline_taker_{date_str}"
    result = generate(out_dir, seed=args.seed, days=args.days)
    print(f"wrote {out_dir}")
    for x, r in result["per_x"].items():
        print(f"X={x}bps: recovered={r['recovered_net_bps_mean']}bps planted={r['planted_net_bps']}bps "
              f"within_mde={r['within_mde']} n={r['n_trades']}")
    for finding in result["findings"]:
        print(f"FINDING: {finding}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
