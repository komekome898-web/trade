#!/usr/bin/env python3
"""価格帯ごとの積み上げから清算価格帯を予測できるかの測定器の実行入口
(`bot.research.liq_bands` の薄いラッパー)。

**これは測定器の入口であり、判定はしない。** 的中率・有意性はここでは一切計算しない。
出力は 1 清算イベント = 1 行の CSV(手法 (a)/(b)/(c) ごとの「帯に入ったか・距離bp」)
だけ。

対象は現状 Binance COIN-M のみ(aggTrades・metrics・liquidationSnapshot が同一取引所・
同一期間で揃うのはこの取引所だけ — `DATA_AVAILABILITY.md` §2b)。Gate は清算+建玉
(contract_stats)は揃うが約定側が本票群では未確認のため、この入口では扱わない。

**複数の起点 `t`(`--origin-times`)それぞれについて、その時点までのデータだけから
候補帯を作り、その直後 `--match-horizon-hours` 時間以内に起きた清算と照合する。**
起点をまたいだ先読みは無い(各 `t` の候補は `build_candidates_at` が内部で
`t` 以前だけに絞る)。

Usage(例):
    python scripts/measure_liq_bands.py \\
        --trades-root backtest_data/binance_cm_o3c_20260913/aggTrades/BTCUSD_PERP \\
        --metrics-root backtest_data/binance_cm_o3c_20260913/metrics/BTCUSD_PERP \\
        --liq-root backtest_data/binance_cm_o3c_20260913/liquidationSnapshot/BTCUSD_PERP \\
        --origin-times 2023-07-01T00:00:00Z,2023-07-02T00:00:00Z \\
        --out /tmp/binance_cm_liq_bands.csv

現在値(手法(c)の基準)は約定の終値をそのまま `PriceSeries` として使う
(専用の1分足OHLCVはこのスクリプトの引数に無いため、価格系列は約定から作る)。
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bot.research import liq_bands as lb  # noqa: E402


def _parse_iso_ms(s: str) -> int:
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.astimezone(timezone.utc).timestamp() * 1000)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trades-root", type=Path, required=True, help="aggTrades の <symbol> ディレクトリ")
    ap.add_argument("--metrics-root", type=Path, required=True, help="metrics の <symbol> ディレクトリ")
    ap.add_argument("--liq-root", type=Path, required=True, help="liquidationSnapshot の <symbol> ディレクトリ")
    ap.add_argument("--start", type=date.fromisoformat, default=None)
    ap.add_argument("--end", type=date.fromisoformat, default=None)
    ap.add_argument("--origin-times", type=str, required=True,
                     help="ISO8601 UTC のカンマ区切り(例 2023-07-01T00:00:00Z,...)。候補帯を作る起点 t")
    ap.add_argument("--lookback-hours", type=float, default=lb.DEFAULT_LOOKBACK_MS / 3_600_000,
                     help=f"積み上げを遡る時間(既定 {lb.DEFAULT_LOOKBACK_MS / 3_600_000:g}h、判断の置き所)")
    ap.add_argument("--price-bin-size", type=float, default=lb.DEFAULT_PRICE_BIN_SIZE,
                     help=f"価格の刻み(USD、既定 {lb.DEFAULT_PRICE_BIN_SIZE:g}、判断の置き所)")
    ap.add_argument("--top-k", type=int, default=lb.DEFAULT_TOP_K)
    ap.add_argument("--leverage-multiples", type=str,
                     default=",".join(str(x) for x in lb.DEFAULT_LEVERAGE_MULTIPLES),
                     help="手法(c)が仮定するレバレッジ倍率のカンマ区切り(判断の置き所)")
    ap.add_argument("--naive-band-half-width-bp", type=float, default=lb.DEFAULT_NAIVE_BAND_HALF_WIDTH_BP)
    ap.add_argument("--match-horizon-hours", type=float, default=lb.DEFAULT_MATCH_HORIZON_MS / 3_600_000,
                     help="起点 t の後、清算をどれだけ先まで見て照合するか(既定24h、判断の置き所)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    origin_times = sorted(_parse_iso_ms(s) for s in args.origin_times.split(","))
    leverage_multiples = tuple(float(x) for x in args.leverage_multiples.split(","))
    lookback_ms = int(args.lookback_hours * 3_600_000)
    match_horizon_ms = int(args.match_horizon_hours * 3_600_000)

    trades = lb.load_binance_cm_agg_trades(args.trades_root, args.start, args.end)
    oi_series, ls_series = lb.load_binance_cm_metrics(args.metrics_root, args.start, args.end)
    liq_events = lb.load_binance_cm_liquidations(args.liq_root, args.start, args.end)
    # 現在値(手法(c)の基準)は約定の終値そのままを価格系列として使う(専用の1分足は未指定)
    price_series = lb.PriceSeries.from_trades([(t.ts_ms, t.price) for t in trades])

    events_sorted = sorted(liq_events, key=lambda e: e.ts_ms)
    ev_ts = [e.ts_ms for e in events_sorted]

    import bisect
    rows: list[dict] = []
    skipped: list[int] = []
    for t in origin_times:
        cand = lb.build_candidates_at(
            trades, oi_series, price_series, t,
            lookback_ms=lookback_ms, price_bin_size=args.price_bin_size,
            funding_series=None,  # Binance COIN-M metrics に資金調達率の列自体が無い(README実測)
            long_short_series=ls_series,
            top_k=args.top_k, leverage_multiples=leverage_multiples,
            naive_band_half_width_bp=args.naive_band_half_width_bp,
        )
        if cand is None:
            skipped.append(t)
            continue
        lo = bisect.bisect_right(ev_ts, t)
        hi = bisect.bisect_right(ev_ts, t + match_horizon_ms)
        rows.extend(lb.match_liquidations_to_bands(events_sorted[lo:hi], cand))

    lb.write_csv(rows, args.out, columns=lb.CSV_COLUMNS)
    # 行数の確認のみ(判定はしない)
    print(f"origin_times={len(origin_times)} skipped(価格が引けない)={len(skipped)} "
          f"合計行数={len(rows)} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
