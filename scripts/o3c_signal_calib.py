#!/usr/bin/env python3
"""§7.5「較正の良い方」を判定する道具(設計 §7.5.1、反証者レビュー7 D2 の直し)。

設計 §7.5(段2): 「良い」= 0.05 刻みの帯で |実際の割合 − 帯の中央| の件数重み平均が
小さい方。同点(差 0.01 以内)なら遅延の短い code。設計 §7.5.1(D2 の直し)で、
帯の起点と少数帯の扱いを後半を見る前に固定した:

  - 帯は `[0,0.05) … [0.95,1.0]` の固定 20 本(起点 0、幅 0.05、最後の帯だけ両端
    閉区間で 1.0 を含む)。
  - 件数 20 未満の帯は平均から外す(外した帯を表に書く)。
  - 値 = Σ n_b × |実際の割合_b − 帯の中央_b| / Σ n_b(使った帯だけの重み付き平均)。
  - 同点(差 0.01 以内)は「code」を返す(§7.5 の規則そのまま)。

委任文: `docs/DATA/delegations/20260921_o3c_signal_refuter7_prompt.md`(反証者7 直し)
設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md` §7.5・§7.5.1
反証者: `docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW7_2026-09-20.md` D2

**探索段なので判定語を 1 つも書かない。`paper_logs/` は開かない。**
"""
from __future__ import annotations

import numpy as np

NAN = float("nan")

N_BINS = 20
BIN_WIDTH = 1.0 / N_BINS
MIN_COUNT = 20          # 設計 §7.5.1「件数 20 未満の帯は平均から外す」
TIE_EPS = 0.01          # 設計 §7.5「同点(差 0.01 以内)」

BIN_EDGES = np.linspace(0.0, 1.0, N_BINS + 1)          # 21 点 = 20 本
BIN_CENTERS = (BIN_EDGES[:-1] + BIN_EDGES[1:]) / 2.0


def _bin_index(prob: np.ndarray) -> np.ndarray:
    """`[0,0.05) … [0.90,0.95)` は左閉右開、最後の `[0.95,1.0]` だけ両端閉区間。
    `prob / BIN_WIDTH` の浮動小数の丸め(例: 0.95/0.05 が 18.999999999999996 に
    なる)で境界の値が 1 本下の帯に落ちないよう、小さな余裕(1e-9)を足してから
    `floor` する。[0,1] の外の値(データの誤りでなければ起きないはず)は端の帯に
    丸める。"""
    idx = np.floor(np.asarray(prob, dtype=float) * N_BINS + 1e-9).astype(int)
    return np.clip(idx, 0, N_BINS - 1)


def calibration_goodness(prob: np.ndarray, y: np.ndarray,
                         min_count: int = MIN_COUNT) -> dict:
    """設計 §7.5・§7.5.1 の較正の良さ(小さいほど良い)。

    戻り値: {"値": float, "使った帯": [...], "外した帯": [...], "帯ごと": [...]}
    「使った帯」「外した帯」はそれぞれ {"帯": b, "範囲": (lo,hi), "件数": n,
    "実際の割合": actual, "帯の中央": center} の辞書のリスト。件数 0 の帯は
    「帯ごと」にも出さない(存在しない帯として扱う)。
    """
    prob = np.asarray(prob, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(prob) & np.isfinite(y)
    prob, y = prob[ok], y[ok]
    idx = _bin_index(prob) if prob.size else np.array([], dtype=int)

    used: list = []
    excluded: list = []
    all_bins: list = []
    w_sum = 0.0
    err_sum = 0.0
    for b in range(N_BINS):
        mask = idx == b
        n_b = int(mask.sum())
        if n_b == 0:
            continue
        actual = float(y[mask].mean())
        center = float(BIN_CENTERS[b])
        row = {"帯": b, "範囲": (float(BIN_EDGES[b]), float(BIN_EDGES[b + 1])),
              "件数": n_b, "実際の割合": actual, "帯の中央": center}
        all_bins.append(row)
        if n_b < min_count:
            excluded.append(row)
            continue
        used.append(row)
        w_sum += n_b
        err_sum += n_b * abs(actual - center)

    value = (err_sum / w_sum) if w_sum > 0 else NAN
    return {"値": value, "使った帯": used, "外した帯": excluded, "帯ごと": all_bins}


def choose_better(jev_goodness: dict, code_goodness: dict,
                  tie_eps: float = TIE_EPS) -> str:
    """設計 §7.5「較正の良い方を方策の模擬に使う」。値が小さい方を返す
    (`"jev"` / `"code"`)。差が `tie_eps`(0.01)以内の同点、またはどちらかの値が
    無い(NaN、使える帯が無い)ときは `"code"`(設計「同点なら遅延の短い code」)。"""
    vj, vc = jev_goodness["値"], code_goodness["値"]
    if not (vj == vj) or not (vc == vc):
        return "code"
    if vj < vc - tie_eps:
        return "jev"
    return "code"
