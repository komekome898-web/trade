"""K1 の**検出力の材料だけ**を測る(効果の大きさは見ない)。

事前登録 `docs/PHASE2/K1/PREREG.md` §5.2 は MDE の基礎に `sd_trade`(1 取引の
符号付きリターンのばらつき)を使う。規約 §4.1 は「**MDE を書いていない事前登録は
実行しない**」と定めているので、**族の全セルで n と `sd_trade` が要る**。

**判定の先取りをしない**ために、出力を意図的に制限する:

- 出すのは **ばらつき(sd)と保有の長さの分布と n** だけ。
- **`mean(r)` は計算しない。** 効果の符号も大きさも、ここでは一切見ない。
  ただし**四分位は出す**ので、分布の非対称から符号の気配は読める。
  対象は**探索区間 2017-2019** で、そこは §2 のとおり「ここだけで全部決める」区間である。
  **封印している判定区間 2020-2021 には触れない。**(この但し書きは L-050 の指摘による。
  旧版の docstring は「符号も大きさも一切見ない」と書いていたが、それは虚偽だった。)

**シグナルの条件は意図どおり**(`KATSUO_PARAMETER_INVENTORY.md` §3.1、L-052 / L-053):

    勝った側のヒゲ w = 反対側のヒゲより長い方(int() で切り捨てて比較)
    シグナルあり ⇔ ( w ≥ s かつ w > |実体| )  または  ( w ≥ b )

`s`(小門)は絞り、`b`(大門)は**実体条件を飛ばして増やす**。
**門は bp 建て**(L-052。絶対ドルは年ごとに別物になる)。

使い方:
    PYTHONPATH=src python scripts/measure_katsuo_dispersion.py            # 族の全セル
    PYTHONPATH=src python scripts/measure_katsuo_dispersion.py --exit-variants
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "backtest_data" / "bitmex_trade_1s_XBTUSD"

# 事前登録 §2。判定区間 2020-01-01 以降はこのスクリプトから触れない。
EXPLORE_START = date(2017, 1, 1)
EXPLORE_END = date(2019, 12, 31)

# 事前登録 §3 の族(L-053 で門を s×b の組に変更)
FEET = (1, 3, 5, 15, 30, 60)
SMALL_GATES = (None, 10.0, 19.0, 30.0)   # bp。None = 最小長を課さない(v03 と同じ)
BIG_GATES = (None, 24.0, 40.0)           # bp。None = 実体を飛ばす枝を使わない
STRENGTHS = ("strong", "weak", "both")

MAX_HOLD = 96  # 原典に上限は無い。検証の都合の制約なので到達率を必ず報告する


def gate_pairs():
    """s ≤ b の組だけを使う。s > b だと小門の枝が大門に包含されて縮退するため。"""
    return [(s, b) for s in SMALL_GATES for b in BIG_GATES
            if b is None or s is None or s <= b]


def _days(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def load_seconds(start: date, end: date):
    """1 秒バーを (epoch秒, o, h, l, c) で返す。約定が無い秒は行そのものが無い。"""
    rows = []
    epoch = datetime(1970, 1, 1)
    for d in _days(start, end):
        path = DATA / f"{d.year}" / f"{d:%Y%m%d}.csv.gz"
        if not path.exists():
            continue
        with gzip.open(path, "rt", newline="") as fh:
            reader = csv.reader(fh)
            next(reader, None)
            for r in reader:
                ts = int((datetime.fromisoformat(r[0]) - epoch).total_seconds())
                rows.append((ts, float(r[1]), float(r[2]), float(r[3]), float(r[4])))
    rows.sort(key=lambda x: x[0])
    return rows


def fold(seconds, foot_min: int):
    """秒バーを UTC の壁時計で foot 分に畳む。**1 秒も約定が無い足は行を作らない**(欠測)。"""
    width = foot_min * 60
    bars = []
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


def signals(bars, small_bp=None, big_bp=None):
    """意図どおりのシグナル判定(`KATSUO_PARAMETER_INVENTORY.md` §3.1)。

    返すのは足ごとの `(signal, lcprice, candle_sign, strength)`。
    `strength` は 'strong'(下ヒゲ陽線 / 上ヒゲ陰線)か 'weak'、シグナルが無ければ ''。
    """
    out = []
    for _ts, o, h, l, c in bars:
        candle = c - o
        csign = 1 if candle > 0 else (-1 if candle < 0 else 0)
        if csign == 0:  # 同値足は原典どおりシグナルにしない
            out.append((0, 0.0, 0, ""))
            continue
        top, under = (h - c, o - l) if csign == 1 else (h - o, c - l)
        body = abs(candle)
        # 条件 3(向きを決める)。24 の枝でも飛ばさない — オーナー確認済み L-053
        if int(top) > int(under):
            sig, w, lc = -1, top, h
        elif int(under) > int(top):
            sig, w, lc = 1, under, l
        else:
            out.append((0, 0.0, csign, ""))
            continue
        wbp = w / c * 1e4 if c > 0 else 0.0
        ok_small = (small_bp is None or wbp >= small_bp) and w > body
        ok_big = big_bp is not None and wbp >= big_bp
        if not (ok_small or ok_big):
            out.append((0, 0.0, csign, ""))
            continue
        # 強い = 下ヒゲ陽線(買い×陽線)/ 上ヒゲ陰線(売り×陰線)
        strength = "strong" if sig == csign else "weak"
        out.append((sig, lc, csign, strength))
    return out


def trades(bars, sigs, variant="both", colour_cond=True, keep=None, max_hold=MAX_HOLD):
    """カツオ自身の決済で 1 取引を切る(事前登録 §4.2)。

    `colour_cond=True` が**原典どおり**: 無効化を見るのは `signal == 0` かつ
    **足の色が建玉と反対**のときだけ(意図マップ §3-d、L-052)。
    旧版は色を見ずに判定しており、文書にも原典にも無い第 3 の挙動だった。

    `keep` は 'strong' / 'weak' / None(両方)。
    **戻り値は符号付きリターン(bp)と保有本数だけ。** 呼び出し側は平均を取らない。
    """
    n = len(bars)
    rets, holds, sig_h = [], [], []
    capped = ran_out = 0
    use_invalid = variant in ("both", "invalid")
    use_opposite = variant in ("both", "opposite")

    for i in range(n):
        s, lc, _cs, strength = sigs[i]
        if s == 0 or (keep is not None and strength != keep):
            continue
        entry = bars[i][4]
        if entry <= 0:
            continue
        # §4.3 の保有曲線用に h=2 の符号付きリターンも拾う(sd_sig(2) の材料)
        if i + 2 < n and bars[i + 2][4] > 0:
            sig_h.append(s * (bars[i + 2][4] / entry - 1.0) * 1e4)

        exit_j = None
        hard = i + max_hold
        limit = min(hard, n - 1)
        for j in range(i + 1, limit + 1):
            sj, _lcj, csj, _stj = sigs[j]
            if use_opposite and sj == -s:
                exit_j = j
                break
            if use_invalid and sj == 0 and (not colour_cond or csj == -s):
                cj = bars[j][4]
                if (s == 1 and cj <= lc) or (s == -1 and cj >= lc):
                    exit_j = j
                    break
        if exit_j is None:
            if limit <= i:
                continue
            exit_j = limit
            # 「上限に達した」と「データが尽きた」を分けて数える(L-050、監査 #25)
            if hard <= n - 1:
                capped += 1
            else:
                ran_out += 1
        rets.append(s * (bars[exit_j][4] / entry - 1.0) * 1e4)
        holds.append(exit_j - i)
    return rets, holds, sig_h, capped, ran_out


def _pct(v, q):
    if not v:
        return float("nan")
    k = (len(v) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return v[int(k)] if lo == hi else v[lo] * (hi - k) + v[hi] * (k - lo)


def _sd(v):
    if len(v) < 2:
        return float("nan")
    m = sum(v) / len(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def _label(gate):
    s, b = gate
    return f"s{'-' if s is None else int(s)}/b{'-' if b is None else int(b)}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--feet", type=int, nargs="+", default=list(FEET))
    ap.add_argument("--exit-variants", action="store_true",
                    help="原典の門(s=19/b=24・両方)についてのみ、決済ルールを分解して測る")
    ap.add_argument("--out", default=str(REPO / "results" / "PHASE2" / "K1" / "dispersion.json"))
    args = ap.parse_args()

    print(f"探索区間 {EXPLORE_START} 〜 {EXPLORE_END}(判定区間には触れない)")
    seconds = load_seconds(EXPLORE_START, EXPLORE_END)
    print(f"  秒バー {len(seconds):,} 行 / 族 = 足 {len(args.feet)} × 門 {len(gate_pairs())} × 強さ 3")

    cells, variants = {}, {}
    for foot in args.feet:
        bars = fold(seconds, foot)
        for gate in gate_pairs():
            sigs = signals(bars, gate[0], gate[1])
            for keep in STRENGTHS:
                rets, holds, sig_h, capped, ran_out = trades(
                    bars, sigs, keep=None if keep == "both" else keep)
                if not rets:
                    continue
                hs = sorted(holds)
                rs = sorted(rets)
                cells[f"{foot}|{_label(gate)}|{keep}"] = {
                    "foot": foot, "small_bp": gate[0], "big_bp": gate[1], "strength": keep,
                    "bars": len(bars), "n": len(rets),
                    "sd_trade_bp": round(_sd(rets), 1),
                    "sd_sig2_bp": round(_sd(sig_h), 1),
                    "iqr_trade_bp": [round(_pct(rs, 0.25), 1), round(_pct(rs, 0.75), 1)],
                    "hold_median": round(_pct(hs, 0.5), 1),
                    "hold_p95": round(_pct(hs, 0.95), 1),
                    "capped_share": round(capped / len(rets), 4),
                    "ran_out_share": round(ran_out / len(rets), 4),
                }
        r = cells.get(f"{foot}|s19/b24|both")
        if r:
            print(f"  {foot:>3}分 原典の門(19/24): n={r['n']:>7,}"
                  f" sd_trade={r['sd_trade_bp']:>6.1f}bp sd_sig2={r['sd_sig2_bp']:>6.1f}bp"
                  f" 保有中央{r['hold_median']:>4.1f} 上限到達{r['capped_share']:.1%}")

        if args.exit_variants:
            sigs = signals(bars, 19.0, 24.0)
            for v in ("both", "invalid", "opposite"):
                for cc in (True, False):
                    rets, holds, _sh, capped, _ro = trades(bars, sigs, variant=v, colour_cond=cc)
                    if not rets:
                        continue
                    variants[f"{foot}|{v}|colour={int(cc)}"] = {
                        "n": len(rets), "sd_trade_bp": round(_sd(rets), 1),
                        "hold_median": round(_pct(sorted(holds), 0.5), 1),
                        "capped_share": round(capped / len(rets), 4),
                    }

    payload = {
        "note": ("K1 の検出力の材料のみ。mean(r) は計算していない(四分位は出す)。"
                 "対象は探索区間 2017-2019 のみで、判定区間 2020-2021 には触れていない。"
                 "シグナルは意図どおりの OR 規則、門は bp 建て、無効化は原典どおり色条件つき。"),
        "explore": [EXPLORE_START.isoformat(), EXPLORE_END.isoformat()],
        "max_hold": MAX_HOLD,
        "family": {"feet": list(args.feet),
                   "gates": [_label(g) for g in gate_pairs()],
                   "strengths": list(STRENGTHS)},
        "cells": cells,
        "exit_variants": variants,
    }
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nセル {len(cells)} 件 → {args.out}")


if __name__ == "__main__":
    main()
