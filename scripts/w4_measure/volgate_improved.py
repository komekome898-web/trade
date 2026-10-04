#!/usr/bin/env python3
"""前の日の荒れ具合の門(日の版)を、改良の周 2 の後の形に当て直す(L-627 の段取り 3、L-619「改良途中の戦略については
改良が終わってから当て直す必要があります」、L-628「ア」= 段取り 1〜3 が済んだら窓へ)。

読み方の決まり(表を見る前に、この台本と `tests/research/test_volgate_improved.py` で固めた):

V1 系列(改良した形。K-047・K-048 の読みでリードが決めた形と、比べの相手):
   カツオ = weak_f15_close_a_time6・weak_f15_close_a_time9(15 分・足の終値・時間で降りる・門なし)と基準 weak_f15_close_a。
   マチルダ = R2_ratio_gate_rolling_center_4_3(過去だけの比の門 × 中心から測る利確 4:3)の良い側・悪い側と、
   比べの相手 A1_center_4_3(利確だけ)の良い側・悪い側。
   日ごとの損益は overlap_daily.daily_from_trades(取引の記録 trades.json.gz、日本時間の日、出の時刻で数える)。
V2 日の区分: vol_split_daily.classify(前の日の bitFlyer FX の 1 分足の |対数の値動き| の平均を、前の暦年の日の
   三分位で切る。先読みなし。2017 年から)。区分の無い日は門の外(いつも入る)として数え、別に日数を出す。
V3 出すもの(系列ごと): 区分ごとの日数・1 日あたりの平均と 95% 区間(vol_split_daily.class_mean_ci、5 日の塊)。
   高 − 低 の差と 95% 区間(vol_split_daily.block_bootstrap_diff)。
V4 門の決まり(表を見る前に決めた): 「避ける区分 = その系列で 1 日あたりの平均の 95% 区間の上端が 0 以下の区分」。
   避ける区分があれば、門の取り分 = −(避ける区分の日の損益の和)÷ 分けた日と区分なしの日の合計の日数。
   無ければ「避ける区分なし」と書く。区間の上端がちょうど 0 も避ける。門は区分ごとに入る・入らないを決めるだけで、
   取引の中身は変えない(日の単位の近似。日をまたぐ持ち高は出の日で数える)。
V5 標本の中: 区分の境は先読みなしだが、避ける区分は同じデータの区間で選ぶので、門の取り分は標本の中の値。
   見ていない期間で試すのは段取り 6(窓、L-628)。経費なし。探索の読みで判定ではない。

出力: docs/RESEARCH/cards/VOLSPLIT/IMPROVED/TABLES.md と volgate.json。数字は手で書かない(research-protocol §1.2)。

    PYTHONPATH=src python3 scripts/w4_measure/volgate_improved.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import overlap_daily as ov  # noqa: E402
import vol_split_daily as vs  # noqa: E402

C2R = os.path.join(ov.REPO, "docs", "RESEARCH", "cards", "c2_owner_xvenue_wick", "limit_sim", "runs")
C4R = os.path.join(ov.REPO, "docs", "RESEARCH", "cards", "c4_owner_matilda_range", "limit_sim", "families_r2")
SERIES = (
    ("カツオ 時間で降りる N=6", os.path.join(C2R, "weak_f15_close_a_time6")),
    ("カツオ 時間で降りる N=9", os.path.join(C2R, "weak_f15_close_a_time9")),
    ("カツオ 基準(降り方なし)", os.path.join(C2R, "weak_f15_close_a")),
    ("マチルダ 過去だけの門 × 利確 4:3 良", os.path.join(C4R, "R2_ratio_gate_rolling_center_4_3_good")),
    ("マチルダ 過去だけの門 × 利確 4:3 悪", os.path.join(C4R, "R2_ratio_gate_rolling_center_4_3_bad")),
    ("マチルダ 利確 4:3 だけ 良", os.path.join(C4R, "A1_center_4_3_good")),
    ("マチルダ 利確 4:3 だけ 悪", os.path.join(C4R, "A1_center_4_3_bad")),
)
CLASSES = ("low", "mid", "high")
JA = {"low": "低", "mid": "中", "high": "高"}


def gate(pnl: dict[str, float], cls: dict[str, str], ci_by_class: dict[str, tuple]) -> dict:
    """V4。ci_by_class[c] = (平均, 下端, 上端)。"""
    avoid = [c for c in CLASSES if c in ci_by_class and ci_by_class[c][2] <= 0]
    days = list(pnl)
    if not avoid:
        return {"avoid": [], "take": None, "days": len(days)}
    lost = sum(pnl[d] for d in days if cls.get(d) in avoid)
    return {"avoid": avoid, "take": -lost / len(days), "days": len(days)}


def analyse(pnl: dict[str, float], cls: dict[str, str]) -> dict:
    days = sorted(pnl)
    out = {"days": len(days), "unclassified_days": sum(1 for d in days if d not in cls), "classes": {}}
    ci = {}
    for c in CLASSES:
        x = np.array([pnl[d] for d in days if cls.get(d) == c], dtype=float)
        if len(x) == 0:
            continue
        m, lo, hi = vs.class_mean_ci(x)
        ci[c] = (m, lo, hi)
        out["classes"][c] = {"days": int(len(x)), "mean": m, "lo": lo, "hi": hi}
    dd, lo, hi = vs.block_bootstrap_diff([d for d in days if d in cls], pnl, cls)
    out["high_minus_low"] = {"diff": dd, "lo": lo, "hi": hi}
    out["gate"] = gate(pnl, cls, ci)
    return out


def render(res: dict) -> str:
    L = ["# 前の日の荒れ具合の門(日の版)を改良した形に当て直す", "",
         "`scripts/w4_measure/volgate_improved.py` が出した。読み方の決まり V1〜V5 はその台本の docstring。経費の前。bp/日。"
         "門の取り分は標本の中の値。", "",
         "| 系列 | 日数(区分なし) | 低 平均 [区間] 日数 | 中 | 高 | 高 − 低 [区間] | 避ける区分 | 門の取り分 |",
         "|---|---|---|---|---|---|---|---|"]
    for name, r in res.items():
        cells = []
        for c in CLASSES:
            k = r["classes"].get(c)
            cells.append("—" if not k else f"{k['mean']:+.2f} [{k['lo']:+.2f}, {k['hi']:+.2f}] {k['days']}")
        hl = r["high_minus_low"]
        hls = "—" if not hl else f"{hl['diff']:+.2f} [{hl['lo']:+.2f}, {hl['hi']:+.2f}]"
        g = r["gate"]
        av = "なし" if not g["avoid"] else "・".join(JA[c] for c in g["avoid"])
        tk = "—" if g["take"] is None else f"{g['take']:+.2f}"
        L.append(f"| {name} | {r['days']}({r['unclassified_days']}) | " + " | ".join(cells) + f" | {hls} | {av} | {tk} |")
    return "\n".join(L) + "\n"


def main() -> int:
    cls = vs.classify(vs.daily_vol(vs.load_closes_by_day()))
    res = {}
    for name, d in SERIES:
        pnl = ov.load_series("trades", d)
        res[name] = analyse(pnl, cls)
    out = os.path.join(ov.REPO, "docs", "RESEARCH", "cards", "VOLSPLIT", "IMPROVED")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write(render(res))
    with open(os.path.join(out, "volgate.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=float)
    print(f"series {len(res)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
