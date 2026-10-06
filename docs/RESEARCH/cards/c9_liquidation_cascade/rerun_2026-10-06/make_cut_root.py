#!/usr/bin/env python3
"""カード 9 の走らせ直し(2026-10-06): 封印の境より後のファイルを含まない読み口(リンクの置き場)を作る。

委任文: `docs/DISCUSSIONS/2026-10-06_held_batches/DELEGATION_rerun_impl.md`(「2023-12-17T15:00Z より後の
足 … を読むこと(grep・ls を含む)」はしない)。`scripts/c9_run_a.py` は `--end` の後も読む
(清算は `--end` + 4 日、約定は日ごとに + 11 日、資金調達率は置き場の月次 zip を**全部**
`load_funding_all`)。そこで `--data-root` に、境より前のファイルへのリンクだけを置いた置き場を渡す。

- 日ごとのファイル(`aggTrades`・`liquidationSnapshot`・`metrics`): `--first-day`〜`--last-day` の日付から
  名前を組み立て、元にあるものだけリンクする(元の置き場を一覧しない)。
- 資金調達率(月次): 月の最後の日が `--last-day` 以前の月だけリンクする(境の月は 1 か月まるごと
  入れない。その月のプリントの材料 10 は前の月の最後の値になる)。
- 日の zip は UTC の 0〜24 時。境 2023-12-17T15:00Z を越えない最後の日まるごとのファイルは
  2023-12-16(既定の `--last-day`)。

    python3 docs/RESEARCH/cards/c9_liquidation_cascade/rerun_2026-10-06/make_cut_root.py \
        --dst data/c9_run_a/cut_root_20231216
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
SYMBOL = "BTCUSD_PERP"
DAILY_KINDS = ("aggTrades", "liquidationSnapshot", "metrics")
SEAL_LAST_FULL_DAY = date(2023, 12, 16)


def month_iter(first: date, last: date):
    y, m = first.year, first.month
    while (y, m) <= (last.year, last.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def month_last_day(y: int, m: int) -> date:
    return (date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)) - timedelta(days=1)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=str(REPO_ROOT / "backtest_data" / "binance_cm_o3c_20260913"))
    ap.add_argument("--dst", required=True)
    ap.add_argument("--first-day", default="2023-01-01")
    ap.add_argument("--last-day", default=SEAL_LAST_FULL_DAY.isoformat())
    args = ap.parse_args(argv)
    src, dst = Path(args.src).resolve(), Path(args.dst)
    first, last = date.fromisoformat(args.first_day), date.fromisoformat(args.last_day)
    if last > SEAL_LAST_FULL_DAY:
        raise SystemExit(f"[止め] --last-day {last} は境(2023-12-17T15:00Z)を越える日のファイルを含む")
    if dst.exists() and any(dst.iterdir()):
        raise SystemExit(f"[止め] 置き場が空でない: {dst}")
    counts = {}
    for kind in DAILY_KINDS:
        n = 0
        d = first
        while d <= last:
            name = f"{SYMBOL}-{kind}-{d.isoformat()}.zip"
            s = src / kind / SYMBOL / name
            if s.exists():
                t = dst / kind / SYMBOL / name
                t.parent.mkdir(parents=True, exist_ok=True)
                t.symlink_to(s)
                n += 1
            d += timedelta(days=1)
        counts[kind] = n
    n = 0
    for y, m in month_iter(first, last):
        if month_last_day(y, m) > last:
            continue
        name = f"{SYMBOL}-fundingRate-{y:04d}-{m:02d}.zip"
        s = src / "fundingRate" / SYMBOL / name
        if s.exists():
            t = dst / "fundingRate" / SYMBOL / name
            t.parent.mkdir(parents=True, exist_ok=True)
            t.symlink_to(s)
            n += 1
    counts["fundingRate(月)"] = n
    meta = {"src": str(src), "first_day": first.isoformat(), "last_day": last.isoformat(),
            "リンクの数": counts}
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "cut_root_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
