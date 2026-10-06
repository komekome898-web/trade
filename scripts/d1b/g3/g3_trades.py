"""# 10(D1B_FRAMINGS の行 10)の約定の記録の読み口: bitFlyer FX_BTC_JPY の封印の前の 6 日(2023 年の各月 1 日、7〜12 月)。

読むのは `scripts/w4_measure/c4_w6b_order.py` の TRADE_FILES(6 日)の名前だけ。表に無い名前(2024 年の 10 日を含む)は
`c4_w6b_order.day_of` が拒む(写さずに import)。md5 は同じ台本の `md5_check` で MD5SUMS と照合し、違えば拒む。
c4_w6b_order.read_trade_minutes は約定の側(列 side)を捨てるので、側と行の並びを持つ読み口をここに置く。

列(tardis の bitFlyer の約定の CSV。見出しは exchange,symbol,timestamp,local_timestamp,id,side,price,amount):
  timestamp = 取引所の時刻(マイクロ秒、UTC)。side = buy / sell / unknown = 成行の側(約定を起こした側)。
  出所(批評家 1 回目の確かめ、`docs/AUDITOR/VERDICTS/2026-10-06_d1b_g3_critic1.md` の「打ったコマンドと出力の要点」3):
  (a) tardis の資料 docs.tardis.dev/downloadable-csv-files/data-types の定義「liquidity taker side (aggressor) …
  buy - liquidity taker was buying」(批評家が読んだ。この台本の作り手は外のサイトを見ていない)、(b) 2023-07-01 のファイルで、
  同じ 1 秒の中で続く 2 件の値段の動き: buy→buy は上 6725・下 514、sell→sell は上 410・下 6892、sell→buy は上 783・下 240、
  buy→sell は上 177・下 839 = buy は売り板(上)・sell は買い板(下)で付く。
並び: (timestamp, id) の昇順に並べ直す(ファイルの行の順に頼らない。6 日のファイルに時刻が前の行より小さい行が計 5 行ある。
  この回の awk の数え: 0701 0・0801 1・0901 0・1001 1・1101 2・1201 1)。
側の数: buy = +1、sell = −1、unknown = 0(側の割合の分母から外し、数は別に出す)。
"""
from __future__ import annotations

import gzip
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
W4 = os.path.join(os.path.dirname(os.path.dirname(HERE)), "w4_measure")
sys.path.insert(0, W4)

from c4_w6b_order import TRADE_DIR, TRADE_FILES, day_of, md5_check, minute_order  # noqa: E402
from common import MIN_NS, NS, ROOT, iso  # noqa: E402

US = 1_000  # ns / µs
DAY_NS = 86_400 * NS
SIDE_CODE = {"buy": 1, "sell": -1, "unknown": 0}


class DayTrades:
    """1 日の約定(時刻 ns・側・値段)。分の始まり(ns)→ その分の行の範囲 [i0, i1)。"""

    def __init__(self, day: str, ts_ns: np.ndarray, side: np.ndarray, px: np.ndarray) -> None:
        self.day = day
        self.day_ns = iso(day + "T00:00:00Z")
        self.ts, self.side, self.px = ts_ns, side, px
        self.minutes: dict = {}
        if len(ts_ns):
            m = ts_ns // MIN_NS * MIN_NS
            cut = np.flatnonzero(np.diff(m)) + 1
            starts = np.concatenate([[0], cut])
            ends = np.concatenate([cut, [len(m)]])
            for a, b in zip(starts.tolist(), ends.tolist()):
                self.minutes[int(m[a])] = (a, b)

        # 側ごとの「行 i 以後で、その側の最初の行」(無ければ −1)。行の順(時刻・id の昇順)で後ろから作る
        self._next_side = {}
        for sd in (1, -1):
            nxt = np.full(len(ts_ns) + 1, -1, dtype=np.int64)
            for i in range(len(ts_ns) - 1, -1, -1):
                nxt[i] = i if side[i] == sd else nxt[i + 1]
            self._next_side[sd] = nxt

    def next_with_side(self, i: int, sd: int):
        """行 i 以後(i を含む)で、側が sd(+1 / −1)の最初の行(日の中に無ければ None)。"""
        j = int(self._next_side[sd][i])
        return None if j < 0 else j

    def hl_order_window(self, t_lo: int, t_hi: int) -> str:
        """時刻 [t_lo, t_hi) の約定だけでの高値と安値の順(決まりは hl_order と同じ。窓が日の終わりを越える分は日の中だけ)。"""
        a = int(np.searchsorted(self.ts, t_lo, side="left"))
        b = int(np.searchsorted(self.ts, t_hi, side="left"))
        return minute_order(zip((self.ts[a:b] // US).tolist(), self.px[a:b].tolist()))

    def in_day(self, t_ns: int) -> bool:
        return self.day_ns <= t_ns < self.day_ns + DAY_NS

    def first_in_minute(self, m_ns: int):
        """その分の最初の約定の行番号(約定が無ければ None)。"""
        r = self.minutes.get(m_ns)
        return None if r is None else r[0]

    def first_at_or_after(self, t_ns: int):
        """時刻 t 以後の最初の約定の行番号(日の中に無ければ None)。"""
        i = int(np.searchsorted(self.ts, t_ns, side="left"))
        return None if i >= len(self.ts) else i

    def hl_order(self, m_ns: int) -> str:
        """その分の高値と安値の順。c4_w6b_order.minute_order(O3 の決まり)をそのまま使う:
        "up" = 最高値の最初の約定が先、"down" = 最安値の最初の約定が先、"none" = 約定 2 件未満か同じ時刻。"""
        r = self.minutes.get(m_ns)
        if r is None:
            return "none"
        a, b = r
        return minute_order(zip((self.ts[a:b] // US).tolist(), self.px[a:b].tolist()))

    def hi_lo(self, m_ns: int):
        r = self.minutes.get(m_ns)
        if r is None:
            return None
        a, b = r
        return float(self.px[a:b].max()), float(self.px[a:b].min())

    def zigzag(self, m_ns: int) -> list:
        """その分の値段の道(行の順の値段から、向きが変わる点だけを残す)。[最初の約定の値段, 折り返し…, 最後の値段]。
        同じ値段が続く行は 1 つにまとめる。約定が無ければ []。"""
        r = self.minutes.get(m_ns)
        if r is None:
            return []
        a, b = r
        pts: list = []
        for p in self.px[a:b].tolist():
            if pts and p == pts[-1]:
                continue
            if len(pts) >= 2 and (pts[-1] - pts[-2]) * (p - pts[-1]) > 0:
                pts[-1] = p  # 同じ向きに進んだ: 端を延ばす
            else:
                pts.append(p)
        return pts


def read_day(name: str) -> DayTrades:
    """6 日の表の 1 ファイルを読む(表に無い名前は拒む。md5 が MD5SUMS と違えば拒む。日の外の時刻の行があれば拒む)。"""
    day = day_of(name, TRADE_FILES)
    md5 = md5_check(name, TRADE_FILES)
    if not md5["match"]:
        raise SystemExit(f"拒否: {name} の md5 が MD5SUMS と違う")
    lo = iso(day + "T00:00:00Z")
    rows = []
    with gzip.open(os.path.join(ROOT, TRADE_DIR, name), "rt", encoding="utf-8", newline="") as fh:
        head = fh.readline().rstrip("\n").split(",")
        i_ts, i_id, i_sd, i_px = (head.index(k) for k in ("timestamp", "id", "side", "price"))
        for line in fh:
            f = line.rstrip("\n").split(",")
            t = int(f[i_ts]) * US
            if not lo <= t < lo + DAY_NS:
                raise SystemExit(f"拒否: {name} に日 {day} の外の時刻の行がある({f[i_ts]})")
            if f[i_sd] not in SIDE_CODE:
                raise SystemExit(f"拒否: {name} に知らない側 {f[i_sd]!r} がある")
            rows.append((t, int(f[i_id]), SIDE_CODE[f[i_sd]], float(f[i_px])))
    rows.sort(key=lambda r: (r[0], r[1]))
    ts = np.array([r[0] for r in rows], dtype=np.int64)
    sd = np.array([r[2] for r in rows], dtype=np.int8)
    px = np.array([r[3] for r in rows], dtype=float)
    return DayTrades(day, ts, sd, px)


def days() -> list:
    """6 日(UTC の日付の文字列)を表の順に。"""
    return [day_of(n, TRADE_FILES) for n in TRADE_FILES]


__all__ = ["DAY_NS", "DayTrades", "SIDE_CODE", "TRADE_FILES", "days", "read_day"]
