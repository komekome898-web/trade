# リードが書いた。委任・批評家を通していない(数えるだけ)。L-916 の調べ(値動きの bp = move_bp の影響範囲)。
# 値動きの bp(diag_paths.py が作る。値段の変化率 × 10,000)の出力の値(diag_paths.json・blocked_*.json の、損益の和 pnl_sum と件数を除く葉)を集め、
# 分析の文書(15 族)・台帳(K-301 以降)・族の表の抜き出しに書かれた数を 1 つずつ次に仕分ける:
#   M1  = 値動きの bp の出力の値を文書の桁に丸めたものと字が合う
#   M20 = 値動きの bp の出力の値 × 20(表示の値 × 20 を含む)と字が合い、M1 には合わない(値動きを円に直した誤りの疑い)
# M1 の数には、その数に付いた単位の書き方(表なら列の見出しと表の前の文、文なら数の直後)を付ける:
#   円 / 口座の bp(「1 bp = 20 円」など)/ 値動き(move_bp・値動き)/ bp だけ / 無し
# 偶然の一致を減らすため、口座の bp の出力を × 20 した円(元の値・表示の値の両方)と、円で出した出力ファイルの数(小数 1 桁まで)の字を
# 「円で説明がつく数」(Y)として集め、M1 の整数・小数 1 桁と M20 から除く(display_x20_suspects.py と同じ集め方)。
# 使い方(リポジトリの根から): python3 docs/RESEARCH/matilda_main/move_bp_check.py > docs/RESEARCH/matilda_main/move_bp_check.out
import glob
import json
import os
import re

M = "docs/RESEARCH/matilda_main/"
A_DIR = "docs/ANAL" + "YSIS/"
FAMS = ["base", "levels", "foot", "count", "alert", "entry_exit", "step", "break_dist", "break_len_mult", "beard", "break_delay",
        "break_off", "range_lo", "range_hi", "vola_gate"]
RUN_FAM = {"levels_1": "levels", "levels_3": "levels", "levels_7": "levels", "foot_5": "foot", "count_20": "count", "count_80": "count",
           "alert_x1": "alert", "alert_x2": "alert", "beard_off": "beard", "break_off": "break_off", "break_len_mult_4": "break_len_mult",
           "base": "base"}
for x in ("entry_exit", "step", "break_dist", "break_delay", "range_lo", "range_hi", "vola_gate"):
    RUN_FAM.update({r: x for r in os.listdir(M) if r.startswith(x + "_")})
NOT_MOVE = {"trades", "analysed", "of", "pnl_sum", "win_peak_share_q", "name", "n", "days"}


def leaves(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k not in NOT_MOVE:
                yield from leaves(v)
    elif isinstance(o, list):
        for v in o:
            yield from leaves(v)
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        yield float(o)


def fmt(x, k):
    return f"{abs(x):,.{k}f}"


M1 = {f: {} for f in FAMS}
M20 = {f: {} for f in FAMS}
srcs = sorted(glob.glob(M + "*/diag_paths.json")) + sorted(glob.glob(M + "*/blocked_*.json"))
n_leaves = 0
for jp in srcs:
    run = jp.split("/")[-2]
    b = os.path.basename(jp)
    fam = RUN_FAM.get(run) if b == "diag_paths.json" else run  # blocked_*.json は族の置き場にある
    if fam not in M1:
        continue
    for v in leaves(json.load(open(jp))):
        n_leaves += 1
        tag = f"{run}/{b} {v!r}"
        for k in (0, 1, 2):
            M1[fam].setdefault(fmt(round(v, k), k), tag)
            M20[fam].setdefault(fmt(round(v * 20, k), k), tag + " × 20")
            M20[fam].setdefault(fmt(round(round(v, 2) * 20, k), k), tag + "(表示) × 20")
for f in FAMS:  # 基準の出力はどの族の文書にも出る
    for s, w in M1["base"].items():
        M1[f].setdefault(s, w)
    for s, w in M20["base"].items():
        M20[f].setdefault(s, w)
SKIPA = {"n", "trades", "days", "k", "n_trades", "count", "both", "only_a", "only_b", "analysed", "of", "share_trades",
         "zero", "steps", "signal_delay", "hold_edges_min", "gap_edges_min", "win_peak_share_q", "mfe_median", "mae_median",
         "t_mfe", "hold", "days_needed", "days_needed_first", "days_needed_second", "d0"}


def aleaves(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k not in SKIPA:
                yield from aleaves(v)
    elif isinstance(o, list):
        for v in o:
            yield from aleaves(v)
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        yield float(o)


Y = {f: set() for f in FAMS}
for jp in sorted(glob.glob(M + "*/diag_tables.json")) + sorted(glob.glob(M + "*/diag_paths.json")) + sorted(glob.glob(M + "*/blocked_*.json")):
    run = jp.split("/")[-2]
    fam = RUN_FAM.get(run) if not os.path.basename(jp).startswith("blocked_") else run
    if fam not in Y:
        continue
    o = json.load(open(jp))
    if not jp.endswith("diag_tables.json"):
        o = [v.get("pnl_sum") for v in o.get("d4", {}).get("groups", {}).values()]
    for v in aleaves(o):
        for k in (0, 1):
            Y[fam].add(fmt(round(v * 20, k), k))
            for nd in (2, 0):
                Y[fam].add(fmt(round(round(v, nd) * 20, k), k))
tok = re.compile(r"(?<![\d.,])[−\-+]?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?![\d])")
for f in FAMS:
    for d in [M + f] + [M + r for r, ff in RUN_FAM.items() if ff == f] + [M]:
        for q in glob.glob(d + "/*"):
            b = os.path.basename(q)
            if not (q.endswith(".md") or q.endswith(".out")) or b in ("diag_tables.md", "diag_paths.md") or b.startswith("blocked_") \
                    or b.startswith("display_x20_") or b.startswith("unit_roundtrip_") or b.startswith("move_bp_"):
                continue
            for m in tok.finditer(open(q, encoding="utf-8", errors="ignore").read()):
                dec = m.group(2) or ""
                kk = len(dec) - 1 if dec else 0
                if kk <= 1:
                    Y[f].add(fmt(float(m.group(1).replace(",", "") + dec), kk))
for f in FAMS:
    Y[f] |= Y["base"]
YALL = set().union(*Y.values())
ALL1, ALL20 = {}, {}
for f in FAMS:
    for s, w in M1[f].items():
        ALL1.setdefault(s, w)
    for s, w in M20[f].items():
        ALL20.setdefault(s, w)

num = re.compile(r"(?<![\d.,A-Za-z_])[−\-+]?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?![\d])")


def unit_of(text):
    t = text
    if re.search(r"move_bp|値動き", t):
        return "値動き"
    if re.search(r"1 bp = 20 円|口座", t):
        return "口座の bp"
    if "円" in t:
        return "円"
    if "bp" in t:
        return "bp だけ"
    return "無し"


def scan(path, fam_sets, only=None):
    lines = open(path, encoding="utf-8").read().split("\n")
    out = []
    header, caption = None, ""
    for i, line in enumerate(lines, 1):
        if only and not only(i, line):
            continue
        if line.startswith(">"):
            continue
        is_tab = line.startswith("|")
        if is_tab and i < len(lines) and re.match(r"^\|[-| :]+\|$", lines[i].strip() if i < len(lines) else ""):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            continue
        if re.match(r"^\|[-| :]+\|$", line.strip()):
            continue
        if not is_tab:
            header = None
            if line.strip():
                caption = line
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if is_tab else None
        for m in num.finditer(line):
            whole, dec = m.group(1), m.group(2) or ""
            k = len(dec) - 1 if dec else 0
            if k > 2:
                continue
            val = float(whole.replace(",", "") + dec)
            if not dec and val < 100:
                continue
            s = fmt(val, k)
            s1, s20, yy = fam_sets
            if k <= 1 and s in yy:
                continue
            kind = "M1" if s in s1 else ("M20" if s in s20 else None)
            if kind is None:
                continue
            if is_tab:
                pos = line[:m.start()].count("|") - 1
                col = header[pos] if header and 0 <= pos < len(header) else ""
                u = "値動き" if re.search(r"MFE|MAE", col) and unit_of(caption) == "値動き" else unit_of(col)
                if u == "無し":
                    u = unit_of(cells[0] if cells else "") if unit_of(cells[0] if cells else "") != "無し" else unit_of(caption)
                ctx = f"列「{col[:30]}」"
            else:  # 数を含む文(「。」で区切る)全体の単位の語
                sent = line[:m.start()].split("。")[-1] + line[m.start():].split("。")[0]
                u = unit_of(sent)
                ctx = f"直後「{line[m.end():m.end() + 14].strip()}」"
            out.append((os.path.basename(path), i, m.group(0), kind, u, ctx, (s1.get(s) if kind == "M1" else s20.get(s)), line.strip()[:60]))
    return out


rows = []
for f in FAMS:
    rows += scan(A_DIR + f"2026-10-09_matilda_main_{f}.md", (M1[f], M20[f], Y[f]))
led = open("docs/RESEARCH/FINDINGS_LEDGER.md", encoding="utf-8").read().split("\n")
start = next(i for i, l in enumerate(led, 1) if l.startswith("### K-301"))
rows += scan("docs/RESEARCH/FINDINGS_LEDGER.md", (ALL1, ALL20, YALL), only=lambda i, l: i >= start)
rows += scan("docs/DISCUSSIONS/2026-10-08_matilda_main/STAGE1_FAMILY_TABLES.md", (ALL1, ALL20, YALL))
# fam_tables.md(機械が出した族の表)は節の見出しに単位を書く(fam_tables.py:105・115・121 が move_bp、ほかは円)ので数えない

print(f"値動きの bp の出力: {len(srcs)} ファイル、葉 {n_leaves:,}")
from collections import Counter
c = Counter((r[3], r[4]) for r in rows)
print("\n| 仕分け | 単位の書き方 | 数 |\n|---|---|---|")
for (k, u), n in sorted(c.items()):
    print(f"| {k} | {u} | {n:,} |")
print(f"\n計 {len(rows):,}(偶然の一致を含む。M1 の「円」「口座の bp」「bp だけ」「無し」と M20 は行の中身を見て仕分ける)\n")
print("| 文書 | 行 | 数 | 仕分け | 単位の書き方 | 手がかり | 合った出力 | 行の頭 |\n|---|---|---|---|---|---|---|---|")
for r in rows:
    if not (r[3] == "M1" and r[4] == "値動き"):
        print("| " + " | ".join(str(x).replace("|", "/") for x in r) + " |")
