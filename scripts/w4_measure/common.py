"""W4 の測定(カード 2 の変種 (a)、カード 3)で共有する入力の組み立て。

封印の門(bot.bt.data の load / load_reference)だけを通して読む。参考にした台本:
scratchpad/w4/c1_rewrite/compare.py(読むだけ。書き換えていない)。

  持つ足: bot.bt.data.load(kind bar、ts = 1 分の始まり、gap は accept、no_trade は drop)
  参照:   bot.bt.data.reference.load_reference(行の時刻 = 置き場の時刻のまま、lag_ns 60 秒)
"""
from __future__ import annotations

import hashlib
import os
import resource
import time
from datetime import datetime, timezone

NS = 1_000_000_000
MIN_NS = 60 * NS
DAY_NS = 86_400 * NS
SEAL = datetime(2023, 12, 18, tzinfo=timezone.utc)
ROOT = "/home/user/trade"

FX_DIR = "backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906"
SPOT_DIR = "backtest_data/bitflyer_lightchart_BTC_JPY_1m_20260906"
BAR_FILE = "candles_1m_{y}.csv.gz"
BIN_DIR = "backtest_data/binance_BTCUSDT_1m_20170801_20231231"
BIN_FILE = "binance_BTCUSDT_1m_{y}.csv.gz"
USDJPY_PATH = "backtest_data/fx_usdjpy_1m_20170801_20221231/usdjpy_1m.csv.gz"
BAR_RESOLVE = {"gap": "accept", "no_trade": "drop"}


def to_ns(d: datetime) -> int:
    return int(d.timestamp()) * NS


def iso(s: str) -> int:
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return to_ns(d)


def to_iso(ns: int) -> str:
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_end(hi_ns: int) -> None:
    if hi_ns > to_ns(SEAL):
        raise SystemExit(f"拒否: 終わり {to_iso(hi_ns)} は封印の境 {SEAL.isoformat()} より後")


def years(lo_ns: int, hi_ns: int) -> range:
    y0 = datetime.fromtimestamp(lo_ns / 1e9, tz=timezone.utc).year
    y1 = datetime.fromtimestamp((hi_ns - 1) / 1e9, tz=timezone.utc).year
    return range(y0, y1 + 1)


def paths(d: str, pattern: str, lo_ns: int, hi_ns: int) -> list:
    return [f"{d}/{pattern.format(y=y)}" for y in years(lo_ns, hi_ns)
            if os.path.exists(os.path.join(ROOT, d, pattern.format(y=y)))]


def bar_dataset(d: str, symbol: str, lo_ns: int, hi_ns: int, name: str = "bars") -> dict:
    check_end(hi_ns)
    return {"name": name, "paths": paths(d, BAR_FILE, lo_ns, hi_ns), "range_ns": [lo_ns, hi_ns],
            "spec": {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip", "kind": "bar",
                     "symbol": symbol, "asset": "crypto",
                     "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
                     "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
                     "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start",
                     "no_trade": {"fields": ["open", "high", "low", "close"]}}}


def binance_ref_dataset(name: str, column: str, lo_ns: int, hi_ns: int) -> dict:
    check_end(hi_ns)
    return {"name": name, "paths": paths(BIN_DIR, BIN_FILE, lo_ns, hi_ns), "range_ns": [lo_ns, hi_ns],
            "spec": {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip",
                     "time": {"columns": ["open_time"], "unit": "iso", "tz": "UTC"}, "value": column}}


def usdjpy_ref_dataset(name: str, lo_ns: int, hi_ns: int) -> dict:
    check_end(hi_ns)
    return {"name": name, "paths": [USDJPY_PATH], "range_ns": [lo_ns, hi_ns],
            "spec": {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip",
                     "time": {"columns": ["timestamp"], "unit": "iso", "tz": "UTC"}, "value": "close"}}


def load_bars(d: str, symbol: str, lo_ns: int, hi_ns: int):
    """(BarEvent のリスト, 異常の種類, 読んだファイルの一覧)。"""
    from bot.bt.data.loader import load
    res = load(ROOT, [bar_dataset(d, symbol, lo_ns, hi_ns)])
    kinds = {}
    for a in res.anomalies("bars"):
        kinds[a["kind"]] = kinds.get(a["kind"], 0) + 1
    bars = list(res.events("bars", BAR_RESOLVE))
    files = [f.__dict__ if hasattr(f, "__dict__") else str(f) for f in res.files()]
    return bars, kinds, res.hashes()


def _unused_sha256_file(path: str) -> str:  # 使わない(sha256 は門の manifest から取る)
    h = hashlib.sha256()
    with open(os.path.join(ROOT, path), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def peak_rss_gb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024


class Clock:
    def __init__(self) -> None:
        self.t0 = time.time()
        self.marks = []

    def mark(self, what: str) -> None:
        dt = time.time() - self.t0
        self.marks.append((what, round(dt, 1), round(peak_rss_gb(), 2)))
        print(f"[{dt:8.1f}s 最大RSS {peak_rss_gb():5.2f}GB] {what}", flush=True)
