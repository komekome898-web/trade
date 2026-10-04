#!/usr/bin/env python3
"""O1 対象の形: マチルダ M-A = `MatildaLimitSim(fill_side=…, ratio_gate_mode="rolling", exit_form="center", entry=4, exit_setting=3)` の良い側と悪い側。過去だけの門の履歴のため、足は 2022-07-01 から流し、6 日(UTC の 0:00〜24:00)の中の足だけを数える。
O2 決まらない足: シミュレーターが「決まらない足」とした足(`_bar` の 3.)。その足で、上が先の道(始値 → 高値 → 安値)と下が先の道(始値 → 安値 → 高値)のどちらを採ったかを、良い側・悪い側それぞれで記録する(悪い側が「利確の手前で止めた道」を採ったときは、止めた道の向きを記録する)。
O3 本当の順序: その分(UTC の分)の約定の記録で、分の中の最高値の最初の約定の時刻と、最安値の最初の約定の時刻を比べ、最高値が先なら「上が先」、最安値が先なら「下が先」。約定が 2 件未満、または最高値と最安値が同じ時刻なら「決まらない」。
O4 一致: 決まらない足ごとに、良い側が採った道・悪い側が採った道が、本当の順序と一致したか。出すもの: 6 日の合計と日ごとに、決まらない足の数・本当の順序が決まった数・良い側が一致した数と割合(Wilson の 95% 区間)・悪い側が一致した数と割合(同)。
O5 足の食い違い: 1 分足の高値・安値と、約定の記録の分の最高値・最安値が違う分の数を並べて出す(足の作り方の違い。除かない)。
O6 境は置かない。どちらの側を主にするかは書かない(リードが読む)。
"""
# 走らせ(読むだけ・冪等・ネットワークなし。出力に時刻・所要時間は入れない):
#     PYTHONPATH=src python3 scripts/w4_measure/c4_w6b_order.py [--out docs/RESEARCH/WINDOW1/W6B_PRESEAL]
# 約定の記録は下の TRADE_FILES の 6 日だけ(2023 年。窓の中の 2024 年のファイルは開かない。名前が表に無ければ拒む)。
# 1 分足は common.load_bars の既定(封印の門のまま。終わりは 2023-12-02T00:00Z で、2023-12-18 より前)。
# 台本の決め(委任文に書いていない所。TABLES.md の「測り方の補足」に同じ文を出す):
#   - 決まらない足は、良い側と悪い側で別々に数える(2 つのシミュレーターは持ち高が分かれるので、足の集合が違う)。
#   - 記録の path が "same"(2 本の道の出来事が同じ = 反対の入りで閉じた後の分かれ目)の足は、道が分かれないので
#     一致の数え(分母・分子)に入れない。数は別の列に出す。
#   - 約定の分は `timestamp`(マイクロ秒)を UTC の分に切る。同じ時刻の複数の行(同じ注文の約定)は、最高値・最安値それぞれの
#     行の中で最も早い時刻を「最初の約定の時刻」とする(ファイルの行の順に頼らない)。
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from common import FX_DIR, MIN_NS, NS, ROOT, iso, load_bars, to_iso  # noqa: E402

from bot.research.matilda_limit_sim import MatildaLimitSim  # noqa: E402

TRADE_DIR = "data/tardis/bitflyer_FX_BTC_JPY_trades"
TRADE_FILES = tuple(f"FX_BTC_JPY_2023{md}.csv.gz" for md in ("0701", "0801", "0901", "1001", "1101", "1201"))
START = "2022-07-01T00:00:00Z"  # 足を流し始める日(過去だけの門の 365 日の履歴のため)
END = "2023-12-02T00:00:00Z"  # 6 日目(2023-12-01)の終わり
SIM_KW = {"ratio_gate_mode": "rolling", "exit_form": "center", "entry": 4, "exit_setting": 3}
SIDES = ("good", "bad")
US_PER_MIN = 60_000_000
Z95 = 1.959963984540054
OUT_DEFAULT = os.path.join(ROOT, "docs/RESEARCH/WINDOW1/W6B_PRESEAL")


def day_of(name: str) -> str:
    """ファイル名 FX_BTC_JPY_YYYYMMDD.csv.gz の日付(UTC)。表に無い名前は拒む。"""
    if name not in TRADE_FILES:
        raise SystemExit(f"拒否: 約定のファイル {name!r} は使う 6 日の表に無い(2024 年のファイルは開かない)")
    d = name[len("FX_BTC_JPY_"):len("FX_BTC_JPY_") + 8]
    return f"{d[:4]}-{d[4:6]}-{d[6:]}"


def day_ns(day: str) -> int:
    return iso(day + "T00:00:00Z")


# ---------------------------------------------------------------- O3 本当の順序
class MinuteAgg:
    """1 分の約定の集計: 件数・最高値とその最初の約定の時刻・最安値とその最初の約定の時刻(時刻はマイクロ秒)。"""
    __slots__ = ("n", "hi", "t_hi", "lo", "t_lo")

    def __init__(self) -> None:
        self.n, self.hi, self.t_hi, self.lo, self.t_lo = 0, None, None, None, None

    def add(self, ts: int, px: float) -> None:
        self.n += 1
        if self.hi is None or px > self.hi:
            self.hi, self.t_hi = px, ts
        elif px == self.hi and ts < self.t_hi:
            self.t_hi = ts
        if self.lo is None or px < self.lo:
            self.lo, self.t_lo = px, ts
        elif px == self.lo and ts < self.t_lo:
            self.t_lo = ts

    def order(self) -> str:
        """"up"(最高値が先)・"down"(最安値が先)・"none"(2 件未満、または最高値と最安値の最初の約定が同じ時刻)。"""
        if self.n < 2 or self.t_hi == self.t_lo:
            return "none"
        return "up" if self.t_hi < self.t_lo else "down"


def minute_order(trades) -> str:
    """(ts_us, price) の並び(順不同)から、その分の本当の順序。"""
    m = MinuteAgg()
    for ts, px in trades:
        m.add(ts, px)
    return m.order()


def read_trade_minutes(name: str) -> dict:
    """1 日のファイルを読み、UTC の分の始まり(ns)→ MinuteAgg。日の外の時刻の行があれば拒む。"""
    day = day_of(name)
    lo_us, hi_us = day_ns(day) // 1000, day_ns(day) // 1000 + 86_400 * 1_000_000
    out: dict = {}
    with gzip.open(os.path.join(ROOT, TRADE_DIR, name), "rt", encoding="utf-8", newline="") as fh:
        head = fh.readline().rstrip("\n").split(",")
        i_ts, i_px = head.index("timestamp"), head.index("price")
        for line in fh:
            f = line.rstrip("\n").split(",")
            ts, px = int(f[i_ts]), float(f[i_px])
            if not lo_us <= ts < hi_us:
                raise SystemExit(f"拒否: {name} に日 {day} の外の時刻の行がある({ts})")
            out.setdefault(ts // US_PER_MIN * MIN_NS, MinuteAgg()).add(ts, px)
    return out


def md5_check(name: str) -> dict:
    """MD5SUMS の該当行(その行だけを読む)と、ファイルの md5 の照合。"""
    day_of(name)
    want = None
    with open(os.path.join(ROOT, TRADE_DIR, "MD5SUMS"), encoding="utf-8") as fh:
        for line in fh:
            h, _, n = line.strip().partition("  ")
            if n.lstrip("./") == name:
                want = h
    h = hashlib.md5()
    with open(os.path.join(ROOT, TRADE_DIR, name), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return {"md5": h.hexdigest(), "md5sums": want, "match": h.hexdigest() == want}


# ---------------------------------------------------------------- O4 一致の数え方
def wilson(k: int, n: int, z: float = Z95):
    """Wilson の区間(95%)。n = 0 は None。"""
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [c - h, c + h]


def _empty() -> dict:
    return {"undecided": 0, "same": 0, "truth_decided": 0, "truth_up": 0, "truth_down": 0, "compared": 0, "match": 0,
            "ratio": None, "wilson": None}


def count_matches(log: list, truth: dict, in_range) -> dict:
    """記録 log(各要素 {"start_ns", "path", "kind"})を、範囲 in_range(start_ns)の足だけ、本当の順序 truth(分の始まり ns → "up"/"down"/"none")
    と照合する。truth に無い分は "none" 扱い。
      undecided      範囲内の記録の数(決まらない足)
      same           そのうち path = "same"(道が分かれない)
      truth_decided  そのうち本当の順序が決まった(up / down)足(same を含む全体)
      truth_up/down  その内訳
      compared       道が分かれ(same でなく)、本当の順序が決まった足 = 一致の数えの分母
      match          そのうち path が本当の順序と同じ足"""
    r = _empty()
    for e in log:
        if not in_range(e["start_ns"]):
            continue
        r["undecided"] += 1
        t = truth.get(e["start_ns"], "none")
        if t != "none":
            r["truth_decided"] += 1
            r["truth_" + t] += 1
        if e["path"] == "same":
            r["same"] += 1
        elif t != "none":
            r["compared"] += 1
            r["match"] += e["path"] == t
    if r["compared"]:
        r["ratio"] = r["match"] / r["compared"]
    r["wilson"] = wilson(r["match"], r["compared"])
    return r


def add_counts(rows: list) -> dict:
    """日ごとの数え(count_matches の出力)の合計。割合と区間は合計の数から作り直す。"""
    r = _empty()
    for x in rows:
        for k in ("undecided", "same", "truth_decided", "truth_up", "truth_down", "compared", "match"):
            r[k] += x[k]
    if r["compared"]:
        r["ratio"] = r["match"] / r["compared"]
    r["wilson"] = wilson(r["match"], r["compared"])
    return r


# ---------------------------------------------------------------- O5 足の食い違い
def count_mismatch(bars: dict, minutes: dict, in_range) -> dict:
    """bars: 分の始まり(ns)→ (高値, 安値)。minutes: 分の始まり(ns)→ MinuteAgg。範囲内の分を数える。
    both = 両方にある分。hi_diff / lo_diff / any_diff = そのうち高値 / 安値 / どちらかが違う分。bars_only / trades_only = 片方にだけある分。"""
    keys = [k for k in set(bars) | set(minutes) if in_range(k)]
    r = {"both": 0, "hi_diff": 0, "lo_diff": 0, "any_diff": 0, "bars_only": 0, "trades_only": 0}
    for k in keys:
        if k in bars and k in minutes:
            r["both"] += 1
            hd, ld = bars[k][0] != minutes[k].hi, bars[k][1] != minutes[k].lo
            r["hi_diff"] += hd
            r["lo_diff"] += ld
            r["any_diff"] += hd or ld
        elif k in bars:
            r["bars_only"] += 1
        else:
            r["trades_only"] += 1
    return r


def mismatch_in_undecided(log: list, bars: dict, minutes: dict, in_range) -> dict:
    """その側の決まらない足(範囲内)のうち、足と約定の記録の両方がある分の数と、高値・安値が違う数。"""
    r = {"undecided": 0, "both": 0, "any_diff": 0}
    for e in log:
        k = e["start_ns"]
        if not in_range(k):
            continue
        r["undecided"] += 1
        if k in bars and k in minutes:
            r["both"] += 1
            r["any_diff"] += bars[k][0] != minutes[k].hi or bars[k][1] != minutes[k].lo
    return r


def by_kind(log: list, truth: dict, in_range) -> dict:
    out: dict = {}
    for kind in sorted({e["kind"] for e in log if in_range(e["start_ns"])}):
        out[kind] = count_matches([e for e in log if e["kind"] == kind], truth, in_range)
    return out


# ---------------------------------------------------------------- 表
def pct(r) -> str:
    return "—" if r["ratio"] is None else f"{r['ratio'] * 100:.1f}%"


def ci(r) -> str:
    w = r["wilson"]
    return "—" if w is None else f"[{w[0] * 100:.1f}%, {w[1] * 100:.1f}%]"


def render(res: dict) -> str:
    days = res["days"]
    L = ["# W6b 順序の確かめ(封印の前の 6 日)", "",
         "数字はすべて `scripts/w4_measure/c4_w6b_order.py` が出した(手で書いていない)。読み方の決まり O1〜O6 は台本の docstring の冒頭。"
         "読みは書かない(O6)。", "",
         "## 測り方の補足(台本の決め。委任文に書いていない所)", "",
         "- 決まらない足は、良い側と悪い側で別々に数える(2 つのシミュレーターは持ち高が分かれるので、足の集合が違う)。",
         "- 記録の道が「両方同じ扱い」(2 本の道の出来事が同じ。反対の入りで閉じた後の分かれ目)の足は、道が分かれないので一致の数え"
         "(分母・分子)に入れず、別の列に出す。",
         "- 約定の分は `timestamp`(マイクロ秒)を UTC の分に切る。同じ時刻の複数の行は、最高値・最安値それぞれの行の中で最も早い時刻を"
         "「最初の約定の時刻」とする。",
         "- 「本当の順序が決まった」= 約定の記録でその分が「上が先」か「下が先」になった足(両方同じ扱いの足を含む全体)。"
         "「照合の対象」= 道が分かれ(両方同じ扱いでなく)、本当の順序が決まった足。一致の割合 = 一致 / 照合の対象。", "",
         "## 入力", "",
         f"- 1 分足: `{FX_DIR}`、{res['bars_range'][0]} 〜 {res['bars_range'][1]}(終わりは含まない)、"
         f"読んだ足 {res['bars_loaded']} 本、異常の種類 {json.dumps(res['bar_anomalies'], ensure_ascii=False)}",
         f"- 形: `MatildaLimitSim(fill_side=…, " + ", ".join(f"{k}={v!r}" for k, v in SIM_KW.items()) + ")`",
         "- 約定の記録(`" + TRADE_DIR + "`):", ""]
    L += ["| 日(UTC) | ファイル | md5 が MD5SUMS と一致 | 行数 | 約定のある分 |", "|---|---|---|---|---|"]
    for d in days:
        v = res["trade_files"][d]
        L.append(f"| {d} | {v['file']} | {v['md5']['match']} | {v['rows']} | {v['minutes']} |")
    L += ["", "- 過去だけの門の日: 6 日それぞれで門が掛かった(境が None でない)か: "
          + ", ".join(f"{s} {res['gate'][s]}" for s in SIDES), ""]

    for s in SIDES:
        L += [f"## O4 一致: {'良い側' if s == 'good' else '悪い側'}({s})", "",
              "| 日(UTC) | 決まらない足 | 両方同じ扱い | 本当の順序が決まった | 照合の対象 | 一致 | 割合 | Wilson 95% |",
              "|---|---|---|---|---|---|---|---|"]
        for d in days + ["合計"]:
            r = res["sides"][s]["by_day"].get(d) if d != "合計" else res["sides"][s]["total"]
            L.append(f"| {d} | {r['undecided']} | {r['same']} | {r['truth_decided']} | {r['compared']} | {r['match']} "
                     f"| {pct(r)} | {ci(r)} |")
        L += ["", "本当の順序が決まった足の内訳(上が先 / 下が先): "
              + " / ".join(f"{d} {res['sides'][s]['by_day'][d]['truth_up']}・{res['sides'][s]['by_day'][d]['truth_down']}"
                           for d in days)
              + f" / 合計 {res['sides'][s]['total']['truth_up']}・{res['sides'][s]['total']['truth_down']}", ""]
        L += [f"決まらない足の場合分け(6 日の合計。`kind` は記録の口の分類):", "",
              "| 場合 | 決まらない足 | 両方同じ扱い | 本当の順序が決まった | 照合の対象 | 一致 | 割合 | Wilson 95% |",
              "|---|---|---|---|---|---|---|---|"]
        for k, r in res["sides"][s]["by_kind"].items():
            L.append(f"| {k} | {r['undecided']} | {r['same']} | {r['truth_decided']} | {r['compared']} | {r['match']} "
                     f"| {pct(r)} | {ci(r)} |")
        L.append("")

    L += ["## O5 足の食い違い(1 分足と約定の記録の分の高値・安値)", "",
          "| 日(UTC) | 両方にある分 | 高値が違う | 安値が違う | どちらかが違う | 足だけにある分 | 約定の記録だけにある分 |",
          "|---|---|---|---|---|---|---|"]
    for d in days + ["合計"]:
        r = res["mismatch"]["by_day"].get(d) if d != "合計" else res["mismatch"]["total"]
        L.append(f"| {d} | {r['both']} | {r['hi_diff']} | {r['lo_diff']} | {r['any_diff']} | {r['bars_only']} | {r['trades_only']} |")
    L += ["", "決まらない足(6 日の合計)の中で、足と約定の記録の両方がある分のうち、高値・安値のどちらかが違う分(O4 の数えから除いていない):", "",
          "| 側 | 決まらない足 | 両方にある分 | どちらかが違う |", "|---|---|---|---|"]
    for s in SIDES:
        r = res["sides"][s]["mismatch_undecided"]
        L.append(f"| {s} | {r['undecided']} | {r['both']} | {r['any_diff']} |")
    L += ["", "## 全期間の決まらない足の数(足を流した全体。参考の数)", "",
          "| 側 | 決まらない足(シミュレーターの数え) | 記録の口の件数 |", "|---|---|---|"]
    for s in SIDES:
        L.append(f"| {s} | {res['sides'][s]['undecided_bars_all']} | {res['sides'][s]['log_len_all']} |")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- 本体
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_DEFAULT)
    a = ap.parse_args()
    days = [day_of(n) for n in TRADE_FILES]
    day_starts = [day_ns(d) for d in days]

    def in_days(ns: int) -> bool:
        return any(s <= ns < s + 86_400 * NS for s in day_starts)

    def in_day(i: int):
        s = day_starts[i]
        return lambda ns: s <= ns < s + 86_400 * NS

    # 約定の記録(6 日だけ)
    minutes: dict = {}
    tfiles: dict = {}
    for n, d in zip(TRADE_FILES, days):
        m = read_trade_minutes(n)
        minutes.update(m)
        md5 = md5_check(n)
        if not md5["match"]:
            raise SystemExit(f"拒否: {n} の md5 が MD5SUMS と違う")
        rows = 0
        with gzip.open(os.path.join(ROOT, TRADE_DIR, n), "rt", encoding="utf-8") as fh:
            rows = sum(1 for _ in fh) - 1
        tfiles[d] = {"file": n, "md5": md5, "rows": rows, "minutes": len(m)}
    truth = {k: m.order() for k, m in minutes.items()}

    # 1 分足を 2 つのシミュレーターに流す(封印の門の既定の呼び方。年ごとに区切る)
    lo, hi = iso(START), iso(END)
    cut = iso("2023-01-01T00:00:00Z")
    logs = {s: [] for s in SIDES}
    sims = {s: MatildaLimitSim(fill_side=s, undecided_log=logs[s], **SIM_KW) for s in SIDES}
    bars_6: dict = {}
    n_bars, kinds_all, hashes = 0, {}, {}
    for x, y in ((lo, cut), (cut, hi)):
        bars, kinds, h = load_bars(FX_DIR, "FX_BTC_JPY", x, y)
        hashes.update(h)
        for k, v in kinds.items():
            kinds_all[k] = kinds_all.get(k, 0) + v
        n_bars += len(bars)
        for b in bars:
            st = int(b.start_time_ns)
            if in_days(st):
                bars_6[st] = (float(b.high), float(b.low))
            for s in SIDES:
                sims[s].feed(b)
        del bars

    res = {"days": days, "bars_range": [to_iso(lo), to_iso(hi)], "bars_loaded": n_bars, "bar_anomalies": kinds_all,
           "bar_files": hashes, "sim_kw": SIM_KW, "trade_files": tfiles, "sides": {}, "gate": {}}
    for s in SIDES:
        sim = sims[s]
        res["gate"][s] = {d: sim.rolling_edges.get(ds // (86_400 * NS)) is not None for d, ds in zip(days, day_starts)}
        by_day = {d: count_matches(logs[s], truth, in_day(i)) for i, d in enumerate(days)}
        res["sides"][s] = {"by_day": by_day, "total": add_counts(list(by_day.values())),
                           "by_kind": by_kind(logs[s], truth, in_days),
                           "mismatch_undecided": mismatch_in_undecided(logs[s], bars_6, minutes, in_days),
                           "undecided_bars_all": sim.undecided_bars, "log_len_all": len(logs[s])}
    mm_day = {d: count_mismatch(bars_6, minutes, in_day(i)) for i, d in enumerate(days)}
    tot = {k: sum(x[k] for x in mm_day.values()) for k in next(iter(mm_day.values()))}
    res["mismatch"] = {"by_day": mm_day, "total": tot}

    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "w6b.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(res, ensure_ascii=False, sort_keys=True, indent=1, allow_nan=False) + "\n")
    with open(os.path.join(a.out, "TABLES.md"), "w", encoding="utf-8") as fh:
        fh.write(render(res))
    print(f"書いた: {a.out}(足 {n_bars} 本)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
