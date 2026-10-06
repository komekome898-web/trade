"""W4 第 2 陣(カード 5〜8)の軽い測定。1 変種 = 1 起動。

    PYTHONPATH=src python run_b2.py --card c5|c6|c7|c8 --variant <変種> [--start --end --chunk year|month]
    (照合) PYTHONPATH=src python run_b2.py --card c7 --variant 1w --check --start 2018-01-01T00:00:00Z --end 2019-01-01T00:00:00Z
    (カード 6 の延長、走らせ直し 2026-10-06) --card c6 --variant <btc|usdjpy> --end 2023-12-17T15:00:00Z --usdjpy-2023
      --out-root <置き場>。--usdjpy-2023 は USDJPY の参照に common.USDJPY_PATH_2023(2023-01-01 から)を足す。
      カード 6 で終わりが 2023-01-01 より後なのにこの引数が無ければ止める(2023 年の週明けが 1 つも無い走らせになるため)。
      既定(引数なし)の読む置き場・期間は変わらない。

走らせ方(scratchpad/w4/measure/run_v2.py の run_carry と同じつなぎ方):
  区切り(既定は暦年)ごとに、その区切りの足(と c6 の参照の行)だけを封印の門(bot.bt.data)から読み、同じカードの物を
  区切りをまたいで使い続けて run_card に通す。カード 5・7・8 は view.bars(1) と自分の属性しか読まないので、物の状態
  (錨・窓の中の r^2・連鎖の起点・セッションの和)がそのまま続く。カード 6 は参照の行を順に読む(_seen が位置)ので、
  区切りの頭で _seen を 0 に戻し、区切りの最後の決定 t_last までに使えるようになった行をその区切りに、残りを次の
  区切りの頭に渡す(as-of の 1 行重ね(carry_last)は使わない: 順に読むカードなので重ねると 2 回読む)。
  慣らし(区切りの前の足を新しいカードに通す形)は使っていない。理由は README。
  同一性は --check(全期間を一度に読んで 1 回走らせた結果と、月の区切りでつないだ結果の持ち高のビット一致)。
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MEAS = os.path.join(os.path.dirname(HERE), "measure")
sys.path.insert(0, HERE)
sys.path.insert(0, MEAS)

from common import (FX_DIR, ROOT, USDJPY_2023_FROM, Clock, iso, load_bars, peak_rss_gb, to_iso,  # noqa: E402
                    usdjpy_ref_dataset)
from post import write_json  # noqa: E402
from run_v2 import boundaries, concat, ref_rows  # noqa: E402

from bot.bt.data.reference import load_reference, reference_series  # noqa: E402
from bot.research.cards import cardmd  # noqa: E402
from bot.research.cards.pnl import pnl  # noqa: E402
from bot.research.cards.run import run_card  # noqa: E402

LAG = 60 * 10**9
FULL = ("2015-11-28T15:00:00Z", "2023-12-17T15:00:00Z")
C4_TP = {"v37": {}, "c08": {"exit_mode": 1, "exit_setting": 0.8}, "c0": {"exit_mode": 1, "exit_setting": 0.0}, "dote": {"exit_mode": 0}}
C4_MAP = tuple(f"m_b{b}_w{w}_e{e}_{tp}" for b in (1, 5) for w in (10, 20, 40, 80, 160) for e in (1, 2, 3) for tp in C4_TP)
CARDS = {
    "c5": ("c5_tokyo_fix_momentum", ("default",), FULL),
    "c6": ("c6_weekend_gap_revert", ("usdjpy", "btc"), ("2017-08-01T15:00:00Z", "2022-12-31T15:00:00Z")),
    "c7": ("c7_barrier_race", ("1h", "1d", "1w"), FULL),
    "c8": ("c8_session_mean_revert", ("jst_day", "bf_maint"), FULL),
    "c4": ("c4_owner_matilda_range", tuple(f"{k}_{r}" for k in ("full", "no_width", "no_trend", "no_time", "no_levels", "follow", "core") for r in ("body", "wick")) + C4_MAP, FULL),
}
C4_KW = {"full": {}, "no_width": {"width_gate": False}, "no_trend": {"trend_gate": False}, "no_time": {"time_exit": False},
         "no_levels": {"levels": False}, "follow": {"on_trend": "follow"},
         "core": {"width_gate": False, "trend_gate": False, "time_exit": False, "levels": False}}


def make_card(card: str, variant: str):
    if card == "c4":
        from bot.research.cards.library.c4_owner_matilda_range import C4OwnerMatildaRange
        if variant.startswith("m_"):
            _, b, w, e, tp = variant.split("_")
            return C4OwnerMatildaRange(bar_min=int(b[1:]), window_min=int(w[1:]), entry_setting=float(e[1:]), **C4_TP[tp])
        k, r = variant.rsplit("_", 1)
        return C4OwnerMatildaRange(range_from=r, **C4_KW[k])
    if card == "c5":
        from bot.research.cards.library.c5_tokyo_fix_momentum import TokyoFixMomentum
        return TokyoFixMomentum()
    if card == "c6":
        from bot.research.cards.library.c6_weekend_gap_revert import WeekendGapRevert
        return WeekendGapRevert(variant)
    if card == "c7":
        from bot.research.cards.library.c7_barrier_race import BarrierRace
        return BarrierRace(variant)
    from bot.research.cards.library.c8_session_mean_revert import SessionMeanRevert
    return SessionMeanRevert(variant)


def run_chunks(card, lo, hi, bnds, decl, fx_all=None, clock=None):
    """同じカードの物で区切りをつなぐ。fx_all: c6 の USDJPY の (時刻, 値, manifest)(全期間を 1 回だけ読んだもの)。"""
    edges = [lo] + bnds + [hi]
    pend_t, pend_v = np.empty(0, dtype=np.int64), []
    runs, log, bar_files, kinds_all = [], [], {}, {}
    for a, b in zip(edges[:-1], edges[1:]):
        final = b == hi
        bars, kinds, h = load_bars(FX_DIR, "FX_BTC_JPY", a, b)
        bar_files.update(h)
        for k, v in kinds.items():
            kinds_all[k] = kinds_all.get(k, 0) + v
        refs, nrows = {}, None
        if fx_all is not None:
            from bot.research.cards.library.c6_weekend_gap_revert import FX
            ne = [x for x in bars if x.volume > 0]
            t_last = int(ne[-1].exchange_time_ns) if ne else int(bars[-1].exchange_time_ns)
            t, v, _m = fx_all
            i, j = np.searchsorted(t, [a, b], side="left")
            t_all = np.concatenate([pend_t, t[i:j]])
            v_all = pend_v + list(v[i:j])
            k = len(t_all) if final else int(np.searchsorted(t_all + LAG, t_last, side="right"))
            rows = list(zip(t_all[:k].tolist(), v_all[:k]))
            pend_t, pend_v = t_all[k:], v_all[k:]
            refs = {FX: reference_series(FX, rows, declarations=decl)}
            nrows = len(rows)
            card._seen = 0  # その区切りの参照の系列は、まだ読んでいない行から始まる
            del ne
        r = run_card(card, bars, references=refs, declarations=decl, venue="bitflyer", symbol="FX_BTC_JPY")
        runs.append(r)
        log.append({"range": [to_iso(a), to_iso(b)], "bars": len(bars), "decisions": int(r.decided.sum()),
                    "ref_rows": nrows, "delivery_digest": r.delivery_digest})
        if clock:
            clock.mark(f"区切り {to_iso(a)[:10]}〜{to_iso(b)[:10]} 足 {len(bars)} 参照 {nrows}")
        del bars, refs
        gc.collect()
    return concat(runs, log), log, {"files": bar_files, "anomalies": kinds_all}


def check(a, card_id, lo, hi, decl, fx_all):
    """全期間を一度に読んで 1 回走らせた結果と、月の区切りでつないだ結果の比較。"""
    t0 = time.time()
    bars, _k, _h = load_bars(FX_DIR, "FX_BTC_JPY", lo, hi)
    refs = {}
    if fx_all is not None:
        from bot.research.cards.library.c6_weekend_gap_revert import FX
        refs = {FX: load_reference(ROOT, usdjpy_ref_dataset(FX, lo, hi, extend=a.usdjpy_2023), declarations=decl)}
    r1 = run_card(make_card(a.card, a.variant), bars, references=refs, declarations=decl, venue="bitflyer",
                  symbol="FX_BTC_JPY")
    del bars, refs
    gc.collect()
    bnds = boundaries(lo, hi, "month")
    if fx_all is not None:  # 照合の範囲の行だけ(全期間を一度に読む側と同じ範囲)
        t, v, m = fx_all
        i, j = np.searchsorted(t, [lo, hi], side="left")
        fx_all = (t[i:j], v[i:j], m)
    r2, log, _ = run_chunks(make_card(a.card, a.variant), lo, hi, bnds, decl, fx_all)
    same_bars = bool(np.array_equal(r1.end_ns, r2.end_ns))
    eq = same_bars and np.array_equal(r1.exposure, r2.exposure, equal_nan=True) and np.array_equal(r1.decided, r2.decided)
    res = {"card": card_id, "variant": a.variant, "range": [to_iso(lo), to_iso(hi)], "chunk": "month",
           "n_boundaries": len(bnds), "n_bars": int(len(r1.end_ns)), "n_decisions": int(r1.decided.sum()),
           "same_bars": same_bars, "exposure_identical": bool(eq),
           "n_exposure_diff": int(np.sum(r1.exposure[r1.decided] != r2.exposure[r2.decided])) if same_bars else None,
           "nonzero_share": float(np.mean(r1.exposure[r1.decided] != 0)),
           "seconds": round(time.time() - t0, 1), "peak_rss_gb": round(peak_rss_gb(), 2)}
    if fx_all is not None and same_bars:
        heads = np.searchsorted(r1.start_ns, np.array(bnds, dtype=np.int64), side="left")  # 区切りの頭 = 始まりが境以後の最初の足
        for n in r1.ref_time:
            dt_ = r1.ref_time[n] != r2.ref_time[n]
            dv_ = ~((r1.ref_value[n] == r2.ref_value[n]) | (np.isnan(r1.ref_value[n]) & np.isnan(r2.ref_value[n])))
            bad = np.flatnonzero(dt_ | dv_)
            # 食い違う足が、区切りの頭から「区切りの中で最初の行が届くまで」の間だけか
            seg = np.searchsorted(heads, bad, side="right") - 1
            first_row = [int(np.argmax(r2.ref_time[n][h:] >= 0)) + h if h < len(r2.end_ns) else None for h in heads]
            only_heads = bool(all(s >= 0 and bad_i < first_row[s] for bad_i, s in zip(bad.tolist(), seg.tolist())))
            res[f"ref_diff_{n}"] = {"n_bars": int(len(bad)), "n_decided": int(r1.decided[bad].sum()),
                                    "chunk2_value_is_none": bool(np.all(r2.ref_time[n][bad] == -1)),
                                    "only_before_first_row_of_chunk": only_heads,
                                    "examples": [str(np.datetime64(int(r1.end_ns[i]), "ns")) for i in bad[:5].tolist()]}
    if fx_all is not None:
        res["ref_equal"] = all(np.array_equal(r1.ref_time[n], r2.ref_time[n])
                               and np.array_equal(r1.ref_value[n], r2.ref_value[n], equal_nan=True) for n in r1.ref_time)
    print(json.dumps(res, ensure_ascii=False), flush=True)
    write_json(res, os.path.join(HERE, "runs", f"check_{a.card}_{a.variant}.json"))
    return 0 if eq else 3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", required=True, choices=list(CARDS))
    ap.add_argument("--map-kw", default=None)
    ap.add_argument("--variant", required=True)
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--chunk", default="year", choices=["year", "month"])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out-root", default=None)
    ap.add_argument("--usdjpy-2023", action="store_true")
    a = ap.parse_args()
    card_id, variants, period = CARDS[a.card]
    if a.variant not in variants:
        raise SystemExit(f"変種 {a.variant} は {variants} に無い")
    clock = Clock()
    lo, hi = iso(a.start or period[0]), iso(a.end or period[1])
    if a.usdjpy_2023 and a.card != "c6":
        raise SystemExit("--usdjpy-2023 はカード 6 だけ(USDJPY を参照に読むのはカード 6 だけ)")
    if a.card == "c6" and hi > iso(USDJPY_2023_FROM) and not a.usdjpy_2023:
        raise SystemExit(f"終わり {to_iso(hi)} は {USDJPY_2023_FROM} より後: 2023 年からの USDJPY を読むには --usdjpy-2023 が要る")
    with open(os.path.join(ROOT, f"docs/RESEARCH/cards/{card_id}/CARD.md"), encoding="utf-8") as fh:
        st, problems = cardmd.settings(cardmd.parse(fh.read()))
    if problems:
        raise SystemExit(f"CARD.md の測定の設定が読めない: {problems}")
    decl = dict(st.declarations)
    fx_all = None
    if a.card == "c6":
        from bot.research.cards.library.c6_weekend_gap_revert import FX
        fx_all = ref_rows(FX, usdjpy_ref_dataset(FX, lo, hi, extend=a.usdjpy_2023), decl)  # 全期間を 1 回だけ読む
        clock.mark(f"USDJPY の行 {len(fx_all[0])}")
    if a.check:
        return check(a, card_id, lo, hi, decl, fx_all)
    bnds = boundaries(lo, hi, a.chunk)
    print(f"{card_id} {a.variant} 期間 {to_iso(lo)} 〜 {to_iso(hi)} 区切り {len(bnds)}", flush=True)
    card = make_card(a.card, a.variant)
    t0 = time.time()
    run, log, bar_in = run_chunks(card, lo, hi, bnds, decl, fx_all, clock=clock)
    t_run = time.time() - t0
    clock.mark(f"区切りの run_card(読み込みを含む) {t_run:.0f}s 決定 {int(run.decided.sum())}")
    out_root = a.out_root or os.path.join(ROOT, f"docs/RESEARCH/cards/{card_id}/measure")
    outdir = os.path.join(out_root, a.variant)
    os.makedirs(outdir, exist_ok=True)
    npz = os.path.join(outdir, "run.npz")
    np.savez_compressed(npz, open=run.open, high=run.high, low=run.low, close=run.close, exposure=run.exposure,
                        decided=run.decided, end_ns=run.end_ns, start_ns=run.start_ns, volume=run.volume)
    clock.mark("npz を保存")
    import light_b2
    t1 = time.time()
    p = pnl(run)
    stats = light_b2.measure(a.card, a.variant, run, p, outdir, lo, hi, fx_all)
    t_meas = time.time() - t1
    clock.mark(f"日ごとの測定と診断 {t_meas:.0f}s")
    inputs = {"bars": bar_in}
    if fx_all is not None:
        inputs["references"] = {"usdjpy_close": fx_all[2]}
    if light_b2.C5_FX_INPUT:
        inputs["usdjpy_for_diagnostic_4-2"] = light_b2.C5_FX_INPUT
    summary = {"card": card_id, "variant": a.variant, "period": [to_iso(lo), to_iso(hi)], "chunk": a.chunk,
               "chunks": log, "inputs": inputs, "npz": os.path.relpath(npz, ROOT),
               "timing": {"chunked_run_s": round(t_run, 1), "measure_s": round(t_meas, 1),
                          "total_s": round(time.time() - clock.t0, 1), "peak_rss_gb": round(peak_rss_gb(), 2)},
               "clock": clock.marks, "headline": stats}
    write_json(summary, os.path.join(outdir, "run_record.json"))
    print(json.dumps({"variant": a.variant, **stats, "timing": summary["timing"]}, ensure_ascii=False), flush=True)
    clock.mark("終わり")
    return 0


if __name__ == "__main__":
    sys.exit(main())
