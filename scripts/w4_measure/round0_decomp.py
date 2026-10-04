#!/usr/bin/env python3
"""D1 今の paper bot(`backtest_runs_shared/cards/c1_xborder_mom/default/`、overlap_daily.py の SERIES と同じ読み込み)の日ごとの損益を、
   暦年(日本時間の日の年)× 前の日のボラの区分(vol_split_daily.py の classify、低・中・高・区分なし)で分け、升ごとに
   日数・損益の和・1 日あたりの平均を出す。各年の行に、その年の損益の和に占める各区分の割合も出す。
D2 週末ギャップ BTC(`backtest_runs_shared/cards/c6_weekend_gap_revert/btc/trades.json.gz`)の取引ごとに、
   窓の大きさ g = (取引の入りの値段 / 入りの時刻より前の最後の金曜(日本時間)の bitFlyer FX_BTC_JPY の 1 分足の最後の終値 − 1) × 1e4(bp)
   を出す。足は common.load_bars(封印の門をそのまま使う。2023-12-18 以降を読まない)。g の符号と持ち高の向きが逆か同じか
   (窓を埋める向きか広げる向きか)、|g| の 3 つの帯(全取引の |g| の 1/3・2/3 分位。分位の値も出す)、暦年 で分け、
   升ごとに取引の数・損益の和・1 取引あたり・勝ちの数を出す。入りの値段は trades.json.gz の entry_px。
D3 区間・検定・境は出さない。経費なし。数字は手で書かない。

    PYTHONPATH=src python3 scripts/w4_measure/round0_decomp.py
"""
from __future__ import annotations

import bisect
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vol_split_daily as vs  # noqa: E402  (overlap_daily を中で読む。どちらも変えない)

ov = vs.ov
JST = timezone(timedelta(hours=9))
C1 = os.path.join(ov.SHARED, "c1_xborder_mom", "default")
C6_TRADES = os.path.join(ov.SHARED, "c6_weekend_gap_revert", "btc", "trades.json.gz")
OUT = os.path.join(ov.REPO, "docs", "RESEARCH", "cards", "ROUND0_DECOMP")
CLASSES = ("low", "mid", "high", "none")
CJ = {"low": "低", "mid": "中", "high": "高", "none": "区分なし"}
BANDS = ("small", "mid", "large")
BJ = {"small": "小", "mid": "中", "large": "大"}
DIRS = ("fill", "widen", "zero")
DJ = {"fill": "埋める向き(g の符号と持ち高が逆)", "widen": "広げる向き(g の符号と持ち高が同じ)", "zero": "g = 0"}


# ---------------------------------------------------------------- D1
def d1_cells(pnl: dict[str, float], cls: dict[str, str]) -> dict:
    """年 → {区分 → {days, sum, mean}}、と年ごとの和・割合。区分なし = classify が値を付けなかった日。"""
    years: dict[str, dict] = {}
    for d in sorted(pnl):
        y = d[:4]
        c = cls.get(d, "none")
        cell = years.setdefault(y, {k: {"days": 0, "sum": 0.0} for k in CLASSES})[c]
        cell["days"] += 1
        cell["sum"] += pnl[d]
    out = {}
    for y, cells in years.items():
        tot = sum(c["sum"] for c in cells.values())
        ndays = sum(c["days"] for c in cells.values())
        row = {}
        for k in CLASSES:
            c = cells[k]
            row[k] = {"days": c["days"], "sum": c["sum"],
                      "mean": (c["sum"] / c["days"]) if c["days"] else None,
                      "share": (c["sum"] / tot) if tot != 0 else None}
        out[y] = {"cells": row, "year_sum": tot, "year_days": ndays}
    return out


# ---------------------------------------------------------------- D2
def friday_bars(bars: list[tuple[int, float]]) -> tuple[list[int], list[float]]:
    """(足の始まり ns, 終値) の並びから、日本時間の金曜(0:00〜翌 0:00 の前)に始まる足だけを時刻順に返す。"""
    st, cl = [], []
    for s, c in bars:
        if datetime.fromtimestamp(s // 10**9, tz=JST).weekday() == 4:
            st.append(s)
            cl.append(c)
    return st, cl


def last_friday_close(fri_starts: list[int], fri_closes: list[float], entry_ns: int):
    """入りの時刻より前に始まった足のうち、日本時間の金曜の最後の足の (始まり ns, 終値)。無ければ None。"""
    i = bisect.bisect_left(fri_starts, entry_ns) - 1
    if i < 0:
        return None
    return fri_starts[i], fri_closes[i]


def gap_bp(entry_px: float, fri_close: float) -> float:
    return (entry_px / fri_close - 1.0) * 1e4


def direction(g: float, side: int) -> str:
    if g == 0:
        return "zero"
    return "fill" if (1 if g > 0 else -1) == -side else "widen"


def tercile_edges(abs_g: list[float]) -> tuple[float, float]:
    q1, q2 = np.quantile(np.asarray(abs_g, dtype=float), [1 / 3, 2 / 3])
    return float(q1), float(q2)


def band(a: float, q1: float, q2: float) -> str:
    """vol_split_daily.classify と同じ向きの境: 下の境より小さければ小、上の境以上なら大、その間(下の境を含む)は中。"""
    return "small" if a < q1 else ("mid" if a < q2 else "large")


def _cell() -> dict:
    return {"n": 0, "sum": 0.0, "wins": 0}


def d2_cells(rows: list[dict]) -> dict:
    """rows の各要素 = {year, dir, band, pnl}。年 × 向き × 帯、年 × 向き、年 × 帯、向き × 帯、年、全体。"""
    tabs: dict[str, dict] = {k: {} for k in ("year_dir_band", "year_dir", "year_band", "dir_band", "year", "all")}
    for r in rows:
        keys = {"year_dir_band": (r["year"], r["dir"], r["band"]), "year_dir": (r["year"], r["dir"]),
                "year_band": (r["year"], r["band"]), "dir_band": (r["dir"], r["band"]),
                "year": (r["year"],), "all": ("all",)}
        for name, key in keys.items():
            c = tabs[name].setdefault("|".join(key), _cell())
            c["n"] += 1
            c["sum"] += r["pnl"]
            c["wins"] += 1 if r["pnl"] > 0 else 0
    for t in tabs.values():
        for c in t.values():
            c["mean"] = c["sum"] / c["n"]
    return tabs


def load_fx_bars():
    """2015-01-01 〜 2023-12-17T15:00Z(封印の境の前)の 1 分足を封印の門(common.load_bars)で読む。
    (日 → 終値の並び[vol_split_daily.load_closes_by_day と同じ区切り], [(始まり ns, 終値)])。"""
    sys.path.insert(0, os.path.join(ov.REPO, "src"))
    from common import FX_DIR, load_bars  # noqa: E402
    closes_by_day: dict[str, list[float]] = {}
    allbars: list[tuple[int, float]] = []
    for y in range(2015, 2024):
        lo = datetime(y, 1, 1, tzinfo=timezone.utc)
        hi = min(datetime(y + 1, 1, 1, tzinfo=timezone.utc), datetime(2023, 12, 17, 15, tzinfo=timezone.utc))
        if lo >= hi:
            continue
        bars, _, _ = load_bars(FX_DIR, "FX_BTC_JPY", int(lo.timestamp() * 1e9), int(hi.timestamp() * 1e9))
        for b in bars:
            s = int(b.start_time_ns)
            closes_by_day.setdefault(datetime.fromtimestamp(s // 10**9, tz=JST).date().isoformat(), []).append(float(b.close))
            allbars.append((s, float(b.close)))
    return closes_by_day, allbars


# ---------------------------------------------------------------- 出力
def _n(v, nd=2):
    return "—" if v is None else f"{v:.{nd}f}"


def _pct(v):
    return "—" if v is None else f"{v * 100:.1f}%"


def render(d1: dict, d2: dict, meta: dict) -> str:
    L = ["# 今の paper bot と週末ギャップの分解の表", "",
         "`scripts/w4_measure/round0_decomp.py` が出した。読み方の決まり D1〜D3 はその台本の docstring。経費の前。", "",
         "## 表 1(D1): 今の paper bot の日ごとの損益を、年 × 前の日のボラの区分で分けた", "",
         f"- 系列: `backtest_runs_shared/cards/c1_xborder_mom/default/daily.csv`(日数 {meta['d1_days']}、{meta['d1_first']}〜{meta['d1_last']})",
         "- 升 = 日数 / 損益の和(bp)/ 1 日あたり(bp)。右の欄 = その年の損益の和に占める割合(区分の和 ÷ 年の和)", "",
         "| 年 | " + " | ".join(CJ[k] for k in CLASSES) + " | 年の日数 | 年の損益の和 | " + " | ".join(f"割合 {CJ[k]}" for k in CLASSES) + " |",
         "|---|" + "---|" * (2 * len(CLASSES) + 2)]
    for y in sorted(d1):
        r = d1[y]
        cells = [f"{r['cells'][k]['days']} / {_n(r['cells'][k]['sum'])} / {_n(r['cells'][k]['mean'])}" for k in CLASSES]
        shares = [_pct(r["cells"][k]["share"]) for k in CLASSES]
        L.append(f"| {y} | " + " | ".join(cells) + f" | {r['year_days']} | {_n(r['year_sum'])} | " + " | ".join(shares) + " |")
    tot_days = sum(r["year_days"] for r in d1.values())
    tot_sum = sum(r["year_sum"] for r in d1.values())
    L.append(f"| 全期間 | " + " | ".join(
        f"{sum(r['cells'][k]['days'] for r in d1.values())} / {_n(sum(r['cells'][k]['sum'] for r in d1.values()))} / "
        f"{_n(sum(r['cells'][k]['sum'] for r in d1.values()) / max(1, sum(r['cells'][k]['days'] for r in d1.values())))}"
        for k in CLASSES) + f" | {tot_days} | {_n(tot_sum)} | " + " | ".join(
        _pct(sum(r["cells"][k]["sum"] for r in d1.values()) / tot_sum if tot_sum != 0 else None) for k in CLASSES) + " |")
    L += ["", f"分けた日の数(classify が区分を付けた日。全 SERIES 共通の母数ではなく、この系列の日だけ): "
              f"低 {meta['d1_n']['low']}・中 {meta['d1_n']['mid']}・高 {meta['d1_n']['high']}・区分なし {meta['d1_n']['none']}",
          "", "## 表 2(D2): 週末ギャップ BTC の取引の分解", "",
          f"- 取引 {meta['d2_trades']} 件(`trades.json.gz`)。g を出せた取引 {meta['d2_with_g']} 件、金曜の足が無く g を出せなかった取引 {meta['d2_no_g']} 件",
          f"- 入りの時刻の日本時間の曜日(月 0〜日 6)ごとの取引数: {meta['d2_entry_weekday']}",
          f"- |g| の分位(全取引の |g|、bp): 1/3 分位 = {meta['q1']:.4f}、2/3 分位 = {meta['q2']:.4f}。帯: 小 = |g| < 1/3 分位、"
          f"中 = 1/3 分位 以上 2/3 分位 未満、大 = 2/3 分位 以上",
          "- 升 = 取引の数 / 損益の和(bp)/ 1 取引あたり(bp)/ 勝ち(損益 > 0)の数", ""]

    def fmt(c):
        return "—" if c is None else f"{c['n']} / {_n(c['sum'])} / {_n(c['mean'])} / {c['wins']}"
    dirs = [d for d in DIRS if any(k.split("|")[0] == d for k in d2["dir_band"])]
    L += ["### 2-1 向き × |g| の帯(全期間)", "", "| 向き | " + " | ".join(f"帯 {BJ[b]}" for b in BANDS) + " | 合計 |",
          "|---|" + "---|" * (len(BANDS) + 1)]
    for d in dirs:
        tot = _cell()
        for b in BANDS:
            c = d2["dir_band"].get(f"{d}|{b}")
            if c:
                tot["n"] += c["n"]; tot["sum"] += c["sum"]; tot["wins"] += c["wins"]
        tot["mean"] = tot["sum"] / tot["n"]
        L.append(f"| {DJ[d]} | " + " | ".join(fmt(d2["dir_band"].get(f"{d}|{b}")) for b in BANDS) + f" | {fmt(tot)} |")
    years = sorted({k.split("|")[0] for k in d2["year"]})
    L += ["", "### 2-2 年 × 向き(全帯)", "", "| 年 | " + " | ".join(DJ[d] for d in dirs) + " | 年の合計 |", "|---|" + "---|" * (len(dirs) + 1)]
    for y in years:
        L.append(f"| {y} | " + " | ".join(fmt(d2["year_dir"].get(f"{y}|{d}")) for d in dirs) + f" | {fmt(d2['year'][y])} |")
    L += ["", "### 2-3 年 × |g| の帯(全向き)", "", "| 年 | " + " | ".join(f"帯 {BJ[b]}" for b in BANDS) + " | 年の合計 |", "|---|" + "---|" * (len(BANDS) + 1)]
    for y in years:
        L.append(f"| {y} | " + " | ".join(fmt(d2["year_band"].get(f"{y}|{b}")) for b in BANDS) + f" | {fmt(d2['year'][y])} |")
    L += ["", "### 2-4 年 × 向き × |g| の帯(全部を掛けた升)", "",
          "| 年 | 向き | " + " | ".join(f"帯 {BJ[b]}" for b in BANDS) + " |", "|---|---|" + "---|" * len(BANDS)]
    for y in years:
        for d in dirs:
            L.append(f"| {y} | {DJ[d]} | " + " | ".join(fmt(d2["year_dir_band"].get(f"{y}|{d}|{b}")) for b in BANDS) + " |")
    L += ["", f"全取引: {fmt(d2['all']['all'])}", ""]
    return "\n".join(L)


def main() -> int:
    t0 = time.time()
    closes_by_day, allbars = load_fx_bars()
    vol = vs.daily_vol(closes_by_day)
    cls = vs.classify(vol)

    # D1
    pnl = ov.load_series("daily", C1)
    d1 = d1_cells(pnl, cls)
    n1 = {k: sum(r["cells"][k]["days"] for r in d1.values()) for k in CLASSES}

    # D2
    from bot.research.trade_record import read_trades_json
    tr = read_trades_json(C6_TRADES)
    fs, fc = friday_bars(allbars)
    recs, no_g = [], 0
    wd: dict[int, int] = {}
    for i in range(len(tr["side"])):
        e = int(tr["entry_t_ns"][i])
        w = datetime.fromtimestamp(e // 10**9, tz=JST).weekday()
        wd[w] = wd.get(w, 0) + 1
        ref = last_friday_close(fs, fc, e)
        if ref is None:
            no_g += 1
            continue
        g = gap_bp(float(tr["entry_px"][i]), ref[1])
        recs.append({"i": i, "entry_t_ns": e, "side": int(tr["side"][i]), "entry_px": float(tr["entry_px"][i]),
                     "fri_bar_start_ns": ref[0], "fri_close": ref[1], "g_bp": g, "pnl": float(tr["pnl_bp"][i]),
                     "year": str(datetime.fromtimestamp(e // 10**9, tz=JST).year), "dir": direction(g, int(tr["side"][i]))})
    q1, q2 = tercile_edges([abs(r["g_bp"]) for r in recs])
    for r in recs:
        r["band"] = band(abs(r["g_bp"]), q1, q2)
    d2 = d2_cells(recs)

    meta = {"d1_days": len(pnl), "d1_first": min(pnl), "d1_last": max(pnl), "d1_n": n1,
            "d2_trades": len(tr["side"]), "d2_with_g": len(recs), "d2_no_g": no_g,
            "d2_entry_weekday": {str(k): v for k, v in sorted(wd.items())}, "q1": q1, "q2": q2}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write(render(d1, d2, meta) + "\n")
    with open(os.path.join(OUT, "decomp.json"), "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "d1": d1, "d2": d2, "d2_trades": recs}, fh, ensure_ascii=False, indent=1)
    print(f"d1 years {len(d1)} / d2 trades {len(recs)} -> {OUT} ({time.time() - t0:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
