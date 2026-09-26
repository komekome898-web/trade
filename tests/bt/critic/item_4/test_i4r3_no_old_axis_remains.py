"""Item 4 critic, the close (i4-c, 2026-09-26, L-470 / L-474): the old axis does not come back.

The closing delegation (docs/DATA/delegations/20260926_backtest_env_item4_close.md, condition 1) withdrew the old
engine as a basis: the bar model has ONE rule set, the split has ONE arithmetic, `bot.backtest` holds names only,
and the live item-4 tree carries none of the withdrawn words. This test pins those facts so that a later edit that
re-introduces a second rule set, a second arithmetic, or arithmetic under `bot.backtest` fails here.

Control: the word scanner is exercised on a planted file (a scanner that finds nothing would pass vacuously).
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import bot.backtest.engine as be
import bot.backtest.metrics as bm
import bot.backtest.walk_forward as bw
from bot.bt import compat
from bot.bt.compat import ARITHMETICS, DECIMAL, RULES, SPEC, rules_of, split_bounds

REPO = Path(__file__).resolve().parents[4]
WORDS = re.compile("旧エンジン|完全上位互換|golden|旧の試験|旧と同じ|旧の写し|current_impl|当方の現状|legacy")
# the live item-4 tree of the close (the record files docs/AUDITOR, OWNER_LOG and the delegations are records, not
# checked here; tests/bt/battery/item_4 holds the withdrawal notes B wrote, checked by its own tests)
LIVE_DIRS = ("src/bot/backtest", "src/bot/bt/compat", "src/bot/bt/reference", "tests/bt/item_4",
             "tests/bt/critic/item_4")


def _hits(root: Path) -> list:
    out = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix in (".py", ".md", ".json", ".tsv", ".txt") and "__pycache__" not in p.parts:
            for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if WORDS.search(line):
                    rel = p.relative_to(REPO) if p.is_relative_to(REPO) else p
                    out.append((str(rel), n, line.strip()[:120]))
    return out


def test_the_live_item4_tree_holds_none_of_the_withdrawn_words():
    hits = [h for d in LIVE_DIRS for h in _hits(REPO / d)]
    # this file names the words on purpose (the pattern and this docstring); nothing else may
    hits = [h for h in hits if not h[0].endswith("test_i4r3_no_old_axis_remains.py")]
    assert hits == [], hits


def test_the_scanner_finds_a_planted_word(tmp_path):
    (tmp_path / "planted.py").write_text("x = 1  # legacy\n", encoding="utf-8")
    (tmp_path / "clean.py").write_text("x = 1\n", encoding="utf-8")
    got = _hits(tmp_path)
    assert len(got) == 1 and got[0][1] == 1 and "planted.py" in got[0][0], got


def test_one_rule_set_and_one_arithmetic():
    assert RULES == (SPEC,) == ("spec",)
    assert ARITHMETICS == (DECIMAL,) == ("decimal",)
    assert rules_of("spec") == "spec"
    for other in ("legacy", "compat", "old", "", None):
        try:
            rules_of(other)
        except ValueError:
            pass
        else:
            raise AssertionError(f"rules_of accepted {other!r}")
        try:
            split_bounds(10, 0.6, 0.2, other)
        except ValueError:
            pass
        else:
            raise AssertionError(f"split_bounds accepted arithmetic {other!r}")


def test_bot_backtest_modules_define_nothing_but_import_and_all():
    for mod in (be, bm, bw):
        tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        kinds = {type(n).__name__ for n in tree.body}
        assert kinds <= {"Expr", "ImportFrom", "Assign"}, (mod.__name__, kinds)  # docstring, imports, __all__
        assigned = [t.id for n in tree.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)]
        assert assigned == ["__all__"], (mod.__name__, assigned)
        for name in mod.__all__:
            assert getattr(mod, name) is getattr(compat, name), (mod.__name__, name)
