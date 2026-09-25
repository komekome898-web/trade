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
    (`SceneResult.provenance`) before it grades;
  * round r7-1 (critic i0-r6-02), narrowed in round r8-1 (L-438 (2)): the
    four scenes named in `L438_2_SCENES` (and only they carry a `type_plan`)
    take their event types from the configured target's own types in the
    fixed order `TYPE_ORDER`; run_battery.py builds the input and the
    expected result with `for_target_types` from the types whose p3-<type>
    scene of the same run of the same configured target was graded
    "正解と一致" (round r8-1, positive definition A). The scene as listed
    here is the one for a target that has all six types.
  * round r8-1 (positive definition A): a result counts only under the
    settings the user made through the target's public means within that
    run (recorded by `adapters/common.py: configure*` and checked by the
    runner), with the configured target's chosen values the same in every
    scene; `COVERS` below names the cells of each viewpoint's range a scene
    declares (positive definition C, grid_c.py);
  * round r13-1 (critic i0-r11-02; ROOTCAUSE_r13-1.md section 3): a declared
    cell counts ("場面にした") only when its event type comes out of the
    scene's input by machine -- the type field of the input's events for the
    market types, the input's `requests` field for the clock and the notices
    (`input_types`, `covers_of`). A scene whose strategy asks the target for
    something holds the kinds in `requests` ("timer" / "place" / "cancel"),
    the same requests its `strategy` text says.
  * round r16-1 (critic i0-r15-05): a viewpoint's title is the fixed requirements' text (VIEWPOINTS); P0-2 holds a
    value scene per time unit (秒 / ミリ / マイクロ秒) and form (decimal text, int, float) whose input is
    {"time", "unit"}; `extra_values_of` gives the extra-axis values (P0-2's units, P0-7's plug points) an input
    holds, and grid_c.named_coverage shows which scenes give each value the viewpoint's text names.
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

# Round r16-1 (critic i0-r15-05; ROOTCAUSE_r16-1.md section 2, root 2): a viewpoint's title is the fixed
# requirements' section 2 row, column 2, character for character (a summary written here by hand dropped part of it).
import grid_c as _grid_c  # noqa: E402  (stdlib only; reads the fixed requirements' file)

VIEWPOINTS = {vp: _grid_c.table_cell(_grid_c.MEASURE_LINE[vp], 2) for vp in _grid_c.VIEWPOINTS}
assert all(_grid_c.table_cell(_grid_c.MEASURE_LINE[vp], 1) == vp for vp in VIEWPOINTS), "REQUIREMENTS.md rows moved"


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
    type_plan: dict | None = None  # when set: the event types come from the target's own types
                                   # (round r7-1): {"slots", "min_types", "cycle"}; see for_target_types
    declares: tuple = ()    # round r8-1 (positive definition C), r13-1: the cells of the viewpoint's range the scene
                            # declares, (event, see-path, extra) in the words of grid_c.py; see COVERS below

    @property
    def covers(self) -> tuple:
        """The declared cells that count: those whose event type comes out of the input (round r13-1, covers_of)."""
        return covers_of(self)


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

# ---------------------------------------------------------------- types taken from the target (round r7-1)
# The order of the market event types in the fixed requirements, §1 of
# REQUIREMENTS.md ("約定・板の写真・板の差分・足・資金調達・清算"). One order for
# every target: a scene with a `type_plan` uses the target's own types in
# this order, so no adapter chooses them.
TYPE_ORDER = ["trade", "book_snapshot", "book_delta", "bar", "funding", "liquidation"]
SLOTS = ["A", "B", "C", "D"]
# Round r8-1 (L-438 (2), LEAD_DESIGN.md section 7.2 item 10): the scenes whose input's type combination is
# decided from the configured target's own types, named by id. Only these four; a test checks that the scenes
# with a `type_plan` are exactly these.
L438_2_SCENES = ("p1-merge-by-time", "p1-typed-events", "p5-same-time-twice", "p5-hand-over-order")
TYPE_RULE = ("この場面は型そのものを測らない(型を持つかは P0-3 が型ごとに測る)。入力の事象の型の組は、設定つき対象の持つ型を、"
             "固定した要件 §1 の型の順(約定・板の写真・板の差分・足・資金調達・清算)に並べたものから runner が決める。"
             "設定つき対象の持つ型 = 同じ設定つき対象の同じ実行の p3-<型> の場面のうち、出所の検め(共通の決まりの設定の操作と"
             "出所の検め)を通って採点された正しさが「正解と一致」の場面の事象の型。値が不一致の型(その型の p3 の場面が"
             "「正解と一致」でない型。届いたが値が違う型、対応なし・結果なしの型を含む)は持つと数えない。違う設定つき対象の"
             "実行の結果を合わせない。adapter は型を選ばない。設定つき対象の持つ型の数が最低に足りない設定つき対象は、runner がこの場面を"
             "「対応なし」にし、理由に p3 の採点を書く。下の入力と期待は 6 種を全部持つ設定つき対象のもの(型の順の最初から)。"
             "各事象の型の欄以外の中身は、その型の p3-<型> の場面の事象と同じ(時刻だけが違う)")


def own_types(target_types) -> list[str]:
    """The target's types in TYPE_ORDER (unknown names dropped)."""
    have = set(target_types or [])
    return [k for k in TYPE_ORDER if k in have]


def plan_types(plan: dict, target_types) -> list[str] | None:
    """The slot types of a `type_plan` for a target with these types, or None
    when the target has fewer than `min_types` of them."""
    own = own_types(target_types)
    if len(own) < plan["min_types"]:
        return None
    if plan["cycle"]:
        return [own[i % len(own)] for i in range(plan["slots"])]
    return own[:plan["slots"]]


def typed_event(kind: str, ts: int) -> dict:
    """An event of this type at this time; its other fields are the P0-3 sample's."""
    return dict(SAMPLES[kind], ts_ns=ts)

SCENES: list[Scene] = []


def add(**kw: Any) -> None:
    SCENES.append(Scene(**kw))


# ---------------------------------------------------------------- P0-1
BUILDERS: dict[str, Any] = {}  # scene id -> slot types -> {"input", "expected"} (round r7-1)


def _merge_by_time(types: list[str]) -> dict:
    # A = days 2 and 5, B = days 1 and 4, C = day 3; handed over A, B, C
    days = {"A": (2, 5), "B": (1, 4), "C": (3,)}
    streams = {slot: [typed_event(t, T0 + d * DAY) for d in days[slot]] for slot, t in zip(SLOTS, types)}
    seq = sorted(([e["kind"], e["ts_ns"]] for evs in streams.values() for e in evs), key=lambda p: p[1])
    return {"input": {"streams": streams, "hand_over_order": list(streams),
                      "types": dict(zip(streams, types)),
                      "note": "3 つの入力 A・B・C をこの順で渡す。同じ銘柄の事象を別々の入力として受ける対象には別々に、"
                              "1 本の入力しか受けない対象には、この順に連結して渡す(並べ替えない)",
                      "type_rule": TYPE_RULE + "。この場面: 入力 A・B・C に対象の型を型の順に割り当てる"
                                               "(2 種なら A・B・A)。最低 2 種"},
            "expected": {"sequence": seq}}


BUILDERS["p1-merge-by-time"] = _merge_by_time
_P1M = {"slots": 3, "min_types": 2, "cycle": True}
_m = _merge_by_time(plan_types(_P1M, TYPE_ORDER))
add(id="p1-merge-by-time", viewpoint="P0-1", kind="value",
    title="別々の入力に分かれた、型の違う事象を、渡した順ではなく時刻の順に処理するか",
    input=_m["input"], expected=_m["expected"], type_plan=_P1M,
    derivation="5 件の時刻は T0 から 1,2,3,4,5 日後で互いに異なる(A = 2・5 日後、B = 1・4 日後、C = 3 日後)。"
               "時刻の昇順に並べると B(1)・A(2)・C(3)・B(4)・A(5)。期待はこの順の(型, 時刻)の列で、型は各入力に割り当てた対象の型。"
               "渡した順(A,A,B,B,C)のまま処理すれば 2,5,1,4,3 日の順になり一致しない。"
               "最低 2 種の理由: 固定した要件 P0-1 は「同期のバー逐次ループではないこと」を問う。同じ型だけの入力を時刻で合わせることは"
               "複数の足の系列を日時で揃える逐次ループでもできるので、1 種では P0-1 の区別が測れない。",
    measures="戦略の呼び出しごとに記録した(事象の型, 時刻)の列が、時刻の昇順と一致するか。")

_SEQ_BARS = [bar(T0 + (i + 1) * DAY, 100.0 + i) for i in range(5)]
add(id="p1-one-call-per-event", viewpoint="P0-1", kind="value",
    title="事象 1 件ごとに戦略が 1 回呼ばれ、呼ばれたときの時刻がその事象の時刻か",
    input={"events": _SEQ_BARS,
           "note": "型は対象が受ける型(対象の配布物の型)を 1 つ選んでよい(型は測らない。足なら OHLC はすべて終値、"
                   "約定なら 価格 = 終値 数量 0.01)。5 件とも同じ型"},
    expected={"observed_ts_ns": [e["ts_ns"] for e in _SEQ_BARS]},
    derivation="入力は 1 日おきの 5 件(時刻の昇順)。事象ごとに 1 回呼ぶなら呼び出しは 5 回で、各回に受けた事象の時刻は入力と同じ。"
               "恒等写像なので計算は要らない。型は測らない(型を持つかは P0-3 が測る。第 r7-1 回)。",
    measures="呼び出しの回数と、各呼び出しで戦略が受け取った事象の時刻。",
    graded_from="出力の `sequence`(戦略の各呼び出しで受けた(型, 時刻)の列)から runner が作る: `observed_ts_ns` = `sequence` の時刻の列"
                "(件数 = 呼び出しの回数)。型の欄は採点に使わない(出所の検めには使う: 対象の型で、1 つの型に 2 つの型の名前を写していないこと)。")


def _typed_events(types: list[str]) -> dict:
    evs = [typed_event(t, T0 + (i + 1) * DAY) for i, t in enumerate(types)]
    return {"input": {"events": evs, "types": list(types),
                      "type_rule": TYPE_RULE + "。この場面: 対象の型の最初の 2 種を 1 日後・2 日後に 1 件ずつ。最低 2 種"},
            "expected": {"sequence": [[e["kind"], e["ts_ns"]] for e in evs]}}


BUILDERS["p1-typed-events"] = _typed_events
_P1T = {"slots": 2, "min_types": 2, "cycle": False}
_t = _typed_events(plan_types(_P1T, TYPE_ORDER))
add(id="p1-typed-events", viewpoint="P0-1", kind="capability",
    title="戦略が受け取った事象の型を見分けられるか",
    input=_t["input"], expected=_t["expected"], type_plan=_P1T,
    derivation="型の違う 2 件を時刻の昇順で 1 本の入力に入れる(型は対象の型の最初の 2 種)。型を持つ事象が 1 件ずつ届くなら、"
               "戦略は 2 回呼ばれ、1 回目に 1 種目、2 回目に 2 種目を受け取る。型を区別できなければ型の欄を埋められない。"
               "見分けるには型が 2 種要るので最低 2 種。",
    measures="戦略が呼ばれた時に受け取ったものから、2 つの型の別を戦略自身が判別できたか(判別した結果の列)。")

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

# Round r16-1 (critic i0-r15-05): the time units the viewpoint's text names besides ISO (秒・ミリ, and マイクロ秒 as
# another of 「他の単位」), each as a decimal text, an int and a float. The known time is ISO_NS (2024-01-01T00:00:00
# .123456789Z) written in the unit; the int and the float forms whose value cannot be ISO_NS carry a known time of their
# own, written in the derivation. The answer is the value the input holds (a text: its decimal; an int: itself; a
# float: the binary value it holds) times the unit's factor, when that is a whole number of ns; otherwise no int64 ns
# is right (NO_INT: any int returned is a different time = 不一致) and the answer is a refusal of the target's entry
# (round r17-1, critic i0-r16-04 and the lead's answer to i0-r15-05: expected[REFUSED] is True; run_battery.py grades
# a refusal it credits to the target's entry, from common.py's record of the exception, as 正解と一致).
REFUSED = "refused_by_entry"  # the expected key of a scene whose answer is a refusal (run_battery.expects_refusal)
REFUSAL_PHRASE = "正解は「対象の入口が断る」: 入口が断れば「正解と一致」"  # every refusal scene's text carries it (test)
UNIT_WORDS = {"s": "秒", "ms": "ミリ", "us": "マイクロ秒"}  # the input's unit code -> the requirements' word
UNIT_FACTOR = {"s": 10 ** 9, "ms": 10 ** 6, "us": 10 ** 3}
NO_INT = "無い(入力が持つ値にナノ秒より細かい端数がある。どの整数も入力と違う時刻)"
_UNIT_NOTE = ("time を、対象が単位 unit(s = 秒、ms = ミリ秒、us = マイクロ秒)の時刻として読む入口(対象のデータの入口の時刻の欄、"
              "または対象が公開する時刻の変換の関数)に、そのままの型(文字列 / 整数 / float)で渡し、対象が作った時刻を int ナノ秒で読む。"
              "adapter は数を換算しない(倍率を掛ける・型を変える・文字列にする・対象の入口を通らない変換をする、をしない)。その単位とその型を"
              "読む入口が無い対象は「対応なし」(試したことを書く)。入口が例外で断れば、その例外の物から common.py が断りの記録を作り"
              "(何を渡したか・例外の道筋の枠)、runner がその記録で対象の入口の断りかを確かめる。確かめた断りは、正解が「断る」の場面では"
              "「正解と一致」、正解が整数の場面では「対応なし」")
_UNIT_GRADED = ("adapter の出力の ns(対象が作った時刻を、対象の時刻の型から正確に int ナノ秒に読んだ値)を runner が採点する: int64 の範囲の"
                "整数(bool でない。numpy の整数を含む)ならその整数、ほかは null(run_battery.py の _grade_unit_time)。入口が断ったときは、"
                "runner が断りの記録(common.py が例外の物から作る)から対象の入口の断りかを決める(run_battery.py の refusal_problem。"
                "入口に渡した物が場面の入力と同じ型・同じ値、断った入口が対象の物、例外の道筋に対象の枠があり、その内側に場面集の側の"
                "ファイルの枠が無い)。文の読みは使わない")
_UNIT_MEASURES = "対象自身の変換が、この単位の時刻を丸めずに int64 ナノ秒にするか(ナノ秒の整数にならない値を黙って丸めないか)。"
_NO_INT_TAIL = ("正解の int64 ナノ秒は無い: どの整数を返しても入力と違う時刻なので「不一致」。" + REFUSAL_PHRASE +
                "(runner が断りの記録で対象の入口の断りと確かめた物)、入口が無ければ「対応なし」。")
_FORM_TITLE = {"text": "十進の文字列・ナノ秒で割り切れる", "text-subns": "十進の文字列・ナノ秒より細かい桁がある", "int": "整数",
               "float-held": "float・float が持つ値がナノ秒で割り切れる",
               "float-subns": "float・書いた数を float が持てず、持つ値にナノ秒より細かい端数がある"}
_UNIT_PLAN = [
    # (unit, form, time, expected int64 ns or NO_INT, derivation)
    ("s", "text", "1704067200.123456789", ISO_NS,
     "既知の時刻 2024-01-01T00:00:00.123456789Z(p2-iso-utc と同じ)を秒の十進で書いた。1,704,067,200 秒(p2-iso-utc の導き方)"
     " + 0.123456789 秒 = 1,704,067,200,123,456,789 ns。"),
    ("s", "text-subns", "1704067200.1234567891", NO_INT,
     "0.1234567891 秒 = 123,456,789.1 ns で、ナノ秒の整数にならない(10 桁目の 1 = 0.1 ns)。" + _NO_INT_TAIL),
    ("s", "int", 1704067200, 1_704_067_200_000_000_000,
     "既知の時刻 2024-01-01T00:00:00Z。1,704,067,200 秒(p2-iso-utc の導き方)× 10^9 = 1,704,067,200,000,000,000 ns。"),
    ("s", "float-held", 1704067200.001953125, 1_704_067_200_001_953_125,
     "既知の時刻 2024-01-01T00:00:00.001953125Z。2^30 ≤ 1704067200 < 2^31 なので float はこの範囲を 2^-22 秒刻みで持つ。"
     "0.001953125 = 1/512 = 8192 × 2^-22 は刻みの上にあるので、float が持つ値は正確に 1704067200.001953125 秒"
     "(最短の表記は 1704067200.0019531 で、表記の桁は持つ値より短い)。1/512 秒 = 1,953,125 ns。"
     "よって 1,704,067,200,001,953,125 ns。"),
    ("s", "float-subns", float("1704067200.123456789"), NO_INT,
     "既知の時刻 2024-01-01T00:00:00.123456789Z を秒の float で書いた数 1704067200.123456789 は float が持てない。"
     "2^-22 秒刻みで最も近いのは 1704067200 + 517815 × 2^-22 秒(0.123456789 × 2^22 = 517,815.30…)で、float が持つ値は正確に "
     "1704067200.1234567165374755859375 秒。ナノ秒にすると 517815 × 10^9 / 2^22 = 517815 × 1953125 / 8192 で、"
     "517815 は奇数なので 8192 で割り切れず、ナノ秒の整数にならない。" + _NO_INT_TAIL),
    ("ms", "text", "1704067200123.456789", ISO_NS,
     "既知の時刻 2024-01-01T00:00:00.123456789Z をミリ秒の十進で書いた。1,704,067,200,123 ミリ秒 + 0.456789 ミリ秒 = "
     "1,704,067,200,123,456,789 ns。"),
    ("ms", "text-subns", "1704067200123.4567891", NO_INT,
     "0.4567891 ミリ秒 = 456,789.1 ns で、ナノ秒の整数にならない。" + _NO_INT_TAIL),
    ("ms", "int", 1704067200123, 1_704_067_200_123_000_000,
     "既知の時刻 2024-01-01T00:00:00.123Z。1,704,067,200,123 ミリ秒 × 10^6 = 1,704,067,200,123,000,000 ns。"),
    ("ms", "float-held", 1704067200123.015625, 1_704_067_200_123_015_625,
     "既知の時刻 2024-01-01T00:00:00.123015625Z。2^40 ≤ 1704067200123 < 2^41 なので float はこの範囲を 2^-12 ミリ秒刻みで持つ。"
     "0.015625 = 1/64 = 64 × 2^-12 は刻みの上にあるので、float が持つ値は正確に 1704067200123.015625 ミリ秒"
     "(最短の表記は 1704067200123.0156)。1/64 ミリ秒 = 15,625 ns。よって 1,704,067,200,123,015,625 ns。"),
    ("ms", "float-subns", float("1704067200123.456789"), NO_INT,
     "既知の時刻 2024-01-01T00:00:00.123456789Z をミリ秒の float で書いた数 1704067200123.456789 は float が持てない。"
     "2^-12 ミリ秒刻みで最も近いのは 1704067200123 + 1871 × 2^-12 ミリ秒(0.456789 × 4096 = 1,871.007…)で、float が持つ値は正確に "
     "1704067200123.456787109375 ミリ秒。ナノ秒にすると 1871 × 10^6 / 2^12 = 1871 × 15625 / 64 で、1871 は奇数なので"
     "ナノ秒の整数にならない。" + _NO_INT_TAIL),
    ("us", "text", "1704067200123456.789", ISO_NS,
     "既知の時刻 2024-01-01T00:00:00.123456789Z をマイクロ秒の十進で書いた。1,704,067,200,123,456 マイクロ秒 + 0.789 マイクロ秒 = "
     "1,704,067,200,123,456,789 ns。"),
    ("us", "text-subns", "1704067200123456.7891", NO_INT,
     "0.7891 マイクロ秒 = 789.1 ns で、ナノ秒の整数にならない。" + _NO_INT_TAIL),
    ("us", "int", 1704067200123456, 1_704_067_200_123_456_000,
     "既知の時刻 2024-01-01T00:00:00.123456Z。1,704,067,200,123,456 マイクロ秒 × 10^3 = 1,704,067,200,123,456,000 ns。"),
    ("us", "float-held", 1704067200123456.75, 1_704_067_200_123_456_750,
     "既知の時刻 2024-01-01T00:00:00.12345675Z。2^50 ≤ 1704067200123456 < 2^51 なので float はこの範囲を 2^-2 マイクロ秒"
     "(= 250 ns)刻みで持つ。0.75 は刻みの上にあるので、float が持つ値は正確に 1704067200123456.75 マイクロ秒(最短の表記は "
     "1704067200123456.8)= 1,704,067,200,123,456,750 ns。この float は、既知の時刻 …123456789Z をマイクロ秒で書いた数 "
     "1704067200123456.789(float が持てない)に最も近い float でもあり、その数を float で入れた場合はこの場面と同じ入力になる。"
     "刻みの 250 ns がナノ秒の整数なので、この範囲の float はどれもナノ秒で割り切れる値を持ち、「持つ値にナノ秒より細かい端数がある」"
     "float はマイクロ秒では作れない。"),
]
for _u, _f, _t, _want, _d in _UNIT_PLAN:
    add(id=f"p2-{_u}-{_f}", viewpoint="P0-2", kind="value",
        title=f"{UNIT_WORDS[_u]}の時刻({_FORM_TITLE[_f]})を対象自身の変換で int64 ナノ秒にした値",
        input={"time": _t, "unit": _u, "note": _UNIT_NOTE},
        expected={"int64_ns": _want, **({REFUSED: True} if _want == NO_INT else {})}, derivation=_d,
        measures=_UNIT_MEASURES, graded_from=_UNIT_GRADED)
UNIT_SCENES = [f"p2-{_u}-{_f}" for _u, _f, *_ in _UNIT_PLAN]

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
                   "型は対象の配布物の型で運ぶ。adapter が作った型(対象の基の class の子・欄を足した基の class・型の印を付けた辞書や関数)で運んだものは、"
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
           "strategy": "1 回目の呼び出し(1 日後)で「4 日後(T0 + 4 DAY)に起こして」と頼む。型は対象が受ける型でよい", "timer_at_ns": T0 + 4 * DAY,
           "requests": ["timer"]},
    expected={"clock_calls_ns": [T0 + 4 * DAY]},
    derivation="頼んだ時刻は T0 + 4 日。データの事象は 1 日後と 6 日後にしか無いので、4 日後ちょうどに呼ばれるのは時計の事象だけ。",
    measures="データの事象が無い時刻に、時計の事象として戦略が呼ばれた時刻の列。")

_NOTICE_TRADES = [trade(T0 + i * DAY, 100.0, qty=100.0) for i in (1, 2, 3)]
add(id="p3-notice-accepted", viewpoint="P0-3", kind="capability",
    title="注文の受付の通知が、事象として戦略に届くか",
    input={"any_type": True, "events": _NOTICE_TRADES,
           "strategy": "1 回目の呼び出しで 指値 買い 数量 1 価格 90.0 を出す(市場は 100.0 なので埋まらない)", "requests": ["place"]},
    expected={"notices": ["accepted"]},
    derivation="価格 90 の買い指値は、約定が 100 のまま続くので埋まらない。取消もしない。よって戦略に届く通知は受付の 1 件だけ。",
    measures="戦略が受け取った、その注文についての通知の種類の列。受け取ったとは、戦略の呼び出しに事象として届いたか、発注の呼び出しの戻り値・例外としてその場で返ったこと。後から戦略が問い合わせて得たものは数えない。")
add(id="p3-notice-rejected", viewpoint="P0-3", kind="capability",
    title="注文の拒否の通知が、事象として戦略に届くか",
    input={"any_type": True, "events": [trade(T0 + i * DAY, 1_000_000.0, qty=100.0) for i in (1, 2, 3)],
           "account": "現金 1,000 円、レバレッジ無し(現物の口座)",
           "strategy": "1 回目の呼び出しで 成行 買い 数量 1 を出す", "requests": ["place"]},
    expected={"notices": ["rejected"]},
    derivation="必要な資金は 1 × 1,000,000 = 1,000,000 円で、現金 1,000 円を超える。レバレッジ無しなので受けられず、"
               "届く通知は拒否の 1 件だけ。",
    measures="戦略が受け取った通知の種類の列(受け取ったの意味は p3-notice-accepted と同じ)。")
add(id="p3-notice-filled", viewpoint="P0-3", kind="capability",
    title="注文の約定の通知が、事象として戦略に届くか",
    input={"any_type": True, "events": _NOTICE_TRADES, "account": "現金 1,000,000 円",
           "strategy": "1 回目の呼び出しで 成行 買い 数量 1 を出す", "requests": ["place"]},
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
                "採点の前に runner は、手段ごとに `namings` のその形の一覧が全部そろっているかを検め、そろっていなければ採点しない(結果なし)。"
                "形 no_means の試しは名指す読み出しとして数える(値が返れば止まらなかった)。")

# ---------------------------------------------------------------- P0-5
_STATED_RULE_TEXT = ("対象ごとの規則(対象の文書か公開のコードから、書いてある所と逐語を写したもの)と、それをこの入力に当てた並びは、"
                     "場面係が走らせる前に場面集の側に固定してある(対象の名前を伏せるため、この定義には載せない)。"
                     "adapter は戦略に届いた(型, 時刻)の列だけを返し、規則もそれを当てた列も返さない。"
                     "規則を明記していない対象には規則が無く、規則どおりにはならない")
_P5 = {"slots": 4, "min_types": 2, "cycle": False}
_P5_RULE = (TYPE_RULE + "。この場面: 対象の型の最初の 4 種まで(対象が 2 種か 3 種しか持たなければその全部)を、"
            "1 つの入力に 1 種 1 件ずつ、同じ時刻 T0 + 1 日に置く。最低 2 種(固定した要件 P0-5 の「複数型」)")


def _tie_streams(types: list[str]) -> dict:
    return {slot: [typed_event(t, T0 + DAY)] for slot, t in zip(SLOTS, types)}


def _same_time_twice(types: list[str]) -> dict:
    streams = _tie_streams(types)
    return {"input": {"streams": streams, "hand_over_order": list(streams), "types": dict(zip(streams, types)),
                      "note": "型ごとの入力(A から順に)。同じ銘柄の事象を別々の入力として受ける対象には別々に、"
                              "1 本しか受けない対象には、この順に連結して渡す(並べ替えない)",
                      "type_rule": _P5_RULE, "stated_rule": _STATED_RULE_TEXT},
            "expected": {"delivered_as_multiset": sorted([e["kind"], e["ts_ns"]] for evs in streams.values() for e in evs),
                         "follows_stated_rule": True}}


def _hand_over_order(types: list[str]) -> dict:
    streams = _tie_streams(types)
    n = len(streams)
    return {"input": {"streams": streams, "hand_over_orders": [list(p) for p in permutations(list(streams))],
                      "types": dict(zip(streams, types)),
                      "note": f"{n} つの入力を全ての順({n}! 通り)で渡して、その回数だけ処理する。同じ銘柄の事象を別々の入力として受ける対象には"
                              "別々の入力として、その回の順で渡す(form = multi_input)。1 本しか受けない対象には、その回の順で連結した 1 本を渡す"
                              "(form = single_input)",
                      "type_rule": _P5_RULE,
                      "stated_rule": _STATED_RULE_TEXT + "。各回の正解の並びは、runner がその規則を場面のその回の渡す順に当てて作る"},
            "expected": {"every_run_delivers_each_once": True, "every_run_follows_stated_rule": True,
                         "same_order_whatever_the_hand_over": True}}


BUILDERS["p5-same-time-twice"] = _same_time_twice
BUILDERS["p5-hand-over-order"] = _hand_over_order
_s2 = _same_time_twice(plan_types(_P5, TYPE_ORDER))
add(id="p5-same-time-twice", viewpoint="P0-5", kind="value",
    title="同時刻の型の違う事象を、対象が明記した並びの規則どおりの順で、1 件も落とさずに処理するか",
    input=_s2["input"], expected=_s2["expected"], type_plan=_P5,
    derivation="固定した要件(REQUIREMENTS.md §2 P0-5)の測り方は「同時刻に複数型の事象を仕込んだ入力を作り、規則どおりの順で処理されるか(値)、"
               "2 回実行して一致するか(再現)」。入力の事象はどれも同じ時刻なので時刻では並びが決まらず、決めるのは対象が明記した規則だけである。"
               "よって正解は (1) 入力の事象がちょうど 1 回ずつ届く(型と時刻の組を並べ替えた列が入力のものと同じ)、"
               "(2) 届いた順が、対象の規則をこの入力に当てた順と同じ、の 2 つ。2 回の一致は表の「再現」の欄で見る。"
               "規則を明記していない対象は (2) を満たさない。型は対象の型から決める(第 r7-1 回。どの型を持つかで結果が決まらないように)。",
    measures="戦略に届いた(型, 時刻)の列が、入力の事象を落とさず重ねず、対象の明記した規則の順と一致するか。",
    graded_from="出力の `order`(戦略に届いた(型, 時刻)の列)と、場面係が固定した対象の規則から runner が作る: `delivered_as_multiset` = `order` を並べ替えた列 / "
                "`follows_stated_rule` = 対象に規則があり、`order` が、その規則を runner がこの入力(渡す順 A, B, …)に当てた並びと同じ。")
_h = _hand_over_order(plan_types(_P5, TYPE_ORDER))
add(id="p5-hand-over-order", viewpoint="P0-5", kind="capability",
    title="同時刻の型の違う事象の並びが、データの中身と無関係な「入力を渡す順」に左右されず、各回が明記した規則どおりか",
    input=_h["input"], expected=_h["expected"], type_plan=_P5,
    derivation="別々の入力(型ごとの記録)を渡す順は、データをどれから先に読んだかで変わる、データの中身と無関係な順である。"
               "複数の入力を受ける対象では、同時刻の並びが規則(型・時刻など中身)で決まるなら全ての回で同じ並びになる。"
               "1 本しか受けない対象では、連結した 1 本がその回の入力そのもので、その入力の順は同時刻でも守るのが規則"
               "(p5-same-stream-order と同じ理由)なので、各回が規則どおりなら並びは回ごとに違ってよい。"
               "どちらの形でも、各回 入力の事象がちょうど 1 回ずつ届き、各回の順がその回の入力に規則を当てた順と同じでなければならない。"
               "型は対象の型から決める(第 r7-1 回)。4 種を持つ対象は 24 通り、3 種は 6 通り、2 種は 2 通り。",
    measures="全ての回で入力の事象が落ちずに届いたか、各回の順が規則どおりか、複数の入力を受ける対象では全ての回の並びが 1 通りか。",
    graded_from="出力の `form`(multi_input / single_input)・`runs`(各回の `hand_over`・`order`)と、場面係が固定した対象の規則から runner が作る。"
                "各回の `hand_over` は場面の渡す順の一覧と同じ並びでなければならない(違えば 3 つとも偽): "
                "`every_run_delivers_each_once` = 全ての回で `order` を並べ替えた列が入力の事象と同じ / "
                "`every_run_follows_stated_rule` = 対象に規則があり、`form` が規則の書かれた形と同じで、全ての回で `order` が、その規則を runner がその回の渡す順に当てた並びと同じ / "
                "`same_order_whatever_the_hand_over` = form が multi_input なら全ての回の `order` が 1 通り、single_input なら真(渡す順がその回の入力そのものなので)。")
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
                       "3 回目: 未決の注文の数を記録する", "requests": ["place", "cancel"]},
    expected={"open_at_call2": 1, "open_at_call3": 0},
    derivation="90 の買い指値は 100 の相場では埋まらないので 2 回目には未決が 1 件。2 回目に取り消せば、"
               "遅延の無い既定の下で 3 回目には 1 − 1 = 0 件。",
    measures="戦略が呼び出しの中で対象の公開の手段で読んだ未決の注文の数。")
add(id="p6-cancel-notice", viewpoint="P0-6", kind="capability",
    title="取消が成ったことが、事象として戦略に届くか",
    input={"any_type": True, "events": _API_TRADES,
           "strategy": "p6-place-then-cancel と同じ。戦略が呼び出しの中で受け取った通知を記録する", "requests": ["place", "cancel"]},
    expected={"cancel_notice_received": True},
    derivation="取消を出し、それが成れば、その知らせは戦略に届く事象として 1 件ある。届かなければ False。",
    measures="取消の成立を知らせる通知を戦略が受け取ったか(受け取ったの意味は p3-notice-accepted と同じ)。")
add(id="p6-fill-seen-by-strategy", viewpoint="P0-6", kind="capability",
    title="戦略が出した成行が埋まったことを、戦略が次の呼び出しで読めるか",
    input={"any_type": True, "events": _API_TRADES, "account": "現金 1,000,000 円",
           "strategy": "1 回目: 成行 買い 数量 1。3 回目: その注文の約定済みの数量を対象の公開の手段で読む", "requests": ["place"]},
    expected={"filled_qty_at_call3": 1.0},
    derivation="成行の買い 1 は 2 日後の約定(100)で全量が埋まる。3 回目にはその注文の約定済み数量は 1.0。",
    measures="3 回目の呼び出しの中で戦略が読んだ約定済み数量。")

# ---------------------------------------------------------------- P0-7
_PLUG_TRADES = [trade(T0 + i * DAY, 100.0, qty=100.0) for i in (1, 2, 3)]
add(id="p7-fill-model-swap", viewpoint="P0-7", kind="capability",
    title="約定の模型を差し替えると、その模型の値で埋まるか",
    input={"any_type": True, "events": _PLUG_TRADES, "account": "現金 100,000 円",
           "plug": "約定模型: 届いた注文を、その場で全量、価格 12345.0 で埋める",
           "strategy": "1 回目: 成行 買い 数量 1", "requests": ["place"]},
    expected={"fill_price": 12345.0},
    derivation="差し替えた模型は相場によらず 12345.0 で埋める。差し替えが効けば約定の価格は 12345.0。"
               "既定の模型なら 100.0 前後になるので区別できる。",
    measures="その約定の価格(戦略が受け取った値か、実行の結果の約定の記録)。対象の公開の差し込み口だけを使い、対象のコードを書き換えない。")
_LAT_TRADES = [trade(T0 + i * MS, 100.0, qty=100.0) for i in range(0, 11)]
add(id="p7-latency-model-swap", viewpoint="P0-7", kind="capability",
    title="発注の遅延の模型を差し替えると、注文がその遅れで取引所に着くか",
    input={"any_type": True, "events": _LAT_TRADES, "account": "現金 100,000 円",
           "plug": "遅延模型: 発注の遅れ 7 ms(7,000,000 ns)。配信・取消・通知の遅れは 0",
           "strategy": "1 回目(T0): 成行 買い 数量 1", "requests": ["place"]},
    expected={"fill_time_ns": T0 + 7 * MS},
    derivation="約定は 1 ms おきに T0〜T0+10 ms。T0 に出した注文は T0+7 ms に取引所に着く。成行はそこで最初の約定"
               "(T0+7 ms、価格 100)で埋まる。着いた時点で埋める模型でも T0+7 ms。",
    measures="その約定の時刻(int ナノ秒。戦略が受け取った値か、実行の結果の約定の記録)。")
add(id="p7-cost-model-swap", viewpoint="P0-7", kind="capability",
    title="費用の模型を差し替えると、その模型の費用が約定に付くか",
    input={"any_type": True, "events": _PLUG_TRADES, "account": "現金 100,000 円",
           "plug": "費用: 約定 1 件につき 0.5 円(数量・価格によらない)",
           "strategy": "1 回目: 成行 買い 数量 1", "requests": ["place"]},
    expected={"fee": 0.5},
    derivation="約定は 1 件、1 件あたり 0.5 円なので費用は 0.5。",
    measures="その約定に付いた費用(戦略が受け取ったか、実行の結果の約定の記録から読んだ値)。")
add(id="p7-cost-per-unit", viewpoint="P0-7", kind="value",
    title="数量に比例する費用の模型に差し替えると、その模型が数量から出した費用が約定に付くか",
    input={"any_type": True, "events": _PLUG_TRADES, "account": "現金 100,000 円",
           "plug": "費用: 約定の数量 1 単位あたり 0.375 円(価格によらない)", "strategy": "1 回目: 成行 買い 数量 2",
           "requests": ["place"]},
    expected={"fee": 0.75},
    derivation="数量 2 の成行は、100 単位の約定(100.0)で 1 回に全量が埋まる。費用は 2 × 0.375 = 0.75(0.375 = 3/8 は 2 進の小数で丸めなく表せる)。"
               "差し込みが効かない対象は、その対象の既定の費用(0 か、その対象の手数料)になり 0.75 にならない。"
               "模型が数量を受け取らなければ 0.75 は出ない。",
    measures="その注文の約定に付いた費用の合計(戦略が受け取ったか、実行の結果の約定の記録から読んだ値)。")
add(id="p7-account-swap", viewpoint="P0-7", kind="capability",
    title="口座を差し替えると、差し替えた口座が約定を受け取るか",
    input={"any_type": True, "events": _PLUG_TRADES, "account": "現金 100,000 円",
           "plug": "口座: 渡された約定の数量を記録するだけの口座(対象の口座の差し込み口の形で書く)",
           "strategy": "1 回目: 成行 買い 数量 1", "requests": ["place"]},
    expected={"account_recorded_fill_qty": [1.0]},
    derivation="約定は 1 件で数量 1。差し替えた口座に対象が約定を渡すなら、記録は [1.0]。",
    measures="差し替えた口座が記録した約定の数量の列。")

# ---------------------------------------------------------------- round r8-1 / r13-1: the cells each scene declares
# (positive definition C; round r13-1's definition, ROOTCAUSE_r13-1.md section 3). Axis values as grid_c.py derives
# them from the fixed requirements' text: the event axis, the see-path axis (R = what reaches the strategy's call,
# O = what the order call returns there and then, X = what the cancel call returns there and then, Q = what the
# strategy reads through the target's public means) and P0-2's time units / P0-7's plug points. A declared cell
# counts ("場面にした") only when its event type comes out of the scene's input by machine (`covers_of` below): a
# market type is the type field of an event the input holds (for a `type_plan` scene, the input built for a target
# with all six types); the clock and the notices come from the input's `requests` field. A declaration whose event
# type the input does not give is named by `covers_problems` and a test fails (it is never dropped silently).
# Which of the three order notices a scene measures is not decided by the input (the order request gives all three);
# the declaration names it and the critic reads it. Round r13-1 (ROOTCAUSE_r13-1.md section 6): a scene declares a
# see-path only when its `measures` names that path as a way its result is observed, and an event only when what is
# observed along it is that event's content -- p6-place-then-cancel reads the count of open orders (not a notice),
# the P0-7 scenes read the fill either as the strategy received it or from the run's fill record afterwards (not
# "what the strategy reads through the target's public means"), and p7-account-swap reads the plugged account's own
# record (no see-path of the axis): those declare nothing there.
_MKT = ("約定", "板の写真", "板の差分", "足", "資金調達", "清算")
_R, _O, _X, _Q = ("戦略の呼び出しに届く物", "発注の呼び出しがその場で返す物", "取消の呼び出しがその場で返す物",
                  "戦略が対象の公開の手段で読む物")
_ACC, _REJ, _FIL = "注文の受付の通知", "注文の拒否の通知", "注文の約定の通知"
_CANCEL = "取消の通知(要件 §1 の事象の型の外)"
COVERS: dict[str, list[tuple[str, str, str]]] = {
    "p1-merge-by-time": [(e, _R, "") for e in ("約定", "板の写真", "板の差分")],
    "p1-one-call-per-event": [("足", _R, "")],
    "p1-typed-events": [(e, _R, "") for e in ("約定", "板の写真")],
    "p2-iso-utc": [],
    "p2-iso-offset": [],
    "p2-event-time-exact": [],
    "p2-one-ns-apart": [],
    **{_i: [] for _i in UNIT_SCENES},
    **{f"p3-{k}": [(JP[k], _R, "")] for k in ("trade", "book_snapshot", "book_delta", "bar", "funding", "liquidation")},
    "p3-mixed-one-run": [(e, _R, "") for e in _MKT],
    "p3-clock-timer": [("時計", _R, "")],
    "p3-notice-accepted": [(_ACC, _R, ""), (_ACC, _O, "")],
    "p3-notice-rejected": [(_REJ, _R, ""), (_REJ, _O, "")],
    "p3-notice-filled": [(_FIL, _R, ""), (_FIL, _O, "")],
    "p4-visible-at-step": [("足", _Q, "")],
    "p4-received-time": [("約定", _R, "")],
    "p4-future-read-attempt": [("足", _Q, "")],
    "p5-same-time-twice": [(e, _R, "") for e in ("約定", "板の写真", "板の差分", "足")],
    "p5-hand-over-order": [(e, _R, "") for e in ("約定", "板の写真", "板の差分", "足")],
    "p5-same-stream-order": [("約定", _R, "")],
    "p6-place-then-cancel": [],
    "p6-cancel-notice": [(_CANCEL, _R, "")],
    "p6-fill-seen-by-strategy": [(_FIL, _Q, "")],
    "p7-fill-model-swap": [(_FIL, _R, "約定模型")],
    "p7-latency-model-swap": [(_FIL, _R, "遅延模型")],
    "p7-cost-model-swap": [(_FIL, _R, "費用")],
    "p7-cost-per-unit": [(_FIL, _R, "費用")],
    "p7-account-swap": [],
}
# cells outside the requirements' axes a scene covers, with the reason (checked by the tests)
OUTSIDE_AXES = {_CANCEL: "要件 §1 の通知は「注文の受付/拒否/約定の通知」の 3 つで、取消の通知を名指さない"}
assert set(COVERS) == {s.id for s in SCENES}, sorted(set(COVERS) ^ {s.id for s in SCENES})
# round r13-1: the kinds a scene's `requests` field may hold, and the event types each one gives
REQUEST_TYPES = {"timer": ("時計",), "place": (_ACC, _REJ, _FIL), "cancel": (_CANCEL,)}


def input_events(scene: Scene) -> list:
    """The event items of the scene's input: every item of `events` and of every stream, in that order (a `type_plan`
    scene: the input built for a target with all six types; none when the target would have too few). Round r15-1:
    the one reader of the input's events that `input_types` and grid_c.unplaced share."""
    built = for_target_types(scene, TYPE_ORDER) if scene.type_plan is not None else scene
    inp = built.input if built is not None and isinstance(built.input, dict) else {}
    evs = list(inp.get("events") or [])
    for stream in (inp.get("streams") or {}).values():
        evs += list(stream)
    return evs


def input_types(scene: Scene) -> set:
    """The event types that come out of the scene's input by machine (round r13-1, ROOTCAUSE_r13-1.md section 3):
    the type field of every event of `events` and of every stream (a `type_plan` scene: the input built for a target
    with all six types), and the types the `requests` field gives. An event without a type field gives nothing; a
    type outside the six market types or an unknown request raises ValueError (never dropped silently)."""
    evs = input_events(scene)
    out = set()
    for e in evs:
        if isinstance(e, dict) and "kind" in e:
            if e["kind"] not in TYPE_ORDER:
                raise ValueError(f"{scene.id}: an event of a type outside the market types: {e['kind']!r}")
            out.add(JP[e["kind"]])
    own = scene.input if isinstance(scene.input, dict) else {}
    if "requests" in own:
        req = own["requests"]
        if not isinstance(req, list) or any(r not in REQUEST_TYPES for r in req):
            raise ValueError(f"{scene.id}: `requests` must be a list of {sorted(REQUEST_TYPES)}: {req!r}")
        for r in req:
            out.update(REQUEST_TYPES[r])
    return out


def covers_of(scene: Scene) -> tuple:
    """The declared cells that count, in the declaration's order: those whose event type comes out of the input."""
    types = input_types(scene)
    return tuple(tuple(c) for c in scene.declares if c[0] in types)


def covers_problems(scene: Scene) -> list:
    """The declared cells whose event type does not come out of the input (a test fails on any)."""
    types = input_types(scene)
    return [tuple(c) for c in scene.declares if c[0] not in types]


# Round r16-1 (critic i0-r15-05; ROOTCAUSE_r16-1.md section 3 item 1): the extra-axis values a scene's input gives by
# machine (families 10 of section 4). The axis names are grid_c_judgments.tsv's (a test checks them); the unit codes'
# words are UNIT_WORDS; a value outside the viewpoint's axis carries its reason in OUTSIDE_EXTRA (a test checks it).
TIME_AXIS, PLUG_AXIS = "時刻の単位", "差し込む口"
OUTSIDE_EXTRA = {"マイクロ秒": "要件 P0-2 の文は「他の単位(秒・ミリ・ISO 文字列)」と括弧で 3 つを列べ、マイクロ秒を列べない。"
                              "マイクロ秒は括弧の外の「他の単位」の 1 つとして場面にした(軸の値は要件の文の切片からだけ作るので、軸には足さない)"}


def extra_values_of(scene: Scene) -> set:
    """{(axis, value)} the scene's input gives: `iso` (a str) -> ISO 文字列; `unit` (s / ms / us, with a `time`) -> its
    word; an event item (input_events) whose `ts_ns` is an int, not a bool -> int64 ナノ秒; `plug` (a str holding ":")
    -> the text before the first ":", stripped. Anything else in those fields raises ValueError (never dropped)."""
    inp = scene.input if isinstance(scene.input, dict) else {}
    out = set()
    if "iso" in inp:
        if not isinstance(inp["iso"], str):
            raise ValueError(f"{scene.id}: `iso` must be a str: {inp['iso']!r}")
        out.add((TIME_AXIS, "ISO 文字列"))
    if ("unit" in inp) != ("time" in inp):
        raise ValueError(f"{scene.id}: `unit` and `time` go together")
    if "unit" in inp:
        if inp["unit"] not in UNIT_WORDS:
            raise ValueError(f"{scene.id}: `unit` must be one of {sorted(UNIT_WORDS)}: {inp['unit']!r}")
        out.add((TIME_AXIS, UNIT_WORDS[inp["unit"]]))
    if any(isinstance(e, dict) and type(e.get("ts_ns")) is int for e in input_events(scene)):
        out.add((TIME_AXIS, "int64 ナノ秒"))
    if "plug" in inp:
        plug = inp["plug"]
        if not isinstance(plug, str) or ":" not in plug:
            raise ValueError(f"{scene.id}: `plug` must be a str with ':' after the plug point: {plug!r}")
        out.add((PLUG_AXIS, plug.split(":", 1)[0].strip()))
    return out


def l438_2_ok(ids_with_type_plan, scenes=None) -> bool:
    """The scenes whose type combination is taken from the configured target (those with a `type_plan`) are
    exactly the four L-438 (2) names by id, all of P0-1 or P0-5 (round r8-1, LEAD_DESIGN.md section 7.2 item 10)."""
    by = {s.id: s for s in (scenes or SCENES)}
    ids = list(ids_with_type_plan)
    return (len(ids) == len(set(ids)) == 4 and set(ids) == set(L438_2_SCENES)
            and all(i in by and by[i].viewpoint in ("P0-1", "P0-5") for i in ids))


assert l438_2_ok([s.id for s in SCENES if s.type_plan is not None]), "L-438 (2) names four scenes by id"
from dataclasses import replace as _replace  # noqa: E402
SCENES[:] = [_replace(s, declares=tuple(tuple(c) for c in COVERS[s.id])) for s in SCENES]

assert len(SCENES) == len({s.id for s in SCENES}), "duplicate scene id"
for _vp in VIEWPOINTS:
    assert any(s.viewpoint == _vp and s.kind == "value" for s in SCENES), f"{_vp} has no value scene"


# ---------------------------------------------------------------- round r7-1: a scene for one target's types
def for_target_types(scene: Scene, target_types) -> Scene | None:
    """The scene with its input and expected result built for a target that
    has these event types (TYPE_ORDER names), or None when the target has
    fewer types than the scene's `type_plan` needs. Scenes without a
    `type_plan` come back unchanged."""
    if scene.type_plan is None:
        return scene
    types = plan_types(scene.type_plan, target_types)
    if types is None:
        return None
    built = BUILDERS[scene.id](types)
    from dataclasses import replace
    return replace(scene, input=built["input"], expected=built["expected"])
