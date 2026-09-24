"""Scene set for item 0 (the core). Single source of truth.

`DEFINITIONS.md` next to this file is generated from this module by
`gen_definitions.py`; `test_battery_item0.py` fails when the two differ.

Every scene -- value scene or capability scene -- carries an `expected`
result fixed BEFORE any engine is run, and `run_battery.py` grades what the
target actually produced against it (rule 1). Capability scenes say which
observable result only a working capability can produce; nothing is graded
on a declaration, a type name or an attribute being present (rule 2).

Viewpoints are the seven of the fixed requirements file
docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md §2
(P0-1 .. P0-7). Every viewpoint has at least one value scene (rule 3).
No tool or product name appears in this file.

Common conventions (they are part of every scene's input):
  * times are ints, nanoseconds since 1970-01-01T00:00:00Z (UTC);
  * `T0` = 1_700_006_400_000_000_000 (2023-11-15T00:00:00Z), `S` = 1 s, `DAY` = 1 day;
  * events are one DAY apart unless the scene measures time itself (P0-2,
    same-time P0-5, the millisecond latency scene), so tools that only take
    daily bars on a calendar can be measured on everything else;
  * an event is a dict with `kind` (trade / book_snapshot / book_delta / bar /
    funding / liquidation) and `ts_ns` (exchange time); `recv_ns` (the time
    our process can first receive it) defaults to `ts_ns`;
  * a bar's `ts_ns` is the time the bar is complete (its close time);
  * in scenes where our order trades, each market trade is 100 units, well
    above the 1-unit order, so a target's volume cap does not decide them;
  * a scene whose input has `any_type: True` measures something other than
    event types: for a target that does not take trades, each trade may be
    replaced by a bar at the same time with open = high = low = close =
    the trade's price (and the same receive time); the adapter says so;
  * an adapter hands the events to the target in the order and the grouping
    given; it never sorts, merges or drops events itself (that is what is
    being measured);
  * "observed" values are what the target handed to the strategy inside
    its callbacks, recorded by the strategy at that moment -- not values
    read from a result object after the run;
  * what a scene measures (an event type, a time conversion, a read of the
    past, an order) counts only when the target's own code produced it
    (round r6-1): an event carried in a type the adapter made, a value the
    strategy kept itself, a conversion the adapter called itself do not
    count; a target without the type or the means is "not supported".
    run_battery.py checks where each measured thing came from
    (`SceneResult.provenance`) before it grades.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Any, Literal

SceneKind = Literal["value", "capability"]

T0 = 1_700_006_400_000_000_000  # 2023-11-15T00:00:00Z (a Wednesday, midnight UTC)
S = 1_000_000_000
DAY = 86_400 * S
MS = 1_000_000

# P0-4 p4-future-read-attempt: the ways of naming the 5th bar, fixed here for
# every target (round r6-1, critic i0-r5-03). `n` is the position right after
# the newest delivered event, in the target's own way of counting; `fut` the
# 5th bar's time, `now` the probe time, `first` the first event's time.
POSITION_NAMINGS = ("[n]", "[n:]", "[n:n+1]", "[n-1:n+1]", "[n::2]", "[n:n]", "[n::-1]", "[:n:-1]")
TIME_NAMINGS = {
    "time_at": ("at(fut)",),
    "time_until": ("until(fut)", "until(fut+1d)"),
    "time_since": ("since(fut)", "since(now+1ns)"),
    "time_range": ("range(first,fut)", "range(fut,fut)", "range(now+1ns,fut+1d)"),
}
NAMING_SHAPES = {"position": POSITION_NAMINGS, **TIME_NAMINGS, "next_call": ("next",)}

VIEWPOINTS = {
    "P0-1": "核が事象駆動(型を持つ事象を時刻順に流す)であること",
    "P0-2": "時刻が UTC の int64 ナノ秒で表されること",
    "P0-3": "8 種の事象型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知)を扱えること",
    "P0-4": "戦略が「受け取れた時刻 ≤ 今」の事象しか見られないこと(構造で)",
    "P0-5": "同時刻の事象の並びが決定的で、規則に従うこと",
    "P0-6": "戦略の API(事象ごとの呼び出し・発注・取消)",
    "P0-7": "他項目が核を書き換えずに差し込める口(約定模型・遅延模型・費用・口座)",
}


@dataclass(frozen=True)
class Scene:
    id: str
    viewpoint: str          # "P0-1" .. "P0-7"
    kind: SceneKind
    title: str
    input: dict[str, Any]
    expected: Any           # the correct result, fixed before any run
    derivation: str         # how `expected` was obtained, without any engine
    measures: str           # what the scene measures, one or two sentences
    graded_from: str = ""   # when set: the graded values are computed by run_battery.py
                            # (never by the adapter) from the raw output, as this text says


def trade(ts: int, price: float, qty: float = 0.01, side: str = "buy", recv: int | None = None) -> dict:
    e = {"kind": "trade", "ts_ns": ts, "price": price, "qty": qty, "side": side}
    if recv is not None:
        e["recv_ns"] = recv
    return e


def bar(ts: int, close: float, o: float | None = None, h: float | None = None,
        lo: float | None = None, vol: float = 1.0) -> dict:
    return {"kind": "bar", "ts_ns": ts, "open": close if o is None else o,
            "high": close if h is None else h, "low": close if lo is None else lo,
            "close": close, "volume": vol}


SAMPLES: dict[str, dict] = {
    "trade": trade(T0 + DAY, 5_012_345.0, 0.01, "buy"),
    "book_snapshot": {"kind": "book_snapshot", "ts_ns": T0 + DAY,
                      "bids": [[5_012_000.0, 0.5], [5_011_000.0, 1.0]],
                      "asks": [[5_012_500.0, 0.4], [5_013_000.0, 2.0]]},
    "book_delta": {"kind": "book_delta", "ts_ns": T0 + DAY, "side": "bid", "price": 5_012_000.0, "qty": 0.3},
    "bar": bar(T0 + DAY, 100.5, 100.0, 101.0, 99.0, 12.0),
    "funding": {"kind": "funding", "ts_ns": T0 + DAY, "rate": 0.0001},
    "liquidation": {"kind": "liquidation", "ts_ns": T0 + DAY, "price": 4_990_000.0, "qty": 0.2, "side": "sell"},
}
JP = {"trade": "約定", "book_snapshot": "板の写真", "book_delta": "板の差分", "bar": "足",
      "funding": "資金調達", "liquidation": "清算", "clock": "時計"}

SCENES: list[Scene] = []


def add(**kw: Any) -> None:
    SCENES.append(Scene(**kw))


# ---------------------------------------------------------------- P0-1
_MERGE_STREAMS = {
    "trades": [trade(T0 + 2 * DAY, 101.0), trade(T0 + 5 * DAY, 104.0)],
    "bars": [bar(T0 + 1 * DAY, 100.0), bar(T0 + 4 * DAY, 103.0)],
    "funding": [{"kind": "funding", "ts_ns": T0 + 3 * DAY, "rate": 0.0001}],
}
add(id="p1-merge-by-time", viewpoint="P0-1", kind="value",
    title="型ごとに分かれた入力を、渡した順ではなく時刻の順に処理するか",
    input={"streams": _MERGE_STREAMS, "hand_over_order": ["trades", "bars", "funding"],
           "note": "3 つの入力をこの順で渡す。1 本の入力しか受けない対象には、この順に連結して渡す(並べ替えない)"},
    expected={"sequence": [["bar", T0 + 1 * DAY], ["trade", T0 + 2 * DAY], ["funding", T0 + 3 * DAY],
                           ["bar", T0 + 4 * DAY], ["trade", T0 + 5 * DAY]]},
    derivation="5 件の時刻は T0 から 1,2,3,4,5 日後で互いに異なる。時刻の昇順に並べると 足(1)・約定(2)・資金調達(3)・足(4)・約定(5)。"
               "渡した順(約定,約定,足,足,資金調達)のまま処理すれば 2,5,1,4,3 日の順になり一致しない。",
    measures="戦略の呼び出しごとに記録した(事象の型, 時刻)の列が、時刻の昇順と一致するか。")

_SEQ_BARS = [bar(T0 + (i + 1) * DAY, 100.0 + i) for i in range(5)]
add(id="p1-one-call-per-event", viewpoint="P0-1", kind="value",
    title="事象 1 件ごとに戦略が 1 回呼ばれ、呼ばれたときの時刻がその事象の時刻か",
    input={"events": _SEQ_BARS},
    expected={"sequence": [["bar", e["ts_ns"]] for e in _SEQ_BARS]},
    derivation="入力は 1 日おきの足 5 本(時刻の昇順)。事象ごとに 1 回呼ぶなら呼び出しは 5 回で、各回の(型, 時刻)は入力と同じ。"
               "恒等写像なので計算は要らない。",
    measures="呼び出しの回数と、各呼び出しで戦略が受け取った事象の型と時刻。")

add(id="p1-typed-events", viewpoint="P0-1", kind="capability",
    title="戦略が受け取った事象の型を見分けられるか",
    input={"events": [bar(T0 + 1 * DAY, 100.0), trade(T0 + 2 * DAY, 100.5)]},
    expected={"sequence": [["bar", T0 + 1 * DAY], ["trade", T0 + 2 * DAY]]},
    derivation="足 1 件と約定 1 件を時刻の昇順で 1 本の入力に入れる。型を持つ事象が 1 件ずつ届くなら、"
               "戦略は 2 回呼ばれ、1 回目に足、2 回目に約定を受け取る。型を区別できなければ型の欄を埋められない。",
    measures="戦略が呼ばれた時に受け取ったものから、足と約定の別を戦略自身が判別できたか(判別した結果の列)。")

# ---------------------------------------------------------------- P0-2
ISO_Z = "2024-01-01T00:00:00.123456789Z"
ISO_JST = "2024-01-01T09:00:00.123456789+09:00"
ISO_NS = 1_704_067_200_123_456_789
_ISO_NOTE = ("対象がデータを読むときに使う、対象自身の時刻の変換を使う: ISO の文字列を、対象のデータの入口(対象が読む表・ファイル・"
             "記録の時刻の欄、または対象が公開する時刻の変換の関数)にそのまま渡し、対象が作った時刻を int ナノ秒で読む。"
             "adapter が自分で変換(pandas・polars・標準の datetime など、対象の入口を通らない呼び出し)をしない。"
             "時刻の文字列を受ける入口が無い対象は「対応なし」(何を渡して何が起きたかを書く)")
add(id="p2-iso-utc", viewpoint="P0-2", kind="value",
    title="ナノ秒つきの ISO 8601(UTC)を対象自身の変換で int64 ナノ秒にした値",
    input={"iso": ISO_Z, "note": _ISO_NOTE},
    expected=ISO_NS,
    derivation="1970-01-01 から 2024-01-01 までの日数 = 54 年 × 365 + うるう日 13(1972〜2020)= 19,723 日。"
               "19,723 × 86,400 = 1,704,067,200 秒。小数部 0.123456789 秒 = 123,456,789 ns を足して "
               "1,704,067,200,123,456,789。",
    measures="小数第 9 位まで丸めずに int64 ナノ秒になるか。")
add(id="p2-iso-offset", viewpoint="P0-2", kind="value",
    title="時差つき(+09:00)の ISO 8601 を UTC の int64 ナノ秒にした値",
    input={"iso": ISO_JST, "note": _ISO_NOTE},
    expected=ISO_NS,
    derivation="+09:00 の 09:00:00.123456789 は UTC の 00:00:00.123456789。よって p2-iso-utc と同じ 1,704,067,200,123,456,789。",
    measures="時差を UTC に直すか(時差を捨てて 9 時間ずれないか)。")
add(id="p2-event-time-exact", viewpoint="P0-2", kind="value",
    title="ナノ秒の端数をもつ事象の時刻が、戦略に届いた時点で 1 ns も変わらないか",
    input={"events": [{"ts_ns": T0 + 123_456_789}],
           "note": "型は対象が受ける型(対象の配布物の型)を 1 つ選んでよい(足なら OHLC はすべて 100.0、約定なら 価格 100.0 数量 0.01)"},
    expected={"observed_ts_ns": [T0 + 123_456_789]},
    derivation="入力の時刻そのもの(恒等写像)。1,700,000,000,123,456,789 ns。",
    measures="戦略が受け取った事象の時刻を int ナノ秒で読んだ値。")
add(id="p2-one-ns-apart", viewpoint="P0-2", kind="capability",
    title="1 ns だけ離れた 2 つの事象の時刻を別の値として保てるか",
    input={"events": [{"ts_ns": T0}, {"ts_ns": T0 + 1}],
           "note": "型は対象が受ける型(対象の配布物の型)を 1 つ選んでよい(2 件とも同じ型)"},
    expected={"observed_ts_ns": [T0, T0 + 1]},
    derivation="int64 ナノ秒なら T0 と T0+1 は別の整数。float64 は 2^53 を超える整数を 256 刻みでしか表せないので"
               "(1.7e18 の近くの間隔は 256)、秒やナノ秒を float で持つと 2 つは同じ値になる。マイクロ秒止まりの型でも同じ値になる。",
    measures="戦略が受け取った 2 件の時刻(int ナノ秒)。")

# ---------------------------------------------------------------- P0-3
for _k in ["trade", "book_snapshot", "book_delta", "bar", "funding", "liquidation"]:
    _s = dict(SAMPLES[_k])
    add(id=f"p3-{_k}", viewpoint="P0-3", kind="capability",
        title=f"事象型「{JP[_k]}」を事象として戦略に届けられるか",
        input={"events": [_s]},
        expected={"sequence": [[_k, _s["ts_ns"]]],
                  "fields": {k: v for k, v in _s.items() if k not in ("kind", "ts_ns")}},
        derivation=f"「{JP[_k]}」1 件だけを入れる。届けられるなら戦略は 1 回呼ばれ、型は「{JP[_k]}」、中身は入力と同じ(恒等写像)。"
                   "型が無い対象は「対応なし」(明示の拒否、または対象の配布物にその型が無いことを確かめた)になる。"
                   "型は対象の配布物が持つ型で運ぶ。adapter が作った型(対象の基の class の子・欄を足した基の class・型の印を付けた辞書や関数)で運んだものは、"
                   "その型を対象が持つことに数えない(固定した要件 P0-3 の測り方「型が無ければ『対応なし』」)。",
        measures=f"戦略が受け取った事象の型・時刻・中身が入力の「{JP[_k]}」と一致するか。")

_MIXED = [dict(SAMPLES[k], ts_ns=T0 + (i + 1) * DAY)
          for i, k in enumerate(["trade", "book_snapshot", "book_delta", "bar", "funding", "liquidation"])]
add(id="p3-mixed-one-run", viewpoint="P0-3", kind="value",
    title="6 種の市場の事象を 1 回の実行に混ぜて入れたとき、型と時刻の列",
    input={"events": _MIXED},
    expected={"sequence": [[e["kind"], e["ts_ns"]] for e in _MIXED]},
    derivation="約定・板の写真・板の差分・足・資金調達・清算を 1〜6 日後に 1 件ずつ、時刻の昇順で 1 本の入力に入れる。"
               "期待は入力の(型, 時刻)の列そのもの。",
    measures="1 回の実行の中で 6 種が同じ流れに載るか。")

add(id="p3-clock-timer", viewpoint="P0-3", kind="capability",
    title="戦略が頼んだ時刻に、時計の事象で呼ばれるか",
    input={"any_type": True, "events": [trade(T0 + 1 * DAY, 100.0, qty=100.0), trade(T0 + 6 * DAY, 100.0, qty=100.0)],
           "strategy": "1 回目の呼び出し(1 日後)で「4 日後(T0 + 4 DAY)に起こして」と頼む。型は対象が受ける型でよい", "timer_at_ns": T0 + 4 * DAY},
    expected={"clock_calls_ns": [T0 + 4 * DAY]},
    derivation="頼んだ時刻は T0 + 4 日。データの事象は 1 日後と 6 日後にしか無いので、4 日後ちょうどに呼ばれるのは時計の事象だけ。",
    measures="データの事象が無い時刻に、時計の事象として戦略が呼ばれた時刻の列。")

_NOTICE_TRADES = [trade(T0 + i * DAY, 100.0, qty=100.0) for i in (1, 2, 3)]
add(id="p3-notice-accepted", viewpoint="P0-3", kind="capability",
    title="注文の受付の通知が、事象として戦略に届くか",
    input={"any_type": True, "events": _NOTICE_TRADES,
           "strategy": "1 回目の呼び出しで 指値 買い 数量 1 価格 90.0 を出す(市場は 100.0 なので埋まらない)"},
    expected={"notices": ["accepted"]},
    derivation="価格 90 の買い指値は、約定が 100 のまま続くので埋まらない。取消もしない。よって戦略に届く通知は受付の 1 件だけ。",
    measures="戦略が受け取った、その注文についての通知の種類の列。受け取ったとは、戦略の呼び出しに事象として届いたか、発注の呼び出しの戻り値・例外としてその場で返ったこと。後から戦略が問い合わせて得たものは数えない。")
add(id="p3-notice-rejected", viewpoint="P0-3", kind="capability",
    title="注文の拒否の通知が、事象として戦略に届くか",
    input={"any_type": True, "events": [trade(T0 + i * DAY, 1_000_000.0, qty=100.0) for i in (1, 2, 3)],
           "account": "現金 1,000 円、レバレッジ無し(現物の口座)",
           "strategy": "1 回目の呼び出しで 成行 買い 数量 1 を出す"},
    expected={"notices": ["rejected"]},
    derivation="必要な資金は 1 × 1,000,000 = 1,000,000 円で、現金 1,000 円を超える。レバレッジ無しなので受けられず、"
               "届く通知は拒否の 1 件だけ。",
    measures="戦略が受け取った通知の種類の列(受け取ったの意味は p3-notice-accepted と同じ)。")
add(id="p3-notice-filled", viewpoint="P0-3", kind="capability",
    title="注文の約定の通知が、事象として戦略に届くか",
    input={"any_type": True, "events": _NOTICE_TRADES, "account": "現金 1,000,000 円",
           "strategy": "1 回目の呼び出しで 成行 買い 数量 1 を出す"},
    expected={"filled_qty_in_notices": 1.0},
    derivation="成行の買い 1 は、次の約定(100.0)で全量が埋まる。資金は 100 円で足りる。"
               "戦略が受け取った約定の通知の数量の合計は 1.0。価格は約定の模型によるので見ない。",
    measures="戦略が受け取った約定の通知の数量の合計(受け取ったの意味は p3-notice-accepted と同じ)。")

# ---------------------------------------------------------------- P0-4
_LA_BARS = [bar(T0 + (i + 1) * DAY, 100.0 + i) for i in range(6)]
add(id="p4-visible-at-step", viewpoint="P0-4", kind="value",
    title="4 本目の足の時刻(T0 + 4 日)の呼び出しで、戦略が見られる足の数と最大の終値",
    input={"events": _LA_BARS, "probe_at_ns": T0 + 4 * DAY,
           "note": "足を受けない対象は、同じ時刻・価格=終値の約定で代えてよい"},
    expected={"visible_count": 4, "max_visible_close": 103.0},
    derivation="終値は 100,101,102,103,104,105 と 1 ずつ増え、n 本目の足の時刻は T0 + n 日。T0 + 4 日の呼び出しの時点で届いているのは 1〜4 本目だけなので、"
               "件数 4、最大の終値 103。104 か 105 が見えれば未来が漏れている。",
    measures="T0 + 4 日の呼び出しの中で、戦略が対象の公開の手段で読んだ過去の件数と最大の終値。戦略が自分で貯めた列は対象の読み出しではないので数えない。"
             "過去を読む公開の手段が無い対象は「対応なし」(何を呼んで何が起きたかを書く)。読み出しが複数あるときは、読んだ件数が全部同じでなければ一致しない。")
_E1 = trade(T0 + 1 * DAY, 101.0, recv=T0 + 3 * DAY)
add(id="p4-received-time", viewpoint="P0-4", kind="value",
    title="取引所の時刻は早いが受け取りが遅い事象を、受け取る前に見せないか",
    input={"any_type": True, "events": [_E1, trade(T0 + 2 * DAY, 100.0), trade(T0 + 4 * DAY, 102.0)],
           "note": "価格 101 の約定は 取引所の時刻 T0+1 日・受け取れる時刻 T0+3 日。ほかの 2 件は両者が同じ。"
                   "入力は取引所の時刻の順に並べてある"},
    expected={"price101_visible_at_day2": False, "price101_delivered_at_ns": T0 + 3 * DAY,
              "price101_visible_at_day4": True},
    derivation="「受け取れた時刻 ≤ 今」の事象しか見せないなら、2 日後の呼び出しでは 101 は見えない(3 日 > 2 日)。"
               "101 が戦略に届くのは 3 日後、4 日後の呼び出しでは見える。取引所の時刻で届けると 1 日後に見えてしまう。",
    measures="2 日後と 4 日後の呼び出しで 101 の約定が見えたか、101 が届いた時刻。")
add(id="p4-future-read-attempt", viewpoint="P0-4", kind="capability",
    title="T0 + 4 日の呼び出しで、戦略が 5 本目の足を名指して読もうとすると、実行時エラーか型エラーで止まるか",
    input={"events": _LA_BARS, "probe_at_ns": T0 + 4 * DAY, "future_ts_ns": T0 + 5 * DAY, "future_value": 104.0,
           "strategy": "T0 + 4 日の呼び出しの中で、5 本目(時刻 T0 + 5 日、終値 104)を名指して読もうとする。"
                       "名指し方は 2 つ: 時刻で(5 本目の時刻を渡す・5 本目を含む範囲を渡す)と、位置で(今の最新の次の位置を、添字・区間・次を覗く手段で読む)。"
                       "対象が戦略に渡す公開の読み出しの手段ごとに、その手段の形に当たる名指し方を、下の `namings` の一覧の全部で試し、1 つずつ記録する"
                       "(手段・形・名指し方・出た例外の名前、または返った値)。一覧のどれを試すかを adapter は選ばない。"
                       "名指さない読み出し(全部・最新の 1 件・中身の配列)は形 other として記録してよく、止まったかには数えないが、104 が返ったかには数える。"
                       "時刻も位置も取る手段が 1 つも無い対象では、戦略のコードが 5 本目を読もうとして書く呼び出し"
                       "(履歴の添字・時刻を渡す問い合わせ)を実際に書いて呼び(形 no_means)、出た例外を記録する",
           "namings": {"position": {"what": "添字と区間を受ける読み出し。n = 最新の次の位置(対象の数え方で)", "namings": list(POSITION_NAMINGS)},
                       "time_at": {"what": "時刻を 1 つ受ける読み出し", "namings": list(TIME_NAMINGS["time_at"])},
                       "time_until": {"what": "終わりの時刻だけを受ける読み出し", "namings": list(TIME_NAMINGS["time_until"])},
                       "time_since": {"what": "始まりの時刻だけを受ける読み出し", "namings": list(TIME_NAMINGS["time_since"])},
                       "time_range": {"what": "始まりと終わりの時刻を受ける読み出し", "namings": list(TIME_NAMINGS["time_range"])},
                       "next_call": {"what": "次の 1 件を返す呼び出し(覗く・次へ)", "namings": ["next"]},
                       "times": "fut = 5 本目の時刻(T0 + 5 日)、now = 呼び出しの時刻(T0 + 4 日)、first = 1 本目の時刻(T0 + 1 日)、1d = 1 日"},
           "note": "足を受けない対象は、同じ時刻・価格=終値の約定で代えてよい"},
    expected={"every_attempt_stopped_by_error": True, "future_value_obtained": False},
    derivation="固定した要件(REQUIREMENTS.md §2 P0-4)の測り方は「戦略側から未来時刻の事象を読もうとするコードが、実行時エラーか型エラーで止まるか"
               "(素通りしたら不合格)」。T0 + 4 日の時点で 5 本目(T0 + 5 日)はまだ届いていないので、5 本目を名指した読み出しは"
               "どれも例外で止まらなければならない。空の結果・切り詰めた結果(4 本目までを黙って返す)・値を返すのは素通りで、"
               "正解ではない。104 が 1 つでも返れば未来が漏れている。",
    measures="試した読み出しのすべてが例外で止まったか、どれかで 104 が得られたか。",
    graded_from="出力の `attempts`(試しの列。各試しは `means` 手段・`form` 名指し方の大分類(time / position / other)・`shape` 手段の形・`naming` 名指し方・"
                "`raised` 例外の名前か null・`returned` 返った値か null)から runner が作る: `every_attempt_stopped_by_error` = 名指し方が time か position の試しが 1 つ以上あり、"
                "その全部の `raised` が null でない / `future_value_obtained` = どれかの試し(other を含む)の `returned` の中に 104(入力の `future_value`)がある。"
                "採点の前に runner は、手段ごとに `namings` のその形の一覧が全部そろっているか、形 no_means の試しが全部例外で止まったかを検め、"
                "そろっていなければ採点しない(結果なし)。")

# ---------------------------------------------------------------- P0-5
_TIE_STREAMS = {
    "trades": [trade(T0 + DAY, 100.0)],
    "bars": [bar(T0 + DAY, 100.0)],
    "funding": [{"kind": "funding", "ts_ns": T0 + DAY, "rate": 0.0001}],
    "liquidation": [{"kind": "liquidation", "ts_ns": T0 + DAY, "price": 99.0, "qty": 0.2, "side": "sell"}],
}
_TIE_ALL = sorted([[e["kind"], e["ts_ns"]] for evs in _TIE_STREAMS.values() for e in evs])
_STATED_RULE_TEXT = ("対象ごとの規則(対象の文書か公開のコードから、書いてある所と逐語を写したもの)と、それをこの入力に当てた並びは、"
                     "場面係が走らせる前に場面集の側に固定してある(対象の名前を伏せるため、この定義には載せない)。"
                     "adapter は戦略に届いた(型, 時刻)の列だけを返し、規則もそれを当てた列も返さない。"
                     "規則を明記していない対象には規則が無く、規則どおりにはならない")
add(id="p5-same-time-twice", viewpoint="P0-5", kind="value",
    title="同時刻の 4 種の事象を、対象が明記した並びの規則どおりの順で、1 件も落とさずに処理するか",
    input={"streams": _TIE_STREAMS, "hand_over_order": ["trades", "bars", "funding", "liquidation"],
           "note": "型ごとの 4 つの入力。1 本しか受けない対象には、この順に連結して渡す(並べ替えない)",
           "stated_rule": _STATED_RULE_TEXT},
    expected={"delivered_as_multiset": _TIE_ALL, "follows_stated_rule": True},
    derivation="固定した要件(REQUIREMENTS.md §2 P0-5)の測り方は「同時刻に複数型の事象を仕込んだ入力を作り、規則どおりの順で処理されるか(値)、"
               "2 回実行して一致するか(再現)」。4 件は同じ時刻なので時刻では並びが決まらず、決めるのは対象が明記した規則だけである。"
               "よって正解は (1) 4 件がちょうど 1 回ずつ届く(型と時刻の組を並べ替えた列が入力の 4 件と同じ)、"
               "(2) 届いた順が、対象の規則をこの入力に当てた順と同じ、の 2 つ。2 回の一致は表の「再現」の欄で見る。"
               "規則を明記していない対象は (2) を満たさない。",
    measures="戦略に届いた(型, 時刻)の列が、4 件を落とさず重ねず、対象の明記した規則の順と一致するか。",
    graded_from="出力の `order`(戦略に届いた(型, 時刻)の列)と、場面係が固定した対象の規則から runner が作る: `delivered_as_multiset` = `order` を並べ替えた列 / "
                "`follows_stated_rule` = 対象に規則があり、`order` が、その規則を runner がこの入力(渡す順 trades, bars, funding, liquidation)に当てた並びと同じ。")
add(id="p5-hand-over-order", viewpoint="P0-5", kind="capability",
    title="同時刻の 4 種の事象の並びが、データの中身と無関係な「入力を渡す順」に左右されず、各回が明記した規則どおりか",
    input={"streams": _TIE_STREAMS,
           "hand_over_orders": [list(p) for p in permutations(["trades", "bars", "funding", "liquidation"])],
           "note": "4 つの入力を 24 通りの順で渡して 24 回処理する。複数の入力を受ける対象は 4 つを別々の入力として、"
                   "その回の順で渡す(form = multi_input)。1 本しか受けない対象には、その回の順で連結した 1 本を渡す(form = single_input)",
           "stated_rule": _STATED_RULE_TEXT + "。各回の正解の並びは、runner がその規則を場面のその回の渡す順に当てて作る"},
    expected={"every_run_delivers_each_once": True, "every_run_follows_stated_rule": True,
              "same_order_whatever_the_hand_over": True},
    derivation="別々の入力(ファイルごとの約定・足・資金調達・清算)を渡す順は、データをどれから先に読んだかで変わる、データの中身と無関係な順である。"
               "複数の入力を受ける対象では、同時刻の並びが規則(型・時刻など中身)で決まるなら 24 回とも同じ並びになる。"
               "1 本しか受けない対象では、連結した 1 本がその回の入力そのもので、その入力の順は同時刻でも守るのが規則"
               "(p5-same-stream-order と同じ理由)なので、各回が規則どおりなら並びは回ごとに違ってよい。"
               "どちらの形でも、各回 4 件がちょうど 1 回ずつ届き、各回の順がその回の入力に規則を当てた順と同じでなければならない。",
    measures="24 回の各回で 4 件が落ちずに届いたか、各回の順が規則どおりか、複数の入力を受ける対象では 24 回の並びが 1 通りか。",
    graded_from="出力の `form`(multi_input / single_input)・`runs`(各回の `hand_over`・`order`)と、場面係が固定した対象の規則から runner が作る。"
                "各回の `hand_over` は場面の 24 通りの順と同じ並びでなければならない(違えば 3 つとも偽): "
                "`every_run_delivers_each_once` = 24 回すべてで `order` を並べ替えた列が入力の 4 件と同じ / "
                "`every_run_follows_stated_rule` = 対象に規則があり、`form` が規則の書かれた形と同じで、24 回すべてで `order` が、その規則を runner がその回の渡す順に当てた並びと同じ / "
                "`same_order_whatever_the_hand_over` = form が multi_input なら 24 回の `order` が 1 通り、single_input なら真(渡す順がその回の入力そのものなので)。")
add(id="p5-same-stream-order", viewpoint="P0-5", kind="value",
    title="1 本の入力の中の同時刻の 3 件を、入力の順のまま処理するか",
    input={"events": [trade(T0 + DAY, 101.0), trade(T0 + DAY, 99.0), trade(T0 + DAY, 100.0)],
           "note": "型は対象が受ける型でよい(足なら終値 101・99・100)"},
    expected={"prices": [101.0, 99.0, 100.0]},
    derivation="同じ取引所から来た 1 本の記録の中では、並びが取引所での起きた順である。同時刻でも入れ替えてはならないので、"
               "処理の順は 101、99、100。価格の昇順(99, 100, 101)でも降順(101, 100, 99)でもない順にしてあるので、"
               "価格で並べ替える対象や 1 件を落とす対象はこの正解を出せない。",
    measures="戦略が受け取った 3 件の価格の順。")

# ---------------------------------------------------------------- P0-6
_API_TRADES = [trade(T0 + i * DAY, 100.0, qty=100.0) for i in (1, 2, 3)]
add(id="p6-place-then-cancel", viewpoint="P0-6", kind="value",
    title="発注して取り消すと、未決の注文が 1 → 0 になるか",
    input={"any_type": True, "events": _API_TRADES,
           "strategy": "1 回目: 指値 買い 数量 1 価格 90.0 を出す。2 回目: 未決の注文の数を記録し、その注文を取り消す。"
                       "3 回目: 未決の注文の数を記録する"},
    expected={"open_at_call2": 1, "open_at_call3": 0},
    derivation="90 の買い指値は 100 の相場では埋まらないので 2 回目には未決が 1 件。2 回目に取り消せば、"
               "遅延の無い既定の下で 3 回目には 1 − 1 = 0 件。",
    measures="戦略が呼び出しの中で対象の公開の手段で読んだ未決の注文の数。")
add(id="p6-cancel-notice", viewpoint="P0-6", kind="capability",
    title="取消が成ったことが、事象として戦略に届くか",
    input={"any_type": True, "events": _API_TRADES,
           "strategy": "p6-place-then-cancel と同じ。戦略が呼び出しの中で受け取った通知を記録する"},
    expected={"cancel_notice_received": True},
    derivation="取消を出し、それが成れば、その知らせは戦略に届く事象として 1 件ある。届かなければ False。",
    measures="取消の成立を知らせる通知を戦略が受け取ったか(受け取ったの意味は p3-notice-accepted と同じ)。")
add(id="p6-fill-seen-by-strategy", viewpoint="P0-6", kind="capability",
    title="戦略が出した成行が埋まったことを、戦略が次の呼び出しで読めるか",
    input={"any_type": True, "events": _API_TRADES, "account": "現金 1,000,000 円",
           "strategy": "1 回目: 成行 買い 数量 1。3 回目: その注文の約定済みの数量を対象の公開の手段で読む"},
    expected={"filled_qty_at_call3": 1.0},
    derivation="成行の買い 1 は 2 日後の約定(100)で全量が埋まる。3 回目にはその注文の約定済み数量は 1.0。",
    measures="3 回目の呼び出しの中で戦略が読んだ約定済み数量。")

# ---------------------------------------------------------------- P0-7
_PLUG_TRADES = [trade(T0 + i * DAY, 100.0, qty=100.0) for i in (1, 2, 3)]
add(id="p7-fill-model-swap", viewpoint="P0-7", kind="capability",
    title="約定の模型を差し替えると、その模型の値で埋まるか",
    input={"any_type": True, "events": _PLUG_TRADES, "account": "現金 100,000 円",
           "plug": "約定の模型: 届いた注文を、その場で全量、価格 12345.0 で埋める",
           "strategy": "1 回目: 成行 買い 数量 1"},
    expected={"fill_price": 12345.0},
    derivation="差し替えた模型は相場によらず 12345.0 で埋める。差し替えが効けば約定の価格は 12345.0。"
               "既定の模型なら 100.0 前後になるので区別できる。",
    measures="その約定の価格(戦略が受け取った値か、実行の結果の約定の記録)。対象の公開の差し込み口だけを使い、対象のコードを書き換えない。")
_LAT_TRADES = [trade(T0 + i * MS, 100.0, qty=100.0) for i in range(0, 11)]
add(id="p7-latency-model-swap", viewpoint="P0-7", kind="capability",
    title="発注の遅延の模型を差し替えると、注文がその遅れで取引所に着くか",
    input={"any_type": True, "events": _LAT_TRADES, "account": "現金 100,000 円",
           "plug": "遅延の模型: 発注の遅れ 7 ms(7,000,000 ns)。配信・取消・通知の遅れは 0",
           "strategy": "1 回目(T0): 成行 買い 数量 1"},
    expected={"fill_time_ns": T0 + 7 * MS},
    derivation="約定は 1 ms おきに T0〜T0+10 ms。T0 に出した注文は T0+7 ms に取引所に着く。成行はそこで最初の約定"
               "(T0+7 ms、価格 100)で埋まる。着いた時点で埋める模型でも T0+7 ms。",
    measures="その約定の時刻(int ナノ秒。戦略が受け取った値か、実行の結果の約定の記録)。")
add(id="p7-cost-model-swap", viewpoint="P0-7", kind="capability",
    title="費用の模型を差し替えると、その模型の費用が約定に付くか",
    input={"any_type": True, "events": _PLUG_TRADES, "account": "現金 100,000 円",
           "plug": "費用の模型: 約定 1 件につき 0.5 円(数量・価格によらない)",
           "strategy": "1 回目: 成行 買い 数量 1"},
    expected={"fee": 0.5},
    derivation="約定は 1 件、1 件あたり 0.5 円なので費用は 0.5。",
    measures="その約定に付いた費用(戦略が受け取ったか、実行の結果の約定の記録から読んだ値)。")
add(id="p7-cost-per-unit", viewpoint="P0-7", kind="value",
    title="数量に比例する費用の模型に差し替えると、その模型が数量から出した費用が約定に付くか",
    input={"any_type": True, "events": _PLUG_TRADES, "account": "現金 100,000 円",
           "plug": "費用の模型: 約定の数量 1 単位あたり 0.375 円(価格によらない)", "strategy": "1 回目: 成行 買い 数量 2"},
    expected={"fee": 0.75},
    derivation="数量 2 の成行は、100 単位の約定(100.0)で 1 回に全量が埋まる。費用は 2 × 0.375 = 0.75(0.375 = 3/8 は 2 進の小数で丸めなく表せる)。"
               "差し込みが効かない対象は、その対象の既定の費用(0 か、その対象の手数料)になり 0.75 にならない。"
               "模型が数量を受け取らなければ 0.75 は出ない。",
    measures="その注文の約定に付いた費用の合計(戦略が受け取ったか、実行の結果の約定の記録から読んだ値)。")
add(id="p7-account-swap", viewpoint="P0-7", kind="capability",
    title="口座を差し替えると、差し替えた口座が約定を受け取るか",
    input={"any_type": True, "events": _PLUG_TRADES, "account": "現金 100,000 円",
           "plug": "口座: 渡された約定の数量を記録するだけの口座(対象の口座の差し込み口の形で書く)",
           "strategy": "1 回目: 成行 買い 数量 1"},
    expected={"account_recorded_fill_qty": [1.0]},
    derivation="約定は 1 件で数量 1。差し替えた口座に対象が約定を渡すなら、記録は [1.0]。",
    measures="差し替えた口座が記録した約定の数量の列。")

assert len(SCENES) == len({s.id for s in SCENES}), "duplicate scene id"
for _vp in VIEWPOINTS:
    assert any(s.viewpoint == _vp and s.kind == "value" for s in SCENES), f"{_vp} has no value scene"
