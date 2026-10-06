# 直し 1 の委任の報告(逐語、2026-10-06)

委任文: `DELEGATION_fix1.md`。

リードの受け取り: 問い 6 の 1〜6 は報告の形のまま受ける。7 は事前登録の読み方の決まりの範囲を G0〜G10 に直した。3(G10 の外す日数が事前登録の 1,305・842 と一致するか)は走らせの後に台本の出力で確かめて報告に書く。

委任文 DELEGATION_fix1.md の 5 項目をすべて直しました。試験は失敗なしです。壊し方は、批評家の 6 通りも新しい試験の分もすべて試験で落ちます。カード 8 は本物の足で回していません(`--dry` だけ)。コミット・押し出しはしていません。

## 1. 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 足の口で値段を整数のセントにし、診断・docstring・平らな区間の試験を直す | (オーナーの逐語なし)委任文「値段 = 平均のときの持ち高(批評家の問 1)」 |
| 試験で事前登録の値を固定し、壊し方 6 通りを一時置き場の写しで確かめる | (オーナーの逐語なし)委任文「試験で事前登録の値を固定する(批評家の問 3)」 |
| G9 年ごとの表と試験 | (オーナーの逐語なし)委任文「G9 年ごとの表」 |
| G10 対照群と試験 | (オーナーの逐語なし)委任文「G10 対照群(補助帰無)」 |
| `.gitignore` に `run.npz` を足し、`check-ignore` で確かめる | (オーナーの逐語なし)委任文「`run.npz` を git の無視に当てる」 |
| 測り全体の目的 | L-714「**yes**」/ L-715「**Binance の 1 分足(推し)**」「**A と B の両方(推し)**」 |
| `bn_split` は値段を USDT のまま読む / G10 の外し方の細部 / 取引の記録の値段の単位 | **(該当語なし)** → 6 に問いとして書きました。作業を止めずに、いちばん文字どおりの形で実装してあります |

## 2. 直したことごとの置き場と差分の要約

**直し 1: 整数のセント**
- `/home/user/trade/scripts/w4_measure/c8_binance/bn_bars.py`
  - `to_cents()` を足しました。始値・高値・安値・終値を `round(値段 × 100)` にします。
  - `load_chunk`・`iter_range` は `cents=True` を既定にしました。事実の記録に `price_unit` と `n_not_whole_cent`(整数のセントから外れていた値段の数)を出します。
  - 「単位は持ち高にも損益の bp にも効かない」と書いていた docstring を、事実どおりに書き直しました。損益の bp は単位に依らないこと、平らな区間では浮動小数の値段だと持ち高が ±1 になることを書いています。
- `/home/user/trade/scripts/w4_measure/c8_binance/bn_run_c8.py`
  - `close_eq_mean()` を足し、`run_record.json` に「終値 = 平均だった決定の数」を出します。整数の和で正確に比べ、内訳(セッションの最初の足 / 終わりの足 / それ以外)と「等しかったのに持ち高 ≠ 0 の数」も出します。
  - `price_unit` を `run_record.json` に書くようにしました。`trades.json.gz` の値段だけは USDT に戻します(÷100)。
  - 作り物の足に平らな区間を作る `flat=` を足しました。`--dry` の作り物の足は値段を 3 万 USDT 台に寄せ、セッションの最初の 60 本を平らにし、セントにしてから回します。
- `/home/user/trade/scripts/w4_measure/c8_binance/bn_split.py`: `iter_range(..., cents=False)` で USDT のまま読みます(理由は 6 の問い (1))。

**直し 3・4: G9・G10**
- `/home/user/trade/scripts/w4_measure/c8_binance/bn_read_gate.py`
  - docstring に G9・G10 を足しました。
  - G9 は `by_year()` です。年ごとに A − 門なし・B − 門なし(区間・MDE・印)と、区分ごとの門なし(区間・日数)を、始値と中ほどの両方で出します。
  - G10 は `placebo_removed()`・`placebo_masks()`・`placebo_compare()`・`placebo()` です。種 20261007、1,000 回、5 日の塊を循環で取り、最後の塊は外す日数ちょうどで切ります。出すのは、上側の割合(≥)、対照群の 95 点、実際の差が 95 点を超えたか、対照群の平均・標準偏差、外した日数が全回でちょうど同じだったか、です。
  - `GATE_READ.md` に G9 と G10 の表を足しました。

**直し 2 と試験**
- `/home/user/trade/tests/research/test_c8_binance.py` に足した試験:
  - 平らな区間(35698.72 と 11868.04): 浮動小数のままなら 0 でない持ち高が出ること(この試験が空振りしていないことの確かめ)、整数のセントなら全部 0 になること。
  - 同じ値段の無い足では、セントでも USDT でも持ち高と損益が同じこと。
  - `n_not_whole_cent` の数え方。
  - `HI == iso("2023-12-17T15:00:00Z")`。
  - 日数が偶数(6 日)のときの前半・後半の境。
  - 区間が `block_bootstrap_ci(x, block_len=5, n_resamples=1000, seed=20261006, method="circular")` と一致すること。比べる相手は台本の定数ではなく、数を直に書いた呼び出しです。
  - `mark` で区間の端がちょうど 0 のとき「0 を含む」になること。
  - G9 を手で計算した値(2 年分、始値と中ほど)。
  - G10:
    - 別に書いた参照の実装との一致(種 20261007・1,000 回・塊 5 を直に書いた)
    - 外した日数がちょうど m で、塊が循環していること
    - 上側の割合が同じ値を数えること(≥)
    - 区分が損益と無関係なら上側の割合がおおむね一様
    - 区分が損益を決めるなら 0.01 以下
  - 既にあった試験も、セントの足を通すように直しました。

**直し 5**
- `/home/user/trade/.gitignore` の 84 行目に `docs/RESEARCH/cards/c8_session_mean_revert/binance_gate/measure/*/run.npz` を足しました。確かめた結果:
  ```
  $ git check-ignore -v --non-matching .../binance_gate/measure/jst_day/run.npz .../measure/jst_day/daily.csv
  .gitignore:84:docs/RESEARCH/cards/c8_session_mean_revert/binance_gate/measure/*/run.npz	.../jst_day/run.npz
  ::	.../jst_day/daily.csv
  $ git ls-files docs/RESEARCH/cards/c8_session_mean_revert/binance_gate | git check-ignore --stdin --no-index
  (出力なし、rc=1)
  ```
- 50 MB を超えそうな出力【推定】: `run.npz` だけです。`--dry` の作り物の足は 10,075 本で 205,892 B でした。全期間は 2,313 日 × 1,440 = 3,330,720 本で、比例で約 68 MB になります。本物の足の圧縮のされ方は未確認です。そのほかは `trades.json.gz` が約 1.1 MB、`daily.csv` は日数に比例して約 0.1 MB です。`daily_stats.json`・`run_record.json` は大きさがほぼ一定です。

**その他**
- モデル名の確かめ: `git diff -- scripts tests .gitignore | grep -inE '^\+.*(opus|claude|sonnet|haiku|gpt)'` の出力は無し(rc=1)【事実】。
- `docs/AUDITOR/TRACE/2026-10-06_220780c0.json` の変更はフックが書く記録です(`"Bash": 3 → 5` など)。私は書き換えていません【事実】。

## 3. 試験の結果

```
$ PYTHONPATH=src python -m pytest tests/research/test_c8_binance.py
..........................                                               [100%]
26 passed in 16.52s
$ PYTHONPATH=src python -m pytest tests/research
1197 passed, 3 skipped in 437.93s (0:07:17)
```

## 4. 壊し方が試験で落ちるか(一時置き場の写し。元のファイルは変えていない)

手順は、`scripts/w4_measure/c8_binance/` と試験を `/tmp/claude-0/-home-user-trade/220780c0-d897-5de0-a902-2af69538ba02/scratchpad/brk/case/` に写し、1 通りずつ壊して写しの試験を打つ、です。道具は `.../scratchpad/brk_tool/breakage.py` です。壊す前の写しは失敗なしで通りました【事実】。

| 壊し方 | 結果(落ちた試験) |
|---|---|
| 批評家 1: `BLOCK = 5` → `1` | 落ちた(test_interval_matches_prereg_values) |
| 批評家 2: `SEED` → `1` | 落ちた(同上) |
| 批評家 3: `circular` → `moving` | 落ちた(同上) |
| 批評家 4: `HI` を 15:00Z → 16:00Z | 落ちた(test_prereg_hi_fixed) |
| 批評家 5: 前半・後半の境を `ds[(len-1)//2]` に | 落ちた(test_half_boundary_even_number_of_days) |
| 批評家 6: `mark` の `lo > 0` → `lo >= 0` | 落ちた(test_interval_matches_prereg_values) |
| 批評家 7: またぎの日を出の足の日にする | 落ちた(test_run_outputs_carry_and_mid) |
| 批評家 8: またぎの日を外さない | 落ちた(test_carry_days_removed_from_diffs ほか) |
| 新 1: セントにしない | 落ちた(平らな区間の試験 2 本ほか 5 本) |
| 新 2: ×100 だけで丸めない | 落ちた(平らな区間 35698.72・同値無しの比べ ほか) |
| 新 3: `load_chunk` でセントにしない | 落ちた(test_loader_drops_…) |
| 新 4: `close_eq_mean` をセッションで区切らずに足す | 落ちた(test_run_outputs_carry_and_mid) |
| 新 5: 取引の記録の値段を USDT に戻さない | 落ちた(test_run_outputs_carry_and_mid) |
| 新 6: G9 を年で分けない | 落ちた(test_g9_by_year_hand_numbers) |
| 新 7: G10 の種 → 1 | 落ちた(test_g10_placebo_matches_reference…) |
| 新 8: G10 の塊 5 → 1 | 落ちた(参照の実装との一致・循環の試験) |
| 新 9: G10 の回数 1000 → 999 | 落ちた(参照の実装との一致) |
| 新 10: G10 の 95 点 → 90 点 | 落ちた(同上) |
| 新 11: G10 の ≥ → > | 落ちた(test_g10_upper_share_counts_ties) |
| 新 12: G10 で最後の塊を切らない | 落ちた(ちょうどの数・参照の実装・同じ値の試験) |
| 新 13: G10 で循環しない | 落ちた(循環の試験・参照の実装) |
| 新 14: G10 の A の外す日数を low の数にする | 落ちた(参照の実装・同じ値の試験) |
| (外した壊し方 1)`close_eq_mean` を浮動小数の比べに変える | 通った。値段が整数なら浮動小数の和も正確なので、中身が同じ書き換えで、壊し方になっていなかった。新 4 に置き換えた |
| (外した壊し方 2)中ほどで外し方を毎回作り直す(`if True:`) | 通った。同じ種から作り直すので同じ外し方になり、中身が同じ書き換えだった。外した |

一様かどうかの試験は、平均と両端の割合で粗く見ているだけです。分布の検定ではありません【事実】。

## 5. `--dry` の結果

`PYTHONPATH=src python3 scripts/w4_measure/c8_binance/bn_run_c8.py --dry --out-root <scratchpad>/dry` → exit=0。

- **本物の足の読み(カードは回していない)**
  - 2019-01-01〜01-08 の 10,080 本、`sealed_unit "P2-08"` です。
  - `price_unit "0.01 USDT(整数のセント…)"`、`n_not_whole_cent: 0` でした。最初の足は `[370123.0, 370372.0, 370109.0, 370246.0]` です。
  - 0.01 USDT 刻みであることは、この 7 日分についてだけの事実です。ほかの年は未確認です。
- **作り物の足**
  - 9 ファイルができました。大きさは `run.npz` 205,892 B、`trades.json.gz` 3,473 B ほかです。
  - `boundary_carry_check.same: true` でした。
  - `close_eq_mean` は `n_close_eq_mean 67 = 最初の足 8 + 終わりの足 0 + それ以外 59`、`n_nonzero_exposure_at_eq: 0`、`sum_exact_in_card: true` でした。
  - 「それ以外 59」は、平らにした 60 本のうち最初の足を除いた 59 本で、どれも持ち高 0 です【事実】。

## 6. 決めきれなかったこと(問い)

いずれも下に書いた形で実装済みで、あとから戻せます。

1. **`bn_split` を `cents=False`(USDT のまま)で読むことにしてよいか。** コミット済みの `split/classes.json` と同じ入力にするためです。セントに丸めると浮動小数の末の桁が変わり、分位の境の日が動きうるからです【推定】。
2. **G10 の外し方はこれでよいか。**
   - 今の形: 始めの番号を一様に引き(重なりを許す)、塊の中のまだ外していない日を順に外し、m に届いたところで最後の塊を切る。
   - 別の形: でたらめにずらした位置から重ならない 5 日の塊に切り分け、塊を並べ替えて外していく。
3. **G10 の外す日数 m の数え方。** G0 の母数(`daily.csv` に行のある区分の日)の中で数えています。事前登録の 1,305 日・842 日と一致するのは、区分のある日すべてに `daily.csv` の行があるときだけです。
4. **G10 の細部。**
   - 乱数は形(A・B)ごとに `default_rng(20261007)` を新しく作ります。
   - 始値と中ほどには同じ外し方を当てます。
   - 上側の割合は「実際の差以上(≥)」で数えます。
   - 95 点は `np.quantile` の既定(線形補間)です。
5. **取引の記録の値段を USDT に戻した(÷100)こと**、`price_unit` を `run_record.json` に足したこと、`--dry` の作り物の足を 3 万 USDT 台・平らな区間つきに変えたこと。この 3 つは委任文に無い判断です。
6. **G9 の年は、母数の日付の先頭 4 文字から作っています**(2019〜2023 と書き込んではいません)。
7. **`PREREG.md` 30 行目が「G0〜G8(と走らせる前に足す G9)」のままです。** 台本の docstring は G0〜G10 になりました。`PREREG.md` は委任されていないので直していません。リードが直すかどうかを決めてください。
