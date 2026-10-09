"""カード 4 の D2: 前の日の荒れ具合(vol_split_daily.classify、判断の時点で分かる)× 前半・後半。カード 1 の
redo2 の台本と同じ形。取引は trade_rows.load_rows で読み、日ごとの損益は出の時刻の日本時間の日に集める
(区分も日本時間の日なので境がそろう。overlap_daily.py の _jst_day・days_between と同じ決まり: 出の時刻 − 1ns の日本時間の日)。
2026-10-05 にアドバイザーの指摘(止める 2)で、出の時刻の UTC の日(9 時間ずれ)から直した。
区間は diag_tables.mean_ci(日の塊 5 日・1,000 回・種 20261004)。前半・後半は日数で 2 つ。
L-920 の後: 損益は %(指値の再現の損益は段ごとの損益率 ÷ 段数の和。bp は値動き率だけの名前)。取引の行は
trade_rows.load_rows で読む(列 pnl_pct。L-920 より前の行の pnl_bp = 率 × 1 万は / 100 して % で読む)。
L-920 の後の diag_tables.load_run は円の列 pnl_jpy の無い置き場で止めるので使わない。期間は summary.json の period。
このフォルダの D2_VOLSPLIT.md・d2_volsplit.json のうち L-920 より前に書いたものは bp/日(= ここの %/日 × 100)。
    PYTHONPATH=src python3 docs/RESEARCH/cards/c4_owner_matilda_range/redo2_2026-10-05/d2_volsplit.py
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
import overlap_daily as od  # noqa: E402
import trade_rows as trw  # noqa: E402
import vol_split_daily as vs  # noqa: E402

C2 = os.path.join(HERE, "..")
R2 = os.path.join(C2, "limit_sim/families_r2")
RUNS = {n: os.path.join(R2, n) for n in ("v37_good", "v37_bad", "A1_center_4_3_good", "A1_center_4_3_bad")}
NM = {"low": "低", "mid": "中", "high": "高"}


def main():
    cls = vs.classify(vs.daily_vol(vs.load_closes_by_day()))
    res, out = {}, ["# カード 4 の D2: 前の日の荒れ具合 × 前半・後半(%/日、経費の前、日本時間の日)", "",
                    "| 走らせ | 前の日の区分 | 全期間: 日数・1 日あたり [区間] | 前半 | 後半 |", "|---|---|---|---|---|"]
    for name, path in RUNS.items():
        rows = trw.load_rows(trw.check_dir(path))  # pnl = pnl_pct(%)、前の行は pnl_bp / 100
        with open(os.path.join(path, "summary.json"), encoding="utf-8") as fh:
            period = json.load(fh)["period"]
        daily = {d: 0.0 for d in od.days_between(*period)}
        for x_ns, p in zip(rows["exit"].tolist(), rows["pnl"].tolist()):
            d = od._jst_day(int(x_ns) - 1)
            if d in daily:
                daily[d] += p
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
                cells.append(f"{len(x)}・{r['mean']:+.4f} [{r['lo']:+.4f}, {r['hi']:+.4f}]" if r.get("lo") is not None else f"{len(x)}・—")
            out.append(f"| {name} | {NM[c]} | {cells[0]} | {cells[1]} | {cells[2]} |")
        res[name]["no_class_days"] = sum(1 for d in days if d not in cls)
    json.dump(res, open(os.path.join(HERE, "d2_volsplit.json"), "w"), ensure_ascii=False, indent=1)
    open(os.path.join(HERE, "D2_VOLSPLIT.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))
    print({k: (v["half_edge"], v["no_class_days"]) for k, v in res.items()})


if __name__ == "__main__":
    main()
