#!/usr/bin/env python3
"""カード 9 (a) の 3 択の規則を、材料に |m10|・|m60| の水準を足して作り直す(2026-10-03、関門 ② の 2 回目の監査「止める 3」)。

走らせの 3 択(`liq_cascade_v2.fit_three_way`、材料 13 本)と同じ関数・同じ前半/後半の分け(`split_days`、
走らせの全 478 日の日付順の半分)・同じラベル(`cont_60`)・同じ帯の規則(L-277)で、材料に
`abs_m10_bp` = |直前 10 秒の値動き|、`abs_m60_bp` = |直前 60 秒の値動き|(bp。`anchors_prints.csv.gz` の
m10_signed・m60_signed の絶対値。ts − 1 ms 以前の約定だけで作った量)を足した 15 本で作り直す。
状態機械は回さない(約定を読まない)。判断の数・較正・当たりだけを出す。

読むもの: `data/c9_run_a/full_20230625_20241014/` の `anchors_prints.csv.gz`・`run_meta.json`。
書くもの: `--out`(既定 `run_a/three_way_m_out/`)だけ。ネットワークを使わない。Jev は呼ばない。

    PYTHONPATH=src python3 docs/RESEARCH/cards/c9_liquidation_cascade/run_a/three_way_m.py
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "src"))
from bot.research import liq_cascade_v2 as v2  # noqa: E402

RUN = REPO / "data" / "c9_run_a" / "full_20230625_20241014"
NEW = ("abs_m10_bp", "abs_m60_bp")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", default=str(RUN))
    ap.add_argument("--out", default=str(HERE / "three_way_m_out"))
    a = ap.parse_args(argv)
    run, out = Path(a.run), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    meta = json.loads((run / "run_meta.json").read_text(encoding="utf-8"))
    days = v2.day_range(date.fromisoformat(meta["期間"][0]), date.fromisoformat(meta["期間"][1]))
    make_days, meas_days = v2.split_days(days)
    cols = ["print_id", "day", v2.LOGIT_LABEL, "m10_signed", "m60_signed"] + list(v2.LOGIT_FEATURES)
    # L-920: 前の出力の材料 5 は名前に単位の無い bp。今の名前(_pct)が無ければ / 100 して読む
    P = v2.with_legacy_columns(pd.read_csv(run / "anchors_prints.csv.gz",
                                           usecols=v2.legacy_usecols(run / "anchors_prints.csv.gz", cols),
                                           dtype={"day": str, "print_id": str}))
    P["abs_m10_bp"], P["abs_m60_bp"] = P["m10_signed"].abs(), P["m60_signed"].abs()
    feats = list(v2.LOGIT_FEATURES) + list(NEW)
    model = v2.fit_three_way(P, make_days, features=feats)
    prob = v2.predict_three_way(model, P, features=feats)
    scene = v2.scene_of(P[v2.MAT_COL[1]])
    judge = [v2.judge_three_way(p, model[s]["band"], model[s]["cross"]) for p, s in zip(prob, scene)]
    per = np.where(P["day"].isin(set(make_days)), "作る", "測る")
    pd.DataFrame({"print_id": P["print_id"], "day": P["day"], "期間": per, "場面": scene, "続くの確率": prob,
                  "判断": judge, v2.LOGIT_LABEL: P[v2.LOGIT_LABEL]}).to_csv(
        out / "three_way_m_probs.csv.gz", index=False, float_format="%.8g")
    rows = []
    for s, m in model.items():
        for r in m["calib"]:
            rows.append({"場面": s} | r)
    pd.DataFrame(rows).to_csv(out / "three_way_m_calibration.csv", index=False, float_format="%.8g")
    jc = pd.Series(judge)
    summ = {"作る日": [make_days[0], make_days[-1]], "測る日": [meas_days[0], meas_days[-1]], "材料": feats,
            "ラベル": v2.LOGIT_LABEL, "場面": {}}
    for s, m in model.items():
        summ["場面"][s] = {"件数(作る)": m["n"], "基準率(作る)": m["base"], "分割数": m.get("n_folds"),
                          "わからないの帯": m["band"], "基準率を跨ぐ帯": m["cross"],
                          "係数": None if m["beta"] is None else dict(zip(["切片"] + feats, map(float, m["beta"])))}
    summ["判断の件数(プリント)"] = {f"{p_}_{j}": int(((per == p_) & (jc == j).to_numpy()).sum())
                               for p_ in ("作る", "測る") for j in ("止まる", "わからない", "続く")}
    summ["注"] = "状態機械は回していない。走らせの 3 択(材料 13 本)と同じ関数・分け・ラベル・帯の規則で、材料を 15 本にした。"
    (out / "three_way_m_model.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1, default=float))
    print(json.dumps(summ["判断の件数(プリント)"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
