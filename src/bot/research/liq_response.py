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
4. `attach_internal_direction` / `reversal_scores` / `compute_reversal` — 「転換」
   (内部の値動きと、その後の反応の符号が逆か)。**タイ(内部の値動きがちょうど 0)を
   既定では落とさず**、落とす場合も件数と群ごとの除外率を必ず戻り値に載せ、
   除外率が群間で離れたら既定で例外にする(`ReversalExclusionImbalance`)。

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
    zips = sorted(root.glob("*-liquidationSnapshot-*.zip"))
    if not zips:
        # 黙って 0 件を返さない(2026-09-13、read_rows と同じ欠陥をここでも塞ぐ)。
        # パスを 1 階層間違えると空が返り、「清算が無かった」と読めてしまう。
        raise FileNotFoundError(
            f"liquidationSnapshot の zip が 1 つも見つからない: {root} "
            f"(期待するのは .../liquidationSnapshot/<SYMBOL>/ のような zip を直接含むディレクトリ)"
        )
    events: list[LiquidationEvent] = []
    for zpath in zips:
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
# 核 3-bis: 「転換」(内部の値動きと、その後の反応の符号が逆か)
#
# 段 0 の実行スクリプトが実行時に操作的に定義した統計量を、測定器の側に移したもの。
# 実行時の定義は `internal_bp == 0`(タイ)の行を **NaN として黙って落として**いた。
# カスケードは数秒〜数十秒で終わるため 1 分バーでは起点と終点が同じ終値になり、
# タイは実カスケードで 8 割、窓の長いプラセボで 0% と **群間で非対称に**発生する。
# ここでは (a) 既定でタイを落とさない、(b) 落とした件数を必ず返す、
# (c) 群ごとの除外率を必ず返す、(d) 除外率が群間で離れたら既定で例外、とする。
# --------------------------------------------------------------------------- #

TiePolicy = Literal["keep", "drop", "refine"]

INTERNAL_BP_KEY = "internal_bp"
INTERNAL_BP_FINE_KEY = "internal_bp_fine"


class ReversalExclusionImbalance(RuntimeError):
    """群ごとの除外率が離れすぎているときに `compute_reversal(strict=True)` が送出する。

    「黙って落とした部分集合どうしを比べていた」という事故(段 0 の転換指標)を
    二度と静かに通さないためのもの。`liquidations.read_rows` と同じ約束で、
    **既定が strict=True**、診断目的でどうしても通したいときだけ `strict=False`。
    """


def _as_float(v: object) -> float:
    """数にならないもの(None・空欄・文字列 "nan")は NaN にする。**0.0 にはしない。**"""
    if v is None:
        return float("nan")
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return float("nan")


def _sign(x: float) -> float:
    """符号。**タイ(0)は 0 を返す**(NaN にしない)。NaN は NaN のまま。"""
    if x != x:  # NaN
        return float("nan")
    if x > 0:
        return 1.0
    if x < 0:
        return -1.0
    return 0.0


def attach_internal_direction(
    rows: Sequence[dict],
    prices: PriceSeries,
    max_staleness_ms: int | None = 300_000,
    key: str = INTERNAL_BP_KEY,
    fine_key: str = INTERNAL_BP_FINE_KEY,
) -> list[dict]:
    """各行に「内部の値動き」(窓の始め → 終わりの価格変化、bp)を 2 つの分解能で付ける。

    - `key`(**粗い**。段 0 の判定時と逐語で同じ定義): 価格系列から
      `at_or_before(start_ms)` を起点、行の `anchor_price`(= `at_or_before(end_ms)`)を終点にする。
      価格系列が 1 分バーの終値のとき、**窓が 1 本のバーに収まれば起点と終点は同じ終値**になり、
      値はちょうど 0(タイ)になる。これは欠測ではなく**分解能の不足**である。
    - `fine_key`(**細かい**): カスケード自身が持つ `first_price` / `last_price`
      (清算約定そのものの価格)から計算する。両方ある行だけで、
      **対照窓(プラセボ・無清算窓)は持たないので NaN**。

    行は**落とさない**(`compute_reactions` と同じ約束)。引けない行は NaN を入れるだけ。
    戻り値は入力の `rows` そのもの(その場で書き込む)。
    """
    for r in rows:
        anchor_start = prices.at_or_before(int(r["start_ms"]), max_staleness_ms)
        end_price = _as_float(r.get("anchor_price"))
        if anchor_start is None or end_price != end_price or not anchor_start[1]:
            r[key] = float("nan")
        else:
            sp = anchor_start[1]
            r[key] = (end_price - sp) / sp * 10_000.0

        fp, lp = _as_float(r.get("first_price")), _as_float(r.get("last_price"))
        if fp != fp or lp != lp or fp == 0.0:
            r[fine_key] = float("nan")
        else:
            r[fine_key] = (lp - fp) / fp * 10_000.0
    return list(rows)


def _fine_internal_bp(row: dict, fine_key: str = INTERNAL_BP_FINE_KEY) -> float:
    """細かい分解能の内部方向。`fine_key` が無ければ `first_price`/`last_price` から作る。

    `attach_internal_direction` を通していない行(`compute_reactions` の出力そのまま)でも
    `tie_policy="refine"` が働くようにするため。作れない行は NaN(0.0 にしない)。
    """
    v = _as_float(row.get(fine_key))
    if v == v:
        return v
    fp, lp = _as_float(row.get("first_price")), _as_float(row.get("last_price"))
    if fp != fp or lp != lp or fp == 0.0:
        return float("nan")
    return (lp - fp) / fp * 10_000.0


@dataclass(frozen=True)
class ReversalGroup:
    """1 群ぶんの転換スコアと、**何を落としたかの内訳**。

    `scores` は実際に集計に使える有限値だけを並べたもの。落とした行は必ず
    `n_excluded_tie` / `n_excluded_missing` のどちらかに数えられ、
    `n_rows == len(scores) + n_excluded_tie + n_excluded_missing` が常に成り立つ。
    """

    name: str
    n_rows: int
    scores: list[float]
    n_tie: int                 # 粗い内部方向が 0 だった行(方針に関わらず数える)
    n_tie_resolved: int        # そのうち細かい分解能で符号が付いた行(refine のときのみ)
    n_excluded_tie: int        # タイとして除外した行(drop のときのみ > 0)
    n_excluded_missing: int    # 内部方向か反応 bp が NaN で計算できなかった行

    @property
    def n_used(self) -> int:
        return len(self.scores)

    @property
    def n_excluded(self) -> int:
        return self.n_excluded_tie + self.n_excluded_missing

    @property
    def exclusion_rate(self) -> float:
        """除外率(0 行なら NaN。**0 を返して「除外なし」に見せない**)。"""
        if self.n_rows == 0:
            return float("nan")
        return self.n_excluded / self.n_rows

    @property
    def tie_rate(self) -> float:
        if self.n_rows == 0:
            return float("nan")
        return self.n_tie / self.n_rows

    @property
    def mean(self) -> float:
        if not self.scores:
            return float("nan")
        return sum(self.scores) / len(self.scores)


@dataclass(frozen=True)
class ReversalReport:
    """群をまたいだ転換スコアの計算結果。**除外率を群ごとに必ず持ち歩く。**"""

    bp_key: str
    tie_policy: TiePolicy
    groups: dict[str, ReversalGroup]

    @property
    def exclusion_rates(self) -> dict[str, float]:
        return {name: g.exclusion_rate for name, g in self.groups.items()}

    @property
    def max_exclusion_gap(self) -> float:
        """群どうしの除外率の差の最大値(1 群以下なら 0.0)。NaN の群は除く。"""
        rates = [r for r in self.exclusion_rates.values() if r == r]
        if len(rates) < 2:
            return 0.0
        return max(rates) - min(rates)

    def scores(self, name: str) -> list[float]:
        return self.groups[name].scores

    def summary_rows(self) -> list[dict]:
        """表に貼れる形(1 群 1 行)。件数と除外率を必ず含む。"""
        return [
            {
                "group": g.name, "n_rows": g.n_rows, "n_used": g.n_used,
                "n_tie": g.n_tie, "n_tie_resolved": g.n_tie_resolved,
                "n_excluded_tie": g.n_excluded_tie,
                "n_excluded_missing": g.n_excluded_missing,
                "exclusion_rate": g.exclusion_rate, "tie_rate": g.tie_rate,
                "mean": g.mean,
            }
            for g in self.groups.values()
        ]


def reversal_scores(
    rows: Sequence[dict],
    bp_key: str,
    name: str = "group",
    tie_policy: TiePolicy = "keep",
    internal_key: str = INTERNAL_BP_KEY,
    fine_key: str = INTERNAL_BP_FINE_KEY,
) -> ReversalGroup:
    """1 群ぶんの転換スコア `-sign(内部の値動き) × 反応bp` を作る。

    `tie_policy`(**既定は `"keep"` = 落とさない**):

    - `"keep"`: タイ(内部の値動きがちょうど 0)を**別の水準として残す**。
      `sign = 0` なのでスコアは 0 になる(「どちらへも転換していない」)。
      **行は落ちない**ので群ごとの件数が非対称に減らない。
      ただし推定量は「タイを 0 と見なした平均」であり、`"drop"` の平均とは**別の量**である。
    - `"drop"`: タイを除外する(段 0 の実行時の振る舞い)。**除外件数は必ず
      `n_excluded_tie` に現れる。**群間で除外率が違えば `compute_reversal` が例外にする。
    - `"refine"`: タイの行だけ**分解能を上げて**判定し直す。粗い内部方向(1 分バーの終値差)が
      0 でも、カスケード自身の `first_price` → `last_price` に符号があればそれを使う
      (`fine_key` があればそれを、無ければ `first_price`/`last_price` から作る)。
      それでも 0 のまま、または細かい値が無い行は `"keep"` と同じく 0 のまま残す(落とさない)。
      **対照窓は `first_price`/`last_price` を持たない**ので、この方針は実群だけを細かくする。
      分解能が群で揃わなくなるので、主にはせず感度として使うこと。

    NaN(内部方向が引けない / 反応 bp が引けない)は `n_excluded_missing` に数える。
    これは分解能の問題ではなく本物の欠測なので、どの方針でも集計に入れない。
    """
    scores: list[float] = []
    n_tie = n_tie_resolved = n_excluded_tie = n_excluded_missing = 0
    for r in rows:
        internal = _as_float(r.get(internal_key))
        bp = _as_float(r.get(bp_key))
        if internal != internal or bp != bp:
            n_excluded_missing += 1
            continue
        sign = _sign(internal)
        if sign == 0.0:
            n_tie += 1
            if tie_policy == "drop":
                n_excluded_tie += 1
                continue
            if tie_policy == "refine":
                fine_sign = _sign(_fine_internal_bp(r, fine_key))
                if fine_sign == fine_sign and fine_sign != 0.0:
                    sign = fine_sign
                    n_tie_resolved += 1
        scores.append(0.0 if sign == 0.0 else -sign * bp)
    return ReversalGroup(
        name=name, n_rows=len(rows), scores=scores,
        n_tie=n_tie, n_tie_resolved=n_tie_resolved,
        n_excluded_tie=n_excluded_tie, n_excluded_missing=n_excluded_missing,
    )


def compute_reversal(
    groups: "dict[str, Sequence[dict]]",
    bp_key: str,
    tie_policy: TiePolicy = "keep",
    internal_key: str = INTERNAL_BP_KEY,
    fine_key: str = INTERNAL_BP_FINE_KEY,
    strict: bool = True,
    max_exclusion_gap: float = 0.10,
) -> ReversalReport:
    """複数の群の転換スコアをまとめて作り、**群ごとの除外率を突き合わせる**。

    `strict=True`(既定・`liquidations.read_rows` と同じ約束): 群どうしの除外率の差が
    `max_exclusion_gap`(既定 0.10 = 10 ポイント)を**超えたら
    `ReversalExclusionImbalance` を送出する**(警告ではなく例外)。
    非無作為に落とした部分集合と、ほぼ全部残った群とを比べる形を黙って通さないため。
    `strict=False` を明示したときだけ、除外率を戻り値に持たせたまま先へ通す。
    """
    report = ReversalReport(
        bp_key=bp_key, tie_policy=tie_policy,
        groups={
            name: reversal_scores(
                rows, bp_key, name=name, tie_policy=tie_policy,
                internal_key=internal_key, fine_key=fine_key,
            )
            for name, rows in groups.items()
        },
    )
    gap = report.max_exclusion_gap
    if strict and gap > max_exclusion_gap:
        detail = ", ".join(
            f"{n}={g.n_excluded}/{g.n_rows}({g.exclusion_rate:.1%}; tie={g.n_excluded_tie})"
            for n, g in report.groups.items()
        )
        raise ReversalExclusionImbalance(
            f"{bp_key}: 群間の除外率の差 {gap:.1%} が上限 {max_exclusion_gap:.1%} を超えた [{detail}]。"
            f"tie_policy='keep' なら落とさない。診断目的で通すなら strict=False を明示する"
        )
    return report


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
