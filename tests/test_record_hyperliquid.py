"""Tests for scripts/record_hyperliquid.py -- forward recorder of
Hyperliquid's published leaderboard and the open positions of every account
on it. All network is replaced by a fake session; payloads reproduce the
shapes measured on 2026-10-02."""
from __future__ import annotations

import csv
import gzip
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import record_hyperliquid as rh  # noqa: E402


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, leaderboard, states):
        self.leaderboard = leaderboard        # FakeResponse / Exception
        self.states = states                  # address -> FakeResponse / Exception
        self.gets = 0
        self.posts = []

    def get(self, url, headers=None, timeout=None):
        self.gets += 1
        v = self.leaderboard
        if isinstance(v, Exception):
            raise v
        return v

    def post(self, url, json=None, headers=None, timeout=None):
        assert json["type"] == "clearinghouseState"
        self.posts.append(json["user"])
        v = self.states[json["user"]]
        if isinstance(v, Exception):
            raise v
        return v


def lb_row(addr, value="100.0"):
    return {"ethAddress": addr, "accountValue": value, "displayName": None,
            "prize": 0,
            "windowPerformances": [[w, {"pnl": "1", "roi": "0.1", "vlm": "9"}]
                                   for w in ("day", "week", "month", "allTime")]}


def lb_response(addrs, etag='"e1"'):
    return FakeResponse({"leaderboardRows": [lb_row(a) for a in addrs]},
                        headers={"ETag": etag,
                                 "Last-Modified": "Fri, 02 Oct 2026 03:48:33 GMT"})


def state(positions):
    return FakeResponse({
        "marginSummary": {"accountValue": "2311.9", "totalNtlPos": "5",
                          "totalRawUsd": "6", "totalMarginUsed": "7"},
        "crossMarginSummary": {"accountValue": "2311.9", "totalNtlPos": "5",
                               "totalRawUsd": "6", "totalMarginUsed": "7"},
        "crossMaintenanceMarginUsed": "0.5", "withdrawable": "8",
        "assetPositions": [
            {"type": "oneWay", "position": {
                "coin": c, "szi": "-15.7", "entryPx": "86477.0",
                "leverage": {"type": "cross", "value": 3},
                "positionValue": "1", "unrealizedPnl": "-2",
                "returnOnEquity": "-0.1", "liquidationPx": "182219.8",
                "marginUsed": "3", "maxLeverage": 40,
                "cumFunding": {"allTime": "-1", "sinceOpen": "-2",
                               "sinceChange": "0"}}}
            for c in positions],
        "time": 1790914622131})


def _rec(tmp_path, session, **kw):
    return rh.HyperliquidRecorder(out_dir=tmp_path, session=session,
                                  sleep=lambda s: None, **kw)


def _rows(tmp_path, name):
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = tmp_path / f"{name}_{day}.csv.gz"
    if not path.exists():
        return []
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


def test_pacing_follows_documented_limit():
    rec = rh.HyperliquidRecorder(out_dir=Path("/nonexistent-never-written"),
                                 session=object(), budget_fraction=0.5)
    # 1200 weight/min * 0.5 / weight 2 = 300 requests/min -> 0.2 s apart
    assert rec.req_interval == pytest.approx(0.2)
    with pytest.raises(ValueError):
        rh.HyperliquidRecorder(out_dir=Path("/x"), session=object(),
                               budget_fraction=1.5)


def test_leaderboard_and_sweep_write_every_file_in_source_order(tmp_path):
    s = FakeSession(lb_response(["0xb", "0xa", "0xc"]),
                    {"0xb": state(["BTC", "ETH"]), "0xa": state([]),
                     "0xc": state(["BTC"])})
    rec = _rec(tmp_path, s)
    assert rec.refresh_leaderboard()
    m = rec.sweep()
    assert s.posts == ["0xb", "0xa", "0xc"]           # the file's own order
    lb = _rows(tmp_path, "leaderboard")
    assert lb[0] == rh.LB_FIELDS
    assert [r[4] for r in lb[1:]] == ["0xb", "0xa", "0xc"]
    r = dict(zip(lb[0], lb[1]))
    assert (r["etag"], r["last_modified"], r["rank_in_file"]) == \
        ("e1", "Fri, 02 Oct 2026 03:48:33 GMT", "1")
    assert r["lb_account_value"] == "100.0" and r["allTime_vlm"] == "9"
    acc = _rows(tmp_path, "accounts")
    assert acc[0] == rh.ACCOUNT_FIELDS
    assert [a[2] for a in acc[1:]] == ["0xb", "0xc"]   # only with positions
    assert acc[1][3] == "1790914622131"                # source time
    pos = _rows(tmp_path, "positions")
    assert pos[0] == rh.POSITION_FIELDS
    p = dict(zip(pos[0], pos[1]))
    assert (p["coin"], p["szi"], p["leverage_type"], p["leverage_value"],
            p["cum_funding_since_open"]) == ("BTC", "-15.7", "cross", "3", "-2")
    assert len(pos) == 1 + 3
    sw = _rows(tmp_path, "sweeps")
    assert sw[0] == rh.SWEEP_FIELDS
    assert [r[2] for r in sw[1:]] == ["start", "end"]
    assert sw[1][1] == sw[2][1] == m[1]
    assert sw[1][5:] == ["3", "", "", "", ""]
    assert sw[2][5:] == ["3", "3", "0", "2", "3"]
    assert m[5:] == [3, 3, 0, 2, 3]


def test_same_leaderboard_etag_is_not_written_twice(tmp_path):
    s = FakeSession(lb_response(["0xa"]), {"0xa": state([])})
    rec = _rec(tmp_path, s)
    rec.refresh_leaderboard()
    rec.lb_day = None                  # force a refetch (as on the next UTC day)
    rec.refresh_leaderboard()
    assert s.gets == 2
    assert len(_rows(tmp_path, "leaderboard")) == 1 + 1


def test_restart_same_day_uses_stored_leaderboard_without_download(tmp_path):
    s = FakeSession(lb_response(["0xa", "0xb"]), {})
    _rec(tmp_path, s).refresh_leaderboard()
    s2 = FakeSession(lb_response(["0xz"]), {"0xa": state([]), "0xb": state([])})
    rec2 = _rec(tmp_path, s2)
    assert rec2.addresses == ["0xa", "0xb"] and "e1" in rec2.seen_etags
    assert rec2.refresh_leaderboard()
    assert s2.gets == 0
    rec2.sweep()
    assert s2.posts == ["0xa", "0xb"]


def test_two_sweeps_get_distinct_ids_and_no_duplicate_position_rows(tmp_path):
    # a malformed response repeating a coin must still give one row per coin
    s = FakeSession(lb_response(["0xa"]), {"0xa": state(["BTC", "BTC"])})
    rec = _rec(tmp_path, s)
    rec.refresh_leaderboard()
    m1 = rec.sweep()
    m2 = rec.sweep()
    assert m1[1] != m2[1]
    pos = _rows(tmp_path, "positions")
    assert len(pos) == 1 + 2
    assert {(r[1], r[2], r[4]) for r in pos[1:]} == {(m1[1], "0xa", "BTC"),
                                                    (m2[1], "0xa", "BTC")}


def test_failed_address_is_recorded_and_sweep_continues(tmp_path):
    s = FakeSession(lb_response(["0xa", "0xb", "0xc"]),
                    {"0xa": requests.exceptions.ConnectTimeout("boom"),
                     "0xb": FakeResponse({}, status_code=429),
                     "0xc": state(["SOL"])})
    sleeps = []
    rec = rh.HyperliquidRecorder(out_dir=tmp_path, session=s,
                                 sleep=sleeps.append)
    rec.refresh_leaderboard()
    m = rec.sweep()
    assert m[5:] == [3, 1, 2, 1, 1]
    err = _rows(tmp_path, "errors")
    assert err[0] == rh.ERROR_FIELDS
    assert [r[2] for r in err[1:]] == ["clearinghouseState 0xa",
                                       "clearinghouseState 0xb"]
    assert "ConnectTimeout" in err[1][3] and "HTTP 429" in err[2][3]
    # consecutive failures back off longer
    backoffs = [x for x in sleeps if x > rec.req_interval]
    assert backoffs == sorted(backoffs) and len(backoffs) == 2
    assert [r[4] for r in _rows(tmp_path, "positions")[1:]] == ["SOL"]


def test_leaderboard_failure_is_recorded_and_keeps_previous_universe(tmp_path):
    s = FakeSession(lb_response(["0xa"]), {"0xa": state([])})
    rec = _rec(tmp_path, s)
    assert rec.refresh_leaderboard()
    s.leaderboard = FakeResponse(None, status_code=503)
    rec.lb_day = None
    assert rec.refresh_leaderboard()          # yesterday's universe kept
    assert rec.addresses == ["0xa"]
    err = _rows(tmp_path, "errors")
    assert err[1][2] == "leaderboard" and "HTTP 503" in err[1][3]
    fresh = _rec(tmp_path / "other", FakeSession(
        requests.exceptions.ConnectionError("down"), {}))
    assert not fresh.refresh_leaderboard()    # nothing to sweep -> False


# ---- pacing: the sweep really waits (2026-10-02 critic) ---------------------
class FakeClock:
    """time.monotonic + time.sleep stand-ins: only sleeping moves time."""

    def __init__(self):
        self.t = 1000.0
        self.slept = []

    def clock(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


def test_sweep_waits_between_calls_at_half_the_documented_limit(tmp_path):
    """Before: only req_interval's arithmetic was tested, and a copy that
    never slept (next_at = clock()) passed every test. Here every call is
    stamped with the fake clock: consecutive calls must start at least
    req_interval = 0.2 s apart (300 requests/min = half of 1200 weight/min at
    weight 2), so N calls take at least (N-1) x 0.2 s."""
    addrs = [f"0x{i:02x}" for i in range(12)]
    clk = FakeClock()

    class Stamped(FakeSession):
        def __init__(self, *a):
            super().__init__(*a)
            self.at = []

        def post(self, url, json=None, headers=None, timeout=None):
            self.at.append(clk.t)
            return super().post(url, json=json, headers=headers, timeout=timeout)

    s = Stamped(lb_response(addrs), {a: state([]) for a in addrs})
    rec = rh.HyperliquidRecorder(out_dir=tmp_path, session=s,
                                 sleep=clk.sleep, clock=clk.clock)
    rec.refresh_leaderboard()
    rec.sweep()
    assert len(s.at) == 12
    gaps = [b - a for a, b in zip(s.at, s.at[1:])]
    assert min(gaps) >= 0.2 - 1e-9
    assert s.at[-1] - s.at[0] >= 11 * 0.2 - 1e-9


def test_an_address_listed_twice_is_polled_once_per_sweep(tmp_path):
    """accounts has the unique key (sweep_id, address): a leaderboard that
    lists an address twice must not produce two account rows."""
    s = FakeSession(lb_response(["0xa", "0xb", "0xa"]),
                    {"0xa": state(["BTC"]), "0xb": state(["ETH"])})
    rec = _rec(tmp_path, s)
    rec.refresh_leaderboard()
    rec.sweep()
    assert s.posts == ["0xa", "0xb"]
    assert [a[2] for a in _rows(tmp_path, "accounts")[1:]] == ["0xa", "0xb"]
    assert len(_rows(tmp_path, "leaderboard")) == 1 + 3      # recorded as published


# ---- writing that survives a kill (L-121; spec r2 sec 2) --------------------
import builtins  # noqa: E402
import random  # noqa: E402

from bot.research.gz_members import iter_members_in_order  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


class FlakyOpen:
    """Stands in for the module's open(): the first `fails` appends ("ab")
    raise. partial=True writes half of the bytes first, as a full disk in the
    middle of the write would."""

    def __init__(self, fails, partial=False):
        self.fails, self.partial = fails, partial

    def __call__(self, file, mode="r", *a, **kw):
        if mode == "ab" and self.fails > 0:
            self.fails -= 1
            if not self.partial:
                raise PermissionError(13, "in use by another process", str(file))
            real = builtins.open(file, mode, *a, **kw)

            class Half:
                def __enter__(self):
                    return self

                def __exit__(self, *exc):
                    real.close()
                    return False

                def write(self, data):
                    real.write(data[: len(data) // 2])
                    real.flush()
                    raise OSError(28, "No space left on device")
            return Half()
        return builtins.open(file, mode, *a, **kw)


def _day():
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _plain(path):
    """What any plain gzip reader sees (raises if a member is broken)."""
    return list(csv.reader(gzip.decompress(path.read_bytes())
                           .decode("utf-8").splitlines()))


def _before_cut(path):
    """Rows of the members up to the cut, read in order (header included)."""
    out = []
    for m in iter_members_in_order(path.read_bytes()):
        if not m.complete:
            break
        out += list(csv.reader(m.payload.decode("utf-8").splitlines()))
    return out


def _cut_member(fields_rows):
    """The first half of a member: what a kill in the middle of its write
    leaves on disk."""
    text = "\n".join(",".join(map(str, r)) for r in fields_rows) + "\n"
    member = gzip.compress(text.encode())
    return member[: len(member) // 2]


def test_kill_mid_write_then_restart_renames_the_file_and_keeps_both_parts(tmp_path):
    """spec r2 sec 3-2: (a) the renamed file still gives every row written
    before the kill, (b) the new file reads with a plain gzip reader. Nothing
    is cut in place."""
    s = FakeSession(lb_response(["0xa"]), {"0xa": state(["BTC"])})
    rec = _rec(tmp_path, s)
    rec.refresh_leaderboard()
    m1 = rec.sweep()
    path = tmp_path / f"positions_{_day()}.csv.gz"
    junk = random.Random(1).randbytes(500).hex()      # does not compress
    with open(path, "ab") as f:
        f.write(_cut_member([[rh._now_iso(), "s", "0xjunk", "", "XRP", junk]]))
    before = path.read_bytes()
    assert [r["sweep_id"] for r in rh.read_gz_rows(path)] == [m1[1]], \
        "the cut member must not count as rows"
    s2 = FakeSession(lb_response(["0xa"]), {"0xa": state(["BTC", "ETH"])})
    rec2 = _rec(tmp_path, s2)
    m2 = rec2.sweep()
    moved = tmp_path / f"positions_{_day()}.trunc1.csv.gz"
    assert moved.read_bytes() == before                         # renamed whole
    old = _before_cut(moved)
    assert old[0] == rh.POSITION_FIELDS
    assert [(r[1], r[4]) for r in old[1:]] == [(m1[1], "BTC")]  # (a)
    rows = _plain(path)                                          # (b)
    assert rows[0] == rh.POSITION_FIELDS
    assert [(r[1], r[4]) for r in rows[1:]] == [(m2[1], "BTC"), (m2[1], "ETH")]
    assert not list(tmp_path.glob("*.bin"))


def test_stray_bytes_after_a_whole_member_rename_the_file(tmp_path):
    """A kill after the first byte of a new member: gzip readers reject the
    file although every member before it is whole."""
    s = FakeSession(lb_response(["0xa"]), {"0xa": state(["BTC"])})
    rec = _rec(tmp_path, s)
    rec.refresh_leaderboard()
    rec.sweep()
    path = tmp_path / f"positions_{_day()}.csv.gz"
    with open(path, "ab") as f:
        f.write(b"\x1f")
    _rec(tmp_path, s).sweep()
    moved = tmp_path / f"positions_{_day()}.trunc1.csv.gz"
    assert moved.read_bytes()[-1:] == b"\x1f"
    assert len(_before_cut(moved)) == 1 + 1
    assert len(_plain(path)) == 1 + 1


def test_second_rename_on_the_same_day_does_not_overwrite_the_first(tmp_path):
    s = FakeSession(lb_response(["0xa"]), {"0xa": state(["BTC"])})
    rec = _rec(tmp_path, s)
    rec.refresh_leaderboard()
    path = tmp_path / f"positions_{_day()}.csv.gz"
    for _ in range(2):
        _rec(tmp_path, s).sweep()
        with open(path, "ab") as f:
            f.write(b"\x1f\x8b")
    _rec(tmp_path, s).sweep()
    t1 = tmp_path / f"positions_{_day()}.trunc1.csv.gz"
    t2 = tmp_path / f"positions_{_day()}.trunc2.csv.gz"
    assert len(_before_cut(t1)) == len(_before_cut(t2)) == len(_plain(path)) == 1 + 1


def test_leaderboard_with_the_magic_inside_survives_a_same_day_restart(tmp_path):
    """The second critic's reproduction (lb_magic2.py): today's leaderboard
    file is one healthy member whose compressed bytes contain 1f 8b 08. The
    first version restored 0 addresses (downloaded again) and then cut the
    file in place so no gzip reader could read it. Now the restart finds the
    addresses without a download, and the file is neither renamed nor cut."""
    def lb_text(seed):
        r = random.Random(seed)
        lines = [",".join(rh.LB_FIELDS)]
        for i in range(1, 1501):
            addr = "0x%040x" % r.getrandbits(160)
            lines.append(",".join(["2026-10-02T03:50:00.000+00:00", "e1",
                                   "Fri 02 Oct 2026 03:48:33 GMT", str(i), addr,
                                   f"{r.random() * 1e6:.2f}", "", "0"]
                                  + ["1", "0.1", "9"] * 4))
        return "\n".join(lines) + "\n"

    for seed in range(661, 661 + 50_000):    # 661: first hit with zlib 1.3
        text = lb_text(seed)
        member = gzip.compress(text.encode(), mtime=0)
        i = member.find(b"\x1f\x8b\x08", 10)
        if i != -1 and i < len(member) - 8:
            break
    else:
        raise AssertionError("no member with an inner 1f 8b 08 found")
    path = tmp_path / f"leaderboard_{_day()}.csv.gz"
    path.write_bytes(member)
    addrs = [line.split(",")[4] for line in text.splitlines()[1:]]
    s2 = FakeSession(lb_response(["0xz"], etag='"e2"'),
                     {a: state([]) for a in addrs[:3]})
    rec2 = _rec(tmp_path, s2)
    assert rec2.addresses == addrs and rec2.seen_etags == {"e1"}
    assert rec2.refresh_leaderboard() and s2.gets == 0
    rec2.sweep(max_addresses=3)
    assert s2.posts == addrs[:3]
    assert path.read_bytes() == member                 # untouched
    assert not list(tmp_path.glob("leaderboard_*.trunc*"))
    assert len(_plain(path)) == 1 + 1500


def test_restart_reads_the_universe_from_a_renamed_leaderboard_file(tmp_path):
    """If today's leaderboard file was renamed (cut by a kill), its rows still
    give today's universe: no second download of the 38.8 MB file."""
    s = FakeSession(lb_response(["0xa", "0xb"]), {})
    _rec(tmp_path, s).refresh_leaderboard()
    path = tmp_path / f"leaderboard_{_day()}.csv.gz"
    with open(path, "ab") as f:
        f.write(b"\x1f\x8b\x08\x00")
    path.rename(tmp_path / f"leaderboard_{_day()}.trunc1.csv.gz")
    s2 = FakeSession(lb_response(["0xz"]), {})
    rec2 = _rec(tmp_path, s2)
    assert rec2.addresses == ["0xa", "0xb"] and rec2.refresh_leaderboard()
    assert s2.gets == 0


def test_failed_write_keeps_its_rows_and_the_sweep_goes_on(tmp_path, monkeypatch):
    """flush empties nothing before the write succeeded, and a failed write
    does not end the sweep (a Windows program holding the file open is the
    case)."""
    s = FakeSession(lb_response(["0xa", "0xb", "0xc"]),
                    {"0xa": state(["BTC"]), "0xb": state(["ETH"]),
                     "0xc": state(["SOL"])})
    ticks = iter(range(0, 10**6, 100))      # every check is past FLUSH_INTERVAL
    rec = _rec(tmp_path, s, clock=lambda: next(ticks))
    rec.refresh_leaderboard()
    monkeypatch.setattr(rh, "open", FlakyOpen(fails=4), raising=False)
    m = rec.sweep()
    assert s.posts == ["0xa", "0xb", "0xc"]
    assert m[5:] == [3, 3, 0, 3, 3]
    assert rec.out.pending() == 0
    assert [r[4] for r in _plain(tmp_path / f"positions_{_day()}.csv.gz")[1:]] \
        == ["BTC", "ETH", "SOL"]
    err = _plain(tmp_path / f"errors_{_day()}.csv.gz")
    assert err[1][2] == "write" and "PermissionError" in err[1][3]


def test_half_written_member_is_not_cut_back_but_the_file_is_renamed(tmp_path, monkeypatch):
    """A write that fails half way leaves part of a member. Nothing is cut in
    place: the next write checks the end again, renames the file and writes
    the kept rows (with a header) to a new file."""
    s = FakeSession(lb_response(["0xa"]), {"0xa": state(["BTC"])})
    rec = _rec(tmp_path, s)
    rec.refresh_leaderboard()
    rec.sweep()
    path = tmp_path / f"positions_{_day()}.csv.gz"
    rec.out.add("positions", rh.POSITION_FIELDS,
                [rh._now_iso(), "s", "0xz"] + [""] * 17)
    monkeypatch.setattr(rh, "open", FlakyOpen(fails=1, partial=True),
                        raising=False)
    with pytest.raises(OSError):
        rec.out.flush()
    half = path.read_bytes()
    assert rec.out.pending() == 1                # the rows were kept
    assert rec.out.flush() == 1
    moved = tmp_path / f"positions_{_day()}.trunc1.csv.gz"
    assert moved.read_bytes() == half
    assert [r[2] for r in _before_cut(moved)[1:]] == ["0xa"]
    rows = _plain(path)
    assert rows[0] == rh.POSITION_FIELDS and [r[2] for r in rows[1:]] == ["0xz"]


def test_restart_after_a_kill_mid_sweep(tmp_path):
    """The nightly restart can land in the middle of a 157-minute sweep. The
    cut sweep keeps a start row and no end row (so a reader knows its
    'no row = no position' does not hold), the restarted process does not
    download the leaderboard again and starts a new sweep with a new id."""
    class Killed(FakeSession):
        def post(self, url, json=None, headers=None, timeout=None):
            if json["user"] == "0xc":
                raise KeyboardInterrupt
            return super().post(url, json=json, headers=headers, timeout=timeout)

    states = {a: state(["BTC"]) for a in ("0xa", "0xb", "0xc")}
    s = Killed(lb_response(["0xa", "0xb", "0xc"]), states)
    ticks = iter(range(0, 10**6, 100))
    rec = _rec(tmp_path, s, clock=lambda: next(ticks))
    rec.refresh_leaderboard()
    with pytest.raises(KeyboardInterrupt):
        rec.sweep()
    s2 = FakeSession(lb_response(["0xz"]), states)
    rec2 = _rec(tmp_path, s2)
    assert rec2.refresh_leaderboard() and s2.gets == 0
    m2 = rec2.sweep()
    sw = _plain(tmp_path / f"sweeps_{_day()}.csv.gz")
    first = sw[1][1]
    assert [(r[1], r[2]) for r in sw[1:]] == [(first, "start"), (m2[1], "start"),
                                              (m2[1], "end")]
    assert first != m2[1]
    # the end row is stamped when it is written (not with the sweep start)
    assert sw[3][0] == sw[3][3]
    assert datetime.fromisoformat(sw[3][0]) >= \
        datetime.fromisoformat(m2[1]).replace(microsecond=0)   # ms vs us stamps
    pos = _plain(tmp_path / f"positions_{_day()}.csv.gz")
    assert [(r[1], r[2]) for r in pos[1:]] == [
        (first, "0xa"), (first, "0xb"),
        (m2[1], "0xa"), (m2[1], "0xb"), (m2[1], "0xc")]
    assert len(_plain(tmp_path / f"leaderboard_{_day()}.csv.gz")) == 1 + 3


def test_ctrl_c_writes_what_is_buffered(tmp_path, monkeypatch):
    def run(rec, args):
        rec.out.add("errors", rh.ERROR_FIELDS, [rh._now_iso(), "t", "x", "y"])
        raise KeyboardInterrupt
    monkeypatch.setattr(rh, "_run", run)
    assert rh.main(["--out-dir", str(tmp_path / "hl")]) == 0
    assert _plain(tmp_path / "hl" / f"errors_{_day()}.csv.gz")[1][1:] == ["t", "x", "y"]
    assert not (tmp_path / "hl.lock").exists()          # released


# ---- one writer per directory (record_liquidations._acquire_lock) ----------
def test_a_second_process_on_the_same_directory_exits_without_writing(tmp_path, monkeypatch):
    out = tmp_path / "hl"
    first = rh._acquire_lock(rh.lock_path_for(out))
    assert first not in (False, None)
    assert rh.lock_path_for(out) == tmp_path / "hl.lock"
    called = []
    monkeypatch.setattr(rh, "_run", lambda rec, args: called.append(1) or 0)
    assert rh.main(["--out-dir", str(out), "--max-addresses", "1"]) == 3
    assert called == [] and not out.exists()
    first.release()
    assert rh.main(["--out-dir", str(out), "--max-addresses", "1"]) == 0
    assert called == [1]


def test_the_lock_is_refreshed_while_the_process_lives(tmp_path, monkeypatch):
    """RunLock counts age from the last write of the lock file, so a resident
    must keep writing it or a second copy could take the lock over."""
    import json
    import time as _time
    monkeypatch.setattr(rh, "LOCK_BEAT_SEC", 0.05)
    lock_path = tmp_path / "x.lock"
    lock = rh._acquire_lock(lock_path)
    t0 = json.loads(lock_path.read_text())["ts"]
    beat = rh._Heartbeat(lock_path).start()
    _time.sleep(0.3)
    beat.stop()
    assert json.loads(lock_path.read_text())["ts"] > t0
    lock.release()
    assert not lock_path.exists()
