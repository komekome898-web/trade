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
        --k1-stop-k <k>(値段で降りる)/ --k1-time-exit-bars <N>(時間で降りる)は長い保有の降り方(既定は切。
        --design k1 --entry a --fill close だけ。中身は再現のモジュールの説明「長い保有の降り方」)。
    参照の行(合図の足の元)の読み方の切り替え(既定はどちらも切 = 今までと同じ。段階 G のデータの扱いに合わせて原因を
    確かめるためのもの。limit_sim/runs/READ_K1YEAR/CAUSE.md):
        --ref-join-bitflyer   (a) 内部結合: 参照の行のうち、その分(open_time を分の頭に切り下げた時刻)に bitFlyer の
                              足(4 本値のある行 = load_bars の後の足。出来高 0 の足も含む)がある行だけを使う。
                              段階 G の結合(分の頭に切り下げ、分の開始時刻の積集合)と同じ分を残す。
        --ref-drop-no-trade   (b) Binance の n_trades == 0 の行を落とす。n_trades は参照の行と同じファイルの
                              n_trades の列を open_time で引く(参照の行の時刻と 1 対 1 に揃わなければ止める)。
        切り替えは参照の形(並走の fill="close" の物)にも同じに当てる。落とした行の数は run_record.json の
        区切りごとの ref_rows_dropped_join・ref_rows_dropped_no_trade、summary.json の params.ref_filter に出す
        (切り替えが 1 つでも入のときだけ。既定の出力は今までと同じ形)。

探索の窓(--window1、P2-08。common.window_guard の門 = 環境変数 W4_WINDOW1 と承認のファイルが要る。記録は
explore_access_log.jsonl): 系列 (a) だけ。読み始め既定 2022-12-18、終わり既定・上限 2025-12-12T00:00Z(判定の期間は読めない)。
参照の行は 2023 年分を今の置き場、2024 年以降を単一のファイルから読む。--measure-from(窓では既定 2023-12-18T00:00Z)より前に
出た取引は集計(summary.json)から外し、trades.csv.gz には in_measure 列(False)を付けて残す(trades.json.gz は集計に入れた取引だけ)。
--ref-drop-no-trade とは併用できない(その読みは窓の口を通らないため)。

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

from common import (DAY_NS, FX_DIR, MIN_NS, ROOT, WINDOW1, WINDOW1_UNIT, WINDOW1_WARMUP_START, Clock, _window_doors,  # noqa: E402
                    binance_ref_dataset, iso, load_bars, paths, peak_rss_gb, split_measured, to_iso, window_guard,
                    window_trim_report)
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


def binance_n_trades(paths_abs: list, lo_ns: int, hi_ns: int) -> dict:
    """Binance の 1 分足のファイル(参照の行と同じもの)から {open_time ns: n_trades}。lo <= t < hi の行だけ。
    行は時刻の順なので、hi 以上の行に来たらそのファイルは読むのを止める(封印の境より後の行の値を読まない)。"""
    out = {}
    for p in paths_abs:
        with gzip.open(p, "rt", encoding="utf-8", newline="") as fh:
            r = csv.reader(fh)
            head = next(r)
            if head[0] != "open_time" or "n_trades" not in head:
                raise SystemExit(f"{p} の見出しに open_time・n_trades が無い: {head}")
            k = head.index("n_trades")
            for row in r:
                t = iso(row[0])
                if t >= hi_ns:
                    break
                if t >= lo_ns:
                    out[t] = int(row[k])
    return out


def filter_ref_rows(ts: list, vals: list, *, join: bool, drop_no_trade: bool, bar_starts=None, n_trades=None):
    """参照の行の切り替え(モジュールの説明)。ts = 参照の行の時刻(ns)、vals = 4 本値の列(各 ts と同じ長さ)。
    join: bar_starts(bitFlyer の足の始まり ns の集合)に、行の時刻を分の頭に切り下げた時刻がある行だけ残す。
    drop_no_trade: n_trades({時刻: n_trades})が 0 の行を落とす(時刻が n_trades に無ければ止める)。
    (残した ts, 残した vals, 結合で落とした数, n_trades == 0 で落とした数)。結合を先に見る。"""
    if not join and not drop_no_trade:
        return ts, vals, 0, 0
    if drop_no_trade:
        missing = [t for t in ts if t not in n_trades]
        if missing:
            raise SystemExit(f"参照の行 {len(missing)} 行の時刻に n_trades が無い(最初 {to_iso(missing[0])})")
    keep, dj, dn = [], 0, 0
    for i, t in enumerate(ts):
        if join and (t - t % MIN_NS) not in bar_starts:
            dj += 1
            continue
        if drop_no_trade and n_trades[t] == 0:
            dn += 1
            continue
        keep.append(i)
    return [ts[i] for i in keep], [[v[i] for i in keep] for v in vals], dj, dn


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
    extra = sorted({r["exit_signal"] for r in rows} - {XSIG_WEAK, XSIG_LINE, None})  # 値段で降りる・時間で降りる
    for k in (XSIG_WEAK, XSIG_LINE, *extra, None):
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
    ap.add_argument("--vol-gate-mode", default="fixed", choices=["fixed", "rolling"],
                    help="fixed = K1 の境目(2018〜2019 年)/ rolling = 直前 365 日の合図の上位 3 分の 1(L-619)")
    ap.add_argument("--fill", default="limit",
                    choices=["limit", "close", "limit_entry_close_exit", "close_entry_limit_exit"])
    ap.add_argument("--fill-side", required=True, choices=["good", "bad"])
    ap.add_argument("--k1-stop-k", type=float, default=None, help="値段で降りる: 建値から不利に k × vol_prev bp")
    ap.add_argument("--k1-time-exit-bars", type=int, default=None, help="時間で降りる: 建ててから海外の足の区切り N 本")
    ap.add_argument("--ref-join-bitflyer", action="store_true")
    ap.add_argument("--ref-drop-no-trade", action="store_true")
    ap.add_argument("--window1", action="store_true", help="探索の窓(2023-12-18〜2025-12-12)の口を通して読む")
    ap.add_argument("--measure-from", default=None, help="これより前に出た取引は集計から外す(窓の既定は 2023-12-18T00:00Z)")
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    attr, ref_dir, ref_file, period, vdesc = C2_VARIANTS[a.series]
    series = getattr(C2, attr)
    edges_v, edges_src = vol_edges(a.foot_min)
    if a.vol_gate and a.vol_gate_mode == "rolling":
        edges_v, edges_src = None, {"mode": "rolling", "days": 365, "min_signals": 100}
    if a.vol_gate and edges_v is None and a.vol_gate_mode == "fixed":
        raise SystemExit(f"止める: 高ボラの門の境目が K1 の出力に無い({edges_src})。境目は作らない(仕様 9)")
    kw = {"fill_side": a.fill_side, "at_max": a.at_max, "foot_min": a.foot_min, "design": a.design,
          "entry": a.entry, "side_keep": a.side_keep, "vol_gate": a.vol_gate, "vol_edges": edges_v, "fill": a.fill}
    if a.vol_gate:
        kw["vol_gate_mode"] = a.vol_gate_mode
    if a.k1_stop_k is not None:
        kw["k1_stop_k"] = a.k1_stop_k
    if a.k1_time_exit_bars is not None:
        kw["k1_time_exit_bars"] = a.k1_time_exit_bars
    sim = KatsuoLimitSim(**kw)  # 表の外の値はここで拒む
    shadow = (KatsuoLimitSim(**dict(kw, fill="close"))
              if (a.design == "k1" and a.fill in ("limit", "limit_entry_close_exit")) else None)
    rows_close: list = []
    if a.window1:
        if a.series != "a" or a.ref_drop_no_trade:
            raise SystemExit("拒否: --window1 は系列 (a) だけで、--ref-drop-no-trade とは併用できない")
        lo, hi = iso(a.start or WINDOW1_WARMUP_START), iso(a.end or to_iso(WINDOW1[1]))
        mf = iso(a.measure_from) if a.measure_from else WINDOW1[0]
        if lo < iso(period[0]) or hi > WINDOW1[1] or not (lo <= mf < hi) or mf < WINDOW1[0]:
            raise SystemExit(f"拒否: 窓の期間 読み {to_iso(lo)}〜{to_iso(hi)}・集計の始め {to_iso(mf)} は窓 "
                             f"{to_iso(WINDOW1[0])}〜{to_iso(WINDOW1[1])} の外")
        _window_doors(hi)  # 門が欠けていれば、ここで(何も読む前に)拒む
    else:
        lo, hi = iso(a.start or period[0]), iso(a.end or period[1])
        mf = iso(a.measure_from) if a.measure_from else None
        if lo < iso(period[0]) or hi > iso(period[1]) or hi > iso(END_MAX) or lo >= hi or (mf is not None and not lo <= mf < hi):
            raise SystemExit(f"拒否: 期間 {to_iso(lo)}〜{to_iso(hi)} は変種 ({a.series}) の期間 {period} の外")
    with open(CARD_MD, encoding="utf-8") as fh:
        st, problems = cardmd.settings(cardmd.parse(fh.read()))
    if problems:
        raise SystemExit(f"CARD.md の測定の設定が読めない: {problems}")
    decl = dict(st.declarations)
    clock = Clock()
    WIN = {"window": True} if a.window1 else {}  # 窓のときだけ load_bars・binance_ref_dataset に窓の引数を渡す(既定の呼び方は今までと同じ)
    edges = [lo] + boundaries(lo, hi, "year") + [hi]
    rows, chunks, bar_files, kinds_all, ref_man = [], [], {}, {}, {n: [] for n in series}
    filt = a.ref_join_bitflyer or a.ref_drop_no_trade
    filt_tot = {"dropped_join": 0, "dropped_no_trade": 0, "rows_read": 0, "rows_used": 0}
    t0 = time.time()
    for x, y in zip(edges[:-1], edges[1:]):
        cols = []
        if a.window1:
            window_guard(x, y, what="c2_limit_run 参照の行")
        for n in series:  # run_v2.py の c2 の mk(n) と同じ読み方
            ds = binance_ref_dataset(n, n.rsplit("_", 1)[1], x, y, **WIN)
            if not a.window1:
                ds["paths"] = paths(ref_dir, ref_file, x, y)
            tt, vv, man = ref_rows(n, ds, decl, WINDOW1_UNIT if a.window1 else None)
            ref_man[n] += man
            cols.append((tt.tolist(), vv))
        if a.window1:  # 読んだ直後に、判定の期間の行を数えて記録し(値は見ない)、残っていれば止める
            window_trim_report(ds["paths"], "open_time", what="c2_limit_run 参照の行")
            if any(c[0] and max(c[0]) >= WINDOW1[1] for c in cols):
                raise SystemExit("拒否: 参照の行に判定の期間の行が残っている")
        ts = cols[0][0]
        if any(c[0] != ts for c in cols):
            raise SystemExit(f"4 本値の参照の行の時刻が揃わない {[len(c[0]) for c in cols]}")
        bars, kinds, h = load_bars(FX_DIR, "FX_BTC_JPY", x, y, **WIN)  # 封印の門(既定は check_end が 2023-12-18 より後を拒む)
        n_ref_read = len(ts)
        vals = [c[1] for c in cols]
        if filt:
            ntr = (binance_n_trades([os.path.join(ROOT, q) for q in paths(ref_dir, ref_file, x, y)], x, y)
                   if a.ref_drop_no_trade else None)
            ts, vals, dj, dn = filter_ref_rows(ts, vals, join=a.ref_join_bitflyer, drop_no_trade=a.ref_drop_no_trade,
                                               bar_starts={int(b.start_time_ns) for b in bars}, n_trades=ntr)
            del ntr
        sim.add_refs(zip(ts, *vals))
        if shadow is not None:
            shadow.add_refs(zip(ts, *vals))
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
        if filt:
            chunks[-1].update({"ref_rows_read": n_ref_read, "ref_rows_dropped_join": dj,
                               "ref_rows_dropped_no_trade": dn})
            for k, v in (("dropped_join", dj), ("dropped_no_trade", dn), ("rows_read", n_ref_read), ("rows_used", len(ts))):
                filt_tot[k] += v
        clock.mark(f"区切り {to_iso(x)[:10]}〜{to_iso(y)[:10]} 足 {len(bars)} 参照 {len(ts)} 取引 {len(rows) - n0}")
        del bars, cols, ts, vals
    rows += sim.finish()
    if shadow is not None:
        rows_close += shadow.finish()
    t_run = time.time() - t0
    os.makedirs(a.out, exist_ok=True)
    kept, dropped = split_measured(rows, mf)  # 集計に入れる取引(出の時刻が mf 以上)と外す取引
    cols_out = COLS + (("in_measure",) if mf is not None else ())
    with gzip.open(os.path.join(a.out, "trades.csv.gz"), "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols_out)
        for r in rows:
            w.writerow([to_iso(r["entry_ns"]), to_iso(r["exit_ns"]), r["side"], repr(r["max_size"]),
                        repr(r["entry_price"]), repr(r["exit_price"]), r["exit_reason"], repr(r["pnl_bp"]),
                        r["undecided"], r["small"], r["big"], repr(r["r"]), to_iso(r["signal_ns"]), r["strength"],
                        r["exit_signal"] or "",
                        to_iso(r["exit_signal_ns"]) if r["exit_signal_ns"] is not None else "", r["h1"],
                        "" if r["vol_prev"] is None else repr(r["vol_prev"]), r["vol_tercile"] or ""]
                       + ([r["exit_ns"] >= mf] if mf is not None else []))
    # 取引の記録(L-D04、L-594。ダッシュボードが読む形。qty = その取引の最大の持ち高)。窓では集計に入れた取引だけ(封印の境の検査は窓の終わりまで)
    write_trades_json(os.path.join(a.out, "trades.json.gz"),
                      ({"entry_t_ns": r["entry_ns"], "entry_px": r["entry_price"], "exit_t_ns": r["exit_ns"],
                        "exit_px": r["exit_price"], "side": r["side"], "qty": r["max_size"],
                        "pnl_bp": r["pnl_bp"]} for r in kept),
                      **({"seal_start_ns": WINDOW1[1]} if a.window1 else {}))
    ms_all = find_missed(rows, rows_close, sim.order_log) if shadow is not None else None
    ms = None if ms_all is None else split_measured(ms_all, mf, "signal_ns")[0]
    if ms is not None:
        with gzip.open(os.path.join(a.out, "missed.csv.gz"), "wt", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(("signal_t", "side", "entry_t", "exit_t", "entry_price", "exit_price", "pnl_bp", "vol_tercile",
                        "limit_order_placed"))
            for m in ms:
                w.writerow([to_iso(m["signal_ns"]), m["side"], to_iso(m["entry_ns"]), to_iso(m["exit_ns"]),
                            repr(m["entry_price"]), repr(m["exit_price"]), repr(m["pnl_bp"]), m["vol_tercile"] or "",
                            m["limit_order_placed"]])
    order_kept = sim.order_log if mf is None else [o for o in sim.order_log if o[1] >= mf]
    lo_s = lo if mf is None else mf  # 集計の始め(日数・年の区切りは集計の期間で数える)
    edges_s = edges if mf is None else [lo_s] + [e for e in edges[1:] if e > lo_s]
    params = dict(kw, series=a.series, series_desc=vdesc, series_names=list(series), vol_edges_source=edges_src)
    if filt:
        params["ref_filter"] = {"join_bitflyer": a.ref_join_bitflyer, "drop_no_trade": a.ref_drop_no_trade, **filt_tot}
    if mf is not None:
        params["measure_from"] = to_iso(mf)
        params["window1"] = a.window1
    summary = {"params": params,
               "period": [to_iso(lo_s), to_iso(hi)], **build_summary(kept, order_kept, ms, lo_s, hi, edges_s, a.vol_gate and a.vol_gate_mode == "fixed"),
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
    if mf is not None:  # 集計から外した取引の数は記録に残す(外した取引の行は trades.csv.gz の in_measure = False)
        record["measure"] = {"read_from": to_iso(lo), "measure_from": to_iso(mf), "trades_excluded": len(dropped),
                             "trades_in_measure": len(kept),
                             "trades_in_measure_entered_before": sum(1 for r in kept if r["entry_ns"] < mf)}
    write_json(record, os.path.join(a.out, "run_record.json"))
    clock.mark(f"終わり 取引 {len(rows)} 走らせ {t_run:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
