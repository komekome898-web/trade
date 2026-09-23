# 項目 0「核」第 1 周 作業者の報告(2026-09-23、3 回目の起動)

委任文: `docs/DATA/delegations/20260923_backtest_env_prompt.md`(指紋 `20260923_backtest_env_prompt.md@4ce1be0fa30b`)。§6 の形で書く。
固定した要件: `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md`(変えていない)。場面集: `tests/bt/battery/item_0/`(読んだだけで、変えていない)。

完了の形(オーナー逐語、委任文 §0): 「**このプロジェクトで実施し得る全てのバックテストが可能な汎用バックテスト環境を実現してください。**」「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」

印: 【事実】= この回にコマンドを打って確かめた / 【推定】= コードを読んだうえでの見立てで、実測していない。

## 0. 対応表(CLAUDE.md §0.1)

| やること | オーナーの原文の該当語(逐語) |
|---|---|
| `src/bot/bt/core/` の核を直す(入力の流れの合流・時刻の検査・時刻の範囲の読み出し・口座の口) | 「バックテスト環境を刷新し、信頼できるバックテストが可能な環境を構築してほしい」(委任文 §0 の表の行) |
| 試験を `tests/bt/item_0/` に置き、自分の項目の試験と核の試験を回す | 「非常に厳しい批評家（クリティック）とし、要件を満たせない場合は達成できるまでループを継続させること」(委任文 §0。試験の置き場所は委任文 §3 場面集の規則 7) |
| 外部の道具は入れない | L-406「1.案1」(委任文 §0) |

原文に無い判断をした所は §6「リードに聞くこと」に書いた。

## 1. 変えたファイル

持ち物 `src/bot/bt/core/` と `tests/bt/item_0/` の中だけ。git の commit / push はしていない(ステージもしていない)。

- 変更: `src/bot/bt/core/engine.py` `ordering.py` `api.py` `interfaces.py` `errors.py` `contract.py` `testing.py` `__init__.py`
- 変えていない: `events.py` `time.py` `window.py` `strategy.py`
- 試験の移動(場面集の規則 7「`src/` の下に試験を置かない」): 前の起動の核の試験 11 本 + `_util.py`(`src/bot/bt/core/tests/`、123 件)を `tests/bt/item_0/` へ移した。名前は `test_<名>.py` → `test_bt0_<名>.py`、`_util.py` → `bt0_util.py`、中の `from ._util import` → `from bt0_util import` の 1 行だけ変えた。名前を変えた理由: `tests/test_orders.py` がすでにあり、`tests/` に `__init__.py` が無いので同じ名前の試験ファイルが 2 つあると pytest が読み込みで衝突する【推定: pytest の既定の読み込み方の仕様。衝突そのものは試していない】。`src/bot/bt/core/tests/` は消した(git の上では 12 本の削除と 12 本の新規に見える)。
- 移した試験のうち中身を変えたもの(規則 8「設計を変えたときに書き直してよいが、…理由を報告に書く」): 消した試験は 0 件。
  - `test_bt0_extension_points.py::test_all_four_sockets_are_called_with_outside_implementations` — 口座の口に 2 つの呼び出し(`on_market_event` `check_order`)を足したので、口座が受けた呼び出しの列の期待を `["market", "check_order", "fill"]` に書き直した。
  - `test_bt0_orders.py` の 2 件 — 同じ理由で、口座の記録から約定・資金調達・清算だけを取り出して比べる形にし、呼ばれた順の期待を 1 行足した。
  - `test_bt0_ordering.py::test_rule_is_declared_machine_readably_and_is_total` — 取引所側の優先度を型ごとに分けたので、機械可読の規則の先頭 8 項目の期待を書き直した。
- 持ち物の外(`tests/bt/critic/` `tests/bt/battery/` `pyproject.toml` ほか)は変えていない。

## 2. この周で変えた構造

1. **入力を「名前つきの複数の流れ」として受け、時刻で合流させる**(`engine.py:236` `_SourceMerger`)。前の核は流れを 1 本しか受けず、要件の観点 P0-1 の測り方「事象を型で投入し、投入順ではなく時刻順に処理されるか」を、流れを分けて渡す使い方(約定・板・足・資金調達を別々のファイルから読む)で満たせなかった。今は `CoreEngine(strategy, {"bars": ..., "trades": ..., "funding": ...})` で渡すと、(取引所の時刻, 流れの名前を `sorted()` した順, 流れの中の位置)で合流する。名前の順は `sorted()` なので、辞書の並びを変えても結果は同じ【事実: `test_bt0_streams.py::test_mapping_order_does_not_change_anything` で 6 通りの並びのダイジェストが 1 つ】。1 本の流れの中の逆行は並べ替えずに `EventOrderError` で止める(流れの名前を出す)。流れごとに先読みは 1 件まで。
2. **取引所側でも同時刻の型の順を規則で決める**(`ordering.py:67` `TYPE_ORDER`、`ordering.py:87` `VENUE_MARKET_PRIORITY`)。前の核は、戦略へ届ける順は型で決めていたが、約定の模型(取引所側)が見る順は入力の順のままだった(同時刻の足と約定を逆に入れると、約定の模型が見る順が変わった)。今は両側とも同じ型の順。
3. **待ち行列に入るすべての時刻を 1 か所で int64 ナノ秒として検査する**(`engine.py:366` `_push`)。前の核は、配信の遅れを足した時刻だけ検査を通らず、int64 を超えた時刻を黙って戦略に渡していた(前の起動の批評家の試験 `tests/bt/critic/item_0/test_feed_delay_bypasses_int64_validation.py` が失敗していた【事実: 着手前に `pytest src/bot/bt/core/tests tests/bt` で `2 failed, 131 passed`、そのうち 1 件がこれ】)。根本原因は「検査を事象の作り直しの経路に頼っていた」ことで、配信・発注・取消・通知・タイマーの 5 経路すべてが通る `_push` に検査を移した。
4. **時刻の範囲で履歴を読む口と、未来を求めたら止める型**(`api.py:336` `visible_events(..., since_ns=, until_ns=)`、`api.py:357` `LookAheadError`)。前の核は、未来を読もうとする書き方の多くが「空や短い答え」を黙って返すだけだった。今は `until_ns > now_ns` を実行時の誤りで止める(観点 P0-4 の測り方「未来時刻の事象を読もうとするコードが、実行時エラーか型エラーで止まるか」)。あわせて型ごとの履歴を核が持ち(`engine.py:460` `_deliver`)、`visible_events(型)` が全履歴をなめないようにした。
5. **口座の口に「値洗い」「発注前の拒否」「強制決済の注文」を足した**(`interfaces.py:153` `Account`、`engine.py:530-590`)。前の口座の口は約定・資金調達・清算を受け取るだけで、項目 6 の要件(証拠金・強制決済・評価の損益)を核を書き換えずに差し込めなかった【推定: 項目 6 の要件の行と前の口の形を読んだ判断】。今は、(a) 市場の事象ごとに取引所の時刻で `on_market_event` が呼ばれ(値洗い)、強制の注文を返せる、(b) 戦略の注文が取引所に着いたとき約定の模型より先に `check_order` が呼ばれ、理由を返すと拒否の通知になる。強制の注文は戦略の発注の遅れを通らずにその時刻に約定の模型へ行き、戦略は最初の通知が届いたときに初めてその注文を知る(`api.py:227` `_adopt`、`OrderView.origin == "forced"`)。`forced-` で始まる注文番号は戦略が使えない。

## 3. 試験

- 足した試験: **40 件**(新しい 6 本 = `test_bt0_streams.py` 11・`test_bt0_venue_order.py` 1・`test_bt0_time_window.py` 6・`test_bt0_time_bounds.py` 6・`test_bt0_account_socket.py` 11・`test_bt0_notices.py` 4、既存の `test_bt0_extension_points.py` に 1)。前の起動の 123 件は移しただけ(§1)。計 163 件。
- 自分の項目の試験(= 核の試験): `PYTHONPATH=src python -m pytest tests/bt/item_0` → 末尾 `163 passed in 2.09s`【事実】
- `tests/bt` 全体(前の起動の批評家の試験を含む): `PYTHONPATH=src python -m pytest tests/bt` → 末尾 `1 failed, 172 passed in 2.57s`【事実】。落ちた 1 件は `tests/bt/critic/item_0/test_liquidation_has_no_account_hook.py::LiquidationReachesAccountTest::test_engine_notifies_the_account_of_a_liquidation_event` で、試験自身の誤り(規則 8 により変えていない。§5 の 1)。着手前は同じ範囲で `2 failed` だった(もう 1 件の int64 の試験は §2 の 3 で通るようになった)。
- 全試験(`PYTHONPATH=src python -m pytest`): 12:40:34 に切り離して開始(記録 `<scratchpad>/bt/pytest_item0_r1_worker_full.log`)、末尾 `1 failed, 3048 passed, 4 skipped, 1 warning in 769.19s (0:12:49)`【事実】。落ちた 1 件は上と同じ批評家の試験(試験自身の誤り、§5 の 1)だけ。`src/bot/bt/` は他のどこからも import されていない【事実: `grep -rn "bot\.bt\b\|bot/bt\|from bot.bt\|import bot.bt" --include=*.py src scripts tests` で `src/bot/bt/` と `tests/bt/` 以外の当たりなし】。
- 場面集の自己確認(資料係の表ではない): `tests/bt/battery/item_0/run_battery.py --target new_impl` を変えた核に対して回した【事実】: `一致=26, 対応なし=2, 不一致(値)=0, 結果なし=0; 再現(2回の実行で不一致)=0`(着手前と同じ)。対応なしの 2 件は `v2-order_notice-cap/known` で、資料係の adapter(`tests/bt/battery/item_0/adapters/new_impl_stub.py`)が通知をデータ源から投入しようとして `not_supported` を返している(§6 の 1)。試金石 `--target mutant` は `不一致(値)=1`(観点 4 の先読みの漏れを検出)。記録は `<scratchpad>/bt/item0_r1_worker_battery_after.tsv` と `..._mutant.tsv`。

## 4. 要件の各行を満たした根拠

### 4.1 委任文 §2 の項目 0 の行

| 要件 | 根拠(ファイル:行) | 試験 |
|---|---|---|
| 時刻は UTC の int64 ナノ秒 | 全事象の時刻は `time.py:74` `validate_nanos` を通る int。待ち行列に入る時刻(遅れを足した時刻・タイマー)も `engine.py:366` `_push` で同じ検査を通る。ISO はナノ秒まで自前で解析(`time.py:152`)。機械可読の契約 `time.py:54` `TIME_CONTRACT` | `test_bt0_time.py` 18、`test_bt0_time_bounds.py` 6 |
| 事象の型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知) | `events.py:44` `EventType` に 12 種(8 分類 + 通知を 受付/拒否/約定/取消済み/状態不明 に分けた)。通知は約定の模型の答えから核が作る(`engine.py` `_handle_reports`) | `test_bt0_events.py` 35、`test_bt0_notices.py` 4(発注して届いた通知の中身を、先に決めた値と比べる) |
| 戦略は「受け取れた時刻 ≤ 今」の事象しか見られない(構造で) | 履歴は「もう届けた事象」の列だけ(`engine.py:460` `_deliver`)。発注の口は取引所ではなく `_OrderPort`。文脈は呼び出しが終わると失効(`api.py:304` `_revoke`、型ごとの履歴も失効)。未来を求める読み出しは `LookAheadError`(`api.py:357`)。入力の流れは 1 本あたり先読み 1 件まで(`engine.py:236`) | `test_bt0_lookahead.py` 11、`test_bt0_time_window.py` 6、`test_bt0_streams.py::test_each_stream_is_pulled_lazily_one_ahead_at_most` |
| 決定的な事象の順序(同時刻の並びの規則を明記) | `ordering.py:1-58`(規則の文)、`ordering.py:67` `TYPE_ORDER`、`ordering.py:112` `ORDERING_RULE`(機械可読、合流の規則 `source_merge` を含む)。鍵 (時刻, 優先度, 通し番号) は全順序 | `test_bt0_ordering.py` 5、`test_bt0_venue_order.py` 1、`test_bt0_streams.py` 11、`test_bt0_determinism.py` 7 |
| 戦略の API(事象ごとの呼び出し・発注・取消) | `strategy.py:12` `on_event`、`api.py:408` `place_order`、`api.py:414` `cancel_order`、`api.py:431` `STRATEGY_API` | `test_bt0_api_surface.py` 2、`test_bt0_orders.py` 20 |
| 他項目が差し込む口(約定模型・遅延模型・費用・口座) | `interfaces.py:106` `FillModel`、`:126` `LatencyModel`、`:146` `CostModel`、`:153` `Account`(値洗い・発注前の拒否・強制決済を含む)。欠けた口は構築時に拒否。費用の模型を渡さずに約定が起きたら `MissingCostModelError` | `test_bt0_extension_points.py` 7、`test_bt0_account_socket.py` 11、`test_bt0_latency.py` 11 |

### 4.2 比較の観点(REQUIREMENTS.md §2)

| 観点 | 根拠 |
|---|---|
| P0-1 事象駆動・投入順ではなく時刻順 | §2 の 1。`test_bt0_streams.py::test_streams_are_processed_in_time_order_not_handing_order`(遅い時刻の流れを先に渡しても、届く時刻の列が手計算の [30, 45, 60, 90, 120] 秒になる) |
| P0-2 UTC の int64 ナノ秒 | 上表 1 行目。全経路の時刻の検査は §2 の 3 |
| P0-3 8 種の事象型 | 上表 2 行目。通知は場面集の規則 2(「データ源から入るか内部で作るかを問わず、戦略に届いたか・中身が正しいかで見る」)の形で試験した(`test_bt0_notices.py`: 場面 v2-order_notice と同じ時刻 1700000000123456789・同じ番号 `synthetic-1` で発注し、届いた受付の通知の中身が一致) |
| P0-4 ルックアヘッドの構造的な禁止 | 上表 3 行目。未来を求める読み出しは実行時の誤りで止まる(§2 の 4) |
| P0-5 同時刻の決定的な順序 | 上表 4 行目。戦略側と取引所側の両方(§2 の 2) |
| P0-6 戦略 API | 上表 5 行目 |
| P0-7 差し込み口 | 上表 6 行目。口座の口の拡張は §2 の 5 |

## 5. 満たせなかった行・限界

1. **批評家の試験 1 件が、試験自身の誤りで落ちる(規則 8 により変えていない)**: `tests/bt/critic/item_0/test_liquidation_has_no_account_hook.py::LiquidationReachesAccountTest::test_engine_notifies_the_account_of_a_liquidation_event`。理由は 2 つ【事実: `<scratchpad>/bt/item0_r1_worker_liq_check.py` と `.log`】: (a) 69 行で `side="long"` を使うが、核の清算の事象は取引所が出す清算の注文の向き(`buy`/`sell`)だけを受け、`long` は推測で置き換えずに `EventValidationError` にする。(b) 試験の中の `_RecordingAccount`(43〜53 行、`apply_fill` と `apply_funding` だけ)に `apply_liquidation`(と今周足した `on_market_event` `check_order`)が無く、核は構築時に `TypeError: account OldShape lacks ['apply_liquidation', 'on_market_event', 'check_order']` で拒否する。この 2 つを直した写しでは、清算の事象 1 件で `apply_liquidation` が 1 回呼ばれる(同じ記録)。同じファイルのもう 1 件 `test_account_protocol_has_a_liquidation_hook` は通る。
2. **Python の言語の性質による限界(場面にしていない)**: 戦略の関数が `gc.get_referrers` などで実行中のオブジェクトを総当たりすれば、核の待ち行列(未来の事象を含む)に届く【推定: 言語の性質。試していない】。核が防いでいるのは「文脈から参照をたどって届く」経路まで(`test_bt0_lookahead.py` の `_Snoop` が非公開の属性・束縛先・入れ物を全部たどって確かめる)。戦略の作者が入力の列そのものを戦略に渡せば、それは読める(どのエンジンでも同じ)【推定】。
3. 既定の妥当範囲(1970〜2100 年)では「秒をナノ秒と取り違えた」向き(値が小さすぎる向き)は捕まらない。`to_nanos(..., plausible=(下限, 上限))` で範囲を渡せば捕まる(`test_bt0_time.py::test_value_too_small_for_its_label_needs_an_era_window`)。データ層(項目 1)で源ごとに範囲を渡す前提。
4. 同じ流れの中で同じ型・同じ時刻の事象は、流れの中の順で並ぶ(例: 同じナノ秒の 2 つの約定の印字順)。これは入力の書き方に依る唯一の並びで、`ordering.py` の説明に明記した。
5. `testing.py` の `ImmediateFillModel` などは試験用の代役で、どの取引所の模型でもない(冒頭に明記)。
6. 外部の道具: 入れていない。ネットワークも使っていない。

## 6. リードに聞くこと

1. 資料係の adapter `tests/bt/battery/item_0/adapters/new_impl_stub.py` の `_scene_v2_generic_cap/known`(`order_notice` の 2 場面)は、通知を `OrderAckEvent` としてデータ源から投入しようとし、核がデータ源からの通知を受けないので `not_supported`(表では「対応なし」)を返す。場面集の規則 2 は「注文の通知は、データ源から入るか内部で作るかを問わず、戦略に届いたか・中身が正しいかで見る」としているので、この adapter は規則 2 に合っていないと読む。核の側で「データ源から通知を受ける」形を足すのは、場面に合わせた特別扱いになり、かつ注文の台帳(届いていない注文への約定などを拒む検算)を迂回する口になるので、していない(記録された取引所の答えを再生したいときは、約定の模型の口に「記録を返す模型」を差せば台帳の検算を通る)。発注して届いた通知の中身が場面の期待と一致することは `tests/bt/item_0/test_bt0_notices.py::test_accepted_notice_known_answer` で確かめた。adapter を直すのは資料係の持ち物なので、扱いを決めてほしい。
2. 口座の口に `on_market_event`(値洗いと強制の注文)と `check_order`(発注前の拒否)を足したのは、要件の行「他項目が差し込む口(…口座)」を、項目 6 の行(証拠金・レバレッジ・強制決済・評価の損益)が核を書き換えずに差し込めることまで含むと読んだため。この読みは委任文の逐語には無い(要件の行は口の名前だけ)。口を増やしたので、口座を差す実装は 5 つの呼び出しを全部持たないと構築時に拒否される。
3. 試験を `src/bot/bt/core/tests/` から `tests/bt/item_0/` へ移し、ファイル名に `bt0_` を足した(§1)。規則 7 に合わせた移動で、消した試験は 0 件。
