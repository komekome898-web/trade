"""カード 2: katsuo_v03 の指値の形を 1 分足で再現する(仕様 docs/RESEARCH/cards/c2_owner_xvenue_wick/limit_sim/SPEC.md)の走らせ。

    PYTHONPATH=src python scripts/w4_measure/c2_limit_run.py --series a|b --foot-min 15 --at-max skip|flip
        --fill-side good|bad --out <置き場> [--start 2017-08-17T15:00:00Z --end 2023-12-17T15:00:00Z]
    (仕様 9) ... --design k1 --entry a|b|c [--side-keep weak|strong] [--vol-gate] --fill-side good|bad --out <置き場>
        design=k1 では --at-max を渡さない。三分位の境目は K1 の出力 results/PHASE2/K1/xvenue/vol_terciles.json の
        feet[足].edges_bp_own(measure_katsuo_xvenue.py --vol-terciles の (2) の列)から読む。その足の境目が無ければ、
        --vol-gate のときは止める(作らない)。門なしのときは三分位の列を空にする。
        --fill limit(既定)|close。close は参照の形(行動の時刻の直前の bitFlyer の終値で必ず約定。design=k1 だけ)。
        design=k1・--fill limit では、同じ入力に --fill close の物を並走させ、取り逃しを数える(下の missed.csv.gz)。
        --fill limit_entry_close_exit(入りは指値・降りるは終値)|close_entry_limit_exit(入りは終値・降りるは 4 本)は
        参照との差を入りと降りに分ける形(design=k1 だけ)。取り逃しは入りが指値の limit_entry_close_exit でも数える。

暦年ごとに、その区切りの参照の行(海外の 1 分足の 4 本値。カード 2 の測定 run_v2.py の c2 と同じ置き場・同じ
binance_ref_dataset・同じ load_reference と CARD.md の宣言)と bitFlyer の足(common.load_bars、封印の門)を読み、
同じ再現の物を区切りをまたいで使い続ける。区切りごとに参照の行を先に渡し、その後で足を渡す(再現は使える時刻が
来るまで行を持ち越す)。最後に持っている持ち高は最後の終値で閉じる(終わり方 = 期間の終わり)。

出力(--out):
  trades.json.gz  取引の記録(L-D04。src/bot/research/trade_record.py の形。git に入れる)
  trades.csv.gz   取引の行(仕様 5 の列。時刻は UTC の ISO。entry_t = 最初の約定の足の終わり、exit_t = 出た約定の足の
                  終わり、signal_t = 取引を始めた注文を出した時刻 T、strength = その合図の強い / 弱い、
                  exit_signal / exit_signal_t = 降りる注文を出した理由と時刻(降りる注文で閉じた取引だけ))
  summary.json    年ごとの 取引・勝ち・負け・平均の勝ち・平均の負け・勝ちの合計・負けの合計・1 日あたり・決まらない足の数・
                  終わり方の内訳・入りの注文の約定の割合と約定までの時間。年 = 取引は出の時刻の暦年(UTC)、注文は出した
                  時刻の暦年。仕様 8-2: 入りの合図の強い / 弱いで分けた表(by_strength)と、降りる注文を出した理由
                  (反対の弱い合図 / ヒゲ先端を終値で越えた)ごとの件数・損益の合計(by_exit_signal)。勝ち = 損益 > 0、負け = 損益 < 0(0 はどちらにも入れない)。1 日あたり = その年の期間の日数
                  (読んだ範囲と暦年の重なり、24 時間 = 1 日)で割った 取引の数・勝ちの数・損益。
  missed.csv.gz   (design=k1・--fill limit / limit_entry_close_exit)取り逃し = 並走させた参照の形(fill="close")で建った取引のうち、指値の形に
                  同じ合図の時刻(signal_t)の取引が無いもの。列は参照の形の取引の行と、limit_order_placed(指値の
                  形がその合図で注文を出したか。False は持ち高・残っていた注文のせいで注文自体を出していない)。
                  summary の years[年].missed(年 = 合図の時刻の暦年)。
  summary.json の years[年] には、取引ごとの vol_prev の三分位で分けた表(by_vol_tercile)と印も入れる:
    vol_tercile_lookahead = 2018 年より前(門の有無に関係なく。三分位の境目は 2018〜2019 年の取引で決めたので、
      2017 年の三分位の表は後の期間の情報を使っている。先読みあり)
    vol_gate_lookahead = 門ありで 2018 年より前(門の判定そのものが先読みあり)
    vol_gate_in_sample = 門ありで 2018〜2019 年(境目を決めた期間の中)
  all(全期間)に加えて all_2018on(出の時刻・注文・合図が 2018 年以降の分だけの合計。1 日あたりの日数も 2018-01-01
  以降)を出す。
  run_record.json 引数・期間・区切りごとの足と参照の行の数・読んだファイルの sha256・異常の種類・所要時間・判定の数。
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import os
import statistics
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from common import (DAY_NS, FX_DIR, MIN_NS, ROOT, Clock, binance_ref_dataset, iso, load_bars, paths,  # noqa: E402
                    peak_rss_gb, to_iso)
from post import write_json  # noqa: E402
from run_v2 import C2_VARIANTS, boundaries, ref_rows  # noqa: E402

from bot.research.cards import cardmd  # noqa: E402
from bot.research.cards.library import c2_owner_xvenue_wick as C2  # noqa: E402
from bot.research.katsuo_limit_sim import STRONG, WEAK, XSIG_LINE, XSIG_WEAK, KatsuoLimitSim  # noqa: E402
from bot.research.trade_record import write_trades_json  # noqa: E402

Y2018_NS = 1_514_764_800 * 1_000_000_000  # 2018-01-01T00:00:00Z

END_MAX = "2023-12-17T15:00:00Z"  # 仕様 1「期間の終わり 2023-12-17T15:00Z」
SERIES_ARGS = ("a", "b")  # 仕様 1: (c) BitMEX は使わない(L-570)
COLS = ("entry_t", "exit_t", "side", "max_size", "entry_price", "exit_price", "exit_reason", "pnl_bp", "undecided",
        "small", "big", "r", "signal_t", "strength", "exit_signal", "exit_signal_t", "h1", "vol_prev", "vol_tercile")
CARD_MD = os.path.join(ROOT, "docs/RESEARCH/cards/c2_owner_xvenue_wick/CARD.md")
VOL_TERCILES = os.path.join(ROOT, "results/PHASE2/K1/xvenue/vol_terciles.json")  # K1 の出力(読むだけ)
VOL_TRAIN_YEARS = (2018, 2019)  # vol_terciles.json の edges_train_years(読んで照合する)


def vol_edges(foot: int):
    """(境目, 出所の記録)。ファイル・足の境目が無ければ (None, 理由)。"""
    if not os.path.exists(VOL_TERCILES):
        return None, f"{VOL_TERCILES} が無い"
    with open(VOL_TERCILES, encoding="utf-8") as fh:
        d = json.load(fh)
    if tuple(d.get("edges_train_years", ())) != VOL_TRAIN_YEARS or d.get("signal_source") != "binance":
        return None, f"{VOL_TERCILES} の edges_train_years / signal_source が想定と違う"
    e = d.get("feet", {}).get(str(foot), {}).get("edges_bp_own")
    if not e:
        return None, f"{VOL_TERCILES} に足 {foot} 分の edges_bp_own が無い"
    return (float(e[0]), float(e[1])), {"file": os.path.relpath(VOL_TERCILES, ROOT), "foot": foot,
                                        "edges_bp_own": e, "design": d.get("design"), "gate": d.get("gate")}


def tercile_stats(rows: list) -> dict:
    out = {}
    for k in ("low", "mid", "high", None):
        xs = [r["pnl_bp"] for r in rows if r["vol_tercile"] == k]
        out[k or "値なし"] = {"trades": len(xs), "wins": sum(1 for x in xs if x > 0),
                             "losses": sum(1 for x in xs if x < 0), "sum_bp": math.fsum(xs),
                             "avg_bp": math.fsum(xs) / len(xs) if xs else None}
    return out


def find_missed(rows_limit: list, rows_close: list, order_log_limit: list) -> list:
    """取り逃し = 参照の形の取引のうち、指値の形に同じ合図の時刻の取引が無いもの(再現のモジュールの説明)。"""
    have = {r["signal_ns"] for r in rows_limit}
    placed = {x[5] for x in order_log_limit}
    return [dict(r, limit_order_placed=r["signal_ns"] in placed) for r in rows_close if r["signal_ns"] not in have]


def missed_stats(ms: list) -> dict:
    def one(xs):
        return {"trades": len(xs), "sum_bp": math.fsum(xs), "avg_bp": math.fsum(xs) / len(xs) if xs else None,
                "wins": sum(1 for x in xs if x > 0), "losses": sum(1 for x in xs if x < 0)}
    out = one([m["pnl_bp"] for m in ms])
    out["limit_order_placed"] = one([m["pnl_bp"] for m in ms if m["limit_order_placed"]])
    out["limit_order_not_placed"] = one([m["pnl_bp"] for m in ms if not m["limit_order_placed"]])
    return out


def _yr(ns: int) -> int:
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).year


def block_stats(rows: list, order_log: list, missed, days: float, vol_gate: bool, lookahead: bool,
                in_sample: bool) -> dict:
    st = year_stats(rows, days)
    st.update(split_stats(rows))
    st["entry_orders"] = order_stats(order_log)
    st["by_vol_tercile"] = tercile_stats(rows)
    st["vol_tercile_lookahead"] = lookahead
    st["vol_gate_lookahead"] = vol_gate and lookahead
    st["vol_gate_in_sample"] = vol_gate and in_sample
    if missed is not None:
        st["missed"] = missed_stats(missed)
    return st


def build_summary(rows: list, order_log: list, missed, lo: int, hi: int, edges: list, vol_gate: bool) -> dict:
    """年ごと(edges の区切り)・all・all_2018on の表。取引は出の時刻、注文は出した時刻、取り逃しは合図の時刻の暦年。"""
    t1, t2 = VOL_TRAIN_YEARS
    years = {}
    for x, y in zip(edges[:-1], edges[1:]):
        k = _yr(x)
        years[str(k)] = block_stats([r for r in rows if _yr(r["exit_ns"]) == k],
                                    [o for o in order_log if _yr(o[1]) == k],
                                    None if missed is None else [m for m in missed if _yr(m["signal_ns"]) == k],
                                    (y - x) / DAY_NS, vol_gate, k < t1, t1 <= k <= t2)
    allst = block_stats(rows, order_log, missed, (hi - lo) / DAY_NS, vol_gate, _yr(lo) < t1,
                        _yr(lo) <= t2 and _yr(hi - 1) >= t1)
    lo2 = max(lo, Y2018_NS)
    on = block_stats([r for r in rows if r["exit_ns"] >= Y2018_NS], [o for o in order_log if o[1] >= Y2018_NS],
                     None if missed is None else [m for m in missed if m["signal_ns"] >= Y2018_NS],
                     max(0, hi - lo2) / DAY_NS, vol_gate, False, _yr(lo2) <= t2 and hi > lo2)
    return {"years": years, "all": allst, "all_2018on": on}


def year_stats(rows: list, days: float) -> dict:
    pn = [r["pnl_bp"] for r in rows]
    wins = [x for x in pn if x > 0]
    losses = [x for x in pn if x < 0]
    und = [r["undecided"] for r in rows]
    reasons: dict = {}
    for r in rows:
        reasons[r["exit_reason"]] = reasons.get(r["exit_reason"], 0) + 1
    return {"trades": len(rows), "wins": len(wins), "losses": len(losses),
            "avg_win_bp": (math.fsum(wins) / len(wins)) if wins else None,
            "avg_loss_bp": (math.fsum(losses) / len(losses)) if losses else None,
            "sum_win_bp": math.fsum(wins), "sum_loss_bp": math.fsum(losses), "sum_bp": math.fsum(pn),
            "days": days,
            "per_day": {"trades": len(rows) / days if days else None, "wins": len(wins) / days if days else None,
                        "pnl_bp": math.fsum(pn) / days if days else None},
            "undecided_bars_in_trades": sum(und), "trades_with_undecided": sum(1 for x in und if x > 0),
            "exit_reasons": reasons}


def split_stats(rows: list) -> dict:
    """仕様 8-2: 入りの合図の強い / 弱いごとの year_stats と、降りる注文を出した理由ごとの 件数・損益の合計・勝ち・負け。"""
    by_strength = {k: year_stats([r for r in rows if r["strength"] == k], 0.0) for k in (STRONG, WEAK)}
    for v in by_strength.values():
        v.pop("days"), v.pop("per_day")
    by_xsig = {}
    for k in (XSIG_WEAK, XSIG_LINE, None):
        xs = [r["pnl_bp"] for r in rows if r["exit_signal"] == k]
        by_xsig[k or "降りる注文以外(ドテン・期間の終わり)"] = {
            "trades": len(xs), "sum_bp": math.fsum(xs), "wins": sum(1 for x in xs if x > 0),
            "losses": sum(1 for x in xs if x < 0), "avg_bp": math.fsum(xs) / len(xs) if xs else None}
    return {"by_strength": by_strength, "by_exit_signal": by_xsig}


def order_stats(log: list) -> dict:
    """入りの注文の 1 本目・2 本目ごとの 出した数・約定した数・割合・約定までの分(足の終わり − 出した時刻)。"""
    out = {}
    for kind in ("ent1", "ent2"):
        xs = [x for x in log if x[0] == kind]
        waits = [(x[3] - x[1]) / MIN_NS for x in xs if x[3] is not None]
        out[kind] = {"placed": len(xs), "filled": len(waits), "fill_ratio": len(waits) / len(xs) if xs else None,
                     "wait_min_mean": statistics.fmean(waits) if waits else None,
                     "wait_min_median": statistics.median(waits) if waits else None}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", default="a", choices=list(SERIES_ARGS))
    ap.add_argument("--foot-min", type=int, default=C2.FOOT_MIN)
    ap.add_argument("--at-max", default=None, choices=["skip", "flip"])
    ap.add_argument("--design", default="v03", choices=["v03", "k1"])
    ap.add_argument("--entry", default="c", choices=["a", "b", "c"])
    ap.add_argument("--side-keep", default="weak", choices=["weak", "strong"])
    ap.add_argument("--vol-gate", action="store_true")
    ap.add_argument("--fill", default="limit",
                    choices=["limit", "close", "limit_entry_close_exit", "close_entry_limit_exit"])
    ap.add_argument("--fill-side", required=True, choices=["good", "bad"])
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    attr, ref_dir, ref_file, period, vdesc = C2_VARIANTS[a.series]
    series = getattr(C2, attr)
    edges_v, edges_src = vol_edges(a.foot_min)
    if a.vol_gate and edges_v is None:
        raise SystemExit(f"止める: 高ボラの門の境目が K1 の出力に無い({edges_src})。境目は作らない(仕様 9)")
    kw = {"fill_side": a.fill_side, "at_max": a.at_max, "foot_min": a.foot_min, "design": a.design,
          "entry": a.entry, "side_keep": a.side_keep, "vol_gate": a.vol_gate, "vol_edges": edges_v, "fill": a.fill}
    sim = KatsuoLimitSim(**kw)  # 表の外の値はここで拒む
    shadow = (KatsuoLimitSim(**dict(kw, fill="close"))
              if (a.design == "k1" and a.fill in ("limit", "limit_entry_close_exit")) else None)
    rows_close: list = []
    lo, hi = iso(a.start or period[0]), iso(a.end or period[1])
    if lo < iso(period[0]) or hi > iso(period[1]) or hi > iso(END_MAX) or lo >= hi:
        raise SystemExit(f"拒否: 期間 {to_iso(lo)}〜{to_iso(hi)} は変種 ({a.series}) の期間 {period} の外")
    with open(CARD_MD, encoding="utf-8") as fh:
        st, problems = cardmd.settings(cardmd.parse(fh.read()))
    if problems:
        raise SystemExit(f"CARD.md の測定の設定が読めない: {problems}")
    decl = dict(st.declarations)
    clock = Clock()
    edges = [lo] + boundaries(lo, hi, "year") + [hi]
    rows, chunks, bar_files, kinds_all, ref_man = [], [], {}, {}, {n: [] for n in series}
    t0 = time.time()
    for x, y in zip(edges[:-1], edges[1:]):
        cols = []
        for n in series:  # run_v2.py の c2 の mk(n) と同じ読み方
            ds = binance_ref_dataset(n, n.rsplit("_", 1)[1], x, y)
            ds["paths"] = paths(ref_dir, ref_file, x, y)
            tt, vv, man = ref_rows(n, ds, decl)
            ref_man[n] += man
            cols.append((tt.tolist(), vv))
        ts = cols[0][0]
        if any(c[0] != ts for c in cols):
            raise SystemExit(f"4 本値の参照の行の時刻が揃わない {[len(c[0]) for c in cols]}")
        sim.add_refs(zip(ts, *(c[1] for c in cols)))
        if shadow is not None:
            shadow.add_refs(zip(ts, *(c[1] for c in cols)))
        bars, kinds, h = load_bars(FX_DIR, "FX_BTC_JPY", x, y)  # 封印の門(check_end で 2023-12-18 より後を拒む)
        bar_files.update(h)
        for k, v in kinds.items():
            kinds_all[k] = kinds_all.get(k, 0) + v
        n0 = len(rows)
        for b in bars:
            rows += sim.feed(b)
            if shadow is not None:
                rows_close += shadow.feed(b)
        chunks.append({"range": [to_iso(x), to_iso(y)], "bars": len(bars), "ref_rows": len(ts),
                       "trades_closed": len(rows) - n0})
        clock.mark(f"区切り {to_iso(x)[:10]}〜{to_iso(y)[:10]} 足 {len(bars)} 参照 {len(ts)} 取引 {len(rows) - n0}")
        del bars, cols, ts
    rows += sim.finish()
    if shadow is not None:
        rows_close += shadow.finish()
    t_run = time.time() - t0
    os.makedirs(a.out, exist_ok=True)
    with gzip.open(os.path.join(a.out, "trades.csv.gz"), "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLS)
        for r in rows:
            w.writerow([to_iso(r["entry_ns"]), to_iso(r["exit_ns"]), r["side"], repr(r["max_size"]),
                        repr(r["entry_price"]), repr(r["exit_price"]), r["exit_reason"], repr(r["pnl_bp"]),
                        r["undecided"], r["small"], r["big"], repr(r["r"]), to_iso(r["signal_ns"]), r["strength"],
                        r["exit_signal"] or "",
                        to_iso(r["exit_signal_ns"]) if r["exit_signal_ns"] is not None else "", r["h1"],
                        "" if r["vol_prev"] is None else repr(r["vol_prev"]), r["vol_tercile"] or ""])
    # 取引の記録(L-D04、L-594。ダッシュボードが読む形。qty = その取引の最大の持ち高)
    write_trades_json(os.path.join(a.out, "trades.json.gz"),
                      ({"entry_t_ns": r["entry_ns"], "entry_px": r["entry_price"], "exit_t_ns": r["exit_ns"],
                        "exit_px": r["exit_price"], "side": r["side"], "qty": r["max_size"],
                        "pnl_bp": r["pnl_bp"]} for r in rows))
    ms = find_missed(rows, rows_close, sim.order_log) if shadow is not None else None
    if ms is not None:
        with gzip.open(os.path.join(a.out, "missed.csv.gz"), "wt", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(("signal_t", "side", "entry_t", "exit_t", "entry_price", "exit_price", "pnl_bp", "vol_tercile",
                        "limit_order_placed"))
            for m in ms:
                w.writerow([to_iso(m["signal_ns"]), m["side"], to_iso(m["entry_ns"]), to_iso(m["exit_ns"]),
                            repr(m["entry_price"]), repr(m["exit_price"]), repr(m["pnl_bp"]), m["vol_tercile"] or "",
                            m["limit_order_placed"]])
    summary = {"params": dict(kw, series=a.series, series_desc=vdesc, series_names=list(series),
                              vol_edges_source=edges_src),
               "period": [to_iso(lo), to_iso(hi)], **build_summary(rows, sim.order_log, ms, lo, hi, edges, a.vol_gate),
               "close_shadow_trades": None if shadow is None else len(rows_close),
               "undecided_bars_total": sim.undecided_bars, "decisions": sim.decisions,
               "signals": len(sim.signal_log)}
    write_json(summary, os.path.join(a.out, "summary.json"))
    record = {"params": summary["params"], "period": summary["period"], "chunks": chunks,
              "inputs": {"bars": {"files": bar_files, "anomalies": kinds_all}, "references": ref_man,
                         "declarations": {n: decl.get(n) for n in series}},
              "timing": {"run_s": round(t_run, 1), "total_s": round(time.time() - clock.t0, 1),
                         "peak_rss_gb": round(peak_rss_gb(), 2)},
              "trades": len(rows), "undecided_bars_total": sim.undecided_bars, "decisions": sim.decisions,
              "clock": clock.marks}
    write_json(record, os.path.join(a.out, "run_record.json"))
    clock.mark(f"終わり 取引 {len(rows)} 走らせ {t_run:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
