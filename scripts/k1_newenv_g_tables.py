#!/usr/bin/env python3
"""K1 段階 G: 実行記録(docs/PHASE2/K1/NEWENV_G/runs_index.json → backtest_runs/k1_newenv_g/<run_id>/trades.json.gz)
から升ごとの数を作る。規則は RESULT.md 1.4・1.5 と 11.7(年ごとの総損益 = 年別 n × 年別平均):
  r = sig × (決済値 / 建値 − 1) × 1e4 [bp](sig = 買い +1 / 売り −1)
  年 = 建てた足の開始時刻の UTC の年(建てた約定の時刻 = 足の閉じる時刻 − 足の長さ)
  95% 区間 = 建てた足の UTC の日でブロックに切り、日を復元抽出、200 回、種 20260909。
    種は升ごとに固定(XVENUE_PREREG.md 「区間はセルごとに種を固定」)。分位の添字は RESULT.md 1.5 の
    2.5% / 97.5% を 200 個の平均の並びに当てる(int(0.025 × 199)・int(0.975 × 199))
  30 取引未満の升は出さない(RESULT.md 1.5)
出力: docs/PHASE2/K1/NEWENV_G/cells.json
"""
from __future__ import annotations

import gzip
import json
import os
import random
import sys
from datetime import datetime, timezone

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(REPO, "docs", "PHASE2", "K1", "NEWENV_G")
RUNS = os.path.join(REPO, "backtest_runs", "k1_newenv_g")
NS = 1_000_000_000
SEED, REPS = 20260909, 200


def trades_of(run_id: str) -> list:
    with gzip.open(os.path.join(RUNS, run_id, "trades.json.gz"), "rt", encoding="utf-8") as fh:
        return json.load(fh)["data"]


def stats(trades: list, foot: int) -> dict:
    rs, byday, byyear = [], {}, {}
    for t in trades:
        sig = 1 if t["side"] == "buy" else -1
        r = sig * (t["exit_px"] / t["entry_px"] - 1.0) * 1e4
        start_s = (t["entry_t_ns"] - foot * 60 * NS) // NS
        rs.append(r)
        byday.setdefault(start_s // 86400, []).append(r)
        byyear.setdefault(str(datetime.fromtimestamp(start_s, tz=timezone.utc).year), []).append(r)
    n = len(rs)
    out = {"n": n, "mean_bp": sum(rs) / n if n else None, "total_bp": sum(rs),
           "per_year": {y: {"n": len(v), "mean_bp": sum(v) / len(v), "total_bp": sum(v)} for y, v in sorted(byyear.items())},
           "exit_reasons": {}}
    for t in trades:
        out["exit_reasons"][t["reason"]] = out["exit_reasons"].get(t["reason"], 0) + 1
    if n >= 30:
        rng = random.Random(SEED)
        days = list(byday.values())
        means = []
        for _ in range(REPS):
            pool = []
            for _ in range(len(days)):
                pool.extend(days[rng.randrange(len(days))])
            means.append(sum(pool) / len(pool))
        means.sort()
        out["ci95_bp"] = [means[int(0.025 * (REPS - 1))], means[int(0.975 * (REPS - 1))]]
    else:
        out["ci95_bp"] = None
        out["note"] = "30 取引未満(RESULT.md 1.5 により表に出さない)"
    return out


def main() -> None:
    with open(os.path.join(OUT, "runs_index.json"), encoding="utf-8") as fh:
        index = json.load(fh)
    cells = {}
    for k, v in sorted(index.items()):
        if not v.get("identical"):
            cells[k] = {"error": "2 回の実行が同じ bytes でない", "run_id": v["run_id"]}
            continue
        c = stats(trades_of(v["run_id"]), v["foot"])
        c["run_id"] = v["run_id"]
        cells[k] = c
    with open(os.path.join(OUT, "cells.json"), "w", encoding="utf-8") as fh:
        json.dump(cells, fh, ensure_ascii=False, indent=0, sort_keys=True)
    print(f"cells {len(cells)} -> {os.path.join(OUT, 'cells.json')}")


if __name__ == "__main__" and "--md" not in sys.argv:
    main()


# ---------------------------------------------------------------------------
# TABLES.md(--md): cells.json と FOLD_MANIFEST.json から表を書く
# ---------------------------------------------------------------------------
GATE_ORDER = ["soff/b24", "soff/b40", "s-/b-", "s-/b24", "s-/b40", "s10/b-", "s10/b24", "s10/b40", "s19/b-",
              "s19/b24", "s19/b40", "s30/b-", "s30/b40"]
FEET = (1, 3, 5, 15, 30, 60)
CMD = ("PYTHONPATH=scripts:src python3 scripts/k1_newenv_g_tables.py && "
       "PYTHONPATH=scripts:src python3 scripts/k1_newenv_g_tables.py --md")


def f2(x):
    return "—" if x is None else f"{x:+.2f}"


def ci(c):
    if not c.get("ci95_bp"):
        return "(30 取引未満)"
    lo, hi = c["ci95_bp"]
    star = "\\*" if lo > 0 or hi < 0 else ""
    return f"{c['mean_bp']:+.2f}{star} [{lo:+.2f}, {hi:+.2f}]"


def year_rows(c, years, last_note):
    out = []
    for y in years:
        v = c["per_year"].get(y)
        lab = f"{y}{last_note if y == years[-1] else ''}"
        out.append(f"| {lab} | {v['n']:,} | {v['mean_bp']:+.2f} | {v['total_bp']:+,.0f} |" if v else f"| {lab} | — | — | — |")
    return out


def render() -> None:
    cells = json.load(open(os.path.join(OUT, "cells.json"), encoding="utf-8"))
    man = json.load(open(os.path.join(REPO, "backtest_data", "k1_newenv_g_20261001", "FOLD_MANIFEST.json"), encoding="utf-8"))
    L = ["# K1 段階 G — 第 17 部の表を新しい環境で(2018-01-01〜2023-12-17)", "",
         "生成: `" + CMD + "`(実行記録 `docs/PHASE2/K1/NEWENV_G/runs_index.json` → `backtest_runs/k1_newenv_g/<run_id>/trades.json.gz`、数は `cells.json`)。",
         "設計 = H1+H2a+H3、シグナル = Binance BTCUSDT 現物、約定 = bitFlyer FX_BTC_JPY の次の足の終値、門 `s19/b24`、強さ「弱い」。経費前・建玉 1 単位。",
         "**2023 は 2023-01-01〜2023-12-17**(P2-08 の封印の境 2023-12-18T00:00Z より前だけ。委任文 L-495「**案1で進めてください**」)。2024〜2026 は読んでいない。",
         "区間 = 建てた足の日でブロック、200 回、種 20260909 を升ごとに固定。`*` = 区間が 0 を跨がない。", ""]
    L += ["## (a) 主統計", ""]
    for foot in (5, 15):
        L += [f"### {foot} 分", "", "年別(実行 `design|full`: 2017-08-17〜2023-12-17 を 1 本で読んだもの。当時の第 17 部 17.1 と同じ読み始め)", "",
              "| 年 | 取引数 | 平均 bp | 総損益 bp |", "|---|---|---|---|"]
        c = cells.get(f"design|full|{foot}|s19/b24|weak")
        L += year_rows(c, [str(y) for y in range(2018, 2024)], "(〜12-17)") if c else ["| (測っていない) | | | |"]
        L += ["", "期間(その期間だけを読んだ別の実行。当時の「サブ実行」と同じ作り)", "", "| 期間 | 平均 [95% 区間] | 取引数 | 総損益 bp |", "|---|---|---|---|"]
        for r, lab in (("2018_2021", "2018-01-01〜2021-12-31"), ("2022_20231217", "**2022-01-01〜2023-12-17**(当時の値は無い)")):
            c = cells.get(f"design|{r}|{foot}|s19/b24|weak")
            L.append(f"| {lab} | {ci(c)} | {c['n']:,} | {c['total_bp']:+,.0f} |" if c else f"| {lab} | (測っていない) | | |")
        L.append("")
    L += ["## (b) 78 升(足 6 × 門 13、弱い)の年別総損益の符号(2022、2023〜12-17)", "",
          "実行 `design|2022_20231217`(2022-01-01 から読み始めた 1 本)。正 = 年の総損益 > 0。", ""]
    cnt = {"2022": [0, 0], "2023": [0, 0]}
    rows = ["| 門 | 足 | 2022 総損益 (n) | 2023〜12-17 総損益 (n) |", "|---|---|---|---|"]
    for g in GATE_ORDER:
        for foot in FEET:
            c = cells.get(f"design|2022_20231217|{foot}|{g}|weak")
            if not c:
                rows.append(f"| `{g}` | {foot} 分 | (測っていない) | (測っていない) |")
                continue
            cs = []
            for y in ("2022", "2023"):
                v = c["per_year"].get(y)
                if v:
                    cnt[y][1] += 1
                    cnt[y][0] += v["total_bp"] > 0
                    cs.append(f"{v['total_bp']:+,.0f} ({v['n']:,}){' ○' if v['total_bp'] > 0 else ''}")
                else:
                    cs.append("取引なし")
            rows.append(f"| `{g}` | {foot} 分 | {cs[0]} | {cs[1]} |")
    L += [f"- 2022: 正 **{cnt['2022'][0]} / {cnt['2022'][1]}** 升(測った升の数が 78 でなければ残りは測っていない)",
          f"- 2023(〜12-17): 正 **{cnt['2023'][0]} / {cnt['2023'][1]}** 升", ""] + rows + [""]
    L += ["## (c) 参考列(門 `s19/b24`、弱い)", "",
          "(i) = 同じシグナルを Binance の終値で値付け(結合していない Binance の足、実行 `single|full_unjoined`)。(ii) は出さない(委任文 §2-2)。"
          "(iii) = bitFlyer の同じ窓の終値で値付け(H3 を外す。取れない価格、実行 `sameclose|*`)。", ""]
    for foot in (5, 15):
        L += [f"### {foot} 分", "", "| 年 | 横断(設計) | (i) Binance の終値 | (iii) bitFlyer 同じ窓 |", "|---|---|---|---|"]
        d, i1, i3 = (cells.get(f"{m}|{r}|{foot}|s19/b24|weak") for m, r in
                     (("design", "full"), ("single", "full_unjoined"), ("sameclose", "full")))
        for y in [str(x) for x in range(2018, 2024)]:
            vals = []
            for c in (d, i1, i3):
                v = c and c["per_year"].get(y)
                vals.append(f"{v['mean_bp']:+.2f} ({v['n']:,})" if v else "(測っていない)")
            L.append(f"| {y}{'(〜12-17)' if y == '2023' else ''} | " + " | ".join(vals) + " |")
        vals = [ci(c) + f" (n {c['n']:,})" if c else "(測っていない)" for c in (d, i1, i3)]
        L.append("| 全期間(2017-08-17〜2023-12-17) | " + " | ".join(vals) + " |")
        for r, lab in (("2018_2021", "2018〜2021(別の実行)"), ("2022_20231217", "2022-01-01〜2023-12-17(別の実行)")):
            c = cells.get(f"sameclose|{r}|{foot}|s19/b24|weak")
            L.append(f"| {lab} | {ci(cells[f'design|{r}|{foot}|s19/b24|weak']) if cells.get(f'design|{r}|{foot}|s19/b24|weak') else '(測っていない)'} | — | {ci(c) if c else '(測っていない)'} |")
        L.append("")
    L += ["## (e) 結合の統計(UTC の分の内部結合で落ちた分の割合)", "",
          "出所 `backtest_data/k1_newenv_g_20261001/FOLD_MANIFEST.json: alignment`(`scripts/k1_newenv_g_fold.py`)。2017 の bitFlyer は 1 月から読んだので落ちる割合が大きい(Binance は 2017-08-17 から)。", "",
          "| 年 | Binance の分 | bitFlyer の分 | 両方 | Binance 側で落ちた割合 | bitFlyer 側で落ちた割合 |", "|---|---|---|---|---|---|"]
    for y, v in man["alignment"].items():
        L.append(f"| {y}{'(〜12-17)' if y == '2023' else ''} | {v['minutes_signal']:,} | {v['minutes_price']:,} | {v['minutes_both']:,} | "
                 f"{v['dropped_share_signal']:.2%} | {v['dropped_share_price']:.2%} |")
    L += ["", "## 第 18 部(Bybit → bitFlyer、2022〜2023)", "",
          "**回していない**: 入力の Bybit 1 分足がディスクに無い(`ENV_DEFECTS.md` G-5)。表は出ていない。", "",
          "## 出さないもの", "", "ボラ三分位 (d)(委任文 §2-2)/ 参考列 (ii)(同)/ 両方・強い (f)(委任文 §2-2 の表の項目に無い)。"]
    with open(os.path.join(OUT, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("TABLES.md written")


if __name__ == "__main__" and "--md" in sys.argv:
    render()
