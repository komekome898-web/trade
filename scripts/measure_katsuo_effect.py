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

import k1_source
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


def signals(bars, small, big, trunc=True, flip_body=False):
    """意図どおりのシグナル。返すのは足ごとの (signal, lcprice, candle_sign, strength)。

    `trunc=True`(既定)は原典どおり `int()` でドル単位に切り捨ててから向きを比べる。
    `trunc=False` は切り捨てずに比べる。**原典からの逸脱**なので、HANDOFF §3 手 2 のとおり
    「原典どおり」と並べて出す用途に限る。既定を変えない(他の測定はすべて原典どおり)。

    `flip_body=True` は **H1**(`docs/PHASE2/K1/H1_PREREG.md` §2、オーナー承認 L-070):
    門を通った足で **実体 ≥ 勝った側のヒゲ** なら、向きを実体と逆(`sig = -csign`)にし、
    無効化ラインを新しい向きの側の極値(売りなら高値、買いなら安値)に置く。強さは定義どおり
    `sig == csign` で決めるので、反転した足は必ず "weak" になる。小門の枝は `w > body` を要求するので、
    この足は大門の枝だけが通す。既定 `False` の出力は原典と 1 bit も変わらない(テストで固定)。
    """
    out = []
    for _ts, o, h, l, c in bars:
        candle = c - o
        csign = 1 if candle > 0 else (-1 if candle < 0 else 0)
        if csign == 0:
            out.append((0, 0.0, 0, ""))
            continue
        top, under = (h - c, o - l) if csign == 1 else (h - o, c - l)
        body = abs(candle)
        t_cmp, u_cmp = (int(top), int(under)) if trunc else (top, under)
        if t_cmp > u_cmp:
            sig, w, lc = -1, top, h
        elif u_cmp > t_cmp:
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
        if flip_body and body >= w:
            sig = -csign                        # 実体を逆張り(H1)
            lc = h if sig == -1 else l          # 新しい向きの側の極値
        out.append((sig, lc, csign, "strong" if sig == csign else "weak"))
    return out


def simulate(bars, sigs, keep=None, use_invalid=True):
    """建玉 1 単位でカツオの 4 分岐を回し、1 取引ずつの符号付きリターン(bp)を返す。

    `keep` で強さを絞ったとき、**絞られて外れたシグナルは「シグナル無し」として扱う**
    (その足でも無効化の判定は走りうる)。これは選択であり、事実として記録する。

    `use_invalid=False` は **H2a**(`docs/PHASE2/K1/H2_PREREG.md` §2、オーナー決定 L-073):
    ヒゲ先端の無効化(損切り)の枝を外し、決済は反対シグナルだけにする。第 7 部
    `measure_katsuo_exit_ablation.simulate(mode="opposite_only")` と同じ経路(再現ゲートで確認)。
    既定 `True` の出力は原典と同一(テストで固定)。
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
            # 無効化: 足の色が建玉と反対のときだけ見る(原典どおり)。H2a では見ない
            if use_invalid and pos != 0 and csign == -pos:
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
    ap.add_argument("--out", default=None)
    ap.add_argument("--flip-body", action="store_true",
                    help="H1(H1_PREREG.md §2): 実体 ≥ ヒゲ の足は実体を逆張りする。別ファイル effect_flipbody.json")
    ap.add_argument("--no-invalidation", action="store_true",
                    help="H2a(H2_PREREG.md §2): ヒゲ先端の無効化を外し反対シグナルだけで決済。"
                         "別ファイル effect_noinval.json(--flip-body と併用なら effect_flip_noinval.json)")
    k1_source.add_source_args(ap)
    args = ap.parse_args()
    start, end = k1_source.resolve_range(args)
    use_invalid = not args.no_invalidation
    if args.out is None:
        name = {(False, True): "effect.json", (True, True): "effect_flipbody.json",
                (False, False): "effect_noinval.json", (True, False): "effect_flip_noinval.json"}[
                    (args.flip_body, use_invalid)]
        args.out = str(k1_source.out_dir(args.source) / name)
    # H2a 単独の再現ゲート: 第 7 部 exit_ablation.json の opposite_only と n・平均が一致すること
    ref = {}
    if not use_invalid and not args.flip_body:
        ea = k1_source.out_dir(args.source) / "exit_ablation.json"
        if ea.exists():
            ref = json.loads(ea.read_text("utf-8"))["cells"]
    repro = []

    rng = random.Random(SEED)
    print(f"{args.source} 区間 {start} 〜 {end}(BitMEX の判定区間 2020-2021 には触れない)")
    seconds = k1_source.load_bars(args.source, start, end)
    gs = gates()
    print(f"  バー {len(seconds):,} 行 / 族 = 足 {len(args.feet)} × 門 {len(gs)} × 強さ 3"
          f" = {len(args.feet) * len(gs) * 3} セル")

    cells = {}
    for foot in args.feet:
        bars = base.fold(seconds, foot)
        ts = [b[0] for b in bars]
        years = [datetime.utcfromtimestamp(t).year for t in ts]
        for g in gs:
            sg = signals(bars, g[0], g[1], flip_body=args.flip_body)
            for keep in STRENGTHS:
                tr = simulate(bars, sg, None if keep == "both" else keep, use_invalid=use_invalid)
                if len(tr) < 30:
                    continue
                rs = [r for _i, r, _h, _w in tr]
                n = len(rs)
                mean = sum(rs) / n
                sd = math.sqrt(sum((x - mean) ** 2 for x in rs) / (n - 1)) if n > 1 else float("nan")
                lo, hi = block_bootstrap(tr, ts, rng)
                srt = sorted(rs)
                quant = {k: round(srt[min(n - 1, int(q * (n - 1)))], 2) for k, q in
                         (("p05", 0.05), ("p25", 0.25), ("p50", 0.50), ("p75", 0.75), ("p95", 0.95))}
                if ref:
                    rc = ref.get(f"opposite_only|{foot}|{label(g)}|{keep}")
                    if rc is not None:
                        ok = rc["n"] == n and abs(rc["mean_bp"] - mean) < 2e-3
                        repro.append({"key": f"{foot}|{label(g)}|{keep}", "ok": ok, "n": n,
                                      "n_ref": rc["n"], "mean": round(mean, 3), "mean_ref": rc["mean_bp"]})
                        if not ok:
                            raise SystemExit(f"再現ゲート不一致(H2a vs exit_ablation opposite_only): "
                                             f"{foot}|{label(g)}|{keep} n {n} vs {rc['n']}, "
                                             f"mean {mean:.3f} vs {rc['mean_bp']}")
                per_year = {}
                for y in sorted(set(years)):
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
                    "quantiles_bp": quant,
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
        "explore": [start.isoformat(), end.isoformat()],
        "source": args.source, "load": k1_source.last_load,
        "flip_body": args.flip_body, "use_invalid": use_invalid,
        "reproduction_gate": repro,
        "bootstrap_reps": BOOTSTRAP, "seed": SEED,
        "family": {"feet": list(args.feet), "gates": [label(g) for g in gs],
                   "strengths": list(STRENGTHS)},
        "cells": cells,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    if repro:
        print(f"再現ゲート(H2a vs exit_ablation opposite_only) {sum(r['ok'] for r in repro)}/{len(repro)} 一致")
    print(f"\nセル {len(cells)} 件 → {args.out}")


if __name__ == "__main__":
    main()
