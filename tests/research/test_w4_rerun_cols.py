"""走らせ直し(2026-10-06、カード 1・2・3・6)のために足した口の試験: `scripts/w4_measure/run_v2.py` の --extra-cols
(save_npz・c2_kind_card・c2_kind_cols・write_rerun_outputs)、`common.usdjpy_ref_dataset` の extend、`run_b2.py` の
--usdjpy-2023 の止め、`rerun_check.py`(元の daily.csv との突き合わせ・足した列の意味)。

封印の決まり: 合成のデータだけを使う。時刻は試験の時刻で、実データではない(実データのファイルは開かない)。
"""
from __future__ import annotations

import importlib
import json
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from bot.bt.core import BarEvent
from bot.bt.data.reference import reference_series
from bot.research.cards import run_card
from bot.research.cards.library.c2_owner_xvenue_wick import ROW_LAG_NS, SERIES_SPOT, C2OwnerXvenueWick
from bot.research.cards.measure import daily_rows, write_daily
from bot.research.cards.pnl import pnl
from bot.research.cards.run import CardRun

NS = 1_000_000_000
M = 60 * NS


def _load_w4(name):
    """scripts/w4_measure の台本を読み込む(test_window1_loader の _load_w4 と同じ中身。説明はそちら)。"""
    d = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "w4_measure"))
    if name in sys.modules:
        return sys.modules[name]
    shared = ("common", "post", "run_v2")

    def mine(m):
        return os.path.dirname(os.path.abspath(getattr(m, "__file__", None) or "")) == d

    before = {k: sys.modules.pop(k) for k in shared if k in sys.modules}
    for k, m in before.items():
        if mine(m):
            sys.modules.setdefault("_w4measure__" + k, m)
    for k in shared:
        if "_w4measure__" + k in sys.modules:
            sys.modules[k] = sys.modules["_w4measure__" + k]
    path_before = list(sys.path)
    sys.path.insert(0, d)
    try:
        return importlib.import_module(name)
    finally:
        sys.path[:] = path_before
        for k in shared:
            m = sys.modules.pop(k, None)
            if m is not None and mine(m):
                sys.modules.setdefault("_w4measure__" + k, m)
        sys.modules.update(before)


V2 = _load_w4("run_v2")
B2 = _load_w4("run_b2")
RC = _load_w4("rerun_check")
# run_b2 が使っている common(ほかの試験が先に run_v2・common を別に読み込んでいても、run_b2 の関数が見る物を使う)
CM = SimpleNamespace(**B2.usdjpy_ref_dataset.__globals__)


# ---------- 合成の CardRun ----------

T0 = 1_704_067_200 * NS  # 2024-01-01T00:00:00Z。試験の時刻で、データではない


def synth_run(n=3 * 1440 + 30, seed=7, empty=(5, 6, 700)):
    """1 分足 n 本の合成の記録。量 0 の足は決定なし(持ち高 NaN)。高値・安値は始値・終値を挟む。"""
    rng = np.random.default_rng(seed)
    start = T0 + np.arange(n, dtype=np.int64) * M
    o = 100.0 * np.exp(np.cumsum(rng.normal(0, 1e-3, n)))
    c = o * np.exp(rng.normal(0, 5e-4, n))
    h = np.maximum(o, c) * (1 + rng.uniform(0, 5e-4, n))
    lo = np.minimum(o, c) * (1 - rng.uniform(0, 5e-4, n))
    vol = np.ones(n)
    vol[list(empty)] = 0.0
    dec = vol > 0
    ex = np.where(dec, rng.choice([-1.0, 0.0, 1.0], n), np.nan)
    return CardRun(card="synthetic", venue="bitflyer", symbol="FX_BTC_JPY", start_ns=start, end_ns=start + M,
                   open=o, high=h, low=lo, close=c, volume=vol, decided=dec, exposure=ex)


def sub_run(run, k):
    f = ("start_ns", "end_ns", "open", "high", "low", "close", "volume", "decided", "exposure")
    return CardRun(card=run.card, venue=run.venue, symbol=run.symbol, **{x: getattr(run, x)[:k] for x in f})


OLD_KEYS = {"end_ns", "start_ns", "open", "close", "volume", "decided", "exposure"}


def test_save_npz_without_flag_keeps_old_name_and_columns(tmp_path):
    """--extra-cols が無ければ、名前は <tag>.npz、列は今までの 7 つ + extra だけ(高値・安値は足さない)。"""
    run = synth_run()
    extra = {"signal_log": np.zeros((2, 4), dtype=np.int64)}
    p = V2.save_npz(run, str(tmp_path), "a_15m_year_2017-08-17_2023-12-17", extra, False)
    assert os.path.basename(p) == "a_15m_year_2017-08-17_2023-12-17.npz"
    with np.load(p) as z:
        assert set(z.files) == OLD_KEYS | {"signal_log"}


def test_save_npz_with_flag_adds_high_low_and_keeps_other_columns_identical(tmp_path):
    """--extra-cols: 名前は run.npz、高値・安値が足され、ほかの列は引数なしの保存とビット一致(NaN も同じ位置)。"""
    run = synth_run()
    os.makedirs(tmp_path / "old")
    os.makedirs(tmp_path / "new")
    p0 = V2.save_npz(run, str(tmp_path / "old"), "t", {}, False)
    p1 = V2.save_npz(run, str(tmp_path / "new"), "t", {}, True)
    assert os.path.basename(p1) == "run.npz"
    with np.load(p0) as z0, np.load(p1) as z1:
        assert set(z1.files) == OLD_KEYS | {"high", "low"}
        for k in OLD_KEYS:
            assert z0[k].dtype == z1[k].dtype and np.array_equal(z0[k], z1[k], equal_nan=(z0[k].dtype.kind == "f")), k
        assert np.array_equal(z1["high"], run.high) and np.array_equal(z1["low"], run.low)


def test_write_rerun_outputs_daily_matches_measure_writer(tmp_path):
    """daily.csv は測定器の write_daily(daily_rows(pnl(run), Asia/Tokyo)) と同じバイト。run_record.json に npz の列と sha。"""
    run = synth_run()
    p1 = V2.save_npz(run, str(tmp_path), "t", {}, True)
    rec = V2.write_rerun_outputs(run, str(tmp_path), p1, {"variant": "x"})
    ref = write_daily(daily_rows(pnl(run), "Asia/Tokyo"), str(tmp_path / "ref.csv"))
    assert rec["daily_csv_sha256"] == ref
    assert (tmp_path / "daily.csv").read_bytes() == (tmp_path / "ref.csv").read_bytes()
    saved = json.loads((tmp_path / "run_record.json").read_text(encoding="utf-8"))
    assert saved["npz_keys"] == sorted(OLD_KEYS | {"high", "low"}) and saved["variant"] == "x"
    assert saved["n_decisions"] == int(run.decided.sum()) and saved["n_undefined"] == 2


@pytest.mark.parametrize("argv", [["--card", "c1", "--extra-cols"],
                                  ["--card", "c1", "--extra-cols", "--no-measure", "--light", "--save-root", "x"],
                                  ["--card", "c1", "--extra-cols", "--no-measure", "--from-npz", "y", "--save-root", "x"],
                                  ["--card", "c1", "--extra-cols", "--no-measure"]])
def test_extra_cols_refused_outside_no_measure(monkeypatch, argv):
    """--extra-cols は --no-measure と --save-root と一緒のときだけ(元の measure/<変種>/ に書かない)。読む前に止まる。"""
    monkeypatch.setattr(sys, "argv", ["run_v2.py"] + argv)
    with pytest.raises(SystemExit) as e:
        V2.main()
    assert "--extra-cols" in str(e.value)


# ---------- カード 2 の強い・弱い ----------

P = 10_000.0  # 試験の値段。1 bp = 1.0
DECL = {n: {"lag_ns": ROW_LAG_NS, "source": "試験の入力"} for n in SERIES_SPOT}


def candle(color, body_bp, top_bp, under_bp, o=P):
    bp = o * 1e-4
    c = o + color * body_bp * bp
    return (o, max(o, c) + top_bp * bp, min(o, c) - under_bp * bp, c)


def c2_run(card, candles, foot=15):
    rows = {n: [] for n in SERIES_SPOT}
    for j, (o, h, lo, c) in enumerate(candles):
        for m in range(foot):
            vals = (o, h, lo, c) if m == 0 else (c, c, c, c)
            for n, v in zip(SERIES_SPOT, vals):
                rows[n].append((T0 + (j * foot + m) * M, float(v)))
    refs = {n: reference_series(n, rows[n], declarations=DECL) for n in rows}
    n_min = len(candles) * foot + 2
    bars = [BarEvent(received_time_ns=T0 + (i + 1) * M, exchange_time_ns=T0 + (i + 1) * M, start_time_ns=T0 + i * M,
                     open=100.0, high=100.0, low=100.0, close=100.0, volume=1.0) for i in range(n_min)]
    return run_card(card, bars, references=refs, declarations=DECL, venue="bitflyer", symbol="FX_BTC_JPY")


# 陽線 × 買い = 強い買い / 陽線 × 売り = 弱い売り / 陰線 × 買い = 弱い買い / 陰線 × 売り = 強い売り(カードの説明の 4 通り)。
# 間に同値足(合図なし)と、ヒゲが短く合図にならない陽線を挟む。
KIND_CANDLES = [candle(+1, 5, 0, 30), (P, P, P, P), candle(+1, 5, 30, 0), candle(+1, 5, 3, 2),
                candle(-1, 5, 0, 30), candle(-1, 5, 30, 0)]


def test_c2_kind_card_records_color_and_strong_without_changing_exposure():
    """継いだカードは、持ち高・signal_log が元のカードとビット一致。色と強い・弱いが 4 通りで意図どおり。"""
    plain = C2OwnerXvenueWick()
    kind = V2.c2_kind_card(SERIES_SPOT, 15)
    r0, r1 = c2_run(plain, KIND_CANDLES), c2_run(kind, KIND_CANDLES)
    assert np.array_equal(r0.exposure, r1.exposure, equal_nan=True) and np.array_equal(r0.decided, r1.decided)
    assert plain.signal_log == kind.signal_log
    cols = V2.c2_kind_cols(kind)
    log = np.array(kind.signal_log).reshape(-1, 4)
    assert log[:, 1].tolist() == [1, -1, 1, -1]
    assert cols["signal_color"].tolist() == [1, 1, -1, -1]
    assert cols["signal_strong"].tolist() == [True, False, False, True]
    assert cols["signal_color"].dtype == np.int8 and cols["signal_strong"].dtype == bool
    # 持ち高そのもの(合図の後の最初の決定の値): 強い買い +1 → 弱い売りで決済 0 → 弱い買い +1 → 強い売り −1
    assert sorted(set(r1.exposure[r1.decided].tolist())) == [-1.0, 0.0, 1.0]


def test_c2_kind_cols_refuses_misaligned_lengths():
    kind = V2.c2_kind_card(SERIES_SPOT, 15)
    c2_run(kind, KIND_CANDLES)
    kind.signal_color.pop()
    with pytest.raises(SystemExit):
        V2.c2_kind_cols(kind)


# ---------- カード 6 の USDJPY の延長 ----------

def test_usdjpy_dataset_default_unchanged_and_extend_only_after_2023():
    lo = CM.iso("2017-08-01T15:00:00Z")
    old = CM.usdjpy_ref_dataset("usdjpy_close", lo, CM.iso("2022-12-31T15:00:00Z"))
    assert old["paths"] == [CM.USDJPY_PATH]
    same = CM.usdjpy_ref_dataset("usdjpy_close", lo, CM.iso("2022-12-31T15:00:00Z"), extend=True)
    assert same == old  # 終わりが 2023-01-01 以前なら extend でも同じ
    ext = CM.usdjpy_ref_dataset("usdjpy_close", lo, CM.iso("2023-12-17T15:00:00Z"), extend=True)
    assert ext["paths"] == [CM.USDJPY_PATH, CM.USDJPY_PATH_2023] and ext["spec"] == old["spec"]
    no_ext = CM.usdjpy_ref_dataset("usdjpy_close", lo, CM.iso("2023-12-17T15:00:00Z"))
    assert no_ext["paths"] == [CM.USDJPY_PATH]  # 引数なしは今までどおり(1 ファイル)
    with pytest.raises(SystemExit):  # 封印の境より後は extend でも拒む
        CM.usdjpy_ref_dataset("usdjpy_close", lo, CM.iso("2023-12-18T00:01:00Z"), extend=True)


@pytest.mark.parametrize("argv,needle", [
    (["--card", "c6", "--variant", "btc", "--end", "2023-12-17T15:00:00Z"], "--usdjpy-2023"),
    (["--card", "c7", "--variant", "1w", "--usdjpy-2023"], "カード 6 だけ"),
])
def test_run_b2_refuses_c6_beyond_2022_without_flag(monkeypatch, argv, needle):
    """カード 6 で終わりが 2023-01-01 より後なのに --usdjpy-2023 が無い → 読む前に止まる。ほかのカードに --usdjpy-2023 → 止まる。"""
    monkeypatch.setattr(sys, "argv", ["run_b2.py"] + argv)
    with pytest.raises(SystemExit) as e:
        B2.main()
    assert needle in str(e.value)


# ---------- rerun_check ----------

def _write_dir(d, run, extra=None):
    os.makedirs(d, exist_ok=True)
    p = V2.save_npz(run, str(d), "t", extra or {}, True)
    V2.write_rerun_outputs(run, str(d), p, {})


def _orig(d, run):
    os.makedirs(d, exist_ok=True)
    write_daily(daily_rows(pnl(run), "Asia/Tokyo"), os.path.join(d, "daily.csv"))


def _check(monkeypatch, new, orig):
    monkeypatch.setattr(sys, "argv", ["rerun_check.py", "--dir", str(new), "--orig", str(orig)])
    code = RC.main()
    return code, json.loads((new / "rerun_check.json").read_text(encoding="utf-8"))


def test_rerun_check_identical(tmp_path, monkeypatch):
    run = synth_run()
    _write_dir(tmp_path / "new", run)
    _orig(tmp_path / "orig", run)
    code, res = _check(monkeypatch, tmp_path / "new", tmp_path / "orig")
    assert code == 0 and res["reproduce"]["identical"] and res["cols"]["high_low"]["ok"] and res["npz_vs_daily_csv_same"]


def test_rerun_check_short_run_matches_prefix_except_last_day(tmp_path, monkeypatch):
    """短い期間の走らせ直し: 最後の日(P の無い最後の 2 決定・途中で切れた日)を外した日が元と同じなら通る。延ばした走らせも同じ。"""
    run = synth_run()
    short = sub_run(run, 1440 + 200)  # 2 日目の途中で切る
    _write_dir(tmp_path / "new", short)
    _orig(tmp_path / "orig", run)
    code, res = _check(monkeypatch, tmp_path / "new", tmp_path / "orig")
    r = res["reproduce"]
    assert code == 0 and not r["identical"] and r["n_days_compared"] >= 1 and r["n_days_mismatch"] == 0
    # 逆向き(元が短く、走らせ直しが延ばした形)
    _write_dir(tmp_path / "ext", run)
    _orig(tmp_path / "orig_short", short)
    code, res = _check(monkeypatch, tmp_path / "ext", tmp_path / "orig_short")
    assert code == 0 and res["reproduce"]["n_days_only_in_new_after_orig_end"] >= 1


def test_rerun_check_detects_changed_day_and_bad_high_low(tmp_path, monkeypatch):
    run = synth_run()
    _write_dir(tmp_path / "new", run)
    _orig(tmp_path / "orig", run)
    lines = (tmp_path / "orig" / "daily.csv").read_text(encoding="utf-8").splitlines()
    d, v, n = lines[1].split(",")
    lines[1] = f"{d},{float(v) + 1e-9!r},{n}"
    (tmp_path / "orig" / "daily.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    code, res = _check(monkeypatch, tmp_path / "new", tmp_path / "orig")
    assert code == 3 and res["reproduce"]["n_days_mismatch"] == 1
    bad = synth_run()
    bad.high[10] = min(bad.open[10], bad.close[10]) - 1.0  # 高値が始値・終値より下
    _write_dir(tmp_path / "bad", bad)
    _orig(tmp_path / "orig_bad", bad)
    code, res = _check(monkeypatch, tmp_path / "bad", tmp_path / "orig_bad")
    assert code == 3 and res["cols"]["high_low"]["n_high_below_open_or_close"] == 1


def test_rerun_check_c2_kind_columns(tmp_path, monkeypatch):
    """カード 2 の列: signal_color と signal_log の行が揃い、strong = (色 == 向き)。4 通りの数を出す。"""
    kind = V2.c2_kind_card(SERIES_SPOT, 15)
    r = c2_run(kind, KIND_CANDLES)
    extra = {"signal_log": np.array(kind.signal_log, dtype=np.int64).reshape(-1, 4), **V2.c2_kind_cols(kind)}
    _write_dir(tmp_path / "new", r, extra)
    _orig(tmp_path / "orig", r)
    code, res = _check(monkeypatch, tmp_path / "new", tmp_path / "orig")
    assert code == 0 and res["cols"]["c2_kind"]["ok"]
    assert res["cols"]["c2_kind"]["counts"] == {"strong_buy": 1, "strong_sell": 1, "weak_buy": 1, "weak_sell": 1}


# ---------- 小さな出力(trades.csv.gz・signals.csv.gz) ----------

def _no_midnight(run, margin_min=5):
    """日本時間の 0 時(15:00 UTC)の前後 margin_min 分の決定の持ち高を 0 にした写し(取引が日をまたがない作り物)。"""
    e = run.exposure.copy()
    mod = (run.end_ns // M - 15 * 60) % 1440  # 15:00 UTC からの分
    near = (mod < margin_min) | (mod > 1440 - margin_min)
    e[near & run.decided] = 0.0
    f = ("start_ns", "end_ns", "open", "high", "low", "close", "volume", "decided")
    return CardRun(card=run.card, venue=run.venue, symbol=run.symbol, exposure=e, **{x: getattr(run, x) for x in f})


def _read_gz(path):
    import csv
    import gzip
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_trades_csv_from_card_trades_sums_to_daily_csv_per_day(tmp_path, monkeypatch):
    """card_trades(import)で書いた trades.csv.gz の、合図の日本時間の日ごとの和が daily.csv と一致する(取引が日をまたがない作り物)。
    列は signal_t・entry_t・exit_t・side・pnl_bp、side は ±1。"""
    run = _no_midnight(synth_run())
    _write_dir(tmp_path / "new", run)
    _orig(tmp_path / "orig", run)
    code, res = _check(monkeypatch, tmp_path / "new", tmp_path / "orig")
    tr = res["trades"]
    assert code == 0 and tr["ok"] and tr["daily_calc_mismatch_days"] == 0
    assert tr["info_days_where_signal_day_sum_differs"] == 0
    rows = _read_gz(tmp_path / "new" / "trades.csv.gz")
    assert list(rows[0]) == ["signal_t", "entry_t", "exit_t", "side", "pnl_bp"] and {r["side"] for r in rows} == {"1", "-1"}
    daily = {ln.split(",")[0]: float(ln.split(",")[1])
             for ln in (tmp_path / "new" / "daily.csv").read_text(encoding="utf-8").splitlines()[1:]}
    from datetime import datetime, timedelta, timezone
    jst = timezone(timedelta(hours=9))
    by_day = {}
    for r in rows:
        dd = datetime.fromisoformat(r["signal_t"].replace("Z", "+00:00")).astimezone(jst).date().isoformat()
        by_day[dd] = by_day.get(dd, 0.0) + float(r["pnl_bp"])
    assert set(by_day) <= set(daily)
    for dd, v in daily.items():
        assert abs(v - by_day.get(dd, 0.0)) <= 1e-6 * len(rows), dd
    assert tr["n_trades"] == len(rows) == tr["sides"]["buy"] + tr["sides"]["sell"]


def test_trades_sum_check_fails_when_a_trade_is_dropped(tmp_path, monkeypatch):
    """取引の行の和の確かめが効くこと: card_trades の write_trades が 1 行落としたら止まる(3)。"""
    run = synth_run()
    _write_dir(tmp_path / "new", run)
    _orig(tmp_path / "orig", run)
    ct = RC._card_trades()
    real = ct.write_trades
    monkeypatch.setattr(ct, "write_trades", lambda trades, d: real(trades[1:], d))
    code, res = _check(monkeypatch, tmp_path / "new", tmp_path / "orig")
    assert code == 3 and not res["trades"]["ok"]


def test_signals_csv_rows_equal_signal_log(tmp_path, monkeypatch):
    """カード 2: signals.csv.gz の行の数 = signal_log の行の数。列は signal_t・side・signal_color・signal_strong、並びは signal_log のまま。"""
    kind = V2.c2_kind_card(SERIES_SPOT, 15)
    r = c2_run(kind, KIND_CANDLES)
    extra = {"signal_log": np.array(kind.signal_log, dtype=np.int64).reshape(-1, 4), **V2.c2_kind_cols(kind)}
    _write_dir(tmp_path / "new", r, extra)
    _orig(tmp_path / "orig", r)
    code, res = _check(monkeypatch, tmp_path / "new", tmp_path / "orig")
    assert code == 0 and res["signals"]["ok"] and res["signals"]["n_rows"] == len(kind.signal_log) == 4
    rows = _read_gz(tmp_path / "new" / "signals.csv.gz")
    assert list(rows[0]) == ["signal_t", "side", "signal_color", "signal_strong"]
    assert [(r_["side"], r_["signal_color"], r_["signal_strong"]) for r_ in rows] == \
        [("1", "1", "1"), ("-1", "1", "0"), ("1", "-1", "0"), ("-1", "-1", "1")]
    ends = [int(x[0]) for x in kind.signal_log]
    assert [r_["signal_t"] for r_ in rows] == [RC._iso(t) for t in ends]


def test_signals_refused_when_lengths_differ(tmp_path):
    z = {"signal_log": np.zeros((3, 4), dtype=np.int64), "signal_color": np.ones(2, dtype=np.int8),
         "signal_strong": np.ones(3, dtype=bool)}
    out = RC.write_signals(z, str(tmp_path))
    assert not out["ok"] and not (tmp_path / "signals.csv.gz").exists()


# ---------- 批評家 1 回目の直し(2026-10-06): --require-identical・カード 3 の 1 本遅らせた損益・extend の終わり ----------

def _same_period_cases(tmp_path):
    """批評家の breaks.py の 7・8・9 と同じ形を作り物で作る。戻り: {名前: (走らせ直しの置き場, 元の置き場)}。"""
    run = synth_run()
    short = sub_run(run, 1440 + 200)
    new = tmp_path / "new"
    _write_dir(new, run)
    lines = (new / "daily.csv").read_text(encoding="utf-8").splitlines()
    o7 = tmp_path / "o7"  # 7: 同じ期間の元で、最後の日だけ損益が +123 bp 違う
    os.makedirs(o7)
    d_, v_, n_ = lines[-1].split(",")
    (o7 / "daily.csv").write_text("\n".join(lines[:-1] + [f"{d_},{float(v_) + 123.0!r},{n_}"]) + "\n", encoding="utf-8")
    new8 = tmp_path / "new8"  # 8: 短い走らせ直し × 長い元
    _write_dir(new8, short)
    o8 = tmp_path / "o8"
    _orig(o8, run)
    o9 = tmp_path / "o9"  # 9: 元に最後の日が無い(走らせ直しが 1 日多い)
    os.makedirs(o9)
    (o9 / "daily.csv").write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    o0 = tmp_path / "o0"  # 0: 壊さない
    os.makedirs(o0)
    (o0 / "daily.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"0": (new, o0), "7": (new, o7), "8": (new8, o8), "9": (new, o9)}


def _check_args(monkeypatch, new, orig, *extra):
    monkeypatch.setattr(sys, "argv", ["rerun_check.py", "--dir", str(new), "--orig", str(orig), *extra])
    code = RC.main()
    return code, json.loads((new / "rerun_check.json").read_text(encoding="utf-8"))


def test_require_identical_refuses_breaks_7_8_9(tmp_path, monkeypatch):
    """--require-identical(カード 1・2・3 の 22 本): 最後の日だけ違う(7)・期間が足りない(8)・元に最後の日が無い(9)は 3。
    壊さない(0)は 0。"""
    cases = _same_period_cases(tmp_path)
    for k, (new, orig) in cases.items():
        code, res = _check_args(monkeypatch, new, orig, "--require-identical")
        if k == "0":
            assert code == 0 and res["reproduce"]["identical"], k
        else:
            assert code == 3 and not res["reproduce"]["ok"] and res["reproduce"]["require_identical"], k
    code, res = _check_args(monkeypatch, *cases["7"], "--require-identical")
    assert res["reproduce"]["same_n_days"] and not res["reproduce"]["same_last_line"]
    code, res = _check_args(monkeypatch, *cases["9"], "--require-identical")
    assert not res["reproduce"]["same_n_days"]


def test_without_require_identical_extension_form_is_kept(tmp_path, monkeypatch):
    """引数なし(カード 6 の延長 2 本の形)は今までどおり: 元の最後の日を除いた突き合わせで通る(8・9 の形は 0)。"""
    cases = _same_period_cases(tmp_path)
    for k in ("0", "8", "9"):
        code, _res = _check_args(monkeypatch, *cases[k])
        assert code == 0, k


def _tiny_c3_like():
    """手で計算できる 8 本の足。2 本目(添字 2)は量 0(決定なし)。持ち高は連続の値。"""
    n = 8
    start = T0 + np.arange(n, dtype=np.int64) * M
    o = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0])
    vol = np.array([1, 1, 0, 1, 1, 1, 1, 1], dtype=float)
    ex = np.array([0.5, -0.25, np.nan, 1.0, 0.0, -1.0, 0.75, 0.2])
    return CardRun(card="c3_yen_premium_revert", venue="bitflyer", symbol="FX_BTC_JPY", start_ns=start, end_ns=start + M,
                   open=o, high=o + 0.5, low=o - 0.5, close=o, volume=vol, decided=vol > 0, exposure=ex)


def test_lag1_pnl_by_hand(tmp_path, monkeypatch):
    """1 本遅らせた損益の手計算: 空でない足は添字 0,1,3,4,5,6,7。決定 t の持ち高を、t の後の 2 本目と 3 本目の空でない足の
    始値の間に当てる。最後の 3 決定(添字 5,6,7)は無し。
      添字 0: e 0.5 × (open[4] 104 / open[3] 103 − 1) × 1e4
      添字 1: e −0.25 × (open[5] 105 / open[4] 104 − 1) × 1e4
      添字 3: e 1 × (open[6] 106 / open[5] 105 − 1) × 1e4
      添字 4: e 0 × (open[7] 107 / open[6] 106 − 1) × 1e4 = 0
    """
    run = _tiny_c3_like()
    z = {k: getattr(run, k) for k in ("decided", "exposure", "open", "end_ns")}
    t, p1 = RC.lag1_pnl(z)
    want = [0.5 * (104 / 103 - 1) * 1e4, -0.25 * (105 / 104 - 1) * 1e4, 1.0 * (106 / 105 - 1) * 1e4, 0.0]
    assert np.allclose(p1, want, rtol=0, atol=1e-12) and t.tolist() == (T0 + np.array([1, 2, 4, 5]) * M).tolist()
    # 通しで: rerun_check がカード 3 の置き場に daily_lag1.csv と positions.npz を書く
    new = tmp_path / "c3"
    _write_dir(new, run)
    rr = json.loads((new / "run_record.json").read_text(encoding="utf-8"))
    rr["card"] = "c3_yen_premium_revert"
    (new / "run_record.json").write_text(json.dumps(rr), encoding="utf-8")
    _orig(tmp_path / "o", run)
    code, res = _check_args(monkeypatch, new, tmp_path / "o", "--require-identical")
    assert code == 0 and res["lag1_positions"]["ok"]
    lines = (new / "daily_lag1.csv").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "day,pnl_bp,n" and len(lines) == 2  # 全部が日本時間の 2024-01-01
    d_, v_, n_ = lines[1].split(",")
    assert d_ == "2024-01-01" and int(n_) == 4 and abs(float(v_) - sum(want)) < 1e-9
    with np.load(new / "positions.npz") as f:
        assert f["t_end_min"].dtype == np.int32 and f["e"].dtype == np.float32
        assert (f["t_end_min"].astype(np.int64) * M).tolist() == run.end_ns[run.decided].tolist()
        assert np.allclose(f["e"], run.exposure[run.decided], atol=1e-7)


def test_positions_written_only_for_card3_or_non_ternary(tmp_path, monkeypatch):
    """持ち高が −1・0・+1 だけでカード 3 でない置き場(カード 1・2・6)には書かない。連続の値なら書く(カードの名前によらず)。"""
    run = synth_run()  # 持ち高は −1・0・+1
    _write_dir(tmp_path / "t", run)
    _orig(tmp_path / "o", run)
    code, res = _check_args(monkeypatch, tmp_path / "t", tmp_path / "o", "--require-identical")
    assert code == 0 and "lag1_positions" not in res and not (tmp_path / "t" / "positions.npz").exists()
    cont = synth_run()
    cont.exposure[cont.decided] *= 0.5
    _write_dir(tmp_path / "c", cont)
    _orig(tmp_path / "oc", cont)
    code, res = _check_args(monkeypatch, tmp_path / "c", tmp_path / "oc", "--require-identical")
    assert code == 0 and res["lag1_positions"]["ok"] and (tmp_path / "c" / "daily_lag1.csv").exists()


def test_usdjpy_extend_end_capped_at_2023_12_17_15z():
    """extend=True の終わりは 2023-12-17T15:00Z まで(15:00:01Z〜封印の境 00:00Z は拒む)。extend=False は今までどおり check_end だけ。"""
    lo = CM.iso("2017-08-01T15:00:00Z")
    ok = CM.usdjpy_ref_dataset("usdjpy_close", lo, CM.iso("2023-12-17T15:00:00Z"), extend=True)
    assert ok["paths"] == [CM.USDJPY_PATH, CM.USDJPY_PATH_2023]
    for hi in ("2023-12-17T15:00:01Z", "2023-12-18T00:00:00Z"):
        with pytest.raises(SystemExit) as e:
            CM.usdjpy_ref_dataset("usdjpy_close", lo, CM.iso(hi), extend=True)
        assert "2023-12-17T15:00:00Z" in str(e.value)
        assert CM.usdjpy_ref_dataset("usdjpy_close", lo, CM.iso(hi))["paths"] == [CM.USDJPY_PATH]  # 既定は変えない
    CM.check_end(CM.iso("2023-12-18T00:00:00Z"))  # ほかの口の境(check_end)は変えない
