"""カツオの機構の**効果量を測る**。探索区間 2017-2019 のみ。

**これが本体である。** 帰無も MDE も判定バーも作らない(オーナー判断 2026-09-09、L-056):
K1 の成果物は「効果量 bp + 信頼区間」であって合否ではないので、
合否を出す装置は何もゲートしていなかった。

## 何を測るか

**建玉を 1 単位持ち、カツオの 4 分岐どおりに動かしたときの、1 取引の符号付きリターン。**

シグナルの条件(オーナー確定 L-052 / L-053):

    勝った側のヒゲ w = 反対側のヒゲより長い方(int() で切り捨てて比較)
    シグナルあり ⇔ ( w ≥ s かつ w > |実体| ) または ( w ≥ b )

行動(原典 `katsuo_v03.py` 490-533 の 4 分岐):

    強い(下ヒゲ陽線 = 買い / 上ヒゲ陰線 = 売り):
        建玉が反対      → **ドテン**(決済して逆に建てる)
        建玉が無い      → 新規
        建玉が同じ向き  → 何もしない(増し玉は意図に無い実装なので外す)
    弱い(上ヒゲ陽線 = 売り / 下ヒゲ陰線 = 買い):
        建玉が反対      → **決済のみ**(逆には建てない)
        建玉が無い      → 新規
        建玉が同じ向き  → 何もしない
    シグナル無し:
        **足の色が建玉と反対のときだけ**、終値がヒゲ先端を割ったか見る → 割ったら決済
        (原典どおり。意図マップ §3-d)

**建玉状態を持たせる理由**: I-4(強さでドテンと決済を分ける)と I-5(建玉が無ければ
弱いシグナルでも建てる)は意図マップで **○** と判定してある。
**持たせない測定は、機構の中心を測らない**(オーナー指摘 2026-09-09)。

## 出さないもの

- **帰無・MDE・判定バー**。上記のとおり
- **判定区間 2020-2021 には触れない**

    PYTHONPATH=src python scripts/measure_katsuo_effect.py
"""
from __future__ import annotations

import argparse
import json
import math
import random
from datetime import date, datetime
from pathlib import Path

import measure_katsuo_dispersion as base  # 秒バーの読み込みと足の畳み込みを共有

REPO = Path(__file__).resolve().parents[1]

EXPLORE_START = date(2017, 1, 1)
EXPLORE_END = date(2019, 12, 31)

FEET = (1, 3, 5, 15, 30, 60)
# 小門 s: "off" = 小門の枝そのものを使わない / None = 最小長を課さない(実体条件のみ)
SMALL = ("off", None, 10.0, 19.0, 30.0)
BIG = (None, 24.0, 40.0)          # 大門 b: None = 実体を飛ばす枝を使わない
STRENGTHS = ("strong", "weak", "both")

BOOTSTRAP = 200                    # ブロックブートストラップの反復
SEED = 20260909


def gates():
    """`s` と `b` の組。**`s > b` は `(off, b)` と同じ規則になるので重複として外す。**

    独立監査の指摘(2 回目 #15)で `off` を足した。旧版は `s > b` を「縮退」として
    落としていたが、残る `(w ≥ b)` 単独は**他のどのセルとも違う固有の設定**で、
    しかも**オーナーが確定させた「実足の長さに関わらず単体で長いヒゲ」を
    単独で測れる唯一のセル**だった。
    """
    out = []
    for s in SMALL:
        for b in BIG:
            if s == "off" and b is None:
                continue                       # 条件が空になる
            if isinstance(s, float) and b is not None and s > b:
                continue                       # (off, b) と同じ規則
            out.append((s, b))
    return out


def label(gate) -> str:
    s, b = gate
    st = "off" if s == "off" else ("-" if s is None else str(int(s)))
    return f"s{st}/b{'-' if b is None else int(b)}"


def signals(bars, small, big):
    """意図どおりのシグナル。返すのは足ごとの (signal, lcprice, candle_sign, strength)。"""
    out = []
    for _ts, o, h, l, c in bars:
        candle = c - o
        csign = 1 if candle > 0 else (-1 if candle < 0 else 0)
        if csign == 0:
            out.append((0, 0.0, 0, ""))
            continue
        top, under = (h - c, o - l) if csign == 1 else (h - o, c - l)
        body = abs(candle)
        if int(top) > int(under):
            sig, w, lc = -1, top, h
        elif int(under) > int(top):
            sig, w, lc = 1, under, l
        else:
            out.append((0, 0.0, csign, ""))
            continue
        wbp = w / c * 1e4 if c > 0 else 0.0
        ok_small = small != "off" and (small is None or wbp >= small) and w > body
        ok_big = big is not None and wbp >= big
        if not (ok_small or ok_big):
            out.append((0, 0.0, csign, ""))
            continue
        out.append((sig, lc, csign, "strong" if sig == csign else "weak"))
    return out


def simulate(bars, sigs, keep=None):
    """建玉 1 単位でカツオの 4 分岐を回し、1 取引ずつの符号付きリターン(bp)を返す。

    `keep` で強さを絞ったとき、**絞られて外れたシグナルは「シグナル無し」として扱う**
    (その足でも無効化の判定は走りうる)。これは選択であり、事実として記録する。
    """
    pos = 0            # +1 買い / -1 売り / 0 なし
    entry = 0.0
    entry_i = 0
    lcline = 0.0
    trades = []        # (entry_index, リターン bp, 保有本数, 決済理由)

    def close(i, price, why):
        nonlocal pos
        trades.append((entry_i, pos * (price / entry - 1.0) * 1e4, i - entry_i, why))
        pos = 0

    for i, (sig, lc, csign, strength) in enumerate(sigs):
        c = bars[i][4]
        if c <= 0:
            continue
        actionable = sig != 0 and (keep is None or strength == keep)

        if not actionable:
            # 無効化: 足の色が建玉と反対のときだけ見る(原典どおり)
            if pos != 0 and csign == -pos:
                if (pos == 1 and c <= lcline) or (pos == -1 and c >= lcline):
                    close(i, c, "invalidated")
            continue

        if pos == sig:
            lcline = lc                     # 同じ向き: 増し玉はしない。ラインだけ更新
        elif pos == -sig:
            close(i, c, "reversed" if strength == "strong" else "opposite_weak")
            if strength == "strong":        # 強いシグナルはドテン(逆に建てる)
                pos, entry, entry_i, lcline = sig, c, i, lc
        else:                               # 建玉なし: 強弱を問わず新規
            pos, entry, entry_i, lcline = sig, c, i, lc

    return trades


def block_bootstrap(trades, bar_ts, rng, reps=BOOTSTRAP):
    """日単位のブロックブートストラップで mean(r) の 95% 区間を出す。

    取引は保有が重なりうるので、素朴な i.i.d. の区間は幅を過小評価する。
    **入口の日でブロックに切り、日を復元抽出する。**
    """
    if not trades:
        return (float("nan"), float("nan"))
    byday: dict[int, list[float]] = {}
    for idx, r, _hold, _why in trades:
        day = bar_ts[idx] // 86400
        byday.setdefault(day, []).append(r)
    days = list(byday.values())
    means = []
    for _ in range(reps):
        pool = []
        for _ in range(len(days)):
            pool.extend(days[rng.randrange(len(days))])
        if pool:
            means.append(sum(pool) / len(pool))
    means.sort()
    lo = means[int(0.025 * (len(means) - 1))]
    hi = means[int(0.975 * (len(means) - 1))]
    return (lo, hi)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--feet", type=int, nargs="+", default=list(FEET))
    ap.add_argument("--out", default=str(REPO / "docs" / "PHASE2" / "K1" / "effect.json"))
    args = ap.parse_args()

    rng = random.Random(SEED)
    print(f"探索区間 {EXPLORE_START} 〜 {EXPLORE_END}(判定区間 2020-2021 には触れない)")
    seconds = base.load_seconds(EXPLORE_START, EXPLORE_END)
    gs = gates()
    print(f"  秒バー {len(seconds):,} 行 / 族 = 足 {len(args.feet)} × 門 {len(gs)} × 強さ 3"
          f" = {len(args.feet) * len(gs) * 3} セル")

    cells = {}
    for foot in args.feet:
        bars = base.fold(seconds, foot)
        ts = [b[0] for b in bars]
        years = [datetime.utcfromtimestamp(t).year for t in ts]
        for g in gs:
            sg = signals(bars, g[0], g[1])
            for keep in STRENGTHS:
                tr = simulate(bars, sg, None if keep == "both" else keep)
                if len(tr) < 30:
                    continue
                rs = [r for _i, r, _h, _w in tr]
                n = len(rs)
                mean = sum(rs) / n
                sd = math.sqrt(sum((x - mean) ** 2 for x in rs) / (n - 1)) if n > 1 else float("nan")
                lo, hi = block_bootstrap(tr, ts, rng)
                per_year = {}
                for y in (2017, 2018, 2019):
                    ys = [r for i, r, _h, _w in tr if years[i] == y]
                    if ys:
                        per_year[str(y)] = {"n": len(ys), "mean_bp": round(sum(ys) / len(ys), 3)}
                why: dict[str, int] = {}
                for _i, _r, _h, w in tr:
                    why[w] = why.get(w, 0) + 1
                cells[f"{foot}|{label(g)}|{keep}"] = {
                    "foot": foot, "gate": label(g), "strength": keep,
                    "n": n,
                    "mean_bp": round(mean, 3),
                    "ci95_bp": [round(lo, 3), round(hi, 3)],
                    "sd_bp": round(sd, 1),
                    "hold_median": sorted(h for _i, _r, h, _w in tr)[n // 2],
                    "exit_reasons": why,
                    "per_year": per_year,
                }
        best = max((v for k, v in cells.items() if v["foot"] == foot),
                   key=lambda v: abs(v["mean_bp"]), default=None)
        if best:
            print(f"  {foot:>3}分 完了。この足の最大 |mean| = {best['mean_bp']:+.2f} bp"
                  f" [{best['ci95_bp'][0]:+.2f}, {best['ci95_bp'][1]:+.2f}]"
                  f" n={best['n']:,} ({best['gate']}/{best['strength']})")

    Path(args.out).write_text(json.dumps({
        "note": ("カツオの 4 分岐を建玉 1 単位で回した 1 取引あたりの符号付きリターン。"
                 "探索区間 2017-2019 のみ。帰無・MDE・判定バーは作っていない。"),
        "explore": [EXPLORE_START.isoformat(), EXPLORE_END.isoformat()],
        "bootstrap_reps": BOOTSTRAP, "seed": SEED,
        "family": {"feet": list(args.feet), "gates": [label(g) for g in gs],
                   "strengths": list(STRENGTHS)},
        "cells": cells,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nセル {len(cells)} 件 → {args.out}")


if __name__ == "__main__":
    main()
