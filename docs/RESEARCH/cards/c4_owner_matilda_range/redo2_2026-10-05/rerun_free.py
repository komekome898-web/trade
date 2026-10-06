"""カード 4 の走らせ直し(L-717、rerun_2026-10-06)の読み: 仮定に左右されない部分の前半・後半と、出の理由ごとの区間。

読み口 `scripts/analysis/diag_tables.py` の関数(load_run・daily_series・d1・group_table)を呼ぶだけ。新しい計算は無い。
仮定に左右されない部分 = 決まらない足を含まない取引(undecided == 0)だけ(diag_tables.d8 と同じ切り方)。

    PYTHONPATH=src:scripts/analysis python3 docs/RESEARCH/cards/c4_owner_matilda_range/redo2_2026-10-05/rerun_free.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../../../../.."))
sys.path.insert(0, os.path.join(ROOT, "scripts/analysis"))
import diag_tables as dt  # noqa: E402

RUN = os.path.join(ROOT, "docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim/rerun_2026-10-06")
OUT = os.path.join(HERE, "rerun_free.md")


def ci(r: dict) -> str:
    return dt._ci(r)


def main() -> int:
    lines = ["# カード 4 の走らせ直し A1_center_4_3: 仮定に左右されない部分の前半・後半と、出の理由ごとの区間", "",
             "`rerun_free.py` が出した(読み口 `diag_tables.py` の関数を呼ぶだけ)。bp、経費の前。区間 95%(日の塊 5 日・1,000 回・種 20261004)。",
             "仮定に左右されない部分 = 決まらない足を含まない取引だけ。決まらない足を含まない取引は、含む取引と性質が違う(利確に届かずに止まった取引に寄る)ので、戦略の損益の見積もりではない。", ""]
    for side in ("good", "bad"):
        run = dt.load_run(os.path.join(RUN, f"A1_center_4_3_{side}"))
        days = dt.period_days(run)
        free = dict(run, trades=[t for t in run["trades"] if t.get("undecided", 0) == 0])
        und = dict(run, trades=[t for t in run["trades"] if t.get("undecided", 0) > 0])
        lines += [f"## {side}(良い側 = good・悪い側 = bad)", ""]
        for label, r in (("全部の取引", run), ("仮定に左右されない部分(決まらない足を含まない取引)", free),
                         ("決まらない足を含む取引", und)):
            res = dt.d1(dt.daily_series(r))
            s = res["segments"]
            lines += [f"### {label}(取引 {len(r['trades'])} 本)の 1 日あたり(bp/日)", "",
                      "| 期間 | 日数 | 1 日あたり [区間] | MDE | 区間が 0 を |", "|---|---|---|---|---|"]
            for row in res["rows"]:
                lines.append(f"| {row['label']} | {row['n']} | {ci(row)} | {dt._f(row.get('mde'))} | {row['zero']} |")
            lines += ["", "| 区切り | 期間 | 1 日あたり [区間] |", "|---|---|---|",
                      f"| 前半 | {s['first']['from']}〜{s['first']['to']} | {ci(s['first'])} |",
                      f"| 後半 | {s['second']['from']}〜{s['second']['to']} | {ci(s['second'])} |",
                      f"| 後半 − 前半 | | {ci(s['diff'])} |", "", f"- 結果(d1_outcome): **{s['outcome']}**", ""]
        lines += ["### 出の理由 × 決まらない足の有無【結果で決まる群】ごとの 1 取引あたり(bp)", "",
                  "| 群 | 取引 | 和 | 1 取引あたり [区間] |", "|---|---|---|---|"]
        key = lambda t: f"{t.get('exit_reason', '')} / {'決まらない足を含む' if t.get('undecided', 0) > 0 else '含まない'}"
        for g, r in dt.group_table(run["trades"], days, key).items():
            lines.append(f"| {g} | {r['trades']} | {r['sum']:+.0f} | {ci(r)} |")
        h = len(days) // 2
        for lab, dd in (("前半", days[:h]), ("後半", days[h:])):
            ds = set(dd)
            sub = [t for t in run["trades"] if dt.utc_day(t["exit_ns"]) in ds]
            lines += ["", f"出の理由 × 決まらない足の有無、{lab}({dd[0]}〜{dd[-1]}):", "",
                      "| 群 | 取引 | 和 | 1 取引あたり [区間] |", "|---|---|---|---|"]
            for g, r in dt.group_table(sub, dd, key).items():
                lines.append(f"| {g} | {r['trades']} | {r['sum']:+.0f} | {ci(r)} |")
        lines.append("")
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
