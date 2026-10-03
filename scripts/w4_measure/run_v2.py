"""1 変種を、区切り(既定は暦年)ごとにその区切りの分だけを封印の門から読んで run_card に通し、つないだ全期間の
CardRun に測定器を 1 回当てる(リードの走らせ方の変更、2026-10-02)。1 変種 = 1 起動。並列は外側で 3 本まで。

    PYTHONPATH=src python run_v2.py --card c2 --variant a --foot 15
    PYTHONPATH=src python run_v2.py --card c3 --window 1w
    PYTHONPATH=src python run_v2.py --card c1
    (照合用) --start/--end/--chunk month|year/--out-root/--save-root/--no-measure

区切りのつなぎ方(区切りごとに読むのは、その区切りの足と参照の行だけ):
  c2・c3: 同じカードの物を区切りをまたいで使い続ける(持ち高・無効化ライン・まとめ中の足・窓の中の上乗せがそのまま続く)。
    参照の行は、区切りの最後の決定 t_last までに使えるようになった行をその区切りに、残り(使えるようになるのが t_last より後)を
    記憶に持ち越して次の区切りの頭に渡す。c2 はカードの「参照の行の位置」(_next_row)を区切りごとに 0 に戻す。
    c3 の USDJPY(as-of で読む)は、前の区切りで最後に使えるようになった行を 1 行重ねて渡す。
    → 各決定でカードが読む行・処理する行は、全期間を一度に走らせたときと同じ(慣らしは要らない)。
  c1: 区切りごとに新しいカードを作り、区切りの 1 日前から足と参照を渡して慣らし、区切りの中の足だけを使う(compare.py と同じ)。
    カードは直近 32 本の足と 31 分前までの参照を読み、持ち高は 買い・売り・決済 のどれかが出た時点で過去に依らなくなる。
同じになることは照合(check_v2.py)で確かめる。
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from common import (BIN_DIR, DAY_NS, FX_DIR, ROOT, SPOT_DIR, Clock, binance_ref_dataset, iso, load_bars,  # noqa: E402
                    paths, peak_rss_gb, to_iso, to_ns, usdjpy_ref_dataset)
from post import canonical_sha, summary_row, week_block, write_json  # noqa: E402

from bot.bt.data.reference import load_reference, reference_series  # noqa: E402
from bot.research.cards import cardmd  # noqa: E402
from bot.research.cards.measure import measure_card  # noqa: E402
from bot.research.cards.pnl import pnl  # noqa: E402
from bot.research.cards.run import CardRun, run_card  # noqa: E402

SEED, CONTROL_SEED = 20261002, 20261003
REGIME_LABEL = "SFD"
C2_VARIANTS = {  # 系列の名前の組の属性名, 置き場, ファイルの形, 期間
    "a": ("SERIES_SPOT", BIN_DIR, "binance_BTCUSDT_1m_{y}.csv.gz", ("2017-08-17T15:00:00Z", "2023-12-17T15:00:00Z"),
          "(a) SERIES_SPOT Binance BTCUSDT 現物"),
    "b": ("SERIES_UM", "backtest_data/binance_um_BTCUSDT_1m_20261002", "binance_um_BTCUSDT_1m_{y}.csv.gz",
          ("2020-01-01T15:00:00Z", "2023-12-17T15:00:00Z"), "(b) SERIES_UM Binance USD-M 先物 BTCUSDT"),
    "c": ("SERIES_BITMEX", "backtest_data/bitmex_XBTUSD_1m_from1s_20261002", "bitmex_XBTUSD_1m_{y}.csv.gz",
          ("2017-08-17T15:00:00Z", "2021-12-31T15:00:00Z"), "(c) SERIES_BITMEX BitMEX XBTUSD(1 秒足から作った 1 分足)"),
}


def boundaries(lo: int, hi: int, chunk: str) -> list:
    out = []
    d = datetime.fromtimestamp(lo / 1e9, tz=timezone.utc)
    y, m = d.year, d.month
    while True:
        if chunk == "year":
            y, m = y + 1, 1
        else:
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        b = to_ns(datetime(y, m, 1, tzinfo=timezone.utc))
        if b >= hi:
            return out
        out.append(b)


def ref_rows(name, dataset, decl):
    s = load_reference(ROOT, dataset, declarations=decl)
    return (np.array(s.times_ns, dtype=np.int64), list(s.values), [list(m) for m in s.manifest])


def concat(runs, log) -> CardRun:
    cat = np.concatenate
    f = runs[0]
    return CardRun(card=f.card, venue=f.venue, symbol=f.symbol,
                   start_ns=cat([r.start_ns for r in runs]), end_ns=cat([r.end_ns for r in runs]),
                   open=cat([r.open for r in runs]), high=cat([r.high for r in runs]), low=cat([r.low for r in runs]),
                   close=cat([r.close for r in runs]), volume=cat([r.volume for r in runs]),
                   decided=cat([r.decided for r in runs]), exposure=cat([r.exposure for r in runs]),
                   ref_time={n: cat([r.ref_time[n] for r in runs]) for n in f.ref_time},
                   ref_value={n: cat([r.ref_value[n] for r in runs]) for n in f.ref_value},
                   ref_lag_ns=f.ref_lag_ns, ref_decl=f.ref_decl,
                   delivery_digest="chunks:" + ",".join(x["delivery_digest"] for x in log))


def run_carry(card, lo, hi, bnds, decl, loaders: dict, carry_last=(), *, lag_ns: int, clock=None):
    """c2・c3: 同じカードの物で区切りをつなぐ。loaders: 名前 -> (lo, hi) を受けて (時刻, 値, manifest) を返す関数。"""
    edges = [lo] + bnds + [hi]
    pend = {n: (np.empty(0, dtype=np.int64), []) for n in loaders}  # 持ち越しの行(まだ使えるようになっていない)
    last_row = {n: None for n in carry_last}  # as-of の系列の、最後に使えるようになった行
    runs, log, manifests, bar_files, kinds_all = [], [], {n: [] for n in loaders}, {}, {}
    for a, b in zip(edges[:-1], edges[1:]):
        final = b == hi
        bars, kinds, h = load_bars(FX_DIR, "FX_BTC_JPY", a, b)
        bar_files.update(h)
        for k, v in kinds.items():
            kinds_all[k] = kinds_all.get(k, 0) + v
        ne = [x for x in bars if x.volume > 0]
        t_last = int(ne[-1].exchange_time_ns) if ne else int(bars[-1].exchange_time_ns)
        crefs, nrows = {}, {}
        for n, load in loaders.items():
            tt, vv, man = load(a, b)
            manifests[n] += man
            t_all = np.concatenate([pend[n][0], tt])
            v_all = pend[n][1] + vv
            k = len(t_all) if final else int(np.searchsorted(t_all + lag_ns, t_last, side="right"))
            rows = list(zip(t_all[:k].tolist(), v_all[:k]))
            if n in carry_last and last_row[n] is not None and (not rows or rows[0][0] > last_row[n][0]):
                rows = [last_row[n]] + rows
            if n in carry_last and k > 0:
                last_row[n] = (int(t_all[k - 1]), v_all[k - 1])
            pend[n] = (t_all[k:], v_all[k:])
            crefs[n] = reference_series(n, rows, declarations=decl)
            nrows[n] = len(rows)
        if hasattr(card, "_next_row"):
            card._next_row = 0
        r = run_card(card, bars, references=crefs, declarations=decl, venue="bitflyer", symbol="FX_BTC_JPY")
        runs.append(r)
        log.append({"range": [to_iso(a), to_iso(b)], "bars": len(bars), "t_last": to_iso(t_last), "ref_rows": nrows,
                    "delivery_digest": r.delivery_digest})
        if clock:
            clock.mark(f"区切り {to_iso(a)[:10]}〜{to_iso(b)[:10]} 足 {len(bars)} 参照 {nrows}")
        del bars, ne, crefs
        gc.collect()
    return concat(runs, log), log, {"bars": {"files": bar_files, "anomalies": kinds_all}, "references": manifests}


def run_c1_chunks(lo, hi, bnds, decl, clock=None):
    from bot.research.cards.library.c1_xborder_mom import LEADER, XborderMom
    edges = [lo] + bnds + [hi]
    runs, log, man, bar_files, kinds_all = [], [], [], {}, {}
    for a, b in zip(edges[:-1], edges[1:]):
        wa = a if a == lo else a - DAY_NS
        bars, kinds, h = load_bars(FX_DIR, "FX_BTC_JPY", wa, b)
        bar_files.update(h)
        for k, v in kinds.items():
            kinds_all[k] = kinds_all.get(k, 0) + v
        ref = load_reference(ROOT, binance_ref_dataset(LEADER, "close", wa - DAY_NS, b), declarations=decl)
        man += [list(m) for m in ref.manifest]
        r = run_card(XborderMom(), bars, references={LEADER: ref}, declarations=decl, venue="bitflyer",
                     symbol="FX_BTC_JPY")
        keep = r.start_ns >= a
        sl = {f: getattr(r, f)[keep] for f in ("start_ns", "end_ns", "open", "high", "low", "close", "volume",
                                                 "decided", "exposure")}
        r2 = CardRun(card=r.card, venue=r.venue, symbol=r.symbol, **sl,
                     ref_time={n: v[keep] for n, v in r.ref_time.items()},
                     ref_value={n: v[keep] for n, v in r.ref_value.items()},
                     ref_lag_ns=r.ref_lag_ns, ref_decl=r.ref_decl, delivery_digest=r.delivery_digest)
        runs.append(r2)
        log.append({"range": [to_iso(a), to_iso(b)], "warm_from": to_iso(wa), "bars_kept": int(keep.sum()),
                    "ref_rows": len(ref), "delivery_digest": r.delivery_digest})
        if clock:
            clock.mark(f"区切り {to_iso(a)[:10]}〜{to_iso(b)[:10]} 足 {int(keep.sum())}(慣らし {int((~keep).sum())})")
        del bars, ref, r
        gc.collect()
    return concat(runs, log), log, {"bars": {"files": bar_files, "anomalies": kinds_all},
                                    "references": {LEADER: man}}


def c3_diag(a, run, p, lo, hi, bnds, decl, fx_all, inputs):
    """カード 3 の診断(INTENT_MAP §4)。main と light の両方から呼ぶ。"""
    import run_c3
    from bot.research.cards.library.c3_yen_premium_revert import OVERSEAS
    st_l, sc_l, skinds, spot_hashes = [], [], {}, {}
    edges = [lo] + bnds + [hi]
    spot_error = None
    for x0, x1 in zip(edges[:-1], edges[1:]):  # 区切りごとに読み、時刻と終値の配列だけを残す(記憶のため)
        try:
            sbars, kk, hh = load_bars(SPOT_DIR, "BTC_JPY", x0, x1)
        except Exception as exc:  # 封印の門(読み込みの検査)が拒んだ: 4-1(4) は出さず、理由を書く
            spot_error = f"{type(exc).__name__}: {exc}"
            break
        spot_hashes.update(hh)
        for k2, v2 in kk.items():
            skinds[k2] = skinds.get(k2, 0) + v2
        st_l.append(np.array([int(x.exchange_time_ns) for x in sbars if x.volume > 0], dtype=np.int64))
        sc_l.append(np.array([float(x.close) for x in sbars if x.volume > 0]))
        del sbars
        gc.collect()
    ov_s = load_reference(ROOT, binance_ref_dataset(OVERSEAS, "close", lo, hi), declarations=decl)
    ov_ser = (np.array(ov_s.times_ns, dtype=np.int64), np.array(ov_s.values))
    fx_ser = (fx_all[0], np.array(fx_all[1]))
    if spot_error is None:
        s_t, s_close = np.concatenate(st_l), np.concatenate(sc_l)
        s_ps, *_ = run_c3.premiums(s_t, s_close, ov_ser[0], ov_ser[1], fx_ser[0], fx_ser[1])
        spot = {"t": s_t, "p": s_ps}
    else:
        spot = {"error": spot_error}
    diag = run_c3.diagnostics(a.window, run, p, spot, ov_ser, fx_ser)
    inputs["spot_bars_for_diagnostic"] = {"files": spot_hashes, "anomalies": skinds, "error": spot_error}
    inputs["binance_for_diagnostic"] = [list(m) for m in ov_s.manifest]
    return diag


def light(a, card, run, log, inputs, clock, t_run, lo, hi, out_root, save_root, name, vdesc, bnds, decl, fx_all) -> int:
    """リードの測り方の変更(2026-10-02): measure_card を打たず、日ごとの系列から軽い測定(daily_stats.py)と軽い診断。"""
    from bot.research.cards.measure import daily_rows, write_daily
    from daily_stats import daily_stats
    outdir = os.path.join(out_root, name)
    p = pnl(run)
    t1 = time.time()
    sha_daily = write_daily(daily_rows(p, "Asia/Tokyo"), os.path.join(outdir, "daily.csv"))
    ds = daily_stats(p.t_ns, p.pnl_bp, run.exposure[run.decided])
    ds["daily_csv_sha256"] = sha_daily
    ds["w4"] = {"variant": vdesc, "period": [to_iso(lo), to_iso(hi)], "chunks": log,
                "note": "measure_card(1 分ごとの系列のブートストラップ・対照・場面の回帰)は打っていない(リードの測り方の変更)"}
    t_ds = time.time() - t1
    t2 = time.time()
    diag = None
    if a.card == "c2":
        from run_c2 import diagnostics as d2
        diag = d2(card, p)
    elif a.card == "c3":
        diag = c3_diag(a, run, p, lo, hi, bnds, decl, fx_all, inputs)
    write_json(ds, os.path.join(outdir, "daily_stats.json"))
    if diag is not None:
        write_json(diag, os.path.join(outdir, "diagnostics.json"))
    t_diag = time.time() - t2
    clock.mark(f"{name}: 日ごとの測定 {t_ds:.0f}s 診断 {t_diag:.0f}s")
    row = {"variant": name, "mode": "light", "overall": ds["overall"], "ci_1d": ds["ci"]["block_1d"],
           "ci_5d": ds["ci"]["block_5d"], "frequency": ds["frequency"],
           "timing": {"chunked_run_s": round(t_run, 1), "daily_s": round(t_ds, 1), "diagnostics_s": round(t_diag, 1),
                      "peak_rss_gb": round(peak_rss_gb(), 2)}}
    write_json({"inputs": inputs, "summary": [row], "clock": clock.marks, "period": [to_iso(lo), to_iso(hi)],
                "chunks": log}, os.path.join(save_root, f"summary_{name}.json"))
    print(json.dumps(row, ensure_ascii=False), flush=True)
    clock.mark("終わり")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", required=True, choices=["c1", "c2", "c3"])
    ap.add_argument("--variant", default="a")
    ap.add_argument("--foot", type=int, default=15)
    ap.add_argument("--window", default="1h")
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--chunk", default="year", choices=["year", "month"])
    ap.add_argument("--out-root", default=None)
    ap.add_argument("--save-root", default=None)
    ap.add_argument("--no-measure", action="store_true")
    ap.add_argument("--from-npz", default=None)
    ap.add_argument("--light", action="store_true")
    a = ap.parse_args()
    clock = Clock()
    if a.card == "c2":
        from bot.research.cards.library import c2_owner_xvenue_wick as M
        card_id = "c2_owner_xvenue_wick"
        attr, ref_dir, ref_file, period, vdesc = C2_VARIANTS[a.variant]
        series = getattr(M, attr)
        name = f"{a.variant}_{a.foot}m"
        card = M.C2OwnerXvenueWick(series=series, foot_min=a.foot)
    elif a.card == "c3":
        from bot.research.cards.library.c3_yen_premium_revert import FX, OVERSEAS, YenPremiumRevert
        card_id = "c3_yen_premium_revert"
        period, vdesc = ("2017-08-17T15:00:00Z", "2022-12-31T15:00:00Z"), f"window {a.window}"
        name = a.window
        card = YenPremiumRevert(a.window)
    else:
        card_id = "c1_xborder_mom"
        period, vdesc, name = ("2017-08-17T15:00:00Z", "2023-12-17T15:00:00Z"), "default(XborderMom() 引数なし)", "default"
    lo, hi = iso(a.start or period[0]), iso(a.end or period[1])
    out_root = a.out_root or os.path.join(ROOT, f"docs/RESEARCH/cards/{card_id}/measure")
    save_root = a.save_root or os.path.join(HERE, "runs", card_id)
    card_md = os.path.join(ROOT, f"docs/RESEARCH/cards/{card_id}/CARD.md")
    with open(card_md, encoding="utf-8") as fh:
        st, problems = cardmd.settings(cardmd.parse(fh.read()))
    if problems:
        raise SystemExit(f"CARD.md の測定の設定が読めない: {problems}")
    decl = dict(st.declarations)
    bnds = boundaries(lo, hi, a.chunk)
    print(f"{card_id} {name} 期間 {to_iso(lo)} 〜 {to_iso(hi)} 区切り {len(bnds)}", flush=True)
    t0 = time.time()
    if a.from_npz:
        from bot.bt.data.reference import parse_decl
        z = np.load(a.from_npz)
        refn = {OVERSEAS: ("ov_time", "ov_value"), FX: ("fx_time", "fx_value")} if a.card == "c3" else {}
        nan = np.full(len(z["end_ns"]), np.nan)
        run = CardRun(card=card.name, venue="bitflyer", symbol="FX_BTC_JPY", start_ns=z["start_ns"], end_ns=z["end_ns"],
                      open=z["open"], high=nan, low=nan, close=z["close"], volume=z["volume"], decided=z["decided"],
                      exposure=z["exposure"], ref_time={n: z[k[0]] for n, k in refn.items()},
                      ref_value={n: z[k[1]] for n, k in refn.items()}, ref_lag_ns={n: 60 * 10**9 for n in refn},
                      ref_decl={n: parse_decl(n, decl[n]).as_dict() for n in refn}, delivery_digest="from_npz")
        log = [{"from_npz": os.path.basename(a.from_npz),
                "note": "区切りごとに読んで run_card に通した記録(同じ手順の 1 回目の起動が、測定の前に保存した npz)から読み直して測った。"
                        "1 回目の起動は測定の後の診断(現物の足の読み込み)で止まった。high・low は保存していない(測定器は使わない)ので NaN"}]
        fx_all = ref_rows(FX, usdjpy_ref_dataset(FX, lo, hi), decl) if a.card == "c3" else None
        inputs = {"bars": {"files": {}, "anomalies": {}}, "references": {}}
        if a.card == "c3":
            inputs["references"][FX] = fx_all[2]
    elif a.card == "c2":
        def mk(n):
            col = n.rsplit("_", 1)[1]
            def load(x, y):
                ds = binance_ref_dataset(n, col, x, y)
                ds["paths"] = paths(ref_dir, ref_file, x, y)
                return ref_rows(n, ds, decl)
            return load
        run, log, inputs = run_carry(card, lo, hi, bnds, decl, {n: mk(n) for n in series}, lag_ns=60 * 10**9,
                                     clock=clock)
    elif a.card == "c3":
        fx_all = ref_rows(FX, usdjpy_ref_dataset(FX, lo, hi), decl)  # 1 ファイル。全期間を 1 回だけ読む

        def load_fx(x, y):
            t, v, _m = fx_all
            i, j = np.searchsorted(t, [x, y], side="left")
            return t[i:j], v[i:j], []

        def load_ov(x, y):
            return ref_rows(OVERSEAS, binance_ref_dataset(OVERSEAS, "close", x, y), decl)
        run, log, inputs = run_carry(card, lo, hi, bnds, decl, {OVERSEAS: load_ov, FX: load_fx}, carry_last=(FX,),
                                     lag_ns=60 * 10**9, clock=clock)
        inputs["references"][FX] = fx_all[2]
    else:
        run, log, inputs = run_c1_chunks(lo, hi, bnds, decl, clock=clock)
    t_run = time.time() - t0
    clock.mark(f"{name}: 区切りの run_card(読み込みを含む) {t_run:.0f}s 決定 {int(run.decided.sum())}")
    os.makedirs(save_root, exist_ok=True)
    tag = f"{name}" if not a.no_measure else f"{name}_{a.chunk}_{to_iso(lo)[:10]}_{to_iso(hi)[:10]}"
    extra = {}
    if a.card == "c2":
        extra["signal_log"] = np.array(card.signal_log, dtype=np.int64).reshape(-1, 4)
    if a.card == "c3":
        extra.update(ov_time=run.ref_time[OVERSEAS], ov_value=run.ref_value[OVERSEAS],
                     fx_time=run.ref_time[FX], fx_value=run.ref_value[FX])
    if not a.from_npz:
        np.savez_compressed(os.path.join(save_root, f"{tag}.npz"), end_ns=run.end_ns, start_ns=run.start_ns, open=run.open,
                            close=run.close, volume=run.volume, decided=run.decided, exposure=run.exposure, **extra)
    if a.no_measure:
        clock.mark("終わり(測定なし)")
        return 0
    if a.light:
        return light(a, card, run, log, inputs, clock, t_run, lo, hi, out_root, save_root, name, vdesc, bnds, decl,
                     fx_all if a.card == "c3" else None)
    outdir = os.path.join(out_root, name)
    t1 = time.time()
    out = measure_card(card_md, run, seed=SEED, control_seed=CONTROL_SEED, regimes=[(lo, REGIME_LABEL)],
                       daily_path=os.path.join(outdir, "daily.csv"))
    t_meas = time.time() - t1
    clock.mark(f"{name}: measure_card {t_meas:.0f}s")
    p = pnl(run)
    t2 = time.time()
    wb = week_block(p.pnl_bp, out, SEED)
    t_week = time.time() - t2
    diag, t_diag = None, 0.0
    t3 = time.time()
    if a.card == "c2":
        from run_c2 import diagnostics as d2
        diag = d2(card, p)
    elif a.card == "c3":
        diag = c3_diag(a, run, p, lo, hi, bnds, decl, fx_all, inputs)
    t_diag = time.time() - t3
    clock.mark(f"{name}: 1 週 {t_week:.0f}s 診断 {t_diag:.0f}s")
    out["w4"] = {"variant": vdesc, "period": [to_iso(lo), to_iso(hi)], "chunks": log,
                 "chunks_note": ("区切りごとにその区切りの分だけを封印の門から読み、run_card に通してつないだ全期間の系列に測定器を "
                                 "1 回当てた(scratchpad の run_v2.py。つなぎ方はその冒頭の説明。全期間を一度に読んだ結果との同一性は check_v2)"),
                 "regimes_note": "W4 の仕様 §3: 期間は全部 SFD の時代。制度の変数は 1 値(期間の始まりから SFD)",
                 "canonical_sha256": canonical_sha({k: v for k, v in out.items() if k != "w4"})}
    if a.card == "c2":
        out["w4"]["foot_min"] = a.foot
    write_json(out, os.path.join(outdir, "measure.json"))
    write_json(wb, os.path.join(outdir, "week_block.json"))
    if diag is not None:
        write_json(diag, os.path.join(outdir, "diagnostics.json"))
    row = summary_row(name, out, wb)
    row["timing"] = {"chunked_run_s": round(t_run, 1), "measure_card_s": round(t_meas, 1),
                     "week_block_s": round(t_week, 1), "diagnostics_s": round(t_diag, 1),
                     "peak_rss_gb": round(peak_rss_gb(), 2)}
    write_json({"inputs": inputs, "summary": [row], "clock": clock.marks, "seed": SEED, "control_seed": CONTROL_SEED,
                "period": [to_iso(lo), to_iso(hi)], "chunks": log},
               os.path.join(save_root, f"summary_{name}.json"))
    print(json.dumps(row, ensure_ascii=False), flush=True)
    clock.mark("終わり")
    return 0


if __name__ == "__main__":
    sys.exit(main())
