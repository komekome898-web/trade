#!/usr/bin/env python3
"""K1 段階 G: 当時の値を機械で読む(2 通り)。

読み 1(--json): results/PHASE2/K1/xvenue/effect_*.json と results/PHASE2/K1/binance/effect_flip_noinval_delay.json
  の升(年別 per_year の n・mean_bp、期間の n・mean_bp・ci95_bp)を docs/PHASE2/K1/NEWENV_G/old_values.json に書く。
読み 2(--check): results/PHASE2/K1/xvenue/XVENUE_TABLES.md の表 (a)(年別の n・平均・総損益、期間の行)と
  表 (b)(78 升 × 年の総損益 (n))を、見出しの文字で区切って本文から読み、読み 1 と突き合わせる。
  読み 1 とコードを共有しない(段階 A の scripts/k1_newenv_check_parse_old.py と同じ考え)。
  結果を docs/PHASE2/K1/NEWENV_G/check_parse_old.txt に書く。
"""
from __future__ import annotations

import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
XV = os.path.join(REPO, "results", "PHASE2", "K1", "xvenue")
OUT = os.path.join(REPO, "docs", "PHASE2", "K1", "NEWENV_G")
FILES = {
    "design|full": "effect_binance_to_bitflyer.json",
    "design|2018_2021": "effect_binance_to_bitflyer_2018_2021.json",
    "design|2022_2026": "effect_binance_to_bitflyer_2022_2026.json",
    "sameclose|full": "effect_binance_to_bitflyer_sameclose.json",
    "sameclose|2018_2021": "effect_binance_to_bitflyer_sameclose_2018_2021.json",
    "sameclose|2022_2026": "effect_binance_to_bitflyer_sameclose_2022_2026.json",
    "single_unjoined|full": "../binance/effect_flip_noinval_delay.json",
}


def read_json() -> None:
    out = {}
    for tag, name in FILES.items():
        path = os.path.normpath(os.path.join(XV, name))
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        for ck, c in d["cells"].items():
            out[f"{tag}|{ck}"] = {"file": os.path.relpath(path, REPO), "explore": d.get("explore"), "n": c["n"],
                                  "mean_bp": c["mean_bp"], "ci95_bp": c.get("ci95_bp"), "per_year": c["per_year"]}
    with open(os.path.join(OUT, "old_values.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=0, sort_keys=True)
    print(f"old_values.json cells {len(out)}")


def num(s: str) -> float:
    return float(s.replace(",", "").replace("+", "").replace("*", ""))


def check() -> None:
    with open(os.path.join(OUT, "old_values.json"), encoding="utf-8") as fh:
        old = json.load(fh)
    text = open(os.path.join(XV, "XVENUE_TABLES.md"), encoding="utf-8").read()
    lines = []
    mism = 0
    read = 0
    # 表 (a): 「### 表 (a)」から「### 表 (b)」まで。足の段は「5 分」「15 分」の見出し語の順に現れる
    a = text.split("### 表 (a)")[1].split("### 表 (b)")[0]
    blocks = re.split(r"\n(?=\| 年 \| n \|)", a)[1:]
    for foot, blk in zip((5, 15), blocks):
        for m in re.finditer(r"^\| (20\d\d) \| ([\d,]+) \| ([+-]?[\d.]+) \| ([+-]?[\d,]+) \|", blk, re.M):
            y, n, mean, tot = m.group(1), int(num(m.group(2))), num(m.group(3)), num(m.group(4))
            o = old[f"design|full|{foot}|s19/b24|weak"]["per_year"].get(y)
            read += 1
            ok = o is not None and o["n"] == n and abs(o["mean_bp"] - mean) <= 0.005 + 1e-9
            if not ok:
                mism += 1
                lines.append(f"MISMATCH (a) {foot} {y}: table n {n} mean {mean} / json {o}")
        for m in re.finditer(r"^\| (2018-2021|2022-2026) \| ([+-]?[\d.]+)\*? \[([+-]?[\d.]+), ([+-]?[\d.]+)\] \|.*\| ([\d,]+) \|$", blk, re.M):
            rg = m.group(1).replace("-", "_")
            o = old[f"design|{rg}|{foot}|s19/b24|weak"]
            read += 1
            ok = (o["n"] == int(num(m.group(5))) and abs(o["mean_bp"] - num(m.group(2))) <= 0.005 + 1e-9
                  and abs(o["ci95_bp"][0] - num(m.group(3))) <= 0.005 + 1e-9 and abs(o["ci95_bp"][1] - num(m.group(4))) <= 0.005 + 1e-9)
            if not ok:
                mism += 1
                lines.append(f"MISMATCH (a) period {foot} {rg}: {m.group(0)} / json {o['n']} {o['mean_bp']} {o['ci95_bp']}")
    # 表 (b): 「**2022**」「**2023**」… の見出しで区切る
    b = text.split("### 表 (b)")[1].split("### 表 (c)")[0]
    parts = re.split(r"\n\*\*(20\d\d)\*\*\n", b)
    feet_of = {"1 分": 1, "3 分": 3, "5 分": 5, "15 分": 15, "30 分": 30, "60 分": 60}
    src_hits = {"design|full": 0, "design|2022_2026": 0}
    for y, body in zip(parts[1::2], parts[2::2]):
        for m in re.finditer(r"^\| `([^`]+)` \| (\d+ 分) \| ([+-]?[\d,]+) \(([\d,]+)\) \|", body, re.M):
            g, foot, tot, n = m.group(1), feet_of[m.group(2)], num(m.group(3)), int(num(m.group(4)))
            read += 1
            found = []
            for src in src_hits:
                o = old.get(f"{src}|{foot}|{g}|weak", {}).get("per_year", {}).get(y)
                if o and o["n"] == n and abs(o["n"] * o["mean_bp"] - tot) <= 0.5 + o["n"] * 0.0005:
                    found.append(src)
                    src_hits[src] += 1
            if not found:
                mism += 1
                lines.append(f"MISMATCH (b) {y} {g} {foot}: {tot} ({n})")
    lines.append(f"(b) rows that agree with each json source: {src_hits}")
    lines.append(f"cells read {read}")
    lines.append(f"mismatches {mism}")
    with open(os.path.join(OUT, "check_parse_old.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines[-3:]))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    if "--check" in sys.argv:
        check()
    else:
        read_json()
