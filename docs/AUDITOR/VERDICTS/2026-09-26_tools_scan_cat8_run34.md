# 検収: 道具サーベイ 区分 8 の 34 回目(2026-09-26、リード)

対象: `docs/DATA/SCAN_2026-09-23_tools_cat8.md` の `## 区分8 — 34 回目の実行(2026-09-26)`(45966 行目から)/ 生ログ `docs/DATA/probes/20260923_tools_8_run34.log`(43,550 バイト)。受け取ったままの形はコミット e52f717。

## 0. 費用と時間

調査班 360,953 トークン・1,299,233 ms(21.7 分)・道具 104 回。

## 1. 受け入れ検査(リードが打ち直した)

`check_scan_report.py`(34 本)`---- 合計 61 件` / `check-elements --round 34` 0 件 / `check "" run34.log` 0 件 / 過去の節から消えた行 0。見出しの行 17 本の全部に `[sandbox …]` がある(`grep '^--- ' run34.log | grep -c sandbox` → 17)。`find /tmp -maxdepth 1 -newermt '2026-09-26T20:31:00'` → `/tmp` 自身だけ、`find /root -xdev -newermt '2026-09-26T20:31:00' -not -path '/root/.claude/*' -type f` → 出力なし。

## 2. リードが見つけたこと(監査の前)

1. **E4 は `未判別` のまま、案 B の記録あり**。見積もり `files_with_hits=1661 total_lines=14613`(500 行超)。文書 347 頁の道と題、ソースの全 3,565 ディレクトリへの語の機械的な選び方は、どちらも 0 件(リードが打ち直した: `doc_titles.txt` 347 行に E4 の語の組 → 0、`find src/spark -type d` に同じ語 → 0)。加えて `chronolog|time.order|…` の全文検索で 20 ファイル、33 回目の Kafka 連携の頁の読み直し。
2. **Auto CDC の逐語**(`docs/declarative-pipelines-programming-guide.md`「It is what lets Auto CDC apply events by their intended order rather than the order they happen to land in.」、`Changelog.java`「distinct commits in strictly increasing event-time order across batches」)は、これまでで最も「時刻順」に近い。調査班は、(a)「市場データ」を言う逐語が無い (b) 適用先はターゲットの表の維持で戦略・執行の再実行ではない、で `未判別` とし、問い 1 にした。
3. scratchpad の外への書き込み・生ログに無い手は無かった(1 のとおり)。

## 3. 中身の監査(132 回目、owner-auditor)の逐語

> 監査 132 回目: 道具サーベイ 区分 8 の 34 回目(2026-09-26)
>
> 対象: `docs/DATA/SCAN_2026-09-23_tools_cat8.md` の `## 区分8 — 34 回目の実行`(45966〜46497 行目)/ 生ログ `docs/DATA/probes/20260923_tools_8_run34.log` / リードの検収下書き `docs/AUDITOR/VERDICTS/2026-09-26_tools_scan_cat8_run34.md`。
>
> 1. [止める] `docs/DATA/SCAN_2026-09-23_tools_cat8.md:46318`(E2 行)・`:46320`(E3b 行) — この回自身の「要素と段」表が、`Apache Spark` の E2・E3b の段を **段4** と明記している(本文にも「対象は任意の外部データソース(段4)」「対象は任意の外部テーブル・DataFrame(段4)」と明示)。しかし現在の台帳 `docs/DATA/tools_catalog_cat8.tsv` は `段_E2=3`・`段_E3b=3` であり、これは 33 回目の検収(監査 130 回目)の処置で「段4の『対象のすべてを外から持ち込める』を言う逐語が根拠の欄に無い」として **段3 に下げた** 値(`docs/DATA/SCAN_2026-09-23_tools_cat8.md:45961` の「リードの追記」参照)。この回の起動文(`docs/DATA/delegations/20260923_tools_survey_cat8_run34_prompt.md:84`)は「この回に触らない行は…値と段は台帳と同じにする」と定めているが、8-035 自身の未変更 7 要素は他の 40 候補のような `台帳の値のまま(<回>回目の節)` の省略形にせず、33 回目の**訂正前(as delivered)の全文をそのまま複写**しており、結果として訂正済みの値と矛盾する記述がこの回の「確定した」節にそのまま載っている。`check-elements`・`check`・`check_scan_report.py`・`git diff` の 4 検査はいずれもこの不一致を検出していない(値の突合せをしていない)。(P10 / 出典 `docs/DATA/delegations/20260923_tools_survey_cat8_run34_prompt.md:84`)
>
> 2. [止める] `docs/DATA/SCAN_2026-09-23_tools_cat8.md:45986`(知見#2)— 「N全体24,454ファイルに…を当てると**20ファイル**が当たった。**個別に開いて確認した結果**、大半は述語と無関係」と書くが、実際に生ログ(`docs/DATA/probes/20260923_tools_8_run34.log:152-170`)を数えると当たりは **19 ファイル**(20 ではない)。さらに、個別確認のループ(`run34.log:347-350`、11 ファイル)と別枝の 3 ファイル(`DirectKafkaInputDStream.scala`・`Scd2BatchProcessor.scala`・`declarative-pipelines-programming-guide.md`)を足しても **14 ファイルしか開かれておらず**、`KeyGroupedPartitioningSuite.scala`・`Scd2BatchProcessorSuite.scala`・`AutoCdcOutOfOrderConvergenceSuite.scala`・`DStreamCheckpointData.scala`(テスト以外の本体ソース)・`WriteAheadLogSuite.scala` の **5 ファイルは一覧に出た行(152・161・163・164・165・169行目)以外どこにも再登場せず、開かれていない**。私が実測(`grep` を当該 scratchpad で再実行)した限り、これら 5 ファイルの中身は同種の無関係な内部実装(`Time.ordering`・テストの説明文)だったが、それは監査でこちらが確かめたことであり、報告自身は開いていない。起動文(`run34_prompt.md:15`)は「29 回目に探す手を `head -25` で打ち切ったまま『探し尽くした』と書いた…この回は同じことをしない」と明記しており、この回の知見#10「印を探し尽くしたが…見つからなかった」という結論の根拠(=全部読んだこと)が実際には成立していない。(P10 / research-protocol §0.2 の「なぜ」の前段にあたる網羅性の欠落)
>
> 3. [直す] `docs/DATA/SCAN_2026-09-23_tools_cat8.md:46488-46491`(`cat8_ledger.py check "" run34.log` の貼り付け出力)— 「手の数 16 / 最後の手 2026-09-26T20:38:28Z」とあるが、生ログの最後の見出しは `run34.log:483`(`大きさ確認`、2026-09-26T20:49:13Z)であり、見出し行の実数は 17(`grep -c '^--- '` で確認)。同じコマンドを今このリポジトリの状態で打ち直すと `手の数 17 / 最後の手 2026-09-26T20:49:13Z` になる(合計 0 件は変わらない)。つまり、報告に貼られた検査出力は、生ログに大きさ確認の手(§7 の要求)が追記される**前**に取得したものであり、納品された生ログの最終状態と一致しない。結論(0件)は動かないが、「実行したコマンドと出力を同じ返答に出す」という自己申告と生ログが食い違っている。(CLAUDE.md §0.2 O-3 / P10)
>
> 4. [直す] `docs/DATA/SCAN_2026-09-23_tools_cat8.md:45993-45994`(知見#9・#10、E4 の案 B の記録)— 設計票の要求(`docs/DATA/delegations/20260923_tools_survey_cat8_run34_prompt.md:27`「この範囲の限界(題に出ない機能の記述は読み落としうる)を『読んだ範囲』の行に1文で書く」)に定める「限界」の一文が無い。同じ報告の 33 回目の節(`docs/DATA/SCAN_2026-09-23_tools_cat8.md:45383`、E3a の案 B 記録)は同じ形式で「限界: 題と目次で頁を選ぶ方式のため、題に出ない機能記述(個別APIの引数の中の記述等)は読み落としうる」と明記しており、同じ道具・同じ回のすぐ隣の節で書式が揃っていない。(出典: `CAT8_DESIGN.md` §1 相当の起動文の逐語)
>
> 5. [直す/聞く] `docs/DATA/delegations/20260923_tools_survey_cat8_run34_prompt.md:102`(§7 の 5)は「返答には次を…書く」として、この回の `なし` の一覧 N件/M件・500行超で未判別にした要素・§4.0で未確認のまま残した項目・4つの検査の合計行・判断に迷った点・**描画でしか読めない一次資料しか無いために未判別のまま残った要素の一覧**・**生ログと報告の大きさ(最後のwc -c)** を列挙するよう求めるが、`docs/DATA/SCAN_2026-09-23_tools_cat8.md:45966-46497` のどこにも「大きさ」「wc -c」「描画」という語も、これらの項目に対応する文言も見当たらない(生ログ側では `run34.log:483-490` に実測はある)。33 回目の節にも同様の欠落があり(過去から続く未指摘のギャップ)、リードの§2(検収下書き)もこの欠落を拾っていない。ファイルに書く要件なのか、返答本文だけの要件なのかをオーナー/リードで確認してほしい。
>
> ---
> 参考(問題なし、確認のみ): 依頼の3「案Bの条件(2)『§4.0 の過半が一次資料か実測』を 8-035 の §4.0 の全項目(33回目の節、`docs/DATA/SCAN_2026-09-23_tools_cat8.md:45778-45823`)で数え直す」を実施。43 項目中 41 項目が `実測`/`一次資料`、`未確認` は 2 項目(コミット数総数・4軸4_向上)のみで、過半の条件は明確に満たしている。E4 の当て方(「時刻順に」の逐語必須、Auto CDC を「市場データ」の逐語欠如で未判別に留めた判断)は 22回目(dbt)・28回目(Kafka)以来の当て方の系譜と整合しており、安全側・甘い側いずれかへの偏りは見当たらなかった。8-035 を「残り」に数えない判断(E3a・E4・E6 全部に案 B の記録がある)も設計票 §2 の当て方と矛盾しない。

## 4. 処置(リード、監査 132 回目)

1. **止める → 直した**。この回の節の 8-035 の E2・E3b の段 4 は、33 回目の受け取ったままの値の写しで、台帳の値(段 3、33 回目の検収 §4 の処置 2)と食い違う。**台帳は段 3 のまま**にする。`import --round 34` は節の値を台帳に写すので、写したあとに E2・E3b の段を 3 に戻し、戻したことを台帳のコミットに書く(リードは `import` の「変わった所」の出力を読み、範囲の外の要素の変化をそのまま入れない)。報告の節の末尾の「リードの追記」に訂正を書く。次の起動文から、範囲の外の要素は **同じ候補の要素も** `台帳の値のまま(<何>回目の節)` の形だけにし、値と段を台帳から写す、と書く。検査の道具が範囲の外の値の突き合わせをしていないことは記録し、区分 8 の資源化の作業で `check-elements` に台帳との突き合わせを足すかを決める。
2. **止める → 直した**。当たりは 19 ファイル(20 ではない)で、開いたのは 14。開いていない 5 つを、リードが読んだ(コマンドと出力は下):
   ```
   $ cd .../venvs/8-035/src/spark && for f in <5 つ>; do grep -n -I -i -E 'chronolog|time.order|time-order|in order of (event )?time|order of arrival|arrival order|時系列順|時刻順' "$f"; done
   == sql/core/src/test/scala/org/apache/spark/sql/connector/KeyGroupedPartitioningSuite.scala
   5828:              "config disabled: simple coalescing loses arrive_time ordering, " +
   5845:    //   arrive_time ordering within a year is lost -> SortExec is added.
   5903:              "config disabled: simple coalescing loses arrive_time ordering within a year, " +
   == sql/pipelines/src/test/scala/org/apache/spark/sql/pipelines/autocdc/Scd2BatchProcessorSuite.scala
   176:  // =============== orderChronologicallyPerKeyWindow tests ===============
   178:  test("orderChronologicallyPerKeyWindow sorts both decomposition tails and non-tails by " +
   193:      "rn", F.row_number().over(processor.orderChronologicallyPerKeyWindow)
   206:  test("orderChronologicallyPerKeyWindow tiebreakers: tails before non-tails, then " +
   226:      "rn", F.row_number().over(processor.orderChronologicallyPerKeyWindow)
   242:  test("orderChronologicallyPerKeyWindow orders rows independently per key") {
   259:      "rn", F.row_number().over(processor.orderChronologicallyPerKeyWindow)
   1654:  test("decomposeOutOfOrderRows uses chronological window order, not input order") {
   1662:    // non-chronological order. The window orders rows by effective recordStartAt, so the
   1913:    // Two open upserts tied on effective recordStartAt = 10. The chronologically-leading
   2034:    // pair ties: the chronologically-leading two copies are dropped, leaving exactly one
   == sql/pipelines/src/test/scala/org/apache/spark/sql/pipelines/graph/AutoCdcOutOfOrderConvergenceSuite.scala
   70:        // arrival order (e.g. deletedByBatchId stamps and cross-batch GC depend on how events are
   == streaming/src/main/scala/org/apache/spark/streaming/dstream/DStreamCheckpointData.scala
   65:      timeToOldestCheckpointFileTime(time) = currentCheckpointFiles.keys.min(Time.ordering)
   == streaming/src/test/scala/org/apache/spark/streaming/util/WriteAheadLogSuite.scala
   542:      // in order of timestamp, and we need the last element.
   ```
   読み: 4 つは候補自身の試験(L-516「数えません」)で、うち `Scd2BatchProcessorSuite.scala`・`AutoCdcOutOfOrderConvergenceSuite.scala` は Auto CDC(§2 の 2 で読んだ機能)の試験。`DStreamCheckpointData.scala` は内部の保存点のファイルを時刻で選ぶ処理。どれも E4 の述語に当たる新しい機能ではない。**E4 は `未判別` のまま**で、案 B の記録に「当たり 19 ファイルのうち調査班が 14、リードが残り 5 を読んだ」と書く(リードの追記)。「探し尽くした」の自己申告は、報告の数(20・全部開いた)が生ログと食い違っていたので、そのままでは受け取らない。次の起動文の「同じことをしない」一覧に、この型(当たりの一覧のうち開いていないものがあるのに探し尽くしたと書く)を入れ、当たりの一覧の全部について開いた手の行を報告に並べさせる。
3. **直す**。貼られた `check` の出力は大きさ確認の手の前のもの。リードの打ち直し(`check "" run34.log` → 0 件、見出し 17 本)をリードの追記に書く。
4. **直す**。E4 の案 B の記録の限界の 1 文を、リードの追記に書く:「限界: 頁とディレクトリを道と題の語で選ぶ方式のため、題・道に出ない機能の記述は読み落としうる(この回は語の選び方で 0 件、全文の語の検索 19 ファイルで補った)」。
5. **答える**。起動文 §7 の 5 は「返答には次をこの順で書く」で、返答の中身の決まり(報告のファイルに書く決まりではない)。この回の調査班の返答には、描画の一覧(「なし」)と大きさ(`wc -c`)が書かれていた。報告のファイルに無いのは決まりどおり。

### 8-035 の扱い(台帳に入れる値)

- E1a 印・段 4 / E1b 印・段 2 / E2 印・段 3 / E3a 未判別 / E3b 印・段 3 / E4 未判別(案 B の記録あり)/ E5 印・段 2 / E6 未判別
- 状態 `浅い`、**「残り」に数えない**(E3a・E4・E6 の全部に案 B の記録があり、§4.0 は 43 項目のうち実測・一次資料が 41。監査 132 回目の数え直し)。**残り 4**(OpenClaw・MetaTrader・NumPy・SciPy)。35 回目 = NumPy。

### リードの読みの案(監査に掛ける)

- E4 `未判別`(案 B の記録あり)を受け取る。Auto CDC は、述語の「記録した市場データを」「戦略・執行・計算を再実行する」のうち「計算」(`netChanges`)はありうるが、「市場データ」を言う逐語が無い。E2 と同じく、汎用の道具の当て方の問い(区分の完了の報告でオーナーに見せる)に入れる。**安全側に振るために未判別にするのではなく、述語の対象の語が無いので決めない**。
- 8-035 は、未判別の要素(E3a・E4・E6)の全部に案 B の記録があるので、**「残り」に数えない**(§4.0 の過半の条件は監査で数え直してほしい)。**残り 4**(OpenClaw・MetaTrader・NumPy・SciPy)。35 回目 = NumPy。
