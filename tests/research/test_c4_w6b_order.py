"""マチルダの 1 分足の中の順序の確かめ(W6b。`scripts/w4_measure/c4_w6b_order.py` の O1〜O6)の測り方を、走らせる前に固める。

O3 の順序の決め方は合成の約定で、O4 の数え方は合成の記録で、記録の口(`undecided_log`)が挙動を変えないことは
既存の指紋(`test_matilda_limit_sim.py` の GOLDEN_SIM)との一致で確かめる。数字は試験の入力で、データではない。
"""
from __future__ import annotations

import gzip
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

from bot.research.matilda_limit_sim import MatildaLimitSim

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("test_matilda_limit_sim_for_w6b", REPO / "tests" / "research" / "test_matilda_limit_sim.py")
tm = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = tm
_spec.loader.exec_module(tm)
w = tm._load_w4("c4_w6b_order")

M = 60 * 10**9
U = 60_000_000  # 1 分のマイクロ秒


# ---------------------------------------------------------------- 決まりの写し
def test_docstring_starts_with_the_reading_rules_verbatim():
    """台本の docstring の冒頭 = 委任文「読み方の決まり」の O1〜O6 の 6 行(逐語。変えない・足さない)。"""
    lines = (REPO / "docs/RESEARCH/WINDOW1/DELEGATION_w6b_order.md").read_text(encoding="utf-8").splitlines()
    rules = [x for x in lines if x[:2] in ("O1", "O2", "O3", "O4", "O5", "O6") and x[2] == " "]
    assert len(rules) == 6
    assert w.__doc__.rstrip("\n").split("\n") == rules


# ---------------------------------------------------------------- O3 本当の順序
@pytest.mark.parametrize("trades,want", [
    ([(1, 100), (5, 110), (9, 90)], "up"),            # 最高値が先
    ([(1, 100), (5, 90), (9, 110)], "down"),          # 最安値が先
    ([(1, 100)], "none"),                              # 2 件未満
    ([], "none"),
    ([(7, 110), (7, 90)], "none"),                     # 最高値と最安値が同じ時刻
    ([(1, 100), (5, 100), (9, 100)], "none"),          # 値段が全部同じ = 最高値と最安値が同じ時刻
    ([(9, 110), (1, 100), (5, 90)], "down"),           # 順不同でも時刻で比べる(最高値 9 は最安値 5 より後)
])
def test_o3_minute_order(trades, want):
    assert w.minute_order(trades) == want


def test_o3_first_trade_at_the_extreme_is_the_earliest_time_even_if_listed_later():
    """最高値の約定が 2 つ(時刻 2 と 8)。最安値は時刻 5。最初の約定の時刻は 2 なので上が先。行の順には頼らない。"""
    assert w.minute_order([(8, 110), (5, 90), (2, 110), (1, 100)]) == "up"
    assert w.minute_order([(2, 110), (5, 90), (8, 110)]) == "up"
    # 最高値の最初が 8 のとき、最安値(5)が先
    assert w.minute_order([(8, 110), (5, 90), (9, 110)]) == "down"


def test_o3_minute_order_is_cut_at_utc_minutes(tmp_path, monkeypatch):
    """ファイルを UTC の分に切って集計する。同じ時刻の複数の行(同じ注文の約定)を持つ。"""
    name = w.TRADE_FILES[0]  # 2023-07-01
    d0 = w.day_ns("2023-07-01") // 1000
    rows = [(d0 + 10, 100), (d0 + 20, 120), (d0 + 20, 80),            # 分 0: 最高値 120 と最安値 80 が同じ時刻 → none
            (d0 + U + 1, 100), (d0 + U + 5, 130), (d0 + U + 9, 70),   # 分 1: 上が先
            (d0 + 2 * U + 1, 100), (d0 + 2 * U + 5, 60), (d0 + 2 * U + 9, 140),  # 分 2: 下が先
            (d0 + 3 * U, 100)]                                         # 分 3: 1 件
    os.makedirs(tmp_path / "t")
    with gzip.open(tmp_path / "t" / name, "wt", encoding="utf-8") as fh:
        fh.write("exchange,symbol,timestamp,local_timestamp,id,side,price,amount\n")
        for i, (ts, px) in enumerate(reversed(rows)):  # 順不同で書く
            fh.write(f"bitflyer,FX_BTC_JPY,{ts},{ts},{i},buy,{px},0.01\n")
    monkeypatch.setattr(w, "ROOT", str(tmp_path))
    monkeypatch.setattr(w, "TRADE_DIR", "t")
    m = w.read_trade_minutes(name)
    day = w.day_ns("2023-07-01")
    assert {k: v.order() for k, v in m.items()} == {day: "none", day + M: "up", day + 2 * M: "down", day + 3 * M: "none"}
    assert (m[day + M].n, m[day + M].hi, m[day + M].lo) == (3, 130, 70)


def test_o3_a_row_outside_the_day_is_refused(tmp_path, monkeypatch):
    name = w.TRADE_FILES[0]
    d0 = w.day_ns("2023-07-01") // 1000
    os.makedirs(tmp_path / "t")
    with gzip.open(tmp_path / "t" / name, "wt", encoding="utf-8") as fh:
        fh.write("exchange,symbol,timestamp,local_timestamp,id,side,price,amount\n")
        fh.write(f"bitflyer,FX_BTC_JPY,{d0 + 86_400 * 1_000_000},0,1,buy,100,0.01\n")
    monkeypatch.setattr(w, "ROOT", str(tmp_path))
    monkeypatch.setattr(w, "TRADE_DIR", "t")
    with pytest.raises(SystemExit):
        w.read_trade_minutes(name)


@pytest.mark.parametrize("name", ["FX_BTC_JPY_20240101.csv.gz", "FX_BTC_JPY_20241001.csv.gz", "FX_BTC_JPY_20230702.csv.gz",
                                  "../x.csv.gz"])
def test_only_the_six_pre_seal_days_can_be_opened(name):
    """6 日の表に無い名前(2024 年のファイルなど)は、開く前に拒む。"""
    with pytest.raises(SystemExit):
        w.day_of(name)
    with pytest.raises(SystemExit):
        w.read_trade_minutes(name)
    with pytest.raises(SystemExit):
        w.md5_check(name)
    assert [w.day_of(n) for n in w.TRADE_FILES] == ["2023-07-01", "2023-08-01", "2023-09-01", "2023-10-01", "2023-11-01",
                                                    "2023-12-01"]


# ---------------------------------------------------------------- O4 一致の数え方
def test_wilson_known_values():
    lo, hi = w.wilson(5, 10)
    assert (round(lo, 4), round(hi, 4)) == (0.2366, 0.7634)
    lo, hi = w.wilson(0, 10)
    assert lo == pytest.approx(0.0, abs=1e-12) and round(hi, 4) == 0.2775
    lo, hi = w.wilson(10, 10)
    assert round(lo, 4) == 0.7225 and hi == pytest.approx(1.0, abs=1e-12)
    assert w.wilson(0, 0) is None


def _e(t, path, kind="one_tp"):
    return {"start_ns": t * M, "path": path, "kind": kind}


def test_o4_count_matches_on_a_synthetic_log():
    log = [_e(0, "up"), _e(1, "down"), _e(2, "up"), _e(3, "same", "r2_same_events"), _e(4, "down"), _e(5, "up"), _e(100, "up")]
    truth = {0: "up", 1: "up", 2: "down", 3: "up", 4: "none", 5: "down"}
    truth = {k * M: v for k, v in truth.items()}  # 分 6 は約定の記録に無い。分 100 は範囲の外
    r = w.count_matches(log, truth, lambda ns: ns < 50 * M)
    # 分 0: 上=上 一致 / 分 1: 下≠上 / 分 2: 上≠下 / 分 3: 同じ扱い(照合しない。順序は決まっている)/ 分 4: 順序が決まらない / 分 5: 上≠下
    assert r["undecided"] == 6 and r["same"] == 1
    assert r["truth_decided"] == 5 and (r["truth_up"], r["truth_down"]) == (3, 2)
    assert (r["compared"], r["match"]) == (4, 1) and r["ratio"] == 0.25
    assert r["wilson"] == w.wilson(1, 4)


def test_o4_missing_minute_in_the_trade_record_counts_as_undecided_truth():
    r = w.count_matches([_e(7, "up")], {}, lambda ns: True)
    assert (r["undecided"], r["truth_decided"], r["compared"], r["match"], r["ratio"], r["wilson"]) == (1, 0, 0, 0, None, None)


def test_o4_totals_are_summed_counts_not_averaged_ratios():
    r1 = w.count_matches([_e(0, "up"), _e(1, "up")], {0: "up", M: "up"}, lambda ns: True)
    r2 = w.count_matches([_e(0, "up")], {0: "down"}, lambda ns: True)
    t = w.add_counts([r1, r2])
    assert (t["undecided"], t["compared"], t["match"]) == (3, 3, 2) and t["ratio"] == pytest.approx(2 / 3)
    assert t["wilson"] == w.wilson(2, 3)


def test_o4_by_kind_splits_the_same_log():
    log = [_e(0, "up", "one_tp"), _e(1, "down", "no_tp"), _e(2, "up", "one_tp")]
    truth = {0: "up", M: "down", 2 * M: "down"}
    k = w.by_kind(log, truth, lambda ns: True)
    assert k["one_tp"]["undecided"] == 2 and k["one_tp"]["match"] == 1 and k["no_tp"]["match"] == 1


# ---------------------------------------------------------------- O5 足の食い違い
def test_o5_mismatch_counts():
    def agg(hi, lo):
        m = w.MinuteAgg()
        m.add(1, hi)
        m.add(2, lo)
        return m
    bars = {0: (110.0, 90.0), M: (110.0, 90.0), 2 * M: (110.0, 90.0), 3 * M: (110.0, 90.0), 9 * M: (1.0, 1.0)}
    minutes = {0: agg(110, 90), M: agg(111, 90), 2 * M: agg(110, 89), 3 * M: agg(112, 88), 8 * M: agg(5, 4)}
    r = w.count_mismatch(bars, minutes, lambda ns: True)
    assert r == {"both": 4, "hi_diff": 2, "lo_diff": 2, "any_diff": 3, "bars_only": 1, "trades_only": 1}
    log = [_e(0, "up"), _e(1, "up"), _e(5, "up")]  # 分 5 はどちらにも無い
    assert w.mismatch_in_undecided(log, bars, minutes, lambda ns: True) == {"undecided": 3, "both": 2, "any_diff": 1}


# ---------------------------------------------------------------- 記録の口(O2)
def _logged(side, bars_after, patch=None):
    log = []
    s = MatildaLimitSim(fill_side=side, undecided_log=log)
    tm.feed(s, tm.base())
    if patch:
        patch(s)
    for b in bars_after:
        s.feed(b)
    return s, log


def test_log_one_tp_good_takes_the_tp_path_bad_logs_the_stopped_paths_direction():
    """売りの入り(S1 = P+500)と利確(P+340)が同じ足。上が先の道でだけ利確 → 良い側は「上が先」、悪い側は利確の手前で
    止めた下が先の道(止めた道の向き)。"""
    b40 = tm.bar(40, tm.P + 400, tm.P + 300, h=tm.P + 501, lo=tm.P + 300)
    t = b40.start_time_ns
    _, lg = _logged("good", [b40])
    _, lb = _logged("bad", [b40])
    assert lg == [{"start_ns": t, "path": "up", "kind": "one_tp"}]
    assert lb == [{"start_ns": t, "path": "down", "kind": "one_tp"}]


def test_log_no_tp_uses_the_path_to_the_nearer_extreme_for_both_sides():
    b40 = tm.bar(40, tm.P + 400, tm.P + 400, h=tm.P + 501, lo=tm.P - 301)  # 始値は高値に近い → 上が先

    def patch(s):
        s._tp = lambda st, q, t: (tm.P + st.side * 10 ** 6, "利確1")
    for side in ("good", "bad"):
        _, lg = _logged(side, [b40], patch)
        assert lg == [{"start_ns": b40.start_time_ns, "path": "up", "kind": "no_tp"}]


@pytest.mark.parametrize("side", ["good", "bad"])
def test_log_same_when_both_paths_have_the_same_events(side):
    """反対の入りで閉じた後の分かれ目。2 本の道の出来事が同じなので道が分かれない(path = same)。"""
    log = []
    s = MatildaLimitSim(fill_side=side, undecided_log=log)
    tm.feed(s, tm.base() + [tm.bar(40, tm.P - 250, tm.P - 250, h=tm.P - 250, lo=tm.P - 300.5)])
    q = s._q
    s._tp = lambda st, q, t: (tm.P + 10 ** 6, "利確1")
    s.feed(tm.bar(41, q.s1 - 10, q.s1 + 5, h=q.s1 + 5, lo=q.s1 - 10))
    assert [(e["path"], e["kind"]) for e in log] == [("same", "r2_same_events")]


def test_log_both_tp_path_is_the_better_path_for_good_and_the_worse_for_bad():
    """段の追加(上)と利確(下)が同じ足で、両方の道で利確(test_8_add_and_take_profit_in_one_bar と同じ足)。"""
    import math
    paths = {}
    for side in ("good", "bad"):
        log = []
        s = MatildaLimitSim(fill_side=side, undecided_log=log)
        tm.feed(s, tm.base() + [tm.bar(40, tm.P + 600, tm.P + 600, h=tm.P + 701, lo=tm.P + 600)])
        q = s._q
        tp = (tm.P + 600) - 0.8 * q.vola / 2
        nxt = math.floor(max(q.s1, tm.P + 700 + q.vola))
        rows = s.feed(tm.bar(41, tm.P + 650, tm.P + 650, h=nxt + 1, lo=tp - 1))
        assert rows[0]["undecided"] == 1
        paths[side] = [(e["path"], e["kind"]) for e in log if e["start_ns"] == tm.T0 + 41 * M]
    assert paths["good"][0][1] == paths["bad"][0][1] == "both_tp"
    assert {paths["good"][0][0], paths["bad"][0][0]} <= {"up", "down"}
    assert paths["good"][0][0] != paths["bad"][0][0]  # 損益の良い方の道と悪い方の道は別の道


# ---------------------------------------------------------------- 記録の口が挙動を変えないこと
@pytest.mark.parametrize("name,kw", tm.GOLDEN_CONFIGS)
def test_undecided_log_does_not_change_default_fingerprint(name, kw):
    """記録を取っても、取引の行と決まらない足の数は、既存の指紋(GOLDEN_SIM)と同じ。記録の件数 = 決まらない足の数。"""
    import hashlib
    bars = tm._golden_bars()
    log = []
    s = MatildaLimitSim(**{**kw, "undecided_log": log})
    rows = tm.feed(s, bars) + s.finish()
    assert hashlib.sha256(repr((rows, s.undecided_bars)).encode()).hexdigest() == tm.GOLDEN_SIM[name]
    assert len(log) == s.undecided_bars > 0
    assert all(e["path"] in ("up", "down", "same") for e in log)
    assert tm._golden_rows_digest(kw) == tm.GOLDEN_SIM[name]  # 口を渡さない呼び方(既定)も同じ


def test_undecided_log_does_not_change_the_rolling_center_form_either():
    """この台本の形(rolling × 中心 4:3)でも、記録の有る無しで取引の行・決まらない足の数・日ごとの境が同じ。"""
    bars = tm._golden_bars()
    for side in ("good", "bad"):
        kw = {"fill_side": side, "ratio_gate_mode": "rolling", "exit_form": "center", "entry": 4, "exit_setting": 3}
        a, la = MatildaLimitSim(**kw), []
        b = MatildaLimitSim(undecided_log=la, **kw)
        ra, rb = tm.feed(a, bars) + a.finish(), tm.feed(b, bars) + b.finish()
        assert ra == rb and a.undecided_bars == b.undecided_bars == len(la)
        assert a.rolling_edges == b.rolling_edges


# ---------------------------------------------------------------- --window(窓の 10 日。合成の置き場だけ。窓のデータは開かない)
CM = sys.modules["_w4measure__common"]  # w が読み込んだ common(名前 common で引き直さない。tm._load_w4 の注)
assert w.load_bars.__globals__ is CM.__dict__


def test_window_table_is_the_ten_2024_days_and_refuses_other_names():
    """--window の日の一覧は 2024 年の 1〜10 月の各 1 日の 10 日。表に無い名前(2025 年・2023 年・別の日・パスの細工)は拒む。"""
    t = w.TRADE_FILES_WINDOW
    assert [w.day_of(n, t) for n in t] == ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01",
                                           "2024-06-01", "2024-07-01", "2024-08-01", "2024-09-01", "2024-10-01"]
    for name in ("FX_BTC_JPY_20250101.csv.gz", "FX_BTC_JPY_20251001.csv.gz", "FX_BTC_JPY_20230701.csv.gz",
                 "FX_BTC_JPY_20240102.csv.gz", "FX_BTC_JPY_20241101.csv.gz", "../x.csv.gz"):
        with pytest.raises(SystemExit):
            w.day_of(name, t)
        with pytest.raises(SystemExit):
            w.read_trade_minutes(name, t)
        with pytest.raises(SystemExit):
            w.md5_check(name, t)
    # 既定(--window なし)は今までと同じ 6 日だけ。窓の 10 日の名前は拒む
    assert w.TRADE_FILES == tuple(f"FX_BTC_JPY_2023{md}.csv.gz" for md in ("0701", "0801", "0901", "1001", "1101", "1201"))
    for name in t:
        with pytest.raises(SystemExit):
            w.day_of(name)


def _synthetic_root(tmp_path, monkeypatch, env=False, approval=False):
    """偽の置き場(本物の backtest_data/phase2_sealed/P2-08/ は使わない)。w と common の ROOT を差し替える。"""
    r = tmp_path / "root"
    (r / "backtest_data" / "phase2_sealed" / "P2-08").mkdir(parents=True)
    monkeypatch.setattr(CM, "ROOT", str(r))
    monkeypatch.setattr(w, "ROOT", str(r))
    monkeypatch.setitem(sys.modules, "common", CM)  # 台本の中の遅い `from common import` があっても CM を読む
    monkeypatch.delenv(CM.WINDOW1_ENV, raising=False)
    if env:
        monkeypatch.setenv(CM.WINDOW1_ENV, CM.WINDOW1_ENV_VALUE)
    if approval:
        (r / CM.WINDOW1_APPROVAL).write_text("test approval (合成)\n", encoding="utf-8")
    return r


class _Opened(Exception):
    pass


@pytest.mark.parametrize("env,approval", [(False, False), (True, False), (False, True)])
def test_window_refuses_before_opening_any_trade_file_when_a_door_is_missing(tmp_path, monkeypatch, env, approval):
    r = _synthetic_root(tmp_path, monkeypatch, env=env, approval=approval)

    def boom(*a, **k):
        raise _Opened("門より先に約定の記録または足を開いた")
    for fn in ("read_trade_minutes", "md5_check", "load_bars"):
        monkeypatch.setattr(w, fn, boom)
    monkeypatch.setattr(w.gzip, "open", boom)
    with pytest.raises(SystemExit) as e:
        w.main(["--window", "--out", str(tmp_path / "out")])
    assert "探索の窓の口" in str(e.value)
    assert not (r / CM.WINDOW1_LOG).exists()      # 門が欠ければ記録にも書かない
    assert not (tmp_path / "out").exists()


def test_window_guard_is_called_once_with_the_ten_day_range_before_the_first_trade_file(tmp_path, monkeypatch):
    """門が揃うと、約定の記録を開く前に記録へ 1 行(10 日の範囲)。その直後の最初のファイルを開くところで止める(窓のデータは開かない)。"""
    r = _synthetic_root(tmp_path, monkeypatch, env=True, approval=True)
    seen = []

    def stop(name, table=None):
        seen.append((name, table))
        raise _Opened(name)
    monkeypatch.setattr(w, "read_trade_minutes", stop)
    with pytest.raises(_Opened):
        w.main(["--window", "--out", str(tmp_path / "out")])
    assert seen == [("FX_BTC_JPY_20240101.csv.gz", w.TRADE_FILES_WINDOW)]
    lines = [json.loads(x) for x in (r / CM.WINDOW1_LOG).read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 1
    assert (lines[0]["lo"], lines[0]["hi"], lines[0]["script"]) == ("2024-01-01T00:00:00Z", "2024-10-02T00:00:00Z",
                                                                  "c4_w6b_order.py")


def test_default_run_does_not_touch_the_window_door(tmp_path, monkeypatch):
    """--window なしは窓の口を呼ばない(門が欠けていても、記録は書かれず、6 日の表で進む)。"""
    r = _synthetic_root(tmp_path, monkeypatch)
    seen = []

    def stop(name, table=None):
        seen.append((name, table))
        raise _Opened(name)
    monkeypatch.setattr(w, "read_trade_minutes", stop)
    with pytest.raises(_Opened):
        w.main(["--out", str(tmp_path / "out")])
    assert seen == [("FX_BTC_JPY_20230701.csv.gz", w.TRADE_FILES)]
    assert not (r / CM.WINDOW1_LOG).exists()


# ---------------------------------------------------------------- 前後の小計
def test_period_split_is_by_the_product_switch_day():
    assert [w.period_of(d) for d in ("2024-01-01", "2024-03-01", "2024-03-27", "2024-03-28", "2024-04-01", "2024-10-01")] == [
        "before", "before", "before", "after", "after", "after"]
    days = [w.day_of(n, w.TRADE_FILES_WINDOW) for n in w.TRADE_FILES_WINDOW]
    assert [w.period_of(d) for d in days] == ["before"] * 3 + ["after"] * 7


def test_subtotals_are_summed_counts_per_period_not_averaged_ratios():
    """合成の記録。前 = 1〜3 月の 3 日、後 = 4〜10 月の 7 日。割合と区間は小計の数から作り直す。"""
    days = [w.day_of(n, w.TRADE_FILES_WINDOW) for n in w.TRADE_FILES_WINDOW]
    by_day = {}
    for i, d in enumerate(days):
        if i == 0:      # 前の 1 日目: 2 件とも一致
            log, truth = [_e(0, "up"), _e(1, "up")], {0: "up", M: "up"}
        elif i == 1:    # 前の 2 日目: 1 件、不一致(下 ≠ 上)
            log, truth = [_e(0, "down")], {0: "up"}
        elif i == 2:    # 前の 3 日目: 同じ扱い 1 件 + 順序が決まらない 1 件
            log, truth = [_e(0, "same", "r2_same_events"), _e(1, "up")], {0: "up", M: "none"}
        elif i == 3:    # 後の 1 日目: 3 件一致
            log, truth = [_e(0, "down"), _e(1, "down"), _e(2, "up")], {0: "down", M: "down", 2 * M: "up"}
        else:           # 後の残りの日: 記録なし
            log, truth = [], {}
        by_day[d] = w.count_matches(log, truth, lambda ns: True)
    st = w.subtotals(by_day, days)
    b, a = st["before"], st["after"]
    assert (b["undecided"], b["same"], b["truth_decided"], b["compared"], b["match"]) == (5, 1, 4, 3, 2)
    assert b["ratio"] == pytest.approx(2 / 3) and b["wilson"] == w.wilson(2, 3)
    assert (a["undecided"], a["same"], a["truth_decided"], a["compared"], a["match"]) == (3, 0, 3, 3, 3)
    assert a["ratio"] == 1.0 and a["wilson"] == w.wilson(3, 3)
    # 前後の小計の合計 = 10 日の合計(O4 の数え方は同じ)
    assert w.add_counts([b, a]) == w.add_counts(list(by_day.values()))


def test_mismatch_subtotals_are_summed_per_period():
    days = [w.day_of(n, w.TRADE_FILES_WINDOW) for n in w.TRADE_FILES_WINDOW]
    base = {"both": 0, "hi_diff": 0, "lo_diff": 0, "any_diff": 0, "bars_only": 0, "trades_only": 0}
    mm = {d: dict(base) for d in days}
    mm[days[0]].update(both=10, hi_diff=1, any_diff=1)
    mm[days[2]].update(both=5, lo_diff=2, any_diff=2, trades_only=1)
    mm[days[9]].update(both=7, hi_diff=3, lo_diff=1, any_diff=3, bars_only=2)
    st = w.mismatch_subtotals(mm, days)
    assert st["before"] == {"both": 15, "hi_diff": 1, "lo_diff": 2, "any_diff": 3, "bars_only": 0, "trades_only": 1}
    assert st["after"] == {"both": 7, "hi_diff": 3, "lo_diff": 1, "any_diff": 3, "bars_only": 2, "trades_only": 0}


def test_render_window_has_subtotals_and_default_render_has_none():
    """表の形: 窓の版だけが前後の小計の行と補足を持つ。既定の版の文面に窓の語は入らない。"""
    def counts(k):
        return {"undecided": k, "same": 0, "truth_decided": k, "truth_up": k, "truth_down": 0, "compared": k, "match": k,
                "ratio": 1.0 if k else None, "wilson": w.wilson(k, k)}
    mm0 = {"both": 1, "hi_diff": 0, "lo_diff": 0, "any_diff": 0, "bars_only": 0, "trades_only": 0}

    def res_for(days, window):
        r = {"days": days, "bars_range": ["a", "b"], "bars_loaded": 1, "bar_anomalies": {}, "bar_files": {}, "sim_kw": w.SIM_KW,
             "trade_files": {d: {"file": "f", "md5": {"match": True}, "rows": 1, "minutes": 1} for d in days},
             "gate": {s: {d: True for d in days} for s in w.SIDES}, "sides": {},
             "mismatch": {"by_day": {d: dict(mm0) for d in days}, "total": dict(mm0)}}
        for s in w.SIDES:
            r["sides"][s] = {"by_day": {d: counts(1) for d in days}, "total": counts(len(days)), "by_kind": {"one_tp": counts(1)},
                             "mismatch_undecided": {"undecided": 1, "both": 1, "any_diff": 0}, "undecided_bars_all": 1,
                             "log_len_all": 1}
        if window:
            r["window"] = True
            for s in w.SIDES:
                r["sides"][s]["subtotals"] = {"before": counts(3), "after": counts(7)}
            r["mismatch"]["subtotals"] = {"before": dict(mm0), "after": dict(mm0)}
        return r
    wdays = [w.day_of(n, w.TRADE_FILES_WINDOW) for n in w.TRADE_FILES_WINDOW]
    t_win = w.render(res_for(wdays, True))
    assert t_win.startswith("# W6b 順序の確かめ(窓の 10 日)")
    assert t_win.count("前(FX、〜2024-03-27)の小計") == 3 and t_win.count("後(CFD、2024-03-28〜)の小計") == 3  # 良い・悪い・O5
    assert "(6 日の版の補足)" in t_win and "window_guard" in t_win and "前後の小計" in t_win
    t_pre = w.render(res_for(list(w.day_of(n) for n in w.TRADE_FILES), False))
    assert t_pre.startswith("# W6b 順序の確かめ(封印の前の 6 日)")
    assert "小計" not in t_pre and "window" not in t_pre and "窓" not in t_pre
