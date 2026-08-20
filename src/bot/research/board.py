"""Order-book reconstruction from recorded bitFlyer Realtime API streams.

Turns ``data/ws/*.jsonl.gz`` recordings (one JSON object per line,
``{"rts": <local unix ts>, "m": <json-rpc message>}``) into a sampled
order-book time series usable for book-imbalance research.

The board feed has two channels:

* ``lightning_board_snapshot_<product>`` — a full book; every snapshot
  RESETS the local state (bitFlyer re-sends snapshots periodically).
* ``lightning_board_<product>`` — diffs against the current book; a level
  with ``size == 0`` is a removal, anything else is an upsert.

Nothing here touches the network or the exchange; it is pure replay of
files already on disk.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Iterable, Iterator

import pandas as pd

SNAPSHOT_PREFIX = "lightning_board_snapshot"
BOARD_PREFIX = "lightning_board"

SERIES_COLUMNS = ["mid", "spread", "bid_depth", "ask_depth", "imbalance"]


def is_snapshot_channel(channel: str) -> bool:
    return channel.startswith(SNAPSHOT_PREFIX)


def is_diff_channel(channel: str) -> bool:
    return channel.startswith(BOARD_PREFIX) and not is_snapshot_channel(channel)


class BookState:
    """Mutable order book: ``{price: size}`` per side.

    Sizes are absolute (not deltas). A diff level of size 0 removes the
    price level entirely.
    """

    def __init__(self) -> None:
        self.bids: dict[float, float] = {}
        self.asks: dict[float, float] = {}
        self.mid_price: float | None = None  # exchange-reported, informational
        self.ready = False  # True once a snapshot has been applied

    # -- mutation ---------------------------------------------------------
    def apply_snapshot(self, msg: dict) -> None:
        self.bids = {}
        self.asks = {}
        self._upsert_levels(msg)
        self.ready = True

    def apply_diff(self, msg: dict) -> None:
        self._upsert_levels(msg)

    def _upsert_levels(self, msg: dict) -> None:
        for side, book in (("bids", self.bids), ("asks", self.asks)):
            for level in msg.get(side) or ():
                price = float(level["price"])
                size = float(level["size"])
                if size == 0.0:
                    book.pop(price, None)
                else:
                    book[price] = size
        mid = msg.get("mid_price")
        if mid is not None:
            self.mid_price = float(mid)

    # -- reads ------------------------------------------------------------
    @property
    def best_bid(self) -> float | None:
        return max(self.bids) if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return min(self.asks) if self.asks else None

    @property
    def mid(self) -> float | None:
        bid, ask = self.best_bid, self.best_ask
        if bid is None or ask is None:
            return None
        return (bid + ask) / 2.0

    @property
    def spread(self) -> float | None:
        bid, ask = self.best_bid, self.best_ask
        if bid is None or ask is None:
            return None
        return ask - bid

    def depth_within_bps(self, bps: float) -> tuple[float, float]:
        """Summed size on each side within ``bps`` of the mid.

        Returns ``(bid_depth, ask_depth)``; ``(0.0, 0.0)`` when the book has
        no two-sided mid.
        """
        mid = self.mid
        if mid is None or mid <= 0:
            return 0.0, 0.0
        band = mid * bps / 1e4
        lo, hi = mid - band, mid + band
        bid_depth = sum(size for price, size in self.bids.items() if price >= lo)
        ask_depth = sum(size for price, size in self.asks.items() if price <= hi)
        return float(bid_depth), float(ask_depth)

    def imbalance(self, bps: float) -> float:
        """(bid_depth - ask_depth) / total within ``bps``; 0.0 if empty.

        Positive means more size resting on the bid side.
        """
        bid_depth, ask_depth = self.depth_within_bps(bps)
        total = bid_depth + ask_depth
        if total <= 0:
            return 0.0
        return (bid_depth - ask_depth) / total


def iter_messages(path: str | Path) -> Iterator[tuple[float, str, dict]]:
    """Yield ``(rts, channel, message)`` for channel messages in one file.

    Subscription acks and any other non-``channelMessage`` frames are
    skipped. Files still being written by the recorder are truncated mid
    gzip-member; those are read up to the last complete line instead of
    raising.
    """
    try:
        with gzip.open(path, "rt") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue  # partially flushed final line
                msg = rec.get("m")
                if not isinstance(msg, dict) or msg.get("method") != "channelMessage":
                    continue
                params = msg.get("params") or {}
                channel = params.get("channel")
                message = params.get("message")
                if channel is None or message is None:
                    continue
                yield float(rec["rts"]), channel, message
    except (EOFError, gzip.BadGzipFile, OSError):
        # Recording in progress / truncated tail: keep what we already read.
        return


def build_series(paths: Iterable[str | Path], interval_sec: float = 1.0,
                 depth_bps: float = 5.0, max_gap_sec: float = 60.0) -> pd.DataFrame:
    """Replay board messages into a sampled book time series.

    One row per ``interval_sec`` bucket, holding the state as of the LAST
    message in that bucket. Buckets before the first snapshot are skipped;
    a quiet bucket inside a recording carries the previous state forward
    (the book genuinely did not change), but a gap longer than
    ``max_gap_sec`` — the recorder was off between sessions — breaks the
    grid instead of inventing rows, so the index jumps. Index is UTC
    timestamps at bucket starts.
    """
    state = BookState()
    rows: dict[int, list[float]] = {}

    for path in sorted(paths, key=str):
        for rts, channel, message in iter_messages(path):
            if is_snapshot_channel(channel):
                state.apply_snapshot(message)
            elif is_diff_channel(channel):
                if not state.ready:
                    continue  # diffs before the first snapshot are unusable
                state.apply_diff(message)
            else:
                continue
            if not state.ready:
                continue
            bucket = int(rts // interval_sec)
            bid_depth, ask_depth = state.depth_within_bps(depth_bps)
            total = bid_depth + ask_depth
            imbalance = (bid_depth - ask_depth) / total if total > 0 else 0.0
            mid = state.mid
            spread = state.spread
            rows[bucket] = [
                float("nan") if mid is None else mid,
                float("nan") if spread is None else spread,
                bid_depth,
                ask_depth,
                imbalance,
            ]

    if not rows:
        idx = pd.DatetimeIndex([], tz="UTC", name="ts")
        return pd.DataFrame(columns=SERIES_COLUMNS, index=idx, dtype=float)

    buckets = sorted(rows)
    max_gap_buckets = max(1, int(max_gap_sec // interval_sec))

    # Split into contiguous segments; only inside a segment is forward fill
    # a statement about the book rather than a guess about missing data.
    segments: list[list[int]] = [[buckets[0]]]
    for prev, cur in zip(buckets, buckets[1:]):
        if cur - prev > max_gap_buckets:
            segments.append([cur])
        else:
            segments[-1].append(cur)

    frames = []
    for seg in segments:
        grid = range(seg[0], seg[-1] + 1)
        data = [rows[b] for b in seg]
        index = pd.to_datetime([b * interval_sec for b in seg], unit="s", utc=True)
        part = pd.DataFrame(data, columns=SERIES_COLUMNS, index=index)
        full = pd.to_datetime([b * interval_sec for b in grid], unit="s", utc=True)
        frames.append(part.reindex(full).ffill())

    frame = pd.concat(frames)
    frame.index.name = "ts"
    return frame
