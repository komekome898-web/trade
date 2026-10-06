"""# 11 の読み口: カード 7 の形を、# 7 の起点ごとの行(走らせ直しで git に残した記録)から作り直す。

事前登録 §4 の # 11 の行「カード 7 の形は流れを抜いた値でも並べる」の値が TABLES に無いので、ここで出す。
- 入力: `docs/RESEARCH/d1b/rerun_records_2026-10-06/records/7_card7_origins.csv.gz`(window, T, w_bp, side, minutes,
  prior_window_move)と、区分(g2lib.prev_day_class = vol_split_daily の daily_vol・classify。bitFlyer FX の 1 分足から。
  台本と同じ関数、同じ期間 2015-11-28T15Z〜2023-12-17T15Z)。
- 続き = side == prior_window_move(side ≠ 0・prior ≠ 0 の起点だけ。台本 g2_item11.c7_daily と同じ)。日 = T の日本時間の日。
- 流れを抜いた値 = (前が上の続きの割合 + 前が下の続きの割合) ÷ 2(# 7 の事前登録 §4 の主の量と同じ作り)。
- 区間 = 日の塊(g2lib._boot: 循環 5 日・1,000 回・種 20261006)。low − high は同じ日の抽き直しで両方を作る。
- 確かめ: 流れを抜かない値が TABLES.json の値と同じか(作り直しの確かめ)。
"""
import gzip, csv, json, os, sys
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "scripts", "d1b", "g2"), os.path.join(ROOT, "scripts", "w4_measure")]
import g2lib as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REC = os.path.join(ROOT, "docs/RESEARCH/d1b/rerun_records_2026-10-06/records/7_card7_origins.csv.gz")

CL = ("low", "mid", "high")


def main():
    lo, hi = L.iso_ns(L.PERIOD_FX[0]), L.iso_ns(L.PERIOD_FX[1])
    g = L.load_grid(lo, hi, log=lambda *a: None)
    cls = L.prev_day_class(g)
    days = L.Days.of(lo, hi)
    d0, nd = int(days.nums[0]), len(days.nums)
    # 日ごと × 窓 × 区分の無い形で: 前が上・前が下 の 続き・分母
    acc = {}
    mins = {}
    with gzip.open(REC, "rt") as fh:
        for r in csv.DictReader(fh):
            side, pr = int(r["side"]), int(r["prior_window_move"])
            if side == 0 or pr == 0:
                continue
            t = L.iso_ns(r["T"].replace("Z", "Z"))
            k = int(L.jst_day(np.int64(t))) - d0
            if not (0 <= k < nd):
                continue
            a = acc.setdefault(r["window"], {x: np.zeros(nd) for x in ("nu", "du", "nd", "dd")})
            mins.setdefault(r["window"], []).append((k, float(r["minutes"])))
            if pr > 0:
                a["du"][k] += 1; a["nu"][k] += (side == pr)
            else:
                a["dd"][k] += 1; a["nd"][k] += (side == pr)
    clsv = np.array([cls.get(int(d), "") for d in days.nums])
    tab = json.load(open(os.path.join(HERE, "..", "TABLES.json")))
    out = ["# # 11 カード 7 の形の作り直し(# 7 の起点ごとの行から。`c7_records.py`)", "",
           "続き = 当たった線の向き == 起点の前の窓の向き。流れを抜いた値 = (前が上の続きの割合 + 前が下の続きの割合) ÷ 2。"
           "区間 = 日の塊(循環 5 日・1,000 回・種 20261006)。日 = 起点の日本時間の日。", "",
           "## 1. 作り直しの確かめ(流れを抜かない値。TABLES.json と同じか)", "", "| 窓 | 期間 | 区分 | この読み口 | TABLES.json |", "|---|---|---|---|---|"]
    parts = days.parts()
    def sub(a, nums):
        k = np.asarray(nums) - d0
        return {x: v[k] for x, v in a.items()}, clsv[k]
    for w, a in acc.items():
        fname = [f for f in tab["forms"] if f"、{w}、" in f][0]
        for pn, nums in parts.items():
            s_, c_ = sub(a, nums)
            for c in CL:
                m = (c_ == c).astype(float)
                v = ((s_["nu"] + s_["nd"]) * m).sum() / ((s_["du"] + s_["dd"]) * m).sum()
                out.append(f"| {w} | {pn} | {c} | {v:.6f} | {tab['forms'][fname][pn][c]['est']:.6f} |")
    out += ["", "## 2. 流れを抜いた値の区分ごとと low − high", "", "| 窓 | 期間 | low | mid | high | low − high |", "|---|---|---|---|---|---|"]
    obj = {}
    for w, a in acc.items():
        for pn, nums in parts.items():
            s_, c_ = sub(a, nums)
            n = len(c_)
            def fr(i, c):
                m = (c_[i] == c)
                du, dd = s_["du"][i][m].sum(), s_["dd"][i][m].sum()
                if du <= 0 or dd <= 0:
                    return np.nan
                return (s_["nu"][i][m].sum() / du + s_["nd"][i][m].sum() / dd) / 2
            cells = []
            allidx = np.arange(n)
            for c in CL:
                est = fr(allidx, c); b = L._boot(n, lambda i, c=c: fr(i, c))
                cells.append(f"{est:+.3f} [{b['lo']:+.3f}, {b['hi']:+.3f}]")
            est = fr(allidx, "low") - fr(allidx, "high"); b = L._boot(n, lambda i: fr(i, "low") - fr(i, "high"))
            obj[f"{w}_{pn}"] = {"est": est, **b}
            out.append(f"| {w} | {pn} | " + " | ".join(cells) + f" | {est:+.3f} [{b['lo']:+.3f}, {b['hi']:+.3f}](MDE {b['mde']:.3f}) |")
    out += ["", "## 3. 年ごとの low − high(流れを抜かない値と抜いた値。区間は年の中の日の塊)", "",
            "| 窓 | 年 | low の日 | high の日 | 抜かない low − high | 抜いた low − high |", "|---|---|---|---|---|---|"]
    for w, a in acc.items():
        for y, nums in days.years().items():
            s_, c_ = sub(a, nums)
            nl, nh = int((c_ == "low").sum()), int((c_ == "high").sum())
            if nl == 0 or nh == 0:
                continue
            n = len(c_)
            def raw(i):
                ml, mh = c_[i] == "low", c_[i] == "high"
                return ((s_["nu"] + s_["nd"])[i][ml].sum() / (s_["du"] + s_["dd"])[i][ml].sum()
                        - (s_["nu"] + s_["nd"])[i][mh].sum() / (s_["du"] + s_["dd"])[i][mh].sum())
            def fl(i):
                r = []
                for c in ("low", "high"):
                    m = c_[i] == c
                    du, dd = s_["du"][i][m].sum(), s_["dd"][i][m].sum()
                    if du <= 0 or dd <= 0:
                        return np.nan
                    r.append((s_["nu"][i][m].sum() / du + s_["nd"][i][m].sum() / dd) / 2)
                return r[0] - r[1]
            ai = np.arange(n); br, bf = L._boot(n, raw), L._boot(n, fl)
            fmt = lambda e, b: f"{e:+.3f} [{b['lo']:+.3f}, {b['hi']:+.3f}]" if b["lo"] is not None else f"{e:+.3f}(区間なし)"
            out.append(f"| {w} | {y} | {nl} | {nh} | {fmt(raw(ai), br)} | {fmt(fl(ai), bf)} |")
    # 4. 年で層に分けた low − high(年ごとの low − high を、重み w_y = n_low・n_high ÷ (n_low + n_high)(日の数)で平均)
    out += ["", "## 4. 年で層に分けた low − high(区分の年の偏りを除く。重み = 年ごとの low・high の日の数の調和の半分。low と high の両方が 10 日以上ある年だけ)", "",
            "| 窓 | 期間 | 使った年 | 抜かない | 抜いた |", "|---|---|---|---|---|"]
    yrs_all = np.array([int(L.day_str(int(d))[:4]) for d in days.nums])
    for w, a in acc.items():
        for pn, nums in parts.items():
            s_, c_ = sub(a, nums)
            yk = yrs_all[np.asarray(nums) - d0]
            ys = [y for y in np.unique(yk) if ((c_ == "low") & (yk == y)).sum() >= 10 and ((c_ == "high") & (yk == y)).sum() >= 10]
            def strat(i, flow):
                num = den = 0.0
                for y in ys:
                    r = []
                    for c in ("low", "high"):
                        m = (c_[i] == c) & (yk[i] == y)
                        if flow:
                            du, dd = s_["du"][i][m].sum(), s_["dd"][i][m].sum()
                            if du <= 0 or dd <= 0:
                                return np.nan
                            r.append((s_["nu"][i][m].sum() / du + s_["nd"][i][m].sum() / dd) / 2)
                        else:
                            dn = (s_["du"] + s_["dd"])[i][m].sum()
                            if dn <= 0:
                                return np.nan
                            r.append((s_["nu"] + s_["nd"])[i][m].sum() / dn)
                    nl, nh = ((c_ == "low") & (yk == y)).sum(), ((c_ == "high") & (yk == y)).sum()
                    wy = nl * nh / (nl + nh)
                    num += wy * (r[0] - r[1]); den += wy
                return num / den
            n = len(c_); ai = np.arange(n)
            cells = []
            for flow in (False, True):
                e = strat(ai, flow); b = L._boot(n, lambda i, flow=flow: strat(i, flow))
                cells.append(f"{e:+.4f} [{b['lo']:+.4f}, {b['hi']:+.4f}]" if b["lo"] is not None else f"{e:+.3f}(区間なし: {b['why']})")
            out.append(f"| {w} | {pn} | {','.join(str(y) for y in ys)} | " + " | ".join(cells) + " |")
    # 5. 1 週の線の依存(相方 01 の指摘 1): レースの長さの分位・区分ごとの週の数・塊を長くした区間(結果を見た後の選び = 探索)
    out += ["", "## 5. 1 週の線の依存の大きさ(相方の指摘で足した。塊を長くした区間は結果を見た後の選び = 探索)", "",
            "| 区分 | 起点 | 起点のある週(暦の週)| 当たるまでの分 25/50/75/90 % 点 |", "|---|---|---|---|"]
    ks = np.array([k for k, _ in mins["1w"]]); ms = np.array([m for _, m in mins["1w"]])
    wk = (days.nums[ks] + 3) // 7  # 1970-01-01 は木曜。+3 で月曜始まりの週の番号
    for c in CL:
        m = clsv[ks] == c
        q = np.percentile(ms[m], [25, 50, 75, 90])
        out.append(f"| {c} | {int(m.sum())} | {len(np.unique(wk[m]))} | " + "/".join(f"{x:.0f}" for x in q) + " |")
    out += ["", "| 塊の長さ(日) | 抜かない low − high(全期間) | 抜いた low − high(全期間) |", "|---|---|---|"]
    a = acc["1w"]; n = nd; ai = np.arange(n)
    def raw1(i):
        r = []
        for c in ("low", "high"):
            m = clsv[i] == c
            r.append((a["nu"] + a["nd"])[i][m].sum() / (a["du"] + a["dd"])[i][m].sum())
        return r[0] - r[1]
    def fl1(i):
        r = []
        for c in ("low", "high"):
            m = clsv[i] == c
            du, dd = a["du"][i][m].sum(), a["dd"][i][m].sum()
            if du <= 0 or dd <= 0:
                return np.nan
            r.append((a["nu"][i][m].sum() / du + a["nd"][i][m].sum() / dd) / 2)
        return r[0] - r[1]
    keep = L.BLOCK
    for bl in (5, 14, 28, 56):
        L.BLOCK = bl
        br, bf = L._boot(n, raw1), L._boot(n, fl1)
        out.append(f"| {bl} | {raw1(ai):+.3f} [{br['lo']:+.3f}, {br['hi']:+.3f}] | {fl1(ai):+.3f} [{bf['lo']:+.3f}, {bf['hi']:+.3f}] |")
    L.BLOCK = keep
    # 6. 起点の行を 1 分足と突き合わせる(監査役 1 回目の直す 5: # 7 の D0 で未確認だった起点の値・当たり・前の向き)。
    #    台本と別に手で書いた素朴な走査で、窓ごとに決まった番号の行(全体の 1/7・3/7・5/7 番目)を作り直して比べる。
    out += ["", "## 6. 起点の行と 1 分足の突き合わせ(素朴な走査で作り直し。監査役 1 回目の直す 5)", "",
            "| 窓 | T | 記録の w・向き・分・前の向き | 作り直しの w・向き・分・前の向き | 一致 |", "|---|---|---|---|---|"]
    WIN = {"1h": 3600, "1d": 86400, "1w": 7 * 86400}
    idx = np.flatnonzero(g.ne); ends = g.start(idx) + L.MIN_NS; xl = np.log(g.c[idx])
    rows = {}
    with gzip.open(REC, "rt") as fh:
        for r in csv.DictReader(fh):
            rows.setdefault(r["window"], []).append(r)
    for wname, rs in rows.items():
        for frac in (1, 3, 5):
            r = rs[len(rs) * frac // 7]
            T = L.iso_ns(r["T"]); wn = WIN[wname] * 10**9
            k = np.searchsorted(ends, T, side="right") - 1; a = xl[k]
            j = np.searchsorted(ends, T - wn, side="right")
            w = float(np.sqrt(np.sum(np.diff(xl[j - 1:k + 1]) ** 2))) if j >= 1 else float(np.sqrt(np.sum(np.diff(xl[j:k + 1]) ** 2)))
            kp = np.searchsorted(ends, T - wn, side="right") - 1
            pr = int(np.sign(a - xl[kp])) if kp >= 0 else 0
            side = 0; mins = -1
            for m in range(k + 1, len(xl)):
                if xl[m] - a >= w:
                    side = 1
                elif xl[m] - a <= -w:
                    side = -1
                if side:
                    mins = int((ends[m] - T) // (60 * 10**9)); break
            rec = (float(r["w_bp"]), int(r["side"]), int(r["minutes"]), int(r["prior_window_move"]))
            mine = (w * 1e4, side, mins, pr)
            ok = abs(rec[0] - mine[0]) < 1e-3 * max(1.0, rec[0]) and rec[1:] == mine[1:]
            out.append(f"| {wname} | {r['T']} | {rec[0]:.3f}・{rec[1]:+d}・{rec[2]}・{rec[3]:+d} | {mine[0]:.3f}・{mine[1]:+d}・{mine[2]}・{mine[3]:+d} | {'○' if ok else '✕'} |")
    # 7. 年で層に分けた 1 日の線を 2017 年を除いて(監査役 1 回目の直す 2: 層に分けた +0.037 の下の端が 2017 年に依るか)
    out += ["", "## 7. 年で層に分けた 1 日の線の low − high(2017 年を除く。監査役 1 回目の直す 2。結果を見た後の選び = 探索)", "",
            "| 窓 | 使った年 | 抜かない | 抜いた |", "|---|---|---|---|"]
    a1 = acc["1d"]; yk = np.array([int(L.day_str(int(dd))[:4]) for dd in days.nums])
    ys = [2018, 2019, 2020, 2022, 2023]
    def st(i, flow):
        num = den = 0.0
        for y in ys:
            r = []
            for c in ("low", "high"):
                m = (clsv[i] == c) & (yk[i] == y)
                if flow:
                    du, dd = a1["du"][i][m].sum(), a1["dd"][i][m].sum()
                    if du <= 0 or dd <= 0:
                        return np.nan
                    r.append((a1["nu"][i][m].sum() / du + a1["nd"][i][m].sum() / dd) / 2)
                else:
                    dn = (a1["du"] + a1["dd"])[i][m].sum()
                    if dn <= 0:
                        return np.nan
                    r.append((a1["nu"] + a1["nd"])[i][m].sum() / dn)
            nl, nh = ((clsv == "low") & (yk == y)).sum(), ((clsv == "high") & (yk == y)).sum()
            wy = nl * nh / (nl + nh); num += wy * (r[0] - r[1]); den += wy
        return num / den
    cells = []
    for flow in (False, True):
        e = st(np.arange(nd), flow); b = L._boot(nd, lambda i, flow=flow: st(i, flow))
        cells.append(f"{e:+.4f} [{b['lo']:+.4f}, {b['hi']:+.4f}]" if b["lo"] is not None else f"{e:+.4f}(区間なし)")
    out.append(f"| 1d | {','.join(map(str, ys))} | " + " | ".join(cells) + " |")
    open(os.path.join(HERE, "c7_records.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
