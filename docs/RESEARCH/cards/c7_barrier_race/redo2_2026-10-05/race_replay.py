"""カード 7: 保存済みの measure/<窓>/run.npz の足の上で、カードの決まり(src/bot/research/cards/library/c7_barrier_race.py の
exposure をそのまま写す)をなぞり、レースごとの当たり(継続 = 前の当たりと同じ側の線 / 反転 = 逆の側の線)を復元する。
新しい損益は作らない。既にある走らせの隠れた中間の値(起点が更新された足)を、その走らせの出力(持ち高の符号が変わった足)と
突き合わせて復元するだけ(アドバイザーの指摘、2026-10-05)。台本の試験は無い(【試験の無い台本の値】)。
    python3 docs/RESEARCH/cards/c7_barrier_race/redo2_2026-10-05/race_replay.py
出力: このフォルダの RACE_REPLAY.md・races_<窓>.csv.gz(当たりごと: 時刻・側・継続か反転か・始めの w・次のレースの w)

決まり(コードの写し): カードは空でない足(decided)の終わり t ごとに呼ばれる。x = ln(終値)。前の呼び出しの x との差の 2 乗を (t, r²) で窓に足し、
t − 窓 以前に終わった分を外す。最初の呼び出しの足の終わり first_end が t − 窓 より後なら温まり(何もしない)。起点が無ければレースを始める
(w = √Σr² > 0 なら起点 = x・幅 = w、w = 0 なら始めない)。起点があれば move = x − 起点、move ≥ w なら持ち高 −1 にしてレースを始め直し、
move ≤ −w なら +1 にして始め直す。窓の和は math.fsum の代わりに累積和の差で出すので、境目で丸めの違いが出うる → 持ち高の符号の変わった足と照らす。
"""
import csv
import gzip
import math
import os
from datetime import date, timedelta

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
M = os.path.join(HERE, "..", "measure")
NS = 10**9
WIN = {"1h": 3600 * NS, "1d": 86400 * NS, "1w": 7 * 86400 * NS}


def wilson(k, n):
    if n == 0:
        return (None, None)
    z = 1.959964
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def jst_day(t):
    return (date(1970, 1, 1) + timedelta(days=int((t // NS + 9 * 3600) // 86400))).isoformat()


def replay(z, W):
    d = np.flatnonzero(z["decided"])
    t = z["end_ns"][d].astype(np.int64)
    x = np.log(z["close"][d].astype(float))
    r2 = np.zeros(len(x))
    r2[1:] = np.diff(x) ** 2
    C = np.cumsum(r2)
    lo = np.searchsorted(t, t - W, side="right")  # 窓の中 = t_j > t_k − W

    def width(k):
        s = C[k] - (C[lo[k] - 1] if lo[k] > 0 else 0.0)
        return math.sqrt(max(s, 0.0))
    first_end = t[0]
    k = int(np.searchsorted(t, first_end + W, side="left"))  # first_end ≤ t − W となる最初の足
    hits = []  # (足の番号 k, 側 +1 上 / −1 下, 始めの w, 次の w)
    anchor = None
    wcur = None
    n = len(x)
    while k < n:
        if anchor is None:
            w = width(k)
            if w > 0:
                anchor, wcur = x[k], w
            k += 1
            continue
        # 次の当たりを塊で探す
        step = 4096
        found = None
        j = k
        while j < n:
            seg = x[j:j + step] - anchor
            up = seg >= wcur
            dn = seg <= -wcur
            hit = up | dn
            if hit.any():
                i = int(np.argmax(hit))
                found = (j + i, 1 if up[i] else -1)
                break
            j += step
        if found is None:
            break
        kk, side = found
        w_new = width(kk)
        hits.append((kk, side, wcur, w_new))
        if w_new > 0:
            anchor, wcur = x[kk], w_new
        else:
            anchor, wcur = None, None
        k = kk + 1
    return d, t, hits


def main():
    out = ["# カード 7: レースの当たりの復元(保存済みの足の上でカードの決まりをなぞった。新しい損益は作らない)", ""]
    for v in ("1h", "1d", "1w"):
        z = np.load(os.path.join(M, v, "run.npz"))
        d, t, hits = replay(z, WIN[v])
        e = z["exposure"][d]
        # 照らし: 持ち高の符号が変わった足(0 → ±1 を含む)
        se = np.sign(e)
        chg = set(np.flatnonzero(se != np.concatenate([[0.0], se[:-1]])).tolist())
        rev, cont = [], []
        prev_side = None
        for (k, side, w0, w1) in hits:
            if prev_side is None or side != prev_side:
                rev.append(k)
            else:
                cont.append(k)
            prev_side = side
        rset = set(rev)
        # 当たりの後の持ち高 = −side になっているか
        sign_ok = sum(1 for (k, side, _, _) in hits if se[k] == -side)
        out += [f"## 窓 {v}", "",
                f"- 当たり {len(hits):,}(反転 {len(rev):,}・継続 {len(cont):,})。最初の当たり {jst_day(t[hits[0][0]]) if hits else '—'}",
                f"- 照らし: 持ち高の符号が変わった足 {len(chg):,}、復元した反転(最初の当たりを含む){len(rset):,}、一致 {len(chg & rset):,}、"
                f"片方だけ: 走らせだけ {len(chg - rset):,}・復元だけ {len(rset - chg):,}。当たりの足の持ち高が −側 と一致 {sign_ok:,} / {len(hits):,}", ""]
        # 年ごと・前半後半(当たりの日本時間の日)。最初の当たりは継続・反転のどちらでもないので除く
        days = sorted(l.split(",")[0] for l in open(os.path.join(M, v, "daily.csv")).read().splitlines()[1:])
        edge = days[len(days) // 2]
        recs = []
        prev_side = None
        for (k, side, w0, w1) in hits:
            if prev_side is not None:
                recs.append((jst_day(t[k]), side != prev_side, w0))
            prev_side = side
        out += ["| 期間 | 当たり | 反転 | 継続 | 反転の割合 [95% 区間、Wilson] |", "|---|---|---|---|---|"]
        groups = [("全期間", lambda dd: True), ("前半", lambda dd: dd < edge), ("後半", lambda dd: dd >= edge)]
        groups += [(y, (lambda y: lambda dd: dd[:4] == y)(y)) for y in sorted({r[0][:4] for r in recs})]
        for nm, fn in groups:
            xs = [r for r in recs if fn(r[0])]
            kk = sum(1 for r in xs if r[1])
            a, b = wilson(kk, len(xs))
            out.append(f"| {nm} | {len(xs):,} | {kk:,} | {len(xs) - kk:,} | " + ("—" if a is None else f"{kk / len(xs):.3f} [{a:.3f}, {b:.3f}]") + " |")
        out += ["", f"前半・後半の境 {edge}(daily.csv の日数で 2 つ)。区間は当たりを独立とみた二項の区間(時間の依存は入れていない)。", ""]
        # w の三分位ごとの反転の割合(建ての前に決まる: そのレースの始めの w)
        ws = np.array([r[2] for r in recs])
        q1, q2 = np.quantile(ws, [1 / 3, 2 / 3])
        out += ["| レースの始めの w(bp)の帯 | 当たり | 反転の割合 [区間] | 前半 | 後半 |", "|---|---|---|---|---|"]
        for lo_, hi_, nm in ((0, q1, f"〜{q1 * 1e4:.1f}"), (q1, q2, f"{q1 * 1e4:.1f}〜{q2 * 1e4:.1f}"), (q2, 1e9, f"{q2 * 1e4:.1f}〜")):
            cells = []
            for fn in (lambda dd: True, lambda dd: dd < edge, lambda dd: dd >= edge):
                xs = [r for r in recs if lo_ <= r[2] < hi_ and fn(r[0])]
                kk = sum(1 for r in xs if r[1])
                a, b = wilson(kk, len(xs))
                cells.append(f"{len(xs):,}・" + ("—" if a is None else f"{kk / len(xs):.3f} [{a:.3f}, {b:.3f}]"))
            out.append(f"| {nm} | {cells[0]} | {cells[1]} | {cells[2]} |")
        out.append("")
        with gzip.open(os.path.join(HERE, f"races_{v}.csv.gz"), "wt", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["hit_end_ns", "jst_day", "side", "kind", "w_start", "w_next"])
            ps = None
            for (k, side, w0, w1) in hits:
                w.writerow([int(t[k]), jst_day(t[k]), side, "first" if ps is None else ("reversal" if side != ps else "continuation"), f"{w0:.8f}", f"{w1:.8f}"])
                ps = side
    open(os.path.join(HERE, "RACE_REPLAY.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
