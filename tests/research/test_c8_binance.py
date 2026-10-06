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
    # 値段は整数のセント(0.01 USDT = 1)で返る(委任文 fix1 の 1)。cents=False なら置き場の USDT のまま
    assert (b0.open, b0.high, b0.low, b0.close) == (10000.0, 10100.0, 9900.0, 10050.0)
    assert f["n_not_whole_cent"] == 0 and f["price_unit"] == bn_bars.PRICE_UNIT_CENTS
    bars_u, fu = bn_bars.load_chunk(iso("2019-01-01T00:00:00Z"), iso("2019-01-01T00:10:00Z"), str(tmp_path), cents=False)
    assert (bars_u[0].open, bars_u[0].close) == (100.0, 100.5) and "n_not_whole_cent" not in fu
    assert [b.volume for b in bars_u] == [b.volume for b in bars]
    assert int(b0.start_time_ns) == iso("2019-01-01T00:00:00Z")  # open_time = 足の始まり
    assert int(b0.exchange_time_ns) == iso("2019-01-01T00:01:00Z")  # 受け取り = 足の終わり
    starts = [int(b.start_time_ns) for b in bars]
    assert iso("2019-01-01T00:04:00Z") not in starts and iso("2019-01-01T00:06:00Z") not in starts
    # 範囲の終わりの足は、足の全体が範囲に入るときだけ残る
    bars2, _ = bn_bars.load_chunk(iso("2019-01-01T00:00:00Z"), iso("2019-01-01T00:03:00Z"), str(tmp_path))
    assert len(bars2) == 3


def test_unit_does_not_change_exposure_or_pnl():
    """同値の無い作り物の足(終値 = 平均の足がセッションの最初の足だけ)の上でだけ成り立つ。平らな区間では
    test_flat_bars_float_vs_cents のとおり、浮動小数の値段では持ち高が変わる。"""
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


def _flat_session_bars(price: float, n_flat: int = 60, n_after: int = 30, start_iso: str = "2019-01-01T15:00:00Z"):
    """セッションの最初の n_flat 本が同じ値段 price(始値 = 高値 = 安値 = 終値)、その後 n_after 本が 1 セントずつ上がる足。"""
    from bot.bt.core import BarEvent
    t0 = iso(start_iso)
    out = []
    for i in range(n_flat + n_after):
        o = price if i < n_flat else round(price + 0.01 * (i - n_flat), 2)
        c = price if i < n_flat else round(price + 0.01 * (i - n_flat + 1), 2)
        s_ = t0 + i * 60 * NS
        out.append(BarEvent(received_time_ns=s_ + 60 * NS, start_time_ns=s_, open=o, high=max(o, c), low=min(o, c),
                            close=c, volume=1.0))
    return out


@pytest.mark.parametrize("price", [35698.72, 11868.04])
def test_flat_bars_float_vs_cents(price):
    """値段 = 平均のときの持ち高(批評家 1 回目の問 1): 0.01 USDT 刻みの小数のままなら平らな区間で ±1 が出る。
    整数のセントにすれば和が正確で、平らな区間の持ち高は全部 0(bitFlyer の 1 円単位と同じ)。"""
    decl = rc.declarations()
    bars = _flat_session_bars(price)
    r_f = run_card(SessionMeanRevert("jst_day"), bars, references={}, declarations=decl, venue="binance", symbol="BTCUSDT")
    cents, n_off = bn_bars.to_cents(bars)
    assert n_off == 0 and cents[0].close == round(price * 100)
    r_c = run_card(SessionMeanRevert("jst_day"), list(cents), references={}, declarations=decl, venue="binance", symbol="BTCUSDT")
    flat_f, flat_c = r_f.exposure[:60], r_c.exposure[:60]
    assert np.count_nonzero(flat_f) > 0  # 浮動小数のままなら 0 でない持ち高が出る(この試験が空振りでないこと)
    assert set(np.abs(flat_f[flat_f != 0]).tolist()) == {1.0}
    assert np.count_nonzero(flat_c) == 0  # 整数のセントなら全部 0
    assert np.all(r_c.exposure[60:] == -1.0)  # 平らな区間の後は値段が平均より上 → −1(セントでも向きは同じ)
    d = rc.close_eq_mean(r_c)
    assert d["n_close_eq_mean"] == 60 and d["n_first_of_session"] == 1 and d["n_other"] == 59
    assert d["n_nonzero_exposure_at_eq"] == 0 and d["n_close_not_integer"] == 0 and d["sum_exact_in_card"]
    assert rc.close_eq_mean(r_f)["not_computed"]  # USDT の小数のままでは正確に比べない


def test_cents_same_as_usdt_without_ties():
    """同値(終値 = 平均)がセッションの最初の足にしか無い足では、セントと USDT(0.01 刻み)で持ち高が同じ、損益の bp も同じ。"""
    decl = rc.declarations()
    cents, _ = bn_bars.to_cents(rc.fabricated_bars(n=3 * 1440, scale=356.9872))
    from dataclasses import replace
    usdt = [replace(b, open=b.open / 100, high=b.high / 100, low=b.low / 100, close=b.close / 100) for b in cents]
    r_c = run_card(SessionMeanRevert("jst_day"), list(cents), references={}, declarations=decl, venue="binance", symbol="BTCUSDT")
    r_u = run_card(SessionMeanRevert("jst_day"), usdt, references={}, declarations=decl, venue="binance", symbol="BTCUSDT")
    d = rc.close_eq_mean(r_c)
    assert d["n_other"] == 0 and d["n_session_end_bar"] == 0  # 前提: 同値はセッションの最初の足だけ
    assert np.array_equal(r_c.exposure, r_u.exposure, equal_nan=True)
    assert np.allclose(pnl(r_c).pnl_bp, pnl(r_u).pnl_bp, rtol=1e-9, atol=1e-9)
    assert np.allclose(rc.mid_pnl(r_c, pnl(r_c)), rc.mid_pnl(r_u, pnl(r_u)), rtol=1e-9, atol=1e-9)


def test_to_cents_counts_not_whole_cent():
    from bot.bt.core import BarEvent
    t = iso("2019-01-01T00:00:00Z")
    b = BarEvent(received_time_ns=t + 60 * NS, start_time_ns=t, open=100.005, high=100.02, low=100.0, close=100.01, volume=1.0)
    out, n_off = bn_bars.to_cents([b])
    assert n_off == 1 and (out[0].high, out[0].low, out[0].close) == (10002.0, 10000.0, 10001.0)
    assert out[0].volume == 1.0 and out[0].start_time_ns == t


def test_prereg_hi_fixed():
    """事前登録の値の固定(批評家 1 回目の問 3): 読む終わり = 2023-12-17T15:00:00Z(封印の前)。"""
    assert bn_bars.HI == iso("2023-12-17T15:00:00Z")
    with pytest.raises(SystemExit):
        bn_bars.check_range(iso("2023-12-17T00:00:00Z"), iso("2023-12-17T15:01:00Z"))


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


def test_half_boundary_even_number_of_days():
    """偶数の日数: 6 日 → 6 // 2 = 3 番目(0 から数える)の日から後半(前半 3 日・後半 3 日)。"""
    days = ["2019-01-06", "2019-01-01", "2019-01-03", "2019-01-02", "2019-01-05", "2019-01-04"]
    b = sp.half_boundary(days)
    assert b == "2019-01-04"
    t = sp.count_table({d: "low" for d in days}, b)
    assert t["first_half"]["total"] == 3 and t["second_half"]["total"] == 3


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
    bars, _ = bn_bars.to_cents(rc.fabricated_bars(n=7 * 1440, drop={i_end, i_end2}, zero_volume={10, 2000}, scale=356.9872))
    bars = list(bars)
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
    # 値段の単位: run はセント、trades.json.gz は USDT に戻す
    opens = set(run2.open.tolist())
    assert all(round(x * 100) in opens for x in list(tr["entry_px"]) + list(tr["exit_px"]))
    assert max(tr["entry_px"]) < 1e5 < min(opens)  # USDT(3 万台)とセント(300 万台)
    rec = json.loads((out / "run_record.json").read_text(encoding="utf-8"))
    assert rec["price_unit"]["run_npz_and_card"] == bn_bars.PRICE_UNIT_CENTS
    ce = rec["close_eq_mean"]
    assert ce["n_close_not_integer"] == 0 and ce["n_nonzero_exposure_at_eq"] == 0
    assert ce["n_first_of_session"] == ce["n_sessions"] and ce["n_close_eq_mean"] >= ce["n_sessions"]


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


def test_interval_matches_prereg_values():
    """事前登録の値の固定(批評家 1 回目の問 3): 区間 = block_bootstrap_ci(塊 5・1,000 回・種 20261006・circular)。
    比べる相手は台本の定数でなく、事前登録の数を直に書いた呼び出し。"""
    from bot.bt.validation import block_bootstrap_ci
    x = np.random.default_rng(11).normal(size=80) + 0.3 * np.sin(np.arange(80) / 3.0)
    want = block_bootstrap_ci(x.tolist(), block_len=5, n_resamples=1000, seed=20261006, alpha=0.05,
                              method="circular", statistic="mean")
    got = rg.stat(x)
    assert got["ci"] == [want.lo, want.hi] and got["se"] == want.se
    assert got["mde"] == pytest.approx(2.8 * want.se)
    assert got["per_day_bp"] == pytest.approx(float(np.mean(x)))
    # 端がちょうど 0 なら「0 を含む」(G7)
    assert rg.mark([0.0, 1.0]) == "0 を含む" and rg.mark([-1.0, 0.0]) == "0 を含む" and rg.mark([0.0, 0.0]) == "0 を含む"


YDAYS = DAYS + ["2021-03-01", "2021-03-02", "2021-03-03", "2021-03-04", "2021-03-05", "2021-03-06"]
YCLS = {**CLS, **dict(zip(YDAYS[8:], ["high", "low", "mid", "high", "low", "low"]))}
YPNL = {**PNL, **dict(zip(YDAYS[8:], [10.0, -1.0, 2.0, -3.0, 4.0, 5.0]))}


def test_g9_by_year_hand_numbers():
    pm = {d: v * 2.0 + 1.0 for d, v in YPNL.items()}  # 中ほどは別の値で、別に計算されること
    res = rg.read_all({"open": YPNL, "mid": pm}, YCLS, "2021-03-01", set(), None, placebo_n=50)
    for price, P in (("open", YPNL), ("mid", pm)):
        yrs = res["prices"][price]["by_year"]["years"]
        assert list(yrs) == ["2020", "2021"]
        for y, n in (("2020", 8), ("2021", 6)):
            ds = [d for d in YDAYS if d.startswith(y)]
            yr = yrs[y]
            assert yr["n_days"] == n
            want_a = -sum(P[d] for d in ds if YCLS[d] != "high") / n
            want_b = -sum(P[d] for d in ds if YCLS[d] == "low") / n
            assert yr["diffs"]["A-none"]["per_day_bp"] == pytest.approx(want_a)
            assert yr["diffs"]["B-none"]["per_day_bp"] == pytest.approx(want_b)
            assert yr["diffs"]["A-none"]["mark"] in ("0 より上", "0 を含む", "0 より下")
            for k in ("low", "mid", "high"):
                xs = [P[d] for d in ds if YCLS[d] == k]
                assert yr["by_class"][k]["n_days"] == len(xs)
                assert yr["by_class"][k]["per_day_bp"] == pytest.approx(sum(xs) / len(xs))
            # 区間は G6 のまま(その年の差の列に当てる)
            x = np.array([(P[d] if YCLS[d] == "high" else 0.0) - P[d] for d in ds])
            assert yr["diffs"]["A-none"]["ci"] == rg.stat(x)["ci"]
    md = rg.to_md(res)
    assert "G9 年ごと" in md and "| 2021 | 6 |" in md


def _placebo_ref(x, m, n_res, seed, block=5):
    """G10 を台本と別に書いた物(事前登録の数を直に書く)。"""
    rng = np.random.default_rng(seed)
    n = len(x)
    out = []
    for _ in range(n_res):
        rm = set()
        while len(rm) < m:
            s0 = int(rng.integers(0, n))
            for j in range(block):
                if len(rm) == m:
                    break
                rm.add((s0 + j) % n)
        out.append(-sum(x[i] for i in rm) / n)
    return np.array(out)


def test_g10_placebo_matches_reference_and_prereg_values():
    rng = np.random.default_rng(5)
    days = [str(np.datetime64("2020-01-01") + i) for i in range(40)]
    cls = {d: ["low", "mid", "high"][int(rng.integers(0, 3))] for d in days}
    pnl_ = {d: float(rng.normal()) for d in days}
    res = rg.read_all({"open": pnl_, "mid": pnl_}, cls, days[20], set(), None)
    pl = res["placebo"]
    assert pl["seed"] == 20261007 and pl["n_resamples"] == 1000 and pl["block_days"] == 5
    x = [pnl_[d] for d in days]
    for f, m in (("A", sum(cls[d] != "high" for d in days)), ("B", sum(cls[d] == "low" for d in days))):
        q = pl["forms"][f]["open"]
        ref = _placebo_ref(x, m, 1000, 20261007)
        actual = res["prices"]["open"]["all"]["diffs"][f"{f}-none"]["per_day_bp"]
        assert q["n_removed"] == m and q["n_days"] == 40 and q["removed_exactly_m"]
        assert q["actual_bp"] == actual
        assert q["upper_share"] == pytest.approx(float(np.mean(ref >= actual)))
        assert q["q95_bp"] == pytest.approx(float(np.quantile(ref, 0.95)))
        assert q["actual_gt_q95"] == bool(actual > np.quantile(ref, 0.95))
        assert pl["forms"][f]["mid"] == q  # 同じ損益なら始値と中ほどで同じ(同じ外し方を当てる)
    assert "G10 対照群" in rg.to_md(res)


def test_g10_upper_share_counts_ties():
    """上側の割合は「実際の差以上(≥)」の割合: 損益が全部の日で同じなら、対照の差は全部実際の差と等しく、割合は 1。"""
    days = [str(np.datetime64("2020-01-01") + i) for i in range(30)]
    cls = {d: ["low", "mid", "high"][i % 3] for i, d in enumerate(days)}
    pnl_ = {d: 2.0 for d in days}
    actual = {"open": {"A": -2.0 * 20 / 30, "B": -2.0 * 10 / 30}}
    pl = rg.placebo({"open": pnl_}, cls, actual, n_res=50)
    for f in ("A", "B"):
        q = pl["forms"][f]["open"]
        assert q["upper_share"] == 1.0 and not q["actual_gt_q95"] and q["q95_bp"] == pytest.approx(actual["open"][f])


def test_g10_removed_exactly_and_circular():
    rng = np.random.default_rng(0)
    for n, m in ((23, 17), (23, 0), (23, 23), (100, 37)):
        for _ in range(20):
            assert rg.placebo_removed(n, m, rng).sum() == m
    # 1 つの塊だけで足りるとき: 循環する 5 日の連なり
    for _ in range(50):
        idx = np.flatnonzero(rg.placebo_removed(7, 5, rng))
        gaps = sorted(set(range(7)) - set(idx.tolist()))
        assert len(gaps) == 2 and (gaps[1] - gaps[0]) % 7 in (1, 6)  # 残る 2 日が隣り合う(循環)
    # 最後の塊を切る: m = 3 なら 3 日の連なり
    for _ in range(50):
        idx = set(np.flatnonzero(rg.placebo_removed(10, 3, rng)).tolist())
        assert any(idx == {(s + j) % 10 for j in range(3)} for s in range(10))
    with pytest.raises(ValueError):
        rg.placebo_removed(5, 6, rng)
    a = rg.placebo_masks(30, 12, 20261007, 20)
    assert np.array_equal(a, rg.placebo_masks(30, 12, 20261007, 20))
    assert not np.array_equal(a, rg.placebo_masks(30, 12, 1, 20))


def test_g10_null_uniform_and_class_driven_near_zero():
    """作り物: (1) 区分が損益と無関係なら上側の割合はおおむね一様、(2) 区分が損益を決めるなら 0 に近い。"""
    shares = []
    for k in range(60):
        rng = np.random.default_rng(1000 + k)
        days = [str(np.datetime64("2020-01-01") + i) for i in range(150)]
        cls = {d: ["low", "mid", "high"][int(rng.integers(0, 3))] for d in days}
        pnl_ = {d: float(rng.normal()) for d in days}
        actual = {"open": {"A": -sum(pnl_[d] for d in days if cls[d] != "high") / 150,
                           "B": -sum(pnl_[d] for d in days if cls[d] == "low") / 150}}
        pl = rg.placebo({"open": pnl_}, cls, actual, n_res=200)
        shares += [pl["forms"][f]["open"]["upper_share"] for f in ("A", "B")]
    shares = np.array(shares)
    assert 0.38 < shares.mean() < 0.62
    assert np.mean(shares < 0.05) < 0.15 and np.mean(shares > 0.95) < 0.15
    assert np.mean(shares < 0.5) == pytest.approx(0.5, abs=0.15)
    rng = np.random.default_rng(7)
    days = [str(np.datetime64("2020-01-01") + i) for i in range(300)]
    cls = {d: ["low", "mid", "high"][int(rng.integers(0, 3))] for d in days}
    level = {"low": -10.0, "mid": 0.0, "high": 10.0}
    pnl_ = {d: level[cls[d]] + float(rng.normal()) for d in days}
    res = rg.read_all({"open": pnl_, "mid": pnl_}, cls, days[150], set(), None, placebo_n=300)
    for f in ("A", "B"):
        for price in ("open", "mid"):
            q = res["placebo"]["forms"][f][price]
            assert q["upper_share"] <= 0.01 and q["actual_gt_q95"]


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
    fab = list(bn_bars.to_cents(rc.fabricated_bars(n=7 * 1440, scale=356.9872))[0])  # 本物の口と同じくセント
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
    assert rec["close_eq_mean"]["n_close_not_integer"] == 0 and rec["close_eq_mean"]["n_nonzero_exposure_at_eq"] == 0
    monkeypatch.setattr(sys, "argv", ["bn_run_c8.py", "--end", "2023-12-18T00:00:00Z", "--out-root", str(tmp_path)])
    with pytest.raises(SystemExit):  # 終わりが 2023-12-17T15:00Z より後なら、読む前に拒む
        rc.main()
