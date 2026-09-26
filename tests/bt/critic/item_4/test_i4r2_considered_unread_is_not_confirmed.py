"""Item 4 critic, round 2 (i4-r2-04): a row of the considered table may be 「持たないと確認した」 only when the
absence was SHOWN (場面集の規則 6: 「その能力の口が無いことを行を引いて示したとき」), never on a part that was
not read.

Round 2 (i4-r1-08) put the words 「読んでいない」「読んだ範囲に無い」「再現していない」 into
gen_considered.UNVERIFIED and matches them as substrings. A reason written 「読んだ範囲(backtesting_broker.py・
order.py)に無い」 -- the same statement with the files read in parentheses -- does not contain the substring
「読んだ範囲に無い」, so the machine counts it as a shown absence.

Grid: every row of tests/bt/battery/item_4/opponents/CONSIDERED.md whose judgement is 「持たないと確認した」 x the
statements of not having read / not having checked, matched with anything in between (「読んだ範囲 … に無い」,
「読んでいない」, 「確かめていない」, 「未確認」). Expected: none.
"""
from __future__ import annotations

import re
from pathlib import Path

CONSIDERED = Path(__file__).resolve().parents[2] / "battery" / "item_4" / "opponents" / "CONSIDERED.md"
UNREAD = re.compile(r"読んだ範囲.{0,120}?に無い|読んでいない|確かめていない|未確認")


def _rows():
    out = []
    for line in CONSIDERED.read_text(encoding="utf-8").splitlines():
        cols = [c.strip() for c in line.split("|")]
        if len(cols) >= 6 and cols[4] == "持たないと確認した":
            out.append((cols[1], cols[5]))
    return out


def test_the_table_has_confirmed_rows():
    assert len(_rows()) > 0


def test_no_confirmed_absence_rests_on_an_unread_part():
    bad = [(name, m.group(0)) for name, why in _rows() for m in [UNREAD.search(why)] if m]
    assert bad == [], bad
