#!/usr/bin/env python3
"""高ボラの門の問い 4(値動き以外の量で荒れた日を前もって当てる)の日の版: Binance の資金調達率。

L-608 の一覧の 8、`c2_owner_xvenue_wick/vol_gate/DESIGN.md` の問い 4(資金調達率は問い 1・2 で測らず問い 4 に回した)。
読み方の決まり(表を見る前に、この台本と `tests/research/test_vol_q4_funding.py` で固めた):

R1 日 = 日本時間の 1 日。f(d) = 日 d に calc_time が入る Binance UM BTCUSDT の資金調達率の |last_funding_rate| の
   平均 × 1e4(bp)。s(d) = 符号つきの平均 × 1e4。精算が 2 回未満の日は値なし。精算は日本時間 1・9・17 時なので、
   日 d − 1 の 3 回は日 d が始まる前に分かっている。
R2 当てる側: 日 d の bitFlyer FX の日の量 v(d)(`vol_split_daily.daily_vol`、同じ R1)。
R3 前もって分かる量: f(d − 1)・s(d − 1)。比べの相手は値動きの量 v(d − 1)(問い 1・2 の主の量の日の版)。
R4 出すもの(期間 2020-01-02〜2023-12-17。2023-12-17 より後の日は使わない):
   (a) f(d − 1)・s(d − 1)・v(d − 1) と v(d) の順位相関。
   (b) log v(d) を log v(d − 1) で回帰した残りと、f(d − 1)・s(d − 1) の順位相関(値動きの量で分かる分を除いた後に
       残る分)。
   (a)(b) の 95% 区間は 5 日の塊の日の塊の再抽出 1,000 回(種 20261003)。区間が 0 を含むかだけを書く(A-12)。
   (c) f(d − 1) の三分位(前の暦年の日の 1/3・2/3 分位。2021 年から)ごとに、日 d が「その日のボラが高」
       (`vol_split_daily.classify_same_day` の高)である日の割合。前の日のボラの区分(`classify`)ごとにも分ける。
R5 経費なし。探索の読みで判定ではない。門にするかはこの表では決めない。

出力: docs/RESEARCH/cards/VOLSPLIT/Q4/TABLES.md と q4.json。

    PYTHONPATH=src python3 scripts/w4_measure/vol_q4_funding.py
"""
from __future__ import annotations

import csv
import glob
import io
import json
import math
import os
import sys
import zipfile
from datetime import datetime, timedelta, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vol_split_daily as vs  # noqa: E402

JST = timezone(timedelta(hours=9))
FUND_DIR = os.path.join(vs.ov.REPO, "backtest_data", "binance_um_fundingRate_BTCUSDT_202001_202312")
FIRST_DAY = "2020-01-02"
MIN_SETTLE = 2


def daily_funding(rows: list[tuple[int, float]]) -> tuple[dict[str, float], dict[str, float]]:
    """R1。(calc_time ms, rate) の並び → (日 → |rate| の平均 bp, 日 → 符号つきの平均 bp)。2023-12-17 より後は捨てる。"""
    by: dict[str, list[float]] = {}
    for t_ms, r in rows:
        d = datetime.fromtimestamp(t_ms / 1000, tz=JST).date().isoformat()
        if d > vs.ov.LAST_DAY:
            continue
        by.setdefault(d, []).append(r)
    fa, fs = {}, {}
    for d, rs in by.items():
        if len(rs) < MIN_SETTLE:
            continue
        fa[d] = float(np.mean(np.abs(rs)) * 1e4)
        fs[d] = float(np.mean(rs) * 1e4)
    return fa, fs


def lagged(x: dict[str, float]) -> dict[str, float]:
    """日 d → x(d − 1)。"""
    return {(datetime.fromisoformat(d) + timedelta(days=1)).date().isoformat(): v for d, v in x.items()}


def _rank(a: np.ndarray) -> np.ndarray:
    order = a.argsort(kind="mergesort")
    r = np.empty(len(a))
    r[order] = np.arange(len(a))
    # 同じ値は平均の順位
    vals, inv, cnt = np.unique(a, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=r)
    return (sums / cnt)[inv]


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3:
        return math.nan
    rx, ry = _rank(x), _rank(y)
    rx, ry = rx - rx.mean(), ry - ry.mean()
    den = math.sqrt(float((rx ** 2).sum() * (ry ** 2).sum()))
    return float((rx * ry).sum() / den) if den > 0 else math.nan


def residual_log(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    """R4 (b)。log y を log x で最小二乗に回帰した残り。"""
    ly, lx = np.log(y), np.log(x)
    A = np.column_stack([np.ones_like(lx), lx])
    beta, *_ = np.linalg.lstsq(A, ly, rcond=None)
    return ly - A @ beta


def block_ci(stat, n: int, block: int = vs.BLOCK) -> tuple[float, float]:
    """日の並び 0..n−1 を 5 日の塊で再抽出し、stat(idx) の 95% 区間。"""
    rng = np.random.default_rng(vs.SEED)
    starts = np.arange(0, max(1, n - block + 1))
    nb = max(1, n // block)
    reps = [stat(np.concatenate([np.arange(s, min(s + block, n)) for s in rng.choice(starts, size=nb)]))
            for _ in range(vs.REPS)]
    lo, hi = np.nanpercentile(reps, [2.5, 97.5])
    return float(lo), float(hi)


def tercile_by_prev_year(x: dict[str, float]) -> dict[str, str]:
    """R4 (c)。日 d → x(d) を d の年の前の暦年の日の分位で切った区分(classify の境の作りと同じ、ずらしは無し)。"""
    by_year: dict[int, list[float]] = {}
    for d, v in x.items():
        by_year.setdefault(int(d[:4]), []).append(v)
    edges = {y + 1: (float(np.quantile(vs_, 1 / 3)), float(np.quantile(vs_, 2 / 3))) for y, vs_ in by_year.items()
             if len(vs_) >= 300}
    out = {}
    for d, v in x.items():
        y = int(d[:4])
        if y not in edges:
            continue
        q1, q2 = edges[y]
        out[d] = "low" if v < q1 else ("mid" if v < q2 else "high")
    return out


def load_funding_rows() -> list[tuple[int, float]]:
    rows = []
    for f in sorted(glob.glob(os.path.join(FUND_DIR, "*.zip"))):
        z = zipfile.ZipFile(f)
        for name in z.namelist():
            r = csv.DictReader(io.StringIO(z.read(name).decode()))
            for row in r:
                rows.append((int(row["calc_time"]), float(row["last_funding_rate"])))
    return rows


def main() -> int:
    vol = vs.daily_vol(vs.load_closes_by_day())
    fa, fs = daily_funding(load_funding_rows())
    fa1, fs1, v1 = lagged(fa), lagged(fs), lagged(vol)
    days = sorted(d for d in vol if d in fa1 and d in v1 and FIRST_DAY <= d <= vs.ov.LAST_DAY)
    V = np.array([vol[d] for d in days])
    V1 = np.array([v1[d] for d in days])
    FA = np.array([fa1[d] for d in days])
    FS = np.array([fs1[d] for d in days])
    n = len(days)
    out = {"days": n, "first": days[0], "last": days[-1], "a": {}, "b": {}}
    for name, x in (("資金調達率の絶対値(d−1)", FA), ("符号つき資金調達率(d−1)", FS), ("bitFlyer のボラ v(d−1)", V1)):
        p = spearman(x, V)
        lo, hi = block_ci(lambda i, x=x: spearman(x[i], V[i]), n)
        out["a"][name] = [p, lo, hi]
    for name, x in (("資金調達率の絶対値(d−1)", FA), ("符号つき資金調達率(d−1)", FS)):
        def stat(i, x=x):
            return spearman(x[i], residual_log(V[i], V1[i]))
        p = stat(np.arange(n))
        lo, hi = block_ci(stat, n)
        out["b"][name] = [p, lo, hi]
    t_f = tercile_by_prev_year(fa1)
    same = vs.classify_same_day(vol)
    prev = vs.classify(vol)
    cdays = [d for d in days if d in t_f and d in same and d in prev]
    tab = {}
    for pk in ("all", "low", "mid", "high"):
        for fk in ("low", "mid", "high"):
            ds = [d for d in cdays if t_f[d] == fk and (pk == "all" or prev[d] == pk)]
            tab[f"{pk}|{fk}"] = [len(ds), (sum(1 for d in ds if same[d] == "high") / len(ds)) if ds else None]
    out["c"] = tab
    out["c_days"] = len(cdays)
    J = {"all": "全部", "low": "低", "mid": "中", "high": "高"}
    L = ["# 問い 4(日の版): 前の日の資金調達率で、荒れた日を前もって当てられるか", "",
         "`scripts/w4_measure/vol_q4_funding.py` が出した。読み方の決まり R1〜R5 はその台本の docstring。", "",
         f"日: {n}({days[0]}〜{days[-1]})。区間は 5 日の塊の再抽出。", "",
         "## 表 1: v(d) との順位相関 (a)", "", "| 前もって分かる量 | 順位相関 [95% 区間] | 区間が 0 を含むか |", "|---|---|---|"]
    for k, (p, lo, hi) in out["a"].items():
        L.append(f"| {k} | {p:+.3f} [{lo:+.3f}, {hi:+.3f}] | {'含む' if lo <= 0 <= hi else '含まない'} |")
    L += ["", "## 表 2: 前の日のボラで分かる分を除いた後の順位相関 (b)", "",
          "| 前もって分かる量 | log v(d) を log v(d−1) で回帰した残りとの順位相関 [95% 区間] | 区間が 0 を含むか |", "|---|---|---|"]
    for k, (p, lo, hi) in out["b"].items():
        L.append(f"| {k} | {p:+.3f} [{lo:+.3f}, {hi:+.3f}] | {'含む' if lo <= 0 <= hi else '含まない'} |")
    L += ["", f"## 表 3: その日のボラが高の日の割合 (c)(2021 年から、{len(cdays)} 日)", "",
          "| 前の日のボラの区分 | 資金調達率の絶対値(d−1) 低 | 中 | 高 |", "|---|---|---|---|"]
    for pk in ("all", "low", "mid", "high"):
        cells = []
        for fk in ("low", "mid", "high"):
            k, r = tab[f"{pk}|{fk}"]
            cells.append("—" if r is None else f"{r:.3f}({k})")
        L.append(f"| {J[pk]} | " + " | ".join(cells) + " |")
    od = os.path.join(vs.ov.REPO, "docs", "RESEARCH", "cards", "VOLSPLIT", "Q4")
    os.makedirs(od, exist_ok=True)
    with open(os.path.join(od, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    with open(os.path.join(od, "q4.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"days {n} -> {od}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
