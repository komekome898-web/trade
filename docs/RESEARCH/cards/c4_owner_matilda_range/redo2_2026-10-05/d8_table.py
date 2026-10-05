"""カード 4 の D8 の表: families_r2 の良い側・悪い側の組ごとに、保存済みの summary.json・analysis.json の値を写す
(trades.json.gz に取引ごとの決まらない足の列が無いので、diag_tables の D8 は「仮定に左右されない部分」を出せない。
analysis.json の decided_only = 決まらない足を含まない取引だけの和が保存されているので、それを日数で割って
1 日あたりにする。区間は付けられない(記述)。台本そのものの試験は無い。値は写して割るだけ)。
    python3 docs/RESEARCH/cards/c4_owner_matilda_range/redo2_2026-10-05/d8_table.py
出力: このフォルダの D8_TABLE.md(全行)
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "..", "limit_sim", "families_r2")


def load(d):
    s = json.load(open(os.path.join(R, d, "summary.json")))["all"]
    a = json.load(open(os.path.join(R, d, "analysis.json")))
    do = a.get("decided_only") or {}
    return s, do


def main():
    names = sorted(d[:-5] for d in os.listdir(R) if d.endswith("_good") and os.path.isdir(os.path.join(R, d[:-5] + "_bad")))
    out = ["# カード 4 の D8: 良い側・悪い側と、決まらない足を含まない取引の和(1 日あたり、bp/日、区間なし)", "",
           "1 日あたり = 和 ÷ summary の days。止める(スキル D8)= 良い側と悪い側の符号が違う、または良い側と良い側の仮定に左右されない部分の符号が違う。", "",
           "| 組 | 日数 | 取引(良い側) | 決まらない足を含む取引(良い側) | 良い側 | 悪い側 | 仮定に左右されない部分(良い側) | 同(悪い側) | 止める |",
           "|---|---|---|---|---|---|---|---|---|"]
    for n in names:
        sg, dg = load(n + "_good")
        sb, db = load(n + "_bad")
        days = sg["days"]
        g, b = sg["sum_bp"] / days, sb["sum_bp"] / sb["days"]
        ag = dg["sum_bp"] / days if dg else None
        ab = db["sum_bp"] / sb["days"] if db else None
        stop = (g > 0) != (b > 0) or (ag is not None and (g > 0) != (ag > 0))
        f = lambda x: "—" if x is None else f"{x:+.2f}"
        out.append(f"| {n} | {days} | {sg['trades']:,} | {sg['trades_with_undecided']:,}({sg['trades_with_undecided'] / sg['trades']:.0%}) | "
                   f"{f(g)} | {f(b)} | {f(ag)} | {f(ab)} | {'止める' if stop else '止めない'} |")
    open(os.path.join(HERE, "D8_TABLE.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
