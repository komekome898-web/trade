#!/usr/bin/env python3
"""BitMEX の公開約定アーカイブを、取引所が閉じる前に取り込む。

**期限がある【事実 2026-09-09、一次情報で確認】**: BitMEX 自身の告知
(`GET https://www.bitmex.com/api/v1/announcement`)に、

- **2026-09-16 12:00 UTC**: XBTUSD / XBTUSDT / ETHUSD / ETHUSDT と各先物を上場廃止・清算
- **2026-09-23**: **BitMEX 取引所そのものを閉鎖**

とある。公開アーカイブ(`public.bitmex.com/data/trade/`)は 2014-11 〜 **2025-02-22** で
既に更新が止まっているが、**閉鎖後も置かれ続ける保証はどこにも無い**。
カツオ(15 分足ヒゲ逆張り)の原典ベニューはここであり、機構の歴史的検証
(`docs/STRATEGY_IDEAS.md` O-3 / O-6 の層 ①)はこのデータでしか出来ない。

**なぜ生のまま全部持てないか**: 全 3,747 日で 47.9 GB。研究環境の空きは 15 GB、
git には載らない。そこで **1 秒バーに落として保存**する — カツオの機構は 15 分足の
ヒゲなので秒の分解能があれば足り、圧縮後は 1 日約 0.67 MB(1 年で約 245 MB)。
**1 秒に潰すと失われるもの**(個々の約定サイズの分布)を補うため、
`max_size`(その秒の最大約定)と `n_large`(閾値超えの本数)も併せて残す —
清算の連鎖は「大口が何本入ったか」で見えるため。
生を残したい場合は `--keep-raw`(1 日 30 MB。置き場所がある時だけ)。

被覆は `progress.json` が真実。取れなかった日と、取ったが空だった日を区別する。

Usage:
    python scripts/fetch_bitmex_archive.py --from 2019-01-01 --to 2019-12-31
    python scripts/fetch_bitmex_archive.py --from 2019-09-01 --to 2019-09-30 --keep-raw
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[1]
BASE = "https://s3-eu-west-1.amazonaws.com/public.bitmex.com/data/trade/"
UA = {"User-Agent": "bitflyer-bot research archive mirror"}
LARGE_TRADE = 100_000          # 枚。これ以上を「大口」として数える(XBTUSD は 1 枚 = 1 USD)
COLUMNS = ["ts", "o", "h", "l", "c", "vol", "buy_vol", "n", "max_size", "n_large"]

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass


def _log(msg: str) -> None:
    print(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}", flush=True)


def fetch_day(day: date, retries: int = 4) -> bytes | None:
    """その日の全銘柄 csv.gz。存在しない日は None(アーカイブに欠けている日がある)。"""
    url = f"{BASE}{day:%Y%m%d}.csv.gz"
    backoff = 2.0
    for _ in range(retries):
        try:
            r = requests.get(url, timeout=300, headers=UA)
        except Exception as e:  # noqa: BLE001
            _log(f"  通信失敗 {type(e).__name__}: {str(e)[:80]} — {backoff:.0f}s 後に再試行")
        else:
            if r.status_code == 200:
                return r.content
            if r.status_code in (403, 404):
                return None            # その日は配布されていない
            _log(f"  HTTP {r.status_code} — {backoff:.0f}s 後に再試行")
        time.sleep(backoff)
        backoff = min(backoff * 2, 30.0)
    raise RuntimeError(f"取得できなかった: {day}")


def to_seconds(blob: bytes, symbol: str) -> tuple[list[list], int, int]:
    """1 秒バーに畳む。返り値は (行, その銘柄の約定数, 全銘柄の約定数)。"""
    text = gzip.decompress(blob).decode("utf-8", errors="replace")
    bars: dict[str, list] = {}
    kept = total = 0
    for row in csv.DictReader(io.StringIO(text)):
        total += 1
        if row.get("symbol") != symbol:
            continue
        kept += 1
        try:
            price = float(row["price"])
            size = float(row["size"])
        except (TypeError, ValueError):
            continue
        # BitMEX の時刻は "2019-09-04D00:00:02.645644000"
        sec = row["timestamp"][:19].replace("D", "T")
        bar = bars.get(sec)
        buy = size if row.get("side") == "Buy" else 0.0
        big = 1 if size >= LARGE_TRADE else 0
        if bar is None:
            bars[sec] = [sec, price, price, price, price, size, buy, 1, size, big]
        else:
            bar[2] = max(bar[2], price)
            bar[3] = min(bar[3], price)
            bar[4] = price
            bar[5] += size
            bar[6] += buy
            bar[7] += 1
            bar[8] = max(bar[8], size)
            bar[9] += big
    return list(bars.values()), kept, total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="XBTUSD")
    ap.add_argument("--from", dest="frm", required=True, help="YYYY-MM-DD")
    ap.add_argument("--to", dest="to", required=True, help="YYYY-MM-DD")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--keep-raw", action="store_true",
                    help="その銘柄の生の約定も残す(1 日約 30 MB。置き場所がある時だけ)")
    args = ap.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else (
        REPO / "backtest_data" / f"bitmex_trade_1s_{args.symbol}")
    out_dir.mkdir(parents=True, exist_ok=True)
    prog_path = out_dir / "progress.json"
    progress: dict[str, dict] = (
        json.loads(prog_path.read_text(encoding="utf-8")) if prog_path.exists() else {})

    d0 = date.fromisoformat(args.frm)
    d1 = date.fromisoformat(args.to)
    days = [d0 + timedelta(days=i) for i in range((d1 - d0).days + 1)]
    todo = [d for d in days if d.isoformat() not in progress]
    _log(f"{args.symbol}: {d0} 〜 {d1} = {len(days)} 日、うち未取得 {len(todo)}")

    for i, day in enumerate(todo, 1):
        blob = fetch_day(day)
        if blob is None:
            progress[day.isoformat()] = {"bars": 0, "trades": 0, "absent": True}
            _log(f"  {day}: アーカイブに無い")
            continue
        bars, kept, total = to_seconds(blob, args.symbol)
        year_dir = out_dir / f"{day:%Y}"
        year_dir.mkdir(exist_ok=True)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(COLUMNS)
        w.writerows(sorted(bars))
        (year_dir / f"{day:%Y%m%d}.csv.gz").write_bytes(
            gzip.compress(buf.getvalue().encode("utf-8"), 6))
        if args.keep_raw:
            raw_dir = out_dir / "raw" / f"{day:%Y}"
            raw_dir.mkdir(parents=True, exist_ok=True)
            text = gzip.decompress(blob).decode("utf-8", errors="replace")
            rd = csv.DictReader(io.StringIO(text))
            rb = io.StringIO()
            rw = csv.DictWriter(rb, fieldnames=rd.fieldnames)
            rw.writeheader()
            rw.writerows(r for r in rd if r.get("symbol") == args.symbol)
            (raw_dir / f"{day:%Y%m%d}.csv.gz").write_bytes(
                gzip.compress(rb.getvalue().encode("utf-8"), 6))
        progress[day.isoformat()] = {"bars": len(bars), "trades": kept,
                                     "trades_all_symbols": total, "absent": False}
        if i % 10 == 0 or i == len(todo):
            prog_path.write_text(json.dumps(progress, separators=(",", ":")), encoding="utf-8")
            _log(f"  {i}/{len(todo)}  {day}  秒バー {len(bars)}  約定 {kept}")

    prog_path.write_text(json.dumps(progress, separators=(",", ":")), encoding="utf-8")
    got = {k: v for k, v in progress.items() if not v["absent"]}
    (out_dir / "MANIFEST.json").write_text(json.dumps({
        "source": BASE,
        "symbol": args.symbol,
        "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "why_now": "BitMEX announced the exchange closes 2026-09-23 and XBTUSD settles "
                   "2026-09-16 12:00 UTC (its own announcement API, read 2026-09-09). "
                   "The public trade archive already stops at 2025-02-22 and is not "
                   "guaranteed to outlive the exchange.",
        "resolution": "1-second bars derived from tick data; raw ticks kept only where "
                      "--keep-raw was used. o/h/l/c/vol/buy_vol/n plus max_size and "
                      f"n_large (trades >= {LARGE_TRADE}) to retain trade-size texture.",
        # 累積(progress 全体)と今回ぶんを混ぜない。混ぜると
        # 「731 日要求して 1,826 日ぶんある」という無意味な行になる。
        "days_requested_this_run": len(days),
        "range_this_run": [d0.isoformat(), d1.isoformat()],
        "days_covered_total": len(got),
        "range_covered_total": [min(got), max(got)] if got else None,
        "days_absent_from_archive": sum(1 for v in progress.values() if v["absent"]),
        "bars": sum(v["bars"] for v in got.values()),
        "trades": sum(v["trades"] for v in got.values()),
        "coverage_note": "progress.json is the truth about coverage: a date missing from "
                         "it was never fetched; a date present with absent=true is not "
                         "published by BitMEX.",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    _log(f"完了: {len(got)} 日 / 秒バー {sum(v['bars'] for v in got.values())} -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
