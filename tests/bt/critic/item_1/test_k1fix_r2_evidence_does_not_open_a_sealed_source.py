"""Critic of the k1 env fixes (rounds 1 and 2 together, 2026-10-01; docs/PHASE2/K1/NEWENV_A/CRITIC_FIXES.md): the integrated run's origin evidence must not open a file the seal
record names by path, even when the declaration names it as the dataset's "source" ((d)1 x (d)2). The run's own data
is an unsealed file holding the two rows before the cutoff (other bytes than the sealed file). Synthetic only."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "item_1"))
import test_i1_fix_seal_read_before_refuse as T  # noqa: E402  (its audit hook, env fixture and helpers)
from test_i1_fix_seal_read_before_refuse import env  # noqa: F401,E402


def test_a_declared_sealed_source_is_not_opened_by_the_evidence(env, monkeypatch):  # noqa: F811
    from bot.bt import pipeline as P
    monkeypatch.setattr(P, "MARKET_BASE", str(env))
    part = "backtest_data/y/part.csv"
    (env / part).write_bytes("".join(T.BODY.splitlines(True)[:3]).encode())  # header + the 2 rows before the cutoff
    plan = P.plan_pipeline(
        root=str(env), datasets=[{**T._ds(part), "origin": "real", "source": [T.SEALED]}],
        instruments=[{"name": "i", "price": "d", "with": [], "rules": T.RULES,
                      "product": {"symbol": "X", "venue": "test", "tick": 1e-9, "min_qty": 1e-8, "qty_step": 1e-8,
                                  "quote_ccy": "JPY", "margin": True}}],
        strategy={"kind": "schedule", "orders": [{"t_ns": T.T2020 - 30 * T.NS, "side": "buy", "qty": 1.0,
                                                  "instrument": "i"}]},
        fill={"optimistic": {"tier": 3}, "pessimistic": {"tier": 1}},
        latency={ch: {"kind": "constant", "ns": 0} for ch in ("feed", "order", "cancel", "notice")},
        costs={"maker_rate": 0.0, "taker_rate": 0.0, "spread": 0.0, "source": "動作確認: 費用 0 を宣言"},
        account={"currency": "JPY", "cash": 1e12, "leverage": 1.0, "mark": "last_trade", "liquidation": None,
                 "margin_check": "open_orders"},
        purpose="動作確認")
    ev = plan.datasets[0]["origin_evidence"]
    assert T._OPENED == [], T._OPENED  # the sealed file is never opened (not its first line, not its bytes)
    assert ev["sealed_skipped"] == [T.SEALED] and T.SEALED in ev["searched"], ev
    assert ev["by"] == "rows" and ev["market_path"] == part, ev
