#!/usr/bin/env python3
"""カードどうしの日ごとの損益の重なりの表(L-608 の一覧の 9。段 4 の組み合わせへの橋)。

読み方の決まり(表を見る前に、この台本と `tests/research/test_overlap_daily.py` で固めた):

R1 系列: 下の SERIES に固定する。ダッシュボードの書き出し(`backtest_runs_shared/cards/<カード>/<変種>/daily.csv`、
   日 = 日本時間の 1 日)と、指値の再現の取引の記録(trades.json.gz の出の時刻を日本時間の日に直して和を取る)。
   出の時刻は足の終わりの時刻なので、出の時刻の 1 ナノ秒前の日に入れる(日本時間 0 時ちょうどに閉じた取引は前の日。
   期間の終わり 2023-12-17T15:00Z に閉じた取引を 12-17 に入れる。関門 ② の 1 回目の止める 1 で直した)。
   取引の記録から作る系列は、その走らせの期間の日のうち取引が無い日を 0 にする。
R2 共通の日: 2 本の系列の両方の期間に入る日だけで比べる。2023-12-17 より後の日は使わない(封印の境の前)。
R3 量は 3 つ。どれにも良い悪いの境は置かない(A-12。表の数で読む):
   (a) 日ごとの損益の相関(ピアソン)
   (b) 両方の損益が 0 でない日のうち、符号が同じ日の割合
   (c) 悪い日の重なり: 行の系列の損益の下から 5% の日のうち、列の系列でも下から 5% に入る日の割合
R4 経費は入れない。どれも探索の読みで、判定ではない。
R5 損益の率は %(L-920 で bp は値動き率だけの名前)。L-920 より前の書き出し(daily.csv の pnl_bp・trades.json.gz の pnl_bp、
   率 × 1 万)は / 100 して % で読む。相関・符号・重なりの割合は単位に依らない。

出力: docs/RESEARCH/cards/OVERLAP/TABLES.md と overlap.json。

    python3 scripts/w4_measure/overlap_daily.py
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
JST = timezone(timedelta(hours=9))
LAST_DAY = "2023-12-17"
SHARED = os.path.join(REPO, "backtest_runs_shared", "cards")
C4 = os.path.join(REPO, "docs", "RESEARCH", "cards", "c4_owner_matilda_range", "limit_sim", "families_r2")
C2 = os.path.join(REPO, "docs", "RESEARCH", "cards", "c2_owner_xvenue_wick", "limit_sim", "runs")

# (表の名前, 種類, パス)。種類 = "daily"(daily.csv)/ "trades"(trades.json.gz、隣の summary.json の期間)
SERIES = (
    ("今の paper bot", "daily", os.path.join(SHARED, "c1_xborder_mom", "default")),
    ("カツオ原典 1分", "daily", os.path.join(SHARED, "c2_owner_xvenue_wick", "a_1m")),
    ("カツオ原典 5分", "daily", os.path.join(SHARED, "c2_owner_xvenue_wick", "a_5m")),
    ("カツオ K1 参照 5分", "trades", os.path.join(C2, "weak_f5_close_a")),
    ("カツオ K1 指値a 5分", "trades", os.path.join(C2, "weak_f5_limit_a_good")),
    ("カツオ 強い1分 半値", "trades", os.path.join(C2, "strong_f1_limit_b_good")),
    ("円の上乗せ 1h", "daily", os.path.join(SHARED, "c3_yen_premium_revert", "1h")),
    ("マチルダ v37", "trades", os.path.join(C4, "v37_good")),
    ("マチルダ 中心5:1", "trades", os.path.join(C4, "A1_center_5_1_good")),
    # 悪い側(関門 ② の 1 回目の直す 7 で足した。良い側だけの表の射程を確かめるため)
    ("マチルダ v37 悪", "trades", os.path.join(C4, "v37_bad")),
    ("マチルダ 中心5:1 悪", "trades", os.path.join(C4, "A1_center_5_1_bad")),
    ("カツオ K1 指値a 5分 悪", "trades", os.path.join(C2, "weak_f5_limit_a_bad")),
    ("東京仲値", "daily", os.path.join(SHARED, "c5_tokyo_fix_momentum", "default")),
    ("週末ギャップ USDJPY", "daily", os.path.join(SHARED, "c6_weekend_gap_revert", "usdjpy")),
    ("バリアレース 1h", "daily", os.path.join(SHARED, "c7_barrier_race", "1h")),
    ("平均回帰 日本時間", "daily", os.path.join(SHARED, "c8_session_mean_revert", "jst_day")),
)


def _jst_day(ns: int) -> str:
    return datetime.fromtimestamp(ns // 10**9, tz=JST).strftime("%Y-%m-%d")  # 整数で秒に(浮動小数の丸めで 1ns 前が戻らないように)


def days_between(start_iso: str, end_iso: str) -> list[str]:
    """期間 [start, end)(UTC の ISO)に入る日本時間の日の一覧。"""
    s = datetime.fromisoformat(start_iso.replace("Z", "+00:00")).astimezone(JST).date()
    e = (datetime.fromisoformat(end_iso.replace("Z", "+00:00")) - timedelta(seconds=1)).astimezone(JST).date()
    out, d = [], s
    while d <= e:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def load_daily_csv(path: str) -> dict[str, float]:
    with open(path, encoding="utf-8") as fh:
        return {r["day"]: (float(r["pnl_pct"]) if r.get("pnl_pct") not in (None, "") else float(r["pnl_bp"]) / 100)
                for r in csv.DictReader(fh) if r["day"] <= LAST_DAY}


def daily_from_trades(trades: dict, period: tuple[str, str]) -> dict[str, float]:
    assert trades["t_unit"] == "ns"
    out = {d: 0.0 for d in days_between(*period) if d <= LAST_DAY}
    pct = trades["pnl_pct"] if "pnl_pct" in trades else [float(v) / 100 for v in trades["pnl_bp"]]
    for t, p in zip(trades["exit_t_ns"], pct):
        d = _jst_day(int(t) - 1)
        if d in out:
            out[d] += float(p)
    return out


def load_series(kind: str, d: str) -> dict[str, float]:
    if kind == "daily":
        return load_daily_csv(os.path.join(d, "daily.csv"))
    with open(os.path.join(d, "summary.json"), encoding="utf-8") as fh:
        period = tuple(json.load(fh)["period"])
    with gzip.open(os.path.join(d, "trades.json.gz"), "rt", encoding="utf-8") as fh:
        return daily_from_trades(json.load(fh), period)


def pair_stats(a: dict[str, float], b: dict[str, float]) -> dict:
    common = sorted(set(a) & set(b))
    x = np.array([a[k] for k in common])
    y = np.array([b[k] for k in common])
    out = {"days": len(common)}
    out["corr"] = float(np.corrcoef(x, y)[0, 1]) if len(common) > 2 and x.std() > 0 and y.std() > 0 else None
    nz = (x != 0) & (y != 0)
    out["same_sign"] = float((np.sign(x[nz]) == np.sign(y[nz])).mean()) if nz.any() else None
    out["both_nonzero_days"] = int(nz.sum())
    if len(common) >= 20:
        k = max(1, int(round(0.05 * len(common))))
        wa = set(np.argsort(x, kind="stable")[:k].tolist())
        wb = set(np.argsort(y, kind="stable")[:k].tolist())
        out["worst5_overlap"] = len(wa & wb) / k
        # 関門 ② の 2 回目の直す 1 で足した: 良い日の重なりと、損益の絶対値が大きい日の重なり
        ba = set(np.argsort(-x, kind="stable")[:k].tolist())
        bb = set(np.argsort(-y, kind="stable")[:k].tolist())
        out["best5_overlap"] = len(ba & bb) / k
        aa = set(np.argsort(-np.abs(x), kind="stable")[:k].tolist())
        ab = set(np.argsort(-np.abs(y), kind="stable")[:k].tolist())
        out["absbig5_overlap"] = len(aa & ab) / k
        out["worst_vs_best5"] = len(wa & bb) / k  # 行の悪い日が列の良い日
    else:
        out["worst5_overlap"] = out["best5_overlap"] = out["absbig5_overlap"] = out["worst_vs_best5"] = None
    return out


def mean_ci(x: np.ndarray, reps: int = 1000, block: int = 5, seed: int = 20261003) -> tuple[float, float, float]:
    """1 日あたりの平均と、5 日の塊の再抽出の 95% 区間(関門 ② の 1 回目の直す 5 で足した)。"""
    n = len(x)
    rng = np.random.default_rng(seed)
    starts = np.arange(0, max(1, n - block + 1))
    nb = max(1, n // block)
    ms = [x[np.concatenate([np.arange(s0, min(s0 + block, n)) for s0 in rng.choice(starts, size=nb)])].mean()
          for _ in range(reps)]
    lo, hi = np.percentile(ms, [2.5, 97.5])
    return float(x.mean()), float(lo), float(hi)


def _f(v, nd=2):
    return "—" if v is None else f"{v:.{nd}f}"


def main() -> int:
    series = {name: load_series(kind, d) for name, kind, d in SERIES}
    names = [n for n, _, _ in SERIES]
    stats = {a: {b: pair_stats(series[a], series[b]) for b in names if b != a} for a in names}
    L = ["# カードどうしの日ごとの損益の重なり", "",
         "`scripts/w4_measure/overlap_daily.py` が出した。読み方の決まり R1〜R4 はその台本の docstring。経費の前。", "",
         "## 系列", "", "| 名前 | 日数 | 最初の日 | 最後の日 | 1 日あたり(%) | 95% 区間(5 日の塊) | 損益が 0 の日の割合 |",
         "|---|---|---|---|---|---|---|"]
    for n in names:
        s = series[n]
        ks = sorted(s)
        x = np.array([s[k] for k in ks])
        m, lo, hi = mean_ci(x)
        L.append(f"| {n} | {len(ks)} | {ks[0]} | {ks[-1]} | {m:.4f} | [{lo:.4f}, {hi:.4f}] | {(x == 0).mean():.3f} |")
    for key, title, nd in (("corr", "表 1: 日ごとの損益の相関", 2), ("same_sign", "表 2: 両方が 0 でない日のうち符号が同じ日の割合", 2),
                           ("worst5_overlap", "表 3: 行の悪い 5% の日のうち、列でも悪い 5% に入る割合", 2)):
        L += ["", f"## {title}", "", "| 行 \\ 列 | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
        for a in names:
            L.append(f"| {a} | " + " | ".join("" if a == b else _f(stats[a][b][key], nd) for b in names) + " |")
    L += ["", "## 表 4: 共通の日の数", "", "| 行 \\ 列 | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for a in names:
        L.append(f"| {a} | " + " | ".join("" if a == b else str(stats[a][b]["days"]) for b in names) + " |")
    # 表 5: 悪い日の重なりの分布(関門 ② の 1 回目の直す 3 で足した)。組ごとに 2 方向の大きい方。同じカードの変種どうしも入る
    pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]]
    mx = [max(stats[a][b]["worst5_overlap"] or 0, stats[b][a]["worst5_overlap"] or 0) for a, b in pairs]
    L += ["", "## 表 5: 悪い日の重なりの分布(組ごとに 2 方向の大きい方。無関係なら 0.05 前後)", "",
          f"- 組の数 {len(pairs)}(同じカードの変種どうしを含む)",
          f"- 0.10 以上 {sum(v >= 0.10 for v in mx)}・0.15 以上 {sum(v >= 0.15 for v in mx)}・0.20 より大 {sum(v > 0.20 for v in mx)}"]
    # 表 6(関門 ② の 2 回目の直す 1 で足した): 悪い日・良い日・絶対値の大きい日・悪い日 × 良い日 の重なりの平均
    sparse = {"カツオ 強い1分 半値", "週末ギャップ USDJPY"}
    dense = [n for n in names if n not in sparse and not n.endswith(" 悪")]
    dp = [(a, b) for i, a in enumerate(dense) for b in dense[i + 1:]]
    def avg(key):
        v = [(stats[a][b][key] + stats[b][a][key]) / 2 for a, b in dp if stats[a][b][key] is not None]
        return sum(v) / len(v)
    L += ["", "## 表 6: 上位・下位 5% の日の重なりの平均(取引の疎い 2 本と悪い側を除く系列の組。無関係なら 0.05 前後)", "",
          f"- 系列 {len(dense)}・組 {len(dp)}(同じカードの変種どうしを含む)",
          f"- 悪い日どうし {avg('worst5_overlap'):.3f}・良い日どうし {avg('best5_overlap'):.3f}・"
          f"損益の絶対値が大きい日どうし {avg('absbig5_overlap'):.3f}・片方の悪い日が他方の良い日 {avg('worst_vs_best5'):.3f}"]
    out = os.path.join(REPO, "docs", "RESEARCH", "cards", "OVERLAP")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    with open(os.path.join(out, "overlap.json"), "w", encoding="utf-8") as fh:
        json.dump({"series": {n: {"days": len(series[n])} for n in names}, "pairs": stats}, fh, ensure_ascii=False, indent=1)
    print(f"series {len(names)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
