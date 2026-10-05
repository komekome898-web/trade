"""カード 6(週末ギャップ)の分析のやり直し(2026-10-05)。保存済みの measure/<変種>/run.npz・daily.csv・diagnostics.json と、
カードと同じ USDJPY の置き場(backtest_data/fx_usdjpy_1m_20170801_20221231/usdjpy_1m.csv.gz、封印の前)を読むだけ。
走らせ直しではない。台本そのものの試験は無い(【試験の無い台本の値】)。
    PYTHONPATH=src python3 docs/RESEARCH/cards/c6_weekend_gap_revert/redo2_2026-10-05/c6_redo.py
出力: このフォルダの C6_TABLES.md・c6_weeks.csv・trades_<変種>/trades.csv.gz

- 取引の行: run.npz から measure の extra.json の式どおり(同じ向きの持ち高が続いた区間 = 1 取引)。本数・和を extra.json と照らす。
- btc の g: カードの定義(src/bot/research/cards/library/c6_weekend_gap_revert.py の docstring)を写して作り直す:
    g = ln(週明けの行の終わり r + 60 秒 の時点の bitFlyer の終値) − ln(前の週の、値が前の行と違った最後の USDJPY の行の終わりの時点の bitFlyer の終値)
  「その時点の bitFlyer の終値」= その時刻までに終わった最後の空でない足の終値。作り直した符号が、カードの窓の最初の持ち高の符号の逆と
  一致するかを全週で確かめる。usdjpy の g は diagnostics.json の per_week の値(カードの記録)。
- D0: 週明けの行の時刻(UTC の曜日と時)ごとの週数と損益。NY 17 時(日 21・22 時 UTC)から外れた週の一覧。
- D2: 前の日(日本時間)の荒れ具合(vol_split_daily.classify)× 前半・後半。単位は 1 取引(= 1 週)あたり、区間は日の塊(群の和 ÷ 群の数)。
- D3: |g| の三分位(建ての前に決まる群)× 前半・後半、1 取引あたり。
- D5: 買い・売り × 本体(約定の始値 → 出の始値)・対照(同じ時刻の 24 時間後から同じ向き)・本体 − 対照、全期間・前半・後半。
  あわせて中ほどの値((高値 + 安値) ÷ 2、約定の足 → 出の足の 1 本前)での本体・対照。
前半・後半の境は diag_tables と同じ(日本時間の日の数で 2 つ。daily.csv の日)。
"""
import collections
import csv
import gzip
import json
import math
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

NS, MIN = 10**9, 60 * 10**9
JST = 9 * 3600 * NS
WEEK0 = 3 * 86400 * NS  # 1970-01-01 は木曜。月曜 0 時(日本時間)始まりの週の番号に使う
M = os.path.join(HERE, "..", "measure")
WD = ["月", "火", "水", "木", "金", "土", "日"]


def jst_week(t):
    return (t + JST + WEEK0) // (7 * 86400 * NS)


def jst_day(t):
    return (date(1970, 1, 1) + timedelta(days=int((t + JST) // (86400 * NS)))).isoformat()


def iso(ns):
    return datetime.fromtimestamp(int(ns) / 1e9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_usdjpy():
    ts, cl = [], []
    with gzip.open(os.path.join(REPO, "backtest_data/fx_usdjpy_1m_20170801_20221231/usdjpy_1m.csv.gz"), "rt") as fh:
        r = csv.reader(fh)
        next(r)
        for row in r:
            ts.append(int(datetime.fromisoformat(row[0]).timestamp()) * NS)
            cl.append(float(row[4]))
    return np.array(ts, dtype=np.int64), np.array(cl)


def trades_of(z):
    d = np.flatnonzero(z["decided"])
    m = len(d) - 2
    bar, fill, ex = d[:m], d[1:m + 1], d[2:m + 2]
    e = z["exposure"][bar]
    p = e * (z["open"][ex] / z["open"][fill] - 1.0) * 1e4
    s = np.sign(e)
    out, i = [], 0
    while i < m:
        if s[i] == 0:
            i += 1
            continue
        j = i
        while j + 1 < m and s[j + 1] == s[i]:
            j += 1
        out.append({"signal_ns": int(z["end_ns"][bar[i]]), "entry_ns": int(z["start_ns"][fill[i]]), "exit_ns": int(z["start_ns"][ex[j]]),
                    "side": int(s[i]), "entry_px": float(z["open"][fill[i]]), "exit_px": float(z["open"][ex[j]]),
                    "pnl": float(p[i:j + 1].sum()), "fill": int(fill[i]), "exit": int(ex[j])})
        i = j + 1
    return out, d


def main():
    out = ["# カード 6 のやり直しの表(保存済みの出力と USDJPY の置き場から。bp、経費の前、成行・次の足の始値で約定)", ""]
    uj_t, uj_c = load_usdjpy()
    chg = np.flatnonzero(np.diff(uj_c) != 0) + 1  # 前の行と値が違う行
    weeks = {}
    res = {}
    for v in ("btc", "usdjpy"):
        z = np.load(os.path.join(M, v, "run.npz"))
        tr, d = trades_of(z)
        ext = json.load(open(os.path.join(M, v, "extra.json")))["trades"]
        diag = json.load(open(os.path.join(M, v, "diagnostics.json")))["per_week"]
        out.append(f"- {v}: 作り直した取引 {len(tr)} 本・和 {sum(t['pnl'] for t in tr):+,.1f}(extra.json: 買い {ext['long']['n']}・売り {ext['short']['n']}、"
                   f"作り直し: 買い {sum(1 for t in tr if t['side'] > 0)})")
        os.makedirs(os.path.join(HERE, f"trades_{v}"), exist_ok=True)
        with gzip.open(os.path.join(HERE, f"trades_{v}", "trades.csv.gz"), "wt", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["signal_t", "entry_t", "exit_t", "side", "entry_price", "pnl_bp"])
            for t in tr:
                w.writerow([iso(t["signal_ns"]), iso(t["entry_ns"]), iso(t["exit_ns"]), t["side"], f"{t['entry_px']:.1f}", f"{t['pnl']:.6f}"])
        res[v] = {"z": z, "tr": tr, "d": d}
        if v == "btc":
            s_dec, c_dec = z["start_ns"][d], z["close"][d]

            def bf_close_asof(t_end):  # t_end までに終わった最後の空でない足の終値
                j = np.searchsorted(s_dec + MIN, t_end, side="right") - 1
                return float(c_dec[j])
            for r, ga, fe in zip(diag["r_ns"], diag["g_usdjpy"], diag["first_exposure_in_window"]):
                wk = jst_week(r)
                rows = chg[(jst_week(uj_t[chg]) == wk - 1)]
                t_last = int(uj_t[rows[-1]]) + MIN
                g = math.log(bf_close_asof(r + MIN)) - math.log(bf_close_asof(t_last))
                weeks[r] = {"r": r, "g_usdjpy": ga, "g_btc": g, "t_last": t_last, "first_exp_btc": fe}
        else:
            for r, fe in zip(diag["r_ns"], diag["first_exposure_in_window"]):
                weeks[r]["first_exp_usdjpy"] = fe
    agree = sum(1 for w in weeks.values() if np.sign(w["g_btc"]) == -w["first_exp_btc"])
    out += [f"- btc の g の作り直しの符号が、カードの窓の最初の持ち高の符号の逆と一致した週: {agree} / {len(weeks)}", ""]

    # 週ごとの表(取引を r で引く)
    for v in ("btc", "usdjpy"):
        for t in res[v]["tr"]:
            r = max(k for k in weeks if k <= t["signal_ns"])
            weeks[r][f"pnl_{v}"] = weeks[r].get(f"pnl_{v}", 0.0) + t["pnl"]
            weeks[r][f"side_{v}"] = t["side"]
    with open(os.path.join(HERE, "c6_weeks.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["r_utc", "jst_day", "g_usdjpy_bp", "g_btc_bp", "side_btc", "pnl_btc", "side_usdjpy", "pnl_usdjpy"])
        for r in sorted(weeks):
            x = weeks[r]
            w.writerow([iso(r), jst_day(r), f"{x['g_usdjpy'] * 1e4:.3f}", f"{x['g_btc'] * 1e4:.3f}", x.get("side_btc"), f"{x.get('pnl_btc', 0):.4f}",
                        x.get("side_usdjpy"), f"{x.get('pnl_usdjpy', 0):.4f}"])

    # D0 週明けの時刻
    by = collections.defaultdict(list)
    for r, x in weeks.items():
        dtu = datetime.fromtimestamp(r / 1e9, tz=timezone.utc)
        by[f"{WD[dtu.weekday()]} {dtu.hour:02d}時"].append(x)
    out += ["## D0 週明けの行の時刻(UTC の曜日と時)ごとの週数と損益の和", "", "| 時刻 | 週 | btc の和 | usdjpy の和 |", "|---|---|---|---|"]
    for k in sorted(by, key=lambda s: (-len(by[s]), s)):
        xs = by[k]
        out.append(f"| {k} | {len(xs)} | {sum(x.get('pnl_btc', 0) for x in xs):+,.1f} | {sum(x.get('pnl_usdjpy', 0) for x in xs):+,.1f} |")
    out += ["", "NY 17 時(日 21・22 時 UTC)から外れた週:", "", "| r(UTC) | 日本時間の日 | 前の週の最後の値の変化(UTC、行の終わり) | g_usdjpy(bp) | g_btc(bp) | btc の損益 | usdjpy の損益 |", "|---|---|---|---|---|---|---|"]
    for r in sorted(weeks):
        dtu = datetime.fromtimestamp(r / 1e9, tz=timezone.utc)
        if not (dtu.weekday() == 6 and dtu.hour in (21, 22)):
            x = weeks[r]
            out.append(f"| {iso(r)} | {jst_day(r)} | {iso(x['t_last'])} | {x['g_usdjpy'] * 1e4:+.2f} | {x['g_btc'] * 1e4:+.2f} | {x.get('pnl_btc', 0):+.1f} | {x.get('pnl_usdjpy', 0):+.1f} |")

    # 日の並びと前半・後半(daily.csv の日)
    days = sorted(l.split(",")[0] for l in open(os.path.join(M, "btc", "daily.csv")).read().splitlines()[1:])
    half = len(days) // 2
    parts = {"全期間": days, "前半": days[:half], "後半": days[half:]}

    def ratio(items, pd):
        su, cn = collections.defaultdict(float), collections.defaultdict(int)
        for dd, x in items:
            su[dd] += x
            cn[dd] += 1
        return dt.group_ratio_ci(pd, su, cn)
    f = lambda q: "—" if q["per_trade"] is None else (f"{q['per_trade']:+.2f}" + ("" if q["lo"] is None else f" [{q['lo']:+.2f}, {q['hi']:+.2f}]"))  # noqa: E731
    pset = {k: set(v) for k, v in parts.items()}

    # D2 前の日の荒れ具合
    import vol_split_daily as vs
    cls = vs.classify(vs.daily_vol(vs.load_closes_by_day()))
    out += ["", f"## D2 前の日(日本時間)の荒れ具合 × 前半・後半(1 取引 = 1 週あたり bp、区間は日の塊。前半・後半の境 {days[half]})", "",
            "| 変種 | 区分 | 全期間: 週・1 取引あたり [区間] | 前半 | 後半 |", "|---|---|---|---|---|"]
    for v in ("btc", "usdjpy"):
        for c in ("low", "mid", "high", None):
            cells = []
            for pn, pd in parts.items():
                its = [(jst_day(t["signal_ns"]), t["pnl"]) for t in res[v]["tr"] if jst_day(t["signal_ns"]) in pset[pn] and cls.get(jst_day(t["signal_ns"])) == c]
                q = ratio(its, pd)
                cells.append(f"{q['trades']}・{f(q)}")
            out.append(f"| {v} | {({'low': '低', 'mid': '中', 'high': '高'}).get(c, '区分なし')} | {cells[0]} | {cells[1]} | {cells[2]} |")

    # D3 |g| の三分位
    out += ["", "## D3 |g| の三分位【建ての前に決まる群】× 前半・後半(1 取引あたり bp)。btc は |g_btc|、usdjpy は |g_usdjpy| で切る", "",
            "| 変種 | |g| の帯(bp) | 全期間: 週・1 取引あたり [区間] | 前半 | 後半 |", "|---|---|---|---|---|"]
    for v in ("btc", "usdjpy"):
        key = "g_btc" if v == "btc" else "g_usdjpy"
        gab = {r: abs(x[key]) * 1e4 for r, x in weeks.items()}
        q1, q2 = np.quantile(list(gab.values()), [1 / 3, 2 / 3])
        for lo_, hi_, nm in ((0, q1, f"〜{q1:.1f}"), (q1, q2, f"{q1:.1f}〜{q2:.1f}"), (q2, 1e18, f"{q2:.1f}〜")):
            cells = []
            for pn, pd in parts.items():
                its = []
                for t in res[v]["tr"]:
                    r = max(k for k in weeks if k <= t["signal_ns"])
                    if lo_ <= gab[r] < hi_ and jst_day(t["signal_ns"]) in pset[pn]:
                        its.append((jst_day(t["signal_ns"]), t["pnl"]))
                q = ratio(its, pd)
                cells.append(f"{q['trades']}・{f(q)}")
            out.append(f"| {v} | {nm} | {cells[0]} | {cells[1]} | {cells[2]} |")

    # D5 買い・売り × 本体・対照(始値)と中ほどの値
    out += ["", "## D5 買い・売り × 本体(約定の始値 → 出の始値)・対照(24 時間後の同じ時刻から同じ向き)(1 取引あたり bp)", "",
            "| 変種 | 向き | 期間 | 取引 | 本体 [区間] | 対照 [区間] | 本体 − 対照 [区間] | 中ほど 本体 | 中ほど 対照 | 中ほど 本体 − 対照 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for v in ("btc", "usdjpy"):
        z, d = res[v]["z"], res[v]["d"]
        s_dec, o_dec, mid_dec = z["start_ns"][d], z["open"][d], ((z["high"] + z["low"]) / 2)[d]

        def at(arr, ns):
            j = np.searchsorted(s_dec, ns, side="left")
            if j >= len(s_dec) or s_dec[j] - ns >= 5 * MIN:
                return None, None
            return float(arr[j]), j
        for side_name, sel in (("全部", (1, -1)), ("買い", (1,)), ("売り", (-1,))):
            for pn, pd in parts.items():
                acc = collections.defaultdict(list)
                for t in res[v]["tr"]:
                    if t["side"] not in sel or jst_day(t["signal_ns"]) not in pset[pn]:
                        continue
                    day_ = jst_day(t["signal_ns"])
                    e0, _ = at(o_dec, t["entry_ns"])
                    e1, _ = at(o_dec, t["exit_ns"])
                    c0, _ = at(o_dec, t["entry_ns"] + 86400 * NS)
                    c1, _ = at(o_dec, t["exit_ns"] + 86400 * NS)
                    m0, _ = at(mid_dec, t["entry_ns"])
                    m1, _ = at(mid_dec, t["exit_ns"] - MIN)
                    n0, _ = at(mid_dec, t["entry_ns"] + 86400 * NS)
                    n1, _ = at(mid_dec, t["exit_ns"] - MIN + 86400 * NS)
                    if None in (e0, e1, c0, c1, m0, m1, n0, n1):
                        continue
                    b = t["side"] * (e1 / e0 - 1) * 1e4
                    c = t["side"] * (c1 / c0 - 1) * 1e4
                    mb = t["side"] * (m1 / m0 - 1) * 1e4
                    mc = t["side"] * (n1 / n0 - 1) * 1e4
                    for k, x in (("b", b), ("c", c), ("d", b - c), ("mb", mb), ("mc", mc), ("md", mb - mc)):
                        acc[k].append((day_, x))
                qs = {k: ratio(acc[k], pd) for k in ("b", "c", "d", "mb", "mc", "md")}
                out.append(f"| {v} | {side_name} | {pn} | {qs['b']['trades']} | {f(qs['b'])} | {f(qs['c'])} | {f(qs['d'])} | {f(qs['mb'])} | {f(qs['mc'])} | {f(qs['md'])} |")
    # 2 変種の週ごとの向き
    both = [x for x in weeks.values() if x.get("side_btc") and x.get("side_usdjpy")]
    ag = [x for x in both if x["side_btc"] == x["side_usdjpy"]]
    out += ["", f"## 2 変種の週ごとの向き: 両方建てた週 {len(both)}、向きが同じ週 {len(ag)}", "",
            "| 週の組 | 週 | btc の和 | usdjpy の和 |", "|---|---|---|---|"]
    for nm, xs in (("向きが同じ", ag), ("向きが逆", [x for x in both if x["side_btc"] != x["side_usdjpy"]])):
        out.append(f"| {nm} | {len(xs)} | {sum(x['pnl_btc'] for x in xs):+,.1f} | {sum(x['pnl_usdjpy'] for x in xs):+,.1f} |")
    open(os.path.join(HERE, "C6_TABLES.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
