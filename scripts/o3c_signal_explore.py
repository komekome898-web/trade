#!/usr/bin/env python3
"""清算を起点とした値動きの予測可能性(SIGNAL)— **探索段**の読みの道具。

設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_DESIGN_2026-09-19.md`(§2 問い Q1〜Q3 /
§4 対照 / §5 設計の段の判定 / §6 データ / §7 決めたこと)。

**この道具がすること**
  - 1 周目の走行 6 本の表(`backtest_data/o3c_reaction_20260918_full/<run>/table.csv`)
    を**読むだけ**。新しい走行はしない。主 = `gap60_w8`、他 5 本は感度(Q3 の全体だけ)。
  - Q1(向き)= 反転の割合(`r_h < 0`)、Q2(大きさ)= 符号付き価格変化の平均 ± SE、
    Q3(時間軸)= h の並びでの平均 / mfe / mae / 反転の割合。
  - 対照 = 1 周目の対照 (ii)(`kind == control_matched` で相手が mixed でない行)。
  - 念のため |`dist_vwap_bp`| の 10 分位でそろえた差も併記する。

**探索段なので判定語(差あり / 検出されず / 陽性 / 陰性 / 有意)を 1 つも書かない。**
検定もしない。出すのは平均・SE・n・割合・単調性の語だけである。

**1 周目から引き継いだ規則(`scripts/o3c_reaction_r2.py` と同じ)**
  - 対照の `r_h` = `bp_{h}m` に**相手の束の side の符号**(SELL: −bp / BUY: +bp)。
    対照行の `*_reactdir` 列は side が無いので符号 +1 で入っている = そのまま使わない。
  - 対照の mfe / mae も同じ符号を当てる。生成側(`scripts/o3c_reaction.py`)が
    `mfe = max(up×sign, dn×sign)` / `mae = min(...)` で作っているので、符号 −1 では
    **入れ替わって符号が反転する**(mfe ← −mae、mae ← −mfe)。
  - 相手が `table_mixed.csv` の束である対照は落とす(1 周目の決定 8')。
  - 標準化(距離の 10 分位)は `o3c_reaction_r2.band_edges` / `band_index` /
    `Standardized` を**そのまま呼ぶ**(同じ値になることを試験で測る)。

**属性(Q2 の切り方)**
  - 分位は 3 分位。**切り値は清算行から作り、対照も同じ切り値で切る(own 方式)。**
  - 対照行に列が無い属性(`side` / `bundle_*` / `implied_leverage`)は
    **1 対 1 の相手の束の値**を当てる(符号付けと同じ「相手の束から採る」規則の延長)。
    設計はこの場合を書いていないので、報告の「未決」に出す。
  - `recent_volatility` は表に列が無いので作らない(未実装)。

**標準化した差の SE** は帯の重み w_k を固定した解析式
`sqrt(Σ_k w_k² (s1k²/n1k + s2k²/n2k))` である(2 周目の判定のブートストラップではない。
探索段なので反復を回さない)。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import o3c_reaction_r2 as r2  # noqa: E402  (標準化の式を使い回す)

NAN = float("nan")

HORIZONS = r2.HORIZONS                       # (1, 5, 15, 30, 60, 240)
KIND_LIQ = r2.KIND_LIQ
KIND_MAT = r2.KIND_MAT

MAIN_RUN = "gap60_w8"
SENSITIVITY_RUNS = ("gap60_w24", "gap30_w8", "gap30_w24", "gap180_w8", "gap180_w24")
ALL_RUNS = (MAIN_RUN,) + SENSITIVITY_RUNS
DEFAULT_RUNS_DIR = "backtest_data/o3c_reaction_20260918_full"

# 判定語。**出力に 1 つも出てはならない**(探索段)。
BANNED_WORDS = ("差あり", "検出されず", "陽性", "陰性", "有意")

# 出力の名前(設計 §6)
Q1_NAME = "q1_direction.csv"
Q2_NAME = "q2_size_by_attribute.csv"
Q3_NAME = "q3_horizon_shape.csv"
SENS_NAME = "sensitivity_q3.csv"
STD_NAME = "standardized_by_distance.csv"
SUMMARY_NAME = "summary.json"
TABLES_NAME = "tables.md"

# 単調性の語(設計 §2 Q2)
MONO_UP = "上がる"
MONO_DOWN = "下がる"
MONO_NONE = "単調でない"
MONO_UNKNOWN = "不明(平均が出ない群がある)"
MONO_NA = "(3 分位でない)"

# 時刻の帯(6 時間の 4 帯)
HOUR_BANDS = (("UTC 00–06", 0, 6), ("UTC 06–12", 6, 12),
              ("UTC 12–18", 12, 18), ("UTC 18–24", 18, 24))

# 属性(束の時点までに分かる列)。
#   name         : 表に出す名前
#   column       : 表の列名(abs=True なら絶対値を採る)
#   from_partner : 対照行に列が無いので 1 対 1 の相手の束から採る
ATTRS_NUM = [
    {"name": "|dist_vwap_bp|", "column": "dist_vwap_bp", "abs": True,
     "from_partner": False},
    {"name": "|dist_node_bp|", "column": "dist_node_bp", "abs": True,
     "from_partner": False},
    {"name": "bin_pct", "column": "bin_pct", "abs": False, "from_partner": False},
    {"name": "bundle_n_events_dedup", "column": "bundle_n_events_dedup",
     "abs": False, "from_partner": True},
    {"name": "bundle_total_notional", "column": "bundle_total_notional",
     "abs": False, "from_partner": True},
    {"name": "bundle_width_ms", "column": "bundle_width_ms", "abs": False,
     "from_partner": True},
    {"name": "doi_pre_1h", "column": "doi_pre_1h", "abs": False,
     "from_partner": False},
    {"name": "implied_leverage", "column": "implied_leverage", "abs": False,
     "from_partner": True},
]
ATTR_SIDE = "side"
ATTR_HOUR = "time_of_day(UTC 時、6 時間の 4 帯)"

# 表に列が無いので作らなかったもの
NOT_IN_TABLE = ["recent_volatility"]


# =============================================================================
# 小道具
# =============================================================================
def _f(x) -> float:
    return r2._f(x)


def _fmt(x, nd: int = 6) -> str:
    return r2._fmt(x, nd)


def mean_se(v: np.ndarray) -> tuple[int, float, float]:
    """有限な値の件数・平均・平均の SE(s/√n)。"""
    v = v[np.isfinite(v)]
    n = int(v.size)
    if n == 0:
        return 0, NAN, NAN
    m = float(v.mean())
    se = float(v.std(ddof=1) / math.sqrt(n)) if n > 1 else NAN
    return n, m, se


def prop_neg_se(v: np.ndarray) -> tuple[int, float, float]:
    """反転の割合(`r_h < 0`)と二項の SE(√(p(1−p)/n))。"""
    v = v[np.isfinite(v)]
    n = int(v.size)
    if n == 0:
        return 0, NAN, NAN
    p = float((v < 0).mean())
    return n, p, math.sqrt(p * (1.0 - p) / n)


def diff_se(se1: float, se2: float) -> float:
    if not (math.isfinite(se1) and math.isfinite(se2)):
        return NAN
    return math.sqrt(se1 * se1 + se2 * se2)


def tertile_cuts(v: np.ndarray) -> tuple[float, float]:
    """3 分位の切り値(`o3c_reaction_r2.Table.tertile_cuts` と同じ作り)。"""
    fin = v[np.isfinite(v)]
    if fin.size == 0:
        return NAN, NAN
    lo, hi = np.nanpercentile(fin, [100.0 / 3.0, 200.0 / 3.0])
    return float(lo), float(hi)


def tertile_mask(v: np.ndarray, lo: float, hi: float, q: int) -> np.ndarray:
    """own 方式: 切り値は清算行から作り、対照にも同じ切り値を当てる。"""
    if not (math.isfinite(lo) and math.isfinite(hi)):
        return np.zeros(v.size, dtype=bool)
    if q == 1:
        sel = v <= lo
    elif q == 2:
        sel = (v > lo) & (v <= hi)
    else:
        sel = v > hi
    return sel & np.isfinite(v)


def monotone_word(means: list[float]) -> str:
    """3 分位の平均が単調か(設計 §2 Q2 の語)。"""
    if len(means) != 3 or not all(math.isfinite(m) for m in means):
        return MONO_UNKNOWN
    a, b, c = means
    if a < b < c:
        return MONO_UP
    if a > b > c:
        return MONO_DOWN
    return MONO_NONE


def standardized_diff(v1: np.ndarray, d1: np.ndarray,
                      v2: np.ndarray, d2: np.ndarray,
                      edges: list[float] | None = None):
    """|dist_vwap_bp| の 10 分位でそろえた差。

    点推定は `o3c_reaction_r2.Standardized`(= `standardize` の中身)そのもの。
    SE は帯の重み w_k を固定した解析式(探索段なのでブートストラップは回さない)。
    返り値: (Standardized, SE, 帯の境界)
    """
    if edges is None:
        edges = r2.band_edges(d1)
    b1 = r2.band_index(d1, edges)
    b2 = r2.band_index(d2, edges)
    st = r2.Standardized(v1, b1, v2, b2, edges)
    var = 0.0
    ok = True
    for k in range(r2.N_BANDS):
        a, b = st.parts1[k], st.parts2[k]
        w = float(st.w[k]) if st.w.size else NAN
        if a.size < 2 or b.size < 2 or not math.isfinite(w):
            ok = False
            break
        var += w * w * (float(a.var(ddof=1)) / a.size + float(b.var(ddof=1)) / b.size)
    se = math.sqrt(var) if ok and math.isfinite(var) else NAN
    return st, se, edges


# =============================================================================
# 走行の表
# =============================================================================
def needed_columns(full: bool) -> set[str]:
    cols = {"kind", "cascade_id", "matched_liq_id", "side"}
    for h in HORIZONS:
        cols.add(f"bp_{h}m")
        cols.add(f"bp_{h}m_reactdir")
        cols.add(f"mfe_{h}m_reactdir")
        cols.add(f"mae_{h}m_reactdir")
    if full:
        cols.add("time_ms")
        for a in ATTRS_NUM:
            cols.add(a["column"])
    return cols


class Run:
    """1 走行の表を、清算行と対照行の 2 つの束に開いたもの。

    清算行 = `kind == liq`(混在の束は `table_mixed.csv` 側にあり、この表に入らない)。
    対照行 = `kind == control_matched` で相手が mixed でないもの(1 周目の対照 (ii))。
    """

    def __init__(self, path: Path | str, *, full: bool = True):
        self.path = Path(path)
        self.full = full
        want = needed_columns(full)
        cols = r2._read_cols(self.path / "table.csv", want)
        self.header_missing = sorted(want - set(cols))

        mixed_p = self.path / "table_mixed.csv"
        if mixed_p.exists():
            m = r2._read_cols(mixed_p, {"cascade_id"})
        else:
            m = {"cascade_id": []}
        self.mixed_ids = set(m.get("cascade_id", []))

        kind = np.array(cols["kind"], dtype=object)
        liq_i = np.flatnonzero(kind == KIND_LIQ)
        mat_i = np.flatnonzero(kind == KIND_MAT)
        self.n_liq_rows = int(liq_i.size)
        self.n_mat_rows = int(mat_i.size)

        cid = cols["cascade_id"]
        pos_by_id = {cid[i]: p for p, i in enumerate(liq_i)}
        partner = [cols["matched_liq_id"][i] for i in mat_i]
        partner_mixed = np.array([p in self.mixed_ids for p in partner], dtype=bool)
        keep = ~partner_mixed if partner_mixed.size else np.zeros(0, dtype=bool)
        self.n_mat_dropped_mixed = int(np.sum(partner_mixed))

        self.liq_i = liq_i
        self.ctl_i = mat_i[keep] if mat_i.size else mat_i
        partner_keep = [p for p, k in zip(partner, keep) if k]
        self.partner_pos = np.array([pos_by_id.get(p, -1) for p in partner_keep],
                                    dtype=int)
        self.n_partner_missing = int(np.sum(self.partner_pos < 0))

        self._cols = cols
        # -- 清算行の side と、対照行に当てる相手の side の符号 -----------------
        self.liq_side = np.array([cols["side"][i] for i in liq_i], dtype=object)
        sgn = np.full(self.partner_pos.size, NAN)
        pside = np.empty(self.partner_pos.size, dtype=object)
        pside[:] = None
        for j, p in enumerate(self.partner_pos):
            if p < 0:
                continue
            s = self.liq_side[p]
            pside[j] = s
            sgn[j] = -1.0 if s == "SELL" else 1.0
        self.ctl_partner_side = pside
        self.ctl_sign = sgn

        # -- 量 ---------------------------------------------------------------
        self.r_liq: dict[int, np.ndarray] = {}
        self.r_ctl: dict[int, np.ndarray] = {}
        self.mfe_liq: dict[int, np.ndarray] = {}
        self.mae_liq: dict[int, np.ndarray] = {}
        self.mfe_ctl: dict[int, np.ndarray] = {}
        self.mae_ctl: dict[int, np.ndarray] = {}
        flip = sgn < 0
        nan_sign = ~np.isfinite(sgn)
        for h in HORIZONS:
            self.r_liq[h] = self._num(liq_i, f"bp_{h}m_reactdir")
            self.mfe_liq[h] = self._num(liq_i, f"mfe_{h}m_reactdir")
            self.mae_liq[h] = self._num(liq_i, f"mae_{h}m_reactdir")
            raw = self._num(self.ctl_i, f"bp_{h}m")
            self.r_ctl[h] = raw * sgn
            # 生成側は mfe = max(up×sign, dn×sign) / mae = min(...)。
            # 対照行は sign = +1 で入っているので、相手が SELL(−1)なら入れ替えて反転する。
            mfe0 = self._num(self.ctl_i, f"mfe_{h}m_reactdir")
            mae0 = self._num(self.ctl_i, f"mae_{h}m_reactdir")
            self.mfe_ctl[h] = np.where(nan_sign, NAN, np.where(flip, -mae0, mfe0))
            self.mae_ctl[h] = np.where(nan_sign, NAN, np.where(flip, -mfe0, mae0))

        if not full:
            return

        # -- 属性 --------------------------------------------------------------
        self.attr_liq: dict[str, np.ndarray] = {}
        self.attr_ctl: dict[str, np.ndarray] = {}
        for a in ATTRS_NUM:
            vl = self._num(liq_i, a["column"])
            if a["abs"]:
                vl = np.abs(vl)
            self.attr_liq[a["name"]] = vl
            if a["from_partner"]:
                take = np.clip(self.partner_pos, 0, None)
                vc = np.where(self.partner_pos >= 0,
                              vl[take] if vl.size else NAN, NAN)
            else:
                vc = self._num(self.ctl_i, a["column"])
                if a["abs"]:
                    vc = np.abs(vc)
            self.attr_ctl[a["name"]] = vc

        # side(対照は相手の束の side)
        self.side_liq = self.liq_side
        self.side_ctl = self.ctl_partner_side
        # 時刻(その行自身の time_ms の UTC 時)
        self.hour_liq = self._hour(self._num(liq_i, "time_ms"))
        self.hour_ctl = self._hour(self._num(self.ctl_i, "time_ms"))
        # 距離(標準化の帯)
        self.dist_liq = np.abs(self._num(liq_i, "dist_vwap_bp"))
        self.dist_ctl = np.abs(self._num(self.ctl_i, "dist_vwap_bp"))

    # ---------------------------------------------------------------------
    @staticmethod
    def _hour(t_ms: np.ndarray) -> np.ndarray:
        out = np.full(t_ms.size, NAN)
        fin = np.isfinite(t_ms)
        out[fin] = (t_ms[fin] // 3_600_000) % 24
        return out

    def _num(self, idx: np.ndarray, col: str) -> np.ndarray:
        src = self._cols.get(col)
        if src is None:
            return np.full(idx.size, NAN)
        return np.array([_f(src[i]) for i in idx], dtype=float)

    # -- 欠測 --------------------------------------------------------------
    def missing_counts(self) -> dict:
        out: dict[str, dict] = {"清算行": {}, "対照行": {}}
        for h in HORIZONS:
            out["清算行"][f"bp_{h}m_reactdir"] = int(
                np.sum(~np.isfinite(self.r_liq[h])))
            out["清算行"][f"mfe_{h}m_reactdir"] = int(
                np.sum(~np.isfinite(self.mfe_liq[h])))
            out["清算行"][f"mae_{h}m_reactdir"] = int(
                np.sum(~np.isfinite(self.mae_liq[h])))
            out["対照行"][f"r_{h}(bp × 相手の符号)"] = int(
                np.sum(~np.isfinite(self.r_ctl[h])))
            out["対照行"][f"mfe_{h}(相手の符号)"] = int(
                np.sum(~np.isfinite(self.mfe_ctl[h])))
            out["対照行"][f"mae_{h}(相手の符号)"] = int(
                np.sum(~np.isfinite(self.mae_ctl[h])))
        if self.full:
            for a in ATTRS_NUM:
                out["清算行"][a["name"]] = int(
                    np.sum(~np.isfinite(self.attr_liq[a["name"]])))
                key = a["name"] + ("(相手の束から)" if a["from_partner"] else "")
                out["対照行"][key] = int(np.sum(~np.isfinite(self.attr_ctl[a["name"]])))
            out["清算行"]["side"] = int(
                sum(1 for s in self.side_liq if s in (None, "")))
            out["対照行"]["side(相手の束から)"] = int(
                sum(1 for s in self.side_ctl if s in (None, "")))
            out["清算行"]["time_of_day"] = int(np.sum(~np.isfinite(self.hour_liq)))
            out["対照行"]["time_of_day"] = int(np.sum(~np.isfinite(self.hour_ctl)))
            out["清算行"]["|dist_vwap_bp|"] = int(np.sum(~np.isfinite(self.dist_liq)))
            out["対照行"]["|dist_vwap_bp|"] = int(np.sum(~np.isfinite(self.dist_ctl)))
        return out


# =============================================================================
# 群の切り方
# =============================================================================
TERTILE_LABELS = ((1, "Q1(下位 3 分位)"), (2, "Q2(中位 3 分位)"),
                  (3, "Q3(上位 3 分位)"))


def attribute_groups(run: Run) -> list[dict]:
    """[{属性, 群, 下限, 上限, mask_liq, mask_ctl, 3分位}] を並べる。"""
    groups: list[dict] = []
    for a in ATTRS_NUM:
        name = a["name"]
        vl = run.attr_liq[name]
        vc = run.attr_ctl[name]
        lo, hi = tertile_cuts(vl)
        bounds = {1: (NAN, lo), 2: (lo, hi), 3: (hi, NAN)}
        for q, label in TERTILE_LABELS:
            groups.append({
                "属性": name, "群": label, "順": q,
                "下限": bounds[q][0], "上限": bounds[q][1],
                "mask_liq": tertile_mask(vl, lo, hi, q),
                "mask_ctl": tertile_mask(vc, lo, hi, q),
                "3分位": True,
                "相手の束から": bool(a["from_partner"]),
            })
    for i, s in enumerate(("SELL", "BUY"), start=1):
        groups.append({
            "属性": ATTR_SIDE, "群": s, "順": i, "下限": NAN, "上限": NAN,
            "mask_liq": np.array([x == s for x in run.side_liq], dtype=bool),
            "mask_ctl": np.array([x == s for x in run.side_ctl], dtype=bool),
            "3分位": False, "相手の束から": True,
        })
    for i, (label, a0, a1) in enumerate(HOUR_BANDS, start=1):
        groups.append({
            "属性": ATTR_HOUR, "群": label, "順": i,
            "下限": float(a0), "上限": float(a1),
            "mask_liq": (run.hour_liq >= a0) & (run.hour_liq < a1),
            "mask_ctl": (run.hour_ctl >= a0) & (run.hour_ctl < a1),
            "3分位": False, "相手の束から": False,
        })
    return groups


def overall_group(run: Run) -> dict:
    return {"属性": "全体", "群": "全体", "順": 1, "下限": NAN, "上限": NAN,
            "mask_liq": np.ones(run.liq_i.size, dtype=bool),
            "mask_ctl": np.ones(run.ctl_i.size, dtype=bool),
            "3分位": False, "相手の束から": False}


def d1_group(run: Run) -> dict:
    """D1 相当 = `doi_pre_1h` の下位 3 分位(切り値は清算行から。own 方式)。"""
    vl = run.attr_liq["doi_pre_1h"]
    vc = run.attr_ctl["doi_pre_1h"]
    lo, hi = tertile_cuts(vl)
    return {"属性": "D1 相当(doi_pre_1h の下位 3 分位)", "群": "Q1(下位 3 分位)",
            "順": 1, "下限": NAN, "上限": lo,
            "mask_liq": tertile_mask(vl, lo, hi, 1),
            "mask_ctl": tertile_mask(vc, lo, hi, 1),
            "3分位": True, "相手の束から": False}


# =============================================================================
# Q1 / Q2 / Q3 / 標準化
# =============================================================================
Q1_HEADER = ["属性", "群", "h", "n(清算)", "反転の割合(清算)", "SE(清算)",
             "n(対照)", "反転の割合(対照)", "SE(対照)", "差(清算 − 対照)", "SE(差)"]


def build_q1(run: Run, groups: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for g in groups:
        for h in HORIZONS:
            n1, p1, s1 = prop_neg_se(run.r_liq[h][g["mask_liq"]])
            n2, p2, s2 = prop_neg_se(run.r_ctl[h][g["mask_ctl"]])
            d = p1 - p2 if (math.isfinite(p1) and math.isfinite(p2)) else NAN
            rows.append({
                "属性": g["属性"], "群": g["群"], "h": h,
                "n(清算)": n1, "反転の割合(清算)": _fmt(p1), "SE(清算)": _fmt(s1),
                "n(対照)": n2, "反転の割合(対照)": _fmt(p2), "SE(対照)": _fmt(s2),
                "差(清算 − 対照)": _fmt(d), "SE(差)": _fmt(diff_se(s1, s2)),
            })
    return rows


Q2_HEADER = ["属性", "群", "群の下限", "群の上限", "対照の属性の出所", "h",
             "n(清算)", "平均bp(清算)", "SE(清算)",
             "n(対照)", "平均bp(対照)", "SE(対照)",
             "差(清算 − 対照)", "SE(差)", "単調性(清算の平均)", "単調性(差)"]


def build_q2(run: Run, groups: list[dict]) -> list[dict]:
    raw: list[dict] = []
    for g in groups:
        for h in HORIZONS:
            n1, m1, s1 = mean_se(run.r_liq[h][g["mask_liq"]])
            n2, m2, s2 = mean_se(run.r_ctl[h][g["mask_ctl"]])
            d = m1 - m2 if (math.isfinite(m1) and math.isfinite(m2)) else NAN
            raw.append({"g": g, "h": h, "n1": n1, "m1": m1, "s1": s1,
                        "n2": n2, "m2": m2, "s2": s2, "d": d})
    # 単調性は (属性, h) ごとに 3 分位の並び(Q1 → Q2 → Q3)から作る
    mono_mean: dict[tuple[str, int], str] = {}
    mono_diff: dict[tuple[str, int], str] = {}
    for x in raw:
        g = x["g"]
        if not g["3分位"]:
            continue
        key = (g["属性"], x["h"])
        if key in mono_mean:
            continue
        got = sorted([y for y in raw
                      if y["g"]["属性"] == key[0] and y["h"] == key[1]],
                     key=lambda y: y["g"]["順"])
        mono_mean[key] = monotone_word([y["m1"] for y in got])
        mono_diff[key] = monotone_word([y["d"] for y in got])
    rows: list[dict] = []
    for x in raw:
        g = x["g"]
        key = (g["属性"], x["h"])
        rows.append({
            "属性": g["属性"], "群": g["群"],
            "群の下限": _fmt(g["下限"]), "群の上限": _fmt(g["上限"]),
            "対照の属性の出所": "相手の束" if g["相手の束から"] else "その行自身",
            "h": x["h"],
            "n(清算)": x["n1"], "平均bp(清算)": _fmt(x["m1"]), "SE(清算)": _fmt(x["s1"]),
            "n(対照)": x["n2"], "平均bp(対照)": _fmt(x["m2"]), "SE(対照)": _fmt(x["s2"]),
            "差(清算 − 対照)": _fmt(x["d"]), "SE(差)": _fmt(diff_se(x["s1"], x["s2"])),
            "単調性(清算の平均)": mono_mean.get(key, MONO_NA),
            "単調性(差)": mono_diff.get(key, MONO_NA),
        })
    return rows


Q3_HEADER = ["走行", "群", "区分", "h", "n", "平均bp", "SE(平均)",
             "mfe平均", "SE(mfe)", "mae平均", "SE(mae)",
             "反転の割合", "SE(反転の割合)"]


def build_q3(run: Run, groups: list[dict], run_name: str) -> list[dict]:
    rows: list[dict] = []
    for g in groups:
        for kind, mask, rv, mfe, mae in (
            ("清算", g["mask_liq"], run.r_liq, run.mfe_liq, run.mae_liq),
            ("対照", g["mask_ctl"], run.r_ctl, run.mfe_ctl, run.mae_ctl),
        ):
            for h in HORIZONS:
                n, m, se = mean_se(rv[h][mask])
                _nf, mf, sf = mean_se(mfe[h][mask])
                _na, ma, sa = mean_se(mae[h][mask])
                _, p, sp = prop_neg_se(rv[h][mask])
                rows.append({
                    "走行": run_name, "群": g["属性"], "区分": kind, "h": h,
                    "n": n, "平均bp": _fmt(m), "SE(平均)": _fmt(se),
                    "mfe平均": _fmt(mf), "SE(mfe)": _fmt(sf),
                    "mae平均": _fmt(ma), "SE(mae)": _fmt(sa),
                    "反転の割合": _fmt(p), "SE(反転の割合)": _fmt(sp),
                })
    return rows


STD_HEADER = ["属性", "群", "h", "n(清算)", "n(対照)", "平均bp(清算)",
              "平均bp(対照。距離でそろえた)", "差(距離でそろえた)", "SE(差)",
              "帯の最小n(清算)", "帯の最小n(対照)"]


def build_standardized(run: Run, groups: list[dict]) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    edges_used: dict[str, list[float]] = {}
    for g in groups:
        d1 = run.dist_liq[g["mask_liq"]]
        d2 = run.dist_ctl[g["mask_ctl"]]
        edges = r2.band_edges(d1)
        edges_used[f'{g["属性"]} / {g["群"]}'] = [float(x) for x in edges]
        for h in HORIZONS:
            st, se, _ = standardized_diff(
                run.r_liq[h][g["mask_liq"]], d1,
                run.r_ctl[h][g["mask_ctl"]], d2, edges=edges)
            rows.append({
                "属性": g["属性"], "群": g["群"], "h": h,
                "n(清算)": st.n1, "n(対照)": st.n2,
                "平均bp(清算)": _fmt(st.mean_d1),
                "平均bp(対照。距離でそろえた)": _fmt(st.mean_c),
                "差(距離でそろえた)": _fmt(st.delta), "SE(差)": _fmt(se),
                "帯の最小n(清算)": st.min_n1, "帯の最小n(対照)": st.min_n2,
            })
    return rows, edges_used


# =============================================================================
# 書き出し
# =============================================================================
def md_table(header: list[str], rows: list[dict]) -> str:
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join("---" for _ in header) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(k, "")) for k in header) + " |")
    return "\n".join(out)


def build_tables_md(blocks, note: str) -> str:
    parts = ["# 清算を起点とした値動きの予測可能性 — 探索段の表(2026-09-19)",
             "", note, ""]
    for title, header, rows in blocks:
        parts += [f"## {title}", "", md_table(header, rows), ""]
    return "\n".join(parts) + "\n"


def check_banned(text: str, where: str) -> None:
    hit = [w for w in BANNED_WORDS if w in text]
    if hit:
        raise SystemExit(f"[止め] {where} に段に合わない語が入っている: {hit}")


def verify_inputs(run_dir: Path) -> dict:
    """出力を書く前に、入力の MD5 を走行の `MD5SUMS` と照合する。"""
    md5_path = run_dir / "MD5SUMS"
    if not md5_path.exists():
        raise SystemExit(f"[止め] {md5_path} が無いので入力を照合できない。")
    want: dict[str, str] = {}
    for line in md5_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        h, _, name = line.partition("  ")
        want[name.strip()] = h.strip()
    got: dict[str, str] = {}
    for name in ("table.csv", "table_mixed.csv"):
        p = run_dir / name
        if not p.exists():
            raise SystemExit(f"[止め] {p} が無い。")
        if name not in want:
            raise SystemExit(f"[止め] {md5_path} に {name} の行が無い。")
        got[name] = r2.file_md5(p)
        if want[name] != got[name]:
            raise SystemExit(
                f"[止め] {p} の MD5 が台帳と食い違う"
                f"(台帳 {want[name]} / 実物 {got[name]})。")
    return got


# =============================================================================
# 本体
# =============================================================================
def run_all(runs_dir: Path, out: Path) -> int:
    if out.exists():
        sys.stderr.write(f"[止め] --out-dir が既にある({out})。\n")
        return 1

    md5s = {name: verify_inputs(runs_dir / name) for name in ALL_RUNS}

    main_run = Run(runs_dir / MAIN_RUN, full=True)
    groups = attribute_groups(main_run)
    over = overall_group(main_run)
    d1 = d1_group(main_run)

    q1 = build_q1(main_run, [over] + groups)
    q2 = build_q2(main_run, groups)
    q3 = build_q3(main_run, [over, d1], MAIN_RUN)
    std_rows, edges_used = build_standardized(main_run, [over] + groups)

    sens: list[dict] = []
    sens_meta: dict[str, dict] = {}
    for name in SENSITIVITY_RUNS:
        rn = Run(runs_dir / name, full=False)
        sens += build_q3(rn, [overall_group(rn)], name)
        sens_meta[name] = {
            "清算行": rn.n_liq_rows,
            "対照行(mixed を除く前)": rn.n_mat_rows,
            "相手が mixed で落とした対照行": rn.n_mat_dropped_mixed,
            "対照行(使った)": int(rn.ctl_i.size),
            "相手が引けなかった対照行": rn.n_partner_missing,
            "欠測": rn.missing_counts(),
        }

    note = ("この表は**探索段**の観測である(設計 §6)。検定はしておらず、判定の語は"
            "どこにも書いていない。平均は bp、SE は平均の標準誤差、n は有限な値の件数"
            "である。対照は 1 周目の対照 (ii)(相手が混在の束の行は落とす)で、値は "
            "`bp_{h}m` に相手の束の side の符号(SELL: −bp / BUY: +bp)を当てたもの"
            "である。反転の割合は `r_h < 0` の割合。")
    blocks = [
        ("Q1 向き(反転の割合 = r_h < 0)", Q1_HEADER, q1),
        ("Q2 大きさ(属性 × h の符号付き価格変化)", Q2_HEADER, q2),
        ("Q3 時間軸(h の形)", Q3_HEADER, q3),
        ("感度(他 5 本の走行の Q3 全体)", Q3_HEADER, sens),
        ("|dist_vwap_bp| の 10 分位でそろえた差", STD_HEADER, std_rows),
    ]
    tables_md = build_tables_md(blocks, note)
    check_banned(tables_md, TABLES_NAME)

    lo_doi, _hi_doi = tertile_cuts(main_run.attr_liq["doi_pre_1h"])
    bounds = {}
    for a in ATTRS_NUM:
        lo, hi = tertile_cuts(main_run.attr_liq[a["name"]])
        bounds[a["name"]] = {"下位/中位の境界": lo, "中位/上位の境界": hi}
    summary = {
        "単位": "o3c_signal_explore_20260919",
        "段": "探索段(判定ではない。判定の語を書かない)",
        "設計": "docs/PHASE2/O3C/SIGNAL/SIGNAL_DESIGN_2026-09-19.md",
        "h": list(HORIZONS),
        "主の走行": MAIN_RUN,
        "感度の走行": list(SENSITIVITY_RUNS),
        "入力の MD5": md5s,
        "件数(主の走行)": {
            "清算行": main_run.n_liq_rows,
            "対照行(mixed を除く前)": main_run.n_mat_rows,
            "相手が mixed で落とした対照行": main_run.n_mat_dropped_mixed,
            "対照行(使った)": int(main_run.ctl_i.size),
            "相手が引けなかった対照行": main_run.n_partner_missing,
        },
        "件数(感度の走行)": sens_meta,
        "欠測(主の走行)": main_run.missing_counts(),
        "3 分位の境界(清算行から。own 方式)": bounds,
        "D1 相当の上限(doi_pre_1h の下位 3 分位)": lo_doi,
        "時刻の帯": [{"名": n, "下限(UTC 時)": a, "上限(UTC 時)": b}
                     for n, a, b in HOUR_BANDS],
        "標準化の帯の境界(群ごと)": edges_used,
        "表に列が無いので作らなかった属性": NOT_IN_TABLE,
        "注": [
            "対照行に列が無い属性(side / bundle_* / implied_leverage)は "
            "1 対 1 の相手の束の値を当てた(設計はこの場合を書いていない = 未決)。",
            "対照の mfe / mae は相手の符号が −1 のとき入れ替えて反転させた"
            "(生成側が mfe = max(up×sign, dn×sign) で作っているため)。",
            "標準化の点推定は scripts/o3c_reaction_r2.py の Standardized そのもの。"
            "SE は帯の重みを固定した解析式で、2 周目の判定のブートストラップではない。",
            "検定はしていない。SE は表に添えた散らばりであって、判定の道具ではない。",
        ],
    }

    out.mkdir(parents=True, exist_ok=False)
    r2.write_csv(out / Q1_NAME, Q1_HEADER, q1)
    r2.write_csv(out / Q2_NAME, Q2_HEADER, q2)
    r2.write_csv(out / Q3_NAME, Q3_HEADER, q3)
    r2.write_csv(out / SENS_NAME, Q3_HEADER, sens)
    r2.write_csv(out / STD_NAME, STD_HEADER, std_rows)
    (out / SUMMARY_NAME).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")
    (out / TABLES_NAME).write_text(tables_md, encoding="utf-8")
    r2.write_md5(out, [Q1_NAME, Q2_NAME, Q3_NAME, SENS_NAME, STD_NAME,
                       SUMMARY_NAME, TABLES_NAME])

    print(f"書いた: {out}")
    for n in (Q1_NAME, Q2_NAME, Q3_NAME, SENS_NAME, STD_NAME, SUMMARY_NAME,
              TABLES_NAME, "MD5SUMS"):
        print(f"  - {n}  ({(out / n).stat().st_size} バイト)")
    return 0


def main(argv=None) -> int:
    repo = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(
        description="清算を起点とした値動きの予測可能性(探索段。1 周目の表を読むだけ)")
    ap.add_argument("--runs-dir", default=str(repo / DEFAULT_RUNS_DIR),
                    help="1 周目の走行 6 本が入った場所")
    ap.add_argument("--out-dir", required=True, help="出力先(既にあれば止まる)")
    a = ap.parse_args(argv)
    return run_all(Path(a.runs_dir), Path(a.out_dir))


if __name__ == "__main__":
    raise SystemExit(main())
