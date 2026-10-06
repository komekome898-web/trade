"""部品 1: Binance BTCUSDT 現物 1 分足の口(カード 8 の門を Binance で確かめる単位、L-714・L-715)。

読む置き場: backtest_data/binance_BTCUSDT_1m_20170801_20231231/ の年ごとの binance_BTCUSDT_1m_<年>.csv.gz だけ。
読む範囲: [2017-08-17T00:00Z, 2023-12-17T15:00Z) の中(終わりがこれより後なら、ファイルを開く前に拒む)。
2024 年以降の置き場(backtest_data/binance_BTCUSDT_1m_20240101_20260831/)へ行く経路は持たない。

読み込みは bitFlyer の口(scripts/w4_measure/common.py の load_bars)と同じく、データ層の 1 つの口
bot.bt.data.loader.load を通す(許された根 AllowList.check と封印の検め SealRegistry.read_checked を、1 バイトでも
使う前に通る)。

足の意味(bitFlyer の口に合わせた所と違う所。報告の 5 にも書く):
  - 時刻: 列 open_time = 1 分の始まり(UTC、ISO)。bitFlyer の ts と同じ「始まり」の印(bar.label = "start")。
    BarEvent の受け取りの時刻 = 始まり + 60 秒(足の終わり)。カードはその時刻に呼ばれる。
  - 取引の無い分: Binance は n_trades = 0・volume = 0 の行を、前の終値で始値・高値・安値・終値を埋めて書く
    (bitFlyer は値段の列を空にして書き、no_trade の宣言で落とす)。ここでは n_trades = "0" の行を synthetic と宣言し、
    方針 drop で落とす(scripts/k1_newenv_g_fold.py の BIN_SPEC と同じ宣言)。落とした後は、bitFlyer と同じく
    「取引の無い分は足が無い」。
  - 行の無い分(ファイルに行が無い分): 異常 gap として数え、方針 accept(bitFlyer の口と同じ BAR_RESOLVE の gap)。
  - 分の頭からずれた行(異常 off_grid、2017・2018 年): 落とす(下の RESOLVE の注)。bitFlyer の口には無い扱い。
  - 値段の単位: 置き場は USDT(0.01 USDT 刻みの小数。bitFlyer は 1 円刻みの JPY)。この口は既定(cents=True)で、
    始値・高値・安値・終値を整数のセント(0.01 USDT を 1 とする整数 = round(値段 × 100)、浮動小数で持つ)にして返す。
    理由(批評家 1 回目の問 1、委任文 fix1 の 1): カード 8 は「終値 = セッションの平均なら持ち高 0」で、平均は終値の和 ÷ 本数。
    値段が整数なら和は正確(2**53 未満のうち)で、平均ちょうどの足は 0 になる(bitFlyer の 1 円単位と同じ扱い)。
    0.01 USDT 刻みの小数のままだと和に丸めが入り、同じ値段が続く足(平らな区間)で持ち高が 0 でなく ±1 になる
    (試験 test_flat_bars_float_vs_cents)。損益の bp は値段の比なので、単位(USDT かセントか)は損益の式を変えない。
    同値の無い足では、持ち高も USDT のままと同じになる(試験 test_unit_does_not_change_exposure_or_pnl)。
    セントにしたときに整数から外れていた値段の数(|値段 × 100 − 丸め| > 1e-6)を事実 n_not_whole_cent に数える
    (0 でなければ 0.01 USDT 刻みでない値段があったということ)。
    bn_split(区分)は cents=False で USDT のまま読む(コミット済みの split/classes.json と同じ入力にするため)。
"""
from __future__ import annotations

import dataclasses
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
W4 = os.path.dirname(HERE)
sys.path.insert(0, W4)

from common import BIN_DIR, BIN_FILE, ROOT, iso, to_iso  # noqa: E402

NS = 1_000_000_000
MIN_NS = 60 * NS
LO = iso("2017-08-17T00:00:00Z")  # 委任文の「2017-08-17〜」。置き場の最初の行は 2017-08-17T04:00Z
HI = iso("2023-12-17T15:00:00Z")  # 委任文の「2023-12-17T15:00:00Z(の前)」。これより後は読まない
SYMBOL = "BTCUSDT"
VENUE = "binance"
# off_grid: 分の頭からずれた行(データ層の読みで確かめた。bitFlyer の置き場には無い異常):
#   2017 年 2017-12-04T06:00:20Z〜2017-12-18T10:00:20Z の 20,401 行(20 秒ずれ)、
#   2018 年 2018-02-09T09:59:14Z〜2018-02-10T05:59:14Z の 1,201 行(14 秒ずれ)。2019 年以降は 0 行。
# そのまま入れると前後の足と時間が重なり run_card が拒むので落とす。落とすと日本時間の 2018-02-09 は足が 0 本になり、
# その日の量 v は無い(2019 年の境は 2018 年の 364 日から)。入れたときとの区分の食い違いは 2019-01-03 の 1 日(報告に書く)。
RESOLVE = {"gap": "accept", "synthetic": "drop", "off_grid": "drop"}
PRICE_SCALE = 100  # 1 USDT = 100 セント(値段の最小の刻み 0.01 USDT を 1 とする)
PRICE_UNIT_CENTS = "0.01 USDT(整数のセント。round(USDT の値段 × 100))"
WHOLE_CENT_TOL = 1e-6


def to_cents(bars) -> tuple:
    """始値・高値・安値・終値を整数のセント(浮動小数で持つ整数)にした BarEvent の並びと、整数から外れていた値段の数。
    量・時刻はそのまま。丸めは単調なので 高値 ≥ 始値・終値 ≥ 安値 の関係は保たれる。"""
    out, n_off = [], 0
    for b in bars:
        kw = {}
        for k in ("open", "high", "low", "close"):
            x = float(getattr(b, k)) * PRICE_SCALE
            r = round(x)
            n_off += abs(x - r) > WHOLE_CENT_TOL
            kw[k] = float(r)
        out.append(dataclasses.replace(b, **kw))
    return tuple(out), n_off


def bar_spec() -> dict:
    return {"format": "csv", "header": True, "delimiter": ",", "compression": "gzip", "kind": "bar",
            "symbol": SYMBOL, "asset": "crypto",
            "time": {"columns": ["open_time"], "unit": "iso", "tz": "UTC"},
            "fields": {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
            "bar": {"interval_s": 60, "label": "start", "session": "24x7"}, "key": "start",
            "synthetic": {"column": "n_trades", "values": ["0"]}}


def check_range(lo_ns: int, hi_ns: int) -> None:
    """読む前の門。範囲が [LO, HI] の外へ出れば、何も開かずに拒む。"""
    if lo_ns >= hi_ns:
        raise SystemExit(f"拒否: 始め {to_iso(lo_ns)} が終わり {to_iso(hi_ns)} 以降")
    if hi_ns > HI:
        raise SystemExit(f"拒否: 終わり {to_iso(hi_ns)} は {to_iso(HI)} より後(この単位で読んでよい終わり)")
    if lo_ns < LO:
        raise SystemExit(f"拒否: 始め {to_iso(lo_ns)} は {to_iso(LO)} より前")


def year_path(y: int) -> str:
    return f"{BIN_DIR}/{BIN_FILE.format(y=y)}"


def year_chunks(lo_ns: int, hi_ns: int) -> list:
    """[lo, hi) を UTC の暦年で切った (年, 始め, 終わり) の並び(ファイルが年ごとなので、1 回の読みは 1 ファイル)。"""
    out = []
    y = datetime.fromtimestamp(lo_ns / 1e9, tz=timezone.utc).year
    while True:
        a = max(lo_ns, int(datetime(y, 1, 1, tzinfo=timezone.utc).timestamp()) * NS)
        b = min(hi_ns, int(datetime(y + 1, 1, 1, tzinfo=timezone.utc).timestamp()) * NS)
        if a >= hi_ns:
            return out
        if a < b:
            out.append((y, a, b))
        y += 1


def load_chunk(lo_ns: int, hi_ns: int, root: str = ROOT, *, check_flags: bool = True, cents: bool = True):
    """[lo, hi) の足(1 つの暦年の中)を読む。戻り: (BarEvent のタプル, 読みの事実 dict)。
    cents=True(既定)なら値段を整数のセントにして返す(docstring の「値段の単位」)。
    事実: ファイル(given・sha256・大きさ・封印の単位)・読んだ行・範囲に残った行・落とした取引の無い分・行の無い分・
    n_trades = 0 と volume = 0 が食い違う行の数・最初と最後の足の始まり・封印の記録の一覧(パスと sha256)・
    値段の単位・整数のセントから外れていた値段の数(cents=True のとき)。"""
    from bot.bt.data.loader import load
    check_range(lo_ns, hi_ns)
    ys = {datetime.fromtimestamp(lo_ns // NS, tz=timezone.utc).year,
          datetime.fromtimestamp((hi_ns - 1) // NS, tz=timezone.utc).year}  # 整数の秒(浮動小数では 1 ns 前が丸めで戻らない)
    if len(ys) != 1:
        raise SystemExit(f"拒否: 1 回の読みは 1 つの暦年の中([{to_iso(lo_ns)}, {to_iso(hi_ns)}))")
    y = ys.pop()
    ds = {"name": "bars", "paths": [year_path(y)], "range_ns": [lo_ns, hi_ns], "spec": bar_spec()}
    res = load(root, [ds])
    an = res.anomalies("bars")
    kinds = {}
    for a in an:
        kinds[a["kind"]] = kinds.get(a["kind"], 0) + 1
    bars = res.events("bars", RESOLVE)
    facts = {"year": y, "range": [to_iso(lo_ns), to_iso(hi_ns)], "anomalies": kinds,
             "n_bars_kept": len(bars), "n_synthetic_dropped": kinds.get("synthetic", 0),
             "n_missing_minutes": kinds.get("gap", 0), "n_off_grid_dropped": kinds.get("off_grid", 0),
             "checks": res.checks("bars"), "checks_not_run": res.checks_not_run("bars"),
             "files": [{"given": f.given, "sha256": f.sha256, "size": f.size, "sealed_unit": f.sealed_unit,
                        "rows_read": f.rows_read, "rows_kept": f.rows_kept} for f in res.files()],
             "seal_records": dict(res.manifest()["seal_records"]),
             "resolution": res.resolutions.get("bars")}
    if check_flags:
        syn = [a["row"] for a in an if a["kind"] == "synthetic"]
        recs = res.records("bars") if syn else []
        facts["n_ntrades0_volume_pos"] = sum(1 for i in syn if recs[i]["volume"] > 0)
        facts["n_kept_volume0"] = sum(1 for b in bars if b.volume == 0)
        facts["n_synthetic_not_flat"] = sum(1 for i in syn if len({recs[i][k] for k in ("open", "high", "low", "close")}) != 1)
        del recs
    if cents:
        bars, n_off = to_cents(bars)
        facts["price_unit"] = PRICE_UNIT_CENTS
        facts["n_not_whole_cent"] = n_off
    else:
        facts["price_unit"] = "USDT(置き場のまま)"
    if bars:
        facts["first_start"] = to_iso(int(bars[0].start_time_ns))
        facts["last_start"] = to_iso(int(bars[-1].start_time_ns))
    return bars, facts


def iter_range(lo_ns: int, hi_ns: int, root: str = ROOT, **kw):
    """暦年ごとに (年, BarEvent のタプル, 事実) を返す。"""
    check_range(lo_ns, hi_ns)
    for y, a, b in year_chunks(lo_ns, hi_ns):
        bars, facts = load_chunk(a, b, root, **kw)
        yield y, bars, facts


__all__ = ["HI", "LO", "PRICE_SCALE", "PRICE_UNIT_CENTS", "RESOLVE", "SYMBOL", "VENUE", "bar_spec", "check_range",
           "iter_range", "load_chunk", "to_cents", "year_chunks", "year_path"]
