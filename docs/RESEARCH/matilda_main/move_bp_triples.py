# リードが書いた。委任・批評家を通していない(数えるだけ)。L-916 の調べ(値動きの bp の、確かな写しだけを拾う版)。
# move_bp_check.py は 1 つの数の字の一致なので、引数(0.25 など)・比・勝率のポイントとの偶然の一致が多い。
# ここでは「点 [下, 上]」の 3 つの数が同じ出力の 1 つの値(点・区間の下・上)と小数 2 桁で全部合うものだけを確かな写しとして拾い、
#   値動きの bp(diag_paths.json・blocked_*.json の after_exit・d5)/ 口座の bp(diag_tables.json の点・区間)/ 円(口座の bp × 20)
# のどれと合うかを出す。値動きと合った写しには、その行(表なら列の見出し・表の前の文も)に書かれた単位を付ける。
# あわせて D4 の MFE・MAE の中央値の組(「a・b」か、同じ行に 2 つ)も拾う。
# 使い方(リポジトリの根から): python3 docs/RESEARCH/matilda_main/move_bp_triples.py > docs/RESEARCH/matilda_main/move_bp_triples.out
import glob
import json
import os
import re
from collections import Counter

M = "docs/RESEARCH/matilda_main/"
A_DIR = "docs/ANAL" + "YSIS/"
FAMS = ["base", "levels", "foot", "count", "alert", "entry_exit", "step", "break_dist", "break_len_mult", "beard", "break_delay",
        "break_off", "range_lo", "range_hi", "vola_gate"]


def f2(x):
    return f"{x:+.2f}".replace("-", "−")


def norm(s):
    s = s.replace("-", "−")
    return s if s.startswith(("−", "+")) else "+" + s


def walk(o, path=""):
    if isinstance(o, dict):
        if {"lo", "hi"} <= set(o) and any(k in o for k in ("per_trade", "mean")):
            yield path, o
        for k, v in o.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{path}[{i}]")


MOVE, ACC, YEN, MED = {}, {}, {}, {}
for jp in sorted(glob.glob(M + "*/diag_paths.json")) + sorted(glob.glob(M + "*/blocked_*.json")):
    o = json.load(open(jp))
    run = jp[len(M):]
    for path, r in walk(o):
        pt = r.get("per_trade", r.get("mean"))
        if pt is None or r["lo"] is None:
            continue
        MOVE.setdefault((f2(pt), f2(r["lo"]), f2(r["hi"])), f"{run}{path}")
    for g, v in o.get("d4", {}).get("groups", {}).items():
        if v.get("mfe_median") is not None:
            MED.setdefault((f2(v["mfe_median"]), f2(v["mae_median"])), f"{run} d4.{g}")
for jp in sorted(glob.glob(M + "*/diag_tables.json")):
    o = json.load(open(jp))
    run = jp[len(M):]
    for path, r in walk(o):
        pt = r.get("per_trade", r.get("mean"))
        if pt is None or r["lo"] is None:
            continue
        ACC.setdefault((f2(pt), f2(r["lo"]), f2(r["hi"])), f"{run}{path}")
        for k in (0, 1):
            YEN.setdefault(tuple(norm(f"{v * 20:.{k}f}") for v in (pt, r["lo"], r["hi"])), f"{run}{path} × 20")

N = r"[−+\-]?\d+(?:,\d{3})*(?:\.\d+)?"
trip = re.compile(rf"({N})\s*\[({N}),\s*({N})\]")
pair = re.compile(r"([−+\-]?\d+\.\d{2})[・ /]+([−+\-]?\d+\.\d{2})")


def unit_of(t):
    if re.search(r"move_bp|値動き", t):
        return "値動き"
    if re.search(r"1 bp = 20 円|口座", t):
        return "口座の bp"
    if "円" in t:
        return "円"
    if "bp" in t:
        return "bp だけ"
    return "無し"


files = [A_DIR + f"2026-10-09_matilda_main_{f}.md" for f in FAMS] + ["docs/RESEARCH/FINDINGS_LEDGER.md",
                                                                       "docs/DISCUSSIONS/2026-10-08_matilda_main/STAGE1_FAMILY_TABLES.md"]
rows, meds = [], []
cnt = Counter()
for p in files:
    L = open(p, encoding="utf-8").read().split("\n")
    st = next(i for i, l in enumerate(L) if l.startswith("### K-301")) if p.endswith("LEDGER.md") else 0
    header, caption = None, ""
    for i in range(st, len(L)):
        line = L[i]
        if line.startswith(">"):
            continue
        is_tab = line.startswith("|")
        if is_tab and i + 1 < len(L) and re.match(r"^\|[-| :]+\|$", L[i + 1].strip()):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            continue
        if not is_tab:
            header = None
            if line.strip():
                caption = line
        for m in trip.finditer(line):
            key = tuple(norm(x.replace(",", "")) for x in m.groups())
            kinds = [k for k, S in (("値動き", MOVE), ("口座の bp", ACC), ("円", YEN)) if key in S]
            cnt[("3 つ組", "・".join(kinds) or "どれでもない")] += 1
            if "値動き" not in kinds:
                continue
            if is_tab:
                pos = line[:m.start()].count("|") - 1
                col = header[pos] if header and 0 <= pos < len(header) else ""
                lab = unit_of(col)
                where = f"列「{col[:24]}」"
                if lab == "無し":
                    lab, where = unit_of(caption), "表の前の文"
            else:
                sent = line[:m.start()].split("。")[-1] + line[m.start():].split("。")[0]
                lab, where = unit_of(sent), "同じ文"
                if lab == "無し":
                    lab, where = unit_of(line), "同じ行"
            cnt[("値動きの 3 つ組の単位", lab)] += 1
            rows.append((os.path.basename(p), i + 1, m.group(0), "・".join(kinds), lab, where, MOVE[key]))
        for m in pair.finditer(line):
            key = tuple(norm(x) for x in m.groups())
            if key in MED:
                sent = line if is_tab else line[:m.start()].split("。")[-1] + line[m.start():].split("。")[0]
                lab = unit_of((" ".join(header) if header else "") + caption) if is_tab else unit_of(sent)
                if lab == "無し":
                    lab = unit_of(line)
                cnt[("MFE・MAE の組の単位", lab)] += 1
                meds.append((os.path.basename(p), i + 1, m.group(0), lab, MED[key]))
print(f"値動きの 3 つ組 {len(MOVE):,}・口座の bp の 3 つ組 {len(ACC):,}・円(× 20)の 3 つ組 {len(YEN):,}・MFE・MAE の組 {len(MED):,}\n")
print("| 何を | 仕分け | 数 |\n|---|---|---|")
for (a, b), n in sorted(cnt.items()):
    print(f"| {a} | {b} | {n:,} |")
print("\n## 値動きの 3 つ組の写しのうち、単位が「値動き」でないもの\n")
print("| 文書 | 行 | 写し | 合った出力の種類 | 書かれた単位 | どこから読んだか | 合った出力 |\n|---|---|---|---|---|---|---|")
for r in rows:
    if r[4] != "値動き":
        print("| " + " | ".join(str(x).replace("|", "/") for x in r) + " |")
print("\n## MFE・MAE の組の写しのうち、単位が「値動き」でないもの\n")
print("| 文書 | 行 | 写し | 書かれた単位 | 合った出力 |\n|---|---|---|---|---|")
for r in meds:
    if r[3] != "値動き":
        print("| " + " | ".join(str(x).replace("|", "/") for x in r) + " |")
