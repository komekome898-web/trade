"""bitFlyer 約定の取り直しを、一番古い日(先に取り元から消える日)から 1 日ずつ行う(L-989)。

各日 D について: D+1 00:00 UTC 直後の約定 id を二分探索で見つけ、そこから古い方へ D 00:00 まで頁送りする。
書き込みは scripts/fetch_bitflyer_executions_range.py の DayWriter(同じ日の既存の行と id で結合)をそのまま使う。
"""
import importlib.util
import json
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path("/home/user/trade")
spec = importlib.util.spec_from_file_location("fbx", ROOT / "scripts/fetch_bitflyer_executions_range.py")
fbx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fbx)

OUT = ROOT / "backtest_data/bitflyer_executions_backfill_20261010"
S = requests.Session()
_last = [0.0]


def get(before=None, count=1):
    w = fbx.MIN_INTERVAL_SEC - (time.time() - _last[0])
    if w > 0:
        time.sleep(w)
    _last[0] = time.time()
    params = {"product_code": "FX_BTC_JPY", "count": count}
    if before is not None:
        params["before"] = before
    for attempt in range(5):
        r = S.get(fbx.BASE, params=params, timeout=30)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 400 or "-156" in r.text:
            return None  # 31 日より古い
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(r.text[:200])


def id_after(t: datetime, lo: int, hi: int) -> int:
    """exec_date >= t となる最小の id(の近く)。before=x は id < x の最新 1 件を返す。"""
    while hi - lo > 1:
        mid = (lo + hi) // 2
        page = get(before=mid)
        if not page:
            lo = mid
            continue
        ts = fbx.parse_ts(page[0]["exec_date"])
        if ts < t:
            lo = mid
        else:
            hi = mid
    return hi


def fetch_day(d: date, before: int):
    since = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    writer = fbx.DayWriter(OUT)
    n = pages = 0
    while True:
        page = get(before=before, count=fbx.PAGE)
        pages += 1
        if not page:
            print(f"{d}: 空の頁(31 日の端)", flush=True)
            break
        done = False
        for r in page:
            ts = fbx.parse_ts(r["exec_date"])
            if ts.date() > d:
                continue
            if ts < since:
                done = True
                break
            writer.add(ts, (r["exec_date"], r["price"], r["size"], r["side"], r["id"]))
            n += 1
        before = page[-1]["id"]
        if done:
            break
    writer.flush()
    print(f"{d}: {n} 行 / {pages} 頁 / {datetime.now(timezone.utc):%H:%M:%S}", flush=True)


def main():
    first = date.fromisoformat(sys.argv[1])
    last = date.fromisoformat(sys.argv[2])
    latest = get()[0]["id"]
    lo = 2_640_000_000
    d = first
    while d <= last:
        end = datetime(d.year, d.month, d.day, tzinfo=timezone.utc) + timedelta(days=1)
        bid = id_after(end, lo, latest + 1)
        fetch_day(d, bid)
        lo = bid - 1
        d += timedelta(days=1)
    print("完了", flush=True)


if __name__ == "__main__":
    main()
