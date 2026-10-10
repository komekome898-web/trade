"""前提の直接の測り(D1b)の台本: 中心から 4 ボラ外れた値段が、起点の後 40 分でどう動くかを、戦略を回さずに 1 分足だけで数える。

決まりの正本: docs/DISCUSSIONS/2026-10-08_matilda_main/D1B_SPEC.md と、受け入れの試験 tests/research/test_d1b_spec.py
(試験の頭の注が、この台本の口 SEAL・CUT・LABELS・base_params・outcome・starts・ratio_diff_ci・summarize・main を決める)。

線(ボラ・中心・建ての線・ブレイクの線・門・ブレイク中の印)は、戦略 MatildaSimple に足が閉じた時点(kind が close)
だけを渡して decide で作ったものをそのまま使い、ここでは計算し直さない。道の中の戦略は足の途中でも呼ばれるので、
ブレイク中の印とブレイクの線は道の中の値と同じではない(D1B_SPEC.md §2 の限界)。

走らせ方(全期間の走らせは受け取りの後にリードがする):
PYTHONPATH=src python3 scripts/analysis/d1b_matilda.py --files backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_201[5-9].csv.gz backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_202[0-3].csv.gz --out docs/RESEARCH/matilda_main/d1b

出力: <out>/day_counts.csv(日 × 側 × 入り × 門 × ブレイク中の印 × 結果ごとの起点の数)・<out>/tables.md(4 つの見方ごとの表)。
"""
from __future__ import annotations

import argparse
import copy
import csv
import math
import os
import statistics
import sys
from collections import deque
from datetime import datetime, timedelta, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import diag_tables as dt  # noqa: E402

from bot.bt.simple import read_bars  # noqa: E402
from bot.strategy.matilda_simple import BASE_PARAMS, MatildaSimple  # noqa: E402

SEAL = "2023-12-17T15:00:00+00:00"  # 封印の境(これ以後に始まる足は読まない)
CUT = "2019-12-09"  # 前半・後半の境(D1 と同じ。day < CUT が前半)
LABELS = ("i", "ii", "iii", "iv", "both")
VIEWS = ("entry_open", "entry_all", "point_open", "point_all")
VIEW_NAMES = {
    "entry_open": "入りごと × 門が開いていて足が閉じた時点の判定でブレイク中でない",
    "entry_all": "入りごと × 全部",
    "point_open": "時点ごと × 門が開いていて足が閉じた時点の判定でブレイク中でない",
    "point_all": "時点ごと × 全部",
}
LABEL_NAMES = {
    "i": "i 20分以内に利確の線",
    "ii": "ii 21〜40分に起点の値段",
    "iii": "iii ブレイクの線に先に",
    "iv": "iv どれも無し",
    "both": "both 同じ足で両方",
}
WINDOW = 40  # 起点の後に見る分
_VIEW_FILTER = {
    "entry_open": lambda r: bool(r["entry"]) and bool(r["gate"]) and r["brk"] == 0,
    "entry_all": lambda r: bool(r["entry"]),
    "point_open": lambda r: bool(r["gate"]) and r["brk"] == 0,
    "point_all": lambda r: True,
}


# ------------------------------------------------------------------ 時刻・引数
def _parse(ts: str) -> datetime:
    """足の始まりの時刻の文字列を時差の付いた時刻に(末尾 Z は UTC)。時差が無ければ ValueError。"""
    d = datetime.fromisoformat(ts.replace("Z", "+00:00") if isinstance(ts, str) else ts)
    if d.tzinfo is None:
        raise ValueError(f"時刻に時差の印が無い: {ts!r}")
    return d


def base_params() -> dict:
    """基準の引数(BASE_PARAMS に 5 段・建て 4・利確 3 を上書きした新しい dict)。"""
    p = copy.deepcopy(dict(BASE_PARAMS))
    p.update({"levels": 5, "entry_setting": 4, "exit_setting": 3})
    return p


def _minutes(t: datetime, t0: datetime) -> int:
    """起点の足から数えた分 k(足の始まりの差を分に丸める)。"""
    return round((t - t0).total_seconds() / 60)


# ------------------------------------------------------------------ 起点の後の結果
def _outcome_k(side: int, c0: float, tp_line: float, break_line, kpath) -> tuple:
    """kpath = (k, 高値, 安値) の並び(時刻の順)。1 ≤ k ≤ 40 の足だけを k の順に見て、最初に何かが起きた足で決める。"""
    for k, h, lo in kpath:
        if k < 1 or k > WINDOW:
            continue
        if side == -1:  # 上の起点: 下へ戻るのを待つ
            hit_b = break_line is not None and h >= break_line
            hit_r = (lo <= tp_line) if k <= 20 else (lo <= c0)
        else:  # 下の起点: 上下を入れ替える
            hit_b = break_line is not None and lo <= break_line
            hit_r = (h >= tp_line) if k <= 20 else (h >= c0)
        if hit_r and hit_b:
            return "both", k
        if hit_r:
            return ("i" if k <= 20 else "ii"), k
        if hit_b:
            return "iii", k
    return "iv", None


def outcome(side, c0, tp_line, break_line, path, t0) -> tuple:
    """起点より後の足 path = (ts, 高値, 安値) の並びから (結果, k) を決める。決まりは試験の頭の注。"""
    t0d = _parse(t0)
    kpath = [(_minutes(_parse(ts), t0d), h, lo) for ts, h, lo in path]
    return _outcome_k(side, c0, tp_line, break_line, kpath)


# ------------------------------------------------------------------ 足を前から 1 回だけ読んで起点を作る
class _Pending:
    """結果がまだ決まらない起点(後の 40 分の足を集めている)。"""

    __slots__ = ("rec", "t0", "kpath", "n_win")

    def __init__(self, rec: dict, t0: datetime) -> None:
        self.rec, self.t0, self.kpath, self.n_win = rec, t0, [], 0


def _finish(pd: _Pending) -> dict:
    rec = pd.rec
    rec["outcome"], rec["k"] = _outcome_k(rec["side"], rec["c0"], rec["tp_line"], rec["break_line"], pd.kpath)
    rec["n_win"] = pd.n_win
    return rec


def starts(bars, params=None, seal: str = SEAL) -> dict:
    """足(read_bars と同じ形)を前から 1 回だけ読み、起点の記録 records と評価した足の日 days を返す。"""
    p = base_params() if params is None else params
    seal_t = _parse(seal)
    ex = p["exit_setting"]
    st = MatildaSimple(p)
    pending: deque = deque()
    records: list = []
    days: list = []
    prev = None  # 飛ばさずに回した直前の足の終値
    prev_side = None  # 直前に評価した足の側(起点でなければ None)
    last_t = None  # 直前に読んだ足(飛ばした足を含む)の時刻
    end = None
    for bar in bars:
        t = _parse(bar[0])
        if t >= seal_t:
            end = seal_t
            break
        if last_t is not None and t <= last_t:
            raise ValueError(f"足の時刻が増えていない: {bar[0]}")
        last_t = t
        o, h, lo, c = bar[1], bar[2], bar[3], bar[4]
        if o == c and (prev is None or o == prev):
            continue  # 向きの決まらない足は無い足として飛ばす(道と同じ)
        prev = c
        # 先に、すでにある起点へこの足を渡す(この足自身は起点の後の足ではない)
        while pending and (t - pending[0].t0) >= timedelta(minutes=WINDOW + 1):
            records.append(_finish(pending.popleft()))
        for pd in pending:
            k = _minutes(t, pd.t0)
            pd.kpath.append((k, h, lo))
            if 1 <= k <= WINDOW:
                pd.n_win += 1
        st.decide({"kind": "close", "ts": bar[0], "price": c, "fills": [], "touched": [], "bar": bar})
        sn = st._snap
        if sn is None or sn["vola"] <= 0:
            continue  # 慣らしの間・ボラが 0 の足は評価しない
        day = bar[0][:10]
        if not days or days[-1] != day:
            days.append(day)
        side = -1 if c > sn["up"] else (1 if c < sn["lo"] else None)
        was, prev_side = prev_side, side
        if side is None:
            continue
        rec = {"ts": bar[0], "day": day, "side": side, "entry": was != side, "gate": bool(sn["gate"]), "brk": st._brk,
               "c0": c, "center": sn["center"], "vola": sn["vola"], "width": st.ind["width"],
               "tp_line": sn["center"] - side * ex * sn["vola"],
               "break_line": sn["bu"] if side == -1 else sn["bd"]}
        pending.append(_Pending(rec, t))
    if end is None:
        end = last_t + timedelta(minutes=1) if last_t is not None else None
    # 後ろの 40 分が終わっている起点だけ記録する(終わり近くの起点は捨てる)
    while pending:
        pd = pending.popleft()
        if end is not None and pd.t0 + timedelta(minutes=WINDOW + 1) <= end:
            records.append(_finish(pd))
    return {"records": records, "days": days}


# ------------------------------------------------------------------ 割合と差の区間
def _boot_ratios(x: np.ndarray, y: np.ndarray, rng) -> list:
    """日の塊(5)の循環の選び直しで Σx ÷ Σy を 1,000 回作り直す。Σy = 0 の回は None。"""
    n = len(x)
    nb = math.ceil(n / dt.BLOCK)
    out = []
    for _ in range(dt.N_RES):
        s = rng.integers(0, n, size=nb)
        idx = (s[:, None] + np.arange(dt.BLOCK)[None, :]).ravel()[:n] % n
        dd = y[idx].sum()
        out.append(x[idx].sum() / dd if dd > 0 else None)
    return out


def ratio_diff_ci(days_a, num_a, den_a, days_b, num_b, den_b) -> dict:
    """後半 b − 前半 a の割合の差: 点・95% 区間・MDE(2.8 × 差の標準偏差)。どちらかの分母が 0 なら 4 つとも None。"""
    none = {"mean": None, "lo": None, "hi": None, "mde": None}
    xa = np.array([num_a.get(d, 0) for d in days_a], dtype=float)
    ya = np.array([den_a.get(d, 0) for d in days_a], dtype=float)
    xb = np.array([num_b.get(d, 0) for d in days_b], dtype=float)
    yb = np.array([den_b.get(d, 0) for d in days_b], dtype=float)
    if len(xa) == 0 or len(xb) == 0 or ya.sum() == 0 or yb.sum() == 0:
        return none
    rng = np.random.default_rng(dt.SEED)
    rb = _boot_ratios(xb, yb, rng)
    ra = _boot_ratios(xa, ya, rng)
    d = np.array([b - a for a, b in zip(ra, rb) if a is not None and b is not None])
    if len(d) < 2:
        return none
    lo, hi = np.percentile(d, [2.5, 97.5])
    return {"mean": float(xb.sum() / yb.sum() - xa.sum() / ya.sum()), "lo": float(lo), "hi": float(hi),
            "mde": 2.8 * float(np.std(d, ddof=1))}


def _cell(sel: list, label: str) -> dict:
    n = len(sel)
    cnt = sum(1 for r in sel if r["outcome"] == label)
    return {"n": n, "count": cnt, "share": (cnt / n) if n else None}


def summarize(records, days, cut: str = CUT) -> dict:
    """res[見方][期間][結果] = {"n","count","share"}(first・second は "lo"・"hi" も)。res[見方]["diff"][結果] = 差の区間。"""
    years = sorted({d[:4] for d in days} | {r["day"][:4] for r in records})
    halves = {"first": [d for d in days if d < cut], "second": [d for d in days if d >= cut]}
    res: dict = {}
    for view in VIEWS:
        sel = [r for r in records if _VIEW_FILTER[view](r)]
        v: dict = {}
        for y in years:
            ry = [r for r in sel if r["day"][:4] == y]
            v[y] = {lab: _cell(ry, lab) for lab in LABELS}
        den: dict = {}
        num: dict = {}
        for name, hd in halves.items():
            keep = set(hd)
            rs = [r for r in sel if r["day"] in keep]
            den[name] = {}
            for r in rs:
                den[name][r["day"]] = den[name].get(r["day"], 0) + 1
            num[name] = {lab: {} for lab in LABELS}
            for r in rs:
                num[name][r["outcome"]][r["day"]] = num[name][r["outcome"]].get(r["day"], 0) + 1
            v[name] = {}
            for lab in LABELS:
                c = _cell(rs, lab)
                g = dt.group_ratio_ci(hd, num[name][lab], den[name]) if rs else {"lo": None, "hi": None}
                c["lo"], c["hi"] = g["lo"], g["hi"]
                v[name][lab] = c
        v["diff"] = {lab: ratio_diff_ci(halves["first"], num["first"][lab], den["first"],
                                        halves["second"], num["second"][lab], den["second"]) for lab in LABELS}
        res[view] = v
    return res


# ------------------------------------------------------------------ 出力
def _pct(x, signed: bool = False) -> str:
    if x is None:
        return "-"
    return f"{100 * x:+.1f}" if signed else f"{100 * x:.1f}"


def _med(vals: list) -> str:
    return f"{statistics.median(vals):.2f}" if vals else "-"


def _period_of(r: dict, period: str, cut: str) -> bool:
    if period == "first":
        return r["day"] < cut
    if period == "second":
        return r["day"] >= cut
    return r["day"][:4] == period


def render_tables(res: dict, records: list, days: list, cut: str = CUT) -> str:
    years = sorted({d[:4] for d in days} | {r["day"][:4] for r in records})
    periods = years + ["first", "second"]
    out = ["# D1b 起点の後 40 分の結果(マチルダ基準の前提の直接の測り)", "",
           f"割合は % で小数 1 桁。first = 日が {cut} より前、second = {cut} 以後。区間は日の塊(5 日・1,000 回・種 {dt.SEED})で"
           "日を選び直した 95%。差 = second − first(百分率ポイント)、MDE = 2.8 × 差の標準偏差。",
           "幅 ÷ ボラ は起点の時点の値(起点だけの母集団)で、`width_vola.out` の全部の足の値とは母集団が違う。"
           "n_win は起点の後 40 分の中の飛ばさない足の数。", ""]
    for view in VIEWS:
        out += [f"## {view}: {VIEW_NAMES[view]}", ""]
        sel = [r for r in records if _VIEW_FILTER[view](r)]
        head = ["期間", "起点の数"] + [f"{LABEL_NAMES[lab]} %" for lab in LABELS] + ["幅 ÷ ボラ の中央値", "n_win の中央値"]
        out += ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        for per in periods:
            rs = [r for r in sel if _period_of(r, per, cut)]
            cells = [per, str(len(rs))] + [_pct(res[view][per][lab]["share"]) for lab in LABELS]
            cells += [_med([r["width"] / r["vola"] for r in rs]), _med([r["n_win"] for r in rs if "n_win" in r])]
            out.append("| " + " | ".join(cells) + " |")
        out += ["", "| 結果 | first の区間 % | second の区間 % | diff の点 pt | diff の区間 pt | diff の MDE pt |", "|---|---|---|---|---|---|"]
        for lab in LABELS:
            f, s, d = res[view]["first"][lab], res[view]["second"][lab], res[view]["diff"][lab]
            ci = lambda c: f"{_pct(c['lo'])} 〜 {_pct(c['hi'])}"  # noqa: E731
            out.append(f"| {LABEL_NAMES[lab]} | {ci(f)} | {ci(s)} | {_pct(d['mean'], True)} | "
                       f"{_pct(d['lo'], True)} 〜 {_pct(d['hi'], True)} | {_pct(d['mde'])} |")
        out.append("")
    return "\n".join(out)


def write_outputs(out_dir: str, result: dict) -> None:
    records, days = result["records"], result["days"]
    os.makedirs(out_dir, exist_ok=True)
    cnt: dict = {}
    for r in records:
        key = (r["day"], str(r["side"]), str(int(r["entry"])), str(int(r["gate"])), str(r["brk"]), r["outcome"])
        cnt[key] = cnt.get(key, 0) + 1
    rows = sorted(list(k) + [str(n)] for k, n in cnt.items())
    with open(os.path.join(out_dir, "day_counts.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["day", "side", "entry", "gate", "brk", "outcome", "n"])
        w.writerows(rows)
    res = summarize(records, days)
    with open(os.path.join(out_dir, "tables.md"), "w", encoding="utf-8") as fh:
        fh.write(render_tables(res, records, days))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="D1b: 起点の後 40 分の結果を数える(戦略を回さない)")
    ap.add_argument("--files", nargs="+", required=True, help="足のファイル(年ごと)")
    ap.add_argument("--out", required=True, help="出力の置き場")
    ap.add_argument("--seal", default=SEAL, help="封印の境(SEAL より後は受けない)")
    a = ap.parse_args(argv)
    try:
        seal_t = _parse(a.seal)
    except ValueError as e:
        print(f"--seal を読めない: {e}", file=sys.stderr)
        return 2
    if seal_t.astimezone(timezone.utc) > _parse(SEAL).astimezone(timezone.utc):
        print(f"--seal が封印の境 {SEAL} より後: ファイルを開かずに止める", file=sys.stderr)
        return 2
    result = starts(read_bars(a.files, a.seal), base_params(), a.seal)
    write_outputs(a.out, result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
