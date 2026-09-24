# 検収: 道具サーベイ 区分 8 の 10 回目(2026-09-24、リード)

対象: `docs/DATA/SCAN_2026-09-23_tools_cat8.md` の `## 区分8 — 10 回目の実行(2026-09-24)` / 生ログ `docs/DATA/probes/20260923_tools_8_run10.log`(6,846 行・624 手)。届いたままのコミット 5ff0bb8。
起動文 `20260923_tools_survey_cat8_run10_prompt.md` の指紋 `292183d28506`、追補の指紋 `2c178ba75341`。

## 0. 費用と時間

調査班 **636,056 トークン・2,641,621 ms(44.0 分)・道具 297 回**。生ログの最初の手 10:33:20Z / 最後の手 11:07:18Z。§2 の 6 項目すべてに手が付いた。描画の道具は使っていない。

## 1. 受け入れ検査(リードが打ち直した)

`check_scan_report.py`(報告 + 生ログ 10 本)0 件 / `check-elements --round 10` 0 件(候補の一覧 16 行・要素と段の表 128 行・知見の表 19 行・辿る一覧から出た名前 25 行)/ `check "" <run10.log>` 0 件。

## 2. 8-016 の件数の数え合わせ(監査 58 回目の答え 2: 生ログを通さずに直接打った)

`python3 scripts/cat8_fetch_tally.py docs/DATA/probes/20260923_tools_8_run10.log --prefix th2-net/` の和の行と、1 MB を超えて取らなかったファイルの全部:

```
== リポジトリ 178 件(終了コード 0 = 178 / 4 = 0 / 5・6 は下の行 / そのほか = 取れなかった = 0)
== 終了コード 5(取った量の和が上限で取らなかった) = 0 / 6(置き場か和のファイルの誤りで取らなかった) = 0
== 終了コード 0 の N の和 = 34610 / skipped の和 = 27 / lfs_pointer の和 = 0 / downloaded_bytes の和 = 67234078
== 誤り 0 件
skipped	th2-net/jsonToHtmlParser	package-lock.json
skipped	th2-net/th2-codec-fix-orchestra	src/test/resources/dict/mit_2016.xml
skipped	th2-net/th2-common-ui-components	package-lock.json
skipped	th2-net/th2-docs	content/deploy/infrastructure/infra-components/overview/infra-comp-1.png
skipped	th2-net/th2-docs	content/deploy/infrastructure/infra-components/overview/infra-comp-2.png
skipped	th2-net/th2-docs	package-lock.json
skipped	th2-net/th2-docs	static/fonts/materialdesignicons-webfont.eot
skipped	th2-net/th2-docs	static/fonts/materialdesignicons-webfont.ttf
skipped	th2-net/th2-documentation	images/demo-ver154-main/recon_flow.gif
skipped	th2-net/th2-documentation	images/demo-ver154-main/script_flow.gif
skipped	th2-net/th2-documentation	images/th2architecture/demo1_gui1.gif
skipped	th2-net/th2-documentation	images/th2architecture/demo1_gui2.gif
skipped	th2-net/th2-documentation	images/th2architecture/demo1_gui3.gif
skipped	th2-net/viewer	package-lock.json
skipped	th2-net/viewer	webpack-starter/node_modules/@babel/parser/lib/index.js.map
skipped	th2-net/viewer	webpack-starter/node_modules/@material-ui/core/umd/material-ui.development.js
skipped	th2-net/viewer	webpack-starter/node_modules/@material-ui/styles/node_modules/csstype/index.d.ts
skipped	th2-net/viewer	webpack-starter/node_modules/@material-ui/system/node_modules/csstype/index.d.ts
skipped	th2-net/viewer	webpack-starter/node_modules/@mui/material/umd/material-ui.development.js
skipped	th2-net/viewer	webpack-starter/node_modules/node-sass/vendor/darwin-x64-93/binding.node
skipped	th2-net/viewer	webpack-starter/node_modules/node-sass/vendor/linux-x64-83/binding.node
skipped	th2-net/viewer	webpack-starter/node_modules/typescript/lib/tsc.js
skipped	th2-net/viewer	webpack-starter/node_modules/typescript/lib/tsserver.js
skipped	th2-net/viewer	webpack-starter/node_modules/typescript/lib/tsserverlibrary.js
skipped	th2-net/viewer	webpack-starter/node_modules/typescript/lib/typescript.js
skipped	th2-net/viewer	webpack-starter/node_modules/typescript/lib/typescriptServices.js
skipped	th2-net/viewer	webpack-starter/node_modules/typescript/lib/typingsInstaller.js
== 集計の終わり(誤り 0 件)
```

報告の数との突き合わせ: N = 34,610(一致)。取らなかった 27 件 = 除外 16 件(ロックファイル 4・画像 7(png 2・gif 5)・フォント 2・ソースマップ 1・バイナリ `binding.node` 2)+ 除外の種類でない 11 件(`mit_2016.xml` 1・`material-ui.development.js` 2・`csstype/index.d.ts` 2・`typescript/lib/*.js` 6)。報告の「除外 16・個別に取った 11」と一致。M = 34,610 − 16 = 34,594(一致)。178 件すべて終了コード 0、取った量の和 67,234,078 バイト(300 MB の内)。
**11 件は起動文の「それ以外は読んでいないに数える」を越えて、`raw.githubusercontent.com` から 1 件ずつ取り直して検索していた**(生ログ 4776〜4810 行、11 件とも HTTP 200)。取り直したものを読んだと数えるのは起動文に反しない(読んでいないものを読んだ)。ただし**その検索の手は `| head -60` で出力を切っている**(生ログ 4811 行)。この回の `$` の行のうち `head -<数>` を含むものは 361 手。`なし` の根拠になった検索が切られた出力で判断されていないかは、中身の監査(63 回目)で見る。

## 3. `[それ以外の問い]` の行(1 件ずつ読んだ)

| 問い | 読んだ結果 |
|---|---|
| 1(8-005 E4 の段 3 か 4 か) | **段の問いである**(値・段を決めずにおく理由)。台帳の 8-005 段_E4 を `未判別` にした(値の `印` は残す) |
| 2(8-014 E3a の段 3 か 4 か) | **段の問いである**。台帳の 8-014 段_E3a を `未判別` にした(値の `印` は残す。値は L-509 の読みで決まる) |
| 3(8-014 を `深掘り` にした妥当性) | 状態の問いで、値・段の問いではない。値に `未判別` が無く §4.0 の表があるので `深掘り` のままにする |

## 4. 辿る一覧から出た名前(監査 48 回目の答え 6)

節の名前の行 `n_trace` = 25。**台帳に `未着手` で足した 22**: 8-017 Great Expectations / 8-018 Vibe-Trading / 8-019 AutoHedge / 8-020 OpenBB Terminal / 8-021 Qlib / 8-022 FinGPT / 8-023 Backtrader / 8-024 Lean / 8-025 FinanceToolkit / 8-026 OpenClaw / 8-027 Quantreo library / 8-028 AlgoBuild / 8-029 MetaTrader の Strategy Tester / 8-030 dbt / 8-031 Debezium / 8-032 Apache Kafka / 8-033 Prefect / 8-034 Pandas / 8-035 Apache Spark / 8-036 AI Trading Lab / 8-037 AlgoNetwork / 8-038 NinjaTrader。**足さない 3**: Fincept Terminal(8-014 と同じ)/ Freqtrade(8-006 と同じ)/ TradingView(8-015 と同じ製品)。22 + 3 = 25(一致)。
同じ記事から出た別の名前は、台帳の道具が「出典の URL が同じ」で重複の疑いとして止めた(9 件)。名前が別の道具であることは記事の列挙で確かめたので、出典の文に「この記事の中の <名前>」を足して別の出典として足した。
一覧 7(1 回目の検索計画 7)は「新しい名前なし」で、`pandas`・`numpy` を「固有の道具名でない」と書かなかったが、一覧 1 では `Pandas` を書いている(扱いが揃っていない)。台帳には一覧 1 の `Pandas` として 1 行足したので、名前の落ちは無い。

## 5. 台帳

`import --round 10`: 変わった所 9。§3 の 2 セルを `set` で直し、§4 の 22 行を足した。`check` 0 件。`recount`: 深掘り 14 / 危険で導入停止 1(8-004)/ 登録が要る 1(8-005)/ 未着手 22。**残り 22 行**(すべて辿る一覧から足した 8-017〜8-038)。もとの 16 行の残りは 0。

## 6. 判定

**一部受け取り**(§3 の 2 セルを直した)。8-016 の `なし` 3 つ(34,594 件)・8-011 E6 段 2・8-014 E1b 段 4・E3a の印・8-005 E4 の印が新しい決定なので、中身の回として監査役(63 回目)に通す。

## 監査 63 回目(中身の回。対象 = 02639af の 10 回目の節と生ログ)

監査役の出力(逐語。[止める] 1 件・[直す] 2 件・[聞く] 2 件):

> 監査 63 回目(中身の回)。対象: `docs/DATA/SCAN_2026-09-23_tools_cat8.md` の `## 区分8 — 10 回目の実行(2026-09-24)` 節(3389〜3742行)、生ログ `docs/DATA/probes/20260923_tools_8_run10.log`(6,846行)、検収 `docs/AUDITOR/VERDICTS/2026-09-24_tools_scan_cat8_run10.md`、起動文 `docs/DATA/delegations/20260923_tools_survey_cat8_run10_prompt.md`、台帳 `docs/DATA/tools_catalog_cat8.tsv`。scratchpad `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/audit63/` で `th2-net/viewer` を `git clone --depth 1` して同じ正規表現で数え直し、Exegy・Fincept Terminal・arXiv:2512.12924 の一次資料を再取得して照合した。
>
> 1. [止める] `docs/DATA/probes/20260923_tools_8_run10.log:4533`(`th2net_viewer_lookahead`)・`4550`(`th2net_viewer_reproduc`)・`4811`(`th2net_unread_lookahead`)・`4840`付近(`th2net_unread_reproduc`) — 8-016 の E3a・E3b・E5 の `なし`(`docs/DATA/SCAN_2026-09-23_tools_cat8.md:3590-3593`)の根拠になった grep は、いずれも末尾に `| head -60` が付いている。しかも生ログ自身が「[出力は 13277 文字。先頭 3000 文字だけを残した]」等と書いているとおり、`cat8_step.py` の既定 `--keep` がその 60 行をさらに切っている。監査で `th2-net/viewer` を素の `git clone --depth 1` で取り直し、報告と同じ正規表現(`look-?ahead|look ahead|ルックアヘッド|先読み...|survivorship` / `再現性|再現する|reproduc`)で数え直すと、一致は lookahead 系 **713 件**・reproduc 系 **282 件**あった(いずれも `webpack-starter/node_modules` 配下のみで、目視した範囲ではトレードのルックアヘッドバイアス検出機能ではない点は報告の結論と一致した)。一方、生ログに実際に残っている(=監査で読める)一致行は viewer 本体の検索で 14 行(lookahead)・8 行(reproduc)、11 件の未読ファイル検索で数十行程度にとどまる。報告は「一致は...のみで、いずれも...無関係」(`docs/DATA/SCAN_2026-09-23_tools_cat8.md:3590`)と全件を読んだ体で書いているが、実際には 713 件・282 件のうち 1 割未満しか記録に残っておらず、残りを 1 件ずつ読んで判断した形跡が無い。設計票 §2「`一覧N件/読んだM件`」の M は「検索の対象に入れたファイル数」であって「当たった行を読んだ数」ではないため、この字面は満たしているが、`なし` の実質的な根拠(その要素に当たる記述が本当に 1 つも無いこと)は `head -60` で切られた一部しか確認されていない。検収(`docs/AUDITOR/VERDICTS/2026-09-24_tools_scan_cat8_run10.md:54`)自身が「`なし`の根拠になった検索が切られた出力で判断されていないかは、中身の監査(63回目)で見る」と問いを先送りしていた箇所で、実際に切られていたことを確認した。今回はたまたま結論が変わらなかったが、手続きとしては P5(行単位で全文を読んで判定する)に反する。
>
> 2. [直す] `docs/DATA/SCAN_2026-09-23_tools_cat8.md:3590`(E3a)・`3591`(E3b、生ログの`th2net_*_lookahead`系コマンド全般) / `3593`(E5、`th2net_*_reproduc`系コマンド全般) — 8-016 の E3a・E3b・E5 の検索語が設計票 §3 の述語をどこまで覆っているか疑問が残る。E3a/E3b の述語は「purged 交差検証・embargo・時点の揃った結合」など lookahead/survivorship という語を使わない実装も含むが、検索語は `look-?ahead|look ahead|ルックアヘッド|先読み(みらい|未来)?|未来.{0,4}情報|survivorship` のみで `embargo`・`purge`・`point-in-time`・`time-travel`・`leakage` 等の同義語を検索していない。E5 の述語は「乱数の種・環境や依存の固定・実験の再実行と結果の差分・データの版の固定」だが検索語は `再現性|再現する|reproduc` のみで `seed`・`deterministic`・`pin`・`lock`・`snapshot`・`golden` 等を検索していない(実際、`th2-check2-recon` の setup.py・requirements.txt には固定バージョンの依存指定があるが、これは E5 の検索語に掛からない語彙である)。178 リポジトリ・34,594 ファイルという大きな母集合に対して「なし」を言うには、述語の語彙をもっと広く当てるべきではないか。
>
> 3. [直す] `docs/AUDITOR/VERDICTS/2026-09-24_tools_scan_cat8_run10.md`(§4)・`docs/DATA/tools_catalog_cat8.tsv` — 辿る一覧で書かなかった名前の理由に、設計票 §3 が明示的に禁じた基準(「専用かどうか・有名かどうかは理由にしない = 委任文§10の当否判定」)を使っている。`docs/DATA/SCAN_2026-09-23_tools_cat8.md:3697` は「pandas/numpy/scipyは固有の検証ツールではなく汎用の数値計算ライブラリのため...書かない理由: 専用のツール名として特定できる固有名詞が無い」と書き、まさに禁じられた「専用かどうか」を理由にしている。報告自身も「一覧7...と一覧1で扱いが揃っていない」と気づいているが、修正はしていない。検収は「台帳には一覧1の`Pandas`として1行足したので、名前の落ちは無い」(`VERDICTS/...run10.md` §4)と書いているが、これは `Pandas` だけの話で、`numpy`・`scipy` はどの一覧からも台帳に足されておらず(`docs/DATA/tools_catalog_cat8.tsv` を検索しても該当行なし)、依然として落ちている。検収の「名前の落ちは無い」という結論は誤り。
>
> 4. [聞く] `docs/DATA/SCAN_2026-09-23_tools_cat8.md:3661-3696`(辿る一覧、8-030〜8-038 の 9 行)・台帳 `8-030`〜`8-038` の「発見の出典」列 — 同じ記事 URL から見つかった別の道具名(dbt・Debezium・Apache Kafka・Prefect・Pandas・Apache Spark、AI Trading Lab、AlgoNetwork、NinjaTrader)は、`sync` の重複検査(名前かURLのどちらか一方でも当たれば止まる)に URL 一致で引っかかったため、「発見の出典」欄に「この記事の中の<名前>」という文言を足して URL の正規形を変え、通した(検収 §4 に記録あり)。設計票が明記する回避手順(名前衝突時の `sync --new <名前>` + 理由を検収に記録)とは異なり、URL 側の衝突をテキストの書き換えで回避する手順は設計票に明記が無い。名前は確かに検証済み(記事の列挙で別物と確認)だが、この扱いが将来「本当に同じ道具を同じ記事から二重登録する」ケースの検出まで一緒にすり抜けさせないか、リードに確認した方がよいのではないか。
>
> 5. [聞く] `docs/DATA/SCAN_2026-09-23_tools_cat8.md:3572`(8-014 E1b 段4) — `_extract_walk_forward_metrics` の入力 `returns: pd.DataFrame`・`models: Dict[str, Any]` は型注釈としては汎用だが、実装(`cross_val_predict(model, returns, cv=cv)`)は skfolio の `cross_val_predict` を呼んでおり、`model` は skfolio 互換の推定器(戻り値が `sharpe_ratio`・`annualized_mean` 等のプロパティを持つ `Portfolio` を返すもの)である必要がある(一次資料で確認済み)。設計票の段4の条件「一般のPythonの関数・CSV等広く使われる形式」に照らすと、特定ライブラリ(skfolio)の API に縛られる `model` 引数を「道具の外から持ち込める」対象と呼んでよいかは境界が甘くないか。
>
> 以上、主一次資料での照合結果: 8-011 arXiv:2512.12924 の `hdt/stats.py`(E6段2の根拠、pass/fail相当の分岐が無くfloat/CSCVResultを返すのみ)、8-014 Fincept Terminal の `skfolio_validation.py`(E1bの根拠、`self.performance_metrics`が未使用で`_extract_walk_forward_metrics`が実際に使われる)・`subagents.py`(E3aの根拠、`BACKTESTER_AGENT`の`Identify lookahead bias and survivorship bias`)、8-005 Exegy の製品頁(E4の根拠、Capture Replayの逐語)は、いずれも報告の引用・要旨が一次資料と一致することを確認した(問題なし)。辿る一覧の22件の足し方・足さなかった3件(Fincept・Freqtrade・TradingView、いずれも既存の台帳行と同一)の理由は妥当。8-005・8-014の段を検収が`未判別`に差し戻した判断(委任文が「値・段の問いではない」と分類した境界の読みの問いを、検収が「段の問い」と読み替えたもの)自体は設計票の値/段の区別に整合しており、問題は見当たらなかった。

**リードの処置**:
1: 認める(リードは検収で「切られた出力で判断されていないかは監査で見る」と先送りし、自分で確かめなかった)。台帳で 8-016 の E3a・E3b・E5 を値・段とも `未判別` に戻し、状態を `判別に一次資料が要る` に戻した。**機械で止めるようにした**: `check-elements` は 11 回目以降、`なし` の 7 列目に引いた手の `$` の行に `| head`・`| tail`・`grep -m` があれば止め、引いた手の出力が生ログで `[出力は N 文字。先頭 M 文字だけを残した]` と切られていても止める。10 回目の報告を 11 回目と見なして打つと、8-016 の `なし` の行で両方が止まる側に出た(2〜10 回目の結果は変わらない: 7・9・10 回目 0 件、8 回目 5 件のまま)。
2: 認める。`check-elements` に 11 回目以降の語の組を足した(設計票 §3 の述語の文から取った。例: E3b = ルックアヘッド / embargo / purge / 時点の揃った結合、E5 = 再現 / 乱数の種 / 決定的 / 版の固定)。組ごとに、どれか 1 つの語が `なし` の手の `$` の行に無ければ止まる。10 回目の報告に当てると、E3a は「時点」、E3b は embargo・purge・時点、E5 は種・決定的・版の固定の組が無いと出た。
3: 認める(検収の「名前の落ちは無い」は誤り)。一覧 7 の NumPy・SciPy を台帳に `未着手` で足した(8-039・8-040)。辿る一覧から足した数は 24、足さない数は 3、節の名前の行 25 + 一覧 7 の書かなかった名前 2 = 27 = 24 + 3。
4: 答える。台帳の道具の重複の検査は「名前か URL が同じなら止める」で、同じ記事から出た**別の名前**でも URL で止まる。9 件は記事の列挙で別の名前であることを確かめてから、出典の文に「この記事の中の <名前>」を足して通した。名前の検査は残っているので、同じ名前を二重に足すことは止まる。同じ道具が別の名前で出たときは止まらない(名前の一致しか見ていないため)が、それは URL の検査でも止まらない(別の記事から出れば URL は違う)。区分の締めの `SURVEY.md` の教訓の案に入れる。
5: 認める(段 4 の条件「広く使われる形式」に、特定のライブラリ `skfolio` の API に縛られた引数が当たるかは、設計票に書かれていない = 読みの問い)。台帳で 8-014 の段_E1b を `未判別` にした。オーナーに聞く。

台帳: `check` 0 件。**残り 25 行**(8-016 と、辿る一覧から足した 8-017〜8-040)。
