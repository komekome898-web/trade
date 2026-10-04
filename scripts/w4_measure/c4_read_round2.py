#!/usr/bin/env python3
"""マチルダ(レンジ、カード 4)の改良の周 2(比の門 × 中心から測る利確 4:3、走らせる前の期間だけから決める比の門)の表を作る。

L-627 の段取り 2、L-628「ア では進めてください」。走らせの一覧は `c4_limit_batch.py` の R2(--r2)。
事前登録 = `docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim/families_r2/R2/PREREG.md`。
読み方の決まり(6 本を走らせる前に、この台本と `tests/research/test_c4_read_round2.py` で固めた):

R1 走らせ(同じ側どうし): 基準 = v37、利確だけ = A1_center_4_3、固定の門だけ = D_ratio_gate12.96、
   固定の門 × 利確 = R2_ratio_gate12.96_center_4_3、過去だけの門 = R2_ratio_gate_rolling、
   過去だけの門 × 利確 = R2_ratio_gate_rolling_center_4_3。
R2 足し算になるか(機構の仮説「比の門はブレイクの大負けを外し、利確の形はそこに触らないので、重ねると両方の効きが残る」):
   門ごと(固定・過去だけ)に 1 日あたりで 利確だけの差・門だけの差・両方の差・重なりの分 = 両方 − 利確だけ − 門だけ
   (c4_read_combo.split と同じ)。軸は 損益・小勝ちの和・大負けの和・ブレイクで閉じた取引の和(c4_read_r2.load_run)。
   取引の数の差を並べる。向きのラベルは c4_read_r2.label(良い側と悪い側の符号)。
R3 過去だけの門 − 固定の門: 門だけの差どうし・両方の差どうしの差(1 日あたり、軸は R2 と同じ)。
R4 年の一致: 2016〜2023 の 8 年で、両方 − 良い方の単独(c4_read_combo.year_agree_vs_best_single と同じ数え方)。
   過去だけの門は最初の 180 日に門が掛からない(PREREG)ので、2016 年はその期間を含む。
R5 取引で見た重なり(設計の段の判定の代替で 2 名とも「測っていない」と挙げた点。R2 の仮説を取引で直接確かめる):
   v37 の大負けの取引(損益 −10 bp 以下、c4_limit_batch の big_loss と同じ線)を入りの時刻(entry_t)で突き合わせ、
   「門で外れた」(門だけの走らせに同じ entry_t が無い)と「利確で大負けでなくなった」(利確だけの走らせの同じ entry_t の
   取引の損益が −10 bp より大きい)に分け、両方・門だけ・利確だけ・どちらでもない の本数と v37 での損益の和。
   持ち高の道が変わると同じ時刻でも別の取引になる(突き合わせは近似)。
R6 検出力: 両方(固定・過去だけ)と各単独について、v37 との日ごとの損益の差(出の時刻の UTC の日。取引の無い日は 0。
   日の範囲は v37 の summary の period)の平均、circular block bootstrap(塊 5 日、1,000 回、種 20261004、95% 百分位)、
   MDE = mde(n = 日の数, sd = se × √n, 5% 両側, 80%, 正規近似)。区間の両端と MDE を並べる。
R7 経費なし。探索の読みで判定ではない。「効く / 効かない」の境は置かない(A-12)。良い側・悪い側を両方出し、同じ側どうしでだけ比べる。

出力: families_r2/READ_ROUND2/TABLES.md と read.json。数字は手で書かない(research-protocol §1.2)。

    python3 scripts/w4_measure/c4_read_round2.py [--root <families_r2>]
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c4_read_combo as cc  # noqa: E402
import c4_read_r2 as r2  # noqa: E402

SIDES = ("good", "bad")
AXES = ("pnl", "small_win", "big_loss", "closed_by_break")
BIG = -10.0
SEED, N_RES, BLOCK = 20261004, 1000, 5
GATES = {"fixed": ("D_ratio_gate12.96", "R2_ratio_gate12.96_center_4_3"),
         "rolling": ("R2_ratio_gate_rolling", "R2_ratio_gate_rolling_center_4_3")}


def names(gate: str, side: str) -> dict:
    g, both = GATES[gate]
    return {"base": f"v37_{side}", "tp": f"A1_center_4_3_{side}", "ruler": f"{g}_{side}", "both": f"{both}_{side}"}


def wanted() -> set[str]:
    return {n for gate in GATES for s in SIDES for n in names(gate, s).values()}


def decompose(runs: dict) -> dict:
    """R2・R4。門ごと・側ごとの split と年の一致。split の 'ruler' は門だけの差。"""
    out = {}
    for gate in GATES:
        row = {}
        for s in SIDES:
            nm = names(gate, s)
            if not all(n in runs for n in nm.values()):
                row = None
                break
            row[s] = {ax: cc.split({k: runs[n]["per_day"][ax] for k, n in nm.items()}) for ax in AXES}
            row[s]["trades"] = cc.split({k: runs[n]["per_day"]["trades"] for k, n in nm.items()})
            row[f"years_{s}"] = cc.year_agree_vs_best_single(runs, nm)
        if row is not None:
            row["labels"] = {k: r2.label(row["good"]["pnl"][k], row["bad"]["pnl"][k])
                             for k in ("ruler", "both", "interaction")}
        out[gate] = row
    return out


def rolling_minus_fixed(dec: dict) -> dict | None:
    """R3。"""
    f, r = dec.get("fixed"), dec.get("rolling")
    if not f or not r:
        return None
    return {s: {ax: {"gate": r[s][ax]["ruler"] - f[s][ax]["ruler"], "both": r[s][ax]["both"] - f[s][ax]["both"]}
                for ax in AXES} for s in SIDES}


def read_trades(d: str) -> list[tuple[str, str, float]] | None:
    """(entry_t, exit_t, pnl_bp)。trades.json.gz から全部の走らせで同じに読む(時刻は UTC の ISO の文字列に直す)。
    2026-10-04 追記: 基準の v37・A1 の走らせには trades.csv.gz が無い(git に入れたのは trades.json.gz だけ)ので、
    同じ取引の行を持つ trades.json.gz に替えた。読み方の決まり R1〜R7 は変えていない。"""
    p = os.path.join(d, "trades.json.gz")
    if not os.path.isfile(p):
        return None
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        o = json.load(fh)
    scale = {"ns": 1, "s": 10**9}[o["t_unit"]]

    def iso(t) -> str:
        ns = int(t) * scale
        if ns % 10**9:
            raise ValueError(f"秒未満の時刻 {ns}(この読みは秒で突き合わせる)")
        return datetime.fromtimestamp(ns // 10**9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return [(iso(e), iso(x), float(p_)) for e, x, p_ in zip(o["entry_t_ns"], o["exit_t_ns"], o["pnl_bp"])]


def big_loss_overlap(base: list, gate: list, tp: list) -> dict:
    """R5。"""
    in_gate = {e for e, _, _ in gate}
    tp_pnl = {}
    for e, _, p in tp:
        tp_pnl.setdefault(e, p)
    out = {k: {"trades": 0, "sum_bp": 0.0} for k in ("both", "gate_only", "tp_only", "neither")}
    for e, _, p in base:
        if p > BIG:
            continue
        gated = e not in in_gate
        tped = e in tp_pnl and tp_pnl[e] > BIG
        k = "both" if gated and tped else "gate_only" if gated else "tp_only" if tped else "neither"
        out[k]["trades"] += 1
        out[k]["sum_bp"] += p
    return out


def daily(rows: list, lo: date, hi: date) -> list[float]:
    """R6。出の時刻(UTC)の日ごとの損益の和。lo〜hi の全部の日。"""
    n = (hi - lo).days + 1
    out = [0.0] * n
    for _, x, p in rows:
        k = (datetime.fromisoformat(x.replace("Z", "+00:00")).date() - lo).days
        if 0 <= k < n:
            out[k] += p
    return out


def paired_ci(x: list[float], b: list[float]) -> dict:
    """R6。"""
    from bot.bt.validation import block_bootstrap_ci, mde
    d = [float(p - q) for p, q in zip(x, b)]
    ci = block_bootstrap_ci(d, block_len=BLOCK, n_resamples=N_RES, seed=SEED, alpha=0.05, method="circular",
                            statistic="mean")
    n = len(d)
    return {"mean": ci.estimate, "lo": ci.lo, "hi": ci.hi, "days": n,
            "mde": mde(n=n, sd=ci.se * n ** 0.5, alpha=0.05, power=0.80, sides=2, approx="normal")}


def render(r: dict) -> str:
    f = r2._f
    L = ["# マチルダ 改良の周 2: 比の門 × 中心から測る利確 4:3、過去だけから決める比の門", "",
         "`scripts/w4_measure/c4_read_round2.py` が出した。読み方の決まり R1〜R7 はその台本の docstring。経費の前。"
         "1 日あたり bp、v37 との差、良い側 / 悪い側。", ""]
    for gate, title in (("fixed", "固定の門(12.96、標本の中)"), ("rolling", "過去だけの門(前の 365 日の 70% 点)")):
        row = r["dec"].get(gate)
        L += [f"## {title}", ""]
        if not row:
            L += ["走らせがそろっていない", ""]
            continue
        L += ["| 軸 | 利確だけ | 門だけ | 両方 | 重なりの分 |", "|---|---|---|---|---|"]
        for ax in AXES + ("trades",):
            g, b = row["good"][ax], row["bad"][ax]
            c = lambda k: f"{f(g[k], 2)} / {f(b[k], 2)}"
            L.append(f"| {r2.AXIS_JA.get(ax, '取引/日')} | {c('tp')} | {c('ruler')} | {c('both')} | {c('interaction')} |")
        L += ["", f"向き(損益): 門だけ {row['labels']['ruler']}・両方 {row['labels']['both']}・重なり {row['labels']['interaction']}。"
              f"年の一致(両方 − 良い方の単独): {row['years_good']}/8 ・ {row['years_bad']}/8", ""]
    rf = r["rolling_minus_fixed"]
    if rf:
        L += ["## 過去だけの門 − 固定の門(R3)", "", "| 軸 | 門だけどうし | 両方どうし |", "|---|---|---|"]
        for ax in AXES:
            L.append(f"| {r2.AXIS_JA[ax]} | {f(rf['good'][ax]['gate'], 2)} / {f(rf['bad'][ax]['gate'], 2)} | "
                     f"{f(rf['good'][ax]['both'], 2)} / {f(rf['bad'][ax]['both'], 2)} |")
        L.append("")
    L += ["## 取引で見た重なり(R5。v37 の大負けの取引の本数 / v37 での損益の和 bp)", "",
          "| 門 | 側 | 両方 | 門だけ | 利確だけ | どちらでもない |", "|---|---|---|---|---|---|"]
    for key, o in sorted(r["overlap"].items()):
        if o:
            gate, s = key.split("|")
            L.append(f"| {gate} | {s} | " + " | ".join(f"{o[k]['trades']:,} / {o[k]['sum_bp']:+,.0f}"
                                                       for k in ("both", "gate_only", "tp_only", "neither")) + " |")
    L += ["", "## 日ごとの差の平均・95% 区間・MDE(R6。bp/日。v37 との差)", "",
          "| 走らせ | 平均 [区間] | MDE |", "|---|---|---|"]
    for name, c in sorted(r["ci"].items()):
        if c:
            L.append(f"| {name} | {c['mean']:+.2f} [{c['lo']:+.2f}, {c['hi']:+.2f}] | {c['mde']:.2f} |")
    if r.get("rolling_off"):
        L += ["", f"過去だけの門が掛からなかった日(summary の ratio_gate_rolling): {json.dumps(r['rolling_off'], ensure_ascii=False)}"]
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r2.DEFAULT_ROOT)
    a = ap.parse_args(argv)
    runs = {n: r2.load_run(os.path.join(a.root, n)) for n in sorted(wanted())
            if os.path.isfile(os.path.join(a.root, n, "analysis.json"))}
    missing = sorted(wanted() - set(runs))
    dec = decompose(runs)
    tr = {n: read_trades(os.path.join(a.root, n)) for n in runs}
    overlap, ci = {}, {}
    for s in SIDES:
        base = f"v37_{s}"
        if tr.get(base) is None:
            continue
        with open(os.path.join(a.root, base, "summary.json"), encoding="utf-8") as fh:
            p0, p1 = json.load(fh)["period"]
        lo = datetime.fromisoformat(p0.replace("Z", "+00:00")).date()
        hi = (datetime.fromisoformat(p1.replace("Z", "+00:00")) - timedelta(microseconds=1)).date()
        db = daily(tr[base], lo, hi)
        for gate in GATES:
            nm = names(gate, s)
            if tr.get(nm["ruler"]) is not None and tr.get(nm["tp"]) is not None:
                overlap[f"{gate}|{s}"] = big_loss_overlap(tr[base], tr[nm["ruler"]], tr[nm["tp"]])
            for k in ("tp", "ruler", "both"):
                if tr.get(nm[k]) is not None and nm[k] not in ci:
                    ci[nm[k]] = paired_ci(daily(tr[nm[k]], lo, hi), db)
    off = {}
    for s in SIDES:
        p = os.path.join(a.root, f"R2_ratio_gate_rolling_{s}", "summary.json")
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as fh:
                off[s] = json.load(fh).get("ratio_gate_rolling")
    r = {"dec": dec, "rolling_minus_fixed": rolling_minus_fixed(dec), "overlap": overlap, "ci": ci,
         "rolling_off": off, "missing": missing}
    out = os.path.join(a.root, "READ_ROUND2")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write(render(r) + ("" if not missing else "\n無い走らせ: " + "・".join(missing) + "\n"))
    with open(os.path.join(out, "read.json"), "w", encoding="utf-8") as fh:
        json.dump(r, fh, ensure_ascii=False, indent=1, default=float)
    print(f"runs {len(runs)} missing {len(missing)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
