"""scripts/share_backtest_runs.py: only the files the バックテスト tab reads are copied, a run whose period
reaches past the seal boundary is never copied, and the dashboard shows what was copied."""
from __future__ import annotations

import builtins
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

# 2023-12-18T00:00:00Z / 2026-08-23T00:00:00Z / 2026-09-06T00:00:00Z in ns
P208 = 1_702_857_600_000_000_000
P208B = 1_787_443_200_000_000_000
H = 3_600_000_000_000


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def share():
    return _load("share_backtest_runs")


def _seal(root: Path, p208_from="2023-12-18T00:00:00+00:00", sealed_file="backtest_data/bf/candles_1m_2018.csv.gz",
          sealed_file_from="2023-12-18T00:00:00+00:00", other_unit=None):
    """P2-08 and P2-08b as the data layer reads them; `other_unit` = (unit, path, seal_from_ts[, bytes]) adds a
    record of another unit, whose file cutoff is not part of the P2-08 / P2-08b boundary. With bytes, the sealed
    file is written under the root and its md5 goes into the record (as every real record has one)."""
    extra = []
    if other_unit is not None:
        u, path, frm, *raw = other_unit
        f = {"path": path, "time_column": "ts", "seal_from_ts": frm}
        if raw:
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_bytes(raw[0])
            f["md5"] = hashlib.md5(raw[0]).hexdigest()
        extra = [(u, "2026-09-06T00:00:00+00:00", [f])]
    for unit, fwd, files in extra + [
            ("P2-08", "2026-09-06T00:00:00+00:00",
             [{"path": "backtest_data/bf/candles_1m_2023.csv.gz", "time_column": "ts", "seal_from_ts": p208_from},
              {"path": sealed_file, "time_column": "ts", "seal_from_ts": sealed_file_from}]),
            ("P2-08b", "2026-09-08T00:00:00+00:00",
             [{"path": "backtest_data/exec.csv.gz", "time_column": "exec_date",
               "seal_from_ts": "2026-08-23T00:00:00+00:00"}])]:
        d = root / "backtest_data" / "phase2_sealed" / unit
        d.mkdir(parents=True, exist_ok=True)
        (d / "SEALED.json").write_text(json.dumps({"unit": unit, "forward_start": fwd, "files": files}), encoding="utf-8")


def _run(d: Path, *, last_ns=None, range_ns=None, asset="crypto", path="backtest_data/k1/bars.csv.gz",
         nested_engine=False, n=2, data_bytes=None, kind="bar", more_kinds=()):
    """A run as bot.bt.repro writes it, with its data file under the root (d's grandparent's parent) and the
    sha256 the run recorded for it. data_bytes=None leaves an existing file as it is (or writes a default one)."""
    d.mkdir(parents=True)
    f = d.parents[2] / path
    if data_bytes is not None or not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data_bytes if data_bytes is not None else b"start,o,h,l,c\n" + path.encode())
    data = [{"path": path, "spec": {"asset": asset, "kind": kind}}]
    if range_ns is not None:
        data[0]["range_ns"] = range_ns
    for i, k in enumerate(more_kinds):                  # further data entries of other kinds (same file, for the hash)
        data.append({"path": path, "spec": {"asset": asset, "kind": k}} if k is not None else {"path": path})
    eng = {}
    if last_ns is not None:
        e = {"first_time_ns": last_ns - 10 * H, "last_time_ns": last_ns}
        eng = {"optimistic": {"XBTUSD": e}, "pessimistic": {"XBTUSD": dict(e)}} if nested_engine else e
    (d / "record.json").write_text(json.dumps({"purpose": "研究", "config": {"instrument": "XBTUSD"},
                                               "setup": {"name": "s"}, "data": data, "engine": eng,
                                               "data_sha256": {path: hashlib.sha256(f.read_bytes()).hexdigest()}
                                               if f.exists() else {},
                                               "currency": "USD"}), encoding="utf-8")
    (d / "repro.json").write_text(json.dumps({"runs": 2, "identical": True, "sha256": {}}), encoding="utf-8")
    m = {"purpose": "m", "data": {"trades": {"n": n, "per_trade_bp": [1.0] * n, "neg_frac": 0.0}}}
    (d / "metrics.json.gz").write_bytes(gzip.compress(json.dumps(m).encode()))
    (d / "trades.json").write_text(json.dumps({"purpose": "t", "data": [{"id": i} for i in range(n)]}),
                                   encoding="utf-8")
    (d / "data_quality.json").write_text(json.dumps({"purpose": "q", "data": {}}), encoding="utf-8")
    (d / "fills.json.gz").write_bytes(gzip.compress(b'{"purpose":"f","data":[]}'))
    (d / "orders.json").write_text('{"purpose":"o","data":[]}', encoding="utf-8")


def _tree(tmp_path: Path) -> tuple[Path, dict]:
    runs = tmp_path / "backtest_runs"
    (runs / "g").mkdir(parents=True)
    (runs / "g" / ".gitignore").write_text("*\n", encoding="utf-8")
    ids = {k: str(i) * 64 for i, k in enumerate(("before", "edge", "after", "noperiod", "equity", "filesealed",
                                                 "declared"), start=1)}
    _run(runs / "g" / ids["before"], last_ns=P208 - 100 * H, nested_engine=True)
    _run(runs / "g" / ids["edge"], last_ns=P208)                         # ends exactly at the boundary
    _run(runs / "g" / ids["after"], last_ns=P208 + H)                    # one bar past it
    _run(runs / "g" / ids["noperiod"])                                  # no range, no engine time
    _run(runs / "g" / ids["equity"], last_ns=P208 - 100 * H, asset="equity")
    _run(runs / "g" / ids["filesealed"], last_ns=P208 - 100 * H, path="backtest_data/bf/candles_1m_2018.csv.gz")
    _run(runs / "g" / ids["declared"], last_ns=P208 - 100 * H, range_ns=[P208 - 200 * H, P208 + H])
    return runs, ids


def _main(share, tmp_path, runs, *extra):
    # --max-mb has no default (the owner decides it); the 1000 here is only "far above these few small runs"
    limit = [] if "--max-mb" in extra else ["--max-mb", "1000"]
    return share.main(["--runs-dir", str(runs), "--out", str(tmp_path / "out"), "--root", str(tmp_path),
                       *limit, *extra])


def test_only_runs_inside_the_seal_boundary_are_copied_with_only_the_view_files(tmp_path, share):
    _seal(tmp_path)
    runs, ids = _tree(tmp_path)
    assert _main(share, tmp_path, runs, "--all") == 0
    out = tmp_path / "out" / "g"
    copied = {p.name for p in out.iterdir() if p.is_dir()}
    assert copied == {ids["before"], ids["edge"], ids["filesealed"]}
    for rid in copied:
        assert sorted(os.listdir(out / rid)) == ["data_quality.json", "metrics.json.gz", "record.json",
                                                 "repro.json", "trades.json"]
    assert not (out / ".gitignore").exists()
    man = {e["run_id"]: e for e in json.loads((out / "SHARED.json").read_text(encoding="utf-8"))["runs"]}
    assert man[ids["edge"]]["shared"] and man[ids["edge"]]["at_boundary"] is True
    assert man[ids["before"]]["at_boundary"] is False
    assert "封印の境 2023-12-18T00:00:00Z" in man[ids["after"]]["reason"]
    assert "封印の境" in man[ids["declared"]]["reason"]          # the declared range reaches past it
    assert "期間が読めない" in man[ids["noperiod"]]["reason"]
    assert "資産の種類" in man[ids["equity"]]["reason"]
    assert all(not man[ids[k]]["shared"] for k in ("after", "noperiod", "equity", "declared"))
    assert man[ids["filesealed"]]["shared"]                      # its file's own cutoff is not reached


def _kind_tree(tmp_path: Path) -> tuple[Path, dict]:
    """Runs that end exactly at the boundary (and one just before it), differing only in the kind of their events."""
    runs = tmp_path / "backtest_runs"
    (runs / "k").mkdir(parents=True)
    ids = {k: str(i) * 64 for i, k in enumerate(("bar_edge", "trade_edge", "trade_before", "mixed_edge",
                                                 "nokind_edge", "bar_then_trade_edge"), start=1)}
    _run(runs / "k" / ids["bar_edge"], last_ns=P208)
    _run(runs / "k" / ids["trade_edge"], last_ns=P208, kind="trade")
    _run(runs / "k" / ids["trade_before"], last_ns=P208 - H, kind="trade")
    _run(runs / "k" / ids["mixed_edge"], last_ns=P208, kind="bar", more_kinds=("trade",))
    _run(runs / "k" / ids["nokind_edge"], last_ns=P208, kind=None, more_kinds=())
    _run(runs / "k" / ids["bar_then_trade_edge"], last_ns=P208, kind="trade", more_kinds=("bar",))
    return runs, ids


def test_a_run_ending_exactly_at_the_boundary_is_shared_only_when_its_events_are_declared_bars(tmp_path, share):
    """A bar's event time is its END, so a bar ending at the boundary is made of rows before it. A fill / book row is
    stamped with its own time, and a row AT the boundary is a sealed row: such a run is not shared, and neither is a
    run whose record does not say that its events are bars only (a mix, or no kind)."""
    _seal(tmp_path)
    runs, ids = _kind_tree(tmp_path)
    assert _main(share, tmp_path, runs, "--all") == 0
    man = {e["run_id"]: e for e in json.loads((tmp_path / "out" / "k" / "SHARED.json").read_text(
        encoding="utf-8"))["runs"]}
    assert man[ids["bar_edge"]]["shared"] and man[ids["bar_edge"]]["at_boundary"] is True
    assert man[ids["trade_before"]]["shared"] and man[ids["trade_before"]]["at_boundary"] is False
    for k in ("trade_edge", "mixed_edge", "nokind_edge", "bar_then_trade_edge"):
        assert not man[ids[k]]["shared"], k
    assert "足以外の事象" in man[ids["trade_edge"]]["reason"] and "境ちょうどの行は封印の側" in man[ids["trade_edge"]]["reason"]
    assert not (tmp_path / "out" / "k" / ids["trade_edge"]).exists()
    assert (tmp_path / "out" / "k" / ids["bar_edge"] / "record.json").is_file()


def test_bars_only_is_read_from_the_record_declaration(share):
    f = share.bars_only
    assert f({"data": [{"spec": {"kind": "bar"}}, {"spec": {"kind": "bar"}}]}) is True
    assert f({"data": [{"spec": {"kind": "bar"}}, {"spec": {"kind": "trade"}}]}) is False
    assert f({"data": [{"spec": {"kind": "book"}}]}) is False
    assert f({"data": [{"spec": {}}]}) is False and f({"data": [{}]}) is False and f({"data": []}) is False
    assert f({}) is False and f({"data": "bar"}) is False


def test_the_file_cutoff_is_read_the_same_way_bars_may_end_at_it_other_events_may_not(tmp_path, share):
    """The data file is in a seal record whose own cutoff is 2023-12-13T20:00:00Z, and the run ends exactly there."""
    cut_ns = P208 - 100 * H
    _seal(tmp_path, other_unit=("P2-04", "backtest_data/k1/bars.csv.gz", "2023-12-13T20:00:00+00:00",
                                b"start,o,h,l,c\nbacktest_data/k1/bars.csv.gz"))
    runs = tmp_path / "backtest_runs"
    (runs / "k").mkdir(parents=True)
    bar, trade = "a" * 64, "b" * 64
    _run(runs / "k" / bar, last_ns=cut_ns)
    _run(runs / "k" / trade, last_ns=cut_ns, kind="trade")
    rule = share.seal_rule(str(tmp_path))
    assert share.decide(str(runs / "k" / bar), rule)["share"] is True
    d = share.decide(str(runs / "k" / trade), rule)
    assert d["share"] is False and "封印の記録 P2-04" in d["reason"] and "足以外の事象" in d["reason"]


def test_max_mb_has_no_default_it_must_be_said(tmp_path, share, capsys):
    _seal(tmp_path)
    runs, _ = _tree(tmp_path)
    with pytest.raises(SystemExit) as e:
        share.main(["--runs-dir", str(runs), "--out", str(tmp_path / "out"), "--root", str(tmp_path), "--all"])
    assert e.value.code == 2
    assert "--max-mb" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_a_sealed_file_with_an_earlier_cutoff_of_its_own_is_not_copied(tmp_path, share):
    _seal(tmp_path, other_unit=("P2-04", "backtest_data/bf/candles_1m_2018.csv.gz", "2018-09-12T00:00:00+00:00"))
    runs, ids = _tree(tmp_path)
    assert _main(share, tmp_path, runs, "--run", ids["filesealed"]) == 0
    man = json.loads((tmp_path / "out" / "g" / "SHARED.json").read_text(encoding="utf-8"))["runs"]
    assert [e["shared"] for e in man] == [False]
    # the file is in P2-04 (2018-09-12) AND in P2-08 (2023-12-18); SealRegistry.by_path returns the last record
    # read (P2-08), so the earlier cutoff is found only by looking at every record naming the path
    assert ("データファイル backtest_data/bf/candles_1m_2018.csv.gz は封印の記録 P2-04 のファイルそのもので、"
            "その境 2018-09-12T00:00:00Z") in man[0]["reason"]
    assert not (tmp_path / "out" / "g" / ids["filesealed"]).exists()


def test_a_copy_of_a_sealed_file_under_another_name_is_not_copied(tmp_path, share):
    sealed = b"start,o,h,l,c\n2018-01-01T00:00:00Z,1,1,1,1\n"
    _seal(tmp_path, other_unit=("P2-04", "backtest_data/jp/sealed.csv.gz", "2018-09-12T00:00:00+00:00", sealed))
    runs = tmp_path / "backtest_runs"
    rid = "c" * 64
    _run(runs / "g" / rid, last_ns=P208 - 100 * H, path="backtest_data/derived/renamed.csv.gz", data_bytes=sealed)
    assert _main(share, tmp_path, runs, "--all") == 0
    man = json.loads((tmp_path / "out" / "g" / "SHARED.json").read_text(encoding="utf-8"))["runs"]
    assert [e["shared"] for e in man] == [False]
    assert "P2-04 のファイルの写し(backtest_data/jp/sealed.csv.gz と同じ中身)" in man[0]["reason"]


def test_a_data_file_missing_or_changed_since_the_run_is_not_copied(tmp_path, share):
    _seal(tmp_path)
    runs = tmp_path / "backtest_runs"
    gone, changed, kept = "d" * 64, "e" * 64, "f" * 64
    _run(runs / "g" / gone, last_ns=P208 - 100 * H, path="backtest_data/k1/gone.csv.gz")
    (tmp_path / "backtest_data" / "k1" / "gone.csv.gz").unlink()
    _run(runs / "g" / changed, last_ns=P208 - 100 * H, path="backtest_data/k1/changed.csv.gz")
    (tmp_path / "backtest_data" / "k1" / "changed.csv.gz").write_bytes(b"other bytes")
    _run(runs / "g" / kept, last_ns=P208 - 100 * H, path="backtest_data/k1/kept.csv.gz")
    assert _main(share, tmp_path, runs, "--all") == 0
    man = {e["run_id"]: e for e in json.loads((tmp_path / "out" / "g" / "SHARED.json").read_text(
        encoding="utf-8"))["runs"]}
    assert not man[gone]["shared"] and "gone.csv.gz が読めず" in man[gone]["reason"]
    assert not man[changed]["shared"] and "data_sha256" in man[changed]["reason"]
    assert man[kept]["shared"]


@pytest.mark.parametrize("frm", ["2017-01-01T00:00:00+00:00", "2026-12-01T00:00:00+00:00"])
def test_a_seal_unit_the_script_does_not_know_stops_all_sharing(tmp_path, share, frm):
    # a later crypto seal on derived data the runs do not name: its cutoff, earlier or later than 2023-12-18,
    # cannot be placed without a person saying what it seals
    _seal(tmp_path, other_unit=("P2-09", "backtest_data/new/derived_15m.csv.gz", frm))
    runs, ids = _tree(tmp_path)
    assert _main(share, tmp_path, runs, "--all") == 0
    out = tmp_path / "out" / "g"
    assert [p for p in out.iterdir() if p.is_dir()] == []
    man = json.loads((out / "SHARED.json").read_text(encoding="utf-8"))["runs"]
    assert len(man) == len(ids)
    assert all(not e["shared"] and "知らない単位 P2-09" in e["reason"] for e in man)


def test_the_units_of_the_real_seal_records_are_all_known(share):
    rule = share.seal_rule(str(REPO))
    assert "error" not in rule, rule.get("error")
    assert rule["boundary_units"] == ["P2-08", "P2-08b"] and share._iso(rule["boundary_ns"]) == "2023-12-18T00:00:00Z"


def test_without_the_seal_records_nothing_is_copied_and_the_list_says_why(tmp_path, share):
    runs, ids = _tree(tmp_path)  # no backtest_data/phase2_sealed under the root
    assert _main(share, tmp_path, runs, "--all") == 0
    out = tmp_path / "out" / "g"
    assert [p for p in out.iterdir() if p.is_dir()] == []
    man = json.loads((out / "SHARED.json").read_text(encoding="utf-8"))["runs"]
    assert len(man) == len(ids) and all(not e["shared"] and "P2-08" in e["reason"] for e in man)


def test_an_unreadable_seal_record_shares_nothing(tmp_path, share):
    _seal(tmp_path)
    (tmp_path / "backtest_data" / "phase2_sealed" / "P2-08b" / "SEALED.json").write_text("{", encoding="utf-8")
    runs, _ = _tree(tmp_path)
    assert _main(share, tmp_path, runs, "--all") == 0
    man = json.loads((tmp_path / "out" / "g" / "SHARED.json").read_text(encoding="utf-8"))["runs"]
    assert all(not e["shared"] and "封印の記録が読めない" in e["reason"] for e in man)


def test_a_run_later_found_inside_the_seal_is_removed_from_the_shared_place(tmp_path, share):
    _seal(tmp_path)
    runs, ids = _tree(tmp_path)
    assert _main(share, tmp_path, runs, "--run", ids["before"]) == 0
    assert (tmp_path / "out" / "g" / ids["before"] / "record.json").is_file()
    _seal(tmp_path, p208_from="2017-01-01T00:00:00+00:00")  # the boundary moves before the run
    assert _main(share, tmp_path, runs, "--run", ids["before"]) == 0
    assert not (tmp_path / "out" / "g" / ids["before"]).exists()
    man = json.loads((tmp_path / "out" / "g" / "SHARED.json").read_text(encoding="utf-8"))["runs"]
    assert man[0]["removed_earlier_copy"] is True and not man[0]["shared"]


def test_over_the_size_limit_nothing_is_copied(tmp_path, share, capsys):
    _seal(tmp_path)
    runs, _ = _tree(tmp_path)
    assert _main(share, tmp_path, runs, "--all", "--max-mb", "0.000001") == 2
    assert not (tmp_path / "out").exists()
    s = json.loads(capsys.readouterr().out)
    assert s["copied"] is False and "上限" in s["not_copied_because"] and s["total_shared"] == 3
    assert _main(share, tmp_path, runs, "--all", "--dry-run") == 0
    assert not (tmp_path / "out").exists()


def test_the_decision_reads_only_the_record_not_the_values(tmp_path, share, monkeypatch):
    _seal(tmp_path)
    runs, ids = _tree(tmp_path)
    rule = share.seal_rule(str(tmp_path))
    opened = []
    real_open = builtins.open

    def spy(file, *a, **k):
        opened.append(os.path.basename(str(file)))
        return real_open(file, *a, **k)

    monkeypatch.setattr(builtins, "open", spy)
    monkeypatch.setattr(gzip, "open", lambda *a, **k: pytest.fail("an export was opened to decide"))
    for rid in ids.values():
        share.decide(str(runs / "g" / rid), rule)
    # record.json, and the data files (hashed to tell a sealed copy); no export (metrics / trades / ...)
    assert "record.json" in opened
    assert set(opened) - {"record.json"} <= {"bars.csv.gz"}


def test_the_dashboard_shows_the_copied_runs_in_the_backtest_tab(tmp_path, share):
    _seal(tmp_path)
    runs, ids = _tree(tmp_path)
    assert _main(share, tmp_path, runs, "--all") == 0
    dash = _load("dashboard")
    empty = tmp_path / "pc_backtest_runs"  # the PC: no backtest_runs of its own
    status, _, body = dash._backtest("/api/backtest/runs", (str(empty), str(tmp_path / "out")))
    listed = {r["run_id"]: r for r in json.loads(body)["runs"]}
    assert status == 200 and set(listed) == {ids["before"], ids["edge"], ids["filesealed"]}
    assert listed[ids["before"]]["group"] == "g" and listed[ids["before"]]["trades"] == 2
    status, _, body = dash._backtest(f"/api/backtest/run/{ids['before']}", (str(empty), str(tmp_path / "out")))
    tabs = {t["label"]: t["text"] for t in json.loads(body)["tabs"]}
    assert status == 200 and "往復の数: 2" in tabs["概要"] and "往復 2 件" in tabs["取引"]
    status, _, _ = dash._backtest(f"/api/backtest/run/{ids['after']}", (str(empty), str(tmp_path / "out")))
    assert status == 404


def test_the_shared_place_is_not_ignored_by_git():
    import subprocess

    r = subprocess.run(["git", "check-ignore", "backtest_runs_shared/k1_newenv_g/" + "a" * 64 + "/record.json",
                        "backtest_runs_shared/k1_newenv_g/" + "a" * 64 + "/metrics.json.gz",
                        "backtest_runs_shared/k1_newenv_g/SHARED.json"], cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 1 and r.stdout == ""  # 1 = none of the paths is ignored
