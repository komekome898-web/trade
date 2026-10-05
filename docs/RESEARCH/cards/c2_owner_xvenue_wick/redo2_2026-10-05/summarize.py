"""diag/*.json(diag_tables の出力)を 1 つの表にまとめる。値は写すだけで計算しない(D8 の止めるも diag_tables の値)。
出力: このフォルダの ALL_RUNS.md(全行。省かない)。
    python3 docs/RESEARCH/cards/c2_owner_xvenue_wick/redo2_2026-10-05/summarize.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "diag")


def f(r):
    if not r or r.get("mean") is None:
        return "—"
    lo, hi = r.get("lo"), r.get("hi")
    if lo is None:
        return f"{r['mean']:+.2f}"
    return f"{r['mean']:+.2f} [{lo:+.2f}, {hi:+.2f}]"


def main():
    rows = []
    for fn in sorted(os.listdir(D)):
        if not fn.endswith(".json"):
            continue
        j = json.load(open(os.path.join(D, fn)))
        name = fn[:-5]
        d1 = j["d1"]
        seg = d1["segments"]
        full = d1["rows"][0]
        years = {r["label"]: r for r in d1["rows"][1:]}
        d8 = j.get("d8")
        p = (j["d0"].get("params") or {})
        sd = j["d0"].get("signal_delay")
        rows.append({
            "name": name, "kind": j["d0"]["kind"], "trades": j["d0"]["trades"],
            "full": f(full), "first": f(seg["first"]), "second": f(seg["second"]), "diff": f(seg["diff"]),
            "outcome": seg["outcome"], "half_edge": seg["second"]["from"],
            "years": " / ".join(f"{y} {years[y]['mean']:+.1f}{'*' if years[y]['zero'] != '含む' else ''}" for y in sorted(years)),
            "d8": ("—" if not d8 else ("止める" if d8.get("stop") else "止めない")),
            "bad_full": (f(d8["rows"][0]["bad"]) if d8 and d8.get("rows") and isinstance(d8["rows"][0].get("bad"), dict) else "—"),
            "af": ("—" if not d8 or not d8.get("assumption_free") else f(d8["assumption_free"]["good"])),
            "und": ("—" if not d8 or not d8.get("undecided") else f"{d8['undecided']['good']['trades']} ({d8['undecided']['good']['share_trades']:.0%})"),
            "delay": ("—" if not sd else f"中央 {sd['q']['50']:.0f}・90% {sd['q']['90']:.0f}・最大 {sd['max']:.0f}"),
        })
    out = ["# カード 2 の全走らせ(diag_tables の値の写し)", "",
           "損益は bp/日、経費の前、区間 95%(日の塊 5 日)。年の値の * は区間が 0 を含まない年。前半・後半の境は走らせごと(期間が違う)。",
           "D8 は良い側・悪い側の組のときだけ。悪い側の全期間は D8 の表の値。合図 → 建て = 分(signal_t のある走らせだけ)。", "",
           "| 走らせ | 種類 | 取引 | 全期間 | 前半 | 後半 | 後半 − 前半 | D1 の結果 | 後半の始まり | D8 | 悪い側の全期間 | 決まらない足を含む取引(割合) | 仮定に左右されない部分 | 合図 → 建て(分) | 年ごと |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['name']} | {r['kind']} | {r['trades'] if r['trades'] is not None else '—'} | {r['full']} | {r['first']} | "
                   f"{r['second']} | {r['diff']} | {r['outcome']} | {r['half_edge']} | {r['d8']} | {r['bad_full']} | {r['und']} | {r['af']} | {r['delay']} | {r['years']} |")
    open(os.path.join(HERE, "ALL_RUNS.md"), "w").write("\n".join(out) + "\n")
    print(len(rows))


if __name__ == "__main__":
    main()
