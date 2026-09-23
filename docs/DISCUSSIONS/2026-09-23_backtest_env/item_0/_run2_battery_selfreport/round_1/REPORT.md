# 項目 0「核」第 1 周 作業者の報告(2026-09-23)

委任文 `docs/DATA/delegations/20260923_backtest_env_prompt.md`(指紋 `20260923_backtest_env_prompt.md@c4d453ab0b09`)§6 の形で書く。
固定した要件: `docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/REQUIREMENTS.md`(変えていない)。場面集 `tests/bt/battery/item_0/`(読んだだけで、変えていない)。

完了の形(オーナー逐語、委任文 §0): 「**このプロジェクトで実施し得る全てのバックテストが可能な汎用バックテスト環境を実現してください。**」「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」

印: 【事実】= この回にコマンドを打って確かめた / 【推定】= コードを読んだうえでの見立てで、実測していない。

## 0. 対応表(CLAUDE.md §0.1)

| やること | オーナーの原文の該当語(逐語) |
|---|---|
| `src/bot/bt/core/` の核を作り直す(事象の型・時刻・順序・戦略の API・差し込み口) | 「バックテスト環境を刷新し、信頼できるバックテストが可能な環境を構築してほしい」(委任文 §0 の表の行) |
| 試験を書き、自分の項目の試験と核の試験を回す | 「非常に厳しい批評家（クリティック）とし、要件を満たせない場合は達成できるまでループを継続させること」(委任文 §0。試験を書くのは作業者の役として委任文 §3 が定める) |
| 状態不明 `STATE_UNKNOWN` を保持し自動で再送しない形を核の型に入れる | 「思いつく限りのあらゆる要素に至るまで」(委任文 §0 の表の異常系の行) |
| 外部の道具は入れない | L-406「1.案1」(委任文 §0) |

原文に無い判断をした所は §5「リードに聞くこと」に書いた。

## 1. 変えたファイル(すべて持ち物 `src/bot/bt/core/` の中)

- 書き直し: `__init__.py` `api.py` `engine.py` `events.py` `interfaces.py` `strategy.py` `time.py` `window.py`
- 新規: `errors.py` `ordering.py` `contract.py` `testing.py`
- 削除: `clock.py`(`ordering.py` に置き換え)
- 試験(`src/bot/bt/core/tests/`): 前の実行の 7 本(69 件)を置き換えた(`test_api_coupling.py` `test_clock.py` `test_engine_integration.py` の 3 本は削除、`test_time.py` `test_events.py` `test_lookahead.py` `test_extension_points.py` の 4 本は同じ名前で中身を書き直し)。今ある試験は次の 11 本 + `_util.py`:`test_time.py` `test_events.py` `test_ordering.py` `test_lookahead.py` `test_orders.py` `test_latency.py` `test_extension_points.py` `test_engine_source.py` `test_api_surface.py` `test_determinism.py` `test_contract.py`

持ち物の外(`tests/bt/critic/` `tests/bt/battery/` `pyproject.toml` ほか)は変えていない。git の commit / push はしていない(ステージもしていない)。

## 2. この周で変えた構造

1. **1 本の待ち行列による離散事象の模擬に変えた**(`engine.py:222` `CoreEngine`)。前の核は事象を全部並べてから 1 本ずつ戦略に渡すだけで、遅延の口(`delay_ns`)は呼ぶが結果を使わず、発注は記録するだけで受付・約定・取消の通知が 1 件も生まれなかった【事実: HEAD の `engine.py` の旧 90〜135 行】。今は「取引所側に市場の事象が届く(`exchange_time_ns`)」「戦略に事象が届く(`received_time_ns` + 配信の遅れ)」「注文・取消が取引所に届く(送信 + 発注の遅れ)」「取引所の答えが戦略に届く(取引所の時刻 + 通知の遅れ)」「タイマー」を同じ待ち行列に入れ、`(時刻, 優先度, 通し番号)` の全順序で処理する(`ordering.py:1-45` の説明、`ordering.py:78` `ORDERING_RULE`)。
2. **先読みを「隠す」から「持たせない」に変えた**。前の核は全期間の事象の列を戦略の手の届く所(`EventWindow._log`、`place_order` の束縛先の `CoreEngine`)に置き、公開の口で範囲を切っていた(前の実行の批評家の試験 `tests/bt/critic/item_0/test_context_leaks_engine_via_private_attrs.py` が 2 経路とも失敗していた【事実: 着手前に `pytest tests/bt` を打って 3 件失敗】)。今は (a) データ源を遅延で 1 件ずつ読む(`engine.py:300` `_refill`)、(b) 戦略の履歴は「もう届けた事象」の列だけ(`engine.py:392` `_deliver`)、(c) 発注の口は取引所ではなく `_OrderPort`(自分の注文の台帳と送信箱だけを持つ、`api.py:147`)、(d) 呼び出しが終わると文脈を失効させる(`api.py:271` `_revoke`、`window.py:32` `revoke`)。
3. **取引所の答えを検算する台帳を核に置いた**(`engine.py:115` `_VenueLedger`)。約定模型(差し込み口)が「届いていない注文への約定」「受付前の約定」「数量超過」「終わった注文への報告」「注文・取消への無回答」を返したら `VenueProtocolError` で止める。

## 3. 試験

- 足した試験: **123 件**(新しい 11 本。前の実行の核の試験 69 件は API を作り替えたため消した → §5 の 3)
- 核の試験: `PYTHONPATH=src python -m pytest src/bot/bt/core/tests` → 末尾 `123 passed in 1.32s`【事実】
- 核 + `tests/bt`(前の実行の批評家の試験 7 件を含む): `PYTHONPATH=src python -m pytest src/bot/bt/core/tests tests/bt` → 末尾 `1 failed, 129 passed in 2.07s`【事実】。落ちた 1 件は `tests/bt/critic/item_0/test_liquidation_has_no_account_hook.py::LiquidationReachesAccountTest::test_engine_notifies_the_account_of_a_liquidation_event`(着手前から失敗していたもの。理由は §5 の 1)。着手前は同じ範囲で `3 failed, 73 passed` だった【事実】。
- 全試験(`PYTHONPATH=src python -m pytest`)はこの周では回していない。`src/bot/bt/` は他のどこからも import されていない【事実: `grep -rn "bot.bt" --include=*.py src scripts tests` で核と `tests/bt/critic` 以外の当たりなし】。ただし既定の `pytest` は核の試験を集めない(§5 の 2)。
- 速さ(参考、合成データ): 事象 20 万件を戦略が何もしない条件で 2.58 秒(約 7.7 万件/秒)。2000→8000 件、3000→12000 件で線形に近いことを試験で固定(`test_engine_source.py` `test_cost_grows_close_to_linearly`、前の実行の批評家の試験 `test_engine_run_scales_quadratically.py` も通る)【事実】。

## 4. 要件の各行を満たした根拠

### 4.1 委任文 §2 の項目 0 の行

| 要件 | 根拠(ファイル:行) | 試験 |
|---|---|---|
| 時刻は UTC の int64 ナノ秒 | 全事象の時刻は `validate_nanos`(`time.py:74`)を通る int。ISO はナノ秒まで自前で解析し丸めない(`time.py` `_iso_to_nanos`。`datetime.fromisoformat` はマイクロ秒で切れる【事実: `...00.123456789+00:00` が `...00.123456` になるのを打って確認】)。浮動小数と文字列の秒は `Decimal` で正確に換算し、ナノ秒未満の桁があれば拒否。機械可読の契約 `TIME_CONTRACT`(`time.py:54`) | `test_time.py` 12 件 |
| 事象の型(約定・板の写真・板の差分・足・資金調達・清算・時計・注文の受付/拒否/約定の通知) | `events.py:44` `EventType` に 12 種(求められた 8 分類 + 通知を 受付/拒否/約定/取消済み/状態不明 に分けた)。各型は凍結・構築時に検査(価格が有限で正・足の高安の整合・板の並び・`exchange_time_ns ≤ received_time_ns` ほか)。`to_dict` / `event_from_dict` で欠落なく往復 | `test_events.py` 8 件(往復 12 型、不正な値 17 通り) |
| 戦略は「受け取れた時刻 ≤ 今」の事象しか見られない(構造で) | §2 の 2。戦略が手にする文脈から届く物(非公開の属性・束縛先・入れ物を全部たどる)に未来の事象が 1 件も無いことを、乱数の遅延つき 5 通りで試験(`test_lookahead.py` `test_nothing_reachable_from_ctx_is_in_the_future`)。データ源の先読みは 1 件まで(`test_source_is_pulled_lazily...`)。取引所側も `exchange_time_ns` より前には事象を見ない(`test_fill_model_never_sees_market_data_before_its_exchange_time`) | `test_lookahead.py` 7 件 |
| 決定的な事象の順序(同時刻の並びの規則を明記) | `ordering.py:1-45`(規則の文)、`ordering.py:53` `DELIVERY_PRIORITY`、`ordering.py:78` `ORDERING_RULE`(機械可読)。通し番号が一意なので全順序。発注と通知の経路は先入れ先出し(`engine.py:428` `_drain`、`engine.py:492` `_handle_reports`) | `test_ordering.py` 5 件、`test_determinism.py` 2 件(乱数の入力・遅延・戦略で 2 回の結果が全項目一致) |
| 戦略の API(事象ごとの呼び出し・発注・取消) | `strategy.py:12` `on_event`、`api.py:343` `place_order`、`api.py:349` `cancel_order`。ほかに `visible_events` `last` `order` `open_orders` `set_timer`(`api.py:362` `STRATEGY_API`) | `test_api_surface.py` 2 件、`test_orders.py` 12 件 |
| 他項目が差し込む口(約定模型・遅延模型・費用・口座) | `interfaces.py:91` `FillModel`(`on_market_event` `on_order` `on_cancel`)、`interfaces.py:111` `LatencyModel`(配信・発注・取消・通知の 4 つを別々に)、`interfaces.py:131` `CostModel`、`interfaces.py:138` `Account`。核の外で書いた実装で 4 つとも差し替えて動くこと、欠けた口は構築時に拒否することを試験。費用の模型を渡さずに約定が起きたら `MissingCostModelError`(`engine.py:507`。黙って 0 にしない) | `test_extension_points.py` 5 件、`test_latency.py` 4 件 |

### 4.2 比較の観点(REQUIREMENTS.md §2)

| 観点 | 根拠 |
|---|---|
| 1 事象駆動 | 事象 1 件ごとに `on_event` を 1 回呼ぶ。`step()` で 1 件ずつ進められる(`engine.py:339`) |
| 2 事象型の網羅 | 8 分類すべて(上表) |
| 3 時刻の精度 | int64 ns・UTC、`TIME_CONTRACT` で申告 |
| 4 先読み防止の構造化 | 上表の 3 行目 |
| 5 同時刻の決定的順序 | 上表の 4 行目 |
| 6 戦略 API | 呼び出し・発注・取消の 3 つ + 5 つ |
| 7 拡張口 | 4 つ。`CORE_CONTRACT["sockets"]` がプロトコルから機械的に作った一覧を出す(`contract.py:15`) |

参考: 場面集の 27 場面の入力を、adapter を介さず核に直接通した自己確認を scratchpad(`bt/item0_r1_worker_scenecheck.py` と `.log`)に置いた。既知解の場面はすべて期待と同じ値が出た(v2 の往復は欄の名前の対応付け `ts_ns`→`received_time_ns`、`qty`→`size` が要る)【事実】。これは資料係の表ではない。

## 5. 満たせなかった行・限界

- **場面にしていない限界(正直に書く)**: Python では、戦略の関数が `gc.get_referrers` などで実行中のオブジェクトを総当たりすれば、核の待ち行列(未来の事象を含む)に届く【推定: 言語の性質。試していない】。核が防いでいるのは「文脈から参照をたどって届く」経路まで。
- 既定の妥当範囲(1970〜2100 年)では、「秒をナノ秒・ミリ秒と取り違えた」向き(値が小さすぎる向き)は捕まらない。`to_nanos(..., plausible=(下限, 上限))` で時代の範囲を渡せば捕まる(`test_time.py` `test_value_too_small_for_its_label_needs_an_era_window`)。データ層(項目 1)で源ごとに範囲を渡す前提。
- `testing.py` の `ImmediateFillModel` などは試験用の代役で、どの取引所の模型でもない(冒頭の注記に明記)。
- 外部の道具: 入れていない。ネットワークも使っていない。

## 6. リードに聞くこと

1. `tests/bt/critic/item_0/test_liquidation_has_no_account_hook.py::...test_engine_notifies_the_account_of_a_liquidation_event` は、核をどう作っても通らない形になっている: 試験の中の `_RecordingAccount` に `apply_liquidation` が無く、`liquidation_events` に書き込むのは誰もいない(試験の 43〜53 行。清算の事象は 69 行、確かめる所は 75 行)。さらに `side="long"` を使うが、新しい核の清算の事象は取引所が出す形(清算の注文の向き `buy`/`sell`)だけを受け、`long`/`short` は推測で置き換えずに拒否する。この試験は持ち物の外なので変えていない。扱い(試験を直すか、除くか)を決めてほしい。
2. `pyproject.toml` の `testpaths = ["tests"]` のため、既定の `PYTHONPATH=src python -m pytest` は `src/bot/bt/core/tests` を 1 件も集めない【事実: `--collect-only` の出力で `src/bot/bt/core/tests` の行 0 件、全体 2887 件】。完了の条件「`PYTHONPATH=src python -m pytest` が全件通る」に核の試験を入れるには、`testpaths` に足すか、`tests/bt/` 側(項目 11 の持ち物)に置く必要がある。どちらも持ち物の外。
3. 前の実行(`_run1_prose_judging`)の核の試験 7 本・69 件を消して新しい 123 件に置き換えた(同じ持ち物の中。旧 API の `build_event_log`・`LatencyModel.delay_ns`・`FillModel.on_event(event, visible)` を作り替えたため)。委任文 §4「既存の試験を落とさない。消さない、飛ばさない」がこれにも当たるなら、旧の試験の性質のうちどれを残すべきか指示がほしい(旧の試験が見ていた性質は新しい試験で全部見ているつもりだが【推定】、1 対 1 の対応表は作っていない)。
4. 場面 v5(同時刻の順序)の入力には「注文の通知」の事象が含まれる。新しい核は通知をデータ源から受けず(`SourceEventTypeError`)、発注したときに取引所の答えとして作る。資料係の adapter がこの場面をどう通すかは資料係の判断で、核は場面に合わせた特別扱いをしていない。
