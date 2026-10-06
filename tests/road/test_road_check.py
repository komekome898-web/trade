"""検査のツールの受け入れの場面 7(委任文 DELEGATION_one_road_step1.md)と、直し 1 の場面
(まとめの約定の数・取引ごとの表の突き合わせ、日本語の文。DELEGATION_one_road_step1_fix1.md 3.・4.・5.)。"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from decimal import Decimal

import pytest

from bot.bt.road.check import FILLS_FILE, SUMMARY_FILE, check_bars, check_outputs, write_store

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
    assert s["pnl_jpy"] == "5"
    s["pnl_jpy"] = str(Decimal(s["pnl_jpy"]) + 1)  # "6"
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
    assert "まとめのファイルが無い" in res.failures[0]["reason"]


def test_broken_json_store_fails_in_japanese(tmp_path):
    d = tmp_path / "run"
    write_store(str(d), _fills())
    (d / FILLS_FILE).write_text("{", encoding="utf-8")
    res = check_outputs(str(d), _bars(_fills()))
    assert len(res.failures) == 1 and "JSON として読めない" in res.failures[0]["reason"]
    assert "Expecting" not in res.failures[0]["reason"]


def test_number_written_where_string_belongs_fails(tmp_path):
    # 損益は帳簿のツールが出す 10 進の文字列。同じ値でも数 5.0 で書かれていたら違うとみなす
    d = tmp_path / "run"
    write_store(str(d), _fills())
    path = d / SUMMARY_FILE
    s = json.loads(path.read_text(encoding="utf-8"))
    s["pnl_jpy"] = 5.0
    path.write_text(json.dumps(s), encoding="utf-8")
    assert [f["row"] for f in check_outputs(str(d), _bars(_fills())).failures] == ["pnl_jpy"]


@pytest.mark.parametrize("key,value", [("hold_ns", 1), ("levels", 4), ("max_position", "0.04"),
                                       ("status", "open"), ("first_t_ns", T0), ("pnl_jpy", "4")])
def test_trade_row_tampered_fails(tmp_path, key, value):
    d = tmp_path / "run"
    write_store(str(d), _fills())
    path = d / SUMMARY_FILE
    s = json.loads(path.read_text(encoding="utf-8"))
    s["trades"][0][key] = value
    path.write_text(json.dumps(s), encoding="utf-8")
    assert [f["row"] for f in check_outputs(str(d), _bars(_fills())).failures] == [f"trades[0].{key}"]


# 批評家の場面: 閉じた取引の後に、2 段足して一部決済した途中の取引
def _s8():
    def f(m, side, q, px):
        return {"t_ns": T0 + m * M + 5, "side": side, "qty": q, "px": px, "ccy": "JPY"}
    return [f(0, "buy", 0.01, 10000), f(1, "sell", 0.01, 10100), f(2, "buy", 0.01, 10000), f(3, "buy", 0.01, 10200),
            f(4, "sell", 0.01, 10300)]


def _s8_bars():
    return [{"t_ns": T0 + k * M, "high": 10400, "low": 9900} for k in range(5)]


def _store_without_fill(tmp_path, i):
    d = tmp_path / f"del{i}"
    write_store(str(d), _s8())
    path = d / FILLS_FILE
    body = json.loads(path.read_text(encoding="utf-8"))
    body["fills"].pop(i)
    path.write_text(json.dumps(body), encoding="utf-8")
    return d


def test_critic_s8_clean_store_passes(tmp_path):
    d = tmp_path / "run"
    write_store(str(d), _s8())
    assert check_outputs(str(d), _s8_bars()).ok


def test_critic_deleting_partial_close_of_open_trade_fails(tmp_path):
    # 途中の取引の一部決済の約定(約定 4)を消した置き場: 前は通った(批評家の指摘 3)
    d = _store_without_fill(tmp_path, 4)
    res = check_outputs(str(d), _s8_bars())
    rows = [f["row"] for f in res.failures]
    assert rows == ["fill_count", "trades[1].last_t_ns", "trades[1].pnl_jpy"], res.failures
    p = _run_cli(d, _s8_bars(), tmp_path)
    assert p.returncode == 1 and "trades[1].pnl_jpy" in p.stdout


@pytest.mark.parametrize("i", range(5))
def test_critic_deleting_any_fill_fails(tmp_path, i):
    d = _store_without_fill(tmp_path, i)
    res = check_outputs(str(d), _s8_bars())
    assert not res.ok
    assert "fill_count" in [f["row"] for f in res.failures]


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
    assert p.returncode == 2
    assert "--bars(1 分足の JSON)が無い" in p.stderr and "使い方" in p.stderr
    assert "usage" not in (p.stdout + p.stderr) and "error" not in (p.stdout + p.stderr)


def test_cli_messages_are_japanese(tmp_path):
    d = tmp_path / "run"
    write_store(str(d), _fills())
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "src"))
    p = subprocess.run([sys.executable, SCRIPT, str(d), "--bars", str(tmp_path / "nothing.json")], capture_output=True,
                       text=True, env=env)
    assert p.returncode == 2 and "1 分足のファイルが無い" in p.stderr
    p = subprocess.run([sys.executable, SCRIPT, "--help"], capture_output=True, text=True, env=env)
    assert p.returncode == 0 and "使い方" in p.stdout
    p = subprocess.run([sys.executable, SCRIPT, str(d), "--bars", "x", "--verbose"], capture_output=True, text=True,
                       env=env)
    assert p.returncode == 2 and "知らない引数" in p.stderr
    for out in (p.stdout, p.stderr):
        # 英語の文(英字の語が 3 つ以上続く)が無い
        assert not re.search(r"[A-Za-z]+ [A-Za-z]+ [A-Za-z]+", out.replace("PYTHONPATH=src python3", ""))


# 批評家 2 回目の指摘 1: 壊れた置き場で英語の文を出して落ちない(O-1)
@pytest.mark.parametrize("bad_fills", [[7], [[1, 2]]])
def test_fill_rows_not_mappings_fail_in_japanese(tmp_path, bad_fills):
    d = tmp_path / "run"
    write_store(str(d), _fills())
    (d / FILLS_FILE).write_text(json.dumps({"fills": bad_fills, "fx": []}), encoding="utf-8")
    p = _run_cli(d, _bars(_fills()), tmp_path)
    assert p.returncode != 0
    assert "Traceback" not in p.stderr and "Error:" not in p.stderr
    assert "検査 失敗" in (p.stdout + p.stderr)


@pytest.mark.parametrize("where", ["fill_px", "bar_high"])
def test_huge_integers_fail_in_japanese(tmp_path, where):
    d = tmp_path / "run"
    fills = _fills()
    write_store(str(d), fills)
    bars = _bars(fills)
    huge = int("1" + "0" * 400)
    if where == "fill_px":
        store = json.loads((d / FILLS_FILE).read_text(encoding="utf-8"))
        store["fills"][0]["px"] = huge
        (d / FILLS_FILE).write_text(json.dumps(store), encoding="utf-8")
    else:
        bars[0]["high"] = huge
    p = _run_cli(d, bars, tmp_path)
    assert p.returncode != 0
    assert "Traceback" not in p.stderr
    assert "検査 失敗" in (p.stdout + p.stderr)
