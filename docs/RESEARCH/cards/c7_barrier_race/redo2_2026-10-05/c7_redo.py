"""カード 7(バリアレース逆張り)の分析のやり直し(2026-10-05)。保存済みの measure/<窓>/run.npz・daily.csv・extra.json だけを読む。
走らせ直しではない。台本そのものの試験は無い(【試験の無い台本の値】)。
    PYTHONPATH=src python3 docs/RESEARCH/cards/c7_barrier_race/redo2_2026-10-05/c7_redo.py
出力: このフォルダの C7_TABLES.md・trades_<窓>/trades.csv.gz

- 取引の行: extra.json の式どおり(同じ向きの持ち高が続いた区間 = 1 取引)。本数・和を extra.json と照らす。
  このカードでは持ち高は ±1 で入れ替わり、同じ側の線にまた当たった(継続)ときは持ち高が変わらないので、取引 = 反転から次の反転まで。
- 決定ごと(持ち高 ≠ 0): 損益 P_t(始値 → 始値)と、中ほどの値((高値 + 安値) ÷ 2)の t+1 → t+2、対照(24 時間後の同じ時刻の足どうし・同じ向き)。
  向きが変わった決定・持ち続けた決定・全部 × 全期間・前半・後半。1 決定あたり、区間は日の塊(群の和 ÷ 群の数)。
- 取引ごと: 買い・売り × 本体(約定の始値 → 出の始値)・対照(24 時間後の同じ時刻から同じ向き、同じ長さ)・本体 − 対照、全期間・前半・後半。
- D2: 前の日(日本時間)の荒れ具合(vol_split_daily.classify)× 前半・後半、1 日あたり(daily.csv)。
日 = 決定の時刻(足の終わり)の日本時間の日(measure と同じ)。前半・後半の境は daily.csv の日の数で 2 つ。
"""
import collections
import csv
import gzip
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/home/user/trade"
sys.path.insert(0, os.path.join(REPO, "scripts/analysis"))
sys.path.insert(0, os.path.join(REPO, "scripts/w4_measure"))
sys.path.insert(0, os.path.join(REPO, "src"))
import diag_tables as dt  # noqa: E402

NS, MIN, DAY = 10**9, 60 * 10**9, 86400 * 10**9
M = os.path.join(HERE, "..", "measure")


def iso(ns):
    return datetime.fromtimestamp(int(ns) / 1e9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def jday_arr(ns):
    """日本時間の日の番号(1970-01-01 からの日数、整数)。文字列にしない(速さのため)。"""
    return ((ns // NS + 9 * 3600) // 86400).astype(np.int64)


def dnum(s):
    return (date.fromisoformat(s) - date(1970, 1, 1)).days


def ratio_by_day(dayarr, vals, pd):
    nums = np.array([dnum(x) for x in pd], dtype=np.int64)
    lo_, hi_ = int(nums.min()), int(nums.max())
    q = (dayarr >= lo_) & (dayarr <= hi_)
    sums = np.bincount(dayarr[q] - lo_, weights=vals[q], minlength=hi_ - lo_ + 1)
    cnts = np.bincount(dayarr[q] - lo_, minlength=hi_ - lo_ + 1)
    s = {x: float(sums[n - lo_]) for x, n in zip(pd, nums)}
    c = {x: int(cnts[n - lo_]) for x, n in zip(pd, nums)}
    return dt.group_ratio_ci(pd, s, c)


def main():
    out = ["# カード 7 のやり直しの表(保存済みの出力から。損益は %(建玉を掛けた損益の率。L-920 で bp は値動き率だけの名前)、経費の前、成行・次の足の始値で約定)", ""]
    import pickle
    cache = os.environ.get("C7_CLS_CACHE")  # 速さのため: 区分(vol_split_daily.classify の戻り値)を保存した pickle があれば使う
    if cache and os.path.exists(cache):
        cls = pickle.load(open(cache, "rb"))
    else:
        import vol_split_daily as vs
        cls = vs.classify(vs.daily_vol(vs.load_closes_by_day()))
    f = lambda q: "—" if q["per_trade"] is None else (f"{q['per_trade']:+.5f}" + ("" if q["lo"] is None else f" [{q['lo']:+.5f}, {q['hi']:+.5f}]"))  # noqa: E731
    d2 = ["## D2 前の日(日本時間)の荒れ具合 × 前半・後半(1 日あたり %、daily.csv)", "", "| 窓 | 区分 | 全期間: 日数・1 日あたり [区間] | 前半 | 後半 |", "|---|---|---|---|---|"]
    dec_t = ["## 決定ごと(持ち高 ≠ 0)。始値 → 始値(= 損益 P_t)・中ほどの値・対照(24 時間後)(%/決定)", "",
             "| 窓 | 決定 | 期間 | 決定の数 | 始値 → 始値 [区間] | 始値の対照 | 始値 本体 − 対照 [区間] | 中ほど 本体 [区間] | 中ほど 本体 − 対照 [区間] |",
             "|---|---|---|---|---|---|---|---|---|"]
    tr_t = ["## 取引ごと: 買い・売り × 本体(約定の始値 → 出の始値)・対照(24 時間後の同じ時刻から同じ向き・同じ長さ)(%/取引)", "",
            "| 窓 | 向き | 期間 | 取引 | 本体 [区間] | 対照 [区間] | 本体 − 対照 [区間] |", "|---|---|---|---|---|---|---|"]
    import time
    for v in os.environ.get("C7_WINDOWS", "1h,1d,1w").split(","):
        print(v, "start", time.strftime("%H:%M:%S"), flush=True)
        _z = np.load(os.path.join(M, v, "run.npz"))
        z = {k_: _z[k_] for k_ in _z.files}  # 圧縮された npz は z[名前] のたびに解き直すので、最初に 1 回だけ読む
        d = np.flatnonzero(z["decided"])
        m = len(d) - 2
        bar, fill, ex = d[:m], d[1:m + 1], d[2:m + 2]
        op, hi, lo = z["open"], z["high"], z["low"]
        e = z["exposure"][bar]
        p = e * (op[ex] / op[fill] - 1) * 100
        mid = (hi + lo) / 2
        pm = e * (mid[ex] / mid[fill] - 1) * 100
        s = np.sign(e)
        prev = np.concatenate([[0.0], s[:-1]])
        days_all = sorted(l.split(",")[0] for l in open(os.path.join(M, v, "daily.csv")).read().splitlines()[1:])
        half = len(days_all) // 2
        parts = {"全期間": days_all, "前半": days_all[:half], "後半": days_all[half:]}
        pset = {k: np.array(sorted(dnum(y) for y in x), dtype=np.int64) for k, x in parts.items()}
        dayarr = jday_arr(z["end_ns"][bar])
        # 対照: 約定の足の始まり + 24 時間 の足と、その次の空でない足
        s_dec = z["start_ns"][d]
        j = np.searchsorted(s_dec, z["start_ns"][fill] + DAY, side="left")
        okc = (j + 1 < len(s_dec))
        j = np.minimum(j, len(s_dec) - 2)
        okc &= (s_dec[j] - (z["start_ns"][fill] + DAY)) < 5 * MIN
        ctrl = e * (op[d][j + 1] / op[d][j] - 1) * 100
        mctrl = e * (mid[d][j + 1] / mid[d][j] - 1) * 100
        # 取引の行
        rows, i = [], 0
        while i < m:
            if s[i] == 0:
                i += 1
                continue
            k = i
            while k + 1 < m and s[k + 1] == s[i]:
                k += 1
            rows.append((i, k))
            i = k + 1
        ext = json.load(open(os.path.join(M, v, "extra.json")))["trades"]
        out.append(f"- {v}: 作り直した取引 {len(rows)} 本・和 {sum(p[a:b + 1].sum() for a, b in rows):+,.3f}(extra.json: 買い {ext['long']['n']}・売り {ext['short']['n']}、作り直し: 買い {sum(1 for a, _ in rows if s[a] > 0)})。"
                   f"P_t の合計 {p.sum():+,.3f}、持ち高 ≠ 0 の決定 {int((s != 0).sum()):,}、向きが変わった決定 {int(((s != 0) & (s != prev)).sum()):,}・その和 {p[(s != 0) & (s != prev)].sum():+,.3f}")
        os.makedirs(os.path.join(HERE, f"trades_{v}"), exist_ok=True)
        with gzip.open(os.path.join(HERE, f"trades_{v}", "trades.csv.gz"), "wt", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["signal_t", "entry_t", "exit_t", "side", "entry_price", "pnl_pct"])
            for a, b in rows:
                w.writerow([iso(z["end_ns"][bar[a]]), iso(z["start_ns"][fill[a]]), iso(z["start_ns"][ex[b]]), int(s[a]), f"{op[fill[a]]:.1f}", f"{p[a:b + 1].sum():.8f}"])
        for nm, msk in (("向きが変わった", (s != 0) & (s != prev)), ("持ち続けた", (s != 0) & (s == prev)), ("全部", s != 0)):
            mm = msk & okc
            for pn in parts:
                q = mm & np.isin(dayarr, pset[pn])
                r1 = ratio_by_day(dayarr[q], p[q], parts[pn])
                rc = ratio_by_day(dayarr[q], ctrl[q], parts[pn])
                rd = ratio_by_day(dayarr[q], p[q] - ctrl[q], parts[pn])
                rm = ratio_by_day(dayarr[q], pm[q], parts[pn])
                rmd = ratio_by_day(dayarr[q], pm[q] - mctrl[q], parts[pn])
                dec_t.append(f"| {v} | {nm} | {pn} | {int(q.sum()):,} | {f(r1)} | {f(rc)} | {f(rd)} | {f(rm)} | {f(rmd)} |")
        # 取引ごと
        o_dec = op[d]
        st = np.array([z["start_ns"][fill[a]] for a, _ in rows])
        en = np.array([z["start_ns"][ex[b]] for _, b in rows])
        sd = np.array([s[a] for a, _ in rows])
        body = np.array([p[a:b + 1].sum() for a, b in rows])
        tday = jday_arr(np.array([z["end_ns"][bar[a]] for a, _ in rows]))

        def open_at(ns):
            jj = np.searchsorted(s_dec, ns, side="left")
            ok = jj < len(s_dec)
            jj = np.minimum(jj, len(s_dec) - 1)
            ok &= (s_dec[jj] - ns) < 5 * MIN
            return o_dec[jj], ok
        c0, ok0 = open_at(st + DAY)
        c1, ok1 = open_at(en + DAY)
        cbody = sd * (c1 / c0 - 1) * 100
        okt = ok0 & ok1
        for side_name, smask in (("全部", np.ones(len(rows), bool)), ("買い", sd > 0), ("売り", sd < 0)):
            for pn in parts:
                q = okt & smask & np.isin(tday, pset[pn])
                rb = ratio_by_day(tday[q], body[q], parts[pn])
                rc = ratio_by_day(tday[q], cbody[q], parts[pn])
                rd = ratio_by_day(tday[q], body[q] - cbody[q], parts[pn])
                tr_t.append(f"| {v} | {side_name} | {pn} | {int(q.sum()):,} | {f(rb)} | {f(rc)} | {f(rd)} |")
        # D2
        daily = {}
        dl = open(os.path.join(M, v, "daily.csv")).read().splitlines()
        k_ = 100.0 if dl[0] == "day,pnl_bp,n" else 1.0  # L-920 より前の daily.csv は率 × 1 万
        for line in dl[1:]:
            dd, pp, _n = line.split(",")
            daily[dd] = float(pp) / k_
        for c_ in ("low", "mid", "high", None):
            cells = []
            for pn, pdays in parts.items():
                x = [daily[dd] for dd in pdays if cls.get(dd) == c_]
                r_ = dt.mean_ci(x) if len(x) >= 10 else {"mean": float(np.mean(x)) if x else None, "lo": None}
                cells.append(f"{len(x)}・" + ("—" if r_["mean"] is None else (f"{r_['mean']:+.4f}" + ("" if r_.get("lo") is None else f" [{r_['lo']:+.4f}, {r_['hi']:+.4f}]"))))
            d2.append(f"| {v} | {({'low': '低', 'mid': '中', 'high': '高'}).get(c_, '区分なし')} | {cells[0]} | {cells[1]} | {cells[2]} |")
    out += ["", f"前半・後半の境: {days_all[half]}", ""] + d2 + [""] + dec_t + [""] + tr_t
    open(os.path.join(HERE, "C7_TABLES.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
