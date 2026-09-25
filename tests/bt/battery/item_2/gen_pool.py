#!/usr/bin/env python3
"""Item 2 battery: the survey-side candidate pool, extracted by machine (委任文 §3「調査結果の側の選び方」).

    python3 tests/bt/battery/item_2/gen_pool.py        # writes pool.tsv next to this file

Rules (REQUIREMENTS.md §3, fixed by the requirements keeper; nobody adds or removes by hand):
- C2-5 / C2-7: catalogue rows whose column 9 (市場影響と約定の模型) or column 10 (段(機構)) is non-empty
  (REQUIREMENTS §3.1 first command, verbatim).
- C2-6: rows whose column 13 (取り消しの扱い) is non-empty.  C2-9: rows whose column 12 (遅延) is non-empty.
  (REQUIREMENTS §3.1 prints these with `$12` / `$11`; by the header `$11` is 段(既定) and `$12` is 遅延,
  `$13` is 取り消しの扱い -- the three columns are non-empty on the same 52 rows, so the set is the same
  whichever reading is taken; this script reads the columns BY NAME.)
- C2-8, C2-12: no catalogue column; REQUIREMENTS §3 greps SCAN and finds 0 candidates (C2-12 has no
  survey row at all: JPX board data is our own data-wait state).
- C2-1 / C2-2 / C2-3 / C2-4 / C2-10 / C2-11: no catalogue column; the candidates are the ones REQUIREMENTS
  §3.2 lists from its grep of SCAN (copied below with the SCAN line REQUIREMENTS cites).  Names are resolved
  to catalogue numbers by the catalogue's name column (a name REQUIREMENTS gives with a wrong number, e.g.
  「7 `Basana`」, is resolved by the name).  C2-3 takes 98 because REQUIREMENTS §3.2 says its self-trade hit
  (98's STP) is counted under C2-1 only to avoid double counting.
"""
from __future__ import annotations

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
CAT = REPO / "docs/DATA/tools_catalog.tsv"

# REQUIREMENTS §3.2, candidate name as written there -> SCAN line(s) REQUIREMENTS cites.
GREP = {
    "C2-1": [("nautilus_trader", "247"), ("Mendl-Labs/BacktestingCore", "1819・1823"), ("Ziplime", "2399"),
             ("SarthakDalmia1/backtesting_execution_simulator", "4104"), ("mote/backtest", "4874・10065・10066"),
             ("mihircoding/limitOrderBook", "5115・5127・5282・5284・5288"), ("trade-frame", "5777"),
             ("VnPy", "6992・9137"), ("ForexTester", "10060"), ("AlgoTest", "10186")],
    "C2-3": [("mihircoding/limitOrderBook", "5115・5127・5282・5284・5288")],
    "C2-4": [],
    "C2-10": [("Jesse", "1226・7147"), ("VnPy", "1269・6897"), ("Mendl-Labs/BacktestingCore", "1374・1382"),
              ("Basana", "1656・1657・1666・1679"), ("Backtrader", "1709・1828"), ("bt", "1795・1846"),
              ("Ziplime", "1819〜1823・2399・2483"), ("fast-trade", "2157・6866"), ("pybotters", "2768・2770"),
              ("PySystemtrade", "3232・3606・3373"), ("prediction-market-backtesting", "4112"),
              ("OpenMarket", "4111・5694・5771"), ("OctoBot", "4135"), ("QuantCore", "4427"),
              ("trade-frame", "6458"), ("barter-rs", "6566"), ("carlos8f/zenbot", "6651"), ("sigc", "6652"),
              ("Superalgos", "6986"), ("DeviaVir/zenbot", "6989"), ("mote/backtest", "10066"),
              ("PredictionMarketBench", "10408・10434")],
    "C2-11": [("vectorbt", "281・5881"), ("Jesse", "1226・1374"), ("Ziplime", "2458〜2462・2484"),
              ("pybotters", "2772"), ("OctoBot", "2813"), ("PySystemtrade", "3232・3234・3567・3606"),
              ("OpenMarket", "5694"), ("barter-rs", "6284・6302・6568"), ("QUANTAXIS", "7825・7968・8303・8669・9498"),
              ("Backtrader", "9132")],
}
GREP["C2-2"] = list(GREP["C2-1"])
# Names whose catalogue row is spelled differently (resolved by the SCAN line the catalogue row points to).
ALIAS = {"OctoBot": "11", "bt": "5", "QuantCore": "34", "sigc": "107", "PredictionMarketBench": "90",
         "nautilus_trader": "58", "vectorbt": "73"}
ALIAS_WHY = {
    "11": "台帳 11 行の名前の欄は python3、最後の記載の行(SCAN 8452)と項目 0 の導入の記録は OctoBot",
    "5": "台帳 5 行の名前の欄は Lean CLI、最後の記載の行(SCAN 6849)は「5. `bt` — 印は `区分1-足`」",
}
GREP_CMD = {
    "C2-1": "grep -inE 'post-?only|\\bIOC\\b|\\bFOK\\b|reduce-?only|\\bOCO\\b|逆指値|stop[_ -]?order|self[- ]?trade|self_match' SCAN_clean.md",
    "C2-3": "grep -inE 'self[- ]?trade|self_match|STATE_UNKNOWN|kill.switch|呼値|tick size' SCAN_clean.md",
    "C2-4": "grep -inE 'self[- ]?trade|self_match|STATE_UNKNOWN|kill.switch|呼値|tick size' SCAN_clean.md",
    "C2-8": "grep -inE '楽観|悲観|optimistic|pessimistic' docs/DATA/SCAN_2026-09-21_tools.md(REQUIREMENTS §3.1 C2-8: 台帳に列が無く、SCAN の grep で候補 0)",
    "C2-10": "grep -inE 'maker.{0,5}taker|手数料|\\bfee\\b|funding|資金調達|swap|スワップ' SCAN_clean.md",
    "C2-11": "grep -inE '証拠金|margin|レバレッジ|leverage|liquidat|強制決済|口座' SCAN_clean.md",
    "C2-12": "ls backtest_data | grep -iE 'jpx|n225|topix|225|kabu|tick'(委任文 §2 の項目 2 の行。JPX の板・ティックのデータ待ちは当方の状態で、調査報告に対応する道具の行は無い)",
}
GREP_CMD["C2-2"] = GREP_CMD["C2-1"]


def catalogue():
    with open(CAT, encoding="utf-8") as fh:
        rows = list(csv.reader(fh, delimiter="\t"))
    head = rows[0]
    return head, {r[0]: dict(zip(head, r)) for r in rows[1:]}


def resolve(name, cat):
    if name in ALIAS:
        return ALIAS[name]
    hit = [k for k, r in cat.items() if r["名前"] == name or r["名前"].endswith("/" + name) or name.endswith("/" + r["名前"])]
    assert len(hit) == 1, (name, hit)
    return hit[0]


def build():
    head, cat = catalogue()
    pool = []  # (viewpoint, cand, name, rule, scan_line)
    tsv_rules = {
        "C2-5": ("市場影響と約定の模型", "段(機構)"), "C2-7": ("市場影響と約定の模型", "段(機構)"),
        "C2-6": ("取り消しの扱い",), "C2-9": ("遅延",),
    }
    for vp, cols in tsv_rules.items():
        for k, r in cat.items():
            if any(r[c] for c in cols):
                pool.append((vp, k, r["名前"], "台帳の列 " + " か ".join(f"{c}(列 {head.index(c) + 1})" for c in cols) + " が空でない",
                             r["報告書の最後の記載の行"]))
    for vp, items in GREP.items():
        for name, lines in items:
            k = resolve(name, cat)
            pool.append((vp, k, cat[k]["名前"], f"REQUIREMENTS §3.2 の grep の当たり(名前「{name}」)", lines))
    order = {f"C2-{i}": i for i in range(1, 13)}
    pool.sort(key=lambda x: (order[x[0]], int(x[1])))
    return pool


def main():
    pool = build()
    with open(HERE / "pool.tsv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["viewpoint", "cand", "name", "rule", "scan_lines", "note"])
        for vp, k, name, rule, lines in pool:
            w.writerow([vp, k, name, rule, lines, ALIAS_WHY.get(k, "")])
    for vp in sorted({p[0] for p in pool} | set(GREP_CMD), key=lambda v: int(v.split("-")[1])):
        n = sum(1 for p in pool if p[0] == vp)
        print(vp, n)
    print("union", len({p[1] for p in pool}))


if __name__ == "__main__":
    main()
