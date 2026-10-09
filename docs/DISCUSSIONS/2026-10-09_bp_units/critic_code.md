# 批評家(作り終えた後): bp の直しのコード(code_diff.patch)

書いた人: 批評家(下位モデル)。2026-10-09。コードは直していない。読まない置き場(`docs/RESEARCH/WINDOW1/`・`backtest_data/phase2_sealed/`)は読んでいない。
オーナーの指示(逐語、L-920): 「**たまたま見つかったやつも含めてわかってる修正が必要なもの全部直してください 方針はbpの意味は「値動き率」としてのみ残し、その他の意味を持たせないようにすること**」。L-923「**2時間を上限にしろ、そうしないと意味不明な試験ばっかりで終わらなくなる**」(試験を足す指摘はしない)。

## 着手前の表

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 差分と直した後のファイルを読み、口座の bp・× 20 の残り、円と値動き率の取り違えを行で挙げる | 「bpの意味は「値動き率」としてのみ残し、その他の意味を持たせないようにすること」 |
| D7 の和集合、カードの枝、D4 の群の名前、その他の壊れた所を指摘する | 「わかってる修正が必要なもの全部直してください」 |
| 試験を足す指摘はしない | 「意味不明な試験ばっかりで終わらなくなる」 |
| この文書に書く(コミットしない) | **(該当語なし)**(リードの委任文の指示) |

完了見込み: 約 20 分(差分と仕様を読む 5 分 + 問いごとの grep と照合 10 分 + 書く 5 分)。

## 指摘

### 問い 1(口座の bp・× 20、円と値動き率の取り違え)

- 1-a [なし・事実] 差分の 11 ファイルでは、損益に「bp」と付けた所と × 20 は残っていない。確かめたコマンドは `grep -n 'bp' scripts/analysis/diag_paths.py | grep -v '値動き率'` で、出力は 0 行。`diag_tables.py` で bp が出るのは :5 の L-920 の引用だけ。`fam_tables.py` の `y()`(:21-22)は円の値にしか使われていない。値動きの値は別の `mv()`(:33-34)が出していて、元々 × 20 していない。
- 1-b [直す] `scripts/analysis/diag_tables.py:28` の docstring に「カードの測定は `daily.csv` の日(日本時間)」が残っている。:99 の `period_days` の docstring にも「card は daily.csv の日」が残っている。今は `daily.csv` を読まずに止めるので(:67-68)、書いてあることが実際の動きと違う。
- 1-c [直す] `scripts/analysis/card_trades.py:17` に「`trades.csv.gz` を書く(`diag_tables.py --run` にそのまま渡せる…)」とある。しかし、この台本が書く列は `pnl_pct`(:126、別の作業者の作業中の変更)で、`diag_tables.load_run` は `pnl_jpy` が無いと止める(diag_tables.py:79-80)。「そのまま渡せる」は今は当たらない。

### 問い 2(D7 の和集合と `d7_fullperiod.py` は同じ値になるか)

[聞く] 6 本のうち 5 本は同じ値になる。count_20 だけ違う(事実。実行した台本と出力は下)。

```
$ python3 scratchpad/cmp2.py   # 読み口と同じ日の決め方(summary.json の period の UTC の日)の和集合 と d7_fullperiod の日(基準の最初〜最後の出の日)で差の平均
base period days 2015-12-01 2023-12-17 2939 | fp days 2015-12-01 2023-12-17 2939
break_len_mult_4   start 2015-12-05 ... union n=2939 mean=+205.4706 | fp n=2939 mean=+205.4706 | 差=+0.0000
count_20           start 2015-11-30 ... union n=2940 mean=-183.7714 | fp n=2939 mean=-185.1735 | 差=+1.4022
count_80           start 2015-12-05 ... union n=2939 mean=-11.4790  | fp n=2939 mean=-11.4790  | 差=+0.0000
foot_5             start 2015-12-02 ... union n=2939 mean=+27.9539  | fp n=2939 mean=+27.9539  | 差=+0.0000
range_hi_p75       start 2015-12-08 ... union n=2939 mean=-88.6509  | fp n=2939 mean=-88.6509  | 差=+0.0000
range_hi_p90       start 2015-12-08 ... union n=2939 mean=-59.3982  | fp n=2939 mean=-59.3982  | 差=+0.0000
$ (count_20 の 2015-11-30 に出た取引) 6 本、和 3937.21 円
```

- 違う本の形: 期間の始まりが基準(2015-12-01)より**早い**本。count_20 の期間は 2015-11-30 から始まる。
- 和集合では 11-30 を入れる(基準 0 円、count_20 の 6 本 +3,937 円)。`d7_fullperiod.py:29-32` は基準の日に `reindex` するので、11-30 の取引を捨てる。
- 終わりの側も同じ形で違いうる(本の最後の出の日が基準の最後の出の日より後なら、`d7_fullperiod` はその日を捨てる)。今の 32 本では、基準の最後の出の日が 2023-12-17 で、period の終わりと同じなので違いは出ていない(事実)。
- 年ごとの 2015 の行と区間も、count_20 では違う。
- FIX_SPEC §1 の「`d7_fullperiod.py` と同じ値になることを試験で確かめる」は、count_20 では当たらない。決めることは 2 つあり、どちらを正にするかはリードが決める(推定: 和集合の方が count_20 の取引を捨てないので、仕様の「取引の無い日を 0 円」に近い)。
  - 和集合を正にする: `d7_fullperiod.out` と、それを写した文書の count_20 の数を直す。
  - 基準の期間を正にする: 読み口を基準の日に揃える。

### 問い 3(`kind == "card"` などの残りの枝)

- 3-a [なし・事実] `load_run` は `kind = "trades"` しか返さない(diag_tables.py:90)。:100-101・:114-115 の `kind == "card"` の枝と、:252-254・:296・:347・:366・:393・:402 の `kind == "trades"` の判定は、今はいつも同じ側に進む。このため読み口の計算は壊れていない。`tests/research/test_diag_tables.py`・`test_diag_paths.py` は通った(`PYTHONPATH=src python -m pytest tests/research/test_diag_tables.py tests/research/test_diag_paths.py` → `17 passed`)。
- 3-b [直す] 枝は死んでいるが残っているので、読む人には「カードの daily.csv も読める」ように見える(1-b と同じ)。`render` の :424(`'—'`)は直してある。
- 3-c [直す] 読み口の外が壊れた。`scripts/analysis/trade_rows.py:31・95` は `diag_tables.load_run(a.run)` を呼ぶ(名前・summary・`period_days` を取るためだけ)。`load_run` は今、`trades.json.gz` と `pnl_jpy` の無い `trades.csv.gz` で止まる。そのため、自分で `pnl_pct`/`pnl_bp`/`trades.json.gz` を読む `trade_rows.load_rows`(:41-57)まで進めず、カードの出力では `trade_rows.py` 全体が動かない。
  - `docs/RESEARCH/cards/*/redo2_2026-10-05/*.py`(`d5_entry_open.py:36`・`c3 d2_volsplit.py:31` ほか)も `dt.load_run` でカードの出力を読む。これらは全捨て後の記録なので直す要は無い(推定)。止まることだけは事実。

### 問い 4(D4 の群の名前を変えたことで、文字で読んでいるコードが壊れたか)

- 4-a [なし・事実] 群の名前を文字で読むコードは無い。`git ls-files -z -- '*.py' '*.sh' '*.js' ':!docs/RESEARCH/WINDOW1' ':!backtest_data/phase2_sealed' | xargs -0 grep -n 'のまま負けた\|だったのに負けた\|有利に動いたのに負けた\|有利に動かずに負けた\|\["groups"\]'` の当たりは次のとおり。
  - `fam_tables.py:113` は `d4["groups"].items()` で回すだけ。
  - `scripts/simple/receive_main.py:45` は見出し「## D4 取引の一生」だけを見る(見出しは変わっていない)。
  - 古い名前を文字で持つのは `docs/RESEARCH/matilda_main/d4_levels_count.py:33`(群の名前を自分で作る調べの記録。L-920 の注が付いていて、今の出力では動かない)と、`d4_position_mfe.py:2` のコメントだけ。
- 4-b [聞く] 名前が FIX_SPEC §1 と違う。仕様は「群の名前に「1 段目の値段に対する」を入れる(例「1 段目の値段に対する MFE > 0 で負けた」)」。コードは「建ての値段から一度は有利に動いたのに負けた」(diag_paths.py:145・150)にしている。
  - 2 段以上建つマチルダでは、「建ての値段」は持ち高の平均の値段とも読める。仕様が避けようとした取り違えがそのまま残る。
  - 同じ差分の中でも呼び方が 3 通りある: `fam_tables.py:105` の見出しは「1 段目の約定の値段に対する」、`diag_paths.py:8` の docstring は「entry_price(マチルダは 1 段目の約定の値段…)」、群の名前は「建ての値段」。
  - 文書の直し(段 5)の「1 段目の値段から見て」と、`ledger_rows_foot.py:13-15`・`ledger_rows_count.py:26` の「1 段目の約定の値段から見て」とも、出力の群の名前が合わない。
  - `.claude/skills/analysis-lens/SKILL.md:193-194` は古い名前のまま(段 5 の範囲)。
  - 作り直した `diag_paths.json`(`docs/RESEARCH/matilda_main/*/diag_paths.json` は今は古い名前)を引く文書がこの名前を写すときに、ずれが出る。

### 問い 5(その他、意味が変わった・壊れた所)

- 5-a [直す] D7 の前半・後半は、まだ共通の日(積集合)で計算している。全期間は和集合なので、同じ表の同じ行で日の取り方が違う。
  - `docs/RESEARCH/matilda_main/fam_tables.py:137-142`: `common = sorted(set(rd) & set(bd))`。全期間の欄は `d7["all"]`(和集合)、前半・後半の欄は `common`(積集合)。見出し :134 も「同じ日どうしの日ごとの差」のまま。
  - `docs/RESEARCH/matilda_main/both_halves.py:13`(`c = sorted(set(rd) & set(bd))`)、docstring :1 の「同じ日どうし」。
  - `docs/RESEARCH/matilda_main/half_diff.py:24-25`(`days = sorted(set(d) & set(base))`、`h = len(days) // 2`)。期間の始まりが遅い 5 本では、日の数が変わるので前半と後半の境の日もずれる。
  - 仕様 §1 の D7 の直しの理由(基準だけの日が落ちる)は、この 3 か所にもそのまま当たる。
- 5-b [直す] `diag_paths.py --blocked-from` は `read_trades_csv(a.blocked_from)`(:229)で `r["pnl_jpy"]` を読む(:99)。`pnl_jpy` が無い相手を渡すと、止める文を出さずに `KeyError` で落ちる。FIX_SPEC §0「黙って受けずに止める(止める文で、何が来たか・何を渡せばよいかを言う)」の形になっていない。`--run` の側は先に `dt.load_run` が止める文を出すので当たらない。
- 5-c [聞く・事実] `simple_trades.py` は summary.json から `all.sum_bp`・`pnl_bp_def` を消した。これを読む `trade_rows.py:112` は、`sum_pct` も `sum_bp` も無いと「無し」と出す。マチルダの出力を `trade_rows.py`/`batch_runs.py` に通す経路は、`scripts/simple`・`batch_tables.sh`・`delegated-study` の SKILL を grep して見つからなかった(`grep -rn 'trade_rows\|batch_runs' scripts/simple docs/RESEARCH/matilda_main/*.sh .claude/skills/delegated-study/SKILL.md` → 0 行)。今は壊れていない。ただし `trade_rows.load_rows`(:47)は `pnl_pct` か `pnl_bp` を前提にしていて、新しいマチルダの行(`pnl_jpy` だけ)では `KeyError` になる。読む口が円と % の 2 系統に分かれた。
- 5-d [聞く・事実] 作り直しの途中で、出力が混ざっている。`backtest_runs_shared/matilda_main_trades/*/summary.json` は 9 本が `sum_bp` 無し(新)、23 本が `sum_bp`・`pnl_bp_def` 有り(旧)。`foot_5/trades.csv.gz` の頭の行には、まだ `pnl_bp` がある。読み口は `pnl_jpy` だけを読むので値は同じになるはずだが、段 4 の終わりの機械の突き合わせは全 32 本が新しくなってから掛けること(推定)。
