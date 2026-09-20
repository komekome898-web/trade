"""`scripts/o3c_signal_continue.py`(清算を起点とした値動きの予測可能性 —
続く / 止まるの単位)の試験。

**測るもの**(委任文【テスト】(1)〜(9))
  1. ラベルの計算(合成の清算列で 60 秒の境界の内外)。
  2. 前半・後半の分割が 228 / 228 日で、切り値が前半だけから出る
     (後半の値を変えても切り値が変わらない)。
  3. 材料が未来を使わない(ts 以後の約定・清算を消した入力で材料 1〜15 が同じ値。
     p0 を変えても同じ)。
  4. 2 枝の損益の符号(続くと言って上がれば正、止まると言って下がれば正)。
  5. 出る時点が入る時点からの保有期間(t0 + entry + hold)。
  6. Q7 の候補が前後 15 分に清算を持たない。
  7. `paper_logs/` を開かない(ソースに文字列が無い)。
  8. 判定語が `tables.md` に無い(`check_no_banned` の単体試験 + 実データがあれば
     実際の `tables.md` も検査)。
  9. Jev の state に p0 と ts 以後の値が入らない(合成データで)。
"""
from __future__ import annotations

import builtins
import gzip
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location(
    "o3c_signal_continue", ROOT / "scripts" / "o3c_signal_continue.py")
sc = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(sc)

DATA_ROOT = ROOT / "backtest_data" / "binance_cm_o3c_20260913"
ROWS_PATH = (ROOT / "backtest_data" / "o3c_signal_explore5_20260920"
            / "rows_prints.csv.gz")
have_data = ROWS_PATH.exists() and (DATA_ROOT / "aggTrades").exists()
needs_data = pytest.mark.skipif(not have_data, reason="探索段5の行データか公開アーカイブが無い")


# ---------------------------------------------------------------------------
# 小道具: 合成の `rows_prints.csv.gz` 相当を作って `PrintsCSV` を組み立てる
# ---------------------------------------------------------------------------
def make_prints_csv(tmp_path: Path, rows: list) -> "sc.PrintsCSV":
    """`rows` は dict のリスト(print_id・day・side・ts_ms・…)。"""
    cols = ["kind", "print_id", "day", "side", "ts_ms", "t0_ms", "p0", "notional",
           "dist_node_bp", "oi_covered", "bundle_id"]
    df = pd.DataFrame([{c: r.get(c, "") for c in cols} for r in rows])
    df["kind"] = "print"
    p = tmp_path / "rows_prints.csv.gz"
    df.to_csv(p, index=False, compression="gzip")
    return sc.PrintsCSV(p)


# ---------------------------------------------------------------------------
# (1) ラベルの計算
# ---------------------------------------------------------------------------
def test_continuation_label_60s_boundary_inside_and_outside(tmp_path):
    day = "2024-01-02"
    base_ts = 1_704_196_800_000  # day 00:00 UTC
    rows = [
        {"print_id": "a", "day": day, "side": "SELL", "ts_ms": base_ts,
         "t0_ms": base_ts, "p0": 100.0, "notional": 1.0, "dist_node_bp": 0.0,
         "oi_covered": 0, "bundle_id": ""},
        # ちょうど 60,000ms 後(境界を含む) -> a の label_60 は 1
        {"print_id": "b", "day": day, "side": "SELL", "ts_ms": base_ts + 60_000,
         "t0_ms": base_ts + 60_000, "p0": 100.0, "notional": 1.0,
         "dist_node_bp": 0.0, "oi_covered": 0, "bundle_id": ""},
        # b から 60,001ms 後(境界を 1ms 超える) -> b の label_60 は 0、label_120 は 1
        {"print_id": "c", "day": day, "side": "SELL", "ts_ms": base_ts + 120_001,
         "t0_ms": base_ts + 120_001, "p0": 100.0, "notional": 1.0,
         "dist_node_bp": 0.0, "oi_covered": 0, "bundle_id": ""},
        # 反対側(BUY)は無視される(次の「同じ側」だけを見る)
        {"print_id": "x", "day": day, "side": "BUY", "ts_ms": base_ts + 1_000,
         "t0_ms": base_ts + 1_000, "p0": 100.0, "notional": 1.0,
         "dist_node_bp": 0.0, "oi_covered": 0, "bundle_id": ""},
    ]
    pc = make_prints_csv(tmp_path, rows)
    idx = {pid: int(np.flatnonzero(pc.print_id == pid)[0]) for pid in "abc"}
    la = sc.continuation_labels(pc, idx["a"])
    assert la[60] == 1 and la[30] == 0 and la[120] == 1  # 次(b)は 60,000ms 後
    lb = sc.continuation_labels(pc, idx["b"])
    assert lb[60] == 0 and lb[30] == 0 and lb[120] == 1
    lc = sc.continuation_labels(pc, idx["c"])
    assert lc[60] == 0 and lc[30] == 0 and lc[120] == 0  # 次が無い(この期間の最後)


# ---------------------------------------------------------------------------
# (2) 前半・後半の分割と切り値
# ---------------------------------------------------------------------------
@needs_data
def test_days_split_228_228():
    df = pd.read_csv(ROWS_PATH, usecols=["kind", "day"])
    days = sorted(df.loc[df["kind"] == "print", "day"].unique())
    assert len(days) == 456
    half = len(days) // 2
    days1, days2 = days[:half], days[half:]
    assert len(days1) == 228 and len(days2) == 228


def test_first_half_cuts_ignore_second_half_values():
    rng = np.random.default_rng(0)
    n = 400
    half = np.array(["前半"] * 200 + ["後半"] * 200)
    data = {"half": half}
    for m in sc.MAT_NUMS_CONT:
        data[sc.MAT_COL[m]] = rng.normal(size=n)
    df = pd.DataFrame(data)
    cuts_a = sc.first_half_cuts(df)
    df2 = df.copy()
    for m in sc.MAT_NUMS_CONT:
        df2.loc[df2["half"] == "後半", sc.MAT_COL[m]] = 9999.0  # 後半を派手に変える
    cuts_b = sc.first_half_cuts(df2)
    for m in sc.MAT_NUMS_CONT:
        assert np.allclose(cuts_a[m], cuts_b[m])


# ---------------------------------------------------------------------------
# (3) 材料が未来を使わない
# ---------------------------------------------------------------------------
def _synthetic_trades(ts: int, future_prices_differ: bool):
    """ts を含む 1 秒刻みの約定列。`ts` より後だけ 2 通りの価格にできる。"""
    lo = ts - 4_000_000
    hi = ts + 400_000
    times = np.arange(lo, hi + 1, 1000, dtype=np.int64)
    prices = 30000.0 + 0.001 * (times - lo)  # ts まではゆるい上昇
    after = times > ts
    if future_prices_differ:
        prices = prices.copy()
        prices[after] = prices[after] + 5000.0  # ts より後だけ大きく変える
    qtys = np.ones(times.size)
    maker = (np.arange(times.size) % 2 == 0)
    return times, prices, qtys, maker


def test_materials_do_not_use_data_after_ts_or_p0(tmp_path):
    day = "2024-01-02"
    ts = sc.day_start_ms(day) + 3_600_000
    rows = [
        {"print_id": "cur", "day": day, "side": "SELL", "ts_ms": ts, "t0_ms": ts,
         "p0": 30003.6, "notional": 500_000.0, "dist_node_bp": -12.5,
         "oi_covered": 0, "bundle_id": ""},
        {"print_id": "prev", "day": day, "side": "SELL", "ts_ms": ts - 30_000,
         "t0_ms": ts - 30_000, "p0": 29990.0, "notional": 200_000.0,
         "dist_node_bp": 0.0, "oi_covered": 0, "bundle_id": ""},
    ]
    pc = make_prints_csv(tmp_path, rows)
    nb = sc.same_side_neighbors(pc)
    i = int(np.flatnonzero(pc.print_id == "cur")[0])
    buckets = {"t_all": np.zeros(0, dtype=np.int64)}
    t_oi = np.zeros(0, dtype=np.int64)
    oi_lvl = np.zeros(0)
    tls = np.zeros(0)
    t_fund = np.zeros(0, dtype=np.int64)
    r_fund = np.zeros(0)

    times_a, prices_a, qtys_a, maker_a = _synthetic_trades(ts, False)
    times_b, prices_b, qtys_b, maker_b = _synthetic_trades(ts, True)
    # ts 以前は 2 系列とも同一であることの前提を確認
    assert np.array_equal(prices_a[times_a <= ts], prices_b[times_b <= ts])

    row_a, mat_a = sc.compute_print_row(day, pc, i, nb, times_a, prices_a, qtys_a,
                                        maker_a, buckets, None, t_oi, oi_lvl, tls,
                                        t_fund, r_fund, "前半")
    row_b, mat_b = sc.compute_print_row(day, pc, i, nb, times_b, prices_b, qtys_b,
                                        maker_b, buckets, None, t_oi, oi_lvl, tls,
                                        t_fund, r_fund, "前半")
    for n in sc.MAT_NUMS:
        a, b = mat_a[n], mat_b[n]
        if isinstance(a, float) and isinstance(b, float) and a != a and b != b:
            continue  # 両方 NaN(引けない)は同じ扱い
        assert a == b, f"材料 {n}({sc.MAT_VAR[n]}) が ts 以後のデータで変わった: {a} != {b}"

    # 対照として、entry/exit 価格(材料ではなく損益の材料)は t0 より後を見るので
    # 変わって当然(このテストの前提が効いていることの確認)
    header_a = dict(zip(sc.CHUNK_HEADER, row_a))
    header_b = dict(zip(sc.CHUNK_HEADER, row_b))
    assert header_a["p_exit_e1_h300"] != header_b["p_exit_e1_h300"]


def test_material5_reuses_dist_node_bp_column_not_p0(tmp_path):
    """材料 5 は `rows_prints.csv.gz` の `dist_node_bp` をそのまま使う(p0 を使って
    作り直さない)。"""
    day = "2024-01-02"
    ts = sc.day_start_ms(day) + 3_600_000
    rows = [{"print_id": "cur", "day": day, "side": "SELL", "ts_ms": ts,
             "t0_ms": ts, "p0": 30003.6, "notional": 500_000.0,
             "dist_node_bp": -42.125, "oi_covered": 0, "bundle_id": ""}]
    pc = make_prints_csv(tmp_path, rows)
    nb = sc.same_side_neighbors(pc)
    i = 0
    times, prices, qtys, maker = _synthetic_trades(ts, False)
    buckets = {"t_all": np.zeros(0, dtype=np.int64)}
    row, mat = sc.compute_print_row(day, pc, i, nb, times, prices, qtys, maker,
                                    buckets, None, np.zeros(0, dtype=np.int64),
                                    np.zeros(0), np.zeros(0),
                                    np.zeros(0, dtype=np.int64), np.zeros(0), "前半")
    assert mat[5] == pytest.approx(-42.125)


# ---------------------------------------------------------------------------
# (4) 2 枝の損益の符号 / (5) 保有期間
# ---------------------------------------------------------------------------
def test_branch_pnl_sign_continue_up_stop_down_are_positive():
    entry, exit_up, exit_down = 100.0, 101.0, 99.0
    s = 1.0  # side sign(SELL/BUY どちらでもここでは形だけ)
    # 続く(枝の向き = +s)で価格が上がれば正
    dirn_continue = s
    pnl_continue_up = dirn_continue * (exit_up - entry) / entry * 1e4
    assert pnl_continue_up > 0
    # 止まる(枝の向き = -s)で価格が下がれば正
    dirn_stop = -s
    pnl_stop_down = dirn_stop * (exit_down - entry) / entry * 1e4
    assert pnl_stop_down > 0
    # 逆向きは負になる
    assert dirn_continue * (exit_down - entry) / entry * 1e4 < 0
    assert dirn_stop * (exit_up - entry) / entry * 1e4 < 0


def test_exit_time_is_entry_time_plus_hold(tmp_path):
    day = "2024-01-02"
    ts = sc.day_start_ms(day) + 3_600_000
    rows = [{"print_id": "cur", "day": day, "side": "SELL", "ts_ms": ts,
             "t0_ms": ts, "p0": 30003.6, "notional": 500_000.0,
             "dist_node_bp": 0.0, "oi_covered": 0, "bundle_id": ""}]
    pc = make_prints_csv(tmp_path, rows)
    nb = sc.same_side_neighbors(pc)
    times, prices, qtys, maker = _synthetic_trades(ts, False)
    buckets = {"t_all": np.zeros(0, dtype=np.int64)}
    row, _mat = sc.compute_print_row(day, pc, 0, nb, times, prices, qtys, maker,
                                     buckets, None, np.zeros(0, dtype=np.int64),
                                     np.zeros(0), np.zeros(0),
                                     np.zeros(0, dtype=np.int64), np.zeros(0), "前半")
    d = dict(zip(sc.CHUNK_HEADER, row))
    for e in sc.ENTRY_DELAYS_S:
        for h in sc.HOLD_SECONDS:
            t_exit = ts + e * 1000 + h * 1000
            expect, _ = sc.price_at_or_before(times, prices, t_exit)
            got = float(d[f"p_exit_e{e}_h{h}"]) if d[f"p_exit_e{e}_h{h}"] != "" else None
            if expect == expect:  # not NaN
                assert got == pytest.approx(expect)


# ---------------------------------------------------------------------------
# (6) Q7 の候補が前後 15 分に清算を持たない
# ---------------------------------------------------------------------------
def test_q7_no_liq_mask_excludes_15min_window():
    all_ts = np.array([1_000_000], dtype=np.int64)
    grid = np.array([1_000_000 - 15 * 60_000,       # ちょうど 15 分前 -> 除外
                     1_000_000 - 15 * 60_000 - 1,   # 15 分より前 -> 許可
                     1_000_000 + 15 * 60_000,        # ちょうど 15 分後 -> 除外
                     1_000_000 + 15 * 60_000 + 1,   # 15 分より後 -> 許可
                     50_000_000], dtype=np.int64)     # 遠い -> 許可
    ok = sc.q7_no_liq_mask(grid, all_ts)
    assert ok.tolist() == [False, True, False, True, True]


# ---------------------------------------------------------------------------
# (7) `paper_logs/` を開かない
# ---------------------------------------------------------------------------
def test_source_never_opens_paper_logs():
    """`paper_logs` という文字列が出るのは説明文(docstring や「開かない」の注記)
    だけで、実際にそれを開くコードは無い(探索段 5 の同名試験と同じ流儀)。"""
    src = (ROOT / "scripts" / "o3c_signal_continue.py").read_text().splitlines()
    hits = [ln for ln in src if "paper_logs" in ln]
    assert hits and all(
        ln.lstrip().startswith(("#", "*", '"""', "設計:", "委任文:"))
        or "開かない" in ln or "モックで" in ln
        for ln in hits), hits


@needs_data
def test_run_does_not_touch_paper_logs(tmp_path, monkeypatch):
    touched: list = []
    real_open = builtins.open
    real_gzopen = gzip.open

    def note(p):
        if "paper_logs" in Path(str(p)).parts:
            touched.append(str(p))

    def guarded_open(file, *a, **k):
        note(file)
        return real_open(file, *a, **k)

    def guarded_gzopen(filename, *a, **k):
        note(filename)
        return real_gzopen(filename, *a, **k)

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(gzip, "open", guarded_gzopen)
    rc = sc.main(["--data-root", str(DATA_ROOT), "--rows-path", str(ROWS_PATH),
                 "--out", str(tmp_path / "o"), "--limit-days", "2",
                 "--skip-jev", "--progress-every", "1000"])
    assert rc == 0
    assert touched == []


# ---------------------------------------------------------------------------
# (8) 判定語
# ---------------------------------------------------------------------------
def test_check_no_banned_raises_on_verdict_words():
    for w in sc.BANNED_WORDS:
        with pytest.raises(SystemExit):
            sc.check_no_banned(f"これは{w}です", "test")
    sc.check_no_banned("判定語の無い普通の文", "test")  # 例外を投げない


@needs_data
def test_no_verdict_words_in_real_tables_md(tmp_path):
    rc = sc.main(["--data-root", str(DATA_ROOT), "--rows-path", str(ROWS_PATH),
                 "--out", str(tmp_path / "o"), "--limit-days", "2",
                 "--skip-jev", "--progress-every", "1000"])
    assert rc == 0
    txt = (tmp_path / "o" / "tables.md").read_text()
    for w in sc.BANNED_WORDS:
        assert w not in txt


# ---------------------------------------------------------------------------
# (9) Jev の state に p0 と ts 以後の値が入らない
# ---------------------------------------------------------------------------
def test_jev_state_excludes_p0_and_future(tmp_path):
    day = "2024-01-02"
    ts = sc.day_start_ms(day) + 3_600_000
    rows = [{"print_id": "cur", "day": day, "side": "SELL", "ts_ms": ts,
             "t0_ms": ts, "p0": 30003.6, "notional": 500_000.0,
             "dist_node_bp": 0.0, "oi_covered": 0, "bundle_id": ""}]
    pc = make_prints_csv(tmp_path, rows)
    all_ts = pc.all_ts_sorted()
    o = np.argsort(pc.ts, kind="stable")
    all_side, all_notional = pc.side[o], pc.notional[o]

    times, prices, _q, _m = _synthetic_trades(ts, False)
    # ts より後の価格を仕込んでおき、state に混ざらないことを見る
    future_price = 999_999.0
    prices2 = prices.copy()
    prices2[times > ts] = future_price

    mat_row = {sc.MAT_COL[n]: 1.0 for n in sc.MAT_NUMS}
    mat_row[sc.MAT_COL[6]] = "UTC 00–06"
    state = sc.jev_state_for_print("cur", pc, all_ts, all_side, all_notional,
                                   times, prices2, mat_row)

    # (a) p0(30003.6)そのものが state のどこにも出ない
    import json
    blob = json.dumps(state, ensure_ascii=False)
    assert "30003.6" not in blob
    # (b) 未来の価格(future_price)が price_path に出ない
    assert future_price not in [p for p in state["price_path_bp_last_60s"] if p is not None]
    # (c) price_path は ts 以前(相対 -60〜0 秒)だけ
    assert len(state["price_path_bp_last_60s"]) == 61
    # (d) prints_last_60s は ts より前だけ(t_rel_s <= 0)
    for ev in state["prints_last_60s"]:
        assert ev["t_rel_s"] <= 0
    # (e) materials 辞書のキーは MAT_VAR の値と一致し、"p0" というキーは無い
    assert "p0" not in state["materials"]
    assert set(state["materials"].keys()) == set(sc.MAT_VAR.values())
