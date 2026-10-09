#!/usr/bin/env python3
"""分析のスキル(`.claude/skills/analysis-lens`)の第 2 部の表を、このプロジェクトの測定の出力から出す共通の読み口。

新しい走らせはしない。既にある出力(カードの測定の `daily.csv`、指値の再現の `trades.csv.gz` / `trades.json.gz` と
`summary.json`)を読むだけ。封印の窓の出力は読まない(`--allow-window` は無い。窓の出力の置き場を渡したら止める)。

出す表(手順の番号はスキルの第 2 部):
  D0 入力の表: 出力の種類・期間・引数・列の有無と、その列で出せる手順
  D1 時間の表: 暦年ごとの 1 日あたり・95% 区間・MDE・区間が 0 を含むか(記述)/ 前半・後半(日数で 2 つに分ける。結果を
     見る前に決めた分け方)と 後半 − 前半 の区間 / 結果(崩れた・続いている・決まらない・後半だけ ほか。決まりは d1_outcome)
     --cut <日> を渡すと、その日を後半の最初の日にする(測定ごとに 1 つ、走らせる前に決めた境。本ごとに期間の始まりが
     立ち上がりの長さで違い、日数の真ん中が本ごとにずれるため。オーナー L-903「**境の統一は必要だが**」)。
  D3 集まりの表: 上位・下位 5% の日の損益の割合 / 取引の損益の分位 / 出の理由・合図の強さ・保有時間の四分位ごとの
     1 取引あたり(日の塊の区間)
  D6 固まりの表: 前の出から次の建てまでの間隔の四分位ごとの 1 取引あたり(日の塊の区間)
  D7 比べの表(--vs): 同じ日どうしの日ごとの差の平均・区間・MDE / 年ごとの差 / 取引の突き合わせ(建ての時刻で)
  D8 仮定の表(--bad): 良い側・悪い側の年ごとの 1 日あたりと符号が同じか / 決まらない足を含む取引の数と損益の割合 /
     仮定に左右されない部分(決まらない足を含まない取引だけ)の 1 日あたり。良い側とその部分の符号が違えば「止める」

決まり(スキル第 2 部の共通の決まり):
  - 損益は既に向きを含む(pnl_bp は取引の向きで符号を付けた損益)。値動きを使う計算(MFE など)はこの台本では出さない。
  - 区間は日の塊(循環、塊 5 日・1,000 回・種 20261004)。日ごとの損益の平均は `bot.bt.validation.block_bootstrap_ci`、
    取引の群の 1 取引あたりは、日を塊で選び直して群の損益の和 ÷ 取引の数を作り直す(同じ塊・回数・種)。
  - MDE は 5% 両側・80%・正規近似(`bot.bt.validation.mde`)。
  - 閾値で判定の言葉を出さない。「区間が 0 を含む」「符号が同じ」などの事実の列だけを出す。
  - 取引の日 = 出の時刻の UTC の暦日(改良の周 2 の読み R10・R6 と同じ)。カードの測定は `daily.csv` の日(日本時間)。

    PYTHONPATH=src python3 scripts/analysis/diag_tables.py --run <置き場> [--vs <比べる置き場>] [--bad <悪い側の置き場>] [--cut <YYYY-MM-DD>] --out <出力.md>
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timezone

import numpy as np

SEED, N_RES, BLOCK = 20261004, 1000, 5
WINDOW_MARK = "docs/RESEARCH/WINDOW1"  # 封印の窓の出力の置き場(読まない)


# ---------------------------------------------------------------- 読み

def _iso_ns(s: str) -> int:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return int(dt.timestamp()) * 10**9 + dt.microsecond * 1000


def load_run(d: str) -> dict:
    """出力の置き場を読む。種類 = card(daily.csv)/ trades(trades.csv.gz か trades.json.gz)。"""
    if WINDOW_MARK in os.path.abspath(d).replace(os.sep, "/"):
        raise SystemExit(f"止める: {d} は封印の窓の出力の置き場(この台本では読まない)")
    out: dict = {"dir": d, "name": os.path.basename(os.path.normpath(d)), "summary": None, "trades": None, "daily": None,
                 "fields": []}
    sp = os.path.join(d, "summary.json")
    if os.path.isfile(sp):
        with open(sp, encoding="utf-8") as fh:
            out["summary"] = json.load(fh)
    dp = os.path.join(d, "daily.csv")
    if os.path.isfile(dp):
        with open(dp, encoding="utf-8") as fh:
            out["daily"] = {r["day"]: float(r["pnl_bp"]) for r in csv.DictReader(fh)}
        out["kind"] = "card"
        return out
    cp, jp = os.path.join(d, "trades.csv.gz"), os.path.join(d, "trades.json.gz")
    rows = []
    if os.path.isfile(cp):
        with gzip.open(cp, "rt", encoding="utf-8", newline="") as fh:
            rd = csv.DictReader(fh)
            out["fields"] = list(rd.fieldnames or [])
            for r in rd:
                if r.get("in_measure", "True") == "False":
                    continue
                t = {"entry_ns": _iso_ns(r["entry_t"]), "exit_ns": _iso_ns(r["exit_t"]), "pnl_bp": float(r["pnl_bp"])}
                for k in ("exit_reason", "strength", "signal_t"):
                    if k in r:
                        t[k] = r[k]
                if "undecided" in r and r["undecided"] != "":
                    t["undecided"] = int(float(r["undecided"]))
                rows.append(t)
    elif os.path.isfile(jp):
        with gzip.open(jp, "rt", encoding="utf-8") as fh:
            o = json.load(fh)
        scale = {"ns": 1, "s": 10**9}[o["t_unit"]]
        out["fields"] = [k for k in o if k not in ("version", "t_unit")]
        rows = [{"entry_ns": int(e) * scale, "exit_ns": int(x) * scale, "pnl_bp": float(p)}
                for e, x, p in zip(o["entry_t_ns"], o["exit_t_ns"], o["pnl_bp"])]
    else:
        raise SystemExit(f"止める: {d} に daily.csv も trades.csv.gz も trades.json.gz も無い")
    rows.sort(key=lambda t: (t["entry_ns"], t["exit_ns"]))
    out["trades"] = rows
    out["kind"] = "trades"
    return out


def utc_day(ns: int) -> str:
    return datetime.fromtimestamp(ns // 10**9, tz=timezone.utc).date().isoformat()


def period_days(run: dict) -> list[str]:
    """日の一覧。trades は summary.json の period(無ければ最初と最後の取引)の UTC の日。card は daily.csv の日。"""
    if run["kind"] == "card":
        return sorted(run["daily"])
    if run["summary"] and run["summary"].get("period"):
        p0, p1 = run["summary"]["period"]
        lo = datetime.fromisoformat(p0.replace("Z", "+00:00")).date()
        hi = datetime.fromtimestamp((_iso_ns(p1) - 1) // 10**9, tz=timezone.utc).date()
    else:
        lo = date.fromisoformat(utc_day(run["trades"][0]["exit_ns"]))
        hi = date.fromisoformat(utc_day(run["trades"][-1]["exit_ns"]))
    return [date.fromordinal(o).isoformat() for o in range(lo.toordinal(), hi.toordinal() + 1)]


def daily_series(run: dict) -> dict[str, float]:
    days = period_days(run)
    if run["kind"] == "card":
        return dict(run["daily"])
    out = {d: 0.0 for d in days}
    for t in run["trades"]:
        d = utc_day(t["exit_ns"])
        if d in out:
            out[d] += t["pnl_bp"]
    return out


# ---------------------------------------------------------------- 統計

def mean_ci(x: list[float]) -> dict:
    from bot.bt.validation import block_bootstrap_ci, mde
    n = len(x)
    if n < BLOCK * 2:
        return {"n": n, "mean": float(np.mean(x)) if n else None, "lo": None, "hi": None, "mde": None}
    c = block_bootstrap_ci([float(v) for v in x], block_len=BLOCK, n_resamples=N_RES, seed=SEED, alpha=0.05,
                           method="circular", statistic="mean")
    sd = c.se * n ** 0.5
    return {"n": n, "mean": c.estimate, "lo": c.lo, "hi": c.hi,
            "mde": mde(n=n, sd=sd, alpha=0.05, power=0.80, sides=2, approx="normal") if sd > 0 else None}


def _boot_means(x: np.ndarray, rng) -> np.ndarray:
    n = len(x)
    nb = math.ceil(n / BLOCK)
    out = np.empty(N_RES)
    for i in range(N_RES):
        starts = rng.integers(0, n, size=nb)
        idx = (starts[:, None] + np.arange(BLOCK)[None, :]).ravel()[:n] % n
        out[i] = x[idx].mean()
    return out


def diff_ci(first: list[float], second: list[float]) -> dict:
    """後半 − 前半 の平均の差と 95% 区間(2 つの半分をそれぞれ日の塊で選び直し、差の分布の 2.5・97.5%)。"""
    a, b = np.array(first, dtype=float), np.array(second, dtype=float)
    if len(a) < BLOCK * 2 or len(b) < BLOCK * 2:
        return {"mean": float(b.mean() - a.mean()) if len(a) and len(b) else None, "lo": None, "hi": None}
    rng = np.random.default_rng(SEED)
    d = _boot_means(b, rng) - _boot_means(a, rng)
    lo, hi = np.percentile(d, [2.5, 97.5])
    return {"mean": float(b.mean() - a.mean()), "lo": float(lo), "hi": float(hi)}


def days_needed(x: list[float], effect: float | None) -> int | None:
    """前半の大きさ effect を、後半と同じ散らばりの日ごとの損益で見分けるのに要る日数(5% 両側・80%):
    (2.8 × 日ごとの標準偏差 ÷ |effect|)²。日の塊の依存は入れていない(目安)。"""
    if effect is None or effect == 0 or len(x) < 2:
        return None
    return int(np.ceil((2.8 * float(np.std(x, ddof=1)) / abs(effect)) ** 2))


def half_state(r: dict) -> str:
    """半分の状態: 正 = 区間が 0 より上 / 負 = 区間が 0 より下 / 含む = 区間が 0 を含む(区間なしも含む)。"""
    if r.get("lo") is None:
        return "含む"
    return "正" if r["lo"] > 0 else ("負" if r["hi"] < 0 else "含む")


def d1_outcome(first: dict, second: dict, diff: dict) -> str:
    """結果の決まり(閾値は置かない。戦略の向きは正 = 損益が正、で固定。標本から決めない):
    前半 × 後半 の状態(正・含む・負)と 後半 − 前半 の区間で決める。
      正 → 正: 続いている(差の区間が 0 より下なら「続いている(縮んだ)」)
      正 → 含む・負: 差の区間が 0 より下なら 崩れた、そうでなければ 決まらない
      含む・負 → 正: 後半だけ(成り立ち始めたのか偶然かは区別できない)
      含む → 含む、負 → 含む: 決まらない
      含む → 負: 後半は逆向き
      負 → 負: 成り立たない(逆向き)"""
    f, s2 = half_state(first), half_state(second)
    diff_down = diff.get("hi") is not None and diff["hi"] < 0
    if f == "正" and s2 == "正":
        return "続いている(縮んだ)" if diff_down else "続いている"
    if f == "正":
        return "崩れた" if diff_down else "決まらない"
    if s2 == "正":
        return "後半だけ"
    if f == "負" and s2 == "負":
        return "成り立たない(逆向き)"
    if s2 == "負":
        return "後半は逆向き"
    return "決まらない"


def group_ratio_ci(days: list[str], sums: dict[str, float], counts: dict[str, int]) -> dict:
    """群の 1 取引あたり = Σ損益 ÷ Σ取引の数。日を循環の塊で選び直して作り直す(塊 5・1,000 回・種 20261004)。"""
    s = np.array([sums.get(d, 0.0) for d in days])
    c = np.array([counts.get(d, 0) for d in days], dtype=float)
    n = len(days)
    tot_c = c.sum()
    if tot_c == 0:
        return {"trades": 0, "sum": 0.0, "per_trade": None, "lo": None, "hi": None}
    point = float(s.sum() / tot_c)
    if n < BLOCK * 2:
        return {"trades": int(tot_c), "sum": float(s.sum()), "per_trade": point, "lo": None, "hi": None}
    rng = np.random.default_rng(SEED)
    nb = math.ceil(n / BLOCK)
    reps = []
    for _ in range(N_RES):
        starts = rng.integers(0, n, size=nb)
        idx = (starts[:, None] + np.arange(BLOCK)[None, :]).ravel()[:n] % n
        cc = c[idx].sum()
        if cc > 0:
            reps.append(s[idx].sum() / cc)
    lo, hi = np.percentile(reps, [2.5, 97.5])
    return {"trades": int(tot_c), "sum": float(s.sum()), "per_trade": point, "lo": float(lo), "hi": float(hi)}


def contains_zero(r: dict) -> str:
    if r.get("lo") is None:
        return "区間なし"
    return "含む" if r["lo"] <= 0 <= r["hi"] else ("正" if r["lo"] > 0 else "負")


# ---------------------------------------------------------------- D0〜D8

def signal_delay(run: dict, valid_min: float | None) -> dict | None:
    """合図が分かった時刻 → 建ての時刻(entry_t = 約定した足の終わり)の分。valid_min(合図の有効期間、分)を渡すと、
    それを越えて建った取引の数・損益の和を分ける(L-659: 合図の意味が切れた後の約定が混ざっていないか)。"""
    ts = [t for t in (run["trades"] or []) if t.get("signal_t")]
    if not ts:
        return None
    d = np.array([(t["entry_ns"] - _iso_ns(t["signal_t"])) / 6e10 for t in ts])
    out = {"trades": len(ts), "q": {str(q): float(np.percentile(d, q)) for q in (25, 50, 75, 90, 99)},
           "max": float(d.max()), "valid_min": valid_min}
    if valid_min is not None:
        pn = np.array([t["pnl_bp"] for t in ts])
        late = d > valid_min
        out["within"] = {"trades": int((~late).sum()), "sum": float(pn[~late].sum())}
        out["late"] = {"trades": int(late.sum()), "sum": float(pn[late].sum())}
    return out


def d0(run: dict, valid_min: float | None = None) -> dict:
    s = run["summary"] or {}
    have = set(run["fields"])
    steps = {"D1 時間": True, "D3 日の集まり": True,
             "D3 取引の分位": run["kind"] == "trades",
             "D3 出の理由ごと": "exit_reason" in have, "D3 合図の強さごと": "strength" in have,
             "D3 保有時間ごと": run["kind"] == "trades", "D6 固まり": run["kind"] == "trades",
             "D8 決まらない足": "undecided" in have}
    return {"name": run["name"], "kind": run["kind"], "period": s.get("period"), "params": s.get("params"),
            "fields": run["fields"], "steps": steps,
            "trades": len(run["trades"]) if run["trades"] is not None else None,
            "signal_delay": signal_delay(run, valid_min)}


def d1(daily: dict[str, float], cut: str | None = None) -> dict:
    """cut = 後半の最初の日(渡さなければ日数の真ん中の日)。cut の前と後の両方に日が無ければ止める。"""
    days = sorted(daily)
    rows = [{"label": "全期間", **mean_ci([daily[d] for d in days])}]
    years = sorted({d[:4] for d in days})
    for y in years:
        rows.append({"label": y, **mean_ci([daily[d] for d in days if d[:4] == y])})
    for r in rows:
        r["zero"] = contains_zero(r)
    if cut is None:
        h = len(days) // 2
    else:
        h = sum(1 for d in days if d < cut)
        if not 0 < h < len(days):
            raise SystemExit(f"--cut {cut} は期間 {days[0]}〜{days[-1]} の中に無い")
    first, second = [daily[d] for d in days[:h]], [daily[d] for d in days[h:]]
    seg = {"first": {"from": days[0], "to": days[h - 1], **mean_ci(first)},
           "second": {"from": days[h], "to": days[-1], **mean_ci(second)},
           "diff": diff_ci(first, second),
           "cut": days[h], "cut_source": "渡した日(--cut)" if cut is not None else "日数の真ん中"}
    seg["outcome"] = d1_outcome(seg["first"], seg["second"], seg["diff"])
    seg["days_needed"] = days_needed(second, seg["first"].get("mean"))
    seg["days_needed_second"] = days_needed(second, seg["second"].get("mean"))
    return {"rows": rows, "segments": seg}


def d3(run: dict, daily: dict[str, float]) -> dict:
    days = sorted(daily)
    v = np.array([daily[d] for d in days])
    tot = float(v.sum())
    k = max(1, int(round(len(v) * 0.05)))
    srt = np.sort(v)
    out = {"total": tot, "days": len(v), "top5_days_sum": float(srt[-k:].sum()), "bottom5_days_sum": float(srt[:k].sum()),
           "k": k}
    if run["kind"] != "trades":
        return out
    tr = run["trades"]
    p = np.array([t["pnl_bp"] for t in tr])
    out["trade_quantiles"] = {q: float(np.quantile(p, q)) for q in (0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99)}
    out["n_trades"] = len(tr)
    hold = [(t["exit_ns"] - t["entry_ns"]) / 6e10 for t in tr]
    qs, hband = bands_by_edges(hold)
    # 群は 2 種類: 建ての前に決まる群(原因の候補として比べられる)と、結果で決まる群(群どうしの差から原因を言えない)
    groups = {"保有時間の帯【結果で決まる群】": lambda t: hband((t["exit_ns"] - t["entry_ns"]) / 6e10)}
    if any("exit_reason" in t for t in tr):
        groups["出の理由【結果で決まる群】"] = lambda t: t.get("exit_reason", "")
    if any("strength" in t for t in tr):
        groups["合図の強さ【建ての前に決まる群】"] = lambda t: t.get("strength", "")
    out["hold_edges_min"] = qs
    out["groups"] = {name: group_table(tr, days, f) for name, f in groups.items()}
    return out


def bands_by_edges(values: list[float]):
    """四分位の境を、同じ値をまとめて重ならない境にする。帯の名前は実際の範囲(分)。"""
    edges = sorted(set(float(x) for x in np.quantile(values, [0.25, 0.5, 0.75])))
    def name(x):
        lo = None
        for e in edges:
            if x <= e:
                return _rng(lo, e)
            lo = e
        return _rng(lo, None)
    return edges, name


def _rng(lo, hi):
    if lo is None:
        return f"〜{hi:g} 分"
    if hi is None:
        return f"{lo:g} 分超"
    return f"{lo:g} 分超〜{hi:g} 分"


def group_table(tr: list[dict], days: list[str], key) -> dict:
    sums: dict = defaultdict(lambda: defaultdict(float))
    cnts: dict = defaultdict(lambda: defaultdict(int))
    for t in tr:
        g, d = key(t), utc_day(t["exit_ns"])
        sums[g][d] += t["pnl_bp"]
        cnts[g][d] += 1
    return {g: group_ratio_ci(days, sums[g], cnts[g]) for g in sorted(sums)}


def d6(run: dict, daily: dict[str, float]) -> dict | None:
    if run["kind"] != "trades":
        return None
    tr = run["trades"]
    gaps = [(tr[i]["entry_ns"] - tr[i - 1]["exit_ns"]) / 6e10 for i in range(1, len(tr))]
    qs, band = bands_by_edges(gaps)
    keyed = [dict(t, _band=band(x)) for t, x in zip(tr[1:], gaps)]  # 最初の取引は間隔が無いので外す
    return {"gap_edges_min": qs,
            "groups": group_table(keyed, sorted(daily), lambda t: t["_band"])}


def d7(a: dict, b: dict) -> dict:
    da, db = daily_series(a), daily_series(b)
    common = sorted(set(da) & set(db))
    diff = [da[d] - db[d] for d in common]
    out = {"all": mean_ci(diff), "years": {}}
    for y in sorted({d[:4] for d in common}):
        out["years"][y] = mean_ci([da[d] - db[d] for d in common if d[:4] == y])
    if a["kind"] == "trades" and b["kind"] == "trades":
        key = "signal_t" if all("signal_t" in t for t in a["trades"] + b["trades"]) else "entry_ns"
        ka, kb = defaultdict(float), defaultdict(float)
        for t in a["trades"]:
            ka[t[key]] += t["pnl_bp"]
        for t in b["trades"]:
            kb[t[key]] += t["pnl_bp"]
        out["match_key"] = key
        both = set(ka) & set(kb)
        out["match"] = {"both": len(both), "only_a": len(set(ka) - both), "only_b": len(set(kb) - both),
                        "sum_only_a": float(sum(ka[k] for k in set(ka) - both)),
                        "sum_only_b": float(sum(kb[k] for k in set(kb) - both)),
                        "sum_both_a_minus_b": float(sum(ka[k] - kb[k] for k in both))}
    return out


def d8(good: dict, bad: dict) -> dict:
    dg, db = daily_series(good), daily_series(bad)
    rows = []
    for y in ["全期間"] + sorted({d[:4] for d in dg}):
        sel = (lambda d: True) if y == "全期間" else (lambda d, y=y: d[:4] == y)
        rg = mean_ci([dg[d] for d in sorted(dg) if sel(d)])
        rb = mean_ci([db[d] for d in sorted(db) if sel(d)])
        same = None if rg["mean"] is None or rb["mean"] is None else (np.sign(rg["mean"]) == np.sign(rb["mean"]))
        rows.append({"label": y, "good": rg, "bad": rb, "same_sign": bool(same) if same is not None else None})
    free = {}
    for name, r in (("good", good), ("bad", bad)):
        if r["kind"] == "trades" and any("undecided" in t for t in r["trades"]):
            fr = dict(r, trades=[t for t in r["trades"] if t.get("undecided", 0) == 0])
            dfree = daily_series(fr)
            free[name] = mean_ci([dfree[d] for d in sorted(dfree)])
    stop = rows[0]["same_sign"] is False
    if "good" in free and free["good"]["mean"] is not None and rows[0]["good"]["mean"] is not None:
        stop = stop or bool(np.sign(free["good"]["mean"]) != np.sign(rows[0]["good"]["mean"]))
    und = {}
    for name, r in (("good", good), ("bad", bad)):
        if r["kind"] == "trades" and any("undecided" in t for t in r["trades"]):
            u = [t for t in r["trades"] if t.get("undecided", 0) > 0]
            tot = sum(t["pnl_bp"] for t in r["trades"])
            und[name] = {"trades": len(u), "share_trades": len(u) / len(r["trades"]),
                         "pnl_sum": float(sum(t["pnl_bp"] for t in u)), "pnl_total": float(tot)}
    return {"rows": rows, "undecided": und, "assumption_free": free, "stop": stop}


# ---------------------------------------------------------------- 書き出し

def _f(x, nd=2):
    return "—" if x is None else f"{x:+.{nd}f}"


def _ci(r):
    return f"{_f(r.get('mean', r.get('per_trade')))} [{_f(r.get('lo'))}, {_f(r.get('hi'))}]"


def render(res: dict) -> str:
    L = [f"# 診断の表: {res['d0']['name']}", "",
         "`scripts/analysis/diag_tables.py` が出した(手で書いていない)。損益は bp、経費の前。区間は 95%(日の塊 5 日・1,000 回)。"
         "MDE は 5% 両側・80%。", ""]
    z = res["d0"]
    L += ["## D0 入力", "", f"- 種類: {z['kind']} / 期間: {z['period']} / 取引: {z['trades']}",
          f"- 引数: `{json.dumps(z['params'], ensure_ascii=False) if z['params'] else '—'}`",
          f"- 列: {', '.join(z['fields']) if z['fields'] else '(daily.csv: day, pnl_bp, n)'}",
          "- 出せる手順: " + "、".join(f"{k} {'○' if v else '✕(列が無い)'}" for k, v in z["steps"].items())]
    sd = z.get("signal_delay")
    if sd:
        L.append("- 合図が分かった時刻 → 建ての時刻(分。建ての時刻は約定した 1 分足の終わり)の 25・50・75・90・99% 点: "
                 + "・".join(_f(v) for v in sd["q"].values()) + f"、最大 {_f(sd['max'])}(取引 {sd['trades']})")
        if sd["valid_min"] is None:
            L.append("- **合図の有効期間が決まっていない**(`--valid-min` で渡す。スキル P・D0)。有効期間を越えて建った取引は、合図の評価には混ざりもの")
        else:
            L.append(f"- 合図の有効期間 {_f(sd['valid_min'])} 分: 以内に建った {sd['within']['trades']} 本・和 {_f(sd['within']['sum'])}、"
                     f"**越えて建った {sd['late']['trades']} 本・和 {_f(sd['late']['sum'])}**(結果で決まる群。期限を付けた形の損益はここから言えない)")
    L.append("")
    d1r = res["d1"]
    L += ["## D1 時間(1 日あたり、bp/日)", "", "年ごと(記述。区切りの判断には使わない):", "",
          "| 期間 | 日数 | 1 日あたり [区間] | MDE | 区間が 0 を |", "|---|---|---|---|---|"]
    for r in d1r["rows"]:
        L.append(f"| {r['label']} | {r['n']} | {_ci(r)} | {_f(r['mde'])} | {r['zero']} |")
    sg = d1r["segments"]
    how = ("測定ごとに 1 つ、走らせる前に決めた日(--cut)" if sg.get("cut_source") == "渡した日(--cut)"
           else "日数で 2 つに分ける。結果を見る前に決めた分け方")
    L += ["", f"前半・後半({how}。後半の最初の日 {sg['cut']}):", "",
          "| 区切り | 期間 | 日数 | 1 日あたり [区間] | MDE |", "|---|---|---|---|---|",
          f"| 前半 | {sg['first']['from']}〜{sg['first']['to']} | {sg['first']['n']} | {_ci(sg['first'])} | {_f(sg['first']['mde'])} |",
          f"| 後半 | {sg['second']['from']}〜{sg['second']['to']} | {sg['second']['n']} | {_ci(sg['second'])} | {_f(sg['second']['mde'])} |",
          f"| 後半 − 前半 | | | {_ci(sg['diff'])} | |", "",
          f"- 0 と見分けるのに要る日数の目安(後半の散らばりで。日の依存は入れていない。後半は {sg['second']['n']} 日): "
          f"前半の大きさ({_f(sg['first']['mean'])})なら {sg.get('days_needed') or '—'} 日、"
          f"後半の点({_f(sg['second']['mean'])})なら {sg.get('days_needed_second') or '—'} 日",
          f"- 結果(決まり d1_outcome): **{sg['outcome']}**"
          + ("。全期間の行は一部の期間の稼ぎ" if sg["outcome"] in ("崩れた", "後半だけ") else ""), ""]
    d3r = res["d3"]
    L += ["## D3 集まり", "",
          f"- 全体の和 {_f(d3r['total'],0)} bp({d3r['days']} 日)。上位 5% の日({d3r['k']} 日)の和 {_f(d3r['top5_days_sum'],0)} bp、"
          f"下位 5% の日の和 {_f(d3r['bottom5_days_sum'],0)} bp。", ""]
    if "trade_quantiles" in d3r:
        q = d3r["trade_quantiles"]
        L += [f"- 取引 {d3r['n_trades']} 本の損益の分位(bp): " + "、".join(f"{int(k*100)}% {_f(v)}" for k, v in q.items()),
              ""]
        for gname, tab in d3r["groups"].items():
            note = ("(取引の結果で群が決まるので、群どうしの差から原因は言えない。記述だけ)" if "結果で決まる" in gname
                    else "(建ての前に決まる群。群どうしの差は原因の候補になる)")
            L += [f"### {gname}ごとの 1 取引あたり(bp)", "", note, "", "| 群 | 取引 | 和 | 1 取引あたり [区間] |", "|---|---|---|---|"]
            for g, r in tab.items():
                L.append(f"| {g or '(空)'} | {r['trades']} | {_f(r['sum'],0)} | {_ci(r)} |")
            L.append("")
    if res.get("d6"):
        r6 = res["d6"]
        L += ["## D6 固まり(前の出から次の建てまでの間隔の帯ごと、1 取引あたり bp。帯は四分位の境を重ならないようにまとめたもの)", "",
              "| 間隔 | 取引 | 和 | 1 取引あたり [区間] |", "|---|---|---|---|"]
        for g, r in r6["groups"].items():
            L.append(f"| {g} | {r['trades']} | {_f(r['sum'],0)} | {_ci(r)} |")
        L.append("")
    if res.get("d7"):
        r7 = res["d7"]
        L += [f"## D7 比べ({res['d0']['name']} − {res['vs_name']}、同じ日どうしの日ごとの差、bp/日)", "",
              "| 期間 | 日数 | 差 [区間] | MDE | 区間が 0 を |", "|---|---|---|---|---|",
              f"| 全期間 | {r7['all']['n']} | {_ci(r7['all'])} | {_f(r7['all']['mde'])} | {contains_zero(r7['all'])} |"]
        for y, r in r7["years"].items():
            L.append(f"| {y} | {r['n']} | {_ci(r)} | {_f(r['mde'])} | {contains_zero(r)} |")
        if "match" in r7:
            m = r7["match"]
            L += ["", f"- 取引の突き合わせ({'合図の時刻' if r7.get('match_key') == 'signal_t' else '建ての時刻'}): 両方 {m['both']} 本(差の和 {_f(m['sum_both_a_minus_b'],0)} bp)/ "
                  f"こちらだけ {m['only_a']} 本(和 {_f(m['sum_only_a'],0)})/ 相手だけ {m['only_b']} 本(和 {_f(m['sum_only_b'],0)})"]
        L.append("")
    if res.get("d8"):
        r8 = res["d8"]
        L += ["## D8 仮定(良い側・悪い側、1 日あたり bp/日)", "", "| 期間 | 良い側 [区間] | 悪い側 [区間] | 符号が同じ |", "|---|---|---|---|"]
        for r in r8["rows"]:
            L.append(f"| {r['label']} | {_ci(r['good'])} | {_ci(r['bad'])} | {r['same_sign']} |")
        for k, f in r8.get("assumption_free", {}).items():
            L.append(f"- 仮定に左右されない部分({k}。決まらない足を含まない取引だけ)の 1 日あたり: {_ci(f)} bp/日")
        L.append("  (注: 決まらない足を含まない取引は、含む取引と性質が違う(利確に届かずに止まった取引に寄る)。この値は戦略の損益の"
                 "見積もりではなく、仮定の外にある部分の大きさ)")
        L.append(f"- 止める(良い側と悪い側の全期間の符号が違う、または良い側と仮定に左右されない部分の符号が違う): **{r8['stop']}**")
        for k, u in r8["undecided"].items():
            L.append(f"- 決まらない足を含む取引({k}): {u['trades']} 本({u['share_trades']:.1%})、その損益の和 {_f(u['pnl_sum'],0)} bp"
                     f"(全体 {_f(u['pnl_total'],0)} bp)")
        L.append("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--vs", default=None)
    ap.add_argument("--bad", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--valid-min", type=float, default=None, help="合図の有効期間(分)。設計の前に決めた値を渡す")
    ap.add_argument("--cut", default=None, help="後半の最初の日(YYYY-MM-DD)。測定ごとに 1 つ、走らせる前に決めた日を全部の本に渡す")
    a = ap.parse_args(argv)
    if a.cut is not None:
        # YYYY-MM-DD の 10 字だけを受ける(fromisoformat は 20191209・2019-W50-1 も受け、文字列の比べで境が静かにずれる。批評家 1 回目)
        if len(a.cut) != 10 or date.fromisoformat(a.cut).isoformat() != a.cut:
            raise SystemExit(f"--cut {a.cut} は YYYY-MM-DD の形でない")
    run = load_run(a.run)
    daily = daily_series(run)
    res = {"d0": d0(run, a.valid_min), "d1": d1(daily, a.cut), "d3": d3(run, daily), "d6": d6(run, daily)}
    if a.vs:
        vs = load_run(a.vs)
        res["d7"], res["vs_name"] = d7(run, vs), vs["name"]
    if a.bad:
        res["d8"] = d8(run, load_run(a.bad))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(render(res) + "\n")
    with open(os.path.splitext(a.out)[0] + ".json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    print(f"-> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
