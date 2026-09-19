#!/usr/bin/env python3
"""O-3c 段 A **2 周目**(機構仮説 F1′)の読みの道具。

事前登録: `docs/PHASE2/O3C/PRICE_LEVEL/REACTION_R2_PREREG_2026-09-19.md`(§3〜§8・§10)。

**この道具がすること**
  - `--power`  : z と h ごとの MDE を印字するだけ(表を 1 枚も書かない。関門も通さない)。
  - `--judge`  : 関門(§8 の #7)→ サニティ #1〜#6 → 6 セルの表と観測のみの表を書く。
                 サニティが破れたら表は 1 枚も書かず `stopped.txt`(破れた番号と検査の名前)
                 だけを書く。`--out-dir` が既にあれば何も書かずに止まる。**判定は一度だけ。**

**1 周目(`scripts/o3c_reaction_judge.py`)から引き継いだ規則**
  - 対照の向き: 合わせた対照は `bp_{h}m` に**相手の束の side の符号**を当てる
    (SELL: −bp / BUY: +bp)。1 周目 `Run.values` / `updown` と同じ規則。**実測で一致を確認**
    (サニティ #2)。
  - 相手が `table_mixed.csv` の束である合わせた対照は落とす(1 周目の決定 8')。
  - 7 分岐の語と当てる順(n1 → n2 → t → |t| ≥ z → MDE → 検出されず)は 1 周目 `decide` と同じ。
  - 関門の呼び方は 1 周目 `pass_audit_gate` と同じ(表を 1 枚も書く前に通す。迂回する旗は無い)。

**1 周目から変えたところ(事前登録 §0 の「改良点は 2 つだけ」)**
  1. 判定の量を `bp_{h}m_reactdir`(負 = 反転)にする。
  2. 対照を出発点の距離(|`dist_vwap_bp`|)でそろえる(D1 の 10 分位の帯で標準化する)。
  これに伴い、ブートストラップは事前登録 §3 の「**帯の中で行ごとに独立に再抽出**」である
  (1 周目の「UTC 日をクラスタにして引く」ではない)。

**限界**
  - この道具は事前登録どおりに**読む**だけで、判定をやり直す経路を持たない。
  - 種と反復は定数(`SEED` / `REPS`)で、引数から動かせない(1 周目の決定 1''' と同じ)。
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

# =============================================================================
# 事前登録で凍結された定数(§3 / §6 / §7 / §10。手で動かさない)
# =============================================================================
UNIT = "o3c_reaction_r2_20260919"          # 関門の単位名(§8 の #7)
STAGE = "事前登録"                          # 同上

PREREG_REL = "docs/PHASE2/O3C/PRICE_LEVEL/REACTION_R2_PREREG_2026-09-19.md"

CUT = -14472.33333333332                   # §3 D1 の切り値(1 周目の実測。凍結)
HORIZONS = (1, 5, 15, 30, 60, 240)         # §4 判定に使う h
N_TESTS = 582                              # §6 1 周目の 576 + この周の 6
ALPHA = 0.05 / N_TESTS                     # §6
_ND = NormalDist()
Z_ALPHA = _ND.inv_cdf(1 - ALPHA / 2)       # §6 z = norm.ppf(1 − α/2)
Z_POWER = 0.8416                           # §7 の式に書かれた値をそのまま使う
MDE_Z = Z_ALPHA + Z_POWER                  # §7
N1_PRE = 5048                              # §7 開封前に数えられる件数
N2_PRE = 4101                              # §7 同上
N_BANDS = 10                               # §3 帯 B_k = D1 の d の 10 分位
REPS = 2000                                # §3 ブートストラップの反復
SEED = 1                                   # §3 種
MIN_N = 30                                 # §6 / §8 の #5
BAR_NEAR_HALFWIDTH = 0.065                 # §6 バー近傍
WANTED = {1: 2.0, 240: 5.0}                # §7 欲しい効果(bp)。他の h は事前登録に無い

BIG = 1e9                                  # 帯の上端(`bugcheck2.py` と同じ)
UNIT_BP = "bp"

KIND_LIQ = "liq"
KIND_MAT = "control_matched"

# 標準化の道具の検算(§8 の #4)。`docs/DATA/probes/20260919_o3c_reaction_bugcheck2.log`
SANITY4_COL = "reach_back_vwap_240m"
SANITY4_EXPECT = 0.015
SANITY_TOL = 1e-3

# 7 分岐(§6。1 周目 §10.1 と同じ語)
UNKNOWN_N = "不明(n < 30)"
UNKNOWN_N2 = "不明(n2 < 30)"
UNKNOWN_T = "不明(t 未算出)"
UNKNOWN_MDE = "不明(MDE 未算出)"
BRANCHES = [UNKNOWN_N, UNKNOWN_N2, UNKNOWN_T, "差あり(+)", "差あり(−)",
            UNKNOWN_MDE, "検出されず(MDE = X bp)"]

DEFAULT_TABLE = "backtest_data/o3c_reaction_20260918_full/gap60_w8"
DEFAULT_TABLE_W24 = "backtest_data/o3c_reaction_20260918_full/gap60_w24"
DEFAULT_SAMPLE = "backtest_data/o3c_reaction_20260918_sample/gap60_w8"
DEFAULT_OBS = "backtest_data/o3c_reaction_20260918_judge/observation_only.csv"

# 出力(§10 の 3)
CELLS_NAME = "cells_6.csv"
OBS_NAME = "observation_only_r2.csv"
BANDS_NAME = "bands.csv"
SUMMARY_NAME = "summary.json"
STOPPED_NAME = "stopped.txt"   # §8: 破れたら番号と検査の名前だけを書く

CELLS_HEADER = ["h", "n1", "n2", "mean_D1", "mean_C(標準化)", "Δ_h", "SE_h", "t_h",
                "CI下限", "CI上限", "MDE", "判定", "バー近傍"]
OBS_HEADER = ["区分", "内容", "h", "n1", "n2", "mean_D1", "mean_C(標準化)", "Δ_h",
              "MDE(参考。族の α に入らない)", "備考"]
BANDS_HEADER = ["区分", "h", "帯", "下限", "上限", "w_k", "n_D1", "n_C",
                "mean_D1", "mean_C", "差"]


# =============================================================================
# 読み込み(必要な列だけ)
# =============================================================================
def needed_columns() -> set[str]:
    cols = {"kind", "day", "cascade_id", "matched_liq_id", "side", "doi_pre_1h",
            "dist_vwap_bp", "dist_node_bp", SANITY4_COL}
    for h in HORIZONS:
        cols.add(f"bp_{h}m")
        cols.add(f"bp_{h}m_reactdir")
    return cols


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


def _read_cols(path: Path, wanted: set[str]) -> dict[str, list[str]]:
    """CSV から欲しい列だけを読む(60,903 行 × 150 列を全部辞書にしないため)。"""
    with path.open(encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh)
        header = next(rd)
        idx = {c: i for i, c in enumerate(header) if c in wanted}
        out: dict[str, list[str]] = {c: [] for c in idx}
        for row in rd:
            for c, i in idx.items():
                out[c].append(row[i] if i < len(row) else "")
    return out


class Table:
    """1 走行の `table.csv`(+ `table_mixed.csv`)。

    実群 = `kind == liq` の行、合わせた対照 = `kind == control_matched` の行。
    対照の向きは 1 対 1 の相手(`matched_liq_id`)の束の side から作る(1 周目と同じ規則)。
    """

    def __init__(self, path: Path | str):
        self.path = Path(path)
        want = needed_columns()
        cols = _read_cols(self.path / "table.csv", want)
        self._cols = cols
        mixed_p = self.path / "table_mixed.csv"
        if mixed_p.exists():
            m = _read_cols(mixed_p, {"cascade_id", "side"})
        else:
            m = {"cascade_id": [], "side": []}
        self.mixed_ids = set(m["cascade_id"])

        kind = np.array(cols["kind"], dtype=object)
        self.liq_i = np.flatnonzero(kind == KIND_LIQ)
        self.mat_i = np.flatnonzero(kind == KIND_MAT)

        side_by_id: dict[str, str] = {}
        for i in self.liq_i:
            side_by_id[cols["cascade_id"][i]] = cols["side"][i]
        for cid, sd in zip(m["cascade_id"], m["side"]):
            side_by_id.setdefault(cid, sd)
        partner = [cols["matched_liq_id"][i] for i in self.mat_i]
        self.partner_id = partner
        self.partner_side = [side_by_id.get(p) for p in partner]
        self.partner_mixed = np.array([p in self.mixed_ids for p in partner], dtype=bool)
        # 相手が引けなかった対照(1 周目の `pair_of_matched is None` に当たる)。
        self.partner_missing = int(sum(1 for s in self.partner_side if s is None))
        self._mat_pos = {int(g): k for k, g in enumerate(self.mat_i)}

    # -- 列 ------------------------------------------------------------------
    def num(self, idx: np.ndarray, col: str) -> np.ndarray:
        src = self._cols[col]
        return np.array([_f(src[i]) for i in idx], dtype=float)

    def text(self, idx: np.ndarray, col: str) -> list[str]:
        src = self._cols[col]
        return [src[i] for i in idx]

    # -- 群(§3)-------------------------------------------------------------
    def d1_idx(self) -> np.ndarray:
        """D1 = 清算行のうち `doi_pre_1h` ≤ 切り値。"""
        v = self.num(self.liq_i, "doi_pre_1h")
        return self.liq_i[v <= CUT]

    def tertile_cuts(self) -> tuple[float, float]:
        """主軸 D の 3 分位の切り値(1 周目 `tertile_cuts` と同じ作り)。"""
        v = self.num(self.liq_i, "doi_pre_1h")
        fin = v[np.isfinite(v)]
        if fin.size == 0:
            return float("nan"), float("nan")
        lo, hi = np.nanpercentile(fin, [100.0 / 3.0, 200.0 / 3.0])
        return float(lo), float(hi)

    def liq_idx_by_tertile(self, q: int) -> np.ndarray:
        """観測のみ (c) 用: 主軸 D の 3 分位の実群。"""
        v = self.num(self.liq_i, "doi_pre_1h")
        lo, hi = self.tertile_cuts()
        if not (math.isfinite(lo) and math.isfinite(hi)):
            return self.liq_i[np.zeros(v.size, dtype=bool)]
        if q == 1:
            sel = v <= lo
        elif q == 2:
            sel = (v > lo) & (v <= hi)
        else:
            sel = v > hi
        return self.liq_i[sel & np.isfinite(v)]

    def _mat_mask_usable(self) -> np.ndarray:
        return ~self.partner_mixed

    def control_idx(self, lo: float | None = None, hi: float | None = None) -> np.ndarray:
        """対照 C = `control_matched` で `doi_pre_1h` が区間に入り、相手が mixed でないもの。

        既定(`lo is None and hi is None`)は §3 の対照 C(`doi_pre_1h` ≤ 切り値)。
        """
        v = self.num(self.mat_i, "doi_pre_1h")
        if lo is None and hi is None:
            sel = v <= CUT
        elif lo is None:
            sel = v <= hi          # type: ignore[operator]
        elif hi is None:
            sel = v > lo
        else:
            sel = (v > lo) & (v <= hi)
        return self.mat_i[sel & self._mat_mask_usable()]

    def control_idx_all(self) -> np.ndarray:
        return self.mat_i[self._mat_mask_usable()]

    # -- 量 ------------------------------------------------------------------
    def r_liq(self, idx: np.ndarray, h: int) -> np.ndarray:
        """清算行の `r_h` = 走行の表の `bp_{h}m_reactdir`(負 = 反転)。"""
        return self.num(idx, f"bp_{h}m_reactdir")

    def r_ctl(self, idx: np.ndarray, h: int) -> np.ndarray:
        """対照の `r_h` = `bp_{h}m` に**相手の束の side の符号**(SELL: −bp / BUY: +bp)。

        1 周目 `Run.values(KIND_MAT, 'bp_{h}m_reactdir')` と同じ規則である
        (1 周目は `updown` で下向き = −bp / 上向き = +bp を作り、相手が SELL なら
         下向きを採る)。相手が引けない行は NaN(1 周目も NaN のまま残す)。
        """
        raw = self.num(idx, f"bp_{h}m")
        out = np.full(raw.size, np.nan)
        for j, g in enumerate(idx):
            side = self.partner_side[self._mat_pos[int(g)]]
            if side is None:
                continue
            out[j] = -raw[j] if side == "SELL" else raw[j]
        return out

    def dist(self, idx: np.ndarray, col: str = "dist_vwap_bp") -> np.ndarray:
        """`d` = |`dist_vwap_bp`|(§3)。観測のみ (b) では `dist_node_bp` を渡す。"""
        return np.abs(self.num(idx, col))

    def plain(self, idx: np.ndarray, col: str) -> np.ndarray:
        return self.num(idx, col)


# =============================================================================
# 標準化(§3 の帯 B_k と Δ_h)
# =============================================================================
def band_edges(d: np.ndarray) -> list[float]:
    """D1 の `d` の 10 分位。`bugcheck2.py` と同じ作り(下端 0 / 上端 1e9)。

    有限な値が 1 つも無いときは NaN の境界を返す(帯に入る行が 0 になり、
    そのセルは「不明」として出る。**黙って別の切り方に落ちない**)。
    """
    fin = d[np.isfinite(d)]
    if fin.size == 0:
        return [float("nan")] * (N_BANDS + 1)
    e = [float(x) for x in np.nanpercentile(fin, np.linspace(0.0, 100.0, N_BANDS + 1))]
    e[0] = 0.0
    e[-1] = BIG
    return e


def band_index(d: np.ndarray, edges: list[float]) -> np.ndarray:
    """各行の帯番号(0〜9)。帯に入らない行(NaN など)は −1。

    `bugcheck2.py` と同じ半開区間 [下限, 上限) で当てる。
    """
    out = np.full(d.size, -1, dtype=int)
    for k in range(N_BANDS):
        m = (d >= edges[k]) & (d < edges[k + 1])
        out[m] = k
    return out


def edges_strictly_increasing(edges: list[float]) -> bool:
    return all(edges[i] < edges[i + 1] for i in range(len(edges) - 1))


class Standardized:
    """1 セル(1 つの量 × 1 つの h)の標準化の結果。

    Δ = Σ_k w_k (mean_D1,k − mean_C,k)、w_k = n_D1,k / n_D1(§3)。
    **n_D1,k はその帯で `r_h` が有限な D1 の行数**(平均に寄与する行と重みの母数をそろえる。
    事前登録は n_D1,k の欠測の扱いを書いていない ⇒ 報告の「未決」に出す)。
    """

    def __init__(self, v1: np.ndarray, b1: np.ndarray,
                 v2: np.ndarray, b2: np.ndarray, edges: list[float]):
        self.edges = edges
        self.bands: list[dict] = []
        self.parts1: list[np.ndarray] = []
        self.parts2: list[np.ndarray] = []
        for k in range(N_BANDS):
            a = v1[(b1 == k) & np.isfinite(v1)]
            b = v2[(b2 == k) & np.isfinite(v2)]
            self.parts1.append(a)
            self.parts2.append(b)
            self.bands.append({
                "帯": k + 1, "下限": edges[k], "上限": edges[k + 1],
                "n_D1": int(a.size), "n_C": int(b.size),
                "mean_D1": float(a.mean()) if a.size else float("nan"),
                "mean_C": float(b.mean()) if b.size else float("nan"),
            })
        self.n1 = int(sum(x["n_D1"] for x in self.bands))
        self.n2 = int(sum(x["n_C"] for x in self.bands))
        self.w = np.array(
            [(x["n_D1"] / self.n1) if self.n1 else float("nan") for x in self.bands]
        )
        for k, x in enumerate(self.bands):
            x["w_k"] = float(self.w[k])
            x["差"] = x["mean_D1"] - x["mean_C"]
        self.mean_d1 = self._weighted("mean_D1")
        self.mean_c = self._weighted("mean_C")
        self.delta = (self.mean_d1 - self.mean_c
                      if math.isfinite(self.mean_d1) and math.isfinite(self.mean_c)
                      else float("nan"))
        self.min_n1 = min(x["n_D1"] for x in self.bands)
        self.min_n2 = min(x["n_C"] for x in self.bands)
        self.se = float("nan")
        self.reps_finite = 0

    def _weighted(self, key: str) -> float:
        """Σ_k w_k mean_k。**帯が 1 つでも空なら nan**(空の帯を黙って落とさない)。"""
        if not self.n1:
            return float("nan")
        tot = 0.0
        for k, x in enumerate(self.bands):
            if not math.isfinite(x[key]) or not math.isfinite(self.w[k]):
                return float("nan")
            tot += self.w[k] * x[key]
        return float(tot)

    def bootstrap(self, reps: int | None = None,
                  seed: int | None = None) -> tuple[float, int]:
        """§3 SE_h: **帯の中で行ごとに独立に再抽出**する(重み w_k は固定)。

        種は毎セル同じ `SEED` から作る(セルの並び順に結果が依らないようにするため)。
        既定は**定数**(`REPS` / `SEED`)を呼び出し時に読む(引数から動かす経路は作らない)。
        """
        reps = REPS if reps is None else reps
        seed = SEED if seed is None else seed
        if not math.isfinite(self.delta):
            self.se, self.reps_finite = float("nan"), 0
            return self.se, self.reps_finite
        rng = np.random.default_rng(seed)
        acc = np.zeros(reps, dtype=float)
        for k in range(N_BANDS):
            a, b = self.parts1[k], self.parts2[k]
            if a.size == 0 or b.size == 0:
                self.se, self.reps_finite = float("nan"), 0
                return self.se, self.reps_finite
            ia = rng.integers(0, a.size, size=(reps, a.size))
            ib = rng.integers(0, b.size, size=(reps, b.size))
            acc += self.w[k] * (a[ia].mean(axis=1) - b[ib].mean(axis=1))
        fin = acc[np.isfinite(acc)]
        self.reps_finite = int(fin.size)
        self.se = float(fin.std(ddof=1)) if fin.size > 1 else float("nan")
        return self.se, self.reps_finite


def standardize(tab: Table, liq_idx: np.ndarray, ctl_idx: np.ndarray, *,
                col_liq, col_ctl, dist_col: str = "dist_vwap_bp",
                edges: list[float] | None = None) -> Standardized:
    """`col_liq` / `col_ctl` は (Table, idx) -> 値の配列。"""
    d1 = tab.dist(liq_idx, dist_col)
    dc = tab.dist(ctl_idx, dist_col)
    if edges is None:
        edges = band_edges(d1)
    b1 = band_index(d1, edges)
    b2 = band_index(dc, edges)
    return Standardized(col_liq(tab, liq_idx), b1, col_ctl(tab, ctl_idx), b2, edges)


# =============================================================================
# MDE(§7)と分岐(§6)
# =============================================================================
def mde_from_sample(sample: Table, h: int, n1: int | None = None,
                    n2: int | None = None) -> tuple[float, int, int]:
    """MDE_h = (z + 0.8416) × sqrt(s_D1² / n1 + s_C² / n2)。

    s は**標本 6 日**の `bp_{h}m_reactdir` の SD。群の切り方は判定区間と同じ
    (D1 = `doi_pre_1h` ≤ 切り値 / 対照 C = 同じ切り値 + 相手が mixed でない)。
    n1 / n2 は事前登録が凍結した件数(5,048 / 4,101)。
    返り値: (MDE, 標本の D1 の件数, 標本の対照 C の件数)。
    """
    n1 = N1_PRE if n1 is None else n1
    n2 = N2_PRE if n2 is None else n2
    d1 = sample.d1_idx()
    c = sample.control_idx()
    a = sample.r_liq(d1, h)
    b = sample.r_ctl(c, h)
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if a.size < 2 or b.size < 2 or n1 <= 0 or n2 <= 0:
        return float("nan"), int(a.size), int(b.size)
    var = float(a.std(ddof=1)) ** 2 / n1 + float(b.std(ddof=1)) ** 2 / n2
    if not math.isfinite(var) or var < 0:
        return float("nan"), int(a.size), int(b.size)
    return MDE_Z * math.sqrt(var), int(a.size), int(b.size)


def mde_weighted_from_sample(sample: Table, h: int, n1: int | None = None,
                             n2: int | None = None) -> tuple[float, str, list[int],
                                                             list[int]]:
    """§7 の「式の近似の向き」: **帯の重みを当てた実際の分散**を標本の帯の n から出す。

    Var = s_D1² / n1 + (s_C² / n2) × F、F = Σ_k w_k² / c_k
      w_k = 標本の D1 の帯の割合、c_k = 標本の対照 C の帯の割合。
    D1 の項は w_k が D1 自身の分布なので Σ w_k² / w_k = 1 となり、§7 の式と同じである。
    C の項は c_k ≠ w_k のぶん F ≥ 1 で大きくなる(= §7 の式は MDE を楽観側に見る)。

    **対照が 1 行も居ない帯があると F は発散する**ので、その場合は
    「残りの帯だけの部分和 = F の下限」で計算し、その旨を返り値の注記に書く
    (**下限は楽観側なので、注記なしに使わないこと**)。
    返り値: (MDE, 注記, 標本の帯ごとの D1 の件数, 同 対照 C の件数)。
    """
    n1 = N1_PRE if n1 is None else n1
    n2 = N2_PRE if n2 is None else n2
    d1 = sample.d1_idx()
    c = sample.control_idx()
    edges = band_edges(sample.dist(d1))
    b1 = band_index(sample.dist(d1), edges)
    b2 = band_index(sample.dist(c), edges)
    a_all = sample.r_liq(d1, h)
    b_all = sample.r_ctl(c, h)
    n_d1 = [int(np.sum((b1 == k) & np.isfinite(a_all))) for k in range(N_BANDS)]
    n_c = [int(np.sum((b2 == k) & np.isfinite(b_all))) for k in range(N_BANDS)]
    a = a_all[np.isfinite(a_all)]
    b = b_all[np.isfinite(b_all)]
    tot1, tot2 = sum(n_d1), sum(n_c)
    if a.size < 2 or b.size < 2 or tot1 == 0 or tot2 == 0:
        return float("nan"), "標本が足りない", n_d1, n_c
    empty = [k + 1 for k in range(N_BANDS) if n_c[k] == 0]
    f = 0.0
    for k in range(N_BANDS):
        if n_c[k] == 0:
            continue
        w = n_d1[k] / tot1
        ck = n_c[k] / tot2
        f += w * w / ck
    var = float(a.std(ddof=1)) ** 2 / n1 + (float(b.std(ddof=1)) ** 2 / n2) * f
    note = (f"F = {f:.4f}" if not empty
            else f"F ≥ {f:.4f}(**下限**。標本の帯 {empty} に対照が 0 行なので"
                 f"真の F は発散する)")
    return MDE_Z * math.sqrt(var), note, n_d1, n_c


def decide(n1: int, n2: int, min_n1: int, min_n2: int, t: float, diff: float,
           m: float) -> str:
    """§6 の 7 分岐。上から当てる(1 周目 `decide` と同じ順)。

    帯の件数は §6 の「いずれかの帯で n < 30 なら、その帯を落とさず『不明』にする」を当てる
    (**帯を落とさない**)。
    """
    if n1 < MIN_N or min_n1 < MIN_N:
        return UNKNOWN_N
    if n2 < MIN_N or min_n2 < MIN_N:
        return UNKNOWN_N2
    if not math.isfinite(t):
        return UNKNOWN_T
    if abs(t) >= Z_ALPHA:
        return "差あり(+)" if diff > 0 else "差あり(−)"
    if not math.isfinite(m):
        return UNKNOWN_MDE
    return f"検出されず(MDE = {_fmt(m)} {UNIT_BP})"


def bar_near(t: float) -> str:
    """|t| が z ± 0.065 に入るとき ○(§6。**観測のみ。判定は変えない**)。"""
    if not math.isfinite(t):
        return ""
    return "○" if abs(abs(t) - Z_ALPHA) <= BAR_NEAR_HALFWIDTH else ""


def f1_reading(cells: list[dict]) -> str:
    """§6 の F1′ の読み(4 分岐)。

      整合 = 差あり(−) ≥ 1 かつ 差あり(+) = 0   ← F1′ は「反転(負)」を言う
      反証 = 差あり(+) ≥ 1 かつ 差あり(−) = 0
      混在 = 両方ある
      不明 = 差ありが 1 つも無い(内訳を併記する)
    """
    if len(cells) != len(HORIZONS):
        return f"読めない({len(HORIZONS)} セルのはずが {len(cells)} セル)"
    pos = sum(1 for c in cells if c["判定"] == "差あり(+)")
    neg = sum(1 for c in cells if c["判定"] == "差あり(−)")
    if pos and neg:
        return f"混在(差あり(−) {neg} / 差あり(+) {pos})"
    if neg:
        return f"F1′ と整合(差あり(−) {neg} / 差あり(+) 0)"
    if pos:
        return f"F1′ の反証(差あり(+) {pos} / 差あり(−) 0)"
    few = sum(1 for c in cells if c["判定"] == UNKNOWN_N)
    few2 = sum(1 for c in cells if c["判定"] == UNKNOWN_N2)
    not_ = sum(1 for c in cells if c["判定"] == UNKNOWN_T)
    nom = sum(1 for c in cells if c["判定"] == UNKNOWN_MDE)
    nod = sum(1 for c in cells if str(c["判定"]).startswith("検出されず"))
    return (f"不明(差あり 0。内訳: {UNKNOWN_N} {few} / {UNKNOWN_N2} {few2} / "
            f"{UNKNOWN_T} {not_} / {UNKNOWN_MDE} {nom} / 検出されず {nod})")


def _fmt(x, nd: int = 6) -> str:
    if x is None:
        return ""
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if not math.isfinite(v):
        return "nan"
    return f"{v:.{nd}f}"


# =============================================================================
# 関門(`CLAUDE.md` §5.0 の 2 / 事前登録 §8 の #7)
# =============================================================================
def pass_audit_gate(root: Path) -> None:
    """表を 1 枚も書く前に通す。迂回する旗は無い(1 周目 `pass_audit_gate` と同じ形)。"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _research_audit_gate import require_audit

    try:
        require_audit(UNIT, STAGE, root)
    except SystemExit:
        sys.stderr.write(
            "\n[止め] 事前登録の監査が通っていないので、表を 1 枚も書かずに終わる。\n"
            f"       単位: {UNIT} / 段階: {STAGE} / 台帳: {root}/docs/AUDITOR/ACTION_LOG.md\n"
        )
        raise SystemExit(1) from None


def check_root_for_out_dir(out_dir: Path, root: Path) -> list[str]:
    """本番の出力に試験用の台帳を使わせない(1 周目 `check_root_for_out_dir` と同じ)。"""
    repo = Path(__file__).resolve().parent.parent
    try:
        out_dir.resolve().relative_to((repo / "backtest_data").resolve())
    except ValueError:
        return []
    if root.resolve() != repo.resolve():
        return [f"--out-dir がリポジトリの backtest_data/ の下({out_dir})なのに "
                f"--root がリポジトリ直下ではない({root})。"
                f"本番の出力に試験用の台帳は使えない。"]
    return []


# =============================================================================
# サニティ(§8)
# =============================================================================
def read_observation_only(path: Path) -> dict[str, dict[str, str]]:
    """1 周目の観測のみの表から D_Q1 / gap60_w8 の行を拾う。"""
    out: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("群") == "D_Q1" and r.get("走行") == "gap60_w8":
                out[r["観測量"]] = r
    return out


def run_sanity(tab: Table, obs_path: Path,
               cells: list[dict]) -> tuple[list[dict], list[str]]:
    """§8 の #1〜#6 を測る。返り値: (検査の結果, 止める理由の一覧)。

    **#5 だけは止めない。**§6 が「いずれかの帯で n < 30 なら、その帯を落とさず
    『不明』にする」と書いているので、#5 の破れはセルの判定(不明)として現れる。
    それ以外(#1〜#4・#6)は §8 の柱書き「1 つでも破れたら表を書かない」に従って止める。
    """
    res: list[dict] = []
    stop: list[str] = []

    def add(num: int, name: str, ok: bool, detail: str, halting: bool = True) -> None:
        res.append({"#": num, "検査": name, "結果": "通る" if ok else "破れ",
                    "詳細": detail, "止める": bool(halting and not ok)})
        if halting and not ok:
            stop.append(f"#{num} {name}: {detail}")

    d1 = tab.d1_idx()
    c = tab.control_idx()
    add(1, "D1 の行数 = 5,048 / 対照 C = 4,101",
        len(d1) == N1_PRE and len(c) == N2_PRE,
        f"D1 {len(d1)} 行 / 対照 C {len(c)} 行(期待 {N1_PRE} / {N2_PRE})")

    obs = read_observation_only(obs_path) if obs_path.exists() else {}
    if not obs:
        add(2, "対照の r_h の符号付けが 1 周目と一致", False,
            f"1 周目の観測のみの表が読めない({obs_path})")
        add(3, "D1 の r_h の平均が 1 周目と一致", False,
            f"1 周目の観測のみの表が読めない({obs_path})")
    else:
        bad2, bad3 = [], []
        for h in HORIZONS:
            key = f"bp_{h}m_reactdir"
            row = obs.get(key)
            if row is None:
                bad2.append(f"h={h} 1 周目に行が無い")
                bad3.append(f"h={h} 1 周目に行が無い")
                continue
            m2 = float(np.nanmean(tab.r_ctl(c, h)))
            e2 = _f(row["対照(ii)"])
            if not (abs(m2 - e2) <= SANITY_TOL):
                bad2.append(f"h={h} {m2:.6f} vs {e2:.6f}")
            m1 = float(np.nanmean(tab.r_liq(d1, h)))
            e1 = _f(row["実群"])
            if not (abs(m1 - e1) <= SANITY_TOL):
                bad3.append(f"h={h} {m1:.6f} vs {e1:.6f}")
        add(2, "対照の r_h の符号付けが 1 周目と 1e−3 以内(6 h)",
            not bad2, "一致" if not bad2 else " / ".join(bad2))
        add(3, "D1 の r_h の平均が 1 周目と 1e−3 以内(6 h)",
            not bad3, "一致" if not bad3 else " / ".join(bad3))

    st4 = standardize(
        tab, d1, c,
        col_liq=lambda t, i: t.plain(i, SANITY4_COL),
        col_ctl=lambda t, i: t.plain(i, SANITY4_COL),
    )
    ok4 = math.isfinite(st4.delta) and abs(st4.delta - SANITY4_EXPECT) <= SANITY_TOL
    add(4, "標準化の検算(`reach_back_vwap_240m` の 10 分位)= +0.015",
        ok4, f"{st4.delta:+.6f}(期待 {SANITY4_EXPECT:+.3f} ± {SANITY_TOL})")

    bad5 = [f"h={x['h']} D1 の帯の最小 {x['_min_n1']} / C の帯の最小 {x['_min_n2']}"
            for x in cells if x["_min_n1"] < MIN_N or x["_min_n2"] < MIN_N]
    add(5, "各帯の n ≥ 30(D1・C とも)", not bad5,
        "全帯 30 以上" if not bad5
        else " / ".join(bad5) + "(§6 によりそのセルは不明)",
        halting=False)

    bad6 = [f"h={x['h']} 有限 {x['_reps']} / {REPS}"
            for x in cells if x["_reps"] != REPS]
    add(6, f"ブートストラップ {REPS} 回すべて有限", not bad6,
        "すべて有限" if not bad6 else " / ".join(bad6))
    return res, stop


# =============================================================================
# 表を組む
# =============================================================================
def build_cells(tab: Table, sample: Table) -> tuple[list[dict], list[dict], dict]:
    """判定に使う 6 セル(§4)と、その帯の表(観測のみ (d))。"""
    d1 = tab.d1_idx()
    c = tab.control_idx()
    edges = band_edges(tab.dist(d1))
    cells: list[dict] = []
    bands: list[dict] = []
    for h in HORIZONS:
        st = standardize(tab, d1, c,
                         col_liq=lambda t, i, h=h: t.r_liq(i, h),
                         col_ctl=lambda t, i, h=h: t.r_ctl(i, h),
                         edges=edges)
        se, reps = st.bootstrap()
        t_h = (st.delta / se if (math.isfinite(se) and se > 0
                                 and math.isfinite(st.delta)) else float("nan"))
        m, _, _ = mde_from_sample(sample, h)
        lo = st.delta - Z_ALPHA * se if math.isfinite(se) else float("nan")
        hi = st.delta + Z_ALPHA * se if math.isfinite(se) else float("nan")
        verdict = decide(st.n1, st.n2, st.min_n1, st.min_n2, t_h, st.delta, m)
        cells.append({
            "h": h, "n1": st.n1, "n2": st.n2,
            "mean_D1": _fmt(st.mean_d1), "mean_C(標準化)": _fmt(st.mean_c),
            "Δ_h": _fmt(st.delta), "SE_h": _fmt(se), "t_h": _fmt(t_h, 4),
            "CI下限": _fmt(lo), "CI上限": _fmt(hi), "MDE": _fmt(m),
            "判定": verdict, "バー近傍": bar_near(t_h),
            "_min_n1": st.min_n1, "_min_n2": st.min_n2, "_reps": reps,
        })
        for b in st.bands:
            bands.append({"区分": "判定(gap60_w8 / |dist_vwap_bp|)", "h": h,
                          "帯": b["帯"], "下限": _fmt(b["下限"]), "上限": _fmt(b["上限"]),
                          "w_k": _fmt(b["w_k"]), "n_D1": b["n_D1"], "n_C": b["n_C"],
                          "mean_D1": _fmt(b["mean_D1"]), "mean_C": _fmt(b["mean_C"]),
                          "差": _fmt(b["差"])})
    meta = {"帯の境界": [float(x) for x in edges],
            "帯の境界は単調増加": edges_strictly_increasing(edges),
            "D1 の行数": int(len(d1)), "対照 C の行数": int(len(c)),
            "帯に入らなかった D1 の行": int(np.sum(band_index(tab.dist(d1), edges) < 0)),
            "帯に入らなかった対照 C の行": int(np.sum(band_index(tab.dist(c), edges) < 0))}
    return cells, bands, meta


def build_observation_only(tab: Table, tab24: Table | None) -> list[dict]:
    """§4 の観測のみ (a)〜(e)。**α にも判定にも入れない。**"""
    rows: list[dict] = []

    def add(section: str, what: str, h, st: Standardized, note: str = "") -> None:
        rows.append({
            "区分": section, "内容": what, "h": h,
            "n1": st.n1, "n2": st.n2,
            "mean_D1": _fmt(st.mean_d1), "mean_C(標準化)": _fmt(st.mean_c),
            "Δ_h": _fmt(st.delta),
            "MDE(参考。族の α に入らない)": "",
            "備考": note,
        })

    # (a) gap60_w24 の距離で標準化する
    if tab24 is not None:
        d1b, cb = tab24.d1_idx(), tab24.control_idx()
        e24 = band_edges(tab24.dist(d1b))
        for h in HORIZONS:
            st = standardize(tab24, d1b, cb,
                             col_liq=lambda t, i, h=h: t.r_liq(i, h),
                             col_ctl=lambda t, i, h=h: t.r_ctl(i, h),
                             edges=e24)
            add("(a)", "gap60_w24 の距離で標準化", h, st,
                note="走行 gap60_w24(距離の定義が 24 時間の VWAP)")
    else:
        rows.append({"区分": "(a)", "内容": "gap60_w24 の距離で標準化", "h": "",
                     "n1": "", "n2": "", "mean_D1": "", "mean_C(標準化)": "",
                     "Δ_h": "", "MDE(参考。族の α に入らない)": "",
                     "備考": "gap60_w24 の走行を渡していないので出していない"})

    d1, c = tab.d1_idx(), tab.control_idx()

    # (b) 帯を `dist_node_bp` で切る
    en = band_edges(tab.dist(d1, "dist_node_bp"))
    for h in HORIZONS:
        st = standardize(tab, d1, c,
                         col_liq=lambda t, i, h=h: t.r_liq(i, h),
                         col_ctl=lambda t, i, h=h: t.r_ctl(i, h),
                         dist_col="dist_node_bp", edges=en)
        add("(b)", "帯を |dist_node_bp| で切る", h, st,
            note="`d` の代わりに |dist_node_bp| の 10 分位")

    # (c) D_Q2 / D_Q3 / 全体
    lo, hi = tab.tertile_cuts()
    for name, li, ci in (
        ("D_Q2", tab.liq_idx_by_tertile(2), tab.control_idx(lo=lo, hi=hi)),
        ("D_Q3", tab.liq_idx_by_tertile(3), tab.control_idx(lo=hi, hi=None)),
        ("全体", tab.liq_i, tab.control_idx_all()),
    ):
        eg = band_edges(tab.dist(li))
        for h in HORIZONS:
            st = standardize(tab, li, ci,
                             col_liq=lambda t, i, h=h: t.r_liq(i, h),
                             col_ctl=lambda t, i, h=h: t.r_ctl(i, h),
                             edges=eg)
            add("(c)", f"{name} の同じ量", h, st,
                note=f"帯はこの群の |dist_vwap_bp| の 10 分位(3 分位の切り値 "
                     f"{_fmt(lo)} / {_fmt(hi)})")

    # (d) 帯ごとの平均は `bands.csv`。ここには**標準化する前の差**を出す
    #     (§4 の (d)「標準化する前の差(距離の交絡の有無を見る)」)。
    rows.append({"区分": "(d)", "内容": "帯ごとの平均(10 帯 × 6 h)", "h": "",
                 "n1": "", "n2": "", "mean_D1": "", "mean_C(標準化)": "", "Δ_h": "",
                 "MDE(参考。族の α に入らない)": "", "備考": f"{BANDS_NAME} に出す"})
    for h in HORIZONS:
        a = tab.r_liq(d1, h)
        b = tab.r_ctl(c, h)
        a, b = a[np.isfinite(a)], b[np.isfinite(b)]
        m1 = float(a.mean()) if a.size else float("nan")
        m2 = float(b.mean()) if b.size else float("nan")
        rows.append({
            "区分": "(d)", "内容": "標準化する前の差(帯で重み付けしない)", "h": h,
            "n1": int(a.size), "n2": int(b.size),
            "mean_D1": _fmt(m1), "mean_C(標準化)": _fmt(m2),
            "Δ_h": _fmt(m1 - m2), "MDE(参考。族の α に入らない)": "",
            "備考": "mean_C 欄は標準化していない生の平均。"
                    "判定の Δ_h(標準化した差)との開きが距離の交絡の大きさ",
        })

    # (e) 反転の割合(r_h < 0)の差
    edges = band_edges(tab.dist(d1))
    for h in HORIZONS:
        def _p_liq(t, i, h=h):
            v = t.r_liq(i, h)
            return np.where(np.isfinite(v), (v < 0).astype(float), np.nan)

        def _p_ctl(t, i, h=h):
            v = t.r_ctl(i, h)
            return np.where(np.isfinite(v), (v < 0).astype(float), np.nan)

        st = standardize(tab, d1, c, col_liq=_p_liq, col_ctl=_p_ctl, edges=edges)
        add("(e)", "反転の割合(r_h < 0)の差", h, st,
            note="帯は判定と同じ(D1 の |dist_vwap_bp| の 10 分位)")

    # (e′) 対照 C の `r_h` の平均と SE(§5 の仮定の確認)。**判定は変えない。**
    for h in HORIZONS:
        b = tab.r_ctl(c, h)
        b = b[np.isfinite(b)]
        m = float(b.mean()) if b.size else float("nan")
        se = float(b.std(ddof=1) / math.sqrt(b.size)) if b.size > 1 else float("nan")
        far = (math.isfinite(m) and math.isfinite(se) and se > 0
               and abs(m) >= Z_ALPHA * se)
        rows.append({
            "区分": "(e′)", "内容": "対照 C の r_h の平均 ± SE", "h": h,
            "n1": "", "n2": int(b.size),
            "mean_D1": "", "mean_C(標準化)": _fmt(m), "Δ_h": "",
            "MDE(参考。族の α に入らない)": "",
            "備考": (f"mean_C 欄は標準化していない生の平均 / SE {_fmt(se)} / "
                     + ("平均が 0 から z × SE 以上離れている"
                        "(対照の向きが流れを拾っている)"
                        if far else "0 から z × SE の中")),
        })
    return rows


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
        lines.append(f"{h}  {n}")
    (out / "MD5SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# =============================================================================
# --power(表を書かない)
# =============================================================================
def power_lines(sample: Table) -> list[str]:
    out = [
        f"単位: {UNIT}",
        f"多重性: {N_TESTS} 検定(1 周目 576 + この周 6) / α = 0.05/{N_TESTS} = {ALPHA:.8e}",
        f"z = norm.ppf(1 − α/2) = {Z_ALPHA:.10f}",
        f"MDE の係数 = z + {Z_POWER} = {MDE_Z:.10f}",
        f"件数(事前登録が凍結): n1 = {N1_PRE} / n2 = {N2_PRE}",
        f"標本: {sample.path}",
        "",
        "h    MDE(bp)   欲しい効果(bp)  欲しい効果 < MDE   標本の D1 行  標本の対照 C 行",
    ]
    for h in HORIZONS:
        m, na, nb = mde_from_sample(sample, h)
        want = WANTED.get(h)
        if want is None:
            w_s, cmp_s = "(事前登録に無い)", "—"
        else:
            w_s = f"{want:.1f}"
            cmp_s = "はい(走る前に外す)" if (math.isfinite(m) and want < m) else "いいえ"
        out.append(f"{h:<4} {m:<9.6f} {w_s:<14} {cmp_s:<18} {na:<12} {nb}")
    out += [
        "",
        "§7 の「式の近似の向き」の確認: 帯の重みを当てた実際の分散(標本の帯の n から)。",
        "  Var = s_D1²/n1 + (s_C²/n2) × F、F = Σ_k w_k²/c_k(w_k = 標本 D1 の帯の割合、",
        "  c_k = 標本の対照 C の帯の割合)。**F ≥ 1 なので上の表は MDE を楽観側に見る。**",
    ]
    for h in HORIZONS:
        m2, note, n_d1, n_c = mde_weighted_from_sample(sample, h)
        out.append(f"  h={h:<4} MDE(帯の重み) {m2:.6f}  {note}")
    m2, note, n_d1, n_c = mde_weighted_from_sample(sample, HORIZONS[0])
    out.append(f"  標本の帯ごとの件数 D1 {n_d1} / 対照 C {n_c}")
    return out


# =============================================================================
# 本体
# =============================================================================
def main(argv=None) -> int:
    repo = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(
        description="O-3c 段 A 2 周目(F1′)を事前登録どおりに読む"
    )
    ap.add_argument("--power", action="store_true",
                    help="z と h ごとの MDE を印字するだけ(表は書かない。関門も通さない)")
    ap.add_argument("--judge", action="store_true",
                    help="関門 → サニティ → 表(一度だけ)")
    ap.add_argument("--out-dir", default=None, help="--judge の出力先(既存なら止まる)")
    ap.add_argument("--table", default=str(repo / DEFAULT_TABLE),
                    help="主表の走行(gap60_w8)")
    ap.add_argument("--table-w24", default=str(repo / DEFAULT_TABLE_W24),
                    help="感度(観測のみ)の走行(gap60_w24)")
    ap.add_argument("--sample", default=str(repo / DEFAULT_SAMPLE),
                    help="標本 6 日(MDE の分散の出所)")
    ap.add_argument("--observation-only", default=str(repo / DEFAULT_OBS),
                    help="1 周目の観測のみの表(サニティ #2・#3 の突き合わせ先)")
    ap.add_argument("--root", default=str(repo),
                    help="監査の台帳(docs/AUDITOR/ACTION_LOG.md)の場所を差し替える(試験用)")
    a = ap.parse_args(argv)

    if a.power == a.judge:
        sys.stderr.write("--power か --judge のどちらか一方を指定する。\n")
        return 2

    if a.power:
        print("\n".join(power_lines(Table(a.sample))))
        return 0

    # ---- ここから --judge ---------------------------------------------------
    if not a.out_dir:
        sys.stderr.write("--judge には --out-dir が要る。\n")
        return 2
    out = Path(a.out_dir)
    if out.exists():
        sys.stderr.write(f"[止め] --out-dir が既にある({out})。判定は一度だけである。\n")
        return 1
    root = Path(a.root).resolve()
    bad_root = check_root_for_out_dir(out, root)
    if bad_root:
        sys.stderr.write("[止め] " + "\n".join(bad_root) + "\n")
        return 1

    # 1. 関門(§8 の #7)。**表を 1 枚も書く前**。
    pass_audit_gate(root)

    # 2. 読み込み
    tab = Table(a.table)
    sample = Table(a.sample)
    tab24 = Table(a.table_w24) if a.table_w24 and Path(a.table_w24).exists() else None

    # 3. 判定の 6 セル(表はまだ書かない)
    cells, bands, meta = build_cells(tab, sample)

    # 4. サニティ #1〜#6
    sanity, stop = run_sanity(tab, Path(a.observation_only), cells)
    if stop:
        # §8: 表は 1 枚も書かず、**破れた番号と検査の名前だけ**を `stopped.txt` に書く。
        # **値は 1 つも書かない**(1 周目の決定 12 と同じ。理由の全文は標準エラー出力へ)。
        sys.stderr.write("[止め] サニティが破れたので表を 1 枚も書かない:\n")
        for line in stop:
            sys.stderr.write(f"  - {line}\n")
        out.mkdir(parents=True, exist_ok=False)
        broken = [x for x in sanity if x["止める"]]
        (out / STOPPED_NAME).write_text(
            "サニティが破れたので表を 1 枚も書かなかった(事前登録 §8)。\n"
            + "".join(f"  - #{x['#']} {x['検査']}\n" for x in broken)
            + "理由の全文は走らせたときの標準エラー出力にある(値はここに書かない)。\n",
            encoding="utf-8")
        write_md5(out, [STOPPED_NAME])
        return 1

    # 5. 観測のみ
    obs_rows = build_observation_only(tab, tab24)

    # 6. 書き出し
    out.mkdir(parents=True, exist_ok=False)
    public_cells = [{k: v for k, v in x.items() if not k.startswith("_")} for x in cells]
    write_csv(out / CELLS_NAME, CELLS_HEADER, public_cells)
    write_csv(out / OBS_NAME, OBS_HEADER, obs_rows)
    write_csv(out / BANDS_NAME, BANDS_HEADER, bands)
    summary = {
        "単位": UNIT,
        "事前登録": PREREG_REL,
        "定数": {
            "切り値(D1)": CUT, "h": list(HORIZONS), "検定の数": N_TESTS,
            "α": ALPHA, "z": Z_ALPHA, "MDE の係数": MDE_Z, "検出力の z": Z_POWER,
            "n1(凍結)": N1_PRE, "n2(凍結)": N2_PRE,
            "帯の数": N_BANDS, "ブートストラップ": REPS, "種": SEED,
            "バー近傍の半幅": BAR_NEAR_HALFWIDTH,
        },
        "入力": {
            "主表": {"path": str(Path(a.table) / "table.csv"),
                     "md5": file_md5(Path(a.table) / "table.csv")},
            "標本": {"path": str(Path(a.sample) / "table.csv"),
                     "md5": file_md5(Path(a.sample) / "table.csv")},
            "感度(gap60_w24)": (
                {"path": str(Path(a.table_w24) / "table.csv"),
                 "md5": file_md5(Path(a.table_w24) / "table.csv")} if tab24 else None),
            "1 周目の観測のみ": str(a.observation_only),
        },
        "帯": meta,
        "サニティ": sanity,
        "F1′ の読み": f1_reading(cells),
        "有限な複製の本数": {str(x["h"]): x["_reps"] for x in cells},
        "帯ごとの最小件数": {str(x["h"]): {"D1": x["_min_n1"], "C": x["_min_n2"]}
                             for x in cells},
        "注": [
            "判定は一度だけ。この表を作り直さない。",
            "対照の r_h は `bp_{h}m` に相手の束の side の符号を当てたもの"
            "(SELL: −bp / BUY: +bp)。1 周目の読みの道具と同じ規則。",
            "SE は帯の中で行ごとに独立に再抽出するブートストラップ"
            "(1 周目の UTC 日クラスタではない。事前登録 §3)。",
            "観測のみの表(a)〜(e)は α にも判定にも入らない。",
        ],
    }
    (out / SUMMARY_NAME).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md5(out, [CELLS_NAME, OBS_NAME, BANDS_NAME, SUMMARY_NAME])
    print(f"書いた: {out}")
    for n in (CELLS_NAME, OBS_NAME, BANDS_NAME, SUMMARY_NAME, "MD5SUMS"):
        print(f"  - {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
