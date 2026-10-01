"""D-4 (K1 stage A, 2026-09-27): the currency of a run's amounts comes from its record.

The runner's record carries `currency` (the setup's Parts.currency: the product's quote currency; None = not
stated), its metrics carry pnl.currency, and the dashboard's labels take the currency from the record: an
XBTUSD run shows USD and never 円; a record that states no currency shows 通貨の記録なし; a JPY record shows 円;
an integrated run's record names its account's currency."""
from __future__ import annotations

import json
import os

from bot.bt.repro.runner import DataInput, run
from bot.monitoring.backtest_view import NO_CURRENCY, run_currency, run_view
from bot.strategy.k1_wick import FILL_NAME, K1Setup

T0 = 1_483_228_800
SPEC = {"format": "csv", "header": True, "delimiter": ",", "compression": "none", "kind": "bar", "symbol": "XBTUSD",
        "asset": "crypto", "time": {"columns": ["start_ts"], "unit": "iso", "tz": "UTC"},
        "fields": {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "vol"},
        "bar": {"interval_s": 3600, "label": "start", "session": "24x7"}, "key": "start"}  # session: G-4 (2026-10-01)
ROWS = [(4000, 4001, 3999, 4000.5), (4000, 4002, 3990, 4001), (4001, 4003, 4000, 4002),
        (4002, 4003, 3985, 3989), (3989, 3999, 3988, 3990), (3990, 3991, 3989, 3990.5)]


def k1_run(tmp_path):
    from datetime import datetime, timezone
    d = tmp_path / "backtest_data" / "k1"
    d.mkdir(parents=True)
    lines = ["start_ts,o,h,l,c,vol"] + [
        f"{datetime.fromtimestamp(T0 + i * 3600, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')},{o},{h},{l},{c},1.0"
        for i, (o, h, l, c) in enumerate(ROWS)]
    (d / "bars.csv").write_text("\n".join(lines) + "\n")
    cfg = {"instrument": "XBTUSD", "foot_min": 60, "gate": {"s": "-", "b": "-"}, "strength": "both", "fill": FILL_NAME,
           "costs": {"maker_fee_rate": 0, "taker_fee_rate": 0, "source": "test: 0"}}
    runs = tmp_path / "runs"
    res = run(runs_dir=str(runs), root=str(tmp_path), data=[DataInput("backtest_data/k1/bars.csv", SPEC)], config=cfg,
              seed=0, setup=K1Setup(), purpose="動作確認")
    return str(runs), res


def texts(view):
    return "\n".join(t["text"] + t["html"] for t in view["tabs"])


def test_xbtusd_run_shows_no_yen(tmp_path):
    runs, res = k1_run(tmp_path)
    assert res.record["currency"] == "USD"
    with open(os.path.join(res.run_dir, "metrics.json"), encoding="utf-8") as fh:
        m = json.load(fh)["data"]
    assert m["pnl"]["currency"] == "USD" and "pnl_jpy" not in m
    assert m["pnl"]["realized"] == (3989.0 - 4000.5) + (3990.0 - 3990.5)  # the two round trips of the scene
    view = run_view(runs, res.run_id)
    body = texts(view)
    assert "円" not in body
    assert "実現損益(USD)" in body and "損益(USD)" in body and "maker 手数料(USD)" in body


def _fake_run(tmp_path, record, metrics):
    rid = "ab" * 32
    d = tmp_path / "runs" / rid
    d.mkdir(parents=True)
    (d / "record.json").write_text(json.dumps(record))
    (d / "repro.json").write_text(json.dumps({"runs": 2, "identical": True, "sha256": {}}))
    (d / "metrics.json").write_text(json.dumps({"purpose": "研究", "run_id": rid, "kind": "metrics", "data": metrics}))
    return str(tmp_path / "runs"), rid


def test_record_without_currency_shows_that_it_has_none(tmp_path):
    runs, rid = _fake_run(tmp_path, {"run_id": "ab" * 32, "purpose": "研究", "config": {}},
                          {"pnl_jpy": {"realized": 5.0, "fees": 0.0}})  # a record written before D-4
    body = texts(run_view(runs, rid))
    assert "円" not in body and f"実現損益({NO_CURRENCY})" in body
    assert run_currency({"currency": None}) is None


def test_jpy_and_integrated_records(tmp_path):
    assert run_currency({"currency": "JPY"}) == "JPY"
    assert run_currency({"config": {"account": {"currency": "USD"}}}) == "USD"
    runs, rid = _fake_run(tmp_path, {"run_id": "ab" * 32, "purpose": "研究", "currency": "JPY", "config": {}},
                          {"pnl": {"currency": "JPY", "realized": 5.0, "fees": 0.0}})
    assert "実現損益(円)" in texts(run_view(runs, rid))
