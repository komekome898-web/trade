"""Item 4 battery, round r2-2: the claims table of ROOTCAUSE_r2-2.md §4 (the scene-keeper's own diff record).

Families (the claim, the test that fails if a hand-written claim is left, the mutant of the machine):
  F1  the diff section at the end of a ROOTCAUSE (and the returned changed_files)   br2-1-touch
  F2  whether the script's machine check (checkBattery) stops                        br2-1-touch
  F3  the scene-keeper's records (battery/materials) are append-only                 br2-1-touch
  F4  (round r2-3) the attribution of each diff line against a baseline taken at the start   br2-2-touch
      (ROOTCAUSE_r2-3.md §4): whether the line already differed from HEAD when the scene-keeper started and whether
      its content changed during the run.  Who wrote a line is not derived (git keeps no author for an uncommitted
      change); that stays prose outside the section.

The adversarial grids (委任文 §3「提出前の吟味」(6)): the rule's input space, built from the rule's text, not from any
branch of diff_scope.py or of the script.
  - test_check_matches_delegation_text_on_grid: every path of PATHS (paths git can print for a changed file: inside
    each item's battery, a sibling whose name starts with the same letters, the battery root, the worker's and the
    critic's tests, the implementation, the lead's trace, the scene-keeper's records, the script) x every item 0..4,
    one path at a time and all paths at once.  The answer is written from the text of 委任文 §0 (L-448 row):
    「その項目の場面集 tests/bt/battery/item_<番号>/ の外のファイルがあれば止める。項目 4 の場面係だけは項目 0 の場面集にも
    触れてよい」.
    Not in the grid (named): (1) paths git prints in quotes (a non-ASCII name, e.g. "tests/bt/battery/item_4/\\350\\241\\250.md"):
    the script's check reads them as outside although the file is inside the battery -- that is the script's defect
    (ROOTCAUSE_r2-2.md §5-4), so the grid cannot hold it and pass; diff_scope reports such lines instead
    (test_quoted_paths_are_reported). (2) paths with a leading "./" or absolute paths: git never prints them for
    `git diff --name-only`. (3) a call without an item (the script always passes one).
  - test_materials_classifier_grid: every path of MAT_PATHS against the text of the recording rule
    「docs/DISCUSSIONS/2026-09-23_backtest_env/item_<N>/battery/materials/<回>/」.
    Not in the grid (named): the table maker's round_<k>/materials (not the scene-keeper's records; the table maker
    has its own rule), quoted paths (as above).
  - test_attribution_matches_rule_on_grid (F4): the rule of ROOTCAUSE_r2-3.md §3-1, over the whole input space of one
    diff line: in the baseline or not x its content at the start (a file / deleted) x its content now (the same / other /
    deleted / not in `git status` at all) x HEAD the same or moved.  The answer is written from the rule's text.
    Not in the grid (named): renames and copies (`git status` prints "R  new\0old"; snapshot() keeps the new path and
    drops the old one, tested by test_snapshot_parses_renames instead), quoted paths (a quoted `git diff` line is never
    a key of the -z status, so it falls in "not in git status" -- inside the grid as that value).
"""
from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D = _load(HERE / "diff_scope.py", "i4_diff_scope")

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed (the script's check is JavaScript)")


def _in_git():
    if shutil.which("git") is None:
        return False
    r = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "true"


needs_git = pytest.mark.skipif(not _in_git(), reason="not a git work tree")

# ------------------------------------------------------------------------------------------- F2  the grid
PATHS = [
    "tests/bt/battery/item_0/scenes.py",
    "tests/bt/battery/item_0/sub/deep.py",
    "tests/bt/battery/item_1/i1_scenes.py",
    "tests/bt/battery/item_2/x.py",
    "tests/bt/battery/item_3/x.py",
    "tests/bt/battery/item_4/i4_scenes.py",
    "tests/bt/battery/item_4/opponents/CONSIDERED.md",
    "tests/bt/battery/item_40/x.py",
    "tests/bt/battery/item_4x/x.py",
    "tests/bt/battery/item_4",
    "tests/bt/battery/README.md",
    "tests/bt/battery_item_4/x.py",
    "Tests/bt/battery/item_4/x.py",
    "tests/bt/item_4/test_x.py",
    "tests/bt/critic/item_4/test_x.py",
    "tests/bt/compat/golden/g.json",
    "src/bot/bt/core/contract.py",
    "src/bot/backtest/engine.py",
    "docs/AUDITOR/TRACE/2026-09-26_220780c0.json",
    "docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/a.txt",
    "scripts/workflows/backtest_env.js",
]
ITEMS = [0, 1, 2, 3, 4]


# 仕上げの委任文 docs/DATA/delegations/20260926_backtest_env_finish.md §3「機械の検査の除外(i4-r2-09、L-448 の補い)」:
# 「場面係の差分の検査(`git diff --name-only HEAD` の全行)で、`docs/AUDITOR/TRACE/` の下のファイルはリードのフックが書く痕跡であり、
#   場面集の外の変更に数えない。」
NOT_COUNTED_BY_TEXT = ("docs/AUDITOR/TRACE/",)


def _inside_by_text(path, item):
    """The answer from the text of the L-448 row (the battery of that item; item 4 also item 0's) and of the finishing
    delegation's exclusion (§3: files under docs/AUDITOR/TRACE/ are the lead's hook traces, not counted as outside)."""
    allowed = [f"tests/bt/battery/item_{item}/"] + (["tests/bt/battery/item_0/"] if item == 4 else [])
    return any(path.startswith(a) for a in allowed) or any(path.startswith(x) for x in NOT_COUNTED_BY_TEXT)


def _cases():
    cases = []
    for item in ITEMS:
        for p in PATHS:
            cases.append(([p], item))
        cases.append((list(PATHS), item))
    return cases


def _disagreements(src_text=None):
    cases = _cases()
    got = D.run_check_many([{"changed_files": files, "item": item} for files, item in cases], src_text=src_text)
    bad = []
    for (files, item), findings in zip(cases, got):
        outside = [p for p in files if not _inside_by_text(p, item)]
        touch = [f for f in findings if str(f.get("id", "")).endswith("-touch")]
        other = [f for f in findings if f not in touch]
        if other:
            bad.append((files, item, "unexpected", other))
        if outside:
            ok = len(touch) == 1 and touch[0].get("level") == "止める" and touch[0]["text"].endswith(": " + ", ".join(outside))
        else:
            ok = touch == []
        if not ok:
            bad.append((files, item, outside, touch))
    return bad


@needs_node
def test_check_matches_delegation_text_on_grid():
    assert _disagreements() == []


def _mutate(old, new):
    """Change the first `old` inside checkBattery only (the same text also sits in the prompts above it)."""
    src = D.script_text()
    at = src.index("function checkBattery(")
    k, end = src.find(old, at), src.find("\nfunction ", at + 1)
    assert k >= 0 and (end < 0 or k < end), f"checkBattery no longer holds {old!r}; rewrite the mutant"
    return src[:k] + new + src[k + len(old):]


MUTANTS_CHECK = {
    "no separator after the item number": ("`tests/bt/battery/item_${item.id}/`", "`tests/bt/battery/item_${item.id}`"),
    "item 4 may not touch item 0": ("item.id === 4 ? ['tests/bt/battery/item_0/'] : []", "[]"),
    "the whole battery is allowed": ("`tests/bt/battery/item_${item.id}/`", "`tests/bt/battery/`"),
    "never stops on a touch": ("if (outside.length) out.push", "if (false) out.push"),
}


@needs_node
@pytest.mark.parametrize("name", sorted(MUTANTS_CHECK))
def test_check_grid_catches_mutants(name):
    old, new = MUTANTS_CHECK[name]
    assert _disagreements(_mutate(old, new)) != [], f"the grid did not notice the mutant: {name}"


@needs_node
def test_quoted_paths_are_reported():
    """A quoted line (git's form for a non-ASCII name) is named by diff_scope, and the script's check reads it as
    outside even when the file is inside the battery (ROOTCAUSE_r2-2.md §5-4: the defect is in the script)."""
    q = '"tests/bt/battery/item_4/\\350\\241\\250.md"'
    assert D.quoted_lines([q, "tests/bt/battery/item_4/a.py"]) == [q]
    got = D.run_check_many([{"changed_files": [q], "item": 4}])[0]
    assert [f["id"].endswith("-touch") for f in got] == [True]


# ------------------------------------------------------------------------------------------- F3  the records
MAT_PATHS = [
    "docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-1/after_fix_pytest_battery_and_critic.txt",
    "docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r2-2/a.txt",
    "docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/battery/materials/r16-1/x.txt",
    "docs/DISCUSSIONS/2026-09-23_backtest_env/item_12/battery/materials/r1/x.txt",
    "docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_2/materials/full_suite.txt",
    "docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials_old/x.txt",
    "docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/x.txt",
    "docs/DISCUSSIONS/2026-09-23_backtest_env/item_x/battery/materials/r1/x.txt",
    "docs/DISCUSSIONS/2026-09-24_other/item_4/battery/materials/r1/x.txt",
    "tests/bt/battery/item_4/materials/x.txt",
    "docs/AUDITOR/TRACE/2026-09-26_220780c0.json",
]
MAT_RULE = re.compile(r"docs/DISCUSSIONS/2026-09-23_backtest_env/item_[0-9]+/battery/materials/")  # the rule's text


def _mat_disagreements(fn):
    return [p for p in MAT_PATHS if bool(fn(p)) != bool(MAT_RULE.match(p))]


def test_materials_classifier_grid():
    assert _mat_disagreements(D.is_materials) == []
    got = D.materials_overwrites(MAT_PATHS)
    assert got == [p for p in MAT_PATHS if MAT_RULE.match(p)]


MUTANTS_MAT = {
    "item 4 only": lambda p: p.startswith("docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/"),
    "battery/ dropped": lambda p: re.match(r"docs/DISCUSSIONS/2026-09-23_backtest_env/item_[0-9]+/.*materials/", p),
    "no separator after materials": lambda p: re.match(r"docs/DISCUSSIONS/2026-09-23_backtest_env/item_[0-9]+/battery/materials", p),
    "never": lambda p: False,
}


@pytest.mark.parametrize("name", sorted(MUTANTS_MAT))
def test_materials_classifier_catches_mutants(name):
    assert _mat_disagreements(MUTANTS_MAT[name]) != [], f"the grid did not notice the mutant: {name}"


@needs_git
def test_materials_records_are_never_rewritten():
    """The live work tree: no record of this battery's scene-keeper that HEAD holds differs from HEAD.
    Item 0's records are not read here: another scene-keeper writes them in parallel (the launch text: item 4 does
    not touch tests/bt/battery/item_0/ in this run)."""
    diff = D.git_lines(["diff", "--name-only", "HEAD"])
    over = [p for p in D.materials_overwrites(diff) if p.startswith(D.MATERIALS_OF(4))]
    assert over == [], f"records rewritten (write a new file instead): {over}"


# ------------------------------------------------------------------------------------------- F1  the section
# ROOTCAUSE files written before diff_scope.py existed keep their hand-pasted section as a record (named, not read):
BEFORE_THE_TOOL = {"ROOTCAUSE_r2-1.md": "round r2-1 pasted the diff by hand (its §9); kept as the record of that round"}
# ROOTCAUSE files written before the baseline (F4) existed: their section has no baseline and no attribution (named):
BEFORE_BASELINE = {"ROOTCAUSE_r2-2.md": "round r2-2 made its section before snapshot()/attribute() existed; kept as the record"}


def test_rootcause_diff_sections_are_machine_made():
    files = sorted(p for p in HERE.glob("ROOTCAUSE*.md") if p.name not in BEFORE_THE_TOOL)
    assert files, "no ROOTCAUSE file to read"
    for p in files:
        text = p.read_text(encoding="utf-8")
        sections = D.find_sections(text)
        assert sections, f"{p.name}: no machine-made diff section (python3 {HERE.relative_to(REPO)}/diff_scope.py --markdown)"
        assert all(ok for _, ok in sections), f"{p.name}: a diff section was edited by hand"
        if p.name not in BEFORE_BASELINE:  # from r2-3 on (F4): the section carries the baseline and the attribution
            assert D.baseline_refs(text), f"{p.name}: the diff section has no baseline (--baseline <file>)"
            assert "差分の行ごとの帰属(" in text and "検査が止める行の帰属:" in text, f"{p.name}: no attribution in the section"


def test_section_hash_catches_hand_edits():
    rep = {"head": "0" * 40, "diff": ["tests/bt/battery/item_4/a.py", "docs/AUDITOR/TRACE/t.json"],
           "status": [" M tests/bt/battery/item_4/a.py", " M docs/AUDITOR/TRACE/t.json", "?? x.txt"],
           "findings": [{"id": "bself-touch", "level": "止める", "text": "…: docs/AUDITOR/TRACE/t.json"}],
           "outside": ["docs/AUDITOR/TRACE/t.json"], "overwrites": [], "untracked_outside": ["x.txt"], "quoted": []}
    sec = D.section_markdown(rep, item=4)
    assert [ok for _, ok in D.find_sections(sec)] == [True]
    lines = sec.split("\n")
    body = [i for i, ln in enumerate(lines) if ln.startswith("docs/AUDITOR/TRACE/t.json")]
    assert body, "the section does not list the diff"
    i = body[0]
    edits = {
        "changed": lines[:i] + ["tests/bt/battery/item_4/b.py"] + lines[i + 1:],
        "dropped": lines[:i] + lines[i + 1:],
        "added": lines[:i] + ["tests/bt/battery/item_4/c.py"] + lines[i:],
    }
    for name, ls in edits.items():
        assert [ok for _, ok in D.find_sections("\n".join(ls))] == [False], name

    # F1 + F4: a section with a baseline -- a hand edit of one attribution label is caught too
    base = {"taken_at_utc": "2026-01-01T00:00:00Z", "head": "0" * 40,
            "entries": {"docs/AUDITOR/TRACE/t.json": {"status": " M", "sha256": "a" * 64}}}
    now = {"taken_at_utc": "2026-01-01T00:01:00Z", "head": "0" * 40,
           "entries": {"docs/AUDITOR/TRACE/t.json": {"status": " M", "sha256": "a" * 64},
                       "tests/bt/battery/item_4/a.py": {"status": " M", "sha256": "b" * 64}}}
    rep2 = dict(rep, baseline={"path": "docs/x/baseline.json", "sha256": "c" * 64, "snap": base},
                attribution=D.attribute(base, rep["diff"], now))
    sec2 = D.section_markdown(rep2, item=4)
    assert [ok for _, ok in D.find_sections(sec2)] == [True]
    assert D.PRE_SAME in sec2 and D.FRESH in sec2
    hand = sec2.replace(D.PRE_SAME + "\tdocs/AUDITOR/TRACE/t.json", D.FRESH + "\tdocs/AUDITOR/TRACE/t.json")
    assert hand != sec2, "the attribution line is not in the section"
    assert [ok for _, ok in D.find_sections(hand)] == [False], "an edited attribution label was not caught"


@needs_git
@needs_node
def test_scope_report_is_the_git_output():
    """The report's diff is `git diff --name-only HEAD` as git prints it, line for line (what changed_files carries)."""
    rep = D.scope_report(item=4)
    assert rep["diff"] == D.git_lines(["diff", "--name-only", "HEAD"])
    assert set(rep["outside"]) <= set(rep["diff"])


# ------------------------------------------------------------------------------------------- F4  the attribution
H0, H1 = "0" * 40, "1" * 40
SA, SB = "a" * 64, "b" * 64
P = "docs/AUDITOR/TRACE/t.json"
IN_BASE = [None, SA, "deleted"]            # not in the baseline / a file with content A / deleted at the start
NOW = [SA, SB, "deleted", "absent"]         # content A / content B / deleted now / not in `git status` now
HEADS = [H0, H1]


def _snap(head, state):
    entries = {}
    if state == "deleted":
        entries[P] = {"status": " D", "sha256": None}
    elif state not in (None, "absent"):
        entries[P] = {"status": " M", "sha256": state}
    return {"taken_at_utc": "2026-01-01T00:00:00Z", "head": head, "entries": entries}


def _answer_by_rule(start, now, head_moved):
    """ROOTCAUSE_r2-3.md §3-1, from its text: a line already in the baseline is 'already different at the start' and
    then 'unchanged' or 'changed' by its content; a line not in the baseline equalled HEAD at the start, so it changed
    during the run -- unless HEAD moved (then the start cannot be compared); a line not in `git status` now cannot be
    classified."""
    if now == "absent":
        return D.NOT_IN_STATUS
    if start is not None:
        return D.PRE_SAME if start == now else D.PRE_CHANGED
    return D.UNKNOWN if head_moved else D.FRESH


def _attr_disagreements(attribute):
    bad = []
    for start in IN_BASE:
        for now in NOW:
            for head in HEADS:
                base, cur = _snap(H0, start), _snap(head, now)
                got = attribute(base, [P], cur)
                want = [(P, _answer_by_rule(start, now, head != H0))]
                if got != want:
                    bad.append((start, now, head, got, want))
    return bad


def test_attribution_matches_rule_on_grid():
    assert _attr_disagreements(D.attribute) == []


def _mutant_attribute(old, new):
    src = (HERE / "diff_scope.py").read_text(encoding="utf-8")
    at = src.index("def attribute(")
    k, end = src.find(old, at), src.find("\ndef ", at + 1)
    assert k >= 0 and (end < 0 or k < end), f"attribute() no longer holds {old!r}; rewrite the mutant"
    ns = {"__name__": "i4_diff_scope_mutant", "__file__": str(HERE / "diff_scope.py")}
    exec(compile(src[:k] + new + src[k + len(old):], "diff_scope_mutant.py", "exec"), ns)
    return ns["attribute"]


MUTANTS_ATTR = {
    "content not compared": ('b["sha256"] == n["sha256"]', "True"),
    "head change ignored": ("elif same_head:", "elif True:"),
    "absent from the baseline counts as already there": ('b = baseline["entries"].get(p)', 'b = baseline["entries"].get(p, n)'),
    "every line unchanged": ("out.append((p, lab))", "out.append((p, PRE_SAME))"),
}


@pytest.mark.parametrize("name", sorted(MUTANTS_ATTR))
def test_attribution_grid_catches_mutants(name):
    assert _attr_disagreements(_mutant_attribute(*MUTANTS_ATTR[name])) != [], f"the grid did not notice the mutant: {name}"


def test_snapshot_parses_renames():
    """`git status --porcelain -z` prints a rename as "R  new\0old\0": the old path is not a separate entry."""
    raw = "R  tests/bt/battery/item_4/new.py\0tests/bt/battery/item_4/old.py\0 M a.txt\0?? b.txt\0"
    assert D.parse_status_z(raw) == [("R ", "tests/bt/battery/item_4/new.py"), (" M", "a.txt"), ("??", "b.txt")]


SHAPE_KEYS = {"taken_at_utc", "head", "entries"}


def _round_baselines():
    """[(ROOTCAUSE path, baseline path, sha256 in the section)] for every ROOTCAUSE from r2-3 on."""
    out = []
    for p in sorted(HERE.glob("ROOTCAUSE*.md")):
        if p.name in BEFORE_THE_TOOL or p.name in BEFORE_BASELINE:
            continue
        refs = D.baseline_refs(p.read_text(encoding="utf-8"))
        assert refs, f"{p.name}: the diff section has no baseline (python3 diff_scope.py --markdown --baseline <file>)"
        out += [(p, REPO / rel, h) for rel, h in refs]
    return out


def test_baseline_file_has_snapshot_shape():
    for _, b, h in _round_baselines():
        snap = D.load_baseline(b, h)
        assert set(snap) == SHAPE_KEYS
        assert all(set(e) == {"status", "sha256"} for e in snap["entries"].values())


@needs_git
def test_live_snapshot_has_the_same_shape():
    snap = D.snapshot()
    assert set(snap) == SHAPE_KEYS
    assert all(set(e) == {"status", "sha256"} for e in snap["entries"].values())


def test_rootcause_baseline_predates_the_round():
    """The baseline was taken before the round wrote anything: neither the round's ROOTCAUSE nor any other record next
    to the baseline is in it (the round's own files did not exist yet when it was taken)."""
    rounds = _round_baselines()
    assert rounds, "no ROOTCAUSE from r2-3 on"
    for rc, b, h in rounds:
        snap = D.load_baseline(b, h)
        own = [str(rc.relative_to(REPO))] + [str(x.relative_to(REPO)) for x in b.parent.iterdir() if x != b]
        early = [x for x in own if x in snap["entries"]]
        assert early == [], f"{rc.name}: the baseline already holds files of its own round: {early}"
