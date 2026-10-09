# 注(L-920、2026-10-09): 口座の bp(取引の行の pnl_bp)は廃止した。この台本は廃止前の列・出力を読む調べの記録で、今の出力では動かない。
# リードが書いた。委任・批評家を通していない(数えるだけ)。L-915 の調べ(display_x20_traps.py の向きを逆にしたもの)。
# 文書に書かれた数 X(小数つきか |X| ≥ 100)のうち、
#   その族の本(と基準)の読み口の出力の「元の値 × 20」を文書の桁に丸めたもの(B の集まり)のどれとも合わず、
#   「表示の値(小数 2 桁・整数)× 20」を丸めたもの(A の集まり)のどれかとは合う数
# を出す。= 読み口の bp の表示を手で × 20 した疑いのある数。pnl_jpy から直接出した数は A にも B にも入らないので出ない。
# 円で出した出力ファイルに同じ字の数があるものは除く(そこから写したものとして説明がつく)。
# 使い方(リポジトリの根から): python3 docs/RESEARCH/matilda_main/display_x20_suspects.py > docs/RESEARCH/matilda_main/display_x20_suspects.out
import glob
import json
import os
import re

M = "docs/RESEARCH/matilda_main/"
A_DIR = "docs/ANAL" + "YSIS/"
SKIP = {"n", "trades", "days", "k", "n_trades", "count", "both", "only_a", "only_b", "analysed", "of", "share_trades",
        "zero", "steps", "signal_delay", "hold_edges_min", "gap_edges_min", "win_peak_share_q", "mfe_median", "mae_median",
        "t_mfe", "hold", "days_needed", "days_needed_first", "days_needed_second", "d0"}
FAMS = ["base", "levels", "foot", "count", "alert", "entry_exit", "step", "break_dist", "break_len_mult", "beard", "break_delay",
        "break_off", "range_lo", "range_hi", "vola_gate"]
RUN_FAM = {"levels_1": "levels", "levels_3": "levels", "levels_7": "levels", "foot_5": "foot", "count_20": "count", "count_80": "count",
           "alert_x1": "alert", "alert_x2": "alert", "beard_off": "beard", "break_off": "break_off", "break_len_mult_4": "break_len_mult",
           "base": "base"}
for x in ("entry_exit", "step", "break_dist", "break_delay", "range_lo", "range_hi", "vola_gate"):
    RUN_FAM.update({r: x for r in os.listdir(M) if r.startswith(x + "_")})


def leaves(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k not in SKIP:
                yield from leaves(v)
    elif isinstance(o, list):
        for v in o:
            yield from leaves(v)
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        yield float(o)


def fmt(x, k):
    return f"{abs(x):,.{k}f}"


A, B = {f: set() for f in FAMS}, {f: set() for f in FAMS}
srcA = {f: {} for f in FAMS}
for jp in sorted(glob.glob(M + "*/diag_tables.json")) + sorted(glob.glob(M + "*/diag_paths.json")):
    run = jp.split("/")[-2]
    fam = RUN_FAM.get(run)
    if fam is None:
        continue
    o = json.load(open(jp))
    if jp.endswith("diag_paths.json"):
        o = [v.get("pnl_sum") for v in o.get("d4", {}).get("groups", {}).values()]
    for v in leaves(o):
        for targets in ([fam, "base"] if run == "base" else [fam]):
            for k in (0, 1):
                B[targets].add(fmt(round(v * 20, k), k))
                for nd in (2, 0):
                    s = fmt(round(round(v, nd) * 20, k), k)
                    A[targets].add(s)
                    srcA[targets].setdefault(s, f"{run} {v!r}(表示 {round(v, nd)}, × 20)")
# base の出力はどの族の文書にも基準として出る
for f in FAMS:
    B[f] |= B["base"]
    A[f] |= A["base"]
    for s, w in srcA["base"].items():
        srcA[f].setdefault(s, w)

# 円で出した出力(fam_tables.md・compare.md・各 .out ほか。読み口の bp の生の出力 diag_tables.md・diag_paths.md・blocked_*.md は除く)に
# 同じ字の数があれば、その数は円の出力から写したものとして説明がつく(B に足す)
tok = re.compile(r"(?<![\d.,])[−\-+]?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?![\d])")
for f in FAMS:
    dirs = [M + f] + [M + r for r, ff in RUN_FAM.items() if ff == f] + [M]
    for d in dirs:
        for q in glob.glob(d + "/*"):
            b = os.path.basename(q)
            if not (q.endswith(".md") or q.endswith(".out")) or b in ("diag_tables.md", "diag_paths.md") or b.startswith("blocked_") \
                    or b.startswith("display_x20_") or b.startswith("unit_roundtrip_"):
                continue
            for m in tok.finditer(open(q, encoding="utf-8", errors="ignore").read()):
                dec = m.group(2) or ""
                kk = len(dec) - 1 if dec else 0
                if kk <= 1:
                    B[f].add(fmt(float(m.group(1).replace(",", "") + dec), kk))

num = re.compile(r"(?<![\d.,])[−\-+]?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?![\d])")
print("| 文書 | 行 | 書かれた数 | 表示 × 20 で合う出力 | 行の頭 |")
print("|---|---|---|---|---|")
total = 0
for f in FAMS:
    p = A_DIR + f"2026-10-09_matilda_main_{f}.md"
    for i, line in enumerate(open(p, encoding="utf-8"), 1):
        if line.startswith(">"):
            continue
        for m in num.finditer(line):
            whole, dec = m.group(1), m.group(2) or ""
            k = len(dec) - 1 if dec else 0
            if k > 1:
                continue
            val = float(whole.replace(",", "") + dec)
            if not dec and val < 100:
                continue
            s = fmt(val, k)
            if s in A[f] and s not in B[f]:
                total += 1
                print(f"| {f} | {i} | {m.group(0)} | {srcA[f].get(s)} | {line.strip()[:70]} |")
print(f"\n計 {total} 箇所(偶然の一致を含む。行の中身を見て仕分ける)")
