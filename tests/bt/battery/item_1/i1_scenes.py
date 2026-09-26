"""Item 1 battery (データと時刻): the scenes.

Every scene is a dict:
    id         -- unique id, prefixed by its viewpoint (v1- ... v7-)
    viewpoint  -- V1 .. V7 (REQUIREMENTS.md §2)
    kind       -- 値 (a value is right) | 能力 (a capability, judged by the result it must give)
    what       -- 何を測るか
    how        -- 正解の出し方 (how the expected answer was fixed, without looking at any engine)
    input      -- what the adapter receives (plus "root", added by the runner)
    expect     -- the expected answer (never given to the adapter)
    variant    -- (optional) a second input that the target must REFUSE (V5)
    tol        -- (optional) relative tolerance for floats; absent = exact equality

All inputs are synthetic.  Times are built from UTC calendar components with
integer arithmetic (``ns`` below); a file's text is written FROM the chosen
instant, so the instant is the answer by construction (a correct normaliser
inverts the writing).  Only the standard library is used, so this module also
loads under every survey tool's interpreter.
"""
from __future__ import annotations

import calendar
import gzip
import hashlib
import random
from fractions import Fraction

NS = 1_000_000_000
BASE_DAY = (2026, 1, 5)  # a Monday


def ns(y: int, mo: int, d: int, h: int = 0, mi: int = 0, s: int = 0, frac_ns: int = 0, offset_h: int = 0) -> int:
    """UTC epoch nanoseconds of a wall-clock time written at UTC+offset_h."""
    return (calendar.timegm((y, mo, d, h, mi, s, 0, 0, 0)) - offset_h * 3600) * NS + frac_ns


T0 = ns(*BASE_DAY)  # 2026-01-05T00:00:00Z


def _civil(t_ns: int, offset_h: int = 0):
    import datetime as _dt
    sec, frac = divmod(t_ns + offset_h * 3600 * NS, NS)
    d = _dt.datetime(1970, 1, 1) + _dt.timedelta(seconds=sec)
    return d, frac


def iso(t_ns: int, *, offset_h: int = 0, digits: int = 9, sep: str = "T", suffix: str = "Z") -> str:
    """Write t_ns as an ISO-8601 text at UTC+offset_h with `digits` fraction digits.

    Digits beyond what the instant carries are zeros; fewer digits require the
    instant to be representable (asserted).  suffix: "Z", "+09:00", "" (naive).
    """
    d, frac = _civil(t_ns, offset_h)
    head = d.strftime(f"%Y-%m-%d{sep}%H:%M:%S")
    f9 = f"{frac:09d}"
    assert f9[digits:] == "0" * (9 - digits), (t_ns, digits)
    body = head + ("." + f9[:digits] if digits else "")
    return body + suffix


def dec(t_ns: int, unit: str) -> str:
    """Write t_ns as a decimal number of `unit` (s/ms/us/ns), exactly, without trailing zero fraction."""
    per = {"s": NS, "ms": 1_000_000, "us": 1_000, "ns": 1}[unit]
    q, r = divmod(t_ns, per)
    if r == 0:
        return str(q)
    width = len(str(per)) - 1
    return f"{q}.{r:0{width}d}".rstrip("0")


def file_bytes(f: dict) -> bytes:
    """The exact bytes a scene file is written with (gzip with mtime 0 when f['gzip'])."""
    data = f["text"].encode("utf-8")
    return gzip.compress(data, mtime=0) if f.get("gzip") else data


def sha256_of(f: dict) -> str:
    return hashlib.sha256(file_bytes(f)).hexdigest()


def csv_text(header, rows, delim=",") -> str:
    lines = [delim.join(header)] if header else []
    lines += [delim.join(str(c) for c in r) for r in rows]
    return "\n".join(lines) + "\n"


def trade(t, px, qty, side, id_):
    return {"t_ns": t, "px": float(px), "qty": float(qty), "side": side, "id": str(id_)}


def bar(start, o, h, l, c, v):
    return {"start_ns": start, "open": float(o), "high": float(h), "low": float(l), "close": float(c), "volume": float(v)}


# --------------------------------------------------------------------------- specs
def spec_bitflyer_rest():
    return {"format": "csv", "header": True, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto",
            "time": {"columns": ["exec_date"], "unit": "iso", "tz": "UTC"},
            "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"},
            "side_map": {"BUY": "buy", "SELL": "sell", "": ""}, "key": "id"}


def spec_bitflyer_us():
    s = spec_bitflyer_rest()
    s["time"] = {"columns": ["ts_us"], "unit": "us", "tz": "UTC"}
    s["compression"] = "gzip"
    return s


BINANCE_NAMES = ["agg_id", "price", "qty", "first_id", "last_id", "transact_time", "is_buyer_maker", "is_best_match"]


def spec_binance():
    return {"format": "csv", "header": False, "names": BINANCE_NAMES, "delimiter": ",", "kind": "trade",
            "symbol": "BTCUSDT", "asset": "crypto",
            "time": {"columns": ["transact_time"], "unit": "ms", "tz": "UTC"},
            "fields": {"id": "agg_id", "px": "price", "qty": "qty", "side": "is_buyer_maker"},
            "side_map": {"True": "sell", "False": "buy"}, "key": "id"}


def spec_fx():
    return {"format": "csv", "header": True, "delimiter": ",", "kind": "quote", "symbol": "USDJPY", "asset": "fx",
            "time": {"columns": ["ts_utc"], "unit": "iso", "tz": "UTC"},
            "fields": {"bid": "bid", "ask": "ask", "bid_qty": "bidvol", "ask_qty": "askvol"}}


def spec_jpx_1m():
    return {"format": "csv", "header": True, "delimiter": ",", "kind": "bar", "symbol": "N225F", "asset": "jpx",
            "time": {"columns": ["date", "time"], "join": " ", "unit": "iso", "tz": "Asia/Tokyo"},
            "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
            "bar": {"interval_s": 60, "label": "start"}, "key": "start"}


def spec_candles(tz="UTC"):
    return {"format": "csv", "header": True, "delimiter": ",", "kind": "bar", "symbol": "FX_BTC_JPY", "asset": "crypto",
            "time": {"columns": ["ts"], "unit": "iso", "tz": tz},
            "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
            "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start"}


def spec_simple_trades(unit, column="t"):
    return {"format": "csv", "header": True, "delimiter": ",", "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto",
            "time": {"columns": [column], "unit": unit, "tz": "UTC"},
            "fields": {"id": "id", "px": "price", "qty": "size", "side": "side"},
            "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id"}


# --------------------------------------------------------------------------- V1
def _bf_rest():
    rows = [(2900000001, T0 + 100_000_000, 3, "15000000", "0.01", "BUY"),
            (2900000002, T0 + 250_000_000, 2, "15000005", "0.02", "SELL"),
            (2900000003, T0 + 1 * NS, 0, "15000010", "0.5", ""),
            (2900000004, T0 + 1_999_000_000, 3, "14999995.5", "0.001", "SELL")]
    text = csv_text(["id", "exec_date", "price", "size", "side"],
                    [(i, iso(t, digits=d, suffix=""), p, q, s) for i, t, d, p, q, s in rows])
    path = "backtest_data/bf_exec_synth_20260105/executions_20260105.csv"
    exp = [trade(t, p, q, {"BUY": "buy", "SELL": "sell", "": ""}[s], i) for i, t, _, p, q, s in rows]
    return {"path": path, "text": text}, {"name": "bf_rest", "paths": [path], "spec": spec_bitflyer_rest()}, exp


def _bf_us():
    rows = [("2900000010", T0 + 5 * NS + 100, "BUY", "15000000", "0.01", "rest"),
            ("", T0 + 5 * NS + 500_000, "SELL", "15000001", "0.25", "ws"),
            ("2900000011", T0 + 6 * NS + 999_999_000, "BUY", "15000002.5", "1.5", "rest")]
    # ts_us carries microseconds: the first row's +100 ns is not writable in us, so the written instant is floored
    written = [(i, (t // 1000) * 1000, s, p, q, src) for i, t, s, p, q, src in rows]
    text = csv_text(["id", "ts_us", "side", "price", "size", "source"],
                    [(i, t // 1000, s, p, q, src) for i, t, s, p, q, src in written])
    path = "backtest_data/bf_exec_us_synth_20260105/executions_20260105.csv.gz"
    exp = [trade(t, p, q, s.lower(), i) for i, t, s, p, q, _ in written]
    return {"path": path, "text": text, "gzip": True}, {"name": "bf_us", "paths": [path], "spec": spec_bitflyer_us()}, exp


def _binance():
    rows = [(1001, "96000.10", "0.00100000", 5001, 5001, T0 + 7 * NS + 123_000_000, "True", "True"),
            (1002, "96000.20", "0.25000000", 5002, 5004, T0 + 7 * NS + 124_000_000, "False", "True"),
            (1003, "95999.90", "1.00000000", 5005, 5005, T0 + 8 * NS, "True", "True")]
    text = csv_text(None, [(a, p, q, f, l, t // 1_000_000, m, b) for a, p, q, f, l, t, m, b in rows])
    path = "backtest_data/binance_BTCUSDT_aggTrades_synth/BTCUSDT-aggTrades-2026-01-05.csv"
    exp = [trade(t, p, q, {"True": "sell", "False": "buy"}[m], a) for a, p, q, f, l, t, m, b in rows]
    return {"path": path, "text": text}, {"name": "binance", "paths": [path], "spec": spec_binance()}, exp


def _fx():
    base = ns(2026, 1, 9, 13, 30)  # an NFP-like release minute
    rows = [(base + 123_000_000, "157.123", "157.126", "1.5", "2.25"),
            (base + 1 * NS, "157.120", "157.124", "0.5", "1"),
            (base + 1 * NS + 5_000_000, "157.301", "157.309", "3", "0.75")]
    text = csv_text(["ts_utc", "bid", "ask", "bidvol", "askvol"], [(iso(t, sep=" ", digits=3, suffix=""), b, a, bv, av) for t, b, a, bv, av in rows])
    path = "backtest_data/fx_event_ticks_synth/NFP_20260109.csv"
    exp = [{"t_ns": t, "bid": float(b), "ask": float(a), "bid_qty": float(bv), "ask_qty": float(av)} for t, b, a, bv, av in rows]
    return {"path": path, "text": text}, {"name": "fx", "paths": [path], "spec": spec_fx()}, exp


def _jpx_1m():
    # JST wall clock 08:45, 08:46 (night->day open) and 12:30 -> UTC 23:45 (previous day!), 23:46, 03:30
    rows = [((2026, 1, 5), (8, 45), "38000", "38010", "37990", "38005", "120"),
            ((2026, 1, 5), (8, 46), "38005", "38020", "38000", "38015", "85"),
            ((2026, 1, 5), (12, 30), "38100", "38105", "38080", "38090", "40")]
    text = csv_text(["date", "time", "open", "high", "low", "close", "volume"],
                    [(f"{d[0]:04d}-{d[1]:02d}-{d[2]:02d}", f"{hm[0]:02d}:{hm[1]:02d}", o, h, l, c, v) for d, hm, o, h, l, c, v in rows])
    path = "backtest_data/n225f_synth_20260105/bars_1min.csv"
    exp = [bar(ns(*d, hm[0], hm[1], offset_h=9), o, h, l, c, v) for d, hm, o, h, l, c, v in rows]
    return {"path": path, "text": text}, {"name": "jpx_1m", "paths": [path], "spec": spec_jpx_1m()}, exp


def spec_board_top10():
    f = {"levels": 10}
    for side in ("bid", "ask"):
        f[f"{side}_px"] = [f"{side}_px_{i}" for i in range(1, 11)]
        f[f"{side}_sz"] = [f"{side}_sz_{i}" for i in range(1, 11)]
    return {"format": "csv", "header": True, "delimiter": ",", "kind": "book", "symbol": "FX_BTC_JPY", "asset": "crypto",
            "time": {"columns": ["ts"], "unit": "iso", "tz": "UTC"}, "fields": f, "compression": "gzip"}


def _board():
    # row 1: 10 levels on both sides; row 2: 3 bid levels and 2 ask levels (blank cells beyond, as in the tape's board_top10)
    t1, t2 = T0 + 10 * NS, T0 + 11 * NS
    full_b = [(15000000 - 5 * i, round(0.01 * (i + 1), 2)) for i in range(10)]
    full_a = [(15000010 + 5 * i, round(0.02 * (i + 1), 2)) for i in range(10)]
    part_b = [(15000000, 0.5), (14999990, 1.25), (14999900, 2)]
    part_a = [(15000020, 0.75), (15000100, 3)]

    def row(t, b, a):
        cells = [iso(t, sep=" ", digits=0, suffix="+00:00")]
        pad = lambda lv, k: [str(lv[i][k]) if i < len(lv) else "" for i in range(10)]  # noqa: E731
        return cells + pad(b, 0) + pad(b, 1) + pad(a, 0) + pad(a, 1)

    header = ["ts"] + [f"bid_px_{i}" for i in range(1, 11)] + [f"bid_sz_{i}" for i in range(1, 11)] + \
             [f"ask_px_{i}" for i in range(1, 11)] + [f"ask_sz_{i}" for i in range(1, 11)]
    text = csv_text(header, [row(t1, full_b, full_a), row(t2, part_b, part_a)])
    path = "backtest_data/bf_board_synth_20260105/board_top10_20260105.csv.gz"
    rec = lambda t, b, a: {"t_ns": t, "bids": [[float(p), float(q)] for p, q in b], "asks": [[float(p), float(q)] for p, q in a]}  # noqa: E731
    return ({"path": path, "text": text, "gzip": True}, {"name": "board", "paths": [path], "spec": spec_board_top10()},
            [rec(t1, full_b, full_a), rec(t2, part_b, part_a)])


def _funding():
    rows = [(ns(2026, 1, 5, 4), ns(2026, 1, 5, 12), "0.0001"), (ns(2026, 1, 5, 12), ns(2026, 1, 5, 20), "-0.00005")]
    text = csv_text(["calculation_date", "settlement_date", "rate"],
                    [(iso(c, digits=0, suffix=""), iso(st, digits=0, suffix=""), r) for c, st, r in rows])
    path = "backtest_data/funding_synth/funding_rate_history.csv"
    spec = {"format": "csv", "header": True, "delimiter": ",", "kind": "funding", "symbol": "FX_BTC_JPY", "asset": "crypto",
            "time": {"columns": ["settlement_date"], "unit": "iso", "tz": "UTC"}, "fields": {"rate": "rate"}}
    return {"path": path, "text": text}, {"name": "funding", "paths": [path], "spec": spec}, [{"t_ns": st, "rate": float(r)} for _, st, r in rows]


def _liquidations():
    import json as _json
    msgs = [(T0 + 12 * NS + 345_000_000, "SELL", "96000.5", "0.25"), (T0 + 13 * NS, "BUY", "96010", "1.5")]
    lines = [_json.dumps({"venue": "binance_um", "recv_us": (t + 50_000_000) // 1000,
                          "raw": {"e": "forceOrder", "o": {"s": "BTCUSDT", "S": sd, "p": p, "q": q, "T": t // 1_000_000}}},
                         separators=(",", ":")) for t, sd, p, q in msgs]
    path = "backtest_data/liquidations_synth/liquidations_20260105.jsonl.gz"
    spec = {"format": "jsonl", "compression": "gzip", "kind": "liquidation", "symbol": "BTCUSDT", "asset": "crypto",
            "time": {"columns": ["raw.o.T"], "unit": "ms", "tz": "UTC"},
            "fields": {"px": "raw.o.p", "qty": "raw.o.q", "side": "raw.o.S"}, "side_map": {"SELL": "sell", "BUY": "buy"}}
    return ({"path": path, "text": "\n".join(lines) + "\n", "gzip": True}, {"name": "liquidations", "paths": [path], "spec": spec},
            [{"t_ns": t, "px": float(p), "qty": float(q), "side": sd.lower()} for t, sd, p, q in msgs])


def _funding_and_liquidations():
    return [_funding(), _liquidations()]


FIXED_V1 = [_bf_rest, _bf_us, _binance, _fx, _jpx_1m, _board, _funding, _liquidations]


def _generic(seed: int, n: int):
    """A trade file whose shape is drawn from `seed`: column names, order, delimiter, header, time unit."""
    rng = random.Random(seed)
    unit = ["s", "ms", "us", "ns", "iso"][n % 5]
    delim = [",", ";", "\t", "|"][rng.randrange(4)]
    header = rng.random() < 0.5
    names = {k: f"c{rng.randrange(10**6):06d}_{k[0]}" for k in ("id", "time", "px", "qty", "side")}
    order = list(names)
    rng.shuffle(order)
    rows = []
    t = T0 + rng.randrange(0, 3600) * NS
    for i in range(4):
        t += rng.randrange(1, 5) * NS + (rng.randrange(0, 1000) * 1_000_000 if unit != "s" else 0)
        rows.append({"id": str(700000 + seed % 1000 * 10 + i), "time": t, "px": f"{rng.randrange(14_000_000, 16_000_000)}",
                     "qty": f"{rng.randrange(1, 400) / 100:.2f}", "side": rng.choice(["BUY", "SELL"])})

    def cell(r, k):
        if k != "time":
            return r[k]
        return iso(r["time"], digits=3) if unit == "iso" else dec(r["time"], unit)

    text = csv_text([names[k] for k in order] if header else None, [[cell(r, k) for k in order] for r in rows], delim)
    path = f"backtest_data/generic_synth_{seed}/trades.txt"
    spec = {"format": "csv", "header": header, "delimiter": delim, "kind": "trade", "symbol": "FX_BTC_JPY", "asset": "crypto",
            "time": {"columns": [names["time"]], "unit": unit, "tz": "UTC"},
            "fields": {"id": names["id"], "px": names["px"], "qty": names["qty"], "side": names["side"]},
            "side_map": {"BUY": "buy", "SELL": "sell"}, "key": "id"}
    if not header:
        spec["names"] = [names[k] for k in order]
    exp = [trade(r["time"], r["px"], r["qty"], r["side"].lower(), r["id"]) for r in rows]
    return {"path": path, "text": text}, {"name": f"generic_{seed}", "paths": [path], "spec": spec}, exp


def _load_scene(sid, vp, kind, what, how, parts, extra_expect=None, want=("events",)):
    files, dss, exp = [], [], {}
    for f, ds, e in parts:
        files.append(f)
        dss.append(ds)
        exp[ds["name"]] = e
    expect = {"events": exp}
    if extra_expect:
        expect.update(extra_expect)
    return {"id": sid, "viewpoint": vp, "kind": kind, "what": what, "how": how,
            "input": {"op": "load", "files": files, "datasets": dss, "want": list(want)}, "expect": expect}


HOW_WRITE = ("合成の行を先に決め、その時刻(UTC の暦から整数の計算で出したナノ秒)と値を、spec の単位・形で"
             "ファイルに書いた。正解は書く前に決めた値そのもの(書き方を正しく逆にたどれば必ずそれになる)。")


def scenes_v1():
    out = []
    for fn, sid, what in [
        (_bf_rest, "v1-bitflyer-rest", "bitFlyer の約定(REST の形: id,exec_date(Z なしの ISO、UTC),price,size,side。side が空の行を含む)を約定の事象にできるか"),
        (_bf_us, "v1-bitflyer-us-gz", "bitFlyer の約定(統合版の形: id,ts_us(マイクロ秒),side,price,size,source、gzip、id が空の行を含む)を約定の事象にできるか"),
        (_binance, "v1-binance-aggtrades", "Binance aggTrades(見出しなし 8 列、ミリ秒、is_buyer_maker から攻め側の売買)を約定の事象にできるか"),
        (_fx, "v1-fx-ticks", "FX のイベントティック(ts_utc,bid,ask,bidvol,askvol、空白区切りの ISO)を気配の事象にできるか"),
        (_jpx_1m, "v1-jpx-1m", "JPX の 1 分足(date,time の 2 列、日本時間。朝 8:45 は UTC で前日)を足の事象にできるか"),
        (_board, "v1-bitflyer-board-top10", "bitFlyer の板の上位 10 段(ts と bid_px_1..10・bid_sz_1..10・ask_px_1..10・ask_sz_1..10、gzip。段が足りない行は空欄)を板の写真の事象にできるか(空欄の段を 0 や欠けた値にしない)"),
    ]:
        out.append(_load_scene(sid, "V1", "値", what, HOW_WRITE, [fn()]))
    out.append(_load_scene(
        "v1-funding-and-liquidations", "V1", "値",
        "資金調達の率(CSV、settlement_date の時刻)と清算の通知(JSON の 1 行 1 通、gzip、欄は入れ子の raw.o.T・raw.o.p・raw.o.q・raw.o.S)を、それぞれ資金調達と清算の事象にできるか(入れ子の欄を宣言で指せるか)",
        HOW_WRITE, _funding_and_liquidations()))
    out.append(_load_scene(
        "v1-all-assets-one-call", "V1", "能力",
        "上の 8 つ(暗号資産の約定 3 形・板の上位 10 段・資金調達・清算・FX の気配・JPX の足)を 1 回の読み込みの呼び出しで渡し、全部を共通の事象の形で返せるか(資産ごとの別の読み口を使わない)",
        HOW_WRITE + " 8 つの正解は上の場面と同じ。", [fn() for fn in FIXED_V1]))
    out.append(_load_scene(
        "v1-generic-shape", "V1", "能力",
        "種(20260925 から 3 つ)で列の名前・並び・区切り文字(, ; タブ |)・見出しの有無・時刻の単位(s/ms/us/ns/iso)を引いた 3 つのファイルを、宣言(spec)だけで読めるか(形ごとの専用の読み口を書かずに読めること)",
        HOW_WRITE + " 形は種から決まり、2 回の実行で同じ。", [_generic(20260925 + k, k) for k in range(3)] + [_generic(20260928 + k, k + 3) for k in range(2)]))
    return out


# --------------------------------------------------------------------------- V2
def scenes_v2():
    out = []
    inst = [T0, T0 + 500_000_000, T0 + 123_456_789, T0 + 86_399 * NS + 999_999_999]
    parts = []
    for unit in ("s", "ms", "us", "ns"):
        path = f"backtest_data/units_synth/{unit}.csv"
        text = csv_text(["id", "t", "price", "size", "side"], [(k + 1, dec(t, unit), "100", "1", "BUY") for k, t in enumerate(inst)])
        parts.append(({"path": path, "text": text}, {"name": f"u_{unit}", "paths": [path], "spec": spec_simple_trades(unit)},
                      [{"t_ns": t} for t in inst]))
    path = "backtest_data/units_synth/iso.csv"
    text = csv_text(["id", "t", "price", "size", "side"], [(k + 1, iso(t), "100", "1", "BUY") for k, t in enumerate(inst)])
    parts.append(({"path": path, "text": text}, {"name": "u_iso", "paths": [path], "spec": spec_simple_trades("iso")},
                  [{"t_ns": t} for t in inst]))
    out.append(_load_scene(
        "v2-same-instant-4-units", "V2", "値",
        "同じ 4 つの瞬間(小数部 0 / 0.5 秒 / 0.123456789 秒 / 23:59:59.999999999)を秒・ミリ・マイクロ・ナノの 10 進(小数部つき)と ISO(9 桁、Z)で書いた 5 ファイルが、全部同じ UTC の int64 ナノ秒になるか(浮動小数に落として桁を失わないか)",
        HOW_WRITE + " 10 進の文字列は瞬間を単位で割った商と余りから正確に書いた(丸めなし)。", parts, want=("times",)))

    one = T0 + 1_500_000_000
    forms = [iso(one, digits=1), iso(one, offset_h=9, digits=1, suffix="+09:00"), iso(one, sep=" ", digits=3, suffix="+00:00"),
             iso(one, offset_h=-5, digits=6, suffix="-05:00"), iso(one, digits=9), iso(one, offset_h=5, digits=3, suffix="+0500")]
    path = "backtest_data/iso_forms_synth/trades.csv"
    text = csv_text(["id", "t", "price", "size", "side"], [(k + 1, f, "100", "1", "SELL") for k, f in enumerate(forms)])
    out.append(_load_scene(
        "v2-iso-offsets", "V2", "値",
        "同じ瞬間を 6 通りの ISO(Z / +09:00 / 空白区切り +00:00 / -05:00 / 9 桁 Z / コロンなし +0500)で書いた行が、全部同じナノ秒になるか",
        HOW_WRITE + " 各行は同じ瞬間を、その行の時差の壁時計で書いた。",
        [({"path": path, "text": text}, {"name": "iso_forms", "paths": [path], "spec": spec_simple_trades("iso")}, [{"t_ns": one}] * len(forms))], want=("times",)))

    # naive local wall clock, declared Asia/Tokyo, across the UTC day boundary
    loc = [ns(2026, 1, 5, 8, 59, 59, offset_h=9), ns(2026, 1, 5, 9, 0, 0, offset_h=9), ns(2026, 1, 5, 0, 0, 0, 250_000_000, offset_h=9)]
    path1 = "backtest_data/local_synth/trades_jst.csv"
    s1 = spec_simple_trades("iso")
    s1["time"]["tz"] = "Asia/Tokyo"
    text1 = csv_text(["id", "t", "price", "size", "side"], [(k + 1, iso(t, offset_h=9, digits=3, sep=" ", suffix=""), "100", "1", "BUY") for k, t in enumerate(loc)])
    path2 = "backtest_data/local_synth/bars_jst.csv"
    rows2 = [((2026, 1, 5), (8, 59)), ((2026, 1, 5), (9, 0)), ((2026, 1, 6), (0, 0))]
    text2 = csv_text(["date", "time", "open", "high", "low", "close", "volume"],
                     [(f"{d[0]:04d}-{d[1]:02d}-{d[2]:02d}", f"{h:02d}:{m:02d}", 10, 10, 10, 10, 1) for d, (h, m) in rows2])
    out.append(_load_scene(
        "v2-naive-local-tz", "V2", "値",
        "オフセットの無い壁時計の時刻を、spec が宣言した Asia/Tokyo で UTC に直せるか(1 つ目は 1 列の ISO、2 つ目は date と time の 2 列。どちらも UTC の日付の境をまたぐ)",
        HOW_WRITE + " 正解は壁時計から 9 時間を引いた UTC。",
        [({"path": path1, "text": text1}, {"name": "jst_trades", "paths": [path1], "spec": s1}, [{"t_ns": t} for t in loc]),
         ({"path": path2, "text": text2}, {"name": "jst_bars", "paths": [path2], "spec": spec_jpx_1m()},
          [{"start_ns": ns(*d, h, m, offset_h=9)} for d, (h, m) in rows2])], want=("times",)))
    return out


# --------------------------------------------------------------------------- V3
def _trade_rows_text(rows):
    return csv_text(["id", "t", "price", "size", "side"], [(i, iso(t, digits=3), p, q, s) for i, t, p, q, s in rows])


def scenes_v3():
    out = []
    t = [T0 + k * NS for k in range(8)]
    clean = [(1, t[0], "100", "1", "BUY"), (2, t[1], "101", "1", "SELL"), (3, t[1], "102", "2", "BUY"), (4, t[2], "103", "1", "BUY"), (5, t[3], "104", "1", "SELL")]
    path = "backtest_data/v3_synth/clean.csv"
    out.append({"id": "v3-clean-control", "viewpoint": "V3", "kind": "値",
                "what": "異常の無いファイル(同じ時刻に id の違う 2 件を含む)で、異常を 0 件と返し、事象を全部返すか(何でも異常と言う対象を通さないための対照)",
                "how": HOW_WRITE + " 異常の正解は空。",
                "input": {"op": "load", "files": [{"path": path, "text": _trade_rows_text(clean)}],
                          "datasets": [{"name": "clean", "paths": [path], "spec": spec_simple_trades("iso")}], "want": ["events", "anomalies"]},
                "expect": {"events": {"clean": [{"t_ns": r[1], "id": str(r[0])} for r in clean]}, "anomalies": {"clean": []}}})

    dup = [(1, t[0], "100", "1", "BUY"), (2, t[1], "101", "1", "SELL"), (3, t[1], "102", "2", "BUY"),
           (2, t[1], "101", "1", "SELL"),   # same id, same values -> duplicate
           (4, t[2], "103", "1", "BUY"),
           (4, t[2], "103.5", "1", "BUY"),  # same id, different price -> conflict
           (5, t[3], "104", "1", "SELL")]
    path = "backtest_data/v3_synth/dup.csv"
    out.append({"id": "v3-duplicate-and-conflict", "viewpoint": "V3", "kind": "値",
                "what": "同じ id の同じ行(重複)と、同じ id で値の違う行(食い違い)を仕込み、重複 1 件・食い違い 1 件を時刻つきで返すか(同じ時刻で id の違う正当な 2 件は異常にしない)",
                "how": "仕込んだ行を定義(キー = spec の key。同じキーで全列が同じ = duplicate、同じキーで値が違う = conflict)に当てて数えた。",
                "input": {"op": "load", "files": [{"path": path, "text": _trade_rows_text(dup)}],
                          "datasets": [{"name": "dup", "paths": [path], "spec": spec_simple_trades("iso")}], "want": ["anomalies"]},
                "expect": {"anomalies": {"dup": [{"kind": "duplicate", "t_ns": t[1]}, {"kind": "conflict", "t_ns": t[2]}]}}})

    half = NS // 2
    back = [(1, t[0], "100", "1", "BUY"), (2, t[1], "100", "1", "BUY"), (3, t[2], "100", "1", "BUY"),
            (4, t[1] + half, "100", "1", "BUY"),  # backward
            (5, t[3], "100", "1", "BUY"),
            (6, t[2] + half, "100", "1", "BUY"),  # backward (below the running maximum t[3])
            (7, t[4], "100", "1", "BUY")]
    path = "backtest_data/v3_synth/backward.csv"
    out.append({"id": "v3-backward", "viewpoint": "V3", "kind": "値",
                "what": "時刻が前の行より戻る行を 2 つ(2 つ目は直前の行より後だが、それまでの最大より前)仕込み、逆行 2 件を時刻つきで返すか",
                "how": "逆行の定義 = その行の時刻 < それより前の行の時刻の最大。仕込んだ 2 行が当たる。",
                "input": {"op": "load", "files": [{"path": path, "text": _trade_rows_text(back)}],
                          "datasets": [{"name": "back", "paths": [path], "spec": spec_simple_trades("iso")}], "want": ["anomalies"]},
                "expect": {"anomalies": {"back": [{"kind": "backward", "t_ns": t[1] + half}, {"kind": "backward", "t_ns": t[2] + half}]}}})

    m = [T0 + k * 60 * NS for k in range(10)]
    present = [0, 1, 2, 5, 6, 8, 9]
    path = "backtest_data/candles_synth/candles_gap.csv"
    text = csv_text(["ts", "open", "high", "low", "close", "volume"], [(iso(m[k], sep=" ", digits=0, suffix="+00:00"), 100, 101, 99, 100, 1) for k in present])
    out.append({"id": "v3-gap-bars", "viewpoint": "V3", "kind": "値",
                "what": "24 時間取引の 1 分足で 3 本(2 本続き + 1 本)が欠けたファイルで、欠落 3 件を欠けた足の始まりの時刻つきで返すか",
                "how": "欠落の定義 = 最初の足から最後の足までの足の間隔(60 秒)の格子で、行の無い始まりの時刻 1 つにつき 1 件(24x7 なので休場は無い)。",
                "input": {"op": "load", "files": [{"path": path, "text": text}],
                          "datasets": [{"name": "gap", "paths": [path], "spec": spec_candles()}], "want": ["anomalies"]},
                "expect": {"anomalies": {"gap": [{"kind": "gap", "t_ns": m[k]} for k in (3, 4, 7)]}}})

    g1 = [(k, 100 + k) for k in range(0, 6)]
    g2 = [(k, 100 + k if k != 5 else 999) for k in range(4, 10)]
    p1, p2 = "backtest_data/candles_synth_gen1/candles.csv", "backtest_data/candles_synth_gen2/candles.csv"
    tx = lambda rows: csv_text(["ts", "open", "high", "low", "close", "volume"], [(iso(m[k], sep=" ", digits=0, suffix="+00:00"), c, c, c, c, 1) for k, c in rows])  # noqa: E731
    out.append({"id": "v3-generations", "viewpoint": "V3", "kind": "値",
                "what": "同じデータの 2 つの世代(分 0〜5 と 分 4〜9)を 1 つのデータとして読ませ、重なりの分 4(同じ値 = 重複)と分 5(値が違う = 食い違い)を返すか(黙ってどちらかを採って結合しない)",
                "how": "重複と食い違いの定義(キー = 足の始まり)を、2 つのファイルの重なり 2 本に当てた。",
                "input": {"op": "load", "files": [{"path": p1, "text": tx(g1)}, {"path": p2, "text": tx(g2)}],
                          "datasets": [{"name": "gens", "paths": [p1, p2], "spec": spec_candles()}], "want": ["anomalies"]},
                "expect": {"anomalies": {"gens": [{"kind": "duplicate", "t_ns": m[4]}, {"kind": "conflict", "t_ns": m[5]}]}}})
    return out


# --------------------------------------------------------------------------- V4
def scenes_v4():
    fa, dsa, ea = _bf_rest()
    fb, dsb, eb = _bf_us()
    same = dict(fa, path="backtest_data/bf_exec_synth_copy/executions_20260105.csv")
    oneb = dict(fa, path="backtest_data/bf_exec_synth_edit/executions_20260105.csv", text=fa["text"].replace("15000005", "15000006"))
    assert oneb["text"] != fa["text"] and len(oneb["text"]) == len(fa["text"])
    s1 = {"id": "v4-sha256-values", "viewpoint": "V4", "kind": "値",
          "what": "読んだファイルごとの sha256(平文と gzip の 2 本。ディスクに置かれたバイト列のまま)を、実行の記録として返すか",
          "how": "書いたバイト列そのものに hashlib.sha256 を当てた(gzip は mtime 0 で圧縮したバイト列)。",
          "input": {"op": "load", "files": [fa, fb], "datasets": [dsa, dsb], "want": ["times", "hashes"]},
          "expect": {"events": {"bf_rest": [{"t_ns": r["t_ns"]} for r in ea], "bf_us": [{"t_ns": r["t_ns"]} for r in eb]},
                     "hashes": "__computed__"}}
    dsc = {"name": "copy", "paths": [same["path"]], "spec": spec_bitflyer_rest()}
    dsd = {"name": "edit", "paths": [oneb["path"]], "spec": spec_bitflyer_rest()}
    s2 = {"id": "v4-sha256-distinguishes", "viewpoint": "V4", "kind": "能力",
          "what": "中身が同じで場所の違うファイルに同じ sha256、1 バイトだけ違うファイルに違う sha256 を記録するか",
          "how": "3 本のバイト列に hashlib.sha256 を当てた(元と写しは同じ値、1 バイト違いは違う値になる)。",
          "input": {"op": "load", "files": [fa, same, oneb], "datasets": [dsa, dsc, dsd], "want": ["hashes"]},
          "expect": {"hashes": "__computed__"}}
    return [s1, s2]


# --------------------------------------------------------------------------- V5
def _v5(sid, what, control_path, variant_path, extra_files=(), how_extra="", variant_via_link=False):
    f, ds, exp = _bf_rest()
    fc = dict(f, path=control_path)
    fv = dict(f, path=variant_path)
    dsc = dict(ds, paths=[control_path])
    dsv = dict(ds, paths=[variant_path])
    return {"id": sid, "viewpoint": "V5", "kind": "能力", "what": what,
            "how": "対照 = 許されるパスに置いた同じ中身(正解は V1 の bitflyer-rest と同じ事象)。変形 = 拒むべきパス。正解 = 対照を正しく読み、変形を拒む。" + how_extra,
            "input": {"op": "load", "files": [fc, *extra_files], "datasets": [dsc], "want": ["events"]},
            "variant": {"op": "load", "files": ([] if variant_via_link else [fv]) + list(extra_files), "datasets": [dsv], "want": ["events"]},
            "expect": {"events": {ds["name"]: [{"t_ns": r["t_ns"], "px": r["px"]} for r in exp]}}}


def _sealed_scene():
    rows = [(k + 1, T0 + k * 3600 * NS, str(100 + k), "1", "BUY") for k in range(10)]
    data_path = "backtest_data/bf_exec_sealtest_20260105/trades.csv"
    cutoff = rows[7][1]
    seal = {"unit": "SYNTH-UNIT", "sealed_at": iso(T0 + 30 * 86400 * NS, digits=0, suffix="+00:00"),
            "forward_start": iso(T0 + 30 * 86400 * NS, digits=0, suffix="+00:00"),
            "files": [{"path": data_path, "time_column": "t", "seal_from_ts": iso(cutoff, digits=0, suffix="+00:00")}]}
    import json as _json
    seal_file = {"path": "backtest_data/phase2_sealed/SYNTH-UNIT/SEALED.json", "text": _json.dumps(seal, indent=1)}
    text = _trade_rows_text(rows)
    ds = {"name": "sealtest", "paths": [data_path], "spec": spec_simple_trades("iso")}
    ctrl = dict(ds, range_ns=[rows[0][1], cutoff])
    var = dict(ds, range_ns=[rows[0][1], rows[-1][1] + 1])
    edge = {"id": "v5-seal-boundary", "viewpoint": "V5", "kind": "値",
            "what": "封印の境ちょうどの扱い: 範囲 [境の 1 時間前, 境) は境の直前の 1 行だけを返し、終わりを境の 1 ns 後にした範囲(境ちょうどの行 = 封印区間の最初の行を含む)は拒むか",
            "how": "範囲は [始まり, 終わり) の半開区間、封印区間は seal_from_ts 以後(sealed.py の load_unsealed と同じ d < cutoff)。境の 1 時間前の行は範囲の中、境ちょうどの行は封印区間。",
            "input": {"op": "load", "files": [{"path": data_path, "text": text}, seal_file], "datasets": [dict(ds, range_ns=[cutoff - 3600 * NS, cutoff])], "want": ["events"]},
            "variant": {"op": "load", "files": [{"path": data_path, "text": text}, seal_file], "datasets": [dict(ds, range_ns=[cutoff - 3600 * NS, cutoff + 1])], "want": ["events"]},
            "expect": {"events": {"sealtest": [{"t_ns": rows[6][1], "px": float(rows[6][2])}]}}}
    return edge, {"id": "v5-sealed-window", "viewpoint": "V5", "kind": "能力",
            "what": "封印の記録(backtest_data/phase2_sealed/<unit>/SEALED.json、load_sealed が守る形)に載ったファイルで、封印の境より前の範囲は読み、境をまたぐ範囲の読み込みを拒むか",
            "how": "対照 = 範囲 [最初の行, seal_from_ts) の 7 行(正解は書いた行そのもの)。変形 = 範囲 [最初の行, 最後の行] = 封印区間の 3 行を含む。正解 = 変形を拒む。",
            "input": {"op": "load", "files": [{"path": data_path, "text": text}, seal_file], "datasets": [ctrl], "want": ["events"]},
            "variant": {"op": "load", "files": [{"path": data_path, "text": text}, seal_file], "datasets": [var], "want": ["events"]},
            "expect": {"events": {"sealtest": [{"t_ns": r[1], "px": float(r[2])} for r in rows[:7]]}}}


def scenes_v5():
    base = "executions_20260105.csv"
    out = [
        _v5("v5-reject-qa", "合成(backtest_data/qa_*)の下のファイルを拒むか", f"backtest_data/bf_exec_synth_20260105/{base}", f"backtest_data/qa_known_answer_synth/{base}"),
        _v5("v5-reject-o3c", "研究の中間物(backtest_data/o3c_*)を拒み、名前に o3c を含むだけの生データ(binance_cm_o3c_*)は読むか",
            f"backtest_data/binance_cm_o3c_synth/{base}", f"backtest_data/o3c_signal_synth/{base}"),
        _v5("v5-reject-phase2-runs", "研究の中間物(backtest_data/phase2_runs/)を拒むか", f"backtest_data/bf_exec_synth_20260105/{base}", f"backtest_data/phase2_runs/unit_synth/{base}"),
        _v5("v5-reject-dotdot", "許されるフォルダから .. で拒むフォルダ(qa_*)へ抜けるパスを拒むか(文字列の頭だけを見ない)",
            f"backtest_data/bf_exec_synth_20260105/{base}", f"backtest_data/bf_exec_synth_20260105/../qa_known_answer_synth/{base}",
            extra_files=[{"path": f"backtest_data/qa_known_answer_synth/{base}", "text": _bf_rest()[0]["text"]}]),
        _v5("v5-reject-symlink", "許される名前のフォルダが拒むフォルダ(qa_*)への symlink のとき、実体で拒むか",
            f"backtest_data/bf_exec_synth_20260105/{base}", f"backtest_data/bf_exec_link_synth/{base}",
            extra_files=[{"path": f"backtest_data/qa_known_answer_synth/{base}", "text": _bf_rest()[0]["text"]},
                         {"path": "backtest_data/bf_exec_link_synth", "symlink_to": "qa_known_answer_synth"}],
            variant_via_link=True),
        *_sealed_scene(),
    ]
    # in the dotdot/symlink scenes the forbidden file itself also exists, so a refusal must come from the path rule
    return out


# --------------------------------------------------------------------------- V6
def _d(day):
    return f"2026-01-{day:02d}"


def _daily(code, day, o, h, l, c, v):
    return {"code": code, "date": _d(day), "open": o, "high": h, "low": l, "close": c, "volume": v}


def _adj(r, pf, vf):
    return {"date": r["date"], "open": float(Fraction(r["open"]) * pf), "high": float(Fraction(r["high"]) * pf),
            "low": float(Fraction(r["low"]) * pf), "close": float(Fraction(r["close"]) * pf), "volume": float(Fraction(r["volume"]) * vf)}


def scenes_v6():
    out = []
    days = [5, 6, 7, 8, 9]
    pre = [_daily("1001", d, 1000 + 10 * k, 1020 + 10 * k, 980 + 10 * k, 1000 + 10 * k, 3000 + 100 * k) for k, d in enumerate(days[:3])]
    post = [_daily("1001", d, 510 + 2 * k, 520 + 2 * k, 500 + 2 * k, 512 + 2 * k, 7000 + 100 * k) for k, d in enumerate(days[3:])]
    listings = [{"code": "1001", "listed": "2000-01-04", "delisted": None}]
    split = {"code": "1001", "type": "split", "ex_date": _d(8), "ratio": 2}
    HOW = "後ろ向きの調整の定義(ex_date より前の足の値段 × 1/r、出来高 × r。as_of より後の ex_date は当てない、as_of より後の足は返さない)を分数で計算した(値段と出来高は割り切れる数に選んだ)。"
    out.append({"id": "v6-split", "viewpoint": "V6", "kind": "値",
                "what": "1:2 の株式分割(ex_date 1/8)を、それより前の足の値段 ÷2・出来高 ×2 に調整して返すか",
                "how": HOW, "input": {"op": "jpx", "bars": pre + post, "actions": [split], "listings": listings, "as_of": _d(9), "universe_dates": []},
                "expect": {"adjusted": {"1001": [_adj(r, Fraction(1, 2), 2) for r in pre] + [_adj(r, 1, 1) for r in post]}}})
    cons_pre = [_daily("1006", d, 200 + 2 * k, 204 + 2 * k, 198 + 2 * k, 202 + 2 * k, 50000 + 500 * k) for k, d in enumerate(days[:2])]
    cons_post = [_daily("1006", d, 1010 + 5 * k, 1025 + 5 * k, 1000 + 5 * k, 1015 + 5 * k, 10100 + 100 * k) for k, d in enumerate(days[2:])]
    out.append({"id": "v6-reverse-split", "viewpoint": "V6", "kind": "値",
                "what": "5 株を 1 株にする株式併合(ex_date 1/7)を、それより前の足の値段 ×5・出来高 ÷5 に調整して返すか",
                "how": HOW, "input": {"op": "jpx", "bars": cons_pre + cons_post,
                                      "actions": [{"code": "1006", "type": "reverse_split", "ex_date": _d(7), "ratio": 5}],
                                      "listings": [{"code": "1006", "listed": "2000-01-04", "delisted": None}], "as_of": _d(9), "universe_dates": []},
                "expect": {"adjusted": {"1006": [_adj(r, 5, Fraction(1, 5)) for r in cons_pre] + [_adj(r, 1, 1) for r in cons_post]}}})
    out.append({"id": "v6-point-in-time", "viewpoint": "V6", "kind": "値",
                "what": "同じ分割のデータを as_of = 1/7(ex_date の前)で読ませたとき、まだ起きていない分割で過去を調整せず(先読みしない)、1/7 までの足だけを返すか",
                "how": HOW, "input": {"op": "jpx", "bars": pre + post, "actions": [split], "listings": listings, "as_of": _d(7), "universe_dates": []},
                "expect": {"adjusted": {"1001": [_adj(r, 1, 1) for r in pre]}}})
    cc_old = [_daily("1002", d, 300, 303, 297, 300 + k, 1000) for k, d in enumerate(days[:3])]
    cc_new = [_daily("1003", d, 305, 309, 301, 305 + k, 1100) for k, d in enumerate(days[3:])]
    out.append({"id": "v6-code-change", "viewpoint": "V6", "kind": "値",
                "what": "銘柄コードの変更(1002 → 1003、1/8 から)で、as_of 1/9 の 1003 の系列に変更前の 1002 の足をつないで返し、1002 を別の銘柄として残さないか。日付ごとの銘柄集合も 1/7 は 1002、1/8 は 1003 に切り替わるか",
                "how": "定義: コード変更は同じ銘柄の名前の付け替え。as_of の時点のコードの下に、それ以前の全部の足(調整なし)を並べる。銘柄集合はex_date より前は古いコード、ex_date 以後は新しいコード。",
                "input": {"op": "jpx", "bars": cc_old + cc_new, "actions": [{"code": "1002", "type": "code_change", "ex_date": _d(8), "new_code": "1003"}],
                          "listings": [{"code": "1002", "listed": "2000-01-04", "delisted": None}], "as_of": _d(9), "universe_dates": [_d(7), _d(8)]},
                "expect": {"adjusted": {"1003": [_adj(r, 1, 1) for r in cc_old + cc_new]}, "universe": {_d(7): ["1002"], _d(8): ["1003"]}}})
    lst = [{"code": "1001", "listed": "2000-01-04", "delisted": None},
           {"code": "1004", "listed": _d(6), "delisted": None},
           {"code": "1005", "listed": "2010-06-01", "delisted": _d(8)}]
    out.append({"id": "v6-universe-survivorship", "viewpoint": "V6", "kind": "能力",
                "what": "日付ごとの銘柄集合を、その日に上場していた銘柄で返すか(後で上場廃止になる 1005 を過去の日から落とさない = 生存者の偏りを避ける、後で上場する 1004 を前の日に入れない)",
                "how": "定義: 日付 d に上場 ⇔ listed ≤ d < delisted(delisted 無しは無限)。4 日について定義どおりに並べた。",
                "input": {"op": "jpx", "bars": [], "actions": [], "listings": lst, "as_of": _d(9), "universe_dates": [_d(5), _d(6), _d(7), _d(8)]},
                "expect": {"universe": {_d(5): ["1001", "1005"], _d(6): ["1001", "1004", "1005"],
                                        _d(7): ["1001", "1004", "1005"], _d(8): ["1001", "1004"]}}})
    return out


# --------------------------------------------------------------------------- V7
def _bars_from_trades_def(trades, interval_ns):
    """The definition, spelled out: [start, start+interval) buckets, first/max/min/last price, summed qty; no bar for an empty bucket."""
    out = {}
    for tr in trades:
        st = tr["t_ns"] // interval_ns * interval_ns
        b = out.get(st)
        if b is None:
            out[st] = b = {"start_ns": st, "open": tr["px"], "high": tr["px"], "low": tr["px"], "close": tr["px"], "volume": Fraction(0)}
        b["high"] = max(b["high"], tr["px"])
        b["low"] = min(b["low"], tr["px"])
        b["close"] = tr["px"]
        b["volume"] += Fraction(tr["qty"])
    return [dict(b, open=float(b["open"]), high=float(b["high"]), low=float(b["low"]), close=float(b["close"]), volume=float(b["volume"])) for b in (out[k] for k in sorted(out))]


def _rule_def(closes, n, init):
    """V7 rule, exact: sma_t = mean of the last n closes (None before n bars); position_t = 1 if close_t > sma_t else 0;
    equity_t = init + sum_{s<=t} position_{s-1} * (close_s - close_{s-1})."""
    fc = [Fraction(float(c)) for c in closes]  # the exact values of the floats the target is given
    sma, pos, eq = [], [], []
    e = Fraction(init)
    for t in range(len(fc)):
        m = sum(fc[t - n + 1:t + 1]) / n if t >= n - 1 else None
        sma.append(m)
        if t > 0:
            e += pos[-1] * (fc[t] - fc[t - 1])
        pos.append(1 if (m is not None and fc[t] > m) else 0)
        eq.append(e)
    return {"sma": [None if m is None else float(m) for m in sma], "position": pos, "equity": [float(x) for x in eq]}


def scenes_v7():
    out = []
    iv = 60 * NS
    tr = [(0, 0, 100, "0.5"), (0, 20 * NS, 103, "0.25"), (0, 59 * NS + 999_999_999, 101, "0.125"),
          (1, 0, 102, "1"), (1, 30 * NS, 99, "0.5"),
          (3, 0, 105, "0.25"),
          (4, 10 * NS, 104, "0.5"), (4, 59 * NS + 999_999_999, 106, "0.75")]
    trades = [{"t_ns": T0 + mm * iv + off, "px": float(p), "qty": float(Fraction(q)), "side": "buy", "id": str(k + 1)} for k, (mm, off, p, q) in enumerate(tr)]
    ebars = _bars_from_trades_def(trades, iv)
    out.append({"id": "v7-bars-from-trades", "viewpoint": "V7", "kind": "値",
                "what": "同じ約定から、事象駆動の経路と近道(ベクトル化)の経路の両方で 1 分足を作り、両方が正解と一致し、互いにビット単位で一致するか(足の端ちょうど・端の 1 ns 前・約定の無い分を含む)",
                "how": "定義どおり: 足 = [始まり, 始まり+60 秒)、始値 = 最初、高値 = 最大、安値 = 最小、終値 = 最後、出来高 = 数量の和(2 進で割り切れる数量なので和は正確)、約定の無い分は足を作らない。",
                "input": {"op": "vector_vs_event", "trades": trades, "interval_s": 60, "rule": None, "want": ["bars"]},
                "expect": {"paths": {"bars": ebars}}})
    closes = [100, 103, 106, 101, 99, 104, 108, 107, 103, 110]
    bars = [bar(T0 + k * iv, c, c + 1, c - 1, c, 1) for k, c in enumerate(closes)]
    out.append({"id": "v7-rule-integer", "viewpoint": "V7", "kind": "値",
                "what": "同じ足(終値が整数)に同じ規則(SMA3・終値 > SMA なら次の足を 1 単位の買い持ち・費用なし)を両方の経路で当て、SMA・建玉・資産の推移が正解と一致し、互いにビット単位で一致するか",
                "how": "V7 の規則の定義を分数で計算した(整数の和と 3 での割り算 1 回なので浮動小数でも丸めの順によらない)。",
                "input": {"op": "vector_vs_event", "bars": bars, "interval_s": 60, "rule": {"type": "sma_long_flat", "n": 3, "init_cash": 1_000_000, "unit": 1},
                          "want": ["sma", "position", "equity"]},
                "expect": {"paths": _rule_def(closes, 3, 1_000_000)}})
    # no near-tie: every |close - sma| >= 0.033 on the binary values (checked by the battery's tests)
    fcl = ["100.7", "101.8", "101.7", "100.4", "101.1", "102.9", "101.9", "101.5", "102.0", "101.8"]
    bars_f = [bar(T0 + k * iv, c, c, c, c, 1) for k, c in enumerate(fcl)]
    out.append({"id": "v7-rule-fractional", "viewpoint": "V7", "kind": "値",
                "what": "終値が 10 進の小数(2 進で割り切れない)の足で同じ規則を当て、両方の経路が互いにビット単位で一致し、正解から相対 1e-9 以内か(浮動小数の丸めの順が経路で違えばビットの一致が崩れる)",
                "how": "V7 の規則の定義を、対象に渡す浮動小数(10 進の文字列を float にしたもの)の正確な値を分数にして計算し、最後に浮動小数にした。終値と SMA の差はどの足でも 0.033 以上(際どい比べが無い)。許す差は相対 1e-9(浮動小数の演算の順の違いの分)。経路の間は差を許さない。",
                "tol": 1e-9,
                "input": {"op": "vector_vs_event", "bars": bars_f, "interval_s": 60, "rule": {"type": "sma_long_flat", "n": 3, "init_cash": 1_000_000, "unit": 1},
                          "want": ["sma", "position", "equity"]},
                "expect": {"paths": _rule_def(fcl, 3, 1_000_000)}})
    rng = random.Random(7_2026_0925)
    closes_big, c = [], 15_000_000
    for k in range(20_000):
        c += rng.randrange(-500, 501)
        closes_big.append(c)
    bars_big = [bar(T0 + k * iv, x, x, x, x, 1) for k, x in enumerate(closes_big)]
    out.append({"id": "v7-speed", "viewpoint": "V7", "kind": "能力",
                "what": "2 万本の足(終値は整数)に同じ規則を当てる仕事で、近道の経路が事象駆動の経路より速く(壁時計)、両方の結果が正解と一致し、互いにビット単位で一致するか(近道の意味を成すか)",
                "how": "SMA・建玉・資産の正解は V7 の規則の定義を分数で計算した(終値は種つきの乱数の整数の歩み)。速さは adapter が両経路の呼び出しの前後で測った秒で、近道の秒 < 事象駆動の秒 を正解とする。",
                "input": {"op": "vector_vs_event", "bars": bars_big, "interval_s": 60, "rule": {"type": "sma_long_flat", "n": 3, "init_cash": 100_000_000, "unit": 1},
                          "want": ["sma", "position", "equity", "timing"]},
                "expect": {"paths": _rule_def(closes_big, 3, 100_000_000), "speed": {"keys": ["sma", "position", "equity"]}}})
    return out


# --------------------------------------------------------------------------- all
def _build():
    s = scenes_v1() + scenes_v2() + scenes_v3() + scenes_v4() + scenes_v5() + scenes_v6() + scenes_v7()
    ids = [x["id"] for x in s]
    assert len(ids) == len(set(ids)), "duplicate scene id"
    return s


SCENES = _build()
VIEWPOINTS = {
    "V1": "全資産の読み込み", "V2": "時刻の単位の正規化", "V3": "重複・逆行・欠落・世代間の食い違いの検出",
    "V4": "sha256 の記録", "V5": "合成・中間物・封印区間を拒む許可一覧",
    "V6": "JPX 個別株の分割・併合・上場廃止・コード変更の調整と、生存者の偏りを避ける銘柄集合",
    "V7": "足のベクトル化の近道(同じ足で事象駆動と一致)",
}


def expected(scene: dict) -> dict:
    """The expected answer; `hashes` are computed from the exact bytes the runner writes."""
    exp = dict(scene["expect"])
    if exp.get("hashes") == "__computed__":
        exp["hashes"] = {f["path"]: sha256_of(f) for f in scene["input"]["files"] if "text" in f}
    return exp
