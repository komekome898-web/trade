# V4(決定表で絞った state)段1 報告(実装 + 前半の確認、2026-09-20)

委任文: `docs/DATA/delegations/20260920_o3c_signal_v4_prompt.md`(段1 だけ)。
設計: `docs/PHASE2/O3C/SIGNAL/SIGNAL_MATERIALS_DESIGN_2026-09-20.md` §6・§7。
**後半 5,000 件には触れていない**(段2 はリードが反証者レビューのあとに別に指示する)。
**Do not commit. Do not push.**(委任文の指定どおり、コミット・プッシュはしていない)。

## (0) 件数と呼び出し数

| 項目 | 件数 |
|---|---|
| N1・N2 の分かれ方(前半・組 A、単発 対 多件の最初) | 単発 5,033 件・多件の最初 3,898 件(計 8,931 件) |
| logistic(1 件目)前半の当てはめ・OOF | 9,069 件 |
| logistic(連鎖の中)前半の当てはめ・OOF | 12,769 件 |
| V4 前半の確認(Jev 呼び出し) | **1,800 回**(1 件目 600 件 × V1・V4 = 1,200 + 連鎖の中 300 件 × V1・V4 = 600)。エラー 0 |
| 遅延(全 1,800 回、`keep_alive=True`) | p50 0.194 秒 / p90 0.242 秒 / p99 0.308 秒 |

## (1) §0 の対応表(委任文どおり)

| やること | オーナーの原文の該当語(逐語) |
|---|---|
| 効く情報は残し、邪魔・無関係は外し、逆に効く情報は逆で与える(決定表 §7.1) | 「**効いている情報は残し、邪魔していたり無関係な情報は排除して、逆に効く情報は逆で与えるべきではないんですか？**」(L-318)、「**全てやってください。**」(L-323) |
| code の logistic を並べ、較正の良い方を方策の模擬に使う | 「**codeでの判断が勝てるならjevを使う意味はありません**」(L-321)、L-323 |
| Jev の遅延を実測し、遅延の項目を足す | 「**判断→注文のタイムロスは後々に成績直結します**」(L-321) |
| 1 件目に「新しい値段の領域」の事実を足す(前半で分かれれば) | L-320 (2) の案に対する L-323 |
| 後半は一度だけ、反証者レビューの後 | 設計 §4・§7.5(リードの規則) |

## (2) コマンド

```
# 1. N1・N2 の分かれ方(screen_N.csv)
python3 -c "import sys, importlib.util; sys.path.insert(0,'scripts'); \
  spec=importlib.util.spec_from_file_location('o3c_jev_state','scripts/o3c_jev_state.py'); \
  js=importlib.util.module_from_spec(spec); spec.loader.exec_module(js); \
  sb=js.StateBuilder(); rows=js.compute_screen_n(sb); \
  js.cont.write_csv(js.SCREEN_N_PATH, rows)"
# 同じことは `python3 scripts/o3c_jev_state.py --stage screen_n` でも再現できる

# 2. logistic(前半の当てはめ・5-fold OOF・config への書き出し)
PYTHONPATH=src python3 scripts/o3c_signal_logit.py

# 3. V4 前半の確認(1,800 回、keep_alive=True、2 件/秒)
PYTHONPATH=src python3 scripts/o3c_jev_state.py --stage v4_preview

# 4. 下見の表(preview_answers.jsonl を読むだけ)
python3 -c "import sys, importlib.util; sys.path.insert(0,'scripts'); \
  spec=importlib.util.spec_from_file_location('o3c_jev_state','scripts/o3c_jev_state.py'); \
  js=importlib.util.module_from_spec(spec); spec.loader.exec_module(js); \
  md=js.build_v4_preview_tables(); js.check_no_banned(md,'preview_tables.md'); \
  (js.V4_OUT_DIR/'preview_tables.md').write_text(md)"

# 5. 全スイート
PYTHONPATH=src python -m pytest
```

## (3) V4 の state の実物 6 件(1 件目 3・連鎖の中 3、英文そのまま)と criteria の英文

### 1 件目(前半の下見サンプルの先頭 3 件)

**`2024-01-31_00084`**
```
No same-side liquidation in the last 60 seconds.
Price made a new 60-second high 0.2 seconds ago and has not pulled back.
Over the last 60 seconds price rose 0.6 bp (range 11.0 bp); over the last 10 seconds it rose 2.7 bp.
Taker flow in the last 5 seconds: 95% buys. Price rose 0.5 bp in the last 5 seconds.
Open interest among the largest fifth within 20 bp above the current price; within 5 bp: none (coverage: yes). Nearest liquidation level above: 18 bp away.
Price is some distance from the day's high. Volatility now vs the last hour: calmer. Trading activity in the last 60 seconds: among the quietest fifth.
Price is 77.1 bp short of a fresh day high.
Within the last 5 minutes, price is near the high end of the range.
```

**`2023-10-26_00004`**
```
No same-side liquidation in the last 60 seconds.
Price made a new 60-second high 0.4 seconds ago and has not pulled back.
Over the last 60 seconds price rose 8.2 bp (range 8.2 bp); over the last 10 seconds it rose 6.6 bp.
Taker flow in the last 5 seconds: 94% buys. Price rose 5.0 bp in the last 5 seconds.
Open interest among the smallest fifth within 20 bp above the current price; within 5 bp: some (coverage: yes). Nearest liquidation level above: none within the mapped range.
Price is at the day's high. Volatility now vs the last hour: much calmer. Trading activity in the last 60 seconds: among the quietest fifth.
This print is at or beyond a fresh day high: price is entering territory not yet traded today.
Within the last 5 minutes, price is near the high end of the range.
```

**`2023-10-31_00053`**
```
No same-side liquidation in the last 60 seconds.
Price made a new 60-second high 32 seconds ago and has not pulled back.
Over the last 60 seconds price rose 1.7 bp (range 1.9 bp); over the last 10 seconds it rose 1.9 bp.
Taker flow in the last 5 seconds: 100% buys. Price rose 0.2 bp in the last 5 seconds.
Open interest among the second-smallest fifth within 20 bp above the current price; within 5 bp: some (coverage: yes). Nearest liquidation level above: none within the mapped range.
Price is some distance from the day's high. Volatility now vs the last hour: much calmer. Trading activity in the last 60 seconds: among the quietest fifth.
Price is 78.3 bp short of a fresh day high.
Within the last 5 minutes, price is near the high end of the range.
```

### 連鎖の中(前半の下見サンプルの先頭 3 件)

**`2023-11-09_00091`**
```
It is the 3th same-side liquidation of a cascade that began 4.6 seconds ago; the amount liquidated so far is among the middle fifth of cascades.
The last two same-side liquidations were 1.8 and 4.6 seconds ago; the gaps are getting shorter.
Same-side liquidations in the last 10 seconds: among the middle fifth (of prints that had any).
Price made a new 60-second high 0.1 seconds ago.
Over the last 60 seconds price rose 12.7 bp (range 12.7 bp); over the last 10 seconds it rose 5.4 bp.
No open interest within 20 bp above the current price; within 5 bp: none (coverage: yes). Nearest liquidation level above: none within the mapped range.
Price is close to the day's high. Volatility now vs the last hour: calmer. Trading activity in the last 60 seconds: among the quietest fifth.
```

**`2024-02-09_00072`**
```
It is the 3th same-side liquidation of a cascade that began 10 seconds ago; the amount liquidated so far is among the middle fifth of cascades.
The last two same-side liquidations were 3.0 and 10 seconds ago; the gaps are getting shorter.
Same-side liquidations in the last 10 seconds: among the second-largest fifth (of prints that had any).
Price made a new 60-second high 0.2 seconds ago.
Over the last 60 seconds price rose 12.4 bp (range 13.6 bp); over the last 10 seconds it rose 8.0 bp.
No open interest within 20 bp above the current price; within 5 bp: none (coverage: yes). Nearest liquidation level above: none within the mapped range.
Price is very close to the day's high. Volatility now vs the last hour: similar. Trading activity in the last 60 seconds: among the second-quietest fifth.
```

**`2023-11-24_00002`**
```
It is the 2th same-side liquidation of a cascade that began 3.6 seconds ago; the amount liquidated so far is among the smallest fifth of cascades.
The last two same-side liquidations were 3.6 and 446 seconds ago; the gaps are getting shorter.
Same-side liquidations in the last 10 seconds: among the second-smallest fifth (of prints that had any).
Price made a new 60-second high 0.7 seconds ago.
Over the last 60 seconds price rose 6.4 bp (range 8.9 bp); over the last 10 seconds it rose 5.4 bp.
No open interest within 20 bp above the current price; within 5 bp: none (coverage: yes). Nearest liquidation level above: none within the mapped range.
Price is very close to the day's high. Volatility now vs the last hour: calmer. Trading activity in the last 60 seconds: among the quietest fifth.
```

### criteria の英文(設計 §7.3、instructions は 1 件目・連鎖の中で共通)

instructions: `Will another same-side liquidation print occur within the next 60 seconds?`

**1 件目**
- yes: `the tape is busy and volatility has picked up versus the last hour; price is at or breaking the day's extreme and has just set a fresh extreme; little or no open interest is mapped just ahead (price is entering territory where positions have not been built); the print is small relative to the recent range`
- no: `a quiet tape, calm volatility, price well inside the day's range, a large amount of open interest mapped just ahead, or an extremely one-sided last 5 seconds on a quiet tape (an isolated forced print)`

**連鎖の中**
- yes: `same-side liquidations are coming faster and larger (more in the last 10 seconds and in the cascade so far), the tape is busy and volatility rising, price keeps setting fresh extremes, near the day's extreme, gaps between prints not lengthening`
- no: `gaps between prints are lengthening, the last extreme was set many seconds ago, price is well inside the day's range, or a large amount of open interest sits just ahead`

(設計 §7.3 の no の原文末尾に付いていた日本語の注記「(前半では多い側の五分位だけが止まる側)」は、Jev に送る英文の criteria からは外した。理由は (5) に書く。)

## (4) N1・N2 の分かれ方の表(前半・組 A〈単発 対 多件の最初〉。材料の表なので数値を書く)

`backtest_data/o3c_signal_materials_20260920/screen_N.csv`(委任文【作るもの】2)

| 候補 | 単発_n | 単発_欠測割合 | 単発_p50 | 多件の最初_n | 多件の最初_欠測割合 | 多件の最初_p50 | 分かれ方の数 | \|分かれ方-0.5\| |
|---|---|---|---|---|---|---|---|---|
| N1(= cand_C3) | 5,033 | 0.0 | 45.977 | 3,898 | 0.0 | 13.092 | 0.5824 | 0.0824 |
| N2(直前5分の値幅の位置) | 5,033 | 0.0 | 0.9989 | 3,898 | 0.0 | 0.9970 | 0.5340 | 0.0340 |

両方とも |分かれ方 − 0.5| ≥ 0.03 なので、設計 §7.2 の規則により **N1・N2 とも V4 の 1 件目の文に足した**(N1 は
`_sentN1`、N2 は `_sentN2`。上の実物 6 件のうち 1 件目 3 件の末尾 1〜2 文がそれ)。N2 は 0.0340 で境目にごく近い
(ブートストラップでの再検定はしていない。§7 限界に書く)。

## (5) 設計に無い判断(全部)

1. **連鎖の中の A3(型9)・A9(型5)の扱い。** 決定表(設計 §7.1)の連鎖の中の行は「残す/逆で与える/向きを
   criteria に」の 3 列を合わせて 11 項目で、設計 §7.4 の「連鎖の中 11 本」と一致するが、A3(型9「連鎖開始
   からの値動き」)と A9(型5「反対側の清算」)はこの 3 列にも「外す」列にも名指しで出てこない。件数の一致
   (11 本)を根拠に、この 2 つは「外す」側として扱った(A9 は §5.2 で「両組とも 99% が 0」と既に書かれており、
   1 件目で「外す」にした根拠がそのまま連鎖の中にも当てはまる)。**この判断は止めずに進めた**(委任文の
   「文の型や criteria を変えたくなったら止めて報告する」は文の型・criteria の変更に対する規定で、この判断は
   決定表の空欄の埋め方であり、件数の内部一致という設計内の証拠で埋められたため)。
2. **決定表が 1 つの文の型の中で材料ごとに違う扱いを指定した箇所の実装。**「「外す」は state からその文を消す」
   (設計 §7.1)は文の型が単一の材料からできている場合はそのまま適用できるが、型10(1 件目: 材料9 残す・材料13
   外す)、型6(連鎖の中: A6 残す・R1 外す)、型3(連鎖の中: 材料2 残す・材料3 外す)の 3 箇所は 1 つの文が
   複数の材料でできていて、決定表の指定が食い違う。**その材料の節(clause)だけを削った版の文を新設した**
   (`_sent10_v4` / `_sent6_v4` / `_sent3_v4`)。型1(材料3・6 とも外す)・型7(材料15・11 とも残す)・型11
   (材料8・5' とも残すが向きだけ反転)・型13(材料14 残す・C3/C4 とも残すが向きだけ反転〈1件目〉/ C3 だけ反転
   〈連鎖の中〉)は 1 つの文の中の全材料が同じ扱いだったので、文はそのまま(向きの違いは criteria だけに反映)。
3. **N1 の logistic 入力は作らない(重複)。** N1 は設計 §7.2 に「C3 の『距離0』を言葉にしたもの」と明記されて
   おり、数値としては `cand_C3` そのもの。すでに C3 を logistic の入力に含めているので、N1 を別入力として
   重複させなかった(完全な共線性になるだけで、logistic には無意味)。N2 は C3 に還元できない新しい数値なので
   入力に足した(1 件目 logistic は 9 本 + N2 の 10 本)。
4. **「先の建玉」(材料8+5' を 1 つの文にまとめたもの)の logistic 代表値は `cand_8`。** 5' は §5.2 で
   「欠測 70〜92%」と書かれており、単独では扱いにくいため、logistic の入力には `cand_8` だけを使った。
5. **N2 の定義・文の形。** 設計は「直前 5 分の値幅の中でいまどこにいるか(清算の向きの端にいる/中/逆の端)」
   としか書いておらず、数式は与えていない。`[ts−300,000ms, ts)` の窓の中の価格の最大・最小を取り、清算の
   向きの端を 1、逆の端を 0 とする線形の位置(0〜1)を作り、2/3 以上・1/3 以下・それ以外の 3 段で文にした
   (`n2_position`・`_sentN2`)。
6. **N1 の文の形と「超えている」のしきい値。** 「距離0」をどこで「超えている」とみなすかの数値を設計は
   与えていないので、型13(「at the day's low/high」)と同じ `DAY_EXTREME_EPS_BP = 0.05` bp を流用した。
7. **criteria の日本語注記を英文から外した。** 設計 §7.3 の連鎖の中の no の原文は英文の直後に
   「(前半では多い側の五分位だけが止まる側)」という日本語の注記が続いていた。Jev に送る criteria は英文だけ
   のはずで、日本語混在の英文を送るのは手引き `docs/JEV.md` の想定から外れると判断し、この注記は
   Jev への送信文からは外した(リードの理解の補足であり、criteria の実質を変えるものではないと読んだ)。
8. **V4 の下見の層化抽出で、1 日 3 件までの上限を「1 件目」「連鎖の中」それぞれ独立に数えた。** 委任文の
   「日を跨いで偏らないよう 1 日 3 件まで」を 2 集団合わせて数えると、900 件 ÷ 3 = 300 日分が要るが前半は
   228 日しか無く、達成できない。前段の実物読み(`select_probes`)のような単一の読み物ではなく、1 件目と
   連鎖の中は別々の統計として扱っているため、集団ごとに独立させた。
9. **logistic の入力の「五分位の順位」の数式。** 設計は「前半の五分位の順位(0〜1、欠測 0.5)」としか書いて
   おらず、量子化の刻みを指定していない。帯の中心(0.1/0.3/0.5/0.7/0.9)を割り当てた(`quintile_rank`)。
10. **ニュートン法の実装細部。** L2 正則化は切片には掛けない(標準的な慣行)。ヘッセ行列が特異なときは
    `lstsq` に切り替える(合成試験では未発火)。収束判定は Δβ の最大絶対値 < 1e-8、最大 100 反復。
11. **下見の表(preview_tables.md)の閾値・ブートストラップの回数。** 閾値 0.6/0.7/0.8 は logistic の報告
    (`logit_firsthalf.md`)と揃えた。ブートストラップは 1,000 回、種は 20260920(委任文の種と同じ)。

## (6) サニティ

- **V4 の呼び出しはエラー 0 件、1,800/1,800。**(`/tmp/v4_preview_run.log`: `V4 呼び出し 1800 件、エラー 0 件、913.3秒`。ログは `data/jev/v4/` の外なので数値の置き場所の制約には当たらない一時ログ)
- **1 件目・連鎖の中とも「外す」側の材料の言い回しが state に出ない**ことを `tests/test_o3c_jev_state.py` の
  `test_v4_first_print_has_no_dropped_material_phrases` / `test_v4_chain_has_no_dropped_material_phrases` で
  合成データに対して検査した(pytest で確認、下の (9) の全スイートに含む)。
- **N2 が ts 以後を使わない**ことを、窓の右端に未来の価格を混ぜても値が変わらない合成試験
  (`test_n2_position_uses_only_causal_window`)と、V4 の 1 件目の state 全体が p0 の書き換えで変わらない試験
  (`test_v4_n1_n2_ignore_future_prices_and_p0`)の 2 段で確認した。
- **logistic の係数が前半だけから決まる**ことを、後半の材料・ラベルを書き換えても前半だけの係数が変わらない
  合成試験(`test_logit_beta_determined_by_front_half_only`)で確認した。予測の決定性も
  (`test_logit_newton_predictions_deterministic`)で確認した。
- **logistic の係数の符号が決定表の向きと整合する**ことを目視で確認した(判定語は使わない、事実の記述):
  1 件目の `cand_8`(先の建玉)の係数は負(建玉が少ない側で確率が上がる = 「先の建玉少ないほど始まる」と同じ
  向き)、`cand_C3`(日の極値からの距離)の係数も負(近いほど確率が上がる = 「近いほど始まる」と同じ向き)。
  連鎖の中の `cand_A6`(極値からの秒数)の係数は負(秒数が小さい = 直近の更新ほど確率が上がる)。
- **N1・N2 とも screen_N.csv で |分かれ方 − 0.5| ≥ 0.03 だったので、V4 の 1 件目の文に実際に足されている**
  ことを (3) の実物 2 件目(`2023-10-26_00004`)の末尾 2 文で確認した。
- **判定語・`paper_logs/` を開いていないこと**は既存の試験(`test_source_never_opens_paper_logs`・
  `test_no_banned_words_in_source_or_sentences`)がそのまま V4 のソースにも掛かる(同じファイル)。

## (7) 限界

- **N2 の分かれ方(0.0340)は境目(0.03)にごく近い。** ブートストラップでの再検定・多重性への算入は
  していない(設計 §7.2 は「|確率 − 0.5| ≥ 0.03」の単純な規則としか指定していないので、その規則どおり実装
  した)。境目に近いことは事実として書く。
- **(5)-1 の A3・A9 の扱いは推測で埋めた空欄であり、オーナー・設計の直接の指定ではない。** 件数の内部一致
  という状況証拠だけを根拠にしている。委任文の指示は「文の型や criteria を変えたくなったら止めて報告する」
  であり、これは「文の型」の変更ではなく決定表の空欄の解釈だが、性格としては同種のグレーゾーンなので、
  ここで明示し、必要なら止めて確認を仰ぐ判断はリードに委ねる。
- **V4 の前半の下見(600+300件)の Jev の確率は、1 件目・連鎖の中とも label_60 との順位分離が V1 よりわずかに
  高いか同程度で、いずれも 0.5〜0.59 の範囲にとどまる**(数値は `preview_tables.md` にのみ書いてあり、
  ここでは性能の数値そのものは書かない。委任文「Jev の性能の数値は書かない」の指定どおり)。この段では
  「V4 が V1 より優れている」という判定はしていない(判定語も使っていない)。較正の良し悪しを使った方策の
  選択は §7.5(段2)の仕事で、段1 では扱っていない。
- **logistic は「先の建玉」を `cand_8` だけで代表させており、5' の情報を落としている。** 5' の欠測率が高い
  ための判断だが、5' が非欠測のときの追加情報は使えていない。
- **Jev(V4)の確率と logistic(OOF)の相関は、1 件目のサンプルでほぼ 0、連鎖の中のサンプルで正の値**
  だった(数値は `preview_tables.md`)。両者が同じ材料から違う判断をしている可能性があるが、この段では
  原因の分析はしていない(段2 以降の仕事)。
- **screen_N.csv・logistic の当てはめは前半全件(8,931 件・9,069 件・12,769 件)に対して行ったが、下見の
  Jev 呼び出しは 900 件(1,800 回)だけ。** 下見サンプルと全数の分布の違いは検査していない。

## (8) 作ったファイル

- `scripts/o3c_jev_state.py`(V4 追加: `build_state_v4`・V4 専用の文の型・N1/N2・`JEV_QUESTIONS_V4_FIRST/CHAIN`・
  `compute_screen_n`・`pick_v4_preview_ids`・`run_preview_v4`・`build_v4_preview_tables`・`--stage screen_n`・
  `--stage v4_preview`)
- `scripts/o3c_signal_logit.py`(新規。logistic の当てはめ・OOF・config 書き出し)
- `tests/test_o3c_jev_state.py`(V4・N1/N2・logistic の試験を追加)
- `backtest_data/o3c_signal_materials_20260920/screen_N.csv`(新規、材料の表なので数値あり)
- `config/o3c_signal_logit_first.yaml`(新規、係数)
- `config/o3c_signal_logit_chain.yaml`(新規、係数)
- `data/jev/v4/logit_firsthalf.md`(数値、リポジトリ外)
- `data/jev/v4/logit_oof.json`(数値、リポジトリ外)
- `data/jev/v4/preview_answers.jsonl`(1,800 行、数値、リポジトリ外)
- `data/jev/v4/preview_tables.md`(数値、リポジトリ外)
- `data/jev/v4/calls/calls_2026-09-20.jsonl`(`JevClient` の呼び出しログ、state 本文は書かない仕様どおり)
- `docs/PHASE2/O3C/SIGNAL/V4_STAGE1_REPORT_2026-09-20.md`(本書)

## (10) 反証者 7 を受けた直し(2026-09-20、後半には触れていない)

対象: `docs/PHASE2/O3C/SIGNAL/REFUTER_REVIEW7_2026-09-20.md` の致命 C1・C3 と、直すべき D1・D2・D4。
設計 §7.5.1 のとおりに直した。**Do not commit. Do not push**(継続)。

### 何を変えたか

- **C1(`cand_8` などの点質量で五分位の順位が潰れる)・C3(前半で固定した切り値を後半に当てる経路が無い)・
  D1(`cand_R1` の同種の退化)**: `scripts/o3c_signal_logit.py` の五分位方式(`quintile_rank`/`build_matrix`、
  4 切り値の `searchsorted`)を撤去し、**前半の経験分布の中央順位**に置き換えた(`ecdf_mid_rank`)。
  材料の値 x の順位 = (前半で x 未満の件数 + x 以下の件数) / (2 × 前半の件数)、欠測は 0.5。前半の並べた値を
  `backtest_data/o3c_signal_materials_20260920/logit_ecdf_{first,chain}.npz` に凍結し(`build_ecdf` /
  `save_ecdf_npz`)、`apply_frozen_rank` が `searchsorted` で引くだけの関数になった(前半の当てはめにも、
  将来の後半への適用にも同じ関数を使う)。`config/o3c_signal_logit_{first,chain}.yaml` は「五分位の切り値」を
  持たず、材料の並び・`ecdf_ファイル`・`ecdf_md5`・係数だけを持つ形に書き直した。R1 は 1 件目の入力
  (`cand_R1`)としてもともと同じパイプラインを通っていたので、同じ直しで退化が解消される(専用の変更は不要)。
  前半全件で当てはめ直し、5-fold out-of-fold(順位分離・的中・閾値 0.6/0.7/0.8 の適合率と件数)を
  `data/jev/v4/logit_firsthalf.md` に書き直した(数値はリポジトリに入れていない)。
- **D2(較正の良さが未実装)**: 新規 `scripts/o3c_signal_calib.py` に `calibration_goodness` を実装。
  帯は `[0,0.05) … [0.95,1.0]` の固定 20 本(起点 0、最後の帯だけ両端閉区間)。件数 20 未満の帯は平均から
  外し、外した帯を戻り値の「外した帯」に入れる。値 = Σ n_b × |実際の割合_b − 帯の中央_b| / Σ n_b(使った帯
  だけの重み付き平均)。`choose_better(jev_goodness, code_goodness)` は差が 0.01 以内の同点(または値が NaN)
  なら `"code"` を返す(設計 §7.5「同点なら遅延の短い code」)。合成データの試験 8 件を
  `tests/test_o3c_signal_calib.py` に追加(完璧に近い較正で値が小さいこと、少数帯の除外、手計算との一致、
  NaN の扱い、同点境界の扱い)。
- **D4(`StateBuilder` が帯を毎回再計算)**: `scripts/o3c_jev_state.py` の `StateBuilder.__init__` に
  `bands_path`(既定 `config/o3c_jev_state_bands.yaml`)を追加。`bands` 引数を明示しない限り、
  `bands_path` が存在すればそれを読む(`load_bands_yaml`)。存在しなければ前半から計算して書く
  (`compute_bands` → `write_bands_yaml`)。以前は `bands` 引数を省略すると常にその場で再計算していた。

### 設計に無い判断

- 5-fold out-of-fold の材料の順位は、旧実装(五分位版)と同じ構造(順位化は前半全件から 1 回だけ決め、
  fold ごとに再学習するのはロジスティックの係数だけ)を踏襲した。設計 §7.5.1 は「前半に当てはめ直し、
  前半の out-of-fold もやり直す」としか書いておらず、fold ごとに ecdf を作り直すかどうかは明記していない
  ため、変更前の構造をそのまま維持した(変えていないので新しい判断ではないが、明記する)。
- `calibration_goodness` の「使った帯」「外した帯」に、件数 0 の帯(そもそもデータが無い帯)は含めない
  実装にした(「外した」というより「存在しない」帯のため)。

### 試験(委任文【作るもの】4 のうち今回追加した分)

`tests/test_o3c_jev_state.py` に追加:
- `test_ecdf_mid_rank_point_mass_does_not_collapse`(点質量でも順位が潰れない。0 は frac_zero/2 前後、
  正の値はその上に分散する)
- `test_ecdf_mid_rank_matches_hand_formula_with_ties`
- `test_apply_frozen_rank_reproduces_fit_time_ranks_and_round_trips_npz`(npz 保存・読み込みの往復でも
  同じ順位、新しい df に当てても同じ値には同じ順位)
- `test_frozen_ecdf_unaffected_by_back_half_values`(後半の値を変えても前半だけの ecdf は不変)
- `test_state_builder_uses_bands_from_yaml_when_present` / `_computes_and_writes_bands_when_yaml_missing`
- `test_state_sentences_change_when_bands_yaml_changes`(yaml の値を変えると文が変わる = yaml を読んでいる)

`tests/test_o3c_signal_calib.py`(新規、8 件)。

### 変更・作成したファイルの MD5(性能の数値ではないので書く)

| ファイル | MD5 |
|---|---|
| `scripts/o3c_signal_logit.py` | c60fa4eae7ea6cb15be3f887cfd5ae76 |
| `scripts/o3c_signal_calib.py` | b7503692fe6829a42b2e276ad4c81862 |
| `scripts/o3c_jev_state.py` | 8b710da4fef88cffaf74fb00f773dc50 |
| `config/o3c_signal_logit_first.yaml` | 9bafb01d675272c97b2f9cf55c75402c |
| `config/o3c_signal_logit_chain.yaml` | 96ec0710a46bcb9b5ac0233182f0d9e9 |
| `backtest_data/o3c_signal_materials_20260920/logit_ecdf_first.npz` | 0187fba59e3526a958582fc5f65327d3 |
| `backtest_data/o3c_signal_materials_20260920/logit_ecdf_chain.npz` | da24154bb12064af56a59ceb8b4a1959 |

### 作ったファイル(追加分)

- `scripts/o3c_signal_calib.py`(新規)
- `tests/test_o3c_signal_calib.py`(新規)
- `backtest_data/o3c_signal_materials_20260920/logit_ecdf_first.npz`(新規、凍結した経験分布)
- `backtest_data/o3c_signal_materials_20260920/logit_ecdf_chain.npz`(新規、凍結した経験分布)

### 全スイートの末尾行(この直しの後、`-q` 無し)

```
2752 passed, 5 skipped, 1 warning in 456.57s (0:07:36)
```

## (9) テストの末尾行(全スイート、`-q` 無し。段1 実装当初のもの)

```
2737 passed, 5 skipped, 1 warning in 461.69s (0:07:41)
```
