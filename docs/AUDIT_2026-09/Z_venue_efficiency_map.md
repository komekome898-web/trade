# Packet Z — 独立監査: L15 / R28 / P6 (JFSA効率ギャップ地図・リベートmaker族・GMO第2ベニュー)

再現手法: `backtest_data/venue_survey_20260827/*_book.jsonl.gz` / `*_trade.jsonl.gz`(11ベニュー/ペア、2026-08-27の共通4h窓)
と `paper_logs/venues/{quotes,trades}_*.csv.gz`(2026-08-27〜09-04、9日分)を自前実装で再集計。
スクリプト: scratchpad/audit_Z.py。手数料は `config/products.yaml`(bitFlyer 2件)+ `venue_survey_20260827/FINAL.txt`
の PHASE3 表(m/t fee bps 列、他ベニューの公開手数料表を集計したもの)を出典として使用(値はそのまま転記、床の再計算式は自前)。

## 1. 前提の誤り(最重要: KNOWN ISSUE の検証結果)

| premise | source in claim | what the data shows | bias direction | inherits |
|---|---|---|---|---|
| コスト床の「+4.00bps」はスリッページ実測値 | L15/R28 floor式 `2*taker+spread_p50+2*slip`, slip=2.00bps一律 | 生データに一律4.00bpsの根拠なし。板/歩み値からタッチ超過(walk-beyond-touch)を実測すると、片道の量(発生率×平均超過幅)はベニュー毎に**0.22〜3.51bps**でバラつく(bf_fxbtc 0.76, bf_xrp 1.78, bb_btc 1.41, bb_xrp 2.03, bb_eth 3.51, gmo_btc 0.80, gmo_btclev 0.55, cc_btc 0.74, okj_btc 0.38, bt_btc 0.22bps; bf_btcは歩み値なしで未測定)。一律仮定は上位3ベニュー(cc/gmolev/bf_fxbtc)を過大評価、bb_ethのように過小評価するベニューもある | 床の**絶対値**を歪める(11床全て一律−4bpsに近い値で動くため symmetric だが、正しい相対差は失われる)。ランキングの上位3(拮抗)/下位グループの粗い構造はロバストだが、隣接ペアの順位(cc_btc⇄gmo_btclev、bt_btc⇄bb_btc、bb_xrp⇄bb_eth)は測定方法で入れ替わる | 「手数料所14.7〜51.9bps」の帯、R28のmaker net計算(cap+adv)の adv 側にも同一の生成源データが使われている可能性 |
| 歩み値の `t` フィールド=取引時刻 | (監査者自身が最初に踏んだ罠。原claimではなく本監査の作業メモとして記録) | `*_trade.jsonl.gz` の `t` はローカル取得(バックフィル収集)時刻でほぼ一定値、実際の約定時刻は `ts`。`t` で板と突合すると fill率が実際の1/3程度に過小算出され、maker net の符号まで変わる(例: bf_fxbtc `t`突合ではnet=+1.17bps、`ts`突合では−0.54bps) | なし(原claimがどちらを使ったかは非公開スクリプトのため不明。ただし本監査は`ts`使用で FINAL.txt の cap+adv 値に近い数字が再現できた ため、原分析は`ts`相当を使っていたと推測) | ベニュー生存査(venue survey)を再利用する監査全般 |
| R28 の係数「rebate − 0.69×half_spread」 | R28 | リベート3ベニュー(bb_xrp, bb_eth, gmo_btc)についてこの式で予測すると全て**正**(+0.77〜+1.99bps)になるが、実測net(fee込み)は全て**負**(−0.32〜−0.49bps)。実測ではadverse selection(5秒)がhalf-spread捕捉よりずっと大きく、固定係数0.69では説明できない | 式自体は再現しないが「rebateがあっても純負」という結論方向は一致(過大な安心材料にはならない) | この係数を使った将来の期待値試算があれば全て要再検証 |

## 2. 主張別 再計算

### L15 コスト床(11ベニュー/ペア)
denominator: ベニュー毎の板スナップショット n=2,878〜7,200(2026-08-27 共通4h窓)。fee出典: 上記。

| job | fee m/t(bps) | spread tw中央値(bps) | 実測片道超過(bps) | **claimed floor** | **recomputed floor**(=2*taker+spread+2*超過) | Δ |
|---|---|---|---|---|---|---|
| bf_fxbtc | 0.0/0.0 | 1.837 | 0.756 | 5.84 | 3.35 | −2.49 |
| gmo_btclev | 0.0/0.0 | 1.597 | 0.548 | 5.60 | 2.69 | −2.91 |
| cc_btc | 0.0/0.0 | 1.428 | 0.737 | 5.43 | 2.90 | −2.53 |
| gmo_btc | -1.0/5.0 | 0.676 | 0.796 | 14.68 | 12.27 | −2.41 |
| bt_btc | 0.0/10.0 | 0.276 | 0.217 | 24.27 | 20.71 | −3.56 |
| bb_btc | 0.0/10.0 | 0.001 | 1.411 | 24.00 | 22.82 | −1.18 |
| bb_xrp | -2.0/12.0 | 0.044 | 2.025 | 28.04 | 28.09 | +0.05 |
| bb_eth | -2.0/12.0 | 0.025 | 3.507 | 28.02 | 31.04 | **+3.02** |
| bf_btc | 15.0/15.0 | 2.990 | 未測定(歩み値なし) | 36.99 | ≥32.99(下限) | ≤−4.00 |
| okj_btc | 7.0/14.0 | 6.811 | 0.378 | 38.81 | 35.57 | −3.24 |
| bf_xrp | 15.0/15.0 | 17.855 | 1.783 | 51.86 | 51.42 | −0.44 |

再計算順位: `gmo_btclev(2.69) < cc_btc(2.90) < bf_fxbtc(3.35) < gmo_btc(12.27) < bt_btc(20.71) < bb_btc(22.82) < bb_xrp(28.09) < bb_eth(31.04) < bf_btc(≥32.99) < okj_btc(35.57) < bf_xrp(51.42)`
claimed順位: `cc_btc(5.43) < gmo_btclev(5.60) < bf_fxbtc(5.84) < gmo_btc(14.68) < bb_btc(24.00) < bt_btc(24.27) < bb_eth(28.02) < bb_xrp(28.04) < bf_btc(36.99) < okj_btc(38.81) < bf_xrp(51.86)`
→ 「拮抗する上位3ベニュー」「bf_xrpが最悪」「gmo_btcが中位」という**粗い構造は再現**。ただし cc_btc⇄gmo_btclev、bt_btc⇄bb_btc、bb_xrp⇄bb_eth の3ペアで順位が入れ替わる。**手数料所14.7〜51.9bps** は再計算で 10.7〜51.4bps(bf_btc除く)相当となり下限のみ有意にずれる。

**Controls**: シャッフル placebo(取引時刻を保持し価格のみランダム化、bf_fxbtc/cc_btc/gmo_btclev/bb_xrpで実施)は net を real と異符号または大幅に変化させた(bf_fxbtc: real −0.54 vs shuffled −0.01; cc_btc: real −0.69 vs shuffled +0.37; gmo_btclev: real −0.60 vs shuffled +0.76)→ 観測されたnegative netは時間構造(直後の逆行)に由来し、単純な価格分布のアーティファクトではない。

**Translation**: bf_fxbtc(現行運用商品FX_BTC_JPY)の再計算床3.35bps ≈ 1BTC=1260万円換算で **JPY 4,221/往復・1BTC** (claimed 5.84bpsなら7,358円)。1日あたり運用規模次第だが、原claimは片道あたり約43%(5.84→3.35 not uniform)過大に見積もっていた可能性がある。

### R28 リベートmaker族(タッチクオート10ベニュー)
denominator: ベニュー毎 fill n=586〜37,117(placed n=3,600〜7,200、2026-08-27 4h窓)。手法: 各板更新でタッチに指値、L=10s以内に歩み値がprint-throughしたらfill、captureはpost時のmid距離、adv5はfill後5秒のmid逆行。

| job | fills | fill% | cap(bps) | adv5(bps) | net(手数料前) | maker fee(bps) | **net_after_fee** |
|---|---|---|---|---|---|---|---|
| bf_fxbtc | 5557 | 77.2% | 0.937 | 1.476 | −0.538 | 0.0 | **−0.538** |
| bf_xrp | 586 | 16.3% | 7.043 | 4.660 | 2.383 | 15.0 | **−12.617** |
| bb_btc | 2361 | 32.8% | 0.118 | 1.859 | −1.741 | 0.0 | **−1.741** |
| bb_xrp | 4316 | 60.0% | 0.114 | 2.464 | −2.350 | -2.0(rebate) | **−0.350** |
| bb_eth | 1376 | 38.2% | 0.100 | 2.588 | −2.488 | -2.0(rebate) | **−0.488** |
| gmo_btc | 1764 | 36.8% | 0.403 | 1.724 | −1.321 | -1.0(rebate) | **−0.321** |
| gmo_btclev | 3931 | 81.9% | 0.848 | 1.443 | −0.596 | 0.0 | **−0.596** |
| cc_btc | 3495 | 72.8% | 0.720 | 1.408 | −0.688 | 0.0 | **−0.688** |
| okj_btc | 879 | 18.3% | 3.218 | 1.715 | 1.503 | 7.0 | **−5.497** |
| bt_btc | 2824 | 58.8% | 0.506 | 0.939 | −0.433 | 0.0 | **−0.433** |

**10/10が net_after_fee<0 → R28の「タッチクオート10ベニュー全て負」は方向として再現**(この監査独自実装でも符号は一致)。CIは全て狭く(±0.05〜0.5bps、n=586〜37,117)、境界事例なし→MDE(80%検出力)は最小0.1〜0.2bps程度で、観測効果(0.3〜12.6bps)を十分検出できる規模。
ただし係数式「rebate−0.69×half_spread」自体は再現しない(§1参照、adverse selectionが支配的要因で、それは半スプレッドの定数倍にはならない)→ **数値差異(結論維持)**。

### P6 GMO第2ベニュー仮説
- **日数**: `paper_logs/venues/` の GMO BTC_JPY は 2026-08-27〜09-04 の **9日/9日連続取得**、判定バー14日に対し **9/14(不足、5日分足りない)**。
- 独立再現(9日・554,369トレード)での同一タッチクオートsim: fill 57.1%, cap 0.698, adv5 0.468, **net(手数料前)=+0.230bps**、rebate込みnet_after_fee=**+1.230bps**(正!)。単一4h窓(venue_survey, 4,344トレード)の同一計算は net=−1.321bps, fee込み−0.321bps(負)。
- **符号が窓によって反転する**(4h窓: 負 / 9日窓: 正)。これは「スプレッドMM校正が独立ベニュー(時間窓)で再現するか」という設問に対し、**まだ再現していない・むしろ不一致**という結果。日数もバー未達のため、判定は**保留のまま**(再計算不能=データ不足。14日到達後に再監査が必要)。

## 3. 残りの10問(簡潔)
4. Relative/absolute: L15の床は「水準」の主張(規模非依存)。ボラ/時間帯別の分解はしていない(スコープ外、時間予算のため見送り。追試候補)。
5. Definition side-effects: タッチクオートsimは「毎スナップショットで新規指値」という単純化で、実際のmaker戦略(在庫・キャンセル)を模していない→ fill率は上振れしやすい(bf_fxbtc 77%は非現実的に高い)。
6. Data validity: bf_fxbtcなど一部で `bid<ask` 崩れ・ゼロ値を除外。19:00-19:10UTCメンテ窓は対象4h窓(2026-08-27T11:49-15:49 UTC)に含まれず影響なし。
7. Selection contamination: 11ベニュー/ペア×複数統計量のmulti-comparisonだが、床の順位入れ替わりが3ペア起きている時点で「僅差のセルは検索対象数に対し脆弱」と評価。
8. Simplest alternative: adverse selection(5秒)がnet negativeの主因(cap自体は多くのベニューで正=半スプレッド捕捉はできている)。ビッド・アスク・バウンスではなく方向性のある直後の逆行。
9. Consistency: PART D(9日 vs 4h)で符号不一致 → 一貫性は**低い**(gmo_btcに関して)。

## 4. Verdict

| claim | verdict | 根拠 |
|---|---|---|
| L15 | 数値差異(結論維持) | 上位3拮抗・bf_xrp最悪という粗い構造は再現。絶対値は一律+4.00bps分過大(根拠なき一律仮定)。3ペアで順位入替。 |
| R28 | 数値差異(結論維持) | 「10ベニュー全て負」は符号一致で再現。係数式(rebate−0.69×half_spread)は再現せず、adverse selectionが支配的という点で結論の**理由付け**が変わる。 |
| P6 | 再計算不能(データ不足→未検証維持) | 9/14日でバー未達。加えて利用可能な9日窓では符号がむしろ反転(+0.23bps)し、4h窓のnegativeな示唆を裏付けない。 |

読んだファイル: docs/AUDIT_2026-09/PROTOCOL.md, docs/AUDIT_2026-09/00_packets.md(grep行のみ), config/products.yaml,
backtest_data/venue_survey_20260827/FINAL.txt(fee表・claimed floor値の出典として), 各 *_book.jsonl.gz / *_trade.jsonl.gz(11本×2),
paper_logs/venues/quotes_*.csv.gz(9日分), paper_logs/venues/trades_bitbank_*.csv.gz・trades_gmo_btc_jpy_*.csv.gz(9日分)。
`backtest_data/venue_survey_20260827/analyze_venues.py` / `analyze_screen.py` / `SCREEN.txt` は未読(ブラインド性維持のため意図的にスキップ)。
