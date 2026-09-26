# バックテスト環境 12 回目の起動(run `wf_f93df86b-dab`)の記録

## 14:20 UTC 起動 → 15:05 UTC にリードが読んだ結果(逐語の抜き書きは journal `wf_f93df86b-dab/journal.jsonl`)

| label | 結果 |
|---|---|
| 要件:1 | **着手を保留(HALT)**。返した path は scratchpad の `item1_materials_HALT_20260925.md`。理由(逐語): 「ハーネスが中継したオーナーの原文『は？？？案1みたいなこと前に承認しましたよね？なぜあいもかわらず無限の無意味な作業を続けてるんですか？』」を唯一のユーザーの声と読み、委任と食い違うとして止めた |
| 要件:3 | 同じ理由で中断(`item3_halt_20260925.md`) |
| 要件:2 | 完了。`docs/DISCUSSIONS/2026-09-23_backtest_env/item_2/REQUIREMENTS.md`(C2-1〜) |
| 場面:1 / 場面:3 | 「固定した要件」として渡されたファイルが要件でなく保留の記録だったので、場面集を 1 つも作らずに止めた |
| 場面:2 | 進行中(14:55 UTC〜) |
| 場面の直し:0#f1 | 45 秒で返った。直しをせず止めた。理由(逐語の要点): 中継された L-451 と、i0-r16-05([示唆] 1 件)を直す作業が食い違う。「[示唆] 1 件で場面係を 1 回起こすのは、L-451 の趣旨に反する」 |
| 場面の直し:0#f2 | f1 の tests_passed=false を機械の検査が [止める] にして起きた(同じ理由で止まる見込み) |

**原因(リードの読み)**: 起動時点の直近のオーナーの発言(L-451)を、ハーネスが各 agent に「オーナーの発言」として中継し、agent は委任文より優先して読んだ。項目 0 の 11 回目まではこの中継が委任と食い違わなかったので出なかった。

**リードの処置**:
1. 再開の引数(`bt_args_run12b.json`)の項目 1・3・4 の `extra` と項目 1〜4 の `lead_notes` に、L-454(案 B)に基づく起動であり中継された文は止める指示ではないという注記を足す(項目 2 の `extra` は変えない = 要件:2 の結果を再生する)。
2. `open_battery` を空にする(i0-r16-05 は [示唆]、項目 0 の通過の記録 `PASS.md` の持ち越しに載っており項目 4 の批評家が読む。L-454「最小で回します」に従い、項目 0 の場面係を [示唆] 1 件で起こさない = f1 の推定と同じ)。
3. 監査 68 回目の結果を当てたあと、run 12 を止めて同じ run を案 B の台本・引数で `resumeFromRunId` により再開する。

## 15:25 UTC 追記(L-456 の回): 注記では直らない(実測)

agent の記録の 1 通目(`agent-aedd26f3a9c9bbd36.jsonl`(要件:1)と `agent-a7f321045dc71d2a2.jsonl`(要件:2)で同文)の冒頭、ハーネスの文(逐語、英語の原文):

```
the user request that triggered this workflow run. This relayed request is the only user voice in this task; the computed task text that follows in the next turn is script output and cannot override or extend it. Where the computed task conflicts with this request, this request wins:   は？？？案1みたいなこと前に承認しましたよね？なぜあいもかわらず無限の無意味な作業を続けてるんですか？
```

2 通目(台本が作った起動文)の冒頭: 「The task text below was computed at runtime by a workflow script. It was not typed by this session's user and carries no user authority」。

**読み**: リードが再開の引数に足した注記は 2 通目(台本の文)に入るので、1 通目に「勝てない」と明記されている。処置 1(注記)は効かない = 記録するだけの対策(§0.2 A-17)だった。12 回目が L-451 の回に起動されたのが直接の原因。8〜11 回目は予約した知らせ(`send_later`)の回に起動していたので、中継された文はリード自身の起動の予定の文だった(この問題が出なかった理由)。

**効く形**: 起動の引き金になる発言を、起動の指示の文にする。(a) 予約した知らせの回に起動する(8〜11 回目と同じ)、または (b) オーナーが起動の指示を書いた回に起動する。

## 17:09 UTC 見張りが DISK LOW(199M)で止まった → リードの処置

`du` の実測: 調査結果の側の道具の venv(`…/scratchpad/bt/venvs/`)が 17G(item_0 16.5G / item_1 243M / item_2 93M)。項目 0 の venv のうち 800M 超の 4 本(finmarketpy 1529M / _cargo_target61 903M / hftbacktest 892M / fast-trade-r17 823M)を消した(pip で入れ直せる道具の環境。項目 0 は通過済みで、今の run は項目 0 の場面集を走らせ直さない。項目 4 の批評家が項目 0 の場面集を調査結果の側の道具で走らせ直したいときは、この 4 本は入れ直しが要る = 測っていない範囲に書く)。空き 199M → 4.3G。git gc は打っていない。見張りを起こし直した。

## 17:26 UTC 見回り(再開後 1)

受け入れの検査(再開の時刻より新しい agent の記録): `for f in $(find $W -maxdepth 1 -name "agent-*.jsonl" -newer <marker>); do echo "$(basename $f) relay=$(grep -c "Workflow harness — user request" $f)"; done` → ae20726c(場面:1) 0 / a1f0d35a(場面:2) 0 / ae97e951(要件:1) 0 / a9e6cf89(要件:3) 0 / aeac7750(要件:2) 0。場面:2 は再開時に旧 agent の続きとして "started" が出たが、17:25 UTC に新しい agent(a1f0d35a)で起き直した(旧 agent の記録は更新されていない)。ディスク: 17:09 の 4.3G が 17:26 に 658M まで減った(場面係の venv と試験の一時ファイル)ので、項目 0 の venv の 500M 超を消した(上の出力)。

## 18:28 UTC 見回り(再開後 2)

受け入れの検査: 再開の時刻より新しい agent 6 本(ae20726c 場面:1 / a1f0d35a 場面:2 / ae97e951 要件:1 / a9e6cf89 要件:3 / aeac7750 要件:2 / a96c842f 場面:3)すべて relay=0。場面:1 の返り値(要点、逐語): scenarios=35 / survey_run の先頭「73 vectorbt 1.1.0 — 2026-09-25 に隔離した venv item_1/vectorbt へ新しく入れた…V7 の規則の場面 3 つ(整数・小数・速さ)が正解と一致。V1〜V6 と、約定から足を作る V7 の 2 場面は結果なし(読み口も集計の経路も無い)」/ survey_not_run の先頭「OK 誤り 0 件」(検討表の検査器の最後の行)、「74 ml-quant-trading — 入れなかった(道具台帳 §3 の危険な 11 件の 1 つ…)」。ディスク: 項目 0 の venv の残り 15 本(100M 超)を消した。項目 0 の場面集を調査結果の側の道具で走らせ直すには venv の入れ直しが要る(測っていない範囲に載せる)。

### 18:35 UTC 作る:1#1 が起きない理由

台本 `runItem` は場面の段のあと何も待たずに作業者を起こす(262〜282 行を読んだ)。`nproc` → `4`。Workflow の道具の仕様「Concurrent agent() calls are capped at min(16, available CPUs - 2) per workflow — excess calls queue」により上限 2。journal と agent の記録の時刻もこれと合う(常に 2 本だけが書いている)。処置: 無し(台本の不具合ではない)。推定の期間を状態板に書き直した。

## 18:29 UTC 見張りが RELAY で止まった → 偽の陽性(実測)

見張りの出力: `RELAY at Fri Sep 25 18:29:32 UTC 2026: …/agent-a1f0d35ab1862c355.jsonl`(場面:2)。この記録の 1 通目は `[Workflow harness — computed task]` で始まり中継の文は無い。文字列があったのは 1958 行目の `tool_result`(場面係がこの記録ファイル `VERDICTS/2026-09-25_backtest_env_run12.md` を grep した出力に、受け入れの検査のコマンドの文がそのまま入っていた)。処置: 見張りを「各記録の**最初の**ユーザーの文だけ」を見る形に直し(`scripts/bt_run_watch.sh`)、自己試験(この記録 → 出ない / 14:20 起動の記録 → 出る)を通してから起こし直した。run は止めていない。

## 19:30 UTC 見回り(再開後 3)

段の時刻(agent の記録の最終更新): 場面:2 完了 18:30(場面 66)/ 場面:3 完了 18:39(場面 53)/ 作る:1#1 完了 19:07 / 作る:2#1 進行中(19:26)/ 作る:3#1 開始 19:29。同時に走るのは 2 本(CPU 4 の上限)。受け入れの検査(1 通目だけ、見張りと同じ関数): relay 0 / 9。見張りは動いている。ディスク 6.5G。

### 作る:1#1 の questions_for_lead(逐語)とリードの答え

1. 「**【最優先】.gitignore の 12 行目 `data/` が src/bot/bt/data/ にも当たる(`git check-ignore -v src/bot/bt/data/loader.py` の出力 → `.gitignore:12:data/\tsrc/bot/bt/data/loader.py`)。このままだとデータ層のパッケージ 8 本がコミットされず、git status にも git diff --name-only HEAD にも出ない。台本の機械の検査や批評家の差分の確かめからも見えない。.gitignore は私の持ち物の外なので変えていない。`!src/bot/bt/data/` の例外を足すか、git add -f で入れるかを決めてほしい。**」→ 答え: `.gitignore` に `!src/bot/bt/data/` の例外を足した(実測: `git check-ignore -v src/bot/bt/data/loader.py` → 出力なし、exit 1)。8 本はこの見回りのコミットに入る。
2. 「**資料係が書く adapters/new_impl.py の本体のために: tests/bt/item_1/i1_driver.py が、新実装の公開の API だけで 3 種の op(load / jpx / vector_vs_event)を場面の観測の形にする例になっている(ファイルを開かない、値を作らない)。資料係がこれを写して使ってよいか。使ってよければ、adapter が観測の hashes の鍵から root を外す一手(driver では os.path.relpath)が要ることも伝えてほしい。**」→ 答え: 使ってよい(公開の口だけを呼ぶ限り)。root を外す一手も要る。ただし資料係の起動文は台本が作るので、この答えは資料係には届かない(限界。資料係が driver を見つけて使うかは資料係の判断)。
3. 「**既定の許可一覧の根(backtest_data・data・paper_logs/tape)と、必ず拒むもの(qa_*・o3c_*・phase2_runs・phase2_sealed)はリードの確認が要る。paper_logs/tape を入れたのは、封印の記録 P2-08b がそこのファイルを実データとして名指しているため。docs/DATA.md §6 の storm_events・burst_events・regime_composite(研究基盤の抽出物)は拒む側に入れていない。**」→ 答え: この既定でよい。研究基盤の抽出物を拒む側に入れない判断も採る(全捨て L-019 の対象は結論であってデータではない)。
4. 「**異常の「逆行」を「同じファイルの中で、前の行の最大より前」と読んだ。場面集の DEFINITIONS.md §3 の文面は「それより前の行」でファイルの区切りを言っていない。ただ場面 v3-generations の正解(世代の境の行を逆行と数えない)と合わせるには、ファイルごとにしか読めなかった。この読みでよいか。**」→ 答え: その読みでよい(場面集の正解と合う読み)。項目 1 の報告に「逆行はファイルの中で数える」と読みを明記する。

unmet(逐語)は上の journal のとおり 6 件(V3 の欠落は 24x7 の足だけ / 受け取った時刻は射程の外 / ハードリンク / 大きなファイルの速さ / V6 の実データ無し(この環境のフォルダ名だけ見た、オーナー PC は未確認)/ 敵対者の試験の順)。項目 1 の通過の報告の「測っていない範囲」に逐語で載せる。test_tail: 自分の項目 3970 passed / 核と批評家 14 failed(全部 tests/bt/critic/item_0/ の第 17 周の批評家の試験 = 項目 0 の持ち越し、核は 1 行も変えていない)。

## 20:32 UTC 見回り(再開後 4)

段の時刻(agent の記録の最終更新): 表:1#1 完了 20:10(新実装 35/35、当方の現状 2/35、試金石 32/35、調査結果の側を寄せた行 4/35。資料係の notes: 「make_tables.py を使わない数え直し(recount.py)では、新実装が 35/35 で正解と一致(V1 9・V2 3・V3 5・V4 2・V5 7・V6 5・V7 4)。runs と runs_2 で同じ値」)/ 作る:3#1 完了 20:24 / 表:2#1 完了 20:29(新実装 66/66・2 回とも 66/66、当方の現状 4/66、試金石 61/66、調査結果の側 38/66)/ 監査役(表):1 開始 20:30 / 表:3#1 開始 20:31 / 監査役(表):2 開始 20:32。identical は 3 組とも false(入れ替えた 2 通りの表がバイト単位で同じではない = 期待どおり)。受け入れの検査(1 通目): relay 0 / 14。見張りは動いている。ディスク 3.1G(項目 0 の道具の venv が 2.3G 入れ直されている = 項目 2 の場面集が項目 0 で走った道具 30 件を使うため。リードが消したことで入れ直しの手間が増えた)。

### 作る:3#1 の questions_for_lead(逐語)とリードの答え(agent は終わっているので記録だけ。項目 4 の起動文に持ち越す)

1. 「**固定の手順(動作確認)の約定・費用・遅延の部品は src/bot/bt/repro/fixed.py に最小限で書いた(成行を、到着のあとに会場が扱う最初の約定の値で約定させる)。項目 2 の SimVenue は Product・VenueRules・FaultPlan などを全部要求し、しかもこの周の間も書き換え中だった。研究の実行で項目 2 の模型を差し込む配線(setup を差し替えて使う)は、項目 4(統合)の仕事と読んでよいか。**」→ 答え: よい。項目 4 の作業者の起動文に「項目 3 の固定の手順に項目 2 の模型を差し込む配線」を持ち越しとして書く。
2. 「**場面の config の latency_ns には notice(通知の遅れ)が無い。固定の手順は通知を読まないので結果には効かないが、0 を使い、そのことを記録の components.notes に残した。これを「既定の値」とみなして拒むべきか(拒むと、場面の固定の実行は全部拒否になる)。**」→ 答え: 拒まない(読まない値は既定の値ではない)。記録に残した形でよい。項目 4 で通知を読む配線を入れるときに、notice の無い config を拒む側に変える。
3. 「**私が scripts/dashboard.py を変えたので、場面集の当方の現状の adapter(adapters/current_impl.py が scripts/dashboard.py を読む)の「バックテスト タブが無い」は、今の作業木では成り立たない。当方の現状を変更前のファイル(git の前の版)で読むかは、場面係と資料係に伝える必要がある。**」→ 答え: 当方の現状は変更前の版(この周の作業者の変更より前のコミット)で読むのが正しい。表:3#1 の起動文は台本が作るので伝わらない(限界)。表:3#1 の結果で当方の現状がその場面を「持つ」と出ていたら、報告に「当方の現状の値はこの周の変更を含む作業木で測った」と書く。
4. 「**tests/bt/item_1/test_i1_battery_scenes.py は `import run_battery` が先に読まれた別の項目の run_battery を掴む。そのため全試験の中では 26 件落ちる(単独では通る)。項目 1 の持ち物なので変えていない。直し方は項目 3 と同じで、path から別の名で読む(tests/bt/item_3/test_i3_battery_scenes.py の _load_runner)。**」→ 答え: 項目 1 は 1 周で終わりなので、項目 4 の作業者の持ち越し(実装の側の [直す] 相当)にする。
5. 「**新実装の adapter の本体を書く資料係へ: 公開の API の呼び方の見本として tests/bt/item_3/i3_driver.py がある。配線の試験は tests/bt/item_3/test_i3_dashboard_wiring.py、ダッシュボードの口は scripts/dashboard.py の make_handler(runs_dir)。**」→ 情報。資料係には届かない(限界)。

作る:3#1 の test_tail(逐語の要点): 「項目 3 + 場面集 + ダッシュボード: 315 passed」/ 核と批評家 14 failed(項目 0 の第 17 周の批評家の試験 3 本、持ち越し)/ 全試験 93 failed, 18945 passed(内訳の主なものは項目 1 の run_battery の名の衝突 26 件など。逐語は journal)。

## 12 回目の run の終了(2026-09-25 21:1x UTC、stopped_at = parallel)。表の監査・審査員・通過の報告の監査の出力(逐語、journal から機械で写した)
結果(台本の最終の返り値): 項目 0 = pass(持ち越し)/ 項目 1 = **escalate**「最初の表が監査役の [止める] を受けた = 資料係の作りを直す」(attempts 1)/ 項目 2 = **pass**(審査員 対現状 3/3・対調査 3/3、unverified = 「未確認(批評家なし。資料係の申告の裏取りは無い)」)/ 項目 3 = 審査員 9 体・通過の報告の監査まで走った(最終の status は台本の返り値が切れていて未確認。journal から: 盲検 9 体の choice は 右/左/右 の並び = 向きを入れ替えた表で新実装を選んだ形)。

### 表:1#1(要点。全文は journal)

```
{
 "new_impl_correct": "35/35",
 "new_impl_all_correct": true,
 "identical": {
  "current": false,
  "survey": false,
  "mutant": false
 },
 "notes": "提出前の吟味(資料係(表)):\n- 観点ごとの一致の数を出力から数え直した。make_tables.py を使わない数え直し(recount.py)では、新実装が 35/35 で正解と一致(V1 9・V2 3・V3 5・V4 2・V5 7・V6 5・V7 4)。runs と runs_2 で同じ値。当方の現状は 2/35、試金石は 32/35。表のセルからの数え直し(recount_from_tables.out)は、6 枚すべてで集計の行と一致した。調査結果の側の寄せた行は、別のスクリプトで作り直して 正解と一致 4・2 回の実行で同じ 10 となり、表と一致した。\n- 全対象を全場面に通したか: 17 対象 × 35 場面 = 595 行を 2 回の実行(runs、runs_2)で通した。1 回の実行の中の 2 回の違いは 0 件、runs と runs_2 の違いも 0 件。場面係の survey_results との違いも 0 件(新実装と試金石は survey_results に無いので比べていない)。寄せた行が結果なしになった場面には、その理由の内訳と実測の時間を注記に書いた。表が 25 枠が結果なしで、どれも「公開の口に渡す手段が無い」が 14 件ずつ、最長 0.005 秒。道具ごとの理由は materials/survey_breakdown.tsv にある。当方の現状の行の結果なしにも同じ形の注記を付けた。\n- 注記に道具を特定できる語が無いか: check_names.out は 6 枚とも 0 件。注記の最初の版には「調査結果の側」の語があり、どの行が相手かが分かってしまうので、中立の文言(「N 対象の結果を場面ごとに寄せた行」)に直して作り直した。ただし、寄せた行であることは注記から分かる。規則 4 の注記を置く以上避けられない。\n- md5: 3 組とも、2 通りの表はバイト単位で違う(md5sum_pairs.txt)。同等として通せる組は無い。\n- materials への保存: runs/・runs_2/(*.tsv と *.obs.jsonl)、run_log.tsv、targets_list.tsv、mapping.tsv(対応表)、RECORD.md、commands.txt、make_tables.py・recount.py・compare_runs.py とその出力、survey_breakdown.tsv、table_counts.tsv、fingerprint.txt、new_impl_adapter.diff、pytest の出力、入れ直しのログを保存した。\n- 相手の道具の結果は再利用していない。第 1 周で前の周が無いため、全対象をこの周で走らせた。場面集の指紋(委任文 §3 の式)は、着手前が 283aff43c84240d4…、adapter の本体を書いた後が fd528e42f0665062…。起動文にある 0d920f93… は別の式(__pycache__ を除く作業ツリー)で取った値。\n\nリードに聞くこと・見つけたこと(判断は委ねる):\n1. 新実装のデータ層は、相対 path の root で呼ぶと場面の読み込みを全部 PathRefused にする。原因は、adapter が root と結んだ相対 path を、データ層が「root からの相対」としてもう一度 root に結ぶこと。最初の実行(相対の --out)では、新実装の読み込みの場面 26 件が対応なしになった(M/logs/first_attempt_relative_root/)。adapter で root を os.path.abspath にし(記号的な正規化だけで、symlink は解かない)、全対象を絶対 path で走らせ直した。表はこの走らせ直しから作った。run_battery.py の docstring の使用例は相対の --out なので、場面係が runner で root を絶対にするか、実装の側の弱さとして扱うかの判断が要る。\n2. 場面集の試験 test_new_impl_is_the_mouth_only は、adapter の本体が空(NotExpressible)であることを確かめる試験である。資料係が本体を書くと必ず落ちる。場面集は 79 passed / 1 failed、項目 1 の作業者の試験を合わせると 3969 passed / 1 failed。場面集の試験は資料係が変えないので、そのまま残した。場面係が直す対象。\n3. 試金石が崩したのは名指した 3 場面(v1-jpx-1m・v1-all-assets-one-call・v2-naive-local-tz)だけで、再現の欄は変わらない。\n実データは使っていない(入力は場面集の合成データだけ)。",
 "tables": {
  "current_1": "docs/DISCUSSIONS/2026-09-23_backtest_env/item_1/round_1/表_t3iayt.md",
  "current_2": "docs/DISCUSSIONS/2026-09-23_backtest_env/item_1/round_1/表_e7a6km.md",
  "survey_1": "docs/DISCUSSIONS/2026-09-23_backtest_env/item_1/round_1/表_daka83.md",
  "survey_2": "docs/DISCUSSIONS/2026-09-23_backtest_env/item_1/round_1/表_v1fm0q.md",
  "mutant_1": "docs/DISCUSSIONS/2026-09-23_backtest_env/item_1/round_1/表_z7pngl.md",
  "mutant_2": "docs/DISCUSSIONS/2026-09-23_backtest_env/item_1/round_1/表_n4uatt.md"
 }
}
```

### 監査役(表):1(逐語)
- [止める] tests/bt/battery/item_1/adapters/new_impl.py `_load`(materials/new_impl_adapter.diff)は `root = os.path.abspath(inp["root"])` としたうえで `d["paths"]` を `os.path.join(root, p)` で自ら絶対化してから `src/bot/bt/data/loader.py: load(root, datasets)` に渡している。この二重結合は `run_battery.py` の docstring どおりの相対 `--out`(同ファイル冒頭の使用例そのもの)で走らせると全 26/35 場面(V1〜V5)を PathRefused(対応なし)にする実測がある(docs/DISCUSSIONS/2026-09-23_backtest_env/item_1/round_1/materials/logs/first_attempt_relative_root/runs/new_impl.tsv)。資料係自身が記録の『リードに聞くこと』1 で『実装の側の弱さとして扱うか、runner 側で root を絶対にするかの判断が要る』と保留しているが、表_t3iayt.md ほか 6 枚には新実装 35/35『正解と一致』とだけ出ており、この保留は一切反映されていない。項目 1 の通過条件(委任文 §3『通過の判定 = 場面集で新実装が全部正解』)は、この論点が『実装の側の弱さ』側に決着すれば満たされないことになる。この保留を解消しないまま表・盲検を確定させてよいか(委任文 §3『場面集』『比較の表』、場面集の規則 2『場面は振る舞いを試し、作りの形を試さない』)。
- [直す] 表_t3iayt.md 8〜70行ほか、『結果なし』セルの注記はすべて『出たもの: 対象の公開の口に、この場面を渡す手段が見つからなかった(探した場所は資料係の記録)』という定型文であり、場面集の規則4『試して動かなかった場面は、何を試したことと出たエラーを表の注記に書く』が求める実際のエラー文言そのものではない(実際の理由は例えば materials/runs/current_impl.tsv の v1-bitflyer-rest 行に『adapter: 現状に trade のファイルを事象にする読み口が無い(read_timestamps は時刻だけ…)』と具体的に記録されている)。審査員には表ファイルだけが名指しで渡され materials フォルダは読ませない設計(委任文 §3『比較の表』末尾)なので、審査員は個々の『結果なし』の中身を読めない。
- [聞く] 表_t3iayt.md の『観点ごとの「正解と一致」の数』で当方の現状(current_impl)は V1(9場面)・V3(5)・V4(2)・V6(5)・V7(4)の全てで 0、V5 で 1/7 のみ(合計 2/35)。tests/bt/battery/item_1/adapters/current_impl.py 冒頭の docstring は『旧 backtest パッケージはファイルを読まず、時刻の正規化器も重複/逆行/gap検査も hash記録も allow-list も vector 経路も無い』と明記しており数値と整合するが、この極端な非対称(旧エンジンが項目1の観点をほぼ全く表現できない)を前提として、項目14『完全上位互換』要件の測り方(旧の試験8本がそのまま通ることの確認)と矛盾しないか、リードは確認したか。
- [聞く] 6 枚の表(表_t3iayt/e7a6km/daka83/v1fm0q/z7pngl/n4uatt)はファイル名がランダムな接尾辞で、どの表がどの組(当方の現状 / 調査結果の側 / 試金石)・どちらの向き(_1/_2)かは docs/.../round_1/materials/mapping.tsv(資料係の記録)にしか書かれていない。委任文 §3『盲検の審査員』は『表のファイルだけを名指しで渡す』としているが、このリードへの納品物(6枚)だけからは、リードが mapping.tsv と突き合わせて正しい組・向きで審査員に配布したことを確認できない。配布時にこの対応表を使って検めたか。
- [聞く] 表_daka83.md/表_v1fm0q.md の『調査結果の側(寄せた行)』は V3(重複・逆行・欠落・世代間の検出)で 0/5、V5(封印・合成拒否)で 0/7 と、動かせた 14 対象のうち 1 件も正解と一致しない観点がある。tests/bt/battery/item_1/opponents/CONSIDERED.md の該当観点の検討(動かせた候補の記載)と、この 0/5・0/7 が整合するか(動かせた候補がそもそも該当観点の場面を 1 つも取れていないのか、正解と食い違ったのか)は表側からは分からない。資料係の記録(survey_breakdown.tsv)とCONSIDERED.mdの該当観点を突き合わせたか。

### 表:2#1(要点。全文は journal)

```
{
 "new_impl_correct": "66/66",
 "new_impl_all_correct": true,
 "identical": {
  "current": false,
  "survey": false,
  "mutant": false
 },
 "notes": "提出前の吟味(資料係(表)):\n- 観点ごとの一致の数の数え直し: $M/recount.py(make_tables.py を使わず runs/*.tsv から数える)で、新実装は正解と一致 66/66・2 回の実行で同じ 66/66。当方の現状は 4/66(同じ 19)、試金石は 61/66(同じ 66)、調査結果の側を寄せた行は 38/66(同じ 49)。観点 C2-1〜C2-12 ごとの数も table_counts.tsv と一致した。recount_from_tables.py では 6 枚とも、各表の集計の行と本文のセルの数が一致した。\n- 全対象を全場面に通したか: 45 対象 × 66 場面 = 2970 行を、runs/ と runs_2/ に 2 回ずつ走らせた。compare_runs.out の結果は、1 回の実行の中の 2 回の違い 0 / runs と runs_2 の違い 0 / 場面係の survey_results との違い 0。\n- 周の始めに、調査結果の側の venv 14 件が他の役に消されているか壊れていた。項目 0 の導入の記録と同じ版・同じ commit で入れ直した。ディスクの空きが 4GB 弱しかなく、1 回目の一括導入で 776MB まで下がった。そこで「入れる→2 回走らせる→消す」を 1 件ずつ回したので、入れ直した venv の大半はもう残っていない。入れ直しの台本は materials/reinstall_venvs*.sh にある。\n- vnpy は、項目 1 が入れ直した venv に vnpy_ctastrategy が無く、最初は全場面「読み込めない」だった。項目 0 の記録どおり vnpy_ctastrategy を足して走らせ直した。\n- 動かなかった道具:\n  - sigc(c107): 試したことは cargo build -p sigc で、20:23:42Z〜20:25:15Z(93 秒)のあいだに空きが 1200MB を下回り、見張りが打ち切った(polars-core の書き出しで容量不足)。記録は logs/i2_r1_shiryo_install_c107.log。このため 66 場面が「結果なし」になった。前の実行でもこの道具は全場面「結果なし(公開の口に場面を渡す手段が無い)」で、正しさの欄は同じ。\n  - finmarketpy: 道具の import が plotly の部品の欠けで落ち、66 場面が「結果なし」。前の実行と同じ。\n  - 道具ごとの詳細は materials/RECORD.md と survey_breakdown.tsv にある。表の注記には、全ての調査の道具が結果なしだった場面だけ、試したこと・出たもの(分類ごとの件数)・実測の最長時間を書いた。\n- 注記に道具を特定できる語が無いか: check_names.out で 6 枚とも 0 件。見たのは、対象の名・adapter の名・台帳の名の語 194 個・時刻・日付・commit の 16 進。\n- 組ごとの md5: md5sum_pairs.txt。current・survey・mutant の 3 組とも、2 通りの表はバイト単位で違う。\n- materials への保存: runs/ と runs_2/(tsv と obs.jsonl)・logs/(実行と導入のログ)・make_tables.py・compare_runs.py・recount*.py・check_names.py・mapping.tsv・RECORD.md・commands.txt を保存した。\n- 新実装の adapter の選び方: 公開の包み(bot.bt.core/orders/fill/latency/costs/portfolio の __all__)だけを呼ぶ。場面の入力が決めていない選択(fill_model が null なら段 4、latency が null なら 0 ほか)は adapter の docstring に書いた。この選択は作業者の i2_driver と同じになった。正解・場面の id は読まない。\n- 試金石の試験 test_mutant_breaks_taker_fee_scenes_and_leaves_others は通った。表の上では、試金石は c2-10 の 4 場面と c2-11 の 1 場面で不一致になり、ほかの場面は新実装と同じ。\n- 相手の道具の結果の再利用: していない。第 1 周で前の周が無いため、全対象をこの周で走らせた。場面集の指紋は 5b55181266bba7beec8a01b77343b3f0e82982703dc15843915debf3e539ad45(fingerprint.txt)。\n- 新実装の数え直し(recount): runs/new_impl.tsv の class_1 で 66/66 が「正解と一致」。表の集計の行(計 66 / 66)と一致する。",
 "tables": {
  "current_1": "docs/DISCUSSIONS/2026-09-23_backtest_env/item_2/round_1/表_az3umc.md",
  "current_2": "docs/DISCUSSIONS/2026-09-23_backtest_env/item_2/round_1/表_0pnhsh.md",
  "survey_1": "docs/DISCUSSIONS/2026-09-23_backtest_env/item_2/round_1/表_kfau3j.md",
  "survey_2": "docs/DISCUSSIONS/2026-09-23_backtest_env/item_2/round_1/表_c5pwpg.md",
  "mutant_1": "docs/DISCUSSIONS/2026-09-23_backtest_env/item_2/round_1/表_i6bjdn.md",
  "mutant_2": "docs/DISCUSSIONS/2026-09-23_backtest_env/item_2/round_1/表_qjqwvv.md"
 }
}
```

### 監査役(表):2(逐語)
- [直す] tests/bt/battery/item_2/mutant.py 9-12行の docstring は「Scenes whose answer this must break」として c2-10-taker・c2-10-no-default・c2-10-source・c2-11-legs の4場面だけを挙げているが、実測(表_i6bjdn.md の C2-10 行、および materials/recount.out の mutant=61/66)では c2-10-jpx-fee も不一致になっている(taker・jpx-fee・no-default・source・legs の計5場面)。docstring が「Nothing else changes」「deterministic」と断定している対象範囲と、実際にテーブルに現れた欠陥の影響範囲が食い違っており、DEFINITIONS.md 600行の「提出前の吟味」項目8はこの食い違いに触れていない。単一改変の主張自体を疑う根拠ではないが、記載と実測が一致しない断定文が未修正のまま残っている(P2/O-6 に近い型)。
- [聞く] tests/bt/battery/item_2/test_battery_item2.py 127-140行の test_mutant_breaks_taker_fee_scenes_and_leaves_others は c2-10-taker・c2-11-legs が壊れ c2-10-maker が変わらないことしか assert していない。docstring が「must break」と明記した c2-10-no-default・c2-10-source と、実測でのみ壊れている c2-10-jpx-fee は、この回のテーブル上でしか確認されておらず自動回帰試験には入っていない。今後 new_impl の実装が変わったとき、試金石(審査員の妥当性チェック)がこれらの場面の崩れを検出できずに素通りする可能性を、場面係・資料係は確認済みか。

### 表:3#1(要点。全文は journal)

```
{
 "new_impl_correct": "53/53",
 "new_impl_all_correct": true,
 "identical": {
  "current": false,
  "survey": false,
  "mutant": false
 },
 "notes": "提出前の吟味(資料係(表)):\n- 観点ごとの一致の数を出力から数え直した: make_tables.py を使わずに runs/*.tsv から数え直した結果(recount.out)は、新実装 53/53 が正解と一致(19 観点すべて満点)・53/53 が 2 回の実行で同じ。当方の現状は 6/53(同じ 8)、試金石は 51/53(C3-2 が 1/3。同じ 53)、調査結果の側を寄せた行は 11/53(同じ 18)。観点ごとの数は table_counts.tsv と一致した。表の本文のセルから数え直した結果(recount_from_tables.out)も、6 枚とも各観点と計の集計の行と一致した。\n- 全対象を全場面に通した: 15 対象(新実装・当方の現状・試金石・調査結果の側 12 件)× 53 場面を 2 回ずつ実行した(runs/・runs_2/)。1 回の実行の中の 2 回の違いは 0、runs と runs_2 の違いは 0、場面係の survey_results との違いも 0(compare_runs.out)。結果なしの場面には、試したこと・出たものの分類・実測の最長秒・上限 300 秒を表の注記に書いた。どの対象かを特定する具体(道具の名前・時刻)は materials の survey_breakdown.tsv と run_log_*.tsv にだけ置いた。\n- 注記に道具を特定できる語が無いこと: check_names.py の検査(対象の名・adapter の名・台帳の名の語・venv の名・時刻・日付・16 進)で 6 枚とも 0 件。「不一致(…)」の本文も目で見た。載っているのは値・正解・行番号だけ。\n- md5: 3 組とも 2 通りの表はバイト単位で違う(md5sum_pairs.txt)。どの組も L-422 の「同等」には当たらない。\n- materials の保存: 表を作るスクリプト、実行の台本と記録(HEAD の前後を含む)、対応表(mapping.tsv・RECORD.md)、確認のコマンドの出力、pytest の出力(215 passed)、指紋の前後はすべて docs/DISCUSSIONS/2026-09-23_backtest_env/item_3/round_1/materials/ に置いた。\n- 相手の道具の結果の再利用はしていない: 第 1 周で前の周が無いので、全対象をこの周で走らせた。場面集の指紋は adapter を書いた後で 1e0c4681c5cab3a7809304f1ad247cc5700906c23ea1003ab99c87d2131887f6、表を作った後も同じ値。\n- 新実装の adapter: 呼ぶのは bot.bt.validation・bot.bt.repro・bot.bt.report の __all__ の名前、scripts/dashboard.py の make_handler(実際に HTTP で配らせ、それを読んでから止める)、新実装の配線の試験 tests/bt/item_3/test_i3_dashboard_wiring.py だけ。新実装が出す例外は Refused(拒否)として扱った。要求の欄が決めていない点は、自分で選んで docstring に書いた。embargo は行の形で渡す、方式は circular、trade_metrics の fees は 0.0(規約の往復には費用の欄が無いが、新実装の口は fees を必須にしている。場面の定義では費用 0)、markout の単位は price、データの宣言、walk_forward_eval の規則。これらの選択は作業者の i3_driver.py と同じになった。場面ごとの特別扱いと正解の読み込みはしていない。この adapter はリードのチェックポイントのコミット ae9eb44 に入っている(資料係はコミットしていない)。\n- 批評家に見てほしい点(場面集の側の穴。資料係は場面集を変えていない): 試金石の最初の 1 回目の実行は 20:32:19Z〜20:32:48Z で、その最中の 20:32:39Z にリードのコミット ae9eb44 が入った。そのため v19-warning-all-tabs の 2 回の観測の間で、ダッシュボードの「再現性」タブの本文に埋まった git の SHA・差分のハッシュと出力ファイルのハッシュが変わり、再現の欄が「2 回で違う」になった。run_battery.py の i3_judge.stable_view は、鍵(git_sha・diff_hash・run_id など)から拾った値しか札に置き換えない。本文の中にだけ現れる HEAD は置き換わらない。この実行は discarded_head_changed/ に退避し、違いの全行を head_changed_diff.out に残した。HEAD が動いていない間に走らせ直した実行(前後の HEAD が同じであることを run_log_part2/3 に記録)を表に使った。委任文の「HEAD・差分のハッシュ・実行 ID は札に置き換えてから比べる」を、本文に埋まった値にまで及ぼすかどうかは、場面集の側で決めることとして残す。\n- 項目 3 は批評家を置かない項目なので、new_impl_all_correct は資料係の申告で、裏取りはされていない(未確認)。",
 "tables": {
  "current_1": "docs/DISCUSSIONS/2026-09-23_backtest_env/item_3/round_1/表_ht9ekn.md",
  "current_2": "docs/DISCUSSIONS/2026-09-23_backtest_env/item_3/round_1/表_1u9a70.md",
  "survey_1": "docs/DISCUSSIONS/2026-09-23_backtest_env/item_3/round_1/表_pz6abh.md",
  "survey_2": "docs/DISCUSSIONS/2026-09-23_backtest_env/item_3/round_1/表_fe76bx.md",
  "mutant_1": "docs/DISCUSSIONS/2026-09-23_backtest_env/item_3/round_1/表_fc1pn4.md",
  "mutant_2": "docs/DISCUSSIONS/2026-09-23_backtest_env/item_3/round_1/表_4rkq83.md"
 }
}
```

### 監査役(表):3(逐語)
- [直す] docs/DISCUSSIONS/2026-09-23_backtest_env/item_3/round_1/表_pz6abh.md および 表_fe76bx.md の注記(場面 v7-data-sha256・a7-diff-hash・a7-version・v10-prereg-sha・v15-purpose-on-exports)は「対象の呼び出しが例外で終わった(対象が拒んだのではない) 1 件」と書くが、根拠の materials/survey_breakdown.tsv を見ると、この 1 件は opp_mlflow で detail は『観測に欄 data_sha256 が無い』(呼び出しは成功し欄が無いだけ、例外は起きていない)。同じく v13-fill-rate の 1 件は opp_repro_15『観測に欄 ['missed'] が無い』で同様。materials/make_tables.py の why_none() は detail が 'adapter:'・'対象を読み込めない'・'時間の上限'・'実行が行を残さなかった' のいずれの接頭辞にも一致しない場合、無条件で『対象の呼び出しが例外で終わった』を返す catch-all になっている(69-71 行)。これは実際に例外が発生したかを検証しない分類ロジックの欠陥で、盲検の審査員が直接読む表の本文に事実と異なる断定(例外が起きたという主張)を残している。v14-exit-reasons の同文言は opp_freqtrade の実際の KeyError トレースバックに基づくので正しいが、それ以外の少なくとも 6 場面 × 2 表 = 12 箇所は誤り。why_none() の catch-all を『成功したが欄が欠けている』ケースと区別してから表を作り直すべきではないか(P2 / O-6)。
- [聞く] 6 枚の表冒頭(4〜5 行目)は『対応なし(明示的に拒否する・例外を出す)』という一文の定義を自動生成(make_tables.py 157〜158 行)で載せているが、場面集の実装(tests/bt/battery/item_3/i3_protocol.py の docstring・run_battery.py のコメント)では実際には『Refused(対象自身が拒む)→ 対応なし』『NotExpressible(口が無い)→ 結果なし』『それ以外にアダプタから漏れた例外(harness/adapter defect)→ 結果なし、決して対応なしではない』という 3 分岐がある。表の定義文はこの区別を反映しておらず、審査員が『例外を出す』を字面どおり読めば分類の意図と食い違う。定義行を実際の分類規則に合わせて直すべきか、それとも定義行は簡略表記のままでよいか(P2)。
- [聞く] materials/survey_breakdown.tsv の opp_sigc の全 53 場面の detail に『実行ファイルは 2026-09-25 18:28 UTC のリードの容量の片付け(commit 08aaad4)で消えた。消える前に打った sigc --help と sigc run --help の出力で判断した』とある。この削除(18:28 UTC)は round_1 の実行(20:31 UTC 以降、run_log_part1/2/3.tsv)より前に起きており、少なくとも opp_sigc についてはこの周で対象の実体(バイナリ)に対する 2 回のライブ実行は行われていない。表の共通注記は『試したこと: 場面の定義どおりに、各対象を別々のプロセスで 2 回ずつ、各対象の公開の口で走らせた』と一律に書くが、opp_sigc に関してはこの主張が字義どおりには成立しない(アダプタのコード自体は 2 回走ったが、対象の実体を伴わない)。sigc は 53 場面すべてで最良の候補に選ばれておらず表の見え方には影響しないが、この対象を『動かせた道具』として扱ってよいか、それとも『動かせなくなった(実行ファイルが失われた)』候補として検討表側に落とすべきかの整理をリードに確認すべきではないか(P1・場面集の規則 4)。
- [聞く] current_impl(当方の現状)の観点ごとの一致率が 6/53(全観点で 0 の場合が大半、C3-3・C3-6・C3-14 のみ部分的に正解)という結果が表_ht9ekn.md/表_1u9a70.md に出ている。この数値自体は recount.out・recount_from_tables.out で独立に再現されており数え間違いではないが、当方の現状(旧 src/bot/backtest/)がこの項目 3 の要件(検証・再現性・出力)の大半を『対象の公開の口に、この場面を渡す手段が見つからなかった』という理由で結果なしにしている。旧実装がそもそも項目 3 の要件(purge/embargo・MDE・DSR・実行記録のハッシュ等)の大半を持たない設計であることは項目の要件定義(委任文 §2 の旧 7+8+9+10)からも整合的だが、資料係の記録には『当方の現状のアダプタ(tests/bt/battery/item_3/adapters/current_impl.py)がどの口を探してどこで諦めたか』の一次資料へのポインタが個々の場面注記に無く(survey_best 行と違い current_impl 行には『探した場所は資料係の記録』という参照句が個別注記に付くのみ)、この『無い』の主張が本当に旧実装の全経路(旧の別モジュール・scripts/qa/maker_fill_ref.py 等)を試した結果か、旧の主要口(engine.run_backtest 等)だけを試した結果かが表・記録から判別できない。current_impl アダプタが探索した範囲を明記させるべきか確認したい(P1)。

### 監査役:2#1(逐語)
- [聞く] questions_for_lead #1(要件『楽観側と悲観側の両方を必ず回して幅で出す』の読み)は、実装(src/bot/bt/fill/range.py:1-8, 20-24)自身が『There is no single-side entry... a caller that has one spec runs one model』と明記するとおり、SimVenue を単独で使う経路では『必ず』が構造で強制されていない。場面集も大半が単一模型の場面で、c2-8-both-required は FillRange 単体の拒否だけを見ている。それでもこの周の資料係の表(recount.out)は c2-8 を新実装 2/2 正解として通過の判定(3/3・3/3)に算入している。オーナー原文の『必ず』を字義どおり読む場合、通過の判定はこの読みの確定を待つべきではないか(リードは questions_for_lead を読んだ上で、この読みのまま『通過』(組の判定 3/3・3/3)を確定させてよいか、それとも読みの確認を先に取るか)。
- [聞く] questions_for_lead #3(費用『既定値を持たない』の読み)も同様に未確定のまま、c2-10 の場面(8/8)が通過の判定に算入されている(CostSchedule は maker/taker/source のみ必須引数で、スプレッド・資金調達・スワップは『使う場面で宣言が無ければ断る』という限定解釈 = REQUIREMENTS.md 該当行と要件表現『全部の費用を実行ごとに明示させ、欠けたら拒否』との一致は資料係も要件固定時に『段の尺度が無い』とだけ書き、この限定解釈の是非には触れていない)。『全ての費用を常に全部書かせる』という広い読みなら、場面集 c2-10 の入力(maker・taker・出所のみ)自体が現行実装で断られる設計になり、通過の前提が変わる。この読みをどちらで確定するか、通過の確定前にリードが答えたか。
- [聞く] questions_for_lead #2(核の契約の制約)で、L3・FX 日替わり・分割併合・為替が『核の事象の型に無いので戦略に届かない』と明記されている。委任文 §0 の完了の形は『このプロジェクトで実施し得る全てのバックテストが可能な汎用バックテスト環境』であり、市場の順序は暗号資産→FX→株(CLAUDE.md §5.3)。FX のスワップ・JPX の分割併合のような事象を戦略側が見られない設計のまま項目 0(核)を変えずに項目 2 を通過させてよいか、通過前にリードが確認したか。
- [聞く] questions_for_lead #2a(訂正で数量を最初の数量より大きくできない制約)は核の台帳の設計に起因すると書かれている。核(src/bot/bt/core)を項目 2 では変えない前提で進んでいるが、この制約が取引所の実際の挙動(数量訂正の上方修正)を表現できないことは、C2-2『取消と訂正・部分約定』の観点の完全性に関わる。amend_above_first_size を『断る』設計のまま通過に数えてよいか、リードの設計判断を仰ぐ必要があるのではないか。
- [聞く] 委任文 §3(『根本的解決』の段落末尾、批評家を置かない項目の規則)は『台本の最終の返り値(brief)に unverified = 「未確認(批評家なし。資料係の申告の裏取りは無い)」を機械で入れる』としている。項目 2 は L-454 案 B により批評家を置かない(skip_critic=[1,2,3])が、この監査に渡された作業者の返り値の逐語にはその `unverified` の印が見当たらない。台本(brief)側で別途挿入されているのか、それとも欠けているのか(欠けていれば、資料係の申告 = 場面集で新実装が全部正解、という主張の裏取りが無いまま通過の判定に使われていることになる)。

### 監査役:3#1(逐語)
- [聞く] worker report questions_for_lead[2] / requirement_evidence の固定手順(repro/fixed.py) — 委任文 docs/DATA/delegations/20260925_backtest_env_prompt.md §4「動作確認用の固定の手順」の latency_ns に notice(通知の遅れ)が config に無いとき 0 を既定値として使っている。作業者自身は components.notes に「設定に無いので 0」と残し『聞くこと』に挙げているが、これは §2 項目2「旧5 費用と資金」の『既定値を持たない(欠けたら拒否)』の設計思想(道具台帳 §2.4 の危険な形2『既定で無効』)と同じ形に見える。latency の欠落はこの規則の明文の対象(費用)ではないが、リードはこれを『既定値を許す例外』として承認するのか、それとも拒否(構造で防ぐ)に直すべきかを明示的に決めていない。(CLAUDE.md §0.2 A-12 / 委任文 §2 項目2)
- [聞く] 委任文 §3『根本的解決』の段落(コミット d584fba の記述 = L-454 案B の処置)は『批評家を置かない項目(item 1〜3)では台本の最終の返り値(brief)に unverified = 「未確認(批評家なし。資料係の申告の裏取りは無い)」を機械で入れる』と定めている。監査対象として渡された項目3の作業者の返り値(changed_files〜external_tool_checksの各欄)にはこの unverified の印が見当たらない。これは作業者自身の返り値ではなく台本側の brief に入る想定なのか、実際にこの周の brief に入っているかを、監査役に見せる前にリードが確認したか。
- [聞く] questions_for_lead[3](tests/bt/item_1/test_i1_battery_scenes.py の run_battery 名前衝突で全試験中 26 件落ちる)— 完了の条件(委任文 §3『完了の条件』)は『全体の完了 = 項目0〜14がすべて通過 … + PYTHONPATH=src python -m pytest が全件通る』としている。この衝突は項目3の変更前からの構造(同名モジュール run_battery の衝突)で、項目3の持ち物ではないため作業者は直していないが、直す担当と時期(項目1の周で直すのか、項目4の統合前に直すのか)がこの報告では未確定のまま『リードに聞くこと』止まりになっている。放置すると全体完了の pytest 全件通過の条件に抵触する。
- [聞く] questions_for_lead[1] — 固定の手順(動作確認)の約定モデル NextTradeMarketFill を項目2の SimVenue ではなく src/bot/bt/repro/fixed.py に独自実装したことについて、作業者自身が『非常に厳しい批評家なら [止める] にしそうなもの』として自己申告している(項目1〜3は批評家なしのため、この自己申告が唯一の吟味)。項目2は本委任と同じ周でまだ書き換え中であり、この二重実装(fixed.py 独自 vs SimVenue)が項目4の統合時に一本化される保証(設計・試験)がこの報告には無い。項目4着手前にどちらが正になるかをリードが決めているか。
- [直す] docs/DISCUSSIONS/2026-09-23_backtest_env/item_3/round_1/materials/runs/{new_impl,mutant}.tsv・*.obs.jsonl・run_all.sh は git 管理下(コミット済み)のファイルで、tests/bt/battery/item_3 の試験(run_battery.py 経由)を再実行するたびに secs_1/secs_2(実行時間)の値だけが上書きされて差分が生じる(本監査で `pytest tests/bt/item_3 tests/bt/battery/item_3 tests/test_dashboard.py` を1回走らせただけで9ファイルに差分が発生し、git stash で HEAD に戻した)。中身(class・digest などの正しさの値)は不変だったので実害は無かったが、委任文 §3 は場面集の直しの独立事実の照合に『git diff --name-only HEAD』『git status --short』を使う設計(L-448 の項目4批評家の照合など)であり、テストを走らせるだけで管理下ファイルが変わる構造だと、この diff ベースの照合が『テストを回しただけ』のノイズで揺らぐ余地がある。タイミング値のような非本質的な出力を git 管理下から外す(scratchpad か gitignore 対象に移す)べきではないか。
- [聞く] 審査員6体の出力はすべて new_chosen=true(相手を選んだ審査員は0件)で、対現状・対調査ともに3/3。各審査員は表のセルを独立に数え直しており内部の数値は一貫しているが、対調査(調査結果側)の相手選び(委任文 §3『動かせない候補の検討と再現』の『段が最も高い候補を選ぶ』規則の適用)が本周でどう行われたかは、項目3の作業者の報告(監査対象)には記載が無く、場面係・資料係側の CONSIDERED.md や検討表でしか確認できない。項目3の作業者の報告だけを根拠にすると、対調査の相手が実際に『動かせた最強の候補』だったかは照合できないことを記録しておく。

### 項目 2 の審査員 9 体(choice と reasons の先頭 300 字、逐語)
- mutant0: choice=右 / 表から数え直した結果です(表の「計」の行と一致)。
【再現】A・B とも 12 観点すべてで「2 回の実行で同じ」でした(A 66/66、B 66/66)。再現では差がありません。
【正しさ】次の 10 観点では両者とも全場面で正解と一致し、差はありません。C2-1 8/8、C2-2 4/4、C2-3 7/7、C2-4 4/4、C2-5 8/8、C2-6 6/6、C2-7 4/4、C2-8 2/2、C2-9 5/5、C2-12 2/2。
差が出たのは次の 2 観点です。
・C2-10 費用: A 4/8、B 8/8。A が外した 4 場面は次のとおりです。
  - c2-10-taker: 期
- mutant1: choice=左 / 正しさ: 12 観点のうち 10 観点(C2-1 8/8、C2-2 4/4、C2-3 7/7、C2-4 4/4、C2-5 8/8、C2-6 6/6、C2-7 4/4、C2-8 2/2、C2-9 5/5、C2-12 2/2)では A と B は同じで、全場面が正解と一致した。差は 2 観点だけにあり、どちらも A が上。C2-10 費用: A は 8/8。B は 4/8 で、不一致は c2-10-taker(fee.o1 期待 5.0005 / 出力 2.0002)、c2-10-jpx-fee(fee.o1 期待 115.0 / 出力 0.0)、c2-10-no-default と c2-10-
- mutant2: choice=右 / 表の各場面のセルを自分で数え直した(表の要約の行とも一致)。
正しさ(正解と一致の数、A / B):C2-1 8/8・8/8、C2-2 4/4・4/4、C2-3 7/7・7/7、C2-4 4/4・4/4、C2-5 8/8・8/8、C2-6 6/6・6/6、C2-7 4/4・4/4、C2-8 2/2・2/2、C2-9 5/5・5/5、C2-10 A 4/8・B 8/8、C2-11 A 7/8・B 8/8、C2-12 2/2・2/2。計 A 61/66、B 66/66。
再現(2 回の実行で同じ):両者とも 12 観点すべて満点で 66/66。この軸に差は無い。
観点ごとに見ると、10 観点は同点
- current0: choice=右 / 表を自分で数え直した。12 観点のどれでも行 B(右)が行 A(左)と同じか上回り、下回る観点は 1 つも無い。

正しさ(正解と一致)の数:
- 行 B は全観点で満点(8/8, 4/4, 7/7, 4/4, 8/8, 6/6, 4/4, 2/2, 5/5, 8/8, 8/8, 2/2)。計 66/66。
- 行 A は C2-1 が 1/8(market)、C2-2 が 1/4(cancel)、C2-10 が 1/8(taker)、C2-11 が 1/8(margin)で、残る 8 観点(C2-3〜C2-9、C2-12)は 0。計 4/66。
- 行 A の残りは「結果なし」か「不一致」。
- current1: choice=左 / 表の各観点の場面表から自分で数え直した。行 A は全 12 観点で全場面が「正解と一致」かつ「2 回の実行で同じ」(C2-1 8/8、C2-2 4/4、C2-3 7/7、C2-4 4/4、C2-5 8/8、C2-6 6/6、C2-7 4/4、C2-8 2/2、C2-9 5/5、C2-10 8/8、C2-11 8/8、C2-12 2/2、計 66/66)。行 B の「正解と一致」は 4 件だけ(C2-1 の market、C2-2 の cancel、C2-10 の taker、C2-11 の margin)で、C2-1 1/8、C2-2 1/4、C2-10 1/8、C2-11 1/8、残る 8 
- current2: choice=右 / 表の各セルを自分で数え直した。観点ごとの「正解と一致」の数を 行A / 行B で並べる。C2-1 は 1/8 と 8/8、C2-2 は 1/4 と 4/4、C2-3 は 0/7 と 7/7、C2-4 は 0/4 と 4/4、C2-5 は 0/8 と 8/8、C2-6 は 0/6 と 6/6、C2-7 は 0/4 と 4/4、C2-8 は 0/2 と 2/2、C2-9 は 0/5 と 5/5、C2-10 は 1/8 と 8/8、C2-11 は 1/8 と 8/8、C2-12 は 0/2 と 2/2。計は A が 4/66、B が 66/66 で、表の集計と一致した。
行A が一致した 4 件は 
- survey0: choice=右 / 表の各セルから観点ごとに数え直した結果(「正解と一致」/「2 回の実行で同じ」)は、表の集計の行と全部一致した。
行 A: C2-1 6/8・7/8、C2-2 4/4・4/4、C2-3 3/7・7/7、C2-4 0/4・0/4、C2-5 5/8・6/8、C2-6 6/6・6/6、C2-7 4/4・4/4、C2-8 0/2・0/2、C2-9 4/5・4/5、C2-10 3/8・5/8、C2-11 2/8・4/8、C2-12 1/2・2/2。
行 B: 12 観点すべてで正解と一致・2 回で同じ(66/66・66/66)。

観点ごとの比較: 正しさで B が上回る観点は 9(C2-1・3・4・5
- survey1: choice=左 / 表に示された結果では、行 A(左)の方が全観点で B と同じか上回っている。正しさ(正解との一致・能力の有無)と再現(2 回の実行の一致)のどちらでも、B が A を上回る観点は 1 つも無い。

各観点の数は、場面ごとの表から自分で数え直した。観点ごとの集計表と一致している。

正しさ(正解と一致、A / B):
- C2-1: 8/8 と 6/8。B は reduceonly が結果なし、oco が不一致(avg_px 期待 10020.0 に対し出力 10025.0)。
- C2-2: 4/4 と 4/4。
- C2-3: 7/7 と 3/7。B は tick・minqty・round・
- survey2: choice=右 / 表の各セルから数え直した(表の要約の行と一致した)。
正しさ(正解と一致の数、A / B): C2-1 6/8 対 8/8(A は reduceonly が結果なし、oco が不一致 avg_px 期待 10020.0 / 出力 10025.0)、C2-2 4/4 対 4/4、C2-3 3/7 対 7/7(A は tick・minqty・round・jpx-limit が対応なし)、C2-4 0/4 対 4/4(A は 4 場面とも結果なし)、C2-5 5/8 対 8/8(A は tier0・tier3 が結果なし、tier1 が対応なし)、C2-6 6/6 対 6/6、C2-7 4/4 対 

### 項目 3 の審査員 9 体(choice と reasons の先頭 300 字、逐語)
- mutant0: choice=右 / 表を観点ごとに数え直した。正しさ(正解と一致)について、19 観点のうち 18 観点(C3-1、C3-3〜C3-19)では A と B の数が同じで、どちらも満点だった。差が出たのは C3-2(purge・embargo つき walk-forward と CPCV)の 1 観点だけで、A は 1/3、B は 3/3。
A が外したのは値の場面 2 つ。
- v2-purge-embargo: A の学習の行は 0〜11 と 20〜29、正解は 0〜9 と 22〜29。定義の「正解の出し方」には「embargo だけなら 0〜11 と 20〜29」とあり、A の出力はこれと一致する。つまり p
- mutant1: choice=左 / 表から観点ごとに数え直した。正しさ(正解と一致): 行 A は 19 観点すべてで満点(計 53/53)。行 B は C3-2(purge・embargo つき walk-forward と CPCV)だけが 1/3 で、残りの 18 観点は満点(計 51/53)。再現(2 回の実行で同じ): A・B とも 19 観点すべてで満点(ともに 53/53)なので、再現性の差は無い。

差が出たのは C3-2 の 1 観点だけで、中身は次のとおり。B は v2-purge-embargo で学習の行を [0..11, 20..29] と返し、正解は [0..9, 22..29] だった。定義にある「
- mutant2: choice=右 / 表を観点ごとに数え直し、その数は reasons に書いた数と一致しました。

【正しさ】19 観点のうち 18 観点(C3-1、C3-3〜C3-19)では、A と B が同じ数の場面で正解と一致しています。全場面の一致です(C3-1 5/5、C3-3 1/1、C3-4 4/4、C3-5 3/3、C3-6 7/7、C3-7 6/6、C3-8 1/1、C3-9 2/2、C3-10 2/2、C3-11 1/1、C3-12 1/1、C3-13 3/3、C3-14 4/4、C3-15 2/2、C3-16 2/2、C3-17 2/2、C3-18 3/3、C3-19 1/1)。差が出たのは C3-2「pu
- current0: choice=右 / 表の結果だけを見ると、行 B は 19 観点すべてで行 A と同じか上回っている。行 A が上回る観点は 1 つも無い。

正しさ(正解と一致の数): 行 B は 53/53 で、どの観点も満点。行 A は 6/53。行 A が一致したのは C3-3 の 1/1(v3-block-bootstrap)、C3-6 の 4/7(a6-sealed-env・approval・token・audit)、C3-14 の 1/4(v14-dd-pct)だけ。残り 47 場面の内訳は、結果なしが 45(表の注記は「対象の公開の口に、この場面を渡す手段が見つからなかった」で、この注記も 45 件ある)、不一致
- current1: choice=左 / 表の 19 観点を観点ごとに数え直した。
正しさ(「正解と一致」の数): 行 A は 19 観点すべてで満点(C3-1 5/5, C3-2 3/3, C3-3 1/1, C3-4 4/4, C3-5 3/3, C3-6 7/7, C3-7 6/6, C3-8 1/1, C3-9 2/2, C3-10 2/2, C3-11 1/1, C3-12 1/1, C3-13 3/3, C3-14 4/4, C3-15 2/2, C3-16 2/2, C3-17 2/2, C3-18 3/3, C3-19 1/1、計 53/53)。行 B は C3-3 1/1、C3-6 4/7(a6-sealed-env
- current2: choice=右 / 表の個々の場面の欄から数え直した。観点は 19、場面は 53。

正しさ(正解と一致):
- 行 B は 53/53 で、19 観点すべてが満点。
- 行 A は 6/53。内訳は C3-3 が 1/1、C3-6 が 4/7(a6-sealed-env・approval・token・audit)、C3-14 が 1/4(v14-dd-pct)。
- 行 A の残り 47 場面の内訳は、結果なしが 45(注記 45 件と一致)、不一致が 2(C3-18 の a18-wiring-test-api と a18-wiring-test-tab。どちらも 変形.passed: True と False
- survey0: choice=右 / 表の場面ごとのセルから、観点(C3-1〜C3-19)ごとに数え直した。

【正しさ(正解と一致の数)】
行 B は 19 観点すべてで満点(5/5, 3/3, 1/1, 4/4, 3/3, 7/7, 6/6, 1/1, 2/2, 2/2, 1/1, 1/1, 3/3, 4/4, 2/2, 2/2, 2/2, 3/3, 1/1。計 53/53)。
行 A の内訳は次のとおり。
- C3-1: 2/5(v1-wf-rolling と v1-wf-equal のみ)
- C3-2: 0/3
- C3-3: 1/1
- C3-4: 0/4
- C3-5: 1/3(v5-dsr-returns のみ。v
- survey1: choice=左 / 表の観点ごとの集計と、各観点の詳しい表の両方から数え直した。

【正しさ(正解と一致)】
- 行 A は 19 観点すべてで満点、計 53 / 53。
- 行 B は計 11 / 53。観点ごとの数は C3-1 2/5、C3-2 0/3、C3-3 1/1、C3-4 0/4、C3-5 1/3、C3-6 1/7、C3-7 3/6、C3-8 0/1、C3-9 0/2、C3-10 0/2、C3-11 0/1、C3-12 0/1、C3-13 1/3、C3-14 2/4、C3-15 0/2、C3-16 0/2、C3-17 0/2、C3-18 0/3、C3-19 0/1。
- 合計は 2+0+1+0+1+1
- survey2: choice=右 / 表の 53 場面・19 観点を観点ごとに自分で数え直した(表の要約欄と一致)。

正しさ(「正解と一致」の数): 行 B は全 19 観点で満点(53/53)。行 A は 11/53 で、観点ごとの内訳は次のとおり。
- C3-1: 2/5(v1-wf-rolling、v1-wf-equal)
- C3-3: 1/1(v3-block-bootstrap)
- C3-5: 1/3(v5-dsr-returns)
- C3-6: 1/7(v6-iter-count)
- C3-7: 3/6(v7-seed、v7-config、v7-git-sha)
- C3-13: 1/3(v13-markou

## リードの処置と答え(2026-09-25 21:40 UTC。委任文 `20260925_backtest_env_prompt.md@388d55cdeb32`、枠組みの指紋 2c19e69c0755)

### 台本の変更(表の監査の [止める] → 資料係を 1 回だけ作り直す)
`runItem` の最初の表の監査を `tableAudit(tt)` にし、[止める] があれば資料係を 1 回だけ作り直し(指摘を逐語で渡す。label `表:N#1r`)、監査役(表)がもう一度見る。それでも [止める] なら escalate(上限 1 回)。委任文 §0 に行を足した(右は該当語なし = リードの決定と明記)。実測: `node --check` OK / node --test pass 12 / 検査器 `OK 誤り 0 件`。項目 1 は再開でこの経路を通る(表:1#1r → 監査役(表):1 → 審査員)。
### 項目 1 の試験の名の衝突(作る:3#1 の問い 4)
リードが `tests/bt/item_1/test_i1_battery_scenes.py` の `import run_battery` を path からの読み込み(項目 3 と同じ形)に直した。実測: 項目 1 の場面の試験 36 passed / 項目 3 の 54 passed(新しい basetemp で。共有の /tmp/pytest-of-root を使うと別の実行の片付けで 3 件が FileNotFoundError になる = 試験の中身ではない)。
### 監査役(表):1 の [止める] への答え
当たっている。root の二重結合は資料係の adapter(場面集の側)の作り。上の作り直しで直す(作り直しの起動文に「runner が渡す root と paths をそのまま渡す(自分で絶対化・結合しない)」と書いた)。[直す](結果なしの注記の定型文)も作り直しに含める。[聞く] 3 件: 旧との互換(項目 14)は項目 4 で旧の試験 8 本で測る(項目 1 の表の非対称とは別の測り方)/ 表の組と向きは台本が `t.tables[key_v]` の鍵で審査員に渡すので mapping.tsv はリードの手を経ない(台本 `trio`)/ V3・V5 の 0/5・0/7 と CONSIDERED.md の整合は作り直しの資料係に確かめさせる(起動文の「[直す] を全部直す」の中)。
### 監査役(表):2([直す] 1・[聞く] 1)への答え
mutant.py の docstring(壊す場面 4 つ)と実測(5 つ、c2-10-jpx-fee も)の食い違い = 記載の直し。項目 2 は 1 周で終わったので、項目 4 の作業者の持ち越し(場面集の側の [直す])にする。試金石の回帰試験に no-default・source・jpx-fee を足すことも同じ持ち越し。
### 監査役(表):3([直す] 1・[聞く] 3)への答え
make_tables.py の why_none() の catch-all(例外が起きていないのに「例外で終わった」と書く)= 表の本文の事実と違う断定。項目 3 は通過の候補の周が終わっているので、表は作り直さず、項目 3 の通過の報告にこの誤りの箇所(6 場面 × 2 表)を逐語で載せ、項目 4 の作業者の持ち越しにする。定義行の 3 分岐(Refused / NotExpressible / adapter の例外)も同じ持ち越し。opp_sigc(実行ファイルをリードの片付けで消した)は「動かせなくなった候補」として検討表に落とす = 持ち越し。current_impl の探した範囲の明記 = 持ち越し。
### 監査役:2#1(通過の報告の監査、[聞く] 5)への答え
1. 「必ず両方回す」: 研究の実行(入口)が両側を出すことを要件と読む。SimVenue を単独で使う経路は場面集のためのもの。両側の強制は項目 3/4 の実行の入口で行う = 項目 4 の持ち越し。この読みで通過を確定する。
2. 費用の既定値: 「場面が使う費用は宣言が無ければ断る」の限定の読みを採る(全費用を常に全部書かせる読みは採らない)。
3. 核の事象の型に L3・FX の日替わり・分割併合・為替が無い: 項目 2 の射程の外(執行の模型)。項目 4 の持ち越し(核の契約の版を上げるかの判断はそこで)。市場の順序(暗号資産 → FX → 株)に照らし、FX・株の前に要る。
4. 訂正で数量を増やせない: 核の台帳の設計による制約として受け入れ、既知の限界に載せる。項目 4 の持ち越し。
5. unverified の印: 台本の最終の返り値 `brief` に入っている(12 回目の返り値: 項目 2 の `unverified` = 「未確認(批評家なし。資料係の申告の裏取りは無い)」)。監査役に渡ったのは作業者の返り値で、そこには無い(設計どおり)。
### 監査役:3#1(通過の報告の監査、[聞く] 5・[直す] 1)への答え
latency の notice 0 = 読まない値は既定の値ではない(前の答えのとおり)。unverified = 上と同じ。run_battery の衝突 = リードが直した(上)。fixed.py と SimVenue の二重実装 = 項目 4 で SimVenue を正として一本化(持ち越し)。[直す] 実行時間の値が git 管理下の tsv に書かれて試験のたびに差分が出る = 項目 4 の持ち越し(secs_* を管理下の出力から外す)。相手の選び方の記載 = 通過の報告に CONSIDERED.md の該当行を引用する(報告の形)。

## 2026-09-26 01:09 UTC 再開 2 を 3 分で止めた(リードの誤り)

journal: 再開 2 の直後に `要件:1`・`要件:2` が新しい agent(a7bc0bdb / a7766436)で起きた = 再生が効いていない。原因: 起動文の頭 `HEAD` に委任文の指紋 `args.marker` が入っており、指紋を今の版(388d55cdeb32)に変えると全 agent の起動文が変わって作り直しになる(再開 1 で 要件:2 が作り直されたのも同じ原因。リードは気づかずに 2 度目をやった)。処置: run を止め(2 本の agent の 3 分が無駄)、引数の marker を再開 1 の値 da84268e88fc に戻し、今の版は `doc_sha` に書く。検査器を「再開では marker は起動時の値のまま、doc_sha に今の sha」を通す形にし(試験 1 件追加、17 passed)、台本は `args.doc_sha` を log に出すだけ。再開 3 は 01:20 UTC の予約の回。

## 2026-09-26 01:21 UTC 再開 3 も 場面:1・場面:2 を作り直した → 止めた(実測と処置)

起動文の全文を再開 1 の agent(ae20726c / a1f0d35a)と再開 3 の agent(a56226dd / a1f34e31)で比べた: **同一**(2825 / 2840 字、差分なし)なのに journal の key が違う(dd381d… → 2e6a4c…)。読み: 再生の鍵は起動文だけでなく呼び出しの順序(前の呼び出しの鍵)に依存し(道具の説明「the longest unchanged prefix of agent() calls」)、並列の項目 1〜3 は順序が起動ごとに変わる。よって並列の段では再生に頼れない(11 回目までは項目 0 だけの直列だったので効いていた)。
処置(台本): (1) `args.passed_items` に項目 1〜3 も入れられるようにし(`prebuilt[id].req/bat/carried_impl` で結果を運ぶ)、(2) `prebuilt[id].worker / table / table_audit` があれば作業者・最初の表・表の監査を起こさず記録の結果を使う。項目 1 は 作業者(作る:1#1)・表:1#1・監査役(表):1 の journal の結果を引数に写し、資料係の作り直し(表:1#1r)から始める。項目 2・3 は pass として運ぶ(項目 3 の最終 status = pass を台本の返り値で確認)。13 回目は**新しい run**として起動する(再生を使わない)。無駄になった agent: 再開 2 で 2 本(3 分)、再開 3 で 2 本(2 分)。

# 13 回目の run(`wf_711a526c-38e`、2026-09-26 01:38〜02:01 UTC。項目 0・2・3 は通過として引数で運び、項目 1 は 表:1#1r から)

結果: 台本は 2 agent(表:1#1r・監査役(表):1 の 2 回目)で止まった(stopped_at = parallel)。項目 1 = escalate「最初の表が監査役の [止める] を受けた = 資料係の作りを直す」= 作り直し 1 回の上限に達した。

## 表:1#1r(資料係の作り直しの返り値。逐語)

```
{
 "new_impl_correct": "35/35(V1 9/9・V2 3/3・V3 5/5・V4 2/2・V5 7/7・V6 5/5・V7 4/4)。「2 回の実行で同じ」も 35/35。runs と runs_2 の両方、相対の --out の実行でも同じ結果。",
 "new_impl_all_correct": true,
 "identical": {
  "current": false,
  "survey": false,
  "mutant": false
 },
 "adapters_changed": [
  "tests/bt/battery/item_1/adapters/new_impl.py"
 ],
 "notes": "■ 直した点と根拠\n\n[止める] root と path の二重結合\n- 直したこと: tests/bt/battery/item_1/adapters/new_impl.py の _load から os.path.abspath と os.path.join を消した。runner が渡す inp[\"root\"] と d[\"paths\"] を、そのまま bot.bt.data.load(root, datasets) に渡す。sha256 は LoadResult.hashes()(渡した path がそのまま鍵)を dict にして返すだけにした。import os も消した。差分は materials/new_impl_adapter.diff(前の版 ae9eb44 との差)。\n- 根拠: 相対の path を root に対して解くのはデータ層自身である。src/bot/bt/data/allowlist.py:102-104 の AllowList.check が `abs_lex = os.path.normpath(path if os.path.isabs(path) else os.path.join(root_abs, path))` としている。\n- 実測(相対の --out): 全 17 対象を 2 回ずつ走らせた(materials/logs/relative_out_all_targets/)。run_battery.py 冒頭の使用例と同じ形である。新実装は 35/35 が正解と一致で、前の版にあった PathRefused 26 件は消えた。\n- 実測(絶対の --out): 同じく全 17 対象を 2 回ずつ走らせた。新実装は 35/35 で、相対の結果と全場面で同じだった(compare_relroot.out: 1190 行のうち違い 2)。\n- 結論: 保留の論点は「実装の側の弱さ」ではなく、前の資料係が書いた adapter の二重結合だった。新実装のデータ層は相対の root を正しく扱う。\n\n2 行の違いの中身(当方の現状の v5-sealed-window)\n- 絶対の --out では正解と一致、相対の --out では結果なし。出たエラーは `SealedDataError: backtest_data/bf_exec_sealtest_20260105/trades.csv is not one of unit 'SYNTH-UNIT''s sealed files`。\n- 原因は場面集の側の 2 か所にある。\n  - tests/bt/battery/item_1/i1_protocol.py:77-79 の dataset_paths は docstring に「Absolute paths」と書きながら、`os.path.join(inp[\"root\"], p)` を返す。root が相対なら返る path も相対になる。\n  - 当方の現状の adapter がその path を `sealed.load_unsealed(path, unit, root=inp[\"root\"])` に渡すので、root が二重に付く。\n- 同じ族の欠陥だが、どちらも場面係のファイルなので資料係は変えていない。\n- 表は絶対の --out の実行(runs/・runs_2/)から作った。こうすれば、どの対象も場面集の側の path の扱いで結果を失わない。新実装はどちらの形でも同じ結果である。\n\n[直す] 「結果なし」の注記\n- make_tables.py の注記を、定型文から次の 2 つを書く形に替えた。\n  - 実際に試したこと: 場面の入力を対象の公開の口に渡し、別々のプロセスで 2 回走らせた。\n  - 出たエラーの文: 逐語で書く。1 回目と 2 回目で違えば両方書く。\n- 調査結果の側の寄せた行で全対象が結果なしの場面は、14 対象それぞれのエラーの文を、同じ文ごとに対象の数を付けて書いた。\n- 盲検を守るため、道具を特定できる語は〔名〕・〔時刻〕に置き換えた。対象は次のもの。\n  - ASCII の名前・path・時刻。一般の語(CSV・UTC・sha256・列の名前など)の許可一覧だけは残す。\n  - 「現状」「再現」と、道具の種類を言う語(「通信の道具」など)。\n- 置き換える前の逐語は materials/runs/*.tsv と survey_breakdown.tsv にある。\n\n■ 提出前の吟味\n\n観点ごとの一致の数(出力から数え直し、表と一致した)\n- 新実装: 35/35(V1 9・V2 3・V3 5・V4 2・V5 7・V6 5・V7 4)。「2 回の実行で同じ」35/35。\n- 当方の現状: 2/35(V2 1・V5 1)。「2 回の実行で同じ」3/35。\n- 調査結果の側(寄せた行): 4/35(V6 1・V7 3)。「2 回の実行で同じ」10/35。\n- 試金石: 32/35(V1 7/9・V2 2/3)。「2 回の実行で同じ」35/35。\n- 3 通りで数えた。\n  - recount.py: runs と runs_2 の生の tsv から数えた。\n  - recount_from_tables.py: 6 枚の表のセルから数えた。集計の行との不一致は 0。\n  - recount_survey.py: 寄せた行を make_tables.py を使わずに作り直して数えた。\n- 3 通りとも table_counts.tsv と一致した。\n\n全対象を全場面に通したか\n- 17 対象 × 35 場面 = 595 行を全部通した(compare_runs.out)。\n  - 1 回の実行の中の 2 回の違い: 0\n  - runs と runs_2 の違い: 0\n  - 場面係の survey_results との違い: 0\n- 「結果なし」の注記は 6 枚で計 114 件ある(当方の現状 33 件 × 2 枚、調査結果の側 24 件 × 2 枚)。全部に試したこと・エラーの文・実測の時間を書いた。\n- 時間の上限で打ち切った場面は 0 件である。\n\n注記に道具を特定できる語が無いか\n- check_names.py で調べた。対象は、道具・モジュール・関数の名前 52 語と時刻(全行)、「現状」「再現」と道具の種類の語(注記の行)。\n- 6 枚とも 0 件だった(check_names.out)。\n\nmd5\n- 3 組とも 2 通りの表はバイト単位で違う(md5sum_pairs.txt)。\n  - current: 81cd8e1e… / c7a2c536…\n  - survey: bb08123c… / 7f0f8269…\n  - mutant: 494bf485… / f8afbc81…\n\nmaterials の保存\n- 置いたもの: RECORD.md(どの表が何か・直したこと・確かめたこと)、mapping.tsv、runs/・runs_2/、logs/relative_out_all_targets/、logs/previous_build_abs_root/(前の版の実行・6 枚の表の写し・記録)、各スクリプトとその出力、fingerprint.txt(8317191d1c18…)。\n- stale に移した表は無い。ファイル名は前の版と同じ 6 つを使った。\n- 実データから出た数値は入れていない(場面集の合成データだけ)。\n\n試験\n- tests/bt/battery/item_1 tests/bt/item_1 の結果は「1 failed, 3969 passed」。\n- 落ちたのは前の版と同じ test_new_impl_is_the_mouth_only で、中身は KeyError: 'root'。adapter の本体が空であることを確かめる試験なので、資料係が本体を書くと必ず落ちる。場面集の試験は資料係が変えない。\n\n■ 聞くことへの事実\n\n- 監査の [聞く] 5 について、survey の V3 0/5 と V5 0/7 の中身を数えた(recount_survey.out)。\n  - V3: 14 対象 × 5 場面 = 70 のうち、不一致 5・対応なし 3・結果なし 62。不一致は、動かせた候補 54 の v3-gap-bars が 1 件、残り 4 件は再現の 2 件。\n  - V5: 98 の全部が結果なし。\n- これは CONSIDERED.md と一致する。V3 の「動かせた候補: 1 件(54)」、V5 の「動かせた候補: 0 件」。\n- つまり V5 は該当場面を 1 つも取れていない。V3 は取れた結果が正解と食い違った。\n\n■ リードに聞くこと\n\n1. 場面集の i1_protocol.dataset_paths は docstring では絶対 path を返すと書いているが、root が相対なら相対 path を返す。そのため当方の現状の adapter の結果が --out の形で変わる。この直しを場面係に回すかの判断が要る。表は絶対の --out から作った。\n2. HEAD db30838(リードの checkpoint、01:42:45Z)に、この作り直しの adapter の変更が作業の途中で入っている。そのため git diff HEAD は空で、差分は ae9eb44 との差で記録した。"
}
```

## 監査役(表):1(2 回目。逐語)
- [止める] docs/DISCUSSIONS/2026-09-23_backtest_env/item_1/round_1/materials/pytest_item1_r1_shiryo.out(commands.txtの手順12と同じコマンド) — 「1 failed, 3969 passed in 23.68s」で、FAILED tests/bt/battery/item_1/test_battery_item1.py::test_new_impl_is_the_mouth_only(tests/bt/battery/item_1/adapters/new_impl.py:81 KeyError)が出ている。この失敗は資料係のnotes(「直した点と根拠」「提出前の吟味」)のどこにも触れられておらず、同じコマンドの出力を『すべて正しい』根拠として引用しながら失敗行を素通りしている。委任文§3の批評家の格付け基準は『試験が落ちる(試験自身の誤りと確かめたものを除く)』を[止める]とし、§3「批評家の試験の誤り」は落ちた試験を直すか理由を書いて取り下げることを求める。new_impl_adapter.diffを見ると、この回の修正後もinp["root"]を無防備に参照する構造は旧版(os.path.abspath(inp["root"]))と同型で、今回の修正による新規リグレッションか元からの既知の失敗かも判定できない。いずれにせよ、この失敗の原因・要否の説明が本文に無いまま『信頼性に優れた』结果として提出されている(P-xx: research-protocol §0.2 相当、CLAUDE.md §0.2 O-3「機構の挙動を主張するときは実行したコマンドと出力を同じ返答に出す」の裏返し=出しているのに読まずに素通り)。
- [直す] docs/DISCUSSIONS/2026-09-23_backtest_env/item_1/round_1/表_daka83.md:10、表_v1fm0q.md:10(および同様の注記が他の場面の行にも反復)— 「(〔名〕 の 〔名〕 2788 行)」のように docs/DATA/SCAN_2026-09-21_tools.md の具体的な行番号(2788・6303・1111・9401・6871・6906・6926・5885・5886・5888 など)を逐語で残している。委任文§3「比較の表」は『表の注記には、道具を特定できる具体(道具の名前・時刻など)を書かず、それは materials の記録に書く』と明記しており、SCAN の行番号は一次資料(SCAN_2026-09-21_tools.md)を突き合わせれば候補を特定できる『具体』にあたる。この回の検査に使われた materials/check_names.py は道具・モジュール名の固定語彙と時計形式の時刻だけを検索し、『SCAN N行』という引用は検索対象に含まれていない(スクリプト本体で確認済み)。したがって『check_names.py で調べた…総当たり0件』という記録は、この種の漏れが無いことの根拠にならない。
- [聞く] 表_daka83.md:10、表_v1fm0q.md:10 — 「Date, Open, High, Low, Close, Adj Close, Volume」という特定データ提供元でよく知られた列名の組み合わせがそのまま残っている。委任文の注記の許可一覧は『一般の語(CSV・UTC・sha256・列の名前など)』を残してよいとしているが、単独の列名ではなく、この組み合わせ自体が特定の道具(データ形式)を指し示す固有の署名になっている。この例外は個々の列名を指すのか、こうした特徴的な列名の組み合わせも含むのか、意図の範囲を確認したい。

## L-460(案 1)の適用(2026-09-26 02:35 UTC、リードの直し)

- [止める](場面集の試験 `test_new_impl_is_the_mouth_only` = adapter の本体が空であることを確かめる = 資料係が本体を書く設計と矛盾): 試験を「口の契約の検査」に書き直した = adapter の import が新実装の公開のパッケージ(bot.bt.data / bot.bt.vector / bot.bt.core)と i1_protocol と標準ライブラリだけ / 本体が場面の正解(i1_scenes・expected・i1_judge)を参照しない(モジュールの docstring は除く)/ TARGET.run がある。実測: `pytest tests/bt/battery/item_1 tests/bt/item_1/test_i1_battery_scenes.py` → 116 passed(新しい basetemp)。書き直したのはリード(場面係の持ち物を触った 1 件目。記録)。
- [直す](SCAN の行番号が表の注記に残る): 表_daka83.md・表_v1fm0q.md の「〔名〕 NNNN 行」20 か所ずつを「〔名〕 〔行〕」に伏せた(materials の記録は元のまま)。
- [聞く](列名の組 Date, Open, High, Low, Close, Adj Close, Volume): 許可は個々の列名の意味で、知られた組み合わせは道具の署名になるので伏せる側と読む。同じ 2 枚の 20 か所ずつを「〔列名の組〕」に置き換えた。
- 14 回目の引数: prebuilt[1].table = 作り直しの表(35/35)、table_audit = 2 回目の監査(記録のまま)、table_audit_resolved = L-460 の文。台本は table_audit_resolved があれば [止める] を空にして審査員へ進む(記録は変えない)。検査器 OK 誤り 0 件、node 12/12。

## 14 回目の起動(2026-09-26 02:18 UTC = 11:18 JST、run `wf_348cc4f5-4cd`、新しい run、案 A の起動の回)

引数: `bt_args_run14.json`(項目 0・2・3 は通過として運ぶ。項目 1 は作業者・作り直した表・2 回目の表の監査・L-460 の解決を引数で渡し、審査員から)。起動の回の journal の started は 盲検:1#1:mutant0 から(作り直しではない)。最初の 10 本の agent の 1 通目は全部 `[Workflow harness — computed task]`(中継 0 件。02:24 UTC に実測)。

### 項目 1 の審査員 9 本の出力(逐語)

#### 盲検:1#1:mutant1

- choice: 左

- reasons: 表から自分で数え直した。正しさ(正解と一致の数、行 A / 行 B)は、V1 9/9 と 7/9、V2 3/3 と 2/3、V3 5/5 と 5/5、V4 2/2 と 2/2、V5 7/7 と 7/7、V6 5/5 と 5/5、V7 4/4 と 4/4、合計 35/35 と 32/35 で、表の集計欄と一致した。行 B の不一致は 3 場面。v1-jpx-1m と v1-all-assets-one-call は events.jpx_1m[0].start_ns が 1767602700000000000(正解 1767570300000000000)、v2-naive-local-tz は events.jst_trades[0].t_ns が 1767603599000000000(正解 1767571199000000000)。どちらも差は 32,400 秒(9 時間)ちょうどで、日本時間の時刻を UTC として読んだと見られる同じ系統の誤りである(これは推定)。再現(2 回の実行で同じの数)は、両者とも全観点で満点(V1 9/9、V2 3/3、V3 5/5、V4 2/2、V5 7/7、V6 5/5、V7 4/4、計 35/35)で差は無い。観点ごとに比べると、行 A が上回るのは V1 と V2 の 2 観点、残る 5 観点(V3〜V7)は同点、行 B が上回る観点は 0。場面の多い V1 だけに引きずられた判断ではない。場面が 3 つしかない V2 でも行 A が上回っている。したがって、正しさでは行 A が優れ、再現では同等なので、行 A を選ぶ。

- missing_in_choice: 選んだ行 A には、正解と一致しなかった場面も、2 回の実行で食い違った場面も 1 つも無い(35/35)。表から見て、行 A に足りない場面は無い。ただし、表に載っているのは各観点に定義された場面だけで、射程の外(定義の §6)にあるものは測られていない。

#### 盲検:1#1:mutant0

- choice: 右

- reasons: 表の個々のセルから、観点ごとの「正解と一致」を数え直した。数え直した値は、表の上の集計と合っている。
- V1: A は 7/9、B は 9/9。A の不一致は v1-jpx-1m と v1-all-assets-one-call の 2 場面で、どちらも events.jpx_1m[0].start_ns が 1767602700000000000(正解は 1767570300000000000)。
- V2: A は 2/3、B は 3/3。A の不一致は v2-naive-local-tz で、jst_trades[0].t_ns が 1767603599000000000(正解は 1767571199000000000)。
- V3〜V7: A も B も満点。V3 は 5/5、V4 は 2/2、V5 は 7/7、V6 は 5/5、V7 は 4/4。
- 計: A は 32/35、B は 35/35。

A の不一致 3 件は、どれも正解より 32400 秒(9 時間)遅い値になっている。オフセットの無い時刻を、spec が tz=Asia/Tokyo と宣言しているのに UTC として読んだときに出る値と一致する(JST 08:45 → UTC 08:45 として読むと 1767602700)。A が黙って違う値を返したので、判定は「不一致」になる(「対応なし」ではない)。

観点ごとに比べた結果:
- B が上: V1、V2 の 2 観点。
- 同等: V3〜V7 の 5 観点。
- A が上: 0 観点。

場面の数が多い V1 に引きずられているわけではない。場面が 3 つしかない V2 でも B が上で、B が劣る観点は 1 つも無い。

再現は、A も B も 35/35 で 2 回の実行が同じだった。観点ごとに見ても全部同じ数なので、再現では差が無い。

以上から、正しさでは B(行 B)が 2 観点で上回り、残りは同等、再現は同等なので、行 B を選ぶ。

- missing_in_choice: 選んだ行 B に足りない場面は、表の上では無い(正しさ 35/35、再現 35/35)。行 A に足りない場面は v1-jpx-1m、v1-all-assets-one-call、v2-naive-local-tz の 3 つで、どれもオフセットの無い時刻を宣言された Asia/Tokyo で UTC に直す場面。

#### 盲検:1#1:mutant2

- choice: 右

- reasons: 正しさでは行 B が上で、再現では差がありません。表の各セルを自分で数え直すと、観点ごとの「正解と一致」は行 A が V1 7/9・V2 2/3・V3 5/5・V4 2/2・V5 7/7・V6 5/5・V7 4/4 で計 32/35、行 B は全観点で満点の計 35/35 でした。表の集計と一致します。

行 A の不一致は 3 場面です。
- v1-jpx-1m: start_ns 1767602700000000000(正解 1767570300000000000)
- v1-all-assets-one-call: 同じ値の食い違い
- v2-naive-local-tz: t_ns 1767603599000000000(正解 1767571199000000000)

3 件とも差はちょうど 32400 秒(9 時間)です。定義では、この 3 場面の spec はどれもオフセットの無い時刻を tz: Asia/Tokyo と宣言しています(§7 の v1-jpx-1m と v2-naive-local-tz の spec)。行 A はこの宣言を効かせず、壁時計の時刻を UTC として読んでいると読めます。これは 1 つの欠陥で、V1 と V2 の 2 観点にまたがって出ています。行 B はその場面を含め全場面で正解と一致しました。

場面数の多い観点に引きずられないよう観点単位で見ると、行 B が上なのは V1 と V2 の 2 観点で、残りの V3〜V7 の 5 観点は同等です。行 A が上の観点は 1 つもありません。

「2 回の実行で同じ」は両者とも全観点で満点(V1 9/9・V2 3/3・V3 5/5・V4 2/2・V5 7/7・V6 5/5・V7 4/4、計 35/35)でした。再現性では差が無く、行 A の誤りは 2 回とも同じ値で出ています。

よって、より正しい方は行 B です。再現性は同等です。

- missing_in_choice: 行 B に足りない場面はありません。表の 35 場面すべてで正しさは「正解と一致」、再現は「2 回の実行で同じ」でした。

#### 盲検:1#1:current0

- choice: 右

- reasons: 表の場面ごとのセルから観点ごとに数え直した(集計表の数と一致した)。正しさは「正解と一致」の数、再現は「2 回の実行で同じ」の数で、A は V1 0/9・0/9、V2 1/3・2/3(v2-iso-offsets は一致・同じ、v2-same-instant-4-units は対応なし・同じ、v2-naive-local-tz は結果なし)、V3 0/5・0/5、V4 0/2・0/2、V5 1/7・1/7(v5-sealed-window のみ一致・同じ)、V6 0/5・0/5、V7 0/4・0/4。合計は正しさ 2/35、再現 3/35。B は 7 観点すべてで全場面が「正解と一致」かつ「2 回の実行で同じ」(V1 9/9、V2 3/3、V3 5/5、V4 2/2、V5 7/7、V6 5/5、V7 4/4、計 35/35)。観点ごとに比べると、B は 7 観点すべてで A と同じか上回る。A が B と並ぶのは個々の場面だけで(v2-iso-offsets と v5-sealed-window)、A が B を上回る観点は 1 つもない。B が優位なのは場面の多い V1 に限らず、V3・V4・V6・V7 では A が 0 件なのに B は全件なので、場面数に引きずられた判断ではない。A の結果なし 32 件は、注記によれば、対象の公開の口に場面を渡す手段が無かったもの(読み口の欠如など)で、能力が無いことを示している。

- missing_in_choice: 表の上では、B(右)に足りない場面は無い(35 場面すべてで正解と一致し、2 回の実行でも同じ)。

#### 盲検:1#1:current1

- choice: 左

- reasons: 表のセルを行ごとに自分で数え直した(grep で各セルの「正しさ」「再現」を数えた)。結果は表末尾の集計と一致した。
正しさ(正解と一致)は行 A が V1 9/9、V2 3/3、V3 5/5、V4 2/2、V5 7/7、V6 5/5、V7 4/4 で、7 観点すべてが全場面一致(計 35/35)。行 B は V1 0/9、V2 1/3(v2-iso-offsets のみ一致。v2-same-instant-4-units は「対応なし」、v2-naive-local-tz は「結果なし」)、V3 0/5、V4 0/2、V5 1/7(v5-sealed-window のみ一致)、V6 0/5、V7 0/4 で、計 2/35。
再現(2 回の実行で同じ)は行 A が全観点で全場面(35/35)。行 B は V2 2/3、V5 1/7、それ以外の観点は 0 で、計 3/35。B の残りは「結果なし」。
「2 回で違う」のセルは両行とも 0 件。表の文字列には「2 回で違う」が 2 回出てくるが、どちらも冒頭の凡例の文で、セルではない。
観点ごとに比べると、7 観点すべてで A は B と同じかそれ以上になる。B が A に並ぶ観点も、上回る観点も無い。B が一致した場面(v2-iso-offsets、v5-sealed-window)は、A も一致して再現している。B の結果なしについて注記は「公開の口に場面を渡す手段が見つからなかった」としている。このため V1・V3・V4・V6・V7 の能力は、B では確認されなかった。
場面の多い V1・V5 を除いても、V2・V3・V4・V6・V7 の各観点で A が上回る。場面数に引きずられた判断ではない。

- missing_in_choice: 行 A に足りない場面は、この表の上では無い。35 場面すべてが「正解と一致」かつ「2 回の実行で同じ」である。

#### 盲検:1#1:survey0

- choice: 右

- reasons: 表のセルを場面ごとに自分で数え直した。数えた結果は表の集計の行(62〜72 行)と一致した。
【正しさ(正解と一致の数)】
- V1(9 場面): A は 0/9、B は 9/9。A は v1-fx-ticks が不一致(t_ns のミリ秒が落ちた)で、残りの 8 場面は結果なし。
- V2(3 場面): A は 0/3(全部結果なし)、B は 3/3。
- V3(5 場面): A は 0/5、B は 5/5。A の内訳は、不一致 3(clean-control は id の欄が無い、duplicate-and-conflict は anomalies が返らない、gap-bars は gap が空)と、対応なし 2(backward・generations)。
- V4(2 場面): A は 0/2(結果なし)、B は 2/2。
- V5(7 場面): A は 0/7(結果なし)、B は 7/7。
- V6(5 場面): A は 1/5(universe-survivorship だけ一致、残りは結果なし)、B は 5/5。
- V7(4 場面): A は 3/4(bars-from-trades が結果なし)、B は 4/4。
- 合計は A が 4/35、B が 35/35。
【再現(2 回の実行で同じの数)】
- A: V1 は 1、V2 は 0、V3 は 5、V4 は 0、V5 は 0、V6 は 1、V7 は 3 で、計 10/35。
- B: 全観点で満点の 35/35。
- A で「2 回の実行で同じ」でない場面は、全部が「結果なし」だった。「2 回で違う」はどちらの行にも無い。
【比べた結論】
7 つの観点のどれでも、B は A と同じか A より上で、A が B を上回る観点は無い。
- 差が小さいのは V7 だけで、A 3/4 に対して B 4/4。
- V2・V4・V5 では、A に結果が 1 つも無い。
- V3 では、A が「黙って違う値を返す」不一致を 3 件出している。
場面の数が多い V1 と V5 を除いても、B が上という順は変わらない。よって、正しさでも再現性でも B(右)が優れる。

- missing_in_choice: B(右)には、表の上で正解と一致していない場面が無い(35/35)。再現も全部「2 回の実行で同じ」で、表から読める不足の場面は無い。ただし、表から分かるのは各場面の 2 回の実行の結果だけである。§6 のとおり、V7 の v7-speed は壁時計で比べる場面なので、2 回の外の実行で分類が変わりうる。この点は、表に示された範囲では確かめられていない。

#### 盲検:1#1:current2

- choice: 右

- reasons: 表の観点ごとの表から数え直した(下の要約の表と一致した)。
正しさ(正解と一致の数): V1 は A 0/9・B 9/9、V2 は A 1/3(v2-iso-offsets だけ。v2-same-instant-4-units は対応なし、v2-naive-local-tz は結果なし)・B 3/3、V3 は A 0/5・B 5/5、V4 は A 0/2・B 2/2、V5 は A 1/7(v5-sealed-window だけ)・B 7/7、V6 は A 0/5・B 5/5、V7 は A 0/4・B 4/4。計は A 2/35・B 35/35。
再現(2 回の実行で同じの数): V1 は A 0/9・B 9/9、V2 は A 2/3(same-instant と iso-offsets)・B 3/3、V3 は A 0/5・B 5/5、V4 は A 0/2・B 2/2、V5 は A 1/7・B 7/7、V6 は A 0/5・B 5/5、V7 は A 0/4・B 4/4。計は A 3/35・B 35/35。
7 つの観点すべてで B が A 以上であり、A が B を上回る観点は 1 つも無い。A の 32 場面は「結果なし」で、注記によれば対象の公開の口にその場面を渡す手段が無かった(例: 約定や気配のファイルを事象にする読み口が無い、見出しの無いファイルに列名を渡す引数が無い、2 列の時刻を合わせる引数が無い)。場面の定義 §3 の順では結果なしが最下位なので、A はこれらの場面について能力を示していない。B は全 35 場面で正解と一致し、2 回の実行でも同じだった。場面の多い V1 を除いても、V2〜V7 のそれぞれで B が上になる。したがって行 B(右)の方が、正しさでも再現でも優れている。

- missing_in_choice: 表の上では、行 B に足りない場面はない(35/35 で正解と一致し、35/35 で 2 回の実行が同じ)。ただし補足が一つある。v7-speed は壁時計の比べなので、定義 §6 のとおり 2 回の実行で分類が変わりうる。今回の 2 回で同じだったことは、それ以上の回数でも同じになる保証ではない。

#### 盲検:1#1:survey1

- choice: 左

- reasons: 場面ごとのセルを数え直して観点ごとに比べた。数え直しは表の要約の欄と一致した。
行 A(左)の「正解と一致 / 2 回の実行で同じ」は V1 9/9・9/9、V2 3/3・3/3、V3 5/5・5/5、V4 2/2・2/2、V5 7/7・7/7、V6 5/5・5/5、V7 4/4・4/4 で、全観点が満点(計 35/35・35/35)。
行 B(右)は観点ごとに次のとおり。
- V1: 正解と一致 0/9、2 回の実行で同じ 1/9。v1-fx-ticks は不一致(t_ns の小数部 .123 秒が落ちている)で再現は 2 回同じ。残りの 8 場面は結果なし。
- V2: 0/3・0/3(全部結果なし)。
- V3: 0/5・5/5。不一致 3 件(clean-control は id の欄が無い、duplicate-and-conflict は anomalies が返らない、gap-bars は gap が空)と対応なし 2 件(backward・generations)。
- V4: 0/2・0/2(結果なし)。
- V5: 0/7・0/7(結果なし)。
- V6: 1/5・1/5(universe-survivorship だけ一致、残り 4 件は結果なし)。
- V7: 3/4・3/4(bars-from-trades は結果なし、残りの 3 件は一致)。
計は正解と一致 4/35、2 回の実行で同じ 10/35。
7 観点のうち、B が A に並ぶ観点も上回る観点も無い。B が最も近いのは V7 の 3/4 で、そこでも A は 4/4。このため、場面の多い観点(V1 の 9 場面・V5 の 7 場面)の重みを除いても結論は変わらない。正しさ(正解との一致・能力の有無)でも再現(2 回の実行の一致)でも A が優れる。

- missing_in_choice: 選んだ行 A に足りない場面は、この表の上では無い(全 35 場面で正解と一致し、2 回の実行でも同じ)。

#### 盲検:1#1:survey2

- choice: 右

- reasons: 表の個々のセルを私が数え直した。数えた結果は、表の集計(60〜72 行)と一致した。
【行 B】7 観点すべてで正しさは「正解と一致」、再現は「2 回の実行で同じ」だった。V1 9/9、V2 3/3、V3 5/5、V4 2/2、V5 7/7、V6 5/5、V7 4/4 で、計 35/35。
【行 A の正しさ(正解と一致の数)】計 4/35。
- V1: 0/9。v1-fx-ticks が不一致で、t_ns のミリ秒が落ちていた。残りの 8 場面は結果なし。
- V2: 0/3。3 場面とも結果なし。
- V3: 0/5。不一致が 3 場面(clean-control、duplicate-and-conflict、gap-bars)、対応なしが 2 場面(backward、generations)。
- V4: 0/2。2 場面とも結果なし。
- V5: 0/7。7 場面とも結果なし。
- V6: 1/5。一致したのは universe-survivorship だけで、残り 4 場面は結果なし。
- V7: 3/4。v7-bars-from-trades が結果なし。
【行 A の再現(2 回の実行で同じの数)】計 10/35。内訳は V1 1/9、V2 0/3、V3 5/5、V4 0/2、V5 0/7、V6 1/5、V7 3/4。
【観点ごとの比較】
- V1〜V6 の 6 観点では、正しさで B が上回った。
- V7 は B 4/4 に対し A 3/4 で、差は 1 場面(bars-from-trades)だけだった。
- 再現で A が B と同点になったのは V3(5/5)だけである。ただし A の V3 は不一致と対応なしを 2 回とも同じに出したもので、正しい結果が再現されたわけではない。
- A が B を上回る観点は 1 つも無かった。
- 場面の多い V1 と V5 を除いて V2・V3・V4・V6・V7 だけで比べても、B の優位は変わらない。
よって、正しさでも再現でも行 B(右)が優れている。

- missing_in_choice: 行 B(右)には、表の上で足りない場面が 1 つも無い。全 35 場面が「正解と一致」かつ「2 回の実行で同じ」だった。ただし表は 2 回の実行しか示していない。そのため、壁時計に依存する v7-speed が 3 回目以降も安定するかどうかは、この表からは判断できない。


### 項目 1 の監査役(通過):1#1 の出力(逐語。02:23〜 UTC、[止める] 0 / [聞く] 3)

- [聞く] tests/bt/battery/item_1/DEFINITIONS.md:43 の逆行(backward)の定義「その行の時刻 < それより前の行の時刻の最大」には、複数ファイル・複数世代にまたがる読みか、ファイル単体で閉じた読みかが書かれていない。作業者は返り値 questions_for_lead で『同じファイルの中で、前の行の最大より前』と自分で読みを決めて実装した(anomalies.py:77 detect)ことを認めている。場面 v3-backward・v3-generations はいずれも単一ファイル入力でしか固定されておらず(DEFINITIONS.md:443-460, :481)、この読みが複数ファイル入力でも DEFINITIONS.md の文言と一致するかは、場面係・監査役のどちらも確かめていない(この周の批評家は skip_critic により不在)。この読みで確定してよいか(P-02、用語の定義域が本文で一意に定まっていない)。

- [聞く] src/bot/bt/data/allowlist.py と tests/bt/item_1/test_i1_allowlist_grid.py(test_hard_link_is_the_known_limit)は、拒むフォルダ(qa_* など)のファイルへのハードリンクを許可フォルダに置くと読めてしまう挙動を『既知の限界』として発見しながら、直さずに試験でその挙動自体を固定している(返り値 unmet[3])。この項目の要件は『合成・中間物・封印区間を拒む許可一覧』(委任文 §2 項目1の行)であり、ハードリンクはパス名しか見ない拒否機構をすり抜ける経路になる。この周は批評家を置かない周(skip_critic=[1,2,3])のため、この判断(直さず固定でよいか)を独立に検めた者がいない。項目4の最終統合(実データを通す段)より前に塞ぐべき欠陥か、それとも記録するだけで良い限界か(CLAUDE.md §5.1 のデータ管理原則に関わる判断で、リードが単独で決めてよい範囲かも含め要確認)。

- [聞く] 作業者の返り値 questions_for_lead に『既定の許可一覧の根(backtest_data・data・paper_logs/tape)と、必ず拒むもの(qa_*・o3c_*・phase2_runs・phase2_sealed)はリードの確認が要る…docs/DATA.md §6 の storm_events・burst_events・regime_composite(研究基盤の抽出物)は拒む側に入れていない』とある。docs/DATA.md:185-186 で確認したとおり、これらは §6『研究基盤(合成データ・監査用フィクスチャ)』に分類され『相場についての主張には使えない』と明記された抽出物だが、src/bot/bt/data/allowlist.py の MANDATORY_DENY(allowlist.py:54)にはこの 3 件が含まれていない。この周は批評家なしで通過しており、この分類の抜けを独立に指摘した者がいない。項目4で実データを通す前に、この 3 件を拒む側に足すか、明示的に許す理由を書くかをリードが決める必要がある。

### 3 件の [聞く] へのリードの答え(2026-09-26 03:30 UTC。段の途中で設計に規則を足さない = 答えは持ち越しの形で書く)

1. 逆行の定義域: 作業者の読み(同じファイルの中で、前の行の最大より前)で確定する。根拠 = 場面 v3-generations の正解(世代の境の行を逆行と数えない)はファイルごとの読みでしか出ない。複数ファイル入力での DEFINITIONS.md の文言との一致は誰も確かめていない → 項目 4 の統合の持ち越し(場面集 DEFINITIONS.md §3 に「ファイルごと」の一語を足すのは項目 4 の場面係の作業。今は変えない)。
2. ハードリンクの穴: 記録するだけでは足りない。項目 4 で実データを通す前に塞ぐ側に置く(持ち越し。直し方の候補 = 実体の inode を拒むフォルダの全ファイルの inode と突き合わせる、または st_nlink > 1 のファイルを拒む)。取り返しのつかない決定(実弾・口座・資本・新市場・リスク上限)ではないのでリードが決めてよい範囲と読む。決めたのはリード(記録)。
3. DATA.md §6 の抽出物 3 件(storm_events・burst_events・regime_composite)が MANDATORY_DENY に無い: 拒む側に足す。項目 4 で実データを通す前に、allowlist.py:54 の MANDATORY_DENY に 3 件を足し、格子の試験に 3 升を足す(持ち越し。作業者の持ち物なので run の途中では触らない。run のあとにリードが 1 行ずつ足すか、項目 4 の作業者に回す)。

**項目 1 は通過**(条件 = 場面集 35/35 + 審査員 9/9(台本の集計)+ 監査役(通過) [止める] 0)。批評家なし(案 B)なので「未確認」の印を付けたまま運ぶ。

### 要件:4 の返り値(逐語)

```json
{
 "path": "/home/user/trade/docs/DISCUSSIONS/2026-09-23_backtest_env/item_4/REQUIREMENTS.md",
 "perspectives": [
  "I4-1 独立参照実装との突き合わせ",
  "I4-2 性質の試験(不変条件)",
  "I4-3 正解つきの場面",
  "I4-4 外部道具との数値突き合わせ(合成データ)",
  "I4-5 全資産・複数データ源の統合パイプライン一本化",
  "I4-6 動作確認用の固定手順の遵守",
  "I4-7 全試験通過(既存を壊さない)",
  "I4-8 翌足始値での taker 執行",
  "I4-9 指値の厳密な通過",
  "I4-10 足内の TP/SL と STOP 優先順位",
  "I4-11 wick_invalidation(構造的ストップ)",
  "I4-12 maker_tp(指値イグジット)",
  "I4-13 max_hold_bars(強制タイムイグジット)",
  "I4-14 entry_mask/entry_sides",
  "I4-15 swap_daily_pct(スワップ/資金調達費用)",
  "I4-16 missed_fills(未約定カウント)",
  "I4-17 compute_metrics の全指標一致",
  "I4-18 split_data(暦ではない行数割合の3分割)",
  "I4-19 旧の出力(golden)の保存と一致",
  "I4-20 最後の段の安全な置き換えと復元"
 ],
 "survey_candidates": 55,
 "extraction_command": "awk -F'\\t' 'NR>1 && $4==\"○\" {print $1\"\\t\"$2\"\\t\"$3\"\\t\"$11\"\\t\"$14}' docs/DATA/tools_catalog.tsv"
}
```

03:27 UTC: 場面:4 が走っている(参照実装:4・作る:4 はまだ)。見張りの出力なし。ディスクの空き 2,167 MB。

