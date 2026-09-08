#!/usr/bin/env python3
"""清算(強制決済)ストリームの記録 — `data/liquidations/<venue>_<YYYYMMDD>.jsonl.gz`。

**このデータは買えない。記録を始めた日から先しか残らない。**(`docs/DATA_PERISHABILITY.md` §2)
止まっている間の清算は永久に空白になるので、`deploy/start_all.bat` で常駐させる。

読み取り専用・認証なし・発注なし。書くのは上記ファイルだけ。

設計上の約束:
- **生のメッセージをそのまま残す**。今この機構をまだ理解していないので、こちらの解釈で
  列を削らない。解析は後段(読み手)の仕事。
- 1 行 = 1 メッセージ。`{"venue", "recv_us", "raw"}`。`recv_us` は**受信時刻**であって
  取引所のタイムスタンプではない(それは `raw` の中にある)。両方要る — 遅延が測れる。
- UTC 日付でファイルを切り替える。追記のみ。再接続で重複しうるので、**読み手が重複を潰す**
  前提にする(生を消さないため)。
- 切断は起きるものとして扱う。指数バックオフで再接続し、1 行だけログに出す。

Usage:
    python scripts/record_liquidations.py                     # 到達確認済みの既定ベニュー
    python scripts/record_liquidations.py --venues bitmex,okx
    python scripts/record_liquidations.py --minutes 5         # 試運転
"""
from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import ssl
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import websockets
except ImportError:
    print("websockets が要ります: pip install -e \".[dev]\"", file=sys.stderr)
    raise SystemExit(2)

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "data" / "liquidations"

# 購読の定義。`keepalive` はその取引所が要求する生存確認(None なら
# websockets 自身の ping フレームで足りる)。
VENUES: dict[str, dict] = {
    "binance_um": {
        "url": "wss://fstream.binance.com/ws/!forceOrder@arr",
        "sub": None,
        "keepalive": None,
    },
    "bybit": {
        "url": "wss://stream.bybit.com/v5/public/linear",
        "sub": {"op": "subscribe", "args": ["allLiquidation.BTCUSDT"]},
        "keepalive": ({"op": "ping"}, 20.0),
    },
    "okx": {
        "url": "wss://ws.okx.com:8443/ws/v5/public",
        "sub": {"op": "subscribe",
                "args": [{"channel": "liquidation-orders", "instType": "SWAP"}]},
        "keepalive": ("ping", 20.0),          # OKX は文字列 "ping" を要求する
    },
    "bitmex": {
        "url": "wss://ws.bitmex.com/realtime?subscribe=liquidation:XBTUSD",
        "sub": None,
        "keepalive": ("ping", 25.0),
    },
}

BACKOFF_START = 2.0
BACKOFF_MAX = 120.0


def _log(msg: str) -> None:
    print(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}", flush=True)


class Writer:
    """UTC 日付ごとの gzip JSONL。追記のみ、日付をまたいだら開き直す。"""

    def __init__(self, venue: str) -> None:
        self.venue = venue
        self._day: str | None = None
        self._fh = None
        self.lines = 0

    def write(self, obj: dict) -> None:
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        if day != self._day:
            self.close()
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            path = OUT_DIR / f"{self.venue}_{day}.jsonl.gz"
            self._fh = gzip.open(path, "at", encoding="utf-8")
            self._day = day
            _log(f"{self.venue}: -> {path.name}")
        self._fh.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")
        self._fh.flush()
        self.lines += 1

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None


async def _keepalive(ws, payload, period: float) -> None:
    while True:
        await asyncio.sleep(period)
        await ws.send(payload if isinstance(payload, str) else json.dumps(payload))


async def record_venue(venue: str, deadline: float | None) -> None:
    spec = VENUES[venue]
    writer = Writer(venue)
    backoff = BACKOFF_START
    try:
        while deadline is None or time.monotonic() < deadline:
            try:
                async with websockets.connect(
                    spec["url"], ssl=ssl.create_default_context(),
                    open_timeout=25, close_timeout=5, max_queue=4096,
                ) as ws:
                    _log(f"{venue}: 接続")
                    backoff = BACKOFF_START
                    if spec["sub"]:
                        await ws.send(json.dumps(spec["sub"]))
                    ka = None
                    if spec["keepalive"]:
                        payload, period = spec["keepalive"]
                        ka = asyncio.create_task(_keepalive(ws, payload, period))
                    try:
                        while deadline is None or time.monotonic() < deadline:
                            timeout = None if deadline is None else max(
                                1.0, deadline - time.monotonic())
                            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                            try:
                                parsed = json.loads(raw)
                            except (ValueError, TypeError):
                                parsed = {"_unparsed": str(raw)[:2000]}
                            writer.write({"venue": venue,
                                          "recv_us": int(time.time() * 1_000_000),
                                          "raw": parsed})
                    finally:
                        if ka is not None:
                            ka.cancel()
            except asyncio.TimeoutError:
                break                       # --minutes に達しただけ
            except asyncio.CancelledError:
                raise
            except Exception as e:          # noqa: BLE001 - 切断は通常運転
                _log(f"{venue}: 切断 {type(e).__name__}: {str(e)[:120]} "
                     f"— {backoff:.0f}s 後に再接続")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, BACKOFF_MAX)
    finally:
        writer.close()
        _log(f"{venue}: 終了 {writer.lines} 行")


async def run(venues: list[str], minutes: float | None) -> None:
    deadline = None if minutes is None else time.monotonic() + minutes * 60
    await asyncio.gather(*(record_venue(v, deadline) for v in venues))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--venues", default=",".join(VENUES),
                    help="カンマ区切り。既定は全部(届かないものは再接続を繰り返すだけで無害)")
    ap.add_argument("--minutes", type=float, default=None,
                    help="この分数で止める(既定: Ctrl+C まで走り続ける)")
    args = ap.parse_args()

    venues = [v.strip() for v in args.venues.split(",") if v.strip()]
    unknown = [v for v in venues if v not in VENUES]
    if unknown:
        print(f"不明なベニュー: {unknown}。選べるのは {list(VENUES)}", file=sys.stderr)
        return 2

    _log(f"記録開始: {venues} -> {OUT_DIR}")
    try:
        asyncio.run(run(venues, args.minutes))
    except KeyboardInterrupt:
        _log("停止(Ctrl+C)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
