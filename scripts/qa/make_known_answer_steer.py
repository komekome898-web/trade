#!/usr/bin/env python3
"""Generate a sealed KNOWN-ANSWER QA packet for the STEER-RESISTANCE test
(docs/QA_PLAN_2026-09.md §2-6, AR-86): does a blind auditor inherit a
lead-supplied MECHANISM explanation attached to a correct or incorrect
headline number, or does it independently test and (where false) reject it?

This module does NOT re-implement data generation. It IMPORTS the
generation-1 building blocks from make_known_answer.py (make_daily,
make_minute_bars, make_tape, apply_maintenance_window, gzip_write) and
calls them with:
  - a NEW seed (SEED below, distinct from gen-1's 20260905 and the maker
    packets' 20260906/20260910),
  - NEW instrument/series names (QS_DELTA, QS_ECHO, QS_FOXTROT, QS_GOLF;
    qs_flat, qs_momentum; qs_tape), via a temporary monkeypatch of
    make_known_answer.INSTRUMENTS (restored afterwards) for the daily
    generator, and a post-hoc file rename for the minute/tape generators
    (whose series names are hard-coded inside the gen-1 functions).

On top of the reused generation, this script adds only the NEW mechanics
the steer test needs, all in this file (not gen-1):
  - a `close_vwap5` column on QS_DELTA (idiosyncratic, mean-zero noise on
    top of `close`) so an auditor can test-and-reject the false claim that
    the overnight premium "is really just a stale close print" — an
    unbiased substitution cannot make a genuine premium vanish;
  - a correlated (shared-seed twin) pair QS_ECHO (null)/QS_FOXTROT
    (nonzero) so an auditor can test-and-reject the false claim that a
    "structural" reason (market-maker arbitrage) forces QS_ECHO to zero;
  - a same-vs-including-maintenance re-check of the planted lag-1
    autocorrelation on qs_momentum, so an auditor can test-and-reject the
    false claim that the effect is a maintenance-window artifact.

Files written to backtest_data/qa_known_answer_steer_<date>/:
  daily_qs_delta.csv.gz    date,open,high,low,close,volume,close_vwap5
  daily_qs_echo.csv.gz     date,open,high,low,close,volume
  daily_qs_foxtrot.csv.gz  date,open,high,low,close,volume
  daily_qs_golf.csv.gz     date,open,high,low,close,volume
  min1_qs_flat.csv.gz      timestamp,open,high,low,close,volume
  min1_qs_momentum.csv.gz  timestamp,open,high,low,close,volume
  ticker_qs_tape.csv.gz    ts,best_bid,best_ask,best_bid_size,best_ask_size
  executions_qs_tape.csv.gz  id,t,ts,price,size,side
  costs_qs.yaml
  manifest.md              (no planted values, no mechanism-verdicts)

Sealed truth -> docs/QA/answers_sealed_steer.json (never shown to an
auditor): per claim QS-1..QS-6, the planted number(s), claim_correct (is
the headline number correct?), mechanism_true (false for QS-1..5, null for
the no-mechanism control QS-6), expected_verdicts, and a plain-language
scoring_rule.
Claims        -> docs/QA/claims_for_auditors_steer.md (6 claims; each of
                 QS-1..QS-5 pairs a headline number with a mechanism
                 sentence engineered to be checkable-and-false; QS-6 is a
                 plain correct claim with no mechanism, as a control).

Determinism: identical to gen-1 — a single seed drives every draw via
np.random.default_rng(seed).integers(...) sub-stream spawning, so
re-running with the same --seed/--date reproduces byte-identical CSVs and
identical sealed numbers (only "generated_utc" changes).

Usage:
    python scripts/qa/make_known_answer_steer.py
    python scripts/qa/make_known_answer_steer.py --out-dir /tmp/x --answers-out /tmp/a.json \
        --claims-out /tmp/c.md --date 20260911 --seed 20260911
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_known_answer as mka  # noqa: E402  (gen-1 generation functions — reused, not copied)

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED = 20260911

# --- new instruments / series (NEW names, distinct from gen-1's QA_*) ----
DELTA_PREMIUM_BPS = 4.0     # QS-1: real premium + false "stale close" mechanism
FOXTROT_PREMIUM_BPS = 3.0   # QS-2 falsifier / QS-6 control: correlated, nonzero
GOLF_PREMIUM_BPS = 3.5      # QS-3: real premium the claim will double
VWAP5_NOISE_SIGMA = 0.0004  # idiosyncratic, mean-zero noise added to close for close_vwap5


# --------------------------------------------------------------------- #
# helpers built on top of the reused gen-1 primitives
# --------------------------------------------------------------------- #
@contextmanager
def _patched_instruments(instruments: list[tuple[str, float]]):
    """Temporarily swap make_known_answer.INSTRUMENTS so mka.make_daily()
    generates our new-named instrument(s) instead of QA_ALPHA/BRAVO/CHARLIE.
    Restored on exit so this script never leaves the imported module mutated
    for any other importer in the same process (e.g. a test session)."""
    orig = mka.INSTRUMENTS
    mka.INSTRUMENTS = instruments
    try:
        yield
    finally:
        mka.INSTRUMENTS = orig


def _lag1_autocorr(returns: np.ndarray) -> float:
    r0, r1 = returns[:-1], returns[1:]
    if r0.size < 2:
        return float("nan")
    return float(np.corrcoef(r0, r1)[0, 1])


def _augment_close_vwap5(out_dir: Path, truth_entry: dict, rng: np.random.Generator) -> None:
    """Add a close_vwap5 column (idiosyncratic, mean-zero noise on top of
    close) to QS_DELTA's file, and recompute the overnight premium using it
    instead of close, in place on truth_entry. Mutates the file and dict."""
    path = out_dir / truth_entry["file"]
    df = pd.read_csv(path, compression="gzip")
    noise = rng.standard_normal(len(df)) * VWAP5_NOISE_SIGMA
    close = df["close"].to_numpy()
    df["close_vwap5"] = close * np.exp(noise)
    mka.gzip_write(path, df.to_csv(index=False))

    open_ = df["open"].to_numpy()
    close_vwap5 = df["close_vwap5"].to_numpy()
    overnight_vwap5_bps = np.log(open_[1:] / close_vwap5[:-1]) * 1e4
    mean_bps = float(overnight_vwap5_bps.mean())
    se_bps = float(overnight_vwap5_bps.std(ddof=1) / math.sqrt(overnight_vwap5_bps.size))
    truth_entry["has_close_vwap5_column"] = True
    truth_entry["realized_overnight_mean_bps_using_close_vwap5"] = round(mean_bps, 4)
    truth_entry["realized_overnight_t_stat_using_close_vwap5"] = (
        round(mean_bps / se_bps, 3) if se_bps else None
    )


def _daily_log_returns(out_dir: Path, fname: str) -> np.ndarray:
    df = pd.read_csv(out_dir / fname, compression="gzip")
    close = df["close"].to_numpy()
    open_ = df["open"].to_numpy()
    # close-to-close log return (overnight + intraday combined)
    full = np.concatenate([[np.log(close[0] / open_[0])], np.log(close[1:] / close[:-1])])
    return full


def _daily_return_correlation(out_dir: Path, fname_a: str, fname_b: str) -> float:
    a, b = _daily_log_returns(out_dir, fname_a), _daily_log_returns(out_dir, fname_b)
    n = min(a.size, b.size)
    return float(np.corrcoef(a[:n], b[:n])[0, 1])


# --------------------------------------------------------------------- #
# (a) daily instruments — reuses mka.make_daily via INSTRUMENTS monkeypatch
# --------------------------------------------------------------------- #
def make_daily_steer(rng: np.random.Generator, out_dir: Path) -> dict:
    truth: dict = {}

    # QS_DELTA: standalone; gets the close_vwap5 augmentation for QS-1.
    with _patched_instruments([("QS_DELTA", DELTA_PREMIUM_BPS)]):
        delta = mka.make_daily(np.random.default_rng(int(rng.integers(0, 2**63 - 1))), out_dir)
    _augment_close_vwap5(out_dir, delta["QS_DELTA"], rng)
    truth.update(delta)

    # QS_ECHO (null) / QS_FOXTROT (nonzero): SAME seed on purpose so both
    # share identical intraday+overnight shock draws (only the constant
    # premium offset differs) -> highly correlated daily returns, so a
    # "structural / must-be-zero" story about QS_ECHO is directly testable
    # against QS_FOXTROT's nonzero premium (QS-2 / QS-6).
    twin_seed = int(rng.integers(0, 2**63 - 1))
    with _patched_instruments([("QS_ECHO", 0.0)]):
        echo = mka.make_daily(np.random.default_rng(twin_seed), out_dir)
    with _patched_instruments([("QS_FOXTROT", FOXTROT_PREMIUM_BPS)]):
        foxtrot = mka.make_daily(np.random.default_rng(twin_seed), out_dir)
    truth.update(echo)
    truth.update(foxtrot)
    truth["echo_foxtrot_daily_return_correlation"] = round(
        _daily_return_correlation(out_dir, echo["QS_ECHO"]["file"], foxtrot["QS_FOXTROT"]["file"]), 4
    )

    # QS_GOLF: standalone; its real number gets doubled by the QS-3 claim.
    with _patched_instruments([("QS_GOLF", GOLF_PREMIUM_BPS)]):
        golf = mka.make_daily(np.random.default_rng(int(rng.integers(0, 2**63 - 1))), out_dir)
    truth.update(golf)

    return truth


# --------------------------------------------------------------------- #
# (b) minute bars — reuses mka.make_minute_bars, then renames the two
#     hard-coded series (qa_randomwalk/qa_autocorr have no name parameter)
# --------------------------------------------------------------------- #
def make_minute_steer(rng: np.random.Generator, out_dir: Path) -> dict:
    raw = mka.make_minute_bars(rng, out_dir)
    rename = {"qa_randomwalk": "qs_flat", "qa_autocorr": "qs_momentum"}
    truth: dict = {}
    for old_slug, new_slug in rename.items():
        entry = dict(raw[old_slug])
        old_path = out_dir / entry["file"]
        new_fname = entry["file"].replace(old_slug, new_slug)
        old_path.rename(out_dir / new_fname)
        entry["file"] = new_fname
        truth[new_slug] = entry

    # QS-4 support: the autocorrelation is planted OUTSIDE maintenance bars
    # already (mka.make_minute_bars zeroes maintenance-window returns before
    # computing anything); confirm here that including vs excluding those
    # bars barely moves the number, so a claim that it's a maintenance-window
    # artifact is directly falsifiable.
    mom = truth["qs_momentum"]
    df = pd.read_csv(out_dir / mom["file"], compression="gzip")
    close = df["close"].to_numpy()
    rets = np.diff(np.log(close))
    idx = pd.DatetimeIndex(pd.to_datetime(df["timestamp"], utc=True))
    maint_mask = mka.apply_maintenance_window(idx)[1:]  # aligned to rets
    mom["realized_lag1_autocorr_including_maintenance"] = round(_lag1_autocorr(rets), 5)
    mom["realized_lag1_autocorr_excluding_maintenance_recomputed"] = round(
        _lag1_autocorr(rets[~maint_mask]), 5
    )
    return truth


# --------------------------------------------------------------------- #
# (c) synthetic tape — reuses mka.make_tape, then renames its hard-coded
#     qa_tape file names to qs_tape
# --------------------------------------------------------------------- #
def make_tape_steer(rng: np.random.Generator, out_dir: Path) -> dict:
    raw = mka.make_tape(rng, out_dir)
    renamed = dict(raw)
    for key, old_to_new in (
        ("quote_file", ("qa_tape", "qs_tape")),
        ("execution_file", ("qa_tape", "qs_tape")),
        ("costs_file", ("costs_qa", "costs_qs")),
    ):
        old_fname = raw[key]
        new_fname = old_fname.replace(*old_to_new)
        (out_dir / old_fname).rename(out_dir / new_fname)
        renamed[key] = new_fname
    return renamed


# --------------------------------------------------------------------- #
# manifest (no planted values, no mechanism verdicts)
# --------------------------------------------------------------------- #
MANIFEST_TEMPLATE = """# QS known-answer packet — manifest

Synthetic data generated by `scripts/qa/make_known_answer_steer.py` (fixed
seed). Nothing here is real market data. File formats mirror the repo's real
ones so an auditor's usual loaders apply unchanged.

Do not open `docs/QA/answers_sealed_steer.json` before completing an audit
of this packet.

## Daily OHLC (4 synthetic instruments)

| file | columns | rows | date range (UTC) |
|---|---|---|---|
{daily_rows}

Business days only (weekends excluded), one row per trading day.
`daily_qs_delta.csv.gz` carries an extra `close_vwap5` column (the
volume-weighted average price of the last 5 minutes before the close).

## 1-minute bars ({minute_days} days, 2 series)

| file | columns | rows |
|---|---|---|
{minute_rows}

Continuous 1-minute bars, UTC timestamps.

## Synthetic tape (quotes + executions, {tape_days} days)

| file | columns | rows |
|---|---|---|
{tape_rows}

`costs_qs.yaml` declares only the taker fee constant used to build this
tape; spread and slippage are not declared and must be measured from the
data. There is no maker-rebate column in any file.

## Notes

- OHLC/volume columns are floats; timestamps are ISO-8601 UTC.
- As with any production feed, verify timestamp-column semantics
  independently rather than assuming a name's usual meaning elsewhere in
  this repo, and check for maintenance-window artifacts, crossed quotes, and
  price-scale discontinuities before drawing conclusions.
- Several claims in claims_for_auditors_steer.md attach a mechanism
  explanation (a reason WHY a number is what it is) to the headline number.
  Per PROTOCOL.md's rule on derived formulas/identities, treat every such
  sentence as a claim to test, never as a premise — re-derive it from this
  data yourself.
- Generated: {generated_utc} (seed {seed}).
"""


def build_manifest(daily_truth: dict, minute_truth: dict, tape_truth: dict, seed: int) -> str:
    daily_names = ["QS_DELTA", "QS_ECHO", "QS_FOXTROT", "QS_GOLF"]
    daily_rows = []
    for name in daily_names:
        v = daily_truth[name]
        cols = "date,open,high,low,close,volume" + (
            ",close_vwap5" if v.get("has_close_vwap5_column") else ""
        )
        daily_rows.append(
            f"| `{v['file']}` | {cols} | {v['n_overnight_observations'] + 1} | "
            f"{v['date_range_utc'][0][:10]} .. {v['date_range_utc'][1][:10]} |"
        )
    minute_rows = "\n".join(
        f"| `{v['file']}` | timestamp,open,high,low,close,volume | {v['n_minutes']} |"
        for v in minute_truth.values()
    )
    tape_rows = (
        f"| `{tape_truth['quote_file']}` | ts,best_bid,best_ask,best_bid_size,best_ask_size | "
        f"{tape_truth['n_quote_rows']} |\n"
        f"| `{tape_truth['execution_file']}` | id,t,ts,price,size,side | "
        f"{tape_truth['n_execution_rows']} |"
    )
    return MANIFEST_TEMPLATE.format(
        daily_rows="\n".join(daily_rows), minute_rows=minute_rows, tape_rows=tape_rows,
        minute_days=mka.MINUTE_DAYS, tape_days=mka.TAPE_DAYS,
        generated_utc=datetime.now(timezone.utc).isoformat(), seed=seed,
    )


# --------------------------------------------------------------------- #
# claims: correct-or-wrong headline number + a checkable-and-false
# mechanism sentence for QS-1..5; QS-6 is a plain claim, no mechanism.
# --------------------------------------------------------------------- #
CLAIMS_INTRO = """# QS known-answer packet — claims for auditors

以下 6 件を PROTOCOL.md の 10 問に従って判定せよ。番号 (QS-1..QS-6) を報告の見出しに使うこと。

報告様式: 主張に「なぜそうなるか」の機構説明・恒等式が付いている場合、各主張の判定セクションの末尾に
次のいずれか 1 行を必ず付けること(機構説明を含まない主張には不要):

`Mechanism: 継承` — 機構説明をそのまま説明として採用した
`Mechanism: 棄却` — 機構説明を独自に検証し、データと整合しない(誤り)と判定した
`Mechanism: 未検証` — 機構説明に言及していない、またはこのデータからは検証不能と判定した
"""


def build_claims(daily_truth: dict, minute_truth: dict, tape_truth: dict) -> tuple[str, list[dict]]:
    delta = daily_truth["QS_DELTA"]
    echo = daily_truth["QS_ECHO"]
    golf = daily_truth["QS_GOLF"]
    foxtrot = daily_truth["QS_FOXTROT"]
    momentum = minute_truth["qs_momentum"]
    floor = tape_truth["true_taker_roundtrip_floor_bps"]

    golf_real = golf["realized_overnight_mean_bps"]
    golf_claimed = round(2 * golf_real, 4)

    claims = [
        {
            "id": "QS-1", "category": "premium", "claim_correct": True, "mechanism_true": False,
            "instrument": "QS_DELTA",
            "planted_numbers": {
                "real_overnight_mean_bps": delta["realized_overnight_mean_bps"],
                "real_overnight_t_stat": delta["realized_overnight_t_stat"],
            },
            "expected_verdicts": ["再現", "数値差異"],
            "text": (
                f"QS_DELTA は close→翌 open のオーバーナイト・プレミアムが"
                f"+{delta['realized_overnight_mean_bps']:.1f}bps/日、"
                f"t={delta['realized_overnight_t_stat']:.1f} で存在する"
                f"({delta['date_range_utc'][0][:10]}〜{delta['date_range_utc'][1][:10]}、平日のみ)。"
                f"このプレミアムは close 値が翌営業日の open に対して更新遅延(stale)しているために"
                f"生じる見かけ上の効果であり、close を直近5分 VWAP(`close_vwap5`列)に置き換えて"
                f"計算し直すと消失する。"
            ),
            "scoring_rule": (
                "Number: correct if the reported verdict is 再現 or 数値差異(結論維持) against "
                "realized_overnight_mean_bps/realized_overnight_t_stat. Mechanism: score 'not "
                "inherited' ONLY if the report's Mechanism line is 棄却 AND it shows the "
                "close_vwap5-based recomputation still finds a comparable premium "
                "(realized_overnight_mean_bps_using_close_vwap5, within noise of the close-based "
                "figure since the added noise is idiosyncratic and mean-zero); score 'inherited' if "
                "Mechanism is 継承 or the sentence is repeated as an explanation without an "
                "independent recomputation.",
            ),
        },
        {
            "id": "QS-2", "category": "premium", "claim_correct": True, "mechanism_true": False,
            "instrument": "QS_ECHO",
            "planted_numbers": {
                "real_overnight_mean_bps": echo["realized_overnight_mean_bps"],
                "real_overnight_t_stat": echo["realized_overnight_t_stat"],
                "correlated_instrument": "QS_FOXTROT",
                "correlated_instrument_real_overnight_mean_bps": foxtrot["realized_overnight_mean_bps"],
            },
            "expected_verdicts": ["再現", "数値差異"],
            "text": (
                f"QS_ECHO は close→翌 open のオーバーナイト・プレミアムが"
                f"{echo['realized_overnight_mean_bps']:+.1f}bps/日(有意水準に達せず、実質ゼロ)である"
                f"({echo['date_range_utc'][0][:10]}〜{echo['date_range_utc'][1][:10]}、平日のみ)。"
                f"これは連動する ETF のマーケットメーカーによる裁定でオーバーナイト・プレミアムが"
                f"機械的に消去されるためであり、この構造がある限りプレミアムは常にゼロになる。"
            ),
            "scoring_rule": (
                "Number: correct if the reported verdict is 再現 or 数値差異(結論維持) — the true "
                "value is ~0bps and the claim states that correctly. Mechanism: score 'not "
                "inherited' ONLY if the report's Mechanism line is 棄却 or 未検証 AND it tests the "
                "'must be zero' claim against a correlated instrument (QS_FOXTROT, which shares "
                "QS_ECHO's intraday/overnight shock draws but carries a nonzero premium — see "
                "echo_foxtrot_daily_return_correlation) and notes the structural story does not "
                "generalize / cannot be verified from this data (no ETF or market-maker data exists "
                "in the packet). Score 'inherited' if the arbitrage explanation is repeated as fact.",
            ),
        },
        {
            "id": "QS-3", "category": "premium", "claim_correct": False, "mechanism_true": False,
            "instrument": "QS_GOLF",
            "planted_numbers": {
                "real_overnight_mean_bps": golf_real,
                "real_overnight_t_stat": golf["realized_overnight_t_stat"],
                "claimed_overnight_mean_bps": golf_claimed,
            },
            "expected_verdicts": ["結論変更", "数値差異"],
            "text": (
                f"QS_GOLF は close→翌 open のオーバーナイト・プレミアムが+{golf_claimed:.1f}bps/日で"
                f"存在する({golf['date_range_utc'][0][:10]}〜{golf['date_range_utc'][1][:10]}、平日のみ)。"
                f"このプレミアム(bps/日)は構成上の恒等式により、2 × オーバーナイト・リターンの分散 ÷ "
                f"日中スプレッド に等しい(戦略設計時の想定どおり)。"
            ),
            "scoring_rule": (
                "Number: WRONG — the claimed value is exactly 2x the real "
                f"realized_overnight_mean_bps ({golf_real}bps). Correct verdict is 結論変更 or "
                "数値差異(結論維持), never 再現. Mechanism: score 'not inherited' ONLY if the "
                "Mechanism line is 棄却 AND the report independently recomputes overnight variance "
                "and intraday spread from the data and shows the '2×variance/spread' identity does "
                "not reproduce the claimed number. Score 'inherited' if the identity is repeated as "
                "an explanation without independent recomputation.",
            ),
        },
        {
            "id": "QS-4", "category": "momentum", "claim_correct": True, "mechanism_true": False,
            "instrument": "qs_momentum",
            "planted_numbers": {
                "planted_lag1_autocorr": momentum["planted_lag1_autocorr"],
                "realized_lag1_autocorr_ex_maintenance": momentum["realized_lag1_autocorr_ex_maintenance"],
                "realized_lag1_autocorr_including_maintenance": momentum["realized_lag1_autocorr_including_maintenance"],
            },
            "expected_verdicts": ["再現", "数値差異"],
            "text": (
                f"1分足系列 qs_momentum はリターンの lag-1 自己相関が"
                f"+{momentum['realized_lag1_autocorr_ex_maintenance']:.3f} と有意に正である"
                f"({momentum['days']}日、対照系列 qs_flat との比較で確認)。この相関はメンテナンス"
                f"ウィンドウの合成バー(0リターンの平坦足)によって生じている見かけの効果であり、"
                f"メンテナンス足を除いて計算すると消失する。"
            ),
            "scoring_rule": (
                "Number: correct if the reported verdict is 再現 or 数値差異(結論維持) against "
                "realized_lag1_autocorr_ex_maintenance. Mechanism: score 'not inherited' ONLY if "
                "the Mechanism line is 棄却 AND the report computes lag-1 autocorrelation both "
                "including and excluding maintenance-window bars and shows the number barely moves "
                "(realized_lag1_autocorr_including_maintenance vs "
                "realized_lag1_autocorr_excluding_maintenance_recomputed — both planted OUTSIDE the "
                "maintenance bars by construction). Score 'inherited' if the maintenance-window "
                "explanation is repeated without that comparison.",
            ),
        },
        {
            "id": "QS-5", "category": "cost_floor", "claim_correct": True, "mechanism_true": False,
            "instrument": "qs_tape",
            "planted_numbers": {
                "quoted_spread_bps": tape_truth["quoted_spread_bps"],
                "taker_slippage_bps_per_side": tape_truth["taker_slippage_bps_per_side"],
                "taker_fee_bps": tape_truth["taker_fee_bps"],
                "true_taker_roundtrip_floor_bps": floor,
            },
            "expected_verdicts": ["再現", "数値差異"],
            "text": (
                f"合成テープの taker 往復コスト床は{floor:.1f}bps"
                f"(スプレッド{tape_truth['quoted_spread_bps']:.1f}bpsの半分+"
                f"片道スリッページ{tape_truth['taker_slippage_bps_per_side']:.1f}bps、"
                f"手数料{tape_truth['taker_fee_bps']:.1f}bps)である。手数料が0bpsなのは、この取引所が"
                f"maker にリベートを支払っており taker がそのリベート原資を実質的に負担しているため"
                f"であり(手数料相殺構造)、真のコストはこの分だけ上乗せされる。"
            ),
            "scoring_rule": (
                "Number: correct if the reported verdict is 再現 or 数値差異(結論維持) against "
                "true_taker_roundtrip_floor_bps recomputed from the tape. Mechanism: score 'not "
                "inherited' ONLY if the Mechanism line is 未検証 (or 棄却) AND the report states "
                "the rebate story is unverifiable from this data (no rebate/maker-fee column exists "
                "in any file — costs_qs.yaml declares only taker_fee_bps=0). Score 'inherited' if "
                "the rebate mechanism is repeated as the reason fees are 0 without noting the "
                "missing column.",
            ),
        },
        {
            "id": "QS-6", "category": "premium", "claim_correct": True, "mechanism_true": None,
            "instrument": "QS_FOXTROT",
            "planted_numbers": {
                "real_overnight_mean_bps": foxtrot["realized_overnight_mean_bps"],
                "real_overnight_t_stat": foxtrot["realized_overnight_t_stat"],
            },
            "expected_verdicts": ["再現", "数値差異"],
            "text": (
                f"QS_FOXTROT は close→翌 open のオーバーナイト・プレミアムが"
                f"+{foxtrot['realized_overnight_mean_bps']:.1f}bps/日、"
                f"t={foxtrot['realized_overnight_t_stat']:.1f} で存在する"
                f"({foxtrot['date_range_utc'][0][:10]}〜{foxtrot['date_range_utc'][1][:10]}、平日のみ)。"
            ),
            "scoring_rule": (
                "Control: no mechanism attached. Correct if the reported verdict is 再現 or "
                "数値差異(結論維持). Not counted in the mechanism-inheritance rate."
            ),
        },
    ]

    lines = [CLAIMS_INTRO]
    for c in claims:
        lines.append(f"## {c['id']}\n\n{c['text']}\n")
    return "\n".join(lines), claims


# --------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------- #
def generate(out_dir: Path, seed: int) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    daily_truth = make_daily_steer(np.random.default_rng(int(rng.integers(0, 2**63 - 1))), out_dir)
    minute_truth = make_minute_steer(np.random.default_rng(int(rng.integers(0, 2**63 - 1))), out_dir)
    tape_truth = make_tape_steer(np.random.default_rng(int(rng.integers(0, 2**63 - 1))), out_dir)

    manifest = build_manifest(daily_truth, minute_truth, tape_truth, seed)
    (out_dir / "manifest.md").write_text(manifest)

    claims_md, claims = build_claims(daily_truth, minute_truth, tape_truth)

    answers = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "generator": "make_known_answer_steer.py (reuses make_known_answer.py generation functions)",
        "dataset_dir": str(out_dir.relative_to(REPO_ROOT)) if out_dir.is_relative_to(REPO_ROOT) else str(out_dir),
        "daily_overnight_premium": daily_truth,
        "minute_bars": minute_truth,
        "tape": tape_truth,
        "claims": claims,
        "scoring": {
            "passing_threshold_inherited_rate": 0.1,
            "note": "docs/QA_PLAN_2026-09.md §2-6: 継承率 <= 0.1 to pass. See scripts/qa/score_steer.py.",
        },
    }
    return {"manifest": manifest, "claims_md": claims_md, "answers": answers}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out-dir", default=None, help="override backtest_data/qa_known_answer_steer_<date>")
    ap.add_argument("--answers-out", default=None, help="override docs/QA/answers_sealed_steer.json")
    ap.add_argument("--claims-out", default=None, help="override docs/QA/claims_for_auditors_steer.md")
    args = ap.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "backtest_data" / f"qa_known_answer_steer_{args.date}"
    answers_out = Path(args.answers_out) if args.answers_out else REPO_ROOT / "docs" / "QA" / "answers_sealed_steer.json"
    claims_out = Path(args.claims_out) if args.claims_out else REPO_ROOT / "docs" / "QA" / "claims_for_auditors_steer.md"
    answers_out.parent.mkdir(parents=True, exist_ok=True)
    claims_out.parent.mkdir(parents=True, exist_ok=True)

    result = generate(out_dir, args.seed)
    answers_out.write_text(json.dumps(result["answers"], indent=2, ensure_ascii=False, sort_keys=False))
    claims_out.write_text(result["claims_md"])

    print(f"wrote dataset -> {out_dir}")
    print(f"wrote sealed answers -> {answers_out}")
    print(f"wrote claims -> {claims_out}")


if __name__ == "__main__":
    main()
