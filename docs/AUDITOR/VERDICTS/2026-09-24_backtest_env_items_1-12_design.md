# 項目 1〜12 のリードの設計メモ(`docs/DISCUSSIONS/2026-09-23_backtest_env/LEAD_DESIGN_items_1-12.md`)の監査の記録

L-439「今リードの手が空いているなら次の項目の設計を進めておいてください」を受けた成果物。O-5 により、オーナーに出す前に監査役を通す。

## 1 回目(対象の版: eed94e8f2cb4。指摘 8 件 = 止める 2・直す 3・聞く 3)

### 監査役の出力(逐語)

監査結果(問いの一覧)を返す。

対象: /home/user/trade/docs/DISCUSSIONS/2026-09-23_backtest_env/LEAD_DESIGN_items_1-12.md

1. [止める] LEAD_DESIGN_items_1-12.md:11 — 「戦略の見え方(`api.py`の`StrategyContext`): …・`place`・`cancel`・`set_timer`」と書かれているが、src/bot/bt/core/api.pyの`StrategyContext`が実際に持つ公開メソッド名は`place_order`(655行)・`cancel_order`(661行)であり、`STRATEGY_API`タプル(708-719行)にも`place`・`cancel`という名は存在しない(`place_order`・`cancel_order`のみ)。加えて`STRATEGY_API`に含まれる`revoked`がこの列挙から漏れている。項目11は「核を見ずに」参照実装を書く規則(委任文§2の項目11行)であり、この`lead_notes`が唯一の情報源になりうる。核の接点の記述が実物(contract.py・interfaces.py・api.py)と一致しているか。

2. [直す] LEAD_DESIGN_items_1-12.md:12 — 「事象 8 種(`event_types`)」とあるが、`CORE_CONTRACT["event_types"]`(contract.py 30行、`EventType`列挙 events.py 52-64行)を実測すると`TRADE`〜`ORDER_STATE_UNKNOWN`の12件(`PYTHONPATH=src python3 -c "from bot.bt.core.contract import CORE_CONTRACT; print(len(CORE_CONTRACT['event_types']))"` → `12`)。コード識別子`event_types`を名指しながら数が実物と食い違っている。

3. [止める] LEAD_DESIGN_items_1-12.md:34(項目4行)・38(項目8行) — 「種つきの乱数は核の`run_settings`の種から」「核の`run_settings`(種・版)」と書かれているが、`CoreEngine.__init__`(engine.py 532-544行)の引数は`strategy/events/fill_model/latency_model/cost_model/account/end_time_ns/history_limit/time_span_ns`のみで`seed`は無く、`CORE_CONTRACT["run_settings"]`(contract.py 130-139行)も`time_span_ns`・`end_time_ns`・`history_limit`の3項目だけで種(seed)を持たない(`grep -rn "seed" src/bot/bt/core`はcontract.py以外に1件も出ない)。項目4・7(種つき乱数)・8(実行記録の種)の設計が、核が持たない機能に依存する形で書かれている。

4. [直す] LEAD_DESIGN_items_1-12.md:17 — 「A(帰属: …対象×設定を1つの候補として走らせる)」の「候補」は、項目0の正の定義A(tests/bt/battery/item_0/ROOTCAUSE_r8-1.md:290-292)が「リードの答え§7の5の『候補』の語は、道具台帳の候補と分けるため『設定つき対象』と書いた」と明記して意図的に言い換えた語そのもの。同じ文書内の§2表の見出し「観点の候補」(29行)、委任文で多用される道具台帳の「候補」と合わせ、「候補」が少なくとも3通りの意味で使われている(用語の使い回し)。

5. [聞く] LEAD_DESIGN_items_1-12.md:32 — 委任文§2の項目2行では注文種が「…OCO・取消と訂正・部分約定…」(1項目として「取消と訂正」)だが、この設計メモでは「注文の種類9つ(…OCO・訂正)」と、単独の「取消」への明示的な言及が列から消えている(総数9は維持)。委任文の行から標的(単独キャンセルの試験)を説明なく狭めていないか。

6. [直す] LEAD_DESIGN_items_1-12.md:47 — 「Workflowの同時実行は16体まで」に出所(コマンド・設定ファイル・ログ)が付いていない。`grep -rl "16体" --include="*.md" .`はこのファイル以外にヒットせず、他の数値(1周の時間、opponents/RUNNABILITY.tsvの36件など)のように参照先が示されていない。

7. [聞く] LEAD_DESIGN_items_1-12.md:47 — 「実測(項目0): 1周 ≈ 1.5〜4時間(場面集の直しが8割)」は「実測」と分類されているが、どの回・どの周・どのVERDICTS/ログを実測したかの参照が無い(このファイルの他の実測値引用は具体的な節番号・ファイル名で示されている)。

8. [聞く] docs/OWNER_LOG.md:440(L-439) — 同じ回の「リードの対応」欄が自ら記した計画は「docs/DISCUSSIONS/2026-09-23_backtest_env/item_<N>/LEAD_DESIGN.md」(項目ごと、item_<N>配下)。実際の成果物は単一のLEAD_DESIGN_items_1-12.md(item_<N>配下ではない)で、項目0の慣行(item_0/round_7/LEAD_DESIGN.md)とも形が異なる。自分の記録した計画と実際の置き場所が食い違う経緯が本文に無い。

最後に読んだ版の sha256 先頭 12 桁: eed94e8f2cb4

参考に読んだファイル(絶対パス):
- /home/user/trade/docs/DISCUSSIONS/2026-09-23_backtest_env/LEAD_DESIGN_items_1-12.md
- /home/user/trade/docs/DATA/delegations/20260923_backtest_env_prompt.md(§2・§3)
- /home/user/trade/docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_7/LEAD_DESIGN.md
- /home/user/trade/tests/bt/battery/item_0/ROOTCAUSE_r8-1.md(正の定義0〜E)
- /home/user/trade/tests/bt/battery/item_0/opponents/RUNNABILITY.tsv
- /home/user/trade/src/bot/bt/core/contract.py
- /home/user/trade/src/bot/bt/core/interfaces.py
- /home/user/trade/src/bot/bt/core/api.py
- /home/user/trade/src/bot/bt/core/engine.py
- /home/user/trade/src/bot/bt/core/events.py
- /home/user/trade/docs/OWNER_LOG.md(L-405, L-406, L-407, L-433〜L-439)

### リードの処置(1 件 1 行)

1. 直した: 戦略の API の名前を `CORE_CONTRACT['strategy_api']` の実物から出力して書いた(`now_ns`・`current_event`・`revoked`・`visible_events`・`last`・`order`・`open_orders`・`place_order`・`cancel_order`・`set_timer`。コマンドを本文に併記)。
2. 直した: 「事象 8 種」→「`event_types` の 12 値(要件の 8 種のうち通知が受付・拒否・約定・取消・状態不明に分かれる)」。同じコマンドで `len` = 12 を出力。
3. 直した: 核は種を持たない(`run_settings` は 3 項目、出力を併記)。種は模型自身の設定として受け取り、項目 8 の実行記録が各模型の種を集める。項目 4・8 の行を直した。核に種を足す設計は取らない。
4. 直した: 対象 × 設定は「設定つき対象」、「候補」は道具台帳の候補にだけ使う。「観点の候補」→「観点の下書き」。
5. 答え+直した: 狭める意図はなかった(数えの誤り)。委任文の行どおり「注文の種類 8 つ(…OCO)/ 取消と訂正 / 部分約定」に直した。
6. 直した: 「16 体まで」の出所 = Workflow の道具の説明の文 `min(16, CPU 数 − 2)` と、この環境の `nproc` = 4 を併記。
7. 直した: 「1 周 ≈ 1.5〜4 時間」→ 周ごとの実測(第 4 周 94 分 / 第 5 周 170 分 / 第 6 周 226 分(場面係の直し 183 分)/ 第 7 周 70 分)と出所(run の記録の時刻の集計、VERDICTS run7、L-437 の行)。
8. 答え+直した: 置き場所を 1 ファイルにした経緯(共通の設計が大半で、12 ファイルに分けると重複し I-007 に触れる)を L-439 の「リードの対応」欄に追記した。

処置後の版: 554b58d7a127。
