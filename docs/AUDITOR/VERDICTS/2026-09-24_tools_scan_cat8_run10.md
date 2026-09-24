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
