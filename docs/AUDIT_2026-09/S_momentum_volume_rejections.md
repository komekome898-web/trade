# Packet S — 通常規模/長期モメンタム/出来高系(いなご)棄却の再監査

対象: R2(通常規模モメンタム, 12構成/FX・BTC・XRP), R3(長期モメンタム 2年4h/日足→train+1.7〜22%/取引・OOS全負「丸暗記」),
R4(出来高系スパイク後ドリフト/いなご/加速)。独自実装で再導出(ノンオーバーラップ・固定保有時間のステップ型バックテスト)。

## 0. コスト前提の検証(着手前チェック)
`src/bot/backtest/engine.py` `CostModel` 既定値: `taker_fee_pct=0.15`, `maker_fee_pct=0.15`, `slippage_pct=0.05`,
`spread_pct=0.10`(半分を片側に適用)。`config/config.yaml` の `costs:` は `taker_fee_pct: 0.15`, `slippage_pct: 0.05`
のみを上書き(`spread_pct` は既定 0.10 のまま)。`scripts/run_backtest.py` はこの `costs:` ブロックのみを読み `CostModel` を構築し、
**`config/products.yaml` の商品別手数料(FX_BTC_JPY: `taker_fee_pct: 0.0`)は参照しない**。
→ 片側コスト = fee0.15%+slippage0.05%+半スプレッド0.05% = 0.25%、往復 **0.50%(50bps)**。課題文の前提「40bps」は
半スプレッド分(片側5bps×2=10bps)を含んでおらず過小。かつ FX_BTC_JPY は実際は fee 0%なので、標準スクリプトで
FX_BTC_JPY を回すと現物(スポット)と同じ 0.15%手数料が誤って課される — これが本パケットの核心の前提誤り。
実測往復2.6bpsの内訳(スプレッド/スリッページ成分)は読める範囲(config/products.yaml/src)からは導出不能(fee0%は確認できるが
スプレッド構成要素の数値根拠は本監査の閲覧範囲外)。→ 2.6bpsは一部検証不能として扱う。

## 1. 手法
グリッド: モメンタム lookback{5,15,60,240}分×hold{5,15,60}分×閾値{0,1σ(train区間のr標準偏差)} = 24セル。
出来高: 60分窓 volume z-score>{2,3}、hold{5,15}分、サプライズ足自身の方向へ同方向 = 4セル。
分割: 時系列60%train/20%val/20%OOS(バーindex基準)。エントリー=lookback/window終了バーclose、エグジット=hold分後close、
非重複(hold幅でステップ)。コスト2種を適用: realized=FX 2.6bps往復(現物2系列は参考として同値+本来の30bps=0.15%×2も比較)、
default40=40bps往復(課題文の前提値、実際のエンジン既定は上記の通り50bps)。
系列: R2=`candles_FX_BTC_JPY_31d_20260823.csv.gz`(44,657本)/`candles_BTC_JPY_20260820.csv`/`candles_XRP_JPY_20260820.csv`。
R3=`binance_BTCUSDT_1m_210d_20260820.csv.gz`(302,403本≈210日、原典の2年4h/日足の代替。整合性用に`binance_XRPUSDT_1m.csv`も)。
R4=`flow_FX_BTC_JPY_20260820.csv`(buy/sell分割あり、方向判定は当該足自身のclose-open)、BTC/XRP は総volume使用。
CIは日クラスタ(OOS内のエントリー日でtrade netをグルーピングし日次平均→t分布95%CI)。MDEはα=.05,power=.8の日次std基準。

## 2. 結果(claimed vs recomputed)

| Claim | claimed headline | recomputed(realized cost) | recomputed(40bps) | Verdict |
|---|---|---|---|---|
| R2 | 条件付きドリフト<往復コスト、12構成 | 3系列×24セル=72、OOS有意正0/72(最良t=1.67,n_days=7,CI[-5.5,+29.0]bps) | 72セル全てOOS非正、多くが有意負(最良t=-4.06) | 数値差異(結論維持) |
| R3 | train+1.7〜22%/取引→OOS全負(丸暗記) | 210日代替でOOS非有意(t=-0.20,CI[-13.9,+11.4]bps,n_days=28,MDE=17.3bps) | OOS有意負(t=-6.27,CI[-51.3,-26.0]bps) | 数値差異(結論維持)/2年4h・日足粒度は未検証 |
| R4 | 同一分内織り込み済み、加速に先行性なし | FX flowでOOS非有意(t=0.48,n_days=4,CI[-11.5,+15.6]bps)。現物2系列は両コストで負 | FX flowもOOS有意負(t=-8.30) | 数値差異(結論維持)、FXセルはn過小 |

FX_BTC_JPY train-best セル(lb15,hold60,1σ): realized→train+3.6bps(n=98)/val-12.2bps/OOS-0.2bps(t=-0.02,CI[-22.9,+22.4]bps)。
40bps→train-33.8/val-49.6/OOS-37.6bps(t=-4.06)。**train・val・OOSがほぼ同水準で負** — 「trainだけ勝ってOOSで崩れる」丸暗記型
ではなく「コストが全区間を等しく食う」型に近い(このグリッドでは)。Binance 210dのtrain-bestセル(lb15,hold60,1σ)も同型:
realized→train-1.9/val-4.6/OOS-1.3bps。原典の「train+1.7〜22%/取引」規模の強い正エッジは本グリッドでは一切再現できず
(最大でも数bps)— 原典はより広い/異なるパラメータ探索だった可能性が高く、丸暗記シグネチャの「train側」は本監査では未検証。

## 3. 対照実験(Q2・Q7)
FX R2 best-cell OOS: 実測+1.9bps(取引単位) vs ランダム符号シャッフル500回 平均-2.7bps・std9.8bps・p(実測以上)=0.33 →
ヌルと区別不能。符号反転コントロール=-7.1bps(反転すると悪化、方向は弱く正しいが無意味な大きさ)。
Binance R3 best-cell OOS: 実測-6.6bps vs シャッフル平均-2.7bps・p=0.72(実測はヌルの72%タイル=ヌルより悪い側)→
先読み・過学習の証拠なし、むしろノイズ並みかそれ以下。符号反転=+1.4bps(ほぼゼロ、反転有利とも言えない)。
→ 両ファミリーとも「本物のエッジがOOSで消える」のではなく「そもそもtrainからしてノイズ」との整合性が高い。

## 4. 10問チェック(要点)
1. 分母: R2=72セル(3系列×24)/セルn=11〜5,355取引・OOS日数4〜7日。R3=48セル(2系列×24)/OOS日数6〜28日。R4=24セル(3系列×4)/OOS日数4〜6日。
2. 対照: §3参照。プラセボと有意差なし(p=0.33/0.72)、符号反転で改善せず→方向性シグナルの実在を支持しない。
3. 換金: realized 2.6bps=BTCPJPY百万円あたり往復260円相当、OOSの点推定は±10〜30bps/取引でこのコスト水準と同オーダー、
   有意水準に届かず(円換算しても月次で数千円規模、規律上のスケール外)。
4. 相対/絶対: 本監査ではレジーム(ボラ三分位・時間帯)別の分割は未実施(予算制約) — 追加検証の余地として明記。
5. 定義の副作用: 非重複ステップ設計のため取引数が原典と一致しない可能性(原典が重複シグナル許容なら母集団が異なる)。
6. データ健全性: bitFlyerメンテ窓(19:00-19:10 UTC)の明示除外は未実施。出来高z-scoreは60分ロール窓のみ、再接続グリッチの個別検知なし。
7. 選択汚染: 72(R2)/48(R3)/24(R4)セルのtrain選択→OOSはいずれも有意水準に届かず、選択効果を主張できるほどの正セルが存在しない。
8. 代替説明: コスト支配(§2「等しく負」パターン)が最も単純な説明で、ボラクラスタリング等を分離するまでもなく成立。
9. 一貫性: FX・BTC・XRP(R2)、Binance BTC・XRP(R3)で符号・有意性のパターンは一致(realizedで非有意、40bpsで有意負)。
10. 反証文/MDE: 「realizedコストでもFX/Binance系列のtrain選択セルにOOSで有意な正エッジは存在しない」は反証可能で、
    本監査ではMDE(R2 FX:25.9bps@n_days=7、R3 Binance:17.3bps@n_days=28)を上回る効果は観測されず、棄却は維持。
    ただし n_days=4(R4 FX flow)は検出力が極めて低く、「存在しないと言い切れる」水準には届いていない。

## 5. 前提の誤り

| premise | source | 実データ | bias方向 | 波及するclaim |
|---|---|---|---|---|
| エンジン既定コスト=往復40bps | 課題文KNOWN PREMISE | `CostModel`既定は`spread_pct=0.10`も課すため実際は往復**50bps**(片側25bps) | 過小評価(実際はより厳しい前提だった) | `scripts/run_backtest.py`のCostModel既定を無変更で使った全ての棄却(source b の momentum/volume系列) |
| FX_BTC_JPY実測往復コスト≈2.6bps | 課題文KNOWN PREMISE | `products.yaml`のfee0%は確認できるが、スプレッド構成要素の数値根拠は閲覧範囲(config/src)に存在せず | 不明(検証不能) | 2.6bpsを再利用する全claim |
| 標準バックテストは商品別手数料を尊重する | 暗黙 | `scripts/run_backtest.py`は`config.yaml costs.taker_fee_pct`(=0.15%固定)のみを使用し`products.yaml`のFX_BTC_JPY fee0%を参照しない | 過大評価(FX_BTC_JPYにspot税率0.15%を誤課金) | **R2・R3(代替)・R4のFXセル全て**。同スクリプト経由の他のFX_BTC_JPY系棄却も同型リスク |
| train区間で強い正エッジ(丸暗記の「train側」) | R3見出し(train+1.7〜22%/取引) | 本監査の同規模グリッドではtrainも数bpsレベルで平坦〜微負、1.7〜22%規模は一切再現せず | 不明(原典設計差の可能性、本監査は「train側」を独立確認できず) | R3、および同じ「丸暗記シグネチャ」を根拠に引用する他claim |
| R3は2年4h/日足で検証された | claim定義 | 監査データは210日1分足のみ(2年4h/日足ファイルは DATA リストに無し) | 粒度不一致 → R3の当該粒度は未検証に格下げ | R3のみ |

## 6. 読んだファイル
`docs/AUDIT_2026-09/PROTOCOL.md`, `docs/AUDIT_2026-09/00_packets.md`(grep: R2/R3/R4/セクション1.3, 267行のSパケット行のみ),
`src/bot/backtest/engine.py`, `config/config.yaml`, `config/products.yaml`, `src/bot/products.py`, `scripts/run_backtest.py`,
`backtest_data/candles_FX_BTC_JPY_31d_20260823.csv.gz`, `candles_BTC_JPY_20260820.csv`, `candles_XRP_JPY_20260820.csv`,
`binance_BTCUSDT_1m_210d_20260820.csv.gz`, `binance_XRPUSDT_1m.csv`, `flow_FX_BTC_JPY_20260820.csv`(ヘッダ+集計のみ)。
`bitbank_xrp_jpy_1m.csv`はヘッダ確認のみで本文計算には未使用(予算内でXRP系はbitFlyer/binanceで代替済み)。

## 総括
R2・R3・R4いずれも「取引可能なエッジは無い」という結論そのものは realized コスト下でも維持(数値差異・結論維持)。
ただし前提には実質的な誤りがあった: (1) 標準バックテストスクリプトが FX_BTC_JPY にスポット税率0.15%を誤課金しており、
エンジン既定コストは課題文の40bpsではなく50bps、(2) 「train合格→OOS全負」の丸暗記シグネチャは、本監査の同規模グリッドでは
「train/val/OOSが揃って負(コスト支配)」という別の型に近く、原典の強いtrain正エッジ(1.7〜22%/取引)は独立再現できず、
(3) R3の「2年4h/日足」粒度そのものは210日1分足代替でしか検証できていない。次アクション: (a) `run_backtest.py`に商品別fee
自動注入を追加(products.yaml参照)、(b) 2.6bpsのスプレッド根拠を一次資料(実約定ログ)で数値提示、(c) R3を実際の2年4h/日足
データで再走査。
