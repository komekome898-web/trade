"""2 つのカードの持ち高を、同じ足と同じ参照の系列で並べて比べる台本(W4 §2 の 5)。

使い方(リポジトリの直下で):
    PYTHONPATH=src python <この場所>/compare.py \
        --other-module <相手のカードの .py のパス、または点で区切ったモジュール名> --other-class <クラス名> \
        [--other-kwargs '{...}'] [--mine-kwargs '{"params": {"k": 30}}'] \
        [--start 2017-08-17T15:00:00Z] [--end 2023-12-17T15:00:00Z] [--out 結果.json]

読み方: リポジトリの封印の門を通す(リードの答え: yes)。
  * 持つ足: bot.bt.data.load(kind bar、no_trade = OHLC が全部空の行、gap は accept、no_trade は drop)
    backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_YYYY.csv.gz(列 ts = 1 分の始まり)
  * 参照: bot.bt.data.reference.load_reference(値の列 close、lag 60 秒)
    backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_YYYY.csv.gz(列 open_time)
門は range_ns の終わりが封印の境より後なら、そのファイルを開く前に拒む(allowlist.py の SealRegistry)。
この台本自身も --end が 2023-12-18 00:00 UTC より後なら拒む。

走らせ方: 暦年ごとに区切って run_card を回す(1 回で 6 年分を載せない)。最初の区切り以外は、区切りの始まりの
1 日前から足を渡して慣らし、比べるのは区切りの中の足だけ。両方のカードを区切りごとに新しく作る。

食い違いの型(入力の足と参照の行だけで決める。相手のコードは見ない):
  持ち越し       直前の持ち高を取った足も食い違いで、両方とも直前の持ち高のまま
  履歴の門       その走らせで届いた足が k+2 本未満
  Binance の抜け 今の分(t-60s)か k 本前の分(t-(k+1)*60s)の参照の行が無い
  bitFlyer の抜け [t-(k+1)*60s, t) の分のどれかに空でない足が無い(足が無い、または volume 0)
  境の等号       mom が ±thr か ±exit に 1e-12 以内
  その他         上のどれでもない
"""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
import sys
from collections import OrderedDict
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from bot.bt.data.errors import DataError  # noqa: E402
from bot.bt.data.loader import load  # noqa: E402
from bot.bt.data.reference import load_reference  # noqa: E402
from bot.research.cards.card import CardError  # noqa: E402
from bot.research.cards.run import run_card  # noqa: E402
from rewrite_card import DEFAULT_PARAMS, MIN_NS, REF_NAME, XborderMomRewrite  # noqa: E402

SEAL = datetime(2023, 12, 18, tzinfo=timezone.utc)
BARS_DIR = "backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906"
BARS_FILE = "candles_1m_{y}.csv.gz"
REF_DIR = "backtest_data/binance_BTCUSDT_1m_20170801_20231231"
REF_FILE = "binance_BTCUSDT_1m_{y}.csv.gz"
DAY_NS = 1440 * MIN_NS
DECLARATIONS = {REF_NAME: {"lag_ns": MIN_NS, "source": "W4 委任文(リードの決め): open_time + 60 秒"}}
BAR_RESOLVE = {"gap": "accept", "no_trade": "drop"}
TYPES = ["持ち越し", "履歴の門", "Binance の抜け", "bitFlyer の抜け", "境の等号", "その他"]


def to_ns(d: datetime) -> int:
    return int(d.timestamp()) * 1_000_000_000


def to_iso(ns: int) -> str:
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_arg_time(s: str) -> datetime:
    d = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def years(lo_ns: int, hi_ns: int) -> range:
    y0 = datetime.fromtimestamp(lo_ns / 1e9, tz=timezone.utc).year
    y1 = datetime.fromtimestamp((hi_ns - 1) / 1e9, tz=timezone.utc).year
    return range(y0, y1 + 1)


def existing(root, d, pattern, lo_ns, hi_ns):
    return [f"{d}/{pattern.format(y=y)}" for y in years(lo_ns, hi_ns)
            if os.path.exists(os.path.join(root, d, pattern.format(y=y)))]


def bar_dataset(root, lo_ns, hi_ns):
    return {"name": "bars", "paths": existing(root, BARS_DIR, BARS_FILE, lo_ns, hi_ns), "range_ns": [lo_ns, hi_ns],
            "spec": {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip", "kind": "bar",
                     "symbol": "FX_BTC_JPY", "asset": "crypto",
                     "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"},
                     "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
                     "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start",
                     "no_trade": {"fields": ["open", "high", "low", "close"]}}}


def ref_dataset(root, lo_ns, hi_ns):
    return {"name": REF_NAME, "paths": existing(root, REF_DIR, REF_FILE, lo_ns, hi_ns), "range_ns": [lo_ns, hi_ns],
            "spec": {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip",
                     "time": {"columns": ["open_time"], "unit": "iso", "tz": "UTC"}, "value": "close"}}


def load_class(module: str, cls: str):
    if module.endswith(".py") or os.path.sep in module:
        path = os.path.abspath(module)
        sys.path.insert(0, os.path.dirname(path))
        spec = importlib.util.spec_from_file_location(f"_other_card_{abs(hash(path))}", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod  # dataclass などがモジュールを sys.modules から引くため
        spec.loader.exec_module(mod)
    else:
        mod = importlib.import_module(module)
    return getattr(mod, cls)


def classify(i, r1, r2, mism, ref_map, nonempty_starts, k, thr, exit_band, prev_decided):
    """食い違い i の型と、そのときの入力(module docstring)。"""
    t = int(r1.end_ns[i])
    now_row, past_row = t - MIN_NS, t - (k + 1) * MIN_NS
    nv, pv = ref_map.get(now_row), ref_map.get(past_row)
    n_delivered = i + 1  # その走らせで届いた足(空の足も含む)
    missing_min = [m for m in range(past_row, t, MIN_NS) if m not in nonempty_starts]
    mom = float(np.log(nv / pv)) if (nv is not None and pv is not None and pv > 0) else None
    j = prev_decided[i]
    info = {"index": int(i), "bar_end": to_iso(t), "mine": float(r1.exposure[i]), "other": float(r2.exposure[i]),
            "volume": float(r1.volume[i]),
            "ref_now": [to_iso(now_row), nv], "ref_past": [to_iso(past_row), pv],
            "mom_pct": None if mom is None else mom * 100,
            "prev_minute_bar": (t - 2 * MIN_NS) in nonempty_starts, "next_minute_bar": t in nonempty_starts,
            "missing_nonempty_minutes_in_window": len(missing_min),
            "prev_decided_end": None if j < 0 else to_iso(int(r1.end_ns[j]))}
    if j >= 0 and mism[j] and r1.exposure[i] == r1.exposure[j] and r2.exposure[i] == r2.exposure[j]:
        typ = "持ち越し"
    elif n_delivered < k + 2:
        typ = "履歴の門"
    elif nv is None or pv is None:
        typ = "Binance の抜け"
    elif missing_min:
        typ = "bitFlyer の抜け"
    elif mom is not None and min(abs(mom - thr), abs(mom + thr), abs(abs(mom) - exit_band)) <= 1e-12:
        typ = "境の等号"
    else:
        typ = "その他"
    info["type"] = typ
    return info


def run_chunk(root, lo, hi, warm_lo, other_cls, other_kw, mine_kw, k, thr, exit_band):
    res = load(root, [bar_dataset(root, warm_lo, hi)])
    kinds = sorted({a["kind"] for a in res.anomalies("bars")})
    bars = list(res.events("bars", BAR_RESOLVE))
    ref = load_reference(root, ref_dataset(root, warm_lo - DAY_NS, hi), declarations=DECLARATIONS)
    runs = []
    for card in (XborderMomRewrite(**mine_kw), other_cls(**other_kw)):
        runs.append(run_card(card, bars, references={REF_NAME: ref}, declarations=DECLARATIONS,
                             venue="bitflyer", symbol="FX_BTC_JPY"))
    r1, r2 = runs
    if not np.array_equal(r1.decided, r2.decided):
        raise CardError("2 つの走らせで、持ち高を取った足が違う")
    inside = r1.start_ns >= lo
    dec = r1.decided
    mism = dec & (r1.exposure != r2.exposure)
    prev_decided = np.full(len(bars), -1)
    last = -1
    for i in range(len(bars)):
        prev_decided[i] = last
        if dec[i]:
            last = i
    ref_map = dict(zip(ref.times_ns, ref.values))
    nonempty_starts = {int(s) for s, v in zip(r1.start_ns, r1.volume) if v > 0}
    infos = [classify(i, r1, r2, mism, ref_map, nonempty_starts, k, thr, exit_band, prev_decided)
             for i in np.flatnonzero(mism & inside)]
    return {"bars": int(inside.sum()), "decided": int((dec & inside).sum()), "mismatch": len(infos),
            "infos": infos, "anomaly_kinds": kinds, "ref_rows": len(ref)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="2 つのカードの持ち高を同じ入力で比べる")
    ap.add_argument("--other-module", required=True)
    ap.add_argument("--other-class", required=True)
    ap.add_argument("--other-kwargs", default="{}")
    ap.add_argument("--mine-kwargs", default="{}")
    ap.add_argument("--start", default="2017-08-17T15:00:00Z")
    ap.add_argument("--end", default="2023-12-17T15:00:00Z")
    ap.add_argument("--root", default=".")
    ap.add_argument("--show", type=int, default=20)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    start, end = parse_arg_time(a.start), parse_arg_time(a.end)
    if end > SEAL:
        print(f"拒否: --end {end.isoformat()} は封印の境 {SEAL.isoformat()} より後")
        return 2
    if start >= end:
        print("拒否: --start が --end 以後")
        return 2
    lo_all, hi_all = to_ns(start), to_ns(end)
    mine_kw, other_kw = json.loads(a.mine_kwargs), json.loads(a.other_kwargs)
    p = dict(DEFAULT_PARAMS)
    p.update(mine_kw.get("params", {}))
    k, thr, exit_band = int(p["k"]), float(p["thr_pct"]) / 100, float(p["exit_pct"]) / 100
    other_cls = load_class(a.other_module, a.other_class)
    print(f"期間 {to_iso(lo_all)} 〜 {to_iso(hi_all)}(終わりを含まない)、自分の側の k={k} thr={thr} exit={exit_band}")

    total = {"bars": 0, "decided": 0, "mismatch": 0}
    infos = []
    for y in years(lo_all, hi_all):
        lo = max(lo_all, to_ns(datetime(y, 1, 1, tzinfo=timezone.utc)))
        hi = min(hi_all, to_ns(datetime(y + 1, 1, 1, tzinfo=timezone.utc)))
        warm_lo = lo if lo == lo_all else lo - DAY_NS
        try:
            c = run_chunk(a.root, lo, hi, warm_lo, other_cls, other_kw, mine_kw, k, thr, exit_band)
        except (DataError, CardError) as e:
            print(f"  {y}: 止まった({type(e).__name__}): {e}")
            return 3
        print(f"  {y}: 足 {c['bars']} 本、持ち高を取った足 {c['decided']} 本、食い違い {c['mismatch']} 本"
              f"(参照 {c['ref_rows']} 行、足の異常の種類 {c['anomaly_kinds']})")
        for key in total:
            total[key] += c[key]
        infos += c["infos"]

    ratio = total["mismatch"] / total["decided"] if total["decided"] else float("nan")
    print(f"足: {total['bars']} 本 / 両方が持ち高を取った足: {total['decided']} 本 / "
          f"食い違った足: {total['mismatch']} 本(割合 {ratio:.6%})")
    by = OrderedDict((t, [x for x in infos if x["type"] == t]) for t in TYPES)
    print("型ごとの件数:")
    for t, xs in by.items():
        print(f"  {t}: {len(xs)}")
    for t, xs in by.items():
        if xs:
            print(f"[{t}] 代表 {min(a.reps, len(xs))} 件:")
            for x in xs[: a.reps]:
                print("  " + json.dumps(x, ensure_ascii=False))
    print(f"最初の {min(a.show, len(infos))} 件:")
    for x in infos[: a.show]:
        print(f"  #{x['index']} {x['bar_end']} mine {x['mine']:+.0f} other {x['other']:+.0f} 型 {x['type']}")
    stop = ratio > 0.001 or len(by["その他"]) > 0
    print("判断の基準(0.1% 超、または理由を説明できない食い違い): " + ("止める" if stop else "超えていない"))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump({"start": to_iso(lo_all), "end": to_iso(hi_all), **total, "ratio": ratio,
                       "counts": {t: len(xs) for t, xs in by.items()}, "mismatches": infos}, f,
                      ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
