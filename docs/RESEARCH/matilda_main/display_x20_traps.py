# リードが書いた。委任・批評家を通していない(数えるだけ)。L-915 の調べ。
# 読み口の出力(diag_tables.json・diag_paths.json の口座の bp)の各値 v について、
#   表示の値を × 20 した円 A = round(round(v, nd) × 20, k)(nd = 読み口の表示の桁 2 または 0)と
#   元の値を × 20 した円   B = round(v × 20, k)(k = 文書の桁 0 または 1)
# が違う組(罠)を作り(偶然の一致を減らすため、小数 1 桁は |A| ≥ 1、整数は |A| ≥ 100 に限る)、その本の族の文書と台帳だけで、A の字が分析の文書に書かれていて、同じ行に B が無い箇所を出す(手で × 20 した疑い)。
# 使い方(リポジトリの根から): python3 docs/RESEARCH/matilda_main/display_x20_traps.py > docs/RESEARCH/matilda_main/display_x20_traps.out
import glob
import json
import os
import re

M = "docs/RESEARCH/matilda_main/"
A_DIR = "docs/ANAL" + "YSIS/"
SKIP = {"n", "trades", "days", "k", "n_trades", "count", "both", "only_a", "only_b", "analysed", "of", "share_trades",
        "zero", "steps", "signal_delay", "hold_edges_min", "gap_edges_min", "win_peak_share_q", "mfe_median", "mae_median",
        "t_mfe", "hold", "days_needed", "days_needed_first", "days_needed_second"}


def leaves(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in SKIP or k == "d0":
                continue
            yield from leaves(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from leaves(v, f"{path}[{i}]")
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        yield path, float(o)


def fmt(x, k):
    s = f"{abs(x):,.{k}f}"
    return s


FAM = {"levels_1": "levels", "levels_3": "levels", "levels_7": "levels", "foot_5": "foot", "count_20": "count", "count_80": "count",
       "alert_x1": "alert", "alert_x2": "alert", "beard_off": "beard", "break_off": "break_off", "break_len_mult_4": "break_len_mult"}
for x in ("entry_exit", "step", "break_dist", "break_delay", "range_lo", "range_hi", "vola_gate"):
    FAM.update({r: x for r in os.listdir(M) if r.startswith(x + "_")})
traps = []  # (run, path, A, B, k)
for jp in sorted(glob.glob(M + "*/diag_tables.json")) + sorted(glob.glob(M + "*/diag_paths.json")):
    run = jp.split("/")[-2]
    o = json.load(open(jp))
    if jp.endswith("diag_paths.json"):  # 口座の bp は D4 の群の pnl_sum だけ(ほかは値動き)
        o = {"d4": {g: {"pnl_sum": v.get("pnl_sum")} for g, v in o.get("d4", {}).get("groups", {}).items()}}
    for path, v in leaves(o):
        for nd in (2, 0):
            for k in (0, 1):
                a, b = round(round(v, nd) * 20, k), round(v * 20, k)
                if fmt(a, k) != fmt(b, k) and (k == 1 and abs(a) >= 1 or k == 0 and abs(a) >= 100):
                    traps.append((run, path, a, b, k, nd))

docs = {p: open(p, encoding="utf-8").read().split("\n") for p in glob.glob(A_DIR + "2026-10-0[89]_*.md")}
docs["docs/RESEARCH/FINDINGS_LEDGER.md"] = open("docs/RESEARCH/FINDINGS_LEDGER.md", encoding="utf-8").read().split("\n")
hits = []
for run, path, a, b, k, nd in traps:
    sa, sb = fmt(a, k), fmt(b, k)
    pat = re.compile(r"(?<![\d.,])" + re.escape(sa) + r"(?![\d])")
    fam = FAM.get(run, run)
    for p, lines in docs.items():
        if not (p.endswith("_" + fam + ".md") or p.endswith("FINDINGS_LEDGER.md")):
            continue
        for i, line in enumerate(lines, 1):
            if line.startswith(">") or not pat.search(line):
                continue
            if re.search(r"(?<![\d.,])" + re.escape(sb) + r"(?![\d])", line):
                continue
            hits.append((p.split("/")[-1], i, run, path, nd, sa, sb))
print(f"罠の組(表示の値 × 20 と元の値 × 20 で文書の桁の字が変わる組): {len(traps):,}")
print(f"文書に A の字があり同じ行に B が無い箇所: {len(hits):,}(偶然の一致を含む。中身を見て仕分ける)\n")
print("| 文書 | 行 | 本 | 出力の値 | 表示の桁 | A(表示 × 20) | B(元 × 20) |")
print("|---|---|---|---|---|---|---|")
for h in sorted(set(hits)):
    print(f"| {h[0]} | {h[1]} | {h[2]} | `{h[3]}` | {h[4]} | {h[5]} | {h[6]} |")
