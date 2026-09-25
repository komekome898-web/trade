"""V5 adversary: the allow-list over the full grid of
(root x directory name x depth x path form), judged by an oracle that knows,
by construction, the written location and the real location of every file
it made, and applies the documented rule with plain string tests (no
fnmatch, no realpath):

  refused  <=>  either location is outside the allowed roots
                (backtest_data, data, paper_logs/tape -- with at least one
                more component), or has a component whose lower-case form
                starts with "qa_" or "o3c_", or is "phase2_runs" or
                "phase2_sealed".

Axes: roots {backtest_data, data, paper_logs/tape, other, paper_logs/x} x
names {ok_x, qa_x, QA_x, o3c_x, binance_cm_o3c_x, phase2_runs,
phase2_runs_x, phase2_sealed, qa} x depth {directly under the root, one
directory deeper} x forms {plain relative, absolute, `..` into it, `..` out
of it, a directory symlink to it, a file symlink to its file}.
Separately: escapes out of the data root (relative `..`, absolute outside,
a symlink inside an allowed root pointing outside), a non-file, and an empty
path. Not in the grid: hard links (a hard link has no "real location" other
than its own path; a hard link to a denied file under an allowed name is
READ -- the known limit, asserted in test_hard_link_is_the_known_limit),
and case-folding file systems (the rule folds case itself).
"""
from __future__ import annotations

import itertools
import os

import pytest

from bot.bt.data import PathRefused, load

ROOTS = ["backtest_data", "data", "paper_logs/tape", "other", "paper_logs/x"]
NAMES = ["ok_x", "qa_x", "QA_x", "o3c_x", "binance_cm_o3c_x", "phase2_runs", "phase2_runs_x", "phase2_sealed", "qa"]
FORMS = ["plain", "absolute", "dotdot_in", "dotdot_out", "dir_symlink", "file_symlink"]
CSV = "id,t,price,size,side\n1,2026-01-05T00:00:00Z,100,1,BUY\n"
SPEC = {"format": "csv", "header": True, "delimiter": ",", "kind": "trade", "symbol": "X", "asset": "crypto",
        "time": {"columns": ["t"], "unit": "iso", "tz": "UTC"},
        "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"BUY": "buy"}}
ALLOWED = [("backtest_data",), ("data",), ("paper_logs", "tape")]


def oracle_refused(parts: list[str]) -> bool:
    under = any(tuple(parts[:len(r)]) == r and len(parts) > len(r) for r in ALLOWED)
    bad = any(p.lower().startswith(("qa_", "o3c_")) or p.lower() in ("phase2_runs", "phase2_sealed") for p in parts)
    return bad or not under


def build(tmp, root_dir, name, depth, form):
    """Make the files for one cell; return (path to pass, written parts, real parts)."""
    base = root_dir.split("/") + (["mid"] if depth else [])
    target = base + [name]
    os.makedirs(os.path.join(tmp, *target), exist_ok=True)
    os.makedirs(os.path.join(tmp, *base, "ok_dir"), exist_ok=True)
    with open(os.path.join(tmp, *target, "f.csv"), "w") as fh:
        fh.write(CSV)
    with open(os.path.join(tmp, *base, "ok_dir", "f.csv"), "w") as fh:
        fh.write(CSV)
    rel_target = "/".join(target + ["f.csv"])
    if form == "plain":
        return rel_target, target + ["f.csv"], target + ["f.csv"]
    if form == "absolute":
        return os.path.join(tmp, *target, "f.csv"), target + ["f.csv"], target + ["f.csv"]
    if form == "dotdot_in":
        return "/".join(base + ["ok_dir", "..", name, "f.csv"]), target + ["f.csv"], target + ["f.csv"]
    if form == "dotdot_out":
        p = base + ["ok_dir", "f.csv"]
        return "/".join(target + ["..", "ok_dir", "f.csv"]), p, p
    if form == "dir_symlink":
        link = base + ["ok_dir", "lnk"]
        os.symlink(os.path.join("..", name), os.path.join(tmp, *link))
        return "/".join(link + ["f.csv"]), link + ["f.csv"], target + ["f.csv"]
    if form == "file_symlink":
        link = base + ["ok_dir", "lnk.csv"]
        os.symlink(os.path.join("..", name, "f.csv"), os.path.join(tmp, *link))
        return "/".join(link), link, target + ["f.csv"]
    raise AssertionError(form)


CELLS = list(itertools.product(ROOTS, NAMES, (0, 1), FORMS))


def test_grid_size():
    assert len(CELLS) == 540


@pytest.mark.parametrize("root_dir,name,depth,form", CELLS, ids=["/".join(map(str, c)) for c in CELLS])
def test_allowlist_cell(tmp_path, root_dir, name, depth, form):
    tmp = str(tmp_path)
    path, written, real = build(tmp, root_dir, name, depth, form)
    want_refused = oracle_refused(written) or oracle_refused(real)
    ds = [{"name": "d", "paths": [path], "spec": SPEC}]
    if want_refused:
        with pytest.raises(PathRefused):
            load(tmp, ds)
    else:
        res = load(tmp, ds)
        assert [r["id"] for r in res.records("d")] == ["1"]


def test_escapes_out_of_the_data_root(tmp_path):
    root = tmp_path / "root"
    (root / "backtest_data" / "ok").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "f.csv").write_text(CSV)
    (root / "backtest_data" / "ok" / "out").symlink_to(outside)
    for p in ["../outside/f.csv", str(outside / "f.csv"), "backtest_data/ok/out/f.csv",
              "backtest_data/../../outside/f.csv"]:
        with pytest.raises(PathRefused):
            load(str(root), [{"name": "d", "paths": [p], "spec": SPEC}])


def test_not_a_file_and_empty_path(tmp_path):
    (tmp_path / "backtest_data" / "dir").mkdir(parents=True)
    for p in ["backtest_data/dir", "backtest_data/missing.csv", ""]:
        with pytest.raises((PathRefused, ValueError)):
            load(str(tmp_path), [{"name": "d", "paths": [p], "spec": SPEC}])


def test_every_path_is_checked_before_any_row_is_read(tmp_path):
    (tmp_path / "backtest_data" / "ok").mkdir(parents=True)
    (tmp_path / "backtest_data" / "qa_x").mkdir(parents=True)
    (tmp_path / "backtest_data" / "ok" / "f.csv").write_text("not,a,valid\nfile\n")
    (tmp_path / "backtest_data" / "qa_x" / "f.csv").write_text(CSV)
    with pytest.raises(PathRefused):  # not a ParseError from the first file
        load(str(tmp_path), [{"name": "a", "paths": ["backtest_data/ok/f.csv"], "spec": SPEC},
                             {"name": "b", "paths": ["backtest_data/qa_x/f.csv"], "spec": SPEC}])


def test_mandatory_denies_cannot_be_removed():
    from bot.bt.data import AllowList, MANDATORY_DENY
    a = AllowList(extra_deny=[("tmp_*", "scratch")])
    pats = [p for p, _ in a.deny]
    assert all(p in pats for p, _ in MANDATORY_DENY) and "tmp_*" in pats


def test_hard_link_is_the_known_limit(tmp_path):
    (tmp_path / "backtest_data" / "qa_x").mkdir(parents=True)
    (tmp_path / "backtest_data" / "ok").mkdir(parents=True)
    (tmp_path / "backtest_data" / "qa_x" / "f.csv").write_text(CSV)
    os.link(tmp_path / "backtest_data" / "qa_x" / "f.csv", tmp_path / "backtest_data" / "ok" / "f.csv")
    res = load(str(tmp_path), [{"name": "d", "paths": ["backtest_data/ok/f.csv"], "spec": SPEC}])
    assert len(res.records("d")) == 1  # READ: a hard link is indistinguishable from its own file by path
