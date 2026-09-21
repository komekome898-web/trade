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
    cuts = vv.condition_cuts(prints)
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
                               "p75_bp", "p90_bp"}
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


def test_stage2_is_implemented_but_not_run_in_this_unit():
    """段2 は実装だけ(後半 2,000 本は別の委任で一度だけ)。この環境で走っていない
    ことを、出力が無いことで確かめる。"""
    assert callable(vv.run_stage2)
    assert not (vv.DEFAULT_OUT_STAGE2 / "summary.json").exists()
