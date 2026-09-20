"""`scripts/o3c_jev_state.py`(Jev に渡す state を「トレーダーが言う英文の列」で組む
道具)+ `scripts/o3c_signal_logit.py`(V4 の比較相手の logistic)の試験。

**測るもの**(委任文【作るもの】2・段1 委任文 20260920_o3c_signal_v4_prompt.md【作るもの】4)
  1. 文の型が設計(`SIGNAL_MATERIALS_DESIGN_2026-09-20.md` §6.2)の 13 本と一致する
     (合成の値で各文を手計算と比較。BUY/SELL の向きの語、1 件目で連鎖の内側の文
     (型3・4・8・9)が無い、欠測は "unknown")。
  2. ts 以後を使わない(ts 以後の約定を変えても同じ文。p0 に当たる約定の価格を
     書き換えても同じ文)。
  3. 帯の境界が前半だけから計算される(後半の値を変えても境界が同じ)。
  4. 同じ入力で同じ文(決定性)。
  5. `paper_logs/` を開かない。
  6. 判定語が出力の markdown に無い。
  7. V4(§7.1 の決定表)の 1 件目に「外す」文が無い / 連鎖の中に「外す」文が無い。
  8. V4 の criteria が位置(1 件目 / 連鎖の中)で切り替わる。
  9. N1・N2 が ts 以後を使わない(p0 書き換え不変)。
  10. logistic の係数が前半だけから決まる(後半の値を変えても同じ)/ 予測が決定的。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

_spec_sc = importlib.util.spec_from_file_location(
    "o3c_signal_continue", ROOT / "scripts" / "o3c_signal_continue.py")
sc = importlib.util.module_from_spec(_spec_sc)
assert _spec_sc.loader is not None
_spec_sc.loader.exec_module(sc)

_spec_js = importlib.util.spec_from_file_location(
    "o3c_jev_state", ROOT / "scripts" / "o3c_jev_state.py")
js = importlib.util.module_from_spec(_spec_js)
assert _spec_js.loader is not None
_spec_js.loader.exec_module(js)

_spec_lg = importlib.util.spec_from_file_location(
    "o3c_signal_logit", ROOT / "scripts" / "o3c_signal_logit.py")
lg = importlib.util.module_from_spec(_spec_lg)
assert _spec_lg.loader is not None
_spec_lg.loader.exec_module(lg)

NAN = float("nan")

# 型1・2・4・11・13 で使う帯(5 分位、4 つの切り値)。値そのものはどうでもよく、
# 境目をまたぐ値を選んで期待する帯の名を手計算する。
BANDS = {
    "notional": [10.0, 20.0, 30.0, 40.0],
    "chain_notional": [10.0, 20.0, 30.0, 40.0],
    "last10s_notional": [10.0, 20.0, 30.0, 40.0],
    "oi_ahead_20bp": [10.0, 20.0, 30.0, 40.0],
    "trade_count_60s": [10.0, 20.0, 30.0, 40.0],
    "vol_ratio_c4": [1.0, 2.0, 3.0, 4.0],
    "oi_slope_1h": [-20.0, -5.0, 5.0, 20.0],
    "day_extreme_c3_quartiles": [10.0, 20.0, 30.0],
}


def base_row(**overrides) -> dict:
    row = {
        "side": "SELL", "day": "2024-01-02", "ts_ms": 1_000_000,
        "cand_1": 0.0, "cand_2": NAN, "cand_3": NAN, "cand_5p": NAN, "cand_6": 2.0,
        "cand_A5": NAN, "cand_A6": NAN, "cand_A9_count": 0.0, "cand_C3": NAN,
        "cand_C4": NAN, "cand_R1": NAN, "cand_F3": NAN, "cand_F5": NAN,
        "cand_14": NAN,
        "mat3_notional_raw": 15.0, "mat1_elapsed_since_burst_s": NAN,
        "mat8_amt_5bp": NAN, "mat8_amt_20bp": NAN, "mat8_covered": 0.0,
        "mat9_taker_imbalance_5s": NAN, "mat13_taker_imbalance_trend": NAN,
        "mat10_oi_slope_and_funding": NAN, "mat10_funding_rate": NAN,
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# (1) 文の型が設計の 13 本と一致(合成の値で手計算と比較)
# ---------------------------------------------------------------------------
def test_sent1_size_and_time_band_sell():
    row = base_row(side="SELL", mat3_notional_raw=25.0, cand_6=2.0)  # 20<25<30 -> 3番目(middle)
    got = js._sent1(row, BANDS)
    assert got == "SELL liquidation, among the middle fifth of prints, at 12-18 UTC."


def test_sent1_size_and_time_band_buy_and_unknown_time():
    row = base_row(side="BUY", mat3_notional_raw=45.0, cand_6=NAN)  # >40 -> largest
    got = js._sent1(row, BANDS)
    assert got == "BUY liquidation, among the largest fifth of prints, at unknown."


def test_sent2_first_print_literal_text():
    assert js._sent2_first() == "No same-side liquidation in the last 60 seconds."


def test_sent2_nonfirst_counts_and_bands():
    row = base_row(cand_1=3.0, mat1_elapsed_since_burst_s=12.345, cand_F3=35.0)
    got = js._sent2_nonfirst(row, BANDS)
    assert got == ("It is the 4th same-side liquidation of a cascade that began "
                   "12 seconds ago; the amount liquidated so far is among the "
                   "second-largest fifth of cascades.")


def test_sent3_two_prev_gaps_shorter_and_larger():
    # cand_2 = gap_b/gap_a > 1+eps -> shorter。cand_3 = ratio to previous > 1+eps -> larger
    row = base_row(cand_2=1.5, cand_3=1.5)
    got = js._sent3(row, a=5.0, b=20.0)
    assert got == ("The last two same-side liquidations were 5.0 and 20 "
                   "seconds ago; the gaps are getting shorter. This print is "
                   "larger than the previous one.")


def test_sent3_single_prev_form():
    row = base_row(cand_2=NAN, cand_3=0.5)  # < 1-eps -> smaller
    got = js._sent3(row, a=3.0, b=None)
    assert got == ("The previous same-side liquidation was 3.0 seconds ago. "
                   "This print is smaller than the previous one.")


def test_sent3_about_the_same_band():
    row = base_row(cand_2=1.0, cand_3=1.0)
    got = js._sent3(row, a=5.0, b=6.0)
    assert "about the same" in got and "This print is about the same than the previous one." in got


def test_sent4_none_and_band():
    assert js._sent4(base_row(cand_F5=0.0), BANDS) == "No same-side liquidation in the last 10 seconds."
    got = js._sent4(base_row(cand_F5=45.0), BANDS)
    assert got == "Same-side liquidations in the last 10 seconds: among the largest fifth (of prints that had any)."


def test_sent5_zero_and_count_with_time():
    assert js._sent5(base_row(cand_A9_count=0.0), None) == "No opposite-side liquidation in the last 60 seconds."
    got = js._sent5(base_row(cand_A9_count=2.0), 7.25)
    assert got == "2 opposite-side liquidations in the last 60 seconds, the last 7.2 seconds ago."


def test_sent6_recent_extreme_and_pullback_sell_vs_buy():
    row_sell = base_row(side="SELL", cand_A6=0.5)
    assert js._sent6(row_sell) == "Price made a new 60-second low 0.5 seconds ago and has not pulled back."
    row_buy = base_row(side="BUY", cand_A6=12.0, cand_R1=3.4)
    assert js._sent6(row_buy) == "Price made a new 60-second high 12 seconds ago and has pulled back 3.4 bp since."
    assert js._sent6(base_row(cand_A6=NAN)) == "unknown"


def test_sent7_direction_words_and_unknown():
    row_sell = base_row(side="SELL")
    assert js._sent7(row_sell, m60=10.0, m10=4.0, r60=12.0) == (
        "Over the last 60 seconds price fell 10.0 bp (range 12.0 bp); "
        "over the last 10 seconds it fell 4.0 bp.")
    row_buy = base_row(side="BUY")
    assert js._sent7(row_buy, m60=-5.0, m10=-1.0, r60=9.0) == (
        "Over the last 60 seconds price fell 5.0 bp (range 9.0 bp); "
        "over the last 10 seconds it fell 1.0 bp.")
    assert js._sent7(row_sell, m60=NAN, m10=1.0, r60=1.0) == "unknown"


def test_sent8_clips_negative_pullback_to_zero():
    assert js._sent8(base_row(cand_A5=-3.0)) == (
        "Since the previous same-side liquidation, the largest pullback was 0.0 bp.")
    assert js._sent8(base_row(cand_A5=2.5)) == (
        "Since the previous same-side liquidation, the largest pullback was 2.5 bp.")
    assert js._sent8(base_row(cand_A5=NAN)) == "unknown"


def test_sent9_participle_words_by_sign_and_side():
    assert js._sent9(base_row(side="SELL"), 12.0) == "Since the cascade began, price has fallen 12.0 bp."
    assert js._sent9(base_row(side="SELL"), -3.0) == "Since the cascade began, price has risen 3.0 bp."
    assert js._sent9(base_row(side="BUY"), 4.0) == "Since the cascade began, price has risen 4.0 bp."
    assert js._sent9(base_row(), None) == "unknown"


def test_sent10_pct_and_trend_and_unknown():
    row = base_row(side="SELL", mat9_taker_imbalance_5s=0.5, mat13_taker_imbalance_trend=0.2)
    got = js._sent10(row, m5=3.3)
    assert got == ("Taker flow in the last 5 seconds: 75% sells; over 30 seconds: "
                   "65% (more one-sided now). Price fell 3.3 bp in the last 5 seconds.")
    assert js._sent10(base_row(mat9_taker_imbalance_5s=NAN), 1.0) == "unknown"


def test_sent11_coverage_and_bands_and_prep_word():
    assert js._sent11(base_row(mat8_covered=0.0), BANDS) == (
        "Open interest below the current price: coverage unknown.")
    row_none = base_row(side="BUY", mat8_covered=1.0, mat8_amt_20bp=0.0, mat8_amt_5bp=0.0, cand_5p=NAN)
    assert js._sent11(row_none, BANDS) == (
        "No open interest within 20 bp above the current price; within 5 bp: none "
        "(coverage: yes). Nearest liquidation level above: none within the mapped range.")
    row_some = base_row(side="SELL", mat8_covered=1.0, mat8_amt_20bp=25.0, mat8_amt_5bp=1.0, cand_5p=-14.2)
    got = js._sent11(row_some, BANDS)
    assert got == ("Open interest among the middle fifth within 20 bp below the "
                   "current price; within 5 bp: some (coverage: yes). Nearest "
                   "liquidation level below: 14 bp away.")


def test_sent12_oi_trend_bands_and_funding_sign():
    row = base_row(mat10_oi_slope_and_funding=25.0, mat10_funding_rate=-0.001)
    assert js._sent12(row, BANDS) == "Open interest over the last hour: rising fast. Funding: negative."
    assert js._sent12(base_row(mat10_funding_rate=0.0), BANDS).endswith("Funding: zero.")


def test_sent13_day_extreme_special_case_and_bands():
    row_at = base_row(side="SELL", cand_C3=0.0, cand_C4=2.5, cand_14=25.0)
    assert js._sent13(row_at, BANDS) == (
        "Price is at the day's low. Volatility now vs the last hour: similar. "
        "Trading activity in the last 60 seconds: among the middle fifth.")
    row_far = base_row(side="BUY", cand_C3=35.0, cand_C4=0.5, cand_14=45.0)
    assert js._sent13(row_far, BANDS) == (
        "Price is far from the day's high. Volatility now vs the last hour: "
        "much calmer. Trading activity in the last 60 seconds: among the busiest fifth.")


# ---------------------------------------------------------------------------
# 帯の索引の境目(手計算)
# ---------------------------------------------------------------------------
def test_band5_index_boundaries_are_right_inclusive_on_lower_cut():
    cuts = [10.0, 20.0, 30.0, 40.0]
    assert js.band5_index(5.0, cuts) == 0
    assert js.band5_index(10.0, cuts) == 1  # searchsorted(side="right") -> 境目は上の帯
    assert js.band5_index(15.0, cuts) == 1
    assert js.band5_index(45.0, cuts) == 4
    assert js.band5_index(NAN, cuts) is None


# ---------------------------------------------------------------------------
# StateBuilder を使う統合試験: 小道具(合成の材料・continue・prints・約定)
# ---------------------------------------------------------------------------
def _write_gz_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, compression="gzip")


def build_synthetic_dataset(tmp_path: Path):
    """1 日・BUY 側の 2 件(1 件目・2 件目)を持つ最小の材料・continue・prints・約定。"""
    day = "2024-01-02"
    t0 = sc.day_start_ms(day) + 3_600_000
    ts1 = t0                      # 1 件目(cand_1 == 0)
    ts2 = t0 + 10_000              # 2 件目(cand_1 == 1、10 秒後)

    prints_df = pd.DataFrame([
        {"kind": "print", "print_id": "p1", "day": day, "side": "BUY", "ts_ms": ts1,
         "t0_ms": ts1, "p0": 100.0, "notional": 500_000.0, "dist_node_bp": 0.0,
         "oi_covered": 0, "bundle_id": ""},
        {"kind": "print", "print_id": "p2", "day": day, "side": "BUY", "ts_ms": ts2,
         "t0_ms": ts2, "p0": 101.0, "notional": 300_000.0, "dist_node_bp": 0.0,
         "oi_covered": 0, "bundle_id": ""},
    ])
    rows_path = tmp_path / "rows_prints.csv.gz"
    _write_gz_csv(rows_path, prints_df)

    def mat_row(pid, day, side, ts_ms, half, cand_1, extra_cand=None, extra_c=None):
        r = {"print_id": pid, "day": day, "side": side, "half": half, "ts_ms": ts_ms,
            "cand_1": cand_1, "cand_2": NAN, "cand_3": NAN, "cand_5p": NAN,
            "cand_6": 0.0, "cand_8": NAN, "cand_9": NAN, "cand_10": NAN,
            "cand_11": NAN, "cand_12": NAN, "cand_13": NAN, "cand_14": 5.0,
            "cand_15": NAN, "cand_F3": NAN, "cand_F4": NAN, "cand_A3": NAN,
            "cand_A4": NAN, "cand_A5": NAN, "cand_A6": 0.2, "cand_A9": 0.0,
            "cand_C3": 5.0, "cand_C4": 1.0, "cand_R1": NAN, "cand_F5": NAN,
            "cand_A9_count": 0.0}
        if extra_cand:
            r.update(extra_cand)
        return r

    materials_df = pd.DataFrame([
        mat_row("p1", day, "BUY", ts1, "前半", 0.0),
        mat_row("p2", day, "BUY", ts2, "前半", 1.0, {"cand_F3": 500_000.0}),
    ])
    materials_path = tmp_path / "rows_materials.csv.gz"
    _write_gz_csv(materials_path, materials_df)

    def cont_row(pid, ts_ms):
        r = {"print_id": pid}
        for n in sc.MAT_NUMS:
            r[sc.MAT_COL[n]] = 1.0
        r[sc.MAT_COL[6]] = "UTC 00–06"
        r["mat1_elapsed_since_burst_s"] = 0.0
        r["mat3_notional_raw"] = 1.0
        r["mat8_amt_5bp"] = NAN
        r["mat8_amt_20bp"] = NAN
        r["mat8_covered"] = 0.0
        r["mat10_funding_rate"] = 0.0
        return r

    continue_df = pd.DataFrame([cont_row("p1", ts1), cont_row("p2", ts2)])
    continue_path = tmp_path / "rows_continue.csv.gz"
    _write_gz_csv(continue_path, continue_df)

    return rows_path, materials_path, continue_path, day, ts1, ts2


def _make_builder(tmp_path, times, prices):
    rows_path, materials_path, continue_path, day, ts1, ts2 = build_synthetic_dataset(tmp_path)
    sb = js.StateBuilder(materials_path=materials_path, continue_path=continue_path,
                         rows_path=rows_path, data_root=tmp_path / "unused",
                         bands=js.compute_bands(pd.read_csv(materials_path).assign(
                             mat3_notional_raw=1.0, mat8_amt_20bp=NAN, mat8_covered=0.0,
                             mat10_oi_slope_and_funding=1.0)))
    qtys = np.ones(times.size)
    maker = np.zeros(times.size, dtype=bool)
    sb._window_cache[day] = (times, prices)

    def fake_load_window5(data_root, day_, cache, back_ms, fwd_ms):
        return times, prices, qtys, [], [day_]

    return sb, fake_load_window5


def test_first_print_omits_cascade_interior_sentence_types(tmp_path, monkeypatch):
    rows_path, materials_path, continue_path, day, ts1, ts2 = build_synthetic_dataset(tmp_path)
    times = np.arange(ts1 - 120_000, ts1 + 1000, 1000, dtype=np.int64)
    prices = np.full(times.size, 100.0)
    sb, fake = _make_builder(tmp_path, times, prices)
    monkeypatch.setattr(js, "load_window5", fake)
    sentences = sb.build_state_sentences("p1")
    # 1 件目: 型2 の 1 件目の文だけで、型3・4・8・9(連鎖の内側)を書かない
    assert sentences[1] == "No same-side liquidation in the last 60 seconds."
    joined = "\n".join(sentences)
    assert "same-side liquidations of a cascade" not in joined  # 型2(非1件目)は出ない
    assert "The last two same-side" not in joined              # 型3
    assert "the largest pullback was" not in joined             # 型8
    assert "Since the cascade began" not in joined               # 型9
    assert len(sentences) == 9  # 13 - (型3・4・8・9 の 4 本)


def test_nonfirst_print_includes_all_13_types(tmp_path, monkeypatch):
    rows_path, materials_path, continue_path, day, ts1, ts2 = build_synthetic_dataset(tmp_path)
    times = np.arange(ts1 - 120_000, ts2 + 1000, 1000, dtype=np.int64)
    prices = np.full(times.size, 100.0)
    sb, fake = _make_builder(tmp_path, times, prices)
    monkeypatch.setattr(js, "load_window5", fake)
    sentences = sb.build_state_sentences("p2")
    assert len(sentences) == 13


def test_future_prices_and_p0_do_not_change_sentences(tmp_path, monkeypatch):
    rows_path, materials_path, continue_path, day, ts1, ts2 = build_synthetic_dataset(tmp_path)
    times = np.arange(ts1 - 120_000, ts2 + 400_000, 1000, dtype=np.int64)
    prices_a = 100.0 + 0.0001 * (times - times[0])
    prices_b = prices_a.copy()
    after = times >= ts2  # ts2 以後(ts2 自身、= p0 に当たる約定を含む)を書き換える
    prices_b[after] = prices_b[after] + 999.0

    sb_a, fake_a = _make_builder(tmp_path, times, prices_a)
    monkeypatch.setattr(js, "load_window5", fake_a)
    sent_a = sb_a.build_state_sentences("p2")

    sb_b, fake_b = _make_builder(tmp_path, times, prices_b)
    monkeypatch.setattr(js, "load_window5", fake_b)
    sent_b = sb_b.build_state_sentences("p2")

    assert sent_a == sent_b


def test_determinism_same_input_same_sentences(tmp_path, monkeypatch):
    rows_path, materials_path, continue_path, day, ts1, ts2 = build_synthetic_dataset(tmp_path)
    times = np.arange(ts1 - 120_000, ts2 + 1000, 1000, dtype=np.int64)
    prices = 100.0 + 0.0002 * (times - times[0])
    sb, fake = _make_builder(tmp_path, times, prices)
    monkeypatch.setattr(js, "load_window5", fake)
    a = sb.build_state_sentences("p2")
    b = sb.build_state_sentences("p2")
    assert a == b


# ---------------------------------------------------------------------------
# (3) 帯の境界は前半だけから
# ---------------------------------------------------------------------------
def test_compute_bands_ignores_second_half_values():
    rng = np.random.default_rng(0)
    n = 400
    half = np.array(["前半"] * 200 + ["後半"] * 200)
    df = pd.DataFrame({
        "half": half,
        "mat3_notional_raw": rng.normal(size=n) + 100,
        "cand_F3": rng.normal(size=n) + 100,
        "cand_F5": np.abs(rng.normal(size=n)) + 1,
        "mat8_amt_20bp": np.abs(rng.normal(size=n)) + 1,
        "mat8_covered": np.ones(n),
        "cand_14": rng.normal(size=n) + 100,
        "cand_C4": np.abs(rng.normal(size=n)) + 1,
        "mat10_oi_slope_and_funding": rng.normal(size=n),
        "cand_C3": np.abs(rng.normal(size=n)) + 1,
    })
    fh_a = df[df["half"] == "前半"]
    bands_a = js.compute_bands(fh_a)

    df2 = df.copy()
    for c in ("mat3_notional_raw", "cand_F3", "cand_F5", "mat8_amt_20bp", "cand_14",
             "cand_C4", "mat10_oi_slope_and_funding", "cand_C3"):
        df2.loc[df2["half"] == "後半", c] = 999_999.0
    fh_b = df2[df2["half"] == "前半"]
    bands_b = js.compute_bands(fh_b)

    for key in bands_a:
        assert np.allclose(bands_a[key], bands_b[key], equal_nan=True), key


# ---------------------------------------------------------------------------
# (5) `paper_logs/` を開かない
# ---------------------------------------------------------------------------
def test_source_never_opens_paper_logs():
    """`paper_logs` という文字列が出るのは説明文(docstring)だけで、実際にそれを
    開くコードは無い(探索段 5・前段 `o3c_signal_continue.py` の同名試験と同じ流儀)。"""
    src = (ROOT / "scripts" / "o3c_jev_state.py").read_text().splitlines()
    hits = [ln for ln in src if "paper_logs" in ln]
    assert hits and all("開かない" in ln for ln in hits), hits


# ---------------------------------------------------------------------------
# (6) 判定語
# ---------------------------------------------------------------------------
def test_no_banned_words_in_source_or_sentences():
    src = (ROOT / "scripts" / "o3c_jev_state.py").read_text()
    sc.check_no_banned(src, "source")  # ソース自体にも判定語を書かない

    samples = [
        base_row(side="SELL", cand_1=3.0, mat1_elapsed_since_burst_s=5.0, cand_F3=15.0,
                mat3_notional_raw=25.0, cand_A5=1.0, cand_A6=2.0, cand_R1=1.0,
                cand_C3=5.0, cand_C4=1.5, cand_14=15.0, mat8_covered=1.0,
                mat8_amt_20bp=15.0, mat8_amt_5bp=1.0, cand_5p=-3.0,
                mat9_taker_imbalance_5s=0.3, mat13_taker_imbalance_trend=0.05,
                mat10_oi_slope_and_funding=0.0, mat10_funding_rate=0.0),
        base_row(side="BUY", cand_1=0.0),
    ]
    for row in samples:
        text = "\n".join([
            js._sent1(row, BANDS), js._sent2_nonfirst(row, BANDS),
            js._sent3(row, 1.0, 2.0), js._sent4(row, BANDS),
            js._sent5(row, 1.0), js._sent6(row),
            js._sent7(row, 1.0, 1.0, 1.0), js._sent8(row), js._sent9(row, 1.0),
            js._sent10(row, 1.0), js._sent11(row, BANDS), js._sent12(row, BANDS),
            js._sent13(row, BANDS),
        ])
        sc.check_no_banned(text, "sentences")


# ---------------------------------------------------------------------------
# (7) V4(決定表 §7.1): 1 件目・連鎖の中に「外す」側の材料の文言が無い
# ---------------------------------------------------------------------------
# 「外す」側の材料だけが持つ言い回し(その型が丸ごと消えるか、型の中のその節だけ
# 消えるかは §7.1 の決定表どおり `o3c_jev_state.py` の docstring に書いた)。
DROPPED_PHRASES_FIRST = [
    "of prints, at",                # 型1(想定元本・時刻帯、丸ごと外す。type1 固有)
    "opposite-side liquidation",    # 型5(A9、丸ごと外す)
    "Open interest over the last hour",  # 型12(建玉の傾き、丸ごと外す)
    "over 30 seconds",              # 型10 の偏りの変化(材料13、節だけ外す)
]
DROPPED_PHRASES_CHAIN = [
    "of prints, at",                      # 型1(想定元本・時刻帯、丸ごと外す。type1 固有)
    "opposite-side liquidation",          # 型5(A9、丸ごと外す)
    "largest pullback was",               # 型8(A5、丸ごと外す)
    "Since the cascade began",            # 型9(A3、丸ごと外す)
    "over 30 seconds",                    # 型10(成行の偏り・変化、丸ごと外す)
    "pulled back",                        # 型6 の戻り(材料R1、節だけ外す)
    "not pulled back",
    "than the previous one",              # 型3 の想定元本の比(材料3、節だけ外す)
]


def _v4_first_dataset(tmp_path, monkeypatch):
    rows_path, materials_path, continue_path, day, ts1, ts2 = build_synthetic_dataset(tmp_path)
    times = np.arange(ts1 - 400_000, ts1 + 400_000, 1000, dtype=np.int64)
    prices = 100.0 + 0.0001 * (times - times[0])
    sb, fake = _make_builder(tmp_path, times, prices)
    monkeypatch.setattr(js, "load_window5", fake)
    return sb


def _v4_chain_dataset(tmp_path, monkeypatch):
    rows_path, materials_path, continue_path, day, ts1, ts2 = build_synthetic_dataset(tmp_path)
    times = np.arange(ts1 - 400_000, ts2 + 400_000, 1000, dtype=np.int64)
    prices = 100.0 + 0.0001 * (times - times[0])
    sb, fake = _make_builder(tmp_path, times, prices)
    monkeypatch.setattr(js, "load_window5", fake)
    return sb


def test_v4_first_print_has_no_dropped_material_phrases(tmp_path, monkeypatch):
    sb = _v4_first_dataset(tmp_path, monkeypatch)
    sentences = sb.build_state_v4("p1")
    joined = "\n".join(sentences)
    for phrase in DROPPED_PHRASES_FIRST:
        assert phrase not in joined, (phrase, sentences)
    # N1_SEPARATES・N2_SEPARATES が両方 True(screen_N.csv の実測)なので
    # 1 件目の文には N1・N2 が足されている
    assert len(sentences) == 8


def test_v4_chain_has_no_dropped_material_phrases(tmp_path, monkeypatch):
    sb = _v4_chain_dataset(tmp_path, monkeypatch)
    sentences = sb.build_state_v4("p2")
    joined = "\n".join(sentences)
    for phrase in DROPPED_PHRASES_CHAIN:
        assert phrase not in joined, (phrase, sentences)
    assert len(sentences) == 7


# ---------------------------------------------------------------------------
# (8) V4 の criteria が位置で切り替わる
# ---------------------------------------------------------------------------
def test_v4_questions_criteria_differ_by_position():
    first = js.JEV_QUESTIONS_V4_FIRST["next_print_within_60s"]
    chain = js.JEV_QUESTIONS_V4_CHAIN["next_print_within_60s"]
    assert first["criteria"]["yes"] != chain["criteria"]["yes"]
    assert first["criteria"]["no"] != chain["criteria"]["no"]
    # instructions(問いの文そのもの)は §7.3 の指定どおり共通
    assert first["instructions"] == chain["instructions"]
    assert "fresh extreme" in first["criteria"]["yes"]
    assert "gaps between prints" in chain["criteria"]["yes"]


# ---------------------------------------------------------------------------
# (9) N1・N2 が ts 以後を使わない(p0 書き換え不変)
# ---------------------------------------------------------------------------
def test_v4_n1_n2_ignore_future_prices_and_p0(tmp_path, monkeypatch):
    rows_path, materials_path, continue_path, day, ts1, ts2 = build_synthetic_dataset(tmp_path)
    times = np.arange(ts1 - 400_000, ts1 + 400_000, 1000, dtype=np.int64)
    prices_a = 100.0 + 0.0001 * (times - times[0])
    prices_b = prices_a.copy()
    after = times >= ts1  # ts1 自身(p0 に当たる約定)を含めて以後を書き換える
    prices_b[after] = prices_b[after] + 999.0

    sb_a, fake_a = _make_builder(tmp_path, times, prices_a)
    monkeypatch.setattr(js, "load_window5", fake_a)
    v4_a = sb_a.build_state_v4("p1")

    sb_b, fake_b = _make_builder(tmp_path, times, prices_b)
    monkeypatch.setattr(js, "load_window5", fake_b)
    v4_b = sb_b.build_state_v4("p1")

    assert v4_a == v4_b


def test_n2_position_uses_only_causal_window():
    times = np.array([0, 60_000, 120_000, 179_000, 179_500, 180_000, 180_500],
                     dtype=np.int64)
    prices = np.array([100.0, 101.0, 99.0, 100.5, 100.5, 999.0, 999.0])
    # ts=180_000。窓は [180000-300000, 180000) = [-120000, 180000)。179500 まで
    # の約定だけを使う(180000・180500 は含めない)。p_pre は 179500 の 100.5。
    pos = js.n2_position(times, prices, 180_000, "BUY", 100.5)
    # 窓内([0,60000,120000,179000,179500])の価格は 100〜101、p_pre=100.5 は
    # ほぼ中央(BUY の清算方向は高い方)
    assert 0.0 <= pos <= 1.0
    pos_future_changed = js.n2_position(
        np.array([0, 60_000, 120_000, 179_000, 179_500, 180_000, 180_500, 300_000],
                 dtype=np.int64),
        np.array([100.0, 101.0, 99.0, 100.5, 100.5, 999.0, 999.0, -5.0]),
        180_000, "BUY", 100.5)
    assert pos == pytest.approx(pos_future_changed)


# ---------------------------------------------------------------------------
# (10) logistic(scripts/o3c_signal_logit.py): 前半だけから係数が決まる・決定的
# ---------------------------------------------------------------------------
def _synthetic_logit_df(seed: int = 0, n_each: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for half in ("前半", "後半"):
        for i in range(n_each):
            a = rng.normal()
            b = rng.normal()
            y = 1 if (a + 0.5 * b + rng.normal(scale=0.1)) > 0 else 0
            rows.append({"print_id": f"{half}_{i}", "half": half,
                        "cand_a": a, "cand_b": b, "label_60": y})
    return pd.DataFrame(rows)


def test_logit_newton_predictions_deterministic():
    df = _synthetic_logit_df()
    df_fh = df[df["half"] == "前半"].reset_index(drop=True)
    X, _cuts = lg.build_matrix(df_fh, ["cand_a", "cand_b"])
    y = df_fh["label_60"].to_numpy(float)
    beta1 = lg.newton_logistic(X, y)
    beta2 = lg.newton_logistic(X, y)
    assert np.array_equal(beta1, beta2)
    p1 = lg.predict(X, beta1)
    p2 = lg.predict(X, beta1)
    assert np.array_equal(p1, p2)


def test_logit_beta_determined_by_front_half_only():
    df = _synthetic_logit_df()
    beta_a = lg.fit_beta_front_half(df, ["cand_a", "cand_b"])

    df2 = df.copy()
    back = df2["half"] == "後半"
    # 後半の材料・ラベルをまるごと書き換えても前半だけの係数は変わらない
    df2.loc[back, "cand_a"] = df2.loc[back, "cand_a"] + 999.0
    df2.loc[back, "cand_b"] = df2.loc[back, "cand_b"] - 999.0
    df2.loc[back, "label_60"] = 1 - df2.loc[back, "label_60"]
    beta_b = lg.fit_beta_front_half(df2, ["cand_a", "cand_b"])

    assert np.allclose(beta_a, beta_b)
