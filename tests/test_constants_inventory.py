"""Tests for scripts/constants_inventory.py (DATA_QA_CHECKLIST item 8)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import constants_inventory as ci  # noqa: E402

CONSTANTS_YAML = """
venue_a:
  fee_bps:
    value: 1.5
    unit: bps
    source_type: primary_document
    source_url: "https://example.com/fees"
    verified_on: "2026-09-05"

  old_floor_bps:
    value: 5.0
    unit: bps
    source_type: assumed
    deprecated: true
    reason: "superseded by measured value"
    notes: "do not use"

venue_b:
  spread_bps:
    value: 2.0
    unit: bps
    source_type: assumed
    notes: "unconfirmed round number"

  unmeasured_bps:
    value: null
    unit: bps
    source_type: assumed
    notes: "no measurement script exists yet"
"""


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "constants.yaml").write_text(CONSTANTS_YAML)
    (tmp_path / "src").mkdir()
    (tmp_path / "scripts").mkdir()
    return tmp_path


def test_flags_assumed_deprecated_and_null_only(tree: Path):
    constants = ci.load_constants(tree)
    flagged = ci.flagged_constants(constants, tree)
    paths = {f.path for f in flagged}
    assert paths == {
        "venue_a.old_floor_bps",
        "venue_b.spread_bps",
        "venue_b.unmeasured_bps",
    }
    assert "venue_a.fee_bps" not in paths  # primary_document, sourced -> not flagged


def test_flag_reasons(tree: Path):
    constants = ci.load_constants(tree)
    flagged = {f.path: f for f in ci.flagged_constants(constants, tree)}
    assert set(flagged["venue_a.old_floor_bps"].flag_reasons) == {"assumed", "deprecated"}
    assert flagged["venue_b.spread_bps"].flag_reasons == ["assumed"]
    assert set(flagged["venue_b.unmeasured_bps"].flag_reasons) == {"assumed", "null"}


def test_finds_consumer_by_full_dotted_path(tree: Path):
    (tree / "scripts" / "uses_it.py").write_text(
        'require_source("venue_b.spread_bps", consts)\n'
    )
    constants = ci.load_constants(tree)
    flagged = {f.path: f for f in ci.flagged_constants(constants, tree)}
    assert flagged["venue_b.spread_bps"].consumers == ["scripts/uses_it.py"]
    assert flagged["venue_b.unmeasured_bps"].consumers == []


def test_does_not_false_positive_on_bare_name_collision(tree: Path):
    # a file uses the bare name "spread_bps" as an unrelated local variable --
    # must NOT be reported as a consumer since only the full dotted path counts.
    (tree / "src" / "unrelated.py").write_text("spread_bps = 3\nprint(spread_bps)\n")
    constants = ci.load_constants(tree)
    flagged = {f.path: f for f in ci.flagged_constants(constants, tree)}
    assert flagged["venue_b.spread_bps"].consumers == []


def test_excludes_self_file_from_consumers(tree: Path):
    # the script's own source mentions constant paths in MEASUREMENT_PLANS
    # keys/tests; self_path exclusion must keep it out of the report.
    constants = ci.load_constants(tree)
    flagged = ci.flagged_constants(constants, tree, self_path=Path(ci.__file__).resolve())
    for f in flagged:
        assert "constants_inventory.py" not in " ".join(f.consumers)


def test_render_and_write_doc(tree: Path):
    constants = ci.load_constants(tree)
    flagged = ci.flagged_constants(constants, tree)
    doc = ci.render_todo_doc(flagged)
    assert "venue_a.old_floor_bps" in doc
    assert "venue_b.spread_bps" in doc
    assert "venue_b.unmeasured_bps" in doc
    assert "計測計画" in doc


def test_main_writes_doc_and_returns_zero(tree: Path, monkeypatch):
    out_path = tree / "docs" / "CONSTANTS_TODO.md"
    monkeypatch.setattr(sys, "argv",
                         ["constants_inventory.py", "--root", str(tree), "--out", str(out_path)])
    rc = ci.main()
    assert rc == 0
    assert out_path.exists()
    text = out_path.read_text()
    assert "venue_b.unmeasured_bps" in text


def test_no_write_skips_doc(tree: Path, monkeypatch):
    out_path = tree / "docs" / "CONSTANTS_TODO.md"
    monkeypatch.setattr(sys, "argv",
                         ["constants_inventory.py", "--root", str(tree), "--out", str(out_path),
                          "--no-write"])
    rc = ci.main()
    assert rc == 0
    assert not out_path.exists()
