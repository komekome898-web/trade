"""探索の窓の口(`scripts/w4_measure/common.py` の window_guard・check_end・load_bars・window_trim_report、
`c2_limit_run.py`・`c4_limit_run.py` の --window1・--measure-from)の試験。

封印の決まり: この試験は合成のデータだけを使う。時刻は試験の時刻で、実データではない(実データのファイルは開かない)。
ROOT は一時ディレクトリに差し替える(承認のファイルは一時ディレクトリに置いた偽物)。
"""
from __future__ import annotations

import gzip
import importlib
import json
import os
import sys
from datetime import datetime, timezone

import pytest

NS = 1_000_000_000
MIN = 60 * NS


def _load_w4(name):
    """scripts/w4_measure の台本を読み込む(test_window1_loader・test_c2_limit_run_ref_filter・test_katsuo_limit_sim・
    test_matilda_limit_sim の _load_w4 は同じ中身)。台本は `from common import ...` で同じ置き場の common を読むが、
    別の試験は別の `common`(tests/bt/battery/item_0/adapters/common.py など)を同じ名前 common で使う。
    - 読み込む間だけ、名前 common・post・run_v2 に w4_measure の物を置く。前に読んだ物は sys.modules の
      `_w4measure__<名前>` に控えた同じ物を使う(全部の試験で w4_measure の common は 1 つ)。
    - 終わったら名前 common・post・run_v2 を読み込む前の状態に戻す(前に無ければ消す)。他の試験に w4_measure の物を残さない。
    - sys.path も読み込む前の並びに戻す(台本が自分の置き場を先頭に足したままにすると、別の試験の `import common` が
      w4_measure の common.py を見つける)。
    台本の common を試験で使うときは名前 common で引き直さず、`sys.modules["_w4measure__common"]` を使う。"""
    d = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "w4_measure"))
    if name in sys.modules:
        return sys.modules[name]
    shared = ("common", "post", "run_v2")

    def mine(m):
        return os.path.dirname(os.path.abspath(getattr(m, "__file__", None) or "")) == d

    before = {k: sys.modules.pop(k) for k in shared if k in sys.modules}
    for k, m in before.items():
        if mine(m):
            sys.modules.setdefault("_w4measure__" + k, m)
    for k in shared:
        if "_w4measure__" + k in sys.modules:
            sys.modules[k] = sys.modules["_w4measure__" + k]
    path_before = list(sys.path)
    sys.path.insert(0, d)
    try:
        return importlib.import_module(name)
    finally:
        sys.path[:] = path_before  # 台本自身も置き場を sys.path の先頭に足す(c4_limit_run・c2_limit_run・run_v2)
        for k in shared:
            m = sys.modules.pop(k, None)
            if m is not None and mine(m):
                sys.modules.setdefault("_w4measure__" + k, m)
        sys.modules.update(before)


C4 = _load_w4("c4_limit_run")
C2 = _load_w4("c2_limit_run")
CM = sys.modules["_w4measure__common"]  # c4・c2 が読み込んだ common(名前 common で引き直さない。_load_w4 の注)
assert C4.load_bars.__globals__ is CM.__dict__ and C2.load_bars.__globals__ is CM.__dict__


def ns(s: str) -> int:
    return CM.iso(s)


@pytest.fixture()
def root(tmp_path, monkeypatch):
    """偽の ROOT。承認のファイルの置き場の親だけ作る(承認のファイルは試験ごとに置く)。環境変数は外しておく。"""
    r = tmp_path / "root"
    (r / "backtest_data" / "phase2_sealed" / "P2-08").mkdir(parents=True)
    monkeypatch.setattr(CM, "ROOT", str(r))
    monkeypatch.setitem(sys.modules, "common", CM)  # 台本の中の遅い `from common import`(vol_split_daily.classify など)も CM を読む
    monkeypatch.delenv(CM.WINDOW1_ENV, raising=False)
    return r


def approve(root):
    (root / CM.WINDOW1_APPROVAL).write_text("test approval (合成)\n", encoding="utf-8")


def log_lines(root):
    p = root / CM.WINDOW1_LOG
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


# --- 門 ---------------------------------------------------------------------------------------------

def test_guard_refuses_without_env_or_file_and_passes_with_both(root, monkeypatch):
    lo, hi = ns("2024-01-01T00:00:00Z"), ns("2024-02-01T00:00:00Z")
    with pytest.raises(SystemExit):  # 両方欠け
        CM.window_guard(lo, hi)
    monkeypatch.setenv(CM.WINDOW1_ENV, CM.WINDOW1_ENV_VALUE)
    with pytest.raises(SystemExit) as e:  # 環境変数だけ
        CM.window_guard(lo, hi)
    assert "承認のファイル" in str(e.value) and "環境変数" not in str(e.value)
    monkeypatch.delenv(CM.WINDOW1_ENV)
    approve(root)
    with pytest.raises(SystemExit) as e:  # ファイルだけ
        CM.window_guard(lo, hi)
    assert "環境変数" in str(e.value) and "承認のファイル" not in str(e.value)
    monkeypatch.setenv(CM.WINDOW1_ENV, "other")
    with pytest.raises(SystemExit):  # 値が違う環境変数
        CM.window_guard(lo, hi)
    assert log_lines(root) == []  # 拒んだ呼びは記録に残さない
    monkeypatch.setenv(CM.WINDOW1_ENV, CM.WINDOW1_ENV_VALUE)
    CM.window_guard(lo, hi)  # 両方そろえば通る
    assert len(log_lines(root)) == 1


def test_guard_refuses_end_past_window_end_even_with_both_doors(root, monkeypatch):
    monkeypatch.setenv(CM.WINDOW1_ENV, CM.WINDOW1_ENV_VALUE)
    approve(root)
    end = ns("2025-12-12T00:00:00Z")
    assert CM.WINDOW1[1] == end and CM.WINDOW1[0] == ns("2023-12-18T00:00:00Z")
    CM.window_guard(ns("2025-12-01T00:00:00Z"), end)  # ちょうど終わりは通る
    with pytest.raises(SystemExit) as e:
        CM.window_guard(ns("2025-12-01T00:00:00Z"), end + NS)
    assert "判定の期間" in str(e.value)
    with pytest.raises(SystemExit):
        CM.check_end(end + NS, window=True)
    with pytest.raises(SystemExit):  # load_bars も、データの層に行く前に拒む
        CM.load_bars(CM.FX_DIR, "FX_BTC_JPY", ns("2025-12-01T00:00:00Z"), end + NS, window=True)
    assert len(log_lines(root)) == 1  # 通った 1 回だけ


def test_default_check_end_and_load_bars_unchanged(root, monkeypatch):
    seal = ns("2023-12-18T00:00:00Z")
    CM.check_end(seal)  # 封印の境ちょうどまでは今までどおり通る
    with pytest.raises(SystemExit) as e:
        CM.check_end(seal + NS)
    assert "封印の境" in str(e.value)
    monkeypatch.setenv(CM.WINDOW1_ENV, CM.WINDOW1_ENV_VALUE)  # 環境変数・承認のファイルがあっても、引数なしは窓を開けない
    approve(root)
    with pytest.raises(SystemExit):
        CM.check_end(seal + NS)
    with pytest.raises(SystemExit):
        CM.bar_dataset(CM.FX_DIR, "FX_BTC_JPY", seal, seal + MIN)
    with pytest.raises(SystemExit):
        CM.binance_ref_dataset("x", "close", seal, seal + MIN)
    assert log_lines(root) == []
    # 窓の口を通っていない呼びの置き場は今までと同じ(2024 年以降の単一のファイルは窓のときだけ)
    d = CM.binance_ref_dataset("x", "close", ns("2023-01-01T00:00:00Z"), seal)
    assert all("20240101" not in p for p in d["paths"])


def test_binance_spot_paths_window_uses_single_file_for_2024_on(root):
    for y in (2022, 2023):  # 置き場の存在だけ見る(中身は空の合成)
        f = root / CM.BIN_DIR / f"binance_BTCUSDT_1m_{y}.csv.gz"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"")
    p = CM.binance_spot_paths(ns("2022-12-18T00:00:00Z"), ns("2024-01-01T00:00:00Z"))
    assert p == [f"{CM.BIN_DIR}/binance_BTCUSDT_1m_2022.csv.gz", f"{CM.BIN_DIR}/binance_BTCUSDT_1m_2023.csv.gz"]
    p = CM.binance_spot_paths(ns("2023-12-01T00:00:00Z"), ns("2025-12-12T00:00:00Z"))
    assert p == [f"{CM.BIN_DIR}/binance_BTCUSDT_1m_2023.csv.gz", f"{CM.BIN_DIR_2024}/{CM.BIN_FILE_2024}"]


# --- 記録 ---------------------------------------------------------------------------------------------

def test_each_pass_appends_one_log_line_with_script_and_range(root, monkeypatch):
    monkeypatch.setenv(CM.WINDOW1_ENV, CM.WINDOW1_ENV_VALUE)
    approve(root)
    for i in range(3):
        CM.window_guard(ns("2024-01-01T00:00:00Z"), ns("2024-01-02T00:00:00Z") + i * MIN, script="fake_script.py", what=f"t{i}")
    ls = log_lines(root)
    assert len(ls) == 3
    assert [x["what"] for x in ls] == ["t0", "t1", "t2"]
    assert all(x["script"] == "fake_script.py" and x["lo"] == "2024-01-01T00:00:00Z" and "ts_utc" in x for x in ls)
    assert ls[2]["hi"] == "2024-01-02T00:02:00Z"


def _write_bars(path, start, n, price0=100.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        fh.write("ts,open,high,low,close,volume,col7_inferred_long_oi,col8_inferred_short_oi,buy_volume,sell_volume\n")
        for i in range(n):
            t = datetime.fromtimestamp(start / 1e9 + i * 60, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            p = price0 + i
            fh.write(f"{t},{p},{p + 1},{p - 1},{p},1.0,0,0,0.5,0.5\n")


def test_load_bars_window_logs_and_trims_rows_at_or_after_window_end(root, monkeypatch):
    """判定の期間の行を混ぜた合成のファイル: 窓の終わりの前 10 本と後ろ 7 本。後ろの行は落ち、数だけが記録に残り、値は残らない。"""
    end = CM.WINDOW1[1]
    f = root / CM.FX_DIR / "candles_1m_2025.csv.gz"
    _write_bars(f, end - 10 * MIN, 17, price0=7777.0)
    monkeypatch.setenv(CM.WINDOW1_ENV, CM.WINDOW1_ENV_VALUE)
    approve(root)
    bars, kinds, hashes = CM.load_bars(CM.FX_DIR, "FX_BTC_JPY", end - 10 * MIN, end, window=True)
    assert len(bars) == 10
    assert all(int(b.start_time_ns) < end for b in bars)
    ls = log_lines(root)
    assert len(ls) == 2  # 通った記録 1 行 + 落とした数の記録 1 行
    assert ls[0]["what"].startswith("load_bars") and ls[0]["hi"] == "2025-12-12T00:00:00Z"
    t = ls[1]
    assert t["what"].startswith("trim") and t["cut"] == "2025-12-12T00:00:00Z"
    assert t["dropped_rows_total"] == 7
    assert list(t["dropped_rows_in_files"].values()) == [7]
    assert t["dropped_after_load"] == 0
    raw = (root / CM.WINDOW1_LOG).read_text(encoding="utf-8")
    assert "7777" not in raw and "7786" not in raw  # 値は記録に残さない


def test_trim_report_counts_in_every_file_and_hides_values(root, monkeypatch):
    end = CM.WINDOW1[1]
    a = root / "backtest_data" / "x" / "a.csv.gz"
    b = root / "backtest_data" / "x" / "b.csv.gz"
    for p, off, n in ((a, -3, 5), (b, 0, 4)):  # a: 前 3 本・後 2 本 / b: 全部後
        p.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(p, "wt", encoding="utf-8", newline="") as fh:
            fh.write("open_time,close\n")
            for i in range(n):
                t = datetime.fromtimestamp(end / 1e9 + (off + i) * 60, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                fh.write(f"{t},424242.5\n")
    with pytest.raises(SystemExit):  # 門がなければ数えない
        CM.window_trim_report(["backtest_data/x/a.csv.gz"], "open_time")
    monkeypatch.setenv(CM.WINDOW1_ENV, CM.WINDOW1_ENV_VALUE)
    approve(root)
    n = CM.window_trim_report(["backtest_data/x/a.csv.gz", "backtest_data/x/b.csv.gz"], "open_time", what="t")
    assert n == 2 + 4
    rec = log_lines(root)[-1]
    assert rec["dropped_rows_in_files"] == {"backtest_data/x/a.csv.gz": 2, "backtest_data/x/b.csv.gz": 4}
    assert "424242" not in (root / CM.WINDOW1_LOG).read_text(encoding="utf-8")
    with pytest.raises(SystemExit):  # 時刻の列が無い
        CM.window_trim_report(["backtest_data/x/a.csv.gz"], "ts")


def test_window_reads_cover_the_2022_file_too(root, monkeypatch):
    """2022-12-18 から読み始める窓の走らせ: 2022 年のファイルの区切りも窓の口を通り、記録に残る。"""
    monkeypatch.setenv(CM.WINDOW1_ENV, CM.WINDOW1_ENV_VALUE)
    approve(root)
    lo = ns("2022-12-18T00:00:00Z")
    f = root / CM.FX_DIR / "candles_1m_2022.csv.gz"
    _write_bars(f, lo, 30)
    bars, _, _ = CM.load_bars(CM.FX_DIR, "FX_BTC_JPY", lo, lo + 30 * MIN, window=True)
    assert len(bars) == 30
    ls = log_lines(root)
    assert ls[0]["lo"] == "2022-12-18T00:00:00Z"
    assert list(ls[1]["dropped_rows_in_files"]) == [f"{CM.FX_DIR}/candles_1m_2022.csv.gz"]


# --- --measure-from -----------------------------------------------------------------------------------

def _trade(entry, exit_):
    return {"entry_ns": entry, "exit_ns": exit_, "pnl_pct": 1.0, "undecided": 0}


def test_split_measured_excludes_trades_before_measure_from():
    mf = ns("2023-12-18T00:00:00Z")
    rows = [_trade(mf - 5 * MIN, mf - MIN), _trade(mf - MIN, mf), _trade(mf, mf + MIN), _trade(mf + MIN, mf + 2 * MIN)]
    kept, dropped = CM.split_measured(rows, mf)
    assert [r["exit_ns"] for r in kept] == [mf, mf + MIN, mf + 2 * MIN]  # 出の時刻が mf ちょうどは入る
    assert [r["exit_ns"] for r in dropped] == [mf - MIN]
    assert CM.split_measured(rows, None) == (rows, [])
    # 集計(c4 の year_stats / by_year)に、外した取引が入らない
    assert C4.year_stats(kept, 1.0)["trades"] == 3
    assert C4.by_year(kept, mf, mf + 2 * 86_400 * NS)["2023"]["trades"] == 3
    assert C4.year_stats(rows, 1.0)["trades"] == 4


def test_c4_main_window_end_to_end_with_synthetic_bars(root, monkeypatch, tmp_path):
    """合成の足で c4 を --window1 で走らせる: 門を通り、記録が残り、集計の期間は --measure-from から、判定の期間の行は入らない。"""
    end = CM.WINDOW1[1]
    _write_bars(root / CM.FX_DIR / "candles_1m_2025.csv.gz", end - 60 * MIN, 70)  # 最後の 10 本は窓の終わり以降
    monkeypatch.setenv(CM.WINDOW1_ENV, CM.WINDOW1_ENV_VALUE)
    approve(root)
    out = tmp_path / "out"
    mfrom = CM.to_iso(end - 30 * MIN)
    monkeypatch.setattr(sys, "argv", ["c4_limit_run.py", "--fill-side", "good", "--out", str(out), "--window1",
                                      "--start", CM.to_iso(end - 60 * MIN), "--measure-from", mfrom])
    assert C4.main() == 0
    s = json.load(open(out / "summary.json", encoding="utf-8"))
    assert s["period"] == [mfrom, "2025-12-12T00:00:00Z"]
    rr = json.load(open(out / "run_record.json", encoding="utf-8"))
    assert rr["chunks"][0]["bars"] == 60  # 窓の終わり以降の 10 本は読まれない
    assert rr["measure"]["measure_from"] == mfrom
    with gzip.open(out / "trades.csv.gz", "rt", encoding="utf-8") as fh:
        assert fh.readline().strip().endswith(",in_measure")
    assert any(x["what"].startswith("trim") for x in log_lines(root))


def test_c4_default_run_has_no_measure_column_and_still_refuses_after_seal(root, tmp_path, monkeypatch):
    out = tmp_path / "o2"
    monkeypatch.setattr(sys, "argv", ["c4_limit_run.py", "--fill-side", "good", "--out", str(out),
                                      "--start", "2023-12-17T00:00:00Z", "--end", "2023-12-19T00:00:00Z"])
    with pytest.raises(SystemExit) as e:
        C4.main()
    assert "封印の境" in str(e.value)  # 引数なし(窓なし)は今までどおり 2023-12-18 より後を拒む


def test_c4_and_c2_window1_refuse_without_doors_before_reading(root, tmp_path, monkeypatch):
    for mod, extra in ((C4, []), (C2, ["--series", "a", "--at-max", "skip"])):
        monkeypatch.setattr(sys, "argv", ["x.py", "--fill-side", "good", "--out", str(tmp_path / "o"), "--window1"] + extra)
        with pytest.raises(SystemExit) as e:
            mod.main()
        assert "環境変数" in str(e.value)
    assert log_lines(root) == []


def test_c2_window1_period_and_option_checks(root, tmp_path, monkeypatch):
    monkeypatch.setenv(CM.WINDOW1_ENV, CM.WINDOW1_ENV_VALUE)
    approve(root)

    def run(*args):
        monkeypatch.setattr(sys, "argv", ["c2_limit_run.py", "--fill-side", "good", "--out", str(tmp_path / "o"),
                                          "--at-max", "skip", "--window1", *args])
        with pytest.raises(SystemExit) as e:
            C2.main()
        return str(e.value)
    assert "系列 (a) だけ" in run("--series", "b")
    assert "併用できない" in run("--ref-drop-no-trade")
    assert "窓" in run("--end", "2025-12-12T00:00:01Z")  # 判定の期間にかかる
    assert "窓" in run("--measure-from", "2023-12-17T23:59:00Z")  # 窓の始めより前
    assert log_lines(root) == []


def test_vol_split_window_args(root, monkeypatch):
    vs = _load_w4("vol_split_daily")
    vol = {}
    from datetime import date, timedelta
    d = date(2022, 1, 1)
    while d <= date(2025, 12, 20):  # 試験の値(実データではない)
        vol[d.isoformat()] = 1.0 + (d.toordinal() % 7)
        d += timedelta(days=1)
    base = vs.classify(vol)  # 既定は 2023-12-17 まで
    assert base and max(base) == "2023-12-17"
    with pytest.raises(SystemExit):  # 門なしでは窓の最後の日まで返さない
        vs.classify(vol, window=True)
    monkeypatch.setenv(CM.WINDOW1_ENV, CM.WINDOW1_ENV_VALUE)
    approve(root)
    w = vs.classify(vol, window=True)
    assert max(w) == "2025-12-11"
    assert {k: v for k, v in w.items() if k <= "2023-12-17"} == base
