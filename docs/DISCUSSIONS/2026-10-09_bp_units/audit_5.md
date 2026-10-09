# 数の突き合わせ 5(range_lo・range_hi・vola_gate の分析の文書)

作業者が書いた(2026-10-09)。読むだけの仕事。文書・台帳・コードは何も変えていない。

## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 3 つの文書の `>` でない行の損益・値動きの数を全部拾い、出所の出力の値・単位と 1 つずつ突き合わせる | 「**もっと徹底的に調べて影響範囲を確定させてください。**」 |
| 判定(一致 / 単位の誤り / 値の誤り / 出所が無い / 確かめられない)を付けてこのファイルに書く | 「**もっと徹底的に調べて影響範囲を確定させてください。**」 |
| 突き合わせを台本(scratchpad の Python)で機械的に行い、合わないものを手で読む | **(該当語なし)**(手段の選択。リードの委任文の「機械的に確かめる」に従った) |

見込み時間: 約 80 分(内訳: 3 文書と出所の読み 15 分 / 突き合わせの台本 20 分 / 台本で合わないものを手で読む 30 分 / このファイルを書く 15 分)。上限 90 分。実際: 約 90 分(台本の直しに見込みより時間がかかった)。

## 結果(判定ごとの個数)

| 文書 | 拾った数 | 一致 | 単位の誤り | 値の誤り | 出所が無い・見つからない | 確かめられない |
|---|---|---|---|---|---|---|
| range_lo | 636 | 620 | 16 | 0 | 0 | 0 |
| range_hi | 567 | 551 | 16 | 0 | 0 | 0 |
| vola_gate | 602 | 598 | 4 | 0 | 0 | 0 |
| 計 | 1,805 | 1,769 | 36 | 0 | 0 | 0 |

「一致」の内訳(各文書の節の頭に個数):
- 一致: 出所の同じ変種の行に同じ数がある(円は ×1、bp の出所は × 20、move_bp は ×1)。
- 一致(出所の行から計算して合う): 文書の数が出所の 2 行の和・和 ÷ 本数・符号の反転などで、計算を出所の欄に書いた(range_lo 35・range_hi 16・vola_gate 11)。
- 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある): range_hi 20・vola_gate 32。range_hi の行 188 と vola_gate の行 190・192 の保有 0 分の帯の前半・後半は `fam_tables.md` の D3 にだけあるが、節の頭(両文書の行 175)は `compare.md` と「読み口の D3」だけを指している。円の値で、単位は合っている(単位の誤りではない)。
- 一致(散文。値の照合だけ。出所の行は機械が選んだもの): D9・D9b・D10 の散文で変種が書いていない数(range_lo 21・range_hi 8・vola_gate 34)。値は出所のどこかに同じ数があるが、指した行が意味の同じ行かは手で全部は確かめていない(下の「確かめきれなかった範囲」)。

**単位の誤り 36 件は全部「指し方」の誤り**(円の値の出所として bp のファイルだけを指した。値そのものは × 20 で合う)。**bp の値を円と書いた・円の値を bp と書いた数は見つからなかった。** 値の誤り(× 20 しても合わない・写し間違い・丸めの最後の桁)も 0。

### 単位の誤りの一覧(行番号つき)

| 文書 | 行 | 数(個数) | 文書の書き方 | 出所の単位 | 円の写しのある所 |
|---|---|---|---|---|---|
| range_lo | 284 | D6 の 1 取引あたり +2.6 [+1.3, +3.7]・+3.0 [+1.5, +4.4]・+4.2 [+1.9, +6.4]・−1.9・−1.9・−1.3 [−4.1, +1.2]・基準 +2.4・−2.0(16) | 「読み口の「D6 固まり」(1 取引あたり 円 [区間]…)」 | 読み口 = `range_lo_<v>/diag_tables.md` の D6 は bp(例 p50 〜1 分 +0.21 [+0.09, +0.32] bp × 20 = +4.2 [+1.8, +6.4]) | `range_lo/fam_tables.md:101-105`(円。指していない) |
| range_hi | 223・224・225 | D4 の和: 勝った +6,091,255・+8,192,321・+10,177,344、負けた 2 群 −6,513,787・−8,669,685・−10,701,050(6) | 行 219「`range_hi_<v>/diag_paths.md`(move_bp。母数は…。和は円)」 | `diag_paths.md` の D4 の「損益の和」は pnl_bp(例 p75 勝った +304563 bp × 20 = +6,091,260) | `range_hi/fam_tables.md:54-68`(円。指していない)。UNITS_MAP §3 の 3 つ目の項と同じもの |
| range_hi | 270 | D6 の 1 取引あたり +1.4 [+0.7, +2.0]・+1.9 [+1.2, +2.6]・−2.0・−2.1・−1.8・−1.3(10) | 「読み口の「D6 固まり」(1 取引あたり 円 [区間]…)」 | 読み口 = `range_hi_<v>/diag_tables.md` の D6 は bp(例 p75 〜1 分 +0.07 [+0.03, +0.10]) | `range_hi/fam_tables.md` の D6(円。指していない) |
| vola_gate | 192 | 上位・下位 5% の日の和 +640,619〜+653,497・−698,735〜−766,805(4) | 節の頭の行 175「`vola_gate/compare.md`(円)と読み口の D3」 | 読み口 = `vola_gate_p50/diag_tables.md:44`・`base/diag_tables.md:44` は bp(+32031 bp × 20 = +640,620) | `vola_gate/fam_tables.md:47-48`(円。指していない) |

判定の決め方(3 文書で同じに当てた): 文書が円の数の出所として bp のファイル(`diag_tables.md`・`diag_paths.md` の D4 の和・`blocked_*.md` の D4 の和)を指し、同じ節に「bp/日 × 20 = 円」の断りも円の写し(`fam_tables.md`)の指しも無いときは「単位の誤り(指し方)」にした。断りか写しの指しがあれば一致にした(range_lo の D1・D7 の「bp/日 × 20 = 円」、range_lo の D3「読み口の D3(写しは fam_tables.md)」、range_lo の D4「写しは fam_tables.md の D4」、range_hi・vola_gate の D1「bp/日 × 20 = 円」、vola_gate の D4・D6「fam_tables.md の D4 / D6」)。リードの委任文の例「円の値の出所に bp のファイルを指した」に当てた。

### 気づいたこと(判定は変えない。値は出所と合う)

- range_hi の行 30 の `both_halves.out` の前半 p75 −176・p90 −101 は、基準と本の共通の日だけで差を取った値(`both_halves.out` の 1 行目の注記・UNITS_MAP §3 の 1 つ目)。文書は「前提を書く前に見たもの」として当時の値を書いており、D7(行 291)と D10 の表 3 は `d7_fullperiod.out` の直した値(−190・−115)を使っている。出所の値どおりなので一致にした。
- range_hi の D7 の表(行 291-293)の MDE(84.9・155・88 など)は `d7_fullperiod.out` ではなく読み口(`range_hi/fam_tables.md:98-99`)の値。文書は行 287 で「MDE は読み口の値のまま」と書いている。
- range_hi の D10 の表 3 の年(2016〜2023)の値は読み口(共通の日)の `fam_tables.md:106-108`。共通の日で落ちるのは 2015-12-01〜07 だけなので、2016 年以降の年の値は落としの影響を受けない(2015 年の列は表 3 に無い)。
- range_lo の行 323・426 の「基準の取引は前半に保有 0 分 +72・足の後 +67 円/日を稼ぎ、後半は保有 0 分 +18・足の後 −212 円/日」は、`band_migration.out` の差(−72・−67・−18・+212。差 = −基準の和)の符号を反転した値。計算を出所の欄に書いて一致にした。
- 拾った数の中に、MFE・MAE・出の後・D5 の move_bp を円と書いたものは無かった(D4・D5 の小さい数は全部 move_bp の出所で合った)。

## 拾い方・判定のしかた

- 対象: 各文書の、行頭が `>` でない行。表の升は、列の見出しが本数・取引・割合・とんとん・差(ポイント)・母数・日数などのものを除いた。D4 の「本 / 和 / MFE・MAE」の升は先頭の本数を除いた。散文は符号付きの数と、「MDE」の後・「円」の前の符号なしの数を拾った。本・%・分・日・年・回などが後に付く数、日付・時刻・`:551` のような行番号、K-・L- の番号は除いた。
- 対象外にした数: 行 29(3 文書とも「1 bp = 20 円」の定義の 20)、D10 の表 2 と D3 の読みの散文の「利確で閉じる割合 − 取引のとんとん」(ポイント。損益ではない。range_lo 行 212・411-414、range_hi 行 201・409-412、vola_gate 行 192・418-421)。
- 出所での探し方: `docs/RESEARCH/matilda_main/` の族の置き場・`<族>_<本>/`・`base/` と、上の階の `both_halves.out`・`d7_fullperiod.out`・`held_blocked.out`・`gate_dist_halves.out`・`base_scenes.out`(range_hi・vola_gate は range_lo の置き場も)の数を全部拾い、文書の数と比べた。比べる幅は「文書の表示の半桁 + 出所の表示の半桁(× 20 のときは × 20)」より小さいこと(両方の丸めの幅が重なる)。同じ桁の円どうしは同じ数のときだけ合う。
- 変種の合わせ: 表の行・列の頭(p10・p75・none・base など)と、散文はその数より前に書いた変種の語で、出所の行の変種(行の名前・置き場の名前・塊の見出し)と合わせた。合わない行の同じ数は使っていない。
- 出所の優先: 節ごとに出所の候補を決め(D1 は `fam_tables.md` と `diag_tables.md`、D5 は `blocked_*.md`、D7 は `d7_fullperiod.out`・`band_migration.out`・`fam_tables.md` など)、その順で最初に合った行を「出所」に書いた。
- 合わなかった数(各文書 15〜60 個)は全部手で開いて確かめた(計算・符号の反転・散文の変種の読み違い)。手で決めたものは出所の欄に計算を書いた。

## 打ったコマンド(主なもの)

```
# 台本(読むだけ)。置き場は scratchpad/a5/
python3 -I match5.py <文書> <族> m_<族>.json      # 文書の数を拾い、出所の数と比べる
python3 -I judge5.py <族> m_<族>.json j_<族>.json  # 節ごとの出所と指し方で判定
python3 -I gen5.py > body.md                        # 手で確かめた分を上書きして表にする
# 手の確かめ(例)
cat -n docs/RESEARCH/matilda_main/range_lo/fam_tables.md
cat -n docs/RESEARCH/matilda_main/range_lo_p50/diag_tables.md docs/RESEARCH/matilda_main/range_lo_p50/diag_paths.md
grep -n "負けた" docs/RESEARCH/matilda_main/{range_lo,range_hi,vola_gate}/fam_tables.md
sed -n 11,14p docs/RESEARCH/matilda_main/range_hi_p75/diag_paths.md
grep -n "11 分超\|〜1 分\|3 分超" docs/RESEARCH/matilda_main/range_hi_p75/diag_tables.md docs/RESEARCH/matilda_main/range_hi_p90/diag_tables.md
python3 -c "print(-4601157-5812359, (106167+98442)/106468, (26115-312028)/1470, 278550/7594, -159303/33412, -46431/1469)"
```

計算の出力(抜き): `-10413516`、`1.9217887064657926`、`-194.49863945578232`、`36.68027390044772`、`-4.767837902549982`、`-31.6072157930565`。

## 確かめきれなかった範囲と理由

- 「一致(散文。値の照合だけ…)」の 63 個(range_lo 21・range_hi 8・vola_gate 34。D9・D9b・D10 の散文と D9b の観察の升で、変種の語が無い数)は、同じ数が出所の置き場のどこかにあることだけを確かめた。指した行が意味の同じ行かは 1 つずつは開いていない(例: range_hi 行 64 の +110 は機械が `fam_tables.md:36` を選んだが、意味の同じ行は `fam_tables.md:108` の none − base 2017 で、そちらも +110。値は合う)。ここに値の誤りが隠れている可能性は 0 とは言えない。
- 散文で変種の語がある数も、機械が選んだ出所の行が同じ数の別の行のことがある(例: range_lo 行 264 の −0.41 は `fam_tables.md:86` の区間の端を選んだが、意味の同じ行は `blocked_range_lo_p50.md` の建てた合図 1 分 −0.41)。判定(一致)は変わらないが、出所の欄の行は意味の同じ行と限らない。
- `summary.json`(行 55・56 の損益の和)は開いていない。`fam_tables.md` の D0 の円の和と比べた。
- json の出力(`diag_tables.json`・`diag_paths.json`)は開いていない。md の表示の値で比べた。
- 範囲は 3 文書の全部の行(`>` の行を除く)。1 回目の台本は D9b の表の「観察」の列を見出しで飛ばしていた(range_lo 373-377・range_hi 370-376・vola_gate 377-385)。気づいて拾い直し、そこの数も上の表に入れた(range_lo +15・range_hi +18・vola_gate +13 個)。読むのをやめた範囲は無い。

## range_lo(`docs/ANALYSIS/2026-10-09_matilda_main_range_lo.md`)

拾った数: 636。判定ごと: 一致 620・単位の誤り 16

細かい判定の内訳: 一致 564・一致(出所の行から計算して合う) 35・一致(散文。値の照合だけ。出所の行は機械が選んだもの) 21・単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) 16

### range_lo: 一致以外

| 文書の行 | 書かれた数 | 判定 | 出所 | 出所の値 | 理由 |
|---|---|---|---|---|---|
| 284 | +2.6 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_lo/fam_tables.md:102 | +2.6 | D6 の行 284 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp。円の写しの fam_tables.md の D6 を指していない |
| 284 | +1.3 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_lo/fam_tables.md:102 | +1.3 | D6 の行 284 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp。円の写しの fam_tables.md の D6 を指していない |
| 284 | +3.7 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_lo/fam_tables.md:102 | +3.7 | D6 の行 284 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp。円の写しの fam_tables.md の D6 を指していない |
| 284 | +3.0 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_lo/fam_tables.md:52 | 3 | D6 の行 284 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp。円の写しの fam_tables.md の D6 を指していない |
| 284 | +1.5 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_lo/fam_tables.md:103 | +1.5 | D6 の行 284 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp。円の写しの fam_tables.md の D6 を指していない |
| 284 | +4.4 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_lo/fam_tables.md:103 | +4.4 | D6 の行 284 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp。円の写しの fam_tables.md の D6 を指していない |
| 284 | +4.2 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_lo/fam_tables.md:104 | +4.2 | D6 の行 284 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp。円の写しの fam_tables.md の D6 を指していない |
| 284 | +1.9 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_lo/fam_tables.md:104 | +1.9 | D6 の行 284 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp。円の写しの fam_tables.md の D6 を指していない |
| 284 | +6.4 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_lo/fam_tables.md:54 | +6.4 | D6 の行 284 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp。円の写しの fam_tables.md の D6 を指していない |
| 284 | −1.9 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_lo/fam_tables.md:102 | -1.9 | D6 の行 284 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp。円の写しの fam_tables.md の D6 を指していない |
| 284 | −1.9 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_lo/fam_tables.md:103 | -1.9 | D6 の行 284 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp。円の写しの fam_tables.md の D6 を指していない |
| 284 | −1.3 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_lo/fam_tables.md:104 | -1.3 | D6 の行 284 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp。円の写しの fam_tables.md の D6 を指していない |
| 284 | −4.1 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_lo/fam_tables.md:104 | -4.1 | D6 の行 284 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp。円の写しの fam_tables.md の D6 を指していない |
| 284 | +1.2 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_lo/fam_tables.md:104 | +1.2 | D6 の行 284 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp。円の写しの fam_tables.md の D6 を指していない |
| 284 | +2.4 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_lo/fam_tables.md:105 | +2.4 | D6 の行 284 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp。円の写しの fam_tables.md の D6 を指していない |
| 284 | −2.0 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_lo/fam_tables.md:105 | -2.0 | D6 の行 284 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp。円の写しの fam_tables.md の D6 を指していない |

### range_lo: 全部の数

| 文書の行 | 書かれた数 | 書かれた単位 | 出所 ファイル:行 | 出所の値 | 出所の単位 | 判定 |
|---|---|---|---|---|---|---|
| 30 | +0 | 円 | both_halves.out:25 | +0 | 円 | 一致 |
| 30 | +0 | 円 | both_halves.out:25 | +0 | 円 | 一致 |
| 30 | −28 | 円 | both_halves.out:26 | -28 | 円 | 一致 |
| 30 | +19 | 円 | both_halves.out:26 | +19 | 円 | 一致 |
| 30 | −59 | 円 | both_halves.out:27 | -59 | 円 | 一致 |
| 30 | +83 | 円 | both_halves.out:27 | +83 | 円 | 一致 |
| 30 | −107 | 円 | both_halves.out:28 | -107 | 円 | 一致 |
| 30 | +199 | 円 | both_halves.out:28 | +199 | 円 | 一致 |
| 56 | +131,462 | 円 | range_lo/fam_tables.md:50 | +131,462 | 円 | 一致 |
| 56 | +119,071 | 円 | range_lo/fam_tables.md:51 | +119,071 | 円 | 一致 |
| 56 | +166,669 | 円 | range_lo/fam_tables.md:52 | +166,669 | 円 | 一致 |
| 56 | +267,101 | 円 | range_lo/fam_tables.md:53 | +267,101 | 円 | 一致 |
| 67 | +0 | 円 | range_lo/fam_tables.md:7 | 0 | 円 | 一致 |
| 86 | −156 | 円 | range_lo/market_side.out:1 | -156 | 円 | 一致 |
| 86 | +22 | 円 | range_lo/market_side.out:2 | 22 | 円 | 一致 |
| 86 | +134 | 円 | range_lo/market_side.out:3 | 134 | 円 | 一致 |
| 86 | −216 | 円 | range_lo/market_side.out:4 | -216 | 円 | 一致 |
| 114 | +362 | 円 | range_lo/fam_tables.md:17 | +362 | 円 | 一致 |
| 114 | +231 | 円 | range_lo/fam_tables.md:17 | +231 | 円 | 一致 |
| 114 | +497 | 円 | range_lo/fam_tables.md:17 | +497 | 円 | 一致 |
| 114 | 195 | 円 | range_lo/fam_tables.md:17 | +195 | 円 | 一致 |
| 114 | −273 | 円 | range_lo/fam_tables.md:17 | -273 | 円 | 一致 |
| 114 | −360 | 円 | range_lo/fam_tables.md:17 | -360 | 円 | 一致 |
| 114 | −184 | 円 | range_lo/fam_tables.md:17 | -184 | 円 | 一致 |
| 114 | 125 | 円 | range_lo/fam_tables.md:17 | +125 | 円 | 一致 |
| 114 | −635 | 円 | range_lo/fam_tables.md:17 | -635 | 円 | 一致 |
| 114 | −805 | 円 | range_lo/fam_tables.md:17 | -805 | 円 | 一致 |
| 114 | −476 | 円 | range_lo/fam_tables.md:17 | -476 | 円 | 一致 |
| 114 | +45 | 円 | range_lo/fam_tables.md:17 | +45 | 円 | 一致 |
| 114 | −41 | 円 | range_lo/fam_tables.md:17 | -41 | 円 | 一致 |
| 114 | +124 | 円 | range_lo/fam_tables.md:17 | +124 | 円 | 一致 |
| 115 | +335 | 円 | range_lo/fam_tables.md:18 | +335 | 円 | 一致 |
| 115 | +208 | 円 | range_lo/fam_tables.md:18 | +208 | 円 | 一致 |
| 115 | +472 | 円 | range_lo/fam_tables.md:18 | +472 | 円 | 一致 |
| 115 | 194 | 円 | range_lo/fam_tables.md:18 | +194 | 円 | 一致 |
| 115 | −253 | 円 | range_lo/fam_tables.md:18 | -253 | 円 | 一致 |
| 115 | −341 | 円 | range_lo/fam_tables.md:18 | -341 | 円 | 一致 |
| 115 | −163 | 円 | range_lo/fam_tables.md:18 | -163 | 円 | 一致 |
| 115 | 125 | 円 | range_lo/fam_tables.md:18 | +125 | 円 | 一致 |
| 115 | −588 | 円 | range_lo/fam_tables.md:18 | -588 | 円 | 一致 |
| 115 | −755 | 円 | range_lo/fam_tables.md:18 | -755 | 円 | 一致 |
| 115 | −430 | 円 | range_lo/fam_tables.md:18 | -430 | 円 | 一致 |
| 115 | +41 | 円 | range_lo/fam_tables.md:18 | +41 | 円 | 一致 |
| 115 | −44 | 円 | range_lo/fam_tables.md:18 | -44 | 円 | 一致 |
| 115 | +120 | 円 | range_lo/fam_tables.md:18 | +120 | 円 | 一致 |
| 116 | +303 | 円 | range_lo/fam_tables.md:19 | +303 | 円 | 一致 |
| 116 | +180 | 円 | range_lo/fam_tables.md:19 | +180 | 円 | 一致 |
| 116 | +438 | 円 | range_lo/fam_tables.md:19 | +438 | 円 | 一致 |
| 116 | 189 | 円 | range_lo/fam_tables.md:19 | +189 | 円 | 一致 |
| 116 | −190 | 円 | range_lo/fam_tables.md:19 | -190 | 円 | 一致 |
| 116 | −277 | 円 | range_lo/fam_tables.md:19 | -277 | 円 | 一致 |
| 116 | −105 | 円 | range_lo/fam_tables.md:19 | -105 | 円 | 一致 |
| 116 | 121 | 円 | range_lo/fam_tables.md:19 | +121 | 円 | 一致 |
| 116 | −493 | 円 | range_lo/fam_tables.md:19 | -493 | 円 | 一致 |
| 116 | −652 | 円 | range_lo/fam_tables.md:19 | -652 | 円 | 一致 |
| 116 | −327 | 円 | range_lo/fam_tables.md:19 | -327 | 円 | 一致 |
| 116 | +57 | 円 | range_lo/fam_tables.md:19 | +57 | 円 | 一致 |
| 116 | −27 | 円 | range_lo/fam_tables.md:19 | -27 | 円 | 一致 |
| 116 | +132 | 円 | range_lo/fam_tables.md:19 | +132 | 円 | 一致 |
| 117 | +255 | 円 | range_lo/fam_tables.md:20 | +255 | 円 | 一致 |
| 117 | +142 | 円 | range_lo/fam_tables.md:20 | +142 | 円 | 一致 |
| 117 | +384 | 円 | range_lo/fam_tables.md:20 | +384 | 円 | 一致 |
| 117 | 176 | 円 | range_lo/fam_tables.md:20 | +176 | 円 | 一致 |
| 117 | −73 | 円 | range_lo/fam_tables.md:20 | -73 | 円 | 一致 |
| 117 | −153 | 円 | range_lo/fam_tables.md:20 | -153 | 円 | 一致 |
| 117 | +4 | 円 | range_lo/fam_tables.md:20 | +4 | 円 | 一致 |
| 117 | 112 | 円 | range_lo/fam_tables.md:20 | +112 | 円 | 一致 |
| 117 | −328 | 円 | range_lo/fam_tables.md:20 | -328 | 円 | 一致 |
| 117 | −479 | 円 | range_lo/fam_tables.md:20 | -479 | 円 | 一致 |
| 117 | −173 | 円 | range_lo/fam_tables.md:20 | -173 | 円 | 一致 |
| 117 | +91 | 円 | range_lo/fam_tables.md:20 | +91 | 円 | 一致 |
| 117 | +14 | 円 | range_lo/fam_tables.md:20 | +14 | 円 | 一致 |
| 117 | +163 | 円 | range_lo/fam_tables.md:20 | +163 | 円 | 一致 |
| 118 | +362 | 円 | range_lo/fam_tables.md:21 | +362 | 円 | 一致 |
| 118 | +231 | 円 | range_lo/fam_tables.md:21 | +231 | 円 | 一致 |
| 118 | +497 | 円 | range_lo/fam_tables.md:21 | +497 | 円 | 一致 |
| 118 | 195 | 円 | range_lo/fam_tables.md:21 | +195 | 円 | 一致 |
| 118 | −273 | 円 | range_lo/fam_tables.md:21 | -273 | 円 | 一致 |
| 118 | −360 | 円 | range_lo/fam_tables.md:21 | -360 | 円 | 一致 |
| 118 | −184 | 円 | range_lo/fam_tables.md:21 | -184 | 円 | 一致 |
| 118 | 125 | 円 | range_lo/fam_tables.md:21 | +125 | 円 | 一致 |
| 118 | −635 | 円 | range_lo/fam_tables.md:21 | -635 | 円 | 一致 |
| 118 | −805 | 円 | range_lo/fam_tables.md:21 | -805 | 円 | 一致 |
| 118 | −476 | 円 | range_lo/fam_tables.md:21 | -476 | 円 | 一致 |
| 118 | +45 | 円 | range_lo/fam_tables.md:21 | +45 | 円 | 一致 |
| 118 | −41 | 円 | range_lo/fam_tables.md:21 | -41 | 円 | 一致 |
| 118 | +124 | 円 | range_lo/fam_tables.md:21 | +124 | 円 | 一致 |
| 124 | −263 | 円 | range_lo/fam_tables.md:28 | -263 | 円 | 一致 |
| 124 | +8 | 円 | range_lo/fam_tables.md:28 | +8 | 円 | 一致 |
| 124 | +536 | 円 | range_lo/fam_tables.md:28 | +536 | 円 | 一致 |
| 124 | +551 | 円 | range_lo/fam_tables.md:28 | +551 | 円 | 一致 |
| 124 | +275 | 円 | range_lo/fam_tables.md:28 | +275 | 円 | 一致 |
| 124 | +31 | 円 | range_lo/fam_tables.md:28 | +31 | 円 | 一致 |
| 124 | −384 | 円 | range_lo/fam_tables.md:28 | -384 | 円 | 一致 |
| 124 | −256 | 円 | range_lo/fam_tables.md:28 | -256 | 円 | 一致 |
| 124 | −429 | 円 | range_lo/fam_tables.md:28 | -429 | 円 | 一致 |
| 125 | −221 | 円 | range_lo/fam_tables.md:29 | -221 | 円 | 一致 |
| 125 | −116 | 円 | range_lo/fam_tables.md:29 | -116 | 円 | 一致 |
| 125 | +543 | 円 | range_lo/fam_tables.md:29 | +543 | 円 | 一致 |
| 125 | +533 | 円 | range_lo/fam_tables.md:29 | +533 | 円 | 一致 |
| 125 | +279 | 円 | range_lo/fam_tables.md:29 | +279 | 円 | 一致 |
| 125 | +82 | 円 | range_lo/fam_tables.md:29 | +82 | 円 | 一致 |
| 125 | −358 | 円 | range_lo/fam_tables.md:29 | -358 | 円 | 一致 |
| 125 | −223 | 円 | range_lo/fam_tables.md:29 | -223 | 円 | 一致 |
| 125 | −274 | 円 | range_lo/fam_tables.md:29 | -274 | 円 | 一致 |
| 126 | −111 | 円 | range_lo/fam_tables.md:30 | -111 | 円 | 一致 |
| 126 | −179 | 円 | range_lo/fam_tables.md:30 | -179 | 円 | 一致 |
| 126 | +524 | 円 | range_lo/fam_tables.md:30 | +524 | 円 | 一致 |
| 126 | +478 | 円 | range_lo/fam_tables.md:30 | +478 | 円 | 一致 |
| 126 | +197 | 円 | range_lo/fam_tables.md:30 | +197 | 円 | 一致 |
| 126 | +116 | 円 | range_lo/fam_tables.md:30 | +116 | 円 | 一致 |
| 126 | −232 | 円 | range_lo/fam_tables.md:30 | -232 | 円 | 一致 |
| 126 | −100 | 円 | range_lo/fam_tables.md:30 | -100 | 円 | 一致 |
| 126 | −64 | 円 | range_lo/fam_tables.md:30 | -64 | 円 | 一致 |
| 127 | −263 | 円 | range_lo/fam_tables.md:31 | -263 | 円 | 一致 |
| 127 | +133 | 円 | range_lo/fam_tables.md:31 | +133 | 円 | 一致 |
| 127 | +564 | 円 | range_lo/fam_tables.md:31 | +564 | 円 | 一致 |
| 127 | +543 | 円 | range_lo/fam_tables.md:31 | +543 | 円 | 一致 |
| 127 | +244 | 円 | range_lo/fam_tables.md:31 | +244 | 円 | 一致 |
| 127 | +6 | 円 | range_lo/fam_tables.md:31 | +6 | 円 | 一致 |
| 127 | −384 | 円 | range_lo/fam_tables.md:31 | -384 | 円 | 一致 |
| 127 | −263 | 円 | range_lo/fam_tables.md:31 | -263 | 円 | 一致 |
| 127 | −479 | 円 | range_lo/fam_tables.md:31 | -479 | 円 | 一致 |
| 129 | +362 | 円 | range_lo/fam_tables.md:17 | +362 | 円 | 一致 |
| 129 | +255 | 円 | range_lo/fam_tables.md:20 | +255 | 円 | 一致 |
| 129 | −273 | 円 | range_lo/fam_tables.md:17 | -273 | 円 | 一致 |
| 129 | −73 | 円 | range_lo/fam_tables.md:20 | -73 | 円 | 一致 |
| 129 | −73 | 円 | range_lo/fam_tables.md:20 | -73 | 円 | 一致 |
| 129 | −153 | 円 | range_lo/fam_tables.md:20 | -153 | 円 | 一致 |
| 129 | +4 | 円 | range_lo/fam_tables.md:20 | +4 | 円 | 一致 |
| 129 | +91 | 円 | range_lo/fam_tables.md:20 | +91 | 円 | 一致 |
| 129 | +14 | 円 | range_lo/fam_tables.md:20 | +14 | 円 | 一致 |
| 129 | +163 | 円 | range_lo/fam_tables.md:20 | +163 | 円 | 一致 |
| 158 | +0 | 円 | range_lo/scene_diff.out:4 | +0 | 円 | 一致 |
| 162 | +23 | 円 | range_lo/scene_diff.out:13 | +23 | 円 | 一致 |
| 162 | +3 | 円 | range_lo/scene_diff.out:13 | +3 | 円 | 一致 |
| 162 | +47 | 円 | range_lo/scene_diff.out:13 | +47 | 円 | 一致 |
| 162 | −19 | 円 | range_lo/scene_diff.out:22 | -19 | 円 | 一致 |
| 162 | −60 | 円 | range_lo/scene_diff.out:22 | -60 | 円 | 一致 |
| 162 | +21 | 円 | range_lo/scene_diff.out:22 | +21 | 円 | 一致 |
| 162 | −142 | 円 | range_lo/scene_diff.out:31 | -142 | 円 | 一致 |
| 162 | −212 | 円 | range_lo/scene_diff.out:31 | -212 | 円 | 一致 |
| 162 | −69 | 円 | range_lo/scene_diff.out:31 | -69 | 円 | 一致 |
| 163 | +37 | 円 | range_lo/scene_diff.out:14 | +37 | 円 | 一致 |
| 163 | +24 | 円 | range_lo/scene_diff.out:14 | +24 | 円 | 一致 |
| 163 | +50 | 円 | range_lo/scene_diff.out:14 | +50 | 円 | 一致 |
| 163 | +115 | 円 | range_lo/scene_diff.out:23 | +115 | 円 | 一致 |
| 163 | +80 | 円 | range_lo/scene_diff.out:23 | +80 | 円 | 一致 |
| 163 | +148 | 円 | range_lo/scene_diff.out:23 | +148 | 円 | 一致 |
| 163 | +205 | 円 | range_lo/scene_diff.out:32 | +205 | 円 | 一致 |
| 163 | +145 | 円 | range_lo/scene_diff.out:32 | +145 | 円 | 一致 |
| 163 | +264 | 円 | range_lo/scene_diff.out:32 | +264 | 円 | 一致 |
| 164 | −10 | 円 | range_lo/scene_diff.out:15 | -10 | 円 | 一致 |
| 164 | −30 | 円 | range_lo/scene_diff.out:15 | -30 | 円 | 一致 |
| 164 | +3 | 円 | range_lo/scene_diff.out:13 | +3 | 円 | 一致 |
| 164 | +22 | 円 | range_lo/scene_diff.out:24 | +22 | 円 | 一致 |
| 164 | −20 | 円 | range_lo/scene_diff.out:24 | -20 | 円 | 一致 |
| 164 | +52 | 円 | range_lo/scene_diff.out:24 | +52 | 円 | 一致 |
| 164 | −34 | 円 | range_lo/scene_diff.out:33 | -34 | 円 | 一致 |
| 164 | −136 | 円 | range_lo/scene_diff.out:33 | -136 | 円 | 一致 |
| 164 | +47 | 円 | range_lo/scene_diff.out:33 | +47 | 円 | 一致 |
| 165 | +13 | 円 | range_lo/scene_diff.out:16 | +13 | 円 | 一致 |
| 165 | +5 | 円 | range_lo/scene_diff.out:16 | +5 | 円 | 一致 |
| 165 | +21 | 円 | range_lo/scene_diff.out:16 | +21 | 円 | 一致 |
| 165 | +106 | 円 | range_lo/scene_diff.out:25 | +106 | 円 | 一致 |
| 165 | +73 | 円 | range_lo/scene_diff.out:25 | +73 | 円 | 一致 |
| 165 | +141 | 円 | range_lo/scene_diff.out:25 | +141 | 円 | 一致 |
| 165 | +206 | 円 | range_lo/scene_diff.out:34 | +206 | 円 | 一致 |
| 165 | +116 | 円 | range_lo/scene_diff.out:34 | +116 | 円 | 一致 |
| 165 | +304 | 円 | range_lo/scene_diff.out:34 | +304 | 円 | 一致 |
| 166 | −2 | 円 | range_lo/scene_diff.out:17 | -2 | 円 | 一致 |
| 166 | −8 | 円 | range_lo/scene_diff.out:17 | -8 | 円 | 一致 |
| 166 | +3 | 円 | range_lo/scene_diff.out:13 | +3 | 円 | 一致 |
| 166 | +8 | 円 | range_lo/scene_diff.out:26 | +8 | 円 | 一致 |
| 166 | −8 | 円 | range_lo/scene_diff.out:26 | -8 | 円 | 一致 |
| 166 | +23 | 円 | range_lo/scene_diff.out:26 | +23 | 円 | 一致 |
| 166 | +28 | 円 | range_lo/scene_diff.out:35 | +28 | 円 | 一致 |
| 166 | −19 | 円 | range_lo/scene_diff.out:35 | -19 | 円 | 一致 |
| 166 | +74 | 円 | range_lo/scene_diff.out:35 | +74 | 円 | 一致 |
| 167 | +2 | 円 | range_lo/scene_diff.out:18 | +2 | 円 | 一致 |
| 167 | +0 | 円 | range_lo/scene_diff.out:18 | +0 | 円 | 一致 |
| 167 | +4 | 円 | range_lo/scene_diff.out:18 | +4 | 円 | 一致 |
| 167 | +23 | 円 | range_lo/scene_diff.out:26 | +23 | 円 | 一致 |
| 167 | +11 | 円 | range_lo/scene_diff.out:27 | +11 | 円 | 一致 |
| 167 | +33 | 円 | range_lo/scene_diff.out:27 | +33 | 円 | 一致 |
| 167 | +187 | 円 | range_lo/scene_diff.out:36 | +187 | 円 | 一致 |
| 167 | +137 | 円 | range_lo/scene_diff.out:36 | +137 | 円 | 一致 |
| 167 | +231 | 円 | range_lo/scene_diff.out:36 | +231 | 円 | 一致 |
| 169 | −142 | 円 | range_lo/scene_diff.out:31 | -142 | 円 | 一致 |
| 169 | +23 | 円 | range_lo/scene_diff.out:13 | +23 | 円 | 一致 |
| 169 | +37 | 円 | range_lo/scene_diff.out:14 | +37 | 円 | 一致 |
| 190 | +40.5 | 円 | range_lo/compare.md:6 | +40.5 | 円 | 一致 |
| 190 | −281.0 | 円 | range_lo/compare.md:6 | -281.0 | 円 | 一致 |
| 190 | +532,210 | 円 | range_lo/compare.md:6 | +532,210 | 円 | 一致 |
| 191 | +46.5 | 円 | range_lo/compare.md:8 | +46.5 | 円 | 一致 |
| 191 | −322.1 | 円 | range_lo/compare.md:8 | -322.1 | 円 | 一致 |
| 191 | +491,388 | 円 | range_lo/compare.md:8 | +491,388 | 円 | 一致 |
| 192 | +54.3 | 円 | range_lo/compare.md:9 | +54.3 | 円 | 一致 |
| 192 | −374.5 | 円 | range_lo/compare.md:9 | -374.5 | 円 | 一致 |
| 192 | +445,358 | 円 | range_lo/compare.md:9 | +445,358 | 円 | 一致 |
| 193 | +70.2 | 円 | range_lo/compare.md:10 | +70.2 | 円 | 一致 |
| 193 | −473.9 | 円 | range_lo/compare.md:10 | -473.9 | 円 | 一致 |
| 193 | +374,834 | 円 | range_lo/compare.md:10 | +374,834 | 円 | 一致 |
| 194 | +32.2 | 円 | range_lo/compare.md:16 | +32.2 | 円 | 一致 |
| 194 | −238.4 | 円 | range_lo/compare.md:16 | -238.4 | 円 | 一致 |
| 194 | −400,821 | 円 | range_lo/compare.md:16 | -400,821 | 円 | 一致 |
| 195 | +34.8 | 円 | range_lo/compare.md:18 | +34.8 | 円 | 一致 |
| 195 | −254.8 | 円 | range_lo/compare.md:18 | -254.8 | 円 | 一致 |
| 195 | −372,317 | 円 | range_lo/compare.md:18 | -372,317 | 円 | 一致 |
| 196 | +40.1 | 円 | range_lo/compare.md:19 | +40.1 | 円 | 一致 |
| 196 | −286.4 | 円 | range_lo/compare.md:19 | -286.4 | 円 | 一致 |
| 196 | −278,690 | 円 | range_lo/compare.md:19 | -278,690 | 円 | 一致 |
| 197 | +53.2 | 円 | range_lo/compare.md:20 | +53.2 | 円 | 一致 |
| 197 | −360.0 | 円 | range_lo/compare.md:20 | -360.0 | 円 | 一致 |
| 197 | −107,733 | 円 | range_lo/compare.md:20 | -107,733 | 円 | 一致 |
| 205 | +317 | 円 | range_lo/fam_tables.md:39 | +317 | 円 | 一致 |
| 205 | +262 | 円 | range_lo/fam_tables.md:39 | +262 | 円 | 一致 |
| 205 | +365 | 円 | range_lo/fam_tables.md:39 | +365 | 円 | 一致 |
| 205 | +116 | 円 | range_lo/fam_tables.md:39 | +116 | 円 | 一致 |
| 205 | +90 | 円 | range_lo/fam_tables.md:39 | +90 | 円 | 一致 |
| 205 | +139 | 円 | range_lo/fam_tables.md:39 | +139 | 円 | 一致 |
| 205 | +18 | 円 | range_lo/fam_tables.md:40 | +18 | 円 | 一致 |
| 205 | −111 | 円 | range_lo/fam_tables.md:40 | -111 | 円 | 一致 |
| 205 | +151 | 円 | range_lo/fam_tables.md:40 | +151 | 円 | 一致 |
| 205 | −369 | 円 | range_lo/fam_tables.md:40 | -369 | 円 | 一致 |
| 205 | −453 | 円 | range_lo/fam_tables.md:40 | -453 | 円 | 一致 |
| 205 | −283 | 円 | range_lo/fam_tables.md:40 | -283 | 円 | 一致 |
| 206 | +299 | 円 | range_lo/fam_tables.md:41 | +299 | 円 | 一致 |
| 206 | +245 | 円 | range_lo/fam_tables.md:41 | +245 | 円 | 一致 |
| 206 | +347 | 円 | range_lo/fam_tables.md:41 | +347 | 円 | 一致 |
| 206 | +112 | 円 | range_lo/fam_tables.md:41 | +112 | 円 | 一致 |
| 206 | +88 | 円 | range_lo/fam_tables.md:41 | +88 | 円 | 一致 |
| 206 | +134 | 円 | range_lo/fam_tables.md:41 | +134 | 円 | 一致 |
| 206 | +4 | 円 | range_lo/fam_tables.md:42 | +4 | 円 | 一致 |
| 206 | −121 | 円 | range_lo/fam_tables.md:42 | -121 | 円 | 一致 |
| 206 | +135 | 円 | range_lo/fam_tables.md:42 | +135 | 円 | 一致 |
| 206 | −302 | 円 | range_lo/fam_tables.md:42 | -302 | 円 | 一致 |
| 206 | −386 | 円 | range_lo/fam_tables.md:42 | -386 | 円 | 一致 |
| 206 | −217 | 円 | range_lo/fam_tables.md:42 | -217 | 円 | 一致 |
| 207 | +257 | 円 | range_lo/fam_tables.md:43 | +257 | 円 | 一致 |
| 207 | +206 | 円 | range_lo/fam_tables.md:43 | +206 | 円 | 一致 |
| 207 | +305 | 円 | range_lo/fam_tables.md:43 | +305 | 円 | 一致 |
| 207 | +88 | 円 | range_lo/compare.md:20 | 88 | 円 | 一致 |
| 207 | +67 | 円 | range_lo/fam_tables.md:43 | +67 | 円 | 一致 |
| 207 | +108 | 円 | range_lo/fam_tables.md:43 | +108 | 円 | 一致 |
| 207 | −1 | 円 | range_lo/fam_tables.md:44 | -1 | 円 | 一致 |
| 207 | −115 | 円 | range_lo/fam_tables.md:44 | -115 | 円 | 一致 |
| 207 | +121 | 円 | range_lo/fam_tables.md:44 | +121 | 円 | 一致 |
| 207 | −161 | 円 | range_lo/fam_tables.md:44 | -161 | 円 | 一致 |
| 207 | −243 | 円 | range_lo/fam_tables.md:44 | -243 | 円 | 一致 |
| 207 | −85 | 円 | range_lo/fam_tables.md:44 | -85 | 円 | 一致 |
| 208 | +329 | 円 | range_lo/fam_tables.md:45 | +329 | 円 | 一致 |
| 208 | +274 | 円 | range_lo/fam_tables.md:45 | +274 | 円 | 一致 |
| 208 | +378 | 円 | range_lo/fam_tables.md:45 | +378 | 円 | 一致 |
| 208 | +117 | 円 | range_lo/fam_tables.md:45 | +117 | 円 | 一致 |
| 208 | +92 | 円 | range_lo/fam_tables.md:45 | +92 | 円 | 一致 |
| 208 | +141 | 円 | range_lo/fam_tables.md:45 | +141 | 円 | 一致 |
| 208 | +33 | 円 | range_lo/fam_tables.md:46 | +33 | 円 | 一致 |
| 208 | −100 | 円 | range_lo/fam_tables.md:46 | -100 | 円 | 一致 |
| 208 | +167 | 円 | range_lo/fam_tables.md:46 | +167 | 円 | 一致 |
| 208 | −390 | 円 | range_lo/fam_tables.md:46 | -390 | 円 | 一致 |
| 208 | −474 | 円 | range_lo/fam_tables.md:46 | -474 | 円 | 一致 |
| 208 | −302 | 円 | range_lo/fam_tables.md:46 | -302 | 円 | 一致 |
| 210 | +36.4 | 円 | range_lo/compare.md:26 | +36.4 | 円 | 一致 |
| 210 | +40.6 | 円 | range_lo/compare.md:28 | +40.6 | 円 | 一致 |
| 210 | +47.0 | 円 | range_lo/compare.md:29 | +47.0 | 円 | 一致 |
| 210 | +61.9 | 円 | range_lo/compare.md:30 | +61.9 | 円 | 一致 |
| 210 | −258.8 | 円 | range_lo/compare.md:26 | -258.8 | 円 | 一致 |
| 210 | −285.8 | 円 | range_lo/compare.md:28 | -285.8 | 円 | 一致 |
| 210 | −326.7 | 円 | range_lo/compare.md:29 | -326.7 | 円 | 一致 |
| 210 | −415.2 | 円 | range_lo/compare.md:30 | -415.2 | 円 | 一致 |
| 210 | −315.2 | 円 | range_lo/compare.md:26 | -315.2 | 円 | 一致 |
| 210 | −326.9 | 円 | range_lo/compare.md:28 | -326.9 | 円 | 一致 |
| 210 | −357.1 | 円 | range_lo/compare.md:29 | -357.1 | 円 | 一致 |
| 210 | −431.8 | 円 | range_lo/compare.md:30 | -431.8 | 円 | 一致 |
| 211 | +653,497 | 円 | range_lo/fam_tables.md:50 | +653,497 | 円 | 一致 |
| 211 | −766,805 | 円 | range_lo/fam_tables.md:50 | -766,805 | 円 | 一致 |
| 211 | +641,952 | 円 | range_lo/fam_tables.md:53 | +641,952 | 円 | 一致 |
| 211 | −719,058 | 円 | range_lo/fam_tables.md:53 | -719,058 | 円 | 一致 |
| 212 | +117 | 円 | range_lo/fam_tables.md:37 | +117 | 円 | 一致 |
| 212 | +88 | 円 | range_lo/compare.md:20 | 88 | 円 | 一致 |
| 212 | −390 | 円 | range_lo/fam_tables.md:38 | -390 | 円 | 一致 |
| 212 | −161 | 円 | range_lo/fam_tables.md:44 | -161 | 円 | 一致 |
| 234 | +9,897,768 | 円 | range_lo/fam_tables.md:64 | +9,897,768 | 円 | 一致 |
| 234 | 6.87 | move_bp | range_lo/fam_tables.md:64 | 6.87 | move_bp | 一致 |
| 234 | −5.65 | move_bp | range_lo/fam_tables.md:64 | -5.65 | move_bp | 一致 |
| 234 | −10,413,516 | 円 | range_lo/fam_tables.md:65+:66 | −4,601,157 + −5,812,359 = −10,413,516 | 円 | 一致(出所の行から計算して合う) |
| 234 | −33.12 | move_bp | range_lo/fam_tables.md:65 | -33.12 | move_bp | 一致 |
| 234 | −36.49 | move_bp | range_lo/fam_tables.md:66 | -36.49 | move_bp | 一致 |
| 235 | +9,165,075 | 円 | range_lo/fam_tables.md:68 | +9,165,075 | 円 | 一致 |
| 235 | 8.27 | move_bp | range_lo/fam_tables.md:68 | 8.27 | move_bp | 一致 |
| 235 | −6.90 | move_bp | range_lo/fam_tables.md:68 | -6.90 | move_bp | 一致 |
| 235 | −9,602,521 | 円 | range_lo/fam_tables.md:69+:70 | −4,306,773 + −5,295,748 = −9,602,521 | 円 | 一致(出所の行から計算して合う) |
| 235 | −38.53 | move_bp | range_lo/fam_tables.md:69 | -38.53 | move_bp | 一致 |
| 235 | −43.25 | move_bp | range_lo/fam_tables.md:70 | -43.25 | move_bp | 一致 |
| 236 | +7,333,641 | 円 | range_lo/fam_tables.md:72 | +7,333,641 | 円 | 一致 |
| 236 | 11.38 | move_bp | range_lo/fam_tables.md:72 | 11.38 | move_bp | 一致 |
| 236 | −9.29 | move_bp | range_lo/fam_tables.md:72 | -9.29 | move_bp | 一致 |
| 236 | −7,572,643 | 円 | range_lo/fam_tables.md:73+:74 | −3,493,012 + −4,079,631 = −7,572,643 | 円 | 一致(出所の行から計算して合う) |
| 236 | −50.08 | move_bp | range_lo/fam_tables.md:73 | -50.08 | move_bp | 一致 |
| 236 | −57.70 | move_bp | range_lo/fam_tables.md:74 | -57.70 | move_bp | 一致 |
| 237 | +10,177,344 | 円 | range_lo/fam_tables.md:76 | +10,177,344 | 円 | 一致 |
| 237 | 6.02 | move_bp | range_lo/fam_tables.md:76 | 6.02 | move_bp | 一致 |
| 237 | −4.74 | move_bp | range_lo/fam_tables.md:76 | -4.74 | move_bp | 一致 |
| 237 | −10,701,050 | 円 | range_lo/fam_tables.md:77+:78 | −4,695,044 + −6,006,006 = −10,701,050 | 円 | 一致(出所の行から計算して合う) |
| 237 | −30.50 | move_bp | range_lo/fam_tables.md:77 | -30.50 | move_bp | 一致 |
| 237 | −32.38 | move_bp | range_lo/fam_tables.md:78 | -32.38 | move_bp | 一致 |
| 239 | −0.38 | move_bp | range_lo/fam_tables.md:84 | -0.38 | move_bp | 一致 |
| 239 | −0.28 | move_bp | range_lo/fam_tables.md:85 | -0.28 | move_bp | 一致 |
| 239 | −0.25 | move_bp | range_lo/fam_tables.md:86 | -0.25 | move_bp | 一致 |
| 239 | −0.42 | move_bp | range_lo/fam_tables.md:83 | -0.42 | move_bp | 一致 |
| 240 | −523,706 | 円 | range_lo/fam_tables.md:76−(:77+:78) | 10,177,344 − 10,701,050 = −523,706 | 円 | 一致(出所の行から計算して合う) |
| 240 | −515,748 | 円 | range_lo/fam_tables.md:64−(:65+:66) | 9,897,768 − 10,413,516 = −515,748 | 円 | 一致(出所の行から計算して合う) |
| 240 | −437,446 | 円 | range_lo/fam_tables.md:68−(:69+:70) | 9,165,075 − 9,602,521 = −437,446 | 円 | 一致(出所の行から計算して合う) |
| 240 | −239,002 | 円 | range_lo/fam_tables.md:72−(:73+:74) | 7,333,641 − 7,572,643 = −239,002 | 円 | 一致(出所の行から計算して合う) |
| 258 | −0.28 | move_bp | range_lo/fam_tables.md:94 | -0.28 | move_bp | 一致 |
| 258 | −0.54 | move_bp | range_lo/fam_tables.md:94 | -0.54 | move_bp | 一致 |
| 258 | −0.78 | move_bp | range_lo/fam_tables.md:94 | -0.78 | move_bp | 一致 |
| 258 | −0.55 | move_bp | range_lo/fam_tables.md:94 | -0.55 | move_bp | 一致 |
| 258 | −1.13 | move_bp | range_lo/fam_tables.md:94 | -1.13 | move_bp | 一致 |
| 258 | −0.05 | move_bp | range_lo/fam_tables.md:94 | -0.05 | move_bp | 一致 |
| 258 | −0.33 | move_bp | range_lo/fam_tables.md:95 | -0.33 | move_bp | 一致 |
| 258 | −0.61 | move_bp | range_lo/fam_tables.md:95 | -0.61 | move_bp | 一致 |
| 258 | −0.85 | move_bp | range_lo/fam_tables.md:95 | -0.85 | move_bp | 一致 |
| 258 | −0.46 | move_bp | range_lo/fam_tables.md:95 | -0.46 | move_bp | 一致 |
| 258 | −1.15 | move_bp | range_lo/fam_tables.md:95 | -1.15 | move_bp | 一致 |
| 258 | +0.15 | move_bp | range_lo/fam_tables.md:95 | +0.15 | move_bp | 一致 |
| 258 | −0.41 | move_bp | range_lo/blocked_range_lo_p50.md:23 | -0.41 | move_bp | 一致 |
| 258 | −0.52 | move_bp | range_lo/blocked_range_lo_p50.md:41 | -0.52 | move_bp | 一致 |
| 258 | −0.30 | move_bp | range_lo/blocked_range_lo_p50.md:41 | -0.30 | move_bp | 一致 |
| 258 | −0.68 | move_bp | range_lo/blocked_range_lo_p50.md:42 | -0.68 | move_bp | 一致 |
| 258 | −1.00 | move_bp | range_lo/blocked_range_lo_p50.md:43 | -1.00 | move_bp | 一致 |
| 258 | −0.54 | move_bp | range_lo/blocked_range_lo_p50.md:43 | -0.54 | move_bp | 一致 |
| 258 | −1.55 | move_bp | range_lo/blocked_range_lo_p50.md:44 | -1.55 | move_bp | 一致 |
| 258 | +0.35 | move_bp | range_lo/blocked_range_lo_p50.md:33 | +0.35 | move_bp | 一致 |
| 258 | −0.25 | move_bp | range_lo/blocked_range_lo_p50.md:24 | -0.25 | move_bp | 一致 |
| 258 | −0.51 | move_bp | range_lo/fam_tables.md:97 | -0.51 | move_bp | 一致 |
| 258 | −0.74 | move_bp | range_lo/fam_tables.md:97 | -0.74 | move_bp | 一致 |
| 258 | −0.58 | move_bp | range_lo/fam_tables.md:97 | -0.58 | move_bp | 一致 |
| 260 | +0.66 | move_bp | range_lo/blocked_range_lo_p50.md:3 | 1 | move_bp | 一致 |
| 260 | +0.83 | move_bp | range_lo/blocked_range_lo_p50.md:3 | 1 | move_bp | 一致 |
| 260 | +1.41 | move_bp | range_lo/blocked_range_lo_p50.md:44 | +1.41 | move_bp | 一致 |
| 264 | −0.41 | move_bp | range_lo/blocked_range_lo_p50.md:23 | -0.41 | move_bp | 一致 |
| 264 | −0.52 | move_bp | range_lo/blocked_range_lo_p50.md:41 | -0.52 | move_bp | 一致 |
| 264 | −0.30 | move_bp | range_lo/blocked_range_lo_p50.md:41 | -0.30 | move_bp | 一致 |
| 264 | −0.13 | move_bp | range_lo/blocked_range_lo_p50.md:42 | -0.13 | move_bp | 一致 |
| 264 | −0.17 | move_bp | range_lo/blocked_range_lo_p50.md:59 | -0.17 | move_bp | 一致 |
| 264 | −0.09 | move_bp | range_lo/blocked_range_lo_p50.md:59 | -0.09 | move_bp | 一致 |
| 265 | −0.68 | move_bp | range_lo/blocked_range_lo_p50.md:42 | -0.68 | move_bp | 一致 |
| 265 | −0.96 | move_bp | range_lo/blocked_range_lo_p50.md:42 | -0.96 | move_bp | 一致 |
| 265 | −0.40 | move_bp | range_lo/blocked_range_lo_p50.md:42 | -0.40 | move_bp | 一致 |
| 265 | −0.35 | move_bp | range_lo/blocked_range_lo_p50.md:60 | -0.35 | move_bp | 一致 |
| 265 | −0.43 | move_bp | range_lo/blocked_range_lo_p50.md:60 | -0.43 | move_bp | 一致 |
| 265 | −0.27 | move_bp | range_lo/blocked_range_lo_p50.md:60 | -0.27 | move_bp | 一致 |
| 266 | −1.00 | move_bp | range_lo/blocked_range_lo_p50.md:43 | -1.00 | move_bp | 一致 |
| 266 | −1.49 | move_bp | range_lo/blocked_range_lo_p50.md:43 | -1.49 | move_bp | 一致 |
| 266 | −0.54 | move_bp | range_lo/blocked_range_lo_p50.md:43 | -0.54 | move_bp | 一致 |
| 266 | −0.50 | move_bp | range_lo/blocked_range_lo_p50.md:61 | -0.50 | move_bp | 一致 |
| 266 | −0.65 | move_bp | range_lo/blocked_range_lo_p50.md:61 | -0.65 | move_bp | 一致 |
| 266 | −0.33 | move_bp | range_lo/blocked_range_lo_p50.md:61 | -0.33 | move_bp | 一致 |
| 267 | −0.54 | move_bp | range_lo/blocked_range_lo_p50.md:43 | -0.54 | move_bp | 一致 |
| 267 | −1.55 | move_bp | range_lo/blocked_range_lo_p50.md:44 | -1.55 | move_bp | 一致 |
| 267 | +0.35 | move_bp | range_lo/blocked_range_lo_p50.md:33 | +0.35 | move_bp | 一致 |
| 267 | −0.60 | move_bp | range_lo/blocked_range_lo_p50.md:62 | -0.60 | move_bp | 一致 |
| 267 | −0.98 | move_bp | range_lo/blocked_range_lo_p50.md:62 | -0.98 | move_bp | 一致 |
| 267 | −0.25 | move_bp | range_lo/blocked_range_lo_p50.md:24 | -0.25 | move_bp | 一致 |
| 269 | −0.60 | move_bp | range_lo/blocked_range_lo_p50.md:62 | -0.60 | move_bp | 一致 |
| 269 | −1.55 | move_bp | range_lo/blocked_range_lo_p50.md:44 | -1.55 | move_bp | 一致 |
| 269 | +0.35 | move_bp | range_lo/blocked_range_lo_p50.md:33 | +0.35 | move_bp | 一致 |
| 284 | +2.6 | 円 | range_lo/fam_tables.md:102 | +2.6 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 284 | +1.3 | 円 | range_lo/fam_tables.md:102 | +1.3 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 284 | +3.7 | 円 | range_lo/fam_tables.md:102 | +3.7 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 284 | +3.0 | 円 | range_lo/fam_tables.md:52 | 3 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 284 | +1.5 | 円 | range_lo/fam_tables.md:103 | +1.5 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 284 | +4.4 | 円 | range_lo/fam_tables.md:103 | +4.4 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 284 | +4.2 | 円 | range_lo/fam_tables.md:104 | +4.2 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 284 | +1.9 | 円 | range_lo/fam_tables.md:104 | +1.9 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 284 | +6.4 | 円 | range_lo/fam_tables.md:54 | +6.4 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 284 | −1.9 | 円 | range_lo/fam_tables.md:102 | -1.9 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 284 | −1.9 | 円 | range_lo/fam_tables.md:103 | -1.9 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 284 | −1.3 | 円 | range_lo/fam_tables.md:104 | -1.3 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 284 | −4.1 | 円 | range_lo/fam_tables.md:104 | -4.1 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 284 | +1.2 | 円 | range_lo/fam_tables.md:104 | +1.2 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 284 | +2.4 | 円 | range_lo/fam_tables.md:105 | +2.4 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 284 | −2.0 | 円 | range_lo/fam_tables.md:105 | -2.0 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 307 | +0.0 | 円 | range_lo/band_migration.out:3 | 0 | 円 | 一致 |
| 307 | −0.0 | 円 | range_lo/band_migration.out:3 | 0 | 円 | 一致 |
| 307 | +0.1 | 円 | range_lo/band_migration.out:3 | 0 | 円 | 一致 |
| 307 | 0.1 | 円 | range_lo/band_migration.out:3 | 0 | 円 | 一致 |
| 307 | +0 | 円 | range_lo/band_migration.out:3 | 0 | 円 | 一致 |
| 307 | −0 | 円 | range_lo/band_migration.out:3 | 0 | 円 | 一致 |
| 307 | +0 | 円 | range_lo/band_migration.out:3 | 0 | 円 | 一致 |
| 307 | +0 | 円 | range_lo/band_migration.out:3 | 0 | 円 | 一致 |
| 307 | +0 | 円 | range_lo/band_migration.out:3 | 0 | 円 | 一致 |
| 307 | +0 | 円 | range_lo/band_migration.out:3 | 0 | 円 | 一致 |
| 308 | −4.2 | 円 | range_lo/band_migration.out:20 | -4 | 円 | 一致 |
| 308 | −12.7 | 円 | range_lo/fam_tables.md:112 | -12.7 | 円 | 一致 |
| 308 | +3.5 | 円 | range_lo/band_migration.out:14 | +3 | 円 | 一致 |
| 308 | 11.6 | 円 | range_lo/fam_tables.md:51 | +11.6 | 円 | 一致 |
| 308 | −28 | 円 | range_lo/fam_tables.md:112 | -28 | 円 | 一致 |
| 308 | −42 | 円 | range_lo/fam_tables.md:112 | -42 | 円 | 一致 |
| 308 | −14 | 円 | range_lo/band_migration.out:15 | -14 | 円 | 一致 |
| 308 | 20 | 円 | range_lo/fam_tables.md:112 | +20 | 円 | 一致 |
| 308 | +19 | 円 | range_lo/fam_tables.md:112 | +19 | 円 | 一致 |
| 308 | +13 | 円 | range_lo/fam_tables.md:112 | +13 | 円 | 一致 |
| 308 | +25 | 円 | range_lo/band_migration.out:23 | +25 | 円 | 一致 |
| 308 | 9 | 円 | range_lo/fam_tables.md:112 | +9 | 円 | 一致 |
| 308 | −125 | 円 | range_lo/fam_tables.md:112 | -125 | 円 | 一致 |
| 308 | −27 | 円 | range_lo/fam_tables.md:112 | -27 | 円 | 一致 |
| 308 | +31 | 円 | range_lo/fam_tables.md:28 | +31 | 円 | 一致 |
| 308 | +25 | 円 | range_lo/band_migration.out:23 | +25 | 円 | 一致 |
| 308 | +50 | 円 | range_lo/fam_tables.md:112 | +50 | 円 | 一致 |
| 309 | +12.0 | 円 | range_lo/fam_tables.md:113 | +12.0 | 円 | 一致 |
| 309 | −5.2 | 円 | range_lo/fam_tables.md:113 | -5.2 | 円 | 一致 |
| 309 | +29.5 | 円 | range_lo/fam_tables.md:113 | +29.5 | 円 | 一致 |
| 309 | 25.2 | 円 | range_lo/fam_tables.md:113 | +25.2 | 円 | 一致 |
| 309 | −59 | 円 | range_lo/fam_tables.md:113 | -59 | 円 | 一致 |
| 309 | −89 | 円 | range_lo/fam_tables.md:113 | -89 | 円 | 一致 |
| 309 | −30 | 円 | range_lo/band_migration.out:27 | -30 | 円 | 一致 |
| 309 | 42 | 円 | range_lo/fam_tables.md:113 | +42 | 円 | 一致 |
| 309 | +83 | 円 | range_lo/fam_tables.md:113 | +83 | 円 | 一致 |
| 309 | +67 | 円 | range_lo/fam_tables.md:113 | +67 | 円 | 一致 |
| 309 | +103 | 円 | range_lo/fam_tables.md:113 | +103 | 円 | 一致 |
| 309 | 25 | 円 | range_lo/fam_tables.md:113 | +25 | 円 | 一致 |
| 309 | +42 | 円 | range_lo/fam_tables.md:113 | +42 | 円 | 一致 |
| 309 | −249 | 円 | range_lo/fam_tables.md:113 | -249 | 円 | 一致 |
| 309 | +35 | 円 | range_lo/fam_tables.md:113 | +35 | 円 | 一致 |
| 309 | +76 | 円 | range_lo/fam_tables.md:113 | +76 | 円 | 一致 |
| 309 | +26 | 円 | range_lo/fam_tables.md:113 | +26 | 円 | 一致 |
| 309 | +40 | 円 | range_lo/fam_tables.md:9 | 40.0 | 円 | 一致 |
| 309 | +205 | 円 | range_lo/fam_tables.md:113 | +205 | 円 | 一致 |
| 310 | +46.2 | 円 | range_lo/fam_tables.md:114 | +46.2 | 円 | 一致 |
| 310 | +14.1 | 円 | range_lo/fam_tables.md:114 | +14.1 | 円 | 一致 |
| 310 | +81.8 | 円 | range_lo/fam_tables.md:114 | +81.8 | 円 | 一致 |
| 310 | 48.2 | 円 | range_lo/fam_tables.md:114 | +48.2 | 円 | 一致 |
| 310 | −107 | 円 | range_lo/fam_tables.md:114 | -107 | 円 | 一致 |
| 310 | −157 | 円 | range_lo/fam_tables.md:114 | -157 | 円 | 一致 |
| 310 | −53 | 円 | range_lo/fam_tables.md:114 | -53 | 円 | 一致 |
| 310 | 77 | 円 | range_lo/fam_tables.md:114 | +77 | 円 | 一致 |
| 310 | +199 | 円 | range_lo/fam_tables.md:114 | +199 | 円 | 一致 |
| 310 | +163 | 円 | range_lo/fam_tables.md:20 | +163 | 円 | 一致 |
| 310 | +242 | 円 | range_lo/fam_tables.md:114 | +242 | 円 | 一致 |
| 310 | 55 | 円 | range_lo/fam_tables.md:114 | +55 | 円 | 一致 |
| 310 | +152 | 円 | range_lo/fam_tables.md:114 | +152 | 円 | 一致 |
| 310 | −312 | 円 | range_lo/fam_tables.md:114 | -312 | 円 | 一致 |
| 310 | +110 | 円 | range_lo/fam_tables.md:114 | +110 | 円 | 一致 |
| 310 | +152 | 円 | range_lo/fam_tables.md:114 | +152 | 円 | 一致 |
| 310 | +163 | 円 | range_lo/fam_tables.md:20 | +163 | 円 | 一致 |
| 310 | +415 | 円 | range_lo/fam_tables.md:114 | +415 | 円 | 一致 |
| 312 | +0 | 円 | range_lo/band_migration.out:3 | 0 | 円 | 一致 |
| 312 | +773 | 円 | range_lo/fam_tables.md:130 | +773 | 円 | 一致 |
| 312 | −1,054 | 円 | range_lo/fam_tables.md:131 | -1,054 | 円 | 一致 |
| 312 | −2,820 | 円 | range_lo/fam_tables.md:132 | -2,820 | 円 | 一致 |
| 312 | +94 | 円 | range_lo/fam_tables.md:129 | +94 | 円 | 一致 |
| 312 | −689 | 円 | range_lo/fam_tables.md:130 | -689 | 円 | 一致 |
| 312 | +8,548 | 円 | range_lo/fam_tables.md:131 | +8,548 | 円 | 一致 |
| 312 | +57,228 | 円 | range_lo/fam_tables.md:132 | +57,228 | 円 | 一致 |
| 312 | +22 | 円 | range_lo/fam_tables.md:129 | +22 | 円 | 一致 |
| 312 | +12,403 | 円 | range_lo/fam_tables.md:130 | +12,403 | 円 | 一致 |
| 312 | −27,786 | 円 | range_lo/fam_tables.md:131 | -27,786 | 円 | 一致 |
| 312 | −81,304 | 円 | range_lo/fam_tables.md:132 | -81,304 | 円 | 一致 |
| 318 | −14 | 円 | range_lo/band_migration.out:15 | -14 | 円 | 一致 |
| 318 | −18 | 円 | range_lo/band_migration.out:17 | -18 | 円 | 一致 |
| 318 | +4 | 円 | range_lo/fam_tables.md:102 | +3.7 | 円 | 一致 |
| 318 | −1 | 円 | range_lo/band_migration.out:21 | -1 | 円 | 一致 |
| 318 | +25 | 円 | range_lo/band_migration.out:23 | +25 | 円 | 一致 |
| 318 | −4 | 円 | range_lo/band_migration.out:20 | -4 | 円 | 一致 |
| 319 | −30 | 円 | range_lo/band_migration.out:27 | -30 | 円 | 一致 |
| 319 | −36 | 円 | range_lo/band_migration.out:29 | -36 | 円 | 一致 |
| 319 | +8 | 円 | range_lo/band_migration.out:26 | +8 | 円 | 一致 |
| 319 | −2 | 円 | range_lo/band_migration.out:33 | -2 | 円 | 一致 |
| 319 | +87 | 円 | range_lo/band_migration.out:35 | +87 | 円 | 一致 |
| 319 | −3 | 円 | range_lo/band_migration.out:31 | -3 | 円 | 一致 |
| 320 | −72 | 円 | range_lo/band_migration.out:39 | -72 | 円 | 一致 |
| 320 | −67 | 円 | range_lo/band_migration.out:41 | -67 | 円 | 一致 |
| 320 | +34 | 円 | range_lo/band_migration.out:38 | +34 | 円 | 一致 |
| 320 | −18 | 円 | range_lo/band_migration.out:45 | -18 | 円 | 一致 |
| 320 | +212 | 円 | range_lo/band_migration.out:47 | +212 | 円 | 一致 |
| 320 | +6 | 円 | range_lo/fam_tables.md:54 | +6.4 | 円 | 一致 |
| 322 | −28 | 円 | range_lo/fam_tables.md:112 | -28 | 円 | 一致 |
| 322 | −59 | 円 | d7_fullperiod.out:7 | -59.4 | 円 | 一致 |
| 322 | −107 | 円 | range_lo/fam_tables.md:114 | -107 | 円 | 一致 |
| 322 | +19 | 円 | d7_fullperiod.out:22 | +19.2 | 円 | 一致 |
| 322 | +83 | 円 | range_lo/fam_tables.md:113 | +83 | 円 | 一致 |
| 322 | +199 | 円 | range_lo/fam_tables.md:114 | +199 | 円 | 一致 |
| 323 | +72 | 円 | range_lo/band_migration.out:39 | 差 −72 の符号を反転(基準の和 +106,167 ÷ 1,469 日 = +72.3) | 円 | 一致(出所の行から計算して合う) |
| 323 | +67 | 円 | range_lo/band_migration.out:41 | 差 −67 の符号を反転(+98,442 ÷ 1,469 = +67.0) | 円 | 一致(出所の行から計算して合う) |
| 323 | +18 | 円 | range_lo/band_migration.out:45 | 差 −18 の符号を反転(+26,115 ÷ 1,470 = +17.8) | 円 | 一致(出所の行から計算して合う) |
| 323 | −212 | 円 | range_lo/band_migration.out:47 | 差 +212 の符号を反転(−312,028 ÷ 1,470 = −212.3) | 円 | 一致(出所の行から計算して合う) |
| 323 | −273 | 円 | range_lo/fam_tables.md:21 | -273(base 後半) | 円 | 一致 |
| 323 | −212 | 円 | range_lo/band_migration.out:47 | 差 +212 の符号を反転(−312,028 ÷ 1,470 = −212.3) | 円 | 一致(出所の行から計算して合う) |
| 323 | +1.9 | 円 | range_lo/band_migration.out:39+:41 | (106,167 + 98,442) ÷ 106,468 = +1.92 | 円 | 一致(出所の行から計算して合う) |
| 323 | −2.6 | 円 | range_lo/band_migration.out:45+:47 | (26,115 − 312,028) ÷ 109,244 = −2.62 | 円 | 一致(出所の行から計算して合う) |
| 323 | +4.7 | 円 | range_lo/compare.md:6・range_lo/band_migration.out:39+:41 | (532,210 − 204,609) ÷ (176,097 − 106,468) = +4.70 | 円 | 一致(出所の行から計算して合う) |
| 323 | −1.8 | 円 | range_lo/compare.md:16・range_lo/band_migration.out:45+:47 | (−400,821 + 285,913) ÷ (172,686 − 109,244) = −1.81 | 円 | 一致(出所の行から計算して合う) |
| 323 | −1 | 円 | range_lo/band_migration.out:42 | -1 | 円 | 一致 |
| 323 | 0 | 円 | range_lo/band_migration.out:48 | -0 | 円 | 一致 |
| 324 | +57,228 | 円 | range_lo/fam_tables.md:132 | +57,228 | 円 | 一致 |
| 324 | +135,712 | 円 | range_lo/compare.md:30 | +135,712 | 円 | 一致 |
| 324 | +34 | 円 | range_lo/band_migration.out:38 | +34 | 円 | 一致 |
| 324 | +6 | 円 | range_lo/band_migration.out:43+:44 | −11 + +17 = +6 | 円 | 一致(出所の行から計算して合う) |
| 324 | −139 | 円 | range_lo/band_migration.out:39+:41 | −72 + −67 = −139 | 円 | 一致(出所の行から計算して合う) |
| 324 | 10 | 円 | range_lo/band_migration.out:13+:14・:19+:20・:25+:26・:31+:32 | p10 +4・−4、p25 +8・−3(いずれも ±10 以内) | 円 | 一致(出所の行から計算して合う) |
| 340 | −212 | 円 | range_lo/band_migration.out:47 | 差 +212 の符号を反転 | 円 | 一致(出所の行から計算して合う) |
| 340 | −273 | 円 | range_lo/fam_tables.md:21 | -273 | 円 | 一致 |
| 373 | +1.9 | 円 | range_lo/band_migration.out:39+:41 | +1.92 | 円 | 一致(出所の行から計算して合う) |
| 373 | −2.6 | 円 | range_lo/band_migration.out:45+:47 | −2.62 | 円 | 一致(出所の行から計算して合う) |
| 373 | +4.7 | 円 | range_lo/compare.md:6・band_migration | +4.70 | 円 | 一致(出所の行から計算して合う) |
| 373 | −1.8 | 円 | range_lo/compare.md:16・band_migration | −1.81 | 円 | 一致(出所の行から計算して合う) |
| 373 | −194 | 円 | range_lo/band_migration.out:45+:47 | (26,115 − 312,028) ÷ 1,470 = −194.5(−194.4986) | 円 | 一致(出所の行から計算して合う) |
| 373 | −273 | 円 | range_lo/fam_tables.md:21 | -273 | 円 | 一致 |
| 373 | −212 | 円 | range_lo/band_migration.out:47 | 差 +212 の符号を反転(−312,028 ÷ 1,470 = −212.3) | 円 | 一致(出所の行から計算して合う) |
| 375 | −125 | 円 | range_lo/fam_tables.md:112 | -125 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 375 | −249 | 円 | range_lo/fam_tables.md:113 | -249 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 375 | −312 | 円 | range_lo/fam_tables.md:114 | -312 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 376 | +36.4 | 円 | range_lo/fam_tables.md:50 | +36.4 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 376 | +61.9 | 円 | range_lo/fam_tables.md:53 | +61.9 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 376 | −258.8 | 円 | range_lo/fam_tables.md:50 | -258.8 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 376 | −415.2 | 円 | range_lo/fam_tables.md:53 | -415.2 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 377 | +0 | 円 | range_lo/fam_tables.md:7 | 0 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 401 | +362 | 円 | range_lo/fam_tables.md:17 | +362 | 円 | 一致 |
| 401 | +231 | 円 | range_lo/fam_tables.md:17 | +231 | 円 | 一致 |
| 401 | +497 | 円 | range_lo/fam_tables.md:17 | +497 | 円 | 一致 |
| 401 | −273 | 円 | range_lo/fam_tables.md:17 | -273 | 円 | 一致 |
| 401 | −360 | 円 | range_lo/fam_tables.md:17 | -360 | 円 | 一致 |
| 401 | −184 | 円 | range_lo/fam_tables.md:17 | -184 | 円 | 一致 |
| 402 | +335 | 円 | range_lo/fam_tables.md:18 | +335 | 円 | 一致 |
| 402 | +208 | 円 | range_lo/fam_tables.md:18 | +208 | 円 | 一致 |
| 402 | +472 | 円 | range_lo/fam_tables.md:18 | +472 | 円 | 一致 |
| 402 | −253 | 円 | range_lo/fam_tables.md:18 | -253 | 円 | 一致 |
| 402 | −341 | 円 | range_lo/fam_tables.md:18 | -341 | 円 | 一致 |
| 402 | −163 | 円 | range_lo/fam_tables.md:18 | -163 | 円 | 一致 |
| 403 | +303 | 円 | range_lo/fam_tables.md:19 | +303 | 円 | 一致 |
| 403 | +180 | 円 | range_lo/fam_tables.md:19 | +180 | 円 | 一致 |
| 403 | +438 | 円 | range_lo/fam_tables.md:19 | +438 | 円 | 一致 |
| 403 | −190 | 円 | range_lo/fam_tables.md:19 | -190 | 円 | 一致 |
| 403 | −277 | 円 | range_lo/fam_tables.md:19 | -277 | 円 | 一致 |
| 403 | −105 | 円 | range_lo/fam_tables.md:19 | -105 | 円 | 一致 |
| 404 | +255 | 円 | range_lo/fam_tables.md:20 | +255 | 円 | 一致 |
| 404 | +142 | 円 | range_lo/fam_tables.md:20 | +142 | 円 | 一致 |
| 404 | +384 | 円 | range_lo/fam_tables.md:20 | +384 | 円 | 一致 |
| 404 | −73 | 円 | range_lo/fam_tables.md:20 | -73 | 円 | 一致 |
| 404 | −153 | 円 | range_lo/fam_tables.md:20 | -153 | 円 | 一致 |
| 404 | +4 | 円 | range_lo/fam_tables.md:20 | +4 | 円 | 一致 |
| 405 | +362 | 円 | range_lo/fam_tables.md:21 | +362 | 円 | 一致 |
| 405 | +231 | 円 | range_lo/fam_tables.md:21 | +231 | 円 | 一致 |
| 405 | +497 | 円 | range_lo/fam_tables.md:21 | +497 | 円 | 一致 |
| 405 | −273 | 円 | range_lo/fam_tables.md:21 | -273 | 円 | 一致 |
| 405 | −360 | 円 | range_lo/fam_tables.md:21 | -360 | 円 | 一致 |
| 405 | −184 | 円 | range_lo/fam_tables.md:21 | -184 | 円 | 一致 |
| 416 | −27 | 円 | range_lo/fam_tables.md:112 | -27 | 円 | 一致 |
| 416 | +31 | 円 | range_lo/fam_tables.md:28 | +31 | 円 | 一致 |
| 416 | +42 | 円 | range_lo/fam_tables.md:113 | +42 | 円 | 一致 |
| 416 | +35 | 円 | range_lo/fam_tables.md:113 | +35 | 円 | 一致 |
| 416 | +26 | 円 | range_lo/fam_tables.md:113 | +26 | 円 | 一致 |
| 416 | +152 | 円 | range_lo/fam_tables.md:114 | +152 | 円 | 一致 |
| 416 | +152 | 円 | range_lo/fam_tables.md:114 | +152 | 円 | 一致 |
| 420 | −4.2 | 円 | range_lo/fam_tables.md:112 | -4.2 | 円 | 一致 |
| 420 | −12.7 | 円 | range_lo/fam_tables.md:112 | -12.7 | 円 | 一致 |
| 420 | +3.5 | 円 | range_lo/fam_tables.md:112 | +3.5 | 円 | 一致 |
| 420 | 11.6 | 円 | range_lo/fam_tables.md:51 | +11.6 | 円 | 一致 |
| 420 | −28 | 円 | range_lo/fam_tables.md:112 | -28 | 円 | 一致 |
| 420 | −42 | 円 | range_lo/fam_tables.md:112 | -42 | 円 | 一致 |
| 420 | −14 | 円 | range_lo/fam_tables.md:112 | -14 | 円 | 一致 |
| 420 | +19 | 円 | range_lo/fam_tables.md:112 | +19 | 円 | 一致 |
| 420 | +13 | 円 | range_lo/fam_tables.md:112 | +13 | 円 | 一致 |
| 420 | +25 | 円 | range_lo/fam_tables.md:112 | +25 | 円 | 一致 |
| 420 | −125 | 円 | range_lo/fam_tables.md:112 | -125 | 円 | 一致 |
| 420 | +8 | 円 | range_lo/fam_tables.md:28 | +8 | 円 | 一致 |
| 420 | +25 | 円 | range_lo/fam_tables.md:112 | +25 | 円 | 一致 |
| 420 | +7 | 円 | range_lo/fam_tables.md:121 | +7 | 円 | 一致 |
| 420 | +50 | 円 | range_lo/fam_tables.md:112 | +50 | 円 | 一致 |
| 421 | +12.0 | 円 | range_lo/fam_tables.md:113 | +12.0 | 円 | 一致 |
| 421 | −5.2 | 円 | range_lo/fam_tables.md:113 | -5.2 | 円 | 一致 |
| 421 | +29.5 | 円 | range_lo/fam_tables.md:113 | +29.5 | 円 | 一致 |
| 421 | 25.2 | 円 | range_lo/fam_tables.md:113 | +25.2 | 円 | 一致 |
| 421 | −59 | 円 | range_lo/fam_tables.md:113 | -59 | 円 | 一致 |
| 421 | −89 | 円 | range_lo/fam_tables.md:113 | -89 | 円 | 一致 |
| 421 | −30 | 円 | range_lo/fam_tables.md:113 | -30 | 円 | 一致 |
| 421 | +83 | 円 | range_lo/fam_tables.md:113 | +83 | 円 | 一致 |
| 421 | +67 | 円 | range_lo/fam_tables.md:113 | +67 | 円 | 一致 |
| 421 | +103 | 円 | range_lo/fam_tables.md:113 | +103 | 円 | 一致 |
| 421 | −249 | 円 | range_lo/fam_tables.md:113 | -249 | 円 | 一致 |
| 421 | −10 | 円 | range_lo/fam_tables.md:122 | -10 | 円 | 一致 |
| 421 | +76 | 円 | range_lo/fam_tables.md:113 | +76 | 円 | 一致 |
| 421 | +40 | 円 | range_lo/fam_tables.md:9 | 40.0 | 円 | 一致 |
| 421 | +205 | 円 | range_lo/fam_tables.md:113 | +205 | 円 | 一致 |
| 422 | +46.2 | 円 | range_lo/fam_tables.md:114 | +46.2 | 円 | 一致 |
| 422 | +14.1 | 円 | range_lo/fam_tables.md:114 | +14.1 | 円 | 一致 |
| 422 | +81.8 | 円 | range_lo/fam_tables.md:114 | +81.8 | 円 | 一致 |
| 422 | 48.2 | 円 | range_lo/fam_tables.md:114 | +48.2 | 円 | 一致 |
| 422 | −107 | 円 | range_lo/fam_tables.md:114 | -107 | 円 | 一致 |
| 422 | −157 | 円 | range_lo/fam_tables.md:114 | -157 | 円 | 一致 |
| 422 | −53 | 円 | range_lo/fam_tables.md:114 | -53 | 円 | 一致 |
| 422 | +199 | 円 | range_lo/fam_tables.md:114 | +199 | 円 | 一致 |
| 422 | +163 | 円 | range_lo/fam_tables.md:20 | +163 | 円 | 一致 |
| 422 | +242 | 円 | range_lo/fam_tables.md:114 | +242 | 円 | 一致 |
| 422 | −312 | 円 | range_lo/fam_tables.md:114 | -312 | 円 | 一致 |
| 422 | −65 | 円 | range_lo/fam_tables.md:123 | -65 | 円 | 一致 |
| 422 | +110 | 円 | range_lo/fam_tables.md:114 | +110 | 円 | 一致 |
| 422 | +163 | 円 | range_lo/fam_tables.md:20 | +163 | 円 | 一致 |
| 422 | +415 | 円 | range_lo/fam_tables.md:114 | +415 | 円 | 一致 |
| 424 | +0 | 円 | range_lo/fam_tables.md:7 | 0 | 円 | 一致 |
| 426 | −73 | 円 | range_lo/fam_tables.md:20 | -73 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 426 | −153 | 円 | range_lo/fam_tables.md:20 | -153 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 426 | +4 | 円 | range_lo/fam_tables.md:20 | +4 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 426 | 112 | 円 | range_lo/fam_tables.md:20 | +112 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 426 | −28 | 円 | range_lo/fam_tables.md:112 | -28 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 426 | −59 | 円 | range_lo/fam_tables.md:113 | -59 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 426 | −107 | 円 | range_lo/fam_tables.md:114 | -107 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 426 | +19 | 円 | range_lo/fam_tables.md:112 | +19 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 426 | +83 | 円 | range_lo/fam_tables.md:113 | +83 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 426 | +199 | 円 | range_lo/fam_tables.md:114 | +199 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 426 | 20 | 円 | range_lo/fam_tables.md:112 | +20 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 426 | 77 | 円 | range_lo/fam_tables.md:114 | +77 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 426 | 55 | 円 | range_lo/fam_tables.md:114 | +55 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 426 | −1 | 円 | range_lo/fam_tables.md:44 | -1 | 円 | 一致 |
| 426 | 0 | 円 | range_lo/fam_tables.md:10 | 0 | 円 | 一致 |
| 426 | +57,228 | 円 | range_lo/fam_tables.md:132 | +57,228 | 円 | 一致 |
| 426 | +135,712 | 円 | range_lo/compare.md:30 | +135,712 | 円 | 一致 |
| 426 | +34 | 円 | range_lo/band_migration.out:38 | +34 | 円 | 一致 |
| 426 | +6 | 円 | range_lo/fam_tables.md:54 | +6.4 | 円 | 一致 |
| 426 | −0 | 円 | range_lo/fam_tables.md:10 | 0 | 円 | 一致 |
| 426 | +34 | 円 | range_lo/band_migration.out:38 | +34 | 円 | 一致 |
| 426 | −11 | 円 | range_lo/band_migration.out:43 | -11 | 円 | 一致 |
| 426 | +17 | 円 | range_lo/band_migration.out:44 | +17 | 円 | 一致 |
| 426 | +1.9 | 円 | range_lo/band_migration.out:39+:41 | +1.92 | 円 | 一致(出所の行から計算して合う) |
| 426 | −2.6 | 円 | range_lo/band_migration.out:45+:47 | −2.62 | 円 | 一致(出所の行から計算して合う) |
| 426 | +4.7 | 円 | range_lo/compare.md:6・band_migration | +4.70 | 円 | 一致(出所の行から計算して合う) |
| 426 | −1.8 | 円 | range_lo/compare.md:16・band_migration | −1.81 | 円 | 一致(出所の行から計算して合う) |
| 426 | −273 | 円 | range_lo/fam_tables.md:21 | -273 | 円 | 一致 |
| 426 | −194 | 円 | range_lo/band_migration.out:45+:47 | (26,115 − 312,028) ÷ 1,470 日 = −194.5(−194.4986) | 円 | 一致(出所の行から計算して合う) |
| 426 | −212 | 円 | range_lo/band_migration.out:47 | 差 +212 の符号を反転 | 円 | 一致(出所の行から計算して合う) |
| 426 | +18 | 円 | range_lo/band_migration.out:45 | 差 −18 の符号を反転 | 円 | 一致(出所の行から計算して合う) |
| 426 | −212 | 円 | range_lo/band_migration.out:47 | 差 +212 の符号を反転 | 円 | 一致(出所の行から計算して合う) |
| 426 | +212 | 円 | range_lo/band_migration.out:47 | +212 | 円 | 一致 |

## range_hi(`docs/ANALYSIS/2026-10-09_matilda_main_range_hi.md`)

拾った数: 567。判定ごと: 一致 551・単位の誤り 16

細かい判定の内訳: 一致 507・一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) 20・一致(出所の行から計算して合う) 16・単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) 16・一致(散文。値の照合だけ。出所の行は機械が選んだもの) 8

### range_hi: 一致以外

| 文書の行 | 書かれた数 | 判定 | 出所 | 出所の値 | 理由 |
|---|---|---|---|---|---|
| 223 | +6,091,255 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_hi/fam_tables.md:54 | +6,091,255 | 行 219 は「range_hi_<v>/diag_paths.md(move_bp。…和は円)」とだけ書き、diag_paths.md の D4 の和は pnl_bp。fam_tables.md を指していない |
| 223 | −6,513,787 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_hi_p75/diag_paths.md:12+:13(写しは range_hi/fam_tables.md:55+:56) | (−136,932 − 188,757) bp × 20 = −6,513,780 / 円の写し −2,738,640 − 3,775,147 = −6,513,787 | 行 219 は「range_hi_<v>/diag_paths.md(move_bp。…和は円)」とだけ書き、diag_paths.md の D4 の和は pnl_bp。円の写しの fam_tables.md を指していない |
| 224 | +8,192,321 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_hi/fam_tables.md:58 | +8,192,321 | 行 219 は「range_hi_<v>/diag_paths.md(move_bp。…和は円)」とだけ書き、diag_paths.md の D4 の和は pnl_bp。fam_tables.md を指していない |
| 224 | −8,669,685 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_hi_p90/diag_paths.md:12+:13(写しは range_hi/fam_tables.md:59+:60) | 円の写し −3,692,328 − 4,977,357 = −8,669,685 | 行 219 は「range_hi_<v>/diag_paths.md(move_bp。…和は円)」とだけ書き、diag_paths.md の D4 の和は pnl_bp。円の写しの fam_tables.md を指していない |
| 225 | +10,177,344 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_hi/fam_tables.md:66 | +10,177,344 | 行 219 は「range_hi_<v>/diag_paths.md(move_bp。…和は円)」とだけ書き、diag_paths.md の D4 の和は pnl_bp。fam_tables.md を指していない |
| 225 | −10,701,050 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | base/diag_paths.md:12+:13(写しは range_hi/fam_tables.md:67+:68) | 円の写し −4,695,044 − 6,006,006 = −10,701,050 | 行 219 は「range_hi_<v>/diag_paths.md(move_bp。…和は円)」とだけ書き、diag_paths.md の D4 の和は pnl_bp。円の写しの fam_tables.md を指していない |
| 270 | +1.4 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_hi/fam_tables.md:89 | +1.4 | 行 270 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp |
| 270 | +0.7 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_hi/fam_tables.md:89 | +0.7 | 行 270 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp |
| 270 | +2.0 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_hi/fam_tables.md:89 | +2.0 | 行 270 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp |
| 270 | +1.9 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_hi/fam_tables.md:90 | +1.9 | 行 270 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp |
| 270 | +1.2 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_hi/fam_tables.md:90 | +1.2 | 行 270 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp |
| 270 | +2.6 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_hi/fam_tables.md:90 | +2.6 | 行 270 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp |
| 270 | −2.0 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_hi_p90/diag_tables.md:75 | -0.10 | 行 270 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp |
| 270 | −2.1 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_hi/fam_tables.md:90 | -2.1 | 行 270 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp |
| 270 | −1.8 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_hi_p75/diag_tables.md:74 | -0.09 bp × 20 = −1.8 | 行 270 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp |
| 270 | −1.3 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | range_hi/fam_tables.md:90 | -1.3 | 行 270 は「読み口の「D6 固まり」(1 取引あたり 円…)」とだけ書き、読み口 = diag_tables.md は bp |

### range_hi: 全部の数

| 文書の行 | 書かれた数 | 書かれた単位 | 出所 ファイル:行 | 出所の値 | 出所の単位 | 判定 |
|---|---|---|---|---|---|---|
| 30 | −176 | 円 | both_halves.out:1 | −176 | 円 | 一致 |
| 30 | +12 | 円 | both_halves.out:23 | +12 | 円 | 一致 |
| 30 | −101 | 円 | both_halves.out:24 | -101 | 円 | 一致 |
| 30 | −4 | 円 | both_halves.out:24 | -4 | 円 | 一致 |
| 30 | +28 | 円 | both_halves.out:22 | +28 | 円 | 一致 |
| 30 | −2 | 円 | both_halves.out:22 | -2 | 円 | 一致 |
| 30 | +14.1 | 円 | range_hi/six_bands.out:8 | +14.1 | 円 | 一致 |
| 30 | +0.8 | 円 | range_hi/six_bands.out:8 | +0.8 | 円 | 一致 |
| 55 | −129,156 | 円 | range_hi/fam_tables.md:7 | -129155.534 | 円 | 一致 |
| 55 | −43,182 | 円 | range_hi/fam_tables.md:8 | -43181.729 | 円 | 一致 |
| 55 | +170,478 | 円 | range_hi/fam_tables.md:47 | +170,478 | 円 | 一致 |
| 63 | 0 | 円 | range_hi/fam_tables.md:8 | 0 | 円 | 一致 |
| 63 | 0 | 円 | range_hi/fam_tables.md:8 | 0 | 円 | 一致 |
| 63 | +174 | 円 | range_hi/fam_tables.md:16 | +174 | 円 | 一致 |
| 63 | +173 | 円 | range_hi_p75/diag_tables.md:35 | +8.68 bp/日 × 20 × 1,462 ÷ 1,469 = +172.8(約 +173) | bp(×20 で円) | 一致(出所の行から計算して合う) |
| 63 | +249 | 円 | range_hi/fam_tables.md:17 | +249 | 円 | 一致 |
| 63 | +248 | 円 | range_hi_p90/diag_tables.md:35 | +12.44 × 20 × 1,462 ÷ 1,469 = +247.6(約 +248) | bp(×20 で円) | 一致(出所の行から計算して合う) |
| 64 | +0 | 円 | range_hi/fam_tables.md:7 | 0 | 円 | 一致 |
| 64 | +32,838 | 円 | range_hi/fam_tables.md:116 | +32,838 | 円 | 一致 |
| 64 | +530 | 円 | range_hi/fam_tables.md:116 | +32,838 ÷ 62 = +529.6 | 円 | 一致(出所の行から計算して合う) |
| 64 | +110 | 円 | range_hi/fam_tables.md:108 | +110(none − base 2017) | 円 | 一致 |
| 83 | −277 | 円 | range_hi/market_side.out:1 | -277 | 円 | 一致 |
| 83 | −1,299 | 円 | range_hi/market_side.out:2 | -1299 | 円 | 一致 |
| 83 | −156 | 円 | range_hi/market_side.out:3 | -156 | 円 | 一致 |
| 111 | +174 | 円 | range_hi/fam_tables.md:16 | +174 | 円 | 一致 |
| 111 | +84 | 円 | range_hi/fam_tables.md:16 | +84 | 円 | 一致 |
| 111 | +260 | 円 | range_hi/fam_tables.md:16 | +260 | 円 | 一致 |
| 111 | 126 | 円 | range_hi/fam_tables.md:16 | +126 | 円 | 一致 |
| 111 | −261 | 円 | range_hi/fam_tables.md:16 | -261 | 円 | 一致 |
| 111 | −329 | 円 | range_hi/fam_tables.md:16 | -329 | 円 | 一致 |
| 111 | −193 | 円 | range_hi/fam_tables.md:16 | -193 | 円 | 一致 |
| 111 | 97 | 円 | range_hi/fam_tables.md:16 | +97 | 円 | 一致 |
| 111 | −434 | 円 | range_hi/fam_tables.md:16 | -434 | 円 | 一致 |
| 111 | −542 | 円 | range_hi/fam_tables.md:16 | -542 | 円 | 一致 |
| 111 | −336 | 円 | range_hi/fam_tables.md:16 | -336 | 円 | 一致 |
| 111 | −44 | 円 | range_hi/fam_tables.md:16 | -44 | 円 | 一致 |
| 111 | −101 | 円 | range_hi/fam_tables.md:16 | -101 | 円 | 一致 |
| 111 | +13 | 円 | range_hi/fam_tables.md:16 | +13 | 円 | 一致 |
| 112 | +249 | 円 | range_hi/fam_tables.md:17 | +249 | 円 | 一致 |
| 112 | +136 | 円 | range_hi/fam_tables.md:17 | +136 | 円 | 一致 |
| 112 | +360 | 円 | range_hi/fam_tables.md:17 | +360 | 円 | 一致 |
| 112 | 154 | 円 | range_hi/fam_tables.md:17 | +154 | 円 | 一致 |
| 112 | −277 | 円 | range_hi/fam_tables.md:17 | -277 | 円 | 一致 |
| 112 | −356 | 円 | range_hi/fam_tables.md:17 | -356 | 円 | 一致 |
| 112 | −194 | 円 | range_hi/fam_tables.md:17 | -194 | 円 | 一致 |
| 112 | 114 | 円 | range_hi/fam_tables.md:17 | +114 | 円 | 一致 |
| 112 | −525 | 円 | range_hi/fam_tables.md:17 | -525 | 円 | 一致 |
| 112 | −654 | 円 | range_hi/fam_tables.md:17 | -654 | 円 | 一致 |
| 112 | −403 | 円 | range_hi/fam_tables.md:17 | -403 | 円 | 一致 |
| 112 | −15 | 円 | range_hi/fam_tables.md:17 | -15 | 円 | 一致 |
| 112 | −84 | 円 | range_hi/fam_tables.md:17 | -84 | 円 | 一致 |
| 112 | +55 | 円 | range_hi/fam_tables.md:17 | +55 | 円 | 一致 |
| 113 | +391 | 円 | range_hi/fam_tables.md:18 | +391 | 円 | 一致 |
| 113 | +256 | 円 | range_hi/fam_tables.md:18 | +256 | 円 | 一致 |
| 113 | +533 | 円 | range_hi/fam_tables.md:18 | +533 | 円 | 一致 |
| 113 | 197 | 円 | range_hi/fam_tables.md:18 | +197 | 円 | 一致 |
| 113 | −274 | 円 | range_hi/fam_tables.md:18 | -274 | 円 | 一致 |
| 113 | −358 | 円 | range_hi/fam_tables.md:18 | -358 | 円 | 一致 |
| 113 | −188 | 円 | range_hi/fam_tables.md:18 | -188 | 円 | 一致 |
| 113 | 123 | 円 | range_hi/fam_tables.md:18 | +123 | 円 | 一致 |
| 113 | −665 | 円 | range_hi/fam_tables.md:18 | -665 | 円 | 一致 |
| 113 | −833 | 円 | range_hi/fam_tables.md:18 | -833 | 円 | 一致 |
| 113 | −493 | 円 | range_hi/fam_tables.md:18 | -493 | 円 | 一致 |
| 113 | +58 | 円 | range_hi/fam_tables.md:18 | +58 | 円 | 一致 |
| 113 | −31 | 円 | range_hi/fam_tables.md:18 | -31 | 円 | 一致 |
| 113 | +139 | 円 | range_hi/fam_tables.md:18 | +139 | 円 | 一致 |
| 114 | +362 | 円 | range_hi/fam_tables.md:19 | +362 | 円 | 一致 |
| 114 | +231 | 円 | range_hi/fam_tables.md:19 | +231 | 円 | 一致 |
| 114 | +497 | 円 | range_hi/fam_tables.md:19 | +497 | 円 | 一致 |
| 114 | 195 | 円 | range_hi/fam_tables.md:19 | +195 | 円 | 一致 |
| 114 | −273 | 円 | range_hi/fam_tables.md:19 | -273 | 円 | 一致 |
| 114 | −360 | 円 | range_hi/fam_tables.md:19 | -360 | 円 | 一致 |
| 114 | −184 | 円 | range_hi/fam_tables.md:19 | -184 | 円 | 一致 |
| 114 | 125 | 円 | range_hi/fam_tables.md:19 | +125 | 円 | 一致 |
| 114 | −635 | 円 | range_hi/fam_tables.md:19 | -635 | 円 | 一致 |
| 114 | −805 | 円 | range_hi/fam_tables.md:19 | -805 | 円 | 一致 |
| 114 | −476 | 円 | range_hi/fam_tables.md:19 | -476 | 円 | 一致 |
| 114 | +45 | 円 | range_hi/fam_tables.md:19 | +45 | 円 | 一致 |
| 114 | −41 | 円 | range_hi/fam_tables.md:19 | -41 | 円 | 一致 |
| 114 | +124 | 円 | range_hi/fam_tables.md:19 | +124 | 円 | 一致 |
| 116 | −572 | 円 | range_hi/fam_tables.md:25 | -572 | 円 | 一致 |
| 116 | +154 | 円 | range_hi/fam_tables.md:25 | +154 | 円 | 一致 |
| 116 | +147 | 円 | range_hi/fam_tables.md:25 | +147 | 円 | 一致 |
| 116 | +254 | 円 | range_hi/fam_tables.md:25 | +254 | 円 | 一致 |
| 116 | +200 | 円 | range_hi/fam_tables.md:25 | +200 | 円 | 一致 |
| 116 | −80 | 円 | range_hi/fam_tables.md:25 | -80 | 円 | 一致 |
| 116 | −310 | 円 | range_hi/fam_tables.md:25 | -310 | 円 | 一致 |
| 116 | −222 | 円 | range_hi/fam_tables.md:25 | -222 | 円 | 一致 |
| 116 | −476 | 円 | range_hi/fam_tables.md:25 | -476 | 円 | 一致 |
| 116 | −762 | 円 | range_hi/fam_tables.md:26 | -762 | 円 | 一致 |
| 116 | +287 | 円 | range_hi/fam_tables.md:26 | +287 | 円 | 一致 |
| 116 | +355 | 円 | range_hi/fam_tables.md:26 | +355 | 円 | 一致 |
| 116 | +280 | 円 | range_hi/fam_tables.md:26 | +280 | 円 | 一致 |
| 116 | +673 | 円 | range_hi/fam_tables.md:27 | +673 | 円 | 一致 |
| 116 | +564 | 円 | range_hi/fam_tables.md:28 | +564(base 2017) | 円 | 一致 |
| 118 | +362 | 円 | range_hi/fam_tables.md:19 | +362 | 円 | 一致 |
| 118 | +249 | 円 | range_hi/fam_tables.md:17 | +249 | 円 | 一致 |
| 118 | +174 | 円 | range_hi/fam_tables.md:16 | +174 | 円 | 一致 |
| 118 | −273 | 円 | range_hi/fam_tables.md:19 | -273 | 円 | 一致 |
| 118 | −277 | 円 | range_hi/fam_tables.md:17 | -277 | 円 | 一致 |
| 118 | −261 | 円 | range_hi/fam_tables.md:16 | -261 | 円 | 一致 |
| 118 | +564 | 円 | range_hi/fam_tables.md:28 | +564 | 円 | 一致 |
| 118 | +287 | 円 | range_hi/fam_tables.md:26 | +287(p90 2017) | 円 | 一致 |
| 118 | +147 | 円 | range_hi/fam_tables.md:25 | +147(p75 2017) | 円 | 一致 |
| 151 | +21 | 円 | range_hi/scene_diff.out:4 | +21 | 円 | 一致 |
| 151 | −36 | 円 | range_hi/scene_diff.out:4 | -36 | 円 | 一致 |
| 151 | +80 | 円 | range_hi/scene_diff.out:4 | +80 | 円 | 一致 |
| 151 | +6 | 円 | range_hi/scene_diff.out:13 | +6 | 円 | 一致 |
| 151 | −39 | 円 | range_hi/scene_diff.out:13 | -39 | 円 | 一致 |
| 151 | +57 | 円 | range_hi/scene_diff.out:13 | +57 | 円 | 一致 |
| 151 | +4 | 円 | range_hi/scene_diff.out:22 | +4 | 円 | 一致 |
| 151 | +0 | 円 | range_hi/scene_diff.out:22 | +0 | 円 | 一致 |
| 151 | +12 | 円 | range_hi/scene_diff.out:22 | +12 | 円 | 一致 |
| 152 | +7 | 円 | range_hi/scene_diff.out:5 | +7 | 円 | 一致 |
| 152 | −37 | 円 | range_hi/scene_diff.out:5 | -37 | 円 | 一致 |
| 152 | +45 | 円 | range_hi/scene_diff.out:5 | +45 | 円 | 一致 |
| 152 | +1 | 円 | range_hi/scene_diff.out:12 | 1 | 円 | 一致 |
| 152 | −27 | 円 | range_hi/scene_diff.out:14 | -27 | 円 | 一致 |
| 152 | +25 | 円 | range_hi/scene_diff.out:14 | +25 | 円 | 一致 |
| 152 | +0 | 円 | range_hi/scene_diff.out:22 | +0 | 円 | 一致 |
| 153 | −123 | 円 | range_hi/scene_diff.out:6 | -123 | 円 | 一致 |
| 153 | −271 | 円 | range_hi/scene_diff.out:6 | -271 | 円 | 一致 |
| 153 | +17 | 円 | range_hi/scene_diff.out:6 | +17 | 円 | 一致 |
| 153 | −20 | 円 | range_hi/scene_diff.out:15 | -20 | 円 | 一致 |
| 153 | −119 | 円 | range_hi/scene_diff.out:15 | -119 | 円 | 一致 |
| 153 | +79 | 円 | range_hi/scene_diff.out:15 | +79 | 円 | 一致 |
| 153 | −58 | 円 | range_hi/scene_diff.out:24 | -58 | 円 | 一致 |
| 153 | −175 | 円 | range_hi/scene_diff.out:24 | -175 | 円 | 一致 |
| 153 | +0 | 円 | range_hi/scene_diff.out:22 | +0 | 円 | 一致 |
| 154 | +73 | 円 | range_hi/scene_diff.out:7 | +73 | 円 | 一致 |
| 154 | −3 | 円 | range_hi/scene_diff.out:7 | -3 | 円 | 一致 |
| 154 | +157 | 円 | range_hi/scene_diff.out:7 | +157 | 円 | 一致 |
| 154 | +19 | 円 | range_hi/scene_diff.out:16 | +19 | 円 | 一致 |
| 154 | −25 | 円 | range_hi/scene_diff.out:16 | -25 | 円 | 一致 |
| 154 | +69 | 円 | range_hi/scene_diff.out:16 | +69 | 円 | 一致 |
| 154 | −0 | 円 | range_hi/scene_diff.out:22 | +0 | 円 | 一致 |
| 155 | −585 | 円 | range_hi/scene_diff.out:8 | -585 | 円 | 一致 |
| 155 | −926 | 円 | range_hi/scene_diff.out:8 | -926 | 円 | 一致 |
| 155 | −282 | 円 | range_hi/scene_diff.out:8 | -282 | 円 | 一致 |
| 155 | −362 | 円 | range_hi/scene_diff.out:17 | -362 | 円 | 一致 |
| 155 | −634 | 円 | range_hi/scene_diff.out:17 | -634 | 円 | 一致 |
| 155 | −107 | 円 | range_hi/scene_diff.out:17 | -107 | 円 | 一致 |
| 155 | +127 | 円 | range_hi/scene_diff.out:26 | +127 | 円 | 一致 |
| 155 | +17 | 円 | range_hi/scene_diff.out:26 | +17 | 円 | 一致 |
| 155 | +267 | 円 | range_hi/scene_diff.out:26 | +267 | 円 | 一致 |
| 156 | −30 | 円 | range_hi/scene_diff.out:9 | -30 | 円 | 一致 |
| 156 | −193 | 円 | range_hi/scene_diff.out:9 | -193 | 円 | 一致 |
| 156 | +128 | 円 | range_hi/scene_diff.out:9 | +128 | 円 | 一致 |
| 156 | −29 | 円 | range_hi/scene_diff.out:18 | -29 | 円 | 一致 |
| 156 | −144 | 円 | range_hi/scene_diff.out:18 | -144 | 円 | 一致 |
| 156 | +97 | 円 | range_hi/scene_diff.out:18 | +97 | 円 | 一致 |
| 156 | −5 | 円 | range_hi/scene_diff.out:27 | -5 | 円 | 一致 |
| 156 | −52 | 円 | range_hi/scene_diff.out:27 | -52 | 円 | 一致 |
| 156 | +25 | 円 | range_hi/scene_diff.out:27 | +25 | 円 | 一致 |
| 158 | −585 | 円 | range_hi/scene_diff.out:8 | -585 | 円 | 一致 |
| 158 | −362 | 円 | range_hi/scene_diff.out:17 | -362 | 円 | 一致 |
| 158 | +127 | 円 | range_hi/scene_diff.out:26 | +127 | 円 | 一致 |
| 179 | +27.0 | 円 | range_hi/compare.md:7 | +27.0 | 円 | 一致 |
| 179 | −181.5 | 円 | range_hi/compare.md:7 | -181.5 | 円 | 一致 |
| 179 | +253,833 | 円 | range_hi/compare.md:7 | +253,833 | 円 | 一致 |
| 180 | +32.9 | 円 | range_hi/compare.md:8 | +32.9 | 円 | 一致 |
| 180 | −225.8 | 円 | range_hi/compare.md:8 | -225.8 | 円 | 一致 |
| 180 | +363,641 | 円 | range_hi/compare.md:8 | +363,641 | 円 | 一致 |
| 181 | +40.5 | 円 | range_hi/compare.md:6 | +40.5 | 円 | 一致 |
| 181 | −281.0 | 円 | range_hi/compare.md:6 | -281.0 | 円 | 一致 |
| 181 | +532,210 | 円 | range_hi/compare.md:6 | +532,210 | 円 | 一致 |
| 182 | +25.5 | 円 | range_hi/compare.md:16 | +25.5 | 円 | 一致 |
| 182 | −188.4 | 円 | range_hi/compare.md:16 | -188.4 | 円 | 一致 |
| 182 | −382,989 | 円 | range_hi/compare.md:16 | -382,989 | 円 | 一致 |
| 183 | +29.1 | 円 | range_hi/compare.md:17 | +29.1 | 円 | 一致 |
| 183 | −216.7 | 円 | range_hi/compare.md:17 | -216.7 | 円 | 一致 |
| 183 | −406,823 | 円 | range_hi/compare.md:17 | -406,823 | 円 | 一致 |
| 184 | +32.2 | 円 | range_hi/compare.md:15 | +32.2 | 円 | 一致 |
| 184 | −238.4 | 円 | range_hi/compare.md:15 | -238.4 | 円 | 一致 |
| 184 | −400,821 | 円 | range_hi/compare.md:15 | -400,821 | 円 | 一致 |
| 188 | +143 | 円 | range_hi/fam_tables.md:34 | +143 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | +118 | 円 | range_hi/fam_tables.md:34 | +118 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | +166 | 円 | range_hi/fam_tables.md:34 | +166 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | +57 | 円 | range_hi/fam_tables.md:34 | +57 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | +38 | 円 | range_hi/fam_tables.md:34 | +38 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | +75 | 円 | range_hi/fam_tables.md:34 | +75 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | +30 | 円 | range_hi/fam_tables.md:35 | +30 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | −55 | 円 | range_hi/fam_tables.md:35 | -55 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | +114 | 円 | range_hi/fam_tables.md:35 | +114 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | −318 | 円 | range_hi/fam_tables.md:35 | -318 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | −378 | 円 | range_hi/fam_tables.md:35 | -378 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | −253 | 円 | range_hi/fam_tables.md:35 | -253 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | +207 | 円 | range_hi/fam_tables.md:36 | +207 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | +89 | 円 | range_hi/fam_tables.md:36 | +89 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | +42 | 円 | range_hi/fam_tables.md:37 | +42 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | −366 | 円 | range_hi/fam_tables.md:37 | -366 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | +329 | 円 | range_hi/fam_tables.md:40 | +329 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | +117 | 円 | range_hi/fam_tables.md:40 | +117 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | +33 | 円 | range_hi/fam_tables.md:41 | +33 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 188 | −390 | 円 | range_hi/fam_tables.md:41 | -390 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 194 | +32 | 円 | range_hi/compare.md:15 | +32.2 | 円 | 一致 |
| 194 | +1.5 | 円 | range_hi/compare.md:4 | 1 | 円 | 一致 |
| 194 | −23 | 円 | range_hi/six_bands.out:3 | -23 | 円 | 一致 |
| 194 | −1.7 | 円 | range_hi/fam_tables.md:92 | -1.7 | 円 | 一致 |
| 195 | +34 | 円 | range_hi/six_bands.out:4 | +34 | 円 | 一致 |
| 195 | +1.6 | 円 | range_hi/fam_tables.md:91 | +1.6 | 円 | 一致 |
| 195 | −62 | 円 | range_hi/fam_tables.md:99 | -62 | 円 | 一致 |
| 195 | −2.6 | 円 | range_hi/six_bands.out:4 | -2.6 | 円 | 一致 |
| 196 | +73 | 円 | range_hi/fam_tables.md:98 | +73 | 円 | 一致 |
| 196 | +2.5 | 円 | range_hi/fam_tables.md:45 | 3 | 円 | 一致 |
| 196 | −109 | 円 | range_hi/six_bands.out:5 | -109 | 円 | 一致 |
| 196 | −2.9 | 円 | range_hi/fam_tables.md:89 | -2.9 | 円 | 一致 |
| 197 | +41 | 円 | range_hi/compare.md:9 | +40.9 | 円 | 一致 |
| 197 | +1.6 | 円 | range_hi/fam_tables.md:91 | +1.6 | 円 | 一致 |
| 197 | −70 | 円 | range_hi/six_bands.out:6 | -70 | 円 | 一致 |
| 197 | −2.4 | 円 | range_hi/fam_tables.md:100 | -2 | 円 | 一致 |
| 198 | +71 | 円 | range_hi/fam_tables.md:100 | +71 | 円 | 一致 |
| 198 | +5.0 | 円 | range_hi/compare.md:6 | 5 | 円 | 一致 |
| 198 | −12 | 円 | range_hi/fam_tables.md:108 | -12 | 円 | 一致 |
| 198 | −1.1 | 円 | range_hi/fam_tables.md:89 | -1.1 | 円 | 一致 |
| 199 | +111 | 円 | range_hi/six_bands.out:8 | +111 | 円 | 一致 |
| 199 | +14.1 | 円 | range_hi/six_bands.out:8 | +14.1 | 円 | 一致 |
| 199 | +3 | 円 | range_hi/fam_tables.md:45 | 3 | 円 | 一致 |
| 199 | +0.8 | 円 | range_hi/compare.md:7 | +0.84 | 円 | 一致 |
| 201 | +40.5 | 円 | range_hi/compare.md:6 | +40.5 | 円 | 一致 |
| 201 | +27.0 | 円 | range_hi/compare.md:7 | +27.0 | 円 | 一致 |
| 201 | −281.0 | 円 | range_hi/compare.md:6 | -281.0 | 円 | 一致 |
| 201 | −181.5 | 円 | range_hi/compare.md:7 | -181.5 | 円 | 一致 |
| 201 | +5.0 | 円 | range_hi/compare.md:6 | 5 | 円 | 一致 |
| 201 | +14.1 | 円 | range_hi/six_bands.out:8 | +14.1 | 円 | 一致 |
| 223 | +6,091,255 | 円 | range_hi/fam_tables.md:54 | +6,091,255 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 223 | 5.19 | move_bp | range_hi/fam_tables.md:54 | 5.19 | move_bp | 一致 |
| 223 | −4.05 | move_bp | range_hi/fam_tables.md:54 | -4.05 | move_bp | 一致 |
| 223 | −6,513,787 | 円 | range_hi_p75/diag_paths.md:12+:13(写しは range_hi/fam_tables.md:55+:56) | (−136,932 − 188,757) bp × 20 = −6,513,780 / 円の写し −2,738,640 − 3,775,147 = −6,513,787 | bp | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 223 | −26.10 | move_bp | range_hi/fam_tables.md:55 | -26.10 | move_bp | 一致 |
| 223 | −28.46 | move_bp | range_hi/fam_tables.md:56 | -28.46 | move_bp | 一致 |
| 224 | +8,192,321 | 円 | range_hi/fam_tables.md:58 | +8,192,321 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 224 | 5.73 | move_bp | range_hi/fam_tables.md:58 | 5.73 | move_bp | 一致 |
| 224 | −4.49 | move_bp | range_hi/fam_tables.md:58 | -4.49 | move_bp | 一致 |
| 224 | −8,669,685 | 円 | range_hi_p90/diag_paths.md:12+:13(写しは range_hi/fam_tables.md:59+:60) | 円の写し −3,692,328 − 4,977,357 = −8,669,685 | bp | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 224 | −28.95 | move_bp | range_hi/fam_tables.md:59 | -28.95 | move_bp | 一致 |
| 224 | −31.22 | move_bp | range_hi/fam_tables.md:60 | -31.22 | move_bp | 一致 |
| 225 | +10,177,344 | 円 | range_hi/fam_tables.md:66 | +10,177,344 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 225 | 6.02 | move_bp | range_hi/fam_tables.md:66 | 6.02 | move_bp | 一致 |
| 225 | −4.74 | move_bp | range_hi/fam_tables.md:66 | -4.74 | move_bp | 一致 |
| 225 | −10,701,050 | 円 | base/diag_paths.md:12+:13(写しは range_hi/fam_tables.md:67+:68) | 円の写し −4,695,044 − 6,006,006 = −10,701,050 | bp | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 225 | −30.50 | move_bp | range_hi/fam_tables.md:67 | -30.50 | move_bp | 一致 |
| 225 | −32.38 | move_bp | range_hi/fam_tables.md:68 | -32.38 | move_bp | 一致 |
| 227 | −0.72 | move_bp | range_hi/fam_tables.md:73 | -0.72 | move_bp | 一致 |
| 227 | −1.11 | move_bp | range_hi/fam_tables.md:73 | -1.11 | move_bp | 一致 |
| 227 | −0.34 | move_bp | range_hi/fam_tables.md:73 | -0.34 | move_bp | 一致 |
| 227 | −0.50 | move_bp | range_hi/fam_tables.md:74 | -0.50 | move_bp | 一致 |
| 227 | −0.91 | move_bp | range_hi/fam_tables.md:74 | -0.91 | move_bp | 一致 |
| 227 | −0.11 | move_bp | range_hi/fam_tables.md:74 | -0.11 | move_bp | 一致 |
| 227 | −0.42 | move_bp | range_hi_p90/diag_paths.md:12 | 0 | move_bp | 一致 |
| 227 | −0.89 | move_bp | base/diag_paths.md:23 | -0.89 | move_bp | 一致 |
| 227 | +0.01 | move_bp | base/diag_paths.md:24 | +0.01 | move_bp | 一致 |
| 250 | −0.19 | move_bp | range_hi/blocked_range_hi_p75.md:34 | -0.19 | move_bp | 一致 |
| 250 | −0.23 | move_bp | range_hi/blocked_range_hi_p75.md:41 | -0.23 | move_bp | 一致 |
| 250 | −0.15 | move_bp | range_hi/blocked_range_hi_p75.md:41 | -0.15 | move_bp | 一致 |
| 250 | −0.60 | move_bp | range_hi/blocked_range_hi_p75.md:59 | -0.60 | move_bp | 一致 |
| 250 | −0.85 | move_bp | range_hi/blocked_range_hi_p75.md:59 | -0.85 | move_bp | 一致 |
| 250 | −0.38 | move_bp | range_hi/blocked_range_hi_p75.md:59 | -0.38 | move_bp | 一致 |
| 251 | −0.40 | move_bp | range_hi/blocked_range_hi_p75.md:42 | -0.40 | move_bp | 一致 |
| 251 | −0.48 | move_bp | range_hi/blocked_range_hi_p75.md:42 | -0.48 | move_bp | 一致 |
| 251 | −0.31 | move_bp | range_hi/blocked_range_hi_p75.md:22 | -0.31 | move_bp | 一致 |
| 251 | −1.13 | move_bp | range_hi/blocked_range_hi_p75.md:60 | -1.13 | move_bp | 一致 |
| 251 | −1.75 | move_bp | range_hi/blocked_range_hi_p75.md:60 | -1.75 | move_bp | 一致 |
| 251 | −0.54 | move_bp | range_hi/blocked_range_hi_p75.md:60 | -0.54 | move_bp | 一致 |
| 252 | −0.56 | move_bp | range_hi/blocked_range_hi_p75.md:43 | -0.56 | move_bp | 一致 |
| 252 | −0.73 | move_bp | range_hi/blocked_range_hi_p75.md:43 | -0.73 | move_bp | 一致 |
| 252 | −0.40 | move_bp | range_hi/blocked_range_hi_p75.md:42 | -0.40 | move_bp | 一致 |
| 252 | −1.79 | move_bp | range_hi/blocked_range_hi_p75.md:61 | -1.79 | move_bp | 一致 |
| 252 | −2.84 | move_bp | range_hi/blocked_range_hi_p75.md:61 | -2.84 | move_bp | 一致 |
| 252 | −0.80 | move_bp | range_hi/blocked_range_hi_p75.md:61 | -0.80 | move_bp | 一致 |
| 253 | −0.76 | move_bp | range_hi/blocked_range_hi_p75.md:44 | -0.76 | move_bp | 一致 |
| 253 | −1.14 | move_bp | range_hi/blocked_range_hi_p75.md:44 | -1.14 | move_bp | 一致 |
| 253 | −0.40 | move_bp | range_hi/blocked_range_hi_p75.md:42 | -0.40 | move_bp | 一致 |
| 253 | +0.31 | move_bp | range_hi/blocked_range_hi_p75.md:62 | +0.31 | move_bp | 一致 |
| 253 | −1.77 | move_bp | range_hi/blocked_range_hi_p75.md:62 | -1.77 | move_bp | 一致 |
| 253 | +2.42 | move_bp | range_hi/blocked_range_hi_p75.md:62 | +2.42 | move_bp | 一致 |
| 270 | +1.4 | 円 | range_hi/fam_tables.md:89 | +1.4 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 270 | +0.7 | 円 | range_hi/fam_tables.md:89 | +0.7 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 270 | +2.0 | 円 | range_hi/fam_tables.md:89 | +2.0 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 270 | +1.9 | 円 | range_hi/fam_tables.md:90 | +1.9 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 270 | +1.2 | 円 | range_hi/fam_tables.md:90 | +1.2 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 270 | +2.6 | 円 | range_hi/fam_tables.md:90 | +2.6 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 270 | −2.0 | 円 | range_hi_p90/diag_tables.md:75 | -0.10 | bp(×20 で円) | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 270 | −2.1 | 円 | range_hi/fam_tables.md:90 | -2.1 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 270 | −1.8 | 円 | range_hi_p75/diag_tables.md:74 | -0.09 bp × 20 = −1.8 | bp | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 270 | −1.3 | 円 | range_hi/fam_tables.md:90 | -1.3 | 円 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 287 | 0 | 円 | range_hi/band_migration.out:15 | 0 | 円 | 一致 |
| 291 | −88.7 | 円 | d7_fullperiod.out:3 | -88.7 | 円 | 一致 |
| 291 | −149.6 | 円 | d7_fullperiod.out:3 | -149.6 | 円 | 一致 |
| 291 | −25.0 | 円 | d7_fullperiod.out:3 | -25.0 | 円 | 一致 |
| 291 | 84.9 | 円 | range_hi/fam_tables.md:98 | +84.9 | 円 | 一致 |
| 291 | −190 | 円 | d7_fullperiod.out:4 | -189.5 | 円 | 一致 |
| 291 | −305 | 円 | d7_fullperiod.out:4 | -305.2 | 円 | 一致 |
| 291 | −81 | 円 | d7_fullperiod.out:4 | -80.7 | 円 | 一致 |
| 291 | 155 | 円 | range_hi/fam_tables.md:98 | +155 | 円 | 一致 |
| 291 | +12 | 円 | d7_fullperiod.out:5 | +12.1 | 円 | 一致 |
| 291 | −50 | 円 | d7_fullperiod.out:5 | -50.0 | 円 | 一致 |
| 291 | +73 | 円 | d7_fullperiod.out:5 | +73.4 | 円 | 一致 |
| 291 | 88 | 円 | range_hi/fam_tables.md:98 | +88 | 円 | 一致 |
| 291 | −417 | 円 | range_hi/fam_tables.md:98 | -417 | 円 | 一致 |
| 291 | −289 | 円 | range_hi/fam_tables.md:98 | -289 | 円 | 一致 |
| 292 | −59.4 | 円 | d7_fullperiod.out:7 | -59.4 | 円 | 一致 |
| 292 | −111.0 | 円 | d7_fullperiod.out:7 | -111.0 | 円 | 一致 |
| 292 | −8.3 | 円 | d7_fullperiod.out:7 | -8.3 | 円 | 一致 |
| 292 | 64.0 | 円 | range_hi/fam_tables.md:99 | +64.0 | 円 | 一致 |
| 292 | −115 | 円 | d7_fullperiod.out:8 | -114.8 | 円 | 一致 |
| 292 | −209 | 円 | d7_fullperiod.out:8 | -209.1 | 円 | 一致 |
| 292 | −30 | 円 | d7_fullperiod.out:8 | -29.7 | 円 | 一致 |
| 292 | 121 | 円 | range_hi/fam_tables.md:99 | +121 | 円 | 一致 |
| 292 | −4 | 円 | d7_fullperiod.out:9 | -4.1 | 円 | 一致 |
| 292 | −48 | 円 | d7_fullperiod.out:9 | -48.4 | 円 | 一致 |
| 292 | +36 | 円 | d7_fullperiod.out:9 | +36.3 | 円 | 一致 |
| 292 | 61 | 円 | range_hi/fam_tables.md:99 | +61 | 円 | 一致 |
| 292 | −276 | 円 | range_hi/fam_tables.md:99 | -276 | 円 | 一致 |
| 292 | −188 | 円 | range_hi/fam_tables.md:99 | -188 | 円 | 一致 |
| 292 | −62 | 円 | range_hi/fam_tables.md:99 | -62 | 円 | 一致 |
| 293 | +13.3 | 円 | range_hi/band_migration.out:27 | 13 | 円 | 一致 |
| 293 | −4.0 | 円 | range_hi/fam_tables.md:100 | -4.0 | 円 | 一致 |
| 293 | +37.3 | 円 | range_hi/fam_tables.md:100 | +37.3 | 円 | 一致 |
| 293 | 30.1 | 円 | range_hi/fam_tables.md:100 | +30.1 | 円 | 一致 |
| 293 | +28 | 円 | range_hi/fam_tables.md:100 | +28 | 円 | 一致 |
| 293 | −1 | 円 | range_hi/band_migration.out:35 | -1 | 円 | 一致 |
| 293 | +71 | 円 | range_hi/fam_tables.md:100 | +71 | 円 | 一致 |
| 293 | 53 | 円 | range_hi/fam_tables.md:39 | +53 | 円 | 一致 |
| 293 | −2 | 円 | range_hi/fam_tables.md:92 | -2.0 | 円 | 一致 |
| 293 | −18 | 円 | range_hi/fam_tables.md:100 | -18 | 円 | 一致 |
| 293 | +12 | 円 | range_hi/fam_tables.md:100 | +12 | 円 | 一致 |
| 293 | 21 | 円 | range_hi/fam_tables.md:100 | +21 | 円 | 一致 |
| 295 | −180 | 円 | d7_fullperiod.out:6 | -179.6 | 円 | 一致 |
| 295 | −1,491 | 円 | d7_fullperiod.out:6 | -1490.7 | 円 | 一致 |
| 295 | +1,235 | 円 | d7_fullperiod.out:6 | +1235.4 | 円 | 一致 |
| 295 | +21 | 円 | range_hi/fam_tables.md:106 | +21 | 円 | 一致 |
| 295 | −417 | 円 | range_hi/fam_tables.md:98 | -417 | 円 | 一致 |
| 295 | −289 | 円 | range_hi/fam_tables.md:98 | -289 | 円 | 一致 |
| 295 | −45 | 円 | range_hi/fam_tables.md:106 | -45 | 円 | 一致 |
| 295 | −86 | 円 | range_hi/fam_tables.md:106 | -86 | 円 | 一致 |
| 295 | +74 | 円 | range_hi/fam_tables.md:106 | +74 | 円 | 一致 |
| 295 | +41 | 円 | range_hi/fam_tables.md:106 | +41 | 円 | 一致 |
| 295 | +2 | 円 | range_hi/band_migration.out:9 | +2 | 円 | 一致 |
| 295 | −327 | 円 | d7_fullperiod.out:10 | -326.8 | 円 | 一致 |
| 295 | −1,539 | 円 | d7_fullperiod.out:10 | -1539.4 | 円 | 一致 |
| 295 | +989 | 円 | d7_fullperiod.out:10 | +989.0 | 円 | 一致 |
| 295 | +7 | 円 | range_hi/fam_tables.md:107 | +7 | 円 | 一致 |
| 295 | −276 | 円 | range_hi/fam_tables.md:99 | -276 | 円 | 一致 |
| 295 | −188 | 円 | range_hi/fam_tables.md:99 | -188 | 円 | 一致 |
| 295 | +36 | 円 | d7_fullperiod.out:9 | +36.3 | 円 | 一致 |
| 295 | −62 | 円 | range_hi/fam_tables.md:99 | -62 | 円 | 一致 |
| 295 | +89 | 円 | range_hi/fam_tables.md:36 | +89 | 円 | 一致 |
| 295 | −62 | 円 | range_hi/fam_tables.md:99 | -62 | 円 | 一致 |
| 295 | +6 | 円 | range_hi/fam_tables.md:107 | +6 | 円 | 一致 |
| 295 | −81.8 | 円 | range_hi/fam_tables.md:98 | -81.8 | 円 | 一致 |
| 295 | −176 | 円 | range_hi/fam_tables.md:98 | -176 | 円 | 一致 |
| 295 | +629 | 円 | range_hi/fam_tables.md:106 | +629 | 円 | 一致 |
| 295 | −52.5 | 円 | range_hi/fam_tables.md:99 | -52.5 | 円 | 一致 |
| 295 | −101 | 円 | range_hi/fam_tables.md:99 | -101 | 円 | 一致 |
| 295 | +439 | 円 | range_hi/fam_tables.md:107 | +439 | 円 | 一致 |
| 297 | −3,150 | 円 | range_hi/fam_tables.md:114 | -3,150 | 円 | 一致 |
| 297 | −4,596 | 円 | range_hi/fam_tables.md:114 | -4,596 | 円 | 一致 |
| 297 | +252,799 | 円 | range_hi/fam_tables.md:114 | +252,799 | 円 | 一致 |
| 297 | −8,519 | 円 | range_hi/fam_tables.md:115 | -8,519 | 円 | 一致 |
| 297 | +1,066 | 円 | range_hi/fam_tables.md:115 | +1,066 | 円 | 一致 |
| 297 | +167,118 | 円 | range_hi/fam_tables.md:115 | +167,118 | 円 | 一致 |
| 297 | +0 | 円 | range_hi/band_migration.out:27 | 0 | 円 | 一致 |
| 297 | +32,838 | 円 | range_hi/fam_tables.md:116 | +32,838 | 円 | 一致 |
| 297 | −6,250 | 円 | range_hi/fam_tables.md:116 | -6,250 | 円 | 一致 |
| 303 | +36.7 | 円 | range_hi/band_migration.out:5 | +278,550 ÷ 7,594 = +36.68 | 円 | 一致(出所の行から計算して合う) |
| 303 | +278,550 | 円 | range_hi/band_migration.out:5 | +278,550 | 円 | 一致 |
| 303 | −190 | 円 | d7_fullperiod.out:4 | -189.5 | 円 | 一致 |
| 304 | −0.5 | 円 | range_hi/band_migration.out:3 | 0 | 円 | 一致 |
| 304 | −12,699 | 円 | range_hi/band_migration.out:7 | -12,699 | 円 | 一致 |
| 304 | +9 | 円 | range_hi/band_migration.out:7 | +9 | 円 | 一致 |
| 305 | +20.7 | 円 | range_hi/fam_tables.md:106 | +21 | 円 | 一致 |
| 305 | +90,466 | 円 | range_hi/band_migration.out:11 | +90,466 | 円 | 一致 |
| 305 | −62 | 円 | range_hi/band_migration.out:11 | -62 | 円 | 一致 |
| 306 | −6.0 | 円 | range_hi/band_migration.out:13 | −103,518 ÷ 17,261 = −6.00 | 円 | 一致(出所の行から計算して合う) |
| 306 | −103,518 | 円 | range_hi/band_migration.out:13 | -103,518 | 円 | 一致 |
| 306 | +70 | 円 | range_hi/band_migration.out:13 | +70 | 円 | 一致 |
| 307 | +69.9 | 円 | range_hi/zero_reason.out:10 | +69.9 | 円 | 一致 |
| 307 | +182,278 | 円 | range_hi/band_migration.out:17 | +182,278 | 円 | 一致 |
| 307 | −124 | 円 | range_hi/band_migration.out:17 | -124 | 円 | 一致 |
| 308 | −2.2 | 円 | range_hi/band_migration.out:19 | −19,595 ÷ 8,916 = −2.20 | 円 | 一致(出所の行から計算して合う) |
| 308 | −19,595 | 円 | range_hi/band_migration.out:19 | -19,595 | 円 | 一致 |
| 308 | +13 | 円 | range_hi/band_migration.out:19 | +13 | 円 | 一致 |
| 309 | +35.2 | 円 | range_hi/band_migration.out:23 | +41,059 ÷ 1,167 = +35.18 | 円 | 一致(出所の行から計算して合う) |
| 309 | +41,059 | 円 | range_hi/band_migration.out:23 | +41,059 | 円 | 一致 |
| 309 | −28 | 円 | range_hi/band_migration.out:23 | -28 | 円 | 一致 |
| 310 | −7.9 | 円 | range_hi/band_migration.out:25 | −36,624 ÷ 4,641 = −7.89 | 円 | 一致(出所の行から計算して合う) |
| 310 | −36,624 | 円 | range_hi/band_migration.out:25 | -36,624 | 円 | 一致 |
| 310 | +25 | 円 | range_hi/band_migration.out:25 | +25 | 円 | 一致 |
| 312 | −5 | 円 | range_hi/band_migration.out:8 | -5 | 円 | 一致 |
| 312 | +3 | 円 | range_hi/band_migration.out:3 | +3 | 円 | 一致 |
| 312 | +3 | 円 | range_hi/band_migration.out:3 | +3 | 円 | 一致 |
| 312 | −7 | 円 | range_hi/band_migration.out:4 | -7 | 円 | 一致 |
| 312 | +2 | 円 | range_hi/band_migration.out:9 | +2 | 円 | 一致 |
| 312 | −1 | 円 | range_hi/band_migration.out:10 | -1 | 円 | 一致 |
| 315 | −190 | 円 | d7_fullperiod.out:4 | -189.5 | 円 | 一致 |
| 315 | −115 | 円 | d7_fullperiod.out:8 | -114.8 | 円 | 一致 |
| 315 | +12 | 円 | d7_fullperiod.out:5 | +12.1 | 円 | 一致 |
| 315 | −4 | 円 | d7_fullperiod.out:9 | -4.1 | 円 | 一致 |
| 315 | 88 | 円 | range_hi/fam_tables.md:98 | (+88)(p75 後半の MDE、読み口の値) | 円 | 一致 |
| 315 | 61 | 円 | range_hi/fam_tables.md:99 | +61 | 円 | 一致 |
| 315 | −180 | 円 | d7_fullperiod.out:6 | -179.6 | 円 | 一致 |
| 315 | +21 | 円 | range_hi/fam_tables.md:106 | +21 | 円 | 一致 |
| 315 | −417 | 円 | range_hi/fam_tables.md:98 | -417 | 円 | 一致 |
| 315 | −289 | 円 | range_hi/fam_tables.md:98 | -289 | 円 | 一致 |
| 315 | −45 | 円 | range_hi/fam_tables.md:106 | -45 | 円 | 一致 |
| 315 | −86 | 円 | range_hi/fam_tables.md:106 | -86 | 円 | 一致 |
| 315 | +74 | 円 | range_hi/fam_tables.md:106 | +74 | 円 | 一致 |
| 315 | +41 | 円 | range_hi/fam_tables.md:106 | +41 | 円 | 一致 |
| 315 | +2 | 円 | range_hi/band_migration.out:9 | +2 | 円 | 一致 |
| 315 | −62 | 円 | range_hi/fam_tables.md:99 | -62 | 円 | 一致 |
| 315 | −129 | 円 | range_hi/fam_tables.md:99 | -129 | 円 | 一致 |
| 315 | −5 | 円 | range_hi/fam_tables.md:99 | -5 | 円 | 一致 |
| 316 | −190 | 円 | d7_fullperiod.out:4 | -189.5 | 円 | 一致 |
| 316 | +36.7 | 円 | range_hi/band_migration.out:5 | +36.68 | 円 | 一致(出所の行から計算して合う) |
| 317 | −62 | 円 | range_hi/band_migration.out:11 | -62 | 円 | 一致 |
| 317 | +70 | 円 | range_hi/band_migration.out:13 | +70 | 円 | 一致 |
| 317 | +36.7 | 円 | range_hi/band_migration.out:5 | +36.68 | 円 | 一致(出所の行から計算して合う) |
| 317 | +20.7 | 円 | range_hi/band_migration.out:11 | +90,466 ÷ 4,365 = +20.73 | 円 | 一致(出所の行から計算して合う) |
| 317 | −0.5 | 円 | range_hi/band_migration.out:3 | 0 | 円 | 一致 |
| 317 | −6.0 | 円 | range_hi/band_migration.out:13 | −6.00 | 円 | 一致(出所の行から計算して合う) |
| 318 | −3,150 | 円 | range_hi/fam_tables.md:114 | -3,150 | 円 | 一致 |
| 319 | +471,518 | 円 | range_hi/zero_reason.out:4 | +471,518 | 円 | 一致 |
| 319 | +66.7 | 円 | range_hi/zero_reason.out:4 | +66.7(p75 前半 close) | 円 | 一致 |
| 319 | −192,968 | 円 | range_hi/zero_reason.out:3 | -192,968 | 円 | 一致 |
| 319 | −364.1 | 円 | range_hi/zero_reason.out:3 | -364.1 | 円 | 一致 |
| 319 | +46.7 | 円 | range_hi/zero_reason.out:6 | +46.7(p75 後半 close) | 円 | 一致 |
| 319 | −297.3 | 円 | range_hi/zero_reason.out:5 | -297.3 | 円 | 一致 |
| 319 | +107.6 | 円 | range_hi/zero_reason.out:8 | +107.6 | 円 | 一致 |
| 319 | −593.0 | 円 | range_hi/zero_reason.out:7 | -593.0 | 円 | 一致 |
| 319 | +69.9 | 円 | range_hi/zero_reason.out:10 | +69.9 | 円 | 一致 |
| 319 | −485.5 | 円 | range_hi/zero_reason.out:9 | -485.5 | 円 | 一致 |
| 319 | +16.8 | 円 | range_hi/levels_reason.out:3 | +16.8 | 円 | 一致 |
| 319 | +19.9 | 円 | range_hi_p90/diag_tables.md:11 | +1.00 | bp(×20 で円) | 一致 |
| 319 | +66.7 | 円 | range_hi/zero_reason.out:4 | +66.7(p75 前半 close) | 円 | 一致 |
| 319 | +107.6 | 円 | range_hi/zero_reason.out:8 | +107.6 | 円 | 一致 |
| 319 | +15.6 | 円 | range_hi/levels_reason.out:19 | 16 | 円 | 一致 |
| 319 | +17.5 | 円 | range_hi/levels_reason.out:15 | +17.5 | 円 | 一致 |
| 319 | +46.7 | 円 | range_hi/zero_reason.out:6 | +46.7(p75 後半 close) | 円 | 一致 |
| 319 | +69.9 | 円 | range_hi/zero_reason.out:10 | +69.9 | 円 | 一致 |
| 320 | +13.3 | 円 | range_hi/band_migration.out:27 | 13 | 円 | 一致 |
| 321 | +28 | 円 | range_hi/fam_tables.md:100 | +28 | 円 | 一致 |
| 321 | −115 | 円 | d7_fullperiod.out:8 | -114.8 | 円 | 一致 |
| 321 | −190 | 円 | d7_fullperiod.out:4 | -189.5 | 円 | 一致 |
| 337 | −1.7 | 円 | range_hi/fam_tables.md:92 | -1.7 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 337 | −2.9 | 円 | range_hi/fam_tables.md:89 | -2.9 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 337 | +0.8 | 円 | range_hi/fam_tables.md:89 | +0.8 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 338 | −190 | 円 | range_hi/band_migration.out:5 | -190 | 円 | 一致 |
| 370 | −115 | 円 | d7_fullperiod.out:8 | -114.8 | 円 | 一致 |
| 370 | −190 | 円 | range_hi/band_migration.out:5 | -190 | 円 | 一致 |
| 370 | +36.7 | 円 | range_hi/band_migration.out:5 | +278,550 ÷ 7,594 = +36.68 | 円 | 一致(出所の行から計算して合う) |
| 370 | −190 | 円 | range_hi/band_migration.out:5 | -190 | 円 | 一致 |
| 370 | +5.0 | 円 | range_hi/six_bands.out:7 | +5.0 | 円 | 一致 |
| 370 | +14.1 | 円 | range_hi/six_bands.out:8 | +14.1 | 円 | 一致 |
| 371 | −585 | 円 | range_hi/scene_diff.out:8 | -585 | 円 | 一致 |
| 371 | −362 | 円 | range_hi/scene_diff.out:17 | -362 | 円 | 一致 |
| 372 | −1.79 | move_bp | range_hi/blocked_range_hi_p75.md:61 | -1.79 | move_bp | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 372 | −0.56 | move_bp | range_hi/blocked_range_hi_p75.md:43 | -0.56 | move_bp | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 372 | −0.50 | move_bp | range_hi/blocked_range_hi_p75.md:23 | -0.50 | move_bp | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 372 | −1.00 | move_bp | range_lo/fam_tables.md:96 | -1.00 | move_bp | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 373 | −62 | 円 | range_hi/band_migration.out:11 | -62 | 円 | 一致 |
| 373 | +70 | 円 | range_hi/band_migration.out:13 | +70 | 円 | 一致 |
| 373 | −6.0 | 円 | range_hi/band_migration.out:13 | −103,518 ÷ 17,261 = −6.00 | 円 | 一致(出所の行から計算して合う) |
| 373 | −0.5 | 円 | range_hi/band_migration.out:9 | −12,699 ÷ 24,975 = −0.51 | 円 | 一致(出所の行から計算して合う) |
| 375 | +40.5 | 円 | range_hi/compare.md:6 | +40.5 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 375 | +27.0 | 円 | range_hi/compare.md:7 | +27.0(前半 p75) | 円 | 一致 |
| 400 | +174 | 円 | range_hi/fam_tables.md:16 | +174 | 円 | 一致 |
| 400 | +84 | 円 | range_hi/fam_tables.md:16 | +84 | 円 | 一致 |
| 400 | +260 | 円 | range_hi/fam_tables.md:16 | +260 | 円 | 一致 |
| 400 | −261 | 円 | range_hi/fam_tables.md:16 | -261 | 円 | 一致 |
| 400 | −329 | 円 | range_hi/fam_tables.md:16 | -329 | 円 | 一致 |
| 400 | −193 | 円 | range_hi/fam_tables.md:16 | -193 | 円 | 一致 |
| 401 | +249 | 円 | range_hi/fam_tables.md:17 | +249 | 円 | 一致 |
| 401 | +136 | 円 | range_hi/fam_tables.md:17 | +136 | 円 | 一致 |
| 401 | +360 | 円 | range_hi/fam_tables.md:17 | +360 | 円 | 一致 |
| 401 | −277 | 円 | range_hi/fam_tables.md:17 | -277 | 円 | 一致 |
| 401 | −356 | 円 | range_hi/fam_tables.md:17 | -356 | 円 | 一致 |
| 401 | −194 | 円 | range_hi/fam_tables.md:17 | -194 | 円 | 一致 |
| 402 | +391 | 円 | range_hi/fam_tables.md:18 | +391 | 円 | 一致 |
| 402 | +256 | 円 | range_hi/fam_tables.md:18 | +256 | 円 | 一致 |
| 402 | +533 | 円 | range_hi/fam_tables.md:18 | +533 | 円 | 一致 |
| 402 | −274 | 円 | range_hi/fam_tables.md:18 | -274 | 円 | 一致 |
| 402 | −358 | 円 | range_hi/fam_tables.md:18 | -358 | 円 | 一致 |
| 402 | −188 | 円 | range_hi/fam_tables.md:18 | -188 | 円 | 一致 |
| 403 | +362 | 円 | range_hi/fam_tables.md:19 | +362 | 円 | 一致 |
| 403 | +231 | 円 | range_hi/fam_tables.md:19 | +231 | 円 | 一致 |
| 403 | +497 | 円 | range_hi/fam_tables.md:19 | +497 | 円 | 一致 |
| 403 | −273 | 円 | range_hi/fam_tables.md:19 | -273 | 円 | 一致 |
| 403 | −360 | 円 | range_hi/fam_tables.md:19 | -360 | 円 | 一致 |
| 403 | −184 | 円 | range_hi/fam_tables.md:19 | -184 | 円 | 一致 |
| 414 | −417 | 円 | range_hi/fam_tables.md:98 | -417 | 円 | 一致 |
| 414 | −276 | 円 | range_hi/fam_tables.md:99 | -276 | 円 | 一致 |
| 418 | −88.7 | 円 | d7_fullperiod.out:3 | -88.7 | 円 | 一致 |
| 418 | −149.6 | 円 | d7_fullperiod.out:3 | -149.6 | 円 | 一致 |
| 418 | −25.0 | 円 | d7_fullperiod.out:3 | -25.0 | 円 | 一致 |
| 418 | 84.9 | 円 | range_hi/fam_tables.md:98 | +84.9 | 円 | 一致 |
| 418 | −190 | 円 | range_hi/band_migration.out:5 | -190 | 円 | 一致 |
| 418 | −305 | 円 | d7_fullperiod.out:4 | -305.2 | 円 | 一致 |
| 418 | −81 | 円 | d7_fullperiod.out:4 | -80.7 | 円 | 一致 |
| 418 | +12 | 円 | range_hi/fam_tables.md:98 | +12 | 円 | 一致 |
| 418 | −50 | 円 | range_hi/fam_tables.md:98 | -50 | 円 | 一致 |
| 418 | +73 | 円 | range_hi/fam_tables.md:98 | +73 | 円 | 一致 |
| 418 | +21 | 円 | range_hi/fam_tables.md:106 | +21 | 円 | 一致 |
| 418 | −289 | 円 | range_hi/fam_tables.md:98 | -289 | 円 | 一致 |
| 418 | −86 | 円 | range_hi/fam_tables.md:106 | -86 | 円 | 一致 |
| 418 | +41 | 円 | range_hi/fam_tables.md:106 | +41 | 円 | 一致 |
| 418 | +2 | 円 | range_hi/fam_tables.md:89 | +2.0 | 円 | 一致 |
| 419 | −59.4 | 円 | d7_fullperiod.out:7 | -59.4 | 円 | 一致 |
| 419 | −111.0 | 円 | d7_fullperiod.out:7 | -111.0 | 円 | 一致 |
| 419 | −8.3 | 円 | d7_fullperiod.out:7 | -8.3 | 円 | 一致 |
| 419 | 64.0 | 円 | range_hi/fam_tables.md:99 | +64.0 | 円 | 一致 |
| 419 | −115 | 円 | d7_fullperiod.out:8 | -114.8 | 円 | 一致 |
| 419 | −209 | 円 | d7_fullperiod.out:8 | -209.1 | 円 | 一致 |
| 419 | −30 | 円 | d7_fullperiod.out:8 | -29.7 | 円 | 一致 |
| 419 | −4 | 円 | range_hi/fam_tables.md:99 | -4 | 円 | 一致 |
| 419 | −48 | 円 | range_hi/fam_tables.md:99 | -48 | 円 | 一致 |
| 419 | +36 | 円 | range_hi/fam_tables.md:99 | +36 | 円 | 一致 |
| 419 | +7 | 円 | range_hi/fam_tables.md:107 | +7 | 円 | 一致 |
| 419 | −188 | 円 | range_hi/fam_tables.md:99 | -188 | 円 | 一致 |
| 419 | −62 | 円 | range_hi/fam_tables.md:99 | -62 | 円 | 一致 |
| 419 | −62 | 円 | range_hi/fam_tables.md:99 | -62 | 円 | 一致 |
| 419 | +6 | 円 | range_hi/fam_tables.md:107 | +6 | 円 | 一致 |
| 420 | +13.3 | 円 | range_hi/fam_tables.md:100 | +13.3 | 円 | 一致 |
| 420 | −4.0 | 円 | range_hi/fam_tables.md:100 | -4.0 | 円 | 一致 |
| 420 | +37.3 | 円 | range_hi/fam_tables.md:100 | +37.3 | 円 | 一致 |
| 420 | 30.1 | 円 | range_hi/fam_tables.md:100 | +30.1 | 円 | 一致 |
| 420 | +28 | 円 | range_hi/fam_tables.md:100 | +28 | 円 | 一致 |
| 420 | −1 | 円 | range_hi/fam_tables.md:100 | -1 | 円 | 一致 |
| 420 | +71 | 円 | range_hi/fam_tables.md:100 | +71 | 円 | 一致 |
| 420 | −2 | 円 | range_hi/fam_tables.md:92 | -2.0 | 円 | 一致 |
| 420 | −18 | 円 | range_hi/fam_tables.md:100 | -18 | 円 | 一致 |
| 420 | +12 | 円 | range_hi/fam_tables.md:100 | +12 | 円 | 一致 |
| 420 | +0 | 円 | range_hi/fam_tables.md:9 | 0 | 円 | 一致 |
| 420 | −12 | 円 | range_hi/fam_tables.md:108 | -12 | 円 | 一致 |
| 420 | −17 | 円 | range_hi/fam_tables.md:108 | -17 | 円 | 一致 |
| 420 | +0 | 円 | range_hi/fam_tables.md:9 | 0 | 円 | 一致 |
| 420 | −0 | 円 | range_hi/fam_tables.md:9 | 0 | 円 | 一致 |
| 422 | −115 | 円 | d7_fullperiod.out:8 | -114.8 | 円 | 一致 |
| 422 | −209 | 円 | d7_fullperiod.out:8 | -209.1 | 円 | 一致 |
| 422 | −30 | 円 | d7_fullperiod.out:8 | -29.7 | 円 | 一致 |
| 422 | −190 | 円 | range_hi/band_migration.out:5 | -190 | 円 | 一致 |
| 422 | −305 | 円 | d7_fullperiod.out:4 | -305.2 | 円 | 一致 |
| 422 | −81 | 円 | d7_fullperiod.out:4 | -80.7 | 円 | 一致 |
| 422 | 121 | 円 | range_hi/fam_tables.md:99 | (+121)(p90 前半の MDE) | 円 | 一致 |
| 422 | 155 | 円 | range_hi/fam_tables.md:98 | +155 | 円 | 一致 |
| 422 | 0 | 円 | range_hi/fam_tables.md:7 | 0 | 円 | 一致 |
| 422 | −4 | 円 | range_hi/levels_band.out:6 | -4.0 | 円 | 一致 |
| 422 | +12 | 円 | range_hi/fam_tables.md:98 | +12 | 円 | 一致 |
| 422 | 61 | 円 | range_hi/fam_tables.md:99 | (+61)(p90 後半の MDE) | 円 | 一致 |
| 422 | 88 | 円 | range_hi/fam_tables.md:98 | +88 | 円 | 一致 |
| 422 | −62 | 円 | range_hi/fam_tables.md:99 | -62 | 円 | 一致 |
| 422 | −129 | 円 | range_hi/fam_tables.md:99 | -129 | 円 | 一致 |
| 422 | −5 | 円 | range_hi/fam_tables.md:99 | -5 | 円 | 一致 |
| 422 | −3,150 | 円 | range_hi/fam_tables.md:114 | -3,150 | 円 | 一致 |
| 422 | +36.7 | 円 | range_hi/band_migration.out:5 | +36.68 | 円 | 一致(出所の行から計算して合う) |
| 422 | −190 | 円 | range_hi/band_migration.out:5 | -190 | 円 | 一致 |
| 422 | +66.7 | 円 | range_hi/zero_reason.out:4 | +66.7 | 円 | 一致 |
| 422 | −364.1 | 円 | range_hi/zero_reason.out:3 | -364.1 | 円 | 一致 |
| 422 | +5.0 | 円 | range_hi/fam_tables.md:45 | 5 | 円 | 一致 |
| 422 | +14.1 | 円 | range_hi/six_bands.out:8 | +14.1 | 円 | 一致 |
| 422 | −1.1 | 円 | range_hi/fam_tables.md:89 | -1.1 | 円 | 一致 |
| 422 | +0.8 | 円 | range_hi/fam_tables.md:89 | +0.8 | 円 | 一致 |
| 422 | −190 | 円 | range_hi/band_migration.out:5 | -190 | 円 | 一致 |
| 422 | +16.8 | 円 | range_hi/levels_reason.out:3 | +16.8 | 円 | 一致 |
| 422 | +19.9 | 円 | range_hi_p75/diag_tables.md:11 | +1.00 | bp(×20 で円) | 一致 |
| 422 | +66.7 | 円 | range_hi/zero_reason.out:4 | +66.7 | 円 | 一致 |
| 422 | +107.6 | 円 | range_hi/zero_reason.out:8 | +107.6 | 円 | 一致 |

## vola_gate(`docs/ANALYSIS/2026-10-09_matilda_main_vola_gate.md`)

拾った数: 602。判定ごと: 一致 598・単位の誤り 4

細かい判定の内訳: 一致 521・一致(散文。値の照合だけ。出所の行は機械が選んだもの) 34・一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) 32・一致(出所の行から計算して合う) 11・単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) 4

### vola_gate: 一致以外

| 文書の行 | 書かれた数 | 判定 | 出所 | 出所の値 | 理由 |
|---|---|---|---|---|---|
| 192 | +640,619 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | vola_gate_p50/diag_tables.md:44(写しは vola_gate/fam_tables.md:47) | +32031 bp × 20 = +640,620 / 写し +640,619 | 行 192 は手で分ける(−390・−168 は fam_tables.md の 0 分超、上位・下位 5% は読み口の D3 = bp) |
| 192 | +653,497 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | base/diag_tables.md:44(写しは vola_gate/fam_tables.md:48) | +32675 bp × 20 = +653,500 / 写し +653,497 | 行 192 は手で分ける(−390・−168 は fam_tables.md の 0 分超、上位・下位 5% は読み口の D3 = bp) |
| 192 | −698,735 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | vola_gate_p50/diag_tables.md:44(写しは vola_gate/fam_tables.md:47) | -34937 bp × 20 = −698,740 / 写し −698,735 | 行 192 は手で分ける(−390・−168 は fam_tables.md の 0 分超、上位・下位 5% は読み口の D3 = bp) |
| 192 | −766,805 | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) | base/diag_tables.md:44(写しは vola_gate/fam_tables.md:48) | -38340 bp × 20 = −766,800 / 写し −766,805 | 行 192 は手で分ける(−390・−168 は fam_tables.md の 0 分超、上位・下位 5% は読み口の D3 = bp) |

### vola_gate: 全部の数

| 文書の行 | 書かれた数 | 書かれた単位 | 出所 ファイル:行 | 出所の値 | 出所の単位 | 判定 |
|---|---|---|---|---|---|---|
| 55 | +128,225 | 円 | vola_gate/fam_tables.md:7 | 128224.664 | 円 | 一致 |
| 55 | +210,229 | 円 | vola_gate/fam_tables.md:8 | 210228.855 | 円 | 一致 |
| 55 | +290,739 | 円 | vola_gate/fam_tables.md:47 | +290,739 | 円 | 一致 |
| 55 | +131,389 | 円 | vola_gate/fam_tables.md:10 | 131389.464 | 円 | 一致 |
| 82 | −86 | 円 | vola_gate/band_migration.out:29 | -86 | 円 | 一致 |
| 82 | +221 | 円 | vola_gate/band_migration.out:37 | +221 | 円 | 一致 |
| 83 | +155 | 円 | vola_gate/market_side.out:1 | 155 | 円 | 一致 |
| 83 | +51 | 円 | vola_gate/market_side.out:2 | 51 | 円 | 一致 |
| 83 | +803 | 円 | vola_gate/market_side.out:3 | 803 | 円 | 一致 |
| 111 | +341 | 円 | vola_gate/fam_tables.md:16 | +341 | 円 | 一致 |
| 111 | +218 | 円 | vola_gate/fam_tables.md:16 | +218 | 円 | 一致 |
| 111 | +475 | 円 | vola_gate/fam_tables.md:16 | +475 | 円 | 一致 |
| 111 | 185 | 円 | vola_gate/fam_tables.md:16 | +185 | 円 | 一致 |
| 111 | −254 | 円 | vola_gate/fam_tables.md:16 | -254 | 円 | 一致 |
| 111 | −341 | 円 | vola_gate/fam_tables.md:16 | -341 | 円 | 一致 |
| 111 | −164 | 円 | vola_gate/fam_tables.md:16 | -164 | 円 | 一致 |
| 111 | 124 | 円 | vola_gate/fam_tables.md:16 | +124 | 円 | 一致 |
| 111 | −595 | 円 | vola_gate/fam_tables.md:16 | -595 | 円 | 一致 |
| 111 | −754 | 円 | vola_gate/fam_tables.md:16 | -754 | 円 | 一致 |
| 111 | −432 | 円 | vola_gate/fam_tables.md:16 | -432 | 円 | 一致 |
| 111 | +44 | 円 | vola_gate/fam_tables.md:16 | +44 | 円 | 一致 |
| 111 | −41 | 円 | vola_gate/fam_tables.md:16 | -41 | 円 | 一致 |
| 111 | +119 | 円 | vola_gate/fam_tables.md:16 | +119 | 円 | 一致 |
| 112 | +322 | 円 | vola_gate/fam_tables.md:17 | +322 | 円 | 一致 |
| 112 | +207 | 円 | vola_gate/fam_tables.md:17 | +207 | 円 | 一致 |
| 112 | +450 | 円 | vola_gate/fam_tables.md:17 | +450 | 円 | 一致 |
| 112 | 177 | 円 | vola_gate/fam_tables.md:17 | +177 | 円 | 一致 |
| 112 | −179 | 円 | vola_gate/fam_tables.md:17 | -179 | 円 | 一致 |
| 112 | −263 | 円 | vola_gate/fam_tables.md:17 | -263 | 円 | 一致 |
| 112 | −97 | 円 | vola_gate/fam_tables.md:17 | -97 | 円 | 一致 |
| 112 | 122 | 円 | vola_gate/fam_tables.md:17 | +122 | 円 | 一致 |
| 112 | −502 | 円 | vola_gate/fam_tables.md:17 | -502 | 円 | 一致 |
| 112 | −658 | 円 | vola_gate/fam_tables.md:17 | -658 | 円 | 一致 |
| 112 | −344 | 円 | vola_gate/fam_tables.md:17 | -344 | 円 | 一致 |
| 112 | +72 | 円 | vola_gate/fam_tables.md:17 | +72 | 円 | 一致 |
| 112 | −14 | 円 | vola_gate/fam_tables.md:17 | -14 | 円 | 一致 |
| 112 | +143 | 円 | vola_gate/fam_tables.md:17 | +143 | 円 | 一致 |
| 113 | +285 | 円 | vola_gate/fam_tables.md:18 | +285 | 円 | 一致 |
| 113 | +172 | 円 | vola_gate/fam_tables.md:18 | +172 | 円 | 一致 |
| 113 | +407 | 円 | vola_gate/fam_tables.md:18 | +407 | 円 | 一致 |
| 113 | 166 | 円 | vola_gate/fam_tables.md:18 | +166 | 円 | 一致 |
| 113 | −87 | 円 | vola_gate/fam_tables.md:18 | -87 | 円 | 一致 |
| 113 | −166 | 円 | vola_gate/fam_tables.md:18 | -166 | 円 | 一致 |
| 113 | −11 | 円 | vola_gate/fam_tables.md:18 | -11 | 円 | 一致 |
| 113 | 113 | 円 | vola_gate/fam_tables.md:18 | +113 | 円 | 一致 |
| 113 | −371 | 円 | vola_gate/fam_tables.md:18 | -371 | 円 | 一致 |
| 113 | −508 | 円 | vola_gate/fam_tables.md:18 | -508 | 円 | 一致 |
| 113 | −216 | 円 | vola_gate/fam_tables.md:18 | -216 | 円 | 一致 |
| 113 | +99 | 円 | vola_gate/fam_tables.md:18 | +99 | 円 | 一致 |
| 113 | +24 | 円 | vola_gate/fam_tables.md:18 | +24 | 円 | 一致 |
| 113 | +168 | 円 | vola_gate/fam_tables.md:18 | +168 | 円 | 一致 |
| 114 | +362 | 円 | vola_gate/fam_tables.md:19 | +362 | 円 | 一致 |
| 114 | +231 | 円 | vola_gate/fam_tables.md:19 | +231 | 円 | 一致 |
| 114 | +497 | 円 | vola_gate/fam_tables.md:19 | +497 | 円 | 一致 |
| 114 | 195 | 円 | vola_gate/fam_tables.md:19 | +195 | 円 | 一致 |
| 114 | −273 | 円 | vola_gate/fam_tables.md:19 | -273 | 円 | 一致 |
| 114 | −360 | 円 | vola_gate/fam_tables.md:19 | -360 | 円 | 一致 |
| 114 | −184 | 円 | vola_gate/fam_tables.md:19 | -184 | 円 | 一致 |
| 114 | 125 | 円 | vola_gate/fam_tables.md:19 | +125 | 円 | 一致 |
| 114 | −635 | 円 | vola_gate/fam_tables.md:19 | -635 | 円 | 一致 |
| 114 | −805 | 円 | vola_gate/fam_tables.md:19 | -805 | 円 | 一致 |
| 114 | −476 | 円 | vola_gate/fam_tables.md:19 | -476 | 円 | 一致 |
| 114 | +45 | 円 | vola_gate/fam_tables.md:19 | +45 | 円 | 一致 |
| 114 | −41 | 円 | vola_gate/fam_tables.md:19 | -41 | 円 | 一致 |
| 114 | +124 | 円 | vola_gate/fam_tables.md:19 | +124 | 円 | 一致 |
| 116 | +125 | 円 | vola_gate/fam_tables.md:27 | +125 | 円 | 一致 |
| 116 | −13 | 円 | vola_gate/fam_tables.md:27 | -13 | 円 | 一致 |
| 116 | +485 | 円 | vola_gate/fam_tables.md:27 | +485 | 円 | 一致 |
| 116 | +438 | 円 | vola_gate/fam_tables.md:27 | +438 | 円 | 一致 |
| 116 | +206 | 円 | vola_gate/fam_tables.md:27 | +206 | 円 | 一致 |
| 116 | +117 | 円 | vola_gate/fam_tables.md:27 | +117 | 円 | 一致 |
| 116 | −291 | 円 | vola_gate/fam_tables.md:27 | -291 | 円 | 一致 |
| 116 | −115 | 円 | vola_gate/fam_tables.md:27 | -115 | 円 | 一致 |
| 116 | −43 | 円 | vola_gate/fam_tables.md:27 | -43 | 円 | 一致 |
| 118 | +362 | 円 | vola_gate/fam_tables.md:19 | +362 | 円 | 一致 |
| 118 | +341 | 円 | vola_gate/fam_tables.md:16 | +341 | 円 | 一致 |
| 118 | +322 | 円 | vola_gate/fam_tables.md:17 | +322 | 円 | 一致 |
| 118 | +285 | 円 | vola_gate/fam_tables.md:18 | +285 | 円 | 一致 |
| 118 | −273 | 円 | vola_gate/fam_tables.md:19 | -273 | 円 | 一致 |
| 118 | −254 | 円 | vola_gate/fam_tables.md:16 | -254 | 円 | 一致 |
| 118 | −179 | 円 | vola_gate/fam_tables.md:17 | -179 | 円 | 一致 |
| 118 | −87 | 円 | vola_gate/fam_tables.md:18 | -87 | 円 | 一致 |
| 151 | +13 | 円 | vola_gate/scene_diff.out:4 | +13 | 円 | 一致 |
| 151 | −8 | 円 | vola_gate/scene_diff.out:4 | -8 | 円 | 一致 |
| 151 | +37 | 円 | vola_gate/scene_diff.out:4 | +37 | 円 | 一致 |
| 151 | −21 | 円 | vola_gate/scene_diff.out:13 | -21 | 円 | 一致 |
| 151 | −57 | 円 | vola_gate/scene_diff.out:13 | -57 | 円 | 一致 |
| 151 | +16 | 円 | vola_gate/scene_diff.out:13 | +16 | 円 | 一致 |
| 151 | −163 | 円 | vola_gate/scene_diff.out:22 | -163 | 円 | 一致 |
| 151 | −221 | 円 | vola_gate/scene_diff.out:22 | -221 | 円 | 一致 |
| 151 | −92 | 円 | vola_gate/scene_diff.out:22 | -92 | 円 | 一致 |
| 152 | +36 | 円 | vola_gate/scene_diff.out:5 | +36 | 円 | 一致 |
| 152 | +20 | 円 | vola_gate/scene_diff.out:5 | +20 | 円 | 一致 |
| 152 | +52 | 円 | vola_gate/scene_diff.out:5 | +52 | 円 | 一致 |
| 152 | +136 | 円 | vola_gate/scene_diff.out:14 | +136 | 円 | 一致 |
| 152 | +98 | 円 | vola_gate/scene_diff.out:14 | +98 | 円 | 一致 |
| 152 | +171 | 円 | vola_gate/scene_diff.out:14 | +171 | 円 | 一致 |
| 152 | +219 | 円 | vola_gate/scene_diff.out:23 | +219 | 円 | 一致 |
| 152 | +150 | 円 | vola_gate/scene_diff.out:23 | +150 | 円 | 一致 |
| 152 | +285 | 円 | vola_gate/scene_diff.out:23 | +285 | 円 | 一致 |
| 153 | −12 | 円 | vola_gate/scene_diff.out:6 | -12 | 円 | 一致 |
| 153 | −31 | 円 | vola_gate/scene_diff.out:6 | -31 | 円 | 一致 |
| 153 | −0 | 円 | vola_gate/scene_diff.out:6 | -0 | 円 | 一致 |
| 153 | −2 | 円 | vola_gate/scene_diff.out:15 | -2 | 円 | 一致 |
| 153 | −43 | 円 | vola_gate/scene_diff.out:15 | -43 | 円 | 一致 |
| 153 | +28 | 円 | vola_gate/scene_diff.out:15 | +28 | 円 | 一致 |
| 153 | −53 | 円 | vola_gate/scene_diff.out:24 | -53 | 円 | 一致 |
| 153 | −146 | 円 | vola_gate/scene_diff.out:24 | -146 | 円 | 一致 |
| 153 | +19 | 円 | vola_gate/scene_diff.out:24 | +19 | 円 | 一致 |
| 154 | +13 | 円 | vola_gate/scene_diff.out:4 | +13 | 円 | 一致 |
| 154 | +3 | 円 | vola_gate/scene_diff.out:7 | +3 | 円 | 一致 |
| 154 | +24 | 円 | vola_gate/scene_diff.out:7 | +24 | 円 | 一致 |
| 154 | +127 | 円 | vola_gate/scene_diff.out:16 | +127 | 円 | 一致 |
| 154 | +79 | 円 | vola_gate/scene_diff.out:16 | +79 | 円 | 一致 |
| 154 | +176 | 円 | vola_gate/scene_diff.out:16 | +176 | 円 | 一致 |
| 154 | +195 | 円 | vola_gate/scene_diff.out:25 | +195 | 円 | 一致 |
| 154 | +102 | 円 | vola_gate/scene_diff.out:25 | +102 | 円 | 一致 |
| 154 | +294 | 円 | vola_gate/scene_diff.out:25 | +294 | 円 | 一致 |
| 155 | −4 | 円 | vola_gate/scene_diff.out:8 | -4 | 円 | 一致 |
| 155 | −7 | 円 | vola_gate/scene_diff.out:8 | -7 | 円 | 一致 |
| 155 | −0 | 円 | vola_gate/scene_diff.out:6 | -0 | 円 | 一致 |
| 155 | −12 | 円 | vola_gate/scene_diff.out:17 | -12 | 円 | 一致 |
| 155 | −28 | 円 | vola_gate/scene_diff.out:17 | -28 | 円 | 一致 |
| 155 | −1 | 円 | vola_gate/scene_diff.out:17 | -1 | 円 | 一致 |
| 155 | +1 | 円 | vola_gate/scene_diff.out:21 | 1 | 円 | 一致 |
| 155 | −42 | 円 | vola_gate/scene_diff.out:26 | -42 | 円 | 一致 |
| 155 | +43 | 円 | vola_gate/scene_diff.out:26 | +43 | 円 | 一致 |
| 156 | −0 | 円 | vola_gate/scene_diff.out:6 | -0 | 円 | 一致 |
| 156 | −3 | 円 | vola_gate/scene_diff.out:9 | -3 | 円 | 一致 |
| 156 | +2 | 円 | vola_gate/scene_diff.out:9 | +2 | 円 | 一致 |
| 156 | +10 | 円 | vola_gate/scene_diff.out:18 | +10 | 円 | 一致 |
| 156 | +0 | 円 | vola_gate/scene_diff.out:18 | +0 | 円 | 一致 |
| 156 | +19 | 円 | vola_gate/scene_diff.out:18 | +19 | 円 | 一致 |
| 156 | +135 | 円 | vola_gate/scene_diff.out:27 | +135 | 円 | 一致 |
| 156 | +90 | 円 | vola_gate/scene_diff.out:27 | +90 | 円 | 一致 |
| 156 | +171 | 円 | vola_gate/scene_diff.out:27 | +171 | 円 | 一致 |
| 158 | −163 | 円 | vola_gate/scene_diff.out:22 | -163 | 円 | 一致 |
| 179 | +45.8 | 円 | vola_gate/compare.md:7 | +45.8 | 円 | 一致 |
| 179 | −317.3 | 円 | vola_gate/compare.md:7 | -317.3 | 円 | 一致 |
| 179 | +501,328 | 円 | vola_gate/compare.md:7 | +501,328 | 円 | 一致 |
| 180 | +52.4 | 円 | vola_gate/compare.md:8 | +52.4 | 円 | 一致 |
| 180 | −366.1 | 円 | vola_gate/compare.md:8 | -366.1 | 円 | 一致 |
| 180 | +473,742 | 円 | vola_gate/compare.md:8 | +473,742 | 円 | 一致 |
| 181 | +65.7 | 円 | vola_gate/compare.md:9 | +65.7 | 円 | 一致 |
| 181 | −463.9 | 円 | vola_gate/compare.md:9 | -463.9 | 円 | 一致 |
| 181 | +418,054 | 円 | vola_gate/compare.md:9 | +418,054 | 円 | 一致 |
| 182 | +40.5 | 円 | vola_gate/compare.md:6 | +40.5 | 円 | 一致 |
| 182 | −281.0 | 円 | vola_gate/compare.md:6 | -281.0 | 円 | 一致 |
| 182 | +532,210 | 円 | vola_gate/compare.md:6 | +532,210 | 円 | 一致 |
| 183 | +34.3 | 円 | vola_gate/compare.md:16 | +34.3 | 円 | 一致 |
| 183 | −252.2 | 円 | vola_gate/compare.md:16 | -252.2 | 円 | 一致 |
| 183 | −373,103 | 円 | vola_gate/compare.md:16 | -373,103 | 円 | 一致 |
| 184 | +38.4 | 円 | vola_gate/compare.md:17 | +38.4 | 円 | 一致 |
| 184 | −281.2 | 円 | vola_gate/compare.md:17 | -281.2 | 円 | 一致 |
| 184 | −263,513 | 円 | vola_gate/compare.md:17 | -263,513 | 円 | 一致 |
| 185 | +48.5 | 円 | vola_gate/compare.md:18 | +48.5 | 円 | 一致 |
| 185 | −354.4 | 円 | vola_gate/compare.md:18 | -354.4 | 円 | 一致 |
| 185 | −127,314 | 円 | vola_gate/compare.md:18 | -127,314 | 円 | 一致 |
| 186 | +32.2 | 円 | vola_gate/compare.md:15 | +32.2 | 円 | 一致 |
| 186 | −238.4 | 円 | vola_gate/compare.md:15 | -238.4 | 円 | 一致 |
| 186 | −400,821 | 円 | vola_gate/compare.md:15 | -400,821 | 円 | 一致 |
| 190 | +310 | 円 | vola_gate/fam_tables.md:34 | +310 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | +113 | 円 | vola_gate/fam_tables.md:34 | +113 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | +32 | 円 | vola_gate/fam_tables.md:35 | +32 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | −94 | 円 | vola_gate/fam_tables.md:35 | -94 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | +164 | 円 | vola_gate/fam_tables.md:35 | +164 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | −367 | 円 | vola_gate/fam_tables.md:35 | -367 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | −452 | 円 | vola_gate/fam_tables.md:35 | -452 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | −282 | 円 | vola_gate/compare.md:25 | -282.1 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | +286 | 円 | vola_gate/fam_tables.md:36 | +286 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | +104 | 円 | vola_gate/fam_tables.md:36 | +104 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | +36 | 円 | vola_gate/fam_tables.md:37 | +36 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | −284 | 円 | vola_gate/fam_tables.md:37 | -284 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | −368 | 円 | vola_gate/fam_tables.md:37 | -368 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | −199 | 円 | vola_gate/fam_tables.md:37 | -199 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | +244 | 円 | vola_gate/fam_tables.md:38 | +244 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | +196 | 円 | vola_gate/fam_tables.md:38 | +196 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | +293 | 円 | vola_gate/fam_tables.md:38 | +293 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | +82 | 円 | vola_gate/fam_tables.md:38 | +82 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | +59 | 円 | vola_gate/fam_tables.md:38 | +59 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | +102 | 円 | vola_gate/fam_tables.md:38 | +102 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | +40 | 円 | vola_gate/fam_tables.md:9 | 40.0 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | −67 | 円 | vola_gate/fam_tables.md:39 | -67 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | +157 | 円 | vola_gate/fam_tables.md:39 | +157 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | −168 | 円 | vola_gate/fam_tables.md:39 | -168 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | −249 | 円 | vola_gate/fam_tables.md:39 | -249 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | −92 | 円 | vola_gate/fam_tables.md:39 | -92 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | +329 | 円 | vola_gate/fam_tables.md:40 | +329 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | +117 | 円 | vola_gate/fam_tables.md:40 | +117 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | +33 | 円 | vola_gate/fam_tables.md:41 | +33 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 190 | −390 | 円 | vola_gate/fam_tables.md:41 | -390 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 192 | +40.5 | 円 | vola_gate/compare.md:6 | +40.5 | 円 | 一致 |
| 192 | +65.7 | 円 | vola_gate/compare.md:9 | +65.7 | 円 | 一致 |
| 192 | −281.0 | 円 | vola_gate/compare.md:6 | -281.0 | 円 | 一致 |
| 192 | −463.9 | 円 | vola_gate/compare.md:9 | -463.9 | 円 | 一致 |
| 192 | −390 | 円 | vola_gate/fam_tables.md:41 | -390 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 192 | −168 | 円 | vola_gate/fam_tables.md:39 | -168 | 円 | 一致(値は合う。ただし文書が指した出所には無く、指していない円のファイルにある) |
| 192 | +640,619 | 円 | vola_gate_p50/diag_tables.md:44(写しは vola_gate/fam_tables.md:47) | +32031 bp × 20 = +640,620 / 写し +640,619 | bp | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 192 | +653,497 | 円 | base/diag_tables.md:44(写しは vola_gate/fam_tables.md:48) | +32675 bp × 20 = +653,500 / 写し +653,497 | bp | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 192 | −698,735 | 円 | vola_gate_p50/diag_tables.md:44(写しは vola_gate/fam_tables.md:47) | -34937 bp × 20 = −698,740 / 写し −698,735 | bp | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 192 | −766,805 | 円 | base/diag_tables.md:44(写しは vola_gate/fam_tables.md:48) | -38340 bp × 20 = −766,800 / 写し −766,805 | bp | 単位の誤り(指し方: 円の値の出所に bp のファイルだけを指した。値は ×20 で合う) |
| 214 | +9,788,194 | 円 | vola_gate/fam_tables.md:54 | +9,788,194 | 円 | 一致 |
| 214 | 6.75 | move_bp | vola_gate/fam_tables.md:54 | 6.75 | move_bp | 一致 |
| 214 | −5.61 | move_bp | vola_gate/fam_tables.md:54 | -5.61 | move_bp | 一致 |
| 214 | −10,280,798 | 円 | vola_gate/fam_tables.md:55+:56 | −4,545,193 + −5,735,605 = −10,280,798 | 円 | 一致(出所の行から計算して合う) |
| 214 | −33.58 | move_bp | vola_gate/fam_tables.md:55 | -33.58 | move_bp | 一致 |
| 214 | −36.63 | move_bp | vola_gate/fam_tables.md:56 | -36.63 | move_bp | 一致 |
| 215 | +9,009,089 | 円 | vola_gate/fam_tables.md:58 | +9,009,089 | 円 | 一致 |
| 215 | 7.93 | move_bp | vola_gate/fam_tables.md:58 | 7.93 | move_bp | 一致 |
| 215 | −6.76 | move_bp | vola_gate/fam_tables.md:58 | -6.76 | move_bp | 一致 |
| 215 | −9,372,504 | 円 | vola_gate/fam_tables.md:59+:60 | −4,195,580 + −5,176,924 = −9,372,504 | 円 | 一致(出所の行から計算して合う) |
| 215 | −39.40 | move_bp | vola_gate/fam_tables.md:59 | -39.40 | move_bp | 一致 |
| 215 | −43.32 | move_bp | vola_gate/fam_tables.md:60 | -43.32 | move_bp | 一致 |
| 216 | +7,222,374 | 円 | vola_gate/fam_tables.md:62 | +7,222,374 | 円 | 一致 |
| 216 | 10.51 | move_bp | vola_gate/fam_tables.md:62 | 10.51 | move_bp | 一致 |
| 216 | −9.07 | move_bp | vola_gate/fam_tables.md:62 | -9.07 | move_bp | 一致 |
| 216 | −7,410,301 | 円 | vola_gate/fam_tables.md:63+:64 | −3,369,593 + −4,040,708 = −7,410,301 | 円 | 一致(出所の行から計算して合う) |
| 216 | −51.86 | move_bp | vola_gate/fam_tables.md:63 | -51.86 | move_bp | 一致 |
| 216 | −56.56 | move_bp | vola_gate/fam_tables.md:64 | -56.56 | move_bp | 一致 |
| 217 | +10,177,344 | 円 | vola_gate/fam_tables.md:66 | +10,177,344 | 円 | 一致 |
| 217 | 6.02 | move_bp | vola_gate/fam_tables.md:66 | 6.02 | move_bp | 一致 |
| 217 | −4.74 | move_bp | vola_gate/fam_tables.md:66 | -4.74 | move_bp | 一致 |
| 217 | −10,701,050 | 円 | vola_gate/fam_tables.md:67+:68 | −4,695,044 + −6,006,006 = −10,701,050 | 円 | 一致(出所の行から計算して合う) |
| 217 | −30.50 | move_bp | vola_gate/fam_tables.md:67 | -30.50 | move_bp | 一致 |
| 217 | −32.38 | move_bp | vola_gate/fam_tables.md:68 | -32.38 | move_bp | 一致 |
| 219 | −0.35 | move_bp | vola_gate/fam_tables.md:73 | -0.35 | move_bp | 一致 |
| 219 | −0.87 | move_bp | vola_gate/fam_tables.md:75 | -0.87(p50 15 分) | move_bp | 一致 |
| 219 | +0.13 | move_bp | vola_gate/fam_tables.md:73 | +0.13 | move_bp | 一致 |
| 219 | −0.28 | move_bp | vola_gate/fam_tables.md:74 | -0.28 | move_bp | 一致 |
| 219 | −0.91 | move_bp | vola_gate/fam_tables.md:74 | -0.91 | move_bp | 一致 |
| 219 | +0.30 | move_bp | vola_gate/fam_tables.md:74 | +0.30 | move_bp | 一致 |
| 219 | −0.03 | move_bp | vola_gate/fam_tables.md:75 | -0.03 | move_bp | 一致 |
| 219 | −0.97 | move_bp | vola_gate/fam_tables.md:75 | -0.97 | move_bp | 一致 |
| 219 | +0.88 | move_bp | vola_gate/fam_tables.md:75 | +0.88 | move_bp | 一致 |
| 219 | −0.42 | move_bp | vola_gate/fam_tables.md:75 | -0.42 | move_bp | 一致 |
| 219 | −0.89 | move_bp | base/diag_paths.md:23 | -0.89 | move_bp | 一致 |
| 219 | +0.01 | move_bp | base/diag_paths.md:24 | +0.01 | move_bp | 一致 |
| 219 | −0.66 | move_bp | base/diag_paths.md:23 | -0.66 | move_bp | 一致 |
| 219 | −0.87 | move_bp | vola_gate/fam_tables.md:75 | -0.87(p50 15 分) | move_bp | 一致 |
| 242 | −0.44 | move_bp | vola_gate/blocked_vola_gate_p50.md:41 | -0.44 | move_bp | 一致 |
| 242 | −0.54 | move_bp | vola_gate/blocked_vola_gate_p50.md:41 | -0.54 | move_bp | 一致 |
| 242 | −0.34 | move_bp | vola_gate/blocked_vola_gate_p50.md:41 | -0.34 | move_bp | 一致 |
| 242 | −0.10 | move_bp | vola_gate/blocked_vola_gate_p50.md:59 | -0.10 | move_bp | 一致 |
| 242 | −0.13 | move_bp | vola_gate/blocked_vola_gate_p50.md:59 | -0.13 | move_bp | 一致 |
| 242 | −0.06 | move_bp | vola_gate/blocked_vola_gate_p50.md:33 | -0.06 | move_bp | 一致 |
| 243 | −0.79 | move_bp | vola_gate/blocked_vola_gate_p50.md:42 | -0.79 | move_bp | 一致 |
| 243 | −1.04 | move_bp | vola_gate/blocked_vola_gate_p50.md:42 | -1.04 | move_bp | 一致 |
| 243 | −0.54 | move_bp | vola_gate/blocked_vola_gate_p50.md:41 | -0.54 | move_bp | 一致 |
| 243 | −0.27 | move_bp | vola_gate/blocked_vola_gate_p50.md:60 | -0.27 | move_bp | 一致 |
| 243 | −0.34 | move_bp | vola_gate/blocked_vola_gate_p50.md:41 | -0.34 | move_bp | 一致 |
| 243 | −0.19 | move_bp | vola_gate/blocked_vola_gate_p50.md:22 | -0.19 | move_bp | 一致 |
| 244 | −1.03 | move_bp | vola_gate/blocked_vola_gate_p50.md:43 | -1.03 | move_bp | 一致 |
| 244 | −1.51 | move_bp | vola_gate/blocked_vola_gate_p50.md:43 | -1.51 | move_bp | 一致 |
| 244 | −0.59 | move_bp | vola_gate/blocked_vola_gate_p50.md:43 | -0.59 | move_bp | 一致 |
| 244 | −0.48 | move_bp | vola_gate/blocked_vola_gate_p50.md:61 | -0.48 | move_bp | 一致 |
| 244 | −0.64 | move_bp | vola_gate/blocked_vola_gate_p50.md:61 | -0.64 | move_bp | 一致 |
| 244 | −0.34 | move_bp | vola_gate/blocked_vola_gate_p50.md:41 | -0.34 | move_bp | 一致 |
| 245 | −0.31 | move_bp | vola_gate/blocked_vola_gate_p50.md:44 | -0.31 | move_bp | 一致 |
| 245 | −1.27 | move_bp | vola_gate/blocked_vola_gate_p50.md:44 | -1.27 | move_bp | 一致 |
| 245 | +0.57 | move_bp | vola_gate/blocked_vola_gate_p50.md:44 | +0.57 | move_bp | 一致 |
| 245 | −0.78 | move_bp | vola_gate/blocked_vola_gate_p50.md:62 | -0.78 | move_bp | 一致 |
| 245 | −1.14 | move_bp | vola_gate/blocked_vola_gate_p50.md:62 | -1.14 | move_bp | 一致 |
| 245 | −0.42 | move_bp | vola_gate/blocked_vola_gate_p50.md:22 | -0.42 | move_bp | 一致 |
| 247 | −0.78 | move_bp | vola_gate/blocked_vola_gate_p50.md:62 | -0.78 | move_bp | 一致 |
| 247 | −1.27 | move_bp | vola_gate/blocked_vola_gate_p50.md:44 | -1.27 | move_bp | 一致 |
| 247 | +0.57 | move_bp | vola_gate/blocked_vola_gate_p50.md:44 | +0.57 | move_bp | 一致 |
| 247 | +1.36 | move_bp | vola_gate/blocked_vola_gate_p50.md:44 | +1.36 | move_bp | 一致 |
| 247 | +0.43 | move_bp | vola_gate/blocked_vola_gate_p50.md:44 | +0.43 | move_bp | 一致 |
| 247 | +2.34 | move_bp | vola_gate/blocked_vola_gate_p50.md:44 | +2.34 | move_bp | 一致 |
| 262 | +2.5 | 円 | vola_gate/fam_tables.md:89 | +2.5 | 円 | 一致 |
| 262 | +1.3 | 円 | vola_gate/fam_tables.md:89 | +1.3 | 円 | 一致 |
| 262 | +3.6 | 円 | vola_gate/fam_tables.md:89 | +3.6 | 円 | 一致 |
| 262 | +3.0 | 円 | vola_gate/fam_tables.md:46 | 3 | 円 | 一致 |
| 262 | +1.7 | 円 | vola_gate/fam_tables.md:90 | +1.7 | 円 | 一致 |
| 262 | +4.3 | 円 | vola_gate/fam_tables.md:90 | +4.3 | 円 | 一致 |
| 262 | +4.4 | 円 | vola_gate/fam_tables.md:91 | +4.4 | 円 | 一致 |
| 262 | +2.3 | 円 | vola_gate/fam_tables.md:91 | +2.3 | 円 | 一致 |
| 262 | +6.5 | 円 | vola_gate/fam_tables.md:91 | +6.5 | 円 | 一致 |
| 262 | −2.2 | 円 | vola_gate/fam_tables.md:91 | -2.2 | 円 | 一致 |
| 262 | −3.6 | 円 | vola_gate/fam_tables.md:89 | -3.6(p10 3 分超〜11 分の区間の下) | 円 | 一致 |
| 262 | −0.8 | 円 | vola_gate/fam_tables.md:92 | -0.8 | 円 | 一致 |
| 262 | −1.6 | 円 | vola_gate/fam_tables.md:92 | -1.6 | 円 | 一致 |
| 262 | −3.2 | 円 | vola_gate/fam_tables.md:92 | -3.2 | 円 | 一致 |
| 262 | +0.1 | 円 | vola_gate/fam_tables.md:9 | 0 | 円 | 一致 |
| 262 | −1.3 | 円 | vola_gate/fam_tables.md:91 | -1.3 | 円 | 一致 |
| 262 | −3.9 | 円 | vola_gate/fam_tables.md:91 | -3.9 | 円 | 一致 |
| 262 | +1.2 | 円 | vola_gate/fam_tables.md:91 | +1.2 | 円 | 一致 |
| 262 | +2.4 | 円 | vola_gate/fam_tables.md:92 | +2.4 | 円 | 一致 |
| 262 | −2.0 | 円 | vola_gate/fam_tables.md:92 | -2.0 | 円 | 一致 |
| 283 | −1.1 | 円 | vola_gate/band_migration.out:9 | -1 | 円 | 一致 |
| 283 | −16.1 | 円 | vola_gate/fam_tables.md:98 | -16.1 | 円 | 一致 |
| 283 | +12.5 | 円 | vola_gate/fam_tables.md:98 | +12.5 | 円 | 一致 |
| 283 | 20.5 | 円 | vola_gate/fam_tables.md:98 | +20.5 | 円 | 一致 |
| 283 | −21 | 円 | vola_gate/fam_tables.md:98 | -21 | 円 | 一致 |
| 283 | −47 | 円 | vola_gate/fam_tables.md:98 | -47 | 円 | 一致 |
| 283 | +5 | 円 | vola_gate/fam_tables.md:45 | 5 | 円 | 一致 |
| 283 | 39 | 円 | vola_gate/fam_tables.md:98 | +39 | 円 | 一致 |
| 283 | +19 | 円 | vola_gate/fam_tables.md:98 | +19 | 円 | 一致 |
| 283 | +11 | 円 | vola_gate/fam_tables.md:89 | 11 | 円 | 一致 |
| 283 | +27 | 円 | vola_gate/fam_tables.md:98 | +27 | 円 | 一致 |
| 283 | 11 | 円 | vola_gate/fam_tables.md:89 | 11 | 円 | 一致 |
| 283 | +271 | 円 | vola_gate/fam_tables.md:98 | +271 | 円 | 一致 |
| 283 | −107 | 円 | vola_gate/fam_tables.md:98 | -107 | 円 | 一致 |
| 283 | −26 | 円 | vola_gate/fam_tables.md:98 | -26 | 円 | 一致 |
| 283 | +16 | 円 | vola_gate/fam_tables.md:98 | +16 | 円 | 一致 |
| 283 | +17 | 円 | vola_gate/fam_tables.md:98 | +17 | 円 | 一致 |
| 283 | +57 | 円 | vola_gate/fam_tables.md:98 | +57 | 円 | 一致 |
| 284 | +26.8 | 円 | vola_gate/fam_tables.md:99 | +26.8 | 円 | 一致 |
| 284 | +1.4 | 円 | vola_gate/band_migration.out:15 | +1 | 円 | 一致 |
| 284 | +52.9 | 円 | vola_gate/fam_tables.md:99 | +52.9 | 円 | 一致 |
| 284 | 36.7 | 円 | vola_gate/fam_tables.md:99 | +36.7 | 円 | 一致 |
| 284 | −40 | 円 | vola_gate/fam_tables.md:99 | -40 | 円 | 一致 |
| 284 | −87 | 円 | vola_gate/fam_tables.md:99 | -87 | 円 | 一致 |
| 284 | +8 | 円 | vola_gate/fam_tables.md:99 | +8 | 円 | 一致 |
| 284 | 66 | 円 | vola_gate/fam_tables.md:99 | +66 | 円 | 一致 |
| 284 | +93 | 円 | vola_gate/fam_tables.md:99 | +93 | 円 | 一致 |
| 284 | +74 | 円 | vola_gate/fam_tables.md:99 | +74 | 円 | 一致 |
| 284 | +120 | 円 | vola_gate/fam_tables.md:99 | +120 | 円 | 一致 |
| 284 | 32 | 円 | vola_gate/fam_tables.md:99 | +32 | 円 | 一致 |
| 284 | −44 | 円 | vola_gate/band_migration.out:17 | -44 | 円 | 一致 |
| 284 | +76 | 円 | vola_gate/fam_tables.md:99 | +76 | 円 | 一致 |
| 284 | +11 | 円 | vola_gate/fam_tables.md:99 | +11 | 円 | 一致 |
| 284 | +41 | 円 | vola_gate/fam_tables.md:99 | +41 | 円 | 一致 |
| 284 | +261 | 円 | vola_gate/fam_tables.md:99 | +261 | 円 | 一致 |
| 285 | +54.2 | 円 | vola_gate/fam_tables.md:100 | +54.2 | 円 | 一致 |
| 285 | +14.8 | 円 | vola_gate/fam_tables.md:48 | +14.8 | 円 | 一致 |
| 285 | +95.1 | 円 | vola_gate/fam_tables.md:100 | +95.1 | 円 | 一致 |
| 285 | 55.9 | 円 | vola_gate/fam_tables.md:100 | +55.9 | 円 | 一致 |
| 285 | −78 | 円 | vola_gate/fam_tables.md:100 | -78 | 円 | 一致 |
| 285 | −144 | 円 | vola_gate/fam_tables.md:100 | -144 | 円 | 一致 |
| 285 | −7 | 円 | vola_gate/fam_tables.md:100 | -7 | 円 | 一致 |
| 285 | 97 | 円 | vola_gate/fam_tables.md:100 | +97 | 円 | 一致 |
| 285 | +186 | 円 | vola_gate/fam_tables.md:100 | +186 | 円 | 一致 |
| 285 | +148 | 円 | vola_gate/fam_tables.md:100 | +148 | 円 | 一致 |
| 285 | +228 | 円 | vola_gate/fam_tables.md:100 | +228 | 円 | 一致 |
| 285 | 58 | 円 | vola_gate/fam_tables.md:100 | +58 | 円 | 一致 |
| 285 | −79 | 円 | vola_gate/fam_tables.md:100 | -79 | 円 | 一致 |
| 285 | −105 | 円 | vola_gate/fam_tables.md:100 | -105 | 円 | 一致 |
| 285 | +111 | 円 | vola_gate/fam_tables.md:100 | +111 | 円 | 一致 |
| 285 | +93 | 円 | vola_gate/fam_tables.md:100 | +93 | 円 | 一致 |
| 285 | +148 | 円 | vola_gate/fam_tables.md:100 | +148 | 円 | 一致 |
| 285 | +435 | 円 | vola_gate/fam_tables.md:100 | +435 | 円 | 一致 |
| 287 | +388 | 円 | vola_gate/fam_tables.md:108 | +388 | 円 | 一致 |
| 287 | −145 | 円 | vola_gate/fam_tables.md:108 | -145 | 円 | 一致 |
| 287 | −79 | 円 | vola_gate/fam_tables.md:100 | -79 | 円 | 一致 |
| 287 | −105 | 円 | vola_gate/fam_tables.md:100 | -105 | 円 | 一致 |
| 287 | −39 | 円 | vola_gate/fam_tables.md:108 | -39 | 円 | 一致 |
| 287 | +111 | 円 | vola_gate/fam_tables.md:100 | +111 | 円 | 一致 |
| 287 | +93 | 円 | vola_gate/fam_tables.md:100 | +93 | 円 | 一致 |
| 287 | +148 | 円 | vola_gate/fam_tables.md:100 | +148 | 円 | 一致 |
| 287 | +435 | 円 | vola_gate/fam_tables.md:100 | +435 | 円 | 一致 |
| 287 | +344 | 円 | vola_gate/fam_tables.md:107 | +344 | 円 | 一致 |
| 287 | −154 | 円 | vola_gate/fam_tables.md:107 | -154 | 円 | 一致 |
| 287 | −44 | 円 | vola_gate/band_migration.out:17 | -44 | 円 | 一致 |
| 287 | −11 | 円 | vola_gate/fam_tables.md:107 | -11 | 円 | 一致 |
| 287 | +18 | 円 | vola_gate/fam_tables.md:107 | +18 | 円 | 一致 |
| 287 | +76 | 円 | vola_gate/fam_tables.md:99 | +76 | 円 | 一致 |
| 287 | +11 | 円 | vola_gate/fam_tables.md:99 | +11 | 円 | 一致 |
| 287 | +41 | 円 | vola_gate/fam_tables.md:99 | +41 | 円 | 一致 |
| 287 | +261 | 円 | vola_gate/fam_tables.md:99 | +261 | 円 | 一致 |
| 287 | +271 | 円 | vola_gate/fam_tables.md:98 | +271 | 円 | 一致 |
| 287 | −107 | 円 | vola_gate/fam_tables.md:98 | -107 | 円 | 一致 |
| 287 | −26 | 円 | vola_gate/fam_tables.md:98 | -26 | 円 | 一致 |
| 287 | +10 | 円 | vola_gate/fam_tables.md:106 | +10 | 円 | 一致 |
| 287 | +16 | 円 | vola_gate/fam_tables.md:98 | +16 | 円 | 一致 |
| 287 | +17 | 円 | vola_gate/fam_tables.md:98 | +17 | 円 | 一致 |
| 287 | −0 | 円 | vola_gate/band_migration.out:3 | 0 | 円 | 一致 |
| 287 | +4 | 円 | vola_gate/fam_tables.md:106 | +4 | 円 | 一致 |
| 287 | +57 | 円 | vola_gate/fam_tables.md:98 | +57 | 円 | 一致 |
| 289 | +1,938 | 円 | vola_gate/fam_tables.md:114 | +1,938 | 円 | 一致 |
| 289 | −5,822 | 円 | vola_gate/fam_tables.md:114 | -5,822 | 円 | 一致 |
| 289 | −719 | 円 | vola_gate/fam_tables.md:114 | -719 | 円 | 一致 |
| 289 | +2,468 | 円 | vola_gate/fam_tables.md:115 | +2,468 | 円 | 一致 |
| 289 | −7,402 | 円 | vola_gate/fam_tables.md:115 | -7,402 | 円 | 一致 |
| 289 | −83,773 | 円 | vola_gate/fam_tables.md:115 | -83,773 | 円 | 一致 |
| 289 | +2,205 | 円 | vola_gate/fam_tables.md:116 | +2,205 | 円 | 一致 |
| 289 | +5,310 | 円 | vola_gate/fam_tables.md:116 | +5,310 | 円 | 一致 |
| 289 | −151,835 | 円 | vola_gate/fam_tables.md:116 | -151,835 | 円 | 一致 |
| 295 | +3.12 | 円 | vola_gate/fam_tables.md:45 | 3 | 円 | 一致 |
| 295 | +29,035 | 円 | vola_gate/band_migration.out:5 | +29,035 | 円 | 一致 |
| 295 | −20 | 円 | vola_gate/band_migration.out:5 | -20 | 円 | 一致 |
| 296 | +0.14 | 円 | vola_gate/band_migration.out:3 | 0 | 円 | 一致 |
| 296 | +2,750 | 円 | vola_gate/band_migration.out:7 | +2,750 | 円 | 一致 |
| 296 | −2 | 円 | vola_gate/band_migration.out:7 | -2 | 円 | 一致 |
| 297 | +0.93 | 円 | vola_gate/band_migration.out:14 | +1 | 円 | 一致 |
| 297 | +4,102 | 円 | vola_gate/band_migration.out:11 | +4,102 | 円 | 一致 |
| 297 | −3 | 円 | vola_gate/band_migration.out:10 | -3 | 円 | 一致 |
| 298 | −3.17 | 円 | vola_gate/band_migration.out:10 | -3 | 円 | 一致 |
| 298 | −36,607 | 円 | vola_gate/band_migration.out:13 | -36,607 | 円 | 一致 |
| 298 | +25 | 円 | vola_gate/band_migration.out:13 | +25 | 円 | 一致 |
| 299 | +3.51 | 円 | vola_gate/band_migration.out:19 | +4 | 円 | 一致 |
| 299 | +63,908 | 円 | vola_gate/band_migration.out:17 | +63,908 | 円 | 一致 |
| 299 | −44 | 円 | vola_gate/band_migration.out:17 | -44 | 円 | 一致 |
| 300 | −0.13 | 円 | vola_gate/band_migration.out:15 | 0 | 円 | 一致 |
| 300 | −5,561 | 円 | vola_gate/band_migration.out:19 | -5,561 | 円 | 一致 |
| 300 | +4 | 円 | vola_gate/band_migration.out:19 | +4 | 円 | 一致 |
| 301 | +1.48 | 円 | vola_gate/band_migration.out:15 | +1 | 円 | 一致 |
| 301 | +17,183 | 円 | vola_gate/band_migration.out:23 | +17,183 | 円 | 一致 |
| 301 | −12 | 円 | vola_gate/band_migration.out:23 | -12 | 円 | 一致 |
| 302 | −4.77 | 円 | vola_gate/band_migration.out:23 | −159,303 ÷ 33,412 = −4.768 | 円 | 一致(出所の行から計算して合う) |
| 302 | −159,303 | 円 | vola_gate/band_migration.out:25 | -159,303 | 円 | 一致 |
| 302 | +108 | 円 | vola_gate/band_migration.out:25 | +108 | 円 | 一致 |
| 303 | +4.23 | 円 | vola_gate/fam_tables.md:91 | +4.2 | 円 | 一致 |
| 303 | +125,811 | 円 | vola_gate/band_migration.out:29 | +125,811 | 円 | 一致 |
| 303 | −86 | 円 | vola_gate/band_migration.out:29 | -86 | 円 | 一致 |
| 304 | −0.03 | 円 | vola_gate/band_migration.out:27 | 0 | 円 | 一致 |
| 304 | −2,224 | 円 | vola_gate/band_migration.out:31 | -2,224 | 円 | 一致 |
| 304 | +2 | 円 | vola_gate/band_migration.out:31 | +2 | 円 | 一致 |
| 305 | +2.07 | 円 | vola_gate/band_migration.out:31 | +2 | 円 | 一致 |
| 305 | +50,033 | 円 | vola_gate/band_migration.out:35 | +50,033 | 円 | 一致 |
| 305 | −34 | 円 | vola_gate/band_migration.out:35 | -34 | 円 | 一致 |
| 306 | −4.44 | 円 | vola_gate/band_migration.out:37 | −325,454 ÷ 73,289 = −4.441 | 円 | 一致(出所の行から計算して合う) |
| 306 | −325,454 | 円 | vola_gate/band_migration.out:37 | -325,454 | 円 | 一致 |
| 306 | +221 | 円 | vola_gate/band_migration.out:37 | +221 | 円 | 一致 |
| 308 | +6 | 円 | vola_gate/band_migration.out:28 | +6 | 円 | 一致 |
| 308 | −2 | 円 | vola_gate/band_migration.out:34 | -2 | 円 | 一致 |
| 308 | 1 | 円 | vola_gate/band_migration.out:27 | +1 | 円 | 一致 |
| 310 | +333,136 | 円 | vola_gate/zero_reason.out:12 | +333,136 | 円 | 一致 |
| 310 | +12.6 | 円 | vola_gate/zero_reason.out:12 | +12.6 | 円 | 一致 |
| 310 | −207,325 | 円 | vola_gate/zero_reason.out:11 | -207,325 | 円 | 一致 |
| 310 | −62.4 | 円 | vola_gate/zero_reason.out:11 | -62.4 | 円 | 一致 |
| 310 | +11.9 | 円 | vola_gate/zero_reason.out:14 | +11.9 | 円 | 一致 |
| 310 | −68.0 | 円 | vola_gate/zero_reason.out:13 | -68.0 | 円 | 一致 |
| 310 | +7.3 | 円 | vola_gate_p10/diag_tables.md:46 | +0.37 | bp(×20 で円) | 一致 |
| 310 | −30.8 | 円 | vola_gate/zero_reason.out:3 | -30.8 | 円 | 一致 |
| 310 | +9.5 | 円 | vola_gate_p25/diag_tables.md:46 | +0.48 | bp(×20 で円) | 一致 |
| 310 | −44.1 | 円 | vola_gate/band_migration.out:17 | -44 | 円 | 一致 |
| 310 | +4.23 | 円 | vola_gate/band_migration.out:19 | +4 | 円 | 一致 |
| 316 | +31,786 | 円 | vola_gate/gate_overlap.out:3 | +31,786 | 円 | 一致 |
| 316 | +46,912 | 円 | vola_gate/gate_overlap.out:3 | +46,912 | 円 | 一致 |
| 316 | +34,628 | 円 | vola_gate/gate_overlap.out:3 | +34,628 | 円 | 一致 |
| 316 | −2,842 | 円 | vola_gate/gate_overlap.out:3 | -2,842 | 円 | 一致 |
| 316 | +12,284 | 円 | vola_gate/gate_overlap.out:3 | +12,284 | 円 | 一致 |
| 317 | −32,505 | 円 | vola_gate/gate_overlap.out:4 | -32,505 | 円 | 一致 |
| 317 | −34,509 | 円 | vola_gate/gate_overlap.out:4 | -34,509 | 円 | 一致 |
| 317 | −22,038 | 円 | vola_gate/gate_overlap.out:4 | -22,038 | 円 | 一致 |
| 317 | −10,467 | 円 | vola_gate/gate_overlap.out:4 | -10,467 | 円 | 一致 |
| 317 | −12,471 | 円 | vola_gate/gate_overlap.out:4 | -12,471 | 円 | 一致 |
| 318 | +58,347 | 円 | vola_gate/gate_overlap.out:7 | +58,347 | 円 | 一致 |
| 318 | +97,492 | 円 | vola_gate/gate_overlap.out:7 | +97,492 | 円 | 一致 |
| 318 | +83,689 | 円 | vola_gate/gate_overlap.out:7 | +83,689 | 円 | 一致 |
| 318 | −25,342 | 円 | vola_gate/gate_overlap.out:7 | -25,342 | 円 | 一致 |
| 318 | +13,803 | 円 | vola_gate/gate_overlap.out:7 | +13,803 | 円 | 一致 |
| 319 | −142,120 | 円 | vola_gate/gate_overlap.out:8 | -142,120 | 円 | 一致 |
| 319 | −125,278 | 円 | vola_gate/gate_overlap.out:8 | -125,278 | 円 | 一致 |
| 319 | −106,826 | 円 | vola_gate/gate_overlap.out:8 | -106,826 | 円 | 一致 |
| 319 | −35,294 | 円 | vola_gate/gate_overlap.out:8 | -35,294 | 円 | 一致 |
| 319 | −18,451 | 円 | vola_gate/gate_overlap.out:8 | -18,451 | 円 | 一致 |
| 320 | +123,586 | 円 | vola_gate/gate_overlap.out:11 | +123,586 | 円 | 一致 |
| 320 | +204,609 | 円 | vola_gate/gate_overlap.out:11 | +204,609 | 円 | 一致 |
| 320 | +170,017 | 円 | vola_gate/gate_overlap.out:11 | +170,017 | 円 | 一致 |
| 320 | −46,431 | 円 | vola_gate/gate_overlap.out:11 | -46,431 | 円 | 一致 |
| 320 | +34,592 | 円 | vola_gate/gate_overlap.out:11 | +34,592 | 円 | 一致 |
| 321 | −275,421 | 円 | vola_gate/gate_overlap.out:12 | -275,421 | 円 | 一致 |
| 321 | −285,913 | 円 | vola_gate/gate_overlap.out:12 | -285,913 | 円 | 一致 |
| 321 | −252,971 | 円 | vola_gate/gate_overlap.out:12 | -252,971 | 円 | 一致 |
| 321 | −22,450 | 円 | vola_gate/gate_overlap.out:12 | -22,450 | 円 | 一致 |
| 321 | −32,942 | 円 | vola_gate/gate_overlap.out:12 | -32,942 | 円 | 一致 |
| 324 | −21 | 円 | vola_gate/fam_tables.md:98 | -21 | 円 | 一致 |
| 324 | −40 | 円 | vola_gate/fam_tables.md:99 | -40 | 円 | 一致 |
| 324 | −78 | 円 | vola_gate/fam_tables.md:100 | -78 | 円 | 一致 |
| 324 | +19 | 円 | d7_fullperiod.out:22 | +19.2 | 円 | 一致 |
| 324 | +93 | 円 | vola_gate/fam_tables.md:99 | +93 | 円 | 一致 |
| 324 | +186 | 円 | vola_gate/fam_tables.md:100 | +186 | 円 | 一致 |
| 325 | +1,938 | 円 | vola_gate/fam_tables.md:114 | +1,938 | 円 | 一致 |
| 325 | +2,468 | 円 | vola_gate/fam_tables.md:115 | +2,468 | 円 | 一致 |
| 325 | +4.23 | 円 | vola_gate/fam_tables.md:91 | +4.2 | 円 | 一致 |
| 325 | −86 | 円 | vola_gate/band_migration.out:29 | -86 | 円 | 一致 |
| 325 | −4.44 | 円 | vola_gate/band_migration.out:37 | −4.441 | 円 | 一致(出所の行から計算して合う) |
| 325 | +221 | 円 | vola_gate/band_migration.out:37 | +221 | 円 | 一致 |
| 325 | −0.03 | 円 | vola_gate/band_migration.out:27 | 0 | 円 | 一致 |
| 325 | −4.44 | 円 | vola_gate/band_migration.out:37 | −4.441 | 円 | 一致(出所の行から計算して合う) |
| 326 | +170,017 | 円 | vola_gate/gate_overlap.out:11 | +170,017 | 円 | 一致 |
| 326 | −252,971 | 円 | vola_gate/gate_overlap.out:12 | -252,971 | 円 | 一致 |
| 327 | −46,431 | 円 | vola_gate/gate_overlap.out:11 | -46,431 | 円 | 一致 |
| 327 | −7.4 | 円 | vola_gate/fam_tables.md:100 | -7 | 円 | 一致 |
| 327 | −25,342 | 円 | vola_gate/gate_overlap.out:7 | -25,342 | 円 | 一致 |
| 327 | +34,592 | 円 | vola_gate/gate_overlap.out:11 | +34,592 | 円 | 一致 |
| 327 | −22,450 | 円 | vola_gate/gate_overlap.out:12 | -22,450 | 円 | 一致 |
| 327 | −32,942 | 円 | vola_gate/gate_overlap.out:12 | -32,942 | 円 | 一致 |
| 327 | −107 | 円 | range_lo/fam_tables.md:114 | -107(range_lo_p50 前半) | 円 | 一致 |
| 327 | −78 | 円 | vola_gate/fam_tables.md:100 | -78 | 円 | 一致 |
| 327 | +29 | 円 | vola_gate/levels_reason.out:27 | +29.1 | 円 | 一致 |
| 327 | +55 | 円 | vola_gate/fam_tables.md:47 | +54.6 | 円 | 一致 |
| 327 | +31.6 | 円 | vola_gate/gate_overlap.out:12 | −(−46,431 ÷ 1,469) = +31.61 | 円 | 一致(出所の行から計算して合う) |
| 327 | +23.5 | 円 | vola_gate/fam_tables.md:18 | +24 | 円 | 一致 |
| 327 | −27 | 円 | range_lo/band_migration.out:38・vola_gate/band_migration.out:27+:28 | (+1 + +6) − +34 = −27 | 円 | 一致(出所の行から計算して合う) |
| 327 | +34 | 円 | range_lo/band_migration.out:38 | +34 | 円 | 一致 |
| 327 | +7 | 円 | vola_gate/fam_tables.md:48 | +7.3 | 円 | 一致 |
| 377 | −86 | 円 | vola_gate/band_migration.out:29 | -86 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 377 | +221 | 円 | vola_gate/band_migration.out:37 | +221 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 379 | −163 | 円 | vola_gate/scene_diff.out:22 | -163 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 382 | −0.48 | move_bp | vola_gate/blocked_vola_gate_p50.md:61 | -0.48 | move_bp | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 382 | −1.03 | move_bp | vola_gate/fam_tables.md:84 | -1.03 | move_bp | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 383 | +40.5 | 円 | vola_gate/compare.md:6 | +40.5 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 383 | +65.7 | 円 | vola_gate/compare.md:9 | +65.7 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 384 | −46,431 | 円 | vola_gate/gate_overlap.out:11 | -46,431 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 384 | −7.4 | 円 | vola_gate/gate_overlap.out:11 | −46,431 ÷ 6,234 = −7.45 | 円 | 一致(出所の行から計算して合う) |
| 384 | −25,342 | 円 | vola_gate/gate_overlap.out:7 | -25,342 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 384 | +34,592 | 円 | vola_gate/gate_overlap.out:11 | +34,592 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 385 | +12.6 | 円 | vola_gate/zero_reason.out:12 | +12.6 | 円 | 一致 |
| 385 | −62.4 | 円 | vola_gate/zero_reason.out:11 | -62.4 | 円 | 一致 |
| 409 | +341 | 円 | vola_gate/fam_tables.md:16 | +341 | 円 | 一致 |
| 409 | +218 | 円 | vola_gate/fam_tables.md:16 | +218 | 円 | 一致 |
| 409 | +475 | 円 | vola_gate/fam_tables.md:16 | +475 | 円 | 一致 |
| 409 | −254 | 円 | vola_gate/fam_tables.md:16 | -254 | 円 | 一致 |
| 409 | −341 | 円 | vola_gate/fam_tables.md:16 | -341 | 円 | 一致 |
| 409 | −164 | 円 | vola_gate/fam_tables.md:16 | -164 | 円 | 一致 |
| 410 | +322 | 円 | vola_gate/fam_tables.md:17 | +322 | 円 | 一致 |
| 410 | +207 | 円 | vola_gate/fam_tables.md:17 | +207 | 円 | 一致 |
| 410 | +450 | 円 | vola_gate/fam_tables.md:17 | +450 | 円 | 一致 |
| 410 | −179 | 円 | vola_gate/fam_tables.md:17 | -179 | 円 | 一致 |
| 410 | −263 | 円 | vola_gate/fam_tables.md:17 | -263 | 円 | 一致 |
| 410 | −97 | 円 | vola_gate/fam_tables.md:17 | -97 | 円 | 一致 |
| 411 | +285 | 円 | vola_gate/fam_tables.md:18 | +285 | 円 | 一致 |
| 411 | +172 | 円 | vola_gate/fam_tables.md:18 | +172 | 円 | 一致 |
| 411 | +407 | 円 | vola_gate/fam_tables.md:18 | +407 | 円 | 一致 |
| 411 | −87 | 円 | vola_gate/fam_tables.md:18 | -87 | 円 | 一致 |
| 411 | −166 | 円 | vola_gate/fam_tables.md:18 | -166 | 円 | 一致 |
| 411 | −11 | 円 | vola_gate/fam_tables.md:18 | -11 | 円 | 一致 |
| 412 | +362 | 円 | vola_gate/fam_tables.md:19 | +362 | 円 | 一致 |
| 412 | +231 | 円 | vola_gate/fam_tables.md:19 | +231 | 円 | 一致 |
| 412 | +497 | 円 | vola_gate/fam_tables.md:19 | +497 | 円 | 一致 |
| 412 | −273 | 円 | vola_gate/fam_tables.md:19 | -273 | 円 | 一致 |
| 412 | −360 | 円 | vola_gate/fam_tables.md:19 | -360 | 円 | 一致 |
| 412 | −184 | 円 | vola_gate/fam_tables.md:19 | -184 | 円 | 一致 |
| 423 | +271 | 円 | vola_gate/fam_tables.md:98 | +271 | 円 | 一致 |
| 423 | −26 | 円 | vola_gate/fam_tables.md:98 | -26 | 円 | 一致 |
| 423 | +16 | 円 | vola_gate/fam_tables.md:98 | +16 | 円 | 一致 |
| 423 | −44 | 円 | vola_gate/fam_tables.md:99 | -44 | 円 | 一致 |
| 423 | +11 | 円 | vola_gate/fam_tables.md:99 | +11 | 円 | 一致 |
| 423 | −79 | 円 | vola_gate/fam_tables.md:100 | -79 | 円 | 一致 |
| 423 | +93 | 円 | vola_gate/fam_tables.md:100 | +93 | 円 | 一致 |
| 427 | −1.1 | 円 | vola_gate/fam_tables.md:98 | -1.1 | 円 | 一致 |
| 427 | −16.1 | 円 | vola_gate/fam_tables.md:98 | -16.1 | 円 | 一致 |
| 427 | +12.5 | 円 | vola_gate/fam_tables.md:98 | +12.5 | 円 | 一致 |
| 427 | 20.5 | 円 | vola_gate/fam_tables.md:98 | +20.5 | 円 | 一致 |
| 427 | −21 | 円 | vola_gate/fam_tables.md:98 | -21 | 円 | 一致 |
| 427 | −47 | 円 | vola_gate/fam_tables.md:98 | -47 | 円 | 一致 |
| 427 | +5 | 円 | vola_gate/fam_tables.md:45 | 5 | 円 | 一致 |
| 427 | +19 | 円 | vola_gate/fam_tables.md:98 | +19 | 円 | 一致 |
| 427 | +11 | 円 | vola_gate/fam_tables.md:89 | 11 | 円 | 一致 |
| 427 | +27 | 円 | vola_gate/fam_tables.md:98 | +27 | 円 | 一致 |
| 427 | −107 | 円 | vola_gate/fam_tables.md:98 | -107 | 円 | 一致 |
| 427 | +10 | 円 | vola_gate/fam_tables.md:106 | +10 | 円 | 一致 |
| 427 | +17 | 円 | vola_gate/fam_tables.md:98 | +17 | 円 | 一致 |
| 427 | +4 | 円 | vola_gate/fam_tables.md:106 | +4 | 円 | 一致 |
| 427 | +57 | 円 | vola_gate/fam_tables.md:98 | +57 | 円 | 一致 |
| 428 | +26.8 | 円 | vola_gate/fam_tables.md:99 | +26.8 | 円 | 一致 |
| 428 | +1.4 | 円 | vola_gate/fam_tables.md:99 | +1.4 | 円 | 一致 |
| 428 | +52.9 | 円 | vola_gate/fam_tables.md:99 | +52.9 | 円 | 一致 |
| 428 | 36.7 | 円 | vola_gate/fam_tables.md:99 | +36.7 | 円 | 一致 |
| 428 | −40 | 円 | vola_gate/fam_tables.md:99 | -40 | 円 | 一致 |
| 428 | −87 | 円 | vola_gate/fam_tables.md:99 | -87 | 円 | 一致 |
| 428 | +8 | 円 | vola_gate/fam_tables.md:99 | +8 | 円 | 一致 |
| 428 | +93 | 円 | vola_gate/fam_tables.md:99 | +93 | 円 | 一致 |
| 428 | +74 | 円 | vola_gate/fam_tables.md:99 | +74 | 円 | 一致 |
| 428 | +120 | 円 | vola_gate/fam_tables.md:99 | +120 | 円 | 一致 |
| 428 | −154 | 円 | vola_gate/fam_tables.md:107 | -154 | 円 | 一致 |
| 428 | −11 | 円 | vola_gate/fam_tables.md:107 | -11 | 円 | 一致 |
| 428 | +76 | 円 | vola_gate/fam_tables.md:99 | +76 | 円 | 一致 |
| 428 | +41 | 円 | vola_gate/fam_tables.md:99 | +41 | 円 | 一致 |
| 428 | +261 | 円 | vola_gate/fam_tables.md:99 | +261 | 円 | 一致 |
| 429 | +54.2 | 円 | vola_gate/fam_tables.md:100 | +54.2 | 円 | 一致 |
| 429 | +14.8 | 円 | vola_gate/fam_tables.md:48 | +14.8 | 円 | 一致 |
| 429 | +95.1 | 円 | vola_gate/fam_tables.md:100 | +95.1 | 円 | 一致 |
| 429 | 55.9 | 円 | vola_gate/fam_tables.md:100 | +55.9 | 円 | 一致 |
| 429 | −78 | 円 | vola_gate/fam_tables.md:100 | -78 | 円 | 一致 |
| 429 | −144 | 円 | vola_gate/fam_tables.md:100 | -144 | 円 | 一致 |
| 429 | −7 | 円 | vola_gate/fam_tables.md:100 | -7 | 円 | 一致 |
| 429 | +186 | 円 | vola_gate/fam_tables.md:100 | +186 | 円 | 一致 |
| 429 | +148 | 円 | vola_gate/fam_tables.md:100 | +148 | 円 | 一致 |
| 429 | +228 | 円 | vola_gate/fam_tables.md:100 | +228 | 円 | 一致 |
| 429 | −145 | 円 | vola_gate/fam_tables.md:108 | -145 | 円 | 一致 |
| 429 | −105 | 円 | vola_gate/fam_tables.md:100 | -105 | 円 | 一致 |
| 429 | +111 | 円 | vola_gate/fam_tables.md:100 | +111 | 円 | 一致 |
| 429 | +148 | 円 | vola_gate/fam_tables.md:100 | +148 | 円 | 一致 |
| 429 | +435 | 円 | vola_gate/fam_tables.md:100 | +435 | 円 | 一致 |
| 431 | −87 | 円 | vola_gate/fam_tables.md:18 | -87 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | −166 | 円 | vola_gate/fam_tables.md:18 | -166 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | −11 | 円 | vola_gate/fam_tables.md:18 | -11 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | −21 | 円 | vola_gate/fam_tables.md:98 | -21 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | −40 | 円 | vola_gate/fam_tables.md:99 | -40 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | −78 | 円 | vola_gate/fam_tables.md:100 | -78 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | +19 | 円 | vola_gate/fam_tables.md:98 | +19 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | +93 | 円 | vola_gate/fam_tables.md:99 | +93 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | +186 | 円 | vola_gate/fam_tables.md:100 | +186 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | 39 | 円 | vola_gate/fam_tables.md:98 | +39 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | 97 | 円 | vola_gate/fam_tables.md:100 | +97 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | 58 | 円 | vola_gate/fam_tables.md:100 | +58 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | +54.2 | 円 | vola_gate/fam_tables.md:100 | +54.2 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | +14.8 | 円 | vola_gate/fam_tables.md:46 | +14.8 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | +95.1 | 円 | vola_gate/fam_tables.md:100 | +95.1 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | +1,938 | 円 | vola_gate/fam_tables.md:114 | +1,938 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | +2,468 | 円 | vola_gate/fam_tables.md:115 | +2,468 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | +4.23 | 円 | vola_gate/fam_tables.md:91 | +4.2 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | −86 | 円 | vola_gate/band_migration.out:29 | -86 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | −4.44 | 円 | vola_gate/levels_band.out:6 | -4.4 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | +221 | 円 | vola_gate/band_migration.out:37 | +221 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | −46,431 | 円 | vola_gate/gate_overlap.out:11 | -46,431 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | +34,592 | 円 | vola_gate/gate_overlap.out:11 | +34,592 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
| 431 | +221 | 円 | vola_gate/band_migration.out:37 | +221 | 円 | 一致(散文。値の照合だけ。出所の行は機械が選んだもの) |
