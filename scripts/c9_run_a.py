#!/usr/bin/env python3
"""カード 9 作り直しの (a) — Binance COIN-M の値段の反応を 1 回で出す(2026-10-03、第 2 稿)。

設計: `docs/RESEARCH/cards/c9_liquidation_cascade/REDESIGN_2026-10-03.md` §3.1・§6。
道具: `src/bot/research/liq_cascade_v2.py`。使い方・出力の列・既知の限り:
`docs/RESEARCH/cards/c9_liquidation_cascade/README_TOOL_A.md`。

**探索であり判定ではない。判定語を書かない。Jev は呼ばない(状態の作り方 `jev_states.jsonl.gz`
まで)。** 封印の台帳に COIN-M は無い(設計 F-4)。bitFlyer は読まない。

    PYTHONPATH=src python3 scripts/c9_run_a.py --start 2023-07-01 --end 2023-07-03 \
        --out data/c9_run_a/20230701_03

2 段で走る:
  段 1 = 各日のプリントの材料 15・9 だけを出し、対照 (ii) の帯の境(10 分位)を**この走らせの
         プリント全体**から作る(§6 の 3: 分割しない)。`chunks/pre/<日>.npz` に残す。
  段 2 = 日ごとに、材料・値動き・束・状態機械・s 秒の曲線・対照 3 種を出し、**日ごとに
         `chunks/` へ書く**(行をメモリに溜めない。最大メモリが日の数で増えない)。
         `chunks/meta/<日>.json` がある日は `--resume` で飛ばす。
各日に [4 日前, 11 日後] の約定を読む(1 週の h + 対照 (ii) の ±3 日 + その 1 週。読んだ日は持ち回す)。

走らせ直し(2026-10-06、`docs/DISCUSSIONS/2026-10-06_held_batches/DELEGATION_rerun_impl.md` 担当 C):
  `--fill-side quote` = 状態機械(判断の方策と基準の方策)の入りと出を、目標の時刻以前で最新の
  最良気配(成行の買いは売り気配、売りは買い気配。`--quotes-dir` = `scripts/c9_fetch_bookticker.py`
  の出力)で付ける(リードの決め。批評家 1 回目の [止める] を受けた直し)。直前の同じ側の約定 (b)・
  以後で最初の同じ側の約定 (a)・元の付け方は並べる列。元の付け方の行は `chunks/*_any/` にも元と
  同じ列で書く(再現の検め用)。既定 `any` = 元の走らせ(どちらの側の約定でもよい)。`--leg-path` = レグの行に
  入り・出の約定と経路(MFE・MAE)の列を足す。どちらも状態機械の連鎖・レグの行にだけ効き、
  値動き・s 秒の曲線・対照は変えない。中身は `bot.research.liq_cascade_fill` の docstring。
  既定(どちらも付けない)は元のとおり `v2.make_price_fn` → `v2.simulate_bundle` を呼ぶ。
"""
from __future__ import annotations

import argparse
import gzip
import json
import random
import resource
import shutil
import sys
import time
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
REPO_ROOT = _HERE.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from bot.research import liq_cascade_fill as fill  # noqa: E402
from bot.research import liq_cascade_v2 as v2  # noqa: E402

NAN = float("nan")
BANNED_WORDS = ("差あり", "検出されず", "陽性", "陰性", "有意", "支持", "棄却")
BACK_DAYS = 4         # 対照 (ii) の −3 日の格子の直前の状態(前の日)まで
FWD_DAYS = 11         # 対照 (ii) の +3 日 + 1 週の h + s の上限 + 遅れ
PRINT_MARGIN_DAYS = 4  # 清算を前後に足して読む日数(直前 60 秒・次の同じ側・±3 日の無清算の判定)
POLICY_TYPES = ("A", "B")   # A = 決済、B = ドテン(前の道具の型)
MAIN_GAP = 60
FLOAT_FMT = "%.8g"


def maxrss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def opened_days() -> set:
    """9 月に開いた印(`o3c_reaction.SAMPLE_DAYS` と `SCALE12_JUDGMENT_DAYS_OPENED`)。"""
    rx = v2._load_script("o3c_reaction")
    return set(rx.SAMPLE_DAYS) | set(rx.SCALE12_JUDGMENT_DAYS_OPENED)


def shift(day: str, k: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=k)).isoformat()


def window_days(day: str, back: int, fwd: int) -> list[str]:
    return [shift(day, k) for k in range(-back, fwd + 1)]


def write_df(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".part")
    df.to_csv(tmp, index=False, float_format=FLOAT_FMT,
              compression="gzip" if path.suffix == ".gz" else None)
    tmp.replace(path)


def reaction_cols(rx: dict) -> dict:
    return {f"{k}_{h}": rx[f"{k}_{h}"] for h in v2.HORIZONS_S for k in v2.REACTION_KEYS}


def make_sim(pr, tr, price_fn, fill_side: str, leg_path: bool, present_days=None,
             quotes=None):
    """束 1 本を流す関数。既定(`any`・経路なし)は元のとおり `v2.simulate_bundle(…, price_fn)`。
    `quote` のときは `present_days`(約定のファイルがある日)と `quotes`(`fill.QuoteBook`)を使う。"""
    if fill_side == fill.FILL_ANY and not leg_path:
        def sim(b, jd, typ, dly, baseline=None):
            if baseline is None:
                return v2.simulate_bundle(pr, b, jd, typ, dly, price_fn)
            return v2.simulate_bundle(pr, b, jd, typ, dly, price_fn, baseline=baseline)
        return sim
    book = fill.TakerBook(tr, present_days) if fill_side == fill.FILL_QUOTE else None

    def sim(b, jd, typ, dly, baseline=None):
        return fill.simulate(pr, b, jd, typ, dly, tr, fill_side, leg_path,
                             baseline=baseline, book=book, quotes=quotes)
    return sim


def baseline_legs(res: dict, direction: str) -> list:
    """基準の方策のレグ(元の run_day の書き方そのまま)。"""
    return [] if res["missing"] else [
        {"位置": 0, "向き": direction, "出口の理由": "連鎖の終わり",
         "レグ損益_bp": res["pnl_bp"], "保有秒": res["hold_seconds"]}]


def any_rows(res: dict, crow: dict, lbase: dict, direction: str | None):
    """`quote` の走らせで、1 回目(どちらの側でも)の結果から元と同じ列の連鎖の行・レグの行を作る
    (再現の検めは `chunks/*_any/` どうしを元と比べる。主の付け方でレグの数が変わっても落ちない)。"""
    ra = res["res_any"]
    c = dict(crow) | {"pnl_bp": ra["pnl_bp"], "entered": int(bool(ra["entered"])),
                      "n_entries": ra["n_entries"], "hold_s": ra["hold_seconds"],
                      "missing": int(bool(ra["missing"])),
                      "first_entry_pos": ra.get("first_entry_pos")}
    legs = baseline_legs(ra, direction) if direction is not None else ra["legs"]
    ls = [dict(lbase) | {"leg_pos": lg["位置"], "leg_dir": lg["向き"],
                         "exit_reason": lg["出口の理由"], "pnl_bp": lg["レグ損益_bp"],
                         "hold_s": lg["保有秒"]} for lg in legs]
    return c, ls


def stage3_window(day: str, fill_side: str) -> list[str]:
    """段 3 の約定の窓。既定は元のとおり [当日, 翌日]。quote は段 2 とそろえて前の日も読む
    ((b) の列が日の始め直後に前の日の約定を引けるように。批評家 1 回目の問 2)。any の値は以後の
    約定しか使わないので、前の日を読んでも値は変わらない。"""
    return window_days(day, 1 if fill_side == fill.FILL_QUOTE else 0, 1)


def quote_book(fill_side: str, quotes_dir, days):
    return (fill.QuoteBook.load(Path(quotes_dir), days) if fill_side == fill.FILL_QUOTE
            else None)


def extra_on(fill_side: str, leg_path: bool) -> bool:
    return fill_side != fill.FILL_ANY or bool(leg_path)


# =========================================================================== #
# 日ごとの本体
# =========================================================================== #
def run_day(day, days, pr, ctx, bund, pday, psign, pre15, pre9, cuts15, cuts9, liq_ts,
            data_end_ms, store, metrics_cache, bucket_cache, funding, cand_cache, opened,
            seed, chunks: Path, data_root: Path, period: str,
            fill_side: str = fill.FILL_ANY, leg_path: bool = False, quotes_dir=None) -> dict:
    tm: dict = {}
    t = time.time()
    rng = random.Random(seed * 100_000 + date.fromisoformat(day).toordinal())
    tr, miss = store.window(window_days(day, BACK_DAYS, FWD_DAYS))
    tm["約定の窓"] = time.time() - t
    sel = np.flatnonzero(pday == day)
    ts_sel = pr.ts[sel]

    # ---- 材料 ----
    t = time.time()
    sd = v2.load_side_data(data_root, day, store, metrics_cache, bucket_cache, funding)
    mats = v2.print_materials(pr, sel, tr, ctx, bund[MAIN_GAP], sd)
    pre = v2.pre_state_arrays(tr, ts_sel)
    tm["材料"] = time.time() - t

    # ---- 値動き ----
    t = time.time()
    rx = v2.reactions_from_anchor(tr, ts_sel, psign[sel])
    tm["値動き(プリント)"] = time.time() - t

    cols = {
        "print_id": pr.print_id[sel], "day": day, "ts_ms": ts_sel, "side": pr.side[sel],
        "sign": psign[sel], "qty": pr.qty[sel], "orig_qty": pr.orig_qty[sel],
        "avg_price": pr.price[sel], "usd_notional_100": pr.qty[sel] * 100.0,
        "before_seal": int(date.fromisoformat(day) < v2.SEAL_BOUNDARY),
        "opened_before": int(day in opened), "period": period,
        "elapsed_prev_s": ctx["elapsed_prev_s"][sel],
        "qty_ratio_prev": ctx["qty_ratio_prev"][sel],
        "qty_ratio_max60": ctx["qty_ratio_max60"][sel],
        "m10_signed": psign[sel] * pre["raw_m10"], "m60_signed": psign[sel] * pre["raw_m60"],
        "imb5": pre["imb5"],
        "gap_next_same_s": np.where(np.isfinite(ctx["gap_next_ms"][sel]),
                                    ctx["gap_next_ms"][sel] / 1000.0, NAN),
    }
    for X in v2.GAPS_S:   # ラベル(1): 同じ側の次が X 秒以内(事後)
        cols[f"cont_{X}"] = (ctx["gap_next_ms"][sel] <= X * 1000).astype(int)
    for g in v2.GAPS_S:
        b = bund[g]
        cols[f"g{g}_bundle"] = b["bundle_id"][sel]
        cols[f"g{g}_k"] = b["k_in_bundle"][sel]
        cols[f"g{g}_n_post"] = b["n_in_bundle"][sel]      # 事後
        cols[f"g{g}_pos_post"] = b["pos_label"][sel]      # 事後
        cols[f"g{g}_qty_so_far"] = b["qty_so_far"][sel]
    cols.update(mats)
    cols["t0_ms"], cols["p0"], cols["p0_lag_ms"] = rx["t0_ms"], rx["p0"], rx["p0_lag_ms"]
    cols.update(reaction_cols(rx))
    write_df(pd.DataFrame(cols), chunks / "prints" / f"{day}.csv.gz")

    # ---- Jev の状態(呼ばない) ----
    jrows = []
    for r, i in enumerate(sel.tolist()):
        row = {k: mats[k][r] for k in mats}
        jrows.append({"print_id": str(pr.print_id[i]),
                      "state": v2.jev_state_raw(i, pr, row, bund[MAIN_GAP])})
    (chunks / "jev").mkdir(parents=True, exist_ok=True)
    v2.write_jsonl_gz(chunks / "jev" / f"{day}.jsonl.gz", jrows)

    # ---- 束と状態機械(束の最初のプリントがこの日) ----
    t = time.time()
    price_fn = v2.make_price_fn(tr)
    wdays = window_days(day, BACK_DAYS, FWD_DAYS)
    sim = make_sim(pr, tr, price_fn, fill_side, leg_path,
                   present_days=[d for d in wdays if d not in set(miss)],
                   quotes=quote_book(fill_side, quotes_dir, wdays))
    xon = extra_on(fill_side, leg_path)
    brows, crows, lrows = [], [], []
    crows_any, lrows_any = [], []
    act, jud = Counter(), Counter()
    for g in v2.GAPS_S:
        for b in bund[g]["bundles"]:
            if v2.day_of_ms(b["start_ms"]) != day:
                continue
            brows.append({k: b[k] for k in ("bundle_id", "side", "gap_s", "start_ms",
                                            "end_ms", "n_prints", "qty_total")}
                         | {"day": day, "dur_s": (b["end_ms"] - b["start_ms"]) / 1000})
            for dly in v2.DELAYS_S:
                runs = []
                for pol in v2.JUDGED_POLICIES:
                    jd = v2.judgments_for(pol, b["members"], ctx)
                    for typ in POLICY_TYPES:
                        res = sim(b, jd, typ, dly)
                        runs.append((pol, typ, res))
                        for p in res["path"]:
                            act[f"{g}|{dly}|{pol}|{typ}|{p['行動']}"] += 1
                            jud[f"{g}|{dly}|{pol}|{typ}|{p['判断']}"] += 1
                for pol, direction in v2.BASELINE_POLICIES.items():
                    res = sim(b, None, "-", dly, baseline=direction)
                    res["legs"] = [] if res["missing"] else [
                        {"位置": 0, "向き": direction, "出口の理由": "連鎖の終わり",
                         "レグ損益_bp": res["pnl_bp"], "保有秒": res["hold_seconds"]}]
                    res["_baseline_dir"] = direction
                    runs.append((pol, "-", res))
                for pol, typ, res in runs:
                    if fill_side == fill.FILL_QUOTE:
                        ca, la = any_rows(
                            res, {"bundle_id": b["bundle_id"], "day": day, "period": period,
                                  "side": b["side"], "gap_s": g, "delay_s": dly, "policy": pol,
                                  "type": typ, "n_prints": b["n_prints"],
                                  "qty_total": b["qty_total"]},
                            {"bundle_id": b["bundle_id"], "day": day, "period": period,
                             "gap_s": g, "delay_s": dly, "policy": pol, "type": typ},
                            res.get("_baseline_dir"))
                        crows_any.append(ca)
                        lrows_any.extend(la)
                    crows.append({"bundle_id": b["bundle_id"], "day": day, "period": period,
                                  "side": b["side"],
                                  "gap_s": g, "delay_s": dly, "policy": pol, "type": typ,
                                  "n_prints": b["n_prints"], "qty_total": b["qty_total"],
                                  "pnl_bp": res["pnl_bp"], "entered": int(bool(res["entered"])),
                                  "n_entries": res["n_entries"], "hold_s": res["hold_seconds"],
                                  "missing": int(bool(res["missing"])),
                                  "first_entry_pos": res.get("first_entry_pos")}
                                 | (fill.cascade_extra(res, fill_side) if xon else {}))
                    for li, lg in enumerate(res["legs"]):
                        lrows.append({"bundle_id": b["bundle_id"], "day": day, "period": period,
                                      "gap_s": g,
                                      "delay_s": dly, "policy": pol, "type": typ,
                                      "leg_pos": lg["位置"], "leg_dir": lg["向き"],
                                      "exit_reason": lg["出口の理由"],
                                      "pnl_bp": lg["レグ損益_bp"], "hold_s": lg["保有秒"]}
                                     | (fill.leg_extra(res, li, fill_side, leg_path)
                                        if xon else {}))
    for name, rows in (("bundles", brows), ("cascades", crows), ("legs", lrows),
                       ("cascades_any", crows_any), ("legs_any", lrows_any)):
        if rows:
            write_df(pd.DataFrame(rows), chunks / name / f"{day}.csv.gz")
    tm["状態機械"] = time.time() - t

    # ---- s 秒の曲線(記述。方策ではない) ----
    t = time.time()
    rows_i, ss = v2.s_curve_points(ts_sel, ctx["gap_next_ms"][sel], data_end_ms)
    sc_cols = [(d, h) for d in v2.DELAYS_S for h in v2.HORIZONS_S]
    mat = np.empty((ss.size, len(sc_cols)), dtype=np.float32)
    for dly in v2.DELAYS_S:
        vals = v2.s_curve_values(tr, ts_sel, psign[sel], rows_i, ss, dly, v2.HORIZONS_S)
        for h, vv in vals.items():
            mat[:, sc_cols.index((dly, h))] = vv
    (chunks / "scurve").mkdir(parents=True, exist_ok=True)
    np.savez(chunks / "scurve" / f"{day}.npz", s=ss.astype(np.int16), v=mat)
    tm["s 秒の曲線"] = time.time() - t

    # ---- 対照 ----
    t = time.time()
    ctrl_meta: dict = {}
    crs = []

    def add_ctrl(kind, t_arr, dir_arr, ref_ids, extra=None):
        rxc = v2.reactions_from_anchor(tr, t_arr, dir_arr)
        c = {"kind": kind, "day": day, "anchor_ms": t_arr, "dir": dir_arr, "ref_id": ref_ids,
             "t0_ms": rxc["t0_ms"], "p0": rxc["p0"]}
        if extra:
            c.update(extra)
        c.update(reaction_cols(rxc))
        crs.append(pd.DataFrame(c))

    # (i) 無作為(±5 分)
    tc = v2.control_random(day, sel.size, liq_ts, rng)
    ctrl_meta["(i)無作為"] = [int(tc.size), int(sel.size)]
    if tc.size:
        add_ctrl("(i)無作為", tc, v2.pre_state_arrays(tr, tc)["dir10"], [""] * tc.size)
    # (ii) 勢いと成行の偏りを合わせた時刻(同じ日 → ±1 → ±2 → ±3 日)
    cands = {}
    for o in v2.CTRL2_DAY_OFFSETS:
        d2 = shift(day, o)
        if d2 not in cand_cache:
            cand_cache[d2] = v2.grid_candidates(d2, tr, liq_ts)
        cands[o] = cand_cache[d2]
    off, pick = v2.match_across_days(pre15[sel], pre9[sel], cands, cuts15, cuts9)
    got = pick >= 0
    ctrl_meta["(ii)合わせた時刻"] = [int(got.sum()), int(sel.size)]
    ctrl_meta["(ii)日のずれ別"] = {str(o): int((off == o).sum()) for o in v2.CTRL2_DAY_OFFSETS}
    if got.any():
        t2c = np.array([cands[o]["t"][j] for o, j in zip(off[got], pick[got])], dtype=np.int64)
        d2c = np.array([cands[o]["dir"][j] for o, j in zip(off[got], pick[got])], dtype=float)
        add_ctrl("(ii)合わせた時刻", t2c, d2c, pr.print_id[sel][got].tolist(),
                 {"day_offset": off[got]})
    # (iii) プラセボ(束ごと、g ごと)
    for g in v2.GAPS_S:
        bl = [b for b in bund[g]["bundles"] if v2.day_of_ms(b["start_ms"]) == day]
        pl = v2.control_placebo(day, tr, bl, liq_ts, rng)
        key = f"(iii)プラセボ_g{g}"
        ctrl_meta[key] = [len(pl), len(bl)]
        if pl:
            add_ctrl(key, np.array([p["end_ms"] for p in pl], dtype=np.int64),
                     np.array([p["dir"] for p in pl], dtype=float),
                     [p["bundle_id"] for p in pl],
                     {"vol_bundle": [p["vol_bundle"] for p in pl],
                      "vol_placebo": [p["vol_placebo"] for p in pl],
                      "win_start_ms": [p["start_ms"] for p in pl]})
    if crs:
        write_df(pd.concat(crs, ignore_index=True), chunks / "controls" / f"{day}.csv.gz")
    tm["対照"] = time.time() - t

    meta = {"day": day, "prints": int(sel.size), "missing_trade_days": miss,
            "action_counts": dict(act), "judge_counts": dict(jud), "controls": ctrl_meta,
            "timing_s": {k: round(v, 3) for k, v in tm.items()},
            "maxrss_mb_after": round(maxrss_mb(), 1)}
    (chunks / "meta").mkdir(parents=True, exist_ok=True)
    (chunks / "meta" / f"{day}.json").write_text(json.dumps(meta, ensure_ascii=False))
    return meta


# =========================================================================== #
# main
# =========================================================================== #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--data-root", default=str(v2.DEFAULT_DATA_ROOT))
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=v2.SEED)
    ap.add_argument("--resume", action="store_true",
                    help="chunks/meta/<日>.json がある日を飛ばす")
    ap.add_argument("--fill-side", choices=fill.FILL_SIDES, default=fill.FILL_ANY,
                    help="状態機械の値段の付け方。any = 元の走らせ(以後で最初の約定、どちらの側でも)、"
                         "quote = 目標の時刻以前で最新の最良気配(買いは売り気配、売りは買い気配。"
                         "liq_cascade_fill の docstring)")
    ap.add_argument("--quotes-dir", default=str(REPO_ROOT / "data" / "c9_bookticker"),
                    help="--fill-side quote の気配の置き場(scripts/c9_fetch_bookticker.py の出力)")
    ap.add_argument("--leg-path", action="store_true",
                    help="レグの行に入り・出の約定と経路(MFE・MAE)の列を足す")
    args = ap.parse_args(argv)

    t_all = time.time()
    timing: dict = {}
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    days = v2.day_range(start, end)
    out = Path(args.out)
    chunks = out / "chunks"
    if chunks.exists() and not args.resume:
        shutil.rmtree(chunks)
    chunks.mkdir(parents=True, exist_ok=True)
    data_root = Path(args.data_root)

    t = time.time()
    pr = v2.load_prints(data_root, start - timedelta(days=PRINT_MARGIN_DAYS),
                        end + timedelta(days=PRINT_MARGIN_DAYS))
    data_end_ms = v2.day_start_ms(shift(args.end, PRINT_MARGIN_DAYS)) + v2.MS_DAY
    pday, psign = pr.day, pr.sign
    ctx = v2.same_side_context(pr)
    bund = {g: v2.same_side_bundles(pr, g) for g in v2.GAPS_S}
    liq_ts = pr.ts.copy()
    in_run = np.isin(pday, np.array(days, dtype=object))
    opened = opened_days()
    funding = v2.cont_module().load_funding_all(data_root)
    timing["清算・資金調達率の読み込みと束"] = time.time() - t
    print(f"[c9a] プリント {len(pr)}(走らせの日 {int(in_run.sum())})"
          f" 一意化 {pr.stats.n_in}→{pr.stats.n_out}", flush=True)

    store = v2.TradeStore(data_root)

    # ---- 段 1: 材料 15・9(対照 (ii) の帯の境のため。日ごとに chunks/pre に残す) ----
    t = time.time()
    pre15 = np.full(len(pr), NAN)
    pre9 = np.full(len(pr), NAN)
    for day in days:
        sel = np.flatnonzero(pday == day)
        cp = chunks / "pre" / f"{day}.npz"
        if cp.exists():
            z = np.load(cp)
            pre15[sel], pre9[sel] = z["mat15"], z["mat9"]
            continue
        tr, _m = store.window(window_days(day, 1, 0))
        pre = v2.pre_state_arrays(tr, pr.ts[sel])
        pre15[sel] = pre["mat15"]
        pre9[sel] = np.where(np.isfinite(pre["imb5"]), psign[sel] * pre["imb5"], NAN)  # 前の材料 9
        cp.parent.mkdir(parents=True, exist_ok=True)
        np.savez(cp, mat15=pre15[sel], mat9=pre9[sel])
        store.drop_before(shift(day, 0))
    cuts15 = v2.decile_cuts(pre15[in_run])
    cuts9 = v2.decile_cuts(pre9[in_run])
    timing["段1 材料15・9"] = time.time() - t
    store.cache.clear()

    # ---- 段 2(日ごとに chunks へ書く) ----
    make_days, meas_days = v2.split_days(days)
    period_of = {d: ("作る" if d in set(make_days) else "測る") for d in days}
    t2 = time.time()
    metrics_cache: dict = {}
    bucket_cache: dict = {}
    cand_cache: dict = {}
    for day in days:
        if args.resume and (chunks / "meta" / f"{day}.json").exists():
            continue
        m = run_day(day, days, pr, ctx, bund, pday, psign, pre15, pre9, cuts15, cuts9,
                    liq_ts, data_end_ms, store, metrics_cache, bucket_cache, funding,
                    cand_cache, opened, args.seed, chunks, data_root, period_of[day],
                    fill_side=args.fill_side, leg_path=args.leg_path,
                    quotes_dir=args.quotes_dir)
        store.drop_before(shift(day, 1 - BACK_DAYS))
        for k in [k for k in cand_cache if k < shift(day, 1 - 3)]:
            del cand_cache[k]
        print(f"[c9a] {day} プリント {m['prints']} 経過 {time.time() - t_all:.1f}s "
              f"maxrss {maxrss_mb():.0f}MB", flush=True)
    timing["段2 合計"] = time.time() - t2

    # ---- 段 3: 規則(3 択)。前半で確率と帯を作り、後半の束に当てる ----
    t = time.time()
    store.cache.clear()
    three = stage3(out, chunks, make_days, meas_days, pr, ctx, bund, store, args.resume,
                   fill_side=args.fill_side, leg_path=args.leg_path,
                   quotes_dir=args.quotes_dir)
    timing["段3 規則3択"] = time.time() - t

    # ---- 集計(chunks を読む) ----
    t = time.time()
    tables, metas = aggregate(chunks, days)
    timing["集計"] = time.time() - t

    # ---- 書き出し ----
    t = time.time()
    for name, df in tables.items():
        df.to_csv(out / f"{name}.csv", index=False, float_format=FLOAT_FMT)
    for name, fname in (("prints", "anchors_prints"), ("bundles", "anchors_bundles"),
                        ("cascades", "policy_cascades"), ("legs", "policy_legs"),
                        ("controls", "controls")):
        concat_chunks(sorted((chunks / name).glob("*.csv.gz")) +
                      (sorted((chunks / f"{name}3").glob("*.csv.gz"))
                       if name in ("cascades", "legs") else []),
                      out / f"{fname}.csv.gz")
    with gzip.open(out / "jev_states.jsonl.gz", "wt", encoding="utf-8") as fo:
        for p in sorted((chunks / "jev").glob("*.jsonl.gz")):
            with gzip.open(p, "rt", encoding="utf-8") as fi:
                shutil.copyfileobj(fi, fo)
    timing["書き出し"] = time.time() - t
    timing["全体"] = time.time() - t_all

    ctrl_tot: dict = {}
    for m in metas:
        for k, v in m["controls"].items():
            if k == "(ii)日のずれ別":
                d = ctrl_tot.setdefault(k, {})
                for o, c in v.items():
                    d[o] = d.get(o, 0) + c
            else:
                a = ctrl_tot.setdefault(k, [0, 0])
                a[0] += v[0]
                a[1] += v[1]
    meta = {
        "設計": "docs/RESEARCH/cards/c9_liquidation_cascade/REDESIGN_2026-10-03.md",
        "期間": [args.start, args.end], "日数": len(days),
        "一意化": {"生の行": pr.stats.n_in, "一意": pr.stats.n_out,
                 "多重度": {str(k): v for k, v in pr.stats.multiplicity.items()},
                 "注": f"前後 {PRINT_MARGIN_DAYS} 日を足して読んだ範囲の数"},
        "走らせの日のプリント": int(in_run.sum()),
        "束の数": {str(g): sum(1 for b in bund[g]["bundles"]
                              if v2.day_of_ms(b["start_ms"]) in set(days)) for g in v2.GAPS_S},
        "約定の欠けた日(窓の中)": sorted({d for m in metas for d in m["missing_trade_days"]}),
        "対照の取れた数": {k: ({"取れた": v[0], "求めた": v[1]} if isinstance(v, list) else v)
                       for k, v in ctrl_tot.items()},
        "対照(ii)の帯の境": {"mat15": cuts15.tolist(), "mat9": cuts9.tolist(),
                         "注": "この走らせのプリントから(分割しない、設計 §6 の 3)"},
        "所要_秒": {k: round(v, 2) for k, v in timing.items()},
        "日ごとの所要_秒": {m["day"]: m["timing_s"] for m in metas},
        "最大メモリ_MB(ru_maxrss)": round(maxrss_mb(), 1),
        "固定値": {"HORIZONS_S": v2.HORIZONS_S, "GAPS_S": v2.GAPS_S, "DELAYS_S": v2.DELAYS_S,
                 "S_MAX": v2.S_MAX, "STALENESS_MS": v2.STALENESS_MS, "seed": args.seed,
                 "CTRL2_DAY_OFFSETS": v2.CTRL2_DAY_OFFSETS},
        "Jev": "呼んでいない(jev_states.jsonl.gz に状態だけ。L-569 で保留)",
        "規則3択": three,
        "resume": bool(args.resume),
    }
    if extra_on(args.fill_side, args.leg_path):
        meta["走らせ直し_2026-10-06"] = {
            "fill_side": args.fill_side, "leg_path": bool(args.leg_path),
            "quotes_dir": args.quotes_dir if args.fill_side == fill.FILL_QUOTE else None,
            "委任文": "docs/DISCUSSIONS/2026-10-06_held_batches/DELEGATION_rerun_impl.md",
            "注": "状態機械の連鎖・レグの行だけに効く。値動き・s 秒の曲線・対照は元と同じ道具"}
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


# =========================================================================== #
# 段 3: 規則(3 択)
# =========================================================================== #
def stage3(out: Path, chunks: Path, make_days, meas_days, pr, ctx, bund, store, resume,
           fill_side: str = fill.FILL_ANY, leg_path: bool = False, quotes_dir=None) -> dict:
    """前半(作る)の日のプリントだけで確率の模型と帯を作り(`v2.fit_three_way`)、後半(測る)の日の
    束に「規則_3択」を当てて状態機械を流す。後半のラベルは模型にも帯にも入らない(試験で固定)。"""
    cols = ["print_id", "day", v2.LOGIT_LABEL] + list(v2.LOGIT_FEATURES)
    P = read_chunks(sorted((chunks / "prints").glob("*.csv.gz")), cols)
    if not len(P):
        return {"注": "プリントが無い"}
    model = v2.fit_three_way(P, make_days)
    prob_rows = v2.predict_three_way(model, P)
    pid_index = {str(x): i for i, x in enumerate(pr.print_id.tolist())}
    prob = np.full(len(pr), NAN)
    for pid, pv in zip(P["print_id"].astype(str), prob_rows):
        prob[pid_index[pid]] = pv
    scene = v2.scene_of(P[v2.MAT_COL[1]])
    judge = [v2.judge_three_way(pv, model[sc]["band"], model[sc]["cross"])
             for pv, sc in zip(prob_rows, scene)]
    pd.DataFrame({"print_id": P["print_id"], "day": P["day"],
                  "期間": np.where(P["day"].astype(str).isin(set(make_days)), "作る", "測る"),
                  "場面": scene, "続くの確率": prob_rows, "判断": judge,
                  v2.LOGIT_LABEL: P[v2.LOGIT_LABEL]}).to_csv(
        out / "three_way_probs.csv.gz", index=False, float_format=FLOAT_FMT)
    cal_rows = []
    for sc, m in model.items():
        for r in m["calib"]:
            cal_rows.append({"場面": sc} | r)
    pd.DataFrame(cal_rows).to_csv(out / "three_way_calibration.csv", index=False,
                                  float_format=FLOAT_FMT)
    summary = {"作る日": [make_days[0], make_days[-1]] if make_days else [],
               "測る日": [meas_days[0], meas_days[-1]] if meas_days else [],
               "材料": list(v2.LOGIT_FEATURES), "ラベル": v2.LOGIT_LABEL, "場面": {}}
    for sc, m in model.items():
        summary["場面"][sc] = {
            "件数(作る)": m["n"], "基準率(作る)": m["base"], "分割数": m.get("n_folds"),
            "わからないの帯": m["band"], "基準率を跨ぐ帯": m["cross"],
            "係数": (None if m["beta"] is None else
                   dict(zip(["切片"] + list(v2.LOGIT_FEATURES), map(float, m["beta"]))))}
    for day in meas_days:
        if resume and (chunks / "meta3" / f"{day}.json").exists():
            continue
        # 既定は元のとおり [当日, 翌日]。quote のときは段 2 とそろえて前の日も読む((b) の列が
        # 日の始め直後に前の日の約定を引けるように。批評家 1 回目の問 2)。any の値は以後の約定しか
        # 使わないので前の日を読んでも変わらない。
        w3 = stage3_window(day, fill_side)
        tr, _miss = store.window(w3)
        price_fn = v2.make_price_fn(tr)
        sim = make_sim(pr, tr, price_fn, fill_side, leg_path,
                       present_days=[d for d in w3 if d not in set(_miss)],
                       quotes=quote_book(fill_side, quotes_dir, w3))
        xon = extra_on(fill_side, leg_path)
        crows, lrows = [], []
        crows_any, lrows_any = [], []
        act, jud = Counter(), Counter()
        for g in v2.GAPS_S:
            for b in bund[g]["bundles"]:
                if v2.day_of_ms(b["start_ms"]) != day:
                    continue
                jd = v2.judgments_for(v2.POLICY_3WAY, b["members"], ctx, prob, model)
                for dly in v2.DELAYS_S:
                    for typ in POLICY_TYPES:
                        res = sim(b, jd, typ, dly)
                        for p in res["path"]:
                            act[f"{g}|{dly}|{v2.POLICY_3WAY}|{typ}|{p['行動']}"] += 1
                            jud[f"{g}|{dly}|{v2.POLICY_3WAY}|{typ}|{p['判断']}"] += 1
                        if fill_side == fill.FILL_QUOTE:
                            ca, la = any_rows(
                                res, {"bundle_id": b["bundle_id"], "day": day, "period": "測る",
                                      "side": b["side"], "gap_s": g, "delay_s": dly,
                                      "policy": v2.POLICY_3WAY, "type": typ,
                                      "n_prints": b["n_prints"], "qty_total": b["qty_total"]},
                                {"bundle_id": b["bundle_id"], "day": day, "period": "測る",
                                 "gap_s": g, "delay_s": dly, "policy": v2.POLICY_3WAY,
                                 "type": typ}, None)
                            crows_any.append(ca)
                            lrows_any.extend(la)
                        crows.append({"bundle_id": b["bundle_id"], "day": day, "period": "測る",
                                      "side": b["side"], "gap_s": g, "delay_s": dly,
                                      "policy": v2.POLICY_3WAY, "type": typ,
                                      "n_prints": b["n_prints"], "qty_total": b["qty_total"],
                                      "pnl_bp": res["pnl_bp"],
                                      "entered": int(bool(res["entered"])),
                                      "n_entries": res["n_entries"], "hold_s": res["hold_seconds"],
                                      "missing": int(bool(res["missing"])),
                                      "first_entry_pos": res.get("first_entry_pos")}
                                     | (fill.cascade_extra(res, fill_side) if xon else {}))
                        for li, lg in enumerate(res["legs"]):
                            lrows.append({"bundle_id": b["bundle_id"], "day": day,
                                          "period": "測る", "gap_s": g, "delay_s": dly,
                                          "policy": v2.POLICY_3WAY, "type": typ,
                                          "leg_pos": lg["位置"], "leg_dir": lg["向き"],
                                          "exit_reason": lg["出口の理由"],
                                          "pnl_bp": lg["レグ損益_bp"], "hold_s": lg["保有秒"]}
                                         | (fill.leg_extra(res, li, fill_side, leg_path)
                                            if xon else {}))
        if crows:
            write_df(pd.DataFrame(crows), chunks / "cascades3" / f"{day}.csv.gz")
        if lrows:
            write_df(pd.DataFrame(lrows), chunks / "legs3" / f"{day}.csv.gz")
        for name, rows in (("cascades3_any", crows_any), ("legs3_any", lrows_any)):
            if rows:
                write_df(pd.DataFrame(rows), chunks / name / f"{day}.csv.gz")
        (chunks / "meta3").mkdir(parents=True, exist_ok=True)
        (chunks / "meta3" / f"{day}.json").write_text(json.dumps(
            {"day": day, "action_counts": dict(act), "judge_counts": dict(jud)},
            ensure_ascii=False))
        store.drop_before(day)
    jc = pd.Series(judge)
    per = np.where(P["day"].astype(str).isin(set(make_days)), "作る", "測る")
    summary["判断の件数(プリント)"] = {
        f"{p_}_{j}": int(((per == p_) & (jc == j).to_numpy()).sum())
        for p_ in ("作る", "測る") for j in ("止まる", "わからない", "続く")}
    (out / "three_way_model.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1,
                                                          default=float))
    return {k: summary[k] for k in ("作る日", "測る日", "判断の件数(プリント)")} | {
        "わからないの帯": {sc: summary["場面"][sc]["わからないの帯"] for sc in summary["場面"]}}


def concat_chunks(paths, dest: Path) -> None:
    """見出しを 1 回だけ残して gz の CSV をつなぐ(列は日ごとに同じ順で書いてある)。

    対照の (ii) が 1 件も合わなかった日は day_offset の列が無い(add_ctrl は出た種類の列だけを書く)。
    列の数が一番多い見出しを基準にし、列がその部分集合の日は基準の並びに直して空欄で埋める。
    基準に無い列がある日は止める。"""
    heads = {}
    for p in paths:
        with gzip.open(p, "rt", encoding="utf-8", newline="") as fi:
            heads[p] = fi.readline()
    if not heads:
        with gzip.open(dest, "wt", encoding="utf-8", newline=""):
            return
    header = max(heads.values(), key=lambda h: (len(h.rstrip("\r\n").split(",")), list(heads.values()).count(h)))
    cols = header.rstrip("\r\n").split(",")
    with gzip.open(dest, "wt", encoding="utf-8", newline="") as fo:
        fo.write(header)
        for p in paths:
            if heads[p] == header:
                with gzip.open(p, "rt", encoding="utf-8", newline="") as fi:
                    fi.readline()
                    shutil.copyfileobj(fi, fo)
                continue
            own = heads[p].rstrip("\r\n").split(",")
            if not set(own) <= set(cols):
                raise SystemExit(f"[止め] 列が日ごとに違う(基準に無い列): {p}")
            df = pd.read_csv(p, dtype=str, keep_default_na=False).reindex(columns=cols, fill_value="")
            df.to_csv(fo, index=False, header=False)


def read_chunks(paths, usecols=None) -> pd.DataFrame:
    parts = [pd.read_csv(p, usecols=usecols) for p in paths]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


# =========================================================================== #
# 集計(平均だけの行は作らない)
# =========================================================================== #
def aggregate(chunks: Path, days: list[str]):
    metas = [json.loads(p.read_text()) for p in sorted((chunks / "meta").glob("*.json"))
             if p.stem in set(days)]
    metas3 = [json.loads(p.read_text()) for p in sorted((chunks / "meta3").glob("*.json"))
              if p.stem in set(days)]
    rk = [f"{k}_{h}" for h in v2.HORIZONS_S for k in v2.REACTION_KEYS]
    keep_p = ["day", "side", "qty", v2.MAT_COL[12]] + [f"cont_{X}" for X in v2.GAPS_S] + \
        [f"g{g}_pos_post" for g in v2.GAPS_S] + [f"g{g}_qty_so_far" for g in v2.GAPS_S] + rk
    P = read_chunks(sorted((chunks / "prints").glob("*.csv.gz")), keep_p)
    C = read_chunks(sorted((chunks / "controls").glob("*.csv.gz")),
                    lambda c: c in {"kind", "day"} or c in set(rk))
    pdays = P["day"].astype(str).to_numpy(object) if len(P) else np.zeros(0, object)

    reaction = []

    def add(group, df, mask=None):
        if not len(df):
            return
        d = df if mask is None else df[mask]
        dd = d["day"].astype(str).to_numpy(object)
        for h in v2.HORIZONS_S:
            for k in v2.REACTION_KEYS:
                reaction.append({"群": group, "h_s": h, "量": k} |
                                v2.dist_stats(d[f"{k}_{h}"].to_numpy(float), dd))

    add("実_全プリント", P)
    if len(P):
        for s in ("SELL", "BUY"):
            add(f"実_側{s}", P, (P["side"] == s).to_numpy())
        for g in v2.GAPS_S:
            for lab in ("単発", "最初", "途中", "最後"):
                add(f"実_g{g}_位置{lab}(事後)", P, (P[f"g{g}_pos_post"] == lab).to_numpy())
    if len(C):
        for kd in sorted(C["kind"].unique()):
            add(f"対照{kd}", C, (C["kind"] == kd).to_numpy())

    size_split = []
    split_cols = [("qty", "1件の数量(枚)"), (v2.MAT_COL[12], "材料12 直前60秒の最大との比")] + \
        [(f"g{g}_qty_so_far", f"g{g}_連鎖のここまでの数量(枚)") for g in v2.GAPS_S]
    for col, name in split_cols:
        if not len(P):
            break
        x = P[col].to_numpy(float)
        cuts = v2.tertile_cuts(x)
        if cuts.size < 2:
            continue
        b = np.where(np.isfinite(x), np.searchsorted(cuts, x, side="right"), -1)
        for t_ in range(3):
            m = b == t_
            for h in v2.HORIZONS_S:
                for k in ("react", "mfe", "mae"):
                    size_split.append({"分け": name, "3分位": t_ + 1,
                                       "境": "|".join(f"{c:.6g}" for c in cuts), "h_s": h,
                                       "量": k} |
                                      v2.dist_stats(P[f"{k}_{h}"].to_numpy(float)[m], pdays[m]))

    policy = []
    CA = read_chunks(sorted((chunks / "cascades").glob("*.csv.gz")) +
                     sorted((chunks / "cascades3").glob("*.csv.gz")))
    LG = read_chunks(sorted((chunks / "legs").glob("*.csv.gz")) +
                     sorted((chunks / "legs3").glob("*.csv.gz")))
    if len(CA):
        key = ["period", "gap_s", "delay_s", "policy", "type"]
        lg_groups = dict(list(LG.groupby(key))) if len(LG) else {}
        for k, rows in CA.groupby(key):
            per, g, dly, pol, typ = k
            dd = rows["day"].astype(str).to_numpy(object)
            pnl = rows["pnl_bp"].to_numpy(float)
            ent = rows["entered"].to_numpy(bool)
            miss = rows["missing"].to_numpy(bool)
            base = {"期間": per, "gap_s": g, "delay_s": dly, "policy": pol, "type": typ,
                    "連鎖の数": len(rows), "入った連鎖": int(ent.sum()), "値の欠け": int(miss.sum())}
            incl = np.where(ent, pnl, np.where(miss, NAN, 0.0))
            policy.append(base | {"単位": "連鎖1本(入らないを0で含める)"} | v2.dist_stats(incl, dd))
            policy.append(base | {"単位": "連鎖1本(入った連鎖だけ)"} |
                          v2.dist_stats(pnl[ent], dd[ent]))
            lr = lg_groups.get(k)
            if lr is not None:
                policy.append(base | {"単位": "1レグ"} |
                              v2.dist_stats(lr["pnl_bp"].to_numpy(float),
                                            lr["day"].astype(str).to_numpy(object)))
            q = rows["qty_total"].to_numpy(float)
            cuts = v2.tertile_cuts(q)
            if cuts.size == 2:
                bq = np.searchsorted(cuts, q, side="right")
                for t_ in range(3):
                    m = bq == t_
                    policy.append(base | {"単位": f"連鎖1本(入らないを0)_束の総量3分位{t_ + 1}(事後)"}
                                  | v2.dist_stats(incl[m], dd[m]))

    # s 秒の曲線: 列ごとに日の npz から読む(全期間の行列を一度に持たない)
    scurve = []
    sc_cols = [(d, h) for d in v2.DELAYS_S for h in v2.HORIZONS_S]
    sc_files = [p for p in sorted((chunks / "scurve").glob("*.npz")) if p.stem in set(days)]
    s_parts, d_parts = [], []
    for p in sc_files:
        z = np.load(p)
        s_parts.append(z["s"].astype(np.int64))
        d_parts.append(np.full(z["s"].size, p.stem, dtype=object))
    if s_parts:
        s_all = np.concatenate(s_parts)
        order = np.argsort(s_all, kind="stable")
        s_all = s_all[order]
        d_all = np.concatenate(d_parts)[order]
        bounds = np.searchsorted(s_all, np.arange(1, v2.S_MAX + 2))
        for c, (dly, h) in enumerate(sc_cols):
            v_all = np.concatenate([np.load(p)["v"][:, c] for p in sc_files]).astype(float)[order]
            for s in range(1, v2.S_MAX + 1):
                a, b = bounds[s - 1], bounds[s]
                scurve.append({"s": s, "delay_s": dly, "h_s": h,
                               "向き": "fade(建玉の向き)・記述の曲線(方策ではない)"} |
                              v2.dist_stats(v_all[a:b], d_all[a:b]))

    labels = []
    for X in v2.GAPS_S:
        c = P[f"cont_{X}"].to_numpy(float) if len(P) else np.zeros(0)
        labels.append({"X_s": X, "プリント": int(c.size),
                       "続く(同じ側の次がX秒以内)": int(np.nansum(c)),
                       "割合": float(np.nanmean(c)) if c.size else NAN})

    act, jud = Counter(), Counter()
    for m in metas + metas3:
        act.update(m["action_counts"])
        jud.update(m["judge_counts"])

    def count_df(cnt, label):
        rows = []
        for k, v in sorted(cnt.items()):
            g, dly, pol, typ, a = k.split("|")
            rows.append({"gap_s": g, "delay_s": dly, "policy": pol, "type": typ, label: a,
                         "件数": v})
        return pd.DataFrame(rows)

    tables = {"dist_reaction": pd.DataFrame(reaction), "dist_size_split": pd.DataFrame(size_split),
              "dist_policy": pd.DataFrame(policy), "dist_s_curve": pd.DataFrame(scurve),
              "label_counts": pd.DataFrame(labels),
              "policy_action_counts": count_df(act, "行動"),
              "policy_judge_counts": count_df(jud, "判断")}
    return tables, metas


if __name__ == "__main__":
    raise SystemExit(main())
