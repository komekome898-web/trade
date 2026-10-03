#!/usr/bin/env python3
"""カード 9 作り直しの (a) — Binance COIN-M の値段の反応を 1 回で出す(2026-10-03)。

設計: `docs/RESEARCH/cards/c9_liquidation_cascade/REDESIGN_2026-10-03.md` §3.1・§6。
道具: `src/bot/research/liq_cascade_v2.py`(前の道具を import して使う。中身はそちらの docstring)。

**探索であり判定ではない。判定語を書かない。Jev は呼ばない(状態の作り方 `jev_states.jsonl.gz`
まで。呼ぶ前にリードが確かめる)。** 封印の台帳に COIN-M は無い(設計 F-4)。bitFlyer は読まない。

使い方(小さな日数での確かめ):
    PYTHONPATH=src python3 scripts/c9_run_a.py --start 2023-07-01 --end 2023-07-03 \
        --out data/c9_run_a/20230701_03

2 段で走る:
  段 1 = 各日のプリントの直前の状態(材料 15・9)だけを出し、対照 (ii) の帯の境(10 分位)を
         **この走らせのプリント全体**から作る(§6 の 3: 分割しない)。
  段 2 = 日ごとに、プリントの値動き・最大順行/逆行・戻り、束、状態機械、s 秒の曲線、対照 3 種。
1 週の h のため、各日に [前の日, 8 日後] の約定を読む(読んだ日は持ち回す)。
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import random
import resource
import sys
import time
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
REPO_ROOT = _HERE.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from bot.research import liq_cascade_v2 as v2  # noqa: E402

NAN = float("nan")
BANNED_WORDS = ("差あり", "検出されず", "陽性", "陰性", "有意", "支持", "棄却")
FWD_DAYS = 8          # 1 週の h + s の上限 + 遅れ を覆う
POLICY_TYPES = ("A", "B")   # A = 決済、B = ドテン(前の道具の型)
MAIN_GAP = 60


def maxrss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def opened_days() -> set:
    """9 月に開いた印(`o3c_reaction.SAMPLE_DAYS` と `SCALE12_JUDGMENT_DAYS_OPENED`)。"""
    rx = v2._load_script("o3c_reaction")
    return set(rx.SAMPLE_DAYS) | set(rx.SCALE12_JUDGMENT_DAYS_OPENED)


def write_csv(path: Path, rows: list[dict], gz: bool = False) -> None:
    if not rows:
        path.write_text("")
        return
    cols = list(rows[0].keys())
    for r in rows[1:]:
        for k in r:
            if k not in cols:
                cols.append(k)
    opener = (lambda p: gzip.open(p, "wt", encoding="utf-8", newline="")) if gz else \
        (lambda p: open(p, "w", encoding="utf-8", newline=""))
    with opener(path) as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: _fmt(r.get(k)) for k in cols})


def _fmt(x):
    if isinstance(x, float):
        if x != x:
            return ""
        return f"{x:.6g}"
    return x


def window_days(day: str, back: int = 1, fwd: int = FWD_DAYS) -> list[str]:
    d = date.fromisoformat(day)
    return [(d + timedelta(days=k)).isoformat() for k in range(-back, fwd + 1)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--data-root", default=str(v2.DEFAULT_DATA_ROOT))
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=v2.SEED)
    args = ap.parse_args(argv)

    t_all = time.time()
    timing: dict = {}
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    days = v2.day_range(start, end)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    data_root = Path(args.data_root)
    rng = random.Random(args.seed)

    # ---- 清算(前後 1 日を足して読む: 直前 60 秒・次の同じ側・日をまたぐ束のため) ----
    t = time.time()
    pr = v2.load_prints(data_root, start - timedelta(days=1), end + timedelta(days=1))
    data_end_ms = v2.day_start_ms((end + timedelta(days=1)).isoformat()) + v2.MS_DAY
    pday = pr.day
    psign = pr.sign
    ctx = v2.same_side_context(pr)
    bund = {g: v2.same_side_bundles(pr, g) for g in v2.GAPS_S}
    liq_ts = pr.ts.copy()
    in_run = np.isin(pday, np.array(days, dtype=object))
    opened = opened_days()
    timing["清算の読み込みと束"] = time.time() - t
    print(f"[c9a] プリント {len(pr)}(走らせの日 {int(in_run.sum())})"
          f" 一意化 {pr.stats.n_in}→{pr.stats.n_out}", flush=True)

    store = v2.TradeStore(data_root)

    # ---- 段 1: プリントの直前の状態(対照 (ii) の帯の境のため) ----
    t = time.time()
    pre_all = {k: np.full(len(pr), NAN) for k in
               ("p_pre", "raw_m10", "raw_m60", "mat15", "imb5", "dir10", "mat9")}
    for day in days:
        sel = np.flatnonzero(in_run & (pday == day))
        tr, _miss = store.window(window_days(day, 1, 0))
        pre = v2.pre_state_arrays(tr, pr.ts[sel])
        for k in pre_all:
            pre_all[k][sel] = pre[k]
        store.drop_before(window_days(day, 1, 0)[0])
    cuts15 = v2.decile_cuts(pre_all["mat15"][in_run])
    cuts9 = v2.decile_cuts(pre_all["mat9"][in_run])
    timing["段1 直前の状態"] = time.time() - t
    store.cache.clear()

    # ---- 段 2 ----
    print_rows: list[dict] = []
    jev_rows: list[dict] = []
    bundle_rows: list[dict] = []
    cas_rows: list[dict] = []
    leg_rows: list[dict] = []
    act_counts: Counter = Counter()
    judge_counts: Counter = Counter()
    ctrl_rows: list[dict] = []
    ctrl_meta = defaultdict(lambda: [0, 0])   # 種 -> [取れた, 求めた]
    # s 秒の曲線: 日ごとに (s int16, 日の番号 int16, 値 float32 の行列〈列 = (d, h)〉) を持つ。
    # 値ごとに日の文字列を持つと全期間で数 GB になるため。
    sc_cols = [(dly, h) for dly in v2.DELAYS_S for h in v2.HORIZONS_S]
    scurve_parts: list = []
    missing_trade_days: set = set()
    t2 = time.time()
    t_sim = t_rx = t_ctrl = t_sc = 0.0
    for day in days:
        wd = window_days(day)
        tr, miss = store.window(wd)
        missing_trade_days.update(miss)
        sel = np.flatnonzero(in_run & (pday == day))
        ts_sel = pr.ts[sel]

        # 値動き(プリント)
        tt = time.time()
        rx = v2.reactions_from_anchor(tr, ts_sel, psign[sel])
        t_rx += time.time() - tt
        for r, i in enumerate(sel.tolist()):
            row = {
                "print_id": pr.print_id[i], "day": day, "ts_ms": int(pr.ts[i]),
                "side": pr.side[i], "sign": psign[i], "qty": pr.qty[i],
                "orig_qty": pr.orig_qty[i], "avg_price": pr.price[i],
                "before_seal": int(date.fromisoformat(day) < v2.SEAL_BOUNDARY),
                "opened_before": int(day in opened),
                "n_prev60": ctx["n_prev60"][i], "elapsed_prev_s": ctx["elapsed_prev_s"][i],
                "qty_ratio_prev": ctx["qty_ratio_prev"][i],
                "qty_ratio_max60": ctx["qty_ratio_max60"][i],
                "m10_signed": psign[i] * pre_all["raw_m10"][i],
                "m60_signed": psign[i] * pre_all["raw_m60"][i],
                "mat15": pre_all["mat15"][i], "mat9": pre_all["mat9"][i],
                "imb5": pre_all["imb5"][i],
                "gap_next_same_s": (ctx["gap_next_ms"][i] / 1000.0
                                    if np.isfinite(ctx["gap_next_ms"][i]) else NAN),
            }
            for X in v2.GAPS_S:   # ラベル(1): 同じ側の次が X 秒以内(事後)
                row[f"cont_{X}"] = int(ctx["gap_next_ms"][i] <= X * 1000)
            for g in v2.GAPS_S:
                b = bund[g]
                row[f"g{g}_bundle"] = b["bundle_id"][i]
                row[f"g{g}_k"] = int(b["k_in_bundle"][i])
                row[f"g{g}_n_post"] = int(b["n_in_bundle"][i])     # 事後
                row[f"g{g}_pos_post"] = b["pos_label"][i]          # 事後
                row[f"g{g}_qty_so_far"] = float(b["qty_so_far"][i])
            row["t0_ms"] = int(rx["t0_ms"][r])
            row["p0"] = float(rx["p0"][r])
            row["p0_lag_ms"] = int(rx["p0_lag_ms"][r])
            for h in v2.HORIZONS_S:
                for k in ("react", "mfe", "mae", "giveback"):
                    row[f"{k}_{h}"] = float(rx[f"{k}_{h}"][r])
            print_rows.append(row)
            jev_rows.append({"print_id": pr.print_id[i],
                             "state": v2.jev_state_raw(i, pr, ctx, pre_all, bund[MAIN_GAP], tr)})

        # 束と状態機械(束の最初のプリントがこの日)
        tt = time.time()
        price_fn = v2.make_price_fn(tr)
        for g in v2.GAPS_S:
            for b in bund[g]["bundles"]:
                if v2.day_of_ms(b["start_ms"]) != day:
                    continue
                bundle_rows.append({k: b[k] for k in ("bundle_id", "side", "gap_s", "start_ms",
                                                      "end_ms", "n_prints", "qty_total")}
                                   | {"day": day, "dur_s": (b["end_ms"] - b["start_ms"]) / 1000})
                for dly in v2.DELAYS_S:
                    runs = []
                    for pol in v2.JUDGED_POLICIES:
                        jd = v2.judgments_for(pol, b["members"], ctx)
                        for typ in POLICY_TYPES:
                            res = v2.simulate_bundle(pr, b, jd, typ, dly, price_fn)
                            runs.append((pol, typ, res))
                            for p in res["path"]:
                                act_counts[(g, dly, pol, typ, p["行動"])] += 1
                                judge_counts[(g, dly, pol, typ, p["判断"])] += 1
                    for pol, direction in v2.BASELINE_POLICIES.items():
                        res = v2.simulate_bundle(pr, b, None, "-", dly, price_fn,
                                                 baseline=direction)
                        if not res["missing"]:
                            pnl = res["pnl_bp"]
                            res["legs"] = [{"位置": 0, "向き": direction, "出口の理由": "連鎖の終わり",
                                            "レグ損益_bp": pnl, "保有秒": res["hold_seconds"]}]
                        else:
                            res["legs"] = []
                        runs.append((pol, "-", res))
                    for pol, typ, res in runs:
                        cas_rows.append({
                            "bundle_id": b["bundle_id"], "day": day, "side": b["side"],
                            "gap_s": g, "delay_s": dly, "policy": pol, "type": typ,
                            "n_prints": b["n_prints"], "qty_total": b["qty_total"],
                            "pnl_bp": res["pnl_bp"], "entered": int(bool(res["entered"])),
                            "n_entries": res["n_entries"], "hold_s": res["hold_seconds"],
                            "missing": int(bool(res["missing"])),
                            "first_entry_pos": res.get("first_entry_pos")})
                        for lg in res["legs"]:
                            leg_rows.append({
                                "bundle_id": b["bundle_id"], "day": day, "gap_s": g,
                                "delay_s": dly, "policy": pol, "type": typ,
                                "leg_pos": lg["位置"], "leg_dir": lg["向き"],
                                "exit_reason": lg["出口の理由"], "pnl_bp": lg["レグ損益_bp"],
                                "hold_s": lg["保有秒"]})
        t_sim += time.time() - tt

        # s 秒の曲線
        tt = time.time()
        rows_i, ss = v2.s_curve_points(ts_sel, ctx["gap_next_ms"][sel], data_end_ms)
        mat = np.empty((ss.size, len(sc_cols)), dtype=np.float32)
        for dly in v2.DELAYS_S:
            vals = v2.s_curve_values(tr, ts_sel, psign[sel], rows_i, ss, dly, v2.HORIZONS_S)
            for h, vv in vals.items():
                mat[:, sc_cols.index((dly, h))] = vv
        scurve_parts.append((ss.astype(np.int16), np.full(ss.size, days.index(day), np.int16),
                             mat))
        t_sc += time.time() - tt

        # 対照
        tt = time.time()
        # (i) 無作為
        tc = v2.control_random(day, sel.size, liq_ts, rng)
        ctrl_meta["(i)無作為"][0] += int(tc.size)
        ctrl_meta["(i)無作為"][1] += int(sel.size)
        if tc.size:
            pre_c = v2.pre_state_arrays(tr, tc)
            rxc = v2.reactions_from_anchor(tr, tc, pre_c["dir10"])
            ctrl_rows += _ctrl_rows("(i)無作為", day, tc, pre_c["dir10"], rxc, [""] * tc.size)
        # (ii) 勢いと成行の偏りを合わせた時刻
        d0 = v2.day_start_ms(day)
        grid = d0 + np.arange(v2.MS_DAY // v2.CTRL_GRID_MS, dtype=np.int64) * v2.CTRL_GRID_MS
        pre_g = v2.pre_state_arrays(tr, grid)
        okg = v2.no_liq_mask(grid, liq_ts, v2.CTRL2_NO_LIQ_MS) & \
            np.isfinite(pre_g["mat15"]) & np.isfinite(pre_g["mat9"])
        cidx = np.flatnonzero(okg)
        pick = v2.control_matched(pre_all["mat15"][sel], pre_all["mat9"][sel], grid[cidx],
                                  pre_g["mat15"][cidx], pre_g["mat9"][cidx], cuts15, cuts9)
        got = pick >= 0
        ctrl_meta["(ii)合わせた時刻"][0] += int(got.sum())
        ctrl_meta["(ii)合わせた時刻"][1] += int(sel.size)
        if got.any():
            gi = cidx[pick[got]]
            t2c = grid[gi]
            rx2 = v2.reactions_from_anchor(tr, t2c, pre_g["dir10"][gi])
            ctrl_rows += _ctrl_rows("(ii)合わせた時刻", day, t2c, pre_g["dir10"][gi], rx2,
                                    pr.print_id[sel][got].tolist())
        # (iii) プラセボ(束ごと、g ごと)
        for g in v2.GAPS_S:
            bl = [b for b in bund[g]["bundles"] if v2.day_of_ms(b["start_ms"]) == day]
            pl = v2.control_placebo(day, tr, bl, liq_ts, rng)
            key = f"(iii)プラセボ_g{g}"
            ctrl_meta[key][0] += len(pl)
            ctrl_meta[key][1] += len(bl)
            if pl:
                ta = np.array([p["end_ms"] for p in pl], dtype=np.int64)
                dr = np.array([p["dir"] for p in pl], dtype=float)
                rx3 = v2.reactions_from_anchor(tr, ta, dr)
                ctrl_rows += _ctrl_rows(key, day, ta, dr, rx3, [p["bundle_id"] for p in pl],
                                        extra=[{"vol_bundle": p["vol_bundle"],
                                                "vol_placebo": p["vol_placebo"],
                                                "win_start_ms": p["start_ms"]} for p in pl])
        t_ctrl += time.time() - tt
        store.drop_before(window_days(day)[1])   # 次の日の窓の最初(= この日)より前を捨てる
        print(f"[c9a] {day} プリント {sel.size} 経過 {time.time() - t_all:.1f}s "
              f"maxrss {maxrss_mb():.0f}MB", flush=True)
    timing["段2 合計"] = time.time() - t2
    timing["段2 値動き(プリント)"] = t_rx
    timing["段2 状態機械"] = t_sim
    timing["段2 s 秒の曲線"] = t_sc
    timing["段2 対照"] = t_ctrl

    # ---- 集計 ----
    t = time.time()
    tables = aggregate(print_rows, cas_rows, leg_rows, ctrl_rows, scurve_parts, sc_cols, days)
    timing["集計"] = time.time() - t

    # ---- 書き出し ----
    t = time.time()
    write_csv(out / "anchors_prints.csv.gz", print_rows, gz=True)
    write_csv(out / "anchors_bundles.csv.gz", bundle_rows, gz=True)
    write_csv(out / "policy_cascades.csv.gz", cas_rows, gz=True)
    write_csv(out / "policy_legs.csv.gz", leg_rows, gz=True)
    write_csv(out / "controls.csv.gz", ctrl_rows, gz=True)
    for name, rows in tables.items():
        write_csv(out / f"{name}.csv", rows)
    write_csv(out / "policy_action_counts.csv",
              [{"gap_s": k[0], "delay_s": k[1], "policy": k[2], "type": k[3], "行動": k[4],
                "件数": v} for k, v in sorted(act_counts.items(), key=lambda x: str(x[0]))])
    write_csv(out / "policy_judge_counts.csv",
              [{"gap_s": k[0], "delay_s": k[1], "policy": k[2], "type": k[3], "判断": k[4],
                "件数": v} for k, v in sorted(judge_counts.items(), key=lambda x: str(x[0]))])
    v2.write_jsonl_gz(out / "jev_states.jsonl.gz", jev_rows)
    timing["書き出し"] = time.time() - t
    timing["全体"] = time.time() - t_all
    meta = {
        "設計": "docs/RESEARCH/cards/c9_liquidation_cascade/REDESIGN_2026-10-03.md",
        "期間": [args.start, args.end], "日数": len(days),
        "一意化": {"生の行": pr.stats.n_in, "一意": pr.stats.n_out,
                 "多重度": {str(k): v for k, v in pr.stats.multiplicity.items()},
                 "注": "前後 1 日を足して読んだ範囲の数"},
        "走らせの日のプリント": int(in_run.sum()),
        "束の数": {str(g): sum(1 for b in bund[g]["bundles"]
                              if v2.day_of_ms(b["start_ms"]) in set(days))
                  for g in v2.GAPS_S},
        "約定の欠けた日(窓の中)": sorted(missing_trade_days),
        "読んだ約定の日": sorted(set(store.days_read)),
        "対照の取れた数": {k: {"取れた": v[0], "求めた": v[1]} for k, v in ctrl_meta.items()},
        "対照(ii)の帯の境": {"mat15": cuts15.tolist(), "mat9": cuts9.tolist(),
                         "注": "この走らせのプリントから(分割しない、設計 §6 の 3)"},
        "所要_秒": {k: round(v, 2) for k, v in timing.items()},
        "最大メモリ_MB(ru_maxrss)": round(maxrss_mb(), 1),
        "固定値": {"HORIZONS_S": v2.HORIZONS_S, "GAPS_S": v2.GAPS_S, "DELAYS_S": v2.DELAYS_S,
                 "S_MAX": v2.S_MAX, "STALENESS_MS": v2.STALENESS_MS, "seed": args.seed},
        "Jev": "呼んでいない(jev_states.jsonl.gz に状態だけ)",
    }
    (out / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    for p in out.glob("*.csv"):
        txt = p.read_text(encoding="utf-8")
        hit = [w for w in BANNED_WORDS if w in txt]
        if hit:
            raise SystemExit(f"[止め] 判定語が出力に混ざっている({p.name}): {hit}")
    print(json.dumps({"所要_秒": meta["所要_秒"], "最大メモリ_MB": meta["最大メモリ_MB(ru_maxrss)"],
                      "対照": meta["対照の取れた数"], "束": meta["束の数"]},
                     ensure_ascii=False), flush=True)
    return 0


def _ctrl_rows(kind, day, t_arr, dir_arr, rx, ref_ids, extra=None) -> list[dict]:
    rows = []
    for r in range(len(t_arr)):
        row = {"kind": kind, "day": day, "anchor_ms": int(t_arr[r]), "dir": float(dir_arr[r]),
               "ref_id": ref_ids[r], "t0_ms": int(rx["t0_ms"][r]), "p0": float(rx["p0"][r])}
        if extra:
            row.update(extra[r])
        for h in v2.HORIZONS_S:
            for k in ("react", "mfe", "mae", "giveback"):
                row[f"{k}_{h}"] = float(rx[f"{k}_{h}"][r])
        rows.append(row)
    return rows


def _col(rows, key):
    return np.array([r.get(key, NAN) if r.get(key) is not None else NAN for r in rows],
                    dtype=float)


def aggregate(print_rows, cas_rows, leg_rows, ctrl_rows, scurve_parts, sc_cols, days) -> dict:
    """分布の表を作る(平均だけの行は作らない)。"""
    metrics = ("react", "mfe", "mae", "giveback")
    pdays = np.array([r["day"] for r in print_rows], dtype=object)

    # 1) 値動きの分布: 実(全体・側・位置〈事後〉)と対照 3 種
    reaction = []

    def add(group, rows, days, mask=None):
        for h in v2.HORIZONS_S:
            for k in metrics:
                vals = _col(rows, f"{k}_{h}")
                dd = days
                if mask is not None:
                    vals, dd = vals[mask], days[mask]
                reaction.append({"群": group, "h_s": h, "量": k} | v2.dist_stats(vals, dd))

    add("実_全プリント", print_rows, pdays)
    sides = np.array([r["side"] for r in print_rows], dtype=object)
    for s in ("SELL", "BUY"):
        add(f"実_側{s}", print_rows, pdays, sides == s)
    for g in v2.GAPS_S:
        pos = np.array([r[f"g{g}_pos_post"] for r in print_rows], dtype=object)
        for lab in ("単発", "最初", "途中", "最後"):
            add(f"実_g{g}_位置{lab}(事後)", print_rows, pdays, pos == lab)
    kinds = sorted({r["kind"] for r in ctrl_rows})
    cdays = np.array([r["day"] for r in ctrl_rows], dtype=object)
    ckind = np.array([r["kind"] for r in ctrl_rows], dtype=object)
    for kd in kinds:
        add(f"対照{kd}", ctrl_rows, cdays, ckind == kd)

    # 2) 清算の量の 3 分位(§9-4)。境はこの走らせのプリントから
    size_split = []
    split_cols = [("qty", "1件の数量"), ("qty_ratio_max60", "直前60秒の最大との比")] + \
        [(f"g{g}_qty_so_far", f"g{g}_連鎖のここまでの数量") for g in v2.GAPS_S]
    for col, name in split_cols:
        x = _col(print_rows, col)
        cuts = v2.tertile_cuts(x)
        if cuts.size < 2:
            continue
        b = np.where(np.isfinite(x), np.searchsorted(cuts, x, side="right"), -1)
        for t_ in range(3):
            m = b == t_
            for h in v2.HORIZONS_S:
                for k in ("react", "mfe", "mae"):
                    vals = _col(print_rows, f"{k}_{h}")[m]
                    size_split.append({"分け": name, "3分位": t_ + 1,
                                       "境": "|".join(f"{c:.6g}" for c in cuts),
                                       "h_s": h, "量": k} | v2.dist_stats(vals, pdays[m]))

    # 3) 状態機械: 連鎖 1 本ごと(入らなかった連鎖を 0 で含める / 含めない)と 1 レグごと
    policy = []
    keyf = lambda r: (r["gap_s"], r["delay_s"], r["policy"], r["type"])  # noqa: E731
    groups = defaultdict(list)
    for r in cas_rows:
        groups[keyf(r)].append(r)
    lgroups = defaultdict(list)
    for r in leg_rows:
        lgroups[keyf(r)].append(r)
    for key in sorted(groups, key=str):
        rows = groups[key]
        g, dly, pol, typ = key
        days_ = np.array([r["day"] for r in rows], dtype=object)
        pnl = _col(rows, "pnl_bp")
        ent = np.array([r["entered"] for r in rows], dtype=bool)
        miss = np.array([r["missing"] for r in rows], dtype=bool)
        base = {"gap_s": g, "delay_s": dly, "policy": pol, "type": typ,
                "連鎖の数": len(rows), "入った連鎖": int(ent.sum()), "値の欠け": int(miss.sum())}
        incl = np.where(ent, pnl, np.where(miss, NAN, 0.0))
        policy.append(base | {"単位": "連鎖1本(入らないを0で含める)"} | v2.dist_stats(incl, days_))
        policy.append(base | {"単位": "連鎖1本(入った連鎖だけ)"} |
                      v2.dist_stats(pnl[ent], days_[ent]))
        lr = lgroups.get(key, [])
        policy.append(base | {"単位": "1レグ"} |
                      v2.dist_stats(_col(lr, "pnl_bp"),
                                    np.array([r["day"] for r in lr], dtype=object)))
        # 束の総量の 3 分位(事後)
        q = _col(rows, "qty_total")
        cuts = v2.tertile_cuts(q)
        if cuts.size == 2:
            bq = np.searchsorted(cuts, q, side="right")
            for t_ in range(3):
                m = bq == t_
                policy.append(base | {"単位": f"連鎖1本(入らないを0)_束の総量3分位{t_ + 1}(事後)"} |
                              v2.dist_stats(incl[m], days_[m]))

    # 4) s 秒の曲線
    scurve = []
    if scurve_parts:
        s_all = np.concatenate([p[0] for p in scurve_parts]).astype(np.int64)
        order = np.argsort(s_all, kind="stable")
        s_all = s_all[order]
        d_all = np.array(days, dtype=object)[
            np.concatenate([p[1] for p in scurve_parts]).astype(np.int64)[order]]
        m_all = np.concatenate([p[2] for p in scurve_parts], axis=0)[order]
        bounds = np.searchsorted(s_all, np.arange(1, v2.S_MAX + 2))
        for c, (dly, h) in enumerate(sc_cols):
            v_all = m_all[:, c].astype(float)
            for s in range(1, v2.S_MAX + 1):
                a, b = bounds[s - 1], bounds[s]
                scurve.append({"s": s, "delay_s": dly, "h_s": h, "向き": "fade(建玉の向き)"} |
                              v2.dist_stats(v_all[a:b], d_all[a:b]))

    # 5) ラベル(続く)の件数
    labels = []
    for X in v2.GAPS_S:
        c = _col(print_rows, f"cont_{X}")
        labels.append({"X_s": X, "プリント": int(c.size), "続く(同じ側の次がX秒以内)": int(np.nansum(c)),
                       "割合": float(np.nanmean(c)) if c.size else NAN})
    return {"dist_reaction": reaction, "dist_size_split": size_split, "dist_policy": policy,
            "dist_s_curve": scurve, "label_counts": labels}


if __name__ == "__main__":
    raise SystemExit(main())
