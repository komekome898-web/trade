## 設計の段の判定(jev_design、2026-10-04、モデル 代替(下位モデル 2 名))

- 記録: `docs/RESEARCH/design_substitute/w4_2026-10-04_record.md`
- 設計文書・候補ファイル・意図の番号は記録の本文にある

この道具は判定の中身(どの量を選ぶか)を決めない。出すのは順位と語だけで、選ぶのはリードである。確率と期待値は json にだけ残す。

### 代替(Jev 不達、記録 = docs/RESEARCH/design_substitute/w4_2026-10-04_record.md)

今日(2026-10-04)の W4 の読み 6 つの、事後の設計の段の判定の代わり(L-625)。Jev は 402(TypeSafe の利用分の残りなし)で届かなかった(`scripts/jev_design.py rank-covariates` の出力「未到達(402: … no available TypeSafe API credits …)」)。

- 問い: `docs/RESEARCH/design_substitute/w4_2026-10-04_questions.md`(結果は見せていない。ほかのファイルを読ませていない)
- 答え(逐語): `docs/RESEARCH/design_substitute/w4_2026-10-04_answer1.md`・`w4_2026-10-04_answer2.md`
- 答えた者: 独立の下位モデル 2 名(互いの答えを見ていない)
- **これは事後の判定**: 6 つの読みはすでに結果を見た後。事前登録の代わりにはならない。オーナー L-625「**Aだが、結果的に問題がなかったのなら改良の土台に使わない方がもったいない**」の「問題がなかったか」を確かめるために、読みに使った量・合わせたものと突き合わせる。

## 突き合わせ(リードの判断)

| 単位 | 2 名がともに「直接」とした量 | 読みで使ったか | 2 名がともに「合わせる」とした変数 | 合わせたか | 2 名が「並べて出す」とした変数で、出していないもの |
|---|---|---|---|---|---|

**読み**: 6 つすべてで、2 名がともに「直接」とした量を読みの主の軸に使い、「合わせる」とした変数を合わせていた。2 名とも、取引の数が変わる比べでも「1 日あたりの損益の合計は公平な見出し。取引の数を並べて出す」と答え、今日の読みはどれも取引の数を並べて出している(一部は監査の後)。出していなかったのは「並べて出す」の 2 つ(組み合わせ C の決まらない足の割合、門の年の荒れ具合の水準)で、どちらも結論の向きを変える量ではない【推定】。抜けによって結論が変わる問題は見つからなかった。

## 問い(2 名に渡した文、逐語)

(design_substitute_q.md の本文。長いので要点: 6 つの単位それぞれについて、(Q1) 候補の量を目的にどれだけ直接かで順位づけし direct / proxy / unrelated と理由、(Q2) 候補の変数を match / report / ignore と理由、とくに取引の数が変わるときに 1 日あたりの損益の比べは公平か。結果は見せていない。)

## 答え 1(逐語、英語のまま)

逐語は `w4_2026-10-04_answer1.md`。要点: Unit 1 direct = (c)(b)(h)、match = fill assumption、report = trades/day・year・ambiguous share。Unit 2 direct = (f)(a)、match = fill、report = trades/day・year・in-sample threshold。Unit 3 direct = (a)(b)(c)(e)(f)、match = fill・bar・entry style、report = trades。Unit 4 direct = (c)(d)(g)(a)、match = bar、report = trades・year。Unit 5 direct = (b)(e)(a)(f)、match = year、report = trades・volatility level。Unit 6 direct = (c)(a)(d)、match = bar、report = year。「Per-day total profit on the same data is the fair net comparison … report the trade count alongside.」

## 答え 2(要点、英語のまま。逐語は `w4_2026-10-04_answer2.md`)

Unit 1 direct = (b)(c)(h)、match = fill、report = trades/day・year・ambiguous share。Unit 2 direct = (a)(f)、match = fill、report = trades/day・year・in-sample threshold。Unit 3 direct = (a)(b)(c)、proxy = (f)(e)(d)、match = fill・bar・entry style、report = trades。Unit 4 direct = (a)(b)、proxy = (g)(d)(c)(f)、match = bar、report = trades・year。Unit 5 direct = (b)(a)(e)、report = trades・year・volatility level。Unit 6 direct = (c)(a)(d)、match = bar、report = year。「Per-day total is the fair headline. Show trades per day and per-trade alongside.」

