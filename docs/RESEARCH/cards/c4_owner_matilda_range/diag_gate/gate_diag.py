"""カード 4 の静観の門の診断(L-574)。走らせ部分。

門の無いカード(no_trend_body = trend_gate=False、range_from="body"、ほかは既定)を全期間走らせ、決定ごとに
カードの中の量(比 ratio・中心・終値)と、門の候補 2 つの「影の状態」を記録する。影の状態はカードの持ち高を
変えない(門の無いカードの持ち高は no_trend_body と同じ。照合は extra の pnl の合計で行う)。

影の状態
  fix10: カードの門そのもの(c4_owner_matilda_range.py _decide の 1. と 4.、VR_MAX = 10)を同じ順で再現。
  v37brk: v37 の break_judge / break_off_judge(docs/legacy/matilda_for_TaroCamp37.py 930-965 行、範囲と
    ブレイク判定値は 490-509 行)を 1 分足で再現。置き換えは README の表。

    PYTHONPATH=src:scripts/w4_measure python3 docs/RESEARCH/cards/c4_owner_matilda_range/diag_gate/gate_diag.py <出力の置き場>
"""
from __future__ import annotations

import math
import os
import sys
import time
from collections import deque

import numpy as np

ROOT = "/home/user/trade"
sys.path.insert(0, os.path.join(ROOT, "scripts/w4_measure"))
sys.path.insert(0, os.path.join(ROOT, "scripts/measure"))

import run_b2  # noqa: E402
from common import iso  # noqa: E402
from run_v2 import boundaries  # noqa: E402

from bot.research.cards import cardmd  # noqa: E402
from bot.research.cards.library.c4_owner_matilda_range import VR_MAX, C4OwnerMatildaRange  # noqa: E402
from bot.research.cards.pnl import pnl  # noqa: E402


class Probe(C4OwnerMatildaRange):
    """門の無いカード + 決定ごとの記録。"""

    def __init__(self):
        super().__init__(range_from="body", trend_gate=False)
        self.rec_t, self.rec_ratio, self.rec_center, self.rec_close, self.rec_width = [], [], [], [], []
        self.rec_fix10, self.rec_v37 = [], []
        self._fix10 = 0
        # v37 の範囲の 2 倍の窓(range_max2 / range_min2、494・498 行 High[-range_count*2:])
        self._b2: deque = deque()
        self._max2: deque = deque()
        self._min2: deque = deque()
        self._bup = None  # break_up_priceList[-1](初めは 9999999 = ブレイクしない、208 行)
        self._bdp = None
        self._brk = 0
        self._raw_hl = (None, None)
        self._prev_hi2 = self._prev_lo2 = self._prev_center = None

    def _push(self, start, o, h, lo, c):
        super()._push(start, o, h, lo, c)
        self._raw_hl = (h, lo)
        top, bot = max(o, c), min(o, c)
        self._b2.append(start)
        while self._max2 and self._max2[-1][1] <= top:
            self._max2.pop()
        self._max2.append((start, top))
        while self._min2 and self._min2[-1][1] >= bot:
            self._min2.pop()
        self._min2.append((start, bot))

    def _decide(self, t):
        lo_start = t - self.window_ns
        lo2 = t - 2 * self.window_ns
        while self._b2 and self._b2[0] < lo2:
            self._b2.popleft()
        while self._max2 and self._max2[0][0] < lo2:
            self._max2.popleft()
        while self._min2 and self._min2[0][0] < lo2:
            self._min2.popleft()
        super()._decide(t)  # 門なしのカードの決定(持ち高はこれだけで決まる)
        if self._first_start is None or self._first_start > lo_start or not self._bars:
            return
        hi, lo = self._maxq[0][1], self._minq[0][1]
        width = hi - lo
        center = (hi + lo) / 2.0
        vola = self._body_sum / len(self._bars)
        close = self._close
        ratio = width / vola if vola > 0 else (math.inf if width > 0 else 0.0)
        # fix10(カードの _decide の 1. と 4. と同じ)
        if ratio >= VR_MAX:
            d = (close > center) - (close < center)
            if d != 0:
                self._fix10 = d
        f10 = self._fix10
        if self._fix10 == 1 and close <= center or self._fix10 == -1 and close >= center:
            if ratio < VR_MAX:
                self._fix10 = 0
        # v37brk。v37 は確定した足(cryptowatch の before = 今の分の頭、439・552 行)で範囲と判定値を作り、
        # 次の分の間ずっと(0.6 秒ごとの巡回)生きた気配と比べる。1 分足では「今の足 k の間の値段」を、
        # 足 k-1 までで作った判定値と比べる: 上は足 k の高値(ヒゲを捨てない生の値)、下は安値、
        # 解けたか(break_off)は足 k の終値と、足 k-1 までの中心。b_signal は使わない(0 とみなす)。
        bh, bl = self._raw_hl
        up = self._bup is not None and self._prev_hi2 is not None
        dn = self._bdp is not None and self._prev_lo2 is not None
        if up and max(self._bup, self._prev_hi2) < bh and self._brk != 1:
            self._brk = 1
        elif dn and min(self._bdp, self._prev_lo2) > bl and self._brk != -1:
            self._brk = -1
        b37 = self._brk
        if self._prev_center is not None and (
                self._brk == 1 and close < self._prev_center or self._brk == -1 and close > self._prev_center):
            self._brk = 0
        # 足 k が確定したので、範囲と判定値を足 k までで作り直す(490-509 行)
        hi2, lo2v = self._max2[0][1], self._min2[0][1]
        if hi != hi2 or self._brk != 0:
            self._bup = hi + width / 2
        if lo != lo2v or self._brk != 0:
            self._bdp = lo - width / 2
        self._prev_hi2, self._prev_lo2, self._prev_center = hi2, lo2v, center
        self.rec_t.append(t)
        self.rec_ratio.append(ratio)
        self.rec_center.append(center)
        self.rec_close.append(close)
        self.rec_width.append(width)
        self.rec_fix10.append(f10)
        self.rec_v37.append(b37)


def main() -> int:
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    lo = iso(sys.argv[2] if len(sys.argv) > 2 else run_b2.FULL[0])
    hi = iso(sys.argv[3] if len(sys.argv) > 3 else run_b2.FULL[1])
    with open(os.path.join(ROOT, "docs/RESEARCH/cards/c4_owner_matilda_range/CARD.md"), encoding="utf-8") as fh:
        st, problems = cardmd.settings(cardmd.parse(fh.read()))
    if problems:
        raise SystemExit(problems)
    card = Probe()
    t0 = time.time()
    run, log, _ = run_b2.run_chunks(card, lo, hi, boundaries(lo, hi, "year"), dict(st.declarations))
    p = pnl(run)
    np.savez_compressed(os.path.join(out, "probe.npz"),
                        bar_t=p.t_ns, exposure=p.exposure, r_bp=p.r_bp, pnl_bp=p.pnl_bp,
                        rec_t=np.array(card.rec_t, dtype=np.int64), ratio=np.array(card.rec_ratio),
                        center=np.array(card.rec_center), close=np.array(card.rec_close),
                        width=np.array(card.rec_width), fix10=np.array(card.rec_fix10, dtype=np.int8),
                        v37=np.array(card.rec_v37, dtype=np.int8))
    print(f"終わり {time.time() - t0:.0f}s 決定 {len(p.t_ns)} 記録 {len(card.rec_t)} pnl の合計 {p.pnl_bp.sum():.3f}",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
