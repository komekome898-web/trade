"""取引の記録 trades.json.gz の形(L-D04、L-594)。"""
import gzip
import json

import pytest

from bot.research.trade_record import (SEAL_START_NS, SealedTradesError, read_trades_json,
                                       write_trades_json)

NS = 1_000_000_000


def _t(e, x, side=1):
    return {"entry_t_ns": e, "entry_px": 100.123456, "exit_t_ns": x, "exit_px": 101.0, "side": side,
            "qty": 1 / 7, "pnl_pct": 0.123456789}


def test_columns_and_round_trip(tmp_path):
    p = tmp_path / "trades.json.gz"
    n = write_trades_json(str(p), [_t(1 * NS, 2 * NS), _t(3 * NS, 4 * NS, -1)])
    assert n == 2
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        doc = json.load(fh)
    assert doc["version"] == 1 and doc["t_unit"] == "ns"
    assert doc["entry_t_ns"] == [NS, 3 * NS] and doc["exit_t_ns"] == [2 * NS, 4 * NS]
    assert doc["side"] == [1, -1]
    assert doc["entry_px"] == [100.1235, 100.1235] and doc["pnl_pct"] == [0.123457, 0.123457]
    assert doc["qty"] == [round(1 / 7, 6)] * 2
    assert read_trades_json(str(p))["side"] == [1, -1]


def test_refuses_sealed_trades(tmp_path):
    p = tmp_path / "trades.json.gz"
    with pytest.raises(SealedTradesError):
        write_trades_json(str(p), [_t(SEAL_START_NS - NS, SEAL_START_NS)])
    assert not p.exists()


def test_rejects_bad_side_and_nan(tmp_path):
    with pytest.raises(ValueError):
        write_trades_json(str(tmp_path / "a.json.gz"), [_t(1, 2, 0)])
    bad = _t(1, 2)
    bad["pnl_pct"] = float("nan")
    with pytest.raises(ValueError):
        write_trades_json(str(tmp_path / "b.json.gz"), [bad])
