# 批評家の記録(項目 0「核」、第 9 周。新しく起こされた批評家)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(指紋 `9ef8d697ad0a`。`sha256sum … | cut -c1-12` で確かめた。全 164 行を読んだ)。
合意した完了の形(委任文 §0 の逐語): 「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」
手元に置いたもの: 固定した要件 `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md`(§1 の行・§2 の P0-1〜P0-7・§3 の調査結果の行)、場面集 `tests/bt/battery/item_0/DEFINITIONS.md`、作業者の根本原因 `round_9/ROOTCAUSE.md`、リードの設計 `round_7/LEAD_DESIGN.md`(§3・§7。§7.4 はこの周の作業者の返り値の後に書かれた = コミット `04e3088`、18:17 UTC)、第 8 周の `CRITIC.md`。
`<S>` = `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt`。行番号は作業木(コミット `5092565` + 作業者の未コミットの変更)のもの。

## 指摘

この周の [止める] は 0 件。以下は全部 [直す] と [示唆](格付けの理由は各指摘と末尾の吟味の表)。

### i0-r9-01 [直す](相手: 実装、repeat_of: null)

**`history_limit` の下で、答えの全部が保たれている読み出しを `HistoryTruncatedError` で断り、その理由の文が事実と違う。**`StrategyContext.__refuse_truncated`(`api.py` 777-799 行)は、型ごとに「最後に落とした事象」の (配達の番号, 受け取った時刻) しか持たず、`until_ns` を見ない。そのため、ある型の落とした部分が `until_ns` より後にだけあるときも、全体(`event_type=None`)の読み出しを断る。断る文は「reaches into the FUNDING history dropped by history_limit」と言い、「since_ns を … より後にするか n を小さくせよ」と勧めるが、読み出しは落とした部分に届いておらず、勧めのどちらでもその答えは得られない(`since_ns` を上げれば答えから保たれた事象が外れる)。空の答えでも同じで、`until_ns` が全部の事象より前の読み出しを断る。契約 `CORE_CONTRACT["visibility"]["history_limit"]`(`contract.py` 81-85 行)は空の答えを断るのを「until_ns cut lies among the dropped events」のときと書くが、全部より前は「落とした事象の間」ではない。

黙って誤った値は返していない(下の神託で 0 件)ので [止める] の基準には当たらない。ただし、事実と違う断りの文と、契約の文と振る舞いの食い違い = [直す]。落とした部分の最初の受け取った時刻(または型ごとの落とした範囲)を核の記録に持てば、`until_ns` で判定できる。

根拠:
- 最小の再現 `<S>/item0_r9_critic_probe_history_until.py`(`history_limit=1`。足 2 件 @1s・2s、資金調達 3 件 @5s・6s・7s。資金調達は 5s・6s を落とし 7s を保つ。足は 2 件とも保つ)→ 5 件目の呼び出しで:
  - `until_ns=T0+3s -> HistoryTruncatedError: visible_events(event_type=None, since_ns=None, n=None) reaches into the FUNDING history dropped by history_limit (last dropped: delivery #4 received at 17000000…`(制限なしの同じ読み出しは `[1, 2] place (0, 1, 5, 0)`。1・2 は保たれている)
  - `n=1, until_ns=T0+3s -> HistoryTruncatedError: …`(制限なしは `[2]`)
  - `until_ns=T0 (before every event) -> HistoryTruncatedError: …`(制限なしは `[]`)
  (`<S>/item0_r9_critic_probe_history_until.out`)
- 独立の神託 `<S>/item0_r9_critic_probe_history_oracle.py`(規則の文だけから作った。3 型・同時刻あり・N ∈ {1,2,3}・種 1〜80、呼び出しごとに event_type × n × since × until の読み出し)→ `{'ok': 320366, 'wrong': 0, 'silent_short': 0, 'over_refused': 55305, 'place_wrong': 0, 'over_refused_nonempty': 1398, 'over_refused_empty': 53907}`(`<S>/item0_r9_critic_probe_history_oracle.out`)。「over_refused」= 制限なしの答えの全部が保たれているのに断った数。
- 同じ神託のうち誤りの 3 種(黙って短い・誤った答え・誤った place)を試験に固定した(通る): `tests/bt/critic/item_0/test_i0r9_history_limit_read_oracle.py` → `PYTHONPATH=src python -m pytest tests/bt/critic/item_0/test_i0r9_history_limit_read_oracle.py -p no:cacheprovider` → `12 passed`。断りすぎはこの試験では見ない(試験の説明に書いた)。

### i0-r9-02 [直す](相手: 実装、repeat_of: i0-r8-01)

**戦略が届く物を変える道のうち、作業者の到達性の試験が列に入れていない 2 つの道があり、その 1 つで核は戦略のコードを `on_event` の外で走らせる。**族は i0-r8-01(核が、戦略が API を通さずに変えられる物に後で触れる)と同じ。ただし、どちらの道でも核の判断・送る物・結果・配達の要約は変わらない(下の根拠で確かめた)ので [直す] とした。

(a) **`__class__` の代入**: 注文の口(`_OrderPort`)は `__slots__` を持つ普通の class の物なので、同じ形の子 class への `__class__` の代入が通る。作業者の敵対者の試験は列の外の理由を「the core's objects are slotted or built-in」と書く(`tests/bt/item_0/test_bt0_r9_reachable_state_adversary.py` 62 行)が、これは事実と違う。核は配達のたびに `port._now = renew(time_ns)`(`engine.py` 925 行)と、口の class を通して書くので、戦略が置いた `__setattr__` が `on_event` の外(配達の途中、`on_event` の前)で走る。そこで例外を投げると、戦略の呼び出しの外で実行が FAILED になる。

(b) **関数の閉じ込め**: 核が作り、実行の間ずっと持ち、書き続ける物(出口の箱 `engine._box`、写しの台帳 `engine._shown`、注文の口 `engine._port`、履歴の列 `history.overall`・`history.typed[...]`)は、文脈の関数の閉じ込め(結び付いた方法の `__self__`・cell の中身)をたどると届く。作業者の構造の試験は、関数に入らないもの(`test_bt0_r9_context_graph.py` 7 行)と、核の状態を属性の名前の一覧で選び `_box`・`_shown`・`_port`・`_history` の列を入れないもの(`test_bt0_r9_reachable_state_adversary.py` 883-889 行)の 2 本で、「閉じ込めを通して届く核の物」を測る試験が無い。リードの設計 §3.4 は「同じ根の探しは、属性の名前の一覧ではなく上の到達性の出力で行う」とし、核の変わりうる物に「台帳・箱・列」を挙げている。§7.4 の 20(作業者の返り値の後、18:20 UTC)は「出口の箱は**戦略の側の物**であり(核の物への参照ではない)…が到達性の試験に入っていること。箱が核の物なら §3.4 に反する」と書くが、今の箱は `engine._box is port._outbox`(`engine.py` 696-697 行で核が作り、999 行で核が `list.clear` する)で、その条件は試験に入っていない。§7.4 は返り値の後に出たので、この周の作業者の落ち度ではなく、次の周で直す物として挙げる(第 8 周の i0-r8-03 と同じ扱い)。

核の判断に届かないことは確かめた: 台帳 `engine._shown` に偽の FILLED の見え方を書いても結果の `orders` は `[('real', 'OPEN', 0.0)]`、箱に強制注文の頭の id の注文を入れると `OrderApiError` で断る、戦略が見え方を `object.__setattr__` で変えても結果は変わらない。

根拠:
- `<S>/item0_r9_critic_probe_port_class_swap.py` → `port class now: Hook` / `('_now', 1700000001000000000, 'OUTSIDE on_event')` / `('_now', 1700000002000000000, 'OUTSIDE on_event')` / `run raised: builtins RuntimeError strategy code raised inside the core`(`<S>/item0_r9_critic_probe_port_class_swap.out`)。
- `<S>/item0_r9_critic_probe_closure_reach.py` → `enter functions=False: reached 25 objects; engine objects reached: []` / `enter functions=True: reached 78 objects; engine objects reached: ['engine._box', 'engine._port', 'engine._shown', 'history.overall', 'history.typed[ORDER_ACK]', 'history.typed[TRADE]']`(`<S>/item0_r9_critic_probe_closure_reach.out`)。
- `<S>/item0_r9_critic_recheck_r8_registry.py` → `ghost: orders [('real', 'OPEN', 0.0)] requests ['real'] venue {'real': 'LIVE'}` / `forced: refused OrderApiError: client_order_id 'forced-1': the prefix 'forced-' is reserved …` / `view: orders [('real', 'OPEN', 0.0)] …`(`<S>/item0_r9_critic_recheck_r8_registry.out`)。

### i0-r9-03 [直す](相手: 場面集、repeat_of: null)

**場面集の定義に「未決」の升目が残っている。**リードの答え `LEAD_DESIGN.md` §7.3 の 15(16:15 UTC、コミット `792a22a`)は「「未決」という語は消す。…測り方の文が名指さない升目は「場面にしていない側面」に、理由「固定した測り方の外(要件は 1 周目の前に固定し、周の途中で広げない…)」で入れる」と決めたが、`DEFINITIONS.md` は答えの前(15:13 UTC、`d99ad78`)の版のままで、升目の判定に「未決(リードに上げた)」を持つ。審査員は `DEFINITIONS.md` を読むので、決まった範囲の外の升目が「決まっていない」と読める。書き出す側(`gen_definitions.py` 71・79・81 行、`grid_c.py` 16・119 行)も「未決」を判定の値に持つ。測る場面そのものは変わらないので [直す]。

根拠: `grep -c "未決" tests/bt/battery/item_0/DEFINITIONS.md` → `402`。`grep -n "未決" …` → 85 行(判定の説明)・92 行「P0-1(升目 40: 場面にした 6 / 場面にしない 12 / 未決 22)」・101 行ほか。`git log -1 --format='%h %ci' -- tests/bt/battery/item_0/DEFINITIONS.md` → `d99ad78 2026-09-24 15:13:01`、`git log --format='%h %ci %s' -- …/LEAD_DESIGN.md` → `792a22a 2026-09-24 16:13:23 Lead answers to the r8-1 battery audit questions …`。

### i0-r9-04 [示唆](相手: 実装、repeat_of: null)

**`OrderRequest.extra` の集合(`set`・`frozenset`)は、核が作り直した `FrozenSet`/`frozenset` の反復の順が `PYTHONHASHSEED` で変わる。**核の配達の要約(`delivery_digest`)と、集合を含まない結果は、種 0〜3 の全部で同じだった。集合の反復の順を読む取引所の模型を差し込むと、別の process での 2 回の実行が違いうる。項目 8(再現性)が実行記録に `PYTHONHASHSEED` を固定して残すか、核が集合を決まった順で持つかを、後の項目の要件を固定するときに決めるとよい。

根拠: `<S>/item0_r9_critic_probe_hashseed.py` を `PYTHONHASHSEED=0..3` で → `digest 04f770d4168a555b` は 4 回とも同じ、集合の repr を含む記録の要約は `63e4a7bc482289f0` / `e34ec07a0b3d00ac` / `d8f2388918cf7dab` / `d1bb2c0bbc51299e`。集合の repr を除いた版 `<S>/item0_r9_critic_probe_hashseed_noset.py` → 4 回とも `6ac13199751bcd56`(`<S>/item0_r9_critic_probe_hashseed.out`・`…_noset.out`)。

## 前の周の指摘の直りを確かめた記録(直ったものは上に挙げない)

| 前の指摘 | 確かめたこと(コマンドと出力) | 結論 |
|---|---|---|
| i0-r8-01(注文の口の台帳と箱を戦略が API の外から書き換えられ、核がそれを信じる) | 批評家の試験 `test_i0r8_order_port_state_written_around_api.py` は通る(下の全件の実行に含む)。第 8 周の試しは口を `__self__` で探していて今の作りでは口に届かない(`AttributeError: 'function' object has no attribute '__self__'`)ので、閉じ込めを歩いて口を見つける形に書き直した `<S>/item0_r9_critic_recheck_r8_registry.py` → 偽の台帳の注文 `ghost` は結果に載らない(`orders [('real', 'OPEN', 0.0)]`)、強制注文の頭の id の箱の項目は `OrderApiError` で断る、見え方の書き換えは結果に届かない。第 8 周の試し `item0_r8_critic_probe_orderview_shared.py` → `same object as open_orders()[0]: False` / `result orders['a']: filled_size 0.0 venue_order_id ''` | 直った(同じ族の別の道 = i0-r9-02。核の判断には届かない) |
| i0-r8-02(`DeliveredList` の `__init__` と `dropped` の代入を断っていない) | 第 8 周の試し `item0_r8_critic_probe_deliveredlist_change.py` → `append -> AttributeError` / `__setitem__ -> AttributeError` / `__init__ -> TypeError` / `dropped = -> AttributeError` / `visible_events() after: [0, 1, 2]`(3 件とも見える) | 直った |
| i0-r8-03(`[-k:]` の代わりが `visible_events(n=k)` であることが契約に無い) | `contract.py` の `position_rule.last_k`(55-60 行)と `visible_events` の説明(`api.py`)に書かれている。作業者の試験 `test_bt0_r9_history_owner.py` の `test_the_contract_says_how_to_read_the_last_k_events`・`test_the_last_k_reads_as_the_contract_says` が通る | 直った |
| i0-r7-01(後ろ向きの答えの負の区間の境界) | 批評家の試験 `test_i0r7_backward_answer_negative_bounds.py` は通る。第 8 周の神託 `item0_r8_critic_probe_semantic_oracle.py` を今の作業木で打ち直した → `seed 1 {'n': 131520, 'SILENT': 0, 'WRONG': 0, 'UNDER': 0, 'IDX_SILENT': 0}` | 直ったまま |
| i0-r7-02(`extra` の Fraction が生きたまま路を渡る) | 批評家の試験 `test_i0r7_fraction_in_extra_stays_live.py` は通る | 直ったまま |
| i0-r7-03(LEAN の再現の購読の組の根拠) | 場面集は第 8 周から変わっていない(`git log -3 -- tests/bt/battery/item_0` の最後は `b6b2263`、資料係の指紋も第 8 周と同じ `d0cb71be…`)。`repro_lean52.py` 30・32・40 行が `AddCryptoFuture` → `LookupSubscriptionConfigDataTypes` の経路を注釈に持つ | 直ったまま |
| i0-r7-04(検討表 15 行の古い前提) | `sed -n 15p opponents/CONSIDERED.md` → 「含む側に引けるもの」の段落で、「資金調達か清算を含む」の文は無い | 直ったまま |
| i0-r7-05(通知の「受け取れた時刻 ≤ 今」の場面が無い) | リードの答え §7 の 2 で「場面にしない」。付け直しの見直しは下 | リードの決定で閉じたまま |

### 付け直しの見直し(前の周の [直す]・[示唆])

前の周の [直す] は i0-r8-02・i0-r8-03 で、どちらも直った。i0-r7-05 は第 8 周の批評家と同じ理由で付け直さない(新実装そのものは通知でも行を満たし、欠けは固定した測り方の外。要件の範囲を変えるのはオーナーだけ)。

### 規則 8(作業者が「試験自身の誤り」と報告した批評家の試験)

この周の作業者の返り値(REPORT)は、この記録を書いた時点で `round_9/` に書き出されていない。作業者の根本原因 `round_9/ROOTCAUSE.md` の E 節が挙げる試験の書き直しは作業者自身の試験 4 本(`ctx._StrategyContext__place_order_cb.__self__`・`win._log` で届いていたもの)と第 8 周の自分の試験の 1 行で、批評家の試験を「誤り」とした記述は無い。前の周までの批評家の試験は全部通る: `PYTHONPATH=src python -m pytest tests/bt/item_0 tests/bt/critic/item_0 -p no:cacheprovider` → `1158 passed, 2 skipped in 272.92s`(この周の私の試験を足す前)。取り下げる試験は無い。

## 場面集の側で見たこと

- 場面集の試験: `PYTHONPATH=src python -m pytest tests/bt/battery/item_0 -p no:cacheprovider` → `75 passed in 23.63s`(`<S>/pytest_item0_r9_critic_battery.log`)。検討表の機械の検め: `python3 scripts/check_bt_considered.py tests/bt/battery/item_0/opponents/CONSIDERED.md` → `OK 誤り 0 件`。
- **リードの答え §7.3 の 16 (a)(検討表の「スキップ(上位互換)」から 3 行を番号の小さい順に選び、含む側の機構の行を自分で読む)**: 第 8 周の記録にこの確かめが無いので、この周を最初として番号の小さい順の 3 行を選んだ: 11 OctoBot(P0-3)・11 OctoBot(P0-5)・13 DeviaVir/zenbot(P0-1)。読んだのは、資料係の venv に入っている配布物のコード(`<S>/venvs/item_0/…`)。
  - 11 OctoBot(P0-3): 行が引く OctoBot の側の行は実在する(`octobot_trading/exchange_data/__init__.py` 126 行 `UNAUTHENTICATED_UPDATER_SIMULATOR_PRODUCERS = {`、146 行の資金調達の注釈「only hard coded value for now」、清算は検証で流す物の一覧に無い = 同じファイルの 126-135 行と `grep -rn "Liquidation\|LIQUIDATION" octobot_trading` の当たりが定数・websocket の feed・建玉の計算だけ)。「在る」とした能力の含む側: barter-rs の p3-trade・p3-book_snapshot、Basana の p3-bar・p3-clock-timer・p3-notice-* は `survey_results/opp_barter.tsv`・`opp_basana.tsv` で「正解と一致」。Basana の `subscribe_to_order_events`(`basana/backtesting/exchange.py` 360 行)・`schedule`(`basana/core/dispatcher/base.py` 195 行)は実在する。含むは成り立つ。
  - 11 OctoBot(P0-5): 含む側の Basana の source の `priority`(`basana/core/event.py` 88-101 行)と dispatcher の `heapq.heappush(self._event_heap, (event.when, -source.priority, id(source), source, event))`(`base.py` 92 行)は実在し、`opp_basana.tsv` の p5-same-time-twice・p5-hand-over-order は「正解と一致」。priority は公開の引数で、利用者がコードを書き足すものではない(検討表 15 行の「含む側に引けるもの」に合う)。含むは成り立つ。
  - 13 DeviaVir/zenbot(P0-1): 能 1・2 の含む側の Basana(`EventMultiplexer` `base.py` 47-61 行、`subscribe` 155 行、`BarEvent` `bar.py` 85 行)は実在し、`opp_basana.tsv` の p1-* は 3 場面とも「正解と一致」。能 3(受けた約定の束を時刻で並べ直す)の含む側 hftbacktest の `correct_event_order`(`hftbacktest/data/validation.py` 54 行)は実在し、事象の列を時刻で並べ直す関数で、`opp_hftbacktest.tsv` の p4-received-time は「正解と一致」。含むは成り立つ。
  - 次の周の批評家は、番号の順で次の 3 行(13 DeviaVir/zenbot(P0-6)・13(P0-7)・38 microsoft/MarS(P0-7))を読む。
- 資料係の表: 6 枚の組の 2 通りは 3 組とも違う(`materials/md5sum_pairs.txt`: current・survey・mutant とも `differ`)。場面集の指紋は第 8 周と同じで、調査結果の側の結果を第 8 周から写した(`materials/commands.txt`、L-435 の規則どおり)。表の注記に「型の組は対象の持つ型から規則で決めた」がある。新実装の行は 32 / 32 が「正解と一致」。
- adapter の公平さ: 場面集(adapter を含む)は第 8 周から変わっていない。第 8 周の批評家の読み(新実装の adapter が約定の模型に場面集の側のダミーを渡すのは公開の差し込み口の範囲で、表の勝敗を決めていない)を、`survey_best.tsv` の P0-6 の 3 場面が全部「正解と一致」(`opp_aat`)であることで確かめ直した。
- 覆い: 固定した要件 §2 の P0-1〜P0-7 の全観点に値の場面が 1 つ以上ある(表の観点ごとの場面の並び)。升目の「未決」は i0-r9-03。

## 構造の変化

前の周から構造は変わった(`structural_change_since_prev = true`)。コードで確かめたもの: 戦略の注文の事実の持ち主が核の台帳 `_OrderBook` になった(`api.py` 428-462 行。文脈から届かない。`<S>/item0_r9_critic_probe_closure_reach.out` の届いた核の物の一覧に台帳が無い)/ 出口の箱を核が自分の参照で 1 度読み、API の規則を核の台帳と時刻に当て直す(`engine.py` 976-1050 行 `_drain`・`_take_message`)/ 文脈と窓は `__slots__` と代入を断る形になり、取り消しはエンジンの閉じ込めた変数 `_alive_switch`(`engine.py` 357-372 行)/ 履歴の保ち方は核の記録(`history.py` 127-205 行 `DeliveredHistory` の `_facts`・`_overall_facts`)から決める / `DeliveredList` は入口で変更を断る(`history.py` 57-124 行)。

## 提出前の吟味(批評家の文: 指摘ごとに根拠を自分で再現し、格付けを基準に照らし、前の周の指摘の直りを自分で確かめ、相手の付け違いが無いか確かめる)

| 指摘 | 根拠を自分で再現したか | 格付けを基準に照らした結果 | 相手 |
|---|---|---|---|
| i0-r9-01 | 最小の再現と神託を打ち、出力を上に逐語で写した。神託の最初の版は自分の誤り(`a[len(a)-n:]` が n > len で負の添字になる)で 3,355 件の「誤り」を出したので、直して打ち直した(直した後は 0 件) | 黙って誤った値は 0 件(神託 320,366 件の答え)で、未来も見えない。断りすぎは「対応なし」側で、固定した要件の行・観点・場面の正解のどれにも当たらない。事実と違う断りの文と契約の文の食い違い = [直す] | 実装(`src/bot/bt/core/api.py`・`contract.py`) |
| i0-r9-02 | 試し 3 本を打ち、出力を上に写した | 戦略のコードが `on_event` の外で走るが、そこで得るものは同じ配達の `on_event` と同じで、核の判断・送る物・結果・配達の要約は変わらない(第 8 周の攻めを打ち直して確かめた)。[止める] の基準(要件・正解・試験・信頼性と再現性・場当たり・§4・場面集の規則)のどれにも当たらない。試験の列の外の理由が事実と違うこと、リードの §7.4 の 20 の条件が試験に無いこと = [直す]。族は i0-r8-01 と同じ機構(核が、戦略が変えられる物に後で触れる)なので repeat_of を i0-r8-01 とした | 実装(`engine.py`・作業者の試験) |
| i0-r9-03 | `grep -c` と `git log` を打った | 測る場面・正解・表は変わらない。リードの決定の未適用で、審査員の読む文書の語の誤り = [直す] | 場面集(`tests/bt/battery/item_0/`) |
| i0-r9-04 | 種 0〜3 で 2 本の試しを打った | 核の要約と集合を含まない結果は同じ。要件の外の改善案 = [示唆] | 実装 |

場当たりの直し(試験だけの特別扱い・閾値や既定値をずらす・文言合わせ・機能を外す)は見つからなかった。作業者の構造の試験が核の状態を名前の一覧で選び、箱・写しの台帳・履歴の列を入れていないこと(i0-r9-02 (b))は、作業者の設計(契約がこれらを「戦略の物」と定める)に沿った選び方で、試験を通すための除外とは読まなかったが、リードの §7.4 の 20 と合わせて次の周に直す物とした。

この周に足した批評家の試験: `tests/bt/critic/item_0/test_i0r9_history_limit_read_oracle.py`(12 件、通る)。
