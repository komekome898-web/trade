#!/usr/bin/env python3
"""K1 段階 G: 新しい環境の数(docs/PHASE2/K1/NEWENV_G/cells.json)と当時の数(old_values.json、
scripts/k1_newenv_g_old.py が effect_*.json から機械で読んだもの)を升ごとに並べ、裁きの材料を作る。

升の対応(当時の実行と同じ読み始めの実行どうしだけを比べる。建玉の機械は読み始めの状態に依るため):
  新 design|full(2017-08-17〜2023-12-17)の年別       ↔ 当時 effect_binance_to_bitflyer.json(2017-08-17〜2026-08-31)の年別
  新 design|2018_2021 の年別・期間                     ↔ 当時 effect_binance_to_bitflyer_2018_2021.json
  新 design|2022_20231217 の 2022                      ↔ 当時 effect_binance_to_bitflyer_2022_2026.json の 2022
  sameclose も同じ対応(当時 *_sameclose*.json)
  新 single|full_unjoined の年別                       ↔ 当時 results/PHASE2/K1/binance/effect_flip_noinval_delay.json
一致 = 取引数が同じ かつ 平均 bp を当時の桁(小数 3 桁)に丸めて同じ。区間は当時と乱数の使い方が違う(DIFF.md D-3)ので並べるだけ。
2023 の升(当時 2023-01-01〜12-31、今回 2023-12-17 まで)は「比べられない(封印、2023 は区間が違う)」、
2024〜2026 の年と、境より後を含む当時の期間(2017-08-17〜2026-08-31・2022〜2026)の升は「比べられない(封印)」。
この印は升ごとに 1 行ずつ diff_rows.json(鍵 "sealed")と diff_table.md に出す(批評家の指摘 3、
docs/AUDITOR/VERDICTS/2026-10-01_k1_stage_g.md)。
出力: docs/PHASE2/K1/NEWENV_G/diff_rows.json と標準出力の要約(--md で diff_table.md・diff_summary.json)。
"""
from __future__ import annotations

import json
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(REPO, "docs", "PHASE2", "K1", "NEWENV_G")
PAIRS = [  # (新の range, 当時のファイルの tag, 比べる年)
    ("design", "full", "design|full", [str(y) for y in range(2018, 2023)]),
    ("design", "2018_2021", "design|2018_2021", [str(y) for y in range(2018, 2022)]),
    ("design", "2022_20231217", "design|2022_2026", ["2022"]),
    ("sameclose", "full", "sameclose|full", [str(y) for y in range(2018, 2023)]),
    ("sameclose", "2018_2021", "sameclose|2018_2021", [str(y) for y in range(2018, 2022)]),
    ("sameclose", "2022_20231217", "sameclose|2022_2026", ["2022"]),
    ("single", "full_unjoined", "single_unjoined|full", [str(y) for y in range(2018, 2023)]),
]


SEALED_YEARS = ("2023", "2024", "2025", "2026")
SEAL_2023 = "比べられない(封印、2023 は区間が違う)"
SEAL = "比べられない(封印)"
NEW_PERIOD = {"full": "2017-08-17〜2023-12-17", "full_unjoined": "2017-08-17〜2023-12-17",
              "2022_20231217": "2022-01-01〜2023-12-17"}


def same(n_new, m_new, o) -> bool:
    return o is not None and n_new == o["n"] and round(m_new, 3) == round(o["mean_bp"], 3)


def main() -> None:
    cells = json.load(open(os.path.join(OUT, "cells.json"), encoding="utf-8"))
    old = json.load(open(os.path.join(OUT, "old_values.json"), encoding="utf-8"))
    rows = []
    for mode, rng, otag, years in PAIRS:
        for k, c in sorted(cells.items()):
            m, r, foot, gate, st = k.split("|")
            if m != mode or r != rng or "error" in c:
                continue
            o = old.get(f"{otag}|{foot}|{gate}|{st}")
            for y in years:
                cy = c["per_year"].get(y)
                oy = (o or {}).get("per_year", {}).get(y)
                if cy is None and oy is None:
                    continue
                rows.append({"cell": k, "old_file": (o or {}).get("file"), "what": f"年 {y}",
                             "new_n": cy and cy["n"], "new_mean": cy and round(cy["mean_bp"], 3),
                             "new_total": cy and round(cy["total_bp"], 1),
                             "old_n": oy and oy["n"], "old_mean": oy and oy["mean_bp"],
                             "same": bool(cy and same(cy["n"], cy["mean_bp"], oy))})
            if rng == "2018_2021" and o is not None:
                rows.append({"cell": k, "old_file": o["file"], "what": "期間 2018〜2021",
                             "new_n": c["n"], "new_mean": round(c["mean_bp"], 3), "new_total": round(c["total_bp"], 1),
                             "new_ci": c["ci95_bp"] and [round(x, 3) for x in c["ci95_bp"]],
                             "old_n": o["n"], "old_mean": o["mean_bp"], "old_ci": o["ci95_bp"],
                             "same": same(c["n"], c["mean_bp"], o)})
            if o is None:
                continue
            # 封印の升(印だけ。値は 2023 の年の行だけ並べる。2024〜2026 は今回読んでいないので新しい値が無い)
            for y in SEALED_YEARS:
                cy = c["per_year"].get(y) if y == "2023" else None
                oy = o.get("per_year", {}).get(y)
                if oy is None and cy is None:
                    continue
                rows.append({"cell": k, "old_file": o["file"], "what": f"年 {y}",
                             "new_n": cy and cy["n"], "new_mean": cy and round(cy["mean_bp"], 3),
                             "new_total": cy and round(cy["total_bp"], 1),
                             "old_n": oy["n"] if (oy and y == "2023") else None,
                             "old_mean": oy["mean_bp"] if (oy and y == "2023") else None,
                             "same": None, "sealed": SEAL_2023 if y == "2023" else SEAL})
            ex = o.get("explore")
            if rng != "2018_2021" and ex and ex[1] >= "2023-12-18":
                rows.append({"cell": k, "old_file": o["file"], "what": f"期間 {ex[0]}〜{ex[1]}",
                             "new_n": None, "new_mean": None, "new_total": None,
                             "old_n": None, "old_mean": None, "same": None, "sealed": SEAL,
                             "new_period": NEW_PERIOD[rng]})
    with open(os.path.join(OUT, "diff_rows.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=0)
    n_same = sum(r["same"] is True for r in rows)
    n_seal = sum(bool(r.get("sealed")) for r in rows)
    print(f"rows {len(rows)} same {n_same} differ {len(rows) - n_same - n_seal} sealed {n_seal}")
    for r in rows:
        if r["same"] is False:
            print("DIFF", r["cell"], r["what"], r["new_n"], r["new_mean"], "| old", r["old_n"], r["old_mean"])


if __name__ == "__main__" and "--md" not in __import__("sys").argv:
    main()


# 批評家の再計算(docs/AUDITOR/VERDICTS/2026-10-01_k1_stage_g.md、批評家「確かめたこと」1 の 2 つの表。
# 規則の文から批評家が書いた別のコード <批評家の scratchpad>/critic/sim.py・full.py の出力。作業者のコードも当時のコードも使っていない)。
# 値 = (分で切り下げた結合 の (取引数, 平均 bp), 秒まで同じ時刻だけの結合 の (取引数, 平均 bp))。ここでは写して機械で突き合わせるだけ。
CRITIC_RECALC = {
    ("design|2018_2021|5", "年 2018"): ((4769, 2.277), (4745, 2.487)),
    ("design|2018_2021|15", "年 2018"): ((3414, 5.357), (3396, 5.141)),
    ("sameclose|2018_2021|5", "年 2018"): ((4769, 2.63), (4745, 2.754)),
    ("sameclose|2018_2021|15", "年 2018"): ((3414, 0.178), (3396, -0.012)),
    ("design|2018_2021|5", "期間 2018〜2021"): ((12999, 3.453), (12975, 3.532)),
    ("design|2018_2021|15", "期間 2018〜2021"): ((10666, 2.538), (10648, 2.464)),
    ("sameclose|2018_2021|5", "期間 2018〜2021"): ((12999, 3.506), (12975, 3.553)),
    ("sameclose|2018_2021|15", "期間 2018〜2021"): ((10666, -0.361), (10648, -0.422)),
    ("design|full|5", "年 2018"): ((4768, 2.282), (4744, 2.492)),
    ("design|full|15", "年 2018"): ((3414, 5.351), (3396, 5.134)),
    ("sameclose|full|5", "年 2018"): ((4768, 2.633), (4744, 2.757)),
    ("sameclose|full|15", "年 2018"): ((3413, 0.202), (3395, 0.011)),
}
CRITIC_SRC = "docs/AUDITOR/VERDICTS/2026-10-01_k1_stage_g.md 批評家「確かめたこと」1"


def _eq(a, b) -> bool:
    return a is not None and b is not None and a[0] == b[0] and abs(a[1] - b[1]) < 0.0005


def critic_match(r):
    """批評家の再計算と、新しい値 = 分で切り下げた結合・当時の値 = 秒まで同じ結合 の両方が合うか(None = 再計算が無い行)。"""
    m, rg, foot = r["cell"].split("|")[:3]
    c = CRITIC_RECALC.get((f"{m}|{rg}|{foot}", r["what"]))
    if c is None:
        return None, None
    return _eq((r["new_n"], r["new_mean"]), c[0]) and _eq((r["old_n"], r["old_mean"]), c[1]), c


def variant_covers(r) -> bool:
    """変種 *_2018_2019_offgriddrop(2018-01-01 から読む)が当時と同じ数になったかを確かめた行 = *_2018_2021 の年 2018 だけ。"""
    m, rg = r["cell"].split("|")[:2]
    return rg == "2018_2021" and r["what"] == "年 2018" and m in ("design", "sameclose")


def verdict(r, variant_ok: dict) -> tuple[str, str]:
    if r.get("sealed"):
        if r["what"] == "年 2023":
            return r["sealed"], ("当時は 2023-01-01〜12-31、今回は 2023-12-17 まで(P2-08 の境 2023-12-18T00:00Z)。"
                                 "当時の json に日次・取引ごとの記録が無く 12-17 で切れない(DIFF.md §2)。並べるだけ")
        if r["what"].startswith("年 "):
            return r["sealed"], ("P2-08 の封印の境より後の年。今回は読んでいない(委任文 L-495「案1で進めてください」)。"
                                 "比べる新しい値が無いので当時の値も並べない(old_values.json にはある)")
        return r["sealed"], (f"当時の期間は封印の境より後を含む。今回の実行は {r['new_period']} まで(TABLES.md)で期間が違う。"
                             "値は並べない")
    if r["same"]:
        return "一致", "取引数と平均(小数 3 桁)が同じ(数が同じという事実だけ)"
    if r["what"] in ("年 2018", "期間 2018〜2021"):
        ok, c = critic_match(r)
        rule = ("規則の文は「UTC の分で内部結合」。当時のコードは秒まで同じ時刻の行だけを結合し、"
                "分の境界に乗っていない Binance の行(2018 に 1,201 行)を落とした(推定、DIFF.md §3)。")
        crit = "" if c is None else (
            f"批評家の再計算({CRITIC_SRC})= 分で切り下げた結合 {c[0][0]} / {c[0][1]}、秒まで同じ結合 {c[1][0]} / {c[1][1]}"
            f" → 新しい値・当時の値の両方と{'一致' if ok else '不一致'}")
        if variant_covers(r) and variant_ok.get(r["cell"].split("|")[0]):
            return "当時の誤り(D-1)", (rule + "【変種が覆う行】変種(格子外れの行を落として畳んだ 2018〜2019、2018-01-01 から読む)で"
                                       "年 2018 が当時と同じ数になった(diff_summary.json: variant_2018)。" + crit)
        if ok:
            return "当時の誤り(D-1)", (rule + "【変種が覆っていない行】変種は読み始めが 2018-01-01 の年 2018 だけを覆い、"
                                       + ("読み始めが 2017-08-17 の実行" if r["cell"].split("|")[1] == "full" else "期間の行")
                                       + "は覆わない。" + crit)
    return "不明", "原因を確かめていない"


def write_md() -> None:
    rows = json.load(open(os.path.join(OUT, "diff_rows.json"), encoding="utf-8"))
    cells = json.load(open(os.path.join(OUT, "cells.json"), encoding="utf-8"))
    old = json.load(open(os.path.join(OUT, "old_values.json"), encoding="utf-8"))
    # 変種(格子外れの行を落として畳んだ 2018〜2019)の 2018 が当時の 2018 と同じ数か。モードごとに確かめる
    # (2026-10-01 08:3x UTC: sameclose の変種も回したので、sameclose の裁きも design の変種に寄りかからない)
    var, variant_ok = {}, {}
    for mode in ("design", "sameclose"):
        for f in ("5", "15"):
            c = cells.get(f"{mode}|2018_2019_offgriddrop|{f}|s19/b24|weak")
            o = old[f"{mode}|2018_2021|{f}|s19/b24|weak"]["per_year"]["2018"]
            var[f"{mode}|{f}"] = (c["per_year"]["2018"]["n"], round(c["per_year"]["2018"]["mean_bp"], 3), o["n"], o["mean_bp"]) if c else None
        variant_ok[mode] = all(v and v[0] == v[2] and v[1] == v[3] for k, v in var.items() if k.startswith(mode + "|"))
    L = ["| 升 | 何を | 当時(n / 平均) | 新(n / 平均) | 差(平均) | 裁き | 根拠 |", "|---|---|---|---|---|---|---|"]
    tally = {}
    cover = {"変種が覆う": [], "変種が覆っていない": []}
    for r in rows:
        v, why = verdict(r, variant_ok)
        tally[v] = tally.get(v, 0) + 1
        d = "" if r["new_mean"] is None or r["old_mean"] is None else f"{r['new_mean'] - r['old_mean']:+.3f}"
        if v.startswith("当時の誤り"):
            cover["変種が覆う" if variant_covers(r) else "変種が覆っていない"].append(f"{r['cell']} {r['what']}")
        if r.get("sealed"):
            d = ""  # 区間が違う・値が無いので差は出さない
            on = "(並べない)" if r["old_n"] is None else f"{r['old_n']} / {r['old_mean']}"
            nn = (f"(読んでいない: 今回は {r['new_period']})" if r["what"].startswith("期間") else
                  "(境より後は読んでいない)" if r["new_n"] is None and r["what"] != "年 2023" else
                  f"{r['new_n']} / {r['new_mean']}(〜12-17)" if r["new_n"] is not None else "取引なし")
            L.append(f"| `{r['cell']}` | {r['what']} | {on} | {nn} | {d} | **{v}** | {why} |")
            continue
        extra = ""
        if "new_ci" in r:
            extra = f"(区間 当時 {r['old_ci']} / 新 {r['new_ci']} は比べられない: D-3)"
        L.append(f"| `{r['cell']}` | {r['what']} | {r['old_n']} / {r['old_mean']} | {r['new_n']} / {r['new_mean']} | {d} | {v} | {why}{extra} |")
    # 78 升の 2022 の符号の数
    sign = {"new": 0, "old_2022_2026": 0, "old_full": 0, "measured": 0}
    for k, c in cells.items():
        m, rg, foot, g, st = k.split("|")
        if m != "design" or rg != "2022_20231217" or "error" in c or "2022" not in c["per_year"]:
            continue
        sign["measured"] += 1
        sign["new"] += c["per_year"]["2022"]["total_bp"] > 0
        for tag, key in (("design|2022_2026", "old_2022_2026"), ("design|full", "old_full")):
            oy = old.get(f"{tag}|{foot}|{g}|{st}", {}).get("per_year", {}).get("2022")
            sign[key] += bool(oy and oy["n"] * oy["mean_bp"] > 0)
    with open(os.path.join(OUT, "diff_table.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    json.dump({"tally": tally, "variant_2018": var, "variant_ok": variant_ok, "sign_2022": sign, "d1_cover": cover},
              open(os.path.join(OUT, "diff_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"tally": tally, "variant_2018": var, "sign_2022": sign,
                      "d1_cover": {k: len(v) for k, v in cover.items()}}, ensure_ascii=False))


if __name__ == "__main__" and "--md" in __import__("sys").argv:
    write_md()
