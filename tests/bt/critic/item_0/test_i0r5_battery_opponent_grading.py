"""Critic, item 0, round 5: two opponent cells of the scene set's table that
are graded 正解と一致 although the opponent does not show the capability.
Both are on the scene-set side (場面係の持ち物); the tests read the recorded
survey results and the adapters, and do not change them.

i0-r5-02 -- Basana (candidate 1) and the event types it has no class for.
The fixed requirements (REQUIREMENTS.md section 2, P0-3) measure the types
as "型ごとに 1 件ずつ投入し、核が拒否せず対応する事象として保持するかを見る
(型が無ければ「対応なし」)". Basana 1.11's public event classes are
`Event` (the base) and `BarEvent` only (`dir(basana)` in the survey venv:
['BarEvent', 'Event', 'EventDispatcher', 'EventSource',
'FifoQueueEventSource']). The adapter defines its own `Generic(bs.Event)`
with a `kind` string and a `fields` dict and sends trade, book snapshot,
book delta, funding and liquidation through it; its own detail says
"basana.Event の子(Basana に無い型)で渡した". Those cells are graded
正解と一致, and for p3-funding, p3-mixed-one-run and p1-merge-by-time Basana
is the ONLY opponent graded 正解と一致, so the survey side's best row takes
them from the adapter's class.

i0-r5-03 -- hftbacktest (candidate 23) and p4-future-read-attempt. The
scene tells every adapter to try, for each public read, every way of naming
the 5th bar ("当てはまる名指し方を全部試し"); the new implementation's
adapter tries the index and the open slices ([4], [4:], [4::2], [4:4], ...),
round 4 having shown that an open slice from the next position is a way of
naming it (i0-r4-01). The hftbacktest adapter tries only
`hbt.last_trades(0)[len]` (IndexError) on the same kind of read (an array
of the delivered trades). In the survey venv, the same probe with
`hbt.last_trades(0)[len:]` added returns [] silently and the runner grades
every_attempt_stopped_by_error = False; the recorded cell says 正解と一致.
"""
from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path

import pytest

BATTERY = Path(__file__).resolve().parents[2] / "battery" / "item_0"
csv.field_size_limit(10**9)


def _cells(target: str) -> dict[str, dict]:
    path = BATTERY / "survey_results" / f"{target}.tsv"
    with path.open(encoding="utf-8") as fh:
        return {r["scene_id"]: r for r in csv.DictReader(fh, delimiter="\t")}


# The six P0-3 cells of Basana that i0-r5-02 was about. Round 6 critic (rule 8 of the
# scene set): the round-5 version asserted `"class Generic(bs.Event)" in adapter`, i.e.
# the adapter's OLD shape, so it failed as soon as the carrier class was removed -- an
# error of the test itself. It also assumed Basana 1.11 has no trade / book classes
# (`dir(basana)` lists top-level names only); the distribution has them under
# `basana.external.*`. The property the test is for is kept and read from the
# records instead: a cell graded 正解と一致 must rest on carriers whose class file is
# in Basana's own distribution (never the scene set's modules), and the types Basana
# has no class for (funding, liquidation, and the run that mixes them in) are not
# graded 正解と一致.
_NO_CLASS_IN_BASANA = ["p3-trade", "p3-book_snapshot", "p3-book_delta", "p3-funding", "p3-liquidation",
                       "p3-mixed-one-run"]
_BASANA_HAS_NO_TYPE = {"p3-funding", "p3-liquidation", "p3-mixed-one-run"}


@pytest.mark.parametrize("scene_id", _NO_CLASS_IN_BASANA)
def test_basana_is_not_credited_with_an_event_type_its_adapter_wrote(scene_id):
    import json

    cell = _cells("opp_basana")[scene_id]
    if scene_id in _BASANA_HAS_NO_TYPE:
        assert cell["correctness"] != "正解と一致", (
            f"{scene_id}: Basana is graded 正解と一致 for a type its distribution has no class for; "
            f"the fixed measurement of P0-3 says 型が無ければ「対応なし」 (detail: {cell['detail_1'][:160]!r})"
        )
        return
    if cell["correctness"] != "正解と一致":
        return
    carriers = json.loads(cell["provenance_1"])["carriers"]
    assert carriers, f"{scene_id}: 正解と一致 without any recorded carrier"
    for c in carriers:
        tf = c.get("type_file") or ""
        assert "/site-packages/basana/" in tf, (
            f"{scene_id}: the carrier {c.get('type')!r} is defined in {tf!r}, not in Basana's distribution"
        )
        assert "/tests/bt/battery/" not in tf, f"{scene_id}: carrier class from the scene set: {tf!r}"


def test_funding_best_cell_of_the_survey_side_does_not_rest_only_on_an_adapter_made_type():
    import glob

    correct = []
    for f in sorted(glob.glob(str(BATTERY / "survey_results" / "*.tsv"))):
        cells = _cells(Path(f).stem)
        if cells.get("p3-funding", {}).get("correctness") == "正解と一致":
            correct.append(Path(f).stem)
    assert correct != ["opp_basana"], (
        "the survey side's best p3-funding cell is 正解と一致 only through opp_basana, whose funding "
        "event is the adapter's own subclass of basana.Event"
    )


_VENV_PY = Path("/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/venvs/"
                "item_0/hftbacktest/bin/python")

_PROBE = r'''
import sys, types
sys.path[:0] = [".", "adapters", "opponents"]
import scenes, run_battery
import opponents.hftbacktest_adapter as H
src = open("opponents/hftbacktest_adapter.py", encoding="utf-8").read()
anchor = 'att.run("この呼び出しで届いた約定(last_trades)"'
assert anchor in src
src = src.replace(anchor, 'att.run("hbt.last_trades(0)[len:]", "position", '
                  'lambda: list(hbt.last_trades(0)[len(hbt.last_trades(0)):]))\n            ' + anchor, 1)
mod = types.ModuleType("hft_copy"); mod.__file__ = H.__file__
exec(compile(src, "hft_copy", "exec"), mod.__dict__)
cls = [v for v in mod.__dict__.values() if isinstance(v, type) and hasattr(v, "scene_p4_future_read_attempt")][0]
sc = next(s for s in scenes.SCENES if s.id == "p4-future-read-attempt")
g = run_battery.graded_output(cls().scene_p4_future_read_attempt(sc), sc, "opp_hftbacktest")
print("STOPPED=%s" % g["every_attempt_stopped_by_error"])
'''


def test_hftbacktest_p4_cell_holds_when_the_open_slice_is_tried_too():
    cell = _cells("opp_hftbacktest")["p4-future-read-attempt"]
    if cell["correctness"] != "正解と一致":
        return
    if not _VENV_PY.exists():
        pytest.skip(f"the survey venv of hftbacktest is not here ({_VENV_PY}); run by the critic of round 5")
    out = subprocess.run([str(_VENV_PY), "-c", _PROBE], cwd=BATTERY, capture_output=True, text=True,
                         timeout=300, env={**os.environ, "PYTHONPATH": str(BATTERY)})
    assert out.returncode == 0, out.stderr[-2000:]
    assert "STOPPED=True" in out.stdout, (
        "opp_hftbacktest is recorded 正解と一致 on p4-future-read-attempt, but its public read "
        "hbt.last_trades(0)[len:] -- the open slice from the next position, which the new implementation's "
        "adapter tries -- returns [] silently in the same probe: " + out.stdout[-500:]
    )


def test_no_superset_skip_rests_on_basanas_generic_event_carrier():
    """i0-r5-04 (same cause as i0-r4-03): a 上位互換 row must show a RUN
    candidate's mechanism that contains each ability. Seven rows of
    CONSIDERED.md (P0-1: 13, 52, 57, 63, 123; P0-3: 11, 57) give as the
    containing mechanism "1 Basana の `basana.Event` の子 ... 型の数に上限が
    無い" -- the base class a user can subclass, i.e. the adapter's
    `Generic(bs.Event)` above. For 11 OctoBot that is the only containment of
    its native FundingChannel (能 5): no run candidate has a funding type of
    its own (only opp_basana is 正解と一致 on p3-funding, through the adapter's
    class). "A user could write it" contains every ability of every
    candidate without reading it -- the 被覆 reading the scene keeper's own
    root cause for i0-r4-03 set out to remove."""
    text = (BATTERY / "opponents" / "CONSIDERED.md").read_text(encoding="utf-8")
    heading, rows = "", []
    for line in text.splitlines():
        if line.startswith("### "):
            heading = line
        elif line.startswith("| ") and "上位互換" in line and ("basana.Event` の子" in line or "basana.Event の子" in line):
            rows.append(f"{heading.split('(')[0][4:]} {line.split('|')[1].strip()}")
    assert not rows, f"上位互換 rows whose containing mechanism is Basana's generic Event base class: {rows}"
