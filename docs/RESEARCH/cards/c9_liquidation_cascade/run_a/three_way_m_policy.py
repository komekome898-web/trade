#!/usr/bin/env python3
"""カード 9 (a) の新しい 3 択(材料 15 本、`three_way_m.py`)で状態機械を回す(2026-10-03、関門 ② の 3 回目の監査「聞く 16」)。

走らせの段 3(`scripts/c9_run_a.py` の `stage3`)と同じ手順を、判断の確率だけ新しい模型に替えて流す:
- 清算を走らせと同じ範囲で読み(`load_prints`、期間 ± 4 日)、同じ側の前後(`same_side_context`)と束(g = 30・60・180)を作る。
- 前半の日だけで模型と帯を作り(`fit_three_way`、材料 = 走らせの 13 本 + |m10|・|m60|)、全プリントの確率を出す。
- 後半の日ごとに、その日に始まる束に `規則_3択` の判断を当て、遅れ 1・3 秒 × 型 A・B で `simulate_bundle` を流す。
`--features old` で走らせと同じ 13 本の模型にすると、走らせの `policy_cascades.csv.gz` の 規則_3択 の行を再現できるかを
確かめられる(`--days` で日数を絞る)。

読むもの: 約定・清算の生データ、`data/c9_run_a/full_20230625_20241014/` の `anchors_prints.csv.gz`・`run_meta.json`。
書くもの: `--out`(既定 `run_a/three_way_m_out/`)の `policy_*_3m*.csv.gz` と `policy_3m_meta*.json` だけ。ネットワークを使わない。

    PYTHONPATH=src python3 docs/RESEARCH/cards/c9_liquidation_cascade/run_a/three_way_m_policy.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(HERE))
from bot.research import liq_cascade_v2 as v2  # noqa: E402
import three_way_m as twm  # noqa: E402

POLICY_TYPES = ("A", "B")
PRINT_MARGIN_DAYS = 4


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", default=str(twm.RUN))
    ap.add_argument("--data-root", default=str(v2.DEFAULT_DATA_ROOT))
    ap.add_argument("--out", default=str(HERE / "three_way_m_out"))
    ap.add_argument("--features", choices=("new", "old"), default="new")
    ap.add_argument("--days", type=int, default=0, help="後半の最初の n 日だけ(0 = 全部)")
    a = ap.parse_args(argv)
    t_all = time.time()
    run, data_root, out = Path(a.run), Path(a.data_root), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    meta_run = json.loads((run / "run_meta.json").read_text(encoding="utf-8"))
    days = v2.day_range(date.fromisoformat(meta_run["期間"][0]), date.fromisoformat(meta_run["期間"][1]))
    make_days, meas_days = v2.split_days(days)
    pr = v2.load_prints(data_root, date.fromisoformat(days[0]) - timedelta(days=PRINT_MARGIN_DAYS),
                        date.fromisoformat(days[-1]) + timedelta(days=PRINT_MARGIN_DAYS))
    ctx = v2.same_side_context(pr)
    bund = {g: v2.same_side_bundles(pr, g) for g in v2.GAPS_S}
    cols = ["print_id", "day", v2.LOGIT_LABEL, "m10_signed", "m60_signed"] + list(v2.LOGIT_FEATURES)
    P = pd.read_csv(run / "anchors_prints.csv.gz", usecols=cols, dtype={"day": str, "print_id": str})
    P["abs_m10_bp"], P["abs_m60_bp"] = P["m10_signed"].abs(), P["m60_signed"].abs()
    feats = list(v2.LOGIT_FEATURES) + (list(twm.NEW) if a.features == "new" else [])
    model = v2.fit_three_way(P, make_days, features=feats)
    prob_rows = v2.predict_three_way(model, P, features=feats)
    idx_of = {pid: i for i, pid in enumerate(pr.print_id.tolist())}
    prob = np.full(len(pr), np.nan)
    for pid, pv in zip(P["print_id"], prob_rows):
        prob[idx_of[pid]] = pv
    check = None
    if a.features == "new":
        old = pd.read_csv(out / "three_way_m_probs.csv.gz", dtype={"print_id": str})
        mm = old.merge(pd.DataFrame({"print_id": P["print_id"], "p": prob_rows}), on="print_id")
        check = float(np.nanmax(np.abs(mm["続くの確率"] - mm["p"])))

    store = v2.TradeStore(data_root)
    crows, lrows = [], []
    act, jud = Counter(), Counter()
    use_days = meas_days[: a.days] if a.days else meas_days
    label = v2.POLICY_3WAY + ("_新15本" if a.features == "new" else "_旧13本の再現")
    for day in use_days:
        tr, _miss = store.window([day, (date.fromisoformat(day) + timedelta(days=1)).isoformat()])
        price_fn = v2.make_price_fn(tr)
        for g in v2.GAPS_S:
            for b in bund[g]["bundles"]:
                if v2.day_of_ms(b["start_ms"]) != day:
                    continue
                jd = v2.judgments_for(v2.POLICY_3WAY, b["members"], ctx, prob, model)
                for dly in v2.DELAYS_S:
                    for typ in POLICY_TYPES:
                        res = v2.simulate_bundle(pr, b, jd, typ, dly, price_fn)
                        for p in res["path"]:
                            act[f"{g}|{dly}|{label}|{typ}|{p['行動']}"] += 1
                            jud[f"{g}|{dly}|{label}|{typ}|{p['判断']}"] += 1
                        crows.append({"bundle_id": b["bundle_id"], "day": day, "period": "測る", "side": b["side"],
                                      "gap_s": g, "delay_s": dly, "policy": label, "type": typ,
                                      "n_prints": b["n_prints"], "qty_total": b["qty_total"], "pnl_bp": res["pnl_bp"],
                                      "entered": int(bool(res["entered"])), "n_entries": res["n_entries"],
                                      "hold_s": res["hold_seconds"], "missing": int(bool(res["missing"])),
                                      "first_entry_pos": res.get("first_entry_pos")})
                        for lg in res["legs"]:
                            lrows.append({"bundle_id": b["bundle_id"], "day": day, "period": "測る", "gap_s": g,
                                          "delay_s": dly, "policy": label, "type": typ, "leg_pos": lg["位置"],
                                          "leg_dir": lg["向き"], "exit_reason": lg["出口の理由"],
                                          "pnl_bp": lg["レグ損益_bp"], "hold_s": lg["保有秒"]})
        store.drop_before(day)
        print(f"[3m] {day} 束の行 {len(crows)} 経過 {time.time() - t_all:.0f}s", flush=True)
    sfx = "" if a.features == "new" else "_oldcheck"
    pd.DataFrame(crows).to_csv(out / f"policy_cascades_3m{sfx}.csv.gz", index=False, float_format="%.8g")
    pd.DataFrame(lrows).to_csv(out / f"policy_legs_3m{sfx}.csv.gz", index=False, float_format="%.8g")
    meta = {"材料": feats, "後半の日": [use_days[0], use_days[-1]], "日数": len(use_days),
            "確率の一致(three_way_m_probs との最大の差)": check,
            "行動の数": dict(act), "判断の数": dict(jud), "所要_秒": round(time.time() - t_all, 1),
            "注": "走らせの段 3 と同じ手順。判断の確率だけ新しい模型。Jev は呼んでいない。"}
    (out / f"policy_3m_meta{sfx}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(json.dumps({k: meta[k] for k in ("日数", "確率の一致(three_way_m_probs との最大の差)", "所要_秒")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
