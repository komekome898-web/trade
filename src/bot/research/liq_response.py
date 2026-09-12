"""清算 → 価格反応の測定器(O-3c I-01)。

**これは測定器であり、測定の実行や判定はしない。** 事前登録より前の段階のスケルトンで、
この module 自身は集計(平均・有意性検定)を一切行わない。行う集計は「行数の確認」まで
(`build_dataset` の戻り値の長さを数える程度)。

## この module がやること(3 つの核)

1. `build_cascades` — 個々の清算イベントを時間で束ねて「カスケード」にする
   (`gap_ms` 以上清算が途絶えたら切る)。
2. `compute_reactions` — カスケード終了時刻を起点に、`horizons_min` 経過後の価格を
   bp で返す。**起点の価格は起点時刻以前のデータだけから決まる**(構造的先読み防止。
   `PriceSeries.at_or_before` が唯一の参照点で、`bisect_right` の性質上
   `ts_ms` より後の要素を絶対に見られない)。
3. `sample_placebo_windows` / `sample_no_liquidation_windows` — 対照群
   (清算を伴わない出来高急増 / 清算の無い時間帯)を、カスケードと同じ形
   (開始・終了・規模)で作る。

## 時刻の扱い(取引所ごと。全て UTC ms に正規化してから扱う)

- **Binance COIN-M**(`liquidationSnapshot` CSV の `time` 列): 取引所発、ミリ秒。
  そのまま `ts_ms` として使う(変換不要)。列名は
  `backtest_data/binance_cm_o3c_20260913/README.md` の実測: `time,side,order_type,
  time_in_force,original_quantity,price,average_price,order_status,last_fill_quantity,
  accumulated_fill_quantity`。`side` は**強制決済オーダー自身の方向**
  (`SELL` = ロングの強制決済、`BUY` = ショートの強制決済 — Binance 公式の
  force order の定義どおり)。数量は `accumulated_fill_quantity`(実際に約定した量。
  `original_quantity` はオーダー全体の量で未約定分を含みうる)、価格は
  `average_price`(実約定 VWAP。`price` はオーダーの指値であり実約定価格ではない)。
- **Gate**(`liq_orders` の `time` フィールド): 取引所発だが**秒精度**
  (`DATA_AVAILABILITY.md` §1 実測)。`ts_ms = int(time) * 1000` として ms に揃えるが、
  実際の精度は秒のまま(下 3 桁は常に `000`)であることをここに明記する。
  `size` は「清算された建玉のサイズ」そのもの(Binance のような「強制決済注文自体の
  方向」ではない。一次資料: `docs/DATA/surveys/O3C_VERIFY_LIQUIDATION_SIDE_2026-09-13.md`
  主張2)。符号の正負が long/short のどちらかは一次資料には無く、**傍証**
  (同ファイル「## 傍証による決着」節、2026-09-13)で決めた: **正 = ロングの強制決済
  (強制売り)、負 = ショートの強制決済(強制買い)**。数量は `abs(size)`、価格は
  `fill_price`。
- **BitMEX は対象外**(取引所発の時刻フィールドが無い。`INTENT_MAP.md` §4 I-06 参照)。

## 規模(`total_size` / `notional`)の注意

`notional = qty * price` は取引所ごとの契約単位の違い(Binance COIN-M は逆数契約、
Gate は USDT 建て)を吸収していない**同一取引所内だけの相対比較用**の値。
取引所を跨いで大小を比較する主張はしない(そもそもこの module は主張自体をしない)。

## 欠測への強さ

`PriceSeries.at_or_before` は要求した時刻から `max_staleness_ms` 以上遡らないと
値が見つからない場合 `None` を返し、呼び出し側はその行を **NaN のまま残す**
(行を消さない)。カスケードの構成・対照群の抽出でも同様に、価格が引けない行は
落とさず NaN で埋める。
"""
from __future__ import annotations

import bisect
import csv
import io
import random
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal, Sequence

from bot.research.liquidations import read_rows

Side = Literal["long", "short"]
Direction = Literal["long", "short", "mixed", "none"]
Kind = Literal["real", "placebo", "no_liquidation"]


def _iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# --------------------------------------------------------------------------- #
# 清算イベント(取引所ごとの生データを共通形に正規化する)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class LiquidationEvent:
    """正規化済みの 1 件の強制決済。`ts_ms` は UTC epoch ms(取引所発。上の docstring 参照)。"""

    exchange: str
    ts_ms: int
    side: Side          # "long" = ロング建玉の強制決済(強制売り) / "short" = 逆
    qty: float
    price: float

    @property
    def notional(self) -> float:
        return self.qty * self.price


def load_binance_cm_liquidations(
    root: str | Path, start: date | None = None, end: date | None = None
) -> list[LiquidationEvent]:
    """`backtest_data/binance_cm_o3c_20260913/liquidationSnapshot/<symbol>/` の日次 zip を読む。

    各 zip の中身は 1 本の CSV(1 行目がヘッダ。実測で確認、README のコード例は
    ヘッダを省いて データ行だけを示していたので注意)。列は上の docstring のとおり。
    `time` 列(ms、取引所発)をそのまま `ts_ms` に使う。ファイル自体が無い日
    (欠測 6 日、README 参照)は単に無視される(呼び出し側は自分でカバレッジを見る)。
    """
    root = Path(root)
    events: list[LiquidationEvent] = []
    for zpath in sorted(root.glob("*-liquidationSnapshot-*.zip")):
        # ファイル名 "<SYMBOL>-liquidationSnapshot-YYYY-MM-DD.zip" から日付を取る
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
                assert header is not None and header[0] == "time", (zpath, header)
                for row in reader:
                    if not row:
                        continue
                    (time_ms, side, _order_type, _tif, _orig_qty, _price,
                     avg_price, _status, _last_fill, accum_fill) = row[:10]
                    events.append(LiquidationEvent(
                        exchange="binance_cm",
                        ts_ms=int(time_ms),
                        side="long" if side == "SELL" else "short",
                        qty=float(accum_fill),
                        price=float(avg_price),
                    ))
    events.sort(key=lambda e: e.ts_ms)
    return events


def load_gate_liquidations(path: str | Path) -> list[LiquidationEvent]:
    """`backtest_data/gate_liquidations_20260908/*.jsonl.gz` を読む。

    `liquidations.read_rows`(gzip の途中切れに強い読み手)をそのまま再利用する。
    `time` は**秒精度**(下 3 桁は ms に揃えるためだけの 0 埋め、精度そのものは秒のまま)。

    **`size` の符号 → long/short の対応は一次資料に無く、傍証で決めた
    (2026-09-13、`docs/DATA/surveys/O3C_VERIFY_LIQUIDATION_SIDE_2026-09-13.md`
    「## 傍証による決着」節)。** 判定の根拠(BTC_USDT, 2026-06-10〜09-08, 79,183 件):
    `size` の符号ごとに清算を 60 秒ギャップでバースト化し、同一バースト内の
    最初→最後の `fill_price` の変化(bp)の向きを見た。複数件(n_events>=2)の
    バーストに限ると、`size > 0` のバースト 3,195 件中 2,555 件(80.0%)が価格下降、
    `size < 0` のバースト 3,176 件中 2,557 件(80.5%)が価格上昇と、**符号ごとに
    明確に逆方向へ偏った**。ロング建玉の強制決済は市場に売りをぶつけるので価格は
    下がる方向に集中するはず → **`size > 0` = ロングの強制決済、`size < 0` = ショートの
    強制決済**と判定した(旧実装は逆だった)。
    """
    rows = read_rows(path).rows
    events = [
        LiquidationEvent(
            exchange="gate",
            ts_ms=int(row["time"]) * 1000,
            side="long" if float(row["size"]) > 0 else "short",
            qty=abs(float(row["size"])),
            price=float(row["fill_price"]),
        )
        for row in rows
    ]
    events.sort(key=lambda e: e.ts_ms)
    return events


# --------------------------------------------------------------------------- #
# 核 1: カスケードの構成
# --------------------------------------------------------------------------- #

@dataclass
class Cascade:
    """1 つの束(実カスケード、またはプラセボ/無清算の対照窓)。"""

    cascade_id: str
    exchange: str
    kind: Kind
    start_ms: int
    end_ms: int
    n_events: int
    total_size: float
    direction: Direction
    first_price: float | None
    last_price: float | None


def _direction_of(sides: Sequence[Side]) -> Direction:
    uniq = set(sides)
    if uniq == {"long"}:
        return "long"
    if uniq == {"short"}:
        return "short"
    return "mixed"


def build_cascades(
    events: Sequence[LiquidationEvent], exchange: str, gap_ms: int = 60_000
) -> list[Cascade]:
    """清算イベントを時間で束ねる。

    規則: 同一 `exchange` のイベントを時刻順に見て、直前のイベントから `gap_ms`
    を**超えて**空いたら新しいカスケードに切る(`gap_ms` ちょうどは同じカスケードに残す。
    境界の扱いはこの一点だけが恣意的なので単体テストで固定する)。

    **既定値 60_000ms(1 分)は判断の置き所**: カスケードを何秒の無清算で切るかは
    原文(OWNER_INTENT)に指定が無い。1 分は「複数の清算が連鎖する」に対して
    短すぎず長すぎない目安として置いた既定値であり、事前登録前にリードが見直す前提。
    """
    evs = sorted((e for e in events if e.exchange == exchange), key=lambda e: e.ts_ms)
    cascades: list[Cascade] = []
    bucket: list[LiquidationEvent] = []
    for e in evs:
        if bucket and e.ts_ms - bucket[-1].ts_ms > gap_ms:
            cascades.append(_finalize_cascade(bucket, exchange, len(cascades)))
            bucket = []
        bucket.append(e)
    if bucket:
        cascades.append(_finalize_cascade(bucket, exchange, len(cascades)))
    return cascades


def _finalize_cascade(bucket: list[LiquidationEvent], exchange: str, idx: int) -> Cascade:
    return Cascade(
        cascade_id=f"{exchange}_real_{idx:06d}",
        exchange=exchange,
        kind="real",
        start_ms=bucket[0].ts_ms,
        end_ms=bucket[-1].ts_ms,
        n_events=len(bucket),
        total_size=sum(e.notional for e in bucket),
        direction=_direction_of([e.side for e in bucket]),
        first_price=bucket[0].price,
        last_price=bucket[-1].price,
    )


# --------------------------------------------------------------------------- #
# 価格系列(先読み防止の唯一の入口)
# --------------------------------------------------------------------------- #

@dataclass
class PriceSeries:
    """UTC ms でソート済みの (時刻, 価格) の列。`at_or_before` だけを通して読む。

    `scripts/k1_source.py: load_bars` の形((epoch秒 or ms, o,h,l,c) のタプル列)を
    そのまま `from_ohlc_bars` に渡せる。約定 tick 列を使う場合は `from_trades` を使う。
    """

    ts_ms: list[int] = field(default_factory=list)
    price: list[float] = field(default_factory=list)

    @classmethod
    def from_trades(cls, rows: Sequence[tuple[int, float]]) -> "PriceSeries":
        """`(ts_ms, price)` の列(未ソートでよい)から作る。"""
        pairs = sorted(rows, key=lambda r: r[0])
        return cls(ts_ms=[p[0] for p in pairs], price=[p[1] for p in pairs])

    @classmethod
    def from_ohlc_bars(cls, bars: Sequence[tuple[int, float, float, float, float]],
                        ts_unit: Literal["s", "ms"] = "s") -> "PriceSeries":
        """`k1_source.load_bars` と同じ形 `(ts, o, h, l, c)` から close を系列にする。

        `ts_unit` は入力の時刻の単位(k1_source 系はすべて秒)。ここで ms に揃える。
        """
        mul = 1000 if ts_unit == "s" else 1
        pairs = sorted(((int(b[0]) * mul, float(b[4])) for b in bars), key=lambda r: r[0])
        return cls(ts_ms=[p[0] for p in pairs], price=[p[1] for p in pairs])

    def at_or_before(
        self, ts_ms: int, max_staleness_ms: int | None = None
    ) -> tuple[int, float] | None:
        """`ts_ms` **以前**で最も新しい点を返す。`ts_ms` より後の点は構造的に見えない。

        `bisect_right(self.ts_ms, ts_ms)` は「ts_ms 以下の要素の個数」を返すので、
        その 1 つ前の添字までしか候補にならない — これが先読み防止の全体。
        見つかっても `ts_ms` からの遡り幅が `max_staleness_ms` を超えていれば
        (穴が空いている区間)`None` を返す = 呼び出し側は NaN として行を残す。
        """
        idx = bisect.bisect_right(self.ts_ms, ts_ms) - 1
        if idx < 0:
            return None
        found_ts = self.ts_ms[idx]
        if max_staleness_ms is not None and ts_ms - found_ts > max_staleness_ms:
            return None
        return found_ts, self.price[idx]


# --------------------------------------------------------------------------- #
# 核 2: 反応窓の切り出し
# --------------------------------------------------------------------------- #

DEFAULT_HORIZONS_MIN: tuple[int, ...] = (1, 5, 15, 60)


def compute_reactions(
    cascades: Sequence[Cascade],
    prices: PriceSeries,
    horizons_min: Sequence[int] = DEFAULT_HORIZONS_MIN,
    anchor_max_staleness_ms: int | None = 300_000,
    future_max_staleness_ms: int | None = 300_000,
) -> list[dict]:
    """カスケード終了時刻を起点に、`horizons_min` 分後の bp 変化を計算する。

    起点価格 = `prices.at_or_before(cascade.end_ms, anchor_max_staleness_ms)`。
    **起点時刻より後のデータは、起点価格の計算に一切現れない**
    (`PriceSeries.at_or_before` の構造上の保証。`tests/test_liq_response.py` で確認)。

    `anchor_max_staleness_ms` / `future_max_staleness_ms` の既定値 300_000(5 分)は
    判断の置き所: 「起点直近の価格」をどこまで遡って許すかは原文に指定が無く、
    板の空白や取引の閑散を NaN として拾うための目安として置いた。事前登録前に見直す前提。

    戻り値は 1 カスケード = 1 dict。行は**落とさない**(起点や将来価格が引けない場合は
    その `bp_{h}m` を `float("nan")` にするだけで、カスケード自体の行は必ず出す)。
    ここでは平均や有意性は計算しない(判定はしない)。
    """
    rows: list[dict] = []
    for c in cascades:
        anchor = prices.at_or_before(c.end_ms, anchor_max_staleness_ms)
        row: dict = {
            "cascade_id": c.cascade_id,
            "exchange": c.exchange,
            "kind": c.kind,
            "start_ms": c.start_ms,
            "start_utc": _iso(c.start_ms),
            "end_ms": c.end_ms,
            "end_utc": _iso(c.end_ms),
            "n_events": c.n_events,
            "total_size": c.total_size,
            "direction": c.direction,
            "first_price": c.first_price,
            "last_price": c.last_price,
            "anchor_ts_ms": anchor[0] if anchor else None,
            "anchor_price": anchor[1] if anchor else float("nan"),
        }
        for h in horizons_min:
            col = f"bp_{h}m"
            if anchor is None:
                row[col] = float("nan")
                continue
            fut = prices.at_or_before(c.end_ms + h * 60_000, future_max_staleness_ms)
            row[col] = float("nan") if fut is None else (fut[1] - anchor[1]) / anchor[1] * 10_000.0
        rows.append(row)
    return rows


# --------------------------------------------------------------------------- #
# 核 3: 対照群の構成
# --------------------------------------------------------------------------- #

def _overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start <= b_end and b_start <= a_end


def sample_placebo_windows(
    cascades: Sequence[Cascade],
    volume_bars: Sequence[tuple[int, int, float]],
    liquidation_events: Sequence[LiquidationEvent],
    exchange: str,
    size_tolerance: float = 0.25,
    rng: random.Random | None = None,
) -> list[Cascade]:
    """規模を揃えた「清算を伴わない出来高の急増」を、カスケードと同じ形で返す。

    `volume_bars` は `(start_ms, end_ms, volume)` の等幅バー列(例: 1 分ごとの出来高)。
    各実カスケードについて、同じ長さ(バー本数換算)の連続窓をスライドさせて総出来高を求め、
    (a) `liquidation_events` を 1 件も含まず、(b) 総出来高が `total_size` の
    `±size_tolerance` 以内、の候補からランダムに 1 つ選ぶ(`rng` で再現可能にする)。
    候補が無いカスケードは**プラセボを作らずスキップする**(規模を揃えられない対照は
    「揃っていない対照」として混ぜない。判定基準ではなく整合性の話)。

    **`size_tolerance=0.25` は判断の置き所**: 「規模を揃える」の許容誤差は原文に無く、
    見つかりやすさとの折り合いで置いた既定値。事前登録前に見直す前提。
    """
    rng = rng or random.Random(0)
    if not volume_bars:
        return []
    bars = sorted(volume_bars, key=lambda b: b[0])
    bar_ms = bars[0][1] - bars[0][0]
    assert bar_ms > 0, "volume_bars は幅 0 のバーを含んでいる"
    ev_starts = sorted(e.ts_ms for e in liquidation_events if e.exchange == exchange)

    def has_liquidation(start_ms: int, end_ms: int) -> bool:
        i = bisect.bisect_left(ev_starts, start_ms)
        return i < len(ev_starts) and ev_starts[i] <= end_ms

    chosen_intervals: list[tuple[int, int]] = []
    out: list[Cascade] = []
    for c in cascades:
        duration_ms = max(c.end_ms - c.start_ms, bar_ms)
        window_bars = max(1, round(duration_ms / bar_ms))
        candidates = []
        for i in range(0, len(bars) - window_bars + 1):
            w_start, w_end = bars[i][0], bars[i + window_bars - 1][1]
            vol = sum(b[2] for b in bars[i:i + window_bars])
            if c.total_size > 0 and abs(vol - c.total_size) / c.total_size > size_tolerance:
                continue
            if has_liquidation(w_start, w_end):
                continue
            if any(_overlaps(w_start, w_end, s, e) for s, e in chosen_intervals):
                continue
            candidates.append((w_start, w_end, vol))
        if not candidates:
            continue
        w_start, w_end, vol = rng.choice(candidates)
        chosen_intervals.append((w_start, w_end))
        out.append(Cascade(
            cascade_id=f"{exchange}_placebo_{len(out):06d}",
            exchange=exchange, kind="placebo",
            start_ms=w_start, end_ms=w_end,
            n_events=0, total_size=vol, direction="none",
            first_price=None, last_price=None,
        ))
    return out


def sample_no_liquidation_windows(
    cascades: Sequence[Cascade],
    liquidation_events: Sequence[LiquidationEvent],
    exchange: str,
    span_start_ms: int,
    span_end_ms: int,
    rng: random.Random | None = None,
    max_attempts: int = 200,
) -> list[Cascade]:
    """清算の無い時間帯を、各カスケードと同じ長さでカスケードと同じ形で返す。

    `[span_start_ms, span_end_ms)` の中からランダムに開始点を選び、その取引所の
    清算イベントを 1 件も含まない窓(かつ他の選出済み窓とも重ならない)が見つかるまで
    `max_attempts` 回まで再抽選する。見つからないカスケードは**スキップする**
    (無理に重ねて偽の「無清算」を作らない)。

    **`max_attempts=200` は判断の置き所**: 有限の再抽選回数を置かないと、
    清算が密な期間ではいつまでも見つからず無限ループになるため。事前登録前に見直す前提。
    """
    rng = rng or random.Random(0)
    ev_starts = sorted(e.ts_ms for e in liquidation_events if e.exchange == exchange)

    def has_liquidation(start_ms: int, end_ms: int) -> bool:
        i = bisect.bisect_left(ev_starts, start_ms)
        return i < len(ev_starts) and ev_starts[i] <= end_ms

    chosen: list[tuple[int, int]] = []
    out: list[Cascade] = []
    for c in cascades:
        duration_ms = max(c.end_ms - c.start_ms, 1)
        if span_end_ms - span_start_ms <= duration_ms:
            continue
        found = None
        for _ in range(max_attempts):
            w_start = rng.randint(span_start_ms, span_end_ms - duration_ms)
            w_end = w_start + duration_ms
            if has_liquidation(w_start, w_end):
                continue
            if any(_overlaps(w_start, w_end, s, e) for s, e in chosen):
                continue
            found = (w_start, w_end)
            break
        if found is None:
            continue
        chosen.append(found)
        out.append(Cascade(
            cascade_id=f"{exchange}_no_liq_{len(out):06d}",
            exchange=exchange, kind="no_liquidation",
            start_ms=found[0], end_ms=found[1],
            n_events=0, total_size=0.0, direction="none",
            first_price=None, last_price=None,
        ))
    return out


# --------------------------------------------------------------------------- #
# まとめ(行数の確認までしか行わない = 判定ではない集計)
# --------------------------------------------------------------------------- #

CSV_COLUMNS: tuple[str, ...] = (
    "cascade_id", "exchange", "kind", "start_ms", "start_utc", "end_ms", "end_utc",
    "n_events", "total_size", "direction", "first_price", "last_price",
    "anchor_ts_ms", "anchor_price",
    *(f"bp_{h}m" for h in DEFAULT_HORIZONS_MIN),
)


def build_dataset(
    real_cascades: Sequence[Cascade],
    placebo_cascades: Sequence[Cascade],
    no_liq_cascades: Sequence[Cascade],
    prices: PriceSeries,
    horizons_min: Sequence[int] = DEFAULT_HORIZONS_MIN,
) -> list[dict]:
    """3 種のカスケードをまとめて反応窓を計算し、1 行 1 カスケードの表にする。

    ここで行うのは**行数を数えられる形に整えるだけ**で、平均・有意性は計算しない
    (`research-protocol` §0.5 の事前登録より前の段階)。
    """
    all_cascades = list(real_cascades) + list(placebo_cascades) + list(no_liq_cascades)
    return compute_reactions(all_cascades, prices, horizons_min=horizons_min)


def write_csv(rows: Sequence[dict], path: str | Path, columns: Sequence[str] = CSV_COLUMNS) -> None:
    """`rows` を CSV に書く。欠けている列は空欄(NaN はそのまま文字列 "nan" で出す)。"""
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in columns})
