"""Binance 現物 BTCUSDT 1 分足の**データ品質の事実**を集める(`docs/PHASE2/K1/BINANCE_PLAN.md` §1)。

合否は出さない。出すのは:

- 行数(読み込んだ行数 / `n_trades == 0` の行数 / 残った行数)
- 重複時刻の件数、時刻の逆転(ファイル順で前の行より時刻が戻る)の件数
- `o = h = l = c` の行数(落とす前 / 落とした後)
- `open_time` が分の境界(60 秒の倍数)に乗っていない行数と、そのオフセットの内訳・日付範囲
- 1 分を超える欠落(落とした後の連続する行の間隔が 60 秒を超えるもの)の件数・最大長・上位 10 件(日付つき)
- 年ごとの行数(落とす前 / 落とした後 / 落とした件数)

読み込みは `k1_source.load_binance_minutes` と同じ経路(同じ CSV、同じ時刻変換)。

    PYTHONPATH=src:scripts python scripts/k1_binance_data_quality.py
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

import k1_source

REPO = Path(__file__).resolve().parents[1]


def utc(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", type=date.fromisoformat, default=k1_source.default_start("binance"))
    ap.add_argument("--end", type=date.fromisoformat, default=k1_source.default_end("binance"))
    ap.add_argument("--out", default=str(k1_source.out_dir("binance") / "data_quality.json"))
    args = ap.parse_args()

    lo = int(datetime(args.start.year, args.start.month, args.start.day, tzinfo=timezone.utc).timestamp())
    hi = int(datetime(args.end.year, args.end.month, args.end.day, tzinfo=timezone.utc).timestamp()) + 86400

    per_file = []
    n_read = n_zero = n_flat_all = n_flat_kept = 0
    reversals = 0
    per_year_read: Counter = Counter()
    per_year_zero: Counter = Counter()
    ts_all = []              # 落とす前の時刻(重複・逆転の検査)
    kept = []                # 落とした後の (ts) だけ
    off_minute: Counter = Counter()
    off_first = off_last = None
    off_per_year: Counter = Counter()
    prev_ts = None
    for path in k1_source.BINANCE_FILES:
        if not path.exists():
            per_file.append({"file": str(path.relative_to(REPO)), "exists": False})
            continue
        n_file = 0
        first = last = None
        with gzip.open(path, "rt", newline="") as fh:
            reader = csv.reader(fh)
            next(reader, None)
            for r in reader:
                ts = int(datetime.fromisoformat(r[0]).timestamp())
                if ts < lo or ts >= hi:
                    continue
                n_file += 1
                n_read += 1
                first = ts if first is None else first
                last = ts
                if prev_ts is not None and ts < prev_ts:
                    reversals += 1
                prev_ts = ts
                ts_all.append(ts)
                y = datetime.fromtimestamp(ts, tz=timezone.utc).year
                per_year_read[y] += 1
                o, h, l, c = float(r[1]), float(r[2]), float(r[3]), float(r[4])
                flat = o == h == l == c
                n_flat_all += flat
                if ts % 60 != 0:
                    off_minute[ts % 60] += 1
                    off_per_year[y] += 1
                    off_first = ts if off_first is None else off_first
                    off_last = ts
                if int(r[7]) == 0:
                    n_zero += 1
                    per_year_zero[y] += 1
                    continue
                n_flat_kept += flat
                kept.append(ts)
        per_file.append({"file": str(path.relative_to(REPO)), "exists": True, "rows_in_range": n_file,
                         "first": utc(first) if first is not None else None,
                         "last": utc(last) if last is not None else None})

    dup = Counter(ts_all)
    dup_ts = sorted(t for t, k in dup.items() if k > 1)
    kept.sort()

    def find_gaps(series):
        out = []
        for a, b in zip(series, series[1:]):
            if b - a > 60:
                out.append((b - a, a, b))
        out.sort(key=lambda g: (-g[0], g[1]))
        per_year: Counter = Counter()
        for _g, a, _b in out:
            per_year[datetime.fromtimestamp(a, tz=timezone.utc).year] += 1
        return out, per_year

    # 落とす前(= CSV に行そのものが無い欠落)と、落とした後(= 測定に入る足の列の欠落)の両方
    raw_sorted = sorted(set(ts_all))
    gaps_raw, gap_raw_per_year = find_gaps(raw_sorted)
    gaps, gap_per_year = find_gaps(kept)

    years = sorted(per_year_read)
    payload = {
        "note": "Binance 現物 BTCUSDT 1 分足のデータ品質の事実。合否ではない。",
        "range": [args.start.isoformat(), args.end.isoformat()],
        "files": per_file,
        "rows_read": n_read,
        "rows_n_trades_0": n_zero,
        "rows_kept": n_read - n_zero,
        "duplicate_timestamps": {"count": len(dup_ts),
                                 "examples": [utc(t) for t in dup_ts[:10]]},
        "time_reversals_in_file_order": reversals,
        "flat_ohlc_rows": {"before_drop": n_flat_all, "after_drop": n_flat_kept},
        "open_time_off_minute": {
            "count": sum(off_minute.values()),
            "offsets_sec": {str(k): v for k, v in sorted(off_minute.items())},
            "first": utc(off_first) if off_first is not None else None,
            "last": utc(off_last) if off_last is not None else None,
            "per_year": {str(y): off_per_year.get(y, 0) for y in years},
        },
        "gaps_over_1min_before_drop": {
            "count": len(gaps_raw),
            "max_sec": gaps_raw[0][0] if gaps_raw else 0,
            "per_year": {str(y): gap_raw_per_year.get(y, 0) for y in years},
            "top10": [{"gap_sec": g, "gap_min": round(g / 60, 1), "from": utc(a), "to": utc(b)}
                      for g, a, b in gaps_raw[:10]],
        },
        "gaps_over_1min_after_drop": {
            "count": len(gaps),
            "max_sec": gaps[0][0] if gaps else 0,
            "per_year": {str(y): gap_per_year.get(y, 0) for y in years},
            "top10": [{"gap_sec": g, "gap_min": round(g / 60, 1), "from": utc(a), "to": utc(b)}
                      for g, a, b in gaps[:10]],
        },
        "per_year": {str(y): {"read": per_year_read[y], "n_trades_0": per_year_zero.get(y, 0),
                              "kept": per_year_read[y] - per_year_zero.get(y, 0)} for y in years},
    }
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"範囲 {args.start} 〜 {args.end}")
    print(f"読み込み {n_read:,} 行 / n_trades==0 {n_zero:,} 行 / 残り {n_read - n_zero:,} 行")
    print(f"重複時刻 {len(dup_ts)} 件 / 時刻の逆転 {reversals} 件")
    print(f"o=h=l=c 落とす前 {n_flat_all:,} / 落とした後 {n_flat_kept:,}")
    print(f"open_time が分の境界に無い行 {sum(off_minute.values()):,} 件 オフセット {dict(sorted(off_minute.items()))}"
          f" 期間 {payload['open_time_off_minute']['first']} 〜 {payload['open_time_off_minute']['last']}")
    for name, key in (("落とす前", "gaps_over_1min_before_drop"), ("落とした後", "gaps_over_1min_after_drop")):
        gp = payload[key]
        print(f"1 分超の欠落({name}) {gp['count']} 件 最大 {gp['max_sec']} 秒 年ごと {gp['per_year']}")
        for g in gp["top10"]:
            print(f"  {g['gap_sec']:>8} 秒 ({g['gap_min']:>8.1f} 分) {g['from']} → {g['to']}")
    print("年ごと(読み込み / n_trades==0 / 残り):")
    for y in years:
        p = payload["per_year"][str(y)]
        print(f"  {y}: {p['read']:,} / {p['n_trades_0']:,} / {p['kept']:,}")
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
