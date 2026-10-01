#!/usr/bin/env python3
"""K1 段階 G(2026-10-01、委任文 docs/DATA/delegations/20261001_k1_stage_g.md): 第 17 部の入力を、
新しい環境のデータ層を通して畳む。データの門(scripts/k1_newenv_g_datagate.py)の下で回す。

規則(docs/PHASE2/K1/XVENUE_PREREG.md §2「揃え方」、RESULT.md 1.2):
  - シグナル側 = Binance BTCUSDT 現物 1 分足。n_trades == 0 の行は約定の無い分として落とす
    (データ層の synthetic 印 + drop の方針)。
  - 価格側 = bitFlyer FX_BTC_JPY 1 分足。OHLC が空の行(約定 0 の分)は落とす。G-2 の直し(2026-10-01)の後は
    データ層の宣言 no_trade(open / high / low / close が全部空)+ 方針 drop で読む(写しは作らない。
    落とした行数は FOLD_MANIFEST.json の inputs[].anomalies.no_trade)。直す前は写しを自前で作っていた
    (filter_bitflyer、ENV_DEFECTS.md G-2 の回避。消した)。
  - 両取引所の分足を「UTC の分」で内部結合する。分の境界に乗っていない行(Binance に実在)は、
    bars_from_bars(60 秒)で分の頭に切り下げてから結合する(規則の文「UTC の分」による。当時の
    コードの結合の仕方とは違いうる。DIFF.md で扱う)。
  - 足への畳みは結合後、両取引所を同じ窓で(bot.bt.vector.bars_from_bars)。窓の開始時刻が両側で
    一致することを確かめる。
  - 2023-12-18T00:00Z(P2-08 の seal_from_ts)以降の行は 1 行も使わない: データ層の range_ns の終わりを
    CUT にし、さらに出力のすべての足で 足の終わり <= CUT を自前で確かめる。

出力(backtest_data/k1_newenv_g_20261001/):
  {venue}_{foot}m_{range}.csv.gz   start_ts,o,h,l,c,vol(venue = binance / bitflyer、range = full /
                                   2018_2021 / 2022_20231217)
  FOLD_MANIFEST.json               読んだファイル(パス・sha256・行数・最初と最後の ts)、結合の統計、
                                   出力の sha256・行数・最初と最後の足、自前の範囲の確認

使い方: PYTHONPATH=scripts:src python3 scripts/k1_newenv_g_fold.py [--feet 1 3 5 15 30 60]
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import k1_newenv_g_datagate as GATE  # noqa: E402,F401  (データの門: import の時点で入る)
import numpy as np  # noqa: E402

from bot.bt.data import load  # noqa: E402
from bot.bt.vector import bars as VB  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT_DIR = "backtest_data/k1_newenv_g_20261001"
BIN_DIR = "backtest_data/binance_BTCUSDT_1m_20170801_20231231"
BF_DIR = "backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906"
NS = 1_000_000_000
YEARS = tuple(range(2017, 2024))
FEET = (1, 3, 5, 15, 30, 60)


def ns_of(s: str) -> int:
    return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()) * NS


CUT = ns_of("2023-12-18T00:00:00")  # P2-08 SEALED.json の seal_from_ts(forward_start 2026-09-06 より前)
RANGES = {"full": (None, CUT), "2018_2021": (ns_of("2018-01-01T00:00:00"), ns_of("2022-01-01T00:00:00")),
          "2022_20231217": (ns_of("2022-01-01T00:00:00"), CUT)}


def iso(t_ns: int) -> str:
    return datetime.fromtimestamp(t_ns // NS, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def spec(symbol: str, tcol: str, fields: dict, synthetic=None, no_trade=None) -> dict:
    s = {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip", "kind": "bar",
         "symbol": symbol, "asset": "crypto", "time": {"columns": [tcol], "unit": "iso", "tz": "UTC"},
         "fields": fields, "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start"}
    if synthetic:
        s["synthetic"] = synthetic
    if no_trade:
        s["no_trade"] = {"fields": list(no_trade)}
    return s


BIN_SPEC = spec("BTCUSDT", "open_time", {"open": "open", "high": "high", "low": "low", "close": "close",
                                         "volume": "volume"}, {"column": "n_trades", "values": ["0"]})
BF_SPEC = spec("FX_BTC_JPY", "ts", {"open": "open", "high": "high", "low": "low", "close": "close",
                                    "volume": "volume"}, no_trade=("open", "high", "low", "close"))


def sha_file(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


OFF_GRID = {"policy": "accept"}  # --offgrid-drop で "drop"(DIFF.md D-1 の確かめ: 当時の結合の仕方を再現する変種)


def read_layer(rel: str, sp: dict, lo: int, hi: int) -> tuple[dict, dict]:
    """データ層で 1 ファイルを [lo, hi) で読み、方針を当てた事象を (start_ns, o, h, l, c, v) の列で返す。"""
    r = load(REPO, [{"name": "d", "paths": [rel], "spec": sp, "range_ns": [lo, hi]}])
    an = r.anomalies("d")
    kinds = sorted({a["kind"] for a in an})
    pol = {"synthetic": "drop", "no_trade": "drop", "gap": "accept", "off_grid": OFF_GRID["policy"]}
    unknown = [k for k in kinds if k not in pol]
    if unknown:
        raise SystemExit(f"{rel}: anomalies {unknown} have no policy in this delegation")
    evs = r.events("d", {k: pol[k] for k in kinds})
    cols = {k: [] for k in ("t", "o", "h", "l", "c", "v")}
    for e in evs:
        cols["t"].append(int(e.start_time_ns))
        cols["o"].append(e.open)
        cols["h"].append(e.high)
        cols["l"].append(e.low)
        cols["c"].append(e.close)
        cols["v"].append(e.volume)
    recs = r.records("d")
    f = r.files()[0]
    counts = {}
    for a in an:
        counts[a["kind"]] = counts.get(a["kind"], 0) + 1
    info = {"path": rel, "sha256": f.sha256, "size": f.size, "sealed_unit": f.sealed_unit,
            "rows_read": f.rows_read, "rows_kept_in_range": f.rows_kept, "events_after_policy": len(cols["t"]),
            "anomalies": counts, "policies": {k: pol[k] for k in kinds},
            "range": [iso(lo), iso(hi)],
            "first_ts": iso(min(x["start_ns"] for x in recs)) if recs else None,
            "last_ts": iso(max(x["start_ns"] for x in recs)) if recs else None,
            "last_ts_after_policy": iso(max(cols["t"])) if cols["t"] else None,
            "off_minute_rows": sum(1 for t in cols["t"] if t % (60 * NS) != 0)}
    return cols, info


def to_minutes(cols: dict) -> dict:
    """分の境界に乗っていない行を分の頭に切り下げる(bars_from_bars 60 秒)。"""
    out = VB.bars_from_bars(cols["t"], cols["o"], cols["h"], cols["l"], cols["c"], cols["v"], 60)
    return {"t": np.array([b["start_ns"] for b in out], dtype=np.int64), "o": np.array([b["open"] for b in out]),
            "h": np.array([b["high"] for b in out]), "l": np.array([b["low"] for b in out]),
            "c": np.array([b["close"] for b in out]), "v": np.array([b["volume"] for b in out])}


def write_bars(rel: str, bars: list[dict]) -> dict:
    path = os.path.join(REPO, rel)
    buf = io.StringIO()
    buf.write("start_ts,o,h,l,c,vol\n")
    for b in bars:
        buf.write(f"{iso(b['start_ns'])},{b['open']!r},{b['high']!r},{b['low']!r},{b['close']!r},{b['volume']!r}\n")
    with gzip.GzipFile(path, "wb", compresslevel=6, mtime=0) as fh:
        fh.write(buf.getvalue().encode())
    return {"path": rel, "rows": len(bars), "sha256": sha_file(path),
            "first_start": iso(bars[0]["start_ns"]) if bars else None,
            "last_start": iso(bars[-1]["start_ns"]) if bars else None}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--feet", type=int, nargs="+", default=list(FEET))
    ap.add_argument("--cache", default=None, help="読んだ分足を .npz に置く / あれば読み直さずに使う(スクラッチパッド)")
    ap.add_argument("--years", type=int, nargs="+", default=list(YEARS))
    ap.add_argument("--offgrid-drop", action="store_true",
                    help="変種: 分の境界に乗っていない Binance の行を落とす(切り下げない)。出力は *_{tag}、5・15 分だけ")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--out-dir", default=None,
                    help="出力の置き場(既定は OUT_DIR)。段階 G の出力を書き換えずに回し直して比べるとき(G-7 の確かめ、"
                         "FIXES.md §11)はスクラッチパッドを名指しする")
    a = ap.parse_args()
    global OUT_DIR
    if a.out_dir:
        OUT_DIR = os.path.abspath(a.out_dir)
    if a.offgrid_drop:
        OFF_GRID["policy"] = "drop"
    t0 = time.time()
    os.makedirs(os.path.join(REPO, OUT_DIR), exist_ok=True)
    man = {"cut": iso(CUT), "cut_source": "backtest_data/phase2_sealed/P2-08/SEALED.json seal_from_ts",
           "inputs": [], "outputs": [], "alignment": {}, "self_check": {}}
    sig = {k: [] for k in ("t", "o", "h", "l", "c", "v")}
    pri = {k: [] for k in ("t", "o", "h", "l", "c", "v")}
    cached = a.cache and os.path.isfile(a.cache)
    if cached:
        z = np.load(a.cache, allow_pickle=False)
        sig = {k: list(z["s_" + k]) for k in sig}
        pri = {k: list(z["p_" + k]) for k in pri}
        with open(a.cache + ".json", encoding="utf-8") as fh:
            man["inputs"] = json.load(fh)
    for y in (() if cached else a.years):
        lo, hi = ns_of(f"{y}-01-01T00:00:00"), min(ns_of(f"{y + 1}-01-01T00:00:00"), CUT)
        cols, info = read_layer(f"{BIN_DIR}/binance_BTCUSDT_1m_{y}.csv.gz", BIN_SPEC, lo, hi)
        man["inputs"].append(info)
        for k in sig:
            sig[k].extend(cols[k])
        cols, info = read_layer(f"{BF_DIR}/candles_1m_{y}.csv.gz", BF_SPEC, lo, hi)  # G-2: 写しを作らない
        man["inputs"].append(info)
        for k in pri:
            pri[k].extend(cols[k])
        print(f"[{time.time() - t0:6.0f}s] {y} read", flush=True)
    if a.cache and not cached:
        np.savez(a.cache, **{"s_" + k: np.asarray(v) for k, v in sig.items()}, **{"p_" + k: np.asarray(v) for k, v in pri.items()})
        with open(a.cache + ".json", "w", encoding="utf-8") as fh:
            json.dump(man["inputs"], fh)
    sm, pm = to_minutes(sig), to_minutes(pri)
    if a.tag:  # 変種: 結合・畳みだけして *_{tag} を書き、終わる(本番の出力と FOLD_MANIFEST.json には触らない)
        common, si, pi = np.intersect1d(sm["t"], pm["t"], assume_unique=True, return_indices=True)
        S = {k: v[si] for k, v in sm.items()}
        P = {k: v[pi] for k, v in pm.items()}
        vm = {"variant": a.tag, "offgrid_policy": OFF_GRID["policy"], "years": a.years, "inputs": man["inputs"],
              "minutes_both": int(len(common)), "outputs": []}
        for foot in (5, 15):
            for venue, X in (("binance", S), ("bitflyer", P)):
                bb = VB.bars_from_bars(X["t"], X["o"], X["h"], X["l"], X["c"], X["v"], foot * 60)
                vm["outputs"].append(write_bars(f"{OUT_DIR}/{venue}_{foot}m_{a.tag}.csv.gz", bb))
        with open(os.path.join(REPO, OUT_DIR, f"VARIANT_{a.tag}.json"), "w", encoding="utf-8") as fh:
            json.dump(vm, fh, ensure_ascii=False, indent=1)
        print(json.dumps({k: v for k, v in vm.items() if k != "inputs"}))
        return
    # 参考列 (i) の当時の値(第 12 部 ② の Binance)は結合していない Binance の足で測られた。比べるために
    # 結合前の Binance の足も 5 分・15 分で書く(range = full_unjoined)
    for foot in (5, 15):
        ub = VB.bars_from_bars(sm["t"], sm["o"], sm["h"], sm["l"], sm["c"], sm["v"], foot * 60)
        ub = [x for x in ub if x["start_ns"] + foot * 60 * NS <= CUT]
        man["outputs"].append({"foot": foot, "range": "full_unjoined", "venue": "binance",
                               **write_bars(f"{OUT_DIR}/binance_{foot}m_full_unjoined.csv.gz", ub)})
    man["self_check"]["signal_minutes_collided_by_floor"] = len(sig["t"]) - len(sm["t"])
    man["self_check"]["price_minutes_collided_by_floor"] = len(pri["t"]) - len(pm["t"])
    common, si, pi = np.intersect1d(sm["t"], pm["t"], assume_unique=True, return_indices=True)
    yrs = lambda ts: np.array([datetime.fromtimestamp(int(t) // NS, tz=timezone.utc).year for t in ts])  # noqa: E731
    ys, yp, yb = yrs(sm["t"]), yrs(pm["t"]), yrs(common)
    for y in YEARS:
        ns_, np_, nb = int((ys == y).sum()), int((yp == y).sum()), int((yb == y).sum())
        man["alignment"][str(y)] = {"minutes_signal": ns_, "minutes_price": np_, "minutes_both": nb,
                                    "dropped_share_signal": round(1 - nb / ns_, 4) if ns_ else None,
                                    "dropped_share_price": round(1 - nb / np_, 4) if np_ else None}
    S = {k: v[si] for k, v in sm.items()}
    P = {k: v[pi] for k, v in pm.items()}
    max_end = 0
    for foot in a.feet:
        sb = VB.bars_from_bars(S["t"], S["o"], S["h"], S["l"], S["c"], S["v"], foot * 60)
        pb = VB.bars_from_bars(P["t"], P["o"], P["h"], P["l"], P["c"], P["v"], foot * 60)
        if [b["start_ns"] for b in sb] != [b["start_ns"] for b in pb]:
            raise SystemExit(f"foot {foot}: the two venues' windows differ after the join")
        # ディスク(残り約 0.6 GB、05:40 UTC に 1 回尽きた): 全期間と 2018〜2021 は主統計の足(5・15 分)だけ書く
        for rname, (lo, hi) in RANGES.items():
            if foot not in (5, 15) and rname != "2022_20231217":
                continue
            keep = [i for i, b in enumerate(sb) if (lo is None or b["start_ns"] >= lo) and b["start_ns"] + foot * 60 * NS <= hi]
            for venue, bars in (("binance", sb), ("bitflyer", pb)):
                sel = [bars[i] for i in keep]
                if sel:
                    max_end = max(max_end, sel[-1]["start_ns"] + foot * 60 * NS)
                man["outputs"].append({"foot": foot, "range": rname, "venue": venue,
                                       **write_bars(f"{OUT_DIR}/{venue}_{foot}m_{rname}.csv.gz", sel)})
        print(f"[{time.time() - t0:6.0f}s] foot {foot}: {len(sb)} bars", flush=True)
    man["self_check"]["max_bar_end_written"] = iso(max_end)
    man["self_check"]["max_bar_end_le_cut"] = bool(max_end <= CUT)
    man["self_check"]["max_input_event_start"] = iso(int(max(sm["t"].max(), pm["t"].max())))
    man["self_check"]["max_input_event_end_le_cut"] = bool(max(sm["t"].max(), pm["t"].max()) + 60 * NS <= CUT)
    man["wall_s"] = round(time.time() - t0, 1)
    man["files_opened_under_data_roots"] = [os.path.relpath(p, REPO) for p in GATE.OPENED]
    with open(os.path.join(REPO, OUT_DIR, "FOLD_MANIFEST.json"), "w", encoding="utf-8") as fh:
        json.dump(man, fh, ensure_ascii=False, indent=1)
    if not (man["self_check"]["max_bar_end_le_cut"] and man["self_check"]["max_input_event_end_le_cut"]):
        raise SystemExit("self check failed: a row at or after the cut")
    print(json.dumps(man["self_check"]), f"wall {man['wall_s']}s")


if __name__ == "__main__":
    main()
