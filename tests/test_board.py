"""Order-book reconstruction from recorded Realtime API board messages."""
from __future__ import annotations

import gzip
import json

import pytest

from bot.research.board import BookState, build_series, iter_messages

PRODUCT = "FX_BTC_JPY"
SNAP_CH = f"lightning_board_snapshot_{PRODUCT}"
DIFF_CH = f"lightning_board_{PRODUCT}"


def levels(*pairs):
    return [{"price": float(p), "size": float(s)} for p, s in pairs]


def board_msg(bids=(), asks=(), mid=None):
    msg = {"bids": levels(*bids), "asks": levels(*asks)}
    if mid is not None:
        msg["mid_price"] = float(mid)
    return msg


def snapshot():
    """Symmetric 4-deep book around a mid of 1_000_000."""
    return board_msg(
        bids=[(999_900, 1.0), (999_800, 2.0), (999_000, 4.0), (990_000, 8.0)],
        asks=[(1_000_100, 1.0), (1_000_200, 2.0), (1_001_000, 4.0), (1_010_000, 8.0)],
        mid=1_000_000,
    )


def write_stream(path, records):
    with gzip.open(path, "wt") as fh:
        fh.write(json.dumps({"jsonrpc": "2.0", "id": 1, "result": True}) + "\n")
        for rts, channel, message in records:
            fh.write(json.dumps({
                "rts": rts,
                "m": {"jsonrpc": "2.0", "method": "channelMessage",
                      "params": {"channel": channel, "message": message}},
            }) + "\n")


# --- BookState ---------------------------------------------------------------

def test_snapshot_sets_best_prices_and_mid():
    book = BookState()
    book.apply_snapshot(snapshot())
    assert book.best_bid == 999_900
    assert book.best_ask == 1_000_100
    assert book.mid == 1_000_000
    assert book.spread == 200


def test_diff_upserts_new_and_existing_levels():
    book = BookState()
    book.apply_snapshot(snapshot())
    book.apply_diff(board_msg(bids=[(999_950, 3.0), (999_800, 5.0)]))
    assert book.best_bid == 999_950  # new inside level becomes best
    assert book.bids[999_800] == 5.0  # existing level overwritten, not summed
    book.apply_diff(board_msg(asks=[(1_000_050, 0.5)]))
    assert book.best_ask == 1_000_050
    assert book.mid == pytest.approx((999_950 + 1_000_050) / 2)


def test_zero_size_removes_level():
    book = BookState()
    book.apply_snapshot(snapshot())
    book.apply_diff(board_msg(bids=[(999_900, 0.0)], asks=[(1_000_100, 0.0)]))
    assert 999_900 not in book.bids
    assert 1_000_100 not in book.asks
    assert book.best_bid == 999_800  # next level down
    assert book.best_ask == 1_000_200


def test_snapshot_resets_previous_state():
    book = BookState()
    book.apply_snapshot(snapshot())
    book.apply_diff(board_msg(bids=[(500_000, 99.0)]))
    assert 500_000 in book.bids
    book.apply_snapshot(snapshot())
    assert 500_000 not in book.bids
    assert len(book.bids) == 4


def test_empty_book_has_no_mid_and_zero_imbalance():
    book = BookState()
    assert book.best_bid is None and book.best_ask is None
    assert book.mid is None and book.spread is None
    assert book.depth_within_bps(5.0) == (0.0, 0.0)
    assert book.imbalance(5.0) == 0.0


def test_one_sided_book_has_no_mid():
    book = BookState()
    book.apply_snapshot(board_msg(bids=[(999_900, 1.0)]))
    assert book.mid is None
    assert book.imbalance(5.0) == 0.0


# --- depth / imbalance -------------------------------------------------------

def test_depth_within_bps_sums_only_levels_inside_the_band():
    book = BookState()
    book.apply_snapshot(snapshot())
    # mid 1_000_000; 5 bps = +/- 500 JPY -> [999_500, 1_000_500]
    assert book.depth_within_bps(5.0) == (3.0, 3.0)  # two levels each side
    # 20 bps = +/- 2000 -> also picks up 999_000 / 1_001_000
    assert book.depth_within_bps(20.0) == (7.0, 7.0)
    # 200 bps = +/- 20_000 -> whole book
    assert book.depth_within_bps(200.0) == (15.0, 15.0)
    # 0.5 bps = +/- 50 -> nothing rests that close
    assert book.depth_within_bps(0.5) == (0.0, 0.0)


def test_depth_band_edge_is_inclusive():
    book = BookState()
    book.apply_snapshot(board_msg(bids=[(999_500, 1.0)], asks=[(1_000_500, 2.0)]))
    # mid 1_000_000, band edge lands exactly on both levels
    assert book.depth_within_bps(5.0) == (1.0, 2.0)


def test_imbalance_is_positive_when_bid_depth_dominates():
    book = BookState()
    book.apply_snapshot(snapshot())
    assert book.imbalance(5.0) == pytest.approx(0.0)  # symmetric book
    book.apply_diff(board_msg(bids=[(999_900, 9.0)]))  # 1.0 -> 9.0 on the bid
    bid_depth, ask_depth = book.depth_within_bps(5.0)
    assert (bid_depth, ask_depth) == (11.0, 3.0)
    assert book.imbalance(5.0) == pytest.approx((11.0 - 3.0) / 14.0)
    assert book.imbalance(5.0) > 0


def test_imbalance_is_negative_when_ask_depth_dominates():
    book = BookState()
    book.apply_snapshot(snapshot())
    book.apply_diff(board_msg(asks=[(1_000_100, 9.0)]))
    assert book.imbalance(5.0) == pytest.approx((3.0 - 11.0) / 14.0)
    assert book.imbalance(5.0) < 0


def test_imbalance_is_bounded_and_zero_when_the_band_holds_nothing():
    book = BookState()
    book.apply_snapshot(board_msg(bids=[(999_000, 3.0)], asks=[(1_001_000, 1.0)]))
    # mid 1_000_000, 5 bps band = +/- 500: both best levels sit outside it
    assert book.depth_within_bps(5.0) == (0.0, 0.0)
    assert book.imbalance(5.0) == 0.0
    # widen past both and the sign follows the heavier side, magnitude <= 1
    assert 0.0 < book.imbalance(200.0) <= 1.0
    assert book.imbalance(200.0) == pytest.approx(0.5)


# --- iter_messages -----------------------------------------------------------

def test_iter_messages_skips_acks_and_yields_channel_messages(tmp_path):
    path = tmp_path / "s.jsonl.gz"
    write_stream(path, [
        (100.0, SNAP_CH, snapshot()),
        (100.5, DIFF_CH, board_msg(bids=[(999_950, 1.0)])),
        (100.7, f"lightning_ticker_{PRODUCT}", {"ltp": 1_000_000}),
    ])
    out = list(iter_messages(path))
    assert [ch for _, ch, _ in out] == [SNAP_CH, DIFF_CH, f"lightning_ticker_{PRODUCT}"]
    assert out[0][0] == 100.0
    assert out[0][2]["bids"][0]["price"] == 999_900


def test_iter_messages_tolerates_a_truncated_recording(tmp_path):
    path = tmp_path / "partial.jsonl.gz"
    write_stream(path, [(100.0, SNAP_CH, snapshot()),
                        (101.0, DIFF_CH, board_msg(bids=[(999_950, 1.0)]))])
    raw = path.read_bytes()
    path.write_bytes(raw[:-12])  # recorder still writing: no end-of-stream marker
    out = list(iter_messages(path))
    assert len(out) >= 1  # whatever decompressed cleanly, no exception


# --- build_series ------------------------------------------------------------

def test_build_series_samples_last_state_per_second(tmp_path):
    path = tmp_path / "a.jsonl.gz"
    write_stream(path, [
        (1000.0, SNAP_CH, snapshot()),                                    # mid 1_000_000
        (1000.4, DIFF_CH, board_msg(asks=[(1_000_100, 0.0)])),            # mid 1_000_050
        (1000.9, DIFF_CH, board_msg(bids=[(999_900, 0.0)])),              # mid 1_000_000
        (1001.2, DIFF_CH, board_msg(bids=[(1_000_000, 1.0)])),            # mid 1_000_100
        (1002.8, DIFF_CH, board_msg(asks=[(1_000_150, 1.0)])),            # mid 1_000_075
    ])
    df = build_series([path], interval_sec=1.0, depth_bps=5.0)
    assert list(df.columns) == ["mid", "spread", "bid_depth", "ask_depth", "imbalance"]
    assert len(df) == 3
    assert list(df["mid"]) == [1_000_000.0, 1_000_100.0, 1_000_075.0]
    assert list(df["spread"]) == [400.0, 200.0, 150.0]
    assert str(df.index[0]) == "1970-01-01 00:16:40+00:00"
    assert (df.index[1] - df.index[0]).total_seconds() == 1.0


def test_build_series_forward_fills_seconds_with_no_messages(tmp_path):
    path = tmp_path / "gap.jsonl.gz"
    write_stream(path, [
        (2000.0, SNAP_CH, snapshot()),
        (2004.0, DIFF_CH, board_msg(bids=[(1_000_000, 1.0)])),  # mid 1_000_050
    ])
    df = build_series([path], interval_sec=1.0)
    assert len(df) == 5  # 2000..2004 inclusive, gap seconds carried forward
    assert list(df["mid"][:4]) == [1_000_000.0] * 4
    assert df["mid"].iloc[-1] == 1_000_050.0


def test_build_series_does_not_fill_across_a_recording_gap(tmp_path):
    """Two sessions minutes apart must not become one fabricated series."""
    path = tmp_path / "sessions.jsonl.gz"
    write_stream(path, [
        (2000.0, SNAP_CH, snapshot()),
        (2001.0, DIFF_CH, board_msg(bids=[(999_950, 1.0)])),
        (8000.0, SNAP_CH, snapshot()),  # recorder restarted 100 minutes later
        (8001.0, DIFF_CH, board_msg(bids=[(999_950, 1.0)])),
    ])
    df = build_series([path], interval_sec=1.0, max_gap_sec=60.0)
    assert len(df) == 4  # not 6001
    gap = (df.index[2] - df.index[1]).total_seconds()
    assert gap == 5999.0  # the hole stays a hole


def test_build_series_max_gap_sec_controls_the_fill(tmp_path):
    path = tmp_path / "gapcfg.jsonl.gz"
    write_stream(path, [(9000.0, SNAP_CH, snapshot()),
                        (9010.0, SNAP_CH, snapshot())])
    assert len(build_series([path], max_gap_sec=60.0)) == 11  # filled through
    assert len(build_series([path], max_gap_sec=5.0)) == 2     # split apart


def test_build_series_skips_diffs_before_the_first_snapshot(tmp_path):
    path = tmp_path / "b.jsonl.gz"
    write_stream(path, [
        (3000.0, DIFF_CH, board_msg(bids=[(1.0, 1.0)])),  # pre-snapshot, unusable
        (3005.0, SNAP_CH, snapshot()),
    ])
    df = build_series([path], interval_sec=1.0)
    assert len(df) == 1
    assert df["mid"].iloc[0] == 1_000_000.0
    assert str(df.index[0]) == "1970-01-01 00:50:05+00:00"


def test_build_series_resets_on_a_mid_stream_snapshot(tmp_path):
    path = tmp_path / "c.jsonl.gz"
    write_stream(path, [
        (4000.0, SNAP_CH, snapshot()),
        (4001.0, DIFF_CH, board_msg(bids=[(999_999, 50.0)])),  # huge fake level
        (4002.0, SNAP_CH, snapshot()),                          # resets it away
    ])
    df = build_series([path], interval_sec=1.0)
    assert df["mid"].iloc[1] == pytest.approx((999_999 + 1_000_100) / 2)
    assert df["imbalance"].iloc[1] > 0.8
    assert df["mid"].iloc[2] == 1_000_000.0
    assert df["imbalance"].iloc[2] == pytest.approx(0.0)


def test_build_series_imbalance_and_depth_columns_track_the_book(tmp_path):
    path = tmp_path / "d.jsonl.gz"
    write_stream(path, [
        (5000.0, SNAP_CH, snapshot()),
        (5001.0, DIFF_CH, board_msg(bids=[(999_900, 9.0)])),
    ])
    df = build_series([path], interval_sec=1.0, depth_bps=5.0)
    assert list(df["bid_depth"]) == [3.0, 11.0]
    assert list(df["ask_depth"]) == [3.0, 3.0]
    assert df["imbalance"].iloc[0] == pytest.approx(0.0)
    assert df["imbalance"].iloc[1] == pytest.approx(8.0 / 14.0)


def test_build_series_spans_multiple_files_in_order(tmp_path):
    first = tmp_path / "part_1.jsonl.gz"
    second = tmp_path / "part_2.jsonl.gz"
    write_stream(first, [(6000.0, SNAP_CH, snapshot())])
    write_stream(second, [(6001.0, SNAP_CH, board_msg(
        bids=[(999_800, 1.0)], asks=[(1_000_200, 1.0)]))])
    df = build_series([second, first], interval_sec=1.0)  # unsorted input
    assert list(df["mid"]) == [1_000_000.0, 1_000_000.0]
    assert list(df["spread"]) == [200.0, 400.0]


def test_build_series_on_empty_input_returns_empty_frame(tmp_path):
    path = tmp_path / "e.jsonl.gz"
    write_stream(path, [(7000.0, f"lightning_ticker_{PRODUCT}", {"ltp": 1.0})])
    df = build_series([path])
    assert df.empty
    assert list(df.columns) == ["mid", "spread", "bid_depth", "ask_depth", "imbalance"]


def test_build_series_honours_interval_sec(tmp_path):
    path = tmp_path / "f.jsonl.gz"
    write_stream(path, [
        (8000.0, SNAP_CH, snapshot()),
        (8003.0, DIFF_CH, board_msg(bids=[(1_000_000, 1.0)])),
        (8009.0, DIFF_CH, board_msg(asks=[(1_000_050, 1.0)])),
    ])
    df = build_series([path], interval_sec=5.0)
    assert len(df) == 2
    assert (df.index[1] - df.index[0]).total_seconds() == 5.0
    assert df["mid"].iloc[0] == 1_000_050.0  # last state in the 8000-8005 bucket
