"""V3 adversary: the checks and the resolutions against an oracle written
from the definitions (anomalies.py docstring) with plain loops over the
rows as the test wrote them -- not the implementation's grouping.

Inputs are drawn from seeds (400 trade datasets, 400 bar datasets, 1..3
files each): repeated ids / starts with the same or different values, a
price written two ways ("100" / "100.0" = the same value), an extra column
that differs, backward steps inside a file, empty ids, overlapping and
disjoint generations, missing and off-grid bars. For each dataset the
anomaly multiset (kind, t_ns, file, line) must equal the oracle's, and the
events after every combination of policies must equal the oracle's rows in
the oracle's order; an unnamed kind must refuse.
Not drawn: rows the core refuses (price <= 0 -- the parse tests), keys
other than id / start (the "time" key goes through the same code as id).
"""
from __future__ import annotations

import datetime as dt
import itertools
import random

import pytest

from bot.bt.data import SpecError, UnresolvedAnomalyError, load

NS = 10**9
T0 = int(dt.datetime(2026, 1, 5, tzinfo=dt.timezone.utc).timestamp()) * NS
IV = 60 * NS


def iso(t):
    s, f = divmod(t, NS)
    return dt.datetime.fromtimestamp(s, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + f".{f:09d}Z"


def trade_spec():
    return {"format": "csv", "header": True, "delimiter": ",", "kind": "trade", "symbol": "X", "asset": "crypto",
            "time": {"columns": ["t"], "unit": "iso", "tz": "UTC"},
            "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"}, "side_map": {"B": "buy"}, "key": "id"}


def bar_spec():
    return {"format": "csv", "header": True, "delimiter": ",", "kind": "bar", "symbol": "X", "asset": "crypto",
            "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
            "fields": {"open": "c", "high": "c", "low": "c", "close": "c", "volume": "v"},
            "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start"}


def gen_trades(rng):
    files = []
    for _ in range(rng.randint(1, 3)):
        t = T0 + rng.randrange(0, 20) * NS
        rows = []
        for _ in range(rng.randint(1, 12)):
            t += rng.choice([0, 1, 1, 2, 3]) * NS if rng.random() > 0.15 else -rng.randrange(1, 4) * NS
            i = rng.choice(["", str(rng.randrange(1, 9))]) if rng.random() < 0.2 else str(rng.randrange(1, 9))
            px = rng.choice(["100", "100.0", "101"])
            note = rng.choice(["a", "a", "b"])
            rows.append((i, max(t, T0), px, note))
        files.append(rows)
    return files


def gen_bars(rng):
    files = []
    for _ in range(rng.randint(1, 3)):
        k = rng.randrange(0, 8)
        rows = []
        for _ in range(rng.randint(1, 10)):
            k += rng.choice([1, 1, 1, 2, 3, 0]) if rng.random() > 0.1 else -rng.randrange(1, 3)
            off = rng.choice([0] * 12 + [30 * NS])
            st = T0 + max(k, 0) * IV + off
            rows.append((st, rng.choice(["100", "100.0", "102"]), rng.choice(["1", "2"])))
        files.append(rows)
    return files


def write(tmp, kind, files):
    paths = []
    for j, rows in enumerate(files):
        p = f"backtest_data/gen_{j}/f.csv"
        (tmp / f"backtest_data/gen_{j}").mkdir(parents=True, exist_ok=True)
        if kind == "trade":
            text = "id,t,price,size,side,note\n" + "".join(f"{i},{iso(t)},{px},1,B,{n}\n" for i, t, px, n in rows)
        else:
            text = "ts,c,v\n" + "".join(f"{iso(st)},{c},{v}\n" for st, c, v in rows)
        (tmp / p).write_text(text)
        paths.append(p)
    return paths


def oracle(kind, files):
    """Rows: dict(file, line, t, key, same) where `same` is what the duplicate
    check compares; anomalies as (kind, t, file, line)."""
    rows = []
    for fi, rs in enumerate(files):
        for li, r in enumerate(rs, start=2):
            if kind == "trade":
                i, t, px, note = r
                rows.append({"file": fi, "line": li, "t": t, "key": i if i else None,
                             "same": (i, t, float(px), note), "ev_t": t, "val": (i, float(px))})
            else:
                st, c, v = r
                rows.append({"file": fi, "line": li, "t": st, "key": st, "same": (st, float(c), float(v)),
                             "ev_t": st + IV, "val": (st, float(c))})
    out = []
    for n, r in enumerate(rows):  # backward: within the file
        earlier = [x["t"] for x in rows[:n] if x["file"] == r["file"]]
        if earlier and r["t"] < max(earlier):
            out.append(("backward", r["t"], r["file"], r["line"], n))
    for n, r in enumerate(rows):  # duplicate / conflict: against the first row with the key
        if r["key"] is None:
            continue
        firsts = [x for x in rows[:n] if x["key"] == r["key"]]
        if firsts:
            out.append(("duplicate" if firsts[0]["same"] == r["same"] else "conflict", r["t"], r["file"], r["line"], n))
    spans = {}
    for r in rows:
        spans.setdefault(r["file"], []).append(r["t"])
    spans = {f: (min(v), max(v)) for f, v in spans.items()}
    if len(files) > 1:
        for n, r in enumerate(rows):
            others = [f for f, (lo, hi) in spans.items() if f != r["file"] and lo <= r["t"] <= hi]
            if r["key"] is None:
                if others:
                    out.append(("unkeyed_overlap", r["t"], r["file"], r["line"], n))
                continue
            if any(not any(x["key"] == r["key"] for x in rows if x["file"] == f) for f in others):
                out.append(("generation_gap", r["t"], r["file"], r["line"], n))
    if kind == "bar" and rows:
        s0 = min(r["t"] for r in rows)
        s1 = max(r["t"] for r in rows)
        for n, r in enumerate(rows):
            if (r["t"] - s0) % IV != 0:
                out.append(("off_grid", r["t"], r["file"], r["line"], n))
        have = {r["t"] for r in rows}
        s = s0
        while s <= s1:
            if s not in have:
                out.append(("gap", s, None, None, None))
            s += IV
    return rows, out


def oracle_resolve(rows, anoms, pol):
    drop = set()
    for k, _, _, _, n in anoms:
        if k == "duplicate":
            drop.add(n)
        if k == "backward" and pol.get("backward") == "drop":
            drop.add(n)
        if k == "off_grid" and pol.get("off_grid") == "drop":
            drop.add(n)
    ckeys = {rows[n]["key"] for k, _, _, _, n in anoms if k == "conflict"}
    for key in ckeys:
        idx = [n for n, r in enumerate(rows) if r["key"] == key]
        keep = idx[0] if pol["conflict"] == "keep_first" else idx[-1]
        drop.update(n for n in idx if n != keep)
    kept = [r for n, r in enumerate(rows) if n not in drop]
    return [r["val"] for r in sorted(kept, key=lambda r: r["ev_t"])]


SEEDS = [("trade", s) for s in range(400)] + [("bar", s) for s in range(400)]
POLICY_GRID = [dict(zip(("conflict", "backward", "off_grid"), c))
               for c in itertools.product(("keep_first", "keep_last"), ("drop", "sort"), ("accept", "drop"))]


@pytest.mark.parametrize("kind,seed", SEEDS, ids=[f"{k}{s}" for k, s in SEEDS])
def test_anomalies_and_resolutions_match_the_oracle(tmp_path, kind, seed):
    rng = random.Random(seed * 7919 + (kind == "bar"))
    files = gen_trades(rng) if kind == "trade" else gen_bars(rng)
    paths = write(tmp_path, kind, files)
    res = load(str(tmp_path), [{"name": "d", "paths": paths, "spec": trade_spec() if kind == "trade" else bar_spec()}])
    rows, want = oracle(kind, files)
    got = sorted((a["kind"], a["t_ns"], a["file"], a["line"]) for a in res.anomalies("d"))
    assert got == sorted(w[:4] for w in want)
    kinds = {w[0] for w in want}
    if kinds:
        with pytest.raises(UnresolvedAnomalyError):
            res.events("d")
    for pol in POLICY_GRID:
        full = {"duplicate": "drop", "gap": "accept", "generation_gap": "accept", "unkeyed_overlap": "accept", **pol}
        evs = res.events("d", full)
        if kind == "trade":
            vals = [(e.trade_id, e.price) for e in evs]
        else:
            vals = [(e.start_time_ns, e.close) for e in evs]
        assert vals == oracle_resolve(rows, want, full)
        times = [int(e.exchange_time_ns) for e in evs]
        assert times == sorted(times)


def test_a_clean_dataset_needs_no_policy_and_records_keep_file_order(tmp_path):
    files = [[("1", T0, "100", "a"), ("2", T0 + NS, "100", "a")]]
    paths = write(tmp_path, "trade", files)
    res = load(str(tmp_path), [{"name": "d", "paths": paths, "spec": trade_spec()}])
    assert res.anomalies("d") == [] and len(res.events("d")) == 2
    assert res.checks("d") == ["backward", "duplicate", "conflict"]


def test_checks_that_cannot_run_are_not_listed(tmp_path):
    files = [[("1", T0, "100", "a")]]
    paths = write(tmp_path, "trade", files)
    sp = trade_spec()
    del sp["key"]
    res = load(str(tmp_path), [{"name": "d", "paths": paths, "spec": sp}])
    assert res.checks("d") == ["backward"]


@pytest.mark.parametrize("bad", [{"conflict": "merge"}, {"nonsense": "drop"}, {"backward": "accept"}])
def test_unknown_policies_are_refused(tmp_path, bad):
    files = [[("1", T0, "100", "a")]]
    paths = write(tmp_path, "trade", files)
    res = load(str(tmp_path), [{"name": "d", "paths": paths, "spec": trade_spec()}])
    with pytest.raises(SpecError):
        res.events("d", bad)


def test_the_seeds_exercise_every_kind():
    seen = {}
    for kind, seed in SEEDS:
        rng = random.Random(seed * 7919 + (kind == "bar"))
        files = gen_trades(rng) if kind == "trade" else gen_bars(rng)
        for w in oracle(kind, files)[1]:
            seen[w[0]] = seen.get(w[0], 0) + 1
    assert all(seen.get(k, 0) >= 20 for k in ("duplicate", "conflict", "backward", "gap", "off_grid",
                                                "generation_gap", "unkeyed_overlap")), seen
