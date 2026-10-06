#!/usr/bin/env python3
"""部品 2: Binance の足で前の日の荒れ具合の区分を作り、区分ごとの日数を数える(損益は 1 つも計算しない)。

  1. 部品 1(bn_bars)の足(取引の無い分は落とした後。値段は USDT のまま = cents=False)から、日本時間の日 → その日の 1 分足の終値の並び(時刻順)を作る。
     日 = 足の始まり(start_time_ns)の日本時間の日(vol_split_daily.load_closes_by_day と同じ)。
  2. vol_split_daily.daily_vol と vol_split_daily.classify をそのまま当てる(写さない。最後の日 ov.LAST_DAY = 2023-12-17 も同じ)。
  3. 出力: 日 → low / mid / high の JSON(classes.json)、日数の表(年ごと × 区分、全体、前半・後半)、
     区分の境(年ごとの 3 分位の値。classify と同じ式で出し直し、classify の結果と食い違わないことを確かめる)。
     前半・後半の境 = 区分のある日を日付順に並べ、日数で 2 つに分けた日(n // 2 番目の日。その日から後半)。
     結果を見る前の決まり(委任文の部品 2)。

    PYTHONPATH=src python3 scripts/w4_measure/c8_binance/bn_split.py [--out <置き場>]
既定の置き場: docs/RESEARCH/cards/c8_session_mean_revert/binance_gate/split/
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
W4 = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, W4)

import bn_bars  # noqa: E402
import vol_split_daily as vs  # noqa: E402
from common import ROOT, to_iso  # noqa: E402

JST = timezone(timedelta(hours=9))
CLASSES = ("low", "mid", "high")
OUT = os.path.join(ROOT, "docs/RESEARCH/cards/c8_session_mean_revert/binance_gate/split")


def add_closes(out: dict, bars) -> dict:
    """日本時間の日(足の始まり)→ 終値の並び に bars を足す(時刻順に渡すこと)。"""
    for b in bars:
        d = datetime.fromtimestamp(int(b.start_time_ns) // 10**9, tz=JST).date().isoformat()
        out.setdefault(d, []).append(float(b.close))
    return out


def edges_by_year(vol: dict) -> dict:
    """classify の中の境と同じ式: 年 y の日の境 = 年 y − 1 の日の v の 1/3・2/3 分位(その年に 300 日以上あるときだけ)。"""
    by_year: dict = {}
    for d, v in vol.items():
        by_year.setdefault(int(d[:4]), []).append(v)
    return {y + 1: {"q1": float(np.quantile(vs_, 1 / 3)), "q2": float(np.quantile(vs_, 2 / 3)), "from_year": y,
                    "n_days_from_year": len(vs_)}
            for y, vs_ in sorted(by_year.items()) if len(vs_) >= 300}


def check_edges(vol: dict, cls: dict, edges: dict) -> int:
    """出し直した境で分けた区分と classify の区分の食い違いの数(0 のはず)。"""
    bad = 0
    for d, c in cls.items():
        e = edges[int(d[:4])]
        v = vol[vs.prev_day(d)]
        mine = "low" if v < e["q1"] else ("mid" if v < e["q2"] else "high")
        bad += mine != c
    return bad


def half_boundary(days: list) -> str:
    """区分のある日を日付順に並べ、日数で 2 つに分ける。戻り = 後半の最初の日(n // 2 番目)。"""
    ds = sorted(days)
    if len(ds) < 2:
        raise ValueError("区分のある日が 2 日未満")
    return ds[len(ds) // 2]


def count_table(cls: dict, boundary: str) -> dict:
    """日数の表: 年ごと × 区分、全体、前半(< 境)・後半(>= 境)。"""
    t = {"by_year": {}, "all": {k: 0 for k in CLASSES}, "first_half": {k: 0 for k in CLASSES},
         "second_half": {k: 0 for k in CLASSES}}
    for d, c in sorted(cls.items()):
        t["by_year"].setdefault(d[:4], {k: 0 for k in CLASSES})[c] += 1
        t["all"][c] += 1
        t["first_half" if d < boundary else "second_half"][c] += 1
    for row in [*t["by_year"].values(), t["all"], t["first_half"], t["second_half"]]:
        row["total"] = sum(row[k] for k in CLASSES)
    return t


def table_md(t: dict, boundary: str, edges: dict, extra: list) -> str:
    L = ["# カード 8 の門(Binance BTCUSDT 1 分足): 前の日の荒れ具合の区分の日数",
         "", "`scripts/w4_measure/c8_binance/bn_split.py` が出した。損益は計算していない。",
         "", "| 年 | low | mid | high | 計 |", "|---|---|---|---|---|"]
    for y, r in t["by_year"].items():
        L.append(f"| {y} | {r['low']} | {r['mid']} | {r['high']} | {r['total']} |")
    for name, key in (("全体", "all"), (f"前半(〜{boundary} の前)", "first_half"), (f"後半({boundary}〜)", "second_half")):
        r = t[key]
        L.append(f"| {name} | {r['low']} | {r['mid']} | {r['high']} | {r['total']} |")
    L += ["", f"前半・後半の境の日(後半の最初の日): {boundary}", "",
          "## 区分の境(年 y の日を分ける値 = 年 y − 1 の日の量 v の 1/3・2/3 分位、bp)", "",
          "| 分ける年 | 境を作った年 | その年の日数 | 1/3 分位 | 2/3 分位 |", "|---|---|---|---|---|"]
    for y, e in edges.items():
        note = "(使われない: classify の最後の日 " + vs.ov.LAST_DAY + " より後の年)" if f"{y}-01-01" > vs.ov.LAST_DAY else ""
        L.append(f"| {y}{note} | {e['from_year']} | {e['n_days_from_year']} | {e['q1']:.6f} | {e['q2']:.6f} |")
    return "\n".join(L + [""] + extra) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    closes: dict = {}
    reads = []
    prev_last = None
    # cents=False: 値段は置き場の USDT のまま(コミット 8f2a8a24 の split/classes.json を作ったときと同じ入力。
    # 量 v は値段の比の対数なので単位に依らないが、セントに丸めると浮動小数の末の桁が変わり、分位の境の日が動きうるため)
    for y, bars, facts in bn_bars.iter_range(bn_bars.LO, bn_bars.HI, cents=False):
        add_closes(closes, bars)
        if prev_last is not None and bars:  # 年の境(ファイルの境)の行の無い分(データ層は 1 ファイルずつなので見ない)
            facts["missing_minutes_at_year_start"] = int((int(bars[0].start_time_ns) - prev_last) // bn_bars.MIN_NS) - 1
        if bars:
            prev_last = int(bars[-1].start_time_ns)
        reads.append(facts)
        print(json.dumps({k: facts[k] for k in ("year", "range", "n_bars_kept", "n_synthetic_dropped", "n_missing_minutes", "n_off_grid_dropped")},
                         ensure_ascii=False), flush=True)
        del bars
    vol = vs.daily_vol(closes)
    cls = vs.classify(vol)
    edges = edges_by_year(vol)
    n_bad = check_edges(vol, cls, edges)
    boundary = half_boundary(list(cls))
    t = count_table(cls, boundary)
    y2018 = {k: v for k, v in t["by_year"].items() if k == "2018"}
    n_days_by_year = {}
    for d in vol:
        n_days_by_year[d[:4]] = n_days_by_year.get(d[:4], 0) + 1
    meta = {"what": "カード 8 の門(Binance)の区分。日 d の区分 = 前の日 d − 1 の量 v を、d の年の前の暦年の日の分位で切ったもの"
                    "(vol_split_daily.classify をそのまま当てた)",
            "rule_half": "区分のある日を日付順に並べ、n // 2 番目の日から後半",
            "half_boundary_day": boundary, "n_classified": len(cls), "first_day": min(cls), "last_day": max(cls),
            "n_days_with_vol_by_year": n_days_by_year, "n_days_closes": len(closes),
            "edges": {str(k): v for k, v in edges.items()}, "classify_vs_edges_mismatch": n_bad,
            "classified_2018": y2018 or "2018 年の日は区分されていない",
            "read": reads, "read_range": [to_iso(bn_bars.LO), to_iso(bn_bars.HI)]}
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "classes.json"), "w", encoding="utf-8") as fh:
        json.dump({"classes": dict(sorted(cls.items())), "half_boundary_day": boundary}, fh, ensure_ascii=False, indent=0)
        fh.write("\n")
    with open(os.path.join(a.out, "split_facts.json"), "w", encoding="utf-8") as fh:
        json.dump({**meta, "counts": t}, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    extra = ["## 量 v(日の終値の |対数の値動き| の平均)のある日の数(年ごと)", "",
             "| 年 | 日数 |", "|---|---|"] + [f"| {y} | {n} |" for y, n in sorted(n_days_by_year.items())]
    with open(os.path.join(a.out, "COUNTS.md"), "w", encoding="utf-8") as fh:
        fh.write(table_md(t, boundary, {str(k): v for k, v in edges.items()}, extra))
    print(json.dumps({"n_classified": len(cls), "half_boundary_day": boundary, "counts": t, "edges": meta["edges"],
                      "classify_vs_edges_mismatch": n_bad, "n_days_with_vol_by_year": n_days_by_year},
                     ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
