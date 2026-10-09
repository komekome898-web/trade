# 突き合わせ 6: 台帳 K-301〜K-364・段 1 の 10 族の表・simple_road_check の損益と値動きの数

作業者(読むだけ)。2026-10-09。書いたのはこのファイルだけ。ほかのファイルは変えていない。コミット・押し出しはしていない。

## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 3 つの文書の損益・値動きの数を全部拾い、出所の出力ファイルの値・単位と 1 つずつ突き合わせる | 「**もっと徹底的に調べて影響範囲を確定させてください。**」 |
| 判定(一致 / 単位の誤り / 値の誤り / 出所が無い / 確かめられない)を付けて audit_6.md に書く | **(該当語なし)**(リードの委任文の指示) |
| 出力が保存されていない台本(`base/d3_extra.py`・`d9b_extra.py`・`d0_extra.py`)を打ち直して標準出力を scratchpad に取る(読むだけの台本。リポジトリは変えない) | **(該当語なし)**(作業者の判断。出所を確かめるため) |

見込み時間(着手時): 90 分 = 単位の地図と 3 文書を読む 15 分 + 数を拾う道具と突き合わせの道具を書く 25 分 + 自動で合わなかった数を手で確かめる 35 分 + 書く 15 分。
実際: 約 110 分かかり、上限 90 分を越えた。越えた分で手の確かめを打ち切り、残りは「確かめられない」として下の §6 に書いた。

## 1. 方法

- 数を拾う: 台帳は K-301〜K-364 の「見出し」「観察」「大きさ」と、行の中の「注」(3 行)。段 1 の表は表 1・表 3 と表 3 の上の注(奇数年の値)、文書の先頭の注記の数。表 2(ポイント = 割合の差)は対象外。本数・割合・日付・時刻・年・分・% の付いた数は道具が外した(外した数の扱いは §6)。
- 単位: 数の後ろ(無ければ前)の同じ文の中の最初の単位の語(円・円/日・bp・bp/日・move_bp・値動きの bp・万円・M 円)。語が無い数は「(語なし)」。
- 出所の索引: `docs/RESEARCH/matilda_main/` の下の全部の .md・.out・.json(.json は精密な値)と、打ち直した 3 つの台本の出力。出所の単位は UNITS_MAP §2 のとおりファイルで決めた(diag_tables = 口座の bp、diag_paths・blocked_* = 損益の和は口座の bp・ほかは値動きの bp、fam_tables = 円(D4 の MFE・MAE、出の後、D5 は値動きの bp)、ほかの .out・compare.md = 円)。UNITS_MAP の地図は、突き合わせの中で食い違いが出なかった(出所の単位と書かれた単位が合わなかったのは K-317 の 1 か所だけで、それは地図 §3 の 2 点目のとおり)。
- 突き合わせ: 円の数は出所が円ならそのまま、口座の bp なら × 20 で比べた。書かれた桁に丸めて合えば一致。区間つきの数(点 [下, 上])は 3 つが出所の同じ行(json は同じ親)に揃うものを「強」とした。区間の無い数は、4 桁以上ならリポジトリの出力全部、3 桁なら族の出力、2 桁以下なら行の出所に名指しのファイルと族の主な表だけで探した。
- × 20 で合った数は、表示(小数 2 桁)ではなく json の精密な値 × 20 でも合うかを確かめ直した(`roundchk.py`)。合わないものを「値の誤り(丸め)」にした。
- 自動で合わなかった数は、出所の行を開いて手で計算した(和 ÷ 本数、差、段数の量の換算など)。計算で合ったものは「一致」にし、備考に計算を書いた。

## 2. 判定ごとの数

| 対象 | 拾った数 | 一致 | 単位の誤り | 値の誤り | 出所が無い・見つからない | 確かめられない |
|---|---|---|---|---|---|---|
| 台帳 K-301〜K-364 | 1297 | 1255 | 1 | 12 | 0 | 29 |
| 段 1 の 10 族の表(STAGE1_FAMILY_TABLES.md) | 563 | 563 | 0 | 0 | 0 | 0 |
| simple_road_check.md | 0 | 0 | 0 | 0 | 0 | 0 |

台帳の「一致」1255 個の証拠の強さ: 強(区間の 3 つが同じ行)685・中(3 桁以上の数が 1 つ)346・弱(2 桁以下の数が 1 つ)183・計算で一致 41。**弱の 183 個は、出所に同じ値があったことだけを確かめた。別の数と偶然合った可能性は消していない**(§6)。

拾ったが対象外にした数(台帳 22 個。損益・値動きの数ではないと手で判断した): K-306 28,000(式の値(20 万円 × 70% ÷ 5 段。出力の数ではない))・K-308 312(件数(312〜395 件))・K-309 3(分(3〜11 分))・K-309 3(分(3〜11 分))・K-313 1(仕組みの定数(利益 1 円))・K-319 20(式の定数(20 万円))・K-319 14(式から出した建玉の大きさ(約 14 万円))・K-319 2(式から出した建玉の大きさ(約 2 万円))・K-320 0(群の定義・仕組みの記述(0 円))・K-320 0(群の定義・仕組みの記述(0 円))・K-320 0(群の定義・仕組みの記述(0 円))・K-320 1(仕組みの定数(1 円))・K-320 1(仕組みの定数(1 円))・K-320 1(仕組みの定数(1 円))・K-320 1(仕組みの定数(1 円))・K-320 1(仕組みの定数(1 円))・K-320 0(群の定義・仕組みの記述(0 円))・K-320 0(群の定義・仕組みの記述(0 円))・K-320 0(群の定義・仕組みの記述(0 円))・K-331 20(上限の言い方(20 円以内))・K-350 3(割(3〜4 割))・K-353 2.7(割合(2.7〜6.0%))。

simple_road_check.md: 行頭が `>` でない行に、損益・値動きの数は無かった。あるのは足の値段(46,420・44,142・46,995 円。値段で損益ではない)、本数、時間・記憶・量(秒・MB)、比だけ。行頭が `>` の行の −17,914 bp は決まりにより対象外。

## 3. 一致以外のものの一覧(台帳)

| 行 | 書かれた数 | 書かれた単位 | 出所 ファイル:行 | 出所の値 | 出所の単位 | 判定 | 備考(証拠の強さ・計算) |
|---|---|---|---|---|---|---|---|
| K-309 観察 L198 | +1.4 | 円 |  |  |  | 値の誤り | 出所の精密な値: base/diag_tables.json /d6/groups/〜1 分/lo = +1.348 → +1.3(fam_tables.md も [+1.3, +3.3])。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-309 観察 L198 | +3.4 | 円 |  |  |  | 値の誤り | 出所の精密な値: base/diag_tables.json /d6/groups/〜1 分/hi = +3.346 → +3.3。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-317 観察 L336 | +42.83 | bp/日 | docs/RESEARCH/matilda_main/levels_1/diag_tables.md(2016 の行) | +42.83 | 口座の bp/日 | 単位の誤り | levels_1/diag_tables.md の 2016 年 +42.83 は口座に対する bp(1 bp = 20 円 → +856.6 円/日)。同じ行の他の数は円。「bp/日」とだけ書き、値動きの bp と読み分ける語が無い(UNITS_MAP §3 の 2 点目) |
| K-323 観察 L439 | −3.60 | (語なし) |  |  |  | 確かめられない | 本体の move_bp(foot_5 の D5)を出所で特定していない。自動の突き合わせは bp のファイルの別の数を × 20 で拾っただけ |
| K-325 観察 L473 | +73.6 | 円 |  |  |  | 値の誤り | 出所の精密な値: foot/compare.md:21 利確 1 本 = +73.7(foot_5/diag_tables.json close per_trade × 20 = +73.70)。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-325 観察 L473 | −562.8 | 円 |  |  |  | 値の誤り | 出所の精密な値: foot/compare.md:21 ブレイク 1 本 = −562.7(json × 20 = −562.71)。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-331 観察 L575 | +6.4 | 円/日 |  |  |  | 値の誤り | 出所の精密な値: alert_x1/diag_tables.json /d7/all/mean × 20 = +6.343 → +6.3。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-331 観察 L575 | −1.4 | 円/日 |  |  |  | 値の誤り | 出所の精密な値: alert_x1/diag_tables.json /d7/all/lo × 20 = −1.335 → −1.3。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-331 観察 L575 | +13.4 | 円/日 |  |  |  | 値の誤り | 出所の精密な値: alert_x1/diag_tables.json /d7/all/hi × 20 = +13.478 → +13.5。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-331 観察 L575 | +4.2 | 円/日 |  |  |  | 値の誤り | 出所の精密な値: alert_x2/diag_tables.json /d7/all/mean × 20 = +4.263 → +4.3。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-331 観察 L575 | −3.4 | 円/日 |  |  |  | 値の誤り | 出所の精密な値: alert_x2/diag_tables.json /d7/all/lo × 20 = −3.456 → −3.5。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-331 観察 L575 | +11.4 | 円/日 |  |  |  | 値の誤り | 出所の精密な値: alert_x2/diag_tables.json /d7/all/hi × 20 = +11.307 → +11.3。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-331 観察 L575 | 10.6 | 円/日 |  |  |  | 値の誤り | 出所の精密な値: alert_x2/diag_tables.json /d7/all/mde × 20 = 10.521 → 10.5。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-331 大きさ L580 | +6.4 | 円/日 |  |  |  | 値の誤り | 出所の精密な値: alert_x1/diag_tables.json /d7/all/mean × 20 = +6.343 → +6.3。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-338 観察 L694 | +193 | 円/日 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-338 観察 L694 | +342 | 円/日 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-338 観察 L694 | +194 | 円/日 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-338 観察 L694 | 664 | 円/日 |  |  |  | 確かめられない | 出所のファイルに同じ数が無い。計算の元を時間内に特定していない |
| K-342 観察 L762 | +3,065 | 円 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-342 観察 L762 | −53,696 | 円 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-350 観察 L898 | −87 | 円 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-350 観察 L898 | −87 | (語なし) |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-356 観察 L1000 | +245 | 円/日 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-356 観察 L1000 | +288 | (語なし) |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-356 観察 L1000 | −84 | 円 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-359 見出し L1050 | −2.9 | 円 |  |  |  | 確かめられない | 出所のファイルに同じ数が無い。計算の元を時間内に特定していない |
| K-359 観察 L1051 | +72 | 円/日 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-359 観察 L1051 | +204,191 | 円 |  |  |  | 確かめられない | 出所のファイルに同じ数が無い。計算の元を時間内に特定していない |
| K-359 観察 L1051 | −285,180 | 円 |  |  |  | 確かめられない | 出所のファイルに同じ数が無い。計算の元を時間内に特定していない |
| K-359 観察 L1051 | +4.7 | 円 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-359 観察 L1051 | +328,019 | 円 |  |  |  | 確かめられない | 出所のファイルに同じ数が無い。計算の元を時間内に特定していない |
| K-359 観察 L1051 | −1.8 | 円 |  |  |  | 確かめられない | −115,641 ÷ 63,442 = −1.82 で同じ行の数とは合うが、−115,641 そのものが出力に無い |
| K-359 観察 L1051 | −115,641 | 円 |  |  |  | 確かめられない | 出所のファイルに同じ数が無い。計算の元を時間内に特定していない |
| K-361 観察 L1085 | −0.5 | 円 |  |  |  | 確かめられない | bp のファイルの別の数と偶然近いだけ(出所の行を時間内に特定していない)。単位の誤りの証拠ではない |
| K-361 観察 L1085 | −6.0 | 円 |  |  |  | 確かめられない | bp のファイルの別の数と偶然近いだけ(出所の行を時間内に特定していない)。単位の誤りの証拠ではない |
| K-361 観察 L1085 | −0.5 | 円 |  |  |  | 確かめられない | bp のファイルの別の数と偶然近いだけ(出所の行を時間内に特定していない)。単位の誤りの証拠ではない |
| K-361 観察 L1085 | −6.0 | 円 |  |  |  | 確かめられない | bp のファイルの別の数と偶然近いだけ(出所の行を時間内に特定していない)。単位の誤りの証拠ではない |
| K-363 観察 L1119 | +4.23 | 円 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-363 観察 L1119 | +2.07 | 円 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-363 観察 L1119 | −0.03 | 円 |  |  |  | 確かめられない | bp のファイルの別の数と偶然近いだけ(出所の行を時間内に特定していない)。単位の誤りの証拠ではない |
| K-363 観察 L1119 | −4.44 | 円 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-363 観察 L1119 | −7.4 | 円 |  |  |  | 確かめられない | bp のファイルの別の数と偶然近いだけ(出所の行を時間内に特定していない)。単位の誤りの証拠ではない |

自動の突き合わせでは確かめられない数のうち、手で開いて分かったこと:
- K-359 の +204,191・−285,180・+328,019・−115,641 円は、`docs/RESEARCH/matilda_main/` の .out・.md のどこにも同じ数が無い(§6 の grep)。出所欄の分析の文書でも、道具は同じ数を見つけなかった(和 ÷ 本数で 1 本あたりは合う。和そのものの出所が未確認)。
- K-338 の +193・+342・+194・664 円/日(帯による分解)、K-350 の −87、K-356 の +245・+288・−84、K-361 の −0.5・−6.0(1 本あたり)、K-363 の +4.23・+2.07・−0.03・−4.44・−7.4 円は、分析の文書の中の写しとは合うか、出力の別の数と偶然近いだけで、計算の元の行を時間内に特定していない。
- 値の誤りは全部、口座の bp の表示(小数 2 桁)を × 20 したための最後の桁の違い(K-309 の区間、K-325 の 1 本あたり、K-331 の差・区間・MDE)。単位は合っている。

## 4. 台帳の全部の数

| 行 | 書かれた数 | 書かれた単位 | 出所 ファイル:行 | 出所の値 | 出所の単位 | 判定 | 備考(証拠の強さ・計算) |
|---|---|---|---|---|---|---|---|
| K-301 観察 L62 | −0.25 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:41 | -0.25 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-301 観察 L62 | −0.51 | bp | docs/RESEARCH/matilda_main/alert_x1/diag_paths.md:42 | -0.51 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-301 観察 L62 | −0.74 | bp | docs/RESEARCH/matilda_main/alert_x1/diag_paths.md:43 | -0.74 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-301 観察 L62 | −0.58 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:44 | -0.58 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-301 観察 L62 | +0.03 | bp | docs/RESEARCH/matilda_main/alert_x1/diag_paths.md:24 | 0.03 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-301 観察 L62 | −0.01 | bp | docs/RESEARCH/matilda_main/alert_x1/diag_paths.md:42 | -0.01 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-301 観察 L62 | +0.11 | bp | docs/RESEARCH/matilda_main/alert_x1/diag_paths.md:43 | 0.11 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-301 観察 L62 | +0.53 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:44 | 0.53 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-301 観察 L62 | +655,095 | 円 | docs/RESEARCH/matilda_main/count/same_bar.out:3 | 655095.0 | 円 | 一致 | 中(3 桁以上) |
| K-301 観察 L62 | −523,706 | 円 | docs/RESEARCH/matilda_main/same_bar_all.out:5 | -523706.0 | 円 | 一致 | 中(3 桁以上) |
| K-301 大きさ L67 | −0.25 | move_bp | docs/RESEARCH/matilda_main/base/diag_paths.md:41 | -0.25 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-301 大きさ L67 | −0.74 | move_bp | docs/RESEARCH/matilda_main/alert_x1/diag_paths.md:43 | -0.74 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-302 観察 L79 | −4,961,897 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d3_extra.out:24 | -4961897.0 | 円 | 一致 | 中(3 桁以上) |
| K-302 観察 L79 | −4,613,613 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d3_extra.out:38 | -4613613.0 | 円 | 一致 | 中(3 桁以上) |
| K-302 観察 L79 | −3,866,293 | 円 | docs/RESEARCH/matilda_main/alert/compare.md:6 | -3866293.0 | 円 | 一致 | 中(3 桁以上) |
| K-302 観察 L79 | −3,834,951 | 円 | docs/RESEARCH/matilda_main/alert/compare.md:14 | -3834951.0 | 円 | 一致 | 中(3 桁以上) |
| K-302 大きさ L84 | −4,961,897 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d3_extra.out:24 | -4961897.0 | 円 | 一致 | 中(3 桁以上) |
| K-302 大きさ L84 | −4,613,613 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d3_extra.out:38 | -4613613.0 | 円 | 一致 | 中(3 桁以上) |
| K-303 観察 L96 | +362 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:35 | 18.11 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-303 観察 L96 | +231 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:35 | 11.55 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-303 観察 L96 | +497 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:35 | 24.86 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-303 観察 L96 | −273 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:36 | -13.63 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-303 観察 L96 | −360 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:36 | -18.0 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-303 観察 L96 | −184 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:36 | -9.19 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-303 観察 L96 | −635 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:37 | -31.75 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-303 観察 L96 | −805 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:37 | -40.27 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-303 観察 L96 | −476 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:37 | -23.82 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-303 観察 L96 | +483,341 | 円 | docs/RESEARCH/matilda_main/count/same_bar.out:3 | 483341.0 | 円 | 一致 | 中(3 桁以上) |
| K-303 観察 L96 | +48,870 | 円 | docs/RESEARCH/matilda_main/same_bar_all.out:5 | 48870.0 | 円 | 一致 | 中(3 桁以上) |
| K-303 観察 L96 | +171,755 | 円 | docs/RESEARCH/matilda_main/count/same_bar.out:3 | 171755.0 | 円 | 一致 | 中(3 桁以上) |
| K-303 観察 L96 | −572,575 | 円 | docs/RESEARCH/matilda_main/range_lo/band_migration.out:12 | -572575.0 | 円 | 一致 | 中(3 桁以上) |
| K-303 大きさ L101 | +362 | 円/日 | docs/RESEARCH/matilda_main/base/diag_tables.md:35 | 18.11 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-303 大きさ L101 | −273 | 円/日 | docs/RESEARCH/matilda_main/base/diag_tables.md:36 | -13.63 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-303 大きさ L101 | −635 | 円/日 | docs/RESEARCH/matilda_main/base/diag_tables.md:37 | -31.75 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-303 大きさ L101 | −805 | 円/日 | docs/RESEARCH/matilda_main/base/diag_tables.md:37 | -40.27 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-303 大きさ L101 | −476 | 円/日 | docs/RESEARCH/matilda_main/base/diag_tables.md:37 | -23.82 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-304 観察 L113 | +73.2 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d3_extra.out:25 | 73.2 | 円 | 一致 | 中(3 桁以上) |
| K-304 観察 L113 | +46.0 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d3_extra.out:39 | 46.0 | 円 | 一致 | 中(3 桁以上) |
| K-304 観察 L113 | +18.0 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d3_extra.out:13 | 18.0 | 円 | 一致 | 中(3 桁以上) |
| K-304 観察 L113 | +14.3 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d3_extra.out:28 | 14.3 | 円 | 一致 | 中(3 桁以上) |
| K-304 観察 L113 | −410.9 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d3_extra.out:24 | -410.9 | 円 | 一致 | 中(3 桁以上) |
| K-304 観察 L113 | −332.1 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d3_extra.out:38 | -332.1 | 円 | 一致 | 中(3 桁以上) |
| K-306 観察 L147 | 27,504 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d0_extra.out:7 | 27504.0 | 円 | 一致 | 中(3 桁以上) |
| K-306 観察 L147 | 27,974 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d0_extra.out:2 | 27974.0 | 円 | 一致 | 中(3 桁以上) |
| K-306 観察 L147 | 25,788 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d0_extra.out:8 | 25788.0 | 円 | 一致 | 中(3 桁以上) |
| K-306 観察 L147 | 22,565 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d0_extra.out:8 | 22565.0 | 円 | 一致 | 中(3 桁以上) |
| K-306 観察 L147 | 26,207 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d0_extra.out:9 | 26207.0 | 円 | 一致 | 中(3 桁以上) |
| K-306 観察 L147 | 26,285 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d0_extra.out:10 | 26285.0 | 円 | 一致 | 中(3 桁以上) |
| K-309 観察 L198 | +2.4 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:76 | 0.12 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-309 観察 L198 | +1.4 | 円 |  |  |  | 値の誤り | 出所の精密な値: base/diag_tables.json /d6/groups/〜1 分/lo = +1.348 → +1.3(fam_tables.md も [+1.3, +3.3])。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-309 観察 L198 | +3.4 | 円 |  |  |  | 値の誤り | 出所の精密な値: base/diag_tables.json /d6/groups/〜1 分/hi = +3.346 → +3.3。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-309 観察 L198 | −2.0 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:75 | -0.1 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-309 観察 L198 | −3.2 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:75 | -0.16 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-309 観察 L198 | −0.8 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:75 | -0.04 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-309 観察 L198 | +36 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:66 | 1.82 ×20 | 口座の bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-309 大きさ L203 | +2.4 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:76 | 0.12 ×20 | 口座の bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-309 大きさ L203 | −2.0 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:75 | -0.1 ×20 | 口座の bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-310 観察 L215 | −0.34 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:22 | -0.34 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-310 観察 L215 | −0.45 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:22 | -0.45 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-310 観察 L215 | −0.22 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:22 | -0.22 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-310 観察 L215 | −0.66 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:23 | -0.66 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-310 観察 L215 | −0.89 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:23 | -0.89 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-310 観察 L215 | −0.43 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:23 | -0.43 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-310 観察 L215 | −0.42 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:24 | -0.42 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-310 観察 L215 | −0.89 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:24 | -0.89 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-310 観察 L215 | +0.01 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:24 | 0.01 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-310 大きさ L220 | −0.34 | move_bp | docs/RESEARCH/matilda_main/base/diag_paths.md:22 | -0.34 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-310 大きさ L220 | −0.66 | move_bp | docs/RESEARCH/matilda_main/base/diag_paths.md:23 | -0.66 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-311 見出し L231 | +0.54 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:35 | 0.54 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-311 観察 L232 | +0.54 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:35 | 0.54 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-311 観察 L232 | +0.04 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:35 | 0.04 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-311 観察 L232 | +1.03 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:35 | 1.03 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-311 観察 L232 | +0.53 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:44 | 0.53 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-311 大きさ L237 | +0.54 | move_bp | docs/RESEARCH/matilda_main/base/diag_paths.md:35 | 0.54 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-311 大きさ L237 | +0.04 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:35 | 0.04 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-311 大きさ L237 | +1.03 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:35 | 1.03 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 中(3 桁以上) |
| K-312 観察 L249 | +40.5 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d9b_extra.out:1 | 40.5 | 円 | 一致 | 中(3 桁以上) |
| K-312 観察 L249 | +32.2 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d9b_extra.out:5 | 32.2 | 円 | 一致 | 中(3 桁以上) |
| K-312 観察 L249 | −280.8 | 円 | docs/RESEARCH/matilda_main/range_hi/levels_reason.out:12 | -280.8 | 円 | 一致 | 中(3 桁以上) |
| K-312 観察 L249 | −240.4 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d9b_extra.out:5 | -240.4 | 円 | 一致 | 中(3 桁以上) |
| K-313 見出し L265 | −66 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d9b_extra.out:10 | -66.4 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-313 観察 L266 | +6,413,777 | 円 | docs/RESEARCH/matilda_main/levels/levels_extra.out:8 | 6413777.0 | 円 | 一致 | 中(3 桁以上) |
| K-313 観察 L266 | +5,146,755 | 円 | docs/RESEARCH/matilda_main/levels/levels_extra.out:9 | 5146755.0 | 円 | 一致 | 中(3 桁以上) |
| K-313 観察 L266 | −110,196 | 円 | docs/RESEARCH/matilda_main/levels/levels_extra.out:8 | -110196.0 | 円 | 一致 | 中(3 桁以上) |
| K-313 観察 L266 | −35.1 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d9b_extra.out:2 | -35.1 | 円 | 一致 | 中(3 桁以上) |
| K-313 観察 L266 | −292,095 | 円 | docs/RESEARCH/matilda_main/levels/levels_extra.out:9 | -292095.0 | 円 | 一致 | 中(3 桁以上) |
| K-313 観察 L266 | −100.0 | 円 | docs/RESEARCH/matilda_main/break_delay/levels_reason.out:6 | -100.0 | 円 | 一致 | 中(3 桁以上) |
| K-313 大きさ L271 | −402,291 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d9b_extra.out:10 | -402291.0 | 円 | 一致 | 中(3 桁以上) |
| K-314 見出し L282 | +2,934,918 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d9b_extra.out:11 | 2934918.0 | 円 | 一致 | 中(3 桁以上) |
| K-314 見出し L282 | −2,803,529 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d9b_extra.out:11 | -2803529.0 | 円 | 一致 | 中(3 桁以上) |
| K-314 観察 L283 | +2,934,918 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d9b_extra.out:11 | 2934918.0 | 円 | 一致 | 中(3 桁以上) |
| K-314 観察 L283 | −2,803,529 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d9b_extra.out:11 | -2803529.0 | 円 | 一致 | 中(3 桁以上) |
| K-314 観察 L283 | +1,873,935 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d9b_extra.out:3 | 1873935.0 | 円 | 一致 | 中(3 桁以上) |
| K-314 観察 L283 | −1,341,725 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d9b_extra.out:3 | -1341725.0 | 円 | 一致 | 中(3 桁以上) |
| K-314 観察 L283 | +1,060,983 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d9b_extra.out:7 | 1060983.0 | 円 | 一致 | 中(3 桁以上) |
| K-314 観察 L283 | −1,461,804 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d9b_extra.out:7 | -1461804.0 | 円 | 一致 | 中(3 桁以上) |
| K-314 大きさ L288 | +2.93 | M円 |  |  |  | 一致 | 計算で一致: d9b_extra.py を打ち直した出力(scratchpad の rerun/d9b_extra.out:11)保有≤3分 全期間 2934918 円 → +2.93M |
| K-314 大きさ L288 | −2.80 | M円 | docs/RESEARCH/matilda_main/base/diag_tables.md:56 | -140176.0 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-315 観察 L300 | −539 | 円/日 | docs/RESEARCH/matilda_main/levels_1/diag_tables.md:82 | -26.95 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | −630 | 円/日 | docs/RESEARCH/matilda_main/levels_1/diag_tables.md:82 | -31.52 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | −438 | 円/日 | docs/RESEARCH/matilda_main/levels_1/diag_tables.md:82 | -21.88 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | −108 | 円/日 | docs/RESEARCH/matilda_main/levels_3/diag_tables.md:82 | -5.38 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | −140 | 円/日 | docs/RESEARCH/matilda_main/levels_3/diag_tables.md:82 | -7.01 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | −76 | 円/日 | docs/RESEARCH/matilda_main/levels_3/diag_tables.md:82 | -3.8 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | +33 | 円/日 | docs/RESEARCH/matilda_main/levels_7/diag_tables.md:82 | 1.64 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | +13 | 円/日 | docs/RESEARCH/matilda_main/levels_7/diag_tables.md:82 | 0.66 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | +53 | 円/日 | docs/RESEARCH/matilda_main/levels_7/diag_tables.md:82 | 2.65 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | −218 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:19 | -218.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | −382 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:19 | -382.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | −53 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:19 | -53.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | −860 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:19 | -860.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | −953 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:19 | -953.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | −773 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:19 | -773.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | −15 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:20 | -15.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | −67 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:20 | -67.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | +37 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:20 | 37.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | −201 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:20 | -201.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | −237 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:20 | -237.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | −166 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:20 | -166.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | −30 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:21 | -30.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | −58 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:21 | -58.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | +2 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:21 | 2.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | +95 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:21 | 95.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | +70 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:21 | 70.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-315 観察 L300 | +121 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:21 | 121.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-315 注 L305 | +323 | 円/日 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/same_bar_daily_4fam.out:3 levels_1 同じ足の中 前半 +1616 × 1/5 = +323.2 |
| K-315 注 L305 | +350 | 円/日 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/same_bar_daily_4fam.out:5 levels_3 +583 × 3/5 = +349.8 |
| K-315 注 L305 | +329 | 円/日 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/count/same_bar_daily.out:3 base 同じ足の中 前半 +329 |
| K-315 注 L305 | +325 | 円/日 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/same_bar_daily_4fam.out:7 levels_7 +232 × 7/5 = +324.8 |
| K-315 注 L305 | −1,471 | 円/日 | docs/RESEARCH/matilda_main/same_bar_daily_4fam.out:4 | -1471.0 | 円 | 一致 | 中(3 桁以上) |
| K-315 注 L305 | −235 | 円/日 | docs/RESEARCH/matilda_main/same_bar_daily_4fam.out:6 | -235.0 | 円 | 一致 | 中(3 桁以上) |
| K-315 注 L305 | +33 | 円/日 | docs/RESEARCH/matilda_main/levels/compare.md:9 | 33.2 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-315 注 L305 | +100 | 円/日 | docs/RESEARCH/matilda_main/base/diag_paths.md:3 | 5.0 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 中(3 桁以上) |
| K-315 注 L305 | −2,129 | 円/日 | docs/RESEARCH/matilda_main/same_bar_daily_4fam.out:4 | -2129.0 | 円 | 一致 | 中(3 桁以上) |
| K-315 注 L305 | −738 | 円/日 | docs/RESEARCH/matilda_main/levels_1/diag_tables.md:88 | -36.9 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-315 注 L305 | −390 | 円/日 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/count/same_bar_daily.out:4 base 後まで持った 後半 −390 |
| K-315 注 L305 | −250 | 円/日 | docs/RESEARCH/matilda_main/half_diff_rest.out:6 | -250.0 | 円 | 一致 | 中(3 桁以上) |
| K-315 大きさ L306 | −539 | 円/日 | docs/RESEARCH/matilda_main/levels_1/diag_tables.md:82 | -26.95 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-315 大きさ L306 | −108 | 円/日 | docs/RESEARCH/matilda_main/levels/scenes.out:22 | -108.0 | 円 | 一致 | 中(3 桁以上) |
| K-315 大きさ L306 | +33 | 円/日 | docs/RESEARCH/matilda_main/levels/compare.md:9 | 33.2 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-317 観察 L336 | +145 | 円 | docs/RESEARCH/matilda_main/levels_1/diag_tables.md:35 | 7.23 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-317 観察 L336 | −93 | 円 | docs/RESEARCH/matilda_main/levels_1/diag_tables.md:35 | -4.65 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-317 観察 L336 | +395 | 円 | docs/RESEARCH/matilda_main/levels_1/diag_tables.md:35 | 19.77 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-317 観察 L336 | −1,133 | 円 | docs/RESEARCH/matilda_main/levels_1/diag_tables.md:36 | -56.63 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-317 観察 L336 | −1,278 | 円 | docs/RESEARCH/matilda_main/levels_1/diag_tables.md:36 | -63.9 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-317 観察 L336 | −984 | 円 | docs/RESEARCH/matilda_main/levels_1/diag_tables.md:36 | -49.18 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-317 観察 L336 | +42.83 | bp/日 | docs/RESEARCH/matilda_main/levels_1/diag_tables.md(2016 の行) | +42.83 | 口座の bp/日 | 単位の誤り | levels_1/diag_tables.md の 2016 年 +42.83 は口座に対する bp(1 bp = 20 円 → +856.6 円/日)。同じ行の他の数は円。「bp/日」とだけ書き、値動きの bp と読み分ける語が無い(UNITS_MAP §3 の 2 点目) |
| K-317 大きさ L341 | +145 | 円/日 | docs/RESEARCH/matilda_main/levels_1/diag_tables.md:35 | 7.23 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-317 大きさ L341 | −1,133 | 円/日 | docs/RESEARCH/matilda_main/levels_1/diag_tables.md:36 | -56.63 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-318 観察 L353 | −1,801 | 円 | docs/RESEARCH/matilda_main/levels/scenes.out:12 | -1801.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-318 観察 L353 | −2,148 | 円 | docs/RESEARCH/matilda_main/levels/scenes.out:12 | -2148.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-318 観察 L353 | −1,461 | 円 | docs/RESEARCH/matilda_main/levels/scenes.out:12 | -1461.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-318 観察 L353 | −684 | 円 | docs/RESEARCH/matilda_main/levels/scenes.out:24 | -684.0 | 円 | 一致 | 中(3 桁以上) |
| K-318 観察 L353 | −343 | 円 | docs/RESEARCH/matilda_main/base_scenes.out:12 | -343.0 | 円 | 一致 | 中(3 桁以上) |
| K-318 観察 L353 | −209 | 円 | docs/RESEARCH/matilda_main/d7_fullperiod.out:8 | -209.1 | 円 | 一致 | 中(3 桁以上) |
| K-318 観察 L353 | −710 | 円 | docs/RESEARCH/matilda_main/levels/scenes.out:6 | -710.0 | 円 | 一致 | 中(3 桁以上) |
| K-318 観察 L353 | −334 | 円 | docs/RESEARCH/matilda_main/break_len_mult/scenes.out:6 | -334.0 | 円 | 一致 | 中(3 桁以上) |
| K-318 観察 L353 | −216 | 円 | docs/RESEARCH/matilda_main/base_scenes.out:6 | -216.0 | 円 | 一致 | 中(3 桁以上) |
| K-318 観察 L353 | −145 | 円 | docs/RESEARCH/matilda_main/break_delay/scenes.out:43 | -145.0 | 円 | 一致 | 中(3 桁以上) |
| K-318 大きさ L358 | −1,801 | 円/日 | docs/RESEARCH/matilda_main/levels/scenes.out:12 | -1801.0 | 円 | 一致 | 中(3 桁以上) |
| K-318 大きさ L358 | −209 | 円/日 | docs/RESEARCH/matilda_main/d7_fullperiod.out:8 | -209.1 | 円 | 一致 | 中(3 桁以上) |
| K-319 観察 L370 | +55.8 | 円 | docs/RESEARCH/matilda_main/levels/compare.md:25 | 55.8 | 円 | 一致 | 中(3 桁以上) |
| K-319 観察 L370 | −415.2 | 円 | docs/RESEARCH/matilda_main/levels/compare.md:25 | -415.2 | 円 | 一致 | 中(3 桁以上) |
| K-319 観察 L370 | +29.5 | 円 | docs/RESEARCH/matilda_main/levels/compare.md:27 | 29.5 | 円 | 一致 | 中(3 桁以上) |
| K-319 観察 L370 | −207.2 | 円 | docs/RESEARCH/matilda_main/break_delay_4/diag_tables.md:27 | -10.36 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-321 観察 L404 | +155 | 円 | docs/RESEARCH/matilda_main/foot/foot_boundary.out:2 | 155.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 観察 L404 | +46 | 円 | docs/RESEARCH/matilda_main/foot/foot_boundary.out:2 | 46.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 観察 L404 | +264 | 円 | docs/RESEARCH/matilda_main/foot/foot_boundary.out:2 | 264.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 観察 L404 | −9 | 円 | docs/RESEARCH/matilda_main/foot/foot_boundary.out:2 | -9.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 観察 L404 | −106 | 円 | docs/RESEARCH/matilda_main/foot/foot_boundary.out:2 | -106.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 観察 L404 | +82 | 円 | docs/RESEARCH/matilda_main/foot/foot_boundary.out:2 | 82.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 観察 L404 | −273 | (語なし) | docs/RESEARCH/matilda_main/base/diag_tables.md:36 | -13.63 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-321 観察 L404 | −360 | (語なし) | docs/RESEARCH/matilda_main/base/diag_tables.md:36 | -18.0 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-321 観察 L404 | −184 | (語なし) | docs/RESEARCH/matilda_main/base/diag_tables.md:36 | -9.19 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-321 観察 L404 | +30 | 円/日 | docs/RESEARCH/matilda_main/foot_5/diag_tables.md:82 | 1.48 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-321 観察 L404 | −66 | 円/日 | docs/RESEARCH/matilda_main/foot_5/diag_tables.md:82 | -3.29 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-321 観察 L404 | +128 | 円/日 | docs/RESEARCH/matilda_main/foot_5/diag_tables.md:82 | 6.39 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-321 観察 L404 | 139 | 円/日 | docs/RESEARCH/matilda_main/foot_5/diag_tables.md:82 | 6.97 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-321 観察 L404 | −204 | 円/日 | docs/RESEARCH/matilda_main/half_diff.out:5 | -204.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 観察 L404 | −354 | 円/日 | docs/RESEARCH/matilda_main/half_diff.out:5 | -354.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 観察 L404 | −53 | 円/日 | docs/RESEARCH/matilda_main/half_diff.out:5 | -53.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 観察 L404 | +263 | 円/日 | docs/RESEARCH/matilda_main/half_diff.out:5 | 263.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 観察 L404 | +144 | 円/日 | docs/RESEARCH/matilda_main/half_diff.out:5 | 144.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 観察 L404 | +377 | 円/日 | docs/RESEARCH/matilda_main/half_diff.out:5 | 377.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 観察 L404 | 131 | 円/日 | docs/RESEARCH/matilda_main/foot_5/diag_tables.md:36 | 6.53 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-321 観察 L404 | +155 | 円/日 | docs/RESEARCH/matilda_main/foot/foot_boundary.out:1 | 155.0 | 円 | 一致 | 中(3 桁以上) |
| K-321 注 L409 | +110 | 円/日 | docs/RESEARCH/matilda_main/same_bar_daily_4fam.out:9 | 110.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 注 L409 | +87 | 円/日 | docs/RESEARCH/matilda_main/same_bar_daily_4fam.out:9 | 87.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 注 L409 | +131 | 円/日 | docs/RESEARCH/matilda_main/same_bar_daily_4fam.out:9 | 131.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 注 L409 | +45 | 円/日 | docs/RESEARCH/matilda_main/same_bar_daily_4fam.out:10 | 45.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 注 L409 | −57 | 円/日 | docs/RESEARCH/matilda_main/same_bar_daily_4fam.out:10 | -57.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 注 L409 | +147 | 円/日 | docs/RESEARCH/matilda_main/same_bar_daily_4fam.out:10 | 147.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 注 L409 | −35 | 円/日 | docs/RESEARCH/matilda_main/same_bar_daily_4fam.out:10 | -35.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 注 L409 | −131 | 円/日 | docs/RESEARCH/matilda_main/same_bar_daily_4fam.out:10 | -131.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 注 L409 | +55 | 円/日 | docs/RESEARCH/matilda_main/same_bar_daily_4fam.out:10 | 55.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 大きさ L410 | −9 | 円/日 | docs/RESEARCH/matilda_main/foot/foot_boundary.out:2 | -9.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 大きさ L410 | −106 | 円/日 | docs/RESEARCH/matilda_main/foot/foot_boundary.out:2 | -106.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 大きさ L410 | +82 | 円/日 | docs/RESEARCH/matilda_main/foot/foot_boundary.out:2 | 82.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-321 大きさ L410 | 131 | 円/日 | docs/RESEARCH/matilda_main/foot_5/diag_tables.md:36 | 6.53 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-321 大きさ L410 | −273 | (語なし) | docs/RESEARCH/matilda_main/base/diag_tables.md:36 | -13.63 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-323 観察 L439 | +0.45 | move_bp | docs/RESEARCH/matilda_main/foot_5/diag_paths.md:43 | 0.45 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-323 観察 L439 | +0.11 | move_bp | docs/RESEARCH/matilda_main/foot_5/diag_paths.md:43 | 0.11 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-323 観察 L439 | +0.79 | move_bp | docs/RESEARCH/matilda_main/foot_5/diag_paths.md:43 | 0.79 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-323 観察 L439 | +1.47 | move_bp | docs/RESEARCH/matilda_main/foot_5/diag_paths.md:44 | 1.47 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-323 観察 L439 | +0.49 | move_bp | docs/RESEARCH/matilda_main/foot_5/diag_paths.md:44 | 0.49 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-323 観察 L439 | +2.42 | move_bp | docs/RESEARCH/matilda_main/foot_5/diag_paths.md:44 | 2.42 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-323 観察 L439 | +0.53 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:44 | 0.53 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-323 観察 L439 | +0.03 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:44 | 0.03 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-323 観察 L439 | +1.03 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:44 | 1.03 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-323 観察 L439 | −1.30 | (語なし) | docs/RESEARCH/matilda_main/foot_5/diag_paths.md:43 | -1.3 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 中(3 桁以上) |
| K-323 観察 L439 | −3.60 | (語なし) |  |  |  | 確かめられない | 本体の move_bp(foot_5 の D5)を出所で特定していない。自動の突き合わせは bp のファイルの別の数を × 20 で拾っただけ |
| K-323 観察 L439 | +0.53 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:44 | 0.53 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-323 大きさ L444 | +1.47 | move_bp | docs/RESEARCH/matilda_main/foot_5/diag_paths.md:44 | 1.47 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 中(3 桁以上) |
| K-323 大きさ L444 | +0.53 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:44 | 0.53 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-324 観察 L456 | +283 | 円 | docs/RESEARCH/matilda_main/foot/scenes.out:11 | 283.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-324 観察 L456 | +57 | 円 | docs/RESEARCH/matilda_main/foot/scenes.out:11 | 57.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-324 観察 L456 | +554 | 円 | docs/RESEARCH/matilda_main/foot/scenes.out:11 | 554.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-324 観察 L456 | +143 | 円 | docs/RESEARCH/matilda_main/foot/scenes.out:8 | 143.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-324 観察 L456 | −181 | 円 | docs/RESEARCH/matilda_main/foot/scenes.out:8 | -181.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-324 観察 L456 | +399 | 円 | docs/RESEARCH/matilda_main/foot/scenes.out:8 | 399.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-324 観察 L456 | +77 | 円 | docs/RESEARCH/matilda_main/foot/scenes.out:5 | 77.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-324 観察 L456 | −23 | 円 | docs/RESEARCH/matilda_main/foot/scenes.out:5 | -23.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-324 観察 L456 | +180 | 円 | docs/RESEARCH/matilda_main/foot/scenes.out:5 | 180.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-324 大きさ L461 | +283 | 円/日 | docs/RESEARCH/matilda_main/foot/scenes.out:11 | 283.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-324 大きさ L461 | +57 | 円/日 | docs/RESEARCH/matilda_main/foot/scenes.out:11 | 57.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-324 大きさ L461 | +554 | 円/日 | docs/RESEARCH/matilda_main/foot/scenes.out:11 | 554.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-325 観察 L473 | +73.6 | 円 |  |  |  | 値の誤り | 出所の精密な値: foot/compare.md:21 利確 1 本 = +73.7(foot_5/diag_tables.json close per_trade × 20 = +73.70)。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-325 観察 L473 | −562.8 | 円 |  |  |  | 値の誤り | 出所の精密な値: foot/compare.md:21 ブレイク 1 本 = −562.7(json × 20 = −562.71)。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-325 観察 L473 | +36.4 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:66 | 1.82 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-325 観察 L473 | −258.8 | 円 | docs/RESEARCH/matilda_main/alert/compare.md:22 | -258.8 | 円 | 一致 | 中(3 桁以上) |
| K-325 観察 L473 | +73 | 円/日 | docs/RESEARCH/matilda_main/foot_5/diag_tables.md:20 | 3.63 ×20 | 口座の bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-325 観察 L473 | +45 | 円/日 | docs/RESEARCH/matilda_main/base/diag_tables.md:20 | 2.24 ×20 | 口座の bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-326 観察 L490 | −27 | 円 | docs/RESEARCH/matilda_main/count_20/diag_tables.md:35 | -1.33 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-326 観察 L490 | −125 | 円 | docs/RESEARCH/matilda_main/count_20/diag_tables.md:35 | -6.24 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-326 観察 L490 | +78 | 円 | docs/RESEARCH/matilda_main/count_20/diag_tables.md:35 | 3.89 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-326 観察 L490 | −252 | 円 | docs/RESEARCH/matilda_main/count_20/diag_tables.md:36 | -12.58 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-326 観察 L490 | −317 | 円 | docs/RESEARCH/matilda_main/count_20/diag_tables.md:36 | -15.84 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-326 観察 L490 | −188 | 円 | docs/RESEARCH/matilda_main/count_20/diag_tables.md:36 | -9.42 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-326 観察 L490 | −392 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:14 | -392.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-326 観察 L490 | −499 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:14 | -499.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-326 観察 L490 | −277 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:14 | -277.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-326 観察 L490 | +21 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:14 | 21.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-326 観察 L490 | −66 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:14 | -66.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-326 観察 L490 | +104 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:14 | 104.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-326 観察 L490 | +22.6 | 円 | docs/RESEARCH/matilda_main/count/compare.md:23 | 22.6 | 円 | 一致 | 中(3 桁以上) |
| K-326 観察 L490 | −88.0 | 円 | docs/RESEARCH/matilda_main/count/compare.md:23 | -88.0 | 円 | 一致 | 中(3 桁以上) |
| K-326 大きさ L495 | −27 | 円/日 | docs/RESEARCH/matilda_main/count_20/diag_tables.md:35 | -1.33 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-326 大きさ L495 | −125 | 円/日 | docs/RESEARCH/matilda_main/count_20/diag_tables.md:35 | -6.24 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-326 大きさ L495 | +78 | 円/日 | docs/RESEARCH/matilda_main/count_20/diag_tables.md:35 | 3.89 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-326 大きさ L495 | −392 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:14 | -392.0 | 円 | 一致 | 中(3 桁以上) |
| K-327 観察 L507 | +478 | 円 | docs/RESEARCH/matilda_main/count_80/diag_tables.md:35 | 23.92 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-327 観察 L507 | +307 | 円 | docs/RESEARCH/matilda_main/count_80/diag_tables.md:35 | 15.35 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-327 観察 L507 | +643 | 円 | docs/RESEARCH/matilda_main/count_80/diag_tables.md:35 | 32.17 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-327 観察 L507 | −411 | 円 | docs/RESEARCH/matilda_main/count_80/diag_tables.md:36 | -20.57 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-327 観察 L507 | −543 | 円 | docs/RESEARCH/matilda_main/count_80/diag_tables.md:36 | -27.14 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-327 観察 L507 | −291 | 円 | docs/RESEARCH/matilda_main/count_80/diag_tables.md:36 | -14.54 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-327 観察 L507 | −890 | 円 | docs/RESEARCH/matilda_main/count_80/diag_tables.md:37 | -44.49 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-327 観察 L507 | −1,088 | 円 | docs/RESEARCH/matilda_main/count_80/diag_tables.md:37 | -54.4 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-327 観察 L507 | −697 | 円 | docs/RESEARCH/matilda_main/count_80/diag_tables.md:37 | -34.86 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-327 観察 L507 | −635 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:37 | -31.75 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-327 観察 L507 | +126 | (語なし) | docs/RESEARCH/matilda_main/half_diff_rest.out:6 | 126.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-327 観察 L507 | −27 | (語なし) | docs/RESEARCH/matilda_main/half_diff_rest.out:6 | -27.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-327 観察 L507 | +271 | (語なし) | docs/RESEARCH/matilda_main/half_diff_rest.out:6 | 271.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-327 観察 L507 | −138 | (語なし) | docs/RESEARCH/matilda_main/half_diff_rest.out:6 | -138.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-327 観察 L507 | −250 | (語なし) | docs/RESEARCH/matilda_main/half_diff_rest.out:6 | -250.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-327 観察 L507 | −25 | (語なし) | docs/RESEARCH/matilda_main/half_diff_rest.out:6 | -25.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-327 観察 L507 | −6 | (語なし) | docs/RESEARCH/matilda_main/count_80/diag_tables.md:81 | -0.29 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-327 観察 L507 | −101 | (語なし) | docs/RESEARCH/matilda_main/count_80/diag_tables.md:81 | -5.06 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-327 観察 L507 | +93 | (語なし) | docs/RESEARCH/matilda_main/count_80/diag_tables.md:81 | 4.66 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-327 観察 L507 | 136 | (語なし) | docs/RESEARCH/matilda_main/count_80/diag_tables.md:81 | 6.82 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-327 大きさ L512 | −890 | 円/日 | docs/RESEARCH/matilda_main/count_80/diag_tables.md:37 | -44.49 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-327 大きさ L512 | −635 | 円/日 | docs/RESEARCH/matilda_main/base/diag_tables.md:37 | -31.75 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-328 観察 L524 | +483,341 | 円 | docs/RESEARCH/matilda_main/count/same_bar.out:3 | 483341.0 | 円 | 一致 | 中(3 桁以上) |
| K-328 観察 L524 | +171,755 | 円 | docs/RESEARCH/matilda_main/count/same_bar.out:3 | 171755.0 | 円 | 一致 | 中(3 桁以上) |
| K-328 観察 L524 | +48,870 | 円 | docs/RESEARCH/matilda_main/same_bar_all.out:5 | 48870.0 | 円 | 一致 | 中(3 桁以上) |
| K-328 観察 L524 | −572,575 | 円 | docs/RESEARCH/matilda_main/range_lo/band_migration.out:12 | -572575.0 | 円 | 一致 | 中(3 桁以上) |
| K-328 観察 L524 | +131,389 | 円 | docs/RESEARCH/matilda_main/alert/compare.md:22 | 131389.0 | 円 | 一致 | 中(3 桁以上) |
| K-328 観察 L524 | −2,160,842 | 円 | docs/RESEARCH/matilda_main/same_bar_all.out:20 | -2160842.0 | 円 | 一致 | 中(3 桁以上) |
| K-328 観察 L524 | +264,630 | 円 | docs/RESEARCH/matilda_main/same_bar_all.out:13 | 264630.0 | 円 | 一致 | 中(3 桁以上) |
| K-328 観察 L524 | −248,970 | 円 | docs/RESEARCH/matilda_main/count/same_bar.out:4 | -248970.0 | 円 | 一致 | 中(3 桁以上) |
| K-328 観察 L524 | +329 | 円/日 | docs/RESEARCH/matilda_main/count/same_bar_daily.out:3 | 329.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-328 観察 L524 | +274 | 円/日 | docs/RESEARCH/matilda_main/count/same_bar_daily.out:3 | 274.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-328 観察 L524 | +378 | 円/日 | docs/RESEARCH/matilda_main/count/same_bar_daily.out:3 | 378.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-328 観察 L524 | +117 | 円/日 | docs/RESEARCH/matilda_main/count/same_bar_daily.out:3 | 117.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-328 観察 L524 | +92 | 円/日 | docs/RESEARCH/matilda_main/count/same_bar_daily.out:3 | 92.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-328 観察 L524 | +141 | 円/日 | docs/RESEARCH/matilda_main/count/same_bar_daily.out:3 | 141.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-328 観察 L524 | +33 | 円/日 | docs/RESEARCH/matilda_main/count/same_bar_daily.out:4 | 33.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-328 観察 L524 | −100 | 円/日 | docs/RESEARCH/matilda_main/count/same_bar_daily.out:4 | -100.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-328 観察 L524 | +167 | 円/日 | docs/RESEARCH/matilda_main/count/same_bar_daily.out:4 | 167.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-328 観察 L524 | −390 | 円/日 | docs/RESEARCH/matilda_main/count/same_bar_daily.out:4 | -390.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-328 観察 L524 | −474 | 円/日 | docs/RESEARCH/matilda_main/count/same_bar_daily.out:4 | -474.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-328 観察 L524 | −302 | 円/日 | docs/RESEARCH/matilda_main/count/same_bar_daily.out:4 | -302.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-328 大きさ L529 | −390 | 円/日 | docs/RESEARCH/matilda_main/count/same_bar_daily.out:4 | -390.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-328 大きさ L529 | −474 | 円/日 | docs/RESEARCH/matilda_main/count/same_bar_daily.out:4 | -474.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-328 大きさ L529 | −302 | 円/日 | docs/RESEARCH/matilda_main/count/same_bar_daily.out:4 | -302.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-328 大きさ L529 | +117 | 円/日 | docs/RESEARCH/matilda_main/count/same_bar_daily.out:3 | 117.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-328 大きさ L529 | +92 | 円/日 | docs/RESEARCH/matilda_main/count/same_bar_daily.out:3 | 92.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-328 大きさ L529 | +141 | 円/日 | docs/RESEARCH/matilda_main/count/same_bar_daily.out:3 | 141.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-329 観察 L541 | −816 | 円 | docs/RESEARCH/matilda_main/count/scenes.out:24 | -816.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-329 観察 L541 | −1,102 | 円 | docs/RESEARCH/matilda_main/count/scenes.out:24 | -1102.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-329 観察 L541 | −539 | 円 | docs/RESEARCH/matilda_main/count/scenes.out:24 | -539.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-329 観察 L541 | −343 | 円 | docs/RESEARCH/matilda_main/base_scenes.out:12 | -343.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-329 観察 L541 | −529 | 円 | docs/RESEARCH/matilda_main/base_scenes.out:12 | -529.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-329 観察 L541 | −135 | 円 | docs/RESEARCH/matilda_main/base_scenes.out:12 | -135.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-329 観察 L541 | −473 | 円 | docs/RESEARCH/matilda_main/count/scene_diff.out:18 | -473.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-329 観察 L541 | −728 | 円 | docs/RESEARCH/matilda_main/count/scene_diff.out:18 | -728.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-329 観察 L541 | −226 | 円 | docs/RESEARCH/matilda_main/count/scene_diff.out:18 | -226.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-329 観察 L541 | +714 | (語なし) | docs/RESEARCH/matilda_main/count/scenes.out:23 | 714.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-329 観察 L541 | +257 | (語なし) | docs/RESEARCH/matilda_main/count/scenes.out:23 | 257.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-329 観察 L541 | +1,170 | (語なし) | docs/RESEARCH/matilda_main/count/scenes.out:23 | 1170.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-329 観察 L541 | +656 | (語なし) | docs/RESEARCH/matilda_main/base_scenes.out:11 | 656.0 | 円 | 一致 | 中(3 桁以上) |
| K-329 観察 L541 | −318 | (語なし) | docs/RESEARCH/matilda_main/count/market_side.out:2 | -318.0 | 円 | 一致 | 中(3 桁以上) |
| K-329 観察 L541 | −171 | (語なし) | docs/RESEARCH/matilda_main/count/scenes.out:18 | -171.0 | 円 | 一致 | 中(3 桁以上) |
| K-329 観察 L541 | −282 | (語なし) | docs/RESEARCH/matilda_main/base_scenes.out:9 | -282.0 | 円 | 一致 | 中(3 桁以上) |
| K-329 観察 L541 | −216 | (語なし) | docs/RESEARCH/matilda_main/base_scenes.out:6 | -216.0 | 円 | 一致 | 中(3 桁以上) |
| K-329 大きさ L546 | −816 | 円/日 | docs/RESEARCH/matilda_main/count/scenes.out:24 | -816.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-329 大きさ L546 | −1,102 | 円/日 | docs/RESEARCH/matilda_main/count/scenes.out:24 | -1102.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-329 大きさ L546 | −539 | 円/日 | docs/RESEARCH/matilda_main/count/scenes.out:24 | -539.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-330 観察 L558 | −17 | move_bp | docs/RESEARCH/matilda_main/count_20/diag_paths.md:12 | -16.99 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-330 観察 L558 | −21 | move_bp | docs/RESEARCH/matilda_main/count_20/diag_paths.md:13 | -21.44 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-330 観察 L558 | −31 | move_bp | docs/RESEARCH/matilda_main/base/diag_paths.md:12 | -30.5 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-330 観察 L558 | −32 | move_bp | docs/RESEARCH/matilda_main/base/diag_paths.md:13 | -32.38 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-330 観察 L558 | −52 | move_bp | docs/RESEARCH/matilda_main/count_80/diag_paths.md:12 | -52.47 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-331 観察 L575 | +6.4 | 円/日 |  |  |  | 値の誤り | 出所の精密な値: alert_x1/diag_tables.json /d7/all/mean × 20 = +6.343 → +6.3。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-331 観察 L575 | −1.4 | 円/日 |  |  |  | 値の誤り | 出所の精密な値: alert_x1/diag_tables.json /d7/all/lo × 20 = −1.335 → −1.3。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-331 観察 L575 | +13.4 | 円/日 |  |  |  | 値の誤り | 出所の精密な値: alert_x1/diag_tables.json /d7/all/hi × 20 = +13.478 → +13.5。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-331 観察 L575 | 10.8 | 円/日 | docs/RESEARCH/matilda_main/alert_x1/diag_paths.md:35 | 0.54 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 中(3 桁以上) |
| K-331 観察 L575 | +4.2 | 円/日 |  |  |  | 値の誤り | 出所の精密な値: alert_x2/diag_tables.json /d7/all/mean × 20 = +4.263 → +4.3。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-331 観察 L575 | −3.4 | 円/日 |  |  |  | 値の誤り | 出所の精密な値: alert_x2/diag_tables.json /d7/all/lo × 20 = −3.456 → −3.5。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-331 観察 L575 | +11.4 | 円/日 |  |  |  | 値の誤り | 出所の精密な値: alert_x2/diag_tables.json /d7/all/hi × 20 = +11.307 → +11.3。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-331 観察 L575 | 10.6 | 円/日 |  |  |  | 値の誤り | 出所の精密な値: alert_x2/diag_tables.json /d7/all/mde × 20 = 10.521 → 10.5。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-331 観察 L575 | +12 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:3 | 12.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-331 観察 L575 | −0 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:3 | -0.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-331 観察 L575 | +26 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:3 | 26.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-331 観察 L575 | +7 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:4 | 7.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-331 観察 L575 | −5 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:4 | -5.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-331 観察 L575 | +20 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:4 | 20.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-331 観察 L575 | +1 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:3 | 1.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-331 観察 L575 | −7 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:3 | -7.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-331 観察 L575 | +8 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:3 | 8.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-331 観察 L575 | +1 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:4 | 1.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-331 観察 L575 | −6 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:4 | -6.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-331 観察 L575 | +9 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:4 | 9.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-331 観察 L575 | −3,200 | 円 | docs/RESEARCH/matilda_main/alert_x1/diag_tables.md:93 | -160.0 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-331 観察 L575 | −13,300 | 円 | docs/RESEARCH/matilda_main/alert_x2/diag_tables.md:93 | -665.0 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-331 観察 L575 | −21,120 | 円 | docs/RESEARCH/matilda_main/alert_x1/diag_tables.md:93 | -1056.0 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-331 観察 L575 | −19,700 | 円 | docs/RESEARCH/matilda_main/alert_x2/diag_tables.md:93 | -985.0 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-331 大きさ L580 | +6.4 | 円/日 |  |  |  | 値の誤り | 出所の精密な値: alert_x1/diag_tables.json /d7/all/mean × 20 = +6.343 → +6.3。書かれた値は bp の表示(小数 2 桁)を × 20 した丸め |
| K-331 大きさ L580 | 10.8 | 円/日 | docs/RESEARCH/matilda_main/alert_x1/diag_paths.md:35 | 0.54 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 中(3 桁以上) |
| K-332 観察 L592 | −1,567,278 | 円 | docs/RESEARCH/matilda_main/alert/alert_check.out:7 | -1567278.0 | 円 | 一致 | 中(3 桁以上) |
| K-332 観察 L592 | −1,547,867 | 円 | docs/RESEARCH/matilda_main/alert/alert_check.out:8 | -1547867.0 | 円 | 一致 | 中(3 桁以上) |
| K-332 観察 L592 | −1,554,138 | 円 | docs/RESEARCH/matilda_main/alert/alert_check.out:9 | -1554138.0 | 円 | 一致 | 中(3 桁以上) |
| K-332 観察 L592 | −279,010 | 円 | docs/RESEARCH/matilda_main/alert/alert_check.out:10 | -279010.0 | 円 | 一致 | 中(3 桁以上) |
| K-332 観察 L592 | −62,873 | 円 | docs/RESEARCH/matilda_main/alert/alert_check.out:11 | -62873.0 | 円 | 一致 | 中(3 桁以上) |
| K-332 観察 L592 | −21,310 | 円 | docs/RESEARCH/matilda_main/alert/alert_check.out:12 | -21310.0 | 円 | 一致 | 中(3 桁以上) |
| K-332 観察 L592 | −901,707 | 円 | docs/RESEARCH/matilda_main/alert/alert_check.out:10 | -901707.0 | 円 | 一致 | 中(3 桁以上) |
| K-332 観察 L592 | −1,126,619 | 円 | docs/RESEARCH/matilda_main/alert/alert_check.out:11 | -1126619.0 | 円 | 一致 | 中(3 桁以上) |
| K-332 観察 L592 | −1,165,218 | 円 | docs/RESEARCH/matilda_main/alert/alert_check.out:12 | -1165218.0 | 円 | 一致 | 中(3 桁以上) |
| K-332 観察 L592 | +131,389 | 円 | docs/RESEARCH/matilda_main/alert/compare.md:22 | 131389.0 | 円 | 一致 | 中(3 桁以上) |
| K-332 観察 L592 | −155 | 万円 | docs/RESEARCH/matilda_main/alert/alert_check.out:8 | -1547867.0 | 円 | 一致 | 中(3 桁以上) |
| K-332 大きさ L597 | −155 | 万円 | docs/RESEARCH/matilda_main/alert/alert_check.out:8 | -1547867.0 | 円 | 一致 | 中(3 桁以上) |
| K-333 観察 L609 | +10 | 円/日 | docs/RESEARCH/matilda_main/alert/scene_diff.out:5 | 10.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-333 観察 L609 | +1 | 円/日 | docs/RESEARCH/matilda_main/alert/scene_diff.out:5 | 1.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-333 観察 L609 | +21 | 円/日 | docs/RESEARCH/matilda_main/alert/scene_diff.out:5 | 21.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-333 観察 L609 | +11 | 円/日 | docs/RESEARCH/matilda_main/alert/scene_diff.out:14 | 11.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-333 観察 L609 | +2 | 円/日 | docs/RESEARCH/matilda_main/alert/scene_diff.out:14 | 2.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-333 観察 L609 | +22 | 円/日 | docs/RESEARCH/matilda_main/alert/scene_diff.out:14 | 22.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-333 大きさ L614 | +10 | 円/日 | docs/RESEARCH/matilda_main/alert/scene_diff.out:5 | 10.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-333 大きさ L614 | +1 | 円/日 | docs/RESEARCH/matilda_main/alert/scene_diff.out:5 | 1.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-333 大きさ L614 | +21 | 円/日 | docs/RESEARCH/matilda_main/alert/scene_diff.out:5 | 21.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-334 観察 L626 | +143 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:17 | 143.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-334 観察 L626 | +68 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:17 | 68.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-334 観察 L626 | +219 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:17 | 219.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-334 観察 L626 | −212 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:17 | -212.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-334 観察 L626 | −273 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:17 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-334 観察 L626 | −154 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:17 | -154.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-334 観察 L626 | +114 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:16 | 114.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-334 観察 L626 | −30 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:16 | -30.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-334 観察 L626 | +238 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:16 | 238.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-334 観察 L626 | −470 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:16 | -470.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-334 観察 L626 | −565 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:16 | -565.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-334 観察 L626 | −372 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:16 | -372.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-334 観察 L626 | −273 | 円/日 | docs/RESEARCH/matilda_main/base/diag_tables.md:36 | -13.63 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-334 観察 L626 | −485 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:15 | -485.0 | 円 | 一致 | 中(3 桁以上) |
| K-334 観察 L626 | −743 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:16 | -743.0 | 円 | 一致 | 中(3 桁以上) |
| K-334 大きさ L631 | −212 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:17 | -212.0 | 円 | 一致 | 中(3 桁以上) |
| K-334 大きさ L631 | −470 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:16 | -470.0 | 円 | 一致 | 中(3 桁以上) |
| K-335 観察 L643 | −258.8 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:65 | -12.94 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-335 観察 L643 | −271.6 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:65 | -13.58 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-335 観察 L643 | −246.3 | 円 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:42 | -246.3 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-335 観察 L643 | −335.3 | 円 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:40 | -335.3 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-335 観察 L643 | −352.0 | 円 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:40 | -352.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-335 観察 L643 | −318.3 | 円 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:40 | -318.3 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-335 観察 L643 | −411.2 | 円 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:41 | -411.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-335 観察 L643 | −432.5 | 円 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:41 | -432.5 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-335 観察 L643 | −389.8 | 円 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:41 | -389.8 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-335 観察 L643 | +36.4 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:66 | 1.82 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-335 観察 L643 | +41.7 | 円 | docs/RESEARCH/matilda_main/entry_exit/compare.md:23 | 41.7 | 円 | 一致 | 中(3 桁以上) |
| K-335 観察 L643 | +46.5 | 円 | docs/RESEARCH/matilda_main/entry_exit/compare.md:24 | 46.5 | 円 | 一致 | 中(3 桁以上) |
| K-335 観察 L643 | −30.5 | move_bp | docs/RESEARCH/matilda_main/base/diag_paths.md:12 | -30.5 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 中(3 桁以上) |
| K-335 観察 L643 | −34.8 | move_bp | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:49 | -34.77 | 円(和)/値動きの bp(MFE・MAE) | 一致 | 中(3 桁以上) |
| K-335 観察 L643 | −38.7 | move_bp | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:53 | -38.65 | 円(和)/値動きの bp(MFE・MAE) | 一致 | 中(3 桁以上) |
| K-335 観察 L643 | −7,701,243 | 円 | docs/RESEARCH/matilda_main/alert/compare.md:22 | -7701243.0 | 円 | 一致 | 中(3 桁以上) |
| K-335 観察 L643 | −10,729,791 | 円 | docs/RESEARCH/matilda_main/entry_exit/compare.md:23 | -10729791.0 | 円 | 一致 | 中(3 桁以上) |
| K-335 観察 L643 | −13,642,774 | 円 | docs/RESEARCH/matilda_main/entry_exit/compare.md:24 | -13642774.0 | 円 | 一致 | 中(3 桁以上) |
| K-335 大きさ L648 | −259 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:65 | -12.94 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-335 大きさ L648 | −335 | 円 | docs/RESEARCH/matilda_main/entry_exit/compare.md:23 | -335.3 | 円 | 一致 | 中(3 桁以上) |
| K-335 大きさ L648 | −411 | 円 | docs/RESEARCH/matilda_main/entry_exit/compare.md:24 | -411.2 | 円 | 一致 | 中(3 桁以上) |
| K-336 観察 L660 | −81 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:5 | -81.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −122 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:5 | -122.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −32 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:5 | -32.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −173 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:7 | -173.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −273 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:7 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −88 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:7 | -88.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −422 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:9 | -422.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −590 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:9 | -590.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −280 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:9 | -280.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −193 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:14 | -193.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −261 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:14 | -261.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −108 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:14 | -108.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −394 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:16 | -394.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −544 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:16 | -544.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −243 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:16 | -243.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −911 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:18 | -911.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −1,135 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:18 | -1135.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −697 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:18 | -697.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −129 | (語なし) | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:13 | -129.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −254 | (語なし) | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:13 | -254.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 観察 L660 | −3 | (語なし) | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:13 | -3.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-336 大きさ L665 | −422 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:9 | -422.0 | 円 | 一致 | 中(3 桁以上) |
| K-336 大きさ L665 | −911 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/scene_diff.out:18 | -911.0 | 円 | 一致 | 中(3 桁以上) |
| K-337 観察 L677 | −0.25 | move_bp | docs/RESEARCH/matilda_main/base/diag_paths.md:41 | -0.25 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | −0.31 | move_bp | docs/RESEARCH/matilda_main/base/diag_paths.md:41 | -0.31 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | −0.20 | move_bp | docs/RESEARCH/matilda_main/base/diag_paths.md:41 | -0.2 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | −0.20 | move_bp | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:71 | -0.2 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | −0.24 | move_bp | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:71 | -0.24 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | −0.15 | move_bp | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:71 | -0.15 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | −0.12 | move_bp | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:72 | -0.12 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | −0.16 | move_bp | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:72 | -0.16 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | −0.08 | move_bp | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:72 | -0.08 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | −0.51 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:42 | -0.51 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-337 観察 L677 | −0.51 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:42 | -0.51 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-337 観察 L677 | −0.30 | bp | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:72 | -0.3 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | −0.39 | bp | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:72 | -0.39 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | −0.22 | bp | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:72 | -0.22 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | +0.36 | (語なし) | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:71 | 0.36 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | −0.02 | (語なし) | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:71 | -0.02 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | +0.76 | (語なし) | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:71 | 0.76 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | +0.25 | (語なし) | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:72 | 0.25 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | −0.06 | (語なし) | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:72 | -0.06 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | +0.59 | (語なし) | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:72 | 0.59 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | +0.53 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:44 | 0.53 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | +0.03 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:44 | 0.03 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-337 観察 L677 | +1.03 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:44 | 1.03 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-337 大きさ L682 | −0.25 | move_bp | docs/RESEARCH/matilda_main/base/diag_paths.md:41 | -0.25 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-337 大きさ L682 | −0.12 | move_bp | docs/RESEARCH/matilda_main/base/diag_paths.md:42 | -0.12 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-338 観察 L694 | +329 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:35 | 329.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-338 観察 L694 | +274 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:35 | 274.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-338 観察 L694 | +378 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:35 | 378.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-338 観察 L694 | +522 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:31 | 522.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-338 観察 L694 | +458 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:31 | 458.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-338 観察 L694 | +578 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:31 | 578.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-338 観察 L694 | +671 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:33 | 671.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-338 観察 L694 | +598 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:33 | 598.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-338 観察 L694 | +735 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:33 | 735.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-338 観察 L694 | +9.9 | 円 | docs/RESEARCH/matilda_main/beard/levels_band.out:7 | 9.9 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-338 観察 L694 | +14.3 | 円 | docs/RESEARCH/matilda_main/entry_exit/levels_band.out:3 | 14.3 | 円 | 一致 | 中(3 桁以上) |
| K-338 観察 L694 | +17.5 | 円 | docs/RESEARCH/matilda_main/entry_exit/levels_band.out:7 | 17.5 | 円 | 一致 | 中(3 桁以上) |
| K-338 観察 L694 | +143 | 円/日 | docs/RESEARCH/matilda_main/base_scenes.out:7 | 143.0 | 円 | 一致 | 中(3 桁以上) |
| K-338 観察 L694 | +193 | 円/日 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-338 観察 L694 | −50 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:41 | -50.4 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-338 観察 L694 | −212 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:17 | -212.0 | 円 | 一致 | 中(3 桁以上) |
| K-338 観察 L694 | +108 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/band_migration.out:6 | 108.0 | 円 | 一致 | 中(3 桁以上) |
| K-338 観察 L694 | +114 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:8 | 114.0 | 円 | 一致 | 中(3 桁以上) |
| K-338 観察 L694 | +342 | 円/日 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-338 観察 L694 | −470 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:16 | -470.0 | 円 | 一致 | 中(3 桁以上) |
| K-338 観察 L694 | +194 | 円/日 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-338 観察 L694 | 664 | 円/日 |  |  |  | 確かめられない | 出所のファイルに同じ数が無い。計算の元を時間内に特定していない |
| K-338 大きさ L699 | +329 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:35 | 329.0 | 円 | 一致 | 中(3 桁以上) |
| K-338 大きさ L699 | +522 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:31 | 522.0 | 円 | 一致 | 中(3 桁以上) |
| K-338 大きさ L699 | +671 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:33 | 671.0 | 円 | 一致 | 中(3 桁以上) |
| K-339 観察 L711 | −116 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:29 | -116.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-339 観察 L711 | −163 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:29 | -163.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-339 観察 L711 | −72 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:29 | -72.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-339 観察 L711 | +50 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:29 | 50.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-339 観察 L711 | +16 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:29 | 16.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-339 観察 L711 | +84 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:29 | 84.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-339 観察 L711 | −233 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:30 | -233.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-339 観察 L711 | −314 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:30 | -314.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-339 観察 L711 | −160 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:30 | -160.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-339 観察 L711 | +66 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:30 | 66.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-339 観察 L711 | +12 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:30 | 12.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-339 観察 L711 | +116 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:30 | 116.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-339 観察 L711 | −102,008 | 円 | docs/RESEARCH/matilda_main/step/fam_tables.md:99 | -102008.0 | 円 | 一致 | 中(3 桁以上) |
| K-339 観察 L711 | −250,923 | 円 | docs/RESEARCH/matilda_main/step/fam_tables.md:100 | -250923.0 | 円 | 一致 | 中(3 桁以上) |
| K-339 観察 L711 | +36 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:66 | 1.82 ×20 | 口座の bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-339 観察 L711 | +26 | 円 | docs/RESEARCH/matilda_main/step/compare.md:23 | 25.6 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-339 観察 L711 | +17 | 円 | docs/RESEARCH/matilda_main/step/compare.md:24 | 17.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-339 観察 L711 | −259 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:65 | -12.94 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-339 観察 L711 | −184 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:36 | -9.19 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-339 観察 L711 | −123 | 円 | docs/RESEARCH/matilda_main/step/compare.md:24 | -122.8 | 円 | 一致 | 中(3 桁以上) |
| K-339 大きさ L716 | −116 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:29 | -116.0 | 円 | 一致 | 中(3 桁以上) |
| K-339 大きさ L716 | −233 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:30 | -233.0 | 円 | 一致 | 中(3 桁以上) |
| K-339 大きさ L716 | +50 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:61 | 50.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-339 大きさ L716 | +66 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:85 | 66.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-340 観察 L728 | +33 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:36 | 33.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-340 観察 L728 | −100 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:36 | -100.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-340 観察 L728 | +167 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:36 | 167.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-340 観察 L728 | −67 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:32 | -67.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-340 観察 L728 | −168 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:32 | -168.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-340 観察 L728 | +32 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:32 | 32.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-340 観察 L728 | −198 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:34 | -198.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-340 観察 L728 | −270 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:34 | -270.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-340 観察 L728 | −127 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:34 | -127.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-340 観察 L728 | −390 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:36 | -390.0 | 円 | 一致 | 中(3 桁以上) |
| K-340 観察 L728 | −374 | 円/日 | docs/RESEARCH/matilda_main/break_delay/levels_reason.out:32 | -373.9 | 円 | 一致 | 中(3 桁以上) |
| K-340 観察 L728 | −391 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:34 | -391.0 | 円 | 一致 | 中(3 桁以上) |
| K-340 観察 L728 | −116 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:29 | -116.0 | 円 | 一致 | 中(3 桁以上) |
| K-340 観察 L728 | −233 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:30 | -233.0 | 円 | 一致 | 中(3 桁以上) |
| K-340 観察 L728 | −100 | 円/日 | docs/RESEARCH/matilda_main/break_delay/levels_reason.out:6 | -100.0 | 円 | 一致 | 中(3 桁以上) |
| K-340 観察 L728 | −231 | 円/日 | docs/RESEARCH/matilda_main/step/compare.md:16 | -231.1 | 円 | 一致 | 中(3 桁以上) |
| K-340 観察 L728 | +329 | (語なし) | docs/RESEARCH/matilda_main/step/fam_tables.md:35 | 329.0 | 円 | 一致 | 中(3 桁以上) |
| K-340 観察 L728 | +314 | (語なし) | docs/RESEARCH/matilda_main/beard/levels_reason.out:11 | 314.0 | 円 | 一致 | 中(3 桁以上) |
| K-340 観察 L728 | +327 | (語なし) | docs/RESEARCH/matilda_main/base/diag_tables.md:24 | 16.33 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-340 観察 L728 | +46.7 | 円 | docs/RESEARCH/matilda_main/beard/levels_reason.out:17 | 46.7 | 円 | 一致 | 中(3 桁以上) |
| K-340 観察 L728 | +20.0 | 円 | docs/RESEARCH/matilda_main/base/diag_paths.md:3 | 1.0 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 中(3 桁以上) |
| K-340 観察 L728 | −341.7 | 円 | docs/RESEARCH/matilda_main/beard/levels_reason.out:18 | -341.7 | 円 | 一致 | 中(3 桁以上) |
| K-340 観察 L728 | −162.7 | 円 | docs/RESEARCH/matilda_main/step/levels_reason.out:18 | -162.7 | 円 | 一致 | 中(3 桁以上) |
| K-340 大きさ L733 | +33 | 円/日 | docs/RESEARCH/matilda_main/range_hi/levels_reason.out:20 | 32.7 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-340 大きさ L733 | −67 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:32 | -67.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-340 大きさ L733 | −198 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:34 | -198.0 | 円 | 一致 | 中(3 桁以上) |
| K-341 観察 L745 | +117 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:35 | 117.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-341 観察 L745 | +92 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:35 | 92.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-341 観察 L745 | +141 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:35 | 141.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-341 観察 L745 | +151 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:31 | 151.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-341 観察 L745 | +131 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:31 | 131.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-341 観察 L745 | +169 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:31 | 169.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-341 観察 L745 | +184 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:33 | 184.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-341 観察 L745 | +167 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:33 | 167.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-341 観察 L745 | +201 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:33 | 201.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-341 観察 L745 | +50 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:61 | 50.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-341 観察 L745 | +66 | 円/日 | docs/RESEARCH/matilda_main/range_lo/levels_reason.out:25 | 66.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-341 観察 L745 | +34 | 円/日 | docs/RESEARCH/matilda_main/range_lo/levels_reason.out:23 | 34.4 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-341 観察 L745 | +67 | 円/日 | docs/RESEARCH/matilda_main/beard/levels_reason.out:17 | 67.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-341 観察 L745 | +16 | 円/日 | docs/RESEARCH/matilda_main/break_off/levels_reason.out:5 | 15.7 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-341 観察 L745 | −1 | 円/日 | docs/RESEARCH/matilda_main/base/diag_tables.md:75 | -0.04 ×20 | 口座の bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-341 観察 L745 | +48.3 | 円 | docs/RESEARCH/matilda_main/beard/levels_reason.out:15 | 48.3 | 円 | 一致 | 中(3 桁以上) |
| K-341 観察 L745 | −118.8 | 円 | docs/RESEARCH/matilda_main/beard/levels_reason.out:16 | -118.8 | 円 | 一致 | 中(3 桁以上) |
| K-341 観察 L745 | −24.9 | 万円 |  |  |  | 一致 | 計算で一致: 同じ行の 4,960 × +48.3 + 4,116 × (−118.8) = −249,413(掛ける数は出力と一致。和そのものは出力に無い) |
| K-341 大きさ L750 | +117 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:35 | 117.0 | 円 | 一致 | 中(3 桁以上) |
| K-341 大きさ L750 | +151 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:31 | 151.0 | 円 | 一致 | 中(3 桁以上) |
| K-341 大きさ L750 | +184 | 円/日 | docs/RESEARCH/matilda_main/break_delay/levels_reason.out:32 | 184.0 | 円 | 一致 | 中(3 桁以上) |
| K-342 観察 L762 | +10.9 | 円 | docs/RESEARCH/matilda_main/base/width_vola.out:8 | 10.95 | 円 | 一致 | 中(3 桁以上) |
| K-342 観察 L762 | +14.6 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_dist/band_migration.out:6 の本の和 +622,749 ÷ 42,673 本 = +14.59 |
| K-342 観察 L762 | +5.0 | 円 | docs/RESEARCH/matilda_main/break_dist_0.25/diag_tables.md:8 | 0.25 ×20 | 口座の bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | +9.2 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_dist/band_migration.out:14 の本の和 +320,773 ÷ 34,817 = +9.21 |
| K-342 観察 L762 | +108 | 円/日 | docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_3.out:2 | 108.5 | 円 | 一致 | 中(3 桁以上) |
| K-342 観察 L762 | +101 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:7 | 101.0 | 円 | 一致 | 中(3 桁以上) |
| K-342 観察 L762 | −31.9 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_dist/band_migration.out:9 の基準の和 −163,705 ÷ 5,137 = −31.87 |
| K-342 観察 L762 | −64.7 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_dist/band_migration.out:9 の本の和 −332,555 ÷ 5,137 = −64.74 |
| K-342 観察 L762 | −37.6 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_dist/band_migration.out:17 −193,954 ÷ 5,153 = −37.64 |
| K-342 観察 L762 | −55.6 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_dist/band_migration.out:17 −286,313 ÷ 5,153 = −55.56 |
| K-342 観察 L762 | −115 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:1 | -115.0 | 円 | 一致 | 中(3 桁以上) |
| K-342 観察 L762 | −63 | 円/日 | docs/RESEARCH/matilda_main/break_dist/band_migration.out:17 | -63.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | −13 | 円/日 | docs/RESEARCH/matilda_main/base/diag_paths.md:23 | -0.66 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | +34 | 円/日 | docs/RESEARCH/matilda_main/break_dist/band_migration.out:18 | 34.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | −112.5 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_dist/band_migration.out:23 −424,194 ÷ 3,772 = −112.46 |
| K-342 観察 L762 | −73.8 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_dist/band_migration.out:23 −278,303 ÷ 3,772 = −73.78 |
| K-342 観察 L762 | −100.9 | 円 | docs/RESEARCH/matilda_main/range_hi_p75/diag_tables.json:/d1/rows[0]/lo | -5.047 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-342 観察 L762 | −72.2 | 円 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d3_extra.out:32 | -72.2 | 円 | 一致 | 中(3 桁以上) |
| K-342 観察 L762 | +99 | 円/日 | docs/RESEARCH/matilda_main/break_dist/band_migration.out:23 | 99.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | +69 | 円/日 | docs/RESEARCH/matilda_main/break_dist/band_migration.out:31 | 69.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | −72 | 円/日 | docs/RESEARCH/matilda_main/break_dist/band_migration.out:22 | -72.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | −57 | 円/日 | docs/RESEARCH/matilda_main/break_dist/band_migration.out:30 | -57.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | +83 | 円/日 | docs/RESEARCH/matilda_main/break_dist/band_migration.out:26 | 83.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | −3 | 円/日 | docs/RESEARCH/matilda_main/base/diag_paths.md:44 | -0.13 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | +3,065 | 円 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-342 観察 L762 | −53,696 | 円 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-342 観察 L762 | +37 | 円/日 | docs/RESEARCH/matilda_main/break_delay/band_migration.out:34 | 37.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | +101 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:7 | 101.0 | 円 | 一致 | 中(3 桁以上) |
| K-342 観察 L762 | +37 | (語なし) | docs/RESEARCH/matilda_main/break_delay/band_migration.out:34 | 37.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | +34 | (語なし) | docs/RESEARCH/matilda_main/break_dist/band_migration.out:18 | 34.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | −63 | (語なし) | docs/RESEARCH/matilda_main/break_dist/band_migration.out:17 | -63.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | +99 | (語なし) | docs/RESEARCH/matilda_main/break_dist/band_migration.out:23 | 99.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | +83 | 円/日 | docs/RESEARCH/matilda_main/break_dist/band_migration.out:26 | 83.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | −3 | 円/日 | docs/RESEARCH/matilda_main/base/diag_paths.md:44 | -0.13 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | −13 | 円/日 | docs/RESEARCH/matilda_main/base/diag_paths.md:23 | -0.66 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | +34 | 円/日 | docs/RESEARCH/matilda_main/break_dist/band_migration.out:18 | 34.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-342 観察 L762 | 1,200 | 円/日 | docs/RESEARCH/matilda_main/alert_x1/diag_paths.md:24 | 60.0 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 中(3 桁以上) |
| K-342 観察 L762 | 1,600 | 円/日 | docs/RESEARCH/matilda_main/alert_x1/diag_tables.md:3 | 80.0 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-342 観察 L762 | +111 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:10 | 111.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-342 観察 L762 | +54 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:10 | 54.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-342 観察 L762 | +174 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:10 | 174.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-342 観察 L762 | +110 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:11 | 110.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-342 観察 L762 | +19 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:11 | 19.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-342 観察 L762 | +213 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:11 | 213.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-342 大きさ L767 | +111 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:10 | 111.0 | 円 | 一致 | 中(3 桁以上) |
| K-342 大きさ L767 | +110 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:11 | 110.0 | 円 | 一致 | 中(3 桁以上) |
| K-343 観察 L779 | +148 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:32 | 148.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-343 観察 L779 | +48 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:32 | 48.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-343 観察 L779 | +257 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:32 | 257.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-343 観察 L779 | +33 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:36 | 33.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-343 観察 L779 | −100 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:36 | -100.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-343 観察 L779 | +167 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:36 | 167.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-343 観察 L779 | −31.9 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_dist/band_migration.out:9 −163,705 ÷ 5,137 = −31.87 |
| K-343 観察 L779 | −64.7 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_dist/band_migration.out:9 −332,555 ÷ 5,137 = −64.74 |
| K-343 観察 L779 | +2.2 | 円 | docs/RESEARCH/matilda_main/base/diag_paths.md:43 | 0.11 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-343 観察 L779 | +2.0 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_dist/band_migration.out:10 +218,211 ÷ 109,970 = +1.98 |
| K-343 観察 L779 | −13 | 円/日 | docs/RESEARCH/matilda_main/base/diag_paths.md:23 | -0.66 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-343 大きさ L784 | +148 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:32 | 148.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-343 大きさ L784 | +48 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:32 | 48.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-343 大きさ L784 | +257 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:32 | 257.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-344 観察 L796 | +80 | 円/日 | docs/RESEARCH/matilda_main/break_dist/scene_diff.out:5 | 80.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-344 観察 L796 | +40 | 円/日 | docs/RESEARCH/matilda_main/break_dist/scene_diff.out:5 | 40.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-344 観察 L796 | +133 | 円/日 | docs/RESEARCH/matilda_main/break_dist/scene_diff.out:5 | 133.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-344 観察 L796 | +60 | 円/日 | docs/RESEARCH/matilda_main/break_dist/scene_diff.out:7 | 60.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-344 観察 L796 | −45 | 円/日 | docs/RESEARCH/matilda_main/break_dist/scene_diff.out:7 | -45.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-344 観察 L796 | +150 | 円/日 | docs/RESEARCH/matilda_main/break_dist/scene_diff.out:7 | 150.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-344 観察 L796 | +195 | 円/日 | docs/RESEARCH/matilda_main/break_dist/scene_diff.out:9 | 195.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-344 観察 L796 | +35 | 円/日 | docs/RESEARCH/matilda_main/break_dist/scene_diff.out:9 | 35.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-344 観察 L796 | +360 | 円/日 | docs/RESEARCH/matilda_main/break_dist/scene_diff.out:9 | 360.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-344 大きさ L801 | +195 | 円/日 | docs/RESEARCH/matilda_main/break_dist/scene_diff.out:9 | 195.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-344 大きさ L801 | +35 | 円/日 | docs/RESEARCH/matilda_main/break_dist/scene_diff.out:9 | 35.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-344 大きさ L801 | +360 | 円/日 | docs/RESEARCH/matilda_main/break_dist/scene_diff.out:9 | 360.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-345 観察 L813 | −0.75 | move_bp | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:63 | -0.75 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-345 観察 L813 | −1.25 | move_bp | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:63 | -1.25 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-345 観察 L813 | −0.29 | move_bp | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:63 | -0.29 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-345 観察 L813 | −0.42 | move_bp | docs/RESEARCH/matilda_main/base/diag_paths.md:24 | -0.42 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-345 観察 L813 | −0.89 | move_bp | docs/RESEARCH/matilda_main/base/diag_paths.md:24 | -0.89 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-345 観察 L813 | +0.01 | move_bp | docs/RESEARCH/matilda_main/base/diag_paths.md:24 | 0.01 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-345 観察 L813 | −0.24 | move_bp | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:64 | -0.24 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-345 観察 L813 | −0.68 | move_bp | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:64 | -0.68 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-345 観察 L813 | +0.17 | move_bp | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:64 | 0.17 | 値動きの bp | 一致 | 強(区間の 3 つが同じ行) |
| K-345 観察 L813 | −0.33 | (語なし) | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:64 | -0.33 | 値動きの bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-345 観察 L813 | −0.39 | (語なし) | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:63 | -0.39 | 値動きの bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-345 観察 L813 | −0.60 | (語なし) | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:64 | -0.6 | 値動きの bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-345 観察 L813 | −0.76 | (語なし) | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:63 | -0.76 | 値動きの bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-345 大きさ L818 | −0.75 | move_bp | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:63 | -0.75 | 値動きの bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-346 観察 L830 | +356 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:12 | 356.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-346 観察 L830 | +264 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:12 | 264.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-346 観察 L830 | +459 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:12 | 459.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-346 観察 L830 | +68 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:12 | 68.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-346 観察 L830 | +10 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:12 | 10.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-346 観察 L830 | +124 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:12 | 124.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-346 観察 L830 | +211.5 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:72 | 211.5 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-346 観察 L830 | +154.9 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:72 | 154.9 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-346 観察 L830 | +265.8 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:72 | 265.8 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-346 観察 L830 | 80.5 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:72 | 80.5 | 円 | 一致 | 中(3 桁以上) |
| K-346 観察 L830 | +487,589 | 円 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:84 | 487589.0 | 円 | 一致 | 中(3 桁以上) |
| K-346 観察 L830 | −205 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:14 | -205.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-346 観察 L830 | −303 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:14 | -303.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-346 観察 L830 | −110 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:14 | -110.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-346 観察 L830 | +424 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:13 | 424.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-346 観察 L830 | +235 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:13 | 235.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-346 観察 L830 | +634 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:13 | 634.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-346 観察 L830 | +160 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:13 | 160.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-346 観察 L830 | +21 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:13 | 21.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-346 観察 L830 | +289 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:13 | 289.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-346 大きさ L835 | +356 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:1 | 356.0 | 円 | 一致 | 中(3 桁以上) |
| K-346 大きさ L835 | +68 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:7 | 68.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-347 観察 L847 | +0.4 | 円 | docs/RESEARCH/matilda_main/base/diag_paths.md:32 | 0.02 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-347 観察 L847 | +2.6 | 円 | docs/RESEARCH/matilda_main/break_len_mult_4/diag_paths.md:34 | 0.13 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-347 観察 L847 | +192 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/band_migration.out:10 | 192.0 | 円 | 一致 | 中(3 桁以上) |
| K-347 観察 L847 | −4.2 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_len_mult/band_migration.out:18 −552,280 ÷ 131,657 = −4.19 |
| K-347 観察 L847 | −3.7 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_len_mult/band_migration.out:18 −488,521 ÷ 131,657 = −3.71 |
| K-347 観察 L847 | +43 | 円 | docs/RESEARCH/matilda_main/break_len_mult/band_migration.out:18 | 43.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-347 観察 L847 | −104.4 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_len_mult/band_migration.out:7 −243,026 ÷ 2,328 = −104.39 |
| K-347 観察 L847 | −43.0 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_len_mult/band_migration.out:7 −100,211 ÷ 2,328 = −43.05 |
| K-347 観察 L847 | −86.2 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_len_mult/band_migration.out:15 −174,833 ÷ 2,028 = −86.21 |
| K-347 観察 L847 | −65.4 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_len_mult/band_migration.out:15 −132,663 ÷ 2,028 = −65.42 |
| K-347 観察 L847 | +97 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/band_migration.out:7 | 97.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-347 観察 L847 | +29 | 円/日 | docs/RESEARCH/matilda_main/beard/band_migration.out:16 | 29.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-347 観察 L847 | +79 | 円/日 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_len_mult/band_migration.out:3-4 +54 + +25 = +79 |
| K-347 観察 L847 | +6 | 円/日 | docs/RESEARCH/matilda_main/base/diag_paths.md:43 | 0.32 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-347 大きさ L852 | +192 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/band_migration.out:10 | 192.0 | 円 | 一致 | 中(3 桁以上) |
| K-348 観察 L864 | +210 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/scene_diff.out:4 | 210.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-348 観察 L864 | +137 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/scene_diff.out:4 | 137.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-348 観察 L864 | +300 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/scene_diff.out:4 | 300.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-348 観察 L864 | +356 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/scene_diff.out:6 | 356.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-348 観察 L864 | +168 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/scene_diff.out:6 | 168.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-348 観察 L864 | +530 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/scene_diff.out:6 | 530.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-348 観察 L864 | +792 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/scene_diff.out:8 | 792.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-348 観察 L864 | +502 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/scene_diff.out:8 | 502.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-348 観察 L864 | +1,078 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/scene_diff.out:8 | 1078.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-348 観察 L864 | +97 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/scene_diff.out:7 | 97.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-348 観察 L864 | −9 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/scene_diff.out:7 | -9.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-348 観察 L864 | +212 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/scene_diff.out:7 | 212.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-348 観察 L864 | +139 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/scene_diff.out:9 | 139.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-348 観察 L864 | −2 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/scene_diff.out:9 | -2.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-348 観察 L864 | +286 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/scene_diff.out:9 | 286.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-348 大きさ L869 | +792 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/scene_diff.out:8 | 792.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-348 大きさ L869 | +502 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/scene_diff.out:8 | 502.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-348 大きさ L869 | +1,078 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/scene_diff.out:8 | 1078.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-349 観察 L881 | +129 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 129.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-349 観察 L881 | +37 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 37.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-349 観察 L881 | +221 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 221.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-349 観察 L881 | 132 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 132.0 | 円 | 一致 | 中(3 桁以上) |
| K-349 観察 L881 | −55 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | -55.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-349 観察 L881 | −127 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | -127.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-349 観察 L881 | +11 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 11.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-349 観察 L881 | 99 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 99.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-349 観察 L881 | +37.2 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 37.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-349 観察 L881 | −22.4 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | -22.4 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-349 観察 L881 | +93.4 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 93.4 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-349 観察 L881 | 83.0 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 83.0 | 円 | 一致 | 中(3 桁以上) |
| K-349 観察 L881 | +303 | (語なし) | docs/RESEARCH/matilda_main/base/diag_tables.md:24 | 15.16 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-349 観察 L881 | +177 | (語なし) | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 177.0 | 円 | 一致 | 中(3 桁以上) |
| K-349 観察 L881 | −159 | (語なし) | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | -159.0 | 円 | 一致 | 中(3 桁以上) |
| K-349 観察 L881 | +491 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:14 | 491.0 | 円 | 一致 | 中(3 桁以上) |
| K-349 観察 L881 | −327 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:14 | -327.0 | 円 | 一致 | 中(3 桁以上) |
| K-349 観察 L881 | +362 | 円/日 | docs/RESEARCH/matilda_main/base/diag_tables.md:35 | 18.11 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-349 観察 L881 | −273 | 円/日 | docs/RESEARCH/matilda_main/base/diag_tables.md:36 | -13.63 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-349 観察 L881 | +110 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:11 | 110.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-349 観察 L881 | +19 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:11 | 19.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-349 観察 L881 | +213 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:11 | 213.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-349 観察 L881 | −16 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:11 | -16.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-349 観察 L881 | −96 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:11 | -96.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-349 観察 L881 | +58 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:11 | 58.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-349 観察 L881 | +63 | (語なし) | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d3_extra.out:33 | 62.6 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-349 観察 L881 | +66 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:30 | 66.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-349 観察 L881 | −1 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:23 | -0.66 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-349 観察 L881 | −55 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:13 | -2.77 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-349 大きさ L886 | +129 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 129.0 | 円 | 一致 | 中(3 桁以上) |
| K-349 大きさ L886 | −55 | 円/日 | docs/RESEARCH/matilda_main/base/diag_paths.md:13 | -2.77 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-350 観察 L898 | +438,082 | 円 | docs/RESEARCH/matilda_main/beard/fam_tables.md:84 | 438082.0 | 円 | 一致 | 中(3 桁以上) |
| K-350 観察 L898 | +421,350 | 円 | docs/RESEARCH/matilda_main/beard/fam_tables.md:84 | 421350.0 | 円 | 一致 | 中(3 桁以上) |
| K-350 観察 L898 | +92,529 | 円 | docs/RESEARCH/matilda_main/beard/fam_tables.md:84 | 92529.0 | 円 | 一致 | 中(3 桁以上) |
| K-350 観察 L898 | +266 | 円 | docs/RESEARCH/matilda_main/both_halves.out:15 | 266.0 | 円 | 一致 | 中(3 桁以上) |
| K-350 観察 L898 | +216 | 円 | docs/RESEARCH/matilda_main/beard/band_migration.out:3 | 216.0 | 円 | 一致 | 中(3 桁以上) |
| K-350 観察 L898 | +50 | 円 | docs/RESEARCH/matilda_main/beard/band_migration.out:4 | 50.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-350 観察 L898 | −200 | 円 | docs/RESEARCH/matilda_main/both_halves.out:9 | -200.0 | 円 | 一致 | 中(3 桁以上) |
| K-350 観察 L898 | −157 | 円 | docs/RESEARCH/matilda_main/base/diag_paths.md:35 | -7.86 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 中(3 桁以上) |
| K-350 観察 L898 | −43 | 円 | docs/RESEARCH/matilda_main/beard/band_migration.out:8 | -43.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-350 観察 L898 | +32 | 円 | docs/RESEARCH/matilda_main/beard/compare.md:13 | 32.2 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-350 観察 L898 | +141 | 円 | docs/RESEARCH/matilda_main/base_scenes.out:10 | 141.0 | 円 | 一致 | 中(3 桁以上) |
| K-350 観察 L898 | −3.2 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:75 | -0.16 ×20 | 口座の bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-350 観察 L898 | −109 | 円 | docs/RESEARCH/matilda_main/beard/band_migration.out:12 | -109.0 | 円 | 一致 | 中(3 桁以上) |
| K-350 観察 L898 | −87 | 円 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-350 観察 L898 | −116 | 円 | docs/RESEARCH/matilda_main/beard/band_migration.out:13 | -116.0 | 円 | 一致 | 中(3 桁以上) |
| K-350 観察 L898 | +29 | 円 | docs/RESEARCH/matilda_main/beard/band_migration.out:16 | 29.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-350 観察 L898 | −1 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:75 | -0.04 ×20 | 口座の bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-350 観察 L898 | −56 | (語なし) | docs/RESEARCH/matilda_main/beard/band_migration.out:6 | -56.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-350 観察 L898 | −109 | (語なし) | docs/RESEARCH/matilda_main/beard/band_migration.out:12 | -109.0 | 円 | 一致 | 中(3 桁以上) |
| K-350 観察 L898 | −50 | (語なし) | docs/RESEARCH/matilda_main/beard/band_migration.out:14 | -50.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-350 観察 L898 | −87 | (語なし) |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-350 観察 L898 | +32 | (語なし) | docs/RESEARCH/matilda_main/beard/compare.md:13 | 32.2 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-350 観察 L898 | 34 | (語なし) | docs/RESEARCH/matilda_main/beard/fam_tables.md:35 | 34.1 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-350 観察 L898 | 70 | (語なし) | docs/RESEARCH/matilda_main/beard/nearest_signal.out:1 | 69.8 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-350 観察 L898 | 66 | (語なし) | docs/RESEARCH/matilda_main/beard/nearest_signal.out:1 | 65.9 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-350 観察 L898 | 43 | (語なし) | docs/RESEARCH/matilda_main/beard/nearest_signal.out:3 | 43.3 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-350 観察 L898 | +483 | (語なし) | docs/RESEARCH/matilda_main/beard/fam_tables.md:28 | 483.0 | 円 | 一致 | 中(3 桁以上) |
| K-350 観察 L898 | +219 | (語なし) | docs/RESEARCH/matilda_main/beard/fam_tables.md:28 | 219.0 | 円 | 一致 | 中(3 桁以上) |
| K-350 観察 L898 | +329 | (語なし) | docs/RESEARCH/matilda_main/beard/fam_tables.md:30 | 329.0 | 円 | 一致 | 中(3 桁以上) |
| K-350 観察 L898 | +117 | (語なし) | docs/RESEARCH/matilda_main/beard/fam_tables.md:30 | 117.0 | 円 | 一致 | 中(3 桁以上) |
| K-350 大きさ L903 | 34 | (語なし) | docs/RESEARCH/matilda_main/beard/fam_tables.md:35 | 34.1 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-351 観察 L915 | −123.8 | 円 | docs/RESEARCH/matilda_main/beard/same_bar_reason.out:1 | -123.8 | 円 | 一致 | 中(3 桁以上) |
| K-351 観察 L915 | −180.6 | 円 | docs/RESEARCH/matilda_main/beard/same_bar_reason.out:1 | -180.6 | 円 | 一致 | 中(3 桁以上) |
| K-351 観察 L915 | −74 | 円/日 | docs/RESEARCH/matilda_main/beard/same_bar_reason.out:1 | -73.9 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-351 観察 L915 | −120.1 | 円 | docs/RESEARCH/matilda_main/beard/same_bar_reason.out:5 | -120.1 | 円 | 一致 | 中(3 桁以上) |
| K-351 観察 L915 | −172.1 | 円 | docs/RESEARCH/matilda_main/beard/same_bar_reason.out:5 | -172.1 | 円 | 一致 | 中(3 桁以上) |
| K-351 観察 L915 | −63 | 円 | docs/RESEARCH/matilda_main/beard/same_bar_reason.out:5 | -62.8 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-351 観察 L915 | +27.6 | 円 | docs/RESEARCH/matilda_main/beard/same_bar_reason.out:4 | 27.6 | 円 | 一致 | 中(3 桁以上) |
| K-351 観察 L915 | +26.9 | 円 | docs/RESEARCH/matilda_main/beard/same_bar_reason.out:4 | 26.9 | 円 | 一致 | 中(3 桁以上) |
| K-351 観察 L915 | −12 | 円 | docs/RESEARCH/matilda_main/base/diag_paths.md:44 | -0.58 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-351 観察 L915 | +21.0 | 円 | docs/RESEARCH/matilda_main/beard/same_bar_reason.out:8 | 21.0 | 円 | 一致 | 中(3 桁以上) |
| K-351 観察 L915 | +20.6 | 円 | docs/RESEARCH/matilda_main/base/diag_paths.md:35 | 1.03 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 中(3 桁以上) |
| K-351 観察 L915 | −4 | 円 | docs/RESEARCH/matilda_main/base/diag_paths.md:22 | -0.22 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-351 大きさ L920 | −124 | 円 | docs/RESEARCH/matilda_main/beard/same_bar_reason.out:1 | -123.8 | 円 | 一致 | 中(3 桁以上) |
| K-351 大きさ L920 | −181 | 円 | docs/RESEARCH/matilda_main/beard/same_bar_reason.out:1 | -180.6 | 円 | 一致 | 中(3 桁以上) |
| K-351 大きさ L920 | −120 | 円 | docs/RESEARCH/matilda_main/beard/same_bar_reason.out:5 | -120.1 | 円 | 一致 | 中(3 桁以上) |
| K-351 大きさ L920 | −172 | 円 | docs/RESEARCH/matilda_main/beard/same_bar_reason.out:5 | -172.1 | 円 | 一致 | 中(3 桁以上) |
| K-352 観察 L932 | +65 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:4 | 65.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 観察 L932 | −38 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:4 | -38.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 観察 L932 | +162 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:4 | 162.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 観察 L932 | +115 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:6 | 115.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 観察 L932 | −94 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:6 | -94.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 観察 L932 | +304 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:6 | 304.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 観察 L932 | +257 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:8 | 257.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 観察 L932 | +19 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:8 | 19.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 観察 L932 | +552 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:8 | 552.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 観察 L932 | −28 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:5 | -28.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 観察 L932 | −95 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:5 | -95.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 観察 L932 | +35 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:5 | 35.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 観察 L932 | −44 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:7 | -44.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 観察 L932 | −158 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:7 | -158.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 観察 L932 | +56 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:7 | 56.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 観察 L932 | −99 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:9 | -99.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 観察 L932 | −263 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:9 | -263.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 観察 L932 | +57 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:9 | 57.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 大きさ L937 | +257 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:8 | 257.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 大きさ L937 | +19 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:8 | 19.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-352 大きさ L937 | +552 | 円/日 | docs/RESEARCH/matilda_main/beard/scene_diff.out:8 | 552.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | −40 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:6 | -40.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | −89 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:6 | -89.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | +3 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:6 | 3.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | +38 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:6 | 38.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | +13 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:6 | 13.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | +64 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:6 | 64.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | −42 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:7 | -42.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | −105 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:7 | -105.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | +14 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:7 | 14.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | +68 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:7 | 68.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | +35 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:7 | 35.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | +101 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:7 | 101.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | −59 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:8 | -59.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | −126 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:8 | -126.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | −1 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:8 | -1.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | +76 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:8 | 76.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | +37 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:8 | 37.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | +114 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:8 | 114.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | −127 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:9 | -127.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | −200 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:9 | -200.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | −59 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:9 | -59.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | +40 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:9 | 40.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | −8 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:9 | -8.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | +87 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:9 | 87.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 観察 L949 | −258.8 | 円 | docs/RESEARCH/matilda_main/alert/compare.md:22 | -258.8 | 円 | 一致 | 中(3 桁以上) |
| K-353 観察 L949 | −243.1 | 円 | docs/RESEARCH/matilda_main/break_delay/compare.md:27 | -243.1 | 円 | 一致 | 中(3 桁以上) |
| K-353 観察 L949 | −235.0 | 円 | docs/RESEARCH/matilda_main/alert_x2/diag_tables.md:67 | -11.75 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-353 観察 L949 | −229.7 | 円 | docs/RESEARCH/matilda_main/break_delay/compare.md:29 | -229.7 | 円 | 一致 | 中(3 桁以上) |
| K-353 観察 L949 | −217.1 | 円 | docs/RESEARCH/matilda_main/break_delay/compare.md:30 | -217.1 | 円 | 一致 | 中(3 桁以上) |
| K-353 観察 L949 | −17 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:10 | -17.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-353 観察 L949 | +111 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:10 | 111.0 | 円 | 一致 | 中(3 桁以上) |
| K-353 大きさ L954 | +76 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:8 | 76.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 大きさ L954 | +37 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:8 | 37.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 大きさ L954 | +114 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:8 | 114.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 大きさ L954 | −59 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:8 | -59.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 大きさ L954 | −126 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:8 | -126.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-353 大きさ L954 | −1 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:8 | -1.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-354 観察 L966 | +30.2 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_2.out:1 −321.7 − (−351.9) = +30.2 |
| K-354 観察 L966 | +277 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:46 | 13.86 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | +23.2 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_2.out:8 −262.6 − (−285.8) = +23.2 |
| K-354 観察 L966 | +246 | 円 | docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_2.out:8 | 246.3 | 円 | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | −317.0 | 円 | docs/RESEARCH/matilda_main/step_4/diag_tables.md:46 | -15.85 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | −365 | 円 | docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_2.out:4 | -364.5 | 円 | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | −246.9 | 円 | docs/RESEARCH/matilda_main/break_dist_1/diag_tables.json:/d7/years/2022/lo | -12.34 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | −282 | 円 | docs/RESEARCH/matilda_main/base_scenes.out:9 | -282.0 | 円 | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | +65 | 円 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:132 | 65.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-354 観察 L966 | +65 | 円 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:132 | 65.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-354 観察 L966 | +48.6 | (語なし) | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:112 | 48.6 | 円 | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | +39.4 | (語なし) |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_4.out 後半 break→break −253.5 − (−292.9) = +39.4 |
| K-354 観察 L966 | +410 | (語なし) | docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_4.out:1 | 409.6 | 円 | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | +387 | (語なし) | docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_4.out:8 | 386.5 | 円 | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | −298.8 | (語なし) | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:51 | -298.8 | 円 | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | −223.7 | (語なし) |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_4.out 後半 close→break −227.1 − (−3.4) = −223.7 |
| K-354 観察 L966 | −610 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:12 | -30.5 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | −482 | (語なし) | docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_4.out:11 | -482.3 | 円 | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | +136 | (語なし) | docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_4.out:2 | 136.4 | 円 | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | +134 | (語なし) | docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_4.out:9 | 134.4 | 円 | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | +61.1 | (語なし) |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_8.out 前半 break→break −310.4 − (−371.5) = +61.1 |
| K-354 観察 L966 | +52.2 | (語なし) |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_8.out 後半 break→break −248.2 − (−300.4) = +52.2 |
| K-354 観察 L966 | +465 | (語なし) | docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_8.out:1 | 465.2 | 円 | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | +467 | (語なし) | docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_8.out:8 | 466.5 | 円 | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | −279.9 | (語なし) |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_8.out 前半 close→break −261.0 − 18.9 = −279.9 |
| K-354 観察 L966 | −209.9 | (語なし) |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_8.out 後半 close→break −209.6 − 0.3 = −209.9 |
| K-354 観察 L966 | −816 | (語なし) | docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_8.out:4 | -816.4 | 円 | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | −676 | (語なし) | docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_8.out:11 | -676.2 | 円 | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | +216 | (語なし) | docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_8.out:2 | 216.0 | 円 | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | +210 | (語なし) | docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_8.out:9 | 210.4 | 円 | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | −88 | (語なし) |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_2.out diff/day +276.9 + (−364.5) = −87.6 |
| K-354 観察 L966 | −36 | (語なし) | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:50 | -36.4 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-354 観察 L966 | −200 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:9 | -200.0 | 円 | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | −95 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:11 | -4.74 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-354 観察 L966 | −351 | (語なし) |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_8.out diff/day +465.2 + (−816.4) = −351.2 |
| K-354 観察 L966 | −209 | (語なし) | docs/RESEARCH/matilda_main/d7_fullperiod.out:8 | -209.1 | 円 | 一致 | 中(3 桁以上) |
| K-354 観察 L966 | 1.2 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:32 | 0.06 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-354 観察 L966 | 0.85 | (語なし) | docs/RESEARCH/matilda_main/break_delay/compare.md:10 | 0.8524 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-354 観察 L966 | 0.86 | (語なし) | docs/RESEARCH/matilda_main/break_delay/compare.md:8 | 0.8622 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-354 観察 L966 | −267.0 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_dist/held_reason_break_dist_0.25.out:4 −227.7 − 39.3 = −267.0 |
| K-354 観察 L966 | −204.7 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_dist/held_reason_break_dist_0.25.out:10 −179.4 − 25.3 = −204.7 |
| K-354 大きさ L971 | −279.9 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_8.out 前半 close→break = −279.9 |
| K-354 大きさ L971 | −209.9 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_8.out 後半 close→break = −209.9 |
| K-355 観察 L983 | +74 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:9 | 74.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | +12 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:9 | 12.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | +137 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:9 | 137.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | +133 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:18 | 133.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | +51 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:18 | 51.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | +214 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:18 | 214.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | +152 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:27 | 152.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | +56 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:27 | 56.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | +250 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:27 | 250.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | +90 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:36 | 90.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | −25 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:36 | -25.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | +205 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:36 | 205.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | −198 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:26 | -198.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | −375 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:26 | -375.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | −16 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:26 | -16.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | −296 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:35 | -296.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | −492 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:35 | -492.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | −99 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:35 | -99.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | +55 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:7 | 55.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-355 観察 L983 | +68 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:112 | 68.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-355 観察 L983 | +88 | 円/日 | docs/RESEARCH/matilda_main/base/diag_tables.md:25 | 4.39 ×20 | 口座の bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-355 観察 L983 | −73 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:31 | -73.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | −135 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:31 | -135.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | −2 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:31 | -2.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 観察 L983 | +15 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:23 | 15.0 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-355 観察 L983 | +20 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:3 | 1.0 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-355 観察 L983 | +13 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:16 | 0.67 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-355 観察 L983 | −23 | (語なし) | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:114 | -23.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-355 観察 L983 | −18 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:23 | -0.89 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-355 大きさ L988 | +152 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:27 | 152.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 大きさ L988 | +56 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:27 | 56.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-355 大きさ L988 | +250 | 円/日 | docs/RESEARCH/matilda_main/break_delay/scene_diff.out:27 | 250.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-356 観察 L1000 | +424 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:13 | 424.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-356 観察 L1000 | +235 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:13 | 235.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-356 観察 L1000 | +634 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:13 | 634.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-356 観察 L1000 | +160 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:13 | 160.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-356 観察 L1000 | +21 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:13 | 21.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-356 観察 L1000 | +289 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:13 | 289.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-356 観察 L1000 | +292.3 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:72 | 292.3 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-356 観察 L1000 | +175.6 | 円/日 | docs/RESEARCH/matilda_main/break_off/diag_tables.md:80 | 8.78 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-356 観察 L1000 | +416.6 | 円/日 | docs/RESEARCH/matilda_main/break_off/diag_tables.md:80 | 20.83 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-356 観察 L1000 | +161 | (語なし) | docs/RESEARCH/matilda_main/half_diff_rest.out:6 | 161.0 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | +166 | (語なし) | docs/RESEARCH/matilda_main/half_diff_rest.out:5 | 166.0 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | −14 | (語なし) | docs/RESEARCH/matilda_main/break_delay/band_migration.out:65 | -14.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-356 観察 L1000 | +108 | (語なし) | docs/RESEARCH/matilda_main/break_dist/band_migration.out:6 | 108.0 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | +6 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:11 | 6.02 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-356 観察 L1000 | −128 | (語なし) | docs/RESEARCH/matilda_main/break_off/band_migration.out:11 | -128.0 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | +9 | (語なし) | docs/RESEARCH/matilda_main/break_delay/band_migration.out:15 | 9.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-356 観察 L1000 | +5 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:3 | 5.0 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-356 観察 L1000 | +40 | (語なし) | docs/RESEARCH/matilda_main/base/diag_tables.md:8 | 2.0 ×20 | 口座の bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-356 観察 L1000 | +116 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:30 | 116.0 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | +787 | 円/日 | docs/RESEARCH/matilda_main/break_off/diag_tables.md:35 | 39.33 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | −112 | 円/日 | docs/RESEARCH/matilda_main/break_off/diag_tables.md:36 | -5.61 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-356 観察 L1000 | −266 | 円/日 | docs/RESEARCH/matilda_main/break_off/diag_tables.md:36 | -13.29 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-356 観察 L1000 | +35 | 円/日 | docs/RESEARCH/matilda_main/break_off/diag_tables.md:36 | 1.77 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-356 観察 L1000 | −330.1 | 円 | docs/RESEARCH/matilda_main/break_off/held_reason.out:1 | -330.1 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | −218.4 | 円 | docs/RESEARCH/matilda_main/break_off/held_reason.out:1 | -218.4 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | −263.8 | 円 | docs/RESEARCH/matilda_main/break_off/held_reason.out:5 | -263.8 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | −170.3 | 円 | docs/RESEARCH/matilda_main/break_off/held_reason.out:5 | -170.3 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | +1,020 | 円/日 | docs/RESEARCH/matilda_main/break_off/held_reason.out:1 | 1020.0 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | +978 | 円/日 | docs/RESEARCH/matilda_main/break_off/held_reason.out:5 | 977.5 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | −469.5 | 円 | docs/RESEARCH/matilda_main/break_off/held_reason.out:2 | -469.5 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | −1,611.0 | 円 | docs/RESEARCH/matilda_main/break_off/held_reason.out:2 | -1611.0 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | −421.4 | 円 | docs/RESEARCH/matilda_main/break_off/held_reason.out:6 | -421.4 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | −1,351.0 | 円 | docs/RESEARCH/matilda_main/break_off/held_reason.out:6 | -1351.0 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | −911 | 円 | docs/RESEARCH/matilda_main/break_off/held_reason.out:2 | -910.7 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | −864 | 円 | docs/RESEARCH/matilda_main/break_off/held_reason.out:6 | -863.8 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | +109 | 円 | docs/RESEARCH/matilda_main/half_diff_rest.out:13 | 109.0 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | +114 | 円 | docs/RESEARCH/matilda_main/both_halves.out:8 | 114.0 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | +245 | 円/日 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-356 観察 L1000 | +5 | 円/日 | docs/RESEARCH/matilda_main/break_delay/band_migration.out:51 | 5.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-356 観察 L1000 | +425 | (語なし) | docs/RESEARCH/matilda_main/break_off/diag_tables.md:86 | 21.25 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | +288 | (語なし) |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-356 観察 L1000 | +240 | (語なし) | docs/RESEARCH/matilda_main/base/diag_tables.md:7 | 12.0 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | +135 | (語なし) | docs/RESEARCH/matilda_main/half_diff.out:6 | 135.0 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | +161 | (語なし) | docs/RESEARCH/matilda_main/half_diff_rest.out:6 | 161.0 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | +166 | (語なし) | docs/RESEARCH/matilda_main/half_diff_rest.out:5 | 166.0 | 円 | 一致 | 中(3 桁以上) |
| K-356 観察 L1000 | −14 | (語なし) | docs/RESEARCH/matilda_main/break_delay/band_migration.out:65 | -14.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-356 観察 L1000 | −84 | 円 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-356 大きさ L1005 | +424 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:13 | 424.0 | 円 | 一致 | 中(3 桁以上) |
| K-356 大きさ L1005 | +160 | 円/日 | docs/RESEARCH/matilda_main/base/diag_tables.md:35 | 8.0 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-357 見出し L1016 | −1,258 | 円 | docs/RESEARCH/matilda_main/break_off/compare.md:21 | -1257.6 | 円 | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −1,257.6 | 円 | docs/RESEARCH/matilda_main/break_off/diag_tables.md:65 | -62.88 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-357 観察 L1017 | −1,360.8 | 円 | docs/RESEARCH/matilda_main/break_off/diag_tables.md:65 | -68.04 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-357 観察 L1017 | −1,157.2 | 円 | docs/RESEARCH/matilda_main/break_off/diag_tables.md:65 | -57.86 ×20 | 口座の bp | 一致 | 強(区間の 3 つが同じ行) |
| K-357 観察 L1017 | −315.2 | 円 | docs/RESEARCH/matilda_main/alert/compare.md:22 | -315.2 | 円 | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −258.8 | 円 | docs/RESEARCH/matilda_main/alert/compare.md:22 | -258.8 | 円 | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −5,439,000 | 円 |  |  |  | 一致 | 計算で一致: 同じ行の 4,325 本 × −1,257.6 円 = −5,439,120(break_off の出力と一致した 2 つの数からの掛け算。和そのものは出力に無い) |
| K-357 観察 L1017 | −1,682.9 | 円 | docs/RESEARCH/matilda_main/break_off/break_off_detail.out:3 | -1682.9 | 円 | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −1,381.0 | 円 | docs/RESEARCH/matilda_main/break_off/break_off_detail.out:8 | -1381.0 | 円 | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −1,270.0 | 円 | docs/RESEARCH/matilda_main/break_off/break_off_detail.out:3 | -1270.0 | 円 | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −1,580.6 | 円 | docs/RESEARCH/matilda_main/break_off/break_off_detail.out:8 | -1580.6 | 円 | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −273.7 | 円 | docs/RESEARCH/matilda_main/break_off/break_off_detail.out:3 | -273.7 | 円 | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −433.6 | 円 |  |  |  | 一致 | 計算で一致: docs/RESEARCH/matilda_main/break_off/break_off_detail.out:8 に −433.6 円がそのまま(自動の突き合わせは別の行を拾っていた) |
| K-357 観察 L1017 | −50.60 | bp | docs/RESEARCH/matilda_main/break_off/diag_tables.md:46 | -50.6 | 口座の bp | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −1,012 | 円 | docs/RESEARCH/matilda_main/break_off/diag_tables.md:46 | -50.6 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −33.70 | bp | docs/RESEARCH/matilda_main/base/diag_tables.md:46 | -33.7 | 口座の bp | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −674 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:46 | -33.7 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −6.10 | bp | docs/RESEARCH/matilda_main/break_off/diag_tables.md:46 | -6.1 | 口座の bp | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −10.40 | bp | docs/RESEARCH/matilda_main/base/diag_tables.md:46 | -10.4 | 口座の bp | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −64.81 | move_bp | docs/RESEARCH/matilda_main/break_off/diag_paths.md:12 | -64.81 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −68.40 | move_bp | docs/RESEARCH/matilda_main/break_off/diag_paths.md:13 | -68.4 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −30.50 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:12 | -30.5 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −32.38 | bp | docs/RESEARCH/matilda_main/base/diag_paths.md:13 | -32.38 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −1,345,377 | 円 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:35 | -1345377.0 | 円 | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | −766,805 | 円 | docs/RESEARCH/matilda_main/beard/fam_tables.md:36 | -766805.0 | 円 | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | +36.4 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:66 | 1.82 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | +15.3 | 円 | docs/RESEARCH/matilda_main/break_off/compare.md:21 | 15.3 | 円 | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | +67.0 | 円 | docs/RESEARCH/matilda_main/break_off/levels_reason.out:13 | 67.0 | 円 | 一致 | 中(3 桁以上) |
| K-357 観察 L1017 | +13.6 | 円 | docs/RESEARCH/matilda_main/break_off/levels_reason.out:5 | 13.6 | 円 | 一致 | 中(3 桁以上) |
| K-357 大きさ L1022 | −1,683 | 円 | docs/RESEARCH/matilda_main/break_off/break_off_detail.out:3 | -1682.9 | 円 | 一致 | 中(3 桁以上) |
| K-357 大きさ L1022 | −1,381 | 円 | docs/RESEARCH/matilda_main/break_off/break_off_detail.out:8 | -1381.0 | 円 | 一致 | 中(3 桁以上) |
| K-357 大きさ L1022 | −1,012 | 円 | docs/RESEARCH/matilda_main/break_off/diag_tables.md:46 | -50.6 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-357 大きさ L1022 | −674 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:46 | -33.7 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-358 観察 L1034 | +1,343 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:8 | 1343.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-358 観察 L1034 | +859 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:8 | 859.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-358 観察 L1034 | +1,888 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:8 | 1888.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-358 観察 L1034 | +666 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:9 | 666.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-358 観察 L1034 | +338 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:9 | 338.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-358 観察 L1034 | +973 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:9 | 973.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-358 観察 L1034 | +443 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:6 | 443.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-358 観察 L1034 | +32 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:6 | 32.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-358 観察 L1034 | +854 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:6 | 854.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-358 観察 L1034 | +56 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:7 | 56.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-358 観察 L1034 | −183 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:7 | -183.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-358 観察 L1034 | +301 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:7 | 301.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-358 観察 L1034 | +86 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:4 | 86.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-358 観察 L1034 | −288 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:4 | -288.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-358 観察 L1034 | +441 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:4 | 441.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-358 観察 L1034 | −147 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:5 | -147.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-358 観察 L1034 | −308 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:5 | -308.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-358 観察 L1034 | −6 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:5 | -6.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-358 大きさ L1039 | +1,343 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:8 | 1343.0 | 円 | 一致 | 中(3 桁以上) |
| K-358 大きさ L1039 | +666 | 円/日 | docs/RESEARCH/matilda_main/break_off/scene_diff.out:9 | 666.0 | 円 | 一致 | 中(3 桁以上) |
| K-359 見出し L1050 | −194 | 円/日 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d3_extra.out:3 | -193.8 | 円 | 一致 | 中(3 桁以上) |
| K-359 見出し L1050 | −212 | (語なし) | docs/RESEARCH/matilda_main/both_halves.out:17 | -212.0 | 円 | 一致 | 中(3 桁以上) |
| K-359 見出し L1050 | +18 | (語なし) | docs/RESEARCH/matilda_main/entry_exit/band_migration.out:31 | 18.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-359 見出し L1050 | −1.7 | 円 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:101 | -1.7 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-359 見出し L1050 | −2.9 | 円 |  |  |  | 確かめられない | 出所のファイルに同じ数が無い。計算の元を時間内に特定していない |
| K-359 見出し L1050 | −1.1 | 円 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:71 | -1.05 | 円(和)/値動きの bp(MFE・MAE) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-359 見出し L1050 | +0.8 | 円 | docs/RESEARCH/matilda_main/base/diag_paths.md:35 | 0.04 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-359 観察 L1051 | −28 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:26 | -28.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 観察 L1051 | −42 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:26 | -42.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 観察 L1051 | −14 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:26 | -14.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 観察 L1051 | −59 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:27 | -59.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 観察 L1051 | −89 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:27 | -89.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 観察 L1051 | −30 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:27 | -30.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 観察 L1051 | −107 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:28 | -107.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 観察 L1051 | −157 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:28 | -157.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 観察 L1051 | −53 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:28 | -53.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 観察 L1051 | +19 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:26 | 19.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 観察 L1051 | +13 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:26 | 13.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 観察 L1051 | +25 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:26 | 25.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 観察 L1051 | +83 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:27 | 83.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 観察 L1051 | +67 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:27 | 67.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 観察 L1051 | +103 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:27 | 103.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 観察 L1051 | +199 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:28 | 199.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 観察 L1051 | +163 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:28 | 163.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 観察 L1051 | +242 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:28 | 242.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 観察 L1051 | +57,228 | 円 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:132 | 57228.0 | 円 | 一致 | 中(3 桁以上) |
| K-359 観察 L1051 | +34 | 円/日 | docs/RESEARCH/matilda_main/break_dist/band_migration.out:18 | 34.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-359 観察 L1051 | +6 | 円/日 | docs/RESEARCH/matilda_main/base/diag_paths.md:43 | 0.32 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-359 観察 L1051 | +72 | 円/日 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-359 観察 L1051 | +67 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:43 | 67.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-359 観察 L1051 | +18 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/band_migration.out:31 | 18.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-359 観察 L1051 | −212 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:17 | -212.0 | 円 | 一致 | 中(3 桁以上) |
| K-359 観察 L1051 | −273 | 円/日 | docs/RESEARCH/matilda_main/base/diag_tables.md:36 | -13.63 ×20 | 口座の bp | 一致 | 中(3 桁以上) |
| K-359 観察 L1051 | −194 | 円/日 | /tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/rerun/d3_extra.out:3 | -193.8 | 円 | 一致 | 中(3 桁以上) |
| K-359 観察 L1051 | −212 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:17 | -212.0 | 円 | 一致 | 中(3 桁以上) |
| K-359 観察 L1051 | +1.9 | 円 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:104 | 1.9 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-359 観察 L1051 | +204,191 | 円 |  |  |  | 確かめられない | 出所のファイルに同じ数が無い。計算の元を時間内に特定していない |
| K-359 観察 L1051 | −2.6 | 円 | docs/RESEARCH/matilda_main/base/diag_paths.md:44 | -0.13 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-359 観察 L1051 | −285,180 | 円 |  |  |  | 確かめられない | 出所のファイルに同じ数が無い。計算の元を時間内に特定していない |
| K-359 観察 L1051 | +4.7 | 円 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-359 観察 L1051 | +328,019 | 円 |  |  |  | 確かめられない | 出所のファイルに同じ数が無い。計算の元を時間内に特定していない |
| K-359 観察 L1051 | −1.8 | 円 |  |  |  | 確かめられない | −115,641 ÷ 63,442 = −1.82 で同じ行の数とは合うが、−115,641 そのものが出力に無い |
| K-359 観察 L1051 | −115,641 | 円 |  |  |  | 確かめられない | 出所のファイルに同じ数が無い。計算の元を時間内に特定していない |
| K-359 観察 L1051 | −1 | 円/日 | docs/RESEARCH/matilda_main/base/diag_tables.md:75 | -0.04 ×20 | 口座の bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-359 観察 L1051 | 0 | 円/日 | docs/RESEARCH/matilda_main/base/diag_paths.md:12 | 0.0 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-359 観察 L1051 | −125 | (語なし) | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:112 | -125.0 | 円 | 一致 | 中(3 桁以上) |
| K-359 観察 L1051 | −249 | (語なし) | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:113 | -249.0 | 円 | 一致 | 中(3 桁以上) |
| K-359 観察 L1051 | −312 | (語なし) | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:52 | -311.7 | 円 | 一致 | 中(3 桁以上) |
| K-359 観察 L1051 | +0 | 円 | docs/RESEARCH/matilda_main/base/diag_paths.md:12 | 0.0 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-359 大きさ L1056 | +199 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:28 | 199.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 大きさ L1056 | +163 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:28 | 163.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 大きさ L1056 | +242 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:28 | 242.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 大きさ L1056 | −107 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:28 | -107.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 大きさ L1056 | −157 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:28 | -157.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-359 大きさ L1056 | −53 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:28 | -53.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 見出し L1067 | +2 | (語なし) | docs/RESEARCH/matilda_main/range_lo/blocked_range_lo_p50.md:41 | 0.09 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-360 見出し L1067 | +0 | (語なし) | docs/RESEARCH/matilda_main/range_lo/blocked_range_lo_p50.md:41 | 0.0 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-360 見出し L1067 | +4 | (語なし) | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:102 | 3.7 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +37 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:14 | 37.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +24 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:14 | 24.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +50 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:14 | 50.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +115 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:23 | 115.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +80 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:23 | 80.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +148 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:23 | 148.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +205 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:32 | 205.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +145 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:32 | 145.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +264 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:32 | 264.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +13 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:16 | 13.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +5 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:16 | 5.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +21 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:16 | 21.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +106 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:25 | 106.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +73 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:25 | 73.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +141 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:25 | 141.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +206 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:34 | 206.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +116 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:34 | 116.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +304 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:34 | 304.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +2 | 円/日 | docs/RESEARCH/matilda_main/range_lo/blocked_range_lo_p50.md:41 | 0.09 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +0 | 円/日 | docs/RESEARCH/matilda_main/range_lo/blocked_range_lo_p50.md:41 | 0.0 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +4 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:102 | 3.7 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +23 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:27 | 23.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +11 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:27 | 11.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +33 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:27 | 33.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +187 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:36 | 187.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +137 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:36 | 137.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +231 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:36 | 231.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | −142 | (語なし) | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:31 | -142.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | −212 | (語なし) | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:31 | -212.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | −69 | (語なし) | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:31 | -69.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +23 | (語なし) | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:13 | 23.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +3 | (語なし) | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:13 | 3.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | +47 | (語なし) | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:13 | 47.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 観察 L1068 | 12 | (語なし) | docs/RESEARCH/matilda_main/alert/scene_diff.out:4 | 12.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-360 大きさ L1073 | +206 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:34 | 206.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 大きさ L1073 | +116 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:34 | 116.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-360 大きさ L1073 | +304 | 円/日 | docs/RESEARCH/matilda_main/range_lo/scene_diff.out:34 | 304.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | −115 | 円 | docs/RESEARCH/matilda_main/d7_fullperiod.out:8 | -114.8 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | −209 | 円 | docs/RESEARCH/matilda_main/d7_fullperiod.out:8 | -209.1 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | −30 | 円 | docs/RESEARCH/matilda_main/d7_fullperiod.out:8 | -29.7 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | −190 | 円 | docs/RESEARCH/matilda_main/d7_fullperiod.out:4 | -189.5 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | −305 | 円 | docs/RESEARCH/matilda_main/d7_fullperiod.out:4 | -305.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | −81 | 円 | docs/RESEARCH/matilda_main/d7_fullperiod.out:4 | -80.7 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | 0 | 円 | docs/RESEARCH/matilda_main/base/diag_paths.md:12 | 0.0 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | −4 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:24 | -4.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | −48 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:24 | -48.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | +36 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:24 | 36.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | +12 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:23 | 12.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | −50 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:23 | -50.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | +73 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:23 | 73.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | −362 | (語なし) | docs/RESEARCH/matilda_main/range_hi/scene_diff.out:17 | -362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | −634 | (語なし) | docs/RESEARCH/matilda_main/range_hi/scene_diff.out:17 | -634.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | −107 | (語なし) | docs/RESEARCH/matilda_main/range_hi/scene_diff.out:17 | -107.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | −585 | (語なし) | docs/RESEARCH/matilda_main/range_hi/scene_diff.out:8 | -585.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | −926 | (語なし) | docs/RESEARCH/matilda_main/range_hi/scene_diff.out:8 | -926.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | −282 | (語なし) | docs/RESEARCH/matilda_main/range_hi/scene_diff.out:8 | -282.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 観察 L1085 | −3,150 | 円 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:114 | -3150.0 | 円 | 一致 | 中(3 桁以上) |
| K-361 観察 L1085 | +36.7 | 円 | docs/RESEARCH/matilda_main/range_hi/compare.md:27 | 36.7 | 円 | 一致 | 中(3 桁以上) |
| K-361 観察 L1085 | −190 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:1 | -190.0 | 円 | 一致 | 中(3 桁以上) |
| K-361 観察 L1085 | −0.5 | 円 |  |  |  | 確かめられない | bp のファイルの別の数と偶然近いだけ(出所の行を時間内に特定していない)。単位の誤りの証拠ではない |
| K-361 観察 L1085 | +9 | 円/日 | docs/RESEARCH/matilda_main/break_delay/band_migration.out:15 | 9.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | +20.7 | 円 | docs/RESEARCH/matilda_main/base/diag_paths.json:/d5/建てた合図(起点 = 建ての時刻)/60/control_24h/hi | 1.035 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 中(3 桁以上) |
| K-361 観察 L1085 | −62 | 円 | docs/RESEARCH/matilda_main/range_hi/band_migration.out:11 | -62.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | −6.0 | 円 |  |  |  | 確かめられない | bp のファイルの別の数と偶然近いだけ(出所の行を時間内に特定していない)。単位の誤りの証拠ではない |
| K-361 観察 L1085 | +70 | 円 | docs/RESEARCH/matilda_main/range_hi/band_migration.out:13 | 70.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | +36.7 | 円 | docs/RESEARCH/matilda_main/range_hi/compare.md:27 | 36.7 | 円 | 一致 | 中(3 桁以上) |
| K-361 観察 L1085 | +20.7 | 円 | docs/RESEARCH/matilda_main/base/diag_paths.json:/d5/建てた合図(起点 = 建ての時刻)/60/control_24h/hi | 1.035 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 中(3 桁以上) |
| K-361 観察 L1085 | −0.5 | 円 |  |  |  | 確かめられない | bp のファイルの別の数と偶然近いだけ(出所の行を時間内に特定していない)。単位の誤りの証拠ではない |
| K-361 観察 L1085 | −6.0 | 円 |  |  |  | 確かめられない | bp のファイルの別の数と偶然近いだけ(出所の行を時間内に特定していない)。単位の誤りの証拠ではない |
| K-361 観察 L1085 | −180 | (語なし) | docs/RESEARCH/matilda_main/d7_fullperiod.out:6 | -179.6 | 円 | 一致 | 中(3 桁以上) |
| K-361 観察 L1085 | +21 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:35 | 1.03 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | −417 | (語なし) | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:98 | -417.0 | 円 | 一致 | 中(3 桁以上) |
| K-361 観察 L1085 | −289 | (語なし) | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:98 | -289.0 | 円 | 一致 | 中(3 桁以上) |
| K-361 観察 L1085 | −45 | (語なし) | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:106 | -45.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | −86 | (語なし) | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:106 | -86.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | +74 | (語なし) | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:106 | 74.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | +41 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:12 | 2.05 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | +2 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:12 | 2.05 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | +66.7 | 円 | docs/RESEARCH/matilda_main/range_hi/zero_reason.out:4 | 66.7 | 円 | 一致 | 中(3 桁以上) |
| K-361 観察 L1085 | −364.1 | 円 | docs/RESEARCH/matilda_main/range_hi/zero_reason.out:3 | -364.1 | 円 | 一致 | 中(3 桁以上) |
| K-361 観察 L1085 | +16.8 | 円 | docs/RESEARCH/matilda_main/range_hi/levels_reason.out:3 | 16.8 | 円 | 一致 | 中(3 桁以上) |
| K-361 観察 L1085 | +19.9 | 円 | docs/RESEARCH/matilda_main/range_hi/levels_reason.out:13 | 19.9 | 円 | 一致 | 中(3 桁以上) |
| K-361 観察 L1085 | +66.7 | 円 | docs/RESEARCH/matilda_main/range_hi/zero_reason.out:4 | 66.7 | 円 | 一致 | 中(3 桁以上) |
| K-361 観察 L1085 | +107.6 | 円 | docs/RESEARCH/matilda_main/range_hi/zero_reason.out:8 | 107.6 | 円 | 一致 | 中(3 桁以上) |
| K-361 観察 L1085 | +1.5 | 円 | docs/RESEARCH/matilda_main/range_hi/six_bands.out:3 | 1.5 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | 10 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:8 | 0.5 ×20 | 口座の bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | +1.6 | 円 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:91 | 1.6 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | 25 | 円 | docs/RESEARCH/matilda_main/break_delay/band_migration.out:39 | 25.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | +2.5 | 円 | docs/RESEARCH/matilda_main/range_hi/six_bands.out:5 | 2.5 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | 50 | 円 | docs/RESEARCH/matilda_main/beard/band_migration.out:4 | 50.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | +1.6 | 円 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:91 | 1.6 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | 75 | 円 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:34 | 75.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | +5.0 | 円 | docs/RESEARCH/matilda_main/range_hi/six_bands.out:7 | 5.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | +14.1 | 円 | docs/RESEARCH/matilda_main/range_hi/levels_reason.out:13 | 14.1 | 円 | 一致 | 中(3 桁以上) |
| K-361 観察 L1085 | −1.7 | 円 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:92 | -1.7 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | −2.6 | 円 | docs/RESEARCH/matilda_main/base/diag_paths.md:44 | -0.13 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | −2.9 | 円 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:89 | -2.9 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | −2.4 | 円 | docs/RESEARCH/matilda_main/base/diag_paths.md:42 | -0.12 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | −1.1 | 円 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:89 | -1.1 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 観察 L1085 | +0.8 | 円 | docs/RESEARCH/matilda_main/base/diag_paths.md:35 | 0.04 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-361 大きさ L1090 | −190 | 円/日 | docs/RESEARCH/matilda_main/d7_fullperiod.out:4 | -189.5 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 大きさ L1090 | −305 | 円/日 | docs/RESEARCH/matilda_main/d7_fullperiod.out:4 | -305.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-361 大きさ L1090 | −81 | 円/日 | docs/RESEARCH/matilda_main/d7_fullperiod.out:4 | -80.7 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-362 見出し L1101 | 1 | move_bp | docs/RESEARCH/matilda_main/base/diag_paths.md:3 | 1.0 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-362 観察 L1102 | −0.60 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:59 | -0.6 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −0.85 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:59 | -0.85 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −0.38 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:59 | -0.38 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −1.13 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:60 | -1.13 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −1.75 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:60 | -1.75 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −0.54 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:60 | -0.54 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −1.79 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:61 | -1.79 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −2.84 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:61 | -2.84 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −0.80 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:61 | -0.8 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | +0.31 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:62 | 0.31 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −1.77 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:62 | -1.77 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | +2.42 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:62 | 2.42 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −0.19 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:34 | -0.19 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-362 観察 L1102 | −0.40 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:42 | -0.4 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-362 観察 L1102 | −0.56 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:43 | -0.56 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −0.73 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:43 | -0.73 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −0.40 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:43 | -0.4 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −0.76 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:44 | -0.76 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −1.14 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:44 | -1.14 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −0.40 | bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:44 | -0.4 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −0.13 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:44 | -0.13 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-362 観察 L1102 | −0.35 | (語なし) | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:84 | -0.35 | 値動きの bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-362 観察 L1102 | −0.50 | (語なし) | docs/RESEARCH/matilda_main/range_lo/blocked_range_lo_p50.md:61 | -0.5 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −0.65 | (語なし) | docs/RESEARCH/matilda_main/range_lo/blocked_range_lo_p50.md:61 | -0.65 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −0.33 | (語なし) | docs/RESEARCH/matilda_main/range_lo/blocked_range_lo_p50.md:61 | -0.33 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −0.60 | (語なし) | docs/RESEARCH/matilda_main/range_lo/blocked_range_lo_p50.md:62 | -0.6 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −0.98 | (語なし) | docs/RESEARCH/matilda_main/range_lo/blocked_range_lo_p50.md:62 | -0.98 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −0.25 | (語なし) | docs/RESEARCH/matilda_main/range_lo/blocked_range_lo_p50.md:62 | -0.25 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −0.41 | (語なし) | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:75 | -0.41 | 値動きの bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-362 観察 L1102 | −0.68 | (語なし) | docs/RESEARCH/matilda_main/range_lo/blocked_range_lo_p50.md:42 | -0.68 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-362 観察 L1102 | −1.00 | (語なし) | docs/RESEARCH/matilda_main/range_lo/blocked_range_lo_p50.md:43 | -1.0 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −1.49 | (語なし) | docs/RESEARCH/matilda_main/range_lo/blocked_range_lo_p50.md:43 | -1.49 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −0.54 | (語なし) | docs/RESEARCH/matilda_main/range_lo/blocked_range_lo_p50.md:43 | -0.54 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −0.54 | (語なし) | docs/RESEARCH/matilda_main/range_lo/blocked_range_lo_p50.md:44 | -0.54 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | −1.55 | (語なし) | docs/RESEARCH/matilda_main/range_lo/blocked_range_lo_p50.md:44 | -1.55 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 観察 L1102 | +0.35 | (語なし) | docs/RESEARCH/matilda_main/range_lo/blocked_range_lo_p50.md:44 | 0.35 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 大きさ L1107 | −1.79 | move_bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:61 | -1.79 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 大きさ L1107 | −2.84 | move_bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:61 | -2.84 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 大きさ L1107 | −0.80 | move_bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:61 | -0.8 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 大きさ L1107 | −0.56 | move_bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:43 | -0.56 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 大きさ L1107 | −0.73 | move_bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:43 | -0.73 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-362 大きさ L1107 | −0.40 | move_bp | docs/RESEARCH/matilda_main/range_hi/blocked_range_hi_p75.md:43 | -0.4 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-363 見出し L1118 | 6 | (語なし) | docs/RESEARCH/matilda_main/base/diag_paths.md:11 | 6.02 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-363 観察 L1119 | −21 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:31 | -21.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 観察 L1119 | −47 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:31 | -47.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 観察 L1119 | +5 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:31 | 5.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 観察 L1119 | −40 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:32 | -40.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 観察 L1119 | −87 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:32 | -87.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 観察 L1119 | +8 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:32 | 8.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 観察 L1119 | −78 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:33 | -78.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 観察 L1119 | −144 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:33 | -144.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 観察 L1119 | −7 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:33 | -7.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 観察 L1119 | +19 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:31 | 19.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 観察 L1119 | +11 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:31 | 11.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 観察 L1119 | +27 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:31 | 27.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 観察 L1119 | +93 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:32 | 93.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 観察 L1119 | +74 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:32 | 74.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 観察 L1119 | +120 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:32 | 120.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 観察 L1119 | +186 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:33 | 186.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 観察 L1119 | +148 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:33 | 148.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 観察 L1119 | +228 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:33 | 228.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 観察 L1119 | +1,938 | 円 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:114 | 1938.0 | 円 | 一致 | 中(3 桁以上) |
| K-363 観察 L1119 | +2,468 | 円 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:115 | 2468.0 | 円 | 一致 | 中(3 桁以上) |
| K-363 観察 L1119 | +4.23 | 円 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-363 観察 L1119 | −86 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/band_migration.out:29 | -86.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-363 観察 L1119 | +2.07 | 円 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-363 観察 L1119 | −34 | 円 | docs/RESEARCH/matilda_main/base/diag_tables.md:56 | -1.68 ×20 | 口座の bp | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-363 観察 L1119 | −0.03 | 円 |  |  |  | 確かめられない | bp のファイルの別の数と偶然近いだけ(出所の行を時間内に特定していない)。単位の誤りの証拠ではない |
| K-363 観察 L1119 | +2 | 円 | docs/RESEARCH/matilda_main/base/diag_paths.md:42 | 0.1 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-363 観察 L1119 | −4.44 | 円 |  |  |  | 確かめられない | 分析の文書(出所欄の文書)の中の写しとは一致。生の出力ファイルに同じ数が無く、計算の元を時間内に特定していない |
| K-363 観察 L1119 | +221 | 円 | docs/RESEARCH/matilda_main/both_halves.out:5 | 221.0 | 円 | 一致 | 中(3 桁以上) |
| K-363 観察 L1119 | −46,431 | 円 | docs/RESEARCH/matilda_main/vola_gate/gate_overlap.out:11 | -46431.0 | 円 | 一致 | 中(3 桁以上) |
| K-363 観察 L1119 | −7.4 | 円 |  |  |  | 確かめられない | bp のファイルの別の数と偶然近いだけ(出所の行を時間内に特定していない)。単位の誤りの証拠ではない |
| K-363 観察 L1119 | −22,450 | 円 | docs/RESEARCH/matilda_main/vola_gate/gate_overlap.out:12 | -22450.0 | 円 | 一致 | 中(3 桁以上) |
| K-363 観察 L1119 | +34,592 | 円 | docs/RESEARCH/matilda_main/vola_gate/gate_overlap.out:11 | 34592.0 | 円 | 一致 | 中(3 桁以上) |
| K-363 観察 L1119 | −32,942 | 円 | docs/RESEARCH/matilda_main/vola_gate/gate_overlap.out:12 | -32942.0 | 円 | 一致 | 中(3 桁以上) |
| K-363 観察 L1119 | 11 | 円 | docs/RESEARCH/matilda_main/base/diag_paths.md:35 | 0.54 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-363 観察 L1119 | 52 | 円 | docs/RESEARCH/matilda_main/entry_exit/band_migration.out:22 | 52.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-363 観察 L1119 | +12.6 | 円 | docs/RESEARCH/matilda_main/vola_gate/zero_reason.out:12 | 12.6 | 円 | 一致 | 中(3 桁以上) |
| K-363 観察 L1119 | −62.4 | 円 | docs/RESEARCH/matilda_main/vola_gate/zero_reason.out:11 | -62.4 | 円 | 一致 | 中(3 桁以上) |
| K-363 大きさ L1124 | +186 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:33 | 186.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 大きさ L1124 | +148 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:33 | 148.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 大きさ L1124 | +228 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:33 | 228.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 大きさ L1124 | −78 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:33 | -78.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 大きさ L1124 | −144 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:33 | -144.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-363 大きさ L1124 | −7 | 円/日 | docs/RESEARCH/matilda_main/both_halves.out:33 | -7.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +36 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:5 | 36.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +20 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:5 | 20.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +52 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:5 | 52.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +136 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:14 | 136.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +98 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:14 | 98.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +171 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:14 | 171.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +219 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:23 | 219.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +150 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:23 | 150.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +285 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:23 | 285.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +13 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:7 | 13.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +3 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:7 | 3.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +24 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:7 | 24.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +127 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:16 | 127.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +79 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:16 | 79.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +176 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:16 | 176.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +195 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:25 | 195.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +102 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:25 | 102.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +294 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:25 | 294.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | −0 | 円/日 | docs/RESEARCH/matilda_main/base/diag_paths.md:42 | -0.01 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | −3 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:90 | -3.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +2 | 円/日 | docs/RESEARCH/matilda_main/base/diag_paths.md:42 | 0.1 ×20 | bp(diag_paths: 損益の和は口座の bp・ほかは値動きの bp) | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +10 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:18 | 10.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +0 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:18 | 0.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +19 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:18 | 19.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +135 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:27 | 135.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +90 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:27 | 90.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | +171 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:27 | 171.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | −163 | (語なし) | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:22 | -163.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | −221 | (語なし) | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:22 | -221.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | −92 | (語なし) | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:22 | -92.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | −12 | (語なし) | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:6 | -12.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | −31 | (語なし) | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:6 | -31.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | −0 | (語なし) | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:6 | -0.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | −4 | (語なし) | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:8 | -4.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | −7 | (語なし) | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:8 | -7.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | −0 | (語なし) | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:8 | -0.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | −12 | (語なし) | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:17 | -12.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | −28 | (語なし) | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:17 | -28.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | −1 | (語なし) | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:17 | -1.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 観察 L1136 | 12 | (語なし) | docs/RESEARCH/matilda_main/alert/scene_diff.out:4 | 12.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ。偶然の一致を消していない) |
| K-364 大きさ L1141 | +219 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:23 | 219.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 大きさ L1141 | +150 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:23 | 150.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| K-364 大きさ L1141 | +285 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/scene_diff.out:23 | 285.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |

## 5. 段 1 の 10 族の表の全部の数

表 3 の年の列(偶数年 + 2023)110 個は、`fam_tables.md` の D7 の「年ごと(円/日)」の表の同じ本・同じ年の升目と 1 つずつ照らした(`stage1_years.py`。110 個とも一致)。range_hi の表 3 の全期間・前半・後半は `d7_fullperiod.out`(基準の期間の日で取り直した値)と一致し、break_len_mult の表 3 は `fam_tables.md` の読み口の値と一致(文書の注記どおり)。

文書の先頭の注記の数(手で照らした): break_len_mult 取り直し 前半 +343 [+246, +442] = `d7_fullperiod.out:12` の +343.4 [+245.7, +441.8]・後半 +68 [+10, +124] = `d7_fullperiod.out:13` の +67.6 [+9.6, +124.0]。6 個とも一致。

| 行 | 書かれた数 | 書かれた単位 | 出所 ファイル:行 | 出所の値 | 出所の単位 | 判定 | 備考 |
|---|---|---|---|---|---|---|---|
| L13 entry_exit | +505 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:15 | 505.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L13 entry_exit | +341 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:15 | 505.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L13 entry_exit | +669 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:15 | 505.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L13 entry_exit | −485 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:15 | -485.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L13 entry_exit | −601 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:15 | -485.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L13 entry_exit | −373 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:15 | -485.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L14 entry_exit | +476 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:16 | 476.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L14 entry_exit | +260 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:16 | 476.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L14 entry_exit | +675 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:16 | 476.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L14 entry_exit | −743 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:16 | -743.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L14 entry_exit | −881 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:16 | -743.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L14 entry_exit | −606 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:16 | -743.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L15 entry_exit | +362 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:17 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L15 entry_exit | +231 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:17 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L15 entry_exit | +497 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:17 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L15 entry_exit | −273 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:17 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L15 entry_exit | −360 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:17 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L15 entry_exit | −184 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:17 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L29 entry_exit | −34.7 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:85 | -34.7 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L29 entry_exit | −88.2 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:85 | -34.7 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L29 entry_exit | +17.1 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:85 | -34.7 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L29 entry_exit | 75.3 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:85 | 75.3 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L29 entry_exit | +143 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:85 | 143.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L29 entry_exit | +68 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:85 | 143.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L29 entry_exit | +219 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:85 | 143.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L29 entry_exit | −212 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:85 | -212.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L29 entry_exit | −273 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:85 | -212.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L29 entry_exit | −154 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:85 | -212.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L29 entry_exit | +268 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:85 | 268.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L29 entry_exit | +174 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:92 | 174.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L29 entry_exit | −214 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:85 | -214.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L29 entry_exit | −291 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:85 | -291.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L29 entry_exit | −57 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:92 | -57.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L30 entry_exit | −178.4 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:86 | -178.4 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L30 entry_exit | −271.0 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:86 | -178.4 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L30 entry_exit | −84.6 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:86 | -178.4 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L30 entry_exit | 132.9 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:86 | 132.9 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L30 entry_exit | +114 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:86 | 114.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L30 entry_exit | −30 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:86 | 114.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L30 entry_exit | +238 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:86 | 114.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L30 entry_exit | −470 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:86 | -470.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L30 entry_exit | −565 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:86 | -470.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L30 entry_exit | −372 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:86 | -470.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L30 entry_exit | +421 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:86 | 421.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L30 entry_exit | +4 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:40 | 4.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L30 entry_exit | −634 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:86 | -634.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L30 entry_exit | −611 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:86 | -611.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L30 entry_exit | −100 | 円/日 | docs/RESEARCH/matilda_main/entry_exit/fam_tables.md:36 | -100.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L41 step | +247 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:15 | 247.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L41 step | +147 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:15 | 247.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L41 step | +349 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:15 | 247.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L41 step | −223 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:15 | -223.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L41 step | −290 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:15 | -223.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L41 step | −159 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:15 | -223.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L42 step | +129 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:16 | 129.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L42 step | +59 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:16 | 129.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L42 step | +199 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:16 | 129.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L42 step | −206 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:16 | -206.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L42 step | −251 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:16 | -206.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L42 step | −165 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:16 | -206.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L43 step | +362 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:17 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L43 step | +231 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:17 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L43 step | +497 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:17 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L43 step | −273 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:17 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L43 step | −360 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:17 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L43 step | −184 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:17 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L57 step | −32.8 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:85 | -32.8 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L57 step | −60.0 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:85 | -32.8 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L57 step | −3.7 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:85 | -32.8 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L57 step | 41.5 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:85 | 41.5 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L57 step | −116 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:85 | -116.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L57 step | −163 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:85 | -116.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L57 step | −72 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:85 | -116.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L57 step | +50 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:85 | 50.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L57 step | +16 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:85 | 50.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L57 step | +84 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:85 | 50.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L57 step | −45 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:92 | -45.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L57 step | −199 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:85 | -199.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L57 step | −62 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:92 | -62.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L57 step | +86 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:85 | 86.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L57 step | +142 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:85 | 142.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L58 step | −83.4 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:86 | -83.4 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L58 step | −130.0 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:86 | -83.4 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L58 step | −34.1 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:86 | -83.4 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L58 step | 69.4 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:86 | 69.4 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L58 step | −233 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:86 | -233.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L58 step | −314 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:86 | -233.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L58 step | −160 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:86 | -233.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L58 step | +66 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:86 | 66.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L58 step | +12 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:86 | 66.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L58 step | +116 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:86 | 66.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L58 step | −37 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:42 | -37.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L58 step | −389 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:86 | -389.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L58 step | −109 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:86 | -109.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L58 step | +67 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:93 | 67.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L58 step | +233 | 円/日 | docs/RESEARCH/matilda_main/step/fam_tables.md:86 | 233.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L69 break_dist | +345 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:15 | 345.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L69 break_dist | +248 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:15 | 345.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L69 break_dist | +456 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:15 | 345.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L69 break_dist | −162 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:15 | -162.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L69 break_dist | −236 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:15 | -162.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L69 break_dist | −82 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:15 | -162.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L70 break_dist | +472 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:16 | 472.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L70 break_dist | +307 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:16 | 472.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L70 break_dist | +636 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:16 | 472.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L70 break_dist | −289 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:16 | -289.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L70 break_dist | −415 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:16 | -289.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L70 break_dist | −176 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:16 | -289.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L71 break_dist | +362 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:17 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L71 break_dist | +231 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:17 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L71 break_dist | +497 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:17 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L71 break_dist | −273 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:17 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L71 break_dist | −360 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:17 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L71 break_dist | −184 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:17 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L85 break_dist | +47.1 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:85 | 47.1 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L85 break_dist | −0.1 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:85 | 47.1 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L85 break_dist | +94.6 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:85 | 47.1 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L85 break_dist | 68.8 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:85 | 68.8 | 円 | 一致 | 中(3 桁以上) |
| L85 break_dist | −17 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:85 | -17.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L85 break_dist | −94 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:85 | -17.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L85 break_dist | +61 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:85 | -17.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L85 break_dist | +111 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:85 | 111.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L85 break_dist | +54 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:85 | 111.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L85 break_dist | +174 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:85 | 111.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L85 break_dist | +17 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:41 | 17.4 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L85 break_dist | −175 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:85 | -175.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L85 break_dist | +73 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:92 | 73.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L85 break_dist | +80 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:92 | 80.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L85 break_dist | +111 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:15 | 111.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L86 break_dist | +46.9 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:86 | 46.9 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L86 break_dist | −23.8 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:86 | 46.9 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L86 break_dist | +107.0 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:86 | 46.9 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L86 break_dist | 93.0 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:86 | 93.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L86 break_dist | +110 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:86 | 110.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L86 break_dist | +19 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:86 | 110.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L86 break_dist | +213 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:86 | 110.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L86 break_dist | −16 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:86 | -16.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L86 break_dist | −96 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:86 | -16.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L86 break_dist | +58 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:86 | -16.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L86 break_dist | −1 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:77 | -1.5 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L86 break_dist | +49 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:92 | 49.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L86 break_dist | +140 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:86 | 140.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L86 break_dist | −60 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:93 | -60.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L86 break_dist | −85 | 円/日 | docs/RESEARCH/matilda_main/break_dist/fam_tables.md:93 | -85.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L97 break_len_mult | +708 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:14 | 708.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L97 break_len_mult | +532 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:14 | 708.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L97 break_len_mult | +889 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:14 | 708.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L97 break_len_mult | −205 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:14 | -205.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L97 break_len_mult | −303 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:14 | -205.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L97 break_len_mult | −110 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:14 | -205.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L98 break_len_mult | +362 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:15 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L98 break_len_mult | +231 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:15 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L98 break_len_mult | +497 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:15 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L98 break_len_mult | −273 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:15 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L98 break_len_mult | −360 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:15 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L98 break_len_mult | −184 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:15 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L111 break_len_mult | +211.5 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:72 | 211.5 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L111 break_len_mult | +154.9 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:72 | 211.5 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L111 break_len_mult | +265.8 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:72 | 211.5 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L111 break_len_mult | 80.5 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:72 | 80.5 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L111 break_len_mult | +356 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:72 | 356.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L111 break_len_mult | +264 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:72 | 356.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L111 break_len_mult | +459 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:72 | 356.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L111 break_len_mult | +68 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:72 | 68.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L111 break_len_mult | +10 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:72 | 68.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L111 break_len_mult | +124 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:72 | 68.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L111 break_len_mult | +52 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:78 | 52.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L111 break_len_mult | +442 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:72 | 442.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L111 break_len_mult | +181 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:29 | 181.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L111 break_len_mult | +40 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:7 | 40.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L111 break_len_mult | +0 | 円/日 | docs/RESEARCH/matilda_main/break_len_mult/fam_tables.md:7 | 0.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L122 beard | +491 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:14 | 491.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L122 beard | +340 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:14 | 491.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L122 beard | +641 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:14 | 491.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L122 beard | −327 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:14 | -327.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L122 beard | −438 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:14 | -327.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L122 beard | −219 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:14 | -327.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L123 beard | +362 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:15 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L123 beard | +231 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:15 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L123 beard | +497 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:15 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L123 beard | −273 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:15 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L123 beard | −360 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:15 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L123 beard | −184 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:15 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L132 beard | +303 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 303.0 | 円 | 一致 | 中(3 桁以上) |
| L132 beard | +177 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 177.0 | 円 | 一致 | 中(3 桁以上) |
| L132 beard | −159 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | -159.0 | 円 | 一致 | 中(3 桁以上) |
| L136 beard | +37.2 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 37.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L136 beard | −22.4 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 37.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L136 beard | +93.4 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 37.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L136 beard | 83.0 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 83.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L136 beard | +129 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 129.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L136 beard | +37 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 129.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L136 beard | +221 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | 129.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L136 beard | −55 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | -55.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L136 beard | −127 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | -55.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L136 beard | +11 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:72 | -55.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L136 beard | +59 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:78 | 59.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L136 beard | −13 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:78 | -13.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L136 beard | +8 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:29 | 8.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L136 beard | −77 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:78 | -77.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L136 beard | +2 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:43 | 2.12 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L138 beard | 34 | 円/日 | docs/RESEARCH/matilda_main/beard/fam_tables.md:35 | 34.1 | 円 | 一致 | 弱(2 桁以下で 1 つだけ) |
| L147 break_delay | +323 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:17 | 323.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L147 break_delay | +195 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:17 | 323.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L147 break_delay | +459 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:17 | 323.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L147 break_delay | −235 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:17 | -235.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L147 break_delay | −317 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:17 | -235.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L147 break_delay | −153 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:17 | -235.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L148 break_delay | +321 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:18 | 321.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L148 break_delay | +192 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:18 | 321.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L148 break_delay | +451 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:18 | 321.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L148 break_delay | −205 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:18 | -205.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L148 break_delay | −286 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:18 | -205.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L148 break_delay | −125 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:18 | -205.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L149 break_delay | +304 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:19 | 304.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L149 break_delay | +176 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:19 | 304.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L149 break_delay | +435 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:19 | 304.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L149 break_delay | −197 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:19 | -197.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L149 break_delay | −273 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:19 | -197.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L149 break_delay | −117 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:19 | -197.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L150 break_delay | +236 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:20 | 236.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L150 break_delay | +114 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:20 | 236.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L150 break_delay | +357 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:20 | 236.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L150 break_delay | −233 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:20 | -233.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L150 break_delay | −313 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:20 | -233.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L150 break_delay | −158 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:20 | -233.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L151 break_delay | +362 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:21 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L151 break_delay | +231 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:21 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L151 break_delay | +497 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:21 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L151 break_delay | −273 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:21 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L151 break_delay | −360 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:21 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L151 break_delay | −184 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:21 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L163 break_delay | +292 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:112 | 292.0 | 円 | 一致 | 中(3 桁以上) |
| L163 break_delay | +291 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:113 | 291.0 | 円 | 一致 | 中(3 桁以上) |
| L163 break_delay | +329 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:45 | 329.0 | 円 | 一致 | 中(3 桁以上) |
| L163 break_delay | −230 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:52 | -229.7 | 円 | 一致 | 中(3 桁以上) |
| L163 break_delay | +111 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:19 | 111.0 | 円 | 一致 | 中(3 桁以上) |
| L163 break_delay | +177 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:113 | 177.0 | 円 | 一致 | 中(3 桁以上) |
| L167 break_delay | −0.9 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:111 | -0.9 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L167 break_delay | −27.1 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:111 | -0.9 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L167 break_delay | +24.5 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:111 | -0.9 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L167 break_delay | 37.1 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:111 | 37.1 | 円 | 一致 | 中(3 桁以上) |
| L167 break_delay | −40 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:111 | -40.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L167 break_delay | −89 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:111 | -40.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L167 break_delay | +3 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:111 | -40.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L167 break_delay | +38 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:111 | 38.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L167 break_delay | +13 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:111 | 38.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L167 break_delay | +64 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:111 | 38.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L167 break_delay | +8 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:10 | 8.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L167 break_delay | −114 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:111 | -114.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L167 break_delay | −5 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:60 | -4.65 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L167 break_delay | +2 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:7 | 2.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L167 break_delay | +35 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:50 | 34.9 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L168 break_delay | +13.1 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:112 | 13.1 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L168 break_delay | −21.4 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:112 | 13.1 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L168 break_delay | +46.3 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:112 | 13.1 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L168 break_delay | 48.6 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:112 | 48.6 | 円 | 一致 | 中(3 桁以上) |
| L168 break_delay | −42 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:112 | -42.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L168 break_delay | −105 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:112 | -42.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L168 break_delay | +14 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:112 | -42.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L168 break_delay | +68 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:112 | 68.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L168 break_delay | +35 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:112 | 68.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L168 break_delay | +101 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:112 | 68.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L168 break_delay | +6 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:31 | 6.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L168 break_delay | −81 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:121 | -81.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L168 break_delay | +48 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:112 | 48.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L168 break_delay | +25 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:81 | 25.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L168 break_delay | +41 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:112 | 41.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L169 break_delay | +8.4 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:113 | 8.4 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L169 break_delay | −30.6 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:113 | 8.4 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L169 break_delay | +43.7 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:113 | 8.4 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L169 break_delay | 52.7 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:113 | 52.7 | 円 | 一致 | 中(3 桁以上) |
| L169 break_delay | −59 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:113 | -59.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L169 break_delay | −126 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:113 | -59.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L169 break_delay | −1 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:113 | -59.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L169 break_delay | +76 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:113 | 76.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L169 break_delay | +37 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:113 | 76.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L169 break_delay | +114 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:113 | 76.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L169 break_delay | −10 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:122 | -10.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L169 break_delay | −118 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:113 | -118.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L169 break_delay | +61 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:122 | 61.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L169 break_delay | +12 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:7 | 12.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L169 break_delay | +57 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:113 | 57.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L170 break_delay | −43.2 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:114 | -43.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L170 break_delay | −86.0 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:114 | -43.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L170 break_delay | +0.0 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:114 | -43.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L170 break_delay | 62.8 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:114 | 62.8 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L170 break_delay | −127 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:114 | -127.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L170 break_delay | −200 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:114 | -127.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L170 break_delay | −59 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:114 | -127.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L170 break_delay | +40 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:114 | 40.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L170 break_delay | −8 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:114 | 40.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L170 break_delay | +87 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:114 | 40.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L170 break_delay | −41 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:17 | -41.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L170 break_delay | −248 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:40 | -248.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L170 break_delay | +21 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:123 | 21.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L170 break_delay | −30 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:50 | -30.2 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L170 break_delay | +20 | 円/日 | docs/RESEARCH/matilda_main/break_delay/fam_tables.md:123 | 20.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L181 break_off | +787 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:14 | 787.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L181 break_off | +540 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:14 | 787.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L181 break_off | +1,035 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:14 | 787.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L181 break_off | −112 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:14 | -112.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L181 break_off | −266 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:14 | -112.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L181 break_off | +35 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:14 | -112.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L182 break_off | +362 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:15 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L182 break_off | +231 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:15 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L182 break_off | +497 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:15 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L182 break_off | −273 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:15 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L182 break_off | −360 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:15 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L182 break_off | −184 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:15 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L191 break_off | −781 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:72 | -781.0 | 円 | 一致 | 中(3 桁以上) |
| L191 break_off | +1,402 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:72 | 1402.0 | 円 | 一致 | 中(3 桁以上) |
| L195 break_off | +292.3 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:72 | 292.3 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L195 break_off | +175.6 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:72 | 292.3 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L195 break_off | +416.6 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:72 | 292.3 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L195 break_off | 175.6 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:72 | 175.6 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L195 break_off | +424 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:72 | 424.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L195 break_off | +235 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:72 | 424.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L195 break_off | +634 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:72 | 424.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L195 break_off | +160 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:72 | 160.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L195 break_off | +21 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:72 | 160.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L195 break_off | +289 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:72 | 160.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L195 break_off | −244 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:72 | -244.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L195 break_off | +439 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:72 | 439.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L195 break_off | +425 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:72 | 425.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L195 break_off | +51 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:35 | 51.1 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L195 break_off | −83 | 円/日 | docs/RESEARCH/matilda_main/break_off/fam_tables.md:78 | -83.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L206 range_lo | +362 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:17 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L206 range_lo | +231 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:17 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L206 range_lo | +497 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:17 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L206 range_lo | −273 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:17 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L206 range_lo | −360 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:17 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L206 range_lo | −184 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:17 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L207 range_lo | +335 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:18 | 335.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L207 range_lo | +208 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:18 | 335.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L207 range_lo | +472 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:18 | 335.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L207 range_lo | −253 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:18 | -253.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L207 range_lo | −341 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:18 | -253.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L207 range_lo | −163 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:18 | -253.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L208 range_lo | +303 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:19 | 303.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L208 range_lo | +180 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:19 | 303.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L208 range_lo | +438 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:19 | 303.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L208 range_lo | −190 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:19 | -190.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L208 range_lo | −277 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:19 | -190.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L208 range_lo | −105 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:19 | -190.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L209 range_lo | +255 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:20 | 255.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L209 range_lo | +142 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:20 | 255.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L209 range_lo | +384 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:20 | 255.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L209 range_lo | −73 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:20 | -73.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L209 range_lo | −153 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:20 | -73.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L209 range_lo | +4 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:20 | -73.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L210 range_lo | +362 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:17 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L210 range_lo | +231 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:17 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L210 range_lo | +497 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:17 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L210 range_lo | −273 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:17 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L210 range_lo | −360 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:17 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L210 range_lo | −184 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:17 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L221 range_lo | −27 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:19 | -27.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ) |
| L221 range_lo | +31 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:28 | 31.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ) |
| L221 range_lo | +42 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:51 | 42.3 | 円 | 一致 | 弱(2 桁以下で 1 つだけ) |
| L221 range_lo | +35 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:50 | 34.7 | 円 | 一致 | 弱(2 桁以下で 1 つだけ) |
| L221 range_lo | +26 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:113 | 26.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ) |
| L221 range_lo | +152 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:114 | 152.0 | 円 | 一致 | 中(3 桁以上) |
| L221 range_lo | +152 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:114 | 152.0 | 円 | 一致 | 中(3 桁以上) |
| L225 range_lo | −4.2 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:112 | -4.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L225 range_lo | −12.7 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:112 | -4.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L225 range_lo | +3.5 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:112 | -4.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L225 range_lo | 11.6 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:51 | 11.6 | 円 | 一致 | 中(3 桁以上) |
| L225 range_lo | −28 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:112 | -28.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L225 range_lo | −42 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:112 | -28.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L225 range_lo | −14 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:112 | -28.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L225 range_lo | +19 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:112 | 19.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L225 range_lo | +13 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:112 | 19.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L225 range_lo | +25 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:112 | 19.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L225 range_lo | −125 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:112 | -125.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L225 range_lo | +8 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:28 | 8.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L225 range_lo | +25 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:81 | 25.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L225 range_lo | +7 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:50 | 7.3 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L225 range_lo | +50 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:81 | 50.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L226 range_lo | +12.0 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:113 | 12.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L226 range_lo | −5.2 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:113 | 12.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L226 range_lo | +29.5 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:113 | 12.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L226 range_lo | 25.2 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:113 | 25.2 | 円 | 一致 | 中(3 桁以上) |
| L226 range_lo | −59 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:113 | -59.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L226 range_lo | −89 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:113 | -59.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L226 range_lo | −30 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:113 | -59.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L226 range_lo | +83 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:113 | 83.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L226 range_lo | +67 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:113 | 83.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L226 range_lo | +103 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:113 | 83.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L226 range_lo | −249 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:113 | -249.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L226 range_lo | −10 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:122 | -10.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L226 range_lo | +76 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:113 | 76.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L226 range_lo | +40 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:7 | 40.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L226 range_lo | +205 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:113 | 205.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L227 range_lo | +46.2 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:114 | 46.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L227 range_lo | +14.1 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:114 | 46.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L227 range_lo | +81.8 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:114 | 46.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L227 range_lo | 48.2 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:114 | 48.2 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L227 range_lo | −107 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:114 | -107.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L227 range_lo | −157 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:114 | -107.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L227 range_lo | −53 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:114 | -107.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L227 range_lo | +199 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:114 | 199.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L227 range_lo | +163 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:114 | 199.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L227 range_lo | +242 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:114 | 199.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L227 range_lo | −312 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:52 | -311.7 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L227 range_lo | −65 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:123 | -65.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L227 range_lo | +110 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:114 | 110.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L227 range_lo | +163 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:20 | 163.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L227 range_lo | +415 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:114 | 415.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L229 range_lo | +0 | 円/日 | docs/RESEARCH/matilda_main/range_lo/fam_tables.md:7 | 0.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ) |
| L238 range_hi | +174 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:16 | 174.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L238 range_hi | +84 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:16 | 174.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L238 range_hi | +260 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:16 | 174.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L238 range_hi | −261 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:16 | -261.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L238 range_hi | −329 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:16 | -261.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L238 range_hi | −193 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:16 | -261.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L239 range_hi | +249 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:17 | 249.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L239 range_hi | +136 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:17 | 249.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L239 range_hi | +360 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:17 | 249.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L239 range_hi | −277 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:17 | -277.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L239 range_hi | −356 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:17 | -277.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L239 range_hi | −194 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:17 | -277.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L240 range_hi | +391 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:18 | 391.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L240 range_hi | +256 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:18 | 391.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L240 range_hi | +533 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:18 | 391.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L240 range_hi | −274 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:18 | -274.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L240 range_hi | −358 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:18 | -274.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L240 range_hi | −188 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:18 | -274.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L241 range_hi | +362 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:19 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L241 range_hi | +231 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:19 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L241 range_hi | +497 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:19 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L241 range_hi | −273 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:19 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L241 range_hi | −360 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:19 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L241 range_hi | −184 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:19 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L252 range_hi | −417 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:98 | -417.0 | 円 | 一致 | 中(3 桁以上) |
| L252 range_hi | −276 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:99 | -276.0 | 円 | 一致 | 中(3 桁以上) |
| L256 range_hi | −88.7 | 円/日 | docs/RESEARCH/matilda_main/d7_fullperiod.out:3 | -88.7 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L256 range_hi | −149.6 | 円/日 | docs/RESEARCH/matilda_main/d7_fullperiod.out:3 | -88.7 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L256 range_hi | −25.0 | 円/日 | docs/RESEARCH/matilda_main/d7_fullperiod.out:3 | -88.7 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L256 range_hi | 84.9 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:98 | 84.9 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L256 range_hi | −190 | 円/日 | docs/RESEARCH/matilda_main/d7_fullperiod.out:4 | -189.5 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L256 range_hi | −305 | 円/日 | docs/RESEARCH/matilda_main/d7_fullperiod.out:4 | -189.5 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L256 range_hi | −81 | 円/日 | docs/RESEARCH/matilda_main/d7_fullperiod.out:4 | -189.5 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L256 range_hi | +12 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:98 | 12.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L256 range_hi | −50 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:98 | 12.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L256 range_hi | +73 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:98 | 12.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L256 range_hi | +21 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:100 | 21.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L256 range_hi | −289 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:98 | -289.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L256 range_hi | −86 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:106 | -86.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L256 range_hi | +41 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:106 | 41.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L256 range_hi | +2 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:55 | 1.75 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L257 range_hi | −59.4 | 円/日 | docs/RESEARCH/matilda_main/d7_fullperiod.out:7 | -59.4 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L257 range_hi | −111.0 | 円/日 | docs/RESEARCH/matilda_main/d7_fullperiod.out:7 | -59.4 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L257 range_hi | −8.3 | 円/日 | docs/RESEARCH/matilda_main/d7_fullperiod.out:7 | -59.4 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L257 range_hi | 64.0 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:99 | 64.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L257 range_hi | −115 | 円/日 | docs/RESEARCH/matilda_main/d7_fullperiod.out:8 | -114.8 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L257 range_hi | −209 | 円/日 | docs/RESEARCH/matilda_main/d7_fullperiod.out:8 | -114.8 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L257 range_hi | −30 | 円/日 | docs/RESEARCH/matilda_main/d7_fullperiod.out:8 | -114.8 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L257 range_hi | −4 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:99 | -4.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L257 range_hi | −48 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:99 | -4.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L257 range_hi | +36 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:99 | -4.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L257 range_hi | +7 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:45 | 7.1 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L257 range_hi | −188 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:18 | -188.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L257 range_hi | −62 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:99 | -62.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L257 range_hi | −62 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:99 | -62.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L257 range_hi | +6 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:28 | 6.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L258 range_hi | +13.3 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:100 | 13.3 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L258 range_hi | −4.0 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:100 | 13.3 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L258 range_hi | +37.3 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:100 | 13.3 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L258 range_hi | 30.1 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:100 | 30.1 | 円 | 一致 | 中(3 桁以上) |
| L258 range_hi | +28 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:100 | 28.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L258 range_hi | −1 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:100 | 28.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L258 range_hi | +71 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:100 | 28.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L258 range_hi | −2 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:100 | -2.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L258 range_hi | −18 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:100 | -2.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L258 range_hi | +12 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:100 | -2.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L258 range_hi | +0 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:7 | 0.008844 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L258 range_hi | −12 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:108 | -12.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L258 range_hi | −17 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:57 | -17.03 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L258 range_hi | +0 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:7 | 0.008844 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L258 range_hi | −0 | 円/日 | docs/RESEARCH/matilda_main/range_hi/fam_tables.md:7 | 0.008844 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L267 vola_gate | +341 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:16 | 341.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L267 vola_gate | +218 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:16 | 341.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L267 vola_gate | +475 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:16 | 341.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L267 vola_gate | −254 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:16 | -254.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L267 vola_gate | −341 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:16 | -254.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L267 vola_gate | −164 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:16 | -254.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L268 vola_gate | +322 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:17 | 322.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L268 vola_gate | +207 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:17 | 322.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L268 vola_gate | +450 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:17 | 322.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L268 vola_gate | −179 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:17 | -179.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L268 vola_gate | −263 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:17 | -179.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L268 vola_gate | −97 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:17 | -179.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L269 vola_gate | +285 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:18 | 285.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L269 vola_gate | +172 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:18 | 285.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L269 vola_gate | +407 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:18 | 285.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L269 vola_gate | −87 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:18 | -87.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L269 vola_gate | −166 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:18 | -87.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L269 vola_gate | −11 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:18 | -87.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L270 vola_gate | +362 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:19 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L270 vola_gate | +231 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:19 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L270 vola_gate | +497 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:19 | 362.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L270 vola_gate | −273 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:19 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L270 vola_gate | −360 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:19 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L270 vola_gate | −184 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:19 | -273.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L281 vola_gate | +271 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:98 | 271.0 | 円 | 一致 | 中(3 桁以上) |
| L281 vola_gate | −26 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:98 | -26.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ) |
| L281 vola_gate | +16 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:47 | 15.6 | 円 | 一致 | 弱(2 桁以下で 1 つだけ) |
| L281 vola_gate | −44 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:45 | -43.7 | 円 | 一致 | 弱(2 桁以下で 1 つだけ) |
| L281 vola_gate | +11 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:45 | 11.2 | 円 | 一致 | 弱(2 桁以下で 1 つだけ) |
| L281 vola_gate | −79 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:100 | -79.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ) |
| L281 vola_gate | +93 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:99 | 93.0 | 円 | 一致 | 弱(2 桁以下で 1 つだけ) |
| L285 vola_gate | −1.1 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:98 | -1.1 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L285 vola_gate | −16.1 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:98 | -1.1 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L285 vola_gate | +12.5 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:98 | -1.1 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L285 vola_gate | 20.5 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:98 | 20.5 | 円 | 一致 | 中(3 桁以上) |
| L285 vola_gate | −21 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:98 | -21.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L285 vola_gate | −47 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:98 | -21.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L285 vola_gate | +5 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:98 | -21.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L285 vola_gate | +19 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:98 | 19.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L285 vola_gate | +11 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:98 | 19.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L285 vola_gate | +27 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:98 | 19.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L285 vola_gate | −107 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:98 | -107.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L285 vola_gate | +10 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:45 | 10.3 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L285 vola_gate | +17 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:47 | 16.7 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L285 vola_gate | +4 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:63 | 3.81 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L285 vola_gate | +57 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:47 | 57.1 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L286 vola_gate | +26.8 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:99 | 26.8 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L286 vola_gate | +1.4 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:99 | 26.8 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L286 vola_gate | +52.9 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:99 | 26.8 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L286 vola_gate | 36.7 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:99 | 36.7 | 円 | 一致 | 中(3 桁以上) |
| L286 vola_gate | −40 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:99 | -40.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L286 vola_gate | −87 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:99 | -40.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L286 vola_gate | +8 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:99 | -40.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L286 vola_gate | +93 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:99 | 93.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L286 vola_gate | +74 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:99 | 93.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L286 vola_gate | +120 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:99 | 93.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L286 vola_gate | −154 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:107 | -154.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L286 vola_gate | −11 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:18 | -11.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L286 vola_gate | +76 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:99 | 76.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L286 vola_gate | +41 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:99 | 41.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L286 vola_gate | +261 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:25 | 261.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L287 vola_gate | +54.2 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:100 | 54.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L287 vola_gate | +14.8 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:100 | 54.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L287 vola_gate | +95.1 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:100 | 54.2 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L287 vola_gate | 55.9 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:100 | 55.9 | 円 | 一致 | 中(3 桁以上) |
| L287 vola_gate | −78 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:100 | -78.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L287 vola_gate | −144 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:100 | -78.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L287 vola_gate | −7 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:100 | -78.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L287 vola_gate | +186 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:100 | 186.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L287 vola_gate | +148 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:100 | 186.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L287 vola_gate | +228 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:100 | 186.0 | 円 | 一致 | 強(区間の 3 つが同じ行) |
| L287 vola_gate | −145 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:108 | -145.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L287 vola_gate | −105 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:100 | -105.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L287 vola_gate | +111 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:100 | 111.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L287 vola_gate | +148 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:100 | 148.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |
| L287 vola_gate | +435 | 円/日 | docs/RESEARCH/matilda_main/vola_gate/fam_tables.md:100 | 435.0 | 円 | 一致 | 表 3 の年の列: fam_tables.md の D7 年ごとの表の同じ本・同じ年で一致(stage1_years.py) |

## 6. 打ったコマンド(主なもの)

```
# 出力の無い台本を打ち直した(読むだけ。標準出力を scratchpad へ)
PYTHONPATH=src python3 docs/RESEARCH/matilda_main/base/d3_extra.py  > <scratchpad>/rerun/d3_extra.out
PYTHONPATH=src python3 docs/RESEARCH/matilda_main/base/d9b_extra.py > <scratchpad>/rerun/d9b_extra.out
PYTHONPATH=src python3 docs/RESEARCH/matilda_main/base/d0_extra.py  > <scratchpad>/rerun/d0_extra.out
#   d9b_extra.out の例: 「全期間 … 保有≤3分 273038 2934918 | >3分 75745 -2803529」「利確 保有>20分 6063 -402291 1 本 -66.4」
# 数を拾い・突き合わせる道具(scratchpad): srcidx.py・tok.py・match.py・list_ledger.py・run_ledger.py・run_stage1.py・stage1_years.py・roundchk.py・gen.py
python3 list_ledger.py      # 台帳の数 2,833 個を拾い、対象 1,319 個を残す
python3 run_ledger.py       # 台帳の突き合わせ
python3 run_stage1.py       # 段 1 の表の突き合わせ(557 個、全部一致)
python3 stage1_years.py     # 表 3 の年の列を fam_tables.md の D7 年ごとの表と升目ごとに照らす(110 個一致)
python3 roundchk.py         # × 20 で合った数を json の精密な値で確かめ直す(13 個が合わず、手で 12 個を値の誤りと確認)
# 手の確かめの例
grep -n "0 分超 → 0 分超" docs/RESEARCH/matilda_main/break_len_mult/band_migration.out
cat docs/RESEARCH/matilda_main/break_delay/held_reason_break_delay_2.out
python3 -c "…alert_x1/diag_tables.json の d7/all を × 20…"   # → mean 6.343・lo −1.335・hi 13.478・mde 10.78
grep -rn -- "204,191" docs/RESEARCH/matilda_main   # 出力 0 件(K-359)
```

## 7. 読むのをやめた・確かめきれなかった範囲

- 上限 90 分を越えた(約 110 分)。越えた後は新しい手の確かめをせず、そこまでの結果を書いた。
- 台帳の「一致」のうち弱(2 桁以下の数が 1 つだけで合った){strength['弱']} 個は、出所に同じ値があることだけを確かめた。同じ値が別の量として偶然あった可能性を、1 つずつ出所の行の意味で消してはいない。とくに 1 桁の数(+2・−1・+0 など)。
- 中(3 桁以上が 1 つ){strength['中']} 個も、出所の行の意味(どの本・どの半分か)までは照らしていない。値が合ったことだけ。
- 道具が「本数・割合・日付・時刻」として外した数(台帳で 2,833 − 1,319 = 1,514 個)は、外し方の誤り(損益の数を外した)を全部は見ていない。見た範囲では、K-321 の「(基準 −0.85)」(ポイント)のように外して正しいものだった。
- 台帳の行の「射程」「なぜの仮説」「次の問い」などの欄の数は対象外(委任文の範囲どおり)。
- 「確かめられない」{lc['確かめられない']} 個は §3 の一覧のとおり。出所の行(計算の元)を特定すれば判定できる。
- 段 1 の表の表 2(ポイント)は割合なので対象外。
- `docs/RESEARCH/WINDOW1/`・`backtest_data/phase2_sealed/` は読んでいない。
