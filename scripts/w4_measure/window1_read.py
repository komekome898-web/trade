#!/usr/bin/env python3
"""探索の窓 1(P2-08 の 2023-12-18〜2025-12-12)で、改良したカツオとマチルダを読む(段取り 6、L-630「ア」)。

事前登録 = `docs/RESEARCH/WINDOW1/PREREG.md`(9ec4fb46)。読み方の決まり W1〜W10 はそこの §3 が正本で、ここには要点だけを
写す(変えない・足さない)。この台本と `tests/research/test_window1_read.py` は、窓の走らせの結果を見る前にコミットする。

W1 主の量: 各形 − 基準の 1 日あたりの損益の差(同じ日どうし)、95% 区間(日の塊 5 日・1,000 回・種 20261004)、MDE(5% 両側・80%)。
   カツオは K-A・K-B − K-0、マチルダは M-A − M-0(同じ側どうし)。
W1b K-B − K-A(区間・MDE)。
W2 日の門の差: K-A+D − K-A、K-B+D − K-B(区間・MDE)。日の門は、建ての日の区分が「低」(K-B+D は「低」と「中」)の取引を外す近似。
W3 元のデータの差 d0 と並べる(D0 の表。走らせる前に固定。--check-d0 で元の走らせから計算し直して一致を確かめる)。
W4 水準: 各形の 1 日あたりの損益・取引/日・1 取引あたり。
W5 商品の前後: W1・W2 を FX の期間(〜2024-03-27)と CFD の期間(2024-03-28〜)に分けて並べる。
W6 マチルダは良い側・悪い側を別々に出し、同じ側どうしでだけ比べる。W6b(窓の 10 日の順序の確かめ)は別の台本。
W7 年ごとの W1、窓の日のボラの分布(三分位の境の値)と元のデータの日のボラの分布を並べる。
W8 選んだ数を書く(カツオは N の 7 通り × 2 から 2 つ、日の門の決まり 1 つ。マチルダは過去だけの門 1 つ)。採用は決めない。
W9 言葉: label(下端, 上端, d0)。最初に当たった 1 つだけ(PREREG §3 W9 の順)。
W10 意図の地図の制限を結果の文書に毎回書く(render の末尾に固定の文で出す)。

台本の決め(事前登録が決めていない所。走らせの結果を見る前に決めた。2026-10-04):
 a. 取引は trades.json.gz(窓の走らせでは --measure-from = 2023-12-18T00:00Z より前に出た取引は入っていない)。
    元の走らせの d0 の計算し直しも同じ読み方。
 b. 日 = 出の時刻から 1 ns 引いた時刻の UTC の暦日(足の終わりの時刻 = 次の日の 0 時ちょうどに出た取引を、その足の日に入れる。
    期間の終わりで閉じた取引が 2025-12-12T00:00:00Z になっても落とさないため)。改良の周 2 の R10・R6 は出の時刻の日そのもので、
    1 日あたりの平均は全部の日の和 ÷ 日数なので、範囲の中で日が 1 つずれても変わらない(--check-d0 で確かめる)。
 c. 窓の日 = UTC の 2023-12-18〜2025-12-11(両端を含む。取引の無い日は 0)。
 d. 日の区分は建ての時刻の日本時間の日(vol_split_daily.classify の日。前の日のボラを前の暦年の三分位で切る)。区分の無い日
    (窓では日本時間の 2025-12-12 の 0〜9 時に建った取引など)は門の外 = 外さない。外した取引の数と全体の数を出す。
 e. W5 の前後は UTC の日で切る(2024-03-27 までが FX、2024-03-28 からが CFD)。
 f. W7 の年は UTC の日の暦年(2023 年は 12-18〜12-31 の 14 日)。区間は W1 と同じ計算(塊 5 日)。
 g. W9 の言葉は窓の全期間の行にだけ当てる(d0 は全期間の値しか無い)。W5・W7 の行は区間と MDE だけを出す。
 h. W7 の境は classify と同じ式(前の暦年の日の 1/3・2/3 分位、300 日以上の年だけ)を edges() で出す(classify は変えない)。

    W4_WINDOW1=P2-08-explore PYTHONPATH=src python3 scripts/w4_measure/window1_read.py      # 窓の読み(窓の口を通る)
    PYTHONPATH=src python3 scripts/w4_measure/window1_read.py --check-d0                       # 元のデータで d0 を計算し直す(窓は読まない)

出力: docs/RESEARCH/WINDOW1/READ/{TABLES.md,read.json}(--check-d0 は D0_CHECK.md)。数字は手で書かない。
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import gzip
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.path.dirname(os.path.dirname(HERE))
JST = timezone(timedelta(hours=9))
SEED, N_RES, BLOCK = 20261004, 1000, 5

RUNS_ROOT = os.path.join(REPO, "docs", "RESEARCH", "WINDOW1", "runs")
OUT = os.path.join(REPO, "docs", "RESEARCH", "WINDOW1", "READ")
WIN_LO, WIN_HI = date(2023, 12, 18), date(2025, 12, 11)
CFD_FROM = date(2024, 3, 28)

# 窓の走らせの置き場の名前(PREREG §2。日の門は取引の後で当てるので走らせは K 3 本・M 4 本)
K_RUNS = ("K-0", "K-A", "K-B")
SIDES = ("good", "bad")
M_RUNS = tuple(f"{f}_{s}" for f in ("M-0", "M-A") for s in SIDES)
GATE_AVOID = {"K-A+D": ("K-A", ("low",)), "K-B+D": ("K-B", ("low", "mid"))}

# W3 の d0(bp/日。PREREG §3 の表。走らせる前に固定。変えない)
D0 = {
    "K-A − K-0": 12.00,
    "K-B − K-0": 1.13,
    "K-B − K-A": -10.87,
    "K-A+D − K-A": -2.56,
    "K-B+D − K-B": -1.00,
    "M-A − M-0 良": 164.13,
    "M-A − M-0 悪": 205.76,
}
# 各差の (形, 基準)
PAIRS = {
    "K-A − K-0": ("K-A", "K-0"),
    "K-B − K-0": ("K-B", "K-0"),
    "K-B − K-A": ("K-B", "K-A"),
    "K-A+D − K-A": ("K-A+D", "K-A"),
    "K-B+D − K-B": ("K-B+D", "K-B"),
    "M-A − M-0 良": ("M-A_good", "M-0_good"),
    "M-A − M-0 悪": ("M-A_bad", "M-0_bad"),
}
W5_PAIRS = ("K-A − K-0", "K-B − K-0", "K-B − K-A", "K-A+D − K-A", "K-B+D − K-B", "M-A − M-0 良", "M-A − M-0 悪")

# 元の走らせ(--check-d0)
C2R = os.path.join(REPO, "docs", "RESEARCH", "cards", "c2_owner_xvenue_wick", "limit_sim", "runs")
C4R = os.path.join(REPO, "docs", "RESEARCH", "cards", "c4_owner_matilda_range", "limit_sim", "families_r2")
ORIG = {
    "K-0": os.path.join(C2R, "weak_f15_close_a"),
    "K-A": os.path.join(C2R, "weak_f15_close_a_time6"),
    "K-B": os.path.join(C2R, "weak_f15_rgate_close_a_time9"),
    "M-0_good": os.path.join(C4R, "v37_good"),
    "M-0_bad": os.path.join(C4R, "v37_bad"),
    "M-A_good": os.path.join(C4R, "R2_ratio_gate_rolling_center_4_3_good"),
    "M-A_bad": os.path.join(C4R, "R2_ratio_gate_rolling_center_4_3_bad"),
}


# ---------------------------------------------------------------- 読み

def read_trades(d: str) -> list[tuple[int, int, float]] | None:
    """(entry_ns, exit_ns, pnl_bp)。trades.json.gz。無ければ None。"""
    p = os.path.join(d, "trades.json.gz")
    if not os.path.isfile(p):
        return None
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        o = json.load(fh)
    scale = {"ns": 1, "s": 10**9}[o["t_unit"]]
    return [(int(e) * scale, int(x) * scale, float(v)) for e, x, v in zip(o["entry_t_ns"], o["exit_t_ns"], o["pnl_bp"])]


def utc_day(ns: int) -> date:
    """決め b: 出の時刻から 1 ns 引いた時刻の UTC の暦日。"""
    return datetime.fromtimestamp((ns - 1) // 10**9, tz=timezone.utc).date()


def jst_day(ns: int) -> str:
    """決め d: 建ての時刻の日本時間の日(classify の鍵)。"""
    return datetime.fromtimestamp(ns // 10**9, tz=JST).date().isoformat()


def daily(trades: list, lo: date, hi: date) -> list[float]:
    """lo〜hi(両端を含む)の全部の UTC の日の損益の和。取引の無い日は 0。範囲の外の日の取引は数えない。"""
    n = (hi - lo).days + 1
    out = [0.0] * n
    for _, x, p in trades:
        k = (utc_day(x) - lo).days
        if 0 <= k < n:
            out[k] += p
    return out


def trades_in(trades: list, lo: date, hi: date) -> list:
    return [t for t in trades if lo <= utc_day(t[1]) <= hi]


def gate_drop(trades: list, cls: dict[str, str], avoid: tuple[str, ...]) -> tuple[list, int]:
    """決め d: 建ての日本時間の日の区分が avoid に入る取引を外す。区分の無い日は外さない。(残り, 外した数)。"""
    keep = [t for t in trades if cls.get(jst_day(t[0])) not in avoid]
    return keep, len(trades) - len(keep)


def paired_ci(x: list[float], b: list[float]) -> dict:
    """W1。日ごとの差の平均・区間(循環の塊 5 日・1,000 回・種 20261004)・MDE(5% 両側・80%)。"""
    from bot.bt.validation import block_bootstrap_ci, mde
    d = [float(p - q) for p, q in zip(x, b)]
    ci = block_bootstrap_ci(d, block_len=BLOCK, n_resamples=N_RES, seed=SEED, alpha=0.05, method="circular",
                            statistic="mean")
    n = len(d)
    sd = ci.se * n ** 0.5  # 差が全部の日で同じ(例: 日の門が 1 本も外さない)なら 0 で、MDE は出せない(None)
    return {"mean": ci.estimate, "lo": ci.lo, "hi": ci.hi, "days": n,
            "mde": mde(n=n, sd=sd, alpha=0.05, power=0.80, sides=2, approx="normal") if sd > 0 else None}


# ---------------------------------------------------------------- W9

def label(lo: float, hi: float, d0: float) -> str:
    """W9。最初に当たった 1 つだけ。d0 < 0 は符号を反転して d0 > 0 の決まりを当てる。"""
    if d0 == 0:
        return "正" if lo > 0 else ("負" if hi < 0 else "不明")
    if d0 < 0:
        lo, hi, d0 = -hi, -lo, -d0
    if hi <= 0:
        return "逆向き"
    if lo > 0:
        return "引き継がれた側" + ("(元の大きさより小さい)" if hi < d0 else "")
    if hi < d0:
        return "元の大きさは否定"
    return "不明"


# ---------------------------------------------------------------- W7

def edges(vol: dict[str, float]) -> dict[int, tuple[float, float]]:
    """決め h: 年 y の境 = 前の暦年 y−1 の日の量の 1/3・2/3 分位(300 日以上の年だけ)。classify と同じ式。"""
    by_year: dict[int, list[float]] = {}
    for d, v in vol.items():
        by_year.setdefault(int(d[:4]), []).append(v)
    return {y + 1: (float(np.quantile(vs, 1 / 3)), float(np.quantile(vs, 2 / 3))) for y, vs in by_year.items()
            if len(vs) >= 300}


def vol_table(vol: dict[str, float], cls: dict[str, str], last_day: str) -> list[dict]:
    """W7。年ごとに、その年に使った境・その年の日の量の中央値・区分ごとの日数(last_day まで)。"""
    e = edges(vol)
    rows = []
    for y in sorted({int(d[:4]) for d in cls}):
        days = [d for d in vol if int(d[:4]) == y and d <= last_day]
        c = [cls[d] for d in cls if int(d[:4]) == y]
        rows.append({"year": y, "edges": e.get(y), "median_vol": float(np.median([vol[d] for d in days])) if days else None,
                     "days": {k: c.count(k) for k in ("low", "mid", "high")}})
    return rows


# ---------------------------------------------------------------- 組み立て

def series(trades: dict, cls: dict[str, str]) -> tuple[dict, dict]:
    """K 3 本・M 4 本の取引に、日の門の 2 形を足す。(取引, 外した数 {形: (外した, 全体)})。"""
    out = dict(trades)
    dropped = {}
    for name, (src, avoid) in GATE_AVOID.items():
        if trades.get(src) is None:
            out[name] = None
            continue
        out[name], n = gate_drop(trades[src], cls, avoid)
        dropped[name] = (n, len(trades[src]))
    return out, dropped


def diffs(tr: dict, lo: date, hi: date, with_label: bool) -> dict:
    out = {}
    for k, (x, b) in PAIRS.items():
        if tr.get(x) is None or tr.get(b) is None:
            out[k] = None
            continue
        r = paired_ci(daily(tr[x], lo, hi), daily(tr[b], lo, hi))
        r["d0"] = D0[k]
        if with_label:
            r["label"] = label(r["lo"], r["hi"], D0[k])
        out[k] = r
    return out


def levels(tr: dict, lo: date, hi: date) -> dict:
    n_days = (hi - lo).days + 1
    out = {}
    for k, t in tr.items():
        if t is None:
            out[k] = None
            continue
        t = trades_in(t, lo, hi)
        s = sum(p for _, _, p in t)
        out[k] = {"pnl_per_day": s / n_days, "trades_per_day": len(t) / n_days,
                  "per_trade": s / len(t) if t else None, "trades": len(t), "days": n_days}
    return out


def build(trades: dict, cls: dict[str, str], vol: dict[str, float] | None, last_day: str = "2025-12-11") -> dict:
    tr, dropped = series(trades, cls)
    r = {"window": [WIN_LO.isoformat(), WIN_HI.isoformat()], "dropped": dropped,
         "W1": diffs(tr, WIN_LO, WIN_HI, True), "W4": levels(tr, WIN_LO, WIN_HI),
         "W5": {"FX": diffs(tr, WIN_LO, CFD_FROM - timedelta(days=1), False),
                "CFD": diffs(tr, CFD_FROM, WIN_HI, False)},
         "W7": {"years": {}}, "missing": sorted(k for k, v in trades.items() if v is None)}
    for y in (2023, 2024, 2025):
        lo, hi = max(WIN_LO, date(y, 1, 1)), min(WIN_HI, date(y, 12, 31))
        r["W7"]["years"][y] = diffs(tr, lo, hi, False)
    if vol is not None:
        r["W7"]["vol"] = vol_table(vol, cls, last_day)
    return r


# ---------------------------------------------------------------- 書き出し

def _f(x, nd=2) -> str:
    return "—" if x is None else f"{x:+.{nd}f}"


def _ci(r: dict | None) -> str:
    return "—" if not r else f"{_f(r['mean'])} [{_f(r['lo'])}, {_f(r['hi'])}]"


W8_TEXT = ("カツオ: 時間で降りる N の 7 通り(6〜12)× 2(時間だけ・直前 365 日の門と組んだ形)= 14 から 2 つ(K-A = 時間だけ N = 6、"
           "K-B = 組んだ形 N = 9)。日の門の決まり 1 つ(L-629)。マチルダ: 過去だけの比の門 1 つ(× 利確 4:3)。"
           "選んだのは元のデータ(〜2023-12-17)で、d0 は選んだ分だけ大きく出ている。窓は探索で、ここで採用は決めない。")
W10_TEXT = ("カツオ: `c2_owner_xvenue_wick/INTENT_MAP.md` の △(I-11a Binance 現物は高レバの取引所でない、I-5u ほか)・"
            "✕(I-10・I-12・I-20)が残る。「弱いだけ」は I-2・I-3(強い合図のドテン、○)を外した形。陰性・逆向きは「この代理・"
            "この形では」までしか言わない。マチルダ: `c4_owner_matilda_range/INTENT_MAP.md` §11 の指値の再現(families_r2)に対応し、"
            "I-8・I-9・I-19 △、I-13 の flat ✕、B5 未実装、L-581 の限界(1 分の中の往復を数えず小勝ちを少なく数える【推定】、"
            "板の位置は再現できない)。経費なし。参照の形(カツオ)は足の終値で遅れなく全量が約定する仮定。")


def render(r: dict) -> str:
    L = ["# 探索の窓 1 の読みの表", "",
         "`scripts/w4_measure/window1_read.py` が出した(手で書いていない)。読み方の決まり W1〜W10 は `PREREG.md` §3、"
         "台本の決め a〜h は台本の docstring。bp/日。経費なし。窓は "
         f"UTC の {r['window'][0]}〜{r['window'][1]}。", ""]
    if r["missing"]:
        L += [f"**足りない走らせ: {', '.join(r['missing'])}**", ""]
    L += ["## W1・W1b・W2・W3・W9(窓の全期間)", "",
          "| 差 | 窓 平均 [区間] | MDE | 日数 | 元のデータの d0 | W9 の言葉 |", "|---|---|---|---|---|---|"]
    for k, v in r["W1"].items():
        L.append(f"| {k} | {_ci(v)} | {_f(v['mde']) if v else '—'} | {v['days'] if v else '—'} | {_f(D0[k])} | "
                 f"{v['label'] if v else '—'} |")
    L += ["", "日の門で外した取引(外した / 全体): " + "、".join(f"{k} {a} / {b}" for k, (a, b) in r["dropped"].items()), ""]
    L += ["## W4 水準(窓の全期間)", "", "| 形 | 1 日あたり | 取引/日 | 1 取引あたり | 取引 |", "|---|---|---|---|---|"]
    for k, v in r["W4"].items():
        L.append(f"| {k} | " + ("— | — | — | —" if not v else
                                f"{_f(v['pnl_per_day'])} | {v['trades_per_day']:.2f} | {_f(v['per_trade'])} | {v['trades']}") + " |")
    L += ["", "## W5 商品の前後(区間と MDE だけ。言葉は当てない = 決め g)", "",
          "| 差 | FX(〜2024-03-27)平均 [区間] | MDE | 日数 | CFD(2024-03-28〜)平均 [区間] | MDE | 日数 |",
          "|---|---|---|---|---|---|---|"]
    for k in W5_PAIRS:
        a, b = r["W5"]["FX"].get(k), r["W5"]["CFD"].get(k)
        L.append(f"| {k} | {_ci(a)} | {_f(a['mde']) if a else '—'} | {a['days'] if a else '—'} | {_ci(b)} | "
                 f"{_f(b['mde']) if b else '—'} | {b['days'] if b else '—'} |")
    L += ["", "## W7 年ごと(区間と MDE だけ)", "", "| 差 | " + " | ".join(f"{y} 平均 [区間] (MDE, 日数)" for y in r["W7"]["years"]) + " |",
          "|---|" + "---|" * len(r["W7"]["years"])]
    for k in PAIRS:
        cells = []
        for y, dd in r["W7"]["years"].items():
            v = dd.get(k)
            cells.append("—" if not v else f"{_ci(v)} ({_f(v['mde'])}, {v['days']})")
        L.append(f"| {k} | " + " | ".join(cells) + " |")
    if r["W7"].get("vol"):
        L += ["", "W7 日のボラ(前の日の 1 分足の |対数の値動き| の平均、bp)。境 = その年に使った前の暦年の 1/3・2/3 分位:", "",
              "| 年 | 境(低/中, 中/高) | その年の日の中央値 | 低 | 中 | 高 |", "|---|---|---|---|---|---|"]
        for v in r["W7"]["vol"]:
            e = "—" if not v["edges"] else f"{v['edges'][0]:.3f}, {v['edges'][1]:.3f}"
            mv = "—" if v["median_vol"] is None else f"{v['median_vol']:.3f}"
            L.append(f"| {v['year']} | {e} | {mv} | {v['days']['low']} | {v['days']['mid']} | {v['days']['high']} |")
    L += ["", "## W6 マチルダの約定の仮定", "",
          "良い側・悪い側を別々に出し、同じ側どうしでだけ比べた(上の表の「良」「悪」)。主の側は決めていない。"
          "順序の確かめ W6b は `docs/RESEARCH/WINDOW1/W6B_PRESEAL/`(封印の前の 6 日)と、窓の 10 日の表(別の台本)。", "",
          "## W8 多重性", "", W8_TEXT, "", "## W10 意図の地図の制限", "", W10_TEXT, ""]
    return "\n".join(L)


# ---------------------------------------------------------------- d0 の計算し直し(元のデータ。窓は読まない)

def check_d0(trades: dict, cls: dict[str, str], periods: dict[str, tuple[date, date]]) -> dict:
    """W3 の d0 を元の走らせから同じ読み方で計算し直す。periods[形] = その形の基準の走らせの期間(lo, hi)。"""
    tr, dropped = series(trades, cls)
    out = {}
    for k, (x, b) in PAIRS.items():
        if tr.get(x) is None or tr.get(b) is None:
            out[k] = None
            continue
        lo, hi = periods[b.split("+")[0]]
        xs, bs = daily(tr[x], lo, hi), daily(tr[b], lo, hi)
        m = float(np.mean(np.array(xs) - np.array(bs)))
        out[k] = {"d0_recomputed": m, "d0_fixed": D0[k], "match": round(m, 2) == round(D0[k], 2)}
    # K-B − K-A の d0 は事前登録で「表 1b の 2 つの平均の差(+1.13 − +12.00)」= 小数 2 桁に丸めた 2 項の差と決めてある。
    # 丸める前の差とは 0.01 ずれうるので、丸めた 2 項の差でも突き合わせる(d0 は事前登録の値のまま使う)
    a, b = out.get("K-B − K-0"), out.get("K-A − K-0")
    if out.get("K-B − K-A") and a and b:
        r2 = round(a["d0_recomputed"], 2) - round(b["d0_recomputed"], 2)
        out["K-B − K-A"]["d0_from_rounded_terms"] = r2
        out["K-B − K-A"]["match"] = round(r2, 2) == round(D0["K-B − K-A"], 2)
    return {"diffs": out, "dropped": dropped}


def _period(d: str) -> tuple[date, date]:
    with open(os.path.join(d, "summary.json"), encoding="utf-8") as fh:
        p0, p1 = json.load(fh)["period"]
    lo = datetime.fromisoformat(p0.replace("Z", "+00:00")).date()
    hi = (datetime.fromisoformat(p1.replace("Z", "+00:00")) - timedelta(microseconds=1)).date()
    return lo, hi


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-d0", action="store_true")
    ap.add_argument("--root", default=RUNS_ROOT)
    a = ap.parse_args(argv)
    import vol_split_daily as vs  # noqa: E402
    os.makedirs(OUT, exist_ok=True)
    if a.check_d0:
        cls = vs.classify(vs.daily_vol(vs.load_closes_by_day()))
        trades = {k: read_trades(d) for k, d in ORIG.items()}
        periods = {k: _period(d) for k, d in ORIG.items()}
        r = check_d0(trades, cls, periods)
        L = ["# W3 の d0 の計算し直し(元のデータ、窓は読まない)", "",
             "`scripts/w4_measure/window1_read.py --check-d0` が出した。走らせの結果を見る前の確かめ。", "",
             "| 差 | 計算し直した値 | 丸めた 2 項の差(K-B − K-A だけ) | 事前登録の値 | 小数 2 桁で一致 |", "|---|---|---|---|---|"]
        for k, v in r["diffs"].items():
            L.append(f"| {k} | {_f(v['d0_recomputed']) if v else '—'} | {_f(v.get('d0_from_rounded_terms')) if v else '—'} | "
                     f"{_f(D0[k])} | {v['match'] if v else '—'} |")
        L += ["", "K-B − K-A の事前登録の値は「表 1b の 2 つの平均の差」(小数 2 桁に丸めた 2 項の差)。一致はその差で見る。"
              "W9 の言葉には事前登録の値をそのまま使う。"]
        L += ["", "日の門で外した取引(外した / 全体): " + "、".join(f"{k} {x} / {y}" for k, (x, y) in r["dropped"].items()), ""]
        with open(os.path.join(OUT, "D0_CHECK.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(L))
        print("\n".join(L))
        return 0 if all(v and v["match"] for v in r["diffs"].values()) else 1
    vol = vs.daily_vol(vs.load_closes_by_day(window=True))
    cls = vs.classify(vol, window=True)
    trades = {k: read_trades(os.path.join(a.root, k)) for k in K_RUNS + M_RUNS}
    r = build(trades, cls, vol)
    with open(os.path.join(OUT, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write(render(r))
    with open(os.path.join(OUT, "read.json"), "w", encoding="utf-8") as fh:
        json.dump(r, fh, ensure_ascii=False, indent=1, default=str)
    print(f"-> {OUT}  missing={r['missing']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
