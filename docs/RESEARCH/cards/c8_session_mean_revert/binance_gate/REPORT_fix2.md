# 委任 fix2 の報告(逐語。委任文 `DELEGATION_fix2.md`、2026-10-06)

# 委任 fix2 の報告(カード 8 の門を Binance で確かめる部品の直し 2)

直すこと 1〜5 は全部入れました。委任文 2 (b) の試験の作り物の値(φ 0.97、遅い揺れの標準偏差 150 bp)は委任文に書かれておらず、私が試して選びました(6 の問い 1)。本走らせ・コミット・押し出しはしていません。私が変えたのは次の 3 ファイルだけです: `scripts/w4_measure/c8_binance/bn_read_gate.py`・`scripts/w4_measure/c8_binance/bn_run_c8.py`・`tests/research/test_c8_binance.py`。

## 1. 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| カード 8 の門を Binance の 1 分足で確かめる部品を直す | L-714「**yes**」/ L-715「**Binance の 1 分足(推し)**」「**A と B の両方(推し)**」 |
| 区分 1,812 日を試験で固定する | L-716「**1,812 日で進める(推し)**」 |
| G10a(循環ずらし)・G10b(年ごと)・G10c(元の作り方)を並べ、G10a を主にする | (オーナーの逐語なし)委任文「G10 を事前登録の新しい形にする」 |
| G3 × G10a の読みの表(5 行)を関数にし、行の文を出す | (オーナーの逐語なし)委任文「読みの表(事前登録の 5 行)を関数にして、出力にその行の読みの文を出す」 |
| 試験 (a)〜(d) を足す | (オーナーの逐語なし)委任文「試験」の (a)〜(d) |
| 本番の経路のセントを固定する(assert と終わり方 4) | (オーナーの逐語なし)委任文「本番の経路のセントを固定する」 |
| G6 の感度として塊 20 日を横に並べる | (オーナーの逐語なし)委任文「G6 の感度(任意だが入れる)」 |
| G10b で乱数を引く順(1 回ごとに年を古い順) | **(該当語なし)** → 6 の問い 2 |
| 試験 (b) の作り物の値(φ・揺れの大きさ・乱数の種) | **(該当語なし)** → 6 の問い 1 |
| 塊 20 日の列を GATE_READ.md の主の差の表にだけ出す | **(該当語なし)** → 6 の問い 3 |
| 壊した写しで試験が落ちるかを確かめる(一時置き場だけ) | (オーナーの逐語なし)委任文の必須報告 4「批評家の壊し方(main_nocents ほか)が今の試験で落ちるかの表」 |

## 2. 直したことごとの置き場と差分の要約【事実: 差分】

**1. G10 の新しい形(`bn_read_gate.py`)**
- 新しい関数:
  - `rot_diffs`(G10a): d_k = −Σ x·roll(印, k) ÷ n を、k = 1〜n−1 の全部について出します。`np.roll` は使わず、x を 2 回つないだ列の窓で計算しています。
  - `year_masks`・`placebo_year`(G10b): 年ごとに、実際の門と同じ日数を、その年の日の中だけで 5 日の塊(循環)で外します。1,000 回、種 20261007。
  - `null_compare`(3 つの対照に共通): 上側の割合(≥)・95 点(`np.quantile` の既定)・実際 > 95 点か、を出します。
- G10c は元の `placebo` のまま残しました。
- 出力の形を `res["placebo"] = {"primary": "G10a", "G10a", "G10b", "G10c"}` に変えました。
- G10a には次も出します: `n_shifts` = n−1、`k0_bp`、`k0_equals_actual`(k = 0 の値が G3 の差と一致するか)。
- G10b には次も出します: `removed_by_year`、`removed_by_year_exactly`。
- 読みの表:
  - `READING`(5 行。文は PREREG.md 108〜112 行のまま)と `g3_g10a_reading(印, 超えるか)` を足しました。
  - `res["reading_g3_g10a"][A|B][open|mid]` に、行の番号と文を出します。
  - G3 の印が無いときは None にします。表に無い組み合わせが来たら ValueError を出します。
- GATE_READ.md: G10a(主)・G10b・G10c を 1 つの表に並べ、その後に「G3 × G10a の読み」の行を出します。
- docstring の G6・G10 を書き直しました。docstring は gate_read.json の `rules` にも入ります。

**2. G6 の感度(`bn_read_gate.py`)**
- `SENS_BLOCK = 20` を足しました。仮定である旨をコメントに書いています。
- `stat(x, block=…)` で塊の日数を選べるようにしました。
- `read_block` の各差に `block20`(区間・se・MDE)を足しました。印は付けません。
- GATE_READ.md の G3 の差の表に「塊 20 日の区間・MDE(感度)」の列を足しました。

**3. セントの固定(`bn_run_c8.py`)**
- `main` で `close_eq_mean` に `not_computed` があれば、出力を書いた後に 4 で終わります。
- docstring にもそう書きました。

**4. 試験(`test_c8_binance.py`)**
- 足した試験:
  - `test_main_stops_when_not_cents`
  - `test_committed_classes_counts`
  - `test_g10a_matches_np_roll_reference`
  - `test_g10a_holds_nominal_where_g10c_inflates`
  - `test_g10b_within_year_and_same_count_as_gate`
  - `test_g3_g10a_reading_rows`(6 通りの組み合わせ)
  - `test_g3_g10a_reading_edges_and_prereg_text`(READING の文が PREREG.md にそのままあるかも見る)
  - `test_g6_block20_sensitivity_beside_block5`
- 既存の試験の直し:
  - G10 の試験 2 本を `["G10c"]` を読むように変えました。G10c の参照の実装 `_placebo_ref` は残しています。
  - 区分で損益が決まる作り物で、G10a・G10b でも「超える」が出ることを足しました。
  - `fake_iter` に `assert kw.get("cents", True) is True` を足しました。
- classes.json と PREREG.md は `common.ROOT` から読みます。壊した写しの中でも本物を読むためです。

## 3. 試験の結果【事実】

```
$ PYTHONPATH=src python -m pytest tests/research/test_c8_binance.py
.......................................                                  [100%]
```
失敗はありません(最後の直し `rot_diffs` を窓の計算に替えた後の版)。

**作り物で、試験 (b) の種を 1〜10 に変えて打った結果**(台本の関数を通した。台本は一時置き場の `fix2/seeds.py`)
- 10 回とも試験の条件を満たしました。
- G10a は A 0.020〜0.050、B 0.040〜0.075 でした。
- G10c は A 0.145〜0.240、B 0.140〜0.200 でした。
- 試験に固定した種は 2 です(G10a A 0.050・B 0.040、G10c A 0.215・B 0.200)。

**本物の区分(コミット済みの classes.json)と、区分と無関係な作り物の損益で、300 回打った結果**(`fix2/real_cls.py`)

| 遅い揺れ | G10a A / B | G10b A / B | G10c A / B |
|---|---|---|---|
| なし | 0.030 / 0.077 | 0.033 / 0.060 | 0.033 / 0.067 |
| φ 0.995、標準偏差 30 bp | 0.053 / 0.070 | 0.057 / 0.083 | 0.120 / 0.130 |
| φ 0.995、標準偏差 60 bp | 0.050 / 0.063 | 0.053 / 0.077 | 0.200 / 0.197 |

- G10a の数は、批評家の `sim_rot.py` の数と 3 行とも同じでした。

## 4. 壊し方ごとに、今の試験で落ちるか【事実】

今の台本と試験の写しを一時置き場 `fix2/brk/<名前>/` に作り、1 か所ずつ壊して試験を打ちました。壊さない写し(none)は失敗なしでした。

| 壊し方 | 落ちたか | 落ちた試験 |
|---|---|---|
| block1(BLOCK 5→1) | 落ちる | interval_matches_prereg_values, g6_block20_sensitivity |
| seed1 | 落ちる | 同じ 2 つ |
| moving | 落ちる | 同じ 2 つ |
| hi16 | 落ちる | prereg_hi_fixed |
| half | 落ちる | half_boundary_even_number_of_days |
| mark(`lo >= 0`) | 落ちる | interval_matches_prereg_values |
| placebo_block10 | 落ちる | g10_placebo_matches_reference, g10b_within_year |
| **main_nocents** | **落ちる** | main_non_dry_path_on_fabricated_bars, main_stops_when_not_cents |
| **split_cents** | **落ちない** | — (批評家の [情報] (3)。委任文の直すことに無いので、手を入れていない) |
| rot_k0(k = 0 を含め n−1 を落とす) | 落ちる | g10a_matches_np_roll_reference |
| rot_sign(差の符号を逆にする) | 落ちる | g10a_matches_np_roll_reference, g10a_holds_nominal |
| year_global(G10b を年で分けない) | 落ちる | g10b_within_year |
| year_order(年を新しい順に回す) | 落ちる | g10b_within_year |
| placebo_seed1 | 落ちる | g10_placebo_matches_reference, g10b_within_year |
| q90(PLACEBO_Q 0.95→0.90) | 落ちる | g10_placebo_matches_reference, g10a_matches_np_roll, g10a_holds_nominal, g10b_within_year |
| upper_gt(≥ を > にする) | 落ちる | g10_upper_share_counts_ties |
| reading_text(2 行目の文を縮める) | 落ちる | g3_g10a_reading_rows[2 行目] |
| reading_swap(3 行目の「超える」を「超えない」に) | 落ちる | reading_rows[3 行目]・[4 行目]、g6_block20_sensitivity |
| reading_g10c(読みに G10c を使う) | 落ちる | g10a_matches_np_roll_reference |
| notcents_rc0(4 を 0 にする) | 落ちる | main_stops_when_not_cents |
| sens10(SENS_BLOCK 20→10) | 落ちる | g6_block20_sensitivity |

- reading_swap で g6_block20_sensitivity が落ちたのは、表に (0 を含む, 超える) の行が無くなり、`read_all` が ValueError を出したためです。
- reading_text では `..._prereg_text` は落ちませんでした。縮めた文も PREREG.md の文の一部だからです。
- 壊した置換は、どれも置換数 1 でした。block1 の最初の版は `PLACEBO_BLOCK` にも当たって置換数 2 になったので、直して作り直しました。

## 5. `--dry` の結果【事実】

```
$ PYTHONPATH=src python3 scripts/w4_measure/c8_binance/bn_run_c8.py --dry --out-root <一時置き場>/fix2/dry
```
- 終わり方 rc=0 です。
- 本物の足の読み:
  - 2019-01-01〜01-08、`n_bars_kept 10080`、`sealed_unit "P2-08"`、`n_not_whole_cent 0`
  - 最初の足は `[370123.0, 370372.0, 370109.0, 370246.0]`
- 作り物の足:
  - `boundary_carry_check.same: true`
  - `close_eq_mean` は `n_close_eq_mean 67`・`n_first_of_session 8`・`n_session_end_bar 0`・`n_nonzero_exposure_at_eq 0`
- 読み方の台本も、作り物の出力とコミット済みの classes.json に当てて rc=0 でした。GATE_READ.md に、G10a(主)・G10b・G10c の表、塊 20 日の列、「行 4: 「区別がつかない(MDE と並べる)」」の読みが出ることを確かめました。

## 6. 決めきれなかったこと(問い)

1. **試験 (b) の作り物の値**
   - 委任文の例(60 日ずつ入れ替わる区分)に批評家の値(φ 0.995、標準偏差 60 bp)を当てると、G10c は G10a をはっきり超えませんでした【事実: 試し打ち。A・B とも 0.02〜0.095 の範囲で重なった】。
   - 理由は、区分の並びが 180 日周期で、遅い揺れの長さと合わないためと見ています【推定】。
   - φ 0.97・標準偏差 150 bp・雑音 300 bp にすると分かれたので、この値を試験に置きました(仮定)。この値でよいですか。
2. **G10b で乱数を引く順**
   - 「1 回ごとに年を古い順」にしました。docstring に書き、参照の実装と一致することを試験で固めています。
   - 事前登録に書く必要はありますか。
3. **塊 20 日の列を出す場所**
   - JSON では、`read_block` を通る全部の差(前半・後半、またぎの日を外した差、G9 の年ごと)に入れました。
   - GATE_READ.md では、主の G3 の差の表の列としてだけ出しています。この出し方でよいですか。
4. **読みの表の 1 行目の文**
   - 1 行目の「(予言 P2・P3 が当たった)」を、A にも B にもそのまま出しています。事前登録では P3 が A、P2 が B の予言です。
   - PREREG.md はリードの持ち物なので、変えていません。A と B で文を分けますか。
5. **[観察] 外す日数が母数と同じとき**
   - dry の 8 日の母数では、A がすべての日を外すので、対照の差は全部、実際の差と同じ値になります。
   - それでも、和を取る順の違いによる丸め誤差のために、G10a の上側の割合が 1.0 でなく 0.143(始値)・0.429(中ほど)になりました。G10b・G10c も、中ほどの約定の A で「実際 > 95 点 はい」が出ました【事実: dry の出力】。
   - 本物の走らせでは外す日数が 1,305・842(1,812 日のうち)なので、これは起きないと見ています【推定: 日数から】。
   - 委任文が「実際」を G3 の値と決めているので、比べの元は変えていません。直すかどうかを決めてください。
6. **[情報] 他の委任先の変更**
   - 試験と壊した写しは、他の委任先がまだコミットしていない `scripts/w4_measure/common.py`・`run_v2.py`・`run_b2.py` が置かれた状態で打ちました。上の結果はその版の上での事実です。

一時置き場(`/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/fix2/`)のファイル:
- `seeds.py`・`real_cls.py`: 3 の作り物の台本
- `make_breaks.py`・`run_breaks.sh`・`brk/`: 4 の壊した写しと試験の記録
- `dry/`・`dry_read/`: 5 の dry の出力
- `orig/`: 直す前の 3 ファイルの写し

---

## リードの検収(2026-10-06)

- 【事実】リードが打った: `PYTHONPATH=src python -m pytest tests/research/test_c8_binance.py` → `39 passed in 40.06s`。
- 【事実】批評家 2 回目が「リードが打って確かめる形に」とした確かめ: 本番の経路がセントで読む assert(試験 529・556 行 `kw.get("cents", True) is True`)、終値の比べが not_computed なら戻り値 4(`bn_run_c8.py` 297 行)、日数の固定(試験 576〜579 行: 1812 / low 842 / low 以外 1305 / 境 2021-06-25)を grep で確かめた。
- 問い 1・2・3・5・6 は報告の形のまま受ける。問い 5 は本物の件数では起きない(除いた数が母数と等しくならない)。
- 問い 4: 読みの表の 1 行目の「予言 P2・P3 が当たった」は事前登録の文を固定した試験があるので文は変えない。報告では A は P3、B は P2 と読み分けて書く。
- 批評家は上限の 2 回に達した。この直しの後に批評家は当てていない(上の確かめはリードが打った)。
