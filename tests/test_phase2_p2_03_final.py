"""Tests for the P2-03 FINAL (sealed-period) evaluator, scripts/phase2/p2_03_final.py.

Three things are checked, none of which opens a real sealed data file:

  1. the three unseal guards — env `PHASE2_FINAL_EVAL=P2-03`, the owner's
     `UNSEAL_APPROVED` file, and the explicit token — each of which must, on
     its own, make the script refuse. Run against a TEMPORARY root, so no
     real seal record, approval file or snapshot is involved, and `main()`
     must fail on the guards BEFORE it creates its output directory;
  2. recovery of a PLANTED overnight drift from the sealed window: a
     synthetic snapshot is sealed at a known date, a known drift is planted,
     and the evaluator's own main indicator must come back with that drift
     and a CI that excludes zero — i.e. the sealed-side pipeline is not inert
     and its endpoint rule really does restrict the sample to the sealed rows;
  3. the 1306.T-shaped sequence: a two-bar ~1/10 defect immediately followed
     by the real 10:1 split's effective date. Because the vendor's mis-dated
     adjustment already divided the pre-split segment by 10, the CSV level is
     CONTINUOUS across the split, so the sequence must be handled by rule 1
     (the two defect bars) and rule 2 (the recovery row, whose ×10 step back
     up looks exactly like a split candidate) — and every pair touching those
     rows must be excluded while the neighbours survive.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "src"))

from bot.research.sealed import UNSEAL_TOKEN, SealedDataError, md5_of  # noqa: E402
from phase2 import p2_03_final as pf  # noqa: E402
from phase2 import p2_03_run as run  # noqa: E402

ALL_SYMBOLS = pf.MAIN_SYMBOLS + pf.CONTROL4_SYMBOLS


# ---------------------------------------------------------------------------
# 1. the three unseal guards
# ---------------------------------------------------------------------------

def _guard_root(tmp_path: Path, approved: bool) -> Path:
    d = tmp_path / "backtest_data" / "phase2_sealed" / "P2-03"
    d.mkdir(parents=True)
    if approved:
        (d / "UNSEAL_APPROVED").write_text("unit: P2-03\napproved_by: test\n",
                                           encoding="utf-8")
    return tmp_path


def test_guards_pass_only_when_all_three_are_present(tmp_path, monkeypatch):
    root = _guard_root(tmp_path, approved=True)
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-03")
    pf.check_guards(root=root, token=UNSEAL_TOKEN)   # must not raise


def test_guard_env_missing_or_wrong_unit_refuses(tmp_path, monkeypatch):
    root = _guard_root(tmp_path, approved=True)
    monkeypatch.delenv("PHASE2_FINAL_EVAL", raising=False)
    with pytest.raises(SealedDataError) as e:
        pf.check_guards(root=root, token=UNSEAL_TOKEN)
    assert "PHASE2_FINAL_EVAL" in str(e.value)
    # another unit's env value is not an approval for P2-03 either
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-01")
    with pytest.raises(SealedDataError):
        pf.check_guards(root=root, token=UNSEAL_TOKEN)


def test_guard_missing_owner_approval_file_refuses(tmp_path, monkeypatch):
    root = _guard_root(tmp_path, approved=False)
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-03")
    with pytest.raises(SealedDataError) as e:
        pf.check_guards(root=root, token=UNSEAL_TOKEN)
    assert "UNSEAL_APPROVED" in str(e.value)


def test_guard_wrong_token_refuses(tmp_path, monkeypatch):
    root = _guard_root(tmp_path, approved=True)
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-03")
    with pytest.raises(SealedDataError) as e:
        pf.check_guards(root=root, token="I_UNDERSTAND_REAL_MONEY")
    assert "token" in str(e.value)


def test_guards_refuse_any_unit_other_than_p2_03(tmp_path, monkeypatch):
    """The owner's approval is scoped to P2-03; P2-01 / P2-02 must stay shut
    even if someone points the env and the token at them."""
    root = _guard_root(tmp_path, approved=True)
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-02")
    with pytest.raises(SealedDataError) as e:
        pf.check_guards(root=root, token=UNSEAL_TOKEN, unit="P2-02")
    assert "P2-03" in str(e.value)


def test_main_refuses_before_touching_anything_when_a_guard_is_missing(
        tmp_path, monkeypatch):
    root = _guard_root(tmp_path, approved=True)
    out = tmp_path / "out"
    monkeypatch.delenv("PHASE2_FINAL_EVAL", raising=False)
    with pytest.raises(SealedDataError):
        pf.main(out_dir=out, root=root, token=UNSEAL_TOKEN)
    assert not out.exists()

    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-03")
    with pytest.raises(SealedDataError):
        pf.main(out_dir=out, root=root, token="nope")
    assert not out.exists()


def test_final_configuration_constants_match_the_prereg_and_ledger():
    assert pf.UNIT == "P2-03"
    assert pf.CUMULATIVE_N == 1                 # ITER.md: 反復1 はデータ修正
    assert (pf.SEALED_START, pf.SEALED_END) == (
        pd.Timestamp("2022-03-05"), pd.Timestamp("2026-09-04"))
    assert (pf.BOOT_BLOCK, pf.BOOT_N, pf.SHUFFLE_N, pf.RUN_SEED) == (
        20, 2000, 1000, 20260906)
    assert pf.ETF_SYMBOLS == ["1306.T", "1591.T", "2516.T"]
    assert pf.REFERENCE_SYMBOL == "1321.T"
    # iteration 1's correction window, verbatim from the ledger / schema
    assert pf.PRICE_LEVEL_CORRECTIONS["1306.T"] == [("2015-01-05", "2026-03-31", 10.0)]
    assert pf.SPLIT_EFFECTIVE == pd.Timestamp("2026-04-01")


# ---------------------------------------------------------------------------
# synthetic snapshot + seal record (shared by tests 2 and 3)
# ---------------------------------------------------------------------------

def _tape(n: int, planted_bps: float, level: float, seed: int) -> pd.DataFrame:
    """A synthetic daily tape with a KNOWN overnight drift planted in it:
    open(t+1) = close(t) * (1 + planted/1e4 + noise), close(t) = open(t) * (1 + noise)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n)
    o_, h_, l_, c_, v_ = [], [], [], [], []
    prev = level
    for i in range(n):
        o = prev * (1 + (planted_bps + rng.normal(0, 30)) / 1e4)
        c = o * (1 + rng.normal(0, 50) / 1e4)
        o_.append(round(o, 1)); c_.append(round(c, 1))
        h_.append(round(max(o, c) * 1.001, 1)); l_.append(round(min(o, c) * 0.999, 1))
        v_.append(100_000 + i)
        prev = c
    return pd.DataFrame({"date": [d.date().isoformat() for d in dates],
                         "open": o_, "high": h_, "low": l_, "close": c_,
                         "adjclose": c_, "volume": v_})


def _collapse_two_bars(df: pd.DataFrame, i: int) -> pd.DataFrame:
    """The 1306.T shape: two consecutive bars printed at ~1/10 the level,
    with the level restored on the very next bar (the real split's effective
    date, at which the CSV is continuous because the vendor's mis-dated
    adjustment already divided the pre-split segment by 10)."""
    df = df.copy()
    for j in (i, i + 1):
        for col in ("open", "high", "low", "close", "adjclose"):
            df.loc[j, col] = round(float(df.loc[j, col]) / 10.0, 1)
        df.loc[j, "volume"] = 0
    return df


def _build_root(tmp_path: Path, seal_from: str, planted_bps: float = 8.0,
                n: int = 900, defect_at: int | None = None) -> tuple[Path, pd.DataFrame]:
    """A temporary repo root carrying a synthetic snapshot, seal record and
    owner approval. Returns (root, the 1306.T frame as written)."""
    root = tmp_path / "root"
    snap = root / "backtest_data" / SNAPSHOT_REL_NAME
    snap.mkdir(parents=True)
    (root / "config").mkdir(parents=True)
    (root / "schema").mkdir(parents=True)
    (root / "config" / "constants.yaml").write_bytes(
        (REPO / "config" / "constants.yaml").read_bytes())
    (root / "schema" / "jpx_etf_daily.json").write_bytes(
        (REPO / "schema" / "jpx_etf_daily.json").read_bytes())

    files, frame_1306 = [], None
    for k, sym in enumerate(ALL_SYMBOLS):
        df = _tape(n, planted_bps if sym in pf.MAIN_SYMBOLS else 1.0,
                   level=430.0, seed=100 + k)
        if sym == "1306.T":
            if defect_at is not None:
                df = _collapse_two_bars(df, defect_at)
            frame_1306 = df
        p = snap / f"{sym}.csv"
        df.to_csv(p, index=False)
        files.append({
            "path": f"{pf.SNAPSHOT_REL.as_posix()}/{sym}.csv",
            "md5": md5_of(p), "time_column": "date",
            "first_ts": f"{df['date'].iloc[0]}T00:00:00+00:00",
            "last_ts": f"{df['date'].iloc[-1]}T00:00:00+00:00",
            "seal_from_ts": f"{seal_from}T00:00:00+00:00",
            "seal_from_ts_per_file": f"{seal_from}T00:00:00+00:00",
        })

    sd = root / "backtest_data" / "phase2_sealed" / "P2-03"
    sd.mkdir(parents=True)
    (sd / "SEALED.json").write_text(json.dumps({
        "unit": "P2-03", "created_utc": datetime.now(timezone.utc).isoformat(),
        "forward_start": "2030-01-01T00:00:00+00:00", "files": files,
        "rule": "synthetic", "primary_series": "1306.T",
    }, indent=1), encoding="utf-8")
    (sd / "UNSEAL_APPROVED").write_text("unit: P2-03\napproved_by: test\n",
                                        encoding="utf-8")
    return root, frame_1306


SNAPSHOT_REL_NAME = pf.SNAPSHOT_REL.name


def _widen_window(monkeypatch, start: str, end: str = "2030-01-01") -> None:
    monkeypatch.setattr(pf, "SEALED_START", pd.Timestamp(start))
    monkeypatch.setattr(pf, "SEALED_END", pd.Timestamp(end))


# ---------------------------------------------------------------------------
# 2. planted-drift recovery from the sealed window
# ---------------------------------------------------------------------------

def test_sealed_window_recovers_a_planted_drift(tmp_path, monkeypatch):
    planted = 8.0
    seal_from = "2022-06-01"
    root, _ = _build_root(tmp_path, seal_from=seal_from, planted_bps=planted)
    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-03")
    _widen_window(monkeypatch, seal_from)
    monkeypatch.setattr(pf, "BOUNDARY_START", pd.Timestamp("2023-01-02"))
    monkeypatch.setattr(pf, "BOUNDARY_END", pd.Timestamp("2023-01-31"))

    out = tmp_path / "out"
    assert pf.main(out_dir=out, root=root) == 0

    ind = pd.read_csv(out / "main_indicator.csv")
    main = ind[(ind["stage"] == "after_exclusion")
               & (ind["cost_scenario"] == "optimistic")].set_index("series")
    for sym in pf.MAIN_SYMBOLS:
        row = main.loc[sym]
        # the planted drift comes back, and its CI is on the right side of zero
        assert row["ci_lo"] > 0.0, sym
        assert abs(row["mean"] - planted) < 5.0, (sym, row["mean"])

    # the endpoint rule really did restrict the sample to the sealed rows
    full = pd.read_csv(root / "backtest_data" / SNAPSHOT_REL_NAME / "1306.T.csv")
    n_sealed = int((pd.to_datetime(full["date"]) >= pd.Timestamp(seal_from)).sum())
    counts = pd.read_csv(out / "rule_counts.csv").set_index("series")
    assert int(counts.loc["1306.T", "n_rows_sealed"]) == n_sealed
    assert n_sealed < len(full)
    pairs = pd.read_csv(out / "pairs_1306T.csv")
    assert pd.to_datetime(pairs["date_t"]).min() >= pd.Timestamp(seal_from)

    # every judgment artefact the PREREG asks for is on disk
    for name in ("RESULTS.md", "RUN.json", "bar_and_falsification.csv",
                 "summary_by_series.csv", "correlation_matrix.csv",
                 "residual_vs_1321.csv", "sign_agreement.csv", "mde.csv",
                 "controls_sign_shuffle.csv", "controls_individual_stocks.csv",
                 "regime_2024_11_05.csv", "input_md5_check.csv"):
        assert (out / name).is_file(), name

    meta = json.loads((out / "RUN.json").read_text(encoding="utf-8"))
    assert meta["seed"] == pf.RUN_SEED
    assert meta["cumulative_N"] == 1
    assert all(r["match"] for r in meta["input_md5_check"])
    # the unseal audit log recorded this run's reads
    assert len(meta["unseal_log_excerpt"]) == len(ALL_SYMBOLS)

    # judgment wording: the report states 満たす/満たさない, never 採用/棄却
    text = (out / "RESULTS.md").read_text(encoding="utf-8")
    assert "満たす" in text or "満たさない" in text
    judgment = pd.read_csv(out / "bar_and_falsification.csv")
    assert set(judgment["outcome"]) <= {"満たす", "満たさない"}


# ---------------------------------------------------------------------------
# 3. the two-bar defect immediately followed by the real split
# ---------------------------------------------------------------------------

def test_two_bar_defect_then_real_split_sequence(tmp_path, monkeypatch):
    """Rule 1 must catch the two-bar collapse (k = 2), rule 2 must catch the
    ×10 step back up on the recovery row, and every pair touching any of the
    three rows must be excluded while the neighbours survive."""
    seal_from = "2022-06-01"
    defect_at = 700
    root, frame = _build_root(tmp_path, seal_from=seal_from, n=900,
                              defect_at=defect_at)
    d_prev = pd.Timestamp(frame["date"].iloc[defect_at - 1])
    d1 = pd.Timestamp(frame["date"].iloc[defect_at])
    d2 = pd.Timestamp(frame["date"].iloc[defect_at + 1])
    d_split = pd.Timestamp(frame["date"].iloc[defect_at + 2])   # 実効日相当
    d_after = pd.Timestamp(frame["date"].iloc[defect_at + 3])

    monkeypatch.setenv("PHASE2_FINAL_EVAL", "P2-03")
    _widen_window(monkeypatch, seal_from)
    monkeypatch.setattr(pf, "BOUNDARY_START", d_prev - pd.Timedelta(days=7))
    monkeypatch.setattr(pf, "BOUNDARY_END", d_after + pd.Timedelta(days=7))
    monkeypatch.setattr(pf, "SPLIT_EFFECTIVE", d_split)

    out = tmp_path / "out"
    assert pf.main(out_dir=out, root=root) == 0

    # -- rule 1: exactly one run, k = 2, on the two collapsed bars -----------
    ev = pd.read_csv(out / "rule1_badprint_events.csv")
    ev = ev[ev["series"] == "1306.T"]
    assert len(ev) == 1
    e = ev.iloc[0]
    assert int(e["k"]) == 2
    assert e["first_date"] == str(d1.date()) and e["last_date"] == str(d2.date())
    assert e["baseline_date"] == str(d_prev.date())
    assert e["revert_date"] == str(d_split.date())
    # the baseline and the recovery close agree to within the ±5% tolerance
    assert abs(e["revert_close"] / e["baseline_close_c0"] - 1.0) <= \
        run.BAD_PRINT_REVERT_TOLERANCE

    # -- rule 2: the ×10 step back up on the split-effective row ------------
    b = pd.read_csv(out / "boundary_2026_1306.csv").set_index("date")
    assert bool(b.loc[str(d1.date()), "flag_rule1_badprint"])
    assert bool(b.loc[str(d2.date()), "flag_rule1_badprint"])
    assert not bool(b.loc[str(d_prev.date()), "flag_rule1_badprint"])
    assert not bool(b.loc[str(d_split.date()), "flag_rule1_badprint"])
    assert bool(b.loc[str(d_split.date()), "flag_rule2_split"])

    # -- the pairs: everything touching the three rows is excluded ----------
    for d in (d_prev, d1, d2, d_split):
        assert bool(b.loc[str(d.date()), "pair_excluded"]), d
        assert not bool(b.loc[str(d.date()), "pair_clean"]), d
    # ... and the neighbours on either side survive
    assert bool(b.loc[str(d_after.date()), "pair_clean"])
    d_before2 = pd.Timestamp(frame["date"].iloc[defect_at - 2])
    assert bool(b.loc[str(d_before2.date()), "pair_clean"])

    # -- the defect never reaches the judgment sample -----------------------
    pairs = pd.read_csv(out / "pairs_1306T.csv")
    clean = pairs[pairs["clean"]]
    assert not set(pd.to_datetime(clean["date_t"])) & {d_prev, d1, d2, d_split}
    # the collapsed bars are ~1/10, so leaving them in would blow the sample up
    assert clean["r_night_bps"].abs().max() < 5_000.0


def test_boundary_narrative_says_so_when_rule1_found_nothing():
    """A tape with no rule-1 run must produce a narrative that SAYS the rule
    found nothing, rather than crashing on the empty event table — the report
    has to be able to tell the owner that the named 2026-03-30/31 defect was
    not caught, which is exactly the case worth noticing."""
    empty = pd.DataFrame(columns=pf.BADPRINT_EVENT_COLUMNS)
    text = pf._boundary_narrative(pd.DataFrame(columns=["date"]), empty)
    assert "1 件も発火しなかった" in text
    # a frame with no columns at all (the pre-fix shape) must not crash either
    assert "1 件も発火しなかった" in pf._boundary_narrative(
        pd.DataFrame(), pd.DataFrame())


def test_rule2_flags_the_recovery_row_not_a_continuous_level(tmp_path):
    """Unit-level companion to the end-to-end case above: the ×10 recovery is
    a split_candidate, while a merely continuous level is not — so the real
    2026-04-01 split, which leaves NO level step in the CSV (the vendor's
    mis-dated adjustment already divided the pre-split segment by 10), does
    not itself trigger rule 2; only the defect's recovery does."""
    flat = [430.0] * 12
    assert not run.detect_split_candidates(flat).any()

    with_defect = flat.copy()
    with_defect[5] = 43.0
    with_defect[6] = 43.1
    mask = run.detect_split_candidates(with_defect)
    assert mask[7], "the ×10 step back up must read as a split candidate"
    assert mask[5], "the ×1/10 step down must read as one too"
