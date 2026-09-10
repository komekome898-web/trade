"""H3 の分解: 入口の遅れと出口の遅れを分ける(`docs/PHASE2/K1/H3_DECOMP_PREREG.md`、第 4 周、L-078)。

**機構は変えない。** 原典の建玉機械(即時執行)が切った各取引 (入口足 i, 決済足 k, 向き pos) を、
価格だけ変えて 4 通りに値付けする:

    EE: close[i]   → close[k]      原典そのもの
    DE: close[i+1] → close[k]      入口だけ 1 本遅らせる
    ED: close[i]   → close[k+1]    出口だけ 1 本遅らせる
    DD: close[i+1] → close[k+1]    両方遅らせる(無効化を外した土台では第 12 部 ② と同一 = 再現ゲート)

取引の集合は 4 腕で同一(k+1 が期末を越える取引は 4 腕すべてから外す)。
帰無・MDE・判定バーは作らない。経費は引かない。封印(BitMEX 2020-2021)は開けない。

    PYTHONPATH=src:scripts python scripts/measure_katsuo_delay_decomp.py [--flip-body --no-invalidation] [--source binance]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from datetime import datetime
from pathlib import Path

import k1_source
import measure_katsuo_dispersion as base
import measure_katsuo_effect as eff

ARMS = ("EE", "DE", "ED", "DD")
BOOTSTRAP = eff.BOOTSTRAP


def reprice(bars, sigs, trades):
    """原典の取引を 4 通りに値付けし直す。返り値: 腕 → [(入口足 i, リターン bp, 保有, 決済理由)]、
    k+1 が無くて外した件数、DE で入口 = 出口になった件数。向き pos は入口足のシグナル(建玉はシグナルの向きに建つ)。"""
    n_bars = len(bars)
    out = {a: [] for a in ARMS}
    dropped = zero_de = 0
    for i, _r, hold, why in trades:
        k = i + hold
        if k + 1 >= n_bars:
            dropped += 1
            continue
        pos = sigs[i][0]
        assert pos in (1, -1), "入口足にはシグナルがあるはず"
        ci, ci1, ck, ck1 = bars[i][4], bars[i + 1][4], bars[k][4], bars[k + 1][4]
        if min(ci, ci1, ck, ck1) <= 0:
            dropped += 1
            continue
        if k == i + 1:
            zero_de += 1
        out["EE"].append((i, pos * (ck / ci - 1.0) * 1e4, hold, why))
        out["DE"].append((i, pos * (ck / ci1 - 1.0) * 1e4, hold, why))
        out["ED"].append((i, pos * (ck1 / ci - 1.0) * 1e4, hold, why))
        out["DD"].append((i, pos * (ck1 / ci1 - 1.0) * 1e4, hold, why))
    return out, dropped, zero_de


def day_block_ci(trades, bar_ts, seed_key, reps=BOOTSTRAP):
    """`measure_katsuo_effect.block_bootstrap` と同じ統計量(入口の日でブロック、日を復元抽出、プール平均)を
    日ごとの和と件数で計算する(結果は同じ、速いだけ)。種はセル名 × 腕の sha256 で固定。"""
    if not trades:
        return [float("nan"), float("nan")]
    byday: dict[int, list[float]] = {}
    for idx, r, _h, _w in trades:
        byday.setdefault(bar_ts[idx] // 86400, [0.0, 0.0])
        byday[bar_ts[idx] // 86400][0] += r
        byday[bar_ts[idx] // 86400][1] += 1
    days = list(byday.values())
    rng = random.Random(int(hashlib.sha256(seed_key.encode()).hexdigest()[:12], 16))
    means = []
    for _ in range(reps):
        s = c = 0.0
        for _ in range(len(days)):
            d = days[rng.randrange(len(days))]
            s += d[0]
            c += d[1]
        if c:
            means.append(s / c)
    means.sort()
    return [round(means[int(0.025 * (len(means) - 1))], 3), round(means[int(0.975 * (len(means) - 1))], 3)]


def summarize(trades, years, ts, seed_key):
    rs = [r for _i, r, _h, _w in trades]
    n = len(rs)
    mean = sum(rs) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in rs) / (n - 1)) if n > 1 else float("nan")
    per_year = {}
    for y in sorted(set(years)):
        ys = [r for i, r, _h, _w in trades if years[i] == y]
        if ys:
            per_year[str(y)] = {"n": len(ys), "mean_bp": round(sum(ys) / len(ys), 3)}
    return {"n": n, "mean_bp": round(mean, 3), "ci95_bp": day_block_ci(trades, ts, seed_key),
            "sd_bp": round(sd, 1), "hold_median": sorted(h for _i, _r, h, _w in trades)[n // 2],
            "per_year": per_year}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--feet", type=int, nargs="+", default=list(eff.FEET))
    ap.add_argument("--flip-body", action="store_true", help="土台に H1 を載せる")
    ap.add_argument("--no-invalidation", action="store_true", help="土台に H2a を載せる")
    ap.add_argument("--out", default=None)
    k1_source.add_source_args(ap)
    args = ap.parse_args()
    start, end = k1_source.resolve_range(args)
    use_invalid = not args.no_invalidation
    tag = {(False, True): "", (True, True): "_flipbody", (False, False): "_noinval", (True, False): "_flip_noinval"}[
        (args.flip_body, use_invalid)]
    if args.out is None:
        args.out = str(k1_source.out_dir(args.source) / f"delay_decomp{tag}.json")
    mech_path = k1_source.out_dir(args.source) / f"effect{tag}_delay.json"     # 第 12 部の遅らせた機構
    mech = json.loads(mech_path.read_text("utf-8"))["cells"] if mech_path.exists() else {}
    gate_exact = not use_invalid                                                 # 無効化なし → DD は機構と一致するはず

    print(f"{args.source} 区間 {start} 〜 {end}(BitMEX の判定区間 2020-2021 には触れない)。土台 {tag or '原典'}")
    seconds = k1_source.load_bars(args.source, start, end)
    gs = eff.gates()
    cells = {}
    repro = []
    for foot in args.feet:
        bars = base.fold(seconds, foot)
        ts = [b[0] for b in bars]
        years = [datetime.utcfromtimestamp(t).year for t in ts]
        for g in gs:
            sg = eff.signals(bars, g[0], g[1], flip_body=args.flip_body)
            for keep in eff.STRENGTHS:
                tr = eff.simulate(bars, sg, None if keep == "both" else keep, use_invalid=use_invalid)
                if len(tr) < 30:
                    continue
                key = f"{foot}|{eff.label(g)}|{keep}"
                arms, dropped, zero_de = reprice(bars, sg, tr)
                cell = {"foot": foot, "gate": eff.label(g), "strength": keep,
                        "n": len(arms["EE"]), "dropped_end": dropped, "de_zero_length": zero_de,
                        "arms": {a: summarize(arms[a], years, ts, f"{key}|{a}") for a in ARMS}}
                ee, de, ed, dd = (arms[a] for a in ARMS)
                n = len(ee)
                cell["decomp_bp"] = {
                    "entry_delay": round(sum(b[1] - a[1] for a, b in zip(ee, de)) / n, 3),
                    "exit_delay": round(sum(b[1] - a[1] for a, b in zip(ee, ed)) / n, 3),
                    "interaction": round(sum(d[1] - b[1] - c[1] + a[1] for a, b, c, d in zip(ee, de, ed, dd)) / n, 3),
                }
                m = mech.get(key)
                if m is not None:
                    diff = {"n_mech": m["n"], "mean_mech_bp": m["mean_bp"],
                            "dn": m["n"] - n, "dmean_bp": round(m["mean_bp"] - cell["arms"]["DD"]["mean_bp"], 3)}
                    cell["dd_vs_mechanism"] = diff
                    if gate_exact:
                        ok = diff["dn"] == 0 and abs(diff["dmean_bp"]) < 2e-3
                        repro.append({"key": key, "ok": ok, **diff})
                        if not ok:
                            raise SystemExit(f"再現ゲート不一致(DD vs 第 12 部 ②): {key} {diff}")
                cells[key] = cell
        c5 = cells.get(f"{foot}|s19/b24|both")
        if c5:
            d = c5["decomp_bp"]
            print(f"  {foot:>3}分 完了。s19/b24 両方: EE {c5['arms']['EE']['mean_bp']:+.2f} DE {c5['arms']['DE']['mean_bp']:+.2f}"
                  f" ED {c5['arms']['ED']['mean_bp']:+.2f} DD {c5['arms']['DD']['mean_bp']:+.2f}"
                  f" | 入口 {d['entry_delay']:+.2f} 出口 {d['exit_delay']:+.2f} 交互 {d['interaction']:+.2f} n={c5['n']:,}")

    Path(args.out).write_text(json.dumps({
        "note": ("H3 の分解: 原典の建玉機械が切った同じ取引を {入口 即時/1 本遅れ} × {出口 即時/1 本遅れ} で値付けし直す。"
                 "機構は変えていない。帰無・MDE・判定バーは作っていない。経費は引いていない。"),
        "explore": [start.isoformat(), end.isoformat()],
        "source": args.source, "load": k1_source.last_load,
        "flip_body": args.flip_body, "use_invalid": use_invalid,
        "mechanism_reference": str(mech_path.name) if mech else None,
        "reproduction_gate": repro,
        "bootstrap_reps": BOOTSTRAP, "seed": "sha256(cell|arm)",
        "family": {"feet": list(args.feet), "gates": [eff.label(g) for g in gs], "strengths": list(eff.STRENGTHS)},
        "arms": list(ARMS),
        "cells": cells,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    if repro:
        print(f"再現ゲート(DD vs 第 12 部 ②) {sum(r['ok'] for r in repro)}/{len(repro)} 一致")
    print(f"\nセル {len(cells)} 件 → {args.out}")


if __name__ == "__main__":
    main()
