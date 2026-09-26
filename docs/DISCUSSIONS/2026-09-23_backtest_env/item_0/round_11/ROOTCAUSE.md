# 項目 0「核」第 11 周 — 直す前の根本原因(作業者)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(起動文の指紋 `d3eae0d221c9`。`sha256sum | cut -c1-12` で作業木の版と一致を確かめ、全 164 行を読んだ)。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
固定した要件: `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md`(変えない)。リードの設計: `round_7/LEAD_DESIGN.md`(§3.1〜§3.4、§7〜§7.5、§8。作業者に当たるのは §3.3・§3.4・§7.4 の 19・20・§8.3)。
行番号はこの周の初め(コミット `667cd4d` の作業木)のファイル。一時ファイルは `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/item0_r11_worker_*`(以下 `<S>`)。

## 0. この周に直す指摘と、この周の初めに確かめたこと

第 10 周は作業者の直しのあと、場面集の定義の段でリードに戻り、批評家は第 10 周の直しを見ていない。だから第 11 周の作業者は、第 10 周の直しが指摘の族の全部に当たっているかを自分で確かめ直し、残っていた同じ根の箇所を直す。

| id | 格 | 相手 | repeat_of | この周の初めに確かめたこと(コマンドと出力) |
|---|---|---|---|---|
| i0-r9-01 | 直す | 実装 | null | `PYTHONPATH=src python3 <S>/item0_r9_critic_probe_history_until.py` → `until_ns=T0+3s -> [1, 2] place (0, 1, 3, 0)` / `n=1, until_ns=T0+3s -> [2] place (1, 1, 3, 0)` / `until_ns=T0 (before every event) -> [] place (0, 1, 3, 0)`(制限なしは `[1, 2]` / `[2]` / `[]`)。批評家の神託 `item0_r9_critic_probe_history_oracle.py 80` → `{'ok': 375671, 'wrong': 0, 'silent_short': 0, 'over_refused': 0, 'place_wrong': 0, 'over_refused_nonempty': 0, 'over_refused_empty': 0}`(出力 `<S>/item0_r11_worker_recheck_history_oracle.out`) |
| i0-r9-02 | 直す | 実装 | i0-r8-01 | (a) `<S>/item0_r10_worker_probe_port_class_swap_tuple.py` → `port class now: Hook` だけ(OUTSIDE の記録も実行の失敗も無い)。(b) `<S>/item0_r10_worker_probe_closure_reach.py` → 全配達で `shared with the core's own state: []`、`callbacks with anything shared: 0`。批評家の元の試し 2 本は、名前(`eng._box` など)や物の置き場所で口を探すため、第 10 周の版では口を見つけられず止まる(`AttributeError: 'CoreEngine' object has no attribute '_box'` / `TypeError: __class__ assignment only supported for mutable types`) |
| i0-r9-03 | 直す | 場面集 | null | 場面係の持ち物。作業者は変えない |
| i0-r9-04 | 示唆 | 実装 | null | LEAD_DESIGN §8.3 で項目 8 の要件を固定するときに決めると答えがあった。この周は変えない |

## A. i0-r9-01 `history_limit` の下で、答えの全部が保たれている読み出しを断る

### なぜ起きたか(根本原因。第 10 周の ROOTCAUSE §A と同じ読み)

1. 読み出しの規則を定義(「制限なしの答えが落とした事象を含むときだけ断る」)から導かず、「断らない場合」の一覧(`since_ns` が最後に落とした事象より後 / `n` が保たれた事象に収まる)で書いた。一覧の外(`until_ns` で手前を切る・落とした事象の間の隙間を読む・全部の前を切る)が断られた。
2. 核が落とした部分について持つ事実が型ごとに「最後に落とした 1 件」だけで、定義を判定するのに足りなかった(隙間があるので両端でも足りない)。足りない所を「断る」に倒した。
3. 作業者の試験が実装の条件を写した神託だった(断ったとき最後に落とした事象が `since_ns` 以後にある、だけを見た)。

### どの構造を変えたか(第 10 周)と、この周に足すもの

- 第 10 周: 落とした事象の事実を全部(型ごとに `array('q')` 2 本)残し、読み出しは二分探索で定義そのものを判定する 1 つの関数にした(`api.py` 807-848 行 `__refuse_truncated`、790-805 行 `__empty_answer`、`history.py` 241-260 行 `dropped_in_range`・`dropped_before`)。試験 `tests/bt/item_0/test_bt0_r10_history_read_oracle.py`(規則の文だけから作った神託 × 全格子)。
- この周に足すもの: LEAD_DESIGN §8.3 の答え「history_limit は保つ事象の数を抑え、落とした事実の数は抑えない(1 件 16 バイト)」を契約 `visibility.history_limit` に書く。コードの構造は変えない(上の確かめ直しで、批評家の神託の 37 万余の読み出しに誤り・断りすぎ・位置の誤りが 0)。

## B. i0-r9-02 核が戦略のコードを `on_event` の外で走らせる / 戦略が届く物と核の物の区分(族 i0-r8-01)

### なぜ起きたか(根本原因)

1. **第 10 周までの読み**: 核が、戦略の届く物に、その物の class を通して触っていた(`port._now` の書き込み、`_drain` の `object.__getattribute__`、`_revoke` の `object.__setattr__` など)。戦略の届く物と核の物の区分が構造に無かった。第 10 周はこれを `_StrategySide` に集め、核はそこの物に基の型の C の関数でしか触らない形にした。
2. **この周に自分で探して見つけた同じ根の箇所**(第 10 周の区分は「戦略が**届く**物」= 文脈から歩いて届く物に当てたが、「戦略が核に**渡す**物」は届く物だけではない。戦略が核に渡す物を、道ごとに列べずに「戦略のコードが作った物で、核が後で持つ物」として探し直した):
   - **戦略が投げた例外**。`on_event` から出た例外は `step()` が `self._failure` に持ち、以後の `step()`・`run()`・`result()` の断りの文を作る所(`engine.py` 860-878 行 `_usable`(867 行 `text = str(failure)`))で `str(failure)` と `type(failure).__name__` を呼ぶ。`str()` は例外の class の `__str__`(戦略のコード)を走らせ、`__name__` は例外の class のメタクラスの属性を走らせうる。どちらも `on_event` の外(呼び手の `run()` / `result()` の中)。確かめ: `PYTHONPATH=src python3 <S>/item0_r11_worker_probe_failure_text.py` → `step -> builtins RuntimeError | is EngineFailedError: False` / `run -> builtins RuntimeError …` / `result -> builtins RuntimeError …` / `strategy code run: [('__str__', 'OUTSIDE on_event'), ('__str__', 'OUTSIDE on_event'), ('__str__', 'OUTSIDE on_event')]`(出力 `<S>/item0_r11_worker_probe_failure_text.before.out`)。**これは契約 `lifecycle` の「FAILED の核は以後の呼び出しを `EngineFailedError` で断る」も破る**(戦略の `__str__` が投げた `RuntimeError` がそのまま出る)。差し込み口(約定模型・遅延模型・費用・口座)と入力の流れが投げた例外も同じ道を通る。
   - **型の名前の読み方**(`values.type_name`、`engine.py` `_qualname`): 断りの文と結果の `models` を作るとき、`t.__module__`・`t.__qualname__` を普通の属性の読みで取る。class の `__module__` は class の本体で任意の物にでき(例: `__format__` を持つ str の子)、メタクラスは `__qualname__` などを自分の記述子で上書きできる。`result()` は差し込み口の class の名前を**呼ばれるたびに**読む(`engine.py` 928-956 行、941 行 `models=`)。
3. **なぜ第 10 周で見つけられなかったか**: 第 10 周の敵対者の格子の入力の空間は「文脈から歩いて届く物」(到達性)と「出口の箱の値」だけで、**戦略が核に渡す道**(呼び出しの戻り・投げた例外・箱・届く物)を全部列べていなかった。例外は届く物でも箱でもないので、どの格子にも入らなかった。LEAD_DESIGN §2 と同じ形(扱う物の一覧の外)。
4. **第 10 周の格子の列の外(試験の穴)**: 到達性の変更の格子(`test_bt0_r9_reachable_state_adversary.py`)は、歩き方が関数の既定値(`__defaults__`)に入らず、閉じ込めの cell の中身の書き換え・`array` の書き換え・`list` / `dict` / `set` の変更の方法の一部(`pop`・`remove`・`extend`・`sort`・`update`・`popitem`・`setdefault`・`discard` など)を列に入れていない。第 10 周の `_StrategySide` で、落とした事実の `array` は関数の既定値から届くようになったので、この穴は第 10 周の直しで新しく開いた。LEAD_DESIGN §8.3「エンジンは `_StrategySide` の中の物を書くだけで、読むのは箱を 1 度写すときだけ、を試験で固定する」はこの格子で固定する。

### どの構造を変えるか

**規則(1 段落。契約に同じ趣旨を置く)**: 核の外のコード(戦略・差し込み口・入力の流れ)が作った物を、核がその持ち主の呼び出しの外で扱うときは、その物の class を通さない(方法・属性の読み・メタクラスの記述子を走らせない)。核が扱ってよいのは、基の型の C の方法と `type` 自身の記述子で読める事実だけで、それ以外は型の名前だけを書く。

1. **FAILED の断りの文を、例外の事実だけから作る**(`engine.py` `_usable`、`values.py` に関数を 1 つ)。型の名前は `type` 自身の記述子(`type.__dict__["__qualname__"]`・`["__module__"]`)で読み、str そのものでなければ(str の子は基の型の方法で写す)名前として使わない。例外の `args` は `BaseException` 自身の記述子で読み、要素が組み込みの str・int・float・bool そのもの(子でない)なら値を、そうでなければ型の名前だけを書く。例外の `__str__`・`__repr__`・`__format__`・メタクラスの属性は走らない。元の例外は今までどおり `__cause__` と `failure` で渡す。
2. **型の名前を読む関数を 1 つにする**(`values.type_name` を上の読み方にし、`engine.py` の `_qualname` もそれを使う)。差し込み口の名前(`result().models`)は構築のときに 1 度だけ読んで str として持ち、`result()` は差し込み口の class を読まない。
3. **試験(先に書く。LEAD_DESIGN §3.3)**:
   - **外のコードが作った物の格子**(`tests/bt/item_0/test_bt0_r11_foreign_objects.py`): 投げる所(戦略の `on_event`・遅延模型の 3 つの口・約定模型・費用・口座・入力の流れの `__next__`)× 例外の作り(`__str__`・`__repr__`・`__format__`・`__getattribute__`・`__eq__`/`__hash__` が走ると記録する / `args` に記録する物・str の子 / メタクラスの `__name__`・`__qualname__`・`__module__` / class の本体の `__module__` が記録する物 / `BaseException` の子 / 核の誤りの子 / 普通の例外)× 後の呼び出し(`step`・`run`・`result`)を全格子で列べる。神託: どの呼び出しも `EngineFailedError`(`__cause__` は元の例外)、例外を投げた後に記録が 1 件も無い、文に実際の型の名前がある。差し込み口の class にメタクラスで名前を読むと記録する物を付け、`run()` と `result()` の間に記録が無いことも見る。
   - **戦略の届く物の全部を変える格子**(同じファイル): 文脈から `gc.get_referents` で歩いて(閉じ込めの cell・既定値・結び付いた方法の `__self__`・入れ物の中身に入る)届く状態の物の全部に、その物の本当の型の**変更の方法の全部**(`list`・`dict`・`set`・`bytearray`・`array` は、その型にあって対になる変わらない型(`tuple`・`frozenset`・`bytes`)に無い方法を機械で列べ、表がそれを尽くすことを試験で確かめる)と、cell の中身の書き換え・消し、関数の `__defaults__`・`__kwdefaults__`・`__dict__` の書き換え、属性と slot の `object.__setattr__`・`object.__delattr__` を、2 つの時機(その呼び出しの中 / 後の呼び出しの中)で当てる。出口の箱は第 9 周の格子の持ち物なので外す。神託(第 9 周の格子と同じ、規則から): 結果・各受け手の記録・配達の列が当てない実行と同じ、または `CoreError`(か戦略自身の呼び出しの失敗)で断り、そこまでの記録が当てない実行の頭と同じ。
   - 列に入れなかった物は試験のファイルの説明に書く。

## C. 監査役・リードの答えのうち作業者に当たるもの(LEAD_DESIGN §8.3)

- 到達性 0 の読み: 「文脈から届く物のうち、核の状態(`_StrategySide` を通らずに届く物)が 0 件」。第 10 周の試験 `test_bt0_r10_strategy_side.py::test_the_strategy_reaches_nothing_of_the_core_s_own_state` のまま。
- 「エンジンは `_StrategySide` の中の物を書くだけで、読むのは箱を 1 度写すときだけ、を試験で固定する」: 上の B-3 の 2 つ目の格子で固定する。**ただし事実を正確に書く**: 核は `_StrategySide` の中の `HistoryLists` が持つ「事象の写しへの参照の列」(`_items`・`_overall_items`)を、落とすときに新しい列を作るために切り出す(`history.py` 160-173 行 `drop`)。この 2 つの列は戦略から届かない(文脈から歩いて届く物に無いことを試験で確かめる)。核がこの列から読むのは参照の並びだけで、写しの中身(属性)は読まない。この周はこの事実を契約と説明に書き、構造は変えない(列を核の側へ移すと核の状態が事象の写しに届き、到達性 0 が崩れる。写しを落とすたびに作り直すと、戦略が持つ事象と列の中の事象が同じ物でなくなる)。この読みでよいかを「リードに聞くこと」に書く。
- 落とした事実の数に上限を付けない: 契約に「1 件 16 バイト」と書く。

## D. i0-r9-04 [示唆]

この周は変えない(LEAD_DESIGN §8.3: 項目 8 の要件を固定するときに決める)。

## E. 直しの途中で見つけた同じ根の箇所(上の §A〜§D はコードを変える前に書いたもの)

| 見つけた形 | なぜ同じ根か | 直した構造 |
|---|---|---|
| `values._now`(送り手の数の変換が失敗したとき)の断りの文が `({type(exc).__name__}: {exc})` で、送り手の変換が投げた例外の `__str__` とメタクラスの `__name__` を走らせる。`__str__` が投げると、断りは `ValueError`(呼び手が自分の誤りの型に包む)にならず、送り手の例外がそのまま出る(契約 `type_decisions`「断りはその入口の誤りの型」を破る) | 外のコードが作った例外を、その class を通して文にする(§B-2 と同じ) | `values.exception_text` を使う(例外の事実だけから作る)。試験: 数を返す差し込み口の方法(プロトコルの戻りの注釈が int / float のもの = 遅延模型の 4 つと費用)× 例外の作り 14 種の格子 `test_a_plug_in_number_whose_conversion_fails_is_refused_by_the_entry_s_error`(70 升目。`Exception` の子は入口の誤り `LatencyModelError` / `CostModelError`、`Exception` でない `BaseException` の子は元のまま出て核は FAILED、どちらも例外のコードは走らない) |
| `engine._VenueLedger.apply` と `engine._take_reports` の「知らない報告の型」の断りの文が `type(report).__module__`・`__qualname__` を普通の属性の読みで取る(約定模型が返した物の class) | 型の名前を普通の属性の読みで取る(§B-2 の 2 つ目) | `values.type_name` を使う |
| `engine._require_protocol`(構築のとき)の断りの文が `type(obj).__name__` で差し込み口の class の名前を読む | 型の名前を普通の属性の読みで取る(§B-2 の 2 つ目) | `values.type_name` を使う |
| 契約・説明の「核は `_StrategySide` を読み返さない(箱だけ)」は、`HistoryLists.drop` が参照の列 `_items`・`_overall_items` を切り出すことと食い違っていた | 事実と違う説明(i0-r9-02 の作業者の試験の説明の誤りと同じ形) | 契約 `channel_payloads.ownership`、`engine.py` の説明と `_StrategySide`、`history.py` の説明を「戦略が届く物のうち読むのは箱だけ。ほかに読むのは戦略から届かない参照の列の並びだけ」に直し、届かないことを試験 `test_the_core_s_own_reference_lists_are_not_reached` で確かめる |
