"""検査のツールの受け入れの場面 7(委任文 DELEGATION_one_road_step1.md)。"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from bot.bt.road.check import SUMMARY_FILE, check_bars, check_outputs, write_store

M = 60_000_000_000
T0 = 1_700_000_040_000_000_000  # 分の区切り
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(REPO, "scripts", "road", "check_outputs.py")


def _fills():
    # オーナーの例(L-747)
    return [{"t_ns": T0 + k * M + 30_000_000_000, "side": "buy", "qty": 0.01, "px": 10200 - 100 * k, "ccy": "JPY"}
            for k in range(5)] + [{"t_ns": T0 + 10 * M + 5_000_000_000, "side": "sell", "qty": 0.05, "px": 10100,
                                   "ccy": "JPY"}]


def _bars(fills, shift_ns=0):
    out = []
    for f in fills:
        s = (f["t_ns"] // M) * M + shift_ns
        out.append({"t_ns": s, "open": f["px"], "high": f["px"] + 50, "low": f["px"] - 50, "close": f["px"]})
    return out


def _run_cli(run_dir, bars, tmp_path):
    bp = tmp_path / "bars.json"
    bp.write_text(json.dumps(bars), encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "src"))
    return subprocess.run([sys.executable, SCRIPT, str(run_dir), "--bars", str(bp)], capture_output=True, text=True,
                          env=env)


def test_clean_store_passes(tmp_path):
    d = tmp_path / "run"
    write_store(str(d), _fills())
    res = check_outputs(str(d), _bars(_fills()))
    assert res.ok, res.failures
    p = _run_cli(d, _bars(_fills()), tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "検査 通過" in p.stdout


def test_scene7_summary_off_by_one_yen_fails(tmp_path):
    d = tmp_path / "run"
    write_store(str(d), _fills())
    path = d / SUMMARY_FILE
    s = json.loads(path.read_text(encoding="utf-8"))
    s["pnl_jpy"] = s["pnl_jpy"] + 1
    path.write_text(json.dumps(s), encoding="utf-8")
    res = check_outputs(str(d), _bars(_fills()))
    assert not res.ok
    assert [(f["check"], f["row"]) for f in res.failures] == [("a", "pnl_jpy")]
    p = _run_cli(d, _bars(_fills()), tmp_path)
    assert p.returncode == 1
    assert "pnl_jpy" in p.stdout and "検査 失敗" in p.stdout


def test_summary_missing_or_extra_key_fails(tmp_path):
    d = tmp_path / "run"
    write_store(str(d), _fills())
    path = d / SUMMARY_FILE
    s = json.loads(path.read_text(encoding="utf-8"))
    del s["open_trades"]
    s["win_rate"] = 1.0
    path.write_text(json.dumps(s), encoding="utf-8")
    rows = sorted(f["row"] for f in check_outputs(str(d), _bars(_fills())).failures)
    assert rows == ["open_trades", "win_rate"]


def test_missing_summary_file_fails(tmp_path):
    d = tmp_path / "run"
    write_store(str(d), _fills())
    os.remove(d / SUMMARY_FILE)
    res = check_outputs(str(d), _bars(_fills()))
    assert not res.ok


def test_scene7_price_one_yen_above_high_fails(tmp_path):
    fills = _fills()
    bars = _bars(fills)
    fills[2]["px"] = bars[2]["high"] + 1  # 約定の値段がその分の高値を 1 円超える
    d = tmp_path / "run"
    write_store(str(d), fills)  # まとめは約定の列から正しく書く: 落ちるのは (b) だけ
    res = check_outputs(str(d), bars)
    assert [(f["check"], f["row"]) for f in res.failures] == [("b", 2)]
    p = _run_cli(d, bars, tmp_path)
    assert p.returncode == 1 and "高値" in p.stdout


def test_price_below_low_fails():
    fills = _fills()
    bars = _bars(fills)
    fills[0]["px"] = bars[0]["low"] - 1
    assert [f["row"] for f in check_bars(fills, bars)] == [0]


def test_scene7_bar_shifted_20s_fails(tmp_path):
    fills = _fills()  # 各約定は分の 30 秒目・5 秒目
    bars = _bars(fills)
    # 約定 0(分の 30 秒目)に当たる足だけ、始まりを 20 秒ずらす(始まり = 分 + 20 秒 → 約定はその足に属する)
    bars[0]["t_ns"] += 20_000_000_000
    d = tmp_path / "run"
    write_store(str(d), fills)
    res = check_outputs(str(d), bars)
    assert [(f["check"], f["row"]) for f in res.failures] == [("b", 0)]
    assert "ずれ" in res.failures[0]["reason"]
    p = _run_cli(d, bars, tmp_path)
    assert p.returncode == 1


def test_no_bar_for_the_minute_fails():
    fills = _fills()
    bars = _bars(fills)[1:]
    assert [f["row"] for f in check_bars(fills, bars)] == [0]


def test_overlapping_bars_fail():
    fills = _fills()
    bars = _bars(fills) + [{"t_ns": (fills[3]["t_ns"] // M) * M - 20_000_000_000, "high": 1e9, "low": 0}]
    assert [f["row"] for f in check_bars(fills, bars)] == [3]


def test_cli_needs_bars(tmp_path):
    d = tmp_path / "run"
    write_store(str(d), _fills())
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "src"))
    p = subprocess.run([sys.executable, SCRIPT, str(d)], capture_output=True, text=True, env=env)
    assert p.returncode != 0
