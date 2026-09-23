# 項目 0(核)ラウンド 2 — 直す前の根本原因分析

指紋: `20260923_backtest_env_prompt.md@a723df99ad38` §3「根本的解決」に従い、前周(round_1)で未解消の指摘 4 件について、
直す前に「なぜ起きたか(根本原因)」と「どの構造を変えるか」をここに書く。場当たりの直し(試験だけの特別扱い・閾値や既定値をずらす・
文言合わせ・機能を外す)はしない。

## i0-r1-01(止める): `EngineResult.order_requests` の `client_order_id` が戦略に返した ID と一致しない

**根本原因**: `CoreEngine._place_order`(engine.py:68-72)は、ID を**その場で新しく計算して戦略へ返す**処理と、
**発注記録を `self._order_requests` に積む**処理を、同じ関数の中で行っていながら、両者が別々の値を見ていた
(返り値は計算した `client_order_id`、記録は関数に渡された元の `request`)。「戦略へ返した ID」と「記録に残る ID」が
本来同一のものを指すはずなのに、コード上は 1 回の代入で結ばれておらず、たまたま両方とも正しく更新されることを
期待する暗黙の前提になっていた。

**変える構造**: ID を決めたら、**記録に積む `OrderRequest` 自体をその ID を持つオブジェクトに置き換える**
(`dataclasses.replace` で `client_order_id` を上書きした新しいインスタンスを作り、それを `self._order_requests` に積む)。
これにより「戦略に返した ID」と「記録の ID」は同じ 1 回の代入から生まれる同一の値になり、以後どちらかだけを直して
もう片方を直し忘れる、という分岐そのものが構造上なくなる。

## i0-r1-02(直す): `visible_events(n=0)` が「0 件」ではなく「全件」になる

**根本原因**: `events[-n:]`(api.py:80)という書き方は「末尾 n 件」を Python のスライスの符号反転に**丸投げ**しており、
`n` が「有効な件数(0 以上の整数)」という契約上の意味を持つのに、Python の言語仕様(`-0 == 0` で `events[0:]` = 全件)という
**別の意味論**にそのまま乗せてしまっていた。契約("last n") とスライス構文("`[-n:]`")の意味がずれる境界(`n=0`)を
明示的に扱っていなかったことが原因。

**変える構造**: `n` を「件数の契約」として明示的に分岐させる。`n is not None` の中で、まず `n <= 0` を専用に判定して
空タプルを返し、その後にだけ `events[-n:]`(この時点で `n >= 1` が保証されている)を使う。スライス構文の暗黙の意味論に
境界値の解釈を委ねる箇所をなくす。

## i0-r1-03(止める): `CoreEngine.run` が O(n^2)

**根本原因**: `engine.py:82` の `visible = self._log[: i + 1]` は、**「戦略がどこまで見てよいかの境界(i+1 という数)を
決める」処理**と、**「その境界までの事象を実際にコピーして tuple を作る」処理**を 1 行で同時にやっている。
前者は本来 O(1)(整数 1 個)で済むのに、後者(タプルのコピー)を**戦略が実際に履歴を要求したかに関係なく毎回強制**しているため、
ループ全体で 1+2+...+n = O(n^2) になる。「境界を決める」と「材料を実体化する」を分けていなかったことが根本原因。

**変える構造**: 境界(ログ全体 `self._log` と終端インデックス `i+1`)だけを保持する O(1) construction のビュー
(`window.py: EventWindow`、`collections.abc.Sequence` を実装し `len`/`__getitem__`/`__iter__` を提供、
実データは元の `self._log` を指すだけでコピーしない)を新設し、これを毎イテレーション作る(O(1))。`StrategyContext` と
`FillModel.on_event` にはこのビューを渡す。実際にタプルとして実体化するのは `StrategyContext.visible_events()` が
**呼ばれたとき**(戦略が実際に履歴を要求したとき)だけで、その時のコストは戦略が要求した分だけに限られ、
呼ばれなければ 0 になる。ループ本体の 1 イテレーションあたりのコストは O(1) になる。

## i0-r1-04(直す): `LiquidationEvent` に `Account` への差し込み口が無い

**根本原因**: 口座への差し込み(`apply_*`)は、「決済・清算のように口座残高が動く事象は口座へ通知する」という
**規則から導かれた集合**としてではなく、`FUNDING` という**個別の事象 1 つに対してその場で配線した**
(`engine.py:98-99` の `if event.EVENT_TYPE is EventType.FUNDING:`)。`LiquidationEvent` は
`events.py:91-96` の docstring 自身が「ours or market-wide」= 自分の建玉の強制決済を表しうると書いているのに、
「口座残高が動く事象」という同じ性質を持つ `FUNDING` と揃えて配線されなかった。個別対応の寄せ集めであって、
「口座に届くべき事象の集合」という構造を最初から持っていなかったことが原因。

**変える構造**: `interfaces.Account` プロトコルに `apply_funding` と対になる `apply_liquidation` を追加し、
`NullAccount` にその no-op 実装を足したうえで、`engine.py` の該当行を
`if event.EVENT_TYPE is EventType.FUNDING: ... / if event.EVENT_TYPE is EventType.LIQUIDATION: ...`
と**同じ形**で並べて書く(FUNDING と LIQUIDATION を対称に扱う)。これにより「口座に届く決済系事象」が
1 つの事象だけの特別扱いではなく、同じパターンを共有する複数事象として構造的に揃う。

**限界(正直に書く)**: `tests/bt/critic/item_0/test_liquidation_has_no_account_hook.py` の
`_RecordingAccount`(この試験ファイル自身が定義するテストダブル)は `apply_fill` と `apply_funding` は持つが
`apply_liquidation` を持たない。上記の構造変更(`apply_liquidation` を `FUNDING` と同じ形で無条件に呼ぶ)を入れると、
この `_RecordingAccount` に対しては `AttributeError` になる可能性がある。この試験ファイルは項目 0 の持ち物
(`src/bot/bt/core/`)の外にあり、作業者は書き換えない。報告の「リードに聞くこと」に事実(実行結果)を書く。
