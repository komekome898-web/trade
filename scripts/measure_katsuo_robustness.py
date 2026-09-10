"""**K1 深掘り — 診断の測定**(`docs/PHASE2/K1/DEEPDIVE_PLAN.md` §1)。

第 4 部(`measure_katsuo_signal_horizon.py`)の効果量が、**測定手順・データ・統計の
どれに依存しているか**を 1 パスで測る。判定・帰無・MDE・判定バーは作らない。経費も引かない。
**引き算をしない**(成分は横に並べる)。

## 母集団と族

    足 6 × 門 2(`s19/b24`, `s-/b-`)× 強さ 3(strong/weak/both)× h ∈ {1,2,3,5,10} = 180 セル

シグナルは `measure_katsuo_effect.signals()`(原典どおり `trunc=True`)、足は
`measure_katsuo_dispersion.fold()`、形は `measure_katsuo_body_wick.direction_and_shape()` を
**import して使う**(書き写さない)。1 セルの材料はシグナル足ごとの行

    (i, ts, sig, strength, r_h, day, year, hour, wday, wbp, body_bp, stale_close, vol_prev)

## 診断

| ID | 何を測るか |
|---|---|
| D1 | 基準線。第 4 部と同じ `r_h`・同じ日ブロックブートストラップ(`day_bootstrap` + `cell_rng`)|
| D2 | 区間の頑健性。日 1000 回 / 週ブロック 200・1000 回 / 月ブロック 200 回 |
| D3 | 1 本遅らせた入口 `sig × (close[i+h]/close[i+1] − 1) × 10⁴`(h ≥ 2)|
| D4 | 古い終値(`close[i] == close[i−1]`)のシグナル足を除いた平均 |
| D5 | 分割の一致。年内を ISO 週の奇偶 / 上半期・下半期で割り、符号が揃うか |
| D6 | UTC 3 時間 × 8 区分 |
| D7 | UTC 曜日 7 区分 |
| D8 | 直前 100 本のボラで三分位(先読み無し)|
| D9 | 年 × ヒゲ層(`WICK_BINS`)|
| D9b | 年 × 実体比の層(`RATIO_BINS`)|
| D10 | 年の成分表(realized vol・平均ヒゲ・平均実体・実体 > ヒゲ の割合・門の通過率)|
| D11 | 裾を落とした平均(1%/5% トリム・ウィンザー)|

**D1 の再現ゲート**: 同じ出所の `signal_horizon.json` の該当セルと n・mean_bp・ci95_bp、
および年別の n・mean_bp・ci95_bp が**全部一致**しなければ `SystemExit` で止まる。

    PYTHONPATH=src:scripts python scripts/measure_katsuo_robustness.py --source binance
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from datetime import date, datetime
from pathlib import Path

import numpy as np

import k1_source
import measure_katsuo_body_wick as bw
import measure_katsuo_dispersion as base
import measure_katsuo_effect as eff
from measure_katsuo_signal_horizon import cell_rng, day_bootstrap

REPO = Path(__file__).resolve().parents[1]

FEET = (1, 3, 5, 15, 30, 60)
# 設計書 §1.1: 門は 2 つだけ(第 4・8 部の年別表がこの 2 門で書かれている)
GATES = {"s19/b24": (19.0, 24.0), "s-/b-": (None, None)}
HORIZONS = (1, 2, 3, 5, 10)
STRENGTHS = ("strong", "weak", "both")

SEED = 20260909            # 第 4 部と同じ(`cell_rng` が使う)
REPS_SMALL = 200           # 第 4 部と同じ反復。D2 以降の numpy 版の既定
REPS_LARGE = 1000
MIN_N = 30                 # 第 4 部と同じ足切り
VOL_WINDOW = 100           # D8 の直前本数
FUNDING_HOURS = (4, 12, 20)   # BitMEX の資金調達時刻(UTC)。D6 の区分に印を付けるだけ
TRIMS = (0.01, 0.05)       # D11
SEAL_END = date(2019, 12, 31)  # BitMEX の封印(判定区間 2020-2021 には触れない)


def bin_labels(edges) -> list[str]:
    """`measure_katsuo_body_wick.bin_of` が返すラベルを、区間の順に並べたもの。"""
    return ([f"[{edges[i]:g},{edges[i + 1]:g})" for i in range(len(edges) - 1)]
            + [f"[{edges[-1]:g},+)"])


WICK_LABELS = bin_labels(bw.WICK_BINS)
RATIO_LABELS = bin_labels(bw.RATIO_BINS)


def bin_index(x: np.ndarray, edges) -> np.ndarray:
    """`bin_of` と同じ層番号(`edges[i] <= x < edges[i+1]`、上限超えは最後の層)。"""
    k = np.searchsorted(np.asarray(edges, dtype=np.float64), x, side="right") - 1
    return np.clip(k, 0, len(edges) - 1).astype(np.int16)


# ---------------------------------------------------------------- 乱数・区間

def seed_of(name: str) -> int:
    """セル名から決まる種。セルを足しても・順番を変えても、そのセルの区間は動かない。"""
    return int.from_bytes(hashlib.sha256(name.encode("utf-8")).digest()[:8], "little")


def np_boot(bsum: np.ndarray, bn: np.ndarray, name: str, reps: int = REPS_SMALL):
    """ブロックブートストラップ(numpy 版)。

    `day_bootstrap` と**同じ流儀**: ブロック単位の (合計, 件数) を先に畳み、
    ブロックを復元抽出して 平均 = Σ合計 / Σ件数。分位は
    `sorted[int(0.025*(reps-1))]` / `sorted[int(0.975*(reps-1))]`。
    """
    k = int(bsum.size)
    if k == 0 or bn.sum() <= 0:
        return [None, None]
    rng = np.random.default_rng(seed_of(name))
    idx = rng.integers(0, k, size=(reps, k))
    s = bsum[idx].sum(axis=1)
    c = bn[idx].sum(axis=1)
    means = np.sort(np.where(c > 0, s / np.where(c > 0, c, 1.0), np.nan))
    lo, hi = means[int(0.025 * (reps - 1))], means[int(0.975 * (reps - 1))]
    return [None if np.isnan(lo) else float(lo), None if np.isnan(hi) else float(hi)]


class Folder:
    """1 セルのブロック集計。ブロックキーを 1 回だけ圧縮し、以後は部分集合を `bincount` で畳む。

    返すのは**件数が 0 でないブロックだけ**(= その部分集合に現れたブロックだけ)なので、
    `day_bootstrap` が日の一覧を作るのと同じ集合・同じ昇順になる。
    """

    def __init__(self, keys: np.ndarray, vals: np.ndarray):
        self.u, self.inv = np.unique(keys, return_inverse=True)
        self.inv = self.inv.astype(np.int64).ravel()
        self.vals = vals
        self.k = int(self.u.size)

    def fold(self, mask=None):
        inv = self.inv if mask is None else self.inv[mask]
        val = self.vals if mask is None else self.vals[mask]
        s = np.bincount(inv, weights=val, minlength=self.k)
        n = np.bincount(inv, minlength=self.k)
        nz = n > 0
        return self.u[nz], s[nz], n[nz].astype(np.float64)


def rnd(x, d=4):
    if x is None:
        return None
    x = float(x)
    return None if x != x else round(x, d)


def rnd2(pair, d=4):
    return [rnd(pair[0], d), rnd(pair[1], d)]


def mean_of(vals: np.ndarray):
    return float(vals.sum() / vals.size) if vals.size else None


def trimmed_and_winsor(vals: np.ndarray, q: float):
    """両側 `q` のトリム平均とウィンザー平均。

    `k = floor(q*n)` 個を両端から落とす(トリム)/ 両端の残った値に丸める(ウィンザー)。
    `n − 2k <= 0` になるときは None。
    """
    n = int(vals.size)
    if n == 0:
        return None, None
    k = int(np.floor(q * n))
    if n - 2 * k <= 0:
        return None, None
    sv = np.sort(vals)
    trimmed = float(sv[k:n - k].mean())
    winsor = float(np.clip(sv, sv[k], sv[n - k - 1]).mean())
    return trimmed, winsor


# ---------------------------------------------------------------- 足ごとの材料

class FootData:
    """1 つの足について、門に依らない材料をすべて作る(足ごとに 1 回だけ)。"""

    def __init__(self, bars):
        self.bars = bars
        n = self.n = len(bars)
        self.ts = ts = np.fromiter((b[0] for b in bars), dtype=np.int64, count=n)
        self.close = close = np.fromiter((b[4] for b in bars), dtype=np.float64, count=n)
        self.day = day = ts // 86400
        self.week = ts // (7 * 86400)                    # 週ブロック = day // 7
        self.hour = ((ts % 86400) // 3600).astype(np.int64)
        self.wday = ((day + 3) % 7).astype(np.int64)     # 1970-01-01 は木曜(weekday=3)
        # 年・月・ISO 週は「日」だけで決まるので、日の一覧について 1 回だけ暦を引く
        uday, dinv = np.unique(day, return_inverse=True)
        dinv = dinv.astype(np.int64).ravel()
        cal = [datetime.utcfromtimestamp(int(d) * 86400) for d in uday]
        self.year = np.array([c.year for c in cal], dtype=np.int64)[dinv]
        self.month = np.array([c.month for c in cal], dtype=np.int64)[dinv]
        self.ymonth = self.year * 12 + self.month                     # 月ブロック(暦月)
        self.isoweek = np.array([c.isocalendar()[1] for c in cal], dtype=np.int64)[dinv]

        # 形(向き・勝った側のヒゲ・実体)は body_wick と同じ関数から取る
        shape = [bw.direction_and_shape(o, h_, l, c) for (_t, o, h_, l, c) in bars]
        self.shape_sig = np.fromiter((s[0] for s in shape), dtype=np.int64, count=n)
        w = np.fromiter((s[1] for s in shape), dtype=np.float64, count=n)
        body = np.fromiter((s[2] for s in shape), dtype=np.float64, count=n)
        del shape
        with np.errstate(divide="ignore", invalid="ignore"):
            self.wbp = np.where(close > 0, w / close * 1e4, np.nan)
            self.body_bp = np.where(close > 0, body / close * 1e4, np.nan)
            self.ratio = np.where(w > 0, body / np.where(w > 0, w, 1.0), np.nan)
        self.body_gt_wick = body > w
        self.wick_bin = bin_index(self.wbp, bw.WICK_BINS)
        self.ratio_bin = bin_index(self.ratio, bw.RATIO_BINS)

        # 古い終値(D4)。i=0 は stale でない
        stale = np.zeros(n, dtype=bool)
        if n > 1:
            stale[1:] = close[1:] == close[:-1]
        self.stale = stale

        # 直前 100 本のボラ(D8)。|log(close[j]/close[j-1])| × 1e4 の平均、j = i-100..i-1。
        # **先読み無し**。j-1 >= 0 が要るので i >= 101 の足だけ値を持つ
        lr = np.zeros(n, dtype=np.float64)
        if n > 1:
            with np.errstate(divide="ignore", invalid="ignore"):
                lr[1:] = np.abs(np.log(close[1:] / close[:-1])) * 1e4
        cs = np.cumsum(lr)                       # cs[k] = Σ_{j<=k} lr[j](lr[0] = 0)
        vol = np.full(n, np.nan)
        if n > VOL_WINDOW + 1:
            i0 = VOL_WINDOW + 1
            vol[i0:] = (cs[i0 - 1:n - 1] - cs[:n - i0]) / VOL_WINDOW
        self.vol_prev = vol

        # 全足の bp リターン(D10 の realized vol)
        bpret = np.full(n, np.nan)
        if n > 1:
            bpret[1:] = (close[1:] / close[:-1] - 1.0) * 1e4
        self.bpret = bpret

        # 前方リターン。第 4 部と同じ条件(i < n−h かつ close[i] > 0)でのみ有効
        self.fwd, self.fwd_delayed = {}, {}
        for h in HORIZONS:
            a = np.full(n, np.nan)
            if n > h:
                ok = close[:n - h] > 0
                a[:n - h] = np.where(ok, (close[h:] / np.where(ok, close[:n - h], 1.0) - 1.0) * 1e4,
                                     np.nan)
            self.fwd[h] = a
            # D3: 1 本遅らせた入口(h >= 2)。i+h < n かつ i+1 < n
            b = np.full(n, np.nan)
            if h >= 2 and n > h:
                den = close[1:n - h + 1]
                ok = den > 0
                b[:n - h] = np.where(ok, (close[h:] / np.where(ok, den, 1.0) - 1.0) * 1e4, np.nan)
            self.fwd_delayed[h] = b


# ---------------------------------------------------------------- 診断の部品

def bin_stats(codes: np.ndarray, r: np.ndarray, folder: Folder, name_prefix: str,
              names=None, extra=None, reps=REPS_SMALL):
    """層ごとの n / mean / ci95(日ブロック)。`extra` は {列名: 値の配列}。"""
    out = {}
    for code in sorted(set(codes.tolist())):
        m = codes == code
        rv = r[m]
        if rv.size == 0:
            continue
        _u, s, c = folder.fold(m)
        lab = str(code) if names is None else names[int(code)]
        d = {"n": int(rv.size), "mean_bp": rnd(mean_of(rv)),
             "ci95_bp": rnd2(np_boot(s, c, f"{name_prefix}|{lab}", reps)),
             "days": int(s.size)}
        if extra:
            for col, arr in extra.items():
                av = arr[m]
                av = av[~np.isnan(av)]
                d[col] = rnd(float(av.mean()) if av.size else None)
        out[lab] = d
    return out


def d11_of(vals: np.ndarray):
    out = {"mean_bp": rnd(mean_of(vals)), "n": int(vals.size)}
    for q in TRIMS:
        t, w = trimmed_and_winsor(vals, q)
        tag = f"{int(q * 100)}pct"
        out[f"trim_{tag}_bp"] = rnd(t)
        out[f"winsor_{tag}_bp"] = rnd(w)
    return out


def build_cell(fd: FootData, key: str, sub: np.ndarray, sg: np.ndarray, h: int, edges):
    """1 セル(足 × 門 × 強さ × h)の D1〜D11。`sub` はシグナル足の添字(昇順)。"""
    r_all = sg * fd.fwd[h][sub]
    ok = ~np.isnan(r_all)
    idx = sub[ok]
    r = r_all[ok]
    if r.size < MIN_N:
        return None
    day, year = fd.day[idx], fd.year[idx]
    years = [int(y) for y in np.unique(year)]
    ykeys = [str(y) for y in years]
    ymask = {str(y): (year == y) for y in years}
    fday = Folder(day, r)
    cell = {}

    # --- D1 基準線(原典の day_bootstrap + cell_rng。key も第 4 部と同じ)
    u, s, c = fday.fold()
    lo, hi = day_bootstrap({int(a): float(b) for a, b in zip(u, s)},
                           {int(a): int(b) for a, b in zip(u, c)}, cell_rng(key))
    per_year = {}
    for y in ykeys:
        m = ymask[y]
        uy, sy, cy = fday.fold(m)
        ylo, yhi = day_bootstrap({int(a): float(b) for a, b in zip(uy, sy)},
                                 {int(a): int(b) for a, b in zip(uy, cy)}, cell_rng(key, y))
        per_year[y] = {"n": int(m.sum()), "mean_bp": rnd(mean_of(r[m]), 3),
                       "ci95_bp": rnd2((ylo, yhi), 3), "days": int(uy.size)}
    cell["d1"] = {"n": int(r.size), "mean_bp": rnd(mean_of(r)),
                  "ci95_bp": rnd2((lo, hi)), "days": int(u.size), "per_year": per_year}

    # --- D2 区間の頑健性(ブロックの取り方を変える。numpy 版)
    fweek = Folder(fd.week[idx], r)
    fmon = Folder(fd.ymonth[idx], r)
    _uw, sw, cw = fweek.fold()
    _um, sm, cm = fmon.fold()
    d2 = {"blocks": {"day": int(u.size), "week": int(_uw.size), "month": int(_um.size)},
          "day_1000": rnd2(np_boot(s, c, f"D2|day|{key}", REPS_LARGE)),
          "week_200": rnd2(np_boot(sw, cw, f"D2|week|{key}", REPS_SMALL)),
          "week_1000": rnd2(np_boot(sw, cw, f"D2|week1000|{key}", REPS_LARGE)),
          "month_200": rnd2(np_boot(sm, cm, f"D2|month|{key}", REPS_SMALL)),
          "per_year": {}}
    for y in ykeys:
        uy, sy, cy = fweek.fold(ymask[y])
        d2["per_year"][y] = {"week_200": rnd2(np_boot(sy, cy, f"D2|week|{key}|{y}"), 3),
                             "blocks": int(uy.size)}
    cell["d2"] = d2

    # --- D3 1 本遅らせた入口(h >= 2)
    cell["d3"] = None
    if h >= 2:
        rd_all = sg * fd.fwd_delayed[h][sub]
        okd = ~np.isnan(rd_all)
        idxd, rd = sub[okd], rd_all[okd]
        if rd.size:
            dday, dyear = fd.day[idxd], fd.year[idxd]
            fd3 = Folder(dday, rd)
            _u3, s3, c3 = fd3.fold()
            py = {}
            for y in [int(x) for x in np.unique(dyear)]:
                m = dyear == y
                _u2, s2, c2 = fd3.fold(m)
                py[str(y)] = {"n": int(m.sum()), "mean_bp": rnd(mean_of(rd[m]), 3),
                              "ci95_bp": rnd2(np_boot(s2, c2, f"D3|{key}|{y}"), 3)}
            cell["d3"] = {"n": int(rd.size), "mean_bp": rnd(mean_of(rd)),
                          "ci95_bp": rnd2(np_boot(s3, c3, f"D3|{key}")), "per_year": py}

    # --- D4 古い終値の除外
    st = fd.stale[idx]
    keep = ~st
    py = {}
    for y in ykeys:
        m = ymask[y]
        mk = m & keep
        n_m = int(m.sum())
        if mk.any():
            _u2, s2, c2 = fday.fold(mk)
            ci = rnd2(np_boot(s2, c2, f"D4|{key}|{y}"), 3)
        else:
            ci = [None, None]
        py[y] = {"n_all": n_m, "n_stale": int((m & st).sum()),
                 "stale_share": rnd((m & st).sum() / n_m if n_m else None, 5),
                 "n_kept": int(mk.sum()), "mean_bp": rnd(mean_of(r[mk]), 3), "ci95_bp": ci}
    if keep.any():
        _uk, sk, ck = fday.fold(keep)
        ci_all = rnd2(np_boot(sk, ck, f"D4|{key}"))
    else:
        ci_all = [None, None]
    cell["d4"] = {"n_all": int(r.size), "n_stale": int(st.sum()),
                  "stale_share": rnd(st.sum() / r.size, 5), "n_kept": int(keep.sum()),
                  "mean_bp": rnd(mean_of(r[keep])), "ci95_bp": ci_all, "per_year": py}

    # --- D5 分割の一致(年内で符号が揃うか)
    iso, mon = fd.isoweek[idx], fd.month[idx]
    d5 = {"per_year": {}, "same_sign_years": {"week_parity": 0, "half": 0},
          "n_years": len(ykeys)}
    for y in ykeys:
        m = ymask[y]
        rec = {}
        for split, parts in (("week_parity", (("even", iso % 2 == 0), ("odd", iso % 2 == 1))),
                             ("half", (("h1", mon <= 6), ("h2", mon > 6)))):
            got = {}
            for lab, cond in parts:
                mm = m & cond
                got[lab] = {"n": int(mm.sum()), "mean_bp": rnd(mean_of(r[mm]), 3)}
            a, b = got[parts[0][0]]["mean_bp"], got[parts[1][0]]["mean_bp"]
            same = bool(a is not None and b is not None and a * b > 0)
            got["same_sign"] = same
            if same:
                d5["same_sign_years"][split] += 1
            rec[split] = got
        d5["per_year"][y] = rec
    cell["d5"] = d5

    # --- D6 UTC 3 時間 × 8 区分
    hb = fd.hour[idx] // 3
    d6 = {"bins": bin_stats(hb, r, fday, f"D6|{key}"), "per_year": {},
          "funding_bins": sorted({int(x // 3) for x in FUNDING_HOURS})}
    for y in ykeys:
        m = ymask[y]
        d6["per_year"][y] = bin_stats(hb[m], r[m], Folder(day[m], r[m]), f"D6|{key}|{y}")
    cell["d6"] = d6

    # --- D7 UTC 曜日
    cell["d7"] = {"bins": bin_stats(fd.wday[idx], r, fday, f"D7|{key}")}

    # --- D8 ボラ三分位(境目は足 × 門で決めたものを受け取る)
    vol, wbp = fd.vol_prev[idx], fd.wbp[idx]
    have = ~np.isnan(vol)
    if edges is None or not have.any():
        cell["d8"] = {"edges": None, "n_no_vol": int((~have).sum()), "bins": {}, "per_year": {}}
    else:
        q1, q2 = edges
        code = np.where(vol < q1, 0, np.where(vol < q2, 1, 2)).astype(np.int16)
        names8 = ["low", "mid", "high"]
        d8 = {"edges": [rnd(q1), rnd(q2)], "n_no_vol": int((~have).sum()),
              "bins": bin_stats(code[have], r[have], Folder(day[have], r[have]), f"D8|{key}",
                                names=names8,
                                extra={"mean_vol_prev": vol[have], "mean_wbp": wbp[have]}),
              "per_year": {}}
        for y in ykeys:
            m = ymask[y] & have
            if not m.any():
                continue
            d8["per_year"][y] = bin_stats(code[m], r[m], Folder(day[m], r[m]), f"D8|{key}|{y}",
                                          names=names8,
                                          extra={"mean_vol_prev": vol[m], "mean_wbp": wbp[m]})
        cell["d8"] = d8

    # --- D9 ヒゲ層 / D9b 実体比の層
    wcode, rcode = fd.wick_bin[idx], fd.ratio_bin[idx]
    ratio = fd.ratio[idx]
    with np.errstate(divide="ignore", invalid="ignore"):
        r_over_w = np.where(wbp > 0, r / np.where(wbp > 0, wbp, 1.0), np.nan)
    d9 = {"bins": bin_stats(wcode, r, fday, f"D9|{key}", names=WICK_LABELS,
                            extra={"mean_wbp": wbp, "mean_r_over_wbp": r_over_w}),
          "per_year": {},
          "note": "mean_r_over_wbp は r_h / wbp の平均。**派生量**であって bp ではない"}
    d9b = {"bins": bin_stats(rcode, r, fday, f"D9b|{key}", names=RATIO_LABELS,
                             extra={"mean_ratio": ratio}),
           "per_year": {}}
    for y in ykeys:
        m = ymask[y]
        fy = Folder(day[m], r[m])
        d9["per_year"][y] = bin_stats(wcode[m], r[m], fy, f"D9|{key}|{y}", names=WICK_LABELS,
                                      extra={"mean_wbp": wbp[m], "mean_r_over_wbp": r_over_w[m]})
        d9b["per_year"][y] = bin_stats(rcode[m], r[m], fy, f"D9b|{key}|{y}", names=RATIO_LABELS,
                                       extra={"mean_ratio": ratio[m]})
    cell["d9"] = d9
    cell["d9b"] = d9b

    # --- D11 裾を落とした平均(区間は出さない)
    cell["d11"] = dict(d11_of(r), per_year={y: d11_of(r[ymask[y]]) for y in ykeys})
    return cell


def year_components(fd: FootData, sub: np.ndarray, strong: np.ndarray):
    """D10 年の成分表。**引き算をしない**(横に並べるだけ)。"""
    out = {}
    ysig = fd.year[sub]
    for y in [int(x) for x in np.unique(fd.year)]:
        mb = fd.year == y
        bp = fd.bpret[mb]
        bp = bp[~np.isnan(bp)]
        ms = ysig == y
        n_sig, n_bars = int(ms.sum()), int(mb.sum())
        st = strong[ms]
        bgw = fd.body_gt_wick[sub][ms]
        out[str(y)] = {
            "n_bars": n_bars,
            "realized_vol_bp": rnd(float(np.abs(bp).mean()) if bp.size else None),
            "n_signals": n_sig,
            "signal_share": rnd(n_sig / n_bars if n_bars else None, 5),
            "mean_wbp": rnd(float(np.nanmean(fd.wbp[sub][ms])) if n_sig else None),
            "mean_abs_body_bp": rnd(float(np.nanmean(fd.body_bp[sub][ms])) if n_sig else None),
            "n_strong": int(st.sum()),
            "strong_body_gt_wick_share": rnd(bgw[st].sum() / st.sum() if st.sum() else None, 5),
        }
    return out


# ---------------------------------------------------------------- 再現ゲート

def check_repro(key: str, cell: dict, ref: dict):
    """D1 が `signal_horizon.json` の該当セルと全部一致するか。"""
    rc = ref.get(key)
    if rc is None:
        return {"key": key, "ok": None, "why": "参照セルが無い"}
    d1 = cell["d1"]
    bad = []
    for f in ("n", "mean_bp", "ci95_bp"):
        if d1[f] != rc[f]:
            bad.append([f, d1[f], rc[f]])
    for y, p in rc.get("per_year", {}).items():
        q = d1["per_year"].get(y)
        if q is None:
            bad.append([f"per_year[{y}]", None, p["n"]])
            continue
        for f in ("n", "mean_bp", "ci95_bp"):
            if q[f] != p[f]:
                bad.append([f"per_year[{y}].{f}", q[f], p[f]])
    return {"key": key, "ok": not bad, "n": d1["n"], **({"mismatch": bad} if bad else {})}


# ---------------------------------------------------------------- 本体

def dump_cell(path: Path, fd: FootData, sub, sg, strengths, h):
    """1 セルのシグナル足ごとの行を CSV に書く(検査者用。リポジトリには置かない)。"""
    r = sg * fd.fwd[h][sub]
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["i", "ts", "sig", "strength", "r_h", "day", "year", "hour", "wday",
                     "wbp", "body_bp", "stale_close", "vol_prev"])
        for k in range(int(sub.size)):
            i = int(sub[k])
            wr.writerow([i, int(fd.ts[i]), int(sg[k]), strengths[k],
                         "" if np.isnan(r[k]) else repr(float(r[k])),
                         int(fd.day[i]), int(fd.year[i]), int(fd.hour[i]), int(fd.wday[i]),
                         repr(float(fd.wbp[i])), repr(float(fd.body_bp[i])),
                         int(bool(fd.stale[i])),
                         "" if np.isnan(fd.vol_prev[i]) else repr(float(fd.vol_prev[i]))])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--feet", type=int, nargs="+", default=list(FEET))
    ap.add_argument("--out", default=None)
    ap.add_argument("--dump-cell", default=None,
                    help='CSV に落とすセル(例 "5|s19/b24|weak|3")')
    ap.add_argument("--dump-path", default=None)
    k1_source.add_source_args(ap)
    args = ap.parse_args()
    start, end = k1_source.resolve_range(args)
    if args.source == "bitmex":
        # 封印: BitMEX の判定区間 2020-2021 には触れない
        assert end <= SEAL_END, f"BitMEX の封印: end は {SEAL_END} 以下でなければならない ({end})"
    if args.out is None:
        args.out = str(k1_source.out_dir(args.source) / "robustness.json")
    ref_path = k1_source.out_dir(args.source) / "signal_horizon.json"
    ref = json.loads(ref_path.read_text("utf-8"))["cells"] if ref_path.exists() else {}

    t0 = time.time()
    print(f"{args.source} 区間 {start} 〜 {end}(BitMEX は封印により end <= {SEAL_END})")
    seconds = k1_source.load_bars(args.source, start, end)
    print(f"  バー {len(seconds):,} 行 / 族 = 足 {len(args.feet)} × 門 {len(GATES)}"
          f" × 強さ {len(STRENGTHS)} × h {len(HORIZONS)}"
          f" = {len(args.feet) * len(GATES) * len(STRENGTHS) * len(HORIZONS)} セル"
          f" / 参照 {ref_path.name} {len(ref)} セル", flush=True)

    cells: dict[str, dict] = {}
    repro: list[dict] = []
    comps: dict[str, dict] = {}
    skipped: list[str] = []

    for foot in args.feet:
        t1 = time.time()
        fd = FootData(base.fold(seconds, foot))
        n0 = len(cells)
        for gname, (small, big) in GATES.items():
            sg_all = eff.signals(fd.bars, small, big)
            sub_all = np.fromiter((i for i, x in enumerate(sg_all) if x[0] != 0), dtype=np.int64)
            if sub_all.size == 0:
                continue
            sig_all = np.fromiter((sg_all[int(i)][0] for i in sub_all), dtype=np.int64,
                                  count=sub_all.size)
            strong_all = np.fromiter((sg_all[int(i)][3] == "strong" for i in sub_all),
                                     dtype=bool, count=sub_all.size)
            del sg_all
            # 形は eff.signals と一致していなければならない(body_wick と同じ検査)
            assert np.array_equal(fd.shape_sig[sub_all], sig_all), (foot, gname, "向きの不一致")

            comps[f"{foot}|{gname}"] = year_components(fd, sub_all, strong_all)

            # D8 の三分位: 足 × 門 × **全シグナル足(strong+weak)** の全期間分布で切る
            # (numpy の既定 = 線形補間)
            v = fd.vol_prev[sub_all]
            v = v[~np.isnan(v)]
            edges = (float(np.quantile(v, 1 / 3)), float(np.quantile(v, 2 / 3))) if v.size else None

            for keep in STRENGTHS:
                m = strong_all if keep == "strong" else (
                    ~strong_all if keep == "weak" else np.ones(sub_all.size, dtype=bool))
                sub, sg = sub_all[m], sig_all[m]
                if sub.size < MIN_N:
                    continue
                for h in HORIZONS:
                    key = f"{foot}|{gname}|{keep}|{h}"
                    cell = build_cell(fd, key, sub, sg, h, edges)
                    if cell is None:
                        skipped.append(key)
                        continue
                    cell.update({"foot": foot, "gate": gname, "strength": keep, "h": h})
                    cells[key] = cell
                    repro.append(check_repro(key, cell, ref))
                    if args.dump_cell == key and args.dump_path:
                        dump_cell(Path(args.dump_path), fd, sub, sg,
                                  np.where(strong_all[m], "strong", "weak"), h)
                        print(f"  セル {key} を {args.dump_path} に書いた({sub.size:,} 行)")
        ok = sum(1 for x in repro if x["ok"])
        n_gate = sum(1 for x in repro if x["ok"] is not None)
        print(f"  {foot:>3}分 完了({len(cells) - n0} セル, {time.time() - t1:.0f} 秒)"
              f" 再現ゲート累計 {ok}/{n_gate}", flush=True)
        del fd

    bad = [x for x in repro if x["ok"] is False]
    if bad:
        head = "\n".join(f"  {x['key']}: {x['mismatch']}" for x in bad[:10])
        raise SystemExit(f"再現ゲート不一致 {len(bad)} セル:\n{head}")

    Path(args.out).write_text(json.dumps({
        "note": ("K1 深掘り §1 の診断 D1〜D11。判定・帰無・MDE・判定バーは作らない。"
                 "経費は引かない。引き算をせず成分を横に並べる。"
                 "D1 は第 4 部と同じ量・同じ乱数で、再現ゲートで一致を確認済み。"),
        "source": args.source,
        "explore": [start.isoformat(), end.isoformat()],
        "load": k1_source.last_load,
        "gates": list(GATES),
        "feet": list(args.feet),
        "strengths": list(STRENGTHS),
        "horizons": list(HORIZONS),
        "seed": SEED,
        "bootstrap": {"d1_reps": 200, "np_small": REPS_SMALL, "np_large": REPS_LARGE,
                      "vol_window": VOL_WINDOW, "trims": list(TRIMS),
                      "wick_bins": list(bw.WICK_BINS), "ratio_bins": list(bw.RATIO_BINS)},
        "reference": str(ref_path),
        "reproduction_gate": repro,
        "skipped_cells": skipped,
        "per_year_components": comps,
        "cells": cells,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for x in repro if x["ok"])
    n_gate = sum(1 for x in repro if x["ok"] is not None)
    print(f"\n再現ゲート {ok}/{n_gate} 一致。セル {len(cells)} 件"
          f"({time.time() - t0:.0f} 秒)→ {args.out}")


if __name__ == "__main__":
    main()
