"""K1 取引所横断 段階 2 — Bybit BTCUSDT 無期限 1 分足の取得(`XVENUE_PREREG.md` §2 段階 2)。

出力: backtest_data/bybit_BTCUSDT_1m_20260910/bybit_BTCUSDT_1m_{year}.csv.gz
      (列 ts,open,high,low,close。ts は UTC epoch 秒、分の頭に揃っている)

2022〜2024: `kline_for_metatrader4` アーカイブ(1 分足、月次ファイル)を使う。
2025〜2026-08: `trading/BTCUSDT/` の日次約定ファイルをダウンロードし、
    UTC の壁時計の分に畳む(open=その分の最初の約定・high/low=最大/最小・close=最後の約定。
    約定の無い分は行を作らない = 他ソースと同じ扱い)。日次ファイルは畳んだら即削除する
    (ディスクの書き込み枠が固定のため)。

**タイムスタンプの基準(実測)**: `kline_for_metatrader4` のタイムスタンプは
**UTC+3(ブローカー/サーバー時間)**。2024-12-31 の約定ファイルを畳んだ分足と
2024-12 の kline ファイルの同日を突き合わせ、UTC+3 時間シフトで
H/L/C が 0.5 USDT 以内で 1239/1261 分一致(重なる分のうち 98.3%。残差は
浮動小数の丸め・trade 順序のタイブレークとみられる小さな差)。offset 0h(UTC のまま)
では 0/1440 一致。よって kline 側は読み込み時に **-3 時間**して UTC に補正する
(`KLINE_UTC_OFFSET_HOURS = -3`、`correct_kline_timestamp()`)。

再試行: 一時的な失敗(タイムアウト・5xx・接続エラー)は最大 4 回、指数バックオフ(2,4,8,16 秒)。
プロキシはそのまま使う(TLS 無効化・HTTPS_PROXY 解除はしない)。

    PYTHONPATH=scripts python scripts/fetch_bybit_minutes.py --years 2022 2023 2024   # kline
    PYTHONPATH=scripts python scripts/fetch_bybit_minutes.py --trade-days 2025-01-01 2026-08-31
    PYTHONPATH=scripts python scripts/fetch_bybit_minutes.py --offset-check   # 2024-12-31 突き合わせのみ
"""
from __future__ import annotations

import argparse
import csv
import gzip
import http.client
import io
import json
import socket
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "backtest_data" / "bybit_BTCUSDT_1m_20260910"

KLINE_URL = "https://public.bybit.com/kline_for_metatrader4/BTCUSDT/{year}/BTCUSDT_1_{start}_{end}.csv.gz"
TRADE_URL = "https://public.bybit.com/trading/BTCUSDT/BTCUSDT{day}.csv.gz"

KLINE_YEARS = (2022, 2023, 2024)
TRADE_START = date(2025, 1, 1)
TRADE_END = date(2026, 8, 31)

# 実測(本ファイル docstring 参照): kline のタイムスタンプは UTC+3。UTC に戻すには -3h
KLINE_UTC_OFFSET_HOURS = -3

MAX_RETRIES = 4
BACKOFF_BASE = 2  # 秒: 2, 4, 8, 16


def _month_range(year: int):
    for m in range(1, 13):
        start = date(year, m, 1)
        end = date(year, m + 1, 1) - timedelta(days=1) if m < 12 else date(year, 12, 31)
        yield start, end


# 一時的失敗として再試行する例外(ネットワーク・プロキシ・切断のみ。プログラムの誤りは再試行しない)。
# `http.client.IncompleteRead`(実際に発生: Content-Length 分読めずに切れる)を含む
TRANSIENT_EXC = (
    urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionError,
    http.client.IncompleteRead, http.client.HTTPException, socket.timeout, OSError,
)


def fetch_bytes(url: str) -> bytes:
    """GET url、一時的失敗は最大 MAX_RETRIES 回・指数バックオフで再試行する。"""
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                return resp.read()
        except TRANSIENT_EXC as exc:
            last_exc = exc
            if attempt == MAX_RETRIES - 1:
                break
            wait = BACKOFF_BASE * (2 ** attempt)
            print(f"    再試行 {attempt + 1}/{MAX_RETRIES}({exc!r}): {wait}s 待機")
            time.sleep(wait)
    raise RuntimeError(f"取得失敗(4 回再試行後): {url}: {last_exc!r}")


def correct_kline_timestamp(dt_naive: datetime) -> int:
    """kline の `YYYY.MM.DD HH:MM` をブローカー時間とみなし UTC epoch 秒に補正する。"""
    dt_utc = dt_naive.replace(tzinfo=timezone.utc) + timedelta(hours=KLINE_UTC_OFFSET_HOURS)
    return int(dt_utc.timestamp())


def parse_kline_csv(raw: bytes):
    """kline の gzip CSV(ヘッダ無し、`YYYY.MM.DD HH:MM,o,h,l,c,v`)を
    (ts_utc, o, h, l, c) の列に変換する(補正込み)。
    """
    rows = []
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
        text = io.TextIOWrapper(gz, encoding="utf-8", newline="")
        for line in text:
            line = line.strip()
            if not line:
                continue
            ts_str, o, h, l, c, _v = line.split(",")
            dt_naive = datetime.strptime(ts_str, "%Y.%m.%d %H:%M")
            ts = correct_kline_timestamp(dt_naive)
            rows.append((ts, float(o), float(h), float(l), float(c)))
    return rows


def fold_trades_to_minutes(trades):
    """約定列 [(ts_epoch_float_or_int, price), ...] を UTC の壁時計の分に畳む。

    open = その分で最初に現れた約定の価格、high/low = 最大/最小、close = 最後に現れた約定の価格。
    約定の無い分は出力に現れない。入力の順序(タイムスタンプ昇順、同一タイムスタンプはファイル内の
    出現順)をそのまま「最初/最後」の基準にする(安定ソートで壊さない)。
    戻り値: [(minute_ts, o, h, l, c), ...](minute_ts 昇順、分の頭 = ts // 60 * 60)。
    """
    bars: dict[int, list] = {}
    order: list[int] = []
    for ts, price in trades:
        minute = int(ts // 60) * 60
        if minute not in bars:
            bars[minute] = [price, price, price, price]  # o, h, l, c
            order.append(minute)
        else:
            b = bars[minute]
            if price > b[1]:
                b[1] = price
            if price < b[2]:
                b[2] = price
            b[3] = price
    return [(m, *bars[m]) for m in sorted(set(order))]


def parse_trade_csv(raw: bytes):
    """日次約定 gzip CSV(ヘッダ有り、`timestamp,symbol,side,size,price,...`)を
    [(ts_float, price), ...](ファイル内の出現順そのまま)で返す。
    """
    out = []
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
        text = io.TextIOWrapper(gz, encoding="utf-8", newline="")
        reader = csv.reader(text)
        header = next(reader)
        idx_ts = header.index("timestamp")
        idx_price = header.index("price")
        for row in reader:
            if not row:
                continue
            out.append((float(row[idx_ts]), float(row[idx_price])))
    return out


def write_year_csv(year: int, rows):
    """(ts, o, h, l, c) の列を年別 gz CSV に書く(ts 昇順・重複無しを保証)。"""
    rows = sorted(rows, key=lambda r: r[0])
    deduped = []
    seen = set()
    for r in rows:
        if r[0] in seen:
            continue
        seen.add(r[0])
        deduped.append(r)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"bybit_BTCUSDT_1m_{year}.csv.gz"
    with gzip.open(path, "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ts", "open", "high", "low", "close"])
        for ts, o, h, l, c in deduped:
            w.writerow([ts, o, h, l, c])
    print(f"  → {path}({len(deduped):,} 行)")
    return path, len(deduped)


def fetch_kline_years(years):
    """複数年の kline を取得して UTC 年別に書き出す。

    **月次ファイルは月境界で 1 分重複する**(実測: 前月ファイルの最終行 = 翌月ファイルの
    先頭行、同じブローカー時刻・同じ OHLC)。さらに **UTC-3 補正で年境界も動く**(ブローカー
    時刻 `YYYY+1.01.01 00:00`〜`00:02` は補正後 UTC `YYYY.12.31 21:00`〜`23:59` になるので、
    そのままだと「取得した年」と「UTC 上の年」がずれて別々の年ファイルに同じ分が入り、
    年をまとめて読むと重複行になる。よって **全年をまとめて集めてから ts で重複排除し、
    補正後の UTC 年でファイルを分ける**(取得年ではなく)。
    """
    all_rows = []
    for year in years:
        print(f"kline {year}: 月次 12 本を取得")
        for start, end in _month_range(year):
            url = KLINE_URL.format(year=year, start=start.isoformat(), end=end.isoformat())
            raw = fetch_bytes(url)
            month_rows = parse_kline_csv(raw)
            all_rows.extend(month_rows)
            print(f"    {start}〜{end}: {len(month_rows):,} 行")
    dedup = {r[0]: r for r in all_rows}  # 同一 ts の重複行は内容が同一(月境界の実測どおり)
    by_year: dict[int, list] = {}
    for r in dedup.values():
        y = datetime.fromtimestamp(r[0], tz=timezone.utc).year
        by_year.setdefault(y, []).append(r)
    n_dup = len(all_rows) - len(dedup)
    print(f"  取得 {len(all_rows):,} 行、重複排除後 {len(dedup):,} 行(月/年境界の重複 {n_dup:,} 件)")
    for y in sorted(by_year):
        write_year_csv(y, by_year[y])


CHECKPOINT_PATH = Path(
    "/tmp/claude-0/-home-user-trade/fa7bf0d4-a5c4-55b7-991b-874b590e00a3/scratchpad/bybit_fetch_checkpoint.json"
)
FLUSH_EVERY_DAYS = 15  # この日数ごとに年別ファイルへ書き出す(クラッシュ時の再処理を上限する)


def _load_checkpoint() -> set[str]:
    if CHECKPOINT_PATH.exists():
        return set(json.loads(CHECKPOINT_PATH.read_text("utf-8")).get("completed_days", []))
    return set()


def _save_checkpoint(completed_days: set[str]) -> None:
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(json.dumps({"completed_days": sorted(completed_days)}), encoding="utf-8")


def fetch_trade_days(start: date, end: date):
    """2025〜2026 の日次約定ファイルを 1 日ずつ取得→分に畳む→即削除。年別に集計して書く。

    **再開可能**: `FLUSH_EVERY_DAYS` 日ごと(・年境界・末尾)に年別ファイルへ書き出し、
    書き出した日付をチェックポイント(`CHECKPOINT_PATH`、リポジトリ外)に記録する。
    一時的失敗が 4 回の再試行後も続いた場合(`fetch_bytes` が例外を投げる)は、その時点までの
    チェックポイント済みの日は失われない。再実行時はチェックポイント済みの日を自動でスキップする。
    """
    completed = _load_checkpoint()
    skipped = 0
    by_year: dict[int, list] = {}
    pending_days: set[str] = set()
    day = start
    n_days = (end - start).days + 1
    i = 0
    n_since_flush = 0

    def flush(reason: str):
        nonlocal by_year, pending_days, n_since_flush
        if not by_year:
            return
        for y, rows in by_year.items():
            _merge_and_write_year(y, rows)
        completed.update(pending_days)
        _save_checkpoint(completed)
        print(f"  [checkpoint:{reason}] {len(pending_days)} 日分を書き出し・記録"
              f"(チェックポイント合計 {len(completed):,} 日)")
        by_year = {}
        pending_days = set()
        n_since_flush = 0

    while day <= end:
        i += 1
        if day.isoformat() in completed:
            skipped += 1
            day += timedelta(days=1)
            continue
        url = TRADE_URL.format(day=day.isoformat())
        print(f"trade {day}({i}/{n_days}): 取得")
        raw = fetch_bytes(url)
        trades = parse_trade_csv(raw)
        bars = fold_trades_to_minutes(trades)
        by_year.setdefault(day.year, []).extend(bars)
        pending_days.add(day.isoformat())
        n_since_flush += 1
        print(f"    約定 {len(trades):,} 件 → 分 {len(bars):,} 本")
        del raw, trades
        next_day = day + timedelta(days=1)
        year_boundary = next_day.year != day.year
        if n_since_flush >= FLUSH_EVERY_DAYS or year_boundary or next_day > end:
            flush("年境界" if year_boundary else ("末尾" if next_day > end else f"{FLUSH_EVERY_DAYS}日ごと"))
        day = next_day
    if skipped:
        print(f"  再開: チェックポイント済み {skipped:,} 日をスキップ")


def _merge_and_write_year(year: int, new_rows):
    """既存の年別ファイル(あれば)に追記して書き直す(複数回に分けて実行しても安全)。"""
    existing = []
    path = OUT_DIR / f"bybit_BTCUSDT_1m_{year}.csv.gz"
    if path.exists():
        with gzip.open(path, "rt", newline="") as fh:
            reader = csv.reader(fh)
            next(reader, None)
            for r in reader:
                existing.append((int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4])))
    write_year_csv(year, existing + new_rows)


def offset_check():
    """2024-12-31 の約定ファイルを畳み、同日の kline(2024-12 月次)と比較して offset を報告する。"""
    print("offset 確認: 2024-12-31 の約定ファイル + 2024-12 kline を突き合わせ")
    trade_raw = fetch_bytes(TRADE_URL.format(day="2024-12-31"))
    trades = parse_trade_csv(trade_raw)
    bars = fold_trades_to_minutes(trades)
    bars_by_min = {b[0]: b[1:] for b in bars}

    kline_start, kline_end = date(2024, 12, 1), date(2024, 12, 31)
    kline_raw = fetch_bytes(KLINE_URL.format(year=2024, start=kline_start.isoformat(), end=kline_end.isoformat()))
    kline_rows = parse_kline_csv(kline_raw)  # 補正済み(-3h)
    kline_by_min = {r[0]: r[1:] for r in kline_rows
                    if date(2024, 12, 31) <= datetime.fromtimestamp(r[0], tz=timezone.utc).date() <= date(2024, 12, 31)}

    common = sorted(set(bars_by_min) & set(kline_by_min))
    matches = sum(
        1 for m in common
        if all(abs(kline_by_min[m][i] - bars_by_min[m][i]) < 0.5 for i in (1, 2, 3))  # h, l, c
    )
    print(f"  補正後(-3h)一致: {matches}/{len(common)} 分(H/L/C を 0.5 USDT 以内で比較)")
    return matches, len(common)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--years", type=int, nargs="*", default=None, help="kline を取得する年(既定 2022 2023 2024)")
    ap.add_argument("--trade-days", nargs=2, metavar=("START", "END"), default=None,
                     help="約定ファイルを畳む範囲(YYYY-MM-DD YYYY-MM-DD)")
    ap.add_argument("--offset-check", action="store_true", help="2024-12-31 の突き合わせのみ実行")
    args = ap.parse_args()

    if args.offset_check:
        offset_check()
        return

    if args.years is not None:
        fetch_kline_years(args.years)

    if args.trade_days is not None:
        start = date.fromisoformat(args.trade_days[0])
        end = date.fromisoformat(args.trade_days[1])
        fetch_trade_days(start, end)

    if args.years is None and args.trade_days is None:
        fetch_kline_years(list(KLINE_YEARS))
        fetch_trade_days(TRADE_START, TRADE_END)


if __name__ == "__main__":
    main()
