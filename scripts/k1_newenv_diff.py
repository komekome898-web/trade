#!/usr/bin/env python3
"""K1 stage A (2026-09-27, L-479): the cell-by-cell comparison of RESULT.md 第 2 部
(tables 2.1-2.4, the values K1 reported in 2026-09-09) with the new environment's
values (docs/PHASE2/K1/NEWENV_A/cells.json, made by scripts/k1_newenv_tables.py).

The old values are read from the markdown tables of docs/PHASE2/K1/RESULT.md
(lines of the form `| \`s19/b24\`(当時の規則) | +0.53 | ... |`) and are used as a
DIFFERENCE DETECTOR only (L-479a): a cell where the two numbers agree is written
「一致」= the fact that the numbers are the same, never as a proof of correctness.
A cell where they differ is written 「差」 with the size, and the judgement column is
left to the worker's investigation (DIFF.md is generated here as the table, the
judgements are added by hand in the same file's §2 with their evidence).

Usage: PYTHONPATH=src python3 scripts/k1_newenv_diff.py  -> docs/PHASE2/K1/NEWENV_A/diff_table.md + old_values.json
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from bot.strategy.k1_wick import gate_label, gates  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RESULT = os.path.join(REPO, "docs", "PHASE2", "K1", "RESULT.md")
OUT_DIR = os.path.join(REPO, "docs", "PHASE2", "K1", "NEWENV_A")
FEET = (1, 3, 5, 15, 30, 60)
SECTIONS = {"2.1": "both", "2.2": "strong", "2.3": "weak"}
TOL_BP = 0.005  # the tables print 2 decimals: |old - new| <= 0.005 is the same printed number


def parse_old() -> dict:
    with open(RESULT, "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    old, sec = {}, None
    n24 = {}
    for ln in lines[131:243]:
        m = re.match(r"^## (2\.\d)", ln)
        if m:
            sec = m.group(1)
            continue
        if not ln.startswith("|") or sec is None:
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) != 7 or cells[0] in ("門", "---"):
            continue
        g = re.sub(r"[`*]|\(当時の規則\)", "", cells[0]).strip()
        if sec in SECTIONS:
            for f, v in zip(FEET, cells[1:]):
                star = "*" in v
                num = float(re.sub(r"[^0-9.+-]", "", v))
                old[f"{f}|{g}|{SECTIONS[sec]}"] = {"mean_bp": num, "star": star}
        elif sec == "2.4":
            for f, v in zip(FEET, cells[1:]):
                n, h = v.split("/")
                n24[f"{f}|{g}|both"] = {"n": int(n.replace(",", "").strip()), "hold_median": int(h.strip())}
    return {"means": old, "n_hold": n24, "exit_reasons": parse_25(lines), "per_year": parse_26(lines)}


def parse_25(lines) -> dict:
    """2.5: exit reason shares (%) for s19/b24, strength both, per foot."""
    out, on = {}, False
    for ln in lines[131:243]:
        if ln.startswith("## 2.5"):
            on = True
            continue
        if ln.startswith("## ") and on:
            break
        m = re.match(r"^\| (\d+) 分 \| ([^|]+) \| ([^|]+) \| ([^|]+) \|", ln) if on else None
        if m:
            vals = [float(re.sub(r"[^0-9.]", "", v)) for v in m.groups()[1:]]
            out[f"{m.group(1)}|s19/b24|both"] = dict(zip(("invalidated", "opposite_weak", "reversed"), vals))
    return out


def parse_26(lines) -> dict:
    """2.6: per-year means (2017 / 2018 / 2019, 1 decimal) for 4 gates x feet 3/5/15/60, strength strong."""
    out, on, feet = {}, False, (3, 5, 15, 60)
    for ln in lines[131:243]:
        if ln.startswith("## 2.6"):
            on = True
            continue
        if ln.startswith("## ") and on:
            break
        if on and ln.startswith("| s"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            g = cells[0]
            for f, v in zip(feet, cells[1:]):
                ys = [float(re.sub(r"[^0-9.+-]", "", x.replace("\u2212", "-"))) for x in v.split("/")]
                out[f"{f}|{g}|strong"] = dict(zip(("2017", "2018", "2019"), ys))
    return out


def main() -> None:
    old = parse_old()
    with open(os.path.join(OUT_DIR, "cells.json"), "r", encoding="utf-8") as fh:
        new = json.load(fh)
    with open(os.path.join(OUT_DIR, "old_values.json"), "w", encoding="utf-8") as fh:
        json.dump(old, fh, ensure_ascii=False, indent=1, sort_keys=True)
    rows = ["| 升(足\\|門\\|強さ) | 当時 mean(r) bp | 新 mean(r) bp | 差(新−当時) | 当時 `*` / 新 `*` | 数の比較 |",
            "|---|---|---|---|---|---|"]
    same = diff = unmeasured = 0
    diffs = []
    for st in ("both", "strong", "weak"):
        for f in FEET:
            for s, b in gates():
                key = f"{f}|{gate_label(s, b)}|{st}"
                o = old["means"].get(key)
                n = new.get(key)
                if o is None:
                    continue
                if n is None:
                    unmeasured += 1
                    rows.append(f"| `{key}` | {o['mean_bp']:+.2f} | (未測定) | — | {'*' if o['star'] else '-'} / — | 未測定 |")
                    continue
                d = round(n["mean_bp"], 2) - o["mean_bp"]
                ok = abs(d) <= TOL_BP
                same += ok
                diff += (not ok)
                if not ok:
                    diffs.append((key, o["mean_bp"], n["mean_bp"], d))
                rows.append(f"| `{key}` | {o['mean_bp']:+.2f} | {n['mean_bp']:+.2f} | {d:+.2f} | "
                            f"{'*' if o['star'] else '-'} / {'*' if n['star'] else '-'} | {'一致' if ok else '**差**'} |")
    rows24 = ["| 升 | 当時 n / 保有中央値 | 新 n / 保有中央値 | 数の比較 |", "|---|---|---|---|"]
    same24 = diff24 = 0
    for key, o in sorted(old["n_hold"].items(), key=lambda kv: (int(kv[0].split("|")[0]), kv[0])):
        n = new.get(key)
        if n is None:
            rows24.append(f"| `{key}` | {o['n']:,} / {o['hold_median']} | (未測定) | 未測定 |")
            continue
        ok = n["n"] == o["n"] and n["hold_median"] == o["hold_median"]
        same24 += ok
        diff24 += (not ok)
        rows24.append(f"| `{key}` | {o['n']:,} / {o['hold_median']} | {n['n']:,} / {n['hold_median']} | {'一致' if ok else '**差**'} |")
    rows25 = ["| 足 | 当時 無効化 / 反対弱 / ドテン (%) | 新 | 数の比較 |", "|---|---|---|---|"]
    for key, o in sorted(old["exit_reasons"].items(), key=lambda kv: int(kv[0].split("|")[0])):
        n = new.get(key)
        if n is None:
            rows25.append(f"| `{key}` | {o['invalidated']} / {o['opposite_weak']} / {o['reversed']} | (未測定) | 未測定 |")
            continue
        w = n["exit_reasons"]
        tot = sum(w.values())
        nv = [round(100 * w.get(k, 0) / tot, 1) for k in ("invalidated", "opposite_weak", "reversed")]
        ok = all(abs(a - b) <= 0.05 for a, b in zip(nv, (o["invalidated"], o["opposite_weak"], o["reversed"])))
        rows25.append(f"| `{key}` | {o['invalidated']} / {o['opposite_weak']} / {o['reversed']} | {nv[0]} / {nv[1]} / {nv[2]} | {'一致' if ok else '**差**'} |")
    rows26 = ["| 升 | 当時 2017 / 2018 / 2019 | 新 | 数の比較 |", "|---|---|---|---|"]
    for key, o in sorted(old["per_year"].items(), key=lambda kv: (int(kv[0].split("|")[0]), kv[0])):
        n = new.get(key)
        if n is None:
            rows26.append(f"| `{key}` | {o['2017']:+.1f} / {o['2018']:+.1f} / {o['2019']:+.1f} | (未測定) | 未測定 |")
            continue
        nv = [round(n["per_year"][y]["mean_bp"], 1) for y in ("2017", "2018", "2019")]
        ok = all(abs(a - o[y]) <= 0.05 for a, y in zip(nv, ("2017", "2018", "2019")))
        rows26.append(f"| `{key}` | {o['2017']:+.1f} / {o['2018']:+.1f} / {o['2019']:+.1f} | {nv[0]:+.1f} / {nv[1]:+.1f} / {nv[2]:+.1f} | {'一致' if ok else '**差**'} |")
    stars_differ = [k for k in new if k in old["means"] and new[k]["star"] != old["means"][k]["star"]]
    body = ["# 升ごとの比較表(生成: `PYTHONPATH=src python3 scripts/k1_newenv_diff.py`)", "",
            f"平均 mean(r): 一致 {same} / 差 {diff} / 未測定 {unmeasured}(判定の閾 |差| ≤ {TOL_BP} bp = 表の 2 桁が同じ)。"
            f" `*` の食い違い {len(stars_differ)} 升。", "",
            f"表 2.4(n / 保有中央値): 一致 {same24} / 差 {diff24}。", "", "## 2.1〜2.3 mean(r)", ""] + rows + \
           ["", "## 2.4 n / 保有本数の中央値", ""] + rows24 + \
           ["", "## 2.5 決済理由の構成(s19/b24、両方)", ""] + rows25 + \
           ["", "## 2.6 年ごとの平均(強い)", ""] + rows26 + \
           ["", "## `*`(95% 区間が 0 を跨がない)が食い違う升", ""] + \
           ([f"- `{k}`: 当時 {'*' if old['means'][k]['star'] else '-'} / 新 {'*' if new[k]['star'] else '-'}"
             f"(新の区間 {new[k]['ci95_bp']})" for k in stars_differ] or ["(なし)"])
    with open(os.path.join(OUT_DIR, "diff_table.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(body) + "\n")
    print(f"means: same {same} diff {diff} unmeasured {unmeasured}; 2.4: same {same24} diff {diff24}; stars differ {len(stars_differ)}")
    for d in diffs[:40]:
        print("  DIFF", d)


if __name__ == "__main__":
    main()
