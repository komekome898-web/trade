#!/usr/bin/env python3
"""bitFlyer の公開約定履歴(`GET /v1/getexecutions`)を、時刻の範囲で遡って取り込む。

なぜあるか(2026-09-21、L-325): PC 側の `fetch_all.bat`(`extract_tape.py`)の出力が
2026-09-18 07:24 UTC で止まり、共有 `paper_logs/tape/executions_*.csv.gz` に穴が空いた。
`data/ws` の生記録は PC に残っているので本来はそこから復元するが、PC の作業を待つ間の
橋渡しと突き合わせ用に、この環境から届く公開 API(31 日で消える)で同じ列の約定を取る。

API の制約(2026-09-21 実測):
- `count` の上限は 500。`before`(約定 id)で古い方へ頁送り。1 頁 0.7〜1.2 秒。
- `exec_date` は ISO-8601(UTC、`Z` 無し、ミリ秒精度)。tape(`extract_tape.py`)の
  `ts` は WS の 7 桁精度なので**同じ約定でも文字列は一致しない**。突き合わせは
  (price, size, side) と秒単位の時刻で行う。
- 公開 API の制限は 5 分 500 回。1 秒に 1 回未満で打つ。

設計上の約束(`fetch_gate_liquidations.py` と同じ):
- 返ってきた行をそのまま列に写す(`ts,price,size,side,id`。先頭 4 列は tape と同じ、
  5 列目は約定 id。同じミリ秒・同じ値段・同じ量・同じ側の約定が実在するので、id 無しでは
  重複除去ができない — 実測: 10 分の窓で 1,172 行のうち 28 行が 4 列では同一)。解釈しない。
- 進捗を `.progress.json` に残す(取得済みの最古 id と時刻)。再実行は続きから。
- 失敗した頁は 5 回まで待って再試行し、それでも駄目なら止めて進捗を残す。

Usage:
    python scripts/fetch_bitflyer_executions_range.py --since 2026-09-18T07:24:44Z
    python scripts/fetch_bitflyer_executions_range.py --since ... --until 2026-09-21T00:00:00Z \
        --out-dir backtest_data/bitflyer_executions_backfill_20260921
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "https://api.bitflyer.com/v1/getexecutions"
PAGE = 500
MIN_INTERVAL_SEC = 0.8


def parse_ts(s: str) -> datetime:
    s = s.rstrip("Z")
    if "." in s:
        head, frac = s.split(".")
        frac = (frac + "000000")[:6]
        s = f"{head}.{frac}"
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def fetch_page(session: requests.Session, product: str, before: int | None,
               retries: int = 5) -> list[dict]:
    params: dict = {"product_code": product, "count": PAGE}
    if before is not None:
        params["before"] = before
    delay = 2.0
    for attempt in range(retries):
        try:
            r = session.get(BASE, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            note = f"HTTP {r.status_code} {r.text[:120]}"
        except Exception as e:  # noqa: BLE001
            note = f"{type(e).__name__}: {str(e)[:120]}"
        print(f"page before={before}: {note} — {delay:.0f}s 後に再試行 ({attempt + 1}/{retries})",
              file=sys.stderr, flush=True)
        time.sleep(delay)
        delay = min(delay * 2, 60)
    raise RuntimeError(f"page before={before}: {retries} 回失敗")


class DayWriter:
    """UTC 日ごとに executions_YYYYMMDD.csv.gz へ書く。古い方へ進むので行は逆順で溜め、
    日が変わった時点で反転して書き出す。"""

    def __init__(self, out_dir: Path):
        self.out_dir = out_dir
        self.day: str | None = None
        self.rows: list[tuple] = []
        self.written: dict[str, int] = {}

    def add(self, ts: datetime, row: tuple) -> None:
        day = ts.strftime("%Y%m%d")
        if self.day is not None and day != self.day:
            self.flush()
        self.day = day
        self.rows.append(row)

    def flush(self) -> None:
        if self.day is None or not self.rows:
            return
        path = self.out_dir / f"executions_{self.day}.csv.gz"
        # 続きからの再実行で同じ日に追記することがある: 既存の行を読んで結合し、時刻順で書き直す
        existing: list[tuple] = []
        if path.exists():
            with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
                rd = csv.reader(fh)
                next(rd, None)
                existing = [tuple(r) for r in rd]
        by_id = {r[4]: r for r in existing}
        for r in reversed(self.rows):
            by_id[str(r[4])] = tuple(str(x) for x in r)
        merged = sorted(by_id.values(), key=lambda r: (r[0], int(r[4])))
        tmp = path.with_suffix(".tmp")
        with gzip.open(tmp, "wt", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["ts", "price", "size", "side", "id"])
            w.writerows(merged)
        tmp.replace(path)
        self.written[self.day] = len(merged)
        self.rows = []
        self.day = None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", default="FX_BTC_JPY")
    ap.add_argument("--since", required=True, help="この時刻(UTC、ISO-8601)より新しい約定を取る")
    ap.add_argument("--until", default=None, help="この時刻以前から遡る(省略 = 今)")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--max-pages", type=int, default=0, help="0 = 制限なし")
    args = ap.parse_args()

    since = parse_ts(args.since)
    until = parse_ts(args.until) if args.until else None
    out_dir = Path(args.out_dir or
                   f"backtest_data/bitflyer_executions_backfill_{datetime.now(timezone.utc):%Y%m%d}")
    out_dir.mkdir(parents=True, exist_ok=True)
    progress_path = out_dir / ".progress.json"
    progress = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.exists() else {}

    before = progress.get("oldest_id")
    if before is not None:
        print(f"続きから: before={before} ({progress.get('oldest_ts')})", flush=True)
    session = requests.Session()
    writer = DayWriter(out_dir)
    pages = 0
    total = 0
    t_last = 0.0
    done = False
    while not done:
        wait = MIN_INTERVAL_SEC - (time.time() - t_last)
        if wait > 0:
            time.sleep(wait)
        t_last = time.time()
        page = fetch_page(session, args.product, before)
        pages += 1
        if not page:
            print("空の頁 — 履歴の端に達した(31 日)", flush=True)
            break
        for r in page:
            ts = parse_ts(r["exec_date"])
            if until is not None and ts > until:
                continue
            if ts < since:
                done = True
                break
            writer.add(ts, (r["exec_date"], r["price"], r["size"], r["side"], r["id"]))
            total += 1
        before = page[-1]["id"]
        progress = {"product": args.product, "since": args.since, "until": args.until,
                    "oldest_id": before, "oldest_ts": page[-1]["exec_date"],
                    "pages": progress.get("pages", 0) + 1,
                    "rows": progress.get("rows", 0) + len(page),
                    "updated_at": datetime.now(timezone.utc).isoformat()}
        if pages % 50 == 0:
            writer.flush()
            progress_path.write_text(json.dumps(progress, indent=1), encoding="utf-8")
            print(f"{pages} 頁 / {total} 行 / 最古 {page[-1]['exec_date']}", flush=True)
        if args.max_pages and pages >= args.max_pages:
            break
    writer.flush()
    progress["done"] = done
    progress_path.write_text(json.dumps(progress, indent=1), encoding="utf-8")

    md5 = []
    for p in sorted(out_dir.glob("executions_*.csv.gz")):
        md5.append(f"{hashlib.md5(p.read_bytes()).hexdigest()}  {p.name}")
    (out_dir / "MD5SUMS").write_text("\n".join(md5) + "\n", encoding="utf-8")
    print(f"完了 done={done} 頁={pages} 行={total} 日別={writer.written}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
