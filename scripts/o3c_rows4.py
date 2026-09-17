#!/usr/bin/env python3
"""O-3c「4 行」の行 1・行 2(2026-09-17、オーナー決定 L-192「**4 行全部進めてください**」)。

行 1 の逐語: 「**重複行を一意化(全列一致の行を 1 件に)してから、測定器の束ね
`build_cascades` を使う**」
行 2 の逐語: 「**3 件目の一覧 §4・§12 の「幅 0 の断片」「タイ」の数え直しは、一意化した後に行う**」

モードは 2 つ。

  `cascades`  行 1。一意化した清算で `build_cascades`(既定 `GAP_MS`=60,000ms)を走らせ、
              一意件数 / 束の数 / 束あたり件数の分布 / 束の長さの分布 / 幅 0 の束を数える。
              **一意化前(2 倍)の同じ数と並べる。**
  `ties`      行 2。`REPORT_2026-09-14.md` §0.0 の「実データに触る前の前提条件(3 つ)」
              = タイの件数を数える / タイの経路(価格の刻み / 時間分解能)を分ける /
              幅 0 の断片の件数を数える。起点は `after_shift` と既定 `before` の両方。

**観測表のみ。判定(予測できる/できない、当たる/当たらない、使える/使えない)は書かない。**

使い方:
  python3 scripts/o3c_rows4.py cascades --data-root <根> --out-dir <出力>
  python3 scripts/o3c_rows4.py ties     --data-root <根> --out-dir <出力の親>
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import o3c_price_level_table as base  # noqa: E402

from bot.research.liq_response import (  # noqa: E402
    PriceSeries,
    attach_internal_direction,
    build_cascades,
    compute_reactions,
    dedup_exact_rows,
    load_binance_cm_liquidations,
    load_binance_cm_liquidations_with_dedup_stats,
    reversal_scores,
)

EXCHANGE = "binance_cm"
GAP_MS = 60_000                      # `build_cascades` の既定値
HORIZON_MIN = 15                     # 反応窓。原文に無い(仮定。REPORT §0.0 の合成検証と同じ)
BAR_MS = 60_000                      # 粒度。原文に無い(仮定。REPORT §0.0 の合成検証と同じ)
STALENESS_MS = 300_000               # `compute_reactions` の既定


# --------------------------------------------------------------------------
# 共通
# --------------------------------------------------------------------------


def liq_dir(root: Path) -> Path:
    return root / "liquidationSnapshot" / base.SYMBOL


def all_days(root: Path) -> list[str]:
    """`liquidationSnapshot` の zip がある日(古い順)。"""
    return sorted(
        "-".join(p.stem.rsplit("-", 3)[1:])
        for p in liq_dir(root).glob("*-liquidationSnapshot-*.zip")
    )


def shift_day(day: str, k: int) -> str:
    return (base._dt.date.fromisoformat(day) + base._dt.timedelta(days=k)).isoformat()


def write_outputs(out_dir: Path, header: list[str], rows: list[list], summary: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "table.csv").open("w", encoding="utf-8") as fh:
        fh.write(",".join(header) + "\n")
        for r in rows:
            fh.write(",".join("" if v is None else str(v) for v in r) + "\n")
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    base.write_md5sums(out_dir, ["table.csv", "summary.json"])


def _quant(x: np.ndarray) -> dict:
    if x.size == 0:
        return {}
    return {
        f"q{q}": float(np.percentile(x, q)) for q in (5, 25, 50, 75, 90, 95, 99)
    } | {"min": float(x.min()), "max": float(x.max()), "mean": float(x.mean())}


def _size_buckets(n: np.ndarray) -> dict:
    """束あたり件数の分布(1 / 2 / 3〜5 / 6〜)。"""
    return {
        "eq1": int((n == 1).sum()),
        "eq2": int((n == 2).sum()),
        "3to5": int(((n >= 3) & (n <= 5)).sum()),
        "ge6": int((n >= 6).sum()),
    }


def _len_buckets(w: np.ndarray) -> dict:
    """束の長さ(end−start ms)の分布。境界は左閉右開。"""
    edges = [0, 1, 1_000, 10_000, 60_000, 600_000, 3_600_000]
    labels = ["eq0", "1-999ms", "1-10s", "10-60s", "60s-10min", "10-60min", "ge60min"]
    out = {"eq0": int((w == 0).sum())}
    for i in range(1, len(edges) - 1):
        out[labels[i]] = int(((w >= edges[i]) & (w < edges[i + 1])).sum())
    out[labels[-1]] = int((w >= edges[-1]).sum())
    return out


# --------------------------------------------------------------------------
# 行 1: 一意化 -> build_cascades
# --------------------------------------------------------------------------


#: `MISSING_2026-09-17.md` §4 が間隔分布を出した 6 日(同じ日で数え直すため)。
MISSING_SAMPLE_DAYS = (
    "2023-06-25", "2023-06-26", "2024-02-19", "2024-02-20", "2024-10-13", "2024-10-14",
)


def _day_of(ts_ms: int) -> str:
    return base._dt.datetime.utcfromtimestamp(ts_ms / 1000).date().isoformat()


def _gap_block(events, within_day: bool = False) -> dict:
    """清算イベントの**間隔**(隣り合う ts_ms の差)の分布。

    `MISSING_2026-09-17.md` §4 が 6 日標本で出した数と同じ量。そこでの値は
    一意化前(重複込み)なので、一意化の前後で並べられるようにここで両方作る。

    `within_day=True` は**日(= ファイル)ごとに区切って**間隔を取る。
    `MISSING` §4 はファイルごとに計算しており、日をまたぐ間隔を数えていない
    (6 日標本で間隔 1,038 件 = Σ(その日の件数 − 1))。つなげて数えると 1,043 件になる。
    """
    ts_all = sorted(e.ts_ms for e in events)
    if within_day:
        per: dict[str, list[int]] = {}
        for t in ts_all:
            per.setdefault(_day_of(t), []).append(t)
        parts = [np.diff(np.array(v, dtype=np.int64)) for v in per.values() if len(v) > 1]
        g = np.concatenate(parts) if parts else np.empty(0, dtype=np.int64)
        ts = np.array(ts_all, dtype=np.int64)
    else:
        ts = np.array(ts_all, dtype=np.int64)
        if ts.size < 2:
            return {"n_gaps": int(max(ts.size - 1, 0))}
        g = np.diff(ts)
    if g.size == 0:
        return {"n_events": int(ts.size), "n_gaps": 0}
    return {
        "n_events": int(ts.size),
        "n_gaps": int(g.size),
        "quantiles_ms": {
            f"q{q}": float(np.percentile(g, q)) for q in (0, 25, 50, 75, 90, 99, 100)
        },
        "n_gap_eq0": int((g == 0).sum()),
        "rate_gap_eq0": float((g == 0).mean()),
        "n_gap_le_60000": int((g <= 60_000).sum()),
        "rate_gap_le_60000": float((g <= 60_000).mean()),
    }


def run_cascades(root: Path, out_dir: Path, gap_ms: int) -> dict:
    t0 = time.time()
    d = liq_dir(root)
    raw_events = load_binance_cm_liquidations(d)
    uniq_events, stats = load_binance_cm_liquidations_with_dedup_stats(d)
    raw_c = build_cascades(raw_events, EXCHANGE, gap_ms=gap_ms)
    uniq_c = build_cascades(uniq_events, EXCHANGE, gap_ms=gap_ms)

    blocks: dict[str, dict] = {}
    for label, evs, cs in (("raw", raw_events, raw_c), ("dedup", uniq_events, uniq_c)):
        n = np.array([c.n_events for c in cs], dtype=np.int64)
        w = np.array([c.end_ms - c.start_ms for c in cs], dtype=np.int64)
        size = np.array([c.total_size for c in cs], dtype=np.float64)
        blocks[label] = {
            "n_liq_events": len(evs),
            "n_cascades": len(cs),
            "n_events_per_cascade": _size_buckets(n) | {"quantiles": _quant(n.astype(float))},
            "cascade_len_ms": _len_buckets(w) | {"quantiles": _quant(w.astype(float))},
            "zero_width": {
                "n": int((w == 0).sum()),
                "rate": float((w == 0).mean()) if w.size else float("nan"),
            },
            "gaps_all_days": _gap_block(evs),
            "gaps_missing_sample_days": _gap_block(
                [e for e in evs if _day_of(e.ts_ms) in MISSING_SAMPLE_DAYS],
                within_day=True,
            ),
            "total_size_sum": float(size.sum()),
            "direction": {
                k: int(sum(1 for c in cs if c.direction == k))
                for k in ("long", "short", "mixed")
            },
        }

    # 表(長い形): 1 行 = 1 指標。一意化前(raw)と一意化後(dedup)を並べる。
    rows: list[list] = []

    def add(group: str, metric: str) -> None:
        def pick(b: dict):
            cur: object = b
            for part in metric.split("."):
                cur = cur[part]  # type: ignore[index]
            return cur
        rows.append([group, metric, pick(blocks["raw"]), pick(blocks["dedup"])])

    add("件数", "n_liq_events")
    add("件数", "n_cascades")
    for k in ("eq1", "eq2", "3to5", "ge6"):
        add("束あたり件数", f"n_events_per_cascade.{k}")
    for k in ("q5", "q25", "q50", "q75", "q90", "q95", "q99", "max"):
        add("束あたり件数の分位", f"n_events_per_cascade.quantiles.{k}")
    for k in _len_buckets(np.array([], dtype=np.int64)):
        add("束の長さ(ms)", f"cascade_len_ms.{k}")
    for k in ("q5", "q25", "q50", "q75", "q90", "q95", "q99", "max"):
        add("束の長さの分位(ms)", f"cascade_len_ms.quantiles.{k}")
    add("幅 0 の束", "zero_width.n")
    add("幅 0 の束", "zero_width.rate")
    for k in ("long", "short", "mixed"):
        add("束の向き", f"direction.{k}")
    for grp, key in (
        ("清算の間隔(全 472 日)", "gaps_all_days"),
        ("清算の間隔(MISSING §4 の 6 日・日ごと)", "gaps_missing_sample_days"),
    ):
        for k in ("q0", "q25", "q50", "q75", "q90", "q99", "q100"):
            add(grp, f"{key}.quantiles_ms.{k}")
        for k in ("n_gap_eq0", "rate_gap_eq0", "n_gap_le_60000", "rate_gap_le_60000"):
            add(grp, f"{key}.{k}")

    summary = {
        "params": {
            "data_root": str(root),
            "symbol": base.SYMBOL,
            "gap_ms": gap_ms,
            "days": len(list(liq_dir(root).glob("*-liquidationSnapshot-*.zip"))),
            "owner_verbatim": "4 行全部進めてください",
            "lead_row1_text": (
                "重複行を一意化(全列一致の行を 1 件に)してから、測定器の束ね "
                "build_cascades を使う"
            ),
        },
        "elapsed_sec": round(time.time() - t0, 2),
        "dedup": {
            "n_in": stats.n_in,
            "n_out": stats.n_out,
            "n_dropped": stats.n_dropped,
            "drop_rate": stats.drop_rate,
            "multiplicity": {str(k): v for k, v in stats.multiplicity.items()},
        },
        "blocks": blocks,
        "notes": [
            "一意化の判定は生の CSV 行の全列一致(load_binance_cm_liquidations の dedup=True)。",
            "raw = 一意化前(ファイルの行のまま)/ dedup = 一意化後。",
            "束ね方は build_cascades の既定 gap_ms=60,000ms(ちょうど 60,000ms は同じ束)。",
            "幅 0 の束 = end_ms == start_ms の束。",
            "清算の間隔 = 隣り合う清算の ts_ms の差。MISSING_2026-09-17.md §4 が"
            "6 日標本で出した量と同じもの(そこでの値は一意化前)。"
            "6 日の行は MISSING と同じく日(ファイル)ごとに区切って数えている"
            "(全 472 日の行はつなげて数えている)。",
            "観測のみ。判定は書いていない。",
        ],
    }
    write_outputs(out_dir, ["group", "metric", "raw", "dedup"], rows, summary)
    return summary


# --------------------------------------------------------------------------
# 行 2: タイ / タイの経路 / 幅 0 の断片
# --------------------------------------------------------------------------

TIE_PATH_TIME = "time_resolution"    # 起点と終点の時刻が同じ(窓の内側に時刻が進んでいない)
TIE_PATH_TICK = "price_tick"         # 別の点なのに価格が同じ(価格が動いていない)


def classify(prices: PriceSeries, cascades, anchor: str) -> list[dict]:
    """1 束ずつ、起点・終点の点を引いて、タイかどうかとその経路を決める。

    起点(anchor)の置き方は `compute_reactions` と同じ:
      `before`      終点の点 = `at_or_before(end_ms)`
      `after_shift` 終点の点 = `at_or_after(end_ms)`
    内部方向の**始点**はどちらも `at_or_before(start_ms)`(`attach_internal_direction`)。

    経路の定義(原文に無い。委任先が置いた分け方):
      `time_resolution` 始点と終点の**時刻が同じ** = 窓の内側で時刻が 1 つも進んでいない
                        (その粒度では窓が 1 点に潰れている)
      `price_tick`      **時刻は違う**のに価格が同じ = その間に価格が動いていない
    判定はまず価格が等しいか(タイか)を見て、タイだった行だけを 2 つに分ける。
    2 つは排他で、タイの全件がどちらかに入る。
    """
    out: list[dict] = []
    for c in cascades:
        s = prices.at_or_before(int(c.start_ms), STALENESS_MS)
        if anchor == "before":
            e = prices.at_or_before(int(c.end_ms), STALENESS_MS)
        else:
            e = prices.at_or_after(int(c.end_ms), STALENESS_MS)
        rec = {
            "cascade_id": c.cascade_id,
            "tie": None,
            "path": "",
            "internal_bp": float("nan"),
            "anchor_ts_ms": e[0] if e else None,
            "start_pt_ts_ms": s[0] if s else None,
        }
        if s is None or e is None or not s[1]:
            rec["path"] = "missing"
            out.append(rec)
            continue
        rec["internal_bp"] = (e[1] - s[1]) / s[1] * 10_000.0
        tie = e[1] == s[1]
        rec["tie"] = bool(tie)
        if tie:
            rec["path"] = TIE_PATH_TIME if e[0] == s[0] else TIE_PATH_TICK
        out.append(rec)
    return out


def tie_block(prices: PriceSeries, cascades, anchor: str, label: str) -> tuple[dict, dict]:
    """1 つの起点の置き方について、タイの件数・率・経路を数える。

    戻り値 (集計, 束 id -> 1 束ぶんの記録)。
    """
    rows = compute_reactions(
        cascades, prices, horizons_min=(HORIZON_MIN,),
        anchor_max_staleness_ms=STALENESS_MS,
        future_max_staleness_ms=STALENESS_MS,
        anchor=anchor,
    )
    rows = attach_internal_direction(rows, prices, max_staleness_ms=STALENESS_MS)
    grp = reversal_scores(rows, bp_key=f"bp_{HORIZON_MIN}m", name=label, tie_policy="keep")

    cls = classify(prices, cascades, anchor)
    by_id = {c["cascade_id"]: c for c in cls}
    # 自前の分類と測定器の `internal_bp` が食い違わないことを確かめる
    # (食い違ったら数え方が違うので、黙って通さない)。
    n_zero_measured = sum(
        1 for r in rows
        if r.get("internal_bp") == r.get("internal_bp") and r["internal_bp"] == 0.0
    )
    n_zero_mine = sum(1 for c in cls if c["tie"] is True)
    assert n_zero_measured == n_zero_mine, (anchor, n_zero_measured, n_zero_mine)

    width = np.array([c.end_ms - c.start_ms for c in cascades], dtype=np.int64)
    tie_arr = np.array([1 if by_id[c.cascade_id]["tie"] else 0 for c in cascades])
    zero_w = width == 0
    n_paths = {
        TIE_PATH_TIME: sum(1 for c in cls if c["path"] == TIE_PATH_TIME),
        TIE_PATH_TICK: sum(1 for c in cls if c["path"] == TIE_PATH_TICK),
    }
    n_missing = sum(1 for c in cls if c["path"] == "missing")
    n_rows = len(cascades)
    agg = {
        "anchor": anchor,
        "n_rows": n_rows,
        # 測定器(reversal_scores)が返す値
        "n_tie": grp.n_tie,
        "tie_rate": grp.tie_rate,
        "n_used": grp.n_used,
        "n_excluded_missing": grp.n_excluded_missing,
        "exclusion_rate": grp.exclusion_rate,
        # 自前の数え直し(起点・終点の点を直接引いたもの)
        "n_tie_direct": n_zero_mine,
        "tie_rate_direct": n_zero_mine / n_rows if n_rows else float("nan"),
        "n_missing_direct": n_missing,
        "paths": n_paths,
        "path_rate_of_ties": {
            k: (v / n_zero_mine if n_zero_mine else float("nan"))
            for k, v in n_paths.items()
        },
        "zero_width_cross": {
            "n_zero_width": int(zero_w.sum()),
            "zero_width_rate": float(zero_w.mean()) if n_rows else float("nan"),
            "n_tie_and_zero_width": int(((tie_arr == 1) & zero_w).sum()),
            "n_tie_and_positive_width": int(((tie_arr == 1) & ~zero_w).sum()),
            "tie_rate_within_zero_width": (
                float(tie_arr[zero_w].mean()) if zero_w.any() else float("nan")
            ),
            "tie_rate_within_positive_width": (
                float(tie_arr[~zero_w].mean()) if (~zero_w).any() else float("nan")
            ),
        },
    }
    return agg, by_id


def build_bar_series(times: np.ndarray, prices_arr: np.ndarray, bar_ms: int
                     ) -> tuple[np.ndarray, np.ndarray]:
    """`scripts/verify_liq_instrument.py: to_bars` と同じ間引き方。

    各 `bar_ms` の枠について**最後の約定の (時刻, 価格)** を残す(枠の開始時刻ではなく
    実際の約定時刻を持つ点になる。合成データの検証で使った形と同じ)。
    """
    if times.size == 0:
        return times, prices_arr
    bucket = times // bar_ms
    last = np.empty(bucket.size, dtype=bool)
    last[-1] = True
    last[:-1] = bucket[1:] != bucket[:-1]
    return times[last], prices_arr[last]


def run_ties(root: Path, out_parent: Path, gap_ms: int, granularity: str) -> dict:
    t0 = time.time()
    uniq_events, stats = load_binance_cm_liquidations_with_dedup_stats(liq_dir(root))
    cascades = build_cascades(uniq_events, EXCHANGE, gap_ms=gap_ms)
    print(f"清算 一意 {len(uniq_events)} 件 -> 束 {len(cascades)} 個", flush=True)

    days = all_days(root)
    day_start = {d: base.day_bounds_ms(d)[0] for d in days}
    # 束を「終了時刻の日」で分ける(約定そのままの粒度は日ごとに読むため)。
    by_day: dict[str, list] = {d: [] for d in days}
    unassigned = []
    bounds = np.array([day_start[d] for d in days], dtype=np.int64)
    for c in cascades:
        i = int(np.searchsorted(bounds, c.end_ms, side="right")) - 1
        if i < 0:
            unassigned.append(c)
        else:
            by_day[days[i]].append(c)

    bar_t: list[np.ndarray] = []
    bar_p: list[np.ndarray] = []
    cache: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    missing_agg: list[str] = []
    per_day_trade: dict[str, dict] = {}
    trade_records: dict[str, dict[str, dict]] = {"before": {}, "after_shift": {}}
    trade_aggs: list[dict] = []

    def agg_day(d: str):
        if d not in cache:
            p = base.agg_path(root, d)
            if not p.exists():
                cache[d] = (
                    np.empty(0, dtype=np.int64),
                    np.empty(0, dtype=np.float64),
                    np.empty(0, dtype=np.float64),
                )
                if d not in missing_agg:
                    missing_agg.append(d)
            else:
                cache[d] = base.load_agg_trades(p)
        return cache[d]

    for i_day, d in enumerate(days):
        t_d, p_d, _q_d = agg_day(d)
        if t_d.size:
            bt, bp = build_bar_series(t_d, p_d, BAR_MS)
            bar_t.append(bt)
            bar_p.append(bp)
        cs = by_day[d]
        if granularity in ("trade", "both") and cs:
            lo = min(c.start_ms for c in cs) - STALENESS_MS
            hi = max(c.end_ms for c in cs) + HORIZON_MIN * 60_000 + STALENESS_MS
            # 要る日 = 束の開始 5 分前 〜 束の終了 + 地平線 + 5 分 を覆う日
            d_lo = base._dt.datetime.utcfromtimestamp(lo / 1000).date().isoformat()
            d_hi = base._dt.datetime.utcfromtimestamp(hi / 1000).date().isoformat()
            need = [d_lo]
            while need[-1] < d_hi:
                need.append(shift_day(need[-1], 1))
            parts = [agg_day(x) for x in need]
            parts = [x for x in parts if x[0].size]
            if parts:
                tt = np.concatenate([x[0] for x in parts])
                pp = np.concatenate([x[1] for x in parts])
                if not bool(np.all(tt[1:] >= tt[:-1])):
                    order = np.argsort(tt, kind="stable")
                    tt, pp = tt[order], pp[order]
                m = (tt >= lo) & (tt <= hi)
                ps = PriceSeries(ts_ms=tt[m].tolist(), price=pp[m].tolist())
                n_pts = int(m.sum())
            else:
                ps = PriceSeries(ts_ms=[], price=[])
                n_pts = 0
            for anchor in ("before", "after_shift"):
                a, recs = tie_block(ps, cs, anchor, f"{d}_{anchor}")
                a["day"] = d
                a["granularity"] = "trade"
                trade_aggs.append(a)
                trade_records[anchor].update(recs)
            per_day_trade[d] = {"n_cascades": len(cs), "n_price_points": n_pts}
        keep_from = shift_day(d, -1)
        for k in list(cache):
            if k < keep_from:
                del cache[k]
        if (i_day + 1) % 50 == 0:
            print(f"  {i_day + 1}/{len(days)} 日 ({round(time.time() - t0)} 秒)", flush=True)

    out: dict = {"granularities": {}}

    # ---- 60 秒バー(全期間を 1 本の系列にできる) ----
    bt = np.concatenate(bar_t)
    bp = np.concatenate(bar_p)
    order = np.argsort(bt, kind="stable")
    bar_series = PriceSeries(ts_ms=bt[order].tolist(), price=bp[order].tolist())
    print(f"60 秒バー {len(bar_series.ts_ms)} 点", flush=True)
    bar_aggs = {}
    bar_records = {}
    for anchor in ("before", "after_shift"):
        a, recs = tie_block(bar_series, cascades, anchor, f"bar{BAR_MS // 1000}_{anchor}")
        bar_aggs[anchor] = a
        bar_records[anchor] = recs
    out["granularities"][f"bar{BAR_MS // 1000}s"] = {
        "n_price_points": len(bar_series.ts_ms),
        "by_anchor": bar_aggs,
    }

    # ---- 約定そのまま(日ごとに切って処理した) ----
    if granularity in ("trade", "both"):
        merged: dict[str, dict] = {}
        for anchor in ("before", "after_shift"):
            recs = trade_records[anchor]
            n_rows = len(recs)
            n_tie = sum(1 for r in recs.values() if r["tie"] is True)
            n_missing = sum(1 for r in recs.values() if r["path"] == "missing")
            paths = {
                TIE_PATH_TIME: sum(1 for r in recs.values() if r["path"] == TIE_PATH_TIME),
                TIE_PATH_TICK: sum(1 for r in recs.values() if r["path"] == TIE_PATH_TICK),
            }
            w = {c.cascade_id: c.end_ms - c.start_ms for c in cascades}
            zw = [cid for cid in recs if w[cid] == 0]
            pw = [cid for cid in recs if w[cid] != 0]
            merged[anchor] = {
                "anchor": anchor,
                "n_rows": n_rows,
                "n_tie_direct": n_tie,
                "tie_rate_direct": n_tie / n_rows if n_rows else float("nan"),
                "n_missing_direct": n_missing,
                "paths": paths,
                "path_rate_of_ties": {
                    k: (v / n_tie if n_tie else float("nan")) for k, v in paths.items()
                },
                "zero_width_cross": {
                    "n_zero_width": len(zw),
                    "n_tie_and_zero_width": sum(1 for c in zw if recs[c]["tie"] is True),
                    "n_tie_and_positive_width": sum(
                        1 for c in pw if recs[c]["tie"] is True
                    ),
                    "tie_rate_within_zero_width": (
                        sum(1 for c in zw if recs[c]["tie"] is True) / len(zw)
                        if zw else float("nan")
                    ),
                    "tie_rate_within_positive_width": (
                        sum(1 for c in pw if recs[c]["tie"] is True) / len(pw)
                        if pw else float("nan")
                    ),
                },
                "n_tie_sum_of_days": sum(
                    a["n_tie_direct"] for a in trade_aggs if a["anchor"] == anchor
                ),
            }
        out["granularities"]["trade"] = {
            "days_processed": len(per_day_trade),
            "cascades_processed": sum(v["n_cascades"] for v in per_day_trade.values()),
            "by_anchor": merged,
        }

    # ---- 表 ----
    header = [
        "cascade_id", "start_ms", "end_ms", "width_ms", "n_events", "total_size",
        "direction",
        "bar60_before_tie", "bar60_before_path", "bar60_before_internal_bp",
        "bar60_after_shift_tie", "bar60_after_shift_path", "bar60_after_shift_internal_bp",
        "trade_before_tie", "trade_before_path", "trade_before_internal_bp",
        "trade_after_shift_tie", "trade_after_shift_path", "trade_after_shift_internal_bp",
    ]
    rows: list[list] = []
    for c in cascades:
        r: list = [
            c.cascade_id, c.start_ms, c.end_ms, c.end_ms - c.start_ms,
            c.n_events, round(c.total_size, 4), c.direction,
        ]
        for store in (bar_records, trade_records):
            for anchor in ("before", "after_shift"):
                rec = store.get(anchor, {}).get(c.cascade_id)
                if rec is None:
                    r += ["", "", ""]
                else:
                    v = rec["internal_bp"]
                    r += [
                        "" if rec["tie"] is None else int(rec["tie"]),
                        rec["path"],
                        "" if v != v else round(v, 6),
                    ]
        rows.append(r)

    summary = {
        "params": {
            "data_root": str(root),
            "symbol": base.SYMBOL,
            "gap_ms": gap_ms,
            "horizon_min": HORIZON_MIN,
            "bar_ms": BAR_MS,
            "staleness_ms": STALENESS_MS,
            "granularity": granularity,
            "owner_verbatim": "4 行全部進めてください",
            "lead_row2_text": (
                "3 件目の一覧 §4・§12 の「幅 0 の断片」「タイ」の数え直しは、"
                "一意化した後に行う"
            ),
            "assumption_source": (
                "粒度(60 秒バー)と地平線(15 分)は原文に無い。"
                "docs/PHASE2/INSTRUMENT_VERIFY/REPORT_2026-09-14.md §0.0 の"
                "合成データ検証で使われた値を仮定として置いた。"
            ),
        },
        "elapsed_sec": round(time.time() - t0, 2),
        "dedup": {
            "n_in": stats.n_in,
            "n_out": stats.n_out,
            "multiplicity": {str(k): v for k, v in stats.multiplicity.items()},
        },
        "n_cascades": len(cascades),
        "n_cascades_unassigned_day": len(unassigned),
        "days": len(days),
        "agg_trades_missing_days": missing_agg,
        "tie_path_definition": {
            TIE_PATH_TIME: "起点と終点の時刻が同じ = その粒度では窓が 1 点に潰れている",
            TIE_PATH_TICK: "時刻は違うのに価格が同じ = その間に価格が動いていない",
        },
        **out,
        "per_day_trade": per_day_trade,
        "notes": [
            "タイ = 粗い内部方向(attach_internal_direction の internal_bp)が 0 の行。",
            "測定器の n_tie(reversal_scores)と自前の数え直し(n_tie_direct)の両方を出している。"
            "自前の分類は internal_bp == 0 の件数と一致することを assert で確かめている。",
            "起点は before(既定)と after_shift の 2 通り。",
            "幅 0 の断片 = end_ms == start_ms の束(行 1 と同じ定義)。",
            "観測のみ。判定は書いていない。",
        ],
    }
    out_dir = out_parent
    write_outputs(out_dir, header, rows, summary)
    return summary


# --------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["cascades", "ties"])
    ap.add_argument("--data-root", default=str(base.DEFAULT_DATA_ROOT))
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--gap-ms", type=int, default=GAP_MS)
    ap.add_argument("--granularity", choices=["bar", "trade", "both"], default="both")
    a = ap.parse_args(argv)
    root = Path(a.data_root)
    if a.mode == "cascades":
        s = run_cascades(root, Path(a.out_dir), a.gap_ms)
        print(
            f"一意 {s['dedup']['n_out']} 件 / 束 {s['blocks']['dedup']['n_cascades']} 個"
            f" / 幅 0 の束 {s['blocks']['dedup']['zero_width']['n']}"
            f" -> {a.out_dir}"
        )
    else:
        s = run_ties(root, Path(a.out_dir), a.gap_ms, a.granularity)
        for g, blk in s["granularities"].items():
            for anchor, v in blk["by_anchor"].items():
                print(
                    f"{g} / {anchor}: タイ {v['n_tie_direct']} / {v['n_rows']}"
                    f" = {v['tie_rate_direct']:.4f}"
                    f"(時間分解能 {v['paths'][TIE_PATH_TIME]} / "
                    f"価格の刻み {v['paths'][TIE_PATH_TICK]})"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
