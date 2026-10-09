# リードが書いた。委任・批評家を通していない。L-916 の調べ。
# move_bp_check.out のうち「値動きの値と字が合うのに、書かれた単位が円・口座の bp・『bp』だけ」(M1)と「値動きの値 × 20 と字が合う」(M20)の行を、
# 数の前後の字(⟨…⟩)と一緒に全部出し、何の数かを仕分ける。仕分けの規則は、リードが全部の行を読んでから、読んだ結果を再現するように書いた。
# 規則に当たらない行は「規則外」として出す(リードが読んで、下の READ に書く)。
# 使い方(リポジトリの根から): python3 docs/RESEARCH/matilda_main/move_bp_read.py > docs/RESEARCH/matilda_main/move_bp_read.out
import re
from collections import Counter

A = "docs/ANAL" + "YSIS/"
READ = {  # 規則外の行をリードが読んだ結果
    ("2026-10-09_matilda_main_range_hi.md", 372, "−1.00"): "値動きの bp(幅の下の族の D5 の値を × 1 で引いた。族をまたいだ引用なので族の出力の集まりに無く、× 20 の字の一致として出た)",
    ("2026-10-09_matilda_main_base.md", 465, "10.80"): "幅 ÷ ボラ の分位",
    ("2026-10-09_matilda_main_base.md", 476, "10.80"): "幅 ÷ ボラ の分位",
    ("2026-10-09_matilda_main_base.md", 477, "10.80"): "幅 ÷ ボラ の分位",
    ("2026-10-09_matilda_main_break_dist.md", 25, "156"): "コードの行番号",
    ("2026-10-09_matilda_main_entry_exit.md", 257, "0.67"): "頂点までの分 ÷ 保有の分 の分位",
    ("2026-10-09_matilda_main_levels.md", 328, "7.02"): "口座の bp(D1 の年ごと・D6・D7・MDE の表と文)",
    ("2026-10-09_matilda_main_base.md", 261, "−134.7"): "円(1 本あたり・和)",
    ("2026-10-09_matilda_main_break_delay.md", 325, "−610"): "円(1 本あたり・和)",
    ("2026-10-09_matilda_main_break_dist.md", 335, "−4.8"): "円(1 本あたり・和)",
    ("2026-10-09_matilda_main_break_dist.md", 364, "0.25"): "引数の値(幅 × 0.25)",
    ("2026-10-09_matilda_main_break_len_mult.md", 303, "−2.2"): "円(1 本あたり・和)",
    ("2026-10-09_matilda_main_count.md", 290, "0.86"): "倍率・比",
    ("2026-10-09_matilda_main_entry_exit.md", 220, "2.74"): "段の数の平均",
    ("2026-10-09_matilda_main_entry_exit.md", 225, "1.46"): "段の数の平均",
    ("2026-10-09_matilda_main_levels.md", 207, "−2.29"): "利確で閉じる割合 − とんとん(ポイント)",
    ("2026-10-09_matilda_main_step.md", 438, "0.46"): "倍率・比",
    ("FINDINGS_LEDGER.md", 324, "−2.29"): "利確で閉じる割合 − とんとん(ポイント)",
    ("FINDINGS_LEDGER.md", 966, "1.23"): "倍率・比",
    ("2026-10-09_matilda_main_step.md", 252, "0.66"): "倍率・比",
    ("2026-10-09_matilda_main_step.md", 252, "0.40"): "倍率・比",
    ("2026-10-09_matilda_main_step.md", 252, "0.69"): "倍率・比",
    ("2026-10-09_matilda_main_step.md", 252, "0.46"): "倍率・比",
    ("2026-10-09_matilda_main_vola_gate.md", 381, "9.2"): "割合・門の値(%)",
    ("2026-10-09_matilda_main_beard.md", 192, "1.46"): "段の数の平均",
    ("2026-10-09_matilda_main_count.md", 413, "+0.69"): "利確で閉じる割合 − とんとん(ポイント)",
    ("2026-10-09_matilda_main_levels.md", 318, "+1.64"): "口座の bp(D1 の年ごと・D6・D7・MDE の表と文)",
    ("2026-10-09_matilda_main_levels.md", 318, "+0.66"): "口座の bp(D1 の年ごと・D6・D7・MDE の表と文)",
}
RULES = [
    (r"\| 0\.\d{4} \| 0\.\d{4} \| [−+\-]", "利確で閉じる割合 − とんとん(ポイント)"),
    (r"ポイント|^\| [^|]+ \| [−+]\d\.\d\d \| [−+]\d\.\d\d \|$", "利確で閉じる割合 − とんとん(ポイント)"),
    (r"万円|M 円", "万円・百万円の和"),
    (r"break_dist_0\.25|幅 × 0\.25|break_dist 0\.25|\| 0\.25 |0\.25 −|0\.25 [+0-9閉利は]|0\.25 の|\(0\.25\)|後半の差 0\.25|前半は 0\.25", "引数の値(幅 × 0.25)"),
    (r"\d% [−+]|% 点は|分位", "取引の損益の分位(口座の bp)"),
    (r"倍|比 0|比\(|前半 ÷ 後半|= 0\.87", "倍率・比"),
    (r"段の数", "段の数の平均"),
    (r"[0-9]% |[0-9]%・|[0-9]%、|% 未満|% で", "割合・門の値(%)"),
    (r"円|→ [−+]?\d+\.\d \||\| [−+]?\d+\.\d\d? \| [−+]?[\d,]+ \|", "円(1 本あたり・和)"),
    (r"bp|\[", "口座の bp(D1 の年ごと・D6・D7・MDE の表と文)"),
]


def text(doc, cache={}):
    if doc not in cache:
        p = "docs/RESEARCH/FINDINGS_LEDGER.md" if doc.startswith("FINDINGS") else (
            "docs/DISCUSSIONS/2026-10-08_matilda_main/STAGE1_FAMILY_TABLES.md" if doc.startswith("STAGE1") else A + doc)
        cache[doc] = open(p, encoding="utf-8").read().split("\n")
    return cache[doc]


rows = []
for line in open("docs/RESEARCH/matilda_main/move_bp_check.out", encoding="utf-8"):
    f = [x.strip() for x in line.strip().strip("|").split("|")]
    if len(f) < 8 or not re.match(r"(2026|FINDINGS|STAGE1)", f[0]):
        continue
    if not (f[3] == "M20" or f[3] == "M1" and f[4] in ("円", "口座の bp", "bp だけ")):
        continue
    doc, ln, num = f[0], int(f[1]), f[2]
    L = text(doc)[ln - 1]
    i = L.find(num)
    snip = L[max(0, i - 28):i + len(num) + 14]
    k = READ.get((doc, ln, num))
    if k is None:
        for pat, name in RULES:
            if re.search(pat, snip):
                k = name
                break
        else:
            k = "規則外"
    rows.append((k, doc, ln, num, f[3], snip))
c = Counter(r[0] for r in rows)
print(f"読んだ行 {len(rows)}(M1 {sum(1 for r in rows if r[4] == 'M1')}・M20 {sum(1 for r in rows if r[4] == 'M20')})\n")
print("| 何の数か | 数 |\n|---|---|")
for k, n in c.most_common():
    print(f"| {k} | {n} |")
print("\n| 何の数か | 文書 | 行 | 数 | 字の一致 | 前後 |\n|---|---|---|---|---|---|")
for r in sorted(rows, key=lambda r: (r[0], r[1], r[2])):
    print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | ⟨{r[5].replace('|', '/')}⟩ |")
