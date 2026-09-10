"""K1 フレッシュ確認 — bitFlyer データ検査(`FRESH_BITFLYER_PREREG.md` §1 の表、最終行)。

年ごとに: 分の本数(実在 / 期待)・欠測の割合・古い終値(前分と同じ終値)の割合・
出来高 0 の分の割合・高値<安値または始値/終値がヒゲの外の件数・
1 分の |リターン| > 1,000 bp の件数・門 `s19/b24` の通過率(5 分・15 分)。

**閾値(事前登録どおり、先に決める)**: 古い終値 > 10% または欠測 > 5% の年は
`excluded_from_reading: true` を立てる(表には出すが読みからは外す)。

`--source` で切り替え可能(既定 `bitflyer`、後方互換で出力名も不変)。段階 2(`XVENUE_PREREG.md`)
用に `--source bybit` を追加(同じ閾値、出力は `xvenue/bybit_data_check.json`)。

    PYTHONPATH=src:scripts python scripts/check_k1_bitflyer_data.py
    PYTHONPATH=src:scripts python scripts/check_k1_bitflyer_data.py --source bybit
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

import k1_source
import measure_katsuo_dispersion as base
import measure_katsuo_effect as eff

REPO = Path(__file__).resolve().parents[1]

YEARS = list(range(2017, 2027))
GATE_NAME = "s19/b24"
SMALL, BIG = 19.0, 24.0
FEET = (5, 15)

STALE_THRESHOLD = 0.10
MISSING_THRESHOLD = 0.05


def minutes_expected(year: int, start: date, end: date) -> int:
    """年 `year` について、読み込み範囲(`start`〜`end`、両端を含む)に入る分数。

    範囲の開始・終了がその年の途中で切れる年(開始年・終了年)は期待値もそれに合わせる。
    """
    from datetime import timedelta
    lo = datetime(start.year, start.month, start.day, tzinfo=timezone.utc) if start.year == year \
        else datetime(year, 1, 1, tzinfo=timezone.utc)
    hi = datetime(end.year, end.month, end.day, tzinfo=timezone.utc) + timedelta(days=1) if end.year == year \
        else datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    return int((hi - lo).total_seconds() // 60)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", choices=sorted(k1_source.SOURCES), default="bitflyer")
    ap.add_argument("--start", type=date.fromisoformat, default=None)
    ap.add_argument("--end", type=date.fromisoformat, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    start = args.start if args.start is not None else k1_source.default_start(args.source)
    end = args.end if args.end is not None else k1_source.default_end(args.source)
    args.start, args.end = start, end
    if args.out is None:
        out_name = "data_check.json" if args.source == "bitflyer" else f"{args.source}_data_check.json"
        args.out = str(k1_source.out_dir(args.source) / out_name)

    rows = k1_source.load_bars(args.source, args.start, args.end)
    load_meta = dict(k1_source.last_load)
    print(f"読み込み {args.start} 〜 {args.end}: {len(rows):,} 行({args.source})")

    bars_by_foot = {ft: base.fold(rows, ft) for ft in FEET}
    sigs_by_foot = {ft: eff.signals(bars_by_foot[ft], SMALL, BIG) for ft in FEET}

    per_year: dict[str, dict] = {}
    for year in YEARS:
        if year < args.start.year or year > args.end.year:
            continue
        y_rows = [r for r in rows if datetime.fromtimestamp(r[0], tz=timezone.utc).year == year]
        n_present = len(y_rows)
        expected = minutes_expected(year, args.start, args.end)
        missing_share = round(1 - n_present / expected, 4) if expected else None

        stale = 0
        zero_vol = 0
        ohlc_bad = 0
        extreme = 0
        prev_close = None
        for ts, o, h, l, c in y_rows:
            if h < l or o > h or o < l or c > h or c < l:
                ohlc_bad += 1
            if prev_close is not None:
                if c == prev_close:
                    stale += 1
                if prev_close > 0:
                    ret_bp = abs((c / prev_close - 1.0) * 1e4)
                    if ret_bp > 1000:
                        extreme += 1
            prev_close = c
        n_comp = max(n_present - 1, 0)
        stale_share = round(stale / n_comp, 4) if n_comp else None
        zero_vol_share = None  # 出来高列は k1_source.load_bars が返す (ts,o,h,l,c) に含まれない(層 ④ 相当。判定不能)

        gate_pass = {}
        for ft in FEET:
            sg = sigs_by_foot[ft]
            bts = bars_by_foot[ft]
            idx = [i for i, b in enumerate(bts) if datetime.fromtimestamp(b[0], tz=timezone.utc).year == year]
            n_ft = len(idx)
            n_sig = sum(1 for i in idx if sg[i][0] != 0)
            gate_pass[str(ft)] = {
                "n_bars": n_ft,
                "n_signal": n_sig,
                "pass_rate": round(n_sig / n_ft, 4) if n_ft else None,
            }

        excluded = bool(
            (stale_share is not None and stale_share > STALE_THRESHOLD)
            or (missing_share is not None and missing_share > MISSING_THRESHOLD)
        )

        per_year[str(year)] = {
            "minutes_present": n_present,
            "minutes_expected": expected,
            "missing_share": missing_share,
            "stale_close_share": stale_share,
            "zero_volume_share": zero_vol_share,
            "ohlc_inconsistent_count": ohlc_bad,
            "extreme_return_gt_1000bp_count": extreme,
            "gate_s19_b24_pass_rate": gate_pass,
            "excluded_from_reading": excluded,
        }
        print(f"  {year}: 実在 {n_present:,}/{expected:,} (欠測 {missing_share:.2%})"
              f" / 古い終値 {stale_share:.2%} / OHLC不整合 {ohlc_bad} / |r|>1000bp {extreme}"
              f" / 除外={excluded}")

    result = {
        "note": (f"{args.source} 1 分足のデータ検査(FRESH_BITFLYER_PREREG.md §1 と同じ閾値・列。"
                 "bybit は XVENUE_PREREG.md §2 段階 2、L-095)。"
                 "閾値: 古い終値 > 10% または欠測 > 5% の年は excluded_from_reading=true。"
                 "zero_volume_share は k1_source.load_bars が volume 列を返さないため判定不能(null)。"),
        "source": args.source,
        "range": [args.start.isoformat(), args.end.isoformat()],
        "thresholds": {"stale_close_share_gt": STALE_THRESHOLD, "missing_share_gt": MISSING_THRESHOLD},
        "gate": GATE_NAME,
        "load": load_meta,
        "per_year": per_year,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n→ {out_path}")


if __name__ == "__main__":
    main()
