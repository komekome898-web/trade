"""`scripts/o3c_signal_value.py`(「値段の続き」を判断の対象にした方策の模擬 ① +
全部逆張りの最適化 ②)と `scripts/o3c_bitflyer_spread.py`(費用 c の材料)の試験。

**測るもの**(委任文【作るもの】2 の 10 項目)
  1. 値段のラベルの再計算が既存列と一致(前半の抽出 200 件)。
  2. 帯の規則(合成の確率列で「わからない」が基準率の周りに出る)。
  3. 費用 = c × 建玉の回数(型 B のドテン 1 回 = c)。
  4. 損切り・出口 3 種の約定が ts + d 以後(合成)。
  5. 格子の列挙が 189。
  6. 選ぶ規則 (a)(b) と「無かった」の分岐。
  7. `stage1` が後半の行で例外。
  8. 判定語(陽性・陰性・有意・差あり・検出されず)が出力の文字列に無い。
  9. `paper_logs/` を開かない。
 10. 実効スプレッドの対の作り方(合成の約定列)。
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


vv = _load("o3c_signal_value", "o3c_signal_value.py")
bsp = _load("o3c_bitflyer_spread", "o3c_bitflyer_spread.py")
sp = vv.sp

have_rows = vv.ROWS_CONTINUE.exists() and vv.ROWS_MATERIALS.exists()
have_trades = (vv.DATA_ROOT / "aggTrades").exists()
needs_data = pytest.mark.skipif(
    not (have_rows and have_trades),
    reason="前段の出力(rows_continue / rows_materials)か Binance の約定が無い")
needs_tardis = pytest.mark.skipif(
    not bsp.sample_day_paths(),
    reason="bitFlyer の標本日の約定(data/tardis/、gitignore 域)が無い")


def _fake_prices(n: int = 1200, step_ms: int = 1000, slope: float = 0.0,
                 base: float = 100.0):
    """合成の約定列(時刻 ms と値段)。`slope` は 1 秒あたりの値段の変化。"""
    times = np.arange(0, n * step_ms, step_ms, dtype=np.int64)
    prices = base + slope * (times / 1000.0)
    return times, prices


# ---------------------------------------------------------------------------
# (1) 値段のラベルの再計算が既存列と一致(前半の抽出 200 件)
# ---------------------------------------------------------------------------
def test_value_label_recompute_matches_column_on_synthetic_path():
    """合成の約定列で、`path_extreme_bp` と同じ窓 (t0, t0+60] の最大値が 5 bp 以上か
    どうかがラベルになり、初めて 5 bp に達した約定の秒が返る。"""
    times, prices = _fake_prices(n=200, step_ms=1000, slope=0.0)
    # 10 秒目に +6 bp、それ以外は横ばい(BUY の清算 = 上向き)
    prices = prices.copy()
    prices[10:] = 100.0 * (1 + 6e-4)
    lab, sec = vv.value_label_and_time_to_target(times, prices, 0, 100.0, 1.0)
    assert lab == 1.0
    assert sec == pytest.approx(10.0)
    # 4 bp しか動かなければラベルは 0、秒は NaN
    prices2 = prices.copy()
    prices2[10:] = 100.0 * (1 + 4e-4)
    lab2, sec2 = vv.value_label_and_time_to_target(times, prices2, 0, 100.0, 1.0)
    assert lab2 == 0.0 and math.isnan(sec2)
    # 窓の外(61 秒目)の動きは入らない
    prices3 = 100.0 * np.ones_like(prices)
    prices3[61:] = 100.0 * (1 + 9e-4)
    lab3, _ = vv.value_label_and_time_to_target(times, prices3, 0, 100.0, 1.0)
    assert lab3 == 0.0
    # 清算が SELL(向き −1)なら下向きの動きで 1 になる
    prices4 = 100.0 * np.ones_like(prices)
    prices4[5:] = 100.0 * (1 - 7e-4)
    lab4, sec4 = vv.value_label_and_time_to_target(times, prices4, 0, 100.0, -1.0)
    assert lab4 == 1.0 and sec4 == pytest.approx(5.0)


@needs_data
def test_value_label_recompute_matches_existing_column_for_200_front_half_prints():
    """前半から 200 件のプリントを抜き、`value_continuation_60` を約定から計算し直して
    既存列と突き合わせる(日をまたぐ読み込みを抑えるため、最初の数日から 200 件取る)。"""
    prints = vv.load_stage1_prints()
    days = sorted(set(prints["day"].astype(str)))
    picked, used = [], []
    for d in days:
        g = prints[prints["day"].astype(str) == d]
        picked.append(g)
        used.append(d)
        if sum(len(x) for x in picked) >= 200:
            break
    df = pd.concat(picked).head(200)
    assert len(df) == 200
    cache = vv.WindowCache(vv.DATA_ROOT)
    rows = vv.recompute_value_labels(df, cache)
    assert len(rows) == 200
    mismatched = [r for r in rows if not r["一致"]]
    assert not mismatched, mismatched[:3]


# ---------------------------------------------------------------------------
# (2) 帯の規則(L-277): 基準率の周りに「わからない」が出る
# ---------------------------------------------------------------------------
def test_calibration_band_puts_unknown_around_the_base_rate():
    rng = np.random.default_rng(20260921)
    n = 40_000
    prob = rng.uniform(0.0, 1.0, n)
    y = (rng.uniform(0.0, 1.0, n) < prob).astype(float)
    cal = vv.calibration_table(prob, y, step=vv.BAND_STEP)
    base = cal["基準率"]
    lo, hi = cal["帯"]
    assert lo < base < hi or (lo <= base <= hi)
    # 帯の中の帯は全部「わからない」、下は「止まる」、上は「続く」
    for r in cal["rows"]:
        if lo <= r["帯下端"] < hi:
            assert r["区分"] == vv.JUDGE_UNKNOWN
        elif r["帯上端"] <= lo:
            assert r["区分"] == vv.JUDGE_STOP
        elif r["帯下端"] >= hi:
            assert r["区分"] == vv.JUDGE_CONTINUE
    # 「わからない」の帯は基準率と 2 SE で区別できない帯だけからなる
    for r in cal["rows"]:
        if r["区分"] == vv.JUDGE_UNKNOWN:
            assert abs(r["続く割合"] - base) <= r["2SE"] + 1e-12
    # 帯の幅は 0.02
    widths = {round(r["帯上端"] - r["帯下端"], 6) for r in cal["rows"]}
    assert widths == {0.02}
    # 3 択がその帯どおりに動く
    assert vv.judge_3way_with_band(lo - 1e-9, (lo, hi)) == vv.JUDGE_STOP
    assert vv.judge_3way_with_band(lo, (lo, hi)) == vv.JUDGE_UNKNOWN
    assert vv.judge_3way_with_band(hi, (lo, hi)) == vv.JUDGE_CONTINUE
    assert vv.judge_3way_with_band(float("nan"), (lo, hi)) == vv.JUDGE_UNKNOWN


def test_calibration_band_is_empty_when_every_bin_is_distinguishable():
    """どの帯も基準率と 2 SE で区別できる場合、「わからない」の帯は作らない
    (規則を緩めて無理に作らない)。"""
    prob = np.concatenate([np.full(5000, 0.05), np.full(5000, 0.95)])
    y = np.concatenate([np.zeros(5000), np.ones(5000)])
    cal = vv.calibration_table(prob, y, step=vv.BAND_STEP)
    assert cal["帯"] is None
    assert {r["区分"] for r in cal["rows"]} <= {vv.JUDGE_STOP, vv.JUDGE_CONTINUE}


def test_two_value_threshold_uses_the_front_half_base_rate():
    assert vv.judge_2way_with_threshold(0.55, 0.5476) == vv.JUDGE_CONTINUE
    assert vv.judge_2way_with_threshold(0.5475, 0.5476) == vv.JUDGE_STOP
    assert vv.judge_2way_with_threshold(None, 0.5476) == vv.JUDGE_UNKNOWN
    # 完全な判断は事後の**値段の**ラベルをそのまま使う(参照点。損益の上限ではない)
    assert vv.judge_perfect_value(1) == vv.JUDGE_CONTINUE
    assert vv.judge_perfect_value(0) == vv.JUDGE_STOP
    assert vv.judge_perfect_value("") == vv.JUDGE_UNKNOWN


# ---------------------------------------------------------------------------
# (3) 費用 = c × 建玉の回数(型 B のドテン 1 回 = c)
# ---------------------------------------------------------------------------
def test_cost_is_c_times_number_of_entries_and_a_flip_costs_one_c():
    c = 1.7869

    def price_fn(t_ms):
        return 100.0 + t_ms / 1.0e7, t_ms

    # 型 B・止まる → 続く: 逆張りで入って 1 回ドテン。建玉の回数 = 2
    #   = 作る(c/2)+ ドテン(閉じる c/2 + 作る c/2 = c)+ 出口で閉じる(c/2) = 2c。
    prints = [{"print_id": "a", "ts_ms": 0, "side": "SELL"},
              {"print_id": "b", "ts_ms": 15_000, "side": "SELL"}]
    judgments = [vv.JUDGE_STOP, vv.JUDGE_CONTINUE]
    end = 15_000 + vv.CASCADE_END_GAP_S * 1000
    res = sp.simulate_cascade(prints, judgments, -1.0, vv.TYPE_B, 0, price_fn, end)
    assert res["n_entries"] == 2

    rows = [{"bundle_id": "x", "day": "2023-07-01", "side": "SELL",
             "連鎖の大きさ": "2件", "n_prints": 2, "方策": "logistic_3択", "型": vv.TYPE_B,
             "遅れ_秒": 1, "pnl_bp": res["pnl_bp"], "建玉の回数": res["n_entries"],
             "保有秒": res["hold_seconds"], "入った": 1, "欠測": 0,
             "最初に入った位置": "1件目で入った"}]
    cdf = vv.apply_cost(rows, c)
    assert float(cdf["pnl_bp"].iloc[0]) == pytest.approx(res["pnl_bp"] - 2 * c)
    # 片道(建玉 1 回)なら c 1 つぶん
    rows1 = [dict(rows[0], 建玉の回数=1)]
    cdf1 = vv.apply_cost(rows1, c)
    assert float(cdf1["pnl_bp"].iloc[0]) == pytest.approx(res["pnl_bp"] - c)
    # 入らなかった連鎖(建玉 0 回)は費用も 0
    rows0 = [dict(rows[0], 建玉の回数=0, pnl_bp=0.0, 入った=0)]
    assert float(vv.apply_cost(rows0, c)["pnl_bp"].iloc[0]) == pytest.approx(0.0)
    # ② は連鎖 1 本 = 建玉 1 回
    times, prices = _fake_prices(n=1200, slope=0.001)
    r = vv.simulate_reverse_entry(prints, -1.0, 0, vv.EXIT_LEVELS[0], None, 1,
                                  times, prices)
    assert r["建玉の回数"] == 1


# ---------------------------------------------------------------------------
# (4) 損切り・出口 3 種の約定が ts + d 以後(合成)
# ---------------------------------------------------------------------------
def test_exit_three_rules_and_stop_fill_at_or_after_ts_plus_delay():
    delay = 1
    prints = [{"print_id": "a", "ts_ms": 10_000, "side": "SELL"},
              {"print_id": "b", "ts_ms": 40_000, "side": "SELL"}]
    # 値段が上がる列(SELL の清算 → 逆張り = 買い建玉 → 勝つ。損切りは掛からない)
    times, prices = _fake_prices(n=1200, slope=0.01)
    for level, want_exit in (
            (vv.EXIT_LEVELS[0], 40_000 + 60_000),
            (vv.EXIT_LEVELS[1], 40_000 + 300_000),
            (vv.EXIT_LEVELS[2], 10_000 + 300_000)):
        assert vv.exit_ts_of(prints, 0, level) == want_exit
        r = vv.simulate_reverse_entry(prints, -1.0, 0, level, None, delay,
                                      times, prices)
        assert r["入りの目標時刻"] == 10_000 + delay * 1000
        assert r["入りの約定時刻"] >= r["入りの目標時刻"]
        assert r["出の目標時刻"] == want_exit + delay * 1000
        assert r["出の約定時刻"] >= r["出の目標時刻"]
        assert r["出口の理由"] == level
        assert r["損切りの引き金時刻"] is None

    # 値段が下がる列 → 買い建玉が含み損。20 bp の損切りが掛かる
    times2, prices2 = _fake_prices(n=1200, slope=-0.05)
    r2 = vv.simulate_reverse_entry(prints, -1.0, 0, vv.EXIT_LEVELS[1], 20.0, delay,
                                   times2, prices2)
    assert r2["出口の理由"].startswith("損切り")
    trig = r2["損切りの引き金時刻"]
    assert trig is not None
    # 引き金は「含み損が閾値に達した最初の約定」
    p_in = 100.0 + (-0.05) * (r2["入りの約定時刻"] / 1000.0)
    i_trig = int(np.searchsorted(times2, trig, side="left"))
    loss = (prices2[i_trig] - p_in) / p_in * 1e4          # 建玉は +1(買い)
    assert loss <= -20.0
    prev = (prices2[i_trig - 1] - p_in) / p_in * 1e4
    assert prev > -20.0
    # 約定は「引き金の時刻 + d」以後
    assert r2["出の目標時刻"] == trig + delay * 1000
    assert r2["出の約定時刻"] >= r2["出の目標時刻"]
    # 50 bp の方が遅く(または同時に)引ける
    r3 = vv.simulate_reverse_entry(prints, -1.0, 0, vv.EXIT_LEVELS[1], 50.0, delay,
                                   times2, prices2)
    assert r3["損切りの引き金時刻"] >= trig
    # 損切りが掛からない列では 3 種の出口のまま
    r4 = vv.simulate_reverse_entry(prints, -1.0, 0, vv.EXIT_LEVELS[1], 50.0, delay,
                                   times, prices)
    assert r4["損切りの引き金時刻"] is None


def test_entry_position_knob_skips_chains_that_are_too_short():
    times, prices = _fake_prices(n=1200, slope=0.01)
    prints = [{"print_id": "a", "ts_ms": 10_000, "side": "SELL"}]
    assert vv.simulate_reverse_entry(prints, -1.0, 0, vv.EXIT_LEVELS[0], None, 1,
                                     times, prices)["入った"] == 1
    for ei in (1, 2):
        r = vv.simulate_reverse_entry(prints, -1.0, ei, vv.EXIT_LEVELS[0], None, 1,
                                      times, prices)
        assert r["入った"] == 0 and r["出口の理由"] == "入らない"


# ---------------------------------------------------------------------------
# (5) 格子の列挙が 189
# ---------------------------------------------------------------------------
def test_grid_enumerates_189_distinct_combinations():
    combos = vv.grid_combos()
    assert len(combos) == 189 == vv.N_GRID
    assert len(ENTRY := vv.ENTRY_POS_LEVELS) == 3
    assert len(vv.COND_LEVELS) == 7
    assert len(vv.EXIT_LEVELS) == 3
    assert len(vv.STOP_LEVELS) == 3
    keys = {(c["入る位置"], c["入る条件"], c["出口"], c["損切り"]) for c in combos}
    assert len(keys) == 189
    assert set(ENTRY) == {c["入る位置"] for c in combos}


@needs_data
def test_grid_table_has_189_rows_on_a_small_slice():
    prints = vv.load_stage1_prints()
    days = sorted(set(prints["day"].astype(str)))[:2]
    sub = prints[prints["day"].astype(str).isin(days)]
    cas = vv.cascades_from_prints(sub)
    cache = vv.WindowCache(vv.DATA_ROOT)
    per_chain = vv.run_grid_core(cas, cache, vv.GRID_DELAY_S)
    cuts, _note = vv.condition_cuts(prints)
    rows = vv.build_grid_table(per_chain, cuts, 1.7869, days[0])
    assert len(rows) == 189
    for r in rows:
        assert r["建玉の回数"] == r["入った本数"]     # ② は連鎖 1 本 = 建玉 1 回


# ---------------------------------------------------------------------------
# (6) 選ぶ規則 (a)(b) と「無かった」の分岐
# ---------------------------------------------------------------------------
def _grid_row(total, med, h1, h2, **kw):
    base = {"入る位置": vv.ENTRY_POS_LEVELS[0], "入る条件": "なし",
            "出口": vv.EXIT_LEVELS[0], "損切り": "なし",
            "総収支_bp": total, "中央値_入った本のみ": med, "中央値_0含む": med,
            "前半の前_総収支_bp": h1, "前半の後_総収支_bp": h2, "入った本数": 10}
    base.update(kw)
    return base


def test_selection_rule_requires_both_halves_positive_and_positive_median():
    rows = [
        _grid_row(100.0, 1.0, 60.0, 40.0),                       # 規則を満たす
        _grid_row(200.0, 1.0, -10.0, 210.0, 出口=vv.EXIT_LEVELS[1]),   # (a) を満たさない
        _grid_row(300.0, -1.0, 150.0, 150.0, 出口=vv.EXIT_LEVELS[2]),  # (b) を満たさない
        _grid_row(150.0, 0.5, 80.0, 70.0, 損切り=vv.STOP_LEVELS[1]),   # 規則を満たす
    ]
    got = vv.select_combo(rows)
    assert got["選ばれた"] is True
    assert got["規則を満たした組の数"] == 2
    assert got["総収支_bp"] == 150.0          # 満たす組の中で総収支が最大
    assert got["組"]["損切り"] == vv.STOP_LEVELS[1]


def test_grid_selected_json_keeps_the_rule_and_the_day_breakdown():
    """`grid_selected.json` は、選ぶ規則・選んだ組・0 含みで読んだ場合・上位 5 組・
    日ごとの内訳(素 / 素+損切り / 選んだ組)を持つ。"""
    rows = [_grid_row(100.0, 1.0, 60.0, 40.0, **c) for c in vv.grid_combos()]
    chosen = vv.select_combo(rows)
    per_chain = {}
    sel = vv.build_grid_selected(rows, chosen, vv.select_combo(rows, "中央値_0含む"),
                                 per_chain, {}, 1.7869, "2023-10-21")
    assert sel["格子の組数"] == 189
    assert len(sel["総収支の上位 5 組"]) == 5
    bd = sel["日ごとの内訳(なぜを読むため)"]
    assert {"素(全部逆張り)", "素 + 損切り20bp", "素 + 損切り50bp", "選んだ組",
            "選んだ組 + 損切り20bp"} == set(bd)
    assert all(v["入った本数"] == 0 for v in bd.values())   # per_chain が空なので 0


def test_selection_rule_reports_when_no_combination_qualifies():
    rows = [_grid_row(100.0, -1.0, 60.0, 40.0),
            _grid_row(200.0, 1.0, -10.0, 210.0, 出口=vv.EXIT_LEVELS[1]),
            _grid_row(50.0, 1.0, 60.0, -10.0, 出口=vv.EXIT_LEVELS[2])]
    got = vv.select_combo(rows)
    assert got["選ばれた"] is False
    assert got["規則を満たした組の数"] == 0
    assert got["組"] is None
    # 選べなければ 1 ノブずつの寄与も作らない(規則を緩めない)
    assert vv.knob_contribution(rows, got) == []


def test_knob_contribution_covers_every_level_of_every_knob():
    rows = []
    for c in vv.grid_combos():
        rows.append(_grid_row(1.0, 1.0, 1.0, 1.0, **c))
    # 1 組だけ総収支を高くして、それが選ばれるようにする
    rows[100]["総収支_bp"] = 999.0
    chosen = vv.select_combo(rows)
    assert chosen["選ばれた"] is True
    kb = vv.knob_contribution(rows, chosen)
    assert len(kb) == 3 + 7 + 3 + 3
    assert {r["ノブ"] for r in kb} == {"入る位置", "入る条件", "出口", "損切り"}
    same = [r for r in kb if r["水準"] == r["選んだ組の水準"]]
    assert all(r["選んだ組との差_bp"] == 0.0 for r in same)


# ---------------------------------------------------------------------------
# (7) `stage1` が後半の行で例外
# ---------------------------------------------------------------------------
def test_stage1_refuses_the_back_half():
    with pytest.raises(RuntimeError):
        vv.run_stage1(half=vv.BACK_HALF)
    with pytest.raises(RuntimeError):
        vv.require_front_half(vv.BACK_HALF)
    assert vv.require_front_half(vv.FRONT_HALF) == vv.FRONT_HALF


def test_assert_front_half_only_raises_on_any_back_half_row():
    ok = pd.DataFrame({"half": ["前半", "前半"], "x": [1, 2]})
    assert vv.assert_front_half_only(ok, "t") is ok
    bad = pd.DataFrame({"half": ["前半", "後半"], "x": [1, 2]})
    with pytest.raises(RuntimeError):
        vv.assert_front_half_only(bad, "t")
    with pytest.raises(RuntimeError):
        vv.assert_front_half_only(pd.DataFrame({"x": [1]}), "t")


@needs_data
def test_stage1_loader_reads_front_half_rows_only():
    df = vv.load_stage1_prints()
    assert (df["half"] == vv.FRONT_HALF).all()
    assert (df["kind"] == "print").all()      # q7_candidate の行は読まない
    assert len(df) == 21838
    assert df["bundle_id"].nunique() == 8931


# ---------------------------------------------------------------------------
# (8) 判定語が出力の文字列に無い
# ---------------------------------------------------------------------------
def test_check_no_banned_raises_on_verdict_words():
    for w in vv.cont.BANNED_WORDS:
        with pytest.raises(SystemExit):
            vv.check_no_banned(f"これは{w}です", "test")
    vv.check_no_banned("判定語の無い普通の文", "test")


def test_no_verdict_words_in_outputs_if_present():
    for path in (vv.DEFAULT_OUT / "tables.md", vv.DEFAULT_OUT / "summary.json",
                 vv.SPREAD_DIR / "tables.md", vv.SPREAD_DIR / "summary.json",
                 vv.CONFIG_VALUE_FIRST, vv.CONFIG_VALUE_CHAIN,
                 ROOT / "docs" / "PHASE2" / "O3C" / "SIGNAL"
                 / "VALUE_STAGE1_REPORT_2026-09-21.md"):
        if not path.exists():
            continue
        txt = path.read_text(encoding="utf-8")
        for w in vv.cont.BANNED_WORDS:
            assert w not in txt, (path.name, w)


# ---------------------------------------------------------------------------
# (9) `paper_logs/` を開かない
# ---------------------------------------------------------------------------
def test_sources_never_open_paper_logs():
    for name in ("o3c_signal_value.py", "o3c_bitflyer_spread.py"):
        src = (ROOT / "scripts" / name).read_text().splitlines()
        hits = [ln for ln in src if "paper_logs" in ln]
        assert all(ln.lstrip().startswith(("#", "*", '"""'))
                   or "開かない" in ln for ln in hits), (name, hits)


def test_sources_never_call_jev():
    for name in ("o3c_signal_value.py", "o3c_bitflyer_spread.py"):
        src = (ROOT / "scripts" / name).read_text()
        assert "JevClient(" not in src
        assert ".evaluate(" not in src


# ---------------------------------------------------------------------------
# (10) 実効スプレッドの対の作り方(合成の約定列)
# ---------------------------------------------------------------------------
def test_effective_spread_pairs_on_synthetic_trades():
    #        時刻(ms):   0     500   2000   2300   2400
    #        向き:      buy   sell   buy    buy    sell
    t = np.array([0, 500, 2000, 2300, 2400], dtype=np.int64)
    p = np.array([100.05, 99.95, 100.10, 100.10, 100.00])
    s = np.array([1, -1, 1, 1, -1], dtype=np.int8)
    ts, bp = bsp.effective_spread_pairs(t, p, s)
    # 対になるのは (0,500)= 向きが違い 500 ms、(2300,2400)= 向きが違い 100 ms。
    # (500,2000) は向きが違うが 1,500 ms 空いているので対にしない。
    # (2000,2300) は同じ向きなので対にしない。
    assert list(ts) == [0, 2300]
    mid1 = (100.05 + 99.95) / 2
    assert bp[0] == pytest.approx((100.05 - 99.95) / mid1 * 1e4)
    mid2 = (100.10 + 100.00) / 2
    assert bp[1] == pytest.approx((100.10 - 100.00) / mid2 * 1e4)
    # 約定が 1 件以下なら対は 0
    assert bsp.effective_spread_pairs(t[:1], p[:1], s[:1])[0].size == 0


def test_post_liquidation_window_is_t0_plus_1_to_5_seconds():
    pair_ts = np.array([0, 1_000, 3_000, 5_000, 5_001, 20_000], dtype=np.int64)
    liq = np.array([0], dtype=np.int64)
    m = bsp.mask_post_liquidation(pair_ts, liq)
    assert list(m) == [False, True, True, True, False, False]
    assert bsp.mask_post_liquidation(pair_ts, np.zeros(0, dtype=np.int64)).sum() == 0


def test_spread_tool_reads_only_the_timestamp_column_of_rows_continue():
    """清算の時刻以外(ラベル・価格・材料)を読まないことを、`usecols` の指定で確かめる。"""
    src = (ROOT / "scripts" / "o3c_bitflyer_spread.py").read_text()
    assert 'usecols=["kind", "day", "half", "ts_ms"]' in src
    assert "value_continuation_60" not in src
    assert "label_60" not in src


@needs_tardis
def test_spread_output_table_is_aggregates_only():
    path = vv.SPREAD_DIR / "spread_by_day.csv"
    if not path.exists():
        pytest.skip("費用の表がまだこの環境で作られていない")
    df = pd.read_csv(path)
    assert set(df.columns) == {"標本日", "半期", "区分", "対の数", "p25_bp", "p50_bp",
                               "p75_bp", "p90_bp", "参考_符号付きp50_bp",
                               "参考_正の対だけp50_bp", "負の対の割合"}
    assert (df["区分"].isin([bsp.SCOPE_ALL, bsp.SCOPE_POST_LIQ])).all()
    c_main, c_p75 = bsp.read_cost(vv.SPREAD_DIR)
    assert math.isfinite(c_main) and math.isfinite(c_p75)


# ---------------------------------------------------------------------------
# 合成の連鎖(状態機械・損切り・出口 3 種・費用の加算の道筋)と出力の形
# ---------------------------------------------------------------------------
def test_synthetic_traces_cover_state_machine_stops_exits_and_cost():
    rows = vv.build_synthetic_traces_value(2.0)
    kinds = {r["区分"] for r in rows}
    assert "①の状態機械(前段の合成3本)" in kinds
    assert any(k.startswith("②の格子") for k in kinds)
    grid_rows = [r for r in rows if r["区分"].startswith("②の格子")]
    assert len(grid_rows) == 2 * len(vv.EXIT_LEVELS) * len(vv.STOP_LEVELS)
    assert any("損切り" in str(r["出口の理由"]) for r in grid_rows)
    for lvl in vv.EXIT_LEVELS:
        assert any(r["出口の理由"] == lvl for r in grid_rows)
    # 費用の加算が道筋に出ている(費用なしの損益 − c × 建玉の回数)
    for r in grid_rows:
        gross = float(r["費用なしの損益_bp"])
        net = float(r["費用 c=2.0000 を引いた損益_bp"])
        assert net == pytest.approx(gross - 2.0 * int(r["建玉の回数"]), abs=1e-3)


@needs_data
def test_stage1_outputs_present_and_consistent_if_run():
    summary_path = vv.DEFAULT_OUT / "summary.json"
    if not summary_path.exists():
        pytest.skip("段1がまだこの環境で実行されていない")
    import json
    s = json.loads(summary_path.read_text(encoding="utf-8"))
    assert s["半期"] == vv.FRONT_HALF
    assert s["前半のプリント数"] == 21838
    assert s["前半の連鎖数"] == 8931
    assert s["②の格子"]["組数"] == 189
    assert s["値段のラベルの再計算"]["一致"] == s["値段のラベルの再計算"]["件数"]
    for name in ("grid.csv", "grid_selected.json", "knob_contrib.csv",
                 "calib_first.csv", "calib_chain.csv", "time_to_target.csv",
                 "dist_table.csv", "position_breakdown.csv", "judge_counts.csv",
                 "synthetic_traces.csv", "q5b_secs_firsthalf.csv", "summary.json",
                 "tables.md", "MD5SUMS"):
        assert (vv.DEFAULT_OUT / name).exists(), name
    assert len(pd.read_csv(vv.DEFAULT_OUT / "grid.csv")) == 189
    sel = json.loads((vv.DEFAULT_OUT / "grid_selected.json").read_text())
    assert sel["格子の組数"] == 189
    assert "日ごとの内訳(なぜを読むため)" in sel


def test_stage2_ran_exactly_once_and_kept_the_rows():
    """段2 は 2026-09-21 に**一度だけ**走った(オーナー承認 L-352)。
    出力があるなら、連鎖 1 本ごとの行と判断の行が残っていて、Q0 の MD5 照合が
    前段と一致していること。まだ走っていない環境では飛ばす。"""
    assert callable(vv.run_stage2)
    if not (vv.DEFAULT_OUT_STAGE2 / "cascades.csv.gz").exists():
        pytest.skip("段2 がまだこの環境で実行されていない")
    for name in ("cascades.csv.gz", "prints_policy.csv.gz", "q0_selfcheck.csv"):
        assert (vv.DEFAULT_OUT_STAGE2 / name).exists(), name
    q0 = pd.read_csv(vv.DEFAULT_OUT_STAGE2 / "q0_selfcheck.csv")
    d = dict(zip(q0["項目"], q0["値"]))
    assert str(d["前段と同一か"]) == "1"
    assert str(d["この単位にだけある bundle_id"]) == "0"
    assert str(d["前段にだけある bundle_id"]) == "0"

# ===========================================================================
# 反証者レビュー9(2026-09-21)を受けた直しの試験
# ===========================================================================

# --- 致命-1: 連鎖 1 本ごとの行 ---------------------------------------------
def test_cascade_rows_file_has_the_required_columns_and_cost_dimension():
    policy_rows = [{
        "bundle_id": "b1", "day": "2023-07-01", "side": "SELL", "連鎖の大きさ": "2件",
        "n_prints": 2, "方策": "logistic_3択", "型": vv.TYPE_B, "遅れ_秒": 1,
        "pnl_bp": 10.0, "建玉の回数": 2, "保有秒": 90.0,
        "入りの約定時刻_ms": 1_000, "出の約定時刻_ms": 91_000, "入った": 1,
        "最初に入った位置": "1件目で入った", "出口の理由": "連鎖の終わり+d"}]
    opt_rows = {"②opt": [{
        "bundle_id": "b1", "day": "2023-07-01", "side": "SELL", "連鎖の大きさ": "2件",
        "n_prints": 2, "pnl_bp": 4.0, "建玉の回数": 1, "保有秒": 300.0,
        "入りの約定時刻": 1_000, "出の約定時刻": 301_000, "入った": 1,
        "出口の理由": "最後のプリント+300秒+d"}]}
    costs = {vv.COST_NONE: 0.0, vv.COST_MAIN: 2.0, vv.COST_P75: 4.0}
    rows = vv.build_cascade_rows_file(policy_rows, costs, opt_rows)
    assert len(rows) == 2 * len(costs)
    for r in rows:
        assert list(r.keys()) == list(vv.CASCADE_COLUMNS)
    need = {"bundle_id", "day", "side", "連鎖の大きさ", "n_prints", "方策", "型",
            "遅れ_秒", "費用の通り", "pnl_bp", "pnl_net_bp", "建玉の回数", "保有秒",
            "入りの目標時刻_ms", "入りの約定時刻_ms", "出の約定時刻_ms", "入った",
            "最初に入った位置", "出口の理由"}
    assert need == set(vv.CASCADE_COLUMNS)
    # 費用は c × 建玉の回数
    main = [r for r in rows if r["費用の通り"] == vv.COST_MAIN and r["方策"] != "②opt"]
    assert main[0]["pnl_net_bp"] == pytest.approx(10.0 - 2.0 * 2)
    opt = [r for r in rows if r["費用の通り"] == vv.COST_MAIN and r["方策"] == "②opt"]
    assert opt[0]["pnl_net_bp"] == pytest.approx(4.0 - 2.0 * 1)
    assert opt[0]["入りの約定時刻_ms"] == 1_000


def test_entry_exit_fill_times_reconstructs_absolute_fill_times():
    P = vv.sp
    prints = [{"print_id": "a", "ts_ms": 0, "side": "SELL"},
              {"print_id": "b", "ts_ms": 15_000, "side": "SELL"}]
    times = np.array([0, 1_500, 16_500, 75_500, 120_000], dtype=np.int64)
    prices = np.array([100.0, 100.1, 100.2, 100.3, 100.4])

    def price_fn(t_ms):
        return vv.price_at_or_after(times, prices, int(t_ms))

    end = 15_000 + vv.CASCADE_END_GAP_S * 1000
    res = P.simulate_cascade(prints, [vv.JUDGE_STOP, vv.JUDGE_CONTINUE], -1.0,
                             vv.TYPE_B, 1, price_fn, end)
    t_in, t_out = vv.entry_exit_fill_times(res, 1)
    assert t_in == 1_500                 # 0 + 1 秒 -> 次の約定 1,500 ms
    # 出口の目標は 75,000 + 1 秒 = 76,000 ms。76,000 ms 以後の最初の約定は 120,000 ms
    # (75,500 ms の約定は目標より前なので取らない)。
    assert t_out == 120_000


# --- 致命-3: 露出(同時建玉・保有時間)-------------------------------------
def test_max_concurrent_counts_overlapping_positions():
    assert vv.max_concurrent([]) == 0
    assert vv.max_concurrent([(0, 10), (10, 20)]) == 1          # 端が触るだけ
    assert vv.max_concurrent([(0, 10), (5, 20)]) == 2
    assert vv.max_concurrent([(0, 30), (5, 20), (10, 15), (12, 14)]) == 4
    assert vv.max_concurrent([(0, 10), (None, 5)]) == 1         # 欠けた区間は飛ばす


def test_exposure_of_computes_hours_and_bp_per_hour():
    rows = [{"pnl_net_bp": 36.0, "保有秒": 1800.0, "入りの約定時刻": 0,
             "出の約定時刻": 1_800_000},
            {"pnl_net_bp": 36.0, "保有秒": 1800.0, "入りの約定時刻": 900_000,
             "出の約定時刻": 2_700_000}]
    e = vv.exposure_of(rows)
    assert e["合計保有時間_時間"] == pytest.approx(1.0)
    assert e["保有1時間あたりの収支_bp/h"] == pytest.approx(72.0)
    assert e["同時建玉の最大_本"] == 2
    assert e["平均保有秒"] == pytest.approx(1800.0)
    assert vv.exposure_of([])["同時建玉の最大_本"] == 0


def test_grid_rows_carry_the_exposure_columns_and_empty_reason():
    per_chain = {}
    times = np.arange(0, 1_200_000, 1_000, dtype=np.int64)
    prices = 100.0 + times / 1.0e7
    for i in range(4):
        prints = [{"print_id": f"p{i}{j}", "ts_ms": 10_000 + j * 20_000,
                   "side": "SELL", "day": "2023-07-01",
                   "mat12_notional_over_max_recent_print": ("" if j == 0 else 5.0),
                   "mat14_trade_count_60s": 2000.0,
                   "mat15_burst_ratio_10s_over_60s": 0.9} for j in range(3)]
        res = {}
        for ei in range(3):
            for ex in vv.EXIT_LEVELS:
                for st in vv.STOP_LEVELS:
                    res[(ei, ex, st)] = vv.simulate_reverse_entry(
                        prints, -1.0, ei, ex, vv.STOP_BP[st], 1, times, prices)
        per_chain[f"b{i}"] = {"day": "2023-07-01", "n_prints": 3, "結果": res,
                              "entry_rows": prints}
    cuts = {"材料12≥p75": ("mat12_notional_over_max_recent_print", 1.0),
            "材料12≥p90": ("mat12_notional_over_max_recent_print", 2.0),
            "材料14≥p75": ("mat14_trade_count_60s", 1.0),
            "材料14≥p90": ("mat14_trade_count_60s", 2.0),
            "材料15≥p75": ("mat15_burst_ratio_10s_over_60s", 0.1),
            "材料15≥p90": ("mat15_burst_ratio_10s_over_60s", 0.2)}
    rows = vv.build_grid_table(per_chain, cuts, 1.0, "2023-07-01")
    assert len(rows) == 189
    for col in ("合計保有時間_時間", "保有1時間あたりの収支_bp/h", "同時建玉の最大_本",
                "空の理由"):
        assert col in rows[0]
    # 材料12 は 1 件目で欠測なので「1件目から × 材料12」は構造的に空(D-4)
    empty = [r for r in rows if r["入った本数"] == 0]
    assert len(empty) == 18
    assert all(r["入る位置"] == "1件目から" and r["入る条件"].startswith("材料12")
               for r in empty)
    assert all("構造的に空" in r["空の理由"] for r in empty)
    assert all(r["空の理由"] == "" for r in rows if r["入った本数"] > 0)
    # 露出の表(3 通り)
    ex = vv.build_exposure_table(per_chain, cuts, 1.0,
                                 {"素": dict(vv.PLAIN_COMBO)})
    assert len(ex) == 1 and ex[0]["入った本数"] == 4


def test_knob_contribution_carries_hold_time_columns():
    rows = [_grid_row(1.0, 1.0, 1.0, 1.0, **c) for c in vv.grid_combos()]
    for r in rows:
        r["合計保有時間_時間"] = 2.0
        r["保有1時間あたりの収支_bp/h"] = 0.5
        r["同時建玉の最大_本"] = 3
    rows[5]["総収支_bp"] = 99.0
    kb = vv.knob_contribution(rows, vv.select_combo(rows))
    assert kb and all("合計保有時間_時間" in r and "同時建玉の最大_本" in r for r in kb)


# --- 致命-2: 母集団と日ブロック分割 ----------------------------------------
def test_day_block_folds_never_split_a_day_and_are_deterministic():
    days = np.array([f"2023-{1 + (i // 28):02d}-{1 + (i % 28):02d}"
                     for i in range(140)], dtype=object)
    rows = np.repeat(days, 3)
    folds = vv.day_block_folds(rows, n_folds=5, seed=20260920)
    assert len(folds) == 5
    assert sorted(np.concatenate(folds).tolist()) == list(range(rows.size))
    day_of_fold = {}
    for fi, f in enumerate(folds):
        for d in set(rows[f].tolist()):
            assert d not in day_of_fold, d      # 同じ日が 2 つの群に跨らない
            day_of_fold[d] = fi
    assert len(day_of_fold) == 140
    again = vv.day_block_folds(rows, n_folds=5, seed=20260920)
    assert [f.tolist() for f in again] == [f.tolist() for f in folds]
    other = vv.day_block_folds(rows, n_folds=5, seed=1)
    assert [f.tolist() for f in other] != [f.tolist() for f in folds]


def test_run_scene_day_blocked_reports_the_day_block_split():
    rng = np.random.default_rng(7)
    n = 900
    days = np.array([f"2023-07-{1 + (i % 25):02d}" for i in range(n)], dtype=object)
    x = rng.uniform(0, 1, n)
    df = pd.DataFrame({"print_id": [f"p{i}" for i in range(n)], "day": days,
                       "cand_14": x, "cand_8": rng.uniform(0, 1, n),
                       vv.LABEL_VALUE: (rng.uniform(0, 1, n) < x).astype(float)})
    res = vv.run_scene_day_blocked(df, ["cand_14", "cand_8"], "試験")
    assert res["report"]["分割"].startswith("日でブロック")
    assert sum(res["report"]["分割の日数"]) == 25
    assert res["n"] == n
    assert set(res["oof_by_pid"]) == set(df["print_id"])


@needs_data
def test_scene_frames_exclude_prints_without_a_bundle():
    first, chain, outside = vv.build_scene_frames()
    assert len(first) == 8931          # 連鎖の数と一致(1 連鎖に 1 件目が 1 つ)
    assert len(chain) == 11866
    assert len(outside) == 1041
    assert first["bundle_id"].notna().all()
    assert chain["bundle_id"].notna().all()
    assert outside["bundle_id"].isna().all()
    assert len(first) + len(chain) == 20797
    q0 = vv.outside_bundle_rows(outside)
    assert q0[0]["件数"] == 1041
    assert q0[0]["値段のラベルの割合"] > 0.9


@needs_data
def test_cascades_from_prints_reports_the_rows_it_drops():
    df = vv.load_stage1_prints()
    assert vv.bundle_drop_count(df) == 1041
    cas = vv.cascades_from_prints(df, "試験")
    assert len(cas) == 8931
    assert sum(len(v) for v in cas.values()) == 20797


@needs_data
def test_condition_cuts_use_the_bundle_population():
    df = vv.load_stage1_prints()
    cuts, note = vv.condition_cuts(df)
    assert note["材料12"]["母数"] == 20797
    assert note["材料14"]["母数"] == 20797
    # 材料12 は 1 件目で全欠測なので有限値は連鎖の中の件数
    assert note["材料12"]["有限値の件数"] == 11866
    assert note["材料14"]["有限値の件数"] <= 20797
    assert set(cuts) == {f"{m}≥{q}" for m in ("材料12", "材料14", "材料15")
                         for q in ("p75", "p90")}


# --- D-1 / D-2: 費用 --------------------------------------------------------
def test_spread_main_quantiles_are_absolute_values():
    vals = np.array([-3.0, -1.0, 1.0, 2.0, 5.0])
    row = bsp._dist_row("2023-07-01", bsp.SCOPE_ALL, vals, "前半")
    assert row["p50_bp"] == pytest.approx(float(np.percentile(np.abs(vals), 50)))
    assert row["p50_bp"] == pytest.approx(2.0)          # |{1,1,2,3,5}| の中央値
    assert row["参考_符号付きp50_bp"] == pytest.approx(1.0)
    assert row["参考_正の対だけp50_bp"] == pytest.approx(2.0)
    assert row["負の対の割合"] == pytest.approx(0.4)
    # 絶対値の中央値は符号付きの中央値以上(負の対が費用を小さく見せない)
    assert row["p50_bp"] >= row["参考_符号付きp50_bp"]


def test_post_liquidation_window_takes_every_liquidation_not_only_the_latest():
    # 清算が 0 ms と 4,500 ms にある。対が 4,600 ms のとき、直前の清算(4,500)からは
    # 100 ms しか経っていないが、最初の清算(0)からは 4,600 ms = 窓の中。
    liq = np.array([0, 4_500], dtype=np.int64)
    pair_ts = np.array([4_600], dtype=np.int64)
    assert bool(bsp.mask_post_liquidation(pair_ts, liq)[0]) is True
    # 窓の外(どの清算からも 5 秒超 / 1 秒未満)は落ちる
    assert bool(bsp.mask_post_liquidation(np.array([200], dtype=np.int64),
                                          np.array([0], dtype=np.int64))[0]) is False
    assert bool(bsp.mask_post_liquidation(np.array([20_000], dtype=np.int64),
                                          np.array([0], dtype=np.int64))[0]) is False
    # 直前だけを見る実装なら落ちる対を拾うので、件数は減らない
    many = np.array([0, 100, 200, 300, 4_500], dtype=np.int64)
    pts = np.array([1_500, 4_600, 5_200], dtype=np.int64)
    assert bsp.mask_post_liquidation(pts, many).sum() == 3


@needs_tardis
def test_read_cost_returns_the_absolute_quantiles():
    if not (vv.SPREAD_DIR / "spread_by_day.csv").exists():
        pytest.skip("費用の表がまだこの環境で作られていない")
    df = pd.read_csv(vv.SPREAD_DIR / "spread_by_day.csv")
    pool = df[(df["標本日"] == bsp.POOL_LABEL) & (df["区分"] == bsp.SCOPE_POST_LIQ)]
    c_main, c_p75 = bsp.read_cost(vv.SPREAD_DIR)
    assert c_main == pytest.approx(float(pool["p50_bp"].iloc[0]))
    assert c_main >= float(pool["参考_符号付きp50_bp"].iloc[0])
    assert c_p75 == pytest.approx(float(pool["p75_bp"].iloc[0]))


# --- D-3: 到達が遅れより早くても取れないとは限らない ------------------------
def test_residual_move_after_delay_measures_from_the_delayed_fill():
    times = np.arange(0, 120_000, 1_000, dtype=np.int64)
    prices = np.full(times.size, 100.0)
    prices[0:] = 100.0
    prices[1:] = 100.0 * (1 + 8e-4)      # 1 秒で +8 bp(遅れの前に到達)
    prices[30:] = 100.0 * (1 + 20e-4)    # そこから更に +12 bp
    # 遅れ 1 秒の約定は 1,000 ms の値段。そこから t0+60 秒までの最大順行
    r = vv.residual_move_after_delay(times, prices, 0, 1.0, delay_s=1)
    p_in = prices[1]
    want = (prices[59] - p_in) / p_in * 1e4
    assert r == pytest.approx(want, rel=1e-6)
    assert r > 0


def test_time_to_target_table_has_the_residual_columns():
    rows = [
        {"到達秒": 0.5, "再計算したラベル": 1.0, "位置": vv.POS_1ST,
         "遅れ1秒の約定からの最大順行_bp": 20.0},
        {"到達秒": 0.8, "再計算したラベル": 1.0, "位置": vv.POS_1ST,
         "遅れ1秒の約定からの最大順行_bp": 1.0},
        {"到達秒": 9.0, "再計算したラベル": 1.0, "位置": vv.POS_CHAIN,
         "遅れ1秒の約定からの最大順行_bp": 30.0},
    ]
    tbl = vv.time_to_target_table(rows)
    whole = [r for r in tbl if r["場面"] == "全体"][0]
    assert whole["到達1秒未満の件数"] == 2
    assert whole["到達1秒未満_遅れ1秒の約定からなお5bp以上の割合"] == pytest.approx(0.5)
    assert whole["到達1秒以上の件数"] == 1
    assert whole["到達1秒以上_遅れ1秒の約定からなお5bp以上の割合"] == pytest.approx(1.0)


# --- D-6: 段2 の停止と dry-run ---------------------------------------------
def test_require_materials_cover_stops_on_a_missing_print_id():
    vv.require_materials_cover({"a", "b"}, {"a", "b", "c"}, "試験")
    with pytest.raises(RuntimeError):
        vv.require_materials_cover({"a", "b"}, {"a"}, "試験")


def test_add_n2_by_day_clears_the_day_cache():
    """D-6(b): 日が変わるたびに約定のキャッシュを空にする(228 日ぶんを溜めない)。"""
    class FakeSB:
        def __init__(self):
            self._window_cache = {}
            self._raw_trade_cache = {}
            self.seen = []
    calls = []

    def fake_add(sb, g):
        sb._window_cache[str(g["day"].iloc[0])] = ("x",)
        calls.append(len(sb._window_cache))
        return g
    orig = vv.lg.add_n2_column
    vv.lg.add_n2_column = fake_add
    try:
        df = pd.DataFrame({"day": ["d1", "d1", "d2", "d3"],
                           "print_id": ["a", "b", "c", "d"]})
        out = vv.add_n2_by_day(FakeSB(), df)
    finally:
        vv.lg.add_n2_column = orig
    assert len(out) == 4
    assert calls == [1, 1, 1]        # 毎回 1 日ぶんしか残らない


def test_stage2_dry_run_builds_every_table_without_reading_the_back_half(tmp_path):
    if not (vv.DEFAULT_OUT / "summary.json").exists():
        pytest.skip("段1 がまだこの環境で実行されていない")
    if not (vv.SPREAD_DIR / "spread_by_day.csv").exists():
        pytest.skip("費用の表がまだこの環境で作られていない")
    out = tmp_path / "dry"
    summary = vv.run_stage2(out_dir=out, dry_run=True)
    assert summary["段"].startswith("段2(dry-run")
    for name in ("q0_selfcheck.csv", "dist_table.csv", "q4_main.csv",
                 "q4_pair_diff.csv", "q4_by_day.csv", "q4_by_side.csv",
                 "q4_by_size.csv", "q4_by_position.csv", "q4_exposure.csv",
                 "cascades.csv.gz", "tables.md", "summary.json", "MD5SUMS"):
        assert (out / name).exists(), name
    main = pd.read_csv(out / "q4_main.csv")
    assert {"①3択A", "①3択B", "全部逆張り(素)", "前段の3択(清算)A",
            "完全な判断(値段)A"} <= set(main["方策"])
    # dry-run は本物の段2 の出力先には書かない
    assert out != vv.DEFAULT_OUT_STAGE2


def test_synthetic_stage2_inputs_are_synthetic_only():
    syn = vv.synthetic_stage2_inputs()
    assert set(syn["cascades"]) == {"dry_0001", "dry_0002", "dry_0003"}
    ids = [pr["print_id"] for v in syn["cascades"].values() for pr in v]
    assert all(i.startswith("d") for i in ids)
    cache = vv.SyntheticCache(syn["times"], syn["prices"])
    px, t = cache.raw_at_or_after(10_500)
    assert t == 11_000 and px > 0


# --- Q4 の対差と参照 2 本 ---------------------------------------------------
def test_pair_diff_rows_pair_on_the_same_bundle_id():
    lines = {
        "A": [{"bundle_id": "b1", "pnl_net_bp": 5.0},
              {"bundle_id": "b2", "pnl_net_bp": -1.0},
              {"bundle_id": "b3", "pnl_net_bp": 2.0}],
        "B": [{"bundle_id": "b1", "pnl_net_bp": 1.0},
              {"bundle_id": "b2", "pnl_net_bp": -1.0}],
    }
    rows = vv.build_pair_diff_rows(lines, (("A", "B"), ("A", "C")))
    a_b = [r for r in rows if r["対差"] == "A − B"
           and r["母集団"] == "両方入った連鎖だけ"][0]
    assert a_b["対の数"] == 2                      # b3 は片側に無いので対にしない
    assert a_b["対差の合計_bp"] == pytest.approx(4.0)
    assert a_b["対差が0の本数"] == 1
    a_c = [r for r in rows if r["対差"] == "A − C"]
    assert len(a_c) == 2 and all(r["対の数"] == 0 and "備考" in r for r in a_c)


def test_reference_policies_use_the_prior_liquidation_bands_and_perfect_judgment():
    prints = [{"print_id": "a", "ts_ms": 0, "side": "SELL"},
              {"print_id": "b", "ts_ms": 10_000, "side": "SELL"}]
    prob = {"a": 0.41, "b": 0.80}
    pos = {"a": vv.POS_1ST, "b": vv.POS_CHAIN}
    got = vv.judgments_for_policy_value(prints, "前段の3択(清算)", prob, pos,
                                        {vv.POS_1ST: (0.1, 0.2),
                                         vv.POS_CHAIN: (0.1, 0.2)},
                                        {vv.POS_1ST: 0.5, vv.POS_CHAIN: 0.5},
                                        kind=vv.JUDGE_LIQ)
    # 値段の帯 (0.1,0.2) ではなく前段の帯(1件目 0.42/0.58、連鎖の中 0.70/0.76)を使う
    assert got == [vv.JUDGE_STOP, vv.JUDGE_CONTINUE]
    perfect = vv.judgments_for_policy_value(prints, "完全な判断(清算)", prob, pos,
                                            {}, {}, kind=vv.JUDGE_LIQ)
    assert perfect == [vv.JUDGE_CONTINUE, vv.JUDGE_STOP]
    assert vv.REF_POLICIES == ("前段の3択(清算)", "完全な判断(清算)")


def test_q4_tables_cover_side_size_position_day_and_exposure():
    rows = [{"bundle_id": f"b{i}", "day": f"2023-07-{1 + i:02d}",
             "side": ("BUY" if i % 2 else "SELL"),
             "連鎖の大きさ": ("単発" if i < 2 else "3件以上"),
             "最初に入った位置": "1件目で入った",
             "pnl_net_bp": float(i - 2), "保有秒": 60.0,
             "入りの約定時刻": i * 100_000, "出の約定時刻": i * 100_000 + 60_000,
             "入った": 1} for i in range(5)]
    q4 = vv.build_q4_tables({"X": rows})
    assert len(q4["並置"]) == 1 and q4["並置"][0]["n"] == 5
    assert len(q4["日ごと"]) == 1 and q4["日ごと"][0]["日数"] == 5
    assert {r["水準"] for r in q4["側別"]} == {"BUY", "SELL"}
    assert {r["水準"] for r in q4["大きさ別"]} == {"単発", "3件以上"}
    assert {r["水準"] for r in q4["位置別"]} == {"1件目で入った"}
    assert q4["露出"][0]["合計保有時間_時間"] == pytest.approx(5 * 60 / 3600)


def test_bundle_id_fingerprint_is_order_insensitive():
    a = vv.bundle_id_fingerprint(["b2", "b1", "b3"])
    b = vv.bundle_id_fingerprint(["b3", "b2", "b1", "b1"])
    assert a == b
    assert a != vv.bundle_id_fingerprint(["b1", "b2"])


@needs_data
def test_prior_stage2_bundle_ids_are_2000_when_present():
    if not vv.PRIOR_STAGE2_CASCADES.exists():
        pytest.skip("前段の段2 の出力が無い")
    ids = vv.prior_stage2_bundle_ids()
    assert len(ids) == 2000


# ===========================================================================
# 反証者レビュー9 の再点検(2026-09-21)を受けた直しの試験
# ===========================================================================

# --- 致命-4: Q5b(a) の母集団は半期の全連鎖 ∩ 標本日 -------------------------
def test_q5b_population_is_all_chains_on_sample_days():
    days = [bsp.day_of_path(q) for q in bsp.sample_day_paths()]
    if not days:
        pytest.skip("標本日の約定が無い")
    d0 = days[0]
    cas = {"a": [{"ts_ms": 1, "day": d0, "side": "BUY"}],
           "b": [{"ts_ms": 2, "day": "1999-01-01", "side": "BUY"}],
           "c": [{"ts_ms": 3, "day": d0, "side": "SELL"},
                 {"ts_ms": 4, "day": d0, "side": "SELL"}]}
    got = vv.chains_on_sample_days(cas)
    assert set(got) == {"a", "c"}


def test_stage2_builds_q5b_from_all_back_half_chains_not_the_2000():
    """段2 は `picked`(抜いた 2,000 本)ではなく後半の全連鎖から Q5b の母集団を作る。"""
    src = (ROOT / "scripts" / "o3c_signal_value.py").read_text()
    body = src[src.index("def run_stage2("):src.index("def minute_rows_for(")]
    assert 'all_back = cascades_from_prints(back_prints, "段2 後半の全連鎖")' in body
    assert "q5b_source = chains_on_sample_days(all_back)" in body
    assert "run_q5b(q5b_source," in body
    assert "run_q5b(picked," not in body


@needs_data
def test_stage1_q5b_population_matches_the_design_count():
    prints = vv.load_stage1_prints()
    cas = vv.cascades_from_prints(prints, "試験")
    assert len(vv.chains_on_sample_days(cas)) == 285      # 設計の「前半 285 本」


# --- N-1: 対差と並置の母集団 2 通り ----------------------------------------
def test_pair_diff_has_both_populations_with_counts():
    lines = {
        "A": [{"bundle_id": "b1", "pnl_net_bp": 5.0, "入った": 1},
              {"bundle_id": "b2", "pnl_net_bp": -1.0, "入った": 1},
              {"bundle_id": "b3", "pnl_net_bp": 0.0, "入った": 0}],
        "B": [{"bundle_id": "b1", "pnl_net_bp": 1.0, "入った": 1}],
    }
    rows = vv.build_pair_diff_rows(lines, (("A", "B"),),
                                   universe=["b1", "b2", "b3"])
    assert len(rows) == 2
    zero = [r for r in rows if r["母集団"].startswith("0として")][0]
    both = [r for r in rows if r["母集団"] == "両方入った連鎖だけ"][0]
    assert zero["対の数"] == 3                     # 入らなかった連鎖も 0 で対にする
    assert zero["対差の合計_bp"] == pytest.approx(5.0 - 1.0 + (-1.0) + 0.0)
    assert both["対の数"] == 1                     # B が入ったのは b1 だけ
    assert both["対差の合計_bp"] == pytest.approx(4.0)
    for r in rows:
        assert "対の数" in r


def test_q4_main_has_both_populations():
    rows_a = [{"bundle_id": f"b{i}", "day": "2024-03-01", "side": "BUY",
               "連鎖の大きさ": "単発", "最初に入った位置": "1件目で入った",
               "pnl_net_bp": 1.0, "保有秒": 60.0, "入りの約定時刻": i * 1000,
               "出の約定時刻": i * 1000 + 60_000, "入った": 1} for i in range(4)]
    rows_b = [rows_a[0]]
    q4 = vv.build_q4_tables({"A": rows_a, "B": rows_b},
                            universe=[f"b{i}" for i in range(4)],
                            day_of={f"b{i}": "2024-03-01" for i in range(4)})
    main = q4["並置"]
    assert len(main) == 4                       # 2 本 × 母集団 2 通り
    b_zero = [r for r in main if r["方策"] == "B"
              and r["母集団"].startswith("0として")][0]
    b_ent = [r for r in main if r["方策"] == "B" and r["母集団"] == "入った連鎖だけ"][0]
    assert b_zero["n"] == 4 and b_ent["n"] == 1
    assert b_zero["合計_bp"] == pytest.approx(b_ent["合計_bp"])   # 0 を足しても同じ


# --- N-2 / N-3: キャッシュと重複定義 ---------------------------------------
def test_add_n2_by_day_is_defined_once():
    src = (ROOT / "scripts" / "o3c_signal_value.py").read_text()
    assert src.count("\ndef add_n2_by_day(") == 1


def test_liq_reference_probs_do_not_recompute_n2():
    """N-2: 参照 2 本の確率は `sp.stage2.compute_logit_probs`(中で `add_n2_column` を
    1 回呼ぶ)ではなく、日ごとに計算済みの N2 を受け取る経路を使う。"""
    src = (ROOT / "scripts" / "o3c_signal_value.py").read_text()
    assert "def compute_liq_logit_probs(df: pd.DataFrame, n2_by_pid: dict)" in src
    assert "sp.stage2.compute_logit_probs(" not in src
    import inspect
    body = inspect.getsource(vv.compute_liq_logit_probs)
    code = body[body.index('"""', body.index('"""') + 3) + 3:]   # docstring を除く
    assert "add_n2_column" not in code
    assert "n2_by_pid.get" in code
    # 1 回の計算を値段と清算の両方で使い回す
    assert "prob_liq = compute_liq_logit_probs(df, n2)" in inspect.getsource(
        vv.compute_probs_for_frame)


# --- N-4: 到達時間の母集団 --------------------------------------------------
def test_time_to_target_table_uses_the_bundle_population():
    rows = [
        {"到達秒": 2.0, "再計算したラベル": 1.0, "位置": vv.POS_1ST, "束の中": 1,
         "遅れ1秒の約定からの最大順行_bp": 9.0},
        {"到達秒": 3.0, "再計算したラベル": 1.0, "位置": vv.POS_1ST, "束の中": 0,
         "遅れ1秒の約定からの最大順行_bp": 40.0},
    ]
    tbl = vv.time_to_target_table(rows)
    whole = [r for r in tbl if r["場面"] == "全体"][0]
    assert whole["値段のラベルが1の件数"] == 1        # 束の外は入れない
    assert whole["母集団"] == "束の中のプリントだけ"
    assert whole["母集団から外した件数(束の外)"] == 1
    tbl_all = vv.time_to_target_table(rows, bundle_only=False)
    assert [r for r in tbl_all if r["場面"] == "全体"][0]["値段のラベルが1の件数"] == 2


@needs_data
def test_stage1_time_to_target_population_is_20797_based():
    path = vv.DEFAULT_OUT / "time_to_target.csv"
    if not path.exists():
        pytest.skip("段1 がまだこの環境で実行されていない")
    df = pd.read_csv(path)
    assert (df["母集団"] == "束の中のプリントだけ").all()
    assert (df["母集団から外した件数(束の外)"] == 1041).all()


# --- 書き出しの順と `入りの目標時刻_ms` ------------------------------------
def test_stage2_writes_the_rows_before_any_table():
    src = (ROOT / "scripts" / "o3c_signal_value.py").read_text()
    body = src[src.index("def run_stage2("):src.index("def minute_rows_for(")]
    i_rows = body.index("n_cascade_rows = write_cascades_gz(out_dir, cascade_file_rows)")
    i_prints = body.index('sp.write_csv_gz(out_dir / "prints_policy.csv.gz"')
    i_tables = body.index("tabs = tables_from_cascade_rows(")
    i_calib = body.index('write_csv(out_dir / "calib_5000.csv"')
    i_q5b = body.index("q5b_rows = run_q5b(")
    assert i_rows < i_prints < i_tables < i_calib < i_q5b


def test_cascade_columns_include_the_entry_target_time():
    assert "入りの目標時刻_ms" in vv.CASCADE_COLUMNS
    res = {"path": [{"ts_ms": 10_000, "約定価格": 100.0},
                    {"ts_ms": 40_000, "約定価格": 100.5}],
           "fill_lag_ms": [250, 400]}
    assert vv.entry_target_time(res, 1) == 11_000
    assert vv.entry_target_time({"path": [], "fill_lag_ms": []}, 1) is None
    # 約定時刻 − 目標時刻 = 約定の遅れ が後から引ける
    t_in, _t_out = vv.entry_exit_fill_times(res, 1)
    assert t_in - vv.entry_target_time(res, 1) == 250


def test_stage2_dry_run_writes_rows_and_from_rows_reproduces_the_tables(tmp_path):
    if not (vv.DEFAULT_OUT / "summary.json").exists():
        pytest.skip("段1 がまだこの環境で実行されていない")
    if not (vv.SPREAD_DIR / "spread_by_day.csv").exists():
        pytest.skip("費用の表がまだこの環境で作られていない")
    out = tmp_path / "dry"
    vv.run_stage2(out_dir=out, dry_run=True)
    assert (out / "cascades.csv.gz").exists()
    assert (out / "prints_policy.csv.gz").exists()
    casc = pd.read_csv(out / "cascades.csv.gz")
    assert list(casc.columns)[:len(vv.CASCADE_COLUMNS)] == list(vv.CASCADE_COLUMNS)
    before = {n: pd.read_csv(out / n) for n in
              ("dist_table.csv", "q4_main.csv", "q4_pair_diff.csv", "q4_by_day.csv",
               "q4_exposure.csv", "position_breakdown.csv")}
    vv.run_from_rows(out)
    for n, b in before.items():
        a = pd.read_csv(out / n)
        assert list(a.columns) == list(b.columns), n
        assert len(a) == len(b), n
        for col in a.columns:
            if pd.api.types.is_numeric_dtype(b[col]):
                # CSV の 6 桁丸めを 1 往復するので、その分だけずれる
                assert np.allclose(a[col].to_numpy(float), b[col].to_numpy(float),
                                   rtol=1e-4, atol=2e-6, equal_nan=True), (n, col)
            else:
                assert a[col].astype(str).tolist() == b[col].astype(str).tolist(), n


def test_from_rows_never_reads_the_back_half_source():
    import inspect
    body = inspect.getsource(vv.run_from_rows) + inspect.getsource(
        vv.tables_from_cascade_rows)
    for forbidden in ("ROWS_CONTINUE", "ROWS_MATERIALS", "load_prints",
                      "select_stage2_cascades", "WindowCache"):
        assert forbidden not in body, forbidden


# ===========================================================================
# L-352: 参照行「① 3 択 A、出口 = 最後のプリント + 300 秒 + 遅れ」
# ===========================================================================
def test_exit300_reference_changes_only_the_forced_close_time():
    """判断・帯・行動は ① 3 択 A のまま、**建玉を持ったまま連鎖の終わりに達したときの
    強制決済の時刻だけ**が「最後のプリント + 300 秒 + 遅れ」になる。"""
    P = vv.sp
    times = np.arange(0, 1_200_000, 1_000, dtype=np.int64)
    prices = 100.0 + times / 1.0e7

    def price_fn(t_ms):
        return vv.price_at_or_after(times, prices, int(t_ms))

    prints = [{"print_id": "a", "ts_ms": 10_000, "side": "SELL"},
              {"print_id": "b", "ts_ms": 40_000, "side": "SELL"}]
    jud = [vv.JUDGE_STOP, vv.JUDGE_UNKNOWN]          # 逆張りで入って持ったまま終わる
    end60 = 40_000 + vv.CASCADE_END_GAP_S * 1000
    end300 = 40_000 + vv.EXIT_HOLD_S * 1000
    r60 = P.simulate_cascade(prints, jud, -1.0, vv.TYPE_A, 1, price_fn, end60)
    r300 = P.simulate_cascade(prints, jud, -1.0, vv.TYPE_A, 1, price_fn, end300)
    # 判断と行動の列は同じ(最後の強制決済の行だけ時刻が違う)
    assert [x["判断"] for x in r60["path"]] == [x["判断"] for x in r300["path"]]
    assert [x["行動"] for x in r60["path"]] == [x["行動"] for x in r300["path"]]
    assert r60["path"][-1]["ts_ms"] == end60
    assert r300["path"][-1]["ts_ms"] == end300
    assert r300["hold_seconds"] > r60["hold_seconds"]
    assert r300["n_entries"] == r60["n_entries"]
    # 途中で決済してしまう連鎖(建玉が残らない)では 2 つは完全に同じ
    jud_close = [vv.JUDGE_STOP, vv.JUDGE_CONTINUE]   # 型 A は次のプリントで決済
    c60 = P.simulate_cascade(prints, jud_close, -1.0, vv.TYPE_A, 1, price_fn, end60)
    c300 = P.simulate_cascade(prints, jud_close, -1.0, vv.TYPE_A, 1, price_fn, end300)
    assert c60["pnl_bp"] == pytest.approx(c300["pnl_bp"])
    assert c60["hold_seconds"] == pytest.approx(c300["hold_seconds"])


def test_run_policies_emits_the_exit300_reference_line():
    times = np.arange(0, 1_200_000, 1_000, dtype=np.int64)
    prices = 100.0 + times / 1.0e7
    cache = vv.SyntheticCache(times, prices)
    cascades = {"c1": [
        {"print_id": "p1", "ts_ms": 10_000, "side": "SELL", "day": "2024-03-01",
         vv.LABEL_VALUE: 1, vv.sp.MAT1_COL: 0},
        {"print_id": "p2", "ts_ms": 40_000, "side": "SELL", "day": "2024-03-01",
         vv.LABEL_VALUE: 0, vv.sp.MAT1_COL: 1}]}
    prob = {"p1": 0.10, "p2": 0.50}
    pos = {"p1": vv.POS_1ST, "p2": vv.POS_CHAIN}
    bands = {vv.POS_1ST: (0.38, 0.5), vv.POS_CHAIN: (0.56, 0.66)}
    base = {vv.POS_1ST: 0.4343, vv.POS_CHAIN: 0.5999}
    off = vv.run_policies(cascades, prob, pos, bands, base, cache)
    on = vv.run_policies(cascades, prob, pos, bands, base, cache, with_exit300=True)
    assert vv.EXIT300_POLICY not in {r["方策"] for r in off["cascade_rows"]}
    extra = [r for r in on["cascade_rows"] if r["方策"] == vv.EXIT300_POLICY]
    assert len(extra) == len(vv.DELAYS_S)            # 型 A のみ × 遅れ 3
    assert {r["型"] for r in extra} == {vv.TYPE_A}
    assert {r["出口の理由"] for r in extra} == {vv.EXIT300_REASON}
    base_rows = [r for r in on["cascade_rows"]
                 if r["方策"] == "logistic_3択" and r["型"] == vv.TYPE_A]
    assert len(base_rows) == len(vv.DELAYS_S)
    # 建玉を持ったまま終わる連鎖なので、300 秒の方が保有秒は長い
    b1 = [r for r in base_rows if r["遅れ_秒"] == vv.MAIN_DELAY][0]
    e1 = [r for r in extra if r["遅れ_秒"] == vv.MAIN_DELAY][0]
    assert e1["保有秒"] > b1["保有秒"]
    assert e1["建玉の回数"] == b1["建玉の回数"]
    # Q4 の線と対差に入る
    assert (vv.EXIT300_LINE, vv.EXIT300_POLICY, vv.TYPE_A) in vv.Q4_LINE_SPEC
    assert len(vv.Q4_LINE_SPEC) == 7
    pairs = vv.q4_pairs({n: [] for n, _p, _t in vv.Q4_LINE_SPEC})
    assert (vv.EXIT300_LINE, "②opt") in pairs
    assert len(pairs) == 4


@needs_data
def test_stage1_outputs_carry_the_exit300_line():
    path = vv.DEFAULT_OUT / "dist_table.csv"
    if not path.exists():
        pytest.skip("段1 がまだこの環境で実行されていない")
    d = pd.read_csv(path)
    assert vv.EXIT300_POLICY in set(d["方策"])
    pb = pd.read_csv(vv.DEFAULT_OUT / "position_breakdown.csv")
    assert vv.EXIT300_POLICY in set(pb["方策"])
    casc = pd.read_csv(vv.DEFAULT_OUT / "cascades.csv.gz", usecols=["方策"])
    assert vv.EXIT300_POLICY in set(casc["方策"])


# ===========================================================================
# 段2 の未計算ブロックの再開(2026-09-21、リードの決定「未決 1」)
# ===========================================================================

def test_q5b_label_follows_the_half_that_was_measured():
    """Q5b の行の「経路」は測った半期を名乗る(段1 = 前半、段2 = 後半)。"""
    src = (ROOT / "scripts" / "o3c_signal_value.py").read_text()
    body = src[src.index("def run_q5b("):src.index("# 13. 段2")]
    head = src[src.index("def run_q5b("):src.index("def run_q5b(") + 500]
    assert 'half_label: str = "前半"' in head          # 段1 の既定
    # 行を作るところに「前半」の直書きが残っていない
    assert "前半" not in body[body.index("rows = []"):]
    assert 'secs_label = f"秒単位(標本日に掛かる{half_label}の連鎖)"' in body
    assert 'minute_label = f"1分の始値({half_label}の全連鎖)"' in body
    # 段2 と再開はどちらも後半を渡す
    assert src.count("half_label=BACK_HALF") == 2


@needs_data
def test_stage2_q5b_output_names_the_back_half():
    path = vv.DEFAULT_OUT_STAGE2 / "q5b_secs_secondhalf.csv"
    if not path.exists():
        pytest.skip("段2 がまだこの環境で実行されていない")
    d = pd.read_csv(path)
    routes = set(d["経路"])
    assert "秒単位(標本日に掛かる後半の連鎖)" in routes
    assert "1分の始値(後半の全連鎖)" in routes
    assert not [r for r in routes if "前半" in r]
    pop = d[d["区分"] == "(母集団)"]
    assert int(pop["対の数"].iloc[0]) == 506       # 後半の全連鎖 ∩ 標本日


@needs_data
def test_resume_did_not_touch_the_cascade_rows():
    """再開は Q1 併記・Q5b・Q0 の追加だけを作り、連鎖ごとの行に触っていない。"""
    out = vv.DEFAULT_OUT_STAGE2
    js = out / "resume_summary.json"
    if not js.exists():
        pytest.skip("再開がまだこの環境で実行されていない")
    s = json.loads(js.read_text(encoding="utf-8"))
    kept = s["触っていないもの(MD5 が前後で同じ)"]
    for name, md5 in kept.items():
        assert vv.md5_of(out / name) == md5
    assert s["Q5b(a) の母集団"] == 506


def test_resume_reads_only_the_outside_bundle_back_half_rows():
    src = (ROOT / "scripts" / "o3c_signal_value.py").read_text()
    body = src[src.index("def outside_bundle_back_half_rows("):
               src.index("def run_resume(")]
    assert 'bundle_id' in body and 'isna()' in body
    assert vv.BACK_HALF in body


def test_resume_raises_when_the_rows_changed():
    src = (ROOT / "scripts" / "o3c_signal_value.py").read_text()
    body = src[src.index("def run_resume("):]
    body = body[:body.index("\ndef ")] if "\ndef " in body else body
    assert "frozen = {n: md5_of(out_dir / n)" in body
    assert "after = {n: md5_of(out_dir / n)" in body
    assert "cascades.csv.gz" in body and "prints_policy.csv.gz" in body
    assert "raise RuntimeError" in body and "連鎖ごとの行が変わった" in body
