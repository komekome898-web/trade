"""データ層の封印(`bot.bt.data.allowlist.SealRegistry`)の探索の窓の上書きの試験。

封印の決まり: 合成のデータと合成の封印の台帳だけを使う(一時ディレクトリ)。時刻は試験の時刻で、実データのファイルは開かない。
上書きが効く条件 = 引数 explore_window="P2-08" + 環境変数 W4_WINDOW1=P2-08-explore + 承認のファイル(試験は一時ディレクトリに偽物を置く)。
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from datetime import datetime, timezone

import pytest

from bot.bt.data.allowlist import (EXPLORE_APPROVAL, EXPLORE_ENV, EXPLORE_ENV_VALUE, EXPLORE_LOG, SealRegistry)
from bot.bt.data.errors import SealedRangeError
from bot.bt.data.loader import load
from bot.bt.data.reference import load_reference

NS = 1_000_000_000
MIN = 60 * NS


def T(s: str) -> int:
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()) * NS


SEAL = T("2023-12-18T00:00:00Z")
END = T("2025-12-12T00:00:00Z")
WIN_FILE = "backtest_data/synth_win/bars_win.csv.gz"      # 台帳の unit P2-08
OTHER_FILE = "backtest_data/synth_other/bars_other.csv.gz"  # 台帳の unit P2-08b
REF_FILE = "backtest_data/synth_ref/ref.csv.gz"            # 台帳の unit P2-08(参照の行用)


def _bars(path, start, n, price0):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        fh.write("ts,open,high,low,close,volume\n")
        for i in range(n):
            t = datetime.fromtimestamp(start / 1e9 + i * 60, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            p = price0 + i
            fh.write(f"{t},{p},{p + 1},{p - 1},{p},1.0\n")


def _ref(path, start, n):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        fh.write("open_time,close\n")
        for i in range(n):
            t = datetime.fromtimestamp(start / 1e9 + i * 60, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            fh.write(f"{t},{100 + i}\n")


def _ledger(root, unit, relpath, col="ts"):
    raw = (root / relpath).read_bytes()
    d = root / "backtest_data" / "phase2_sealed" / unit
    d.mkdir(parents=True, exist_ok=True)
    rec = {"unit": unit, "forward_start": "2026-09-06T00:00:00+00:00",
           "files": [{"path": relpath, "time_column": col, "seal_from_ts": "2023-12-18T00:00:00+00:00",
                      "md5": hashlib.md5(raw).hexdigest()}]}
    (d / "SEALED.json").write_text(json.dumps(rec), encoding="utf-8")


@pytest.fixture()
def root(tmp_path, monkeypatch):
    """合成の台帳 2 つ(unit P2-08 と P2-08b)と合成のファイル。環境変数と承認のファイルは無い状態。"""
    r = tmp_path / "root"
    # 窓の終わりをまたぐ 90 本(2025-12-11T23:00Z から)。窓の終わり以降の 30 本は判定の期間の側
    _bars(r / WIN_FILE, END - 60 * MIN, 90, 1000.0)
    _bars(r / OTHER_FILE, END - 60 * MIN, 90, 5000.0)
    _ref(r / REF_FILE, END - 60 * MIN, 90)
    _ledger(r, "P2-08", WIN_FILE)
    _ledger(r, "P2-08b", OTHER_FILE)
    # 参照の行の台帳は P2-08 の別の台帳が要るが 1 unit 1 台帳なので、参照の試験は WIN_FILE の台帳に REF_FILE も載せる
    d = r / "backtest_data" / "phase2_sealed" / "P2-08" / "SEALED.json"
    rec = json.loads(d.read_text(encoding="utf-8"))
    rec["files"].append({"path": REF_FILE, "time_column": "open_time", "seal_from_ts": "2023-12-18T00:00:00+00:00",
                         "md5": hashlib.md5((r / REF_FILE).read_bytes()).hexdigest()})
    d.write_text(json.dumps(rec), encoding="utf-8")
    monkeypatch.delenv(EXPLORE_ENV, raising=False)
    return r


def approve(root):
    (root / os.path.join(*EXPLORE_APPROVAL)).write_text("test approval (合成)\n", encoding="utf-8")


def log_lines(root):
    p = root / os.path.join(*EXPLORE_LOG)
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


def ds(path, lo, hi):
    return {"name": "bars", "paths": [path], "range_ns": [lo, hi],
            "spec": {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip", "kind": "bar",
                     "symbol": "SYNTH", "asset": "crypto", "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
                     "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
                     "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start"}}


def ref_ds(lo, hi):
    return {"name": "ref", "paths": [REF_FILE], "range_ns": [lo, hi],
            "spec": {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip",
                     "time": {"columns": ["open_time"], "unit": "iso", "tz": "UTC"}, "value": "close"}}


def test_default_unchanged_without_override(root, monkeypatch):
    """引数なしの既定: 封印の境ちょうどまでは通り、越えると拒む。環境変数と承認のファイルがあっても引数なしは上書きしない。"""
    monkeypatch.setenv(EXPLORE_ENV, EXPLORE_ENV_VALUE)
    approve(root)
    # 封印の境の前の読みは今までどおり通る(ファイルは窓の終わりの前後の時刻だけなので、行は 0 本)
    assert load(str(root), [ds(WIN_FILE, SEAL - 30 * MIN, SEAL)]).records("bars") == []
    with pytest.raises(SealedRangeError):
        load(str(root), [ds(WIN_FILE, SEAL, SEAL + MIN)])
    reg = SealRegistry(str(root))
    assert {e.unit: e.cutoff_ns for e in reg.entries} == {"P2-08": SEAL, "P2-08b": SEAL}
    assert log_lines(root) == []


@pytest.mark.parametrize("missing", ["arg", "env", "file"])
def test_any_one_of_three_missing_refuses_beyond_seal_with_reason(root, monkeypatch, missing):
    if missing != "env":
        monkeypatch.setenv(EXPLORE_ENV, EXPLORE_ENV_VALUE)
    if missing != "file":
        approve(root)
    arg = None if missing == "arg" else "P2-08"
    reason = {"arg": "引数 explore_window", "env": "環境変数 W4_WINDOW1", "file": "承認のファイル"}[missing]
    others = [v for k, v in {"arg": "引数 explore_window", "env": "環境変数 W4_WINDOW1", "file": "承認のファイル"}.items()
              if k != missing]
    with pytest.raises(SealedRangeError) as e:
        load(str(root), [ds(WIN_FILE, SEAL, SEAL + 30 * MIN)], explore_window=arg)
    msg = str(e.value)
    assert "探索の窓の上書きは効いていない" in msg and reason in msg
    assert all(o not in msg for o in others)  # 欠けていないものは理由に出ない
    assert str(SEAL) in msg  # 境は今までと同じ 2023-12-18
    assert log_lines(root) == []  # 上書きが効いていないので記録は足さない
    with pytest.raises(SealedRangeError):  # 参照の行の口も同じ
        load_reference(str(root), ref_ds(SEAL, SEAL + 30 * MIN), declarations=_decl(), explore_window=arg)


def _decl():
    return {"ref": {"lag_ns": 60 * NS, "source": "synthetic (test)"}}  # 定数のラグ 60 秒の宣言


def test_all_three_open_window_to_judgment_start_and_refuse_beyond(root, monkeypatch):
    monkeypatch.setenv(EXPLORE_ENV, EXPLORE_ENV_VALUE)
    approve(root)
    res = load(str(root), [ds(WIN_FILE, END - 60 * MIN, END)], explore_window="P2-08")  # ちょうど窓の終わりまで
    assert len(res.records("bars")) == 60
    assert max(r["start_ns"] for r in res.records("bars")) < END
    with pytest.raises(SealedRangeError) as e:  # 終わりが 1 分でも後なら拒む(ファイルは開く前)
        load(str(root), [ds(WIN_FILE, END - 60 * MIN, END + MIN)], explore_window="P2-08")
    assert str(END) in str(e.value)
    reg = SealRegistry(str(root), "P2-08")
    with pytest.raises(SealedRangeError):  # 範囲なしも拒む
        reg.check_range(reg.by_path(os.path.realpath(root / WIN_FILE)), WIN_FILE, None)
    # 参照の行の口も同じ
    s = load_reference(str(root), ref_ds(END - 60 * MIN, END), declarations=_decl(), explore_window="P2-08")
    assert len(s.times_ns) == 60 and max(s.times_ns) < END
    with pytest.raises(SealedRangeError):
        load_reference(str(root), ref_ds(END - 60 * MIN, END + MIN), declarations=_decl(), explore_window="P2-08")


def test_all_three_do_not_move_other_units_cutoff(root, monkeypatch):
    monkeypatch.setenv(EXPLORE_ENV, EXPLORE_ENV_VALUE)
    approve(root)
    reg = SealRegistry(str(root), "P2-08")
    cut = {e.unit: e.cutoff_ns for e in reg.entries}
    assert cut == {"P2-08": END, "P2-08b": SEAL}
    with pytest.raises(SealedRangeError) as e:
        load(str(root), [ds(OTHER_FILE, SEAL, SEAL + 30 * MIN)], explore_window="P2-08")
    assert "P2-08b" in str(e.value) and "探索の窓" not in str(e.value)  # 別の unit は理由の文も付かない
    # 別の unit の copy(別名のファイル、同じ中身)も P2-08b の境のまま
    (root / "backtest_data" / "synth_other" / "copy.csv.gz").write_bytes((root / OTHER_FILE).read_bytes())
    with pytest.raises(SealedRangeError):
        load(str(root), [ds("backtest_data/synth_other/copy.csv.gz", SEAL, SEAL + 30 * MIN)], explore_window="P2-08")


def test_override_writes_one_log_line_per_load_and_none_when_not_in_force(root, monkeypatch):
    monkeypatch.setenv(EXPLORE_ENV, EXPLORE_ENV_VALUE)
    approve(root)
    load(str(root), [ds(WIN_FILE, END - 60 * MIN, END)], explore_window="P2-08")
    ls = log_lines(root)
    assert len(ls) == 1
    x = ls[0]
    assert x["what"] == "load" and x["cut"] == "2025-12-12T00:00:00Z" and "ts_utc" in x
    assert x["ranges"] == [{"name": "bars", "lo": "2025-12-11T23:00:00Z", "hi": "2025-12-12T00:00:00Z"}]
    assert os.path.basename(__file__) in x["script"]  # 呼び出し元 = このファイル(データ層の中ではない)
    load_reference(str(root), ref_ds(END - 60 * MIN, END), declarations=_decl(), explore_window="P2-08")
    ls = log_lines(root)
    assert len(ls) == 2 and ls[1]["what"] == "load_reference"
    # 拒まれた読み(終わりが後)も、上書きが効いていれば読む前に記録は残る
    with pytest.raises(SealedRangeError):
        load(str(root), [ds(WIN_FILE, END - 60 * MIN, END + MIN)], explore_window="P2-08")
    assert len(log_lines(root)) == 3
    # 値は記録に残らない
    assert "1000" not in (root / os.path.join(*EXPLORE_LOG)).read_text(encoding="utf-8")


def test_log_unwritable_refuses_before_reading(root, monkeypatch):
    monkeypatch.setenv(EXPLORE_ENV, EXPLORE_ENV_VALUE)
    approve(root)
    p = root / os.path.join(*EXPLORE_LOG)
    p.mkdir()  # 記録の置き場がディレクトリで書けない
    with pytest.raises(SealedRangeError) as e:
        load(str(root), [ds(WIN_FILE, END - 60 * MIN, END)], explore_window="P2-08")
    assert "記録" in str(e.value)


def test_w4_common_load_bars_window_passes_argument_through_both_doors(root, monkeypatch):
    """窓の口(common.load_bars(window=True))は、窓の口の 2 つの門とデータ層の門の両方を通ったときだけ読める。"""
    import importlib.util
    path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts",
                                         "w4_measure", "common.py"))
    spec = importlib.util.spec_from_file_location("w4_common_seal_override", path)  # 名前 common を sys.modules に残さない
    CM = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(CM)
    rel = f"{CM.FX_DIR}/candles_1m_2025.csv.gz"
    _bars(root / rel, END - 60 * MIN, 90, 2000.0)
    _ledger(root, "P2-08", rel)
    monkeypatch.setattr(CM, "ROOT", str(root))
    monkeypatch.setenv(CM.WINDOW1_ENV, CM.WINDOW1_ENV_VALUE)
    approve(root)
    bars, kinds, hashes = CM.load_bars(CM.FX_DIR, "FX_BTC_JPY", END - 60 * MIN, END, window=True)
    assert len(bars) == 60
    ls = log_lines(root)
    assert [x.get("what", "") for x in ls].count("load") == 1  # データ層の記録 1 行(窓の口の記録と trim の記録は別)
    # 窓の口の門だけでは足りない: データ層の引数が欠ければ(= window=False)窓の口の外で拒まれる
    with pytest.raises(SystemExit):
        CM.load_bars(CM.FX_DIR, "FX_BTC_JPY", END - 60 * MIN, END)
    # データ層の門が欠ける(承認のファイルを消す)と、窓の口の門で拒まれ、データ層まで行かない
    (root / os.path.join(*EXPLORE_APPROVAL)).unlink()
    with pytest.raises(SystemExit):
        CM.load_bars(CM.FX_DIR, "FX_BTC_JPY", END - 60 * MIN, END, window=True)


def test_no_log_line_when_ledger_has_no_p2_08_entry(root, monkeypatch):
    """3 つそろっていても、台帳に unit P2-08 の項目が無ければ動かす境が無いので記録は足さない(別の unit の読みだけ)。"""
    monkeypatch.setenv(EXPLORE_ENV, EXPLORE_ENV_VALUE)
    approve(root)
    (root / "backtest_data" / "phase2_sealed" / "P2-08" / "SEALED.json").unlink()
    load(str(root), [ds(OTHER_FILE, SEAL - 30 * MIN, SEAL)], explore_window="P2-08")
    assert log_lines(root) == []
