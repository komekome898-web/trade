# 突き合わせ 4: beard・break_delay・break_off の文書の数と出所(読むだけ)

作業者が 2026-10-09 に書いた。文書・台帳・コードは何も変えていない。書いたのはこのファイルだけ。

## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 担当の 3 文書の、行頭が `>` でない行にある損益・値動きの数を全部拾い、出所の出力ファイルの値・単位と 1 つずつ突き合わせて判定を付ける | 「**もっと徹底的に調べて影響範囲を確定させてください。**」 |
| 結果を `docs/DISCUSSIONS/2026-10-09_bp_units/audit_4.md` だけに書く | **(該当語なし)**(リードの委任文の指示) |

見込み時間(着手時): 90 分 = 単位の地図と 3 文書を読む 15 分 + 出所の出力を読む 15 分 + 突き合わせの台本を書く 25 分 + 3 文書の突き合わせと外れの見直し 25 分 + この文書を書く 10 分。上限 90 分。

**実際: 上限の 90 分に達したので、beard と break_delay の 2 文書で止めた。break_off は突き合わせていない(下の「確かめきれなかった範囲」)。**

## 決めたこと(判定の決まり。数えるときの読み方)

- 拾った数: 行頭が `>` でない行の、符号の付いた数(+・−)と、MDE(`](…)`・`MDE …`)と、D4 の表の MFE(符号なし)。本数・割合(`%`、利確で閉じる割合、差(ポイント))・日付・時刻・倍(1.4 倍など)・段の数は数えない。`±30` のような幅も数えない。
- 比べ方: 出所の値(円の出力はそのまま、bp の出力は json の全桁 × 20)を文書の桁に丸めて同じなら一致。比べには `.md` ではなく `.json`(全桁)を使った(`.md` の bp の和は整数に丸めてあり、× 20 すると最後の桁がずれるため。例 `beard_off/diag_paths.md:11` の +580516 × 20 = 11,610,320、json の 580515.773 × 20 = 11,610,315)。
- 出所を探す範囲: 文書がその節で名指したファイルを先に、名指しが無ければ `docs/RESEARCH/matilda_main/` の族の置き場・`both_halves.out`・`base_scenes.out`・`base/` の json。出所の候補は節ごとに台本に書いた(下の「打ったコマンド」)。
- **一致**: 出所で同じ数を見つけた。10 の位に丸めた範囲の端(「+250〜+470」など)は、端が出所の値を 10 の位に丸めたものと同じなら一致とし、備考に書いた。
- **単位の誤り(出所の指し方)**: 値は × 20 で合う(円の写し `fam_tables.md` とも合う)が、その行・節が出所として名指したのが bp のファイル(読み口の `diag_tables` の D3・D6、`diag_paths` の D4 の和)で、× 20 の換算を書いていないもの。D1・D7 の節は「bp/日 × 20 = 円」と書いてあるので一致にした。D3・D4 の節は「写しは fam_tables.md」とも書いてある(D6 の節はそれも無い)。読み手が名指しのファイルを開くと数が 20 分の 1 で見つかる、という指し方の誤りで、文書の数そのものは円として正しい。
- **値の誤り**: × 20 しても・丸めても合わない。丸めた値どうしを足し引きして最後の桁がずれたものを含む。
- **出所が無い(計算で再現)**: どの出力ファイルにも無い数で、文書の書き手が出力の値から計算した数(升目の和、和 ÷ 本数、2 つの差など)。出所の値から同じ計算をして再現できたもの。式は「出所」の列に書いた。計算で再現できなかったものは「値の誤り」に入れた。
- **確かめられない(丸めの境)**: 出所の表示がちょうど .5(例 −11.5)で、文書がそれを整数に丸めている。出所の全桁が無いので、どちらに丸まるか決められない。
- 出所の台本の単位(UNITS_MAP §2 に無い出力を確かめた): `scenes.py:30`・`scene_diff.py:16`・`same_bar_reason.py:23`(`held_reason_*.out` も `--held` で同じ台本)・`band_migration.py:15`・`levels_band.py:18`・`levels_reason.py:17`・`compare_family.py:28-36`・`break_off/break_off_detail.py:40` はどれも `pnl_jpy` を足す = 円。`market_side.py:20` は約定の数量 × 値段の差 = 円。`both_halves.py:15` は json の bp × 20 = 円。`fam_tables.py:22` は × 20 = 円(`:91` の帯は pnl_bp を足して × 20)。`nearest_signal.py` は割合だけ(対象外)。UNITS_MAP §1・§2 と食い違う点は見つからなかった。

## docs/ANALYSIS/2026-10-09_matilda_main_beard.md

| 文書の行 | 書かれた数 | 書かれた単位 | 出所 ファイル:行 | 出所の値 | 出所の単位 | 判定 | 備考 |
|---|---|---|---|---|---|---|---|
| 30 | +129 | 円/日 | both_halves.out:5 | 129 | 円/日 | 一致 |  |
| 30 | +37 | 円/日 | both_halves.out:5 | 37 | 円/日 | 一致 |  |
| 30 | +221 | 円/日 | both_halves.out:5 | 221 | 円/日 | 一致 |  |
| 30 | −55 | 円/日 | both_halves.out:5 | -55 | 円/日 | 一致 |  |
| 30 | −127 | 円/日 | both_halves.out:5 | -127 | 円/日 | 一致 |  |
| 30 | +11 | 円/日 | both_halves.out:5 | 11 | 円/日 | 一致 |  |
| 56 | +240,650.347 | 円 | beard/fam_tables.md:7 | 240650 | 円 | 一致 |  |
| 85 | −2,309 | 円 | beard/market_side.out:1 | -2309 | 円 | 一致 |  |
| 85 | +240,650 | 円 | beard/fam_tables.md:7 | 240650 | 円 | 一致 |  |
| 113 | +491 | 円/日 | beard_off/diag_tables.json:.d1.segments.first | 24.5636(× 20 = 491.27) | bp(口座) | 一致 |  |
| 113 | +340 | 円/日 | beard_off/diag_tables.json:.d1.segments.first | 17.0035(× 20 = 340.07) | bp(口座) | 一致 |  |
| 113 | +641 | 円/日 | beard_off/diag_tables.json:.d1.segments.first | 32.0298(× 20 = 640.60) | bp(口座) | 一致 |  |
| 113 | 216 | 円/日 | beard_off/diag_tables.json:.d1.segments.first | 10.8246(× 20 = 216.49) | bp(口座) | 一致 |  |
| 113 | −327 | 円/日 | beard_off/diag_tables.json:.d1.segments.second | -16.3615(× 20 = -327.23) | bp(口座) | 一致 |  |
| 113 | −438 | 円/日 | beard_off/diag_tables.json:.d1.segments.second | -21.9084(× 20 = -438.17) | bp(口座) | 一致 |  |
| 113 | −219 | 円/日 | beard_off/diag_tables.json:.d1.segments.second | -10.9278(× 20 = -218.56) | bp(口座) | 一致 |  |
| 113 | 155 | 円/日 | beard_off/diag_tables.json:.d1.segments.second | 7.75126(× 20 = 155.03) | bp(口座) | 一致 |  |
| 113 | −819 | 円/日 | beard_off/diag_tables.json:.d1.segments.diff | -40.9251(× 20 = -818.50) | bp(口座) | 一致 |  |
| 113 | −1,007 | 円/日 | beard_off/diag_tables.json:.d1.segments.diff | -50.3537(× 20 = -1,007.07) | bp(口座) | 一致 |  |
| 113 | −645 | 円/日 | beard_off/diag_tables.json:.d1.segments.diff | -32.2635(× 20 = -645.27) | bp(口座) | 一致 |  |
| 113 | +82 | 円/日 | beard_off/diag_tables.json:.d1.rows[0] | 4.09409(× 20 = 81.88) | bp(口座) | 一致 |  |
| 113 | −24 | 円/日 | beard_off/diag_tables.json:.d1.rows[0] | -1.2134(× 20 = -24.27) | bp(口座) | 一致 |  |
| 113 | +180 | 円/日 | beard_off/diag_tables.json:.d1.rows[0] | 8.97818(× 20 = 179.56) | bp(口座) | 一致 |  |
| 114 | +362 | 円/日 | base/diag_tables.json:.d1.segments.first | 18.1147(× 20 = 362.29) | bp(口座) | 一致 |  |
| 114 | +231 | 円/日 | base/diag_tables.json:.d1.segments.first | 11.5545(× 20 = 231.09) | bp(口座) | 一致 |  |
| 114 | +497 | 円/日 | base/diag_tables.json:.d1.segments.first | 24.8558(× 20 = 497.12) | bp(口座) | 一致 |  |
| 114 | 195 | 円/日 | base/diag_tables.json:.d1.segments.first | 9.75585(× 20 = 195.12) | bp(口座) | 一致 |  |
| 114 | −273 | 円/日 | base/diag_tables.json:.d1.segments.second | -13.6334(× 20 = -272.67) | bp(口座) | 一致 |  |
| 114 | −360 | 円/日 | base/diag_tables.json:.d1.segments.second | -17.9998(× 20 = -360.00) | bp(口座) | 一致 |  |
| 114 | −184 | 円/日 | base/diag_tables.json:.d1.segments.second | -9.19333(× 20 = -183.87) | bp(口座) | 一致 |  |
| 114 | 125 | 円/日 | base/diag_tables.json:.d1.segments.second | 6.2593(× 20 = 125.19) | bp(口座) | 一致 |  |
| 114 | −635 | 円/日 | base/diag_tables.json:.d1.segments.diff | -31.7481(× 20 = -634.96) | bp(口座) | 一致 |  |
| 114 | −805 | 円/日 | base/diag_tables.json:.d1.segments.diff | -40.2715(× 20 = -805.43) | bp(口座) | 一致 |  |
| 114 | −476 | 円/日 | base/diag_tables.json:.d1.segments.diff | -23.8222(× 20 = -476.44) | bp(口座) | 一致 |  |
| 114 | +45 | 円/日 | base/diag_tables.json:.d1.rows[0] | 2.23527(× 20 = 44.71) | bp(口座) | 一致 |  |
| 114 | −41 | 円/日 | base/diag_tables.json:.d1.rows[0] | -2.05628(× 20 = -41.13) | bp(口座) | 一致 |  |
| 114 | +124 | 円/日 | base/diag_tables.json:.d1.rows[0] | 6.20764(× 20 = 124.15) | bp(口座) | 一致 |  |
| 120 | −253 | 円/日 | beard_off/diag_tables.json:.d1.rows[1] | -12.669(× 20 = -253.38) | bp(口座) | 一致 |  |
| 120 | +191 | 円/日 | beard_off/diag_tables.json:.d1.rows[2] | 9.57337(× 20 = 191.47) | bp(口座) | 一致 |  |
| 120 | +867 | 円/日 | beard_off/diag_tables.json:.d1.rows[3] | 43.3287(× 20 = 866.57) | bp(口座) | 一致 |  |
| 120 | +530 | 円/日 | beard_off/diag_tables.json:.d1.rows[4] | 26.5008(× 20 = 530.02) | bp(口座) | 一致 |  |
| 120 | +421 | 円/日 | beard_off/diag_tables.json:.d1.rows[5] | 21.048(× 20 = 420.96) | bp(口座) | 一致 |  |
| 120 | +13 | 円/日 | beard_off/diag_tables.json:.d1.rows[6] | 0.67474(× 20 = 13.49) | bp(口座) | 一致 |  |
| 120 | −543 | 円/日 | beard_off/diag_tables.json:.d1.rows[7] | -27.1698(× 20 = -543.40) | bp(口座) | 一致 |  |
| 120 | −340 | 円/日 | beard_off/diag_tables.json:.d1.rows[8] | -17.0032(× 20 = -340.06) | bp(口座) | 一致 |  |
| 120 | −477 | 円/日 | beard_off/diag_tables.json:.d1.rows[9] | -23.8538(× 20 = -477.08) | bp(口座) | 一致 |  |
| 121 | −263 | 円/日 | base/diag_tables.json:.d1.rows[1] | -13.143(× 20 = -262.86) | bp(口座) | 一致 |  |
| 121 | +133 | 円/日 | base/diag_tables.json:.d1.rows[2] | 6.63264(× 20 = 132.65) | bp(口座) | 一致 |  |
| 121 | +564 | 円/日 | base/diag_tables.json:.d1.rows[3] | 28.1875(× 20 = 563.75) | bp(口座) | 一致 |  |
| 121 | +543 | 円/日 | base/diag_tables.json:.d1.rows[4] | 27.1491(× 20 = 542.98) | bp(口座) | 一致 |  |
| 121 | +244 | 円/日 | beard_off/diag_tables.json:.d1.rows[6] | 12.2057(× 20 = 244.11) | bp(口座) | 一致 |  |
| 121 | +6 | 円/日 | base/diag_tables.json:.d1.rows[6] | 0.295167(× 20 = 5.90) | bp(口座) | 一致 |  |
| 121 | −384 | 円/日 | base/diag_tables.json:.d1.rows[7] | -19.2131(× 20 = -384.26) | bp(口座) | 一致 |  |
| 121 | −263 | 円/日 | base/diag_tables.json:.d1.rows[1] | -13.143(× 20 = -262.86) | bp(口座) | 一致 |  |
| 121 | −479 | 円/日 | base/diag_tables.json:.d1.rows[9] | -23.9354(× 20 = -478.71) | bp(口座) | 一致 |  |
| 123 | +491 | 円/日 | beard_off/diag_tables.json:.d1.segments.first | 24.5636(× 20 = 491.27) | bp(口座) | 一致 |  |
| 123 | −327 | 円/日 | beard_off/diag_tables.json:.d1.segments.second | -16.3615(× 20 = -327.23) | bp(口座) | 一致 |  |
| 123 | +82 | 円/日 | beard_off/diag_tables.json:.d1.rows[0] | 4.09409(× 20 = 81.88) | bp(口座) | 一致 |  |
| 156 | +328 | 円/日 | beard/scenes.out:5 | 328 | 円/日 | 一致 |  |
| 156 | +190 | 円/日 | beard/scenes.out:5 | 190 | 円/日 | 一致 |  |
| 156 | +455 | 円/日 | beard/scenes.out:5 | 455 | 円/日 | 一致 |  |
| 156 | +264 | 円/日 | base_scenes.out:5 | 264 | 円/日 | 一致 |  |
| 156 | +65 | 円/日 | beard/scene_diff.out:4 | 65 | 円/日 | 一致 |  |
| 156 | −38 | 円/日 | beard/scene_diff.out:4 | -38 | 円/日 | 一致 |  |
| 156 | +162 | 円/日 | beard/scene_diff.out:4 | 162 | 円/日 | 一致 |  |
| 156 | −244 | 円/日 | beard/scenes.out:6 | -244 | 円/日 | 一致 |  |
| 156 | −343 | 円/日 | beard/scenes.out:6 | -343 | 円/日 | 一致 |  |
| 156 | −139 | 円/日 | beard/scenes.out:6 | -139 | 円/日 | 一致 |  |
| 156 | −216 | 円/日 | base_scenes.out:6 | -216 | 円/日 | 一致 |  |
| 156 | −28 | 円/日 | beard/scene_diff.out:5 | -28 | 円/日 | 一致 |  |
| 156 | −95 | 円/日 | beard/scene_diff.out:5 | -95 | 円/日 | 一致 |  |
| 156 | +35 | 円/日 | beard/scene_diff.out:5 | 35 | 円/日 | 一致 |  |
| 157 | +527 | 円/日 | beard/scenes.out:8 | 527 | 円/日 | 一致 |  |
| 157 | +298 | 円/日 | beard/scenes.out:8 | 298 | 円/日 | 一致 |  |
| 157 | +801 | 円/日 | beard/scenes.out:8 | 801 | 円/日 | 一致 |  |
| 157 | +411 | 円/日 | base_scenes.out:8 | 411 | 円/日 | 一致 |  |
| 157 | +115 | 円/日 | beard/scene_diff.out:6 | 115 | 円/日 | 一致 |  |
| 157 | −94 | 円/日 | beard/scene_diff.out:6 | -94 | 円/日 | 一致 |  |
| 157 | +304 | 円/日 | beard/scene_diff.out:6 | 304 | 円/日 | 一致 |  |
| 157 | −325 | 円/日 | beard/scenes.out:9 | -325 | 円/日 | 一致 |  |
| 157 | −519 | 円/日 | beard/scenes.out:9 | -519 | 円/日 | 一致 |  |
| 157 | −133 | 円/日 | beard/scenes.out:9 | -133 | 円/日 | 一致 |  |
| 157 | −282 | 円/日 | base_scenes.out:9 | -282 | 円/日 | 一致 |  |
| 157 | −44 | 円/日 | beard/scene_diff.out:7 | -44 | 円/日 | 一致 |  |
| 157 | −158 | 円/日 | beard/scene_diff.out:7 | -158 | 円/日 | 一致 |  |
| 157 | +56 | 円/日 | beard/scene_diff.out:7 | 56 | 円/日 | 一致 |  |
| 158 | +914 | 円/日 | beard/scenes.out:11 | 914 | 円/日 | 一致 |  |
| 158 | +620 | 円/日 | beard/scenes.out:11 | 620 | 円/日 | 一致 |  |
| 158 | +1,251 | 円/日 | beard/scenes.out:11 | 1251 | 円/日 | 一致 |  |
| 158 | +656 | 円/日 | base_scenes.out:11 | 656 | 円/日 | 一致 |  |
| 158 | +257 | 円/日 | beard/scene_diff.out:8 | 257 | 円/日 | 一致 |  |
| 158 | +19 | 円/日 | beard/scene_diff.out:8 | 19 | 円/日 | 一致 |  |
| 158 | +552 | 円/日 | beard/scene_diff.out:8 | 552 | 円/日 | 一致 |  |
| 158 | −443 | 円/日 | beard/scenes.out:12 | -443 | 円/日 | 一致 |  |
| 158 | −695 | 円/日 | beard/scenes.out:12 | -695 | 円/日 | 一致 |  |
| 158 | −202 | 円/日 | beard/scenes.out:12 | -202 | 円/日 | 一致 |  |
| 158 | −343 | 円/日 | beard/scenes.out:6 | -343 | 円/日 | 一致 |  |
| 158 | −99 | 円/日 | beard/scene_diff.out:9 | -99 | 円/日 | 一致 |  |
| 158 | −263 | 円/日 | beard/scene_diff.out:9 | -263 | 円/日 | 一致 |  |
| 158 | +57 | 円/日 | beard/scene_diff.out:9 | 57 | 円/日 | 一致 |  |
| 160 | +65 | 円/日 | beard/scene_diff.out:4 | 65 | 円/日 | 一致 |  |
| 160 | +115 | 円/日 | beard/scene_diff.out:6 | 115 | 円/日 | 一致 |  |
| 160 | +257 | 円/日 | beard/scene_diff.out:8 | 257 | 円/日 | 一致 |  |
| 160 | −28 | 円/日 | beard/scene_diff.out:5 | -28 | 円/日 | 一致 |  |
| 160 | −44 | 円/日 | beard/scene_diff.out:7 | -44 | 円/日 | 一致 |  |
| 160 | −99 | 円/日 | beard/scene_diff.out:9 | -99 | 円/日 | 一致 |  |
| 160 | +257 | 円/日 | beard/scene_diff.out:8 | 257 | 円/日 | 一致 |  |
| 160 | +19 | 円/日 | beard/scene_diff.out:8 | 19 | 円/日 | 一致 |  |
| 160 | +552 | 円/日 | beard/scene_diff.out:8 | 552 | 円/日 | 一致 |  |
| 181 | +40.1 | 円 | beard/compare.md:7 | 40.1 | 円 | 一致 |  |
| 181 | −365.7 | 円 | beard/compare.md:7 | -365.7 | 円 | 一致 |  |
| 181 | −316.7 | 円 | beard/compare.md:7 | -316.7 | 円 | 一致 |  |
| 181 | −4,543,597 | 円 | beard/compare.md:7 | -4,543,597 | 円 | 一致 |  |
| 181 | +721,678 | 円 | beard/compare.md:7 | +721,678 | 円 | 一致 |  |
| 182 | +40.5 | 円 | beard/compare.md:6 | 40.5 | 円 | 一致 |  |
| 182 | −281.0 | 円 | beard/compare.md:6 | -281 | 円 | 一致 |  |
| 182 | −273.4 | 円 | beard/compare.md:6 | -273.4 | 円 | 一致 |  |
| 182 | −3,866,293 | 円 | beard/compare.md:6 | -3,866,293 | 円 | 一致 |  |
| 182 | +532,210 | 円 | beard/compare.md:6 | +532,210 | 円 | 一致 |  |
| 183 | +31.4 | 円 | beard/compare.md:14 | 31.4 | 円 | 一致 |  |
| 183 | −312.1 | 円 | beard/compare.md:14 | -312.1 | 円 | 一致 |  |
| 183 | −471.5 | 円 | beard/compare.md:14 | -471.5 | 円 | 一致 |  |
| 183 | −4,585,908 | 円 | beard/compare.md:14 | -4,585,908 | 円 | 一致 |  |
| 183 | −481,028 | 円 | beard/compare.md:14 | -481,028 | 円 | 一致 |  |
| 184 | +32.2 | 円 | beard/compare.md:13 | 32.2 | 円 | 一致 |  |
| 184 | −238.4 | 円 | beard/compare.md:13 | -238.4 | 円 | 一致 |  |
| 184 | −431.6 | 円 | beard/compare.md:13 | -431.6 | 円 | 一致 |  |
| 184 | −3,834,951 | 円 | beard/compare.md:13 | -3,834,951 | 円 | 一致 |  |
| 184 | −400,821 | 円 | beard/compare.md:13 | -400,821 | 円 | 一致 |  |
| 190 | +483 | 円/日 | beard/fam_tables.md:28 | 483 | 円 | 一致 |  |
| 190 | +424 | 円/日 | beard/fam_tables.md:28 | 424 | 円 | 一致 |  |
| 190 | +541 | 円/日 | beard/fam_tables.md:28 | 541 | 円 | 一致 |  |
| 190 | +219 | 円/日 | beard/fam_tables.md:28 | 219 | 円 | 一致 |  |
| 190 | +193 | 円/日 | beard/fam_tables.md:28 | 193 | 円 | 一致 |  |
| 190 | +246 | 円/日 | beard/fam_tables.md:28 | 246 | 円 | 一致 |  |
| 190 | −153.2 | 円/日 | beard/levels_reason.out:4 | -153.2 | 円 | 一致 |  |
| 190 | −137.7 | 円/日 | beard/levels_reason.out:6 | -137.7 | 円 | 一致 |  |
| 191 | +8 | 円/日 | beard/fam_tables.md:29 | 8 | 円 | 一致 |  |
| 191 | −140 | 円/日 | beard/fam_tables.md:29 | -140 | 円 | 一致 |  |
| 191 | +149 | 円/日 | beard/fam_tables.md:29 | 149 | 円 | 一致 |  |
| 191 | −547 | 円/日 | beard/fam_tables.md:29 | -547 | 円 | 一致 |  |
| 191 | −657 | 円/日 | beard/fam_tables.md:29 | -657 | 円 | 一致 |  |
| 191 | −444 | 円/日 | beard/fam_tables.md:29 | -444 | 円 | 一致 |  |
| 191 | −422.0 | 円/日 | beard/levels_reason.out:8 | -422 | 円 | 一致 |  |
| 191 | −350.2 | 円/日 | beard/levels_reason.out:11 | -350.2 | 円 | 一致 |  |
| 192 | +329 | 円/日 | beard/fam_tables.md:30 | 329 | 円 | 一致 |  |
| 192 | +274 | 円/日 | beard/fam_tables.md:30 | 274 | 円 | 一致 |  |
| 192 | +378 | 円/日 | beard/fam_tables.md:30 | 378 | 円 | 一致 |  |
| 192 | +117 | 円/日 | beard/fam_tables.md:30 | 117 | 円 | 一致 |  |
| 192 | +92 | 円/日 | beard/fam_tables.md:30 | 92 | 円 | 一致 |  |
| 192 | +141 | 円/日 | beard/fam_tables.md:30 | 141 | 円 | 一致 |  |
| 192 | −113.4 | 円/日 | beard/levels_reason.out:14 | -113.4 | 円 | 一致 |  |
| 192 | −103.8 | 円/日 | beard/levels_reason.out:16 | -103.8 | 円 | 一致 |  |
| 193 | +33 | 円/日 | beard/fam_tables.md:31 | 33 | 円 | 一致 |  |
| 193 | −100 | 円/日 | beard/fam_tables.md:31 | -100 | 円 | 一致 |  |
| 193 | +167 | 円/日 | beard/fam_tables.md:31 | 167 | 円 | 一致 |  |
| 193 | −390 | 円/日 | beard/fam_tables.md:31 | -390 | 円 | 一致 |  |
| 193 | −474 | 円/日 | beard/fam_tables.md:31 | -474 | 円 | 一致 |  |
| 193 | −302 | 円/日 | beard/fam_tables.md:31 | -302 | 円 | 一致 |  |
| 193 | −341.7 | 円/日 | beard/levels_reason.out:18 | -341.7 | 円 | 一致 |  |
| 193 | −277.2 | 円/日 | beard/levels_reason.out:21 | -277.2 | 円 | 一致 |  |
| 195 | +35.8 | 円 | beard_off/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.close | 1.79015(× 20 = 35.80) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 195 | +34.1 | 円 | beard_off/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.close | 1.7046(× 20 = 34.09) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 195 | +37.5 | 円 | beard_off/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.close | 1.87627(× 20 = 37.53) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 195 | −337.8 | 円 | beard_off/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.break | -16.8902(× 20 = -337.80) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 195 | −354.5 | 円 | beard_off/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.break | -17.7256(× 20 = -354.51) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 195 | −321.4 | 円 | beard_off/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.break | -16.0717(× 20 = -321.43) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 195 | −367.0 | 円 | beard_off/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.market | -18.349(× 20 = -366.98) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 195 | −413.0 | 円 | beard_off/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.market | -20.6478(× 20 = -412.96) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 195 | −325.8 | 円 | beard_off/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.market | -16.2897(× 20 = -325.79) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 195 | +36.4 | 円 | base/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.close | 1.82104(× 20 = 36.42) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 195 | −258.8 | 円 | base/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.break | -12.9406(× 20 = -258.81) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 195 | −315.2 | 円 | base/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.market | -15.7597(× 20 = -315.19) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 196 | +746,134 | 円 | beard_off/diag_tables.json:.d3 | 37306.7(× 20 = 746,134.32) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 196 | −838,374 | 円 | beard_off/diag_tables.json:.d3 | -41918.7(× 20 = -838,374.46) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 196 | +240,650 | 円 | beard_off/diag_tables.json:.d3 | 12032.5(× 20 = 240,650.35) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 197 | −259 | 円 | beard/compare.md:20 | -258.8 | 円 | 一致 |  |
| 197 | −338 | 円 | beard/compare.md:21 | -337.8 | 円 | 一致 |  |
| 197 | +483 | 円 | beard/fam_tables.md:28 | 483 | 円 | 一致 |  |
| 197 | +219 | 円 | beard/fam_tables.md:28 | 219 | 円 | 一致 |  |
| 197 | −547 | 円 | beard/fam_tables.md:29 | -547 | 円 | 一致 |  |
| 197 | −390 | 円 | beard/fam_tables.md:31 | -390 | 円 | 一致 |  |
| 219 | +11,610,315 | 円 | beard_off/diag_paths.json:.d4.groups.勝った | 580516(× 20 = 11,610,315.46) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 219 | 6.02 | move_bp(文脈) | beard_off/diag_paths.json:.d4.groups.勝った | 6.02326 | move_bp | 一致 |  |
| 219 | −5.11 | move_bp(文脈) | beard_off/diag_paths.json:.d4.groups.勝った | -5.11193 | move_bp | 一致 |  |
| 219 | +10,177,344 | 円 | base/diag_paths.json:.d4.groups.勝った | 508867(× 20 = 10,177,343.87) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 219 | 6.02 | move_bp(文脈) | beard_off/diag_paths.json:.d4.groups.勝った | 6.02326 | move_bp | 一致 |  |
| 219 | −4.74 | move_bp(文脈) | base/diag_paths.json:.d4.groups.勝った | -4.74403 | move_bp | 一致 |  |
| 220 | −5,418,507 | 円 | beard_off/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた | -270925(× 20 = -5,418,506.99) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 220 | 2.12 | move_bp(文脈) | beard_off/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた | 2.12202 | move_bp | 一致 |  |
| 220 | −35.46 | move_bp(文脈) | beard_off/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた | -35.4552 | move_bp | 一致 |  |
| 220 | −4,695,044 | 円 | base/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた | -234752(× 20 = -4,695,043.87) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 220 | 2.05 | move_bp(文脈) | base/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた | 2.05371 | move_bp | 一致 |  |
| 220 | −30.50 | move_bp(文脈) | base/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた | -30.4965 | move_bp | 一致 |  |
| 221 | −6,983,067 | 円 | beard_off/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた | -349153(× 20 = -6,983,066.83) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 221 | −3.07 | move_bp(文脈) | beard_off/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた | -3.06774 | move_bp | 一致 |  |
| 221 | −37.63 | move_bp(文脈) | beard_off/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた | -37.6325 | move_bp | 一致 |  |
| 221 | −6,006,006 | 円 | base/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた | -300300(× 20 = -6,006,005.81) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 221 | −2.77 | move_bp(文脈) | base/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた | -2.77315 | move_bp | 一致 |  |
| 221 | −32.38 | move_bp(文脈) | base/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた | -32.3832 | move_bp | 一致 |  |
| 223 | −0.31 | move_bp(文脈) | beard_off/diag_paths.json:.d4.after_exit.5 | -0.305872 | move_bp | 一致 |  |
| 223 | −0.43 | move_bp(文脈) | beard_off/diag_paths.json:.d4.after_exit.5 | -0.426702 | move_bp | 一致 |  |
| 223 | −0.19 | move_bp(文脈) | beard_off/diag_paths.json:.d4.after_exit.5 | -0.193793 | move_bp | 一致 |  |
| 223 | −0.52 | move_bp(文脈) | beard_off/diag_paths.json:.d4.after_exit.15 | -0.524007 | move_bp | 一致 |  |
| 223 | −0.78 | move_bp(文脈) | beard_off/diag_paths.json:.d4.after_exit.15 | -0.77738 | move_bp | 一致 |  |
| 223 | −0.28 | move_bp(文脈) | beard_off/diag_paths.json:.d4.after_exit.15 | -0.283443 | move_bp | 一致 |  |
| 223 | −0.10 | move_bp(文脈) | beard_off/diag_paths.json:.d4.after_exit.60 | -0.102628 | move_bp | 一致 |  |
| 223 | −0.59 | move_bp(文脈) | beard_off/diag_paths.json:.d4.after_exit.60 | -0.591463 | move_bp | 一致 |  |
| 223 | +0.32 | move_bp(文脈) | beard_off/diag_paths.json:.d4.after_exit.60 | 0.324697 | move_bp | 一致 |  |
| 223 | −0.34 | move_bp(文脈) | base/diag_paths.json:.d4.after_exit.5 | -0.335294 | move_bp | 一致 |  |
| 223 | −0.66 | move_bp(文脈) | base/diag_paths.json:.d4.after_exit.15 | -0.656481 | move_bp | 一致 |  |
| 223 | −0.42 | move_bp(文脈) | base/diag_paths.json:.d4.after_exit.60 | -0.419486 | move_bp | 一致 |  |
| 224 | −30 | move_bp(文脈) | base/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた | -30.4965 | move_bp | 一致 |  |
| 224 | −32 | move_bp(文脈) | base/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた | -32.3832 | move_bp | 一致 |  |
| 224 | −35 | move_bp | beard_off/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた | -35.4552 | move_bp | 一致 |  |
| 224 | −38 | move_bp | beard_off/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた | -37.6325 | move_bp | 一致 |  |
| 224 | −10,701,050 | 円 | 計算 base/diag_paths.json d4 負けた 2 群の和 ×20 (-4,695,044-6,006,006) | -1.0701e+07 | 計算(円) | 出所が無い(計算で再現) |  |
| 224 | −12,401,574 | 円 | 計算 beard_off/diag_paths.json d4 負けた 2 群の和 ×20 (-5,418,507-6,983,067) | -1.24016e+07 | 計算(円) | 出所が無い(計算で再現) |  |
| 224 | +10,177,344 | 円 | base/diag_paths.json:.d4.groups.勝った | 508867(× 20 = 10,177,343.87) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 224 | +11,610,315 | 円 | beard_off/diag_paths.json:.d4.groups.勝った | 580516(× 20 = 11,610,315.46) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 224 | −523,706 | 円 | 計算 base/diag_paths.json d4 勝ち+負け 2 群 ×20 | -523706 | 計算(円) | 出所が無い(計算で再現) |  |
| 224 | −791,259 | 円 | 計算 beard_off/diag_paths.json d4 (勝った+負けた 2 群)×20 | -791258 | 計算(円) | 値の誤り(最後の桁) | 出所の精度で −791,258.4 → −791,258。文書は丸めた和どうしの差(+11,610,315 − 12,401,574)で −791,259 |
| 242 | −0.27 | move_bp(文脈) | beard_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).1.signal | -0.265327 | move_bp | 一致 |  |
| 242 | −0.32 | move_bp(文脈) | beard_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).1.signal | -0.318387 | move_bp | 一致 |  |
| 242 | −0.22 | move_bp(文脈) | beard_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).1.signal | -0.215651 | move_bp | 一致 |  |
| 242 | −0.49 | move_bp(文脈) | beard_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).5.signal | -0.4894 | move_bp | 一致 |  |
| 242 | −0.61 | move_bp(文脈) | beard_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).5.signal | -0.612102 | move_bp | 一致 |  |
| 242 | −0.37 | move_bp(文脈) | beard_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).5.signal | -0.366429 | move_bp | 一致 |  |
| 242 | −0.68 | move_bp(文脈) | beard_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).15.signal | -0.675166 | move_bp | 一致 |  |
| 242 | −0.91 | move_bp(文脈) | beard_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).15.signal | -0.906638 | move_bp | 一致 |  |
| 242 | −0.46 | move_bp(文脈) | beard_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).15.signal | -0.455077 | move_bp | 一致 |  |
| 242 | −0.36 | move_bp(文脈) | beard_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.signal | -0.364699 | move_bp | 一致 |  |
| 242 | −0.85 | move_bp(文脈) | beard_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.signal | -0.849454 | move_bp | 一致 |  |
| 242 | +0.09 | move_bp(文脈) | beard_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.signal | 0.0879174 | move_bp | 一致 |  |
| 242 | +0.37 | move_bp(文脈) | beard_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.control_24h | 0.366009 | move_bp | 一致 |  |
| 242 | −0.11 | move_bp(文脈) | beard_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.control_24h | -0.111836 | move_bp | 一致 |  |
| 242 | +0.84 | move_bp(文脈) | beard_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.control_24h | 0.842385 | move_bp | 一致 |  |
| 242 | −0.25 | move_bp(文脈) | base/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).1.signal | -0.253716 | move_bp | 一致 |  |
| 242 | −0.51 | move_bp(文脈) | base/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).5.signal | -0.508002 | move_bp | 一致 |  |
| 242 | −0.74 | move_bp(文脈) | base/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).15.signal | -0.74338 | move_bp | 一致 |  |
| 242 | −0.58 | move_bp(文脈) | base/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.signal | -0.575653 | move_bp | 一致 |  |
| 242 | −1.10 | move_bp(文脈) | base/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.signal | -1.09528 | move_bp | 一致 |  |
| 242 | −0.13 | move_bp(文脈) | base/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.signal | -0.129566 | move_bp | 一致 |  |
| 242 | +0.53 | move_bp(文脈) | base/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.control_24h | 0.525178 | move_bp | 一致 |  |
| 242 | +0.03 | move_bp(文脈) | base/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.control_24h | 0.0268808 | move_bp | 一致 |  |
| 242 | +1.03 | move_bp(文脈) | base/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.control_24h | 1.03455 | move_bp | 一致 |  |
| 259 | +2.2 | 円 | beard_off/diag_tables.json:.d6.groups.〜1 分 | 0.110543(× 20 = 2.21) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | +1.1 | 円 | beard_off/diag_tables.json:.d6.groups.〜1 分 | 0.0541446(× 20 = 1.08) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | +3.3 | 円 | beard_off/diag_tables.json:.d6.groups.〜1 分 | 0.16352(× 20 = 3.27) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | −1.2 | 円 | beard_off/diag_tables.json:.d6.groups.1 分超〜3 分 | -0.0611274(× 20 = -1.22) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | −3.1 | 円 | beard_off/diag_tables.json:.d6.groups.1 分超〜3 分 | -0.15482(× 20 = -3.10) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | +0.4 | 円 | beard_off/diag_tables.json:.d6.groups.1 分超〜3 分 | 0.0188486(× 20 = 0.38) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | −0.3 | 円 | beard_off/diag_tables.json:.d6.groups.3 分超〜9 分 | -0.0133841(× 20 = -0.27) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | −1.7 | 円 | beard_off/diag_tables.json:.d6.groups.3 分超〜9 分 | -0.0833083(× 20 = -1.67) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | +1.1 | 円 | beard_off/diag_tables.json:.d6.groups.〜1 分 | 0.0541446(× 20 = 1.08) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | +0.2 | 円 | beard_off/diag_tables.json:.d6.groups.9 分超 | 0.00899256(× 20 = 0.18) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | −1.3 | 円 | beard_off/diag_tables.json:.d6.groups.9 分超 | -0.0655341(× 20 = -1.31) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | +1.6 | 円 | beard_off/diag_tables.json:.d6.groups.9 分超 | 0.0799088(× 20 = 1.60) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | +2.4 | 円 | base/diag_tables.json:.d6.groups.〜1 分 | 0.117982(× 20 = 2.36) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | +1.3 | 円 | base/diag_tables.json:.d6.groups.〜1 分 | 0.0674201(× 20 = 1.35) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | +3.3 | 円 | beard_off/diag_tables.json:.d6.groups.〜1 分 | 0.16352(× 20 = 3.27) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | −0.1 | 円 | base/diag_tables.json:.d6.groups.1 分超〜3 分 | -0.00499949(× 20 = -0.10) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | −2.0 | 円 | base/diag_tables.json:.d6.groups.3 分超〜11 分 | -0.100096(× 20 = -2.00) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | −3.2 | 円 | base/diag_tables.json:.d6.groups.3 分超〜11 分 | -0.161759(× 20 = -3.24) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | −0.8 | 円 | base/diag_tables.json:.d6.groups.3 分超〜11 分 | -0.0400397(× 20 = -0.80) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 259 | −0.2 | 円 | base/diag_tables.json:.d6.groups.11 分超 | -0.01021(× 20 = -0.20) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 282 | +37.2 | 円/日 | beard_off/diag_tables.json:.d7.all | 1.85881(× 20 = 37.18) | bp(口座) | 一致 |  |
| 282 | −22.4 | 円/日 | beard_off/diag_tables.json:.d7.all | -1.12032(× 20 = -22.41) | bp(口座) | 一致 |  |
| 282 | +93.4 | 円/日 | beard_off/diag_tables.json:.d7.all | 4.66958(× 20 = 93.39) | bp(口座) | 一致 |  |
| 282 | 83.0 | 円/日 | beard_off/diag_tables.json:.d7.all | 4.14968(× 20 = 82.99) | bp(口座) | 一致 |  |
| 283 | +129 | 円/日 | beard/fam_tables.md:72 | 129 | 円 | 一致 |  |
| 283 | +37 | 円/日 | beard/fam_tables.md:72 | 37 | 円 | 一致 |  |
| 283 | +221 | 円/日 | beard/fam_tables.md:72 | 221 | 円 | 一致 |  |
| 283 | 132 | 円/日 | beard/fam_tables.md:72 | 132 | 円 | 一致 |  |
| 284 | −55 | 円/日 | beard/fam_tables.md:72 | -55 | 円 | 一致 |  |
| 284 | −127 | 円/日 | beard/fam_tables.md:72 | -127 | 円 | 一致 |  |
| 284 | +11 | 円/日 | beard/fam_tables.md:72 | 11 | 円 | 一致 |  |
| 284 | 99 | 円/日 | beard/fam_tables.md:72 | 99 | 円 | 一致 |  |
| 286 | +9 | 円/日 | beard_off/diag_tables.json:.d7.years.2015 | 0.473955(× 20 = 9.48) | bp(口座) | 一致 |  |
| 286 | +59 | 円/日 | beard_off/diag_tables.json:.d7.years.2016 | 2.94073(× 20 = 58.81) | bp(口座) | 一致 |  |
| 286 | +303 | 円/日 | beard_off/diag_tables.json:.d7.years.2017 | 15.1412(× 20 = 302.82) | bp(口座) | 一致 |  |
| 286 | −13 | 円/日 | beard_off/diag_tables.json:.d7.years.2018 | -0.64837(× 20 = -12.97) | bp(口座) | 一致 |  |
| 286 | +177 | 円/日 | beard_off/diag_tables.json:.d7.years.2019 | 8.8331(× 20 = 176.66) | bp(口座) | 一致 |  |
| 286 | +8 | 円/日 | beard_off/diag_tables.json:.d7.years.2020 | 0.379573(× 20 = 7.59) | bp(口座) | 一致 |  |
| 286 | −159 | 円/日 | beard_off/diag_tables.json:.d7.years.2021 | -7.95671(× 20 = -159.13) | bp(口座) | 一致 |  |
| 286 | −77 | 円/日 | beard_off/diag_tables.json:.d7.years.2022 | -3.85009(× 20 = -77.00) | bp(口座) | 一致 |  |
| 286 | +2 | 円/日 | beard_off/diag_tables.json:.d7.years.2023 | 0.0815452(× 20 = 1.63) | bp(口座) | 一致 |  |
| 288 | +92,529 | 円/日 | beard_off/diag_tables.json:.d7.match | 4626.45(× 20 = 92,528.94) | bp(口座) | 一致 |  |
| 288 | +438,082 | 円/日 | beard_off/diag_tables.json:.d7.match | 21904.1(× 20 = 438,081.76) | bp(口座) | 一致 |  |
| 288 | +421,350 | 円/日 | beard_off/diag_tables.json:.d7.match | 21067.5(× 20 = 421,349.82) | bp(口座) | 一致 |  |
| 294 | +14.8 | 円/日 | 計算 beard/band_migration.out:3 本の和÷本数 +317296/21394 | 14.8311 | 計算(円) | 出所が無い(計算で再現) |  |
| 294 | +216 | 円/日 | beard/band_migration.out:3 | 216 | 円 | 一致 |  |
| 295 | +1.5 | 円/日 | 計算 beard/band_migration.out:4 本の和÷本数 +73224/47444 | 1.54338 | 計算(円) | 出所が無い(計算で再現) |  |
| 295 | +50 | 円/日 | beard/band_migration.out:4 | 50 | 円 | 一致 |  |
| 296 | +13.3 | 円/日 | 計算 beard/band_migration.out:5 基準の和÷本数 +231150/17385 | 13.2959 | 計算(円) | 出所が無い(計算で再現) |  |
| 296 | −157 | 円/日 | beard/band_migration.out:5 | -157 | 円 | 一致 |  |
| 297 | +1.7 | 円/日 | 計算 beard/band_migration.out:8 基準の和÷本数 +62619/37215 | 1.68263 | 計算(円) | 出所が無い(計算で再現) |  |
| 297 | −43 | 円/日 | beard/band_migration.out:8 | -43 | 円 | 一致 |  |
| 298 | +15.1 | 円/日 | 計算 beard/band_migration.out:6 基準の和÷本数 +391820/25891 | 15.1334 | 計算(円) | 出所が無い(計算で再現) |  |
| 298 | +12.0 | 円/日 | 計算 beard/band_migration.out:6 本の和÷本数 +310237/25891 | 11.9824 | 計算(円) | 出所が無い(計算で再現) |  |
| 298 | −56 | 円/日 | beard/band_migration.out:6 | -56 | 円 | 一致 |  |
| 299 | −24.1 | 円/日 | 計算 beard/band_migration.out:7 基準の和÷本数 -139629/5787 | -24.128 | 計算(円) | 出所が無い(計算で再現) |  |
| 299 | −0.2 | 円/日 | 計算 beard/band_migration.out:7 本の和÷本数 -1378/5787 | -0.23812 | 計算(円) | 出所が無い(計算で再現) |  |
| 299 | +94 | 円/日 | beard/band_migration.out:7 | 94 | 円 | 一致 |  |
| 300 | −1.1 | 円/日 | 計算 beard/band_migration.out:10 基準の和÷本数 -90415/85883 | -1.05277 | 計算(円) | 出所が無い(計算で再現) |  |
| 300 | −0.7 | 円/日 | 計算 beard/band_migration.out:10 本の和÷本数 -59596/85883 | -0.693921 | 計算(円) | 出所が無い(計算で再現) |  |
| 300 | +21 | 円/日 | beard/band_migration.out:10 | 21 | 円 | 一致 |  |
| 301 | +19.5 | 円/日 | 計算 beard/band_migration.out:9 基準の和÷本数 +76666/3936 | 19.4782 | 計算(円) | 出所が無い(計算で再現) |  |
| 301 | +20.8 | 円/日 | 計算 beard/band_migration.out:9 本の和÷本数 +81915/3936 | 20.8117 | 計算(円) | 出所が無い(計算で再現) |  |
| 301 | +4 | 円/日 | beard/band_migration.out:9 | 4 | 円 | 一致 |  |
| 302 | +11.2 | 円/日 | 計算 beard/band_migration.out:11 本の和÷本数 +207945/18629 | 11.1624 | 計算(円) | 出所が無い(計算で再現) |  |
| 302 | +141 | 円/日 | beard/band_migration.out:11 | 141 | 円 | 一致 |  |
| 303 | −3.2 | 円/日 | 計算 beard/band_migration.out:12 本の和÷本数 -160383/50046 | -3.20471 | 計算(円) | 出所が無い(計算で再現) |  |
| 303 | −109 | 円/日 | beard/band_migration.out:12 | -109 | 円 | 一致 |  |
| 304 | +11.0 | 円/日 | 計算 beard/band_migration.out:13 基準の和÷本数 +170267/15470 | 11.0063 | 計算(円) | 出所が無い(計算で再現) |  |
| 304 | −116 | 円/日 | beard/band_migration.out:13 | -116 | 円 | 一致 |  |
| 305 | −1.0 | 円/日 | 計算 beard/band_migration.out:16 基準の和÷本数 -42686/40762 | -1.0472 | 計算(円) | 出所が無い(計算で再現) |  |
| 305 | +29 | 円/日 | beard/band_migration.out:16 | 29 | 円 | 一致 |  |
| 306 | +7.3 | 円/日 | 計算 beard/band_migration.out:14 基準の和÷本数 +142587/19623 | 7.26632 | 計算(円) | 出所が無い(計算で再現) |  |
| 306 | +3.5 | 円/日 | 計算 beard/band_migration.out:14 本の和÷本数 +69199/19623 | 3.52642 | 計算(円) | 出所が無い(計算で再現) |  |
| 306 | −50 | 円/日 | beard/band_migration.out:14 | -50 | 円 | 一致 |  |
| 307 | −27.3 | 円/日 | 計算 beard/band_migration.out:15 基準の和÷本数 -141099/5168 | -27.3024 | 計算(円) | 出所が無い(計算で再現) |  |
| 307 | −8.0 | 円/日 | 計算 beard/band_migration.out:15 本の和÷本数 -41125/5168 | -7.95762 | 計算(円) | 出所が無い(計算で再現) |  |
| 307 | +68 | 円/日 | beard/band_migration.out:15 | 68 | 円 | 一致 |  |
| 308 | −6.5 | 円/日 | 計算 beard/band_migration.out:18 基準の和÷本数 -570241/88306 | -6.45756 | 計算(円) | 出所が無い(計算で再現) |  |
| 308 | −6.8 | 円/日 | 計算 beard/band_migration.out:18 本の和÷本数 -602001/88306 | -6.81722 | 計算(円) | 出所が無い(計算で再現) |  |
| 308 | −22 | 円/日 | beard/band_migration.out:18 | -22 | 円 | 一致 |  |
| 309 | +12.0 | 円/日 | 計算 beard/band_migration.out:6 本の和÷本数 +310237/25891 | 11.9824 | 計算(円) | 出所が無い(計算で再現) |  |
| 309 | +13.5 | 円/日 | 計算 beard/band_migration.out:17 本の和÷本数 +45316/3357 | 13.499 | 計算(円) | 出所が無い(計算で再現) |  |
| 309 | +3 | 円/日 | beard/band_migration.out:17 | 3 | 円 | 一致 |  |
| 311 | +129 | 円/日 | 計算 beard/band_migration.out beard_off 前半 全部の升目(差 円/日の和: +216++50+-157+-56++94+-43++4++21) | 129 | 計算(円) | 出所が無い(計算で再現) |  |
| 311 | −56 | 円/日 | 計算 beard/band_migration.out beard_off 後半 全部の升目(差 円/日の和: +141+-109+-116+-50++68++29++3+-22) | -56 | 計算(円) | 出所が無い(計算で再現) |  |
| 311 | +129 | 円/日 | beard/fam_tables.md:72 | 129 | 円 | 一致 |  |
| 311 | −55 | 円/日 | beard/fam_tables.md:72 | -55 | 円 | 一致 |  |
| 313 | +129 | 円/日 | beard/fam_tables.md:72 | 129 | 円 | 一致 |  |
| 313 | +37 | 円/日 | beard/fam_tables.md:72 | 37 | 円 | 一致 |  |
| 313 | +221 | 円/日 | beard/fam_tables.md:72 | 221 | 円 | 一致 |  |
| 313 | −55 | 円/日 | beard/fam_tables.md:72 | -55 | 円 | 一致 |  |
| 313 | −127 | 円/日 | beard/fam_tables.md:72 | -127 | 円 | 一致 |  |
| 313 | +11 | 円/日 | beard/fam_tables.md:72 | 11 | 円 | 一致 |  |
| 314 | +438,082 | 円/日 | beard_off/diag_tables.json:.d7.match | 21904.1(× 20 = 438,081.76) | bp(口座) | 一致 |  |
| 314 | +421,350 | 円 | beard_off/diag_tables.json:.d7.match | 21067.5(× 20 = 421,349.82) | bp(口座) | 一致 |  |
| 314 | +92,529 | 円 | beard_off/diag_tables.json:.d7.match | 4626.45(× 20 = 92,528.94) | bp(口座) | 一致 |  |
| 314 | +266 | 円/日 | 計算 beard/band_migration.out beard_off 前半 こちらだけ(差 円/日の和: +216++50) | 266 | 計算(円) | 出所が無い(計算で再現) |  |
| 314 | −200 | 円/日 | 計算 beard/band_migration.out beard_off 前半 基準だけ(差 円/日の和: -157+-43) | -200 | 計算(円) | 出所が無い(計算で再現) |  |
| 314 | +94 | 円/日 | beard/band_migration.out:7 | 94 | 円 | 一致 |  |
| 314 | +141 | 円/日 | beard/band_migration.out:11 | 141 | 円 | 一致 |  |
| 314 | −116 | 円/日 | beard/band_migration.out:13 | -116 | 円 | 一致 |  |
| 314 | −109 | 円/日 | beard/band_migration.out:12 | -109 | 円 | 一致 |  |
| 314 | +7.3 | 円/日 | 計算 beard/band_migration.out:14 基準の和÷本数 +142587/19623 | 7.26632 | 計算(円) | 出所が無い(計算で再現) |  |
| 314 | +3.5 | 円 | 計算 beard/band_migration.out:14 本の和÷本数 +69199/19623 | 3.52642 | 計算(円) | 出所が無い(計算で再現) |  |
| 314 | −50 | 円/日 | beard/band_migration.out:14 | -50 | 円 | 一致 |  |
| 314 | −87 | 円/日 | 計算 beard/band_migration.out beard_off 後半 基準だけ(差 円/日の和: -116++29) | -87 | 計算(円) | 出所が無い(計算で再現) |  |
| 314 | +32 | 円/日 | 計算 beard/band_migration.out beard_off 後半 こちらだけ(差 円/日の和: +141+-109) | 32 | 計算(円) | 出所が無い(計算で再現) |  |
| 316 | +15.1 | 円/日 | 計算 beard/band_migration.out:6 基準の和÷本数 +391820/25891 | 15.1334 | 計算(円) | 出所が無い(計算で再現) |  |
| 316 | +12.0 | 円/日 | 計算 beard/band_migration.out:6 本の和÷本数 +310237/25891 | 11.9824 | 計算(円) | 出所が無い(計算で再現) |  |
| 316 | +7.3 | 円/日 | 計算 beard/band_migration.out:14 基準の和÷本数 +142587/19623 | 7.26632 | 計算(円) | 出所が無い(計算で再現) |  |
| 316 | +3.5 | 円 | 計算 beard/band_migration.out:14 本の和÷本数 +69199/19623 | 3.52642 | 計算(円) | 出所が無い(計算で再現) |  |
| 316 | −123.8 | 円/日 | beard/same_bar_reason.out:1 | -123.8 | 円 | 一致 |  |
| 316 | −180.6 | 円/日 | beard/same_bar_reason.out:1 | -180.6 | 円 | 一致 |  |
| 316 | −74 | 円/日 | beard/same_bar_reason.out:1 | -73.9 | 円 | 一致 |  |
| 316 | −120.1 | 円/日 | beard/same_bar_reason.out:5 | -120.1 | 円 | 一致 |  |
| 316 | −172.1 | 円 | beard/same_bar_reason.out:5 | -172.1 | 円 | 一致 |  |
| 316 | −63 | 円/日 | beard/same_bar_reason.out:5 | -62.8 | 円 | 一致 |  |
| 316 | +27.6 | 円/日 | beard/same_bar_reason.out:4 | 27.6 | 円 | 一致 |  |
| 316 | +26.9 | 円/日 | beard/same_bar_reason.out:4 | 26.9 | 円 | 一致 |  |
| 316 | −12 | 円/日 | beard/same_bar_reason.out:4 | -11.5 | 円 | 確かめられない(丸めの境) |  |
| 316 | +21.0 | 円/日 | beard/same_bar_reason.out:8 | 21 | 円 | 一致 |  |
| 316 | +20.6 | 円/日 | beard/same_bar_reason.out:8 | 20.6 | 円 | 一致 |  |
| 316 | −4 | 円/日 | beard/same_bar_reason.out:8 | -3.9 | 円 | 一致 |  |
| 316 | +34 | 円/日 | beard/same_bar_reason.out:2 | 33.7 | 円 | 一致 |  |
| 316 | +20 | 円/日 | beard/same_bar_reason.out:6 | 19.7 | 円 | 一致 |  |
| 332 | +129 | 円/日 | both_halves.out:5 | 129 | 円/日 | 一致 |  |
| 332 | −55 | 円/日 | both_halves.out:5 | -55 | 円/日 | 一致 |  |
| 332 | +110 | 円/日 | both_halves.out:11 | 110 | 円/日 | 一致 |  |
| 332 | −16 | 円/日 | both_halves.out:11 | -16 | 円/日 | 一致 |  |
| 332 | −124 | 円/日 | beard/same_bar_reason.out:1 | -123.8 | 円 | 一致 |  |
| 332 | −181 | 円/日 | beard/same_bar_reason.out:1 | -180.6 | 円 | 一致 |  |
| 332 | −120 | 円/日 | beard/same_bar_reason.out:5 | -120.1 | 円 | 一致 |  |
| 332 | −172 | 円 | beard/same_bar_reason.out:5 | -172.1 | 円 | 一致 |  |
| 334 | +65 | 円/日 | beard/scene_diff.out:4 | 65 | 円/日 | 一致 |  |
| 334 | +115 | 円/日 | beard/scene_diff.out:6 | 115 | 円/日 | 一致 |  |
| 334 | +257 | 円/日 | beard/scene_diff.out:8 | 257 | 円/日 | 一致 |  |
| 335 | +216 | 円/日 | beard/band_migration.out:3 | 216 | 円 | 一致 |  |
| 335 | +141 | 円/日 | beard/band_migration.out:11 | 141 | 円 | 一致 |  |
| 335 | −56 | 円/日 | beard/band_migration.out:6 | -56 | 円 | 一致 |  |
| 335 | −50 | 円/日 | beard/band_migration.out:14 | -50 | 円 | 一致 |  |
| 366 | +129 | 円/日 | beard/fam_tables.md:72 | 129 | 円 | 一致 |  |
| 366 | +37 | 円/日 | beard/fam_tables.md:72 | 37 | 円 | 一致 |  |
| 366 | +221 | 円/日 | beard/fam_tables.md:72 | 221 | 円 | 一致 |  |
| 366 | −55 | 円/日 | beard/fam_tables.md:72 | -55 | 円 | 一致 |  |
| 366 | −127 | 円/日 | beard/fam_tables.md:72 | -127 | 円 | 一致 |  |
| 366 | +11 | 円/日 | beard/fam_tables.md:72 | 11 | 円 | 一致 |  |
| 367 | −87 | 円/日 | 計算 beard/band_migration.out beard_off 後半 基準だけ(差 円/日の和: -116++29) | -87 | 計算(円) | 出所が無い(計算で再現) |  |
| 367 | +32 | 円/日 | 計算 beard/band_migration.out beard_off 後半 こちらだけ(差 円/日の和: +141+-109) | 32 | 計算(円) | 出所が無い(計算で再現) |  |
| 369 | −124 | 円/日 | beard/same_bar_reason.out:1 | -123.8 | 円 | 一致 |  |
| 369 | −181 | 円/日 | beard/same_bar_reason.out:1 | -180.6 | 円 | 一致 |  |
| 369 | −120 | 円/日 | beard/same_bar_reason.out:5 | -120.1 | 円 | 一致 |  |
| 369 | −172 | 円 | beard/same_bar_reason.out:5 | -172.1 | 円 | 一致 |  |
| 370 | +65 | 円/日 | beard/scene_diff.out:4 | 65 | 円/日 | 一致 |  |
| 370 | +115 | 円/日 | beard/scene_diff.out:6 | 115 | 円/日 | 一致 |  |
| 370 | +257 | 円/日 | beard/scene_diff.out:8 | 257 | 円/日 | 一致 |  |
| 371 | −259 | 円/日 | beard/compare.md:20 | -258.8 | 円 | 一致 |  |
| 371 | −338 | 円 | beard/compare.md:21 | -337.8 | 円 | 一致 |  |
| 372 | −0.58 | move_bp(文脈) | base/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.signal | -0.575653 | move_bp | 一致 |  |
| 372 | −1.10 | move_bp(文脈) | base/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.signal | -1.09528 | move_bp | 一致 |  |
| 372 | −0.13 | move_bp(文脈) | base/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.signal | -0.129566 | move_bp | 一致 |  |
| 372 | −0.36 | move_bp(文脈) | beard_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.signal | -0.364699 | move_bp | 一致 |  |
| 372 | −0.85 | move_bp(文脈) | beard_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.signal | -0.849454 | move_bp | 一致 |  |
| 372 | +0.09 | move_bp(文脈) | beard_off/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.signal | 0.0879174 | move_bp | 一致 |  |
| 373 | −30 | move_bp(文脈) | base/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた | -30.4965 | move_bp | 一致 |  |
| 373 | −32 | move_bp(文脈) | base/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた | -32.3832 | move_bp | 一致 |  |
| 373 | −35 | move_bp | beard_off/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた | -35.4552 | move_bp | 一致 |  |
| 373 | −38 | move_bp | beard_off/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた | -37.6325 | move_bp | 一致 |  |
| 376 | −2,309 | 円 | beard/market_side.out:1 | -2309 | 円 | 一致 |  |
| 399 | +491 | 円/日 | beard_off/diag_tables.json:.d1.segments.first | 24.5636(× 20 = 491.27) | bp(口座) | 一致 |  |
| 399 | +340 | 円/日 | beard_off/diag_tables.json:.d1.segments.first | 17.0035(× 20 = 340.07) | bp(口座) | 一致 |  |
| 399 | +641 | 円/日 | beard_off/diag_tables.json:.d1.segments.first | 32.0298(× 20 = 640.60) | bp(口座) | 一致 |  |
| 399 | −327 | 円/日 | beard_off/diag_tables.json:.d1.segments.second | -16.3615(× 20 = -327.23) | bp(口座) | 一致 |  |
| 399 | −438 | 円/日 | beard_off/diag_tables.json:.d1.segments.second | -21.9084(× 20 = -438.17) | bp(口座) | 一致 |  |
| 399 | −219 | 円/日 | beard_off/diag_tables.json:.d1.segments.second | -10.9278(× 20 = -218.56) | bp(口座) | 一致 |  |
| 400 | +362 | 円/日 | base/diag_tables.json:.d1.segments.first | 18.1147(× 20 = 362.29) | bp(口座) | 一致 |  |
| 400 | +231 | 円/日 | base/diag_tables.json:.d1.segments.first | 11.5545(× 20 = 231.09) | bp(口座) | 一致 |  |
| 400 | +497 | 円/日 | base/diag_tables.json:.d1.segments.first | 24.8558(× 20 = 497.12) | bp(口座) | 一致 |  |
| 400 | −273 | 円/日 | base/diag_tables.json:.d1.segments.second | -13.6334(× 20 = -272.67) | bp(口座) | 一致 |  |
| 400 | −360 | 円/日 | base/diag_tables.json:.d1.segments.second | -17.9998(× 20 = -360.00) | bp(口座) | 一致 |  |
| 400 | −184 | 円/日 | base/diag_tables.json:.d1.segments.second | -9.19333(× 20 = -183.87) | bp(口座) | 一致 |  |
| 409 | +303 | 円/日 | beard_off/diag_tables.json:.d7.years.2017 | 15.1412(× 20 = 302.82) | bp(口座) | 一致 |  |
| 409 | +177 | 円/日 | beard_off/diag_tables.json:.d7.years.2019 | 8.8331(× 20 = 176.66) | bp(口座) | 一致 |  |
| 409 | −159 | 円/日 | beard_off/diag_tables.json:.d7.years.2021 | -7.95671(× 20 = -159.13) | bp(口座) | 一致 |  |
| 413 | +37.2 | 円/日 | beard_off/diag_tables.json:.d7.all | 1.85881(× 20 = 37.18) | bp(口座) | 一致 |  |
| 413 | −22.4 | 円/日 | beard_off/diag_tables.json:.d7.all | -1.12032(× 20 = -22.41) | bp(口座) | 一致 |  |
| 413 | +93.4 | 円/日 | beard_off/diag_tables.json:.d7.all | 4.66958(× 20 = 93.39) | bp(口座) | 一致 |  |
| 413 | 83.0 | 円/日 | beard_off/diag_tables.json:.d7.all | 4.14968(× 20 = 82.99) | bp(口座) | 一致 |  |
| 413 | +129 | 円/日 | beard/fam_tables.md:72 | 129 | 円 | 一致 |  |
| 413 | +37 | 円/日 | beard/fam_tables.md:72 | 37 | 円 | 一致 |  |
| 413 | +221 | 円/日 | beard/fam_tables.md:72 | 221 | 円 | 一致 |  |
| 413 | −55 | 円/日 | beard/fam_tables.md:72 | -55 | 円 | 一致 |  |
| 413 | −127 | 円/日 | beard/fam_tables.md:72 | -127 | 円 | 一致 |  |
| 413 | +11 | 円/日 | beard/fam_tables.md:72 | 11 | 円 | 一致 |  |
| 413 | +59 | 円/日 | beard_off/diag_tables.json:.d7.years.2016 | 2.94073(× 20 = 58.81) | bp(口座) | 一致 |  |
| 413 | −13 | 円/日 | beard_off/diag_tables.json:.d7.years.2018 | -0.64837(× 20 = -12.97) | bp(口座) | 一致 |  |
| 413 | +8 | 円/日 | beard_off/diag_tables.json:.d7.years.2020 | 0.379573(× 20 = 7.59) | bp(口座) | 一致 |  |
| 413 | −77 | 円/日 | beard_off/diag_tables.json:.d7.years.2022 | -3.85009(× 20 = -77.00) | bp(口座) | 一致 |  |
| 413 | +2 | 円/日 | beard_off/diag_tables.json:.d7.years.2023 | 0.0815452(× 20 = 1.63) | bp(口座) | 一致 |  |
| 417 | +491 | 円/日 | beard_off/diag_tables.json:.d1.segments.first | 24.5636(× 20 = 491.27) | bp(口座) | 一致 |  |
| 417 | −327 | 円/日 | beard_off/diag_tables.json:.d1.segments.second | -16.3615(× 20 = -327.23) | bp(口座) | 一致 |  |
| 417 | +362 | 円/日 | base/diag_tables.json:.d1.segments.first | 18.1147(× 20 = 362.29) | bp(口座) | 一致 |  |
| 417 | −273 | 円/日 | base/diag_tables.json:.d1.segments.second | -13.6334(× 20 = -272.67) | bp(口座) | 一致 |  |
| 417 | +129 | 円/日 | beard/fam_tables.md:72 | 129 | 円 | 一致 |  |
| 417 | +37 | 円/日 | beard/fam_tables.md:72 | 37 | 円 | 一致 |  |
| 417 | +221 | 円/日 | beard/fam_tables.md:72 | 221 | 円 | 一致 |  |
| 417 | 132 | 円/日 | beard/fam_tables.md:72 | 132 | 円 | 一致 |  |
| 417 | −55 | 円/日 | beard/fam_tables.md:72 | -55 | 円 | 一致 |  |
| 417 | −127 | 円/日 | beard/fam_tables.md:72 | -127 | 円 | 一致 |  |
| 417 | +11 | 円/日 | beard/fam_tables.md:72 | 11 | 円 | 一致 |  |
| 417 | 99 | 円/日 | beard/fam_tables.md:72 | 99 | 円 | 一致 |  |
| 417 | +110 | 円/日 | both_halves.out:11 | 110 | 円/日 | 一致 |  |
| 417 | −16 | 円/日 | both_halves.out:11 | -16 | 円/日 | 一致 |  |
| 417 | +63 | 円/日 | 計算 beard/band_migration.out beard_off 前半 同じ取引(差 円/日の和: -56++94++4++21) | 63 | 計算(円) | 出所が無い(計算で再現) |  |
| 417 | +66 | 円/日 | 計算 beard/band_migration.out beard_off 前半 入れ替わり(差 円/日の和: +216++50+-157+-43) | 66 | 計算(円) | 出所が無い(計算で再現) |  |
| 417 | −1 | 円/日 | 計算 beard/band_migration.out beard_off 後半 同じ取引(差 円/日の和: -50++68++3+-22) | -1 | 計算(円) | 出所が無い(計算で再現) |  |
| 417 | −55 | 円/日 | beard/fam_tables.md:72 | -55 | 円 | 一致 |  |
| 417 | −259 | 円/日 | beard/compare.md:20 | -258.8 | 円 | 一致 |  |
| 417 | −338 | 円 | beard/compare.md:21 | -337.8 | 円 | 一致 |  |
| 417 | −124 | 円/日 | beard/same_bar_reason.out:1 | -123.8 | 円 | 一致 |  |
| 417 | −181 | 円/日 | beard/same_bar_reason.out:1 | -180.6 | 円 | 一致 |  |
| 417 | −120 | 円/日 | beard/same_bar_reason.out:5 | -120.1 | 円 | 一致 |  |
| 417 | −172 | 円 | beard/same_bar_reason.out:5 | -172.1 | 円 | 一致 |  |
| 417 | +438,082 | 円 | beard_off/diag_tables.json:.d7.match | 21904.1(× 20 = 438,081.76) | bp(口座) | 一致 |  |
| 417 | +421,350 | 円 | beard_off/diag_tables.json:.d7.match | 21067.5(× 20 = 421,349.82) | bp(口座) | 一致 |  |
| 417 | +257 | 円/日 | beard/scene_diff.out:8 | 257 | 円/日 | 一致 |  |
| 417 | +19 | 円/日 | beard/scene_diff.out:8 | 19 | 円/日 | 一致 |  |
| 417 | +552 | 円/日 | beard/scene_diff.out:8 | 552 | 円/日 | 一致 |  |
| 417 | +65 | 円/日 | beard/scene_diff.out:4 | 65 | 円/日 | 一致 |  |
| 417 | −38 | 円/日 | beard/scene_diff.out:4 | -38 | 円/日 | 一致 |  |
| 417 | +162 | 円/日 | beard/scene_diff.out:4 | 162 | 円/日 | 一致 |  |
| 417 | +115 | 円/日 | beard/scene_diff.out:6 | 115 | 円/日 | 一致 |  |
| 417 | −94 | 円/日 | beard/scene_diff.out:6 | -94 | 円/日 | 一致 |  |
| 417 | +304 | 円/日 | beard/scene_diff.out:6 | 304 | 円/日 | 一致 |  |

**2026-10-09_matilda_main_beard.md の数**: 拾った数 480。一致 391・出所が無い(計算で再現) 44・単位の誤り(出所の指し方) 43・値の誤り(最後の桁) 1・確かめられない(丸めの境) 1

## docs/ANALYSIS/2026-10-09_matilda_main_break_delay.md

| 文書の行 | 書かれた数 | 書かれた単位 | 出所 ファイル:行 | 出所の値 | 出所の単位 | 判定 | 備考 |
|---|---|---|---|---|---|---|---|
| 30 | −40 | 円/日 | both_halves.out:6 | -40 | 円/日 | 一致 |  |
| 30 | +38 | 円/日 | both_halves.out:6 | 38 | 円/日 | 一致 |  |
| 30 | −42 | 円/日 | both_halves.out:7 | -42 | 円/日 | 一致 |  |
| 30 | +68 | 円/日 | both_halves.out:7 | 68 | 円/日 | 一致 |  |
| 30 | −59 | 円/日 | both_halves.out:9 | -59 | 円/日 | 一致 |  |
| 30 | +76 | 円/日 | both_halves.out:8 | 76 | 円/日 | 一致 |  |
| 30 | −127 | 円/日 | both_halves.out:9 | -127 | 円/日 | 一致 |  |
| 30 | +40 | 円/日 | both_halves.out:9 | 40 | 円/日 | 一致 |  |
| 56 | +128,729 | 円 | break_delay/fam_tables.md:7 | 128729 | 円 | 一致 |  |
| 56 | +169,987 | 円 | break_delay/fam_tables.md:8 | 169987 | 円 | 一致 |  |
| 56 | +156,063 | 円 | break_delay/fam_tables.md:9 | 156063 | 円 | 一致 |  |
| 56 | +4,383 | 円 | break_delay/fam_tables.md:10 | 4383.39 | 円 | 一致 |  |
| 85 | −197 | 円 | break_delay/market_side.out:1 | -197 | 円 | 一致 |  |
| 85 | −410 | 円 | break_delay/market_side.out:2 | -410 | 円 | 一致 |  |
| 85 | +272 | 円 | break_delay/market_side.out:3 | 272 | 円 | 一致 |  |
| 85 | −615 | 円 | break_delay/market_side.out:4 | -615 | 円 | 一致 |  |
| 85 | +4,383 | 円 | break_delay/fam_tables.md:10 | 4383.39 | 円 | 一致 |  |
| 85 | −615 | 円 | break_delay/market_side.out:4 | -615 | 円 | 一致 |  |
| 85 | +3,768 | 円 | 計算 fam_tables.md:10 の +4,383.386 − market_side.out:4 の 615 | 3768.39 | 計算(円) | 出所が無い(計算で再現) |  |
| 113 | +323 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.first | 16.126(× 20 = 322.52) | bp(口座) | 一致 |  |
| 113 | +195 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.first | 9.76367(× 20 = 195.27) | bp(口座) | 一致 |  |
| 113 | +459 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.first | 22.9424(× 20 = 458.85) | bp(口座) | 一致 |  |
| 113 | 191 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.first | 9.52762(× 20 = 190.55) | bp(口座) | 一致 |  |
| 113 | −235 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.second | -11.7365(× 20 = -234.73) | bp(口座) | 一致 |  |
| 113 | −317 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.second | -15.8703(× 20 = -317.41) | bp(口座) | 一致 |  |
| 113 | −153 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.second | -7.62594(× 20 = -152.52) | bp(口座) | 一致 |  |
| 113 | 119 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.second | 5.93718(× 20 = 118.74) | bp(口座) | 一致 |  |
| 113 | −557 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.diff | -27.8625(× 20 = -557.25) | bp(口座) | 一致 |  |
| 113 | −722 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.diff | -36.1172(× 20 = -722.34) | bp(口座) | 一致 |  |
| 113 | −404 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.diff | -20.2191(× 20 = -404.38) | bp(口座) | 一致 |  |
| 113 | +44 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[0] | 2.19001(× 20 = 43.80) | bp(口座) | 一致 |  |
| 113 | −41 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[0] | -2.04861(× 20 = -40.97) | bp(口座) | 一致 |  |
| 113 | +123 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[0] | 6.15508(× 20 = 123.10) | bp(口座) | 一致 |  |
| 114 | +321 | 円/日 | break_delay_3/diag_tables.json:.d1.segments.first | 16.0365(× 20 = 320.73) | bp(口座) | 一致 |  |
| 114 | +192 | 円/日 | break_delay_3/diag_tables.json:.d1.segments.first | 9.60587(× 20 = 192.12) | bp(口座) | 一致 |  |
| 114 | +451 | 円/日 | break_delay_3/diag_tables.json:.d1.segments.first | 22.5524(× 20 = 451.05) | bp(口座) | 一致 |  |
| 114 | 186 | 円/日 | break_delay_3/diag_tables.json:.d1.segments.first | 9.32303(× 20 = 186.46) | bp(口座) | 一致 |  |
| 114 | −205 | 円/日 | break_delay_3/diag_tables.json:.d1.segments.second | -10.2437(× 20 = -204.87) | bp(口座) | 一致 |  |
| 114 | −286 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[9] | -14.2815(× 20 = -285.63) | bp(口座) | 一致 |  |
| 114 | −125 | 円/日 | break_delay_3/diag_tables.json:.d1.segments.second | -6.22952(× 20 = -124.59) | bp(口座) | 一致 |  |
| 114 | 115 | 円/日 | break_delay_3/diag_tables.json:.d1.rows[0] | 5.74211(× 20 = 114.84) | bp(口座) | 一致 |  |
| 114 | −526 | 円/日 | break_delay_3/diag_tables.json:.d1.segments.diff | -26.2802(× 20 = -525.60) | bp(口座) | 一致 |  |
| 114 | −687 | 円/日 | break_delay_3/diag_tables.json:.d1.segments.diff | -34.3608(× 20 = -687.22) | bp(口座) | 一致 |  |
| 114 | −374 | 円/日 | break_delay_3/diag_tables.json:.d1.segments.diff | -18.6979(× 20 = -373.96) | bp(口座) | 一致 |  |
| 114 | +58 | 円/日 | break_delay_3/diag_tables.json:.d1.rows[0] | 2.89193(× 20 = 57.84) | bp(口座) | 一致 |  |
| 114 | −25 | 円/日 | break_delay_3/diag_tables.json:.d1.rows[0] | -1.24711(× 20 = -24.94) | bp(口座) | 一致 |  |
| 114 | +133 | 円/日 | break_delay_3/diag_tables.json:.d1.rows[0] | 6.65617(× 20 = 133.12) | bp(口座) | 一致 |  |
| 115 | +304 | 円/日 | break_delay_4/diag_tables.json:.d1.segments.first | 15.1766(× 20 = 303.53) | bp(口座) | 一致 |  |
| 115 | +176 | 円/日 | break_delay_4/diag_tables.json:.d1.segments.first | 8.8105(× 20 = 176.21) | bp(口座) | 一致 |  |
| 115 | +435 | 円/日 | break_delay_4/diag_tables.json:.d1.segments.first | 21.7317(× 20 = 434.63) | bp(口座) | 一致 |  |
| 115 | 183 | 円/日 | break_delay_4/diag_tables.json:.d1.segments.first | 9.13671(× 20 = 182.73) | bp(口座) | 一致 |  |
| 115 | −197 | 円/日 | break_delay_4/diag_tables.json:.d1.segments.second | -9.85795(× 20 = -197.16) | bp(口座) | 一致 |  |
| 115 | −273 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[7] | -13.6684(× 20 = -273.37) | bp(口座) | 一致 |  |
| 115 | −117 | 円/日 | break_delay_4/diag_tables.json:.d1.segments.second | -5.86238(× 20 = -117.25) | bp(口座) | 一致 |  |
| 115 | 111 | 円/日 | break_delay_4/diag_tables.json:.d1.segments.second | 5.56439(× 20 = 111.29) | bp(口座) | 一致 |  |
| 115 | −501 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[7] | -25.0432(× 20 = -500.86) | bp(口座) | 一致 |  |
| 115 | −657 | 円/日 | break_delay_4/diag_tables.json:.d1.segments.diff | -32.8555(× 20 = -657.11) | bp(口座) | 一致 |  |
| 115 | −350 | 円/日 | break_delay_4/diag_tables.json:.d1.segments.diff | -17.5231(× 20 = -350.46) | bp(口座) | 一致 |  |
| 115 | +53 | 円/日 | break_delay_4/diag_tables.json:.d1.rows[0] | 2.65504(× 20 = 53.10) | bp(口座) | 一致 |  |
| 115 | −25 | 円/日 | break_delay_3/diag_tables.json:.d1.rows[0] | -1.24711(× 20 = -24.94) | bp(口座) | 一致 |  |
| 115 | +127 | 円/日 | break_delay_4/diag_tables.json:.d1.rows[0] | 6.35061(× 20 = 127.01) | bp(口座) | 一致 |  |
| 116 | +236 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.first | 11.7851(× 20 = 235.70) | bp(口座) | 一致 |  |
| 116 | +114 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.first | 5.71527(× 20 = 114.31) | bp(口座) | 一致 |  |
| 116 | +357 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.first | 17.8321(× 20 = 356.64) | bp(口座) | 一致 |  |
| 116 | 173 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.first | 8.66152(× 20 = 173.23) | bp(口座) | 一致 |  |
| 116 | −233 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.second | -11.628(× 20 = -232.56) | bp(口座) | 一致 |  |
| 116 | −313 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.second | -15.6629(× 20 = -313.26) | bp(口座) | 一致 |  |
| 116 | −158 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.second | -7.87508(× 20 = -157.50) | bp(口座) | 一致 |  |
| 116 | 115 | 円/日 | break_delay_3/diag_tables.json:.d1.rows[0] | 5.74211(× 20 = 114.84) | bp(口座) | 一致 |  |
| 116 | −468 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.diff | -23.4131(× 20 = -468.26) | bp(口座) | 一致 |  |
| 116 | −613 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.diff | -30.631(× 20 = -612.62) | bp(口座) | 一致 |  |
| 116 | −322 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.diff | -16.1045(× 20 = -322.09) | bp(口座) | 一致 |  |
| 116 | +1 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[6] | 0.0553624(× 20 = 1.11) | bp(口座) | 一致 |  |
| 116 | −76 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[7] | -3.77985(× 20 = -75.60) | bp(口座) | 一致 |  |
| 116 | +76 | 円/日 | break_delay_8/diag_tables.json:.d1.rows[0] | 3.81424(× 20 = 76.28) | bp(口座) | 一致 |  |
| 117 | +362 | 円/日 | base/diag_tables.json:.d1.segments.first | 18.1147(× 20 = 362.29) | bp(口座) | 一致 |  |
| 117 | +231 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[4] | 11.558(× 20 = 231.16) | bp(口座) | 一致 |  |
| 117 | +497 | 円/日 | base/diag_tables.json:.d1.segments.first | 24.8558(× 20 = 497.12) | bp(口座) | 一致 |  |
| 117 | 195 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.first | 9.76367(× 20 = 195.27) | bp(口座) | 一致 |  |
| 117 | −273 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[7] | -13.6684(× 20 = -273.37) | bp(口座) | 一致 |  |
| 117 | −360 | 円/日 | base/diag_tables.json:.d1.segments.second | -17.9998(× 20 = -360.00) | bp(口座) | 一致 |  |
| 117 | −184 | 円/日 | base/diag_tables.json:.d1.segments.second | -9.19333(× 20 = -183.87) | bp(口座) | 一致 |  |
| 117 | 125 | 円/日 | base/diag_tables.json:.d1.segments.second | 6.2593(× 20 = 125.19) | bp(口座) | 一致 |  |
| 117 | −635 | 円/日 | base/diag_tables.json:.d1.segments.diff | -31.7481(× 20 = -634.96) | bp(口座) | 一致 |  |
| 117 | −805 | 円/日 | base/diag_tables.json:.d1.segments.diff | -40.2715(× 20 = -805.43) | bp(口座) | 一致 |  |
| 117 | −476 | 円/日 | base/diag_tables.json:.d1.segments.diff | -23.8222(× 20 = -476.44) | bp(口座) | 一致 |  |
| 117 | +45 | 円/日 | base/diag_tables.json:.d1.rows[0] | 2.23527(× 20 = 44.71) | bp(口座) | 一致 |  |
| 117 | −41 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[0] | -2.04861(× 20 = -40.97) | bp(口座) | 一致 |  |
| 117 | +124 | 円/日 | base/diag_tables.json:.d1.rows[0] | 6.20764(× 20 = 124.15) | bp(口座) | 一致 |  |
| 123 | −129 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[1] | -6.46938(× 20 = -129.39) | bp(口座) | 一致 |  |
| 123 | +141 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[2] | 7.03175(× 20 = 140.63) | bp(口座) | 一致 |  |
| 123 | +491 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[3] | 24.5333(× 20 = 490.67) | bp(口座) | 一致 |  |
| 123 | +429 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[4] | 21.4563(× 20 = 429.13) | bp(口座) | 一致 |  |
| 123 | +262 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[5] | 13.1217(× 20 = 262.43) | bp(口座) | 一致 |  |
| 123 | +1 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[6] | 0.0553624(× 20 = 1.11) | bp(口座) | 一致 |  |
| 123 | −273 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[7] | -13.6684(× 20 = -273.37) | bp(口座) | 一致 |  |
| 123 | −261 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[8] | -13.0514(× 20 = -261.03) | bp(口座) | 一致 |  |
| 123 | −443 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[9] | -22.1647(× 20 = -443.29) | bp(口座) | 一致 |  |
| 124 | +29 | 円/日 | break_delay_3/diag_tables.json:.d1.rows[1] | 1.46739(× 20 = 29.35) | bp(口座) | 一致 |  |
| 124 | +139 | 円/日 | break_delay_3/diag_tables.json:.d1.rows[2] | 6.94823(× 20 = 138.96) | bp(口座) | 一致 |  |
| 124 | +452 | 円/日 | break_delay_3/diag_tables.json:.d1.rows[3] | 22.5872(× 20 = 451.74) | bp(口座) | 一致 |  |
| 124 | +462 | 円/日 | break_delay_3/diag_tables.json:.d1.rows[4] | 23.0805(× 20 = 461.61) | bp(口座) | 一致 |  |
| 124 | +244 | 円/日 | break_delay_3/diag_tables.json:.d1.rows[5] | 12.2187(× 20 = 244.37) | bp(口座) | 一致 |  |
| 124 | +54 | 円/日 | break_delay_3/diag_tables.json:.d1.rows[6] | 2.68705(× 20 = 53.74) | bp(口座) | 一致 |  |
| 124 | −229 | 円/日 | break_delay_3/diag_tables.json:.d1.rows[7] | -11.4516(× 20 = -229.03) | bp(口座) | 一致 |  |
| 124 | −238 | 円/日 | break_delay_3/diag_tables.json:.d1.rows[8] | -11.8962(× 20 = -237.92) | bp(口座) | 一致 |  |
| 124 | −438 | 円/日 | break_delay_3/diag_tables.json:.d1.rows[7] | -21.8784(× 20 = -437.57) | bp(口座) | 一致 |  |
| 125 | +28 | 円/日 | break_delay_4/diag_tables.json:.d1.rows[1] | 1.40144(× 20 = 28.03) | bp(口座) | 一致 |  |
| 125 | +123 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[0] | 6.15508(× 20 = 123.10) | bp(口座) | 一致 |  |
| 125 | +406 | 円/日 | break_delay_4/diag_tables.json:.d1.rows[3] | 20.3189(× 20 = 406.38) | bp(口座) | 一致 |  |
| 125 | +425 | 円/日 | break_delay_4/diag_tables.json:.d1.rows[4] | 21.2686(× 20 = 425.37) | bp(口座) | 一致 |  |
| 125 | +267 | 円/日 | break_delay_4/diag_tables.json:.d1.rows[5] | 13.3433(× 20 = 266.87) | bp(口座) | 一致 |  |
| 125 | +67 | 円/日 | break_delay_4/diag_tables.json:.d1.rows[6] | 3.34568(× 20 = 66.91) | bp(口座) | 一致 |  |
| 125 | −207 | 円/日 | break_delay_4/diag_tables.json:.d1.rows[7] | -10.3586(× 20 = -207.17) | bp(口座) | 一致 |  |
| 125 | −251 | 円/日 | break_delay_4/diag_tables.json:.d1.rows[8] | -12.54(× 20 = -250.80) | bp(口座) | 一致 |  |
| 125 | −422 | 円/日 | break_delay_4/diag_tables.json:.d1.rows[9] | -21.1037(× 20 = -422.07) | bp(口座) | 一致 |  |
| 126 | +66 | 円/日 | break_delay_8/diag_tables.json:.d1.rows[1] | 3.28498(× 20 = 65.70) | bp(口座) | 一致 |  |
| 126 | +92 | 円/日 | break_delay_8/diag_tables.json:.d1.rows[2] | 4.58598(× 20 = 91.72) | bp(口座) | 一致 |  |
| 126 | +334 | 円/日 | break_delay_8/diag_tables.json:.d1.rows[3] | 16.6962(× 20 = 333.92) | bp(口座) | 一致 |  |
| 126 | +295 | 円/日 | break_delay_8/diag_tables.json:.d1.rows[4] | 14.7279(× 20 = 294.56) | bp(口座) | 一致 |  |
| 126 | +231 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[4] | 11.558(× 20 = 231.16) | bp(口座) | 一致 |  |
| 126 | +26 | 円/日 | break_delay_8/diag_tables.json:.d1.rows[6] | 1.32424(× 20 = 26.48) | bp(口座) | 一致 |  |
| 126 | −237 | 円/日 | break_delay_8/diag_tables.json:.d1.rows[7] | -11.8651(× 20 = -237.30) | bp(口座) | 一致 |  |
| 126 | −293 | 円/日 | break_delay_8/diag_tables.json:.d1.rows[8] | -14.6477(× 20 = -292.95) | bp(口座) | 一致 |  |
| 126 | −459 | 円/日 | break_delay_8/diag_tables.json:.d1.rows[9] | -22.9265(× 20 = -458.53) | bp(口座) | 一致 |  |
| 127 | −263 | 円/日 | base/diag_tables.json:.d1.rows[1] | -13.143(× 20 = -262.86) | bp(口座) | 一致 |  |
| 127 | +133 | 円/日 | break_delay_3/diag_tables.json:.d1.rows[0] | 6.65617(× 20 = 133.12) | bp(口座) | 一致 |  |
| 127 | +564 | 円/日 | base/diag_tables.json:.d1.rows[3] | 28.1875(× 20 = 563.75) | bp(口座) | 一致 |  |
| 127 | +543 | 円/日 | base/diag_tables.json:.d1.rows[4] | 27.1491(× 20 = 542.98) | bp(口座) | 一致 |  |
| 127 | +244 | 円/日 | break_delay_3/diag_tables.json:.d1.rows[5] | 12.2187(× 20 = 244.37) | bp(口座) | 一致 |  |
| 127 | +6 | 円/日 | base/diag_tables.json:.d1.rows[6] | 0.295167(× 20 = 5.90) | bp(口座) | 一致 |  |
| 127 | −384 | 円/日 | base/diag_tables.json:.d1.rows[7] | -19.2131(× 20 = -384.26) | bp(口座) | 一致 |  |
| 127 | −263 | 円/日 | base/diag_tables.json:.d1.rows[1] | -13.143(× 20 = -262.86) | bp(口座) | 一致 |  |
| 127 | −479 | 円/日 | base/diag_tables.json:.d1.rows[9] | -23.9354(× 20 = -478.71) | bp(口座) | 一致 |  |
| 129 | +362 | 円/日 | base/diag_tables.json:.d1.segments.first | 18.1147(× 20 = 362.29) | bp(口座) | 一致 |  |
| 129 | +323 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.first | 16.126(× 20 = 322.52) | bp(口座) | 一致 |  |
| 129 | +321 | 円/日 | break_delay_3/diag_tables.json:.d1.segments.first | 16.0365(× 20 = 320.73) | bp(口座) | 一致 |  |
| 129 | +304 | 円/日 | break_delay_4/diag_tables.json:.d1.segments.first | 15.1766(× 20 = 303.53) | bp(口座) | 一致 |  |
| 129 | +236 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.first | 11.7851(× 20 = 235.70) | bp(口座) | 一致 |  |
| 129 | −635 | 円/日 | base/diag_tables.json:.d1.segments.diff | -31.7481(× 20 = -634.96) | bp(口座) | 一致 |  |
| 129 | −468 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.diff | -23.4131(× 20 = -468.26) | bp(口座) | 一致 |  |
| 129 | −273 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[7] | -13.6684(× 20 = -273.37) | bp(口座) | 一致 |  |
| 129 | −197 | 円/日 | break_delay_4/diag_tables.json:.d1.segments.second | -9.85795(× 20 = -197.16) | bp(口座) | 一致 |  |
| 129 | −233 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.second | -11.628(× 20 = -232.56) | bp(口座) | 一致 |  |
| 162 | −23 | 円/日 | break_delay/scene_diff.out:4 | -23 | 円/日 | 一致 |  |
| 162 | −62 | 円/日 | break_delay/scene_diff.out:4 | -62 | 円/日 | 一致 |  |
| 162 | +18 | 円/日 | break_delay/scene_diff.out:4 | 18 | 円/日 | 一致 |  |
| 162 | −23 | 円/日 | break_delay/scene_diff.out:4 | -23 | 円/日 | 一致 |  |
| 162 | −69 | 円/日 | break_delay/scene_diff.out:6 | -69 | 円/日 | 一致 |  |
| 162 | +28 | 円/日 | break_delay/scene_diff.out:6 | 28 | 円/日 | 一致 |  |
| 162 | −27 | 円/日 | break_delay/scene_diff.out:22 | -27 | 円/日 | 一致 |  |
| 162 | −82 | 円/日 | break_delay/scene_diff.out:22 | -82 | 円/日 | 一致 |  |
| 162 | +38 | 円/日 | break_delay/scene_diff.out:22 | 38 | 円/日 | 一致 |  |
| 162 | −73 | 円/日 | break_delay/scene_diff.out:31 | -73 | 円/日 | 一致 |  |
| 162 | −135 | 円/日 | break_delay/scene_diff.out:31 | -135 | 円/日 | 一致 |  |
| 162 | −2 | 円/日 | break_delay/scene_diff.out:31 | -2 | 円/日 | 一致 |  |
| 163 | +1 | 円/日 | break_delay/scene_diff.out:5 | 1 | 円/日 | 一致 |  |
| 163 | −28 | 円/日 | break_delay/scene_diff.out:5 | -28 | 円/日 | 一致 |  |
| 163 | +31 | 円/日 | break_delay/scene_diff.out:5 | 31 | 円/日 | 一致 |  |
| 163 | +20 | 円/日 | break_delay/scene_diff.out:14 | 20 | 円/日 | 一致 |  |
| 163 | −18 | 円/日 | break_delay/scene_diff.out:14 | -18 | 円/日 | 一致 |  |
| 163 | +61 | 円/日 | break_delay/scene_diff.out:14 | 61 | 円/日 | 一致 |  |
| 163 | +12 | 円/日 | break_delay/scene_diff.out:23 | 12 | 円/日 | 一致 |  |
| 163 | −30 | 円/日 | break_delay/scene_diff.out:23 | -30 | 円/日 | 一致 |  |
| 163 | +52 | 円/日 | break_delay/scene_diff.out:23 | 52 | 円/日 | 一致 |  |
| 163 | +20 | 円/日 | break_delay/scene_diff.out:14 | 20 | 円/日 | 一致 |  |
| 163 | −31 | 円/日 | break_delay/scene_diff.out:32 | -31 | 円/日 | 一致 |  |
| 163 | +71 | 円/日 | break_delay/scene_diff.out:32 | 71 | 円/日 | 一致 |  |
| 164 | −69 | 円/日 | break_delay/scene_diff.out:6 | -69 | 円/日 | 一致 |  |
| 164 | −162 | 円/日 | break_delay/scene_diff.out:6 | -162 | 円/日 | 一致 |  |
| 164 | +28 | 円/日 | break_delay/scene_diff.out:6 | 28 | 円/日 | 一致 |  |
| 164 | −18 | 円/日 | break_delay/scene_diff.out:15 | -18 | 円/日 | 一致 |  |
| 164 | −101 | 円/日 | break_delay/scene_diff.out:15 | -101 | 円/日 | 一致 |  |
| 164 | +75 | 円/日 | break_delay/scene_diff.out:15 | 75 | 円/日 | 一致 |  |
| 164 | +15 | 円/日 | break_delay/scene_diff.out:24 | 15 | 円/日 | 一致 |  |
| 164 | −87 | 円/日 | break_delay/scene_diff.out:24 | -87 | 円/日 | 一致 |  |
| 164 | +122 | 円/日 | break_delay/scene_diff.out:24 | 122 | 円/日 | 一致 |  |
| 164 | −96 | 円/日 | break_delay/scene_diff.out:33 | -96 | 円/日 | 一致 |  |
| 164 | −222 | 円/日 | break_delay/scene_diff.out:33 | -222 | 円/日 | 一致 |  |
| 164 | +29 | 円/日 | break_delay/scene_diff.out:33 | 29 | 円/日 | 一致 |  |
| 165 | +55 | 円/日 | break_delay/scene_diff.out:7 | 55 | 円/日 | 一致 |  |
| 165 | +4 | 円/日 | break_delay/scene_diff.out:7 | 4 | 円/日 | 一致 |  |
| 165 | +99 | 円/日 | break_delay/scene_diff.out:7 | 99 | 円/日 | 一致 |  |
| 165 | +68 | 円/日 | break_delay/scene_diff.out:16 | 68 | 円/日 | 一致 |  |
| 165 | +12 | 円/日 | break_delay/scene_diff.out:16 | 12 | 円/日 | 一致 |  |
| 165 | +120 | 円/日 | break_delay/scene_diff.out:16 | 120 | 円/日 | 一致 |  |
| 165 | +88 | 円/日 | break_delay/scene_diff.out:25 | 88 | 円/日 | 一致 |  |
| 165 | +18 | 円/日 | break_delay/scene_diff.out:25 | 18 | 円/日 | 一致 |  |
| 165 | +149 | 円/日 | break_delay/scene_diff.out:25 | 149 | 円/日 | 一致 |  |
| 165 | +13 | 円/日 | break_delay/scene_diff.out:34 | 13 | 円/日 | 一致 |  |
| 165 | −69 | 円/日 | break_delay/scene_diff.out:34 | -69 | 円/日 | 一致 |  |
| 165 | +93 | 円/日 | break_delay/scene_diff.out:34 | 93 | 円/日 | 一致 |  |
| 166 | −88 | 円/日 | break_delay/scene_diff.out:8 | -88 | 円/日 | 一致 |  |
| 166 | −220 | 円/日 | break_delay/scene_diff.out:8 | -220 | 円/日 | 一致 |  |
| 166 | +33 | 円/日 | break_delay/scene_diff.out:8 | 33 | 円/日 | 一致 |  |
| 166 | −136 | 円/日 | break_delay/scene_diff.out:17 | -136 | 円/日 | 一致 |  |
| 166 | −293 | 円/日 | break_delay/scene_diff.out:17 | -293 | 円/日 | 一致 |  |
| 166 | +33 | 円/日 | break_delay/scene_diff.out:8 | 33 | 円/日 | 一致 |  |
| 166 | −198 | 円/日 | break_delay/scene_diff.out:26 | -198 | 円/日 | 一致 |  |
| 166 | −375 | 円/日 | break_delay/scene_diff.out:26 | -375 | 円/日 | 一致 |  |
| 166 | −16 | 円/日 | break_delay/scene_diff.out:26 | -16 | 円/日 | 一致 |  |
| 166 | −296 | 円/日 | break_delay/scene_diff.out:35 | -296 | 円/日 | 一致 |  |
| 166 | −492 | 円/日 | break_delay/scene_diff.out:35 | -492 | 円/日 | 一致 |  |
| 166 | −99 | 円/日 | break_delay/scene_diff.out:35 | -99 | 円/日 | 一致 |  |
| 167 | +74 | 円/日 | break_delay/scene_diff.out:9 | 74 | 円/日 | 一致 |  |
| 167 | +12 | 円/日 | break_delay/scene_diff.out:9 | 12 | 円/日 | 一致 |  |
| 167 | +137 | 円/日 | break_delay/scene_diff.out:9 | 137 | 円/日 | 一致 |  |
| 167 | +133 | 円/日 | break_delay/scene_diff.out:18 | 133 | 円/日 | 一致 |  |
| 167 | +51 | 円/日 | break_delay/scene_diff.out:18 | 51 | 円/日 | 一致 |  |
| 167 | +214 | 円/日 | break_delay/scene_diff.out:18 | 214 | 円/日 | 一致 |  |
| 167 | +152 | 円/日 | break_delay/scene_diff.out:27 | 152 | 円/日 | 一致 |  |
| 167 | +56 | 円/日 | break_delay/scene_diff.out:27 | 56 | 円/日 | 一致 |  |
| 167 | +250 | 円/日 | break_delay/scene_diff.out:27 | 250 | 円/日 | 一致 |  |
| 167 | +90 | 円/日 | break_delay/scene_diff.out:36 | 90 | 円/日 | 一致 |  |
| 167 | −25 | 円/日 | break_delay/scene_diff.out:36 | -25 | 円/日 | 一致 |  |
| 167 | +205 | 円/日 | break_delay/scene_diff.out:36 | 205 | 円/日 | 一致 |  |
| 169 | −73 | 円/日 | break_delay/scene_diff.out:31 | -73 | 円/日 | 一致 |  |
| 169 | −135 | 円/日 | break_delay/scene_diff.out:31 | -135 | 円/日 | 一致 |  |
| 169 | −2 | 円/日 | break_delay/scene_diff.out:31 | -2 | 円/日 | 一致 |  |
| 169 | +15 | 円/日 | break_delay/scene_diff.out:24 | 15 | 円/日 | 一致 |  |
| 169 | +20 | 円/日 | break_delay/scene_diff.out:14 | 20 | 円/日 | 一致 |  |
| 169 | +13 | 円/日 | break_delay/scene_diff.out:34 | 13 | 円/日 | 一致 |  |
| 169 | −23 | 円/日 | break_delay/scene_diff.out:4 | -23 | 円/日 | 一致 |  |
| 169 | −18 | 円/日 | break_delay/scene_diff.out:14 | -18 | 円/日 | 一致 |  |
| 190 | +40.5 | 円 | break_delay/compare.md:6 | 40.5 | 円 | 一致 |  |
| 190 | −281.0 | 円 | break_delay/compare.md:6 | -281 | 円 | 一致 |  |
| 190 | −273.4 | 円 | break_delay/compare.md:6 | -273.4 | 円 | 一致 |  |
| 190 | −3,866,293 | 円 | break_delay/compare.md:6 | -3,866,293 | 円 | 一致 |  |
| 190 | +532,210 | 円 | break_delay/compare.md:6 | +532,210 | 円 | 一致 |  |
| 191 | +40.5 | 円 | break_delay/compare.md:7 | 40.5 | 円 | 一致 |  |
| 191 | −262.3 | 円 | break_delay/compare.md:7 | -262.3 | 円 | 一致 |  |
| 191 | −268.2 | 円 | break_delay/compare.md:7 | -268.2 | 円 | 一致 |  |
| 191 | −3,750,823 | 円 | break_delay/compare.md:7 | -3,750,823 | 円 | 一致 |  |
| 191 | +473,781 | 円 | break_delay/compare.md:7 | +473,781 | 円 | 一致 |  |
| 192 | +40.6 | 円 | break_delay/compare.md:8 | 40.6 | 円 | 一致 |  |
| 192 | −253.9 | 円 | break_delay/compare.md:8 | -253.9 | 円 | 一致 |  |
| 192 | −253.7 | 円 | break_delay/compare.md:8 | -253.7 | 円 | 一致 |  |
| 192 | −3,679,900 | 円 | break_delay/compare.md:8 | -3,679,900 | 円 | 一致 |  |
| 192 | +471,152 | 円 | break_delay/compare.md:8 | +471,152 | 円 | 一致 |  |
| 193 | +40.7 | 円 | break_delay/compare.md:9 | 40.7 | 円 | 一致 |  |
| 193 | −248.1 | 円 | break_delay/compare.md:9 | -248.1 | 円 | 一致 |  |
| 193 | −258.9 | 円 | break_delay/compare.md:9 | -258.9 | 円 | 一致 |  |
| 193 | −3,651,777 | 円 | break_delay/compare.md:9 | -3,651,777 | 円 | 一致 |  |
| 193 | +445,887 | 円 | break_delay/compare.md:9 | +445,887 | 円 | 一致 |  |
| 194 | +40.7 | 円 | break_delay/compare.md:10 | 40.7 | 円 | 一致 |  |
| 194 | −234.9 | 円 | break_delay/compare.md:10 | -234.9 | 円 | 一致 |  |
| 194 | −247.4 | 円 | break_delay/compare.md:10 | -247.4 | 円 | 一致 |  |
| 194 | −3,599,402 | 円 | break_delay/compare.md:10 | -3,599,402 | 円 | 一致 |  |
| 194 | +346,247 | 円 | break_delay/compare.md:10 | +346,247 | 円 | 一致 |  |
| 195 | +32.2 | 円 | break_delay/compare.md:16 | 32.2 | 円 | 一致 |  |
| 195 | −238.4 | 円 | break_delay/compare.md:16 | -238.4 | 円 | 一致 |  |
| 195 | −431.6 | 円 | break_delay/compare.md:16 | -431.6 | 円 | 一致 |  |
| 195 | −3,834,951 | 円 | break_delay/compare.md:16 | -3,834,951 | 円 | 一致 |  |
| 195 | −400,821 | 円 | break_delay/compare.md:16 | -400,821 | 円 | 一致 |  |
| 196 | +32.6 | 円 | break_delay/compare.md:17 | 32.6 | 円 | 一致 |  |
| 196 | −225.2 | 円 | break_delay/compare.md:17 | -225.2 | 円 | 一致 |  |
| 196 | −412.9 | 円 | break_delay/compare.md:17 | -412.9 | 円 | 一致 |  |
| 196 | −3,674,368 | 円 | break_delay/compare.md:17 | -3,674,368 | 円 | 一致 |  |
| 196 | −345,052 | 円 | break_delay/compare.md:17 | -345,052 | 円 | 一致 |  |
| 197 | +32.7 | 円 | break_delay/compare.md:18 | 32.7 | 円 | 一致 |  |
| 197 | −217.3 | 円 | break_delay/compare.md:18 | -217.3 | 円 | 一致 |  |
| 197 | −391.8 | 円 | break_delay/compare.md:18 | -391.8 | 円 | 一致 |  |
| 197 | −3,571,306 | 円 | break_delay/compare.md:18 | -3,571,306 | 円 | 一致 |  |
| 197 | −301,164 | 円 | break_delay/compare.md:18 | -301,164 | 円 | 一致 |  |
| 198 | +32.9 | 円 | break_delay/compare.md:19 | 32.9 | 円 | 一致 |  |
| 198 | −212.6 | 円 | break_delay/compare.md:19 | -212.6 | 円 | 一致 |  |
| 198 | −373.9 | 円 | break_delay/compare.md:19 | -373.9 | 円 | 一致 |  |
| 198 | −3,525,353 | 円 | break_delay/compare.md:19 | -3,525,353 | 円 | 一致 |  |
| 198 | −289,824 | 円 | break_delay/compare.md:19 | -289,824 | 円 | 一致 |  |
| 199 | +32.9 | 円 | break_delay/compare.md:20 | 32.9 | 円 | 一致 |  |
| 199 | −200.5 | 円 | break_delay/compare.md:20 | -200.5 | 円 | 一致 |  |
| 199 | −380.8 | 円 | break_delay/compare.md:20 | -380.8 | 円 | 一致 |  |
| 199 | −3,444,759 | 円 | break_delay/compare.md:20 | -3,444,759 | 円 | 一致 |  |
| 199 | −341,863 | 円 | break_delay/compare.md:20 | -341,863 | 円 | 一致 |  |
| 207 | +327 | 円/日 | break_delay/fam_tables.md:37 | 327 | 円 | 一致 |  |
| 207 | +274 | 円/日 | break_delay/fam_tables.md:37 | 274 | 円 | 一致 |  |
| 207 | +373 | 円/日 | break_delay/fam_tables.md:37 | 373 | 円 | 一致 |  |
| 207 | +121 | 円/日 | break_delay/fam_tables.md:37 | 121 | 円 | 一致 |  |
| 207 | +96 | 円/日 | break_delay/fam_tables.md:37 | 96 | 円 | 一致 |  |
| 207 | +145 | 円/日 | break_delay/fam_tables.md:37 | 145 | 円 | 一致 |  |
| 207 | −4 | 円/日 | break_delay/fam_tables.md:38 | -4 | 円 | 一致 |  |
| 207 | −134 | 円/日 | break_delay/fam_tables.md:38 | -134 | 円 | 一致 |  |
| 207 | +130 | 円/日 | break_delay/fam_tables.md:38 | 130 | 円 | 一致 |  |
| 207 | −356 | 円/日 | break_delay/fam_tables.md:38 | -356 | 円 | 一致 |  |
| 207 | −435 | 円/日 | break_delay/fam_tables.md:38 | -435 | 円 | 一致 |  |
| 207 | −273 | 円/日 | break_delay/fam_tables.md:38 | -273 | 円 | 一致 |  |
| 208 | +322 | 円/日 | break_delay/fam_tables.md:39 | 322 | 円 | 一致 |  |
| 208 | +272 | 円/日 | break_delay/fam_tables.md:39 | 272 | 円 | 一致 |  |
| 208 | +366 | 円/日 | break_delay/fam_tables.md:39 | 366 | 円 | 一致 |  |
| 208 | +124 | 円/日 | break_delay/fam_tables.md:39 | 124 | 円 | 一致 |  |
| 208 | +98 | 円/日 | break_delay/fam_tables.md:39 | 98 | 円 | 一致 |  |
| 208 | +148 | 円/日 | break_delay/fam_tables.md:39 | 148 | 円 | 一致 |  |
| 208 | −1 | 円/日 | break_delay/fam_tables.md:40 | -1 | 円 | 一致 |  |
| 208 | −131 | 円/日 | break_delay/fam_tables.md:40 | -131 | 円 | 一致 |  |
| 208 | +126 | 円/日 | break_delay/fam_tables.md:40 | 126 | 円 | 一致 |  |
| 208 | −328 | 円/日 | break_delay/fam_tables.md:40 | -328 | 円 | 一致 |  |
| 208 | −406 | 円/日 | break_delay/fam_tables.md:40 | -406 | 円 | 一致 |  |
| 208 | −248 | 円/日 | break_delay/fam_tables.md:40 | -248 | 円 | 一致 |  |
| 209 | +325 | 円/日 | break_delay/fam_tables.md:41 | 325 | 円 | 一致 |  |
| 209 | +274 | 円/日 | break_delay/fam_tables.md:41 | 274 | 円 | 一致 |  |
| 209 | +370 | 円/日 | break_delay/fam_tables.md:41 | 370 | 円 | 一致 |  |
| 209 | +120 | 円/日 | break_delay/fam_tables.md:41 | 120 | 円 | 一致 |  |
| 209 | +96 | 円/日 | break_delay/fam_tables.md:41 | 96 | 円 | 一致 |  |
| 209 | +143 | 円/日 | break_delay/fam_tables.md:41 | 143 | 円 | 一致 |  |
| 209 | −22 | 円/日 | break_delay/fam_tables.md:42 | -22 | 円 | 一致 |  |
| 209 | −153 | 円/日 | break_delay/fam_tables.md:42 | -153 | 円 | 一致 |  |
| 209 | +106 | 円/日 | break_delay/fam_tables.md:42 | 106 | 円 | 一致 |  |
| 209 | −317 | 円/日 | break_delay/fam_tables.md:42 | -317 | 円 | 一致 |  |
| 209 | −392 | 円/日 | break_delay/fam_tables.md:42 | -392 | 円 | 一致 |  |
| 209 | −235 | 円/日 | break_delay/fam_tables.md:42 | -235 | 円 | 一致 |  |
| 210 | +305 | 円/日 | break_delay/fam_tables.md:43 | 305 | 円 | 一致 |  |
| 210 | +258 | 円/日 | break_delay/fam_tables.md:43 | 258 | 円 | 一致 |  |
| 210 | +350 | 円/日 | break_delay/fam_tables.md:43 | 350 | 円 | 一致 |  |
| 210 | +113 | 円/日 | break_delay/fam_tables.md:43 | 113 | 円 | 一致 |  |
| 210 | +91 | 円/日 | break_delay/fam_tables.md:43 | 91 | 円 | 一致 |  |
| 210 | +133 | 円/日 | break_delay/fam_tables.md:43 | 133 | 円 | 一致 |  |
| 210 | −69 | 円/日 | break_delay/fam_tables.md:44 | -69 | 円 | 一致 |  |
| 210 | −198 | 円/日 | break_delay/fam_tables.md:44 | -198 | 円 | 一致 |  |
| 210 | +53 | 円/日 | break_delay/fam_tables.md:44 | 53 | 円 | 一致 |  |
| 210 | −346 | 円/日 | break_delay/fam_tables.md:44 | -346 | 円 | 一致 |  |
| 210 | −425 | 円/日 | break_delay/fam_tables.md:44 | -425 | 円 | 一致 |  |
| 210 | −267 | 円/日 | break_delay/fam_tables.md:44 | -267 | 円 | 一致 |  |
| 211 | +329 | 円/日 | break_delay/fam_tables.md:45 | 329 | 円 | 一致 |  |
| 211 | +274 | 円/日 | break_delay/fam_tables.md:45 | 274 | 円 | 一致 |  |
| 211 | +378 | 円/日 | break_delay/fam_tables.md:45 | 378 | 円 | 一致 |  |
| 211 | +117 | 円/日 | break_delay/fam_tables.md:45 | 117 | 円 | 一致 |  |
| 211 | +92 | 円/日 | break_delay/fam_tables.md:45 | 92 | 円 | 一致 |  |
| 211 | +141 | 円/日 | break_delay/fam_tables.md:45 | 141 | 円 | 一致 |  |
| 211 | +33 | 円/日 | break_delay/fam_tables.md:46 | 33 | 円 | 一致 |  |
| 211 | −100 | 円/日 | break_delay/fam_tables.md:46 | -100 | 円 | 一致 |  |
| 211 | +167 | 円/日 | break_delay/fam_tables.md:46 | 167 | 円 | 一致 |  |
| 211 | −390 | 円/日 | break_delay/fam_tables.md:46 | -390 | 円 | 一致 |  |
| 211 | −474 | 円/日 | break_delay/fam_tables.md:46 | -474 | 円 | 一致 |  |
| 211 | −302 | 円/日 | break_delay/fam_tables.md:46 | -302 | 円 | 一致 |  |
| 213 | −243.1 | 円 | break_delay_2/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.break | -12.155(× 20 = -243.10) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 213 | −255.3 | 円 | break_delay_2/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.break | -12.7632(× 20 = -255.26) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 213 | −231.2 | 円 | break_delay_2/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.break | -11.5615(× 20 = -231.23) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 213 | −235.0 | 円 | break_delay_3/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.break | -11.749(× 20 = -234.98) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 213 | −229.7 | 円 | break_delay_4/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.break | -11.4856(× 20 = -229.71) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 213 | −217.1 | 円 | break_delay_8/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.break | -10.8568(× 20 = -217.14) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 213 | −228.8 | 円 | break_delay_8/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.break | -11.4388(× 20 = -228.78) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 213 | −205.9 | 円 | break_delay_8/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.break | -10.2939(× 20 = -205.88) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 213 | −258.8 | 円 | base/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.break | -12.9406(× 20 = -258.81) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 213 | +36.4 | 円 | base/diag_tables.json:.d3.groups.出の理由【結果で決まる群】.close | 1.82104(× 20 = 36.42) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 213 | +36.8 | 円 | break_delay_3/diag_tables.json:.d3.trade_quantiles.0 | 1.8417(× 20 = 36.83) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 214 | +633,304 | 円 | break_delay_2/diag_tables.json:.d3 | 31665.2(× 20 = 633,303.69) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 214 | −755,561 | 円 | break_delay_2/diag_tables.json:.d3 | -37778(× 20 = -755,560.51) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 214 | +637,311 | 円 | break_delay_3/diag_tables.json:.d3 | 31865.5(× 20 = 637,310.54) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 214 | −741,974 | 円 | break_delay_3/diag_tables.json:.d3 | -37098.7(× 20 = -741,973.89) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 214 | +620,803 | 円 | break_delay_4/diag_tables.json:.d3 | 31040.2(× 20 = 620,803.43) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 214 | −716,091 | 円 | break_delay_4/diag_tables.json:.d3 | -35804.5(× 20 = -716,090.89) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 214 | +571,011 | 円 | break_delay_8/diag_tables.json:.d3 | 28550.5(× 20 = 571,010.73) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 214 | −725,471 | 円 | break_delay_8/diag_tables.json:.d3 | -36273.5(× 20 = -725,470.72) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 214 | +653,497 | 円 | base/diag_tables.json:.d3 | 32674.9(× 20 = 653,497.39) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 214 | −766,805 | 円 | base/diag_tables.json:.d3 | -38340.3(× 20 = -766,805.01) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 215 | −259 | 円 | break_delay/compare.md:9 | -258.9 | 円 | 一致 |  |
| 215 | −217 | 円 | break_delay/compare.md:18 | -217.3 | 円 | 一致 |  |
| 237 | +9,889,944 | 円 | break_delay_2/diag_paths.json:.d4.groups.勝った | 494497(× 20 = 9,889,944.43) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 237 | −10,420,068 | 円 | 計算 break_delay_2/diag_paths.json d4 負けた 2 群の和 ×20 (-4,547,674-5,872,394) | -1.04201e+07 | 計算(円) | 出所が無い(計算で再現) |  |
| 237 | −29.21 | move_bp(文脈) | break_delay_2/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた | -29.2092 | move_bp | 一致 |  |
| 237 | −31.03 | move_bp(文脈) | break_delay_2/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた | -31.0344 | move_bp | 一致 |  |
| 238 | +9,755,438 | 円 | break_delay_3/diag_paths.json:.d4.groups.勝った | 487772(× 20 = 9,755,438.22) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 238 | −10,240,154 | 円 | 計算 break_delay_3/diag_paths.json d4 負けた 2 群の和 ×20 (-4,468,290-5,771,864) | -1.02402e+07 | 計算(円) | 出所が無い(計算で再現) |  |
| 238 | −28.52 | move_bp(文脈) | break_delay_3/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた | -28.5236 | move_bp | 一致 |  |
| 238 | −30.37 | move_bp(文脈) | break_delay_3/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた | -30.3717 | move_bp | 一致 |  |
| 239 | +9,657,027 | 円 | break_delay_4/diag_paths.json:.d4.groups.勝った | 482851(× 20 = 9,657,027.13) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 239 | −10,155,299 | 円 | 計算 break_delay_4/diag_paths.json d4 負けた 2 群の和 ×20 (-4,467,779-5,687,520) | -1.01553e+07 | 計算(円) | 出所が無い(計算で再現) |  |
| 239 | −28.03 | move_bp(文脈) | break_delay_4/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた | -28.0277 | move_bp | 一致 |  |
| 239 | −30.04 | move_bp(文脈) | break_delay_4/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた | -30.0441 | move_bp | 一致 |  |
| 240 | +9,321,903 | 円 | break_delay_8/diag_paths.json:.d4.groups.勝った | 466095(× 20 = 9,321,903.43) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 240 | −9,931,720 | 円 | 計算 break_delay_8/diag_paths.json d4 負けた 2 群の和 ×20 (-4,365,487-5,566,233) | -9.93172e+06 | 計算(円) | 出所が無い(計算で再現) |  |
| 240 | −26.55 | move_bp(文脈) | break_delay_8/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた | -26.5491 | move_bp | 一致 |  |
| 240 | −29.37 | move_bp(文脈) | break_delay_8/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた | -29.3664 | move_bp | 一致 |  |
| 241 | +10,177,344 | 円 | base/diag_paths.json:.d4.groups.勝った | 508867(× 20 = 10,177,343.87) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 241 | −10,701,050 | 円 | 計算 base/diag_paths.json d4 負けた 2 群の和 ×20 (-4,695,044-6,006,006) | -1.0701e+07 | 計算(円) | 出所が無い(計算で再現) |  |
| 241 | −30.50 | move_bp(文脈) | base/diag_paths.json:.d4.groups.一度は MFE > 0 だったのに負けた | -30.4965 | move_bp | 一致 |  |
| 241 | −32.38 | move_bp(文脈) | base/diag_paths.json:.d4.groups.MFE ≤ 0 のまま負けた | -32.3832 | move_bp | 一致 |  |
| 243 | −0.42 | move_bp(文脈) | break_delay_2/diag_paths.json:.d4.after_exit.60 | -0.419021 | move_bp | 一致 |  |
| 243 | −0.89 | move_bp(文脈) | break_delay_2/diag_paths.json:.d4.after_exit.60 | -0.885259 | move_bp | 一致 |  |
| 243 | +0.01 | move_bp(文脈) | break_delay_2/diag_paths.json:.d4.after_exit.60 | 0.00883785 | move_bp | 一致 |  |
| 243 | −0.38 | move_bp(文脈) | break_delay_3/diag_paths.json:.d4.after_exit.60 | -0.382108 | move_bp | 一致 |  |
| 243 | −0.40 | move_bp(文脈) | break_delay_4/diag_paths.json:.d4.after_exit.60 | -0.39867 | move_bp | 一致 |  |
| 243 | −0.32 | move_bp(文脈) | break_delay_2/diag_paths.json:.d4.after_exit.5 | -0.323476 | move_bp | 一致 |  |
| 243 | −0.80 | move_bp(文脈) | break_delay_8/diag_paths.json:.d4.after_exit.60 | -0.796607 | move_bp | 一致 |  |
| 243 | +0.10 | move_bp(文脈) | break_delay_8/diag_paths.json:.d4.after_exit.60 | 0.0972 | move_bp | 一致 |  |
| 243 | −0.42 | move_bp(文脈) | break_delay_2/diag_paths.json:.d4.after_exit.60 | -0.419021 | move_bp | 一致 |  |
| 262 | −0.25 | move_bp(文脈) | break_delay_3/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).1.signal | -0.253966 | move_bp | 一致 |  |
| 262 | −0.26 | move_bp(文脈) | break_delay_2/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).1.signal | -0.256089 | move_bp | 一致 |  |
| 262 | −0.49 | move_bp(文脈) | break_delay_3/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).5.signal | -0.488561 | move_bp | 一致 |  |
| 262 | −0.50 | move_bp(文脈) | break_delay_2/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).15.signal | -0.495428 | move_bp | 一致 |  |
| 262 | −0.68 | move_bp(文脈) | break_delay_8/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).15.signal | -0.682921 | move_bp | 一致 |  |
| 262 | −0.73 | move_bp(文脈) | break_delay_2/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).15.signal | -0.727583 | move_bp | 一致 |  |
| 262 | −0.50 | move_bp(文脈) | break_delay_2/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).15.signal | -0.495428 | move_bp | 一致 |  |
| 262 | −0.56 | move_bp(文脈) | break_delay_2/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.signal | -0.564364 | move_bp | 一致 |  |
| 262 | −0.25 | move_bp(文脈) | break_delay_3/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).1.signal | -0.253966 | move_bp | 一致 |  |
| 262 | −0.51 | move_bp(文脈) | base/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).5.signal | -0.508002 | move_bp | 一致 |  |
| 262 | −0.74 | move_bp(文脈) | base/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).15.signal | -0.74338 | move_bp | 一致 |  |
| 262 | −0.58 | move_bp(文脈) | base/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.signal | -0.575653 | move_bp | 一致 |  |
| 264 | +0.41 | move_bp(文脈) | break_delay_8/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.control_24h | 0.407384 | move_bp | 一致 |  |
| 264 | +0.52 | move_bp(文脈) | break_delay_3/diag_paths.json:.d5.建てた合図(起点 = 建ての時刻).60.control_24h | 0.516353 | move_bp | 一致 |  |
| 279 | +1.9 | 円 | break_delay_8/diag_tables.json:.d6.groups.〜1 分 | 0.0942785(× 20 = 1.89) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 279 | +2.5 | 円 | break_delay_4/diag_tables.json:.d6.groups.〜1 分 | 0.123785(× 20 = 2.48) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 279 | −1.8 | 円 | break_delay_8/diag_tables.json:.d6.groups.3 分超〜12 分 | -0.0917803(× 20 = -1.84) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 279 | −2.3 | 円 | break_delay_3/diag_tables.json:.d6.groups.3 分超〜11 分 | -0.112886(× 20 = -2.26) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 279 | +2.4 | 円 | base/diag_tables.json:.d6.groups.〜1 分 | 0.117982(× 20 = 2.36) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 279 | +1.3 | 円 | base/diag_tables.json:.d6.groups.〜1 分 | 0.0674201(× 20 = 1.35) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 279 | +3.3 | 円 | break_delay_3/diag_tables.json:.d6.groups.〜1 分 | 0.16433(× 20 = 3.29) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 279 | −2.0 | 円 | base/diag_tables.json:.d6.groups.3 分超〜11 分 | -0.100096(× 20 = -2.00) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 279 | −3.2 | 円 | base/diag_tables.json:.d6.groups.3 分超〜11 分 | -0.161759(× 20 = -3.24) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 279 | −0.8 | 円 | base/diag_tables.json:.d6.groups.3 分超〜11 分 | -0.0400397(× 20 = -0.80) | bp(口座) | 単位の誤り(出所の指し方) | ×20 で一致。この行の出所は bp のファイル(読み口 diag_tables / diag_paths)を指し、× 20 の換算を書いていない(写しの fam_tables.md は円) |
| 302 | −0.9 | 円/日 | break_delay_2/diag_tables.json:.d7.all | -0.0452615(× 20 = -0.91) | bp(口座) | 一致 |  |
| 302 | −27.1 | 円/日 | break_delay_2/diag_tables.json:.d7.all | -1.35496(× 20 = -27.10) | bp(口座) | 一致 |  |
| 302 | +24.5 | 円/日 | break_delay_2/diag_tables.json:.d7.all | 1.22542(× 20 = 24.51) | bp(口座) | 一致 |  |
| 302 | 37.1 | 円/日 | break_delay_2/diag_tables.json:.d7.all | 1.85526(× 20 = 37.11) | bp(口座) | 一致 |  |
| 302 | −40 | 円/日 | break_delay/fam_tables.md:111 | -40 | 円 | 一致 |  |
| 302 | −89 | 円/日 | break_delay/fam_tables.md:111 | -89 | 円 | 一致 |  |
| 302 | +3 | 円/日 | break_delay/fam_tables.md:111 | 3 | 円 | 一致 |  |
| 302 | 64 | 円/日 | break_delay/fam_tables.md:111 | 64 | 円 | 一致 |  |
| 302 | +38 | 円/日 | break_delay/fam_tables.md:111 | 38 | 円 | 一致 |  |
| 302 | +13 | 円/日 | break_delay/fam_tables.md:111 | 13 | 円 | 一致 |  |
| 302 | +64 | 円/日 | break_delay/fam_tables.md:111 | 64 | 円 | 一致 |  |
| 302 | 38 | 円/日 | break_delay/fam_tables.md:111 | 38 | 円 | 一致 |  |
| 302 | −114 | 円/日 | break_delay/fam_tables.md:111 | -114 | 円 | 一致 |  |
| 302 | +111 | 円/日 | break_delay/fam_tables.md:111 | 111 | 円 | 一致 |  |
| 302 | +35 | 円/日 | break_delay/fam_tables.md:111 | 35 | 円 | 一致 |  |
| 303 | +13.1 | 円/日 | break_delay_3/diag_tables.json:.d7.all | 0.65665(× 20 = 13.13) | bp(口座) | 一致 |  |
| 303 | −21.4 | 円/日 | break_delay_3/diag_tables.json:.d7.all | -1.06856(× 20 = -21.37) | bp(口座) | 一致 |  |
| 303 | +46.3 | 円/日 | break_delay_3/diag_tables.json:.d7.all | 2.31725(× 20 = 46.35) | bp(口座) | 一致 |  |
| 303 | 48.6 | 円/日 | break_delay_3/diag_tables.json:.d7.all | 2.42954(× 20 = 48.59) | bp(口座) | 一致 |  |
| 303 | −42 | 円/日 | break_delay/fam_tables.md:112 | -42 | 円 | 一致 |  |
| 303 | −105 | 円/日 | break_delay/fam_tables.md:112 | -105 | 円 | 一致 |  |
| 303 | +14 | 円/日 | break_delay/fam_tables.md:112 | 14 | 円 | 一致 |  |
| 303 | 82 | 円/日 | break_delay/fam_tables.md:112 | 82 | 円 | 一致 |  |
| 303 | +68 | 円/日 | break_delay/fam_tables.md:112 | 68 | 円 | 一致 |  |
| 303 | +35 | 円/日 | break_delay/fam_tables.md:112 | 35 | 円 | 一致 |  |
| 303 | +101 | 円/日 | break_delay/fam_tables.md:112 | 101 | 円 | 一致 |  |
| 303 | 48 | 円/日 | break_delay/fam_tables.md:112 | 48 | 円 | 一致 |  |
| 303 | +292 | 円/日 | break_delay/fam_tables.md:112 | 292 | 円 | 一致 |  |
| 303 | +155 | 円/日 | break_delay/fam_tables.md:112 | 155 | 円 | 一致 |  |
| 303 | +41 | 円/日 | break_delay/fam_tables.md:112 | 41 | 円 | 一致 |  |
| 304 | +8.4 | 円/日 | break_delay_4/diag_tables.json:.d7.all | 0.419766(× 20 = 8.40) | bp(口座) | 一致 |  |
| 304 | −30.6 | 円/日 | break_delay_4/diag_tables.json:.d7.all | -1.53043(× 20 = -30.61) | bp(口座) | 一致 |  |
| 304 | +43.7 | 円/日 | break_delay_4/diag_tables.json:.d7.all | 2.1872(× 20 = 43.74) | bp(口座) | 一致 |  |
| 304 | 52.7 | 円/日 | break_delay_4/diag_tables.json:.d7.all | 2.63364(× 20 = 52.67) | bp(口座) | 一致 |  |
| 304 | −59 | 円/日 | break_delay/fam_tables.md:113 | -59 | 円 | 一致 |  |
| 304 | −126 | 円/日 | break_delay/fam_tables.md:113 | -126 | 円 | 一致 |  |
| 304 | −1 | 円/日 | break_delay/fam_tables.md:113 | -1 | 円 | 一致 |  |
| 304 | 90 | 円/日 | break_delay/fam_tables.md:113 | 90 | 円 | 一致 |  |
| 304 | +76 | 円/日 | break_delay/fam_tables.md:113 | 76 | 円 | 一致 |  |
| 304 | +37 | 円/日 | break_delay/fam_tables.md:113 | 37 | 円 | 一致 |  |
| 304 | +114 | 円/日 | break_delay/fam_tables.md:113 | 114 | 円 | 一致 |  |
| 304 | 57 | 円/日 | break_delay/fam_tables.md:113 | 57 | 円 | 一致 |  |
| 304 | +291 | 円/日 | break_delay/fam_tables.md:113 | 291 | 円 | 一致 |  |
| 304 | −118 | 円/日 | break_delay/fam_tables.md:113 | -118 | 円 | 一致 |  |
| 304 | +177 | 円/日 | break_delay/fam_tables.md:113 | 177 | 円 | 一致 |  |
| 304 | +57 | 円/日 | break_delay/fam_tables.md:113 | 57 | 円 | 一致 |  |
| 305 | −43.2 | 円/日 | break_delay_8/diag_tables.json:.d7.all | -2.1607(× 20 = -43.21) | bp(口座) | 一致 |  |
| 305 | −86.0 | 円/日 | break_delay_8/diag_tables.json:.d7.all | -4.29952(× 20 = -85.99) | bp(口座) | 一致 |  |
| 305 | +0.0 | 円/日 | break_delay_8/diag_tables.json:.d7.all | 0.00241621(× 20 = 0.05) | bp(口座) | 一致 |  |
| 305 | 62.8 | 円/日 | break_delay_8/diag_tables.json:.d7.all | 3.13827(× 20 = 62.77) | bp(口座) | 一致 |  |
| 305 | −127 | 円/日 | break_delay/fam_tables.md:114 | -127 | 円 | 一致 |  |
| 305 | −200 | 円/日 | break_delay/fam_tables.md:114 | -200 | 円 | 一致 |  |
| 305 | −59 | 円/日 | break_delay/fam_tables.md:114 | -59 | 円 | 一致 |  |
| 305 | 104 | 円/日 | break_delay/fam_tables.md:114 | 104 | 円 | 一致 |  |
| 305 | +40 | 円/日 | break_delay/fam_tables.md:114 | 40 | 円 | 一致 |  |
| 305 | −8 | 円/日 | break_delay/fam_tables.md:114 | -8 | 円 | 一致 |  |
| 305 | +87 | 円/日 | break_delay/fam_tables.md:114 | 87 | 円 | 一致 |  |
| 305 | 69 | 円/日 | break_delay/fam_tables.md:114 | 69 | 円 | 一致 |  |
| 305 | +329 | 円/日 | break_delay/fam_tables.md:114 | 329 | 円 | 一致 |  |
| 305 | −230 | 円/日 | break_delay/fam_tables.md:114 | -230 | 円 | 一致 |  |
| 305 | −248 | 円/日 | break_delay/fam_tables.md:114 | -248 | 円 | 一致 |  |
| 305 | +147 | 円/日 | break_delay/fam_tables.md:114 | 147 | 円 | 一致 |  |
| 307 | −3,909 | 円 | break_delay_2/diag_tables.json:.d7.match | -195.471(× 20 = -3,909.42) | bp(口座) | 一致 |  |
| 307 | +8,011 | 円 | break_delay_3/diag_tables.json:.d7.match | 400.554(× 20 = 8,011.08) | bp(口座) | 一致 |  |
| 307 | −14,005 | 円 | break_delay_4/diag_tables.json:.d7.match | -700.247(× 20 = -14,004.93) | bp(口座) | 一致 |  |
| 307 | −197,904 | 円 | break_delay_8/diag_tables.json:.d7.match | -9895.22(× 20 = -197,904.32) | bp(口座) | 一致 |  |
| 307 | −2,437 | 円 | break_delay_2/diag_tables.json:.d7.match | -121.827(× 20 = -2,436.53) | bp(口座) | 一致 |  |
| 307 | +1,175 | 円 | break_delay_3/diag_tables.json:.d7.match | 58.756(× 20 = 1,175.12) | bp(口座) | 一致 |  |
| 307 | −986 | 円 | break_delay_4/diag_tables.json:.d7.match | -49.2994(× 20 = -985.99) | bp(口座) | 一致 |  |
| 307 | +65 | 円 | break_delay_8/diag_tables.json:.d7.match | 3.2596(× 20 = 65.19) | bp(口座) | 一致 |  |
| 307 | −3,685 | 円 | break_delay_2/diag_tables.json:.d7.match | -184.274(× 20 = -3,685.48) | bp(口座) | 一致 |  |
| 307 | −29,412 | 円 | break_delay_3/diag_tables.json:.d7.match | -1470.58(× 20 = -29,411.69) | bp(口座) | 一致 |  |
| 307 | −39,665 | 円 | break_delay_4/diag_tables.json:.d7.match | -1983.24(× 20 = -39,664.74) | bp(口座) | 一致 |  |
| 307 | −70,833 | 円 | break_delay_8/diag_tables.json:.d7.match | -3541.65(× 20 = -70,833.05) | bp(口座) | 一致 |  |
| 315 | −32 | 円/日 | 計算 break_delay/band_migration.out break_delay_2 前半 同じ取引(差 円/日の和: +0++8+-16+-24) | -32 | 計算(円) | 出所が無い(計算で再現) |  |
| 315 | −8 | 円/日 | 計算 break_delay/band_migration.out break_delay_2 前半 入れ替わり(差 円/日の和: +2+-5+-9++4) | -8 | 計算(円) | 出所が無い(計算で再現) |  |
| 315 | +30 | 円/日 | 計算 break_delay/band_migration.out break_delay_2 後半 同じ取引(差 円/日の和: -0++9+-9++30) | 30 | 計算(円) | 出所が無い(計算で再現) |  |
| 315 | +8 | 円/日 | 計算 break_delay/band_migration.out break_delay_2 後半 入れ替わり(差 円/日の和: +0++1+-1++8) | 8 | 計算(円) | 出所が無い(計算で再現) |  |
| 316 | −47 | 円/日 | 計算 break_delay/band_migration.out break_delay_3 前半 同じ取引(差 円/日の和: -0++20+-24+-43) | -47 | 計算(円) | 出所が無い(計算で再現) |  |
| 316 | +6 | 円/日 | 計算 break_delay/band_migration.out break_delay_3 前半 入れ替わり(差 円/日の和: +3+-5+-12++20) | 6 | 計算(円) | 出所が無い(計算で再現) |  |
| 316 | +53 | 円/日 | 計算 break_delay/band_migration.out break_delay_3 後半 同じ取引(差 円/日の和: +3++16+-3++37) | 53 | 計算(円) | 出所が無い(計算で再現) |  |
| 316 | +16 | 円/日 | 計算 break_delay/band_migration.out break_delay_3 後半 入れ替わり(差 円/日の和: -0++4+-3++15) | 16 | 計算(円) | 出所が無い(計算で再現) |  |
| 317 | −72 | 円/日 | 計算 break_delay/band_migration.out break_delay_4 前半 同じ取引(差 円/日の和: -0++25+-33+-64) | -72 | 計算(円) | 出所が無い(計算で再現) |  |
| 317 | +13 | 円/日 | 計算 break_delay/band_migration.out break_delay_4 前半 入れ替わり(差 円/日の和: +3+-6+-13++29) | 13 | 計算(円) | 出所が無い(計算で再現) |  |
| 317 | +63 | 円/日 | 計算 break_delay/band_migration.out break_delay_4 後半 同じ取引(差 円/日の和: +1++21++0++41) | 63 | 計算(円) | 出所が無い(計算で再現) |  |
| 317 | +12 | 円/日 | 計算 break_delay/band_migration.out break_delay_4 後半 入れ替わり(+0+1−5+16) | 12 | 計算(円) | 出所が無い(計算で再現) |  |
| 318 | −158 | 円/日 | 計算 break_delay/band_migration.out break_delay_8 前半 同じ取引(差 円/日の和: -7++35+-53+-133) | -158 | 計算(円) | 出所が無い(計算で再現) |  |
| 318 | +31 | 円/日 | 計算 break_delay/band_migration.out break_delay_8 前半 入れ替わり(差 円/日の和: +5+-1+-22++49) | 31 | 計算(円) | 出所が無い(計算で再現) |  |
| 318 | +23 | 円/日 | 計算 break_delay/band_migration.out break_delay_8 後半 同じ取引(差 円/日の和: -4++33+-14++8) | 23 | 計算(円) | 出所が無い(計算で再現) |  |
| 318 | +18 | 円/日 | 計算 break_delay/band_migration.out break_delay_8 後半 入れ替わり(差 円/日の和: -0+-3+-6++27) | 18 | 計算(円) | 出所が無い(計算で再現) |  |
| 320 | −24 | 円/日 | break_delay/band_migration.out:10 | -24 | 円 | 一致 |  |
| 320 | −43 | 円/日 | break_delay/band_migration.out:26 | -43 | 円 | 一致 |  |
| 320 | −64 | 円/日 | break_delay/band_migration.out:42 | -64 | 円 | 一致 |  |
| 320 | −133 | 円/日 | break_delay/band_migration.out:58 | -133 | 円 | 一致 |  |
| 320 | +30 | 円/日 | break_delay/band_migration.out:18 | 30 | 円 | 一致 |  |
| 320 | +37 | 円/日 | break_delay/band_migration.out:34 | 37 | 円 | 一致 |  |
| 320 | +41 | 円/日 | break_delay/band_migration.out:50 | 41 | 円 | 一致 |  |
| 320 | +8 | 円/日 | break_delay/band_migration.out:58 | 8 | 円 | 一致 |  |
| 324 | +277 | 円/日 | break_delay/held_reason_break_delay_2.out:1 | 276.9 | 円 | 一致 |  |
| 324 | +246 | 円/日 | break_delay/held_reason_break_delay_2.out:8 | 246.3 | 円 | 一致 |  |
| 324 | −351.9 | 円/日 | break_delay/held_reason_break_delay_2.out:1 | -351.9 | 円 | 一致 |  |
| 324 | −321.7 | 円/日 | break_delay/held_reason_break_delay_2.out:1 | -321.7 | 円 | 一致 |  |
| 324 | −285.8 | 円/日 | break_delay/held_reason_break_delay_2.out:8 | -285.8 | 円 | 一致 |  |
| 324 | −262.6 | 円 | break_delay/held_reason_break_delay_2.out:8 | -262.6 | 円 | 一致 |  |
| 324 | −365 | 円/日 | break_delay/held_reason_break_delay_2.out:4 | -364.5 | 円 | 確かめられない(丸めの境) |  |
| 324 | −282 | 円/日 | break_delay/held_reason_break_delay_2.out:11 | -281.5 | 円 | 確かめられない(丸めの境) |  |
| 324 | +65 | 円/日 | break_delay/held_reason_break_delay_2.out:2 | 65.2 | 円 | 一致 |  |
| 324 | +65 | 円/日 | break_delay/held_reason_break_delay_2.out:2 | 65.2 | 円 | 一致 |  |
| 325 | +410 | 円/日 | break_delay/held_reason_break_delay_4.out:1 | 409.6 | 円 | 一致 |  |
| 325 | +387 | 円/日 | break_delay/held_reason_break_delay_4.out:8 | 386.5 | 円 | 確かめられない(丸めの境) |  |
| 325 | −610 | 円/日 | break_delay/held_reason_break_delay_4.out:4 | -610.2 | 円 | 一致 |  |
| 325 | −482 | 円/日 | break_delay/held_reason_break_delay_4.out:11 | -482.3 | 円 | 一致 |  |
| 325 | +136 | 円/日 | break_delay/held_reason_break_delay_4.out:2 | 136.4 | 円 | 一致 |  |
| 325 | +134 | 円/日 | break_delay/held_reason_break_delay_4.out:9 | 134.4 | 円 | 一致 |  |
| 326 | +465 | 円/日 | break_delay/held_reason_break_delay_8.out:1 | 465.2 | 円 | 一致 |  |
| 326 | +467 | 円/日 | break_delay/held_reason_break_delay_8.out:8 | 466.5 | 円 | 確かめられない(丸めの境) |  |
| 326 | −816 | 円/日 | break_delay/held_reason_break_delay_8.out:4 | -816.4 | 円 | 一致 |  |
| 326 | −676 | 円/日 | break_delay/held_reason_break_delay_8.out:11 | -676.2 | 円 | 一致 |  |
| 326 | +216 | 円/日 | break_delay/held_reason_break_delay_8.out:2 | 216 | 円 | 一致 |  |
| 326 | +210 | 円/日 | break_delay/held_reason_break_delay_8.out:9 | 210.4 | 円 | 一致 |  |
| 330 | −59 | 円/日 | both_halves.out:9 | -59 | 円/日 | 一致 |  |
| 330 | −126 | 円/日 | both_halves.out:8 | -126 | 円/日 | 一致 |  |
| 330 | −1 | 円/日 | both_halves.out:8 | -1 | 円/日 | 一致 |  |
| 330 | −127 | 円/日 | both_halves.out:9 | -127 | 円/日 | 一致 |  |
| 330 | −200 | 円/日 | both_halves.out:9 | -200 | 円/日 | 一致 |  |
| 330 | −59 | 円/日 | both_halves.out:9 | -59 | 円/日 | 一致 |  |
| 330 | −17 | 円/日 | both_halves.out:10 | -17 | 円/日 | 一致 |  |
| 330 | +111 | 円/日 | both_halves.out:10 | 111 | 円/日 | 一致 |  |
| 330 | +250 | 円/日 | break_delay/held_reason_break_delay_2.out:8(両方ブレイク、3 本の中の最小) | 246.3 | 円 | 一致 | 10 の位に丸めた範囲の端(k = 2・4・8 の両方ブレイクの円/日 +246.3〜+466.5) |
| 330 | +470 | 円/日 | break_delay/held_reason_break_delay_8.out:8(両方ブレイク、最大) | 466.5 | 円 | 一致 | 10 の位に丸めた範囲の端 |
| 330 | −280 | 円/日 | break_delay/held_reason_break_delay_2.out:11(利確→ブレイク、絶対値の最小) | -281.5 | 円 | 一致 | 10 の位に丸めた範囲の端(−281.5〜−816.4) |
| 330 | −820 | 円/日 | break_delay/held_reason_break_delay_8.out:4(利確→ブレイク、絶対値の最大) | -816.4 | 円 | 一致 | 10 の位に丸めた範囲の端 |
| 330 | −317.0 | 円/日 | 計算 break_delay/held_reason_break_delay_2.out:4 1 本の差 -297.8−(+19.2) | -317 | 計算(円) | 出所が無い(計算で再現) |  |
| 330 | −246.9 | 円 | 計算 break_delay/held_reason_break_delay_2.out:11 1 本の差 -248.5−(-1.6) | -246.9 | 計算(円) | 出所が無い(計算で再現) |  |
| 330 | −298.8 | 円/日 | 計算 break_delay/held_reason_break_delay_4.out:4 1 本の差 -283.2−(+15.6) | -298.8 | 計算(円) | 出所が無い(計算で再現) |  |
| 330 | −223.7 | 円/日 | 計算 break_delay/held_reason_break_delay_4.out:11 1 本の差 -227.1−(-3.4) | -223.7 | 計算(円) | 出所が無い(計算で再現) |  |
| 330 | −279.9 | 円/日 | 計算 break_delay/held_reason_break_delay_8.out:4 1 本の差 -261.0−(+18.9) | -279.9 | 計算(円) | 出所が無い(計算で再現) |  |
| 330 | −209.9 | 円/日 | 計算 break_delay/held_reason_break_delay_8.out:11 1 本の差 -209.6−(+0.3) | -209.9 | 計算(円) | 出所が無い(計算で再現) |  |
| 330 | +30.2 | 円/日 | 計算 break_delay/held_reason_break_delay_2.out:1 1 本の差 -321.7−(-351.9) | 30.2 | 計算(円) | 出所が無い(計算で再現) |  |
| 330 | +23.2 | 円/日 | 計算 break_delay/held_reason_break_delay_2.out:8 1 本の差 -262.6−(-285.8) | 23.2 | 計算(円) | 出所が無い(計算で再現) |  |
| 330 | +48.6 | 円/日 | 計算 break_delay/held_reason_break_delay_4.out:1 1 本の差 -312.1−(-360.7) | 48.6 | 計算(円) | 出所が無い(計算で再現) |  |
| 330 | +39.4 | 円/日 | 計算 break_delay/held_reason_break_delay_4.out:8 1 本の差 -253.5−(-292.9) | 39.4 | 計算(円) | 出所が無い(計算で再現) |  |
| 330 | +61.1 | 円/日 | 計算 break_delay/held_reason_break_delay_8.out:1 1 本の差 -310.4−(-371.5) | 61.1 | 計算(円) | 出所が無い(計算で再現) |  |
| 330 | +52.2 | 円 | 計算 break_delay/held_reason_break_delay_8.out:8 1 本の差 -248.2−(-300.4) | 52.2 | 計算(円) | 出所が無い(計算で再現) |  |
| 330 | +65 | 円/日 | break_delay/held_reason_break_delay_2.out:2 | 65.2 | 円 | 一致 |  |
| 330 | +65 | 円/日 | break_delay/held_reason_break_delay_2.out:2 | 65.2 | 円 | 一致 |  |
| 330 | +136 | 円/日 | break_delay/held_reason_break_delay_4.out:2 | 136.4 | 円 | 一致 |  |
| 330 | +134 | 円/日 | break_delay/held_reason_break_delay_4.out:9 | 134.4 | 円 | 一致 |  |
| 330 | +216 | 円/日 | break_delay/held_reason_break_delay_8.out:2 | 216 | 円 | 一致 |  |
| 330 | +210 | 円/日 | break_delay/held_reason_break_delay_8.out:9 | 210.4 | 円 | 一致 |  |
| 330 | −88 | 円/日 | 計算 break_delay/held_reason_break_delay_2.out:1+4 初めの 2 項の和 +276.9-364.5 | -87.6 | 計算(円) | 出所が無い(計算で再現) |  |
| 330 | −36 | 円/日 | break_delay/held_reason_break_delay_2.out:8+11 (+246.3)+(−281.5) | -35.2 | 計算(円) | 値の誤り(丸めた値どうしの計算) | 出所の値で −35.2 → −35。文書の −36 は丸めた +246・−282 の和 |
| 330 | −200 | 円/日 | break_delay/held_reason_break_delay_4.out:1+4 (+409.6)+(−610.2) | -200.6 | 計算(円) | 値の誤り(丸めた値どうしの計算) | 出所の値で −200.6 → −201。文書の −200 は丸めた +410・−610 の和 |
| 330 | −95 | 円/日 | break_delay/held_reason_break_delay_4.out:8+11 (+386.5)+(−482.3) | -95.8 | 計算(円) | 値の誤り(丸めた値どうしの計算) | 出所の値で −95.8 → −96。文書の −95 は丸めた +387・−482 の和 |
| 330 | −351 | 円/日 | 計算 break_delay/held_reason_break_delay_8.out:1+4 初めの 2 項の和 +465.2-816.4 | -351.2 | 計算(円) | 出所が無い(計算で再現) |  |
| 330 | −209 | 円/日 | break_delay/held_reason_break_delay_8.out:8+11 (+466.5)+(−676.2) | -209.7 | 計算(円) | 値の誤り(丸めた値どうしの計算) | 出所の値で −209.7 → −210。文書の −209 は丸めた +467・−676 の和 |
| 331 | −40 | 円/日 | both_halves.out:6 | -40 | 円/日 | 一致 |  |
| 331 | −42 | 円/日 | both_halves.out:7 | -42 | 円/日 | 一致 |  |
| 331 | −59 | 円/日 | both_halves.out:9 | -59 | 円/日 | 一致 |  |
| 331 | −127 | 円/日 | both_halves.out:9 | -127 | 円/日 | 一致 |  |
| 331 | +38 | 円/日 | both_halves.out:6 | 38 | 円/日 | 一致 |  |
| 331 | +68 | 円/日 | both_halves.out:7 | 68 | 円/日 | 一致 |  |
| 331 | +76 | 円/日 | both_halves.out:8 | 76 | 円/日 | 一致 |  |
| 331 | +40 | 円/日 | both_halves.out:9 | 40 | 円/日 | 一致 |  |
| 381 | +250 | 円/日 | break_delay/held_reason_break_delay_2.out:8(両方ブレイク、3 本の中の最小) | 246.3 | 円 | 一致 | 10 の位に丸めた範囲の端(k = 2・4・8 の両方ブレイクの円/日 +246.3〜+466.5) |
| 381 | +470 | 円/日 | break_delay/held_reason_break_delay_8.out:8(両方ブレイク、最大) | 466.5 | 円 | 一致 | 10 の位に丸めた範囲の端 |
| 381 | −280 | 円/日 | break_delay/held_reason_break_delay_2.out:11(利確→ブレイク、絶対値の最小) | -281.5 | 円 | 一致 | 10 の位に丸めた範囲の端(−281.5〜−816.4) |
| 381 | −820 | 円/日 | break_delay/held_reason_break_delay_8.out:4(利確→ブレイク、絶対値の最大) | -816.4 | 円 | 一致 | 10 の位に丸めた範囲の端 |
| 381 | +65 | 円/日 | break_delay/held_reason_break_delay_2.out:2 | 65.2 | 円 | 一致 |  |
| 381 | +216 | 円/日 | break_delay/held_reason_break_delay_8.out:2 | 216 | 円 | 一致 |  |
| 382 | −73 | 円/日 | break_delay/scene_diff.out:31 | -73 | 円/日 | 一致 |  |
| 382 | −135 | 円/日 | break_delay/scene_diff.out:31 | -135 | 円/日 | 一致 |  |
| 382 | −2 | 円/日 | both_halves.out:22 | -2 | 円/日 | 一致 |  |
| 383 | +38 | 円/日 | both_halves.out:6 | 38 | 円/日 | 一致 |  |
| 383 | +68 | 円/日 | both_halves.out:7 | 68 | 円/日 | 一致 |  |
| 383 | +76 | 円/日 | both_halves.out:8 | 76 | 円/日 | 一致 |  |
| 383 | +40 | 円/日 | both_halves.out:9 | 40 | 円/日 | 一致 |  |
| 385 | +292 | 円/日 | break_delay/fam_tables.md:112 | 292 | 円 | 一致 |  |
| 385 | +291 | 円/日 | break_delay/fam_tables.md:113 | 291 | 円 | 一致 |  |
| 385 | +329 | 円/日 | break_delay/fam_tables.md:45 | 329 | 円 | 一致 |  |
| 386 | −30 | 円/日 | both_halves.out:16 | -30 | 円/日 | 一致 |  |
| 386 | −32 | 円/日 | break_delay/fam_tables.md:51 | -32 | 円 | 一致 |  |
| 386 | −27 | move_bp | break_delay/scene_diff.out:22 | -27 | 円/日 | 一致 |  |
| 386 | −29 | move_bp | break_delay/fam_tables.md:51 | -29.1 | 円 | 一致 |  |
| 410 | +323 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.first | 16.126(× 20 = 322.52) | bp(口座) | 一致 |  |
| 410 | +195 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.first | 9.76367(× 20 = 195.27) | bp(口座) | 一致 |  |
| 410 | +459 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.first | 22.9424(× 20 = 458.85) | bp(口座) | 一致 |  |
| 410 | −235 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.second | -11.7365(× 20 = -234.73) | bp(口座) | 一致 |  |
| 410 | −317 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.second | -15.8703(× 20 = -317.41) | bp(口座) | 一致 |  |
| 410 | −153 | 円/日 | break_delay_2/diag_tables.json:.d1.segments.second | -7.62594(× 20 = -152.52) | bp(口座) | 一致 |  |
| 411 | +321 | 円/日 | break_delay_3/diag_tables.json:.d1.segments.first | 16.0365(× 20 = 320.73) | bp(口座) | 一致 |  |
| 411 | +192 | 円/日 | break_delay_3/diag_tables.json:.d1.segments.first | 9.60587(× 20 = 192.12) | bp(口座) | 一致 |  |
| 411 | +451 | 円/日 | break_delay_3/diag_tables.json:.d1.segments.first | 22.5524(× 20 = 451.05) | bp(口座) | 一致 |  |
| 411 | −205 | 円/日 | break_delay_3/diag_tables.json:.d1.segments.second | -10.2437(× 20 = -204.87) | bp(口座) | 一致 |  |
| 411 | −286 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[9] | -14.2815(× 20 = -285.63) | bp(口座) | 一致 |  |
| 411 | −125 | 円/日 | break_delay_3/diag_tables.json:.d1.segments.second | -6.22952(× 20 = -124.59) | bp(口座) | 一致 |  |
| 412 | +304 | 円/日 | break_delay_4/diag_tables.json:.d1.segments.first | 15.1766(× 20 = 303.53) | bp(口座) | 一致 |  |
| 412 | +176 | 円/日 | break_delay_4/diag_tables.json:.d1.segments.first | 8.8105(× 20 = 176.21) | bp(口座) | 一致 |  |
| 412 | +435 | 円/日 | break_delay_4/diag_tables.json:.d1.segments.first | 21.7317(× 20 = 434.63) | bp(口座) | 一致 |  |
| 412 | −197 | 円/日 | break_delay_4/diag_tables.json:.d1.segments.second | -9.85795(× 20 = -197.16) | bp(口座) | 一致 |  |
| 412 | −273 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[7] | -13.6684(× 20 = -273.37) | bp(口座) | 一致 |  |
| 412 | −117 | 円/日 | break_delay_4/diag_tables.json:.d1.segments.second | -5.86238(× 20 = -117.25) | bp(口座) | 一致 |  |
| 413 | +236 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.first | 11.7851(× 20 = 235.70) | bp(口座) | 一致 |  |
| 413 | +114 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.first | 5.71527(× 20 = 114.31) | bp(口座) | 一致 |  |
| 413 | +357 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.first | 17.8321(× 20 = 356.64) | bp(口座) | 一致 |  |
| 413 | −233 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.second | -11.628(× 20 = -232.56) | bp(口座) | 一致 |  |
| 413 | −313 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.second | -15.6629(× 20 = -313.26) | bp(口座) | 一致 |  |
| 413 | −158 | 円/日 | break_delay_8/diag_tables.json:.d1.segments.second | -7.87508(× 20 = -157.50) | bp(口座) | 一致 |  |
| 414 | +362 | 円/日 | base/diag_tables.json:.d1.segments.first | 18.1147(× 20 = 362.29) | bp(口座) | 一致 |  |
| 414 | +231 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[4] | 11.558(× 20 = 231.16) | bp(口座) | 一致 |  |
| 414 | +497 | 円/日 | base/diag_tables.json:.d1.segments.first | 24.8558(× 20 = 497.12) | bp(口座) | 一致 |  |
| 414 | −273 | 円/日 | break_delay_2/diag_tables.json:.d1.rows[7] | -13.6684(× 20 = -273.37) | bp(口座) | 一致 |  |
| 414 | −360 | 円/日 | base/diag_tables.json:.d1.segments.second | -17.9998(× 20 = -360.00) | bp(口座) | 一致 |  |
| 414 | −184 | 円/日 | base/diag_tables.json:.d1.segments.second | -9.19333(× 20 = -183.87) | bp(口座) | 一致 |  |
| 426 | +292 | 円/日 | break_delay_3/diag_tables.json:.d7.years.2015 | 14.6104(× 20 = 292.21) | bp(口座) | 一致 |  |
| 426 | +291 | 円/日 | break_delay_4/diag_tables.json:.d7.years.2015 | 14.5444(× 20 = 290.89) | bp(口座) | 一致 |  |
| 426 | +329 | 円/日 | break_delay_8/diag_tables.json:.d7.years.2015 | 16.428(× 20 = 328.56) | bp(口座) | 一致 |  |
| 426 | −230 | 円/日 | break_delay_8/diag_tables.json:.d7.years.2017 | -11.4913(× 20 = -229.83) | bp(口座) | 一致 |  |
| 426 | +111 | 円/日 | break_delay_2/diag_tables.json:.d7.years.2021 | 5.54477(× 20 = 110.90) | bp(口座) | 一致 |  |
| 426 | +177 | 円/日 | break_delay_4/diag_tables.json:.d7.years.2021 | 8.85457(× 20 = 177.09) | bp(口座) | 一致 |  |
| 430 | −0.9 | 円/日 | break_delay_2/diag_tables.json:.d7.all | -0.0452615(× 20 = -0.91) | bp(口座) | 一致 |  |
| 430 | −27.1 | 円/日 | break_delay_2/diag_tables.json:.d7.all | -1.35496(× 20 = -27.10) | bp(口座) | 一致 |  |
| 430 | +24.5 | 円/日 | break_delay_2/diag_tables.json:.d7.all | 1.22542(× 20 = 24.51) | bp(口座) | 一致 |  |
| 430 | 37.1 | 円/日 | break_delay_2/diag_tables.json:.d7.all | 1.85526(× 20 = 37.11) | bp(口座) | 一致 |  |
| 430 | −40 | 円/日 | break_delay/fam_tables.md:111 | -40 | 円 | 一致 |  |
| 430 | −89 | 円/日 | break_delay/fam_tables.md:111 | -89 | 円 | 一致 |  |
| 430 | +3 | 円/日 | break_delay/fam_tables.md:111 | 3 | 円 | 一致 |  |
| 430 | +38 | 円/日 | break_delay/fam_tables.md:111 | 38 | 円 | 一致 |  |
| 430 | +13 | 円/日 | break_delay/fam_tables.md:111 | 13 | 円 | 一致 |  |
| 430 | +64 | 円/日 | break_delay/fam_tables.md:111 | 64 | 円 | 一致 |  |
| 430 | +8 | 円/日 | break_delay_2/diag_tables.json:.d7.years.2016 | 0.399105(× 20 = 7.98) | bp(口座) | 一致 |  |
| 430 | −114 | 円/日 | break_delay/fam_tables.md:111 | -114 | 円 | 一致 |  |
| 430 | −5 | 円/日 | break_delay_2/diag_tables.json:.d7.years.2020 | -0.239805(× 20 = -4.80) | bp(口座) | 一致 |  |
| 430 | +2 | 円/日 | break_delay/fam_tables.md:111 | 2 | 円 | 一致 |  |
| 430 | +35 | 円/日 | break_delay/fam_tables.md:111 | 35 | 円 | 一致 |  |
| 431 | +13.1 | 円/日 | break_delay_3/diag_tables.json:.d7.all | 0.65665(× 20 = 13.13) | bp(口座) | 一致 |  |
| 431 | −21.4 | 円/日 | break_delay_3/diag_tables.json:.d7.all | -1.06856(× 20 = -21.37) | bp(口座) | 一致 |  |
| 431 | +46.3 | 円/日 | break_delay_3/diag_tables.json:.d7.all | 2.31725(× 20 = 46.35) | bp(口座) | 一致 |  |
| 431 | 48.6 | 円/日 | break_delay_3/diag_tables.json:.d7.all | 2.42954(× 20 = 48.59) | bp(口座) | 一致 |  |
| 431 | −42 | 円/日 | break_delay/fam_tables.md:112 | -42 | 円 | 一致 |  |
| 431 | −105 | 円/日 | break_delay/fam_tables.md:112 | -105 | 円 | 一致 |  |
| 431 | +14 | 円/日 | break_delay/fam_tables.md:112 | 14 | 円 | 一致 |  |
| 431 | +68 | 円/日 | break_delay/fam_tables.md:112 | 68 | 円 | 一致 |  |
| 431 | +35 | 円/日 | break_delay/fam_tables.md:112 | 35 | 円 | 一致 |  |
| 431 | +101 | 円/日 | break_delay/fam_tables.md:112 | 101 | 円 | 一致 |  |
| 431 | +6 | 円/日 | break_delay_3/diag_tables.json:.d7.years.2016 | 0.31559(× 20 = 6.31) | bp(口座) | 一致 |  |
| 431 | −81 | 円/日 | break_delay_3/diag_tables.json:.d7.years.2018 | -4.06859(× 20 = -81.37) | bp(口座) | 一致 |  |
| 431 | +48 | 円/日 | break_delay/fam_tables.md:112 | 48 | 円 | 一致 |  |
| 431 | +25 | 円/日 | break_delay_3/diag_tables.json:.d7.years.2022 | 1.25686(× 20 = 25.14) | bp(口座) | 一致 |  |
| 431 | +41 | 円/日 | break_delay/fam_tables.md:112 | 41 | 円 | 一致 |  |
| 432 | +8.4 | 円/日 | break_delay_4/diag_tables.json:.d7.all | 0.419766(× 20 = 8.40) | bp(口座) | 一致 |  |
| 432 | −30.6 | 円/日 | break_delay_4/diag_tables.json:.d7.all | -1.53043(× 20 = -30.61) | bp(口座) | 一致 |  |
| 432 | +43.7 | 円/日 | break_delay_4/diag_tables.json:.d7.all | 2.1872(× 20 = 43.74) | bp(口座) | 一致 |  |
| 432 | 52.7 | 円/日 | break_delay_4/diag_tables.json:.d7.all | 2.63364(× 20 = 52.67) | bp(口座) | 一致 |  |
| 432 | −59 | 円/日 | break_delay/fam_tables.md:113 | -59 | 円 | 一致 |  |
| 432 | −126 | 円/日 | break_delay/fam_tables.md:113 | -126 | 円 | 一致 |  |
| 432 | −1 | 円/日 | break_delay/fam_tables.md:113 | -1 | 円 | 一致 |  |
| 432 | +76 | 円/日 | break_delay/fam_tables.md:113 | 76 | 円 | 一致 |  |
| 432 | +37 | 円/日 | break_delay/fam_tables.md:113 | 37 | 円 | 一致 |  |
| 432 | +114 | 円/日 | break_delay/fam_tables.md:113 | 114 | 円 | 一致 |  |
| 432 | −10 | 円/日 | break_delay_4/diag_tables.json:.d7.years.2016 | -0.482679(× 20 = -9.65) | bp(口座) | 一致 |  |
| 432 | −118 | 円/日 | break_delay/fam_tables.md:113 | -118 | 円 | 一致 |  |
| 432 | +61 | 円/日 | break_delay_4/diag_tables.json:.d7.years.2020 | 3.05051(× 20 = 61.01) | bp(口座) | 一致 |  |
| 432 | +12 | 円/日 | break_delay/fam_tables.md:113 | 12 | 円 | 一致 |  |
| 432 | +57 | 円/日 | break_delay/fam_tables.md:113 | 57 | 円 | 一致 |  |
| 433 | −43.2 | 円/日 | break_delay_8/diag_tables.json:.d7.all | -2.1607(× 20 = -43.21) | bp(口座) | 一致 |  |
| 433 | −86.0 | 円/日 | break_delay_8/diag_tables.json:.d7.all | -4.29952(× 20 = -85.99) | bp(口座) | 一致 |  |
| 433 | +0.0 | 円/日 | break_delay_8/diag_tables.json:.d7.all | 0.00241621(× 20 = 0.05) | bp(口座) | 一致 |  |
| 433 | 62.8 | 円/日 | break_delay_8/diag_tables.json:.d7.all | 3.13827(× 20 = 62.77) | bp(口座) | 一致 |  |
| 433 | −127 | 円/日 | break_delay/fam_tables.md:114 | -127 | 円 | 一致 |  |
| 433 | −200 | 円/日 | break_delay/fam_tables.md:114 | -200 | 円 | 一致 |  |
| 433 | −59 | 円/日 | break_delay/fam_tables.md:114 | -59 | 円 | 一致 |  |
| 433 | +40 | 円/日 | break_delay/fam_tables.md:114 | 40 | 円 | 一致 |  |
| 433 | −8 | 円/日 | break_delay/fam_tables.md:114 | -8 | 円 | 一致 |  |
| 433 | +87 | 円/日 | break_delay/fam_tables.md:114 | 87 | 円 | 一致 |  |
| 433 | −41 | 円/日 | break_delay_8/diag_tables.json:.d7.years.2016 | -2.04666(× 20 = -40.93) | bp(口座) | 一致 |  |
| 433 | −248 | 円/日 | break_delay/fam_tables.md:114 | -248 | 円 | 一致 |  |
| 433 | +21 | 円/日 | break_delay_8/diag_tables.json:.d7.years.2020 | 1.02907(× 20 = 20.58) | bp(口座) | 一致 |  |
| 433 | −30 | 円/日 | break_delay_8/diag_tables.json:.d7.years.2022 | -1.49464(× 20 = -29.89) | bp(口座) | 一致 |  |
| 433 | +20 | 円/日 | break_delay_8/diag_tables.json:.d7.years.2023 | 1.00884(× 20 = 20.18) | bp(口座) | 一致 |  |
| 437 | −259 | 円/日 | break_delay/compare.md:26(基準 全期間 ブレイク 1 本) | -258.8 | 円 | 一致 |  |
| 437 | −243 | 円 | break_delay/compare.md:27 | -243.1 | 円 | 一致 |  |
| 437 | −217 | 円 | break_delay/compare.md:30(k = 8 全期間 ブレイク 1 本) | -217.1 | 円 | 一致 |  |
| 437 | −59 | 円/日 | both_halves.out:8 | -59 | 円/日 | 一致 |  |
| 437 | −126 | 円/日 | both_halves.out:8 | -126 | 円/日 | 一致 |  |
| 437 | −1 | 円/日 | both_halves.out:8 | -1 | 円/日 | 一致 |  |
| 437 | −127 | 円/日 | both_halves.out:9 | -127 | 円/日 | 一致 |  |
| 437 | −200 | 円/日 | both_halves.out:9 | -200 | 円/日 | 一致 |  |
| 437 | −59 | 円/日 | both_halves.out:8 | -59 | 円/日 | 一致 |  |
| 437 | +38 | 円/日 | both_halves.out:6 | 38 | 円/日 | 一致 |  |
| 437 | +13 | 円/日 | both_halves.out:6 | 13 | 円/日 | 一致 |  |
| 437 | +64 | 円/日 | both_halves.out:6 | 64 | 円/日 | 一致 |  |
| 437 | +68 | 円/日 | both_halves.out:7 | 68 | 円/日 | 一致 |  |
| 437 | +35 | 円/日 | both_halves.out:7 | 35 | 円/日 | 一致 |  |
| 437 | +101 | 円/日 | both_halves.out:7 | 101 | 円/日 | 一致 |  |
| 437 | +76 | 円/日 | both_halves.out:8 | 76 | 円/日 | 一致 |  |
| 437 | +37 | 円/日 | both_halves.out:8 | 37 | 円/日 | 一致 |  |
| 437 | +114 | 円/日 | both_halves.out:8 | 114 | 円/日 | 一致 |  |
| 437 | +0.0 | 円/日 | break_delay/fam_tables.md:114 | 0 | 円 | 一致 |  |
| 437 | +250 | 円/日 | break_delay/held_reason_break_delay_2.out:8(両方ブレイク、3 本の中の最小) | 246.3 | 円 | 一致 | 10 の位に丸めた範囲の端(k = 2・4・8 の両方ブレイクの円/日 +246.3〜+466.5) |
| 437 | +470 | 円/日 | break_delay/held_reason_break_delay_8.out:8(両方ブレイク、最大) | 466.5 | 円 | 一致 | 10 の位に丸めた範囲の端 |
| 437 | −280 | 円/日 | break_delay/held_reason_break_delay_2.out:11(利確→ブレイク、絶対値の最小) | -281.5 | 円 | 一致 | 10 の位に丸めた範囲の端(−281.5〜−816.4) |
| 437 | −820 | 円/日 | break_delay/held_reason_break_delay_8.out:4(利確→ブレイク、絶対値の最大) | -816.4 | 円 | 一致 | 10 の位に丸めた範囲の端 |
| 437 | +65 | 円/日 | break_delay/held_reason_break_delay_2.out:2 | 65.2 | 円 | 一致 |  |
| 437 | +216 | 円/日 | break_delay/held_reason_break_delay_8.out:2 | 216 | 円 | 一致 |  |
| 437 | −88 | 円/日 | 計算 break_delay/held_reason_break_delay_2.out:1+4 初めの 2 項の和 +276.9-364.5 | -87.6 | 計算(円) | 出所が無い(計算で再現) |  |
| 437 | −36 | 円/日 | break_delay/held_reason_break_delay_2.out:8+11 (+246.3)+(−281.5) | -35.2 | 計算(円) | 値の誤り(丸めた値どうしの計算) | 出所の値で −35.2 → −35。文書の −36 は丸めた +246・−282 の和 |
| 437 | −200 | 円/日 | break_delay/held_reason_break_delay_4.out:1+4 (+409.6)+(−610.2) | -200.6 | 計算(円) | 値の誤り(丸めた値どうしの計算) | 出所の値で −200.6 → −201。文書の −200 は丸めた +410・−610 の和 |
| 437 | −95 | 円/日 | break_delay/held_reason_break_delay_4.out:8+11 (+386.5)+(−482.3) | -95.8 | 計算(円) | 値の誤り(丸めた値どうしの計算) | 出所の値で −95.8 → −96。文書の −95 は丸めた +387・−482 の和 |
| 437 | −351 | 円/日 | 計算 break_delay/held_reason_break_delay_8.out:1+4 初めの 2 項の和 +465.2-816.4 | -351.2 | 計算(円) | 出所が無い(計算で再現) |  |
| 437 | −209 | 円/日 | break_delay/held_reason_break_delay_8.out:8+11 (+466.5)+(−676.2) | -209.7 | 計算(円) | 値の誤り(丸めた値どうしの計算) | 出所の値で −209.7 → −210。文書の −209 は丸めた +467・−676 の和 |

**2026-10-09_matilda_main_break_delay.md の数**: 拾った数 721。一致 635・出所が無い(計算で再現) 38・単位の誤り(出所の指し方) 36・値の誤り(丸めた値どうしの計算) 8・確かめられない(丸めの境) 4

## 一致以外のものの一覧(行番号つき)

### beard

- **単位の誤り(出所の指し方)**(43): 195 行 +35.8、195 行 +34.1、195 行 +37.5、195 行 −337.8、195 行 −354.5、195 行 −321.4、195 行 −367.0、195 行 −413.0、195 行 −325.8、195 行 +36.4、195 行 −258.8、195 行 −315.2、196 行 +746,134、196 行 −838,374、196 行 +240,650、219 行 +11,610,315、219 行 +10,177,344、220 行 −5,418,507、220 行 −4,695,044、221 行 −6,983,067、221 行 −6,006,006、224 行 +10,177,344、224 行 +11,610,315、259 行 +2.2、259 行 +1.1、259 行 +3.3、259 行 −1.2、259 行 −3.1、259 行 +0.4、259 行 −0.3、259 行 −1.7、259 行 +1.1、259 行 +0.2、259 行 −1.3、259 行 +1.6、259 行 +2.4、259 行 +1.3、259 行 +3.3、259 行 −0.1、259 行 −2.0、259 行 −3.2、259 行 −0.8、259 行 −0.2
- **出所が無い(計算で再現)**(44): 224 行 −10,701,050、224 行 −12,401,574、224 行 −523,706、294 行 +14.8、295 行 +1.5、296 行 +13.3、297 行 +1.7、298 行 +15.1、298 行 +12.0、299 行 −24.1、299 行 −0.2、300 行 −1.1、300 行 −0.7、301 行 +19.5、301 行 +20.8、302 行 +11.2、303 行 −3.2、304 行 +11.0、305 行 −1.0、306 行 +7.3、306 行 +3.5、307 行 −27.3、307 行 −8.0、308 行 −6.5、308 行 −6.8、309 行 +12.0、309 行 +13.5、311 行 +129、311 行 −56、314 行 +266、314 行 −200、314 行 +7.3、314 行 +3.5、314 行 −87、314 行 +32、316 行 +15.1、316 行 +12.0、316 行 +7.3、316 行 +3.5、367 行 −87、367 行 +32、417 行 +63、417 行 +66、417 行 −1
- **値の誤り(最後の桁)**(1): 224 行 −791,259
- **確かめられない(丸めの境)**(1): 316 行 −12

### break_delay

- **出所が無い(計算で再現)**(38): 85 行 +3,768、237 行 −10,420,068、238 行 −10,240,154、239 行 −10,155,299、240 行 −9,931,720、241 行 −10,701,050、315 行 −32、315 行 −8、315 行 +30、315 行 +8、316 行 −47、316 行 +6、316 行 +53、316 行 +16、317 行 −72、317 行 +13、317 行 +63、317 行 +12、318 行 −158、318 行 +31、318 行 +23、318 行 +18、330 行 −317.0、330 行 −246.9、330 行 −298.8、330 行 −223.7、330 行 −279.9、330 行 −209.9、330 行 +30.2、330 行 +23.2、330 行 +48.6、330 行 +39.4、330 行 +61.1、330 行 +52.2、330 行 −88、330 行 −351、437 行 −88、437 行 −351
- **単位の誤り(出所の指し方)**(36): 213 行 −243.1、213 行 −255.3、213 行 −231.2、213 行 −235.0、213 行 −229.7、213 行 −217.1、213 行 −228.8、213 行 −205.9、213 行 −258.8、213 行 +36.4、213 行 +36.8、214 行 +633,304、214 行 −755,561、214 行 +637,311、214 行 −741,974、214 行 +620,803、214 行 −716,091、214 行 +571,011、214 行 −725,471、214 行 +653,497、214 行 −766,805、237 行 +9,889,944、238 行 +9,755,438、239 行 +9,657,027、240 行 +9,321,903、241 行 +10,177,344、279 行 +1.9、279 行 +2.5、279 行 −1.8、279 行 −2.3、279 行 +2.4、279 行 +1.3、279 行 +3.3、279 行 −2.0、279 行 −3.2、279 行 −0.8
- **確かめられない(丸めの境)**(4): 324 行 −365、324 行 −282、325 行 +387、326 行 +467
- **値の誤り(丸めた値どうしの計算)**(8): 330 行 −36、330 行 −200、330 行 −95、330 行 −209、437 行 −36、437 行 −200、437 行 −95、437 行 −209

## 打ったコマンド(主なもの)

- 出所を読む: `cat -n docs/RESEARCH/matilda_main/{beard,break_delay,break_off}/*.out`・`*/fam_tables.md`・`*/compare.md`・`beard_off/diag_tables.md`・`beard_off/diag_paths.md`・`break_off/diag_tables.md`・`base/diag_tables.md`・`both_halves.out`・`break_len_mult/held_reason_break_len_mult_4.out`。
- 台本の単位: `grep -n "pnl_jpy\|pnl_bp\|\* *20" scenes.py scene_diff.py market_side.py same_bar_reason.py band_migration.py levels_band.py levels_reason.py both_halves.py compare_family.py fam_tables.py nearest_signal.py break_off/break_off_detail.py`(`docs/RESEARCH/matilda_main/` で)と `cat -n market_side.py nearest_signal.py same_bar_reason.py break_off/break_off_detail.py fam_tables.py`。
- 突き合わせの台本(作業者の置き場 `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/`。リポジトリには置いていない): `audit.py`(数の拾い出し・出所の候補の行との比べ・計算の再現)、`cfg_beard.py`・`cfg_bd.py`(節ごとの出所の候補と、手で直した行)。`python3 cfg_beard.py out_beard.json`・`python3 cfg_bd.py out_bd.json`・`python3 gen.py`。
- 出所の候補は節ごとに名指しのファイルを先に置き、候補の行のうち文書の行の数を一番多く含む行に寄せる(同じ値が別の場所にあるとき取り違えないため)。取り違えが見えたもの(例: beard 413 行の +37 が全期間の +37.2 に寄った、break_delay 437 行の −259 が k = 4 の成行 −258.9 に寄った)は手で出所を直した(`cfg_*.py` の `tok`・`lines`・`MV`)。

## 読むのをやめた・確かめきれなかった範囲

1. **break_off の文書(`docs/ANAL` `YSIS/2026-10-09_matilda_main_break_off.md`、450 行)は突き合わせていない**。上限の 90 分に達したため。出所の出力(`break_off/fam_tables.md`・`compare.md`・`diag_tables.md`・`band_migration.out`・`levels_*.out`・`scene_diff.out`・`scenes.out`・`market_side.out`・`held_reason.out`・`same_bar_reason.out`・`break_off_detail.out`・`break_len_mult/held_reason_break_len_mult_4.out`)は読んだが、判定は付けていない。読んでいる途中で目に入ったもの(判定ではなく、確かめの手がかり):
   - 199 行の分位は「bp。× 20 = 円」と書いてあり、`break_off/diag_tables.md:46` の bp(1% −50.60)と `base/diag_tables.md` の bp(1% −33.70)に同じ数がある。−1,012・−674 円はその × 20。
   - 300〜303 行の円/日は `held_reason.out`・`same_bar_reason.out` の diff/day を丸めたもの(+1,020 ← +1020.0、−911 ← −910.7、+978 ← +977.5(.5 の境)、−864 ← −863.8、+48 ← +47.6、+33 ← +33.2)。+978 は丸めの境に当たる。
   - 313 行・414 行の +109 / +114 は計算(+1,020 − 911 = +109、+978 − 864 = +114。出所の値では +1020.0 − 910.7 = +109.3、+977.5 − 863.8 = +113.7 → +114)。
   - 197 行の「約 −5,439,000 円(4,325 × −1,257.6)」は、出所に `break_off/diag_tables.json` の D3 market の和(md では −271955 bp、× 20 = −5,439,100 円)がある。
2. **break_delay の「一致」の行の出所の列**は、値は機械で合っているが、出所の行が文書の意図した行かを全部は目で見ていない(同じ値が別の升目にある小さな整数で取り違えが起こりうる。値が同じなので判定は変わらないが、出所の列が別の升目を指している行が残っている可能性がある)。beard は最初の出力の全部の行を目で見て、見えた取り違えを直した(直した後の出力を全部見直してはいない)。
3. **丸めの境(確かめられない)の 5 件**は、出所の全桁が出力に無い(`same_bar_reason.py` は小数 1 桁で書く)。取引の行から数え直せば決まるが、読むだけの仕事なので台本を回していない。
4. 拾い出しは機械の決まり(上の「決めたこと」)による。符号の無い損益の数で MDE・D4 の MFE 以外の形のものは拾っていない(見て回った範囲では無かったが、全部を目で確かめてはいない)。
5. UNITS_MAP §3 の 3 点のうち、この 3 文書に当たるのは無かった(D7 の共通の日の件は、beard・break_delay・break_off とも期間の始まりが基準と同じ 2015-12-01 で、`fam_tables.md` の D0 の表で確かめた)。
