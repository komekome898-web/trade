"""K-135 の確かめ: バリアレースの規則(カード 7)を、K-135 を見つけるのに使っていない 1 分足に当てて、w の帯ごとの反転の割合を数える。

## K-135 の予言(docs/RESEARCH/FINDINGS_LEDGER.md の ### K-135 の「予言」の欄の逐語。データを見る前にコミット 36e3e615 で押し出した)

①-a Binance BTCUSDT 現物の 1 分足で同じ規則のレース(窓 1 日・1 週、帯の境はそのデータの w の 3 分位)を数えると、下の帯の反転の割合の
区間が 0.5 より下(外れ = 区間が 0.5 を含むか上。② を分ける: ② なら bitFlyer より弱まる。③④ は同じ値動きなので分けない)→ 未
①-b USDJPY の 1 分足で同じく、下の帯の反転の割合の区間が 0.5 より下(外れ = 区間が 0.5 を含むか上。④ 偶然と ① の一般性を分ける。
BTC だけの仕組みなら外れても ① の BTC 版は残る)→ 未
①-c ①-a・①-b のそれぞれで、反転の割合の下の帯の区間が上の帯の区間より下にあり重ならない(外れ = 重なる。量に比例)→ 未
②-a ①-a と同じ Binance のレースを、終値ではなく 1 分の高値・安値で当たりを決めて数え直しても、下の帯の区間が 0.5 より下に残る
(外れ = 区間が 0.5 を含む。② が正しければ消える)→ 未

## オーナーの逐語(L-709「**2件目　y**」= 次の測り方で進めてよいかへの yes)

「問いの立て方: 戦略の損益ではなく、続いたか・戻ったかの割合で測る / 何を何通り試すか: 1 日と 1 週の 2 つの幅 × 2 つのデータ
(Binance のビットコインの 1 分足・ドル円の 1 分足)× 静か・中・荒いの 3 つ + Binance で終値判定と高値・安値判定を比べる 1 つ /
何を 1 件と数えるか: 線を引いてどちらかに届くまでの 1 回」

## データ(封印の門 bot.bt.data.loader.load だけを通して読む。kind bar、gap は accept、no_trade は drop)

- binance_btcusdt: backtest_data/binance_BTCUSDT_1m_20170801_20231231 の年ごとのファイル。期間 2017-08-17T15:00Z〜2023-12-17T15:00Z
  (始め = 置き場の最初の行 2017-08-17 04:00 UTC の後の最初の日本時間の 0 時、終わり = 日本時間の 2023-12-18 0 時。
  2023-12-18 以後は読まない: src/bot/research/trade_record.py の SEAL_START_NS)。2024 年以後の置き場は使わない(拒む)。
- usdjpy: backtest_data/fx_usdjpy_1m_20170801_20221231/usdjpy_1m.csv.gz。期間 2017-08-01T15:00Z〜2022-12-31T15:00Z
  (始め = 最初の行 2017-08-01 00:00 UTC の後の最初の日本時間の 0 時、終わり = 最後の行 2022-12-30 23:59 UTC を含む日本時間の日の終わり)。
- bitflyer_fx: 再現の試験だけに使う。backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906、2015-11-28T15:00Z〜2023-12-17T15:00Z
  (カード 7 の測定と同じ。docs/RESEARCH/cards/c7_barrier_race/measure/README.md)。
- 期間の端の決め方の出所: docs/RESEARCH/cards/c7_barrier_race/CARD.md「測る期間」(端は日本時間の日の境、開始 = 置き場の最初の行の後の
  最初の日本時間の 0 時)。

## 規則の出所(変えていない)

- src/bot/research/cards/library/c7_barrier_race.py(カードの決まり)、src/bot/research/cards/run.py 80〜81・120〜122 行
  (カードが呼ばれるのは volume > 0 の足だけ = decided)。
- docs/RESEARCH/cards/c7_barrier_race/redo2_2026-10-05/race_replay.py(レースの当たりの復元: replay・反転と継続の数え方・前半後半・
  w の 3 分位の帯・Wilson の区間)と race_block_ci.py(日の塊の区間 = scripts/analysis/diag_tables.group_ratio_ci: 循環 5 日・
  1,000 回・種 20261004、群の和 ÷ 群の数)。
- 要点: x = ln(終値)。呼ばれた足どうしの r² を足の終わり t で窓 (t − 窓, t] に足す。w = √Σr²。最初に呼ばれた足の終わり + 窓 まで温まり。
  起点が無ければ w > 0 の足でレースを始める(起点 = その足の x)。次の足から x − 起点 ≥ w で上の当たり、≤ −w で下の当たり。
  当たった足で次のレースを始める(起点 = その足の x、w は決め直す。w = 0 なら次の足で始め直す)。最初の当たりは数えない。
  前の当たりと逆の側 = 反転、同じ側 = 継続。帯 = 数えたレースの始めの w の 3 分位(np.quantile、線形)で [0, q1)・[q1, q2)・[q2, ∞)。
  日 = 当たりの足の終わりの日本時間の日。日の並び = 決定(volume > 0)の足のうち最後の 2 本を除いた足のある日本時間の日(測定の
  daily.csv と同じ作り方。day_list の docstring)。前半・後半の境 = 並びの len // 2 番目の日。
- 高値・安値の判定(--judge highlow): 当たりの判定だけを、x の代わりに ln(高値) − 起点 ≥ w(上)・ln(安値) − 起点 ≤ −w(下)にする
  (CARD.md 迷った点 4 の別の形 (a))。同じ足で両方に届いたら「決まらない」(順序が分からない)。w(終値どうしの r²)と
  起点(当たった足の終値)は変えない。決まらない当たりは数えず、その次の当たりも前の当たりの側が分からないので数えない(数は表に出す)。
  帯の境は数えた(決まった)レースの w の 3 分位。

## 結果を見てから足した記述(批評家の指摘による。本番の読みは登録どおりの同じ規則の表)

- 窓 1d の「週末明けに始まったレース / それ以外」: レースの始まり = 起点を置いた足(直前の当たりの足、または w = 0 の後に始め直した
  足)の終わりの時刻 s。**週末明け = s が UTC の日曜 20:00 以上、または UTC の月曜 22:00 未満(月曜 0:00〜22:00)**(WEEKEND_* の定数)。
  あわせて、始まりの足の 1 日の窓 (s − 1 日, s] の決定の足の数が 800 本未満のレースの割合。
- off_grid の区間にかかるレース(Binance): 始まりの足の終わり ≤ off_grid の最後の行の始まり + 60 秒 かつ 当たりの足の終わり ≥ off_grid の
  最初の行の始まり、の数を帯ごとに。
- 高値・安値の判定のレースを、同じ窓の終値の判定の帯の境で数え直した帯ごとの数(全期間)。
- gap の内訳: 期間の分の数 − 門が出した足 = 欠けた分。gap = 欠けた分 + off_grid になるかを出す。

## 出力

docs/RESEARCH/why_predict/K-135_2026-10-05/ の <data>.md(表)と races_<data>_<judge>_<窓>.csv.gz(当たりごとの行)。
判定(当たった・外れた)と読みは書かない(リードが書く)。1h の窓は予言の外(記述)。

    PYTHONPATH=src python3 scripts/why_predict/k135_race_confirm.py --data binance_btcusdt --windows 1h,1d,1w --judge close,highlow --off-grid accept
    PYTHONPATH=src python3 scripts/why_predict/k135_race_confirm.py --data usdjpy --windows 1h,1d,1w --judge close
"""
from __future__ import annotations

import argparse
import csv
import gzip
import math
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "analysis"))
sys.path.insert(0, os.path.join(ROOT, "src"))
import diag_tables as dt  # noqa: E402

NS = 10**9
WIN = {"1h": 3600 * NS, "1d": 86400 * NS, "1w": 7 * 86400 * NS}
OUT_DIR = os.path.join(ROOT, "docs", "RESEARCH", "why_predict", "K-135_2026-10-05")
SEAL_START_NS = int(datetime(2023, 12, 18, tzinfo=timezone.utc).timestamp()) * NS  # = trade_record.SEAL_START_NS
FORBIDDEN_DIRS = ("binance_BTCUSDT_1m_20240101_20260831", "phase2_sealed", "WINDOW1")
IN_PREDICTION = {"1h": False, "1d": True, "1w": True}
WEEKEND_FROM = (6, 20 * 3600)  # UTC の日曜(月曜 = 0)20:00 から
WEEKEND_TO = (0, 22 * 3600)  # UTC の月曜 22:00 まで(含まない)
WEEKEND_DEF = "UTC の日曜 20:00 ≤ 始まり、または 始まり < UTC の月曜 22:00(月曜 0:00 から)"
NWIN_LT = 800

DATA = {
    "bitflyer_fx": {
        "label": "bitFlyer FX_BTC_JPY 1 分足(再現の試験だけ)",
        "dir": "backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906", "pattern": "candles_1m_{y}.csv.gz",
        "time_col": "ts", "symbol": "FX_BTC_JPY", "asset": "crypto", "session": "24x7",
        "lo": "2015-11-28T15:00:00Z", "hi": "2023-12-17T15:00:00Z"},
    "binance_btcusdt": {
        "label": "Binance BTCUSDT 現物 1 分足",
        "dir": "backtest_data/binance_BTCUSDT_1m_20170801_20231231", "pattern": "binance_BTCUSDT_1m_{y}.csv.gz",
        "time_col": "open_time", "symbol": "BTCUSDT", "asset": "crypto", "session": "24x7",
        "lo": "2017-08-17T15:00:00Z", "hi": "2023-12-17T15:00:00Z"},
    "usdjpy": {
        "label": "USDJPY 1 分足(Dukascopy BID)",
        "dir": "backtest_data/fx_usdjpy_1m_20170801_20221231", "pattern": "usdjpy_1m.csv.gz",
        "time_col": "timestamp", "symbol": "USDJPY", "asset": "fx", "session": "24x5",
        "lo": "2017-08-01T15:00:00Z", "hi": "2022-12-31T15:00:00Z"},
}


def iso_ns(s: str) -> int:
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return int(d.timestamp()) * NS


def ns_iso(t: int) -> str:
    return datetime.fromtimestamp(t / 1e9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def jst_day(t: int) -> str:
    """race_replay.jst_day と同じ。"""
    return (date(1970, 1, 1) + timedelta(days=int((t // NS + 9 * 3600) // 86400))).isoformat()


def jst_day_num(t: np.ndarray) -> np.ndarray:
    return (t // NS + 9 * 3600) // 86400


def day_str(n: int) -> str:
    return (date(1970, 1, 1) + timedelta(days=int(n))).isoformat()


def wilson(k, n):
    """race_replay.wilson と同じ。"""
    if n == 0:
        return (None, None)
    z = 1.959964
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


# ---------------------------------------------------------------- データ(封印の門だけ)

def _paths(cfg: dict, lo: int, hi: int) -> list[str]:
    if "{y}" not in cfg["pattern"]:
        return [f"{cfg['dir']}/{cfg['pattern']}"]
    y0 = datetime.fromtimestamp(lo / 1e9, tz=timezone.utc).year
    y1 = datetime.fromtimestamp((hi - 1) / 1e9, tz=timezone.utc).year
    out = []
    for y in range(y0, y1 + 1):
        p = f"{cfg['dir']}/{cfg['pattern'].format(y=y)}"
        if os.path.exists(os.path.join(ROOT, p)):
            out.append(p)
    return out


def _dataset(cfg: dict, paths: list[str], lo: int, hi: int) -> dict:
    return {"name": "bars", "paths": paths, "range_ns": [lo, hi],
            "spec": {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip", "kind": "bar",
                     "symbol": cfg["symbol"], "asset": cfg["asset"],
                     "time": {"columns": [cfg["time_col"]], "unit": "iso", "tz": "UTC"},
                     "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
                     "bar": {"interval_s": 60, "label": "start", "session": cfg["session"]}, "key": "start",
                     "no_trade": {"fields": ["open", "high", "low", "close"]}}}


def load_series(data: str, lo: int | None = None, hi: int | None = None, log=print, off_grid: str | None = None) -> dict:
    """門(bot.bt.data.loader.load)から読み、決定の足(volume > 0。run.py の _nonempty)の end_ns・close・high・low の配列を返す。
    ファイルごと(年ごと)に読んで配列にし、物は捨てる(記憶を抑える)。
    off_grid(分の格子に乗らない足。カード 7 の bitFlyer には無かったので規則の出所に決まりが無い)は、呼び手が accept / drop を
    名前で渡したときだけ通す(既定 None = 出たら止める)。accept は足の時刻を切り下げずにそのまま使う。"""
    from bot.bt.data.loader import load
    cfg = DATA[data]
    lo = iso_ns(cfg["lo"]) if lo is None else lo
    hi = iso_ns(cfg["hi"]) if hi is None else hi
    if hi > SEAL_START_NS:
        raise SystemExit(f"拒否: 終わり {ns_iso(hi)} は封印の境 2023-12-18T00:00Z より後")
    if any(f in cfg["dir"] for f in FORBIDDEN_DIRS):
        raise SystemExit(f"拒否: 使わない置き場 {cfg['dir']}")
    parts = {k: [] for k in ("end", "close", "high", "low", "vol")}
    info = {"data": data, "label": cfg["label"], "lo": ns_iso(lo), "hi": ns_iso(hi), "files": [], "bars": 0, "off_grid_policy": off_grid,
            "anomalies": {}, "hashes": {}}
    for p in _paths(cfg, lo, hi):
        t0 = time.time()
        res = load(ROOT, [_dataset(cfg, [p], lo, hi)])
        for a in res.anomalies("bars"):
            info["anomalies"][a["kind"]] = info["anomalies"].get(a["kind"], 0) + 1
        kinds = {a["kind"] for a in res.anomalies("bars")}
        resolve = {"gap": "accept", "no_trade": "drop"}
        if off_grid is not None:
            resolve["off_grid"] = off_grid
        for a in res.anomalies("bars"):
            if a["kind"] == "off_grid":
                og = info.setdefault("off_grid", {}).setdefault(p, {"n": 0, "first": None, "last": None, "seconds": {}})
                og["n"] += 1
                ts = ns_iso(int(a["t_ns"]))
                og["first"] = og["first"] or ts
                og["last"] = ts
                sec = str((int(a["t_ns"]) // NS) % 60)
                og["seconds"][sec] = og["seconds"].get(sec, 0) + 1
        unknown = kinds - set(resolve)
        if unknown:
            raise SystemExit(f"門が知らない異常の種類 {sorted(unknown)}(決まりが無いので止める)")
        bars = res.events("bars", resolve)
        n = len(bars)
        parts["end"].append(np.fromiter((int(b.exchange_time_ns) for b in bars), dtype=np.int64, count=n))
        parts["close"].append(np.fromiter((float(b.close) for b in bars), dtype=np.float64, count=n))
        parts["high"].append(np.fromiter((float(b.high) for b in bars), dtype=np.float64, count=n))
        parts["low"].append(np.fromiter((float(b.low) for b in bars), dtype=np.float64, count=n))
        parts["vol"].append(np.fromiter((float(b.volume) for b in bars), dtype=np.float64, count=n))
        info["hashes"].update(res.hashes())
        info["files"].append(p)
        info["bars"] += n
        del bars, res
        log(f"  読んだ {p}: 足 {n:,}({time.time() - t0:.0f} 秒)")
    end = np.concatenate(parts["end"])
    close = np.concatenate(parts["close"])
    high = np.concatenate(parts["high"])
    low = np.concatenate(parts["low"])
    vol = np.concatenate(parts["vol"])
    if not (np.diff(end) > 0).all():
        raise SystemExit("足の終わりが増えていない(つなぎの誤り)")
    nonempty = vol > 0
    # volume 0 の足のうち、終値が直前の足の終値と違うもの(記述。カードは volume 0 の足では呼ばれない)
    chg = np.zeros(len(close), dtype=bool)
    chg[1:] = close[1:] != close[:-1]
    info["vol0"] = int((~nonempty).sum())
    info["vol0_close_changed"] = int((~nonempty & chg).sum())
    d = np.flatnonzero(nonempty)
    info["decided"] = int(len(d))
    # 期間の分の数(ファイルごとの [max(lo, 年の始め), min(hi, 次の年の始め)))。gap の内訳に使う
    mins = 0
    for p in info["files"]:
        if "{y}" in cfg["pattern"]:
            y = int(p.rsplit("_", 1)[-1].split(".")[0])
            a0 = max(lo, int(datetime(y, 1, 1, tzinfo=timezone.utc).timestamp()) * NS)
            b0 = min(hi, int(datetime(y + 1, 1, 1, tzinfo=timezone.utc).timestamp()) * NS)
        else:
            a0, b0 = lo, hi
        mins += (b0 - a0) // (60 * NS)
    info["range_minutes"] = int(mins)
    # 門が読んだ封印の記録のうち、読んだファイルに当たるもの(bot.bt.data.allowlist.SealRegistry: 門と同じ読み)
    from bot.bt.data.allowlist import SealRegistry
    reg = SealRegistry(ROOT)
    info["seals"] = []
    for p in info["files"]:
        real = os.path.realpath(os.path.join(ROOT, p))
        es = [e for e in reg.entries if e.real == real]
        info["seals"].append((p, [(e.unit, e.time_column, ns_iso(int(e.cutoff_ns))) for e in es]))
    info["seal_records_n"] = len(reg.records_read)
    return {"end_ns": end[d], "close": close[d], "high": high[d], "low": low[d], "info": info}


# ---------------------------------------------------------------- レース(race_replay.replay の写し + 高値・安値)

def replay(t: np.ndarray, x: np.ndarray, W: int, xh: np.ndarray | None = None, xl: np.ndarray | None = None) -> list:
    """当たりの並び [(足の番号 k, 側 +1 上 / −1 下 / 0 決まらない, 始めの w, 次の w, レースの始まりの足の番号)]。
    t・x は決定の足の終わりと ln(終値)。xh・xl を渡すと、当たりの判定だけを ln(高値)・ln(安値)でする(同じ足で両方 → 0)。"""
    hl = xh is not None
    r2 = np.zeros(len(x))
    r2[1:] = np.diff(x) ** 2
    C = np.cumsum(r2)
    lo = np.searchsorted(t, t - W, side="right")  # 窓の中 = t_j > t_k − W

    def width(k):
        s = C[k] - (C[lo[k] - 1] if lo[k] > 0 else 0.0)
        return math.sqrt(max(s, 0.0))
    first_end = t[0]
    k = int(np.searchsorted(t, first_end + W, side="left"))  # first_end ≤ t − W となる最初の足
    hits = []
    anchor = None
    wcur = None
    kstart = None
    n = len(x)
    while k < n:
        if anchor is None:
            w = width(k)
            if w > 0:
                anchor, wcur, kstart = x[k], w, k
            k += 1
            continue
        step = 4096
        found = None
        j = k
        while j < n:
            if hl:
                up = (xh[j:j + step] - anchor) >= wcur
                dn = (xl[j:j + step] - anchor) <= -wcur
            else:
                seg = x[j:j + step] - anchor
                up = seg >= wcur
                dn = seg <= -wcur
            hit = up | dn
            if hit.any():
                i = int(np.argmax(hit))
                found = (j + i, 0 if (up[i] and dn[i]) else (1 if up[i] else -1))
                break
            j += step
        if found is None:
            break
        kk, side = found
        w_new = width(kk)
        hits.append((kk, side, wcur, w_new, kstart))
        if w_new > 0:
            anchor, wcur, kstart = x[kk], w_new, kk
        else:
            anchor, wcur = None, None
        k = kk + 1
    return hits


def classify(hits: list) -> list:
    """当たりごとの種類: first / reversal / continuation / undecided_both(同じ足で両方)/ undecided_prev(前の側が分からない)。"""
    out = []
    prev = None
    for h in hits:
        side = h[1]
        if prev is None:
            kind = "first"
        elif side == 0:
            kind = "undecided_both"
        elif prev == 0:
            kind = "undecided_prev"
        else:
            kind = "reversal" if side != prev else "continuation"
        out.append(kind)
        prev = side
    return out


def day_list(end_ns: np.ndarray) -> list[str]:
    """日の並び = カード 7 の測定の daily.csv の日と同じ作り方: 決定の足のうち最後の 2 本を除いた足(src/bot/research/cards/pnl.py の
    m = len(dec) − 2: 次の次の足の始値がある決定だけが P_t を持つ)の終わりの日本時間の日(scripts/w4_measure/light_b2.py の
    daily_rows(p, "Asia/Tokyo"))。race_replay.py・race_block_ci.py はこの daily.csv の日で前半・後半を切っている。"""
    return [day_str(v) for v in np.unique(jst_day_num(end_ns[:-2]))]


def tables(t: np.ndarray, hits: list, days: list[str], edges: tuple | None = None) -> dict:
    """帯 × 期間の数。帯の境 = 数えたレース(反転・継続)の始めの w の 3 分位(edges を渡すとその境)。"""
    kinds = classify(hits)
    recs = []  # (日, 反転 0/1 または None, w0, kind)
    for h, kind in zip(hits, kinds):
        k, w0 = h[0], h[2]
        if kind == "first":
            continue
        recs.append((jst_day(int(t[k])), (1.0 if kind == "reversal" else 0.0) if kind in ("reversal", "continuation") else None, w0, kind))
    counted = [r for r in recs if r[1] is not None]
    ws = np.array([r[2] for r in counted])
    if edges is not None:
        q1, q2 = edges
    else:
        q1, q2 = (np.quantile(ws, [1 / 3, 2 / 3]) if len(ws) else (float("nan"), float("nan")))
    half = len(days) // 2
    parts = {"全期間": days, "前半": days[:half], "後半": days[half:]}
    bands = [("全部", 0.0, 1e9), ("下", 0.0, q1), ("中", q1, q2), ("上", q2, 1e9)]
    rows = []
    edge = days[half]
    # 当たりの選び方は race_replay.py と同じ(全期間 = 全部、前半 = 日 < 境、後半 = 日 ≥ 境)。日の塊の区間は race_block_ci.py と同じく
    # 期間の日の並びの中の日だけを使う(group_ratio_ci が並びの外の日を見ない)。
    pred = {"全期間": lambda d: True, "前半": lambda d: d < edge, "後半": lambda d: d >= edge}
    for bn, lo_, hi_ in bands:
        for pn, pd in parts.items():
            sel = [r for r in recs if lo_ <= r[2] < hi_ and pred[pn](r[0])]
            cnt = [r for r in sel if r[1] is not None]
            kk = int(sum(r[1] for r in cnt))
            a, b = wilson(kk, len(cnt))
            su, cn = {}, {}
            for d, x, _, _ in cnt:
                su[d] = su.get(d, 0.0) + x
                cn[d] = cn.get(d, 0) + 1
            q = dt.group_ratio_ci(pd, su, cn)
            rows.append({"band": bn, "part": pn, "n": len(cnt), "rev": kk,
                         "rate": (kk / len(cnt)) if cnt else None, "wilson": (a, b), "block": (q["lo"], q["hi"]),
                         "und_both": sum(1 for r in sel if r[3] == "undecided_both"),
                         "und_prev": sum(1 for r in sel if r[3] == "undecided_prev")})
    n_first = kinds.count("first")
    dset = set(days)
    n_outside = sum(1 for r in counted if r[0] not in dset)
    return {"q1": float(q1), "q2": float(q2), "rows": rows, "hits": len(hits), "first": n_first,
            "first_day": jst_day(int(t[hits[0][0]])) if hits else None,
            "n_rev": kinds.count("reversal"), "n_cont": kinds.count("continuation"),
            "n_und_both": kinds.count("undecided_both"), "n_und_prev": kinds.count("undecided_prev"),
            "n_outside_days": n_outside, "edge": edge, "days": len(days), "first_d": days[0] if days else None,
            "last_d": days[-1] if days else None}


def _row(sel: list, days: list[str]) -> dict:
    """sel = [(日, 反転 0/1)]。数・反転・割合・二項・日の塊(全期間の日の並び)。"""
    kk = int(sum(x for _, x in sel))
    a, b = wilson(kk, len(sel))
    su, cn = {}, {}
    for d, x in sel:
        su[d] = su.get(d, 0.0) + x
        cn[d] = cn.get(d, 0) + 1
    q = dt.group_ratio_ci(days, su, cn)
    return {"n": len(sel), "rev": kk, "rate": (kk / len(sel)) if sel else None, "wilson": (a, b), "block": (q["lo"], q["hi"])}


def is_weekend_start(s_ns: int) -> bool:
    """週末明けに始まったか(WEEKEND_DEF)。1970-01-01 は木曜(月曜 = 0 で 3)。"""
    sec = s_ns // NS
    wd = (sec // 86400 + 3) % 7
    sod = sec % 86400
    return (wd == WEEKEND_FROM[0] and sod >= WEEKEND_FROM[1]) or (wd == WEEKEND_TO[0] and sod < WEEKEND_TO[1])


def _counted(t: np.ndarray, hits: list) -> list:
    """数えたレース: (当たりの足の番号, 始まりの足の番号, 始めの w, 日, 反転 0/1)。"""
    out = []
    for h, kind in zip(hits, classify(hits)):
        if kind in ("reversal", "continuation"):
            out.append((h[0], h[4], h[2], jst_day(int(t[h[0]])), 1.0 if kind == "reversal" else 0.0))
    return out


def weekend_split(t: np.ndarray, hits: list, days: list[str], tb: dict, W: int) -> list:
    """帯 × (週末明け / それ以外 / 帯全体) × 全期間。各行に、始まりの足の窓 (s − W, s] の決定の足が NWIN_LT 本未満の割合。"""
    lo = np.searchsorted(t, t - W, side="right")
    rows = []
    for bn, a_, b_ in (("下", 0.0, tb["q1"]), ("中", tb["q1"], tb["q2"]), ("上", tb["q2"], 1e9)):
        cs = [c for c in _counted(t, hits) if a_ <= c[2] < b_]
        for gn, fn in (("週末明け", lambda c: is_weekend_start(int(t[c[1]]))), ("それ以外", lambda c: not is_weekend_start(int(t[c[1]]))),
                       ("帯全体", lambda c: True)):
            sel = [c for c in cs if fn(c)]
            r = _row([(c[3], c[4]) for c in sel], days)
            nw = [int(c[1] - lo[c[1]] + 1) for c in sel]
            r.update({"band": bn, "group": gn, "lt": (sum(1 for v in nw if v < NWIN_LT) / len(nw)) if nw else None})
            rows.append(r)
    return rows


def off_grid_overlap(t: np.ndarray, hits: list, tb: dict, spans: list) -> dict:
    """帯ごとの、off_grid の区間 [最初の行の始まり, 最後の行の始まり + 60 秒] にかかる数えたレースの数。"""
    out = {"下": 0, "中": 0, "上": 0}
    for c in _counted(t, hits):
        s0, s1 = int(t[c[1]]), int(t[c[0]])
        if any(s0 <= b and s1 >= a for a, b in spans):
            band = "下" if c[2] < tb["q1"] else ("中" if c[2] < tb["q2"] else "上")
            out[band] += 1
    return out


def run(series: dict, window: str, judge: str) -> tuple[list, dict]:
    t = series["end_ns"]
    x = np.log(series["close"])
    if judge == "close":
        hits = replay(t, x, WIN[window])
    elif judge == "highlow":
        hits = replay(t, x, WIN[window], np.log(series["high"]), np.log(series["low"]))
    else:
        raise SystemExit(f"judge は close か highlow: {judge!r}")
    days = day_list(t)
    return hits, tables(t, hits, days)


# ---------------------------------------------------------------- 書き出し

def _fmt(r: dict, hl: bool) -> str:
    def iv(p):
        return "—" if p[0] is None else f"[{p[0]:.3f}, {p[1]:.3f}]"
    rate = "—" if r["rate"] is None else f"{r['rate']:.3f}"
    s = f"| {r['n']:,} | {r['rev']:,} | {rate} | {iv(r['wilson'])} | {iv(r['block'])} |"
    if hl:
        s += f" {r['und_both']:,} | {r['und_prev']:,} |"
    return s


def _iv(p):
    return "—" if p[0] is None else f"[{p[0]:.3f}, {p[1]:.3f}]"


def _extra_md(window: str, judge: str, tb: dict, extra: dict, names: dict) -> list:
    out = []
    if extra.get("off_grid") is not None:
        og = extra["off_grid"]
        out += [f"- 記述(批評家の指摘による): off_grid の区間にかかる数えたレース 下 {og['下']:,}・中 {og['中']:,}・上 {og['上']:,}"
                f"(計 {sum(og.values()):,})", ""]
    if extra.get("weekend"):
        out += [f"### 窓 {window}: 週末明けに始まったレース / それ以外(結果を見てから分けた記述(批評家の指摘による。本番の読みは上の表 = 登録どおりの同じ規則))",
                "", f"- 週末明けの定義: {WEEKEND_DEF}。始まり = 起点を置いた足(直前の当たりの足)の終わりの時刻。期間は全期間。",
                f"- 「窓の決定の足 < {NWIN_LT}」= 始まりの足の 1 日の窓 (始まり − 1 日, 始まり] の決定の足が {NWIN_LT} 本未満のレースの割合。", "",
                f"| 帯(bp) | 始まり | レース | 反転 | 反転の割合 | 二項の 95% 区間 | 日の塊の 95% 区間 | 窓の決定の足 < {NWIN_LT} の割合 |",
                "|---|---|---|---|---|---|---|---|"]
        for r in extra["weekend"]:
            rate = "—" if r["rate"] is None else f"{r['rate']:.3f}"
            lt = "—" if r["lt"] is None else f"{r['lt']:.3f}"
            out.append(f"| {names[r['band']]} | {r['group']} | {r['n']:,} | {r['rev']:,} | {rate} | {_iv(r['wilson'])} | {_iv(r['block'])} | {lt} |")
        out.append("")
    if extra.get("close_edges"):
        ce = extra["close_edges"]
        out += [f"### 窓 {window}・高値・安値の判定を終値の判定の帯の境で数え直した記述(批評家の指摘による。全期間)", "",
                f"- 境(同じ窓の終値の判定の境、bp): 下 〜{ce['q1'] * 1e4:.1f} / 中 {ce['q1'] * 1e4:.1f}〜{ce['q2'] * 1e4:.1f} / 上 {ce['q2'] * 1e4:.1f}〜", "",
                "| 帯(bp) | レース | 反転 | 反転の割合 | 二項の 95% 区間 | 日の塊の 95% 区間 |", "|---|---|---|---|---|---|"]
        cn = {"下": f"下 〜{ce['q1'] * 1e4:.1f}", "中": f"中 {ce['q1'] * 1e4:.1f}〜{ce['q2'] * 1e4:.1f}", "上": f"上 {ce['q2'] * 1e4:.1f}〜"}
        for r in ce["rows"]:
            if r["part"] == "全期間" and r["band"] != "全部":
                out.append(f"| {cn[r['band']]} | {r['n']:,} | {r['rev']:,} | {r['rate']:.3f} | {_iv(r['wilson'])} | {_iv(r['block'])} |")
        out.append("")
    return out


def write_md(data: str, info: dict, results: list, path: str) -> str:
    out = [f"# K-135 の確かめ: {info['label']}(バリアレースの反転の割合。判定と読みは書かない)", "",
           "台本: `scripts/why_predict/k135_race_confirm.py`(規則の出所は台本の docstring)。",
           "", "## データ", "",
           f"- 期間(足の始まりで [始め, 終わり)): {info['lo']} 〜 {info['hi']}",
           f"- 読んだファイル(封印の門 `bot.bt.data.loader.load`): " + "、".join(f"`{p}`" for p in info["files"]),
           f"- 門が出した足 {info['bars']:,}、うち決定の足(volume > 0。カードが呼ばれる足){info['decided']:,}、"
           f"volume 0 の足 {info['vol0']:,}(うち終値が直前の足と違う {info['vol0_close_changed']:,})",
           f"- 門が報告した異常の種類と数: {info['anomalies']}"]
    if info.get("off_grid"):
        out.append(f"- **分の格子に乗らない足(off_grid)の扱い: {info['off_grid_policy']}**(規則の出所に決まりが無い。リードへの問い。"
                   "accept = 足の時刻を切り下げずにそのまま使う)。ファイルごと: "
                   + " / ".join(f"`{p.split('/')[-1]}` {v['n']:,} 本({v['first']}〜{v['last']}、秒 {v['seconds']})"
                                for p, v in info["off_grid"].items()))
    if "gap" in info["anomalies"]:
        og_n = info["anomalies"].get("off_grid", 0)
        miss = info["range_minutes"] - info["bars"]
        out.append(f"- gap の内訳: 期間の分の数 {info['range_minutes']:,} − 門が出した足 {info['bars']:,} = 欠けた分 {miss:,}。"
                   f"欠けた分 + off_grid {og_n:,} = {miss + og_n:,}(門の gap {info['anomalies']['gap']:,})。off_grid の行は :00 の枠を空けるので"
                   f"、gap のうち {og_n:,} は off_grid のずれの見かけ")
    out.append(f"- 門が読んだ封印の記録 {info['seal_records_n']} 件のうち、読んだファイルに当たるもの(単位・時刻の列・切りの時刻): "
               + " / ".join(f"`{p.split('/')[-1]}` " + ("、".join(f"{u}・{c}・{cut}" for u, c, cut in es) if es else "なし")
                            for p, es in info["seals"]))
    out.append("")
    for (window, judge, tb, extra) in results:
        hl = judge == "highlow"
        mark = "" if IN_PREDICTION[window] else ("(予言の外。記述。オーナーの合意(L-709)は 1 日と 1 週の 2 つ。"
                                                 "1 時間は合意の外で作った記述)")
        out += [f"## 窓 {window}・{'終値の判定' if not hl else '高値・安値の判定'}{mark}", "",
                f"- 当たり {tb['hits']:,}(最初の当たり {tb['first']}・反転 {tb['n_rev']:,}・継続 {tb['n_cont']:,}"
                + (f"・決まらない: 同じ足で両方 {tb['n_und_both']:,}・前の側が分からない {tb['n_und_prev']:,}" if hl else "")
                + f")。最初の当たりの日 {tb['first_day']}",
                f"- 日の並び(決定のある日本時間の日){tb['days']:,} 日({tb['first_d']}〜{tb['last_d']})、前半・後半の境 {tb['edge']}"
                f"(前半 = 境より前)。数えた当たりのうち日の並びの外の日に落ちたもの {tb['n_outside_days']:,}"
                f"(二項の数には入り、日の塊の区間には入らない。race_replay.py・race_block_ci.py と同じ)",
                f"- 帯の境(数えたレースの始めの w の 3 分位、bp): 下 〜{tb['q1'] * 1e4:.1f} / 中 {tb['q1'] * 1e4:.1f}〜{tb['q2'] * 1e4:.1f} / "
                f"上 {tb['q2'] * 1e4:.1f}〜(**帯の境は標本の中**: このデータの全期間の w で決めた)", "",
                "| 帯(bp) | 期間 | レース | 反転 | 反転の割合 | 二項の 95% 区間(Wilson) | 日の塊の 95% 区間(5 日・1,000 回・種 20261004) |"
                + (" 決まらない: 同じ足で両方 | 決まらない: 前の側が分からない |" if hl else ""),
                "|---|---|---|---|---|---|---|" + ("---|---|" if hl else "")]
        names = {"全部": "全部", "下": f"下 〜{tb['q1'] * 1e4:.1f}", "中": f"中 {tb['q1'] * 1e4:.1f}〜{tb['q2'] * 1e4:.1f}",
                 "上": f"上 {tb['q2'] * 1e4:.1f}〜"}
        for r in tb["rows"]:
            out.append(f"| {names[r['band']]} | {r['part']} " + _fmt(r, hl))
        out.append("")
        out += _extra_md(window, judge, tb, extra, names)
    out += ["区間: 二項 = 当たりを独立とみた Wilson の区間(race_replay.py と同じ)。日の塊 = 日本時間の日ごとの反転の数と当たりの数を、",
            "期間の日の並びを循環 5 日の塊で選び直して(1,000 回・種 20261004)群の和 ÷ 群の数を作り直した百分位(race_block_ci.py と同じ",
            "`diag_tables.group_ratio_ci`)。数えるのは最初の当たりを除いた当たり。", ""]
    text = "\n".join(out) + "\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


def write_races(path: str, t: np.ndarray, hits: list) -> None:
    kinds = classify(hits)
    with gzip.open(path, "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["hit_end_ns", "jst_day", "side", "kind", "w_start", "w_next", "race_start_end_ns"])
        for h, kind in zip(hits, kinds):
            k, side, w0, w1, ks = h
            w.writerow([int(t[k]), jst_day(int(t[k])), side, kind, f"{w0:.8f}", f"{w1:.8f}", int(t[ks])])


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True, choices=sorted(DATA))
    ap.add_argument("--windows", default="1d,1w")
    ap.add_argument("--judge", default="close", help="close / highlow をカンマで")
    ap.add_argument("--start", default=None, help="既定はデータごとの期間(docstring)")
    ap.add_argument("--end", default=None)
    ap.add_argument("--out", default=OUT_DIR)
    ap.add_argument("--off-grid", choices=("accept", "drop"), default=None,
                    help="分の格子に乗らない足の扱い。既定なし(出たら止める)。渡した値は表の .md に書く")
    a = ap.parse_args(argv)
    windows = [w for w in a.windows.split(",") if w]
    judges = [j for j in a.judge.split(",") if j]
    for w in windows:
        if w not in WIN:
            raise SystemExit(f"窓は 1h・1d・1w: {w!r}")
    for j in judges:
        if j not in ("close", "highlow"):
            raise SystemExit(f"judge は close か highlow: {j!r}")
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    s = load_series(a.data, iso_ns(a.start) if a.start else None, iso_ns(a.end) if a.end else None, off_grid=a.off_grid)
    print(f"読み込み {time.time() - t0:.0f} 秒、決定の足 {s['info']['decided']:,}")
    results = []
    close_tb = {}
    t = s["end_ns"]
    days = day_list(t)
    spans = [(iso_ns(v["first"]), iso_ns(v["last"]) + 60 * NS) for v in s["info"].get("off_grid", {}).values()]
    for j in judges:
        for w in windows:
            if j == "highlow" and not IN_PREDICTION[w]:
                print(f"高値・安値の判定は 1d・1w だけ(L-709 の比べる 1 つ)。{w} は飛ばす")
                continue
            hits, tb = run(s, w, j)
            extra = {}
            if j == "close":
                close_tb[w] = tb
                if w == "1d":
                    extra["weekend"] = weekend_split(t, hits, days, tb, WIN[w])
            if spans and IN_PREDICTION[w]:
                extra["off_grid"] = off_grid_overlap(t, hits, tb, spans)
            if j == "highlow" and w in close_tb:
                ce = tables(t, hits, days, (close_tb[w]["q1"], close_tb[w]["q2"]))
                extra["close_edges"] = ce
            results.append((w, j, tb, extra))
            write_races(os.path.join(a.out, f"races_{a.data}_{j}_{w}.csv.gz"), s["end_ns"], hits)
    print(write_md(a.data, s["info"], results, os.path.join(a.out, f"{a.data}.md")))


if __name__ == "__main__":
    main()
