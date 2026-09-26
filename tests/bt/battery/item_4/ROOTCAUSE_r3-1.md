# 項目 4 場面集の第 r3-1 回の直し(仕上げの第 1 段)— 根本原因と主張の表

場面係が書く。仕上げの委任文 `docs/DATA/delegations/20260926_backtest_env_finish.md`(指紋 ec283fb43be1)と親の委任文(指紋 388d55cdeb32)の
§3「場面集の規則」1〜9・「提出前の吟味」・記録の規則・§4 に従う。第 2 周の批評家の指摘の逐語は
`docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_2/CRITIC.md`。記録は `<M>` = `docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r3-1/`
(仕上げの委任文 §3 の置き場所 `…/item_4/round_3/materials/scenekeeper/` にも「直す前に落ちる」記録を写した)。

**開示(手順の順)**: この文書は直しを始めたあとに書いた。「直す前に落ちる」記録(`<M>/before_fix_pytest.txt`、12:17:17 UTC)は場面集を
1 行も変える前に取ったが、根本原因と主張の表を先に書く手順(親の委任文 §3)は守れていない。基準 `<M>/baseline_at_start.json` も着手時に
`diff_scope.py --baseline-out` で取っておらず、着手の直後(12:10 UTC ごろ)に打った `git status --short` の出力が空だったこと(作業木は
HEAD 658582d と同じ)を、あとから同じ形に書き写したもの(`entries` が空、`head` = 658582d。HEAD はその後動いていない:
`git reflog -1` = `658582d HEAD@{2026-09-26 12:09:07 +0000}`)。`taken_at_utc` は書き写した時刻で、着手の時刻ではない。

## 0. 対応表(CLAUDE.md §0.1)

| やろうとすること | 原文の該当語(逐語) |
|---|---|
| R-O1 / R-H3 の文と i4-13-stop-on-time-bar・同 -maker の正解を時の順に直す | 仕上げの委任文 §1 i4-r2-02「**R-O1 の順(始値の出来事が先)を正とし、R-H3 の「同じ足で先に見るのは逆指値だけ」は始値より後の範囲の中での順と読み直す(場面係が規則の文と正解を直す…)**」 |
| R-M・R-E の規則を足し、値の場面と 2 出力の場面を置く | §1 i4-r2-08「**場面係が規則の文(R-M・R-E)を足し、場面を置く**」「**マスク False の合図は指値を置かない(取り逃しに数えない)**」「**同じ向きの合図は指値を置き直さない(古い指値を残す)**」 |
| `gen_considered.py` の照合を括弧を挟んでも当たる形にし、該当の行を「再現できない」に直す | §1 i4-r2-04「**場面係が `gen_considered.py` の照合を直し(括弧を挟んでも UNVERIFIED に当たる形)、該当の行を「再現できない」に直す**」 |
| PineForge の構築し直しを試み、止めるなら実測と「比べていない(理由)」を書く | §1 i4-r2-07「**容量か時間で止めるなら `df` の実測と打ったコマンドを記録し、検討表と表の注記に「比べていない(理由)」と書く**」 |
| `_inside_by_text` を委任文の除外の文に合わせる | §1 i4-r2-09「**場面係は `test_battery_item4_diffscope.py` の `_inside_by_text` をこの文書の文に合わせる(台本に合わせるのではなく、文書の文に合わせる)**」 |
| 足した・直した場面を動かせた道具・再現の全部に通し、survey_results を直す | 親の委任文 §3 場面集の規則 4「**動かせた道具は全部の場面に通す。**」 |
| 時間切れの足の逆指値を別の出来事 `stop@time` として持つのをやめ、範囲の逆指値 1 つにまとめる(下の §3-1) | **(該当語なし)** — 直し方の決め(R-H3 の読み直し)から導いた作りの変更。場面の正解と規則の文は決めのとおりで、変えたのは場面集の中の順の表し方だけ。リードに聞くこと 1 |
| 2 出力の場面 i4-13-stop-on-time-bar-two-models を足す | **(該当語なし)** — 起こし文は「legacy と spec の 2 出力の場面はそのまま」。既存の 2 出力の場面は変えていない。足したのは、(time, stop) の組が仕様と互換で順が違う組になり、既存の試験 `test_every_order_pair_is_pinned` が互換の側の固めを求めたため。リードに聞くこと 1 |

## 1. 直す前の再現(コマンドと出力)

`<M>/before_fix_pytest.txt`(12:17:17 UTC、HEAD 658582d):
`PYTHONPATH=src timeout 900 python -m pytest tests/bt/battery/item_4 tests/bt/critic/item_4 --basetemp=<scratchpad>/bt/finish_scene_basetemp -p no:cacheprovider -o tmp_path_retention_policy=none`
→ `13 failed, 224 passed`。場面集の側の 2 件: `test_battery_item4_diffscope.py::test_check_matches_delegation_text_on_grid`(i4-r2-09)・
`tests/bt/critic/item_4/test_i4r2_considered_unread_is_not_confirmed.py::test_no_confirmed_absence_rests_on_an_unread_part`(i4-r2-04)。
残りの 11 件は実装の側(i4-r2-02 の `test_i4r2_time_exit_at_the_open.py` 2 件・i4-r2-03 の 6 件・i4-r2-05 の 3 件)。
直す前の 2 場面の正解(98)は `<M>/scenes_i4-13-stop-on-time-bar_at_HEAD.txt`。

## 2. 根本原因(指摘ごと)

- **i4-r2-02(R-H3)**: 規則の文 R-O1 の ② が「足 j が b + N なら足 j の範囲の逆指値、無ければ時間切れ」と書き、始値の出来事(時間切れ)の中に
  範囲の出来事(逆指値)を入れていた。R-O1 自身の原則(始値の出来事は範囲より先)と食い違う文を、場面集の順の表(`ORDER_SPEC`)が
  別の出来事 `stop@time` として写し取り、正解 98 がその表から「導かれた」ので、機械の検査(`test_every_close_is_the_winner_of_its_bar`)は
  食い違いを見つけられなかった。**根 = 規則の文の食い違いを、機械が別名の出来事で固めていた**(機械は文を写すだけで、文の原則との
  矛盾は検めていなかった)。
- **i4-r2-08(maker の R-E・R-M)**: 規則の文が maker の建ての経路のうち「マスク False の合図」と「待っている建ての指値と同じ向きの合図」を
  決めていなかった。前の回の規則の文は、既存の文書と既存の計算にある分岐(R-M1〜R-M5・R-E1〜R-E3)を書き写しただけで、入力の空間
  (合図 × 待っている指値 × マスク)を全部並べて文の有無を検めていなかった。
- **i4-r2-04(読んでいない部分)**: `gen_considered.UNVERIFIED` が 3 語の部分文字列で、「読んだ範囲(ファイル名)に無い」のように語の間に
  何かが挟まる形を見逃した。場面集の試験 `test_considered_rows_rest_on_verified_absence` も同じ 3 語の部分文字列で検めていた(同じ根)。
- **i4-r2-07(PineForge)**: 項目 2 の構築物と driver の source が scratchpad から消え、場面集の側の記録(RUNNABILITY.tsv)にも driver の
  source が無かった(項目 0 の driver は導入記録に source があったが、項目 2 の driver には無い)。消えた後に構築し直す手順が無かった。
- **i4-r2-09(台本と委任文)**: 場面集の試験の答え(`_inside_by_text`)は委任文の文から書いたもので、リードが台本に足した除外が委任文に
  無かった。仕上げの委任文 §3 に除外の文が置かれたので、試験の答えをその文に合わせる。

## 3. どの作りを変えるか

1. **順の表し方**: 出来事 `stop@time` を消し、時間切れの足の逆指値も範囲の逆指値 `stop`(④)にした(`i4_scenes.py:204-216・280`)。
   仕様の順 = 始値の出来事(wick・time・signal)→ 範囲の出来事(stop・tp・mtp・limit)。互換の順(L-5)= wick → stop → tp → mtp → time →
   signal → limit(時間切れの足でも範囲の逆指値が先 = 既存の計算)。これで「時間切れの足の逆指値」は別名の特例ではなく、(time, stop) の
   組が仕様と互換で順の違う組の 1 つになり、既存の機械(組の固め・入れ替えの試験・規則の文から書いた表 PROSE_SPEC / PROSE_LEGACY)が
   そのまま検める。
2. **規則の文**(`gen_definitions.py`): R-H3・R-O1 を決めの文に直し、R-M6・R-E4・L-6・L-7 を足し、R-M5 に「置かなかった・置き直さなかった指値は
   数えない」を足した。組の数(16)は `order_pairs()` から刷る(手で書かない)。
3. **照合**(`gen_considered.py:205・222`): 読んでいない・確かめていないの言い方を正規表現 1 つにし(間に何が挟まっても当たる)、場面集の
   試験(`test_considered_rows_rest_on_verified_absence`)も同じ照合器を使う。
4. **PineForge の adapter**: driver が無いときは、全部の場面の理由の先頭に「比べていない(理由)」を置く(`pineforge_adapter.py:49-60・128`)。
5. `_inside_by_text` に仕上げの委任文 §3 の除外の文(逐語をコメントに置いた)を足した。

## 4. 主張の表(この直しが触る主張の族)

| 族 | 導く関数 | 手書きが残る部分と機械で導けない理由 | 手書きの主張が 1 つでも残っていれば落ちる試験 | 主張を作る機械への mutant の試験 |
|---|---|---|---|---|
| A 同じ足の中の順(R-O1・R-H3・L-5) | `i4_scenes.exit_events`・`winner`・`exit_fill`・`ORDER_SPEC`・`ORDER_LEGACY` | 順そのもの(規則の文)は決めで、機械で導けない。規則の文から独立に書いた表 PROSE_SPEC / PROSE_LEGACY が手書き | `test_every_close_is_the_winner_of_its_bar`・`test_every_order_pair_is_pinned`(仕様と互換の両方)・`test_order_matches_the_rule_text`・`test_exit_events_grid` | `test_swapping_any_pair_of_the_order_breaks_a_scene`(16 組の全部で、順を入れ替えると場面の正解と食い違う。(time, stop) の組を含む) |
| I maker の建ての経路(R-M1〜R-M3・R-M6・R-E2・R-E4、L-6・L-7) | `test_battery_item4_claims._maker_entries`(規則の文だけから書いた建ての経路の導出。建ての経路だけの場面を機械で選ぶ `_entry_path_scenes`) | 場面の正解(`i4_scenes.py` の trade の並び)は手で置いた。導出の範囲は「maker・出口の設定なし・BUY だけ」で、決済の指値と出口は族 A が見る(試験のファイルに書いた) | `test_maker_entry_scenes_follow_the_rule_text`(仕様の答えは R-E4・R-M6 で、互換の答えは L-6・L-7 で導出と一致)・`test_legacy_answers_of_two_model_scenes_are_the_existing_engine`(互換の答えを当方の現状を呼んで確かめる) | `test_each_maker_entry_rule_is_pinned_by_a_scene`(R-E4 を外す・R-M6 を外すの 2 通りで場面と食い違う) |
| G 検討表の判断(規則 6) | `gen_considered.verified_absence`・`judge_row` | 理由の文(adapter・再現の理由)は各 adapter の手書き。読んだか否かの語の正しさは批評家が読む | `test_considered_rows_rest_on_verified_absence`・批評家の `test_i4r2_considered_unread_is_not_confirmed.py` | `test_unread_parts_never_count_as_a_shown_absence`(言い方 5 × 間に挟まる物 4 の格子)・`test_the_unread_grid_catches_the_old_substring_matcher`(前の回の照合器を入れると格子が見つける) |
| F 差分の範囲(i4-r2-09) | 台本の `checkBattery`(`diff_scope.run_check_many`) | 答え `_inside_by_text` は委任文の文から手で書く(台本から導くと検査にならない) | `test_check_matches_delegation_text_on_grid` | `test_check_grid_catches_mutants`(既存) |

## 5. 直した記録(直した根拠)

- i4-r2-02: `gen_definitions.py:84-86`(R-H3)・`93-104`(R-O1)、`i4_scenes.py:1399-1415・1445-1452`(正解 101、2 出力の場面)、
  `test_battery_item4.py:36-45`(当方の現状との食い違いの一覧に 3 場面)。
- i4-r2-08: `gen_definitions.py:69-70`(R-M6)・`89-90`(R-E4)・`107-109`(R-M5)・`139-142`(L-6・L-7)、`i4_scenes.py:1194-1247`(5 場面)。
- i4-r2-04: `gen_considered.py:205・222`、`test_battery_item4_claims.py:378`。検討表の変化: 56 zvt・67 lumibot の I4-17 は「再現できない」
  (批評家の挙げた行)。足した場面で「結果なし」以外を返した候補は、その観点で「動かせた / 再現した」に数えが変わった(機械の数え)。
- i4-r2-07: 下の §6-3。
- i4-r2-09: `test_battery_item4_diffscope.py:99-109`。
- 規則 4: 足した・直した 8 場面(i4-13-stop-on-time-bar・同 -maker・同 -two-models・i4-14-maker-mask-false・i4-16-maker-mask-false-not-missed・
  同 -two-models・i4-16-same-side-keeps-limit・同 -two-models)を全 42 対象に通した: `<M>/run_new_scenes.sh`(12:23:25〜12:23:53 UTC、
  全部 rc=0、`<M>/run_new_scenes.log`)。行は `<M>/merge.py` で survey_results に場面の順で差し込んだ(他の行は変えていない)。
  PineForge は adapter の理由を変えたので全 73 場面を通し直した。i4-13-tp-on-exit-bar は文だけ変え、正解は同じなので通し直していない。
- `python3 scripts/check_bt_considered.py tests/bt/battery/item_4/opponents/CONSIDERED.md --write` → `OK 誤り 0 件`。
- `python3 tests/bt/battery/item_4/gen_definitions.py` → `wrote …/DEFINITIONS.md (877 lines)`。

## 6. 提出前の吟味

1. **読み直し**: 仕上げの委任文 §1(i4-r2-02・04・07・08・09 の決め)、第 2 周の CRITIC.md の i4-r2-02・04・07・08・09、場面集の規則 1〜9。
2. **同じ根の全箇所**: (a) R-H3 の旧い読み(「同じ足で先に見るのは逆指値だけ」)を使っていた文: i4-13-tp-on-exit-bar の what・how(直した)、
   試験の表 PROSE_SPEC の注記(直した)、`i4_scenes.py` の出来事の注記(直した)。ROOTCAUSE_r2-1.md の記述は当時の記録なので変えない。
   (b) 部分文字列の照合: `gen_considered.py` の判断と `test_battery_item4_claims.py:378` の 2 か所(両方直した)。
   (c) 規則の文の空き(入力の空間に文の無い所)は、maker の建ての経路について `_maker_entries` の格子で見た。**見ていない空き**: 売りの
   建て・CLOSE を含む maker の経路の全組(合図 × 待っている指値の向き × 建玉 × マスク)。R-M3 と R-E4 が重なる所(待っている買いの指値に、
   マスク False の売りの合図)の文は無い(リードに聞くこと 2)。
3. **試験**: 下の返り値の (b)。
4. **厳しい批評家なら何を [止める] にするか**: (i) 「2 出力の場面を足したのは起こし文の『そのまま』に反する」→ 既存の 2 出力の場面は 1 行も
   変えていない。足したのは組の固めに要る 1 つで、対応表に「該当語なし」と書いてリードに聞く。(ii) 「PineForge は規則 4 違反のまま」→ 止めた
   理由と実測を検討表・survey_results の全 73 行に書いた。比べていないことは通過の判定の外に出さない(リードに聞くこと 3)。(iii) 「基準を
   着手時に取っていない」→ 上の開示。(iv) 「新しい場面が相手に不利な向き」→ 新しい 8 場面で「正解と一致」を返した相手は 13(backtesting.py・
   Backtrader・Basana・PyAlgoTrade・vn.py・再現 7 件ほか。survey_results)。同じ向きの合図の場面は全部の相手が「不一致」で、どの相手も置き直す
   (L-7 と同じ)。規則 R-M6 の値はリードの決めで、決めの開示(仕上げの委任文 §1 i4-r2-08)どおり、同じ文を 2 者が実装した一致に留まる。
5. **場当たりの直しでないか**: 試験だけの特別扱いはしていない。2 場面の正解は規則の文から出る値(機械の検査 A が文から導いた値と照らす)。
6. **敵対者の格子を先に書いたか**: 族 I・G2 の格子は直しのあとに書いた(順は守れていない)。格子は規則の文から書き、直す前の照合器を
   入れると落ちることを mutant の試験で確かめた。

### 6-3. PineForge(候補 70)の構築し直し(i4-r2-07)

- 打ったコマンド(`<M>/pineforge/rebuild_70.sh`、記録 `<M>/pineforge/rebuild_70.log`): `git clone --depth 1 https://github.com/pineforge-4pass/pineforge-engine.git
  <venvs>/item_2/src/c70`(12:12:21 UTC)→ `cmake -B build -S . -DCMAKE_BUILD_TYPE=Release -DPINEFORGE_BUILD_TESTS=OFF && cmake --build build -j4`
  (12:12:28〜12:14:24 UTC、`build/lib/libpineforge.a`・`libpineforge_kernel.a` ができた)。
- `df -m /` の実測: 開始 2,046 MB 空き(12:12:21)、clone 後 1,992 MB、構築後 1,935 MB、`<M>/pineforge/df_after.txt`。**容量でも時間でも止めていない。**
- **止めた理由**: clone が返した版は `0d76a099…`(2026-09-26 06:03 +08:00)で、項目 0・2 が検査して入れた `5e62602c` ではない。この版は導入前の
  検査(道具サーベイ §6。親の委任文 §4)を通していない。**私は検査をせずに CMake の構築まで走らせた(CMake の FetchContent も外から取る)。これは
  §4 の手順から外れた。**項目 2 の driver の source は残っていなかったので、項目 0 の導入記録の driver と項目 2・4 の adapter の呼び方から
  書き直した(`<M>/pineforge/i2drv70.c`、翻訳していない)。その次の操作を、この環境の許可の判定が `[Code from External]` として止めたので、
  driver の翻訳と実行に進んでいない。道具は 1 度も呼んでいない。
- 検討表の 70 の行・RUNNABILITY.tsv の 70 の行・survey_results/opp_pineforge.tsv の全 73 行の理由に「比べていない(理由)」を書いた。
- 残した物: 検査を通していない版の clone と構築物が `<venvs>/item_2/src/c70` にある(消していない)。driver の source は `<venvs>/item_2/drivers/i2drv70.c`。

### 6-4. リードの答えのあと(12:35 UTC〜)

- **(1)** `stop@time` をまとめたこと・2 出力の場面を足したことはリードが認めた。
- **(2)** 待っている建ての指値に、マスク False の反対向きの合図が来たとき = 古い指値を残す(リードの決め)。規則の文 R-E4 に補いを足し
  (`gen_definitions.py` の R-E4 の 3 行目)、互換の計算 **L-8**(旧エンジンは置き換えて取り逃しに 1 を足し、置き換えた指値が通過しても建てない)を
  足した。場面 i4-16-mask-false-opposite-keeps-limit(値)・i4-16-mask-false-opposite-two-models(2 出力)を足した。L-8 の互換の答えは旧エンジンを
  呼んで確かめた(`test_legacy_answers_of_two_model_scenes_are_the_existing_engine` が通る)。建ての経路の導出 `_maker_entries` を売りの建てと
  R-M3・R-E4 の重なりに広げた(`test_maker_entry_scenes_follow_the_rule_text` の対象 7 場面)。2 場面を全 42 対象に通した(`<M>/run_new_scenes2.sh`、
  12:37:54〜12:38:14 UTC、全部 rc=0)。
- **(3)** PineForge: 検査していない版 0d76a099 の clone と構築物を消し、検査した版 5e62602c を `git fetch --depth 1 origin
  5e62602cb1ebaff9ec16d7dfbbfaaaff08603764` で取り直した(12:36:06 UTC、HEAD = 5e62602cb1ebaff9ec16d7dfbbfaaaff08603764、`df -m /` の空き 1,881 → 1,943 MB、
  記録 `<M>/pineforge/refetch_70.log`)。次の手(前の検査の記録 = 項目 0 の導入記録を読み、構築・実行へ進む)を、この環境の許可の判定が
  `[Code from External]` としてもう一度止めた。許可の判定は「同じ結果を別の手で追わない」と言うので、ここで止めた。**PineForge は比べていない**
  (理由は検討表・RUNNABILITY・survey_results の全 75 行)。取り直した 5e62602c の clone(構築していない)は `<venvs>/item_2/src/c70` に残っている。
  **自己申告(§4 から外れたこと)**: 最初の版 0d76a099 を、導入前の検査をせずに CMake で構築した(FetchContent の取得を含む)。その版は実行していない。
- **(4)** 記録は両方の置き場所に置いた。

### 6-5. 第 2 段(リードの指示 12:39 UTC ごろ: U1〜U8 を規則の文に、参照を bar_sim に)

- **根本原因**: 規則の文は、既存の文書と計算にある分岐だけを書き写し、入力の空間のうち「文が決めていない所」を列べていなかった(§2 の
  i4-r2-08 と同じ根)。独立の参照を文だけから書いた役が、その空きを U1〜U8 として見つけた。
- **規則の文**(`gen_definitions.py`): R-M7・R-W5・R-W6・R-E5・R-V1〜R-V4 を足し、入力の形に「使わない物は null」を書いた。
- **場面**: 11 を足した(definitions_review.md の第 2 段の節)。場面集の機械も文に合わせた: `i4_scenes._closing_limit` は仕様では待っている決済の
  指値を寿命まで残す(R-M7)、互換では最後の合図で置き直す(L-7)。`_maker_entries` は向き・空売りの止めを R-E5 として扱う。
- **主張の表に足した行**: (族 A)R-M7 = 導く関数 `_closing_limit`、落ちる試験 `test_every_close_is_the_winner_of_its_bar`、mutant
  `test_the_kept_closing_limit_is_pinned_by_a_scene`(仕様を置き直しに・互換を残すに変えると場面と食い違う)。(族 I)R-E5 = `_maker_entries`、
  `test_maker_entry_scenes_follow_the_rule_text`・`test_each_maker_entry_rule_is_pinned_by_a_scene`。(新しい族 V)場面の足そのものが R-V1 を
  満たすこと = `test_every_accepted_scene_bar_holds_its_open_and_close`(対照・格子の全部の足。拒む変形だけを除く)。**この試験は、私が最初に
  書いた場面 XS の足 4(高値 101 < 終値 101.5)を見つけた**(新実装が「bar invariant violated」で拒んだので気づき、足を直し、同じ誤りが
  場面集の他に無いことをこの試験で確かめた)。
- **参照の切り替え**: `adapters/new_impl.py:_run_reference` を `bar_sim.run_bars` にした(入口は SPEC.md §7、options の鍵は場面の config と同じ名、
  capital・order_amount は initial_equity・order_notional から)。参照は指標を持たないので、I4-1 の 2 場面の参照の側の判定から指標を外した
  (`i4_scenes.W_E_REF`。本体の側は指標も判定する)。**これは場面の判定の変更で、リードの指示の語に無い**(リードに聞くこと 5)。
- **規則 4**: 第 2 段の 11 場面と、参照の判定を変えた 3 場面を全 42 対象に通した(`<M>/run_new_scenes3.sh`、12:45:47〜12:47:04 UTC、全部 rc=0)。
- **新実装が「不一致」の 4 場面**(新実装の側で直す物): i4-14-sides-opposite-keeps-limit・同 -two-models(R-E5: 向き long で止められた SELL で
  買いの指値を置き換えている = 約定 0)、i4-10-zero-rate-refused(R-V2: 率 0 を拒まない)、i4-16-zero-timeout-refused(R-V4: 寿命 0 を拒まない)。

### 6-6. 第 3 段(i4-r2-06 の場面集の側。リードの指示 13:29 UTC ごろ、期限 14:05 UTC)

- **やったこと**: 統合の 5 場面(i4-5-fills・i4-5-outputs・i4-6-label・i4-6-signal-refused・i4-6-research-refused)の宣言を新しい形にした
  (`i4_scenes.py` の PIPE_FILL・PIPE_LATENCY・PIPE_COSTS・PIPE_ACCOUNT・銘柄の product と rules・事前登録のファイル PREREG_FILE)。形の語は
  `plan_pipeline` の本体と `tests/bt/item_4/i4w_decl.py` を読んで写した(import はしていない)。
  - i4-6-research-refused: 対照 2 = 目的「研究」+ 事前登録のファイル、変形 = 事前登録なし。
  - i4-6-signal-refused の対照 2: ファイルを合成と宣言する口が無くなった(合成は種つきの生成器からだけ)。そこで「同じファイルに目的『研究』
    (事前登録のファイルつき)で値の条件の戦略を通せば通る」に置き換えた(対象が値で条件づけた戦略を走らせられることを示す対照の意味は同じ)。
    **これは場面の対照の変更で、指示の語に無い**(リードに聞くこと 7)。
  - adapter `_pipeline` を新しい引数(latency・account・prereg)にし、約定と損益を約定の幅の**両側**(`res.range`)から `<側>:<銘柄>` の鍵で返す。
  - 正解は両側とも F-1(注文の時刻以後に最初に観測した値)の**ままにした**(下の理由)。`both_sides` で両側に同じ正解を置いた。
- **正解を出し直せなかった理由**: 新しい統合の口を場面のファイルに通した出力(`<M>/stage3_probe_pipe.py`・`.out`)は、F-1 と次の 4 点で違う。
  どれも、項目 2 の規則の文(`tests/bt/battery/item_2/DEFINITIONS.md`)から場面係が 1 つに決められなかった(`market_ref` の `last_trade` /
  `next_bar_open` の語は項目 2 の DEFINITIONS.md に無い: `grep -n -i 'market_ref\|last_trade\|next_bar_open'` の結果は 0 行)。**出力を正解に写すのは
  場面集の規則(正解は対象を見ずに手で出す)に反するので、写していない。**
  1. 時刻 T0 の最初の買いは、5 銘柄とも両側で約定しない(T0 より前に観測が無い)。F-1 では最初の観測で約定する。
  2. bf(板つき)の成行は板を歩く(売り 1.0 = 買いの気配 15000000 から 5 刻みで 0.1 ずつ 10 段、買い 1.0 = 売りの気配 15000010 から 0.2 ずつ 5 段)。
     悲観の側も同じ(指示の文「悲観 = 直前の約定 ± スプレッド」と違う)。
  3. binance・FX ティックの成行は、注文の時刻**以前**の最後の約定・気配で埋まる(binance の売り 96010 = 300 秒より前の最後の約定)。F-1 は以後の最初。
  4. 足(JPX・FX の 1 分足)の成行は、300 秒の注文が 420 秒に始まる足の始値で埋まる(F-1 は 300 秒に始まる足の始値)。
  5. 楽観・悲観の両側が同じ値(成行には tier が効かない)。
- **試験**: 場面集の側は全部通る。批評家の `test_i4r1_pending_signal_before_intrabar_exit.py` の 12 件が落ちる(`ModuleNotFoundError:
  bot.bt.reference.bar_rules`。第 2 段で作業者が bar_rules.py を消したため。場面集の規則 8: 批評家の試験は変えない)。
- **規則 4**: 5 場面を全 42 対象に通した(new_impl は 13:32:48〜13:45 UTC、他の 41 は `<M>/run_new_scenes4.sh` 13:46:08〜13:49:34 UTC、全部 rc=0)。
  新実装と mutant は 5 場面とも「不一致」(上の 1〜5)。他の 40 対象は 5 場面とも「結果なし」。

### 6-7. 第 3 段の続き(リードの答え 13:53 UTC ごろ: 統合の口の規則 I-1〜I-5)

- 規則の文(`gen_definitions.py` の「統合の場面」)に I-1〜I-5 を足し、F-1 を「I-1・I-2・I-4 と悲観の側の I-3 をまとめた形」と書き直した。
- 正解を手で出し直した(出力は写していない): 悲観の側と板の無い銘柄の楽観の側 = F-1(`_PF`、I-1・I-2・I-4・I-5)。bf の楽観の側 = I-3 で板を歩く
  (`i4_scenes.walk_board`: 注文の時刻以後の最初の板の写しを、買いは売りの気配の良い方から、売りは買いの気配の良い方から数量の分だけ)。
  損益は `<側>:<銘柄>` ごとに 売り − 買い(bf の楽観 = -85、悲観 = 2000)。
- **場面の入力の変更(開示)**: 01:05 の売りの後に板の写しが無かった(板は 00:00:10・00:05:01・01:00:01 の 3 つ)ので、I-3 の「以後の最初の板の写し」が
  無い注文ができていた。01:05:02 の板の写しを 1 つ足した(`_BOARD_T`)。読んだ事象の数の正解(bf_board 4)と sha256 は場面のファイルから刷る。
  **指示の語に無い変更**(リードに聞くこと 9)。
- 値で条件づけた戦略の対照(i4-6-signal-refused の対照 2)の楽観の側も、同じ注文を I-3 で板に歩かせて出した(`_PR_FILLS2`)。
- 試験: `test_pipeline_book_walk_matches_the_board_file` を足した(場面が書く板のファイルを読み直して、板の歩き方の正解を別に導き直す)。
- リードの答え: i4-6-signal-refused の対照 2 の置き換え = 認める。I4-1 の参照の側から指標を外すこと = 認める。PineForge = 比べていないのまま。

## リードに聞くこと

1. 出来事 `stop@time` を消して範囲の逆指値 1 つにまとめたこと、と、2 出力の場面 i4-13-stop-on-time-bar-two-models を足したことは、起こし文と
   仕上げの委任文に語の無い作りの変更です(上の対応表の「該当語なし」の 2 行)。直し方の決め(R-H3 の読み直し)から導きましたが、よいか。
2. R-M3(反対向きの合図は置き換えて取り逃しに数える)と R-E4(マスク False の合図は指値を置かない)が重なる所 = 待っている建ての指値に、
   マスク False の反対向きの合図が来たとき、古い指値を残すか・消して取り逃しに数えるかの文がありません。決めてもらえれば文と場面を足します。
3. PineForge: `5e62602c` を取り直して(`git fetch --depth 1 origin 5e62602cb1ebaff9ec16d7dfbbfaaaff08603764`)項目 0・2 の検査の記録をそのまま当てて
   構築・実行してよいか、それとも「比べていない」のまま進めるか。検査を通していない版の clone と構築物(`<venvs>/item_2/src/c70`)を消すかどうか。
4. 「直す前に落ちる」記録の置き場所: 起こし文は `battery/materials/r3-1/`、仕上げの委任文 §3 は `round_3/materials/<役>/`。両方に写しました。
   (1〜4 はリードが答えた = §6-4。)
5. 参照 bar_sim は指標の式を持たないので、I4-1 の 2 場面の参照の側の判定から指標を外しました(本体の側は指標も判定)。これでよいか。
   別の案は、参照の役に指標の式 M-1〜M-12 を足してもらうこと。
(5〜8 はリードが答えた = §6-7。)
7. i4-6-signal-refused の対照 2 を「合成と宣言したファイル」から「同じファイルを目的『研究』(事前登録のファイルつき)で」に変えた(§6-6)。これでよいか。
8. 統合の 5 場面の正解(§6-6 の 1〜5): 成行の参照(注文の時刻以前の最後の観測か、以後の最初か)・最初の観測より前の注文・板を歩くか・
   足の成行が何本目の始値か・悲観の側の成行の値、を項目 2 のどの規則の文で決めるかを示してほしい。文が決まれば手で出し直す。
9. 統合の場面の板の写しを 01:05:02 に 1 つ足した(§6-7)。これでよいか。
6. PineForge は検査した版 5e62602c を取り直しましたが、構築・実行へ進む操作をこの環境の許可の判定が止めました。進めるには、オーナーが
   この種の操作の許可の規則を足す必要があります(許可の判定の文: 「the user can add a Bash permission rule to their settings」)。

## 7. 末尾の節の読み方(節の外の散文)

- この回に私(場面係)が書いたのは `tests/bt/battery/item_4/` の下と、記録 `<M>` と `docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/scenekeeper/`
  だけ。節の「検査が止める行」の `src/bot/bt/…`・`tests/bt/item_4/…` は、同じ時刻に並行して動いている作業者と参照実装の役の持ち物で、私は書いていない
  (git はコミットされていない変更の書き手を記録しないので、節の中では導いていない)。`docs/AUDITOR/TRACE/` はリードのフックの痕跡で、仕上げの委任文
  §3 の除外の文により場面集の外に数えない(台本の checkBattery も数えていない)。
- 基準の書き写しについては冒頭の開示。

## `git diff --name-only HEAD` の節(`diff_scope.py` が作った。手で変えない)

<!-- diff_scope:begin sha256=c5f85df79d365386bc33553016041eb1bc904c4bfcea63c34ce6e0f035b4f4ac -->
```text
HEAD: fa82126eab3d289e2433befa65f226108334976b

$ git diff --name-only HEAD
docs/AUDITOR/TRACE/2026-09-26_220780c0.json
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/ROOTCAUSE_worker.md
src/bot/backtest/engine.py
src/bot/backtest/metrics.py
src/bot/backtest/walk_forward.py
src/bot/bt/compat/engine.py
src/bot/bt/reference/bar_rules.py
tests/bt/battery/item_4/DEFINITIONS.md
tests/bt/battery/item_4/ROOTCAUSE_r3-1.md
tests/bt/battery/item_4/adapters/new_impl.py
tests/bt/battery/item_4/gen_definitions.py
tests/bt/battery/item_4/i4_scenes.py
tests/bt/battery/item_4/survey_results/current_impl.tsv
tests/bt/battery/item_4/survey_results/mutant.tsv
tests/bt/battery/item_4/survey_results/new_impl.tsv
tests/bt/battery/item_4/survey_results/opp_backtesting.tsv
tests/bt/battery/item_4/survey_results/opp_backtrader.tsv
tests/bt/battery/item_4/survey_results/opp_basana.tsv
tests/bt/battery/item_4/survey_results/opp_bt.tsv
tests/bt/battery/item_4/survey_results/opp_fast_trade.tsv
tests/bt/battery/item_4/survey_results/opp_finmarketpy.tsv
tests/bt/battery/item_4/survey_results/opp_freqtrade.tsv
tests/bt/battery/item_4/survey_results/opp_hftbacktest.tsv
tests/bt/battery/item_4/survey_results/opp_luczinsritter.tsv
tests/bt/battery/item_4/survey_results/opp_pineforge.tsv
tests/bt/battery/item_4/survey_results/opp_pm_backtester.tsv
tests/bt/battery/item_4/survey_results/opp_pyalgotrade.tsv
tests/bt/battery/item_4/survey_results/opp_pybotters.tsv
tests/bt/battery/item_4/survey_results/opp_pybroker.tsv
tests/bt/battery/item_4/survey_results/opp_pysystemtrade.tsv
tests/bt/battery/item_4/survey_results/opp_pytrendfollow.tsv
tests/bt/battery/item_4/survey_results/opp_qflib.tsv
tests/bt/battery/item_4/survey_results/opp_qlib.tsv
tests/bt/battery/item_4/survey_results/opp_qstrader.tsv
tests/bt/battery/item_4/survey_results/opp_qtradex.tsv
tests/bt/battery/item_4/survey_results/opp_quanttrader.tsv
tests/bt/battery/item_4/survey_results/opp_repro_11_octobot.tsv
tests/bt/battery/item_4/survey_results/opp_repro_15_backtestingcore.tsv
tests/bt/battery/item_4/survey_results/opp_repro_52_lean.tsv
tests/bt/battery/item_4/survey_results/opp_repro_56_zvt.tsv
tests/bt/battery/item_4/survey_results/opp_repro_57_wondertrader.tsv
tests/bt/battery/item_4/survey_results/opp_repro_60_hikyuu.tsv
tests/bt/battery/item_4/survey_results/opp_repro_61_barter.tsv
tests/bt/battery/item_4/survey_results/opp_repro_67_lumibot.tsv
tests/bt/battery/item_4/survey_results/opp_repro_69_gobacktest.tsv
tests/bt/battery/item_4/survey_results/opp_repro_7_superalgos.tsv
tests/bt/battery/item_4/survey_results/opp_repro_80_hummingbot.tsv
tests/bt/battery/item_4/survey_results/opp_repro_8_opentrader.tsv
tests/bt/battery/item_4/survey_results/opp_repro_94_mote.tsv
tests/bt/battery/item_4/survey_results/opp_rqalpha.tsv
tests/bt/battery/item_4/survey_results/opp_vectorbt.tsv
tests/bt/battery/item_4/survey_results/opp_vnpy.tsv
tests/bt/battery/item_4/survey_results/opp_ziplime.tsv
tests/bt/battery/item_4/survey_results/opp_zipline_reloaded.tsv
tests/bt/battery/item_4/test_battery_item4.py
tests/bt/item_4/i4w_drive.py
tests/bt/item_4/test_i4_r2_signal_at_open_grid.py
tests/bt/item_4/test_i4_spec_vs_reference_grid.py

$ git status --porcelain --untracked-files=all
 M docs/AUDITOR/TRACE/2026-09-26_220780c0.json
 M docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/ROOTCAUSE_worker.md
 M src/bot/backtest/engine.py
 M src/bot/backtest/metrics.py
 M src/bot/backtest/walk_forward.py
 M src/bot/bt/compat/engine.py
D  src/bot/bt/reference/bar_rules.py
 M tests/bt/battery/item_4/DEFINITIONS.md
 M tests/bt/battery/item_4/ROOTCAUSE_r3-1.md
 M tests/bt/battery/item_4/adapters/new_impl.py
 M tests/bt/battery/item_4/gen_definitions.py
 M tests/bt/battery/item_4/i4_scenes.py
 M tests/bt/battery/item_4/survey_results/current_impl.tsv
 M tests/bt/battery/item_4/survey_results/mutant.tsv
 M tests/bt/battery/item_4/survey_results/new_impl.tsv
 M tests/bt/battery/item_4/survey_results/opp_backtesting.tsv
 M tests/bt/battery/item_4/survey_results/opp_backtrader.tsv
 M tests/bt/battery/item_4/survey_results/opp_basana.tsv
 M tests/bt/battery/item_4/survey_results/opp_bt.tsv
 M tests/bt/battery/item_4/survey_results/opp_fast_trade.tsv
 M tests/bt/battery/item_4/survey_results/opp_finmarketpy.tsv
 M tests/bt/battery/item_4/survey_results/opp_freqtrade.tsv
 M tests/bt/battery/item_4/survey_results/opp_hftbacktest.tsv
 M tests/bt/battery/item_4/survey_results/opp_luczinsritter.tsv
 M tests/bt/battery/item_4/survey_results/opp_pineforge.tsv
 M tests/bt/battery/item_4/survey_results/opp_pm_backtester.tsv
 M tests/bt/battery/item_4/survey_results/opp_pyalgotrade.tsv
 M tests/bt/battery/item_4/survey_results/opp_pybotters.tsv
 M tests/bt/battery/item_4/survey_results/opp_pybroker.tsv
 M tests/bt/battery/item_4/survey_results/opp_pysystemtrade.tsv
 M tests/bt/battery/item_4/survey_results/opp_pytrendfollow.tsv
 M tests/bt/battery/item_4/survey_results/opp_qflib.tsv
 M tests/bt/battery/item_4/survey_results/opp_qlib.tsv
 M tests/bt/battery/item_4/survey_results/opp_qstrader.tsv
 M tests/bt/battery/item_4/survey_results/opp_qtradex.tsv
 M tests/bt/battery/item_4/survey_results/opp_quanttrader.tsv
 M tests/bt/battery/item_4/survey_results/opp_repro_11_octobot.tsv
 M tests/bt/battery/item_4/survey_results/opp_repro_15_backtestingcore.tsv
 M tests/bt/battery/item_4/survey_results/opp_repro_52_lean.tsv
 M tests/bt/battery/item_4/survey_results/opp_repro_56_zvt.tsv
 M tests/bt/battery/item_4/survey_results/opp_repro_57_wondertrader.tsv
 M tests/bt/battery/item_4/survey_results/opp_repro_60_hikyuu.tsv
 M tests/bt/battery/item_4/survey_results/opp_repro_61_barter.tsv
 M tests/bt/battery/item_4/survey_results/opp_repro_67_lumibot.tsv
 M tests/bt/battery/item_4/survey_results/opp_repro_69_gobacktest.tsv
 M tests/bt/battery/item_4/survey_results/opp_repro_7_superalgos.tsv
 M tests/bt/battery/item_4/survey_results/opp_repro_80_hummingbot.tsv
 M tests/bt/battery/item_4/survey_results/opp_repro_8_opentrader.tsv
 M tests/bt/battery/item_4/survey_results/opp_repro_94_mote.tsv
 M tests/bt/battery/item_4/survey_results/opp_rqalpha.tsv
 M tests/bt/battery/item_4/survey_results/opp_vectorbt.tsv
 M tests/bt/battery/item_4/survey_results/opp_vnpy.tsv
 M tests/bt/battery/item_4/survey_results/opp_ziplime.tsv
 M tests/bt/battery/item_4/survey_results/opp_zipline_reloaded.tsv
 M tests/bt/battery/item_4/test_battery_item4.py
 M tests/bt/item_4/i4w_drive.py
 M tests/bt/item_4/test_i4_r2_signal_at_open_grid.py
 M tests/bt/item_4/test_i4_spec_vs_reference_grid.py
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r3-1/run_new_scenes4.log
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r3-1/run_new_scenes4.sh
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r3-1/stage3_probe_pipe.out
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r3-1/stage3_probe_pipe.py
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/before_old8_and_compat_at_HEAD_fa82126.log
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/before_old8_and_compat_at_HEAD_fa82126_first_try_without_schema_dir.log
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/compat_engine_before_layer.py
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/old_engine_snapshot/SHA256SUMS
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/old_engine_snapshot/__init__.py
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/old_engine_snapshot/engine.py
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/old_engine_snapshot/metrics.py
?? docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/old_engine_snapshot/walk_forward.py
?? tests/bt/compat/test_replace_layer_grid.py

台本の checkBattery(項目 4、node で台本の文から切り出して走らせた。tests_passed は真として渡す)の指摘:
{"id": "bself-touch", "level": "止める", "repeat_of": null, "text": "場面係の差分に場面集の外のファイルがある(L-448 の機械の検査): docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/ROOTCAUSE_worker.md, src/bot/backtest/engine.py, src/bot/backtest/metrics.py, src/bot/backtest/walk_forward.py, src/bot/bt/compat/engine.py, src/bot/bt/reference/bar_rules.py, tests/bt/item_4/i4w_drive.py, tests/bt/item_4/test_i4_r2_signal_at_open_grid.py, tests/bt/item_4/test_i4_spec_vs_reference_grid.py"}

検査が止める行(場面集の外):
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/ROOTCAUSE_worker.md
src/bot/backtest/engine.py
src/bot/backtest/metrics.py
src/bot/backtest/walk_forward.py
src/bot/bt/compat/engine.py
src/bot/bt/reference/bar_rules.py
tests/bt/item_4/i4w_drive.py
tests/bt/item_4/test_i4_r2_signal_at_open_grid.py
tests/bt/item_4/test_i4_spec_vs_reference_grid.py

記録の上書き(HEAD にある materials の記録が変わっている = 追記だけの規則の破れ):
(無し)

未追跡で場面集の外(git diff に出ないので検査に見えない):
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r3-1/run_new_scenes4.log
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r3-1/run_new_scenes4.sh
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r3-1/stage3_probe_pipe.out
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r3-1/stage3_probe_pipe.py
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/before_old8_and_compat_at_HEAD_fa82126.log
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/before_old8_and_compat_at_HEAD_fa82126_first_try_without_schema_dir.log
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/compat_engine_before_layer.py
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/old_engine_snapshot/SHA256SUMS
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/old_engine_snapshot/__init__.py
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/old_engine_snapshot/engine.py
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/old_engine_snapshot/metrics.py
docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/materials/replace/old_engine_snapshot/walk_forward.py
tests/bt/compat/test_replace_layer_grid.py

引用符つきの path(git の引用の形。場面集の中でも検査は外と読む):
(無し)

基準: docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/battery/materials/r3-1/baseline_at_start.json sha256=8e21b97d40963d8638117fc7255f70770748ff79de1a20c57faf88e152841486
(取った時刻 2026-09-26T12:30:03Z、そのときの HEAD 658582da3168deb8005001cd900a7c8a34cdcf4b。場面係の最初の書き込みとして取った写し)

差分の行ごとの帰属(基準と今の写しの sha256・HEAD から機械で分けた。書き手は git に記録が無いので出さない):
判定できない(HEAD が作業中に変わった)	docs/AUDITOR/TRACE/2026-09-26_220780c0.json
判定できない(HEAD が作業中に変わった)	docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/ROOTCAUSE_worker.md
判定できない(HEAD が作業中に変わった)	src/bot/backtest/engine.py
判定できない(HEAD が作業中に変わった)	src/bot/backtest/metrics.py
判定できない(HEAD が作業中に変わった)	src/bot/backtest/walk_forward.py
判定できない(HEAD が作業中に変わった)	src/bot/bt/compat/engine.py
判定できない(HEAD が作業中に変わった)	src/bot/bt/reference/bar_rules.py
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/DEFINITIONS.md
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/ROOTCAUSE_r3-1.md
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/adapters/new_impl.py
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/gen_definitions.py
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/i4_scenes.py
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/current_impl.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/mutant.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/new_impl.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_backtesting.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_backtrader.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_basana.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_bt.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_fast_trade.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_finmarketpy.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_freqtrade.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_hftbacktest.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_luczinsritter.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_pineforge.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_pm_backtester.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_pyalgotrade.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_pybotters.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_pybroker.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_pysystemtrade.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_pytrendfollow.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_qflib.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_qlib.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_qstrader.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_qtradex.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_quanttrader.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_repro_11_octobot.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_repro_15_backtestingcore.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_repro_52_lean.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_repro_56_zvt.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_repro_57_wondertrader.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_repro_60_hikyuu.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_repro_61_barter.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_repro_67_lumibot.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_repro_69_gobacktest.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_repro_7_superalgos.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_repro_80_hummingbot.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_repro_8_opentrader.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_repro_94_mote.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_rqalpha.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_vectorbt.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_vnpy.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_ziplime.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/survey_results/opp_zipline_reloaded.tsv
判定できない(HEAD が作業中に変わった)	tests/bt/battery/item_4/test_battery_item4.py
判定できない(HEAD が作業中に変わった)	tests/bt/item_4/i4w_drive.py
判定できない(HEAD が作業中に変わった)	tests/bt/item_4/test_i4_r2_signal_at_open_grid.py
判定できない(HEAD が作業中に変わった)	tests/bt/item_4/test_i4_spec_vs_reference_grid.py

検査が止める行の帰属:
判定できない(HEAD が作業中に変わった)	docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/round_3/ROOTCAUSE_worker.md
判定できない(HEAD が作業中に変わった)	src/bot/backtest/engine.py
判定できない(HEAD が作業中に変わった)	src/bot/backtest/metrics.py
判定できない(HEAD が作業中に変わった)	src/bot/backtest/walk_forward.py
判定できない(HEAD が作業中に変わった)	src/bot/bt/compat/engine.py
判定できない(HEAD が作業中に変わった)	src/bot/bt/reference/bar_rules.py
判定できない(HEAD が作業中に変わった)	tests/bt/item_4/i4w_drive.py
判定できない(HEAD が作業中に変わった)	tests/bt/item_4/test_i4_r2_signal_at_open_grid.py
判定できない(HEAD が作業中に変わった)	tests/bt/item_4/test_i4_spec_vs_reference_grid.py
```
<!-- diff_scope:end -->

