#!/usr/bin/env python3
"""カツオ(ヒゲ逆張り、カード 2)の改良の周 2(改良した形を 1 本に組む)の表を作る。

L-627 の段取り 1、L-628「ア では進めてください」。走らせの一覧は `c2_limit_batch.py` の JOBS_R2(--r2)。
事前登録 = `docs/RESEARCH/cards/c2_owner_xvenue_wick/limit_sim/runs/READ_R2/PREREG.md`。
読み方の決まり(16 本を走らせる前に、この台本と `tests/research/test_c2_read_r2.py` で固めた):

R1 比べる相手: 15 分・入り方 a・参照の形・弱いだけの weak_f15_close_a(門なし・降り方なし)を基準 B とする。
   T_N = weak_f15_close_a_time<N>(時間で降りるだけ)、G = weak_f15_rgate_close_a(直前 365 日の門だけ)、
   C_N = weak_f15_rgate_close_a_time<N>(両方)。N = 6〜12。
R2 足し算になるか(機構の仮説「時間で降りるは長い負けの保有を切り、門は静かな場面の取引を外すので、別の取引に効き、
   組むと足し算に近い」の確かめ): 1 日あたりの損益の差 dT = T_N − B、dG = G − B、dC = C_N − B と、
   重なりの分 = dC − dT − dG、組んだ形 − 良い方の単独 = dC − max(dT, dG)。取引の数の差・1 取引あたりの差・
   勝ちの和と負けの和の差(1 日あたり)を並べる。
R3 年ごとの安定: C_N − B の年の差の符号が全期間の差の符号と同じ年の数(2018〜2023 の n/6、c2_read_limit.year_agreement)。
   年ごとの差の表(C_N − B・T_N − B・G − B)も出す。門は直前 365 日の合図を使うので、2017-08〜2018-08 は履歴が 1 年に
   満たない(K-044 と同じ扱い。年の一致は 2018 からで、2018 年はこの期間を含む)。
R4 N の形: N = 6〜12 の dC と dT を並べ、最良の N と、その両隣(N ± 1)の dC を出す。最良は「7 通りの中の最良」と書く
   (候補の数 7)。境は置かない(A-12)。
R5 保有時間の帯ごとの差(C_N − B): 0〜5・5〜30・30〜120・120〜480・480 分〜(c2_read_limit.hold_sums と同じ帯)。
R6 内部結合(K-040、--ref-join-bitflyer)の下での同じ差: B_j = weak_f15_close_a_refjoin、T6_j、G_j、C6_j・C12_j。
   dC_j − dC(結合あり − なし)を出し、組んだ形の差が bitFlyer に足が無い分の扱いでどれだけ動くかを読む。
   内部結合は本番の扱いではなく、扱いの違いへの敏感さの代理(△)。T12_j は無いので、重なりの分は N = 6 だけ。
R7 経費なし。探索の読みで判定ではない。「効く / 効かない」の境は置かない。取引の数が変わる比べなので、1 日あたりの損益の差に
   取引の数の差と 1 取引あたりの差を必ず並べる(設計の段の判定の代替、2 名の答え。PREREG.md)。
R8 取引で見た重なり(設計の段の判定の代替で 2 名とも「測っていない」と挙げた点。R2 の機構の仮説を取引で直接確かめる):
   trades.csv.gz の合図の時刻(signal_t)で突き合わせ、B の取引を「門で外れた」(B にあり G に無い)と
   「時間で切られた」(T_N で終わり方が「時間で降りる」の取引と同じ signal_t)に分け、両方・門だけ・時間だけ・どちらでもない
   の 4 つの群の本数と、B での損益の和を出す。合図の時刻が同じでも持ち高の道が変わると別の取引になる(突き合わせは近似)。
R9 門の履歴が 1 年に満たない期間(2017-08〜2018-08)を外した見方として、年の差の 2019〜2023 年の和(bp)を並べる。
R10 検出力(W4 の完了の形の「検出力」): 組んだ形 C_N と時間だけ T_N のそれぞれについて、基準 B との日ごとの損益の差
   (取引の出の時刻の UTC の日で合計。取引の無い日は 0。日の範囲は B の summary の period)の平均と、
   circular block bootstrap(塊 5 日、1,000 回、種 20261004、95% 百分位、bot.bt.validation.block_bootstrap_ci)の区間、
   MDE = mde(n = 日の数, sd = se × √n, 5% 両側, 80%, 正規近似)。区間の両端と MDE を並べ、「効く / 効かない」と言わない。

出力: runs/READ_R2/TABLES.md と read.json。数字は手で書かない(research-protocol §1.2)。

    python3 scripts/w4_measure/c2_read_r2.py [--root <runs>]
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c2_read_limit as rl  # noqa: E402

NS = (6, 7, 8, 9, 10, 11, 12)
B, G = "weak_f15_close_a", "weak_f15_rgate_close_a"
BJ, GJ = "weak_f15_close_a_refjoin", "weak_f15_rgate_close_a_refjoin"


def T(n: int, j: bool = False) -> str:
    return f"weak_f15_close_a{'_refjoin' if j else ''}_time{n}"


def C(n: int, j: bool = False) -> str:
    return f"weak_f15_rgate_close_a{'_refjoin' if j else ''}_time{n}"


def wanted() -> set[str]:
    w = {B, G, BJ, GJ, T(6, True), C(6, True), C(12, True)}
    for n in NS:
        w |= {T(n), C(n)}
    return w


def dd(runs: dict, alls: dict, x: str, b: str) -> dict | None:
    """x − b の 1 日あたりの差(R2 の欄)。どちらかが無ければ None。"""
    if x not in runs or b not in runs:
        return None
    X, Bb = runs[x], runs[b]
    return {"pnl": X["per_day"]["pnl"] - Bb["per_day"]["pnl"],
            "trades": X["per_day"]["trades"] - Bb["per_day"]["trades"],
            "per_trade": X["per_trade"] - Bb["per_trade"],
            "win": alls[x]["sum_win_bp"] / X["days"] - alls[b]["sum_win_bp"] / Bb["days"],
            "loss": alls[x]["sum_loss_bp"] / X["days"] - alls[b]["sum_loss_bp"] / Bb["days"]}


def additivity(dT: dict | None, dG: dict | None, dC: dict | None) -> dict | None:
    """R2。重なりの分と、組んだ形 − 良い方の単独。"""
    if dT is None or dG is None or dC is None:
        return None
    return {"overlap": dC["pnl"] - dT["pnl"] - dG["pnl"], "vs_best_single": dC["pnl"] - max(dT["pnl"], dG["pnl"])}


def year_diffs(runs: dict, x: str, b: str) -> dict | None:
    if x not in runs or b not in runs:
        return None
    return {y: runs[x]["year_pnl"].get(y, 0.0) - runs[b]["year_pnl"].get(y, 0.0) for y in rl.YEARS}


def best_n(rows: list[dict]) -> dict | None:
    """R4。dC が最大の N と両隣。rows は N の昇順で、dC が None の行は除く。"""
    have = [r for r in rows if r["dC"] is not None]
    if not have:
        return None
    top = max(have, key=lambda r: r["dC"]["pnl"])
    by = {r["n"]: r["dC"]["pnl"] for r in have}
    return {"n": top["n"], "dC": top["dC"]["pnl"], "candidates": len(have),
            "left": by.get(top["n"] - 1), "right": by.get(top["n"] + 1)}


SEED, N_RES, BLOCK = 20261004, 1000, 5


def read_daily(d: str, lo: date, hi: date) -> list[float] | None:
    """R10。trades.csv.gz の出の時刻(UTC)の日ごとの損益の和。lo〜hi(両端を含む)の全部の日、取引が無い日は 0。"""
    p = os.path.join(d, "trades.csv.gz")
    if not os.path.isfile(p):
        return None
    n = (hi - lo).days + 1
    out = [0.0] * n
    with gzip.open(p, "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            k = (datetime.fromisoformat(r["exit_t"].replace("Z", "+00:00")).date() - lo).days
            if 0 <= k < n:
                out[k] += float(r["pnl_bp"])
    return out


def paired_ci(x: list[float], b: list[float]) -> dict:
    """R10。日ごとの差の平均・区間・MDE。"""
    from bot.bt.validation import block_bootstrap_ci, mde
    d = [float(p - q) for p, q in zip(x, b)]
    ci = block_bootstrap_ci(d, block_len=BLOCK, n_resamples=N_RES, seed=SEED, alpha=0.05, method="circular",
                            statistic="mean")
    n = len(d)
    return {"mean": ci.estimate, "lo": ci.lo, "hi": ci.hi, "days": n,
            "mde": mde(n=n, sd=ci.se * n ** 0.5, alpha=0.05, power=0.80, sides=2, approx="normal")}


def read_signals(d: str) -> list[tuple[str, str, float]] | None:
    """trades.csv.gz の (signal_t, exit_reason, pnl_bp)。無ければ None。"""
    p = os.path.join(d, "trades.csv.gz")
    if not os.path.isfile(p):
        return None
    with gzip.open(p, "rt", encoding="utf-8", newline="") as fh:
        return [(r["signal_t"], r["exit_reason"], float(r["pnl_bp"])) for r in csv.DictReader(fh)]


def trade_overlap(b: list, g: list, t: list) -> dict:
    """R8。b・g・t = read_signals の行(B・G・T_N)。B の取引を 4 群に分け、本数と B での損益の和。"""
    in_g = {s for s, _, _ in g}
    cut = {s for s, why, _ in t if why == "時間で降りる"}
    out = {k: {"trades": 0, "sum_bp": 0.0} for k in ("both", "gate_only", "time_only", "neither")}
    for s, _, p in b:
        gated, timed = s not in in_g, s in cut
        k = "both" if gated and timed else "gate_only" if gated else "time_only" if timed else "neither"
        out[k]["trades"] += 1
        out[k]["sum_bp"] += p
    return out


def sum_years(yd: dict | None, years=range(2019, 2024)) -> float | None:
    """R9。"""
    return None if yd is None else sum(yd[y] for y in years)


def build(runs: dict, alls: dict, sig: dict | None = None, daily: dict | None = None) -> dict:
    dG = dd(runs, alls, G, B)
    rows = []
    for n in NS:
        dT, dC = dd(runs, alls, T(n), B), dd(runs, alls, C(n), B)
        rows.append({"n": n, "dT": dT, "dC": dC, "add": additivity(dT, dG, dC),
                     "years_agree": rl.year_agreement(runs[C(n)], runs[B]) if C(n) in runs and B in runs else None,
                     "year_dC": year_diffs(runs, C(n), B), "year_dT": year_diffs(runs, T(n), B),
                     "hold": (rl_hold_diff(runs[C(n)]["hold"], runs[B]["hold"])
                              if C(n) in runs and B in runs else None)})
        rows[-1]["dC_2019on"] = sum_years(rows[-1]["year_dC"])
        dy = daily or {}
        for key, name in (("ci_C", C(n)), ("ci_T", T(n))):
            rows[-1][key] = (paired_ci(dy[name], dy[B]) if dy.get(name) is not None and dy.get(B) is not None
                             else None)
        sg = sig or {}
        rows[-1]["overlap_trades"] = (trade_overlap(sg[B], sg[G], sg[T(n)])
                                      if all(sg.get(k) is not None for k in (B, G, T(n))) else None)
    dGj = dd(runs, alls, GJ, BJ)
    join = []
    for n in (6, 12):
        dCj = dd(runs, alls, C(n, True), BJ)
        dTj = dd(runs, alls, T(n, True), BJ) if n == 6 else None
        dC = next(r["dC"] for r in rows if r["n"] == n)
        join.append({"n": n, "dTj": dTj, "dCj": dCj, "add_j": additivity(dTj, dGj, dCj),
                     "dCj_minus_dC": (dCj["pnl"] - dC["pnl"]) if dCj is not None and dC is not None else None})
    return {"dG": dG, "year_dG": year_diffs(runs, G, B), "rows": rows, "best": best_n(rows), "dGj": dGj, "join": join}


def rl_hold_diff(x: list[dict] | None, b: list[dict] | None) -> list[dict] | None:
    """R5。"""
    if x is None or b is None:
        return None
    return [{"lo": p["lo"], "hi": p["hi"], "d_trades": p["trades"] - q["trades"], "d_sum_bp": p["sum_bp"] - q["sum_bp"]}
            for p, q in zip(x, b)]


def _f(x, nd=2) -> str:
    return "—" if x is None else rl._f(x, nd)


def render(r: dict) -> str:
    L = ["# カツオ 改良の周 2: 時間で降りる × 直前 365 日の門を組んだ形", "",
         "`scripts/w4_measure/c2_read_r2.py` が出した。読み方の決まり R1〜R7 はその台本の docstring。15 分・入り方 a・参照の形・"
         "弱いだけ。経費の前。bp/日。基準 B = weak_f15_close_a。", "",
         f"門だけ(G − B): 損益 {_f(r['dG'] and r['dG']['pnl'])}、取引の数 {_f(r['dG'] and r['dG']['trades'], 3)}", "",
         "## 表 1: 足し算になるか(N ごと、1 日あたり)", "",
         "| N | 時間だけ dT | 組んだ形 dC | 重なりの分 dC−dT−dG | 組んだ形 − 良い方の単独 | dC の取引の数の差 | dC の 1 取引あたりの差 | "
         "dC の勝ちの和の差 | dC の負けの和の差 | 年の一致 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for x in r["rows"]:
        dT, dC, ad = x["dT"], x["dC"], x["add"]
        L.append(f"| {x['n']} | {_f(dT and dT['pnl'])} | {_f(dC and dC['pnl'])} | {_f(ad and ad['overlap'])} | "
                 f"{_f(ad and ad['vs_best_single'])} | {_f(dC and dC['trades'], 3)} | {_f(dC and dC['per_trade'])} | "
                 f"{_f(dC and dC['win'])} | {_f(dC and dC['loss'])} | "
                 f"{'—' if x['years_agree'] is None else str(x['years_agree']) + '/' + str(len(rl.YEARS))} |")
    b = r["best"]
    if b:
        L += ["", f"R4: 組んだ形の最良は N = {b['n']}({b['candidates']} 通りの中の最良)dC {_f(b['dC'])}、"
                  f"両隣 N−1 {_f(b['left'])}・N+1 {_f(b['right'])}"]
    L += ["", "## 表 2: 年ごとの差(bp。C_N − B / T_N − B、G − B は最後の行)", "",
          "| N | " + " | ".join(str(y) for y in rl.YEARS) + " |", "|---|" + "---|" * len(rl.YEARS)]
    for x in r["rows"]:
        if x["year_dC"]:
            L.append(f"| C{x['n']} | " + " | ".join(f"{x['year_dC'][y]:+,.0f}" for y in rl.YEARS) + " |")
        if x["year_dT"]:
            L.append(f"| T{x['n']} | " + " | ".join(f"{x['year_dT'][y]:+,.0f}" for y in rl.YEARS) + " |")
    if r["year_dG"]:
        L.append("| G | " + " | ".join(f"{r['year_dG'][y]:+,.0f}" for y in rl.YEARS) + " |")
    L += ["", "## 表 1b: 日ごとの差の平均・95% 区間・MDE(R10。bp/日。基準 B との差)", "",
          "| N | 組んだ形 平均 [区間] | 組んだ形 MDE | 時間だけ 平均 [区間] | 時間だけ MDE |", "|---|---|---|---|---|"]
    for x in r["rows"]:
        c, t = x.get("ci_C"), x.get("ci_T")
        L.append(f"| {x['n']} | " + (f"{c['mean']:+.2f} [{c['lo']:+.2f}, {c['hi']:+.2f}] | {c['mde']:.2f}" if c else "— | —")
                 + " | " + (f"{t['mean']:+.2f} [{t['lo']:+.2f}, {t['hi']:+.2f}] | {t['mde']:.2f}" if t else "— | —") + " |")
    L += ["", "R9: 年の差の 2019〜2023 年の和(門の履歴が 1 年に満たない期間を外す。bp): "
          + "・".join(f"C{x['n']} {_f(x['dC_2019on'], 0)}" for x in r["rows"]),
          "", "## 表 2b: 取引で見た重なり(R8。B の取引の本数 / B での損益の和 bp)", "",
          "| N | 門と時間の両方 | 門だけ | 時間だけ | どちらでもない |", "|---|---|---|---|---|"]
    for x in r["rows"]:
        o = x["overlap_trades"]
        if o:
            L.append(f"| {x['n']} | " + " | ".join(f"{o[k]['trades']:,} / {o[k]['sum_bp']:+,.0f}"
                                                   for k in ("both", "gate_only", "time_only", "neither")) + " |")
    L += ["", "## 表 3: 保有時間の帯ごとの差(C_N − B。取引の数 / 損益の和 bp)", ""]
    bands = next((x["hold"] for x in r["rows"] if x["hold"]), None)
    if bands:
        L += ["| N | " + " | ".join(f"{h['lo']}〜{h['hi']} 分" if h["hi"] is not None else f"{h['lo']} 分〜" for h in bands)
              + " |", "|---|" + "---|" * len(bands)]
        for x in r["rows"]:
            if x["hold"]:
                L.append(f"| {x['n']} | " + " | ".join(f"{h['d_trades']:+,} / {h['d_sum_bp']:+,.0f}" for h in x["hold"]) + " |")
    L += ["", "## 表 4: 内部結合(△ 代理)の下での同じ差(基準 B_j = weak_f15_close_a_refjoin)", "",
          f"門だけ(G_j − B_j): {_f(r['dGj'] and r['dGj']['pnl'])}", "",
          "| N | 時間だけ dT_j | 組んだ形 dC_j | 重なりの分 | dC_j − dC(結合あり − なし) |", "|---|---|---|---|---|"]
    for x in r["join"]:
        L.append(f"| {x['n']} | {_f(x['dTj'] and x['dTj']['pnl'])} | {_f(x['dCj'] and x['dCj']['pnl'])} | "
                 f"{_f(x['add_j'] and x['add_j']['overlap'])} | {_f(x['dCj_minus_dC'])} |")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=rl.DEFAULT_ROOT)
    a = ap.parse_args(argv)
    runs, alls = {}, {}
    for n in sorted(wanted()):
        d = os.path.join(a.root, n)
        if not os.path.isfile(os.path.join(d, "summary.json")):
            continue
        runs[n] = rl.load_run(d)
        with open(os.path.join(d, "summary.json"), encoding="utf-8") as fh:
            alls[n] = json.load(fh)["all"]
    missing = sorted(wanted() - set(runs))
    sig = {k: read_signals(os.path.join(a.root, k)) for k in [B, G] + [T(n) for n in NS] if k in runs}
    with open(os.path.join(a.root, B, "summary.json"), encoding="utf-8") as fh:
        p0, p1 = json.load(fh)["period"]
    lo = datetime.fromisoformat(p0.replace("Z", "+00:00")).date()
    hi = (datetime.fromisoformat(p1.replace("Z", "+00:00")) - timedelta(microseconds=1)).date()
    daily = {k: read_daily(os.path.join(a.root, k), lo, hi) for k in [B] + [T(n) for n in NS] + [C(n) for n in NS]
             if k in runs}
    r = build(runs, alls, sig, daily)
    r["missing"] = missing
    out = os.path.join(a.root, "READ_R2")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write(render(r) + ("" if not missing else "\n無い走らせ: " + "・".join(missing) + "\n"))
    with open(os.path.join(out, "read.json"), "w", encoding="utf-8") as fh:
        json.dump(r, fh, ensure_ascii=False, indent=1)
    print(f"runs {len(runs)} missing {len(missing)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
