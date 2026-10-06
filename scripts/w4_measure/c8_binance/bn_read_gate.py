#!/usr/bin/env python3
"""部品 4: 門の読み方の台本。部品 3 の出力(daily.csv・daily_mid.csv・diagnostics.json・boundary_carry_days.csv)と
部品 2 の区分(classes.json)を読み、数を全部この台本が出す(手で書かない)。段 1 では作り物でしか動かさない。

    PYTHONPATH=src python3 scripts/w4_measure/c8_binance/bn_read_gate.py --run-dir <部品 3 の出力> --classes <classes.json> --out <置き場>

決まり(結果を見る前に、この台本と tests/research/test_c8_binance.py で固める):
  G0 母数 = 区分のある日(classes.json の日)のうち、daily.csv に行のある日。区分の無い日は数えない。
     区分があって daily.csv に行の無い日の数は別に出す(その日は母数に入れない)。
  G1 門の形 3 つ(日 d の区分 = 前の日 d − 1 の荒れ具合。classify の出したまま):
       門なし: 母数の日の全部に入る。
       A: 区分が high の日だけ入る。ほかの日の損益は 0。
       B: 区分が low の日は入らない(損益 0)。ほかの日はそのまま。
  G2 形ごと: 「全部の日に均した」= 母数の日の全部(入らない日は 0)の 1 日あたり・95% 区間・MDE、
     「入った日だけ」= 入った日の 1 日あたり・区間・MDE、入った日の数・母数のうちの割合。
     A と B に順位は付けない(全部の日に均した値は 0 の日の割合が違うので、A と B を比べる物差しにしない)。
  G3 差: A − 門なし、B − 門なし = 同じ日どうしの差の系列(母数の日)の 1 日あたり・区間・MDE。
  G4 区分ごとの表: low / mid / high × 全期間・前半・後半の、門なしの 1 日あたり・区間。
  G5 全部を、始値 → 始値(daily.csv)と中ほど(daily_mid.csv)の両方で。前半・後半にも分ける
     (境 = classes.json の half_boundary_day。その日から後半)。
  G6 区間 = 日の塊のブートストラップ: bot.bt.validation.block_bootstrap_ci(method "circular"、塊 5 日、1,000 回、
     種 20261006、統計量 = 平均、95% 百分位)。日の系列は日付順(入った日だけのときは入った日を日付順に詰めた列)。
     se = 再標本の平均の標準偏差(ddof 1)。MDE = 2.8 × se(委任文の式。5% 両側・80%)。日が 5 日未満なら塊 = 日数、
     2 日未満なら区間なし。
  G7 読みの結果の印(値は段 2 まで出ない): 各差の区間が 0 より上 / 0 を含む / 0 より下(mark)。
  G8 セッションをまたいだ持ち高: diagnostics.json の 5_boundary_carry(回数・その決定の損益の和)をそのまま写し、
     boundary_carry_days.csv の day(またいだ持ち高の損益が乗った日)を母数から外した A − 門なし・B − 門なし も並べる
     (中ほども同じ日を外す。またいだ決定の損益は始値でも中ほどでも同じ日に乗る)。
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

import numpy as np

from bot.bt.validation import block_bootstrap_ci  # noqa: E402

SEED = 20261006
N_RES = 1000
BLOCK = 5
MDE_K = 2.8  # 委任文「MDE = 2.8 × 標準誤差(5% 両側・80%)」の 2.8 のまま(z_0.975 + z_0.80 = 2.8016 とは丸めの差がある)
FORMS = ("none", "A", "B")
CLASSES = ("low", "mid", "high")
PRICES = {"open": "daily.csv", "mid": "daily_mid.csv"}


def read_daily(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    if not lines or lines[0] != "day,pnl_bp,n":
        raise ValueError(f"{path}: daily.csv の形でない")
    return {ln.split(",")[0]: float(ln.split(",")[1]) for ln in lines[1:]}


def read_carry_days(path: str) -> set:
    with open(path, encoding="utf-8") as fh:
        return {r["day"] for r in csv.DictReader(fh)}


def enters(form: str, c: str) -> bool:
    if form == "none":
        return True
    if form == "A":
        return c == "high"
    if form == "B":
        return c != "low"
    raise ValueError(form)


def gated(days: list, pnl: dict, cls: dict, form: str) -> np.ndarray:
    """母数の日(日付順)の門ありの損益(入らない日は 0)。"""
    return np.array([pnl[d] if enters(form, cls[d]) else 0.0 for d in days], dtype=float)


def stat(x) -> dict:
    """1 日あたり・95% 区間・se・MDE(G6)。"""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n == 0:
        return {"n_days": 0, "per_day_bp": None, "ci": None, "se": None, "mde": None}
    if n < 2:
        return {"n_days": n, "per_day_bp": float(x.mean()), "ci": None, "se": None, "mde": None}
    ci = block_bootstrap_ci(x.tolist(), block_len=min(BLOCK, n), n_resamples=N_RES, seed=SEED, alpha=0.05,
                            method="circular", statistic="mean")
    return {"n_days": n, "per_day_bp": float(x.mean()), "ci": [ci.lo, ci.hi], "se": ci.se, "mde": MDE_K * ci.se}


def mark(ci) -> str | None:
    """G7: 区間が 0 より上 / 0 を含む / 0 より下。"""
    if ci is None:
        return None
    lo, hi = ci
    if lo > 0:
        return "0 より上"
    if hi < 0:
        return "0 より下"
    return "0 を含む"


def read_block(days: list, pnl: dict, cls: dict, n_universe: int | None = None) -> dict:
    """1 つの母数(日の並び)で、形ごと(G2)・差(G3)・印(G7)。"""
    n_u = len(days) if n_universe is None else n_universe
    base = gated(days, pnl, cls, "none")
    out = {"n_days": len(days), "forms": {}, "diffs": {}}
    for f in FORMS:
        g = gated(days, pnl, cls, f)
        ent = [i for i, d in enumerate(days) if enters(f, cls[d])]
        out["forms"][f] = {"all_days": stat(g), "entered_days": stat(g[ent]) if ent else stat([]),
                           "n_entered": len(ent), "entered_share": (len(ent) / n_u) if n_u else None}
    for f in ("A", "B"):
        s = stat(gated(days, pnl, cls, f) - base)
        s["mark"] = mark(s["ci"])
        out["diffs"][f"{f}-none"] = s
    return out


def by_class(days: list, pnl: dict, cls: dict) -> dict:
    """G4: 区分ごとの門なしの 1 日あたり・区間。"""
    out = {}
    for k in CLASSES:
        x = [pnl[d] for d in days if cls[d] == k]
        s = stat(x)
        out[k] = {"n_days": s["n_days"], "per_day_bp": s["per_day_bp"], "ci": s["ci"]}
    return out


def read_all(pnls: dict, cls: dict, boundary: str, carry_days: set, carry_diag: dict | None) -> dict:
    """pnls: {"open": 日 → 損益, "mid": 日 → 損益}。"""
    out = {"rules": __doc__, "seed": SEED, "n_resamples": N_RES, "block_days": BLOCK, "mde_k": MDE_K,
           "half_boundary_day": boundary, "prices": {}}
    for price, pnl in pnls.items():
        univ = sorted(d for d in cls if d in pnl)
        parts = {"all": univ, "first_half": [d for d in univ if d < boundary],
                 "second_half": [d for d in univ if d >= boundary]}
        r = {"n_classified": len(cls), "n_classified_without_daily_row": sum(1 for d in cls if d not in pnl),
             "n_daily_rows_without_class": sum(1 for d in pnl if d not in cls)}
        for pn, ds in parts.items():
            r[pn] = read_block(ds, pnl, cls)
            r[pn]["by_class"] = by_class(ds, pnl, cls)
            kept = [d for d in ds if d not in carry_days]
            ex = read_block(kept, pnl, cls)
            r[pn]["without_carry_days"] = {"n_days": len(kept), "n_removed": len(ds) - len(kept),
                                           "diffs": ex["diffs"]}
        out["prices"][price] = r
    out["boundary_carry"] = {"from_diagnostics": carry_diag, "n_carry_days": len(carry_days),
                             "n_carry_days_in_universe": sum(1 for d in carry_days if d in cls)}
    return out


def fmt(s: dict) -> str:
    if s.get("per_day_bp") is None:
        return "—"
    t = f"{s['per_day_bp']:+.3f}"
    if s.get("ci"):
        t += f" [{s['ci'][0]:+.3f}, {s['ci'][1]:+.3f}]"
    if s.get("mde") is not None:
        t += f" MDE {s['mde']:.3f}"
    return t


def to_md(res: dict) -> str:
    L = ["# カード 8 の門(Binance)の読み", "", "`scripts/w4_measure/c8_binance/bn_read_gate.py` が出した。bp、経費の前。"
         "決まりは台本の docstring(G0〜G8)。A と B に順位は付けない。", "",
         f"前半・後半の境(後半の最初の日): {res['half_boundary_day']}", ""]
    J = {"all": "全期間", "first_half": "前半", "second_half": "後半"}
    for price, r in res["prices"].items():
        L += [f"## 約定 = {'始値 → 始値(daily.csv)' if price == 'open' else '中ほど(daily_mid.csv)'}", "",
              f"区分のある日 {r['n_classified']}・そのうち daily の行の無い日 {r['n_classified_without_daily_row']}", "",
              "| 期間 | 形 | 全部の日に均した 1 日あたり [区間] | 入った日だけ [区間] | 入った日の数 | 割合 |", "|---|---|---|---|---|---|"]
        for pn in ("all", "first_half", "second_half"):
            for f in FORMS:
                x = r[pn]["forms"][f]
                L.append(f"| {J[pn]} | {f} | {fmt(x['all_days'])} | {fmt(x['entered_days'])} | {x['n_entered']} | "
                         f"{x['entered_share']:.4f} |" if x["entered_share"] is not None else f"| {J[pn]} | {f} | — | — | 0 | — |")
        L += ["", "| 期間 | 差 | 1 日あたり [区間] | 印 | またぎの日を外した 1 日あたり [区間](外した日数) | 印 |", "|---|---|---|---|---|---|"]
        for pn in ("all", "first_half", "second_half"):
            w = r[pn]["without_carry_days"]
            for k in ("A-none", "B-none"):
                a, b = r[pn]["diffs"][k], w["diffs"][k]
                L.append(f"| {J[pn]} | {k} | {fmt(a)} | {a['mark']} | {fmt(b)}({w['n_removed']}) | {b['mark']} |")
        L += ["", "| 期間 | low [区間] | mid [区間] | high [区間] |", "|---|---|---|---|"]
        for pn in ("all", "first_half", "second_half"):
            c = r[pn]["by_class"]
            L.append(f"| {J[pn]} | " + " | ".join(f"{fmt(c[k])}({c[k]['n_days']})" for k in CLASSES) + " |")
        L.append("")
    bc = res["boundary_carry"]
    L += ["## セッションをまたいだ持ち高", "", f"diagnostics.json の 5_boundary_carry: {json.dumps(bc['from_diagnostics'], ensure_ascii=False)}",
          f"またぎのあった日の数: {bc['n_carry_days']}(区分のある日のうち {bc['n_carry_days_in_universe']})", ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--classes", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    with open(a.classes, encoding="utf-8") as fh:
        cj = json.load(fh)
    pnls = {k: read_daily(os.path.join(a.run_dir, f)) for k, f in PRICES.items()}
    with open(os.path.join(a.run_dir, "diagnostics.json"), encoding="utf-8") as fh:
        dg = json.load(fh).get("5_boundary_carry")
    carry = read_carry_days(os.path.join(a.run_dir, "boundary_carry_days.csv"))
    res = read_all(pnls, cj["classes"], cj["half_boundary_day"], carry, dg)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "gate_read.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, allow_nan=False)
    with open(os.path.join(a.out, "GATE_READ.md"), "w", encoding="utf-8") as fh:
        fh.write(to_md(res) + "\n")
    print(f"-> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
