"""カード 8 の Binance の門の読み、監査役 1 回目の指摘 2・5・6 の確かめ(2026-10-06、事後の確かめ。事前登録の主の量ではない)。

- 指摘 2: 区分の 高 − 低 が値幅の違いだけで作られていないか。日 d の損益を、前の日 d−1 の量 v(区分を作った量 =
  1 分足の |対数の値動き| の平均、bp)で割った値(先読みなし)と、その日 d の v で割った値(先読みあり、記述だけ)で 高 − 低 を出す。
  v は `vol_split_daily.daily_vol` を `bn_split.py` と同じ読み(`bn_bars.iter_range(cents=False)`・`add_closes`)で作る。
- 指摘 5: 一番不利な組み合わせ(門の形の中ほど − 門なしの始値 と 門の形の始値 − 門なしの中ほど)の区間。
- 指摘 6: 事前登録の MDE の見積もり(仮定のばらつき)と、Binance の実測のばらつきの並べ。
区間と MDE は読み口 `scripts/analysis/diag_tables.py` の `mean_ci`・`diff_ci`(種 20261004)。

    PYTHONPATH=src:scripts/w4_measure:scripts/w4_measure/c8_binance python3 docs/RESEARCH/cards/c8_session_mean_revert/binance_gate/read/audit1_checks.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import date, timedelta

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../../../../../.."))
for p in ("scripts/analysis", "scripts/w4_measure", "scripts/w4_measure/c8_binance"):
    sys.path.insert(0, os.path.join(ROOT, p))
import diag_tables as dt  # noqa: E402
import vol_split_daily as vs  # noqa: E402
import bn_bars  # noqa: E402
import bn_split  # noqa: E402

BG = os.path.dirname(HERE)


def daily(name):
    with open(os.path.join(BG, "measure/jst_day", name), encoding="utf-8") as fh:
        return {r["day"]: float(r["pnl_bp"]) for r in csv.DictReader(fh)}


def prev(d):
    return (date.fromisoformat(d) - timedelta(days=1)).isoformat()


def main() -> int:
    cj = json.load(open(os.path.join(BG, "split/classes.json"), encoding="utf-8"))
    cls, hb = cj["classes"], cj["half_boundary_day"]
    days = sorted(cls)
    closes: dict = {}
    for _y, bars, _f in bn_bars.iter_range(bn_bars.LO, bn_bars.HI, cents=False):
        bn_split.add_closes(closes, bars)
        del bars
    vol = vs.daily_vol(closes)
    # 区分が vol から作り直せることの照合(classes.json と同じか)
    re_cls = vs.classify(vol)
    n_mismatch = sum(1 for d in days if re_cls.get(d) != cls[d])
    L = ["# 監査役 1 回目の指摘 2・5・6 の確かめ(事後)", "", "`audit1_checks.py` が出した。bp/日、経費の前。区間は日の塊(5 日・1,000 回・種 20261004)。", "",
         f"- 区分の作り直しの照合: `vol_split_daily.classify` で作り直した区分と `classes.json` の食い違い {n_mismatch} 日 / {len(days)} 日", ""]
    for fill, name in (("始値", "daily.csv"), ("中ほど", "daily_mid.csv")):
        d = daily(name)
        L += [f"## 指摘 2: 値幅で割った 高 − 低(約定 = {fill})", "",
              "| 割る量 | 期間 | 低 [区間] | 高 [区間] | 高 − 低 [区間] |", "|---|---|---|---|---|"]
        for lab_v, vf in (("前の日の v(先読みなし)", lambda x: vol.get(prev(x))), ("その日の v(先読みあり・記述)", lambda x: vol.get(x))):
            for lab, sel in (("全期間", lambda x: True), ("前半", lambda x: x < hb), ("後半", lambda x: x >= hb)):
                lo = [d.get(x, 0.0) / vf(x) for x in days if sel(x) and cls[x] == "low" and vf(x)]
                hi = [d.get(x, 0.0) / vf(x) for x in days if sel(x) and cls[x] == "high" and vf(x)]
                L.append(f"| {lab_v} | {lab} | {dt._ci(dt.mean_ci(lo))}({len(lo)}) | {dt._ci(dt.mean_ci(hi))}({len(hi)}) | {dt._ci(dt.diff_ci(lo, hi))} |")
        L.append("")
        mv = {c: float(np.mean([vol[prev(x)] for x in days if cls[x] == c and prev(x) in vol])) for c in ("low", "mid", "high")}
        L += [f"区分ごとの前の日の v の平均(bp): 低 {mv['low']:.3f}・中 {mv['mid']:.3f}・高 {mv['high']:.3f}", ""]
    # 指摘 5
    do, dm = daily("daily.csv"), daily("daily_mid.csv")
    L += ["## 指摘 5: 一番不利な組み合わせ(区分のある 1,812 日に均した、同じ日どうしの差)", "",
          "| 差 | 1 日あたり [区間] | MDE |", "|---|---|---|"]
    for gate, keep in (("A", lambda x: cls[x] == "high"), ("B", lambda x: cls[x] != "low")):
        for lab, g, n in (("門の形 中ほど − 門なし 始値", dm, do), ("門の形 始値 − 門なし 中ほど", do, dm)):
            v = [(g.get(x, 0.0) if keep(x) else 0.0) - n.get(x, 0.0) for x in days]
            r = dt.mean_ci(v)
            L.append(f"| {gate}: {lab} | {dt._ci(r)} | {dt._f(r['mde'])} |")
    L.append("")
    # 指摘 6
    L += ["## 指摘 6: MDE の見積もりと実測", "",
          "| 量 | 事前登録の見積もり(仮定のばらつき) | 実測の MDE(GATE_READ、始値) | 実測の日ごとの標準偏差 |", "|---|---|---|---|"]
    for gate, keep, est, meas in (("A − 門なし", lambda x: cls[x] == "high", 16.5, 15.362), ("B − 門なし", lambda x: cls[x] != "low", 11.9, 11.560)):
        v = [(do.get(x, 0.0) if keep(x) else 0.0) - do.get(x, 0.0) for x in days]
        L.append(f"| {gate} | {est} | {meas} | {float(np.std(v, ddof=1)):.2f} |")
    sd = {c: float(np.std([do.get(x, 0.0) for x in days if cls[x] == c], ddof=1)) for c in ("low", "mid", "high")}
    L += ["", f"区分ごとの日ごとの標準偏差(実測、始値): 低 {sd['low']:.1f}・中 {sd['mid']:.1f}・高 {sd['high']:.1f}(事前登録の仮定は bitFlyer の区間の幅から逆算: 低 265・中 342・高 528)", ""]
    out = os.path.join(HERE, "audit1_checks.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
