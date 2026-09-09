"""K1 の**検出力の材料だけ**を測る(効果の大きさは見ない)。

事前登録 `docs/PHASE2/K1/PREREG.md` §5.2 は MDE の基礎に `sd_trade`(1 取引の
符号付きリターンのばらつき)を使う。規約 §4.1 は「**MDE を書いていない事前登録は
実行しない**」と決めているので、**族の全水準で `sd_trade` が要る**。

ところが事前登録の表は 6 水準のうち 5 / 15 / 60 分の 3 つしか埋まっていなかった。
その 3 つを選んだ理由は「保有が固定でないことを論証するのに桁の違う 3 点が要った」
だけで、**論証の都合であって仮説から出た選択ではない**(オーナー指摘 2026-09-09、L-049)。
本スクリプトは残る 1 / 3 / 30 分を埋め、6 水準すべてを同じ手続きで測り直す。

**判定の先取りをしない**ために、出力を意図的に制限する:

- 出すのは **ばらつき(sd)と保有の長さの分布と n** だけ。
- **`mean(r)` は計算しない。** 効果の符号も大きさも、ここでは一切見ない。
- 対象は**探索区間 2017-2019 のみ**。判定区間 2020-2021 は開かない。

ばらつきは「測定の粗さ」であって仮説の答えではないので、これを先に見ても
探索/判定の分離は壊れない。逆に、見ずに走らせると陰性を陰性と呼べない。

使い方:
    PYTHONPATH=src python scripts/measure_katsuo_dispersion.py
    PYTHONPATH=src python scripts/measure_katsuo_dispersion.py --feet 1 3 30
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
from bisect import bisect_left
from datetime import date, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "backtest_data" / "bitmex_trade_1s_XBTUSD"

# 事前登録 §2。判定区間 2020-01-01 以降はこのスクリプトから触れない。
EXPLORE_START = date(2017, 1, 1)
EXPLORE_END = date(2019, 12, 31)

# 事前登録 §3 の足の軸(6 水準)。
FEET = (1, 3, 5, 15, 30, 60)

# 事前登録 §4.2。原典に上限は無く、これは検証の都合で入れる制約なので
# 上限に達した割合を必ず報告する。
MAX_HOLD = 96


def _days(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def load_seconds(start: date, end: date) -> list[tuple[int, float, float, float, float]]:
    """1 秒バーを (epoch秒, o, h, l, c) で返す。約定が無い秒は行そのものが無い。"""
    rows: list[tuple[int, float, float, float, float]] = []
    epoch = datetime(1970, 1, 1)
    for d in _days(start, end):
        path = DATA / f"{d.year}" / f"{d:%Y%m%d}.csv.gz"
        if not path.exists():
            continue
        with gzip.open(path, "rt", newline="") as fh:
            reader = csv.reader(fh)
            next(reader, None)  # header
            for r in reader:
                ts = int((datetime.fromisoformat(r[0]) - epoch).total_seconds())
                rows.append((ts, float(r[1]), float(r[2]), float(r[3]), float(r[4])))
    rows.sort(key=lambda x: x[0])
    return rows


def fold(seconds, foot_min: int):
    """秒バーを UTC の壁時計で foot 分に畳む(事前登録 §1)。

    **1 秒も約定が無い足は行を作らない**(値動きなしではなく欠測として扱う)。
    """
    width = foot_min * 60
    bars: list[tuple[int, float, float, float, float]] = []
    cur = -1
    o = h = l = c = 0.0
    for ts, so, sh, sl, sc in seconds:
        bucket = ts - (ts % width)
        if bucket != cur:
            if cur >= 0:
                bars.append((cur, o, h, l, c))
            cur, o, h, l, c = bucket, so, sh, sl, sc
        else:
            h = max(h, sh)
            l = min(l, sl)
            c = sc
    if cur >= 0:
        bars.append((cur, o, h, l, c))
    return bars


def signals(bars):
    """原典 katsuo_v03 のヒゲ判定(`KATSUO_PARAMETER_INVENTORY.md` §2/§3)。

    足の向きで測り分けること、`int()` で切り捨ててから比較することを含め、
    原典どおりに実装する。返すのは (signal, lcprice, beard_len)。
    """
    out = []
    for _ts, o, h, l, c in bars:
        candle = c - o
        sign = 1 if candle > 0 else (-1 if candle < 0 else 0)
        if sign == 1:
            top, under = h - c, o - l
        else:  # 陰線と同値足は同じ測り方(同値足は下で signal=0 に落ちる)
            top, under = h - o, c - l
        body = abs(candle)
        if sign == 0:
            out.append((0, 0.0, 0.0))
        elif top > body and int(top) > int(under):
            out.append((-1, h, top))
        elif under > body and int(under) > int(top):
            out.append((1, l, under))
        else:
            out.append((0, 0.0, 0.0))
    return out


def trades(bars, sigs, max_hold: int = MAX_HOLD, variant: str = "both"):
    """カツオ自身の決済で 1 取引を切る(事前登録 §4.2)。

    建値 = シグナル足の終値。決済は次の早い方:
      1. 無効化: 終値がヒゲ先端(lcprice)を割った足
      2. 反対シグナルが出た足
    上限 max_hold 本で打ち切る(**原典に無い制約**なので到達率を報告する)。

    `variant` は §7 のアブレーション 4(決済ルールの分解)。
    2026-09-09 に前回の測定と保有中央値が食い違った(8 本 vs 2 本)ので、
    **どちらのルールがその差を作るのかを測定で切り分ける**ためにも使う。

    - ``both``       : 無効化 + 反対シグナル(主指標)
    - ``invalid``    : 無効化のみ
    - ``opposite``   : 反対シグナルのみ
    - ``global_lc``  : ``both`` だが lcprice を原典どおりグローバルに更新(§3-a)

    **戻り値は符号付きリターン(bp)と保有本数だけ。** 呼び出し側は平均を取らない。
    """
    n = len(bars)
    rets: list[float] = []
    holds: list[int] = []
    capped = 0

    # 原典の lcprice はグローバルで、シグナルが出るたびに上書きされる(§3-a)。
    # variant="global_lc" のときだけ、その挙動を各時点で再現するために先に畳んでおく。
    running_lc = None
    if variant == "global_lc":
        running_lc = [0.0] * n
        cur = 0.0
        for k in range(n):
            if sigs[k][0] != 0:
                cur = sigs[k][1]
            running_lc[k] = cur

    use_invalid = variant in ("both", "invalid", "global_lc")
    use_opposite = variant in ("both", "opposite", "global_lc")

    for i in range(n):
        s, lc, _ = sigs[i]
        if s == 0:
            continue
        entry = bars[i][4]
        if entry <= 0:
            continue
        exit_j = None
        limit = min(i + max_hold, n - 1)
        for j in range(i + 1, limit + 1):
            cj = bars[j][4]
            sj = sigs[j][0]
            if use_opposite and sj == -s:
                exit_j = j
                break
            # 無効化は「シグナルなしの足」でのみ見る(原典 §3-b の挙動をそのまま)
            if use_invalid and sj == 0:
                line = running_lc[j - 1] if running_lc is not None else lc
                if (s == 1 and cj <= line) or (s == -1 and cj >= line):
                    exit_j = j
                    break
        if exit_j is None:
            if limit <= i:
                continue
            exit_j = limit
            capped += 1
        rets.append(s * (bars[exit_j][4] / entry - 1.0) * 1e4)
        holds.append(exit_j - i)
    return rets, holds, capped


def _pct(sorted_vals, q: float) -> float:
    if not sorted_vals:
        return float("nan")
    k = (len(sorted_vals) - 1) * q
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return sorted_vals[int(k)]
    return sorted_vals[lo] * (hi - k) + sorted_vals[hi] * (k - lo)


def _sd(vals) -> float:
    if len(vals) < 2:
        return float("nan")
    m = sum(vals) / len(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--feet", type=int, nargs="+", default=list(FEET))
    ap.add_argument(
        "--variants",
        nargs="+",
        default=["both"],
        choices=["both", "invalid", "opposite", "global_lc"],
        help="決済ルールの分解(§7 アブレーション 4)。既定は主指標の both のみ",
    )
    ap.add_argument("--out", default=str(REPO / "docs" / "PHASE2" / "K1" / "dispersion.json"))
    args = ap.parse_args()

    print(f"探索区間 {EXPLORE_START} 〜 {EXPLORE_END} の 1 秒バーを読む(判定区間には触れない)")
    seconds = load_seconds(EXPLORE_START, EXPLORE_END)
    print(f"  秒バー {len(seconds):,} 行")

    results = {}
    for foot in args.feet:
        bars = fold(seconds, foot)
        sigs = signals(bars)
        n_sig = sum(1 for s, _, _ in sigs if s != 0)
        for variant in args.variants:
            rets, holds, capped = trades(bars, sigs, variant=variant)
            rs, hs = sorted(rets), sorted(holds)
            key = str(foot) if variant == "both" else f"{foot}:{variant}"
            results[key] = {
                "foot": foot,
                "variant": variant,
                "bars": len(bars),
                "signals": n_sig,
                "signal_rate": round(n_sig / len(bars), 4) if bars else None,
                "trades": len(rets),
                # **ばらつきのみ。平均は出さない(判定の先取りを避ける)**
                "sd_trade_bp": round(_sd(rets), 1),
                "iqr_trade_bp": [round(_pct(rs, 0.25), 1), round(_pct(rs, 0.75), 1)],
                "hold_median": round(_pct(hs, 0.5), 1),
                "hold_p25": round(_pct(hs, 0.25), 1),
                "hold_p75": round(_pct(hs, 0.75), 1),
                "hold_p95": round(_pct(hs, 0.95), 1),
                "capped_at_96": capped,
                "capped_share": round(capped / len(rets), 4) if rets else None,
            }
            r = results[key]
            print(
                f"{foot:>3}分 {variant:>9}: 足 {r['bars']:>9,}"
                f" / シグナル {r['signals']:>8,} ({r['signal_rate']:.1%})"
                f" / 取引 {r['trades']:>8,}"
                f" / sd_trade {r['sd_trade_bp']:>7.1f} bp"
                f" / 保有 中央 {r['hold_median']:>5.1f} 25% {r['hold_p25']:>5.1f}"
                f" 75% {r['hold_p75']:>5.1f} 95% {r['hold_p95']:>5.1f}"
                f" / 上限到達 {r['capped_share']:.1%}"
            )

    Path(args.out).write_text(
        json.dumps(
            {
                "note": (
                    "K1 の検出力の材料のみ。mean(r) は意図的に計算していない。"
                    "対象は探索区間 2017-2019 のみで、判定区間 2020-2021 には触れていない。"
                ),
                "explore": [EXPLORE_START.isoformat(), EXPLORE_END.isoformat()],
                "max_hold": MAX_HOLD,
                "feet": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n書き出し: {args.out}")


if __name__ == "__main__":
    main()
