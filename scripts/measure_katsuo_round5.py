"""第 5 周 — (a') 出口の遅れを決済理由別に分ける / (c)-iii 「強い」の残りの負を層別で探す
(`docs/PHASE2/K1/ROUND5_PREREG.md`、L-080)。

**新しい機構仮説ではない。理解の続き。機構は 1 つも変えていない。** 帰無・MDE・判定バーは作らない。
経費は引かない。封印(BitMEX 2020-2021)は開けない。1 回の実行でデータを 1 回だけ読み、
フラグに応じて (a') と (c)-iii の**両方**を出す(同じ `seconds` を使い回す)。

## (a') — `round5_exit_reason{tag}.json`(`tag` は第 13 部と同じ: `""` = 原典 / `"_flip_noinval"` = H1+H2a)

第 13 部と同じ取引・同じ 4 通りの値付け(`measure_katsuo_delay_decomp.reprice`)を、
決済理由 {`invalidated`, `opposite_weak`, `reversed`} で分ける。234 セル(足 6 × 門 13 × 強さ 3)。
**再現ゲート**: 理由別の (n × 分解量) の和 / n 全体が、既存の `delay_decomp{tag}.json` の
`decomp_bp` と 1e-3 で一致すること(全セル)。`--flip-body` 単独(H1 だけ)はこの出力を出さない
(事前登録どおり、土台は原典 / H1+H2a の 2 つだけ)。

## (c)-iii — `round5_residual_strong{tag2}.json`(`--flip-body` を立てたときだけ。
`tag2` = `"_flipbody"`(H1 のみ)/ `"_flip_noinval"`(H1+H2a))

対象は H1 の後に「強い」に残る足(ヒゲ > 実体)。門は `s19/b24` のみ、足 6、`keep="strong"`。
層: 向き・ヒゲ/実体比 r=w/|実体|・ヒゲ長・局所ボラ三分位(直前 100 本、全期間、
`measure_katsuo_robustness.FootData.vol_prev` を import して再利用)・年・保有・決済理由。
経路: 入口足の終値から h ∈ {1,2,3,5,10,20,50} 本後の終値まで(決済を無視して持ち続けた場合)。

    PYTHONPATH=src:scripts python scripts/measure_katsuo_round5.py --source binance [--flip-body] [--no-invalidation]
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

import numpy as np

import k1_source
import measure_katsuo_delay_decomp as dec
import measure_katsuo_dispersion as base
import measure_katsuo_effect as eff
import measure_katsuo_robustness as rob

REPO = Path(__file__).resolve().parents[1]

GATE = (19.0, 24.0)
GATE_LABEL = eff.label(GATE)                       # "s19/b24"
SEAL_END = date(2019, 12, 31)                        # BitMEX の封印

REASONS3 = ("invalidated", "opposite_weak", "reversed")
PATH_H = (1, 2, 3, 5, 10, 20, 50)

# ヒゲ/実体比 r = w / |実体|(w = 勝った側のヒゲ)。事前登録のビン (1,1.5],(1.5,2],(2,3],(3,+)。実体 0 は最後のビン
RATIO_LABELS = ("(1,1.5]", "(1.5,2]", "(2,3]", "(3,+)")
# ヒゲ長 bp。事前登録は [24,40),[40,80),[80,+) の 3 つだが、門 s19/b24 は小門(w>=19 かつ w>実体)の枝
# だけでも通るので、残った「強い」に 19〜24bp の足が混ざりうる(大門 b24 の枝だけを通るとは限らない)。
# **事前登録どおりの 3 ビンでは母集団を覆いきれない**ので [19,24) を別ビンとして残す(取りこぼさない)
WICK_LABELS = ("[19,24)", "[24,40)", "[40,80)", "[80,+)")
HOLD_LABELS = ("[1,3)", "[3,10)", "[10,30)", "[30,+)")


def ratio_bin_of(wbp: float, bodybp: float) -> str:
    if bodybp <= 0:
        return "(3,+)"
    r = wbp / bodybp
    if r <= 1.5:
        return "(1,1.5]"
    if r <= 2.0:
        return "(1.5,2]"
    if r <= 3.0:
        return "(2,3]"
    return "(3,+)"


def wick_bin_of(wbp: float) -> str:
    if wbp < 24.0:
        return "[19,24)"
    if wbp < 40.0:
        return "[24,40)"
    if wbp < 80.0:
        return "[40,80)"
    return "[80,+)"


def hold_bin_of(hold: int) -> str:
    if hold < 3:
        return "[1,3)"
    if hold < 10:
        return "[3,10)"
    if hold < 30:
        return "[10,30)"
    return "[30,+)"


def vol_tercile_of(v: float, edges) -> str:
    q1, q2 = edges
    if v < q1:
        return "low"
    if v < q2:
        return "mid"
    return "high"


def path_return(close, pos: int, i: int, h: int) -> float:
    """入口足 `i` の終値から `h` 本後の終値までの符号付きリターン(bp)。決済を無視する。"""
    return pos * (close[i + h] / close[i] - 1.0) * 1e4


# ---------------------------------------------------------------- (a') 決済理由別の分解


def split_by_reason(arms: dict, years) -> dict:
    """`reprice()` の 4 腕を決済理由で分け、理由ごとに n・EE 平均・入口/出口の遅れ・年別を出す。"""
    n = len(arms["EE"])
    idx_by_reason: dict[str, list[int]] = {}
    for k in range(n):
        why = arms["EE"][k][3]
        idx_by_reason.setdefault(why, []).append(k)
    out = {}
    for why, idxs in idx_by_reason.items():
        ee = [arms["EE"][k][1] for k in idxs]
        de = [arms["DE"][k][1] for k in idxs]
        ed = [arms["ED"][k][1] for k in idxs]
        nr = len(idxs)
        entry_delay = sum(d - e for e, d in zip(ee, de)) / nr
        exit_delay = sum(d - e for e, d in zip(ee, ed)) / nr
        yrs = [years[arms["EE"][k][0]] for k in idxs]
        per_year = {}
        for y in sorted(set(yrs)):
            sel = [k for k, yy in zip(idxs, yrs) if yy == y]
            eey = [arms["EE"][k][1] for k in sel]
            dey = [arms["DE"][k][1] for k in sel]
            edy = [arms["ED"][k][1] for k in sel]
            per_year[str(y)] = {"n": len(sel), "ee_mean_bp": round(sum(eey) / len(sel), 3),
                                 "de_mean_bp": round(sum(dey) / len(sel), 3),
                                 "ed_mean_bp": round(sum(edy) / len(sel), 3)}
        out[why] = {"n": nr, "ee_mean_bp": round(sum(ee) / nr, 3),
                    "entry_delay_bp": round(entry_delay, 3), "exit_delay_bp": round(exit_delay, 3),
                    "entry_delay_exact": entry_delay, "exit_delay_exact": exit_delay,
                    "per_year": per_year}
    return out


def run_exit_reason(args, seconds, tag: str, use_invalid: bool, start, end) -> None:
    ref_path = k1_source.out_dir(args.source) / f"delay_decomp{tag}.json"
    if not ref_path.exists():
        raise SystemExit(f"再現ゲートの参照が無い: {ref_path}(先に measure_katsuo_delay_decomp.py を実行)")
    ref = json.loads(ref_path.read_text("utf-8"))["cells"]

    gs = eff.gates()
    cells: dict = {}
    repro: list = []
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
                arms, dropped, zero_de = dec.reprice(bars, sg, tr)
                n = len(arms["EE"])
                reasons = split_by_reason(arms, years)

                # 再現ゲート: 理由別 (n × 量) の重み付き和(丸め前)が第 13 部の分解量と 1e-3 で一致
                w_entry = sum(v["n"] * v["entry_delay_exact"] for v in reasons.values()) / n
                w_exit = sum(v["n"] * v["exit_delay_exact"] for v in reasons.values()) / n
                rc = ref.get(key, {})
                rc_decomp = rc.get("decomp_bp")
                ok = None
                if rc_decomp is not None:
                    ok = (rc.get("n") == n and abs(w_entry - rc_decomp["entry_delay"]) < 1e-3
                          and abs(w_exit - rc_decomp["exit_delay"]) < 1e-3)
                    repro.append({"key": key, "ok": ok, "n_mine": n, "n_ref": rc.get("n"),
                                  "entry_weighted": round(w_entry, 3), "entry_ref": rc_decomp["entry_delay"],
                                  "exit_weighted": round(w_exit, 3), "exit_ref": rc_decomp["exit_delay"]})
                    if not ok:
                        raise SystemExit(f"再現ゲート不一致(理由別の和 vs 第13部の分解量): {key} {repro[-1]}")

                for v in reasons.values():
                    del v["entry_delay_exact"], v["exit_delay_exact"]

                cells[key] = {"foot": foot, "gate": eff.label(g), "strength": keep, "n": n,
                              "dropped_end": dropped, "de_zero_length": zero_de,
                              "decomp_bp": {"entry_delay": round(w_entry, 3), "exit_delay": round(w_exit, 3)},
                              "reasons": reasons}
        ok_n = sum(1 for r in repro if r["ok"])
        print(f"  {foot:>3}分 完了(理由別)。再現ゲート累計 {ok_n}/{len(repro)}", flush=True)

    out_path = k1_source.out_dir(args.source) / f"round5_exit_reason{tag}.json"
    Path(out_path).write_text(json.dumps({
        "note": ("(a') 第 13 部と同じ取引・同じ 4 腕(EE/DE/ED/DD)を決済理由 "
                 "{invalidated, opposite_weak, reversed} で分けた。機構は変えていない。"
                 "帰無・MDE・判定バーは作っていない。経費は引いていない。"),
        "explore": [start.isoformat(), end.isoformat()],
        "source": args.source, "load": k1_source.last_load,
        "flip_body": args.flip_body, "use_invalid": use_invalid, "tag": tag,
        "reproduction_gate": repro,
        "bootstrap_reps": dec.BOOTSTRAP, "seed": "sha256(cell|arm)(第13部と同一取引の再集計。区間は出さない)",
        "family": {"feet": list(args.feet), "gates": [eff.label(g) for g in gs], "strengths": list(eff.STRENGTHS)},
        "reasons_family": list(REASONS3),
        "cells": cells,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    ok_n = sum(1 for r in repro if r["ok"])
    print(f"再現ゲート(理由別の和 vs 第13部の分解量) {ok_n}/{len(repro)} 一致")
    print(f"(a') セル {len(cells)} 件 → {out_path}")


# ---------------------------------------------------------------- (c)-iii 残りの「強い」の層別


def run_residual_strong(args, seconds, tag2: str, use_invalid: bool, start, end) -> None:
    cells: dict = {}
    for foot in args.feet:
        bars = base.fold(seconds, foot)
        ts = [b[0] for b in bars]
        close = [b[4] for b in bars]
        n_bars = len(bars)
        years = [datetime.utcfromtimestamp(t).year for t in ts]
        fd = rob.FootData(bars)                     # D6/D8 の局所ボラ・ヒゲ長・実体長を再利用(import のみ)

        sig = eff.signals(bars, GATE[0], GATE[1], flip_body=True)
        idx_all = [i for i, x in enumerate(sig) if x[0] != 0]
        vol_all = np.array([fd.vol_prev[i] for i in idx_all], dtype=np.float64)
        vol_all = vol_all[~np.isnan(vol_all)]
        edges = (float(np.quantile(vol_all, 1 / 3)), float(np.quantile(vol_all, 2 / 3))) if vol_all.size else None

        trades = eff.simulate(bars, sig, "strong", use_invalid=use_invalid)
        if len(trades) < 30:
            continue
        for i, _r, _h, _w in trades:
            assert sig[i][3] == "strong" and int(fd.shape_sig[i]) == sig[i][0], \
                "残った「強い」は反転していない足のはず"

        key = f"{foot}|{GATE_LABEL}|strong"
        cell: dict = {"foot": foot, "gate": GATE_LABEL, "strength": "strong", "n": len(trades),
                      "vol_edges": [round(edges[0], 3), round(edges[1], 3)] if edges else None,
                      "vol_edge_population_n": len(idx_all), "vol_edge_population_no_vol_n":
                          int(len(idx_all) - vol_all.size)}
        cell["mechanism"] = dec.summarize(trades, years, ts, f"{key}|mechanism")

        # 経路の h=保有 での値は機構のリターンと恒等(決済は終値なので)。全取引で確認する
        hold_check_max = 0.0
        hold_check_n = 0
        for i, r, hold, _w in trades:
            if i + hold < n_bars:
                pr = path_return(close, sig[i][0], i, hold)
                hold_check_max = max(hold_check_max, abs(pr - r))
                hold_check_n += 1
        if hold_check_max > 1e-6:
            raise SystemExit(f"経路 h=保有 が機構のリターンと一致しない: {key} 最大差 {hold_check_max}")
        cell["path_hold_sanity"] = {"n_checked": hold_check_n, "max_abs_diff_bp": round(hold_check_max, 9)}

        layers = {name: {} for name in
                  ("direction", "wick_body_ratio", "wick_length", "local_vol", "year", "hold", "exit_reason")}
        below24 = vol_missing = 0
        for tr in trades:
            i, _r, hold, why = tr
            pos = sig[i][0]
            layers["direction"].setdefault("buy" if pos == 1 else "sell", []).append(tr)
            wbp_i, bodybp_i = float(fd.wbp[i]), float(fd.body_bp[i])
            layers["wick_body_ratio"].setdefault(ratio_bin_of(wbp_i, bodybp_i), []).append(tr)
            wl = wick_bin_of(wbp_i)
            below24 += wl == "[19,24)"
            layers["wick_length"].setdefault(wl, []).append(tr)
            vol_i = float(fd.vol_prev[i])
            if edges is not None and vol_i == vol_i:
                layers["local_vol"].setdefault(vol_tercile_of(vol_i, edges), []).append(tr)
            else:
                vol_missing += 1
            layers["year"].setdefault(str(years[i]), []).append(tr)
            layers["hold"].setdefault(hold_bin_of(hold), []).append(tr)
            layers["exit_reason"].setdefault(why, []).append(tr)

        cell["wick_below_24bp_n"] = below24
        cell["vol_missing_n"] = vol_missing
        cell["layers"] = {}
        for lname, buckets in layers.items():
            out_b = {}
            for blabel, trs in buckets.items():
                rs = [x[1] for x in trs]
                nb = len(rs)
                mean_bp = sum(rs) / nb
                out_b[blabel] = {"n": nb, "mean_bp": round(mean_bp, 3),
                                  "ci95_bp": dec.day_block_ci(trs, ts, f"{key}|{lname}|{blabel}"),
                                  "total_bp": round(mean_bp * nb, 1)}
            cell["layers"][lname] = out_b

        path_overall, path_by_reason, path_by_vol = {}, {r: {} for r in REASONS3}, {"low": {}, "mid": {}, "high": {}}
        for h in PATH_H:
            vals: list = []
            vbr = {r: [] for r in REASONS3}
            vbv = {"low": [], "mid": [], "high": []}
            for i, _r, _hold, why in trades:
                if i + h >= n_bars:
                    continue
                pr = path_return(close, sig[i][0], i, h)
                vals.append(pr)
                if why in vbr:
                    vbr[why].append(pr)
                vol_i = float(fd.vol_prev[i])
                if edges is not None and vol_i == vol_i:
                    vbv[vol_tercile_of(vol_i, edges)].append(pr)
            path_overall[str(h)] = {"n": len(vals), "mean_bp": round(sum(vals) / len(vals), 3) if vals else None}
            for r in REASONS3:
                v = vbr[r]
                path_by_reason[r][str(h)] = {"n": len(v), "mean_bp": round(sum(v) / len(v), 3) if v else None}
            for vt in ("low", "mid", "high"):
                v = vbv[vt]
                path_by_vol[vt][str(h)] = {"n": len(v), "mean_bp": round(sum(v) / len(v), 3) if v else None}
        cell["path"] = {"horizons": list(PATH_H), "overall": path_overall,
                        "by_exit_reason": path_by_reason, "by_local_vol": path_by_vol}

        cells[key] = cell
        print(f"  {foot:>3}分 完了(残りの強い)。n={len(trades):,} vol_edges={cell['vol_edges']}", flush=True)

    out_path = k1_source.out_dir(args.source) / f"round5_residual_strong{tag2}.json"
    Path(out_path).write_text(json.dumps({
        "note": ("(c)-iii H1 の後に「強い」に残る足(ヒゲ > 実体)。門 s19/b24 のみ、keep=strong。"
                 "層: 向き・ヒゲ/実体比・ヒゲ長・局所ボラ三分位(直前100本、全期間、"
                 "measure_katsuo_robustness.FootData.vol_prev を再利用)・年・保有・決済理由。"
                 "経路 = 決済を無視して h 本後の終値まで持ち続けた場合の符号付きリターン。"
                 "機構は変えていない。帰無・MDE・判定バーは作っていない。経費は引いていない。"
                 "ヒゲ長のビンは事前登録の [24,40)/[40,80)/[80,+) に [19,24) を足した"
                 "(門 s19/b24 は小門 w>=19bp の枝だけでも通るため、24bp 未満の「強い」が母集団に残る)。"),
        "explore": [start.isoformat(), end.isoformat()],
        "source": args.source, "load": k1_source.last_load,
        "flip_body": True, "use_invalid": use_invalid, "tag2": tag2,
        "gate": GATE_LABEL, "feet": list(args.feet), "strength": "strong",
        "bootstrap_reps": dec.BOOTSTRAP, "seed": "sha256(cell|layer|bin)",
        "ratio_bins": list(RATIO_LABELS), "wick_bins": list(WICK_LABELS), "hold_bins": list(HOLD_LABELS),
        "path_horizons": list(PATH_H),
        "cells": cells,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"(c)-iii セル {len(cells)} 件 → {out_path}")


# ---------------------------------------------------------------- 本体


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--feet", type=int, nargs="+", default=list(eff.FEET))
    ap.add_argument("--flip-body", action="store_true", help="H1: (a') は土台 H1+H2a、(c)-iii を出す条件")
    ap.add_argument("--no-invalidation", action="store_true", help="H2a")
    k1_source.add_source_args(ap)
    args = ap.parse_args()
    start, end = k1_source.resolve_range(args)
    if args.source == "bitmex":
        # 封印: BitMEX の判定区間 2020-2021 には触れない(既存スクリプトと同じ assert)
        assert end <= SEAL_END, f"BitMEX の封印: end は {SEAL_END} 以下でなければならない ({end})"
    use_invalid = not args.no_invalidation
    tag = {(False, True): "", (True, True): "_flipbody", (False, False): "_noinval", (True, False): "_flip_noinval"}[
        (args.flip_body, use_invalid)]
    want_reason = tag in ("", "_flip_noinval")        # 事前登録: 土台は原典 / H1+H2a の 2 つだけ
    want_residual = args.flip_body                    # (c)-iii は --flip-body のときだけ
    if not want_reason and not want_residual:
        raise SystemExit(f"このフラグの組では出力が無い(tag={tag})。(a') は原典/H1+H2a、"
                          f"(c)-iii は --flip-body のときだけ")

    print(f"{args.source} 区間 {start} 〜 {end}(BitMEX の判定区間 2020-2021 には触れない)。土台 {tag or '原典'}")
    seconds = k1_source.load_bars(args.source, start, end)
    print(f"  バー {len(seconds):,} 行。データは 1 回だけ読み込む(以降は足の畳み込みだけ)")

    if want_reason:
        run_exit_reason(args, seconds, tag, use_invalid, start, end)
    if want_residual:
        run_residual_strong(args, seconds, tag, use_invalid, start, end)


if __name__ == "__main__":
    main()
