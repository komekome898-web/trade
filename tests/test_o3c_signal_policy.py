"""`scripts/o3c_signal_policy.py`(方策の模擬 — 清算の列に沿って判断を繋ぐ、改訂2 + R2.7:
判断の出所は前半で固定した logistic、Jev は呼ばない)の試験。

**測るもの**(委任文〈段1〉【作るもの】3、(1)〜(9)、+ 反証者レビュー8〈R2.7〉の直し)
  1. 状態機械: 建玉なし/順張り/逆張り × 止まる/続く/わからない の 9 通りの行動が
     設計の表どおり(合成の連鎖で1本ずつ)。
  2. 型 A は同じプリントで新規を開かない、型 B はドテン。
  3. 出口の時刻 = 最後のプリント + 60 秒。
  4. 遅れ d(0.5/1/2 秒を含む)で `at_or_after` が動く。
  5. 帯の3択が改訂2(R2.2)の値。
  6. 判断が ts 以前だけを使う(ts 以後の約定・清算を変えても判断が同じ。p₀ を
     書き換えても同じ)。
  7. 完全な判断は事後のラベル(連鎖の道筋の位置)だけを使う参照点(損益の上限ではない)。
  8. 損益の符号が建玉の向き(清算の向きではない)。
  9. `paper_logs/` を開かない。
  + 判定語なし。
  R2.7-C1: 基準率2値(1件目0.436/連鎖の中0.690)の判断が帯どおり。
  R2.7-C3: 出口(連鎖の終わり)の強制決済の行が per-print の道筋に出て、その
    「レグ損益_bp」の合算が連鎖の損益(`pnl_bp`)と一致する。
  R2.7-D3: per-print の道筋に建玉(向き・無し)の列がある。
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location(
    "o3c_signal_policy", ROOT / "scripts" / "o3c_signal_policy.py")
sp = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(sp)

cont = sp.cont  # 前段の道具(流用元)

have_data = (sp.ROWS_CONTINUE.exists() and sp.ROWS_MATERIALS.exists()
            and sp.lg.CONFIG_FIRST.exists() and sp.lg.CONFIG_CHAIN.exists()
            and sp.lg.ECDF_FIRST.exists() and sp.lg.ECDF_CHAIN.exists())
needs_data = pytest.mark.skipif(not have_data, reason="前段の出力(rows_continue/"
                                "materials/logit config・npz)が無い")


# ---------------------------------------------------------------------------
# (1) 状態機械 9 通り × 型 A/B(設計の用語表どおり)
# ---------------------------------------------------------------------------
def test_state_machine_matches_design_table_9x2():
    P = sp
    expect = {
        (P.POS_NONE, P.JUDGE_STOP): {
            P.TYPE_A: (P.POS_AGAINST, P.ACT_NEW_AGAINST),
            P.TYPE_B: (P.POS_AGAINST, P.ACT_NEW_AGAINST)},
        (P.POS_NONE, P.JUDGE_CONTINUE): {
            P.TYPE_A: (P.POS_WITH, P.ACT_NEW_WITH),
            P.TYPE_B: (P.POS_WITH, P.ACT_NEW_WITH)},
        (P.POS_NONE, P.JUDGE_UNKNOWN): {
            P.TYPE_A: (P.POS_NONE, P.ACT_NOTHING),
            P.TYPE_B: (P.POS_NONE, P.ACT_NOTHING)},
        (P.POS_WITH, P.JUDGE_STOP): {
            P.TYPE_A: (P.POS_NONE, P.ACT_CLOSE),
            P.TYPE_B: (P.POS_AGAINST, P.ACT_FLIP_AGAINST)},
        (P.POS_WITH, P.JUDGE_CONTINUE): {
            P.TYPE_A: (P.POS_WITH, P.ACT_HOLD),
            P.TYPE_B: (P.POS_WITH, P.ACT_HOLD)},
        (P.POS_WITH, P.JUDGE_UNKNOWN): {
            P.TYPE_A: (P.POS_WITH, P.ACT_HOLD),
            P.TYPE_B: (P.POS_WITH, P.ACT_HOLD)},
        (P.POS_AGAINST, P.JUDGE_STOP): {
            P.TYPE_A: (P.POS_AGAINST, P.ACT_HOLD),
            P.TYPE_B: (P.POS_AGAINST, P.ACT_HOLD)},
        (P.POS_AGAINST, P.JUDGE_CONTINUE): {
            P.TYPE_A: (P.POS_NONE, P.ACT_CLOSE),
            P.TYPE_B: (P.POS_WITH, P.ACT_FLIP_WITH)},
        (P.POS_AGAINST, P.JUDGE_UNKNOWN): {
            P.TYPE_A: (P.POS_AGAINST, P.ACT_HOLD),
            P.TYPE_B: (P.POS_AGAINST, P.ACT_HOLD)},
    }
    assert len(expect) == 9  # 建玉 3 × 判断 3
    for (pos, judge), by_type in expect.items():
        for ptype, exp in by_type.items():
            got = P.next_action(pos, judge, ptype)
            assert got == exp, (pos, judge, ptype, got, exp)


# ---------------------------------------------------------------------------
# (2) 型 A は同じプリントで新規を開かない・型 B はドテン(合成の連鎖で1本ずつ)
# ---------------------------------------------------------------------------
def test_type_a_no_reopen_same_print_type_b_flips():
    P = sp

    def fake_price(t_ms):
        return 100.0 + float(t_ms) / 1.0e7, t_ms

    prints = [{"print_id": "a", "ts_ms": 0, "side": "BUY"},
             {"print_id": "b", "ts_ms": 10_000, "side": "BUY"},
             {"print_id": "c", "ts_ms": 20_000, "side": "BUY"}]
    judgments = [P.JUDGE_CONTINUE, P.JUDGE_CONTINUE, P.JUDGE_STOP]
    end = 20_000 + P.CASCADE_END_GAP_S * 1000

    res_a = P.simulate_cascade(prints, judgments, 1.0, P.TYPE_A, 0, fake_price, end)
    # c で「止まる」: 型 A は決済だけ(同じプリントで新規_逆張りは開かない)
    assert res_a["path"][2]["行動"] == P.ACT_CLOSE
    assert res_a["path"][2]["建玉"] == P.POS_NONE
    assert res_a["n_entries"] == 1

    res_b = P.simulate_cascade(prints, judgments, 1.0, P.TYPE_B, 0, fake_price, end)
    # c で「止まる」: 型 B はドテン(順張り→逆張りへ反転)し、以後その建玉のまま
    assert res_b["path"][2]["行動"] == P.ACT_FLIP_AGAINST
    assert res_b["path"][2]["建玉"] == P.POS_AGAINST
    assert res_b["n_entries"] == 2  # 最初の新規 + ドテンの新規


# ---------------------------------------------------------------------------
# (3) 出口の時刻 = 最後のプリント + 60 秒
# ---------------------------------------------------------------------------
def _fake_price_fn(queries: list):
    def fn(t_ms):
        queries.append(int(t_ms))
        return float(t_ms), int(t_ms)
    return fn


def test_exit_time_is_last_print_plus_60s():
    P = sp
    prints = [{"print_id": "a", "ts_ms": 1_000_000, "side": "BUY"},
             {"print_id": "b", "ts_ms": 1_030_000, "side": "BUY"}]
    judgments = [P.JUDGE_CONTINUE, P.JUDGE_CONTINUE]
    cascade_end_ts = prints[-1]["ts_ms"] + P.CASCADE_END_GAP_S * 1000
    assert cascade_end_ts == prints[-1]["ts_ms"] + 60_000
    queries = []
    P.simulate_cascade(prints, judgments, 1.0, P.TYPE_A, 3, _fake_price_fn(queries),
                       cascade_end_ts)
    assert queries == [prints[0]["ts_ms"] + 3000, cascade_end_ts + 3000]


# ---------------------------------------------------------------------------
# (4) 遅れ d(0.5/1/2 秒)で at_or_after が動く
# ---------------------------------------------------------------------------
def test_price_at_or_after_basic():
    times = np.array([0, 1000, 2000, 5000], dtype=np.int64)
    prices = np.array([10.0, 11.0, 12.0, 13.0])
    assert sp.price_at_or_after(times, prices, 1000) == (11.0, 1000)
    assert sp.price_at_or_after(times, prices, 1001) == (12.0, 2000)
    px, t = sp.price_at_or_after(times, prices, 100_000)
    assert px != px and t is None


def test_delay_grid_includes_half_second_and_is_applied_as_int_ms():
    P = sp
    assert P.DELAYS_S == (0.5, 1, 2)
    prints = [{"print_id": "a", "ts_ms": 0, "side": "BUY"}]
    judgments = [P.JUDGE_CONTINUE]
    end = 0 + P.CASCADE_END_GAP_S * 1000
    for delay in P.DELAYS_S:
        queries = []
        P.simulate_cascade(prints, judgments, 1.0, P.TYPE_A, delay,
                           _fake_price_fn(queries), end)
        assert queries[0] == int(round(delay * 1000))  # 0.5秒 -> 500ms、端数なし


# ---------------------------------------------------------------------------
# (5) 帯の3択が改訂2(R2.2)の値
# ---------------------------------------------------------------------------
def test_band_thresholds_match_revision2():
    P = sp
    assert P.BAND_1ST == (0.42, 0.58)
    assert P.BAND_CHAIN == (0.70, 0.76)
    # 1件目: p<0.42 止まる/[0.42,0.58) わからない/p>=0.58 続く
    assert P.judge_3way_from_prob(0.41, P.POS_1ST) == P.JUDGE_STOP
    assert P.judge_3way_from_prob(0.42, P.POS_1ST) == P.JUDGE_UNKNOWN
    assert P.judge_3way_from_prob(0.579, P.POS_1ST) == P.JUDGE_UNKNOWN
    assert P.judge_3way_from_prob(0.58, P.POS_1ST) == P.JUDGE_CONTINUE
    # 連鎖の中: p<0.70 止まる/[0.70,0.76) わからない/p>=0.76 続く
    assert P.judge_3way_from_prob(0.69, P.POS_CHAIN) == P.JUDGE_STOP
    assert P.judge_3way_from_prob(0.70, P.POS_CHAIN) == P.JUDGE_UNKNOWN
    assert P.judge_3way_from_prob(0.759, P.POS_CHAIN) == P.JUDGE_UNKNOWN
    assert P.judge_3way_from_prob(0.76, P.POS_CHAIN) == P.JUDGE_CONTINUE
    # 確率が読めない -> わからない
    assert P.judge_3way_from_prob(None, P.POS_1ST) == P.JUDGE_UNKNOWN
    assert P.judge_3way_from_prob(float("nan"), P.POS_CHAIN) == P.JUDGE_UNKNOWN
    # logistic 2値(0.5、わからない無し)
    assert P.judge_2way_from_prob(0.5) == P.JUDGE_CONTINUE
    assert P.judge_2way_from_prob(0.499999) == P.JUDGE_STOP


# ---------------------------------------------------------------------------
# R2.7-C1: 基準率2値(1件目0.436/連鎖の中0.690)の判断が帯どおり
# ---------------------------------------------------------------------------
def test_base_rate_two_value_policy_matches_r27_thresholds():
    P = sp
    assert P.BASE_RATE_1ST == 0.436
    assert P.BASE_RATE_CHAIN == 0.690
    # 1件目: p>=0.436 で続く、それ未満は止まる(わからない無し)
    assert P.judge_2way_baserate_from_prob(0.436, P.POS_1ST) == P.JUDGE_CONTINUE
    assert P.judge_2way_baserate_from_prob(0.435999, P.POS_1ST) == P.JUDGE_STOP
    # 連鎖の中: p>=0.690 で続く、それ未満は止まる
    assert P.judge_2way_baserate_from_prob(0.690, P.POS_CHAIN) == P.JUDGE_CONTINUE
    assert P.judge_2way_baserate_from_prob(0.689999, P.POS_CHAIN) == P.JUDGE_STOP
    # 同じ確率値でも位置が違えば判断が変わりうる(閾値が位置ごとに違うことの確認)
    assert P.judge_2way_baserate_from_prob(0.5, P.POS_1ST) == P.JUDGE_CONTINUE
    assert P.judge_2way_baserate_from_prob(0.5, P.POS_CHAIN) == P.JUDGE_STOP
    # 確率が読めない -> わからない
    assert P.judge_2way_baserate_from_prob(None, P.POS_1ST) == P.JUDGE_UNKNOWN
    assert P.judge_2way_baserate_from_prob(float("nan"), P.POS_CHAIN) == P.JUDGE_UNKNOWN
    # 方策一覧に入っていること(R2.7: 7本)
    assert "logistic_2値基準率" in P.JUDGED_POLICIES
    assert len(P.ALL_POLICIES) == 7
    assert P.judgments_for_policy(
        [{"print_id": "a", "ts_ms": 0, "side": "BUY"}], "logistic_2値基準率",
        {"a": 0.5}, {"a": P.POS_1ST}) == [P.JUDGE_CONTINUE]


def test_position_of_uses_cand1_zero_rule():
    assert sp.position_of(0) == sp.POS_1ST
    assert sp.position_of(0.0) == sp.POS_1ST
    assert sp.position_of(1) == sp.POS_CHAIN
    assert sp.position_of(5) == sp.POS_CHAIN


# ---------------------------------------------------------------------------
# (6) 判断が ts 以前だけを使う
# ---------------------------------------------------------------------------
def test_judgments_depend_only_on_pre_ts_inputs_not_future_data():
    P = sp
    prints = [{"print_id": "a", "ts_ms": 0, "side": "BUY", P.MAT1_COL: 0.0},
             {"print_id": "b", "ts_ms": 10_000, "side": "BUY", P.MAT1_COL: 1.0}]
    logit_prob_of = {"a": 0.9, "b": 0.1}
    position_of_pid = {"a": P.POS_1ST, "b": P.POS_CHAIN}

    def run():
        out = {}
        for policy in P.JUDGED_POLICIES:
            out[policy] = P.judgments_for_policy(prints, policy, logit_prob_of,
                                                  position_of_pid)
        return out

    base = run()
    # p0・ts以後の約定・清算に相当するものは `prints` にも `judgments_for_policy` の
    # 引数にも渡していない ── 関数のシグネチャ自体が ts 以前の情報(print_id・ts・side・
    # mat1・あらかじめ計算済みの確率と位置)しか受け取れない。ここでは、無関係の
    # 「未来」を模したキー(p0 や約定情報)を prints の辞書に混ぜても結果が変わらない
    # ことで、実装がそれらを一切参照していないことを確かめる。
    prints_with_future = [dict(p) for p in prints]
    prints_with_future[0]["p0"] = 999_999.0
    prints_with_future[0]["future_trade_price"] = 1.0
    prints_with_future[1]["p0"] = -1.0
    for policy in P.JUDGED_POLICIES:
        got = P.judgments_for_policy(prints_with_future, policy, logit_prob_of,
                                     position_of_pid)
        assert got == base[policy]


# ---------------------------------------------------------------------------
# (7) 完全な判断は連鎖の道筋の位置だけを使う参照点(反証者レビュー8 致命-2:
#     「上限」の語は撤回。連鎖単位では他方策を下回ることがある)
# ---------------------------------------------------------------------------
def test_perfect_judgment_uses_position_in_cascade_only():
    P = sp
    assert [P.judge_perfect(i, 3) for i in range(3)] == [
        P.JUDGE_CONTINUE, P.JUDGE_CONTINUE, P.JUDGE_STOP]
    assert [P.judge_perfect(i, 1) for i in range(1)] == [P.JUDGE_STOP]  # 単発


def test_source_does_not_call_perfect_judgment_an_upper_bound():
    """反証者レビュー8 致命-2: 用語表・R2.3 の「上限」という語は撤回済み。
    `judge_perfect` の docstring にその撤回の理由が書かれていることも確かめる。"""
    src = (ROOT / "scripts" / "o3c_signal_policy.py").read_text()
    assert "上限ではない" in src
    assert "= 上限" not in src


# ---------------------------------------------------------------------------
# R2.7-C3・D3: 出口の強制決済の行が per-print の道筋に出て、その「レグ損益_bp」の
# 合算が連鎖の損益(pnl_bp)と一致する。建玉の列がある。
# ---------------------------------------------------------------------------
def test_exit_leg_row_appears_in_path_and_sums_to_cascade_pnl():
    P = sp

    def price_fn(t_ms):
        return 100.0 + t_ms / 1.0e7, t_ms

    # 型B(ドテン)で連鎖が建玉を持ったまま終わる合成連鎖(前半200本の実測でも
    # 型Bは入った連鎖の100%がこの「見えないレグ」に依存していた、致命-3)。
    prints = [{"print_id": "a", "ts_ms": 0, "side": "SELL"},
             {"print_id": "b", "ts_ms": 15_000, "side": "SELL"}]
    judgments = [P.JUDGE_STOP, P.JUDGE_CONTINUE]
    end = 15_000 + P.CASCADE_END_GAP_S * 1000
    res = P.simulate_cascade(prints, judgments, -1.0, P.TYPE_B, 0, price_fn, end)

    # path の最後の行が出口の強制決済(判断「終わり」・行動「決済」)
    last = res["path"][-1]
    assert last["判断"] == P.JUDGE_EXIT == "終わり"
    assert last["行動"] == P.ACT_CLOSE == "決済"
    assert last["print_id"] is None
    assert last["ts_ms"] == end
    assert last["建玉"] == P.POS_NONE
    assert last["レグ損益_bp"] is not None

    # レグ損益_bp の合算(None は0扱い)が連鎖の損益と一致する
    leg_sum = sum(r["レグ損益_bp"] for r in res["path"] if r["レグ損益_bp"] is not None)
    assert leg_sum == pytest.approx(res["pnl_bp"])

    # 建玉(D3)の列がどの行にもある(向きが状態機械の遷移どおり)
    assert [r["建玉"] for r in res["path"]] == [
        P.POS_AGAINST, P.POS_WITH, P.POS_NONE]

    # 型Aで途中で決済されるだけ(出口まで建玉が残らない)場合は出口の行が付かない
    judgments_a = [P.JUDGE_CONTINUE, P.JUDGE_CONTINUE, P.JUDGE_STOP]
    prints_a = [{"print_id": "x", "ts_ms": 0, "side": "BUY"},
               {"print_id": "y", "ts_ms": 10_000, "side": "BUY"},
               {"print_id": "z", "ts_ms": 20_000, "side": "BUY"}]
    end_a = 20_000 + P.CASCADE_END_GAP_S * 1000
    res_a = P.simulate_cascade(prints_a, judgments_a, 1.0, P.TYPE_A, 0, price_fn, end_a)
    assert len(res_a["path"]) == 3  # 出口の行は付かない(型Aの決済で既に建玉なし)
    assert res_a["path"][-1]["判断"] != P.JUDGE_EXIT
    leg_sum_a = sum(r["レグ損益_bp"] for r in res_a["path"] if r["レグ損益_bp"] is not None)
    assert leg_sum_a == pytest.approx(res_a["pnl_bp"])


# ---------------------------------------------------------------------------
# (8) 損益の符号が建玉の向き(清算の向きではない、手計算と突き合わせ)
# ---------------------------------------------------------------------------
def test_pnl_sign_follows_position_direction_not_liquidation_side():
    P = sp

    def price_fn(t_ms):
        return 100.0 + t_ms / 1.0e7, t_ms

    # SELL の清算(s_sign=-1)。1件目「止まる」→ 逆張りで入る(entry_dir = +1、
    # 清算の向きとは逆)。価格は単調増加なので、逆張り(+1)の建玉は「勝つ」はず。
    prints = [{"print_id": "a", "ts_ms": 0, "side": "SELL"},
             {"print_id": "b", "ts_ms": 10_000, "side": "SELL"}]
    judgments = [P.JUDGE_STOP, P.JUDGE_UNKNOWN]  # 逆張りで入り、ホールド
    end = 10_000 + P.CASCADE_END_GAP_S * 1000
    res = P.simulate_cascade(prints, judgments, -1.0, P.TYPE_A, 0, price_fn, end)
    assert res["path"][0]["行動"] == P.ACT_NEW_AGAINST
    assert res["path"][0]["建玉"] == P.POS_AGAINST
    assert res["pnl_bp"] > 0  # 価格が上がる経路で逆張り(建玉の向き=+1)は正の損益

    # 同じ価格経路・同じ判断列で、順張り新規(建玉の向き=-1相当)なら符号が反転する
    # ことを、同じ経路の「全部逆張り/全部順張り」基準で確かめる(手計算どおり符号だけ逆)。
    res_i = P.simulate_baseline(prints, -1.0, P.POS_AGAINST, 0, price_fn, end)
    res_ii = P.simulate_baseline(prints, -1.0, P.POS_WITH, 0, price_fn, end)
    assert res_i["pnl_bp"] == pytest.approx(-res_ii["pnl_bp"])


# ---------------------------------------------------------------------------
# (9) `paper_logs/` を開かない
# ---------------------------------------------------------------------------
def test_source_never_opens_paper_logs():
    src = (ROOT / "scripts" / "o3c_signal_policy.py").read_text().splitlines()
    hits = [ln for ln in src if "paper_logs" in ln]
    assert hits and all(
        ln.lstrip().startswith(("#", "*", '"""', "設計:", "委任文:"))
        or "開かない" in ln or "使わない" in ln for ln in hits), hits


def test_source_never_calls_jev_client_evaluate():
    """段1では Jev を 1 回も呼ばない(委任文の厳守事項)。`client.evaluate(` /
    `JevClient(` の呼び出しがソースに無いことで確かめる。"""
    src = (ROOT / "scripts" / "o3c_signal_policy.py").read_text()
    assert "JevClient(" not in src
    assert ".evaluate(" not in src


# ---------------------------------------------------------------------------
# 判定語
# ---------------------------------------------------------------------------
def test_check_no_banned_raises_on_verdict_words():
    for w in sp.BANNED_WORDS:
        with pytest.raises(SystemExit):
            sp.check_no_banned(f"これは{w}です", "test")
    sp.check_no_banned("判定語の無い普通の文", "test")


@needs_data
def test_no_verdict_words_in_real_tables_md_if_present():
    out = sp.DEFAULT_OUT / "tables.md"
    if not out.exists():
        pytest.skip("段1がまだこの環境で実行されていない")
    txt = out.read_text()
    for w in sp.BANNED_WORDS:
        assert w not in txt


# ---------------------------------------------------------------------------
# R2.7-D1: 表の行数の決定式(judge_counts=24・dist_table=84・position_breakdown=42)
# ---------------------------------------------------------------------------
def test_judge_count_table_has_24_rows_decision_formula():
    """位置2×判断3×方策4(logistic_3択・logistic_2値0.5・logistic_2値基準率・規則)= 24。
    観測されなかった組(例: 規則は「わからない」を持たない)も件数0の行として出る。"""
    P = sp
    rows = P.build_judge_count_table({})  # 空の実測でも行数は変わらない(決定的)
    assert len(rows) == 24
    assert all(r["件数"] == 0 for r in rows)
    policies = {r["方策"] for r in rows}
    assert policies == set(P.COUNT_JUDGE_POLICIES)
    assert "完全な判断" not in policies  # ラベルの位置で決まる別種の判断なので含めない
    positions = {r["位置"] for r in rows}
    assert positions == {P.POS_1ST, P.POS_CHAIN}
    judges = {r["判断"] for r in rows}
    assert judges == {P.JUDGE_STOP, P.JUDGE_CONTINUE, P.JUDGE_UNKNOWN}
    # 実測を1件混ぜても行数は変わらず、その1件の件数だけ反映される
    rows2 = P.build_judge_count_table({("規則", P.POS_1ST, P.JUDGE_STOP): 200})
    assert len(rows2) == 24
    hit = [r for r in rows2 if r["方策"] == "規則" and r["位置"] == P.POS_1ST
          and r["判断"] == P.JUDGE_STOP]
    assert hit == [{"方策": "規則", "位置": P.POS_1ST, "判断": P.JUDGE_STOP, "件数": 200}]


def test_dist_and_position_tables_have_r27_row_counts():
    """dist_table = 方策7×型2×遅れ3×含める/含めない2 = 84。
    position_breakdown = 方策7×型2×位置3(1件目で入った/途中で入った/入らなかった)= 42。"""
    P = sp
    rows = []
    for policy in P.ALL_POLICIES:
        for ptype in (P.TYPE_A, P.TYPE_B):
            for delay in P.DELAYS_S:
                rows.append({"bundle_id": "b1", "day": "2024-01-01", "side": "BUY",
                            "方策": policy, "型": ptype, "遅れ_秒": delay,
                            "pnl_bp": 1.0, "建玉の回数": 1, "保有秒": 60.0,
                            "入った": 1, "欠測": 0, "最初に入った位置": "1件目で入った"})
    cdf = pd.DataFrame(rows)
    dist = P.build_dist_table(cdf)
    posb = P.build_position_breakdown(cdf)
    assert len(dist) == 84
    assert len(posb) == 42


# ---------------------------------------------------------------------------
# 段1: 前半だけを抜く(較正5,000件は後半なので除外は不要)・種で決定的
# ---------------------------------------------------------------------------
def test_sample_cascades_is_deterministic_for_fixed_seed():
    pool = [f"c{i}" for i in range(50)]
    a = sp.sample_cascades(pool, seed=20260920, k=10)
    b = sp.sample_cascades(pool, seed=20260920, k=10)
    assert a == b
    assert len(a) == 10
    assert len(set(a)) == 10
    assert set(a) <= set(pool)


@needs_data
def test_stage1_select_uses_front_half_only_and_counts_are_consistent():
    info = sp.stage1_select(k=200)
    assert info["抜いた本数"] == 200
    sizes = sum(info["抜いた本数の内訳(単発/2件/3件以上)"].values())
    assert sizes == 200
    # 前半だけを対象にしていること(全連鎖のプリントの half 列を確かめる)
    df = sp.load_prints_half(sp.ROWS_CONTINUE, "前半")
    assert (df["half"] == "前半").all()
    for prints in list(info["cascades"].values())[:5]:
        for pr in prints:
            assert pr["half"] == "前半"


@needs_data
def test_stage1_output_present_and_row_estimate_recorded():
    summary_path = sp.DEFAULT_OUT / "summary.json"
    if not summary_path.exists():
        pytest.skip("段1がまだこの環境で実行されていない")
    import json
    summary = json.loads(summary_path.read_text())
    assert summary["抜いた連鎖の本数"] == 200
    assert summary["種"] == sp.SEED
    assert set(summary["方策"]) == set(sp.ALL_POLICIES)
