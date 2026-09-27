# 検収: 道具サーベイ 区分 8 の 39 回目(2026-09-27、リード)

対象: `docs/DATA/SCAN_2026-09-23_tools_cat8.md` の `## 区分8 — 39 回目の実行(2026-09-27)`(49060 行目から)/ 生ログ `docs/DATA/probes/20260923_tools_8_run39.log`(155,303 バイト、手 21)。受け取ったままの形はコミット b4f439b。

## 0. 費用と時間

調査班 474,825 トークン・1,543,470 ms(25.7 分)・道具 131 回。

## 1. 受け入れ検査(リードが打ち直した)

- 報告の末尾に `### 受け入れ検査の出力(道具が貼った)` がある。リードの打ち直し: `check_scan_report.py`(39 本)「---- 合計 71 件」/ `check-elements --round 39` 0 件。
- 見出し 21 本の全部に `[sandbox …]`。候補のコードを動かす手は 0(調査班の申告)。
- `find /tmp -maxdepth 1 -newermt '2026-09-27T01:04:08Z'` → `/tmp/build2.py`・`/tmp/build3.py`・`/tmp/run38_candidates.txt`・`/tmp/run38_elements_table.txt`(調査班が報告の組み立てのために `cat8_step.py` を通さずに書いた。知見 14 で申告)。`find /root -xdev -newermt '2026-09-27T01:04:08Z' -not -path '/root/.claude/*' -type f` → 出力なし。4 つはリードが `scratchpad/cat8/run39_tmp/` へ移した。

## 2. リードが見つけたこと(監査の前)

1. **E2 の案 B の記録が揃った**。時系列を名指す語の検索(文書 2 件・ソース 17 件、スペクトル解析の入力の説明と平滑化のフィルタ)、金融の語の検索(該当なし)、文書 432 頁の道と題への語の選び方で 9 頁を読んだ、ソース 365 ディレクトリへの語の選び方で 0 件、見積もり `files_with_hits=1179 total_lines=16907`(500 行超)。新しい `印` は無い。**型で対象を限定するだけの候補(NumPy の `isnat` の形)も無い**(調査班の申告)ので、8-039 と違い、E2 は案 B の「探し尽くしても見つからない」の場面に当たる。
2. 8-040 の §4.0(38 回目の節)をリードが数えた: 一次資料 11・実測 29・未確認 3(43 項目)。案 B の条件(2)を満たす。
3. 公式のリポジトリの書き足し: `scipy/scipy.org`・`scipy/scipy-cookbook` を `git ls-remote` で確かめ、名前と URL を書いた(N に入れない。35 回目の NumPy の `numpy.org` と同じ扱い)。
4. scratchpad の外への書き込み(1 のとおり)。26・31・32・33・39 回目。報告の組み立ての小さいスクリプトを `/tmp` 直下に書く型。

## 3. 中身の監査(142 回目、owner-auditor)の逐語

> 監査 142 回目の指摘(4件、severityは各行に記載)。
>
> 1. [直す] `docs/DATA/SCAN_2026-09-23_tools_cat8.md:49082`(知見2)/ 生ログ `docs/DATA/probes/20260923_tools_8_run39.log:34-56` — 「scipy/本体では17件」という数が、生ログの実際のgrep出力と食い違う。当該コマンド(34-35行目)の出力は実際には計21行(`_spectral_py.py`18行・`_whittaker.py`1行・`scipy/stats/__init__.py`2行、`sed -n '36,56p' ... | wc -l`で確認)であり、17ではない。内訳の説明(「14件はdocstring」「残り3件のうち…」)も、(a)`_spectral_py.py`L124の書誌引用が数に入っておらず、(b)`stats/__init__.py`は実際には2行(L20・L22)ヒットしているのに1件としてしか記述されていない。E2の最終判定(未判別のまま)自体はどの行を見ても変わらないが、案Bの「当たりの行の数」の正確性という点で自己申告と生ログが合っていない(P5、CLAUDE.md §0.2 O-6)。リードの§2(下書き `docs/AUDITOR/VERDICTS/2026-09-27_tools_scan_cat8_run39.md`)はこの食い違いを拾っていない。
>
> 2. [直す] `docs/DATA/SCAN_2026-09-23_tools_cat8.md:49085-49086,49090`(知見5・6・10)/ 生ログ `docs/DATA/probes/20260923_tools_8_run39.log:172-618` — 文書432頁の中に、まさに38回目に却下した候補`nan_policy`自身の設計仕様書`doc/source/dev/api-dev/nan_policy.rst`(題「A Design Specification for `nan_policy`」、生ログ215行目に道と題が印字済み)が存在するが、E2語の組による機械選定(9頁)にはタイトルがE2語を含まないため選ばれず、本文も読まれていない。実際に中身を確認すると(私が直接読んだ)対象を時系列等に限定する逐語は無く結論(E2未判別)は変わらないが、この回固有の最も疑うべき頁を「探し尽くした」の範囲から外している。知見10の「限界」の一文はこの具体的な見落としを名指ししていない。
>
> 3. [聞く] `docs/DATA/SCAN_2026-09-23_tools_cat8.md:49094`(知見14)/ 起動文 `docs/DATA/delegations/20260923_tools_survey_cat8_run39_prompt.md:15` — scratchpad外(`/tmp`直下)への書き込みは26・31・32・33回目に続き今回で5回目の再発。起動文は毎回この失敗を列挙するだけで、`cat8_step.py`を経由しないBash呼び出し自体を防ぐ技術的な手当ては無い。自己申告自体は起動文の指示どおりだが、CLAUDE.md §0.2 A-17(「対策を記録するだけで終わらせない」)に照らし、5回目の再発でも技術的な手当てを検討しなくてよいかはリード単独では決められない。
>
> 4. [聞く](指摘ではなく確認・監査ブリーフ項目3への回答) — `docs/DATA/tools_catalog_cat8.tsv`で`dbt`(8-030)・`Debezium`(8-031)・`Apache Kafka`(8-032)・`Prefect`(8-033)・`Pandas`(8-034)・`Apache Spark`(8-035)にも複数の`未判別`要素が残っていることを確認したが、これらは過去の検収(23・25・27・30・32・34回目、`docs/AUDITOR/VERDICTS/2026-09-26_tools_scan_cat8_run36.md:50`に一覧)で個別に案Bの除外条件を満たすと既に確認済みであり、run39の「残り3」(8-026 OpenClaw・8-029 MetaTrader・8-039 NumPy)という数え方はこの経緯と矛盾しない。安全側・甘い側いずれへの偏りも見当たらなかった。
>
> 他の点(§1の測定手順の遵守、`--sandbox`が全21手に付いている、候補コードを動かす手が0件、E1a〜E6の据え置き行と台帳・38回目節との一致、公式リポジトリ書き足しの`git ls-remote`実測、受け入れ検査4種が0件、手の数21・バイト数155,303の自己申告一致、38回目起動文監査(141回目)の5指摘の反映確認)はすべて生ログ・台帳と一致しており、追加の指摘なし。
>
> 参照した主なファイル:
> - `/home/user/trade/docs/DATA/SCAN_2026-09-23_tools_cat8.md`(49060行目〜末尾、および38回目節48345〜49058行目)
> - `/home/user/trade/docs/DATA/probes/20260923_tools_8_run39.log`
> - `/home/user/trade/docs/DATA/delegations/20260923_tools_survey_cat8_run39_prompt.md`
> - `/home/user/trade/docs/AUDITOR/VERDICTS/2026-09-27_tools_scan_cat8_run39.md`(リードの検収下書き)
> - `/home/user/trade/docs/AUDITOR/VERDICTS/2026-09-27_tools_scan_cat8_run39_prompt.md`(起動文監査、監査141回目)
> - `/home/user/trade/docs/DATA/tools_catalog_cat8.tsv`
> - `/home/user/trade/docs/DATA/surveys/CAT8_DESIGN.md`
> - `/tmp/claude-0/-home-user-trade/2da9385f-4fe4-506a-be3d-78153c549662/scratchpad/cat8/venvs/8-040/src/scipy/doc/source/dev/api-dev/nan_policy.rst`(現物確認用)

## 4. 処置(リード、監査 142 回目)

1. **直す**。リードの打ち直し: `sed -n '36,56p' docs/DATA/probes/20260923_tools_8_run39.log | wc -l` → 21。報告の知見 2 の「scipy/本体では17件」は 21 行(`_spectral_py.py` 18・`_whittaker.py` 1・`scipy/stats/__init__.py` 2)。リードの §2 は見落とした。リードの追記に訂正を書く。E2 の結論は変わらない。
2. **直した**。`doc/source/dev/api-dev/nan_policy.rst`(181 行)をリードが語で読んだ: `grep -n -i -E 'time.?series|timestamp|datetime|market|trade|tick|order book|ohlc|candle|時系列' …/nan_policy.rst` → 0 件(出力なし)。対象を時系列などに限定する逐語は無い(監査役の読みと同じ)。案 B の「読んだ範囲」にこの頁を足し、限界の文に「題に E2 の語が無い、38 回目に受け取らなかった機能の設計の頁(`nan_policy.rst`)は語の選び方で選ばれず、リードが検収で読んだ」と書く(リードの追記)。
3. **答える**。`cat8_step.py` を通さない殻の手と `/tmp` 直下への書き込みを技術で止めるには、調査班の道具の呼び出しを止める仕組み(フック)が要る。フック・`settings.json` はオーナーの指示のときだけ変える(CLAUDE.md §0.2 A-16)ので、リードは作れない。リードが道具で手当てできたのは、見つけること(最後の手の `find`・`cat8_final_checks.py`・検収の `find`)と、置き場所の変数を道具で付けること(`--sandbox`)まで。**止める仕組みが要るかは、オーナーに見せる**: 区分の完了の報告に、scratchpad の外への書き込みが 26・31・32・33・39 回目にあったこと(どれもリードが見つけて移すか消した)、フックで止める案(`Bash` の手のうち `/tmp/` の直下へ書く形を止める)と、その案はリードが提案するだけでオーナーの指示が要ることを書く。
4. **答える**。確認として受け取る。

### 8-040 の扱い(台帳に入れる値)

- E2 `未判別`(案 B の記録あり。読んだ範囲に `nan_policy.rst` を足した)。ほかは台帳の値のまま。
- **「残り」に数えない**(E2・E4 の全部に案 B の記録があり、§4.0 は 43 項目のうち一次資料 11・実測 29・未確認 3)。**残り 3**(8-026 OpenClaw・8-029 MetaTrader・8-039 NumPy)。40 回目 = 8-029 MetaTrader の E1a、そのあと 8-026 OpenClaw。

### リードの読みの案(監査に掛ける)

- 台帳: 8-040 E2 `未判別`(案 B の記録あり)。ほかは台帳の値のまま。
- **8-040 は「残り」に数えない**(E2・E4 の全部に案 B の記録があり、§4.0 の過半が一次資料・実測)。**残り 3**(8-026 OpenClaw = 未判別 7 要素・8-029 MetaTrader = E1a・8-039 NumPy = オーナーの判断待ち)。40 回目 = 8-029 MetaTrader の E1a(小さい)、41 回目以降 = 8-026 OpenClaw。
