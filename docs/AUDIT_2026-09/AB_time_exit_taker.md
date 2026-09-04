# AB: 時間による出口緩和はtakerの別名 (short scale = long scale) -- L16 の再検証

監査対象claim: L16 (00_packets.md sec1.2)。5秒スケール実質taker執行の損失(-7〜-15bps/回)と
40分スケール値幅損失が同一メカニズム(taker化)であるという法則の再導出。

## 1. データ・母集団
- board_round_series_5s.csv.gz: n_bins=249336, bin=5s, 期間 2026-08-20T06:13:20Z ～ 2026-09-04T12:50:50Z (約15日)
- 欠測bin=14635 (5.5%), >60s gap=45件(最大2件は長時間ダウン)
- 受動エントリー試行: stride=60bar(300秒)ごとに 4147 candidate点。共通地平線COMMON_H=2700s窓が
  gap>60sまたはbitFlyerメンテ窓(19:00-19:12 UTC、余裕込み)に触れる点は除外。
- 有効試行数(妥当性フィルタ後) n=3749 、実カレンダー日数=16
- モデル: 各試行時刻iでBUYとSELL両方を同時にシミュレート(同一時点・対称)。best価格に指値、
  キュー先頭=既存best板厚(最後尾着席=最保守)、対向テイカー出来高(vol_buy/vol_sell)が累積でキューを消化したら約定。
  cap内未約定→cap到達時にtaker成行(spread/2+slippage 1.0bps+fee 0.0bps)。
  P&L指標 = sign*(mid[i+2700s] − 執行価格)/執行価格 ×1e4 (bps)。全capで同一の共通地平線に対して測定(cap間を公平比較)。
  symmetric_bps = (buy_total_bps + sell_total_bps)/2 は方向性ドリフトを打ち消す一次指標。

## 2. ヘッドライン結果 (queue_frac=1.0, 最後尾着席=保守)

| cap | taker_share(mean) | symmetric_bps mean | 95%CI(day-cluster boot) | n_days |
|---|---|---|---|---|
| 5s | 76.8% | -1.21 | [-1.27, -1.15] | 16 |
| 60s | 12.2% | 0.51 | [0.34, 0.66] | 16 |
| 300s | 0.3% | 0.93 | [0.85, 1.01] | 16 |
| 2400s | 0.0% | 0.94 | [0.88, 1.01] | 16 |

### taker脚の実現コスト(強制taker化した試行のみ、drift抜きの純執行コスト)
| cap | 平均taker脚コスト(bps, buy+sell計) | n(強制) |
|---|---|---|
| 5s | 1.90 | 5757 |
| 60s | 1.77 | 915 |
| 300s | 1.63 | 26 |
| 2400s | nan | 0 |

(参考: 指示コスト前提 spread≈1.9bps, slippage≈1bps/side, fee=0% → 半スプレッド+slip想定=1.95bps。
 データ実測spread_bps: 無効bar除外後 平均=1.88bps / 中央値=1.77bps。
 (除外前の単純平均は-12.51bpsで、後述のsentinel外れ値により大きく歪む。)

## 3. 頑健性: キュー位置感度 (queue_frac=0.5, 中位着席)
| cap | taker_share | symmetric_bps mean | 95%CI |
|---|---|---|---|
| 5s | 72.2% | -1.07 | [-1.15, -0.98] |
| 60s | 9.2% | 0.62 | [0.46, 0.77] |
| 300s | 0.2% | 0.94 | [0.86, 1.01] |
| 2400s | 0.0% | 0.94 | [0.88, 1.01] |

## 3b. データ健全性(Q6): 再接続グリッチ
board_round_series_5s に spread_bps=-20000(sentinel)の行が **180件**存在。全件が19:00-19:10 UTCメンテナンス明け
直後(19:10-19:11台)に集中し(17エピソード、最大23連続bin=115秒)、当該区間はmidも約半値(例: 11,514,147→5,757,633)に
汚損される再接続グリッチと確認。本監査は該当bar([maint_hour19,minute<12] ∪ spread<=-100)を含む地平線窓を持つ
試行を全て除外(妥当性フィルタ)。除外なしで実行すると exec_price=0 の除算エラー・infでheadline統計が崩壊することを確認済み
(spread=-20000のとき 1+spread/2/1e4 が厳密に0になるため)。

## 4. コントロール
### (i) シャッフルplacebo (未来経路を n/2 循環シフトして時刻対応を破壊)
| cap | symmetric_bps mean(placebo) | 95%CI |
|---|---|---|
| 5s | -1.17 | [-1.24, -1.09] |
| 60s | 0.43 | [0.26, 0.59] |
| 300s | 0.92 | [0.84, 0.99] |
| 2400s | 0.93 | [0.86, 0.99] |

### (ii) sign-reversed: buy-only vs sell-only (ドリフト混入チェック)
| cap | buy_total_bps mean | sell_total_bps mean | 差(buy-(-sell)) |
|---|---|---|---|
| 5s | 1.72 | -4.15 | -2.43 |
| 60s | 3.40 | -2.43 | 0.96 |
| 300s | 3.86 | -2.03 | 1.83 |
| 2400s | 3.87 | -2.01 | 1.86 |

## 5. 時間帯 / ボラ3分位
### 時間帯 (UTC, cap=5s / cap=2400s のsymmetric_bps)
| hour帯 | n | 5s mean | 2400s mean |
|---|---|---|---|
| 0-4 | 739 | -1.26 | 0.86 |
| 4-8 | 710 | -1.21 | 0.85 |
| 8-12 | 656 | -1.17 | 0.93 |
| 12-16 | 693 | -0.99 | 1.12 |
| 16-20 | 485 | -1.41 | 0.92 |
| 20-24 | 466 | -1.36 | 0.90 |

### ボラ3分位 (直近300秒 log-return std)
| vol tercile | n | 5s mean | 60s mean | 300s mean | 2400s mean |
|---|---|---|---|---|---|
| low | 1250 | -1.42 | 0.03 | 0.71 | 0.74 |
| mid | 1249 | -1.26 | 0.47 | 0.90 | 0.91 |
| high | 1249 | -0.97 | 0.95 | 1.15 | 1.15 |

## 6. スケーリング検定・MDE・棄却文
- cap=5s symmetric_bps = -1.21 [-1.27,-1.15]、cap=2400s = 0.94 [0.88,1.01]
- 対応差分(2400s−5s) = 2.15 [2.11,2.20] (day-clustered)
- MDE(日クラスタ, n_days=16, alpha=5% two-sided, power=80%) ≈ 0.09 bps (5s cap の日次symmetric_bps SD=0.13bps基準)

**棄却文**: もし対応差分(2400s−5s)の95%CIが0を含まず、かつ|差分|>MDEで正方向(2400sの方が損失が小さい/有利)であれば
「短scale=長scale」法則は棄却される(capを伸ばすことが真に有利という結論に変わる)。
逆にCIが0を跨ぐか、taker_shareの急減にもかかわらずsymmetric_bpsがほぼ同水準なら法則は支持される。

## 7. 前提の誤り
| premise | claimの出典 | データが示すこと | バイアス方向 | 波及するclaim |
|---|---|---|---|---|
| spread≈1.9bps(指示コスト) | 監査指示の realized cost regime | 板実測spread_bps平均=1.88bps、中央値=1.78bps | 実測が指示値と乖離する分だけtaker脚コスト見積りが変動 | AB自身、コストregimeを共有する他の全capパケット(AD,AE,AF,AG等) |
| config/config.yaml costs.taker_fee_pct=0.15%(15bps)+slippage_pct=0.05%(5bps) | 本番PAPER約定モデル | 本監査指示のfee0%/slippage1bpsと1桁近く異なる(paper側は保守バッファ) | configの値を使うと本監査より遥かに悲観的な結果になる | costs.taker_fee_pct/slippage_pctを直接引用する他の全pnl系claim |
| キュー位置=着席時点のbestサイズ全量(最後尾) | 本監査の待ち行列近似(データに真のキュー位置情報なし) | 実際のキュー位置は不明(半分着席のqueue_frac=0.5感度では結果は§3参照) | 最後尾仮定はtaker化率を過大に見積る方向(悲観)=法則を支持する方向にバイアス | AB自身、キューモデルを流用する将来のmaker系claim |
| 板データは常に健全 | (暗黙) | spread_bps=-20000のsentinelが180行、19:10-19:11UTC再接続時にmidも半値に汚損(§3b) | 未フィルタでtaker脚コストやspread平均を計算すると符号・桁が破綻(実測平均が-12.5bpsに歪む) | spread/コストをboard_round系データから直接平均するAB以外の全claim(特に同スナップショットを使うクロスパケット) |
| 「5秒スケールで-7〜-15bps/回」の絶対水準 | claim文言 | 本監査のsymmetric_bps@5s = -1.21bps (CI [-1.27,-1.15]) | 前提spread/slippageに敏感。値の絶対一致は要検討、方向(負・大きい)の一致度は§6参照 | L16本体、40分側の値幅換算 |

## 8. 検証した読み取りファイル
- backtest_data/board_round_20260904/board_round_series_5s.csv.gz
- backtest_data/board_round_20260904/board_round_coverage.json, MD5SUMS
- config/config.yaml (costs.* のみ参照)
- paper_logs/tape/executions_20260903.csv.gz, ticker_20260903.csv.gz (列構造確認のみ、直接統計には未使用)
- backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz (列構造確認のみ、直接統計には未使用)

注: backtest_data/board_round_20260904/JUDGE_RUN.txt, JUDGE_RUN_qc.txt はプロトコルの `*_RUN.txt` 禁止規定に
該当するため未読。TP_OPERATING_REF.txt は明示禁止リストには非該当だが、禁止スクリプト`tp_operating_curve.py`の
出力である疑いが強く、盲検性を守るため意図的に未読とした。

## 9. 評決
**結論変更**

claim=「短scale=長scale、5秒で-7〜-15bps/回」。本監査のsymmetric_bps(day-clustered)は
cap=5s: -1.21bps [-1.27,-1.15]、cap=2400s: 0.94bps [0.88,1.01]、
差分2.15bps [2.11,2.20] (MDE=0.09bps)。
taker_shareの低下に伴いsymmetric_bpsも有意に改善し、capを伸ばすことが実質的な経済価値を生んでいる
。

| 項目 | claim値 | 本監査再計算値 |
|---|---|---|
| 5秒capの1回あたり損失 | -7〜-15bps | -1.21bps [-1.27,-1.15] |
| taker_share@5s | (未記載) | 76.8% |
| taker_share@2400s | (未記載) | 0.0% |
| 2400s(40分)capのsymmetric_bps | 値幅で-10〜-29bps/unit(別定義) | 0.94bps [0.88,1.01] |