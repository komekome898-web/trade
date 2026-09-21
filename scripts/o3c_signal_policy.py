#!/usr/bin/env python3
"""清算を起点とした値動きの予測可能性 — 方策の模擬(清算の列に沿って判断を繋ぐ)の道具
(2026-09-20、**改訂2 + R2.7**: 判断の出所を Jev から前半で固定した logistic に置き換え、
反証者レビュー8の致命 C1・C3・直すべき D3 を受けて直した版)。

設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_POLICY_DESIGN_2026-09-20.md`(改訂2・R2.7が優先)
委任文(段1): `docs/DATA/delegations/20260920_o3c_signal_policy2_prompt.md`
反証者: `docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW8_2026-09-20.md`

**この道具がすること(段1 = 前半の連鎖 200 本だけ)**
  - 母集団: `rows_continue.csv.gz` の `half == "前半"` の `print` 行を `bundle_id`
    (=連鎖、直前から60秒以内なら繋いだもの)でまとめ、種 20260920 で 200 本抜く。
    5,000 件の較正サンプルは後半なので、前半には重ならない(設計 §6)。
  - 各プリントの判断は、前半で固定した logistic(`o3c_signal_logit.apply_frozen_rank`
    + `config/o3c_signal_logit_{first,chain}.yaml` + `logit_ecdf_{first,chain}.npz`、
    すべて読むだけ)から出る確率を、改訂2 R2.2 の帯(1件目 [0.42,0.58)・連鎖の中
    [0.70,0.76) が「わからない」)で 3 択にする。**この道具は Jev を 1 回も呼ばない。**
  - 用語表の状態機械(建玉なし/順張り/逆張り × 止まる/続く/わからない の 9 通り ×
    型A〈決済〉/型B〈ドテン〉)で方策を模擬する。方策 = R2.7(**7 本**): logistic_3択・
    logistic_2値(0.5)・logistic_2値(基準率、1件目0.436/連鎖の中0.690)・規則(材料1)・
    全部逆張り・全部順張り・完全な判断(事後のラベルを使った参照 ── 損益の上限ではない、
    反証者レビュー8 致命-2で「上限」の語を撤回)。
  - 遅れ d = 0.5/1/2 秒(R2.4)。約定は `at_or_after(t+d)`。出口 = 連鎖の終わり
    (最後のプリント + 60 秒)+ d。損益は建玉の向きで符号(清算の向きではない)。
    連鎖の終わりで建玉を強制決済したレグは per-print 出力にも 1 行出す(判断「終わり」・
    行動「決済」・約定価格・そのレグの損益。反証者レビュー8 致命-3)。
  - 連鎖ごとの損益の分布(中央値・四分位・負の割合・日等重み平均・日クラスタSE)を
    方策×型×遅れで、「わからない」で入らなかった連鎖を 0 として含める表/含めない表、
    位置別(1件目で入った/途中で入った/入らなかった)の内訳、判断の件数・行動の件数。

**判定語(陽性/陰性/有意/差あり/検出されず/支持/棄却)は書かない。`paper_logs/` は
開かない。確率(logistic の生の値)そのものは repo に入るファイルには書かない
(判断のラベル・損益・行動は書く。前段の Jev 確率を data/ にだけ置く慣行に倣う)。**

**前版との関係**: このファイルの前版(2026-09-20 の別の委任、Jev を判断に使う版)は
git 履歴にのみ残す(改訂2で Jev 判断が「使わない」に変わったため、この版で置き換えた
── 委任文の「使えるなら使い、使わないなら消さずに残す」は git 履歴で満たす。
状態機械・価格キャッシュ・出力の小道具は前版から流用)。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# 前段の道具をそのまま流用(state 作り・at_or_after 系の下請け関数・表の小道具)。
_spec_cont = importlib.util.spec_from_file_location(
    "o3c_signal_continue", _HERE / "o3c_signal_continue.py")
cont = importlib.util.module_from_spec(_spec_cont)
assert _spec_cont.loader is not None
_spec_cont.loader.exec_module(cont)

# logistic(前半で固定した係数・経験分布を読むだけ)。
_spec_lg = importlib.util.spec_from_file_location(
    "o3c_signal_logit", _HERE / "o3c_signal_logit.py")
lg = importlib.util.module_from_spec(_spec_lg)
assert _spec_lg.loader is not None
_spec_lg.loader.exec_module(lg)

# 段2(後半5,000件)で使った frozen-rank 適用の道具(`compute_logit_probs`・
# `position_of`)を前半にもそのまま流用する(同じ経路を使うことが目的、D5 の精神)。
_spec_s2 = importlib.util.spec_from_file_location(
    "o3c_signal_stage2", _HERE / "o3c_signal_stage2.py")
stage2 = importlib.util.module_from_spec(_spec_s2)
assert _spec_s2.loader is not None
_spec_s2.loader.exec_module(stage2)

# StateBuilder(N2 の計算に `_trades_for_day` だけを使う。Jev は呼ばない)。
_spec_js = importlib.util.spec_from_file_location(
    "o3c_jev_state", _HERE / "o3c_jev_state.py")
js = importlib.util.module_from_spec(_spec_js)
assert _spec_js.loader is not None
_spec_js.loader.exec_module(js)

REPO_ROOT = _HERE.parent
NAN = float("nan")

BANNED_WORDS = cont.BANNED_WORDS
check_no_banned = cont.check_no_banned
quantiles = cont.quantiles
mean_se_cluster = cont.mean_se_cluster
day_equal_weight_mean = cont.day_equal_weight_mean
md5_of = cont.md5_of
write_csv = cont.write_csv
md_table = cont.md_table
count_numeric_cells = cont.count_numeric_cells
normalize_rows = cont.normalize_rows
_fmt = cont._fmt
_f = cont._f
STALENESS_MS = cont.STALENESS_MS  # 300_000(穴)
gz_open_w = cont.gz_open_w
REACT_SIGN = cont.REACT_SIGN

# ---------------------------------------------------------------------------
# 固定値(委任文・設計。変えるときは報告に列挙する)
# ---------------------------------------------------------------------------
SEED = 20260920
N_CASCADES_STAGE1 = 200         # 段1: 前半の連鎖から抜く本数(委任文 §2-2)
N_CASCADES_STAGE2 = 2000        # 段2: 後半の連鎖から抜く本数(段2委任文【作るもの】1)
DELAYS_S = (0.5, 1, 2)          # R2.4
MAIN_DELAY = 1                  # print 単位の詳細行・位置別内訳に使う代表の遅れ
                                 # (設計に無い判断: R2.4 は 3 通りを対等に扱い「主」を
                                 # 名指ししていない。旧版〈§7〉の 1 秒〈主〉を踏襲した)
CASCADE_END_GAP_S = 60          # 連鎖の終わり = 最後のプリント + 60 秒
PRICE_WINDOW_BACK_MS = 400_000
PRICE_WINDOW_FWD_MS = 400_000

ROWS_CONTINUE = (REPO_ROOT / "backtest_data" / "o3c_signal_continue_20260920"
                 / "rows_continue.csv.gz")
ROWS_MATERIALS = (REPO_ROOT / "backtest_data" / "o3c_signal_materials_20260920"
                  / "rows_materials.csv.gz")
CALIB_MANIFEST = (REPO_ROOT / "backtest_data" / "o3c_signal_continue_20260920" / "jev"
                  / "selection_manifest.json")  # 較正5,000件の選定(段2委任文【作るもの】1)
DATA_ROOT = cont.DEFAULT_DATA_ROOT
DEFAULT_OUT = (REPO_ROOT / "backtest_data" / "o3c_signal_policy_20260920"
              / "stage1_firsthalf")
DEFAULT_OUT_STAGE2 = (REPO_ROOT / "backtest_data" / "o3c_signal_policy_20260920"
                      / "stage2_secondhalf")
DELEGATION_STAGE1 = "docs/DATA/delegations/20260920_o3c_signal_policy2_prompt.md"
DELEGATION_STAGE2 = "docs/DATA/delegations/20260920_o3c_signal_policy2_stage2_prompt.md"
MAT1_COL = cont.MAT_COL[1]  # mat1_same_side_count_60s_and_elapsed(= cand_1 と同一)

# ---- 状態機械の記号(設計の用語表) ----------------------------------------
POS_NONE, POS_WITH, POS_AGAINST = "建玉なし", "順張り", "逆張り"
JUDGE_STOP, JUDGE_CONTINUE, JUDGE_UNKNOWN = "止まる", "続く", "わからない"
JUDGE_EXIT = "終わり"  # 連鎖の終わりの強制決済の行だけに使う専用ラベル(用語表の3択では
                       # ない。反証者レビュー8 致命-3、R2.7)
JUDGE_TP = "利確"      # 順張りの建玉を入り値基準の目標で閉じた行だけに使う専用ラベル
                       # (2026-09-21、L-355・L-356。用語表の3択ではない)
TYPE_A, TYPE_B = "A", "B"

# レグ(建玉 1 つ)の出口の理由。`simulate_cascade` の戻り値 `legs` に入る。
EXIT_TP = "利確"
EXIT_NEXT_PRINT = "次の清算で決済"
EXIT_CASCADE_END = "連鎖の終わり"

ACT_NEW_WITH = "新規_順張り"
ACT_NEW_AGAINST = "新規_逆張り"
ACT_NOTHING = "何もしない"
ACT_HOLD = "ホールド"
ACT_CLOSE = "決済"
ACT_FLIP_AGAINST = "ドテン_逆張り"   # 順張り建玉 → 止まる → 型B
ACT_FLIP_WITH = "ドテン_順張り"      # 逆張り建玉 → 続く → 型B

# 9 通り(建玉なし/順張り/逆張り × 止まる/続く/わからない)× 型 A/B。
# 建玉なしの 3 通りは型に依らない(そこに A/B の分岐は無い)。設計の用語表そのもの。
STATE_TABLE = {
    (POS_NONE, JUDGE_STOP): {
        TYPE_A: (POS_AGAINST, ACT_NEW_AGAINST), TYPE_B: (POS_AGAINST, ACT_NEW_AGAINST)},
    (POS_NONE, JUDGE_CONTINUE): {
        TYPE_A: (POS_WITH, ACT_NEW_WITH), TYPE_B: (POS_WITH, ACT_NEW_WITH)},
    (POS_NONE, JUDGE_UNKNOWN): {
        TYPE_A: (POS_NONE, ACT_NOTHING), TYPE_B: (POS_NONE, ACT_NOTHING)},
    (POS_WITH, JUDGE_STOP): {
        TYPE_A: (POS_NONE, ACT_CLOSE), TYPE_B: (POS_AGAINST, ACT_FLIP_AGAINST)},
    (POS_WITH, JUDGE_CONTINUE): {
        TYPE_A: (POS_WITH, ACT_HOLD), TYPE_B: (POS_WITH, ACT_HOLD)},
    (POS_WITH, JUDGE_UNKNOWN): {
        TYPE_A: (POS_WITH, ACT_HOLD), TYPE_B: (POS_WITH, ACT_HOLD)},
    (POS_AGAINST, JUDGE_STOP): {
        TYPE_A: (POS_AGAINST, ACT_HOLD), TYPE_B: (POS_AGAINST, ACT_HOLD)},
    (POS_AGAINST, JUDGE_CONTINUE): {
        TYPE_A: (POS_NONE, ACT_CLOSE), TYPE_B: (POS_WITH, ACT_FLIP_WITH)},
    (POS_AGAINST, JUDGE_UNKNOWN): {
        TYPE_A: (POS_AGAINST, ACT_HOLD), TYPE_B: (POS_AGAINST, ACT_HOLD)},
}
ACTIONS_NEEDING_PRICE = {ACT_NEW_WITH, ACT_NEW_AGAINST, ACT_CLOSE,
                         ACT_FLIP_AGAINST, ACT_FLIP_WITH}

# R2.7 の方策一覧(反証者レビュー8 致命-1: R2.2 が明示する「基準率で2値」比較列が
# 段1に無かったので足した)。9 通り(建玉状態×判断)の状態機械を実際に回すのは 5 つ
# (logistic_3択・logistic_2値0.5・logistic_2値基準率・規則・完全な判断)。
# 「全部逆張り/全部順張り」は用語表の「基準の方策 (i)(ii)」で、最初のプリントで一度だけ
# 入り判断を見ずに終わりまで持つ(状態機械を通らない。型 A/B の分岐が無い)。
JUDGED_POLICIES = ("logistic_3択", "logistic_2値0.5", "logistic_2値基準率", "規則",
                   "完全な判断")
POLICY_IS_BASELINE = {"全部逆張り": POS_AGAINST, "全部順張り": POS_WITH}
ALL_POLICIES = JUDGED_POLICIES + tuple(POLICY_IS_BASELINE.keys())  # 7 本(R2.7)

# R2.7 D1: 判断の件数表(judge_counts)は確率の閾値で「続く/止まる」を決める4方策だけを
# 対象にする(「完全な判断」はラベルの位置=連鎖内の最後かどうかで決まる別種の判断なので
# 含めない)。位置2×判断3×方策4 = 24 行(件数0の組も明示的に0行として出す)。
COUNT_JUDGE_POLICIES = ("logistic_3択", "logistic_2値0.5", "logistic_2値基準率", "規則")

# R2.2: 3択の帯(位置ごと、段2の較正から固定。ここでは読むだけで動かさない)。
BAND_1ST = (0.42, 0.58)     # 止まる: p<0.42 / わからない: [0.42,0.58) / 続く: p>=0.58
BAND_CHAIN = (0.70, 0.76)   # 止まる: p<0.70 / わからない: [0.70,0.76) / 続く: p>=0.76
POS_1ST, POS_CHAIN = "1件目", "連鎖の中"

# R2.7 致命-1: 「基準率で2値」の閾値(R2.2 の逐語「1件目0.436/連鎖の中0.690」)。
# わからない無し(2値)。§7.7 の後半5,000件の基準率(1件目0.436・連鎖の中0.690)そのもの。
BASE_RATE_1ST = 0.436
BASE_RATE_CHAIN = 0.690


def next_action(position: str, judgment: str, policy_type: str) -> tuple:
    """設計の用語表どおりの (次の建玉状態, 行動) を返す。9 通り × 型 A/B。"""
    return STATE_TABLE[(position, judgment)][policy_type]


# ===========================================================================
# 価格(at_or_after、穴 300 秒)
# ===========================================================================
def price_at_or_after(times: np.ndarray, prices: np.ndarray, t_ms: int,
                      tol: int = STALENESS_MS):
    """`t_ms` 以後で最も古い約定の価格。無ければ (NaN, None)。"""
    if times is None or times.size == 0:
        return NAN, None
    i = int(np.searchsorted(times, t_ms, side="left"))
    if i >= times.size:
        return NAN, None
    if int(times[i]) - int(t_ms) > tol:
        return NAN, None
    return float(prices[i]), int(times[i])


class PriceCache:
    """日ごとの約定(±`PRICE_WINDOW_*_MS`)をキャッシュし、任意の時刻の
    at_or_after 価格を返す(段4のホットパス)。"""

    def __init__(self, data_root: Path):
        self.data_root = data_root
        self._trade_cache: dict = {}
        self._window_cache: dict = {}

    def raw_at_or_after(self, t_ms: int, tol: int = STALENESS_MS):
        """遅れを足さない生の at_or_after(`price_fn` として渡す形。遅れの加算は
        呼び出し側〈simulate_cascade/simulate_baseline〉が行う — 二重加算を防ぐ)。"""
        day = cont.day_of_ms(int(t_ms))
        win = self._window_cache.get(day)
        if win is None:
            times, prices, _q, _miss, _need = cont.load_window5(
                self.data_root, day, self._trade_cache,
                PRICE_WINDOW_BACK_MS, PRICE_WINDOW_FWD_MS)
            win = (times, prices)
            self._window_cache[day] = win
            if len(self._window_cache) > 3:
                oldest = sorted(self._window_cache.keys())[0]
                if oldest != day:
                    del self._window_cache[oldest]
        return price_at_or_after(win[0], win[1], int(t_ms), tol)


# ===========================================================================
# 位置(1件目/連鎖の中)と判断(logistic の 3 択・2 値・規則・完全な判断)
# ===========================================================================
position_of = stage2.position_of  # cand_1 == 0 -> "1件目" / それ以外 -> "連鎖の中"


def judge_3way_from_prob(prob, position: str) -> str:
    """R2.2 の帯(位置ごと)で 3 択にする。確率が読めなければ「わからない」。"""
    if prob is None or not math.isfinite(float(prob)):
        return JUDGE_UNKNOWN
    p = float(prob)
    lo, hi = BAND_1ST if position == POS_1ST else BAND_CHAIN
    if p < lo:
        return JUDGE_STOP
    if p >= hi:
        return JUDGE_CONTINUE
    return JUDGE_UNKNOWN


def judge_2way_from_prob(prob) -> str:
    """R2.3 項目2: logistic を 0.5 で 2 値化(「わからない」無し)。"""
    if prob is None or not math.isfinite(float(prob)):
        return JUDGE_UNKNOWN  # 読めない場合だけ「わからない」扱い(通常は起きない)
    return JUDGE_CONTINUE if float(prob) >= 0.5 else JUDGE_STOP


def judge_2way_baserate_from_prob(prob, position: str) -> str:
    """R2.7 致命-1(R2.2 逐語「基準率で2値(1件目0.436/連鎖の中0.690)」)。位置ごとに
    閾値が違う2値化(「わからない」無し)。0.5 固定版〈`judge_2way_from_prob`〉との違いは
    閾値だけ。"""
    if prob is None or not math.isfinite(float(prob)):
        return JUDGE_UNKNOWN  # 読めない場合だけ「わからない」扱い(通常は起きない)
    thr = BASE_RATE_1ST if position == POS_1ST else BASE_RATE_CHAIN
    return JUDGE_CONTINUE if float(prob) >= thr else JUDGE_STOP


def judge_from_rule(mat1) -> str:
    """規則(材料1: 直前60秒の同じ側の件数)≥1 → 続く、0 → 止まる。わからない無し。"""
    v = _f(mat1)
    if not math.isfinite(v):
        v = 0.0
    return JUDGE_CONTINUE if v >= 1.0 else JUDGE_STOP


def judge_perfect(pos_in_cascade: int, cascade_len: int) -> str:
    """完全な判断 = 事後のラベル(この後60秒以内に同じ側の次の清算が来るか)を
    そのまま判断に使う参照点。**損益の上限ではない**(反証者レビュー8 致命-2で
    用語表・R2.3 の「上限」の語を撤回。当てているのは「続く/止まる」ラベルであって
    価格経路の損益ではないので、連鎖単位では他方策を下回ることがある)。
    連鎖の最後だけ「止まる」。"""
    return JUDGE_STOP if pos_in_cascade == cascade_len - 1 else JUDGE_CONTINUE


def judgments_for_policy(prints: list, policy: str, logit_prob_of: dict,
                         position_of_pid: dict) -> list:
    """判断は prints の ts・side・print_id(と、あらかじめ計算済みの logit_prob_of /
    position_of_pid)だけで決まる。価格・約定・清算の以後のデータには一切触れない
    (ts 以前だけを使う不変条件)。"""
    n = len(prints)
    if policy == "完全な判断":
        return [judge_perfect(i, n) for i in range(n)]
    if policy == "規則":
        return [judge_from_rule(p.get(MAT1_COL)) for p in prints]
    if policy == "logistic_3択":
        out = []
        for p in prints:
            pid = p["print_id"]
            pos = position_of_pid.get(pid, POS_1ST)
            out.append(judge_3way_from_prob(logit_prob_of.get(pid), pos))
        return out
    if policy == "logistic_2値0.5":
        return [judge_2way_from_prob(logit_prob_of.get(p["print_id"])) for p in prints]
    if policy == "logistic_2値基準率":
        out = []
        for p in prints:
            pid = p["print_id"]
            pos = position_of_pid.get(pid, POS_1ST)
            out.append(judge_2way_baserate_from_prob(logit_prob_of.get(pid), pos))
        return out
    raise ValueError(f"未知の方策: {policy}")


# ===========================================================================
# 連鎖(前半、bundle_id でまとめる。前段〈o3c_signal_continue〉の道具をそのまま使う)
# ===========================================================================
def size_bucket(n: int) -> str:
    if n <= 1:
        return "単発"
    if n == 2:
        return "2件"
    return "3件以上"


def load_prints_half(rows_continue_path: Path, half: str) -> pd.DataFrame:
    df = pd.read_csv(rows_continue_path, low_memory=False)
    df = df[(df["kind"] == "print") & (df["half"] == half)].copy()
    df["ts_ms"] = df["ts_ms"].astype(np.int64)
    return df.sort_values(["bundle_id", "ts_ms"]).reset_index(drop=True)


def cascades_from_prints(df: pd.DataFrame) -> dict:
    """`bundle_id` ごとに ts 順のプリント(dict のリスト)。"""
    out: dict = {}
    for bid, g in df.groupby("bundle_id", sort=False):
        out[str(bid)] = g.sort_values("ts_ms").to_dict("records")
    return out


def sample_cascades(bundle_ids: list, seed: int = SEED, k: int = N_CASCADES_STAGE1) -> list:
    pool = sorted(bundle_ids)
    rng = random.Random(seed)
    rng.shuffle(pool)
    return pool[:k]


def stage1_select(rows_continue_path: Path = ROWS_CONTINUE, seed: int = SEED,
                  k: int = N_CASCADES_STAGE1) -> dict:
    """段1: 前半の連鎖から種 20260920 で k 本抜く(較正5,000件は後半なので除外は不要)。"""
    df = load_prints_half(rows_continue_path, "前半")
    all_cascades = cascades_from_prints(df)
    picked_ids = sample_cascades(list(all_cascades.keys()), seed, k)
    picked = {bid: all_cascades[bid] for bid in picked_ids}

    def breakdown(d: dict) -> dict:
        b: dict = defaultdict(int)
        for prints in d.values():
            b[size_bucket(len(prints))] += 1
        return dict(b)

    return {
        "前半連鎖の総数": len(all_cascades),
        "前半連鎖の内訳(単発/2件/3件以上)": breakdown(all_cascades),
        "抜いた本数": len(picked),
        "抜いた本数の内訳(単発/2件/3件以上)": breakdown(picked),
        "cascades": picked,
    }


def load_calibration_bundle_ids(rows_continue_path: Path = ROWS_CONTINUE,
                                manifest_path: Path = CALIB_MANIFEST) -> set:
    """段2委任文【作るもの】1・R2.7 D4: 較正5,000件(`selection_manifest.json` の
    print_id)を `rows_continue.csv.gz` で bundle_id に変換する(突合は print_id →
    bundle_id、D4 の規定どおり)。"""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    calib_ids = {p["print_id"] for p in manifest["prints"]}
    df = pd.read_csv(rows_continue_path, usecols=["print_id", "kind", "bundle_id"],
                     dtype={"print_id": str, "bundle_id": str})
    df = df[(df["kind"] == "print") & (df["print_id"].isin(calib_ids))]
    found = set(df["print_id"])
    if len(found) != len(calib_ids):
        missing = calib_ids - found
        raise SystemExit(f"[止め] 較正5,000件に rows_continue.csv.gz に無い print_id が"
                         f"ある: {sorted(missing)[:5]}(計 {len(missing)} 件)")
    return set(df["bundle_id"].tolist())


def select_stage2_cascades(rows_continue_path: Path = ROWS_CONTINUE,
                           manifest_path: Path = CALIB_MANIFEST, seed: int = SEED,
                           k: int = N_CASCADES_STAGE2) -> dict:
    """段2: 後半の連鎖から、較正5,000件を含む連鎖(bundle_id で突合、D4)を除き、
    種 20260920 で k 本抜く。"""
    df = load_prints_half(rows_continue_path, "後半")
    all_cascades = cascades_from_prints(df)
    calib_bids = load_calibration_bundle_ids(rows_continue_path, manifest_path)
    excluded = [bid for bid in all_cascades if bid in calib_bids]
    kept = {bid: prints for bid, prints in all_cascades.items() if bid not in calib_bids}
    picked_ids = sample_cascades(list(kept.keys()), seed, k)
    picked = {bid: kept[bid] for bid in picked_ids}

    def breakdown(d: dict) -> dict:
        b: dict = defaultdict(int)
        for prints in d.values():
            b[size_bucket(len(prints))] += 1
        return dict(b)

    return {
        "後半連鎖の総数(除外前)": len(all_cascades),
        "後半連鎖の内訳(除外前、単発/2件/3件以上)": breakdown(all_cascades),
        "除外した連鎖の数(較正5000件を含む)": len(excluded),
        "除外後の残数": len(kept),
        "抜いた本数": len(picked),
        "抜いた本数の内訳(単発/2件/3件以上)": breakdown(picked),
        "cascades": picked,
    }


# ===========================================================================
# logistic の確率(前半で固定した係数・経験分布を読むだけ。段2 と同じ経路)
# ===========================================================================
def load_logit_probs_for_cascades(cascades: dict, materials_path: Path = ROWS_MATERIALS
                                   ) -> tuple[dict, dict]:
    """抜いた連鎖の print_id に絞った materials(cand_*)から logistic の確率を計算する。
    `apply_frozen_rank` だけを使い、前半の ecdf・係数は一切再計算しない(D5 の精神)。
    戻り値: (print_id -> 確率, print_id -> 位置("1件目"/"連鎖の中"))。"""
    ids = {pr["print_id"] for prints in cascades.values() for pr in prints}
    mat = pd.read_csv(materials_path, low_memory=False)
    df = mat[mat["print_id"].isin(ids)].reset_index(drop=True)
    if len(df) != len(ids):
        missing = ids - set(df["print_id"])
        raise SystemExit(f"[止め] materials に無い print_id がある: {sorted(missing)[:5]}"
                         f"(計 {len(missing)} 件)")
    sb = js.StateBuilder()
    prob_of = stage2.compute_logit_probs(sb, df)
    position_of_pid = {pid: position_of(c1) for pid, c1 in zip(df["print_id"], df["cand_1"])}
    return prob_of, position_of_pid


# ===========================================================================
# 段4: 方策の模擬(状態機械)
# ===========================================================================
def simulate_cascade(prints: list, judgments: list, side_sign: float, policy_type: str,
                     delay_s: float, price_fn, cascade_end_ts: int,
                     tp_bp: float | None = None, tp_scan=None) -> dict:
    """`prints`(ts 順)・`judgments`(同じ長さ)から 1 本の連鎖の損益・回数・保有秒を返す。
    `price_fn(t_ms)` は `(price, matched_ts)` を返す(at_or_after、穴は price_fn 側)。
    損益の符号は建玉の向き(清算の向きではない)。

    `tp_bp`(bp)と `tp_scan` を渡すと、**順張りの建玉だけ**に「入りの約定価格から
    `tp_bp` 進んだ価格で利確する」出口が付く(2026-09-21、L-355・L-356)。
    `tp_scan(after_ts, until_ts, target_px, dir_sign)` は `after_ts` より後・
    `until_ts` 以下で `dir_sign*(値段 − target_px) >= 0` になる**最初の約定**の
    `(値段, 時刻ms)` を返す(無ければ `(NaN, None)`)。目標は入り値で決まり、
    ホールドしても動かない。逆張りの建玉は一切変えない。`tp_bp` が None なら
    この分岐は 1 行も走らないので、従来の道筋と完全に同じ。

    `path`(戻り値)の各行は「レグ損益_bp」を持つ(決済・ドテン・連鎖の終わりの強制決済の
    行だけ数値、他は None)。この列の合計は必ず `pnl_bp` と一致する(反証者レビュー8
    致命-3。建玉を持ったまま連鎖が終わった場合、`path` の最後にもう1行、判断「終わり」・
    行動「決済」の強制決済の行が付く ── 集計〈cascade_rows〉には元々含まれていた損益だが、
    どの print 単位の出力にも現れていなかった)。
    """
    delay_ms = int(round(float(delay_s) * 1000))
    pos = POS_NONE
    entry_price = entry_ts = entry_dir = None
    entry_fill_ts = None
    tp_hit = None       # 入りのときに 1 回だけ引く (利確の値段, 利確の約定時刻)
    total_pnl = 0.0
    n_entries = 0
    total_hold_ms = 0
    missing = False
    path_rows = []
    legs = []
    entered_ever = False
    first_entry_pos = None  # 何件目(0始まり)で最初に建玉を持ったか

    def close_leg(px, ts):
        nonlocal total_pnl, total_hold_ms
        leg_pnl = entry_dir * (px - entry_price) / entry_price * 1e4
        total_pnl += leg_pnl
        total_hold_ms += ts - entry_ts
        return leg_pnl

    def record_leg(reason, leg_pnl, exit_ts, exit_fill_ts, at_pos, tp_seconds=None):
        legs.append({
            "位置": at_pos,
            "向き": (POS_WITH if entry_dir == side_sign else POS_AGAINST),
            "出口の理由": reason, "レグ損益_bp": leg_pnl,
            "入りの約定時刻_ms": entry_fill_ts, "出の約定時刻_ms": exit_fill_ts,
            "保有秒": (exit_ts - entry_ts) / 1000.0,
            "利確までの秒": tp_seconds})

    def open_leg(px, ts, matched_t, direction):
        """建玉を作る。順張りで `tp_bp` があるなら、入り値基準の目標に**最初に**
        達する約定を 1 回だけ引いておく(入りの約定より後・連鎖の終わり + 遅れ まで)。"""
        nonlocal entry_price, entry_ts, entry_dir, entry_fill_ts, tp_hit
        entry_price, entry_ts, entry_dir = px, ts, direction
        entry_fill_ts = matched_t
        tp_hit = None
        if (tp_bp is not None and tp_scan is not None and direction == side_sign
                and px == px and matched_t is not None):
            target = float(px) * (1.0 + float(direction) * float(tp_bp) * 1e-4)
            hit_px, hit_ts = tp_scan(int(matched_t),
                                     int(cascade_end_ts) + delay_ms,
                                     target, float(direction))
            if hit_ts is not None and hit_px == hit_px:
                tp_hit = (float(hit_px), int(hit_ts))

    def take_profit_before(limit_ts: int, at_pos: int) -> bool:
        """`limit_ts`(目標時刻)までに利確の約定が来ていたら、そこで建玉を閉じる。"""
        nonlocal pos, entry_price, entry_ts, entry_dir, entry_fill_ts, tp_hit
        if tp_hit is None or entry_price is None or tp_hit[1] > int(limit_ts):
            return False
        hit_px, hit_ts = tp_hit
        # 他のレグと同じ「目標時刻の時計」に揃える(約定時刻 − 遅れ)。
        exit_ts = hit_ts - delay_ms
        leg_pnl = close_leg(hit_px, exit_ts)
        record_leg(EXIT_TP, leg_pnl, exit_ts, hit_ts, at_pos,
                   tp_seconds=(hit_ts - entry_fill_ts) / 1000.0)
        path_rows.append({"print_id": None, "ts_ms": exit_ts, "位置": at_pos,
                          "判断": JUDGE_TP, "行動": ACT_CLOSE, "建玉": POS_NONE,
                          "約定価格": hit_px, "レグ損益_bp": leg_pnl})
        # 値段の付いた行と `fill_lag_ms` は 1 対 1 で並ぶ(`entry_exit_fill_times`)。
        # 利確の行は ts_ms を「約定時刻 − 遅れ」に置いたので、この行の遅れは 0。
        fill_lag_ms.append(0)
        pos = POS_NONE
        entry_price = entry_ts = entry_dir = entry_fill_ts = None
        tp_hit = None
        return True

    fill_lag_ms = []
    for j, (pr, judge) in enumerate(zip(prints, judgments)):
        ts = int(pr["ts_ms"])
        # 利確は成行の判断より先に効く(建玉は 1 つ。閉じたあとは「建玉なし」から
        # 従来の 3 択が動く)。
        take_profit_before(ts + delay_ms, j)
        new_pos, action = next_action(pos, judge, policy_type)
        px, matched_t = (NAN, None)
        leg_pnl = None
        if action in ACTIONS_NEEDING_PRICE:
            target = ts + delay_ms
            px, matched_t = price_fn(target)
            if px != px:
                missing = True
            else:
                fill_lag_ms.append(matched_t - target)
        if action == ACT_NEW_WITH:
            open_leg(px, ts, matched_t, side_sign)
            entered_ever = True
            n_entries += 1
            if first_entry_pos is None:
                first_entry_pos = j
        elif action == ACT_NEW_AGAINST:
            open_leg(px, ts, matched_t, -side_sign)
            entered_ever = True
            n_entries += 1
            if first_entry_pos is None:
                first_entry_pos = j
        elif action == ACT_CLOSE:
            if entry_price is not None and px == px:
                leg_pnl = close_leg(px, ts)
                record_leg(EXIT_NEXT_PRINT, leg_pnl, ts, matched_t, j)
            entry_price = entry_ts = entry_dir = entry_fill_ts = None
            tp_hit = None
        elif action == ACT_FLIP_AGAINST:
            if entry_price is not None and px == px:
                leg_pnl = close_leg(px, ts)
                record_leg(EXIT_NEXT_PRINT, leg_pnl, ts, matched_t, j)
            open_leg(px, ts, matched_t, -side_sign)
            entered_ever = True
            n_entries += 1
        elif action == ACT_FLIP_WITH:
            if entry_price is not None and px == px:
                leg_pnl = close_leg(px, ts)
                record_leg(EXIT_NEXT_PRINT, leg_pnl, ts, matched_t, j)
            open_leg(px, ts, matched_t, side_sign)
            entered_ever = True
            n_entries += 1
        pos = new_pos
        path_rows.append({"print_id": pr.get("print_id"), "ts_ms": ts,
                          "位置": j, "判断": judge, "行動": action, "建玉": pos,
                          "約定価格": (px if px == px else None),
                          "レグ損益_bp": leg_pnl})

    # 連鎖の終わり + 遅れ より前に利確の約定が来ていたら、そこで閉じている。
    take_profit_before(cascade_end_ts + delay_ms, len(prints))
    if pos != POS_NONE and entry_price is not None:
        target = cascade_end_ts + delay_ms
        px, matched_t = price_fn(target)
        exit_leg_pnl = None
        if px != px:
            missing = True
        else:
            exit_leg_pnl = close_leg(px, cascade_end_ts)
            record_leg(EXIT_CASCADE_END, exit_leg_pnl, cascade_end_ts, matched_t,
                       len(prints))
            fill_lag_ms.append(matched_t - target)
        # 反証者レビュー8 致命-3: 連鎖の終わりの強制決済を per-print の道筋にも出す
        # (判断「終わり」、行動「決済」。集計 total_pnl には元々含まれていた)。
        path_rows.append({"print_id": None, "ts_ms": cascade_end_ts,
                          "位置": len(prints), "判断": JUDGE_EXIT, "行動": ACT_CLOSE,
                          "建玉": POS_NONE,
                          "約定価格": (px if px == px else None),
                          "レグ損益_bp": exit_leg_pnl})
        pos = POS_NONE

    return {
        "pnl_bp": (NAN if missing else total_pnl),
        "n_entries": n_entries,
        "hold_seconds": (total_hold_ms / 1000.0),
        "entered": entered_ever,
        "missing": missing,
        "path": path_rows,
        "legs": legs,
        "fill_lag_ms": fill_lag_ms,
        "first_entry_pos": first_entry_pos,
    }


def simulate_baseline(prints: list, side_sign: float, direction: str, delay_s: float,
                      price_fn, cascade_end_ts: int) -> dict:
    """基準の方策(用語表「基準の方策 (i)(ii)」): 最初のプリントで一度だけ入り、
    連鎖の終わりまで持つ。判断は使わない(状態機械を通らないので型に依らない)。"""
    delay_ms = int(round(float(delay_s) * 1000))
    first = prints[0]
    entry_ts = int(first["ts_ms"])
    entry_dir = side_sign if direction == POS_WITH else -side_sign
    t_in = entry_ts + delay_ms
    t_out = cascade_end_ts + delay_ms
    px_in, m_in = price_fn(t_in)
    px_out, m_out = price_fn(t_out)
    missing = (px_in != px_in) or (px_out != px_out)
    pnl = NAN if missing else entry_dir * (px_out - px_in) / px_in * 1e4
    hold_s = (cascade_end_ts - entry_ts) / 1000.0
    lags = [] if missing else [m_in - t_in, m_out - t_out]
    act = ACT_NEW_WITH if direction == POS_WITH else ACT_NEW_AGAINST
    return {"pnl_bp": pnl, "n_entries": 1, "hold_seconds": hold_s,
           "entered": True, "missing": missing,
           "path": [{"print_id": first.get("print_id"), "ts_ms": entry_ts, "位置": 0,
                     "判断": "(基準・判断は使わない)", "行動": act, "建玉": direction,
                     "約定価格": px_in}],
           "fill_lag_ms": lags, "first_entry_pos": 0}


def entry_bucket(first_entry_pos) -> str:
    if first_entry_pos is None:
        return "入らなかった"
    return "1件目で入った" if int(first_entry_pos) == 0 else "途中で入った"


# ===========================================================================
# 段4: 全体の組み立て
# ===========================================================================
def run_simulation(cascades: dict, logit_prob_of: dict, position_of_pid: dict,
                   price_cache: PriceCache) -> dict:
    cascade_rows = []
    print_rows = []
    fill_lags = defaultdict(list)
    judge_counts = defaultdict(int)   # (方策, 位置, 判断) -> 件数
    action_counts = defaultdict(int)  # (方策, 型, 行動) -> 件数(主遅れのみ)

    for bid in sorted(cascades.keys()):
        prints = cascades[bid]
        n = len(prints)
        side = str(prints[0]["side"])
        day = str(prints[0]["day"])
        s_sign = REACT_SIGN[side]
        cascade_end_ts = int(prints[-1]["ts_ms"]) + CASCADE_END_GAP_S * 1000
        sb = size_bucket(n)

        judge_cache = {policy: judgments_for_policy(prints, policy, logit_prob_of,
                                                     position_of_pid)
                       for policy in JUDGED_POLICIES}
        # 判断の3択/2値の件数(R2.7 D1): 確率の閾値で決まる4方策
        # (logistic_3択・logistic_2値0.5・logistic_2値基準率・規則)だけを対象に、
        # 実際の位置(1件目/連鎖の中)で数える。「完全な判断」はラベルの位置(連鎖内の
        # 最後かどうか)で決まる別種の判断なので、この確率ベースの件数表には含めない
        # (D1: 位置2×判断のある方策4 = 24 行の決定式に合わせた)。
        for policy in COUNT_JUDGE_POLICIES:
            for j, pr in enumerate(prints):
                pos_label = position_of_pid.get(pr["print_id"], POS_1ST)
                judge_counts[(policy, pos_label, judge_cache[policy][j])] += 1

        for delay in DELAYS_S:
            price_fn = price_cache.raw_at_or_after
            for policy in JUDGED_POLICIES:
                judgments = judge_cache[policy]
                for ptype in (TYPE_A, TYPE_B):
                    res = simulate_cascade(prints, judgments, s_sign, ptype, delay,
                                           price_fn, cascade_end_ts)
                    cascade_rows.append({
                        "bundle_id": bid, "day": day, "side": side,
                        "連鎖の大きさ": sb, "n_prints": n, "方策": policy, "型": ptype,
                        "遅れ_秒": delay, "pnl_bp": res["pnl_bp"],
                        "建玉の回数": res["n_entries"], "保有秒": res["hold_seconds"],
                        "入った": int(res["entered"]), "欠測": int(res["missing"]),
                        "最初に入った位置": entry_bucket(res["first_entry_pos"])})
                    fill_lags[delay].extend(res["fill_lag_ms"])
                    if delay == MAIN_DELAY:
                        # 反証者レビュー8 致命-3・直すべき-3: 連鎖の終わりの強制決済の行
                        # (path の末尾に付くことがある)も含めて全行を出す。「建玉」列と
                        # 「レグ損益_bp」列を足した(D3・致命-3)。
                        for row in res["path"]:
                            action_counts[(policy, ptype, row["行動"])] += 1
                            print_rows.append({
                                "print_id": row["print_id"], "bundle_id": bid,
                                "day": day, "side": side, "方策": policy, "型": ptype,
                                "遅れ_秒": delay, "位置": row["位置"],
                                "判断": row["判断"], "行動": row["行動"],
                                "建玉": row["建玉"], "約定価格": row["約定価格"],
                                "レグ損益_bp": row["レグ損益_bp"]})
            for policy_name, direction in POLICY_IS_BASELINE.items():
                for ptype in (TYPE_A, TYPE_B):  # 型に依らないが表の形をそろえるため両方書く
                    res = simulate_baseline(prints, s_sign, direction, delay, price_fn,
                                            cascade_end_ts)
                    cascade_rows.append({
                        "bundle_id": bid, "day": day, "side": side,
                        "連鎖の大きさ": sb, "n_prints": n, "方策": policy_name, "型": ptype,
                        "遅れ_秒": delay, "pnl_bp": res["pnl_bp"],
                        "建玉の回数": res["n_entries"], "保有秒": res["hold_seconds"],
                        "入った": int(res["entered"]), "欠測": int(res["missing"]),
                        "最初に入った位置": entry_bucket(res["first_entry_pos"])})
                    fill_lags[delay].extend(res["fill_lag_ms"])
                    if delay == MAIN_DELAY:
                        action_counts[(policy_name, ptype, res["path"][0]["行動"])] += 1

    return {"cascade_rows": cascade_rows, "print_rows": print_rows,
           "fill_lags": fill_lags, "judge_counts": judge_counts,
           "action_counts": action_counts}


# ===========================================================================
# 表(R2.5: 分布・0として含める/含めない・位置別・件数)
# ===========================================================================
def dist_stats(cdf: pd.DataFrame, policy: str, ptype: str, delay: float,
              include_zero_for_no_entry: bool) -> dict:
    sub = cdf[(cdf["方策"] == policy) & (cdf["型"] == ptype) & (cdf["遅れ_秒"] == delay)]
    ok = sub[sub["欠測"] == 0]
    vals = ok["pnl_bp"].to_numpy(float)
    entered_mask = ok["入った"].to_numpy(int) == 1
    if not include_zero_for_no_entry:
        vals_use = vals[entered_mask]
        days_use = ok.loc[entered_mask, "day"].to_numpy(object)
    else:
        vals_use = np.where(entered_mask, vals, 0.0)
        days_use = ok["day"].to_numpy(object)
    q = quantiles(vals_use, [25, 50, 75])
    neg_share = float(np.mean(vals_use < 0)) if vals_use.size else NAN
    dew = day_equal_weight_mean(vals_use, days_use)
    m, se_c, se_naive, nn, ndays = mean_se_cluster(vals_use, days_use)
    return {
        "方策": policy, "型": ptype, "遅れ_秒": delay,
        "中央値": q[1], "p25": q[0], "p75": q[2], "負の割合": neg_share,
        "日等重み平均": dew, "日クラスタSE": se_c, "n": int(vals_use.size),
        "日数": ndays,
        "建玉の回数の平均": float(ok["建玉の回数"].mean()) if ok.shape[0] else NAN,
        "保有秒の中央値": (float(np.median(ok["保有秒"].to_numpy(float)))
                    if ok.shape[0] else NAN),
        "入らなかった割合": (float(1.0 - ok["入った"].mean()) if ok.shape[0] else NAN),
        "0として含めたか": int(include_zero_for_no_entry),
    }


def build_dist_table(cdf: pd.DataFrame) -> list:
    rows = []
    for policy in ALL_POLICIES:
        for ptype in (TYPE_A, TYPE_B):
            for delay in DELAYS_S:
                for inc0 in (True, False):
                    rows.append(dist_stats(cdf, policy, ptype, delay, inc0))
    return rows


def build_position_breakdown(cdf: pd.DataFrame) -> list:
    """位置別(1件目で入った/途中で入った/入らなかった)の内訳(主遅れのみ)。"""
    rows = []
    sub_all = cdf[(cdf["遅れ_秒"] == MAIN_DELAY) & (cdf["欠測"] == 0)]
    for policy in ALL_POLICIES:
        for ptype in (TYPE_A, TYPE_B):
            sub = sub_all[(sub_all["方策"] == policy) & (sub_all["型"] == ptype)]
            for bucket in ("1件目で入った", "途中で入った", "入らなかった"):
                g = sub[sub["最初に入った位置"] == bucket]
                vals = g["pnl_bp"].to_numpy(float)
                q = quantiles(vals, [50])
                rows.append({"方策": policy, "型": ptype, "位置": bucket,
                            "n": int(g.shape[0]), "中央値": q[0],
                            "負の割合": (float(np.mean(vals < 0)) if vals.size else NAN)})
    return rows


def build_judge_count_table(judge_counts: dict) -> list:
    """R2.7 D1: 位置2×判断3×方策4 = 24 行を明示的に列挙する(観測されなかった組
    〈例: 規則は「わからない」を持たない〉も件数0の行として出す。決定的な行数)。"""
    rows = []
    for policy in COUNT_JUDGE_POLICIES:
        for pos_label in (POS_1ST, POS_CHAIN):
            for judge in (JUDGE_STOP, JUDGE_CONTINUE, JUDGE_UNKNOWN):
                n = judge_counts.get((policy, pos_label, judge), 0)
                rows.append({"方策": policy, "位置": pos_label, "判断": judge, "件数": n})
    return rows


def build_action_count_table(action_counts: dict) -> list:
    rows = []
    for (policy, ptype, action), n in sorted(action_counts.items()):
        rows.append({"方策": policy, "型": ptype, "行動": action, "件数": n,
                    "遅れ_秒": MAIN_DELAY})
    return rows


# ===========================================================================
# 合成の連鎖 3 本(報告 §3。判断は手で与え、状態機械の動作だけを見せる)
# ===========================================================================
def build_synthetic_traces() -> list:
    """報告の項目(3): 合成の連鎖 3 本の状態機械の道筋。価格は t_ms をそのまま
    返す偽の price_fn(bp が手計算しやすい)。判断は手で与える(実データを使わない
    ので logistic は呼ばない)。"""
    def fake_price(t_ms):
        return 100.0 + float(t_ms) / 1.0e7, t_ms

    cases = [
        ("A: 続く→続く→止まる(型A、決済で終わる)", TYPE_A,
         [{"print_id": "s1a", "ts_ms": 0, "side": "BUY"},
          {"print_id": "s1b", "ts_ms": 10_000, "side": "BUY"},
          {"print_id": "s1c", "ts_ms": 20_000, "side": "BUY"}],
         [JUDGE_CONTINUE, JUDGE_CONTINUE, JUDGE_STOP]),
        ("B: 止まる→続く(型B、逆張りで入りドテン)", TYPE_B,
         [{"print_id": "s2a", "ts_ms": 0, "side": "SELL"},
          {"print_id": "s2b", "ts_ms": 15_000, "side": "SELL"}],
         [JUDGE_STOP, JUDGE_CONTINUE]),
        ("C: わからない(単発、入らない)", TYPE_A,
         [{"print_id": "s3a", "ts_ms": 0, "side": "BUY"}],
         [JUDGE_UNKNOWN]),
    ]
    rows = []
    for title, ptype, prints, judgments in cases:
        side = prints[0]["side"]
        s_sign = REACT_SIGN[side]
        cascade_end_ts = int(prints[-1]["ts_ms"]) + CASCADE_END_GAP_S * 1000
        res = simulate_cascade(prints, judgments, s_sign, ptype, delay_s=0,
                               price_fn=fake_price, cascade_end_ts=cascade_end_ts)
        for r in res["path"]:
            rows.append({"合成連鎖": title, "print_id": r["print_id"],
                        "ts_ms": r["ts_ms"], "判断": r["判断"], "行動": r["行動"],
                        "建玉": r["建玉"], "約定価格": r["約定価格"],
                        "レグ損益_bp": _fmt(r["レグ損益_bp"], 4)
                                  if r["レグ損益_bp"] is not None else ""})
        rows.append({"合成連鎖": title, "print_id": "(連鎖損益)",
                    "ts_ms": "", "判断": "", "行動": "",
                    "建玉": "", "約定価格": _fmt(res["pnl_bp"], 4), "レグ損益_bp": ""})
    return rows


# ===========================================================================
# 出力
# ===========================================================================
def write_csv_gz(path: Path, rows: list) -> None:
    import csv as _csv
    rows = normalize_rows(rows)
    with gz_open_w(path) as fh:
        w = _csv.writer(fh)
        if rows:
            cols = list(rows[0].keys())
            w.writerow(cols)
            for r in rows:
                w.writerow([_fmt(r[c], 6) if isinstance(r[c], float) else r[c]
                           for c in cols])


def write_output(out_dir: Path, select_info: dict, built: dict, *, stage_no: int = 1
                 ) -> dict:
    """段1・段2共通の出力書式(段2委任文【作るもの】2: 「段1と同じ道具で」)。
    段2は `synthetic_traces.csv` を作らない(委任文の構成に無い ── 段1の合成データは
    テスト用の実データ非依存の例なので、実連鎖しか扱わない段2には不要)。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    cascade_rows = built["cascade_rows"]
    print_rows = built["print_rows"]
    write_csv_gz(out_dir / "cascades.csv.gz", cascade_rows)
    write_csv_gz(out_dir / "prints_policy.csv.gz", print_rows)

    cdf = pd.DataFrame(cascade_rows)
    dist = build_dist_table(cdf)
    posb = build_position_breakdown(cdf)
    jc = build_judge_count_table(built["judge_counts"])
    ac = build_action_count_table(built["action_counts"])

    named = [("dist_table.csv", dist, "連鎖ごとの損益分布(方策×型×遅れ、0含める/含めない)"),
            ("position_breakdown.csv", posb, "位置別(1件目で入った/途中で入った/入らなかった)の内訳"),
            ("judge_counts.csv", jc, "判断(3択/2値)の件数"),
            ("action_counts.csv", ac, "行動(決済/ドテン/ホールド等)の件数(遅れ1秒)")]
    if stage_no == 1:
        named.append(("synthetic_traces.csv", build_synthetic_traces(),
                     "合成の連鎖3本の状態機械の道筋"))
    norm = {name: normalize_rows(rows) for name, rows, _k in named}
    for name, rows, _k in named:
        write_csv(out_dir / name, norm[name])

    if stage_no == 1:
        title = "段1(前半200本)"
        delegation = DELEGATION_STAGE1
        pop_line = (f"- 抜いた連鎖: {select_info['抜いた本数']} 本(前半連鎖の総数 "
                   f"{select_info['前半連鎖の総数']} 本から種 {SEED})")
        stage_label = "段1(前半200本の動作確認)"
        select_summary = {
            "前半連鎖の総数": select_info["前半連鎖の総数"],
            "前半連鎖の内訳(単発/2件/3件以上)": select_info["前半連鎖の内訳(単発/2件/3件以上)"],
            "抜いた本数の内訳(単発/2件/3件以上)": select_info["抜いた本数の内訳(単発/2件/3件以上)"],
        }
    else:
        title = "段2(後半2,000本、一度だけ)"
        delegation = DELEGATION_STAGE2
        pop_line = (f"- 抜いた連鎖: {select_info['抜いた本数']} 本(後半連鎖の総数〈除外前〉"
                   f"{select_info['後半連鎖の総数(除外前)']} 本、較正5,000件を含む "
                   f"{select_info['除外した連鎖の数(較正5000件を含む)']} 本を除いた "
                   f"{select_info['除外後の残数']} 本から種 {SEED})")
        stage_label = "段2(後半2,000本、一度だけ)"
        select_summary = {
            "後半連鎖の総数(除外前)": select_info["後半連鎖の総数(除外前)"],
            "後半連鎖の内訳(除外前、単発/2件/3件以上)":
                select_info["後半連鎖の内訳(除外前、単発/2件/3件以上)"],
            "除外した連鎖の数(較正5000件を含む)":
                select_info["除外した連鎖の数(較正5000件を含む)"],
            "除外後の残数": select_info["除外後の残数"],
            "抜いた本数の内訳(単発/2件/3件以上)": select_info["抜いた本数の内訳(単発/2件/3件以上)"],
        }

    md = [f"# O3C SIGNAL 方策の模擬 — {title}の表", "",
         f"- 委任文: `{delegation}`",
         "- 設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_POLICY_DESIGN_2026-09-20.md`(改訂2・R2.7)",
         "- 反証者: `docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW8_2026-09-20.md`(致命 C1・C3・"
         "直すべき D3 を受けて直した版)",
         pop_line, ""]
    for name, rows, key in named:
        md += [f"## {key}(`{name}`、{len(norm[name])} 行)", "", md_table(norm[name]), ""]
    mdtxt = "\n".join(md)
    check_no_banned(mdtxt, "tables.md")
    (out_dir / "tables.md").write_text(mdtxt, encoding="utf-8")
    n_cells = count_numeric_cells(mdtxt)

    total_rows = sum(len(v) for _n, v, _k in named)
    inputs_md5 = {}
    for p in (ROWS_CONTINUE, ROWS_MATERIALS, lg.CONFIG_FIRST, lg.CONFIG_CHAIN,
             lg.ECDF_FIRST, lg.ECDF_CHAIN):
        if p.exists():
            inputs_md5[str(p.relative_to(REPO_ROOT))] = md5_of(p)

    n_missing = {str(d): int((cdf[(cdf["遅れ_秒"] == d)]["欠測"] == 1).sum())
                for d in DELAYS_S}
    summary = {
        "段": stage_label,
        "実行時刻(UTC)": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(),
        "委任文": delegation,
        "設計": "docs/PHASE2/O3C/SIGNAL/SIGNAL_POLICY_DESIGN_2026-09-20.md(改訂2・R2.7)",
        "反証者": "docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW8_2026-09-20.md",
        "種": SEED,
        "抜いた連鎖の本数": select_info["抜いた本数"],
        **select_summary,
        "方策": list(ALL_POLICIES),
        "遅れ_秒": list(DELAYS_S),
        "3択の帯(1件目)": list(BAND_1ST),
        "3択の帯(連鎖の中)": list(BAND_CHAIN),
        "基準率2値の閾値(1件目)": BASE_RATE_1ST,
        "基準率2値の閾値(連鎖の中)": BASE_RATE_CHAIN,
        "欠測(価格が引けなかった行数、遅れ別)": n_missing,
        "行数の内訳": {name: len(rows) for name, rows, _k in named},
        "行数の合計": total_rows,
        "数値セル数(tables.md)": n_cells,
        "入力のMD5(読むだけ、書き換えていない)": inputs_md5,
    }
    txt = json.dumps(summary, ensure_ascii=False, indent=2)
    check_no_banned(txt, "summary.json")
    (out_dir / "summary.json").write_text(txt, encoding="utf-8")

    lines = []
    for p in sorted(out_dir.iterdir()):
        if p.name in ("MD5SUMS",) or p.is_dir():
            continue
        lines.append(f"{md5_of(p)}  {p.name}")
    (out_dir / "MD5SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


# ===========================================================================
# main
# ===========================================================================
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="O3C SIGNAL 方策の模擬(段1: 前半200本 / "
                                             "段2: 後半2,000本、一度だけ)")
    ap.add_argument("--stage", type=int, choices=(1, 2), default=1)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    out_dir = a.out if a.out is not None else (DEFAULT_OUT if a.stage == 1
                                               else DEFAULT_OUT_STAGE2)

    t0 = time.time()
    if a.stage == 1:
        select_info = stage1_select()
        print(f"[段1-1] 前半連鎖 {select_info['前半連鎖の総数']} 本から "
             f"{select_info['抜いた本数']} 本を種 {SEED} で抜いた", flush=True)
    else:
        select_info = select_stage2_cascades()
        print(f"[段2-1] 後半連鎖 {select_info['後半連鎖の総数(除外前)']} 本のうち較正5,000件を"
             f"含む {select_info['除外した連鎖の数(較正5000件を含む)']} 本を除いた "
             f"{select_info['除外後の残数']} 本から {select_info['抜いた本数']} 本を種 {SEED} "
             f"で抜いた", flush=True)

    logit_prob_of, position_of_pid = load_logit_probs_for_cascades(select_info["cascades"])
    print(f"[段{a.stage}-2] logistic の確率を {len(logit_prob_of)} 件計算した "
         f"({time.time() - t0:.0f}s)", flush=True)

    price_cache = PriceCache(DATA_ROOT)
    built = run_simulation(select_info["cascades"], logit_prob_of, position_of_pid,
                           price_cache)
    print(f"[段{a.stage}-3] 方策の模擬を終えた({time.time() - t0:.0f}s)", flush=True)

    summary = write_output(out_dir, select_info, built, stage_no=a.stage)
    print(f"完了 {time.time() - t0:.0f}s -> {out_dir}", flush=True)
    print(json.dumps({"行数の合計": summary["行数の合計"],
                      "数値セル数": summary["数値セル数(tables.md)"]},
                     ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
