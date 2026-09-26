"""Adversarial grid (finishing stage, i4-r2-03): the origin of a FILE dataset is decided by its ROWS.

Rule text (finishing delegation §1 i4-r2-03, verbatim): 「出所は宣言でもファイルの中身の同一性でもなく、行の中身で
決める(読んだ行の (時刻, 値) の並びが、この環境の市場データのフォルダのファイルから読んだ行の並びと一致するか =
データ層の read を通した比較)。一致すれば実データ。合成は種つきの生成器からだけ作れる口にし、その種と生成器の版を
実行記録に残す」. bot.bt.pipeline reads it as: a file dataset is real (declaring it synthetic is refused); its rows,
read through the data layer, are compared with the rows of this environment's market files read through the data
layer with the same declaration; a row equal in time and every value is the evidence.

WHAT IS JUDGED REAL MARKET DATA, BY EVIDENCE (the rows): the market file itself; recompressed (another gzip header);
decompressed; cut to a part (the first rows, rows in the middle); one row's value edited by one byte (the other rows
still match: rows_matched = rows_read - 1); the columns reordered (the data layer's normalised rows are the same).
WHAT IS NOT MATCHED (evidence "unmatched", the dataset STILL real by the rule, so §4 still applies): every row edited
(no row equal to a market row); market data that exists only outside this environment (the owner's PC); a market
file whose rows are sealed (the data layer refuses the sealed rows, recorded in sealed_skipped); a market file the
first/last-row time bounds miss (its rows out of time order); zip files (the data layer reads none / gzip only).

Grid: market file {FX event ticks (quotes), TOPIX futures 1-minute bars} x way {as_is (a byte copy under another
name), regzip, decompressed, first_rows, middle_rows, one_byte_edit, every_row_edited, columns_reordered} x declared
{real, synthetic} x strategy {schedule, price_rule} under 動作確認 = 2 x 8 x 2 x 2 = 64 cells, planned only.
Expected: declared synthetic -> refused; price_rule -> refused (real data, 動作確認: 委任文 §4); schedule + real ->
accepted, origin real, evidence "rows" with the counts above, or "unmatched" for every_row_edited.
Skipped only when a market file is not in this environment.
"""
from __future__ import annotations

import gzip
import itertools
import os
import shutil
import tempfile
from pathlib import Path

import pytest

import i4w_decl as D
import test_i4_r2_origin_from_data_grid as G
from bot.bt.pipeline import PipelineError, plan_pipeline

REPO = Path(__file__).resolve().parents[3]
WAYS = ("as_is", "regzip", "decompressed", "first_rows", "middle_rows", "one_byte_edit", "every_row_edited",
        "columns_reordered")
CELLS = list(itertools.product(sorted(G.MARKET), WAYS, ("real", "synthetic"), ("schedule", "price_rule")))


def _edit_last_field(line: bytes) -> bytes:
    return line + b"1"  # the last column's value gains a digit: another value


def _rewrite(src: Path, dst: str, way: str) -> dict:
    raw_gz = src.read_bytes()
    raw = gzip.decompress(raw_gz)
    lines = raw.rstrip(b"\n").split(b"\n")
    head, body = lines[0], lines[1:]
    if way == "as_is":
        with open(dst, "wb") as fh:
            fh.write(raw_gz)
        return {}
    if way == "first_rows":
        body = body[:200]
    elif way == "middle_rows":
        k = len(body) // 2
        body = body[k:k + 200]
    elif way == "one_byte_edit":
        body = body[:]
        body[len(body) // 3] = _edit_last_field(body[len(body) // 3])
    elif way == "every_row_edited":
        body = [_edit_last_field(b) for b in body]
    elif way == "columns_reordered":
        def swap(b: bytes) -> bytes:
            c = b.split(b",")
            c[-1], c[-2] = c[-2], c[-1]
            return b",".join(c)
        head, body = swap(head), [swap(b) for b in body]
    out = b"\n".join([head] + body) + b"\n"
    if way == "decompressed":
        with open(dst, "wb") as fh:
            fh.write(out)
        return {"compression": "none"}
    with open(dst, "wb") as fh:
        fh.write(gzip.compress(out, mtime=12345))
    return {}


@pytest.fixture(scope="module")
def tmp_root():
    for rel, _ in G.MARKET.values():
        if not (REPO / rel).is_file():
            pytest.skip(f"{rel} is not in this environment")
    tmp = tempfile.mkdtemp(prefix="i4w_rows_")
    os.makedirs(os.path.join(tmp, "data"))
    for name, (rel, _) in G.MARKET.items():
        for way in WAYS:
            _rewrite(REPO / rel, os.path.join(tmp, "data", f"{name}_{way}" + (".csv" if way == "decompressed" else ".csv.gz")), way)
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.parametrize("name,way,origin,strat", CELLS, ids=["-".join(c) for c in CELLS])
def test_origin_by_rows(tmp_root, name, way, origin, strat):
    rel, spec = G.MARKET[name]
    spec = dict(spec)
    if way == "decompressed":
        spec["compression"] = "none"
    path = f"data/{name}_{way}" + (".csv" if way == "decompressed" else ".csv.gz")
    kind = "bar" if name == "jpx_1m" else "quote"
    ds = [{"name": name, "paths": [path], "spec": spec, "origin": origin,
           **({"resolve": {"backward": "sort"}} if kind == "bar" else {})}]
    call = dict(root=tmp_root, datasets=ds, instruments=[D.instrument(name, name, kind)], strategy=G.STRATS[strat],
                purpose="動作確認", **D.kw())
    if origin == "synthetic" or strat == "price_rule":
        with pytest.raises(PipelineError):
            plan_pipeline(**call)
        return
    plan = plan_pipeline(**call)
    d = plan.datasets[0]
    assert d["origin"] == "real"
    ev = d["origin_evidence"]
    if way == "every_row_edited":
        assert ev["by"] == "unmatched" and ev["rows_matched"] == 0, ev
        return
    assert ev["by"] == "rows", ev
    want = ev["rows_read"] - 1 if way == "one_byte_edit" else ev["rows_read"]
    assert ev["rows_matched"] == want, ev
    assert plan.identity["datasets"][0]["origin_evidence"] == ev
