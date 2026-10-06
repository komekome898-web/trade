#!/usr/bin/env python3
"""前提の直接の測り # 2(カツオ)の読み口。台本の出力 RESULT_{um,spot}.md の表を読み、次を出す(値は手で書かない)。

se は各行の MDE ÷ 2.8(表の MDE = 2.8 × se)。区間 = 点 ± 1.96 × se。
- 実 − 対照平均: 対照平均 = (24 時間前 + 24 時間後) ÷ 2。se は 実の se + 対照の se の平均 の和(保守。同じ日の値なので独立とみない)
- 実 − 24 時間前 / 実 − 24 時間後: se の和(保守)
- 全部の合図: 強い・弱いを件数で重み付けた点。se は重み × se の和(保守。同じ日なので独立とみない)
- 後半 − 前半: 2 つの半分は別の日なので se を √(a² + b²)
- 強い − 弱い、bitFlyer − 海外、60 分 − 15 分(終点): 同じ日・同じ合図なので se の和(保守)

使い方: python3 docs/RESEARCH/d1b/2_card2/read/contrast.py  → 同じ置き場の contrast.md
"""
from __future__ import annotations

import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
Z = 1.96
PERIODS = ("全期間", "前半", "後半")
SERIES = ("海外", "bitFlyer")
HORIZONS = ("1分", "5分", "15分", "60分")
KINDS = ("終点", "ヒゲと逆の向き(取引の向き)の一番深い点", "ヒゲの向き(取引に不利)の一番深い点")
KSHORT = {"終点": "終点", "ヒゲと逆の向き(取引の向き)の一番深い点": "有利の深い点", "ヒゲの向き(取引に不利)の一番深い点": "不利の深い点"}


def parse(src: str) -> dict:
    """{(強弱, 実/前/後, 系列, 時間, 種類, 区切り): (n, 点, se)}"""
    out, sec = {}, None
    for line in open(os.path.join(BASE, f"RESULT_{src}.md"), encoding="utf-8"):
        m = re.match(r"## 合図\((強い|弱い)\)— (実|24 時間前|24 時間後)", line)
        if m:
            sec = (m.group(1), {"実": "実", "24 時間前": "前", "24 時間後": "後"}[m.group(2)])
            continue
        if sec and line.startswith("| ") and not line.startswith("| 量") and not line.startswith("|---"):
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(c) != 7 or c[1] not in PERIODS:
                continue
            ser, hz, kind = c[0].split(" ", 2)
            out[(sec[0], sec[1], ser, hz, kind, c[1])] = (int(c[2]), float(c[4]), float(c[6]) / 2.8)
    return out


def with_all(d: dict) -> dict:
    keys = {k[1:] for k in d if k[0] == "強い"}
    for k in keys:
        s, w = d[("強い",) + k], d[("弱い",) + k]
        n = s[0] + w[0]
        d[("全部",) + k] = (n, (s[0] * s[1] + w[0] * w[1]) / n, (s[0] * s[2] + w[0] * w[2]) / n)
    return d


def ci(p: float, se: float) -> str:
    return f"{p:+.2f} [{p - Z * se:+.2f}, {p + Z * se:+.2f}]"


def state(p: float, se: float) -> str:
    lo, hi = p - Z * se, p + Z * se
    return "正" if lo > 0 else ("負" if hi < 0 else "含む")


def contrast(d, st, ser, hz, kind, per, ctl="平均"):
    r = d[(st, "実", ser, hz, kind, per)]
    a, f = d[(st, "前", ser, hz, kind, per)], d[(st, "後", ser, hz, kind, per)]
    if ctl == "平均":
        return r[1] - (a[1] + f[1]) / 2, r[2] + (a[2] + f[2]) / 2
    c = a if ctl == "前" else f
    return r[1] - c[1], r[2] + c[2]


def outcome(h1, h2, diff) -> str:
    s1, s2, sd = state(*h1), state(*h2), state(*diff)
    if s1 == "正" and s2 == "正":
        return "続いている(縮んだ)" if sd == "負" else "続いている"
    if s1 == "正":
        return "崩れた" if sd == "負" else "決まらない"
    if s2 == "正":
        return "後半だけ"
    if s1 == "負" and s2 == "負":
        return "成り立たない(逆向き)"
    if s1 == "含む" and s2 == "負":
        return "後半は逆向き"
    return "決まらない"


def halves_diff(v1, v2):
    return v2[0] - v1[0], math.hypot(v1[1], v2[1])


def main() -> None:
    L = ["# # 2 カツオ — 読み口の表(`read/contrast.py` が出した。手で書いていない)", "",
         "値は bp、合図の向き(ヒゲと逆)に正。se = 表の MDE ÷ 2.8。区間の作りは台本の説明(この台本の先頭)。", ""]
    for src in ("um", "spot"):
        d = with_all(parse(src))
        L += [f"## {src}(合図の出所 = {'Binance USD-M' if src == 'um' else 'Binance 現物'})", ""]
        # 1. 主の量と終点の全部: 実 − 対照平均、半分ごと、後半 − 前半、d1_outcome
        L += ["### 1. 終点: 実 − 対照平均(保守)、前半・後半と判定", "",
              "| 合図 | 系列 | 時間 | 全期間 | 前半 | 後半 | 後半 − 前半 | 判定(d1_outcome の決まりを当てた) |", "|---|---|---|---|---|---|---|---|"]
        for st in ("全部", "強い", "弱い"):
            for ser in SERIES:
                for hz in HORIZONS:
                    v = {p: contrast(d, st, ser, hz, "終点", p) for p in PERIODS}
                    dd = halves_diff(v["前半"], v["後半"])
                    L.append(f"| {st} | {ser} | {hz} | {ci(*v['全期間'])} | {ci(*v['前半'])} | {ci(*v['後半'])} | {ci(*dd)} | {outcome(v['前半'], v['後半'], dd)} |")
        L.append("")
        # 2. 実だけと対照を別々に(全部の合図)
        L += ["### 2. 終点: 実・24 時間前・24 時間後を別々に、と 実 − 前・実 − 後(全部の合図、保守)", "",
              "| 系列 | 時間 | 区切り | 実 | 24 時間前 | 24 時間後 | 実 − 前 | 実 − 後 |", "|---|---|---|---|---|---|---|---|"]
        for ser in SERIES:
            for hz in HORIZONS:
                for p in PERIODS:
                    r, a, f = (d[("全部", x, ser, hz, "終点", p)] for x in ("実", "前", "後"))
                    L.append(f"| {ser} | {hz} | {p} | {ci(r[1], r[2])} | {ci(a[1], a[2])} | {ci(f[1], f[2])} | {ci(*contrast(d, '全部', ser, hz, '終点', p, '前'))} | {ci(*contrast(d, '全部', ser, hz, '終点', p, '後'))} |")
        L.append("")
        # 3. 一番深い点: 実 − 対照平均(全部・強い・弱い)
        L += ["### 3. 一番深い点: 実 − 対照平均(保守)", "",
              "| 合図 | 系列 | 時間 | 種類 | 全期間 | 前半 | 後半 |", "|---|---|---|---|---|---|---|"]
        for st in ("全部", "強い", "弱い"):
            for ser in SERIES:
                for hz in HORIZONS:
                    for kind in KINDS[1:]:
                        v = {p: contrast(d, st, ser, hz, kind, p) for p in PERIODS}
                        L.append(f"| {st} | {ser} | {hz} | {KSHORT[kind]} | {ci(*v['全期間'])} | {ci(*v['前半'])} | {ci(*v['後半'])} |")
        L.append("")
        # 4. 強い − 弱い(実 − 対照平均 どうし、保守)
        L += ["### 4. 強い − 弱い(どちらも 実 − 対照平均。se の和、保守)", "",
              "| 系列 | 時間 | 種類 | 全期間 | 前半 | 後半 |", "|---|---|---|---|---|---|"]
        for ser in SERIES:
            for hz in HORIZONS:
                for kind in KINDS:
                    row = []
                    for p in PERIODS:
                        a, b = contrast(d, "強い", ser, hz, kind, p), contrast(d, "弱い", ser, hz, kind, p)
                        row.append(ci(a[0] - b[0], a[1] + b[1]))
                    L.append(f"| {ser} | {hz} | {KSHORT[kind]} | " + " | ".join(row) + " |")
        L.append("")
        # 5. bitFlyer − 海外(終点、実 − 対照平均 どうし、保守)
        L += ["### 5. bitFlyer − 海外(終点、どちらも 実 − 対照平均。se の和、保守)", "",
              "| 合図 | 時間 | 全期間 | 前半 | 後半 |", "|---|---|---|---|---|"]
        for st in ("全部", "強い", "弱い"):
            for hz in HORIZONS:
                row = []
                for p in PERIODS:
                    a, b = contrast(d, st, "bitFlyer", hz, "終点", p), contrast(d, st, "海外", hz, "終点", p)
                    row.append(ci(a[0] - b[0], a[1] + b[1]))
                L.append(f"| {st} | {hz} | " + " | ".join(row) + " |")
        L.append("")
        # 6. 60 分 − 15 分(終点。カードが建てた後の 45 分に近い量)
        L += ["### 6. 60 分 − 15 分の終点(T + 15 分から T + 60 分の動き。カードが建てた後の 45 分に近い量。どちらも 実 − 対照平均、se の和、保守)", "",
              "| 合図 | 系列 | 全期間 | 前半 | 後半 |", "|---|---|---|---|---|"]
        for st in ("全部", "強い", "弱い"):
            for ser in SERIES:
                row = []
                for p in PERIODS:
                    a, b = contrast(d, st, ser, "60分", "終点", p), contrast(d, st, ser, "15分", "終点", p)
                    row.append(ci(a[0] - b[0], a[1] + b[1]))
                L.append(f"| {st} | {ser} | " + " | ".join(row) + " |")
        L.append("")
    with open(os.path.join(HERE, "contrast.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()


# ---- 年ごと(記述)と分位(関門 ② 1 回目の止める 1 で足した。result_<出所>.json の各表の「年ごと(記述)」「分位」から)
def _json(src):
    import json
    return json.load(open(os.path.join(BASE, f"result_{src}.json"), encoding="utf-8"))["表"]


def _cell(t, st, ctl, ser, hz, kind, year):
    """(n, 点, se)。st = 強い・弱い・全部(全部は件数の重み、se は重み × se の和の保守)。"""
    if st == "全部":
        a, b = _cell(t, "強い", ctl, ser, hz, kind, year), _cell(t, "弱い", ctl, ser, hz, kind, year)
        if a is None or b is None:
            return None
        n = a[0] + b[0]
        return n, (a[0] * a[1] + b[0] * b[1]) / n, (a[0] * a[2] + b[0] * b[2]) / n
    x = t[f"{st}|{ctl}|{ser}|{hz}|{kind}"]["年ごと(記述)"].get(year)
    return None if x is None else (x["n"], x["estimate"], x["se"])


def years_section():
    L = []
    for src in ("um", "spot"):
        t = _json(src)
        years = sorted(t[f"強い|実|bitFlyer|15分|終点"]["年ごと(記述)"])
        L += [f"## 年ごと({src}。実 − 対照平均、保守。記述)", "",
              "| 合図 | 系列 | 時間 | " + " | ".join(years) + " |", "|---|---|---|" + "---|" * len(years)]
        for st in ("全部", "強い", "弱い"):
            for ser in SERIES:
                for hz in HORIZONS:
                    row = []
                    for y in years:
                        r, a, f = (_cell(t, st, c, ser, hz, "終点", y) for c in ("実", "24 時間前", "24 時間後"))
                        if None in (r, a, f):
                            row.append("—")
                            continue
                        row.append(ci(r[1] - (a[1] + f[1]) / 2, r[2] + (a[2] + f[2]) / 2))
                    L.append(f"| {st} | {ser} | {hz} | " + " | ".join(row) + " |")
        L += ["", f"## 分位({src}。実の終点、1 合図の値、bp。全期間)", "",
              "| 合図 | 系列 | 時間 | q05 | q25 | q50 | q75 | q95 |", "|---|---|---|---|---|---|---|---|"]
        for st in ("強い", "弱い"):
            for ser in SERIES:
                for hz in HORIZONS:
                    q = t[f"{st}|実|{ser}|{hz}|終点"]["分位"]
                    L.append(f"| {st} | {ser} | {hz} | " + " | ".join(f"{q[k]:+.2f}" for k in ("q05", "q25", "q50", "q75", "q95")) + " |")
        L.append("")
    return L


if __name__ == "__main__":
    with open(os.path.join(HERE, "contrast.md"), "a", encoding="utf-8") as fh:
        fh.write("\n".join(years_section()) + "\n")
