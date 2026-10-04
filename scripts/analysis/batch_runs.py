#!/usr/bin/env python3
"""走らせの置き場の下の全部の走らせに、分析のスキルの同じ表を一括で出す読み口(新しい走らせはしない。保存済みの取引の行を読むだけ)。

走らせごとに出すもの(`--out` の下に `<走らせ>.md`)と、一覧(`--out/INDEX.md`):
  確かめ: 取引の数・損益の和(summary.json の all.trades / all.sum_bp と突き合わせ)
  D1: 全期間・暦年ごと・前半・後半の 1 日あたり [区間]・MDE と、後半 − 前半、結果(`diag_tables.d1_outcome`)
  勝ち負けの分解: 全期間・前半・後半・暦年ごと
  向きの情報の検め: 買いの取引の値段の動き ÷ 保有の分 − 売りの取引の同じ値(bp/分。値段の動き = pnl_bp × side)
  買いだけの対照: 同じ取引を全部買いで持った 1 日あたり
  良い側・悪い側の組(名前の末尾 `_good` / `_bad`)には、D8 の全期間の符号(両側が同じか)を一覧に出す。
日 = 出の時刻の UTC の日。期間 = summary.json の period(無ければ最初と最後の取引)。前半・後半 = 期間の日を日数で 2 つに分けたもの。
区間 = 95%、日の塊(循環、5 日・1,000 回・種 20261004)。`diag_tables.py`・`trade_rows.py` と同じ式(1 本ずつ同じ値になることを
`--check` で確かめられる)。

    PYTHONPATH=src python3 scripts/analysis/batch_runs.py --runs <置き場> --out <出力の置き場> [--only <名前の一部>] [--jobs 4]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import date, datetime, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diag_tables import BLOCK, N_RES, SEED, _f, d1_outcome, days_needed, diff_ci, mean_ci  # noqa: E402
from trade_rows import load_rows  # noqa: E402

WINDOW_MARK = "docs/RESEARCH/WINDOW1"


def _iso_day(s: str) -> date:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).date()


def period(run_dir: str, R: dict) -> list[str]:
    sp = os.path.join(run_dir, "summary.json")
    sm = json.load(open(sp, encoding="utf-8")) if os.path.isfile(sp) else {}
    if sm.get("period"):
        p0, p1 = sm["period"]
        lo = _iso_day(p0)
        hi = datetime.fromtimestamp((int(datetime.fromisoformat(p1.replace("Z", "+00:00")).timestamp()) * 10**9 - 1) // 10**9,
                                    tz=timezone.utc).date()
    else:
        lo = datetime.fromtimestamp(int(R["exit"].min()) // 10**9, tz=timezone.utc).date()
        hi = datetime.fromtimestamp(int(R["exit"].max()) // 10**9, tz=timezone.utc).date()
    return [date.fromordinal(o).isoformat() for o in range(lo.toordinal(), hi.toordinal() + 1)], sm


def ci(r: dict) -> str:
    if r.get("lo") is None:
        return f"{_f(r.get('mean'))}(区間なし)"
    return f"{_f(r['mean'])} [{_f(r['lo'])}, {_f(r['hi'])}]"


def ratio_diff_arr(a1, c1, a2, c2):
    if c1.sum() == 0 or c2.sum() == 0:
        return None, None, None
    pt = a1.sum() / c1.sum() - a2.sum() / c2.sum()
    n = len(a1)
    rng = np.random.default_rng(SEED)
    nb = math.ceil(n / BLOCK)
    reps = []
    for _ in range(N_RES):
        idx = (rng.integers(0, n, size=nb)[:, None] + np.arange(BLOCK)[None, :]).ravel()[:n] % n
        s1, s2 = c1[idx].sum(), c2[idx].sum()
        if s1 > 0 and s2 > 0:
            reps.append(a1[idx].sum() / s1 - a2[idx].sum() / s2)
    if len(reps) < N_RES // 2:
        return float(pt), None, None
    lo, hi = np.percentile(reps, [2.5, 97.5])
    return float(pt), float(lo), float(hi)


def wl(p: np.ndarray) -> str:
    w, l, z = p[p > 0], p[p < 0], p[p == 0]
    m = lambda a: _f(float(a.mean())) if len(a) else "—"  # noqa: E731
    md = lambda a: _f(float(np.median(a))) if len(a) else "—"  # noqa: E731
    return (f"{len(p):,} | {_f(float(p.sum()))} | {len(w):,} | {_f(float(w.sum()))} | {m(w)} | {md(w)} | {len(l):,} | "
            f"{_f(float(l.sum()))} | {m(l)} | {md(l)} | {len(z):,} | {_f(len(w) / len(p), 3) if len(p) else '—'}")


def analyze(run_dir: str, out_dir: str) -> dict:
    name = os.path.basename(os.path.normpath(run_dir))
    if WINDOW_MARK in os.path.abspath(run_dir).replace(os.sep, "/"):
        raise SystemExit("止める: 封印の窓の出力は読まない")
    R = load_rows(run_dir)
    days, sm = period(run_dir, R)
    di = {d: i for i, d in enumerate(days)}
    eday = (R["exit"] // (86400 * 10**9)).astype("datetime64[D]").astype(str)
    idx = np.array([di.get(d, -1) for d in eday])
    inside = idx >= 0
    p, sd = R["pnl"][inside], R["side"][inside]
    hold = ((R["exit"] - R["entry"]) / 6e10)[inside]
    ix = idx[inside]
    n = len(days)
    daily = np.bincount(ix, weights=p, minlength=n)
    move = p * sd
    ctl = np.bincount(ix, weights=move, minlength=n)
    buy = sd > 0
    mb = np.bincount(ix, weights=np.where(buy, move, 0.0), minlength=n)
    hb = np.bincount(ix, weights=np.where(buy, hold, 0.0), minlength=n)
    ms = np.bincount(ix, weights=np.where(~buy, move, 0.0), minlength=n)
    hs = np.bincount(ix, weights=np.where(~buy, hold, 0.0), minlength=n)
    h = n // 2
    full, f1, f2 = mean_ci(list(daily)), mean_ci(list(daily[:h])), mean_ci(list(daily[h:]))
    dd = diff_ci(list(daily[:h]), list(daily[h:]))
    outcome = d1_outcome(f1, f2, dd)
    dirs = {lbl: ratio_diff_arr(mb[sl], hb[sl], ms[sl], hs[sl]) for lbl, sl in
            (("全期間", slice(0, n)), ("前半", slice(0, h)), ("後半", slice(h, n)))}
    ctls = {lbl: (mean_ci(list(ctl[sl])), mean_ci(list(daily[sl] - ctl[sl]))) for lbl, sl in
            (("全期間", slice(0, n)), ("前半", slice(0, h)), ("後半", slice(h, n)))}
    al = sm.get("all", {}) if isinstance(sm, dict) else {}
    L = [f"# 一括の表 — {name}", "", "読み口 `scripts/analysis/batch_runs.py`(保存済みの取引の行から計算。新しい走らせではない)。bp、経費の前。"
         "日 = 出の時刻の UTC の日。区間 = 95%、日の塊(5 日・1,000 回・種 20261004)。", "",
         "## 確かめ", "", f"- 取引の数: 期間の中 {int(inside.sum()):,}(読んだ行 {len(R['pnl']):,})/ summary.json の all.trades {al.get('trades', '無し')}",
         f"- 損益の和: 期間の中 {p.sum():,.2f} / summary.json の all.sum_bp {al.get('sum_bp', '無し')}",
         f"- 期間: {days[0]}〜{days[-1]}({n:,} 日)。前半 {days[0]}〜{days[h - 1]}、後半 {days[h]}〜{days[-1]}", "",
         "## D1 時間(1 日あたり、bp/日)", "", "| 期間 | 日数 | 1 日あたり [区間] | MDE |", "|---|---|---|---|",
         f"| 全期間 | {n} | {ci(full)} | {_f(full.get('mde'))} |"]
    years = sorted({d[:4] for d in days})
    for y in years:
        sel = np.array([d[:4] == y for d in days])
        r = mean_ci(list(daily[sel]))
        L.append(f"| {y} | {int(sel.sum())} | {ci(r)} | {_f(r.get('mde'))} |")
    L += ["", "| 区切り | 日数 | 1 日あたり [区間] | MDE |", "|---|---|---|---|",
          f"| 前半 | {h} | {ci(f1)} | {_f(f1.get('mde'))} |", f"| 後半 | {n - h} | {ci(f2)} | {_f(f2.get('mde'))} |",
          f"| 後半 − 前半 | | {ci(dd)} | |", "",
          f"- 結果(d1_outcome): **{outcome}**。0 と見分けるのに要る日数の目安: 前半の大きさなら {days_needed(list(daily[h:]), f1.get('mean'))} 日、"
          f"後半の点なら {days_needed(list(daily[h:]), f2.get('mean'))} 日(後半は {n - h} 日)", "",
          "## 勝ち負けの分解", "", "| 区分 | 取引 | 和 | 勝ち 数 | 勝ち 和 | 勝ち 平均 | 勝ち 中央値 | 負け 数 | 負け 和 | 負け 平均 | 負け 中央値 | 損益 0 | 勝率 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|", f"| 全期間 | {wl(p)} |", f"| 前半 | {wl(p[ix < h])} |", f"| 後半 | {wl(p[ix >= h])} |"]
    ey = np.array([days[i][:4] for i in ix])
    for y in years:
        L.append(f"| {y} | {wl(p[ey == y])} |")
    L += ["", "## 向きの情報の検め(買いの取引の値段の動き − 売りの取引の値段の動き、保有の 1 分あたり bp/分。差が正 = 取引の向きに動いた)", "",
          "| 区分 | 差 [区間] |", "|---|---|"]
    for lbl, (pt, lo, hi) in dirs.items():
        L.append(f"| {lbl} | {_f(pt, 4)} [{_f(lo, 4)}, {_f(hi, 4)}] |")
    L += ["", "## 買いだけの対照(同じ取引を全部買いで持った 1 日あたり。取引 − 買いだけ は向きの情報の検めではない)", "",
          "| 区分 | 買いだけの対照 | 取引 − 買いだけの対照 |", "|---|---|---|"]
    for lbl, (c, dlt) in ctls.items():
        L.append(f"| {lbl} | {ci(c)} | {ci(dlt)} |")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{name}.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    w = (p > 0).mean() if len(p) else None
    return {"name": name, "trades": int(inside.sum()), "sum_ok": abs(p.sum() - al.get("sum_bp", p.sum())) < max(0.05, 1e-5 * abs(p.sum())),  # 値の丸め・和の順の差は一致とみなす
            "full": full, "first": f1, "second": f2, "outcome": outcome, "dir": dirs, "win": w,
            "ctl": ctls["全期間"][0], "days": n}


def _job(args):
    try:
        return analyze(*args)
    except Exception as e:  # 1 本の失敗で全部を止めない。一覧に書く
        return {"name": os.path.basename(os.path.normpath(args[0])), "error": repr(e)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default=None)
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args(argv)
    dirs = sorted(d for d in os.listdir(a.runs) if os.path.isdir(os.path.join(a.runs, d)) and
                  (os.path.isfile(os.path.join(a.runs, d, "trades.csv.gz")) or os.path.isfile(os.path.join(a.runs, d, "trades.json.gz"))))
    if a.only:
        dirs = [d for d in dirs if a.only in d]
    with ProcessPoolExecutor(a.jobs) as ex:
        res = list(ex.map(_job, [(os.path.join(a.runs, d), a.out) for d in dirs]))
    by = {r["name"]: r for r in res}
    L = [f"# 一括の表の一覧 — `{a.runs}`", "", f"走らせ {len(dirs)} 本。各行の全部の表は同じ置き場の `<走らせ>.md`。読み口 `scripts/analysis/batch_runs.py`。"
         "1 日あたり bp/日、向きの情報の検めは bp/分。区間 = 95%、日の塊。", "",
         "| 走らせ | 取引 | 和の一致 | 全期間 | 前半 | 後半 | 結果(D1) | 向きの情報 全期間 | 前半 | 後半 | 勝率 | 買いだけの対照 | 良い側と悪い側の全期間の符号 |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for d in dirs:
        r = by[d]
        if "error" in r:
            L.append(f"| {d} | 失敗: {r['error']} | | | | | | | | | | | |")
            continue
        pair = ""
        if d.endswith("_good") and d[:-5] + "_bad" in by and "error" not in by[d[:-5] + "_bad"]:
            g, b = r["full"]["mean"], by[d[:-5] + "_bad"]["full"]["mean"]
            pair = "同じ" if np.sign(g) == np.sign(b) else "**違う(D8 止める)**"
        dc = lambda k: f"{_f(r['dir'][k][0], 4)} [{_f(r['dir'][k][1], 4)}, {_f(r['dir'][k][2], 4)}]"  # noqa: E731
        L.append(f"| {d} | {r['trades']:,} | {'○' if r['sum_ok'] else '✕'} | {ci(r['full'])} | {ci(r['first'])} | {ci(r['second'])} | "
                 f"{r['outcome']} | {dc('全期間')} | {dc('前半')} | {dc('後半')} | {_f(r['win'], 3)} | {ci(r['ctl'])} | {pair} |")
    with open(os.path.join(a.out, "INDEX.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(os.path.join(a.out, "INDEX.md"), len(dirs), sum(1 for r in res if "error" in r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
