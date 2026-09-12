"""価格帯ごとの積み上げから清算価格帯の候補を出す測定器(O-3c I-08 / Q2)。

**これは測定器であり、測定の実行や判定はしない。** 的中率・有意性は一切計算しない。
行う集計は「行数の確認」まで(`INTENT_MAP.md` §4 I-08、`REFRAME/LEAD_READING_2026-09-12.md`
§1 変更5)。

## この module がやること(4 つの中核)

1. `volume_at_price` — 時点 `t_ms` までの約定を価格の刻みで集計する(volume at price)。
   **`t_ms` より後の約定は、渡されていても構造的に無視する**(関数内部でフィルタする。
   呼び出し側の事前フィルタに依存しない)。
2. `open_interest_bands` — 同じ `t_ms` までの建玉(OI)時系列から、**OI が増えた区間**に
   重みを置いた価格帯分布を返す(重み = OI 増分 × その時点の代表価格)。資金調達率・
   ロング/ショート比は `t_ms` 以前の直近値を 1 点だけ添える(分布ではない)。
3. `candidate_bands` — 1・2 の分布から清算価格帯の候補を出す。**手法を 1 つに決めない**:
   (a) 出来高の山(volume-at-price の上位) / (b) 建玉の山(OI 増分の上位) /
   (c) 現在値からの乖離(レバレッジ倍率の仮定による素朴な線)。
4. `match_liquidations_to_bands` — 実際の清算と 3 の候補帯を突き合わせ、
   **1 清算イベント = 1 行**で手法ごとに(帯に入ったか・距離 bp)を返す。

補助として `build_candidates_at`(1→2→3 を 1 回の `t_ms` でまとめて呼ぶ配線)、
Binance COIN-M の aggTrades/metrics zip ローダー、CSV 書き出しを用意する。

## `liq_response.py` から再利用したもの(書き直さない)

- `PriceSeries`(時刻正規化・`at_or_before` による構造的先読み防止)。OI・資金調達率・
  L/S 比もすべて `PriceSeries`(スカラー時系列という点で価格と同型)として扱う。
- `LiquidationEvent` / `load_binance_cm_liquidations` / `load_gate_liquidations`
  (清算イベントの読み込みと正規化はここでは重複させない)。
- `write_csv`(列を渡せば流用できる)、`_iso`(ms→UTC ISO 文字列)。

## 時刻の扱い(すべて UTC ms に正規化してから扱う。使ったフィールドを明記)

- **aggTrades**(`backtest_data/binance_cm_o3c_20260913/README.md` 実測列:
  `agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker`):
  `ts_ms = transact_time`(取引所発、ms、そのまま使う)。価格は `price`、量は `quantity`。
- **metrics**(実測列: `create_time,symbol,sum_open_interest,sum_open_interest_value,
  count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,count_long_short_ratio,
  sum_taker_long_short_vol_ratio`): `create_time` は `"YYYY-MM-DD HH:MM:SS"` の
  タイムゾーン表記の無い文字列(実測)。**UTC と仮定して ms に変換する — この仮定は
  判断の置き所**(Binance Vision の日次ファイル自体が UTC 日境界で切られているため
  可能性は高いが、一次資料での明記は確認していない)。建玉は `sum_open_interest`。
  L/S 比は `sum_taker_long_short_vol_ratio` を使う(README 実測: 全行に値が入っている。
  `count_toptrader_long_short_ratio` 等は空文字列の行があるため避ける)。
  **資金調達率の列はこのファイルに存在しない**(実測、README 参照)。これはデータの
  制約であり判断の置き所ではない — `load_binance_cm_metrics` は funding series を
  作らず、呼び出し側は `funding_series=None` を渡すことになる(結果は NaN 列)。

## 欠測への強さ

`open_interest_bands` は窓内に OI の点が 1 点以下(増分を計算できない)なら
`bins` が空の `dict` を返す。`candidate_bands` はそれを受けて手法 (b) の候補を
空リストにする。`match_liquidation_to_bands` は候補が空の手法だけ NaN にし、
**行自体は消さない**。資金調達率・L/S 比が引けない場合も同様に該当列だけ NaN。
"""
from __future__ import annotations

import csv
import io
import math
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Sequence

from bot.research.liq_response import (  # noqa: F401  (LiquidationEvent 等は再エクスポートする)
    LiquidationEvent,
    PriceSeries,
    _iso,
    load_binance_cm_liquidations,
    load_gate_liquidations,
    write_csv,
)

# --------------------------------------------------------------------------- #
# 既定値(すべて判断の置き所。事前登録前にリードが見直す前提)
# --------------------------------------------------------------------------- #

#: 価格の刻み(USD)。約 30,000〜70,000 の BTC 価格帯に対しては約 1〜17bp 相当。
#: 原文・データ台帳に指定が無いため置いた既定値。
DEFAULT_PRICE_BIN_SIZE: float = 50.0

#: 積み上げを遡る期間(ms)。既定 24 時間。原文に指定が無いため置いた既定値。
DEFAULT_LOOKBACK_MS: int = 24 * 3_600_000

#: 手法 (a)/(b) で上位何本の bin を候補にするか。
DEFAULT_TOP_K: int = 3

#: 手法 (c) が仮定するレバレッジ倍率。**この仮定倍率は判断の置き所**。
#: bitFlyer FX / 海外 perp で実際に使われる代表的な倍率の並び(2/5/10/25/50/100倍)
#: をカバーする目的で置いたが、対象取引所の実際のレバレッジ分布は未確認。
DEFAULT_LEVERAGE_MULTIPLES: tuple[float, ...] = (5.0, 10.0, 25.0, 50.0, 100.0)

#: 手法 (c) の各センターに持たせる半width(bp)。原文に指定が無いため置いた既定値。
DEFAULT_NAIVE_BAND_HALF_WIDTH_BP: float = 25.0

#: 候補帯を作った後、清算をどれだけ先まで見て照合するか(ms、既定24時間)。
#: `scripts/measure_liq_bands.py` の複数起点ループでのみ使う。原文に指定が無いため
#: 置いた既定値。
DEFAULT_MATCH_HORIZON_MS: int = 24 * 3_600_000


# --------------------------------------------------------------------------- #
# 約定(価格側の積み上げの入力)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Trade:
    """正規化済みの 1 件の約定。`ts_ms` は UTC epoch ms(取引所発)。"""

    ts_ms: int
    price: float
    qty: float


def load_binance_cm_agg_trades(
    root: str | Path, start: date | None = None, end: date | None = None
) -> list[Trade]:
    """`backtest_data/binance_cm_o3c_20260913/aggTrades/<symbol>/` の日次 zip を読む。

    各 zip の中身は 1 本の CSV(1 行目がヘッダ、実測で確認)。列は上の module docstring
    のとおり。`transact_time`(ms、取引所発)をそのまま `ts_ms` に使う。
    """
    root = Path(root)
    trades: list[Trade] = []
    for zpath in sorted(root.glob("*-aggTrades-*.zip")):
        day = date.fromisoformat("-".join(zpath.stem.rsplit("-", 3)[1:]))
        if start is not None and day < start:
            continue
        if end is not None and day > end:
            continue
        with zipfile.ZipFile(zpath) as zf:
            names = [n for n in zf.namelist() if n.endswith(".csv")]
            assert len(names) == 1, (zpath, names)
            with zf.open(names[0]) as fh:
                reader = csv.reader(io.TextIOWrapper(fh, encoding="utf-8"))
                header = next(reader, None)
                assert header is not None and header[0] == "agg_trade_id", (zpath, header)
                for row in reader:
                    if not row:
                        continue
                    _id, price, qty, _first, _last, transact_time, _ibm = row[:7]
                    trades.append(Trade(ts_ms=int(transact_time), price=float(price), qty=float(qty)))
    trades.sort(key=lambda t: t.ts_ms)
    return trades


def load_binance_cm_metrics(
    root: str | Path, start: date | None = None, end: date | None = None
) -> tuple[PriceSeries, PriceSeries]:
    """`backtest_data/binance_cm_o3c_20260913/metrics/<symbol>/` の日次 zip から
    (建玉 `PriceSeries`, L/S比 `PriceSeries`) の 2 本を返す。

    列・UTC 仮定・funding が存在しない旨は module docstring 参照。
    `sum_taker_long_short_vol_ratio` が空文字列の行は L/S 比側のみ読み飛ばす
    (建玉側は同じ行でも読む — 独立に欠測する可能性があるため両者を別々に扱う)。
    """
    root = Path(root)
    oi_pairs: list[tuple[int, float]] = []
    ls_pairs: list[tuple[int, float]] = []
    for zpath in sorted(root.glob("*-metrics-*.zip")):
        day = date.fromisoformat("-".join(zpath.stem.rsplit("-", 3)[1:]))
        if start is not None and day < start:
            continue
        if end is not None and day > end:
            continue
        with zipfile.ZipFile(zpath) as zf:
            names = [n for n in zf.namelist() if n.endswith(".csv")]
            assert len(names) == 1, (zpath, names)
            with zf.open(names[0]) as fh:
                reader = csv.reader(io.TextIOWrapper(fh, encoding="utf-8"))
                header = next(reader, None)
                assert header is not None and header[0] == "create_time", (zpath, header)
                for row in reader:
                    if not row:
                        continue
                    (create_time, _symbol, sum_oi, _sum_oi_val,
                     _c_top, _s_top, _c_ls, sum_taker_ls) = row[:8]
                    dt = datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    ts_ms = int(dt.timestamp() * 1000)
                    oi_pairs.append((ts_ms, float(sum_oi)))
                    if sum_taker_ls != "":
                        ls_pairs.append((ts_ms, float(sum_taker_ls)))
    return PriceSeries.from_trades(oi_pairs), PriceSeries.from_trades(ls_pairs)


# --------------------------------------------------------------------------- #
# 価格帯への割り当て(bin の下端。境界値ちょうどは上の bin に入る)
# --------------------------------------------------------------------------- #

def _bin_low(price: float, bin_size: float) -> float:
    """`price` を `bin_size` 刻みの bin の下端に割り当てる(半開区間 `[low, low+bin_size)`)。

    境界値ちょうど(`price` が `bin_size` の整数倍)は、その値を下端とする bin に入る
    (下の bin ではなく、その値が始点の bin)。`math.floor` の定義そのものなので、
    この割り当て規則は `_bin_low` の外では変えない。
    """
    return math.floor(price / bin_size) * bin_size


# --------------------------------------------------------------------------- #
# 中核 1: 価格別の積み上げ(volume at price)
# --------------------------------------------------------------------------- #

@dataclass
class PriceBandProfile:
    """`t_ms` までの積み上げを bin 下端 → 重みの辞書として持つ。"""

    t_ms: int
    lookback_ms: int
    bin_size: float
    bins: dict[float, float]
    n_points: int


def volume_at_price(
    trades: Sequence[Trade],
    t_ms: int,
    lookback_ms: int = DEFAULT_LOOKBACK_MS,
    bin_size: float = DEFAULT_PRICE_BIN_SIZE,
) -> PriceBandProfile:
    """`t_ms` までの約定を `bin_size` 刻みで集計する(volume at price)。

    対象窓は `(t_ms - lookback_ms, t_ms]`(半開区間、下端を含まない)。
    **`t_ms` より後(`ts_ms > t_ms`)の約定は、`trades` に含まれていても構造的に無視する**
    (フィルタが関数内部にあり、呼び出し側の事前フィルタに依存しない。
    `tests/test_liq_bands.py` で確認)。
    """
    lo = t_ms - lookback_ms
    bins: dict[float, float] = {}
    n = 0
    for tr in trades:
        if tr.ts_ms > t_ms or tr.ts_ms <= lo:
            continue
        b = _bin_low(tr.price, bin_size)
        bins[b] = bins.get(b, 0.0) + tr.qty
        n += 1
    return PriceBandProfile(t_ms=t_ms, lookback_ms=lookback_ms, bin_size=bin_size, bins=bins, n_points=n)


# --------------------------------------------------------------------------- #
# 中核 2: 建玉側の積み上げ
# --------------------------------------------------------------------------- #

@dataclass
class OpenInterestBandProfile:
    """`t_ms` までの OI 増分を bin 下端 → 重みの辞書として持つ。資金調達率・L/S比は
    分布ではなく `t_ms` 以前の直近値を 1 点だけ持つ(引けなければ `None` = NaN 扱い)。
    """

    t_ms: int
    lookback_ms: int
    bin_size: float
    bins: dict[float, float]
    n_increments: int
    funding_rate: float | None
    long_short_ratio: float | None


def _window_points(series: PriceSeries, t_ms: int, lookback_ms: int) -> list[tuple[int, float]]:
    """`series` の中で `(t_ms - lookback_ms, t_ms]` にある点だけを時刻順で返す。

    `series.ts_ms` は `PriceSeries` の生成時点でソート済み(`from_trades`/`from_ohlc_bars`
    が保証)なので、ここでの単純な線形フィルタでも `t_ms` より後の点を混入させない。
    """
    lo = t_ms - lookback_ms
    return [(ts, v) for ts, v in zip(series.ts_ms, series.price) if lo < ts <= t_ms]


def open_interest_bands(
    oi_series: PriceSeries,
    price_series: PriceSeries,
    t_ms: int,
    lookback_ms: int = DEFAULT_LOOKBACK_MS,
    bin_size: float = DEFAULT_PRICE_BIN_SIZE,
    funding_series: PriceSeries | None = None,
    long_short_series: PriceSeries | None = None,
    price_max_staleness_ms: int | None = 300_000,
) -> OpenInterestBandProfile:
    """`t_ms` までの建玉(OI)時系列から、**OI が増えた区間**に重みを置いた価格帯分布を返す。

    重み = その区間の OI 増分 × 区間終端時点の代表価格
    (`price_series.at_or_before(区間終端, price_max_staleness_ms)` で引く。
    区間終端は窓内 = `t_ms` 以前なので、価格側でも構造的に先読みしない)。
    OI が減った・変化しなかった区間は重みに加えない(「積み上がった」区間のみ)。

    窓内の OI の点が 1 点以下(増分を計算できない)場合、または代表価格が
    `price_max_staleness_ms` 以内で引けない区間しか無い場合、`bins` は空の
    `dict` になる(呼び出し側はこれを「この手法(b)は候補が無い」として NaN 扱いする。
    行を落とさない — module docstring「欠測への強さ」参照)。

    `funding_series`/`long_short_series` は省略可(Binance COIN-M の metrics には
    資金調達率の列自体が無いため、`funding_series=None` で呼ぶのが現状の既定)。
    """
    points = _window_points(oi_series, t_ms, lookback_ms)
    bins: dict[float, float] = {}
    n_incr = 0
    for (_ts_prev, oi_prev), (ts_cur, oi_cur) in zip(points, points[1:]):
        delta = oi_cur - oi_prev
        if delta <= 0:
            continue
        anchor = price_series.at_or_before(ts_cur, price_max_staleness_ms)
        if anchor is None:
            continue
        b = _bin_low(anchor[1], bin_size)
        bins[b] = bins.get(b, 0.0) + delta
        n_incr += 1

    funding_point = funding_series.at_or_before(t_ms) if funding_series is not None else None
    ls_point = long_short_series.at_or_before(t_ms) if long_short_series is not None else None

    return OpenInterestBandProfile(
        t_ms=t_ms, lookback_ms=lookback_ms, bin_size=bin_size, bins=bins, n_increments=n_incr,
        funding_rate=(funding_point[1] if funding_point is not None else None),
        long_short_ratio=(ls_point[1] if ls_point is not None else None),
    )


# --------------------------------------------------------------------------- #
# 中核 3: 清算価格帯の候補(手法を 1 つに決めない)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Band:
    """1 本の候補帯。`weight` は手法 (a)/(b) の集計値(出来高/OI増分の合計)、
    手法 (c) では `None`(集計値という概念が無いため)。
    """

    method: str  # "a" | "b" | "c"
    label: str
    low: float
    high: float
    weight: float | None


@dataclass
class BandCandidates:
    """1 時点 `t_ms` に対する、手法 (a)/(b)/(c) の候補帯一式。"""

    t_ms: int
    current_price: float
    by_method: dict[str, list[Band]]
    funding_rate: float | None
    long_short_ratio: float | None


def candidate_bands(
    volume_profile: PriceBandProfile,
    oi_profile: OpenInterestBandProfile,
    current_price: float,
    t_ms: int,
    top_k: int = DEFAULT_TOP_K,
    leverage_multiples: Sequence[float] = DEFAULT_LEVERAGE_MULTIPLES,
    naive_band_half_width_bp: float = DEFAULT_NAIVE_BAND_HALF_WIDTH_BP,
) -> BandCandidates:
    """1・2 の分布から清算価格帯の候補を並べて出す。**手法を 1 つに決めない**。

    - (a) 出来高の山: `volume_profile.bins` を重み降順に上位 `top_k` 件、
      bin をそのまま帯にする(`[low, low+bin_size)`)。
    - (b) 建玉の山: `oi_profile.bins` を同様に上位 `top_k` 件。`bins` が空なら
      候補ゼロを返す(建玉データが窓内に無い/増分が計算できない場合。
      呼び出し側は `match_liquidation_to_bands` で NaN 扱いする)。
    - (c) レバレッジ仮定の素朴な線: `leverage_multiples` の各倍率 `L` について、
      `long_center = current_price * (1 - 1/L)`(その価格まで下がるとロングが
      その倍率で全損する、という維持率・逆選択・資金調達を無視した最も粗い近似)、
      `short_center = current_price * (1 + 1/L)`。各センターの
      `± naive_band_half_width_bp` を帯にする。**`leverage_multiples` の既定値と
      `naive_band_half_width_bp` の既定値はいずれも判断の置き所**
      (module docstring の `DEFAULT_*` 定義を参照)。
    """
    by_method: dict[str, list[Band]] = {"a": [], "b": [], "c": []}

    ranked_vol = sorted(volume_profile.bins.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    for rank, (low, vol) in enumerate(ranked_vol):
        by_method["a"].append(
            Band(method="a", label=f"vol_rank{rank}", low=low, high=low + volume_profile.bin_size, weight=vol)
        )

    ranked_oi = sorted(oi_profile.bins.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    for rank, (low, w) in enumerate(ranked_oi):
        by_method["b"].append(
            Band(method="b", label=f"oi_rank{rank}", low=low, high=low + oi_profile.bin_size, weight=w)
        )

    half = naive_band_half_width_bp / 10_000.0
    for lev in leverage_multiples:
        long_center = current_price * (1.0 - 1.0 / lev)
        short_center = current_price * (1.0 + 1.0 / lev)
        by_method["c"].append(Band(
            method="c", label=f"long_{lev}x",
            low=long_center * (1.0 - half), high=long_center * (1.0 + half), weight=None,
        ))
        by_method["c"].append(Band(
            method="c", label=f"short_{lev}x",
            low=short_center * (1.0 - half), high=short_center * (1.0 + half), weight=None,
        ))

    return BandCandidates(
        t_ms=t_ms, current_price=current_price, by_method=by_method,
        funding_rate=oi_profile.funding_rate, long_short_ratio=oi_profile.long_short_ratio,
    )


# --------------------------------------------------------------------------- #
# 中核 4: 照合(1清算イベント = 1行)
# --------------------------------------------------------------------------- #

_METHODS: tuple[str, ...] = ("a", "b", "c")


def match_liquidation_to_bands(event_price: float, candidates: BandCandidates) -> dict:
    """1 件の清算価格を候補帯と突き合わせる。手法ごとに `in_band_{m}` / `distance_bp_{m}`。

    候補が無い手法(`by_method[m]` が空)は両方 `float("nan")` にする(判定不可を明示。
    `False`/`0.0` にはしない — 「帯の外」と「候補が無い」は異なる状態のため)。
    候補が複数ある手法は、最も近い(距離が最小の)帯を採用する。帯の内側は距離 0。
    距離は「帯の外にある場合、最も近い辺までの距離」を `event_price` に対する bp で表す
    (符号は付けない絶対値)。
    """
    out: dict = {}
    for method in _METHODS:
        bands = candidates.by_method.get(method, [])
        if not bands:
            out[f"in_band_{method}"] = float("nan")
            out[f"distance_bp_{method}"] = float("nan")
            continue
        in_band = False
        min_dist_bp = None
        for b in bands:
            if b.low <= event_price <= b.high:
                in_band = True
                dist_bp = 0.0
            else:
                dist_bp = min(abs(event_price - b.low), abs(event_price - b.high)) / event_price * 10_000.0
            if min_dist_bp is None or dist_bp < min_dist_bp:
                min_dist_bp = dist_bp
        out[f"in_band_{method}"] = in_band
        out[f"distance_bp_{method}"] = 0.0 if in_band else min_dist_bp
    return out


def match_liquidations_to_bands(
    events: Sequence[LiquidationEvent], candidates: BandCandidates
) -> list[dict]:
    """`events` を候補帯と突き合わせ、1 清算イベント = 1 行の表にする。

    列は最低限: 時刻(`ts_ms`/`ts_utc`)・取引所・清算価格・向き・サイズ・
    手法ごとの `in_band_{a,b,c}`/`distance_bp_{a,b,c}`・予測の起点時刻
    (`origin_t_ms`/`origin_t_utc`)。加えて起点時点の資金調達率・L/S比(いずれも
    引けなければ NaN)。行は落とさない(候補が無い手法の列だけ NaN にする)。
    """
    rows: list[dict] = []
    for e in events:
        row: dict = {
            "ts_ms": e.ts_ms,
            "ts_utc": _iso(e.ts_ms),
            "exchange": e.exchange,
            "liq_price": e.price,
            "side": e.side,
            "qty": e.qty,
            "origin_t_ms": candidates.t_ms,
            "origin_t_utc": _iso(candidates.t_ms),
            "funding_rate_at_t": candidates.funding_rate if candidates.funding_rate is not None else float("nan"),
            "long_short_ratio_at_t": (
                candidates.long_short_ratio if candidates.long_short_ratio is not None else float("nan")
            ),
        }
        row.update(match_liquidation_to_bands(e.price, candidates))
        rows.append(row)
    return rows


# --------------------------------------------------------------------------- #
# 配線: 1・2・3 を 1 回の t_ms でまとめて呼ぶ
# --------------------------------------------------------------------------- #

def build_candidates_at(
    trades: Sequence[Trade],
    oi_series: PriceSeries,
    price_series: PriceSeries,
    t_ms: int,
    lookback_ms: int = DEFAULT_LOOKBACK_MS,
    price_bin_size: float = DEFAULT_PRICE_BIN_SIZE,
    oi_bin_size: float | None = None,
    funding_series: PriceSeries | None = None,
    long_short_series: PriceSeries | None = None,
    top_k: int = DEFAULT_TOP_K,
    leverage_multiples: Sequence[float] = DEFAULT_LEVERAGE_MULTIPLES,
    naive_band_half_width_bp: float = DEFAULT_NAIVE_BAND_HALF_WIDTH_BP,
    current_price_max_staleness_ms: int | None = 300_000,
    oi_price_max_staleness_ms: int | None = 300_000,
) -> BandCandidates | None:
    """`volume_at_price` → `open_interest_bands` → `candidate_bands` を 1 回の `t_ms` で配線する。

    `current_price`(手法 (c) の基準値)は `price_series.at_or_before(t_ms, ...)` で
    引く。引けない(`t_ms` 以前に価格の点が無い/`max_staleness` を超えている)場合は
    候補自体を作れないので `None` を返す(呼び出し側はこの `t_ms` をスキップする)。
    **`trades`・`oi_series`・`price_series`・`funding_series`・`long_short_series` は
    どれも `t_ms` より後のデータを含んでいてよい** — `volume_at_price` と
    `open_interest_bands`(および `PriceSeries.at_or_before`)がそれぞれ内部で
    `t_ms` 以前だけに絞るため、この関数の出力は構造的に `t_ms` より後のデータに
    依存しない(`tests/test_liq_bands.py` で確認)。
    """
    anchor = price_series.at_or_before(t_ms, current_price_max_staleness_ms)
    if anchor is None:
        return None
    current_price = anchor[1]

    vol_profile = volume_at_price(trades, t_ms, lookback_ms, price_bin_size)
    oi_profile = open_interest_bands(
        oi_series, price_series, t_ms, lookback_ms, oi_bin_size or price_bin_size,
        funding_series=funding_series, long_short_series=long_short_series,
        price_max_staleness_ms=oi_price_max_staleness_ms,
    )
    return candidate_bands(
        vol_profile, oi_profile, current_price, t_ms,
        top_k=top_k, leverage_multiples=leverage_multiples,
        naive_band_half_width_bp=naive_band_half_width_bp,
    )


# --------------------------------------------------------------------------- #
# CSV 出力(行数の確認までしか行わない = 判定ではない)
# --------------------------------------------------------------------------- #

CSV_COLUMNS: tuple[str, ...] = (
    "ts_ms", "ts_utc", "exchange", "liq_price", "side", "qty",
    "origin_t_ms", "origin_t_utc",
    "in_band_a", "distance_bp_a",
    "in_band_b", "distance_bp_b",
    "in_band_c", "distance_bp_c",
    "funding_rate_at_t", "long_short_ratio_at_t",
)
