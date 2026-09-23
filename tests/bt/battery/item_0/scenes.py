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

  capability -- "can the target actually do X", invoked for real. **Every
      capability scene below also carries an `expected` and a `derivation`**
      (2026-09-23 fix, 場面集の規則1: "能力の場面も、呼んだ結果を正解と
      突き合わせる。「持っている」という申告...は数えない。能力があるかは、
      その能力を使ったときに出るはずの結果(正解)が出たかで決める").
      The round-1 build of this file left `expected=None` for every
      capability scene and `run_battery.py` recorded whatever `status` word
      the adapter self-reported -- the監査役 rejected this because a
      mutant's *prose claim* ("a future-peeking method exists!") could not
      be told apart from a genuine finding by the runner itself; only a
      human critic re-reading the cited code line by line could catch it.
      Every capability scene here now states, in `derivation`, exactly what
      *observable* result an adapter must produce to count as correct, and
      `expected` is that result (or the required subset of it) so
      `run_battery.py` can grade it the same mechanical way it grades a
      known-answer scene -- self-reported prose no longer decides the
      verdict.

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
    expected: Any = None          # the correct/required observable result -- for BOTH kinds
                                   # (2026-09-23: capability scenes are no longer exempt, 場面集の規則1).
                                   # A dict `expected` is graded as a required-subset match against a
                                   # dict `output` (extra informational keys in `output` are fine);
                                   # any other type is graded by exact equality. See run_battery.py
                                   # `_grade`.
    derivation: str = ""          # how `expected` was determined -- by hand (known_answer) or by
                                   # stating the one observable action that only a genuine
                                   # implementation of the capability can produce (capability)
    notes: str = ""


# ---------------------------------------------------------------------------
# Viewpoint 1 -- event-driven architecture (has a catalog column: has/has not)
# ---------------------------------------------------------------------------

_V1_EVENTS = [
    {"kind": "bar", "ts_ns": 1_700_000_000_000_000_000 + i * 60_000_000_000,
     "close": 100.0 + i}
    for i in range(5)
]

V1 = [
    Scene(
        id="v1-event_driven-cap",
        viewpoint=1,
        kind="capability",
        title="1件ずつ事象を渡して駆動できるか",
        input={"events": _V1_EVENTS},
        expected={"event_driven": True},
        derivation=(
            "5件の合成事象を1件ずつ(逐次)供給する呼び口の有無そのものが観測できる結果:"
            "対象の戦略コールバックが事象ごとに1回、計5回呼ばれれば逐次駆動(event_driven=True)、"
            "1回だけ(または0回)なら一括のベクトル処理でしかない(event_driven=False)。"
            "5件・0件・1件しかありえない閉じた式であり、手計算そのもの(期待値は5回呼ばれること)。"
            "「持っている」という自己申告の文字列ではなく、対象へ実際に5件投入して呼ばれた回数を"
            "数えた結果で判定する(場面集の規則1)。"
        ),
        measures=(
            "対象へ5件の合成事象を1件ずつ(逐次)供給する呼び口があるか。"
            "一括の配列/DataFrameでしか受け付けられない場合は「持たない」。"
            "戦略コードが1事象ごとに1回呼ばれた回数を数える(5であれば逐次駆動、"
            "1であれば一括のベクトル処理とみなす)。"
        ),
    ),
    Scene(
        id="v1-event_driven-known",
        viewpoint=1,
        kind="known_answer",
        title="逐次供給された各事象で観測される「今」の時刻が入力の時刻列とそのまま一致するか",
        input={"events": _V1_EVENTS},
        expected={"now_sequence": [e["ts_ns"] for e in _V1_EVENTS]},
        derivation=(
            "入力は ts_ns が単調増加する5件の事象。各事象が戦略に届いたときに対象が報告する"
            "「今」の値(あるいは処理中の事象の時刻)を、届いた順に並べたものが正解。"
            "真に1件ずつ届けているなら、この列は入力の ts_ns 列とビット単位で一致するはずで"
            "(恒等写像、計算不要)、途中でどれか1件でも欠落・重複・別の値に化けていれば"
            "不一致になる。v1-event_driven-cap が「1件ずつ届く」ことを確認する能力の場面なのに"
            "対し、この場面は「届いた各時刻の値そのものが壊れていないか」を見る値の場面"
            "(場面集の規則3: 各観点に値の場面を1つ以上)。"
        ),
        measures="事象ごとのコールバックで観測される時刻が、入力の時刻列と欠落・変質なく対応するか。",
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
        expected={"supported": True},
        derivation=(
            f"「{_jp}」型の合成1件を対象へ実際に投入し、対象がその型を独立した事象として"
            f"受理・配送したか(supported=True)/しなかったか(supported=False)を実測する。"
            f"型が無ければ受理のしようがないので supported=False が唯一の正しい観測結果になる"
            f"——「型・名前がある」という申告だけでは数えない(場面集の規則1)。8種のうち"
            f"どれだけが supported=True を実測できるかが観点2の網羅性そのもの。"
        ),
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

# Two ts_ns values exactly 1 nanosecond apart, at "now"-scale magnitude
# (~1.7e18, same order as the other viewpoint-3/4 scenes' epoch-ns values).
# See v3-precision-cap's derivation below for why this pair -- rather than any
# implementation's internal type name -- is the requirement-derived probe.
_TS_A = 1_700_000_000_000_000_000
_TS_B = _TS_A + 1  # +1 ns, deliberately NOT round in any other unit

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
        title="隣接する1ナノ秒差の2時刻を区別して保持できるか",
        input={
            "event_a": {"kind": "clock", "ts_ns": _TS_A},
            "event_b": {"kind": "clock", "ts_ns": _TS_B},
        },
        expected={"distinguishable": True},
        derivation=(
            "2026-09-23再修正(監査役の[止める]、場面集の規則2『場面は振る舞いを試し、作りの形を"
            "試さない』)。旧版の期待値 {'unit': 'ns', 'timezone': 'UTC'} は、同じコミット"
            "(baacefa)で同時に追加された新実装の内部契約 src/bot/bt/core/contract.py の "
            "CORE_CONTRACT['time'] のキー・値と文字通り一致しており、要件文から独立に導いた"
            "ものか新実装の内部の形をそのまま採用したものか監査役に問われた(git show で同時"
            "追加を確認済み)。実際、旧版は当方の調査結果側アダプタの実測出力"
            "(例: zipline-reloaded は {'dtype': 'pandas.Timestamp (int64 ns, tz-aware)'}、"
            "qf-lib は {'dtype': 'datetime.datetime (microsecond precision)'} で申告してい"
            "た。'unit'/'timezone' キーを持たないため、実際にはnsを厳密に保持できる"
            "zipline-reloaded の pandas.Timestamp 経路までもが機械比較で不一致になっていた"
            "= 新実装の語彙だけが通る設計だった、という欠陥を含んでいた)。"
            "この版は要件文(『時刻はUTCのint64ナノ秒』)のみから、実装の内部名に頼らない"
            "観測可能な必要条件を導く: int64ナノ秒である以上、1ナノ秒だけ離れた2つの時刻は"
            "厳密に異なる整数として区別できねばならない。IEEE754 float64 は仮数部52ビットで"
            "2**53(=9,007,199,254,740,992)を超える整数を正確に表現できない。"
            "1,700,000,000,000,000,000(約1.7e18)はこの閾値を大きく超えており、実測"
            "(`python3 -c \"import math; a=1_700_000_000_000_000_000.0; "
            "print(math.nextafter(a, math.inf)-a)\"` -> 256.0)のとおり、この桁の float64 は"
            "隣接する表現可能値の間隔(ULP)が256もあるため、1ナノ秒差の2値は必ず同じ float64 "
            "に潰れる(区別不能)。よって「distinguishable=True」は要件(int64ナノ秒)だけから"
            "導ける閉じた必要条件であり、int64・Decimal・厳密な整数保持型のいずれでも自動的に"
            "満たされ、float64(秒/ns)・datetime.datetime(マイクロ秒止まり)のような精度を"
            "落とす型では構造的に満たせない。対象がどんなキー名・型名で内部を申告するかには"
            "一切依存しない。"
        ),
        measures=(
            "対象へ ts_ns が厳密に1だけ異なる2つの合成事象を投入し、対象が報告する2つの"
            "時刻の値が実際に区別できるか(同じ値に潰れていないか)を実測する。"
            "「int64 ns で持っている」という自己申告の型名・キー名では判定しない"
            "(場面集の規則1・規則2)。"
        ),
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
        expected={"future_index_raises": True},
        derivation=(
            "2026-09-23修正(場面集の規則1): 旧版は「構造上そもそも存在しないと申告できるか」を"
            "文章で自己申告させ、run_battery.py はその申告をそのまま記録するだけだった"
            "(監査役の指摘、試金石 mutant.py の `_fake_cap_claim` が実在しない"
            "`peek_next(n=1)` を『存在する』と偽って主張してもこの場面単体では検出できなかった)。"
            "この版は自己申告をやめ、実際に1つ先(probe_index+1個目、まだ届いていないはずの"
            "事象)を、known答え合わせの場面(v4-lookahead-known)と同じ経路で取得しようと"
            "**実際に試す**: probe_index+1件目までしか届いていない時点で、届いた列の"
            "「1つ先」を公開の手段(索引アクセス等)で読もうとする。正解は「読めない"
            "(IndexError相当の例外か、読み出し不可を示す明示的な失敗)」= future_index_raises: True。"
            "黙って値が返る(=1つ先のbarのcloseが読めてしまう)なら False で不一致になる。"
            "対象がこの実測を行える手段を持たない場合は対応なし。"
        ),
        measures=(
            "戦略コードから「今」より先の事象を取得できる公開の手段(索引アクセス・"
            "全件配列の直接参照など)が構造上そもそも存在しないか(存在しない=良い)。"
            "自己申告ではなく、実際に1つ先を読もうと試みて失敗するかを実測する。"
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
        title="同時刻の並びが投入順ではなく規則に基づくか(投入順を変えて再確認)",
        input={"events": _TIED_EVENTS, "events_reversed": list(reversed(_TIED_EVENTS))},
        expected={"order_independent_of_input_order": True},
        derivation=(
            "2026-09-23修正(場面集の規則1): 旧版は『規則を明記しているか』を自己申告の文章"
            "(prose)で答えさせていた(申告文字列が本物の規則かは読者が検証するしかなかった)。"
            "この版は同じ4件の同時刻事象を(a)元の投入順(A,B,C,D)と(b)逆順(D,C,B,A)の"
            "2通りで実際に処理させ、出てきた処理順序が両方で一致するかを実測する。"
            "もし対象が『投入順=処理順』でしかない(=規則ではなく偶然の並びに従っているだけ)"
            "なら、入力の並びを逆にすれば出力も逆になり不一致になる。内容(型・時刻)に基づく"
            "決定的な規則を本当に適用しているなら、入力の並びを変えても同じ処理順序が出るのが"
            "正解(order_independent_of_input_order=True)。v5-order-knownの『同じ入力を2回"
            "実行して同じ順序か』(再現性)とは別の軸: こちらは『入力の並びを変えても規則が"
            "支配するか』(規則の実在)を見る。"
        ),
        measures="同一タイムスタンプの事象順序を決める規則を、対象が明記(実装のコードまたは契約)しているか。入力の並びを変えても同じ処理順序になるかを実測する。",
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
        expected={"count": 3},
        derivation=(
            "§1直書きの要件は『戦略のAPI(事象ごとの呼び出し・発注・取消)』の3つ。"
            "対象の公開API(クラス定義・契約データ)を実測して hasattr 相当で3つそれぞれの"
            "有無を数える。正解は3つとも揃っていること(count=3)。1つでも欠ければ"
            "count<3で不一致 -- 個数という閉じた整数なので自己申告ではなく実測値そのもので"
            "判定できる。"
        ),
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
        expected={"count": 4},
        derivation=(
            "§1直書きの要件は『他項目が差し込む口(約定模型・遅延模型・費用・口座)』の4つ。"
            "対象の公開API(コンストラクタ引数・契約データ)を実測して4口それぞれの有無を"
            "数える。正解は4つとも揃っていること(count=4)。個数という閉じた整数なので"
            "自己申告ではなく実測値そのもので判定できる。"
        ),
        measures="約定模型・遅延模型・費用・口座の4要素それぞれについて、核を書き換えずに差し替え可能な口を持つか(0〜4の数)。",
    ),
]


SCENES: list[Scene] = V1 + V2 + V3 + V4 + V5 + V6 + V7

assert len(SCENES) == len({s.id for s in SCENES}), "duplicate scene id"
