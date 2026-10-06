#!/usr/bin/env python3
"""前提の直接の測り # 3(円の上乗せの戻り)の読み口。台本の出力 RESULT_outside_onset_last1m.md の表を読み、次を出す(手で書かない)。

se は各行の MDE ÷ 2.8。区間 = 点 ± 1.96 × se。
- 実 − 対照平均: 対照平均 = (24 時間前 + 24 時間後) ÷ 2。se = 実の se + 対照の se の平均(保守。同じ日の値なので独立とみない)
- 後半 − 前半: 2 つの半分は別の日なので √(a² + b²)
- 脚の受け持ち: 各脚の 実 − 対照平均 ÷ 合計の 実 − 対照平均(点だけ。区間は出さない)

使い方: python3 docs/RESEARCH/d1b/3_card3/read/contrast.py → 同じ置き場の contrast.md
"""
from __future__ import annotations

import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
SRC = os.path.join(BASE, "RESULT_outside_onset_last1m.md")
Z = 1.96
PERIODS = ("全期間", "前半", "後半")
WINDOWS = ("1h", "1d", "1w")
CAUSES = ("全部", "bitFlyer", "Binance", "USDJPY", "不明")
HZ = ("1分", "5分", "15分", "60分")
LEGS = ("bitFlyer", "Binance", "USDJPY", "合計(上乗せの戻り)")
LSHORT = {"合計(上乗せの戻り)": "合計"}


def parse() -> dict:
    out, sec = {}, None
    for line in open(SRC, encoding="utf-8"):
        m = re.match(r"## 窓 (1h|1d|1w) — (実|24 時間前|24 時間後)", line)
        if m:
            sec = (m.group(1), {"実": "実", "24 時間前": "前", "24 時間後": "後"}[m.group(2)])
            continue
        if line.startswith("NaN の件数"):
            sec = None
            continue
        if sec and line.startswith("| 原因 "):
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(c) != 7 or c[1] not in PERIODS:
                continue
            cause, hz, leg = [x.strip() for x in c[0][len("原因 "):].split(" / ")]
            out[(sec[0], sec[1], cause, hz, leg, c[1])] = (int(c[2]), float(c[4]), float(c[6]) / 2.8)
    return out


def ci(p, se):
    return f"{p:+.2f} [{p - Z * se:+.2f}, {p + Z * se:+.2f}]"


def state(p, se):
    return "正" if p - Z * se > 0 else ("負" if p + Z * se < 0 else "含む")


def outcome(h1, h2, dd):
    s1, s2, sd = state(*h1), state(*h2), state(*dd)
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


def con(d, w, cause, hz, leg, per, ctl="平均"):
    r = d[(w, "実", cause, hz, leg, per)]
    a, f = d[(w, "前", cause, hz, leg, per)], d[(w, "後", cause, hz, leg, per)]
    if ctl == "平均":
        return r[1] - (a[1] + f[1]) / 2, r[2] + (a[2] + f[2]) / 2
    c = a if ctl == "前" else f
    return r[1] - c[1], r[2] + c[2]


def main():
    d = parse()
    L = ["# # 3 円の上乗せの戻り — 読み口の表(`read/contrast.py` が出した。手で書いていない)", "",
         "値は bp、上乗せが戻る向き(端の向き s に対して −s × Δ)に正。脚の和 = 合計。se = 表の MDE ÷ 2.8。区間の作りは台本の先頭。", ""]
    # 1. 合計(主の量の形)の 実 − 対照平均、判定
    L += ["## 1. 合計(上乗せの戻り): 実 − 対照平均(保守)、前半・後半と判定", "",
          "| 窓 | 原因の脚 | 時間 | 件数(全期間) | 全期間 | 前半 | 後半 | 後半 − 前半 | 判定 |", "|---|---|---|---|---|---|---|---|---|"]
    for w in WINDOWS:
        for cause in CAUSES:
            for hz in HZ:
                k = (w, "実", cause, hz, "合計(上乗せの戻り)", "全期間")
                if k not in d:
                    continue
                v = {p: con(d, w, cause, hz, "合計(上乗せの戻り)", p) for p in PERIODS}
                dd = (v["後半"][0] - v["前半"][0], math.hypot(v["前半"][1], v["後半"][1]))
                L.append(f"| {w} | {cause} | {hz} | {d[k][0]} | {ci(*v['全期間'])} | {ci(*v['前半'])} | {ci(*v['後半'])} | {ci(*dd)} | {outcome(v['前半'], v['後半'], dd)} |")
    L.append("")
    # 2. 実・前・後 を別々に(合計、全部の原因)
    L += ["## 2. 合計: 実・24 時間前・24 時間後を別々に(原因 全部)", "",
          "| 窓 | 時間 | 区切り | 実 | 24 時間前 | 24 時間後 |", "|---|---|---|---|---|---|"]
    for w in WINDOWS:
        for hz in HZ:
            for p in PERIODS:
                r, a, f = (d[(w, x, "全部", hz, "合計(上乗せの戻り)", p)] for x in ("実", "前", "後"))
                L.append(f"| {w} | {hz} | {p} | {ci(r[1], r[2])} | {ci(a[1], a[2])} | {ci(f[1], f[2])} |")
    L.append("")
    # 3. 脚の分け: 実 − 対照平均、原因の脚ごと
    L += ["## 3. 脚の分け: 実 − 対照平均(保守)と受け持ち(脚 ÷ 合計、点)", "",
          "| 窓 | 原因の脚 | 時間 | 区切り | bitFlyer の脚 | Binance の脚 | USDJPY の脚 | 受け持ち bitFlyer : Binance : USDJPY |", "|---|---|---|---|---|---|---|---|"]
    for w in WINDOWS:
        for cause in CAUSES:
            for hz in HZ:
                if (w, "実", cause, hz, "bitFlyer", "全期間") not in d:
                    continue
                for p in PERIODS:
                    vs = [con(d, w, cause, hz, leg, p) for leg in LEGS]
                    tot = vs[3][0]
                    sh = " : ".join(f"{v[0] / tot:.2f}" for v in vs[:3]) if abs(tot) > 1e-9 else "—"
                    L.append(f"| {w} | {cause} | {hz} | {p} | {ci(*vs[0])} | {ci(*vs[1])} | {ci(*vs[2])} | {sh} |")
    L.append("")
    # 4. 実だけの脚の分け(対照を引く前、原因 全部と原因ごとの全期間)
    L += ["## 4. 脚の分け: 実だけ(対照を引く前)", "",
          "| 窓 | 原因の脚 | 時間 | 区切り | bitFlyer の脚 | Binance の脚 | USDJPY の脚 | 合計 |", "|---|---|---|---|---|---|---|---|"]
    for w in WINDOWS:
        for cause in CAUSES:
            for hz in HZ:
                if (w, "実", cause, hz, "bitFlyer", "全期間") not in d:
                    continue
                for p in PERIODS:
                    vs = [d[(w, "実", cause, hz, leg, p)] for leg in LEGS]
                    L.append(f"| {w} | {cause} | {hz} | {p} | " + " | ".join(ci(v[1], v[2]) for v in vs) + " |")
    L.append("")
    with open(os.path.join(HERE, "contrast.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()


# ---- 年ごと(記述)。result_outside_onset_last1m.json の各表の「年ごと(記述)」から(# 2 の関門 ② 1 回目の止める 1 を受けて、読む前に足した)
def years_section():
    import json
    W = json.load(open(os.path.join(BASE, "result_outside_onset_last1m.json"), encoding="utf-8"))["窓"]

    def cell(w, ctl, hz, cause, leg, y):
        x = W[w][f"{ctl}|{hz}|原因 {cause}|{leg}"]["年ごと(記述)"].get(y)
        return None if x is None else (x["n"], x["estimate"], x["se"])

    years = sorted(W["1d"]["実|60分|原因 全部|合計(上乗せの戻り)"]["年ごと(記述)"])
    L = ["## 5. 年ごと(実 − 対照平均、保守。記述)", "",
         "| 窓 | 原因の脚 | 時間 | 脚 | " + " | ".join(years) + " |", "|---|---|---|---|" + "---|" * len(years)]
    rows = [(w, "全部", hz, "合計(上乗せの戻り)") for w in WINDOWS for hz in ("1分", "60分")]
    rows += [("1d", c, hz, leg) for c in ("全部", "bitFlyer", "Binance", "USDJPY") for hz in ("1分", "5分", "60分")
             for leg in ("bitFlyer", "Binance", "USDJPY")]
    for w, cause, hz, leg in rows:
        out = []
        for y in years:
            r, a, f = (cell(w, c, hz, cause, leg, y) for c in ("実", "24 時間前", "24 時間後"))
            if None in (r, a, f):
                out.append("—")
                continue
            out.append(ci(r[1] - (a[1] + f[1]) / 2, r[2] + (a[2] + f[2]) / 2))
        L.append(f"| {w} | {cause} | {hz} | {LSHORT.get(leg, leg)} | " + " | ".join(out) + " |")
    L.append("")
    return L


if __name__ == "__main__":
    with open(os.path.join(HERE, "contrast.md"), "a", encoding="utf-8") as fh:
        fh.write("\n".join(years_section()) + "\n")
