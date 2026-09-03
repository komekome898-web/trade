"""Tests for scripts/research_clock_burst.py (S12 clock-burst-30m judgment).

Covers: 60s/20bps trigger detection, the 12:30-15:00 UTC window gate,
flat-only episode-start semantics, exact 30-minute settlement, and the
n<30 safety valve (prints exactly one line, no statistics).

Synthetic tape convention: two prints per second (a taker BUY at .1s and a
taker SELL at .2s, same price) so the bounce-free mid equals the price
path exactly and is trivial to reason about.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import research_clock_burst as m  # noqa: E402

D0 = 20_400 * 86400  # an arbitrary UTC-midnight epoch, comfortably post-fresh-cutoff


def synth_prints(t0: int, segments: list[tuple[int, float]]):
    """segments = [(duration_s, price), ...] consecutive price levels
    starting at integer epoch second t0. Returns (t, price, buy) arrays."""
    t_list, p_list, b_list = [], [], []
    sec = t0
    for dur, price in segments:
        for _ in range(dur):
            t_list.append(sec + 0.1)
            p_list.append(price)
            b_list.append(True)
            t_list.append(sec + 0.2)
            p_list.append(price)
            b_list.append(False)
            sec += 1
    return (np.asarray(t_list, dtype=float), np.asarray(p_list, dtype=float),
            np.asarray(b_list, dtype=bool))


def iso_to_epoch(iso: str) -> float:
    return float((pd.Timestamp(iso) - m.EPOCH) / pd.Timedelta("1s"))


# --------------------------------------------------------------------------
# 1. trigger detection (60s window, 20bps threshold)
# --------------------------------------------------------------------------
def test_trigger_fires_on_20bps_60s_displacement_and_reports_side():
    t0 = D0 + 12 * 3600  # arbitrary; window gate is not exercised here
    p0 = 10_000_000.0
    up = p0 * 1.0030  # +30bps, well above the 20bps threshold
    t, price, buy = synth_prints(t0, [(65, p0), (65, up)])
    grid = m.build_mid_grid(t, price, buy)
    idx, side = m.find_triggers(grid["gm"], grid["valid_from"])
    assert len(idx) > 0
    # the earliest firing must be the first second the 60s-back mid is
    # still pre-jump and the current mid is post-jump.
    first_fire_price = grid["gm"][idx[0]]
    assert first_fire_price == up
    assert side[0] == 1  # upward displacement -> momentum long


def test_trigger_does_not_fire_below_threshold():
    t0 = D0 + 12 * 3600
    p0 = 10_000_000.0
    small_up = p0 * 1.0010  # +10bps, below the 20bps threshold
    t, price, buy = synth_prints(t0, [(65, p0), (65, small_up)])
    grid = m.build_mid_grid(t, price, buy)
    idx, side = m.find_triggers(grid["gm"], grid["valid_from"])
    assert len(idx) == 0


def test_trigger_downward_displacement_reports_short_side():
    t0 = D0 + 12 * 3600
    p0 = 10_000_000.0
    down = p0 * 0.9970  # -30bps
    t, price, buy = synth_prints(t0, [(65, p0), (65, down)])
    grid = m.build_mid_grid(t, price, buy)
    idx, side = m.find_triggers(grid["gm"], grid["valid_from"])
    assert len(idx) > 0
    assert side[0] == -1


# --------------------------------------------------------------------------
# 2. window gate (UTC 12:30-15:00)
# --------------------------------------------------------------------------
def test_window_gate_blocks_entry_outside_1230_1500_utc():
    t0 = int(iso_to_epoch("2026-08-26T08:00:00Z"))  # well outside the window
    p0 = 10_000_000.0
    up = p0 * 1.0030
    t, price, buy = synth_prints(t0, [(65, p0), (65, up)])
    grid = m.build_mid_grid(t, price, buy)
    idx, side = m.find_triggers(grid["gm"], grid["valid_from"])
    assert len(idx) > 0  # the trigger itself still fires...
    result = m.build_episodes(grid["gm"], grid["g0"], idx, side, t, price, t[-1])
    assert result["episodes"] == []  # ...but never becomes a trade
    assert result["n_ignored_holding"] == 0  # it is gated out, not "ignored while holding"


def test_window_gate_allows_entry_inside_1230_1500_utc():
    t0 = int(iso_to_epoch("2026-08-26T12:35:00Z"))
    p0 = 10_000_000.0
    up = p0 * 1.0030
    # enough post-trigger data (>1800s + exit guard) for the episode to settle
    t, price, buy = synth_prints(t0, [(65, p0), (2000, up)])
    grid = m.build_mid_grid(t, price, buy)
    idx, side = m.find_triggers(grid["gm"], grid["valid_from"])
    result = m.build_episodes(grid["gm"], grid["g0"], idx, side, t, price, t[-1])
    assert len(result["episodes"]) == 1
    tod = m.time_of_day_s(result["episodes"][0]["t_sig"])
    assert m.CLOCK_LO_S <= tod < m.CLOCK_HI_S


# --------------------------------------------------------------------------
# 3. flat-only entry + 30-minute settlement
# --------------------------------------------------------------------------
def test_flat_only_ignores_refires_then_opens_new_episode_once_flat():
    t0 = int(iso_to_epoch("2026-08-26T12:35:00Z"))
    p0 = 10_000_000.0
    up = p0 * 1.0030     # first sustained displacement (many consecutive firings)
    down = p0 * 0.9970   # second displacement, opposite side, after the first exits
    # 65s baseline, then a sustained "up" run (many re-firings while
    # flat->held, plenty of margin past the first position's 1800s exit),
    # then a flat stretch, then a fresh "down" displacement that must open
    # a second episode -- itself followed by enough data to settle too.
    t, price, buy = synth_prints(t0, [
        (65, p0), (2200, up), (65, p0), (2200, down),
    ])
    grid = m.build_mid_grid(t, price, buy)
    idx, side = m.find_triggers(grid["gm"], grid["valid_from"])
    result = m.build_episodes(grid["gm"], grid["g0"], idx, side, t, price, t[-1])
    episodes = result["episodes"]

    assert len(episodes) == 2
    assert episodes[0]["side"] == 1
    assert episodes[1]["side"] == -1
    # every re-firing while the first position was open must be counted,
    # not silently dropped and not turned into extra episodes
    assert result["n_ignored_holding"] > 0

    # episodes never overlap: the second cannot start before the first exits
    assert episodes[1]["t_sig"] >= episodes[0]["exit_t"]

    # exactly 30 minutes (first print at/after t_entry+1800s) each time
    for ep in episodes:
        held = ep["exit_t"] - ep["entry_t"]
        assert 1800.0 <= held < 1801.0


def test_second_position_while_first_is_open_is_ignored_not_traded():
    t0 = int(iso_to_epoch("2026-08-26T12:35:00Z"))
    p0 = 10_000_000.0
    up = p0 * 1.0030
    # sustained displacement for a while: only the FIRST second's firing
    # may become the entry; every later second while held is ignored.
    # Enough post-trigger data for the single episode to settle.
    t, price, buy = synth_prints(t0, [(65, p0), (2000, up)])
    grid = m.build_mid_grid(t, price, buy)
    idx, side = m.find_triggers(grid["gm"], grid["valid_from"])
    assert len(idx) > 1  # more than one candidate firing exists
    result = m.build_episodes(grid["gm"], grid["g0"], idx, side, t, price, t[-1])
    assert len(result["episodes"]) == 1
    assert result["n_ignored_holding"] == len(idx) - 1


# --------------------------------------------------------------------------
# 4. n < 30 safety valve
# --------------------------------------------------------------------------
def write_gz_tape(path: Path, t: np.ndarray, price: np.ndarray, buy: np.ndarray) -> None:
    ts = [pd.Timestamp(x, unit="s", tz="UTC").strftime("%Y-%m-%dT%H:%M:%S.%f0Z") for x in t]
    side = np.where(buy, "BUY", "SELL")
    df = pd.DataFrame({"ts": ts, "price": price, "size": 0.01, "side": side})
    with gzip.open(path, "wt") as f:
        df.to_csv(f, index=False)


def test_safety_valve_prints_only_the_n_line_when_fresh_n_below_30(tmp_path, capsys):
    t0 = int(iso_to_epoch("2026-08-26T12:35:00Z"))
    p0 = 10_000_000.0
    up = p0 * 1.0030
    down = p0 * 0.9970
    # generous pre-baseline padding (>120s) so the 120s edge-trim of the
    # adopted recorder segment cannot eat the trigger; two well-separated
    # episodes -> n well under 30.
    t, price, buy = synth_prints(t0, [
        (250, p0), (200, up), (2000, up), (250, p0), (200, down),
    ])
    tape = tmp_path / "executions_synth.csv.gz"
    write_gz_tape(tape, t, price, buy)

    rc = m.main(paths=[str(tape)])
    out = capsys.readouterr().out
    assert rc == 0

    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == 1, f"safety valve must print exactly one line, got: {lines!r}"
    line = lines[0]
    match = re.match(r"^n=(\d+)/30, judgment not executed \(seed 20260825, "
                      r"2-run hash match [0-9a-f]{16}\)$", line)
    assert match, f"unexpected safety-valve line: {line!r}"
    n = int(match.group(1))
    assert 0 < n < 30

    # nothing statistics-shaped leaked out
    for forbidden in ("bps", "PASS", "FAIL", "maxDD", "t=", "CI"):
        assert forbidden not in out


def test_safety_valve_is_deterministic_across_two_calls(tmp_path, capsys):
    t0 = int(iso_to_epoch("2026-08-26T12:35:00Z"))
    p0 = 10_000_000.0
    up = p0 * 1.0030
    t, price, buy = synth_prints(t0, [(250, p0), (200, up), (2000, up)])
    tape = tmp_path / "executions_synth.csv.gz"
    write_gz_tape(tape, t, price, buy)

    m.main(paths=[str(tape)])
    out1 = capsys.readouterr().out
    m.main(paths=[str(tape)])
    out2 = capsys.readouterr().out
    assert out1 == out2


def test_status_json_writes_n_period_and_last_day_but_no_statistics(tmp_path, capsys):
    """--status-json feeds the dashboard S12 tile: n / fresh period / last day
    only. The n<30 safety valve on stdout is unaffected, and the JSON payload
    itself never carries a statistic even though it is written at any n."""
    t0 = int(iso_to_epoch("2026-08-26T12:35:00Z"))
    p0 = 10_000_000.0
    up = p0 * 1.0030
    down = p0 * 0.9970
    t, price, buy = synth_prints(t0, [
        (250, p0), (200, up), (2000, up), (250, p0), (200, down),
    ])
    tape = tmp_path / "executions_synth.csv.gz"
    write_gz_tape(tape, t, price, buy)
    out_path = tmp_path / "sub" / "s12_status.json"

    rc = m.main(paths=[str(tape)], status_json_path=str(out_path))
    out = capsys.readouterr().out
    assert rc == 0
    assert out_path.exists()

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert set(payload) == {"n", "need", "fresh_start", "fresh_end", "last_day",
                            "generated_at"}
    assert 0 < payload["n"] < 30
    assert payload["need"] == 30
    assert payload["fresh_start"].startswith("2026-08-26")
    assert payload["last_day"] == payload["fresh_end"][:10]

    # the printed safety-valve line is unchanged, and no statistic leaked into
    # either the stdout line or the JSON payload's own (small, fixed) key set
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == 1 and "judgment not executed" in lines[0]
    dumped = json.dumps(payload)
    for forbidden in ("bps", "PASS", "FAIL", "maxDD", "CI"):
        assert forbidden not in dumped


def test_status_json_payload_has_no_period_when_no_fresh_prints(tmp_path):
    t0 = int(iso_to_epoch("2026-08-20T12:00:00Z"))  # before the fresh cutoff
    t, price, buy = synth_prints(t0, [(10, 10_000_000.0)])
    tape = tmp_path / "executions_stale.csv.gz"
    write_gz_tape(tape, t, price, buy)
    pipe = m.run_pipeline([str(tape)])
    payload = m.status_json_payload(pipe, now=1_800_000_000.0)
    assert payload == {"n": 0, "need": 30, "fresh_start": None, "fresh_end": None,
                       "last_day": None, "generated_at": 1_800_000_000.0}


# --------------------------------------------------------------------------
# 5. gap handling (every fresh segment kept; only overlapping episodes drop)
# --------------------------------------------------------------------------
def test_find_gap_zones_detects_restart_gap_and_builds_trim_zone():
    t0 = float(D0)
    seg1 = t0 + np.arange(0, 500, dtype=float)          # 500s run
    gap_start_to_end = m.GAP_THRESHOLD_S + 1.0
    seg2 = t0 + 500 + gap_start_to_end + np.arange(0, 5000, dtype=float)
    t = np.concatenate([seg1, seg2])
    info = m.find_gap_zones(t)
    assert info["n_gaps"] == 1
    lo, hi = info["zones"][0]
    assert lo == pytest.approx(seg1[-1] - m.EDGE_TRIM_S)
    assert hi == pytest.approx(seg2[0] + m.EDGE_TRIM_S)


def test_no_gap_zones_when_all_gaps_are_ordinary_quiet_spacing():
    t0 = float(D0)
    t = t0 + np.arange(0, 2000, dtype=float) * 5.0  # 5s spacing, well under threshold
    info = m.find_gap_zones(t)
    assert info["n_gaps"] == 0
    assert info["excluded_days"] == 0.0


def test_episode_straddling_a_restart_gap_is_excluded_but_the_earlier_segment_is_still_used():
    # Segment 1 (pre-fresh-cutoff-irrelevant here) contains a clean, fully
    # resolvable episode; a big gap follows; segment 2 resumes with plenty
    # of clean data. The pre-QA implementation would have discarded the
    # entire first segment (2026-08-25..08-28 in the real tape) -- the
    # fix must keep it.
    t0 = int(iso_to_epoch("2026-08-26T12:35:00Z"))
    p0 = 10_000_000.0
    up = p0 * 1.0030
    down = p0 * 0.9970
    # jump held just long enough to open one episode, then REVERT to
    # baseline for a long flat tail so the position closes cleanly; >120s
    # of baseline pads each side of the segment boundary so the resolved
    # episode's own re-fire train clears the gap's edge_trim zone (some of
    # ITS earlier re-fires legitimately land inside the zone and are
    # gap-excluded -- that is the feature under test elsewhere).
    t1, p1, b1 = synth_prints(t0, [(150, p0), (200, up), (2000, p0)])

    gap_len = m.GAP_THRESHOLD_S + 500.0
    t2_start = int(t1[-1]) + int(gap_len)
    t2, p2, b2 = synth_prints(t2_start, [(150, p0), (200, down), (2000, p0)])

    t = np.concatenate([t1, t2])
    price = np.concatenate([p1, p2])
    buy = np.concatenate([b1, b2])

    gaps_info = m.find_gap_zones(t)
    assert gaps_info["n_gaps"] == 1

    grid = m.build_mid_grid(t, price, buy)
    idx, side = m.find_triggers(grid["gm"], grid["valid_from"])
    result = m.build_episodes(grid["gm"], grid["g0"], idx, side, t, price,
                               data_hi=t[-1], zones=gaps_info["zones"])
    episodes = result["episodes"]

    # both the pre-gap and post-gap episodes resolve -- neither segment is discarded
    assert len(episodes) == 2
    assert episodes[0]["side"] == 1
    assert episodes[1]["side"] == -1
    for ep in episodes:
        lo, hi = min(ep["t_sig"], ep["exit_t"]), max(ep["t_sig"], ep["exit_t"])
        assert not m.overlaps_any_zone(lo, hi, gaps_info["zones"])


def test_episode_that_would_overlap_the_gap_zone_is_dropped():
    # A firing lands just before the gap such that its 30-minute
    # settlement window would run into the gap+trim zone -- must be
    # gap-excluded, not silently traded through the hole.
    t0 = int(iso_to_epoch("2026-08-26T12:35:00Z"))
    p0 = 10_000_000.0
    up = p0 * 1.0030
    t1, p1, b1 = synth_prints(t0, [(65, p0), (100, up)])  # firing near the end of seg1

    gap_len = m.GAP_THRESHOLD_S + 10.0  # gap starts right after seg1 ends
    t2_start = int(t1[-1]) + int(gap_len)
    t2, p2, b2 = synth_prints(t2_start, [(65, p0), (2200, up)])

    t = np.concatenate([t1, t2])
    price = np.concatenate([p1, p2])
    buy = np.concatenate([b1, b2])

    gaps_info = m.find_gap_zones(t)
    assert gaps_info["n_gaps"] == 1

    grid = m.build_mid_grid(t, price, buy)
    idx, side = m.find_triggers(grid["gm"], grid["valid_from"])
    result = m.build_episodes(grid["gm"], grid["g0"], idx, side, t, price,
                               data_hi=t[-1], zones=gaps_info["zones"])

    assert result["n_gap_excluded"] >= 1
    for ep in result["episodes"]:
        lo, hi = min(ep["t_sig"], ep["exit_t"]), max(ep["t_sig"], ep["exit_t"])
        assert not m.overlaps_any_zone(lo, hi, gaps_info["zones"])
