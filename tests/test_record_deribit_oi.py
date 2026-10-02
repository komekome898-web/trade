"""Tests for scripts/record_deribit_oi.py -- forward recorder of Deribit
option open interest per instrument. All network is replaced by a fake
session; the payload reproduces the shape measured on 2026-10-02."""
from __future__ import annotations

import builtins
import csv
import gzip
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import record_deribit_oi as rdo  # noqa: E402


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.headers = {}

    def json(self):
        return self._payload


class FakeSession:
    """GET routed by params["currency"]; a value may be an Exception, a
    FakeResponse, or a list consumed one per call."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, dict(params or {})))
        v = self.routes[params["currency"]]
        if isinstance(v, list):
            v = v.pop(0)
        if isinstance(v, Exception):
            raise v
        return v


def book(us_out, names=("BTC-9OCT26-81000-P", "BTC-9OCT26-90000-C")):
    return {"jsonrpc": "2.0", "usIn": us_out - 100, "usOut": us_out,
            "result": [{"instrument_name": n, "creation_timestamp": 1790914766456,
                        "open_interest": 480.9, "mark_iv": 35.61,
                        "underlying_index": "BTC-9OCT26", "base_currency": "BTC",
                        "quote_currency": "BTC", "some_future_key": 1}
                       for n in names]}


def _rows(path):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


def _today():
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def test_columns_and_day_file(tmp_path):
    s = FakeSession({"BTC": FakeResponse(book(1790915115006694))})
    rec = rdo.DeribitOiRecorder(out_dir=tmp_path, session=s, currencies=("BTC",))
    assert rec.run_once() == {"BTC": 2}
    rows = _rows(tmp_path / f"book_{_today()}.csv.gz")
    assert rows[0] == rdo.FIELDS
    assert len(rows) == 3
    r = dict(zip(rows[0], rows[1]))
    assert r["us_out"] == "1790915115006694"           # source time
    assert r["ts_recv_utc"].startswith(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    assert r["currency"] == "BTC"
    assert r["instrument_name"] == "BTC-9OCT26-81000-P"
    assert r["open_interest"] == "480.9"
    assert r["high"] == ""                               # missing key -> blank
    assert "some_future_key" not in rows[0]
    assert s.calls[0][1] == {"currency": "BTC", "kind": "option"}


def test_same_response_twice_is_written_once(tmp_path):
    s = FakeSession({"BTC": [FakeResponse(book(111)), FakeResponse(book(111)),
                             FakeResponse(book(222))]})
    rec = rdo.DeribitOiRecorder(out_dir=tmp_path, session=s, currencies=("BTC",))
    assert rec.run_once() == {"BTC": 2}
    assert rec.run_once() == {"BTC": 0}
    assert rec.run_once() == {"BTC": 2}
    assert len(_rows(tmp_path / f"book_{_today()}.csv.gz")) == 1 + 4


def test_nothing_is_read_back_at_start(tmp_path, monkeypatch):
    """Before: every 15-minute run read yesterday's and today's book files
    back (about 2 s and 440 MB by the end of a day) to restore keys that can
    never match, since us_out is the response time. A new run only checks the
    end of the file it appends to."""
    s1 = FakeSession({"BTC": FakeResponse(book(111))})
    rdo.DeribitOiRecorder(out_dir=tmp_path, session=s1, currencies=("BTC",)).run_once()
    read = []
    monkeypatch.setattr(rdo, "read_gz_rows", lambda p: read.append(p) or [])
    s2 = FakeSession({"BTC": FakeResponse(book(112))})
    rec2 = rdo.DeribitOiRecorder(out_dir=tmp_path, session=s2, currencies=("BTC",))
    assert rec2.seen == set() and read == []
    assert rec2.run_once() == {"BTC": 2}
    assert [r[1] for r in _rows(tmp_path / f"book_{_today()}.csv.gz")[1:]] == \
        ["111", "111", "112", "112"]


def test_duplicate_instrument_within_one_response_written_once(tmp_path):
    s = FakeSession({"BTC": FakeResponse(book(333, names=("A", "A", "B")))})
    rec = rdo.DeribitOiRecorder(out_dir=tmp_path, session=s, currencies=("BTC",))
    assert rec.run_once() == {"BTC": 2}


def test_failure_is_recorded_and_other_currency_continues(tmp_path):
    s = FakeSession({"BTC": requests.exceptions.ConnectTimeout("boom"),
                     "ETH": FakeResponse(book(444, names=("ETH-X",)))})
    rec = rdo.DeribitOiRecorder(out_dir=tmp_path, session=s,
                                currencies=("BTC", "ETH"))
    assert rec.run_once() == {"BTC": -1, "ETH": 1}
    err = _rows(tmp_path / f"errors_{_today()}.csv.gz")
    assert err[0] == rdo.ERROR_FIELDS
    assert err[1][1:3] == ["deribit", "get_book_summary_by_currency BTC"]
    assert "ConnectTimeout" in err[1][3]
    assert len(_rows(tmp_path / f"book_{_today()}.csv.gz")) == 2


def test_http_error_and_bad_shape_are_recorded(tmp_path):
    s = FakeSession({"BTC": [FakeResponse({}, status_code=429),
                             FakeResponse({"usOut": 1, "result": []})]})
    rec = rdo.DeribitOiRecorder(out_dir=tmp_path, session=s, currencies=("BTC",))
    assert rec.run_once() == {"BTC": -1}
    assert rec.run_once() == {"BTC": -1}
    err = _rows(tmp_path / f"errors_{_today()}.csv.gz")
    assert "HTTP 429" in err[1][3]
    assert "no result list" in err[2][3]
    assert not (tmp_path / f"book_{_today()}.csv.gz").exists()


from bot.research.gz_members import iter_members_in_order  # noqa: E402


def _before_cut(path):
    out = []
    for m in iter_members_in_order(path.read_bytes()):
        if not m.complete:
            break
        out += list(csv.reader(m.payload.decode("utf-8").splitlines()))
    return out


def test_kill_mid_write_then_next_run_renames_the_file_and_keeps_both_parts(tmp_path):
    """spec r2 sec 3-2: a run killed in the middle of its append. The next
    run (a) leaves the earlier snapshot readable in the renamed file and (b)
    starts a new file that plain gzip reads end to end. Nothing is cut."""
    s = FakeSession({"BTC": FakeResponse(book(555))})
    rdo.DeribitOiRecorder(out_dir=tmp_path, session=s, currencies=("BTC",)).run_once()
    path = tmp_path / f"book_{_today()}.csv.gz"
    junk = random.Random(3).randbytes(400).hex()
    member = gzip.compress(f"x,{junk}\n".encode())
    with open(path, "ab") as f:            # the killed run's half-written member
        f.write(member[: len(member) // 2])
    before = path.read_bytes()
    rec = rdo.DeribitOiRecorder(out_dir=tmp_path,
                                session=FakeSession({"BTC": FakeResponse(book(556))}),
                                currencies=("BTC",))
    assert rec.run_once() == {"BTC": 2}
    moved = tmp_path / f"book_{_today()}.trunc1.csv.gz"
    assert moved.read_bytes() == before
    old = _before_cut(moved)
    assert old[0] == rdo.FIELDS and [r[1] for r in old[1:]] == ["555", "555"]   # (a)
    rows = _rows(path)                                                         # (b)
    assert rows[0] == rdo.FIELDS and [r[1] for r in rows[1:]] == ["556", "556"]


def test_book_with_the_magic_inside_a_healthy_member_is_appended_to(tmp_path):
    """The second critic's reproduction (false_magic2.py): the book file holds
    one healthy member whose compressed bytes contain 1f 8b 08 (an earlier
    run's append). The first version cut the file at the false boundary,
    after which no gzip reader could read it. Now it is neither cut nor
    renamed, and every row reads with plain gzip."""
    def book_text(seed):
        r = random.Random(seed)
        rows = [",".join(["2026-10-02T06:15:00.000+00:00", str(seed), "ETH"]
                         + [f"{r.random():.9f}" for _ in rdo.BOOK_FIELDS])
                for _ in range(1500)]
        return ",".join(rdo.FIELDS) + "\n" + "\n".join(rows) + "\n"

    for seed in range(93, 93 + 50_000):      # 93: first hit with zlib 1.3
        text = book_text(seed)
        member = gzip.compress(text.encode(), mtime=0)
        i = member.find(b"\x1f\x8b\x08", 10)
        if i != -1 and i < len(member) - 8:
            break
    else:
        raise AssertionError("no member with an inner 1f 8b 08 found")
    path = tmp_path / f"book_{_today()}.csv.gz"
    path.write_bytes(member)
    rec = rdo.DeribitOiRecorder(out_dir=tmp_path,
                                session=FakeSession({"BTC": FakeResponse(book(7))}),
                                currencies=("BTC",))
    assert rec.run_once() == {"BTC": 2}
    assert not list(tmp_path.glob("*.trunc*"))
    assert path.read_bytes().startswith(member)
    rows = _rows(path)
    assert len(rows) == 1 + 1500 + 2 and rows[-1][1] == "7"


class FlakyOpen:
    def __init__(self, fails):
        self.fails = fails

    def __call__(self, file, mode="r", *a, **kw):
        if mode == "ab" and self.fails > 0:
            self.fails -= 1
            raise PermissionError(13, "in use by another process", str(file))
        return builtins.open(file, mode, *a, **kw)


def test_failed_write_is_retried_and_other_currency_is_kept(tmp_path, monkeypatch):
    """A write that fails once keeps its rows and writes them on the retry at
    the end of the run; the failure is an error row."""
    s = FakeSession({"BTC": FakeResponse(book(1)), "ETH": FakeResponse(book(2))})
    rec = rdo.DeribitOiRecorder(out_dir=tmp_path, session=s)
    monkeypatch.setattr(rdo, "open", FlakyOpen(fails=1), raising=False)
    assert rec.run_once() == {"BTC": 2, "ETH": 2}
    assert rec.unwritten == 0
    assert [r[2] for r in _rows(tmp_path / f"book_{_today()}.csv.gz")[1:]] == \
        ["BTC", "BTC", "ETH", "ETH"]
    err = _rows(tmp_path / f"errors_{_today()}.csv.gz")
    assert err[1][2] == "write" and "PermissionError" in err[1][3]


def test_write_that_never_succeeds_is_reported_by_the_exit_code(tmp_path, monkeypatch):
    """Deribit is a one-shot process: rows still unwritten at the end of the
    run are lost with it, and the exit code says so (docs/OPERATIONS.md)."""
    monkeypatch.setattr(rdo, "open", FlakyOpen(fails=10**6), raising=False)
    monkeypatch.setattr(rdo.requests, "Session",
                        lambda: FakeSession({"BTC": FakeResponse(book(1))}))
    out = tmp_path / "d"
    assert rdo.main(["--out-dir", str(out), "--currencies", "BTC"]) == 1
    assert not (tmp_path / "d.lock").exists()


def test_two_runs_never_append_at_once(tmp_path, monkeypatch):
    out = tmp_path / "d"
    other = rdo._acquire_lock(rdo.lock_path_for(out))
    assert other not in (False, None)
    monkeypatch.setattr(rdo.requests, "Session",
                        lambda: FakeSession({"BTC": FakeResponse(book(1))}))
    assert rdo.main(["--out-dir", str(out), "--currencies", "BTC"]) == 3
    assert not out.exists()
    other.release()
    assert rdo.main(["--out-dir", str(out), "--currencies", "BTC"]) == 0
    assert len(_rows(out / f"book_{_today()}.csv.gz")) == 1 + 2
