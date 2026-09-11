#!/usr/bin/env python3
"""清算(強制決済)ストリームの記録 — `data/liquidations/<venue>_<YYYYMMDD>.jsonl.gz`。

**履歴の有無は取引所で違う**(全経路の実測: `docs/DATA_SOURCES/LIQUIDATION_HISTORY_SURVEY.md`)。
Gate.io はローリング約 90 日、OKX は約 24 時間を REST で公開しているが、**Binance と BitMEX は
ストリームのみで履歴が無い** — この 2 つは止まっている間が永久に空白になるので、
`deploy/start_all.bat` で常駐させる。OKX の 24 時間は欠測の修復に使える。

読み取り専用・認証なし・発注なし。書くのは上記ファイルだけ。

設計上の約束:
- **生のメッセージをそのまま残す**。今この機構をまだ理解していないので、こちらの解釈で
  列を削らない。解析は後段(読み手)の仕事。
- 1 行 = 1 メッセージ。`{"venue", "recv_us", "raw"}`。`recv_us` は**受信時刻**であって
  取引所のタイムスタンプではない(それは `raw` の中にある)。両方要る — 遅延が測れる。
- UTC 日付でファイルを切り替える。追記のみ。再接続で重複しうるので、**読み手が重複を潰す**
  前提にする(生を消さないため)。
- 切断は起きるものとして扱う。指数バックオフで再接続し、1 行だけログに出す。

**gzip の書き方(2026-09-12、L-121)**: `Writer` は 1 つの gzip メンバを開いたまま
保持しない。行はメモリ上のバッファに積み、`FLUSH_MAX_LINES` 行(既定 200)か
`FLUSH_INTERVAL_SEC` 秒(既定 5)のどちらか早い方に達したら、バッファを
`gzip.compress()` で**完結した 1 メンバ**にしてから 1 回の追記(`open(path, "ab")`)
で書き出す。清算はバースト性が強く数時間 0 件のこともあるので、時間側のトリガは
「メッセージが来た時にだけ経過時間を見る」方式で、メッセージが無い間はタイマーで
スピンしない。日付が変わった時と `close()` 時にも必ず flush する。
これで**ハードキル(`Stop-Process -Force`)後に壊れるのは直前の未 flush 分だけ**になる
— 以前の `gzip.open(path, "at")` を開いたままにする設計は、キル時に終端マーカーの無い
メンバを残し、再起動後の追記がそのメンバの途中に新しいヘッダを継ぎ足すことで
`zlib.error: invalid block type` を起こしファイル全体を読めなくした(2026-09-11、
オーナー PC で 10 ファイル発生)。回収は `scripts/repair_liquidation_gz.py`
(読み取り専用)。詳細 `docs/OWNER_PROCEDURES.md` P14。

**既存ファイルの自己修復(2026-09-12)**: この修正を配る夜間自動再起動
(オーナー承認、L-125)自体が、修正を取り込む前の旧 `Writer` をハードキルする
— つまり**この修正が入って最初に起動する時、その日のファイルは既に壊れている
可能性がある**。そこで `Writer` は日付を切り替える(=その日のファイルを初めて
使う)たびに、既存ファイルの**最後のメンバが完結しているか**を確認する。
不完全なら、そのファイルには**追記しない** — `<venue>_<day>.truncN.jsonl.gz`
(N は 1, 2, ... で既存を上書きしない)へ退避し、ログに 1 行出してから、
同じファイル名で新規に書き始める。退避したファイルは
`scripts/repair_liquidation_gz.py` が `*.trunc*.jsonl.gz` としてそのまま拾う。

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
import os
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
LOCK_PATH = REPO / "data" / "liquidations.lock"

sys.path.insert(0, str(REPO / "src"))
try:
    from bot.research.gz_members import decompress_piece, split_raw_members
except Exception:  # noqa: BLE001 - 自己修復が読めなくても記録は止めない
    decompress_piece = split_raw_members = None

# **出力で死なせない。** Windows の既定コンソールは cp932 で、そこに cp932 が
# 表現できない文字(em ダッシュなど)を print すると UnicodeEncodeError が上がる。
# 2026-09-09、記録器はこれで**最初の切断時に落ちた** — 例外処理の中の
# ログ行そのものが例外を投げたため。ログは記録の付随物であって、
# 記録を止める理由にしてはならない。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - 古い Python / 差し替えられた stdout
        pass

# 購読の定義。`keepalive` はその取引所が要求する生存確認(None なら
# websockets 自身の ping フレームで足りる)。
VENUES: dict[str, dict] = {
    # USD-M。**接続はできるがデータが来ないことがある**(2026-09-09 実測):
    # 開発セッションの経路では対照の btcusdt@aggTrade すら 0 件、
    # オーナー PC でも 12 時間 0 件。購読名の誤りではなく fstream への
    # 経路の問題と見ている。届く経路では最大手の清算が全銘柄で取れるので残す。
    "binance_um": {
        "url": "wss://fstream.binance.com/ws/!forceOrder@arr",
        "sub": None,
        "keepalive": None,
    },
    # COIN-M。**こちらは実際に届いた**(同 2026-09-09、40 秒で 13 件)。
    # USD-M とは別商品(証拠金が現物建て)なので代替ではなく別系統として持つ。
    "binance_cm": {
        "url": "wss://dstream.binance.com/ws/!forceOrder@arr",
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
LOCK_STALE_SEC = 180.0          # これを過ぎた鍵は死んだプロセスのものとみなす
LOCK_BEAT_SEC = 45.0            # 生きている間はこの間隔で鍵の時刻を更新する

# Writer の flush トリガ(2026-09-12、L-121)。行数優先で、静かな時間帯は
# 秒側が「次のメッセージが来た時」にだけ効く(タイマースレッドでスピンしない)。
FLUSH_MAX_LINES = 200
FLUSH_INTERVAL_SEC = 5.0


def _log(msg: str) -> None:
    print(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}", flush=True)


class Writer:
    """UTC 日付ごとの gzip JSONL。**1 つの gzip メンバを開いたまま保持しない**
    (2026-09-12、L-121 — 経緯はモジュール docstring)。行はメモリのバッファに積み、
    `FLUSH_MAX_LINES` 行か `FLUSH_INTERVAL_SEC` 秒のどちらか早い方に達したら
    `gzip.compress()` で完結した 1 メンバを作って 1 回の `open(path, "ab")` で
    追記する。時間側のトリガは `write()` が呼ばれた時にしか見ないので、
    メッセージが来ない間はタイマーがスピンしない — 静かな時間帯の代償は
    「次のメッセージが来るまで flush されない」だけで、CPU コストは無い。
    日付が変わった時と `close()` 時にも必ず flush する。
    **ハードキルで失われるのは直前の未 flush 分だけ**であり、ファイル全体が
    読めなくなることはない。
    """

    def __init__(self, venue: str) -> None:
        self.venue = venue
        self._day: str | None = None
        self._path: Path | None = None
        self._buf: list[bytes] = []
        self._last_flush = time.monotonic()
        self.lines = 0

    def write(self, obj: dict) -> None:
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        if day != self._day:
            self.flush()
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            path = OUT_DIR / f"{self.venue}_{day}.jsonl.gz"
            self._heal_if_needed(path, day)
            self._path = path
            self._day = day
            self._last_flush = time.monotonic()
            _log(f"{self.venue}: -> {self._path.name}")
        line = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
        self._buf.append(line.encode("utf-8"))
        self.lines += 1
        if self._should_flush():
            self.flush()

    def _heal_if_needed(self, path: Path, day: str) -> None:
        """**その日のファイルを初めて使う時**(=通常の日付切り替え、または
        プロセス再起動直後の最初の write — `__init__` は `_day=None` で
        始まるので、同じ日に再起動しても必ずここを通る)に、既存ファイルの
        **最後のメンバが完結しているか**を検査する。2026-09-12、L-121:
        この修正を配る夜間自動再起動(L-125)自体が旧 `Writer` をハードキル
        するので、修正後の最初の起動時にはまだ壊れたファイルが残っている
        ことが前提。不完全なら**そのファイルには絶対に追記しない**
        — `<venue>_<day>.truncN.jsonl.gz`(N は既存を上書きしない次の番号)
        へ退避し、ログに 1 行出してから、同じファイル名で新規に書き始める。
        退避先は `scripts/repair_liquidation_gz.py` が `*.trunc*.jsonl.gz`
        としてそのまま拾う。検査自体が読めない場合(自己修復機構の import
        失敗)は、記録を止めないために**検査せず追記を続ける**(壊れた
        ファイルへの追記が再発するリスクはあるが、記録停止より優先度が低い)。
        """
        if not path.exists():
            return
        if split_raw_members is None or decompress_piece is None:
            _log(f"{self.venue}: 警告: 自己修復機構を読めないので "
                 f"警告: 自己修復なし - {path.name} の末尾メンバを検査せず追記する")
            return
        try:
            pieces = split_raw_members(path.read_bytes())
            healthy = bool(pieces) and decompress_piece(pieces[-1]).complete
        except Exception as e:  # noqa: BLE001 - 読めない = 不完全とみなす(安全側)
            _log(f"{self.venue}: 警告: {path.name} の検査に失敗 "
                 f"{type(e).__name__}: {str(e)[:80]} — 不完全として退避する")
            healthy = False
        if healthy:
            return
        n = 1
        while True:
            moved = OUT_DIR / f"{self.venue}_{day}.trunc{n}.jsonl.gz"
            if not moved.exists():
                break
            n += 1
        path.rename(moved)
        _log(f"{self.venue}: {path.name} の末尾メンバが不完全 "
             f"-> {moved.name} へ退避して新規作成")

    def _should_flush(self) -> bool:
        if not self._buf:
            return False
        return (len(self._buf) >= FLUSH_MAX_LINES
                or time.monotonic() - self._last_flush >= FLUSH_INTERVAL_SEC)

    def flush(self) -> None:
        """バッファを1個の完結した gzip メンバとして追記する。空なら何もしない。"""
        if not self._buf or self._path is None:
            return
        data = gzip.compress(b"".join(self._buf))
        with open(self._path, "ab") as f:
            f.write(data)
        self._buf = []
        self._last_flush = time.monotonic()

    def close(self) -> None:
        self.flush()


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


def _acquire_lock() -> object | None:
    """**同じファイルに 2 つのプロセスが追記するのを防ぐ。**

    書き出しは gzip の追記なので、2 プロセスが同時に書くとメンバが混ざって
    ファイルごと読めなくなりうる。start_all の起動ガードは stop_all の
    取りこぼしなどで擦り抜けうるので、記録器自身が持つ(2026-09-09)。
    """
    try:
        sys.path.insert(0, str(REPO / "src"))
        from bot.jpx.run_lock import LockBusy, RunLock
    except Exception:  # noqa: BLE001 - 鍵が無いより記録が動く方が大事
        _log("警告: run_lock を読めないので二重起動ガードなしで動く")
        return None
    # 常駐プロセスなので **鍵の時刻を更新し続ける**(`_heartbeat`)。
    # RunLock の陳腐化判定は「取得してからの経過」なので、更新しないと
    # 数分後には自分の鍵が陳腐扱いになり、ガードが無くなってしまう。
    # 逆に更新だけでは、クラッシュ後に鍵が残って**二度と起動できない**ので、
    # 陳腐化の窓は短く取る(落ちたら次のウォッチドッグで復帰する)。
    lock = RunLock(LOCK_PATH, stale_after_sec=LOCK_STALE_SEC)
    try:
        lock.acquire()
    except LockBusy as e:
        _log(f"既に記録器が動いている({e})。二重に書かないので終了する。"
             "止めたい場合は deploy\\stop_all.bat を使う")
        return False
    return lock


async def _heartbeat(lock) -> None:
    """鍵の時刻を更新し続ける = 「このプロセスは生きている」の表明。"""
    while True:
        await asyncio.sleep(LOCK_BEAT_SEC)
        try:
            LOCK_PATH.write_text(
                json.dumps({"pid": os.getpid(), "ts": time.time()}), encoding="utf-8")
        except Exception as e:  # noqa: BLE001 - 鍵の更新失敗で記録は止めない
            _log(f"警告: 鍵の更新に失敗 {type(e).__name__}: {str(e)[:80]}")


async def run(venues: list[str], minutes: float | None, lock=None) -> None:
    deadline = None if minutes is None else time.monotonic() + minutes * 60
    beat = asyncio.create_task(_heartbeat(lock)) if lock else None
    try:
        # **1 つの取引所が落ちても他を巻き込まない。** return_exceptions が無いと
        # 最初の例外で gather 全体が終わり、他の取引所の記録まで止まる。
        results = await asyncio.gather(
            *(record_venue(v, deadline) for v in venues), return_exceptions=True)
        for venue, r in zip(venues, results):
            if isinstance(r, BaseException) and not isinstance(r, asyncio.CancelledError):
                _log(f"{venue}: 異常終了 {type(r).__name__}: {str(r)[:200]}")
    finally:
        if beat is not None:
            beat.cancel()


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

    lock = _acquire_lock()
    if lock is False:
        return 3

    _log(f"記録開始: {venues} -> {OUT_DIR}")
    try:
        asyncio.run(run(venues, args.minutes, lock))
    except KeyboardInterrupt:
        _log("停止(Ctrl+C)")
    finally:
        if lock:
            lock.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
