#!/usr/bin/env python3
"""高ボラの門の問い 3(ほかのカードに当てる)の日の版: 前の日のボラで日を分けて、各カードの日ごとの損益を並べる。

L-608 の一覧の 8、`c2_owner_xvenue_wick/vol_gate/DESIGN.md` 問い 3。読み方の決まり(表を見る前に、この台本と
`tests/research/test_vol_split_daily.py` で固めた):

R1 日 = 日本時間の 1 日。日の量 v(d) = その日の bitFlyer FX_BTC_JPY の 1 分足の |log(終値 / 前の終値)| の平均 × 1e4(bp)。
   足が 60 本未満の日は値なし。
R2 前もって分かる量: 日 d を分けるのは v(d − 1)(前の日の量。日 d が始まる時点で分かる)。前の日に値が無ければ分けない。
R3 三分位の境: 日 d の年の前の暦年の日の v の 1/3・2/3 分位(先読みなし)。最初の年(2015・2016 年)は前の年が
   そろわないので分けない(2017 年から)。
R4 系列: `overlap_daily.py` の SERIES と同じ 13 本(同じ読み込み)。各系列の期間の日だけ。
R5 出すもの: 系列ごとに、低・中・高の日の 1 日あたりの損益(平均)と日数、高 − 低 の差と、その 95% 区間
   (5 日の塊の日の塊の再抽出 1,000 回、種 20261003)。区間が 0 を含むかだけを書き、境は置かない(A-12)。
R6 経費なし。探索の読みで判定ではない。2023-12-17 より後の日は使わない(封印の境の前)。
関門 ② の 1 回目の後に足した出力(読み方の決まり R1〜R6 は変えていない): 分けた日だけの全体の平均(同じ母数)、
低・中・高それぞれの平均の 95% 区間(5 日の塊)、高 − 低 の 20 日の塊の区間(塊の長さの確かめ)、
診断としてその日のボラ(先読みあり。門には使えない)で同じ境で分けた 高 − 低。

関門 ② の 2 回目の後に足した表 3(R7〜R9、表を見る前にこの台本と試験で固めた):
R7 前の日のボラの区分(classify)とその日のボラの区分(classify_same_day)の 3 × 3 で日を分け、系列ごとに各升の
   1 日あたりの損益の平均と日数を出す。両方の区分がある日だけ。
R8 その日のボラの区分ごとに、前の日のボラの 高 − 低 と 95% 区間(5 日の塊、R5 と同じ再抽出)。前の日のボラの
   区分ごとに、その日のボラの 高 − 低 と区間。区間が 0 を含むかだけを書く。
R9 読み: その日の区分の中でも前の日の 高 − 低 が同じ向きに残るなら、前の日の量がその日の量と別に効いている
   【推定】。消えるなら、前の日の差はその日の差の写し。升の日数が 30 日未満の差は「日数が少ない」と書く(30 は
   読み手の目安で、判定の境ではない)。

出力: docs/RESEARCH/cards/VOLSPLIT/TABLES.md と volsplit.json。

    PYTHONPATH=src python3 scripts/w4_measure/vol_split_daily.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import overlap_daily as ov  # noqa: E402

JST = timezone(timedelta(hours=9))
MIN_BARS = 60
SEED = 20261003
REPS = 1000
BLOCK = 5


def daily_vol(closes_by_day: dict[str, list[float]]) -> dict[str, float]:
    """R1。日 → その日の 1 分足の終値の並び(時刻順)から、|対数の値動き| の平均(bp)。"""
    out = {}
    for d, cs in closes_by_day.items():
        if len(cs) < MIN_BARS:
            continue
        c = np.asarray(cs, dtype=float)
        out[d] = float(np.mean(np.abs(np.diff(np.log(c)))) * 1e4)
    return out


def prev_day(d: str) -> str:
    return (datetime.fromisoformat(d) - timedelta(days=1)).date().isoformat()


def classify(vol: dict[str, float], window: bool = False) -> dict[str, str]:
    """R2・R3。日 d → "low" / "mid" / "high"(前の日の量を、前の暦年の日の分位で切る)。
    window=True は窓の口の門(common._window_doors: 環境変数・承認のファイル)を通ったときだけ、最後の日を
    WINDOW1_LAST_DAY(2025-12-11)にする。既定は ov.LAST_DAY(2023-12-17)で今までと同じ。"""
    last_day = ov.LAST_DAY
    if window:
        from common import WINDOW1, WINDOW1_LAST_DAY, _window_doors  # noqa: E402
        _window_doors(WINDOW1[1])
        last_day = WINDOW1_LAST_DAY
    by_year: dict[int, list[float]] = {}
    for d, v in vol.items():
        by_year.setdefault(int(d[:4]), []).append(v)
    edges = {y + 1: (float(np.quantile(vs, 1 / 3)), float(np.quantile(vs, 2 / 3))) for y, vs in by_year.items()
             if len(vs) >= 300}
    out = {}
    for d in sorted(vol):
        p = prev_day(d)
        y = int(d[:4])
        if p not in vol or y not in edges or y < 2017 or d > last_day:
            continue
        q1, q2 = edges[y]
        v = vol[p]
        out[d] = "low" if v < q1 else ("mid" if v < q2 else "high")
    return out


def block_bootstrap_diff(days: list[str], pnl: dict[str, float], cls: dict[str, str],
                         block: int = BLOCK) -> tuple[float, float, float]:
    """R5。高 − 低 の 1 日あたりの差と、塊の再抽出の 95% 区間(既定は 5 日の塊)。"""
    ds = [d for d in days if d in cls]
    x = np.array([pnl[d] for d in ds])
    c = np.array([cls[d] for d in ds])

    def diff(xx, cc):
        hi, lo = xx[cc == "high"], xx[cc == "low"]
        return (hi.mean() if hi.size else math.nan) - (lo.mean() if lo.size else math.nan)

    point = diff(x, c)
    n = len(ds)
    nb = max(1, n // block)
    starts = np.arange(0, n - block + 1) if n >= block else np.array([0])
    rng = np.random.default_rng(SEED)
    reps = []
    for _ in range(REPS):
        pick = rng.choice(starts, size=nb, replace=True)
        idx = np.concatenate([np.arange(s, min(s + block, n)) for s in pick])
        reps.append(diff(x[idx], c[idx]))
    lo, hi = np.nanpercentile(reps, [2.5, 97.5])
    return float(point), float(lo), float(hi)


def class_mean_ci(x: np.ndarray, block: int = BLOCK) -> tuple[float, float, float]:
    """1 つの区分の日の平均と、塊の再抽出の 95% 区間(区分の日を時刻順に並べた列で塊を作る)。"""
    n = len(x)
    if n == 0:
        return math.nan, math.nan, math.nan
    rng = np.random.default_rng(SEED)
    starts = np.arange(0, max(1, n - block + 1))
    nb = max(1, n // block)
    ms = [x[np.concatenate([np.arange(s0, min(s0 + block, n)) for s0 in rng.choice(starts, size=nb)])].mean()
          for _ in range(REPS)]
    lo, hi = np.percentile(ms, [2.5, 97.5])
    return float(x.mean()), float(lo), float(hi)


def classify_same_day(vol: dict[str, float], window: bool = False) -> dict[str, str]:
    """診断(先読みあり): 日 d をその日の量 v(d) で、classify と同じ前の暦年の境で分ける。"""
    # classify は日 d' を vol[d' − 1] で分けるので、v(d) を d − 1 の鍵に置けば、日 d' は v(d') で分かれる。
    # (関門 ② の 2 回目の止める 1: 前は d + 1 の鍵に置いていて、2 日前のボラで分けていた)
    shifted = {}
    for d, v in vol.items():
        shifted[(datetime.fromisoformat(d) - timedelta(days=1)).date().isoformat()] = v
    return classify(shifted, window)


def cross_cells(days: list[str], pnl: dict[str, float], cls_prev: dict[str, str],
                cls_same: dict[str, str]) -> dict[tuple[str, str], tuple[int, float]]:
    """R7。(前の日の区分, その日の区分) → (日数, 1 日あたりの平均)。両方の区分がある日だけ。"""
    out: dict[tuple[str, str], list[float]] = {}
    for d in days:
        if d in cls_prev and d in cls_same:
            out.setdefault((cls_prev[d], cls_same[d]), []).append(pnl[d])
    return {k: (len(v), float(np.mean(v))) for k, v in out.items()}


def within_diff(days: list[str], pnl: dict[str, float], split_by: dict[str, str], hold: dict[str, str],
                k: str) -> tuple[float, float, float, int, int]:
    """R8。hold の区分が k の日だけで、split_by の 高 − 低 と 5 日の塊の区間、高・低の日数。"""
    ds = [d for d in days if d in split_by and hold.get(d) == k]
    point, lo, hi = block_bootstrap_diff(ds, pnl, split_by)
    return point, lo, hi, sum(1 for d in ds if split_by[d] == "high"), sum(1 for d in ds if split_by[d] == "low")


def load_closes_by_day(window: bool = False) -> dict[str, list[float]]:
    """日(日本時間)→ その日の 1 分足の終値の並び。既定は 2015〜2023-12-17T15:00Z まで。
    window=True は窓の口(common.window_guard。環境変数・承認のファイル・記録)を通ったときだけ、2025-12-12T00:00Z の前まで読む。
    窓のときは、どの年の読みも窓の口を通る(記録に残る。2022 年以前のファイルも同じ)。"""
    sys.path.insert(0, os.path.join(ov.REPO, "src"))
    from common import FX_DIR, WINDOW1, load_bars  # noqa: E402
    out: dict[str, list[float]] = {}
    last_utc = datetime.fromtimestamp(WINDOW1[1] / 1e9, tz=timezone.utc) if window else datetime(2023, 12, 17, 15, tzinfo=timezone.utc)
    for y in range(2015, 2026 if window else 2024):
        lo = datetime(y, 1, 1, tzinfo=timezone.utc)
        hi = min(datetime(y + 1, 1, 1, tzinfo=timezone.utc), last_utc)
        if lo >= hi:
            continue
        hi_ns = int(hi.timestamp() * 1e9)
        bars, _, _ = load_bars(FX_DIR, "FX_BTC_JPY", int(lo.timestamp() * 1e9), hi_ns, **({"window": True} if window else {}))
        for b in bars:
            d = datetime.fromtimestamp(int(b.start_time_ns) / 1e9, tz=JST).date().isoformat()
            out.setdefault(d, []).append(float(b.close))
    return out


def main() -> int:
    vol = daily_vol(load_closes_by_day())
    cls = classify(vol)
    cls_same = classify_same_day(vol)
    names = [n for n, _, _ in ov.SERIES]
    rows = []
    for name, kind, d in ov.SERIES:
        s = ov.load_series(kind, d)
        days = sorted(k for k in s if k in cls)
        r = {"name": name}
        for k in ("low", "mid", "high"):
            v = [s[x] for x in days if cls[x] == k]
            r[k] = {"days": len(v), "mean": float(np.mean(v)) if v else None}
        r["diff"], r["lo"], r["hi"] = block_bootstrap_diff(days, s, cls)
        _, r["lo20"], r["hi20"] = block_bootstrap_diff(days, s, cls, block=20)
        r["all_split_days"] = {"days": len(days), "mean": float(np.mean([s[x] for x in days])) if days else None}
        for k in ("low", "mid", "high"):
            r[k]["mean"], r[k]["lo"], r[k]["hi"] = class_mean_ci(np.array([s[x] for x in days if cls[x] == k]))
        days_same = sorted(k for k in s if k in cls_same)
        r["same_day_diff"], r["same_day_lo"], r["same_day_hi"] = block_bootstrap_diff(days_same, s, cls_same)
        all_days = sorted(s)
        r["cross"] = {f"{a}|{b}": v for (a, b), v in cross_cells(all_days, s, cls, cls_same).items()}
        r["prev_within_same"] = {k: within_diff(all_days, s, cls, cls_same, k) for k in ("low", "mid", "high")}
        r["same_within_prev"] = {k: within_diff(all_days, s, cls_same, cls, k) for k in ("low", "mid", "high")}
        rows.append(r)
    L = ["# 前の日のボラで日を分けた、カードごとの 1 日あたりの損益", "",
         "`scripts/w4_measure/vol_split_daily.py` が出した。読み方の決まり R1〜R9 はその台本の docstring。経費の前。", "",
         "| 系列 | 低(日数) | 中(日数) | 高(日数) | 高 − 低 | 95% 区間(5 日の塊) | 区間が 0 を含むか |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        f = lambda k: "—" if r[k]["mean"] is None else f"{r[k]['mean']:.2f}({r[k]['days']})"
        L.append(f"| {r['name']} | {f('low')} | {f('mid')} | {f('high')} | {r['diff']:+.2f} | [{r['lo']:+.2f}, {r['hi']:+.2f}] | "
                 f"{'含む' if r['lo'] <= 0 <= r['hi'] else '含まない'} |")
    L += ["", "## 表 2: 同じ母数・区分ごとの区間・塊の長さ・その日のボラ(関門 ② の 1 回目の後に足した)", "",
          "| 系列 | 分けた日の全体(日数) | 低 [区間] | 中 [区間] | 高 [区間] | 高 − 低 の 20 日の塊の区間 | 診断: その日のボラで分けた 高 − 低 [5 日の塊] |",
          "|---|---|---|---|---|---|---|"]
    for r in rows:
        g = lambda k: f"{r[k]['mean']:.2f} [{r[k]['lo']:.2f}, {r[k]['hi']:.2f}]"
        L.append(f"| {r['name']} | {r['all_split_days']['mean']:.2f}({r['all_split_days']['days']}) | {g('low')} | {g('mid')} | {g('high')} | "
                 f"[{r['lo20']:+.2f}, {r['hi20']:+.2f}] | {r['same_day_diff']:+.2f} [{r['same_day_lo']:+.2f}, {r['same_day_hi']:+.2f}] |")
    J = {"low": "低", "mid": "中", "high": "高"}

    def wd(t):
        p, lo, hi, nh, nl = t
        few = "・日数が少ない" if min(nh, nl) < 30 else ""
        return f"{p:+.2f} [{lo:+.2f}, {hi:+.2f}]({nh}/{nl}{few})"
    L += ["", "## 表 3: 前の日のボラとその日のボラを同時に入れた区分(関門 ② の 2 回目の後に足した。R7〜R9)", "",
          "### 3-1 その日のボラの区分の中で、前の日のボラの 高 − 低 [5 日の塊](高の日数/低の日数)", "",
          "| 系列 | その日 低 | その日 中 | その日 高 |", "|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['name']} | " + " | ".join(wd(r["prev_within_same"][k]) for k in ("low", "mid", "high")) + " |")
    L += ["", "### 3-2 前の日のボラの区分の中で、その日のボラの 高 − 低 [5 日の塊](高の日数/低の日数)", "",
          "| 系列 | 前の日 低 | 前の日 中 | 前の日 高 |", "|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['name']} | " + " | ".join(wd(r["same_within_prev"][k]) for k in ("low", "mid", "high")) + " |")
    L += ["", "### 3-3 各升の 1 日あたりの平均(日数)。列は 前の日/その日", "",
          "| 系列 | " + " | ".join(f"{J[a]}/{J[b]}" for a in ("low", "mid", "high") for b in ("low", "mid", "high")) + " |",
          "|---|" + "---|" * 9]
    for r in rows:
        cells = []
        for a in ("low", "mid", "high"):
            for b in ("low", "mid", "high"):
                v = r["cross"].get(f"{a}|{b}")
                cells.append("—" if v is None else f"{v[1]:.2f}({v[0]})")
        L.append(f"| {r['name']} | " + " | ".join(cells) + " |")
    n_by = {k: sum(1 for v in cls.values() if v == k) for k in ("low", "mid", "high")}
    L += ["", f"分けた日: 低 {n_by['low']}・中 {n_by['mid']}・高 {n_by['high']}(2017-01-01〜{ov.LAST_DAY})"]
    out = os.path.join(ov.REPO, "docs", "RESEARCH", "cards", "VOLSPLIT")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    with open(os.path.join(out, "volsplit.json"), "w", encoding="utf-8") as fh:
        json.dump({"rows": rows, "n_by_class": n_by}, fh, ensure_ascii=False, indent=1)
    print(f"rows {len(rows)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
