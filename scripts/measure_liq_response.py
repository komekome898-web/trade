#!/usr/bin/env python3
"""清算→価格反応の測定器の実行入口(`bot.research.liq_response` の薄いラッパー)。

**これは測定器の入口であり、判定はしない。** 事前登録より前の段階の道具で、
出力は 1 カスケード = 1 行の CSV(反応窓の bp・実カスケード/プラセボ/無清算の種別)
だけ。平均・有意性検定はここでは一切行わない。

対象は O-3c INTENT_MAP.md §4.2 決定 5 により Binance COIN-M と Gate の 2 つのみ
(取引所ごとに時刻精度・清算方式が違うため `--exchange` で必ず片方を選ぶ)。

Usage(例。実行するとファイルを書くので、事前登録前に走らせる際は出力先に注意):
    python scripts/measure_liq_response.py \\
        --exchange binance_cm \\
        --liq-root backtest_data/binance_cm_o3c_20260913/liquidationSnapshot/BTCUSD_PERP \\
        --price-csv <ts_ms,price の CSV> \\
        --out /tmp/binance_cm_liq_response.csv

    python scripts/measure_liq_response.py \\
        --exchange gate \\
        --gate-file backtest_data/gate_liquidations_20260908/BTC_USDT.jsonl.gz \\
        --price-csv <ts_ms,price の CSV> \\
        --out /tmp/gate_liq_response.csv

`--price-csv` の形式は 2 列 `ts_ms,price`(ヘッダ行あり)。1 分足などの OHLCV を使う場合は
`bot.research.liq_response.PriceSeries.from_ohlc_bars` を直接呼ぶ別スクリプトに任せる
(このスクリプトは tick/価格列専用)。
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bot.research import liq_response as lr  # noqa: E402


def _load_prices(path: Path) -> lr.PriceSeries:
    rows: list[tuple[int, float]] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames is not None and {"ts_ms", "price"} <= set(reader.fieldnames), (
            f"--price-csv は ts_ms,price の2列を要求する(実際の列: {reader.fieldnames})"
        )
        for r in reader:
            rows.append((int(r["ts_ms"]), float(r["price"])))
    return lr.PriceSeries.from_trades(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exchange", choices=["binance_cm", "gate"], required=True)
    ap.add_argument("--liq-root", type=Path, help="binance_cm: liquidationSnapshot の <symbol> ディレクトリ")
    ap.add_argument("--gate-file", type=Path, help="gate: *.jsonl.gz 1本")
    ap.add_argument("--start", type=date.fromisoformat, default=None)
    ap.add_argument("--end", type=date.fromisoformat, default=None)
    ap.add_argument("--price-csv", type=Path, required=True, help="ts_ms,price の2列CSV")
    ap.add_argument("--gap-ms", type=int, default=60_000, help="カスケードを切る無清算の閾値(既定60秒)")
    ap.add_argument("--horizons-min", type=str, default="1,5,15,60")
    ap.add_argument("--volume-csv", type=Path, default=None,
                     help="プラセボ抽出用の出来高バー(start_ms,end_ms,volume の3列CSV)。省略時はプラセボを作らない")
    ap.add_argument("--seed", type=int, default=0, help="プラセボ/無清算窓の抽選シード")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    horizons = tuple(int(h) for h in args.horizons_min.split(","))

    if args.exchange == "binance_cm":
        assert args.liq_root is not None, "--exchange binance_cm には --liq-root が要る"
        events = lr.load_binance_cm_liquidations(args.liq_root, args.start, args.end)
    else:
        assert args.gate_file is not None, "--exchange gate には --gate-file が要る"
        events = lr.load_gate_liquidations(args.gate_file)

    real = lr.build_cascades(events, args.exchange, gap_ms=args.gap_ms)
    prices = _load_prices(args.price_csv)
    rng = random.Random(args.seed)

    placebo: list[lr.Cascade] = []
    if args.volume_csv is not None:
        vol_bars = []
        with args.volume_csv.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                vol_bars.append((int(r["start_ms"]), int(r["end_ms"]), float(r["volume"])))
        placebo = lr.sample_placebo_windows(real, vol_bars, events, args.exchange, rng=rng)

    no_liq: list[lr.Cascade] = []
    if real:
        span_start = min(e.ts_ms for e in events)
        span_end = max(e.ts_ms for e in events)
        no_liq = lr.sample_no_liquidation_windows(real, events, args.exchange, span_start, span_end, rng=rng)

    rows = lr.build_dataset(real, placebo, no_liq, prices, horizons_min=horizons)
    lr.write_csv(rows, args.out)
    # 行数の確認のみ(判定はしない)
    print(f"{args.exchange}: real={len(real)} placebo={len(placebo)} no_liquidation={len(no_liq)} "
          f"合計行数={len(rows)} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
