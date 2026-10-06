#!/usr/bin/env python3
"""# 10(D1B_FRAMINGS の行 10、担当 G3)の台本: 1 分足の損益は、約定の側(次の足の始値がどちら側の約定か)と 1 分足の中の
順序の仮定で、どれだけ動くか。データ = bitFlyer FX の約定の記録、封印の前の 6 日(2023 年の 7〜12 月の各 1 日)。

行 10 の言葉と、担う関数:
  「カード 3 の上乗せの合図」「カード 5 の向きが変わった分」「カード 8 の平均をまたいだ分」
      → g3_decisions.run_card_for_day / exposure_decisions / card_decisions_for_day(決定)、read_decision(約定の側・順)
  「カード 4 の入りと利確(良い側・悪い側のどちらの順が当たるか)」「1 分足のシミュレーターと同じ仕様のロジックを約定の記録の上で回す」
      → g3_c4_replay.TradePathMatilda(mode "watch" = 決まらない足ごとの比べ、"replay" = 約定の道で回した損益)、c4_run
  「カード 9 の清算の直後(秒)」 → g3_decisions.liq_prints_for_day / liq_decisions / read_liq_decision
  「1 決定(その分の最初の約定の側・その足の中の高値と安値の順)」 → read_decision・read_liq_decision の列
  「側が半々のときの割合 0.5」 → ratio_stats(割合と 0.5 の差)
  「どれだけ動くか」 → カード 3・5・8・9 は side_bp(g3_decisions.side_bp)の平均、カード 4 は道の損益の差と 1 日の損益
  「6 日で決められるのは割合までで、損益の区間は広い」 → 日の塊の区間をそのまま出す(広く出ても狭めない)。ただし塊(値のある日)が
      6 以下だと、日の塊の区間は狭く出る偏りがある(標本の分散の偏り。およそ √((塊 − 1) / 塊) 倍【推定】。批評家 2 回目)
区間(批評家 1 回目の後のリードの決め): 主 = 日を 1 塊とした区間(値のある日を選び直す、1,000 回、種 20261006)と日ごとの表。
  並べる = 6 日の合計の割合の、決定を独立とみた二項の Wilson の 95% 区間(印:「決定を独立とみた区間。日の依存を入れていないので
  狭く出る」)。前半・後半 = 日数で 2 つ(7〜9 月の 3 日 / 10〜12 月の 3 日)、区間なしで点だけ。年ごとの表は記述(6 日とも 2023 年
  = 合計と同じ)。経費は引かない。カード 3・5・8・9 は各決定に側の差の bp(side_bp)を 1 列足し、型・分けごとに平均と区間を出す
  (決め 7 を取り消し)。カード 4 の割合は 2 通り(A = 選んだ道と同じ ÷ 比べた全部、B = 選んだ道とだけ同じ ÷(選んだ道とだけ同じ
  + もう一方の道とだけ同じ))と、両方と同じ足の数。カード 9 は wait_ms の分位。

使い方(読むだけ。ネットワークなし。出力に時刻・所要時間は入れない):
  件数の数え上げ(損益・値動きを計算しない): PYTHONPATH=src python3 scripts/d1b/g3/g3_run.py --counts
  短い期間の確かめ(1 日、カード 4 の慣らしを短くする): PYTHONPATH=src python3 scripts/d1b/g3/g3_run.py --short 2023-07-01 \
        --c4-start 2023-06-28T00:00:00Z --out <置き場>
  本走らせ: PYTHONPATH=src python3 scripts/d1b/g3/g3_run.py --full
  数え上げの表だけ書き直す(counts.json から。計算しない): PYTHONPATH=src python3 scripts/d1b/g3/g3_run.py --render-counts
出力の既定の置き場: docs/RESEARCH/d1b/10_cards34589/(COUNTS.md・counts.json / TABLES.md・g3.json)。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import g3_decisions as D  # noqa: E402
from g3_c4_replay import TradePathMatilda  # noqa: E402
from g3_trades import DAY_NS, TRADE_FILES, days as trade_days, read_day  # noqa: E402

from bot.research.matilda_limit_sim import MatildaLimitSim  # noqa: E402
from c4_w6b_order import SIM_KW, START as C4_START, wilson  # noqa: E402
from common import FX_DIR, ROOT, iso, load_bars, to_iso  # noqa: E402

OUT_DEFAULT = os.path.join(ROOT, "docs/RESEARCH/d1b/10_cards34589")
C4_END = "2023-12-02T00:00:00Z"  # 6 日目(2023-12-01)の終わり(c4_w6b_order.END と同じ)
C4_CUT = "2023-01-01T00:00:00Z"  # 足を暦年で 2 回に分けて読む(c4_w6b_order と同じ)
SIDES = ("good", "bad")


# ---------------------------------------------------------------- 割合と区間
# 区間(批評家 1 回目の後のリードの決め): 主 = 日を 1 塊とした区間(bot.bt.validation.label_block_bootstrap_ci。値のある日を
# 選び直す、1,000 回、種 20261006、95%)と日ごとの表。並べる = 決定を独立とみた二項の Wilson の 95% 区間(c4_w6b_order.wilson)
SEED, N_BOOT = 20261006, 1000
WILSON_MARK = "決定を独立とみた区間。日の依存を入れていないので狭く出る"


def day_block(values: list, labels: list) -> dict:
    """日を 1 塊とした区間(値のある日だけが塊。塊の中の値は全部入る。統計量は選んだ日の値を合わせた平均)。se と
    MDE = 2.8 × se(2.8 = 1.96 + 0.84: 両側 5%・検出力 80%)。塊が 6 以下だと区間は狭く出る偏りがある。"""
    from bot.bt.validation import ValidationError, label_block_bootstrap_ci
    out = {"ci": None, "se": None, "mde": None, "n_blocks": len(set(labels)), "note": None}
    if len(values) < 2:
        out["note"] = "値が 2 未満"
        return out
    if out["n_blocks"] < 2:
        out["note"] = "区間なし(値のある日が 1 日だけ。日の塊の区間は 2 日以上が要る)"
        return out
    try:
        b = label_block_bootstrap_ci([float(v) for v in values], labels, n_resamples=N_BOOT, seed=SEED, alpha=0.05)
    except ValidationError:
        out["note"] = "区間なし(区間の計算が入力を拒んだ)"
        return out
    out.update(ci=[b.lo, b.hi], se=b.se, mde=2.8 * b.se, n_blocks=b.n_blocks)
    return out


def ratio_stats(vals_by_day: dict, dlist: list) -> dict:
    """vals_by_day: 日 → 真偽の列(None は除いてある)。日ごとの k/n、6 日の割合と 0.5 との差、日の塊の区間(主)、Wilson(並べる)、
    前半・後半の点。"""
    h1, h2 = halves(dlist)
    K = {d: sum(bool(v) for v in vals_by_day.get(d, [])) for d in dlist}
    N = {d: len(vals_by_day.get(d, [])) for d in dlist}
    k, n = sum(K.values()), sum(N.values())
    vals = [1.0 if v else 0.0 for d in dlist for v in vals_by_day.get(d, [])]
    labs = [d for d in dlist for _v in vals_by_day.get(d, [])]

    def pt(ds):
        kk, nn = sum(K[d] for d in ds), sum(N[d] for d in ds)
        return (kk / nn) if nn else None
    return {"per_day": [[K[d], N[d], (K[d] / N[d]) if N[d] else None] for d in dlist], "k": k, "n": n,
            "ratio": (k / n) if n else None, "minus_half": (k / n - 0.5) if n else None,
            "day_block": day_block(vals, labs), "wilson": wilson(k, n), "first_half": pt(h1), "second_half": pt(h2)}


def mean_stats(vals_by_day: dict, dlist: list) -> dict:
    """vals_by_day: 日 → 数の列。日ごとの件数と平均、6 日の平均(値を合わせた平均)、日の塊の区間(主)、前半・後半の点。"""
    h1, h2 = halves(dlist)
    vals = [float(v) for d in dlist for v in vals_by_day.get(d, [])]
    labs = [d for d in dlist for _v in vals_by_day.get(d, [])]

    def mean_of(ds):
        xs = [float(v) for d in ds for v in vals_by_day.get(d, [])]
        return math.fsum(xs) / len(xs) if xs else None
    return {"per_day": [[len(vals_by_day.get(d, [])), mean_of([d])] for d in dlist], "n": len(vals),
            "mean": mean_of(dlist), "day_block": day_block(vals, labs), "first_half": mean_of(h1),
            "second_half": mean_of(h2)}


def quantiles(xs: list) -> dict:
    """分位(numpy の既定の補間): 0・10・25・50・75・90・99・100%。"""
    import numpy as np
    if not xs:
        return {"n": 0}
    q = np.percentile(np.asarray(xs, dtype=float), [0, 10, 25, 50, 75, 90, 99, 100])
    return {"n": len(xs), **{f"p{k}": float(v) for k, v in zip((0, 10, 25, 50, 75, 90, 99, 100), q)}}


def halves(dlist: list) -> tuple:
    h = len(dlist) // 2
    return dlist[:h], dlist[h:]


# ---------------------------------------------------------------- カード 4
def c4_trade_paths(trades: dict) -> dict:
    """6 日の分の始まり → 約定の値段の折り返し点。"""
    out = {}
    for dt in trades.values():
        for m in dt.minutes:
            out[m] = dt.zigzag(m)
    return out


def c4_run(trades: dict, start: str, end: str, modes=("watch", "replay"), counts_only: bool = False) -> dict:
    """カード 4 のシミュレーターを 2 × 2 通り(良い側・悪い側 × watch・replay)流す。counts_only は watch だけ・決まらない足の
    数だけを返す(損益は読まない)。足は start から end まで、暦年の区切りで 2 回に分けて読み、同じ物に続けて流す。"""
    paths = c4_trade_paths(trades)
    sims, logs = {}, {}
    for s in SIDES:
        for m in modes:
            if counts_only:  # 数えるだけ: 1 分足のシミュレーターのまま(約定の道は通さない)。決まらない足の記録の口だけを読む
                logs[s] = []
                sims[(s, m)] = MatildaLimitSim(fill_side=s, undecided_log=logs[s], **SIM_KW)
            else:
                sims[(s, m)] = TradePathMatilda(trade_paths=paths, mode=m, fill_side=s, **SIM_KW)
    rows = {k: [] for k in sims}
    lo, hi = iso(start), iso(end)
    edges = [lo] + ([iso(C4_CUT)] if lo < iso(C4_CUT) < hi else []) + [hi]
    n_bars, kinds_all, hashes = 0, {}, {}
    day_ns = {d: dt.day_ns for d, dt in trades.items()}
    bar_hl = {}
    for a, b in zip(edges[:-1], edges[1:]):
        bars, kinds, h = load_bars(FX_DIR, "FX_BTC_JPY", a, b)
        hashes.update(h)
        for k, v in kinds.items():
            kinds_all[k] = kinds_all.get(k, 0) + v
        n_bars += len(bars)
        for bar in bars:
            st = int(bar.start_time_ns)
            if st in paths:
                bar_hl[st] = (float(bar.high), float(bar.low))
            for k, sim in sims.items():
                rows[k] += sim.feed(bar)
        del bars
    for k, sim in sims.items():
        rows[k] += sim.finish()

    def day_of_ns(t):
        for d, s in day_ns.items():
            if s <= t < s + DAY_NS:
                return d
        return None
    res = {"bars_range": [to_iso(lo), to_iso(hi)], "bars_loaded": n_bars, "bar_anomalies": kinds_all,
           "bar_files": hashes, "sim_kw": SIM_KW, "by_side": {}}
    # 6 日の中の、1 分足と約定の記録の高値・安値の食い違い(W6b の O5 と同じ数え方。除かない)
    mm = {d: {"both": 0, "hl_differ": 0} for d in trades}
    for st, (bh, bl) in bar_hl.items():
        d = day_of_ns(st)
        zz = paths[st]
        mm[d]["both"] += 1
        mm[d]["hl_differ"] += (bh, bl) != (max(zz), min(zz))
    res["bar_vs_trades"] = mm
    for s in SIDES:
        w = sims[(s, "watch")]
        if counts_only:  # 記録の口の行のうち、約定の記録のある分 = 比べられる決まらない足
            comp = [{"start_ns": e["start_ns"], "kind": e["kind"]} for e in logs[s] if paths.get(e["start_ns"])]
        else:
            comp = w.compare
        per = {}
        for d in trades:
            cs = [c for c in comp if day_of_ns(c["start_ns"]) == d]
            per[d] = {"undecided_with_trades": len(cs),
                      "by_kind": {k: sum(1 for c in cs if c["kind"] == k) for k in sorted({c["kind"] for c in comp})}}
            if not counts_only:
                per[d].update({"eq_chosen": sum(c["eq_chosen"] for c in cs), "eq_other": sum(c["eq_other"] for c in cs),
                               "eq_neither": sum(1 for c in cs if not c["eq_chosen"] and not c["eq_other"]),
                               # 両方の数えが同時に真の足(選んだ道ともう一方の道が同じ結果)を別に数え、残りを片方だけに分ける
                               "eq_both": sum(1 for c in cs if c["eq_chosen"] and c["eq_other"]),
                               "eq_chosen_only": sum(1 for c in cs if c["eq_chosen"] and not c["eq_other"]),
                               "eq_other_only": sum(1 for c in cs if c["eq_other"] and not c["eq_chosen"]),
                               "tp_true": sum(c["tp_true"] for c in cs), "tp_chosen": sum(c["tp_chosen"] for c in cs),
                               "value_true_minus_chosen_bp": math.fsum(c["value_true_minus_chosen_bp"] for c in cs),
                               "bar_hl_differ": sum(c["bar_vs_trades_hl_differ"] for c in cs)})
        res["by_side"][s] = {"per_day": per, "undecided_bars_all": w.undecided_bars}
        if counts_only:
            continue
        for m in modes:
            rs = rows[(s, m)]
            res["by_side"][s].setdefault("pnl_per_day_bp", {})[m] = {
                d: math.fsum(r["pnl_bp"] for r in rs if day_of_ns(r["exit_ns"]) == d) for d in trades}
            res["by_side"][s].setdefault("trades_per_day", {})[m] = {
                d: sum(1 for r in rs if day_of_ns(r["exit_ns"]) == d) for d in trades}
        res["by_side"][s]["replayed_bars"] = sims[(s, "replay")].replayed_bars if "replay" in modes else None
        res["by_side"][s]["compare_rows"] = comp
    return res


def c4_ratios(rows: list, day_ns: dict, dlist: list) -> dict:
    """カード 4 の比べの行(watch の compare)から 2 通りの割合。
    A = 選んだ道と同じ(両方と同じを含む)÷ 比べた全部。
    B = 選んだ道とだけ同じ ÷(選んだ道とだけ同じ + もう一方の道とだけ同じ)。両方と同じ足・どちらとも違う足は B に入れない。"""
    dmap = {d: [c for c in rows if day_ns[d] <= c["start_ns"] < day_ns[d] + DAY_NS] for d in dlist}
    return {"eq_chosen": ratio_stats({d: [c["eq_chosen"] for c in cs] for d, cs in dmap.items()}, dlist),
            "chosen_vs_other": ratio_stats({d: [c["eq_chosen"] for c in cs if c["eq_chosen"] != c["eq_other"]]
                                            for d, cs in dmap.items()}, dlist)}


# ---------------------------------------------------------------- カード 3・5・8・9
def card_part(trades: dict, counts_only: bool) -> dict:
    out = {}
    for typ in D.CARD_TYPES:
        per = {}
        for d, dt in trades.items():
            ds = D.card_decisions_for_day(typ, dt.day_ns)
            kinds = {}
            for x in ds:
                kinds[x["kind"]] = kinds.get(x["kind"], 0) + 1
            rec = {"decisions": len(ds), "by_kind": kinds,
                   "with_trades": sum(1 for x in ds if x["fill_ns"] in dt.minutes)}
            if not counts_only:
                rd = [dict(x, **D.read_decision(dt, x["fill_ns"], x["dir"])) for x in ds]
                rec["rows"] = rd
            per[d] = rec
        out[typ] = per
    # カード 9
    per = {}
    for d, dt in trades.items():
        prints, info = D.liq_prints_for_day(d)
        ds = D.liq_decisions(prints)
        rec = {"decisions": len(ds), "load": info,
               "with_trades_one_min": sum(1 for x in ds if ((x["t_ns"] // D.MIN_NS + 1) * D.MIN_NS) in dt.minutes),
               "with_trades_sec": sum(1 for x in ds if dt.first_at_or_after(x["t_ns"]) is not None)}
        if not counts_only:
            rec["rows"] = [dict(x, **D.read_liq_decision(dt, x["t_ns"], x["dir"])) for x in ds]
        per[d] = rec
    out["c9"] = per
    return out


# 型ごとの分け(リードの決め 1・2・5)。最初が主。カード 3 は全部と種類ごと、カード 5・8 は flip を主に open・close を別の行、
# カード 9 は「秒」を主に「1 分」を並べる
GROUPS_C3 = (("all", None), ("flip", "flip"), ("resize", "resize"), ("open", "open"), ("close", "close"))
GROUPS_C58 = (("flip", "flip"), ("open", "open"), ("close", "close"))
GROUPS_C9 = (("sec", "sec"), ("one_min", "one_min"))
KEYS = ("same_side", "dir_first")
# side_bp の待ち(side_wait_ms、ミリ秒)の帯: [下, 上)
WAIT_BANDS = (("1 秒未満", 0.0, 1000.0), ("1〜10 秒", 1000.0, 10000.0), ("10 秒以上", 10000.0, math.inf))


def groups_of(typ: str) -> tuple:
    return GROUPS_C9 if typ == "c9" else GROUPS_C3 if typ.startswith("c3") else GROUPS_C58


def side_tables(part: dict, dlist: list) -> dict:
    """型 × 分けごとに、同じ側の割合(same_side)・向きの側の端が先の割合(dir_first)・側の差の bp(side_bp)を、日ごと・6 日
    (日の塊の区間が主、割合には Wilson を並べる)・前半後半(点)で。カード 9 は「秒」の wait_ms の分位も。"""
    res = {}
    for typ, per in part.items():
        for gname, sel in groups_of(typ):
            rows_by_day = {}
            for d in dlist:
                rows = per[d]["rows"]
                if typ == "c9":
                    rows = [r[sel] for r in rows]
                elif sel is not None:
                    rows = [r for r in rows if r["kind"] == sel]
                rows_by_day[d] = rows
            g = res.setdefault(typ, {}).setdefault(gname, {})
            for key in KEYS:
                g[key] = ratio_stats({d: [r[key] for r in rs if r[key] is not None] for d, rs in rows_by_day.items()}, dlist)
            g["side_bp"] = mean_stats({d: [r["side_bp"] for r in rs if r["side_bp"] is not None]
                                       for d, rs in rows_by_day.items()}, dlist)
            g["side_bp_missing"] = sum(1 for rs in rows_by_day.values() for r in rs if r["side_bp"] is None)
            # 待ち(side_wait_ms)の帯ごとの side_bp と、待ちの分位(批評家 2 回目: 平均に待ちの間の値動きが混ざる)
            g["side_bp_by_wait"] = {band: mean_stats({d: [r["side_bp"] for r in rs if r["side_bp"] is not None
                                                          and lo <= r["side_wait_ms"] < hi] for d, rs in rows_by_day.items()},
                                                     dlist) for band, lo, hi in WAIT_BANDS}
            g["side_wait_ms"] = quantiles([r["side_wait_ms"] for rs in rows_by_day.values() for r in rs
                                           if r["side_bp"] is not None])
            if typ == "c9" and sel == "sec":
                w = [r["wait_ms"] for rs in rows_by_day.values() for r in rs if r["wait_ms"] is not None]
                g["wait_ms"] = {"all": quantiles(w), "per_day": {
                    d: quantiles([r["wait_ms"] for r in rs if r["wait_ms"] is not None]) for d, rs in rows_by_day.items()}}
                g["window_truncated"] = sum(1 for rs in rows_by_day.values() for r in rs if r["window_truncated"])
    return res


# ---------------------------------------------------------------- 表
def f3(x):
    return "—" if x is None else f"{x:.3f}"


def wil_s(r):
    w = r["wilson"]
    return "—" if w is None else f"[{w[0]:.3f}, {w[1]:.3f}]"


def blk_s(r):
    b = r["day_block"]
    return (b["note"] or "—") if b["ci"] is None else f"[{b['ci'][0]:.3f}, {b['ci'][1]:.3f}]({b['n_blocks']} 日)"


def render_counts(c: dict, dlist: list) -> str:
    L = ["# # 10 件数の数え上げ(走らせる前。損益・値動きは計算していない)", "",
         "数はすべて `scripts/d1b/g3/g3_run.py --counts` が出した(手で書いていない)。決定の定義は `scripts/d1b/g3/g3_decisions.py` の"
         "説明(台本の決め)。日 = 約定の分の UTC の日(約定の記録の日)。前半 = " + "・".join(dlist[:3]) + "、後半 = "
         + "・".join(dlist[3:]) + "。年ごと = 6 日とも 2023 年(年ごとの表は全体と同じ)。", "",
         "## カード 3・5・8(1 分足のカードの持ち高が変わった分)", "",
         "分け(リードの決め 1・2): flip = 符号が変わる(反転)、open = 0 → ±、close = ± → 0、resize = 同じ向きの大きさの変化。"
         "カード 3 は全部と種類ごと、カード 5・8 は flip が主(「向きが変わった分」「平均をまたいだ分」)で open・close を別の行。", "",
         "| 型・分け | " + " | ".join(dlist) + " | 合計 | 前半 | 後半 |", "|---|" + "---|" * (len(dlist) + 3)]
    for typ in D.CARD_TYPES:
        per = c["cards"][typ]
        for gname, sel in groups_of(typ):
            v = [per[d]["decisions"] if sel is None else per[d]["by_kind"].get(sel, 0) for d in dlist]
            L.append(f"| {typ}・{gname} | " + " | ".join(map(str, v)) + f" | {sum(v)} | {sum(v[:3])} | {sum(v[3:])} |")
    L += ["", "約定の分に約定がある決定(全部の種類、6 日の合計): "
          + "、".join(f"{t} {sum(c['cards'][t][d]['with_trades'] for d in dlist)}" for t in D.CARD_TYPES)]
    per = c["cards"]["c9"]
    L += ["", "## カード 9(Binance COIN-M BTCUSD_PERP の清算のプリント、一意化の後、その UTC の日の中)", "",
          "| | " + " | ".join(dlist) + " | 合計 | 前半 | 後半 |", "|---|" + "---|" * (len(dlist) + 3)]
    for key, lab in (("decisions", "プリント(決定)"), ("with_trades_sec", "t0 以後に約定がある(「秒」、主)"),
                     ("with_trades_one_min", "「1 分」の分に約定がある(並べる)")):
        v = [per[d][key] for d in dlist]
        L.append(f"| {lab} | " + " | ".join(map(str, v)) + f" | {sum(v)} | {sum(v[:3])} | {sum(v[3:])} |")
    L += ["", "読み込みの件数(日ごと): " + " / ".join(f"{d} 読んだ {per[d]['load']['read']}・日の中 {per[d]['load']['in_day']}"
                                               for d in dlist)]
    c4 = c["c4"]
    L += ["", "## カード 4(1 分足のシミュレーターの決まらない足のうち、約定の記録がある分)", "",
          f"- 形: `MatildaLimitSim(fill_side=…, " + ", ".join(f"{k}={v!r}" for k, v in SIM_KW.items()) + ")`"
          f"(c4_w6b_order.SIM_KW を import)。足 {c4['bars_range'][0]} 〜 {c4['bars_range'][1]}、読んだ足 {c4['bars_loaded']} 本。",
          "", "| 側 | " + " | ".join(dlist) + " | 合計 | 前半 | 後半 |", "|---|" + "---|" * (len(dlist) + 3)]
    for s in SIDES:
        v = [c4["by_side"][s]["per_day"][d]["undecided_with_trades"] for d in dlist]
        L.append(f"| {s} | " + " | ".join(map(str, v)) + f" | {sum(v)} | {sum(v[:3])} | {sum(v[3:])} |")
    L += ["", "決まらない足の場合分け(6 日の合計。`kind` はシミュレーターの記録の口の分類):", ""]
    for s in SIDES:
        tot = {}
        for d in dlist:
            for k, v in c4["by_side"][s]["per_day"][d]["by_kind"].items():
                tot[k] = tot.get(k, 0) + v
        L.append(f"- {s}: " + "、".join(f"{k} {v}" for k, v in sorted(tot.items())))
    L += ["", "1 分足と約定の記録の高値・安値が違う分(6 日の中、両方にある分のうち): "
          + " / ".join(f"{d} {c4['bar_vs_trades'][d]['hl_differ']} / {c4['bar_vs_trades'][d]['both']}" for d in dlist), "",
          "## 日数", "", "- 6 日(前半 3 日・後半 3 日)。区間の主は日を 1 塊とした区間(値のある日を選び直す、1,000 回、種 20261006。"
          "塊が 6 以下だと狭く出る偏りがある)。決定を独立とみた Wilson の区間は印を付けて並べる"
          "(「決定を独立とみた区間。日の依存を入れていないので狭く出る」)。前半・後半は点だけ。", ""]
    return "\n".join(L) + "\n"


def _ratio_row(label: str, r: dict) -> str:
    days = " | ".join("—" if x[1] == 0 else f"{x[0]}/{x[1]}({x[2]:.3f})" for x in r["per_day"])
    return (f"| {label} | {days} | {r['k']} / {r['n']} | {f3(r['ratio'])} | {f3(r['minus_half'])} | {blk_s(r)} | "
            f"{f3(r['day_block']['se'])} | {f3(r['day_block']['mde'])} | {wil_s(r)} | {f3(r['first_half'])} | "
            f"{f3(r['second_half'])} |")


def _mean_row(label: str, r: dict) -> str:
    days = " | ".join("—" if x[0] == 0 else f"{x[1]:.3f}({x[0]})" for x in r["per_day"])
    return (f"| {label} | {days} | {r['n']} | {f3(r['mean'])} | {blk_s(r)} | {f3(r['day_block']['se'])} | "
            f"{f3(r['day_block']['mde'])} | {f3(r['first_half'])} | {f3(r['second_half'])} |")


def render_tables(res: dict, dlist: list) -> str:
    rhead = ("| 型・分け・量 | " + " | ".join(dlist) + " | 6 日の k / n | 割合 | 割合 − 0.5 | 日の塊の 95% 区間(主) | se | MDE"
             " | Wilson 95%(独立とみた) | 前半(点) | 後半(点) |", "|---|" + "---|" * (len(dlist) + 9))
    mhead = ("| 型・分け | " + " | ".join(dlist) + " | 件数 | 平均 | 日の塊の 95% 区間(主) | se | MDE | 前半(点) | 後半(点) |",
             "|---|" + "---|" * (len(dlist) + 7))
    L = ["# # 10 約定の側と 1 分足の中の順序(封印の前の 6 日)", "",
         "数はすべて `scripts/d1b/g3/g3_run.py` が出した(手で書いていない)。読みは書かない。対照 = 0.5(行 10)。", "",
         "- 区間(主): 日を 1 塊とした区間(`label_block_bootstrap_ci`。値のある日を選び直す、1,000 回、種 20261006、95%。"
         "括弧は塊の日数。塊が 6 以下だと狭く出る偏りがある)。se と MDE = 2.8 × se(2.8 = 1.96 + 0.84: 両側 5%・検出力 80%)はこの区間から。"
         f"並べる: Wilson の 95% 区間は「{WILSON_MARK}」。前半・後半は点だけ。年ごと = 6 日とも 2023 年(合計と同じ)。",
         "- same_side = 約定の分の最初の約定の側が決定の向きと同じ割合(unknown は分母から外す)。dir_first = その分の高値と安値の順で、"
         "決定の向きの側の端が先だった割合(順が決まらない分は分母から外す)。カード 9 の「秒」の順は、時刻 [t0, t0 + 60 秒) の約定だけで数える。",
         "- side_bp = 決定の向き × (約定の分の始値の後で、側 = 決定の向きの最初の約定の値段 − 始値) ÷ 始値 × 1e4(bp)。"
         "カード 9 の「秒」の始値 = t0 以後の最初の約定。向きの側の約定を探すのは約定の分の始まり(「秒」は t0)から 60 秒まで"
         "(無ければ値なし。件数は表の下)。", "",
         "## カード 3・5・8・9: 割合", "", "日ごとの欄は k/n(割合)。", "", *rhead]
    for typ, gs in res["side"].items():
        for gname, t in gs.items():
            for key in KEYS:
                L.append(_ratio_row(f"{typ}・{gname}・{key}", t[key]))
    L += ["", "## カード 3・5・8・9: 側の差の bp(side_bp)", "", "日ごとの欄は 平均(件数)。", "", *mhead]
    for typ, gs in res["side"].items():
        for gname, t in gs.items():
            L.append(_mean_row(f"{typ}・{gname}", t["side_bp"]))
    L += ["", "side_bp が無い決定(約定の分の始まり(カード 9 の「秒」は t0)から 60 秒以内に向きの側の約定が無い。"
          "約定の分に約定が無い決定も入る(カード 9 の「1 分」で起こる)): "
          + "、".join(f"{typ}・{g} {t['side_bp_missing']}" for typ, gs in res["side"].items() for g, t in gs.items())]
    L += ["", "## カード 3・5・8・9: side_bp を待ち(始値から向きの側の約定までの時間 side_wait_ms)の帯で分けたもの", "",
          "待ちの間の値動きが平均に混ざる(批評家 2 回目)ので帯で分ける。日ごとの欄は 平均(件数)。", "",
          "| 型・分け・待ち | " + " | ".join(dlist) + " | 件数 | 平均 | 日の塊の 95% 区間(主) | se | MDE | 前半(点) | 後半(点) |",
          "|---|" + "---|" * (len(dlist) + 7)]
    for typ, gs in res["side"].items():
        for gname, t in gs.items():
            for band, _lo, _hi in WAIT_BANDS:
                L.append(_mean_row(f"{typ}・{gname}・{band}", t["side_bp_by_wait"][band]))
    wq = ("p0", "p10", "p25", "p50", "p75", "p90", "p99", "p100")
    L += ["", "待ち(side_wait_ms、ミリ秒。side_bp のある決定)の分位:", "",
          "| 型・分け | 件数 | " + " | ".join(wq) + " |", "|---|---|" + "---|" * len(wq)]
    for typ, gs in res["side"].items():
        for gname, t in gs.items():
            q = t["side_wait_ms"]
            L.append(f"| {typ}・{gname} | {q['n']} | " + " | ".join("—" if k not in q else f"{q[k]:.1f}" for k in wq) + " |")
    sec = res["side"]["c9"]["sec"]
    qs = ("p0", "p10", "p25", "p50", "p75", "p90", "p99", "p100")
    L += ["", "## カード 9: Binance の清算の時刻 t0 から bitFlyer の最初の約定までの時間(wait_ms、ミリ秒)の分位", "",
          "| 日 | 件数 | " + " | ".join(qs) + " |", "|---|---|" + "---|" * len(qs)]
    for d, q in list(sec["wait_ms"]["per_day"].items()) + [("6 日", sec["wait_ms"]["all"])]:
        L.append(f"| {d} | {q['n']} | " + " | ".join("—" if k not in q else f"{q[k]:.1f}" for k in qs) + " |")
    L += ["", f"60 秒の窓が日の終わりで切れた決定: {sec['window_truncated']}"]
    c4 = res["c4"]
    L += ["", "## カード 4: 決まらない足ごとに、約定の道が選んだ道と同じか(1 決定 = 1 本の決まらない足)", "",
          "- 形: `MatildaLimitSim(fill_side=…, " + ", ".join(f"{k}={v!r}" for k, v in SIM_KW.items()) + ")`。",
          "- 片方だけ = 選んだ道かもう一方の道の片方とだけ同じ。両方 = 2 本の道が同じ結果で、約定の道もそれと同じ(別に数える)。", "",
          "| 側 | 比べた足 | 選んだ道とだけ同じ | もう一方の道とだけ同じ | 両方と同じ | どちらとも違う | 道の損益の差の和(約定 − 選んだ、bp) |",
          "|---|---|---|---|---|---|---|"]
    for s in SIDES:
        per = c4["by_side"][s]["per_day"]
        tot = {k: sum(per[d][k] for d in dlist) for k in ("undecided_with_trades", "eq_chosen_only", "eq_other_only",
                                                           "eq_both", "eq_neither")}
        L.append(f"| {s} | {tot['undecided_with_trades']} | {tot['eq_chosen_only']} | {tot['eq_other_only']} | {tot['eq_both']} | "
                 f"{tot['eq_neither']} | {math.fsum(per[d]['value_true_minus_chosen_bp'] for d in dlist):.2f} |")
    L += ["", "割合 A = 選んだ道と同じ(両方を含む)÷ 比べた全部。割合 B = 選んだ道とだけ同じ ÷(選んだ道とだけ同じ + もう一方の道とだけ同じ)。"
          "日ごとの欄は k/n(割合)。", "", *rhead]
    for s in SIDES:
        L.append(_ratio_row(f"c4・{s}・A 選んだ道と同じ ÷ 全部", c4["stats"][s]["eq_chosen"]))
        L.append(_ratio_row(f"c4・{s}・B 選んだ道 ÷(選んだ道 + もう一方)", c4["stats"][s]["chosen_vs_other"]))
    L += ["", "## カード 4: 1 日の損益(bp、出の時刻がその日の取引の和。経費の前)", "",
          "| 日 | 良い側(1 分足) | 悪い側(1 分足) | 約定の道(良い側から) | 約定の道(悪い側から) |", "|---|---|---|---|---|"]
    g, b = c4["by_side"]["good"]["pnl_per_day_bp"], c4["by_side"]["bad"]["pnl_per_day_bp"]
    for d in dlist:
        L.append(f"| {d} | {g['watch'][d]:.2f} | {b['watch'][d]:.2f} | {g['replay'][d]:.2f} | {b['replay'][d]:.2f} |")
    L += ["", "日の平均(日を 1 塊とした区間。1 日 = 1 値):", "", *mhead]
    for k, r in c4["pnl_stats"].items():
        L.append(_mean_row(k, r))
    L += ["", "1 分足と約定の記録の高値・安値が違う分: "
          + " / ".join(f"{d} {c4['bar_vs_trades'][d]['hl_differ']} / {c4['bar_vs_trades'][d]['both']}" for d in dlist), ""]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- 本体
def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--counts", action="store_true", help="件数の数え上げ(損益・値動きを計算しない)")
    g.add_argument("--short", default=None, help="短い期間の確かめ: 6 日のうち 1 日(YYYY-MM-DD)")
    g.add_argument("--full", action="store_true", help="本走らせ(6 日)")
    g.add_argument("--render-counts", action="store_true", help="置き場の counts.json から COUNTS.md を書き直すだけ(計算しない)")
    ap.add_argument("--c4-start", default=C4_START, help=f"カード 4 の足を流し始める時刻(既定 {C4_START}。過去だけの比の門の履歴)")
    ap.add_argument("--out", default=None, help=f"置き場(既定 {OUT_DEFAULT})")
    a = ap.parse_args(argv)
    if a.render_counts:  # 数え上げの数は変えず、表の形だけを書き直す(約定の記録・足は読まない)
        out = a.out or OUT_DEFAULT
        with open(os.path.join(out, "counts.json"), encoding="utf-8") as fh:
            c = json.load(fh)
        with open(os.path.join(out, "COUNTS.md"), "w", encoding="utf-8") as fh:
            fh.write(render_counts(c, c["days"]))
        print(f"書いた: {out}/COUNTS.md(counts.json から)")
        return 0
    all_days = trade_days()
    if a.short is not None and a.short not in all_days:
        raise SystemExit(f"拒否: {a.short} は 6 日 {all_days} に無い")
    dlist = [a.short] if a.short else all_days
    names = {d: n for d, n in zip(all_days, TRADE_FILES)}
    trades = {d: read_day(names[d]) for d in dlist}
    out = a.out or OUT_DEFAULT
    os.makedirs(out, exist_ok=True)
    c4_end = to_iso(max(dt.day_ns for dt in trades.values()) + DAY_NS)
    if a.counts:
        c = {"days": dlist, "cards": card_part(trades, counts_only=True),
             "c4": c4_run(trades, a.c4_start, c4_end, modes=("watch",), counts_only=True)}
        with open(os.path.join(out, "counts.json"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(c, ensure_ascii=False, sort_keys=True, indent=1, allow_nan=False) + "\n")
        with open(os.path.join(out, "COUNTS.md"), "w", encoding="utf-8") as fh:
            fh.write(render_counts(c, dlist))
        print(f"書いた: {out}/COUNTS.md")
        return 0
    cards = card_part(trades, counts_only=False)
    c4 = c4_run(trades, a.c4_start, c4_end)
    c4["stats"] = {s: c4_ratios(c4["by_side"][s]["compare_rows"], {d: trades[d].day_ns for d in dlist}, dlist)
                   for s in SIDES}
    pn = {f"{s}_{m}": {d: [c4["by_side"][s]["pnl_per_day_bp"][m][d]] for d in dlist} for s in SIDES for m in ("watch", "replay")}
    pn["replay_from_good_minus_good"] = {d: [pn["good_replay"][d][0] - pn["good_watch"][d][0]] for d in dlist}
    pn["replay_from_bad_minus_bad"] = {d: [pn["bad_replay"][d][0] - pn["bad_watch"][d][0]] for d in dlist}
    c4["pnl_stats"] = {k: mean_stats(v, dlist) for k, v in pn.items()}
    res = {"days": dlist, "side": side_tables(cards, dlist), "cards": cards, "c4": c4}
    with open(os.path.join(out, "g3.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(res, ensure_ascii=False, sort_keys=True, indent=1, allow_nan=False, default=str) + "\n")
    with open(os.path.join(out, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write(render_tables(res, dlist))
    print(f"書いた: {out}/TABLES.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
