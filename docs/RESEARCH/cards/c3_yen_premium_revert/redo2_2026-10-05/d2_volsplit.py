"""カード 3 の D2: 前の日の荒れ具合(vol_split_daily.classify、判断の時点で分かる)× 前半・後半。カード 1 の
redo2 の台本と同じ形。日ごとの損益は diag_tables.load_run・daily_series(カードの測定は日本時間の日、取引の行は
出の時刻の UTC の日。区分は日本時間の日で引くので、取引の行の走らせでは日の境が 9 時間ずれる【限界として書く】)。
区間は diag_tables.mean_ci(日の塊 5 日・1,000 回・種 20261004)。前半・後半は日数で 2 つ。
    PYTHONPATH=src python3 docs/RESEARCH/cards/c3_yen_premium_revert/redo2_2026-10-05/d2_volsplit.py
出力: このフォルダの D2_VOLSPLIT.md・d2_volsplit.json
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/home/user/trade"
sys.path.insert(0, os.path.join(REPO, "scripts/analysis"))
sys.path.insert(0, os.path.join(REPO, "scripts/w4_measure"))
sys.path.insert(0, os.path.join(REPO, "src"))
import diag_tables as dt  # noqa: E402
import vol_split_daily as vs  # noqa: E402

C2 = os.path.join(HERE, "..")
RUNS = {"measure_1h": os.path.join(C2, "measure/1h"), "measure_1d": os.path.join(C2, "measure/1d"),
        "measure_1w": os.path.join(C2, "measure/1w")}
NM = {"low": "低", "mid": "中", "high": "高"}


def main():
    cls = vs.classify(vs.daily_vol(vs.load_closes_by_day()))
    res, out = {}, ["# カード 3 の D2: 前の日の荒れ具合 × 前半・後半(bp/日、経費の前)", "",
                    "| 走らせ | 前の日の区分 | 全期間: 日数・1 日あたり [区間] | 前半 | 後半 |", "|---|---|---|---|---|"]
    for name, path in RUNS.items():
        daily = dt.daily_series(dt.load_run(path))
        days = sorted(daily)
        half = len(days) // 2
        parts = {"全期間": set(days), "前半": set(days[:half]), "後半": set(days[half:])}
        res[name] = {"half_edge": days[half], "rows": []}
        for c in ("low", "mid", "high"):
            cells = []
            for pn, part in parts.items():
                x = [daily[d] for d in days if d in part and cls.get(d) == c]
                r = dt.mean_ci(x) if len(x) >= 10 else {"n": len(x), "mean": None}
                res[name]["rows"].append({"class": c, "part": pn, "days": len(x), **r})
                cells.append(f"{len(x)}・{r['mean']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}]" if r.get("lo") is not None else f"{len(x)}・—")
            out.append(f"| {name} | {NM[c]} | {cells[0]} | {cells[1]} | {cells[2]} |")
        res[name]["no_class_days"] = sum(1 for d in days if d not in cls)
    json.dump(res, open(os.path.join(HERE, "d2_volsplit.json"), "w"), ensure_ascii=False, indent=1)
    open(os.path.join(HERE, "D2_VOLSPLIT.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))
    print({k: (v["half_edge"], v["no_class_days"]) for k, v in res.items()})


if __name__ == "__main__":
    main()
