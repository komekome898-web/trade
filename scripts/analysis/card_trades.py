#!/usr/bin/env python3
"""カードの測定(`measure/<変種>/run.npz`)の 1 分ごとの持ち高から、取引の行と、分析のスキルの D3(勝ち負けの分解・
建ての前に決まる群)の表を出す読み口。新しい走らせはしない(保存済みの持ち高と始値から計算するだけ)。

損益の式は `bot.research.cards.pnl.pnl` と同じ: 決定の時刻 t(足の終わり)の持ち高 e_t を、次の空でない足の始値で約定し、
その次の空でない足の始値まで持つ。P_t = e_t × (open_{t+2} / open_{t+1} − 1) × 10,000(bp、持ち高 1 単位あたり、経費の前)。
取引 = P のある決定を順に並べ、sign(e) が同じで 0 でない決定がつながった最長の区間(`extra.json` の formula と同じ)。
  signal_t = 区間の最初の決定の時刻 t(足の終わり = 合図が分かった時刻)
  entry_t  = 最初の約定の足の始値の時刻(= t の次の空でない足の始まり)
  exit_t   = 最後の決定の手仕舞いの足の始まり
  pnl_bp   = 区間の P_t の和
確かめ: 日本時間の日ごとの P の和が `daily.csv` と一致するか、取引の数・和が `extra.json` と一致するかを出力に書く。

    PYTHONPATH=src python3 scripts/analysis/card_trades.py --measure <measure/変種> --trades-out <置き場> --out <出力.md>

`--trades-out` に `trades.csv.gz` を書く(`diag_tables.py --run` にそのまま渡せる。取引の日は出の時刻の UTC の日)。
表の区間は日の塊(循環、5 日・1,000 回・種 20261004、`diag_tables.group_ratio_ci`)。日は daily.csv の日本時間の日。
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diag_tables import group_ratio_ci, mean_ci, diff_ci, _f  # noqa: E402

JST = timezone(timedelta(hours=9))
BP = 10_000.0


def _iso(ns: int) -> str:
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _jst_day(ns: int) -> str:
    return datetime.fromtimestamp(ns // 10**9, tz=JST).date().isoformat()


SESSION_BANDS = ((0, 10), (10, 60), (60, 240), (240, 720), (720, 1440))  # セッションの始まりからの分(帯の境は結果を見る前に置いた)


def build(measure: str, session_hour: int | None = None) -> dict:
    with np.load(os.path.join(measure, "run.npz")) as f:  # 鍵ごとに読み直さないよう、先に全部読む
        z = {k: f[k] for k in ("decided", "exposure", "open", "end_ns", "start_ns")}
    dec = np.flatnonzero(z["decided"])
    m = len(dec) - 2
    bar, fill, ex = dec[:m], dec[1:m + 1], dec[2:m + 2]
    e = z["exposure"][bar]
    p = e * (z["open"][ex] / z["open"][fill] - 1.0) * BP
    t_ns = z["end_ns"][bar]
    # 日本時間の日ごとの和(確かめ用)
    day_ns = (t_ns + 9 * 3600 * 10**9) // (86400 * 10**9)
    uniq, inv = np.unique(day_ns, return_inverse=True)
    dsum = np.bincount(inv, weights=p)
    # 対照: 同じ分に、同じ大きさで買いだけで持った場合(|e_t| × r)。向きの情報を抜いた、その時間帯の値動きの偏りの分
    ctl = np.bincount(inv, weights=np.abs(e) * (z["open"][ex] / z["open"][fill] - 1.0) * BP)
    r = (z["open"][ex] / z["open"][fill] - 1.0) * BP
    held = e != 0
    wkend = ((day_ns + 3) % 7) >= 5  # 日本時間の曜日(1970-01-01 は木曜 = 3、月 = 0)。土日
    minute_rate = {}
    for lbl, msk in (("held", held), ("nh_weekday", ~held & ~wkend), ("nh_weekend", ~held & wkend),
                     ("held_buy", e > 0), ("held_sell", e < 0)):
        ss = np.bincount(inv, weights=np.where(msk, r, 0.0), minlength=len(uniq))
        nn = np.bincount(inv, weights=msk.astype(float), minlength=len(uniq))
        minute_rate[lbl] = {datetime.fromtimestamp(int(u) * 86400, tz=timezone.utc).date().isoformat(): (float(a), int(c))
                            for u, a, c in zip(uniq, ss, nn)}
    session = {}
    if session_hour is not None:
        since = ((t_ns // 60_000_000_000) - session_hour * 60) % 1440  # セッションの始まり(UTC の時)からの分
        for lo, hi in SESSION_BANDS:
            inb = (since >= lo) & (since < hi)
            for lbl, msk in (("buy", (e > 0) & inb), ("sell", (e < 0) & inb)):
                ss = np.bincount(inv, weights=np.where(msk, r, 0.0), minlength=len(uniq))
                nn = np.bincount(inv, weights=msk.astype(float), minlength=len(uniq))
                session[(lo, hi, lbl)] = {datetime.fromtimestamp(int(u) * 86400, tz=timezone.utc).date().isoformat(): (float(a), int(c))
                                          for u, a, c in zip(uniq, ss, nn)}
    control_calc = {datetime.fromtimestamp(int(u) * 86400, tz=timezone.utc).date().isoformat(): float(s)
                    for u, s in zip(uniq, ctl)}
    daily_calc = {datetime.fromtimestamp(int(u) * 86400, tz=timezone.utc).date().isoformat(): float(s)
                  for u, s in zip(uniq, dsum)}
    sg = np.sign(e)
    trades = []
    nz = np.flatnonzero(sg != 0)
    # 区間の切れ目: 符号が変わるか 0 を挟む所
    if len(nz):
        brk = np.flatnonzero((np.diff(nz) != 1) | (sg[nz[1:]] != sg[nz[:-1]])) + 1
        starts = np.concatenate([[0], brk])
        ends = np.concatenate([brk, [len(nz)]])
        cp = np.concatenate([[0.0], np.cumsum(p[nz])])
        for a, b in zip(starts, ends):
            k0, k1 = nz[a], nz[b - 1]
            trades.append({"signal_ns": int(t_ns[k0]), "entry_ns": int(z["start_ns"][fill[k0]]),
                           "exit_ns": int(z["start_ns"][ex[k1]]), "side": int(sg[k0]),
                           "size": float(np.abs(e[k0])), "pnl_bp": float(cp[b] - cp[a]), "decisions": int(b - a)})
    return {"trades": trades, "daily_calc": daily_calc, "control_calc": control_calc, "minute_rate": minute_rate, "session": session, "n_dec": int(m), "sizes": sorted(set(np.round(np.abs(e[nz]), 6).tolist()))[:10]}


def load_daily(measure: str) -> dict[str, float]:
    with open(os.path.join(measure, "daily.csv"), encoding="utf-8") as fh:
        return {r["day"]: float(r["pnl_bp"]) for r in csv.DictReader(fh)}


def write_trades(trades: list[dict], out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "trades.csv.gz")
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["signal_t", "entry_t", "exit_t", "side", "pnl_bp"])
        for t in trades:
            w.writerow([_iso(t["signal_ns"]), _iso(t["entry_ns"]), _iso(t["exit_ns"]), t["side"], f"{t['pnl_bp']:.6f}"])
    return path


def table(trades: list[dict], days: list[str], key) -> dict:
    sums: dict = defaultdict(lambda: defaultdict(float))
    cnts: dict = defaultdict(lambda: defaultdict(int))
    for t in trades:
        g = key(t)
        if g is None:
            continue
        d = _jst_day(t["signal_ns"])
        sums[g][d] += t["pnl_bp"]
        cnts[g][d] += 1
    return {g: group_ratio_ci(days, sums[g], cnts[g]) for g in sorted(sums)}


def winloss(trades: list[dict]) -> dict:
    p = np.array([t["pnl_bp"] for t in trades]) if trades else np.array([])
    w, l, z = p[p > 0], p[p < 0], p[p == 0]
    return {"n": len(p), "sum": float(p.sum()), "win_n": len(w), "win_sum": float(w.sum()),
            "win_mean": float(w.mean()) if len(w) else None, "win_med": float(np.median(w)) if len(w) else None,
            "loss_n": len(l), "loss_sum": float(l.sum()), "loss_mean": float(l.mean()) if len(l) else None,
            "loss_med": float(np.median(l)) if len(l) else None, "zero_n": len(z),
            "win_rate": len(w) / len(p) if len(p) else None}


def rate_diff(days: list[str], mr: dict, k1: str = "held", k2: str = "nh_weekday") -> str:
    """持っていた分と持っていなかった分の 1 分あたりの差。日を循環の塊で選び直して(塊 5・1,000 回・種 20261004)作り直す。"""
    import math
    from diag_tables import SEED, N_RES, BLOCK
    a = np.array([[*mr[k1].get(d, (0.0, 0)), *mr[k2].get(d, (0.0, 0))] for d in days], dtype=float)
    pt = (a[:, 0].sum() / a[:, 1].sum() - a[:, 2].sum() / a[:, 3].sum()) if a[:, 1].sum() > 0 and a[:, 3].sum() > 0 else float("nan")
    rng = np.random.default_rng(SEED)
    n = len(days)
    nb = math.ceil(n / BLOCK)
    reps = []
    for _ in range(N_RES):
        idx = (rng.integers(0, n, size=nb)[:, None] + np.arange(BLOCK)[None, :]).ravel()[:n] % n
        x = a[idx].sum(axis=0)
        if x[1] > 0 and x[3] > 0:
            reps.append(x[0] / x[1] - x[2] / x[3])
    if len(reps) < N_RES // 2 or not np.isfinite(pt):
        return f"{_f(pt, 4) if np.isfinite(pt) else '—'}(片方の分がほとんど無く区間なし。作り直し {len(reps)} 回)"
    lo, hi = np.percentile(reps, [2.5, 97.5])
    return f"{_f(pt, 4)} [{_f(float(lo), 4)}, {_f(float(hi), 4)}]"


def render(name: str, b: dict, daily: dict, extra: dict, trades_path: str) -> str:
    tr = b["trades"]
    days = sorted(daily)
    h = len(days) // 2
    first = set(days[:h])
    L = [f"# 取引の表 — {name}", "",
         "読み口 `scripts/analysis/card_trades.py`(保存済みの持ち高から計算。新しい走らせではない)。単位 bp・持ち高 1 単位あたり・経費の前。",
         "区間 = 95%、日の塊(循環、5 日・1,000 回・種 20261004)で日を選び直して群の和 ÷ 群の取引の数を作り直したもの。日 = 合図の時刻の日本時間の日。", ""]
    # 確かめ
    mism = [d for d in days if abs(daily[d] - b["daily_calc"].get(d, 0.0)) > 1e-6 * max(1.0, abs(daily[d]))]
    ext = extra.get("trades", {})
    L += ["## 確かめ(保存済みの出力と合うか)", "",
          f"- 日ごとの和: daily.csv の {len(days):,} 日のうち、計算し直した値と合わない日 {len(mism)} 日" + (f"(最初: {mism[:3]})" if mism else ""),
          f"- 取引の数: 計算 {len(tr):,} / extra.json {ext.get('n', '無し')}。損益の和: 計算 {sum(t['pnl_bp'] for t in tr):,.2f} / extra.json の買い + 売り {ext.get('long', {}).get('sum_bp', 0) + ext.get('short', {}).get('sum_bp', 0):,.2f}",
          f"- 持ち高の大きさ(0 でない値、最初の 10 種): {b['sizes']}",
          f"- 取引の行: `{trades_path}`(リポジトリには入れない。この読み口で何度でも作り直せる)", ""]
    # 対照
    def ci(r):
        return f"{_f(r['mean'])} [{_f(r['lo'])}, {_f(r['hi'])}]"
    cc = b["control_calc"]
    L += ["## 買いだけの対照: 同じ分に買いだけで持った場合(向きの情報を抜いたもの)", "",
          "買いだけの対照 = カードが持ち高を持っていた同じ 1 分に、同じ大きさで買いだけで持った損益(|e_t| × 値動き)。カード − 買いだけの対照"
          " = 売りの決定の損益の 2 倍。向きの情報の有無はこの差では決まらない(その時間帯に上げの偏りがあれば、情報が無くても負になる)。"
          "向きの情報は下の「向きの情報の検め」で見る。1 日あたり bp。", "",
          "| 区分 | 日数 | カード | 買いだけの対照 | カード − 買いだけの対照 |", "|---|---|---|---|---|"]
    for lbl, ds in (("全期間", days), ("前半", days[:h]), ("後半", days[h:])):
        L.append(f"| {lbl} | {len(ds):,} | {ci(mean_ci([daily[d] for d in ds]))} | {ci(mean_ci([cc.get(d, 0.0) for d in ds]))} | "
                 f"{ci(mean_ci([daily[d] - cc.get(d, 0.0) for d in ds]))} |")
    dd = diff_ci([daily[d] - cc.get(d, 0.0) for d in days[:h]], [daily[d] - cc.get(d, 0.0) for d in days[h:]])
    L += ["", f"カード − 買いだけの対照 の 後半 − 前半: {ci(dd)}", ""]
    L += ["買いだけで持った 1 分あたりの値動き(bp/分)を、カードが持っていた分・持っていなかった平日の分・持っていなかった土日の分で並べる"
          "(その時間帯に固有の偏りか、期間全体の上げ下げかを見る)。曜日は合図の時刻の日本時間。区間は日の塊で日を選び直して 和 ÷ 分の数 を作り直したもの。", "",
          "| 区分 | 持っていた分 | 持っていなかった平日の分 | 持っていなかった土日の分 | 差(持っていた − 持っていなかった平日) |", "|---|---|---|---|---|"]
    for lbl, ds in (("全期間", days), ("前半", days[:h]), ("後半", days[h:])):
        cells = []
        for k in ("held", "nh_weekday", "nh_weekend"):
            mr = b["minute_rate"][k]
            g = group_ratio_ci(ds, {d: mr.get(d, (0.0, 0))[0] for d in ds}, {d: mr.get(d, (0.0, 0))[1] for d in ds})
            cells.append("分 0" if not g["trades"] else f"{_f(g['per_trade'], 4)} [{_f(g['lo'], 4)}, {_f(g['hi'], 4)}](分 {g['trades']:,})")
        L.append(f"| {lbl} | {cells[0]} | {cells[1]} | {cells[2]} | {rate_diff(ds, b['minute_rate'])} |")
    L.append("")
    # 向きの情報の検め
    L += ["## 向きの情報の検め: 買いの合図の分 − 売りの合図の分(1 分あたりの値動き、bp/分)", "",
          "買いの合図の分 = 持ち高が正だった 1 分、売りの合図の分 = 持ち高が負だった 1 分。どちらも値段そのものの動き(向きを掛けない)。"
          "差が正 = 値段が合図の向きに動いた(向きの情報がある)。合図に情報が無ければ、両方とも同じ時間帯の上げ下げの偏りだけを含むので差は 0。"
          "区間は日の塊で日を選び直して作り直したもの。", "",
          "| 区分 | 買いの合図の分 | 売りの合図の分 | 差(買い − 売り) |", "|---|---|---|---|"]
    for lbl, ds in (("全期間", days), ("前半", days[:h]), ("後半", days[h:])):
        cells = []
        for k in ("held_buy", "held_sell"):
            mr = b["minute_rate"][k]
            g = group_ratio_ci(ds, {d: mr.get(d, (0.0, 0))[0] for d in ds}, {d: mr.get(d, (0.0, 0))[1] for d in ds})
            cells.append("分 0" if not g["trades"] else f"{_f(g['per_trade'], 4)} [{_f(g['lo'], 4)}, {_f(g['hi'], 4)}](分 {g['trades']:,})")
        L.append(f"| {lbl} | {cells[0]} | {cells[1]} | {rate_diff(ds, b['minute_rate'], 'held_buy', 'held_sell')} |")
    L.append("")
    if b.get("session"):
        L += ["## 向きの情報の検め × セッションの始まりからの経過時間(決定の時刻、bp/分)", "",
              "帯の境(分)は結果を見る前に置いた: 0〜10・10〜60・60〜240・240〜720・720〜1440。", "",
              "| 経過(分) | 区分 | 買いの合図の分 | 売りの合図の分 | 差(買い − 売り) |", "|---|---|---|---|---|"]
        for lo, hi in SESSION_BANDS:
            mr = {"held_buy": b["session"][(lo, hi, "buy")], "held_sell": b["session"][(lo, hi, "sell")]}
            for lbl, ds in (("全期間", days), ("前半", days[:h]), ("後半", days[h:])):
                cells = []
                for k in ("held_buy", "held_sell"):
                    g = group_ratio_ci(ds, {d: mr[k].get(d, (0.0, 0))[0] for d in ds}, {d: mr[k].get(d, (0.0, 0))[1] for d in ds})
                    cells.append("分 0" if not g["trades"] else f"{_f(g['per_trade'], 4)} [{_f(g['lo'], 4)}, {_f(g['hi'], 4)}](分 {g['trades']:,})")
                L.append(f"| {lo}〜{hi} | {lbl} | {cells[0]} | {cells[1]} | {rate_diff(ds, mr, 'held_buy', 'held_sell')} |")
        L.append("")
    # 曜日
    wd = "月火水木金土日"
    L += ["## 曜日ごと(合図の時刻の日本時間の曜日。1 日あたり bp)【建ての前に決まる群】", "",
          "区間は、その曜日の日だけを並べた列を日の塊(5 日)で選び直したもの(並べた日は 7 日おき)。", "",
          "| 曜日 | 日数 | カード | 買いだけの対照 | カード − 買いだけの対照 |", "|---|---|---|---|---|"]
    from datetime import date as _date
    for k in range(7):
        ds = [d for d in days if _date.fromisoformat(d).weekday() == k]
        L.append(f"| {wd[k]} | {len(ds):,} | {ci(mean_ci([daily[d] for d in ds]))} | {ci(mean_ci([cc.get(d, 0.0) for d in ds]))} | "
                 f"{ci(mean_ci([daily[d] - cc.get(d, 0.0) for d in ds]))} |")
    L += ["", "曜日 × 前半・後半(カード / カード − 買いだけの対照 / 買いだけの対照、1 日あたり bp):", "",
          "| 曜日 | 前半 カード | 後半 カード | 前半 カード − 買いだけの対照 | 後半 カード − 買いだけの対照 | 前半 買いだけ | 後半 買いだけ |", "|---|---|---|---|---|---|---|"]
    for k in range(7):
        c = []
        for part in (days[:h], days[h:]):
            ds = [d for d in part if _date.fromisoformat(d).weekday() == k]
            c.append((ci(mean_ci([daily[d] - cc.get(d, 0.0) for d in ds])), ci(mean_ci([cc.get(d, 0.0) for d in ds])),
                      ci(mean_ci([daily[d] for d in ds]))))
        L.append(f"| {wd[k]} | {c[0][2]} | {c[1][2]} | {c[0][0]} | {c[1][0]} | {c[0][1]} | {c[1][1]} |")
    L.append("")
    # 勝ち負けの分解
    L += ["## 勝ち負けの分解(全期間・前半・後半・年ごと)", "",
          f"前半 = daily.csv の日を日数で 2 つに分けた前の半分({days[0]}〜{days[h-1]})、後半 = {days[h]}〜{days[-1]}(結果を見る前に決まる分け方。D1 と同じ)。",
          "", "| 区分 | 取引 | 和 | 勝ち 数 | 勝ち 和 | 勝ち 平均 | 勝ち 中央値 | 負け 数 | 負け 和 | 負け 平均 | 負け 中央値 | 損益 0 | 勝率 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    def row(lbl, ts):
        r = winloss(ts)
        return (f"| {lbl} | {r['n']:,} | {_f(r['sum'])} | {r['win_n']:,} | {_f(r['win_sum'])} | {_f(r['win_mean'])} | {_f(r['win_med'])} | "
                f"{r['loss_n']:,} | {_f(r['loss_sum'])} | {_f(r['loss_mean'])} | {_f(r['loss_med'])} | {r['zero_n']:,} | {_f(r['win_rate'], 3)} |")
    L.append(row("全期間", tr))
    L.append(row("前半", [t for t in tr if _jst_day(t["signal_ns"]) in first]))
    L.append(row("後半", [t for t in tr if _jst_day(t["signal_ns"]) not in first]))
    for y in sorted({_jst_day(t["signal_ns"])[:4] for t in tr}):
        L.append(row(y, [t for t in tr if _jst_day(t["signal_ns"])[:4] == y]))
    L.append("")
    # 損益の分位
    p = np.array([t["pnl_bp"] for t in tr])
    qs = (0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99)
    L += ["## 取引の損益の分位", "", "| " + " | ".join(f"{int(q*100)}%" for q in qs) + " |", "|" + "---|" * len(qs),
          "| " + " | ".join(_f(float(np.quantile(p, q))) for q in qs) + " |", ""]
    # 群
    hold = np.array([(t["exit_ns"] - t["entry_ns"]) / 6e10 for t in tr])
    edges = sorted(set(float(x) for x in np.quantile(hold, [0.25, 0.5, 0.75])))
    def hband(t):
        x = (t["exit_ns"] - t["entry_ns"]) / 6e10
        lo = None
        for e_ in edges:
            if x <= e_:
                return f"{'' if lo is None else f'{lo:g} 分超'}〜{e_:g} 分"
            lo = e_
        return f"{lo:g} 分超"
    groups = [
        ("向き【建ての前に決まる群】", lambda t: "買い" if t["side"] > 0 else "売り"),
        ("建ての時刻(合図の時刻の日本時間の時)【建ての前に決まる群】",
         lambda t: f"{datetime.fromtimestamp(t['signal_ns'] // 10**9, tz=JST).hour:02d} 時"),
        ("前半・後半 × 向き【建ての前に決まる群】",
         lambda t: ("前半" if _jst_day(t["signal_ns"]) in first else "後半") + " " + ("買い" if t["side"] > 0 else "売り")),
        ("保有時間の帯(四分位の境)【結果で決まる群】", hband),
    ]
    for gname, key in groups:
        L += [f"## {gname}", "", "| 群 | 取引 | 和 | 1 取引あたり | 区間 | 0 を |", "|---|---|---|---|---|---|"]
        for g, r in table(tr, days, key).items():
            z = "区間なし" if r["lo"] is None else ("含む" if r["lo"] <= 0 <= r["hi"] else ("正" if r["lo"] > 0 else "負"))
            L.append(f"| {g} | {r['trades']:,} | {_f(r['sum'])} | {_f(r['per_trade'], 3)} | [{_f(r['lo'], 3)}, {_f(r['hi'], 3)}] | {z} |")
        L.append("")
    L += ["保有時間の帯の境(分): " + ", ".join(f"{x:g}" for x in edges), ""]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", required=True)
    ap.add_argument("--trades-out", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--session-hour", type=int, default=None, help="セッションの始まりの UTC の時(カード 8: jst_day = 15、bf_maint = 19)")
    a = ap.parse_args(argv)
    if "docs/RESEARCH/WINDOW1" in os.path.abspath(a.measure).replace(os.sep, "/"):
        raise SystemExit("止める: 封印の窓の出力は読まない")
    b = build(a.measure, a.session_hour)
    daily = load_daily(a.measure)
    with open(os.path.join(a.measure, "extra.json"), encoding="utf-8") as fh:
        extra = json.load(fh)
    path = write_trades(b["trades"], a.trades_out)
    name = os.path.relpath(a.measure)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(render(name, b, daily, extra, path))
    print(a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
