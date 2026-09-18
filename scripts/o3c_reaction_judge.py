#!/usr/bin/env python3
"""段 A「清算の後の反応」の**結果の読み**(事前登録どおりに読むだけの道具)。

**判定区間を開ける前に書いた。**開封の後に読み方を書くと、出てきた数値に合わせて
読み方を調整できてしまうため(`CLAUDE.md` §0.2 の A-6「判定バーを開封後に動かさない」)。

**出所**: `docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md`(確定版・凍結)。
本ファイルは事前登録の次の節を実装したものである。**事前登録は書き換えていない。**

  §4    16 軸 = 48 群と、どの走行から取るか
  §4.3  判定の対象 = F1 の戻り到達 2 系統 × 48 群 × h 6 = 576 検定、α = 0.05/576
  §6.1  対照 (i) の、向きの要る量の重み付け
  §7.0  F1 の 12 セルの読み(4 分岐)
  §8.5  MDE の計算式と入力
  §8.6  p・s は標本 6 日で固定、n は走行後の群の件数
  §9    バー |t| ≥ 3.925、n < 30 → 不明、台地条件は隣の分位の併記
  §9.1  UTC 日クラスタのブートストラップ 2,000 回・種 1
  §10.1 576 行の表の列の順と分岐
  §10.2 観測のみの表(t と判定の列なし。前進到達を入れない)
  §10.3 「なぜ」の欄の形

**関門**(`CLAUDE.md` §5.0 の 2): 表を 1 枚も書く前に
`scripts/_research_audit_gate.py: require_audit(<unit>, "結果")` を通す。
**迂回する旗は作っていない。**`--root` は試験のために台帳の場所を差し替えるだけのもので、
関門そのものを外さない。

**判定語(予測できる / 使える / 有効)は出力に 1 つも書かない**(事前登録 §10.1 の末尾)。
**「差なし」「陰性」も書かない**(走行前の再監査の決定 2)。
書いてしまっていないことは、書き出しの最後に自分で走査して確かめる。

**走行前の再監査(2 回目)で決めた 7 点**(事前登録の本文は別の委任先が同じ決定で直す。
**本ファイルは事前登録を書き換えていない**):

  1. CI は正規近似 `差 ± z × ブートストラップ SE`。2,000 回・種 1 は SE の推定に使う。
     よって「|t| ≥ z」と「CI が 0 を除外」は同値である。→ `bootstrap_diff` / `ci_normal`
  2. 分岐は 3 つ: 実群 n < 30 →「不明(n < 30)」/ |t| ≥ z →「差あり(+)(−)」/
     それ以外 →「検出されず(MDE = X)」。→ `decide`
  3. 3 分位の切り値は判定区間の実群の `np.nanpercentile([100/3, 200/3])`、同点は下側、
     欠測はどの群にも入れない。切り値が等しければ中の群は空。空の群も 576 行に出す。
     → `tertile_cuts` / `_quantile_label`
  4. MDE の p・s は、判定区間の切り値を標本 6 日の行に当てて分けた群から取る
     (標本で切り直さない)。n は走行後の群の件数。`alpha` は直接渡す。→ `mde`
  5. F1 の 12 セルの読みは 差あり(+) / 差あり(−) の件数で決め、不明のときは内訳を併記する。
     → `f1_reading`
  6. W に依らない 12 群は W8h の走行からだけ 576 に入れ、W24h 側の同じ 12 群は
     観測のみの表に出す。→ `build_groups` / `build_flat_groups_w24`
  7. 「全体」群の 実群 列は差の入力として出すが、その水準を根拠にした文を書かない
     (事前登録 §3 の #1 = a)。→ `main` の標準出力と `summary.json` の注記

**走行前の再監査(3 回目)で決めた 8 点**(同じく事前登録の本文は別の委任先が直す):

  1'. 対照 (ii) の軸の値の作り方を 3 通りに分ける(指摘 1。→ `control_axis_kinds`):
      **自前(own)** = 対照行にその列の値がある(`bin_pct` / `doi_pre_1h`)。
      **相手の符号(partner_sign)** = 対照行に**符号なしの大きさ**がある(A2〜A5 の 24 群)。
      1 対 1 の相手の実群の `side` の符号(`LIQ_SIGN`)を当てて対照自身の軸の値を作る。
      **受け継ぐ(inherit)** = 対照行に対応物が無い(E の 6 + B1 3 + B2 3 + C 2 = **14 群**)。
  5'. 対照 (ii) の `*_reactdir` は相手の実群の側の符号を当てる(指摘 5。→ `Run.values`)。
  6'. 1 対 1 の対応は `matched_liq_id` 列で取る(指摘 6)。**連番の算術による復元はやめた。**
      走行ごとに **サニティ #14**(相手が実在 / 同日 / `bin_pct` の差が許容内)を通す。
      → `check_pairing`
  8'. 相手が mixed 束の合わせた対照は**全群から落とす**(指摘 8。→ `Run.mat_usable`)。
  11'. `summary.json` に観測のみの表の行数・受け継いだ群・落とした対照の件数を出す(指摘 11)。
  12'. `z` は 1 本(`norm.ppf(1 − α/2)`)。バー・CI・MDE のすべてに同じ値を使う(指摘 12)。
  17'. MDE が計算できないセルは「**不明(MDE 未算出)**」にする(指摘 17。→ `decide`)。
  19'. `--sens NAME=DIR` で感度 4 本の観測のみの表を別ファイルに出す(指摘 19)。
  20'. W = 24h 側の 12 群(観測のみ)は **W = 24h の実群で切り直した切り値**を使う(指摘 20)。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from statistics import NormalDist

import numpy as np

# --- 事前登録で凍結された定数(走行の後に動かさない)-------------------------
HORIZONS = (1, 5, 15, 30, 60, 240)          # §4.1 h 6 本
N_TESTS = 576                                # §4.3 2 系統 × 48 群 × h 6
ALPHA = 0.05 / N_TESTS                       # §4.3 / §8.2
POWER = 0.80                                 # §8.2 検出力(仮定・委任先)
MIN_N = 30                                   # §9 の項 1(欠測を引いた後の実群の件数)
N_GROUPS = 48                                # §4
RUN_W8 = "gap60_w8"                          # §14.1 判定に使う走行
RUN_W24 = "gap60_w24"
UNIT = "o3c_reaction_20260918"               # 関門の単位名
# §10.1 の判定語 + 走行前の再監査(2 回目)の決定 2 で禁じた語。**出力に 1 つも書かない。**
FORBIDDEN = ("予測できる", "使える", "有効", "差なし", "陰性")

_ND = NormalDist()
# **z は 1 本だけ**(走行前の再監査(3 回目)の指摘 12。リードの決定)。
# 丸めた 3.925 と `norm.ppf(1 − α/2)` を使い分けると、同じ α の z が 1 つの判定の中で
# 2 通りになる(§5「同じ量が 2 か所で別の桁に見えないようにする」)。**バー・CI・MDE の
# すべてがこの `Z_ALPHA` を使う。**本文の「3.925」は丸め表示であって、計算はこの値である。
Z_ALPHA = _ND.inv_cdf(1 - ALPHA / 2)         # 3.9247896514056540...
BAR_T = Z_ALPHA                              # §9 の項 3(両側 α に対応する z)
Z_POWER = _ND.inv_cdf(POWER)                 # 0.8416212...
MDE_Z = Z_ALPHA + Z_POWER                    # §8.1 の (z_{1-α/2} + z_{1-β})
BAR_T_SHOWN = "3.925"                        # 文面に出す丸め表示(計算には使わない)

# 合わせた対照 (ii) のマッチングの許容(`scripts/o3c_reaction.py:140` の
# `MATCH_TOL_PCT = 5.0` を読んで書いた。**実測**)。サニティ #14 で使う。
MATCH_TOL_PCT = 5.0
# 清算の向きの符号(`scripts/o3c_oi_distance.py:127` の `LIQ_SIGN`。**実測**)。
LIQ_SIGN = {"SELL": 1.0, "BUY": -1.0}
# `*_liqdir` 列 -> その符号なしの元の列(`scripts/o3c_oi_distance.py:87` の
# `LIQDIR_SOURCE` を読んで書いた。**実測**)。対照行には**元の列だけ**値がある。
LIQDIR_SOURCE = {
    "dist_vwap_bp_liqdir": "dist_vwap_bp",
    "dist_node_bp_liqdir": "dist_node_bp",
    "oi_dist_vwap_bp_liqdir": "oi_dist_vwap_bp",
    "oi_dist_node_bp_liqdir": "oi_dist_node_bp",
    "oi_side_dist_vwap_bp_liqdir": "oi_side_dist_vwap_bp",
    "oi_side_dist_node_bp_liqdir": "oi_side_dist_node_bp",
}
# 対照 (ii) の軸の値の作り方(走行ごとに**測って**決める。決め打ちにしない)。
AX_OWN = "own"                   # 対照行にその列の値がある
AX_PARTNER_SIGN = "partner_sign"  # 対照行に符号なしの大きさがある -> 相手の側の符号を当てる
AX_INHERIT = "inherit"           # 対照行に対応物が無い -> 1 対 1 の相手の群を受け継ぐ

# --- 観測量の系統(§4.1。前進到達 `fwd_node` は 1 周目では出さない = §4.3)---
JUDGE_SYSTEMS = (
    ("reach_back_vwap_{h}m", "prop"),
    ("reach_back_node_{h}m", "prop"),
)
OBS_H_SYSTEMS = (
    ("bp_{h}m_reactdir", "mean"),
    ("mfe_{h}m_reactdir", "mean"),
    ("mae_{h}m_reactdir", "mean"),
    ("doi_post_{h}m", "mean"),
    ("reach_node_up_{h}m", "prop"),
    ("reach_node_dn_{h}m", "prop"),
)
OBS_FLAT_SYSTEMS = (
    ("reach_back_vwap_sec", "mean"),
    ("reach_back_node_sec", "mean"),
    ("reach_node_up_sec", "mean"),
    ("reach_node_dn_sec", "mean"),
    ("doi_pre_1h", "mean"),
    ("doi_pre_4h", "mean"),
    ("doi_in", "mean"),
)

# --- 軸(§4 の表)------------------------------------------------------------
# W に依る軸: 走行ごとに切る(= だから群が 3 + 3 である)。
AXES_W = (
    ("A1", "bin_pct"),
    ("A2", "dist_node_bp_liqdir"),
    ("A3", "dist_vwap_bp_liqdir"),
    ("A4", "oi_dist_node_bp_liqdir"),
    ("A5", "oi_dist_vwap_bp_liqdir"),
    ("E", "implied_leverage"),
)
# W に依らない 3 分位の軸: gap60_w8 の実群で 1 回だけ切る(§4 の内訳表)。
AXES_FLAT = (
    ("B1", "bundle_n_events_dedup"),
    ("B2", "bundle_total_qty_accum"),
    ("D", "doi_pre_1h"),
)
KIND_LIQ = "liq"
KIND_UNI = "control_uniform"
KIND_MAT = "control_matched"


# --- 向きの要る量(§6.1)------------------------------------------------------
# 実装は対照行(side が無い)に `REACT_SIGN` = +1 を当てて生の値を入れている
# (`scripts/o3c_reaction.py` 冒頭の注 42 行目。**実測**)。よって
# `*_reactdir` の 3 系統だけが「向きの要る量」である。
# 下向き(SELL の向き)と上向き(BUY の向き)の作り方:
#   bp  : 下 = −bp_raw   / 上 = +bp_raw
#   mfe : 下 = −mae_raw  / 上 = +mfe_raw  (符号を反転すると mfe と mae が入れ替わる)
#   mae : 下 = −mfe_raw  / 上 = +mae_raw
def _directional(col: str) -> bool:
    return col.endswith("_reactdir")


def _updown_sources(col: str) -> tuple[tuple[str, float], tuple[str, float]]:
    """(下向きの (元の列, 係数), 上向きの (元の列, 係数)) を返す。"""
    if col.startswith("bp_"):
        raw = col[: -len("_reactdir")]           # bp_{h}m
        return (raw, -1.0), (raw, +1.0)
    if col.startswith("mfe_"):
        h = col[len("mfe_"): -len("_reactdir")]
        return (f"mae_{h}_reactdir", -1.0), (f"mfe_{h}_reactdir", +1.0)
    if col.startswith("mae_"):
        h = col[len("mae_"): -len("_reactdir")]
        return (f"mfe_{h}_reactdir", -1.0), (f"mae_{h}_reactdir", +1.0)
    raise KeyError(col)


# =============================================================================
# 読み込み
# =============================================================================
def _f(x) -> float:
    if x is None:
        return float("nan")
    s = str(x).strip()
    if not s:
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


class Run:
    """1 走行(`--mode full` の出力ディレクトリ)を読んだもの。"""

    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = Path(path)
        rows = list(csv.DictReader((self.path / "table.csv").open(encoding="utf-8", newline="")))
        mixed_p = self.path / "table_mixed.csv"
        mixed = (
            list(csv.DictReader(mixed_p.open(encoding="utf-8", newline="")))
            if mixed_p.exists()
            else []
        )
        try:
            self.summary = json.loads((self.path / "summary.json").read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.summary = {}
        self.window_hours = (self.summary.get("params") or {}).get("window_hours")

        self.by_kind: dict[str, list[dict]] = {KIND_LIQ: [], KIND_UNI: [], KIND_MAT: []}
        for r in rows:
            if r.get("kind") in self.by_kind:
                self.by_kind[r["kind"]].append(r)

        # --- 1 対 1 の対応(決定 6')-----------------------------------------
        # **`matched_liq_id` 列で取る。**連番の算術による復元はしない
        # (走行前の再監査(3 回目)の指摘 6: 復元は mixed 束が相手のとき静かに外れ、
        # 行が黙って落ちていた)。mixed 束の行は `table_mixed.csv` 側にあるので、
        # 引き当ての辞書は主表の束 + mixed の両方から作る。
        self.mixed_ids = {r["cascade_id"] for r in mixed}
        by_id: dict[str, dict] = {r["cascade_id"]: r for r in self.by_kind[KIND_LIQ]}
        for r in mixed:
            by_id.setdefault(r["cascade_id"], r)
        self.pair_of_matched: list[dict | None] = [
            by_id.get(str(r.get("matched_liq_id") or ""))
            for r in self.by_kind[KIND_MAT]
        ]
        # 決定 8': **相手が mixed 束の合わせた対照は全群から落とす。**
        # 実群の側は mixed を主表から外しているので、残すと 1 対 1 の対称性が崩れる。
        self.mat_mixed_partner = [
            bool(str(r.get("matched_liq_id") or "") in self.mixed_ids)
            for r in self.by_kind[KIND_MAT]
        ]
        self.n_dropped_mixed_partner = int(sum(self.mat_mixed_partner))
        self.mat_usable = np.array(
            [not m for m in self.mat_mixed_partner], dtype=bool
        )
        self.pairing_worst_bin_pct_gap = float("nan")   # サニティ #14 が埋める

        self.days = sorted({r["day"] for r in rows})
        self._day_index = {d: i for i, d in enumerate(self.days)}
        self.day_idx = {
            k: np.array([self._day_index[r["day"]] for r in v], dtype=np.int64)
            for k, v in self.by_kind.items()
        }
        self._cache: dict[tuple[str, str], np.ndarray] = {}

    # -- 列の値(向きの要る量は kind ごとに作り方が違う)----------------------
    def raw(self, kind: str, col: str) -> np.ndarray:
        key = (kind, "#" + col)
        if key not in self._cache:
            self._cache[key] = np.array(
                [_f(r.get(col)) for r in self.by_kind[kind]], dtype=float
            )
        return self._cache[key]

    def values(self, kind: str, col: str) -> np.ndarray:
        """§6.1 を当てた後の値。対照 (i) の向きの要る量はここでは作らない
        (下向き / 上向きの 2 本を `updown()` で別々に出してから合成する)。

        **決定 5'(走行前の再監査(3 回目)の指摘 5)**: 合わせた対照の `*_reactdir` は、
        1 対 1 の相手の実群の側の符号を当てる。下向き(SELL 側)では
        `mfe` と `mae` が入れ替わる(`mfe = max(s·up, s·dn)` の定義から)。
        **「重み付けが要らない」のではなく「相手の符号を当てる」である。**
        """
        key = (kind, col)
        if key in self._cache:
            return self._cache[key]
        if kind == KIND_MAT and _directional(col):
            # 1 対 1 の相手の束の side を当てる(§6.1 の 4)。
            dn_up = self.updown(kind, col)
            out = np.full(len(self.by_kind[kind]), np.nan)
            for i, p in enumerate(self.pair_of_matched):
                if p is None:
                    continue
                out[i] = dn_up[0][i] if p.get("side") == "SELL" else dn_up[1][i]
            self._cache[key] = out
            return out
        out = self.raw(kind, col)
        self._cache[key] = out
        return out

    def matched_partner_sign_axis(self, col: str) -> np.ndarray:
        """**決定 1'**: 合わせた対照自身の軸の値を「符号なしの大きさ × 相手の側の符号」で作る。

        `*_liqdir` 列は `LIQ_SIGN`(SELL +1 / BUY −1)を掛けたものなので
        (`scripts/o3c_oi_distance.py:542` の `_apply_liqdir_and_leverage`。**実測**)、
        対照行に残っている**符号なしの元の列**に相手の側の符号を当てれば、
        実群と同じ規則で作った**対照自身の**軸の値になる(群を受け継ぐのではない)。
        丸めも実装に合わせて 4 桁にする。
        """
        key = (KIND_MAT, "@" + col)
        if key in self._cache:
            return self._cache[key]
        src = LIQDIR_SOURCE[col]
        base_v = self.raw(KIND_MAT, src)
        out = np.full(base_v.size, np.nan)
        for i, p in enumerate(self.pair_of_matched):
            if p is None or not math.isfinite(base_v[i]):
                continue
            s = LIQ_SIGN.get(str(p.get("side") or ""))
            if s is None:
                continue
            out[i] = round(base_v[i] * s, 4)
        self._cache[key] = out
        return out

    def updown(self, kind: str, col: str) -> tuple[np.ndarray, np.ndarray]:
        (dn_col, dn_k), (up_col, up_k) = _updown_sources(col)
        return self.raw(kind, dn_col) * dn_k, self.raw(kind, up_col) * up_k

    def w_sell(self) -> float:
        """§6.1 の 1: 実群の side 比を**判定区間で**数える。"""
        sides = [r.get("side") for r in self.by_kind[KIND_LIQ]]
        ns, nb = sides.count("SELL"), sides.count("BUY")
        return (ns / (ns + nb)) if (ns + nb) else float("nan")


# =============================================================================
# 群(§4 の 48 群)
# =============================================================================
class Group:
    __slots__ = ("name", "run", "axis", "col", "q", "side", "cuts", "control_axis")

    def __init__(self, name, run, axis, col=None, q=None, side=None, cuts=None,
                 control_axis=AX_OWN):
        self.name, self.run, self.axis = name, run, axis
        self.col, self.q, self.side, self.cuts = col, q, side, cuts
        # 対照 (ii) の軸の値をどう作るか(決定 1'。走行ごとに**測って**決める)。
        #   AX_OWN          = 対照行にその列の値があるので、対照にも同じ切り方を当てる
        #   AX_PARTNER_SIGN = 対照行に符号なしの大きさがあるので、相手の側の符号を当てて
        #                     **対照自身の**軸の値を作る(受け継ぎではない)
        #   AX_INHERIT      = 対照行に対応物が無いので、1 対 1 の相手の群を受け継ぐ
        self.control_axis = control_axis

    @property
    def pair_inherit(self) -> bool:
        """**受け継ぐ**群か(= `AX_INHERIT`)。E 6 + B1 3 + B2 3 + C 2 = 14 群。"""
        return self.control_axis == AX_INHERIT

    @property
    def is_quantile(self) -> bool:
        return self.q is not None


def control_axis_kinds(run: Run) -> dict[str, str]:
    """**測って**決める: 軸の列ごとに、対照 (ii) の軸の値をどう作るか(決定 1')。

    **前版はここが 2 分岐で、「対照行にその列の値があるのは `bin_pct` と `doi_pre_1h`
    だけ」と書いていた。数えたのは `*_liqdir` の付いた列だけだった**
    (走行前の再監査(3 回目)の指摘 1)。**符号なしの列(`dist_node_bp` /
    `dist_vwap_bp` / `oi_dist_node_bp` / `oi_dist_vwap_bp`)は対照行にも値がある。**

    決め方(**走行ごとに数える。決め打ちにしない**):
      1. その列自身が対照行で 1 つでも有限 → `AX_OWN`
      2. `*_liqdir` で、符号なしの元の列が対照行で 1 つでも有限 → `AX_PARTNER_SIGN`
      3. それ以外 → `AX_INHERIT`
    `side`(軸 C)は対照行に無く、符号なしの元も無いので必ず `AX_INHERIT`。
    """
    out: dict[str, str] = {"side": AX_INHERIT}
    for _axis, col in AXES_W + AXES_FLAT:
        own = np.concatenate([run.raw(KIND_MAT, col), run.raw(KIND_UNI, col)])
        if bool(np.isfinite(own).any()):
            out[col] = AX_OWN
            continue
        src = LIQDIR_SOURCE.get(col)
        if src is not None:
            base_v = np.concatenate([run.raw(KIND_MAT, src), run.raw(KIND_UNI, src)])
            if bool(np.isfinite(base_v).any()):
                out[col] = AX_PARTNER_SIGN
                continue
        out[col] = AX_INHERIT
    return out


def tertile_cuts(vals: np.ndarray) -> tuple[float, float]:
    """§4 の 3 分位: 判定区間の**実群**の軸の値で分位点を決める(決定 3)。

    切り値 = `np.nanpercentile(..., [100/3, 200/3])`。同点は `<=` で下側に入れる。
    欠測はどの群にも入れない。切り値 2 つが等しければ中の群は空になる。
    """
    v = vals[np.isfinite(vals)]
    if v.size == 0:
        return (float("nan"), float("nan"))
    lo, hi = np.nanpercentile(v, [100.0 / 3.0, 200.0 / 3.0])
    return (float(lo), float(hi))


def build_groups(run8: Run, run24: Run) -> list[Group]:
    """§4 の内訳表をそのまま組む。全体 1 + 3 分位 15 軸 × 3 + side 2 = 48 群。"""
    kinds = {run8.name: control_axis_kinds(run8), run24.name: control_axis_kinds(run24)}
    groups: list[Group] = []
    groups.append(Group("全体", RUN_W8, "—"))
    for axis, col in AXES_W:
        for run, tag in ((run8, "W8h"), (run24, "W24h")):
            cuts = tertile_cuts(run.values(KIND_LIQ, col))
            for q in (1, 2, 3):
                groups.append(Group(f"{axis}_{tag}_Q{q}", run.name, axis, col=col, q=q,
                                    cuts=cuts, control_axis=kinds[run.name][col]))
    for axis, col in AXES_FLAT:
        cuts = tertile_cuts(run8.values(KIND_LIQ, col))
        for q in (1, 2, 3):
            groups.append(Group(f"{axis}_Q{q}", RUN_W8, axis, col=col, q=q, cuts=cuts,
                                control_axis=kinds[RUN_W8][col]))
    for s in ("SELL", "BUY"):
        groups.append(Group(f"C_{s}", RUN_W8, "C", col="side", side=s,
                            control_axis=AX_INHERIT))
    return groups


def build_flat_groups_w24(run24: Run) -> list[Group]:
    """決定 6: W に依らない 12 群の **W = 24h 側**。

    **576 検定には入れない**(判定に使うのは W8h の走行から取った 12 群だけ)。
    ここで作った 12 群は**観測のみの表**に出す(t と判定の列なし)。

    **決定 20'(走行前の再監査(3 回目)の指摘 20)**: 切り値は **W = 24h の実群で
    切り直す**(W = 8h の切り値を持ち込まない)。W が違えば実群の分布そのものが違うので、
    W = 8h の切り値を当てると「3 分位」でなくなるためである(**リードの決定**)。
    """
    kinds = control_axis_kinds(run24)
    out = [Group("全体", RUN_W24, "—")]
    for axis, col in AXES_FLAT:
        cuts = tertile_cuts(run24.values(KIND_LIQ, col))   # ← W = 24h で切り直す
        for q in (1, 2, 3):
            out.append(Group(f"{axis}_Q{q}", RUN_W24, axis, col=col, q=q, cuts=cuts,
                             control_axis=kinds[col]))
    for s in ("SELL", "BUY"):
        out.append(Group(f"C_{s}", RUN_W24, "C", col="side", side=s,
                         control_axis=AX_INHERIT))
    return out


def build_groups_single(run: Run) -> list[Group]:
    """**決定 19'**: 感度 1 本ぶんの群(その走行の実群だけで切る)。

    全体 1 + 3 分位 9 軸(A1〜A5・E・B1・B2・D)× 3 = 27 + side 2 = **30 群**。
    **判定には 1 つも使わない**(観測のみの表にしか出さない)。
    """
    kinds = control_axis_kinds(run)
    out = [Group("全体", run.name, "—")]
    for axis, col in AXES_W + AXES_FLAT:
        cuts = tertile_cuts(run.values(KIND_LIQ, col))
        for q in (1, 2, 3):
            out.append(Group(f"{axis}_Q{q}", run.name, axis, col=col, q=q, cuts=cuts,
                             control_axis=kinds[col]))
    for s in ("SELL", "BUY"):
        out.append(Group(f"C_{s}", run.name, "C", col="side", side=s,
                         control_axis=AX_INHERIT))
    return out


def _quantile_label(v: float, cuts: tuple[float, float]) -> int:
    if not math.isfinite(v) or not math.isfinite(cuts[0]) or not math.isfinite(cuts[1]):
        return 0
    return 1 if v <= cuts[0] else (2 if v <= cuts[1] else 3)


def membership(run: Run, kind: str, g: Group) -> np.ndarray:
    """その群に入る行の真偽値。

    合わせた対照 (ii) の軸の値の作り方は 3 通り(決定 1'。`control_axis_kinds` が
    走行ごとに**測って**決める):

    - `AX_OWN`(`bin_pct` / `doi_pre_1h`)= 対照行にその列の値があるので、
      **対照にも同じ切り方を当てる**(§4)。
    - `AX_PARTNER_SIGN`(A2〜A5 の 4 軸)= 対照行に**符号なしの大きさ**があるので、
      1 対 1 の相手の側の符号を当てて**対照自身の**軸の値を作り、同じ切り値に当てる。
    - `AX_INHERIT`(E・B1・B2・C の 14 群)= 対照行に対応物が無いので、
      **1 対 1 の相手の束の群を受け継ぐ**(§6.1 の 4)。

    一様対照 (i) は 1 対 1 の相手が無いので、`AX_OWN` 以外の群には**入れない**
    (= その群の 対照 (i) と 差 (i) の欄が空になる)。

    **決定 8'**: 相手が mixed 束の合わせた対照は、どの群からも落とす
    (実群の側が mixed を主表から外しているので、残すと 1 対 1 が崩れる)。
    """
    rows = run.by_kind[kind]
    n = len(rows)
    if kind == KIND_MAT:
        usable = run.mat_usable
    if g.axis == "—":
        return usable.copy() if kind == KIND_MAT else np.ones(n, dtype=bool)
    if g.control_axis != AX_OWN and kind == KIND_UNI:
        return np.zeros(n, dtype=bool)
    if g.side is not None:
        if kind == KIND_LIQ:
            return np.array([r.get("side") == g.side for r in rows], dtype=bool)
        if kind == KIND_UNI:
            return np.zeros(n, dtype=bool)
        return np.array(
            [(p is not None and p.get("side") == g.side) for p in run.pair_of_matched],
            dtype=bool,
        ) & usable
    if kind == KIND_MAT and g.control_axis == AX_INHERIT:
        vals = np.array(
            [_f(p.get(g.col)) if p is not None else float("nan") for p in run.pair_of_matched],
            dtype=float,
        )
    elif kind == KIND_MAT and g.control_axis == AX_PARTNER_SIGN:
        vals = run.matched_partner_sign_axis(g.col)
    else:
        vals = run.values(kind, g.col)
    sel = np.array([_quantile_label(v, g.cuts) == g.q for v in vals], dtype=bool)
    return (sel & usable) if kind == KIND_MAT else sel


def check_pairing(run: Run) -> list[str]:
    """**サニティ #14**(決定 6'): 1 対 1 の対応が成り立っているかを走行ごとに測る。

    3 つを見る。1 つでも破れたら呼び出し側が「[止め]」で終了コード 1 にする
    (**崩れても静かに行が落ちるだけ、という前版の形を閉じる**)。

      1. すべての合わせた対照に相手が実在する(`matched_liq_id` が引ける)
      2. 相手が**同じ日**である
      3. `bin_pct` の差が **±5.0 ポイント以内**(`scripts/o3c_reaction.py:140` の
         `MATCH_TOL_PCT`。境界を含む = マッチングが `bp ± tol` を閉区間で取るため)
    """
    bad: list[str] = []
    rows = run.by_kind[KIND_MAT]
    n_missing = n_day = n_tol = 0
    worst = 0.0
    for r, p in zip(rows, run.pair_of_matched):
        if p is None:
            n_missing += 1
            continue
        if p.get("day") != r.get("day"):
            n_day += 1
        a, b = _f(r.get("bin_pct")), _f(p.get("bin_pct"))
        if math.isfinite(a) and math.isfinite(b):
            d = abs(a - b)
            worst = max(worst, d)
            if d > MATCH_TOL_PCT + 1e-9:
                n_tol += 1
    if n_missing:
        bad.append(f"{run.name}: 相手の束が引けない合わせた対照が {n_missing} 件")
    if n_day:
        bad.append(f"{run.name}: 相手が別の日の合わせた対照が {n_day} 件")
    if n_tol:
        bad.append(
            f"{run.name}: bin_pct の差が ±{MATCH_TOL_PCT} を超える組が {n_tol} 件"
            f"(最大 {worst:.4f})"
        )
    run.pairing_worst_bin_pct_gap = worst
    return bad


# =============================================================================
# 集計・ブートストラップ(§9.1)
# =============================================================================
def mean_se(vals: np.ndarray) -> tuple[float, float, int]:
    v = vals[np.isfinite(vals)]
    if v.size == 0:
        return float("nan"), float("nan"), 0
    m = float(v.mean())
    se = float(v.std(ddof=1) / math.sqrt(v.size)) if v.size > 1 else float("nan")
    return m, se, int(v.size)


def control_i(run: Run, sel: np.ndarray, col: str, w_sell: float) -> tuple[float, float, int]:
    """対照 (i)。向きの要る量は §6.1 の重み付けを必ず通す。"""
    if not _directional(col):
        return mean_se(run.values(KIND_UNI, col)[sel])
    if not math.isfinite(w_sell):
        return float("nan"), float("nan"), 0
    w_buy = 1.0 - w_sell
    dn, up = run.updown(KIND_UNI, col)
    m_dn, se_dn, n_dn = mean_se(dn[sel])
    m_up, se_up, n_up = mean_se(up[sel])
    if n_dn == 0 or n_up == 0:
        return float("nan"), float("nan"), 0
    m = w_sell * m_dn + w_buy * m_up
    # §6.1 の 3: 独立を仮定した合成 = SE を小さく見る向きの近似(結果に併記する)。
    se = (
        math.sqrt(w_sell**2 * se_dn**2 + w_buy**2 * se_up**2)
        if (math.isfinite(se_dn) and math.isfinite(se_up))
        else float("nan")
    )
    return m, se, min(n_dn, n_up)


def day_sums(vals: np.ndarray, sel: np.ndarray, day_idx: np.ndarray, n_days: int):
    ok = sel & np.isfinite(vals)
    s = np.bincount(day_idx[ok], weights=vals[ok], minlength=n_days)
    c = np.bincount(day_idx[ok], minlength=n_days).astype(float)
    return s, c


def ci_normal(diff: float, se: float) -> tuple[float, float]:
    """決定 1: CI は正規近似 `差 ± z_{1−α/2} × ブートストラップ SE`。

    **この形なので「|t| ≥ z」と「CI が 0 を除外」は同値である。**
    **z は `BAR_T`(= `Z_ALPHA` = `norm.ppf(1 − α/2)`)の 1 本だけ**(決定 12')。
    """
    if not (math.isfinite(diff) and math.isfinite(se)):
        return float("nan"), float("nan")
    return diff - BAR_T * se, diff + BAR_T * se


def bootstrap_diff(run: Run, sel_liq, sel_ctl, col: str, boot_idx: np.ndarray):
    """§9.1: クラスタ = UTC 日、置換ありで日を引き、その日の行を丸ごと採る。

    2,000 回・種 1 は**標準誤差の推定にだけ**使う(決定 1)。
    統計量 t = (実群 − 対照 (ii) の差) ÷ (その差のブートストラップ標準誤差)。
    返り値: (差, t, SE, n1, n2)。
    """
    n_days = len(run.days)
    sl, cl = day_sums(run.values(KIND_LIQ, col), sel_liq, run.day_idx[KIND_LIQ], n_days)
    sc, cc = day_sums(run.values(KIND_MAT, col), sel_ctl, run.day_idx[KIND_MAT], n_days)
    n1, n2 = int(cl.sum()), int(cc.sum())
    if n1 == 0 or n2 == 0:
        return float("nan"), float("nan"), float("nan"), n1, n2
    diff = float(sl.sum() / cl.sum() - sc.sum() / cc.sum())
    with np.errstate(invalid="ignore", divide="ignore"):
        a = sl[boot_idx].sum(axis=1) / cl[boot_idx].sum(axis=1)
        b = sc[boot_idx].sum(axis=1) / cc[boot_idx].sum(axis=1)
    d = a - b
    d = d[np.isfinite(d)]
    if d.size < 2:
        return diff, float("nan"), float("nan"), n1, n2
    se = float(d.std(ddof=1))
    t = diff / se if se > 0 else float("nan")
    return diff, t, se, n1, n2


# =============================================================================
# MDE(§8.5 / §8.6)
# =============================================================================
def mde(kind: str, a: np.ndarray, b: np.ndarray, n1: int, n2: int,
        alpha: float = ALPHA) -> float:
    """§8.5 の式。`alpha` は倍率で読み替えず**直接渡す**(決定 4 / §8.2 の指摘 18)。

    `a` / `b` = **標本 6 日**の実群 / 合わせた対照の値。
    **判定区間の切り値で群に分けた標本の行**を渡す(標本で切り直さない)。
    `n1` / `n2` = **走行後の群の件数**(欠測を引いた後)。
    """
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if a.size == 0 or b.size == 0 or n1 <= 0 or n2 <= 0:
        return float("nan")
    if kind == "prop":
        p1, p2 = float(a.mean()), float(b.mean())
        var = p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2
    else:
        if a.size < 2 or b.size < 2:
            return float("nan")
        var = float(a.std(ddof=1)) ** 2 / n1 + float(b.std(ddof=1)) ** 2 / n2
    if not math.isfinite(var) or var < 0:
        return float("nan")
    z = (_ND.inv_cdf(1 - alpha / 2) + Z_POWER) if alpha != ALPHA else MDE_Z
    return z * math.sqrt(var)


# =============================================================================
# 分岐(§10.1 + 走行前の再監査の決定 2)
# =============================================================================
UNKNOWN_N = "不明(n < 30)"
UNKNOWN_MDE = "不明(MDE 未算出)"


def decide(n1: int, t: float, diff: float, m: float) -> tuple[str, str]:
    """(判定, 検出力の欄)。上から順に当てる(決定 2 + 決定 17')。

    1. その検定に使う**欠測を引いた後の実群 n** が 30 未満 → 「不明(n < 30)」
    2. |t| ≥ z(= `BAR_T`。丸め表示 3.925)→ 「差あり(+)」/「差あり(−)」
    3. MDE が計算できない → **「不明(MDE 未算出)」**
    4. それ以外 → 「検出されず(MDE = X)」

    **3 は決定 17'(走行前の再監査(3 回目)の指摘 17)で分けた。**
    前版は MDE が無くても「検出されず(MDE = 未算出)」と書いていたが、
    **「検出されず」は「この n とこの MDE では検出できなかった」という意味なので、
    MDE が無い行にその語を当てると、検出力が分からないことを不在の側に読ませてしまう**
    (`CLAUDE.md` §0.2 の A-18)。**MDE が無い行は「不明」である。**

    **「差なし」「陰性」は書かない。**MDE との比較(≥ / <)は別の列に残す。
    """
    if n1 < MIN_N:
        return UNKNOWN_N, "n < 30"
    if math.isfinite(t) and abs(t) >= BAR_T:
        return ("差あり(+)" if diff > 0 else "差あり(−)"), ""
    if not math.isfinite(m):
        return UNKNOWN_MDE, "MDE 未算出"
    return f"検出されず(MDE = {_fmt(m)})", ""


def mde_mark(diff: float, m: float) -> str:
    if not math.isfinite(diff) or not math.isfinite(m):
        return ""
    return "≥" if abs(diff) >= m else "<"


# =============================================================================
# 表を組む
# =============================================================================
JUDGE_HEADER = [
    "観測量", "群", "h", "n1", "n2", "実群", "対照(i)", "対照(ii)",
    "差(ii)", "差(i)", "対照(i)SE", "走行", "t", "ブートストラップSE", "CI下限", "CI上限",
    "MDE(α=0.05/576)", "MDEとの比較", "検出力", "隣の分位", "判定",
]
# §10.2: 同じ形で出すが、`t` の列と `判定` の列を置かない。
OBS_HEADER = [
    c for c in JUDGE_HEADER
    if c not in ("t", "ブートストラップSE", "CI下限", "CI上限", "判定")
]


def _fmt(x, nd=6) -> str:
    if x is None:
        return ""
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    v = float(x)
    return "" if not math.isfinite(v) else f"{v:.{nd}f}"


def neighbours(g: Group, per_group: dict[str, dict], judge: bool) -> str:
    """§9 の項 4 / §10.1: 同じ軸の隣の分位の 差(ii) と |t| を併記する(**観測のみ**)。"""
    if not g.is_quantile:
        return ""
    parts = []
    for q in (g.q - 1, g.q + 1):
        if not 1 <= q <= 3:
            continue
        r = per_group.get(g.name[:-1] + str(q))
        if r is None:
            continue
        s = f"Q{q}:差={_fmt(r['d2'])}"
        if judge:
            at = abs(r["t"]) if math.isfinite(r["t"]) else float("nan")
            s += f",|t|={_fmt(at, 4)}"
        parts.append(s)
    return " ".join(parts)


def judge_systems() -> list[tuple[str, str, object]]:
    return [(c.format(h=h), k, h) for c, k in JUDGE_SYSTEMS for h in HORIZONS]


def observation_systems() -> list[tuple[str, str, object]]:
    return (
        [(c.format(h=h), k, h) for c, k in OBS_H_SYSTEMS for h in HORIZONS]
        + [(c, k, "") for c, k in OBS_FLAT_SYSTEMS]
    )


def build_rows(runs: dict[str, Run], samples: dict[str, Run], groups: list[Group],
               boot: dict[str, np.ndarray], *, judge: bool,
               systems: list | None = None) -> list[dict]:
    if systems is None:
        systems = judge_systems() if judge else observation_systems()
    w_sell = {n: r.w_sell() for n, r in runs.items()}
    sel_cache: dict[tuple[str, str, str, str], np.ndarray] = {}

    def sel(g: Group, kind: str, which) -> np.ndarray:
        key = (g.name, g.run, kind, "s" if which is samples else "r")
        if key not in sel_cache:
            sel_cache[key] = membership(which[g.run], kind, g)
        return sel_cache[key]

    out: list[dict] = []
    for col, kind, h in systems:
        per_group: dict[str, dict] = {}
        for g in groups:
            run, smp = runs[g.run], samples.get(g.run)
            s_liq = sel(g, KIND_LIQ, runs)
            s_uni = sel(g, KIND_UNI, runs)
            s_mat = sel(g, KIND_MAT, runs)
            m_liq, _, n1 = mean_se(run.values(KIND_LIQ, col)[s_liq])
            m_uni, se_uni, _ = control_i(run, s_uni, col, w_sell[g.run])
            m_mat, _, n2 = mean_se(run.values(KIND_MAT, col)[s_mat])
            if judge:
                diff2, t, se_b, n1, n2 = bootstrap_diff(
                    run, s_liq, s_mat, col, boot[g.run]
                )
                lo, hi = ci_normal(diff2, se_b)
            else:
                diff2 = (
                    (m_liq - m_mat)
                    if (math.isfinite(m_liq) and math.isfinite(m_mat))
                    else float("nan")
                )
                t = se_b = lo = hi = float("nan")
            diff1 = (
                (m_liq - m_uni)
                if (math.isfinite(m_liq) and math.isfinite(m_uni))
                else float("nan")
            )
            # MDE: p・s は標本 6 日(その群の切り方を当てたもの)、n は走行後の件数(§8.6)。
            # **感度の走行(決定 19')には対を成す標本が無いので MDE を出さない。**
            # その表は観測のみで、判定にも F1 の読みにも 1 つも入らない。
            if smp is None:
                m_val = float("nan")
            else:
                sa = smp.values(KIND_LIQ, col)[sel(g, KIND_LIQ, samples)]
                sb = smp.values(KIND_MAT, col)[sel(g, KIND_MAT, samples)]
                m_val = mde(kind, sa, sb, n1, n2)
            per_group[g.name] = dict(
                g=g, n1=n1, n2=n2, liq=m_liq, uni=m_uni,
                se_uni=se_uni, mat=m_mat, d2=diff2, d1=diff1, t=t, se_b=se_b,
                lo=lo, hi=hi, mde=m_val,
            )
        for g in groups:
            r = per_group[g.name]
            row = {
                "観測量": col, "群": g.name, "h": h,
                "n1": r["n1"], "n2": r["n2"],
                "実群": _fmt(r["liq"]), "対照(i)": _fmt(r["uni"]), "対照(ii)": _fmt(r["mat"]),
                "差(ii)": _fmt(r["d2"]), "差(i)": _fmt(r["d1"]),
                "対照(i)SE": _fmt(r["se_uni"]),
                "走行": g.run,
                "MDE(α=0.05/576)": _fmt(r["mde"]),
                "MDEとの比較": mde_mark(r["d2"], r["mde"]),
                "隣の分位": neighbours(g, per_group, judge),
            }
            if judge:
                verdict, power = decide(r["n1"], r["t"], r["d2"], r["mde"])
                row.update({
                    "t": _fmt(r["t"], 4), "ブートストラップSE": _fmt(r["se_b"]),
                    "CI下限": _fmt(r["lo"]), "CI上限": _fmt(r["hi"]),
                    "検出力": power, "判定": verdict,
                })
            else:
                row["検出力"] = "n < 30" if r["n1"] < MIN_N else ""
            out.append(row)
    return out


# =============================================================================
# F1 の 12 セル(§7.0)
# =============================================================================
F1_GROUP = "D_Q1"   # 主軸 D の D1 = `doi_pre_1h` が最も負の 3 分位


def f1_cells(judge_rows: list[dict]) -> list[dict]:
    """主軸 D の D1 × 戻り到達 2 系統 × h 6 本 = 12 セル。走行は gap60_w8。"""
    want = {c.format(h=h) for c, _ in JUDGE_SYSTEMS for h in HORIZONS}
    return [r for r in judge_rows if r["群"] == F1_GROUP and r["観測量"] in want]


def f1_reading(cells: list[dict]) -> str:
    """§7.0 の読み。**決定 5** の数え方で決める。

      整合 = 差あり(+) ≥ 1 かつ 差あり(−) 0
      反証 = 差あり(−) ≥ 1 かつ 差あり(+) 0
      混在 = 両方ある
      不明 = 差ありが 1 つも無い(**内訳を併記する**。決定 17' で
             「不明(MDE 未算出)」が内訳に 1 つ増えた)
    """
    if len(cells) != 12:
        return f"読めない(12 セルのはずが {len(cells)} セル)"
    pos = sum(1 for c in cells if c["判定"] == "差あり(+)")
    neg = sum(1 for c in cells if c["判定"] == "差あり(−)")
    if pos and neg:
        return f"混在(差あり(+) {pos} / 差あり(−) {neg})"
    if pos:
        return f"F1 と整合(差あり(+) {pos} / 差あり(−) 0)"
    if neg:
        return f"F1 の反証(差あり(−) {neg} / 差あり(+) 0)"
    few = sum(1 for c in cells if c["判定"] == UNKNOWN_N)
    nom = sum(1 for c in cells if c["判定"] == UNKNOWN_MDE)
    nod = sum(1 for c in cells if c["判定"].startswith("検出されず"))
    return (f"不明(差あり 0。内訳: 不明(n < 30) {few} / {UNKNOWN_MDE} {nom} / "
            f"検出されず {nod})")


# =============================================================================
# 「なぜ」の欄(§10.3。欄の形だけ。中身は結果の後に書く)
# =============================================================================
WHY_HEADER = [
    "読み", "候補1:機構にエッジが無い", "候補2:実装が意図を反映していない",
    "候補3:バグ", "候補4:検出力不足", "2周目に測るもの",
]
WHY_READINGS = ("F1 と整合", "F1 の反証", "混在", "不明")
WHY_PLACEHOLDER = "(結果を見てから書く。空欄にしない)"


# =============================================================================
# 書き出し
# =============================================================================
def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


def write_md5(out: Path, names: list[str]) -> None:
    lines = []
    for n in sorted(names):
        h = hashlib.md5((out / n).read_bytes()).hexdigest()
        lines.append(f"{h}  {n}")          # `./` を付けない相対パス
    (out / "MD5SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def scan_forbidden(out: Path, names: list[str]) -> list[str]:
    hits = []
    for n in names:
        text = (out / n).read_text(encoding="utf-8", errors="replace")
        for w in FORBIDDEN:
            if w in text:
                hits.append(f"{n}: {w}")
    return hits


# =============================================================================
# 関門(`CLAUDE.md` §5.0 の 2)
# =============================================================================
def pass_audit_gate(root: Path) -> None:
    """表を 1 枚も書く前に通す。迂回する旗は無い。"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _research_audit_gate import require_audit

    try:
        require_audit(UNIT, "結果", root)
    except SystemExit:
        sys.stderr.write(
            "\n[止め] 測定後・報告前の監査が通っていないので、表を 1 枚も書かずに終わる。\n"
            f"       単位: {UNIT} / 段階: 結果 / 台帳: {root}/docs/AUDITOR/ACTION_LOG.md\n"
        )
        raise SystemExit(1) from None


# =============================================================================
# 本体
# =============================================================================
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="段 A の結果を事前登録どおりに読む(判定区間を開ける前に書いた)"
    )
    ap.add_argument("--run-w8", required=True, help="gap 60 秒 × W 8h の走行の出力ディレクトリ")
    ap.add_argument("--run-w24", required=True, help="gap 60 秒 × W 24h の走行の出力ディレクトリ")
    ap.add_argument("--sample-w8", required=True,
                    help="標本 6 日の gap60_w8(MDE の p・s の出所。§8.6)")
    ap.add_argument("--sample-w24", default=None,
                    help="標本 6 日の gap60_w24(既定は --sample-w8 の隣の gap60_w24)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--seed", type=int, default=1, help="§9.1 の種(既定 1)")
    ap.add_argument("--reps", type=int, default=2000, help="§9.1 の反復回数(既定 2,000)")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent),
                    help="監査の台帳(docs/AUDITOR/ACTION_LOG.md)を探す根。試験でだけ差し替える")
    ap.add_argument("--sens", action="append", default=[], metavar="NAME=DIR",
                    help="感度の走行(繰り返し可)。観測のみの表 observation_only_<NAME>.csv "
                         "を 1 本ずつ出す(t と判定の列なし。決定 19')")
    a = ap.parse_args(argv)

    s24 = Path(a.sample_w24) if a.sample_w24 else Path(a.sample_w8).parent / RUN_W24
    runs = {RUN_W8: Run(RUN_W8, Path(a.run_w8)), RUN_W24: Run(RUN_W24, Path(a.run_w24))}
    samples = {RUN_W8: Run(RUN_W8, Path(a.sample_w8)), RUN_W24: Run(RUN_W24, s24)}

    sens: dict[str, Run] = {}
    for spec in a.sens:
        if "=" not in spec:
            sys.stderr.write(f"[止め] --sens は NAME=DIR の形で渡す: {spec}\n")
            return 1
        nm, _, d = spec.partition("=")
        nm = nm.strip()
        if nm in runs or nm in sens:
            sys.stderr.write(f"[止め] --sens の名前が重なっている: {nm}\n")
            return 1
        sens[nm] = Run(nm, Path(d.strip()))

    # --- サニティ #14(決定 6'): 1 対 1 の対応を走行ごとに測る -----------------
    bad: list[str] = []
    for r in list(runs.values()) + list(sens.values()):
        bad += check_pairing(r)
    if bad:
        sys.stderr.write(
            "[止め] サニティ #14(1 対 1 の対応)が通らない。表を 1 枚も書かずに終わる。\n"
            + "".join(f"       - {b}\n" for b in bad)
        )
        return 1

    groups = build_groups(runs[RUN_W8], runs[RUN_W24])
    if len(groups) != N_GROUPS:
        sys.stderr.write(f"[止め] 群が {len(groups)} 個。§4 の 48 群と違う。\n")
        return 1

    boot = {}
    for name, run in list(runs.items()) + list(sens.items()):
        rng = np.random.default_rng(a.seed)
        nd = len(run.days)
        boot[name] = rng.integers(0, nd, size=(a.reps, nd)) if nd else np.zeros((a.reps, 0), int)

    judge_rows = build_rows(runs, samples, groups, boot, judge=True)
    if len(judge_rows) != N_TESTS:
        sys.stderr.write(f"[止め] 判定の行が {len(judge_rows)} 行。§4.3 の 576 と違う。\n")
        return 1
    obs_rows = build_rows(runs, samples, groups, boot, judge=False)
    # 決定 6: W に依らない 12 群の W = 24h 側は、判定ではなく観測のみの表に出す。
    flat24 = build_flat_groups_w24(runs[RUN_W24])
    obs_rows += build_rows(runs, samples, flat24, boot, judge=False,
                           systems=judge_systems())
    # 決定 19': 感度 1 本ごとに観測のみの表を 1 枚ずつ出す(判定には 1 行も入らない)。
    sens_rows: dict[str, list[dict]] = {}
    for nm, r in sens.items():
        gs = build_groups_single(r)
        sens_rows[nm] = build_rows(
            {nm: r}, {}, gs, boot, judge=False,
            systems=judge_systems() + observation_systems(),
        )
    cells = f1_cells(judge_rows)
    reading = f1_reading(cells)

    # --- 表を書く前に関門を通す(閉じていれば 1 枚も書かない)---------------
    pass_audit_gate(Path(a.root).resolve())

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "judgment_576.csv", JUDGE_HEADER, judge_rows)
    write_csv(out / "f1_12cells.csv", JUDGE_HEADER, cells)
    write_csv(out / "observation_only.csv", OBS_HEADER, obs_rows)
    for nm, rows_ in sens_rows.items():
        write_csv(out / f"observation_only_{nm}.csv", OBS_HEADER, rows_)
    write_csv(out / "why_frame.csv", WHY_HEADER,
              [{**{k: WHY_PLACEHOLDER for k in WHY_HEADER}, "読み": r} for r in WHY_READINGS])
    (out / "f1_reading.txt").write_text(
        "§7.0 の 4 分岐のうちの読み: " + reading + "\n"
        "見たセル: 主軸 D の D1 × 戻り到達 2 系統 × h 6 本 = "
        f"{len(cells)} セル(走行 {RUN_W8})\n",
        encoding="utf-8",
    )

    summary = {
        "単位": UNIT,
        "事前登録": "docs/PHASE2/O3C/PRICE_LEVEL/REACTION_PREREG_2026-09-18.md(確定版・凍結)",
        "seed": a.seed,
        "reps": a.reps,
        "CI水準": {"alpha": ALPHA, "クラスタ": "UTC 日",
                   "方法": (f"正規近似(差 ± z × ブートストラップ SE。"
                            f"z = {BAR_T_SHOWN} は丸め表示で、計算は norm.ppf(1 − α/2))"),
                   "z_{1-α/2}": BAR_T,
                   "注": "|t| ≥ z と CI が 0 を除外することは同値である"},
        "バー": {"|t|": BAR_T, "|t|の丸め表示": BAR_T_SHOWN, "最低イベント数": MIN_N,
                 "最低イベント数の当て先": "その検定に使う、欠測を引いた後の実群の件数 n1",
                 "z_{1-α/2}": Z_ALPHA, "z_{1-β}": Z_POWER, "MDEの係数": MDE_Z,
                 "注": "バー・CI・MDE は同じ z(norm.ppf(1 − α/2))を使う(決定 12')"},
        "分岐": ["不明(n < 30)", "差あり(+)", "差あり(−)",
                 UNKNOWN_MDE, "検出されず(MDE = X)"],
        "検定の数": len(judge_rows),
        "群の数": len(groups),
        "観測のみの表の行数": {
            "observation_only.csv": len(obs_rows),
            **{f"observation_only_{nm}.csv": len(rows_) for nm, rows_ in sens_rows.items()},
        },
        "走行": {
            n: {"path": str(r.path), "window_hours": r.window_hours,
                "日数": len(r.days), "行数": {k: len(v) for k, v in r.by_kind.items()},
                "w_SELL": r.w_sell(),
                "相手がmixed束で落とした合わせた対照": r.n_dropped_mixed_partner,
                "サニティ14_bin_pctの差の最大": r.pairing_worst_bin_pct_gap}
            for n, r in list(runs.items()) + list(sens.items())
        },
        "感度(観測のみ)": {nm: str(r.path) for nm, r in sens.items()},
        "標本(MDE の p・s)": {n: str(r.path) for n, r in samples.items()},
        "対照(ii)の軸の作り方": {
            "own(対照行自身の値)": sorted(
                {g.name for g in groups if g.control_axis == AX_OWN}),
            "partner_sign(符号なしの大きさ × 相手の側の符号)": sorted(
                {g.name for g in groups if g.control_axis == AX_PARTNER_SIGN}),
            "inherit(相手の実群の群を受け継ぐ)": sorted(
                {g.name for g in groups if g.control_axis == AX_INHERIT}),
        },
        "受け継いだ群": [
            {"群": g.name, "走行": g.run, "列": g.col,
             "n_control_matched": int(membership(runs[g.run], KIND_MAT, g).sum())}
            for g in groups if g.control_axis == AX_INHERIT
        ],
        "受け継いだ群の数": sum(1 for g in groups if g.control_axis == AX_INHERIT),
        "相手の符号を当てた群の数": sum(
            1 for g in groups if g.control_axis == AX_PARTNER_SIGN),
        "群ごと": [
            {"群": g.name, "走行": g.run, "軸": g.axis, "列": g.col,
             "分位": g.q, "side": g.side,
             "対照は1対1の束から受け継いだか": g.pair_inherit,
             "対照(ii)の軸の作り方": g.control_axis,
             "切り値": (list(g.cuts) if g.cuts else None),
             "n_liq": int(membership(runs[g.run], KIND_LIQ, g).sum()),
             "n_control_uniform": int(membership(runs[g.run], KIND_UNI, g).sum()),
             "n_control_matched": int(membership(runs[g.run], KIND_MAT, g).sum())}
            for g in groups
        ],
        "F1の読み": reading,
        "注記": [
            "対照 (i) の向きの要る量(*_reactdir)は §6.1 の重み付けを通した。"
            "SE の合成は独立を仮定しており、**SE を小さく見る向きの近似**である(§6.1 の 3)。",
            "合わせた対照の *_reactdir は 1 対 1 の相手の束の side の符号を当てた"
            "(§6.1 の 4。下向き = SELL 側では mfe と mae が入れ替わる)。",
            "対照 (ii) の軸の値の作り方は 3 通りで、走行ごとに数えて決めた"
            "(summary の「対照(ii)の軸の作り方」)。own = 対照行自身の値 /"
            " partner_sign = 対照行の符号なしの大きさに相手の側の符号を当てた対照自身の値 /"
            " inherit = 対照行に対応物が無いので 1 対 1 の相手の群を受け継いだ。"
            "一様対照は 1 対 1 の相手が無いので own 以外の群には入れていない"
            "(その群の 対照(i) と 差(i) は空になる)。",
            "相手が mixed 束の合わせた対照は全群から落とした"
            "(件数は summary の「相手がmixed束で落とした合わせた対照」)。"
            "実群の側が mixed を主表から外しているので、残すと 1 対 1 が崩れるためである。",
            "1 対 1 の対応は table.csv の matched_liq_id 列で取り、"
            "走行ごとにサニティ #14(相手が実在 / 同日 / bin_pct の差が ±5 以内)を通した。",
            "判定に使う走行は gap 60 秒 × W 8h と gap 60 秒 × W 24h の 2 本で、"
            "W に依らない 12 群は gap60_w8 の走行からだけ 576 検定に入れた(§4 の内訳表)。"
            "同じ 12 群の W = 24h 側は観測のみの表に出してある(t と判定の列なし)。"
            "その 12 群の切り値は W = 24h の実群で切り直してある(決定 20')。",
            "感度の走行(--sens)は observation_only_<NAME>.csv に別の表として出した。"
            "対を成す標本が無いので MDE の列は空である。判定にも F1 の読みにも入れていない。",
            "「全体」群の 実群 の欄は差の入力として出しているだけで、"
            "その水準を根拠にした文はこの summary にも標準出力にも書いていない"
            "(事前登録 §3 の #1 = a「全体分布の水準を根拠にした主張は書かない」)。",
            "不在を断ずる語は 1 つも書かない。"
            "検出できなかったセルは「検出されず(MDE = X)」と書き、"
            "MDE が計算できなかったセルは「" + UNKNOWN_MDE + "」と書く(決定 17')。"
            "MDE との比較(≥ / <)は別の列に残してある。",
            "MDE は p・s を標本 6 日で固定し、n だけ走行後の群の件数から取った(§8.6)。"
            "群の切り方は判定区間の実群で決めた切り値を標本にも当てた(§4)。",
            "前進到達(fwd_node)はどちらの表にも入れていない(1 周目は測定不能。§4.3)。",
        ],
    }
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    names = (["judgment_576.csv", "f1_12cells.csv", "observation_only.csv"]
             + [f"observation_only_{nm}.csv" for nm in sens_rows]
             + ["why_frame.csv", "f1_reading.txt", "summary.json"])
    hits = scan_forbidden(out, names)
    if hits:
        sys.stderr.write("[止め] 出力に判定語が混ざっている: " + " / ".join(hits) + "\n")
        return 1
    write_md5(out, names)

    print(f"判定の表: {len(judge_rows)} 行 / 観測のみの表: {len(obs_rows)} 行 / 群 {len(groups)}")
    for nm, rows_ in sens_rows.items():
        print(f"感度(観測のみ)の表 {nm}: {len(rows_)} 行")
    print(f"F1 の 12 セルの読み: {reading}")
    print(f"出力先: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
