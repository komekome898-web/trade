"""**手 3 — 決済ルールのアブレーション**(`docs/PHASE2/K1/HANDOFF.md` §3)。

シグナル単体(第 4 部)では「弱い」が +2〜5 bp なのに、機構(第 2 部)を通すと +0.2〜1.1 bp に落ちる。
**決済ルールが取り分を削っているのか、母集団が違うだけなのかは分かっていない**(`RESULT.md` §4.6)。
それを分ける。

**これはアブレーションであって改良ではない。** 「弱いだけを使う BOT」を設計しない(流れの ③ の話)。

## 変種

`measure_katsuo_effect.simulate` と同じ 4 分岐を、決済ルールだけ差し替えて回す:

| 変種 | 無効化(ヒゲ先端割れ) | 反対シグナル | 保有上限 |
|---|---|---|---|
| `full`          | あり | 決済(弱)/ドテン(強) | なし | ← 第 2 部そのもの。**再現ゲート**
| `invalid_only`  | あり | **無視**(建玉は続く)   | なし |
| `opposite_only` | **なし** | 決済(弱)/ドテン(強) | なし |
| `fixed_h3`      | なし | 無視 | **3 本で必ず決済**(その間の新規シグナルは無視) |

`fixed_h3` は「建玉が無いときだけ建て、3 本で閉じる」なので、**第 4 部(全シグナルを独立に数える)
と第 2 部(建玉機械)の間**に位置する。第 4 部 h=3 との差が**母集団の差**、`full` との差が**決済ルールの差**。

## 再現ゲート

`full` の (n, 平均) が `effect.json` の全セルと**一致することを検査してから**出力する。

区間: `measure_katsuo_signal_horizon.day_bootstrap` / `cell_rng`(セルごとに種を固定)。
第 2 部は共有乱数列で区間を出していたので、`full` の区間は第 2 部と**わずかに違いうる**。平均と n は同じ。

    PYTHONPATH=src:scripts python scripts/measure_katsuo_exit_ablation.py
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

import measure_katsuo_dispersion as base
import measure_katsuo_effect as eff
from measure_katsuo_signal_horizon import cell_rng, day_bootstrap

REPO = Path(__file__).resolve().parents[1]
EFFECT = REPO / "docs" / "PHASE2" / "K1" / "effect.json"

EXPLORE_START = date(2017, 1, 1)
EXPLORE_END = date(2019, 12, 31)
FEET = (1, 3, 5, 15, 30, 60)
STRENGTHS = ("strong", "weak", "both")
MODES = ("full", "invalid_only", "opposite_only", "fixed_h3")
FIXED_H = 3


def simulate(bars, sigs, keep, mode):
    """`eff.simulate` の 4 分岐に、決済ルールの差し替えを足したもの。
    `mode == "full"` は `eff.simulate` と**同じ経路**を通る(再現ゲートで確認する)。"""
    pos = 0
    entry = 0.0
    entry_i = 0
    lcline = 0.0
    trades = []
    use_invalid = mode in ("full", "invalid_only")
    use_opposite = mode in ("full", "opposite_only")
    fixed = FIXED_H if mode == "fixed_h3" else None

    def close(i, price, why):
        nonlocal pos
        trades.append((entry_i, pos * (price / entry - 1.0) * 1e4, i - entry_i, why))
        pos = 0

    for i, (sig, lc, csign, strength) in enumerate(sigs):
        c = bars[i][4]
        if c <= 0:
            continue
        if fixed is not None and pos != 0 and i - entry_i >= fixed:
            close(i, c, "fixed_h")
        actionable = sig != 0 and (keep is None or strength == keep)

        if not actionable:
            if use_invalid and pos != 0 and csign == -pos:
                if (pos == 1 and c <= lcline) or (pos == -1 and c >= lcline):
                    close(i, c, "invalidated")
            continue

        if pos == sig:
            lcline = lc
        elif pos == -sig:
            if use_opposite:
                close(i, c, "reversed" if strength == "strong" else "opposite_weak")
                if strength == "strong":
                    pos, entry, entry_i, lcline = sig, c, i, lc
            # 無視する変種では建玉が続く(lcline も動かさない)
        else:
            pos, entry, entry_i, lcline = sig, c, i, lc
    return trades


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--feet", type=int, nargs="+", default=list(FEET))
    ap.add_argument("--out", default=str(REPO / "docs" / "PHASE2" / "K1" / "exit_ablation.json"))
    args = ap.parse_args()

    ref = json.loads(EFFECT.read_text("utf-8"))["cells"] if EFFECT.exists() else {}
    print(f"探索区間 {EXPLORE_START} 〜 {EXPLORE_END}(判定区間 2020-2021 には触れない)")
    seconds = base.load_seconds(EXPLORE_START, EXPLORE_END)
    gs = eff.gates()
    print(f"  秒バー {len(seconds):,} 行 / 変種 {len(MODES)} × 足 {len(args.feet)} × 門 {len(gs)} × 強さ 3")

    cells = {}
    repro = []
    for foot in args.feet:
        bars = base.fold(seconds, foot)
        ts = [b[0] for b in bars]
        years = [datetime.utcfromtimestamp(t).year for t in ts]
        for g in gs:
            sg = eff.signals(bars, g[0], g[1])
            for keep in STRENGTHS:
                for mode in MODES:
                    tr = simulate(bars, sg, None if keep == "both" else keep, mode)
                    if len(tr) < 30:
                        continue
                    n = len(tr)
                    rs = sorted(r for _i, r, _h, _w in tr)
                    mean = sum(rs) / n
                    # 損切りを外す変種は裾が変わりうるので、平均だけでなく散らばりと分位も出す
                    sd = (sum((x - mean) ** 2 for x in rs) / (n - 1)) ** 0.5 if n > 1 else float("nan")
                    q = {k: rs[min(n - 1, int(f * (n - 1)))] for k, f in
                         (("p05", 0.05), ("p25", 0.25), ("p50", 0.50), ("p75", 0.75), ("p95", 0.95))}
                    key = f"{mode}|{foot}|{eff.label(g)}|{keep}"
                    dsum: dict[int, float] = {}
                    dn: dict[int, int] = {}
                    for idx, r, _h, _w in tr:
                        dday = ts[idx] // 86400
                        dsum[dday] = dsum.get(dday, 0.0) + r
                        dn[dday] = dn.get(dday, 0) + 1
                    lo, hi = day_bootstrap(dsum, dn, cell_rng("exit_ablation", key))
                    why: dict[str, int] = {}
                    for _i, _r, _h, w in tr:
                        why[w] = why.get(w, 0) + 1
                    per_year = {}
                    for y in (2017, 2018, 2019):
                        ys = [r for i, r, _h, _w in tr if years[i] == y]
                        if ys:
                            per_year[str(y)] = {"n": len(ys), "mean_bp": round(sum(ys) / len(ys), 3)}
                    cells[key] = {
                        "mode": mode, "foot": foot, "gate": eff.label(g), "strength": keep,
                        "n": n, "mean_bp": round(mean, 3),
                        "ci95_bp": [round(lo, 3), round(hi, 3)],
                        "sd_bp": round(sd, 1),
                        "quantiles_bp": {k: round(v, 2) for k, v in q.items()},
                        "min_bp": round(rs[0], 1), "max_bp": round(rs[-1], 1),
                        "hold_median": sorted(h for _i, _r, h, _w in tr)[n // 2],
                        "exit_reasons": why, "per_year": per_year,
                    }
                    if mode == "full" and ref:
                        rc = ref.get(f"{foot}|{eff.label(g)}|{keep}")
                        if rc is not None:
                            ok = rc["n"] == n and abs(rc["mean_bp"] - mean) < 2e-3
                            repro.append({"key": key, "ok": ok, "n": n, "n_ref": rc["n"],
                                          "mean": round(mean, 3), "mean_ref": rc["mean_bp"]})
                            if not ok:
                                raise SystemExit(f"再現ゲート不一致: {key} n {n} vs {rc['n']}, "
                                                 f"mean {mean:.3f} vs {rc['mean_bp']}")
        print(f"  {foot:>3}分 完了")

    Path(args.out).write_text(json.dumps({
        "note": "決済ルールのアブレーション。探索区間 2017-2019 のみ。判定・帰無・MDE・経費は無し。",
        "modes": list(MODES), "fixed_h": FIXED_H,
        "reproduction_gate": repro, "cells": cells,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n再現ゲート {sum(r['ok'] for r in repro)}/{len(repro)} 一致。セル {len(cells)} 件 → {args.out}")


if __name__ == "__main__":
    main()
