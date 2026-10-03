#!/usr/bin/env python3
"""参照(weak_f<足>_close_a)の参照の行の読み方を切り替えた 6 本(c2_limit_run.py --ref-join-bitflyer・--ref-drop-no-trade)を、
段階 G と年ごとに並べる(limit_sim/runs/READ_K1YEAR/CAUSE.md の 2・3)。

    PYTHONPATH=src python3 scripts/w4_measure/c2_ref_vs_g_toggle_cmp.py predict   # 走らせの前: 写し(c2_ref_vs_g_cause の D4)で予想
    PYTHONPATH=src python3 scripts/w4_measure/c2_ref_vs_g_toggle_cmp.py table     # 走らせの後: 表

predict: c2_ref_vs_g_cause.py の写しの機械(D4)を、参照の作り方 none の代わりに join・n0・both の足の列で回し
(約定の値は参照の規則のまま)、建ての年 2019〜2022 の取引を toggle_predict.json に書く。走らせの結果を見る前に書く。
table: 6 本の走らせの trades.json.gz と、元の参照・段階 G を、c2_ref_vs_g_match.py と同じ鍵・年で突き合わせる。
各升 = 取引の数・損益の和・段階 G との共通・この走らせだけ・段階 G だけ・差(この走らせ − 段階 G)。
予想(toggle_predict.json)と走らせの取引が、鍵・出の時刻・損益(1e-3 bp)で一致するかも出す。
出力: limit_sim/runs/READ_K1YEAR/CAUSE_TABLES2.md と toggle_cmp.json。
"""
from __future__ import annotations

import gzip
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import c2_ref_vs_g_cause as cz  # noqa: E402
import c2_ref_vs_g_match as mm  # noqa: E402

OUT = cz.OUT_DIR
# 名前の後ろ → (作り方, 説明)
VARIANTS = (("", cz.NONE, "参照(切り替えなし)"),
            ("_refjoin", cz.JOIN, "(a) 内部結合だけ"),
            ("_refn0", cz.N0, "(b) 約定の無い分を落とすだけ"),
            ("_refjoin_n0", (True, True), "(a)+(b)"))
NS = mm.NS


def run_dir(f: int, suffix: str) -> str:
    return os.path.join(mm.RUNS, f"weak_f{f}_close_a{suffix}")


def predict() -> int:
    b = cz.load_binance(0, cz.READ_HI)
    bf = cz.load_bitflyer(0, cz.READ_HI)
    bfv = {"t": bf["t"][bf["v"] > 0], "c": bf["c"][bf["v"] > 0]}
    bfv_ref = {"t": bfv["t"][bfv["t"] >= cz.REF_LO], "c": bfv["c"][bfv["t"] >= cz.REF_LO]}
    out = {}
    for f in mm.FEET:
        for suffix, cons, _d in VARIANTS[1:]:
            # 参照の足の作り方(区切り = 参照の式)に切り替えを当てる。both の作り方は区切りの式が段階 G なので、
            # ここでは参照の式で作り直す(2019〜2022 年は分の頭に無い行が 0 なので同じ。cause.json の data_facts)
            bars = build_ref_bars(b, bf["t"], f * 60, cons)
            tr, _st = cz.machine(bars, cz.ref_price_fn(bars, bfv_ref))
            out[f"{f}{suffix}"] = [(e * NS, s, x * NS, cz.pnl(s, p0, p1)) for e, s, x, p0, p1 in tr
                                   if mm.year_of(e * NS, f) in mm.YEARS]
    with open(os.path.join(OUT, "toggle_predict.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh)
    print(f"-> {OUT}/toggle_predict.json")
    return 0


def build_ref_bars(b, bf_t, F, cons):
    if cons != (True, True):
        return cz.build_bars(b, bf_t, F, cons, cz.REF_LO)
    # 参照の式の区切りで join + n0
    join_only = dict(b)
    m = b["nt"] > 0
    for k in ("t", "o", "h", "l", "c", "nt"):
        join_only[k] = b[k][m]
    return cz.build_bars(join_only, bf_t, F, cz.JOIN, cz.REF_LO)


def load_run(d: str) -> list:
    with gzip.open(os.path.join(d, "trades.json.gz"), "rt", encoding="utf-8") as fh:
        return mm.ref_trades(json.load(fh))


def table() -> int:
    cells = json.load(open(os.path.join(mm.G_DIR, "cells.json"), encoding="utf-8"))
    pred_p = os.path.join(OUT, "toggle_predict.json")
    pred = json.load(open(pred_p, encoding="utf-8")) if os.path.exists(pred_p) else {}
    res = {}
    L = ["# カツオ: 参照の行の読み方を切り替えた走らせと段階 G の年ごとの比べ(台本の出力)", "",
         "`PYTHONPATH=src python3 scripts/w4_measure/c2_ref_vs_g_toggle_cmp.py table` が出した。年 = 建てた足の始まりの年。"
         "損益は経費の前の bp。突き合わせの鍵 = (建ての時刻, 向き)(c2_ref_vs_g_match.py の R1・R2)。", ""]
    for f in mm.FEET:
        rid = cells[f"design|full|{f}|s19/b24|weak"]["run_id"]
        with gzip.open(os.path.join(mm.G_RUNS, rid, "trades.json.gz"), "rt", encoding="utf-8") as fh:
            g = mm.g_trades(json.load(fh)["data"])
        L += [f"## {f} 分", "",
              "| 走らせ | 年 | 取引 | 損益の和 | 段階 G 取引 | 段階 G 損益の和 | 共通 | この走らせだけ | 段階 G だけ | 差(この走らせ − 段階 G) | 共通で出が違う本数 |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for suffix, _cons, desc in VARIANTS:
            d = run_dir(f, suffix)
            if not os.path.exists(os.path.join(d, "trades.json.gz")):
                L.append(f"| {desc}(`{os.path.basename(d)}`) | — | 走らせの出力が無い | | | | | | | | |")
                continue
            r = load_run(d)
            for y in mm.YEARS:
                ry = [t for t in r if mm.year_of(t[0], f) == y]
                gy = [t for t in g if mm.year_of(t[0], f) == y]
                m = mm.match_year(ry, gy)
                m.update({"n": len(ry), "sum_bp": math.fsum(t[3] for t in ry), "g_n": len(gy),
                          "g_sum_bp": math.fsum(t[3] for t in gy)})
                res[f"{f}{suffix}|{y}"] = m
                L.append(f"| {desc}(`{os.path.basename(d)}`) | {y} | {m['n']:,} | {m['sum_bp']:+,.2f} | {m['g_n']:,} | "
                         f"{m['g_sum_bp']:+,.2f} | {m['common_n']:,} | {m['r_only_n']} | {m['g_only_n']} | {m['diff_bp']:+,.2f} | "
                         f"{m['common_exit_differs_n']} |")
            if suffix and f"{f}{suffix}" in pred:
                p = {(t[0], t[1]): t for t in pred[f"{f}{suffix}"]}
                rr = {(t[0], t[1]): t for t in r if mm.year_of(t[0], f) in mm.YEARS}
                bad = sum(1 for k in set(p) | set(rr) if k not in p or k not in rr or p[k][2] != rr[k][2]
                          or abs(p[k][3] - rr[k][3]) > 1e-3)
                res[f"{f}{suffix}|predict_mismatch"] = bad
                L.append(f"| 予想との一致(`toggle_predict.json`、2019〜2022) | | 走らせ {len(rr):,} 本・予想 {len(p):,} 本・"
                         f"一致しない鍵 {bad} | | | | | | | | |")
        L.append("")
    # どの切り替えで段階 G に近づくか: 差(走らせ − 段階 G)と、片側だけの本数(この走らせだけ + 段階 G だけ)
    L += ["## 切り替えごとの、段階 G との差と片側だけの本数", "",
          "升 = 損益の差(この走らせ − 段階 G、bp)/ 片側だけの本数(この走らせだけ + 段階 G だけ)。「—」= 走らせの出力が無い。", "",
          "| 足 | 年 | " + " | ".join(d for _s, _c, d in VARIANTS) + " |", "|---|---|" + "---|" * len(VARIANTS)]
    for f in mm.FEET:
        for y in mm.YEARS:
            cs = []
            for suffix, _c, _d in VARIANTS:
                m = res.get(f"{f}{suffix}|{y}")
                cs.append("—" if m is None else f"{m['diff_bp']:+,.2f} / {m['r_only_n'] + m['g_only_n']}")
            L.append(f"| {f} 分 | {y} | " + " | ".join(cs) + " |")
    L.append("")
    with open(os.path.join(OUT, "CAUSE_TABLES2.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    with open(os.path.join(OUT, "toggle_cmp.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(f"-> {OUT}/CAUSE_TABLES2.md")
    return 0


if __name__ == "__main__":
    sys.exit(predict() if sys.argv[1:] == ["predict"] else table() if sys.argv[1:] == ["table"] else 2)
