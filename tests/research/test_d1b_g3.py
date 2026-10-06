"""# 10(D1B_FRAMINGS の行 10、担当 G3)の台本 `scripts/d1b/g3/` の試験。

作り物のデータで: 各量が手計算と合うこと(割合・Wilson の区間を含む)/ 先読みが無いこと(時刻 t の判断に t より後の値を使っていない)/ カード 4 の約定の道が 1 分足のシミュレーターの 2 本の道と同じ処理であること。
値段・時刻は試験の入力で、データではない。約定の記録のファイルは開かない(2024 年の名前を拒むことだけを、開く前に確かめる)。
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "w4_measure"))
sys.path.insert(0, str(REPO / "scripts" / "d1b" / "g3"))

import g3_decisions as D  # noqa: E402
import g3_run as R  # noqa: E402
from g3_c4_replay import TradePathMatilda  # noqa: E402
from g3_trades import DayTrades, read_day  # noqa: E402

from bot.bt.core import BarEvent  # noqa: E402
from bot.research.matilda_limit_sim import MatildaLimitSim  # noqa: E402

NS = 1_000_000_000
M = 60 * NS
T0 = 1_704_067_200 * NS  # 2024-01-01T00:00:00Z(試験の時刻)
P = 1_000_000.0


def bar(i, o, c, h=None, lo=None, vol=1.0):
    h = max(o, c) if h is None else h
    lo = min(o, c) if lo is None else lo
    return BarEvent(received_time_ns=T0 + (i + 1) * M, exchange_time_ns=T0 + (i + 1) * M, start_time_ns=T0 + i * M,
                    open=o, high=h, low=lo, close=c, volume=vol)


def osc(i):
    return bar(i, P, P + 200) if i % 2 == 0 else bar(i, P + 200, P)


def base(n=40):
    return [osc(i) for i in range(n)]


def day_trades(rows):
    """rows: (分の番号, 秒, 側, 値段)。時刻の順に並べて DayTrades を作る。"""
    rows = sorted(rows, key=lambda r: (r[0], r[1]))
    ts = np.array([T0 + m * M + int(s * NS) for m, s, _sd, _p in rows], dtype=np.int64)
    sd = np.array([x[2] for x in rows], dtype=np.int8)
    px = np.array([x[3] for x in rows], dtype=float)
    return DayTrades("2024-01-01", ts, sd, px)


# ---------------------------------------------------------------- 約定の記録の読み口
def test_zigzag_keeps_only_turning_points_by_hand():
    dt = day_trades([(0, s, 1, p) for s, p in enumerate([100, 101, 103, 103, 102, 99, 100])])
    assert dt.zigzag(T0) == [100, 103, 99, 100]
    assert dt.zigzag(T0 + M) == []


def test_hl_order_first_trade_and_first_at_or_after_by_hand():
    dt = day_trades([(0, 1, -1, 100), (0, 2, 1, 105), (0, 3, -1, 95), (1, 5, 1, 96), (1, 9, -1, 94), (1, 20, 1, 99)])
    assert dt.hl_order(T0) == "up"  # 105 が 2 秒、95 が 3 秒
    assert dt.hl_order(T0 + M) == "down"  # 99 が 20 秒、94 が 9 秒
    assert dt.first_in_minute(T0 + M) == 3 and int(dt.side[3]) == 1
    assert dt.first_at_or_after(T0 + M + 6 * NS) == 4
    assert dt.first_at_or_after(T0 + 2 * M) is None


def test_2024_file_is_refused_before_opening():
    with pytest.raises(SystemExit):
        read_day("FX_BTC_JPY_20240101.csv.gz")


# ---------------------------------------------------------------- 決定
def test_exposure_decisions_by_hand_and_fill_skips_empty_bar():
    start = np.array([T0 + i * M for i in range(6)], dtype=np.int64)
    end = start + M
    vol = np.array([1, 1, 0, 1, 1, 1], dtype=float)
    decided = np.array([True, True, False, True, True, True])
    e = np.array([0.0, 1.0, np.nan, 1.0, -1.0, 0.0])
    ds = D.exposure_decisions(start, end, vol, decided, e)
    assert [(d["t_ns"], d["fill_ns"], d["dir"], d["size"], d["kind"]) for d in ds] == [
        (T0 + 2 * M, T0 + 3 * M, 1, 1.0, "open"),  # 足 1 の終わりで決め、足 2 は空なので足 3 の始値
        (T0 + 5 * M, T0 + 5 * M, -1, 2.0, "flip"),
        (T0 + 6 * M, None, 1, 1.0, "close")]  # 売り持ち −1 → 0 は買い。次の足が無い


def test_exposure_decisions_no_lookahead():
    rnd = random.Random(3)
    n = 50
    start = np.array([T0 + i * M for i in range(n)], dtype=np.int64)
    vol = np.ones(n)
    e = np.array([rnd.choice([-1.0, 0.0, 1.0]) for _ in range(n)])
    ds = D.exposure_decisions(start, start + M, vol, np.ones(n, bool), e)
    e2 = e.copy()
    e2[30:] = -e2[30:] + 0.5  # 足 30 から後を変える
    ds2 = D.exposure_decisions(start, start + M, vol, np.ones(n, bool), e2)
    cut = T0 + 30 * M
    assert [d for d in ds if d["t_ns"] <= cut] == [d for d in ds2 if d["t_ns"] <= cut]
    # 約定の分は決定の足より後(批評家の M2: 決定の足の始値で約定する誤りを捕まえる)
    assert ds and all(d["fill_ns"] is None or d["fill_ns"] >= d["t_ns"] for d in ds)


def test_read_decision_side_order_and_side_bp_by_hand():
    dt = day_trades([(3, 0, -1, 100), (3, 10, 1, 90), (3, 20, 1, 110)])
    r = D.read_decision(dt, T0 + 3 * M, 1)  # 買いの決定、始値は売りの約定、安値が先
    # side_bp = 向き × (始値の後で側 = 買いの最初の約定 90 − 始値 100) ÷ 100 × 1e4 = −1000、その約定まで 10 秒
    assert r == {"first_side": -1, "same_side": False, "hl_order": "down", "dir_first": False, "side_bp": -1000.0,
                 "side_wait_ms": 10000.0}
    r2 = D.read_decision(dt, T0 + 3 * M, -1)
    assert r2["same_side"] is True and r2["side_bp"] == 0.0 and r2["side_wait_ms"] == 0.0  # 始値そのものが売りの約定
    assert D.read_decision(dt, T0 + 4 * M, 1)["first_side"] is None
    dt0 = day_trades([(3, 0, 0, 100), (3, 1, 1, 101)])
    assert D.read_decision(dt0, T0 + 3 * M, 1)["same_side"] is None  # unknown は分母に入れない
    assert D.read_decision(dt0, T0 + 3 * M, -1)["side_bp"] is None  # 売りの約定が後に無い


def test_side_bp_search_stops_60_seconds_after_the_fill_minute_start():
    """向きの側の約定を探すのは約定の分の始まりから 60 秒まで(リードの決め)。60 秒ちょうど以後の約定は使わない。"""
    late = day_trades([(3, 0, -1, 100), (4, 0, 1, 90)])  # 買いの約定は分の始まりから 60 秒ちょうど
    assert D.read_decision(late, T0 + 3 * M, 1)["side_bp"] is None
    near = day_trades([(3, 0, -1, 100), (3, 59, 1, 90)])
    assert D.read_decision(near, T0 + 3 * M, 1)["side_bp"] == -1000.0
    # カード 9 の「秒」: t0 から 60 秒
    t0 = T0 + 2 * M + 30 * NS
    liq = day_trades([(2, 35, 1, 100), (3, 31, -1, 99)])  # 売りの約定は t0 + 61 秒
    assert D.read_liq_decision(liq, t0, -1)["sec"]["side_bp"] is None
    liq2 = day_trades([(2, 35, 1, 100), (3, 29, -1, 99)])  # t0 + 59 秒
    assert D.read_liq_decision(liq2, t0, -1)["sec"]["side_bp"] == pytest.approx(-1 * (99 - 100) / 100 * 1e4)


def test_next_with_side_by_hand():
    dt = day_trades([(0, 0, 1, 1), (0, 1, -1, 2), (0, 2, 0, 3), (0, 3, 1, 4)])
    assert [dt.next_with_side(i, 1) for i in range(4)] == [0, 3, 3, 3]
    assert [dt.next_with_side(i, -1) for i in range(4)] == [1, 1, None, None]


def test_read_decision_does_not_use_trades_after_the_fill_minute():
    a = day_trades([(3, 0, 1, 100), (3, 30, -1, 101), (4, 0, -1, 80)])
    b = day_trades([(3, 0, 1, 100), (3, 30, -1, 101), (4, 0, 1, 500), (5, 0, 1, 1)])
    ra, rb = D.read_decision(a, T0 + 3 * M, 1), D.read_decision(b, T0 + 3 * M, 1)
    assert ra == rb  # side_bp は始値の後の最初の買い(同じ分の中にある)


def test_read_liq_decision_one_minute_and_second_by_hand():
    dt = day_trades([(2, 40, -1, 100), (2, 50, 1, 101), (3, 0, 1, 102), (3, 5, -1, 99)])
    t0 = T0 + 2 * M + 45 * NS
    r = D.read_liq_decision(dt, t0, -1)
    assert r["sec"]["first_side"] == 1 and r["sec"]["same_side"] is False and r["sec"]["wait_ms"] == 5000.0
    # 窓 [t0, t0 + 60 秒) = 101(2 分 50 秒)・102(3 分 0 秒)・99(3 分 5 秒)。高値 102 が先(清算の前の 100 は入れない)
    assert r["sec"]["hl_order"] == "up" and r["sec"]["dir_first"] is False
    # 「秒」の side_bp: 始値 101(買い)の後で売りの最初の約定 99 → −1 × (99 − 101) ÷ 101 × 1e4
    assert r["sec"]["side_bp"] == pytest.approx(-1 * (99 - 101) / 101 * 1e4)
    assert r["one_min"]["first_side"] == 1 and r["one_min"]["hl_order"] == "up" and r["one_min"]["dir_first"] is False
    assert r["sec"]["window_truncated"] is False


def test_liq_second_order_uses_a_fixed_60_second_window_from_t0():
    """「秒」の高値と安値の順は、時刻 [t0, t0 + 60 秒) の約定だけ(清算の前の約定と 60 秒の後の約定は入れない。分の終わりで切らない)。"""
    # 清算の前: 90(2 分 10 秒)・120(2 分 20 秒)。t0 = 2 分 30 秒。窓の中: 100・110(2 分 40 秒)・95(2 分 50 秒)・130(3 分 20 秒)。
    # 窓の後: 50(3 分 40 秒)
    dt = day_trades([(2, 10, -1, 90), (2, 20, 1, 120), (2, 35, 1, 100), (2, 40, 1, 110), (2, 50, -1, 95), (3, 20, 1, 130),
                     (3, 40, -1, 50)])
    t0 = T0 + 2 * M + 30 * NS
    assert dt.hl_order(T0 + 2 * M) == "down"  # 分 2 の全体なら 90 が先
    r = D.read_liq_decision(dt, t0, 1)
    assert r["sec"]["hl_order"] == "down" and r["sec"]["dir_first"] is False  # 安値 95(2 分 50 秒)が高値 130(3 分 20 秒)より先
    dt2 = day_trades([(2, 35, 1, 100), (2, 40, 1, 110), (2, 50, -1, 95), (3, 20, 1, 130)])
    assert D.read_liq_decision(dt2, t0, 1)["sec"]["hl_order"] == "down"  # 窓の外の行を消しても同じ
    assert r["sec"]["first_side"] == 1 and r["sec"]["wait_ms"] == 5000.0


# ---------------------------------------------------------------- 区間
DL = ["d1", "d2", "d3", "d4", "d5", "d6"]


def test_ratio_stats_day_block_wilson_and_points_by_hand():
    vb = {"d1": [True, False], "d2": [True, True, False, False], "d3": [True, True, True, False], "d4": [],
          "d5": [True] * 5 + [False] * 5, "d6": [True]}
    a = R.ratio_stats(vb, DL)
    assert (a["k"], a["n"]) == (12, 21) and a["ratio"] == pytest.approx(12 / 21)
    assert a["minus_half"] == pytest.approx(12 / 21 - 0.5)
    assert a["per_day"] == [[1, 2, 0.5], [2, 4, 0.5], [3, 4, 0.75], [0, 0, None], [5, 10, 0.5], [1, 1, 1.0]]
    z, n, p = 1.959963984540054, 21, 12 / 21  # Wilson の 95% を手で
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    assert a["wilson"] == pytest.approx([c - h, c + h])
    assert a["first_half"] == pytest.approx(6 / 10) and a["second_half"] == pytest.approx(6 / 11)
    b = a["day_block"]
    assert b["n_blocks"] == 5 and b["ci"][0] <= 12 / 21 <= b["ci"][1] and b["mde"] == pytest.approx(2.8 * b["se"])
    assert R.ratio_stats(vb, DL) == a  # 種で決まる
    assert R.ratio_stats({}, DL)["wilson"] is None and R.ratio_stats({}, DL)["day_block"]["ci"] is None


def test_day_block_draws_whole_days_by_hand():
    """日を 1 塊: 日の中の値が全部同じなら、区間の端は日の平均の最小・最大の範囲の中。"""
    vb = {"d1": [1.0, 1.0], "d2": [3.0], "d3": [], "d4": [], "d5": [], "d6": []}
    m = R.mean_stats(vb, DL)
    assert m["mean"] == pytest.approx(5 / 3) and m["per_day"][0] == [2, 1.0] and m["per_day"][2] == [0, None]
    assert 1.0 <= m["day_block"]["ci"][0] <= m["day_block"]["ci"][1] <= 3.0 and m["day_block"]["n_blocks"] == 2
    assert R.mean_stats(vb, DL)["day_block"] == m["day_block"]
    q = R.quantiles([1.0, 2.0, 3.0, 4.0, 5.0])
    assert (q["n"], q["p0"], q["p50"], q["p100"], q["p25"]) == (5, 1.0, 3.0, 5.0, 2.0)


# ---------------------------------------------------------------- カード 4
@pytest.mark.parametrize("kw", [{}, {"exit_form": "center", "entry": 4, "exit_setting": 3}])
def test_watch_mode_gives_the_same_trades_as_the_simulator(kw):
    """watch はシミュレーターと同じ取引・同じ決まらない足の数(既定の形と、本走らせの形の利確・入り)。
    比の門の rolling は 180 日の履歴が要るので、400 本の足では効かない(ここでは確かめていない)。"""
    rnd = random.Random(11)
    px, bars, paths = P, [], {}
    for i in range(400):
        o = px
        c = o + rnd.choice([-1, 1]) * rnd.randint(0, 400)
        h, lo = max(o, c) + rnd.randint(0, 300), min(o, c) - rnd.randint(0, 300)
        bars.append(bar(i, o, c, h, lo))
        if i % 3 == 0:
            paths[T0 + i * M] = [o, h, lo, c] if rnd.random() < 0.5 else [o, lo, h, c]
        px = c
    for side in ("good", "bad"):
        a = MatildaLimitSim(fill_side=side, **kw)
        w = TradePathMatilda(trade_paths=paths, mode="watch", fill_side=side, **kw)
        ra = [r for b in bars for r in a.feed(b)] + a.finish()
        rw = [r for b in bars for r in w.feed(b)] + w.finish()
        assert ra == rw and a.undecided_bars == w.undecided_bars
        assert len(w.compare) > 0


B40 = (P + 400, P + 300, P + 501, P + 300)  # 始値・終値・高値・安値。売り(S1 = P+500)と利確(P+340)が同じ足に入る


@pytest.mark.parametrize("zz,want_tp", [([P + 400, P + 501, P + 300], True), ([P + 400, P + 300, P + 501], False)])
def test_replay_follows_the_trade_path(zz, want_tp):
    """上が先の約定の道 → 1 分足の良い側(上が先の道)と同じ取引。下が先 → 利確は起きず売りを持ったまま(悪い側と同じ持ち高)。"""
    b40 = bar(40, B40[0], B40[1], B40[2], B40[3])
    for side in ("good", "bad"):
        s = TradePathMatilda(trade_paths={T0 + 40 * M: zz}, mode="replay", fill_side=side)
        rows = [r for b in base() + [b40] for r in s.feed(b)]
        if want_tp:
            assert [(r["entry_price"], r["exit_price"], r["exit_reason"], r["undecided"]) for r in rows] == [
                (P + 500, P + 340, "利確1", 0)]
        else:
            assert rows == [] and s._side == -1 and s._fills == [P + 500]
        assert s.undecided_bars == 0 and s.replayed_bars == 1


def test_replay_with_one_turn_equals_simulator_path_bit_for_bit():
    """折り返しが 1 回の約定の道(始値 → 高値 → 安値)は、シミュレーターの上が先の道と同じ状態になる。"""
    b40 = bar(40, B40[0], B40[1], B40[2], B40[3])
    s = TradePathMatilda(trade_paths={}, mode="watch", fill_side="good")
    for b in base():
        s.feed(b)
    st0, q = s._state(), s._q
    ev, pb = 0, None
    o, h, lo = B40[0], B40[2], B40[3]
    a = s._run_path(st0, True, (o, h, lo, T0 + 40 * M, T0 + 41 * M), q, ev, pb, False)
    t = s._true_path(st0, [o, h, lo], q, ev, pb, T0 + 40 * M, T0 + 41 * M)
    assert (a.events, a.side, a.fills, a.brk, a.closed) == (t.events, t.side, t.fills, t.brk, t.closed)
    b = s._run_path(st0, False, (o, h, lo, T0 + 40 * M, T0 + 41 * M), q, ev, pb, False)
    t2 = s._true_path(st0, [o, lo, h], q, ev, pb, T0 + 40 * M, T0 + 41 * M)
    assert (b.events, b.side, b.fills, b.brk, b.closed) == (t2.events, t2.side, t2.fills, t2.brk, t2.closed)


@pytest.mark.parametrize("zz,good_eq,bad_eq", [([P + 400, P + 501, P + 300], True, False),
                                               ([P + 400, P + 300, P + 501], False, True)])
def test_watch_compare_by_hand(zz, good_eq, bad_eq):
    b40 = bar(40, B40[0], B40[1], B40[2], B40[3])
    out = {}
    for side in ("good", "bad"):
        w = TradePathMatilda(trade_paths={T0 + 40 * M: zz}, mode="watch", fill_side=side)
        for b in base() + [b40]:
            w.feed(b)
        assert len(w.compare) == 1
        out[side] = w.compare[0]
    assert out["good"]["kind"] == "one_tp" and out["good"]["eq_chosen"] is good_eq
    assert out["good"]["eq_other"] is (not good_eq)
    assert out["bad"]["eq_chosen"] is bad_eq and out["bad"]["tp_chosen"] is False
    assert out["good"]["tp_true"] is good_eq
    # 道の損益の差: 約定の道と選んだ道が同じなら 0
    assert (out["good"]["value_true_minus_chosen_bp"] == 0) is good_eq


def test_replay_does_not_use_later_minutes():
    """分 k の約定の道の結果は、分 k+1 の約定の道・足を変えても変わらない(足 k まで流した取引の行が同じ)。"""
    b40 = bar(40, B40[0], B40[1], B40[2], B40[3])
    zz = [P + 400, P + 501, P + 300]
    rows = []
    for later in ([P + 300, P + 900], [P + 300, P - 900]):
        s = TradePathMatilda(trade_paths={T0 + 40 * M: zz, T0 + 41 * M: later}, mode="replay", fill_side="good")
        r40 = [r for b in base() + [b40] for r in s.feed(b)]
        s.feed(bar(41, later[0], later[-1]))
        rows.append(r40)
    assert rows[0] == rows[1]


# ---------------------------------------------------------------- カード 3 の慣らし
def test_card3_exposure_after_one_window_equals_a_longer_run():
    """カード 3 は窓が 1 回過ぎた後は、始めの位置によらず同じ持ち高(慣らし 8 日の根拠)。1 時間の窓で、始めを 90 分ずらす。"""
    from bot.bt.data.reference import reference_series
    from bot.research.cards.library.c3_yen_premium_revert import FX, OVERSEAS
    from bot.research.cards.run import run_card
    decl = D.card_decl("c3_yen_premium_revert")
    rnd = random.Random(5)
    n = 300
    bfp = [5_000_000 + rnd.randint(-3000, 3000) for _ in range(n)]
    bars = [bar(i, bfp[i], bfp[i]) for i in range(n)]
    ov = [(T0 + i * M, 35_000.0 + rnd.uniform(-20, 20)) for i in range(n)]
    fx = [(T0 + i * M, 143.0 + rnd.uniform(-0.05, 0.05)) for i in range(n)]

    def run(k):
        refs = {OVERSEAS: reference_series(OVERSEAS, ov[k:], declarations=decl),
                FX: reference_series(FX, fx[k:], declarations=decl)}
        r = run_card(D.make_card("c3_yen_premium_revert", "1h"), bars[k:], references=refs, declarations=decl,
                     venue="bitflyer", symbol="FX_BTC_JPY")
        return {int(t): e for t, e, dd in zip(r.end_ns, r.exposure, r.decided) if dd}
    a, b = run(0), run(90)
    later = [t for t in b if t >= T0 + (90 + 61) * M]
    assert later and all(a[t] == b[t] for t in later)
    assert any(a[t] != 0 for t in later)


# ---------------------------------------------------------------- 批評家 1 回目の M3・M4
def test_head_leg_when_open_is_already_beyond_the_entry_price():
    """始値 P+600 が S1(P+500)を越えている足: シミュレーターは足の頭で S1 に売る。約定の道 [P+600, P+550] でも同じ(批評家の M3:
    足の頭の脚を消す誤りを捕まえる)。"""
    b40 = bar(40, P + 600, P + 550, h=P + 600, lo=P + 550)
    plain = MatildaLimitSim(fill_side="good")
    rep = TradePathMatilda(trade_paths={T0 + 40 * M: [P + 600, P + 550]}, mode="replay", fill_side="good")
    for b in base() + [b40]:
        plain.feed(b)
        rep.feed(b)
    assert plain._side == -1 and plain._fills == [P + 500]
    assert (rep._side, rep._fills) == (plain._side, plain._fills) and rep.replayed_bars == 1


def _both_tp_bars():
    """番号 40 で売り 2 段(P+500・P+700)。番号 41 で、上が先 = 段を 1 つ足してから 3 段の利確、下が先 = 2 段のまま利確
    (両方の道で利確 = both_tp。良い側 = 損益の良い道 = 下が先、悪い側 = 上が先)。"""
    b40 = bar(40, P + 600, P + 600, h=P + 701, lo=P + 600)
    s = MatildaLimitSim(fill_side="good")
    for b in base() + [b40]:
        s.feed(b)
    q = s._q
    tp = (P + 600) - 0.8 * q.vola / 2
    nxt = math.floor(max(q.s1, P + 700 + q.vola))
    return b40, bar(41, P + 650, P + 650, h=nxt + 1, lo=tp - 1), nxt + 1, tp - 1


def test_both_tp_compare_picks_the_right_chosen_and_other_by_hand():
    """both_tp の足で、約定の道 = 上が先。良い側は下が先を選ぶので「もう一方と同じ」、悪い側は上が先を選ぶので「選んだ道と同じ」
    (批評家の M4: 選んだ道ともう一方の道の入れ替えを捕まえる)。"""
    b40, b41, hi, lo = _both_tp_bars()
    out = {}
    for side in ("good", "bad"):
        w = TradePathMatilda(trade_paths={T0 + 41 * M: [P + 650, hi, lo]}, mode="watch", fill_side=side)
        for b in base() + [b40, b41]:
            w.feed(b)
        assert [c["kind"] for c in w.compare] == ["both_tp"]
        out[side] = w.compare[0]
    assert out["good"]["path"] == "down" and out["good"]["eq_chosen"] is False and out["good"]["eq_other"] is True
    assert out["bad"]["path"] == "up" and out["bad"]["eq_chosen"] is True and out["bad"]["eq_other"] is False
    assert out["good"]["value_true_minus_chosen_bp"] < 0 == out["bad"]["value_true_minus_chosen_bp"]


# ---------------------------------------------------------------- カード 5・8・3(1 週)の慣らし
def _exposures(card, bars, refs=None, decl=None):
    from bot.research.cards.run import run_card
    r = run_card(card, bars, references=refs or {}, declarations=decl or {}, venue="bitflyer", symbol="FX_BTC_JPY")
    return {int(t): e for t, e, dd in zip(r.end_ns, r.exposure, r.decided) if dd}


def _walk(n, seed, step_min=1):
    rnd = random.Random(seed)
    out, px = [], 5_000_000.0
    for i in range(n):
        o = px
        c = o + rnd.randint(-3000, 3000)
        s0 = T0 + i * step_min * M
        out.append(BarEvent(received_time_ns=s0 + M, exchange_time_ns=s0 + M, start_time_ns=s0, open=o, high=max(o, c),
                            low=min(o, c), close=c, volume=1.0))
        px = c
    return out


def test_card5_exposure_after_the_jst_day_start_does_not_depend_on_the_start():
    """カード 5: 日本時間の 0 時(15:00 UTC)より前から流せば、その日の持ち高は始めの位置によらない(慣らし 1 日の根拠)。
    2024-01-01 00:00 UTC から 2 日分。始めを 10 時間ずらす。比べるのは 2024-01-01 15:00 UTC(日本時間 1 月 2 日(火)0 時)以後。"""
    bars = _walk(2 * 1440, 1)
    a = _exposures(D.make_card("c5_tokyo_fix_momentum", None), bars)
    b = _exposures(D.make_card("c5_tokyo_fix_momentum", None), bars[600:])
    later = [t for t in b if t > T0 + 15 * 60 * M]
    assert later and all(a[t] == b[t] for t in later) and any(a[t] != 0 for t in later)


@pytest.mark.parametrize("session,start_h", [("jst_day", 15), ("bf_maint", 19)])
def test_card8_exposure_after_the_session_start_does_not_depend_on_the_start(session, start_h):
    """カード 8: セッションの始まり(jst_day 15:00 UTC・bf_maint 19:00 UTC)より前から流せば、その後の持ち高は始めの位置によらない。"""
    bars = _walk(2 * 1440, 2)
    a = _exposures(D.make_card("c8_session_mean_revert", session), bars)
    b = _exposures(D.make_card("c8_session_mean_revert", session), bars[300:])
    later = [t for t in b if t > T0 + start_h * 60 * M]
    assert later and all(a[t] == b[t] for t in later) and any(a[t] != 0 for t in later)


def test_card3_1w_exposure_after_one_window_equals_a_longer_run():
    """カード 3 の 1 週の窓: 窓が 1 回過ぎた後は、始めの位置によらず同じ持ち高(慣らし 8 日の根拠)。足は 10 分ごと(1 分足を 10 分
    おきに置く)で 9 日。始めを 1 日ずらし、比べるのは遅い方の始め + 1 週 + 1 分より後。"""
    from bot.bt.data.reference import reference_series
    from bot.research.cards.library.c3_yen_premium_revert import FX, OVERSEAS
    decl = D.card_decl("c3_yen_premium_revert")
    rnd = random.Random(9)
    n = 9 * 144
    bars = _walk(n, 3, step_min=10)
    ov = [(int(b.start_time_ns), 35_000.0 + rnd.uniform(-20, 20)) for b in bars]
    fx = [(int(b.start_time_ns), 143.0 + rnd.uniform(-0.05, 0.05)) for b in bars]

    def run(k):
        refs = {OVERSEAS: reference_series(OVERSEAS, ov[k:], declarations=decl),
                FX: reference_series(FX, fx[k:], declarations=decl)}
        return _exposures(D.make_card("c3_yen_premium_revert", "1w"), bars[k:], refs, decl)
    a, b = run(0), run(144)
    later = [t for t in b if t >= int(bars[144].start_time_ns) + 7 * 1440 * M + M]
    assert later and all(a[t] == b[t] for t in later) and any(a[t] != 0 for t in later)


# ---------------------------------------------------------------- 批評家 2 回目: 割合 B・side_tables の数
def test_c4_ratio_b_excludes_bars_equal_to_both_paths_by_hand():
    """割合 A = 選んだ道と同じ(両方と同じを含む)÷ 全部、割合 B = 選んだ道とだけ ÷(選んだ道とだけ + もう一方とだけ)。
    両方と同じ足は B に入れない(批評家 2 回目の写し m3: `!=` を `or` にする誤りを捕まえる)。"""
    day_ns = {d: T0 + i * 86_400 * NS for i, d in enumerate(DL)}

    def row(day, ch, ot):
        return {"start_ns": day_ns[day] + 5 * M, "eq_chosen": ch, "eq_other": ot}
    rows = [row("d1", True, False), row("d1", False, True), row("d1", True, True), row("d1", False, False),
            row("d1", True, False), row("d2", True, True), row("d2", False, True)]
    r = R.c4_ratios(rows, day_ns, DL)
    assert (r["eq_chosen"]["k"], r["eq_chosen"]["n"]) == (4, 7)  # 選んだ道とだけ 2 + 両方 2
    assert (r["chosen_vs_other"]["k"], r["chosen_vs_other"]["n"]) == (2, 4)  # 選んだ道とだけ 2 ÷(2 + もう一方とだけ 2)
    assert r["chosen_vs_other"]["per_day"][:2] == [[2, 3, 2 / 3], [0, 1, 0.0]]


def _liq_row(side_bp, side_wait_ms, wait_ms, trunc=False):
    return {"first_side": 1, "same_side": True, "hl_order": "up", "dir_first": True, "side_bp": side_bp,
            "side_wait_ms": side_wait_ms, "wait_ms": wait_ms, "window_truncated": trunc}


def test_side_tables_missing_counts_wait_quantiles_and_wait_bands_by_hand():
    one = {"first_side": None, "same_side": None, "hl_order": None, "dir_first": None, "side_bp": None, "side_wait_ms": None}
    c9 = {d: {"rows": []} for d in DL}
    c9["d1"]["rows"] = [{"sec": _liq_row(1.0, 500.0, 100.0), "one_min": one},
                        {"sec": _liq_row(None, None, 300.0, trunc=True), "one_min": one},
                        {"sec": _liq_row(3.0, 5000.0, 200.0), "one_min": one}]
    c9["d2"]["rows"] = [{"sec": _liq_row(-2.0, 20000.0, 400.0), "one_min": one}]
    c3 = {d: {"rows": []} for d in DL}
    c3["d1"]["rows"] = [dict(_liq_row(2.0, 0.0, None), kind="flip"), dict(_liq_row(None, None, None), kind="resize")]
    t = R.side_tables({"c3_1h": c3, "c9": c9}, DL)
    sec = t["c9"]["sec"]
    assert sec["side_bp_missing"] == 1 and t["c9"]["one_min"]["side_bp_missing"] == 4  # 「1 分」は約定の無い分も欠けに入る
    assert sec["window_truncated"] == 1
    assert sec["wait_ms"]["all"]["n"] == 4 and sec["wait_ms"]["all"]["p50"] == 250.0 and sec["wait_ms"]["all"]["p100"] == 400.0
    assert sec["wait_ms"]["per_day"]["d2"]["p0"] == 400.0
    bw = sec["side_bp_by_wait"]
    assert (bw["1 秒未満"]["n"], bw["1 秒未満"]["mean"]) == (1, 1.0)
    assert (bw["1〜10 秒"]["n"], bw["1〜10 秒"]["mean"]) == (1, 3.0)
    assert (bw["10 秒以上"]["n"], bw["10 秒以上"]["mean"]) == (1, -2.0)
    assert sec["side_wait_ms"]["n"] == 3 and sec["side_wait_ms"]["p50"] == 5000.0
    assert sec["side_bp"]["mean"] == pytest.approx(2 / 3)
    assert t["c3_1h"]["all"]["side_bp_missing"] == 1 and t["c3_1h"]["flip"]["side_bp_missing"] == 0
    assert t["c3_1h"]["resize"]["side_bp_missing"] == 1 and t["c3_1h"]["flip"]["side_bp_by_wait"]["1 秒未満"]["n"] == 1
