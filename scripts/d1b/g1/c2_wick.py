#!/usr/bin/env python3
"""# 2 カード 2(カツオ)の前提の直接の測り(D1B_FRAMINGS.md の # 2 の行)。

行の言葉と、それを担う関数:
  問い「海外の長いヒゲの足が閉じた後、海外と bitFlyer の値段はどれだけ・いつまでヒゲと逆へ動くか」
  「合図」                      wick_signals: カード 2 の物(C2OwnerXvenueWick、import)に海外の 1 分足の 4 本値を渡し、
                                カード自身のまとめ方と判定(classify_detail)で出た signal_log(足の終わり T・向き)を使う。
                                足の長さはカードの既定 15 分(原典 katsuo_v03.py の 15 分足。行に足の長さの変種は無い)
  「合図の出所 2(USD-M を主、現物を並べる)」  --source um / spot(Binance USD-M BTCUSDT / Binance 現物 BTCUSDT)
  「強い・弱い 2」              足の色と向きが同じ(陽線 × 買い・陰線 × 売り)= 強い、違う = 弱い(カードの説明の 4 通り。
                                走らせ直しの run_v2.py の signal_strong と同じ定義)。色はカードの _apply が判定に使った
                                classify_detail の色を、薄い継ぎ(_ColorLog)で記録する(持ち高の更新はカードのまま)
  「時間 4(1・5・15・60 分)」   HORIZONS_MIN
  「終点」                      move: 向き s(買い +1 / 売り −1)× (終値_{T+h} / 終値_T − 1)× 10,000。値は終わりがちょうど T・
                                T+h の 1 分足の終値(海外 = 合図の出所の系列、bitFlyer = 空でない足)。その足が無ければ NaN
                                (前の値で埋めない。# 9 とそろえる。リードの決め 2026-10-06 の 2)。終わりが T・T+h 以下の最後の足
                                (as-of)が古かった件数(= ちょうどの足が無かった件数)と NaN の件数を表に出す
  「経路の一番深い点」          deep: 終わりが (T, T+h] の 1 分足の高値・安値から、両方を出す(リードの決め 2026-10-06 の 2):
                                「ヒゲと逆の向き(取引の向き)の一番深い点」= 合図の向き s への一番深い点
                                「ヒゲの向き(取引に不利)の一番深い点」= s と逆の向きへの一番深い点(負の値)
                                (T・T+h のちょうどの足が無ければ NaN。経路に足が 1 本も無いときも NaN)
  「海外と bitFlyer」           同じ T・同じ h で、海外(合図の出所の系列)と bitFlyer FX_BTC_JPY を別々に
  「1 合図。年ごと・前半後半」  g1common.table(1 件あたり、日の塊の区間)
  対照「24 時間前と後の同じ時刻(合図の符号が経路で決まるので両方)」  同じ s を T ± 1,440 分の値動きに当てる。前と後を別に出す

使い方:
  件数だけ: PYTHONPATH=src python3 scripts/d1b/g1/c2_wick.py --source um --counts
  本走らせ: PYTHONPATH=src python3 scripts/d1b/g1/c2_wick.py --source um
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import g1common as G  # noqa: E402

OUT = os.path.join(G.ROOT, "docs", "RESEARCH", "d1b", "2_card2")
HORIZONS_MIN = (1, 5, 15, 60)
FOOT_MIN = 15  # カードの既定(c2_owner_xvenue_wick.FOOT_MIN。下で同じことを確かめる)
PERIODS = {"spot": "2017-08-17T15:00:00Z", "um": "2020-01-01T15:00:00Z"}  # run_v2.py の C2_VARIANTS の a・b の始め


class _Rows:
    """カードの view.ref(name) の代わり: (行の時刻, 値) を i 番目に返す列。"""

    def __init__(self, t: np.ndarray, v: np.ndarray) -> None:
        self.t, self.v = t, v

    def __len__(self) -> int:
        return len(self.t)

    def __getitem__(self, k: int):
        return (int(self.t[k]), float(self.v[k]))


class _View:
    def __init__(self, now_ns: int, rows: dict) -> None:
        self.now_ns = now_ns
        self._rows = rows

    def ref(self, name: str):
        return self._rows[name]


def _color_card(series: tuple):
    from bot.research.cards.library import c2_owner_xvenue_wick as M

    class _ColorLog(M.C2OwnerXvenueWick):
        """カードの物そのもの。_apply の前に、カードと同じ classify_detail で足の色を出し、signal_log に行が
        足されたときだけ色を記録する(持ち高・状態に触らない)。"""

        def __init__(self, **kw) -> None:
            super().__init__(**kw)
            self.signal_color: list = []

        def _apply(self, end_ns, o, h, lo, c) -> None:
            color = M.classify_detail(o, h, lo, c, small_gate_bp=self.small_gate_bp, big_gate_bp=self.big_gate_bp)[0]
            n0 = len(self.signal_log)
            super()._apply(end_ns, o, h, lo, c)
            if len(self.signal_log) != n0:
                self.signal_color.append(color)

    assert M.FOOT_MIN == FOOT_MIN
    return _ColorLog(series=series, foot_min=FOOT_MIN)


def wick_signals(ov: dict, series: tuple, chunks: list) -> dict:
    """海外の 1 分足(ov: t = 行の時刻、open/high/low/close)をカードに区切りごとに渡し、signal_log と色を返す。
    chunks = [(a, b), ...]: 行の時刻が [a, b) の行を渡し、now = b で呼ぶ(b は足の区切りにそろえる)。"""
    card = _color_card(series)
    names = dict(zip(("open", "high", "low", "close"), series))
    for a, b in chunks:
        i, j = np.searchsorted(ov["t"], [a, b], side="left")
        rows = {names[c]: _Rows(ov["t"][i:j], ov[c][i:j]) for c in names}
        card._next_row = 0
        card.exposure(_View(b + 60 * G.NS, rows))  # 行の時刻 < b の行は終わりが b 以下 → b で閉じた足まで判定される
    log = np.array(card.signal_log, dtype=np.int64).reshape(-1, 4)
    color = np.array(card.signal_color, dtype=np.int64)
    return {"T": log[:, 0], "s": log[:, 1], "strong": color == log[:, 1], "small": log[:, 2].astype(bool),
            "big": log[:, 3].astype(bool)}


FAV = "ヒゲと逆の向き(取引の向き)の一番深い点"
ADV = "ヒゲの向き(取引に不利)の一番深い点"
QTY = ("終点", FAV, ADV)


def moves(T: np.ndarray, s: np.ndarray, end: np.ndarray, close: np.ndarray, high: np.ndarray, low: np.ndarray,
          h_min: int, hi: int) -> dict:
    """終点・2 つの一番深い点(bp、向き s に正)と、件数の印。T・T + h のちょうどの足が無いか、T + h が hi を越えれば NaN。
    "_stale" = as-of の足が古かった(T か T + h のちょうどの足が無く、それより前の足はあった)件、"_late" = T + h > hi の件。"""
    h = h_min * G.MIN_NS
    i0, ih = G.exact_idx(end, T), G.exact_idx(end, T + h)
    a0, ah = G.asof_idx(end, T), G.asof_idx(end, T + h)
    p0 = G.take(close, i0)
    ph = G.take(close, ih)
    mx, mn, n = G.path_extremes(end, high, low, T, T + h)
    s = s.astype(float)
    fav = np.where(s > 0, mx / p0 - 1.0, 1.0 - mn / p0) * G.BP
    adv = np.where(s > 0, mn / p0 - 1.0, 1.0 - mx / p0) * G.BP
    late = T + h > hi
    out = {"終点": s * (ph / p0 - 1.0) * G.BP, FAV: fav, ADV: adv}
    bad = late | ~np.isfinite(p0) | ~np.isfinite(ph)
    for k in out:
        out[k] = np.where(bad, np.nan, out[k])
    out["_stale"] = ~late & (((i0 < 0) & (a0 >= 0)) | ((ih < 0) & (ah >= 0)))
    out["_late"] = late
    return out


def chunks_of(lo: int, hi: int) -> list:
    edges = [lo]
    y = int(G.ns_iso(lo)[:4]) + 1
    while G.iso_ns(f"{y}-01-01T00:00:00Z") < hi:
        edges.append(G.iso_ns(f"{y}-01-01T00:00:00Z"))
        y += 1
    edges.append(hi)
    return list(zip(edges[:-1], edges[1:]))


def main() -> int:
    from bot.research.cards.library import c2_owner_xvenue_wick as M
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, choices=["um", "spot"])
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=G.HI_MAX_ISO)
    ap.add_argument("--counts", action="store_true")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    lo, hi = G.iso_ns(a.start or PERIODS[a.source]), G.iso_ns(a.end)
    G.check_hi(hi)
    if lo % (FOOT_MIN * G.MIN_NS) or hi % (FOOT_MIN * G.MIN_NS):
        raise SystemExit("始めと終わりは 15 分の区切りにそろえる")
    series = M.SERIES_UM if a.source == "um" else M.SERIES_SPOT
    t0 = time.time()
    # 合図: 期間の中の行だけをカードに渡す。対照・h のために海外の値は前後 1 日を足して読む
    rd_lo = lo - G.DAY_NS
    if a.source == "um":
        rd_lo = max(rd_lo, G.iso_ns("2020-01-01T00:00:00Z"))
    ov = G.binance_ohlc(rd_lo, hi, a.source)
    t_read = time.time() - t0
    sg = wick_signals(ov, series, chunks_of(lo, hi))
    keep = (sg["T"] > lo) & (sg["T"] <= hi)
    sg = {k: v[keep] for k, v in sg.items()}
    all_days = G.all_days_between(lo, hi)
    days = G.jst_day(sg["T"] - 1)  # 足の終わり T の日本時間の日(T ちょうどが日の境のときは前の日の足)
    groups = {"強い": sg["strong"], "弱い": ~sg["strong"]}
    os.makedirs(a.out, exist_ok=True)
    head = [f"- 台本: `scripts/d1b/g1/c2_wick.py --source {a.source}`(数は台本が出した。手で書いていない)",
            f"- 合図の出所: {a.source}({'Binance USD-M BTCUSDT' if a.source == 'um' else 'Binance 現物 BTCUSDT'})、"
            f"足 {FOOT_MIN} 分(カードの既定)、期間 {G.ns_iso(lo)} 〜 {G.ns_iso(hi)}(日本時間の暦日 {len(all_days)} 日)",
            f"- 読み込み {t_read:.0f} 秒・合図 {time.time() - t0 - t_read:.0f} 秒", ""]
    if a.counts:
        L = [f"# # 2 カード 2 — 件数の数え上げ({a.source})", ""] + head
        cj = {}
        for g, m in groups.items():
            cj[g] = G.count_table(days[m], all_days)
            L += G.md_counts(f"合図({g})", cj[g], "合図の数")
        cj["全部"] = G.count_table(days, all_days)
        L += G.md_counts("全部の合図", cj["全部"], "合図の数")
        with open(os.path.join(a.out, f"COUNTS_{a.source}.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(L))
        G.write_json(cj, os.path.join(a.out, f"counts_{a.source}.json"))
        print("\n".join(L))
        return 0
    bf = G.bars_np("backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906", "FX_BTC_JPY", lo - G.DAY_NS, hi)
    ov_end = ov["t"] + G.MIN_NS
    res = {"source": a.source, "period": [G.ns_iso(lo), G.ns_iso(hi)], "n_signals": int(len(sg["T"])),
           "inputs": {"overseas": ov["manifest"], "bitflyer_files": bf["files"]}, "表": {}}
    L = [f"# # 2 カード 2 — ヒゲの後の値動き({a.source})", ""] + head
    L += ["値は bp、合図の向き(ヒゲと逆 = 取引の向き)に正。1 件 = 1 合図。区間は日の塊(5 日・1,000 回・種 20261006)。", ""]
    for g, m in groups.items():
        for lab, sh in (("実", 0), ("24 時間前", -G.DAY_NS), ("24 時間後", G.DAY_NS)):
            T = sg["T"][m] + sh
            s = sg["s"][m]
            for venue, (end, c, hh, ll) in (("海外", (ov_end, ov["close"], ov["high"], ov["low"])),
                                             ("bitFlyer", (bf["end"], bf["close"], bf["high"], bf["low"]))):
                for hm in HORIZONS_MIN:
                    mv = moves(T, s, end, c, hh, ll, hm, hi)
                    marks = {"as-of が古かった件数(ちょうどの足が無い)": int(mv["_stale"].sum()),
                             "終わりを越えた件数": int(mv["_late"].sum())}
                    for q in QTY:
                        v = mv[q]
                        key = f"{g}|{lab}|{venue}|{hm}分|{q}"
                        res["表"][key] = G.table(v, days[m], all_days, per="event")
                        res["表"][key]["分位"] = G.quantiles(v)
                        res["表"][key].update(marks)
    for g in groups:
        for lab in ("実", "24 時間前", "24 時間後"):
            L += [f"## 合図({g})— {lab}", ""] + G.MD_STAT_HEAD
            marks = []
            for venue in ("海外", "bitFlyer"):
                for hm in HORIZONS_MIN:
                    for q in QTY:
                        t = res["表"][f"{g}|{lab}|{venue}|{hm}分|{q}"]
                        L += [r for r in G.md_stat_rows(f"{venue} {hm}分 {q}", t) if "(記述)" not in r]
                    t = res["表"][f"{g}|{lab}|{venue}|{hm}分|終点"]
                    marks.append(f"| {venue} | {hm}分 | {t['n_nan']} | {t['as-of が古かった件数(ちょうどの足が無い)']} | "
                                 f"{t['終わりを越えた件数']} |")
            L += ["", "NaN の件数(終点。一番深い点は経路に足が無い件も NaN):", "",
                  "| 値段 | 時間 | NaN の件数 | うち as-of が古かった件数(T か T+h のちょうどの足が無い) | うち終わりを越えた件数 |",
                  "|---|---|---|---|---|"] + marks
            L.append("")
    L += ["年ごとの表(記述)は result_<出所>.json の各表の「年ごと(記述)」。", ""]
    res["所要_秒"] = round(time.time() - t0, 1)
    G.write_json(res, os.path.join(a.out, f"result_{a.source}.json"))
    with open(os.path.join(a.out, f"RESULT_{a.source}.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print(f"書いた: {a.out} 所要 {res['所要_秒']} 秒")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
