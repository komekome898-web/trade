#!/usr/bin/env python3
"""Coinalyze の清算履歴(足ごとの集計)で、自前記録の穴を埋める。**オーナー PC で実行する**
(鍵 `COINALYZE_API_KEY` は PC の `.env` にだけある。手順 P9)。

なぜあるか(2026-09-21、L-325): 自前の清算記録器(`record_liquidations.py`)の Bybit が
2026-09-16 00:47 UTC〜09-19 07:09 UTC、OKX が 09-14 21:57 UTC〜09-19 07:09 UTC の間、
止まっていた(接続の時間切れで venue の仕事が終了していた)。1 件ごとの履歴を遡れる経路は
Bybit・OKX には無い(`docs/DATA/surveys/LIQUIDATION_HISTORY_SURVEY.md`: OKX は約 24 時間、
Bybit は無し)。**唯一の経路は Coinalyze の 1 分足の集計(ロング清算量 / ショート清算量)で、
遡れるのは約 7 日**(2026-09-08 実測、L-031)。これは 1 件ごとの記録の代わりにはならない
(連鎖の 60 秒の間隔は 1 分足では潰れる)。**埋まるのは「その分にどれだけ清算されたか」だけ**。

設計上の約束(`fetch_gate_liquidations.py` と同じ):
- 返ってきた点をそのまま保存する(`t`, `l`, `s` の列。解釈しない)。生の応答も `raw/` に残す。
- 窓ごとの取得結果を `.progress.json` に残す(0 点だった窓と、まだ取っていない窓を区別する)。
- 再実行は続きから。
- 制限は 1 分 40 回。1 回ごとに 1.6 秒待つ。429 は `Retry-After` に従う。

Usage(PC の `.venv` で。鍵は環境変数か `.env`):
    python scripts/fetch_coinalyze_liquidations.py --exchanges bybit,okx \
        --from 2026-09-14T21:00:00Z --to 2026-09-19T08:00:00Z
    python scripts/fetch_coinalyze_liquidations.py --list-markets          # 銘柄の対応表だけ出す
    python scripts/fetch_coinalyze_liquidations.py --dry-run ...           # 打つ予定の窓を出すだけ
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

API = "https://api.coinalyze.net/v1"
WINDOW_H = 6            # 1 分足 360 点 / 回
SLEEP_SEC = 1.6         # 40 回 / 分 の制限
INTERVAL = "1min"
DEFAULT_BASE = "BTC"
DEFAULT_QUOTES = ("USDT", "USD")


def load_key() -> str:
    key = os.environ.get("COINALYZE_API_KEY", "").strip()
    if not key and Path(".env").exists():
        for line in Path(".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("COINALYZE_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit("COINALYZE_API_KEY が無い(環境変数か .env)。手順 P9。")
    return key


def parse_ts(s: str) -> datetime:
    return datetime.strptime(s.rstrip("Z"), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def get(session: requests.Session, key: str, path: str, params: dict | None = None,
        retries: int = 5) -> tuple[int, object]:
    delay = 2.0
    for attempt in range(retries):
        try:
            r = session.get(f"{API}{path}", params=params, headers={"api_key": key}, timeout=30)
        except Exception as e:  # noqa: BLE001
            print(f"{path}: {type(e).__name__}: {str(e)[:100]} — {delay:.0f}s 後に再試行",
                  file=sys.stderr, flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 60)
            continue
        if r.status_code == 429:
            wait = float(r.headers.get("Retry-After", "5") or 5)
            print(f"{path}: 429 — {wait:.0f}s 待つ", file=sys.stderr, flush=True)
            time.sleep(wait + 0.5)
            continue
        if r.status_code == 200:
            return 200, r.json()
        return r.status_code, r.text[:200]
    return 0, f"{retries} 回失敗"


def resolve_markets(session, key, exchanges: list[str], base: str, quotes: tuple[str, ...]) -> list[dict]:
    """取引所名(部分一致、大小無視)→ 無期限先物の銘柄。`/exchanges` の code と
    `/future-markets` の exchange を突き合わせる。"""
    st, ex = get(session, key, "/exchanges")
    if st != 200:
        sys.exit(f"/exchanges: {st} {ex}")
    time.sleep(SLEEP_SEC)
    st, mk = get(session, key, "/future-markets")
    if st != 200:
        sys.exit(f"/future-markets: {st} {mk}")
    codes = {}
    for e in ex:
        for want in exchanges:
            if want.lower() in str(e.get("name", "")).lower() or want.lower() == str(e.get("code", "")).lower():
                codes[e["code"]] = e["name"]
    out = []
    for m in mk:
        if (m.get("exchange") in codes and m.get("is_perpetual") and m.get("base_asset") == base
                and m.get("quote_asset") in quotes):
            out.append({**m, "exchange_name": codes[m["exchange"]]})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exchanges", default="bybit,okx", help="取引所名(部分一致)をカンマ区切り")
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--quotes", default=",".join(DEFAULT_QUOTES))
    ap.add_argument("--from", dest="frm", default=None, help="UTC ISO-8601(例 2026-09-14T21:00:00Z)")
    ap.add_argument("--to", dest="to", default=None)
    ap.add_argument("--interval", default=INTERVAL)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--list-markets", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    key = load_key()
    session = requests.Session()
    exchanges = [x.strip() for x in args.exchanges.split(",") if x.strip()]
    markets = resolve_markets(session, key, exchanges, args.base,
                              tuple(q.strip() for q in args.quotes.split(",")))
    print("銘柄の対応表:", flush=True)
    for m in markets:
        print(f"  {m['symbol']:24s} {m['exchange_name']:12s} {m['symbol_on_exchange']:20s} "
              f"{m['base_asset']}/{m['quote_asset']} margined={m.get('margined')} "
              f"denominated={m.get('oi_lq_vol_denominated_in')}", flush=True)
    if args.list_markets:
        return 0
    if not markets:
        sys.exit("該当する銘柄が無い。--list-markets で確かめる。")
    if not (args.frm and args.to):
        sys.exit("--from と --to が要る")

    frm, to = parse_ts(args.frm), parse_ts(args.to)
    out_dir = Path(args.out_dir or
                   f"backtest_data/coinalyze_liquidations_{datetime.now(timezone.utc):%Y%m%d}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "raw").mkdir(exist_ok=True)
    progress_path = out_dir / ".progress.json"
    progress = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.exists() else {}
    (out_dir / "markets.json").write_text(json.dumps(markets, indent=1, ensure_ascii=False),
                                          encoding="utf-8")

    windows = []
    t = frm
    while t < to:
        t2 = min(t + timedelta(hours=WINDOW_H), to)
        windows.append((t, t2))
        t = t2
    symbols = [m["symbol"] for m in markets]
    print(f"窓 {len(windows)} × 銘柄 {len(symbols)}(1 回で最大 20 銘柄)", flush=True)
    if args.dry_run:
        for a, b in windows:
            print(f"  {a:%Y-%m-%dT%H:%M}Z .. {b:%Y-%m-%dT%H:%M}Z symbols={','.join(symbols)}")
        return 0

    rows: dict[str, list[tuple]] = {s: [] for s in symbols}
    for a, b in windows:
        wkey = f"{a:%Y%m%dT%H%M}_{b:%Y%m%dT%H%M}"
        if wkey in progress.get("windows", {}):
            continue
        params = {"symbols": ",".join(symbols), "interval": args.interval,
                  "from": int(a.timestamp()), "to": int(b.timestamp()), "convert_to_usd": "false"}
        st, body = get(session, key, "/liquidation-history", params)
        time.sleep(SLEEP_SEC)
        if st != 200:
            progress.setdefault("failed", {})[wkey] = f"{st} {body}"
            progress_path.write_text(json.dumps(progress, indent=1), encoding="utf-8")
            print(f"{wkey}: 失敗 {st} {body}", file=sys.stderr, flush=True)
            continue
        (out_dir / "raw" / f"{wkey}.json").write_text(json.dumps(body), encoding="utf-8")
        counts = {}
        for item in body:
            sym = item.get("symbol")
            pts = item.get("history", [])
            counts[sym] = len(pts)
            for p in pts:
                rows.setdefault(sym, []).append((p.get("t"), p.get("l"), p.get("s")))
        progress.setdefault("windows", {})[wkey] = counts
        progress_path.write_text(json.dumps(progress, indent=1), encoding="utf-8")
        print(f"{wkey}: {counts}", flush=True)

    # 銘柄ごとに 1 本の csv(既存があれば結合、t で一意化)
    for sym, new in rows.items():
        path = out_dir / f"{sym.replace('/', '_')}_{args.interval}.csv"
        by_t: dict[str, tuple] = {}
        if path.exists():
            with open(path, encoding="utf-8", newline="") as fh:
                rd = csv.reader(fh)
                next(rd, None)
                for r in rd:
                    by_t[r[0]] = tuple(r)
        for r in new:
            by_t[str(r[0])] = tuple(str(x) for x in r)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["t", "l", "s"])
            w.writerows(sorted(by_t.values(), key=lambda r: int(r[0])))
    md5 = [f"{hashlib.md5(p.read_bytes()).hexdigest()}  {p.name}"
           for p in sorted(out_dir.glob("*.csv"))]
    (out_dir / "MD5SUMS").write_text("\n".join(md5) + "\n", encoding="utf-8")
    print(f"完了: 窓 {len(progress.get('windows', {}))} 取得 / 失敗 {len(progress.get('failed', {}))}",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
