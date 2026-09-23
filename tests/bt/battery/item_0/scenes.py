"""Scene definitions for item 0 ("核") of the backtest-environment battery.

This file is the single source of truth for the scene set. `DEFINITIONS.md`
in this same directory is a generated, human-readable rendering of exactly
this data (see `gen_definitions.py`) -- if you change a scene here, regenerate
that file so the two never drift.

Two scene kinds (delegation doc `docs/DATA/delegations/20260923_backtest_env_prompt.md`
Sec.3 "scene set"):

  known_answer -- a synthetic input plus an expected output computed BY HAND
      (closed form, without looking at any engine). `expected` and
      `derivation` are filled in below; the derivation is the arithmetic /
      rule an auditor can redo without running any code.

  capability -- "can the target actually do X", invoked for real. There is
      no single "correct" value; the runner records what the adapter
      reports and the scene states what property that answer measures.

No tool/product name appears in this file (delegation doc Sec.3 item 1:
"道具の名前は書かない"). Adapters (which DO know which product they wrap)
translate an opaque `scene_id` + `input` into a `SceneResult` defined in
`adapters/protocol.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

SceneKind = Literal["known_answer", "capability"]


@dataclass(frozen=True)
class Scene:
    id: str
    viewpoint: int  # 1..7, matches REQUIREMENTS.md Sec.2
    kind: SceneKind
    title: str
    input: dict[str, Any]
    measures: str  # what the scene measures, one sentence
    expected: Any = None          # only for kind == "known_answer"
    derivation: str = ""          # only for kind == "known_answer": how `expected` was computed by hand
    notes: str = ""


# ---------------------------------------------------------------------------
# Viewpoint 1 -- event-driven architecture (has a catalog column: has/has not)
# ---------------------------------------------------------------------------

V1 = [
    Scene(
        id="v1-event_driven-cap",
        viewpoint=1,
        kind="capability",
        title="1件ずつ事象を渡して駆動できるか",
        input={
            "events": [
                {"kind": "bar", "ts_ns": 1_700_000_000_000_000_000 + i * 60_000_000_000,
                 "close": 100.0 + i}
                for i in range(5)
            ]
        },
        measures=(
            "対象へ5件の合成事象を1件ずつ(逐次)供給する呼び口があるか。"
            "一括の配列/DataFrameでしか受け付けられない場合は「持たない」。"
            "戦略コードが1事象ごとに1回呼ばれた回数を数える(5であれば逐次駆動、"
            "1であれば一括のベクトル処理とみなす)。"
        ),
    ),
]


# ---------------------------------------------------------------------------
# Viewpoint 2 -- event type coverage (8 types; 3 have a catalog column)
# ---------------------------------------------------------------------------

_EVENT_TYPES = [
    ("fill", "約定", {"ts_ns": 1_700_000_000_123_456_789, "price": 5_012_345.0, "qty": 0.01, "side": "buy"}),
    ("book_snapshot", "板の写真", {"ts_ns": 1_700_000_000_123_456_789,
                                    "bids": [[5_012_000.0, 0.5]], "asks": [[5_012_500.0, 0.4]]}),
    ("book_delta", "板の差分", {"ts_ns": 1_700_000_000_123_456_789, "side": "bid", "price": 5_012_000.0, "size": 0.3}),
    ("bar", "足", {"ts_ns": 1_700_000_000_000_000_000, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 12.0}),
    ("funding", "資金調達", {"ts_ns": 1_700_000_000_000_000_000, "rate": 0.0001}),
    ("liquidation", "清算", {"ts_ns": 1_700_000_000_123_456_789, "price": 4_990_000.0, "qty": 0.2, "side": "sell"}),
    ("clock", "時計", {"ts_ns": 1_700_000_000_000_000_000}),
    ("order_notice", "注文の受付/拒否/約定の通知", {"ts_ns": 1_700_000_000_123_456_789, "notice": "accepted", "order_id": "synthetic-1"}),
]

V2: list[Scene] = []
for _key, _jp, _sample in _EVENT_TYPES:
    V2.append(Scene(
        id=f"v2-{_key}-cap",
        viewpoint=2,
        kind="capability",
        title=f"事象型「{_jp}」を扱えるか",
        input={"event_type": _key, "sample": _sample},
        measures=f"「{_jp}」型の事象を、実装のコードで確かめられる形で受理・処理できるか(持つ/持たない)。",
    ))
    V2.append(Scene(
        id=f"v2-{_key}-known",
        viewpoint=2,
        kind="known_answer",
        title=f"事象型「{_jp}」の値がそのまま往復するか",
        input={"event_type": _key, "sample": _sample},
        expected=dict(_sample),
        derivation=(
            "合成の1件をそのまま投入し、対象が保持/報告する値が入力と完全一致するかを見る。"
            "期待値は入力そのもの(恒等写像)なので手計算は不要 -- 一致しなければ、"
            "その型を値の損失なく保持できていないことを意味する。"
        ),
        measures=f"「{_jp}」型の主要フィールドが欠落・丸め・変質なく保持されるか。",
    ))


# ---------------------------------------------------------------------------
# Viewpoint 3 -- timestamp precision (UTC int64 ns)
# ---------------------------------------------------------------------------

# 2024-01-01T00:00:00.123456789Z, hand-computed:
#   days from epoch to 2024-01-01 = 19723 (365*54 + leap days 1970..2023 = 13 -> 19723)
#   19723 * 86400 = 1,704,067,200 seconds
#   + 0.123456789 s = 1,704,067,200.123456789 s
#   * 1e9 -> int64 ns = 1704067200123456789
_TS_ISO = "2024-01-01T00:00:00.123456789Z"
_TS_NS_EXPECTED = 1704067200123456789

V3 = [
    Scene(
        id="v3-precision-known",
        viewpoint=3,
        kind="known_answer",
        title="ISO8601(ナノ秒つき)の時刻を int64 UTC ナノ秒へ変換した値",
        input={"iso": _TS_ISO},
        expected=_TS_NS_EXPECTED,
        derivation=(
            "2024-01-01 00:00:00 UTC は 1970-01-01 からのうるう年を数えて 19723 日 "
            "(1972,76,80,...,2020 の 13 回のうるう日を含む)。19723*86400=1,704,067,200 秒。"
            "小数部 .123456789 秒を ns に換算して加算: 1,704,067,200,123,456,789 ns。"
            "`python3 -c \"import datetime as dt; print(int(dt.datetime(2024,1,1,tzinfo=dt.timezone.utc).timestamp()*1_000_000_000)+123456789)\"` "
            "でも同じ値が出ることを確認済み(1704067200123456789)。"
        ),
        measures="ナノ秒精度のタイムスタンプを、丸めずに int64 UTC ナノ秒として保持できるか。",
    ),
    Scene(
        id="v3-precision-cap",
        viewpoint=3,
        kind="capability",
        title="内部の時刻表現の型を申告できるか",
        input={},
        measures="対象が内部で時刻をどの型(int64 ns / float 秒 / その他)で持つかを、実装のコードまたは機械可読の契約から申告できるか。",
    ),
]


# ---------------------------------------------------------------------------
# Viewpoint 4 -- structural look-ahead prevention
# ---------------------------------------------------------------------------

# 6 synthetic bars, strictly increasing close price by +1 each bar so any
# leak of a later bar is detectable by comparing the observed max close to
# the hand-computed ceiling for step i.
_LA_BARS = [
    {"ts_ns": 1_700_000_000_000_000_000 + i * 60_000_000_000, "close": 100.0 + i}
    for i in range(6)
]

V4 = [
    Scene(
        id="v4-lookahead-known",
        viewpoint=4,
        kind="known_answer",
        title="時刻 t 時点で見える最大 close は bar[t].close を超えない",
        input={"bars": _LA_BARS, "probe_index": 3},
        # hand-computed: at step i=3 (0-indexed), only bars[0..3] have been
        # "received" (ts <= now); their closes are 100,101,102,103 -> max 103.
        expected={"max_visible_close": 103.0, "visible_count": 4},
        derivation=(
            "入力は close が 100,101,102,103,104,105 と単調増加する 6 本の合成足。"
            "probe_index=3 の時点で「受け取れた時刻 <= 今」を満たすのは bars[0..3] の4本のみ"
            "(100,101,102,103)なので、見えてよい close の最大値は 103.0、件数は4。"
            "105 や 104 が見えていれば未来の事象が漏れている。"
        ),
        measures="戦略側から観測できる事象が、探査時刻以前に受け取れたものだけに構造的に制限されているか。",
    ),
    Scene(
        id="v4-lookahead-cap",
        viewpoint=4,
        kind="capability",
        title="将来事象への直接アクセス手段の有無",
        input={"bars": _LA_BARS, "probe_index": 3},
        measures=(
            "戦略コードから「今」より先の事象を取得できる公開の手段(索引アクセス・"
            "全件配列の直接参照など)が構造上そもそも存在しないか(存在しない=良い)。"
        ),
    ),
]


# ---------------------------------------------------------------------------
# Viewpoint 5 -- deterministic ordering of same-timestamp events
# ---------------------------------------------------------------------------

_SAME_TS = 1_700_000_000_000_000_000
_TIED_EVENTS = [
    {"kind": "fill", "ts_ns": _SAME_TS, "tag": "A"},
    {"kind": "bar", "ts_ns": _SAME_TS, "tag": "B"},
    {"kind": "order_notice", "ts_ns": _SAME_TS, "tag": "C"},
    {"kind": "clock", "ts_ns": _SAME_TS, "tag": "D"},
]

V5 = [
    Scene(
        id="v5-order-known",
        viewpoint=5,
        kind="known_answer",
        title="同一タイムスタンプの事象列を2回処理して同じ順序が出るか",
        input={"events": _TIED_EVENTS},
        # The known answer here is NOT a specific order (no universal
        # tie-break rule exists across candidates) -- it is the equality of
        # run 1 and run 2. This is closed-form and needs no engine: any
        # deterministic system, by definition, satisfies run1_order == run2_order.
        expected={"run1_equals_run2": True},
        derivation=(
            "「決定的」の定義そのものが closed-form の正解を与える: 同じ入力を2回処理して"
            "得られる出力順序が一致することが、決定的順序規則を持つことの必要条件。"
            "一致しない場合、regardless of どんな規則を採用していても、その規則が実装に"
            "反映されていない(非決定的)と判定できる。"
        ),
        measures="同一タイムスタンプの複数事象を処理したとき、出力順序が実行のたびに再現するか。",
    ),
    Scene(
        id="v5-order-cap",
        viewpoint=5,
        kind="capability",
        title="同時刻の並びの規則が明記されているか",
        input={"events": _TIED_EVENTS},
        measures="同一タイムスタンプの事象順序を決める規則を、対象が明記(実装のコードまたは契約)しているか。",
    ),
]


# ---------------------------------------------------------------------------
# Viewpoint 6 -- strategy API completeness
# ---------------------------------------------------------------------------

V6 = [
    Scene(
        id="v6-order_lifecycle-known",
        viewpoint=6,
        kind="known_answer",
        title="注文を1件発注して1件取消すと未決注文数が0に戻るか",
        input={"order": {"side": "buy", "qty": 1.0}, "action": "place_then_cancel"},
        expected={"open_orders_after": 0},
        derivation=(
            "発注1件・取消1件という単純な操作列なので、操作後の未決注文数は代数的に "
            "1 - 1 = 0 。これはどんな注文管理の実装であっても成り立つべき不変条件。"
        ),
        measures="発注APIと取消APIが対になって機能するか(戦略が明示的に呼べる形であるか)。",
    ),
    Scene(
        id="v6-api_surface-cap",
        viewpoint=6,
        kind="capability",
        title="事象ごとのコールバック・発注・取消の3種の呼び口",
        input={},
        measures="戦略が呼べる公開APIとして (a) 事象ごとのコールバック (b) 発注 (c) 取消 の3種をそれぞれ持つか(0〜3の数)。",
    ),
]


# ---------------------------------------------------------------------------
# Viewpoint 7 -- extension points (module boundary)
# ---------------------------------------------------------------------------

V7 = [
    Scene(
        id="v7-cost_swap-known",
        viewpoint=7,
        kind="known_answer",
        title="費用模型をゼロコスト版に差し替えると手数料が0になるか",
        input={"order": {"side": "buy", "qty": 1.0, "price": 100.0}, "cost_model": "zero"},
        expected={"fee": 0.0},
        derivation=(
            "「ゼロコスト模型」という定義そのものから手数料は恒等的に0。核を書き換えずに"
            "この模型へ差し替えられれば、既定の非ゼロ手数料が0に変わって出力されるはず。"
            "差し替え口が無い実装は、この既知解を再現できない(対応なし、または既定値のまま)。"
        ),
        measures="核のコードを書き換えずに費用模型を差し替えられるか(構造としての拡張口の有無を、値の変化で確認する)。",
    ),
    Scene(
        id="v7-extension_points-cap",
        viewpoint=7,
        kind="capability",
        title="約定模型・遅延模型・費用・口座の4口",
        input={},
        measures="約定模型・遅延模型・費用・口座の4要素それぞれについて、核を書き換えずに差し替え可能な口を持つか(0〜4の数)。",
    ),
]


SCENES: list[Scene] = V1 + V2 + V3 + V4 + V5 + V6 + V7

assert len(SCENES) == len({s.id for s in SCENES}), "duplicate scene id"
