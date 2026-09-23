# 作業者の報告(作る:0#1、agent a85da652e00ac1055。Workflow の記録の返り値から逐語で書き出し)

## 変えたファイル

- /home/user/trade/src/bot/bt/core/engine.py
- /home/user/trade/src/bot/bt/core/ordering.py
- /home/user/trade/src/bot/bt/core/time.py
- /home/user/trade/src/bot/bt/core/events.py
- /home/user/trade/src/bot/bt/core/contract.py
- /home/user/trade/src/bot/bt/core/__init__.py
- /home/user/trade/tests/bt/item_0/test_bt0_scene_set.py
- /home/user/trade/tests/bt/item_0/test_bt0_queue_key.py
- /home/user/trade/tests/bt/item_0/test_bt0_time.py
- /home/user/trade/tests/bt/item_0/test_bt0_ordering.py

## 足した試験の数

40

## 試験のコマンド

PYTHONPATH=src python -m pytest tests/bt/item_0 (核 = 自分の項目) / PYTHONPATH=src python -m pytest tests/bt / 全試験は setsid nohup PYTHONPATH=src python -m pytest > <scratchpad>/bt/pytest_item0_r1_worker_full.log 2>&1 &

## 試験の末尾の行

tests/bt/item_0: 「203 passed in 2.32s」【事実】 / tests/bt 全体: 「1 failed, 221 passed in 3.55s」【事実】(着手前は 1 failed, 181 passed。落ちたのは同じ 1 件で、批評家の試験 test_liquidation_has_no_account_hook.py::LiquidationReachesAccountTest::test_engine_notifies_the_account_of_a_liquidation_event。試験自身の誤りなので規則 8 により変えていない) / 全試験(17:23:46 開始、記録 /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/pytest_item0_r1_worker_full.log): 「1 failed, 3108 passed, 4 skipped, 1 warning in 757.92s (0:12:37)」【事実】。FAILED の行はこの批評家の試験 1 件だけ。

## この周で変えた構造

(1) 戦略に見える event.seq を、待ち行列の通し番号から「戦略が受け取った回数」(1, 2, 3, …)に変えた(engine.py:490)。前の核では seq の飛びから「取引所では起きたがまだ受け取っていない事象」の件数を数えられた(実測: 隠れた事象 1 件で 2 日目の seq が 4 → 6)。これは先読みの側道だった。(2) 待ち行列の鍵を (時刻, 優先度, seq) から (時刻, 優先度, 由来, 序数) に変えた(engine.py:373 `_push`、ordering.py:113-114・ORDERING_RULE)。由来 = 入力から来たか核が作ったか、序数 = 合流した入力の中の位置、または核が作った順。これで同時刻の並びが入力の中身と模型の答えだけで決まり、流れを遅延で読む時点には左右されなくなった(入力の心拍とタイマーが同時刻なら心拍が先)。(3) ISO の時差が範囲外(例 +09:75)のとき、黙ってずらさず TimestampUnitError で止める(time.py:185)。

## 満たせなかった行・要件の各行の根拠・限界

- 委任文 §6 の報告を docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/round_1/REPORT.md に書けなかった。Write の道具が「Subagents should return findings as text, not write report files」で拒んだ。Bash で回り込んで書くことはしていない。報告の中身はこの出力の各欄に入れた。リードかその道具を通せる者が書き写す必要がある。
- 要件の行と観点で満たせなかったものは無い。根拠: 場面集の 32 場面すべてを、核の公開の名前(bot.bt.core)だけで 2 回ずつ走らせ、全部が正解と一致し、2 回の出力も同じだった(tests/bt/item_0/test_bt0_scene_set.py)。差し込む口(約定の模型・遅延・費用・口座)は、この試験のファイルの中で公開の口の形に書いた。核の側の代役は testing.ImmediateFillModel だけ。これは作業者の自己確認であり、資料係の表ではない。
- 要件の行ごとの根拠(ファイル:行)。時刻 = time.py:74 validate_nanos、engine.py:373 _push、time.py:152 と :185 の ISO(時差の範囲の検査を含む)、time.py:54 TIME_CONTRACT。事象の型 = events.py:44 EventType 12 種。先読みの禁止 = engine.py:479 _deliver、api.py:304 の失効、api.py:357 LookAheadError、engine.py:490 の seq。順序 = ordering.py 冒頭の規則の文、:82 TYPE_ORDER、:113-114、:130 ORDERING_RULE。戦略の API = strategy.py:12、api.py:408/:414/:418/:431。差し込む口 = interfaces.py:106/:126/:146/:153。
- 書き直した試験は 1 件(規則 8)。test_bt0_ordering.py::test_rule_is_declared_machine_readably_and_is_total の鍵の期待を ['time_ns','priority','origin','ordinal'] に変え、depends_on_pull_timing is False を確かめる 1 行を足した。消した試験は 0 件。新しい試験 4 件(seq 2 件・心拍とタイマー・ISO の時差)は前の核では落ちる。確かめ方: git archive HEAD src/bot を scratchpad に出し、同じ試験を回して「4 failed, 19 passed」【事実】。規則の全体の並べ替えを確かめる性質の試験(種つきの乱数で 200 通り)は、前の核でも通る。
- 限界(前の報告と同じ)。(a) gc.get_referrers などの言語の性質を使えば待ち行列に届く【推定・試していない】。(b) 既定の妥当範囲 1970〜2100 年では、秒をナノ秒と取り違えた向きは捕まらない(plausible= を渡せば捕まる)。(c) 同じ流れの中で同じ型・同じ時刻の事象は、流れの中の順で並ぶ。外部の道具は入れていない。ネットワークも使っていない。

## リードに聞くこと

- 同時刻に入力の心拍(時計)と戦略のタイマーが並ぶとき、入力の心拍を先にした(ORIGIN_SOURCE=0 < ORIGIN_ENGINE=1)。REQUIREMENTS.md の P0-5 で調査結果の側に挙がっている候補 44 の契約「データ → 派生 → 信号 → 注文 → 約定」に合わせ、入力から来たものを核が作ったものより先に置く、と読んだ。この向きは委任文の逐語には無い。逆にするなら定数 2 つを入れ替えるだけで、規則の形(入力の中身だけで決まる)は変わらない。
- event.seq の意味を「待ち行列の番号」から「戦略が受け取った回数」に変えた。src/bot/bt/ の外で bot.bt を読む所は無い【事実: grep -rn "bot\.bt\b\|bot/bt\|from bot.bt\|import bot.bt" --include=*.py src scripts tests の当たりは src/bot/bt/ と tests/bt/ だけ】。CORE_VERSION は core-3 から core-4 に上げた。
- 資料係の新実装の adapter(tests/bt/battery/item_0/adapters/new_impl.py)はまだ無い。adapters/ にあるのは __init__.py・common.py・current_impl.py・protocol.py だけ。mutant.py --check も new_impl.py が無いと回らない。場面を公開の口だけで通す書き方は tests/bt/item_0/test_bt0_scene_set.py にある(口座・約定の模型・遅延・費用を公開の口の形で書いている)。adapter は資料係の持ち物なので、作業者は作っていない。
- 批評家の試験 test_liquidation_has_no_account_hook.py::...test_engine_notifies_the_account_of_a_liquidation_event は、試験自身の誤りで落ちる(規則 8 により変えていない)。誤りは 2 つある。(a) 69 行の side="long" は清算の注文の向き(buy/sell)ではないので、EventValidationError になる。(b) 43〜53 行の _RecordingAccount に apply_liquidation・on_market_event・check_order が無く、構築時に TypeError で拒まれる。2 つを直した写しでは apply_liquidation が 1 回呼ばれる【事実: /tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/item0_r1_worker_liq_check.py と .log】。リードの処置 11 のとおり、次の周の批評家に確かめてもらう。
- REPORT.md を置く場所(round_1/)には、この周の前(14:32)に作られた 表_*.md が 6 枚ある。作業者が作ったものではないので、触っていない。
