"""W4 の測定(カード 2 の変種 (a)、カード 3)で共有する入力の組み立て。

封印の門(bot.bt.data の load / load_reference)だけを通して読む。参考にした台本:
scratchpad/w4/c1_rewrite/compare.py(読むだけ。書き換えていない)。

  持つ足: bot.bt.data.load(kind bar、ts = 1 分の始まり、gap は accept、no_trade は drop)
  参照:   bot.bt.data.reference.load_reference(行の時刻 = 置き場の時刻のまま、lag_ns 60 秒)
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import resource
import sys
import time
from datetime import datetime, timezone

NS = 1_000_000_000
MIN_NS = 60 * NS
DAY_NS = 86_400 * NS
SEAL = datetime(2023, 12, 18, tzinfo=timezone.utc)
ROOT = "/home/user/trade"

FX_DIR = "backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906"
SPOT_DIR = "backtest_data/bitflyer_lightchart_BTC_JPY_1m_20260906"
BAR_FILE = "candles_1m_{y}.csv.gz"
BIN_DIR = "backtest_data/binance_BTCUSDT_1m_20170801_20231231"
BIN_FILE = "binance_BTCUSDT_1m_{y}.csv.gz"
USDJPY_PATH = "backtest_data/fx_usdjpy_1m_20170801_20221231/usdjpy_1m.csv.gz"
# 2023-01-01 からの USDJPY(USDJPY_PATH の置き場の README「Extends … (2023-01-01 onward)」「0 overlapping rows」「Safe to
# concatenate」)。usdjpy_ref_dataset(extend=True) で、終わりが 2023-01-01 より後のときだけ足す。extend=True の終わりは USDJPY_EXTEND_END まで。
USDJPY_PATH_2023 = "backtest_data/fx_usdjpy_1m_20260822.csv.gz"
USDJPY_2023_FROM = "2023-01-01T00:00:00Z"
USDJPY_EXTEND_END = "2023-12-17T15:00:00Z"  # extend=True の終わりの上限(封印の境 2023-12-18T00:00Z の前の日本時間の日の終わり)
BIN_DIR_2024 = "backtest_data/binance_BTCUSDT_1m_20240101_20260831"  # 2024 年以降は 1 つのファイル(窓の口でだけ使う)
BIN_FILE_2024 = "binance_BTCUSDT_1m_20240101_20260831.csv.gz"
BAR_RESOLVE = {"gap": "accept", "no_trade": "drop"}


def to_ns(d: datetime) -> int:
    return int(d.timestamp()) * NS


def iso(s: str) -> int:
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return to_ns(d)


def to_iso(ns: int) -> str:
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# 探索の窓(P2-08、オーナー L-532「決めること　開けてよい」)。[始め, 終わり)。判定の期間(終わり以降)は読む経路を作らない。
WINDOW1 = (to_ns(datetime(2023, 12, 18, tzinfo=timezone.utc)), to_ns(datetime(2025, 12, 12, tzinfo=timezone.utc)))
WINDOW1_LAST_DAY = "2025-12-11"  # 窓の終わり(2025-12-12T00:00Z = 日本時間 9 時)の前で、日本時間の 1 日が全部入る最後の日
WINDOW1_WARMUP_START = "2022-12-18T00:00:00Z"  # 窓の走らせの読み始め(窓の始まりの直前 365 日の門のため)
WINDOW1_ENV = "W4_WINDOW1"
WINDOW1_ENV_VALUE = "P2-08-explore"
WINDOW1_UNIT = "P2-08"  # データ層(SealRegistry)の探索の窓の引数 explore_window の値。窓の口を通ったときだけ load・load_reference に渡す
WINDOW1_APPROVAL = "backtest_data/phase2_sealed/P2-08/EXPLORE_WINDOW_APPROVED"  # リードがオーナーの言葉を写して作る。このコードは作らない
WINDOW1_LOG = "backtest_data/phase2_sealed/P2-08/explore_access_log.jsonl"


def _window_doors(hi_ns: int, root: str | None = None) -> None:
    """窓の口の門。(1) 環境変数 (2) 承認のファイル (3) 終わりが WINDOW1 の終わりを越えない。欠ければ全部の理由を書いて拒む。"""
    root = ROOT if root is None else root
    why = []
    if os.environ.get(WINDOW1_ENV) != WINDOW1_ENV_VALUE:
        why.append(f"環境変数 {WINDOW1_ENV} が {WINDOW1_ENV_VALUE!r} でない")
    if not os.path.isfile(os.path.join(root, WINDOW1_APPROVAL)):
        why.append(f"承認のファイル {WINDOW1_APPROVAL} が無い")
    if hi_ns > WINDOW1[1]:
        why.append(f"終わり {to_iso(hi_ns)} は窓の終わり {to_iso(WINDOW1[1])} より後(判定の期間は読めない)")
    if why:
        raise SystemExit("拒否(探索の窓の口): " + "; ".join(why))


def window_guard(lo_ns: int, hi_ns: int, *, script: str | None = None, what: str = "", root: str | None = None) -> None:
    """窓の口: 上の 3 つの門を通れば、記録(WINDOW1_LOG)に 1 行追記してから返す。記録を書けなければ拒む。
    記録は読む前に書く(読みが途中で落ちても残る)。script = 呼んだ台本(既定は起動した台本のファイル名)。"""
    root = ROOT if root is None else root
    if lo_ns >= hi_ns:
        raise SystemExit(f"拒否(探索の窓の口): 始め {to_iso(lo_ns)} が終わり {to_iso(hi_ns)} 以降")
    _window_doors(hi_ns, root)
    rec = {"ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
           "script": script or os.path.basename(sys.argv[0] or ""), "what": what,
           "lo": to_iso(lo_ns), "hi": to_iso(hi_ns)}
    try:
        with open(os.path.join(root, WINDOW1_LOG), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError as exc:
        raise SystemExit(f"拒否(探索の窓の口): 記録 {WINDOW1_LOG} に書けない({exc})")


def split_measured(rows: list, measure_from_ns: int | None, key: str = "exit_ns") -> tuple:
    """(集計に入れる行, 外す行)。key の時刻が measure_from 以上の行を入れる(None なら全部入れる)。外した行は呼び出し側が記録に残す。"""
    if measure_from_ns is None:
        return list(rows), []
    return ([r for r in rows if r[key] >= measure_from_ns], [r for r in rows if r[key] < measure_from_ns])


def window_trim_report(rel_paths: list, time_col: str, *, what: str = "", late_after_load: int = 0,
                       script: str | None = None, root: str | None = None) -> int:
    """窓の口の、判定の期間の行の扱い。ファイルを読んだ直後(値を使う前)に呼ぶ。各ファイルの時刻の列だけを見て、
    時刻が WINDOW1 の終わり(2025-12-12T00:00Z)以上の行を数え、数だけを記録(WINDOW1_LOG)に 1 行足す(値は見ない・書かない)。
    落とすのは読み込み層の範囲([始め, 終わり)、終わり <= WINDOW1 の終わり)で、範囲の外の行は値を読まずに飛ばされる。
    late_after_load = 読み込みの後に残っていて、呼び出し側が落とした行の数(0 のはず)。合計を返す。"""
    root = ROOT if root is None else root
    _window_doors(WINDOW1[1], root)
    per = {}
    for p in rel_paths:
        n = 0
        opener = gzip.open if p.endswith(".gz") else open
        with opener(os.path.join(root, p), "rt", encoding="utf-8", newline="") as fh:
            r = csv.reader(fh)
            head = next(r, None)
            if head is None or time_col not in head:
                raise SystemExit(f"拒否(探索の窓の口): {p} の見出しに時刻の列 {time_col!r} が無い")
            k = head.index(time_col)
            for row in r:
                if row and iso(row[k]) >= WINDOW1[1]:
                    n += 1
        per[p] = n
    rec = {"ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
           "script": script or os.path.basename(sys.argv[0] or ""), "what": "trim " + what,
           "cut": to_iso(WINDOW1[1]), "dropped_rows_in_files": per, "dropped_rows_total": sum(per.values()),
           "dropped_after_load": late_after_load}
    try:
        with open(os.path.join(root, WINDOW1_LOG), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError as exc:
        raise SystemExit(f"拒否(探索の窓の口): 記録 {WINDOW1_LOG} に書けない({exc})")
    return sum(per.values())


def check_end(hi_ns: int, window: bool = False) -> None:
    """既定は封印の境(SEAL)より後を拒む。window=True は窓の口の門(_window_doors)を通ったときだけ、終わりを WINDOW1 の終わりまで許す。"""
    if window:
        _window_doors(hi_ns)
        return
    if hi_ns > to_ns(SEAL):
        raise SystemExit(f"拒否: 終わり {to_iso(hi_ns)} は封印の境 {SEAL.isoformat()} より後")


def years(lo_ns: int, hi_ns: int) -> range:
    y0 = datetime.fromtimestamp(lo_ns / 1e9, tz=timezone.utc).year
    y1 = datetime.fromtimestamp((hi_ns - 1) / 1e9, tz=timezone.utc).year
    return range(y0, y1 + 1)


def paths(d: str, pattern: str, lo_ns: int, hi_ns: int) -> list:
    return [f"{d}/{pattern.format(y=y)}" for y in years(lo_ns, hi_ns)
            if os.path.exists(os.path.join(ROOT, d, pattern.format(y=y)))]


def bar_dataset(d: str, symbol: str, lo_ns: int, hi_ns: int, name: str = "bars", window: bool = False) -> dict:
    check_end(hi_ns, window)
    return {"name": name, "paths": paths(d, BAR_FILE, lo_ns, hi_ns), "range_ns": [lo_ns, hi_ns],
            "spec": {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip", "kind": "bar",
                     "symbol": symbol, "asset": "crypto",
                     "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
                     "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
                     "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start",
                     "no_trade": {"fields": ["open", "high", "low", "close"]}}}


def binance_spot_paths(lo_ns: int, hi_ns: int) -> list:
    """Binance 現物 BTCUSDT 1 分足の置き場(窓の口用)。2023 年以前は今の置き場の年ごとのファイル、2024 年以降は 1 つのファイル
    (範囲が 2024 年以降にかかるときだけ入れる)。"""
    ps = paths(BIN_DIR, BIN_FILE, lo_ns, hi_ns)
    if hi_ns > to_ns(datetime(2024, 1, 1, tzinfo=timezone.utc)):
        ps.append(f"{BIN_DIR_2024}/{BIN_FILE_2024}")
    return ps


def binance_ref_dataset(name: str, column: str, lo_ns: int, hi_ns: int, window: bool = False) -> dict:
    check_end(hi_ns, window)
    return {"name": name, "paths": binance_spot_paths(lo_ns, hi_ns) if window else paths(BIN_DIR, BIN_FILE, lo_ns, hi_ns), "range_ns": [lo_ns, hi_ns],
            "spec": {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip",
                     "time": {"columns": ["open_time"], "unit": "iso", "tz": "UTC"}, "value": column}}


def usdjpy_ref_dataset(name: str, lo_ns: int, hi_ns: int, extend: bool = False) -> dict:
    """既定(extend=False)は今までと同じ USDJPY_PATH の 1 ファイル。extend=True で終わりが USDJPY_2023_FROM より後なら
    USDJPY_PATH_2023 を後ろに足す(読むのは封印の門 load_reference の中だけ。範囲 [lo, hi) の外の行は門が値を使わずに飛ばす)。
    extend=True のときだけ、終わりが USDJPY_EXTEND_END(2023-12-17T15:00Z)より後なら拒む(check_end の境 2023-12-18T00:00Z より
    9 時間前。既定の extend=False と、ほかの口の check_end は変えない)。"""
    check_end(hi_ns)
    if extend and hi_ns > iso(USDJPY_EXTEND_END):
        raise SystemExit(f"拒否: extend=True の終わり {to_iso(hi_ns)} は {USDJPY_EXTEND_END} より後(2023 年の USDJPY の読みは "
                         f"{USDJPY_EXTEND_END} まで)")
    ps = [USDJPY_PATH]
    if extend and hi_ns > iso(USDJPY_2023_FROM):
        ps.append(USDJPY_PATH_2023)
    return {"name": name, "paths": ps, "range_ns": [lo_ns, hi_ns],
            "spec": {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip",
                     "time": {"columns": ["timestamp"], "unit": "iso", "tz": "UTC"}, "value": "close"}}


def load_bars(d: str, symbol: str, lo_ns: int, hi_ns: int, window: bool = False):
    """(BarEvent のリスト, 異常の種類, 読んだファイルの一覧)。window=True は窓の口(window_guard)を通ったときだけ、
    終わりを WINDOW1 の終わりまで許す(読む前に記録へ 1 行足す)。既定は今までと同じ。"""
    from bot.bt.data.loader import load
    if window:
        window_guard(lo_ns, hi_ns, what=f"load_bars {d}")
    ds = bar_dataset(d, symbol, lo_ns, hi_ns, window=window)
    res = load(ROOT, [ds], explore_window=WINDOW1_UNIT if window else None)  # 窓の口の 2 つの門の後に、データ層の門(3 つ)
    kinds = {}
    for a in res.anomalies("bars"):
        kinds[a["kind"]] = kinds.get(a["kind"], 0) + 1
    bars = list(res.events("bars", BAR_RESOLVE))
    if window:  # 読んだ直後に、判定の期間の行を落とす(読み込み層の範囲で落ちているので 0 のはず。数は記録に残す)
        n_late = sum(1 for b in bars if int(b.start_time_ns) >= WINDOW1[1])
        bars = [b for b in bars if int(b.start_time_ns) < WINDOW1[1]]
        window_trim_report(ds["paths"], "ts", what=f"load_bars {d}", late_after_load=n_late)
    files = [f.__dict__ if hasattr(f, "__dict__") else str(f) for f in res.files()]
    return bars, kinds, res.hashes()


def _unused_sha256_file(path: str) -> str:  # 使わない(sha256 は門の manifest から取る)
    h = hashlib.sha256()
    with open(os.path.join(ROOT, path), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def peak_rss_gb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024


class Clock:
    def __init__(self) -> None:
        self.t0 = time.time()
        self.marks = []

    def mark(self, what: str) -> None:
        dt = time.time() - self.t0
        self.marks.append((what, round(dt, 1), round(peak_rss_gb(), 2)))
        print(f"[{dt:8.1f}s 最大RSS {peak_rss_gb():5.2f}GB] {what}", flush=True)
