"""K1 の足の**出所を切り替える**(`docs/PHASE2/K1/BINANCE_PLAN.md` §4.1)。

`bitmex` は `measure_katsuo_dispersion.load_seconds` を呼ぶだけ(秒バー。既定の挙動は変えない)。
`binance` は現物 BTCUSDT の 1 分足スナップショット 2 つを読む:

    backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_{2017..2023}.csv.gz
    backtest_data/binance_BTCUSDT_1m_20240101_20260831/binance_BTCUSDT_1m_20240101_20260831.csv.gz

**同条件にするための扱い**(設計書 §1):

- `open_time` を足の時刻(epoch 秒)とする。BitMEX の秒バーも区間の開始時刻
- BitMEX は「約定が 1 秒も無い足は行を作らない」ので、`n_trades == 0` の行は**落とす**
  (落とした件数は `last_load` に記録し、標準出力にも出す)
- 1 分足では `fold()` が恒等であること(1 分足の行数 = 読み込んだ行数 − 落とした行数、
  かつ各行が同じ)を assert する(設計書 §4.3)

測定スクリプトはここから `load_bars(source, start, end)` だけを呼び、それ以降の経路
(`fold` / `signals` / `simulate` / ブートストラップ)は出所に依らず同じものを通る。
"""
from __future__ import annotations

import csv
import gzip
import os
from datetime import date, datetime, timezone
from pathlib import Path

import measure_katsuo_dispersion as base

REPO = Path(__file__).resolve().parents[1]
K1 = REPO / "docs" / "PHASE2" / "K1"

# BitMEX の封印(`docs/PHASE2/K1/JUDGEMENT_PREREG.md` §1/§7)。判定区間 2020-2021 を
# 開けるには CLI の `--open-seal` と環境変数の**両方**が要る。開封は 1 回きり(L-085)
# なので承認の値もその L 行に固定する(以後この設計で封印は使わない)。
SEAL_END = date(2019, 12, 31)
SEAL_APPROVAL_ENV = "K1_SEAL_APPROVAL"
SEAL_APPROVAL_VALUE = "L-085"

BINANCE_FILES = (
    [REPO / "backtest_data" / "binance_BTCUSDT_1m_20170801_20231231" / f"binance_BTCUSDT_1m_{y}.csv.gz"
     for y in range(2017, 2024)]
    + [REPO / "backtest_data" / "binance_BTCUSDT_1m_20240101_20260831"
       / "binance_BTCUSDT_1m_20240101_20260831.csv.gz"]
)

# ソースごとの既定の期間と出力ディレクトリ。bitmex は従来どおり(探索区間 2017-2019、判定区間は封印)
SOURCES = {
    "bitmex": {"start": date(2017, 1, 1), "end": date(2019, 12, 31), "out_dir": K1},
    "binance": {"start": date(2017, 8, 17), "end": date(2026, 8, 31), "out_dir": K1 / "binance"},
}

# 直近の読み込みの事実(行数・落とした件数)。報告用
last_load: dict = {}


def default_start(source: str) -> date:
    return SOURCES[source]["start"]


def default_end(source: str) -> date:
    return SOURCES[source]["end"]


def out_dir(source: str) -> Path:
    """出力ディレクトリ。`binance` は無ければ作る。`bitmex` は従来の場所そのまま。"""
    d = SOURCES[source]["out_dir"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def add_source_args(ap) -> None:
    """5 本の測定スクリプトで共通の引数。既定は `bitmex`(従来どおり)。"""
    ap.add_argument("--source", choices=sorted(SOURCES), default="bitmex")
    ap.add_argument("--start", type=date.fromisoformat, default=None,
                    help="足の開始日(UTC)。既定はソースごと")
    ap.add_argument("--end", type=date.fromisoformat, default=None,
                    help="足の終了日(UTC、含む)。既定はソースごと")
    ap.add_argument("--open-seal", action="store_true",
                    help="BitMEX の封印(判定区間 2020-2021)を開ける。環境変数 "
                         f"{SEAL_APPROVAL_ENV}={SEAL_APPROVAL_VALUE} も要る"
                         "(docs/PHASE2/K1/JUDGEMENT_PREREG.md §1/§7)。開封は 1 回きり")


def resolve_range(args) -> tuple[date, date]:
    start = args.start if args.start is not None else default_start(args.source)
    end = args.end if args.end is not None else default_end(args.source)
    if args.source == "bitmex" and end > SEAL_END:
        opened = (getattr(args, "open_seal", False)
                  and os.environ.get(SEAL_APPROVAL_ENV) == SEAL_APPROVAL_VALUE)
        assert opened, (
            f"BitMEX の封印: end は {SEAL_END} 以下でなければならない({end} が渡された)。"
            f"開けるには --open-seal と環境変数 {SEAL_APPROVAL_ENV}={SEAL_APPROVAL_VALUE} の"
            "両方が要る(docs/PHASE2/K1/JUDGEMENT_PREREG.md §1/§7)"
        )
    return start, end


def load_binance_minutes(start: date, end: date):
    """Binance 1 分足を (epoch秒, o, h, l, c) で返す。`n_trades == 0` の行は落とす。

    戻り値は (rows, n_read, n_dropped)。`n_read` は期間内の行数(落とす前)。
    """
    lo = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp())
    hi = int(datetime(end.year, end.month, end.day, tzinfo=timezone.utc).timestamp()) + 86400
    rows = []
    n_read = n_dropped = 0
    for path in BINANCE_FILES:
        if not path.exists():
            continue
        with gzip.open(path, "rt", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader, None)
            assert header is not None and header[:5] == ["open_time", "open", "high", "low", "close"], (path, header)
            assert header[7] == "n_trades", (path, header)
            for r in reader:
                ts = int(datetime.fromisoformat(r[0]).timestamp())
                if ts < lo or ts >= hi:
                    continue
                n_read += 1
                if int(r[7]) == 0:
                    n_dropped += 1
                    continue
                rows.append((ts, float(r[1]), float(r[2]), float(r[3]), float(r[4])))
    rows.sort(key=lambda x: x[0])
    return rows, n_read, n_dropped


def load_bars(source: str, start: date, end: date):
    """出所を切り替えて足の列 [(ts, o, h, l, c), ...] を返す。`fold()` にそのまま渡せる。"""
    global last_load
    if source == "bitmex":
        rows = base.load_seconds(start, end)
        last_load = {"source": source, "rows": len(rows)}
        return rows
    if source == "binance":
        rows, n_read, n_dropped = load_binance_minutes(start, end)
        # 1 分足では fold() が恒等(設計書 §4.3: 1 分足の行数 = 読み込んだ行数 − 落とした行数)。
        # 加えて各行の o/h/l/c が同じであることも確かめる。時刻は `fold()` が分の頭に切り下げるので、
        # `open_time` が分の境界に乗っていない行(実測で存在する)は時刻ラベルだけが動く。件数を記録する
        bars1 = base.fold(rows, 1)
        assert len(bars1) == len(rows) == n_read - n_dropped, (len(bars1), len(rows), n_read, n_dropped)
        assert all(a[1:] == b[1:] for a, b in zip(rows, bars1)), "1 分足の fold() で o/h/l/c が変わった"
        off_minute = sum(1 for r in rows if r[0] % 60 != 0)
        last_load = {"source": source, "rows": len(rows), "rows_read": n_read,
                     "dropped_n_trades_0": n_dropped, "open_time_off_minute": off_minute}
        print(f"  Binance 分足 {n_read:,} 行のうち n_trades==0 を {n_dropped:,} 行落とし {len(rows):,} 行"
              f"(1 分足の fold() は行数・o/h/l/c とも恒等。open_time が分の境界に無い行 {off_minute:,})")
        return rows
    raise ValueError(source)
