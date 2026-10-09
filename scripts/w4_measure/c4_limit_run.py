"""カード 4 段 1: v37 を 1 分足で指値として再現する(仕様 docs/RESEARCH/cards/c4_owner_matilda_range/limit_sim/SPEC.md)の走らせ。

    PYTHONPATH=src python scripts/w4_measure/c4_limit_run.py --fill-side good|bad --out <置き場>
        [--start 2015-11-28T15:00:00Z --end 2023-12-17T15:00:00Z] [族の値: --window-min 40 --entry 2 ...]

探索の窓(--window1、P2-08。common.window_guard の門 = 環境変数 W4_WINDOW1 と承認のファイルが要る。記録は
explore_access_log.jsonl): 読み始め既定 2022-12-18(過去だけの比の門が窓の始まりで前の 365 日を使えるように)、終わり既定・上限
2025-12-12T00:00Z。--measure-from(窓では既定 2023-12-18T00:00Z)より前に出た取引は集計(summary.json)から外し、
trades.csv.gz には in_measure 列(False)を付けて残す(trades.json.gz は集計に入れた取引だけ)。

暦年ごとに足を封印の門(common.load_bars)から読み、同じ再現の物を区切りをまたいで使い続ける(run_b2.run_chunks と
同じ考え)。最後に持っている持ち高は最後の終値で閉じる(終わり方 = 期間の終わり)。

出力(--out):
  trades.csv.gz   取引の行(仕様 4 の列。時刻は UTC の ISO。entry_t = 1 段目が約定した足の終わり、exit_t = 出た足の
                  終わり(時間の成行は閉じた足の始まり))
  summary.json    年ごとの 取引・勝ち・平均の勝ち・平均の負け・勝ちの合計・負けの合計・1 日あたり・決まらない足の数。
                  年 = 出の時刻の暦年(UTC)。年の鍵は、読んだ範囲と重なる暦年と、出の時刻がある暦年の和(期間の終わりの
                  行が範囲の外の年に出ても落とさない)。勝ち = 損益 > 0、負け = 損益 < 0(0 はどちらにも入れない)。
                  1 日あたり = その年の日数(読んだ範囲 [始め, 終わり) と暦年の重なり、24 時間 = 1 日。0 日なら null)で
                  割った 取引の数・勝ちの数・損益。
                  決まらない足の数 = 取引の行の「決まらない足の数」の合計と、それが 1 以上の取引の数。
                  --ratio-gate-mode rolling のときだけ ratio_gate_rolling(日ごとの境の要約: 年ごとの境の最小・中央・最大と、
                  門を掛けなかった日の数。年 = 境の日の UTC の暦年)。
  trades.json.gz  取引の記録(L-D04。src/bot/research/trade_record.py の形。git に入れる)
  run_record.json 引数・期間・区切りごとの足の数・読んだファイルの sha256・異常の種類・所要時間・全体の決まらない足の数。
"""
from __future__ import annotations

import argparse
import csv
import gzip
import math
import os
import statistics
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from common import (DAY_NS, FX_DIR, WINDOW1, WINDOW1_WARMUP_START, Clock, _window_doors, iso, load_bars,  # noqa: E402
                    peak_rss_gb, split_measured, to_iso)
from post import write_json  # noqa: E402
from run_v2 import boundaries  # noqa: E402

from bot.research.matilda_limit_sim import MatildaLimitSim  # noqa: E402
from bot.research.trade_record import write_trades_json  # noqa: E402

FULL = ("2015-11-28T15:00:00Z", "2023-12-17T15:00:00Z")  # 仕様 1(run_b2.FULL と同じ)
COLS = ("entry_t", "exit_t", "side", "levels", "entry_price", "exit_price", "exit_reason", "pnl_pct", "undecided",
        "width", "vola", "ratio", "brk", "close_k")


def _bool(s: str) -> bool:
    if s not in ("True", "False"):
        raise argparse.ArgumentTypeError(f"True / False: {s!r}")
    return s == "True"


def _num(s: str):
    v = float(s)
    return int(v) if v.is_integer() else v


def year_stats(rows: list, days: float) -> dict:
    pn = [r["pnl_pct"] for r in rows]
    wins = [x for x in pn if x > 0]
    losses = [x for x in pn if x < 0]
    und = [r["undecided"] for r in rows]
    return {"trades": len(rows), "wins": len(wins), "losses": len(losses),
            "avg_win_pct": (math.fsum(wins) / len(wins)) if wins else None,
            "avg_loss_pct": (math.fsum(losses) / len(losses)) if losses else None,
            "sum_win_pct": math.fsum(wins), "sum_loss_pct": math.fsum(losses), "sum_pct": math.fsum(pn),
            "days": days,
            "per_day": {"trades": len(rows) / days if days else None, "wins": len(wins) / days if days else None,
                        "pnl_pct": math.fsum(pn) / days if days else None},
            "undecided_bars_in_trades": sum(und), "trades_with_undecided": sum(1 for x in und if x > 0)}


def _year(ns: int) -> int:
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).year


def _year_ns(y: int) -> int:
    return int(datetime(y, 1, 1, tzinfo=timezone.utc).timestamp()) * 10**9


def by_year(rows: list, lo: int, hi: int) -> dict:
    """年(出の時刻の暦年)ごとの year_stats。日数は読んだ範囲 [lo, hi) とその年の重なり。"""
    groups: dict = {}
    for r in rows:
        groups.setdefault(_year(r["exit_ns"]), []).append(r)
    years = set(range(_year(lo), _year(hi - 1) + 1)) | set(groups)
    out = {}
    for y in sorted(years):
        days = max(0, min(hi, _year_ns(y + 1)) - max(lo, _year_ns(y))) / DAY_NS
        out[str(y)] = year_stats(groups.get(y, []), days)
    return out


def rolling_summary(edges: dict, ungated_days: int) -> dict:
    """ratio_gate_mode="rolling" の日ごとの境(日の番号 → 境か None)の要約。年(UTC の暦年)ごとに、足を処理した日の数・
    門を掛けなかった日の数・門を掛けた日の境の最小・中央・最大(無ければ null)。"""
    by_year: dict = {}
    for day, edge in sorted(edges.items()):
        by_year.setdefault(_year(day * DAY_NS), []).append(edge)
    years = {}
    for y, es in by_year.items():
        v = [e for e in es if e is not None]
        years[str(y)] = {"days": len(es), "days_ungated": len(es) - len(v),
                         "edge_min": min(v) if v else None, "edge_median": statistics.median(v) if v else None,
                         "edge_max": max(v) if v else None}
    return {"days": len(edges), "days_ungated": ungated_days, "years": years}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fill-side", required=True, choices=["good", "bad"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--window1", action="store_true", help="探索の窓(2023-12-18〜2025-12-12)の口を通して読む")
    ap.add_argument("--measure-from", default=None, help="これより前に出た取引は集計から外す(窓の既定は 2023-12-18T00:00Z)")
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--window-min", type=int, default=40)
    ap.add_argument("--bar-min", type=int, default=1)
    ap.add_argument("--range-from", default="body")
    ap.add_argument("--entry", type=_num, default=2)
    ap.add_argument("--exit-form", default="v37")
    ap.add_argument("--exit-setting", type=_num, default=None)
    ap.add_argument("--step-exit", type=_num, default=0.8)
    ap.add_argument("--step", type=_num, default=1)
    ap.add_argument("--n-levels", type=int, default=7)
    ap.add_argument("--alert-min", type=int, default=20)
    ap.add_argument("--width-gate", type=_bool, default=True)
    ap.add_argument("--break-delay", type=int, default=1)
    ap.add_argument("--on-break", default="hold")
    ap.add_argument("--ratio-gate", type=float, default=None)  # 族 D 比の門(既定 None = 門なし = v37)
    ap.add_argument("--ratio-gate-mode", default=None)  # 族 D 比の門の境の決め方(既定 None = fixed。rolling = 走らせる前の期間だけから)
    ap.add_argument("--break-close-offset", type=float, default=0.0)  # 族 D 閉じる位置(既定 0 = 判定値 = v37)
    a = ap.parse_args()
    kw = {"fill_side": a.fill_side, "window_min": a.window_min, "bar_min": a.bar_min, "range_from": a.range_from,
          "entry": a.entry, "exit_form": a.exit_form, "exit_setting": a.exit_setting, "step_exit": a.step_exit,
          "step": a.step, "n_levels": a.n_levels, "alert_min": a.alert_min, "width_gate": a.width_gate,
          "break_delay": a.break_delay, "on_break": a.on_break}
    if a.ratio_gate is not None:  # 既定の走らせの summary.json・run_record.json の引数の欄は変えない
        kw["ratio_gate"] = a.ratio_gate
    if a.ratio_gate_mode is not None:  # 同上。--ratio-gate と同時に指定すると表の検査で拒む
        kw["ratio_gate_mode"] = a.ratio_gate_mode
    if a.break_close_offset != 0:
        kw["break_close_offset"] = a.break_close_offset
    sim = MatildaLimitSim(**kw)  # 表の外の値はここで拒む
    clock = Clock()
    WIN = {"window": True} if a.window1 else {}  # 窓のときだけ load_bars・binance_ref_dataset に窓の引数を渡す(既定の呼び方は今までと同じ)
    if a.window1:
        lo, hi = iso(a.start or WINDOW1_WARMUP_START), iso(a.end or to_iso(WINDOW1[1]))
        mf = iso(a.measure_from) if a.measure_from else WINDOW1[0]
        if lo < iso(FULL[0]) or hi > WINDOW1[1] or not (lo <= mf < hi) or mf < WINDOW1[0]:
            raise SystemExit(f"拒否: 窓の期間 読み {to_iso(lo)}〜{to_iso(hi)}・集計の始め {to_iso(mf)} は窓 "
                             f"{to_iso(WINDOW1[0])}〜{to_iso(WINDOW1[1])} の外")
        _window_doors(hi)  # 門が欠けていれば、ここで(何も読む前に)拒む
    else:
        lo, hi = iso(a.start or FULL[0]), iso(a.end or FULL[1])
        mf = iso(a.measure_from) if a.measure_from else None
        if mf is not None and not lo <= mf < hi:
            raise SystemExit(f"拒否: 集計の始め {to_iso(mf)} が期間 {to_iso(lo)}〜{to_iso(hi)} の外")
    edges = [lo] + boundaries(lo, hi, "year") + [hi]
    rows, chunks, files, kinds_all = [], [], {}, {}
    t0 = time.time()
    for x, y in zip(edges[:-1], edges[1:]):
        bars, kinds, h = load_bars(FX_DIR, "FX_BTC_JPY", x, y, **WIN)  # 封印の門(既定は check_end が 2023-12-18 より後を拒む)
        files.update(h)
        for k, v in kinds.items():
            kinds_all[k] = kinds_all.get(k, 0) + v
        n0 = len(rows)
        for b in bars:
            rows += sim.feed(b)
        chunks.append({"range": [to_iso(x), to_iso(y)], "bars": len(bars), "trades_closed": len(rows) - n0})
        clock.mark(f"区切り {to_iso(x)[:10]}〜{to_iso(y)[:10]} 足 {len(bars)} 取引 {len(rows) - n0}")
        del bars
    rows += sim.finish()
    t_run = time.time() - t0
    os.makedirs(a.out, exist_ok=True)
    kept, dropped = split_measured(rows, mf)  # 集計に入れる取引(出の時刻が mf 以上)と外す取引
    with gzip.open(os.path.join(a.out, "trades.csv.gz"), "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLS + (("in_measure",) if mf is not None else ()))
        for r in rows:
            w.writerow([to_iso(r["entry_ns"]), to_iso(r["exit_ns"]), r["side"], r["levels"], repr(r["entry_price"]),
                        repr(r["exit_price"]), r["exit_reason"], repr(r["pnl_pct"]), r["undecided"],
                        repr(r["width"]), repr(r["vola"]), repr(r["ratio"]), r["brk"], repr(r["close_k"])]
                       + ([r["exit_ns"] >= mf] if mf is not None else []))
    # 取引の記録(L-D04、L-594。ダッシュボードが読む形。qty = 段の数 / 段の数の上限)。窓では集計に入れた取引だけ(封印の境の検査は窓の終わりまで)
    write_trades_json(os.path.join(a.out, "trades.json.gz"),
                      ({"entry_t_ns": r["entry_ns"], "entry_px": r["entry_price"], "exit_t_ns": r["exit_ns"],
                        "exit_px": r["exit_price"], "side": r["side"], "qty": r["levels"] / sim.n_levels,
                        "pnl_pct": r["pnl_pct"]} for r in kept),
                      **({"seal_start_ns": WINDOW1[1]} if a.window1 else {}))
    lo_s = lo if mf is None else mf  # 集計の始め(日数は集計の期間で数える)
    years = by_year(kept, lo_s, hi)
    reasons: dict = {}
    for r in kept:
        reasons[r["exit_reason"]] = reasons.get(r["exit_reason"], 0) + 1
    summary = {"params": kw, "period": [to_iso(lo_s), to_iso(hi)], "years": years,
               "all": year_stats(kept, (hi - lo_s) / DAY_NS), "exit_reasons": reasons,
               "undecided_bars_total": sim.undecided_bars}
    if mf is not None:
        summary["measure"] = {"read_from": to_iso(lo), "measure_from": to_iso(mf), "window1": a.window1}
    if sim.ratio_gate_mode == "rolling":
        if mf is None:
            summary["ratio_gate_rolling"] = rolling_summary(sim.rolling_edges, sim.ungated_days)
        else:  # 集計の始めより前の日(門の慣らしの日)は要約に入れない
            ed = {d: e for d, e in sim.rolling_edges.items() if d * DAY_NS >= mf}
            summary["ratio_gate_rolling"] = rolling_summary(ed, sum(1 for e in ed.values() if e is None))
    write_json(summary, os.path.join(a.out, "summary.json"))
    record = {"params": kw, "period": [to_iso(lo), to_iso(hi)], "chunks": chunks,
              "inputs": {"bars": {"files": files, "anomalies": kinds_all}},
              "timing": {"run_s": round(t_run, 1), "total_s": round(time.time() - clock.t0, 1),
                         "peak_rss_gb": round(peak_rss_gb(), 2)},
              "trades": len(rows), "undecided_bars_total": sim.undecided_bars, "clock": clock.marks}
    if mf is not None:  # 集計から外した取引の数は記録に残す(外した取引の行は trades.csv.gz の in_measure = False)
        record["measure"] = {"read_from": to_iso(lo), "measure_from": to_iso(mf), "trades_excluded": len(dropped),
                             "trades_in_measure": len(kept),
                             "trades_in_measure_entered_before": sum(1 for r in kept if r["entry_ns"] < mf)}
    write_json(record, os.path.join(a.out, "run_record.json"))
    clock.mark(f"終わり 取引 {len(rows)} 走らせ {t_run:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
