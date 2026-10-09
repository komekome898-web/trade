# 数の突き合わせ 3(step・break_dist・break_len_mult の分析の文書)

作業者が書いた(2026-10-09、読むだけの仕事。文書・台帳・コードは変えていない)。書いたのはこのファイルだけ。

## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 3 つの文書(step・break_dist・break_len_mult)の、行頭が `>` でない行の損益・値動きの数を全部拾い、文書が指す出所の出力の値・単位と 1 つずつ突き合わせる | 「**もっと徹底的に調べて影響範囲を確定させてください。**」 |
| 1 つずつ判定(一致 / 単位の誤り / 値の誤り / 出所が無い・見つからない / 確かめられない)を付け、この audit_3.md に表で書く | **(該当語なし)**(リードの委任文の指示) |
| 円の出力(fam_tables.md)が、読み口の bp の出力(diag_tables.json・diag_paths.json)の × 20 と合うかも数え、単位の連鎖を確かめる | **(該当語なし)**(委任文「円の数は、出所が bp なら × 20 して比べる」) |
| 出力ファイルに無い数 1 つ(+16,834 円)を、取引の行(`trades.csv.gz`)から読んで計算し直す | **(該当語なし)**(リードの判断が要るなら、この 1 行は外してよい。判定は「出力ファイルには無い」と添えて書いた) |

見込み時間(着手時): 上限 90 分。内訳 = 単位の地図と 3 文書を読む 15 分 + 数を拾う台本と突き合わせの台本を作る 20 分 + 文書ごとの突き合わせと一致しないものの読み 3 × 12 分 = 36 分 + 書く 15 分 = 86 分。
実際: 08:49 UTC に着手、09:05 UTC に書き終えた(上限の内)。

完了の形(委任文の逐語): 「文書に書かれた数が、出所の出力ファイルの値・単位と合っているかを、1 つずつ機械的に確かめる」。

## 判定ごとの個数(3 文書の合計)

| 文書 | 拾った数 | 一致 | 単位の誤り | 値の誤り | 出所が無い・見つからない | 確かめられない |
|---|---|---|---|---|---|---|
| step | 673 | 655 | 0 | 0 | 18 | 0 |
| break_dist | 683 | 676 | 0 | 1 | 6 | 0 |
| break_len_mult | 403 | 375 | 18 | 4 | 6 | 0 |
| 合計 | 1759 | 1706 | 18 | 5 | 30 | 0 |

- 出所の値を計算で作った行(差・和・積・和 ÷ 本数。出所の値をそのまま写した数ではない)は、「出所の単位」を「円(計算)」とし、式か計算に使った出所の行を書いた。step 17 行(うち一致 17)・break_dist 66 行(うち一致 65)・break_len_mult 40 行(うち一致 36)。
- 一致のうち、出所の書き方に注意が要るもの(値は合う)は、下の「注記」に行番号を書いた。判定は一致のまま。

## 拾い方と判定の決まり

- 拾った数: 行頭が `>` でない行の、符号つきの数(`+`・`−`・`-`)全部と、符号の無い MDE(「(146)」「MDE 41.5」)・D4 の表の MFE の中央値・「万」の付いた数・「±1,300〜1,600」の形の範囲。外した数: 本数・日数・割合・とんとん・差(ポイント)・段の数の平均・上限段の割合・倍・%・年・日付・時刻・`L-`・`K-` の番号・「+1 分」のような時間(数の後ろが 本・日・分・年・段・ボラ・倍・% などのもの)。D10 の表 2(差(ポイント))は全部外した。
- 書かれた単位: 文書の表の見出し・文の単位。「円」は 円・円/日・円/取引 をまとめた書き方。「move_bp」は文書が move_bp と書いた節(D4 の MFE・MAE と出の後の値動き、D5)。
- 突き合わせ: 文書の行ごとに、文書が指す出所の行を決め(表の行は出所の同じ行と順に、本文の箇条は出所の行の範囲の中で)、同じ数を探した。出所の表示の桁が多いときは、文書の桁に丸めて合えば一致(許す差は文書の最後の桁の半分)。
- 円の数で、文書の出所が読み口(bp)のときは、写しの `fam_tables.md`(円)で比べ、さらに同じ本の `diag_tables.json`・`diag_paths.json` の値 × 20 を表の「出所」「出所の値」の欄に並べた(「/」の右)。json の数は表示より桁が多いので、md の 2 桁の bp を × 20 したときの丸めのずれ(例: D6 −0.01 bp × 20 = −0.2 と、json の −0.01374 × 20 = −0.27 → −0.3)は起きない。
- 計算値(差・和・和 ÷ 本数)は、出所の表示の値か和から計算し、式を「出所の値」に書いた。
- 本文の箇条で、同じ値が出所の範囲の別の行にもあって機械の当てが別の行を指したもの(例: break_dist 397 行の +69 が fam_tables.md の MDE +68.8 に当たった)は、読んで正しい行に直した(直した行は表の出所の欄に正しい行だけを書いた)。

## 一致以外のもの(行番号つき)

### step(`docs/ANALYSIS/2026-10-09_matilda_main_step.md`)

- **出所が無い・見つからない 18**: 157〜159 行(D2 の場面の表)の base の 3 列(前半 base・後半 base の点と区間、3 場面 × 2 × 3 = 18)。153 行は「基準の値は `alert/scenes.out` の base の行」と書くが、`docs/RESEARCH/matilda_main/alert/scenes.out` には alert_x1・alert_x2 の行しか無い(読んだ: 24 行全部)。同じ 18 の値は `docs/RESEARCH/matilda_main/base_scenes.out:5・6・8・9・11・12` にある(円。単位は合う)。

### break_dist(`docs/ANALYSIS/2026-10-09_matilda_main_break_dist.md`)

- **出所が無い・見つからない 6**: 157〜159 行の「前半 base」「後半 base」(+264・−216・+411・−282・+656・−343)。153 行が `alert/scenes.out` の base の行を指すが、その行は無い。同じ値は `base_scenes.out:5・6・8・9・11・12`。
- **値の誤り 1**: 345 行「升目の和は … 後半 +112(0.25)」。`break_dist/band_migration.out:11-18` の和から計算すると、本の和 −237,631 − 基準の和 −400,821 = +163,190 円 ÷ 1,470 = **+111.01**。文書の +112 は表示した升目の丸めた差(−0・+0・−4・+101・+3・+41・−63・+34)の和。同じ行の前半 −17(−16.84)・1 の前半 +110(+110.09)・後半 −16(−16.20)は和からの計算と合う。

### break_len_mult(`docs/ANALYSIS/2026-10-09_matilda_main_break_len_mult.md`)

- **出所が無い・見つからない 6**: 156〜158 行の「前半 base」「後半 base」(+264・−216・+411・−282・+656・−343)。152 行が `alert/scenes.out` の base の行を指すが、その行は無い。同じ値は `base_scenes.out:5・6・8・9・11・12`。
- **単位の誤り 18**(出所の指し方。値は合う): 259 行の D6 の 18 の数(本 12・基準 6)。行は「読み口の「D6 固まり」(1 取引あたり 円 [区間]。帯の境は標本の中)」とだけ書き、読み口の D6 は bp(`break_len_mult_4/diag_tables.md` の D6 は「1 取引あたり bp」)。× 20 とも、写しの `fam_tables.md` とも書いていない。値は `break_len_mult/fam_tables.md:65・66`(円 = bp × 20)と全部合う。step(293 行)と break_dist(278 行)の同じ節は「`fam_tables.md` の D6」と書いているので一致にした。
- **値の誤り 4**(どれも 305・307 行の、band_migration.out の升目の和):
  - 305 行「全部の升目の和は前半 +344」: 和から計算すると +1,036,690 − 532,210 = +504,480 円 ÷ 1,469 = **+343.42**(`d7_fullperiod.out:12` の前半 +343.4 と同じ)。+344 は表示した升目の丸めた値の和。
  - 305 行「後半 +67」: −301,422 − (−400,820) = +99,398 円 ÷ 1,470 = **+67.62**(丸めると +68)。+67 は表示した升目の丸めた値の和。
  - 305 行「D7 の前半 +356 と 12 円/日違う」: +356 − 343.42 = **+12.58**(丸めると 13)。12 は +344 から出た値。
  - 307 行「ブレイク中が減って新しく建った取引の分(+79)」: `band_migration.out:3・4` の (+78,610 + 36,449) ÷ 1,469 = **+78.32**。+79 は表示した +54・+25 の和。同じ行の後半の +6(+6.32)は合う。

## 注記(判定は一致。値は合うが、出所の書き方か出所の種類に注意が要るもの)

- break_dist 228 行・break_len_mult 215 行(D4 の表。break_dist 232〜234 行の和 9 個、break_len_mult 219〜221 行の和 6 個): 出所を「`…/diag_paths.md`(move_bp。… 和は円。写しは `fam_tables.md` の D4)」と書く。`diag_paths.md` の D4 の「損益の和」は pnl_bp(例 break_dist_0.25 の勝った群 +404,296 bp)で、× 20 とは書いていない。写しの `fam_tables.md`(円)を挙げているので一致にした。step 243 行は「損益の和は × 20 で円」と書いている。UNITS_MAP §3 の range_hi の D4 と同じ形の書き方。
- break_len_mult 177 行(D3。195・196 行の 15 個): 「`break_len_mult/compare.md`(円)と読み口の D3(写しは `fam_tables.md`)」。読み口の D3 は bp で、× 20 とは書いていない(step 186 行・break_dist 186 行は「bp × 20 = 円」と書く)。写しを挙げているので一致にした。
- break_len_mult 305 行の +16,834 円・11.5 円/日: 出力ファイル(`docs/RESEARCH/matilda_main/` の下)には無い(Grep で 16,834 は 0 件)。文書の数の元は相方の記録 `docs/RESEARCH/partner/2026-10-09_matilda_main_break_len_mult/01_D9b_reply.md:40`。取引の行 `backtest_runs_shared/matilda_main_trades/base/trades.csv.gz` から、合図の日が 2015-12-05 より前の行を数えると 20 本・pnl_jpy の和 +16,833.992 円(÷ 1,469 = 11.46)で合う。
- break_dist 346・347・397 行の「±1,300〜1,600」「±1,200〜1,600」は丸めた範囲として突き合わせた(出所 `held_reason_break_dist_1.out:1・2・8・9` の 1,324.0〜1,588.6、`held_reason_break_dist_0.25.out:1・4・8・10` の 1,176.8〜1,278.0)。
- break_dist の same_bar_reason・held_reason の出力は UNITS_MAP の表に載っていない。単位は円(`docs/RESEARCH/matilda_main/same_bar_reason.py:23` が `pnl_jpy` を足し、`:25` で 1 本あたりと ÷ 1,469 / 1,470 の 1 日あたりを出す)。
- 計算値で、表示の値(丸めた値)の差から作った数(step 338・438 行の帯の分解、break_dist 323 行)は、出所の表示の値の差と合う。表示の前の値は fam_tables.md に無いので、表示の前の値での差は確かめていない(帯の 1 日あたりは json に無く、`fam_tables.py` が取引の行から作る)。

## 単位の地図(UNITS_MAP.md)との突き合わせ

- §1 の 1 bp = 20 円: 合う。例 step_2 の `summary.json` の pnl_jpy 35024.494 と、`step_2/diag_tables.json` の d0.signal_delay.within.sum 1751.2247 bp × 20 = 35,024.49。
- §2 の `fam_tables.md` は `y()` で × 20 した円: 合う。`fam_tables.md` の D1・D3(出の理由・保有時間・上位下位の日)・D4・D5・D6・D7 の数を、同じ本の json(× 20、D4 の MFE・MAE と出の後・D5 はそのまま)と比べた(下の「連鎖」)。合わないのは D7 の前半・後半(json に無い。`fam_tables.py` が作る)だけで、それらは `both_halves.out`(円)と合う(step_2 −116 [−163, −72]・+50 [+16, +84]、step_4 −233 [−314, −160]・+66 [+12, +116]、break_dist_0.25 −17 [−94, +61]・+111 [+54, +174]、break_dist_1 +110 [+19, +213]・−16 [−96, +58]、break_len_mult_4 +356 [+264, +459]・+68 [+10, +124])。
- §2 の `diag_paths` の D4 の和は pnl_bp: 合う(例 step_2 勝った群 +338,286.84 bp × 20 = +6,765,737 円 = fam_tables.md:48)。
- §2 の `compare.md`・`band_migration.out` などは pnl_jpy を直接読む円: `band_migration.py:15` が `pnl_jpy` を読む。合う。
- §3 の 1 点目(読み口の D7 は共通の日だけ): break_len_mult の文書は 288 行で自分で書き、`d7_fullperiod.out:11-14` の値(+205.5 [+150.0, +263.2]・+343 [+246, +442]・+68 [+10, +124]・−1,070 [−2,180, −148])を写している。合う。
- 地図に無い問題として見つけたもの: 3 文書とも、D2 の場面の表の base の値の出所を `alert/scenes.out` の base の行と書くが、その行は無い(値は `base_scenes.out`)。単位は円で合う。

## 連鎖: fam_tables.md(円)と json(bp)× 20

`chain.py <族> <本…>`(手で書いた台本。fam_tables.md の D1・D3 出の理由・D4・D5・D6・D7 の行の数を、その行の本の `diag_tables.json`・`diag_paths.json` の値 × 20(円)かそのまま(move_bp)と比べる。保有 0 分の帯の表と D0 は除く)の出力:

```
step: 確かめた数 375、json と一致 361、合わない 14   ← 14 は全部 D7 の前半・後半と MDE(step_2 −116 −163 −72 +66 +50 +16 +47、step_4 −233 −314 −160 +66 +12 +116 +72)
break_dist: 確かめた数 357、json と一致 345、合わない 12   ← 12 は全部 D7 の前半・後半と MDE
break_len_mult: 確かめた数 229、json と一致 223、合わない 6   ← 6 は全部 D7 の前半・後半と MDE
```

(この台本は値が json の中のどれかと合うかを見るので、小さい数は別の欄と偶然合うことがある。文書の数ごとの表では、節を決めて json の場所を書いた。)

## 打ったコマンド(主なもの)

台本は作業場 `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/a3w/` に置いた(作業場は共有で、同じ名前の別の作業者の台本に上書きされたので、途中から専用の置き場に移した)。

```
# 出所を読む
cat -n docs/RESEARCH/matilda_main/{step,break_dist,break_len_mult}/{fam_tables.md,compare.md,*.out}
cat -n docs/RESEARCH/matilda_main/{step_2,base}/diag_tables.md docs/RESEARCH/matilda_main/step_2/diag_paths.md
cat -n docs/RESEARCH/matilda_main/{base_scenes.out,alert/scenes.out,both_halves.out,d7_fullperiod.out}
# 文書の数を拾う(行頭が > の行は飛ばす)
CFG=cfg_step.json OUT=step_rows.json python3 extract.py docs/ANAL""YSIS/2026-10-09_matilda_main_step.md   → 673 tokens
CFG=cfg_bd.json   OUT=bd_rows.json   python3 extract.py docs/ANAL""YSIS/2026-10-09_matilda_main_break_dist.md → 680 tokens
CFG=cfg_blm.json  OUT=blm_rows.json  python3 extract.py docs/ANAL""YSIS/2026-10-09_matilda_main_break_len_mult.md → 400 tokens
# 行ごとに決めた出所の行で探す
python3 check2.py step_rows.json map_step.json step_check.tsv   → OK 661 / MISS 12(全部 計算値。手で式を書いた)
python3 check2.py bd_rows.json map_bd.json bd_check.tsv         → OK 667 / MISS 13(計算値 12・値の誤り 1)
python3 check2.py blm_rows.json map_blm.json blm_check.tsv      → OK 396 / MISS 4(値の誤り 3・取引の行から計算し直し 1)
# band_migration.out の 1 本あたり(和 ÷ 本数)と升目の差の和
python3 bm_derive.py docs/RESEARCH/matilda_main/break_dist/band_migration.out
python3 bm_derive.py docs/RESEARCH/matilda_main/break_len_mult/band_migration.out
# 連鎖
python3 chain.py step step_2 step_4 / python3 chain.py break_dist break_dist_0.25 break_dist_1 / python3 chain.py break_len_mult break_len_mult_4
# 出所を探す
Grep '\+264 \[|1,?007\]' docs → base_scenes.out:5・11(と range_lo/scenes.out の別の値 +264 [+155, +357])
Grep '16,?834|11\.5' docs/RESEARCH/matilda_main → 16,834 は 0 件(11.5 は別の本・別の欄の値だけ)
grep -rln '16,834' docs/RESEARCH/partner → 01_D9b_reply.md
python3 -I -c "…trades.csv.gz の signal_t[:10] < '2015-12-05' の行を数えて pnl_jpy を足す…" → 20 16833.992 11.46
grep -n pnl same_bar_reason.py band_migration.py → same_bar_reason.py:23 pnl_jpy、band_migration.py:15 pnl_jpy
python3 -c "…break_len_mult_4/diag_tables.json d1.segments.first.n…" → 1465
# 表を作る
python3 report.py step step_check.tsv step step_2 step_4            → step 673 {'一致': 655, '出所が無い・見つからない': 18}
python3 report.py bd bd_check.tsv break_dist break_dist_0.25 break_dist_1 → bd 683 {'一致': 676, '出所が無い・見つからない': 6, '値の誤り': 1}
python3 report.py blm blm_check.tsv break_len_mult break_len_mult_4  → blm 403 {'一致': 375, '出所が無い・見つからない': 6, '単位の誤り': 18, '値の誤り': 4}
```

## 読むのをやめた・確かめきれなかった範囲

- 対象外にした数(損益・値動きの数ではないとした): 割合・とんとん・差(ポイント)・段の数の平均・上限段の割合・本数・日数・倍・%。ただし損益の比である「0.69・0.43 倍」「0.72・0.48 倍」(step 224 行)、「0.66・0.40 倍」「0.69・0.46 倍」(step 252・438 行)、「86%・99%」(step 338 行)は、表示の値から計算して合うことだけ見た(例 32.2 ÷ 46.7 = 0.689、−100 ÷ −116 = 86%)。表には入れていない。
- 保有 0 分の帯の 1 日あたり(3 文書の D3 の帯の表と、それを使う本文)は、写しの `fam_tables.md` と合うことまで。json に無い数なので、bp × 20 の連鎖は確かめていない。取引の行から作り直してもいない。
- D7 の前半・後半(3 文書)は `fam_tables.md` と `both_halves.out`(どちらも円)で合うことまで。MDE(+66・+47 など)は `fam_tables.md` にしか無い。
- 本文の箇条は、行ごとに決めた出所の行の範囲の中で探した。範囲の中で同じ値が 2 か所にあるとき、機械が当てた行を全部読み直してはいない(読み直して直したのは「拾い方と判定の決まり」の最後の項に書いた種類のもの: step 338・438 行、break_dist 323・332・342・343・346・397・447 行、break_len_mult 305・307・324 行)。
- `summary.json` との突き合わせは 6 本の pnl_jpy の合計だけ(各文書の 56 行)。

## 文書ごとの表

### step(`docs/ANALYSIS/2026-10-09_matilda_main_step.md`)

拾った数 673: 一致 655・単位の誤り 0・値の誤り 0・出所が無い・見つからない 18・確かめられない 0

| 文書の行 | 書かれた数 | 書かれた単位 | 出所 ファイル:行 | 出所の値 | 出所の単位 | 判定 |
|---|---|---|---|---|---|---|
| 56 | +35,024.494 | 円 | step/fam_tables.md:7 | 35024.494 | 円 | 一致 |
| 56 | −113,745.271 | 円 | step/fam_tables.md:8 | -113745.271 | 円 | 一致 |
| 84 | −158 | 円 | step/market_side.out:1 | -158 | 円 | 一致 |
| 84 | −526 | 円 | step/market_side.out:2 | -526 | 円 | 一致 |
| 84 | +35,024 | 円 | step/fam_tables.md:7 | 35024.494 | 円 | 一致 |
| 84 | −113,745 | 円 | step/fam_tables.md:8 | -113745.271 | 円 | 一致 |
| 112 | +247 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.segments.first.mean | +247 / +12.3303 bp(× 20 = +246.61 円) | 円 / bp | 一致 |
| 112 | +147 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.segments.first.lo | +147 / +7.3620 bp(× 20 = +147.24 円) | 円 / bp | 一致 |
| 112 | +349 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.segments.first.hi | +349 / +17.4493 bp(× 20 = +348.99 円) | 円 / bp | 一致 |
| 112 | 146 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.segments.first.mde | +146 / +7.3229 bp(× 20 = +146.46 円) | 円 / bp | 一致 |
| 112 | −223 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.segments.second.mean | -223 / -11.1306 bp(× 20 = -222.61 円) | 円 / bp | 一致 |
| 112 | −290 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.segments.second.lo | -290 / -14.4894 bp(× 20 = -289.79 円) | 円 / bp | 一致 |
| 112 | −159 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.segments.second.hi | -159 / -7.9505 bp(× 20 = -159.01 円) | 円 / bp | 一致 |
| 112 | 92 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.rows[0].mde または d1.segments.second.mde | +92 / +4.5825 bp(× 20 = +91.65 円) | 円 / bp | 一致 |
| 112 | −469 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.segments.diff.mean | -469 / -23.4610 bp(× 20 = -469.22 円) | 円 / bp | 一致 |
| 112 | −600 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.segments.diff.lo | -600 / -29.9922 bp(× 20 = -599.84 円) | 円 / bp | 一致 |
| 112 | −349 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.segments.diff.hi | -349 / -17.4361 bp(× 20 = -348.72 円) | 円 / bp | 一致 |
| 113 | +129 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.first.mean | +129 / +6.4528 bp(× 20 = +129.06 円) | 円 / bp | 一致 |
| 113 | +59 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.first.lo | +59 / +2.9603 bp(× 20 = +59.21 円) | 円 / bp | 一致 |
| 113 | +199 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.first.hi | +199 / +9.9662 bp(× 20 = +199.32 円) | 円 / bp | 一致 |
| 113 | 102 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.first.mde | +102 / +5.0987 bp(× 20 = +101.97 円) | 円 / bp | 一致 |
| 113 | −206 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.second.mean | -206 / -10.3173 bp(× 20 = -206.35 円) | 円 / bp | 一致 |
| 113 | −251 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.second.lo | -251 / -12.5349 bp(× 20 = -250.70 円) | 円 / bp | 一致 |
| 113 | −165 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.second.hi | -165 / -8.2486 bp(× 20 = -164.97 円) | 円 / bp | 一致 |
| 113 | 63 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.second.mde | +63 / +3.1616 bp(× 20 = +63.23 円) | 円 / bp | 一致 |
| 113 | −335 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.diff.mean | -335 / -16.7700 bp(× 20 = -335.40 円) | 円 / bp | 一致 |
| 113 | −425 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.diff.lo | -425 / -21.2594 bp(× 20 = -425.19 円) | 円 / bp | 一致 |
| 113 | −250 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.diff.hi | -250 / -12.5132 bp(× 20 = -250.26 円) | 円 / bp | 一致 |
| 114 | +362 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.first.mean | +362 / +18.1147 bp(× 20 = +362.29 円) | 円 / bp | 一致 |
| 114 | +231 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.first.lo | +231 / +11.5545 bp(× 20 = +231.09 円) | 円 / bp | 一致 |
| 114 | +497 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.first.hi | +497 / +24.8558 bp(× 20 = +497.12 円) | 円 / bp | 一致 |
| 114 | 195 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.first.mde | +195 / +9.7558 bp(× 20 = +195.12 円) | 円 / bp | 一致 |
| 114 | −273 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.second.mean | -273 / -13.6334 bp(× 20 = -272.67 円) | 円 / bp | 一致 |
| 114 | −360 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.second.lo | -360 / -17.9998 bp(× 20 = -360.00 円) | 円 / bp | 一致 |
| 114 | −184 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.second.hi | -184 / -9.1933 bp(× 20 = -183.87 円) | 円 / bp | 一致 |
| 114 | 125 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.second.mde | +125 / +6.2593 bp(× 20 = +125.19 円) | 円 / bp | 一致 |
| 114 | −635 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.diff.mean | -635 / -31.7481 bp(× 20 = -634.96 円) | 円 / bp | 一致 |
| 114 | −805 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.diff.lo | -805 / -40.2715 bp(× 20 = -805.43 円) | 円 / bp | 一致 |
| 114 | −476 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.diff.hi | -476 / -23.8222 bp(× 20 = -476.44 円) | 円 / bp | 一致 |
| 120 | −133 | 円 | step/fam_tables.md:23 / step_2/diag_tables.json d1.rows[1].mean | -133 / -6.6422 bp(× 20 = -132.84 円) | 円 / bp | 一致 |
| 120 | +88 | 円 | step/fam_tables.md:23 / step_2/diag_tables.json d1.rows[2].mean | +88 / +4.3769 bp(× 20 = +87.54 円) | 円 / bp | 一致 |
| 120 | +441 | 円 | step/fam_tables.md:23 / step_2/diag_tables.json d1.rows[3].mean | +441 / +22.0475 bp(× 20 = +440.95 円) | 円 / bp | 一致 |
| 120 | +344 | 円 | step/fam_tables.md:23 / step_2/diag_tables.json d1.rows[4].mean | +344 / +17.2189 bp(× 20 = +344.38 円) | 円 / bp | 一致 |
| 120 | +130 | 円 | step/fam_tables.md:23 / step_2/diag_tables.json d1.rows[5].mean | +130 / +6.5132 bp(× 20 = +130.26 円) | 円 / bp | 一致 |
| 120 | −56 | 円 | step/fam_tables.md:23 / step_2/diag_tables.json d1.rows[6].mean | -56 / -2.8001 bp(× 20 = -56.00 円) | 円 / bp | 一致 |
| 120 | −339 | 円 | step/fam_tables.md:23 / step_2/diag_tables.json d1.rows[7].mean | -339 / -16.9435 bp(× 20 = -338.87 円) | 円 / bp | 一致 |
| 120 | −177 | 円 | step/fam_tables.md:23 / step_2/diag_tables.json d1.rows[8].mean | -177 / -8.8498 bp(× 20 = -177.00 円) | 円 / bp | 一致 |
| 120 | −337 | 円 | step/fam_tables.md:23 / step_2/diag_tables.json d1.rows[9].mean | -337 / -16.8517 bp(× 20 = -337.03 円) | 円 / bp | 一致 |
| 120 | +12 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.rows[0].mean | +12 / +0.5959 bp(× 20 = +11.92 円) | 円 / bp | 一致 |
| 120 | −53 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.rows[0].lo | -53 / -2.6685 bp(× 20 = -53.37 円) | 円 / bp | 一致 |
| 120 | +73 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.rows[0].hi | +73 / +3.6339 bp(× 20 = +72.68 円) | 円 / bp | 一致 |
| 121 | −21 | 円 | step/fam_tables.md:24 / step_4/diag_tables.json d1.rows[1].mean | -21 / -1.0565 bp(× 20 = -21.13 円) | 円 / bp | 一致 |
| 121 | +96 | 円 | step/fam_tables.md:24 / step_4/diag_tables.json d1.rows[2].mean | +96 / +4.8069 bp(× 20 = +96.14 円) | 円 / bp | 一致 |
| 121 | +262 | 円 | step/fam_tables.md:24 / step_4/diag_tables.json d1.rows[3].mean | +262 / +13.0974 bp(× 20 = +261.95 円) | 円 / bp | 一致 |
| 121 | +154 | 円 | step/fam_tables.md:24 / step_4/diag_tables.json d1.rows[4].mean | +154 / +7.6826 bp(× 20 = +153.65 円) | 円 / bp | 一致 |
| 121 | +7 | 円 | step/fam_tables.md:24 / step_4/diag_tables.json d1.rows[5].mean | +7 / +0.3545 bp(× 20 = +7.09 円) | 円 / bp | 一致 |
| 121 | −103 | 円 | step/fam_tables.md:24 / step_4/diag_tables.json d1.rows[6].mean | -103 / -5.1574 bp(× 20 = -103.15 円) | 円 / bp | 一致 |
| 121 | −293 | 円 | step/fam_tables.md:24 / step_4/diag_tables.json d1.rows[7].mean | -293 / -14.6298 bp(× 20 = -292.60 円) | 円 / bp | 一致 |
| 121 | −197 | 円 | step/fam_tables.md:24 / step_4/diag_tables.json d1.rows[8].mean | -197 / -9.8250 bp(× 20 = -196.50 円) | 円 / bp | 一致 |
| 121 | −246 | 円 | step/fam_tables.md:24 / step_4/diag_tables.json d1.rows[9].mean | -246 / -12.2915 bp(× 20 = -245.83 円) | 円 / bp | 一致 |
| 121 | −39 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.rows[0].mean | -39 / -1.9351 bp(× 20 = -38.70 円) | 円 / bp | 一致 |
| 121 | −82 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.rows[0].lo | -82 / -4.1205 bp(× 20 = -82.41 円) | 円 / bp | 一致 |
| 121 | +6 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.rows[0].hi | +6 / +0.2801 bp(× 20 = +5.60 円) | 円 / bp | 一致 |
| 122 | −263 | 円 | step/fam_tables.md:25 / base/diag_tables.json d1.rows[1].mean または d1.rows[8].mean | -263 / -13.1430 bp(× 20 = -262.86 円) | 円 / bp | 一致 |
| 122 | +133 | 円 | step/fam_tables.md:25 / base/diag_tables.json d1.rows[2].mean | +133 / +6.6326 bp(× 20 = +132.65 円) | 円 / bp | 一致 |
| 122 | +564 | 円 | step/fam_tables.md:25 / base/diag_tables.json d1.rows[3].mean | +564 / +28.1875 bp(× 20 = +563.75 円) | 円 / bp | 一致 |
| 122 | +543 | 円 | step/fam_tables.md:25 / base/diag_tables.json d1.rows[4].mean | +543 / +27.1491 bp(× 20 = +542.98 円) | 円 / bp | 一致 |
| 122 | +244 | 円 | step/fam_tables.md:25 / base/diag_tables.json d1.rows[5].mean | +244 / +12.2149 bp(× 20 = +244.30 円) | 円 / bp | 一致 |
| 122 | +6 | 円 | step/fam_tables.md:25 / base/diag_tables.json d1.rows[6].mean | +6 / +0.2952 bp(× 20 = +5.90 円) | 円 / bp | 一致 |
| 122 | −384 | 円 | step/fam_tables.md:25 / base/diag_tables.json d1.rows[7].mean | -384 / -19.2131 bp(× 20 = -384.26 円) | 円 / bp | 一致 |
| 122 | −263 | 円 | step/fam_tables.md:25 / base/diag_tables.json d1.rows[1].mean または d1.rows[8].mean | -263 / -13.1430 bp(× 20 = -262.86 円) | 円 / bp | 一致 |
| 122 | −479 | 円 | step/fam_tables.md:25 / base/diag_tables.json d1.rows[9].mean | -479 / -23.9354 bp(× 20 = -478.71 円) | 円 / bp | 一致 |
| 122 | +45 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.rows[0].mean | +45 / +2.2353 bp(× 20 = +44.71 円) | 円 / bp | 一致 |
| 122 | −41 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.rows[0].lo | -41 / -2.0563 bp(× 20 = -41.13 円) | 円 / bp | 一致 |
| 122 | +124 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.rows[0].hi | +124 / +6.2076 bp(× 20 = +124.15 円) | 円 / bp | 一致 |
| 124 | +362 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.first.mean | +362 / +18.1147 bp(× 20 = +362.29 円) | 円 / bp | 一致 |
| 124 | +247 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.segments.first.mean | +247 / +12.3303 bp(× 20 = +246.61 円) | 円 / bp | 一致 |
| 124 | +129 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.first.mean | +129 / +6.4528 bp(× 20 = +129.06 円) | 円 / bp | 一致 |
| 124 | −273 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.second.mean | -273 / -13.6334 bp(× 20 = -272.67 円) | 円 / bp | 一致 |
| 124 | −223 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.segments.second.mean | -223 / -11.1306 bp(× 20 = -222.61 円) | 円 / bp | 一致 |
| 124 | −206 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.second.mean | -206 / -10.3173 bp(× 20 = -206.35 円) | 円 / bp | 一致 |
| 124 | +12 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.rows[0].mean | +12 / +0.5959 bp(× 20 = +11.92 円) | 円 / bp | 一致 |
| 124 | −39 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.rows[0].mean | -39 / -1.9351 bp(× 20 = -38.70 円) | 円 / bp | 一致 |
| 157 | +178 | 円 | step/scenes.out:5 | +178 | 円 | 一致 |
| 157 | +104 | 円 | step/scenes.out:5 | +104 | 円 | 一致 |
| 157 | +244 | 円 | step/scenes.out:5 | +244 | 円 | 一致 |
| 157 | +82 | 円 | step/scenes.out:17 | +82 | 円 | 一致 |
| 157 | +30 | 円 | step/scenes.out:17 | +30 | 円 | 一致 |
| 157 | +126 | 円 | step/scenes.out:17 | +126 | 円 | 一致 |
| 157 | +264 | 円 | base_scenes.out:5 | +264 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 157 | +154 | 円 | base_scenes.out:5 | +154 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 157 | +357 | 円 | base_scenes.out:5 | +357 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 157 | −168 | 円 | step/scenes.out:6 | -168 | 円 | 一致 |
| 157 | −235 | 円 | step/scenes.out:6 | -235 | 円 | 一致 |
| 157 | −100 | 円 | step/scenes.out:6 | -100 | 円 | 一致 |
| 157 | −144 | 円 | step/scenes.out:18 | -144 | 円 | 一致 |
| 157 | −189 | 円 | step/scenes.out:18 | -189 | 円 | 一致 |
| 157 | −102 | 円 | step/scenes.out:18 | -102 | 円 | 一致 |
| 157 | −216 | 円 | base_scenes.out:6 | -216 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 157 | −307 | 円 | base_scenes.out:6 | -307 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 157 | −126 | 円 | base_scenes.out:6 | -126 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 158 | +236 | 円 | step/scenes.out:8 | +236 | 円 | 一致 |
| 158 | +93 | 円 | step/scenes.out:8 | +93 | 円 | 一致 |
| 158 | +392 | 円 | step/scenes.out:8 | +392 | 円 | 一致 |
| 158 | +78 | 円 | step/scenes.out:20 | +78 | 円 | 一致 |
| 158 | −27 | 円 | step/scenes.out:20 | -27 | 円 | 一致 |
| 158 | +189 | 円 | step/scenes.out:20 | +189 | 円 | 一致 |
| 158 | +411 | 円 | base_scenes.out:8 | +411 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 158 | +226 | 円 | base_scenes.out:8 | +226 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 158 | +634 | 円 | base_scenes.out:8 | +634 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 158 | −242 | 円 | step/scenes.out:9 | -242 | 円 | 一致 |
| 158 | −371 | 円 | step/scenes.out:9 | -371 | 円 | 一致 |
| 158 | −120 | 円 | step/scenes.out:9 | -120 | 円 | 一致 |
| 158 | −211 | 円 | step/scenes.out:21 | -211 | 円 | 一致 |
| 158 | −294 | 円 | step/scenes.out:21 | -294 | 円 | 一致 |
| 158 | −131 | 円 | step/scenes.out:21 | -131 | 円 | 一致 |
| 158 | −282 | 円 | base_scenes.out:9 | -282 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 158 | −462 | 円 | base_scenes.out:9 | -462 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 158 | −111 | 円 | base_scenes.out:9 | -111 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 159 | +474 | 円 | step/scenes.out:11 | +474 | 円 | 一致 |
| 159 | +239 | 円 | step/scenes.out:11 | +239 | 円 | 一致 |
| 159 | +723 | 円 | step/scenes.out:11 | +723 | 円 | 一致 |
| 159 | +241 | 円 | step/scenes.out:23 | +241 | 円 | 一致 |
| 159 | +88 | 円 | step/scenes.out:23 | +88 | 円 | 一致 |
| 159 | +391 | 円 | step/scenes.out:23 | +391 | 円 | 一致 |
| 159 | +656 | 円 | base_scenes.out:11 | +656 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 159 | +336 | 円 | base_scenes.out:11 | +336 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 159 | +1,007 | 円 | base_scenes.out:11 | +1007 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 159 | −282 | 円 | step/scenes.out:12 | -282 | 円 | 一致 |
| 159 | −429 | 円 | step/scenes.out:12 | -429 | 円 | 一致 |
| 159 | −131 | 円 | step/scenes.out:12 | -131 | 円 | 一致 |
| 159 | −289 | 円 | step/scenes.out:24 | -289 | 円 | 一致 |
| 159 | −390 | 円 | step/scenes.out:24 | -390 | 円 | 一致 |
| 159 | −188 | 円 | step/scenes.out:24 | -188 | 円 | 一致 |
| 159 | −343 | 円 | base_scenes.out:12 | -343 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 159 | −529 | 円 | base_scenes.out:12 | -529 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 159 | −135 | 円 | base_scenes.out:12 | -135 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 165 | −86 | 円 | step/scene_diff.out:4 | -86 | 円 | 一致 |
| 165 | −126 | 円 | step/scene_diff.out:4 | -126 | 円 | 一致 |
| 165 | −42 | 円 | step/scene_diff.out:4 | -42 | 円 | 一致 |
| 165 | +48 | 円 | step/scene_diff.out:5 | +48 | 円 | 一致 |
| 165 | +15 | 円 | step/scene_diff.out:5 | +15 | 円 | 一致 |
| 165 | +83 | 円 | step/scene_diff.out:5 | +83 | 円 | 一致 |
| 165 | −182 | 円 | step/scene_diff.out:13 | -182 | 円 | 一致 |
| 165 | −245 | 円 | step/scene_diff.out:13 | -245 | 円 | 一致 |
| 165 | −116 | 円 | step/scene_diff.out:13 | -116 | 円 | 一致 |
| 165 | +72 | 円 | step/scene_diff.out:14 | +72 | 円 | 一致 |
| 165 | +19 | 円 | step/scene_diff.out:14 | +19 | 円 | 一致 |
| 165 | +127 | 円 | step/scene_diff.out:14 | +127 | 円 | 一致 |
| 166 | −175 | 円 | step/scene_diff.out:6 | -175 | 円 | 一致 |
| 166 | −260 | 円 | step/scene_diff.out:6 | -260 | 円 | 一致 |
| 166 | −111 | 円 | step/scene_diff.out:6 | -111 | 円 | 一致 |
| 166 | +40 | 円 | step/scene_diff.out:7 | +40 | 円 | 一致 |
| 166 | −18 | 円 | step/scene_diff.out:7 | -18 | 円 | 一致 |
| 166 | +99 | 円 | step/scene_diff.out:7 | +99 | 円 | 一致 |
| 166 | −333 | 円 | step/scene_diff.out:15 | -333 | 円 | 一致 |
| 166 | −467 | 円 | step/scene_diff.out:15 | -467 | 円 | 一致 |
| 166 | −234 | 円 | step/scene_diff.out:15 | -234 | 円 | 一致 |
| 166 | +71 | 円 | step/scene_diff.out:16 | +71 | 円 | 一致 |
| 166 | −29 | 円 | step/scene_diff.out:16 | -29 | 円 | 一致 |
| 166 | +171 | 円 | step/scene_diff.out:16 | +171 | 円 | 一致 |
| 167 | −182 | 円 | step/scene_diff.out:8 | -182 | 円 | 一致 |
| 167 | −317 | 円 | step/scene_diff.out:8 | -317 | 円 | 一致 |
| 167 | −58 | 円 | step/scene_diff.out:8 | -58 | 円 | 一致 |
| 167 | +61 | 円 | step/scene_diff.out:9 | +61 | 円 | 一致 |
| 167 | −17 | 円 | step/scene_diff.out:9 | -17 | 円 | 一致 |
| 167 | +144 | 円 | step/scene_diff.out:9 | +144 | 円 | 一致 |
| 167 | −415 | 円 | step/scene_diff.out:17 | -415 | 円 | 一致 |
| 167 | −634 | 円 | step/scene_diff.out:17 | -634 | 円 | 一致 |
| 167 | −221 | 円 | step/scene_diff.out:17 | -221 | 円 | 一致 |
| 167 | +55 | 円 | step/scene_diff.out:18 | +55 | 円 | 一致 |
| 167 | −69 | 円 | step/scene_diff.out:18 | -69 | 円 | 一致 |
| 167 | +164 | 円 | step/scene_diff.out:18 | +164 | 円 | 一致 |
| 169 | +48 | 円 | step/scene_diff.out:5 | +48 | 円 | 一致 |
| 169 | +15 | 円 | step/scene_diff.out:5 | +15 | 円 | 一致 |
| 169 | +83 | 円 | step/scene_diff.out:5 | +83 | 円 | 一致 |
| 169 | +72 | 円 | step/scene_diff.out:14 | +72 | 円 | 一致 |
| 169 | +19 | 円 | step/scene_diff.out:14 | +19 | 円 | 一致 |
| 169 | +127 | 円 | step/scene_diff.out:14 | +127 | 円 | 一致 |
| 190 | +28.7 | 円 | step/compare.md:7 | +28.7 | 円 | 一致 |
| 190 | −199.3 | 円 | step/compare.md:7 | -199.3 | 円 | 一致 |
| 190 | −223.6 | 円 | step/compare.md:7 | -223.6 | 円 | 一致 |
| 190 | −2,255,199 | 円 | step/compare.md:7 | -2,255,199 | 円 | 一致 |
| 190 | +362,265 | 円 | step/compare.md:7 | +362,265 | 円 | 一致 |
| 191 | +19.3 | 円 | step/compare.md:8 | +19.3 | 円 | 一致 |
| 191 | −133.6 | 円 | step/compare.md:8 | -133.6 | 円 | 一致 |
| 191 | −155.3 | 円 | step/compare.md:8 | -155.3 | 円 | 一致 |
| 191 | −611,835 | 円 | step/compare.md:8 | -611,835 | 円 | 一致 |
| 191 | +189,582 | 円 | step/compare.md:8 | +189,582 | 円 | 一致 |
| 192 | +40.5 | 円 | step/compare.md:6 | +40.5 | 円 | 一致 |
| 192 | −281.0 | 円 | step/compare.md:6 | -281.0 | 円 | 一致 |
| 192 | −273.4 | 円 | step/compare.md:6 | -273.4 | 円 | 一致 |
| 192 | −3,866,293 | 円 | step/compare.md:6 | -3,866,293 | 円 | 一致 |
| 192 | +532,210 | 円 | step/compare.md:6 | +532,210 | 円 | 一致 |
| 193 | +22.4 | 円 | step/compare.md:15 | +22.4 | 円 | 一致 |
| 193 | −168.8 | 円 | step/compare.md:15 | -168.8 | 円 | 一致 |
| 193 | −342.3 | 円 | step/compare.md:15 | -342.3 | 円 | 一致 |
| 193 | −2,195,357 | 円 | step/compare.md:15 | -2,195,357 | 円 | 一致 |
| 193 | −327,241 | 円 | step/compare.md:15 | -327,241 | 円 | 一致 |
| 194 | +14.7 | 円 | step/compare.md:16 | +14.7 | 円 | 一致 |
| 194 | −112.7 | 円 | step/compare.md:16 | -112.7 | 円 | 一致 |
| 194 | −231.1 | 円 | step/compare.md:16 | -231.1 | 円 | 一致 |
| 194 | −552,713 | 円 | step/compare.md:16 | -552,713 | 円 | 一致 |
| 194 | −303,327 | 円 | step/compare.md:16 | -303,327 | 円 | 一致 |
| 195 | +32.2 | 円 | step/compare.md:14 | +32.2 | 円 | 一致 |
| 195 | −238.4 | 円 | step/compare.md:14 | -238.4 | 円 | 一致 |
| 195 | −431.6 | 円 | step/compare.md:14 | -431.6 | 円 | 一致 |
| 195 | −3,834,951 | 円 | step/compare.md:14 | -3,834,951 | 円 | 一致 |
| 195 | −400,821 | 円 | step/compare.md:14 | -400,821 | 円 | 一致 |
| 201 | +314 | 円 | step/fam_tables.md:31 | +314 | 円 | 一致 |
| 201 | +270 | 円 | step/fam_tables.md:31 | +270 | 円 | 一致 |
| 201 | +352 | 円 | step/fam_tables.md:31 | +352 | 円 | 一致 |
| 201 | +151 | 円 | step/fam_tables.md:31 | +151 | 円 | 一致 |
| 201 | +131 | 円 | step/fam_tables.md:31 | +131 | 円 | 一致 |
| 201 | +169 | 円 | step/fam_tables.md:31 | +169 | 円 | 一致 |
| 202 | −67 | 円 | step/fam_tables.md:32 | -67 | 円 | 一致 |
| 202 | −168 | 円 | step/fam_tables.md:32 | -168 | 円 | 一致 |
| 202 | +32 | 円 | step/fam_tables.md:32 | +32 | 円 | 一致 |
| 202 | −374 | 円 | step/fam_tables.md:32 | -374 | 円 | 一致 |
| 202 | −436 | 円 | step/fam_tables.md:32 | -436 | 円 | 一致 |
| 202 | −309 | 円 | step/fam_tables.md:32 | -309 | 円 | 一致 |
| 203 | +327 | 円 | step/fam_tables.md:33 | +327 | 円 | 一致 |
| 203 | +292 | 円 | step/fam_tables.md:33 | +292 | 円 | 一致 |
| 203 | +359 | 円 | step/fam_tables.md:33 | +359 | 円 | 一致 |
| 203 | +184 | 円 | step/fam_tables.md:33 | +184 | 円 | 一致 |
| 203 | +167 | 円 | step/fam_tables.md:33 | +167 | 円 | 一致 |
| 203 | +201 | 円 | step/fam_tables.md:33 | +201 | 円 | 一致 |
| 204 | −198 | 円 | step/fam_tables.md:34 | -198 | 円 | 一致 |
| 204 | −270 | 円 | step/fam_tables.md:34 | -270 | 円 | 一致 |
| 204 | −127 | 円 | step/fam_tables.md:34 | -127 | 円 | 一致 |
| 204 | −391 | 円 | step/fam_tables.md:34 | -391 | 円 | 一致 |
| 204 | −435 | 円 | step/fam_tables.md:34 | -435 | 円 | 一致 |
| 204 | −346 | 円 | step/fam_tables.md:34 | -346 | 円 | 一致 |
| 205 | +329 | 円 | step/fam_tables.md:35 | +329 | 円 | 一致 |
| 205 | +274 | 円 | step/fam_tables.md:35 | +274 | 円 | 一致 |
| 205 | +378 | 円 | step/fam_tables.md:35 | +378 | 円 | 一致 |
| 205 | +117 | 円 | step/fam_tables.md:35 | +117 | 円 | 一致 |
| 205 | +92 | 円 | step/fam_tables.md:35 | +92 | 円 | 一致 |
| 205 | +141 | 円 | step/fam_tables.md:35 | +141 | 円 | 一致 |
| 206 | +33 | 円 | step/fam_tables.md:36 | +33 | 円 | 一致 |
| 206 | −100 | 円 | step/fam_tables.md:36 | -100 | 円 | 一致 |
| 206 | +167 | 円 | step/fam_tables.md:36 | +167 | 円 | 一致 |
| 206 | −390 | 円 | step/fam_tables.md:36 | -390 | 円 | 一致 |
| 206 | −474 | 円 | step/fam_tables.md:36 | -474 | 円 | 一致 |
| 206 | −302 | 円 | step/fam_tables.md:36 | -302 | 円 | 一致 |
| 208 | +25.6 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.groups.出の理由【結果で決まる群】.close.per_trade | +25.6 / +1.2782 bp(× 20 = +25.56 円) | 円 / bp | 一致 |
| 208 | +24.4 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.groups.出の理由【結果で決まる群】.close.lo | +24.4 / +1.2178 bp(× 20 = +24.36 円) | 円 / bp | 一致 |
| 208 | +26.8 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.groups.出の理由【結果で決まる群】.close.hi | +26.8 / +1.3394 bp(× 20 = +26.79 円) | 円 / bp | 一致 |
| 208 | −183.5 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.groups.出の理由【結果で決まる群】.break.per_trade | -183.5 / -9.1729 bp(× 20 = -183.46 円) | 円 / bp | 一致 |
| 208 | −192.6 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.groups.出の理由【結果で決まる群】.break.lo | -192.6 / -9.6314 bp(× 20 = -192.63 円) | 円 / bp | 一致 |
| 208 | −174.4 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.groups.出の理由【結果で決まる群】.break.hi | -174.4 / -8.7184 bp(× 20 = -174.37 円) | 円 / bp | 一致 |
| 208 | −253.5 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.groups.出の理由【結果で決まる群】.market.per_trade | -253.5 / -12.6741 bp(× 20 = -253.48 円) | 円 / bp | 一致 |
| 208 | −293.3 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.groups.出の理由【結果で決まる群】.market.lo | -293.3 / -14.6668 bp(× 20 = -293.34 円) | 円 / bp | 一致 |
| 208 | −222.9 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.groups.出の理由【結果で決まる群】.market.hi | -222.9 / -11.1446 bp(× 20 = -222.89 円) | 円 / bp | 一致 |
| 208 | +17.0 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.groups.出の理由【結果で決まる群】.close.per_trade | +17.0 / +0.8513 bp(× 20 = +17.03 円) | 円 / bp | 一致 |
| 208 | +16.2 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.groups.出の理由【結果で決まる群】.close.lo | +16.2 / +0.8105 bp(× 20 = +16.21 円) | 円 / bp | 一致 |
| 208 | +17.8 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.groups.出の理由【結果で決まる群】.close.hi | +17.8 / +0.8921 bp(× 20 = +17.84 円) | 円 / bp | 一致 |
| 208 | −122.8 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.groups.出の理由【結果で決まる群】.break.per_trade | -122.8 / -6.1380 bp(× 20 = -122.76 円) | 円 / bp | 一致 |
| 208 | −128.9 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.groups.出の理由【結果で決まる群】.break.lo | -128.9 / -6.4437 bp(× 20 = -128.87 円) | 円 / bp | 一致 |
| 208 | −116.8 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.groups.出の理由【結果で決まる群】.break.hi | -116.8 / -5.8395 bp(× 20 = -116.79 円) | 円 / bp | 一致 |
| 208 | −174.3 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.groups.出の理由【結果で決まる群】.market.per_trade | -174.3 / -8.7145 bp(× 20 = -174.29 円) | 円 / bp | 一致 |
| 208 | −202.4 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.groups.出の理由【結果で決まる群】.market.lo | -202.4 / -10.1195 bp(× 20 = -202.39 円) | 円 / bp | 一致 |
| 208 | −151.0 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.groups.出の理由【結果で決まる群】.market.hi | -151.0 / -7.5477 bp(× 20 = -150.95 円) | 円 / bp | 一致 |
| 208 | +36.4 | 円 | step/fam_tables.md:42 / base/diag_tables.json d3.groups.出の理由【結果で決まる群】.close.per_trade | +36.4 / +1.8210 bp(× 20 = +36.42 円) | 円 / bp | 一致 |
| 208 | −258.8 | 円 | step/fam_tables.md:42 / base/diag_tables.json d3.groups.出の理由【結果で決まる群】.break.per_trade | -258.8 / -12.9406 bp(× 20 = -258.81 円) | 円 / bp | 一致 |
| 208 | −315.2 | 円 | step/fam_tables.md:42 / base/diag_tables.json d3.groups.出の理由【結果で決まる群】.market.per_trade | -315.2 / -15.7597 bp(× 20 = -315.19 円) | 円 / bp | 一致 |
| 209 | +7.6 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.groups.保有時間の帯【結果で決まる群】.〜0 分.per_trade | +7.6 / +0.3803 bp(× 20 = +7.61 円) | 円 / bp | 一致 |
| 209 | +9.1 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.groups.保有時間の帯【結果で決まる群】.0 分超〜1 分.per_trade | +9.1 / +0.4536 bp(× 20 = +9.07 円) | 円 / bp | 一致 |
| 209 | +1.9 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.groups.保有時間の帯【結果で決まる群】.1 分超〜3 分.per_trade | +1.9 / +0.0953 bp(× 20 = +1.91 円) | 円 / bp | 一致 |
| 209 | −24.1 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.groups.保有時間の帯【結果で決まる群】.3 分超.per_trade | -24.1 / -1.2059 bp(× 20 = -24.12 円) | 円 / bp | 一致 |
| 209 | +8.5 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.groups.保有時間の帯【結果で決まる群】.0 分超〜1 分.lo | +8.5 / +0.4227 bp(× 20 = +8.45 円) | 円 / bp | 一致 |
| 209 | +7.9 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.groups.保有時間の帯【結果で決まる群】.0 分超〜1 分.per_trade または d3.groups.保有時間の帯【結果で決まる群】.〜0 分.lo | +7.9 / +0.3965 bp(× 20 = +7.93 円) | 円 / bp | 一致 |
| 209 | −1.2 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.groups.保有時間の帯【結果で決まる群】.1 分超〜3 分.per_trade | -1.2 / -0.0612 bp(× 20 = -1.22 円) | 円 / bp | 一致 |
| 209 | −1.8 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.groups.保有時間の帯【結果で決まる群】.1 分超〜3 分.lo | -1.8 / -0.0920 bp(× 20 = -1.84 円) | 円 / bp | 一致 |
| 209 | −0.6 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.groups.保有時間の帯【結果で決まる群】.1 分超〜3 分.hi | -0.6 / -0.0318 bp(× 20 = -0.64 円) | 円 / bp | 一致 |
| 209 | −22.1 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.groups.保有時間の帯【結果で決まる群】.3 分超.per_trade | -22.1 / -1.1044 bp(× 20 = -22.09 円) | 円 / bp | 一致 |
| 209 | +7.3 | 円 | step/fam_tables.md:42 / base/diag_tables.json d3.groups.保有時間の帯【結果で決まる群】.〜0 分.per_trade | +7.3 / +0.3667 bp(× 20 = +7.33 円) | 円 / bp | 一致 |
| 209 | +13.9 | 円 | step/fam_tables.md:42 / base/diag_tables.json d3.groups.保有時間の帯【結果で決まる群】.0 分超〜1 分.per_trade | +13.9 / +0.6973 bp(× 20 = +13.95 円) | 円 / bp | 一致 |
| 209 | +9.6 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.groups.保有時間の帯【結果で決まる群】.0 分超〜1 分.hi | +9.6 / +0.4824 bp(× 20 = +9.65 円) | 円 / bp | 一致 |
| 209 | −37.0 | 円 | step/fam_tables.md:42 / base/diag_tables.json d3.groups.保有時間の帯【結果で決まる群】.3 分超.per_trade | -37.0 / -1.8506 bp(× 20 = -37.01 円) | 円 / bp | 一致 |
| 210 | +480,639 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.top5_days_sum | +480,639 / +24031.9663 bp(× 20 = +480639.33 円) | 円 / bp | 一致 |
| 210 | −588,095 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.bottom5_days_sum | -588,095 / -29404.7314 bp(× 20 = -588094.63 円) | 円 / bp | 一致 |
| 210 | +307,988 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.top5_days_sum | +307,988 / +15399.3949 bp(× 20 = +307987.90 円) | 円 / bp | 一致 |
| 210 | −407,501 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.bottom5_days_sum | -407,501 / -20375.0307 bp(× 20 = -407500.61 円) | 円 / bp | 一致 |
| 210 | +35,024 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.total | +35,024 / +1751.2247 bp(× 20 = +35024.49 円) | 円 / bp | 一致 |
| 210 | −113,745 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.total | -113,745 / -5687.2636 bp(× 20 = -113745.27 円) | 円 / bp | 一致 |
| 215 | +18.6 | 円 | step/levels_reason.out:27 | +18.6 | 円 | 一致 |
| 215 | +67.0 | 円 | step/levels_reason.out:27 | +67.0 | 円 | 一致 |
| 215 | +46.7 | 円 | step/levels_reason.out:27 | +46.7 | 円 | 一致 |
| 215 | −43.6 | 円 | step/levels_reason.out:28 | -43.6 | 円 | 一致 |
| 215 | −352.0 | 円 | step/levels_reason.out:28 | -352.0 | 円 | 一致 |
| 215 | −341.7 | 円 | step/levels_reason.out:28 | -341.7 | 円 | 一致 |
| 216 | +17.2 | 円 | step/levels_reason.out:7 | +17.2 | 円 | 一致 |
| 216 | +59.9 | 円 | step/levels_reason.out:7 | +59.9 | 円 | 一致 |
| 216 | +32.2 | 円 | step/levels_reason.out:7 | +32.2 | 円 | 一致 |
| 216 | −42.7 | 円 | step/levels_reason.out:8 | -42.7 | 円 | 一致 |
| 216 | −266.6 | 円 | step/levels_reason.out:8 | -266.6 | 円 | 一致 |
| 216 | −245.0 | 円 | step/levels_reason.out:8 | -245.0 | 円 | 一致 |
| 217 | +15.3 | 円 | step/levels_reason.out:17 | +15.3 | 円 | 一致 |
| 217 | +46.9 | 円 | step/levels_reason.out:17 | +46.9 | 円 | 一致 |
| 217 | +20.0 | 円 | step/levels_reason.out:17 | +20.0 | 円 | 一致 |
| 217 | −53.1 | 円 | step/levels_reason.out:18 | -53.1 | 円 | 一致 |
| 217 | −208.8 | 円 | step/levels_reason.out:18 | -208.8 | 円 | 一致 |
| 217 | −162.7 | 円 | step/levels_reason.out:18 | -162.7 | 円 | 一致 |
| 218 | +14.3 | 円 | step/levels_reason.out:30 | +14.3 | 円 | 一致 |
| 218 | +51.4 | 円 | step/levels_reason.out:30 | +51.4 | 円 | 一致 |
| 218 | +36.2 | 円 | step/levels_reason.out:30 | +36.2 | 円 | 一致 |
| 218 | −37.8 | 円 | step/levels_reason.out:31 | -37.8 | 円 | 一致 |
| 218 | −285.1 | 円 | step/levels_reason.out:31 | -285.1 | 円 | 一致 |
| 218 | −277.2 | 円 | step/levels_reason.out:31 | -277.2 | 円 | 一致 |
| 219 | +11.9 | 円 | step/levels_reason.out:20 | +11.9 | 円 | 一致 |
| 219 | +30.4 | 円 | step/levels_reason.out:20 | +30.4 | 円 | 一致 |
| 219 | +14.8 | 円 | step/levels_reason.out:20 | +14.8 | 円 | 一致 |
| 219 | −44.4 | 円 | step/levels_reason.out:21 | -44.4 | 円 | 一致 |
| 219 | −166.2 | 円 | step/levels_reason.out:21 | -166.2 | 円 | 一致 |
| 219 | −130.6 | 円 | step/levels_reason.out:21 | -130.6 | 円 | 一致 |
| 220 | +17.2 | 円 | step/levels_reason.out:23 | +17.2 | 円 | 一致 |
| 220 | +61.7 | 円 | step/levels_reason.out:23 | +61.7 | 円 | 一致 |
| 220 | +24.7 | 円 | step/levels_reason.out:23 | +24.7 | 円 | 一致 |
| 220 | −17.2 | 円 | step/levels_reason.out:24 | -17.2 | 円 | 一致 |
| 220 | −134.6 | 円 | step/levels_reason.out:24 | -134.6 | 円 | 一致 |
| 220 | −113.4 | 円 | step/levels_reason.out:24 | -113.4 | 円 | 一致 |
| 221 | +14.3 | 円 | step/levels_reason.out:25 | +14.3 | 円 | 一致 |
| 221 | +48.3 | 円 | step/levels_reason.out:25 | +48.3 | 円 | 一致 |
| 221 | +19.1 | 円 | step/levels_reason.out:25 | +19.1 | 円 | 一致 |
| 221 | −19.4 | 円 | step/levels_reason.out:26 | -19.4 | 円 | 一致 |
| 221 | −118.8 | 円 | step/levels_reason.out:26 | -118.8 | 円 | 一致 |
| 221 | −103.8 | 円 | step/levels_reason.out:26 | -103.8 | 円 | 一致 |
| 222 | +14.0 | 円 | step/levels_reason.out:15 | +14.0 | 円 | 一致 |
| 222 | +63.2 | 円 | step/levels_reason.out:15 | +63.2 | 円 | 一致 |
| 222 | +14.3 | 円 | step/levels_reason.out:15 | +14.3 | 円 | 一致 |
| 222 | −28.9 | 円 | step/levels_reason.out:16 | -28.9 | 円 | 一致 |
| 222 | −88.3 | 円 | step/levels_reason.out:16 | -88.3 | 円 | 一致 |
| 222 | −48.3 | 円 | step/levels_reason.out:16 | -48.3 | 円 | 一致 |
| 224 | +46.7 | 円 | step/levels_reason.out:27 | +46.7 | 円 | 一致 |
| 224 | +32.2 | 円 | step/levels_reason.out:7 | +32.2 | 円 | 一致 |
| 224 | +20.0 | 円 | step/levels_reason.out:17 | +20.0 | 円 | 一致 |
| 224 | −341.7 | 円 | step/levels_reason.out:28 | -341.7 | 円 | 一致 |
| 224 | −245.0 | 円 | step/levels_reason.out:8 | -245.0 | 円 | 一致 |
| 224 | −162.7 | 円 | step/levels_reason.out:18 | -162.7 | 円 | 一致 |
| 224 | +61.7 | 円 | step/levels_reason.out:23 | +61.7 | 円 | 一致 |
| 224 | −134.6 | 円 | step/levels_reason.out:24 | -134.6 | 円 | 一致 |
| 224 | −12.5 万 | 円 | step/levels_reason.out:23-24 | 7,422 × +61.7 + 4,332 × (−134.6) = −125,150 | 円(計算) | 一致(計算値: 表示の値から計算して −12.5 万と合う) |
| 224 | +48.3 | 円 | step/levels_reason.out:25 | +48.3 | 円 | 一致 |
| 224 | −118.8 | 円 | step/levels_reason.out:26 | -118.8 | 円 | 一致 |
| 224 | −24.9 万 | 円 | step/levels_reason.out:25-26 | 4,960 × +48.3 + 4,116 × (−118.8) = −249,413 | 円(計算) | 一致(計算値: 表示の値から計算して −24.9 万と合う) |
| 225 | +36 | 円 | step/compare.md:22 | +36.4 | 円 | 一致 |
| 225 | +26 | 円 | step/compare.md:23 | +25.6 | 円 | 一致 |
| 225 | +17 | 円 | step/compare.md:24 | +17.0 | 円 | 一致 |
| 225 | −259 | 円 | step/compare.md:22 | -258.8 | 円 | 一致 |
| 225 | −184 | 円 | step/compare.md:23 | -183.5 | 円 | 一致 |
| 225 | −123 | 円 | step/compare.md:24 | -122.8 | 円 | 一致 |
| 225 | +329 | 円 | step/fam_tables.md:35 | +329 | 円 | 一致 |
| 225 | +314 | 円 | step/fam_tables.md:31 | +314 | 円 | 一致 |
| 225 | +327 | 円 | step/fam_tables.md:33 | +327 | 円 | 一致 |
| 225 | +117 | 円 | step/fam_tables.md:35 | +117 | 円 | 一致 |
| 225 | +151 | 円 | step/fam_tables.md:31 | +151 | 円 | 一致 |
| 225 | +184 | 円 | step/fam_tables.md:33 | +184 | 円 | 一致 |
| 225 | −390 | 円 | step/fam_tables.md:36 | -390 | 円 | 一致 |
| 225 | −374 | 円 | step/fam_tables.md:32 | -374 | 円 | 一致 |
| 225 | −391 | 円 | step/fam_tables.md:34 | -391 | 円 | 一致 |
| 225 | +33 | 円 | step/fam_tables.md:36 | +33 | 円 | 一致 |
| 225 | −100 | 円 | step/fam_tables.md:36 | -100 | 円 | 一致 |
| 225 | +167 | 円 | step/fam_tables.md:33 | +167 | 円 | 一致 |
| 225 | −67 | 円 | step/fam_tables.md:32 | -67 | 円 | 一致 |
| 225 | −168 | 円 | step/fam_tables.md:32 | -168 | 円 | 一致 |
| 225 | +32 | 円 | step/fam_tables.md:32 | +32 | 円 | 一致 |
| 225 | −198 | 円 | step/fam_tables.md:34 | -198 | 円 | 一致 |
| 225 | −270 | 円 | step/fam_tables.md:34 | -270 | 円 | 一致 |
| 225 | −127 | 円 | step/fam_tables.md:34 | -127 | 円 | 一致 |
| 247 | +6,765,737 | 円 | step/fam_tables.md:48 / step_2/diag_paths.json d4.groups.勝った.pnl_sum | +6,765,737 / +338286.8359 bp(× 20 = +6765736.72 円) | 円 / bp | 一致 |
| 247 | 5.98 | move_bp | step/fam_tables.md:48 / step_2/diag_paths.json d4.groups.勝った.mfe_median | 5.98 / +5.9824 move_bp | move_bp / move_bp | 一致 |
| 247 | −4.84 | move_bp | step/fam_tables.md:48 / step_2/diag_paths.json d4.groups.勝った.mae_median | -4.84 / -4.8427 move_bp | move_bp / move_bp | 一致 |
| 247 | +4,028,575 | 円 | step/fam_tables.md:52 / step_4/diag_paths.json d4.groups.勝った.pnl_sum | +4,028,575 / +201428.7275 bp(× 20 = +4028574.55 円) | 円 / bp | 一致 |
| 247 | 6.07 | move_bp | step/fam_tables.md:52 / step_4/diag_paths.json d4.groups.勝った.mfe_median | 6.07 / +6.0668 move_bp | move_bp / move_bp | 一致 |
| 247 | −4.82 | move_bp | step/fam_tables.md:52 / step_4/diag_paths.json d4.groups.勝った.mae_median | -4.82 / -4.8200 move_bp | move_bp / move_bp | 一致 |
| 247 | +10,177,344 | 円 | step/fam_tables.md:56 / base/diag_paths.json d4.groups.勝った.pnl_sum | +10,177,344 / +508867.1933 bp(× 20 = +10177343.87 円) | 円 / bp | 一致 |
| 247 | 6.02 | move_bp | step/fam_tables.md:56 / base/diag_paths.json d4.groups.勝った.mfe_median | 6.02 / +6.0217 move_bp | move_bp / move_bp | 一致 |
| 247 | −4.74 | move_bp | step/fam_tables.md:56 / base/diag_paths.json d4.groups.勝った.mae_median | -4.74 / -4.7440 move_bp | move_bp / move_bp | 一致 |
| 248 | −3,227,696 | 円 | step/fam_tables.md:49 / step_2/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.pnl_sum | -3,227,696 / -161384.8202 bp(× 20 = -3227696.40 円) | 円 / bp | 一致 |
| 248 | 2.03 | move_bp | step/fam_tables.md:49 / step_2/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mfe_median | 2.03 / +2.0271 move_bp | move_bp / move_bp | 一致 |
| 248 | −29.83 | move_bp | step/fam_tables.md:49 / step_2/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mae_median | -29.83 / -29.8339 move_bp | move_bp / move_bp | 一致 |
| 248 | −2,139,633 | 円 | step/fam_tables.md:53 / step_4/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.pnl_sum | -2,139,633 / -106981.6381 bp(× 20 = -2139632.76 円) | 円 / bp | 一致 |
| 248 | 2.02 | move_bp | step/fam_tables.md:53 / step_4/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mfe_median | 2.02 / +2.0202 move_bp | move_bp / move_bp | 一致 |
| 248 | −29.58 | move_bp | step/fam_tables.md:53 / step_4/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mae_median | -29.58 / -29.5849 move_bp | move_bp / move_bp | 一致 |
| 248 | −4,695,044 | 円 | step/fam_tables.md:57 / base/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.pnl_sum | -4,695,044 / -234752.1937 bp(× 20 = -4695043.87 円) | 円 / bp | 一致 |
| 248 | 2.05 | move_bp | step/fam_tables.md:57 / base/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mfe_median | 2.05 / +2.0537 move_bp | move_bp / move_bp | 一致 |
| 248 | −30.50 | move_bp | step/fam_tables.md:57 / base/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mae_median | -30.50 / -30.4965 move_bp | move_bp / move_bp | 一致 |
| 249 | −4,186,111 | 円 | step/fam_tables.md:50 / step_2/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.pnl_sum | -4,186,111 / -209305.5441 bp(× 20 = -4186110.88 円) | 円 / bp | 一致 |
| 249 | −2.78 | move_bp | step/fam_tables.md:50 / step_2/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mfe_median | -2.78 / -2.7790 move_bp | move_bp / move_bp | 一致 |
| 249 | −31.94 | move_bp | step/fam_tables.md:50 / step_2/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mae_median | -31.94 / -31.9402 move_bp | move_bp / move_bp | 一致 |
| 249 | −2,754,523 | 円 | step/fam_tables.md:54 / step_4/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.pnl_sum | -2,754,523 / -137726.1536 bp(× 20 = -2754523.07 円) | 円 / bp | 一致 |
| 249 | −2.71 | move_bp | step/fam_tables.md:54 / step_4/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mfe_median | -2.71 / -2.7132 move_bp | move_bp / move_bp | 一致 |
| 249 | −31.82 | move_bp | step/fam_tables.md:54 / step_4/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mae_median | -31.82 / -31.8213 move_bp | move_bp / move_bp | 一致 |
| 249 | −6,006,006 | 円 | step/fam_tables.md:58 / base/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.pnl_sum | -6,006,006 / -300300.2903 bp(× 20 = -6006005.81 円) | 円 / bp | 一致 |
| 249 | −2.77 | move_bp | step/fam_tables.md:58 / base/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mfe_median | -2.77 / -2.7731 move_bp | move_bp / move_bp | 一致 |
| 249 | −32.38 | move_bp | step/fam_tables.md:58 / base/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mae_median | -32.38 / -32.3832 move_bp | move_bp / move_bp | 一致 |
| 251 | −0.33 | move_bp | step/fam_tables.md:63 / step_2/diag_paths.json d4.after_exit.5.per_trade | -0.33 / -0.3258 move_bp | move_bp / move_bp | 一致 |
| 251 | −0.64 | move_bp | step/fam_tables.md:63 / step_2/diag_paths.json d4.after_exit.15.per_trade | -0.64 / -0.6394 move_bp | move_bp / move_bp | 一致 |
| 251 | −0.43 | move_bp | step/fam_tables.md:63 / step_2/diag_paths.json d4.after_exit.60.per_trade | -0.43 / -0.4268 move_bp | move_bp / move_bp | 一致 |
| 251 | −0.31 | move_bp | step/fam_tables.md:64 / step_4/diag_paths.json d4.after_exit.5.per_trade | -0.31 / -0.3137 move_bp | move_bp / move_bp | 一致 |
| 251 | −0.63 | move_bp | step/fam_tables.md:64 / step_4/diag_paths.json d4.after_exit.15.per_trade | -0.63 / -0.6271 move_bp | move_bp / move_bp | 一致 |
| 251 | −0.39 | move_bp | step/fam_tables.md:64 / step_4/diag_paths.json d4.after_exit.60.per_trade | -0.39 / -0.3925 move_bp | move_bp / move_bp | 一致 |
| 251 | −0.34 | move_bp | step/fam_tables.md:65 / base/diag_paths.json d4.after_exit.5.per_trade | -0.34 / -0.3353 move_bp | move_bp / move_bp | 一致 |
| 251 | −0.66 | move_bp | step/fam_tables.md:65 / base/diag_paths.json d4.after_exit.15.per_trade | -0.66 / -0.6565 move_bp | move_bp / move_bp | 一致 |
| 251 | −0.42 | move_bp | step/fam_tables.md:65 / base/diag_paths.json d4.after_exit.60.per_trade | -0.42 / -0.4195 move_bp | move_bp / move_bp | 一致 |
| 252 | +1,018 万 | 円 | step/fam_tables.md:56 / base/diag_paths.json d4.groups.勝った.pnl_sum | +10,177,344 / +508867.1933 bp(× 20 = +10177343.87 円) | 円 / bp | 一致 |
| 252 | +677 万 | 円 | step/fam_tables.md:48 / step_2/diag_paths.json d4.groups.勝った.pnl_sum | +6,765,737 / +338286.8359 bp(× 20 = +6765736.72 円) | 円 / bp | 一致 |
| 252 | +403 万 | 円 | step/fam_tables.md:52 / step_4/diag_paths.json d4.groups.勝った.pnl_sum | +4,028,575 / +201428.7275 bp(× 20 = +4028574.55 円) | 円 / bp | 一致 |
| 252 | −1,070 万 | 円 | step/fam_tables.md:57-58 | −4,695,044 + (−6,006,006) = −10,701,050 | 円(計算) | 一致(計算値) |
| 252 | −741 万 | 円 | step/fam_tables.md:49-50 | −3,227,696 + (−4,186,111) = −7,413,807 | 円(計算) | 一致(計算値) |
| 252 | −489 万 | 円 | step/fam_tables.md:53-54 | −2,139,633 + (−2,754,523) = −4,894,156 | 円(計算) | 一致(計算値) |
| 274 | −0.25 | move_bp | step/fam_tables.md:71 / step_2/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.per_trade | -0.25 / -0.2550 move_bp | move_bp / move_bp | 一致 |
| 274 | −0.31 | move_bp | step/fam_tables.md:71 / step_2/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.lo | -0.31 / -0.3114 move_bp | move_bp / move_bp | 一致 |
| 274 | −0.20 | move_bp | step/fam_tables.md:71 / step_2/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.hi | -0.20 / -0.2006 move_bp | move_bp / move_bp | 一致 |
| 274 | −0.50 | move_bp | step/fam_tables.md:71 / step_2/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.per_trade | -0.50 / -0.5028 move_bp | move_bp / move_bp | 一致 |
| 274 | −0.62 | move_bp | step/fam_tables.md:71 / step_2/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.lo | -0.62 / -0.6201 move_bp | move_bp / move_bp | 一致 |
| 274 | −0.38 | move_bp | step/fam_tables.md:71 / step_2/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.hi | -0.38 / -0.3780 move_bp | move_bp / move_bp | 一致 |
| 274 | −0.73 | move_bp | step/fam_tables.md:71 / step_2/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.per_trade | -0.73 / -0.7258 move_bp | move_bp / move_bp | 一致 |
| 274 | −0.96 | move_bp | step/fam_tables.md:71 / step_2/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.lo | -0.96 / -0.9609 move_bp | move_bp / move_bp | 一致 |
| 274 | −0.51 | move_bp | step/fam_tables.md:71 / step_2/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.hi | -0.51 / -0.5065 move_bp | move_bp / move_bp | 一致 |
| 274 | −0.58 | move_bp | step/fam_tables.md:71 / step_2/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.per_trade | -0.58 / -0.5811 move_bp | move_bp / move_bp | 一致 |
| 274 | −1.09 | move_bp | step/fam_tables.md:71 / step_2/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.lo | -1.09 / -1.0885 move_bp | move_bp / move_bp | 一致 |
| 274 | −0.14 | move_bp | step/fam_tables.md:71 / step_2/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.hi | -0.14 / -0.1386 move_bp | move_bp / move_bp | 一致 |
| 274 | +0.49 | move_bp | step/fam_tables.md:71 / step_2/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.control_24h.per_trade | +0.49 / +0.4895 move_bp | move_bp / move_bp | 一致 |
| 274 | −0.02 | move_bp | step/fam_tables.md:71 / step_2/diag_paths.json d5.建てた合図(起点 = 合図の時刻).1.control_24h.lo または d5.建てた合図(起点 = 建ての時刻).1.control_24h.lo または d5.建てた合図(起点 = 建ての時刻).60.control_24h.lo | -0.02 / -0.0187 move_bp | move_bp / move_bp | 一致 |
| 274 | +0.98 | move_bp | step/fam_tables.md:71 / step_2/diag_paths.json d5.建てた合図(起点 = 合図の時刻).60.control_24h.hi または d5.建てた合図(起点 = 建ての時刻).60.control_24h.hi | +0.98 / +0.9820 move_bp | move_bp / move_bp | 一致 |
| 275 | −0.25 | move_bp | step/fam_tables.md:72 / step_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.per_trade | -0.25 / -0.2536 move_bp | move_bp / move_bp | 一致 |
| 275 | −0.31 | move_bp | step/fam_tables.md:72 / step_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.lo | -0.31 / -0.3106 move_bp | move_bp / move_bp | 一致 |
| 275 | −0.20 | move_bp | step/fam_tables.md:72 / step_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.hi | -0.20 / -0.2008 move_bp | move_bp / move_bp | 一致 |
| 275 | −0.50 | move_bp | step/fam_tables.md:72 / step_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.per_trade | -0.50 / -0.5031 move_bp | move_bp / move_bp | 一致 |
| 275 | −0.62 | move_bp | step/fam_tables.md:72 / step_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.lo | -0.62 / -0.6218 move_bp | move_bp / move_bp | 一致 |
| 275 | −0.38 | move_bp | step/fam_tables.md:72 / step_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.hi | -0.38 / -0.3800 move_bp | move_bp / move_bp | 一致 |
| 275 | −0.73 | move_bp | step/fam_tables.md:72 / step_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.per_trade | -0.73 / -0.7337 move_bp | move_bp / move_bp | 一致 |
| 275 | −0.97 | move_bp | step/fam_tables.md:72 / step_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.lo | -0.97 / -0.9724 move_bp | move_bp / move_bp | 一致 |
| 275 | −0.51 | move_bp | step/fam_tables.md:72 / step_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.hi | -0.51 / -0.5124 move_bp | move_bp / move_bp | 一致 |
| 275 | −0.54 | move_bp | step/fam_tables.md:72 / step_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.per_trade | -0.54 / -0.5367 move_bp | move_bp / move_bp | 一致 |
| 275 | −1.07 | move_bp | step/fam_tables.md:72 / step_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.lo | -1.07 / -1.0651 move_bp | move_bp / move_bp | 一致 |
| 275 | −0.10 | move_bp | step/fam_tables.md:72 / step_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.control_24h.lo または d5.建てた合図(起点 = 建ての時刻).60.signal.hi | -0.10 / -0.1045 move_bp | move_bp / move_bp | 一致 |
| 275 | +0.50 | move_bp | step/fam_tables.md:72 / step_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.control_24h.per_trade | +0.50 / +0.4964 move_bp | move_bp / move_bp | 一致 |
| 275 | −0.01 | move_bp | step/fam_tables.md:72 / step_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.control_24h.lo | -0.01 / -0.0099 move_bp | move_bp / move_bp | 一致 |
| 275 | +1.01 | move_bp | step/fam_tables.md:72 / step_4/diag_paths.json d5.建てた合図(起点 = 合図の時刻).60.control_24h.hi または d5.建てた合図(起点 = 建ての時刻).60.control_24h.hi | +1.01 / +1.0112 move_bp | move_bp / move_bp | 一致 |
| 276 | −0.25 | move_bp | step/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.per_trade | -0.25 / -0.2537 move_bp | move_bp / move_bp | 一致 |
| 276 | −0.31 | move_bp | step/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.lo | -0.31 / -0.3118 move_bp | move_bp / move_bp | 一致 |
| 276 | −0.20 | move_bp | step/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.hi | -0.20 / -0.1989 move_bp | move_bp / move_bp | 一致 |
| 276 | −0.51 | move_bp | step/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.per_trade | -0.51 / -0.5080 move_bp | move_bp / move_bp | 一致 |
| 276 | −0.63 | move_bp | step/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.lo | -0.63 / -0.6269 move_bp | move_bp / move_bp | 一致 |
| 276 | −0.38 | move_bp | step/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.hi | -0.38 / -0.3795 move_bp | move_bp / move_bp | 一致 |
| 276 | −0.74 | move_bp | step/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.per_trade | -0.74 / -0.7434 move_bp | move_bp / move_bp | 一致 |
| 276 | −0.98 | move_bp | step/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.lo | -0.98 / -0.9791 move_bp | move_bp / move_bp | 一致 |
| 276 | −0.52 | move_bp | step/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.hi | -0.52 / -0.5232 move_bp | move_bp / move_bp | 一致 |
| 276 | −0.58 | move_bp | step/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.per_trade | -0.58 / -0.5757 move_bp | move_bp / move_bp | 一致 |
| 276 | −1.10 | move_bp | step/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.lo | -1.10 / -1.0953 move_bp | move_bp / move_bp | 一致 |
| 276 | −0.13 | move_bp | step/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.hi | -0.13 / -0.1296 move_bp | move_bp / move_bp | 一致 |
| 276 | +0.53 | move_bp | step/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.control_24h.per_trade | +0.53 / +0.5252 move_bp | move_bp / move_bp | 一致 |
| 276 | +0.03 | move_bp | step/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 合図の時刻).5.control_24h.per_trade または d5.建てた合図(起点 = 建ての時刻).1.control_24h.per_trade または d5.建てた合図(起点 = 建ての時刻).60.control_24h.lo | +0.03 / +0.0305 move_bp | move_bp / move_bp | 一致 |
| 276 | +1.03 | move_bp | step/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 合図の時刻).60.control_24h.hi または d5.建てた合図(起点 = 建ての時刻).60.control_24h.hi | +1.03 / +1.0279 move_bp | move_bp / move_bp | 一致 |
| 278 | +0.03 | move_bp | step/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 合図の時刻).5.control_24h.per_trade または d5.建てた合図(起点 = 建ての時刻).1.control_24h.per_trade または d5.建てた合図(起点 = 建ての時刻).60.control_24h.lo | +0.03 / +0.0305 move_bp | move_bp / move_bp | 一致 |
| 295 | +1.6 | 円 | step/fam_tables.md:77 / step_2/diag_tables.json d6.groups.〜1 分.per_trade | +1.6 / +0.0805 bp(× 20 = +1.61 円) | 円 / bp | 一致 |
| 295 | +0.9 | 円 | step/fam_tables.md:77 / step_2/diag_tables.json d6.groups.〜1 分.lo | +0.9 / +0.0435 bp(× 20 = +0.87 円) | 円 / bp | 一致 |
| 295 | +2.3 | 円 | step/fam_tables.md:77 / step_2/diag_tables.json d6.groups.〜1 分.hi | +2.3 / +0.1168 bp(× 20 = +2.34 円) | 円 / bp | 一致 |
| 295 | −0.3 | 円 | step/fam_tables.md:77 / step_2/diag_tables.json d6.groups.1 分超〜3 分.per_trade または d6.groups.3 分超〜11 分.hi | -0.3 / -0.0137 bp(× 20 = -0.27 円) | 円 / bp | 一致 |
| 295 | −1.4 | 円 | step/fam_tables.md:77 / step_2/diag_tables.json d6.groups.1 分超〜3 分.lo | -1.4 / -0.0705 bp(× 20 = -1.41 円) | 円 / bp | 一致 |
| 295 | +0.7 | 円 | step/fam_tables.md:77 / step_2/diag_tables.json d6.groups.1 分超〜3 分.hi | +0.7 / +0.0359 bp(× 20 = +0.72 円) | 円 / bp | 一致 |
| 295 | −1.2 | 円 | step/fam_tables.md:77 / step_2/diag_tables.json d6.groups.3 分超〜11 分.per_trade | -1.2 / -0.0616 bp(× 20 = -1.23 円) | 円 / bp | 一致 |
| 295 | −2.1 | 円 | step/fam_tables.md:77 / step_2/diag_tables.json d6.groups.3 分超〜11 分.lo | -2.1 / -0.1047 bp(× 20 = -2.09 円) | 円 / bp | 一致 |
| 295 | −0.3 | 円 | step/fam_tables.md:77 / step_2/diag_tables.json d6.groups.1 分超〜3 分.per_trade または d6.groups.3 分超〜11 分.hi | -0.3 / -0.0137 bp(× 20 = -0.27 円) | 円 / bp | 一致 |
| 295 | −0.8 | 円 | step/fam_tables.md:77 / step_2/diag_tables.json d6.groups.11 分超.per_trade | -0.8 / -0.0403 bp(× 20 = -0.81 円) | 円 / bp | 一致 |
| 295 | −2.0 | 円 | step/fam_tables.md:77 / step_2/diag_tables.json d6.groups.11 分超.lo | -2.0 / -0.1011 bp(× 20 = -2.02 円) | 円 / bp | 一致 |
| 295 | +0.3 | 円 | step/fam_tables.md:77 / step_2/diag_tables.json d6.groups.11 分超.hi | +0.3 / +0.0146 bp(× 20 = +0.29 円) | 円 / bp | 一致 |
| 296 | +1.1 | 円 | step/fam_tables.md:78 / step_4/diag_tables.json d6.groups.〜1 分.per_trade | +1.1 / +0.0562 bp(× 20 = +1.12 円) | 円 / bp | 一致 |
| 296 | +0.6 | 円 | step/fam_tables.md:78 / step_4/diag_tables.json d6.groups.〜1 分.lo | +0.6 / +0.0309 bp(× 20 = +0.62 円) | 円 / bp | 一致 |
| 296 | +1.6 | 円 | step/fam_tables.md:78 / step_4/diag_tables.json d6.groups.〜1 分.hi | +1.6 / +0.0815 bp(× 20 = +1.63 円) | 円 / bp | 一致 |
| 296 | −1.0 | 円 | step/fam_tables.md:78 / step_4/diag_tables.json d6.groups.1 分超〜3 分.per_trade | -1.0 / -0.0486 bp(× 20 = -0.97 円) | 円 / bp | 一致 |
| 296 | −1.7 | 円 | step/fam_tables.md:78 / step_4/diag_tables.json d6.groups.1 分超〜3 分.lo | -1.7 / -0.0875 bp(× 20 = -1.75 円) | 円 / bp | 一致 |
| 296 | −0.2 | 円 | step/fam_tables.md:78 / step_4/diag_tables.json d6.groups.1 分超〜3 分.hi | -0.2 / -0.0110 bp(× 20 = -0.22 円) | 円 / bp | 一致 |
| 296 | −1.4 | 円 | step/fam_tables.md:78 / step_4/diag_tables.json d6.groups.3 分超〜11 分.per_trade | -1.4 / -0.0710 bp(× 20 = -1.42 円) | 円 / bp | 一致 |
| 296 | −2.0 | 円 | step/fam_tables.md:78 / step_4/diag_tables.json d6.groups.11 分超.lo または d6.groups.3 分超〜11 分.lo | -2.0 / -0.0984 bp(× 20 = -1.97 円) | 円 / bp | 一致 |
| 296 | −0.8 | 円 | step/fam_tables.md:78 / step_4/diag_tables.json d6.groups.3 分超〜11 分.hi | -0.8 / -0.0407 bp(× 20 = -0.81 円) | 円 / bp | 一致 |
| 296 | −1.1 | 円 | step/fam_tables.md:78 / step_4/diag_tables.json d6.groups.11 分超.per_trade | -1.1 / -0.0561 bp(× 20 = -1.12 円) | 円 / bp | 一致 |
| 296 | −2.0 | 円 | step/fam_tables.md:78 / step_4/diag_tables.json d6.groups.11 分超.lo または d6.groups.3 分超〜11 分.lo | -2.0 / -0.0984 bp(× 20 = -1.97 円) | 円 / bp | 一致 |
| 296 | −0.3 | 円 | step/fam_tables.md:78 / step_4/diag_tables.json d6.groups.11 分超.hi | -0.3 / -0.0169 bp(× 20 = -0.34 円) | 円 / bp | 一致 |
| 297 | +2.4 | 円 | step/fam_tables.md:79 / base/diag_tables.json d6.groups.〜1 分.per_trade | +2.4 / +0.1180 bp(× 20 = +2.36 円) | 円 / bp | 一致 |
| 297 | +1.3 | 円 | step/fam_tables.md:79 / base/diag_tables.json d6.groups.〜1 分.lo | +1.3 / +0.0674 bp(× 20 = +1.35 円) | 円 / bp | 一致 |
| 297 | +3.3 | 円 | step/fam_tables.md:79 / base/diag_tables.json d6.groups.〜1 分.hi | +3.3 / +0.1673 bp(× 20 = +3.35 円) | 円 / bp | 一致 |
| 297 | −2.0 | 円 | step/fam_tables.md:79 / base/diag_tables.json d6.groups.3 分超〜11 分.per_trade | -2.0 / -0.1001 bp(× 20 = -2.00 円) | 円 / bp | 一致 |
| 297 | −3.2 | 円 | step/fam_tables.md:79 / base/diag_tables.json d6.groups.3 分超〜11 分.lo | -3.2 / -0.1618 bp(× 20 = -3.24 円) | 円 / bp | 一致 |
| 297 | −0.8 | 円 | step/fam_tables.md:79 / base/diag_tables.json d6.groups.3 分超〜11 分.hi | -0.8 / -0.0400 bp(× 20 = -0.80 円) | 円 / bp | 一致 |
| 319 | −32.8 | 円 | step/fam_tables.md:85 / step_2/diag_tables.json d7.all.mean | -32.8 / -1.6394 bp(× 20 = -32.79 円) | 円 / bp | 一致 |
| 319 | −60.0 | 円 | step/fam_tables.md:85 / step_2/diag_tables.json d7.all.lo | -60.0 / -2.9997 bp(× 20 = -59.99 円) | 円 / bp | 一致 |
| 319 | −3.7 | 円 | step/fam_tables.md:85 / step_2/diag_tables.json d7.all.hi | -3.7 / -0.1859 bp(× 20 = -3.72 円) | 円 / bp | 一致 |
| 319 | 41.5 | 円 | step/fam_tables.md:85 / step_2/diag_tables.json d7.all.mde | +41.5 / +2.0768 bp(× 20 = +41.54 円) | 円 / bp | 一致 |
| 319 | −83.4 | 円 | step/fam_tables.md:86 / step_4/diag_tables.json d7.all.mean | -83.4 / -4.1704 bp(× 20 = -83.41 円) | 円 / bp | 一致 |
| 319 | −130.0 | 円 | step/fam_tables.md:86 / step_4/diag_tables.json d7.all.lo | -130.0 / -6.4984 bp(× 20 = -129.97 円) | 円 / bp | 一致 |
| 319 | −34.1 | 円 | step/fam_tables.md:86 / step_4/diag_tables.json d7.all.hi | -34.1 / -1.7056 bp(× 20 = -34.11 円) | 円 / bp | 一致 |
| 319 | 69.4 | 円 | step/fam_tables.md:86 / step_4/diag_tables.json d7.all.mde | +69.4 / +3.4708 bp(× 20 = +69.42 円) | 円 / bp | 一致 |
| 320 | −116 | 円 | step/fam_tables.md:85 | -116 | 円 | 一致 |
| 320 | −163 | 円 | step/fam_tables.md:85 | -163 | 円 | 一致 |
| 320 | −72 | 円 | step/fam_tables.md:85 | -72 | 円 | 一致 |
| 320 | 66 | 円 | step/fam_tables.md:85 | +66 | 円 | 一致 |
| 320 | −233 | 円 | step/fam_tables.md:86 | -233 | 円 | 一致 |
| 320 | −314 | 円 | step/fam_tables.md:86 | -314 | 円 | 一致 |
| 320 | −160 | 円 | step/fam_tables.md:86 | -160 | 円 | 一致 |
| 320 | 112 | 円 | step/fam_tables.md:86 | +112 | 円 | 一致 |
| 321 | +50 | 円 | step/fam_tables.md:85 | +50 | 円 | 一致 |
| 321 | +16 | 円 | step/fam_tables.md:85 | +16 | 円 | 一致 |
| 321 | +84 | 円 | step/fam_tables.md:85 | +84 | 円 | 一致 |
| 321 | 47 | 円 | step/fam_tables.md:85 | +47 | 円 | 一致 |
| 321 | +66 | 円 | step/fam_tables.md:86 | +66 | 円 | 一致 |
| 321 | +12 | 円 | step/fam_tables.md:86 | +12 | 円 | 一致 |
| 321 | +116 | 円 | step/fam_tables.md:86 | +116 | 円 | 一致 |
| 321 | 72 | 円 | step/fam_tables.md:86 | +72 | 円 | 一致 |
| 327 | +130 | 円 | step/fam_tables.md:92 / step_2/diag_tables.json d7.years.2015.mean または d7.years.2021.hi | +130 / +6.5008 bp(× 20 = +130.02 円) | 円 / bp | 一致 |
| 327 | −45 | 円 | step/fam_tables.md:92 / step_2/diag_tables.json d7.years.2016.mean | -45 / -2.2558 bp(× 20 = -45.12 円) | 円 / bp | 一致 |
| 327 | −123 | 円 | step/fam_tables.md:92 / step_2/diag_tables.json d7.years.2017.mean | -123 / -6.1399 bp(× 20 = -122.80 円) | 円 / bp | 一致 |
| 327 | −199 | 円 | step/fam_tables.md:92 / step_2/diag_tables.json d7.years.2018.mean | -199 / -9.9303 bp(× 20 = -198.61 円) | 円 / bp | 一致 |
| 327 | −114 | 円 | step/fam_tables.md:92 / step_2/diag_tables.json d7.years.2019.mean | -114 / -5.7017 bp(× 20 = -114.03 円) | 円 / bp | 一致 |
| 327 | −62 | 円 | step/fam_tables.md:92 / step_2/diag_tables.json d7.years.2020.mean | -62 / -3.0953 bp(× 20 = -61.91 円) | 円 / bp | 一致 |
| 327 | +45 | 円 | step/fam_tables.md:92 / step_2/diag_tables.json d7.years.2021.mean | +45 / +2.2696 bp(× 20 = +45.39 円) | 円 / bp | 一致 |
| 327 | +86 | 円 | step/fam_tables.md:92 / step_2/diag_tables.json d7.years.2022.mean または d7.years.2022.mde または d7.years.2023.lo | +86 / +4.3033 bp(× 20 = +86.07 円) | 円 / bp | 一致 |
| 327 | +142 | 円 | step/fam_tables.md:92 / step_2/diag_tables.json d7.years.2023.mean | +142 / +7.0837 bp(× 20 = +141.67 円) | 円 / bp | 一致 |
| 328 | +242 | 円 | step/fam_tables.md:93 / step_4/diag_tables.json d7.years.2015.mean | +242 / +12.0865 bp(× 20 = +241.73 円) | 円 / bp | 一致 |
| 328 | −37 | 円 | step/fam_tables.md:93 / step_4/diag_tables.json d7.years.2016.mean | -37 / -1.8258 bp(× 20 = -36.52 円) | 円 / bp | 一致 |
| 328 | −302 | 円 | step/fam_tables.md:93 / step_4/diag_tables.json d7.years.2017.mean | -302 / -15.0901 bp(× 20 = -301.80 円) | 円 / bp | 一致 |
| 328 | −389 | 円 | step/fam_tables.md:93 / step_4/diag_tables.json d7.years.2018.mean | -389 / -19.4665 bp(× 20 = -389.33 円) | 円 / bp | 一致 |
| 328 | −237 | 円 | step/fam_tables.md:93 / step_4/diag_tables.json d7.years.2019.mean | -237 / -11.8604 bp(× 20 = -237.21 円) | 円 / bp | 一致 |
| 328 | −109 | 円 | step/fam_tables.md:93 / step_4/diag_tables.json d7.years.2020.mean | -109 / -5.4526 bp(× 20 = -109.05 円) | 円 / bp | 一致 |
| 328 | +92 | 円 | step/fam_tables.md:93 / step_4/diag_tables.json d7.years.2021.mean | +92 / +4.5834 bp(× 20 = +91.67 円) | 円 / bp | 一致 |
| 328 | +67 | 円 | step/fam_tables.md:93 / step_4/diag_tables.json d7.years.2022.mean | +67 / +3.3281 bp(× 20 = +66.56 円) | 円 / bp | 一致 |
| 328 | +233 | 円 | step/fam_tables.md:93 / step_4/diag_tables.json d7.years.2023.mean | +233 / +11.6438 bp(× 20 = +232.88 円) | 円 / bp | 一致 |
| 334 | −102,008 | 円 | step/fam_tables.md:99 / step_2/diag_tables.json d7.match.sum_both_a_minus_b | -102,008 / -5100.3799 bp(× 20 = -102007.60 円) | 円 / bp | 一致 |
| 334 | −11,178 | 円 | step/fam_tables.md:99 / step_2/diag_tables.json d7.match.sum_only_a | -11,178 / -558.8932 bp(× 20 = -11177.86 円) | 円 / bp | 一致 |
| 334 | −16,820 | 円 | step/fam_tables.md:99 / step_2/diag_tables.json d7.match.sum_only_b | -16,820 / -841.0245 bp(× 20 = -16820.49 円) | 円 / bp | 一致 |
| 335 | −250,923 | 円 | step/fam_tables.md:100 / step_4/diag_tables.json d7.match.sum_both_a_minus_b | -250,923 / -12546.1555 bp(× 20 = -250923.11 円) | 円 / bp | 一致 |
| 335 | −5,516 | 円 | step/fam_tables.md:100 / step_4/diag_tables.json d7.match.sum_only_a | -5,516 / -275.7950 bp(× 20 = -5515.90 円) | 円 / bp | 一致 |
| 335 | −11,304 | 円 | step/fam_tables.md:100 / step_4/diag_tables.json d7.match.sum_only_b | -11,304 / -565.2138 bp(× 20 = -11304.28 円) | 円 / bp | 一致 |
| 337 | −116 | 円 | step/fam_tables.md:85 | -116 | 円 | 一致 |
| 337 | −163 | 円 | step/fam_tables.md:85 | -163 | 円 | 一致 |
| 337 | −72 | 円 | step/fam_tables.md:85 | -72 | 円 | 一致 |
| 337 | −233 | 円 | step/fam_tables.md:86 | -233 | 円 | 一致 |
| 337 | −314 | 円 | step/fam_tables.md:86 | -314 | 円 | 一致 |
| 337 | −160 | 円 | step/fam_tables.md:86 | -160 | 円 | 一致 |
| 337 | +50 | 円 | step/fam_tables.md:85 | +50 | 円 | 一致 |
| 337 | +16 | 円 | step/fam_tables.md:85 | +16 | 円 | 一致 |
| 337 | +84 | 円 | step/fam_tables.md:85 | +84 | 円 | 一致 |
| 337 | +66 | 円 | step/fam_tables.md:85 | +66 | 円 | 一致 |
| 337 | +12 | 円 | step/fam_tables.md:86 | +12 | 円 | 一致 |
| 337 | +116 | 円 | step/fam_tables.md:86 | +116 | 円 | 一致 |
| 337 | −102,008 | 円 | step/fam_tables.md:99 / step_2/diag_tables.json d7.match.sum_both_a_minus_b | -102,008 / -5100.3799 bp(× 20 = -102007.60 円) | 円 / bp | 一致 |
| 337 | −250,923 | 円 | step/fam_tables.md:100 / step_4/diag_tables.json d7.match.sum_both_a_minus_b | -250,923 / -12546.1555 bp(× 20 = -250923.11 円) | 円 / bp | 一致 |
| 338 | −116 | 円 | step/fam_tables.md:85 | -116 | 円 | 一致 |
| 338 | −15 | 円 | step/fam_tables.md:31・35 | +314 − (+329) = −15 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 338 | +329 | 円 | step/fam_tables.md:35 | +329 | 円 | 一致 |
| 338 | +314 | 円 | step/fam_tables.md:31 | +314 | 円 | 一致 |
| 338 | −100 | 円 | step/fam_tables.md:32・36 | −67 − (+33) = −100 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 338 | +33 | 円 | step/fam_tables.md:36 | +33 | 円 | 一致 |
| 338 | −67 | 円 | step/fam_tables.md:32 | -67 | 円 | 一致 |
| 338 | +50 | 円 | step/fam_tables.md:85 | +50 | 円 | 一致 |
| 338 | +34 | 円 | step/fam_tables.md:31・35 | +151 − (+117) = +34 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 338 | +117 | 円 | step/fam_tables.md:35 | +117 | 円 | 一致 |
| 338 | +151 | 円 | step/fam_tables.md:31 | +151 | 円 | 一致 |
| 338 | +16 | 円 | step/fam_tables.md:32・36 | −374 − (−390) = +16 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 338 | −390 | 円 | step/fam_tables.md:36 | -390 | 円 | 一致 |
| 338 | −374 | 円 | step/fam_tables.md:32 | -374 | 円 | 一致 |
| 338 | −233 | 円 | step/fam_tables.md:86 | -233 | 円 | 一致 |
| 338 | −2 | 円 | step/fam_tables.md:33・35 | +327 − (+329) = −2 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 338 | −231 | 円 | step/fam_tables.md:34・36 | −198 − (+33) = −231 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 338 | +66 | 円 | step/fam_tables.md:85 | +66 | 円 | 一致 |
| 338 | +67 | 円 | step/fam_tables.md:33・35 | +184 − (+117) = +67 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 338 | −1 | 円 | step/fam_tables.md:34・36 | −391 − (−390) = −1 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 387 | −116 | 円 | step/fam_tables.md:85 | -116 | 円 | 一致 |
| 387 | −233 | 円 | step/fam_tables.md:86 | -233 | 円 | 一致 |
| 387 | +50 | 円 | step/fam_tables.md:85 | +50 | 円 | 一致 |
| 387 | +66 | 円 | step/fam_tables.md:85 | +66 | 円 | 一致 |
| 388 | +46.7 | 円 | step/levels_reason.out:27 | +46.7 | 円 | 一致 |
| 388 | +20.0 | 円 | step/levels_reason.out:17 | +20.0 | 円 | 一致 |
| 388 | −341.7 | 円 | step/levels_reason.out:28 | -341.7 | 円 | 一致 |
| 388 | −162.7 | 円 | step/levels_reason.out:18 | -162.7 | 円 | 一致 |
| 389 | −198 | 円 | step/fam_tables.md:34 | -198 | 円 | 一致 |
| 389 | −270 | 円 | step/fam_tables.md:34 | -270 | 円 | 一致 |
| 389 | −127 | 円 | step/fam_tables.md:34 | -127 | 円 | 一致 |
| 390 | +117 | 円 | step/fam_tables.md:35 | +117 | 円 | 一致 |
| 390 | +151 | 円 | step/fam_tables.md:31 | +151 | 円 | 一致 |
| 390 | +184 | 円 | step/fam_tables.md:33 | +184 | 円 | 一致 |
| 391 | +48 | 円 | step/scene_diff.out:5 | +48 | 円 | 一致 |
| 391 | +15 | 円 | step/scene_diff.out:5 | +15 | 円 | 一致 |
| 391 | +83 | 円 | step/scene_diff.out:5 | +83 | 円 | 一致 |
| 391 | +72 | 円 | step/scene_diff.out:14 | +72 | 円 | 一致 |
| 391 | +19 | 円 | step/scene_diff.out:14 | +19 | 円 | 一致 |
| 391 | +127 | 円 | step/scene_diff.out:14 | +127 | 円 | 一致 |
| 392 | −1.2 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.groups.保有時間の帯【結果で決まる群】.1 分超〜3 分.per_trade | -1.2 / -0.0612 bp(× 20 = -1.22 円) | 円 / bp | 一致 |
| 392 | −1.8 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.groups.保有時間の帯【結果で決まる群】.1 分超〜3 分.lo | -1.8 / -0.0920 bp(× 20 = -1.84 円) | 円 / bp | 一致 |
| 392 | −0.6 | 円 | step/fam_tables.md:41 / step_4/diag_tables.json d3.groups.保有時間の帯【結果で決まる群】.1 分超〜3 分.hi | -0.6 / -0.0318 bp(× 20 = -0.64 円) | 円 / bp | 一致 |
| 392 | +9.6 | 円 | step/fam_tables.md:40 / step_2/diag_tables.json d3.groups.保有時間の帯【結果で決まる群】.0 分超〜1 分.hi | +9.6 / +0.4824 bp(× 20 = +9.65 円) | 円 / bp | 一致 |
| 417 | +247 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.segments.first.mean | +247 / +12.3303 bp(× 20 = +246.61 円) | 円 / bp | 一致 |
| 417 | +147 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.segments.first.lo | +147 / +7.3620 bp(× 20 = +147.24 円) | 円 / bp | 一致 |
| 417 | +349 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.segments.first.hi | +349 / +17.4493 bp(× 20 = +348.99 円) | 円 / bp | 一致 |
| 417 | −223 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.segments.second.mean | -223 / -11.1306 bp(× 20 = -222.61 円) | 円 / bp | 一致 |
| 417 | −290 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.segments.second.lo | -290 / -14.4894 bp(× 20 = -289.79 円) | 円 / bp | 一致 |
| 417 | −159 | 円 | step/fam_tables.md:15 / step_2/diag_tables.json d1.segments.second.hi | -159 / -7.9505 bp(× 20 = -159.01 円) | 円 / bp | 一致 |
| 418 | +129 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.first.mean | +129 / +6.4528 bp(× 20 = +129.06 円) | 円 / bp | 一致 |
| 418 | +59 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.first.lo | +59 / +2.9603 bp(× 20 = +59.21 円) | 円 / bp | 一致 |
| 418 | +199 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.first.hi | +199 / +9.9662 bp(× 20 = +199.32 円) | 円 / bp | 一致 |
| 418 | −206 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.second.mean | -206 / -10.3173 bp(× 20 = -206.35 円) | 円 / bp | 一致 |
| 418 | −251 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.second.lo | -251 / -12.5349 bp(× 20 = -250.70 円) | 円 / bp | 一致 |
| 418 | −165 | 円 | step/fam_tables.md:16 / step_4/diag_tables.json d1.segments.second.hi | -165 / -8.2486 bp(× 20 = -164.97 円) | 円 / bp | 一致 |
| 419 | +362 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.first.mean | +362 / +18.1147 bp(× 20 = +362.29 円) | 円 / bp | 一致 |
| 419 | +231 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.first.lo | +231 / +11.5545 bp(× 20 = +231.09 円) | 円 / bp | 一致 |
| 419 | +497 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.first.hi | +497 / +24.8558 bp(× 20 = +497.12 円) | 円 / bp | 一致 |
| 419 | −273 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.second.mean | -273 / -13.6334 bp(× 20 = -272.67 円) | 円 / bp | 一致 |
| 419 | −360 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.second.lo | -360 / -17.9998 bp(× 20 = -360.00 円) | 円 / bp | 一致 |
| 419 | −184 | 円 | step/fam_tables.md:17 / base/diag_tables.json d1.segments.second.hi | -184 / -9.1933 bp(× 20 = -183.87 円) | 円 / bp | 一致 |
| 433 | −32.8 | 円 | step/fam_tables.md:85 / step_2/diag_tables.json d7.all.mean | -32.8 / -1.6394 bp(× 20 = -32.79 円) | 円 / bp | 一致 |
| 433 | −60.0 | 円 | step/fam_tables.md:85 / step_2/diag_tables.json d7.all.lo | -60.0 / -2.9997 bp(× 20 = -59.99 円) | 円 / bp | 一致 |
| 433 | −3.7 | 円 | step/fam_tables.md:85 / step_2/diag_tables.json d7.all.hi | -3.7 / -0.1859 bp(× 20 = -3.72 円) | 円 / bp | 一致 |
| 433 | 41.5 | 円 | step/fam_tables.md:85 / step_2/diag_tables.json d7.all.mde | +41.5 / +2.0768 bp(× 20 = +41.54 円) | 円 / bp | 一致 |
| 433 | −116 | 円 | step/fam_tables.md:85 | -116 | 円 | 一致 |
| 433 | −163 | 円 | step/fam_tables.md:85 | -163 | 円 | 一致 |
| 433 | −72 | 円 | step/fam_tables.md:85 | -72 | 円 | 一致 |
| 433 | +50 | 円 | step/fam_tables.md:85 | +50 | 円 | 一致 |
| 433 | +16 | 円 | step/fam_tables.md:85 | +16 | 円 | 一致 |
| 433 | +84 | 円 | step/fam_tables.md:85 | +84 | 円 | 一致 |
| 433 | −45 | 円 | step/fam_tables.md:92 / step_2/diag_tables.json d7.years.2016.mean | -45 / -2.2558 bp(× 20 = -45.12 円) | 円 / bp | 一致 |
| 433 | −199 | 円 | step/fam_tables.md:92 / step_2/diag_tables.json d7.years.2018.mean | -199 / -9.9303 bp(× 20 = -198.61 円) | 円 / bp | 一致 |
| 433 | −62 | 円 | step/fam_tables.md:92 / step_2/diag_tables.json d7.years.2020.mean | -62 / -3.0953 bp(× 20 = -61.91 円) | 円 / bp | 一致 |
| 433 | +86 | 円 | step/fam_tables.md:92 / step_2/diag_tables.json d7.years.2022.mean または d7.years.2022.mde または d7.years.2023.lo | +86 / +4.3033 bp(× 20 = +86.07 円) | 円 / bp | 一致 |
| 433 | +142 | 円 | step/fam_tables.md:92 / step_2/diag_tables.json d7.years.2023.mean | +142 / +7.0837 bp(× 20 = +141.67 円) | 円 / bp | 一致 |
| 434 | −83.4 | 円 | step/fam_tables.md:86 / step_4/diag_tables.json d7.all.mean | -83.4 / -4.1704 bp(× 20 = -83.41 円) | 円 / bp | 一致 |
| 434 | −130.0 | 円 | step/fam_tables.md:86 / step_4/diag_tables.json d7.all.lo | -130.0 / -6.4984 bp(× 20 = -129.97 円) | 円 / bp | 一致 |
| 434 | −34.1 | 円 | step/fam_tables.md:86 / step_4/diag_tables.json d7.all.hi | -34.1 / -1.7056 bp(× 20 = -34.11 円) | 円 / bp | 一致 |
| 434 | 69.4 | 円 | step/fam_tables.md:86 / step_4/diag_tables.json d7.all.mde | +69.4 / +3.4708 bp(× 20 = +69.42 円) | 円 / bp | 一致 |
| 434 | −233 | 円 | step/fam_tables.md:86 | -233 | 円 | 一致 |
| 434 | −314 | 円 | step/fam_tables.md:86 | -314 | 円 | 一致 |
| 434 | −160 | 円 | step/fam_tables.md:86 | -160 | 円 | 一致 |
| 434 | +66 | 円 | step/fam_tables.md:86 | +66 | 円 | 一致 |
| 434 | +12 | 円 | step/fam_tables.md:86 | +12 | 円 | 一致 |
| 434 | +116 | 円 | step/fam_tables.md:86 | +116 | 円 | 一致 |
| 434 | −37 | 円 | step/fam_tables.md:93 / step_4/diag_tables.json d7.years.2016.mean | -37 / -1.8258 bp(× 20 = -36.52 円) | 円 / bp | 一致 |
| 434 | −389 | 円 | step/fam_tables.md:93 / step_4/diag_tables.json d7.years.2018.mean | -389 / -19.4665 bp(× 20 = -389.33 円) | 円 / bp | 一致 |
| 434 | −109 | 円 | step/fam_tables.md:93 / step_4/diag_tables.json d7.years.2020.mean | -109 / -5.4526 bp(× 20 = -109.05 円) | 円 / bp | 一致 |
| 434 | +67 | 円 | step/fam_tables.md:93 / step_4/diag_tables.json d7.years.2022.mean | +67 / +3.3281 bp(× 20 = +66.56 円) | 円 / bp | 一致 |
| 434 | +233 | 円 | step/fam_tables.md:93 / step_4/diag_tables.json d7.years.2023.mean | +233 / +11.6438 bp(× 20 = +232.88 円) | 円 / bp | 一致 |
| 438 | −116 | 円 | step/fam_tables.md:85 | -116 | 円 | 一致 |
| 438 | −163 | 円 | step/fam_tables.md:85 | -163 | 円 | 一致 |
| 438 | −72 | 円 | step/fam_tables.md:85 | -72 | 円 | 一致 |
| 438 | +50 | 円 | step/fam_tables.md:85 | +50 | 円 | 一致 |
| 438 | +16 | 円 | step/fam_tables.md:85 | +16 | 円 | 一致 |
| 438 | +84 | 円 | step/fam_tables.md:85 | +84 | 円 | 一致 |
| 438 | −233 | 円 | step/fam_tables.md:86 | -233 | 円 | 一致 |
| 438 | −314 | 円 | step/fam_tables.md:86 | -314 | 円 | 一致 |
| 438 | −160 | 円 | step/fam_tables.md:86 | -160 | 円 | 一致 |
| 438 | +66 | 円 | step/fam_tables.md:85 | +66 | 円 | 一致 |
| 438 | +12 | 円 | step/fam_tables.md:86 | +12 | 円 | 一致 |
| 438 | +116 | 円 | step/fam_tables.md:86 | +116 | 円 | 一致 |
| 438 | −100 | 円 | step/fam_tables.md:32・36 | −67 − (+33) = −100 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 438 | −231 | 円 | step/fam_tables.md:34・36 | −198 − (+33) = −231 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 438 | +67 | 円 | step/fam_tables.md:33・35 | +184 − (+117) = +67 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 438 | +66 | 円 | step/fam_tables.md:85 | +66 | 円 | 一致 |
| 438 | +34 | 円 | step/fam_tables.md:31・35 | +151 − (+117) = +34 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 438 | +50 | 円 | step/fam_tables.md:85 | +50 | 円 | 一致 |
| 438 | +33 | 円 | step/fam_tables.md:36 | +33 | 円 | 一致 |
| 438 | −100 | 円 | step/fam_tables.md:36 | -100 | 円 | 一致 |
| 438 | +167 | 円 | step/fam_tables.md:33 | +167 | 円 | 一致 |
| 438 | −67 | 円 | step/fam_tables.md:32 | -67 | 円 | 一致 |
| 438 | −168 | 円 | step/fam_tables.md:32 | -168 | 円 | 一致 |
| 438 | +32 | 円 | step/fam_tables.md:32 | +32 | 円 | 一致 |
| 438 | −198 | 円 | step/fam_tables.md:34 | -198 | 円 | 一致 |
| 438 | −270 | 円 | step/fam_tables.md:34 | -270 | 円 | 一致 |
| 438 | −127 | 円 | step/fam_tables.md:34 | -127 | 円 | 一致 |
| 438 | +46.7 | 円 | step/levels_reason.out:27 | +46.7 | 円 | 一致 |
| 438 | +20.0 | 円 | step/levels_reason.out:17 | +20.0 | 円 | 一致 |
| 438 | −341.7 | 円 | step/levels_reason.out:28 | -341.7 | 円 | 一致 |
| 438 | −162.7 | 円 | step/levels_reason.out:18 | -162.7 | 円 | 一致 |

### break_dist(`docs/ANALYSIS/2026-10-09_matilda_main_break_dist.md`)

拾った数 683: 一致 676・単位の誤り 0・値の誤り 1・出所が無い・見つからない 6・確かめられない 0

| 文書の行 | 書かれた数 | 書かれた単位 | 出所 ファイル:行 | 出所の値 | 出所の単位 | 判定 |
|---|---|---|---|---|---|---|
| 56 | +269,844.29 | 円 | break_dist/fam_tables.md:7 | 269844.29 | 円 | 一致 |
| 56 | +269,304.527 | 円 | break_dist/fam_tables.md:8 | 269304.527 | 円 | 一致 |
| 84 | +422 | 円 | break_dist/market_side.out:1 | 422 | 円 | 一致 |
| 84 | −10 | 円 | break_dist/market_side.out:2 | -10 | 円 | 一致 |
| 84 | +269,844 | 円 | break_dist/fam_tables.md:7 | 269844.29 | 円 | 一致 |
| 84 | +269,305 | 円 | break_dist/fam_tables.md:8 | 269304.527 | 円 | 一致 |
| 112 | +345 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.first.mean | +345 / +17.2728 bp(× 20 = +345.46 円) | 円 / bp | 一致 |
| 112 | +248 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.first.lo | +248 / +12.4077 bp(× 20 = +248.15 円) | 円 / bp | 一致 |
| 112 | +456 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.first.hi | +456 / +22.7951 bp(× 20 = +455.90 円) | 円 / bp | 一致 |
| 112 | 152 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.first.mde | +152 / +7.5792 bp(× 20 = +151.58 円) | 円 / bp | 一致 |
| 112 | −162 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.second.mean | -162 / -8.0827 bp(× 20 = -161.65 円) | 円 / bp | 一致 |
| 112 | −236 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.second.lo | -236 / -11.8001 bp(× 20 = -236.00 円) | 円 / bp | 一致 |
| 112 | −82 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.second.hi | -82 / -4.0757 bp(× 20 = -81.51 円) | 円 / bp | 一致 |
| 112 | 111 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.second.mde | +111 / +5.5272 bp(× 20 = +110.54 円) | 円 / bp | 一致 |
| 112 | −507 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.diff.mean | -507 / -25.3555 bp(× 20 = -507.11 円) | 円 / bp | 一致 |
| 112 | −645 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.diff.lo | -645 / -32.2383 bp(× 20 = -644.77 円) | 円 / bp | 一致 |
| 112 | −374 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.diff.hi | -374 / -18.6960 bp(× 20 = -373.92 円) | 円 / bp | 一致 |
| 112 | +92 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.rows[0].mean | +92 / +4.5908 bp(× 20 = +91.82 円) | 円 / bp | 一致 |
| 112 | +21 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.rows[0].lo | +21 / +1.0286 bp(× 20 = +20.57 円) | 円 / bp | 一致 |
| 112 | +155 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.rows[0].hi | +155 / +7.7464 bp(× 20 = +154.93 円) | 円 / bp | 一致 |
| 113 | +472 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.segments.first.mean | +472 / +23.6182 bp(× 20 = +472.36 円) | 円 / bp | 一致 |
| 113 | +307 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.rows[5].mde または d1.segments.first.lo | +307 / +15.3581 bp(× 20 = +307.16 円) | 円 / bp | 一致 |
| 113 | +636 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.segments.first.hi | +636 / +31.8200 bp(× 20 = +636.40 円) | 円 / bp | 一致 |
| 113 | 237 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.segments.first.mde | +237 / +11.8376 bp(× 20 = +236.75 円) | 円 / bp | 一致 |
| 113 | −289 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.segments.second.mean | -289 / -14.4422 bp(× 20 = -288.84 円) | 円 / bp | 一致 |
| 113 | −415 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.segments.second.lo | -415 / -20.7712 bp(× 20 = -415.42 円) | 円 / bp | 一致 |
| 113 | −176 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.segments.second.hi | -176 / -8.8215 bp(× 20 = -176.43 円) | 円 / bp | 一致 |
| 113 | 169 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.segments.second.mde | +169 / +8.4338 bp(× 20 = +168.68 円) | 円 / bp | 一致 |
| 113 | −761 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.segments.diff.mean | -761 / -38.0604 bp(× 20 = -761.21 円) | 円 / bp | 一致 |
| 113 | −969 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.segments.diff.lo | -969 / -48.4282 bp(× 20 = -968.56 円) | 円 / bp | 一致 |
| 113 | −567 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.segments.diff.hi | -567 / -28.3727 bp(× 20 = -567.45 円) | 円 / bp | 一致 |
| 113 | +92 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.rows[0].mean | +92 / +4.5816 bp(× 20 = +91.63 円) | 円 / bp | 一致 |
| 113 | −16 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.rows[0].lo | -16 / -0.8219 bp(× 20 = -16.44 円) | 円 / bp | 一致 |
| 113 | +193 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.rows[0].hi | +193 / +9.6706 bp(× 20 = +193.41 円) | 円 / bp | 一致 |
| 114 | +362 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.segments.first.mean | +362 / +18.1147 bp(× 20 = +362.29 円) | 円 / bp | 一致 |
| 114 | +231 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.segments.first.lo | +231 / +11.5545 bp(× 20 = +231.09 円) | 円 / bp | 一致 |
| 114 | +497 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.segments.first.hi | +497 / +24.8558 bp(× 20 = +497.12 円) | 円 / bp | 一致 |
| 114 | 195 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.segments.first.mde | +195 / +9.7558 bp(× 20 = +195.12 円) | 円 / bp | 一致 |
| 114 | −273 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.segments.second.mean | -273 / -13.6334 bp(× 20 = -272.67 円) | 円 / bp | 一致 |
| 114 | −360 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.segments.second.lo | -360 / -17.9998 bp(× 20 = -360.00 円) | 円 / bp | 一致 |
| 114 | −184 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.segments.second.hi | -184 / -9.1933 bp(× 20 = -183.87 円) | 円 / bp | 一致 |
| 114 | 125 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.segments.second.mde | +125 / +6.2593 bp(× 20 = +125.19 円) | 円 / bp | 一致 |
| 114 | −635 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.segments.diff.mean | -635 / -31.7481 bp(× 20 = -634.96 円) | 円 / bp | 一致 |
| 114 | −805 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.segments.diff.lo | -805 / -40.2715 bp(× 20 = -805.43 円) | 円 / bp | 一致 |
| 114 | −476 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.segments.diff.hi | -476 / -23.8222 bp(× 20 = -476.44 円) | 円 / bp | 一致 |
| 114 | +45 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.rows[0].mean | +45 / +2.2353 bp(× 20 = +44.71 円) | 円 / bp | 一致 |
| 114 | −41 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.rows[0].lo | -41 / -2.0563 bp(× 20 = -41.13 円) | 円 / bp | 一致 |
| 114 | +124 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.rows[0].hi | +124 / +6.2076 bp(× 20 = +124.15 円) | 円 / bp | 一致 |
| 120 | −67 | 円 | break_dist/fam_tables.md:23 / break_dist_0.25/diag_tables.json d1.rows[1].mean | -67 / -3.3341 bp(× 20 = -66.68 円) | 円 / bp | 一致 |
| 120 | +149 | 円 | break_dist/fam_tables.md:23 / break_dist_0.25/diag_tables.json d1.rows[2].mean | +149 / +7.4648 bp(× 20 = +149.30 円) | 円 / bp | 一致 |
| 120 | +597 | 円 | break_dist/fam_tables.md:23 / break_dist_0.25/diag_tables.json d1.rows[3].mean | +597 / +29.8525 bp(× 20 = +597.05 円) | 円 / bp | 一致 |
| 120 | +368 | 円 | break_dist/fam_tables.md:23 / break_dist_0.25/diag_tables.json d1.rows[4].mean | +368 / +18.3884 bp(× 20 = +367.77 円) | 円 / bp | 一致 |
| 120 | +293 | 円 | break_dist/fam_tables.md:23 / break_dist_0.25/diag_tables.json d1.rows[5].mean | +293 / +14.6529 bp(× 20 = +293.06 円) | 円 / bp | 一致 |
| 120 | +79 | 円 | break_dist/fam_tables.md:23 / break_dist_0.25/diag_tables.json d1.rows[6].mean | +79 / +3.9592 bp(× 20 = +79.18 円) | 円 / bp | 一致 |
| 120 | −205 | 円 | break_dist/fam_tables.md:23 / break_dist_0.25/diag_tables.json d1.rows[7].mean | -205 / -10.2512 bp(× 20 = -205.02 円) | 円 / bp | 一致 |
| 120 | −183 | 円 | break_dist/fam_tables.md:23 / break_dist_0.25/diag_tables.json d1.rows[8].mean | -183 / -9.1750 bp(× 20 = -183.50 円) | 円 / bp | 一致 |
| 120 | −368 | 円 | break_dist/fam_tables.md:23 / break_dist_0.25/diag_tables.json d1.rows[9].mean | -368 / -18.3799 bp(× 20 = -367.60 円) | 円 / bp | 一致 |
| 121 | −660 | 円 | break_dist/fam_tables.md:24 / break_dist_1/diag_tables.json d1.rows[1].mean | -660 / -32.9914 bp(× 20 = -659.83 円) | 円 / bp | 一致 |
| 121 | +132 | 円 | break_dist/fam_tables.md:24 / break_dist_1/diag_tables.json d1.rows[2].mean | +132 / +6.5902 bp(× 20 = +131.80 円) | 円 / bp | 一致 |
| 121 | +822 | 円 | break_dist/fam_tables.md:24 / break_dist_1/diag_tables.json d1.rows[3].mean | +822 / +41.0916 bp(× 20 = +821.83 円) | 円 / bp | 一致 |
| 121 | +592 | 円 | break_dist/fam_tables.md:24 / break_dist_1/diag_tables.json d1.rows[4].mean | +592 / +29.5928 bp(× 20 = +591.86 円) | 円 / bp | 一致 |
| 121 | +426 | 円 | break_dist/fam_tables.md:24 / break_dist_1/diag_tables.json d1.rows[5].mean | +426 / +21.3099 bp(× 20 = +426.20 円) | 円 / bp | 一致 |
| 121 | +146 | 円 | break_dist/fam_tables.md:24 / break_dist_1/diag_tables.json d1.rows[6].mean | +146 / +7.2951 bp(× 20 = +145.90 円) | 円 / bp | 一致 |
| 121 | −459 | 円 | break_dist/fam_tables.md:24 / break_dist_1/diag_tables.json d1.rows[7].mean | -459 / -22.9667 bp(× 20 = -459.33 円) | 円 / bp | 一致 |
| 121 | −324 | 円 | break_dist/fam_tables.md:24 / break_dist_1/diag_tables.json d1.rows[8].mean | -324 / -16.1758 bp(× 20 = -323.52 円) | 円 / bp | 一致 |
| 121 | −563 | 円 | break_dist/fam_tables.md:24 / break_dist_1/diag_tables.json d1.rows[9].mean | -563 / -28.1622 bp(× 20 = -563.24 円) | 円 / bp | 一致 |
| 122 | −263 | 円 | break_dist/fam_tables.md:25 / base/diag_tables.json d1.rows[1].mean または d1.rows[8].mean | -263 / -13.1430 bp(× 20 = -262.86 円) | 円 / bp | 一致 |
| 122 | +133 | 円 | break_dist/fam_tables.md:25 / base/diag_tables.json d1.rows[2].mean | +133 / +6.6326 bp(× 20 = +132.65 円) | 円 / bp | 一致 |
| 122 | +564 | 円 | break_dist/fam_tables.md:25 / base/diag_tables.json d1.rows[3].mean | +564 / +28.1875 bp(× 20 = +563.75 円) | 円 / bp | 一致 |
| 122 | +543 | 円 | break_dist/fam_tables.md:25 / base/diag_tables.json d1.rows[4].mean | +543 / +27.1491 bp(× 20 = +542.98 円) | 円 / bp | 一致 |
| 122 | +244 | 円 | break_dist/fam_tables.md:25 / base/diag_tables.json d1.rows[5].mean | +244 / +12.2149 bp(× 20 = +244.30 円) | 円 / bp | 一致 |
| 122 | +6 | 円 | break_dist/fam_tables.md:25 / base/diag_tables.json d1.rows[6].mean | +6 / +0.2952 bp(× 20 = +5.90 円) | 円 / bp | 一致 |
| 122 | −384 | 円 | break_dist/fam_tables.md:25 / base/diag_tables.json d1.rows[7].mean | -384 / -19.2131 bp(× 20 = -384.26 円) | 円 / bp | 一致 |
| 122 | −263 | 円 | break_dist/fam_tables.md:25 / base/diag_tables.json d1.rows[1].mean または d1.rows[8].mean | -263 / -13.1430 bp(× 20 = -262.86 円) | 円 / bp | 一致 |
| 122 | −479 | 円 | break_dist/fam_tables.md:25 / base/diag_tables.json d1.rows[9].mean | -479 / -23.9354 bp(× 20 = -478.71 円) | 円 / bp | 一致 |
| 124 | +345 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.first.mean | +345 / +17.2728 bp(× 20 = +345.46 円) | 円 / bp | 一致 |
| 124 | −162 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.second.mean | -162 / -8.0827 bp(× 20 = -161.65 円) | 円 / bp | 一致 |
| 124 | +472 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.segments.first.mean | +472 / +23.6182 bp(× 20 = +472.36 円) | 円 / bp | 一致 |
| 124 | −289 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.segments.second.mean | -289 / -14.4422 bp(× 20 = -288.84 円) | 円 / bp | 一致 |
| 124 | +92 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.rows[0].mean | +92 / +4.5908 bp(× 20 = +91.82 円) | 円 / bp | 一致 |
| 124 | +21 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.rows[0].lo | +21 / +1.0286 bp(× 20 = +20.57 円) | 円 / bp | 一致 |
| 124 | +155 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.rows[0].hi | +155 / +7.7464 bp(× 20 = +154.93 円) | 円 / bp | 一致 |
| 157 | +242 | 円 | break_dist/scenes.out:5 | +242 | 円 | 一致 |
| 157 | +143 | 円 | break_dist/scenes.out:5 | +143 | 円 | 一致 |
| 157 | +343 | 円 | break_dist/scenes.out:5 | +343 | 円 | 一致 |
| 157 | +350 | 円 | break_dist/scenes.out:17 | +350 | 円 | 一致 |
| 157 | +222 | 円 | break_dist/scenes.out:17 | +222 | 円 | 一致 |
| 157 | +476 | 円 | break_dist/scenes.out:17 | +476 | 円 | 一致 |
| 157 | +264 | 円 | base_scenes.out:5 | +264 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 157 | −136 | 円 | break_dist/scenes.out:6 | -136 | 円 | 一致 |
| 157 | −204 | 円 | break_dist/scenes.out:6 | -204 | 円 | 一致 |
| 157 | −54 | 円 | break_dist/scenes.out:6 | -54 | 円 | 一致 |
| 157 | −227 | 円 | break_dist/scenes.out:18 | -227 | 円 | 一致 |
| 157 | −338 | 円 | break_dist/scenes.out:18 | -338 | 円 | 一致 |
| 157 | −112 | 円 | break_dist/scenes.out:18 | -112 | 円 | 一致 |
| 157 | −216 | 円 | base_scenes.out:6 | -216 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 158 | +395 | 円 | break_dist/scenes.out:8 | +395 | 円 | 一致 |
| 158 | +246 | 円 | break_dist/scenes.out:8 | +246 | 円 | 一致 |
| 158 | +572 | 円 | break_dist/scenes.out:8 | +572 | 円 | 一致 |
| 158 | +491 | 円 | break_dist/scenes.out:20 | +491 | 円 | 一致 |
| 158 | +229 | 円 | break_dist/scenes.out:20 | +229 | 円 | 一致 |
| 158 | +789 | 円 | break_dist/scenes.out:20 | +789 | 円 | 一致 |
| 158 | +411 | 円 | base_scenes.out:8 | +411 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 158 | −222 | 円 | break_dist/scenes.out:9 | -222 | 円 | 一致 |
| 158 | −349 | 円 | break_dist/scenes.out:9 | -349 | 円 | 一致 |
| 158 | −106 | 円 | break_dist/scenes.out:9 | -106 | 円 | 一致 |
| 158 | −291 | 円 | break_dist/scenes.out:21 | -291 | 円 | 一致 |
| 158 | −506 | 円 | break_dist/scenes.out:21 | -506 | 円 | 一致 |
| 158 | −74 | 円 | break_dist/scenes.out:21 | -74 | 円 | 一致 |
| 158 | −282 | 円 | base_scenes.out:9 | -282 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 159 | +598 | 円 | break_dist/scenes.out:11 | +598 | 円 | 一致 |
| 159 | +359 | 円 | break_dist/scenes.out:11 | +359 | 円 | 一致 |
| 159 | +848 | 円 | break_dist/scenes.out:11 | +848 | 円 | 一致 |
| 159 | +931 | 円 | break_dist/scenes.out:23 | +931 | 円 | 一致 |
| 159 | +579 | 円 | break_dist/scenes.out:23 | +579 | 円 | 一致 |
| 159 | +1,324 | 円 | break_dist/scenes.out:23 | +1324 | 円 | 一致 |
| 159 | +656 | 円 | base_scenes.out:11 | +656 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 159 | −148 | 円 | break_dist/scenes.out:12 | -148 | 円 | 一致 |
| 159 | −327 | 円 | break_dist/scenes.out:12 | -327 | 円 | 一致 |
| 159 | +51 | 円 | break_dist/scenes.out:12 | +51 | 円 | 一致 |
| 159 | −372 | 円 | break_dist/scenes.out:24 | -372 | 円 | 一致 |
| 159 | −629 | 円 | break_dist/scenes.out:24 | -629 | 円 | 一致 |
| 159 | −103 | 円 | break_dist/scenes.out:24 | -103 | 円 | 一致 |
| 159 | −343 | 円 | base_scenes.out:12 | -343 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 165 | −21 | 円 | break_dist/scene_diff.out:4 | -21 | 円 | 一致 |
| 165 | −91 | 円 | break_dist/scene_diff.out:4 | -91 | 円 | 一致 |
| 165 | +55 | 円 | break_dist/scene_diff.out:4 | +55 | 円 | 一致 |
| 165 | +80 | 円 | break_dist/scene_diff.out:5 | +80 | 円 | 一致 |
| 165 | +40 | 円 | break_dist/scene_diff.out:5 | +40 | 円 | 一致 |
| 165 | +133 | 円 | break_dist/scene_diff.out:5 | +133 | 円 | 一致 |
| 165 | +87 | 円 | break_dist/scene_diff.out:13 | +87 | 円 | 一致 |
| 165 | −1 | 円 | break_dist/scene_diff.out:13 | -1 | 円 | 一致 |
| 165 | +179 | 円 | break_dist/scene_diff.out:13 | +179 | 円 | 一致 |
| 165 | −11 | 円 | break_dist/scene_diff.out:14 | -11 | 円 | 一致 |
| 165 | −83 | 円 | break_dist/scene_diff.out:14 | -83 | 円 | 一致 |
| 165 | +68 | 円 | break_dist/scene_diff.out:14 | +68 | 円 | 一致 |
| 166 | −16 | 円 | break_dist/scene_diff.out:6 | -16 | 円 | 一致 |
| 166 | −160 | 円 | break_dist/scene_diff.out:6 | -160 | 円 | 一致 |
| 166 | +139 | 円 | break_dist/scene_diff.out:6 | +139 | 円 | 一致 |
| 166 | +60 | 円 | break_dist/scene_diff.out:7 | +60 | 円 | 一致 |
| 166 | −45 | 円 | break_dist/scene_diff.out:7 | -45 | 円 | 一致 |
| 166 | +150 | 円 | break_dist/scene_diff.out:7 | +150 | 円 | 一致 |
| 166 | +80 | 円 | break_dist/scene_diff.out:15 | +80 | 円 | 一致 |
| 166 | −147 | 円 | break_dist/scene_diff.out:15 | -147 | 円 | 一致 |
| 166 | +315 | 円 | break_dist/scene_diff.out:15 | +315 | 円 | 一致 |
| 166 | −9 | 円 | break_dist/scene_diff.out:16 | -9 | 円 | 一致 |
| 166 | −138 | 円 | break_dist/scene_diff.out:16 | -138 | 円 | 一致 |
| 166 | +117 | 円 | break_dist/scene_diff.out:16 | +117 | 円 | 一致 |
| 167 | −58 | 円 | break_dist/scene_diff.out:8 | -58 | 円 | 一致 |
| 167 | −266 | 円 | break_dist/scene_diff.out:8 | -266 | 円 | 一致 |
| 167 | +153 | 円 | break_dist/scene_diff.out:8 | +153 | 円 | 一致 |
| 167 | +195 | 円 | break_dist/scene_diff.out:9 | +195 | 円 | 一致 |
| 167 | +35 | 円 | break_dist/scene_diff.out:9 | +35 | 円 | 一致 |
| 167 | +360 | 円 | break_dist/scene_diff.out:9 | +360 | 円 | 一致 |
| 167 | +275 | 円 | break_dist/scene_diff.out:17 | +275 | 円 | 一致 |
| 167 | −7 | 円 | break_dist/scene_diff.out:17 | -7 | 円 | 一致 |
| 167 | +556 | 円 | break_dist/scene_diff.out:17 | +556 | 円 | 一致 |
| 167 | −29 | 円 | break_dist/scene_diff.out:18 | -29 | 円 | 一致 |
| 167 | −226 | 円 | break_dist/scene_diff.out:18 | -226 | 円 | 一致 |
| 167 | +166 | 円 | break_dist/scene_diff.out:18 | +166 | 円 | 一致 |
| 169 | +80 | 円 | break_dist/scene_diff.out:5 | +80 | 円 | 一致 |
| 169 | +40 | 円 | break_dist/scene_diff.out:5 | +40 | 円 | 一致 |
| 169 | +133 | 円 | break_dist/scene_diff.out:5 | +133 | 円 | 一致 |
| 169 | +195 | 円 | break_dist/scene_diff.out:9 | +195 | 円 | 一致 |
| 169 | +35 | 円 | break_dist/scene_diff.out:9 | +35 | 円 | 一致 |
| 169 | +360 | 円 | break_dist/scene_diff.out:9 | +360 | 円 | 一致 |
| 169 | −1 | 円 | break_dist/scene_diff.out:13 | -1 | 円 | 一致 |
| 169 | −7 | 円 | break_dist/scene_diff.out:17 | -7 | 円 | 一致 |
| 169 | −148 | 円 | break_dist/scenes.out:12 | -148 | 円 | 一致 |
| 169 | −327 | 円 | break_dist/scenes.out:12 | -327 | 円 | 一致 |
| 169 | +51 | 円 | break_dist/scenes.out:12 | +51 | 円 | 一致 |
| 190 | +39.9 | 円 | break_dist/compare.md:7 | +39.9 | 円 | 一致 |
| 190 | −173.4 | 円 | break_dist/compare.md:7 | -173.4 | 円 | 一致 |
| 190 | −219.9 | 円 | break_dist/compare.md:7 | -219.9 | 円 | 一致 |
| 190 | −2,684,367 | 円 | break_dist/compare.md:7 | -2,684,367 | 円 | 一致 |
| 190 | +507,476 | 円 | break_dist/compare.md:7 | +507,476 | 円 | 一致 |
| 191 | +38.0 | 円 | break_dist/compare.md:8 | +38.0 | 円 | 一致 |
| 191 | −479.7 | 円 | break_dist/compare.md:8 | -479.7 | 円 | 一致 |
| 191 | −380.8 | 円 | break_dist/compare.md:8 | -380.8 | 円 | 一致 |
| 191 | −4,785,051 | 円 | break_dist/compare.md:8 | -4,785,051 | 円 | 一致 |
| 191 | +693,904 | 円 | break_dist/compare.md:8 | +693,904 | 円 | 一致 |
| 192 | +40.5 | 円 | break_dist/compare.md:6 | +40.5 | 円 | 一致 |
| 192 | −281.0 | 円 | break_dist/compare.md:6 | -281.0 | 円 | 一致 |
| 192 | −273.4 | 円 | break_dist/compare.md:6 | -273.4 | 円 | 一致 |
| 192 | −3,866,293 | 円 | break_dist/compare.md:6 | -3,866,293 | 円 | 一致 |
| 192 | +532,210 | 円 | break_dist/compare.md:6 | +532,210 | 円 | 一致 |
| 193 | +32.0 | 円 | break_dist/compare.md:15 | +32.0 | 円 | 一致 |
| 193 | −144.3 | 円 | break_dist/compare.md:15 | -144.3 | 円 | 一致 |
| 193 | −358.9 | 円 | break_dist/compare.md:15 | -358.9 | 円 | 一致 |
| 193 | −2,625,845 | 円 | break_dist/compare.md:15 | -2,625,845 | 円 | 一致 |
| 193 | −237,631 | 円 | break_dist/compare.md:15 | -237,631 | 円 | 一致 |
| 194 | +29.0 | 円 | break_dist/compare.md:16 | +29.0 | 円 | 一致 |
| 194 | −407.3 | 円 | break_dist/compare.md:16 | -407.3 | 円 | 一致 |
| 194 | −577.0 | 円 | break_dist/compare.md:16 | -577.0 | 円 | 一致 |
| 194 | −4,701,133 | 円 | break_dist/compare.md:16 | -4,701,133 | 円 | 一致 |
| 194 | −424,600 | 円 | break_dist/compare.md:16 | -424,600 | 円 | 一致 |
| 195 | +32.2 | 円 | break_dist/compare.md:14 | +32.2 | 円 | 一致 |
| 195 | −238.4 | 円 | break_dist/compare.md:14 | -238.4 | 円 | 一致 |
| 195 | −431.6 | 円 | break_dist/compare.md:14 | -431.6 | 円 | 一致 |
| 195 | −3,834,951 | 円 | break_dist/compare.md:14 | -3,834,951 | 円 | 一致 |
| 195 | −400,821 | 円 | break_dist/compare.md:14 | -400,821 | 円 | 一致 |
| 201 | +197 | 円 | break_dist/fam_tables.md:31 | +197 | 円 | 一致 |
| 201 | +157 | 円 | break_dist/fam_tables.md:31 | +157 | 円 | 一致 |
| 201 | +242 | 円 | break_dist/fam_tables.md:31 | +242 | 円 | 一致 |
| 201 | +24 | 円 | break_dist/fam_tables.md:31 | +24 | 円 | 一致 |
| 201 | +5 | 円 | break_dist/fam_tables.md:31 | +5 | 円 | 一致 |
| 201 | +43 | 円 | break_dist/fam_tables.md:31 | +43 | 円 | 一致 |
| 201 | −67.6 | 円 | break_dist/levels_reason.out:4 | -67.6 | 円 | 一致 |
| 201 | −60.0 | 円 | break_dist/levels_reason.out:6 | -60.0 | 円 | 一致 |
| 202 | +148 | 円 | break_dist/fam_tables.md:32 | +148 | 円 | 一致 |
| 202 | +48 | 円 | break_dist/fam_tables.md:32 | +48 | 円 | 一致 |
| 202 | +257 | 円 | break_dist/fam_tables.md:32 | +257 | 円 | 一致 |
| 202 | −185 | 円 | break_dist/fam_tables.md:32 | -185 | 円 | 一致 |
| 202 | −255 | 円 | break_dist/fam_tables.md:32 | -255 | 円 | 一致 |
| 202 | −109 | 円 | break_dist/fam_tables.md:32 | -109 | 円 | 一致 |
| 202 | −231.9 | 円 | break_dist/levels_reason.out:8 | -231.9 | 円 | 一致 |
| 202 | −181.8 | 円 | break_dist/levels_reason.out:11 | -181.8 | 円 | 一致 |
| 203 | +582 | 円 | break_dist/fam_tables.md:33 | +582 | 円 | 一致 |
| 203 | +516 | 円 | break_dist/fam_tables.md:33 | +516 | 円 | 一致 |
| 203 | +639 | 円 | break_dist/fam_tables.md:33 | +639 | 円 | 一致 |
| 203 | +307 | 円 | break_dist/fam_tables.md:33 | +307 | 円 | 一致 |
| 203 | +280 | 円 | break_dist/fam_tables.md:33 | +280 | 円 | 一致 |
| 203 | +335 | 円 | break_dist/fam_tables.md:33 | +335 | 円 | 一致 |
| 203 | −183.7 | 円 | break_dist/levels_reason.out:14 | -183.7 | 円 | 一致 |
| 203 | −167.2 | 円 | break_dist/levels_reason.out:16 | -167.2 | 円 | 一致 |
| 204 | −110 | 円 | break_dist/fam_tables.md:34 | -110 | 円 | 一致 |
| 204 | −278 | 円 | break_dist/fam_tables.md:34 | -278 | 円 | 一致 |
| 204 | +50 | 円 | break_dist/fam_tables.md:34 | +50 | 円 | 一致 |
| 204 | −596 | 円 | break_dist/fam_tables.md:34 | -596 | 円 | 一致 |
| 204 | −721 | 円 | break_dist/fam_tables.md:34 | -721 | 円 | 一致 |
| 204 | −483 | 円 | break_dist/fam_tables.md:34 | -483 | 円 | 一致 |
| 204 | −540.0 | 円 | break_dist/levels_reason.out:18 | -540.0 | 円 | 一致 |
| 204 | −448.9 | 円 | break_dist/levels_reason.out:21 | -448.9 | 円 | 一致 |
| 205 | +329 | 円 | break_dist/fam_tables.md:35 | +329 | 円 | 一致 |
| 205 | +274 | 円 | break_dist/fam_tables.md:35 | +274 | 円 | 一致 |
| 205 | +378 | 円 | break_dist/fam_tables.md:35 | +378 | 円 | 一致 |
| 205 | +117 | 円 | break_dist/fam_tables.md:35 | +117 | 円 | 一致 |
| 205 | +92 | 円 | break_dist/fam_tables.md:35 | +92 | 円 | 一致 |
| 205 | +141 | 円 | break_dist/fam_tables.md:35 | +141 | 円 | 一致 |
| 205 | −113.4 | 円 | break_dist/levels_reason.out:24 | -113.4 | 円 | 一致 |
| 205 | −103.8 | 円 | break_dist/levels_reason.out:26 | -103.8 | 円 | 一致 |
| 206 | +33 | 円 | break_dist/fam_tables.md:36 | +33 | 円 | 一致 |
| 206 | −100 | 円 | break_dist/fam_tables.md:36 | -100 | 円 | 一致 |
| 206 | +167 | 円 | break_dist/fam_tables.md:36 | +167 | 円 | 一致 |
| 206 | −390 | 円 | break_dist/fam_tables.md:36 | -390 | 円 | 一致 |
| 206 | −474 | 円 | break_dist/fam_tables.md:36 | -474 | 円 | 一致 |
| 206 | −302 | 円 | break_dist/fam_tables.md:36 | -302 | 円 | 一致 |
| 206 | −341.7 | 円 | break_dist/levels_reason.out:28 | -341.7 | 円 | 一致 |
| 206 | −277.2 | 円 | break_dist/levels_reason.out:31 | -277.2 | 円 | 一致 |
| 208 | +36.1 | 円 | break_dist/fam_tables.md:40 / break_dist_0.25/diag_tables.json d3.groups.出の理由【結果で決まる群】.close.per_trade | +36.1 / +1.8025 bp(× 20 = +36.05 円) | 円 / bp | 一致 |
| 208 | +34.3 | 円 | break_dist/fam_tables.md:40 / break_dist_0.25/diag_tables.json d3.groups.出の理由【結果で決まる群】.close.lo | +34.3 / +1.7135 bp(× 20 = +34.27 円) | 円 / bp | 一致 |
| 208 | +37.8 | 円 | break_dist/fam_tables.md:40 / break_dist_0.25/diag_tables.json d3.groups.出の理由【結果で決まる群】.close.hi | +37.8 / +1.8903 bp(× 20 = +37.81 円) | 円 / bp | 一致 |
| 208 | −158.2 | 円 | break_dist/fam_tables.md:40 / break_dist_0.25/diag_tables.json d3.groups.出の理由【結果で決まる群】.break.per_trade | -158.2 / -7.9102 bp(× 20 = -158.20 円) | 円 / bp | 一致 |
| 208 | −166.5 | 円 | break_dist/fam_tables.md:40 / break_dist_0.25/diag_tables.json d3.groups.出の理由【結果で決まる群】.break.lo | -166.5 / -8.3229 bp(× 20 = -166.46 円) | 円 / bp | 一致 |
| 208 | −150.1 | 円 | break_dist/fam_tables.md:40 / break_dist_0.25/diag_tables.json d3.groups.出の理由【結果で決まる群】.break.hi | -150.1 / -7.5051 bp(× 20 = -150.10 円) | 円 / bp | 一致 |
| 208 | −246.8 | 円 | break_dist/fam_tables.md:40 / break_dist_0.25/diag_tables.json d3.groups.出の理由【結果で決まる群】.market.per_trade | -246.8 / -12.3377 bp(× 20 = -246.75 円) | 円 / bp | 一致 |
| 208 | +33.6 | 円 | break_dist/fam_tables.md:41 / break_dist_1/diag_tables.json d3.groups.出の理由【結果で決まる群】.close.per_trade | +33.6 / +1.6775 bp(× 20 = +33.55 円) | 円 / bp | 一致 |
| 208 | +32.0 | 円 | break_dist/fam_tables.md:41 / break_dist_1/diag_tables.json d3.groups.出の理由【結果で決まる群】.close.lo | +32.0 / +1.6012 bp(× 20 = +32.02 円) | 円 / bp | 一致 |
| 208 | +35.1 | 円 | break_dist/fam_tables.md:41 / break_dist_1/diag_tables.json d3.groups.出の理由【結果で決まる群】.close.hi | +35.1 / +1.7566 bp(× 20 = +35.13 円) | 円 / bp | 一致 |
| 208 | −442.3 | 円 | break_dist/fam_tables.md:41 / break_dist_1/diag_tables.json d3.groups.出の理由【結果で決まる群】.break.per_trade | -442.3 / -22.1175 bp(× 20 = -442.35 円) | 円 / bp | 一致 |
| 208 | −465.6 | 円 | break_dist/fam_tables.md:41 / break_dist_1/diag_tables.json d3.groups.出の理由【結果で決まる群】.break.lo | -465.6 / -23.2793 bp(× 20 = -465.59 円) | 円 / bp | 一致 |
| 208 | −419.2 | 円 | break_dist/fam_tables.md:41 / break_dist_1/diag_tables.json d3.groups.出の理由【結果で決まる群】.break.hi | -419.2 / -20.9589 bp(× 20 = -419.18 円) | 円 / bp | 一致 |
| 208 | −447.5 | 円 | break_dist/fam_tables.md:41 / break_dist_1/diag_tables.json d3.groups.出の理由【結果で決まる群】.market.per_trade | -447.5 / -22.3755 bp(× 20 = -447.51 円) | 円 / bp | 一致 |
| 208 | +36.4 | 円 | break_dist/fam_tables.md:42 / base/diag_tables.json d3.groups.出の理由【結果で決まる群】.close.per_trade | +36.4 / +1.8210 bp(× 20 = +36.42 円) | 円 / bp | 一致 |
| 208 | −258.8 | 円 | break_dist/fam_tables.md:42 / base/diag_tables.json d3.groups.出の理由【結果で決まる群】.break.per_trade | -258.8 / -12.9406 bp(× 20 = -258.81 円) | 円 / bp | 一致 |
| 209 | +552,335 | 円 | break_dist/fam_tables.md:40 / break_dist_0.25/diag_tables.json d3.top5_days_sum | +552,335 / +27616.7538 bp(× 20 = +552335.08 円) | 円 / bp | 一致 |
| 209 | −614,572 | 円 | break_dist/fam_tables.md:40 / break_dist_0.25/diag_tables.json d3.bottom5_days_sum | -614,572 / -30728.6080 bp(× 20 = -614572.16 円) | 円 / bp | 一致 |
| 209 | +770,629 | 円 | break_dist/fam_tables.md:41 / break_dist_1/diag_tables.json d3.top5_days_sum | +770,629 / +38531.4641 bp(× 20 = +770629.28 円) | 円 / bp | 一致 |
| 209 | −984,043 | 円 | break_dist/fam_tables.md:41 / break_dist_1/diag_tables.json d3.bottom5_days_sum | -984,043 / -49202.1433 bp(× 20 = -984042.87 円) | 円 / bp | 一致 |
| 209 | +269,844 | 円 | break_dist/fam_tables.md:40 / break_dist_0.25/diag_tables.json d3.total | +269,844 / +13492.2145 bp(× 20 = +269844.29 円) | 円 / bp | 一致 |
| 209 | +269,305 | 円 | break_dist/fam_tables.md:41 / break_dist_1/diag_tables.json d3.total | +269,305 / +13465.2263 bp(× 20 = +269304.53 円) | 円 / bp | 一致 |
| 210 | −259 | 円 | break_dist/compare.md:22 | -258.8 | 円 | 一致 |
| 210 | −158 | 円 | break_dist/compare.md:23 | -158.2 | 円 | 一致 |
| 210 | −442 | 円 | break_dist/compare.md:24 | -442.3 | 円 | 一致 |
| 210 | +329 | 円 | break_dist/fam_tables.md:35 | +329 | 円 | 一致 |
| 210 | +197 | 円 | break_dist/fam_tables.md:31 | +197 | 円 | 一致 |
| 210 | +117 | 円 | break_dist/fam_tables.md:35 | +117 | 円 | 一致 |
| 210 | +24 | 円 | break_dist/fam_tables.md:31 | +24 | 円 | 一致 |
| 210 | +582 | 円 | break_dist/fam_tables.md:33 | +582 | 円 | 一致 |
| 210 | +307 | 円 | break_dist/fam_tables.md:33 | +307 | 円 | 一致 |
| 210 | +148 | 円 | break_dist/fam_tables.md:32 | +148 | 円 | 一致 |
| 210 | +48 | 円 | break_dist/fam_tables.md:32 | +48 | 円 | 一致 |
| 210 | +257 | 円 | break_dist/fam_tables.md:32 | +257 | 円 | 一致 |
| 210 | −185 | 円 | break_dist/fam_tables.md:32 | -185 | 円 | 一致 |
| 210 | −110 | 円 | break_dist/fam_tables.md:34 | -110 | 円 | 一致 |
| 210 | −596 | 円 | break_dist/fam_tables.md:34 | -596 | 円 | 一致 |
| 232 | +8,085,911 | 円 | break_dist/fam_tables.md:48 / break_dist_0.25/diag_paths.json d4.groups.勝った.pnl_sum | +8,085,911 / +404295.5262 bp(× 20 = +8085910.52 円) | 円 / bp | 一致 |
| 232 | 6.29 | move_bp | break_dist/fam_tables.md:48 / break_dist_0.25/diag_paths.json d4.groups.勝った.mfe_median | 6.29 / +6.2934 move_bp | move_bp / move_bp | 一致 |
| 232 | −4.13 | move_bp | break_dist/fam_tables.md:48 / break_dist_0.25/diag_paths.json d4.groups.勝った.mae_median | -4.13 / -4.1332 move_bp | move_bp / move_bp | 一致 |
| 232 | +12,121,461 | 円 | break_dist/fam_tables.md:52 / break_dist_1/diag_paths.json d4.groups.勝った.pnl_sum | +12,121,461 / +606073.0264 bp(× 20 = +12121460.53 円) | 円 / bp | 一致 |
| 232 | 5.81 | move_bp | break_dist/fam_tables.md:52 / break_dist_1/diag_paths.json d4.groups.勝った.mfe_median | 5.81 / +5.8061 move_bp | move_bp / move_bp | 一致 |
| 232 | −5.32 | move_bp | break_dist/fam_tables.md:52 / break_dist_1/diag_paths.json d4.groups.勝った.mae_median | -5.32 / -5.3160 move_bp | move_bp / move_bp | 一致 |
| 232 | +10,177,344 | 円 | break_dist/fam_tables.md:56 / base/diag_paths.json d4.groups.勝った.pnl_sum | +10,177,344 / +508867.1933 bp(× 20 = +10177343.87 円) | 円 / bp | 一致 |
| 232 | 6.02 | move_bp | break_dist/fam_tables.md:56 / base/diag_paths.json d4.groups.勝った.mfe_median | 6.02 / +6.0217 move_bp | move_bp / move_bp | 一致 |
| 232 | −4.74 | move_bp | break_dist/fam_tables.md:56 / base/diag_paths.json d4.groups.勝った.mae_median | -4.74 / -4.7440 move_bp | move_bp / move_bp | 一致 |
| 233 | −3,761,000 | 円 | break_dist/fam_tables.md:49 / break_dist_0.25/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.pnl_sum | -3,761,000 / -188050.0001 bp(× 20 = -3761000.00 円) | 円 / bp | 一致 |
| 233 | 2.08 | move_bp | break_dist/fam_tables.md:49 / break_dist_0.25/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mfe_median | 2.08 / +2.0754 move_bp | move_bp / move_bp | 一致 |
| 233 | −22.45 | move_bp | break_dist/fam_tables.md:49 / break_dist_0.25/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mae_median | -22.45 / -22.4460 move_bp | move_bp / move_bp | 一致 |
| 233 | −5,419,801 | 円 | break_dist/fam_tables.md:53 / break_dist_1/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.pnl_sum | -5,419,801 / -270990.0330 bp(× 20 = -5419800.66 円) | 円 / bp | 一致 |
| 233 | 2.12 | move_bp | break_dist/fam_tables.md:53 / break_dist_1/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mfe_median | 2.12 / +2.1175 move_bp | move_bp / move_bp | 一致 |
| 233 | −41.98 | move_bp | break_dist/fam_tables.md:53 / break_dist_1/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mae_median | -41.98 / -41.9831 move_bp | move_bp / move_bp | 一致 |
| 233 | −4,695,044 | 円 | break_dist/fam_tables.md:57 / base/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.pnl_sum | -4,695,044 / -234752.1937 bp(× 20 = -4695043.87 円) | 円 / bp | 一致 |
| 233 | 2.05 | move_bp | break_dist/fam_tables.md:57 / base/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mfe_median | 2.05 / +2.0537 move_bp | move_bp / move_bp | 一致 |
| 233 | −30.50 | move_bp | break_dist/fam_tables.md:57 / base/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mae_median | -30.50 / -30.4965 move_bp | move_bp / move_bp | 一致 |
| 234 | −4,379,743 | 円 | break_dist/fam_tables.md:50 / break_dist_0.25/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.pnl_sum | -4,379,743 / -218987.1439 bp(× 20 = -4379742.88 円) | 円 / bp | 一致 |
| 234 | −2.42 | move_bp | break_dist/fam_tables.md:50 / break_dist_0.25/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mfe_median | -2.42 / -2.4245 move_bp | move_bp / move_bp | 一致 |
| 234 | −25.65 | move_bp | break_dist/fam_tables.md:50 / break_dist_0.25/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mae_median | -25.65 / -25.6450 move_bp | move_bp / move_bp | 一致 |
| 234 | −7,739,320 | 円 | break_dist/fam_tables.md:54 / break_dist_1/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.pnl_sum | -7,739,320 / -386966.0012 bp(× 20 = -7739320.02 円) | 円 / bp | 一致 |
| 234 | −3.20 | move_bp | break_dist/fam_tables.md:54 / break_dist_1/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mfe_median | -3.20 / -3.2026 move_bp | move_bp / move_bp | 一致 |
| 234 | −43.65 | move_bp | break_dist/fam_tables.md:54 / break_dist_1/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mae_median | -43.65 / -43.6485 move_bp | move_bp / move_bp | 一致 |
| 234 | −6,006,006 | 円 | break_dist/fam_tables.md:58 / base/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.pnl_sum | -6,006,006 / -300300.2903 bp(× 20 = -6006005.81 円) | 円 / bp | 一致 |
| 234 | −2.77 | move_bp | break_dist/fam_tables.md:58 / base/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mfe_median | -2.77 / -2.7731 move_bp | move_bp / move_bp | 一致 |
| 234 | −32.38 | move_bp | break_dist/fam_tables.md:58 / base/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mae_median | -32.38 / -32.3832 move_bp | move_bp / move_bp | 一致 |
| 236 | −0.39 | move_bp | break_dist/fam_tables.md:63 / break_dist_0.25/diag_paths.json d4.after_exit.5.per_trade | -0.39 / -0.3872 move_bp | move_bp / move_bp | 一致 |
| 236 | −0.76 | move_bp | break_dist/fam_tables.md:63 / break_dist_0.25/diag_paths.json d4.after_exit.15.per_trade | -0.76 / -0.7618 move_bp | move_bp / move_bp | 一致 |
| 236 | −0.75 | move_bp | break_dist/fam_tables.md:63 / break_dist_0.25/diag_paths.json d4.after_exit.60.per_trade | -0.75 / -0.7492 move_bp | move_bp / move_bp | 一致 |
| 236 | −1.25 | move_bp | break_dist/fam_tables.md:63 / break_dist_0.25/diag_paths.json d4.after_exit.60.lo | -1.25 / -1.2517 move_bp | move_bp / move_bp | 一致 |
| 236 | −0.29 | move_bp | break_dist/fam_tables.md:63 / break_dist_0.25/diag_paths.json d4.after_exit.60.hi | -0.29 / -0.2919 move_bp | move_bp / move_bp | 一致 |
| 236 | −0.33 | move_bp | break_dist/fam_tables.md:64 / break_dist_1/diag_paths.json d4.after_exit.5.per_trade | -0.33 / -0.3290 move_bp | move_bp / move_bp | 一致 |
| 236 | −0.60 | move_bp | break_dist/fam_tables.md:64 / break_dist_1/diag_paths.json d4.after_exit.15.per_trade | -0.60 / -0.5998 move_bp | move_bp / move_bp | 一致 |
| 236 | −0.24 | move_bp | break_dist/fam_tables.md:64 / break_dist_1/diag_paths.json d4.after_exit.60.per_trade | -0.24 / -0.2443 move_bp | move_bp / move_bp | 一致 |
| 236 | −0.68 | move_bp | break_dist/fam_tables.md:64 / break_dist_1/diag_paths.json d4.after_exit.60.lo | -0.68 / -0.6797 move_bp | move_bp / move_bp | 一致 |
| 236 | +0.17 | move_bp | break_dist/fam_tables.md:64 / break_dist_1/diag_paths.json d4.after_exit.60.hi | +0.17 / +0.1713 move_bp | move_bp / move_bp | 一致 |
| 236 | −0.34 | move_bp | break_dist/fam_tables.md:65 / base/diag_paths.json d4.after_exit.5.per_trade | -0.34 / -0.3353 move_bp | move_bp / move_bp | 一致 |
| 236 | −0.66 | move_bp | break_dist/fam_tables.md:65 / base/diag_paths.json d4.after_exit.15.per_trade | -0.66 / -0.6565 move_bp | move_bp / move_bp | 一致 |
| 236 | −0.42 | move_bp | break_dist/fam_tables.md:65 / base/diag_paths.json d4.after_exit.60.per_trade | -0.42 / -0.4195 move_bp | move_bp / move_bp | 一致 |
| 237 | −22 | move_bp | break_dist/fam_tables.md:49 / break_dist_0.25/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mae_median | -22.45 / -22.4460 move_bp | move_bp / move_bp | 一致 |
| 237 | −26 | move_bp | break_dist/fam_tables.md:50 / break_dist_0.25/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mae_median | -25.65 / -25.6450 move_bp | move_bp / move_bp | 一致 |
| 237 | −42 | move_bp | break_dist/fam_tables.md:53 / break_dist_1/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mae_median | -41.98 / -41.9831 move_bp | move_bp / move_bp | 一致 |
| 237 | −44 | move_bp | break_dist/fam_tables.md:54 / break_dist_1/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mae_median | -43.65 / -43.6485 move_bp | move_bp / move_bp | 一致 |
| 237 | −30 | move_bp | break_dist/fam_tables.md:57 / base/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mae_median | -30.50 / -30.4965 move_bp | move_bp / move_bp | 一致 |
| 237 | −32 | move_bp | break_dist/fam_tables.md:58 / base/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mae_median | -32.38 / -32.3832 move_bp | move_bp / move_bp | 一致 |
| 237 | −0.75 | move_bp | break_dist/fam_tables.md:63 / break_dist_0.25/diag_paths.json d4.after_exit.60.per_trade | -0.75 / -0.7492 move_bp | move_bp / move_bp | 一致 |
| 237 | −1.25 | move_bp | break_dist/fam_tables.md:63 / break_dist_0.25/diag_paths.json d4.after_exit.60.lo | -1.25 / -1.2517 move_bp | move_bp / move_bp | 一致 |
| 237 | −0.29 | move_bp | break_dist/fam_tables.md:63 / break_dist_0.25/diag_paths.json d4.after_exit.60.hi | -0.29 / -0.2919 move_bp | move_bp / move_bp | 一致 |
| 259 | −0.24 | move_bp | break_dist/fam_tables.md:71 / break_dist_0.25/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.per_trade | -0.24 / -0.2422 move_bp | move_bp / move_bp | 一致 |
| 259 | −0.30 | move_bp | break_dist/fam_tables.md:71 / break_dist_0.25/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.lo | -0.30 / -0.2989 move_bp | move_bp / move_bp | 一致 |
| 259 | −0.19 | move_bp | break_dist/fam_tables.md:71 / break_dist_0.25/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.hi | -0.19 / -0.1885 move_bp | move_bp / move_bp | 一致 |
| 259 | −0.48 | move_bp | break_dist/fam_tables.md:71 / break_dist_0.25/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.per_trade | -0.48 / -0.4836 move_bp | move_bp / move_bp | 一致 |
| 259 | −0.61 | move_bp | break_dist/fam_tables.md:71 / break_dist_0.25/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.lo | -0.61 / -0.6072 move_bp | move_bp / move_bp | 一致 |
| 259 | −0.35 | move_bp | break_dist/fam_tables.md:71 / break_dist_0.25/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.hi | -0.35 / -0.3511 move_bp | move_bp / move_bp | 一致 |
| 259 | −0.77 | move_bp | break_dist/fam_tables.md:71 / break_dist_0.25/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.per_trade | -0.77 / -0.7730 move_bp | move_bp / move_bp | 一致 |
| 259 | −1.01 | move_bp | break_dist/fam_tables.md:71 / break_dist_0.25/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.lo | -1.01 / -1.0124 move_bp | move_bp / move_bp | 一致 |
| 259 | −0.55 | move_bp | break_dist/fam_tables.md:71 / break_dist_0.25/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.hi | -0.55 / -0.5464 move_bp | move_bp / move_bp | 一致 |
| 259 | −0.80 | move_bp | break_dist/fam_tables.md:71 / break_dist_0.25/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.per_trade | -0.80 / -0.7953 move_bp | move_bp / move_bp | 一致 |
| 259 | −1.32 | move_bp | break_dist/fam_tables.md:71 / break_dist_0.25/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.lo | -1.32 / -1.3239 move_bp | move_bp / move_bp | 一致 |
| 259 | −0.34 | move_bp | break_dist/fam_tables.md:71 / break_dist_0.25/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.hi | -0.34 / -0.3438 move_bp | move_bp / move_bp | 一致 |
| 259 | +0.44 | move_bp | break_dist/fam_tables.md:71 / break_dist_0.25/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.control_24h.per_trade | +0.44 / +0.4386 move_bp | move_bp / move_bp | 一致 |
| 259 | −0.08 | move_bp | break_dist/fam_tables.md:71 / break_dist_0.25/diag_paths.json d5.建てた合図(起点 = 合図の時刻).15.control_24h.lo または d5.建てた合図(起点 = 建ての時刻).60.control_24h.lo | -0.08 / -0.0842 move_bp | move_bp / move_bp | 一致 |
| 259 | +0.95 | move_bp | break_dist/fam_tables.md:71 / break_dist_0.25/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.control_24h.hi | +0.95 / +0.9502 move_bp | move_bp / move_bp | 一致 |
| 260 | −0.24 | move_bp | break_dist/fam_tables.md:72 / break_dist_1/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.per_trade | -0.24 / -0.2388 move_bp | move_bp / move_bp | 一致 |
| 260 | −0.29 | move_bp | break_dist/fam_tables.md:72 / break_dist_1/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.lo | -0.29 / -0.2913 move_bp | move_bp / move_bp | 一致 |
| 260 | −0.19 | move_bp | break_dist/fam_tables.md:72 / break_dist_1/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.hi | -0.19 / -0.1886 move_bp | move_bp / move_bp | 一致 |
| 260 | −0.49 | move_bp | break_dist/fam_tables.md:72 / break_dist_1/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.per_trade | -0.49 / -0.4924 move_bp | move_bp / move_bp | 一致 |
| 260 | −0.60 | move_bp | break_dist/fam_tables.md:72 / break_dist_1/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.lo | -0.60 / -0.5994 move_bp | move_bp / move_bp | 一致 |
| 260 | −0.37 | move_bp | break_dist/fam_tables.md:72 / break_dist_1/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.hi | -0.37 / -0.3712 move_bp | move_bp / move_bp | 一致 |
| 260 | −0.73 | move_bp | break_dist/fam_tables.md:72 / break_dist_1/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.per_trade | -0.73 / -0.7346 move_bp | move_bp / move_bp | 一致 |
| 260 | −0.97 | move_bp | break_dist/fam_tables.md:72 / break_dist_1/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.lo | -0.97 / -0.9732 move_bp | move_bp / move_bp | 一致 |
| 260 | −0.51 | move_bp | break_dist/fam_tables.md:72 / break_dist_1/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.hi | -0.51 / -0.5058 move_bp | move_bp / move_bp | 一致 |
| 260 | −0.48 | move_bp | break_dist/fam_tables.md:72 / break_dist_1/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.per_trade | -0.48 / -0.4833 move_bp | move_bp / move_bp | 一致 |
| 260 | −0.98 | move_bp | break_dist/fam_tables.md:72 / break_dist_1/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.lo | -0.98 / -0.9833 move_bp | move_bp / move_bp | 一致 |
| 260 | −0.06 | move_bp | break_dist/fam_tables.md:72 / break_dist_1/diag_paths.json d5.建てた合図(起点 = 合図の時刻).5.control_24h.lo または d5.建てた合図(起点 = 合図の時刻).15.control_24h.lo または d5.建てた合図(起点 = 建ての時刻).60.signal.hi | -0.06 / -0.0557 move_bp | move_bp / move_bp | 一致 |
| 260 | +0.48 | move_bp | break_dist/fam_tables.md:72 / break_dist_1/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.control_24h.per_trade | +0.48 / +0.4849 move_bp | move_bp / move_bp | 一致 |
| 260 | −0.01 | move_bp | break_dist/fam_tables.md:72 / break_dist_1/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.control_24h.lo | -0.01 / -0.0088 move_bp | move_bp / move_bp | 一致 |
| 260 | +0.98 | move_bp | break_dist/fam_tables.md:72 / break_dist_1/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.control_24h.hi | +0.98 / +0.9794 move_bp | move_bp / move_bp | 一致 |
| 261 | −0.25 | move_bp | break_dist/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.per_trade | -0.25 / -0.2537 move_bp | move_bp / move_bp | 一致 |
| 261 | −0.31 | move_bp | break_dist/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.lo | -0.31 / -0.3118 move_bp | move_bp / move_bp | 一致 |
| 261 | −0.20 | move_bp | break_dist/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.hi | -0.20 / -0.1989 move_bp | move_bp / move_bp | 一致 |
| 261 | −0.51 | move_bp | break_dist/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.per_trade | -0.51 / -0.5080 move_bp | move_bp / move_bp | 一致 |
| 261 | −0.63 | move_bp | break_dist/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.lo | -0.63 / -0.6269 move_bp | move_bp / move_bp | 一致 |
| 261 | −0.38 | move_bp | break_dist/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.hi | -0.38 / -0.3795 move_bp | move_bp / move_bp | 一致 |
| 261 | −0.74 | move_bp | break_dist/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.per_trade | -0.74 / -0.7434 move_bp | move_bp / move_bp | 一致 |
| 261 | −0.98 | move_bp | break_dist/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.lo | -0.98 / -0.9791 move_bp | move_bp / move_bp | 一致 |
| 261 | −0.52 | move_bp | break_dist/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.hi | -0.52 / -0.5232 move_bp | move_bp / move_bp | 一致 |
| 261 | −0.58 | move_bp | break_dist/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.per_trade | -0.58 / -0.5757 move_bp | move_bp / move_bp | 一致 |
| 261 | −1.10 | move_bp | break_dist/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.lo | -1.10 / -1.0953 move_bp | move_bp / move_bp | 一致 |
| 261 | −0.13 | move_bp | break_dist/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.hi | -0.13 / -0.1296 move_bp | move_bp / move_bp | 一致 |
| 261 | +0.53 | move_bp | break_dist/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.control_24h.per_trade | +0.53 / +0.5252 move_bp | move_bp / move_bp | 一致 |
| 261 | +0.03 | move_bp | break_dist/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 合図の時刻).5.control_24h.per_trade または d5.建てた合図(起点 = 建ての時刻).1.control_24h.per_trade または d5.建てた合図(起点 = 建ての時刻).60.control_24h.lo | +0.03 / +0.0305 move_bp | move_bp / move_bp | 一致 |
| 261 | +1.03 | move_bp | break_dist/fam_tables.md:73 / base/diag_paths.json d5.建てた合図(起点 = 合図の時刻).60.control_24h.hi または d5.建てた合図(起点 = 建ての時刻).60.control_24h.hi | +1.03 / +1.0279 move_bp | move_bp / move_bp | 一致 |
| 280 | +2.9 | 円 | break_dist/fam_tables.md:77 / break_dist_0.25/diag_tables.json d6.groups.〜1 分.per_trade | +2.9 / +0.1440 bp(× 20 = +2.88 円) | 円 / bp | 一致 |
| 280 | +1.9 | 円 | break_dist/fam_tables.md:77 / break_dist_0.25/diag_tables.json d6.groups.〜1 分.lo | +1.9 / +0.0964 bp(× 20 = +1.93 円) | 円 / bp | 一致 |
| 280 | +3.8 | 円 | break_dist/fam_tables.md:77 / break_dist_0.25/diag_tables.json d6.groups.〜1 分.hi | +3.8 / +0.1904 bp(× 20 = +3.81 円) | 円 / bp | 一致 |
| 280 | −0.1 | 円 | break_dist/fam_tables.md:77 / break_dist_0.25/diag_tables.json d6.groups.1 分超〜3 分.per_trade | -0.1 / -0.0027 bp(× 20 = -0.05 円) | 円 / bp | 一致 |
| 280 | −1.5 | 円 | break_dist/fam_tables.md:77 / break_dist_0.25/diag_tables.json d6.groups.1 分超〜3 分.lo または d6.groups.3 分超〜13 分.per_trade | -1.5 / -0.0736 bp(× 20 = -1.47 円) | 円 / bp | 一致 |
| 280 | −2.6 | 円 | break_dist/fam_tables.md:77 / break_dist_0.25/diag_tables.json d6.groups.3 分超〜13 分.lo | -2.6 / -0.1292 bp(× 20 = -2.58 円) | 円 / bp | 一致 |
| 280 | −0.4 | 円 | break_dist/fam_tables.md:77 / break_dist_0.25/diag_tables.json d6.groups.13 分超.lo または d6.groups.3 分超〜13 分.hi | -0.4 / -0.0179 bp(× 20 = -0.36 円) | 円 / bp | 一致 |
| 280 | +1.0 | 円 | break_dist/fam_tables.md:77 / break_dist_0.25/diag_tables.json d6.groups.13 分超.per_trade | 1 / +0.0484 bp(× 20 = +0.97 円) | 円 / bp | 一致 |
| 280 | −0.4 | 円 | break_dist/fam_tables.md:77 / break_dist_0.25/diag_tables.json d6.groups.13 分超.lo または d6.groups.3 分超〜13 分.hi | -0.4 / -0.0179 bp(× 20 = -0.36 円) | 円 / bp | 一致 |
| 280 | +2.2 | 円 | break_dist/fam_tables.md:77 / break_dist_0.25/diag_tables.json d6.groups.13 分超.hi | +2.2 / +0.1099 bp(× 20 = +2.20 円) | 円 / bp | 一致 |
| 281 | +2.4 | 円 | break_dist/fam_tables.md:78 / break_dist_1/diag_tables.json d6.groups.〜1 分.per_trade | +2.4 / +0.1183 bp(× 20 = +2.37 円) | 円 / bp | 一致 |
| 281 | +1.3 | 円 | break_dist/fam_tables.md:78 / break_dist_1/diag_tables.json d6.groups.〜1 分.lo | +1.3 / +0.0631 bp(× 20 = +1.26 円) | 円 / bp | 一致 |
| 281 | +3.4 | 円 | break_dist/fam_tables.md:78 / break_dist_1/diag_tables.json d6.groups.〜1 分.hi | +3.4 / +0.1711 bp(× 20 = +3.42 円) | 円 / bp | 一致 |
| 281 | +0.3 | 円 | break_dist/fam_tables.md:78 / break_dist_1/diag_tables.json d6.groups.1 分超〜2 分.per_trade または d6.groups.9 分超.per_trade | +0.3 / +0.0142 bp(× 20 = +0.28 円) | 円 / bp | 一致 |
| 281 | −1.4 | 円 | break_dist/fam_tables.md:78 / break_dist_1/diag_tables.json d6.groups.2 分超〜9 分.per_trade | -1.4 / -0.0692 bp(× 20 = -1.38 円) | 円 / bp | 一致 |
| 281 | −2.8 | 円 | break_dist/fam_tables.md:78 / break_dist_1/diag_tables.json d6.groups.2 分超〜9 分.lo | -2.8 / -0.1413 bp(× 20 = -2.83 円) | 円 / bp | 一致 |
| 281 | −0.1 | 円 | break_dist/fam_tables.md:78 / break_dist_1/diag_tables.json d6.groups.2 分超〜9 分.hi | -0.1 / -0.0037 bp(× 20 = -0.07 円) | 円 / bp | 一致 |
| 281 | +0.3 | 円 | break_dist/fam_tables.md:78 / break_dist_1/diag_tables.json d6.groups.1 分超〜2 分.per_trade または d6.groups.9 分超.per_trade | +0.3 / +0.0142 bp(× 20 = +0.28 円) | 円 / bp | 一致 |
| 282 | +2.4 | 円 | break_dist/fam_tables.md:79 / base/diag_tables.json d6.groups.〜1 分.per_trade | +2.4 / +0.1180 bp(× 20 = +2.36 円) | 円 / bp | 一致 |
| 282 | +1.3 | 円 | break_dist/fam_tables.md:79 / base/diag_tables.json d6.groups.〜1 分.lo | +1.3 / +0.0674 bp(× 20 = +1.35 円) | 円 / bp | 一致 |
| 282 | +3.3 | 円 | break_dist/fam_tables.md:79 / base/diag_tables.json d6.groups.〜1 分.hi | +3.3 / +0.1673 bp(× 20 = +3.35 円) | 円 / bp | 一致 |
| 282 | −2.0 | 円 | break_dist/fam_tables.md:79 / base/diag_tables.json d6.groups.3 分超〜11 分.per_trade | -2.0 / -0.1001 bp(× 20 = -2.00 円) | 円 / bp | 一致 |
| 282 | −3.2 | 円 | break_dist/fam_tables.md:79 / base/diag_tables.json d6.groups.3 分超〜11 分.lo | -3.2 / -0.1618 bp(× 20 = -3.24 円) | 円 / bp | 一致 |
| 282 | −0.8 | 円 | break_dist/fam_tables.md:79 / base/diag_tables.json d6.groups.3 分超〜11 分.hi | -0.8 / -0.0400 bp(× 20 = -0.80 円) | 円 / bp | 一致 |
| 304 | +47.1 | 円 | break_dist/fam_tables.md:85 / break_dist_0.25/diag_tables.json d7.all.mean | +47.1 / +2.3555 bp(× 20 = +47.11 円) | 円 / bp | 一致 |
| 304 | −0.1 | 円 | break_dist/fam_tables.md:85 / break_dist_0.25/diag_tables.json d7.all.lo | -0.1 / -0.0061 bp(× 20 = -0.12 円) | 円 / bp | 一致 |
| 304 | +94.6 | 円 | break_dist/fam_tables.md:85 / break_dist_0.25/diag_tables.json d7.all.hi | +94.6 / +4.7302 bp(× 20 = +94.60 円) | 円 / bp | 一致 |
| 304 | 68.8 | 円 | break_dist/fam_tables.md:85 / break_dist_0.25/diag_tables.json d7.all.mde | +68.8 / +3.4421 bp(× 20 = +68.84 円) | 円 / bp | 一致 |
| 304 | +46.9 | 円 | break_dist/fam_tables.md:86 / break_dist_1/diag_tables.json d7.all.mean | +46.9 / +2.3463 bp(× 20 = +46.93 円) | 円 / bp | 一致 |
| 304 | −23.8 | 円 | break_dist/fam_tables.md:86 / break_dist_1/diag_tables.json d7.all.lo | -23.8 / -1.1902 bp(× 20 = -23.80 円) | 円 / bp | 一致 |
| 304 | +107.0 | 円 | break_dist/fam_tables.md:86 / break_dist_1/diag_tables.json d7.all.hi | +107.0 / +5.3518 bp(× 20 = +107.04 円) | 円 / bp | 一致 |
| 304 | 93.0 | 円 | break_dist/fam_tables.md:86 / break_dist_1/diag_tables.json d7.all.mde | +93.0 / +4.6495 bp(× 20 = +92.99 円) | 円 / bp | 一致 |
| 305 | −17 | 円 | break_dist/fam_tables.md:85 | -17 | 円 | 一致 |
| 305 | −94 | 円 | break_dist/fam_tables.md:85 | -94 | 円 | 一致 |
| 305 | +61 | 円 | break_dist/fam_tables.md:85 | +61 | 円 | 一致 |
| 305 | 109 | 円 | break_dist/fam_tables.md:85 / break_dist_0.25/diag_tables.json d7.years.2016.hi | +109 / +5.4424 bp(× 20 = +108.85 円) | 円 / bp | 一致 |
| 305 | +110 | 円 | break_dist/fam_tables.md:86 | +110 | 円 | 一致 |
| 305 | +19 | 円 | break_dist/fam_tables.md:86 | +19 | 円 | 一致 |
| 305 | +213 | 円 | break_dist/fam_tables.md:86 | +213 | 円 | 一致 |
| 305 | 144 | 円 | break_dist/fam_tables.md:86 | +144 | 円 | 一致 |
| 306 | +111 | 円 | break_dist/fam_tables.md:85 / break_dist_0.25/diag_tables.json d7.years.2023.mean | +111 / +5.5555 bp(× 20 = +111.11 円) | 円 / bp | 一致 |
| 306 | +54 | 円 | break_dist/fam_tables.md:85 | +54 | 円 | 一致 |
| 306 | +174 | 円 | break_dist/fam_tables.md:85 | +174 | 円 | 一致 |
| 306 | 84 | 円 | break_dist/fam_tables.md:85 | +84 | 円 | 一致 |
| 306 | −16 | 円 | break_dist/fam_tables.md:86 | -16 | 円 | 一致 |
| 306 | −96 | 円 | break_dist/fam_tables.md:86 | -96 | 円 | 一致 |
| 306 | +58 | 円 | break_dist/fam_tables.md:86 | +58 | 円 | 一致 |
| 306 | 110 | 円 | break_dist/fam_tables.md:86 | +110 | 円 | 一致 |
| 312 | +196 | 円 | break_dist/fam_tables.md:92 / break_dist_0.25/diag_tables.json d7.years.2015.mean | +196 / +9.8089 bp(× 20 = +196.18 円) | 円 / bp | 一致 |
| 312 | +17 | 円 | break_dist/fam_tables.md:92 / break_dist_0.25/diag_tables.json d7.years.2016.mean | +17 / +0.8322 bp(× 20 = +16.64 円) | 円 / bp | 一致 |
| 312 | +33 | 円 | break_dist/fam_tables.md:92 / break_dist_0.25/diag_tables.json d7.years.2017.mean | +33 / +1.6650 bp(× 20 = +33.30 円) | 円 / bp | 一致 |
| 312 | −175 | 円 | break_dist/fam_tables.md:92 / break_dist_0.25/diag_tables.json d7.years.2018.mean | -175 / -8.7607 bp(× 20 = -175.21 円) | 円 / bp | 一致 |
| 312 | +49 | 円 | break_dist/fam_tables.md:92 / break_dist_0.25/diag_tables.json d7.years.2019.mean | +49 / +2.4380 bp(× 20 = +48.76 円) | 円 / bp | 一致 |
| 312 | +73 | 円 | break_dist/fam_tables.md:92 / break_dist_0.25/diag_tables.json d7.years.2020.mean | +73 / +3.6640 bp(× 20 = +73.28 円) | 円 / bp | 一致 |
| 312 | +179 | 円 | break_dist/fam_tables.md:92 / break_dist_0.25/diag_tables.json d7.years.2021.mean | +179 / +8.9619 bp(× 20 = +179.24 円) | 円 / bp | 一致 |
| 312 | +80 | 円 | break_dist/fam_tables.md:92 / break_dist_0.25/diag_tables.json d7.years.2022.mean | +80 / +3.9781 bp(× 20 = +79.56 円) | 円 / bp | 一致 |
| 312 | +111 | 円 | break_dist/fam_tables.md:92 / break_dist_0.25/diag_tables.json d7.years.2023.mean | +111 / +5.5555 bp(× 20 = +111.11 円) | 円 / bp | 一致 |
| 313 | −397 | 円 | break_dist/fam_tables.md:93 / break_dist_1/diag_tables.json d7.years.2015.mean | -397 / -19.8485 bp(× 20 = -396.97 円) | 円 / bp | 一致 |
| 313 | −1 | 円 | break_dist/fam_tables.md:93 / break_dist_1/diag_tables.json d7.years.2016.mean | -1 / -0.0425 bp(× 20 = -0.85 円) | 円 / bp | 一致 |
| 313 | +258 | 円 | break_dist/fam_tables.md:93 / break_dist_1/diag_tables.json d7.years.2017.mean | +258 / +12.9041 bp(× 20 = +258.08 円) | 円 / bp | 一致 |
| 313 | +49 | 円 | break_dist/fam_tables.md:93 / break_dist_1/diag_tables.json d7.years.2018.mean | +49 / +2.4436 bp(× 20 = +48.87 円) | 円 / bp | 一致 |
| 313 | +182 | 円 | break_dist/fam_tables.md:93 / break_dist_1/diag_tables.json d7.years.2019.mean | +182 / +9.0950 bp(× 20 = +181.90 円) | 円 / bp | 一致 |
| 313 | +140 | 円 | break_dist/fam_tables.md:93 / break_dist_1/diag_tables.json d7.years.2020.mean | +140 / +6.9999 bp(× 20 = +140.00 円) | 円 / bp | 一致 |
| 313 | −75 | 円 | break_dist/fam_tables.md:93 / break_dist_1/diag_tables.json d7.years.2021.mean | -75 / -3.7536 bp(× 20 = -75.07 円) | 円 / bp | 一致 |
| 313 | −60 | 円 | break_dist/fam_tables.md:93 / break_dist_1/diag_tables.json d7.years.2022.mean | -60 / -3.0227 bp(× 20 = -60.45 円) | 円 / bp | 一致 |
| 313 | −85 | 円 | break_dist/fam_tables.md:93 / break_dist_1/diag_tables.json d7.years.2023.mean | -85 / -4.2269 bp(× 20 = -84.54 円) | 円 / bp | 一致 |
| 319 | +87,963 | 円 | break_dist/fam_tables.md:99 / break_dist_0.25/diag_tables.json d7.match.sum_both_a_minus_b | +87,963 / +4398.1280 bp(× 20 = +87962.56 円) | 円 / bp | 一致 |
| 319 | −139 | 円 | break_dist/fam_tables.md:99 / break_dist_0.25/diag_tables.json d7.match.sum_only_a | -139 / -6.9506 bp(× 20 = -139.01 円) | 円 / bp | 一致 |
| 319 | −50,631 | 円 | break_dist/fam_tables.md:99 / break_dist_0.25/diag_tables.json d7.match.sum_only_b | -50,631 / -2531.5639 bp(× 20 = -50631.28 円) | 円 / bp | 一致 |
| 320 | +151,483 | 円 | break_dist/fam_tables.md:100 / break_dist_1/diag_tables.json d7.match.sum_both_a_minus_b | +151,483 / +7574.1414 bp(× 20 = +151482.83 円) | 円 / bp | 一致 |
| 320 | −24,296 | 円 | break_dist/fam_tables.md:100 / break_dist_1/diag_tables.json d7.match.sum_only_a | -24,296 / -1214.7753 bp(× 20 = -24295.51 円) | 円 / bp | 一致 |
| 320 | −10,728 | 円 | break_dist/fam_tables.md:100 / break_dist_1/diag_tables.json d7.match.sum_only_b | -10,728 / -536.3869 bp(× 20 = -10727.74 円) | 円 / bp | 一致 |
| 322 | +111 | 円 | break_dist/fam_tables.md:85 / break_dist_0.25/diag_tables.json d7.years.2023.mean | +111 / +5.5555 bp(× 20 = +111.11 円) | 円 / bp | 一致 |
| 322 | +54 | 円 | break_dist/fam_tables.md:85 | +54 | 円 | 一致 |
| 322 | +174 | 円 | break_dist/fam_tables.md:85 | +174 | 円 | 一致 |
| 322 | +110 | 円 | break_dist/fam_tables.md:86 | +110 | 円 | 一致 |
| 322 | +19 | 円 | break_dist/fam_tables.md:86 | +19 | 円 | 一致 |
| 322 | +213 | 円 | break_dist/fam_tables.md:86 | +213 | 円 | 一致 |
| 322 | +47 | 円 | break_dist/fam_tables.md:85 / break_dist_0.25/diag_tables.json d7.all.mean | +47.1 / +2.3555 bp(× 20 = +47.11 円) | 円 / bp | 一致 |
| 323 | −17 | 円 | break_dist/fam_tables.md:85 | -17 | 円 | 一致 |
| 323 | −132 | 円 | break_dist/fam_tables.md:31・35 | +197 − (+329) = −132 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 323 | +329 | 円 | break_dist/fam_tables.md:35 | +329 | 円 | 一致 |
| 323 | +197 | 円 | break_dist/fam_tables.md:31 | +197 | 円 | 一致 |
| 323 | +115 | 円 | break_dist/fam_tables.md:32・36 | +148 − (+33) = +115 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 323 | +33 | 円 | break_dist/fam_tables.md:36 | +33 | 円 | 一致 |
| 323 | +148 | 円 | break_dist/fam_tables.md:32 | +148 | 円 | 一致 |
| 323 | +111 | 円 | break_dist/fam_tables.md:85 / break_dist_0.25/diag_tables.json d7.years.2023.mean | +111 / +5.5555 bp(× 20 = +111.11 円) | 円 / bp | 一致 |
| 323 | −93 | 円 | break_dist/fam_tables.md:31・35 | +24 − (+117) = −93 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 323 | +205 | 円 | break_dist/fam_tables.md:32・36 | −185 − (−390) = +205 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 323 | +110 | 円 | break_dist/fam_tables.md:86 | +110 | 円 | 一致 |
| 323 | +253 | 円 | break_dist/fam_tables.md:33・35 | +582 − (+329) = +253 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 323 | −143 | 円 | break_dist/fam_tables.md:34・36 | −110 − (+33) = −143 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 323 | −16 | 円 | break_dist/fam_tables.md:86 | -16 | 円 | 一致 |
| 323 | +190 | 円 | break_dist/fam_tables.md:33・35 | +307 − (+117) = +190 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 323 | −206 | 円 | break_dist/fam_tables.md:34・36 | −596 − (−390) = −206 | 円(計算) | 一致(計算値: 帯の 1 日あたりの差。表示の値の差) |
| 328 | +10.9 | 円 | break_dist/band_migration.out:6(和 ÷ 本数・和の差 ÷ 日数を計算) | +10.87 | 円(計算) | 一致 |
| 328 | +14.6 | 円 | break_dist/band_migration.out:6(和 ÷ 本数・和の差 ÷ 日数を計算) | +14.59 | 円(計算) | 一致 |
| 328 | +108 | 円 | break_dist/band_migration.out:6(和 ÷ 本数・和の差 ÷ 日数を計算) | +108.05 | 円(計算) | 一致 |
| 329 | −31.9 | 円 | break_dist/band_migration.out:9(和 ÷ 本数・和の差 ÷ 日数を計算) | -31.87 | 円(計算) | 一致 |
| 329 | −64.7 | 円 | break_dist/band_migration.out:9(和 ÷ 本数・和の差 ÷ 日数を計算) | -64.74 | 円(計算) | 一致 |
| 329 | −115 | 円 | break_dist/band_migration.out:9(和 ÷ 本数・和の差 ÷ 日数を計算) | -114.94 | 円(計算) | 一致 |
| 330 | +2.2 | 円 | break_dist/band_migration.out:10(和 ÷ 本数・和の差 ÷ 日数を計算) | +2.15 | 円(計算) | 一致 |
| 330 | +2.0 | 円 | break_dist/band_migration.out:10(和 ÷ 本数・和の差 ÷ 日数を計算) | +1.98 | 円(計算) | 一致 |
| 330 | −13 | 円 | break_dist/band_migration.out:10(和 ÷ 本数・和の差 ÷ 日数を計算) | -12.67 | 円(計算) | 一致 |
| 331 | +4.4 | 円 | break_dist/band_migration.out:5(和 ÷ 本数・和の差 ÷ 日数を計算) | +4.44 | 円(計算) | 一致 |
| 331 | −2.0 | 円 | break_dist/band_migration.out:8(和 ÷ 本数・和の差 ÷ 日数を計算) | -2.03 | 円(計算) | 一致 |
| 331 | −19 | 円 | break_dist/band_migration.out:5(和 ÷ 本数・和の差 ÷ 日数を計算) | -18.59 | 円(計算) | 一致 |
| 331 | +17 | 円 | break_dist/band_migration.out:8(和 ÷ 本数・和の差 ÷ 日数を計算) | +16.50 | 円(計算) | 一致 |
| 332 | +5.0 | 円 | break_dist/band_migration.out:14 | +172,455 ÷ 34,817 = +4.95 | 円(計算) | 一致(計算値) |
| 332 | +9.2 | 円 | break_dist/band_migration.out:14(和 ÷ 本数・和の差 ÷ 日数を計算) | +9.21 | 円(計算) | 一致 |
| 332 | +101 | 円 | break_dist/band_migration.out:14(和 ÷ 本数・和の差 ÷ 日数を計算) | +100.90 | 円(計算) | 一致 |
| 333 | −37.6 | 円 | break_dist/band_migration.out:17(和 ÷ 本数・和の差 ÷ 日数を計算) | -37.64 | 円(計算) | 一致 |
| 333 | −55.6 | 円 | break_dist/band_migration.out:17(和 ÷ 本数・和の差 ÷ 日数を計算) | -55.56 | 円(計算) | 一致 |
| 333 | −63 | 円 | break_dist/band_migration.out:17(和 ÷ 本数・和の差 ÷ 日数を計算) | -62.83 | 円(計算) | 一致 |
| 334 | −2.8 | 円 | break_dist/band_migration.out:18(和 ÷ 本数・和の差 ÷ 日数を計算) | -2.78 | 円(計算) | 一致 |
| 334 | −2.3 | 円 | break_dist/band_migration.out:18(和 ÷ 本数・和の差 ÷ 日数を計算) | -2.35 | 円(計算) | 一致 |
| 334 | +34 | 円 | break_dist/band_migration.out:18(和 ÷ 本数・和の差 ÷ 日数を計算) | +33.59 | 円(計算) | 一致 |
| 335 | +1.2 | 円 | break_dist/band_migration.out:13(和 ÷ 本数・和の差 ÷ 日数を計算) | +1.23 | 円(計算) | 一致 |
| 335 | −4.8 | 円 | break_dist/band_migration.out:16(和 ÷ 本数・和の差 ÷ 日数を計算) | -4.80 | 円(計算) | 一致 |
| 335 | −4 | 円 | break_dist/band_migration.out:13(和 ÷ 本数・和の差 ÷ 日数を計算) | -4.36 | 円(計算) | 一致 |
| 335 | +41 | 円 | break_dist/band_migration.out:16(和 ÷ 本数・和の差 ÷ 日数を計算) | +40.89 | 円(計算) | 一致 |
| 336 | +20.3 | 円 | break_dist/band_migration.out:22(和 ÷ 本数・和の差 ÷ 日数を計算) | +20.27 | 円(計算) | 一致 |
| 336 | +17.9 | 円 | break_dist/band_migration.out:22(和 ÷ 本数・和の差 ÷ 日数を計算) | +17.90 | 円(計算) | 一致 |
| 336 | −72 | 円 | break_dist/band_migration.out:22(和 ÷ 本数・和の差 ÷ 日数を計算) | -72.03 | 円(計算) | 一致 |
| 337 | −112.5 | 円 | break_dist/band_migration.out:23(和 ÷ 本数・和の差 ÷ 日数を計算) | -112.46 | 円(計算) | 一致 |
| 337 | −73.8 | 円 | break_dist/band_migration.out:23(和 ÷ 本数・和の差 ÷ 日数を計算) | -73.78 | 円(計算) | 一致 |
| 337 | +99 | 円 | break_dist/band_migration.out:23(和 ÷ 本数・和の差 ÷ 日数を計算) | +99.31 | 円(計算) | 一致 |
| 338 | +0.5 | 円 | break_dist/band_migration.out:26(和 ÷ 本数・和の差 ÷ 日数を計算) | +0.50 | 円(計算) | 一致 |
| 338 | +1.5 | 円 | break_dist/band_migration.out:11(和 ÷ 本数・和の差 ÷ 日数を計算) | +1.52 | 円(計算) | 一致 |
| 338 | +83 | 円 | break_dist/band_migration.out:26(和 ÷ 本数・和の差 ÷ 日数を計算) | +82.89 | 円(計算) | 一致 |
| 339 | +14.1 | 円 | break_dist/band_migration.out:19(和 ÷ 本数・和の差 ÷ 日数を計算) | +14.06 | 円(計算) | 一致 |
| 339 | −5.3 | 円 | break_dist/band_migration.out:20(和 ÷ 本数・和の差 ÷ 日数を計算) | -5.27 | 円(計算) | 一致 |
| 339 | +53 | 円 | break_dist/band_migration.out:19(和 ÷ 本数・和の差 ÷ 日数を計算) | +52.99 | 円(計算) | 一致 |
| 339 | −46 | 円 | break_dist/band_migration.out:20(和 ÷ 本数・和の差 ÷ 日数を計算) | -45.96 | 円(計算) | 一致 |
| 340 | +14.5 | 円 | break_dist/band_migration.out:30(和 ÷ 本数・和の差 ÷ 日数を計算) | +14.51 | 円(計算) | 一致 |
| 340 | +12.2 | 円 | break_dist/band_migration.out:30(和 ÷ 本数・和の差 ÷ 日数を計算) | +12.21 | 円(計算) | 一致 |
| 340 | −57 | 円 | break_dist/band_migration.out:30(和 ÷ 本数・和の差 ÷ 日数を計算) | -56.96 | 円(計算) | 一致 |
| 341 | −100.9 | 円 | break_dist/band_migration.out:31(和 ÷ 本数・和の差 ÷ 日数を計算) | -100.90 | 円(計算) | 一致 |
| 341 | −72.2 | 円 | break_dist/band_migration.out:31(和 ÷ 本数・和の差 ÷ 日数を計算) | -72.16 | 円(計算) | 一致 |
| 341 | +69 | 円 | break_dist/band_migration.out:31(和 ÷ 本数・和の差 ÷ 日数を計算) | +68.86 | 円(計算) | 一致 |
| 342 | −4.2 | 円 | break_dist/band_migration.out:34(和 ÷ 本数・和の差 ÷ 日数を計算) | -4.19 | 円(計算) | 一致 |
| 342 | −4.2 | 円 | break_dist/band_migration.out:34(和 ÷ 本数・和の差 ÷ 日数を計算) | -4.19 | 円(計算) | 一致 |
| 342 | −3 | 円 | break_dist/band_migration.out:34 | -3 | 円 | 一致 |
| 343 | +7.5 | 円 | break_dist/band_migration.out:27(和 ÷ 本数・和の差 ÷ 日数を計算) | +7.52 | 円(計算) | 一致 |
| 343 | −5.2 | 円 | break_dist/band_migration.out:28(和 ÷ 本数・和の差 ÷ 日数を計算) | -5.18 | 円(計算) | 一致 |
| 343 | +22 | 円 | break_dist/band_migration.out:27 | +22 | 円 | 一致 |
| 343 | −46 | 円 | break_dist/band_migration.out:20(和 ÷ 本数・和の差 ÷ 日数を計算) | -45.96 | 円(計算) | 一致 |
| 345 | −17 | 円 | 和(和 ÷ 本数・和の差 ÷ 日数を計算) | -16.84 | 円(計算) | 一致 |
| 345 | +112 | 円 | break_dist/band_migration.out:11-18 | 後半 8 升目: 本の和 −237,631 − 基準の和 −400,821 = +163,190 円 ÷ 1,470 = +111.01 | 円(計算) | 値の誤り(丸めで最後の桁が違う。升目の差の和を和から計算すると +111.0。文書の +112 は表示した升目の丸めた値(−0・+0・−4・+101・+3・+41・−63・+34)を足した値) |
| 345 | +110 | 円 | 和(和 ÷ 本数・和の差 ÷ 日数を計算) | +110.09 | 円(計算) | 一致 |
| 345 | −16 | 円 | 和(和 ÷ 本数・和の差 ÷ 日数を計算) | -16.20 | 円(計算) | 一致 |
| 346 | −143.5 | 円 | break_dist/same_bar_reason_break_dist_0.25.out:1 | -143.5 | 円 | 一致 |
| 346 | −81.3 | 円 | break_dist/same_bar_reason_break_dist_0.25.out:1 | -81.3 | 円 | 一致 |
| 346 | −131.2 | 円 | break_dist/same_bar_reason_break_dist_0.25.out:5 | -131.2 | 円 | 一致 |
| 346 | −73.3 | 円 | break_dist/same_bar_reason_break_dist_0.25.out:5 | -73.3 | 円 | 一致 |
| 346 | +148 | 円 | break_dist/same_bar_reason_break_dist_0.25.out:1 | +148.4 | 円 | 一致 |
| 346 | +129 | 円 | break_dist/same_bar_reason_break_dist_0.25.out:5 | +128.7 | 円 | 一致 |
| 346 | −42 | 円 | break_dist/same_bar_reason_break_dist_0.25.out:3 | -41.5 | 円 | 一致 |
| 346 | −29 | 円 | break_dist/same_bar_reason_break_dist_0.25.out:7 | -29.2 | 円 | 一致 |
| 346 | +0 | 円 | break_dist/same_bar_reason_break_dist_0.25.out:4 | +0.0 | 円 | 一致 |
| 346 | +0 | 円 | break_dist/same_bar_reason_break_dist_0.25.out:4 | +0.0 | 円 | 一致 |
| 346 | +1,589 | 円 | break_dist/held_reason_break_dist_1.out:2 | +1588.6 | 円 | 一致 |
| 346 | +1,402 | 円 | break_dist/held_reason_break_dist_1.out:9 | +1401.6 | 円 | 一致 |
| 346 | −335.2 | 円 | break_dist/held_reason_break_dist_1.out:1 | -335.2 | 円 | 一致 |
| 346 | −670.7 | 円 | break_dist/held_reason_break_dist_1.out:1 | -670.7 | 円 | 一致 |
| 346 | −274.9 | 円 | break_dist/held_reason_break_dist_1.out:8 | -274.9 | 円 | 一致 |
| 346 | −548.6 | 円 | break_dist/held_reason_break_dist_1.out:8 | -548.6 | 円 | 一致 |
| 346 | −1,426 | 円 | break_dist/held_reason_break_dist_1.out:1 | -1426.0 | 円 | 一致 |
| 346 | −1,324 | 円 | break_dist/held_reason_break_dist_1.out:8 | -1324.0 | 円 | 一致 |
| 346 | +83 | 円 | break_dist/band_migration.out:26 | +83 | 円 | 一致 |
| 346 | −3 | 円 | break_dist/band_migration.out:34 | -3 | 円 | 一致 |
| 346 | −6 | 円 | break_dist/held_reason_break_dist_1.out:5 | diff/day -6.4 | 円 | 一致 |
| 346 | −4 | 円 | break_dist/held_reason_break_dist_1.out:12 | -4.3 | 円 | 一致 |
| 346 | ±1,300〜1,600 | 円 | break_dist/held_reason_break_dist_1.out:1・2・8・9 | −1,426.0・+1,588.6・−1,324.0・+1,401.6 | 円 | 一致(丸めた範囲(1,324〜1,589)) |
| 347 | +108 | 円 | break_dist/band_migration.out:6 | +108 | 円 | 一致 |
| 347 | +101 | 円 | break_dist/band_migration.out:14 | +101 | 円 | 一致 |
| 347 | +148 | 円 | break_dist/same_bar_reason_break_dist_0.25.out:1 | +148.4 | 円 | 一致 |
| 347 | +129 | 円 | break_dist/same_bar_reason_break_dist_0.25.out:5 | +128.7 | 円 | 一致 |
| 347 | −115 | 円 | break_dist/band_migration.out:9 | -115 | 円 | 一致 |
| 347 | −63 | 円 | break_dist/band_migration.out:17 | -63 | 円 | 一致 |
| 347 | −13 | 円 | break_dist/band_migration.out:10 | -13 | 円 | 一致 |
| 347 | +34 | 円 | break_dist/band_migration.out:18 | +34 | 円 | 一致 |
| 347 | +99 | 円 | break_dist/band_migration.out:23 | +99 | 円 | 一致 |
| 347 | +69 | 円 | break_dist/band_migration.out:31 | +69 | 円 | 一致 |
| 347 | −72 | 円 | break_dist/band_migration.out:22 | -72 | 円 | 一致 |
| 347 | −57 | 円 | break_dist/band_migration.out:30 | -57 | 円 | 一致 |
| 347 | +83 | 円 | break_dist/band_migration.out:26 | +83 | 円 | 一致 |
| 347 | −3 | 円 | break_dist/band_migration.out:34 | -3 | 円 | 一致 |
| 347 | ±1,300〜1,600 | 円 | break_dist/held_reason_break_dist_1.out:1・2・8・9 | −1,426.0・+1,588.6・−1,324.0・+1,401.6 | 円 | 一致(丸めた範囲(1,324〜1,589)) |
| 348 | −50,631 | 円 | break_dist/fam_tables.md:99 / break_dist_0.25/diag_tables.json d7.match.sum_only_b | -50,631 / -2531.5639 bp(× 20 = -50631.28 円) | 円 / bp | 一致 |
| 348 | −24,296 | 円 | break_dist/fam_tables.md:100 / break_dist_1/diag_tables.json d7.match.sum_only_a | -24,296 / -1214.7753 bp(× 20 = -24295.51 円) | 円 / bp | 一致 |
| 348 | +87,963 | 円 | break_dist/fam_tables.md:99 / break_dist_0.25/diag_tables.json d7.match.sum_both_a_minus_b | +87,963 / +4398.1280 bp(× 20 = +87962.56 円) | 円 / bp | 一致 |
| 348 | +151,483 | 円 | break_dist/fam_tables.md:100 / break_dist_1/diag_tables.json d7.match.sum_both_a_minus_b | +151,483 / +7574.1414 bp(× 20 = +151482.83 円) | 円 / bp | 一致 |
| 364 | −13 | 円 | break_dist/band_migration.out:10 | -13 | 円 | 一致 |
| 364 | +197 | 円 | break_dist/fam_tables.md:31 | +197 | 円 | 一致 |
| 364 | +582 | 円 | break_dist/fam_tables.md:33 | +582 | 円 | 一致 |
| 365 | −99 | 円 | step/band_migration.out:8 | -99 | 円 | 一致 |
| 365 | −238 | 円 | step/band_migration.out:20 | -238 | 円 | 一致 |
| 397 | +111 | 円 | break_dist/fam_tables.md:85 / break_dist_0.25/diag_tables.json d7.years.2023.mean | +111 / +5.5555 bp(× 20 = +111.11 円) | 円 / bp | 一致 |
| 397 | +110 | 円 | break_dist/fam_tables.md:86 | +110 | 円 | 一致 |
| 397 | +108 | 円 | break_dist/band_migration.out:6 | +108 | 円 | 一致 |
| 397 | +101 | 円 | break_dist/band_migration.out:14 | +101 | 円 | 一致 |
| 397 | −115 | 円 | break_dist/band_migration.out:9 | -115 | 円 | 一致 |
| 397 | −63 | 円 | break_dist/band_migration.out:17 | -63 | 円 | 一致 |
| 397 | +99 | 円 | break_dist/band_migration.out:23 | +99 | 円 | 一致 |
| 397 | +69 | 円 | break_dist/band_migration.out:31 | +69 | 円 | 一致 |
| 397 | +83 | 円 | break_dist/band_migration.out:26 | +83 | 円 | 一致 |
| 397 | −3 | 円 | break_dist/band_migration.out:34 | -3 | 円 | 一致 |
| 397 | −13 | 円 | break_dist/band_migration.out:10 | -13 | 円 | 一致 |
| 397 | +34 | 円 | break_dist/band_migration.out:18 | +34 | 円 | 一致 |
| 397 | ±1,200〜1,600 | 円 | break_dist/held_reason_break_dist_0.25.out:1・4・8・10, break_dist/held_reason_break_dist_1.out:1・2・8・9 | +1,242.7・−1,278.0・+1,181.4・−1,176.8・−1,426.0・+1,588.6・−1,324.0・+1,401.6 | 円 | 一致(丸めた範囲(1,177〜1,589)) |
| 398 | +148 | 円 | break_dist/fam_tables.md:32 | +148 | 円 | 一致 |
| 398 | +48 | 円 | break_dist/fam_tables.md:32 | +48 | 円 | 一致 |
| 398 | +257 | 円 | break_dist/fam_tables.md:32 | +257 | 円 | 一致 |
| 398 | −13 | 円 | break_dist/band_migration.out:10 | -13 | 円 | 一致 |
| 399 | +80 | 円 | break_dist/scene_diff.out:5 | +80 | 円 | 一致 |
| 399 | +195 | 円 | break_dist/scene_diff.out:9 | +195 | 円 | 一致 |
| 400 | −0.75 | 円 | break_dist/fam_tables.md:63 | -0.75 | 円 | 一致 |
| 400 | −1.25 | 円 | break_dist/fam_tables.md:63 | -1.25 | 円 | 一致 |
| 400 | −0.29 | 円 | break_dist/fam_tables.md:63 | -0.29 | 円 | 一致 |
| 401 | −50,631 | 円 | break_dist/fam_tables.md:99 / break_dist_0.25/diag_tables.json d7.match.sum_only_b | -50,631 / -2531.5639 bp(× 20 = -50631.28 円) | 円 / bp | 一致 |
| 401 | +3,065 | 円 | break_dist/band_migration.out:5・8 | +27,309 + (−24,244) = +3,065 | 円(計算) | 一致(計算値: 基準だけの取引の前半の和) |
| 401 | −53,696 | 円 | break_dist/band_migration.out:13・16 | +6,413 + (−60,109) = −53,696 | 円(計算) | 一致(計算値: 基準だけの取引の後半の和) |
| 401 | +37 | 円 | break_dist/band_migration.out:13・16 | −(−53,696) ÷ 1,470 = +36.5(差の列 −4 と +41 の和 +37) | 円(計算) | 一致(計算値) |
| 402 | +47 | 円 | break_dist/fam_tables.md:85 / break_dist_0.25/diag_tables.json d7.all.mean | +47.1 / +2.3555 bp(× 20 = +47.11 円) | 円 / bp | 一致 |
| 426 | +345 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.first.mean | +345 / +17.2728 bp(× 20 = +345.46 円) | 円 / bp | 一致 |
| 426 | +248 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.first.lo | +248 / +12.4077 bp(× 20 = +248.15 円) | 円 / bp | 一致 |
| 426 | +456 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.first.hi | +456 / +22.7951 bp(× 20 = +455.90 円) | 円 / bp | 一致 |
| 426 | −162 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.second.mean | -162 / -8.0827 bp(× 20 = -161.65 円) | 円 / bp | 一致 |
| 426 | −236 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.second.lo | -236 / -11.8001 bp(× 20 = -236.00 円) | 円 / bp | 一致 |
| 426 | −82 | 円 | break_dist/fam_tables.md:15 / break_dist_0.25/diag_tables.json d1.segments.second.hi | -82 / -4.0757 bp(× 20 = -81.51 円) | 円 / bp | 一致 |
| 427 | +472 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.segments.first.mean | +472 / +23.6182 bp(× 20 = +472.36 円) | 円 / bp | 一致 |
| 427 | +307 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.rows[5].mde または d1.segments.first.lo | +307 / +15.3581 bp(× 20 = +307.16 円) | 円 / bp | 一致 |
| 427 | +636 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.segments.first.hi | +636 / +31.8200 bp(× 20 = +636.40 円) | 円 / bp | 一致 |
| 427 | −289 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.segments.second.mean | -289 / -14.4422 bp(× 20 = -288.84 円) | 円 / bp | 一致 |
| 427 | −415 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.segments.second.lo | -415 / -20.7712 bp(× 20 = -415.42 円) | 円 / bp | 一致 |
| 427 | −176 | 円 | break_dist/fam_tables.md:16 / break_dist_1/diag_tables.json d1.segments.second.hi | -176 / -8.8215 bp(× 20 = -176.43 円) | 円 / bp | 一致 |
| 428 | +362 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.segments.first.mean | +362 / +18.1147 bp(× 20 = +362.29 円) | 円 / bp | 一致 |
| 428 | +231 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.segments.first.lo | +231 / +11.5545 bp(× 20 = +231.09 円) | 円 / bp | 一致 |
| 428 | +497 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.segments.first.hi | +497 / +24.8558 bp(× 20 = +497.12 円) | 円 / bp | 一致 |
| 428 | −273 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.segments.second.mean | -273 / -13.6334 bp(× 20 = -272.67 円) | 円 / bp | 一致 |
| 428 | −360 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.segments.second.lo | -360 / -17.9998 bp(× 20 = -360.00 円) | 円 / bp | 一致 |
| 428 | −184 | 円 | break_dist/fam_tables.md:17 / base/diag_tables.json d1.segments.second.hi | -184 / -9.1933 bp(× 20 = -183.87 円) | 円 / bp | 一致 |
| 442 | +47.1 | 円 | break_dist/fam_tables.md:85 / break_dist_0.25/diag_tables.json d7.all.mean | +47.1 / +2.3555 bp(× 20 = +47.11 円) | 円 / bp | 一致 |
| 442 | −0.1 | 円 | break_dist/fam_tables.md:85 / break_dist_0.25/diag_tables.json d7.all.lo | -0.1 / -0.0061 bp(× 20 = -0.12 円) | 円 / bp | 一致 |
| 442 | +94.6 | 円 | break_dist/fam_tables.md:85 / break_dist_0.25/diag_tables.json d7.all.hi | +94.6 / +4.7302 bp(× 20 = +94.60 円) | 円 / bp | 一致 |
| 442 | 68.8 | 円 | break_dist/fam_tables.md:85 / break_dist_0.25/diag_tables.json d7.all.mde | +68.8 / +3.4421 bp(× 20 = +68.84 円) | 円 / bp | 一致 |
| 442 | −17 | 円 | break_dist/fam_tables.md:85 | -17 | 円 | 一致 |
| 442 | −94 | 円 | break_dist/fam_tables.md:85 | -94 | 円 | 一致 |
| 442 | +61 | 円 | break_dist/fam_tables.md:85 | +61 | 円 | 一致 |
| 442 | +111 | 円 | break_dist/fam_tables.md:85 / break_dist_0.25/diag_tables.json d7.years.2023.mean | +111 / +5.5555 bp(× 20 = +111.11 円) | 円 / bp | 一致 |
| 442 | +54 | 円 | break_dist/fam_tables.md:85 | +54 | 円 | 一致 |
| 442 | +174 | 円 | break_dist/fam_tables.md:85 | +174 | 円 | 一致 |
| 442 | +17 | 円 | break_dist/fam_tables.md:92 / break_dist_0.25/diag_tables.json d7.years.2016.mean | +17 / +0.8322 bp(× 20 = +16.64 円) | 円 / bp | 一致 |
| 442 | −175 | 円 | break_dist/fam_tables.md:92 / break_dist_0.25/diag_tables.json d7.years.2018.mean | -175 / -8.7607 bp(× 20 = -175.21 円) | 円 / bp | 一致 |
| 442 | +73 | 円 | break_dist/fam_tables.md:92 / break_dist_0.25/diag_tables.json d7.years.2020.mean | +73 / +3.6640 bp(× 20 = +73.28 円) | 円 / bp | 一致 |
| 442 | +80 | 円 | break_dist/fam_tables.md:92 / break_dist_0.25/diag_tables.json d7.years.2022.mean | +80 / +3.9781 bp(× 20 = +79.56 円) | 円 / bp | 一致 |
| 442 | +111 | 円 | break_dist/fam_tables.md:92 / break_dist_0.25/diag_tables.json d7.years.2023.mean | +111 / +5.5555 bp(× 20 = +111.11 円) | 円 / bp | 一致 |
| 443 | +46.9 | 円 | break_dist/fam_tables.md:86 / break_dist_1/diag_tables.json d7.all.mean | +46.9 / +2.3463 bp(× 20 = +46.93 円) | 円 / bp | 一致 |
| 443 | −23.8 | 円 | break_dist/fam_tables.md:86 / break_dist_1/diag_tables.json d7.all.lo | -23.8 / -1.1902 bp(× 20 = -23.80 円) | 円 / bp | 一致 |
| 443 | +107.0 | 円 | break_dist/fam_tables.md:86 / break_dist_1/diag_tables.json d7.all.hi | +107.0 / +5.3518 bp(× 20 = +107.04 円) | 円 / bp | 一致 |
| 443 | 93.0 | 円 | break_dist/fam_tables.md:86 / break_dist_1/diag_tables.json d7.all.mde | +93.0 / +4.6495 bp(× 20 = +92.99 円) | 円 / bp | 一致 |
| 443 | +110 | 円 | break_dist/fam_tables.md:86 | +110 | 円 | 一致 |
| 443 | +19 | 円 | break_dist/fam_tables.md:86 | +19 | 円 | 一致 |
| 443 | +213 | 円 | break_dist/fam_tables.md:86 | +213 | 円 | 一致 |
| 443 | −16 | 円 | break_dist/fam_tables.md:86 | -16 | 円 | 一致 |
| 443 | −96 | 円 | break_dist/fam_tables.md:86 | -96 | 円 | 一致 |
| 443 | +58 | 円 | break_dist/fam_tables.md:86 | +58 | 円 | 一致 |
| 443 | −1 | 円 | break_dist/fam_tables.md:93 / break_dist_1/diag_tables.json d7.years.2016.mean | -1 / -0.0425 bp(× 20 = -0.85 円) | 円 / bp | 一致 |
| 443 | +49 | 円 | break_dist/fam_tables.md:93 / break_dist_1/diag_tables.json d7.years.2018.mean | +49 / +2.4436 bp(× 20 = +48.87 円) | 円 / bp | 一致 |
| 443 | +140 | 円 | break_dist/fam_tables.md:93 / break_dist_1/diag_tables.json d7.years.2020.mean | +140 / +6.9999 bp(× 20 = +140.00 円) | 円 / bp | 一致 |
| 443 | −60 | 円 | break_dist/fam_tables.md:93 / break_dist_1/diag_tables.json d7.years.2022.mean | -60 / -3.0227 bp(× 20 = -60.45 円) | 円 / bp | 一致 |
| 443 | −85 | 円 | break_dist/fam_tables.md:93 / break_dist_1/diag_tables.json d7.years.2023.mean | -85 / -4.2269 bp(× 20 = -84.54 円) | 円 / bp | 一致 |
| 447 | +111 | 円 | break_dist/fam_tables.md:85 / break_dist_0.25/diag_tables.json d7.years.2023.mean | +111 / +5.5555 bp(× 20 = +111.11 円) | 円 / bp | 一致 |
| 447 | +54 | 円 | break_dist/fam_tables.md:85 | +54 | 円 | 一致 |
| 447 | +174 | 円 | break_dist/fam_tables.md:85 | +174 | 円 | 一致 |
| 447 | +110 | 円 | break_dist/fam_tables.md:86 | +110 | 円 | 一致 |
| 447 | +19 | 円 | break_dist/fam_tables.md:86 | +19 | 円 | 一致 |
| 447 | +213 | 円 | break_dist/fam_tables.md:86 | +213 | 円 | 一致 |
| 447 | +47 | 円 | break_dist/fam_tables.md:85 / break_dist_0.25/diag_tables.json d7.all.mean | +47.1 / +2.3555 bp(× 20 = +47.11 円) | 円 / bp | 一致 |
| 447 | +101 | 円 | break_dist/band_migration.out:14 | +101 | 円 | 一致 |
| 447 | +37 | 円 | break_dist/band_migration.out:13・16 | −(−53,696) ÷ 1,470 = +36.5(差の列 −4 と +41 の和 +37) | 円(計算) | 一致(計算値) |
| 447 | +34 | 円 | break_dist/band_migration.out:18 | +34 | 円 | 一致 |
| 447 | +1,181 | 円 | break_dist/held_reason_break_dist_0.25.out:8 | +1181.4 | 円 | 一致 |
| 447 | −1,177 | 円 | break_dist/held_reason_break_dist_0.25.out:10 | -1176.8 | 円 | 一致 |
| 447 | −13 | 円 | break_dist/band_migration.out:10 | -13 | 円 | 一致 |
| 447 | +1,243 | 円 | break_dist/held_reason_break_dist_0.25.out:1 | +1242.7 | 円 | 一致 |
| 447 | −1,278 | 円 | break_dist/held_reason_break_dist_0.25.out:4 | -1278.0 | 円 | 一致 |
| 447 | −63 | 円 | break_dist/band_migration.out:17 | -63 | 円 | 一致 |
| 447 | +99 | 円 | break_dist/band_migration.out:23 | +99 | 円 | 一致 |
| 447 | +83 | 円 | break_dist/band_migration.out:26 | +83 | 円 | 一致 |
| 447 | −3 | 円 | break_dist/band_migration.out:34 | -3 | 円 | 一致 |
| 447 | +1,589 | 円 | break_dist/held_reason_break_dist_1.out:2 | +1588.6 | 円 | 一致 |
| 447 | −1,426 | 円 | break_dist/held_reason_break_dist_1.out:1 | -1426.0 | 円 | 一致 |
| 447 | −72 | 円 | break_dist/band_migration.out:22 | -72 | 円 | 一致 |
| 447 | −142.7 | 円 | break_dist/same_bar_reason_break_dist_1.out:1 | -142.7 | 円 | 一致 |
| 447 | −270.0 | 円 | break_dist/same_bar_reason_break_dist_1.out:1 | -270.0 | 円 | 一致 |
| 447 | −92 | 円 | break_dist/same_bar_reason_break_dist_1.out:1 | -91.6 | 円 | 一致 |
| 447 | +148 | 円 | break_dist/fam_tables.md:32 | +148 | 円 | 一致 |
| 447 | +48 | 円 | break_dist/fam_tables.md:32 | +48 | 円 | 一致 |
| 447 | +257 | 円 | break_dist/fam_tables.md:32 | +257 | 円 | 一致 |
| 447 | +83 | 円 | break_dist/band_migration.out:26 | +83 | 円 | 一致 |
| 447 | −3 | 円 | break_dist/band_migration.out:34 | -3 | 円 | 一致 |

### break_len_mult(`docs/ANALYSIS/2026-10-09_matilda_main_break_len_mult.md`)

拾った数 403: 一致 375・単位の誤り 18・値の誤り 4・出所が無い・見つからない 6・確かめられない 0

| 文書の行 | 書かれた数 | 書かれた単位 | 出所 ファイル:行 | 出所の値 | 出所の単位 | 判定 |
|---|---|---|---|---|---|---|
| 56 | +735,267.612 | 円 | break_len_mult/fam_tables.md:7 | 735267.612 | 円 | 一致 |
| 85 | −2,378 | 円 | break_len_mult/market_side.out:1 | -2378 | 円 | 一致 |
| 85 | +735,268 | 円 | break_len_mult/fam_tables.md:7 | 735267.612 | 円 | 一致 |
| 113 | +708 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.first.mean | +708 / +35.3819 bp(× 20 = +707.64 円) | 円 / bp | 一致 |
| 113 | +532 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.first.lo | +532 / +26.5774 bp(× 20 = +531.55 円) | 円 / bp | 一致 |
| 113 | +889 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.first.hi | +889 / +44.4456 bp(× 20 = +888.91 円) | 円 / bp | 一致 |
| 113 | 255 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.first.mde | +255 / +12.7701 bp(× 20 = +255.40 円) | 円 / bp | 一致 |
| 113 | −205 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.second.mean | -205 / -10.2524 bp(× 20 = -205.05 円) | 円 / bp | 一致 |
| 113 | −303 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.second.lo | -303 / -15.1669 bp(× 20 = -303.34 円) | 円 / bp | 一致 |
| 113 | −110 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.second.hi | -110 / -5.5234 bp(× 20 = -110.47 円) | 円 / bp | 一致 |
| 113 | 143 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.second.mde | +143 / +7.1612 bp(× 20 = +143.22 円) | 円 / bp | 一致 |
| 113 | −913 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.diff.mean | -913 / -45.6343 bp(× 20 = -912.69 円) | 円 / bp | 一致 |
| 113 | −1,107 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.diff.lo | -1,107 / -55.3369 bp(× 20 = -1106.74 円) | 円 / bp | 一致 |
| 113 | −734 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.diff.hi | -734 / -36.6788 bp(× 20 = -733.58 円) | 円 / bp | 一致 |
| 113 | +251 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.rows[0].mean または d1.rows[5].mde | +251 / +12.5259 bp(× 20 = +250.52 円) | 円 / bp | 一致 |
| 113 | +147 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.rows[0].lo | +147 / +7.3523 bp(× 20 = +147.05 円) | 円 / bp | 一致 |
| 113 | +353 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.rows[0].hi | +353 / +17.6624 bp(× 20 = +353.25 円) | 円 / bp | 一致 |
| 114 | +362 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.segments.first.mean | +362 / +18.1147 bp(× 20 = +362.29 円) | 円 / bp | 一致 |
| 114 | +231 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.segments.first.lo | +231 / +11.5545 bp(× 20 = +231.09 円) | 円 / bp | 一致 |
| 114 | +497 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.segments.first.hi | +497 / +24.8558 bp(× 20 = +497.12 円) | 円 / bp | 一致 |
| 114 | 195 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.segments.first.mde | +195 / +9.7558 bp(× 20 = +195.12 円) | 円 / bp | 一致 |
| 114 | −273 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.segments.second.mean | -273 / -13.6334 bp(× 20 = -272.67 円) | 円 / bp | 一致 |
| 114 | −360 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.segments.second.lo | -360 / -17.9998 bp(× 20 = -360.00 円) | 円 / bp | 一致 |
| 114 | −184 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.segments.second.hi | -184 / -9.1933 bp(× 20 = -183.87 円) | 円 / bp | 一致 |
| 114 | 125 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.segments.second.mde | +125 / +6.2593 bp(× 20 = +125.19 円) | 円 / bp | 一致 |
| 114 | −635 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.segments.diff.mean | -635 / -31.7481 bp(× 20 = -634.96 円) | 円 / bp | 一致 |
| 114 | −805 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.segments.diff.lo | -805 / -40.2715 bp(× 20 = -805.43 円) | 円 / bp | 一致 |
| 114 | −476 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.segments.diff.hi | -476 / -23.8222 bp(× 20 = -476.44 円) | 円 / bp | 一致 |
| 114 | +45 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.rows[0].mean | +45 / +2.2353 bp(× 20 = +44.71 円) | 円 / bp | 一致 |
| 114 | −41 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.rows[0].lo | -41 / -2.0563 bp(× 20 = -41.13 円) | 円 / bp | 一致 |
| 114 | +124 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.rows[0].hi | +124 / +6.2076 bp(× 20 = +124.15 円) | 円 / bp | 一致 |
| 120 | −1,531 | 円 | break_len_mult/fam_tables.md:21 / break_len_mult_4/diag_tables.json d1.rows[1].mean | -1,531 / -76.5386 bp(× 20 = -1530.77 円) | 円 / bp | 一致 |
| 120 | +185 | 円 | break_len_mult/fam_tables.md:21 / break_len_mult_4/diag_tables.json d1.rows[2].mean | +185 / +9.2556 bp(× 20 = +185.11 円) | 円 / bp | 一致 |
| 120 | +1,375 | 円 | break_len_mult/fam_tables.md:21 / break_len_mult_4/diag_tables.json d1.rows[3].mean | +1,375 / +68.7572 bp(× 20 = +1375.14 円) | 円 / bp | 一致 |
| 120 | +985 | 円 | break_len_mult/fam_tables.md:21 / break_len_mult_4/diag_tables.json d1.rows[4].mean | +985 / +49.2282 bp(× 20 = +984.56 円) | 円 / bp | 一致 |
| 120 | +417 | 円 | break_len_mult/fam_tables.md:21 / break_len_mult_4/diag_tables.json d1.rows[5].mean | +417 / +20.8577 bp(× 20 = +417.15 円) | 円 / bp | 一致 |
| 120 | +186 | 円 | break_len_mult/fam_tables.md:21 / break_len_mult_4/diag_tables.json d1.rows[6].mean | +186 / +9.3231 bp(× 20 = +186.46 円) | 円 / bp | 一致 |
| 120 | −339 | 円 | break_len_mult/fam_tables.md:21 / break_len_mult_4/diag_tables.json d1.rows[7].mean | -339 / -16.9330 bp(× 20 = -338.66 円) | 円 / bp | 一致 |
| 120 | −223 | 円 | break_len_mult/fam_tables.md:21 / break_len_mult_4/diag_tables.json d1.rows[8].mean | -223 / -11.1398 bp(× 20 = -222.80 円) | 円 / bp | 一致 |
| 120 | −479 | 円 | break_len_mult/fam_tables.md:21 / break_len_mult_4/diag_tables.json d1.rows[9].mean | -479 / -23.9346 bp(× 20 = -478.69 円) | 円 / bp | 一致 |
| 121 | −263 | 円 | break_len_mult/fam_tables.md:22 / base/diag_tables.json d1.rows[1].mean または d1.rows[8].mean | -263 / -13.1430 bp(× 20 = -262.86 円) | 円 / bp | 一致 |
| 121 | +133 | 円 | break_len_mult/fam_tables.md:22 / base/diag_tables.json d1.rows[2].mean | +133 / +6.6326 bp(× 20 = +132.65 円) | 円 / bp | 一致 |
| 121 | +564 | 円 | break_len_mult/fam_tables.md:22 / base/diag_tables.json d1.rows[3].mean | +564 / +28.1875 bp(× 20 = +563.75 円) | 円 / bp | 一致 |
| 121 | +543 | 円 | break_len_mult/fam_tables.md:22 / base/diag_tables.json d1.rows[4].mean | +543 / +27.1491 bp(× 20 = +542.98 円) | 円 / bp | 一致 |
| 121 | +244 | 円 | break_len_mult/fam_tables.md:22 / base/diag_tables.json d1.rows[5].mean | +244 / +12.2149 bp(× 20 = +244.30 円) | 円 / bp | 一致 |
| 121 | +6 | 円 | break_len_mult/fam_tables.md:22 / base/diag_tables.json d1.rows[6].mean | +6 / +0.2952 bp(× 20 = +5.90 円) | 円 / bp | 一致 |
| 121 | −384 | 円 | break_len_mult/fam_tables.md:22 / base/diag_tables.json d1.rows[7].mean | -384 / -19.2131 bp(× 20 = -384.26 円) | 円 / bp | 一致 |
| 121 | −263 | 円 | break_len_mult/fam_tables.md:22 / base/diag_tables.json d1.rows[1].mean または d1.rows[8].mean | -263 / -13.1430 bp(× 20 = -262.86 円) | 円 / bp | 一致 |
| 121 | −479 | 円 | break_len_mult/fam_tables.md:22 / base/diag_tables.json d1.rows[9].mean | -479 / -23.9354 bp(× 20 = -478.71 円) | 円 / bp | 一致 |
| 123 | +708 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.first.mean | +708 / +35.3819 bp(× 20 = +707.64 円) | 円 / bp | 一致 |
| 123 | −205 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.second.mean | -205 / -10.2524 bp(× 20 = -205.05 円) | 円 / bp | 一致 |
| 123 | −1,531 | 円 | break_len_mult/fam_tables.md:21 / break_len_mult_4/diag_tables.json d1.rows[1].mean | -1,531 / -76.5386 bp(× 20 = -1530.77 円) | 円 / bp | 一致 |
| 123 | +251 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.rows[0].mean または d1.rows[5].mde | +251 / +12.5259 bp(× 20 = +250.52 円) | 円 / bp | 一致 |
| 156 | +474 | 円 | break_len_mult/scenes.out:5 | +474 | 円 | 一致 |
| 156 | +339 | 円 | break_len_mult/scenes.out:5 | +339 | 円 | 一致 |
| 156 | +611 | 円 | break_len_mult/scenes.out:5 | +611 | 円 | 一致 |
| 156 | +264 | 円 | base_scenes.out:5 | +264 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 156 | +210 | 円 | break_len_mult/scene_diff.out:4 | +210 | 円 | 一致 |
| 156 | +137 | 円 | break_len_mult/scene_diff.out:4 | +137 | 円 | 一致 |
| 156 | +300 | 円 | break_len_mult/scene_diff.out:4 | +300 | 円 | 一致 |
| 156 | −218 | 円 | break_len_mult/scenes.out:6 | -218 | 円 | 一致 |
| 156 | −334 | 円 | break_len_mult/scenes.out:6 | -334 | 円 | 一致 |
| 156 | −103 | 円 | break_len_mult/scenes.out:6 | -103 | 円 | 一致 |
| 156 | −216 | 円 | base_scenes.out:6 | -216 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 156 | −2 | 円 | break_len_mult/scene_diff.out:5 | -2 | 円 | 一致 |
| 156 | −65 | 円 | break_len_mult/scene_diff.out:5 | -65 | 円 | 一致 |
| 156 | +57 | 円 | break_len_mult/scene_diff.out:5 | +57 | 円 | 一致 |
| 157 | +767 | 円 | break_len_mult/scenes.out:8 | +767 | 円 | 一致 |
| 157 | +522 | 円 | break_len_mult/scenes.out:8 | +522 | 円 | 一致 |
| 157 | +1,059 | 円 | break_len_mult/scenes.out:8 | +1059 | 円 | 一致 |
| 157 | +411 | 円 | base_scenes.out:8 | +411 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 157 | +356 | 円 | break_len_mult/scene_diff.out:6 | +356 | 円 | 一致 |
| 157 | +168 | 円 | break_len_mult/scene_diff.out:6 | +168 | 円 | 一致 |
| 157 | +530 | 円 | break_len_mult/scene_diff.out:6 | +530 | 円 | 一致 |
| 157 | −185 | 円 | break_len_mult/scenes.out:9 | -185 | 円 | 一致 |
| 157 | −379 | 円 | break_len_mult/scenes.out:9 | -379 | 円 | 一致 |
| 157 | +5 | 円 | break_len_mult/scenes.out:9 | +5 | 円 | 一致 |
| 157 | −282 | 円 | base_scenes.out:9 | -282 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 157 | +97 | 円 | break_len_mult/scene_diff.out:7 | +97 | 円 | 一致 |
| 157 | −9 | 円 | break_len_mult/scene_diff.out:7 | -9 | 円 | 一致 |
| 157 | +212 | 円 | break_len_mult/scene_diff.out:7 | +212 | 円 | 一致 |
| 158 | +1,448 | 円 | break_len_mult/scenes.out:11 | +1448 | 円 | 一致 |
| 158 | +1,068 | 円 | break_len_mult/scenes.out:11 | +1068 | 円 | 一致 |
| 158 | +1,882 | 円 | break_len_mult/scenes.out:11 | +1882 | 円 | 一致 |
| 158 | +656 | 円 | base_scenes.out:11 | +656 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 158 | +792 | 円 | break_len_mult/scene_diff.out:8 | +792 | 円 | 一致 |
| 158 | +502 | 円 | break_len_mult/scene_diff.out:8 | +502 | 円 | 一致 |
| 158 | +1,078 | 円 | break_len_mult/scene_diff.out:8 | +1078 | 円 | 一致 |
| 158 | −205 | 円 | break_len_mult/scenes.out:12 | -205 | 円 | 一致 |
| 158 | −411 | 円 | break_len_mult/scenes.out:12 | -411 | 円 | 一致 |
| 158 | +44 | 円 | break_len_mult/scenes.out:12 | +44 | 円 | 一致 |
| 158 | −343 | 円 | base_scenes.out:12 | -343 | 円 | 出所が無い・見つからない(書かれた出所 `alert/scenes.out` に base の行が無い(alert_x1・alert_x2 だけ)。同じ値は `base_scenes.out` にある) |
| 158 | +139 | 円 | break_len_mult/scene_diff.out:9 | +139 | 円 | 一致 |
| 158 | −2 | 円 | break_len_mult/scene_diff.out:9 | -2 | 円 | 一致 |
| 158 | +286 | 円 | break_len_mult/scene_diff.out:9 | +286 | 円 | 一致 |
| 160 | +210 | 円 | break_len_mult/scene_diff.out:4 | +210 | 円 | 一致 |
| 160 | +356 | 円 | break_len_mult/scene_diff.out:6 | +356 | 円 | 一致 |
| 160 | +792 | 円 | break_len_mult/scene_diff.out:8 | +792 | 円 | 一致 |
| 160 | −9 | 円 | break_len_mult/scene_diff.out:7 | -9 | 円 | 一致 |
| 160 | −2 | 円 | break_len_mult/scene_diff.out:5 | -2 | 円 | 一致 |
| 181 | +36.8 | 円 | break_len_mult/compare.md:7 | +36.8 | 円 | 一致 |
| 181 | −375.1 | 円 | break_len_mult/compare.md:7 | -375.1 | 円 | 一致 |
| 181 | −420.7 | 円 | break_len_mult/compare.md:7 | -420.7 | 円 | 一致 |
| 181 | −4,139,710 | 円 | break_len_mult/compare.md:7 | -4,139,710 | 円 | 一致 |
| 181 | +1,036,689 | 円 | break_len_mult/compare.md:7 | +1,036,689 | 円 | 一致 |
| 182 | +40.5 | 円 | break_len_mult/compare.md:6 | +40.5 | 円 | 一致 |
| 182 | −281.0 | 円 | break_len_mult/compare.md:6 | -281.0 | 円 | 一致 |
| 182 | −273.4 | 円 | break_len_mult/compare.md:6 | -273.4 | 円 | 一致 |
| 182 | −3,866,293 | 円 | break_len_mult/compare.md:6 | -3,866,293 | 円 | 一致 |
| 182 | +532,210 | 円 | break_len_mult/compare.md:6 | +532,210 | 円 | 一致 |
| 183 | +27.9 | 円 | break_len_mult/compare.md:14 | +27.9 | 円 | 一致 |
| 183 | −314.7 | 円 | break_len_mult/compare.md:14 | -314.7 | 円 | 一致 |
| 183 | −630.8 | 円 | break_len_mult/compare.md:14 | -630.8 | 円 | 一致 |
| 183 | −4,303,688 | 円 | break_len_mult/compare.md:14 | -4,303,688 | 円 | 一致 |
| 183 | −301,421 | 円 | break_len_mult/compare.md:14 | -301,421 | 円 | 一致 |
| 184 | +32.2 | 円 | break_len_mult/compare.md:13 | +32.2 | 円 | 一致 |
| 184 | −238.4 | 円 | break_len_mult/compare.md:13 | -238.4 | 円 | 一致 |
| 184 | −431.6 | 円 | break_len_mult/compare.md:13 | -431.6 | 円 | 一致 |
| 184 | −3,834,951 | 円 | break_len_mult/compare.md:13 | -3,834,951 | 円 | 一致 |
| 184 | −400,821 | 円 | break_len_mult/compare.md:13 | -400,821 | 円 | 一致 |
| 190 | +527 | 円 | break_len_mult/fam_tables.md:28 | +527 | 円 | 一致 |
| 190 | +466 | 円 | break_len_mult/fam_tables.md:28 | +466 | 円 | 一致 |
| 190 | +589 | 円 | break_len_mult/fam_tables.md:28 | +589 | 円 | 一致 |
| 190 | +232 | 円 | break_len_mult/fam_tables.md:28 | +232 | 円 | 一致 |
| 190 | +207 | 円 | break_len_mult/fam_tables.md:28 | +207 | 円 | 一致 |
| 190 | +258 | 円 | break_len_mult/fam_tables.md:28 | +258 | 円 | 一致 |
| 190 | −134.1 | 円 | break_len_mult/levels_reason.out:4 | -134.1 | 円 | 一致 |
| 190 | −123.6 | 円 | break_len_mult/levels_reason.out:6 | -123.6 | 円 | 一致 |
| 191 | +181 | 円 | break_len_mult/fam_tables.md:29 | +181 | 円 | 一致 |
| 191 | +9 | 円 | break_len_mult/fam_tables.md:29 | +9 | 円 | 一致 |
| 191 | +351 | 円 | break_len_mult/fam_tables.md:29 | +351 | 円 | 一致 |
| 191 | −437 | 円 | break_len_mult/fam_tables.md:29 | -437 | 円 | 一致 |
| 191 | −535 | 円 | break_len_mult/fam_tables.md:29 | -535 | 円 | 一致 |
| 191 | −340 | 円 | break_len_mult/fam_tables.md:29 | -340 | 円 | 一致 |
| 191 | −450.6 | 円 | break_len_mult/levels_reason.out:8 | -450.6 | 円 | 一致 |
| 191 | −365.9 | 円 | break_len_mult/levels_reason.out:11 | -365.9 | 円 | 一致 |
| 192 | +329 | 円 | break_len_mult/fam_tables.md:30 | +329 | 円 | 一致 |
| 192 | +274 | 円 | break_len_mult/fam_tables.md:30 | +274 | 円 | 一致 |
| 192 | +378 | 円 | break_len_mult/fam_tables.md:30 | +378 | 円 | 一致 |
| 192 | +117 | 円 | break_len_mult/fam_tables.md:30 | +117 | 円 | 一致 |
| 192 | +92 | 円 | break_len_mult/fam_tables.md:30 | +92 | 円 | 一致 |
| 192 | +141 | 円 | break_len_mult/fam_tables.md:30 | +141 | 円 | 一致 |
| 192 | −113.4 | 円 | break_len_mult/levels_reason.out:14 | -113.4 | 円 | 一致 |
| 192 | −103.8 | 円 | break_len_mult/levels_reason.out:16 | -103.8 | 円 | 一致 |
| 193 | +33 | 円 | break_len_mult/fam_tables.md:31 | +33 | 円 | 一致 |
| 193 | −100 | 円 | break_len_mult/fam_tables.md:31 | -100 | 円 | 一致 |
| 193 | +167 | 円 | break_len_mult/fam_tables.md:31 | +167 | 円 | 一致 |
| 193 | −390 | 円 | break_len_mult/fam_tables.md:31 | -390 | 円 | 一致 |
| 193 | −474 | 円 | break_len_mult/fam_tables.md:31 | -474 | 円 | 一致 |
| 193 | −302 | 円 | break_len_mult/fam_tables.md:31 | -302 | 円 | 一致 |
| 193 | −341.7 | 円 | break_len_mult/levels_reason.out:18 | -341.7 | 円 | 一致 |
| 193 | −277.2 | 円 | break_len_mult/levels_reason.out:21 | -277.2 | 円 | 一致 |
| 195 | +32.4 | 円 | break_len_mult/fam_tables.md:35 / break_len_mult_4/diag_tables.json d3.groups.出の理由【結果で決まる群】.close.per_trade | +32.4 / +1.6210 bp(× 20 = +32.42 円) | 円 / bp | 一致 |
| 195 | +30.7 | 円 | break_len_mult/fam_tables.md:35 / break_len_mult_4/diag_tables.json d3.groups.出の理由【結果で決まる群】.close.lo | +30.7 / +1.5371 bp(× 20 = +30.74 円) | 円 / bp | 一致 |
| 195 | +34.1 | 円 | break_len_mult/fam_tables.md:35 / break_len_mult_4/diag_tables.json d3.groups.出の理由【結果で決まる群】.close.hi | +34.1 / +1.7061 bp(× 20 = +34.12 円) | 円 / bp | 一致 |
| 195 | −343.3 | 円 | break_len_mult/fam_tables.md:35 / break_len_mult_4/diag_tables.json d3.groups.出の理由【結果で決まる群】.break.per_trade | -343.3 / -17.1650 bp(× 20 = -343.30 円) | 円 / bp | 一致 |
| 195 | −362.1 | 円 | break_len_mult/fam_tables.md:35 / break_len_mult_4/diag_tables.json d3.groups.出の理由【結果で決まる群】.break.lo | -362.1 / -18.1034 bp(× 20 = -362.07 円) | 円 / bp | 一致 |
| 195 | −325.3 | 円 | break_len_mult/fam_tables.md:35 / break_len_mult_4/diag_tables.json d3.groups.出の理由【結果で決まる群】.break.hi | -325.3 / -16.2625 bp(× 20 = -325.25 円) | 円 / bp | 一致 |
| 195 | −494.2 | 円 | break_len_mult/fam_tables.md:35 / break_len_mult_4/diag_tables.json d3.groups.出の理由【結果で決まる群】.market.per_trade | -494.2 / -24.7113 bp(× 20 = -494.23 円) | 円 / bp | 一致 |
| 195 | −548.8 | 円 | break_len_mult/fam_tables.md:35 / break_len_mult_4/diag_tables.json d3.groups.出の理由【結果で決まる群】.market.lo | -548.8 / -27.4376 bp(× 20 = -548.75 円) | 円 / bp | 一致 |
| 195 | −445.7 | 円 | break_len_mult/fam_tables.md:35 / break_len_mult_4/diag_tables.json d3.groups.出の理由【結果で決まる群】.market.hi | -445.7 / -22.2835 bp(× 20 = -445.67 円) | 円 / bp | 一致 |
| 195 | +36.4 | 円 | break_len_mult/fam_tables.md:36 / base/diag_tables.json d3.groups.出の理由【結果で決まる群】.close.per_trade | +36.4 / +1.8210 bp(× 20 = +36.42 円) | 円 / bp | 一致 |
| 195 | −258.8 | 円 | break_len_mult/fam_tables.md:36 / base/diag_tables.json d3.groups.出の理由【結果で決まる群】.break.per_trade | -258.8 / -12.9406 bp(× 20 = -258.81 円) | 円 / bp | 一致 |
| 195 | −315.2 | 円 | break_len_mult/fam_tables.md:36 / base/diag_tables.json d3.groups.出の理由【結果で決まる群】.market.per_trade | -315.2 / -15.7597 bp(× 20 = -315.19 円) | 円 / bp | 一致 |
| 196 | +824,555 | 円 | break_len_mult/fam_tables.md:35 / break_len_mult_4/diag_tables.json d3.top5_days_sum | +824,555 / +41227.7404 bp(× 20 = +824554.81 円) | 円 / bp | 一致 |
| 196 | −844,157 | 円 | break_len_mult/fam_tables.md:35 / break_len_mult_4/diag_tables.json d3.bottom5_days_sum | -844,157 / -42207.8409 bp(× 20 = -844156.82 円) | 円 / bp | 一致 |
| 196 | +735,268 | 円 | break_len_mult/fam_tables.md:35 / break_len_mult_4/diag_tables.json d3.total | +735,268 / +36763.3806 bp(× 20 = +735267.61 円) | 円 / bp | 一致 |
| 197 | −259 | 円 | break_len_mult/compare.md:20 | -258.8 | 円 | 一致 |
| 197 | −343 | 円 | break_len_mult/compare.md:21 | -343.3 | 円 | 一致 |
| 219 | +11,583,515 | 円 | break_len_mult/fam_tables.md:42 / break_len_mult_4/diag_paths.json d4.groups.勝った.pnl_sum | +11,583,515 / +579175.7522 bp(× 20 = +11583515.04 円) | 円 / bp | 一致 |
| 219 | 5.85 | move_bp | break_len_mult/fam_tables.md:42 / break_len_mult_4/diag_paths.json d4.groups.勝った.mfe_median | 5.85 / +5.8473 move_bp | move_bp / move_bp | 一致 |
| 219 | −5.15 | move_bp | break_len_mult/fam_tables.md:42 / break_len_mult_4/diag_paths.json d4.groups.勝った.mae_median | -5.15 / -5.1497 move_bp | move_bp / move_bp | 一致 |
| 219 | +10,177,344 | 円 | break_len_mult/fam_tables.md:46 / base/diag_paths.json d4.groups.勝った.pnl_sum | +10,177,344 / +508867.1933 bp(× 20 = +10177343.87 円) | 円 / bp | 一致 |
| 219 | 6.02 | move_bp | break_len_mult/fam_tables.md:46 / base/diag_paths.json d4.groups.勝った.mfe_median | 6.02 / +6.0217 move_bp | move_bp / move_bp | 一致 |
| 219 | −4.74 | move_bp | break_len_mult/fam_tables.md:46 / base/diag_paths.json d4.groups.勝った.mae_median | -4.74 / -4.7440 move_bp | move_bp / move_bp | 一致 |
| 220 | −5,111,738 | 円 | break_len_mult/fam_tables.md:43 / break_len_mult_4/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.pnl_sum | -5,111,738 / -255586.8885 bp(× 20 = -5111737.77 円) | 円 / bp | 一致 |
| 220 | 2.11 | move_bp | break_len_mult/fam_tables.md:43 / break_len_mult_4/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mfe_median | 2.11 / +2.1122 move_bp | move_bp / move_bp | 一致 |
| 220 | −38.22 | move_bp | break_len_mult/fam_tables.md:43 / break_len_mult_4/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mae_median | -38.22 / -38.2243 move_bp | move_bp / move_bp | 一致 |
| 220 | −4,695,044 | 円 | break_len_mult/fam_tables.md:47 / base/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.pnl_sum | -4,695,044 / -234752.1937 bp(× 20 = -4695043.87 円) | 円 / bp | 一致 |
| 220 | 2.05 | move_bp | break_len_mult/fam_tables.md:47 / base/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mfe_median | 2.05 / +2.0537 move_bp | move_bp / move_bp | 一致 |
| 220 | −30.50 | move_bp | break_len_mult/fam_tables.md:47 / base/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mae_median | -30.50 / -30.4965 move_bp | move_bp / move_bp | 一致 |
| 221 | −6,850,264 | 円 | break_len_mult/fam_tables.md:44 / break_len_mult_4/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.pnl_sum | -6,850,264 / -342513.2017 bp(× 20 = -6850264.03 円) | 円 / bp | 一致 |
| 221 | −2.97 | move_bp | break_len_mult/fam_tables.md:44 / break_len_mult_4/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mfe_median | -2.97 / -2.9748 move_bp | move_bp / move_bp | 一致 |
| 221 | −40.66 | move_bp | break_len_mult/fam_tables.md:44 / break_len_mult_4/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mae_median | -40.66 / -40.6605 move_bp | move_bp / move_bp | 一致 |
| 221 | −6,006,006 | 円 | break_len_mult/fam_tables.md:48 / base/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.pnl_sum | -6,006,006 / -300300.2903 bp(× 20 = -6006005.81 円) | 円 / bp | 一致 |
| 221 | −2.77 | move_bp | break_len_mult/fam_tables.md:48 / base/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mfe_median | -2.77 / -2.7731 move_bp | move_bp / move_bp | 一致 |
| 221 | −32.38 | move_bp | break_len_mult/fam_tables.md:48 / base/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mae_median | -32.38 / -32.3832 move_bp | move_bp / move_bp | 一致 |
| 223 | −0.34 | move_bp | break_len_mult/fam_tables.md:53 / break_len_mult_4/diag_paths.json d4.after_exit.5.per_trade | -0.34 / -0.3357 move_bp | move_bp / move_bp | 一致 |
| 223 | −0.64 | move_bp | break_len_mult/fam_tables.md:53 / break_len_mult_4/diag_paths.json d4.after_exit.15.per_trade | -0.64 / -0.6443 move_bp | move_bp / move_bp | 一致 |
| 223 | −0.37 | move_bp | break_len_mult/fam_tables.md:53 / break_len_mult_4/diag_paths.json d4.after_exit.60.per_trade | -0.37 / -0.3746 move_bp | move_bp / move_bp | 一致 |
| 223 | −0.86 | move_bp | break_len_mult/fam_tables.md:53 / break_len_mult_4/diag_paths.json d4.after_exit.60.lo | -0.86 / -0.8577 move_bp | move_bp / move_bp | 一致 |
| 223 | +0.08 | move_bp | break_len_mult/fam_tables.md:53 / break_len_mult_4/diag_paths.json d4.after_exit.60.hi | +0.08 / +0.0787 move_bp | move_bp / move_bp | 一致 |
| 223 | −0.34 | move_bp | break_len_mult/fam_tables.md:54 / base/diag_paths.json d4.after_exit.5.per_trade | -0.34 / -0.3353 move_bp | move_bp / move_bp | 一致 |
| 223 | −0.66 | move_bp | break_len_mult/fam_tables.md:54 / base/diag_paths.json d4.after_exit.15.per_trade | -0.66 / -0.6565 move_bp | move_bp / move_bp | 一致 |
| 223 | −0.42 | move_bp | break_len_mult/fam_tables.md:54 / base/diag_paths.json d4.after_exit.60.per_trade | -0.42 / -0.4195 move_bp | move_bp / move_bp | 一致 |
| 224 | −30 | move_bp | break_len_mult/fam_tables.md:47 / base/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mae_median | -30.50 / -30.4965 move_bp | move_bp / move_bp | 一致 |
| 224 | −32 | move_bp | break_len_mult/fam_tables.md:48 / base/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mae_median | -32.38 / -32.3832 move_bp | move_bp / move_bp | 一致 |
| 224 | −38 | move_bp | break_len_mult/fam_tables.md:43 / break_len_mult_4/diag_paths.json d4.groups.一度は MFE > 0 だったのに負けた.mae_median | -38.22 / -38.2243 move_bp | move_bp / move_bp | 一致 |
| 224 | −41 | move_bp | break_len_mult/fam_tables.md:44 / break_len_mult_4/diag_paths.json d4.groups.MFE ≤ 0 のまま負けた.mae_median | -40.66 / -40.6605 move_bp | move_bp / move_bp | 一致 |
| 242 | −0.24 | move_bp | break_len_mult/fam_tables.md:60 / break_len_mult_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.per_trade | -0.24 / -0.2432 move_bp | move_bp / move_bp | 一致 |
| 242 | −0.30 | move_bp | break_len_mult/fam_tables.md:60 / break_len_mult_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.lo | -0.30 / -0.2961 move_bp | move_bp / move_bp | 一致 |
| 242 | −0.19 | move_bp | break_len_mult/fam_tables.md:60 / break_len_mult_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.hi | -0.19 / -0.1902 move_bp | move_bp / move_bp | 一致 |
| 242 | −0.48 | move_bp | break_len_mult/fam_tables.md:60 / break_len_mult_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.per_trade または d5.建てた合図(起点 = 建ての時刻).15.signal.hi | -0.48 / -0.4765 move_bp | move_bp / move_bp | 一致 |
| 242 | −0.59 | move_bp | break_len_mult/fam_tables.md:60 / break_len_mult_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.lo | -0.59 / -0.5937 move_bp | move_bp / move_bp | 一致 |
| 242 | −0.36 | move_bp | break_len_mult/fam_tables.md:60 / break_len_mult_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.hi | -0.36 / -0.3623 move_bp | move_bp / move_bp | 一致 |
| 242 | −0.68 | move_bp | break_len_mult/fam_tables.md:60 / break_len_mult_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.per_trade | -0.68 / -0.6776 move_bp | move_bp / move_bp | 一致 |
| 242 | −0.89 | move_bp | break_len_mult/fam_tables.md:60 / break_len_mult_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.lo | -0.89 / -0.8940 move_bp | move_bp / move_bp | 一致 |
| 242 | −0.48 | move_bp | break_len_mult/fam_tables.md:60 / break_len_mult_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.per_trade または d5.建てた合図(起点 = 建ての時刻).15.signal.hi | -0.48 / -0.4765 move_bp | move_bp / move_bp | 一致 |
| 242 | −0.46 | move_bp | break_len_mult/fam_tables.md:60 / break_len_mult_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.per_trade | -0.46 / -0.4601 move_bp | move_bp / move_bp | 一致 |
| 242 | −0.96 | move_bp | break_len_mult/fam_tables.md:60 / break_len_mult_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.lo | -0.96 / -0.9623 move_bp | move_bp / move_bp | 一致 |
| 242 | −0.03 | move_bp | break_len_mult/fam_tables.md:60 / break_len_mult_4/diag_paths.json d5.建てた合図(起点 = 合図の時刻).1.control_24h.lo または d5.建てた合図(起点 = 建ての時刻).60.signal.hi | -0.03 / -0.0281 move_bp | move_bp / move_bp | 一致 |
| 242 | +0.50 | move_bp | break_len_mult/fam_tables.md:60 / break_len_mult_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.control_24h.per_trade | +0.50 / +0.5004 move_bp | move_bp / move_bp | 一致 |
| 242 | −0.02 | move_bp | break_len_mult/fam_tables.md:60 / break_len_mult_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.control_24h.lo | -0.02 / -0.0187 move_bp | move_bp / move_bp | 一致 |
| 242 | +0.98 | move_bp | break_len_mult/fam_tables.md:60 / break_len_mult_4/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.control_24h.hi | +0.98 / +0.9770 move_bp | move_bp / move_bp | 一致 |
| 242 | −0.25 | move_bp | break_len_mult/fam_tables.md:61 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).1.signal.per_trade | -0.25 / -0.2537 move_bp | move_bp / move_bp | 一致 |
| 242 | −0.51 | move_bp | break_len_mult/fam_tables.md:61 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).5.signal.per_trade | -0.51 / -0.5080 move_bp | move_bp / move_bp | 一致 |
| 242 | −0.74 | move_bp | break_len_mult/fam_tables.md:61 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).15.signal.per_trade | -0.74 / -0.7434 move_bp | move_bp / move_bp | 一致 |
| 242 | −0.58 | move_bp | break_len_mult/fam_tables.md:61 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.signal.per_trade | -0.58 / -0.5757 move_bp | move_bp / move_bp | 一致 |
| 242 | +0.53 | move_bp | break_len_mult/fam_tables.md:61 / base/diag_paths.json d5.建てた合図(起点 = 建ての時刻).60.control_24h.per_trade | +0.53 / +0.5252 move_bp | move_bp / move_bp | 一致 |
| 242 | +0.03 | move_bp | break_len_mult/fam_tables.md:61 / base/diag_paths.json d5.建てた合図(起点 = 合図の時刻).5.control_24h.per_trade または d5.建てた合図(起点 = 建ての時刻).1.control_24h.per_trade または d5.建てた合図(起点 = 建ての時刻).60.control_24h.lo | +0.03 / +0.0305 move_bp | move_bp / move_bp | 一致 |
| 242 | +1.03 | move_bp | break_len_mult/fam_tables.md:61 / base/diag_paths.json d5.建てた合図(起点 = 合図の時刻).60.control_24h.hi または d5.建てた合図(起点 = 建ての時刻).60.control_24h.hi | +1.03 / +1.0279 move_bp | move_bp / move_bp | 一致 |
| 259 | +4.4 | 円 | break_len_mult/fam_tables.md:65 | +4.4 | 円 / bp(読み口) | 単位の誤り(出所の指し方: 書いた出所は読み口の「D6 固まり」(bp の diag_tables.md)だけで、× 20 とも写しの fam_tables.md とも書いていない。値は × 20 した円(fam_tables.md の D6)と合う) |
| 259 | +3.3 | 円 | break_len_mult/fam_tables.md:65 | +3.3 | 円 / bp(読み口) | 単位の誤り(出所の指し方: 書いた出所は読み口の「D6 固まり」(bp の diag_tables.md)だけで、× 20 とも写しの fam_tables.md とも書いていない。値は × 20 した円(fam_tables.md の D6)と合う) |
| 259 | +5.5 | 円 | break_len_mult/fam_tables.md:65 | +5.5 | 円 / bp(読み口) | 単位の誤り(出所の指し方: 書いた出所は読み口の「D6 固まり」(bp の diag_tables.md)だけで、× 20 とも写しの fam_tables.md とも書いていない。値は × 20 した円(fam_tables.md の D6)と合う) |
| 259 | +1.8 | 円 | break_len_mult/fam_tables.md:65 | +1.8 | 円 / bp(読み口) | 単位の誤り(出所の指し方: 書いた出所は読み口の「D6 固まり」(bp の diag_tables.md)だけで、× 20 とも写しの fam_tables.md とも書いていない。値は × 20 した円(fam_tables.md の D6)と合う) |
| 259 | −0.3 | 円 | break_len_mult/fam_tables.md:65 | -0.3 | 円 / bp(読み口) | 単位の誤り(出所の指し方: 書いた出所は読み口の「D6 固まり」(bp の diag_tables.md)だけで、× 20 とも写しの fam_tables.md とも書いていない。値は × 20 した円(fam_tables.md の D6)と合う) |
| 259 | +3.7 | 円 | break_len_mult/fam_tables.md:65 | +3.7 | 円 / bp(読み口) | 単位の誤り(出所の指し方: 書いた出所は読み口の「D6 固まり」(bp の diag_tables.md)だけで、× 20 とも写しの fam_tables.md とも書いていない。値は × 20 した円(fam_tables.md の D6)と合う) |
| 259 | −0.1 | 円 | break_len_mult/fam_tables.md:65 | -0.1 | 円 / bp(読み口) | 単位の誤り(出所の指し方: 書いた出所は読み口の「D6 固まり」(bp の diag_tables.md)だけで、× 20 とも写しの fam_tables.md とも書いていない。値は × 20 した円(fam_tables.md の D6)と合う) |
| 259 | −1.4 | 円 | break_len_mult/fam_tables.md:65 | -1.4 | 円 / bp(読み口) | 単位の誤り(出所の指し方: 書いた出所は読み口の「D6 固まり」(bp の diag_tables.md)だけで、× 20 とも写しの fam_tables.md とも書いていない。値は × 20 した円(fam_tables.md の D6)と合う) |
| 259 | +1.1 | 円 | break_len_mult/fam_tables.md:65 | +1.1 | 円 / bp(読み口) | 単位の誤り(出所の指し方: 書いた出所は読み口の「D6 固まり」(bp の diag_tables.md)だけで、× 20 とも写しの fam_tables.md とも書いていない。値は × 20 した円(fam_tables.md の D6)と合う) |
| 259 | +0.2 | 円 | break_len_mult/fam_tables.md:65 | +0.2 | 円 / bp(読み口) | 単位の誤り(出所の指し方: 書いた出所は読み口の「D6 固まり」(bp の diag_tables.md)だけで、× 20 とも写しの fam_tables.md とも書いていない。値は × 20 した円(fam_tables.md の D6)と合う) |
| 259 | −1.3 | 円 | break_len_mult/fam_tables.md:65 | -1.3 | 円 / bp(読み口) | 単位の誤り(出所の指し方: 書いた出所は読み口の「D6 固まり」(bp の diag_tables.md)だけで、× 20 とも写しの fam_tables.md とも書いていない。値は × 20 した円(fam_tables.md の D6)と合う) |
| 259 | +1.9 | 円 | break_len_mult/fam_tables.md:65 | +1.9 | 円 / bp(読み口) | 単位の誤り(出所の指し方: 書いた出所は読み口の「D6 固まり」(bp の diag_tables.md)だけで、× 20 とも写しの fam_tables.md とも書いていない。値は × 20 した円(fam_tables.md の D6)と合う) |
| 259 | +2.4 | 円 | break_len_mult/fam_tables.md:66 | +2.4 | 円 / bp(読み口) | 単位の誤り(出所の指し方: 書いた出所は読み口の「D6 固まり」(bp の diag_tables.md)だけで、× 20 とも写しの fam_tables.md とも書いていない。値は × 20 した円(fam_tables.md の D6)と合う) |
| 259 | +1.3 | 円 | break_len_mult/fam_tables.md:66 | +1.3 | 円 / bp(読み口) | 単位の誤り(出所の指し方: 書いた出所は読み口の「D6 固まり」(bp の diag_tables.md)だけで、× 20 とも写しの fam_tables.md とも書いていない。値は × 20 した円(fam_tables.md の D6)と合う) |
| 259 | +3.3 | 円 | break_len_mult/fam_tables.md:66 | +3.3 | 円 / bp(読み口) | 単位の誤り(出所の指し方: 書いた出所は読み口の「D6 固まり」(bp の diag_tables.md)だけで、× 20 とも写しの fam_tables.md とも書いていない。値は × 20 した円(fam_tables.md の D6)と合う) |
| 259 | −2.0 | 円 | break_len_mult/fam_tables.md:66 | -2.0 | 円 / bp(読み口) | 単位の誤り(出所の指し方: 書いた出所は読み口の「D6 固まり」(bp の diag_tables.md)だけで、× 20 とも写しの fam_tables.md とも書いていない。値は × 20 した円(fam_tables.md の D6)と合う) |
| 259 | −3.2 | 円 | break_len_mult/fam_tables.md:66 | -3.2 | 円 / bp(読み口) | 単位の誤り(出所の指し方: 書いた出所は読み口の「D6 固まり」(bp の diag_tables.md)だけで、× 20 とも写しの fam_tables.md とも書いていない。値は × 20 した円(fam_tables.md の D6)と合う) |
| 259 | −0.8 | 円 | break_len_mult/fam_tables.md:66 | -0.8 | 円 / bp(読み口) | 単位の誤り(出所の指し方: 書いた出所は読み口の「D6 固まり」(bp の diag_tables.md)だけで、× 20 とも写しの fam_tables.md とも書いていない。値は × 20 した円(fam_tables.md の D6)と合う) |
| 282 | +211.5 | 円 | break_len_mult/fam_tables.md:72 / break_len_mult_4/diag_tables.json d7.all.mean | +211.5 / +10.5743 bp(× 20 = +211.49 円) | 円 / bp | 一致 |
| 282 | +154.9 | 円 | break_len_mult/fam_tables.md:72 / break_len_mult_4/diag_tables.json d7.all.lo | +154.9 / +7.7437 bp(× 20 = +154.87 円) | 円 / bp | 一致 |
| 282 | +265.8 | 円 | break_len_mult/fam_tables.md:72 / break_len_mult_4/diag_tables.json d7.all.hi | +265.8 / +13.2903 bp(× 20 = +265.81 円) | 円 / bp | 一致 |
| 282 | 80.5 | 円 | break_len_mult/fam_tables.md:72 / break_len_mult_4/diag_tables.json d7.all.mde | +80.5 / +4.0257 bp(× 20 = +80.51 円) | 円 / bp | 一致 |
| 283 | +356 | 円 | break_len_mult/fam_tables.md:72 | +356 | 円 | 一致 |
| 283 | +264 | 円 | break_len_mult/fam_tables.md:72 | +264 | 円 | 一致 |
| 283 | +459 | 円 | break_len_mult/fam_tables.md:72 | +459 | 円 | 一致 |
| 283 | 140 | 円 | break_len_mult/fam_tables.md:72 | +140 | 円 | 一致 |
| 284 | +68 | 円 | break_len_mult/fam_tables.md:72 | +68 | 円 | 一致 |
| 284 | +10 | 円 | break_len_mult/fam_tables.md:72 | +10 | 円 | 一致 |
| 284 | +124 | 円 | break_len_mult/fam_tables.md:72 | +124 | 円 | 一致 |
| 284 | 83 | 円 | break_len_mult/fam_tables.md:72 | +83 | 円 | 一致 |
| 286 | −605 | 円 | break_len_mult/fam_tables.md:78 / break_len_mult_4/diag_tables.json d7.years.2015.mean | -605 / -30.2745 bp(× 20 = -605.49 円) | 円 / bp | 一致 |
| 286 | +52 | 円 | break_len_mult/fam_tables.md:78 / break_len_mult_4/diag_tables.json d7.years.2016.mean | +52 / +2.6230 bp(× 20 = +52.46 円) | 円 / bp | 一致 |
| 286 | +811 | 円 | break_len_mult/fam_tables.md:78 / break_len_mult_4/diag_tables.json d7.years.2017.mean | +811 / +40.5697 bp(× 20 = +811.39 円) | 円 / bp | 一致 |
| 286 | +442 | 円 | break_len_mult/fam_tables.md:78 / break_len_mult_4/diag_tables.json d7.years.2018.mean | +442 / +22.0791 bp(× 20 = +441.58 円) | 円 / bp | 一致 |
| 286 | +173 | 円 | break_len_mult/fam_tables.md:78 / break_len_mult_4/diag_tables.json d7.years.2019.mean | +173 / +8.6428 bp(× 20 = +172.86 円) | 円 / bp | 一致 |
| 286 | +181 | 円 | break_len_mult/fam_tables.md:78 / break_len_mult_4/diag_tables.json d7.years.2020.mean | +181 / +9.0279 bp(× 20 = +180.56 円) | 円 / bp | 一致 |
| 286 | +46 | 円 | break_len_mult/fam_tables.md:78 / break_len_mult_4/diag_tables.json d7.years.2021.mean | +46 / +2.2801 bp(× 20 = +45.60 円) | 円 / bp | 一致 |
| 286 | +40 | 円 | break_len_mult/fam_tables.md:78 / break_len_mult_4/diag_tables.json d7.years.2022.mean | +40 / +2.0133 bp(× 20 = +40.27 円) | 円 / bp | 一致 |
| 286 | +0 | 円 | break_len_mult/fam_tables.md:78 / break_len_mult_4/diag_tables.json d7.years.2023.mean | +0 / +0.0008 bp(× 20 = +0.02 円) | 円 / bp | 一致 |
| 288 | +205.5 | 円 | d7_fullperiod.out:11 | +205.5 | 円 | 一致 |
| 288 | +150.0 | 円 | d7_fullperiod.out:11 | +150.0 | 円 | 一致 |
| 288 | +263.2 | 円 | d7_fullperiod.out:11 | +263.2 | 円 | 一致 |
| 288 | +343 | 円 | d7_fullperiod.out:12 | +343.4 | 円 | 一致 |
| 288 | +246 | 円 | d7_fullperiod.out:12 | +245.7 | 円 | 一致 |
| 288 | +442 | 円 | d7_fullperiod.out:12 | +441.8 | 円 | 一致 |
| 288 | +68 | 円 | d7_fullperiod.out:13 | +67.6 | 円 | 一致 |
| 288 | +10 | 円 | d7_fullperiod.out:13 | +9.6 | 円 | 一致 |
| 288 | +124 | 円 | d7_fullperiod.out:13 | +124.0 | 円 | 一致 |
| 288 | −1,070 | 円 | d7_fullperiod.out:14 | -1070.4 | 円 | 一致 |
| 288 | −2,180 | 円 | d7_fullperiod.out:14 | -2179.8 | 円 | 一致 |
| 288 | −148 | 円 | d7_fullperiod.out:14 | -147.5 | 円 | 一致 |
| 290 | +487,589 | 円 | break_len_mult/fam_tables.md:84 / break_len_mult_4/diag_tables.json d7.match.sum_both_a_minus_b | +487,589 / +24379.4510 bp(× 20 = +487589.02 円) | 円 / bp | 一致 |
| 290 | +124,344 | 円 | break_len_mult/fam_tables.md:84 / break_len_mult_4/diag_tables.json d7.match.sum_only_a | +124,344 / +6217.1845 bp(× 20 = +124343.69 円) | 円 / bp | 一致 |
| 290 | +8,055 | 円 | break_len_mult/fam_tables.md:84 / break_len_mult_4/diag_tables.json d7.match.sum_only_b | +8,055 / +402.7281 bp(× 20 = +8054.56 円) | 円 / bp | 一致 |
| 296 | +0.4 | 円 | break_len_mult/band_migration.out:10(和 ÷ 本数・和の差 ÷ 日数を計算) | +0.36 | 円(計算) | 一致 |
| 296 | +2.6 | 円 | break_len_mult/band_migration.out:10(和 ÷ 本数・和の差 ÷ 日数を計算) | +2.60 | 円(計算) | 一致 |
| 296 | +192 | 円 | break_len_mult/band_migration.out:10(和 ÷ 本数・和の差 ÷ 日数を計算) | +192.37 | 円(計算) | 一致 |
| 297 | −104.4 | 円 | break_len_mult/band_migration.out:7(和 ÷ 本数・和の差 ÷ 日数を計算) | -104.39 | 円(計算) | 一致 |
| 297 | −43.0 | 円 | break_len_mult/band_migration.out:7(和 ÷ 本数・和の差 ÷ 日数を計算) | -43.05 | 円(計算) | 一致 |
| 297 | +97 | 円 | break_len_mult/band_migration.out:7(和 ÷ 本数・和の差 ÷ 日数を計算) | +97.22 | 円(計算) | 一致 |
| 298 | +15.6 | 円 | break_len_mult/band_migration.out:6(和 ÷ 本数・和の差 ÷ 日数を計算) | +15.62 | 円(計算) | 一致 |
| 298 | +15.3 | 円 | break_len_mult/band_migration.out:6(和 ÷ 本数・和の差 ÷ 日数を計算) | +15.35 | 円(計算) | 一致 |
| 298 | −9 | 円 | break_len_mult/band_migration.out:6(和 ÷ 本数・和の差 ÷ 日数を計算) | -8.54 | 円(計算) | 一致 |
| 299 | +19.1 | 円 | break_len_mult/band_migration.out:3(和 ÷ 本数・和の差 ÷ 日数を計算) | +19.15 | 円(計算) | 一致 |
| 299 | +3.5 | 円 | break_len_mult/band_migration.out:4(和 ÷ 本数・和の差 ÷ 日数を計算) | +3.51 | 円(計算) | 一致 |
| 299 | +54 | 円 | break_len_mult/band_migration.out:3(和 ÷ 本数・和の差 ÷ 日数を計算) | +53.51 | 円(計算) | 一致 |
| 299 | +25 | 円 | break_len_mult/band_migration.out:4(和 ÷ 本数・和の差 ÷ 日数を計算) | +24.81 | 円(計算) | 一致 |
| 300 | −4.2 | 円 | break_len_mult/band_migration.out:18(和 ÷ 本数・和の差 ÷ 日数を計算) | -4.19 | 円(計算) | 一致 |
| 300 | −3.7 | 円 | break_len_mult/band_migration.out:18(和 ÷ 本数・和の差 ÷ 日数を計算) | -3.71 | 円(計算) | 一致 |
| 300 | +43 | 円 | break_len_mult/band_migration.out:18(和 ÷ 本数・和の差 ÷ 日数を計算) | +43.37 | 円(計算) | 一致 |
| 301 | −86.2 | 円 | break_len_mult/band_migration.out:15(和 ÷ 本数・和の差 ÷ 日数を計算) | -86.21 | 円(計算) | 一致 |
| 301 | −65.4 | 円 | break_len_mult/band_migration.out:15(和 ÷ 本数・和の差 ÷ 日数を計算) | -65.42 | 円(計算) | 一致 |
| 301 | +29 | 円 | break_len_mult/band_migration.out:15(和 ÷ 本数・和の差 ÷ 日数を計算) | +28.69 | 円(計算) | 一致 |
| 302 | +9.1 | 円 | break_len_mult/band_migration.out:14(和 ÷ 本数・和の差 ÷ 日数を計算) | +9.11 | 円(計算) | 一致 |
| 302 | +8.6 | 円 | break_len_mult/band_migration.out:14(和 ÷ 本数・和の差 ÷ 日数を計算) | +8.56 | 円(計算) | 一致 |
| 302 | −14 | 円 | break_len_mult/band_migration.out:14(和 ÷ 本数・和の差 ÷ 日数を計算) | -14.15 | 円(計算) | 一致 |
| 303 | +10.7 | 円 | break_len_mult/band_migration.out:11(和 ÷ 本数・和の差 ÷ 日数を計算) | +10.69 | 円(計算) | 一致 |
| 303 | −2.2 | 円 | break_len_mult/band_migration.out:12(和 ÷ 本数・和の差 ÷ 日数を計算) | -2.22 | 円(計算) | 一致 |
| 303 | +21 | 円 | break_len_mult/band_migration.out:11(和 ÷ 本数・和の差 ÷ 日数を計算) | +21.24 | 円(計算) | 一致 |
| 303 | −15 | 円 | break_len_mult/band_migration.out:12(和 ÷ 本数・和の差 ÷ 日数を計算) | -14.92 | 円(計算) | 一致 |
| 305 | +344 | 円 | break_len_mult/band_migration.out:3-10 | 前半 8 升目: 本の和 +1,036,690 − 基準の和 +532,210 = +504,480 円 ÷ 1,469 = +343.42 | 円(計算) | 値の誤り(丸めで最後の桁が違う。和から計算すると +343.4(d7_fullperiod.out:12 の前半 +343.4 とも同じ)。文書の +344 は表示した升目の丸めた値(+54・+25・−1・−9・+97・−10・−4・+192)を足した値) |
| 305 | +67 | 円 | break_len_mult/band_migration.out:11-18 | 後半 8 升目: 本の和 −301,422 − 基準の和 −400,820 = +99,398 円 ÷ 1,470 = +67.62 | 円(計算) | 値の誤り(丸めで最後の桁が違う。和から計算すると +67.6 で丸めると +68。文書の +67 は表示した升目の丸めた値(+21・−15・−0・−14・+29・+6・−3・+43)を足した値) |
| 305 | +356 | 円 | break_len_mult/fam_tables.md:72 | +356 | 円 | 一致 |
| 305 | +16,834 | 円 | backtest_runs_shared/matilda_main_trades/base/trades.csv.gz(合図の日 < 2015-12-05 の行) | 20 本・pnl_jpy の和 +16,833.992(÷ 1,469 = +11.46) | 円(計算) | 一致(出力ファイルには無い。取引の行から計算し直して合う。文書の出所の記述は相方の記録(docs/RESEARCH/partner/2026-10-09_matilda_main_break_len_mult/01_D9b_reply.md:40)) |
| 305 | +68 | 円 | break_len_mult/fam_tables.md:72 | +68 | 円 | 一致 |
| 305 | 11.5 | 円/日 | backtest_runs_shared/matilda_main_trades/base/trades.csv.gz(合図の日 < 2015-12-05 の行) | +16,833.992 ÷ 1,469 = +11.46 | 円(計算) | 一致(出力ファイルには無い。取引の行から計算し直して合う) |
| 305 | 12 | 円/日 | break_len_mult/fam_tables.md:72・band_migration.out:3-10 | +356 − (+343.42) = +12.58 | 円(計算) | 値の誤り(丸めで最後の桁が違う。文書の 12 は +356 − (+344) で、+344 が表示した升目の丸めた値の和(305 行の +344 を見よ)) |
| 305 | 1 円/日未満 | 円/日 | break_len_mult_4/diag_tables.json d1.segments.first.n(1,465 日) | +356 × (1,469 − 1,465) ÷ 1,469 = 0.97 | 円(計算) | 一致(計算値。共通の日 1,465 と表の 1,469 日の分母の違いの大きさ) |
| 307 | +356 | 円 | break_len_mult/fam_tables.md:72 | +356 | 円 | 一致 |
| 307 | +264 | 円 | break_len_mult/fam_tables.md:72 | +264 | 円 | 一致 |
| 307 | +459 | 円 | break_len_mult/fam_tables.md:72 | +459 | 円 | 一致 |
| 307 | +68 | 円 | break_len_mult/fam_tables.md:72 | +68 | 円 | 一致 |
| 307 | +10 | 円 | break_len_mult/fam_tables.md:72 | +10 | 円 | 一致 |
| 307 | +124 | 円 | break_len_mult/fam_tables.md:72 | +124 | 円 | 一致 |
| 307 | +192 | 円 | break_len_mult/band_migration.out:10 | +192 | 円 | 一致 |
| 307 | +97 | 円 | break_len_mult/band_migration.out:7 | +97 | 円 | 一致 |
| 307 | +79 | 円 | break_len_mult/band_migration.out:3・4 | +78,610 + 36,449 = +115,059 円 ÷ 1,469 = +78.32 | 円(計算) | 値の誤り(丸めで最後の桁が違う。和から計算すると +78.3。文書の +79 は表示した 2 升目の丸めた値 +54・+25 を足した値) |
| 307 | +43 | 円 | break_len_mult/band_migration.out:18 | +43 | 円 | 一致 |
| 307 | +29 | 円 | break_len_mult/band_migration.out:15 | +29 | 円 | 一致 |
| 307 | +6 | 円 | break_len_mult/band_migration.out:11・12 | (+31,217 − 21,932) ÷ 1,470 = +6.32 | 円(計算) | 一致(計算値: 新しく建った取引の後半の分) |
| 308 | +487,589 | 円 | break_len_mult/fam_tables.md:84 / break_len_mult_4/diag_tables.json d7.match.sum_both_a_minus_b | +487,589 / +24379.4510 bp(× 20 = +487589.02 円) | 円 / bp | 一致 |
| 324 | −16 | 円 | both_halves.out:11 | -16 | 円 | 一致 |
| 324 | +68 | 円 | both_halves.out:12 | +68 | 円 | 一致 |
| 324 | +10 | 円 | both_halves.out:12 | +10 | 円 | 一致 |
| 324 | +124 | 円 | both_halves.out:12 | +124 | 円 | 一致 |
| 324 | +68 | 円 | both_halves.out:12 | +68 | 円 | 一致 |
| 324 | −16 | 円 | both_halves.out:11 | -16 | 円 | 一致 |
| 324 | +160 | 円 | both_halves.out:13 | +160 | 円 | 一致 |
| 325 | +181 | 円 | break_len_mult/fam_tables.md:29 | +181 | 円 | 一致 |
| 325 | +9 | 円 | break_len_mult/fam_tables.md:29 | +9 | 円 | 一致 |
| 325 | +351 | 円 | break_len_mult/fam_tables.md:29 | +351 | 円 | 一致 |
| 325 | +192 | 円 | break_len_mult/band_migration.out:10 | +192 | 円 | 一致 |
| 325 | +97 | 円 | break_len_mult/band_migration.out:7 | +97 | 円 | 一致 |
| 356 | +356 | 円 | break_len_mult/fam_tables.md:72 | +356 | 円 | 一致 |
| 356 | +68 | 円 | break_len_mult/fam_tables.md:72 | +68 | 円 | 一致 |
| 357 | +192 | 円 | break_len_mult/band_migration.out:10 | +192 | 円 | 一致 |
| 357 | +43 | 円 | break_len_mult/band_migration.out:18 | +43 | 円 | 一致 |
| 357 | +97 | 円 | break_len_mult/band_migration.out:7 | +97 | 円 | 一致 |
| 357 | +29 | 円 | break_len_mult/band_migration.out:15 | +29 | 円 | 一致 |
| 358 | +210 | 円 | break_len_mult/scene_diff.out:4 | +210 | 円 | 一致 |
| 358 | +356 | 円 | break_len_mult/scene_diff.out:6 | +356 | 円 | 一致 |
| 358 | +792 | 円 | break_len_mult/scene_diff.out:8 | +792 | 円 | 一致 |
| 359 | −259 | 円 | break_len_mult/compare.md:20 | -258.8 | 円 | 一致 |
| 359 | −343 | 円 | break_len_mult/compare.md:21 | -343.3 | 円 | 一致 |
| 360 | −1,531 | 円 | break_len_mult/fam_tables.md:21 / break_len_mult_4/diag_tables.json d1.rows[1].mean | -1,531 / -76.5386 bp(× 20 = -1530.77 円) | 円 / bp | 一致 |
| 360 | −605 | 円 | break_len_mult/fam_tables.md:78 / break_len_mult_4/diag_tables.json d7.years.2015.mean | -605 / -30.2745 bp(× 20 = -605.49 円) | 円 / bp | 一致 |
| 361 | −9 | 円 | break_len_mult/band_migration.out:6(和 ÷ 本数・和の差 ÷ 日数を計算) | -8.54 | 円(計算) | 一致 |
| 361 | −14 | 円 | break_len_mult/band_migration.out:14(和 ÷ 本数・和の差 ÷ 日数を計算) | -14.15 | 円(計算) | 一致 |
| 361 | +15.6 | 円 | break_len_mult/band_migration.out:6(和 ÷ 本数・和の差 ÷ 日数を計算) | +15.62 | 円(計算) | 一致 |
| 361 | +15.3 | 円 | break_len_mult/band_migration.out:6(和 ÷ 本数・和の差 ÷ 日数を計算) | +15.35 | 円(計算) | 一致 |
| 361 | +9.1 | 円 | break_len_mult/band_migration.out:14(和 ÷ 本数・和の差 ÷ 日数を計算) | +9.11 | 円(計算) | 一致 |
| 361 | +8.6 | 円 | break_len_mult/band_migration.out:14(和 ÷ 本数・和の差 ÷ 日数を計算) | +8.56 | 円(計算) | 一致 |
| 361 | −156.2 | 円 | break_len_mult/levels_reason.out:4 | -156.2 | 円 | 一致 |
| 361 | −134.6 | 円 | break_len_mult/levels_reason.out:14 | -134.6 | 円 | 一致 |
| 385 | +708 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.first.mean | +708 / +35.3819 bp(× 20 = +707.64 円) | 円 / bp | 一致 |
| 385 | +532 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.first.lo | +532 / +26.5774 bp(× 20 = +531.55 円) | 円 / bp | 一致 |
| 385 | +889 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.first.hi | +889 / +44.4456 bp(× 20 = +888.91 円) | 円 / bp | 一致 |
| 385 | −205 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.second.mean | -205 / -10.2524 bp(× 20 = -205.05 円) | 円 / bp | 一致 |
| 385 | −303 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.second.lo | -303 / -15.1669 bp(× 20 = -303.34 円) | 円 / bp | 一致 |
| 385 | −110 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.second.hi | -110 / -5.5234 bp(× 20 = -110.47 円) | 円 / bp | 一致 |
| 386 | +362 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.segments.first.mean | +362 / +18.1147 bp(× 20 = +362.29 円) | 円 / bp | 一致 |
| 386 | +231 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.segments.first.lo | +231 / +11.5545 bp(× 20 = +231.09 円) | 円 / bp | 一致 |
| 386 | +497 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.segments.first.hi | +497 / +24.8558 bp(× 20 = +497.12 円) | 円 / bp | 一致 |
| 386 | −273 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.segments.second.mean | -273 / -13.6334 bp(× 20 = -272.67 円) | 円 / bp | 一致 |
| 386 | −360 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.segments.second.lo | -360 / -17.9998 bp(× 20 = -360.00 円) | 円 / bp | 一致 |
| 386 | −184 | 円 | break_len_mult/fam_tables.md:15 / base/diag_tables.json d1.segments.second.hi | -184 / -9.1933 bp(× 20 = -183.87 円) | 円 / bp | 一致 |
| 399 | +211.5 | 円 | break_len_mult/fam_tables.md:72 / break_len_mult_4/diag_tables.json d7.all.mean | +211.5 / +10.5743 bp(× 20 = +211.49 円) | 円 / bp | 一致 |
| 399 | +154.9 | 円 | break_len_mult/fam_tables.md:72 / break_len_mult_4/diag_tables.json d7.all.lo | +154.9 / +7.7437 bp(× 20 = +154.87 円) | 円 / bp | 一致 |
| 399 | +265.8 | 円 | break_len_mult/fam_tables.md:72 / break_len_mult_4/diag_tables.json d7.all.hi | +265.8 / +13.2903 bp(× 20 = +265.81 円) | 円 / bp | 一致 |
| 399 | 80.5 | 円 | break_len_mult/fam_tables.md:72 / break_len_mult_4/diag_tables.json d7.all.mde | +80.5 / +4.0257 bp(× 20 = +80.51 円) | 円 / bp | 一致 |
| 399 | +356 | 円 | break_len_mult/fam_tables.md:72 | +356 | 円 | 一致 |
| 399 | +264 | 円 | break_len_mult/fam_tables.md:72 | +264 | 円 | 一致 |
| 399 | +459 | 円 | break_len_mult/fam_tables.md:72 | +459 | 円 | 一致 |
| 399 | +68 | 円 | break_len_mult/fam_tables.md:72 | +68 | 円 | 一致 |
| 399 | +10 | 円 | break_len_mult/fam_tables.md:72 | +10 | 円 | 一致 |
| 399 | +124 | 円 | break_len_mult/fam_tables.md:72 | +124 | 円 | 一致 |
| 399 | +52 | 円 | break_len_mult/fam_tables.md:78 / break_len_mult_4/diag_tables.json d7.years.2016.mean | +52 / +2.6230 bp(× 20 = +52.46 円) | 円 / bp | 一致 |
| 399 | +442 | 円 | break_len_mult/fam_tables.md:78 / break_len_mult_4/diag_tables.json d7.years.2018.mean | +442 / +22.0791 bp(× 20 = +441.58 円) | 円 / bp | 一致 |
| 399 | +181 | 円 | break_len_mult/fam_tables.md:78 / break_len_mult_4/diag_tables.json d7.years.2020.mean | +181 / +9.0279 bp(× 20 = +180.56 円) | 円 / bp | 一致 |
| 399 | +40 | 円 | break_len_mult/fam_tables.md:78 / break_len_mult_4/diag_tables.json d7.years.2022.mean | +40 / +2.0133 bp(× 20 = +40.27 円) | 円 / bp | 一致 |
| 399 | +0 | 円 | break_len_mult/fam_tables.md:78 / break_len_mult_4/diag_tables.json d7.years.2023.mean | +0 / +0.0008 bp(× 20 = +0.02 円) | 円 / bp | 一致 |
| 403 | −205 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.second.mean | -205 / -10.2524 bp(× 20 = -205.05 円) | 円 / bp | 一致 |
| 403 | −303 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.second.lo | -303 / -15.1669 bp(× 20 = -303.34 円) | 円 / bp | 一致 |
| 403 | −110 | 円 | break_len_mult/fam_tables.md:14 / break_len_mult_4/diag_tables.json d1.segments.second.hi | -110 / -5.5234 bp(× 20 = -110.47 円) | 円 / bp | 一致 |
| 403 | +356 | 円 | break_len_mult/fam_tables.md:72 | +356 | 円 | 一致 |
| 403 | +264 | 円 | break_len_mult/fam_tables.md:72 | +264 | 円 | 一致 |
| 403 | +459 | 円 | break_len_mult/fam_tables.md:72 | +459 | 円 | 一致 |
| 403 | +68 | 円 | break_len_mult/fam_tables.md:72 | +68 | 円 | 一致 |
| 403 | +10 | 円 | break_len_mult/fam_tables.md:72 | +10 | 円 | 一致 |
| 403 | +124 | 円 | break_len_mult/fam_tables.md:72 | +124 | 円 | 一致 |
| 403 | +68 | 円 | break_len_mult/fam_tables.md:72 | +68 | 円 | 一致 |
| 403 | −16 | 円 | both_halves.out:11 | -16 | 円 | 一致 |
| 403 | +160 | 円 | both_halves.out:13 | +160 | 円 | 一致 |
| 403 | +192 | 円 | break_len_mult/band_migration.out:10 | +192 | 円 | 一致 |
| 403 | +43 | 円 | break_len_mult/band_migration.out:18 | +43 | 円 | 一致 |
| 403 | +97 | 円 | break_len_mult/band_migration.out:7 | +97 | 円 | 一致 |
| 403 | +29 | 円 | break_len_mult/band_migration.out:15 | +29 | 円 | 一致 |
| 403 | −259 | 円 | break_len_mult/compare.md:20 | -258.8 | 円 | 一致 |
| 403 | −343 | 円 | break_len_mult/compare.md:21 | -343.3 | 円 | 一致 |
| 403 | +210 | 円 | break_len_mult/scene_diff.out:4 | +210 | 円 | 一致 |
| 403 | +356 | 円 | break_len_mult/fam_tables.md:72 | +356 | 円 | 一致 |
| 403 | +792 | 円 | break_len_mult/scene_diff.out:8 | +792 | 円 | 一致 |

