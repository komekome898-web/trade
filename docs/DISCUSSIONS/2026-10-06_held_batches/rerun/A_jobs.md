# 走らせ直しの一覧 — 担当 A(カード 1・2・3・6)、24 本

出所: 委任文 `docs/DISCUSSIONS/2026-10-06_held_batches/DELEGATION_rerun_impl.md`(担当 A)。オーナーの逐語: L-717「**走らせ直し 27 本 … これ全部開始していいです。できる作業は並列 測定は別のセッション**」/ L-718「**各束 1 周**」。

## 打つ人への約束(測定用のセッション)

- **前提**: 下のコマンドは担当 A の台本の直し(`scripts/w4_measure/run_v2.py`・`run_b2.py`・`common.py`・`rerun_check.py`、試験 `tests/research/test_w4_rerun_cols.py`)が取り込まれた checkout でだけ動く。この一覧を書いた時点では未コミット。取り込んだコミット: (リードが書く)。
- **1 本ごとの順**(リードの決め 2026-10-06): ① 走らせる(`run.npz`・`daily.csv`・`run_record.json`)→ ② `rerun_check.py` で確かめと小さな出力(`trades.csv.gz`、カード 2 は `signals.csv.gz`、`rerun_check.json`)を作る → ③ ② が 0 を返したときだけ `run.npz` を消す。npz は同時に打っている本数分しか残らないので、測定用のセッションの空きは「npz 1 本 約 50〜110MB × 同時の本数」で足りる【推定: 下の「大きさの見込み」】。② が 3 を返したら `run.npz` を消さずに残して止める(調べるため)。
- **git に入れるもの**: 各出力先の `daily.csv`・`run_record.json`・`rerun_check.json`・`trades.csv.gz`・(カード 2)`signals.csv.gz`・(カード 3)`daily_lag1.csv`・`positions.npz`・(カード 6)`daily_stats.json`・`extra.json`・`diagnostics.json`・`*.log`。**`run.npz` はコミットしない**(`.gitignore` に `docs/RESEARCH/cards/*/rerun_2026-10-06/**/run.npz` をリードが足す)。高値・安値は npz にだけ残る(経路は分析の側で 1 分足から読む。リードの決め)。
- **終わる条件**: 下の 24 本すべてで、上の git に入れるものがそろい、`rerun_check.py` の終わりの値が 0。A01〜A22(カード 1・2・3)は `--require-identical` を付けるので、0 は「`daily.csv` の sha256 が元と同じ(日の数・最後の日を含む)」を含む。A23・A24(カード 6 の延長)は付けない(元の最後の日 2022-12-31 を除いた突き合わせ。批評家 1 回目へのリードの応答)。
- **上限**: 1 周(L-718)。1 本が見込みの 2 倍を超えたら止めて記録する。`rerun_check.py` が 3 を返したら、そのカードの残りを打たずに止め、`rerun_check.json` をリードに返す(元の走らせが再現できていないので、足した列も読まない)。 **ただし A02(カード 2 の a_1m)は元の走らせが別の台本(全期間を一度に読む)なので、カード 2 は A03〜A19 を先に打ち、A02 を最後に打つ。A02 が 3 を返しても A02 だけを止めて記録する**(批評家 2 回目の [直すとよい]、リードの決め 2026-10-06)。
- 同時は最大 3 本(前の回の記憶の扱い。各 `measure/README.md`「並列」)。読むのは封印の門(`bot.bt.data` の load / load_reference)だけ。期間の終わりはどれも 2023-12-17T15:00Z 以前。
- 全部リポジトリの直下で打つ。`run_v2.py` は **`--no-measure` の経路だけを使う**(`--extra-cols` は `--no-measure` と `--save-root` と一緒のときだけ動き、元の置き場 `measure/<変種>/` には書かない)。`run_v2.py` の測定の経路・`--light` の経路はカード 2・3 で、リポジトリに無い `run_c2`・`run_c3` を読むので動かない(範囲の外。触っていない)。
- **カード 6 の注**: 2023 年の USDJPY のファイル `backtest_data/fx_usdjpy_1m_20260822.csv.gz` は、カード 6 の CARD.md の「使うデータ」に無い。`check_card` はこのファイルを見ない(CARD.md は変えない。リードの決め)。読むのは `run_b2.py --usdjpy-2023` の中の封印の門(`load_reference`)だけ。

## 一覧(1 行 = 1 本)

見込みの時間 = 前の回の「区切りの run_card(読み込みを含む)」の秒【事実: 各 `measure/README.md` の表】。足すもの(npz の保存・daily.csv・確かめ・取引の行)は 1 本あたり数十秒〜数分【推定: 短い期間の確かめでは数秒。全期間は未確認】。

| # | カード | 変種 | 期間 | 出力先(`docs/RESEARCH/cards/` の下) | 元の置き場 | 見込み(秒) |
|---|---|---|---|---|---|---|
| A01 | 1 | default | 2017-08-17T15Z〜2023-12-17T15Z | `c1_xborder_mom/rerun_2026-10-06/default/` | `c1_xborder_mom/measure/default` | 1,154 |
| A02 | 2 | a_1m | 同上 | `c2_owner_xvenue_wick/rerun_2026-10-06/a_1m/` | `c2_owner_xvenue_wick/measure/a_1m` | 約 1,900【推定: 前の回は別の台本(全期間を一度に読む)で 502 + 1,079。区切りで読むほかの a の 5 本と同じ桁と見た】 |
| A03 | 2 | a_3m | 同上 | `…/rerun_2026-10-06/a_3m/` | `…/measure/a_3m` | 1,879 |
| A04 | 2 | a_5m | 同上 | `…/rerun_2026-10-06/a_5m/` | `…/measure/a_5m` | 1,814 |
| A05 | 2 | a_15m | 同上 | `…/rerun_2026-10-06/a_15m/` | `…/measure/a_15m` | 1,872 |
| A06 | 2 | a_30m | 同上 | `…/rerun_2026-10-06/a_30m/` | `…/measure/a_30m` | 1,861 |
| A07 | 2 | a_60m | 同上 | `…/rerun_2026-10-06/a_60m/` | `…/measure/a_60m` | 1,888 |
| A08 | 2 | b_1m | 2020-01-01T15Z〜2023-12-17T15Z | `…/rerun_2026-10-06/b_1m/` | `…/measure/b_1m` | 1,103 |
| A09 | 2 | b_3m | 同上 | `…/rerun_2026-10-06/b_3m/` | `…/measure/b_3m` | 1,106 |
| A10 | 2 | b_5m | 同上 | `…/rerun_2026-10-06/b_5m/` | `…/measure/b_5m` | 1,106 |
| A11 | 2 | b_15m | 同上 | `…/rerun_2026-10-06/b_15m/` | `…/measure/b_15m` | 1,010 |
| A12 | 2 | b_30m | 同上 | `…/rerun_2026-10-06/b_30m/` | `…/measure/b_30m` | 955 |
| A13 | 2 | b_60m | 同上 | `…/rerun_2026-10-06/b_60m/` | `…/measure/b_60m` | 999 |
| A14 | 2 | c_1m | 2017-08-17T15Z〜2021-12-31T15Z | `…/rerun_2026-10-06/c_1m/` | `…/measure/c_1m` | 1,214 |
| A15 | 2 | c_3m | 同上 | `…/rerun_2026-10-06/c_3m/` | `…/measure/c_3m` | 1,272 |
| A16 | 2 | c_5m | 同上 | `…/rerun_2026-10-06/c_5m/` | `…/measure/c_5m` | 1,100 |
| A17 | 2 | c_15m | 同上 | `…/rerun_2026-10-06/c_15m/` | `…/measure/c_15m` | 1,250 |
| A18 | 2 | c_30m | 同上 | `…/rerun_2026-10-06/c_30m/` | `…/measure/c_30m` | 1,104 |
| A19 | 2 | c_60m | 同上 | `…/rerun_2026-10-06/c_60m/` | `…/measure/c_60m` | 1,075 |
| A20 | 3 | 1h | 2017-08-17T15Z〜2022-12-31T15Z | `c3_yen_premium_revert/rerun_2026-10-06/1h/` | `c3_yen_premium_revert/measure/1h` | 1,084 |
| A21 | 3 | 1d | 同上 | `…/rerun_2026-10-06/1d/` | `…/measure/1d` | 1,073 |
| A22 | 3 | 1w | 同上 | `…/rerun_2026-10-06/1w/` | `…/measure/1w` | 1,087 |
| A23 | 6 | btc(延長) | 2017-08-01T15Z〜**2023-12-17T15Z** | `c6_weekend_gap_revert/rerun_2026-10-06/ext_2023-12-17/btc/` | `c6_weekend_gap_revert/measure/btc` | 約 800【推定: 前の回 678 × 日数の比 2,329 ÷ 1,978】 |
| A24 | 6 | usdjpy(延長) | 同上 | `…/rerun_2026-10-06/ext_2023-12-17/usdjpy/` | `…/measure/usdjpy` | 約 800【推定: 同上(前の回 678.7)】 |

合計 約 30,500 秒(約 8.5 時間)を 1 本ずつ、3 本同時なら約 3 時間【推定: 上の表の和】。

## コマンド(行の番号ごと。そのまま打てる形)

```sh
# 共通: 置き場の頭
C1=docs/RESEARCH/cards/c1_xborder_mom
C2=docs/RESEARCH/cards/c2_owner_xvenue_wick
C3=docs/RESEARCH/cards/c3_yen_premium_revert
C6=docs/RESEARCH/cards/c6_weekend_gap_revert

# A01
mkdir -p $C1/rerun_2026-10-06/default && PYTHONPATH=src python3 scripts/w4_measure/run_v2.py --card c1 --extra-cols --no-measure --save-root $C1/rerun_2026-10-06/default > $C1/rerun_2026-10-06/default/run.log 2>&1 && PYTHONPATH=src python3 scripts/w4_measure/rerun_check.py --dir $C1/rerun_2026-10-06/default --orig $C1/measure/default --require-identical > $C1/rerun_2026-10-06/default/check.log 2>&1 && rm $C1/rerun_2026-10-06/default/run.npz

# A02〜A19(V = a b c、F = 1 3 5 15 30 60 の 18 本。1 行 = 1 本。例は A02 = a_1m)
V=a F=1; D=$C2/rerun_2026-10-06/${V}_${F}m; mkdir -p $D && PYTHONPATH=src python3 scripts/w4_measure/run_v2.py --card c2 --variant $V --foot $F --extra-cols --no-measure --save-root $D > $D/run.log 2>&1 && PYTHONPATH=src python3 scripts/w4_measure/rerun_check.py --dir $D --orig $C2/measure/${V}_${F}m --require-identical > $D/check.log 2>&1 && rm $D/run.npz
# A03 は V=a F=3、A04 は V=a F=5、A05 は V=a F=15、A06 は V=a F=30、A07 は V=a F=60、
# A08〜A13 は V=b F=1/3/5/15/30/60、A14〜A19 は V=c F=1/3/5/15/30/60(期間は台本の C2_VARIANTS の既定。--start・--end は渡さない)

# A20〜A22(W = 1h 1d 1w。例は A20)
W=1h; D=$C3/rerun_2026-10-06/$W; mkdir -p $D && PYTHONPATH=src python3 scripts/w4_measure/run_v2.py --card c3 --window $W --extra-cols --no-measure --save-root $D > $D/run.log 2>&1 && PYTHONPATH=src python3 scripts/w4_measure/rerun_check.py --dir $D --orig $C3/measure/$W --require-identical > $D/check.log 2>&1 && rm $D/run.npz

# A23・A24(V = btc usdjpy。例は A23)
V=btc; R=$C6/rerun_2026-10-06/ext_2023-12-17; mkdir -p $R && PYTHONPATH=src python3 scripts/w4_measure/run_b2.py --card c6 --variant $V --end 2023-12-17T15:00:00Z --usdjpy-2023 --out-root $R > $R/$V.run.log 2>&1 && PYTHONPATH=src python3 scripts/w4_measure/rerun_check.py --dir $R/$V --orig $C6/measure/$V > $R/$V.check.log 2>&1 && rm $R/$V/run.npz
```

## 何が出るか

| 出力 | 中身 |
|---|---|
| `run.npz`(カード 1・2・3。② の後に消す) | 今までの 7 列(end_ns・start_ns・open・close・volume・decided・exposure)+ **high・low**。カード 2 は signal_log(足の終わり ns, 向き, 19 の枝, 24 の枝)+ **signal_color**(+1 陽線 / −1 陰線)・**signal_strong**(色 = 向き。陽線 × 買い・陰線 × 売り が強い)。カード 3 は今までの ov_time・ov_value・fx_time・fx_value も |
| `run.npz`(カード 6。② の後に消す) | `run_b2.py` の今までの形(open・high・low・close・exposure・decided・end_ns・start_ns・volume)。違いは期間と USDJPY の 2023 年の置き場だけ |
| `daily.csv` | 日本時間の日ごとの P の和(測定器の `daily_rows`・`write_daily`)。カード 6 は `run_b2.py` の今までの測定(`daily_stats.json`・`extra.json`・`diagnostics.json`)も出る |
| `run_record.json` | 引数・期間・区切り・読んだファイルの sha256・所要・npz の列 |
| `rerun_check.json` | 元の走らせの再現(下)・足した列の意味の確かめ・取引の行と合図の行の確かめ |
| `trades.csv.gz` | 取引の行(signal_t・entry_t・exit_t・side・pnl_bp)。既にある読み口 `scripts/analysis/card_trades.py` の `build`・`write_trades` を import して `run.npz` から作る(取引 = 持ち高の符号が同じで 0 でない決定がつながった区間)。確かめ: card_trades が決定の日ごとに計算し直した和 = `daily.csv`、取引の和 = `daily.csv` の和(小数 6 桁の丸めの分だけ許す)。取引を合図の日に寄せた日ごとの和は、日本時間の 0 時をまたいだ取引の日で `daily.csv` と合わないのが正しい(数だけ `rerun_check.json` に書く) |
| `daily_lag1.csv`(カード 3) | 持ち高を 1 本遅らせた損益の日本時間の日ごとの和(day・pnl_bp・n)。P1_t = e_t × (open_{t+3} / open_{t+2} − 1) × 10,000、t+k = t の後の k 本目の空でない足(`rerun_check.lag1_pnl`)。日は `daily.csv` と同じく決定の時刻の日。カード 3 の D10 次の手 2(跳ねか遅い戻りか)のため、`run.npz` を消す前に書く |
| `positions.npz`(カード 3) | 決定の足の持ち高: `t_end_min`(足の終わり ÷ 60 秒、int32)・`e`(float32、元との差の最大 約 3e-8【事実: 短い確かめ】)。カード 3 の持ち高は連続の値(e = 1 − 2q)で、取引の行から作り直せないため |
| `signals.csv.gz`(カード 2) | 合図 1 つ = 1 行(signal_t = 海外の足の終わり・side・signal_color・signal_strong)。並びは signal_log のまま。行の数 = signal_log の行の数を確かめる |

**再現の見込み**: カード 1・2・3 は元と同じ期間なので、`daily.csv` の sha256 が元と同じ(`"identical": true`)になるはず【推定: 決定的な走らせ。短い期間の確かめでは、最後の日を除いて全部の日が同じだった】。カード 6 は期間を延ばすので、元の最後の日(2022-12-31)を除いた 1,977 日が同じで、2023-01-01〜2023-12-17 の日が足される形になるはず【推定】。カード 2 の a_1m は前の回が別の台本(全期間を一度に読んで区切りで run_card)なので、全部同じかは未確認(短い期間では同じだった)。

## 大きさの見込み

- `run.npz`(消すもの): 短い期間の確かめの npz の大きさ ÷ 足の数 × 全期間の足の数【推定】で、カード 1 約 85MB、カード 2 a 約 86MB・b 約 51MB・c 約 61MB、カード 3 約 112MB、カード 6 約 92MB。前の回のカード 6 の `measure/btc/run.npz` は 76,779,169 バイト(5.4 年)【事実: `ls -la`】。
- `positions.npz`(カード 3、git に入れるもの): 短い期間(14 日、決定 20,526)の確かめで 1h 52,547・1w 64,325 バイト【事実】。全期間(決定 約 2,793,408)は 1 本 約 7〜9MB、3 本で 約 25MB【推定: 決定の数に比例と見た】。`daily_lag1.csv` は 1 本 約 80KB【推定: 1,962 行】。
- `trades.csv.gz`(git に入れるもの): 短い期間(14 日)の確かめで カード 1 8,845 バイト、カード 2 2,297〜4,084 バイト、カード 3 1h 45,750・1d 21,473・1w 10,222 バイト【事実】。全期間はその日数倍で、カード 3 1h 約 6MB、ほかは 0.2〜3MB【推定: 比例と見た】。`signals.csv.gz` は 14 日で 1,313〜2,718 バイト【事実】、全期間で 0.2〜0.5MB【推定】。
