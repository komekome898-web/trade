#!/usr/bin/env python3
"""指値の再現などの取引の行(`trades.csv.gz` か `trades.json.gz`、side の列が要る)から、分析のスキルの D3 と向きの情報の検めの表を出す読み口。
新しい走らせはしない(保存済みの取引の行を読むだけ)。カードの測定(1 分ごとの持ち高)の版は `card_trades.py`。

出す表:
  損益は % で持つ(指値の再現の損益は段ごとの損益率 ÷ 段数の和。L-920 で bp は値動き率だけの名前)。
  取引の行の列 pnl_pct を読む。L-920 より前の行(pnl_bp = 率 × 1 万)は / 100 して読む。
  確かめ: 取引の数・損益の和を `summary.json` の all.trades / all.sum_pct(前の記録は all.sum_bp / 100)と突き合わせる。
  勝ち負けの分解: 全期間・前半・後半・年ごと(取引の数・和・勝ち/負けの数・和・平均・中央値・損益 0・勝率)。
  向き × 前半・後半【建ての前に決まる群】: 1 取引あたり(日の塊の区間)。
  向きの情報の検め: 買いの取引の保有中の値段の動き ÷ 保有の分 − 売りの取引の同じ値(%/分)。値段の動き = pnl_pct × side
    (取引の向きを外した、建てから出までの値段の変化。指値の約定の値段を含む)。差が正 = 値段が取引の向きに動いた。
  買いだけの対照: 同じ取引を全部買いで持ったときの 1 日あたり(Σ pnl_pct × side)と、取引 − 買いだけ(= 売りの取引の損益の 2 倍。
    向きの情報の検めにはならない。上げ下げの偏りの大きさを見るため)。
日 = 出の時刻の UTC の暦日(`diag_tables.py` と同じ)。前半・後半 = 期間の日を日数で 2 つに分けたもの(D1 と同じ)。
区間 = 95%、日の塊(循環、5 日・1,000 回・種 20261004)。

    PYTHONPATH=src python3 scripts/analysis/trade_rows.py --run <置き場> --out <出力.md>
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diag_tables import (BLOCK, N_RES, SEED, WINDOW_MARK, _f, group_ratio_ci, mean_ci, period_days,  # noqa: E402
                         utc_day)
import csv  # noqa: E402
import gzip  # noqa: E402
import json  # noqa: E402


def load_rows(d: str) -> dict:
    """取引の行を、side と一緒に読む(並べ替えで side がずれないように、1 回で読む)。"""
    from diag_tables import _iso_ns
    cp, jp = os.path.join(d, "trades.csv.gz"), os.path.join(d, "trades.json.gz")
    if os.path.isfile(cp):
        with gzip.open(cp, "rt", encoding="utf-8", newline="") as fh:
            rows = [r for r in csv.DictReader(fh) if r.get("in_measure", "True") != "False"]
        e = np.array([_iso_ns(r["entry_t"]) for r in rows], dtype=np.int64)
        x = np.array([_iso_ns(r["exit_t"]) for r in rows], dtype=np.int64)
        p = np.array([float(r["pnl_pct"]) if r.get("pnl_pct") not in (None, "") else float(r["pnl_bp"]) / 100
                      for r in rows])
        sd = np.array([float(r["side"]) for r in rows])
    else:
        with gzip.open(jp, "rt", encoding="utf-8") as fh:
            o = json.load(fh)
        scale = {"ns": 1, "s": 10**9}[o["t_unit"]]
        e = np.array(o["entry_t_ns"], dtype=np.int64) * scale
        x = np.array(o["exit_t_ns"], dtype=np.int64) * scale
        p = np.array(o["pnl_pct"], dtype=float) if "pnl_pct" in o else np.array(o["pnl_bp"], dtype=float) / 100
        sd = np.array(o["side"], dtype=float)
    return {"entry": e, "exit": x, "pnl": p, "side": sd}


def check_dir(d: str) -> str:
    """封印の窓の出力の置き場なら、読む前に止める(`diag_tables.load_run` と同じ決まり)。"""
    if WINDOW_MARK in os.path.abspath(d).replace(os.sep, "/"):
        raise SystemExit(f"止める: {d} は封印の窓の出力の置き場(この台本では読まない)")
    return d


def load_meta(d: str, R: dict) -> dict:
    """置き場の名前・`summary.json`・期間の日を読むための入れ物(`diag_tables.period_days` に渡す形)。

    L-920 の後の `diag_tables.load_run` は円の列 `pnl_jpy` の無い `trades.csv.gz` と `trades.json.gz` で止めるので、
    率(%)の取引の行を読むこの台本は `load_run` を使わない(封印の窓の置き場で止める決まりは `check_dir`、`load_run` と同じ)。
    期間の日は `summary.json` の period、無ければ最初と最後の取引の出の日(`load_run` と同じく建て・出の順に並べた最初と最後)。
    """
    summary = None
    sp = os.path.join(d, "summary.json")
    if os.path.isfile(sp):
        with open(sp, encoding="utf-8") as fh:
            summary = json.load(fh)
    order = sorted(zip(R["entry"].tolist(), R["exit"].tolist()))
    return {"dir": d, "name": os.path.basename(os.path.normpath(d)), "summary": summary, "kind": "trades",
            "trades": [{"entry_ns": e, "exit_ns": x} for e, x in order]}


def load_pct_run(d: str) -> dict:
    """損益を率(%)で持つ出力の置き場を読む。L-920 より前の `diag_tables.load_run` と同じ形(種類 card / trades)で、
    損益の鍵だけ `pnl_pct`(%)。`diag_tables.period_days` にそのまま渡せる。日ごとの和は `daily_pct`。

    L-920 の後の `diag_tables.load_run` は円の列 `pnl_jpy` の無い置き場で止めるので、率の出力(カードの測定の
    `daily.csv`、指値の再現の `trades.csv.gz`・`trades.json.gz`)の読み手はこちらを使う。
      - `daily.csv`: 列 `pnl_pct`。L-920 より前の `pnl_bp`(率 × 1 万)は / 100 して % で読む。
      - `trades.csv.gz`・`trades.json.gz`: `load_rows` と同じ(`pnl_pct`、前の `pnl_bp` は / 100)。
    """
    check_dir(d)
    out: dict = {"dir": d, "name": os.path.basename(os.path.normpath(d)), "summary": None, "trades": None, "daily": None}
    sp = os.path.join(d, "summary.json")
    if os.path.isfile(sp):
        with open(sp, encoding="utf-8") as fh:
            out["summary"] = json.load(fh)
    dp = os.path.join(d, "daily.csv")
    if os.path.isfile(dp):
        with open(dp, encoding="utf-8") as fh:
            rd = csv.DictReader(fh)
            col, k = ("pnl_pct", 1.0) if "pnl_pct" in (rd.fieldnames or []) else ("pnl_bp", 100.0)  # 前の記録は / 100
            out["daily"] = {r["day"]: float(r[col]) / k for r in rd}
        out["kind"] = "card"
        return out
    if not (os.path.isfile(os.path.join(d, "trades.csv.gz")) or os.path.isfile(os.path.join(d, "trades.json.gz"))):
        raise SystemExit(f"止める: {d} に daily.csv も trades.csv.gz も trades.json.gz も無い")
    R = load_rows(d)
    rows = sorted(zip(R["entry"].tolist(), R["exit"].tolist(), R["pnl"].tolist()), key=lambda t: (t[0], t[1]))
    out["trades"] = [{"entry_ns": e, "exit_ns": x, "pnl_pct": p} for e, x, p in rows]
    out["kind"] = "trades"
    return out


def daily_pct(run: dict) -> dict[str, float]:
    """`load_pct_run` の出力の日ごとの損益(%)。L-920 より前の `diag_tables.daily_series` と同じ決まり
    (card は daily.csv の日、trades は期間の日に 0 を置き、出の時刻の UTC の日に足す)。"""
    if run["kind"] == "card":
        return dict(run["daily"])
    out = {d: 0.0 for d in period_days(run)}
    for t in run["trades"]:
        d = utc_day(t["exit_ns"])
        if d in out:
            out[d] += t["pnl_pct"]
    return out


def ratio_diff(days, a1, c1, a2, c2):
    """(Σa1/Σc1) − (Σa2/Σc2) の点と、日を循環の塊で選び直した 95% 区間。"""
    A = np.array([[a1.get(d, 0.0), c1.get(d, 0.0), a2.get(d, 0.0), c2.get(d, 0.0)] for d in days])
    if A[:, 1].sum() == 0 or A[:, 3].sum() == 0:
        return None, None, None
    pt = A[:, 0].sum() / A[:, 1].sum() - A[:, 2].sum() / A[:, 3].sum()
    rng = np.random.default_rng(SEED)
    n = len(days)
    nb = math.ceil(n / BLOCK)
    reps = []
    for _ in range(N_RES):
        idx = (rng.integers(0, n, size=nb)[:, None] + np.arange(BLOCK)[None, :]).ravel()[:n] % n
        s = A[idx].sum(axis=0)
        if s[1] > 0 and s[3] > 0:
            reps.append(s[0] / s[1] - s[2] / s[3])
    if len(reps) < N_RES // 2:
        return pt, None, None
    lo, hi = np.percentile(reps, [2.5, 97.5])
    return float(pt), float(lo), float(hi)


def winloss(p: np.ndarray) -> str:
    w, l, z = p[p > 0], p[p < 0], p[p == 0]
    f = lambda a: _f(float(a.mean())) if len(a) else "—"  # noqa: E731
    m = lambda a: _f(float(np.median(a))) if len(a) else "—"  # noqa: E731
    return (f"{len(p):,} | {_f(float(p.sum()))} | {len(w):,} | {_f(float(w.sum()))} | {f(w)} | {m(w)} | {len(l):,} | "
            f"{_f(float(l.sum()))} | {f(l)} | {m(l)} | {len(z):,} | {_f(len(w) / len(p), 3) if len(p) else '—'}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    R = load_rows(check_dir(a.run))
    run = load_meta(a.run, R)
    tr = R["pnl"]
    side, pnl = R["side"], R["pnl"]
    hold = (R["exit"] - R["entry"]) / 6e10
    day = (R["exit"] // (86400 * 10**9)).astype("datetime64[D]").astype(str)
    days = period_days(run)
    h = len(days) // 2
    first = set(days[:h])
    half = np.array(["前半" if d in first else "後半" for d in day])
    move = pnl * side
    L = [f"# 取引の行の表 — {run['name']}", "",
         "読み口 `scripts/analysis/trade_rows.py`(保存済みの取引の行から計算。新しい走らせではない)。損益は %、経費の前。日 = 出の時刻の UTC の日。"
         "区間 = 95%、日の塊(循環、5 日・1,000 回・種 20261004)。", ""]
    s = (run["summary"] or {}).get("all", {})
    L += ["## 確かめ", "", f"- 取引の数: 読んだ行 {len(tr):,} / summary.json の all.trades {s.get('trades', '無し')}",
          f"- 損益の和(%): 読んだ行 {pnl.sum():,.4f} / summary.json の all.sum_pct "
          f"{s['sum_pct'] if 'sum_pct' in s else (s['sum_bp'] / 100 if 'sum_bp' in s else '無し')}",
          f"- 期間の日: {days[0]}〜{days[-1]}({len(days):,} 日)。前半 = {days[0]}〜{days[h - 1]}、後半 = {days[h]}〜{days[-1]}", ""]
    # 勝ち負け
    L += ["## 勝ち負けの分解(全期間・前半・後半・年ごと)", "",
          "| 区分 | 取引 | 和 | 勝ち 数 | 勝ち 和 | 勝ち 平均 | 勝ち 中央値 | 負け 数 | 負け 和 | 負け 平均 | 負け 中央値 | 損益 0 | 勝率 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
          f"| 全期間 | {winloss(pnl)} |", f"| 前半 | {winloss(pnl[half == '前半'])} |", f"| 後半 | {winloss(pnl[half == '後半'])} |"]
    yrs = np.array([d[:4] for d in day])
    for y in sorted(set(yrs)):
        L.append(f"| {y} | {winloss(pnl[yrs == y])} |")
    L.append("")
    # 向き × 前半・後半
    sums, cnts = defaultdict(lambda: defaultdict(float)), defaultdict(lambda: defaultdict(int))
    for p_, s_, d_, hf in zip(pnl, side, day, half):
        g = f"{hf} {'買い' if s_ > 0 else '売り'}"
        sums[g][d_] += p_
        cnts[g][d_] += 1
    L += ["## 向き × 前半・後半【建ての前に決まる群】(1 取引あたり)", "", "| 群 | 取引 | 和 | 1 取引あたり | 区間 |", "|---|---|---|---|---|"]
    for g in sorted(sums):
        ds = days[:h] if g.startswith("前半") else days[h:]
        r = group_ratio_ci(ds, sums[g], cnts[g])
        L.append(f"| {g} | {r['trades']:,} | {_f(r['sum'])} | {_f(r['per_trade'], 3)} | [{_f(r['lo'], 3)}, {_f(r['hi'], 3)}] |")
    L.append("")
    # 向きの情報の検め
    mb, hb, ms, hs = (defaultdict(float) for _ in range(4))
    for mv, hd, s_, d_ in zip(move, hold, side, day):
        if s_ > 0:
            mb[d_] += mv; hb[d_] += hd
        else:
            ms[d_] += mv; hs[d_] += hd
    L += ["## 向きの情報の検め: 買いの取引の値段の動き − 売りの取引の値段の動き(保有の 1 分あたり、%/分)", "",
          "値段の動き = pnl_pct × side(向きを外した、建てから出までの値段の変化。約定の値段を含む)。差が正 = 値段が取引の向きに動いた。"
          "取引に向きの情報が無ければ、両方とも保有中の上げ下げの偏りだけを含むので差は 0。", "",
          "| 区分 | 買いの取引(分) | 売りの取引(分) | 差 [区間] |", "|---|---|---|---|"]
    for lbl, ds in (("全期間", days), ("前半", days[:h]), ("後半", days[h:])):
        pt, lo, hi = ratio_diff(ds, mb, hb, ms, hs)
        rb = sum(mb[d] for d in ds) / max(1e-9, sum(hb[d] for d in ds))
        rs = sum(ms[d] for d in ds) / max(1e-9, sum(hs[d] for d in ds))
        L.append(f"| {lbl} | {_f(rb, 4)}({sum(hb[d] for d in ds):,.0f} 分) | {_f(rs, 4)}({sum(hs[d] for d in ds):,.0f} 分) | "
                 f"{_f(pt, 4)} [{_f(lo, 4)}, {_f(hi, 4)}] |")
    L.append("")
    # 買いだけの対照
    dp, dc = defaultdict(float), defaultdict(float)
    for p_, mv, d_ in zip(pnl, move, day):
        dp[d_] += p_; dc[d_] += mv
    def ci(r):
        return f"{_f(r['mean'])} [{_f(r['lo'])}, {_f(r['hi'])}]"
    L += ["## 買いだけの対照(同じ取引を全部買いで持った 1 日あたり)", "",
          "取引 − 買いだけ = 売りの取引の損益の 2 倍。向きの情報の検めにはならない(上げの偏りがあれば情報が無くても負)。上げ下げの偏りの大きさを見るため。", "",
          "| 区分 | 日数 | 取引 | 買いだけの対照 | 取引 − 買いだけの対照 |", "|---|---|---|---|---|"]
    for lbl, ds in (("全期間", days), ("前半", days[:h]), ("後半", days[h:])):
        L.append(f"| {lbl} | {len(ds):,} | {ci(mean_ci([dp.get(d, 0.0) for d in ds]))} | {ci(mean_ci([dc.get(d, 0.0) for d in ds]))} | "
                 f"{ci(mean_ci([dp.get(d, 0.0) - dc.get(d, 0.0) for d in ds]))} |")
    L.append("")
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print(a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
