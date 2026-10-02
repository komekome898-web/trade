"""Tests for scripts/record_okx_traders.py -- forward recorder of OKX's
public lead-trader lists, their positions and the top-trader ratios. All
network is replaced by a fake session; payloads reproduce the shapes
measured on 2026-10-02."""
from __future__ import annotations

import csv
import gzip
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import record_okx_traders as rot  # noqa: E402


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.headers = {}

    def json(self):
        return self._payload


class FakeSession:
    """GET routed by a function of (path, params) -> FakeResponse/Exception."""

    def __init__(self, route):
        self.route = route
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        path = url.split("okx.com")[-1]
        self.calls.append((path, dict(params or {})))
        v = self.route(path, dict(params or {}))
        if isinstance(v, Exception):
            raise v
        return v


def ok(data):
    return FakeResponse({"code": "0", "msg": "", "data": data})


def trader(code):
    return {"uniqueCode": code, "nickName": f"n{code}", "ccy": "USDT",
            "aum": "1", "pnl": "2", "pnlRatio": "0.1", "winRatio": "0.5",
            "leadDays": "72", "copyTraderNum": "3", "maxCopyTraderNum": "300",
            "accCopyTraderNum": "9", "copyState": "0", "portLink": "",
            "traderInsts": ["BTC-USDT-SWAP"],
            "pnlRatios": [{"beginTs": "1790870400000", "pnlRatio": "0.1"}]}


def subpos(sid, inst="BTC-USDT-SWAP"):
    return {"ccy": "USDT", "instId": inst, "instType": "SWAP", "lever": "50",
            "margin": "1", "markPx": "2", "mgnMode": "cross", "openAvgPx": "3",
            "openTime": "1790877102346", "posSide": "long", "subPos": "1000",
            "subPosId": sid, "uniqueCode": "A", "upl": "4", "uplRatio": "0.1"}


def histpos(sid):
    d = subpos(sid)
    d.update({"closeAvgPx": "5", "closeTime": "1790900000000", "pnl": "6",
              "pnlRatio": "0.2"})
    return d


def make_route(lists, current=None, history=None, ratios=None, fail=None):
    current = current or {}
    history = history or {}
    fail = fail or {}

    def route(path, params):
        for needle, exc in fail.items():
            if needle in path and (params.get("uniqueCode") in (None, exc[0])):
                return exc[1]
        if path.endswith("public-lead-traders"):
            pages = lists.get(params["instType"], [])
            page = int(params.get("page", "1"))
            ranks = pages[page - 1] if page <= len(pages) else []
            return ok([{"dataVer": "20261002110001", "totalPage": str(len(pages)),
                        "ranks": ranks}])
        if path.endswith("public-current-subpositions"):
            return ok(current.get(params["uniqueCode"], []))
        if path.endswith("public-subpositions-history"):
            return ok(history.get(params["uniqueCode"], []))
        if "/rubik/" in path:
            return ok(ratios if ratios is not None
                      else [["1790914800000", "0.9"], ["1790914500000", "0.8"]])
        raise AssertionError(path)
    return route


def _rec(tmp_path, route, **kw):
    return rot.OkxTradersRecorder(out_dir=tmp_path, session=FakeSession(route),
                                  ratio_inst_ids=("BTC-USDT-SWAP",),
                                  sleep=lambda s: None, **kw)


def _rows(tmp_path, name):
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = tmp_path / f"{name}_{day}.csv.gz"
    if not path.exists():
        return []
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


def test_cycle_writes_every_file_with_its_columns(tmp_path):
    route = make_route({"SWAP": [[trader("A"), trader("B")], [trader("C")]],
                        "SPOT": [[trader("S")]]},
                       current={"A": [subpos("1"), subpos("2")]},
                       history={"B": [histpos("9")]})
    rec = _rec(tmp_path, route)
    counts = rec.run_cycle()
    assert counts["traders"] == 3                     # SWAP only: A, B, C
    lt = _rows(tmp_path, "leadtraders")
    assert lt[0] == rot.LIST_FIELDS
    got = [(r[2], r[3], r[4], r[5]) for r in lt[1:]]   # inst_type, page, rank, code
    assert got == [("SWAP", "1", "1", "A"), ("SWAP", "1", "2", "B"),
                   ("SWAP", "2", "1", "C"), ("SPOT", "1", "1", "S")]
    assert lt[1][1] == "20261002110001"                 # source's dataVer
    pos = _rows(tmp_path, "positions")
    assert pos[0] == rot.POS_FIELDS and len(pos) == 3
    hist = _rows(tmp_path, "history")
    assert hist[0] == rot.HIST_FIELDS and hist[1][3] == "9"
    rat = _rows(tmp_path, "ratios")
    assert rat[0] == rot.RATIO_FIELDS
    # oldest first, source time kept next to the receive time
    assert [r[4] for r in rat[1:4]] == ["1790914500000", "1790914800000",
                                        "1790914500000"]
    assert rat[1][5] == "2026-10-02T04:15:00.000+00:00"
    # SPOT positions are never requested (OKX answers code 51000 for them)
    spot_calls = [c for c in rec.session.calls
                  if "subpositions" in c[0] and c[1].get("instType") == "SPOT"]
    assert spot_calls == []


def test_second_cycle_writes_no_duplicate_list_history_or_ratio_rows(tmp_path):
    route = make_route({"SWAP": [[trader("A")]]},
                       current={"A": [subpos("1")]},
                       history={"A": [histpos("9"), histpos("8")]})
    rec = _rec(tmp_path, route)
    rec.run_cycle()
    rec.run_cycle()
    assert len(_rows(tmp_path, "leadtraders")) == 1 + 1
    assert len(_rows(tmp_path, "history")) == 1 + 2
    assert len(_rows(tmp_path, "ratios")) == 1 + 2 * len(rot.RATIO_KINDS)
    # open positions are a snapshot per sweep: one row per sweep
    pos = _rows(tmp_path, "positions")
    assert len(pos) == 1 + 2 and pos[1][1] != pos[2][1]


def _write_history_file(path, sub_pos_ids, day_iso):
    with gzip.open(path, "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(rot.HIST_FIELDS)
        for sid in sub_pos_ids:
            w.writerow([f"{day_iso}T00:00:00+00:00", "SWAP", "A", sid] + [""] * 13)


def test_restart_restores_closed_position_keys_from_every_history_file(tmp_path):
    """Before: the test had two files, and a copy that read only the newest
    two (sorted(...)[-2:]) passed. Here the OLDEST of four day files and a
    renamed (truncN) file hold keys that OKX returns again; none of them may
    be written twice."""
    _write_history_file(tmp_path / "history_20250101.csv.gz", ["1"], "2025-01-01")
    _write_history_file(tmp_path / "history_20250301.csv.gz", ["2"], "2025-03-01")
    _write_history_file(tmp_path / "history_20250601.csv.gz", ["3"], "2025-06-01")
    _write_history_file(tmp_path / "history_20250901.csv.gz", ["4"], "2025-09-01")
    _write_history_file(tmp_path / "history_20250602.trunc1.csv.gz", ["5"], "2025-06-02")
    route = make_route({"SWAP": [[trader("A")]]},
                       history={"A": [histpos(s) for s in ("6", "5", "4", "3", "2", "1")]})
    rec = _rec(tmp_path, route)
    assert rec.seen_hist == {"1", "2", "3", "4", "5"}
    rec.run_cycle()
    assert [r[3] for r in _rows(tmp_path, "history")[1:]] == ["6"]


def test_restart_restores_list_and_ratio_keys_from_today_and_yesterday(tmp_path):
    route = make_route({"SWAP": [[trader("A")]]}, history={"A": [histpos("9")]})
    _rec(tmp_path, route).run_cycle()
    rec2 = _rec(tmp_path, route)
    rec2.run_cycle()
    assert len(_rows(tmp_path, "history")) == 1 + 1
    assert len(_rows(tmp_path, "leadtraders")) == 1 + 1
    assert len(_rows(tmp_path, "ratios")) == 1 + 2 * len(rot.RATIO_KINDS)


def test_history_page_cap_is_recorded_as_an_error(tmp_path):
    """Before: turning the cap's raise into a silent return passed every test.
    A trader whose closed positions fill every page up to --max-pages writes
    what it got and one error row naming the cap."""
    def route(path, params):
        if path.endswith("public-subpositions-history"):
            after = int(params.get("after") or 10_000)
            return ok([histpos(str(after - 1 - i)) for i in range(rot.PAGE_LIMIT)])
        return make_route({"SWAP": [[trader("A")]]})(path, params)
    rec = _rec(tmp_path, route, max_pages=3)
    counts = rec.run_cycle()
    assert counts["history"] == 3 * rot.PAGE_LIMIT
    err = [r for r in _rows(tmp_path, "errors")[1:]
           if r[2] == "subpositions-history SWAP A"]
    assert len(err) == 1 and "page cap 3 reached" in err[0][3]


def test_failed_trader_is_recorded_and_sweep_continues(tmp_path):
    route = make_route(
        {"SWAP": [[trader("A"), trader("B")]]},
        current={"B": [subpos("5")]},
        fail={"public-current-subpositions": ("A", FakeResponse(
            {"code": "60004", "msg": "Trader doesn't exist", "data": []}))})
    rec = _rec(tmp_path, route)
    counts = rec.run_cycle()
    assert counts["errors"] == 1
    err = _rows(tmp_path, "errors")
    assert err[0] == rot.ERROR_FIELDS
    assert err[1][1:3] == ["okx", "current-subpositions SWAP A"]
    assert "60004" in err[1][3]
    assert [r[4] for r in _rows(tmp_path, "positions")[1:]] == ["5"]


def test_network_exception_on_ratio_and_list_page_is_recorded(tmp_path):
    base = make_route({"SWAP": [[trader("A")], [trader("B")]]})
    failing = {"page": None}

    def route(path, params):
        if "/rubik/" in path:
            return requests.exceptions.ConnectTimeout("boom")
        if path.endswith("public-lead-traders") and params["instType"] == "SWAP" \
                and params.get("page") == failing["page"]:
            return FakeResponse({}, status_code=503)
        return base(path, params)
    rec = _rec(tmp_path, route)
    failing["page"] = "2"              # a later page fails: the rest goes on
    counts = rec.run_cycle()
    err = _rows(tmp_path, "errors")
    assert sum("ConnectTimeout" in r[3] for r in err[1:]) == len(rot.RATIO_KINDS)
    assert any("lead-traders SWAP page 2" == r[2] and "HTTP 503" in r[3]
               for r in err[1:])
    assert counts["traders"] == 1      # A from page 1
    failing["page"] = "1"              # page 1 fails: totalPage unknown, list
    counts = rec.run_cycle()           # skipped this cycle, recorded
    assert counts["traders"] == 0
    assert any("lead-traders SWAP page 1" == r[2] for r in _rows(tmp_path, "errors")[1:])
    failing["page"] = None             # next cycle reads both pages
    assert rec.run_cycle()["traders"] == 2


def test_current_positions_follow_pagination(tmp_path):
    full = [subpos(str(1000 + i)) for i in range(rot.PAGE_LIMIT)]
    rest = [subpos("1"), subpos("2")]

    def route(path, params):
        if path.endswith("public-current-subpositions"):
            return ok(rest if params.get("after") else full)
        return make_route({"SWAP": [[trader("A")]]})(path, params)
    rec = _rec(tmp_path, route)
    rec.run_cycle()
    assert len(_rows(tmp_path, "positions")) == 1 + rot.PAGE_LIMIT + 2
    afters = [c[1].get("after") for c in rec.session.calls
              if c[0].endswith("public-current-subpositions")]
    assert afters == [None, str(1000 + rot.PAGE_LIMIT - 1)]


def test_history_pagination_stops_at_a_known_position(tmp_path):
    page1 = [histpos(str(5000 - i)) for i in range(rot.PAGE_LIMIT)]

    def route(path, params):
        if path.endswith("public-subpositions-history"):
            return ok(page1 if not params.get("after") else [histpos("1")])
        return make_route({"SWAP": [[trader("A")]]})(path, params)
    rec = _rec(tmp_path, route)
    rec.run_cycle()                                  # page 1 all new -> page 2
    n_hist_calls = sum(c[0].endswith("history") for c in rec.session.calls)
    assert n_hist_calls == 2
    rec.session.calls.clear()
    rec.run_cycle()                                  # page 1 known -> stop
    assert sum(c[0].endswith("history") for c in rec.session.calls) == 1
    assert len(_rows(tmp_path, "history")) == 1 + rot.PAGE_LIMIT + 1


# ---- writing that survives a kill (L-121; spec r2 sec 2) --------------------
import builtins  # noqa: E402
import random  # noqa: E402

from bot.research.gz_members import iter_members_in_order  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
ISIZE_MAGIC_LEN = 0x088B1F     # a member this long ends with ISIZE = 1f 8b 08 00


class FlakyOpen:
    """The module's open(): the first `fails` appends ("ab") raise, as when
    another program holds the file open on Windows."""

    def __init__(self, fails):
        self.fails = fails

    def __call__(self, file, mode="r", *a, **kw):
        if mode == "ab" and self.fails > 0:
            self.fails -= 1
            raise PermissionError(13, "in use by another process", str(file))
        return builtins.open(file, mode, *a, **kw)


def _day():
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _plain(path):
    return list(csv.reader(gzip.decompress(path.read_bytes())
                           .decode("utf-8").splitlines()))


def _before_cut(path):
    out = []
    for m in iter_members_in_order(path.read_bytes()):
        if not m.complete:
            break
        out += list(csv.reader(m.payload.decode("utf-8").splitlines()))
    return out


def test_kill_mid_write_then_restart_renames_the_file_and_keeps_both_parts(tmp_path):
    """spec r2 sec 3-2 on the history file, whose rows also feed the
    write-once key: (a) the renamed file still gives the row written before
    the kill, and it counts for the key; (b) the new file reads with plain
    gzip; the closed position whose write was cut is written again, once."""
    route = make_route({"SWAP": [[trader("A")]]}, history={"A": [histpos("9")]})
    _rec(tmp_path, route).run_cycle()
    path = tmp_path / f"history_{_day()}.csv.gz"
    junk = random.Random(2).randbytes(400).hex()
    member = gzip.compress(f"2026-10-02T00:00:00+00:00,SWAP,A,7,{junk}\n".encode())
    with open(path, "ab") as f:
        f.write(member[: len(member) // 2])              # killed mid-write
    before = path.read_bytes()
    route2 = make_route({"SWAP": [[trader("A")]]},
                        history={"A": [histpos("9"), histpos("7")]})
    rec2 = _rec(tmp_path, route2)
    assert rec2.seen_hist == {"9"}
    rec2.run_cycle()
    moved = tmp_path / f"history_{_day()}.trunc1.csv.gz"
    assert moved.read_bytes() == before                     # renamed whole
    assert [r[3] for r in _before_cut(moved)[1:]] == ["9"]   # (a)
    rows = _plain(path)                                      # (b)
    assert rows[0] == rot.HIST_FIELDS and [r[3] for r in rows[1:]] == ["7"]
    _rec(tmp_path, route2).run_cycle()        # a third start writes nothing new
    assert [r[3] for r in _plain(path)[1:]] == ["7"]


def test_healthy_history_file_with_the_magic_inside_is_neither_renamed_nor_forgotten(tmp_path):
    """1f 8b 08 inside a healthy history member (here in its ISIZE trailer
    field). The first version split the member there: the restore dropped
    its keys (so the positions would be written again) and the append cut
    the file in place."""
    head = ",".join(rot.HIST_FIELDS) + "\n"
    rows = "".join(f"2026-10-01T00:00:00+00:00,SWAP,A,{sid}" + "," * 13 + "\n"
                   for sid in ("1", "2"))
    rows += "2026-10-01T00:00:00+00:00,SWAP,A,3" + "," * 13 + "\n"
    # filler rows without a sub_pos_id (skipped by the key) up to the length
    filler = "2026-10-01T00:00:00+00:00,SWAP,A," + "," * 13
    need = ISIZE_MAGIC_LEN - len(head + rows)
    sizes = [1000] * (need // 1000 - 1) + [1000 + need % 1000]
    text = head + rows + "".join(filler + "x" * (n - len(filler) - 1) + "\n"
                                 for n in sizes)
    assert len(text.encode()) == ISIZE_MAGIC_LEN
    member = gzip.compress(text.encode())
    assert member[-4:] == b"\x1f\x8b\x08\x00"
    path = tmp_path / f"history_{_day()}.csv.gz"
    path.write_bytes(member)
    route = make_route({"SWAP": [[trader("A")]]},
                       history={"A": [histpos(s) for s in ("4", "3", "2", "1")]})
    rec = _rec(tmp_path, route)
    assert rec.seen_hist == {"1", "2", "3"}
    rec.run_cycle()
    assert not list(tmp_path.glob("*.trunc*"))
    assert [r[3] for r in _plain(path)[1:] if r[3]] == ["1", "2", "3", "4"]


def test_failed_write_keeps_rows_and_the_cycle_goes_on(tmp_path, monkeypatch):
    route = make_route({"SWAP": [[trader("A"), trader("B")]]},
                       current={"A": [subpos("1")], "B": [subpos("2")]},
                       history={"A": [histpos("8")], "B": [histpos("9")]})
    rec = _rec(tmp_path, route)
    monkeypatch.setattr(rot, "open", FlakyOpen(fails=3), raising=False)
    counts = rec.run_cycle()
    assert counts["traders"] == 2 and counts["positions"] == 2
    assert rec.out.pending() == 0
    assert [r[4] for r in _plain(tmp_path / f"positions_{_day()}.csv.gz")[1:]] \
        == ["1", "2"]
    assert [r[3] for r in _plain(tmp_path / f"history_{_day()}.csv.gz")[1:]] \
        == ["8", "9"]
    err = _plain(tmp_path / f"errors_{_day()}.csv.gz")
    assert err[1][2] == "write" and "PermissionError" in err[1][3]


def test_ctrl_c_writes_what_is_buffered(tmp_path, monkeypatch):
    def run(rec, args):
        rec.out.add("errors", rot.ERROR_FIELDS, [rot._now_iso(), "t", "x", "y"])
        raise KeyboardInterrupt
    monkeypatch.setattr(rot, "_run", run)
    assert rot.main(["--out-dir", str(tmp_path / "okx")]) == 0
    assert _plain(tmp_path / "okx" / f"errors_{_day()}.csv.gz")[1][1:] == ["t", "x", "y"]
    assert not (tmp_path / "okx.lock").exists()          # released


def test_a_backfill_while_the_resident_runs_exits_without_writing(tmp_path, monkeypatch):
    """The first critic's case: --max-pages 500 typed while the resident runs
    used to append to the same files at the same time."""
    out = tmp_path / "okx"
    resident = rot._acquire_lock(rot.lock_path_for(out))
    assert resident not in (False, None)
    called = []
    monkeypatch.setattr(rot, "_run", lambda rec, args: called.append(1) or 0)
    assert rot.main(["--out-dir", str(out), "--max-pages", "500"]) == 3
    assert called == [] and not out.exists()
    resident.release()
    assert rot.main(["--out-dir", str(out), "--max-pages", "500"]) == 0
    assert called == [1]


def test_bytes_added_by_someone_else_between_two_appends_are_noticed(tmp_path):
    """The first critic's trunc_demo.py: a cut member lands in the file while
    the same writer is still running (another writer without the lock, a
    copy tool). The writer sees the size is not what it left, checks the end
    again, renames the file, and every key comes back on the next start."""
    out = rot.BufferedDailyGz(tmp_path)
    now = rot._now_iso()
    out.add("history", rot.HIST_FIELDS, [now, "SWAP", "A", "1"] + [""] * 13)
    out.flush()
    path = tmp_path / f"history_{_day()}.csv.gz"
    with open(path, "ab") as f:
        f.write(gzip.compress(("x," * 2000 + "\n").encode())[:40])
    out.add("history", rot.HIST_FIELDS, [now, "SWAP", "A", "2"] + [""] * 13)
    out.flush()
    assert [r[3] for r in _plain(path)[1:]] == ["2"]
    assert [r[3] for r in _before_cut(tmp_path / f"history_{_day()}.trunc1.csv.gz")[1:]] == ["1"]
    assert _rec(tmp_path, make_route({})).seen_hist == {"1", "2"}
