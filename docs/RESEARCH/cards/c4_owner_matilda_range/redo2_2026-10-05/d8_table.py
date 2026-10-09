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


def _scale100(v):
    """`*_bp` の鍵の中身(数・数の並び・{ci, se, mde} のような入れ物)の数を全部 / 100 する。"""
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, (int, float)):
        return v / 100
    if isinstance(v, list):
        return [_scale100(x) for x in v]
    if isinstance(v, dict):
        return {k: _scale100(x) for k, x in v.items()}
    return v


def _to_pct(o):
    """L-920 より前の出力の損益の鍵 `*_bp`(率 × 1 万)を `*_pct`(%)に直す。新しい出力はそのまま。"""
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            if isinstance(k, str) and k.endswith("_bp"):
                out[k[:-3] + "_pct"] = _scale100(v)
            else:
                out[k] = _to_pct(v)
        return out
    if isinstance(o, list):
        return [_to_pct(x) for x in o]
    return o


def load(d):
    s = _to_pct(json.load(open(os.path.join(R, d, "summary.json"))))["all"]
    a = _to_pct(json.load(open(os.path.join(R, d, "analysis.json"))))
    do = a.get("decided_only") or {}
    return s, do


def main():
    names = sorted(d[:-5] for d in os.listdir(R) if d.endswith("_good") and os.path.isdir(os.path.join(R, d[:-5] + "_bad")))
    out = ["# カード 4 の D8: 良い側・悪い側と、決まらない足を含まない取引の和(1 日あたり、%/日(段で割った損益の率。L-920)、区間なし)", "",
           "1 日あたり = 和 ÷ summary の days。止める(スキル D8)= 良い側と悪い側の符号が違う、または良い側と良い側の仮定に左右されない部分の符号が違う。", "",
           "| 組 | 日数 | 取引(良い側) | 決まらない足を含む取引(良い側) | 良い側 | 悪い側 | 仮定に左右されない部分(良い側) | 同(悪い側) | 止める |",
           "|---|---|---|---|---|---|---|---|---|"]
    for n in names:
        sg, dg = load(n + "_good")
        sb, db = load(n + "_bad")
        days = sg["days"]
        g, b = sg["sum_pct"] / days, sb["sum_pct"] / sb["days"]
        ag = dg["sum_pct"] / days if dg else None
        ab = db["sum_pct"] / sb["days"] if db else None
        stop = (g > 0) != (b > 0) or (ag is not None and (g > 0) != (ag > 0))
        f = lambda x: "—" if x is None else f"{x:+.4f}"
        out.append(f"| {n} | {days} | {sg['trades']:,} | {sg['trades_with_undecided']:,}({sg['trades_with_undecided'] / sg['trades']:.0%}) | "
                   f"{f(g)} | {f(b)} | {f(ag)} | {f(ab)} | {'止める' if stop else '止めない'} |")
    open(os.path.join(HERE, "D8_TABLE.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
