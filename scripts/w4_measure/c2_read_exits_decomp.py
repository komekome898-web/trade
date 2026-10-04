#!/usr/bin/env python3
"""カツオの長い保有の降り方の差を、取引を 1 本ずつ突き合わせて分ける(関門 ② の 1 回目の止める 1・直す 2 を受けて足した)。

`runs/READ_EXITS/RESULTS.md` の監査(`docs/AUDITOR/VERDICTS/2026-10-04_c2_exits_read.md`)の後に足した。R1〜R5・R2b は変えていない。

鍵 = (建ての時刻 entry_t_ns, 向き)。降り方なし(weak_f<足>_close_a)と降り方あり(…_stop<k> / …_time<N>)の取引を突き合わせ、
  差の和 = 共通の取引の損益の差の和 + 降り方ありにだけある取引の和 − 降り方なしにだけある取引の和
に分ける。共通の取引は、降り方ありの側の終わり方が新しい降り方(値段で降りる・時間で降りる)かどうかでも分ける
(trades.csv.gz の exit_reason。trades.csv.gz と trades.json.gz の行は同じ並び)。
さらに、共通で新しい降り方で閉じた取引を、降り方なしの側の保有の帯で分け、降り方なし・ありの損益の和を並べる。
すべて bp の和と、2,313 日で割った 1 日あたり(日数は summary の all.days)。経費なし。

    python3 scripts/w4_measure/c2_read_exits_decomp.py [--root <runs>]
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c2_read_exits as rx  # noqa: E402
import c2_read_limit as rl  # noqa: E402

NEW = set(rx.NEW_EXITS)


def load(d: str, with_reason: bool) -> list[tuple]:
    """(鍵, 損益, 保有の分, 新しい降り方で閉じたか)。"""
    with gzip.open(os.path.join(d, "trades.json.gz"), "rt", encoding="utf-8") as fh:
        o = json.load(fh)
    reasons = None
    if with_reason:
        with gzip.open(os.path.join(d, "trades.csv.gz"), "rt", encoding="utf-8", newline="") as fh:
            reasons = [r["exit_reason"] for r in csv.DictReader(fh)]
        assert len(reasons) == len(o["pnl_bp"]), d
    scale = {"ns": 1e9 * 60, "s": 60.0}[o["t_unit"]]
    out = []
    for i in range(len(o["pnl_bp"])):
        hold = (o["exit_t_ns"][i] - o["entry_t_ns"][i]) / scale
        out.append(((int(o["entry_t_ns"][i]), int(o["side"][i])), float(o["pnl_bp"][i]), hold,
                    bool(reasons and reasons[i] in NEW)))
    return out


def band_of(hold: float) -> str:
    for lo, hi in rl.HOLD_BINS_MIN:
        if hold >= lo and (hi is None or hold < hi):
            return f"{lo}〜{hi}" if hi is not None else f"{lo}〜"
    return "?"


def decomp(base: list[tuple], var: list[tuple]) -> dict:
    B, V = {}, {}
    for t in base:
        B.setdefault(t[0], []).append(t)
    for t in var:
        V.setdefault(t[0], []).append(t)
    common, bo, vo = [], [], []
    for k in set(B) | set(V):
        x, y = B.get(k, []), V.get(k, [])
        n = min(len(x), len(y))
        common += list(zip(x[:n], y[:n]))
        bo += x[n:]
        vo += y[n:]
    cut = [(b, v) for b, v in common if v[3]]
    bands: dict = {}
    for b, v in cut:
        g = bands.setdefault(band_of(b[2]), {"n": 0, "base": 0.0, "var": 0.0})
        g["n"] += 1
        g["base"] += b[1]
        g["var"] += v[1]
    return {
        "total": math.fsum(t[1] for t in var) - math.fsum(t[1] for t in base),
        "common_n": len(common), "common_diff": math.fsum(v[1] - b[1] for b, v in common),
        "common_cut_n": len(cut), "common_cut_diff": math.fsum(v[1] - b[1] for b, v in cut),
        "var_only_n": len(vo), "var_only": math.fsum(t[1] for t in vo),
        "base_only_n": len(bo), "base_only": math.fsum(t[1] for t in bo),
        "cut_by_base_band": bands,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=rl.DEFAULT_ROOT)
    a = ap.parse_args(argv)
    names = {n for n in os.listdir(a.root) if os.path.isfile(os.path.join(a.root, n, "summary.json"))}
    out = {}
    L = ["# カツオ: 長い保有の降り方の差を取引 1 本ずつの突き合わせで分ける", "",
         "`scripts/w4_measure/c2_read_exits_decomp.py` が出した(関門 ② の 1 回目の後に足した)。経費の前。bp の和(括弧は 1 日あたり)。", "",
         "## 表 A: 差の和 = 共通の取引の差 + 降り方ありにだけある取引 − 降り方なしにだけある取引", "",
         "| 降り方あり | 差の和 | 共通 本数・差 | うち新しい降り方で閉じた 本数・差 | 降り方ありにだけ 本数・和 | 降り方なしにだけ 本数・和 |",
         "|---|---|---|---|---|---|"]
    B = []
    for x, b in rx.pairs(names):
        days = json.load(open(os.path.join(a.root, b, "summary.json"), encoding="utf-8"))["all"]["days"]
        r = decomp(load(os.path.join(a.root, b), False), load(os.path.join(a.root, x), True))
        r["days"] = days
        out[x] = r
        d = lambda v: f"{v:+,.0f}({v / days:+.2f})"  # noqa: E731
        L.append(f"| {x} | {d(r['total'])} | {r['common_n']:,}・{d(r['common_diff'])} | {r['common_cut_n']:,}・{d(r['common_cut_diff'])} | "
                 f"{r['var_only_n']:,}・{d(r['var_only'])} | {r['base_only_n']:,}・{d(r['base_only'])} |")
        for band, g in r["cut_by_base_band"].items():
            B.append(f"| {x} | {band} 分 | {g['n']:,} | {g['base']:+,.0f} | {g['var']:+,.0f} | {g['var'] - g['base']:+,.0f} |")
    L += ["", "## 表 B: 共通で新しい降り方で閉じた取引を、降り方なしの側の保有の帯で分けた損益の和", "",
          "| 降り方あり | 降り方なしの保有の帯 | 本数 | 降り方なしの和 | 降り方ありの和 | 差 |", "|---|---|---|---|---|---|"] + sorted(B)
    od = os.path.join(a.root, "READ_EXITS")
    with open(os.path.join(od, "DECOMP.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    with open(os.path.join(od, "decomp.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"-> {od}/DECOMP.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
