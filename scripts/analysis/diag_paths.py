#!/usr/bin/env python3
"""分析のスキルの第 2 部 D4(取引の一生)と D5(合図そのものの情報)の表を、bitFlyer FX の 1 分足から出す読み口。

新しい走らせはしない。既にある取引の行(`trades.csv.gz`)と、封印の門の既定の呼び方(`common.load_bars`、
2023-12-18 より後は読まない)の 1 分足だけを読む。封印の窓の出力の置き場は読まない。

D4 取引の一生(取引ごと。値動きはすべて取引の向き side(+1 買い / −1 売り)を掛けた値動き率(bp)。基準の値段は取引の行の
  entry_price(マチルダは 1 段目の約定の値段。2 段以上建った取引の持ち高全体の平均の値段ではない)。損益の和は円):
  - MFE = 建ての時刻(entry_t)から出の時刻(exit_t)までに始まった 1 分足の、有利な側の端(買いは高値・売りは安値)の最大の値動き
  - MAE = 同じ足の不利な側の端(買いは安値・売りは高値)の最小の値動き
  - 頂点までの分 = MFE の足の始まり − 建て、保有の分 = 出 − 建て
  - 群: 「建ての値段から一度は有利に動いたのに負けた」「建ての値段から一度も有利に動かずに負けた」「勝った」の数・損益の和
  - 勝ち取引の 頂点までの分 ÷ 保有の分 の分位(0.25・0.5・0.75)
  - 出の後の値動き: 出の時刻の終値(出の時刻に終わる 1 分足の終値)から 5・15・60 分後の終値まで × side。1 取引あたり(日の塊の区間)
D5 合図そのものの情報(合図ごと。合図の時刻 signal_t の終値から h 分後の終値まで × 合図の向き):
  - h = 1・5・15・60 分。1 合図あたり(日の塊の区間)。起点は 2 つ: 合図の時刻(注文を出した時刻)と、建ての時刻(約定した足の終わり)。
    合図から建てまでに時間がある形では、合図の時刻からの値動きに建てる前の動きが混ざるので、建ての時刻からも並べる。
    例: カツオの K1 の形(入り方 a)は、合図が分かった時刻 T(海外の足の終わり)の次の区切り T + 足の長さで建てる(H3)。
    trades.csv.gz の signal_t は T、entry_t は T + 15 分で、entry_price は entry_t の bitFlyer の終値(D0 で確かめる)
  - 対照: 同じ合図を 24 時間後の同じ時刻に置いた値動き(結果を見る前に決めたずらし)
  - --blocked-from <走らせ> を渡すと、そちらにあってこちらに無い合図(門などで建てなかった合図)を別の群にする
決まり: 1 分の中の高値・安値の順は分からないので、MFE・MAE は足の端で数える(建ての足は含めない: entry_t は約定した足の終わり)。
区間は日の塊(循環、5 日・1,000 回・種 20261004)で日を選び直し、群の和 ÷ 群の数を作り直す(`diag_tables.group_ratio_ci`)。閾値で判定の言葉を出さない。

    PYTHONPATH=src python3 scripts/analysis/diag_paths.py --run <走らせ> [--blocked-from <門の無い走らせ>] --out <出力.md>
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "w4_measure"))
import diag_tables as dt  # noqa: E402

MIN = 60 * 10**9
DAY = 86_400 * 10**9
HORIZONS = (1, 5, 15, 60)
EXIT_HORIZONS = (5, 15, 60)


class Bars:
    """1 分足の配列(始まりの時刻の昇順)。"""

    def __init__(self, t: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray):
        self.t, self.h, self.l, self.c = t, h, l, c

    def close_at(self, ns: int) -> float | None:
        """時刻 ns に終わる足(始まり = ns − 1 分)の終値。無ければその前で一番近い足(5 分以内)。"""
        i = int(np.searchsorted(self.t, ns - MIN, side="right")) - 1
        if i < 0 or ns - MIN - self.t[i] > 5 * MIN:
            return None
        return float(self.c[i])

    def span(self, lo_ns: int, hi_ns: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """始まりが [lo, hi) の足の (始まり, 高値, 安値)。"""
        a, b = np.searchsorted(self.t, lo_ns, side="left"), np.searchsorted(self.t, hi_ns, side="left")
        return self.t[a:b], self.h[a:b], self.l[a:b]


def load_bitflyer_bars(lo_ns: int, hi_ns: int) -> Bars:
    from common import FX_DIR, load_bars, to_ns  # noqa: E402
    t, h, l, c = [], [], [], []
    y0 = datetime.fromtimestamp(lo_ns / 1e9, tz=timezone.utc).year
    y1 = datetime.fromtimestamp((hi_ns - 1) / 1e9, tz=timezone.utc).year
    for y in range(y0, y1 + 1):
        a = max(lo_ns, to_ns(datetime(y, 1, 1, tzinfo=timezone.utc)))
        b = min(hi_ns, to_ns(datetime(y + 1, 1, 1, tzinfo=timezone.utc)))
        if a >= b:
            continue
        bars, _, _ = load_bars(FX_DIR, "FX_BTC_JPY", a, b)
        for x in bars:
            t.append(int(x.start_time_ns)); h.append(float(x.high)); l.append(float(x.low)); c.append(float(x.close))
    o = np.argsort(np.array(t))
    return Bars(np.array(t)[o], np.array(h)[o], np.array(l)[o], np.array(c)[o])


def read_trades_csv(d: str) -> list[dict]:
    p = os.path.join(d, "trades.csv.gz")
    if not os.path.isfile(p):
        raise SystemExit(f"止める: {p} が無い(D4・D5 は取引の向きと合図の時刻の列が要る。走らせの記録から作り直す)")
    if dt.WINDOW_MARK in os.path.abspath(d).replace(os.sep, "/"):
        raise SystemExit(f"止める: {d} は封印の窓の出力の置き場")
    out = []
    with gzip.open(p, "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("in_measure", "True") == "False":
                continue
            t = {"entry_ns": dt._iso_ns(r["entry_t"]), "exit_ns": dt._iso_ns(r["exit_t"]), "side": int(float(r["side"])),
                 "pnl_jpy": float(r["pnl_jpy"]), "entry_px": float(r["entry_price"])}
            if r.get("signal_t"):
                t["signal_ns"] = dt._iso_ns(r["signal_t"])
            out.append(t)
    return out


def trade_life(tr: dict, bars: Bars) -> dict | None:
    """D4 の 1 取引。値は建ての値段に対する値動き率(bp)、取引の向きを掛ける。"""
    ts, hs, ls = bars.span(tr["entry_ns"], tr["exit_ns"])
    if len(ts) == 0:
        return None
    e, s = tr["entry_px"], tr["side"]
    fav = (hs / e - 1.0) * 1e4 if s > 0 else -(ls / e - 1.0) * 1e4
    adv = (ls / e - 1.0) * 1e4 if s > 0 else -(hs / e - 1.0) * 1e4
    i = int(np.argmax(fav))
    hold = (tr["exit_ns"] - tr["entry_ns"]) / MIN
    out = {"mfe": float(fav[i]), "mae": float(np.min(adv)), "t_mfe": (ts[i] - tr["entry_ns"]) / MIN, "hold": hold}
    pe = bars.close_at(tr["exit_ns"])
    for h in EXIT_HORIZONS:
        pf = bars.close_at(tr["exit_ns"] + h * MIN)
        out[f"after_{h}"] = None if pe is None or pf is None else s * (pf / pe - 1.0) * 1e4
    return out


def signal_move(sig_ns: int, side: int, bars: Bars, h: int) -> float | None:
    p0, p1 = bars.close_at(sig_ns), bars.close_at(sig_ns + h * MIN)
    if p0 is None or p1 is None:
        return None
    return side * (p1 / p0 - 1.0) * 1e4


def per_day_ratio(items: list[tuple[str, float]], days: list[str]) -> dict:
    sums, cnts = defaultdict(float), defaultdict(int)
    for d, v in items:
        sums[d] += v
        cnts[d] += 1
    return dt.group_ratio_ci(days, sums, cnts)


def d4(trades: list[dict], bars: Bars, days: list[str]) -> dict:
    rows = []
    for t in trades:
        r = trade_life(t, bars)
        if r is not None:
            rows.append((t, r))
    groups = {"勝った": [], "建ての値段から一度は有利に動いたのに負けた": [], "建ての値段から一度も有利に動かずに負けた": [], "損益 0": []}
    for t, r in rows:
        if t["pnl_jpy"] > 0:
            groups["勝った"].append((t, r))
        elif t["pnl_jpy"] < 0:
            groups["建ての値段から一度は有利に動いたのに負けた" if r["mfe"] > 0 else "建ての値段から一度も有利に動かずに負けた"].append((t, r))
        else:
            groups["損益 0"].append((t, r))
    gtab = {}
    for g, xs in groups.items():
        gtab[g] = {"trades": len(xs), "pnl_sum": float(sum(t["pnl_jpy"] for t, _ in xs)),
                   "mfe_median": float(np.median([r["mfe"] for _, r in xs])) if xs else None,
                   "mae_median": float(np.median([r["mae"] for _, r in xs])) if xs else None}
    win_share = [r["t_mfe"] / r["hold"] for t, r in groups["勝った"] if r["hold"] > 0]
    after = {}
    for h in EXIT_HORIZONS:
        items = [(dt.utc_day(t["exit_ns"]), r[f"after_{h}"]) for t, r in rows if r[f"after_{h}"] is not None]
        after[h] = per_day_ratio(items, days)
    return {"analysed": len(rows), "of": len(trades), "groups": gtab,
            "win_peak_share_q": [float(x) for x in np.quantile(win_share, [0.25, 0.5, 0.75])] if win_share else None,
            "after_exit": after}


def d5(signals: list[tuple[int, int]], bars: Bars, days: list[str]) -> dict:
    """signals = [(起点の時刻, 向き)]。"""
    out = {}
    for h in HORIZONS:
        real, ctrl = [], []
        for ns, side in signals:
            v = signal_move(ns, side, bars, h)
            if v is not None:
                real.append((dt.utc_day(ns), v))
            c = signal_move(ns + DAY, side, bars, h)
            if c is not None:
                ctrl.append((dt.utc_day(ns), c))
        out[h] = {"signal": per_day_ratio(real, days), "control_24h": per_day_ratio(ctrl, days)}
    return out


def render(res: dict) -> str:
    f, ci = dt._f, dt._ci
    L = [f"# 取引の一生と合図の情報: {res['name']}", "",
         "`scripts/analysis/diag_paths.py` が出した(手で書いていない)。値動きは取引(合図)の向きを掛けた値動き率(bp)、D4 の基準の値段は取引の行の entry_price。損益の和は円。bitFlyer FX の 1 分足。"
         "区間は 95%(日の塊 5 日・1,000 回)。1 分の中の高値・安値の順は分からない。", ""]
    r4 = res["d4"]
    L += ["## D4 取引の一生", "", f"- 調べた取引: {r4['analysed']} / {r4['of']}", "",
          "| 群 | 取引 | 損益の和(円) | MFE の中央値(値動き率 bp) | MAE の中央値(値動き率 bp) |", "|---|---|---|---|---|"]
    for g, x in r4["groups"].items():
        L.append(f"| {g} | {x['trades']} | {f(x['pnl_sum'],0)} | {f(x['mfe_median'])} | {f(x['mae_median'])} |")
    if r4["win_peak_share_q"]:
        q = r4["win_peak_share_q"]
        L += ["", f"- 勝ち取引の 頂点までの分 ÷ 保有の分 の分位(25・50・75%): {q[0]:.2f}・{q[1]:.2f}・{q[2]:.2f}"]
    L += ["", "出の後の値動き(取引の向きを掛けた値動き率 bp、1 取引あたり。正 = 出た後も取引の向きに動いた):", "",
          "| 出の後 | 取引 | 1 取引あたり [区間] |", "|---|---|---|"]
    for h, x in r4["after_exit"].items():
        L.append(f"| {h} 分 | {x['trades']} | {ci(x)} |")
    L += ["", "## D5 合図そのものの情報(合図の向きを掛けた値動き率 bp、1 合図あたり)", ""]
    for name, r5 in res["d5"].items():
        L += [f"### {name}", "", "| 合図の後 | 合図 | 起点から [区間] | 対照(24 時間後の同じ時刻)[区間] |", "|---|---|---|---|"]
        for h, x in r5.items():
            L.append(f"| {h} 分 | {x['signal']['trades']} | {ci(x['signal'])} | {ci(x['control_24h'])} |")
        L.append("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--blocked-from", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    run = dt.load_run(a.run)
    days = sorted(dt.daily_series(run))
    trades = read_trades_csv(a.run)
    lo = min(t["entry_ns"] for t in trades) - 2 * MIN
    hi = max(t["exit_ns"] for t in trades) + 2 * DAY
    from common import SEAL, to_ns  # noqa: E402
    hi = min(hi, to_ns(SEAL))
    bars = load_bitflyer_bars(lo, hi)
    res = {"name": run["name"], "d4": d4(trades, bars, days), "d5": {}}
    taken = [(t["signal_ns"], t["side"]) for t in trades if "signal_ns" in t]
    res["d5"]["建てた合図(起点 = 合図の時刻)"] = d5(taken, bars, days)
    res["d5"]["建てた合図(起点 = 建ての時刻)"] = d5([(t["entry_ns"], t["side"]) for t in trades], bars, days)
    if a.blocked_from:
        other = read_trades_csv(a.blocked_from)
        mine = {t.get("signal_ns") for t in trades}
        bl = [t for t in other if "signal_ns" in t and t["signal_ns"] not in mine]
        name = os.path.basename(os.path.normpath(a.blocked_from))
        res["d5"][f"建てなかった合図(起点 = 合図の時刻。{name} にあってこちらに無い)"] = d5([(t["signal_ns"], t["side"]) for t in bl], bars, days)
        res["d5"][f"建てなかった合図(起点 = {name} で建った時刻)"] = d5([(t["entry_ns"], t["side"]) for t in bl], bars, days)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(render(res) + "\n")
    with open(os.path.splitext(a.out)[0] + ".json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    print(f"-> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
