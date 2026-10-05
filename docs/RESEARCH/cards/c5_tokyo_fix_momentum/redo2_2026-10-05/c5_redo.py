"""カード 5(東京仲値・前モメンタム)の分析のやり直し(2026-10-05)。保存済みの measure/default の run.npz・daily.csv・
run_record.json と、内閣府の祝日の一覧(このフォルダの syukujitsu_cao_20261005.csv、
https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv を 2026-10-05 に取得し cp932 → utf-8 にしたもの)を読むだけ。
走らせ直しではない。台本そのものの試験は無い(【試験の無い台本の値】)。
    PYTHONPATH=src python3 docs/RESEARCH/cards/c5_tokyo_fix_momentum/redo2_2026-10-05/c5_redo.py
出力: このフォルダの C5_TABLES.md・c5_redo.json

P_t は bot.research.cards.pnl.pnl と同じ式(e_t × (open_{t+2} / open_{t+1} − 1) × 1e4、t+1・t+2 は次の空でない足)を
CardRun を作らずに npz の配列で作り直し、合計が daily.csv の和と合うことを確かめる。日 = 決定の時刻 t(足の終わり)の
日本時間の日(measure の formula と同じ)。
D0: 年ごとの足・決定の数(run_record)/ 9 時 55 分(日本時間)以後に持ち高のある決定 / 土日の持ち高 / 持ち高の変更の回数。
D2: 前の日の荒れ具合(vol_split_daily.classify)・曜日(月〜金)・時刻の帯(決定の時刻の日本時間の時。9 時の帯は 9:00〜9:55)・
    暦(祝日 = 内閣府の一覧 / 年末年始 = 12-31・01-02・01-03【仮定: 銀行の休日。一次資料は未確認】/ ふつうの平日)× 前半・後半。
    1 日あたり = その区分の日の S_d の平均(帯は、その帯の P_t の日ごとの和を、平日すべての日で平均)。
D5: 持ち高 ≠ 0 の決定ごとに、約定の足の始値から h 分後(h = 1・5・15・60)の最初の空でない足の始値までの値動き × 持ち高の符号。
    対照 = 同じ符号で、約定の足の始まり + 24 時間 からの同じ値動き(向きの偏り = 上げ相場の流れと時刻の癖をそろえる)。
    買い・売り・全部 × 本体・対照・本体 − 対照、全期間・前半・後半。1 決定あたり、区間は日の塊(群の和 ÷ 群の数)。
"""
import collections
import csv
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

M = os.path.join(HERE, "..", "measure", "default")
JST = timezone(timedelta(hours=9))
NS = 10**9
MIN = 60 * NS
WD = ["月", "火", "水", "木", "金", "土", "日"]


def jst(ns):
    return datetime.fromtimestamp(int(ns) // NS, tz=JST)


def main():
    z = np.load(os.path.join(M, "run.npz"))
    op, e_all, dec, end_ns, start_ns, vol = (z[k] for k in ("open", "exposure", "decided", "end_ns", "start_ns", "volume"))
    d_idx = np.flatnonzero(dec)
    assert np.array_equal(d_idx, np.flatnonzero(vol > 0))
    m = len(d_idx) - 2
    bar, fill, ex = d_idx[:m], d_idx[1:m + 1], d_idx[2:m + 2]
    e = e_all[bar]
    r = (op[ex] / op[fill] - 1.0) * 1e4
    p = e * r
    t_end = end_ns[bar]
    # 日(決定の時刻 t の日本時間の日)。end_ns は足の終わり。measure の formula「日 = 決定の時刻 t の日本時間の日」
    secs = t_end // NS
    jst_days = (secs + 9 * 3600) // 86400  # 1970-01-01 からの日本時間の日の番号
    jst_sec_of_day = (secs + 9 * 3600) % 86400
    daily = {}
    for line in open(os.path.join(M, "daily.csv")).read().splitlines()[1:]:
        dd, pp, _n = line.split(",")
        daily[dd] = float(pp)
    days = sorted(daily)
    day_of = lambda k: (date(1970, 1, 1) + timedelta(days=int(k))).isoformat()  # noqa: E731
    uniq, inv = np.unique(jst_days, return_inverse=True)
    sums = np.bincount(inv, weights=p)
    recon = {day_of(k): float(s) for k, s in zip(uniq, sums)}
    res = {"check": {"sum_P": float(p.sum()), "sum_daily_csv": float(sum(daily.values())),
                     "max_abs_day_diff": max(abs(recon.get(d, 0.0) - daily[d]) for d in days),
                     "days_in_recon_not_csv": sorted(set(recon) - set(daily))[:5]}}
    out = ["# カード 5 のやり直しの表(保存済みの出力から。bp、経費の前、成行・次の足の始値で約定)", ""]
    c = res["check"]
    out += ["## 確かめ", "", f"- P_t の合計 {c['sum_P']:+,.1f} bp、daily.csv の和 {c['sum_daily_csv']:+,.1f} bp、"
            f"日ごとの差の最大 {c['max_abs_day_diff']:.2e} bp、daily.csv に無い日 {c['days_in_recon_not_csv']}", ""]

    # ---------------- D0
    rr = json.load(open(os.path.join(M, "run_record.json")))
    out += ["## D0 年(暦年の区切り、UTC)ごとの足と決定の数(run_record の chunks)", "", "| 区切り | 足 | 決定 | 1 年の分の数に対する決定の割合 |", "|---|---|---|---|"]
    for ch in rr["chunks"]:
        a, b = (datetime.fromisoformat(x.replace("Z", "+00:00")) for x in ch["range"])
        mins = (b - a).total_seconds() / 60
        out.append(f"| {ch['range'][0][:10]}〜{ch['range'][1][:10]} | {ch['bars']:,} | {ch['decisions']:,} | {ch['decisions'] / mins:.1%} |")
    fix_sec = 9 * 3600 + 55 * 60
    # 約定の足の始まりの日本時間の時刻が 9:55 以後(= 仲値の後の値動きを含む)で持ち高 ≠ 0
    f_sec = ((start_ns[fill] // NS) + 9 * 3600) % 86400
    f_wd = np.array([(date(1970, 1, 1) + timedelta(days=int(k))).weekday() for k in ((start_ns[fill] // NS + 9 * 3600) // 86400)])
    nz = e != 0
    after = nz & (f_sec >= fix_sec)
    wkend = nz & (f_wd >= 5)
    after_days = sorted({day_of(k) for k in ((start_ns[fill][after] // NS + 9 * 3600) // 86400)})
    dE = np.abs(np.diff(e_all[d_idx]))
    res["d0"] = {"after_fix_decisions": int(after.sum()), "after_fix_days": len(after_days), "after_fix_sum": float(p[after].sum()),
                 "weekend_decisions": int(wkend.sum()), "weekend_sum": float(p[wkend].sum()),
                 "nonzero_decisions": int(nz.sum()), "sum_abs_de": float(dE.sum()), "changes": int((dE > 0).sum()),
                 "days": len(days)}
    d0 = res["d0"]
    out += ["", "## D0 仲値の後・土日の持ち高と、持ち高の変更", "",
            f"- 持ち高 ≠ 0 の決定 {d0['nonzero_decisions']:,}。うち約定の足が 9 時 55 分(日本時間)以後に始まるもの {d0['after_fix_decisions']:,}"
            f"({d0['after_fix_days']} 日)、その損益の和 {d0['after_fix_sum']:+,.1f} bp。土日に約定したもの {d0['weekend_decisions']:,}、和 {d0['weekend_sum']:+,.1f}",
            f"- 持ち高が変わった回数 {d0['changes']:,}、Σ|Δe| {d0['sum_abs_de']:,.0f}(1 日あたり {d0['sum_abs_de'] / d0['days']:.2f})",
            f"- 仲値の後の日の例(最初の 10): {after_days[:10]}", ""]

    # ---------------- D2
    import vol_split_daily as vs
    cls = vs.classify(vs.daily_vol(vs.load_closes_by_day()))
    hol = {}
    for row in csv.reader(open(os.path.join(HERE, "syukujitsu_cao_20261005.csv"), encoding="utf-8")):
        if row and row[0][:1].isdigit():
            y, mo, da = row[0].split("/")
            hol[date(int(y), int(mo), int(da)).isoformat()] = row[1]
    half = len(days) // 2
    parts = {"全期間": set(days), "前半": set(days[:half]), "後半": set(days[half:])}
    res["d2"] = {"half_edge": days[half], "rows": []}

    def cell(x):
        r_ = dt.mean_ci(x) if len(x) >= 10 else {"n": len(x), "mean": float(np.mean(x)) if x else None, "lo": None, "hi": None}
        if r_.get("lo") is None:
            return r_, f"{len(x)}・{'—' if r_['mean'] is None else format(r_['mean'], '+.2f')}"
        return r_, f"{len(x)}・{r_['mean']:+.2f} [{r_['lo']:+.2f}, {r_['hi']:+.2f}]"

    def table(title, keyf, keys, src=None, day_filter=None):
        nonlocal out
        out += [f"## D2 {title}", "", "| 区分 | 全期間: 日数・1 日あたり [区間] | 前半 | 後半 |", "|---|---|---|---|"]
        for k in keys:
            cells = []
            for pn, part in parts.items():
                x = [(src[d] if src is not None else daily[d]) for d in days if d in part and (day_filter is None or day_filter(d)) and keyf(d) == k]
                r_, s_ = cell(x)
                res["d2"]["rows"].append({"table": title, "key": str(k), "part": pn, **{kk: r_.get(kk) for kk in ("n", "mean", "lo", "hi", "mde")}})
                cells.append(s_)
            out.append(f"| {k} | {cells[0]} | {cells[1]} | {cells[2]} |")
        out.append("")

    wd = lambda d: date.fromisoformat(d).weekday()  # noqa: E731
    weekday = lambda d: wd(d) < 5  # noqa: E731
    table("前の日の荒れ具合(平日だけ。区分は 2017 年から)", lambda d: {"low": "低", "mid": "中", "high": "高"}.get(cls.get(d), "区分なし"),
          ["低", "中", "高", "区分なし"], day_filter=weekday)
    table("曜日(日本時間の日)", lambda d: WD[wd(d)], WD)

    def cal(d):
        if wd(d) >= 5:
            return "土日"
        if d in hol:
            return "祝日(内閣府)"
        if d[5:] in ("12-31", "01-02", "01-03"):
            return "年末年始(12-31・01-02・01-03)"
        return "ふつうの平日"
    table("暦(仲値の無い日 = 祝日・年末年始)", cal, ["ふつうの平日", "祝日(内閣府)", "年末年始(12-31・01-02・01-03)", "土日"])
    # 時刻の帯: 決定の時刻 t(足の終わり)の日本時間の時。9 時の帯 = 9:00〜9:55 に終わる足
    hour = (jst_sec_of_day - 1) // 3600  # 足の終わりちょうどの時刻は前の時に入れる(0:00 に終わる足 = 前の日の 23 時)
    band_daily = collections.defaultdict(lambda: collections.defaultdict(float))
    for h in range(10):
        msk = (hour == h)
        u2, inv2 = np.unique(jst_days[msk], return_inverse=True)
        s2 = np.bincount(inv2, weights=p[msk])
        for k, s in zip(u2, s2):
            band_daily[h][day_of(k)] = float(s)
    rest = ~np.isin(hour, np.arange(10))
    res["d2"]["p_outside_bands"] = float(p[rest].sum())
    for h in range(10):
        src = {d: band_daily[h].get(d, 0.0) for d in days}
        table(f"時刻の帯 {h} 時台(平日すべての日で平均。決定の時刻 = 足の終わりの日本時間)", lambda d, h=h: f"{h} 時台", [f"{h} 時台"], src=src, day_filter=weekday)
    out += [f"- 0〜9 時台の外の決定の損益の和: {res['d2']['p_outside_bands']:+,.1f} bp", ""]

    # ---------------- D5
    # 足の始まりの時刻 → 空でない足の索引(その時刻以後の最初の空でない足)
    s_dec = start_ns[d_idx]
    o_dec = op[d_idx]

    def open_at(ns_arr):
        j = np.searchsorted(s_dec, ns_arr, side="left")
        ok = j < len(s_dec)
        j2 = np.minimum(j, len(s_dec) - 1)
        lag = np.where(ok, s_dec[j2] - ns_arr, np.iinfo(np.int64).max)
        return o_dec[j2], ok & (lag < 5 * MIN)  # 5 分より先の足しか無ければ欠け
    sel = np.flatnonzero(nz)
    f0 = start_ns[fill][sel]
    sg = np.sign(e[sel])
    dayk = [day_of(k) for k in jst_days[sel]]
    dayarr = np.array(dayk)
    o0, ok0 = open_at(f0)
    oc0, okc0 = open_at(f0 + 86400 * NS)
    res["d5"] = []
    out += ["## D5 持ち高 ≠ 0 の決定の、約定の時刻からの値動き × 持ち高の符号(bp/決定)。対照 = 24 時間後の同じ時刻から同じ符号", "",
            "| 向き | h 分 | 期間 | 決定 | 本体 [区間] | 対照 [区間] | 本体 − 対照 [区間] |", "|---|---|---|---|---|---|---|"]
    for h in (1, 5, 15, 60):
        o1, ok1 = open_at(f0 + h * MIN)
        oc1, okc1 = open_at(f0 + 86400 * NS + h * MIN)
        main_ = sg * (o1 / o0 - 1) * 1e4
        ctrl = sg * (oc1 / oc0 - 1) * 1e4
        okb = ok0 & ok1 & okc0 & okc1
        for side_name, smask in (("全部", np.ones_like(okb)), ("買い", sg > 0), ("売り", sg < 0)):
            for pn, part in parts.items():
                pm = okb & smask & np.isin(dayarr, list(part))
                row = {"side": side_name, "h": h, "part": pn}
                for nm, v in (("main", main_), ("ctrl", ctrl), ("diff", main_ - ctrl)):
                    s_, n_ = collections.defaultdict(float), collections.defaultdict(int)
                    for d, x in zip(dayarr[pm], v[pm]):
                        s_[d] += float(x)
                        n_[d] += 1
                    pdays = [d for d in days if d in part]
                    row[nm] = dt.group_ratio_ci(pdays, s_, n_)
                res["d5"].append(row)
                f = lambda q: "—" if q["per_trade"] is None else (f"{q['per_trade']:+.3f}" + ("" if q["lo"] is None else f" [{q['lo']:+.3f}, {q['hi']:+.3f}]"))  # noqa: E731
                out.append(f"| {side_name} | {h} | {pn} | {row['main']['trades']:,} | {f(row['main'])} | {f(row['ctrl'])} | {f(row['diff'])} |")
    json.dump(res, open(os.path.join(HERE, "c5_redo.json"), "w"), ensure_ascii=False, indent=1)
    open(os.path.join(HERE, "C5_TABLES.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
