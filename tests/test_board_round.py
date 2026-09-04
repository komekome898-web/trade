"""Tests for scripts/run_board_round.py and scripts/judge_board_round.py
(docs/PREREG_board_round.md, Round 17)."""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_board_round as rbr  # noqa: E402
import judge_board_round as jbr  # noqa: E402

PRODUCT = "FX_BTC_JPY"
SNAP_CH = f"lightning_board_snapshot_{PRODUCT}"
DIFF_CH = f"lightning_board_{PRODUCT}"
EXEC_CH = f"lightning_executions_{PRODUCT}"


def levels(*pairs):
    return [{"price": float(p), "size": float(s)} for p, s in pairs]


def write_stream(path, records):
    with gzip.open(path, "wt") as fh:
        for rts, channel, message in records:
            fh.write(json.dumps({
                "rts": rts,
                "m": {"jsonrpc": "2.0", "method": "channelMessage",
                      "params": {"channel": channel, "message": message}},
            }) + "\n")


# ==========================================================================
# run_board_round
# ==========================================================================
def test_run_board_round_bins_and_gap(tmp_path):
    ws_dir = tmp_path / "data" / "ws"
    ws_dir.mkdir(parents=True)

    snapshot_msg = {
        "mid_price": 1_000_000.0,
        "bids": levels((999_900, 1.0), (999_800, 2.0), (999_000, 4.0)),
        "asks": levels((1_000_100, 1.0), (1_000_200, 2.0), (1_001_000, 4.0)),
    }
    diff1 = {"bids": levels((999_900, 1.5)), "asks": []}
    exec1 = [
        {"side": "BUY", "price": 1_000_100.0, "size": 0.05, "exec_date": "x"},
        {"side": "SELL", "price": 999_900.0, "size": 0.12, "exec_date": "x"},
    ]
    diff2 = {"bids": [], "asks": levels((1_000_200, 1.0))}
    diff3 = {"bids": levels((999_900, 2.0)), "asks": []}

    records = [
        (0.0, SNAP_CH, snapshot_msg),
        (2.0, DIFF_CH, diff1),
        (3.0, EXEC_CH, exec1),
        (6.0, DIFF_CH, diff2),
        (200.0, DIFF_CH, diff3),   # 194s after rts=6 -> gap > 60s
    ]
    write_stream(ws_dir / f"{PRODUCT}_20260101_000000.jsonl.gz", records)

    rows, coverage = rbr.build(ws_dir)
    df = pd.DataFrame(rows, columns=rbr.COLUMNS)

    # bin 0: ts=0, holds the snapshot + diff1 + the two executions
    row0 = df[df["ts"] == 0.0].iloc[0]
    assert row0["n_board_updates"] == 2          # snapshot + diff1
    assert row0["best_bid_size"] == pytest.approx(1.5)   # diff1 overrides
    assert row0["best_ask_size"] == pytest.approx(1.0)
    # depth within 5bps of mid=1,000,000 (band 999,500..1,000,500):
    # bids 999900(1.5)+999800(2.0)=3.5 (999000 excluded), asks 1000100(1.0)+1000200(2.0)=3.0
    assert row0["bid_depth_5bps"] == pytest.approx(3.5)
    assert row0["ask_depth_5bps"] == pytest.approx(3.0)
    assert row0["imb_5bps"] == pytest.approx((3.5 - 3.0) / (3.5 + 3.0))
    assert row0["imb_top"] == pytest.approx((1.5 - 1.0) / (1.5 + 1.0))
    assert row0["spread_bps"] == pytest.approx(200.0 / 1_000_000 * 1e4)
    assert row0["n_trades"] == 2
    assert row0["vol_buy"] == pytest.approx(0.05)
    assert row0["vol_sell"] == pytest.approx(0.12)
    assert row0["n_large"] == 1
    assert row0["vol_large"] == pytest.approx(0.12)
    assert row0["max_trade_size"] == pytest.approx(0.12)

    # bin 1 (ts=5): only diff2, no trades
    row1 = df[df["ts"] == 5.0].iloc[0]
    assert row1["n_board_updates"] == 1
    assert row1["n_trades"] == 0
    assert row1["best_ask_size"] == pytest.approx(1.0)

    # the gap (last_rts=6 .. rts=200) is real and > 60s: bins between are
    # simply absent, and it is recorded in coverage.
    assert 10.0 not in set(df["ts"])
    assert len(coverage["gaps_over_60s"]) == 1
    gap = coverage["gaps_over_60s"][0]
    assert gap["duration_sec"] == pytest.approx(194.0)

    # bin 40 (ts=200) resumes on the far side of the gap
    row40 = df[df["ts"] == 200.0].iloc[0]
    assert row40["n_board_updates"] == 1

    assert coverage["total_bins"] == 41   # bins 0..40 inclusive
    assert coverage["missing_bins"] == coverage["total_bins"] - len(df)
    assert coverage["missing_bins"] > 0


def test_run_board_round_cli_writes_files(tmp_path):
    ws_dir = tmp_path / "data" / "ws"
    ws_dir.mkdir(parents=True)
    snapshot_msg = {
        "mid_price": 1_000_000.0,
        "bids": levels((999_900, 1.0)),
        "asks": levels((1_000_100, 1.0)),
    }
    write_stream(ws_dir / f"{PRODUCT}_20260101_000000.jsonl.gz",
                [(0.0, SNAP_CH, snapshot_msg)])

    # exercise via the real CLI entry point
    old_argv = sys.argv
    try:
        sys.argv = ["run_board_round.py", "--root", str(tmp_path)]
        rc = rbr.main()
    finally:
        sys.argv = old_argv
    assert rc == 0
    assert (tmp_path / "data" / "board_round" / "series_5s.csv.gz").exists()
    assert (tmp_path / "data" / "board_round" / "coverage.json").exists()


# ==========================================================================
# judge_board_round -- helpers and section logic
# ==========================================================================
def _make_series(n_bins=200, start=0, seed=0):
    """A synthetic 5s-bin series with a mildly informative imb_5bps signal:
    mid drifts in the direction of the current imbalance sign, and the rest
    of the columns are filled with harmless small values."""
    rng = np.random.default_rng(seed)
    bins = np.arange(start, start + n_bins)
    imb = rng.uniform(-1, 1, n_bins)
    mid = np.empty(n_bins)
    mid[0] = 1_000_000.0
    for i in range(1, n_bins):
        mid[i] = mid[i - 1] * (1 + 0.0005 * imb[i - 1] / 100.0)
    ts = pd.to_datetime(bins * 5, unit="s", utc=True)
    df = pd.DataFrame({
        "ts": ts,
        "mid": mid,
        "spread_bps": 2.0,
        "best_bid_size": 1.0,
        "best_ask_size": 1.0,
        "bid_depth_5bps": 3.0,
        "ask_depth_5bps": 3.0,
        "imb_top": imb,
        "imb_5bps": imb,
        "n_board_updates": 1,
        "n_trades": 1,
        "vol_buy": 0.01,
        "vol_sell": 0.01,
        "n_large": 0,
        "vol_large": 0.0,
        "max_trade_size": 0.01,
    })
    df["bin_idx"] = bins
    df["hour"] = df["ts"].dt.hour + df["ts"].dt.minute / 60.0
    return df


def test_decile_labels_monotone_and_range():
    x = np.arange(100, dtype=float)
    d = jbr.decile_labels(x)
    assert d.min() == 1 and d.max() == 10
    # monotone: label is non-decreasing in x
    assert np.all(np.diff(d) >= 0)


def test_bi_decile_sign_reflects_engineered_drift():
    df = _make_series(n_bins=3000, seed=1)
    res = jbr.compute_bi(df)
    table30 = res["decile_tables"]["imb_5bps"][30]
    # the series was built so higher imb_5bps precedes a higher forward
    # return: decile 10 should beat decile 1 on average.
    assert table30[10] > table30[1]


def test_nonoverlap_mask_enforces_spacing():
    bin_idx = np.arange(0, 50)
    candidate = np.ones(50, dtype=bool)
    kept = jbr.nonoverlap_mask(bin_idx, candidate, stride_bins=6)
    kept_bins = bin_idx[kept]
    assert len(kept_bins) > 1
    assert np.all(np.diff(kept_bins) >= 6)


def test_vr_cells_are_four_and_nonoverlapping_per_hold():
    df = _make_series(n_bins=2000, seed=2)
    res = jbr.compute_vr(df)
    assert len(res["cells"]) == 4
    assert {c["regime"] for c in res["cells"]} == {"quiet(vr t1)", "turbulent(vr t3)"}
    assert {c["h"] for c in res["cells"]} == {30, 60}


def test_tp_event_detection_after_quiet_period():
    n_bins = 500
    bins = np.arange(n_bins)
    mid = np.full(n_bins, 1_000_000.0)
    # a burst just after 40 minutes (480 bins) of flat (quiet) market: mid
    # jumps 25bps over 60s (12 bins) starting at bin 400.
    burst_start = 400
    for i in range(burst_start, burst_start + 12):
        mid[i] = 1_000_000.0 * (1 + 0.0025 * (i - burst_start) / 12.0)
    for i in range(burst_start + 12, n_bins):
        mid[i] = mid[burst_start + 11]

    ts = pd.to_datetime(bins * 5, unit="s", utc=True)
    df = pd.DataFrame({"ts": ts, "mid": mid})
    df["bin_idx"] = bins
    df["hour"] = df["ts"].dt.hour + df["ts"].dt.minute / 60.0

    burst, events = jbr.detect_burst_and_events(df)
    assert burst.any()
    assert len(events) == 1
    # the event fires at the first bin where the trailing-60s displacement
    # first reaches 20bps, i.e. >= burst_start (not before).
    assert events[0] >= burst_start


def test_tp_event_detection_respects_30min_quiet_requirement():
    # two bursts 10 minutes apart (120 bins): only the FIRST should count as
    # an event; the second is inside the 30-minute non-recurrence window and
    # so is suppressed even though the burst condition itself re-triggers.
    n_bins = 400
    bins = np.arange(n_bins)
    mid = np.full(n_bins, 1_000_000.0)

    def bump(start):
        for i in range(start, start + 12):
            mid[i] = mid[i - 1] * 1.00003 if i > 0 else mid[i]
        # force a clean 25bps ramp regardless of prior state
        base = mid[start - 1] if start > 0 else mid[0]
        for i in range(start, start + 12):
            mid[i] = base * (1 + 0.0025 * (i - start + 1) / 12.0)
        for i in range(start + 12, n_bins):
            mid[i] = mid[start + 11]

    bump(100)
    bump(220)   # 120 bins = 600s = 10 min after the first burst window

    ts = pd.to_datetime(bins * 5, unit="s", utc=True)
    df = pd.DataFrame({"ts": ts, "mid": mid})
    df["bin_idx"] = bins
    df["hour"] = df["ts"].dt.hour + df["ts"].dt.minute / 60.0

    _, events = jbr.detect_burst_and_events(df)
    assert len(events) == 1


def test_auc_perfectly_separating_feature_is_one():
    pos = [5.0, 6.0, 7.0, 8.0]
    neg = [1.0, 2.0, 3.0, 4.0]
    assert jbr.auc_score(pos, neg) == pytest.approx(1.0)


def test_auc_no_separation_is_half():
    rng = np.random.default_rng(0)
    x = rng.normal(size=2000)
    pos = x[:1000]
    neg = x[1000:]
    assert jbr.auc_score(pos, neg) == pytest.approx(0.5, abs=0.05)


def test_gmo_not_reached_below_day_bar(tmp_path):
    vdir = tmp_path / "data" / "venues"
    vdir.mkdir(parents=True)
    for d in ("20260827", "20260828", "20260829", "20260830", "20260831"):
        with gzip.open(vdir / f"quotes_{d}.csv.gz", "wt") as fh:
            fh.write("ts_utc,venue,pair,bid,ask,last\n")

    res = jbr.compute_gmo(tmp_path)
    assert res["reached"] is False
    assert res["day_count"] == 5


# ==========================================================================
# QC amendment (2026-09-04): post-maintenance crossed/garbage book
# ==========================================================================
def _clean_full_series(n_bins, seed=7):
    """A fully-featured, all-valid synthetic series (every column
    apply_qc/compute_tp touch), spanning the maintenance window so the
    exclusion clause has something to bite on."""
    rng = np.random.default_rng(seed)
    bins = np.arange(n_bins)
    mid = 1_000_000.0 + np.cumsum(rng.normal(0, 5, n_bins))
    # 12:00 UTC start, far from the 19:00-19:15 maintenance window -- tests
    # that need to exercise that window set df["hour"] explicitly instead.
    ts = pd.to_datetime(pd.Timestamp("2026-09-01T12:00:00Z") + bins * pd.Timedelta("5s"))
    df = pd.DataFrame({
        "ts": ts,
        "mid": mid,
        "spread_bps": rng.uniform(1.0, 3.0, n_bins),
        "best_bid_size": rng.uniform(0.5, 2.0, n_bins),
        "best_ask_size": rng.uniform(0.5, 2.0, n_bins),
        "bid_depth_5bps": rng.uniform(1.0, 4.0, n_bins),
        "ask_depth_5bps": rng.uniform(1.0, 4.0, n_bins),
        "imb_top": rng.uniform(-1, 1, n_bins),
        "imb_5bps": rng.uniform(-1, 1, n_bins),
        "n_board_updates": 1,
        "n_trades": 1,
        "vol_buy": 0.01,
        "vol_sell": 0.01,
        "n_large": 0,
        "vol_large": 0.0,
        "max_trade_size": 0.01,
    })
    df["bin_idx"] = bins
    df["hour"] = df["ts"].dt.hour + df["ts"].dt.minute / 60.0
    return df


def test_qc_mask_flags_each_reason_and_maintenance_window():
    df = _clean_full_series(20)
    df.loc[3, "spread_bps"] = -1.0          # crossed
    df.loc[4, "spread_bps"] = 999.0         # far too wide
    df.loc[5, "bid_depth_5bps"] = 0.0
    df.loc[6, "ask_depth_5bps"] = 0.0
    df.loc[7, "best_bid_size"] = 0.0
    df.loc[8, "best_ask_size"] = -0.01
    df.loc[9, "mid"] = np.nan
    df.loc[10, "hour"] = 19.05              # inside 19:00-19:15 maintenance

    valid, counts = jbr.compute_qc_mask(df)
    assert counts["spread_le_0"] == 1
    assert counts["spread_gt_50bps"] == 1
    assert counts["bid_depth_5bps_zero"] == 1
    assert counts["ask_depth_5bps_zero"] == 1
    assert counts["best_bid_size_le_0"] == 1
    assert counts["best_ask_size_le_0"] == 1
    assert counts["mid_not_finite"] == 1
    assert counts["maintenance_window"] == 1
    assert counts["invalid_total"] == 7           # rows 3..9, not row 10
    assert counts["excluded_total"] == 8           # + row 10
    for i in (3, 4, 5, 6, 7, 8, 9, 10):
        assert not valid[i]
    for i in (0, 1, 2, 11, 12):
        assert valid[i]


def test_apply_qc_nans_mid_and_breaks_forward_return_like_a_gap():
    df = _clean_full_series(60)
    bad_bin = 30
    df.loc[bad_bin, "spread_bps"] = -1.0
    masked, counts = jbr.apply_qc(df)
    assert np.isnan(masked.loc[bad_bin, "mid"])
    assert np.isnan(masked.loc[bad_bin, "imb_5bps"])
    assert masked.loc[bad_bin, "valid"] == False  # noqa: E712
    assert counts["invalid_total"] == 1

    # a forward return spanning the invalid bin is NaN, exactly like a gap
    bin_idx = masked["bin_idx"].to_numpy()
    mid = masked["mid"].to_numpy(float)
    fwd = jbr.forward_value(mid, bin_idx, 0)
    assert np.isnan(fwd[bad_bin])


def test_tp_drops_event_whose_prewindow_touches_an_invalid_bin():
    n_bins = 700
    df = _clean_full_series(n_bins, seed=11)
    burst_start = 500
    base = df.loc[burst_start - 1, "mid"]
    for i in range(burst_start, burst_start + 12):
        df.loc[i, "mid"] = base * (1 + 0.0025 * (i - burst_start + 1) / 12.0)
    for i in range(burst_start + 12, n_bins):
        df.loc[i, "mid"] = df.loc[burst_start + 11, "mid"]

    # baseline: the event survives on the untouched series
    clean, _ = jbr.apply_qc(df.copy())
    res_clean = jbr.compute_tp(clean)
    assert res_clean["n_events"] == 1

    # corrupt one bin 100s before t0 -- inside the QC amendment's
    # [t0-180s, t0] drop range -- and confirm the event is now dropped
    contaminated = df.copy()
    contaminated.loc[burst_start - 20, "spread_bps"] = -1.0
    masked, qc_counts = jbr.apply_qc(contaminated)
    assert qc_counts["invalid_total"] == 1
    res = jbr.compute_tp(masked)
    assert res["n_events"] == 0


def test_gmo_day_count_prefers_shared_paper_logs(tmp_path):
    local = tmp_path / "data" / "venues"
    shared = tmp_path / "paper_logs" / "venues"
    local.mkdir(parents=True)
    shared.mkdir(parents=True)
    for d in ("20260101",):
        with gzip.open(local / f"quotes_{d}.csv.gz", "wt") as fh:
            fh.write("ts_utc,venue,pair,bid,ask,last\n")
    for d in ("20260101", "20260102", "20260103"):
        with gzip.open(shared / f"quotes_{d}.csv.gz", "wt") as fh:
            fh.write("ts_utc,venue,pair,bid,ask,last\n")

    count, vdir = jbr.gmo_day_count(tmp_path)
    assert count == 3
    assert vdir == shared
