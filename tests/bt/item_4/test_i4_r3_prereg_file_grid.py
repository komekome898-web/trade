"""Adversarial grid (finishing stage, i4-r2-05): a 研究 run needs its pre-registration FILE.

Rule text (finishing delegation §1 i4-r2-05, verbatim): 「事前登録はファイルとして受け取り(項目 3 の
repro/runner.py と同じ形)、その sha256 を計算して実行記録に残す。文字列の hash は受けない」 + 委任文 §4
「目的 `研究` の実行は事前登録のハッシュが無いと作れない」.

Grid: pre-registration {none, a bare hash string only, a file that does not exist, an empty file, a file with
content, a file with content AND a hash string} x purpose {動作確認, 研究} = 12 cells, on a generated (synthetic)
dataset and the schedule strategy, planned only. Expected from the text: a hash string is refused in every cell
(「文字列の hash は受けない」); a missing or empty file is refused; 研究 without a file is refused; a file with content
gives identity["prereg_sha256"] = sha256 of the file's bytes, for either purpose.
Not in the grid: the file's content itself (any non-empty bytes are a pre-registration here; what a
pre-registration must say is the research protocol's, not this run's).
"""
from __future__ import annotations

import hashlib
import itertools
import os
import shutil
import tempfile

import pytest

import i4w_decl as D
from bot.bt.pipeline import PipelineError, plan_pipeline

NS = 1_000_000_000
T0 = 1767571200 * NS
KINDS = ("none", "hash_only", "missing_file", "empty_file", "file", "file_and_hash")
CELLS = list(itertools.product(KINDS, ("動作確認", "研究")))
CONTENT = b"pre-registration: hypothesis, measure, MDE (test content)\n"


@pytest.fixture(scope="module")
def root():
    tmp = tempfile.mkdtemp(prefix="i4w_prereg_")
    with open(os.path.join(tmp, "PREREG.md"), "wb") as fh:
        fh.write(CONTENT)
    with open(os.path.join(tmp, "EMPTY.md"), "wb") as fh:
        fh.write(b"  \n")
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.parametrize("kind,purpose", CELLS, ids=["-".join(c) for c in CELLS])
def test_prereg_is_a_file(root, kind, purpose):
    gen = {"name": "random_walk", "seed": 3, "params": {"kind": "bar", "start_ns": T0, "step_ns": 60 * NS, "n": 30,
                                                        "price0": 100.0, "step_pct": 0.2, "qty": 1.0}}
    extra = {"none": {}, "hash_only": {"prereg_sha256": hashlib.sha256(CONTENT).hexdigest()},
             "missing_file": {"prereg": "NOPE.md"}, "empty_file": {"prereg": "EMPTY.md"}, "file": {"prereg": "PREREG.md"},
             "file_and_hash": {"prereg": "PREREG.md", "prereg_sha256": hashlib.sha256(CONTENT).hexdigest()}}[kind]
    call = dict(root=root, datasets=[{"name": "g", "generator": gen}], instruments=[D.instrument("g", "g", "bar")],
                strategy={"kind": "schedule", "orders": [{"t_ns": T0 + 120 * NS, "side": "buy", "qty": 1.0},
                                                         {"t_ns": T0 + 600 * NS, "side": "sell", "qty": 1.0}]},
                purpose=purpose, **D.kw(), **extra)
    ok = kind == "file" or (kind == "none" and purpose == "動作確認")
    if not ok:
        with pytest.raises(PipelineError):
            plan_pipeline(**call)
        return
    plan = plan_pipeline(**call)
    want = hashlib.sha256(CONTENT).hexdigest() if kind == "file" else None
    assert plan.identity["prereg_sha256"] == want
