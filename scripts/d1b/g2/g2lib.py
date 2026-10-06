"""前提の直接の測り(D1b)担当 G2 の共通部: 読み込み・分の格子・日の並び・区間・表の書き出し。

委任文: docs/DISCUSSIONS/2026-10-06_held_batches/DELEGATION_d1b_impl.md(共通の決まり)
問いの立て方: docs/DISCUSSIONS/2026-10-06_held_batches/D1B_FRAMINGS.md の # 4〜8・# 11 の行

- 読み込み: scripts/w4_measure/common.py の load_bars(封印の門 bot.bt.data.loader.load を通る)を暦年ごとに呼び、
  numpy の配列にして物は捨てる。終わりは common.check_end が封印の境で拒む。この台本は 2023-12-17T15:00Z より後を
  読まない(HI_MAX で先に拒む)。
- 分の格子: 期間の始まりの分から 1 分ごとの枠。足の無い分は NaN。決定に使う足 = 出来高 > 0 で終値が有限の足
  (src/bot/research/cards/run.py の _nonempty と同じ)。前の日の荒れ具合(vol_split_daily.daily_vol)には、
  load_bars が返した全部の足の終値を使う(vol_split_daily.load_closes_by_day と同じ)。
- 日 = 日本時間の暦の日。日の並び = 期間 [lo, hi) の日本時間の暦の日すべて(事象の無い日も入る)。
  前半・後半 = 日の並びを日数で 2 つ(len // 2 番目の日から後半)。
- 区間: bot.bt.validation.block_bootstrap_ci(循環、塊 5 日、1,000 回、種 20261006、95%)。x = 日の番号、統計量 =
  抽き直した日の 分子の和 ÷ 分母の和(群の和 ÷ 群の数)。抽き直しで分母が 0 になると関数が拒むので、そのときは
  「区間なし」と理由を書く(種も方法も替えない)。MDE = 2.8 × se(se = 抽き直した統計量の標準偏差)。
- 年ごとの表は記述(点と数だけ。区間なし)。
"""
from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for _p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "scripts", "w4_measure")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

NS = 1_000_000_000
MIN_NS = 60 * NS
HOUR_NS = 3600 * NS
DAY_NS = 86_400 * NS
JST_NS = 9 * HOUR_NS

SEED = 20261006
REPS = 1000
BLOCK = 5
ALPHA = 0.05
MDE_K = 2.8

HI_MAX = "2023-12-17T15:00:00Z"  # 委任文「2023-12-17T15:00Z より後を読まない」
PERIOD_FX = ("2015-11-28T15:00:00Z", "2023-12-17T15:00:00Z")  # カード 4・5・7・8 の CARD.md「測る期間」
PERIOD_C6 = ("2017-08-01T15:00:00Z", "2022-12-31T15:00:00Z")  # カード 6 の CARD.md「測る期間」(約 282 週)
OUT_ROOT = os.path.join(ROOT, "docs", "RESEARCH", "d1b")


def iso_ns(s: str) -> int:
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return int(d.timestamp()) * NS


def ns_iso(t: int) -> str:
    return datetime.fromtimestamp(t / 1e9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def jst_day(t_ns):
    """日本時間の暦の日の番号(1970-01-01 から)。配列も受ける。"""
    return (np.asarray(t_ns, dtype=np.int64) + JST_NS) // DAY_NS if np.ndim(t_ns) else (int(t_ns) + JST_NS) // DAY_NS


def day_str(n: int) -> str:
    return (date(1970, 1, 1) + timedelta(days=int(n))).isoformat()


def check_period(lo: int, hi: int) -> None:
    if hi > iso_ns(HI_MAX):
        raise SystemExit(f"拒否: 終わり {ns_iso(hi)} は {HI_MAX} より後(委任文の共通の決まり)")
    if lo >= hi:
        raise SystemExit(f"拒否: 始め {ns_iso(lo)} が終わり {ns_iso(hi)} 以降")
    for t in (lo, hi):
        if (t + JST_NS) % DAY_NS:
            raise SystemExit(f"拒否: 端 {ns_iso(t)} が日本時間の 0 時でない(日の並びが欠ける)")


# ---------------------------------------------------------------- 分の格子

@dataclass
class Grid:
    """t0 = 0 番目の分の始まり。o/h/l/c/v は分ごと(足の無い分は NaN、v は 0)。ne = 決定に使う足。"""
    t0: int
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    v: np.ndarray
    close_all: np.ndarray = None  # load_bars が返した全部の足の終値(出来高 0 の足も。無い分は NaN)
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        self.ne = np.isfinite(self.c) & (self.v > 0)
        if self.close_all is None:
            self.close_all = self.c.copy()
        n = len(self.c)
        # nxt[i] = i 以上で最初の決定の足(無ければ n)。prv[i] = i 以下で最後の決定の足(無ければ −1)
        idx = np.where(self.ne, np.arange(n), n)
        self.nxt = np.minimum.accumulate(idx[::-1])[::-1].astype(np.int64)
        idx2 = np.where(self.ne, np.arange(n), -1)
        self.prv = np.maximum.accumulate(idx2).astype(np.int64)

    @property
    def n(self) -> int:
        return len(self.c)

    def slice(self, lo: int, hi: int) -> "Grid":
        """[lo, hi) の分だけの格子(読み直さずに切り出す)。"""
        a, b = int(self.index(lo)), int(self.index(hi))
        if a < 0 or b > self.n or a >= b:
            raise ValueError(f"切り出しの範囲 {ns_iso(lo)}〜{ns_iso(hi)} が格子の外")
        return Grid(lo, self.o[a:b], self.h[a:b], self.l[a:b], self.c[a:b], self.v[a:b], self.close_all[a:b],
                    dict(self.meta, sliced=[ns_iso(lo), ns_iso(hi)]))

    def start(self, i):
        return self.t0 + np.asarray(i, dtype=np.int64) * MIN_NS

    def index(self, t_ns):
        return (np.asarray(t_ns, dtype=np.int64) - self.t0) // MIN_NS

    def next_ne(self, i):
        """i 以上で最初の決定の足の番号(i が格子の外なら n)。"""
        i = np.asarray(i, dtype=np.int64)
        out = np.full(i.shape, self.n, dtype=np.int64)
        ok = (i >= 0) & (i < self.n)
        out[ok] = self.nxt[i[ok]]
        return out

    def prev_ne(self, i):
        """i 以下で最後の決定の足の番号(無ければ −1)。"""
        i = np.asarray(i, dtype=np.int64)
        out = np.full(i.shape, -1, dtype=np.int64)
        ok = (i >= 0) & (i < self.n)
        out[ok] = self.prv[i[ok]]
        big = i >= self.n
        out[big] = self.prv[-1] if self.n else -1
        return out


def grid_from_bars(t0: int, n: int, starts, o, h, l, c, v) -> Grid:
    """足の並び(始まりの時刻)から格子を作る。格子の外の足は捨てる。同じ分に 2 本あれば拒む。"""
    starts = np.asarray(starts, dtype=np.int64)
    k = (starts - t0) // MIN_NS
    if np.any((starts - t0) % MIN_NS):
        raise ValueError("分の格子に乗らない足がある")
    ok = (k >= 0) & (k < n)
    k = k[ok]
    if len(np.unique(k)) != len(k):
        raise ValueError("同じ分に足が 2 本ある")
    arrs = []
    for x in (o, h, l, c):
        a = np.full(n, np.nan)
        a[k] = np.asarray(x, dtype=float)[ok]
        arrs.append(a)
    vv = np.zeros(n)
    vv[k] = np.asarray(v, dtype=float)[ok]
    return Grid(t0, *arrs, vv)


def load_grid(lo: int, hi: int, log=print) -> Grid:
    """bitFlyer FX_BTC_JPY の 1 分足 [lo, hi) を common.load_bars で暦年ごとに読み、格子にする。"""
    check_period(lo, hi)
    import common  # scripts/w4_measure/common.py
    n = (hi - lo) // MIN_NS
    parts = {k: [] for k in ("s", "o", "h", "l", "c", "v")}
    meta = {"source": common.FX_DIR, "lo": ns_iso(lo), "hi": ns_iso(hi), "anomalies": {}, "hashes": {}, "bars": 0}
    y0 = datetime.fromtimestamp(lo / 1e9, tz=timezone.utc).year
    y1 = datetime.fromtimestamp((hi - 1) / 1e9, tz=timezone.utc).year
    for y in range(y0, y1 + 1):
        a = max(lo, iso_ns(f"{y}-01-01T00:00:00Z"))
        b = min(hi, iso_ns(f"{y + 1}-01-01T00:00:00Z"))
        if a >= b:
            continue
        bars, kinds, hashes = common.load_bars(common.FX_DIR, "FX_BTC_JPY", a, b)
        for kk, vv in kinds.items():
            meta["anomalies"][kk] = meta["anomalies"].get(kk, 0) + vv
        meta["hashes"].update(hashes if isinstance(hashes, dict) else {str(y): hashes})
        parts["s"].append(np.fromiter((int(x.start_time_ns) for x in bars), dtype=np.int64, count=len(bars)))
        for kk, f in (("o", "open"), ("h", "high"), ("l", "low"), ("c", "close"), ("v", "volume")):
            parts[kk].append(np.fromiter((float(getattr(x, f)) for x in bars), dtype=float, count=len(bars)))
        meta["bars"] += len(bars)
        log(f"  読んだ {y}: {len(bars)} 本 {dict(kinds)}")
        del bars
    cat = {k: (np.concatenate(v) if v else np.zeros(0)) for k, v in parts.items()}
    g = grid_from_bars(lo, n, cat["s"], cat["o"], cat["h"], cat["l"], cat["c"], cat["v"])
    meta["vol0_bars"] = int(np.sum(np.isfinite(g.c) & ~(g.v > 0)))
    g.meta = meta
    return g


def closes_by_day(g: Grid) -> dict:
    """vol_split_daily.daily_vol に渡す 日(文字列)→ その日の全部の足の終値の並び(時刻順)。"""
    i = np.flatnonzero(np.isfinite(g.close_all))
    d = jst_day(g.start(i))
    out: dict = {}
    if len(i) == 0:
        return out
    cut = np.flatnonzero(np.diff(d)) + 1
    for seg in np.split(np.arange(len(i)), cut):
        out[day_str(int(d[seg[0]]))] = g.close_all[i[seg]].tolist()
    return out


def prev_day_class(g: Grid) -> dict:
    """前の日の荒れ具合の区分(scripts/w4_measure/vol_split_daily.py の daily_vol と classify。2017 年から)。
    日の番号 → "low" / "mid" / "high"。"""
    import vol_split_daily as vs  # noqa: E402
    cls = vs.classify(vs.daily_vol(closes_by_day(g)))
    return {int((date.fromisoformat(k) - date(1970, 1, 1)).days): v for k, v in cls.items()}


# ---------------------------------------------------------------- 日の並び・前半後半

@dataclass
class Days:
    nums: np.ndarray  # 日の番号(昇順、連続)

    @classmethod
    def of(cls, lo: int, hi: int) -> "Days":
        return cls(np.arange(jst_day(lo), jst_day(hi), dtype=np.int64))

    @property
    def half_start(self) -> int:
        return int(self.nums[len(self.nums) // 2])

    def parts(self) -> dict:
        """全期間・前半・後半の日の番号の並び。"""
        h = len(self.nums) // 2
        return {"全期間": self.nums, "前半": self.nums[:h], "後半": self.nums[h:]}

    def years(self) -> dict:
        ys = np.array([int(day_str(d)[:4]) for d in self.nums])
        return {int(y): self.nums[ys == y] for y in np.unique(ys)}

    def describe(self) -> dict:
        p = self.parts()
        return {k: {"from": day_str(v[0]), "to": day_str(v[-1]), "days": int(len(v))} for k, v in p.items() if len(v)}


class DayAcc:
    """日ごとの和をためる。add(日の番号の配列, 名前=値の配列) で日ごとに足す。"""

    def __init__(self, days: Days, names):
        self.days = days
        self.d0 = int(days.nums[0])
        self.n = len(days.nums)
        self.s = {k: np.zeros(self.n) for k in names}

    def add(self, day_nums, **vals) -> None:
        k = np.asarray(day_nums, dtype=np.int64) - self.d0
        ok = (k >= 0) & (k < self.n)
        for name, v in vals.items():
            v = np.broadcast_to(np.asarray(v, dtype=float), k.shape)
            self.s[name] += np.bincount(k[ok], weights=v[ok], minlength=self.n)

    def sub(self, nums) -> dict:
        k = np.asarray(nums, dtype=np.int64) - self.d0
        return {name: a[k] for name, a in self.s.items()}


# ---------------------------------------------------------------- 区間

def _boot(n_days: int, stat):
    from bot.bt.validation import ValidationError, block_bootstrap_ci
    try:
        with np.errstate(divide="ignore", invalid="ignore"):
            r = block_bootstrap_ci([float(k) for k in range(n_days)], block_len=BLOCK, n_resamples=REPS, seed=SEED,
                                   alpha=ALPHA, method="circular",
                                   statistic=lambda v: stat(v.astype(np.int64)))
        return {"lo": r.lo, "hi": r.hi, "se": r.se, "mde": MDE_K * r.se, "why": None}
    except ValidationError as e:
        return {"lo": None, "hi": None, "se": None, "mde": None, "why": f"区間なし: {e}"}


def ratio_ci(num, den, ci: bool = True) -> dict:
    """群の和 ÷ 群の数(分子の和 ÷ 分母の和)と、日の塊の区間。num・den は日ごと(日の並びの順)。"""
    num = np.asarray(num, dtype=float)
    den = np.asarray(den, dtype=float)
    tot = float(den.sum())
    out = {"n": tot, "days": int(len(den)), "est": (float(num.sum()) / tot) if tot > 0 else None}
    if not ci:
        return out
    if tot <= 0:
        out.update({"lo": None, "hi": None, "se": None, "mde": None, "why": "区間なし: 分母 0"})
        return out
    out.update(_boot(len(den), lambda i: num[i].sum() / den[i].sum()))
    return out


def _corr(n, sx, sy, sxx, syy, sxy) -> float:
    vx = sxx - sx * sx / n
    vy = syy - sy * sy / n
    if not (n > 1 and vx > 0 and vy > 0):
        return float("nan")
    return (sxy - sx * sy / n) / math.sqrt(vx * vy)


def corr_ci(acc: dict, ci: bool = True) -> dict:
    """日ごとの和 n・sx・sy・sxx・syy・sxy からのピアソンの相関と、日の塊の区間。"""
    a = {k: np.asarray(acc[k], dtype=float) for k in ("n", "sx", "sy", "sxx", "syy", "sxy")}
    tot = {k: float(v.sum()) for k, v in a.items()}
    r = _corr(**tot)
    out = {"n": tot["n"], "days": int(len(a["n"])), "est": None if math.isnan(r) else r}
    if not ci:
        return out
    if out["est"] is None:
        out.update({"lo": None, "hi": None, "se": None, "mde": None, "why": "区間なし: 相関が出ない"})
        return out
    out.update(_boot(len(a["n"]), lambda i: _corr(*(a[k][i].sum() for k in ("n", "sx", "sy", "sxx", "syy", "sxy")))))
    return out


def diff_ratio_ci(num1, den1, num2, den2) -> dict:
    """(分子 1 ÷ 分母 1)−(分子 2 ÷ 分母 2)。同じ日の抽き直しで両方を作る(区分の間の比べ)。"""
    a = [np.asarray(x, dtype=float) for x in (num1, den1, num2, den2)]
    if a[1].sum() <= 0 or a[3].sum() <= 0:
        return {"est": None, "lo": None, "hi": None, "se": None, "mde": None, "why": "区間なし: 分母 0"}
    out = {"est": float(a[0].sum() / a[1].sum() - a[2].sum() / a[3].sum())}
    out.update(_boot(len(a[0]), lambda i: a[0][i].sum() / a[1][i].sum() - a[2][i].sum() / a[3][i].sum()))
    return out


# ---------------------------------------------------------------- 表

def f(x, nd=3) -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "—"
    return f"{x:+.{nd}f}" if nd and abs(x) < 1e6 else f"{x:.{nd}f}"


def fci(r: dict, nd=3) -> str:
    if r.get("est") is None:
        return "—"
    if r.get("lo") is None:
        return f"{f(r['est'], nd)}(区間なし)"
    return f"{f(r['est'], nd)} [{f(r['lo'], nd)}, {f(r['hi'], nd)}]"


def fmde(r: dict, nd=3) -> str:
    return "—" if r.get("mde") is None else f"{r['mde']:.{nd}f}"


def quantiles(x, qs=(25, 50, 75, 90, 99)) -> dict:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if not len(x):
        return {str(q): None for q in qs}
    return {str(q): float(v) for q, v in zip(qs, np.percentile(x, qs))}


def write_out(out_dir: str, stem: str, md_lines: list, obj: dict) -> None:
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, stem + ".md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md_lines).rstrip() + "\n")
    with open(os.path.join(out_dir, stem + ".json"), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, default=_json_default)


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def count_table(days: Days, day_of_events, title: str, extra_cols: dict | None = None) -> list:
    """件数の数え上げの表(年ごと・前半後半)。day_of_events = 事象ごとの日の番号。extra_cols = 列名 → 事象ごとの日の番号。"""
    cols = {title: np.asarray(day_of_events, dtype=np.int64)}
    cols.update(extra_cols or {})
    head = "| 区分 | 日数 | " + " | ".join(cols) + " |"
    lines = [head, "|" + "---|" * (2 + len(cols))]
    groups = list(days.parts().items()) + [(str(y), v) for y, v in days.years().items()]
    for name, nums in groups:
        if not len(nums):
            continue
        lo_, hi_ = nums[0], nums[-1]
        cells = [str(int(np.sum((c >= lo_) & (c <= hi_)))) for c in cols.values()]
        lines.append(f"| {name} | {len(nums)} | " + " | ".join(cells) + " |")
    return lines
