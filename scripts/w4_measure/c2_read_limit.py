#!/usr/bin/env python3
"""カツオ(ヒゲ逆張り、カード 2)の指値の再現 40 本(`c2_owner_xvenue_wick/limit_sim/runs/`)の読みの表を作る。

読み方の決まり(40 本を並べて見る前に、この台本と `tests/research/test_c2_read_limit.py` で固めた。
research-protocol §0.7 の 7。weak_f5_limit_b_good と weak_f5_close_a/b の summary は、この台本を書く前に欄を確かめるために見た):

R1 比べる相手: 指値の入り方ごとに、同じ合図・同じ規則を足の終値で約定させた参照と比べる(SPEC §9「比べる相手」)。
   入り方 a(次の足の区切りで最良気配に 1 本)↔ close_a、b(合図の時点で半値に 1 本)↔ close_b、
   c(合図の時点で最良気配と半値の 2 本)↔ close_b。足の組(weak_f5・f15・f30・f60、strong_f1)の中だけで比べる。
   1 日あたりに直す(日数は各走らせの summary の `all.days`)。
R2 向きのラベル: 参照との差の符号が、良い側と悪い側で同じなら「増える / 減る(両側)」、違えば「側で割れる」、両側 0 なら「同じ」。
   大きさの境は置かない(A-12)。
R3 取り逃し: 参照なら入っていたが指値が約定しなかった取引(summary の `missed`)の数と 1 取引あたりの損益を、
   指値を置いた・置かなかったに分けて出す。取り逃しが参照の勝ちに偏っているか(逆選択)を、取り逃しの 1 取引あたりと
   参照の全取引の 1 取引あたりを並べて読む。
R4 年ごとの安定: 2018〜2023 の 6 年(2017 は 8 月から)で、年の損益の差(指値 − 参照)の符号が全期間の差の符号と同じ年の数を「n/6」。
R5 保有の長さ: 取引の記録(trades.json.gz)から保有の分を出し、[0,5)・[5,30)・[30,120)・[120,480)・[480,∞) 分で損益の和を出す
   (マチルダの K-004「保有が長い取引は負けている」と同じ切り方で、カツオでも同じかを見る)。
R6 ボラの三分位: summary の `by_vol_tercile`(K1 の境。2017 は先読みあり、2018〜2019 は境を決めた期間の中)の
   1 取引あたりの損益を、指値と参照で並べる。

出力: runs/READ/TABLES.md と read.json。数字は手で書かない(research-protocol §1.2)。

    python3 scripts/w4_measure/c2_read_limit.py [--root <runs>]
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DEFAULT_ROOT = os.path.join(REPO, "docs", "RESEARCH", "cards", "c2_owner_xvenue_wick", "limit_sim", "runs")
SIDES = ("good", "bad")
YEARS = tuple(range(2018, 2024))
HOLD_BINS_MIN = ((0, 5), (5, 30), (30, 120), (120, 480), (480, None))
REF = {"a": "close_a", "b": "close_b", "c": "close_b"}


def hold_sums(path: str) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        o = json.load(fh)
    scale = {"ns": 1e9 * 60, "s": 60.0}[o["t_unit"]]
    hold = (np.asarray(o["exit_t_ns"], dtype=float) - np.asarray(o["entry_t_ns"], dtype=float)) / scale
    pnl = np.asarray(o["pnl_bp"], dtype=float)
    out = []
    for lo, hi in HOLD_BINS_MIN:
        m = (hold >= lo) & ((hold < hi) if hi is not None else True)
        out.append({"lo": lo, "hi": hi, "trades": int(m.sum()), "sum_bp": float(pnl[m].sum())})
    return out


def load_run(d: str) -> dict:
    with open(os.path.join(d, "summary.json"), encoding="utf-8") as fh:
        s = json.load(fh)
    a = s["all"]
    days = float(a["days"])
    r = {
        "days": days,
        "trades": int(a["trades"]),
        "wins": int(a["wins"]),
        "avg_win_bp": float(a["avg_win_bp"] or 0.0),
        "avg_loss_bp": float(a["avg_loss_bp"] or 0.0),
        "per_day": {"pnl": float(a["sum_bp"]) / days, "trades": a["trades"] / days},
        "per_trade": float(a["sum_bp"]) / max(1, int(a["trades"])),
        "year_pnl": {int(y): float(v["sum_bp"]) for y, v in s["years"].items()},
        "entry_orders": a.get("entry_orders"),
        "missed": a.get("missed"),
        "by_vol": {k: v for k, v in a["by_vol_tercile"].items()},
        "exit_reasons": a.get("exit_reasons"),
    }
    tp = os.path.join(d, "trades.json.gz")
    r["hold"] = hold_sums(tp) if os.path.isfile(tp) else None
    return r


def label(dg: float, db: float) -> str:
    if dg == 0 and db == 0:
        return "同じ"
    if dg > 0 and db > 0:
        return "増える(両側)"
    if dg < 0 and db < 0:
        return "減る(両側)"
    return "側で割れる"


def year_agreement(var: dict, ref: dict) -> int:
    total = var["per_day"]["pnl"] * var["days"] - ref["per_day"]["pnl"] * ref["days"]
    sgn = np.sign(total)
    return sum(1 for y in YEARS
               if sgn != 0 and np.sign(var["year_pnl"].get(y, 0.0) - ref["year_pnl"].get(y, 0.0)) == sgn)


def compare(runs: dict) -> list[dict]:
    """runs[名前] = load_run の値。名前は <組>_limit_<入り方>_<側> と <組>_close_<入り方>。"""
    groups = sorted({n.split("_limit_")[0] for n in runs if "_limit_" in n})
    out = []
    for g in groups:
        for e in ("a", "b", "c"):
            keys = {s: f"{g}_limit_{e}_{s}" for s in SIDES}
            ref_key = f"{g}_{REF[e]}"
            if not all(k in runs for k in keys.values()) or ref_key not in runs:
                continue
            ref = runs[ref_key]
            row = {"group": g, "entry": e, "ref": ref_key}
            for ax in ("pnl", "trades"):
                dg = runs[keys["good"]]["per_day"][ax] - ref["per_day"][ax]
                db = runs[keys["bad"]]["per_day"][ax] - ref["per_day"][ax]
                row[ax] = {"d_good": dg, "d_bad": db, "label": label(dg, db)}
            row["years_good"] = year_agreement(runs[keys["good"]], ref)
            row["years_bad"] = year_agreement(runs[keys["bad"]], ref)
            out.append(row)
    return out


def _f(x: float, nd: int = 1) -> str:
    if x != 0 and abs(x) < 0.05:
        return f"{x:+.4f}"
    return f"{x:+.{nd}f}"


def render(runs: dict, rows: list[dict]) -> str:
    L = ["# カツオ(ヒゲ逆張り)の指値の再現 40 本の読みの表", "",
         "`scripts/w4_measure/c2_read_limit.py` が出した。読み方の決まり R1〜R6 はその台本の docstring。単位は bp(量 1 = 持ち高の上限に対する bp)。", ""]
    L += ["## 表 1: 走らせごとの値", "",
          "| 走らせ | 取引/日 | 損益/日 | 1 取引あたり | 勝ち率 | 平均の勝ち | 平均の負け | 入りの指値の約定の割合(1 本目 / 2 本目) |",
          "|---|---|---|---|---|---|---|---|"]
    for n in sorted(runs):
        r = runs[n]
        eo = r["entry_orders"] or {}
        fr = " / ".join(f"{(eo.get(k) or {}).get('fill_ratio'):.3f}" if (eo.get(k) or {}).get("fill_ratio") is not None else "—"
                        for k in ("ent1", "ent2"))
        L.append(f"| {n} | {r['per_day']['trades']:.2f} | {r['per_day']['pnl']:.2f} | {r['per_trade']:.2f} | "
                 f"{r['wins'] / max(1, r['trades']):.3f} | {r['avg_win_bp']:.1f} | {r['avg_loss_bp']:.1f} | {fr} |")
    L += ["", "## 表 2: 参照(足の終値で約定)との差(1 日あたり。良い側 / 悪い側)", "",
          "| 組 | 入り方 | 参照 | 取引/日の差 | 損益/日の差 | 向き | 年の一致(良 / 悪) |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['group']} | {r['entry']} | {r['ref']} | {_f(r['trades']['d_good'], 2)} / {_f(r['trades']['d_bad'], 2)} | "
                 f"{_f(r['pnl']['d_good'], 2)} / {_f(r['pnl']['d_bad'], 2)} | {r['pnl']['label']} | {r['years_good']}/6 / {r['years_bad']}/6 |")
    L += ["", "## 表 3: 取り逃し(参照なら入っていたが指値が約定しなかった取引。R3)", "",
          "| 走らせ | 参照の 1 取引あたり | 取り逃し(指値を置いた): 数・1 取引あたり・勝ち率 | 取り逃し(置かなかった): 数・1 取引あたり |",
          "|---|---|---|---|"]
    for n in sorted(k for k in runs if "_limit_" in k):
        g, rest = n.split("_limit_")
        e = rest.split("_")[0]
        ref = runs.get(f"{g}_{REF[e]}")
        m = runs[n]["missed"] or {}
        p = m.get("limit_order_placed") or {}
        q = m.get("limit_order_not_placed") or {}
        wr = p["wins"] / p["trades"] if p.get("trades") else float("nan")
        L.append(f"| {n} | {ref['per_trade']:.2f} | {p.get('trades', 0)}・{p.get('avg_bp') or 0:.2f}・{wr:.3f} | "
                 f"{q.get('trades', 0)}・{q.get('avg_bp') or 0:.2f} |")
    L += ["", "## 表 4: 保有の分ごとの損益の和(R5)", "", "| 走らせ | " + " | ".join(
        f"{lo}〜{hi if hi is not None else ''} 分" for lo, hi in HOLD_BINS_MIN) + " |", "|---|" + "---|" * len(HOLD_BINS_MIN)]
    for n in sorted(runs):
        h = runs[n]["hold"]
        if h:
            L.append(f"| {n} | " + " | ".join(f"{x['sum_bp']:.0f}({x['trades']})" for x in h) + " |")
    L += ["", "## 表 5: ボラの三分位ごとの 1 取引あたりの損益(R6。K1 の境、2017 は先読みあり)", "",
          "| 走らせ | 低 | 中 | 高 |", "|---|---|---|---|"]
    for n in sorted(runs):
        bv = runs[n]["by_vol"]
        L.append(f"| {n} | " + " | ".join(f"{(bv.get(k) or {}).get('avg_bp') or 0:.2f}({(bv.get(k) or {}).get('trades', 0)})"
                                            for k in ("low", "mid", "high")) + " |")
    L += derived_lines(runs, rows)
    return "\n".join(L) + "\n"


def derived_lines(runs: dict, rows: list[dict]) -> list[str]:
    """表 6: 報告と知見台帳に写す派生の数(40 本を並べて見た後に足した出力。読み方の決まり R1〜R6 は変えていない)。"""
    L = ["", "## 表 6: 読みに使う派生の数", ""]
    groups = sorted({n.split("_limit_")[0] for n in runs if "_limit_" in n})
    for g in groups:
        for e in ("a", "b", "c"):
            k = f"{g}_limit_{e}"
            if f"{k}_good" in runs and f"{k}_bad" in runs:
                pg, pb = runs[f"{k}_good"]["per_day"]["pnl"], runs[f"{k}_bad"]["per_day"]["pnl"]
                if pg > 0 and pb > 0:
                    L.append(f"- 損益が両側とも正: {k}(良 {pg:.2f} / 悪 {pb:.2f} bp/日、取引 {runs[f'{k}_good']['per_day']['trades']:.2f}/日)")
    for n in sorted(k for k in runs if "_limit_" in k and k.endswith("_good")):
        m = (runs[n]["missed"] or {}).get("limit_order_placed") or {}
        if m.get("trades"):
            L.append(f"- {n}: 指値を置いたが約定せず取り逃した取引の損益の和 {m['sum_bp']:.0f}bp = {m['sum_bp'] / runs[n]['days']:.2f} bp/日")
    for n in sorted(k for k in runs if "_close_a" in k):
        L.append(f"- 参照 {n}: 損益 {runs[n]['per_day']['pnl']:.2f} bp/日")
    return L


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    a = ap.parse_args(argv)
    runs = {}
    for d in sorted(os.listdir(a.root)):
        p = os.path.join(a.root, d)
        if os.path.isfile(os.path.join(p, "summary.json")):
            runs[d] = load_run(p)
    rows = compare(runs)
    out = os.path.join(a.root, "READ")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write(render(runs, rows))
    with open(os.path.join(out, "read.json"), "w", encoding="utf-8") as fh:
        json.dump({"runs": runs, "compare": rows}, fh, ensure_ascii=False, indent=1)
    print(f"runs {len(runs)} compare {len(rows)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
