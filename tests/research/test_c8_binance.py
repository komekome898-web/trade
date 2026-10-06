"""カード 8 の門を Binance の 1 分足で確かめる部品(scripts/w4_measure/c8_binance/)の試験。作り物の足と作り物の日ごとの損益だけを使う。"""
from __future__ import annotations

import csv
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "w4_measure"))
sys.path.insert(0, str(REPO / "scripts" / "w4_measure" / "c8_binance"))

import bn_bars  # noqa: E402
import bn_read_gate as rg  # noqa: E402
import bn_run_c8 as rc  # noqa: E402
import bn_split as sp  # noqa: E402
import vol_split_daily as vs  # noqa: E402
from common import BIN_DIR, iso  # noqa: E402

from bot.research.cards.library.c8_session_mean_revert import SessionMeanRevert  # noqa: E402
from bot.research.cards.pnl import pnl  # noqa: E402
from bot.research.cards.run import run_card  # noqa: E402
from bot.research.trade_record import read_trades_json  # noqa: E402

NS = 10**9


# ---------- 部品 1 ----------

def test_range_refused_before_reading():
    with pytest.raises(SystemExit):
        bn_bars.check_range(bn_bars.LO, bn_bars.HI + 60 * NS)
    with pytest.raises(SystemExit):
        bn_bars.check_range(bn_bars.LO - 60 * NS, bn_bars.HI)
    with pytest.raises(SystemExit):  # 2024 年以降へは行かない(終わりで拒む)
        list(bn_bars.iter_range(iso("2023-12-01T00:00:00Z"), iso("2024-01-02T00:00:00Z")))
    with pytest.raises(SystemExit):  # 1 回の読みは 1 つの暦年
        bn_bars.load_chunk(iso("2018-12-31T00:00:00Z"), iso("2019-01-01T01:00:00Z"))
    ch = bn_bars.year_chunks(bn_bars.LO, bn_bars.HI)
    assert [c[0] for c in ch] == list(range(2017, 2024))
    assert ch[0][1] == bn_bars.LO and ch[-1][2] == bn_bars.HI


def _write_fake_year(root: Path, rows: list) -> None:
    d = root / BIN_DIR
    d.mkdir(parents=True)
    with gzip.open(d / "binance_BTCUSDT_1m_2019.csv.gz", "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["open_time", "open", "high", "low", "close", "volume", "quote_volume", "n_trades", "taker_buy_base"])
        w.writerows(rows)


def test_loader_drops_no_trade_minutes_and_counts_missing(tmp_path):
    rows = []
    for m in range(10):
        if m == 4:  # 行の無い分(分の頭から 20 秒ずれた行だけがある: off_grid、落とす)
            rows.append(["2019-01-01 00:04:20+00:00", "104", "105", "103", "104.5", "1.5", "150", "3", "0.5"])
            continue
        t = f"2019-01-01 00:{m:02d}:00+00:00"
        if m == 6:  # 取引の無い分(Binance は前の終値で埋める)
            rows.append([t, "105", "105", "105", "105", "0.0", "0.0", "0", "0.0"])
        else:
            rows.append([t, f"{100 + m}", f"{101 + m}", f"{99 + m}", f"{100.5 + m}", "1.5", "150", "3", "0.5"])
    _write_fake_year(tmp_path, rows)
    bars, f = bn_bars.load_chunk(iso("2019-01-01T00:00:00Z"), iso("2019-01-01T00:10:00Z"), str(tmp_path))
    assert f["n_bars_kept"] == 8 and len(bars) == 8
    assert f["n_synthetic_dropped"] == 1 and f["n_missing_minutes"] == 1
    assert f["n_off_grid_dropped"] == 1
    assert f["files"][0]["rows_read"] == 10 and f["files"][0]["rows_kept"] == 10 and f["files"][0]["sealed_unit"] is None
    assert f["n_ntrades0_volume_pos"] == 0 and f["n_kept_volume0"] == 0 and f["n_synthetic_not_flat"] == 0
    assert f["resolution"] == {"gap": "accept", "synthetic": "drop", "off_grid": "drop"}
    b0 = bars[0]
    assert int(b0.start_time_ns) == iso("2019-01-01T00:00:00Z")  # open_time = 足の始まり
    assert int(b0.exchange_time_ns) == iso("2019-01-01T00:01:00Z")  # 受け取り = 足の終わり
    starts = [int(b.start_time_ns) for b in bars]
    assert iso("2019-01-01T00:04:00Z") not in starts and iso("2019-01-01T00:06:00Z") not in starts
    # 範囲の終わりの足は、足の全体が範囲に入るときだけ残る
    bars2, _ = bn_bars.load_chunk(iso("2019-01-01T00:00:00Z"), iso("2019-01-01T00:03:00Z"), str(tmp_path))
    assert len(bars2) == 3


def test_unit_does_not_change_exposure_or_pnl():
    decl = rc.declarations()
    out = []
    for k in (1.0, 157.3):
        bars = rc.fabricated_bars(n=2 * 1440, scale=k)
        r = run_card(SessionMeanRevert("jst_day"), bars, references={}, declarations=decl, venue="binance", symbol="BTCUSDT")
        out.append((r, pnl(r)))
    (r1, p1), (r2, p2) = out
    assert np.array_equal(r1.exposure, r2.exposure, equal_nan=True)
    assert np.allclose(p1.pnl_bp, p2.pnl_bp, rtol=1e-9, atol=1e-9)
    assert np.allclose(rc.mid_pnl(r1, p1), rc.mid_pnl(r2, p2), rtol=1e-9, atol=1e-9)


# ---------- 部品 2 ----------

class _B:
    def __init__(self, start_iso, close):
        self.start_time_ns = iso(start_iso)
        self.close = close


def test_closes_by_jst_day_of_bar_start():
    out = sp.add_closes({}, [_B("2019-01-01T14:58:00Z", 1.0), _B("2019-01-01T14:59:00Z", 2.0), _B("2019-01-01T15:00:00Z", 3.0)])
    assert out == {"2019-01-01": [1.0, 2.0], "2019-01-02": [3.0]}


def test_half_boundary_and_counts():
    cls = {"2019-01-01": "low", "2019-01-02": "high", "2019-01-03": "mid", "2020-01-01": "high", "2020-01-02": "high"}
    b = sp.half_boundary(list(cls))
    assert b == "2019-01-03"  # 5 日 → 5 // 2 = 2 番目の日から後半
    t = sp.count_table(cls, b)
    assert t["by_year"]["2019"] == {"low": 1, "mid": 1, "high": 1, "total": 3}
    assert t["by_year"]["2020"] == {"low": 0, "mid": 0, "high": 2, "total": 2}
    assert t["first_half"] == {"low": 1, "mid": 0, "high": 1, "total": 2}
    assert t["second_half"] == {"low": 0, "mid": 1, "high": 2, "total": 3}
    assert t["all"]["total"] == 5


def test_edges_match_classify():
    from datetime import date, timedelta
    vol = {}
    d = date(2018, 1, 1)
    rng = np.random.default_rng(1)
    while d < date(2019, 3, 1):
        vol[d.isoformat()] = float(rng.random())
        d += timedelta(days=1)
    cls = vs.classify(vol)
    e = sp.edges_by_year(vol)
    assert set(e) == {2019} and e[2019]["from_year"] == 2018 and e[2019]["n_days_from_year"] == 365
    assert sp.check_edges(vol, cls, e) == 0
    assert all(k.startswith("2019") for k in cls)
    # 前の暦年が 300 日未満なら分けない(Binance の 2017 年は 8 月 17 日から)
    short = {k: v for k, v in vol.items() if k >= "2018-08-17"}
    assert not any(k.startswith("2019") for k in vs.classify(short))


# ---------- 部品 3 ----------

def _session_end_index(bars, end_iso="2019-01-01T15:00:00Z"):
    return [i for i, b in enumerate(bars) if int(b.exchange_time_ns) == iso(end_iso)][0]


def test_run_outputs_carry_and_mid(tmp_path):
    base = rc.fabricated_bars(n=7 * 1440)
    i_end = _session_end_index(base)
    i_end2 = _session_end_index(base, "2019-01-02T15:00:00Z")
    bars = rc.fabricated_bars(n=7 * 1440, drop={i_end, i_end2}, zero_volume={10, 2000})
    decl = rc.declarations()
    run1, _ = rc.run_chunks(SessionMeanRevert("jst_day"), [("all", bars)], decl)
    k = len(bars) // 3
    run2, _ = rc.run_chunks(SessionMeanRevert("jst_day"), [("a", bars[:k]), ("b", bars[k:2 * k]), ("c", bars[2 * k:])], decl)
    assert np.array_equal(run1.exposure, run2.exposure, equal_nan=True)  # 区切りでつないでも同じ
    s = rc.write_outputs(run2, str(tmp_path / "jst_day"), int(bars[0].start_time_ns), int(bars[-1].exchange_time_ns), {"chunks": []})
    out = tmp_path / "jst_day"
    for f in ("daily.csv", "daily_mid.csv", "daily_stats.json", "extra.json", "diagnostics.json", "run_record.json",
              "trades.json.gz", "boundary_carry_days.csv", "run.npz"):
        assert (out / f).exists(), f
    c = s["boundary_carry_check"]
    assert c["same"] and c["n_carried_diag"] == c["n_carried_rewrite"]
    # 区切りの足を消したので、持ち高 ≠ 0 なら区切りをまたぐ
    p = pnl(run2)
    n, rows = rc.carry_rows(run2, p)
    dec = np.flatnonzero(run2.decided)
    for end_iso in ("2019-01-01T15:00:00Z", "2019-01-02T15:00:00Z"):
        last = dec[run2.end_ns[dec] < iso(end_iso)][-1]
        if run2.exposure[last] != 0:
            want_day = "2019-01-01" if end_iso.startswith("2019-01-01") else "2019-01-02"
            assert any(r["day"] == want_day and r["t"] == rc.to_iso(int(run2.end_ns[last])) for r in rows)
    with open(out / "boundary_carry_days.csv", encoding="utf-8") as fh:
        assert {r["day"] for r in csv.DictReader(fh)} == {r["day"] for r in rows}
    # 中ほど: 手で作った値と daily_mid.csv
    mid = (run2.high + run2.low) / 2
    pm = p.exposure * (mid[p.exit_bar] / mid[p.fill_bar] - 1) * 1e4
    days = np.array([str(np.datetime64((int(t) + 9 * 3600 * NS) // (86400 * NS), "D")) for t in p.t_ns])
    dm = rg.read_daily(str(out / "daily_mid.csv"))
    for d in set(days.tolist()):
        assert abs(dm[d] - pm[days == d].sum()) < 1e-9
    do = rg.read_daily(str(out / "daily.csv"))
    for d in set(days.tolist()):
        assert abs(do[d] - p.pnl_bp[days == d].sum()) < 1e-9
    tr = read_trades_json(str(out / "trades.json.gz"))
    assert abs(sum(tr["pnl_bp"]) - p.pnl_bp.sum()) < 1e-3 * max(1, len(tr["pnl_bp"]))
    assert set(tr["side"]) <= {1, -1}


# ---------- 部品 4 ----------

DAYS = ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04", "2020-01-05", "2020-01-06", "2020-01-07", "2020-01-08"]
CLS = dict(zip(DAYS, ["low", "mid", "high", "high", "low", "mid", "high", "low"]))
PNL = dict(zip(DAYS, [1.0, -2.0, 3.0, 4.0, -5.0, 6.0, -7.0, 8.0]))


def test_gates_hand_numbers_and_unclassified_not_counted():
    pnl_ = {**PNL, "2019-12-31": 100.0}  # 区分の無い日
    res = rg.read_all({"open": pnl_, "mid": PNL}, CLS, "2020-01-05", set(), {"n_carried": 0, "carried_sum_bp": 0.0})
    r = res["prices"]["open"]
    assert r["n_daily_rows_without_class"] == 1 and r["n_classified_without_daily_row"] == 0
    a = r["all"]
    assert a["n_days"] == 8
    assert a["forms"]["none"]["all_days"]["per_day_bp"] == pytest.approx(sum(PNL.values()) / 8)
    assert a["forms"]["A"]["all_days"]["per_day_bp"] == pytest.approx((3 + 4 - 7) / 8)
    assert a["forms"]["A"]["entered_days"]["per_day_bp"] == pytest.approx((3 + 4 - 7) / 3)
    assert a["forms"]["B"]["all_days"]["per_day_bp"] == pytest.approx((-2 + 3 + 4 + 6 - 7) / 8)
    assert a["forms"]["B"]["entered_days"]["per_day_bp"] == pytest.approx((-2 + 3 + 4 + 6 - 7) / 5)
    assert (a["forms"]["A"]["n_entered"], a["forms"]["B"]["n_entered"], a["forms"]["none"]["n_entered"]) == (3, 5, 8)
    assert a["forms"]["A"]["entered_share"] == pytest.approx(3 / 8) and a["forms"]["B"]["entered_share"] == pytest.approx(5 / 8)
    assert a["diffs"]["A-none"]["per_day_bp"] == pytest.approx(-(1 - 2 - 5 + 6 + 8) / 8)
    assert a["diffs"]["B-none"]["per_day_bp"] == pytest.approx(-(1 - 5 + 8) / 8)
    assert a["diffs"]["A-none"]["mde"] == pytest.approx(2.8 * a["diffs"]["A-none"]["se"])
    # 前半・後半(境 2020-01-05 から後半)
    assert r["first_half"]["n_days"] == 4 and r["second_half"]["n_days"] == 4
    assert r["first_half"]["forms"]["none"]["all_days"]["per_day_bp"] == pytest.approx((1 - 2 + 3 + 4) / 4)
    # 区分ごと
    assert a["by_class"]["low"]["per_day_bp"] == pytest.approx((1 - 5 + 8) / 3) and a["by_class"]["low"]["n_days"] == 3
    assert a["by_class"]["high"]["per_day_bp"] == pytest.approx((3 + 4 - 7) / 3)


def test_gated_days_are_zero():
    g = rg.gated(DAYS, PNL, CLS, "A")
    assert [x for x, d in zip(g, DAYS) if CLS[d] != "high"] == [0.0] * 5
    g = rg.gated(DAYS, PNL, CLS, "B")
    assert [x for x, d in zip(g, DAYS) if CLS[d] == "low"] == [0.0] * 3
    assert [x for x, d in zip(g, DAYS) if CLS[d] != "low"] == [PNL[d] for d in DAYS if CLS[d] != "low"]


def test_interval_fixed_by_seed():
    x = np.random.default_rng(3).normal(size=60)
    a, b = rg.stat(x), rg.stat(x)
    assert a == b and a["ci"][0] <= a["per_day_bp"] <= a["ci"][1]
    assert rg.mark([0.1, 0.5]) == "0 より上" and rg.mark([-0.5, -0.1]) == "0 より下" and rg.mark([-0.1, 0.1]) == "0 を含む"
    assert rg.mark(None) is None
    assert rg.stat([1.0])["ci"] is None and rg.stat([])["per_day_bp"] is None


def test_carry_days_removed_from_diffs():
    carry = {"2020-01-02", "2020-01-08", "2021-05-05"}  # 最後の日は区分が無い
    res = rg.read_all({"open": PNL, "mid": PNL}, CLS, "2020-01-05", carry, {"n_carried": 4, "carried_sum_bp": 1.5})
    w = res["prices"]["open"]["all"]["without_carry_days"]
    assert w["n_days"] == 6 and w["n_removed"] == 2
    kept = [d for d in DAYS if d not in carry]
    want_a = sum((PNL[d] if CLS[d] == "high" else 0.0) - PNL[d] for d in kept) / 6
    want_b = sum((0.0 if CLS[d] == "low" else PNL[d]) - PNL[d] for d in kept) / 6
    assert w["diffs"]["A-none"]["per_day_bp"] == pytest.approx(want_a)
    assert w["diffs"]["B-none"]["per_day_bp"] == pytest.approx(want_b)
    assert res["boundary_carry"]["from_diagnostics"] == {"n_carried": 4, "carried_sum_bp": 1.5}
    assert res["boundary_carry"]["n_carry_days"] == 3 and res["boundary_carry"]["n_carry_days_in_universe"] == 2
    assert "A と B に順位は付けない" in rg.to_md(res)


def test_reader_main_on_written_files(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    for name in ("daily.csv", "daily_mid.csv"):
        (run / name).write_text("day,pnl_bp,n\n" + "".join(f"{d},{PNL[d]!r},1\n" for d in DAYS), encoding="utf-8")
    (run / "diagnostics.json").write_text(json.dumps({"5_boundary_carry": {"n_carried": 1, "carried_sum_bp": 2.0}}), encoding="utf-8")
    (run / "boundary_carry_days.csv").write_text("day,t,pnl_bp,minutes_after_boundary\n2020-01-03,2020-01-03T14:58:00Z,2.0,1.0\n", encoding="utf-8")
    cj = tmp_path / "classes.json"
    cj.write_text(json.dumps({"classes": CLS, "half_boundary_day": "2020-01-05"}), encoding="utf-8")
    sys.argv = ["bn_read_gate.py", "--run-dir", str(run), "--classes", str(cj), "--out", str(tmp_path / "out")]
    assert rg.main() == 0
    res = json.loads((tmp_path / "out" / "gate_read.json").read_text(encoding="utf-8"))
    assert res["prices"]["mid"]["all"]["without_carry_days"]["n_removed"] == 1


def test_year_end_chunk_is_one_year():
    ch = bn_bars.year_chunks(bn_bars.LO, bn_bars.HI)
    with pytest.raises(SystemExit, match="1 回の読みは"):
        bn_bars.load_chunk(iso("2018-12-31T00:00:00Z"), iso("2019-01-01T00:01:00Z"))
    # 年の終わりちょうどで切った区切りは 1 つの暦年として通る(ファイルが無い根では、年の門の後で読みが拒まれる)
    y, a, b = ch[0]
    with pytest.raises(Exception) as ei:
        bn_bars.load_chunk(a, b, "/nonexistent_root_for_test")
    assert "1 回の読みは" not in str(ei.value)


def test_main_non_dry_path_on_fabricated_bars(tmp_path, monkeypatch):
    """段 2 の経路(--dry なし)を、本物の足を読まずに通す(部品 1 の iter_range を作り物に差し替える)。"""
    fab = rc.fabricated_bars(n=7 * 1440)
    k = len(fab) // 2
    seen = {}

    def fake_iter(lo, hi, **kw):
        seen["range"] = (lo, hi)
        yield 2019, fab[:k], {"year": 2019, "fake": True}
        yield 2019, fab[k:], {"year": 2019, "fake": True}

    monkeypatch.setattr(rc.bn_bars, "iter_range", fake_iter)
    monkeypatch.setattr(sys, "argv", ["bn_run_c8.py", "--start", "2019-01-01T12:00:00Z", "--end", "2019-01-08T12:00:00Z",
                                      "--out-root", str(tmp_path)])
    assert rc.main() == 0
    assert seen["range"] == (iso("2019-01-01T12:00:00Z"), iso("2019-01-08T12:00:00Z"))
    for f in ("daily.csv", "daily_mid.csv", "daily_stats.json", "extra.json", "diagnostics.json", "run_record.json",
              "trades.json.gz", "boundary_carry_days.csv", "run.npz"):
        assert (tmp_path / "jst_day" / f).exists(), f
    rec = json.loads((tmp_path / "jst_day" / "run_record.json").read_text(encoding="utf-8"))
    assert rec["boundary_carry_check"]["same"] and len(rec["chunks"]) == 2
    monkeypatch.setattr(sys, "argv", ["bn_run_c8.py", "--end", "2023-12-18T00:00:00Z", "--out-root", str(tmp_path)])
    with pytest.raises(SystemExit):  # 終わりが 2023-12-17T15:00Z より後なら、読む前に拒む
        rc.main()
