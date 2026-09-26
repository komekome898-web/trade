# 項目 4 第 2 周 批評家の記録(新しく起こされた批評家)

委任文 `docs/DATA/delegations/20260925_backtest_env_prompt.md`(指紋 `20260925_backtest_env_prompt.md@388d55cdeb32`。`sha256sum` の先頭 12 桁 `388d55cdeb32` を確かめた)を最初に全部読み、§3「批評家」の格付けの基準で付けた。固定した要件 `docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/REQUIREMENTS.md`、場面集 `tests/bt/battery/item_4/DEFINITIONS.md` を手元に置いた。実データから出た数値はこの記録に入れていない(委任文 §4)。

## 0. 対応表(CLAUDE.md §0.1)

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 非常に厳しく批評し、自分で試験を書いて壊しにいく | 「非常に厳しい批評家（クリティック）とし、要件を満たせない場合は達成できるまでループを継続させること」 |
| 調査結果以上の信頼性と再現性を軸に見る | L-405「すべてが調査結果以上の信頼性と再現性に優れたものにすること。」 |
| 資料係の申告を数え直す | L-451「案1みたいなこと前に承認しましたよね？…」(台本の配線 = 監査 66-2。数え直しの手順はリードの語) |

## 1. 資料係の申告の数え直し(table_recount)

申告: new_impl_correct = 67/67、new_impl_all_correct = true。

打ったコマンド(materials の置き場所 `round_2/materials/runs/new_impl.tsv`):
```
F=runs/new_impl.tsv; tail -n +2 $F | wc -l                 -> 67
tail -n +2 $F | cut -f1 | sort -u | wc -l                    -> 67(場面の重複なし)
tail -n +2 $F | cut -f4 | sort | uniq -c                     -> 67 正解と一致(1 回目)
tail -n +2 $F | cut -f7 | sort | uniq -c                     -> 67 正解と一致(2 回目)
tail -n +2 $F | cut -f10 | sort | uniq -c                    -> 67 2 回の実行で同じ
```
場面集の場面の総数: `i4_scenes.SCENES` の長さ 67(NOT_SCENES は I4-7・I4-19・I4-20 の 3 観点)。場面集の指紋 `git ls-files -z tests/bt/battery/item_4 | xargs -0 sha256sum | sha256sum` = `baccb379…`(materials の fingerprint.txt と同じ)。

独立の再走: `TMPDIR=<scratchpad>/bt/i4_r2_critic_rerun_tmp PYTHONPATH=src python3 tests/bt/battery/item_4/run_battery.py --target new_impl --out <scratchpad>/bt/i4_r2_critic_rerun_new_impl.tsv`(rc=0)→ 67 行・67 正解と一致・67 2 回の実行で同じ。materials の表との違いは i4-5-outputs・i4-6-label の観測の要約値だけ(組は同じ。私が試験のファイルを足してコードの状態が変わったためと読む。materials の commands.txt も同じ 2 場面の要約値の違いを記録している)。

**数え直し = 67/67。申告と一致(table_recount_ok = true)。**

## 2. 走らせた試験(私有の一時フォルダ)

- `PYTHONPATH=src python -m pytest tests/bt/battery/item_4 tests/bt/critic/item_4 --basetemp=<scratchpad>/bt/i4_r2_critic_battery_basetemp -p no:cacheprovider -o tmp_path_retention_policy=none` → **1 failed, 223 passed**(落ちたのは `test_battery_item4_diffscope.py::test_check_matches_delegation_text_on_grid`。§4 の i4-r2-09)。前の周の批評家の試験 4 本はすべて通る。
- `PYTHONPATH=src python -m pytest tests/bt/item_4 tests/bt/compat …(同じ形)` → **1070 passed, 2 skipped**(飛ばしたのは `test_i4_core_carryover.py:56` の 2 件。理由の文は「2**41 回の訪問」で作れない、作業者の試験で、この作業の前からの試験ではない)。
- この周に私が足した試験(`tests/bt/critic/item_4/test_i4r2_*.py`、4 本)→ **10 failed**(下の指摘の根拠。壊れた試験は残し、作業者・場面係が直す)。

## 3. 前の周の指摘の直りを自分で確かめた結果

| id | 確かめ方 | 結果 |
|---|---|---|
| i4-r1-01 | spec の足 j の始値の合図と範囲の出口の順(`barmodel.py` 冒頭 25-38 行、`BarRules.signal_at_open`)を読み、前の周の批評家の試験 `test_i4r1_pending_signal_before_intrabar_exit.py` を回した(通る) | 合図の順は直った。**同じ族の残り**: 時間切れの足で範囲の逆指値を始値より先に取る(R-H3)→ i4-r2-02 |
| i4-r1-02 | DEFINITIONS.md 70-83 行に R-O1 が入り、20 組の順を場面が固める | 足した。ただし R-O1 の中の R-H3 が R-O1 自身の原則と食い違う(i4-r2-02)。規則の文が決めていない振る舞いが別に残る(i4-r2-08) |
| i4-r1-03 | 参照実装の成果物の形と、場面集の I4-1 の口 | **直っていない**(i4-r2-01) |
| i4-r1-04 | 出所の判定(`pipeline.py:134-192・346-356`)を試験で壊した | 置き場所と同じバイトは断るが、再圧縮・展開・切り出しで破れる(i4-r2-03)。同じ族の別の形(研究の事前登録の語)も残る(i4-r2-05) |
| i4-r1-05 | 表の注記と場面の一覧 | I4-10・I4-13 などに足 0 でなく手数料を分けない値の場面が足され、相手が正解を出せるようになった(例: i4-10-stop-first-plain で Backtrader・backtesting.py が正解と一致)。直ったと読む |
| i4-r1-06 | 性質の場面(DEFINITIONS.md 208-272 行)が逆指値・利確・maker・持ち越し・時間切れ・構造的な逆指値を種つきで含む | 直ったと読む |
| i4-r1-07 | i4-3-core-delivery・i4-3-core-delivery-gap(核の粒度) | 直った |
| i4-r1-08 | 検討表の「持たないと確認した」の理由を正規表現で検めた | **直っていない**(i4-r2-04) |
| i4-r1-09 | i4-6-signal-refused・research-refused に対照 1・2 | 直った |
| i4-r1-10 | adapter の legacy が `run_backtest`(旧の名前・旧の引数)から取る(`adapters/new_impl.py` `_legacy_bars`) | 直った |
| i4-r1-11 | `opponents/attempts/` の dry-run と大きさの実測 | lumibot・Hikyuu・zvt は記録が足された。**同じ族の別の形**: PineForge が 2 周続けて 1 場面も走っていない(i4-r2-07) |
| i4-r1-12 | 変わっていない(作業者はリードに聞いた) | 未解消 → i4-r2-10 |
| i4-r1-13 | `tests/bt/battery/item_0/scenes.py:378-384`、最後の変更は 2026-09-25(i4-r1-13 より前) | 未解消 → i4-r2-11 |
| i4-r1-14 | `test_i4_real_data_smoke.py:6-17・150` | 直った |

前の周の批評家の試験で、作業者が「試験自身の誤り」と報告したものは無い(作業者の ROOTCAUSE.md §8、4 本とも通る)。取り下げたものは無い。

## 4. 指摘

### i4-r2-01 [止める] 実装(repeat_of i4-r1-03)I4-1 の場面の「参照実装」は独立でないまま
- 場面集の I4-1 の 2 場面と i4-3-ref-signal-first が突き合わせる「参照」は `bot.bt.reference.bar_rules.run_rules`(`adapters/new_impl.py` の `_run_reference`。その docstring は「the independent reference of the stated rules」と書く)。`bar_rules.py:1-22` 自身が「NOT the independent reference … written by the item-4 worker, who has read the core」と書く。要件 I4-1「核を読まない別の agent が書いた、遅くてよい参照実装…と同じ出力」を、表の I4-1 の 2/2 は測っていない。
- 作業者は独立の参照 `bar_sim` との突き合わせの試験を足した(`test_i4_engine_vs_independent_bar_sim.py`、良い)。しかし (a) `bar_sim` は数量・合図の手仕舞い・率の水準・持ち越し・構造的な逆指値を持たず、その範囲は突き合わせていない(同ファイル 34-37 行)、(b) 突き合わせで出た違い D1〜D3 を「結果」として許して通している。D1 は i4-r2-02 の欠陥そのもので、独立の参照の方が要件 I4-13 の文に合っていた。
- 成果物の形の読み(監査 65-3): `bar_sim.py`・`event_sim.py`・`num.py`・`SPEC.md` に核の import は無く、核の内部の名(received_time_ns・exchange_time_ns・FORCED_ID_PREFIX・visible_events・StrategyContext・OrderRequest・CoreEngine・BarVenue・on_market_event・ZeroLatency・OrderFillEvent・BookSnapshotEvent)の出現は 0(`grep -c` の合計)。独立の参照そのものは独立に書かれたと読む。欠けは「独立の参照が場面集の規則を持たない」ことと「場面集の口が独立でない方を呼ぶ」こと。

### i4-r2-02 [止める] 実装(repeat_of i4-r1-01)時間切れの足で、範囲の逆指値を始値の時間切れ・始値の合図より先に取る(R-H3)
- 試験 `tests/bt/critic/item_4/test_i4r2_time_exit_at_the_open.py`(2 件とも落ちる)。手で作った足: 始値は全部 100、BUY@0 → 足 1 の始値 100、逆指値 2%(98)、max_hold_bars = 2 → 足 3 の始値で時間切れ。足 3 の安値 97 は始値のあと。spec の出力 `{'bar': 3, 'side': 'CLOSE_LONG', 'price': 98.0, …}`(期待 100)。足 2 に CLOSE の合図を置いても同じ 98。
- 要件 I4-13「ちょうど bar entry_bar + max_hold_bars の始値で taker 決済されるか」に反する。場面集の R-O1 自身が「始値の出来事(①・②の時間切れ・③)は足の範囲の出来事(④〜⑦)より先」と書きながら、② の中で範囲の逆指値を時間切れより先に置く(DEFINITIONS.md 64-65・70-77 行)。始値が水準より上なら逆指値は始値より前に発火できないので、98 は時の順が許さない値。しかも利確は時間切れより先に取らない(R-H3 後半)ので、偏りは損の向きにだけ掛かる(構造的に棄却側へ振れる = CLAUDE.md §0.2 A-18 の形)。
- 場面集はこの答えを正解に固めている: i4-13-stop-on-time-bar・i4-13-stop-on-time-bar-maker(DEFINITIONS.md 581-584・621-624 行、正解 98)。表では backtesting.py と Backtrader がこの 2 場面で時の順どおり 101 を返し「不一致」にされている(`materials/runs/opp_backtesting.tsv`・`opp_backtrader.tsv` の該当行「fills[1].price = 101.0(正解 98.0)」)= 相手に不利な向きの場面。独立の参照 `bar_sim` も時間切れを始値で取り(作業者の D1)、要件の文に合っていた。
- 互換の口(legacy)は旧どおりでよい。spec と場面集の R-H3・2 場面を直す。

### i4-r2-03 [止める] 実装(repeat_of i4-r1-04)出所の判定が、中身の同じ市場データの再圧縮・展開・切り出しで破れる
- 試験 `tests/bt/critic/item_4/test_i4r2_origin_survives_reencoding.py`(6 件とも落ちる)。作業者の格子と同じ 2 本の市場データを、gunzip → gzip(ヘッダの時刻だけ違う)/ 展開 / 先頭 200 行の切り出し にして一時の根に置き `origin: "synthetic"` と宣言すると、`price_rule` × `動作確認` の計画が通る(FX の再圧縮は実行まで通った)。
- `pipeline.py:52-62` の docstring は「one byte … recompressed, decompressed, re-encoded, cut to a part -- is another file by content」を限界として書く。限界として書いても要件 I4-6「実データを通す実行の戦略が…に限られ」を構造で満たしていない。どれも研究者が 1 日のデータを手早く回す前にする普通の操作。行の中身(時刻と値)で照らす・合成は種つきの生成器からだけ作らせる、など宣言に依らない作りがありうる。

### i4-r2-04 [止める] 場面集(repeat_of i4-r1-08)検討表が「読んだ範囲(…)に無い」を「持たないと確認した」に数える
- 試験 `tests/bt/critic/item_4/test_i4r2_considered_unread_is_not_confirmed.py` が落ちる: `('56 zvt', '読んだ範囲(sim_account.py)に無い'), ('67 lumibot', '読んだ範囲(backtesting_broker.py・order.py)に無い') × 2`。lumibot の I4-17 の行は、根拠の全部が「読んだ範囲に無い」。
- 原因: `gen_considered.py:202` の `UNVERIFIED = ("読んでいない", "読んだ範囲に無い", "再現していない")` を部分文字列で照らすので、「読んだ範囲(ファイル名)に無い」と括弧が挟まると一致しない(`verified_absence` 212-222 行)。場面集の規則 6 の「行を引いて示したとき」に当たらない。DEFINITIONS.md 797 行の「読んでいない部分に依る場面は…『再現できない』に数えた」とも食い違う。
- `python3 scripts/check_bt_considered.py …` は「OK 誤り 0 件」(語の有無しか見ないので捕まらない)。

### i4-r2-05 [止める] 実装(repeat_of i4-r1-04)「研究」の実行が、どのファイルの hash でもない 64 桁の文字列で作れる
- 試験 `tests/bt/critic/item_4/test_i4r2_research_needs_a_real_preregistration.py`(3 件とも落ちる)。この環境の市場データ(作業者の格子の FX のファイル、市場のフォルダの中)× 目的「研究」× `price_rule` × `prereg_sha256` = `"00"*32`・`"cd"*32`(作業者の格子の値)・`sha256(b"x")` で計画が通る。
- `pipeline.py:288-292` は 64 桁の小文字の 16 進かどうかだけを見る。項目 3 の実行記録の口 `bot/bt/repro/runner.py:119-131` は事前登録をファイルとして受けて hash する。統合の口が、統合する部品より弱い。委任文 §4「目的 `研究` の実行は事前登録のハッシュが無いと作れない」が呼び手の一語で満たされる(i4-r1-04 と同じ形)。

### i4-r2-06 [止める] 実装(repeat_of null)統合の口が項目 2 の執行の模型を繋いでいない
- `pipeline.py` の import は core・data・report・repro だけ(84-92 行)。約定・遅延・費用・口座は自前の `FirstObservedFill`・`_Latency`・`_Fee`・`NullAccount`(372-470 行付近)。`_check_fill`(235-242 行)は `fill.price` を `'first_observed_at_or_after'`(「the one fill rule of the integrated run」)以外断る。コマンド: `_check_fill(dict(FILL_RULE, price='pessimistic', latency_ns=0))` → `PipelineError fill.price must be 'first_observed_at_or_after' …`。
- 項目 2 は核の差し込み口の形で `fill/venue.py`(`on_market_event` 270 行)・`latency.LatencyModel`(92 行)・`costs/schedule.ScheduleCostModel`(176 行)・`portfolio/account.MarginAccount`(110 行)を持つ。要件 §2 の射程の文「それらの部品が 1 本の統合されたパイプラインとして繋がっているか(I4-5)」を満たさない。実データを通す統合の実行で、項目 2 の「楽観側と悲観側の両方を必ず回して幅で出す」・遅延の分布・費用の出所・証拠金が 1 つも通らない。
- 場面集の I4-5 の 2 場面も F-1(最初に観測した値)の成行だけで、部品の繋がりを測らない(同じ直しで場面を足す)。

### i4-r2-07 [止める] 場面集(repeat_of i4-r1-11)動かせた道具 PineForge が 2 周続けて 1 場面も走っていない
- `materials/runs/opp_pineforge.tsv` の注記「項目 2 の driver … と道具の clone … が scratchpad から消えていて…道具を呼べない。構築し直しはこの周の持ち越し」、`opponents/RUNNABILITY.tsv` の 70 の行「この役の最初の走行では走ったが…最後の走行では呼べない(構築し直しは持ち越し)」。第 1 周の表でも 40 場面すべて結果なし。
- 場面集の規則 4「動かせた道具は全部の場面に通す。『この周では未実行』は禁止」に反する。PineForge は足の上の逆指値・指値・時間の手仕舞いを持つ候補で、I4-8〜I4-13 の相手として弱くない。構築し直しを試し、容量で止めるなら実測を付ける(規則 4)。
- 同じ族の小さい形: zvt は取得の大きさ 121.4 MiB に対し空き 826,646,528 バイトの時点で「展開後は取得の大きさより大きい」として導入を止めた(展開後の大きさは測っていない。RUNNABILITY.tsv 33 行)。

### i4-r2-08 [止める] 場面集(repeat_of i4-r1-02)規則の文が決めていない maker の振る舞いが 2 つ残り、場面が無い
- 作業者の独立の参照との突き合わせで出た違い D2・D3(`test_i4_engine_vs_independent_bar_sim.py:22-27`)は、どちらも場面集の規則の文(R-M1〜R-M5・R-E2)が決めていない所。
- D3 を自分で確かめた(maker、寿命 3、合図の足のマスク False、BUY@0): 次の足が指値を厳密に通過する足の並びでは spec も legacy も約定 0・取り逃し 0、通過しない並びでは約定 0・取り逃し 1。建てられない指値の取り逃しの数が値の道筋で変わる。要件 I4-16(取り逃しの数)と I4-14(マスク)の maker の経路を固める規則と場面が無い(I4-14 の 2 場面は taker だけ)。
- D2(待っている建ての指値と同じ向きの合図)も規則が無い。

### i4-r2-09 [止める] 場面集(repeat_of null)場面集の試験が 1 件落ちる(台本の変更が委任文の文に無い)
- `test_battery_item4_diffscope.py::test_check_matches_delegation_text_on_grid` が落ちる(10 件の食い違い、最初は `docs/AUDITOR/TRACE/2026-09-26_220780c0.json`)。
- 自分で確かめた: 場面係の直しの時点の台本(`git show d703870:scripts/workflows/backtest_env.js`)に同じ格子を当てると食い違い 0、HEAD の台本では 10。原因はリードのコミット 129fdc1 が `checkBattery` に `docs/AUDITOR/TRACE/` の除外を足したこと(`backtest_env.js:157-159`)で、委任文の L-448 の行には除外の文が無い。場面係の申告(試験が通った)はその時点では正しかった。
- 試験は委任文の文と台本の食い違いを正しく捕まえている。直し方は、リードが委任文に除外の文を足し、場面係が `_inside_by_text` をその文に合わせること。場面係が台本に合わせて試験だけを変えるのは文言合わせになる。

### i4-r2-10 [直す] 実装(repeat_of i4-r1-12)互換の口が、旧が計算していた入力(高値 < 安値の行・NaN の行)を断る
- 変わっていない(作業者の ROOTCAUSE.md §4・§7-4 でリードに聞いた)。自分でも確かめた: 足の列に open=100・high=101・low=100.2・close=100.5 の行(始値が安値より下)を入れると `BarModelError: bar 1 cannot be a bar event: bar invariant violated`(`barmodel.py:691`)。旧を import する 12 本が実データでこの形の行に当たるかは測られていない。

### i4-r2-11 [直す] 場面集(項目 0)(repeat_of i4-r1-13)P0-2 の単位の場面にマイクロ秒の float-subns の形が無い
- `tests/bt/battery/item_0/scenes.py:341-384`: s・ms には `float-subns` があり、us には無い。us の `float-held` の導き方は 2^50〜2^51 の範囲の話で「この範囲の float は…」と書くが、小さい時刻のマイクロ秒の float(例: 1.0005 マイクロ秒 = 1000.5 ns)は持つ値にナノ秒より細かい端数を持つ。最後の変更は 2026-09-25 で、i4-r1-13 のあと手が入っていない。

## 5. 場面集の規則 1〜9 と要件の観点の覆い

- 規則 1(能力を申告で数えない): 能力の場面(12)は全部、出力を正解と突き合わせる(two-models は互換と仕様の両方の値、i4-6 は対照つき)。違反は見つけていない。
- 規則 3(各観点に値の場面): I4-1〜I4-18(I4-7 を除く)のすべてに値の場面がある(`i4_scenes.SCENES` を観点と種類で数えた)。
- 規則 4: PineForge(i4-r2-07)。
- 規則 6: i4-r2-04。
- 規則 9: `check_bt_considered.py` は誤り 0。語の正しさは i4-r2-04。
- 観点の覆い: I4-5 の部品の繋がり(i4-r2-06)、I4-14・I4-16 の maker の経路(i4-r2-08)が欠ける。I4-7・I4-19・I4-20 は場面にできない観点として NOT_SCENES に理由がある。
- 偏り: i4-r2-02 の 2 場面は相手に不利な向き。
- 資料係の adapter: 新実装の口は旧の名前・旧の引数(`run_backtest`・`split_data`)で互換の出力を取り、spec は `run_bars`、核の粒度は核の Strategy で呼ぶ。新実装だけを有利にする呼び方は見つけていない。ただし `_run_reference` の docstring が作業者の写しを「independent」と書く(i4-r2-01)。
- 再現の忠実さ: この周に変わった共通部分(`_i4_base.py` の `delivery`、`_repro_bars.py` の DELIVERY)を読んだ。再現は約定の規則だけを写し、道具の事象の流れを写していないと注記して「結果なし」にしており、弱めた答えを作ってはいない。

## 6. 参照実装の独立(監査 65-3)の判断の根拠

`src/bot/bt/reference/bar_sim.py`・`event_sim.py`・`num.py` の import は標準ライブラリと `bot.bt.reference.num` だけ(`grep -n "^from\|^import"`)。核の内部の名 12 語の出現は 0。`bar_rules.py` は核を import しないが、作業者が書いたと自分で書いており、独立の参照ではない(i4-r2-01)。`tests/bt/item_4/reference/` の import は `bot.bt.reference.*` と外部の道具(backtesting.py)の比較だけ。核の写しは見つけていない。

## 7. 場面係の申告の裏取り(L-448、監査 64-6)

- `git diff --name-only HEAD` → `docs/AUDITOR/TRACE/2026-09-26_220780c0.json` だけ(リードのフックの記録)。`git status --short` は同じ 1 件と、資料係の materials・表(未追跡)。場面係と作業者の変更はリードのコミットに入っているので、第 1 周の記録のコミット 4869667 から HEAD までの差分を見た: 場面集の外の変更は作業者の持ち物(`src/bot/bt/compat/`・`reference/`・`pipeline.py`・`tests/bt/item_4/`)と docs の記録で、場面係が `src/bot/bt/` に触れた形跡は無い(誰が書いたかは git に残らないので、持ち物の区分で読んだ)。
- 場面集の試験: 1 件落ちる(i4-r2-09)。場面係の申告の時点(d703870 の台本)では通ることを確かめた。

## 8. リードに渡す事実(指摘ではない)

- 要件 §1(b) は最後の段(I4-20)の条件を「この周の批評家の [止める] が 0 件」にし、項目 4 の上限は 2 周(L-454)。この周の [止める] は 0 ではないので、この起動の中で最後の段を行う周は無い(作業者の ROOTCAUSE.md §7-5 と同じ)。旧の 3 本は置き換えられていない。

## 9. 提出前の吟味(批評家の文)

- 指摘ごとに根拠を自分で再現した: i4-r2-02・03・04・05 は私の試験が落ちることを走らせて確かめた(`tests/bt/critic/item_4/` の全体で 10 failed, 67 passed)。i4-r2-03 の JPX の 2 升は最初、実行の段のデータの異常の断りで通っていた(出所の規則ではない理由)。出所の規則は計画で検めるので、計画だけで判定する形に直して 6 件とも落ちることを確かめた。i4-r2-06 は `_check_fill` をコマンドで叩いた。i4-r2-08 の D3 は spec と legacy を 2 通りの足で走らせた。i4-r2-09 は台本の 2 つの版に格子を当てた。
- 格付け: 要件の文(I4-1・I4-5・I4-6・I4-13)に反する・試験が落ちる・場面集の規則 4・6 に反するものを [止める]。i4-r2-10・11 は前の周の [直す] を見直し、要件の列挙に無い(10)・場面集の欠けだが核は正しく断る(11)ので [直す] のまま。
- 相手の付け違い: 実装の直しが要るもの(01・02・03・05・06)は fix_files に `src/bot/bt/` を入れ、実装と付けた。02・06 は場面集の直しも要るので場面集のファイルも fix_files に入れた。04・07・08・09・11 は `tests/bt/battery/` の下だけ。
- 場当たりの直しは見つけていない(場面の id や場面集の語で分ける分岐は `grep` で 0)。全部 patchwork = false。
- 射程(L-445)の外の反例は出していない。
