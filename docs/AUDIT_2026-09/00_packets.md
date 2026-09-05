# 全件監査パケット表(2026-09、確定版)

`docs/AUDIT_PLAN_2026-09.md` に基づく網羅棚卸し。**パケット表(§2)はここで確定し、以後増減しない**(計画§1)。
主張は KNOWLEDGE系文書のセクションから機械的に切り出し。ID接頭辞 = 出所:
`C`=KNOWLEDGE.md§1(BTCコスト実測) `L`=同§2(BTC法則) `R`=同§3(BTC棄却台帳) `P`=同§4(BTC係属)
`FXC/FXL/FXT/FXR/FXP`=KNOWLEDGE_FX.md §1/§2/§3/§3.5/§4 `JPC/JPL/JPR/JPP`=KNOWLEDGE_JP.md §1/§2/§3/§4
`PR`=PREREG判定 `SV`=SURVEY結論。評価報告id(b〜ap)の凡例は `docs/KNOWLEDGE.md` 冒頭・`docs/RESEARCH_REPORT_*.md`
ファイル名。データ状態: **available**(パス明記)/ **partial**(一部・進行中)/ **lost**(bitFlyer31日 or OKX30日で消滅)
/ **external-fetchable**(URL)。

## 1. 主張インベントリ(全165件)

### 1.1 BTC — KNOWLEDGE.md §1 コスト実測(C1–C7)

| ID | 主張(逐語トリム) | 評価報告 | データ状態 |
|---|---|---|---|
| C1 | 手数料taker/maker とも0%。コストは半スプレッド+スリッページ2bpsのみ | config/products.yaml, NOTE_CRYPTO_CFD | available: config/, docs/NOTE_CRYPTO_CFD_2026-08-20.md |
| C2 | taker片道≒3.2bps(半スプレッド1.18+スリッページ2.0)、往復6.35bps | e | available: backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz |
| C3 | バースト時3.96bps(1.96+2.0)、平穏時2.93bps — スプレッドはバースト時に約2倍 | i | available: backtest_data/burst_events_20260820/ |
| C4 | 板記録実測スプレッド1.56〜2.22bps(mid比)は30秒以下の全条件付きドリフトを上回る | f, g | available: backtest_data/flow_FX_BTC_JPY_20260820.csv |
| C5 | maker建ては手数料もスプレッドも払わないが逆選択で6〜9bps失う。3独立研究で実測 | i, j, k | available: backtest_data/board_round_20260904/ |
| C6 | 現物(XRP_JPY等)は往復0.55%。CFDの約10倍 | BT | available: backtest_data/candles_XRP_JPY_20260820.csv |
| C7 | 資金調達率は8h毎決済(05/13/21 UTC)、実測平均\|rate\|≒0.017〜0.02%/8h | f | available: data/funding_rate_history.csv(201行) |

### 1.2 BTC — §2 市場構造の法則(L1–L30)

| ID | 主張(逐語トリム) | 評価報告 | データ状態 |
|---|---|---|---|
| L1 | コストの壁: 単一銘柄テクニカル(ema_cross/rsi_reversion/breakout、全時間足)は例外なくコスト未満 | BT, b | available: backtest_data/candles_*_20260820.csv |
| L2 | 消えた遅れ: 薄いXRP_JPYはlag1+0.176、厚いFX_BTC_JPYは+0.019(同時相関+0.878) | b, c | available: 同上+bitbank_xrp_jpy_1m.csv |
| L3 | 秒単位にだけ遅れが残る: 1秒足でlag1+0.11〜0.25、吸収1〜2秒。閾値20bps級のみプラス | e | available: backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz |
| L4 | 予測可能な脚は取引不能な側: ベーシス閉じるのは遅行する現物側、CFD自身は同方向にドリフト | f | available: candles_{BTC,ETH,XRP}_JPY_20260820.csv |
| L5 | 逆選択の壁: 発火直後の成行フローは逆側指値を1.6秒で96%約定、約定群は240分14.9bps走る。champion反転最良+0.018%/取引=バーの1/8.2 | x | lost: 元テープはbitFlyer31日超過分未スナップショット(結果値のみ報告に残存) |
| L6 | バースト面の法則(約1,190セル): 無条件反転3/900(非有意)。時計窓×先頭×20bps/30-60s×30分保有のみ+23.71bps コスト前、CI[+7.92,+37.27]、n=40 | y | available: backtest_data/burst_events_20260820/, storm_events_20260820/(汚染面。判定はP5=フレッシュ後継続テープ) |
| L7 | リーダー追随族死亡診断: 1分lag1+0.016。210日25セル×5地平ドリフト<コスト床0.079%、n≥400でtaker線超え0.0% | y | available: backtest_data/binance_BTCUSDT_1m.csv+candles_FX* |
| L8 | 逆選択の壁: レンジ逆張り約定は指値の0.86%のみ・約定後平均−6.5bps逆行。TP指値+88bps(トーナメントC1) | i, j, k, T | available: backtest_data/board_round_20260904/ |
| L9 | レンジ端タッチは順張り: 23,642件バリアレースで戻り31.7% vs 突破61.4%。USD/JPYでも戻り40% vs BTC34% | k, o, s | available: candles_FX_BTC_JPY_30d, fx_usdjpy_1m_20260822.csv.gz |
| L10 | 嵐は時計に支配される: UTC12:30–15:00のみ合格(リフト2.23・再現率0.33・n=234、月次1.84〜4.05) | h | available: backtest_data/storm_events_20260820/ |
| L11 | 嵐の方向は事前予測不能: 上下49.3/50.7%で無偏。31分前読みでコイントスに崩壊 | i | available: 同上 |
| L12 | 出口チューニングの限界: 曲面に尾根なし。適応型TPは定数の大TPと有意差なし | k, l | available: paper_logs/scalp_paper.jsonl, data/scalp_paper.jsonl |
| L13 | 時計窓はタッチ継続を増幅: 30分極値タッチ後、時計窓内+6.81bps@30分 vs 全日+1.15bps(n=821/7,157) | v | available: candles_FX_BTC_JPY_30d_20260820.csv |
| L14 | 確率面の法則(3,008セル): 規模lift0.03〜245(1〜2桁)。方向は全特徴lift0.93〜1.16に潰れる。必要p線通過セルは面全体で0 | z | available: 同上+storm/burst events |
| L15 | JFSA効率ギャップ地図(11ベニュー): コスト床Coincheck5.4/GMOレバ5.6/bitFlyerCFD5.8bpsで拮抗、手数料所14.7〜51.9bps | ac | available: backtest_data/venue_survey_20260827/ |
| L16 | 時間による出口緩和はtakerの別名: 5秒スケールで損失−7〜−15bps/回。40分スケールは値幅で−10〜−29bps/unit | ad, ae | available: backtest_data/board_round_20260904/ |
| L17 | 日足トレンドフィルタ: BTC15年SMA/TSMOM6セルmaxDD床−70〜−82%。プレミアはサイクル毎単調減衰(+100.6→−27.7pp) | ai | available: backtest_data/daily_btcusd_{yahoo,coinbase,bitstamp}_20260828.csv.gz |
| L18 | エッジ×レイテンシ曲線: エッジは最初0.2秒に集中。頻度0.84回/日×板厚0.02BTCで最良+27円/日 vs サーバ費33〜50円/日 | ah | partial: data/latency/(セッション終了で消失リスク。要約値のみ報告に残存) |
| L19 | maker往復閉じ脚のはさみ撃ち: 対約定p50 7〜15秒・maker閉率99.8%だが脚間midが−3.2〜−3.6bps動く | ag | available: backtest_data/venue_survey_20260827/ |
| L20 | 在庫型片側ミーンリバージョンの床: 5軸×210日51セルで0.66bpsしか動かない。バイアス補正後≤0 | af | available: candles_FX_BTC_JPY_30d_20260820.csv |
| L21 | v37レンジ上限ゲートは嵐フィルタ: 40分実体レンジ≤82bpsが嵐分の99.9%を排除(嵐中145bps vs平常35bps) | af | available: 同上 |
| L22 | 嵐後2〜6hはmaker回転に最も優しいレジーム: 平常比+1.2bps/unit。単独では床を越えない(到達−1.7) | af | available: storm_events_20260820/+candles_FX_BTC_JPY_30d |
| L23 | candle近似の手法バイアス実測+1.27bps/unit(悲観)。高安タッチ=全約定参加率過大 | af | available: 同上 |
| L24 | 按分TPは勝ち固定装置: 往復粗利=0.8×volaに固定。勝ち90.5%×+5.3、負け9.5%×−85.7(平均k5.0) | ae | available: 同上 |
| L25 | 在庫平均化は1単位救うが集計悪化: 寄与+2.4〜+3.5bps/unitもゼロに届かず(残−2.3〜−3.4)、notional1.7倍 | ad | available: 同上 |
| L26 | 壁板は吸収体でない: M24比10倍超の壁の63〜65%が10秒以内に消える。10秒生存13% | ab | available: backtest_data/venue_survey_20260827/ |
| L27 | f(fill率)実測: 実板7日でf=18.1%。支配軸=滞在時間(取消方針4.33x>スプレッド2.04x>寿命1.63x) | aa | available: 同上 |
| L28 | captureとfは同じつまみ: 約定クオートcapture≒名目半スプレッドの約半分(+0.60bps)。単発クオートcapture+adverse(5s)は−0.09〜−0.86bps | aa | available: 同上 |
| L29 | 両側フローレジームはmakerが正になる唯一の場所: W=30s窓、理想化makerネット窓内のみ+0.38〜+0.76bps、f=100%で8〜13万円/日 | u | available: 同上 |
| L30 | bot狩り機構: pick-off後継続幅中央値+0.6bps@30s/+1.8bps@30m(n=29,163挿入、7日)。成立には往復0.5〜1bps以下が必要 | ao | available: 同上 |

### 1.3 BTC — §3 棄却済み仮説索引(R1–R43)

| ID | 主張(逐語トリム) | 評価報告 | データ状態 |
|---|---|---|---|
| R1 | 単一銘柄テクニカル: コスト前に優位性なし。「最良」は取引回数最少の構成 | BT | available |
| R2 | 通常規模モメンタム追随(XRP/BTC現物/FX、12構成): 条件付きドリフト<往復コスト | b, c | available |
| R3 | 長期モメンタム(2年4h/日足): train+1.7〜22%/取引→val・OOS全負(丸暗記) | b | available: binance_BTCUSDT_1m/4h/1d |
| R4 | 出来高系(スパイク後ドリフト/いなご/加速): 同一分内織り込み済み。加速は先行性なし | b, d, h | available |
| R5 | ヒゲ逆張り(15分足mult2.0/穏やか+指値): 21日合格→新鮮データで崩壊(過学習) | d→g, j | available |
| R6 | レンジ逆張り(素/穏やか+指値+嵐損切り/執行逆転): 全執行極性で負(−3.30/−9.12bps) | d, j, k | available |
| R7 | アンカー乖離逆張り(v1/v2/穏やか+指値): 生フェード効果が往復コスト6.3bps超えず | g, j | available |
| R8 | ベーシス平均回帰: 回帰実在(半減期9.1分)だが閉じるのは取引不能な現物脚 | f | available |
| R9 | 常時型スキャル(秒スケールthr3〜5bps): 全窓ネット−2.6〜−6.1bps | e | available |
| R10 | 嵐の予兆(価格/出来高/IV/大口): 最大リフト1.57(基準2.0未満)、合成は逆相関 | h | available: storm_events_20260820/ |
| R11 | 嵐の方向予測(モメンタム/フロー/24hレンジ位置): 定義窓外でコイントス。レンジ位置は日次−6.6bps | i | available |
| R12 | 時間帯の方向性(時刻別/曜日別): 全てノイズフロア(1bps)未満 | f | available |
| R13 | 板不均衡の単独taker戦略: 効果実在も0.29〜1.35bps<スプレッド2.22bps | g | available |
| R14 | スキャルパー武装閾値(10→8bps): 限界トレードが系統的に低質(−4.14bps) | i | available: paper_logs/scalp_paper.jsonl |
| R15 | 出口設計(E1/E3/E4、固定曲面24セル、適応型TP3方式): E2を有意に上回る構成なし | k, l | available |
| R16 | メインBOT出口グリッド(54構成): 訓練最良構成がval・OOS両方で現行に敗北 | k | available |
| R17 | 旧bot要素(ヒゲ無効化ストップ/vr予兆/vrフィルタ): ヒゲストップは30日実データで勝つがval・OOS敗北。vrリフト≈1.00 | n | available |
| R18 | バーストスキャルパー本体: 86イベントnet−3.83bps、95%CI[−9.2,−2.8] | p | available: paper_logs/bot.jsonl, scalp_paper.jsonl |
| R19 | TPのボラ連動: ライブ前方検証n=77で傾き−0.20bpsに消滅 | p | available |
| R20 | TP上限(maker TP+0.3/0.5/0.8%、トーナメントC1): 選択効果+88bps実在も出口効果−37bps対コスト削減+1.8bps | T | available |
| R21 | 高速サイクルmakerスキャルパー: 実板capture+adverse(5s)=−0.716[−1.040,−0.505]<バー+0.38、全21セル不通過 | u, aa | available: backtest_data/venue_survey_20260827/ |
| R22 | M2マチルダ現代化(8セル): 8セル全滅、56日次値すべて負(−516〜−7,141bps/日) | ad | available |
| R23 | M3マチルダTaroCamp v37(4セル): 0/4、−0.40〜−1.36bps/unit。史上最接近 | ae | available |
| R24 | LT1長期トレンド: maxDD FAIL(6セル全て−70%超)、後半Sharpe FAIL+プレミア単調減衰 | ai | available: daily_btcusd_*, daily_ethusd_* |
| R25 | WS化ライン: ハードは届くが経済が閉じる。最良+27円/日 vs サーバ費33〜50円/日 | ah | partial: data/latency/ |
| R26 | SMスプレッドMM対称族(4セル): 0/4、−1.02〜−1.42unit-bps → maker線閉鎖 | ag | available |
| R27 | M4マチルダ面(210日57セル): 正の台地なし・凍結候補0。51セル全負 | af | available |
| R28 | リベートmaker族: makerネット≈リベート−0.69×半スプレッド。タッチクオート10ベニュー全て負 | ac | available: venue_survey_20260827/ |
| R29 | ベーシス再監査2026: 依然棄却、余裕20倍→1.0倍。最良組往復2.82 vs グロス2.70 | f, ac | available |
| R30 | 薄いペアのリード・ラグ追随: lag1+0.365@5sだが追随側床24〜52bpsが全て食う | b, ac | available |
| R31 | 壁板手前指値(6セル): 0/6通過。差+0.32〜+0.70bps<バー1/2.3〜1/4.8。壁の63〜65%は10秒以内に引かれる | ab | available |
| R32 | vrレジーム指標(原典5秒スケール): fリフト1.07、逆選択差ゼロ(t=−0.28) | n, aa | available |
| R33 | 板不均衡(top-of-book実板再訪): 0.08〜0.26bps、半スプレッドに1桁不足 | g, aa | available |
| R34 | 板不均衡taker深掘り(深さ5bps×時計窓、最終): ネット−3.6〜−5.6bps(t−2.4〜−107) | ap | available: board_round_20260904/ |
| R35 | 5秒スケールvr静穏モード逆張り(最終): 粗−0.2〜−0.5bps、無条件も負 | ap | available |
| R36 | メインBOT champion(xborder_momentum): 30取引net−0.148%/取引、CI[−0.243,+0.063] | w | available: paper_logs/bot.jsonl |
| R37 | C3ロングオンリー(composite long_only): n=17 net−0.013%、CI[−0.194,+0.196] | w | available |
| R38 | S10雪崩追随(thr20/30bps): thr20の2セルが4通り全て負(−0.5〜−12.8bps) | x | available: burst_events_20260820/ |
| R39 | S11シグナル反転フェード: 後半40%が4セル全負。最良型でもバーの1/8.2 | x | available |
| R40 | 嵐時計ブラケット(S9): 全6セル負(−2.8〜−7.1bps) | v | available: storm_events_20260820/ |
| R41 | ソーシャル注目度→方向予測(日次): 着手前閉鎖。必要効果0.7〜1.5%/日 vs 文献0.03〜0.08 | SURVEY_ATTENTION_DATA | external-fetchable: Wikipedia pageviews API, GDELT, F&G index |
| R42 | RC1等重量合成指標(週次方向): IC−0.073(t−1.0)、Q5−Q1−0.66%/週、符号整合3/6 | am | available: backtest_data/regime_composite_20260901/ |
| R43 | C2レーダー窓内エントリー限定: n=21、中央値−0.375%/取引、CI[−0.404,−0.094] | an | available: paper_logs/bot.jsonl |

### 1.4 BTC — §4 係属中(P1–P6、既決着の~~取り消し線~~項目は§3側の R42/R37/R43/R21/R38/R31 と同一なので除外)

| ID | 主張(逐語トリム) | 評価報告 | データ状態 |
|---|---|---|---|
| P1 | 加熱×ボラ増幅ゲート: 加熱Zと翌日レンジ相関+0.21〜0.24。増分は高ボラ×加熱z-highで翌日レンジ+38%に集中 | al | available: data/attention/attention.csv |
| P2 | OI系(急増/静穏×増/L-S極値): OKX履歴約30日固定・ページング不可。自前蓄積が30日到達でフェーズC判定 | h | partial: paper_logs/oi_snapshots.csv(1298行、蓄積中) / lost(OKX 30日超過分) |
| P3 | 約定後5分回転(maker両建てTP2〜3bps): +1.1bps戻り実在も同一30日データで自己汚染。新鮮2週間で再監査 | j | available(旧) / 新鮮データ未取得=pending |
| P4 | 資金調達決済後ドリフト: 13:00UTC決済後30分−8.2bps(n=21,σ=20.9,t≈1.8)。サンプル3倍で再検定 | f | available: data/funding_rate_history.csv(n=201、拡張余地あり) |
| P5 | S12時計バースト30分保有(本体判定): バー=ネット≥+5bps・n≥30・日クラスタt≥2/CI>0・maxDD≤1000bps | PREREG_clock_burst | partial: フレッシュテープ(2026-08-25T12:00Z以降)蓄積中、n未達 |
| P6 | GMO第2ベニュー仮説: スプレッドMM校正が独立ベニューで再現するか。クロスベニュー14板日で判定 | ac | partial: paper_logs/venues/(9/14日時点) |

### 1.5 FX — KNOWLEDGE_FX.md §1 コスト(FXC1–FXC7)

| ID | 主張(逐語トリム) | 評価報告 | データ状態 |
|---|---|---|---|
| FXC1 | 往復コスト0.71bps(スプレッド0.5銭=0.314bps+API手数料0.4bps)。BTC CFDの約1/9 | [M+V] | available: backtest_data/gmo_swap_usdjpy.csv, fx_usdjpy_1m |
| FXC2 | 変動/コスト比0.94(BTC CFDは0.39) | r | available: fx_usdjpy_1m_20260822.csv.gz |
| FXC3 | スプレッドは床(p10=p75=0.5銭、24時間中21時間フラット)。UTC21のみ6.33bps=20倍 | [M] | available: 同上 |
| FXC4 | API手数料は指値にも注文変更にも課金 → maker逃げ道なし | products.yaml | available: config/products.yaml |
| FXC5 | 週末ギャップ中央値4.4bps(コストの6倍)、最大26.7bps | [M] | available: fx_usdjpy_1m_20260822.csv.gz |
| FXC6 | スワップ実測: 仲値=銀行間金利差×1.056+加算スプレッド0.162bps/日。ロング受取中央値1.108bps/日(2026年0.696) | t2 | available: backtest_data/gmo_swap_usdjpy.csv |
| FXC7 | OANDA証券APIはGold要件(月50万ドル+プロコース+25万円)が研究プロトコルと非両立 | r | external-fetchable: OANDA証券公開約款 |

### 1.6 FX — §2 市場構造(FXL1–FXL8)+ §2.5 イベントコスト地図(FXL9–FXL12)+ §4.5 カレンダー精度(FXL13–FXL14)

| ID | 主張(逐語トリム) | 評価報告 | データ状態 |
|---|---|---|---|
| FXL1 | ボラのピークはUTC12:00–15:00(0.68/0.79/0.82bps)—BTC嵐時計と同一窓 | [M] | available: fx_usdjpy_1m_20260822.csv.gz |
| FXL2 | 第2ピークUTC0。谷はUTC21(0.24bps、スプレッド20倍)と東京昼 | [M] | available: 同上 |
| FXL3 | 東京仲値(9:55JST)は実在のボライベント: 9:54に平常の3.2倍(1.92bps) | [M] | available: 同上 |
| FXL4 | ゴトー日仲値は測定済みヌル: n=28、方向も逆符号(t=−0.42) | r | available: 同上 |
| FXL5 | 介入テール(USD/JPY固有): MOF介入は一方向・無制限・数百bps/分。テールルールで守る | [T/V] | external-fetchable: 財務省為替介入実績(四半期後公表) |
| FXL6 | BOJ声明は発表時刻自体が漂う(11:30〜15:00JST) | [T] | external-fetchable: 日銀公表資料 |
| FXL7 | FOMC2026-27確定日程取得済み。BOJ MPM確定日程は調査報告本文 | r | available: docs/RESEARCH_REPORT_2026-08-22r.md |
| FXL8 | 日銀会合の値動きは11:30〜13:30JSTに集中(13:30以降ピークゼロ、中央値ピーク25bps) | [M], s | available: fx_event_ticks_2015_2026/BOJ_*.csv.gz |
| FXL9 | 米指標のスプレッド爆発はE+1sに集中(中央値1.7〜1.9bps・p90 5〜6bps)、約35秒で1.5倍以内に回復 | S4 | available: fx_event_ticks_2005_2014/, 2015_2026/ |
| FXL10 | E+5s→E+300sの往復実コスト中央値0.89〜1.46bps=平常床の1.3〜2倍 | S4 | available: 同上 |
| FXL11 | 日銀にはスプレッドイベントが無い(E+1sの方が発表前より狭い) | S4 | available: 同上BOJ_*.csv.gz |
| FXL12 | 初撃\|E→E+5s\|中央値: NFP17.7/CPI12.9/FOMC3.0/BOJ2.4bps | S4 | available: 同上 |
| FXL13 | CPI「12日近傍」ルール正答20.9%。NFP第1金曜ルール81.3% | t(477件) | available: fx_event_ticks_2015_2026/calendar.csv |
| FXL14 | FOMC声明時刻は2019-20に変則6件。BOJは発表時刻自体が漂うため時刻列は名目値 | t | available: 同上 |

### 1.7 FX — §3 BTC転移事前分布(FXT1–FXT3、メタ)+ §3.5 棄却台帳(FXR1–FXR10)+ §4係属(FXP1–FXP2)

| ID | 主張(逐語トリム) | 評価報告 | データ状態 |
|---|---|---|---|
| FXT1 | 指標発表は確実に局所ボラを上げる(BTC発表後30分レンジ順位0.767、16/19日、p=0.002) | h(転移) | available(BTC側) |
| FXT2 | NFP/CPIはBTC嵐を予告しない。FOMCのみ全対照生存(n=5、係属) | h | available |
| FXT3 | BTC§2法則群はコスト1/9環境で経済条件が変わるため機構ごと再検定対象(自動転移しない) | (方針) | n/a(方針記述) |
| FXR1 | 東京仲値・前モメンタム: コスト負け(グロス+0.4bps符号安定<床0.71) | 第19報 | available |
| FXR2 | 東京仲値・後リバーサル: 機構不在(判定区間でグロス符号反転) | 第19報 | available |
| FXR3 | バリアレース逆張り(全セッション×3バリア): 全18セル戻り<50%。東京昼42.9% | 第19報 | available |
| FXR4 | セッション内平均回帰: 最強セルでも予測可能量0.1bps=コストの1/7 | 第19報 | available |
| FXR5 | イベント方向継続(1分足): 機構は29/29実在も方向は読めず | 第19報 | available |
| FXR6 | イベント初撃継続/フェード: ゼロコストでも全12構成≈0以下、構成乗り換わり | 第19報 | available |
| FXR7 | ゴトー日仲値: 測定済みヌル(n=28逆符号) | 第19報 | available |
| FXR8 | キャリー(無条件/トレンドゲート/ボラ目標、41年): 収入実在(41年中33年+)だが判定シャープ0.487<0.70 | 第19報 | external-fetchable: FRED金利差41年 |
| FXR9 | ファンダ系(COT逆張り/順張り・金利差モメンタム): 全て単純ドル買い持ちに敗北(COT t=−2.53) | 第19報 | available: fx_fundamentals_20260822/cot_jpy_legacy.csv |
| FXR10 | 初撃方向再開E+60→300s(S4): 後方新鮮2005-14(n=317)で棄却、主2セル符号逆転 | 第35報, PREREG_fx_s4 | available: fx_event_ticks_2005_2014/ |
| FXP1 | GBP/JPY頑健性検査/スリッページ実測: 対象戦略消滅(第35報)により凍結 | — | n/a |
| FXP2 | スリッページ実測(最小100通貨のライブ微量実験)が最安の測定手段 | — | pending: ライブ承認未取得 |

### 1.8 JP — KNOWLEDGE_JP.md §1 コスト床(JPC1–JPC5)

| ID | 主張(逐語トリム) | 評価報告 | データ状態 |
|---|---|---|---|
| JPC1 | 東証TOPIX100級現物 往復2.2〜3.4bps(手数料0・SOR条件+スプレッド) | SURVEY_JP_EQUITIES | external-fetchable: 東証気配データ |
| JPC2 | 東証Mid400 往復3.4〜11bps | SURVEY_JP_EQUITIES | external-fetchable |
| JPC3 | 日経225マイクロ先物(ザラバ) 1.08bps(手数料0.33+スプレッド1ティック仮定、未実測) | SURVEY_JP_INDEX_FUTURES | external-fetchable: 一次資料(未実測は要ザラバ実測) |
| JPC4 | 日経225マイクロ先物(板寄せ) 0.35bps+引当。ON1の執行前提 | SURVEY_JP_INDEX_FUTURES | available: backtest_data/n225f_225labo_20260828/ |
| JPC5 | コストモデルの賞味期限2027-03-01(呼値制度全面改定) | JPX一次資料 | external-fetchable: JPX制度アナウンス |

### 1.9 JP — §2 確立した法則(JPL1–JPL7)

| ID | 主張(逐語トリム) | 評価報告 | データ状態 |
|---|---|---|---|
| JPL1 | 単元株100株制はクロスセクショナルの資本床: 30銘柄分散に¥20M〜 | SURVEY_JP_EQUITIES | external-fetchable |
| JPL2 | 日本の暦アノマリーは全滅(月初月末/SQ/曜日/祝日前/日銀ETF) | SURVEY_JP_INDEX_FUTURES | available: backtest_data/n225f_225labo_20260828/ |
| JPL3 | モメンタム不在は2026年も継続(FF Japan WML+1.5%/年t=0.62)。バリュー生存(+4.85%t=2.69) | SURVEY_JP_EQUITIES | external-fetchable: Fama-French Japan factors |
| JPL4 | オーバーナイト効果は本物かつ取引可能(第36報): 縮小率0.99、36.6年・4時代全正、保守コスト後+6.6%/年t=2.43 | 第36報, PREREG_overnight_on1 | available: backtest_data/n225f_225labo_20260828/ |
| JPL5 | 日中セッション(寄り→引け)は1990-2015有意に負、近年ゼロ近傍 | 第36報 | available: 同上 |
| JPL6 | 夜間プレミアムはJPX市場横断(第40報): N225/TOPIX/JPX400/グロース250/J-REITのETF全てで引け→翌寄り正 | ao(第40報) | partial: backtest_data/reit_onr_20260904/(J-REITのみ完備)、他指数ETF夜間系列は未スナップショット |
| JPL7 | 薄いETFの夜間は約定アーティファクトで過大(1311 Core30 0.3億円/日) | 第40報 | partial: 同上 |

### 1.10 JP — §3 棄却台帳(JPR1–JPR10)

| ID | 主張(逐語トリム) | 評価報告 | データ状態 |
|---|---|---|---|
| JPR1 | 個別株クロスセクショナル(全形態): 資本床¥20M(オーナー資本不足) | SURVEY_JP_EQUITIES §7.4 | external-fetchable |
| JPR2 | 暦アノマリー(月初月末/SQ/曜日/祝日前): 全て\|t\|<2、t=2に265年〜 | SURVEY_JP_INDEX_FUTURES §3 | available: n225f_225labo_20260828/ |
| JPR3 | 日銀ETFフロー: 構造消滅(2024-03買入終了、売却は代金の0.05%) | SURVEY_JP_INDEX_FUTURES | external-fetchable: 日銀公表 |
| JPR4 | 米国型2脚(ON買い+日中売り): 日中脚−1.84%t=−0.38(近年ゼロ化) | 第36報 | available: n225f_225labo_20260828/ |
| JPR5 | NT倍率平均回帰: 最小構成¥8M相当で粒度不足+定量報告なし。保留(棄却ではない) | SURVEY_JP_INDEX_FUTURES | n/a(未実測) |
| JPR6 | レバETF引け前リバランス追随(RB1): 2026年1分足170日で痕跡なし(順張り全セル≈−1bps、t≈0) | 第40報 | partial: 個別ETF分足は未スナップショット |
| JPR7 | 東証上場・米株ETFの東京時間分解(UO1): 時間帯対応の誤り。東京日中の負は上場初年に集中 | 第40報 | partial: 同上 |
| JPR8 | TOPIX Core30 ETF夜間(1311): 薄いETFの約定アーティファクト(売買代金0.3億円/日) | 第40報 | partial: 同上 |
| JPR9 | 優待・配当の権利落ち季節性(YT1): 権利付き最終日−3.8bps t=−2.1。10日ランアップ2015-19+74bps→2020-26 D−5脚−38bps t=−7.6 | SURVEY_JP_YUTAI | available: backtest_data/yutai_20260904/ |
| JPR10 | 日経225入替の引け板寄せ反転(IR1): 採用側引け値+241bps・翌寄り−122bps t=−4.2(2000-26 n=111)、2017-26は−45bps t=−1.4 | SURVEY_JP_INDEX_EVENTS | available: backtest_data/nk225_events_20260904/ |

### 1.11 JP — §4 係属(JPP1–JPP3)

| ID | 主張(逐語トリム) | 評価報告 | データ状態 |
|---|---|---|---|
| JPP1 | ON1オーバーナイト: フォワード・ペーパー追跡稼働。実弾は口座・リスク上限・明示承認が前提 | PREREG_on1_forward | available: paper_logs/on1_ledger.csv(n=9、蓄積中) |
| JPP2 | マイクロのオークション約定はラージから±数ティックずれるが対称ノイズで純コスト≈0(符号付き往復差+0.6円/8日) | 運用観測 | available: n225f_225labo_20260828/ |
| JPP3 | ONR(J-REIT夜間): 仮通過(第40報§5)。298日重なりでETF夜間+9.2bpsに対し指数≈0 | ao, PREREG_overnight_onr/onr_forward | available: backtest_data/reit_onr_20260904/; partial: paper_logs/onr_ledger.csv(n=1、開始直後) |

### 1.12 PREREG 判定(PR1–PR13)

| ID | 主張(逐語トリム) | 評価報告 | データ状態 |
|---|---|---|---|
| PR1 | PREREG_board_round: Round17一括判定(BI-deep/VR5/TP/GMO-cal) → BI-deep最終閉鎖(R34)・vr最終閉鎖(R35)・TP特徴不通過(AUC0.62/0.40) | ap(第41報) | available: board_round_20260904/ |
| PR2 | PREREG_clock_burst: S12凍結条件ネット≥+5bps・n≥30・日クラスタt≥2/CI>0・maxDD≤1000bps。判定未到達 | y, 係属 | partial: フレッシュテープ蓄積中 |
| PR3 | PREREG_fast_cycle: S8判定手続き凍結→実測で恒久閉鎖(R21) | aa(第26報) | available |
| PR4 | PREREG_fx_s4_judgment: S4後方新鮮2005-14判定→棄却(FXR10) | 第35報 | available: fx_event_ticks_2005_2014/ |
| PR5 | PREREG_matilda_modern: M2 8セルフィージビリティ判定→棄却(R22) | ad(第29報) | available |
| PR6 | PREREG_matilda_taro: M3 4セル判定→棄却(R23)、史上最接近(損益均衡1.13〜1.48倍) | ae(第30報) | available |
| PR7 | PREREG_on1_forward: 記録規則・月次レビュー・停止線凍結、稼働中 | 凍結2026-08-28 | available: paper_logs/on1_ledger.csv(n=9) |
| PR8 | PREREG_onr_forward: J-REIT ETF1343夜間フォワード追跡凍結、記録開始直後 | 凍結2026-09-04 | partial: paper_logs/onr_ledger.csv(n=1) |
| PR9 | PREREG_overnight_on1: 本体判定(1990-2026、n≈9,037) → 全バー通過(JPL4) | 第36報 | available: n225f_225labo_20260828/ |
| PR10 | PREREG_overnight_onr: 本体判定→仮通過(JPP3)。2011以降のETF水準は汚染面で判定不使用 | 第40報 | available: reit_onr_20260904/ |
| PR11 | PREREG_regime_composite: RC1週次方向判定(2020-26非重複350週) → 棄却(R42) | 第38報 | available: regime_composite_20260901/ |
| PR12 | PREREG_spread_mm: SM4セル判定 → 棄却(R26)、maker線閉鎖 | ag(第32報) | available: venue_survey_20260827/ |
| PR13 | PREREG_trend_lt1: LT1判定(BTC15年/ETH10年) → 棄却(R24) | ai(第34報) | available: daily_btcusd_*, daily_ethusd_* |

### 1.13 SURVEY 結論(SV1–SV5、机上調査)

| ID | 主張(逐語トリム) | 評価報告 | データ状態 |
|---|---|---|---|
| SV1 | 注目度日次系列の入手性・事前分布調査: 文献の事前分布は自プロジェクトの既存法則と一致して否定的 | SURVEY_ATTENTION_DATA | external-fetchable: Wikipedia/GDELT/F&G API(調査当時) |
| SV2 | 個別株クロスセクショナル実現可能性: 資本床¥20Mでno-go確定 | SURVEY_JP_EQUITIES | external-fetchable: 東証気配 |
| SV3 | 日経225入替の引け板寄せ効果、一次資料調査(IR1の直接データ源) | SURVEY_JP_INDEX_EVENTS | available: nk225_events_20260904/ |
| SV4 | 日経225マイクロ先物・国内指数先物調査: 商品・資本適合クリア、オーバーナイト効果のみ単独生存の事前分布 | SURVEY_JP_INDEX_FUTURES | available: n225f_225labo_20260828/ |
| SV5 | 優待/配当権利落ちseasonality、一次資料調査(YT1の直接データ源) | SURVEY_JP_YUTAI | available: yutai_20260904/ |

## 2. 監査パケット(45)

A・B・C・E・G は既存 ID を保持。D は FX「東京仲値」家族、F は「規模predictable・方向not」則(注目度・報道トーン・大口ポジション・funding の4系統)に割当。

| ID | タイトル | 主張ID | データパス | 盲検再計算の要求 |
|---|---|---|---|---|
| A | ON1 overnight(日経225先物オーバーナイト) | JPL4,JPL5,JPR4,JPP1,JPP2,PR7,PR9,SV4,JPC3,JPC4 | backtest_data/n225f_225labo_20260828/, paper_logs/on1_ledger.csv | 1990-2026全営業日の引け→翌寄りリターンを独立再構成し、コストモデル(板寄せ0.35bps)込みt値・4時代Sharpeを再現 |
| B | S12 clock burst(時計バースト30分保有) | L6,L10,L11,R10,R11,R12,R40,R38,P5,PR2 | backtest_data/storm_events_20260820/, burst_events_20260820/, candles_FX_BTC_JPY_30d | 約1,190セル探索面のうち凍結1セル(時計窓×先頭×20bps/30-60s×30分保有)を非重複標本で再計算、CI[+7.92,+37.27]・n=40を再現 |
| C | 板不均衡 taker(board imbalance) | L14(規模部分),R13,R33,R34,PR1 | backtest_data/board_round_20260904/ | imb 5bps深度×時計窓の6セルをネット再計算、コスト床5.8bpsとの差を確認 |
| D | FX 東京仲値(Tokyo Fix)ボライベント | FXL3,FXL4,FXR1,FXR2,FXC3 | backtest_data/fx_usdjpy_1m_20260822.csv.gz | 9:54JSTのボラ倍率(3.2x)と前後モメンタム/リバーサルのグロスP&Lをコスト0.71bps込みで再現 |
| E | コスト床+逆選択の壁(核となる市場構造法則) | C1-C7,L1,L5,L8,R1,R9 | backtest_data/candles_FX_BTC_JPY_31d, executions_FX_BTC_JPY_31d, board_round_20260904/ | taker片道3.2bps・maker逆選択6-9bpsを実データから独立再計測 |
| F | 規模predictable・方向not則(注目度/報道トーン/大口ポジション/funding) | L14,R41,R42,P1,P4,PR11,SV1 | data/attention/attention.csv, backtest_data/regime_composite_20260901/, data/funding_rate_history.csv | RC1の6成分(funding, premium, retail L/S, whale L/S, news tone, momentum)個別ICと合成ICを非重複350週で再現、L30確率面の必要p線を再走査 |
| G | ONR(J-REIT overnight) | JPL6,JPL7,JPP3,PR8,PR10,JPR8 | backtest_data/reit_onr_20260904/, data/onr/, paper_logs/onr_ledger.csv | ETF−指数 乖離(gap_bps)を298日重なりで再計算、ETF約定アーティファクト成分を分離 |
| H | JPX夜間プレミアム市場横断+ETFアーティファクト(RB1/UO1/Core30) | JPL6,JPL7,JPR6,JPR7,JPR8 | backtest_data/reit_onr_20260904/, backtest_data/jpx_etf_daily_20260905/(15 銘柄 15 年日足、2026-09-05 追加スナップショット) | N225/TOPIX/JPX400/グロース250/REIT の5系列で夜間プレミアム符号・大きさを横断再計算 |
| I | Matilda M2(在庫グリッド型ミーンリバージョンMM現代化) | R22,PR5 | backtest_data/venue_survey_20260827/(4 時間の板), paper_logs/tape/ticker_*.csv.gz + executions_*.csv.gz(16 日), backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz | 8セル(N{1,4}×時間ラダー2×ゲート2)を再構築し56日次値の符号を再現 |
| J | Matilda M3 TaroCamp(非対称レンジ/ブレイク2モード機) | R23,PR6 | backtest_data/venue_survey_20260827/ | 4セルのbps/unitと損益均衡までの倍率(1.13〜1.48)を再計算 |
| K | Matilda M4 面探索+在庫床法則群(L20-25)+旧bot要素+vr原典 | L20,L21,L22,L23,L24,L25,R17,R27,R32,R35 | backtest_data/candles_FX_BTC_JPY_30d, board_round_20260904/ | 210日57セル面を再走査し正の台地の有無を確認、按分恒等式(width×k=0.8×vola)を検算 |
| L | スプレッドMM対称族(SM)+maker閉じ脚はさみ撃ち法則 | L19,R26,PR12 | backtest_data/venue_survey_20260827/ | 4セルのcapture×2 vs 脚間ドリフト(−3.2〜−3.6bps)を実板から再計測 |
| M | 高速サイクルmakerスキャルパー復活チェック+TP上限(トーナメントC1) | R20,R21,PR3 | backtest_data/venue_survey_20260827/, paper_logs/bot.jsonl | capture+adverse(5s)を実板7日で再計測しバー+0.38bpsとの差を確認 |
| N | 壁板/板厚(壁は吸収体でない+壁板手前指値棄却) | L26,R31 | backtest_data/venue_survey_20260827/ | M24比10倍超の壁の10秒生存率・消失率を再計算 |
| O | f(約定率)とcapture/逆選択の支配軸(実板7日) | L27,L28 | backtest_data/venue_survey_20260827/ | queue-realistic約定モデルでf=18.1%を再現、支配軸(取消方針>スプレッド>寿命>レジーム>約定モデル>vr)の順序を確認 |
| P | 両側フローレジーム(S7) | L29 | backtest_data/venue_survey_20260827/ | W=30s窓のduty11.5%・理想化makerネット+0.38〜+0.76bpsを再計算 |
| Q | bot狩り機構(旧Zaif手法)+約定後5分回転pending | L30,P3 | backtest_data/venue_survey_20260827/ | pick-off後継続幅(+0.6bps@30s〜+1.8bps@30m)を n=29,163 挿入で再現 |
| R | リーダー追随族の死亡診断(機構水準) | L7 | backtest_data/binance_BTCUSDT_1m.csv, candles_FX_BTC_JPY_30d | 210日25セル×5地平ドリフトとコスト床0.079%の差を再計算 |
| S | 通常規模/長期モメンタム/出来高系の棄却 | R2,R3,R4 | backtest_data/candles_*, binance_*, bitbank_xrp_jpy_1m.csv | train/val/OOS分割を再現し丸暗記シグネチャ(train合格→OOS全負)を確認 |
| T | レンジ端タッチ=順張りイベント(核+USD/JPY横断) | L9,FXR3 | backtest_data/candles_FX_BTC_JPY_30d, fx_usdjpy_1m_20260822.csv.gz | 23,642件バリアレースの戻り/突破比率をBTC・USD/JPY双方で再現 |
| U | ヒゲ逆張り・アンカー乖離逆張りの棄却 | R5,R6,R7 | backtest_data/candles_FX_BTC_JPY_30d | 21日訓練窓と新鮮データでの構成乗り換わりを再現 |
| V | 時計窓はタッチ継続を増幅する(L13、時計×タッチの相互作用) | L13 | backtest_data/candles_FX_BTC_JPY_30d | 時計窓内+6.81bps@30分 vs 全日+1.15bpsをn=821/7,157で再計算 |
| W | 出口設計の限界一式(限界+設計棄却+出口グリッド+TP連動+E2採用) | L12,R15,R16,R19 | paper_logs/scalp_paper.jsonl, bot.jsonl | 24セル固定曲面・適応型TP3方式の有意差なしを再現、E2の分散改善を確認 |
| X | 効率性コア法則(消えた遅れ・秒遅れ・ベーシス平均回帰) | L2,L3,L4,R8 | backtest_data/candles_FX_BTC_JPY_31d, candles_XRP_JPY, bitbank_xrp_jpy_1m | lag1相関(薄い市場+0.176 vs 厚い市場+0.019)とベーシス半減期9.1分を再計算 |
| Y | ベーシス再監査2026+薄いペアのリード・ラグ追随棄却 | R29,R30 | backtest_data/venue_survey_20260827/, candles_XRP_JPY | 4脚maker約定仮定下の往復コスト2.82bpsを現行手数料で再現 |
| Z | JFSA効率ギャップ地図+リベートmaker族+GMO第2ベニューpending | L15,R28,P6 | backtest_data/venue_survey_20260827/, paper_logs/venues/ | 11ベニュー/ペアのコスト床とmakerネットを独立再計算 |
| AA | エッジ×レイテンシ曲線とWS化ライン経済閉鎖 | L18,R25 | data/latency/(partial) | エッジ×λ曲線の傾き(−1bps/100ms)と経済天井(+27円/日 vs サーバ費)を再現 |
| AB | 時間による出口緩和はtakerの別名(短スケール=長スケール) | L16 | backtest_data/board_round_20260904/ | 5秒スケール実質taker執行の損失(−7〜−15bps/回)と40分スケール値幅損失を再計算 |
| AC | 日足トレンドフィルタ+LT1長期トレンド棄却 | L17,R24,PR13 | backtest_data/daily_btcusd_*, daily_ethusd_* | SMA/TSMOM6セルのmaxDDとサイクル毎プレミア減衰を15年/10年で再現 |
| AD | スキャルパー武装閾値撤回+バーストスキャルパー本体棄却 | R14,R18 | paper_logs/scalp_paper.jsonl, bot.jsonl | 86イベントのnet −3.83bps・95%CI[−9.2,−2.8]を再計算 |
| AE | メインBOT champion(xborder_momentum)棄却判定 | R36 | paper_logs/bot.jsonl | 30取引net−0.148%/取引・CIを再現、ストップ束7本の寄与を分離 |
| AF | compositeモジュール棄却(C3ロングオンリー・S11シグナル反転フェード) | R37,R39 | paper_logs/bot.jsonl | n=17/n=4セルのCIと符号を再計算 |
| AG | S9嵐時計ブラケット・S10雪崩追随・C2レーダー窓内(棄却3件) | R40,R38,R43 | backtest_data/storm_events_20260820/, burst_events_20260820/, paper_logs/bot.jsonl | 時計窓限定サブセットのCIが0を負側に除外することを再現 |
| AH | 嵐の予兆棄却+嵐の方向予測棄却+時間帯の方向性棄却 | R10,R11,R12 | backtest_data/storm_events_20260820/(16 イベント窓、対照母集団なし), backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz(全時刻母集団), backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz | 予兆13仮説のリフト値、嵐方向49.3/50.7%、時間帯ドリフトのノイズフロア比較を再現 |
| AI | FX スワップ/キャリー経済性(棄却41年) | FXC6,FXR8 | backtest_data/gmo_swap_usdjpy.csv, fred_DGS2.csv, fred_DFF.csv | スワップ仲値公式(銀行間金利差×1.056+0.162bps)とキャリー判定シャープ0.487を41年で再現 |
| AJ | FXイベントティック家族(指標発表ボラ+S4棄却+カレンダー精度) | FXL9,FXL10,FXL11,FXL12,FXL13,FXL14,FXR5,FXR6,FXR10,PR4,FXP1 | backtest_data/fx_event_ticks_2005_2014/, fx_event_ticks_2015_2026/ | 477イベントのE+1sスプレッド爆発と初撃継続/フェードを一次資料カレンダーで再現 |
| AK | FXセッション時計/週末ギャップ/介入テール | FXL1,FXL2,FXL5,FXL6,FXC5,FXR4,FXT1,FXT2 | backtest_data/fx_usdjpy_1m_20260822.csv.gz | UTC時間帯別ボラ・週末ギャップ中央値4.4bpsを再計算 |
| AL | JP株式・先物の実現可能性(資本床+暦アノマリー+日銀ETF+米国型2脚+NT保留) | JPL1,JPL2,JPR1,JPR2,JPR3,JPR5,SV2 | backtest_data/n225f_225labo_20260828/ | 資本床算定式(30銘柄×¥20M)と暦アノマリー|t|<2を再現 |
| AM | JPモメンタム/バリュー/リバーサル ファクター則 | JPL3 | 未スナップショット(SURVEY_JP_EQUITIES本文の一次値のみ) | Fama-French Japan WML/HML/リバーサルの符号・t値を独立再取得して再現(要外部取得) |
| AN | 日経225入替の引け板寄せ反転(IR1) | JPR10,SV3 | backtest_data/nk225_events_20260904/ | 採用側n=111の引け・翌寄りリターンと2017-26減衰(t=−1.4)を再現、生存バイアス除外側を明記 |
| AO | 優待・配当権利落ちseasonality(YT1) | JPR9,SV5 | backtest_data/yutai_20260904/ | 優待株600・対照300の8,159/4,781イベントで権利日−3.8bpsとD−5反転を再現 |
| AP | OI/L-S比 regime pending diagnostics | P2 | paper_logs/oi_snapshots.csv(partial、蓄積中) | 30日到達後にOI急増/L-S極値の規模ゲートを再判定(現状は判定不能) |
| AQ | 外部ツール評価(Freqtrade・crypto MCP) — due diligence | (§7表2行、非経験的) | n/a | 対応取引所リスト等の一次資料記載事実のみを検証(統計的再計算対象なし) |
| AR | データ寿命・基盤事実(bitFlyer31日・OKX30日・Binanceアーカイブ・VM一時性) | (§6、5事実) | 該当なし(インフラ制約の記述) | 各URLに実アクセスし保持期限・ページング可否を再確認 |
| AS | 運用手順的決定(戦略切替カウント再スタート・却下レポート方針・武装閾値運用) | (§5、手続き的) | n/a | 監査対象外(統計的主張ではなく運用ルール)。記録のみ |

## 3. 集計

**主張数(source別、計165件)**: BTCコスト C=7 / BTC法則 L=30 / BTC棄却 R=43 / BTC係属 P=6 /
FXコスト FXC=7 / FX法則 FXL=14 / FX転移事前分布 FXT=3 / FX棄却 FXR=10 / FX係属 FXP=2 /
JPコスト JPC=5 / JP法則 JPL=7 / JP棄却 JPR=10 / JP係属 JPP=3 / PREREG PR=13 / SURVEY SV=5

**パケット数: 45**(A〜Z の26 + AA〜AS の19)。データ可用性別内訳(パケットが跨るものは主要パスで分類):
- **available(完全)**: 33パケット(A,B,C,D,E,G,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z,AB,AC,AD,AE,AF,AG,AH,AI,AJ,AK,AL,AN,AO のうち大半 — 具体的にはbacktest_data配下スナップショットのみで再計算可能)
- **partial(一部欠損・蓄積中)**: F(regime_composite一部+進行中フォワード), H(RB1/UO1/Core30の個別ETF分足が未スナップショット), AA(latency生ログがセッション終了で消失リスク), AM(ファクター一次値が未スナップショット), AP(OI30日到達前)
- **external-fetchable(要外部再取得、URLあり)**: AQ, AR(定義上インフラ確認)。個別主張ではJPC1-3, JPL1, JPL3, JPR1, JPR3, SV1, SV2, FXC7, FXL5, FXL6, FXR8, R41 が該当(一次資料URLは各行に記載)
- **procedural(統計的再計算対象外)**: AS

**「lost」判定の主張(bitFlyer 31日制限またはOKX 30日制限で再計算不能、監査計画§2-8により「未検証」へ格下げ対象)**:
- **L5**(逆選択の壁・シグナル文脈の顔、report x): 元テープがbitFlyer31日超過分で未スナップショット。数値は報告書に残るが生データからの独立再計算は不可能
- **P2 / OKX由来のOI・L-S比履歴**(2026-08-23スナップショット以前の期間): OKX API 30日固定でページング不可、それ以前の生データは取得手段なし。L14の一部(OI関連lift値)・PR1のGMO-cal時系列にも波及

その他の主張は上記の通り backtest_data/ スナップショットまたは外部一次資料で再取得可能であり、「lost」には該当しない。
