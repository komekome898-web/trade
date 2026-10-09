# 数の突き合わせ 1(base・levels・foot の 3 文書)

作業者(下位モデル)が書いた。読むだけ。文書・台帳・コードは変えていない(書いたのはこのファイルだけ)。

## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 3 文書の行頭が `>` でない行の損益・値動きの数を全部拾い、出所の出力ファイルの値・単位と 1 つずつ突き合わせる | 「**もっと徹底的に調べて影響範囲を確定させてください。**」 |
| 判定を 1 つずつ付けて表にし、このファイルに書く | 「**もっと徹底的に調べて影響範囲を確定させてください。**」 |
| 保存された出力ファイルが無い数(base の `d0_extra.py`・`d2_scenes.py`・`d3_extra.py`・`d8_market.py`・`d9b_extra.py`・levels の `market_side.py levels_*`)は、その台本を読むだけで再実行し、出力を scratchpad に置いて突き合わせる(リポジトリの中には何も書かない。`PYTHONDONTWRITEBYTECODE=1`) | **(該当語なし)**(委任文にも無い。リードが不要とするなら、該当する行の判定「再実行で一致」等を捨てれば残りは成り立つ) |
| UNITS_MAP の単位の主張を、台本の `pnl_jpy` / `pnl_bp` / `* 20` の読み方で確かめる | 「**もっと徹底的に調べて影響範囲を確定させてください。**」(委任文「ここに書いてあることも鵜呑みにせず」) |

見込み時間: 約 80 分(上限 90 分)。内訳: 台本の再実行と単位の確かめ 15 分 / base(数が最も多い。D0〜D10 で約 200 個)30 分 / levels(約 200 個。表が多く機械で比べる)20 分 / foot(約 120 個)15 分 / まとめ 5 分。

## 対象にした数・しなかった数(決まり)

- 対象: 損益(円・円/日・bp・bp/日・1 取引あたり)、値動き(move_bp)、それらの区間・MDE、損益の表の中の単位なしの数。
- 対象外: 本数・取引数・日数・割合(利確で閉じる割合・とんとん・ブレイクの割合・ポイント差は割合の差なので対象外)・日付・時刻・値段(44,900 などの約定の値段)・1 段目の円の大きさ(建玉の大きさで損益ではない)・幅 ÷ ボラ(比)・頂点までの分 ÷ 保有の分(比)。base D0 の成行の遅れの表(本数だけ)は表ごと対象外。
- 丸め: 出所の値を文書の桁に丸めて同じなら一致。円 = bp × 20 は、出所の bp(表示の桁)× 20 を文書の桁に丸めて比べた。
- 出所の欄の書き方: パスは `docs/RESEARCH/matilda_main/` からの相対(`backtest_runs_shared/...` はリポジトリ直下から)。`scratchpad/<名前>.out` は、保存された出力ファイルが無いので台本を再実行して作業者の scratchpad(`/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/`)に置いた出力(リポジトリには入れていない。会話が終わると消えうる)。
- 判定の付け方: 文書の数と出所の数を、作業者の台本(scratchpad の `lib.py`・`base_all.py`・`lev_all.py`・`foot_all.py`)で 1 つずつ比べた(文書の行と出所の行から数を取り出し、出所 × 1 または × 20 を文書の桁に四捨五入して等しいかを見る)。表の各行が 1 回の比べ。目で見て「一致」にした行は無い。ただし、四捨五入の比べでなく判定の欄に理由を書いた「一致」が 5 行ある: base 264 行「約 +4,213,000」(出所から計算した +4,212,793 の概数)・base 294 行「−30〜−32」(出所 −30.50・−32.38 の範囲)・levels 205 行「−242〜−554」(出所 8 値の最大と最小を台本で取った)・levels 438 行と 442 行の「0」(基準 − 基準)。

## まとめ(判定ごとの個数)

| 文書 | 拾った数 | 一致 | 単位の誤り | 値の誤り | 出所が無い・見つからない | 確かめられない |
|---|---|---|---|---|---|---|
| base | 392 | 391 | 0 | 0 | 0 | 1 |
| levels | 691 | 691 | 0 | 0 | 0 | 0 |
| foot | 343 | 343 | 0 | 0 | 0 | 0 |
| 計 | 1,426 | 1,425 | 0 | 0 | 0 | 1 |

- 「一致」1,425 個のうち、保存された出力ファイルが無く台本の再実行で突き合わせたもの: base 141 個(`d3_extra.py` 97・`d2_scenes.py` 27・`d9b_extra.py` 7・`d0_extra.py` 6・`d8_market.py` 4。表の出所の欄が `scratchpad/` のもの)、levels 21 個(D2 の基準の列 18・D8 の `market_side.py` 3)、foot 18 個(D2 の基準の列)。計 180 個。再実行を認めないなら、これらは「出所が無い(保存された出力が無い)」になる。
- 3 文書とも、円と書いた数は出所が円(pnl_jpy・fills の量 × 値段・pnl_bp × 20 で円にした出力)か、出所の bp × 20 で合った。bp と書いた数は出所が bp で合った。move_bp と書いた数は出所 `diag_paths.md` の値動きの bp で合った。「bp の値を円と書いた」「円の値の出所に bp のファイルを指した(× 20 をしていない)」形は、この 3 文書では見つからなかった。

## 一致以外のもの(行番号つき)

| 文書 | 行 | 数 | 判定 | 理由 |
|---|---|---|---|---|
| base | 104 | +1,159 円 | 確かめられない | 「監査 1 回目の指摘 7 で +1,159 から直した」の、直す前の値。今の `d8_market.py` の再実行の出力は 2017〜2023 年 計 +858 円(文書の今の値と一致)で、+1,159 は出力に出ない |

## 一致だが、知らせておくこと(判定は変えていない)

1. **同じ量を 2 つの出所から書いて、文書の中で最後の桁が合わない**(どちらも自分の出所とは一致):
   - base 238 行「3 分超 … −2,803,520 円」(`base/diag_tables.md:56` の −140176 bp × 20)と base 435 行「3 分超の 75,745 本が −2,803,529 円」(`d9b_extra.py` の再実行、pnl_jpy の和)。差 9 円は bp の表示の丸め。
   - base 235〜237 行の 3 つの帯の和 +655,100 + 1,651,420 + 628,400 = +2,934,920 円と、base 435 行「3 分以内 … +2,934,918 円」(pnl_jpy)。差 2 円、同じ理由。
   - foot 184 行・365 行「利確 +73.6・ブレイク −562.8 円」(`foot_5/diag_tables.md:65・66` の bp × 20)と、`foot/compare.md:36` の全期間「利確 1 本 +73.7・ブレイク 1 本 −562.7 円」(pnl_jpy)。同じ理由。
   - base 220 行「全体の和 +131,389 円」は、文書が指す読み口 `base/diag_tables.md:44` の表示 +6569 bp × 20 = 131,380 とは 9 円違う。丸める前の和(`summary.json` の sum_bp 6569.4732 × 20 = 131,389.46、sum_jpy 131389.464)とは一致。
2. **出所の指し方**: levels 209 行の「+2,373,234 円」「−2,160,842 円」は、文書が「下の表」と指す表(`same_bar_daily_4fam.out`、円/日)には無く、`same_bar_all.out:20`(levels_1 の 前半の和、円)にある。値は一致。単位は円で合っている(円/日の表を指したが、円/日の数を円と書いたのではない)。
3. **単位の書き方の小さな揺れ**: foot 362 行「+283 円」は出所 `foot/scenes.out:11` では 1 日あたり(円/日)、foot 363 行「+8.0 円」は出所では 1 取引あたり(円/取引)。同じ文に「1 日あたり」「1 取引あたり」と書いてあるので一致にした。
4. **levels の文書は円と bp を表ごとに使い分けている**: D1 の年ごと(124〜132 行)・D6(292〜295 行)・D7(318〜328 行)・取引の突き合わせ(330 行)は bp(見出しに「bp/日」「1 取引あたり bp」「bp」と書いてある)、ほかの表は円。bp と書いた数は出所の bp と合っており、この文書の中で bp を円と書いた所は無い。UNITS_MAP §3 の 2 つ目「段数の族の文書 levels.md は D1 の年ごと・D6・D7・突き合わせを bp のまま載せている」は、この文書のこの書き方のことなら事実(単位の誤りではなく、円と bp が同じ文書に混ざっていること)。134 行「+42.83 bp/日」・332 行「+36.20」も bp で、出所と一致(332 行の +36.20 は単位を書いていないが、直前の「levels_1 − base が 2016 年」は D7 の bp/日 の表の値)。
5. **D7 の共通の日の問題**(UNITS_MAP §3 の 1 つ目): foot の D7 の表(292〜301 行・403 行)は読み口の値のまま(共通の日だけ)で、出所と一致。文書 288 行が `d7_fullperiod.out` の取り直しの値(+28.0 [−63.8, +134.1]・−208 [−363, −64]・+263 [+150, +376])を並べており、これも出所と一致。
6. 期間の境: foot の D1・D7 は境 2019-12-10、D2・D3 は 2019-12-09(文書 69 行に書いてある)。突き合わせは文書が指す出所どうしで行った。

## UNITS_MAP の単位の主張を台本で確かめた結果

`grep -nE "pnl_jpy|pnl_bp|\* ?20\b" <台本>`(下の「打ったコマンド」)で読んだ列:

| 出力 | 台本 | 台本が読む列 | 出力の単位 | UNITS_MAP と |
|---|---|---|---|---|
| `half_diff.out` | `half_diff.py:17` | 読み口 `diag_tables.daily_series`(pnl_bp)× 20 | 円/日 | 合う |
| `same_bar_daily*.out` | `same_bar_daily.py:11・23` | pnl_bp × 20 | 円/日 | 合う |
| `foot/foot_boundary.out` | `foot/foot_boundary.py:10` | × 20 | 円/日 | 合う |
| `same_bar_all.out` | `same_bar_all.py:16` | pnl_jpy | 円 | 合う(「ほか」に入る) |
| `d7_fullperiod.out` | `d7_fullperiod.py:14・16` | pnl_jpy | 円/日 | 合う |
| `levels/compare.md`・`foot/compare.md` | `compare_family.py:28・32・36` | pnl_jpy | 円 | 合う |
| `levels/scenes.out`・`foot/scenes.out` | `scenes.py:30` | pnl_jpy | 円/日 | 合う |
| `levels/levels_extra.out` | `levels/levels_extra.py:16・21` | pnl_jpy | 円 | 合う |
| `foot/market_side.out`・levels の D8 | `market_side.py:19・20` | fills の量 × (値段の差) | 円 | 単位は合う。pnl_jpy ではなく約定の記録から計算(UNITS_MAP §2 の最後の行の「pnl_jpy を直接読む」とは読み方が違う) |
| base の `d2_scenes`・`d3_extra`・`d9b_extra`・`d0_extra` | 各台本 | pnl_jpy | 円 | UNITS_MAP に行が無い(保存された出力も無い) |
| base の `d8_market` | `base/d8_market.py:19・20` | fills の量 × 値段 | 円 | UNITS_MAP に行が無い |
| `<本>/diag_tables.md` | `diag_tables.py` | pnl_bp | bp | 合う(出力の 3 行目に「損益は bp」と書いてある) |
| `<本>/diag_paths.md` | `diag_paths.py` | D4 の「損益の和」は pnl_bp、ほかは値動きの bp | 単位名なし / bp | 合う(D4 の和 × 20 が文書の円と合った: base 288〜291 行・levels 241〜244 行・foot 210〜213 行) |

## 打ったコマンド(主なもの)

- 読んだ: `UNITS_MAP.md`、3 文書の全行(Read と `grep -vn '^>'`)、`base/diag_tables.md`・`base/diag_paths.md`・`levels_{1,3,7}/diag_tables.md`・`levels_{1,3,7}/diag_paths.md`・`foot_5/diag_tables.md`・`foot_5/diag_paths.md`・`levels/compare.md`・`levels/scenes.out`・`levels/levels_extra.out`・`foot/compare.md`・`foot/scenes.out`・`foot/market_side.out`・`foot/foot_boundary.out`・`half_diff.out`・`same_bar_daily_4fam.out`・`count/same_bar_daily.out`・`same_bar_all.out`・`d7_fullperiod.out`・`backtest_runs_shared/matilda_main_trades/{base,levels_1,levels_3,levels_7,foot_5}/summary.json`。
- 台本の再実行(出力は scratchpad、リポジトリには書かない。`cd /home/user/trade; export PYTHONDONTWRITEBYTECODE=1`):
  - `PYTHONPATH=src python3 docs/RESEARCH/matilda_main/base/{d0_extra,d3_extra,d8_market,d9b_extra,market_delay}.py > $S/<名前>.out`(全部 rc=0。`market_delay` は本数だけの表なので突き合わせに使っていない)
  - `PYTHONPATH=src:scripts/w4_measure python3 docs/RESEARCH/matilda_main/base/d2_scenes.py > $S/d2_scenes.out`(rc=0)
  - `PYTHONPATH=src python3 docs/RESEARCH/matilda_main/market_side.py levels_1 levels_3 levels_7 > $S/market_side_levels.out`(rc=0。出力: levels_1 1119 本 −955 円・levels_3 976 本 −876 円・levels_7 843 本 −235 円)
- 単位の確かめ: `grep -nE "pnl_jpy|pnl_bp|\* ?20\b|/ ?20\b|200000|200_000" half_diff.py both_halves.py same_bar_daily.py same_bar_all.py d7_fullperiod.py compare_family.py scenes.py market_side.py levels/levels_extra.py fam_tables.py foot/foot_boundary.py base/d2_scenes.py base/d3_extra.py base/d8_market.py base/d9b_extra.py`(`docs/RESEARCH/matilda_main/` で)。
- 突き合わせ: `python3 $S/base_all.py` → `392 Counter({'一致': 391, '確かめられない': 1})`、`python3 $S/lev_all.py` → `691 Counter({'一致': 691})`、`python3 $S/foot_all.py` → `343 Counter({'一致': 343})`(アドバイザーの検めで拾い漏れの foot 122・311・330 行の 4 個を足した後)。途中で作業者の台本の列の取り違え(出所の行の何番目の数か)で「値の誤り」が出た所は、出所の行を表示して取り違えを直してから数え直した(直す前の誤判定は数に入れていない)。

## 読むのをやめた・確かめきれなかった範囲

- 行頭が `>` の行(スキルの本文の写し)は対象外(委任文の決まり)。
- 対象外にした数(上の決まり): 本数・日数・割合とポイント差・日付・時刻・値段・1 段目の円の大きさ(base 67 行)・幅 ÷ ボラ(base 461〜477 行)・頂点までの分 ÷ 保有の分・base D0 の成行の遅れの表(71〜81 行、本数だけ)・foot 121 行の「279,837 日」「992 日」。base 266 行「6〜8%」・base 156 行「1 割」・base 264 行「−37%」「−19%」も割合として対象外。
- 「確かめられない」の 1 個(base 104 行 +1,159)は上の表のとおり。
- 再実行した台本の出力が、文書を書いた時点の出力と同じかは確かめられない(保存された出力が無い)。今の取引の行(`backtest_runs_shared/matilda_main_trades/<本>/trades.csv.gz`、手元だけの派生物)から出した値が文書と全部一致した、までが言えること。
- 上限 90 分の中で終えた(残りの範囲は無い)。

## 文書: `docs/ANALYSIS/2026-10-09_matilda_main_base.md`

拾った数 392 個。判定ごと: 一致 391・確かめられない 1

数を拾った行: 31・57・61・68・104・135・136・137・138・139・140・141・142・143・144・150・151・152・154・189・190・191・192・193・194・195・196・197・220・221・227・228・229・235・236・237・238・244・245・246・247・248・249・250・251・252・258・259・260・261・262・264・266・288・289・290・291・294・300・301・302・327・328・329・330・333・335・356・357・358・359・361・432・434・435・437・456・478・487・488

| 文書の行 | 書かれた数 | 書かれた単位 | 出所 ファイル:行 | 出所の値 | 出所の単位 | 判定 |
|---|---|---|---|---|---|---|
| 31 | +131,389 | 円 | backtest_runs_shared/matilda_main_trades/base/summary.json(all.sum_jpy・check.pnl_jpy) | 131389.464 | 円 | 一致 |
| 57 | 131389.464 | 円 | backtest_runs_shared/matilda_main_trades/base/summary.json(check.pnl_jpy) | 131389.464 | 円 | 一致 |
| 61 | −78,738 | 円 | scratchpad/d0_extra.out:11(d0_extra.py の再実行。保存された出力ファイル無し) | -78738 | 円(pnl_jpy) | 一致 |
| 68 | +2,539,704 | 円 | scratchpad/d0_extra.out:13(再実行) | 2539704 | 円(pnl_jpy) | 一致 |
| 68 | +2,334,032 | 円 | scratchpad/d0_extra.out:14(再実行) | 2334032 | 円(pnl_jpy) | 一致 |
| 68 | +1,773,191 | 円 | scratchpad/d0_extra.out:15(再実行) | 1773191 | 円(pnl_jpy) | 一致 |
| 68 | +1,185,705 | 円 | scratchpad/d0_extra.out:16(再実行) | 1185705 | 円(pnl_jpy) | 一致 |
| 68 | −7,701,243 | 円 | scratchpad/d0_extra.out:17(再実行) | -7701243 | 円(pnl_jpy) | 一致 |
| 104 | −156 | 円 | scratchpad/d8_market.out:11(d8_market.py の再実行。保存された出力ファイル無し) | -156 | 円(fills の量 × 値段) | 一致 |
| 104 | −1,042 | 円 | scratchpad/d8_market.out:2(再実行) | -1042 | 円 | 一致 |
| 104 | +27 | 円 | scratchpad/d8_market.out:3(再実行) | 27 | 円 | 一致 |
| 104 | +858 | 円 | scratchpad/d8_market.out:4〜10 の和(再実行) | 858 | 円 | 一致 |
| 104 | +1,159 | 円(直す前の値と書かれている) | — | 出力に無い(今の出力は 2017〜2023 年 +858) | — | 確かめられない(直す前の値として書かれた数。今の台本の出力には出ない) |
| 104 | +131,389 | 円 | backtest_runs_shared/matilda_main_trades/base/summary.json | 131389.464 | 円 | 一致 |
| 135 | +2.24 | bp/日 | base/diag_tables.md:20 | +2.24 | bp/日 | 一致 |
| 135 | −2.06 | bp/日 | base/diag_tables.md:20 | −2.06 | bp/日 | 一致 |
| 135 | +6.21 | bp/日 | base/diag_tables.md:20 | +6.21 | bp/日 | 一致 |
| 135 | +45 | 円/日 | base/diag_tables.md:20 | +2.24(×20 = 45) | bp/日 | 一致 |
| 135 | −41 | 円/日 | base/diag_tables.md:20 | −2.06(×20 = −41) | bp/日 | 一致 |
| 135 | +124 | 円/日 | base/diag_tables.md:20 | +6.21(×20 = 124) | bp/日 | 一致 |
| 135 | +6.14 | bp(MDE) | base/diag_tables.md:20 | +6.14 | bp(MDE) | 一致 |
| 136 | −13.14 | bp/日 | base/diag_tables.md:21 | −13.14 | bp/日 | 一致 |
| 136 | −79.49 | bp/日 | base/diag_tables.md:21 | −79.49 | bp/日 | 一致 |
| 136 | +58.82 | bp/日 | base/diag_tables.md:21 | +58.82 | bp/日 | 一致 |
| 136 | −263 | 円/日 | base/diag_tables.md:21 | −13.14(×20 = −263) | bp/日 | 一致 |
| 136 | −1590 | 円/日 | base/diag_tables.md:21 | −79.49(×20 = −1590) | bp/日 | 一致 |
| 136 | +1176 | 円/日 | base/diag_tables.md:21 | +58.82(×20 = 1176) | bp/日 | 一致 |
| 136 | +100.11 | bp(MDE) | base/diag_tables.md:21 | +100.11 | bp(MDE) | 一致 |
| 137 | +6.63 | bp/日 | base/diag_tables.md:22 | +6.63 | bp/日 | 一致 |
| 137 | −8.10 | bp/日 | base/diag_tables.md:22 | −8.10 | bp/日 | 一致 |
| 137 | +21.66 | bp/日 | base/diag_tables.md:22 | +21.66 | bp/日 | 一致 |
| 137 | +133 | 円/日 | base/diag_tables.md:22 | +6.63(×20 = 133) | bp/日 | 一致 |
| 137 | −162 | 円/日 | base/diag_tables.md:22 | −8.10(×20 = −162) | bp/日 | 一致 |
| 137 | +433 | 円/日 | base/diag_tables.md:22 | +21.66(×20 = 433) | bp/日 | 一致 |
| 137 | +21.88 | bp(MDE) | base/diag_tables.md:22 | +21.88 | bp(MDE) | 一致 |
| 138 | +28.19 | bp/日 | base/diag_tables.md:23 | +28.19 | bp/日 | 一致 |
| 138 | +10.73 | bp/日 | base/diag_tables.md:23 | +10.73 | bp/日 | 一致 |
| 138 | +45.25 | bp/日 | base/diag_tables.md:23 | +45.25 | bp/日 | 一致 |
| 138 | +564 | 円/日 | base/diag_tables.md:23 | +28.19(×20 = 564) | bp/日 | 一致 |
| 138 | +215 | 円/日 | base/diag_tables.md:23 | +10.73(×20 = 215) | bp/日 | 一致 |
| 138 | +905 | 円/日 | base/diag_tables.md:23 | +45.25(×20 = 905) | bp/日 | 一致 |
| 138 | +25.11 | bp(MDE) | base/diag_tables.md:23 | +25.11 | bp(MDE) | 一致 |
| 139 | +27.15 | bp/日 | base/diag_tables.md:24 | +27.15 | bp/日 | 一致 |
| 139 | +16.33 | bp/日 | base/diag_tables.md:24 | +16.33 | bp/日 | 一致 |
| 139 | +37.39 | bp/日 | base/diag_tables.md:24 | +37.39 | bp/日 | 一致 |
| 139 | +543 | 円/日 | base/diag_tables.md:24 | +27.15(×20 = 543) | bp/日 | 一致 |
| 139 | +327 | 円/日 | base/diag_tables.md:24 | +16.33(×20 = 327) | bp/日 | 一致 |
| 139 | +748 | 円/日 | base/diag_tables.md:24 | +37.39(×20 = 748) | bp/日 | 一致 |
| 139 | +15.16 | bp(MDE) | base/diag_tables.md:24 | +15.16 | bp(MDE) | 一致 |
| 140 | +12.21 | bp/日 | base/diag_tables.md:25 | +12.21 | bp/日 | 一致 |
| 140 | +4.39 | bp/日 | base/diag_tables.md:25 | +4.39 | bp/日 | 一致 |
| 140 | +19.71 | bp/日 | base/diag_tables.md:25 | +19.71 | bp/日 | 一致 |
| 140 | +244 | 円/日 | base/diag_tables.md:25 | +12.21(×20 = 244) | bp/日 | 一致 |
| 140 | +88 | 円/日 | base/diag_tables.md:25 | +4.39(×20 = 88) | bp/日 | 一致 |
| 140 | +394 | 円/日 | base/diag_tables.md:25 | +19.71(×20 = 394) | bp/日 | 一致 |
| 140 | +11.30 | bp(MDE) | base/diag_tables.md:25 | +11.30 | bp(MDE) | 一致 |
| 141 | +0.30 | bp/日 | base/diag_tables.md:26 | +0.30 | bp/日 | 一致 |
| 141 | −7.90 | bp/日 | base/diag_tables.md:26 | −7.90 | bp/日 | 一致 |
| 141 | +8.16 | bp/日 | base/diag_tables.md:26 | +8.16 | bp/日 | 一致 |
| 141 | +6 | 円/日 | base/diag_tables.md:26 | +0.30(×20 = 6) | bp/日 | 一致 |
| 141 | −158 | 円/日 | base/diag_tables.md:26 | −7.90(×20 = −158) | bp/日 | 一致 |
| 141 | +163 | 円/日 | base/diag_tables.md:26 | +8.16(×20 = 163) | bp/日 | 一致 |
| 141 | +11.50 | bp(MDE) | base/diag_tables.md:26 | +11.50 | bp(MDE) | 一致 |
| 142 | −19.21 | bp/日 | base/diag_tables.md:27 | −19.21 | bp/日 | 一致 |
| 142 | −32.15 | bp/日 | base/diag_tables.md:27 | −32.15 | bp/日 | 一致 |
| 142 | −8.03 | bp/日 | base/diag_tables.md:27 | −8.03 | bp/日 | 一致 |
| 142 | −384 | 円/日 | base/diag_tables.md:27 | −19.21(×20 = −384) | bp/日 | 一致 |
| 142 | −643 | 円/日 | base/diag_tables.md:27 | −32.15(×20 = −643) | bp/日 | 一致 |
| 142 | −161 | 円/日 | base/diag_tables.md:27 | −8.03(×20 = −161) | bp/日 | 一致 |
| 142 | +17.64 | bp(MDE) | base/diag_tables.md:27 | +17.64 | bp(MDE) | 一致 |
| 143 | −13.15 | bp/日 | base/diag_tables.md:28 | −13.15 | bp/日 | 一致 |
| 143 | −20.44 | bp/日 | base/diag_tables.md:28 | −20.44 | bp/日 | 一致 |
| 143 | −6.51 | bp/日 | base/diag_tables.md:28 | −6.51 | bp/日 | 一致 |
| 143 | −263 | 円/日 | base/diag_tables.md:28 | −13.15(×20 = −263) | bp/日 | 一致 |
| 143 | −409 | 円/日 | base/diag_tables.md:28 | −20.44(×20 = −409) | bp/日 | 一致 |
| 143 | −130 | 円/日 | base/diag_tables.md:28 | −6.51(×20 = −130) | bp/日 | 一致 |
| 143 | +10.16 | bp(MDE) | base/diag_tables.md:28 | +10.16 | bp(MDE) | 一致 |
| 144 | −23.94 | bp/日 | base/diag_tables.md:29 | −23.94 | bp/日 | 一致 |
| 144 | −31.95 | bp/日 | base/diag_tables.md:29 | −31.95 | bp/日 | 一致 |
| 144 | −15.74 | bp/日 | base/diag_tables.md:29 | −15.74 | bp/日 | 一致 |
| 144 | −479 | 円/日 | base/diag_tables.md:29 | −23.94(×20 = −479) | bp/日 | 一致 |
| 144 | −639 | 円/日 | base/diag_tables.md:29 | −31.95(×20 = −639) | bp/日 | 一致 |
| 144 | −315 | 円/日 | base/diag_tables.md:29 | −15.74(×20 = −315) | bp/日 | 一致 |
| 144 | +11.60 | bp(MDE) | base/diag_tables.md:29 | +11.60 | bp(MDE) | 一致 |
| 150 | +18.11 | bp/日 | base/diag_tables.md:35 | +18.11 | bp/日 | 一致 |
| 150 | +11.55 | bp/日 | base/diag_tables.md:35 | +11.55 | bp/日 | 一致 |
| 150 | +24.86 | bp/日 | base/diag_tables.md:35 | +24.86 | bp/日 | 一致 |
| 150 | +362 | 円/日 | base/diag_tables.md:35 | +18.11(×20 = 362) | bp/日 | 一致 |
| 150 | +231 | 円/日 | base/diag_tables.md:35 | +11.55(×20 = 231) | bp/日 | 一致 |
| 150 | +497 | 円/日 | base/diag_tables.md:35 | +24.86(×20 = 497) | bp/日 | 一致 |
| 150 | +9.76 | bp(MDE) | base/diag_tables.md:35 | +9.76 | bp(MDE) | 一致 |
| 151 | −13.63 | bp/日 | base/diag_tables.md:36 | −13.63 | bp/日 | 一致 |
| 151 | −18.00 | bp/日 | base/diag_tables.md:36 | −18.00 | bp/日 | 一致 |
| 151 | −9.19 | bp/日 | base/diag_tables.md:36 | −9.19 | bp/日 | 一致 |
| 151 | −273 | 円/日 | base/diag_tables.md:36 | −13.63(×20 = −273) | bp/日 | 一致 |
| 151 | −360 | 円/日 | base/diag_tables.md:36 | −18.00(×20 = −360) | bp/日 | 一致 |
| 151 | −184 | 円/日 | base/diag_tables.md:36 | −9.19(×20 = −184) | bp/日 | 一致 |
| 151 | +6.26 | bp(MDE) | base/diag_tables.md:36 | +6.26 | bp(MDE) | 一致 |
| 152 | −31.75 | bp/日 | base/diag_tables.md:37 | −31.75 | bp/日 | 一致 |
| 152 | −40.27 | bp/日 | base/diag_tables.md:37 | −40.27 | bp/日 | 一致 |
| 152 | −23.82 | bp/日 | base/diag_tables.md:37 | −23.82 | bp/日 | 一致 |
| 152 | −635 | 円/日 | base/diag_tables.md:37 | −31.75(×20 = −635) | bp/日 | 一致 |
| 152 | −805 | 円/日 | base/diag_tables.md:37 | −40.27(×20 = −805) | bp/日 | 一致 |
| 152 | −476 | 円/日 | base/diag_tables.md:37 | −23.82(×20 = −476) | bp/日 | 一致 |
| 154 | +45 | 円/日 | base/diag_tables.md:20 | +2.24(×20 = 45) | bp/日 | 一致 |
| 189 | −39 | 円/日 | scratchpad/d2_scenes.out:2(d2_scenes.py の再実行。保存された出力ファイル無し) | -39 | 円/日(pnl_jpy) | 一致 |
| 189 | −113 | 円/日 | scratchpad/d2_scenes.out:2(d2_scenes.py の再実行。保存された出力ファイル無し) | -113 | 円/日(pnl_jpy) | 一致 |
| 189 | +38 | 円/日 | scratchpad/d2_scenes.out:2(d2_scenes.py の再実行。保存された出力ファイル無し) | +38 | 円/日(pnl_jpy) | 一致 |
| 190 | +264 | 円/日 | scratchpad/d2_scenes.out:3(d2_scenes.py の再実行。保存された出力ファイル無し) | +264 | 円/日(pnl_jpy) | 一致 |
| 190 | +154 | 円/日 | scratchpad/d2_scenes.out:3(d2_scenes.py の再実行。保存された出力ファイル無し) | +154 | 円/日(pnl_jpy) | 一致 |
| 190 | +357 | 円/日 | scratchpad/d2_scenes.out:3(d2_scenes.py の再実行。保存された出力ファイル無し) | +357 | 円/日(pnl_jpy) | 一致 |
| 191 | −216 | 円/日 | scratchpad/d2_scenes.out:4(d2_scenes.py の再実行。保存された出力ファイル無し) | -216 | 円/日(pnl_jpy) | 一致 |
| 191 | −307 | 円/日 | scratchpad/d2_scenes.out:4(d2_scenes.py の再実行。保存された出力ファイル無し) | -307 | 円/日(pnl_jpy) | 一致 |
| 191 | −126 | 円/日 | scratchpad/d2_scenes.out:4(d2_scenes.py の再実行。保存された出力ファイル無し) | -126 | 円/日(pnl_jpy) | 一致 |
| 192 | +6 | 円/日 | scratchpad/d2_scenes.out:5(d2_scenes.py の再実行。保存された出力ファイル無し) | +6 | 円/日(pnl_jpy) | 一致 |
| 192 | −135 | 円/日 | scratchpad/d2_scenes.out:5(d2_scenes.py の再実行。保存された出力ファイル無し) | -135 | 円/日(pnl_jpy) | 一致 |
| 192 | +143 | 円/日 | scratchpad/d2_scenes.out:5(d2_scenes.py の再実行。保存された出力ファイル無し) | +143 | 円/日(pnl_jpy) | 一致 |
| 193 | +411 | 円/日 | scratchpad/d2_scenes.out:6(d2_scenes.py の再実行。保存された出力ファイル無し) | +411 | 円/日(pnl_jpy) | 一致 |
| 193 | +226 | 円/日 | scratchpad/d2_scenes.out:6(d2_scenes.py の再実行。保存された出力ファイル無し) | +226 | 円/日(pnl_jpy) | 一致 |
| 193 | +634 | 円/日 | scratchpad/d2_scenes.out:6(d2_scenes.py の再実行。保存された出力ファイル無し) | +634 | 円/日(pnl_jpy) | 一致 |
| 194 | −282 | 円/日 | scratchpad/d2_scenes.out:7(d2_scenes.py の再実行。保存された出力ファイル無し) | -282 | 円/日(pnl_jpy) | 一致 |
| 194 | −462 | 円/日 | scratchpad/d2_scenes.out:7(d2_scenes.py の再実行。保存された出力ファイル無し) | -462 | 円/日(pnl_jpy) | 一致 |
| 194 | −111 | 円/日 | scratchpad/d2_scenes.out:7(d2_scenes.py の再実行。保存された出力ファイル無し) | -111 | 円/日(pnl_jpy) | 一致 |
| 195 | +141 | 円/日 | scratchpad/d2_scenes.out:8(d2_scenes.py の再実行。保存された出力ファイル無し) | +141 | 円/日(pnl_jpy) | 一致 |
| 195 | −82 | 円/日 | scratchpad/d2_scenes.out:8(d2_scenes.py の再実行。保存された出力ファイル無し) | -82 | 円/日(pnl_jpy) | 一致 |
| 195 | +345 | 円/日 | scratchpad/d2_scenes.out:8(d2_scenes.py の再実行。保存された出力ファイル無し) | +345 | 円/日(pnl_jpy) | 一致 |
| 196 | +656 | 円/日 | scratchpad/d2_scenes.out:9(d2_scenes.py の再実行。保存された出力ファイル無し) | +656 | 円/日(pnl_jpy) | 一致 |
| 196 | +336 | 円/日 | scratchpad/d2_scenes.out:9(d2_scenes.py の再実行。保存された出力ファイル無し) | +336 | 円/日(pnl_jpy) | 一致 |
| 196 | +1007 | 円/日 | scratchpad/d2_scenes.out:9(d2_scenes.py の再実行。保存された出力ファイル無し) | +1007 | 円/日(pnl_jpy) | 一致 |
| 197 | −343 | 円/日 | scratchpad/d2_scenes.out:10(d2_scenes.py の再実行。保存された出力ファイル無し) | -343 | 円/日(pnl_jpy) | 一致 |
| 197 | −529 | 円/日 | scratchpad/d2_scenes.out:10(d2_scenes.py の再実行。保存された出力ファイル無し) | -529 | 円/日(pnl_jpy) | 一致 |
| 197 | −135 | 円/日 | scratchpad/d2_scenes.out:10(d2_scenes.py の再実行。保存された出力ファイル無し) | -135 | 円/日(pnl_jpy) | 一致 |
| 220 | +653500 | 円 | base/diag_tables.md:44 | +32675(×20 = 653500) | bp | 一致 |
| 220 | −766800 | 円 | base/diag_tables.md:44 | −38340(×20 = −766800) | bp | 一致 |
| 220 | +131,389 | 円 | base/diag_tables.md:44(表示 +6569 bp、×20 = 131,380)と backtest_runs_shared/matilda_main_trades/base/summary.json の all.sum_bp | 6569.4732(×20 = 131389)。表示の +6569 を × 20 すると 131,380 で、丸める前の和で合う | bp | 一致 |
| 221 | −674 | 円 | base/diag_tables.md:46 | −33.70(×20 = −674) | bp | 一致 |
| 221 | −208 | 円 | base/diag_tables.md:46 | −10.40(×20 = −208) | bp | 一致 |
| 221 | +6 | 円 | base/diag_tables.md:46 | +0.30(×20 = 6) | bp | 一致 |
| 221 | +15 | 円 | base/diag_tables.md:46 | +0.77(×20 = 15) | bp | 一致 |
| 221 | +38 | 円 | base/diag_tables.md:46 | +1.88(×20 = 38) | bp | 一致 |
| 221 | +127 | 円 | base/diag_tables.md:46 | +6.37(×20 = 127) | bp | 一致 |
| 221 | +277 | 円 | base/diag_tables.md:46 | +13.86(×20 = 277) | bp | 一致 |
| 227 | +11158240 | 円 | base/diag_tables.md:66 | +557912(×20 = 11158240) | bp | 一致 |
| 227 | +36.4 | 円/取引 | base/diag_tables.md:66 | +1.82(×20 = 36.4) | bp/取引 | 一致 |
| 227 | +34.8 | 円/取引 | base/diag_tables.md:66 | +1.74(×20 = 34.8) | bp/取引 | 一致 |
| 227 | +38.2 | 円/取引 | base/diag_tables.md:66 | +1.91(×20 = 38.2) | bp/取引 | 一致 |
| 228 | −10747900 | 円 | base/diag_tables.md:65 | −537395(×20 = −10747900) | bp | 一致 |
| 228 | −258.8 | 円/取引 | base/diag_tables.md:65 | −12.94(×20 = −258.8) | bp/取引 | 一致 |
| 228 | −271.6 | 円/取引 | base/diag_tables.md:65 | −13.58(×20 = −271.6) | bp/取引 | 一致 |
| 228 | −246.4 | 円/取引 | base/diag_tables.md:65 | −12.32(×20 = −246.4) | bp/取引 | 一致 |
| 229 | −278940 | 円 | base/diag_tables.md:67 | −13947(×20 = −278940) | bp | 一致 |
| 229 | −315.2 | 円/取引 | base/diag_tables.md:67 | −15.76(×20 = −315.2) | bp/取引 | 一致 |
| 229 | −361.4 | 円/取引 | base/diag_tables.md:67 | −18.07(×20 = −361.4) | bp/取引 | 一致 |
| 229 | −278.4 | 円/取引 | base/diag_tables.md:67 | −13.92(×20 = −278.4) | bp/取引 | 一致 |
| 235 | +655100 | 円 | base/diag_tables.md:57 | +32755(×20 = 655100) | bp | 一致 |
| 235 | +7.4 | 円/取引 | base/diag_tables.md:57 | +0.37(×20 = 7.4) | bp/取引 | 一致 |
| 235 | +6.4 | 円/取引 | base/diag_tables.md:57 | +0.32(×20 = 6.4) | bp/取引 | 一致 |
| 235 | +8.2 | 円/取引 | base/diag_tables.md:57 | +0.41(×20 = 8.2) | bp/取引 | 一致 |
| 236 | +1651420 | 円 | base/diag_tables.md:54 | +82571(×20 = 1651420) | bp | 一致 |
| 236 | +14.0 | 円/取引 | base/diag_tables.md:54 | +0.70(×20 = 14.0) | bp/取引 | 一致 |
| 236 | +13.0 | 円/取引 | base/diag_tables.md:54 | +0.65(×20 = 13.0) | bp/取引 | 一致 |
| 236 | +14.8 | 円/取引 | base/diag_tables.md:54 | +0.74(×20 = 14.8) | bp/取引 | 一致 |
| 237 | +628400 | 円 | base/diag_tables.md:55 | +31420(×20 = 628400) | bp | 一致 |
| 237 | +9.6 | 円/取引 | base/diag_tables.md:55 | +0.48(×20 = 9.6) | bp/取引 | 一致 |
| 237 | +8.4 | 円/取引 | base/diag_tables.md:55 | +0.42(×20 = 8.4) | bp/取引 | 一致 |
| 237 | +10.8 | 円/取引 | base/diag_tables.md:55 | +0.54(×20 = 10.8) | bp/取引 | 一致 |
| 238 | −2803520 | 円 | base/diag_tables.md:56 | −140176(×20 = −2803520) | bp | 一致 |
| 238 | −37.0 | 円/取引 | base/diag_tables.md:56 | −1.85(×20 = −37.0) | bp/取引 | 一致 |
| 238 | −40.2 | 円/取引 | base/diag_tables.md:56 | −2.01(×20 = −40.2) | bp/取引 | 一致 |
| 238 | −33.6 | 円/取引 | base/diag_tables.md:56 | −1.68(×20 = −33.6) | bp/取引 | 一致 |
| 244 | +65444 | 円 | scratchpad/d3_extra.out:2(d3_extra.py の再実行。保存された出力ファイル無し) | 65444 | 円(pnl_jpy) | 一致 |
| 244 | +147.7 | 円/本 | scratchpad/d3_extra.out:2(d3_extra.py の再実行。保存された出力ファイル無し) | 147.7 | 円(pnl_jpy) | 一致 |
| 244 | −44986 | 円 | scratchpad/d3_extra.out:2(d3_extra.py の再実行。保存された出力ファイル無し) | -44986 | 円(pnl_jpy) | 一致 |
| 244 | −882.1 | 円/本 | scratchpad/d3_extra.out:2(d3_extra.py の再実行。保存された出力ファイル無し) | -882.1 | 円(pnl_jpy) | 一致 |
| 244 | −28607 | 円 | scratchpad/d3_extra.out:2(d3_extra.py の再実行。保存された出力ファイル無し) | -28607 | 円(pnl_jpy) | 一致 |
| 245 | +897484 | 円 | scratchpad/d3_extra.out:3(d3_extra.py の再実行。保存された出力ファイル無し) | 897484 | 円(pnl_jpy) | 一致 |
| 245 | +27.1 | 円/本 | scratchpad/d3_extra.out:3(d3_extra.py の再実行。保存された出力ファイル無し) | 27.1 | 円(pnl_jpy) | 一致 |
| 245 | −723875 | 円 | scratchpad/d3_extra.out:3(d3_extra.py の再実行。保存された出力ファイル無し) | -723875 | 円(pnl_jpy) | 一致 |
| 245 | −193.8 | 円/本 | scratchpad/d3_extra.out:3(d3_extra.py の再実行。保存された出力ファイル無し) | -193.8 | 円(pnl_jpy) | 一致 |
| 245 | −125058 | 円 | scratchpad/d3_extra.out:3(d3_extra.py の再実行。保存された出力ファイル無し) | -125058 | 円(pnl_jpy) | 一致 |
| 246 | +2270901 | 円 | scratchpad/d3_extra.out:4(d3_extra.py の再実行。保存された出力ファイル無し) | 2270901 | 円(pnl_jpy) | 一致 |
| 246 | +54.7 | 円/本 | scratchpad/d3_extra.out:4(d3_extra.py の再実行。保存された出力ファイル無し) | 54.7 | 円(pnl_jpy) | 一致 |
| 246 | −2053600 | 円 | scratchpad/d3_extra.out:4(d3_extra.py の再実行。保存された出力ファイル無し) | -2053600 | 円(pnl_jpy) | 一致 |
| 246 | −401.9 | 円/本 | scratchpad/d3_extra.out:4(d3_extra.py の再実行。保存された出力ファイル無し) | -401.9 | 円(pnl_jpy) | 一致 |
| 246 | −11532 | 円 | scratchpad/d3_extra.out:4(d3_extra.py の再実行。保存された出力ファイル無し) | -11532 | 円(pnl_jpy) | 一致 |
| 247 | +1820155 | 円 | scratchpad/d3_extra.out:5(d3_extra.py の再実行。保存された出力ファイル無し) | 1820155 | 円(pnl_jpy) | 一致 |
| 247 | +43.5 | 円/本 | scratchpad/d3_extra.out:5(d3_extra.py の再実行。保存された出力ファイル無し) | 43.5 | 円(pnl_jpy) | 一致 |
| 247 | −1617959 | 円 | scratchpad/d3_extra.out:5(d3_extra.py の再実行。保存された出力ファイル無し) | -1617959 | 円(pnl_jpy) | 一致 |
| 247 | −284.9 | 円/本 | scratchpad/d3_extra.out:5(d3_extra.py の再実行。保存された出力ファイル無し) | -284.9 | 円(pnl_jpy) | 一致 |
| 247 | −4007 | 円 | scratchpad/d3_extra.out:5(d3_extra.py の再実行。保存された出力ファイル無し) | -4007 | 円(pnl_jpy) | 一致 |
| 248 | +1303316 | 円 | scratchpad/d3_extra.out:6(d3_extra.py の再実行。保存された出力ファイル無し) | 1303316 | 円(pnl_jpy) | 一致 |
| 248 | +31.7 | 円/本 | scratchpad/d3_extra.out:6(d3_extra.py の再実行。保存された出力ファイル無し) | 31.7 | 円(pnl_jpy) | 一致 |
| 248 | −1205390 | 円 | scratchpad/d3_extra.out:6(d3_extra.py の再実行。保存された出力ファイル無し) | -1205390 | 円(pnl_jpy) | 一致 |
| 248 | −212.9 | 円/本 | scratchpad/d3_extra.out:6(d3_extra.py の再実行。保存された出力ファイル無し) | -212.9 | 円(pnl_jpy) | 一致 |
| 248 | −8757 | 円 | scratchpad/d3_extra.out:6(d3_extra.py の再実行。保存された出力ファイル無し) | -8757 | 円(pnl_jpy) | 一致 |
| 249 | +1315661 | 円 | scratchpad/d3_extra.out:7(d3_extra.py の再実行。保存された出力ファイル無し) | 1315661 | 円(pnl_jpy) | 一致 |
| 249 | +32.7 | 円/本 | scratchpad/d3_extra.out:7(d3_extra.py の再実行。保存された出力ファイル無し) | 32.7 | 円(pnl_jpy) | 一致 |
| 249 | −1303045 | 円 | scratchpad/d3_extra.out:7(d3_extra.py の再実行。保存された出力ファイル無し) | -1303045 | 円(pnl_jpy) | 一致 |
| 249 | −231.7 | 円/本 | scratchpad/d3_extra.out:7(d3_extra.py の再実行。保存された出力ファイル無し) | -231.7 | 円(pnl_jpy) | 一致 |
| 249 | −10455 | 円 | scratchpad/d3_extra.out:7(d3_extra.py の再実行。保存された出力ファイル無し) | -10455 | 円(pnl_jpy) | 一致 |
| 250 | +1612201 | 円 | scratchpad/d3_extra.out:8(d3_extra.py の再実行。保存された出力ファイル無し) | 1612201 | 円(pnl_jpy) | 一致 |
| 250 | +43.6 | 円/本 | scratchpad/d3_extra.out:8(d3_extra.py の再実行。保存された出力ファイル無し) | 43.6 | 円(pnl_jpy) | 一致 |
| 250 | −1721412 | 円 | scratchpad/d3_extra.out:8(d3_extra.py の再実行。保存された出力ファイル無し) | -1721412 | 円(pnl_jpy) | 一致 |
| 250 | −314.4 | 円/本 | scratchpad/d3_extra.out:8(d3_extra.py の再実行。保存された出力ファイル無し) | -314.4 | 円(pnl_jpy) | 一致 |
| 250 | −31045 | 円 | scratchpad/d3_extra.out:8(d3_extra.py の再実行。保存された出力ファイル無し) | -31045 | 円(pnl_jpy) | 一致 |
| 251 | +1153645 | 円 | scratchpad/d3_extra.out:9(d3_extra.py の再実行。保存された出力ファイル無し) | 1153645 | 円(pnl_jpy) | 一致 |
| 251 | +29.2 | 円/本 | scratchpad/d3_extra.out:9(d3_extra.py の再実行。保存された出力ファイル無し) | 29.2 | 円(pnl_jpy) | 一致 |
| 251 | −1226443 | 円 | scratchpad/d3_extra.out:9(d3_extra.py の再実行。保存された出力ファイル無し) | -1226443 | 円(pnl_jpy) | 一致 |
| 251 | −220.5 | 円/本 | scratchpad/d3_extra.out:9(d3_extra.py の再実行。保存された出力ファイル無し) | -220.5 | 円(pnl_jpy) | 一致 |
| 251 | −23220 | 円 | scratchpad/d3_extra.out:9(d3_extra.py の再実行。保存された出力ファイル無し) | -23220 | 円(pnl_jpy) | 一致 |
| 252 | +719435 | 円 | scratchpad/d3_extra.out:10(d3_extra.py の再実行。保存された出力ファイル無し) | 719435 | 円(pnl_jpy) | 一致 |
| 252 | +22.7 | 円/本 | scratchpad/d3_extra.out:10(d3_extra.py の再実行。保存された出力ファイル無し) | 22.7 | 円(pnl_jpy) | 一致 |
| 252 | −851196 | 円 | scratchpad/d3_extra.out:10(d3_extra.py の再実行。保存された出力ファイル無し) | -851196 | 円(pnl_jpy) | 一致 |
| 252 | −183.9 | 円/本 | scratchpad/d3_extra.out:10(d3_extra.py の再実行。保存された出力ファイル無し) | -183.9 | 円(pnl_jpy) | 一致 |
| 252 | −36265 | 円 | scratchpad/d3_extra.out:10(d3_extra.py の再実行。保存された出力ファイル無し) | -36265 | 円(pnl_jpy) | 一致 |
| 258 | +1494421 | 円 | scratchpad/d3_extra.out:13(再実行) | 1494421 | 円(pnl_jpy) | 一致 |
| 258 | +18.0 | 円/本 | scratchpad/d3_extra.out:13(再実行) | 18.0 | 円(pnl_jpy) | 一致 |
| 258 | −37813 | 円 | scratchpad/d3_extra.out:12(再実行) | -37813 | 円(pnl_jpy) | 一致 |
| 258 | −26.1 | 円/本 | scratchpad/d3_extra.out:12(再実行) | -26.1 | 円(pnl_jpy) | 一致 |
| 258 | +1114486 | 円 | scratchpad/d3_extra.out:28(再実行) | 1114486 | 円(pnl_jpy) | 一致 |
| 258 | +14.3 | 円/本 | scratchpad/d3_extra.out:28(再実行) | 14.3 | 円(pnl_jpy) | 一致 |
| 258 | −34279 | 円 | scratchpad/d3_extra.out:27(再実行) | -34279 | 円(pnl_jpy) | 一致 |
| 258 | −27.2 | 円/本 | scratchpad/d3_extra.out:27(再実行) | -27.2 | 円(pnl_jpy) | 一致 |
| 259 | +1400821 | 円 | scratchpad/d3_extra.out:16(再実行) | 1400821 | 円(pnl_jpy) | 一致 |
| 259 | +45.4 | 円/本 | scratchpad/d3_extra.out:16(再実行) | 45.4 | 円(pnl_jpy) | 一致 |
| 259 | −88584 | 円 | scratchpad/d3_extra.out:15(再実行) | -88584 | 円(pnl_jpy) | 一致 |
| 259 | −51.0 | 円/本 | scratchpad/d3_extra.out:15(再実行) | -51.0 | 円(pnl_jpy) | 一致 |
| 259 | +1104970 | 円 | scratchpad/d3_extra.out:31(再実行) | 1104970 | 円(pnl_jpy) | 一致 |
| 259 | +37.4 | 円/本 | scratchpad/d3_extra.out:31(再実行) | 37.4 | 円(pnl_jpy) | 一致 |
| 259 | −81944 | 円 | scratchpad/d3_extra.out:30(再実行) | -81944 | 円(pnl_jpy) | 一致 |
| 259 | −45.6 | 円/本 | scratchpad/d3_extra.out:30(再実行) | -45.6 | 円(pnl_jpy) | 一致 |
| 260 | +1162719 | 円 | scratchpad/d3_extra.out:19(再実行) | 1162719 | 円(pnl_jpy) | 一致 |
| 260 | +76.3 | 円/本 | scratchpad/d3_extra.out:19(再実行) | 76.3 | 円(pnl_jpy) | 一致 |
| 260 | −179658 | 円 | scratchpad/d3_extra.out:18(再実行) | -179658 | 円(pnl_jpy) | 一致 |
| 260 | −80.6 | 円/本 | scratchpad/d3_extra.out:18(再実行) | -80.6 | 円(pnl_jpy) | 一致 |
| 260 | +956645 | 円 | scratchpad/d3_extra.out:33(再実行) | 956645 | 円(pnl_jpy) | 一致 |
| 260 | +62.6 | 円/本 | scratchpad/d3_extra.out:33(再実行) | 62.6 | 円(pnl_jpy) | 一致 |
| 260 | −164134 | 円 | scratchpad/d3_extra.out:32(再実行) | -164134 | 円(pnl_jpy) | 一致 |
| 260 | −72.2 | 円/本 | scratchpad/d3_extra.out:32(再実行) | -72.2 | 円(pnl_jpy) | 一致 |
| 261 | +975868 | 円 | scratchpad/d3_extra.out:22(再実行) | 975868 | 円(pnl_jpy) | 一致 |
| 261 | +109.6 | 円/本 | scratchpad/d3_extra.out:22(再実行) | 109.6 | 円(pnl_jpy) | 一致 |
| 261 | −325457 | 円 | scratchpad/d3_extra.out:21(再実行) | -325457 | 円(pnl_jpy) | 一致 |
| 261 | −134.7 | 円/本 | scratchpad/d3_extra.out:21(再実行) | -134.7 | 円(pnl_jpy) | 一致 |
| 261 | +798950 | 円 | scratchpad/d3_extra.out:36(再実行) | 798950 | 円(pnl_jpy) | 一致 |
| 261 | +87.7 | 円/本 | scratchpad/d3_extra.out:36(再実行) | 87.7 | 円(pnl_jpy) | 一致 |
| 261 | −260527 | 円 | scratchpad/d3_extra.out:35(再実行) | -260527 | 円(pnl_jpy) | 一致 |
| 261 | −108.6 | 円/本 | scratchpad/d3_extra.out:35(再実行) | -108.6 | 円(pnl_jpy) | 一致 |
| 262 | +1269752 | 円 | scratchpad/d3_extra.out:25(再実行) | 1269752 | 円(pnl_jpy) | 一致 |
| 262 | +73.2 | 円/本 | scratchpad/d3_extra.out:25(再実行) | 73.2 | 円(pnl_jpy) | 一致 |
| 262 | −4961897 | 円 | scratchpad/d3_extra.out:24(再実行) | -4961897 | 円(pnl_jpy) | 一致 |
| 262 | −410.9 | 円/本 | scratchpad/d3_extra.out:24(再実行) | -410.9 | 円(pnl_jpy) | 一致 |
| 262 | +879610 | 円 | scratchpad/d3_extra.out:39(再実行) | 879610 | 円(pnl_jpy) | 一致 |
| 262 | +46.0 | 円/本 | scratchpad/d3_extra.out:39(再実行) | 46.0 | 円(pnl_jpy) | 一致 |
| 262 | −4613613 | 円 | scratchpad/d3_extra.out:38(再実行) | -4613613 | 円(pnl_jpy) | 一致 |
| 262 | −332.1 | 円/本 | scratchpad/d3_extra.out:38(再実行) | -332.1 | 円(pnl_jpy) | 一致 |
| 264 | −4,961,897 | 円 | scratchpad/d3_extra.out:24(再実行) | -4961897 | 円 | 一致 |
| 264 | −4,613,613 | 円 | scratchpad/d3_extra.out:38(再実行) | -4613613 | 円 | 一致 |
| 264 | +5,494,107 | 円 | scratchpad/d3_extra.out:12〜26 の前半の和 − 前半 5 段ブレイク(再実行の出力から計算。成行を含む) | 5494107 | 円 | 一致 |
| 264 | 約 +4,213,000 | 円 | scratchpad/d3_extra.out:27〜40 の後半の和 − 後半 5 段ブレイク(再実行の出力から計算。成行を含む) | +4,212,793 | 円 | 一致(「約」の概数。千の位で丸めて同じ) |
| 264 | +18.0 | 円/本 | scratchpad/d3_extra.out:13(再実行) | 18.0 | 円 | 一致 |
| 264 | +14.3 | 円/本 | scratchpad/d3_extra.out:28(再実行) | 14.3 | 円 | 一致 |
| 264 | +73.2 | 円/本 | scratchpad/d3_extra.out:25(再実行) | 73.2 | 円 | 一致 |
| 264 | +46.0 | 円/本 | scratchpad/d3_extra.out:39(再実行) | 46.0 | 円 | 一致 |
| 264 | −410.9 | 円/本 | scratchpad/d3_extra.out:24(再実行) | -410.9 | 円 | 一致 |
| 264 | −332.1 | 円/本 | scratchpad/d3_extra.out:38(再実行) | -332.1 | 円 | 一致 |
| 266 | +54.7 | 円/本 | scratchpad/d3_extra.out:4(再実行) | 54.7 | 円 | 一致 |
| 266 | +22.7 | 円/本 | scratchpad/d3_extra.out:10(再実行) | 22.7 | 円 | 一致 |
| 288 | +10177340 | 円 | base/diag_paths.md:11 | +508867(×20 = 10177340) | bp(単位名なし。pnl_bp) | 一致 |
| 288 | +6.02 | move_bp | base/diag_paths.md:11 | +6.02 | bp(取引の向きを掛けた値動き) | 一致 |
| 288 | −4.74 | move_bp | base/diag_paths.md:11 | −4.74 | bp(取引の向きを掛けた値動き) | 一致 |
| 289 | −4695040 | 円 | base/diag_paths.md:12 | −234752(×20 = −4695040) | bp(単位名なし。pnl_bp) | 一致 |
| 289 | +2.05 | move_bp | base/diag_paths.md:12 | +2.05 | bp(取引の向きを掛けた値動き) | 一致 |
| 289 | −30.50 | move_bp | base/diag_paths.md:12 | −30.50 | bp(取引の向きを掛けた値動き) | 一致 |
| 290 | −6006000 | 円 | base/diag_paths.md:13 | −300300(×20 = −6006000) | bp(単位名なし。pnl_bp) | 一致 |
| 290 | −2.77 | move_bp | base/diag_paths.md:13 | −2.77 | bp(取引の向きを掛けた値動き) | 一致 |
| 290 | −32.38 | move_bp | base/diag_paths.md:13 | −32.38 | bp(取引の向きを掛けた値動き) | 一致 |
| 291 | 0 | 円 | base/diag_paths.md:14 | +0(×20 = 0) | bp(単位名なし。pnl_bp) | 一致 |
| 291 | −1.52 | move_bp | base/diag_paths.md:14 | −1.52 | bp(取引の向きを掛けた値動き) | 一致 |
| 291 | −11.21 | move_bp | base/diag_paths.md:14 | −11.21 | bp(取引の向きを掛けた値動き) | 一致 |
| 294 | −30〜−32 | move_bp | base/diag_paths.md:12・13 | −30.50・−32.38 | bp(値動き) | 一致(概数の範囲。出所の 2 つの値を整数で囲んだ書き方) |
| 294 | +6 | move_bp | base/diag_paths.md:11 | +6.02 | bp(値動き) | 一致 |
| 300 | −0.34 | move_bp | base/diag_paths.md:22 | −0.34 | bp(値動き) | 一致 |
| 300 | −0.45 | move_bp | base/diag_paths.md:22 | −0.45 | bp(値動き) | 一致 |
| 300 | −0.22 | move_bp | base/diag_paths.md:22 | −0.22 | bp(値動き) | 一致 |
| 301 | −0.66 | move_bp | base/diag_paths.md:23 | −0.66 | bp(値動き) | 一致 |
| 301 | −0.89 | move_bp | base/diag_paths.md:23 | −0.89 | bp(値動き) | 一致 |
| 301 | −0.43 | move_bp | base/diag_paths.md:23 | −0.43 | bp(値動き) | 一致 |
| 302 | −0.42 | move_bp | base/diag_paths.md:24 | −0.42 | bp(値動き) | 一致 |
| 302 | −0.89 | move_bp | base/diag_paths.md:24 | −0.89 | bp(値動き) | 一致 |
| 302 | +0.01 | move_bp | base/diag_paths.md:24 | +0.01 | bp(値動き) | 一致 |
| 327 | −6.67 | move_bp | base/diag_paths.md:32 | -6.67 | bp(値動き) | 一致 |
| 327 | −6.99 | move_bp | base/diag_paths.md:32 | -6.99 | bp(値動き) | 一致 |
| 327 | −6.32 | move_bp | base/diag_paths.md:32 | -6.32 | bp(値動き) | 一致 |
| 327 | +0.02 | move_bp | base/diag_paths.md:32 | +0.02 | bp(値動き) | 一致 |
| 327 | −0.02 | move_bp | base/diag_paths.md:32 | -0.02 | bp(値動き) | 一致 |
| 327 | +0.06 | move_bp | base/diag_paths.md:32 | +0.06 | bp(値動き) | 一致 |
| 327 | −0.25 | move_bp | base/diag_paths.md:41 | -0.25 | bp(値動き) | 一致 |
| 327 | −0.31 | move_bp | base/diag_paths.md:41 | -0.31 | bp(値動き) | 一致 |
| 327 | −0.20 | move_bp | base/diag_paths.md:41 | -0.20 | bp(値動き) | 一致 |
| 327 | +0.03 | move_bp | base/diag_paths.md:41 | +0.03 | bp(値動き) | 一致 |
| 327 | −0.02 | move_bp | base/diag_paths.md:41 | -0.02 | bp(値動き) | 一致 |
| 327 | +0.07 | move_bp | base/diag_paths.md:41 | +0.07 | bp(値動き) | 一致 |
| 328 | −7.13 | move_bp | base/diag_paths.md:33 | -7.13 | bp(値動き) | 一致 |
| 328 | −7.53 | move_bp | base/diag_paths.md:33 | -7.53 | bp(値動き) | 一致 |
| 328 | −6.73 | move_bp | base/diag_paths.md:33 | -6.73 | bp(値動き) | 一致 |
| 328 | +0.03 | move_bp | base/diag_paths.md:33 | +0.03 | bp(値動き) | 一致 |
| 328 | −0.08 | move_bp | base/diag_paths.md:33 | -0.08 | bp(値動き) | 一致 |
| 328 | +0.14 | move_bp | base/diag_paths.md:33 | +0.14 | bp(値動き) | 一致 |
| 328 | −0.51 | move_bp | base/diag_paths.md:42 | -0.51 | bp(値動き) | 一致 |
| 328 | −0.63 | move_bp | base/diag_paths.md:42 | -0.63 | bp(値動き) | 一致 |
| 328 | −0.38 | move_bp | base/diag_paths.md:42 | -0.38 | bp(値動き) | 一致 |
| 328 | −0.01 | move_bp | base/diag_paths.md:42 | -0.01 | bp(値動き) | 一致 |
| 328 | −0.12 | move_bp | base/diag_paths.md:42 | -0.12 | bp(値動き) | 一致 |
| 328 | +0.10 | move_bp | base/diag_paths.md:42 | +0.10 | bp(値動き) | 一致 |
| 329 | −7.36 | move_bp | base/diag_paths.md:34 | -7.36 | bp(値動き) | 一致 |
| 329 | −7.82 | move_bp | base/diag_paths.md:34 | -7.82 | bp(値動き) | 一致 |
| 329 | −6.90 | move_bp | base/diag_paths.md:34 | -6.90 | bp(値動き) | 一致 |
| 329 | +0.14 | move_bp | base/diag_paths.md:34 | +0.14 | bp(値動き) | 一致 |
| 329 | −0.08 | move_bp | base/diag_paths.md:34 | -0.08 | bp(値動き) | 一致 |
| 329 | +0.36 | move_bp | base/diag_paths.md:34 | +0.36 | bp(値動き) | 一致 |
| 329 | −0.74 | move_bp | base/diag_paths.md:43 | -0.74 | bp(値動き) | 一致 |
| 329 | −0.98 | move_bp | base/diag_paths.md:43 | -0.98 | bp(値動き) | 一致 |
| 329 | −0.52 | move_bp | base/diag_paths.md:43 | -0.52 | bp(値動き) | 一致 |
| 329 | +0.11 | move_bp | base/diag_paths.md:43 | +0.11 | bp(値動き) | 一致 |
| 329 | −0.11 | move_bp | base/diag_paths.md:43 | -0.11 | bp(値動き) | 一致 |
| 329 | +0.32 | move_bp | base/diag_paths.md:43 | +0.32 | bp(値動き) | 一致 |
| 330 | −7.18 | move_bp | base/diag_paths.md:35 | -7.18 | bp(値動き) | 一致 |
| 330 | −7.86 | move_bp | base/diag_paths.md:35 | -7.86 | bp(値動き) | 一致 |
| 330 | −6.61 | move_bp | base/diag_paths.md:35 | -6.61 | bp(値動き) | 一致 |
| 330 | +0.54 | move_bp | base/diag_paths.md:35 | +0.54 | bp(値動き) | 一致 |
| 330 | +0.04 | move_bp | base/diag_paths.md:35 | +0.04 | bp(値動き) | 一致 |
| 330 | +1.03 | move_bp | base/diag_paths.md:35 | +1.03 | bp(値動き) | 一致 |
| 330 | −0.58 | move_bp | base/diag_paths.md:44 | -0.58 | bp(値動き) | 一致 |
| 330 | −1.10 | move_bp | base/diag_paths.md:44 | -1.10 | bp(値動き) | 一致 |
| 330 | −0.13 | move_bp | base/diag_paths.md:44 | -0.13 | bp(値動き) | 一致 |
| 330 | +0.53 | move_bp | base/diag_paths.md:44 | +0.53 | bp(値動き) | 一致 |
| 330 | +0.03 | move_bp | base/diag_paths.md:44 | +0.03 | bp(値動き) | 一致 |
| 330 | +1.03 | move_bp | base/diag_paths.md:44 | +1.03 | bp(値動き) | 一致 |
| 333 | −6.4 | move_bp | base/diag_paths.md:32・41 の差(−6.67 − (−0.25)) | -6.42 | bp(値動き) | 一致 |
| 333 | 6.4 | move_bp | base/diag_paths.md:32・41 の差の絶対値 | 6.42 | bp(値動き) | 一致 |
| 335 | +0.54 | move_bp(書いていない。前の文脈で move_bp) | base/diag_paths.md:35 | +0.54 | bp(値動き) | 一致 |
| 335 | +0.04 | move_bp(書いていない。前の文脈で move_bp) | base/diag_paths.md:35 | +0.04 | bp(値動き) | 一致 |
| 335 | +1.03 | move_bp(書いていない。前の文脈で move_bp) | base/diag_paths.md:35 | +1.03 | bp(値動き) | 一致 |
| 356 | +308900 | 円 | base/diag_tables.md:76 | +15445(×20 = 308900) | bp | 一致 |
| 356 | +2.4 | 円/取引 | base/diag_tables.md:76 | +0.12(×20 = 2.4) | bp/取引 | 一致 |
| 356 | +1.4 | 円/取引 | base/diag_tables.md:76 | +0.07(×20 = 1.4) | bp/取引 | 一致 |
| 356 | +3.4 | 円/取引 | base/diag_tables.md:76 | +0.17(×20 = 3.4) | bp/取引 | 一致 |
| 357 | −5840 | 円 | base/diag_tables.md:73 | -292(×20 = -5840) | bp | 一致 |
| 357 | −0.0 | 円/取引 | base/diag_tables.md:73 | -0.00(×20 = -0.0) | bp/取引 | 一致 |
| 357 | −1.6 | 円/取引 | base/diag_tables.md:73 | -0.08(×20 = -1.6) | bp/取引 | 一致 |
| 357 | +1.4 | 円/取引 | base/diag_tables.md:73 | +0.07(×20 = 1.4) | bp/取引 | 一致 |
| 358 | −154560 | 円 | base/diag_tables.md:75 | -7728(×20 = -154560) | bp | 一致 |
| 358 | −2.0 | 円/取引 | base/diag_tables.md:75 | -0.10(×20 = -2.0) | bp/取引 | 一致 |
| 358 | −3.2 | 円/取引 | base/diag_tables.md:75 | -0.16(×20 = -3.2) | bp/取引 | 一致 |
| 358 | −0.8 | 円/取引 | base/diag_tables.md:75 | -0.04(×20 = -0.8) | bp/取引 | 一致 |
| 359 | −16820 | 円 | base/diag_tables.md:74 | -841(×20 = -16820) | bp | 一致 |
| 359 | −0.2 | 円/取引 | base/diag_tables.md:74 | -0.01(×20 = -0.2) | bp/取引 | 一致 |
| 359 | −1.8 | 円/取引 | base/diag_tables.md:74 | -0.09(×20 = -1.8) | bp/取引 | 一致 |
| 359 | +1.2 | 円/取引 | base/diag_tables.md:74 | +0.06(×20 = 1.2) | bp/取引 | 一致 |
| 361 | +2.4 | 円/取引 | base/diag_tables.md:76 | +0.12(×20 = 2.4) | bp/取引 | 一致 |
| 361 | −2.0 | 円/取引 | base/diag_tables.md:75 | -0.10(×20 = -2.0) | bp/取引 | 一致 |
| 361 | +36 | 円/取引 | base/diag_tables.md:66 | +1.82(×20 = 36) | bp/取引 | 一致 |
| 361 | −259 | 円/取引 | base/diag_tables.md:65 | -12.94(×20 = -259) | bp/取引 | 一致 |
| 432 | +0.54 | move_bp(単位を書いていない) | base/diag_paths.md:35 | +0.54 | bp(値動き) | 一致 |
| 434 | −35.1 | 円/本 | scratchpad/d9b_extra.out:2(d9b_extra.py の再実行。保存された出力ファイル無し) | -35.1 | 円(pnl_jpy) | 一致 |
| 434 | −100.0 | 円/本 | scratchpad/d9b_extra.out:6(再実行) | -100.0 | 円 | 一致 |
| 434 | −402,291 | 円 | scratchpad/d9b_extra.out:10(再実行) | -402291 | 円 | 一致 |
| 435 | +2,934,918 | 円 | scratchpad/d9b_extra.out:11(再実行) | 2934918 | 円 | 一致 |
| 435 | −2,803,529 | 円 | scratchpad/d9b_extra.out:11(再実行) | -2803529 | 円 | 一致 |
| 437 | −3,866,293 | 円 | scratchpad/d9b_extra.out:4(再実行) | -3866293 | 円 | 一致 |
| 437 | −3,834,951 | 円 | scratchpad/d9b_extra.out:8(再実行) | -3834951 | 円 | 一致 |
| 456 | +362 | 円/日 | base/diag_tables.md:35 | +18.11(×20 = 362) | bp/日 | 一致 |
| 456 | +231 | 円/日 | base/diag_tables.md:35 | +11.55(×20 = 231) | bp/日 | 一致 |
| 456 | +497 | 円/日 | base/diag_tables.md:35 | +24.86(×20 = 497) | bp/日 | 一致 |
| 456 | −273 | 円/日 | base/diag_tables.md:36 | -13.63(×20 = -273) | bp/日 | 一致 |
| 456 | −360 | 円/日 | base/diag_tables.md:36 | -18.00(×20 = -360) | bp/日 | 一致 |
| 456 | −184 | 円/日 | base/diag_tables.md:36 | -9.19(×20 = -184) | bp/日 | 一致 |
| 478 | −635 | 円/日 | base/diag_tables.md:37 | -31.75(×20 = -635) | bp/日 | 一致 |
| 478 | −805 | 円/日 | base/diag_tables.md:37 | -40.27(×20 = -805) | bp/日 | 一致 |
| 478 | −476 | 円/日 | base/diag_tables.md:37 | -23.82(×20 = -476) | bp/日 | 一致 |
| 487 | +329 | 円/日 | count/same_bar_daily.out:3 | +329 | 円/日(pnl_bp × 20) | 一致 |
| 487 | +274 | 円/日 | count/same_bar_daily.out:3 | +274 | 円/日(pnl_bp × 20) | 一致 |
| 487 | +378 | 円/日 | count/same_bar_daily.out:3 | +378 | 円/日(pnl_bp × 20) | 一致 |
| 487 | +117 | 円/日 | count/same_bar_daily.out:3 | +117 | 円/日(pnl_bp × 20) | 一致 |
| 487 | +92 | 円/日 | count/same_bar_daily.out:3 | +92 | 円/日(pnl_bp × 20) | 一致 |
| 487 | +141 | 円/日 | count/same_bar_daily.out:3 | +141 | 円/日(pnl_bp × 20) | 一致 |
| 488 | +33 | 円/日 | count/same_bar_daily.out:4 | +33 | 円/日(pnl_bp × 20) | 一致 |
| 488 | −100 | 円/日 | count/same_bar_daily.out:4 | -100 | 円/日(pnl_bp × 20) | 一致 |
| 488 | +167 | 円/日 | count/same_bar_daily.out:4 | +167 | 円/日(pnl_bp × 20) | 一致 |
| 488 | −390 | 円/日 | count/same_bar_daily.out:4 | -390 | 円/日(pnl_bp × 20) | 一致 |
| 488 | −474 | 円/日 | count/same_bar_daily.out:4 | -474 | 円/日(pnl_bp × 20) | 一致 |
| 488 | −302 | 円/日 | count/same_bar_daily.out:4 | -302 | 円/日(pnl_bp × 20) | 一致 |

## 文書: `docs/ANALYSIS/2026-10-09_matilda_main_levels.md`

拾った数 691 個。判定ごと: 一致 691

数を拾った行: 31・57・85・115・116・117・118・124・125・126・127・128・129・130・131・132・134・167・168・169・170・171・172・174・196・197・198・199・200・201・202・203・205・209・214・215・216・217・219・241・242・243・244・268・269・270・271・292・293・294・295・297・318・319・320・321・322・323・324・325・326・327・328・330・332・352・382・384・390・416・417・418・419・434・435・436・438・442

| 文書の行 | 書かれた数 | 書かれた単位 | 出所 ファイル:行 | 出所の値 | 出所の単位 | 判定 |
|---|---|---|---|---|---|---|
| 31 | −1,452,627 | 円 | backtest_runs_shared/matilda_main_trades/levels_1/summary.json(check.pnl_jpy) | −1452626.755 | 円 | 一致 |
| 57 | −1452626.755 | 円 | backtest_runs_shared/matilda_main_trades/levels_1/summary.json(check.pnl_jpy) | −1452626.755 | 円 | 一致 |
| 85 | −1,452,627 | 円 | backtest_runs_shared/matilda_main_trades/levels_1/summary.json(check.pnl_jpy) | −1452626.755 | 円 | 一致 |
| 31 | −185,022 | 円 | backtest_runs_shared/matilda_main_trades/levels_3/summary.json(check.pnl_jpy) | −185021.571 | 円 | 一致 |
| 57 | −185021.571 | 円 | backtest_runs_shared/matilda_main_trades/levels_3/summary.json(check.pnl_jpy) | −185021.571 | 円 | 一致 |
| 85 | −185,022 | 円 | backtest_runs_shared/matilda_main_trades/levels_3/summary.json(check.pnl_jpy) | −185021.571 | 円 | 一致 |
| 31 | +227,914 | 円 | backtest_runs_shared/matilda_main_trades/levels_7/summary.json(check.pnl_jpy) | 227914.469 | 円 | 一致 |
| 57 | +227914.469 | 円 | backtest_runs_shared/matilda_main_trades/levels_7/summary.json(check.pnl_jpy) | 227914.469 | 円 | 一致 |
| 85 | +227,914 | 円 | backtest_runs_shared/matilda_main_trades/levels_7/summary.json(check.pnl_jpy) | 227914.469 | 円 | 一致 |
| 85 | −955 | 円 | scratchpad/market_side_levels.out:1(market_side.py levels_1 levels_3 levels_7 の再実行。保存された出力ファイル無し) | −955 | 円(fills の量 × 値段) | 一致 |
| 85 | −876 | 円 | scratchpad/market_side_levels.out:2(market_side.py levels_1 levels_3 levels_7 の再実行。保存された出力ファイル無し) | −876 | 円(fills の量 × 値段) | 一致 |
| 85 | −235 | 円 | scratchpad/market_side_levels.out:3(market_side.py levels_1 levels_3 levels_7 の再実行。保存された出力ファイル無し) | −235 | 円(fills の量 × 値段) | 一致 |
| 115 | +145 | 円/日 | levels_1/diag_tables.md:35 | +7.23(×20 = 145) | bp/日 | 一致 |
| 115 | −93 | 円/日 | levels_1/diag_tables.md:35 | −4.65(×20 = −93) | bp/日 | 一致 |
| 115 | +395 | 円/日 | levels_1/diag_tables.md:35 | +19.77(×20 = 395) | bp/日 | 一致 |
| 115 | −1133 | 円/日 | levels_1/diag_tables.md:36 | −56.63(×20 = −1133) | bp/日 | 一致 |
| 115 | −1278 | 円/日 | levels_1/diag_tables.md:36 | −63.90(×20 = −1278) | bp/日 | 一致 |
| 115 | −984 | 円/日 | levels_1/diag_tables.md:36 | −49.18(×20 = −984) | bp/日 | 一致 |
| 115 | −1277 | 円/日 | levels_1/diag_tables.md:37 | −63.86(×20 = −1277) | bp/日 | 一致 |
| 115 | −1577 | 円/日 | levels_1/diag_tables.md:37 | −78.85(×20 = −1577) | bp/日 | 一致 |
| 115 | −964 | 円/日 | levels_1/diag_tables.md:37 | −48.21(×20 = −964) | bp/日 | 一致 |
| 116 | +348 | 円/日 | levels_3/diag_tables.md:35 | +17.38(×20 = 348) | bp/日 | 一致 |
| 116 | +181 | 円/日 | levels_3/diag_tables.md:35 | +9.05(×20 = 181) | bp/日 | 一致 |
| 116 | +514 | 円/日 | levels_3/diag_tables.md:35 | +25.68(×20 = 514) | bp/日 | 一致 |
| 116 | −473 | 円/日 | levels_3/diag_tables.md:36 | −23.66(×20 = −473) | bp/日 | 一致 |
| 116 | −589 | 円/日 | levels_3/diag_tables.md:36 | −29.46(×20 = −589) | bp/日 | 一致 |
| 116 | −364 | 円/日 | levels_3/diag_tables.md:36 | −18.18(×20 = −364) | bp/日 | 一致 |
| 116 | −821 | 円/日 | levels_3/diag_tables.md:37 | −41.05(×20 = −821) | bp/日 | 一致 |
| 116 | −1023 | 円/日 | levels_3/diag_tables.md:37 | −51.13(×20 = −1023) | bp/日 | 一致 |
| 116 | −617 | 円/日 | levels_3/diag_tables.md:37 | −30.85(×20 = −617) | bp/日 | 一致 |
| 117 | +362 | 円/日 | base/diag_tables.md:35 | +18.11(×20 = 362) | bp/日 | 一致 |
| 117 | +231 | 円/日 | base/diag_tables.md:35 | +11.55(×20 = 231) | bp/日 | 一致 |
| 117 | +497 | 円/日 | base/diag_tables.md:35 | +24.86(×20 = 497) | bp/日 | 一致 |
| 117 | −273 | 円/日 | base/diag_tables.md:36 | −13.63(×20 = −273) | bp/日 | 一致 |
| 117 | −360 | 円/日 | base/diag_tables.md:36 | −18.00(×20 = −360) | bp/日 | 一致 |
| 117 | −184 | 円/日 | base/diag_tables.md:36 | −9.19(×20 = −184) | bp/日 | 一致 |
| 117 | −635 | 円/日 | base/diag_tables.md:37 | −31.75(×20 = −635) | bp/日 | 一致 |
| 117 | −805 | 円/日 | base/diag_tables.md:37 | −40.27(×20 = −805) | bp/日 | 一致 |
| 117 | −476 | 円/日 | base/diag_tables.md:37 | −23.82(×20 = −476) | bp/日 | 一致 |
| 118 | +333 | 円/日 | levels_7/diag_tables.md:35 | +16.64(×20 = 333) | bp/日 | 一致 |
| 118 | +224 | 円/日 | levels_7/diag_tables.md:35 | +11.18(×20 = 224) | bp/日 | 一致 |
| 118 | +448 | 円/日 | levels_7/diag_tables.md:35 | +22.42(×20 = 448) | bp/日 | 一致 |
| 118 | −178 | 円/日 | levels_7/diag_tables.md:36 | −8.88(×20 = −178) | bp/日 | 一致 |
| 118 | −250 | 円/日 | levels_7/diag_tables.md:36 | −12.51(×20 = −250) | bp/日 | 一致 |
| 118 | −106 | 円/日 | levels_7/diag_tables.md:36 | −5.30(×20 = −106) | bp/日 | 一致 |
| 118 | −510 | 円/日 | levels_7/diag_tables.md:37 | −25.51(×20 = −510) | bp/日 | 一致 |
| 118 | −663 | 円/日 | levels_7/diag_tables.md:37 | −33.13(×20 = −663) | bp/日 | 一致 |
| 118 | −373 | 円/日 | levels_7/diag_tables.md:37 | −18.66(×20 = −373) | bp/日 | 一致 |
| 124 | +80.72 | bp/日 | levels_1/diag_tables.md:21 | +80.72 | bp/日 | 一致 |
| 124 | −53.91 | bp/日 | levels_1/diag_tables.md:21 | −53.91 | bp/日 | 一致 |
| 124 | +292.43 | bp/日 | levels_1/diag_tables.md:21 | +292.43 | bp/日 | 一致 |
| 124 | +0.76 | bp/日 | levels_3/diag_tables.md:21 | +0.76 | bp/日 | 一致 |
| 124 | −76.71 | bp/日 | levels_3/diag_tables.md:21 | −76.71 | bp/日 | 一致 |
| 124 | +97.34 | bp/日 | levels_3/diag_tables.md:21 | +97.34 | bp/日 | 一致 |
| 124 | −13.14 | bp/日 | base/diag_tables.md:21 | −13.14 | bp/日 | 一致 |
| 124 | −79.49 | bp/日 | base/diag_tables.md:21 | −79.49 | bp/日 | 一致 |
| 124 | +58.82 | bp/日 | base/diag_tables.md:21 | +58.82 | bp/日 | 一致 |
| 124 | −16.80 | bp/日 | levels_7/diag_tables.md:21 | −16.80 | bp/日 | 一致 |
| 124 | −76.30 | bp/日 | levels_7/diag_tables.md:21 | −76.30 | bp/日 | 一致 |
| 124 | +44.18 | bp/日 | levels_7/diag_tables.md:21 | +44.18 | bp/日 | 一致 |
| 125 | +42.83 | bp/日 | levels_1/diag_tables.md:22 | +42.83 | bp/日 | 一致 |
| 125 | +17.11 | bp/日 | levels_1/diag_tables.md:22 | +17.11 | bp/日 | 一致 |
| 125 | +69.95 | bp/日 | levels_1/diag_tables.md:22 | +69.95 | bp/日 | 一致 |
| 125 | +15.01 | bp/日 | levels_3/diag_tables.md:22 | +15.01 | bp/日 | 一致 |
| 125 | −3.14 | bp/日 | levels_3/diag_tables.md:22 | −3.14 | bp/日 | 一致 |
| 125 | +33.52 | bp/日 | levels_3/diag_tables.md:22 | +33.52 | bp/日 | 一致 |
| 125 | +6.63 | bp/日 | base/diag_tables.md:22 | +6.63 | bp/日 | 一致 |
| 125 | −8.10 | bp/日 | base/diag_tables.md:22 | −8.10 | bp/日 | 一致 |
| 125 | +21.66 | bp/日 | base/diag_tables.md:22 | +21.66 | bp/日 | 一致 |
| 125 | +3.19 | bp/日 | levels_7/diag_tables.md:22 | +3.19 | bp/日 | 一致 |
| 125 | −9.39 | bp/日 | levels_7/diag_tables.md:22 | −9.39 | bp/日 | 一致 |
| 125 | +15.90 | bp/日 | levels_7/diag_tables.md:22 | +15.90 | bp/日 | 一致 |
| 126 | +13.70 | bp/日 | levels_1/diag_tables.md:23 | +13.70 | bp/日 | 一致 |
| 126 | −16.68 | bp/日 | levels_1/diag_tables.md:23 | −16.68 | bp/日 | 一致 |
| 126 | +41.96 | bp/日 | levels_1/diag_tables.md:23 | +41.96 | bp/日 | 一致 |
| 126 | +25.70 | bp/日 | levels_3/diag_tables.md:23 | +25.70 | bp/日 | 一致 |
| 126 | +5.11 | bp/日 | levels_3/diag_tables.md:23 | +5.11 | bp/日 | 一致 |
| 126 | +46.26 | bp/日 | levels_3/diag_tables.md:23 | +46.26 | bp/日 | 一致 |
| 126 | +28.19 | bp/日 | base/diag_tables.md:23 | +28.19 | bp/日 | 一致 |
| 126 | +10.73 | bp/日 | base/diag_tables.md:23 | +10.73 | bp/日 | 一致 |
| 126 | +45.25 | bp/日 | base/diag_tables.md:23 | +45.25 | bp/日 | 一致 |
| 126 | +28.21 | bp/日 | levels_7/diag_tables.md:23 | +28.21 | bp/日 | 一致 |
| 126 | +13.00 | bp/日 | levels_7/diag_tables.md:23 | +13.00 | bp/日 | 一致 |
| 126 | +42.16 | bp/日 | levels_7/diag_tables.md:23 | +42.16 | bp/日 | 一致 |
| 127 | −13.44 | bp/日 | levels_1/diag_tables.md:24 | −13.44 | bp/日 | 一致 |
| 127 | −34.07 | bp/日 | levels_1/diag_tables.md:24 | −34.07 | bp/日 | 一致 |
| 127 | +4.44 | bp/日 | levels_1/diag_tables.md:24 | +4.44 | bp/日 | 一致 |
| 127 | +22.03 | bp/日 | levels_3/diag_tables.md:24 | +22.03 | bp/日 | 一致 |
| 127 | +8.88 | bp/日 | levels_3/diag_tables.md:24 | +8.88 | bp/日 | 一致 |
| 127 | +34.33 | bp/日 | levels_3/diag_tables.md:24 | +34.33 | bp/日 | 一致 |
| 127 | +27.15 | bp/日 | base/diag_tables.md:24 | +27.15 | bp/日 | 一致 |
| 127 | +16.33 | bp/日 | base/diag_tables.md:24 | +16.33 | bp/日 | 一致 |
| 127 | +37.39 | bp/日 | base/diag_tables.md:24 | +37.39 | bp/日 | 一致 |
| 127 | +25.18 | bp/日 | levels_7/diag_tables.md:24 | +25.18 | bp/日 | 一致 |
| 127 | +16.55 | bp/日 | levels_7/diag_tables.md:24 | +16.55 | bp/日 | 一致 |
| 127 | +33.52 | bp/日 | levels_7/diag_tables.md:24 | +33.52 | bp/日 | 一致 |
| 128 | −22.22 | bp/日 | levels_1/diag_tables.md:25 | −22.22 | bp/日 | 一致 |
| 128 | −35.68 | bp/日 | levels_1/diag_tables.md:25 | −35.68 | bp/日 | 一致 |
| 128 | −9.45 | bp/日 | levels_1/diag_tables.md:25 | −9.45 | bp/日 | 一致 |
| 128 | +7.12 | bp/日 | levels_3/diag_tables.md:25 | +7.12 | bp/日 | 一致 |
| 128 | −3.26 | bp/日 | levels_3/diag_tables.md:25 | −3.26 | bp/日 | 一致 |
| 128 | +16.50 | bp/日 | levels_3/diag_tables.md:25 | +16.50 | bp/日 | 一致 |
| 128 | +12.21 | bp/日 | base/diag_tables.md:25 | +12.21 | bp/日 | 一致 |
| 128 | +4.39 | bp/日 | base/diag_tables.md:25 | +4.39 | bp/日 | 一致 |
| 128 | +19.71 | bp/日 | base/diag_tables.md:25 | +19.71 | bp/日 | 一致 |
| 128 | +11.93 | bp/日 | levels_7/diag_tables.md:25 | +11.93 | bp/日 | 一致 |
| 128 | +5.68 | bp/日 | levels_7/diag_tables.md:25 | +5.68 | bp/日 | 一致 |
| 128 | +17.98 | bp/日 | levels_7/diag_tables.md:25 | +17.98 | bp/日 | 一致 |
| 129 | −36.61 | bp/日 | levels_1/diag_tables.md:26 | −36.61 | bp/日 | 一致 |
| 129 | −48.14 | bp/日 | levels_1/diag_tables.md:26 | −48.14 | bp/日 | 一致 |
| 129 | −26.20 | bp/日 | levels_1/diag_tables.md:26 | −26.20 | bp/日 | 一致 |
| 129 | −5.86 | bp/日 | levels_3/diag_tables.md:26 | −5.86 | bp/日 | 一致 |
| 129 | −15.88 | bp/日 | levels_3/diag_tables.md:26 | −15.88 | bp/日 | 一致 |
| 129 | +2.82 | bp/日 | levels_3/diag_tables.md:26 | +2.82 | bp/日 | 一致 |
| 129 | +0.30 | bp/日 | base/diag_tables.md:26 | +0.30 | bp/日 | 一致 |
| 129 | −7.90 | bp/日 | base/diag_tables.md:26 | −7.90 | bp/日 | 一致 |
| 129 | +8.16 | bp/日 | base/diag_tables.md:26 | +8.16 | bp/日 | 一致 |
| 129 | +1.78 | bp/日 | levels_7/diag_tables.md:26 | +1.78 | bp/日 | 一致 |
| 129 | −4.78 | bp/日 | levels_7/diag_tables.md:26 | −4.78 | bp/日 | 一致 |
| 129 | +8.63 | bp/日 | levels_7/diag_tables.md:26 | +8.63 | bp/日 | 一致 |
| 130 | −81.22 | bp/日 | levels_1/diag_tables.md:27 | −81.22 | bp/日 | 一致 |
| 130 | −105.73 | bp/日 | levels_1/diag_tables.md:27 | −105.73 | bp/日 | 一致 |
| 130 | −59.83 | bp/日 | levels_1/diag_tables.md:27 | −59.83 | bp/日 | 一致 |
| 130 | −33.58 | bp/日 | levels_3/diag_tables.md:27 | −33.58 | bp/日 | 一致 |
| 130 | −51.02 | bp/日 | levels_3/diag_tables.md:27 | −51.02 | bp/日 | 一致 |
| 130 | −18.83 | bp/日 | levels_3/diag_tables.md:27 | −18.83 | bp/日 | 一致 |
| 130 | −19.21 | bp/日 | base/diag_tables.md:27 | −19.21 | bp/日 | 一致 |
| 130 | −32.15 | bp/日 | base/diag_tables.md:27 | −32.15 | bp/日 | 一致 |
| 130 | −8.03 | bp/日 | base/diag_tables.md:27 | −8.03 | bp/日 | 一致 |
| 130 | −13.61 | bp/日 | levels_7/diag_tables.md:27 | −13.61 | bp/日 | 一致 |
| 130 | −24.12 | bp/日 | levels_7/diag_tables.md:27 | −24.12 | bp/日 | 一致 |
| 130 | −4.80 | bp/日 | levels_7/diag_tables.md:27 | −4.80 | bp/日 | 一致 |
| 131 | −56.97 | bp/日 | levels_1/diag_tables.md:28 | −56.97 | bp/日 | 一致 |
| 131 | −71.60 | bp/日 | levels_1/diag_tables.md:28 | −71.60 | bp/日 | 一致 |
| 131 | −43.32 | bp/日 | levels_1/diag_tables.md:28 | −43.32 | bp/日 | 一致 |
| 131 | −22.87 | bp/日 | levels_3/diag_tables.md:28 | −22.87 | bp/日 | 一致 |
| 131 | −32.33 | bp/日 | levels_3/diag_tables.md:28 | −32.33 | bp/日 | 一致 |
| 131 | −13.50 | bp/日 | levels_3/diag_tables.md:28 | −13.50 | bp/日 | 一致 |
| 131 | −13.15 | bp/日 | base/diag_tables.md:28 | −13.15 | bp/日 | 一致 |
| 131 | −20.44 | bp/日 | base/diag_tables.md:28 | −20.44 | bp/日 | 一致 |
| 131 | −6.51 | bp/日 | base/diag_tables.md:28 | −6.51 | bp/日 | 一致 |
| 131 | −6.93 | bp/日 | levels_7/diag_tables.md:28 | −6.93 | bp/日 | 一致 |
| 131 | −12.76 | bp/日 | levels_7/diag_tables.md:28 | −12.76 | bp/日 | 一致 |
| 131 | −1.29 | bp/日 | levels_7/diag_tables.md:28 | −1.29 | bp/日 | 一致 |
| 132 | −54.01 | bp/日 | levels_1/diag_tables.md:29 | −54.01 | bp/日 | 一致 |
| 132 | −66.85 | bp/日 | levels_1/diag_tables.md:29 | −66.85 | bp/日 | 一致 |
| 132 | −40.76 | bp/日 | levels_1/diag_tables.md:29 | −40.76 | bp/日 | 一致 |
| 132 | −34.30 | bp/日 | levels_3/diag_tables.md:29 | −34.30 | bp/日 | 一致 |
| 132 | −44.16 | bp/日 | levels_3/diag_tables.md:29 | −44.16 | bp/日 | 一致 |
| 132 | −24.15 | bp/日 | levels_3/diag_tables.md:29 | −24.15 | bp/日 | 一致 |
| 132 | −23.94 | bp/日 | base/diag_tables.md:29 | −23.94 | bp/日 | 一致 |
| 132 | −31.95 | bp/日 | base/diag_tables.md:29 | −31.95 | bp/日 | 一致 |
| 132 | −15.74 | bp/日 | base/diag_tables.md:29 | −15.74 | bp/日 | 一致 |
| 132 | −17.80 | bp/日 | levels_7/diag_tables.md:29 | −17.80 | bp/日 | 一致 |
| 132 | −24.03 | bp/日 | levels_7/diag_tables.md:29 | −24.03 | bp/日 | 一致 |
| 132 | −11.42 | bp/日 | levels_7/diag_tables.md:29 | −11.42 | bp/日 | 一致 |
| 134 | −1,133 | 円/日 | levels_1/diag_tables.md:36 | −56.63(×20 = −1133) | bp/日 | 一致 |
| 134 | −178 | 円/日 | levels_7/diag_tables.md:36 | −8.88(×20 = −178) | bp/日 | 一致 |
| 134 | +333 | 円/日 | levels_7/diag_tables.md:35 | +16.64(×20 = 333) | bp/日 | 一致 |
| 134 | +362 | 円/日 | base/diag_tables.md:35 | +18.11(×20 = 362) | bp/日 | 一致 |
| 134 | +42.83 | bp/日 | levels_1/diag_tables.md:22 | +42.83 | bp/日 | 一致 |
| 167 | −107 | 円/日 | levels/scenes.out:5 | −107 | 円/日(pnl_jpy) | 一致 |
| 167 | −279 | 円/日 | levels/scenes.out:5 | −279 | 円/日(pnl_jpy) | 一致 |
| 167 | +40 | 円/日 | levels/scenes.out:5 | +40 | 円/日(pnl_jpy) | 一致 |
| 167 | +246 | 円/日 | levels/scenes.out:17 | +246 | 円/日(pnl_jpy) | 一致 |
| 167 | +117 | 円/日 | levels/scenes.out:17 | +117 | 円/日(pnl_jpy) | 一致 |
| 167 | +352 | 円/日 | levels/scenes.out:17 | +352 | 円/日(pnl_jpy) | 一致 |
| 167 | +264 | 円/日 | scratchpad/d2_scenes.out:3(d2_scenes.py の再実行) | +264 | 円/日(pnl_jpy) | 一致 |
| 167 | +154 | 円/日 | scratchpad/d2_scenes.out:3(d2_scenes.py の再実行) | +154 | 円/日(pnl_jpy) | 一致 |
| 167 | +357 | 円/日 | scratchpad/d2_scenes.out:3(d2_scenes.py の再実行) | +357 | 円/日(pnl_jpy) | 一致 |
| 167 | +251 | 円/日 | levels/scenes.out:29 | +251 | 円/日(pnl_jpy) | 一致 |
| 167 | +165 | 円/日 | levels/scenes.out:29 | +165 | 円/日(pnl_jpy) | 一致 |
| 167 | +329 | 円/日 | levels/scenes.out:29 | +329 | 円/日(pnl_jpy) | 一致 |
| 168 | −710 | 円/日 | levels/scenes.out:6 | −710 | 円/日(pnl_jpy) | 一致 |
| 168 | −842 | 円/日 | levels/scenes.out:6 | −842 | 円/日(pnl_jpy) | 一致 |
| 168 | −557 | 円/日 | levels/scenes.out:6 | −557 | 円/日(pnl_jpy) | 一致 |
| 168 | −334 | 円/日 | levels/scenes.out:18 | −334 | 円/日(pnl_jpy) | 一致 |
| 168 | −444 | 円/日 | levels/scenes.out:18 | −444 | 円/日(pnl_jpy) | 一致 |
| 168 | −215 | 円/日 | levels/scenes.out:18 | −215 | 円/日(pnl_jpy) | 一致 |
| 168 | −216 | 円/日 | scratchpad/d2_scenes.out:4(d2_scenes.py の再実行) | −216 | 円/日(pnl_jpy) | 一致 |
| 168 | −307 | 円/日 | scratchpad/d2_scenes.out:4(d2_scenes.py の再実行) | −307 | 円/日(pnl_jpy) | 一致 |
| 168 | −126 | 円/日 | scratchpad/d2_scenes.out:4(d2_scenes.py の再実行) | −126 | 円/日(pnl_jpy) | 一致 |
| 168 | −145 | 円/日 | levels/scenes.out:30 | −145 | 円/日(pnl_jpy) | 一致 |
| 168 | −221 | 円/日 | levels/scenes.out:30 | −221 | 円/日(pnl_jpy) | 一致 |
| 168 | −72 | 円/日 | levels/scenes.out:30 | −72 | 円/日(pnl_jpy) | 一致 |
| 169 | −135 | 円/日 | levels/scenes.out:8 | −135 | 円/日(pnl_jpy) | 一致 |
| 169 | −482 | 円/日 | levels/scenes.out:8 | −482 | 円/日(pnl_jpy) | 一致 |
| 169 | +221 | 円/日 | levels/scenes.out:8 | +221 | 円/日(pnl_jpy) | 一致 |
| 169 | +344 | 円/日 | levels/scenes.out:20 | +344 | 円/日(pnl_jpy) | 一致 |
| 169 | +90 | 円/日 | levels/scenes.out:20 | +90 | 円/日(pnl_jpy) | 一致 |
| 169 | +634 | 円/日 | levels/scenes.out:20 | +634 | 円/日(pnl_jpy) | 一致 |
| 169 | +411 | 円/日 | scratchpad/d2_scenes.out:6(d2_scenes.py の再実行) | +411 | 円/日(pnl_jpy) | 一致 |
| 169 | +226 | 円/日 | scratchpad/d2_scenes.out:6(d2_scenes.py の再実行) | +226 | 円/日(pnl_jpy) | 一致 |
| 169 | +634 | 円/日 | scratchpad/d2_scenes.out:6(d2_scenes.py の再実行) | +634 | 円/日(pnl_jpy) | 一致 |
| 169 | +354 | 円/日 | levels/scenes.out:32 | +354 | 円/日(pnl_jpy) | 一致 |
| 169 | +206 | 円/日 | levels/scenes.out:32 | +206 | 円/日(pnl_jpy) | 一致 |
| 169 | +536 | 円/日 | levels/scenes.out:32 | +536 | 円/日(pnl_jpy) | 一致 |
| 170 | −1022 | 円/日 | levels/scenes.out:9 | −1022 | 円/日(pnl_jpy) | 一致 |
| 170 | −1276 | 円/日 | levels/scenes.out:9 | −1276 | 円/日(pnl_jpy) | 一致 |
| 170 | −775 | 円/日 | levels/scenes.out:9 | −775 | 円/日(pnl_jpy) | 一致 |
| 170 | −449 | 円/日 | levels/scenes.out:21 | −449 | 円/日(pnl_jpy) | 一致 |
| 170 | −653 | 円/日 | levels/scenes.out:21 | −653 | 円/日(pnl_jpy) | 一致 |
| 170 | −248 | 円/日 | levels/scenes.out:21 | −248 | 円/日(pnl_jpy) | 一致 |
| 170 | −282 | 円/日 | scratchpad/d2_scenes.out:7(d2_scenes.py の再実行) | −282 | 円/日(pnl_jpy) | 一致 |
| 170 | −462 | 円/日 | scratchpad/d2_scenes.out:7(d2_scenes.py の再実行) | −462 | 円/日(pnl_jpy) | 一致 |
| 170 | −111 | 円/日 | scratchpad/d2_scenes.out:7(d2_scenes.py の再実行) | −111 | 円/日(pnl_jpy) | 一致 |
| 170 | −194 | 円/日 | levels/scenes.out:33 | −194 | 円/日(pnl_jpy) | 一致 |
| 170 | −344 | 円/日 | levels/scenes.out:33 | −344 | 円/日(pnl_jpy) | 一致 |
| 170 | −53 | 円/日 | levels/scenes.out:33 | −53 | 円/日(pnl_jpy) | 一致 |
| 171 | −165 | 円/日 | levels/scenes.out:11 | −165 | 円/日(pnl_jpy) | 一致 |
| 171 | −743 | 円/日 | levels/scenes.out:11 | −743 | 円/日(pnl_jpy) | 一致 |
| 171 | +399 | 円/日 | levels/scenes.out:11 | +399 | 円/日(pnl_jpy) | 一致 |
| 171 | +504 | 円/日 | levels/scenes.out:23 | +504 | 円/日(pnl_jpy) | 一致 |
| 171 | +118 | 円/日 | levels/scenes.out:23 | +118 | 円/日(pnl_jpy) | 一致 |
| 171 | +923 | 円/日 | levels/scenes.out:23 | +923 | 円/日(pnl_jpy) | 一致 |
| 171 | +656 | 円/日 | scratchpad/d2_scenes.out:9(d2_scenes.py の再実行) | +656 | 円/日(pnl_jpy) | 一致 |
| 171 | +336 | 円/日 | scratchpad/d2_scenes.out:9(d2_scenes.py の再実行) | +336 | 円/日(pnl_jpy) | 一致 |
| 171 | +1007 | 円/日 | scratchpad/d2_scenes.out:9(d2_scenes.py の再実行) | +1007 | 円/日(pnl_jpy) | 一致 |
| 171 | +665 | 円/日 | levels/scenes.out:35 | +665 | 円/日(pnl_jpy) | 一致 |
| 171 | +404 | 円/日 | levels/scenes.out:35 | +404 | 円/日(pnl_jpy) | 一致 |
| 171 | +959 | 円/日 | levels/scenes.out:35 | +959 | 円/日(pnl_jpy) | 一致 |
| 172 | −1801 | 円/日 | levels/scenes.out:12 | −1801 | 円/日(pnl_jpy) | 一致 |
| 172 | −2148 | 円/日 | levels/scenes.out:12 | −2148 | 円/日(pnl_jpy) | 一致 |
| 172 | −1461 | 円/日 | levels/scenes.out:12 | −1461 | 円/日(pnl_jpy) | 一致 |
| 172 | −684 | 円/日 | levels/scenes.out:24 | −684 | 円/日(pnl_jpy) | 一致 |
| 172 | −932 | 円/日 | levels/scenes.out:24 | −932 | 円/日(pnl_jpy) | 一致 |
| 172 | −420 | 円/日 | levels/scenes.out:24 | −420 | 円/日(pnl_jpy) | 一致 |
| 172 | −343 | 円/日 | scratchpad/d2_scenes.out:10(d2_scenes.py の再実行) | −343 | 円/日(pnl_jpy) | 一致 |
| 172 | −529 | 円/日 | scratchpad/d2_scenes.out:10(d2_scenes.py の再実行) | −529 | 円/日(pnl_jpy) | 一致 |
| 172 | −135 | 円/日 | scratchpad/d2_scenes.out:10(d2_scenes.py の再実行) | −135 | 円/日(pnl_jpy) | 一致 |
| 172 | −209 | 円/日 | levels/scenes.out:36 | −209 | 円/日(pnl_jpy) | 一致 |
| 172 | −367 | 円/日 | levels/scenes.out:36 | −367 | 円/日(pnl_jpy) | 一致 |
| 172 | −42 | 円/日 | levels/scenes.out:36 | −42 | 円/日(pnl_jpy) | 一致 |
| 174 | −1,801 | 円/日 | levels/scenes.out:12 | −1801 | 円/日 | 一致 |
| 174 | −209 | 円/日 | levels/scenes.out:36 | −209 | 円/日 | 一致 |
| 196 | +63.0 | 円/本 | levels/compare.md:7 | +63.0 | 円(pnl_jpy) | 一致 |
| 196 | −443.4 | 円/本 | levels/compare.md:7 | −443.4 | 円(pnl_jpy) | 一致 |
| 196 | +212392 | 円 | levels/compare.md:7 | +212392 | 円(pnl_jpy) | 一致 |
| 196 | +212392 | 円 | levels/compare.md:7 | +212392 | 円(pnl_jpy) | 一致 |
| 196 | −319818 | 円 | levels/compare.md:7 | −319818 | 円(pnl_jpy) | 一致 |
| 197 | +50.3 | 円/本 | levels/compare.md:8 | +50.3 | 円(pnl_jpy) | 一致 |
| 197 | −351.0 | 円/本 | levels/compare.md:8 | −351.0 | 円(pnl_jpy) | 一致 |
| 197 | −4069614 | 円 | levels/compare.md:8 | −4069614 | 円(pnl_jpy) | 一致 |
| 197 | +510686 | 円 | levels/compare.md:8 | +510686 | 円(pnl_jpy) | 一致 |
| 197 | −21525 | 円 | levels/compare.md:8 | −21525 | 円(pnl_jpy) | 一致 |
| 198 | +40.5 | 円/本 | levels/compare.md:6 | +40.5 | 円(pnl_jpy) | 一致 |
| 198 | −281.0 | 円/本 | levels/compare.md:6 | −281.0 | 円(pnl_jpy) | 一致 |
| 198 | −3866293 | 円 | levels/compare.md:6 | −3866293 | 円(pnl_jpy) | 一致 |
| 198 | +532210 | 円 | levels/compare.md:6 | +532210 | 円(pnl_jpy) | 一致 |
| 198 | 0 | 円 | levels/compare.md:6 | +0 | 円(pnl_jpy) | 一致 |
| 199 | +33.2 | 円/本 | levels/compare.md:9 | +33.2 | 円(pnl_jpy) | 一致 |
| 199 | −228.1 | 円/本 | levels/compare.md:9 | −228.1 | 円(pnl_jpy) | 一致 |
| 199 | −2978976 | 円 | levels/compare.md:9 | −2978976 | 円(pnl_jpy) | 一致 |
| 199 | +488843 | 円 | levels/compare.md:9 | +488843 | 円(pnl_jpy) | 一致 |
| 199 | −43367 | 円 | levels/compare.md:9 | −43367 | 円(pnl_jpy) | 一致 |
| 200 | +48.3 | 円/本 | levels/compare.md:16 | +48.3 | 円(pnl_jpy) | 一致 |
| 200 | −389.3 | 円/本 | levels/compare.md:16 | −389.3 | 円(pnl_jpy) | 一致 |
| 200 | −1665019 | 円 | levels/compare.md:16 | −1665019 | 円(pnl_jpy) | 一致 |
| 200 | −1665019 | 円 | levels/compare.md:16 | −1665019 | 円(pnl_jpy) | 一致 |
| 200 | −1264198 | 円 | levels/compare.md:16 | −1264198 | 円(pnl_jpy) | 一致 |
| 201 | +40.1 | 円/本 | levels/compare.md:17 | +40.1 | 円(pnl_jpy) | 一致 |
| 201 | −302.5 | 円/本 | levels/compare.md:17 | −302.5 | 円(pnl_jpy) | 一致 |
| 201 | −4239080 | 円 | levels/compare.md:17 | −4239080 | 円(pnl_jpy) | 一致 |
| 201 | −695707 | 円 | levels/compare.md:17 | −695707 | 円(pnl_jpy) | 一致 |
| 201 | −294886 | 円 | levels/compare.md:17 | −294886 | 円(pnl_jpy) | 一致 |
| 202 | +32.2 | 円/本 | levels/compare.md:15 | +32.2 | 円(pnl_jpy) | 一致 |
| 202 | −238.4 | 円/本 | levels/compare.md:15 | −238.4 | 円(pnl_jpy) | 一致 |
| 202 | −3834951 | 円 | levels/compare.md:15 | −3834951 | 円(pnl_jpy) | 一致 |
| 202 | −400821 | 円 | levels/compare.md:15 | −400821 | 円(pnl_jpy) | 一致 |
| 202 | 0 | 円 | levels/compare.md:15 | +0 | 円(pnl_jpy) | 一致 |
| 203 | +25.6 | 円/本 | levels/compare.md:18 | +25.6 | 円(pnl_jpy) | 一致 |
| 203 | −187.9 | 円/本 | levels/compare.md:18 | −187.9 | 円(pnl_jpy) | 一致 |
| 203 | −2844418 | 円 | levels/compare.md:18 | −2844418 | 円(pnl_jpy) | 一致 |
| 203 | −260929 | 円 | levels/compare.md:18 | −260929 | 円(pnl_jpy) | 一致 |
| 203 | +139892 | 円 | levels/compare.md:18 | +139892 | 円(pnl_jpy) | 一致 |
| 205 | −242〜−554 | 円/本 | levels/compare.md:6〜9・15〜18 の「成行 1 本」 | 前半・後半 8 値の範囲 -242.0〜-554.3 | 円 | 一致 |
| 209 | +212,392 | 円 | levels/compare.md:7 | +212392 | 円 | 一致 |
| 209 | −1,665,019 | 円 | levels/compare.md:16 | −1665019 | 円 | 一致 |
| 209 | +2,373,234 | 円 | same_bar_all.out:20(levels_1 の「同じ足 前半」) | 2373234。文書は出所を「下の表」(same_bar_daily_4fam.out、円/日)と書いている。和は same_bar_all.out にある | 円(pnl_jpy) | 一致 |
| 209 | −2,160,842 | 円 | same_bar_all.out:20(levels_1 の「後まで 前半」) | −2160842。同上 | 円(pnl_jpy) | 一致 |
| 214 | +1616 | 円/日 | same_bar_daily_4fam.out:3 | +1616 | 円/日(pnl_bp × 20) | 一致 |
| 214 | +1453 | 円/日 | same_bar_daily_4fam.out:3 | +1453 | 円/日(pnl_bp × 20) | 一致 |
| 214 | +1768 | 円/日 | same_bar_daily_4fam.out:3 | +1768 | 円/日(pnl_bp × 20) | 一致 |
| 214 | +997 | 円/日 | same_bar_daily_4fam.out:3 | +997 | 円/日(pnl_bp × 20) | 一致 |
| 214 | +912 | 円/日 | same_bar_daily_4fam.out:3 | +912 | 円/日(pnl_bp × 20) | 一致 |
| 214 | +1075 | 円/日 | same_bar_daily_4fam.out:3 | +1075 | 円/日(pnl_bp × 20) | 一致 |
| 214 | −1471 | 円/日 | same_bar_daily_4fam.out:4 | −1471 | 円/日(pnl_bp × 20) | 一致 |
| 214 | −1753 | 円/日 | same_bar_daily_4fam.out:4 | −1753 | 円/日(pnl_bp × 20) | 一致 |
| 214 | −1184 | 円/日 | same_bar_daily_4fam.out:4 | −1184 | 円/日(pnl_bp × 20) | 一致 |
| 214 | −2129 | 円/日 | same_bar_daily_4fam.out:4 | −2129 | 円/日(pnl_bp × 20) | 一致 |
| 214 | −2293 | 円/日 | same_bar_daily_4fam.out:4 | −2293 | 円/日(pnl_bp × 20) | 一致 |
| 214 | −1957 | 円/日 | same_bar_daily_4fam.out:4 | −1957 | 円/日(pnl_bp × 20) | 一致 |
| 215 | +583 | 円/日 | same_bar_daily_4fam.out:5 | +583 | 円/日(pnl_bp × 20) | 一致 |
| 215 | +503 | 円/日 | same_bar_daily_4fam.out:5 | +503 | 円/日(pnl_bp × 20) | 一致 |
| 215 | +651 | 円/日 | same_bar_daily_4fam.out:5 | +651 | 円/日(pnl_bp × 20) | 一致 |
| 215 | +265 | 円/日 | same_bar_daily_4fam.out:5 | +265 | 円/日(pnl_bp × 20) | 一致 |
| 215 | +229 | 円/日 | same_bar_daily_4fam.out:5 | +229 | 円/日(pnl_bp × 20) | 一致 |
| 215 | +299 | 円/日 | same_bar_daily_4fam.out:5 | +299 | 円/日(pnl_bp × 20) | 一致 |
| 215 | −235 | 円/日 | same_bar_daily_4fam.out:6 | −235 | 円/日(pnl_bp × 20) | 一致 |
| 215 | −408 | 円/日 | same_bar_daily_4fam.out:6 | −408 | 円/日(pnl_bp × 20) | 一致 |
| 215 | −70 | 円/日 | same_bar_daily_4fam.out:6 | −70 | 円/日(pnl_bp × 20) | 一致 |
| 215 | −738 | 円/日 | same_bar_daily_4fam.out:6 | −738 | 円/日(pnl_bp × 20) | 一致 |
| 215 | −853 | 円/日 | same_bar_daily_4fam.out:6 | −853 | 円/日(pnl_bp × 20) | 一致 |
| 215 | −631 | 円/日 | same_bar_daily_4fam.out:6 | −631 | 円/日(pnl_bp × 20) | 一致 |
| 216 | +329 | 円/日 | count/same_bar_daily.out:3 | +329 | 円/日(pnl_bp × 20) | 一致 |
| 216 | +274 | 円/日 | count/same_bar_daily.out:3 | +274 | 円/日(pnl_bp × 20) | 一致 |
| 216 | +378 | 円/日 | count/same_bar_daily.out:3 | +378 | 円/日(pnl_bp × 20) | 一致 |
| 216 | +117 | 円/日 | count/same_bar_daily.out:3 | +117 | 円/日(pnl_bp × 20) | 一致 |
| 216 | +92 | 円/日 | count/same_bar_daily.out:3 | +92 | 円/日(pnl_bp × 20) | 一致 |
| 216 | +141 | 円/日 | count/same_bar_daily.out:3 | +141 | 円/日(pnl_bp × 20) | 一致 |
| 216 | +33 | 円/日 | count/same_bar_daily.out:4 | +33 | 円/日(pnl_bp × 20) | 一致 |
| 216 | −100 | 円/日 | count/same_bar_daily.out:4 | −100 | 円/日(pnl_bp × 20) | 一致 |
| 216 | +167 | 円/日 | count/same_bar_daily.out:4 | +167 | 円/日(pnl_bp × 20) | 一致 |
| 216 | −390 | 円/日 | count/same_bar_daily.out:4 | −390 | 円/日(pnl_bp × 20) | 一致 |
| 216 | −474 | 円/日 | count/same_bar_daily.out:4 | −474 | 円/日(pnl_bp × 20) | 一致 |
| 216 | −302 | 円/日 | count/same_bar_daily.out:4 | −302 | 円/日(pnl_bp × 20) | 一致 |
| 217 | +232 | 円/日 | same_bar_daily_4fam.out:7 | +232 | 円/日(pnl_bp × 20) | 一致 |
| 217 | +190 | 円/日 | same_bar_daily_4fam.out:7 | +190 | 円/日(pnl_bp × 20) | 一致 |
| 217 | +270 | 円/日 | same_bar_daily_4fam.out:7 | +270 | 円/日(pnl_bp × 20) | 一致 |
| 217 | +72 | 円/日 | same_bar_daily_4fam.out:7 | +72 | 円/日(pnl_bp × 20) | 一致 |
| 217 | +53 | 円/日 | same_bar_daily_4fam.out:7 | +53 | 円/日(pnl_bp × 20) | 一致 |
| 217 | +90 | 円/日 | same_bar_daily_4fam.out:7 | +90 | 円/日(pnl_bp × 20) | 一致 |
| 217 | +100 | 円/日 | same_bar_daily_4fam.out:8 | +100 | 円/日(pnl_bp × 20) | 一致 |
| 217 | −11 | 円/日 | same_bar_daily_4fam.out:8 | −11 | 円/日(pnl_bp × 20) | 一致 |
| 217 | +215 | 円/日 | same_bar_daily_4fam.out:8 | +215 | 円/日(pnl_bp × 20) | 一致 |
| 217 | −250 | 円/日 | same_bar_daily_4fam.out:8 | −250 | 円/日(pnl_bp × 20) | 一致 |
| 217 | −318 | 円/日 | same_bar_daily_4fam.out:8 | −318 | 円/日(pnl_bp × 20) | 一致 |
| 217 | −180 | 円/日 | same_bar_daily_4fam.out:8 | −180 | 円/日(pnl_bp × 20) | 一致 |
| 219 | +323 | 円/日 | 文書 214〜217 行の「同じ足の中 前半」× 段数 ÷ 5(出所 same_bar_daily_4fam.out) | 323.2 | 円/日 | 一致 |
| 219 | +350 | 円/日 | 文書 214〜217 行の「同じ足の中 前半」× 段数 ÷ 5(出所 same_bar_daily_4fam.out) | 349.8 | 円/日 | 一致 |
| 219 | +329 | 円/日 | 文書 214〜217 行の「同じ足の中 前半」× 段数 ÷ 5(出所 count/same_bar_daily.out) | 329 | 円/日 | 一致 |
| 219 | +325 | 円/日 | 文書 214〜217 行の「同じ足の中 前半」× 段数 ÷ 5(出所 same_bar_daily_4fam.out) | 324.8 | 円/日 | 一致 |
| 241 | +13062520 | 円 | levels_1/diag_paths.md:11 | +653126(×20 = 13062520) | bp(単位名なし。pnl_bp) | 一致 |
| 241 | −8190320 | 円 | levels_1/diag_paths.md:12 | −409516(×20 = −8190320) | bp(単位名なし。pnl_bp) | 一致 |
| 241 | −30.70 | move_bp | levels_1/diag_paths.md:12 | −30.70 | bp(値動き) | 一致 |
| 241 | −10162940 | 円 | levels_1/diag_paths.md:13 | −508147(×20 = −10162940) | bp(単位名なし。pnl_bp) | 一致 |
| 241 | −32.38 | move_bp | levels_1/diag_paths.md:13 | −32.38 | bp(値動き) | 一致 |
| 241 | −0.33 | move_bp | levels_1/diag_paths.md:22 | −0.33 | bp(値動き) | 一致 |
| 241 | −0.45 | move_bp | levels_1/diag_paths.md:22 | −0.45 | bp(値動き) | 一致 |
| 241 | −0.21 | move_bp | levels_1/diag_paths.md:22 | −0.21 | bp(値動き) | 一致 |
| 241 | −0.64 | move_bp | levels_1/diag_paths.md:23 | −0.64 | bp(値動き) | 一致 |
| 241 | −0.87 | move_bp | levels_1/diag_paths.md:23 | −0.87 | bp(値動き) | 一致 |
| 241 | −0.42 | move_bp | levels_1/diag_paths.md:23 | −0.42 | bp(値動き) | 一致 |
| 242 | +12339800 | 円 | levels_3/diag_paths.md:11 | +616990(×20 = 12339800) | bp(単位名なし。pnl_bp) | 一致 |
| 242 | −6073360 | 円 | levels_3/diag_paths.md:12 | −303668(×20 = −6073360) | bp(単位名なし。pnl_bp) | 一致 |
| 242 | −30.91 | move_bp | levels_3/diag_paths.md:12 | −30.91 | bp(値動き) | 一致 |
| 242 | −7696880 | 円 | levels_3/diag_paths.md:13 | −384844(×20 = −7696880) | bp(単位名なし。pnl_bp) | 一致 |
| 242 | −32.57 | move_bp | levels_3/diag_paths.md:13 | −32.57 | bp(値動き) | 一致 |
| 242 | −0.34 | move_bp | levels_3/diag_paths.md:22 | −0.34 | bp(値動き) | 一致 |
| 242 | −0.45 | move_bp | levels_3/diag_paths.md:22 | −0.45 | bp(値動き) | 一致 |
| 242 | −0.22 | move_bp | levels_3/diag_paths.md:22 | −0.22 | bp(値動き) | 一致 |
| 242 | −0.66 | move_bp | levels_3/diag_paths.md:23 | −0.66 | bp(値動き) | 一致 |
| 242 | −0.90 | move_bp | levels_3/diag_paths.md:23 | −0.90 | bp(値動き) | 一致 |
| 242 | −0.43 | move_bp | levels_3/diag_paths.md:23 | −0.43 | bp(値動き) | 一致 |
| 243 | +10177340 | 円 | base/diag_paths.md:11 | +508867(×20 = 10177340) | bp(単位名なし。pnl_bp) | 一致 |
| 243 | −4695040 | 円 | base/diag_paths.md:12 | −234752(×20 = −4695040) | bp(単位名なし。pnl_bp) | 一致 |
| 243 | −30.50 | move_bp | base/diag_paths.md:12 | −30.50 | bp(値動き) | 一致 |
| 243 | −6006000 | 円 | base/diag_paths.md:13 | −300300(×20 = −6006000) | bp(単位名なし。pnl_bp) | 一致 |
| 243 | −32.38 | move_bp | base/diag_paths.md:13 | −32.38 | bp(値動き) | 一致 |
| 243 | −0.34 | move_bp | base/diag_paths.md:22 | −0.34 | bp(値動き) | 一致 |
| 243 | −0.45 | move_bp | base/diag_paths.md:22 | −0.45 | bp(値動き) | 一致 |
| 243 | −0.22 | move_bp | base/diag_paths.md:22 | −0.22 | bp(値動き) | 一致 |
| 243 | −0.66 | move_bp | base/diag_paths.md:23 | −0.66 | bp(値動き) | 一致 |
| 243 | −0.89 | move_bp | base/diag_paths.md:23 | −0.89 | bp(値動き) | 一致 |
| 243 | −0.43 | move_bp | base/diag_paths.md:23 | −0.43 | bp(値動き) | 一致 |
| 244 | +8250920 | 円 | levels_7/diag_paths.md:11 | +412546(×20 = 8250920) | bp(単位名なし。pnl_bp) | 一致 |
| 244 | −3716960 | 円 | levels_7/diag_paths.md:12 | −185848(×20 = −3716960) | bp(単位名なし。pnl_bp) | 一致 |
| 244 | −30.10 | move_bp | levels_7/diag_paths.md:12 | −30.10 | bp(値動き) | 一致 |
| 244 | −4753360 | 円 | levels_7/diag_paths.md:13 | −237668(×20 = −4753360) | bp(単位名なし。pnl_bp) | 一致 |
| 244 | −32.13 | move_bp | levels_7/diag_paths.md:13 | −32.13 | bp(値動き) | 一致 |
| 244 | −0.34 | move_bp | levels_7/diag_paths.md:22 | −0.34 | bp(値動き) | 一致 |
| 244 | −0.45 | move_bp | levels_7/diag_paths.md:22 | −0.45 | bp(値動き) | 一致 |
| 244 | −0.22 | move_bp | levels_7/diag_paths.md:22 | −0.22 | bp(値動き) | 一致 |
| 244 | −0.64 | move_bp | levels_7/diag_paths.md:23 | −0.64 | bp(値動き) | 一致 |
| 244 | −0.88 | move_bp | levels_7/diag_paths.md:23 | −0.88 | bp(値動き) | 一致 |
| 244 | −0.42 | move_bp | levels_7/diag_paths.md:23 | −0.42 | bp(値動き) | 一致 |
| 268 | −0.26 | move_bp | levels_1/diag_paths.md:41 | −0.26 | bp(値動き) | 一致 |
| 268 | −0.31 | move_bp | levels_1/diag_paths.md:41 | −0.31 | bp(値動き) | 一致 |
| 268 | −0.20 | move_bp | levels_1/diag_paths.md:41 | −0.20 | bp(値動き) | 一致 |
| 268 | −0.51 | move_bp | levels_1/diag_paths.md:42 | −0.51 | bp(値動き) | 一致 |
| 268 | −0.62 | move_bp | levels_1/diag_paths.md:42 | −0.62 | bp(値動き) | 一致 |
| 268 | −0.38 | move_bp | levels_1/diag_paths.md:42 | −0.38 | bp(値動き) | 一致 |
| 268 | −0.75 | move_bp | levels_1/diag_paths.md:43 | −0.75 | bp(値動き) | 一致 |
| 268 | −0.99 | move_bp | levels_1/diag_paths.md:43 | −0.99 | bp(値動き) | 一致 |
| 268 | −0.52 | move_bp | levels_1/diag_paths.md:43 | −0.52 | bp(値動き) | 一致 |
| 268 | −0.55 | move_bp | levels_1/diag_paths.md:44 | −0.55 | bp(値動き) | 一致 |
| 268 | −1.05 | move_bp | levels_1/diag_paths.md:44 | −1.05 | bp(値動き) | 一致 |
| 268 | −0.11 | move_bp | levels_1/diag_paths.md:44 | −0.11 | bp(値動き) | 一致 |
| 268 | +0.44 | move_bp | levels_1/diag_paths.md:44 | +0.44 | bp(値動き) | 一致 |
| 268 | −0.06 | move_bp | levels_1/diag_paths.md:44 | −0.06 | bp(値動き) | 一致 |
| 268 | +0.94 | move_bp | levels_1/diag_paths.md:44 | +0.94 | bp(値動き) | 一致 |
| 269 | −0.26 | move_bp | levels_3/diag_paths.md:41 | −0.26 | bp(値動き) | 一致 |
| 269 | −0.31 | move_bp | levels_3/diag_paths.md:41 | −0.31 | bp(値動き) | 一致 |
| 269 | −0.20 | move_bp | levels_3/diag_paths.md:41 | −0.20 | bp(値動き) | 一致 |
| 269 | −0.51 | move_bp | levels_3/diag_paths.md:42 | −0.51 | bp(値動き) | 一致 |
| 269 | −0.63 | move_bp | levels_3/diag_paths.md:42 | −0.63 | bp(値動き) | 一致 |
| 269 | −0.38 | move_bp | levels_3/diag_paths.md:42 | −0.38 | bp(値動き) | 一致 |
| 269 | −0.76 | move_bp | levels_3/diag_paths.md:43 | −0.76 | bp(値動き) | 一致 |
| 269 | −0.99 | move_bp | levels_3/diag_paths.md:43 | −0.99 | bp(値動き) | 一致 |
| 269 | −0.53 | move_bp | levels_3/diag_paths.md:43 | −0.53 | bp(値動き) | 一致 |
| 269 | −0.57 | move_bp | levels_3/diag_paths.md:44 | −0.57 | bp(値動き) | 一致 |
| 269 | −1.09 | move_bp | levels_3/diag_paths.md:44 | −1.09 | bp(値動き) | 一致 |
| 269 | −0.13 | move_bp | levels_3/diag_paths.md:44 | −0.13 | bp(値動き) | 一致 |
| 269 | +0.55 | move_bp | levels_3/diag_paths.md:44 | +0.55 | bp(値動き) | 一致 |
| 269 | +0.04 | move_bp | levels_3/diag_paths.md:44 | +0.04 | bp(値動き) | 一致 |
| 269 | +1.06 | move_bp | levels_3/diag_paths.md:44 | +1.06 | bp(値動き) | 一致 |
| 270 | −0.25 | move_bp | base/diag_paths.md:41 | −0.25 | bp(値動き) | 一致 |
| 270 | −0.31 | move_bp | base/diag_paths.md:41 | −0.31 | bp(値動き) | 一致 |
| 270 | −0.20 | move_bp | base/diag_paths.md:41 | −0.20 | bp(値動き) | 一致 |
| 270 | −0.51 | move_bp | base/diag_paths.md:42 | −0.51 | bp(値動き) | 一致 |
| 270 | −0.63 | move_bp | base/diag_paths.md:42 | −0.63 | bp(値動き) | 一致 |
| 270 | −0.38 | move_bp | base/diag_paths.md:42 | −0.38 | bp(値動き) | 一致 |
| 270 | −0.74 | move_bp | base/diag_paths.md:43 | −0.74 | bp(値動き) | 一致 |
| 270 | −0.98 | move_bp | base/diag_paths.md:43 | −0.98 | bp(値動き) | 一致 |
| 270 | −0.52 | move_bp | base/diag_paths.md:43 | −0.52 | bp(値動き) | 一致 |
| 270 | −0.58 | move_bp | base/diag_paths.md:44 | −0.58 | bp(値動き) | 一致 |
| 270 | −1.10 | move_bp | base/diag_paths.md:44 | −1.10 | bp(値動き) | 一致 |
| 270 | −0.13 | move_bp | base/diag_paths.md:44 | −0.13 | bp(値動き) | 一致 |
| 270 | +0.53 | move_bp | base/diag_paths.md:44 | +0.53 | bp(値動き) | 一致 |
| 270 | +0.03 | move_bp | base/diag_paths.md:44 | +0.03 | bp(値動き) | 一致 |
| 270 | +1.03 | move_bp | base/diag_paths.md:44 | +1.03 | bp(値動き) | 一致 |
| 271 | −0.25 | move_bp | levels_7/diag_paths.md:41 | −0.25 | bp(値動き) | 一致 |
| 271 | −0.31 | move_bp | levels_7/diag_paths.md:41 | −0.31 | bp(値動き) | 一致 |
| 271 | −0.20 | move_bp | levels_7/diag_paths.md:41 | −0.20 | bp(値動き) | 一致 |
| 271 | −0.50 | move_bp | levels_7/diag_paths.md:42 | −0.50 | bp(値動き) | 一致 |
| 271 | −0.62 | move_bp | levels_7/diag_paths.md:42 | −0.62 | bp(値動き) | 一致 |
| 271 | −0.37 | move_bp | levels_7/diag_paths.md:42 | −0.37 | bp(値動き) | 一致 |
| 271 | −0.73 | move_bp | levels_7/diag_paths.md:43 | −0.73 | bp(値動き) | 一致 |
| 271 | −0.96 | move_bp | levels_7/diag_paths.md:43 | −0.96 | bp(値動き) | 一致 |
| 271 | −0.50 | move_bp | levels_7/diag_paths.md:43 | −0.50 | bp(値動き) | 一致 |
| 271 | −0.57 | move_bp | levels_7/diag_paths.md:44 | −0.57 | bp(値動き) | 一致 |
| 271 | −1.09 | move_bp | levels_7/diag_paths.md:44 | −1.09 | bp(値動き) | 一致 |
| 271 | −0.13 | move_bp | levels_7/diag_paths.md:44 | −0.13 | bp(値動き) | 一致 |
| 271 | +0.52 | move_bp | levels_7/diag_paths.md:44 | +0.52 | bp(値動き) | 一致 |
| 271 | +0.01 | move_bp | levels_7/diag_paths.md:44 | +0.01 | bp(値動き) | 一致 |
| 271 | +1.02 | move_bp | levels_7/diag_paths.md:44 | +1.02 | bp(値動き) | 一致 |
| 292 | +0.12 | bp/取引 | levels_1/diag_tables.md:76 | +0.12 | bp/取引 | 一致 |
| 292 | +0.02 | bp/取引 | levels_1/diag_tables.md:76 | +0.02 | bp/取引 | 一致 |
| 292 | +0.20 | bp/取引 | levels_1/diag_tables.md:76 | +0.20 | bp/取引 | 一致 |
| 292 | +0.13 | bp/取引 | levels_3/diag_tables.md:76 | +0.13 | bp/取引 | 一致 |
| 292 | +0.07 | bp/取引 | levels_3/diag_tables.md:76 | +0.07 | bp/取引 | 一致 |
| 292 | +0.19 | bp/取引 | levels_3/diag_tables.md:76 | +0.19 | bp/取引 | 一致 |
| 292 | +0.12 | bp/取引 | base/diag_tables.md:76 | +0.12 | bp/取引 | 一致 |
| 292 | +0.07 | bp/取引 | base/diag_tables.md:76 | +0.07 | bp/取引 | 一致 |
| 292 | +0.17 | bp/取引 | base/diag_tables.md:76 | +0.17 | bp/取引 | 一致 |
| 292 | +0.10 | bp/取引 | levels_7/diag_tables.md:76 | +0.10 | bp/取引 | 一致 |
| 292 | +0.06 | bp/取引 | levels_7/diag_tables.md:76 | +0.06 | bp/取引 | 一致 |
| 292 | +0.14 | bp/取引 | levels_7/diag_tables.md:76 | +0.14 | bp/取引 | 一致 |
| 293 | −0.30 | bp/取引 | levels_1/diag_tables.md:73 | −0.30 | bp/取引 | 一致 |
| 293 | −0.43 | bp/取引 | levels_1/diag_tables.md:73 | −0.43 | bp/取引 | 一致 |
| 293 | −0.17 | bp/取引 | levels_1/diag_tables.md:73 | −0.17 | bp/取引 | 一致 |
| 293 | −0.07 | bp/取引 | levels_3/diag_tables.md:73 | −0.07 | bp/取引 | 一致 |
| 293 | −0.17 | bp/取引 | levels_3/diag_tables.md:73 | −0.17 | bp/取引 | 一致 |
| 293 | +0.02 | bp/取引 | levels_3/diag_tables.md:73 | +0.02 | bp/取引 | 一致 |
| 293 | −0.00 | bp/取引 | base/diag_tables.md:73 | −0.00 | bp/取引 | 一致 |
| 293 | −0.08 | bp/取引 | base/diag_tables.md:73 | −0.08 | bp/取引 | 一致 |
| 293 | +0.07 | bp/取引 | base/diag_tables.md:73 | +0.07 | bp/取引 | 一致 |
| 293 | +0.02 | bp/取引 | levels_7/diag_tables.md:73 | +0.02 | bp/取引 | 一致 |
| 293 | −0.05 | bp/取引 | levels_7/diag_tables.md:73 | −0.05 | bp/取引 | 一致 |
| 293 | +0.08 | bp/取引 | levels_7/diag_tables.md:73 | +0.08 | bp/取引 | 一致 |
| 294 | −0.51 | bp/取引 | levels_1/diag_tables.md:75 | −0.51 | bp/取引 | 一致 |
| 294 | −0.62 | bp/取引 | levels_1/diag_tables.md:75 | −0.62 | bp/取引 | 一致 |
| 294 | −0.40 | bp/取引 | levels_1/diag_tables.md:75 | −0.40 | bp/取引 | 一致 |
| 294 | −0.19 | bp/取引 | levels_3/diag_tables.md:75 | −0.19 | bp/取引 | 一致 |
| 294 | −0.27 | bp/取引 | levels_3/diag_tables.md:75 | −0.27 | bp/取引 | 一致 |
| 294 | −0.11 | bp/取引 | levels_3/diag_tables.md:75 | −0.11 | bp/取引 | 一致 |
| 294 | −0.10 | bp/取引 | base/diag_tables.md:75 | −0.10 | bp/取引 | 一致 |
| 294 | −0.16 | bp/取引 | base/diag_tables.md:75 | −0.16 | bp/取引 | 一致 |
| 294 | −0.04 | bp/取引 | base/diag_tables.md:75 | −0.04 | bp/取引 | 一致 |
| 294 | −0.04 | bp/取引 | levels_7/diag_tables.md:75 | −0.04 | bp/取引 | 一致 |
| 294 | −0.09 | bp/取引 | levels_7/diag_tables.md:75 | −0.09 | bp/取引 | 一致 |
| 294 | +0.01 | bp/取引 | levels_7/diag_tables.md:75 | +0.01 | bp/取引 | 一致 |
| 295 | −0.38 | bp/取引 | levels_1/diag_tables.md:74 | −0.38 | bp/取引 | 一致 |
| 295 | −0.51 | bp/取引 | levels_1/diag_tables.md:74 | −0.51 | bp/取引 | 一致 |
| 295 | −0.27 | bp/取引 | levels_1/diag_tables.md:74 | −0.27 | bp/取引 | 一致 |
| 295 | −0.09 | bp/取引 | levels_3/diag_tables.md:74 | −0.09 | bp/取引 | 一致 |
| 295 | −0.18 | bp/取引 | levels_3/diag_tables.md:74 | −0.18 | bp/取引 | 一致 |
| 295 | −0.00 | bp/取引 | levels_3/diag_tables.md:74 | −0.00 | bp/取引 | 一致 |
| 295 | −0.01 | bp/取引 | base/diag_tables.md:74 | −0.01 | bp/取引 | 一致 |
| 295 | −0.09 | bp/取引 | base/diag_tables.md:74 | −0.09 | bp/取引 | 一致 |
| 295 | +0.06 | bp/取引 | base/diag_tables.md:74 | +0.06 | bp/取引 | 一致 |
| 295 | −0.01 | bp/取引 | levels_7/diag_tables.md:74 | −0.01 | bp/取引 | 一致 |
| 295 | −0.07 | bp/取引 | levels_7/diag_tables.md:74 | −0.07 | bp/取引 | 一致 |
| 295 | +0.06 | bp/取引 | levels_7/diag_tables.md:74 | +0.06 | bp/取引 | 一致 |
| 297 | +0.10 | bp/取引 | levels_7/diag_tables.md:76 | +0.10 | bp/取引 | 一致 |
| 297 | +0.13 | bp/取引 | levels_3/diag_tables.md:76 | +0.13 | bp/取引 | 一致 |
| 297 | +2.0 | 円/取引 | levels_7/diag_tables.md:76 | +0.10(×20 = 2.0) | bp/取引 | 一致 |
| 297 | +2.6 | 円/取引 | levels_3/diag_tables.md:76 | +0.13(×20 = 2.6) | bp/取引 | 一致 |
| 318 | −26.95 | bp/日 | levels_1/diag_tables.md:82 | −26.95 | bp/日 | 一致 |
| 318 | −31.52 | bp/日 | levels_1/diag_tables.md:82 | −31.52 | bp/日 | 一致 |
| 318 | −21.88 | bp/日 | levels_1/diag_tables.md:82 | −21.88 | bp/日 | 一致 |
| 318 | −539 | 円/日 | levels_1/diag_tables.md:82 | −26.95(×20 = −539) | bp/日 | 一致 |
| 318 | −5.38 | bp/日 | levels_3/diag_tables.md:82 | −5.38 | bp/日 | 一致 |
| 318 | −7.01 | bp/日 | levels_3/diag_tables.md:82 | −7.01 | bp/日 | 一致 |
| 318 | −3.80 | bp/日 | levels_3/diag_tables.md:82 | −3.80 | bp/日 | 一致 |
| 318 | −108 | 円/日 | levels_3/diag_tables.md:82 | −5.38(×20 = −108) | bp/日 | 一致 |
| 318 | +1.64 | bp/日 | levels_7/diag_tables.md:82 | +1.64 | bp/日 | 一致 |
| 318 | +0.66 | bp/日 | levels_7/diag_tables.md:82 | +0.66 | bp/日 | 一致 |
| 318 | +2.65 | bp/日 | levels_7/diag_tables.md:82 | +2.65 | bp/日 | 一致 |
| 318 | +33 | 円/日 | levels_7/diag_tables.md:82 | +1.64(×20 = 33) | bp/日 | 一致 |
| 319 | +93.86 | bp/日 | levels_1/diag_tables.md:83 | +93.86 | bp/日 | 一致 |
| 319 | +5.04 | bp/日 | levels_1/diag_tables.md:83 | +5.04 | bp/日 | 一致 |
| 319 | +239.03 | bp/日 | levels_1/diag_tables.md:83 | +239.03 | bp/日 | 一致 |
| 319 | +13.91 | bp/日 | levels_3/diag_tables.md:83 | +13.91 | bp/日 | 一致 |
| 319 | −4.54 | bp/日 | levels_3/diag_tables.md:83 | −4.54 | bp/日 | 一致 |
| 319 | +41.98 | bp/日 | levels_3/diag_tables.md:83 | +41.98 | bp/日 | 一致 |
| 319 | −3.66 | bp/日 | levels_7/diag_tables.md:83 | −3.66 | bp/日 | 一致 |
| 319 | −19.71 | bp/日 | levels_7/diag_tables.md:83 | −19.71 | bp/日 | 一致 |
| 319 | +6.97 | bp/日 | levels_7/diag_tables.md:83 | +6.97 | bp/日 | 一致 |
| 320 | +36.20 | bp/日 | levels_1/diag_tables.md:84 | +36.20 | bp/日 | 一致 |
| 320 | +23.75 | bp/日 | levels_1/diag_tables.md:84 | +23.75 | bp/日 | 一致 |
| 320 | +50.94 | bp/日 | levels_1/diag_tables.md:84 | +50.94 | bp/日 | 一致 |
| 320 | +8.37 | bp/日 | levels_3/diag_tables.md:84 | +8.37 | bp/日 | 一致 |
| 320 | +4.21 | bp/日 | levels_3/diag_tables.md:84 | +4.21 | bp/日 | 一致 |
| 320 | +12.66 | bp/日 | levels_3/diag_tables.md:84 | +12.66 | bp/日 | 一致 |
| 320 | −3.45 | bp/日 | levels_7/diag_tables.md:84 | −3.45 | bp/日 | 一致 |
| 320 | −6.14 | bp/日 | levels_7/diag_tables.md:84 | −6.14 | bp/日 | 一致 |
| 320 | −0.86 | bp/日 | levels_7/diag_tables.md:84 | −0.86 | bp/日 | 一致 |
| 321 | −14.49 | bp/日 | levels_1/diag_tables.md:85 | −14.49 | bp/日 | 一致 |
| 321 | −32.45 | bp/日 | levels_1/diag_tables.md:85 | −32.45 | bp/日 | 一致 |
| 321 | +0.82 | bp/日 | levels_1/diag_tables.md:85 | +0.82 | bp/日 | 一致 |
| 321 | −2.48 | bp/日 | levels_3/diag_tables.md:85 | −2.48 | bp/日 | 一致 |
| 321 | −9.31 | bp/日 | levels_3/diag_tables.md:85 | −9.31 | bp/日 | 一致 |
| 321 | +3.92 | bp/日 | levels_3/diag_tables.md:85 | +3.92 | bp/日 | 一致 |
| 321 | +0.02 | bp/日 | levels_7/diag_tables.md:85 | +0.02 | bp/日 | 一致 |
| 321 | −3.85 | bp/日 | levels_7/diag_tables.md:85 | −3.85 | bp/日 | 一致 |
| 321 | +4.35 | bp/日 | levels_7/diag_tables.md:85 | +4.35 | bp/日 | 一致 |
| 322 | −40.59 | bp/日 | levels_1/diag_tables.md:86 | −40.59 | bp/日 | 一致 |
| 322 | −56.17 | bp/日 | levels_1/diag_tables.md:86 | −56.17 | bp/日 | 一致 |
| 322 | −27.37 | bp/日 | levels_1/diag_tables.md:86 | −27.37 | bp/日 | 一致 |
| 322 | −5.12 | bp/日 | levels_3/diag_tables.md:86 | −5.12 | bp/日 | 一致 |
| 322 | −9.70 | bp/日 | levels_3/diag_tables.md:86 | −9.70 | bp/日 | 一致 |
| 322 | −0.53 | bp/日 | levels_3/diag_tables.md:86 | −0.53 | bp/日 | 一致 |
| 322 | −1.97 | bp/日 | levels_7/diag_tables.md:86 | −1.97 | bp/日 | 一致 |
| 322 | −4.51 | bp/日 | levels_7/diag_tables.md:86 | −4.51 | bp/日 | 一致 |
| 322 | +0.86 | bp/日 | levels_7/diag_tables.md:86 | +0.86 | bp/日 | 一致 |
| 323 | −34.43 | bp/日 | levels_1/diag_tables.md:87 | −34.43 | bp/日 | 一致 |
| 323 | −42.36 | bp/日 | levels_1/diag_tables.md:87 | −42.36 | bp/日 | 一致 |
| 323 | −26.77 | bp/日 | levels_1/diag_tables.md:87 | −26.77 | bp/日 | 一致 |
| 323 | −5.10 | bp/日 | levels_3/diag_tables.md:87 | −5.10 | bp/日 | 一致 |
| 323 | −8.60 | bp/日 | levels_3/diag_tables.md:87 | −8.60 | bp/日 | 一致 |
| 323 | −2.02 | bp/日 | levels_3/diag_tables.md:87 | −2.02 | bp/日 | 一致 |
| 323 | −0.28 | bp/日 | levels_7/diag_tables.md:87 | −0.28 | bp/日 | 一致 |
| 323 | −2.41 | bp/日 | levels_7/diag_tables.md:87 | −2.41 | bp/日 | 一致 |
| 323 | +1.81 | bp/日 | levels_7/diag_tables.md:87 | +1.81 | bp/日 | 一致 |
| 324 | −36.90 | bp/日 | levels_1/diag_tables.md:88 | −36.90 | bp/日 | 一致 |
| 324 | −44.14 | bp/日 | levels_1/diag_tables.md:88 | −44.14 | bp/日 | 一致 |
| 324 | −29.88 | bp/日 | levels_1/diag_tables.md:88 | −29.88 | bp/日 | 一致 |
| 324 | −6.16 | bp/日 | levels_3/diag_tables.md:88 | −6.16 | bp/日 | 一致 |
| 324 | −8.76 | bp/日 | levels_3/diag_tables.md:88 | −8.76 | bp/日 | 一致 |
| 324 | −3.78 | bp/日 | levels_3/diag_tables.md:88 | −3.78 | bp/日 | 一致 |
| 324 | +1.48 | bp/日 | levels_7/diag_tables.md:88 | +1.48 | bp/日 | 一致 |
| 324 | −0.89 | bp/日 | levels_7/diag_tables.md:88 | −0.89 | bp/日 | 一致 |
| 324 | +3.81 | bp/日 | levels_7/diag_tables.md:88 | +3.81 | bp/日 | 一致 |
| 325 | −62.00 | bp/日 | levels_1/diag_tables.md:89 | −62.00 | bp/日 | 一致 |
| 325 | −75.79 | bp/日 | levels_1/diag_tables.md:89 | −75.79 | bp/日 | 一致 |
| 325 | −49.73 | bp/日 | levels_1/diag_tables.md:89 | −49.73 | bp/日 | 一致 |
| 325 | −14.36 | bp/日 | levels_3/diag_tables.md:89 | −14.36 | bp/日 | 一致 |
| 325 | −19.44 | bp/日 | levels_3/diag_tables.md:89 | −19.44 | bp/日 | 一致 |
| 325 | −9.58 | bp/日 | levels_3/diag_tables.md:89 | −9.58 | bp/日 | 一致 |
| 325 | +5.60 | bp/日 | levels_7/diag_tables.md:89 | +5.60 | bp/日 | 一致 |
| 325 | +2.43 | bp/日 | levels_7/diag_tables.md:89 | +2.43 | bp/日 | 一致 |
| 325 | +9.03 | bp/日 | levels_7/diag_tables.md:89 | +9.03 | bp/日 | 一致 |
| 326 | −43.82 | bp/日 | levels_1/diag_tables.md:90 | −43.82 | bp/日 | 一致 |
| 326 | −53.58 | bp/日 | levels_1/diag_tables.md:90 | −53.58 | bp/日 | 一致 |
| 326 | −34.97 | bp/日 | levels_1/diag_tables.md:90 | −34.97 | bp/日 | 一致 |
| 326 | −9.72 | bp/日 | levels_3/diag_tables.md:90 | −9.72 | bp/日 | 一致 |
| 326 | −13.67 | bp/日 | levels_3/diag_tables.md:90 | −13.67 | bp/日 | 一致 |
| 326 | −6.46 | bp/日 | levels_3/diag_tables.md:90 | −6.46 | bp/日 | 一致 |
| 326 | +6.22 | bp/日 | levels_7/diag_tables.md:90 | +6.22 | bp/日 | 一致 |
| 326 | +3.90 | bp/日 | levels_7/diag_tables.md:90 | +3.90 | bp/日 | 一致 |
| 326 | +8.94 | bp/日 | levels_7/diag_tables.md:90 | +8.94 | bp/日 | 一致 |
| 327 | −30.07 | bp/日 | levels_1/diag_tables.md:91 | −30.07 | bp/日 | 一致 |
| 327 | −36.15 | bp/日 | levels_1/diag_tables.md:91 | −36.15 | bp/日 | 一致 |
| 327 | −23.97 | bp/日 | levels_1/diag_tables.md:91 | −23.97 | bp/日 | 一致 |
| 327 | −10.37 | bp/日 | levels_3/diag_tables.md:91 | −10.37 | bp/日 | 一致 |
| 327 | −13.15 | bp/日 | levels_3/diag_tables.md:91 | −13.15 | bp/日 | 一致 |
| 327 | −7.68 | bp/日 | levels_3/diag_tables.md:91 | −7.68 | bp/日 | 一致 |
| 327 | +6.14 | bp/日 | levels_7/diag_tables.md:91 | +6.14 | bp/日 | 一致 |
| 327 | +4.15 | bp/日 | levels_7/diag_tables.md:91 | +4.15 | bp/日 | 一致 |
| 327 | +8.03 | bp/日 | levels_7/diag_tables.md:91 | +8.03 | bp/日 | 一致 |
| 328 | 7.02 | bp/日(MDE) | levels_1/diag_tables.md:82 | +7.02 | bp/日(MDE) | 一致 |
| 328 | 2.30 | bp/日(MDE) | levels_3/diag_tables.md:82 | +2.30 | bp/日(MDE) | 一致 |
| 328 | 1.50 | bp/日(MDE) | levels_7/diag_tables.md:82 | +1.50 | bp/日(MDE) | 一致 |
| 330 | −79,594 | bp | levels_1/diag_tables.md:93 | −79594 | bp | 一致 |
| 330 | −14,683 | bp | levels_3/diag_tables.md:93 | −14683 | bp | 一致 |
| 330 | +4,220 | bp | levels_7/diag_tables.md:93 | +4220 | bp | 一致 |
| 332 | −539 | 円/日 | levels_1/diag_tables.md:82 | −26.95(×20 = −539) | bp/日 | 一致 |
| 382 | −539 | 円/日 | levels_1/diag_tables.md:82 | −26.95(×20 = −539) | bp/日 | 一致 |
| 332 | −108 | 円/日 | levels_3/diag_tables.md:82 | −5.38(×20 = −108) | bp/日 | 一致 |
| 382 | −108 | 円/日 | levels_3/diag_tables.md:82 | −5.38(×20 = −108) | bp/日 | 一致 |
| 332 | +33 | 円/日 | levels_7/diag_tables.md:82 | +1.64(×20 = 33) | bp/日 | 一致 |
| 382 | +33 | 円/日 | levels_7/diag_tables.md:82 | +1.64(×20 = 33) | bp/日 | 一致 |
| 332 | +36.20 | bp/日 | levels_1/diag_tables.md:84 | +36.20 | bp/日 | 一致 |
| 352 | −4,069,614 | 円 | levels/compare.md:8 | −4069614 | 円(pnl_jpy) | 一致 |
| 352 | −4,239,080 | 円 | levels/compare.md:17 | −4239080 | 円(pnl_jpy) | 一致 |
| 352 | −2,978,976 | 円 | levels/compare.md:9 | −2978976 | 円(pnl_jpy) | 一致 |
| 352 | −2,844,418 | 円 | levels/compare.md:18 | −2844418 | 円(pnl_jpy) | 一致 |
| 384 | +145 | 円/日 | levels_1/diag_tables.md:35 | +7.23(×20 = 145) | bp/日 | 一致 |
| 384 | −1,133 | 円/日 | levels_1/diag_tables.md:36 | −56.63(×20 = −1133) | bp/日 | 一致 |
| 390 | −394,294 | 円 | levels/levels_extra.out:2 | −394294 | 円(pnl_jpy) | 一致 |
| 390 | −748,785 | 円 | levels/levels_extra.out:3 | −748785 | 円(pnl_jpy) | 一致 |
| 390 | −17,001 | 円 | levels/levels_extra.out:11 | −17001 | 円(pnl_jpy) | 一致 |
| 390 | −163,478 | 円 | levels/levels_extra.out:12 | −163478 | 円(pnl_jpy) | 一致 |
| 416 | +145 | 円/日 | levels_1/diag_tables.md:35 | +7.23(×20 = 145) | bp/日 | 一致 |
| 416 | −93 | 円/日 | levels_1/diag_tables.md:35 | −4.65(×20 = −93) | bp/日 | 一致 |
| 416 | +395 | 円/日 | levels_1/diag_tables.md:35 | +19.77(×20 = 395) | bp/日 | 一致 |
| 416 | −1133 | 円/日 | levels_1/diag_tables.md:36 | −56.63(×20 = −1133) | bp/日 | 一致 |
| 416 | −1278 | 円/日 | levels_1/diag_tables.md:36 | −63.90(×20 = −1278) | bp/日 | 一致 |
| 416 | −984 | 円/日 | levels_1/diag_tables.md:36 | −49.18(×20 = −984) | bp/日 | 一致 |
| 417 | +348 | 円/日 | levels_3/diag_tables.md:35 | +17.38(×20 = 348) | bp/日 | 一致 |
| 417 | +181 | 円/日 | levels_3/diag_tables.md:35 | +9.05(×20 = 181) | bp/日 | 一致 |
| 417 | +514 | 円/日 | levels_3/diag_tables.md:35 | +25.68(×20 = 514) | bp/日 | 一致 |
| 417 | −473 | 円/日 | levels_3/diag_tables.md:36 | −23.66(×20 = −473) | bp/日 | 一致 |
| 417 | −589 | 円/日 | levels_3/diag_tables.md:36 | −29.46(×20 = −589) | bp/日 | 一致 |
| 417 | −364 | 円/日 | levels_3/diag_tables.md:36 | −18.18(×20 = −364) | bp/日 | 一致 |
| 418 | +362 | 円/日 | base/diag_tables.md:35 | +18.11(×20 = 362) | bp/日 | 一致 |
| 418 | +231 | 円/日 | base/diag_tables.md:35 | +11.55(×20 = 231) | bp/日 | 一致 |
| 418 | +497 | 円/日 | base/diag_tables.md:35 | +24.86(×20 = 497) | bp/日 | 一致 |
| 418 | −273 | 円/日 | base/diag_tables.md:36 | −13.63(×20 = −273) | bp/日 | 一致 |
| 418 | −360 | 円/日 | base/diag_tables.md:36 | −18.00(×20 = −360) | bp/日 | 一致 |
| 418 | −184 | 円/日 | base/diag_tables.md:36 | −9.19(×20 = −184) | bp/日 | 一致 |
| 419 | +333 | 円/日 | levels_7/diag_tables.md:35 | +16.64(×20 = 333) | bp/日 | 一致 |
| 419 | +224 | 円/日 | levels_7/diag_tables.md:35 | +11.18(×20 = 224) | bp/日 | 一致 |
| 419 | +448 | 円/日 | levels_7/diag_tables.md:35 | +22.42(×20 = 448) | bp/日 | 一致 |
| 419 | −178 | 円/日 | levels_7/diag_tables.md:36 | −8.88(×20 = −178) | bp/日 | 一致 |
| 419 | −250 | 円/日 | levels_7/diag_tables.md:36 | −12.51(×20 = −250) | bp/日 | 一致 |
| 419 | −106 | 円/日 | levels_7/diag_tables.md:36 | −5.30(×20 = −106) | bp/日 | 一致 |
| 434 | −539 | 円/日 | levels_1/diag_tables.md:82 | −26.95(×20 = −539) | bp/日 | 一致 |
| 434 | −630 | 円/日 | levels_1/diag_tables.md:82 | −31.52(×20 = −630) | bp/日 | 一致 |
| 434 | −438 | 円/日 | levels_1/diag_tables.md:82 | −21.88(×20 = −438) | bp/日 | 一致 |
| 434 | −218 | 円/日 | half_diff.out:6 | −218 | 円/日(pnl_bp × 20) | 一致 |
| 434 | −382 | 円/日 | half_diff.out:6 | −382 | 円/日(pnl_bp × 20) | 一致 |
| 434 | −53 | 円/日 | half_diff.out:6 | −53 | 円/日(pnl_bp × 20) | 一致 |
| 434 | −860 | 円/日 | half_diff.out:6 | −860 | 円/日(pnl_bp × 20) | 一致 |
| 434 | −953 | 円/日 | half_diff.out:6 | −953 | 円/日(pnl_bp × 20) | 一致 |
| 434 | −773 | 円/日 | half_diff.out:6 | −773 | 円/日(pnl_bp × 20) | 一致 |
| 434 | +724 | 円/日 | levels_1/diag_tables.md:84 | +36.20(×20 = 724) | bp/日 | 一致 |
| 434 | −812 | 円/日 | levels_1/diag_tables.md:86 | −40.59(×20 = −812) | bp/日 | 一致 |
| 434 | −738 | 円/日 | levels_1/diag_tables.md:88 | −36.90(×20 = −738) | bp/日 | 一致 |
| 434 | −876 | 円/日 | levels_1/diag_tables.md:90 | −43.82(×20 = −876) | bp/日 | 一致 |
| 434 | −601 | 円/日 | levels_1/diag_tables.md:91 | −30.07(×20 = −601) | bp/日 | 一致 |
| 435 | −108 | 円/日 | levels_3/diag_tables.md:82 | −5.38(×20 = −108) | bp/日 | 一致 |
| 435 | −140 | 円/日 | levels_3/diag_tables.md:82 | −7.01(×20 = −140) | bp/日 | 一致 |
| 435 | −76 | 円/日 | levels_3/diag_tables.md:82 | −3.80(×20 = −76) | bp/日 | 一致 |
| 435 | −15 | 円/日 | half_diff.out:7 | −15 | 円/日(pnl_bp × 20) | 一致 |
| 435 | −67 | 円/日 | half_diff.out:7 | −67 | 円/日(pnl_bp × 20) | 一致 |
| 435 | +37 | 円/日 | half_diff.out:7 | +37 | 円/日(pnl_bp × 20) | 一致 |
| 435 | −201 | 円/日 | half_diff.out:7 | −201 | 円/日(pnl_bp × 20) | 一致 |
| 435 | −237 | 円/日 | half_diff.out:7 | −237 | 円/日(pnl_bp × 20) | 一致 |
| 435 | −166 | 円/日 | half_diff.out:7 | −166 | 円/日(pnl_bp × 20) | 一致 |
| 435 | +167 | 円/日 | levels_3/diag_tables.md:84 | +8.37(×20 = 167) | bp/日 | 一致 |
| 435 | −102 | 円/日 | levels_3/diag_tables.md:86 | −5.12(×20 = −102) | bp/日 | 一致 |
| 435 | −123 | 円/日 | levels_3/diag_tables.md:88 | −6.16(×20 = −123) | bp/日 | 一致 |
| 435 | −194 | 円/日 | levels_3/diag_tables.md:90 | −9.72(×20 = −194) | bp/日 | 一致 |
| 435 | −207 | 円/日 | levels_3/diag_tables.md:91 | −10.37(×20 = −207) | bp/日 | 一致 |
| 436 | +33 | 円/日 | levels_7/diag_tables.md:82 | +1.64(×20 = 33) | bp/日 | 一致 |
| 436 | +13 | 円/日 | levels_7/diag_tables.md:82 | +0.66(×20 = 13) | bp/日 | 一致 |
| 436 | +53 | 円/日 | levels_7/diag_tables.md:82 | +2.65(×20 = 53) | bp/日 | 一致 |
| 436 | −30 | 円/日 | half_diff.out:8 | −30 | 円/日(pnl_bp × 20) | 一致 |
| 436 | −58 | 円/日 | half_diff.out:8 | −58 | 円/日(pnl_bp × 20) | 一致 |
| 436 | +2 | 円/日 | half_diff.out:8 | +2 | 円/日(pnl_bp × 20) | 一致 |
| 436 | +95 | 円/日 | half_diff.out:8 | +95 | 円/日(pnl_bp × 20) | 一致 |
| 436 | +70 | 円/日 | half_diff.out:8 | +70 | 円/日(pnl_bp × 20) | 一致 |
| 436 | +121 | 円/日 | half_diff.out:8 | +121 | 円/日(pnl_bp × 20) | 一致 |
| 436 | −69 | 円/日 | levels_7/diag_tables.md:84 | −3.45(×20 = −69) | bp/日 | 一致 |
| 436 | −39 | 円/日 | levels_7/diag_tables.md:86 | −1.97(×20 = −39) | bp/日 | 一致 |
| 436 | +30 | 円/日 | levels_7/diag_tables.md:88 | +1.48(×20 = 30) | bp/日 | 一致 |
| 436 | +124 | 円/日 | levels_7/diag_tables.md:90 | +6.22(×20 = 124) | bp/日 | 一致 |
| 436 | +123 | 円/日 | levels_7/diag_tables.md:91 | +6.14(×20 = 123) | bp/日 | 一致 |
| 438 | −860 | 円/日 | half_diff.out:6 | −860 | 円/日 | 一致 |
| 438 | −201 | 円/日 | half_diff.out:7 | −201 | 円/日 | 一致 |
| 438 | +95 | 円/日 | half_diff.out:8 | +95 | 円/日 | 一致 |
| 438 | 0 | 円/日 | (基準どうしの差。定義から 0) | — | — | 一致(基準 − 基準。数える出所は要らない) |
| 442 | −1,133 | 円/日 | levels_1/diag_tables.md:36 | −56.63(×20 = −1133) | bp/日 | 一致 |
| 442 | −178 | 円/日 | levels_7/diag_tables.md:36 | −8.88(×20 = −178) | bp/日 | 一致 |
| 442 | −539 | 円/日 | levels_1/diag_tables.md:82 | −26.95(×20 = −539) | bp/日 | 一致 |
| 442 | −108 | 円/日 | levels_3/diag_tables.md:82 | −5.38(×20 = −108) | bp/日 | 一致 |
| 442 | +33 | 円/日 | levels_7/diag_tables.md:82 | +1.64(×20 = 33) | bp/日 | 一致 |
| 442 | −860 | 円/日 | half_diff.out:6 | −860 | 円/日 | 一致 |
| 442 | −201 | 円/日 | half_diff.out:7 | −201 | 円/日 | 一致 |
| 442 | +95 | 円/日 | half_diff.out:8 | +95 | 円/日 | 一致 |
| 442 | 0 | 円/日 | (基準どうしの差。定義から 0) | — | — | 一致(基準 − 基準) |
| 442 | −218 | 円/日 | half_diff.out:6 | −218 | 円/日 | 一致 |
| 442 | +145 | 円/日 | levels_1/diag_tables.md:35 | +7.23(×20 = 145) | bp/日 | 一致 |
| 442 | −93 | 円/日 | levels_1/diag_tables.md:35 | −4.65(×20 = −93) | bp/日 | 一致 |
| 442 | +395 | 円/日 | levels_1/diag_tables.md:35 | +19.77(×20 = 395) | bp/日 | 一致 |
| 442 | +1,616 | 円/日 | same_bar_daily_4fam.out:3 | +1616 | 円/日 | 一致 |
| 442 | −1,471 | 円/日 | same_bar_daily_4fam.out:4 | −1471 | 円/日 | 一致 |
| 442 | +323 | 円/日 | 文書 214 行 +1,616 × 1 ÷ 5 | 323.2 | 円/日 | 一致 |
| 442 | +350 | 円/日 | 文書 215 行 +583 × 3 ÷ 5 | 349.8 | 円/日 | 一致 |

## 文書: `docs/ANALYSIS/2026-10-09_matilda_main_foot.md`

拾った数 343 個。判定ごと: 一致 343

数を拾った行: 31・57・69・88・116・117・119・121・122・154・155・156・179・180・181・182・184・185・186・187・210・211・212・213・216・239・240・241・242・244・264・265・266・267・288・292・293・294・295・296・297・298・299・300・301・303・309・311・327・328・330・359・361・362・363・364・365・389・390・403・407

| 文書の行 | 書かれた数 | 書かれた単位 | 出所 ファイル:行 | 出所の値 | 出所の単位 | 判定 |
|---|---|---|---|---|---|---|
| 31 | +213,546 | 円 | backtest_runs_shared/matilda_main_trades/foot_5/summary.json(check.pnl_jpy) | 213545.96 | 円 | 一致 |
| 57 | +213,545.96 | 円 | backtest_runs_shared/matilda_main_trades/foot_5/summary.json(check.pnl_jpy) | 213545.96 | 円 | 一致 |
| 69 | +155 | 円/日 | foot/foot_boundary.out:1・2 | +155 | 円/日(pnl_bp × 20) | 一致 |
| 69 | −9 | 円/日 | foot/foot_boundary.out:1・2 | −9 | 円/日(pnl_bp × 20) | 一致 |
| 69 | −99 | 円/日 | foot/foot_boundary.out:1 | −99 | 円/日 | 一致 |
| 69 | +85 | 円/日 | foot/foot_boundary.out:1 | +85 | 円/日 | 一致 |
| 69 | −106 | 円/日 | foot/foot_boundary.out:2 | −106 | 円/日 | 一致 |
| 69 | +82 | 円/日 | foot/foot_boundary.out:2 | +82 | 円/日 | 一致 |
| 88 | +213,546 | 円 | backtest_runs_shared/matilda_main_trades/foot_5/summary.json(check.pnl_jpy) | 213545.96 | 円 | 一致 |
| 88 | +527 | 円 | foot/market_side.out:1 | 527 | 円(fills の量 × 値段) | 一致 |
| 116 | +155 | 円/日 | foot_5/diag_tables.md:35 | +7.73(×20 = 155) | bp/日 | 一致 |
| 116 | +46 | 円/日 | foot_5/diag_tables.md:35 | +2.28(×20 = 46) | bp/日 | 一致 |
| 116 | +264 | 円/日 | foot_5/diag_tables.md:35 | +13.22(×20 = 264) | bp/日 | 一致 |
| 116 | −9 | 円/日 | foot_5/diag_tables.md:36 | −0.46(×20 = −9) | bp/日 | 一致 |
| 116 | −106 | 円/日 | foot_5/diag_tables.md:36 | −5.31(×20 = −106) | bp/日 | 一致 |
| 116 | +82 | 円/日 | foot_5/diag_tables.md:36 | +4.08(×20 = 82) | bp/日 | 一致 |
| 116 | −164 | 円/日 | foot_5/diag_tables.md:37 | −8.19(×20 = −164) | bp/日 | 一致 |
| 116 | −307 | 円/日 | foot_5/diag_tables.md:37 | −15.34(×20 = −307) | bp/日 | 一致 |
| 116 | −25 | 円/日 | foot_5/diag_tables.md:37 | −1.27(×20 = −25) | bp/日 | 一致 |
| 117 | +362 | 円/日 | base/diag_tables.md:35 | +18.11(×20 = 362) | bp/日 | 一致 |
| 117 | +231 | 円/日 | base/diag_tables.md:35 | +11.55(×20 = 231) | bp/日 | 一致 |
| 117 | +497 | 円/日 | base/diag_tables.md:35 | +24.86(×20 = 497) | bp/日 | 一致 |
| 117 | −273 | 円/日 | base/diag_tables.md:36 | −13.63(×20 = −273) | bp/日 | 一致 |
| 117 | −360 | 円/日 | base/diag_tables.md:36 | −18.00(×20 = −360) | bp/日 | 一致 |
| 117 | −184 | 円/日 | base/diag_tables.md:36 | −9.19(×20 = −184) | bp/日 | 一致 |
| 117 | −635 | 円/日 | base/diag_tables.md:37 | −31.75(×20 = −635) | bp/日 | 一致 |
| 117 | −805 | 円/日 | base/diag_tables.md:37 | −40.27(×20 = −805) | bp/日 | 一致 |
| 117 | −476 | 円/日 | base/diag_tables.md:37 | −23.82(×20 = −476) | bp/日 | 一致 |
| 119 | −252 | 円/日 | foot_5/diag_tables.md:21 | −12.59(×20 = −252) | bp/日 | 一致 |
| 119 | +122 | 円/日 | foot_5/diag_tables.md:22 | +6.10(×20 = 122) | bp/日 | 一致 |
| 119 | +371 | 円/日 | foot_5/diag_tables.md:23 | +18.56(×20 = 371) | bp/日 | 一致 |
| 119 | −35 | 円/日 | foot_5/diag_tables.md:24 | −1.77(×20 = −35) | bp/日 | 一致 |
| 119 | +182 | 円/日 | foot_5/diag_tables.md:25 | +9.09(×20 = 182) | bp/日 | 一致 |
| 119 | +221 | 円/日 | foot_5/diag_tables.md:26 | +11.04(×20 = 221) | bp/日 | 一致 |
| 119 | −225 | 円/日 | foot_5/diag_tables.md:27 | −11.26(×20 = −225) | bp/日 | 一致 |
| 119 | −63 | 円/日 | foot_5/diag_tables.md:28 | −3.16(×20 = −63) | bp/日 | 一致 |
| 119 | +34 | 円/日 | foot_5/diag_tables.md:29 | +1.70(×20 = 34) | bp/日 | 一致 |
| 119 | +73 | 円/日 | foot_5/diag_tables.md:20 | +3.63(×20 = 73) | bp/日 | 一致 |
| 119 | +9 | 円/日 | foot_5/diag_tables.md:20 | +0.46(×20 = 9) | bp/日 | 一致 |
| 119 | +142 | 円/日 | foot_5/diag_tables.md:20 | +7.11(×20 = 142) | bp/日 | 一致 |
| 121 | 131 | 円/日(MDE) | foot_5/diag_tables.md:36 | +6.53(×20 = 131) | bp/日(MDE) | 一致 |
| 121 | −9 | 円/日 | foot_5/diag_tables.md:36 | −0.46(×20 = −9) | bp/日 | 一致 |
| 121 | +155 | 円/日 | foot_5/diag_tables.md:35 | +7.73(×20 = 155) | bp/日 | 一致 |
| 121 | −164 | 円/日 | foot_5/diag_tables.md:37 | −8.19(×20 = −164) | bp/日 | 一致 |
| 121 | −307 | 円/日 | foot_5/diag_tables.md:37 | −15.34(×20 = −307) | bp/日 | 一致 |
| 121 | −25 | 円/日 | foot_5/diag_tables.md:37 | −1.27(×20 = −25) | bp/日 | 一致 |
| 122 | +73 | 円/日 | foot_5/diag_tables.md:20 | +3.63(×20 = 73) | bp/日 | 一致 |
| 154 | +77 | 円/日 | foot/scenes.out:5 | +77 | 円/日(pnl_jpy) | 一致 |
| 154 | −23 | 円/日 | foot/scenes.out:5 | −23 | 円/日(pnl_jpy) | 一致 |
| 154 | +180 | 円/日 | foot/scenes.out:5 | +180 | 円/日(pnl_jpy) | 一致 |
| 154 | +264 | 円/日 | scratchpad/d2_scenes.out(d2_scenes.py の再実行):3 | +264 | 円/日(pnl_jpy) | 一致 |
| 154 | +154 | 円/日 | scratchpad/d2_scenes.out(d2_scenes.py の再実行):3 | +154 | 円/日(pnl_jpy) | 一致 |
| 154 | +357 | 円/日 | scratchpad/d2_scenes.out(d2_scenes.py の再実行):3 | +357 | 円/日(pnl_jpy) | 一致 |
| 154 | −63 | 円/日 | foot/scenes.out:6 | −63 | 円/日(pnl_jpy) | 一致 |
| 154 | −144 | 円/日 | foot/scenes.out:6 | −144 | 円/日(pnl_jpy) | 一致 |
| 154 | +13 | 円/日 | foot/scenes.out:6 | +13 | 円/日(pnl_jpy) | 一致 |
| 154 | −216 | 円/日 | scratchpad/d2_scenes.out(d2_scenes.py の再実行):4 | −216 | 円/日(pnl_jpy) | 一致 |
| 154 | −307 | 円/日 | scratchpad/d2_scenes.out(d2_scenes.py の再実行):4 | −307 | 円/日(pnl_jpy) | 一致 |
| 154 | −126 | 円/日 | scratchpad/d2_scenes.out(d2_scenes.py の再実行):4 | −126 | 円/日(pnl_jpy) | 一致 |
| 155 | +143 | 円/日 | foot/scenes.out:8 | +143 | 円/日(pnl_jpy) | 一致 |
| 155 | −181 | 円/日 | foot/scenes.out:8 | −181 | 円/日(pnl_jpy) | 一致 |
| 155 | +399 | 円/日 | foot/scenes.out:8 | +399 | 円/日(pnl_jpy) | 一致 |
| 155 | +411 | 円/日 | scratchpad/d2_scenes.out(d2_scenes.py の再実行):6 | +411 | 円/日(pnl_jpy) | 一致 |
| 155 | +226 | 円/日 | scratchpad/d2_scenes.out(d2_scenes.py の再実行):6 | +226 | 円/日(pnl_jpy) | 一致 |
| 155 | +634 | 円/日 | scratchpad/d2_scenes.out(d2_scenes.py の再実行):6 | +634 | 円/日(pnl_jpy) | 一致 |
| 155 | +12 | 円/日 | foot/scenes.out:9 | +12 | 円/日(pnl_jpy) | 一致 |
| 155 | −140 | 円/日 | foot/scenes.out:9 | −140 | 円/日(pnl_jpy) | 一致 |
| 155 | +162 | 円/日 | foot/scenes.out:9 | +162 | 円/日(pnl_jpy) | 一致 |
| 155 | −282 | 円/日 | scratchpad/d2_scenes.out(d2_scenes.py の再実行):7 | −282 | 円/日(pnl_jpy) | 一致 |
| 155 | −462 | 円/日 | scratchpad/d2_scenes.out(d2_scenes.py の再実行):7 | −462 | 円/日(pnl_jpy) | 一致 |
| 155 | −111 | 円/日 | scratchpad/d2_scenes.out(d2_scenes.py の再実行):7 | −111 | 円/日(pnl_jpy) | 一致 |
| 156 | +283 | 円/日 | foot/scenes.out:11 | +283 | 円/日(pnl_jpy) | 一致 |
| 156 | +57 | 円/日 | foot/scenes.out:11 | +57 | 円/日(pnl_jpy) | 一致 |
| 156 | +554 | 円/日 | foot/scenes.out:11 | +554 | 円/日(pnl_jpy) | 一致 |
| 156 | +656 | 円/日 | scratchpad/d2_scenes.out(d2_scenes.py の再実行):9 | +656 | 円/日(pnl_jpy) | 一致 |
| 156 | +336 | 円/日 | scratchpad/d2_scenes.out(d2_scenes.py の再実行):9 | +336 | 円/日(pnl_jpy) | 一致 |
| 156 | +1007 | 円/日 | scratchpad/d2_scenes.out(d2_scenes.py の再実行):9 | +1007 | 円/日(pnl_jpy) | 一致 |
| 156 | +47 | 円/日 | foot/scenes.out:12 | +47 | 円/日(pnl_jpy) | 一致 |
| 156 | −173 | 円/日 | foot/scenes.out:12 | −173 | 円/日(pnl_jpy) | 一致 |
| 156 | +257 | 円/日 | foot/scenes.out:12 | +257 | 円/日(pnl_jpy) | 一致 |
| 156 | −343 | 円/日 | scratchpad/d2_scenes.out(d2_scenes.py の再実行):10 | −343 | 円/日(pnl_jpy) | 一致 |
| 156 | −529 | 円/日 | scratchpad/d2_scenes.out(d2_scenes.py の再実行):10 | −529 | 円/日(pnl_jpy) | 一致 |
| 156 | −135 | 円/日 | scratchpad/d2_scenes.out(d2_scenes.py の再実行):10 | −135 | 円/日(pnl_jpy) | 一致 |
| 179 | +78.0 | 円/本 | foot/compare.md:7 | +78.0 | 円(pnl_jpy) | 一致 |
| 179 | −607.7 | 円/本 | foot/compare.md:7 | −607.7 | 円(pnl_jpy) | 一致 |
| 179 | −2103428 | 円 | foot/compare.md:7 | −2103428 | 円(pnl_jpy) | 一致 |
| 179 | +227294 | 円 | foot/compare.md:7 | +227294 | 円(pnl_jpy) | 一致 |
| 180 | +40.5 | 円/本 | foot/compare.md:6 | +40.5 | 円(pnl_jpy) | 一致 |
| 180 | −281.0 | 円/本 | foot/compare.md:6 | −281.0 | 円(pnl_jpy) | 一致 |
| 180 | −3866293 | 円 | foot/compare.md:6 | −3866293 | 円(pnl_jpy) | 一致 |
| 180 | +532210 | 円 | foot/compare.md:6 | +532210 | 円(pnl_jpy) | 一致 |
| 181 | +69.0 | 円/本 | foot/compare.md:14 | +69.0 | 円(pnl_jpy) | 一致 |
| 181 | −518.7 | 円/本 | foot/compare.md:14 | −518.7 | 円(pnl_jpy) | 一致 |
| 181 | −1903637 | 円 | foot/compare.md:14 | −1903637 | 円(pnl_jpy) | 一致 |
| 181 | −13748 | 円 | foot/compare.md:14 | −13748 | 円(pnl_jpy) | 一致 |
| 182 | +32.2 | 円/本 | foot/compare.md:13 | +32.2 | 円(pnl_jpy) | 一致 |
| 182 | −238.4 | 円/本 | foot/compare.md:13 | −238.4 | 円(pnl_jpy) | 一致 |
| 182 | −3834951 | 円 | foot/compare.md:13 | −3834951 | 円(pnl_jpy) | 一致 |
| 182 | −400821 | 円 | foot/compare.md:13 | −400821 | 円(pnl_jpy) | 一致 |
| 184 | +73.6 | 円/取引 | foot_5/diag_tables.md:66 | +3.68(×20 = 73.6) | bp/取引 | 一致 |
| 184 | +69.6 | 円/取引 | foot_5/diag_tables.md:66 | +3.48(×20 = 69.6) | bp/取引 | 一致 |
| 184 | +77.8 | 円/取引 | foot_5/diag_tables.md:66 | +3.89(×20 = 77.8) | bp/取引 | 一致 |
| 184 | −562.8 | 円/取引 | foot_5/diag_tables.md:65 | −28.14(×20 = −562.8) | bp/取引 | 一致 |
| 184 | −595.0 | 円/取引 | foot_5/diag_tables.md:65 | −29.75(×20 = −595.0) | bp/取引 | 一致 |
| 184 | −529.0 | 円/取引 | foot_5/diag_tables.md:65 | −26.45(×20 = −529.0) | bp/取引 | 一致 |
| 184 | −1237.4 | 円/取引 | foot_5/diag_tables.md:67 | −61.87(×20 = −1237.4) | bp/取引 | 一致 |
| 184 | −1635.4 | 円/取引 | foot_5/diag_tables.md:67 | −81.77(×20 = −1635.4) | bp/取引 | 一致 |
| 184 | −926.0 | 円/取引 | foot_5/diag_tables.md:67 | −46.30(×20 = −926.0) | bp/取引 | 一致 |
| 185 | +20.6 | 円/取引 | foot_5/diag_tables.md:57 | +1.03(×20 = 20.6) | bp/取引 | 一致 |
| 185 | +21.4 | 円/取引 | foot_5/diag_tables.md:54 | +1.07(×20 = 21.4) | bp/取引 | 一致 |
| 185 | +22.6 | 円/取引 | foot_5/diag_tables.md:56 | +1.13(×20 = 22.6) | bp/取引 | 一致 |
| 185 | −58.2 | 円/取引 | foot_5/diag_tables.md:55 | −2.91(×20 = −58.2) | bp/取引 | 一致 |
| 185 | −67.4 | 円/取引 | foot_5/diag_tables.md:55 | −3.37(×20 = −67.4) | bp/取引 | 一致 |
| 185 | −49.2 | 円/取引 | foot_5/diag_tables.md:55 | −2.46(×20 = −49.2) | bp/取引 | 一致 |
| 186 | −1439 | 円 | foot_5/diag_tables.md:46 | −71.94(×20 = −1439) | bp | 一致 |
| 186 | −401 | 円 | foot_5/diag_tables.md:46 | −20.07(×20 = −401) | bp | 一致 |
| 186 | +13 | 円 | foot_5/diag_tables.md:46 | +0.64(×20 = 13) | bp | 一致 |
| 186 | +30 | 円 | foot_5/diag_tables.md:46 | +1.51(×20 = 30) | bp | 一致 |
| 186 | +75 | 円 | foot_5/diag_tables.md:46 | +3.73(×20 = 75) | bp | 一致 |
| 186 | +265 | 円 | foot_5/diag_tables.md:46 | +13.24(×20 = 265) | bp | 一致 |
| 186 | +581 | 円 | foot_5/diag_tables.md:46 | +29.06(×20 = 581) | bp | 一致 |
| 187 | +110 | 円/日 | same_bar_daily_4fam.out:9 | +110 | 円/日(pnl_bp × 20) | 一致 |
| 187 | +87 | 円/日 | same_bar_daily_4fam.out:9 | +87 | 円/日(pnl_bp × 20) | 一致 |
| 187 | +131 | 円/日 | same_bar_daily_4fam.out:9 | +131 | 円/日(pnl_bp × 20) | 一致 |
| 187 | +26 | 円/日 | same_bar_daily_4fam.out:9 | +26 | 円/日(pnl_bp × 20) | 一致 |
| 187 | +12 | 円/日 | same_bar_daily_4fam.out:9 | +12 | 円/日(pnl_bp × 20) | 一致 |
| 187 | +37 | 円/日 | same_bar_daily_4fam.out:9 | +37 | 円/日(pnl_bp × 20) | 一致 |
| 187 | +45 | 円/日 | same_bar_daily_4fam.out:10 | +45 | 円/日(pnl_bp × 20) | 一致 |
| 187 | −57 | 円/日 | same_bar_daily_4fam.out:10 | −57 | 円/日(pnl_bp × 20) | 一致 |
| 187 | +147 | 円/日 | same_bar_daily_4fam.out:10 | +147 | 円/日(pnl_bp × 20) | 一致 |
| 187 | −35 | 円/日 | same_bar_daily_4fam.out:10 | −35 | 円/日(pnl_bp × 20) | 一致 |
| 187 | −131 | 円/日 | same_bar_daily_4fam.out:10 | −131 | 円/日(pnl_bp × 20) | 一致 |
| 187 | +55 | 円/日 | same_bar_daily_4fam.out:10 | +55 | 円/日(pnl_bp × 20) | 一致 |
| 187 | +329 | 円/日 | count/same_bar_daily.out:3 | +329 | 円/日(pnl_bp × 20) | 一致 |
| 187 | +117 | 円/日 | count/same_bar_daily.out:3 | +117 | 円/日(pnl_bp × 20) | 一致 |
| 187 | +33 | 円/日 | count/same_bar_daily.out:4 | +33 | 円/日(pnl_bp × 20) | 一致 |
| 187 | −100 | 円/日 | count/same_bar_daily.out:4 | −100 | 円/日(pnl_bp × 20) | 一致 |
| 187 | +167 | 円/日 | count/same_bar_daily.out:4 | +167 | 円/日(pnl_bp × 20) | 一致 |
| 187 | −390 | 円/日 | count/same_bar_daily.out:4 | −390 | 円/日(pnl_bp × 20) | 一致 |
| 187 | −474 | 円/日 | count/same_bar_daily.out:4 | −474 | 円/日(pnl_bp × 20) | 一致 |
| 187 | −302 | 円/日 | count/same_bar_daily.out:4 | −302 | 円/日(pnl_bp × 20) | 一致 |
| 187 | +160994 | 円 | same_bar_all.out:19 | +160994 | 円(pnl_jpy) | 一致 |
| 187 | +37917 | 円 | same_bar_all.out:19 | +37917 | 円(pnl_jpy) | 一致 |
| 187 | +66301 | 円 | same_bar_all.out:19 | +66301 | 円(pnl_jpy) | 一致 |
| 187 | −51665 | 円 | same_bar_all.out:19 | −51665 | 円(pnl_jpy) | 一致 |
| 210 | +5811060 | 円 | foot_5/diag_paths.md:11 | +290553(×20 = 5811060) | bp(単位名なし。pnl_bp) | 一致 |
| 210 | +10.92 | move_bp(列名に単位なし。本文で move_bp) | foot_5/diag_paths.md:11 | +10.92 | bp(値動き) | 一致 |
| 210 | −6.63 | move_bp(同) | foot_5/diag_paths.md:11 | −6.63 | bp(値動き) | 一致 |
| 211 | −3855980 | 円 | foot_5/diag_paths.md:12 | −192799(×20 = −3855980) | bp(単位名なし。pnl_bp) | 一致 |
| 211 | +4.10 | move_bp(同) | foot_5/diag_paths.md:12 | +4.10 | bp(値動き) | 一致 |
| 211 | −59.99 | move_bp(同) | foot_5/diag_paths.md:12 | −59.99 | bp(値動き) | 一致 |
| 212 | −1940440 | 円 | foot_5/diag_paths.md:13 | −97022(×20 = −1940440) | bp(単位名なし。pnl_bp) | 一致 |
| 212 | −3.66 | move_bp(同) | foot_5/diag_paths.md:13 | −3.66 | bp(値動き) | 一致 |
| 212 | −57.50 | move_bp(同) | foot_5/diag_paths.md:13 | −57.50 | bp(値動き) | 一致 |
| 213 | 0 | 円 | foot_5/diag_paths.md:14 | +0(×20 = 0) | bp(単位名なし。pnl_bp) | 一致 |
| 213 | +2.57 | move_bp(同) | foot_5/diag_paths.md:14 | +2.57 | bp(値動き) | 一致 |
| 213 | +0.00 | move_bp(同) | foot_5/diag_paths.md:14 | +0.00 | bp(値動き) | 一致 |
| 216 | −0.48 | move_bp | foot_5/diag_paths.md:22 | −0.48 | bp(値動き) | 一致 |
| 216 | −0.67 | move_bp | foot_5/diag_paths.md:22 | −0.67 | bp(値動き) | 一致 |
| 216 | −0.28 | move_bp | foot_5/diag_paths.md:22 | −0.28 | bp(値動き) | 一致 |
| 216 | −1.55 | move_bp | foot_5/diag_paths.md:23 | −1.55 | bp(値動き) | 一致 |
| 216 | −1.94 | move_bp | foot_5/diag_paths.md:23 | −1.94 | bp(値動き) | 一致 |
| 216 | −1.17 | move_bp | foot_5/diag_paths.md:23 | −1.17 | bp(値動き) | 一致 |
| 216 | −3.32 | move_bp | foot_5/diag_paths.md:24 | −3.32 | bp(値動き) | 一致 |
| 216 | −4.22 | move_bp | foot_5/diag_paths.md:24 | −4.22 | bp(値動き) | 一致 |
| 216 | −2.45 | move_bp | foot_5/diag_paths.md:24 | −2.45 | bp(値動き) | 一致 |
| 216 | −0.34 | move_bp | base/diag_paths.md:22 | −0.34 | bp(値動き) | 一致 |
| 216 | −0.66 | move_bp | base/diag_paths.md:23 | −0.66 | bp(値動き) | 一致 |
| 216 | −0.42 | move_bp | base/diag_paths.md:24 | −0.42 | bp(値動き) | 一致 |
| 239 | −9.41 | move_bp | foot_5/diag_paths.md:32 | −9.41 | bp(値動き) | 一致 |
| 239 | −9.86 | move_bp | foot_5/diag_paths.md:32 | −9.86 | bp(値動き) | 一致 |
| 239 | −8.91 | move_bp | foot_5/diag_paths.md:32 | −8.91 | bp(値動き) | 一致 |
| 239 | −0.18 | move_bp | foot_5/diag_paths.md:41 | −0.18 | bp(値動き) | 一致 |
| 239 | −0.29 | move_bp | foot_5/diag_paths.md:41 | −0.29 | bp(値動き) | 一致 |
| 239 | −0.08 | move_bp | foot_5/diag_paths.md:41 | −0.08 | bp(値動き) | 一致 |
| 239 | +0.01 | move_bp | foot_5/diag_paths.md:41 | +0.01 | bp(値動き) | 一致 |
| 239 | −0.07 | move_bp | foot_5/diag_paths.md:41 | −0.07 | bp(値動き) | 一致 |
| 239 | +0.08 | move_bp | foot_5/diag_paths.md:41 | +0.08 | bp(値動き) | 一致 |
| 240 | −9.67 | move_bp | foot_5/diag_paths.md:33 | −9.67 | bp(値動き) | 一致 |
| 240 | −10.20 | move_bp | foot_5/diag_paths.md:33 | −10.20 | bp(値動き) | 一致 |
| 240 | −9.10 | move_bp | foot_5/diag_paths.md:33 | −9.10 | bp(値動き) | 一致 |
| 240 | −0.37 | move_bp | foot_5/diag_paths.md:42 | −0.37 | bp(値動き) | 一致 |
| 240 | −0.58 | move_bp | foot_5/diag_paths.md:42 | −0.58 | bp(値動き) | 一致 |
| 240 | −0.17 | move_bp | foot_5/diag_paths.md:42 | −0.17 | bp(値動き) | 一致 |
| 240 | +0.06 | move_bp | foot_5/diag_paths.md:42 | +0.06 | bp(値動き) | 一致 |
| 240 | −0.11 | move_bp | foot_5/diag_paths.md:42 | −0.11 | bp(値動き) | 一致 |
| 240 | +0.24 | move_bp | foot_5/diag_paths.md:42 | +0.24 | bp(値動き) | 一致 |
| 241 | −10.49 | move_bp | foot_5/diag_paths.md:34 | −10.49 | bp(値動き) | 一致 |
| 241 | −11.14 | move_bp | foot_5/diag_paths.md:34 | −11.14 | bp(値動き) | 一致 |
| 241 | −9.81 | move_bp | foot_5/diag_paths.md:34 | −9.81 | bp(値動き) | 一致 |
| 241 | −1.30 | move_bp | foot_5/diag_paths.md:43 | −1.30 | bp(値動き) | 一致 |
| 241 | −1.72 | move_bp | foot_5/diag_paths.md:43 | −1.72 | bp(値動き) | 一致 |
| 241 | −0.91 | move_bp | foot_5/diag_paths.md:43 | −0.91 | bp(値動き) | 一致 |
| 241 | +0.45 | move_bp | foot_5/diag_paths.md:43 | +0.45 | bp(値動き) | 一致 |
| 241 | +0.11 | move_bp | foot_5/diag_paths.md:43 | +0.11 | bp(値動き) | 一致 |
| 241 | +0.79 | move_bp | foot_5/diag_paths.md:43 | +0.79 | bp(値動き) | 一致 |
| 242 | −12.94 | move_bp | foot_5/diag_paths.md:35 | −12.94 | bp(値動き) | 一致 |
| 242 | −14.06 | move_bp | foot_5/diag_paths.md:35 | −14.06 | bp(値動き) | 一致 |
| 242 | −11.79 | move_bp | foot_5/diag_paths.md:35 | −11.79 | bp(値動き) | 一致 |
| 242 | −3.60 | move_bp | foot_5/diag_paths.md:44 | −3.60 | bp(値動き) | 一致 |
| 242 | −4.52 | move_bp | foot_5/diag_paths.md:44 | −4.52 | bp(値動き) | 一致 |
| 242 | −2.74 | move_bp | foot_5/diag_paths.md:44 | −2.74 | bp(値動き) | 一致 |
| 242 | +1.47 | move_bp | foot_5/diag_paths.md:44 | +1.47 | bp(値動き) | 一致 |
| 242 | +0.49 | move_bp | foot_5/diag_paths.md:44 | +0.49 | bp(値動き) | 一致 |
| 242 | +2.42 | move_bp | foot_5/diag_paths.md:44 | +2.42 | bp(値動き) | 一致 |
| 244 | −3.60 | move_bp | foot_5/diag_paths.md:44 | −3.60 | bp(値動き) | 一致 |
| 244 | +0.45 | move_bp | foot_5/diag_paths.md:43 | +0.45 | bp(値動き) | 一致 |
| 244 | +1.47 | move_bp | foot_5/diag_paths.md:44 | +1.47 | bp(値動き) | 一致 |
| 264 | +8.0 | 円/取引 | foot_5/diag_tables.md:76 | +0.40(×20 = 8.0) | bp/取引 | 一致 |
| 264 | +4.0 | 円/取引 | foot_5/diag_tables.md:76 | +0.20(×20 = 4.0) | bp/取引 | 一致 |
| 264 | +12.0 | 円/取引 | foot_5/diag_tables.md:76 | +0.60(×20 = 12.0) | bp/取引 | 一致 |
| 265 | +1.4 | 円/取引 | foot_5/diag_tables.md:73 | +0.07(×20 = 1.4) | bp/取引 | 一致 |
| 265 | −3.8 | 円/取引 | foot_5/diag_tables.md:73 | −0.19(×20 = −3.8) | bp/取引 | 一致 |
| 265 | +6.6 | 円/取引 | foot_5/diag_tables.md:73 | +0.33(×20 = 6.6) | bp/取引 | 一致 |
| 266 | −2.2 | 円/取引 | foot_5/diag_tables.md:75 | −0.11(×20 = −2.2) | bp/取引 | 一致 |
| 266 | −7.2 | 円/取引 | foot_5/diag_tables.md:75 | −0.36(×20 = −7.2) | bp/取引 | 一致 |
| 266 | +2.6 | 円/取引 | foot_5/diag_tables.md:75 | +0.13(×20 = 2.6) | bp/取引 | 一致 |
| 267 | +1.0 | 円/取引 | foot_5/diag_tables.md:74 | +0.05(×20 = 1.0) | bp/取引 | 一致 |
| 267 | −3.8 | 円/取引 | foot_5/diag_tables.md:74 | −0.19(×20 = −3.8) | bp/取引 | 一致 |
| 267 | +6.4 | 円/取引 | foot_5/diag_tables.md:74 | +0.32(×20 = 6.4) | bp/取引 | 一致 |
| 288 | +28.0 | 円/日 | d7_fullperiod.out:19 | +28.0 | 円/日(pnl_jpy) | 一致 |
| 288 | −63.8 | 円/日 | d7_fullperiod.out:19 | −63.8 | 円/日(pnl_jpy) | 一致 |
| 288 | +134.1 | 円/日 | d7_fullperiod.out:19 | +134.1 | 円/日(pnl_jpy) | 一致 |
| 288 | −208 | 円/日 | d7_fullperiod.out:20 | −207.6 | 円/日(pnl_jpy) | 一致 |
| 288 | −363 | 円/日 | d7_fullperiod.out:20 | −363.0 | 円/日(pnl_jpy) | 一致 |
| 288 | −64 | 円/日 | d7_fullperiod.out:20 | −63.7 | 円/日(pnl_jpy) | 一致 |
| 288 | +263 | 円/日 | d7_fullperiod.out:21 | +263.3 | 円/日(pnl_jpy) | 一致 |
| 288 | +150 | 円/日 | d7_fullperiod.out:21 | +150.3 | 円/日(pnl_jpy) | 一致 |
| 288 | +376 | 円/日 | d7_fullperiod.out:21 | +375.8 | 円/日(pnl_jpy) | 一致 |
| 292 | +30 | 円/日 | foot_5/diag_tables.md:82 | +1.48(×20 = 30) | bp/日 | 一致 |
| 292 | −66 | 円/日 | foot_5/diag_tables.md:82 | −3.29(×20 = −66) | bp/日 | 一致 |
| 292 | +128 | 円/日 | foot_5/diag_tables.md:82 | +6.39(×20 = 128) | bp/日 | 一致 |
| 292 | 139 | 円/日(MDE) | foot_5/diag_tables.md:82 | +6.97(×20 = 139) | bp/日(MDE) | 一致 |
| 293 | +181 | 円/日 | foot_5/diag_tables.md:83 | +9.06(×20 = 181) | bp/日 | 一致 |
| 294 | −11 | 円/日 | foot_5/diag_tables.md:84 | −0.53(×20 = −11) | bp/日 | 一致 |
| 295 | −192 | 円/日 | foot_5/diag_tables.md:85 | −9.62(×20 = −192) | bp/日 | 一致 |
| 296 | −578 | 円/日 | foot_5/diag_tables.md:86 | −28.92(×20 = −578) | bp/日 | 一致 |
| 296 | −841 | 円/日 | foot_5/diag_tables.md:86 | −42.05(×20 = −841) | bp/日 | 一致 |
| 296 | −316 | 円/日 | foot_5/diag_tables.md:86 | −15.79(×20 = −316) | bp/日 | 一致 |
| 297 | −63 | 円/日 | foot_5/diag_tables.md:87 | −3.13(×20 = −63) | bp/日 | 一致 |
| 298 | +215 | 円/日 | foot_5/diag_tables.md:88 | +10.74(×20 = 215) | bp/日 | 一致 |
| 299 | +159 | 円/日 | foot_5/diag_tables.md:89 | +7.95(×20 = 159) | bp/日 | 一致 |
| 300 | +200 | 円/日 | foot_5/diag_tables.md:90 | +10.00(×20 = 200) | bp/日 | 一致 |
| 300 | +23 | 円/日 | foot_5/diag_tables.md:90 | +1.13(×20 = 23) | bp/日 | 一致 |
| 300 | +370 | 円/日 | foot_5/diag_tables.md:90 | +18.50(×20 = 370) | bp/日 | 一致 |
| 301 | +513 | 円/日 | foot_5/diag_tables.md:91 | +25.64(×20 = 513) | bp/日 | 一致 |
| 301 | +354 | 円/日 | foot_5/diag_tables.md:91 | +17.68(×20 = 354) | bp/日 | 一致 |
| 301 | +680 | 円/日 | foot_5/diag_tables.md:91 | +33.98(×20 = 680) | bp/日 | 一致 |
| 303 | +17,157 | bp | foot_5/diag_tables.md:93 | +17157 | bp | 一致 |
| 303 | +12,897 | bp | foot_5/diag_tables.md:93(単位を書いていない「和 +12897」) | +12897 | bp(同じ行の前の和が bp) | 一致 |
| 303 | +25,946 | bp | foot_5/diag_tables.md:93(同) | +25946 | bp(同) | 一致 |
| 309 | −204 | 円/日 | half_diff.out:5 | −204 | 円/日(pnl_bp × 20) | 一致 |
| 309 | −354 | 円/日 | half_diff.out:5 | −354 | 円/日(pnl_bp × 20) | 一致 |
| 309 | −53 | 円/日 | half_diff.out:5 | −53 | 円/日(pnl_bp × 20) | 一致 |
| 309 | 218 | 円/日(MDE) | half_diff.out:5 | 218 | 円/日(pnl_bp × 20) | 一致 |
| 309 | +263 | 円/日 | half_diff.out:5 | +263 | 円/日(pnl_bp × 20) | 一致 |
| 309 | +144 | 円/日 | half_diff.out:5 | +144 | 円/日(pnl_bp × 20) | 一致 |
| 309 | +377 | 円/日 | half_diff.out:5 | +377 | 円/日(pnl_bp × 20) | 一致 |
| 309 | 165 | 円/日(MDE) | half_diff.out:5 | 165 | 円/日(pnl_bp × 20) | 一致 |
| 311 | 139 | 円/日(MDE) | foot_5/diag_tables.md:82 | +6.97(×20 = 139) | bp/日(MDE) | 一致 |
| 311 | +30 | 円/日(単位は同じ文の MDE と同じ) | foot_5/diag_tables.md:82 | +1.48(×20 = 30) | bp/日 | 一致 |
| 327 | −13,748 | 円 | foot/compare.md:14 | −13748 | 円(pnl_jpy) | 一致 |
| 328 | −3.60 | move_bp(単位を書いていない) | foot_5/diag_paths.md:44 | −3.60 | bp(値動き) | 一致 |
| 330 | −3.60 | move_bp(単位を書いていない) | foot_5/diag_paths.md:44 | −3.60 | bp(値動き) | 一致 |
| 359 | −204 | 円/日(単位を書いていない。D7 の表は円/日) | half_diff.out:5 | −204 | 円/日 | 一致 |
| 359 | −354 | 円/日(単位を書いていない。D7 の表は円/日) | half_diff.out:5 | −354 | 円/日 | 一致 |
| 359 | −53 | 円/日(単位を書いていない。D7 の表は円/日) | half_diff.out:5 | −53 | 円/日 | 一致 |
| 359 | +263 | 円/日(単位を書いていない。D7 の表は円/日) | half_diff.out:5 | +263 | 円/日 | 一致 |
| 359 | +144 | 円/日(単位を書いていない。D7 の表は円/日) | half_diff.out:5 | +144 | 円/日 | 一致 |
| 359 | +377 | 円/日(単位を書いていない。D7 の表は円/日) | half_diff.out:5 | +377 | 円/日 | 一致 |
| 361 | +1.47 | move_bp(単位を書いていない) | foot_5/diag_paths.md:44 | +1.47 | bp(値動き) | 一致 |
| 361 | +0.53 | move_bp(単位を書いていない) | base/diag_paths.md:44 | +0.53 | bp(値動き) | 一致 |
| 362 | +283 | 円 | foot/scenes.out:11 | +283。文書は「円」と書き、出所は 1 日あたり 円/日 | 円/日 | 一致 |
| 363 | +8.0 | 円 | foot_5/diag_tables.md:76 | +0.40(×20 = 8.0)。文書は「円」、出所は 1 取引あたり | bp/取引 | 一致 |
| 364 | −3.60 | move_bp(単位を書いていない) | foot_5/diag_paths.md:44 | −3.60 | bp(値動き) | 一致 |
| 365 | +73.6 | 円 | foot_5/diag_tables.md:66 | +3.68(×20 = 73.6) | bp/取引 | 一致 |
| 365 | −562.8 | 円 | foot_5/diag_tables.md:65 | −28.14(×20 = −562.8) | bp/取引 | 一致 |
| 365 | +36.4 | 円 | base/diag_tables.md:66 | +1.82(×20 = 36.4) | bp/取引 | 一致 |
| 365 | −258.8 | 円 | base/diag_tables.md:65 | −12.94(×20 = −258.8) | bp/取引 | 一致 |
| 365 | +73 | 円/日 | foot_5/diag_tables.md:20 | +3.63(×20 = 73) | bp/日 | 一致 |
| 365 | +45 | 円/日 | base/diag_tables.md:20 | +2.24(×20 = 45) | bp/日 | 一致 |
| 389 | +155 | 円/日 | foot_5/diag_tables.md:35 | +7.73(×20 = 155) | bp/日 | 一致 |
| 389 | +46 | 円/日 | foot_5/diag_tables.md:35 | +2.28(×20 = 46) | bp/日 | 一致 |
| 389 | +264 | 円/日 | foot_5/diag_tables.md:35 | +13.22(×20 = 264) | bp/日 | 一致 |
| 389 | −9 | 円/日 | foot_5/diag_tables.md:36 | −0.46(×20 = −9) | bp/日 | 一致 |
| 389 | −106 | 円/日 | foot_5/diag_tables.md:36 | −5.31(×20 = −106) | bp/日 | 一致 |
| 389 | +82 | 円/日 | foot_5/diag_tables.md:36 | +4.08(×20 = 82) | bp/日 | 一致 |
| 389 | 131 | 円/日(MDE) | foot_5/diag_tables.md:36 | +6.53(×20 = 131) | bp/日(MDE) | 一致 |
| 390 | +362 | 円/日 | base/diag_tables.md:35 | +18.11(×20 = 362) | bp/日 | 一致 |
| 390 | +231 | 円/日 | base/diag_tables.md:35 | +11.55(×20 = 231) | bp/日 | 一致 |
| 390 | +497 | 円/日 | base/diag_tables.md:35 | +24.86(×20 = 497) | bp/日 | 一致 |
| 390 | −273 | 円/日 | base/diag_tables.md:36 | −13.63(×20 = −273) | bp/日 | 一致 |
| 390 | −360 | 円/日 | base/diag_tables.md:36 | −18.00(×20 = −360) | bp/日 | 一致 |
| 390 | −184 | 円/日 | base/diag_tables.md:36 | −9.19(×20 = −184) | bp/日 | 一致 |
| 403 | +30 | 円/日 | foot_5/diag_tables.md:82 | +1.48(×20 = 30) | bp/日 | 一致 |
| 403 | −66 | 円/日 | foot_5/diag_tables.md:82 | −3.29(×20 = −66) | bp/日 | 一致 |
| 403 | +128 | 円/日 | foot_5/diag_tables.md:82 | +6.39(×20 = 128) | bp/日 | 一致 |
| 403 | 139 | 円/日(MDE) | foot_5/diag_tables.md:82 | +6.97(×20 = 139) | bp/日(MDE) | 一致 |
| 403 | −204 | 円/日 | half_diff.out:5 | −204 | 円/日 | 一致 |
| 403 | −354 | 円/日 | half_diff.out:5 | −354 | 円/日 | 一致 |
| 403 | −53 | 円/日 | half_diff.out:5 | −53 | 円/日 | 一致 |
| 403 | +263 | 円/日 | half_diff.out:5 | +263 | 円/日 | 一致 |
| 403 | +144 | 円/日 | half_diff.out:5 | +144 | 円/日 | 一致 |
| 403 | +377 | 円/日 | half_diff.out:5 | +377 | 円/日 | 一致 |
| 403 | −11 | 円/日 | foot_5/diag_tables.md:84 | −0.53(×20 = −11) | bp/日 | 一致 |
| 403 | −578 | 円/日 | foot_5/diag_tables.md:86 | −28.92(×20 = −578) | bp/日 | 一致 |
| 403 | −841 | 円/日 | foot_5/diag_tables.md:86 | −42.05(×20 = −841) | bp/日 | 一致 |
| 403 | −316 | 円/日 | foot_5/diag_tables.md:86 | −15.79(×20 = −316) | bp/日 | 一致 |
| 403 | +215 | 円/日 | foot_5/diag_tables.md:88 | +10.74(×20 = 215) | bp/日 | 一致 |
| 403 | +200 | 円/日 | foot_5/diag_tables.md:90 | +10.00(×20 = 200) | bp/日 | 一致 |
| 403 | +23 | 円/日 | foot_5/diag_tables.md:90 | +1.13(×20 = 23) | bp/日 | 一致 |
| 403 | +370 | 円/日 | foot_5/diag_tables.md:90 | +18.50(×20 = 370) | bp/日 | 一致 |
| 403 | +513 | 円/日 | foot_5/diag_tables.md:91 | +25.64(×20 = 513) | bp/日 | 一致 |
| 403 | +354 | 円/日 | foot_5/diag_tables.md:91 | +17.68(×20 = 354) | bp/日 | 一致 |
| 403 | +680 | 円/日 | foot_5/diag_tables.md:91 | +33.98(×20 = 680) | bp/日 | 一致 |
| 407 | +155 | 円/日 | foot_5/diag_tables.md:35 | +7.73(×20 = 155) | bp/日 | 一致 |
| 407 | +46 | 円/日 | foot_5/diag_tables.md:35 | +2.28(×20 = 46) | bp/日 | 一致 |
| 407 | +264 | 円/日 | foot_5/diag_tables.md:35 | +13.22(×20 = 264) | bp/日 | 一致 |
| 407 | −9 | 円/日 | foot_5/diag_tables.md:36 | −0.46(×20 = −9) | bp/日 | 一致 |
| 407 | −106 | 円/日 | foot_5/diag_tables.md:36 | −5.31(×20 = −106) | bp/日 | 一致 |
| 407 | +82 | 円/日 | foot_5/diag_tables.md:36 | +4.08(×20 = 82) | bp/日 | 一致 |
| 407 | −164 | 円/日 | foot_5/diag_tables.md:37 | −8.19(×20 = −164) | bp/日 | 一致 |
| 407 | −307 | 円/日 | foot_5/diag_tables.md:37 | −15.34(×20 = −307) | bp/日 | 一致 |
| 407 | −25 | 円/日 | foot_5/diag_tables.md:37 | −1.27(×20 = −25) | bp/日 | 一致 |
| 407 | +155 | 円/日(2 回目) | foot_5/diag_tables.md:35 | +7.73(×20 = 155) | bp/日 | 一致 |
| 407 | 131 | 円/日(MDE) | foot_5/diag_tables.md:36 | +6.53(×20 = 131) | bp/日(MDE) | 一致 |
| 407 | +110 | 円/日 | same_bar_daily_4fam.out:9 | +110 | 円/日 | 一致 |
| 407 | +87 | 円/日 | same_bar_daily_4fam.out:9 | +87 | 円/日 | 一致 |
| 407 | +131 | 円/日 | same_bar_daily_4fam.out:9 | +131 | 円/日 | 一致 |
| 407 | +45 | 円/日 | same_bar_daily_4fam.out:10 | +45 | 円/日 | 一致 |
| 407 | −57 | 円/日 | same_bar_daily_4fam.out:10 | −57 | 円/日 | 一致 |
| 407 | +147 | 円/日 | same_bar_daily_4fam.out:10 | +147 | 円/日 | 一致 |
| 407 | −35 | 円/日 | same_bar_daily_4fam.out:10 | −35 | 円/日 | 一致 |
| 407 | −131 | 円/日 | same_bar_daily_4fam.out:10 | −131 | 円/日 | 一致 |
| 407 | +55 | 円/日 | same_bar_daily_4fam.out:10 | +55 | 円/日 | 一致 |
| 407 | −204 | 円/日 | half_diff.out:5 | −204 | 円/日 | 一致 |
| 407 | −354 | 円/日 | half_diff.out:5 | −354 | 円/日 | 一致 |
| 407 | −53 | 円/日 | half_diff.out:5 | −53 | 円/日 | 一致 |
| 407 | +263 | 円/日 | half_diff.out:5 | +263 | 円/日 | 一致 |
| 407 | +144 | 円/日 | half_diff.out:5 | +144 | 円/日 | 一致 |
| 407 | +377 | 円/日 | half_diff.out:5 | +377 | 円/日 | 一致 |
| 407 | +30 | 円/日 | foot_5/diag_tables.md:82 | +1.48(×20 = 30) | bp/日 | 一致 |
| 407 | 139 | 円/日(MDE) | foot_5/diag_tables.md:82 | +6.97(×20 = 139) | bp/日(MDE) | 一致 |
