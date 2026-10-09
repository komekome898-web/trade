# 突き合わせ 7: break_off の文書の数と出所(読むだけ)

作業者が 2026-10-09 に書いた。文書・台帳・コードは何も変えていない。書いたのはこのファイルだけ。コミット・押し出しはしていない。

## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 担当の文書 `docs/ANAL` `YSIS/2026-10-09_matilda_main_break_off.md` の、行頭が `>` でない行にある損益・値動きの数を全部拾い、出所の出力ファイルの値・単位と 1 つずつ突き合わせて判定を付け、影響範囲を数で示す | 「**もっと徹底的に調べて影響範囲を確定させてください。**」 |
| 結果を `docs/DISCUSSIONS/2026-10-09_bp_units/audit_7.md` だけに書く(ほかは変えない・コミットしない) | **(該当語なし)**(リードの委任文の指示) |

見込み時間(着手時): 55 分 = 単位の地図・手本(audit_4)・担当の文書を読む 10 分 + 出所の出力(break_off の .md・.out・json、base の json、break_dist・break_len_mult の .out)を読む 10 分 + 拾い出しと突き合わせの台本を書く 20 分 + 外れの見直し 5 分 + この文書を書く 10 分。上限 60 分。

実際: 上限の 60 分の中で、担当の文書の全部の行を突き合わせた(残りの範囲は無い。確かめきれなかった点は末尾)。

## 決めたこと(判定の決まり)

- 拾った数: 行頭が `>` でない行の、符号の付いた数(+・−)と、MDE(表の括弧 `(353)` と `MDE …`)と、D4 の表の符号の無い MFE。本数・割合(「利確で閉じる割合」・`99%`・`99.8%`・「24.4%」)・差(ポイント)(181〜184・403・404 行の +0.43 など)・日付・時刻・分(65 行の「+1 分」)・倍(「約 5 倍」「3.4 / 3.2 倍」)・段の数・頂点の比(0.00・0.67)・ボラの倍数は数えない。`[A]-数`(K-346・L-875 など)の番号は数えない。台本の拾い出しと表の行が、符号付きの数について行ごとに過不足なく合うことを機械で確かめた(打ったコマンドの 3)。
- 換算は書かれた単位に合わせて 1 通りだけ: 文書が円・円/日と書き出所が口座の bp(`diag_tables`・`diag_paths` の損益)なら出所 × 20、文書が bp と書けば × 1、move_bp は × 1。比べには `.json` の全桁を使い、文書の桁に丸めて比べた(台本が 1 つずつ自動で比べ、合わないものを印字する。印字は −5,439,000 の 1 件だけで、これは「約」で千の位に丸めた数なので出所が無い(計算で再現)にした)。
- **一致**: 出所で同じ数を見つけた(円の出力はそのまま、bp の出力は × 20)。D1(109 行「bp/日 × 20 = 円」)・D7(282 行「bp/日 × 20 = 円」、412 行「年の値は bp/日 × 20」)・D3 の分位(199 行「bp。× 20 = 円」)は換算が書いてあるので、bp の json を出所にして一致とした。
- **単位の誤り(出所の指し方)**: 値は × 20 で合う(円の写し `fam_tables.md` とも合う)が、その行・節が名指したのが bp のファイル(読み口の D3・D6、`diag_paths.md` の D4 の和)で、× 20 の換算を書いていないもの。手本の audit_4 と同じ決まり。
  - **audit_4 と違う点(1 つ)**: 177 行(D3 の節)は「`break_off/compare.md`(円)と読み口の D3(写しは `fam_tables.md`)」と 2 つを名指す。この節の数のうち、名指しの円のファイル `compare.md` に同じ数があるもの(197 行の +15.3・−1,257.6(2 回。2 回目は「4,325 × −1,257.6」の式の中)・+36.4・−258.8・−315.2、198 行の +990,576)は**一致**にし、`compare.md` に無く読み口の D3(bp)にしか無いもの(197 行の区間 4 つ、198 行の上位・下位 5% の日の和 4 つ)を出所の指し方にした。audit_4 は beard の同じ書き方の節(beard 177 行)で、`compare.md` にある +36.4・−258.8・−315.2 も出所の指し方に数えている。audit_4 の決まりに合わせると、この文書の出所の指し方は 34 → 41(197 行の 6 つと 198 行の 1 つ)、一致は 381 → 374 になる。
  - D9b・D10(367〜418 行)で同じ数を繰り返す行は、ファイルを名指さず文書の節を指す。この行の数は、円のファイルにあれば一致、bp のファイルにしか無ければ書かれた単位(円)で × 20 して比べた(368 行の −1,345,377、414 行の分位の円 4 つは一致にした)。最初に出た節での判定と変わりうる。
- **値の誤り**: × 20 しても・丸めても合わない。この文書では全部が「丸めた値どうしの足し引き」で、帯の移り(`band_migration.out`)の升目の 1 日あたり(整数に丸めた表示)を足した数。出所の精度の値は、升目の差の和(本の和 − 基準の和、円)÷ 半分の日数(`band_migration.py:9` の DAYS = 前半 1,469・後半 1,470)で出した。
- **出所が無い(計算で再現)**: どの出力ファイルにも無い数で、出所の値から計算して文書の桁で再現できたもの。式は「出所」の列に書いた。
- **確かめられない(丸めの境)**: 出所の表示がちょうど .5(`held_reason.out:5` の +977.5)で、文書がそれを整数に丸めている。
- 出所の列のパスは `docs/RESEARCH/matilda_main/` からの相対。json は行の代わりに鍵(`.d1.segments.first.mean` など)を書いた。base の値は `base/diag_tables.json`・`base/diag_paths.json` から直接引いた(audit_4 の出所の列は写していない)。
- 出所の台本の単位(UNITS_MAP §2 に無い出力): `band_migration.py:15` は `pnl_jpy` を足す = 円、`:9` の日数 1,469・1,470。`break_off/break_off_detail.out`・`held_reason.out`・`same_bar_reason.out`・`levels_reason.out`・`market_side.out`・`scene_diff.out`・`scenes.out` の台本の単位は audit_4 が確かめたもの(円)をそのまま使った(この仕事では台本を読み直していない)。UNITS_MAP §1・§2 の主張(`diag_tables` の D1・D3・D6・D7 と `diag_paths` の D4 の和が口座の bp、`fam_tables.md` が × 20 の円、MFE・MAE・出の後・D5 が move_bp)は、この文書の数で食い違う点が無かった(例: `diag_paths.json` の勝った群 741,413.0 × 20 = 14,828,260 = `fam_tables.md:42`、`diag_tables.json` の D6 〜1 分 0.23027 × 20 = 4.6 = `fam_tables.md:65`)。UNITS_MAP §3 の 1・2 点目はこの文書に当たらない(期間の始まりは本・基準とも 2015-12-01、`fam_tables.md:7-8`。段数の文書ではない)。**3 点目(円の値なのに出所を `diag_paths.md`(bp)と書いている)と同じ型が、この文書の 219 行(D4 の節)にある**。range_hi だけの問題ではない。D4 の和 8 件(223〜225 行・228 行)を出所の指し方に数えた。

## 判定ごとの個数

拾った数 478。
- 一致: 381
- 出所が無い(計算で再現): 43
- 単位の誤り(出所の指し方): 34
- 値の誤り(丸めた値どうしの計算): 18
- 確かめられない(丸めの境): 2

## 一致以外のものの一覧(行番号つき)

- **出所が無い(計算で再現)**(43): 197 行 −5,439,000、228 行 −10,701,050、228 行 −16,200,617、294 行 +245、294 行 +2、294 行 +9、294 行 +147、310 行 −107、310 行 −85、313 行 +109、313 行 +114、313 行 +245、313 行 +245、313 行 +147、314 行 +288、314 行 +135、314 行 +2、314 行 +166、314 行 −14、314 行 +9、314 行 +40、314 行 +116、314 行 −14、334 行 +245、334 行 +147、367 行 +109、367 行 +114、367 行 +245、372 行 +147、372 行 +245、414 行 +109、414 行 +114、414 行 +147、414 行 +288、414 行 +166、414 行 −14、414 行 +9、414 行 +40、414 行 +116、418 行 +166、418 行 −14、418 行 +116、418 行 +40
- **単位の誤り(出所の指し方)**(34): 197 行 +14.3、197 行 +16.2、197 行 −1,360.8、197 行 −1,157.2、198 行 +1,193,340、198 行 −1,345,377、198 行 +653,497、198 行 −766,805、223 行 +14,828,260、223 行 +10,177,344、224 行 −6,512,367、224 行 −4,695,044、225 行 −9,688,250、225 行 −6,006,006、228 行 +10,177,344、228 行 +14,828,260、263 行 +4.6、263 行 +3.0、263 行 +6.2、263 行 +1.7、263 行 −0.7、263 行 +4.0、263 行 +1.8、263 行 +0.1、263 行 +3.6、263 行 −1.1、263 行 −3.2、263 行 +0.8、263 行 +2.4、263 行 +1.3、263 行 +3.3、263 行 −2.0、263 行 −3.2、263 行 −0.8
- **値の誤り(丸めた値どうしの計算)**(18): 294 行 +178、294 行 +5、294 行 +425、294 行 +161、313 行 +5、313 行 +5、313 行 +178、314 行 +425、314 行 +161、314 行 +5、334 行 +5、334 行 +178、367 行 +5、372 行 +178、372 行 +5、414 行 +178、414 行 +161、414 行 +5
- **確かめられない(丸めの境)**(2): 300 行 +978、313 行 +978

値の誤りの中身(18 件は 5 種類の数の繰り返し):

| 文書の数 | 出てくる行 | 文書の書き方 | 出所の精度の値 |
|---|---|---|---|
| 前半の同じ取引 +178 | 294・313・334・372・414 | 升目 +48 + 28 + 102 | 差の和 260,607 円 ÷ 1,469 = +177.4 → +177 |
| 後半のこちらだけ +5(314・414 行では「基準の帯で分けた(無し)+5」) | 294・313(2 回)・314・334・367・372・414 | 升目 +133 − 128 | 差の和 6,308 円 ÷ 1,470 = +4.29 → +4 |
| 前半の升目の和 +425 | 294・314 | 升目 7 つの和。294 行は「D7 と合う」と書く | 623,339 円 ÷ 1,469 = +424.3 → +424(D7 の前半 +424 と同じ) |
| 後半の升目の和 +161 | 294・314・414 | 升目 7 つの和。294 行は「D7 と合う」と書く | 235,848 円 ÷ 1,470 = +160.4 → +160(D7 の後半 +160 と同じ) |

知見の文(414 行)に入っているのは +178・+161・+5(各 1 回)。単位の取り違えではない(円/日どうし)。

出所の指し方の中身: 197 行の区間 4 つ・198 行の 5% の日の和 4 つ(D3、名指し = 読み口の D3)、223〜225 行と 228 行の D4 の損益の和 8 つ(名指し = `break_off/diag_paths.md`、219 行は「和は円」と書く)、263 行の D6 の 18 個(名指し = 読み口の「D6 固まり」だけ、写しも書いていない)。どれも × 20 で合い、円の数としては正しい。

## 表

| 文書の行 | 書かれた数 | 書かれた単位 | 出所 ファイル:行 | 出所の値 | 出所の単位 | 判定 | 備考 |
|---|---|---|---|---|---|---|---|
| 30 | +424 | 円/日 | both_halves.out:13 | 424 | 円/日 | 一致 |  |
| 30 | +235 | 円/日 | both_halves.out:13 | 235 | 円/日 | 一致 |  |
| 30 | +634 | 円/日 | both_halves.out:13 | 634 | 円/日 | 一致 |  |
| 30 | +160 | 円/日 | both_halves.out:13 | 160 | 円/日 | 一致 |  |
| 30 | +21 | 円/日 | both_halves.out:13 | 21 | 円/日 | 一致 |  |
| 30 | +289 | 円/日 | both_halves.out:13 | 289 | 円/日 | 一致 |  |
| 56 | +990,575.985 | 円 | break_off/fam_tables.md:7 | 990576 | 円 | 一致 |  |
| 85 | −14,138 | 円 | break_off/market_side.out:1 | -14138 | 円 | 一致 |  |
| 85 | +990,576 | 円 | break_off/compare.md:21 | 990576 | 円 | 一致 |  |
| 85 | −1,258 | 円 | break_off/compare.md:21(成行 1 本) | -1257.6 | 円 | 一致 |  |
| 113 | +787 | 円/日 | break_off/diag_tables.json:.d1.segments.first.mean | 39.3301(× 20 = 786.60) | bp/日(口座) | 一致 |  |
| 113 | +540 | 円/日 | break_off/diag_tables.json:.first.lo | 27.0024(× 20 = 540.05) | bp/日(口座) | 一致 |  |
| 113 | +1,035 | 円/日 | break_off/diag_tables.json:.first.hi | 51.7351(× 20 = 1,034.70) | bp/日(口座) | 一致 |  |
| 113 | 353 | 円/日(MDE も円/日) | break_off/diag_tables.json:.first.mde | 17.6653(× 20 = 353.31) | bp/日(口座) | 一致 |  |
| 113 | −112 | 円/日 | break_off/diag_tables.json:.second.mean | -5.61026(× 20 = -112.21) | bp/日(口座) | 一致 |  |
| 113 | −266 | 円/日 | break_off/diag_tables.json:.second.lo | -13.2853(× 20 = -265.71) | bp/日(口座) | 一致 |  |
| 113 | +35 | 円/日 | break_off/diag_tables.json:.second.hi | 1.76715(× 20 = 35.34) | bp/日(口座) | 一致 |  |
| 113 | 216 | 円/日(MDE も円/日) | break_off/diag_tables.json:.second.mde | 10.8064(× 20 = 216.13) | bp/日(口座) | 一致 |  |
| 113 | −899 | 円/日 | break_off/diag_tables.json:.diff.mean | -44.9403(× 20 = -898.81) | bp/日(口座) | 一致 |  |
| 113 | −1,188 | 円/日 | break_off/diag_tables.json:.diff.lo | -59.396(× 20 = -1,187.92) | bp/日(口座) | 一致 |  |
| 113 | −620 | 円/日 | break_off/diag_tables.json:.diff.hi | -31.0154(× 20 = -620.31) | bp/日(口座) | 一致 |  |
| 113 | +337 | 円/日 | break_off/diag_tables.json:.d1.rows[全期間].mean | 16.8523(× 20 = 337.05) | bp/日(口座) | 一致 |  |
| 113 | +187 | 円/日 | break_off/diag_tables.json:.rows[全期間].lo | 9.34552(× 20 = 186.91) | bp/日(口座) | 一致 |  |
| 113 | +482 | 円/日 | break_off/diag_tables.json:.rows[全期間].hi | 24.0885(× 20 = 481.77) | bp/日(口座) | 一致 |  |
| 114 | +362 | 円/日 | base/diag_tables.json:.d1.segments.first.mean | 18.1147(× 20 = 362.29) | bp/日(口座) | 一致 |  |
| 114 | +231 | 円/日 | base/diag_tables.json:.first.lo | 11.5545(× 20 = 231.09) | bp/日(口座) | 一致 |  |
| 114 | +497 | 円/日 | base/diag_tables.json:.first.hi | 24.8558(× 20 = 497.12) | bp/日(口座) | 一致 |  |
| 114 | 195 | 円/日(MDE も円/日) | base/diag_tables.json:.first.mde | 9.75585(× 20 = 195.12) | bp/日(口座) | 一致 |  |
| 114 | −273 | 円/日 | base/diag_tables.json:.second.mean | -13.6334(× 20 = -272.67) | bp/日(口座) | 一致 |  |
| 114 | −360 | 円/日 | base/diag_tables.json:.second.lo | -17.9998(× 20 = -360.00) | bp/日(口座) | 一致 |  |
| 114 | −184 | 円/日 | base/diag_tables.json:.second.hi | -9.19333(× 20 = -183.87) | bp/日(口座) | 一致 |  |
| 114 | 125 | 円/日(MDE も円/日) | base/diag_tables.json:.second.mde | 6.2593(× 20 = 125.19) | bp/日(口座) | 一致 |  |
| 114 | −635 | 円/日 | base/diag_tables.json:.diff.mean | -31.7481(× 20 = -634.96) | bp/日(口座) | 一致 |  |
| 114 | −805 | 円/日 | base/diag_tables.json:.diff.lo | -40.2715(× 20 = -805.43) | bp/日(口座) | 一致 |  |
| 114 | −476 | 円/日 | base/diag_tables.json:.diff.hi | -23.8222(× 20 = -476.44) | bp/日(口座) | 一致 |  |
| 114 | +45 | 円/日 | base/diag_tables.json:.d1.rows[全期間].mean | 2.23527(× 20 = 44.71) | bp/日(口座) | 一致 |  |
| 114 | −41 | 円/日 | base/diag_tables.json:.rows[全期間].lo | -2.05628(× 20 = -41.13) | bp/日(口座) | 一致 |  |
| 114 | +124 | 円/日 | base/diag_tables.json:.rows[全期間].hi | 6.20764(× 20 = 124.15) | bp/日(口座) | 一致 |  |
| 120 | −1,044 | 円/日 | break_off/diag_tables.json:.d1.rows[2015].mean | -52.1908(× 20 = -1,043.82) | bp/日(口座) | 一致 |  |
| 120 | −111 | 円/日 | break_off/diag_tables.json:.d1.rows[2016].mean | -5.55334(× 20 = -111.07) | bp/日(口座) | 一致 |  |
| 120 | +1,966 | 円/日 | break_off/diag_tables.json:.d1.rows[2017].mean | 98.2857(× 20 = 1,965.71) | bp/日(口座) | 一致 |  |
| 120 | +982 | 円/日 | break_off/diag_tables.json:.d1.rows[2018].mean | 49.099(× 20 = 981.98) | bp/日(口座) | 一致 |  |
| 120 | +454 | 円/日 | break_off/diag_tables.json:.d1.rows[2019].mean | 22.7187(× 20 = 454.37) | bp/日(口座) | 一致 |  |
| 120 | +431 | 円/日 | break_off/diag_tables.json:.d1.rows[2020].mean | 21.5417(× 20 = 430.83) | bp/日(口座) | 一致 |  |
| 120 | −168 | 円/日 | break_off/diag_tables.json:.d1.rows[2021].mean | -8.4082(× 20 = -168.16) | bp/日(口座) | 一致 |  |
| 120 | −212 | 円/日 | break_off/diag_tables.json:.d1.rows[2022].mean | -10.5831(× 20 = -211.66) | bp/日(口座) | 一致 |  |
| 120 | −562 | 円/日 | break_off/diag_tables.json:.d1.rows[2023].mean | -28.094(× 20 = -561.88) | bp/日(口座) | 一致 |  |
| 121 | −263 | 円/日 | base/diag_tables.json:.d1.rows[2015].mean | -13.143(× 20 = -262.86) | bp/日(口座) | 一致 |  |
| 121 | +133 | 円/日 | base/diag_tables.json:.d1.rows[2016].mean | 6.63264(× 20 = 132.65) | bp/日(口座) | 一致 |  |
| 121 | +564 | 円/日 | base/diag_tables.json:.d1.rows[2017].mean | 28.1875(× 20 = 563.75) | bp/日(口座) | 一致 |  |
| 121 | +543 | 円/日 | base/diag_tables.json:.d1.rows[2018].mean | 27.1491(× 20 = 542.98) | bp/日(口座) | 一致 |  |
| 121 | +244 | 円/日 | base/diag_tables.json:.d1.rows[2019].mean | 12.2149(× 20 = 244.30) | bp/日(口座) | 一致 |  |
| 121 | +6 | 円/日 | base/diag_tables.json:.d1.rows[2020].mean | 0.295167(× 20 = 5.90) | bp/日(口座) | 一致 |  |
| 121 | −384 | 円/日 | base/diag_tables.json:.d1.rows[2021].mean | -19.2131(× 20 = -384.26) | bp/日(口座) | 一致 |  |
| 121 | −263 | 円/日 | base/diag_tables.json:.d1.rows[2022].mean | -13.1531(× 20 = -263.06) | bp/日(口座) | 一致 |  |
| 121 | −479 | 円/日 | base/diag_tables.json:.d1.rows[2023].mean | -23.9354(× 20 = -478.71) | bp/日(口座) | 一致 |  |
| 123 | +1,966 | 円/日 | break_off/diag_tables.json:.d1.rows[2017].mean | 98.2857(× 20 = 1,965.71) | bp/日(口座) | 一致 |  |
| 123 | +337 | 円/日 | break_off/diag_tables.json:.d1.rows[全期間].mean | 16.8523(× 20 = 337.05) | bp/日(口座) | 一致 |  |
| 123 | 216 | 円/日(MDE) | break_off/diag_tables.json:.d1.segments.second.mde | 10.8064(× 20 = 216.13) | bp/日(口座) | 一致 |  |
| 156 | +86 | 円/日 | break_off/scene_diff.out:4 | 86 | 円/日 | 一致 |  |
| 156 | −288 | 円/日 | break_off/scene_diff.out:4 | -288 | 円/日 | 一致 |  |
| 156 | +441 | 円/日 | break_off/scene_diff.out:4 | 441 | 円/日 | 一致 |  |
| 156 | −147 | 円/日 | break_off/scene_diff.out:5 | -147 | 円/日 | 一致 |  |
| 156 | −308 | 円/日 | break_off/scene_diff.out:5 | -308 | 円/日 | 一致 |  |
| 156 | −6 | 円/日 | break_off/scene_diff.out:5 | -6 | 円/日 | 一致 |  |
| 157 | +443 | 円/日 | break_off/scene_diff.out:6 | 443 | 円/日 | 一致 |  |
| 157 | +32 | 円/日 | break_off/scene_diff.out:6 | 32 | 円/日 | 一致 |  |
| 157 | +854 | 円/日 | break_off/scene_diff.out:6 | 854 | 円/日 | 一致 |  |
| 157 | +56 | 円/日 | break_off/scene_diff.out:7 | 56 | 円/日 | 一致 |  |
| 157 | −183 | 円/日 | break_off/scene_diff.out:7 | -183 | 円/日 | 一致 |  |
| 157 | +301 | 円/日 | break_off/scene_diff.out:7 | 301 | 円/日 | 一致 |  |
| 158 | +1,343 | 円/日 | break_off/scene_diff.out:8 | 1343 | 円/日 | 一致 |  |
| 158 | +859 | 円/日 | break_off/scene_diff.out:8 | 859 | 円/日 | 一致 |  |
| 158 | +1,888 | 円/日 | break_off/scene_diff.out:8 | 1888 | 円/日 | 一致 |  |
| 158 | +666 | 円/日 | break_off/scene_diff.out:9 | 666 | 円/日 | 一致 |  |
| 158 | +338 | 円/日 | break_off/scene_diff.out:9 | 338 | 円/日 | 一致 |  |
| 158 | +973 | 円/日 | break_off/scene_diff.out:9 | 973 | 円/日 | 一致 |  |
| 160 | +1,343 | 円/日 | break_off/scene_diff.out:8 | 1343 | 円/日 | 一致 |  |
| 160 | +666 | 円/日 | break_off/scene_diff.out:9 | 666 | 円/日 | 一致 |  |
| 160 | −147 | 円/日 | break_off/scene_diff.out:5 | -147 | 円/日 | 一致 |  |
| 181 | +18.6 | 円 | break_off/compare.md:7 | 18.6 | 円 | 一致 |  |
| 181 | −1,219.2 | 円 | break_off/compare.md:7 | -1219.2 | 円 | 一致 |  |
| 181 | −5,625,036 | 円 | break_off/compare.md:7 | -5.62504e+06 | 円 | 一致 |  |
| 181 | +1,155,518 | 円 | break_off/compare.md:7 | 1.15552e+06 | 円 | 一致 |  |
| 182 | +40.5 | 円 | break_off/compare.md:6 | 40.5 | 円 | 一致 |  |
| 182 | −281.0 | 円 | break_off/compare.md:6 | -281 | 円 | 一致 |  |
| 182 | −273.4 | 円 | break_off/compare.md:6 | -273.4 | 円 | 一致 |  |
| 182 | −3,866,293 | 円 | break_off/compare.md:6 | -3.86629e+06 | 円 | 一致 |  |
| 182 | +532,210 | 円 | break_off/compare.md:6 | 532210 | 円 | 一致 |  |
| 183 | +11.9 | 円 | break_off/compare.md:14 | 11.9 | 円 | 一致 |  |
| 183 | −1,301.6 | 円 | break_off/compare.md:14 | -1301.6 | 円 | 一致 |  |
| 183 | −5,401,042 | 円 | break_off/compare.md:14 | -5.40104e+06 | 円 | 一致 |  |
| 183 | −164,942 | 円 | break_off/compare.md:14 | -164942 | 円 | 一致 |  |
| 184 | +32.2 | 円 | break_off/compare.md:13 | 32.2 | 円 | 一致 |  |
| 184 | −238.4 | 円 | break_off/compare.md:13 | -238.4 | 円 | 一致 |  |
| 184 | −431.6 | 円 | break_off/compare.md:13 | -431.6 | 円 | 一致 |  |
| 184 | −3,834,951 | 円 | break_off/compare.md:13 | -3.83495e+06 | 円 | 一致 |  |
| 184 | −400,821 | 円 | break_off/compare.md:13 | -400821 | 円 | 一致 |  |
| 192 | +1,002 | 円/日 | break_off/fam_tables.md:28 | 1002 | 円/日 | 一致 |  |
| 192 | +921 | 円/日 | break_off/fam_tables.md:28 | 921 | 円/日 | 一致 |  |
| 192 | +1,078 | 円/日 | break_off/fam_tables.md:28 | 1078 | 円/日 | 一致 |  |
| 192 | +606 | 円/日 | break_off/fam_tables.md:28 | 606 | 円/日 | 一致 |  |
| 192 | +574 | 円/日 | break_off/fam_tables.md:28 | 574 | 円/日 | 一致 |  |
| 192 | +637 | 円/日 | break_off/fam_tables.md:28 | 637 | 円/日 | 一致 |  |
| 192 | +18.4 | 円(1 本) | break_off/levels_reason.out:3 | 18.4 | 円(1 本) | 一致 |  |
| 192 | +68.2 | 円(1 本) | break_off/levels_reason.out:3 | 68.2 | 円(1 本) | 一致 |  |
| 193 | −215 | 円/日 | break_off/fam_tables.md:29 | -215 | 円/日 | 一致 |  |
| 193 | −447 | 円/日 | break_off/fam_tables.md:29 | -447 | 円/日 | 一致 |  |
| 193 | +4 | 円/日 | break_off/fam_tables.md:29 | 4 | 円/日 | 一致 |  |
| 193 | −719 | 円/日 | break_off/fam_tables.md:29 | -719 | 円/日 | 一致 |  |
| 193 | −868 | 円/日 | break_off/fam_tables.md:29 | -868 | 円/日 | 一致 |  |
| 193 | −579 | 円/日 | break_off/fam_tables.md:29 | -579 | 円/日 | 一致 |  |
| 193 | +19.6 | 円(1 本) | break_off/levels_reason.out:5 | 19.6 | 円(1 本) | 一致 |  |
| 193 | +13.6 | 円(1 本) | break_off/levels_reason.out:5 | 13.6 | 円(1 本) | 一致 |  |
| 193 | −1,242.8 | 円(1 本) | break_off/levels_reason.out:6 | -1242.8 | 円(1 本) | 一致 |  |
| 194 | +329 | 円/日 | break_off/fam_tables.md:30 | 329 | 円/日 | 一致 |  |
| 194 | +274 | 円/日 | break_off/fam_tables.md:30 | 274 | 円/日 | 一致 |  |
| 194 | +378 | 円/日 | break_off/fam_tables.md:30 | 378 | 円/日 | 一致 |  |
| 194 | +117 | 円/日 | break_off/fam_tables.md:30 | 117 | 円/日 | 一致 |  |
| 194 | +92 | 円/日 | break_off/fam_tables.md:30 | 92 | 円/日 | 一致 |  |
| 194 | +141 | 円/日 | break_off/fam_tables.md:30 | 141 | 円/日 | 一致 |  |
| 194 | +17.2 | 円(1 本) | break_off/levels_reason.out:9 | 17.2 | 円(1 本) | 一致 |  |
| 194 | +61.7 | 円(1 本) | break_off/levels_reason.out:9 | 61.7 | 円(1 本) | 一致 |  |
| 195 | +33 | 円/日 | break_off/fam_tables.md:31 | 33 | 円/日 | 一致 |  |
| 195 | −100 | 円/日 | break_off/fam_tables.md:31 | -100 | 円/日 | 一致 |  |
| 195 | +167 | 円/日 | break_off/fam_tables.md:31 | 167 | 円/日 | 一致 |  |
| 195 | −390 | 円/日 | break_off/fam_tables.md:31 | -390 | 円/日 | 一致 |  |
| 195 | −474 | 円/日 | break_off/fam_tables.md:31 | -474 | 円/日 | 一致 |  |
| 195 | −302 | 円/日 | break_off/fam_tables.md:31 | -302 | 円/日 | 一致 |  |
| 195 | +18.6 | 円(1 本) | break_off/levels_reason.out:13 | 18.6 | 円(1 本) | 一致 |  |
| 195 | +67.0 | 円(1 本) | break_off/levels_reason.out:13 | 67 | 円(1 本) | 一致 |  |
| 195 | −291.7 | 円(1 本) | break_off/levels_reason.out:15 | -291.7 | 円(1 本) | 一致 |  |
| 197 | +15.3 | 円 | break_off/compare.md:21(利確 1 本) | 15.3 | 円 | 一致 |  |
| 197 | +14.3 | 円 | break_off/diag_tables.json:.d3.groups.出の理由.close.lo | 0.716699(× 20 = 14.33) | bp(口座) | 単位の誤り(出所の指し方) |  |
| 197 | +16.2 | 円 | break_off/diag_tables.json:.d3.groups.出の理由.close.hi | 0.810069(× 20 = 16.20) | bp(口座) | 単位の誤り(出所の指し方) |  |
| 197 | −1,257.6 | 円 | break_off/compare.md:21(成行 1 本) | -1257.6 | 円 | 一致 |  |
| 197 | −1,360.8 | 円 | break_off/diag_tables.json:.d3.groups.出の理由.market.lo | -68.0393(× 20 = -1,360.79) | bp(口座) | 単位の誤り(出所の指し方) |  |
| 197 | −1,157.2 | 円 | break_off/diag_tables.json:.d3.groups.出の理由.market.hi | -57.8618(× 20 = -1,157.24) | bp(口座) | 単位の誤り(出所の指し方) |  |
| 197 | +36.4 | 円 | break_off/compare.md:20 | 36.4 | 円 | 一致 |  |
| 197 | −258.8 | 円 | break_off/compare.md:20 | -258.8 | 円 | 一致 |  |
| 197 | −315.2 | 円 | break_off/compare.md:20 | -315.2 | 円 | 一致 |  |
| 197 | −5,439,000 | 円(約) | 計算 4,325 × −1,257.6(compare.md:21)= −5,439,120 を千の位に丸め | −5,439,120 | 計算(円) | 出所が無い(計算で再現) | 文書は「約」と式を書いている。式の値 −5,439,120・json の market の和 −271,955.478 × 20 = −5,439,109.6 のどちらも千の位で −5,439,000 |
| 197 | −1,257.6 | 円 | break_off/compare.md:21(成行 1 本) | -1257.6 | 円 | 一致 |  |
| 198 | +1,193,340 | 円 | break_off/diag_tables.json:.d3.top5_days_sum | 59667(× 20 = 1,193,340.17) | bp(口座) | 単位の誤り(出所の指し方) | 円の写しは fam_tables.md:35 |
| 198 | −1,345,377 | 円 | break_off/diag_tables.json:.d3.bottom5_days_sum | -67268.8(× 20 = -1,345,376.68) | bp(口座) | 単位の誤り(出所の指し方) | 円の写しは fam_tables.md:35 |
| 198 | +990,576 | 円 | break_off/compare.md:21 | 990576 | 円 | 一致 |  |
| 198 | +653,497 | 円 | base/diag_tables.json:.d3.top5_days_sum | 32674.9(× 20 = 653,497.39) | bp(口座) | 単位の誤り(出所の指し方) | 円の写しは fam_tables.md:36 |
| 198 | −766,805 | 円 | base/diag_tables.json:.d3.bottom5_days_sum | -38340.3(× 20 = -766,805.01) | bp(口座) | 単位の誤り(出所の指し方) | 円の写しは fam_tables.md:36 |
| 199 | −50.60 | bp(口座) | break_off/diag_tables.json:.d3.trade_quantiles.0.01 | -50.6039 | bp(口座) | 一致 |  |
| 199 | −1,012 | 円 | break_off/diag_tables.json:.d3.trade_quantiles.0.01 | -50.6039(× 20 = -1,012.08) | bp(口座) | 一致 | 行に「bp。× 20 = 円」と書いてある |
| 199 | −6.10 | bp(口座) | break_off/diag_tables.json:.d3.trade_quantiles.0.05 | -6.10417 | bp(口座) | 一致 |  |
| 199 | +0.39 | bp(口座) | break_off/diag_tables.json:.d3.trade_quantiles.0.25 | 0.3857 | bp(口座) | 一致 |  |
| 199 | +0.91 | bp(口座) | break_off/diag_tables.json:.d3.trade_quantiles.0.5 | 0.9057 | bp(口座) | 一致 |  |
| 199 | +2.22 | bp(口座) | break_off/diag_tables.json:.d3.trade_quantiles.0.75 | 2.21727 | bp(口座) | 一致 |  |
| 199 | +7.41 | bp(口座) | break_off/diag_tables.json:.d3.trade_quantiles.0.95 | 7.413 | bp(口座) | 一致 |  |
| 199 | +16.11 | bp(口座) | break_off/diag_tables.json:.d3.trade_quantiles.0.99 | 16.1062 | bp(口座) | 一致 |  |
| 199 | −33.70 | bp(口座) | base/diag_tables.json:.d3.trade_quantiles.0.01 | -33.6975 | bp(口座) | 一致 |  |
| 199 | −674 | 円 | base/diag_tables.json:.d3.trade_quantiles.0.01 | -33.6975(× 20 = -673.95) | bp(口座) | 一致 | 行に「bp。× 20 = 円」と書いてある |
| 199 | −10.40 | bp(口座) | base/diag_tables.json:.d3.trade_quantiles.0.05 | -10.404 | bp(口座) | 一致 |  |
| 199 | +0.77 | bp(口座) | base/diag_tables.json:.d3.trade_quantiles.0.5 | 0.7716 | bp(口座) | 一致 |  |
| 199 | +13.86 | bp(口座) | base/diag_tables.json:.d3.trade_quantiles.0.99 | 13.8556 | bp(口座) | 一致 |  |
| 200 | −1,682.9 | 円(1 本) | break_off/break_off_detail.out:3 | -1682.9 | 円 | 一致 |  |
| 200 | −1,381.0 | 円(1 本) | break_off/break_off_detail.out:8 | -1381 | 円 | 一致 |  |
| 200 | −1,270.0 | 円(1 本) | break_off/break_off_detail.out:3 | -1270 | 円 | 一致 |  |
| 200 | −1,580.6 | 円(1 本) | break_off/break_off_detail.out:8 | -1580.6 | 円 | 一致 |  |
| 200 | −273.7 | 円(1 本) | break_off/break_off_detail.out:3 | -273.7 | 円 | 一致 |  |
| 200 | −433.6 | 円(1 本) | break_off/break_off_detail.out:8 | -433.6 | 円 | 一致 |  |
| 200 | −1,258 | 円 | break_off/compare.md:21(成行 1 本) | -1257.6 | 円 | 一致 |  |
| 201 | +36.4 | 円 | break_off/compare.md:20 | 36.4 | 円 | 一致 |  |
| 201 | +15.3 | 円 | break_off/compare.md:21 | 15.3 | 円 | 一致 |  |
| 201 | +67.0 | 円 | break_off/levels_reason.out:13 | 67 | 円 | 一致 |  |
| 201 | +13.6 | 円 | break_off/levels_reason.out:5 | 13.6 | 円 | 一致 |  |
| 201 | −1,258 | 円 | break_off/compare.md:21 | -1257.6 | 円 | 一致 |  |
| 201 | +1,002 | 円/日 | break_off/fam_tables.md:28 | 1002 | 円/日 | 一致 |  |
| 201 | +606 | 円/日 | break_off/fam_tables.md:28 | 606 | 円/日 | 一致 |  |
| 201 | +329 | 円/日 | break_off/fam_tables.md:30 | 329 | 円/日 | 一致 |  |
| 201 | +117 | 円/日 | break_off/fam_tables.md:30 | 117 | 円/日 | 一致 |  |
| 223 | +14,828,260 | 円 | break_off/diag_paths.json:.d4.groups.勝った.pnl_sum | 741413(× 20 = 14,828,260.00) | bp(口座) | 単位の誤り(出所の指し方) | 節(219 行)は break_off/diag_paths.md を名指して「和は円」と書き、× 20 を書いていない(円の写しは fam_tables.md:42-48) |
| 223 | 5.82 | move_bp | break_off/diag_paths.json:.d4.groups.勝った.mfe_median | 5.82058 | move_bp | 一致 |  |
| 223 | −5.86 | move_bp | break_off/diag_paths.json:.d4.groups.勝った.mae_median | -5.85984 | move_bp | 一致 |  |
| 223 | +10,177,344 | 円 | base/diag_paths.json:.d4.groups.勝った.pnl_sum | 508867(× 20 = 10,177,343.87) | bp(口座) | 単位の誤り(出所の指し方) | 節(219 行)は break_off/diag_paths.md を名指して「和は円」と書き、× 20 を書いていない(円の写しは fam_tables.md:42-48) |
| 223 | 6.02 | move_bp | base/diag_paths.json:.d4.groups.勝った.mfe_median | 6.02168 | move_bp | 一致 |  |
| 223 | −4.74 | move_bp | base/diag_paths.json:.d4.groups.勝った.mae_median | -4.74403 | move_bp | 一致 |  |
| 224 | −6,512,367 | 円 | break_off/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた.pnl_sum | -325618(× 20 = -6,512,367.08) | bp(口座) | 単位の誤り(出所の指し方) | 節(219 行)は break_off/diag_paths.md を名指して「和は円」と書き、× 20 を書いていない(円の写しは fam_tables.md:42-48) |
| 224 | 2.24 | move_bp | break_off/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた.mfe_median | 2.23712 | move_bp | 一致 |  |
| 224 | −64.81 | move_bp | break_off/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた.mae_median | -64.8113 | move_bp | 一致 |  |
| 224 | −4,695,044 | 円 | base/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた.pnl_sum | -234752(× 20 = -4,695,043.87) | bp(口座) | 単位の誤り(出所の指し方) | 節(219 行)は break_off/diag_paths.md を名指して「和は円」と書き、× 20 を書いていない(円の写しは fam_tables.md:42-48) |
| 224 | 2.05 | move_bp | base/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた.mfe_median | 2.05371 | move_bp | 一致 |  |
| 224 | −30.50 | move_bp | base/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた.mae_median | -30.4965 | move_bp | 一致 |  |
| 225 | −9,688,250 | 円 | break_off/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた.pnl_sum | -484412(× 20 = -9,688,249.56) | bp(口座) | 単位の誤り(出所の指し方) | 節(219 行)は break_off/diag_paths.md を名指して「和は円」と書き、× 20 を書いていない(円の写しは fam_tables.md:42-48) |
| 225 | −3.52 | move_bp | break_off/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた.mfe_median | -3.52332 | move_bp | 一致 |  |
| 225 | −68.40 | move_bp | break_off/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた.mae_median | -68.4036 | move_bp | 一致 |  |
| 225 | −6,006,006 | 円 | base/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた.pnl_sum | -300300(× 20 = -6,006,005.81) | bp(口座) | 単位の誤り(出所の指し方) | 節(219 行)は break_off/diag_paths.md を名指して「和は円」と書き、× 20 を書いていない(円の写しは fam_tables.md:42-48) |
| 225 | −2.77 | move_bp | base/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた.mfe_median | -2.77315 | move_bp | 一致 |  |
| 225 | −32.38 | move_bp | base/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた.mae_median | -32.3832 | move_bp | 一致 |  |
| 227 | −0.28 | move_bp | break_off/diag_paths.json:.d4.after_exit.5.per_trade | -0.281775 | move_bp | 一致 |  |
| 227 | −0.39 | move_bp | break_off/diag_paths.json:.d4.after_exit.5.lo | -0.388804 | move_bp | 一致 |  |
| 227 | −0.18 | move_bp | break_off/diag_paths.json:.d4.after_exit.5.hi | -0.177676 | move_bp | 一致 |  |
| 227 | −0.52 | move_bp | break_off/diag_paths.json:.d4.after_exit.15.per_trade | -0.520718 | move_bp | 一致 |  |
| 227 | −0.76 | move_bp | break_off/diag_paths.json:.d4.after_exit.15.lo | -0.762234 | move_bp | 一致 |  |
| 227 | −0.30 | move_bp | break_off/diag_paths.json:.d4.after_exit.15.hi | -0.304135 | move_bp | 一致 |  |
| 227 | −0.10 | move_bp | break_off/diag_paths.json:.d4.after_exit.60.per_trade | -0.098547 | move_bp | 一致 |  |
| 227 | −0.56 | move_bp | break_off/diag_paths.json:.d4.after_exit.60.lo | -0.557899 | move_bp | 一致 |  |
| 227 | +0.31 | move_bp | break_off/diag_paths.json:.d4.after_exit.60.hi | 0.314135 | move_bp | 一致 |  |
| 227 | −0.34 | move_bp | base/diag_paths.json:.d4.after_exit.5.per_trade | -0.335294 | move_bp | 一致 |  |
| 227 | −0.66 | move_bp | base/diag_paths.json:.d4.after_exit.15.per_trade | -0.656481 | move_bp | 一致 |  |
| 227 | −0.42 | move_bp | base/diag_paths.json:.d4.after_exit.60.per_trade | -0.419486 | move_bp | 一致 |  |
| 228 | −30 | move_bp | base/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた.mae_median | -30.4965 | move_bp | 一致 |  |
| 228 | −32 | move_bp | base/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた.mae_median | -32.3832 | move_bp | 一致 |  |
| 228 | −65 | move_bp | break_off/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた.mae_median | -64.8113 | move_bp | 一致 |  |
| 228 | −68 | move_bp | break_off/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた.mae_median | -68.4036 | move_bp | 一致 |  |
| 228 | −10,701,050 | 円 | 計算 base/diag_paths.json 負けた 2 群の pnl_sum の和 × 20 | -10,701,049.68 | 計算(円) | 出所が無い(計算で再現) |  |
| 228 | −16,200,617 | 円 | 計算 break_off/diag_paths.json 負けた 2 群の pnl_sum の和 × 20 | -16,200,616.63 | 計算(円) | 出所が無い(計算で再現) |  |
| 228 | +10,177,344 | 円 | base/diag_paths.json:.d4.groups.勝った.pnl_sum | 508867(× 20 = 10,177,343.87) | bp(口座) | 単位の誤り(出所の指し方) | 節(219 行)は break_off/diag_paths.md を名指して「和は円」と書き、× 20 を書いていない(円の写しは fam_tables.md:42-48) |
| 228 | +14,828,260 | 円 | break_off/diag_paths.json:.d4.groups.勝った.pnl_sum | 741413(× 20 = 14,828,260.00) | bp(口座) | 単位の誤り(出所の指し方) | 節(219 行)は break_off/diag_paths.md を名指して「和は円」と書き、× 20 を書いていない(円の写しは fam_tables.md:42-48) |
| 246 | −0.22 | move_bp | break_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).1.signal.per_trade | -0.216617 | move_bp | 一致 |  |
| 246 | −0.27 | move_bp | break_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).1.signal.lo | -0.266334 | move_bp | 一致 |  |
| 246 | −0.17 | move_bp | break_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).1.signal.hi | -0.166082 | move_bp | 一致 |  |
| 246 | −0.45 | move_bp | break_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).5.signal.per_trade | -0.447173 | move_bp | 一致 |  |
| 246 | −0.56 | move_bp | break_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).5.signal.lo | -0.561254 | move_bp | 一致 |  |
| 246 | −0.32 | move_bp | break_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).5.signal.hi | -0.320244 | move_bp | 一致 |  |
| 246 | −0.65 | move_bp | break_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).15.signal.per_trade | -0.650527 | move_bp | 一致 |  |
| 246 | −0.89 | move_bp | break_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).15.signal.lo | -0.888416 | move_bp | 一致 |  |
| 246 | −0.43 | move_bp | break_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).15.signal.hi | -0.42648 | move_bp | 一致 |  |
| 246 | −0.35 | move_bp | break_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.signal.per_trade | -0.353906 | move_bp | 一致 |  |
| 246 | −0.85 | move_bp | break_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.signal.lo | -0.847687 | move_bp | 一致 |  |
| 246 | +0.08 | move_bp | break_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.signal.hi | 0.07591 | move_bp | 一致 |  |
| 246 | −0.25 | move_bp | base/diag_paths.json:.d5.建て起点.1.signal.per_trade | -0.253716 | move_bp | 一致 |  |
| 246 | −0.51 | move_bp | base/diag_paths.json:.d5.建て起点.5.signal.per_trade | -0.508002 | move_bp | 一致 |  |
| 246 | −0.74 | move_bp | base/diag_paths.json:.d5.建て起点.15.signal.per_trade | -0.74338 | move_bp | 一致 |  |
| 246 | −0.58 | move_bp | base/diag_paths.json:.d5.建て起点.60.signal.per_trade | -0.575653 | move_bp | 一致 |  |
| 246 | −1.10 | move_bp | base/diag_paths.json:.d5.建て起点.60.signal.lo | -1.09528 | move_bp | 一致 |  |
| 246 | −0.13 | move_bp | base/diag_paths.json:.d5.建て起点.60.signal.hi | -0.129566 | move_bp | 一致 |  |
| 248 | +0.67 | move_bp | break_off/diag_paths.json:.d5.建て起点.60.control_24h.per_trade | 0.671308 | move_bp | 一致 |  |
| 263 | +4.6 | 円(1 取引) | break_off/diag_tables.json:.d6.groups.〜1 分.per_trade | 0.230266(× 20 = 4.61) | bp(口座) | 単位の誤り(出所の指し方) | 節(263 行)は読み口の「D6 固まり」(bp)だけを名指して「円」と書き、× 20 も写しも書いていない(円の値は fam_tables.md:65-66) |
| 263 | +3.0 | 円(1 取引) | break_off/diag_tables.json:.d6.groups.〜1 分.lo | 0.148531(× 20 = 2.97) | bp(口座) | 単位の誤り(出所の指し方) | 節(263 行)は読み口の「D6 固まり」(bp)だけを名指して「円」と書き、× 20 も写しも書いていない(円の値は fam_tables.md:65-66) |
| 263 | +6.2 | 円(1 取引) | break_off/diag_tables.json:.d6.groups.〜1 分.hi | 0.307962(× 20 = 6.16) | bp(口座) | 単位の誤り(出所の指し方) | 節(263 行)は読み口の「D6 固まり」(bp)だけを名指して「円」と書き、× 20 も写しも書いていない(円の値は fam_tables.md:65-66) |
| 263 | +1.7 | 円(1 取引) | break_off/diag_tables.json:.d6.groups.1 分超〜2 分.per_trade | 0.0845468(× 20 = 1.69) | bp(口座) | 単位の誤り(出所の指し方) | 節(263 行)は読み口の「D6 固まり」(bp)だけを名指して「円」と書き、× 20 も写しも書いていない(円の値は fam_tables.md:65-66) |
| 263 | −0.7 | 円(1 取引) | break_off/diag_tables.json:.d6.groups.1 分超〜2 分.lo | -0.0366173(× 20 = -0.73) | bp(口座) | 単位の誤り(出所の指し方) | 節(263 行)は読み口の「D6 固まり」(bp)だけを名指して「円」と書き、× 20 も写しも書いていない(円の値は fam_tables.md:65-66) |
| 263 | +4.0 | 円(1 取引) | break_off/diag_tables.json:.d6.groups.1 分超〜2 分.hi | 0.199336(× 20 = 3.99) | bp(口座) | 単位の誤り(出所の指し方) | 節(263 行)は読み口の「D6 固まり」(bp)だけを名指して「円」と書き、× 20 も写しも書いていない(円の値は fam_tables.md:65-66) |
| 263 | +1.8 | 円(1 取引) | break_off/diag_tables.json:.d6.groups.2 分超〜7 分.per_trade | 0.0923386(× 20 = 1.85) | bp(口座) | 単位の誤り(出所の指し方) | 節(263 行)は読み口の「D6 固まり」(bp)だけを名指して「円」と書き、× 20 も写しも書いていない(円の値は fam_tables.md:65-66) |
| 263 | +0.1 | 円(1 取引) | break_off/diag_tables.json:.d6.groups.2 分超〜7 分.lo | 0.00703688(× 20 = 0.14) | bp(口座) | 単位の誤り(出所の指し方) | 節(263 行)は読み口の「D6 固まり」(bp)だけを名指して「円」と書き、× 20 も写しも書いていない(円の値は fam_tables.md:65-66) |
| 263 | +3.6 | 円(1 取引) | break_off/diag_tables.json:.d6.groups.2 分超〜7 分.hi | 0.179263(× 20 = 3.59) | bp(口座) | 単位の誤り(出所の指し方) | 節(263 行)は読み口の「D6 固まり」(bp)だけを名指して「円」と書き、× 20 も写しも書いていない(円の値は fam_tables.md:65-66) |
| 263 | −1.1 | 円(1 取引) | break_off/diag_tables.json:.d6.groups.7 分超.per_trade | -0.0552657(× 20 = -1.11) | bp(口座) | 単位の誤り(出所の指し方) | 節(263 行)は読み口の「D6 固まり」(bp)だけを名指して「円」と書き、× 20 も写しも書いていない(円の値は fam_tables.md:65-66) |
| 263 | −3.2 | 円(1 取引) | break_off/diag_tables.json:.d6.groups.7 分超.lo | -0.158322(× 20 = -3.17) | bp(口座) | 単位の誤り(出所の指し方) | 節(263 行)は読み口の「D6 固まり」(bp)だけを名指して「円」と書き、× 20 も写しも書いていない(円の値は fam_tables.md:65-66) |
| 263 | +0.8 | 円(1 取引) | break_off/diag_tables.json:.d6.groups.7 分超.hi | 0.0387223(× 20 = 0.77) | bp(口座) | 単位の誤り(出所の指し方) | 節(263 行)は読み口の「D6 固まり」(bp)だけを名指して「円」と書き、× 20 も写しも書いていない(円の値は fam_tables.md:65-66) |
| 263 | +2.4 | 円(1 取引) | base/diag_tables.json:.d6.groups.〜1 分.per_trade | 0.117982(× 20 = 2.36) | bp(口座) | 単位の誤り(出所の指し方) | 節(263 行)は読み口の「D6 固まり」(bp)だけを名指して「円」と書き、× 20 も写しも書いていない(円の値は fam_tables.md:65-66) |
| 263 | +1.3 | 円(1 取引) | base/diag_tables.json:.d6.groups.〜1 分.lo | 0.0674201(× 20 = 1.35) | bp(口座) | 単位の誤り(出所の指し方) | 節(263 行)は読み口の「D6 固まり」(bp)だけを名指して「円」と書き、× 20 も写しも書いていない(円の値は fam_tables.md:65-66) |
| 263 | +3.3 | 円(1 取引) | base/diag_tables.json:.d6.groups.〜1 分.hi | 0.167303(× 20 = 3.35) | bp(口座) | 単位の誤り(出所の指し方) | 節(263 行)は読み口の「D6 固まり」(bp)だけを名指して「円」と書き、× 20 も写しも書いていない(円の値は fam_tables.md:65-66) |
| 263 | −2.0 | 円(1 取引) | base/diag_tables.json:.d6.groups.3 分超〜11 分.per_trade | -0.100096(× 20 = -2.00) | bp(口座) | 単位の誤り(出所の指し方) | 節(263 行)は読み口の「D6 固まり」(bp)だけを名指して「円」と書き、× 20 も写しも書いていない(円の値は fam_tables.md:65-66) |
| 263 | −3.2 | 円(1 取引) | base/diag_tables.json:.d6.groups.3 分超〜11 分.lo | -0.161759(× 20 = -3.24) | bp(口座) | 単位の誤り(出所の指し方) | 節(263 行)は読み口の「D6 固まり」(bp)だけを名指して「円」と書き、× 20 も写しも書いていない(円の値は fam_tables.md:65-66) |
| 263 | −0.8 | 円(1 取引) | base/diag_tables.json:.d6.groups.3 分超〜11 分.hi | -0.0400397(× 20 = -0.80) | bp(口座) | 単位の誤り(出所の指し方) | 節(263 行)は読み口の「D6 固まり」(bp)だけを名指して「円」と書き、× 20 も写しも書いていない(円の値は fam_tables.md:65-66) |
| 286 | +292.3 | 円/日 | break_off/diag_tables.json:.d7.all.mean | 14.617(× 20 = 292.34) | bp/日(口座) | 一致 |  |
| 286 | +175.6 | 円/日 | break_off/diag_tables.json:.d7.all.lo | 8.78142(× 20 = 175.63) | bp/日(口座) | 一致 |  |
| 286 | +416.6 | 円/日 | break_off/diag_tables.json:.d7.all.hi | 20.8289(× 20 = 416.58) | bp/日(口座) | 一致 |  |
| 286 | 175.6 | 円/日 | break_off/diag_tables.json:.d7.all.mde | 8.7787(× 20 = 175.57) | bp/日(口座) | 一致 |  |
| 287 | +424 | 円/日 | break_off/fam_tables.md:72 | 424 | 円/日 | 一致 |  |
| 287 | +235 | 円/日 | break_off/fam_tables.md:72 | 235 | 円/日 | 一致 |  |
| 287 | +634 | 円/日 | break_off/fam_tables.md:72 | 634 | 円/日 | 一致 |  |
| 287 | 289 | 円/日 | break_off/fam_tables.md:72 | 289 | 円/日 | 一致 |  |
| 288 | +160 | 円/日 | break_off/fam_tables.md:72 | 160 | 円/日 | 一致 |  |
| 288 | +21 | 円/日 | break_off/fam_tables.md:72 | 21 | 円/日 | 一致 |  |
| 288 | +289 | 円/日 | break_off/fam_tables.md:72 | 289 | 円/日 | 一致 |  |
| 288 | 192 | 円/日 | break_off/fam_tables.md:72 | 192 | 円/日 | 一致 |  |
| 290 | −781 | 円/日 | break_off/diag_tables.json:.d7.years.2015.mean | -39.0478(× 20 = -780.96) | bp/日(口座) | 一致 |  |
| 290 | −244 | 円/日 | break_off/diag_tables.json:.d7.years.2016.mean | -12.186(× 20 = -243.72) | bp/日(口座) | 一致 |  |
| 290 | +1,402 | 円/日 | break_off/diag_tables.json:.d7.years.2017.mean | 70.0983(× 20 = 1,401.97) | bp/日(口座) | 一致 |  |
| 290 | +439 | 円/日 | break_off/diag_tables.json:.d7.years.2018.mean | 21.9499(× 20 = 439.00) | bp/日(口座) | 一致 |  |
| 290 | +210 | 円/日 | break_off/diag_tables.json:.d7.years.2019.mean | 10.5038(× 20 = 210.08) | bp/日(口座) | 一致 |  |
| 290 | +425 | 円/日 | break_off/diag_tables.json:.d7.years.2020.mean | 21.2465(× 20 = 424.93) | bp/日(口座) | 一致 |  |
| 290 | +216 | 円/日 | break_off/diag_tables.json:.d7.years.2021.mean | 10.8049(× 20 = 216.10) | bp/日(口座) | 一致 |  |
| 290 | +51 | 円/日 | break_off/diag_tables.json:.d7.years.2022.mean | 2.56997(× 20 = 51.40) | bp/日(口座) | 一致 |  |
| 290 | −83 | 円/日 | break_off/diag_tables.json:.d7.years.2023.mean | -4.15862(× 20 = -83.17) | bp/日(口座) | 一致 |  |
| 292 | +476,917 | 円 | break_off/fam_tables.md:84 | 476917 | 円 | 一致 |  |
| 292 | +366,364 | 円 | break_off/fam_tables.md:84 | 366364 | 円 | 一致 |  |
| 292 | −15,906 | 円 | break_off/fam_tables.md:84 | -15906 | 円 | 一致 |  |
| 294 | +245 | 円/日 | 計算 break_off/band_migration.out:3,4 の差の和 (352,867 + 7,189) ÷ 1,469 | 245.10 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 294 | +240 | 円/日 | break_off/band_migration.out:3 | 240 | 円/日 | 一致 |  |
| 294 | +5 | 円/日 | break_off/band_migration.out:4 | 5 | 円/日 | 一致 |  |
| 294 | +2 | 円/日 | 計算 break_off/band_migration.out:5,8 の差の和 (91 + 2,585) ÷ 1,469 | 1.82 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 294 | +178 | 円/日 | 計算 break_off/band_migration.out:6,7,9 の差の和 260,607 ÷ 1,469 | 177.40 | 計算(円/日) | 値の誤り(丸めた値どうしの計算) | 出所の精度では +177.4 → +177。文書は丸めた升目 +48 + 28 + 102 = +178 の和 |
| 294 | +48 | 円/日 | break_off/band_migration.out:6 | 48 | 円/日 | 一致 |  |
| 294 | +28 | 円/日 | break_off/band_migration.out:7 | 28 | 円/日 | 一致 |  |
| 294 | +102 | 円/日 | break_off/band_migration.out:9 | 102 | 円/日 | 一致 |  |
| 294 | +5 | 円/日 | 計算 break_off/band_migration.out:10,11 の差の和 (194,885 − 188,577) ÷ 1,470 | 4.29 | 計算(円/日) | 値の誤り(丸めた値どうしの計算) | 出所の精度では +4.29 → +4。文書は丸めた升目 +133 − 128 = +5 の差 |
| 294 | +133 | 円/日 | break_off/band_migration.out:10 | 133 | 円/日 | 一致 |  |
| 294 | −128 | 円/日 | break_off/band_migration.out:11 | -128 | 円/日 | 一致 |  |
| 294 | +9 | 円/日 | 計算 break_off/band_migration.out:12,15 の差の和 (1,654 + 11,575) ÷ 1,470 | 9.00 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 294 | +147 | 円/日 | 計算 break_off/band_migration.out:13,14,16 の差の和 216,311 ÷ 1,470 | 147.15 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 294 | +33 | 円/日 | break_off/band_migration.out:13 | 33 | 円/日 | 一致 |  |
| 294 | +6 | 円/日 | break_off/band_migration.out:14 | 6 | 円/日 | 一致 |  |
| 294 | +108 | 円/日 | break_off/band_migration.out:16 | 108 | 円/日 | 一致 |  |
| 294 | +425 | 円/日 | 計算 break_off/band_migration.out:3-9 の差の和 623,339 ÷ 1,469 | 424.33 | 計算(円/日) | 値の誤り(丸めた値どうしの計算) | 出所の精度では +424.3 → +424(D7 の前半 +424 と合う)。文書は丸めた升目 7 つの和 +425。文書の「D7 と合う」は丸めの和では 1 ずれている |
| 294 | +161 | 円/日 | 計算 break_off/band_migration.out:10-16 の差の和 235,848 ÷ 1,470 | 160.44 | 計算(円/日) | 値の誤り(丸めた値どうしの計算) | 出所の精度では +160.4 → +160(D7 の後半 +160 と合う)。文書は丸めた升目 7 つの和 +161。文書の「D7 と合う」は丸めの和では 1 ずれている |
| 300 | −330.1 | 円(1 本) | break_off/held_reason.out:1 | -330.1 | 円 | 一致 |  |
| 300 | −218.4 | 円(1 本) | break_off/held_reason.out:1 | -218.4 | 円 | 一致 |  |
| 300 | +1,020 | 円/日 | break_off/held_reason.out:1 | 1020 | 円/日 | 一致 |  |
| 300 | −263.8 | 円(1 本) | break_off/held_reason.out:5 | -263.8 | 円 | 一致 |  |
| 300 | −170.3 | 円(1 本) | break_off/held_reason.out:5 | -170.3 | 円 | 一致 |  |
| 300 | +978 | 円/日 | break_off/held_reason.out:5 | 977.5 | 円/日 | 確かめられない(丸めの境) | 出所の表示 +977.5(小数 1 桁)で、整数への丸めが決まらない |
| 301 | −469.5 | 円(1 本) | break_off/held_reason.out:2 | -469.5 | 円 | 一致 |  |
| 301 | −1,611.0 | 円(1 本) | break_off/held_reason.out:2 | -1611 | 円 | 一致 |  |
| 301 | −911 | 円/日 | break_off/held_reason.out:2 | -910.7 | 円/日 | 一致 |  |
| 301 | −421.4 | 円(1 本) | break_off/held_reason.out:6 | -421.4 | 円 | 一致 |  |
| 301 | −1,351.0 | 円(1 本) | break_off/held_reason.out:6 | -1351 | 円 | 一致 |  |
| 301 | −864 | 円/日 | break_off/held_reason.out:6 | -863.8 | 円/日 | 一致 |  |
| 302 | +46.7 | 円(1 本) | break_off/held_reason.out:3 | 46.7 | 円 | 一致 |  |
| 302 | +46.6 | 円(1 本) | break_off/held_reason.out:3 | 46.6 | 円 | 一致 |  |
| 302 | −8 | 円/日 | break_off/held_reason.out:3 | -7.8 | 円/日 | 一致 |  |
| 302 | +36.2 | 円(1 本) | break_off/held_reason.out:7 | 36.2 | 円 | 一致 |  |
| 302 | +36.1 | 円(1 本) | break_off/held_reason.out:7 | 36.1 | 円 | 一致 |  |
| 302 | −5 | 円/日 | break_off/held_reason.out:7 | -5.4 | 円/日 | 一致 |  |
| 303 | −76.1 | 円(1 本) | break_off/same_bar_reason.out:1 | -76.1 | 円 | 一致 |  |
| 303 | +113.5 | 円(1 本) | break_off/same_bar_reason.out:1 | 113.5 | 円 | 一致 |  |
| 303 | +48 | 円/日 | break_off/same_bar_reason.out:1 | 47.6 | 円/日 | 一致 |  |
| 303 | −74.1 | 円(1 本) | break_off/same_bar_reason.out:3 | -74.1 | 円 | 一致 |  |
| 303 | +97.2 | 円(1 本) | break_off/same_bar_reason.out:3 | 97.2 | 円 | 一致 |  |
| 303 | +33 | 円/日 | break_off/same_bar_reason.out:3 | 33.2 | 円/日 | 一致 |  |
| 309 | −218.4 | 円(1 本) | break_off/held_reason.out:1 | -218.4 | 円 | 一致 |  |
| 309 | −170.3 | 円(1 本) | break_off/held_reason.out:5 | -170.3 | 円 | 一致 |  |
| 309 | −1,611.0 | 円(1 本) | break_off/held_reason.out:2 | -1611 | 円 | 一致 |  |
| 309 | −1,351.0 | 円(1 本) | break_off/held_reason.out:6 | -1351 | 円 | 一致 |  |
| 310 | −459.7 | 円(1 本) | break_len_mult/held_reason_break_len_mult_4.out:1 | -459.7 | 円 | 一致 |  |
| 310 | −372.0 | 円(1 本) | break_len_mult/held_reason_break_len_mult_4.out:8 | -372 | 円 | 一致 |  |
| 310 | −107 | 円(1 本) | 計算 break_len_mult/held_reason_break_len_mult_4.out:1 −459.7 − (−353.0) | -106.70 | 計算(円) | 出所が無い(計算で再現) |  |
| 310 | −85 | 円(1 本) | 計算 break_len_mult/held_reason_break_len_mult_4.out:8 −372.0 − (−287.4) | -84.60 | 計算(円) | 出所が無い(計算で再現) | 小数 1 桁どうしの差 −84.6(±0.1)で、丸めの境 −84.5 に近い |
| 310 | −84.3 | 円(1 本) | break_len_mult/held_reason_break_len_mult_4.out:2 | -84.3 | 円 | 一致 |  |
| 310 | −82.7 | 円(1 本) | break_len_mult/held_reason_break_len_mult_4.out:9 | -82.7 | 円 | 一致 |  |
| 310 | −747.3 | 円(1 本) | break_len_mult/held_reason_break_len_mult_4.out:3 | -747.3 | 円 | 一致 |  |
| 310 | −798.9 | 円(1 本) | break_len_mult/held_reason_break_len_mult_4.out:10 | -798.9 | 円 | 一致 |  |
| 312 | +424 | 円/日 | break_off/fam_tables.md:72 | 424 | 円/日 | 一致 |  |
| 312 | +235 | 円/日 | break_off/fam_tables.md:72 | 235 | 円/日 | 一致 |  |
| 312 | +634 | 円/日 | break_off/fam_tables.md:72 | 634 | 円/日 | 一致 |  |
| 312 | +160 | 円/日 | break_off/fam_tables.md:72 | 160 | 円/日 | 一致 |  |
| 312 | +21 | 円/日 | break_off/fam_tables.md:72 | 21 | 円/日 | 一致 |  |
| 312 | +289 | 円/日 | break_off/fam_tables.md:72 | 289 | 円/日 | 一致 |  |
| 313 | −218 | 円 | break_off/held_reason.out:1 | -218.4 | 円 | 一致 |  |
| 313 | −170 | 円 | break_off/held_reason.out:5 | -170.3 | 円 | 一致 |  |
| 313 | −330 | 円 | break_off/held_reason.out:1 | -330.1 | 円 | 一致 |  |
| 313 | −264 | 円 | break_off/held_reason.out:5 | -263.8 | 円 | 一致 |  |
| 313 | −1,611 | 円 | break_off/held_reason.out:2 | -1611 | 円 | 一致 |  |
| 313 | −1,351 | 円 | break_off/held_reason.out:6 | -1351 | 円 | 一致 |  |
| 313 | +1,020 | 円/日 | break_off/held_reason.out:1 | 1020 | 円/日 | 一致 |  |
| 313 | +978 | 円/日 | break_off/held_reason.out:5 | 977.5 | 円/日 | 確かめられない(丸めの境) | 出所の表示 +977.5 |
| 313 | −911 | 円/日 | break_off/held_reason.out:2 | -910.7 | 円/日 | 一致 |  |
| 313 | −864 | 円/日 | break_off/held_reason.out:6 | -863.8 | 円/日 | 一致 |  |
| 313 | +109 | 円/日 | 計算 break_off/held_reason.out:1,2 +1020.0 − 910.7 | 109.30 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 313 | +114 | 円/日 | 計算 break_off/held_reason.out:5,6 +977.5 − 863.8 | 113.70 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 313 | +245 | 円/日 | 計算 break_off/band_migration.out:3,4 の差の和 (352,867 + 7,189) ÷ 1,469 | 245.10 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 313 | +5 | 円/日 | 計算 break_off/band_migration.out:10,11 の差の和 (194,885 − 188,577) ÷ 1,470 | 4.29 | 計算(円/日) | 値の誤り(丸めた値どうしの計算) | 出所の精度では +4.29 → +4。文書は丸めた升目 +133 − 128 = +5 の差 |
| 313 | +424 | 円/日 | break_off/fam_tables.md:72 | 424 | 円/日 | 一致 |  |
| 313 | +160 | 円/日 | break_off/fam_tables.md:72 | 160 | 円/日 | 一致 |  |
| 313 | +245 | 円/日 | 計算 break_off/band_migration.out:3,4 の差の和 (352,867 + 7,189) ÷ 1,469 | 245.10 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 313 | +5 | 円/日 | 計算 break_off/band_migration.out:10,11 の差の和 (194,885 − 188,577) ÷ 1,470 | 4.29 | 計算(円/日) | 値の誤り(丸めた値どうしの計算) | 出所の精度では +4.29 → +4。文書は丸めた升目 +133 − 128 = +5 の差 |
| 313 | +178 | 円/日 | 計算 break_off/band_migration.out:6,7,9 の差の和 260,607 ÷ 1,469 | 177.40 | 計算(円/日) | 値の誤り(丸めた値どうしの計算) | 出所の精度では +177.4 → +177。文書は丸めた升目 +48 + 28 + 102 = +178 の和 |
| 313 | +147 | 円/日 | 計算 break_off/band_migration.out:13,14,16 の差の和 216,311 ÷ 1,470 | 147.15 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 314 | +425 | 円/日 | 計算 break_off/band_migration.out:3-9 の差の和 623,339 ÷ 1,469 | 424.33 | 計算(円/日) | 値の誤り(丸めた値どうしの計算) | 出所の精度では +424.3 → +424(D7 の前半 +424 と合う)。文書は丸めた升目 7 つの和 +425。文書の「D7 と合う」は丸めの和では 1 ずれている |
| 314 | +288 | 円/日 | 計算 break_off/band_migration.out:3,6 の差の和 422,850 ÷ 1,469 | 287.85 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 314 | +240 | 円/日 | break_off/band_migration.out:3 | 240 | 円/日 | 一致 |  |
| 314 | +135 | 円/日 | 計算 break_off/band_migration.out:4,7,9 の差の和 197,813 ÷ 1,469 | 134.66 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 314 | +2 | 円/日 | 計算 break_off/band_migration.out:5,8 の差の和 (91 + 2,585) ÷ 1,469 | 1.82 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 314 | +161 | 円/日 | 計算 break_off/band_migration.out:10-16 の差の和 235,848 ÷ 1,470 | 160.44 | 計算(円/日) | 値の誤り(丸めた値どうしの計算) | 出所の精度では +160.4 → +160(D7 の後半 +160 と合う)。文書は丸めた升目 7 つの和 +161。文書の「D7 と合う」は丸めの和では 1 ずれている |
| 314 | +166 | 円/日 | 計算 break_off/band_migration.out:10,13 の差の和 243,722 ÷ 1,470 | 165.80 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 314 | −14 | 円/日 | 計算 break_off/band_migration.out:11,14,16 の差の和 −21,103 ÷ 1,470 | -14.36 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 314 | +9 | 円/日 | 計算 break_off/band_migration.out:12,15 の差の和 (1,654 + 11,575) ÷ 1,470 | 9.00 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 314 | +5 | 円/日 | 計算 break_off/band_migration.out:10,11 の差の和 (194,885 − 188,577) ÷ 1,470 | 4.29 | 計算(円/日) | 値の誤り(丸めた値どうしの計算) | 出所の精度では +4.29 → +4。文書は丸めた升目 +133 − 128 = +5 の差 |
| 314 | +40 | 円/日 | 計算 break_off/band_migration.out:12,13,14 の差の和 58,804 ÷ 1,470 | 40.00 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 314 | +116 | 円/日 | 計算 break_off/band_migration.out:15,16 の差の和 170,736 ÷ 1,470 | 116.15 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 314 | −14 | 円/日 | 計算 break_off/band_migration.out:11,14,16 の差の和 −21,103 ÷ 1,470 | -14.36 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 314 | +108 | 円/日 | break_off/band_migration.out:16 | 108 | 円/日 | 一致 |  |
| 314 | +6 | 円/日 | break_off/band_migration.out:14 | 6 | 円/日 | 一致 |  |
| 314 | −128 | 円/日 | break_off/band_migration.out:11 | -128 | 円/日 | 一致 |  |
| 316 | −84 | 円(1 本) | break_len_mult/held_reason_break_len_mult_4.out:2 | -84.3 | 円 | 一致 |  |
| 316 | −218 | 円(1 本) | break_off/held_reason.out:1 | -218.4 | 円 | 一致 |  |
| 316 | −170 | 円(1 本) | break_off/held_reason.out:5 | -170.3 | 円 | 一致 |  |
| 332 | −112 | 円/日 | break_off/diag_tables.json:.d1.segments.second.mean | -5.61026(× 20 = -112.21) | bp/日(口座) | 一致 |  |
| 332 | −266 | 円/日 | break_off/diag_tables.json:.d1.segments.second.lo | -13.2853(× 20 = -265.71) | bp/日(口座) | 一致 |  |
| 332 | +35 | 円/日 | break_off/diag_tables.json:.d1.segments.second.hi | 1.76715(× 20 = 35.34) | bp/日(口座) | 一致 |  |
| 333 | +424 | 円/日 | break_off/fam_tables.md:72 | 424 | 円/日 | 一致 |  |
| 333 | +160 | 円/日 | break_off/fam_tables.md:72 | 160 | 円/日 | 一致 |  |
| 334 | +245 | 円/日 | 計算 break_off/band_migration.out:3,4 の差の和 (352,867 + 7,189) ÷ 1,469 | 245.10 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 334 | +5 | 円/日 | 計算 break_off/band_migration.out:10,11 の差の和 (194,885 − 188,577) ÷ 1,470 | 4.29 | 計算(円/日) | 値の誤り(丸めた値どうしの計算) | 出所の精度では +4.29 → +4。文書は丸めた升目 +133 − 128 = +5 の差 |
| 334 | +178 | 円/日 | 計算 break_off/band_migration.out:6,7,9 の差の和 260,607 ÷ 1,469 | 177.40 | 計算(円/日) | 値の誤り(丸めた値どうしの計算) | 出所の精度では +177.4 → +177。文書は丸めた升目 +48 + 28 + 102 = +178 の和 |
| 334 | +147 | 円/日 | 計算 break_off/band_migration.out:13,14,16 の差の和 216,311 ÷ 1,470 | 147.15 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 334 | +83 | 円/日 | break_dist/band_migration.out:26 | 83 | 円/日 | 一致 | break_dist_1 の「0 分超 → 0 分超」の升目(台帳 K-342 の「足の後まで持ったままの同じ取引」)。文書の「同じ取引の分」は break_off では同じ取引の 3 升目の和の意味で使っているが、ここは 1 升目(break_dist_1 の同じ取引の 4 升目の和は前半 +101・後半 +2) |
| 334 | −3 | 円/日 | break_dist/band_migration.out:34 | -3 | 円/日 | 一致 | break_dist_1 の「0 分超 → 0 分超」の升目(台帳 K-342 の「足の後まで持ったままの同じ取引」)。文書の「同じ取引の分」は break_off では同じ取引の 3 升目の和の意味で使っているが、ここは 1 升目(break_dist_1 の同じ取引の 4 升目の和は前半 +101・後半 +2) |
| 367 | +424 | 円/日 | break_off/fam_tables.md:72 | 424 | 円/日 | 一致 |  |
| 367 | +160 | 円/日 | break_off/fam_tables.md:72 | 160 | 円/日 | 一致 |  |
| 367 | +109 | 円/日 | 計算 break_off/held_reason.out:1,2 +1020.0 − 910.7 | 109.30 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 367 | +114 | 円/日 | 計算 break_off/held_reason.out:5,6 +977.5 − 863.8 | 113.70 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 367 | +245 | 円/日 | 計算 break_off/band_migration.out:3,4 の差の和 (352,867 + 7,189) ÷ 1,469 | 245.10 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 367 | +5 | 円/日 | 計算 break_off/band_migration.out:10,11 の差の和 (194,885 − 188,577) ÷ 1,470 | 4.29 | 計算(円/日) | 値の誤り(丸めた値どうしの計算) | 出所の精度では +4.29 → +4。文書は丸めた升目 +133 − 128 = +5 の差 |
| 368 | −1,258 | 円 | break_off/compare.md:21 | -1257.6 | 円 | 一致 |  |
| 368 | −1,345,377 | 円 | break_off/fam_tables.md:35 | -1.34538e+06 | 円 | 一致 | この行は文書の節(D3・D4)を指し、ファイルを名指していない。円のファイルにある |
| 369 | +1,343 | 円/日 | break_off/scene_diff.out:8 | 1343 | 円/日 | 一致 |  |
| 369 | +666 | 円/日 | break_off/scene_diff.out:9 | 666 | 円/日 | 一致 |  |
| 369 | −147 | 円/日 | break_off/scene_diff.out:5 | -147 | 円/日 | 一致 |  |
| 370 | +36.4 | 円 | break_off/compare.md:20 | 36.4 | 円 | 一致 |  |
| 370 | +15.3 | 円 | break_off/compare.md:21 | 15.3 | 円 | 一致 |  |
| 370 | +67.0 | 円 | break_off/levels_reason.out:13 | 67 | 円 | 一致 |  |
| 370 | +13.6 | 円 | break_off/levels_reason.out:5 | 13.6 | 円 | 一致 |  |
| 371 | −781 | 円/日 | break_off/fam_tables.md:78 | -781 | 円/日 | 一致 |  |
| 371 | −244 | 円/日 | break_off/fam_tables.md:78 | -244 | 円/日 | 一致 |  |
| 372 | +178 | 円/日 | 計算 break_off/band_migration.out:6,7,9 の差の和 260,607 ÷ 1,469 | 177.40 | 計算(円/日) | 値の誤り(丸めた値どうしの計算) | 出所の精度では +177.4 → +177。文書は丸めた升目 +48 + 28 + 102 = +178 の和 |
| 372 | +147 | 円/日 | 計算 break_off/band_migration.out:13,14,16 の差の和 216,311 ÷ 1,470 | 147.15 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 372 | +245 | 円/日 | 計算 break_off/band_migration.out:3,4 の差の和 (352,867 + 7,189) ÷ 1,469 | 245.10 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 372 | +5 | 円/日 | 計算 break_off/band_migration.out:10,11 の差の和 (194,885 − 188,577) ÷ 1,470 | 4.29 | 計算(円/日) | 値の誤り(丸めた値どうしの計算) | 出所の精度では +4.29 → +4。文書は丸めた升目 +133 − 128 = +5 の差 |
| 396 | +787 | 円/日 | break_off/fam_tables.md:14 | 787 | 円/日 | 一致 |  |
| 396 | +540 | 円/日 | break_off/fam_tables.md:14 | 540 | 円/日 | 一致 |  |
| 396 | +1,035 | 円/日 | break_off/fam_tables.md:14 | 1035 | 円/日 | 一致 |  |
| 396 | −112 | 円/日 | break_off/fam_tables.md:14 | -112 | 円/日 | 一致 |  |
| 396 | −266 | 円/日 | break_off/fam_tables.md:14 | -266 | 円/日 | 一致 |  |
| 396 | +35 | 円/日 | break_off/fam_tables.md:14 | 35 | 円/日 | 一致 |  |
| 397 | +362 | 円/日 | break_off/fam_tables.md:15 | 362 | 円/日 | 一致 |  |
| 397 | +231 | 円/日 | break_off/fam_tables.md:15 | 231 | 円/日 | 一致 |  |
| 397 | +497 | 円/日 | break_off/fam_tables.md:15 | 497 | 円/日 | 一致 |  |
| 397 | −273 | 円/日 | break_off/fam_tables.md:15 | -273 | 円/日 | 一致 |  |
| 397 | −360 | 円/日 | break_off/fam_tables.md:15 | -360 | 円/日 | 一致 |  |
| 397 | −184 | 円/日 | break_off/fam_tables.md:15 | -184 | 円/日 | 一致 |  |
| 406 | −781 | 円/日 | break_off/fam_tables.md:72 | -781 | 円/日 | 一致 |  |
| 406 | +1,402 | 円/日 | break_off/fam_tables.md:72 | 1402 | 円/日 | 一致 |  |
| 410 | +292.3 | 円/日 | break_off/diag_tables.json:.d7.all.mean | 14.617(× 20 = 292.34) | bp/日(口座) | 一致 |  |
| 410 | +175.6 | 円/日 | break_off/diag_tables.json:.d7.all.lo | 8.78142(× 20 = 175.63) | bp/日(口座) | 一致 |  |
| 410 | +416.6 | 円/日 | break_off/diag_tables.json:.d7.all.hi | 20.8289(× 20 = 416.58) | bp/日(口座) | 一致 |  |
| 410 | 175.6 | 円/日 | break_off/diag_tables.json:.d7.all.mde | 8.7787(× 20 = 175.57) | bp/日(口座) | 一致 |  |
| 410 | +424 | 円/日 | break_off/fam_tables.md:72 | 424 | 円/日 | 一致 |  |
| 410 | +235 | 円/日 | break_off/fam_tables.md:72 | 235 | 円/日 | 一致 |  |
| 410 | +634 | 円/日 | break_off/fam_tables.md:72 | 634 | 円/日 | 一致 |  |
| 410 | +160 | 円/日 | break_off/fam_tables.md:72 | 160 | 円/日 | 一致 |  |
| 410 | +21 | 円/日 | break_off/fam_tables.md:72 | 21 | 円/日 | 一致 |  |
| 410 | +289 | 円/日 | break_off/fam_tables.md:72 | 289 | 円/日 | 一致 |  |
| 410 | −244 | 円/日 | break_off/diag_tables.json:.d7.years.2016.mean | -12.186(× 20 = -243.72) | bp/日(口座) | 一致 | 412 行に「年の値は bp/日 × 20」 |
| 410 | +439 | 円/日 | break_off/diag_tables.json:.d7.years.2018.mean | 21.9499(× 20 = 439.00) | bp/日(口座) | 一致 | 412 行に「年の値は bp/日 × 20」 |
| 410 | +425 | 円/日 | break_off/diag_tables.json:.d7.years.2020.mean | 21.2465(× 20 = 424.93) | bp/日(口座) | 一致 | 412 行に「年の値は bp/日 × 20」 |
| 410 | +51 | 円/日 | break_off/diag_tables.json:.d7.years.2022.mean | 2.56997(× 20 = 51.40) | bp/日(口座) | 一致 | 412 行に「年の値は bp/日 × 20」 |
| 410 | −83 | 円/日 | break_off/diag_tables.json:.d7.years.2023.mean | -4.15862(× 20 = -83.17) | bp/日(口座) | 一致 | 412 行に「年の値は bp/日 × 20」 |
| 414 | −112 | 円/日 | break_off/fam_tables.md:14 | -112 | 円/日 | 一致 |  |
| 414 | −266 | 円/日 | break_off/fam_tables.md:14 | -266 | 円/日 | 一致 |  |
| 414 | +35 | 円/日 | break_off/fam_tables.md:14 | 35 | 円/日 | 一致 |  |
| 414 | 216 | 円/日 | break_off/fam_tables.md:14 | 216 | 円/日 | 一致 |  |
| 414 | +424 | 円/日 | break_off/fam_tables.md:72 | 424 | 円/日 | 一致 |  |
| 414 | +235 | 円/日 | break_off/fam_tables.md:72 | 235 | 円/日 | 一致 |  |
| 414 | +634 | 円/日 | break_off/fam_tables.md:72 | 634 | 円/日 | 一致 |  |
| 414 | +160 | 円/日 | break_off/fam_tables.md:72 | 160 | 円/日 | 一致 |  |
| 414 | +21 | 円/日 | break_off/fam_tables.md:72 | 21 | 円/日 | 一致 |  |
| 414 | +289 | 円/日 | break_off/fam_tables.md:72 | 289 | 円/日 | 一致 |  |
| 414 | 289 | 円/日 | break_off/fam_tables.md:72 | 289 | 円/日 | 一致 |  |
| 414 | 192 | 円/日 | break_off/fam_tables.md:72 | 192 | 円/日 | 一致 |  |
| 414 | −218 | 円(1 本) | break_off/held_reason.out:1 | -218.4 | 円 | 一致 |  |
| 414 | −170 | 円(1 本) | break_off/held_reason.out:5 | -170.3 | 円 | 一致 |  |
| 414 | −1,611 | 円(1 本) | break_off/held_reason.out:2 | -1611 | 円 | 一致 |  |
| 414 | −1,351 | 円(1 本) | break_off/held_reason.out:6 | -1351 | 円 | 一致 |  |
| 414 | +109 | 円/日 | 計算 break_off/held_reason.out:1,2 +1020.0 − 910.7 | 109.30 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 414 | +114 | 円/日 | 計算 break_off/held_reason.out:5,6 +977.5 − 863.8 | 113.70 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 414 | +178 | 円/日 | 計算 break_off/band_migration.out:6,7,9 の差の和 260,607 ÷ 1,469 | 177.40 | 計算(円/日) | 値の誤り(丸めた値どうしの計算) | 出所の精度では +177.4 → +177。文書は丸めた升目 +48 + 28 + 102 = +178 の和 |
| 414 | +147 | 円/日 | 計算 break_off/band_migration.out:13,14,16 の差の和 216,311 ÷ 1,470 | 147.15 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 414 | +288 | 円/日 | 計算 break_off/band_migration.out:3,6 の差の和 422,850 ÷ 1,469 | 287.85 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 414 | +240 | 円/日 | break_off/band_migration.out:3 | 240 | 円/日 | 一致 |  |
| 414 | +161 | 円/日 | 計算 break_off/band_migration.out:10-16 の差の和 235,848 ÷ 1,470 | 160.44 | 計算(円/日) | 値の誤り(丸めた値どうしの計算) | 出所の精度では +160.4 → +160(D7 の後半 +160 と合う)。文書は丸めた升目 7 つの和 +161。文書の「D7 と合う」は丸めの和では 1 ずれている |
| 414 | +166 | 円/日 | 計算 break_off/band_migration.out:10,13 の差の和 243,722 ÷ 1,470 | 165.80 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 414 | −14 | 円/日 | 計算 break_off/band_migration.out:11,14,16 の差の和 −21,103 ÷ 1,470 | -14.36 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 414 | +108 | 円/日 | break_off/band_migration.out:16 | 108 | 円/日 | 一致 |  |
| 414 | +6 | 円/日 | break_off/band_migration.out:14 | 6 | 円/日 | 一致 |  |
| 414 | −128 | 円/日 | break_off/band_migration.out:11 | -128 | 円/日 | 一致 |  |
| 414 | +9 | 円/日 | 計算 break_off/band_migration.out:12,15 の差の和 (1,654 + 11,575) ÷ 1,470 | 9.00 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 414 | +5 | 円/日 | 計算 break_off/band_migration.out:10,11 の差の和 (194,885 − 188,577) ÷ 1,470 | 4.29 | 計算(円/日) | 値の誤り(丸めた値どうしの計算) | 出所の精度では +4.29 → +4。文書は丸めた升目 +133 − 128 = +5 の差 |
| 414 | +40 | 円/日 | 計算 break_off/band_migration.out:12,13,14 の差の和 58,804 ÷ 1,470 | 40.00 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 414 | +116 | 円/日 | 計算 break_off/band_migration.out:15,16 の差の和 170,736 ÷ 1,470 | 116.15 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 414 | −1,012 | 円 | break_off/diag_tables.json:.d3.trade_quantiles.0.01 | -50.6039(× 20 = -1,012.08) | bp(口座) | 一致 | 行は出所を名指していない。書かれた単位(円)で × 20(199 行に同じ数の bp と換算がある) |
| 414 | −674 | 円 | base/diag_tables.json:.d3.trade_quantiles.0.01 | -33.6975(× 20 = -673.95) | bp(口座) | 一致 | 行は出所を名指していない。書かれた単位(円)で × 20(199 行に同じ数の bp と換算がある) |
| 414 | −122 | 円 | break_off/diag_tables.json:.d3.trade_quantiles.0.05 | -6.10417(× 20 = -122.08) | bp(口座) | 一致 | 行は出所を名指していない。書かれた単位(円)で × 20(199 行に同じ数の bp と換算がある) |
| 414 | −208 | 円 | base/diag_tables.json:.d3.trade_quantiles.0.05 | -10.404(× 20 = -208.08) | bp(口座) | 一致 | 行は出所を名指していない。書かれた単位(円)で × 20(199 行に同じ数の bp と換算がある) |
| 414 | +1,343 | 円/日 | break_off/scene_diff.out:8 | 1343 | 円/日 | 一致 |  |
| 414 | +666 | 円/日 | break_off/scene_diff.out:9 | 666 | 円/日 | 一致 |  |
| 418 | +166 | 円/日 | 計算 break_off/band_migration.out:10,13 の差の和 243,722 ÷ 1,470 | 165.80 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 418 | −14 | 円/日 | 計算 break_off/band_migration.out:11,14,16 の差の和 −21,103 ÷ 1,470 | -14.36 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 418 | +116 | 円/日 | 計算 break_off/band_migration.out:15,16 の差の和 170,736 ÷ 1,470 | 116.15 | 計算(円/日) | 出所が無い(計算で再現) |  |
| 418 | +40 | 円/日 | 計算 break_off/band_migration.out:12,13,14 の差の和 58,804 ÷ 1,470 | 40.00 | 計算(円/日) | 出所が無い(計算で再現) |  |

## 打ったコマンド(主なもの)

1. 出所を読む: `cat -n docs/RESEARCH/matilda_main/break_off/{diag_tables.md,diag_paths.md,fam_tables.md,compare.md}`、`cat -n docs/RESEARCH/matilda_main/{break_off/*.out,base_scenes.out,break_len_mult/held_reason_break_len_mult_4.out}`、`grep -n break_off docs/RESEARCH/matilda_main/both_halves.out`、`cat -n docs/RESEARCH/matilda_main/break_dist/band_migration.out`、`cat -n docs/RESEARCH/matilda_main/band_migration.py`。json は `python3 -c "import json; …"` で `break_off/diag_tables.json`・`break_off/diag_paths.json`・`base/diag_tables.json`・`base/diag_paths.json` の鍵を印字した。
2. 「遠い線 1」の対応: `grep -n K-342 docs/RESEARCH/FINDINGS_LEDGER.md` と 762 行の本文(「遠ざけた(× 1)本 … 足の後まで持ったままの同じ取引は前半 +83・後半 −3 円/日」)で、334 行の +83・−3 が break_dist_1 の「0 分超 → 0 分超」の升目だと確かめた。
3. 突き合わせの台本(作業者の置き場 `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/a7/`。リポジトリには置いていない): `tok.py`(文書の `>` でない行から符号付きの数を拾う。`[A-Z]-数` と日付を除く)、`gen.py`(1 つずつ出所の値を json・出力から引き、書かれた単位の換算 1 通りで文書の桁に丸めて自動で比べ、合わなければ印字)、行ごとの過不足の照合(拾った符号付きの数と表の行が、除外した 181〜184・403・404 行のポイントと 65 行の「+1 分」を除いて全部の行で一致)。`python3 gen.py` → 「MISMATCH 197 −5,439,000 …」の 1 件だけ(上の決まりで計算で再現にした)。

## 確かめきれなかった範囲

1. **丸めの境 2 件**(300・313 行の +978): `held_reason.out:5` の +977.5 は小数 1 桁で書かれていて、全桁が出力に無い。取引の行から数え直せば決まるが、読むだけの仕事なので台本を回していない。
2. 310 行の −85(−372.0 − (−287.4) = −84.6)は小数 1 桁どうしの差で、出所の丸め(±0.05 ずつ)を入れると −84.5〜−84.7 になり、端の −84.5 は丸めの境。計算で再現にしたが、全桁では確かめていない。
3. 帯の移りの升目の和は、`band_migration.out` の整数に丸めた和(円)から出した。升目ごとの丸めは 1 日あたり 0.001 円以下で、値の誤りの判定(差は 0.6 以上)は変わらない。
4. 334 行の +83・−3 は値・単位とも出所と同じで一致にしたが、文書の「同じ取引の分」は break_off では同じ取引の 3 升目の和の意味で使われ、ここだけ 1 升目(足の後まで持ったまま)を指す。break_dist_1 の同じ取引の 4 升目の和は前半 +101・後半 +2(`break_dist/band_migration.out:22,23,25,26` と `:30,31,33,34` の差 円/日の和。升目の丸めた値の和で、全桁では数えていない)。言葉の食い違いで、判定には入れていない。
5. `held_reason.out`・`same_bar_reason.out`・`levels_reason.out`・`break_off_detail.out`・`market_side.out`・`scene_diff.out`・`scenes.out` を作る台本の単位(円)は、audit_4 の確かめ(`docs/DISCUSSIONS/2026-10-09_bp_units/audit_4.md` 26 行)に依った。この仕事では台本を読み直していない。
6. 拾い出しは上の機械の決まりによる。符号の無い損益の数は MDE と D4 の MFE だけを拾った(文書の全行を目で見て、ほかに符号の無い損益・値動きの数は見つけなかったが、機械では確かめていない)。
7. 出所の列は、台本が名指しの節の候補から引いた鍵・行を書いた。同じ値が別の升目にもある小さな整数(例: +5、+6、+2)は、文書の文脈(升目の名前)で手で行を選んだ。値が同じなので判定は変わらない。
