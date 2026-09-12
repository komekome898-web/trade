"""K1-B(Binance 現物で同条件・同方法)の**独立検査**。read-only・ネットワークなし。

設計は `docs/PHASE2/K1/binance/CHECKS.md`(検査 ID はそこと対応)。
実装者の成果物(`scripts/k1_source.py`、`results/PHASE2/K1/binance/*.json`、`TABLES.md`)と
BitMEX 側のコミット済み出力(`results/PHASE2/K1/*.json`)を読み、各検査の
**合格 / 不合格 / 判定不能 / 情報** と根拠の数値を印字する。存在しない入力は「未生成」と出して落ちない。

  PYTHONPATH=src:scripts python scripts/check_k1_binance.py
      [--skip-data]                 データ全走査(約 1 分)を飛ばす(O 系の一部が判定不能になる)
      [--skip-loader-full]          実装者の loader で全期間を読む検査(L-08、約 1〜2 分)を飛ばす
      [--bitmex-rerun-dir DIR]      `--source bitmex` 再実行の出力が別ディレクトリにあるとき
      [--binance-dir DIR]           既定 results/PHASE2/K1/binance

書き込みは一切しない(subprocess は python 自身と `git show`/`git diff`/`git status` の読み取りだけ)。
"""
from __future__ import annotations

import argparse
import csv
import gzip
import importlib
import inspect
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
K1 = REPO / "results" / "PHASE2" / "K1"
BN1 = REPO / "backtest_data" / "binance_BTCUSDT_1m_20170801_20231231"
BN2 = REPO / "backtest_data" / "binance_BTCUSDT_1m_20240101_20260831"
BITMEX = REPO / "backtest_data" / "bitmex_trade_1s_XBTUSD"
BINANCE_FILES = [BN1 / f"binance_BTCUSDT_1m_{y}.csv.gz" for y in range(2017, 2024)] + \
                [BN2 / "binance_BTCUSDT_1m_20240101_20260831.csv.gz"]

FEET = (1, 3, 5, 15, 30, 60)
HORIZONS = (1, 2, 3, 5, 10, 20, 50)
MATCH_FROM = 1502942400            # 2017-08-17 04:00:00 UTC(Binance BTCUSDT の最初の足)
END_2019 = 1577836800              # 2020-01-01 00:00:00 UTC
OUTPUTS = ("effect", "direction_bias", "signal_horizon", "signal_horizon_notrunc",
           "body_wick", "exit_ablation")
# 走らせる前に書いた期待(CHECKS.md §D)。スナップショットの README から
EXPECT = {
    "rows": 3_343_519 + 1_402_560,
    "first": "2017-08-17 04:00:00+00:00",
    "last": "2026-08-31 23:59:00+00:00",
    "gaps_gt_60s": 35 + 0,
}
# 検査者が独立に評価する門(実装者の経路 `eff.signals` を通さない再実装)
MY_GATES = {"s19/b24": (19.0, 24.0), "s-/b-": (None, None), "soff/b24": ("off", 24.0),
            "s30/b40": (30.0, 40.0)}


# ------------------------------------------------------------------ 出力 ----

class Report:
    def __init__(self):
        self.rows = []
        self.counts = Counter()

    def add(self, cid, verdict, msg):
        self.counts[verdict] += 1
        self.rows.append((cid, verdict, msg))
        print(f"[{verdict}] {cid}: {msg}")

    def ok(self, cid, msg): self.add(cid, "合格", msg)
    def ng(self, cid, msg): self.add(cid, "不合格", msg)
    def na(self, cid, msg): self.add(cid, "判定不能", msg)
    def info(self, cid, msg): self.add(cid, "情報", msg)

    def check(self, cid, cond, msg):
        (self.ok if cond else self.ng)(cid, msg)


def load_json(path: Path):
    try:
        return json.loads(path.read_text("utf-8"))
    except FileNotFoundError:
        return None
    except Exception as e:  # noqa: BLE001
        return {"__error__": repr(e)}


def fmt(n):
    return f"{n:,}" if isinstance(n, int) else str(n)


# ---------------------------------------------------- 検査者側の再実装 ----

def my_direction(o, h, l, c, trunc=True):
    """RESULT.md §1.3 の擬似コードをそのまま書き直したもの(実装者の経路を通さない)。
    返すのは (sig, w, body, csign)。sig=0 は向き無し。"""
    candle = c - o
    if candle == 0 or c <= 0:
        return 0, 0.0, 0.0, 0
    csign = 1 if candle > 0 else -1
    top, under = (h - c, o - l) if csign == 1 else (h - o, c - l)
    tc, uc = (int(top), int(under)) if trunc else (top, under)
    if tc > uc:
        return -1, top, abs(candle), csign
    if uc > tc:
        return 1, under, abs(candle), csign
    return 0, 0.0, abs(candle), csign


def my_gate(sig, w, body, c, small, big):
    if sig == 0:
        return False
    wbp = w / c * 1e4
    ok_small = small != "off" and (small is None or wbp >= small) and w > body
    ok_big = big is not None and wbp >= big
    return ok_small or ok_big


# ------------------------------------------------------------ D: データ ----

def scan_data(rep: Report):
    """Binance 1m 全走査。事実を印字し、後続の検査に使う期待値を返す。"""
    facts = {}
    rows = 0
    dups = rev = misaligned = bad_suffix = 0
    zero_trades = zero_not_doji = zero_open_ne_prev = 0
    doji_with_trades = bad_ohlc = 0
    dec = Counter()
    per_year = Counter()
    per_year_zero = Counter()
    gaps = []
    mis_runs = []
    cur_run = None
    prev_ts = None
    prev_close = None
    first = last = None
    headers = set()
    # 落とした後の足の数(foot ごと・年ごと)と、足の開始時刻の列(gap_share 用)
    cur_bucket = {f: None for f in FEET}
    bars_per_foot = Counter()
    bars_per_foot_year = defaultdict(Counter)
    bucket_ts = {f: [] for f in FEET}
    kept_collisions = 0
    bucket_has_off = {f: False for f in FEET}
    bars_with_off = Counter()      # 秒≠0 の行を含む足の本数(foot ごと)
    off_straddle = Counter()       # 秒≠0 の行のうち、60 秒の尾が foot の窓境界をまたぐもの
    # 検査者の再実装による foot=1 の向きと門の数(年ごと)。落とした後の行 = 1 分足
    dirc = defaultdict(lambda: Counter())          # year -> buy/sell/tie/signed/bull/bear
    dirc_raw = defaultdict(lambda: Counter())
    gatec = defaultdict(lambda: Counter())         # (gate, year) -> buy/sell/strong_buy/...
    win_dir = Counter()                            # 2017-08-17..2019 窓(既存 venue.binance との突合)
    win_gate = defaultdict(Counter)
    for path in BINANCE_FILES:
        if not path.exists():
            rep.na("D-00", f"データ無し: {path}")
            return None
        with gzip.open(path, "rt", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader)
            headers.add(tuple(header))
            ix = {h: i for i, h in enumerate(header)}
            for r in reader:
                rows += 1
                s = r[ix["open_time"]]
                if not s.endswith("+00:00"):
                    bad_suffix += 1
                dt = datetime.fromisoformat(s)
                ts = int(dt.timestamp())
                y = dt.year
                o, h, l, c = (float(r[ix[k]]) for k in ("open", "high", "low", "close"))
                nt = int(r[ix["n_trades"]])
                for v in (r[ix["open"]], r[ix["high"]], r[ix["low"]], r[ix["close"]]):
                    dec[len(v.split(".")[1]) if "." in v else 0] += 1
                if first is None:
                    first = s
                last = s
                per_year[y] += 1
                if ts % 60:
                    misaligned += 1
                    if cur_run is None:
                        cur_run = [s, s, 1, ts % 60]
                    else:
                        cur_run[1] = s
                        cur_run[2] += 1
                elif cur_run is not None:
                    mis_runs.append(cur_run)
                    cur_run = None
                if prev_ts is not None:
                    if ts == prev_ts:
                        dups += 1
                    elif ts < prev_ts:
                        rev += 1
                    elif ts - prev_ts != 60:
                        gaps.append((ts - prev_ts,
                                     datetime.fromtimestamp(prev_ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                                     s[:19]))
                if h < l or h < max(o, c) or l > min(o, c):
                    bad_ohlc += 1
                if nt == 0:
                    zero_trades += 1
                    per_year_zero[y] += 1
                    if not (o == h == l == c):
                        zero_not_doji += 1
                    if prev_close is not None and o != prev_close:
                        zero_open_ne_prev += 1
                else:
                    if o == h == l == c:
                        doji_with_trades += 1
                    # ---- 落とした後の行についてのみ
                    off = ts % 60 != 0
                    for f in FEET:
                        w = f * 60
                        b = ts - ts % w
                        if b != cur_bucket[f]:
                            cur_bucket[f] = b
                            bars_per_foot[f] += 1
                            bars_per_foot_year[f][datetime.fromtimestamp(b, timezone.utc).year] += 1
                            bucket_ts[f].append(b)
                            bucket_has_off[f] = False
                        elif f == 1:
                            kept_collisions += 1
                        if off:
                            if not bucket_has_off[f]:
                                bucket_has_off[f] = True
                                bars_with_off[f] += 1
                            # この kline(60 秒)の尾が foot の窓境界をまたぐ = 切り下げ以外の規則なら所属が変わる行
                            if (ts + 60) - (ts + 60) % w != b:
                                off_straddle[f] += 1
                    sig, w, body, cs = my_direction(o, h, l, c)
                    sig_raw = my_direction(o, h, l, c, trunc=False)[0]
                    dc = dirc[y]
                    dcr = dirc_raw[y]
                    in_win = MATCH_FROM <= ts < END_2019
                    if cs != 0:
                        dc["signed"] += 1
                        dc["bull" if cs == 1 else "bear"] += 1
                        dc["sell" if sig == -1 else ("buy" if sig == 1 else "tie")] += 1
                        dcr["sell" if sig_raw == -1 else ("buy" if sig_raw == 1 else "tie")] += 1
                        if in_win:
                            win_dir["signed"] += 1
                            win_dir["sell" if sig == -1 else ("buy" if sig == 1 else "tie")] += 1
                            win_dir["raw_" + ("sell" if sig_raw == -1 else ("buy" if sig_raw == 1 else "tie"))] += 1
                    if sig != 0:
                        for gname, (sm, bg) in MY_GATES.items():
                            if my_gate(sig, w, body, c, sm, bg):
                                side = "buy" if sig == 1 else "sell"
                                strength = "strong" if sig == cs else "weak"
                                gatec[(gname, y)][side] += 1
                                gatec[(gname, y)][f"{strength}_{side}"] += 1
                                if in_win:
                                    win_gate[gname][side] += 1
                                    win_gate[gname][f"{strength}_{side}"] += 1
                prev_ts, prev_close = ts, c
    if cur_run is not None:
        mis_runs.append(cur_run)
    gaps.sort(key=lambda g: -g[0])

    kept = rows - zero_trades
    facts.update({
        "rows": rows, "first": first, "last": last, "headers": [list(h) for h in headers],
        "duplicates": dups, "reversals": rev, "bad_tz_suffix": bad_suffix,
        "misaligned": misaligned, "misaligned_runs": mis_runs,
        "n_trades_eq0": zero_trades, "n_trades_eq0_not_doji": zero_not_doji,
        "n_trades_eq0_open_ne_prev_close": zero_open_ne_prev,
        "doji_with_trades": doji_with_trades, "bad_ohlc": bad_ohlc,
        "price_decimals": dict(dec), "per_year_rows": dict(sorted(per_year.items())),
        "per_year_n_trades_eq0": dict(sorted(per_year_zero.items())),
        "gaps": gaps, "kept": kept, "kept_collisions_1m": kept_collisions,
        "bars_per_foot": dict(bars_per_foot),
        "bars_per_foot_year": {f: dict(sorted(c.items())) for f, c in bars_per_foot_year.items()},
        "bucket_ts": bucket_ts, "dirc": dirc, "dirc_raw": dirc_raw, "gatec": gatec,
        "win_dir": win_dir, "win_gate": win_gate,
        "bars_with_off": dict(bars_with_off), "off_straddle": dict(off_straddle),
    })
    rep.info("D-14", "秒≠0 の行(申告 1): 含む足の本数 " + ", ".join(f"{f}分 {bars_with_off[f]:,}/{bars_per_foot[f]:,}" for f in FEET)
                     + " / 60 秒の尾が窓境界をまたぐ行(切り下げ以外の規則なら所属が変わる) "
                     + ", ".join(f"{f}分 {off_straddle[f]:,}" for f in FEET))

    # ---- 印字と期待との突合
    rep.check("D-01", rows == EXPECT["rows"] and first == EXPECT["first"] and last == EXPECT["last"],
              f"行数 {fmt(rows)}(期待 {fmt(EXPECT['rows'])})/ 最初 {first} / 最後 {last}")
    rep.check("D-02", dups == 0 and rev == 0, f"重複時刻 {dups} / 逆転 {rev}(期待 0/0)")
    rep.check("D-03a", bad_suffix == 0, f"'+00:00' 以外の時刻 {bad_suffix} 行(期待 0)。列名 {sorted(headers)}")
    runs_s = "; ".join(f"{a[:16]}〜{b[:16]} {n:,}行 +{sec}s" for a, b, n, sec in mis_runs)
    rep.add("D-03b", "合格" if misaligned == 0 else "情報",
            f"秒≠0 の open_time {fmt(misaligned)} 行(期待 0)。連続区間: {runs_s or '無し'}")
    rep.check("D-04", zero_not_doji == 0 and zero_open_ne_prev == 0,
              f"n_trades==0 は {fmt(zero_trades)} 行({zero_trades / rows:.2%})。うち o=h=l=c でない {zero_not_doji}、"
              f"o≠直前終値 {zero_open_ne_prev}(期待 0/0)。年別 {dict(sorted(per_year_zero.items()))}")
    rep.info("D-04b", f"n_trades>0 かつ o=h=l=c(同値足、残す)= {fmt(doji_with_trades)} 行")
    rep.check("D-05", bad_ohlc == 0, f"h<l / h<max(o,c) / l>min(o,c) の行 {bad_ohlc}(期待 0)")
    idx = load_json(BN1 / "binance_1m_index.json")
    if idx:
        exp_years = {int(y): v["rows"] for y, v in idx["years"].items()}
        ok = all(per_year.get(y) == n for y, n in exp_years.items())
        rep.check("D-06", ok, f"年別行数 2017-2023 が index.json と一致: {ok}。全年 {dict(sorted(per_year.items()))}")
    else:
        rep.na("D-06", "binance_1m_index.json 無し")
    top = "; ".join(f"{g[0]:,}s {g[1]}→{g[2]}" for g in gaps[:10])
    rep.check("D-07", len(gaps) == EXPECT["gaps_gt_60s"],
              f"60 秒を超える隣接間隔 {len(gaps)} 件(期待 {EXPECT['gaps_gt_60s']})、最大 {gaps[0][0] if gaps else 0:,}s。上位: {top}")
    rep.info("D-07b", f"落とした後の隣接 1 分足で間隔≠60s: {sum(1 for a, b in zip(bucket_ts[1], bucket_ts[1][1:]) if b - a != 60):,} 箇所"
                      f" → 1|1 の gap_share 期待 {sum(1 for a, b in zip(bucket_ts[1], bucket_ts[1][1:]) if b - a != 60) / (bars_per_foot[1] - 1):.4f}")
    y23 = per_year.get(2023, 0)
    rep.info("D-08", "2023-12-31 23:59 → 2024-01-01 00:00 の連続性は D-07 の欠落一覧に境界が無いことで確認: "
                     + ("境界に欠落無し" if not any(g[1].startswith('2023-12-31 23:59') for g in gaps) else "境界に欠落あり"))
    rep.check("D-09", bars_per_foot[1] == kept and kept_collisions == 0,
              f"落とした後の行 {fmt(kept)} / 1 分バケット {fmt(bars_per_foot[1])} / 落とした後の分衝突 {kept_collisions}"
              f" → fold() が 1 分で恒等: {bars_per_foot[1] == kept}(落とさない版は衝突 1 件で 1 本ずれる)")
    rep.info("D-10", "落とした後の足の本数(期待値として O-05 で使う): " + ", ".join(f"{f}分 {fmt(bars_per_foot[f])}" for f in FEET))
    rep.info("D-10b", f"1 分足の年別本数: {facts['bars_per_foot_year'][1]}")
    rep.add("D-11", "合格" if max(dec) <= 2 else "情報",
            f"価格の小数桁分布 {dict(sorted(dec.items()))}(期待: 2 桁以下 = 呼値 0.01。3 桁以上は件数を記録)")
    rep.info("D-12", f"検査者の再実装(§1.3)による 1 分足・窓 2017-08-17〜2019 の向き: {dict(win_dir)}; "
                     + "; ".join(f"{g}: {dict(win_gate[g])}" for g in MY_GATES))
    return facts


def scan_bitmex_ticks(rep: Report):
    """BitMEX 秒バーを数日だけ読み、価格の刻みを確かめる(全期間は読まない)。"""
    days = ("2017/20170101", "2017/20170601", "2017/20171201", "2018/20180601", "2019/20190601", "2019/20191231")
    out = []
    for d in days:
        p = BITMEX / f"{d}.csv.gz"
        if not p.exists():
            out.append(f"{d}: 無し")
            continue
        n = half = 0
        with gzip.open(p, "rt", newline="") as fh:
            r = csv.reader(fh)
            hdr = next(r)
            for row in r:
                n += 1
                if all((float(v) * 2).is_integer() for v in row[1:5]):
                    half += 1
        out.append(f"{d[5:]}: 0.5 刻み {half / n:.1%}(行 {n:,}, 列 {hdr[:5]})")
    rep.info("D-13", "BitMEX 秒バーの呼値(標本日): " + "; ".join(out))


# ------------------------------------------------------------ L: loader ----

def check_loader(rep: Report, facts, full: bool):
    try:
        ks = importlib.import_module("k1_source")
    except ModuleNotFoundError:
        rep.na("L-01", "scripts/k1_source.py 未生成")
        return None
    except Exception as e:  # noqa: BLE001
        rep.ng("L-01", f"k1_source の import で例外: {e!r}")
        return None
    lb = getattr(ks, "load_bars", None)
    if lb is None:
        rep.ng("L-01", "k1_source.load_bars が無い")
        return None
    sig = str(inspect.signature(lb))
    rep.info("L-01", f"k1_source.load_bars{sig}。公開名: "
                     + ", ".join(n for n in dir(ks) if not n.startswith("_") and n.isupper()))
    consts = {n: getattr(ks, n) for n in dir(ks) if n.isupper() and not n.startswith("_")}
    rep.info("L-07", "k1_source の定数: " + "; ".join(f"{k}={v!r}"[:120] for k, v in consts.items()))

    def call(src, a, b):
        return lb(src, a, b)

    # L-02: 最初の日
    try:
        bars = call("binance", date(2017, 8, 17), date(2017, 8, 17))
    except Exception as e:  # noqa: BLE001
        rep.ng("L-02", f"load_bars('binance', 2017-08-17, 2017-08-17) で例外: {e!r}")
        return ks
    exp_n = None
    # CSV から列名で当日の生行と n_trades==0 を数える
    raw = []
    with gzip.open(BN1 / "binance_BTCUSDT_1m_2017.csv.gz", "rt", newline="") as fh:
        r = csv.reader(fh)
        hdr = next(r)
        ix = {h: i for i, h in enumerate(hdr)}
        for row in r:
            if row[ix["open_time"]].startswith("2017-08-17"):
                raw.append(row)
    kept_raw = [row for row in raw if int(row[ix["n_trades"]]) != 0]
    exp_n = len(kept_raw)
    b0 = bars[0] if bars else None
    exp0 = (MATCH_FROM,) + tuple(float(kept_raw[0][ix[k]]) for k in ("open", "high", "low", "close"))
    rep.check("L-02", len(bars) == exp_n and b0 is not None and tuple(b0[:5]) == exp0,
              f"2017-08-17: 返した本数 {len(bars)}(期待 {exp_n} = 生 {len(raw)} − n_trades==0 {len(raw) - exp_n});"
              f" 先頭 {b0} / 期待 {exp0}(列名で読んだ o,h,l,c)")
    rep.check("L-02b", len(bars) != len(raw), f"n_trades==0 を落としている: {len(bars) != len(raw)}")
    rep.info("L-02c", f"戻り値の型: 要素 {type(b0).__name__} 長さ {len(b0) if b0 else None}, ts 型 {type(b0[0]).__name__ if b0 else None}")

    # L-03: 時間帯に依存しないか(別プロセスを TZ=Asia/Tokyo で走らせる)
    code = ("import sys,json,datetime;sys.path.insert(0,'scripts');import k1_source as k;"
            "d=datetime.date;b=k.load_bars('binance',d(2017,8,17),d(2017,8,17));"
            "c=k.load_bars('binance',d(2018,2,9),d(2018,2,9));"
            "print(json.dumps([len(b),list(b[0][:5]),list(b[-1][:5]),len(c),list(c[0][:5])]))")
    env = dict(os.environ, TZ="Asia/Tokyo", PYTHONPATH="src:scripts")
    try:
        p = subprocess.run([sys.executable, "-c", code], cwd=REPO, env=env, capture_output=True, text=True, timeout=600)
        got = json.loads(p.stdout.strip().splitlines()[-1])
        here = call("binance", date(2018, 2, 9), date(2018, 2, 9))
        mine = [len(bars), list(bars[0][:5]), list(bars[-1][:5]), len(here), list(here[0][:5])]
        rep.check("L-03", got == mine, f"TZ=Asia/Tokyo での結果 {got} / TZ=UTC {mine}")
    except Exception as e:  # noqa: BLE001
        rep.na("L-03", f"別プロセス実行に失敗: {e!r} / stderr={getattr(p, 'stderr', '')[-300:] if 'p' in dir() else ''}")

    # L-04: 終端の含み方
    try:
        bars = call("binance", date(2026, 8, 31), date(2026, 8, 31))
        last_exp = int(datetime(2026, 8, 31, 23, 59, tzinfo=timezone.utc).timestamp())
        rep.check("L-04", bool(bars) and bars[-1][0] == last_exp and len(bars) == 1440,
                  f"2026-08-31: 本数 {len(bars)}(期待 1440)、最後の ts {bars[-1][0] if bars else None}(期待 {last_exp} = 23:59)")
    except Exception as e:  # noqa: BLE001
        rep.ng("L-04", f"例外: {e!r}")

    # L-05: bitmex 経路が base.load_seconds と同一か(1 日だけ)
    try:
        base = importlib.import_module("measure_katsuo_dispersion")
        a = call("bitmex", date(2017, 1, 1), date(2017, 1, 1))
        b = base.load_seconds(date(2017, 1, 1), date(2017, 1, 1))
        rep.check("L-05", list(map(tuple, a)) == list(map(tuple, b)),
                  f"load_bars('bitmex', 2017-01-01) {len(a)} 行 vs base.load_seconds {len(b)} 行、同一: {list(map(tuple, a)) == list(map(tuple, b))}")
    except Exception as e:  # noqa: BLE001
        rep.na("L-05", f"例外: {e!r}")

    # L-06: +20 秒区間の ts をどう返すか(情報)
    try:
        bars = call("binance", date(2017, 12, 5), date(2017, 12, 5))
        secs = Counter(b[0] % 60 for b in bars)
        rep.info("L-06", f"2017-12-05(open_time が +20s の日): 返した ts の秒 {dict(secs)}、本数 {len(bars)}。"
                         "fold() は分に切り下げるので結果は同じだが、loader が切り下げるか生のまま返すかを記録")
    except Exception as e:  # noqa: BLE001
        rep.na("L-06", f"例外: {e!r}")

    # L-09: bitmex の既定(期間・出力先)が従来どおりか
    srcs = consts.get("SOURCES")
    if isinstance(srcs, dict) and "bitmex" in srcs:
        bm = srcs["bitmex"]
        ok = (bm.get("start") == date(2017, 1, 1) and bm.get("end") == date(2019, 12, 31)
              and Path(bm.get("out_dir", "")).resolve() == K1.resolve())
        rep.check("L-09", ok, f"SOURCES['bitmex'] = {bm}(期待 2017-01-01〜2019-12-31、出力 results/PHASE2/K1)")
        bn = srcs.get("binance", {})
        rep.check("L-09b", bn.get("start") == date(2017, 8, 17) and bn.get("end") == date(2026, 8, 31),
                  f"SOURCES['binance'] = {bn}(期待 2017-08-17〜2026-08-31)")
    else:
        rep.na("L-09", "k1_source.SOURCES が無い(既定の期間・出力先の置き場が違う。目視で確認)")

    # L-08: 全期間を読んで fold(…,1) が恒等か・落とした件数
    if full and facts:
        try:
            base = importlib.import_module("measure_katsuo_dispersion")
            start = consts.get("BINANCE_START", date(2017, 8, 17))
            end = consts.get("BINANCE_END", date(2026, 8, 31))
            if not isinstance(start, date):
                start, end = date(2017, 8, 17), date(2026, 8, 31)
            allb = call("binance", start, end)
            n1 = len(base.fold(allb, 1))
            rep.check("L-08", len(allb) == facts["kept"] and n1 == len(allb),
                      f"全期間 {start}〜{end}: 返した本数 {fmt(len(allb))}(期待 {fmt(facts['kept'])} = 生 {fmt(facts['rows'])} − {fmt(facts['n_trades_eq0'])});"
                      f" fold(…,1) の本数 {fmt(n1)}(恒等: {n1 == len(allb)})")
            per_foot = {f: len(base.fold(allb, f)) for f in FEET if f != 1}
            rep.check("L-08b", all(per_foot[f] == facts["bars_per_foot"][f] for f in per_foot),
                      f"foot 別本数 {per_foot} vs 検査者の計算 { {f: facts['bars_per_foot'][f] for f in per_foot} }")
            # L-10(申告 2): loader の assert は時刻の一致を求めない。fold(…,1) の ts と loader の ts が違う行数
            b1 = base.fold(allb, 1)
            ts_diff = sum(1 for a, b in zip(allb, b1) if a[0] != b[0])
            ts_off = sum(1 for a in allb if a[0] % 60)
            rep.check("L-10", ts_diff == ts_off,
                      f"loader の ts と fold(…,1) の ts が違う行 {ts_diff:,}(= 秒≠0 の行 {ts_off:,}。落とす前は {facts['misaligned']:,})。"
                      "o/h/l/c は恒等、時刻ラベルだけが分の頭に動く")
            del allb, b1
        except Exception as e:  # noqa: BLE001
            rep.na("L-08", f"例外: {e!r}")
    elif full:
        rep.na("L-08", "データ走査を飛ばしたので期待値が無い")
    return ks


# ----------------------------------------------------------- S: 差分・静的 ----

def git(*args):
    try:
        p = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=60)
        return p.returncode, p.stdout
    except Exception as e:  # noqa: BLE001
        return -1, repr(e)


def check_static(rep: Report):
    rc, out = git("status", "--porcelain", "--", "scripts", "results/PHASE2/K1")
    changed = [l[3:] for l in out.splitlines()] if rc == 0 else []
    rep.info("S-01", f"作業ツリーで変更/追加されたファイル({len(changed)}): {', '.join(changed) or '無し'}")

    for name in ("measure_katsuo_effect.py", "measure_katsuo_exit_ablation.py", "measure_katsuo_direction_bias.py"):
        p = REPO / "scripts" / name
        txt = p.read_text("utf-8") if p.exists() else ""
        hard = re.findall(r"\(\s*2017\s*,\s*2018\s*,\s*2019\s*\)", txt)
        rep.check("S-02", not hard, f"{name}: 年のハードコード (2017, 2018, 2019) = {len(hard)} 箇所(期待 0)")

    rc, out = git("diff", "--", "scripts/measure_katsuo_dispersion.py")
    touched = [l for l in out.splitlines() if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
    rep.add("S-03", "合格" if not touched else "情報",
            f"measure_katsuo_dispersion.py(load_seconds / fold の置き場)の差分行 {len(touched)}"
            + (":\n      " + "\n      ".join(touched[:20]) if touched else ""))

    for name, needle in (("measure_katsuo_effect.py", '"effect.json"'),
                         ("measure_katsuo_signal_horizon.py", '"signal_horizon.json"'),
                         ("measure_katsuo_body_wick.py", '"body_wick.json"'),
                         ("measure_katsuo_exit_ablation.py", '"exit_ablation.json"'),
                         ("measure_katsuo_direction_bias.py", '"direction_bias.json"')):
        p = REPO / "scripts" / name
        txt = p.read_text("utf-8") if p.exists() else ""
        has_src = ("--source" in txt) or ("add_source_args" in txt)
        rep.info("S-04", f"{name}: `--source`(add_source_args 経由を含む){'あり' if has_src else '無し'}; 既定出力名 {needle} {'あり' if needle in txt else '無し'};"
                         f" EXPLORE_START/END 定数 {'あり' if 'EXPLORE_START' in txt else '無し'}; base.load_seconds の直接呼び出し {'あり' if 'base.load_seconds' in txt else '無し'}")

    p = REPO / "scripts" / "k1_source.py"
    if p.exists():
        txt = p.read_text("utf-8")
        lines = [f"{i + 1}: {l.strip()}" for i, l in enumerate(txt.splitlines())
                 if re.search(r"timestamp\(|strptime|fromisoformat|tzinfo|timezone|epoch|utcfromtimestamp", l)]
        rep.info("S-05", "k1_source.py の時刻の解釈に関わる行(目視用):\n      " + "\n      ".join(lines))
        rep.check("S-05b", "n_trades" in txt, f"k1_source.py が n_trades を参照: {'n_trades' in txt}")
        by_name = ("open_time" in txt) or ("DictReader" in txt)
        by_pos = bool(re.search(r"\w\[[1-4]\]", txt))
        rep.info("S-05c", f"k1_source.py の列参照: 列名 {by_name} / 位置 [1]〜[4] {by_pos}")
    else:
        rep.na("S-05", "scripts/k1_source.py 未生成")

    p = REPO / "scripts" / "render_k1_year_tables.py"
    txt = p.read_text("utf-8") if p.exists() else ""
    years_hard = bool(re.search(r'YEARS\s*=\s*\(\s*"2017"', txt))
    rep.info("S-06", f"render_k1_year_tables.py: YEARS ハードコード {'あり' if years_hard else '無し'}、"
                     f"MARKET ラベル(+1335% 等){'あり' if '+1335%' in txt else '無し'}、--dir {'あり' if '--dir' in txt else '無し'}")

    # S-07(モデル名の有無)は検査者が手で grep する。パターンをここに書くと自分が引っかかる
    rep.na("S-07", "変更ファイル中のモデル名の有無は手で grep する(このスクリプトには書かない)")


# ----------------------------------------------------- R: BitMEX 再現ゲート ----

def diff_json(a, b, path="", out=None, limit=200):
    if out is None:
        out = []
    if len(out) >= limit:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append((f"{path}/{k}", "片方に無い"))
            else:
                diff_json(a[k], b[k], f"{path}/{k}", out, limit)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, f"長さ {len(a)} vs {len(b)}"))
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                diff_json(x, y, f"{path}[{i}]", out, limit)
    else:
        if isinstance(a, float) and isinstance(b, float):
            if not (a == b or (math.isnan(a) and math.isnan(b)) or abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))):
                out.append((path, f"{a} vs {b}"))
        elif a != b:
            out.append((path, f"{a!r} vs {b!r}"))
    return out


def check_bitmex_regression(rep: Report, rerun_dir: Path | None):
    for name in OUTPUTS:
        committed_path = K1 / f"{name}.json"
        if rerun_dir is not None:
            new = load_json(rerun_dir / f"{name}.json")
            ref = load_json(committed_path)
            src = f"{rerun_dir}/{name}.json vs コミット済み"
        else:
            rc, out = git("diff", "--quiet", "--", str(committed_path.relative_to(REPO)))
            if rc == 0:
                rep.na(f"R-{name}", "再実行の出力が見当たらない(作業ツリーは HEAD と同一。再実行して上書きしたなら一致、"
                                    "未実施なら未検査。--bitmex-rerun-dir で別置きの出力を指定できる)")
                continue
            rc, out = git("show", f"HEAD:{committed_path.relative_to(REPO).as_posix()}")
            ref = json.loads(out) if rc == 0 else None
            new = load_json(committed_path)
            src = "作業ツリー(再実行後)vs HEAD"
        if new is None or ref is None:
            rep.na(f"R-{name}", f"ファイル無し({src})" + ("(BitMEX 側の notrunc は設計書 §4.2 の 5 本に含まれない)" if name == "signal_horizon_notrunc" else ""))
            continue
        # 再実行側が top-level に足したメタ(source / load / reference / explore / trunc)は本体の差分と分けて報告する
        added = sorted(k for k in ("source", "load", "reference", "explore", "trunc") if k in new and k not in ref)
        new_body = {k: v for k, v in new.items() if k not in added}
        rep.info(f"R-{name}-meta", f"再実行側だけにある top-level キー {added}(本体の比較から除外)。load={new.get('load')} explore={new.get('explore')}"
                                   f"(期待 rows 49,054,818 / 2017-01-01〜2019-12-31: "
                                   f"{new.get('load', {}).get('rows') == 49054818 and new.get('explore') in (None, ['2017-01-01', '2019-12-31'])})")
        diffs = diff_json(new_body, ref)
        strict = name in ("signal_horizon", "signal_horizon_notrunc", "body_wick", "exit_ablation")
        non_ci = [d for d in diffs if "ci95_bp" not in d[0]]
        if strict:
            rep.check(f"R-{name}", not diffs, f"{src}: 差分 {len(diffs)} 箇所(期待 0、全フィールド一致)"
                      + (" 例: " + "; ".join(f"{p} {m}" for p, m in diffs[:8]) if diffs else ""))
        else:
            rep.check(f"R-{name}", not non_ci,
                      f"{src}: ci95 以外の差分 {len(non_ci)} 箇所(期待 0)、ci95 の差分 {len(diffs) - len(non_ci)} 箇所"
                      f"(共有乱数列なので動きうる。動いたなら消費順が変わった印 → 報告に書く)"
                      + (" 例: " + "; ".join(f"{p} {m}" for p, m in non_ci[:8]) if non_ci else ""))
        if name == "effect" and diffs and not non_ci:
            rep.info("R-effect-b", "ci95 だけが動いた = 乱数の消費順が変わっている(セルの順・件数・欠落のどれか)。同じコード経路なら動かないはず")


# ------------------------------------------------------ O: Binance の出力 ----

def year_sum(per_year, years, key):
    return sum(v.get(key, 0) for y, v in per_year.items() if int(y) in years)


def check_outputs(rep: Report, bdir: Path, facts):
    B = {n: load_json(bdir / f"{n}.json") for n in OUTPUTS}
    M = {n: load_json(K1 / f"{n}.json") for n in OUTPUTS}
    for n in OUTPUTS:
        if B[n] is None:
            rep.na(f"O-00-{n}", f"{bdir / (n + '.json')} 未生成")
        elif "__error__" in B[n]:
            rep.ng(f"O-00-{n}", f"読めない: {B[n]['__error__']}")
            B[n] = None
    years_all = set(range(2017, 2027))

    # ---- O-01 / O-02 / O-03: 族・種・キー集合・期間
    for n in ("effect", "signal_horizon", "signal_horizon_notrunc", "exit_ablation", "body_wick"):
        b, m = B.get(n), M.get(n)
        if not b or not m:
            continue
        for fld in ("family", "bootstrap_reps", "seed", "trunc", "bins", "horizons", "gates", "modes", "fixed_h"):
            if fld in m:
                rep.check(f"O-01-{n}", b.get(fld) == m.get(fld), f"{fld}: binance={str(b.get(fld))[:80]} / bitmex={str(m.get(fld))[:80]}")
        kb, km = set(b.get("cells", {})), set(m.get("cells", {}))
        if n == "body_wick":
            rep.info(f"O-02-{n}", f"セル数 binance {len(kb)} / bitmex {len(km)}(層の n≥30 で変わるので一致は求めない。共通 {len(kb & km)})")
        else:
            rep.check(f"O-02-{n}", kb == km, f"セルのキー集合: binance {len(kb)} / bitmex {len(km)} / 片方だけ {len(kb ^ km)}"
                      + (" 例: " + ", ".join(sorted(kb ^ km)[:6]) if kb ^ km else ""))
        per = {k: str(v) for k, v in b.items() if k in ("explore", "period", "range", "start", "end", "source", "load", "reference")}
        rep.check(f"O-03-{n}", b.get("explore") == ["2017-08-17", "2026-08-31"] and b.get("source") == "binance",
                  f"explore/source(期待 ['2017-08-17','2026-08-31'] / 'binance'): {per}")
        note = str(b.get("note", ""))
        if "2017-2019" in note or "2017-2019" in note.replace("〜", "-"):
            rep.info(f"O-03b-{n}", f"note が BitMEX 時代の文面のまま('2017-2019' を含む): {note[:80]}… → 読み手を誤らせる(軽微)")

    # ---- O-04: per_year の年集合と n の整合
    for n in ("effect", "signal_horizon", "signal_horizon_notrunc", "exit_ablation"):
        b = B.get(n)
        if not b:
            continue
        ys = set()
        bad_sum = 0
        for k, c in b["cells"].items():
            py = c.get("per_year", {})
            ys |= {int(y) for y in py}
            if sum(v["n"] for v in py.values()) != c["n"]:
                bad_sum += 1
        rep.check(f"O-04-{n}", ys == years_all and bad_sum == 0,
                  f"per_year の年集合 {sorted(ys)}(期待 2017..2026)、per_year の n 合計 ≠ n のセル {bad_sum}(期待 0)")

    # ---- O-05: 無条件ベースラインの n / gap_share と データ走査の期待値
    sh = B.get("signal_horizon")
    if sh and facts:
        bl = sh.get("baseline_unconditional", {})
        bad = []
        for f in FEET:
            for h in HORIZONS:
                c = bl.get(f"{f}|{h}")
                if c is None:
                    bad.append(f"{f}|{h} 無し")
                    continue
                exp_n = facts["bars_per_foot"][f] - h
                bts = facts["bucket_ts"][f]
                exp_gap = sum(1 for i in range(len(bts) - h) if bts[i + h] - bts[i] != f * 60 * h) / exp_n
                if c["n"] != exp_n or abs(c["gap_share"] - exp_gap) > 1e-4:
                    bad.append(f"{f}|{h}: n {c['n']} vs 期待 {exp_n}, gap_share {c['gap_share']} vs 期待 {exp_gap:.4f}")
        rep.check("O-05", not bad, f"baseline_unconditional の n = 足の本数 − h、gap_share = 落とした後の間隔ずれ: 不一致 {len(bad)}(期待 0)"
                  + (" " + "; ".join(bad[:6]) if bad else ""))
        c11 = bl.get("1|1", {}).get("per_year", {})
        exp = dict(facts["bars_per_foot_year"][1])
        last_y = max(exp)
        exp[last_y] -= 1
        got = {int(y): v["n"] for y, v in c11.items()}
        rep.check("O-05b", got == exp, f"1|1 の年別 n {got} vs 期待(年別 1 分足本数、最終年 −1){exp}")
    elif sh:
        rep.na("O-05", "データ走査を飛ばしたので期待値が無い")

    # ---- O-06: signal_horizon の内部整合
    for n in ("signal_horizon", "signal_horizon_notrunc"):
        b = B.get(n)
        if not b:
            continue
        bad = 0
        ci_out = 0
        for k, c in b["cells"].items():
            if c["buy_n"] + c["sell_n"] != c["n"] or not (0 <= c["hit"] <= 1):
                bad += 1
            if sum(v["buy_n"] for v in c["per_year"].values()) != c["buy_n"]:
                bad += 1
            lo, hi = c["ci95_bp"]
            if not (lo <= c["mean_bp"] <= hi):
                ci_out += 1
        rep.check(f"O-06-{n}", bad == 0, f"buy_n+sell_n=n・hit∈[0,1]・年別 buy_n 合計: 不整合 {bad}(期待 0)。平均が区間外のセル {ci_out}(情報)")

    # ---- O-07: 切り捨てなし ⊇ 切り捨てあり
    t, nt = B.get("signal_horizon"), B.get("signal_horizon_notrunc")
    if t and nt:
        viol = [k for k, c in t["cells"].items() if k in nt["cells"] and
                (nt["cells"][k]["n"] < c["n"] or nt["cells"][k]["buy_n"] < c["buy_n"] or nt["cells"][k]["sell_n"] < c["sell_n"])]
        rep.check("O-07", not viol and t.get("trunc", True) is True and nt.get("trunc") is False,
                  f"trunc フラグ {t.get('trunc')}/{nt.get('trunc')}(期待 True/False)。n_notrunc < n_trunc のセル {len(viol)}(期待 0)"
                  + (" 例: " + ", ".join(viol[:5]) if viol else ""))
        d = diff_json(t.get("baseline_unconditional"), nt.get("baseline_unconditional"))
        rep.check("O-07b", not d, f"無条件ベースラインは切り捨てに依らないので両ファイルで同一: 差分 {len(d)}(期待 0)")
        same = sum(1 for k, c in t["cells"].items() if k in nt["cells"] and nt["cells"][k]["n"] == c["n"])
        rep.info("O-07c", f"n が切り捨ての有無で同じセル {same}/{len(t['cells'])}(BitMEX 側: "
                          f"{sum(1 for k, c in M['signal_horizon']['cells'].items() if k in M['signal_horizon_notrunc']['cells'] and M['signal_horizon_notrunc']['cells'][k]['n'] == c['n']) if M.get('signal_horizon') and M.get('signal_horizon_notrunc') else '?'})")

    # ---- O-08: effect の内部整合
    e = B.get("effect")
    if e:
        bad = 0
        reasons = set()
        for k, c in e["cells"].items():
            reasons |= set(c["exit_reasons"])
            if sum(c["exit_reasons"].values()) != c["n"] or c["hold_median"] < 1:
                bad += 1
        rep.check("O-08", bad == 0 and reasons <= {"invalidated", "reversed", "opposite_weak"},
                  f"exit_reasons 合計 = n・hold_median ≥ 1: 不整合 {bad}(期待 0)。理由の集合 {sorted(reasons)}")

    # ---- O-09: exit_ablation の full を effect と検査者が突き合わせる(組み込みゲートを信用しない)
    xa = B.get("exit_ablation")
    if xa and e:
        bad = []
        full_keys = [k for k in xa["cells"] if k.startswith("full|")]
        for k in full_keys:
            c = xa["cells"][k]
            ek = k[len("full|"):]
            r = e["cells"].get(ek)
            if r is None:
                bad.append(f"{k}: effect に無し")
                continue
            if (c["n"] != r["n"] or abs(c["mean_bp"] - r["mean_bp"]) > 2e-3 or c["per_year"] != r["per_year"]
                    or c["exit_reasons"] != r["exit_reasons"] or c["hold_median"] != r["hold_median"]):
                bad.append(k)
        rg = xa.get("reproduction_gate", [])
        rep.check("O-09", not bad and len(rg) == len(full_keys) and all(x["ok"] for x in rg) and len(full_keys) == len(e["cells"]),
                  f"full セル {len(full_keys)} / effect セル {len(e['cells'])} / 検査者の突合で不一致 {len(bad)}(n・平均・年別・決済理由・保有中央値)"
                  f" / 組み込みゲート {sum(x['ok'] for x in rg)}/{len(rg)}" + (" 例: " + "; ".join(bad[:5]) if bad else ""))
    elif xa and not e:
        rep.na("O-09", "binance/effect.json が無いので突合できない(組み込みゲートも空のはず: "
                       f"reproduction_gate {len(xa.get('reproduction_gate', []))} 件)")

    # ---- O-10: body_wick の (*,*) を signal_horizon と検査者が突き合わせる
    bw = B.get("body_wick")
    if bw and sh:
        bad = []
        cnt = 0
        for f in FEET:
            for st in ("strong", "weak"):
                for h in bw.get("horizons", (1, 2, 3, 5, 10)):
                    a = bw["cells"].get(f"s19/b24|{f}|*|*|{st}|{h}")
                    r = sh["cells"].get(f"{f}|s19/b24|{st}|{h}")
                    if a is None or r is None:
                        bad.append(f"{f}|{st}|{h}: 無し({a is None},{r is None})")
                        continue
                    cnt += 1
                    if a["n"] != r["n"] or abs(a["mean_bp"] - r["mean_bp"]) > 1e-3:
                        bad.append(f"{f}|{st}|{h}: n {a['n']} vs {r['n']}, mean {a['mean_bp']} vs {r['mean_bp']}")
        rg = bw.get("reproduction_gate", [])
        rep.check("O-10", not bad and len(rg) == cnt and all(x["ok"] for x in rg) and cnt == len(FEET) * 2 * len(bw.get("horizons", (1, 2, 3, 5, 10))),
                  f"(*,*) セル {cnt} 件を突合、不一致 {len(bad)} / 組み込みゲート {sum(x['ok'] for x in rg)}/{len(rg)}(期待 60/60)"
                  + (" 例: " + "; ".join(bad[:5]) if bad else ""))
        both_bad = sum(1 for f in FEET for h in HORIZONS
                       if all(sh["cells"].get(f"{f}|s19/b24|{s}|{h}") for s in ("strong", "weak", "both"))
                       and sh["cells"][f"{f}|s19/b24|both|{h}"]["n"] != sh["cells"][f"{f}|s19/b24|strong|{h}"]["n"] + sh["cells"][f"{f}|s19/b24|weak|{h}"]["n"])
        rep.check("O-10b", both_bad == 0, f"signal_horizon で both.n = strong.n + weak.n でない (foot,h) {both_bad}(期待 0)")
    elif bw and not sh:
        rep.na("O-10", f"binance/signal_horizon.json が無い(組み込みゲート {len(bw.get('reproduction_gate', []))} 件)")

    # ---- O-11: direction_bias — 既存の venue.binance(2017-08-17〜2019、落とさない版)と 1 分足で突合
    db, dm = B.get("direction_bias"), M.get("direction_bias")
    if db:
        feet = db.get("feet", {})
        ys = set()
        for f, v in feet.items():
            ys |= {int(y) for y in v.get("stage_a", {}).get("per_year", {})}
        rep.check("O-11a", ys == years_all and set(feet) == {str(f) for f in FEET},
                  f"feet {sorted(feet)} / stage_a.per_year の年集合 {sorted(ys)}(期待 2017..2026)")
        if dm and "1" in feet:
            ref = dm["venue"]["1"]["binance"]
            py = feet["1"]["stage_a"]["per_year"]
            got = {k: year_sum(py, {2017, 2018, 2019}, k) for k in ("buy", "sell", "tie")}
            exp = ref["stage_a"]["trunc"]
            rep.check("O-11b", got == exp, f"1 分足・2017〜2019 の段 A(切り捨てあり)= 既存 venue.binance: {got} vs {exp}"
                                           "(落とした行は全て同値足なので 1 分足では厳密に一致するはず)")
            bad = {}
            for g, gv in feet["1"]["gates"].items():
                gp = gv.get("per_year", {})
                got = (year_sum(gp, {2017, 2018, 2019}, "buy"), year_sum(gp, {2017, 2018, 2019}, "sell"))
                exp = (ref["gates"][g]["sig_buy"], ref["gates"][g]["sig_sell"])
                if got != exp:
                    bad[g] = (got, exp)
            rep.check("O-11c", not bad, f"1 分足・2017〜2019 の段 B(門ごとの買い/売り)= 既存 venue.binance.gates: 不一致 {len(bad)}/{len(feet['1']['gates'])}"
                                        + (f" {bad}" if bad else ""))
            for f in ("3", "60"):
                if f in feet:
                    ref = dm["venue"][f]["binance"]["stage_a"]["trunc"]
                    py = feet[f]["stage_a"]["per_year"]
                    got = {k: year_sum(py, {2017, 2018, 2019}, k) for k in ("buy", "sell", "tie")}
                    rep.info("O-11d", f"{f} 分足・2017〜2019 の段 A: 新 {got} vs 既存(落とさない版){ref} → 差 "
                                      f"{ {k: got[k] - ref[k] for k in got} }(落とすと窓の始値が変わりうるので小さな差は想定内)")
        if "venue" in db:
            rep.info("O-11e", f"binance/direction_bias.json に venue セクションあり: キー {list(db['venue'].get('1', {}).keys()) if isinstance(db['venue'], dict) else '?'}"
                              "(何と何を比べたものかを実装者の報告と照合すること)")
        if facts and "1" in feet:
            py = feet["1"]["stage_a"]["per_year"]
            bad = []
            for y in sorted(years_all):
                mine = facts["dirc"].get(y)
                got = py.get(str(y))
                if mine is None or got is None:
                    bad.append(f"{y}: 無し")
                    continue
                if (got["buy"], got["sell"], got["tie"], got["n"]) != (mine["buy"], mine["sell"], mine["tie"], mine["signed"]):
                    bad.append(f"{y}: 実装 {(got['buy'], got['sell'], got['tie'], got['n'])} vs 検査者 {(mine['buy'], mine['sell'], mine['tie'], mine['signed'])}")
            rep.check("O-11f", not bad, f"1 分足・年別の段 A を検査者の再実装(列名で読み、§1.3 を独立に書いた)と突合: 不一致 {len(bad)}(期待 0)"
                                        + (" " + "; ".join(bad[:4]) if bad else ""))
            bad = []
            for g in MY_GATES:
                gv = feet["1"]["gates"].get(g)
                if gv is None:
                    bad.append(f"{g}: 出力に無し")
                    continue
                for y in sorted(years_all):
                    mine = facts["gatec"].get((g, y), Counter())
                    got = gv["per_year"].get(str(y), {})
                    if (got.get("buy", 0), got.get("sell", 0)) != (mine["buy"], mine["sell"]):
                        bad.append(f"{g}/{y}: 実装 {(got.get('buy'), got.get('sell'))} vs 検査者 {(mine['buy'], mine['sell'])}")
            rep.check("O-11g", not bad, f"1 分足・年別の段 B({', '.join(MY_GATES)})を検査者の再実装と突合: 不一致 {len(bad)}(期待 0)"
                                        + (" " + "; ".join(bad[:4]) if bad else ""))
            tot = feet["1"]["gates"].get("s19/b24", {})
            mine_strong = sum(facts["gatec"][(("s19/b24"), y)]["strong_buy"] + facts["gatec"][("s19/b24", y)]["strong_sell"] for y in years_all)
            rep.check("O-11h", tot.get("strong_buy", -1) + tot.get("strong_sell", -1) == mine_strong,
                      f"s19/b24 の強い(全期間)= 実装 {tot.get('strong_buy')}+{tot.get('strong_sell')} vs 検査者 {mine_strong}")
    if dm and facts:
        ref = dm["venue"]["1"]["binance"]
        w = facts["win_dir"]
        got = {"buy": w["buy"], "sell": w["sell"], "tie": w["tie"]}
        rep.check("O-12a", got == ref["stage_a"]["trunc"] and w["signed"] == ref["stage_a"]["signed"],
                  f"検査者の再実装(落とす版)vs 既存 venue.binance(落とさない版)、1 分足・窓 2017-08-17〜2019: {got} vs {ref['stage_a']['trunc']}")
        bad = {g: (dict(facts['win_gate'][g]), ref["gates"][g]) for g in MY_GATES
               if (facts["win_gate"][g]["buy"], facts["win_gate"][g]["sell"]) != (ref["gates"][g]["sig_buy"], ref["gates"][g]["sig_sell"])}
        rep.check("O-12b", not bad, f"同上、門ごと: 不一致 {len(bad)}/{len(MY_GATES)}" + (f" {bad}" if bad else ""))

    # ---- O-11i: 年別の同点率(int() 切り捨ての効き方が年で変わる事実。解釈はしない)
    if db and "1" in db.get("feet", {}):
        py = db["feet"]["1"]["stage_a"]["per_year"]
        tie = {y: round(v["tie"] / v["n"], 3) for y, v in sorted(py.items()) if v.get("n")}
        rep.info("O-11i", f"1 分足・年別の同点率(int() 切り捨てあり、tie/n): {tie}")
        if dm:
            pm = dm["feet"]["1"]["stage_a"]["per_year"]
            rep.info("O-11j", f"同 BitMEX 2017-2019: { {y: round(v['tie'] / v['n'], 3) for y, v in sorted(pm.items())} }")

    # ---- O-14: 実装者の data_quality.json と検査者の走査の突合
    dq = load_json(bdir / "data_quality.json")
    if dq is None:
        rep.na("O-14", f"{bdir / 'data_quality.json'} 未生成")
    elif facts:
        exp = {"rows_read": facts["rows"], "rows_n_trades_0": facts["n_trades_eq0"], "rows_kept": facts["kept"]}
        got = {k: dq.get(k) for k in exp}
        off = dq.get("open_time_off_minute", {}).get("count")
        dupc = dq.get("duplicate_timestamps", {}).get("count")
        revc = dq.get("time_reversals_in_file_order")
        py_kept = {int(y): v.get("kept") for y, v in dq.get("per_year", {}).items()}
        ok = got == exp and off == facts["misaligned"] and dupc == 0 and revc == 0 and py_kept == facts["bars_per_foot_year"][1]
        rep.check("O-14", ok, f"data_quality.json: {got}(期待 {exp});秒≠0 {off}(期待 {facts['misaligned']});重複 {dupc} / 逆転 {revc};"
                              f" 年別 kept 一致 {py_kept == facts['bars_per_foot_year'][1]}")
        g = dq.get("gaps_over_1min_after_drop", {})
        rep.info("O-14b", f"data_quality.json の欠落は『落とした後』で数えている: {g.get('count')} 件、最大 {g.get('max_sec')} 秒"
                          f"(検査者: 落とす前 {len(facts['gaps'])} 件 / 落とした後の 1 分バケット間隔≠60s {sum(1 for a, b in zip(facts['bucket_ts'][1], facts['bucket_ts'][1][1:]) if b - a != 60):,} 箇所)。"
                          "設計書 §1 の『1 分を超える欠落』がどちらを指すかは設計書に無い")
    else:
        rep.na("O-14", "データ走査を飛ばしたので期待値が無い")

    # ---- O-15(申告 7): 出力のメタ(load)が 6 本で同一、セル数、ファイルの時刻順
    loads = {n: json.dumps(B[n].get("load"), sort_keys=True) for n in OUTPUTS if B.get(n)}
    exp_load = json.dumps({"source": "binance", "rows": 4722076, "rows_read": 4746079,
                           "dropped_n_trades_0": 24003, "open_time_off_minute": 21521}, sort_keys=True)
    ncell = {n: len(B[n].get("cells", {})) for n in OUTPUTS if B.get(n)}
    exp_cells = {"effect": 234, "signal_horizon": 1638, "signal_horizon_notrunc": 1638, "exit_ablation": 936, "direction_bias": 0}
    mt = {n: (bdir / f"{n}.json").stat().st_mtime for n in OUTPUTS if (bdir / f"{n}.json").exists()}
    order_ok = (mt.get("effect", 0) < mt.get("exit_ablation", 1e18)) and (mt.get("signal_horizon", 0) < mt.get("body_wick", 1e18))
    rep.check("O-15", all(v == exp_load for v in loads.values()) and len(loads) == 6
              and all(ncell.get(k) == v for k, v in exp_cells.items()) and order_ok,
              f"load メタが 6 本とも同一かつ期待どおり: {all(v == exp_load for v in loads.values())}({len(loads)} 本);"
              f" セル数 {ncell}; 参照される側が先に書かれている(effect<exit_ablation, signal_horizon<body_wick): {order_ok};"
              f" mtime(UTC) { {n: datetime.fromtimestamp(v, timezone.utc).strftime('%H:%M:%S') for n, v in mt.items()} }")
    for n in ("body_wick", "exit_ablation"):
        if B.get(n):
            rep.info(f"O-15b-{n}", f"reference = {B[n].get('reference')}")

    # ---- O-13: TABLES.md
    t = bdir / "TABLES.md"
    if t.exists():
        txt = t.read_text("utf-8", errors="replace")
        yrs = [y for y in range(2017, 2027) if str(y) in txt]
        dash_rows = sum(1 for l in txt.splitlines() if re.match(r"\|\s*\d+ 分\s*\|[^|]*\|\s*20\d\d\s*\|\s*—\s*\|", l))
        rep.check("O-13", yrs == list(range(2017, 2027)) and "+1335%" not in txt and dash_rows > 0,
                  f"TABLES.md({len(txt):,} 文字): 含む年 {yrs}(期待 2017..2026); 相場ラベル '+1335%' {'あり' if '+1335%' in txt else '無し'}(期待 無し);"
                  f" 相場列が '—' の行 {dash_rows}(申告 5)")
    else:
        rep.na("O-13", f"{t} 未生成")


# ------------------------------------------------------------------ main ----

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-data", action="store_true")
    ap.add_argument("--skip-loader-full", action="store_true")
    ap.add_argument("--bitmex-rerun-dir", default=None)
    ap.add_argument("--binance-dir", default=str(K1 / "binance"))
    args = ap.parse_args()
    sys.path.insert(0, str(REPO / "scripts"))

    rep = Report()
    print(f"K1-B 独立検査 {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC / TZ={os.environ.get('TZ', '')!r} / python {sys.version.split()[0]}")
    print("前提: 落とすのは n_trades==0 の行。足の時刻は open_time(UTC)。合否はセル内の数値の解釈を含まない。\n")

    facts = None
    print("== D: データ(Binance 1m 全走査、BitMEX 標本日)")
    if not args.skip_data:
        facts = scan_data(rep)
        scan_bitmex_ticks(rep)
    else:
        rep.na("D-*", "--skip-data")

    print("\n== L: 実装者の loader(scripts/k1_source.py)")
    check_loader(rep, facts, full=not args.skip_loader_full)

    print("\n== S: 差分・静的")
    check_static(rep)

    print("\n== R: BitMEX 再現ゲート(--source bitmex の再実行 vs コミット済み)")
    check_bitmex_regression(rep, Path(args.bitmex_rerun_dir) if args.bitmex_rerun_dir else None)

    print("\n== O: Binance の出力")
    check_outputs(rep, Path(args.binance_dir), facts)

    print("\n== 集計")
    for v in ("合格", "不合格", "判定不能", "情報"):
        print(f"  {v}: {rep.counts[v]}")
    if rep.counts["不合格"]:
        print("  不合格:")
        for cid, v, m in rep.rows:
            if v == "不合格":
                print(f"    {cid}: {m[:160]}")
    return 1 if rep.counts["不合格"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
