"""カード 9(清算の連鎖)作り直しの (a) — Binance COIN-M の値段の反応の道具(2026-10-03)。

設計: `docs/RESEARCH/cards/c9_liquidation_cascade/REDESIGN_2026-10-03.md` §3.1・§6。
走らせる口: `scripts/c9_run_a.py`。試験: `tests/research/test_liq_cascade_v2.py`。

**これは探索の道具であり、判定はしない**(§6 の 3: 作ると測るの分割はしない)。判定語を出力に
書かない。集計は分布(分位・正負の割合・日等重み平均・日クラスタ SE・日ごとの合計)で出し、
平均だけの行は作らない(L-260)。

## 前の道具から使うもの(import。写さない)

- `bot.research.liq_response`: `_read_binance_cm_rows`(生の 10 列 + 正規化)、`dedup_exact_rows`
  (全列一致を 1 件)、`build_cascades`(gap で束ねる。`gap` ちょうどは同じ束)、`LiquidationEvent`。
  数量 = `accumulated_fill_quantity`、価格 = `average_price`(設計 D-4)。`original_quantity` は
  生の行から並べて持つ(診断)。
- `scripts/o3c_oi_distance.py`: `load_agg_trades_with_maker`(約定 + `is_buyer_maker`)。
- `scripts/o3c_signal_policy.py`: `STATE_TABLE` / `next_action` / `simulate_cascade` /
  `simulate_baseline`(L-269 の状態機械。遅れは `simulate_cascade` の中で足すので、渡す
  `price_fn` は遅れを足さない生の at_or_after)。読み込みに数秒かかるので `policy_module()` で遅延。

## 前の道具から変えたもの(理由は各関数の docstring)

1. 連鎖は**同じ側だけ**で束ねる(`build_cascades` を側ごとに呼ぶ)。前の `build_cascades` は両側を
   混ぜるが、続く/止まるのラベルと L-269 の状態機械は「同じ側の次のプリント」で決まるため。
2. 連鎖の終わり = 最後のプリント + g(前は + 60 秒固定)。g を 30/60/180 で並べるため。
   最後 + g の時点では「g の間来なかった」ことが分かっているので先読みにならない。
3. 対照 (i) は「どの清算からも ±5 分以上」を守る自前の抽出(前の
   `sample_no_liquidation_windows` は窓の中だけを見て、前後の余白を見ない)。
4. 対照 (iii)(プラセボ)は、束の窓の**約定数量(枚)**と、同じ長さの無清算の窓の約定数量(枚)を
   ±25% で合わせる(前の段 0 は `total_size = 数量×価格` を約定数量のバーと比べていて単位が違う)。
5. 直前の状態(m10・m60・成行の偏り)はプリントにも対照の時刻にも同じ関数
   `pre_state_arrays` を当て、`t − 1 ms` 以前の約定だけを使う(前の Q7 の格子は `t` ちょうどの
   約定を含めていた。プリントでは `t` ちょうどの約定は清算そのものでありうるので外した)。
6. 値段の続きの 5 bp のラベルは使わない(A-12)。最大順行・最大逆行・山からの最大の戻りを出す。

## 符号(O-7: 2 つを混ぜない)

- `react_*`・`mfe_*`・`mae_*` = **清算の向き**に正(SELL = ロングの強制決済 = 下へ押す = −1)。
  対照は直前 10 秒の変位の符号を向きにする。
- `pnl_bp`・`レグ損益_bp` = **建玉の向き**に正(状態機械の出力)。
"""
from __future__ import annotations

import gzip
import importlib.util
import json
import math
import random
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

from bot.research.liq_response import (
    DedupStats,
    LiquidationEvent,
    _read_binance_cm_rows,
    build_cascades,
    dedup_exact_rows,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
DEFAULT_DATA_ROOT = REPO_ROOT / "backtest_data" / "binance_cm_o3c_20260913"
SYMBOL = "BTCUSD_PERP"
NAN = float("nan")
MS_S = 1000
MS_DAY = 86_400_000

# --------------------------------------------------------------------------- #
# 固定値(どれもオーナーの数ではない。出所を書く)
# --------------------------------------------------------------------------- #
#: 見る時間 h(秒)。設計 §3.1「1・5・10・30・60 秒、5・15・30・60・240 分、1 日、1 週」(12 本)。
HORIZONS_S: tuple[int, ...] = (1, 5, 10, 30, 60, 300, 900, 1800, 3600, 14400, 86400, 604800)
#: 束ね方 g(秒)。段 A の 30/60/180(設計 §3.1・§6 の 6)。
GAPS_S: tuple[int, ...] = (30, 60, 180)
#: 遅れ d(秒)。前の方策の段の 1(主)/ 3(併記)(設計 §3.1)。
DELAYS_S: tuple[int, ...] = (1, 3)
#: s 秒の曲線の上限 = g の最大(設計 §3.1)。
S_MAX = 180
#: 穴の防御(前の道具の `STALENESS_MS` と同じ 300 秒)。
STALENESS_MS = 300_000
#: 封印の境(設計 F-6)。COIN-M は封印の台帳に無いが、列として持つ(設計 §3.0)。
SEAL_BOUNDARY = date(2023, 12, 18)
#: 対照 (i)(iii) の「どの清算からも ±5 分以上」(段 A の対照 (i))。
CTRL_MARGIN_MS = 300_000
#: 対照 (ii) の「前後 15 分に清算無し」・10 秒刻み・10 分位(前の Q7)。
CTRL2_NO_LIQ_MS = 900_000
CTRL_GRID_MS = 10_000
CTRL2_N_BANDS = 10
#: 対照 (iii) の規模の許容(前の `sample_placebo_windows` の `size_tolerance=0.25`)。
PLACEBO_TOL = 0.25
#: 材料 1・12 の窓(前の `SAME_SIDE_WINDOW_MS`)と成行の偏りの窓(前の 5 秒)。
SAME_SIDE_WINDOW_MS = 60_000
IMB_WINDOW_MS = 5_000
#: 分布の分位(%)。
QS: tuple[int, ...] = (5, 10, 25, 50, 75, 90, 95)
SEED = 20261003

REACT_SIGN = {"SELL": -1.0, "BUY": 1.0}

# 状態機械の判断の語(前の道具の語をそのまま使う)
JUDGE_STOP, JUDGE_CONTINUE, JUDGE_UNKNOWN = "止まる", "続く", "わからない"


# --------------------------------------------------------------------------- #
# 前の道具の読み込み(遅延)
# --------------------------------------------------------------------------- #
_MODS: dict = {}


def _load_script(name: str):
    if name in _MODS:
        return _MODS[name]
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    _MODS[name] = mod
    return mod


def policy_module():
    """`scripts/o3c_signal_policy.py`(状態機械)。import に数秒かかる。"""
    return _load_script("o3c_signal_policy")


def oi_module():
    """`scripts/o3c_oi_distance.py`(約定の読み手)。"""
    return _load_script("o3c_oi_distance")


# --------------------------------------------------------------------------- #
# 日付
# --------------------------------------------------------------------------- #
def day_of_ms(ts_ms: int) -> str:
    return datetime.fromtimestamp(int(ts_ms) / 1000, timezone.utc).date().isoformat()


def day_start_ms(day: str) -> int:
    d = date.fromisoformat(day)
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)


def day_range(start: date, end: date) -> list[str]:
    out = []
    d = start
    while d <= end:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


# --------------------------------------------------------------------------- #
# 清算(プリント)
# --------------------------------------------------------------------------- #
@dataclass
class Prints:
    """一意化したプリントの列(時刻順)。配列はすべて同じ長さ。"""

    ts: np.ndarray            # int64 ms
    side: np.ndarray          # object "SELL"/"BUY"(強制決済オーダー自身の向き)
    qty: np.ndarray           # accumulated_fill_quantity(枚)
    orig_qty: np.ndarray      # original_quantity(診断)
    price: np.ndarray         # average_price
    print_id: np.ndarray      # object
    stats: DedupStats | None = None

    def __len__(self) -> int:
        return int(self.ts.size)

    @property
    def sign(self) -> np.ndarray:
        return np.array([REACT_SIGN[s] for s in self.side.tolist()], dtype=float)

    @property
    def day(self) -> np.ndarray:
        return np.array([day_of_ms(t) for t in self.ts.tolist()], dtype=object)

    @classmethod
    def from_rows(cls, rows: Sequence[tuple], stats: DedupStats | None = None) -> "Prints":
        """`rows` = (ts_ms, side, qty, orig_qty, price) の列。時刻順に並べ直して id を振る。"""
        rows = sorted(rows, key=lambda r: (int(r[0]), str(r[1]), float(r[2])))
        ts = np.array([int(r[0]) for r in rows], dtype=np.int64)
        ids, cnt = [], defaultdict(int)
        for t in ts.tolist():
            d = day_of_ms(t)
            ids.append(f"{d}_{cnt[d]:05d}")
            cnt[d] += 1
        return cls(
            ts=ts,
            side=np.array([str(r[1]) for r in rows], dtype=object),
            qty=np.array([float(r[2]) for r in rows], dtype=float),
            orig_qty=np.array([float(r[3]) for r in rows], dtype=float),
            price=np.array([float(r[4]) for r in rows], dtype=float),
            print_id=np.array(ids, dtype=object),
            stats=stats,
        )


def load_prints(data_root: Path, start: date, end: date) -> Prints:
    """`liquidationSnapshot` の日次 zip を読み、**生の全 10 列の一致**で一意化する(設計 D-4)。

    数量 = `accumulated_fill_quantity`、価格 = `average_price`(`_read_binance_cm_rows` の正規化)。
    `original_quantity` は生の行の 5 列目から並べて持つ。落とした件数は `stats` に残す。
    """
    root = Path(data_root) / "liquidationSnapshot" / SYMBOL
    pairs = list(_read_binance_cm_rows(root, start, end))
    kept, stats = dedup_exact_rows(pairs, key=lambda pe: pe[0])
    rows = []
    for raw, ev in kept:
        rows.append((ev.ts_ms, str(raw[1]), ev.qty, float(raw[4]), ev.price))
    return Prints.from_rows(rows, stats)


# --------------------------------------------------------------------------- #
# 約定(日ごとの読み込みと、窓の連結)
# --------------------------------------------------------------------------- #
@dataclass
class Trades:
    times: np.ndarray   # int64 ms(昇順)
    prices: np.ndarray
    qtys: np.ndarray
    maker: np.ndarray   # bool: True = 買い手が maker = 売り taker

    @classmethod
    def empty(cls) -> "Trades":
        return cls(np.zeros(0, np.int64), np.zeros(0), np.zeros(0), np.zeros(0, bool))

    def slice_time(self, lo_ms: int, hi_ms: int) -> "Trades":
        """[lo, hi) の約定。"""
        a = int(np.searchsorted(self.times, lo_ms, side="left"))
        b = int(np.searchsorted(self.times, hi_ms, side="left"))
        return Trades(self.times[a:b], self.prices[a:b], self.qtys[a:b], self.maker[a:b])


class TradeStore:
    """日ごとの aggTrades を読み、必要な日の窓を連結して返す(読んだ日は持ち回す)。"""

    def __init__(self, data_root: Path, loader: Callable | None = None):
        self.data_root = Path(data_root)
        self._loader = loader
        self.cache: dict[str, Trades | None] = {}
        self.days_read: list[str] = []

    def _path(self, day: str) -> Path:
        return self.data_root / "aggTrades" / SYMBOL / f"{SYMBOL}-aggTrades-{day}.zip"

    def day(self, day: str) -> Trades | None:
        if day not in self.cache:
            if self._loader is not None:
                self.cache[day] = self._loader(day)
            else:
                p = self._path(day)
                if p.exists():
                    t, px, q, m = oi_module().load_agg_trades_with_maker(p)
                    self.cache[day] = Trades(t, px, q, m)
                else:
                    self.cache[day] = None
            self.days_read.append(day)
        return self.cache[day]

    def window(self, days: Sequence[str]) -> tuple[Trades, list[str]]:
        parts, missing = [], []
        for d in days:
            v = self.day(d)
            if v is None:
                missing.append(d)
            else:
                parts.append(v)
        if not parts:
            return Trades.empty(), missing
        tr = Trades(np.concatenate([p.times for p in parts]),
                    np.concatenate([p.prices for p in parts]),
                    np.concatenate([p.qtys for p in parts]),
                    np.concatenate([p.maker for p in parts]))
        if tr.times.size > 1 and not bool(np.all(tr.times[1:] >= tr.times[:-1])):
            o = np.argsort(tr.times, kind="stable")
            tr = Trades(tr.times[o], tr.prices[o], tr.qtys[o], tr.maker[o])
        return tr, missing

    def drop_before(self, day: str) -> None:
        for k in [k for k in self.cache if k < day]:
            del self.cache[k]


# --------------------------------------------------------------------------- #
# 価格の引き方(先読みの向きを名前で分ける)
# --------------------------------------------------------------------------- #
def idx_at_or_before(times: np.ndarray, tgt, tol: int = STALENESS_MS):
    """`tgt` 以前で最も新しい約定の添字と可否(`PriceSeries.at_or_before` と同じ規則)。"""
    tgt = np.asarray(tgt, dtype=np.int64)
    if times.size == 0:
        return np.zeros(tgt.shape, np.int64), np.zeros(tgt.shape, bool)
    i = np.searchsorted(times, tgt, side="right") - 1
    ok = i >= 0
    ic = np.clip(i, 0, times.size - 1)
    ok &= (tgt - times[ic]) <= tol
    return ic, ok


def idx_at_or_after(times: np.ndarray, tgt, tol: int = STALENESS_MS):
    """`tgt` 以後で最も古い約定の添字と可否(起点・入る約定にだけ使う)。"""
    tgt = np.asarray(tgt, dtype=np.int64)
    if times.size == 0:
        return np.zeros(tgt.shape, np.int64), np.zeros(tgt.shape, bool)
    i = np.searchsorted(times, tgt, side="left")
    ok = i < times.size
    ic = np.clip(i, 0, times.size - 1)
    ok &= (times[ic] - tgt) <= tol
    return ic, ok


def make_price_fn(tr: Trades, tol: int = STALENESS_MS):
    """`simulate_cascade` に渡す形 `price_fn(t_ms) -> (price, matched_ts)`(遅れは足さない)。"""
    def fn(t_ms: int):
        i, ok = idx_at_or_after(tr.times, np.array([int(t_ms)]), tol)
        if not bool(ok[0]):
            return NAN, None
        return float(tr.prices[i[0]]), int(tr.times[i[0]])
    return fn


# --------------------------------------------------------------------------- #
# 直前の状態(t − 1 ms 以前だけ)
# --------------------------------------------------------------------------- #
def pre_state_arrays(tr: Trades, t_arr) -> dict:
    """時刻 `t` ごとに、`t − 1 ms` 以前の約定だけから直前の状態を返す(プリントにも対照にも同じ)。

    - `raw_m10` / `raw_m60`: 直前の価格(t−1 以前の最後)の、10 秒 / 60 秒前(t−1−T 以前の最後)からの
      変化(bp、向きなし)。
    - `mat15` = raw_m10 ÷ raw_m60(前の材料 15 の定義)。
    - `imb5`: [t−5 秒, t) の成行の偏り (買い − 売り) ÷ 合計(前の `vectorized_imbalance`)。
    - `dir10` = raw_m10 の符号(0 は +1。前の Q7 と同じ)。対照の向きに使う。
    """
    t = np.asarray(t_arr, dtype=np.int64)
    ref = t - 1
    ip, okp = idx_at_or_before(tr.times, ref)
    p_pre = np.where(okp, tr.prices[ip] if tr.times.size else NAN, NAN)
    out = {"p_pre": p_pre}
    for T in (10, 60):
        im, okm = idx_at_or_before(tr.times, ref - T * MS_S)
        p_m = np.where(okm, tr.prices[im] if tr.times.size else NAN, NAN)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[f"raw_m{T}"] = np.where(okp & okm & (p_m > 0), (p_pre - p_m) / p_m * 1e4, NAN)
    with np.errstate(invalid="ignore", divide="ignore"):
        r60 = out["raw_m60"]
        out["mat15"] = np.where(np.isfinite(out["raw_m10"]) & np.isfinite(r60) & (r60 != 0),
                                out["raw_m10"] / np.where(r60 != 0, r60, 1.0), NAN)
    out["imb5"] = imbalance(tr, t, IMB_WINDOW_MS)
    out["dir10"] = np.where(np.isfinite(out["raw_m10"]),
                            np.where(out["raw_m10"] >= 0, 1.0, -1.0), NAN)
    out["mat9"] = np.where(np.isfinite(out["dir10"]) & np.isfinite(out["imb5"]),
                           out["dir10"] * out["imb5"], NAN)
    return out


def imbalance(tr: Trades, t_arr, window_ms: int) -> np.ndarray:
    """[t − window, t) の (買い taker − 売り taker) ÷ 合計。約定 0 なら NaN。"""
    t = np.asarray(t_arr, dtype=np.int64)
    if tr.times.size == 0:
        return np.full(t.size, NAN)
    buy = np.concatenate(([0.0], np.cumsum(np.where(~tr.maker, tr.qtys, 0.0))))
    sell = np.concatenate(([0.0], np.cumsum(np.where(tr.maker, tr.qtys, 0.0))))
    hi = np.searchsorted(tr.times, t, side="left")
    lo = np.searchsorted(tr.times, t - window_ms, side="left")
    b, s = buy[hi] - buy[lo], sell[hi] - sell[lo]
    tot = b + s
    out = np.full(t.size, NAN)
    ok = tot > 0
    out[ok] = (b[ok] - s[ok]) / tot[ok]
    return out


# --------------------------------------------------------------------------- #
# 同じ側の前後(材料 1・3・12 とラベル)
# --------------------------------------------------------------------------- #
def same_side_context(pr: Prints) -> dict:
    """プリントごとに、同じ側の前後を返す。**前の値は ts より前(厳密に小さい)だけ**。

    - `n_prev60`: [ts − 60 秒, ts) の同じ側の件数(材料 1。前の規則の入力)
    - `elapsed_prev_s`: 直前の同じ側のプリントからの秒(無ければ NaN)
    - `qty_ratio_prev`: 数量 ÷ 直前の同じ側の数量(材料 3)
    - `qty_ratio_max60`: 数量 ÷ [ts−60 秒, ts) の同じ側の最大(材料 12。無ければ NaN)
    - `gap_next_ms`: 次の同じ側のプリントまでの ms(**未来**。ラベル・s 秒の曲線にだけ使う。
      読んだ範囲に無ければ inf)
    """
    n = len(pr)
    out = {k: np.full(n, NAN) for k in ("n_prev60", "elapsed_prev_s", "qty_ratio_prev",
                                         "qty_ratio_max60")}
    out["gap_next_ms"] = np.full(n, np.inf)
    for s in ("SELL", "BUY"):
        idx = np.flatnonzero(pr.side == s)
        if idx.size == 0:
            continue
        t = pr.ts[idx]
        q = pr.qty[idx]
        lo = np.searchsorted(t, t - SAME_SIDE_WINDOW_MS, side="left")
        first_same = np.searchsorted(t, t, side="left")   # 同じ ms の他のプリントを前に数えない
        out["n_prev60"][idx] = (first_same - lo).astype(float)
        for k, j in enumerate(idx.tolist()):
            p = first_same[k] - 1
            if p >= 0:
                out["elapsed_prev_s"][j] = (t[k] - t[p]) / 1000.0
                out["qty_ratio_prev"][j] = q[k] / q[p] if q[p] > 0 else NAN
            if first_same[k] > lo[k]:
                mx = float(np.max(q[lo[k]:first_same[k]]))
                out["qty_ratio_max60"][j] = q[k] / mx if mx > 0 else NAN
        nxt = np.searchsorted(t, t, side="right")
        has = nxt < t.size
        g = np.full(idx.size, np.inf)
        g[has] = (t[np.clip(nxt, 0, t.size - 1)][has] - t[has]).astype(float)
        out["gap_next_ms"][idx] = g
    return out


# --------------------------------------------------------------------------- #
# 束(同じ側だけ、gap g)
# --------------------------------------------------------------------------- #
def same_side_bundles(pr: Prints, gap_s: int) -> dict:
    """側ごとに `build_cascades` を呼び、プリントごとに束の番号・位置・ここまでの量を返す。

    `pos_label`(最初 / 途中 / 最後 / 単発)の「最後」「単発」は**束が閉じてから分かる**(事後)。
    `k_in_bundle`(0 始まり)と `qty_so_far`(このプリントを含むここまでの数量)は ts 以前で決まる。
    """
    n = len(pr)
    bid = np.full(n, "", dtype=object)
    k_in = np.zeros(n, dtype=np.int64)
    n_b = np.zeros(n, dtype=np.int64)
    q_sofar = np.zeros(n)
    pos = np.full(n, "", dtype=object)
    bundles: list[dict] = []
    for s in ("SELL", "BUY"):
        idx = np.flatnonzero(pr.side == s)
        if idx.size == 0:
            continue
        evs = [LiquidationEvent(exchange=s, ts_ms=int(pr.ts[j]), side="long" if s == "SELL"
                                else "short", qty=float(pr.qty[j]), price=float(pr.price[j]))
               for j in idx.tolist()]
        cas = build_cascades(evs, exchange=s, gap_ms=gap_s * MS_S)
        # build_cascades は時刻順に区切るので、件数で元の添字に戻せる
        o = 0
        for c in cas:
            members = idx[o:o + c.n_events]
            o += c.n_events
            b = f"{s}_g{gap_s}_{day_of_ms(c.start_ms)}_{len(bundles):06d}"
            cum = np.cumsum(pr.qty[members])
            for k, j in enumerate(members.tolist()):
                bid[j] = b
                k_in[j] = k
                n_b[j] = c.n_events
                q_sofar[j] = cum[k]
                pos[j] = ("単発" if c.n_events == 1 else "最初" if k == 0
                          else "最後" if k == c.n_events - 1 else "途中")
            bundles.append({"bundle_id": b, "side": s, "gap_s": gap_s,
                            "start_ms": c.start_ms, "end_ms": c.end_ms,
                            "n_prints": c.n_events, "qty_total": float(cum[-1]),
                            "members": members})
        assert o == idx.size
    return {"bundle_id": bid, "k_in_bundle": k_in, "n_in_bundle": n_b,
            "qty_so_far": q_sofar, "pos_label": pos, "bundles": bundles}


# --------------------------------------------------------------------------- #
# 起点からの値動き・最大順行・最大逆行・山からの戻り
# --------------------------------------------------------------------------- #
def reactions_from_anchor(tr: Trades, anchor_ms: np.ndarray, direction: np.ndarray,
                          horizons_s: Sequence[int] = HORIZONS_S) -> dict:
    """起点 t₀ = `anchor_ms` 以後の最初の約定、p₀ = その価格。h ごとに:

    - `react_h`: p(t₀ + h)(t₀+h **以前**の最後の約定)の、p₀ からの変化(bp)× 向き
    - `mfe_h` / `mae_h`: (t₀, t₀+h] の約定の最大順行 / 最大逆行(bp、向き付き。mae は ≤ 0)
    - `giveback_h`: (t₀, t₀+h] の「それまでの山(p₀ を 0 とする)からの最大の下がり」(bp、≥ 0)
      = 最大順行の後の戻り(設計 §6 の 9)。
    `react_h` が NaN(穴)の行は mfe/mae/giveback も NaN にする。
    """
    anchor_ms = np.asarray(anchor_ms, dtype=np.int64)
    direction = np.asarray(direction, dtype=float)
    n = anchor_ms.size
    i0, ok0 = idx_at_or_after(tr.times, anchor_ms)
    ok0 &= np.isfinite(direction)
    t0 = np.where(ok0, tr.times[i0] if tr.times.size else -1, -1).astype(np.int64)
    p0 = np.where(ok0, tr.prices[i0] if tr.times.size else NAN, NAN)
    out = {"t0_ms": t0, "p0": p0, "p0_lag_ms": np.where(ok0, t0 - anchor_ms, -1)}
    hs = list(horizons_s)
    for h in hs:
        for k in ("react", "mfe", "mae", "giveback"):
            out[f"{k}_{h}"] = np.full(n, NAN)
    if n == 0 or tr.times.size == 0:
        return out
    h_ms = np.array(hs, dtype=np.int64) * MS_S
    for r in np.flatnonzero(ok0).tolist():
        tt0, pp0, sg = int(t0[r]), float(p0[r]), float(direction[r])
        ie, oke = idx_at_or_before(tr.times, tt0 + h_ms)
        a = int(i0[r]) + 1                                   # (t₀, …]
        b = int(np.searchsorted(tr.times, tt0 + h_ms[-1], side="right"))
        seg = sg * (tr.prices[a:b] - pp0) / pp0 * 1e4
        seg0 = np.concatenate(([0.0], seg))
        cmax = np.maximum.accumulate(seg0)
        cmin = np.minimum.accumulate(seg0)
        dd = np.maximum.accumulate(cmax - seg0)
        ends = np.searchsorted(tr.times[a:b], tt0 + h_ms, side="right")  # seg の個数
        for k, h in enumerate(hs):
            if not bool(oke[k]):
                continue
            out[f"react_{h}"][r] = sg * (tr.prices[ie[k]] - pp0) / pp0 * 1e4
            e = int(ends[k])                                  # seg0 の添字 e まで
            out[f"mfe_{h}"][r] = cmax[e]
            out[f"mae_{h}"][r] = cmin[e]
            out[f"giveback_{h}"][r] = dd[e]
    return out


# --------------------------------------------------------------------------- #
# s 秒の曲線(最後の同じ側のプリントから s 秒、次が来ていない時点で fade に入る)
# --------------------------------------------------------------------------- #
def s_curve_points(ts: np.ndarray, gap_next_ms: np.ndarray, data_end_ms: int,
                   s_max: int = S_MAX) -> tuple[np.ndarray, np.ndarray]:
    """(プリントの添字, s) の組を返す。条件: 次の同じ側のプリントまでの間隔 > s 秒
    (= ts + s 秒の時点で、まだ次が来ていない)。間隔が読んだ範囲の外(inf)のときは
    `data_end_ms`(次が無いと言える最後の時刻)までの s だけを数える。

    先読みの点: 「ts + s 秒の時点で次が来ていない」はその時点で分かる(過去の事実)。
    """
    ts = np.asarray(ts, dtype=np.int64)
    gn = np.asarray(gap_next_ms, dtype=float)
    rows, ss = [], []
    for i in range(ts.size):
        lim = gn[i] if np.isfinite(gn[i]) else float(data_end_ms - ts[i])
        # s*1000 < lim を満たす最大の s(上限 s_max)。lim は inf の場合も上で有限にしてある
        top = min(s_max, int(math.ceil(lim / MS_S)) - 1)
        if top >= 1:
            rows.append(np.full(top, i, dtype=np.int64))
            ss.append(np.arange(1, top + 1, dtype=np.int64))
    if not rows:
        return np.zeros(0, np.int64), np.zeros(0, np.int64)
    return np.concatenate(rows), np.concatenate(ss)


def s_curve_values(tr: Trades, ts: np.ndarray, sign: np.ndarray, rows: np.ndarray,
                   ss: np.ndarray, delay_s: int, horizons_s: Sequence[int]) -> dict:
    """各 (プリント, s) で、判断の時刻 ts + s、入る = at_or_after(ts + s + d)、
    出る = (入る約定の時刻 + h) 以前の最後の約定。fade の損益(bp、**建玉の向き** = −清算の向き)。"""
    ts = np.asarray(ts, dtype=np.int64)
    t_dec = ts[rows] + ss * MS_S
    ie, oke = idx_at_or_after(tr.times, t_dec + delay_s * MS_S)
    te = np.where(oke, tr.times[ie] if tr.times.size else 0, 0).astype(np.int64)
    pe = np.where(oke, tr.prices[ie] if tr.times.size else NAN, NAN)
    pos_dir = -np.asarray(sign, dtype=float)[rows]
    out = {}
    for h in horizons_s:
        ix, okx = idx_at_or_before(tr.times, te + h * MS_S)
        px = np.where(okx & oke, tr.prices[ix] if tr.times.size else NAN, NAN)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[h] = pos_dir * (px - pe) / pe * 1e4
    return out


# --------------------------------------------------------------------------- #
# 状態機械(前の道具をそのまま呼ぶ)
# --------------------------------------------------------------------------- #
def judge_rule_mat1(n_prev60: float) -> str:
    """規則(前の方策の段の「規則」= 材料 1): 直前 60 秒の同じ側の件数 ≥ 1 → 続く、0 → 止まる。"""
    v = float(n_prev60) if n_prev60 == n_prev60 else 0.0
    return JUDGE_CONTINUE if v >= 1.0 else JUDGE_STOP


def judge_perfect(k: int, n: int) -> str:
    """完全な判断(事後のラベル = 束の最後だけ「止まる」)。**未来を使う参照点**。"""
    return JUDGE_STOP if k == n - 1 else JUDGE_CONTINUE


JUDGED_POLICIES = ("規則_材料1", "完全な判断")
BASELINE_POLICIES = {"全部順張り": "順張り", "全部逆張り": "逆張り"}


def judgments_for(policy: str, members: np.ndarray, ctx: dict) -> list[str]:
    n = int(members.size)
    if policy == "完全な判断":
        return [judge_perfect(k, n) for k in range(n)]
    if policy == "規則_材料1":
        return [judge_rule_mat1(ctx["n_prev60"][j]) for j in members.tolist()]
    raise ValueError(policy)


def simulate_bundle(pr: Prints, bundle: dict, judgments: list[str] | None, policy_type: str,
                    delay_s: float, price_fn, baseline: str | None = None) -> dict:
    """1 本の束を状態機械に流す。連鎖の終わり = 最後のプリント + g(この時点で「g の間
    来なかった」が分かる)。`baseline` を渡すと判断を見ない基準の方策(最初で入り終わりまで)。"""
    pol = policy_module()
    members = bundle["members"]
    prints = [{"ts_ms": int(pr.ts[j]), "print_id": str(pr.print_id[j])}
              for j in members.tolist()]
    side_sign = REACT_SIGN[bundle["side"]]
    end_ts = int(bundle["end_ms"]) + int(bundle["gap_s"]) * MS_S
    if baseline is not None:
        return pol.simulate_baseline(prints, side_sign, baseline, delay_s, price_fn, end_ts)
    return pol.simulate_cascade(prints, judgments, side_sign, policy_type, delay_s,
                                price_fn, end_ts)


# --------------------------------------------------------------------------- #
# 対照
# --------------------------------------------------------------------------- #
def no_liq_mask(t_arr: np.ndarray, liq_ts_sorted: np.ndarray, margin_ms: int,
                t_end: np.ndarray | None = None) -> np.ndarray:
    """[t − margin, (t_end or t) + margin] に清算が 1 件も無いか。"""
    t = np.asarray(t_arr, dtype=np.int64)
    te = t if t_end is None else np.asarray(t_end, dtype=np.int64)
    lo = np.searchsorted(liq_ts_sorted, t - margin_ms, side="left")
    hi = np.searchsorted(liq_ts_sorted, te + margin_ms, side="right")
    return (hi - lo) == 0


def control_random(day: str, n: int, liq_ts_sorted: np.ndarray, rng: random.Random,
                   margin_ms: int = CTRL_MARGIN_MS, step_ms: int = MS_S) -> np.ndarray:
    """対照 (i): 同じ日の無作為時刻を `n` 個(1 秒刻みの格子から置換なし)、どの清算からも
    ±`margin_ms` 以上離れる。足りなければ取れた分だけ返す(呼び出し側が割合を出す)。"""
    d0 = day_start_ms(day)
    grid = d0 + np.arange(MS_DAY // step_ms, dtype=np.int64) * step_ms
    ok = np.flatnonzero(no_liq_mask(grid, liq_ts_sorted, margin_ms))
    k = min(n, ok.size)
    pick = sorted(rng.sample(ok.tolist(), k)) if k else []
    return grid[np.array(pick, dtype=np.int64)] if k else np.zeros(0, np.int64)


def decile_cuts(v: np.ndarray, n_bands: int = CTRL2_N_BANDS) -> np.ndarray:
    fin = np.asarray(v, dtype=float)
    fin = fin[np.isfinite(fin)]
    if fin.size == 0:
        return np.zeros(0)
    return np.percentile(fin, np.linspace(0, 100, n_bands + 1)[1:-1])


def band_of(v: np.ndarray, cuts: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    b = np.searchsorted(cuts, v, side="right").astype(np.int64)
    return np.where(np.isfinite(v), b, -1)


def control_matched(target_15: np.ndarray, target_9: np.ndarray, cand_t: np.ndarray,
                    cand_15: np.ndarray, cand_9: np.ndarray, cuts15: np.ndarray,
                    cuts9: np.ndarray) -> np.ndarray:
    """対照 (ii): 目標ごとに、同じ帯(材料 15 と材料 9 の 10 分位)の候補から
    |Δ材料15| + |Δ材料9| が最小のものを置換なしで 1 つ選ぶ。取れなければ −1。
    候補はあらかじめ「同じ日・前後 15 分に清算無し・値が有限」に絞って渡す。"""
    tb15, tb9 = band_of(target_15, cuts15), band_of(target_9, cuts9)
    cb15, cb9 = band_of(cand_15, cuts15), band_of(cand_9, cuts9)
    used = np.zeros(cand_t.size, dtype=bool)
    out = np.full(np.asarray(target_15).size, -1, dtype=np.int64)
    for r in range(out.size):
        if tb15[r] < 0 or tb9[r] < 0:
            continue
        idx = np.flatnonzero(~used & (cb15 == tb15[r]) & (cb9 == tb9[r]))
        if idx.size == 0:
            continue
        dist = np.abs(cand_15[idx] - target_15[r]) + np.abs(cand_9[idx] - target_9[r])
        j = int(idx[int(np.argmin(dist))])
        used[j] = True
        out[r] = j
    return out


def control_placebo(day: str, tr: Trades, bundles: list[dict], liq_ts_sorted: np.ndarray,
                    rng: random.Random, tol: float = PLACEBO_TOL,
                    step_ms: int = CTRL_GRID_MS, margin_ms: int = CTRL_MARGIN_MS) -> list[dict]:
    """対照 (iii): 束ごとに、束の窓 [start, end + 1 秒) の**約定数量(枚)** V と、同じ長さ
    (10 秒単位に切り上げ)の窓で、窓の前後 ±5 分に清算が無く、約定数量が V の ±`tol` に
    入るものを同じ日の 10 秒刻みから無作為に 1 つ(重ならない)。起点 = 窓の終わり、
    向き = 窓の中の値動きの符号(0 は +1)。取れない束は返さない(呼び出し側が割合を出す)。"""
    d0 = day_start_ms(day)
    grid = d0 + np.arange(MS_DAY // step_ms, dtype=np.int64) * step_ms
    cum = np.concatenate(([0.0], np.cumsum(tr.qtys)))

    def vol(a, b):
        return cum[np.searchsorted(tr.times, b, side="left")] - \
            cum[np.searchsorted(tr.times, a, side="left")]

    taken: list[tuple[int, int]] = []
    out = []
    for b in bundles:
        V = float(vol(np.array([b["start_ms"]]), np.array([b["end_ms"] + MS_S]))[0])
        dur = max(int(b["end_ms"] + MS_S - b["start_ms"]), step_ms)
        dur = int(math.ceil(dur / step_ms) * step_ms)
        if V <= 0:
            continue
        ends = grid + dur
        v = vol(grid, ends)
        ok = (np.abs(v - V) / V <= tol) & no_liq_mask(grid, liq_ts_sorted, margin_ms, ends)
        ok &= ends <= d0 + MS_DAY
        for s, e in taken:
            ok &= ~((grid <= e) & (ends >= s))
        cand = np.flatnonzero(ok)
        if cand.size == 0:
            continue
        j = int(cand[rng.randrange(cand.size)])
        s_, e_ = int(grid[j]), int(ends[j])
        taken.append((s_, e_))
        ia, oka = idx_at_or_before(tr.times, np.array([s_]))
        ib, okb = idx_at_or_before(tr.times, np.array([e_ - 1]))
        dirv = NAN
        if bool(oka[0]) and bool(okb[0]):
            dirv = 1.0 if tr.prices[ib[0]] >= tr.prices[ia[0]] else -1.0
        out.append({"bundle_id": b["bundle_id"], "start_ms": s_, "end_ms": e_,
                    "vol_bundle": V, "vol_placebo": float(v[j]), "dir": dirv})
    return out


# --------------------------------------------------------------------------- #
# 分布の集計(平均だけの行は作らない)
# --------------------------------------------------------------------------- #
def cluster_se(vals: np.ndarray, days: np.ndarray) -> tuple[float, int]:
    """日クラスタ SE(前の `mean_se_cluster` と同じ式。試験でその関数と一致を確かめる)。"""
    v = np.asarray(vals, dtype=float)
    d = np.asarray(days, dtype=object)
    ok = np.isfinite(v)
    v, d = v[ok], d[ok]
    n = v.size
    if n == 0:
        return NAN, 0
    m = v.mean()
    _u, inv = np.unique(d.astype(str), return_inverse=True)
    s = np.bincount(inv, weights=v - m)
    g = s.size
    if g <= 1:
        return NAN, g
    return float(math.sqrt(float(np.sum(s * s))) / n * math.sqrt(g / (g - 1))), g


def dist_stats(vals, days) -> dict:
    """1 件ごとの値の分布: 件数・NaN 件数・分位・正負零の割合・平均・日等重み平均・日クラスタ SE・
    日ごとの合計の平均と SE(日の数で割る標準誤差)。"""
    v = np.asarray(vals, dtype=float)
    d = np.asarray(days, dtype=object)
    ok = np.isfinite(v)
    out = {"n": int(ok.sum()), "n_nan": int((~ok).sum())}
    fv, fd = v[ok], d[ok].astype(str)
    if fv.size == 0:
        for q in QS:
            out[f"q{q:02d}"] = NAN
        out.update({"min": NAN, "max": NAN, "share_pos": NAN, "share_neg": NAN,
                    "share_zero": NAN, "mean": NAN, "day_eq_mean": NAN, "se_day_cluster": NAN,
                    "n_days": 0, "daysum_mean": NAN, "daysum_se": NAN})
        return out
    for q, x in zip(QS, np.percentile(fv, QS)):
        out[f"q{q:02d}"] = float(x)
    out["min"], out["max"] = float(fv.min()), float(fv.max())
    out["share_pos"] = float((fv > 0).mean())
    out["share_neg"] = float((fv < 0).mean())
    out["share_zero"] = float((fv == 0).mean())
    out["mean"] = float(fv.mean())
    u, inv = np.unique(fd, return_inverse=True)
    sums = np.bincount(inv, weights=fv)
    cnts = np.bincount(inv)
    out["day_eq_mean"] = float(np.mean(sums / cnts))
    out["se_day_cluster"], out["n_days"] = cluster_se(fv, fd)
    out["daysum_mean"] = float(sums.mean())
    out["daysum_se"] = (float(sums.std(ddof=1) / math.sqrt(sums.size)) if sums.size > 1
                        else NAN)
    return out


def tertile_cuts(v: np.ndarray) -> np.ndarray:
    fin = np.asarray(v, dtype=float)
    fin = fin[np.isfinite(fin)]
    if fin.size == 0:
        return np.zeros(0)
    return np.percentile(fin, [100 / 3, 200 / 3])


# --------------------------------------------------------------------------- #
# Jev に渡す状態(呼ばない。入力の作り方まで)
# --------------------------------------------------------------------------- #
def jev_state_raw(i: int, pr: Prints, ctx: dict, pre: dict, bund60: dict, tr: Trades) -> dict:
    """プリント `i` の時点の状態(生の数)。**ts より前のプリントと ts − 1 ms 以前の約定だけ**。
    前の `jev_state_for_print`(V3 = 価格の道筋なし)の形に、束のここまで(g = 60)を足した。"""
    ts = int(pr.ts[i])
    s = str(pr.side[i])
    lo = int(np.searchsorted(pr.ts, ts - SAME_SIDE_WINDOW_MS, side="left"))
    hi = int(np.searchsorted(pr.ts, ts, side="left"))
    prev = [{"t_rel_s": round((int(pr.ts[j]) - ts) / 1000.0, 3),
             "qty_contracts": float(pr.qty[j]), "side": str(pr.side[j])}
            for j in range(lo, hi)]

    def f(x):
        x = float(x)
        return None if not math.isfinite(x) else round(x, 6)

    return {
        "side": s,
        "qty_contracts": float(pr.qty[i]),
        "prints_last_60s": prev,
        "materials": {
            "same_side_count_60s": f(ctx["n_prev60"][i]),
            "elapsed_since_prev_same_side_s": f(ctx["elapsed_prev_s"][i]),
            "qty_ratio_to_previous": f(ctx["qty_ratio_prev"][i]),
            "qty_ratio_to_max_recent_60s": f(ctx["qty_ratio_max60"][i]),
            "move_10s_bp_signed": f(REACT_SIGN[s] * pre["raw_m10"][i]),
            "move_60s_bp_signed": f(REACT_SIGN[s] * pre["raw_m60"][i]),
            "burst_ratio_10s_over_60s": f(pre["mat15"][i]),
            "taker_imbalance_5s": f(pre["imb5"][i]),
            "cascade_so_far_count_g60": int(bund60["k_in_bundle"][i]) + 1,
            "cascade_so_far_qty_g60": f(bund60["qty_so_far"][i]),
        },
    }


def write_jsonl_gz(path: Path, rows: Sequence[dict]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
