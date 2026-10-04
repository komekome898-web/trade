# 外からの取り込み 第 2 回の案(案の供給 第 3 周)

番号は X2-<組>-<連番>(組は round1 の行の組。組 B は作業者が 2 人いたので 01〜・51〜・81〜に分けた)。各節は作業者の書いたものを、見出しの段を 1 つ下げたほかは手を加えずに並べた。

---

# 作業者 A: 組 A の 14 升(P1〜P5)

## 案の供給 第 3 周 組 A: 外からの取り込みの続き(担当 14 升)

委任文: `r3_prompt_A.txt`。仕様: `docs/DISCUSSIONS/2026-10-02_W3_spec.md` §1 ③・§2・§3。
この文書には評価(効く・効かない・有望)・数値の見込み・過去の検証結果への参照を書かない。データのファイル(backtest_data/・paper_logs/)は 1 つも開いていない。bitFlyer・その他の取引所の API は 1 回も叩いていない(使ったのは WebSearch と WebFetch だけ)。
恒等式: bitFlyer FX_BTC_JPY の価格 ≡ BTCUSD × USDJPY ×(1 + 円の上乗せ)。円の上乗せは「bitFlyer の価格が BTCUSD × USDJPY から離れる分」の意味だけで使う。
出所の文中の数値・判定は「出所の主張」であり、ここで確かめたものではない。

### 着手前の表(CLAUDE.md §0.1)

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 案の供給の 3 周目を再開する | L-616「**とりあえずこれは再開してください。**」 |
| 外の記述(論文・note・X・ブログなど)から、round1 で拾えていない機構を案にする | L-528「**ありとあらゆる多角的な視点から戦略立案をやれと言ってもやってくれなかったこと**」/ L-019「**私が思いつけないあなたが見つけた戦略を、片っ端から検証し**」 |
| オーナーの挙げた例をそのまま探すのではなく、升(誰の・どの段階の跡か)から検索語を作る | L-531「**この私が挙げた例をそのまま探しまーすなんて怠惰で陳腐な追加案は許しません**」 |
| 出所の URL と逐語を付け、英語の逐語に訳を付ける | L-126「**日本人に読めない英語の出力してなんの意味があるの？2度と出すな**」/ L-049「**この文章の意味が何一つわからないので全て説明してください**」 |
| 担当を組 A の 14 升(検索が 1 回だけだった升)に限る | **(該当語なし)** — リードの委任文(`SUPPLY_HANDOFF.md` §2-3、round2/README.md の対象の升) |
| 升ごとに検索語を 2 つ以上作る | **(該当語なし)** — リードの委任文 `r3_prompt_A.txt`「すること 1」 |
| 締め切り(UTC 23:55)で止め、残りを持ち越す | L-451「**なぜあいもかわらず無限の無意味な作業を続けてるんですか？**」(I-013) |

右が空の 2 行は、リードの委任文が決めた範囲と手順。成果物の中身をオーナーの語から外さないので、委任文どおり進めた。

### 升の表

時刻は `date -u +%FT%TZ` の出力。検索を升の組でまとめて並べて打ったため、書き始めはその組の検索を打つ直前に取った時刻(同じ組の升は同じ時刻)、書き終わりはこのファイルを書く直前に取った時刻(全升で同じ)。升ごとに分けて取っていない(迷った点 1)。

| 升 | 書き始め | 書き終わり | 検索語と結果 | 出た案の番号 | 在庫との重なり |
|---|---|---|---|---|---|
| P1-約定 | 2026-10-03T22:38:18Z | 2026-10-03T22:41:53Z | (1)「bitcoin perpetual trade size distribution round lot retail clustering order size 0.001 BTC price impact study」→ 取引の大きさの集まり(trade-size clustering)と価格への影響の論文(Lingnan 大学の論文のページ)、BTC の取引の大きさの分布の論文(repec)、Jupiter の perps の価格影響の議論。Lingnan のページを WebFetch で開いた。(2)「crypto retail market orders weekend Sunday evening time of day buying pressure perpetual futures paper」→ 週末の取引の記事(Blockworks の Hyperliquid の週末の価格発見、btcmarkets、Crypto.com のリサーチ)。Blockworks のページは 301 → 転送先が 404 で開けず(ページ未確認)。開けたページが無いので、この検索からは案にしていない | X2-A-01 | round1 の D1-A-06(約定の大きさで個人の代理を作る)と同じ「約定の大きさ」を使う。X2-A-01 は小さい・大きいではなく「切りのよい大きさに集まる度合い」を使い、出所はそれを情報を持つ側の跡と読む点が違う |
| P1-持ち高 | 2026-10-03T22:38:18Z | 2026-10-03T22:41:53Z | (1)「open interest increase with price decline new shorts entering bitcoin open interest delta price divergence trading rule」→ 建玉と価格の 4 つの組み合わせの記事(axeladlerjr、decrypt、cointelegraph、TradingView)。axeladlerjr を WebFetch で開いた。(2)「funding rate sign flip retail positioning crowded long perpetual average entry price estimate cost basis traders underwater」→ 資金調達率の解説(Kraken、IG、sharpe.ai)。資金調達率の極端な値を偏りの印と読む記述で、round1 の #70・#37 と同じ機構のため案にしていない | X2-A-02 | #37(ロング・ショート比の極端な値)・#70(建玉を状態変数)・D1-A-10(全体の口座比の変化)。X2-A-02 は建玉の増減と価格の増減の向きの組(4 区分)と 7 日の変化の幅を使う点が違う |
| P1-強制 | 2026-10-03T22:38:18Z | 2026-10-03T22:41:53Z | (1)「auto-deleveraging ADL event bitcoin perpetual exchange price effect profitable traders closed paper」→ 自動減額(ADL)の論文(arXiv 2512.01112)、Gauntlet の解説、Arch の解説。arXiv の要旨を WebFetch で開いた。(2)「liquidation price level magnet stop hunt wick round number leverage 100x 50x clusters bitcoin research」→ 清算の帯を磁石と読む記事(sharpe.ai、quadcode、buildix、TradingView の公開スクリプト)。buildix を開いたが、検索の要旨にあった「25 倍のロングは安値の約 4% 下で清算」の文はそのページに無かった。ページにあったのは「Wait for the cascade to happen, then trade the reversal」(連鎖が起きるのを待ってから反転を取る)で、round1 の X1-A-06・O-3c と同じ機構のため案にしていない | X2-A-03 | O-3c・O-6(強制フローの観測)・D1-A-11〜13・X1-A-06 は「清算される側」の強制。X2-A-03 は「勝っている側」が取引所に建玉を閉じられる強制で、強制を受ける側が逆である点が違う |
| P2-約定 | 2026-10-03T22:38:49Z | 2026-10-03T22:41:53Z | (1)「Hyperliquid HLP vault market making counterparty flow vault PnL against traders informed flow analysis」→ HLP(取引所が運営する板の出し手の金庫)の解説(onekey、eco.com、coingecko、zealynx)。onekey を WebFetch で開いた。(2)「on-chain perpetual DEX order flow toxicity maker taker adverse selection decentralized perps study dYdX GMX traders profitable」→ 注文の流れの毒性の一般の解説(ethresear.ch、coinapi、arXiv 2607.11888)。dYdX・GMX の利用者の損益を比べる実証は、この検索で見つからなかった | X2-A-04 | #70(建玉・偏りの外生変数)・X1-A-13・X1-A-26(上位口座・コホートの偏り)。X2-A-04 は利用者の口座ではなく、利用者全体の反対側に立つ HLP の持ち高・損益を読む点が違う |
| P2-持ち高 | 2026-10-03T22:38:49Z | 2026-10-03T22:41:53Z | (1)「Hyperliquid open interest cap asset reached OI cap only reduce orders price effect」→ Hyperliquid の建玉の上限の記述(公式文書の risks・error-responses、goldrush の `perpsAtOpenInterestCap`、onfinality、JELLY の件の記事)。公式文書の risks は 2 つの URL とも 404。goldrush と onfinality を WebFetch で開いた。(2)「Hyperliquid whale unrealized PnL large position holding duration closing behavior take profit price reaction analysis」→ 大口の建玉の合計と含み損益(KuCoin のニュース、出所の主張では Coinglass の値)、大口の清算の記事(forklog、thedefiant)。KuCoin のページを開いた。大口の含み損益は round1 の D1-A-23 と同じ機構のため案にしていない | X2-A-05 | D1-A-24(建玉の集中)・#70。X2-A-05 は取引所の規則(建玉の上限に達すると建玉を増やす注文が拒まれる)を使う点が違う。2 つ目の検索の含み損益は D1-A-23(大口の建値と含み損益)と同じ機構 |
| P3-約定 | 2026-10-03T22:39:11Z | 2026-10-03T22:41:53Z | (1)「Coinbase Premium Index bitcoin US institutional buying signal Coinbase Binance price gap trading」→ Coinbase と Binance の価格差の解説(bit.com、KuCoin、TradingView)。bit.com を WebFetch で開いた。(2)「exchange specific price leadership bitcoin which exchange leads price discovery information share Binance Coinbase OKX study」→ 価格発見の主導の研究(socialscience.international、mlquants、NHH の論文、K33、SSRN)。socialscience.international を開いた | X2-A-06、X2-A-07 | D1-A-29(入金先の取引所ごとの価格の前後)・#28(他市場の先行する動きの追随)。X2-A-06 は 2 取引所の価格差の水準と、その時間帯の癖(米国の取引時間)を使う点が違う。X2-A-07 は #28 と近い。違う点は、動きの起点の取引所が毎回同じではない(出所の主張では 7 割が Binance、3 割がそれ以外)ことを条件に使う点 |
| P3-持ち高 | 2026-10-03T22:39:11Z | 2026-10-03T22:41:53Z | (1)「exchange reserves bitcoin falling stablecoin reserves rising exchange buying power ratio stablecoin supply ratio SSR signal」→ 取引所の BTC 残高とステーブルコイン残高の記事(yahoo finance、theblock、CryptoQuant の文書、decrypt)。yahoo finance を WebFetch で開いた。(2)「Binance futures open interest by exchange share shift whale positions moved between exchanges OI migration CME Binance dominance」→ CME と Binance の建玉の順位の入れ替わりの記事(yahoo finance、cryptometer、forklog、K33)。cryptometer を開いた | X2-A-08、X2-A-09 | #69(オンチェーンの取引所流入出の日次集計)。X2-A-08 は流れではなく残高の比(BTC 残高 ÷ ステーブルコイン残高)を使う点が違う。X2-A-09 は X1-A-31・D1-A-53(CME の先物の差・CFTC)と同じ CME の系列を使うが、取引所の間の建玉の割合の移り変わりを使う点が違う |
| P3-強制 | 2026-10-03T22:39:33Z | 2026-10-03T22:41:53Z | (1)「insurance fund balance drawdown exchange liquidation losses bitcoin insurance fund change as indicator」→ 保険基金の記事(theblock、fxstreet、cointelegraph、bitcoinist の dYdX の件)。theblock を WebFetch で開き、BitMEX の数値は取らず Deribit と仕組みの文だけを取った(L-570)。(2)「margin call collateral haircut altcoin collateral value drop forced selling bitcoin cross margin unified account liquidation spillover」→ 証拠金の追加要求の解説(Arch、Bloomberg の bot の清算、altfins の BTC 財務企業の担保の要求)。altfins の記事は企業の財務(P11)の升の跡で、組 A の担当外のため案にしていない(迷った点 4) | X2-A-10 | O-3c(強制フローの観測)・D1-A-35(清算を 1 件の大きさで層に分ける)。X2-A-10 は清算の注文そのものではなく、清算が破産価格より悪い値で約定した分が残る保険基金の残高の増減を使う点が違う |
| P4-関心 | 2026-10-03T22:39:33Z | 2026-10-03T22:41:53Z | (1)「YouTube crypto influencer video thumbnails bullish bearish sentiment views predict bitcoin returns study」→ YouTube の視聴数・肯定否定の動画の数と BTC の収益の論文(repec、Fay ほか 2025)、Chulalongkorn の論文、The Tie のリサーチ、NTU の報道。repec を WebFetch で開いた。NTU のページは 403(ページ未確認)。(2)「TradingView ideas published long short ratio users bitcoin contrarian sentiment study crowd forecasts」→ TradingView の公開スクリプト(Bitfinex の証拠金のロング・ショートの逆張り)ばかりで、公開の「アイデア」の投稿を集計する研究は、この検索で見つからなかった。スクリプトは #37 と同じ機構のため案にしていない | X2-A-11 | #42(ソーシャル注目度→方向予測)・X1-A-21・X1-A-22(X の投稿)。X2-A-11 は YouTube の視聴数と肯定・否定の動画の数を話題ごとに分けて使う点が違う |
| P4-予告 | 2026-10-03T22:39:33Z | 2026-10-03T22:41:53Z | (1)「Telegram crypto signal channels pump announcements trading signals followers price impact empirical study signal providers」→ Telegram の吊り上げ(pump-and-dump)の研究(arXiv 1811.10109、EPFL の PDF、CEPR、theblock)。arXiv の要旨を開いた。EPFL の PDF は本文を読めず(ページ未確認)。対象が小さい銘柄で、BTCUSD・USDJPY・円の上乗せ・経費のどれに効くかを書けなかったので案にしていない(迷った点 3)。(2)「analyst price targets crypto Twitter predictions accuracy forecast dispersion bitcoin experts forecasts herding study」→ 個別の予想の記事と、Twitter の感情で予測する研究(RSM の論文)。予想の散らばり・同調を扱う研究は、この検索で見つからなかった。(3)「front-running influencer trade calls before posting crypto paid group VIP signal released to free channel later price」→ 有料と無料の signal のチャンネルの説明(finage、umip など)。finage を開いたが本文が無く(ページ未確認)、先回りの記述は、この検索で見つからなかった | (無し) | — |
| P4-約定 | 2026-10-03T22:40:02Z | 2026-10-03T22:41:53Z | (1)「copy trading followers slippage lead trader order execution delay follower orders price impact exchange copy trade mechanism study」→ 複製の注文が指導者の約定の後に出る記述(Tradecopia の文書、metacopier、KuCoin)。Tradecopia を WebFetch で開いた。(2)「Bybit copy trading master trader order triggers follower market orders burst volume same second detection」→ Bybit のヘルプの複製の仕組み(1 注文ずつ複製・価格保護 0.1%)。Bybit のページは 503(ページ未確認) | X2-A-12 | D1-A-44(複数の指導者の約定の重なり)。X2-A-12 は 1 人の指導者の約定の後に複製の注文が遅れて続くことと、取引所の価格保護(許す滑りの上限)で複製の注文が止まることを使う点が違う |
| P4-持ち高 | 2026-10-03T22:40:02Z | 2026-10-03T22:41:53Z | (1)「social trading platform leader performance followers herding disposition effect eToro copy traders empirical paper」→ eToro などの社会的取引の研究(arXiv 1406.7729、Nottingham、ICIS 2019、repec の Erdős ほか)。repec と ICIS のページを開いたが、どちらも実験・学習の研究で、持ち高の機構の記述は無かった。検索の要旨にあった「暗号資産で複製の利用者が勢いに従い、株より連れ動きが強い」の出所のページは、この検索で特定できなかった(ページ未確認)。(2)「copy trading assets under management lead trader followers count capacity limit inflows after high returns performance chasing crypto」→ KuCoin の指導者のレバレッジの上限を運用額で変える告知。KuCoin の告知を開いた | X2-A-13 | D1-A-45・D1-A-46(建玉の年齢・向き別の口座数)・#70。X2-A-13 は取引所の規則(指導者の複製の運用額が大きいほどレバレッジの上限が下がる)を使う点が違う |
| P5-約定 | 2026-10-03T22:40:29Z | 2026-10-03T22:41:53Z | (1)「ETF authorized participants creation redemption timing bitcoin purchase market on close benchmark fixing CF Benchmarks 4pm price impact」→ CF Benchmarks の BRRNY(ETF の基準価格)の記事、cryptoslate、decrypt。CF Benchmarks を WebFetch で開いた。(2)「hedge fund crypto quarter end month end rebalancing flows bitcoin window dressing turn of month effect study」→ 四半期末の配分の戻しの記事(phemex、cointelegraph、Binance Square、tmgm)。phemex を開いた | X2-A-14、X2-A-15 | D1-A-55(CME の再開・休止の時刻)・D1-A-56(満期のロール)・#33・#46(時刻・暦)。X2-A-14 は ETF の基準価格を決める 1 時間の窓、X2-A-15 は四半期末の配分の戻しと次の四半期の始めの戻りを使う点が違う |
| P5-持ち高 | 2026-10-03T22:40:29Z | 2026-10-03T22:41:53Z | (1)「13F filings bitcoin ETF holders hedge funds basis trade share institutional holdings quarterly change interpretation」→ 13F(四半期の保有の届出)の分析(CoinShares、etftrends、blockworks、bnnbloomberg)。CoinShares を WebFetch で開いた。(2)「options market makers dealer gamma vs fund covered call overwriting bitcoin ETF options IBIT call selling volatility suppression fund positioning」→ IBIT のオプションのガンマの記事(spark.money、FlashAlpha、quantwheel)。spark.money を開いた | X2-A-16、X2-A-17 | X1-A-32・D1-A-34・D1-A-53(CFTC・ETF フロー・方向性と裁定の区別)。X2-A-16 は 13F の区分(ヘッジファンドと助言業者)の保有の割合を使う点が違う。X2-A-17 は組 A に同じ機構の案を見つけていない(組 B の P7 オプションのディーラーの升と重なるかは、組 B の案を読んでいないので未確認) |

### 案

#### X2-A-01(升 P1-約定)
- 原文(逐語。WebFetch で開いたページの要旨): 「Motivated by the prevalence of trade-size clustering in financial markets, this study examines whether this trading irregularity affects intraday price dynamics. Based on a global sample, we document that stronger trade-size clustering is associated with lower temporary price impact, consistent with the stealth trading hypothesis. Meanwhile, a positive interaction between clustering and permanent price changes further confirms that clustering trades convey information, suggesting that they originate from informed investors. After partitioning sizes into top, round, and non-round groups, we find that all are informative, despite the finding that top and round (non-round) sizes have more (less) clustering.」
  訳: 「金融市場で取引の大きさが特定の値に集まること(trade-size clustering)が広く見られることを受け、この研究はこの取引の不規則性が日中の価格の動きに影響するかを調べる。世界の標本に基づき、集まりが強いほど一時的な価格影響が小さいことを示し、これは隠密取引の仮説と合う。また、集まりと恒久的な価格変化の正の交互作用は、集まった取引が情報を運ぶこと、つまり情報を持つ投資家から出ていることを示唆する。大きさを最上位・切りのよい値・切りのよくない値の組に分けると、すべてが情報を持つ。ただし最上位と切りのよい値(切りのよくない値)は集まりが多い(少ない)。」
  出所 URL: https://scholars.ln.edu.hk/en/publications/the-price-impact-of-trade-size-clustering-evidence-from-an-intrad/ (「global sample」がどの市場か(暗号資産を含むか)は要旨に無い)
- 意図の地図: 入る条件=未定(切りのよい大きさに集まる約定の向きの偏りが出たとき、その向き、が候補)。出る条件=未定。保有中の判断=未定。強弱の付け方=集まりの度合い(原文の「clustering」の強さ)。最上位・切りのよい値・切りのよくない値の組の分け方は原文にある。
- なぜ: 誰が損をしているか=集まった取引の反対側(出所の主張では情報を持つ側の取引の相手)。なぜ続くか=出所は、情報を持つ側が価格影響を小さくするために大きさを揃えて分ける(隠密取引)と読む。何で崩れるか=集まりが個人の切りのよい注文(例えば 0.01 BTC)で生じていて、情報を持つ側の跡ではない場合。
- 期待する向きと場面: 集まった約定の向きに、恒久的な価格変化が続く場面(向きは出所の主張。当方では未定)。項=BTCUSD(海外の取引所の約定)。
- 反証: 約定を集まりの度合いで層に分けても、その後の価格変化と約定の向きの関係が層で変わらなければ違う。
- 段 3 の種類: (a)。
- 水準とその出所: 原文の要旨に数値の水準は無い。未定(W4 で測る前に決める)。
- 使うデータと遅れ: 海外の取引所の約定の記録(1 件ごとの大きさと向き。例: Binance の約定のアーカイブ、区分 A、日次で翌日)。ライブの経路は未確認。
- 約定の模型: 未定(原文に無い)。

#### X2-A-02(升 P1-持ち高)
- 原文(逐語。WebFetch で開いたページ): 「OI↑Price↑ (confirmation), OI↑Price↓ (bearish divergence), OI↓Price↓ (capitulation), OI↓Price↑ (organic rally).」/「7-day OI change ≥ ±15% with 7-day price change in the opposite direction ≥ ±5%.」/「When these thresholds are met, the divergence is statistically likely to resolve within 7–21 days - either through a correction (if OI↑Price↓) or through trend acceleration (if OI↓Price↑).」
  訳: 「建玉↑価格↑(確認)、建玉↑価格↓(弱気の食い違い)、建玉↓価格↓(投げ)、建玉↓価格↑(自然な上昇)。」/「7 日の建玉の変化が ±15% 以上で、7 日の価格の変化が逆向きに ±5% 以上。」/「この閾値を満たすと、食い違いは統計的に 7〜21 日の間に解消しやすい。建玉↑価格↓なら調整で、建玉↓価格↑なら流れの加速で。」(「統計的に」は出所の主張)
  出所 URL: https://axeladlerjr.com/bitcoin-open-interest-price-divergence-patterns/
- 意図の地図: 入る条件=7 日の建玉の変化と 7 日の価格の変化が逆向きで、原文の閾値を超えたとき。向きは、建玉↑価格↓なら下、建玉↓価格↑なら上(原文の読み)。出る条件=未定(原文は 7〜21 日の間の解消と書くだけ)。保有中の判断=未定。強弱の付け方=未定(変化の幅が候補)。
- なぜ: 誰が損をしているか=建玉↑価格↓では、下げの中で新しく建てた側(原文の別の文の読みでは、流れに逆らってレバレッジを掛ける側)。なぜ続くか=新しい建玉は手仕舞い・強制の注文として後で出る。何で崩れるか=建玉の増加が裁定・ヘッジ(方向を持たない建玉)で生じている場合。
- 期待する向きと場面: 建玉↑価格↓の場面は下、建玉↓価格↑の場面は上(原文の読み。当方では両向きを未定のまま測る)。項=BTCUSD(海外の無期限先物の建玉)。
- 反証: 4 つの区分で分けても、その後 7〜21 日の価格の動きの分布が区分の間で変わらなければ違う。
- 段 3 の種類: (a)。
- 水準とその出所: 7 日・±15%・±5%・7〜21 日(原文の値)。
- 使うデータと遅れ: 海外の取引所の建玉(例: Binance の建玉の履歴。区分と遅れは round1 の P1-持ち高 の跡に従う。未確認)と BTCUSD の日足。
- 約定の模型: 未定(原文に無い)。

#### X2-A-03(升 P1-強制)
- 原文(逐語。WebFetch で開いた arXiv の要旨の一部): 「Autodeleveraging (ADL) is a last-resort loss socialization mechanism for perpetual futures venues. It is triggered when solvency-preserving liquidations fail.」/「We analyze these mechanisms on the Hyperliquid dataset from October 10, 2025, when ADL was used repeatedly to close $2.1 billion of positions in 12 minutes. By comparing production ADL to transparent benchmark allocations, we find that Hyperliquid's production algorithm overshot the minimum trader profit haircut required to cover the shortfall.」/「This comparison also suggests that Binance overutilized ADL far more than Hyperliquid.」
  訳: 「自動減額(ADL)は、無期限先物の取引所の最後の手段の損失の分担の仕組みである。支払い能力を保つための清算が失敗したときに発動する。」/「2025 年 10 月 10 日の Hyperliquid のデータでこの仕組みを分析する。この日、ADL は繰り返し使われ、12 分で 21 億ドルの建玉を閉じた。実際の ADL を透明な基準の割り当てと比べると、Hyperliquid の実際の算法は、不足を埋めるのに要る最小の利益の削減を超えて削っていた。」/「この比較は、Binance が Hyperliquid よりはるかに多く ADL を使ったことも示唆する。」(金額と判定は出所の主張)
  出所 URL: https://arxiv.org/abs/2512.01112
- 意図の地図: 入る条件=未定(ADL の発動を知った時点が候補)。出る条件=未定。保有中の判断=未定。強弱の付け方=未定(閉じられた建玉の額が候補)。
- なぜ: 誰が損をしているか=ADL で建玉を閉じられた勝っている側(自分の意思でなく利益の出ている建玉を失う)。なぜ続くか=清算が板で埋まらないほど一方に偏った急変のときに、取引所の規則で発動する。勝っている側の建玉が消えると、その向きの持ち高が市場から一度に減る。何で崩れるか=閉じられた側がすぐに建て直す場合(建玉が戻る)。
- 期待する向きと場面: 清算の連鎖の最中に ADL が出た場面。勝っている側の建玉が強制的に減るので、急変の向きの続きか戻りかは未定。項=BTCUSD(海外の無期限先物の強制の約定)。
- 反証: ADL が出た急変と、ADL が出なかった同じ大きさの急変で、その後の動きの分布が変わらなければ、勝っている側の建玉が消えることに意味があるというこの「なぜ」は違う。
- 段 3 の種類: (a)。
- 水準とその出所: 原文の要旨に売買の水準は無い。未定(W4 で測る前に決める)。
- 使うデータと遅れ: ADL の発動の記録(Hyperliquid の約定の記録で ADL が区別できるか、Binance で ADL の記録が公開されるかは未確認)。区分は未確認。
- 約定の模型: 未定。

#### X2-A-04(升 P2-約定)
- 原文(逐語。WebFetch で開いたページ): 「HLP acts as a counterparty to traders. If the market trends strongly and many traders are correctly positioned, HLP can lose money, causing the vault's net asset value to decline.」
  訳: 「HLP はトレーダーの取引相手として振る舞う。市場が強く一方に動き、多くのトレーダーが正しい向きに建てていると、HLP は損をし、金庫の純資産価値が下がる。」
  出所 URL: https://onekey.so/blog/ecosystem/what-is-hyperliquid-hlp/
  (参考。検索の要旨の文で、開いたページには逐語で無かったもの。ページ未確認の扱い: 「When users are net long, HLP effectively holds net short exposure. When users are net short, HLP effectively holds net long exposure.」=「利用者が正味でロングのとき、HLP は実質的に正味のショートを持つ。利用者が正味でショートのとき、HLP は実質的に正味のロングを持つ。」経路: WebSearch の結果の要旨。どのページの文かは特定できなかった)
- 意図の地図: 入る条件=未定(HLP の正味の持ち高の向き・大きさ、または HLP の損益の向きが候補)。出る条件=未定。保有中の判断=未定。強弱の付け方=未定。
- なぜ: 誰が損をしているか=HLP が勝つ場面では利用者全体、HLP が負ける場面では HLP(板の出し手として逆選択を受ける)。なぜ続くか=HLP は全銘柄で板を出し清算も引き受けるので、その持ち高は利用者全体の流れの反対側の合計の跡になる。何で崩れるか=HLP が持ち高をすぐに他の場で消していて(ヘッジ)、正味の持ち高が利用者の流れを映さない場合。
- 期待する向きと場面: HLP の正味の持ち高が一方に大きい場面(向きは未定)。項=BTCUSD(公開の無期限先物の大口・利用者全体の流れ)。
- 反証: HLP の正味の持ち高(または損益の変化)と、その後の BTCUSD の動きの間に関係が測れなければ違う。
- 段 3 の種類: (a)。
- 水準とその出所: 原文に水準は無い。未定(W4 で測る前に決める)。
- 使うデータと遅れ: HLP の金庫の口座の持ち高・純資産価値(Hyperliquid の公開の口座の経路で取れるかは未確認。round1 の P2-持ち高 の跡では口座ごとの持ち高は今の値だけ=区分 C)。
- 約定の模型: 未定。

#### X2-A-05(升 P2-持ち高)
- 原文(逐語。WebFetch で開いた 2 ページ): goldrush の文書「list the perp assets currently at their open-interest cap」/「orders that would increase aggregate open interest are rejected」。onfinality の解説「Cannot increase position when open interest is at cap (or similar) appears when the asset's open interest has reached its cap.」
  訳: 「いま建玉の上限に達している無期限先物の銘柄を一覧にする」/「全体の建玉を増やす注文は拒否される」/「建玉が上限にあるとき(またはそれに近い文言で)『建玉が上限にあるため持ち高を増やせない』と出る。これは銘柄の建玉が上限に達したときに出る。」
  出所 URL: https://goldrush.dev/docs/api-reference/hyperliquid-info/perps-at-open-interest-cap.md 、 https://onfinality.io/en/learn/hyperliquid-api-error-handling-order-rejections
  (公式文書 https://hyperliquid.gitbook.io/hyperliquid-docs/risks と https://hyperliquid.gitbook.io/Hyperliquid-docs/risks は WebFetch で 404。検索の要旨にあった「Orders cannot rest further than 1% from the oracle price.」(上限にある間は、注文をオラクル価格から 1% より離して置けない)と HLP の除外は、ページ未確認)
- 意図の地図: 入る条件=未定(銘柄が建玉の上限に達した・外れたとき、が候補)。出る条件=未定。保有中の判断=未定。強弱の付け方=未定。
- なぜ: 誰が損をしているか=未定(上限の間に新しく建てたい側は Hyperliquid で建てられず、他の場に移るか待つ)。なぜ続くか=取引所の規則で、上限の間は建玉を減らす注文だけが通る。何で崩れるか=BTC の上限が実際には到達しない値に置かれている場合(BTC が上限に達するかは未確認)。
- 期待する向きと場面: 上限に達した間と、外れた直後(向きは未定)。項=BTCUSD(公開の無期限先物の大口の建玉)。
- 反証: 上限に達した間・外れた直後の動きの分布が、それ以外の時と変わらなければ違う。
- 段 3 の種類: (a)。
- 水準とその出所: 原文に上限の値は無い(出所は上限が流動性・基準・レバレッジの組で決まると書く旨の要旨。ページ未確認)。未定。
- 使うデータと遅れ: 上限にある銘柄の一覧(`perpsAtOpenInterestCap`。今の値を返す経路と読める。履歴の経路は未確認=区分 C の見込み)。
- 約定の模型: 未定。

#### X2-A-06(升 P3-約定)
- 原文(逐語。WebFetch で開いたページ): 「Coinbase Premium = (Coinbase BTC/USD − Binance BTC/USDT) ÷ Binance BTC/USDT × 100」/「Analysts monitoring the Coinbase Premium in real time had an intraday signal of accelerating US institutional buying several hours before daily ETF flow reports were published」/「Cross-exchange arbitrageurs do narrow persistent spreads, but their capacity is finite, which is why the premium can remain elevated for hours」/「tends to expand during US market hours (9am–5pm ET) and compress or invert during Asian sessions」
  訳: 「Coinbase の上乗せ =(Coinbase の BTC/USD − Binance の BTC/USDT)÷ Binance の BTC/USDT × 100」/「Coinbase の上乗せを実時間で見ていた分析者は、日次の ETF のフローの報告が出る数時間前に、米国の機関の買いが加速している日中の印を得ていた」/「取引所の間の裁定者は続く差を縮めるが、その容量には限りがあるので、上乗せは何時間も高いまま残りうる」/「米国の取引時間(東部時間 9 時〜17 時)に広がり、アジアの時間帯に縮むか逆になる傾向がある」(傾向は出所の主張)
  出所 URL: https://www.bit.com/insights/knowledge-hub/coinbase-premium
- 意図の地図: 入る条件=未定(上乗せが正に広がったとき、その向き=BTCUSD の上、が候補)。出る条件=未定。保有中の判断=未定。強弱の付け方=上乗せの大きさと続いた時間(原文は何時間も残りうると書く)。時間帯(米国の取引時間とアジアの時間帯)で分ける。
- なぜ: 誰が損をしているか=未定(上乗せの間に Binance 側で売っている側が、後から裁定で引き上げられる価格の分を取り逃す、が候補)。なぜ続くか=原文は裁定者の容量に限りがあると書く。何で崩れるか=上乗せが USD と USDT の差(ステーブルコインの値の揺れ)で生じている場合。
- 期待する向きと場面: 米国の取引時間に上乗せが正に広がる場面で上、負に広がる場面で下(向きは原文の読み)。項=BTCUSD(取引所の大口の約定の取引所ごとの偏り)。日本の時間帯ではアジアの時間帯に当たるので、bitFlyer の取引時間との重なりは未定。
- 反証: 上乗せの大きさで層に分けても、その後の BTCUSD の動きが層で変わらなければ違う。
- 段 3 の種類: (a)。
- 水準とその出所: 東部時間 9 時〜17 時(原文の時間帯)。上乗せの閾値は原文に無い(未定)。
- 使うデータと遅れ: Coinbase の BTC/USD と Binance の BTC/USDT の約定・足(どちらも公開の取引所の経路。到達は未確認)。
- 約定の模型: 未定。

#### X2-A-07(升 P3-約定)
- 原文(逐語。WebFetch で開いたページ): 「70% of bitcoin price movements start on Binance and are then followed by the other exchanges. Only 30% start on the semi-regulated exchanges」
  訳: 「BTC の価格の動きの 70% は Binance で始まり、他の取引所が後を追う。半ば規制された取引所で始まるのは 30% だけである」(割合は出所の主張。方法は「minute-level OHLCV prices on 11 products」(11 の商品の 1 分足)と書くだけで、詳しい方法は「forthcoming paper」(近く出る論文)とある)
  出所 URL: https://www.socialscience.international/almost-all-bitcoin-price-transmission-comes-from-binance
- 意図の地図: 入る条件=未定(ある動きがどの取引所で始まったかを判定し、起点が Binance の場合と Coinbase などの場合で分ける、が候補)。出る条件=未定。保有中の判断=未定。強弱の付け方=未定。
- なぜ: 誰が損をしているか=後を追う取引所で、動きが伝わる前の古い価格の板に注文を置いている側。なぜ続くか=価格発見は流動性の深い場で起き、他の場は裁定で追う(出所の別の要旨の文、ページ未確認)。何で崩れるか=取引所の間の伝わりが 1 分より短く、1 分足では起点を判定できない場合。
- 期待する向きと場面: 起点の取引所の動きの向きに、後を追う取引所が続く場面。起点が Binance 以外の 3 割の場面を別に扱う点が #28 との違い。項=BTCUSD(取引所ごとの BTCUSD の起点)。bitFlyer の価格への伝わりは BTCUSD × USDJPY ×(1 + 円の上乗せ)の BTCUSD の項を通る。
- 反証: 起点を判定しても、起点が違う場面の間で、後を追う取引所の動きの遅れ・大きさが変わらなければ、起点で分けることは違う。
- 段 3 の種類: (a)。
- 水準とその出所: 1 分足・11 の商品(原文の値)。判定の閾値は未定。
- 使うデータと遅れ: Binance・Coinbase などの 1 分足(公開の経路。到達は未確認)。
- 約定の模型: 未定。

#### X2-A-08(升 P3-持ち高)
- 原文(逐語。WebFetch で開いたページ): 「CryptoQuant and market dashboards also note the BTC-to-stablecoin reserve ratio at Binance has sunk to multi-year lows, a setup that has preceded past rallies by signaling outsized buying power relative to available BTC on the venue.」
  訳: 「CryptoQuant や市場の計器盤も、Binance の BTC 残高とステーブルコイン残高の比が数年来の低さに沈んだと記している。これはその場で売りに出せる BTC に対して大きな買いの余力があることを示し、過去の上昇の前に見られた形である。」(過去の上昇の前に見られたは出所の主張)
  出所 URL: https://finance.yahoo.com/news/binance-bitcoin-reserves-decline-time-140213722.html
- 意図の地図: 入る条件=未定(比が低い場面、が候補)。出る条件=未定。保有中の判断=未定。強弱の付け方=比の水準と変化。
- なぜ: 誰が損をしているか=未定(取引所に置かれた BTC の売りの供給が少ない中で、後から買う側が高く買う、が候補)。なぜ続くか=取引所に置かれた残高は、すぐ注文に変えられる持ち高の跡である。何で崩れるか=ステーブルコインの残高が買いの待機ではなく、無期限先物の証拠金・取引所の運用で積まれている場合。
- 期待する向きと場面: 比が低い場面で上(出所の読み)。項=BTCUSD(取引所の大口の取引所に置いた持ち高)。
- 反証: 比の水準で層に分けても、その後の BTCUSD の動きが層で変わらなければ違う。
- 段 3 の種類: (a)。
- 水準とその出所: 原文に閾値は無い(「数年来の低さ」のみ)。未定。
- 使うデータと遅れ: 取引所の BTC 残高・ステーブルコイン残高(CryptoQuant の指標。無料で取れるか・履歴の深さは未確認。round1 の P3-移動 の跡と同じ提供元)。
- 約定の模型: 未定。

#### X2-A-09(升 P3-持ち高)
- 原文(逐語。WebFetch で開いたページ): 「CME's average Bitcoin futures open interest dropped below $8 billion in March and around $7.2 billion in early April」/「Binance, mean while, benefited from a different type of demand. Its derivatives market attracts traders seeking leverage, volatility and short-term directional exposure.」/「The change does not necessarily signal that institutions are abandoning crypto. Instead, it suggests that one major source of institutional leverage has become less attractive.」
  訳: 「CME の BTC 先物の平均の建玉は 3 月に 80 億ドルを下回り、4 月の初めに約 72 億ドルになった」/「一方 Binance は別の種類の需要の恩恵を受けた。その派生の市場は、レバレッジ・値動き・短期の方向の持ち高を求めるトレーダーを引き付ける」/「この変化は、機関が暗号資産を捨てていることを必ずしも示さない。機関のレバレッジの大きな源の 1 つの魅力が下がったことを示唆する。」
  出所 URL: https://www.cryptometer.io/news/binance-reclaims-bitcoin-futures-lead-as-institutional-demand-retreats-from-cme/
- 意図の地図: 入る条件=未定(CME と Binance の建玉の割合の変化を、方向の持ち高と裁定の持ち高の割合の代理として使う、が候補)。出る条件=未定。保有中の判断=未定。強弱の付け方=割合の変化の幅。
- なぜ: 誰が損をしているか=未定。なぜ続くか=出所の読みでは、CME の建玉は裁定(先物の差を取る)、Binance の建玉は方向の持ち高で、割合はどちらの持ち高が市場に多いかの跡になる。何で崩れるか=CME の建玉に方向の持ち高が多く含まれる場合。
- 期待する向きと場面: 方向の持ち高の割合が高い場面と低い場面で、値動きの大きさ・強制の起きやすさが違う、が候補(向きは未定)。項=BTCUSD。
- 反証: 割合で層に分けても、その後の値動きの大きさ・向きの分布が層で変わらなければ違う。
- 段 3 の種類: (a)。
- 水準とその出所: 原文の数値は出来事の値で、閾値は無い。未定。
- 使うデータと遅れ: CME の BTC 先物の建玉(区分 A、日次)と Binance の建玉(round1 の P1-持ち高 の跡)。
- 約定の模型: 未定。

#### X2-A-10(升 P3-強制)
- 原文(逐語。WebFetch で開いたページ。BitMEX の数値は取らなかった): 「the insurance fund maintained by Deribit has been slashed almost by half」/「Due to extreme volatility, we have seen a significant impact on our BTC insurance fund.」/「The two crypto derivatives exchanges both have insurance funds to pay out the winning party of a trade when its gains cannot be fully covered by the liquidated side.」/「Deribit grows its insurance fund by charging fees on executing liquidation orders」
  訳: 「Deribit が持つ保険基金はほぼ半分に削られた」/「(Deribit の発言)極端な値動きのため、BTC の保険基金に大きな影響があった。」/「2 つの暗号資産の派生の取引所はどちらも、清算された側で勝った側の利益を払い切れないときに払うための保険基金を持つ。」/「Deribit は清算の注文の執行に手数料を課して保険基金を増やす」
  出所 URL: https://www.theblock.co/post/58703/derivatives-market-liquidations-push-bitmexs-insurance-fund-to-all-time-high-cut-deribits-by-almost-half
- 意図の地図: 入る条件=未定(保険基金の残高の減少=清算が破産価格より悪い値で約定した跡、が候補)。出る条件=未定。保有中の判断=未定。強弱の付け方=減少の幅。
- なぜ: 誰が損をしているか=保険基金(取引所)と、基金が尽きた後に損失の分担を受ける勝っている側。なぜ続くか=清算の注文が板を食い尽くして破産価格より悪く約定したときだけ基金が減るので、基金の減少は板の薄さと強制の大きさが重なった跡になる。何で崩れるか=取引所が基金の残高を遅れて・まとめて公開する場合。
- 期待する向きと場面: 基金が減った急変の後(向きは未定)。項=BTCUSD(取引所の強制の約定)。
- 反証: 基金が減った急変と減らなかった同じ大きさの急変で、その後の動きの分布が変わらなければ違う。
- 段 3 の種類: (a)。
- 水準とその出所: 原文に閾値は無い(「ほぼ半分」は出来事の値)。未定。
- 使うデータと遅れ: 取引所ごとの保険基金の残高の履歴(Binance・Deribit などで公開されているか・更新の間隔は未確認。BitMEX は使わない、L-570)。
- 約定の模型: 未定。

#### X2-A-11(升 P4-関心)
- 原文(逐語。WebFetch で開いた repec の要旨の一部): 「Unlike previous studies, we used YouTube videos to propose two sentiment proxies: investor attention to YouTube (daily number of YouTube video views) and investor sentiment on YouTube (number of positive and negative videos on YouTube). Interestingly, we break down both attention and sentiment per subject.」/「First, we find lead-lag effects between bitcoin returns and per subject investor's attention and sentiment proxies. Second, we show that our deep learning LSTM model relying on the information provided by attention and sentiment supplants benchmark Buy and Hold Strategy to forecast future bitcoin returns.」
  訳: 「先行研究と違い、YouTube の動画を使って 2 つの感情の代理を作る。YouTube への投資家の関心(YouTube の動画の日々の視聴数)と、YouTube 上の投資家の感情(YouTube の肯定的な動画と否定的な動画の数)である。関心と感情はどちらも話題ごとに分ける。」/「第 1 に、BTC の収益と、話題ごとの投資家の関心・感情の代理の間に、先行・遅行の関係を見出す。第 2 に、関心と感情の情報に頼る深層学習の LSTM の模型が、BTC の将来の収益の予測で、基準の買って持つ戦略を上回ることを示す。」(上回るは出所の主張)
  出所 URL: https://ideas.repec.org/a/taf/applec/v57y2025i45p7215-7233.html (Fay, Bourghelle, Jawadi「Bitcoin returns and YouTube news: a behavioural time series analysis」。期間は要旨に「2017–2023」)
- 意図の地図: 入る条件=未定(話題ごとの視聴数の変化・肯定と否定の動画の数の差、が候補)。出る条件=未定。保有中の判断=未定。強弱の付け方=未定。予測の模型(LSTM)は原文の手段で、当方の測り方は W4 で決める。
- なぜ: 誰が損をしているか=関心・感情に遅れて動く個人(公開トレーダーの動画を見て後から入る側)。なぜ続くか=動画は日次で出て、視聴者の注文は視聴の後に出る。何で崩れるか=先行・遅行の向きが逆(価格が動いた後に動画が増える)だけの場合。
- 期待する向きと場面: 未定(原文は先行・遅行の関係と書き、向きは要旨に無い)。項=BTCUSD。
- 反証: 話題ごとの視聴数・動画の数が、その後の BTCUSD の動きに先行しない(価格の後にだけ動く)なら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 日次(原文の粒度)。閾値は未定。
- 使うデータと遅れ: YouTube の動画の数と視聴数(YouTube の公開の API は鍵が要る見込み。鍵が要る経路は使わないので、取得の経路は未確認)。
- 約定の模型: 未定。

#### X2-A-12(升 P4-約定)
- 原文(逐語。WebFetch で開いたページ): 「The leader typically receives better fills. It is the originator of the trade — the order reaches the leader's broker first.」/「Follower orders are replicated after the leader fill event is detected, which means they arrive at the follower's broker slightly later.」/「In fast markets, this time difference can produce meaningful price differences.」
  訳: 「指導者のほうがふつう良い値で約定する。指導者は取引の発信元で、注文は先に指導者の取次に届く。」/「フォロワーの注文は、指導者の約定が検出された後に複製されるので、フォロワーの取次には少し遅れて届く。」/「速い相場では、この時間差が意味のある価格の差を生む。」
  出所 URL: https://docs.tradecopia.com/en/articles/15515228-why-do-follower-orders-fill-at-a-different-price-than-the-leader
  (ページ未確認: Bybit のヘルプ https://www.bybit.com/en/help-center/article/Understanding-Discrepancies-in-Copy-Trading-Positions-between-Master-Trader-s-and-Follower-s は WebFetch で HTTP 503。検索の要旨の文: 複製は「one order at a time, after the Master Trader places them」(指導者が出した後に 1 注文ずつ)、価格保護は「a default maximum slippage allowance of 0.1% per order, which can be adjusted by users up to a maximum of 5%」(1 注文あたり既定で最大 0.1% の滑りを許し、利用者が最大 5% まで変えられる)。逐語はページで確かめていない)
- 意図の地図: 入る条件=未定(指導者の約定が出た直後、同じ向き、が候補)。出る条件=未定(フォロワーの複製の注文が出切った後、が候補)。保有中の判断=未定。強弱の付け方=指導者のフォロワーの数・運用額。
- なぜ: 誰が損をしているか=後から届くフォロワー(指導者より悪い値で約定する)。なぜ続くか=複製は指導者の約定を検出してから出るので、同じ向きの注文が遅れて続く。価格保護があると、価格が許す滑りの外に出た後のフォロワーの注文は出ない(ページ未確認)。何で崩れるか=フォロワーの注文の合計が板に比べて小さい場合。
- 期待する向きと場面: 指導者の約定の直後、同じ向き(短い時間)。価格保護の幅を超えて動いた後は、複製の注文が止まる場面(向きは未定)。項=BTCUSD(海外の取引所の複製の注文)と経費(当方が同じ向きに入るときの滑り)。
- 反証: 指導者の約定の後の短い時間の約定の向きの偏りが、指導者の約定が無い時と変わらなければ違う。
- 段 3 の種類: (a)。
- 水準とその出所: 0.1%・5%(Bybit の価格保護。ページ未確認)。時間の窓は未定。
- 使うデータと遅れ: 指導者の約定の記録(round1 の P4-約定 の跡: OKX の指導者の決済済みの取引、区分 B)と海外の取引所の約定。
- 約定の模型: 未定。

#### X2-A-13(升 P4-持ち高)
- 原文(逐語。WebFetch で開いた KuCoin の告知): 「Effective from 16:00 on July 07, 2026 (UTC)」/「When a lead trader's copy trading AUM is between 100,000 USDT and 400,000 USDT (inclusive), the lead trader can only use up to 20x leverage.」/「When a lead trader's copy trading AUM exceeds 400,000 USDT, the lead trader can only use up to 10x leverage.」/「Current leverage of existing positions: Will not be affected, regardless of whether it exceeds the new maximum leverage.」
  訳: 「2026 年 7 月 7 日 16:00(UTC)から適用」/「指導者の複製の運用額が 100,000 USDT 以上 400,000 USDT 以下のとき、指導者は最大 20 倍のレバレッジしか使えない。」/「指導者の複製の運用額が 400,000 USDT を超えると、最大 10 倍のレバレッジしか使えない。」/「既存の持ち高のレバレッジ: 新しい上限を超えていても影響を受けない。」
  出所 URL: https://www.kucoin.com/announcement/kucoin-copy-trading-adjusts-leverage-limits-for-lead-traders
- 意図の地図: 入る条件=未定。出る条件=未定。保有中の判断=未定。強弱の付け方=未定。案の中身は場面の変数: 運用額の大きい指導者の新しい建玉はレバレッジが低く、清算までの距離が遠い。既存の建玉は高いレバレッジのまま残るので、規則の適用の前に建った建玉と後に建った建玉で清算までの距離の分布が違う。
- なぜ: 誰が損をしているか=高いレバレッジのまま残る既存の建玉の持ち主と、その複製のフォロワー(清算までの距離が近い)。なぜ続くか=取引所の規則で、既存の建玉は変わらず、新しい建玉だけが下がる。何で崩れるか=指導者の建玉の合計が市場の建玉に比べて小さい場合。
- 期待する向きと場面: 清算の帯の推定(round1 の D1-A-03・D1-A-15 の系統)で、指導者の建玉のレバレッジを運用額の階層で置く場面。向きは未定。項=BTCUSD。
- 反証: 運用額の階層で分けた指導者の建玉の清算までの距離が、規則の前後で変わらなければ、この規則が建玉の形を変えるという「なぜ」は違う。
- 段 3 の種類: (a)。
- 水準とその出所: 100,000 USDT・400,000 USDT・20 倍・10 倍・2026-07-07 16:00 UTC(原文の値)。
- 使うデータと遅れ: 指導者の運用額と建玉(KuCoin の指導者の公開の頁で取れるかは未確認。round1 の P4-持ち高 の跡は OKX・Hyperliquid の公開口座で今の値だけ=区分 C)。
- 約定の模型: 未定。

#### X2-A-14(升 P5-約定)
- 原文(逐語。WebFetch で開いた CF Benchmarks のページ): 「All Relevant Transactions that are executed between 15:00 and 16:00 New York Time are added to a joint list」/「The list is partitioned into a number of equally-sized, 12 individual time intervals of 5-minute length」
  訳: 「ニューヨーク時間 15:00〜16:00 に執行された対象の取引はすべて 1 つの一覧に加えられる」/「一覧は、同じ長さの 5 分の 12 個の区間に分けられる」
  出所 URL: https://www.cfbenchmarks.com/blog/optimizing-capital-efficiency-in-replicating-the-brrny-for-the-creation-and-redemption-of-shares-for-us-spot-bitcoin-etfs
  (検索の要旨の文で、ページ未確認: 「Authorized Participants such as Goldman Sachs, Jane Street, and JPMorgan Securities place their creation orders by a set time on any business day—2 pm for Grayscale and 6 pm for BlackRock.」(指定参加者は営業日の決まった時刻までに設定の注文を出す。Grayscale は 14 時、BlackRock は 18 時)。開いたページには、指定参加者がこの窓で売買して基準価格を写す方法・価格への影響の文は無かった)
- 意図の地図: 入る条件=未定(ニューヨーク時間 15:00〜16:00 の窓の前・中・後、が候補)。出る条件=未定。保有中の判断=未定。強弱の付け方=未定(その日の ETF のフローの向きと大きさが候補)。
- なぜ: 誰が損をしているか=未定(基準価格の窓の中で、基準価格で約定したい側の注文がまとまって出るなら、その窓の中で反対側に立つ側が得をし、窓の外で待つ側が古い値で取引する、が候補)。なぜ続くか=ETF の設定・解約は毎日この 1 時間の窓の値で決まる。何で崩れるか=ETF の設定・解約が現物の受け渡し(in-kind)や、窓の外での事前の調達で行われ、窓の中で注文が出ない場合。
- 期待する向きと場面: 平日のニューヨーク時間 15:00〜16:00(日本時間では早朝 4:00〜5:00 または 5:00〜6:00、夏時間による)。向きは未定。項=BTCUSD(ファンドの約定)。
- 反証: この 1 時間の窓の約定の量・向きの偏りが、前後の同じ長さの時間と変わらなければ違う。
- 段 3 の種類: (a)。
- 水準とその出所: 15:00〜16:00 ニューヨーク時間・5 分 × 12 区間(原文の値)。
- 使うデータと遅れ: 海外の取引所の約定(区分 A)と ETF の日次のフロー(round1 の組 B の P6 の跡、区分 A、翌日)。
- 約定の模型: 未定。

#### X2-A-15(升 P5-約定)
- 原文(逐語。WebFetch で開いた phemex のページ): 「If a fund's target allocation to digital assets is 5% and BTC's Q1 decline pushed that weighting down to 3.8%, the fund buys on Monday to get back to target.」/「Rebalancing flows from pension funds and ETF issuers show up as sustained volume over the final 1-2 days of the quarter rather than a single large candle.」/「higher-than-normal volume concentrated in Monday's final hours, with price moves that may reverse within the first 48 hours of Q2 once reporting pressure lifts.」
  訳: 「ファンドの暗号資産への目標の配分が 5% で、第 1 四半期の BTC の下落でその比重が 3.8% に下がったなら、ファンドは目標に戻すために月曜に買う。」/「年金基金や ETF の発行体の配分の戻しの流れは、1 本の大きな足ではなく、四半期の最後の 1〜2 日にわたる続いた出来高として出る。」/「月曜の最後の数時間に普段より多い出来高が集まり、報告の圧力が消えると、第 2 四半期の最初の 48 時間の間に値の動きが戻ることがある。」(「月曜」は 2026 年 3 月末の記事の日付による)
  出所 URL: https://phemex.com/blogs/q1-2026-closes-tomorrow
- 意図の地図: 入る条件=未定(四半期の最後の 1〜2 日に、その四半期の BTC と他の資産の騰落の差から配分の戻しの向きを推定する、が候補)。出る条件=未定(次の四半期の最初の 48 時間、が候補)。保有中の判断=未定。強弱の付け方=四半期の BTC と他の資産の騰落の差。
- なぜ: 誰が損をしているか=未定(配分を期日に戻すために値を選ばず売買するファンド、が候補)。なぜ続くか=四半期末は報告の期日で、配分の戻しは期日に縛られる。何で崩れるか=配分の戻しが ETF の外(現物の受け渡し・期日の前の分散)で済む場合。
- 期待する向きと場面: 四半期の最後の 1〜2 日は配分の戻しの向き、次の四半期の最初の 48 時間はその戻り(原文の読み。向きは当方では未定)。項=BTCUSD。
- 反証: 四半期の最後の 1〜2 日の動きの向きが、その四半期の騰落の差と関係しなければ違う。
- 段 3 の種類: (a)。
- 水準とその出所: 最後の 1〜2 日・最初の 48 時間・5% と 3.8%(原文の例の値)。
- 使うデータと遅れ: BTCUSD と比べる資産(株価指数など)の四半期の騰落(公開の日足)。
- 約定の模型: 未定。

#### X2-A-16(升 P5-持ち高)
- 原文(逐語。WebFetch で開いた CoinShares のページ): 「hedge funds cut exposure by nearly one-third, signaling, in our view, less short-term tactical exposure」/「the main contributor to the hedge fund reduction is the unwinding of the basis trade, a common arbitrage strategy that became less attractive as futures premiums compressed」/「Advisor holdings increased in BTC terms quarter-over-quarter」
  訳: 「ヘッジファンドは持ち高をほぼ 3 分の 1 減らした。我々の見方では、短期の戦術的な持ち高が減ったことを示す」/「ヘッジファンドの減少の主な要因は、先物の上乗せが縮んで魅力が下がった一般的な裁定の戦略であるベーシス取引の巻き戻しである」/「助言業者の保有は BTC 建てで前の四半期より増えた」
  出所 URL: https://etp.coinshares.com/insights/research-data/13f-filings-of-bitcoin-etfs-q1-2025-institutional-report/
- 意図の地図: 入る条件=未定(13F の公表時点で、ヘッジファンドと助言業者の保有の割合の変化、が候補)。出る条件=未定。保有中の判断=未定。強弱の付け方=区分の間の割合の変化。
- なぜ: 誰が損をしているか=未定。なぜ続くか=出所の読みでは、ヘッジファンドの ETF の保有は先物の売りと組のベーシス取引で、方向を持たない。助言業者の保有は方向の持ち高。区分の割合は、ETF の保有のうち方向の持ち高の割合の跡になる。何で崩れるか=13F は四半期末の時点の保有で、公表まで遅れるので、公表時には持ち高が変わっている場合。
- 期待する向きと場面: 未定(方向の持ち高の割合が増えた四半期と減った四半期で、ETF のフローとその後の値動きの関係が違う、が候補)。項=BTCUSD(ファンドの持ち高)。
- 反証: 区分の割合で四半期を分けても、ETF のフローと価格の関係が変わらなければ違う。
- 段 3 の種類: (a)。
- 水準とその出所: 原文の「ほぼ 3 分の 1」は出来事の値で、閾値は無い。未定。
- 使うデータと遅れ: SEC の 13F の届出(四半期ごと。届出の期限は四半期末から 45 日後とされるが、このページで確かめていない=未確認)。区分 B の見込み(周期が粗い)。
- 約定の模型: 未定。

#### X2-A-17(升 P5-持ち高)
- 原文(逐語。WebFetch で開いた spark.money のページ): 「BlackRock launched the iShares Bitcoin Premium Income ETF (BITA) on June 16, 2026, writing covered calls against 25% to 35% of its NAV monthly...」/「IBIT has predominantly operated in a positive gamma environment since its options launch. Large-scale covered call selling by institutions and the resulting dealer positioning has acted as a structural dampener.」
  訳: 「BlackRock は 2026 年 6 月 16 日に iShares Bitcoin Premium Income ETF(BITA)を始めた。純資産の 25%〜35% に対して毎月カバードコールを売る……」/「IBIT はオプションの開始以来、主に正のガンマの環境で動いてきた。機関の大規模なカバードコールの売りと、その結果のディーラーの持ち高が、構造的に値動きを抑える役をしてきた。」(抑える役は出所の主張)
  出所 URL: https://www.spark.money/research/bitcoin-etf-options-derivatives-impact
- 意図の地図: 入る条件=未定(月ごとのコールの売りの建て替えの日の前後、またはカバードコールの運用額の大きさ、が候補)。出る条件=未定。保有中の判断=未定。強弱の付け方=カバードコールの ETF の運用額・売ったコールの行使価格と現在値の距離。
- なぜ: 誰が損をしているか=未定(コールを売ったファンドは上の値動きを手放し、その反対のディーラーは買ったガンマのヘッジで値動きに逆らって売買する)。なぜ続くか=カバードコールの ETF は規則で毎月コールを売る。何で崩れるか=ディーラーが買ったコールを他で売り戻していて、正味のガンマが正にならない場合。
- 期待する向きと場面: 売ったコールの行使価格の近くで値動きが小さくなる場面、建て替え(満期)の前後で抑えが外れる場面(向きは未定)。項=BTCUSD(ファンドの持ち高とオプションのヘッジの約定)。
- 反証: カバードコールの運用額・建て替えの暦で分けても、BTCUSD の値動きの大きさが変わらなければ違う。
- 段 3 の種類: (a)。
- 水準とその出所: 純資産の 25%〜35%・毎月・2026-06-16(原文の値)。
- 使うデータと遅れ: IBIT のオプションの建玉・行使価格(取得の経路は未確認)と BITA の保有の公表(未確認)。
- 約定の模型: 未定。

### 升ごとの案の数

| 升 | 案の数 | 番号 |
|---|---|---|
| P1-約定 | 1 | X2-A-01 |
| P1-持ち高 | 1 | X2-A-02 |
| P1-強制 | 1 | X2-A-03 |
| P2-約定 | 1 | X2-A-04 |
| P2-持ち高 | 1 | X2-A-05 |
| P3-約定 | 2 | X2-A-06、X2-A-07 |
| P3-持ち高 | 2 | X2-A-08、X2-A-09 |
| P3-強制 | 1 | X2-A-10 |
| P4-関心 | 1 | X2-A-11 |
| P4-予告 | 0 | — |
| P4-約定 | 1 | X2-A-12 |
| P4-持ち高 | 1 | X2-A-13 |
| P5-約定 | 2 | X2-A-14、X2-A-15 |
| P5-持ち高 | 2 | X2-A-16、X2-A-17 |
| 計 | 17 | |

検索の回数: WebSearch 29 回(P4-予告 は 3 回、他の 13 升は各 2 回)。WebFetch 31 回(うち開けなかったもの: Blockworks 301→404、Hyperliquid 公式文書 404 × 2、NTU 403、EPFL の PDF 本文が読めず、finage 本文無し、Bybit 503)。

### 持ち越し

- 14 升はすべて通した(締め切り UTC 23:55 の前に終えた)。
- ページ未確認のまま残した引用: X2-A-04 の参考の文(HLP の正味の持ち高の向き)、X2-A-05 の公式文書(1% の規則・HLP の除外)、X2-A-12 の Bybit のヘルプ(503)、X2-A-14 の指定参加者の注文の時刻。次の周で取り直す。
- P4-予告 は 3 回の検索で案が出なかった(下の迷った点 3)。
- P4-持ち高 の検索の要旨にあった「暗号資産で複製の利用者が勢いに従い、株より連れ動きが強い」の出所のページを特定できなかった。

### 迷った点

1. 時刻の取り方: 検索を升の組でまとめて並べて打ったので、升ごとの書き始めは組の検索の直前の時刻、書き終わりはこのファイルを書く直前の 1 つの時刻にした。升ごとの所要時間はこの表からは出せない。
2. X2-A-01 の出所は「global sample」(世界の標本)とだけ書き、暗号資産を含むかが要旨から分からない。暗号資産の市場の記述ではない可能性があるが、升 P1-約定 の跡(約定の大きさ)を使う機構なので案にした。
3. P4-予告 の 1 つ目の検索で開いた論文(Xu・Livshits「The Anatomy of a Cryptocurrency Pump-and-Dump Scheme」、https://arxiv.org/abs/1811.10109)の要旨の逐語: 「We then build a model that predicts the pump likelihood of all coins listed in a crypto-exchange prior to a pump.」(吊り上げの前に、取引所に上場しているすべての銘柄の吊り上げの起きやすさを予測する模型を作る)。対象は小さい銘柄の吊り上げで、BTCUSD・USDJPY・円の上乗せ・経費のどれに効くかを書けなかった。仕様 §2-1「どの項にも効かない案は、案ではなく誤りである」に当たると判断して案にしなかったが、捨てたのではなく、項を書ける読み替えがあるかはリードの判断に残す。
4. P3-強制 の 2 つ目の検索で見つかった altfins の記事(BTC を持つ企業の担保の要求)は、企業の財務(P11)の升の跡で組 A の担当外のため案にしなかった。組 C の升に回すかはリードの判断に残す。
5. X2-A-07 は round1 在庫の #28(他市場の先行する動きの追随)とほぼ同じ機構で、違いは「起点の取引所が場面ごとに違うこと」を条件にする点だけ。重なりとして番号を付けずに残すべきか迷ったが、委任文の「重なっても違う点があれば案にして、違う点を書く」に従って案にした。
6. X2-A-17 は組 B の P7(オプションのディーラー)の升と重なる可能性がある。組 B の案は読んでいないので重なりは未確認。


---

# 作業者 B1: 組 B の P6・P7

## 案の供給 第 3 周 作業者 B1: 升 P6(ETF)・P7(オプションのディーラー)の外からの取り込み

書き始め: 2026-10-03T22:38:12Z / 書き終わり: 2026-10-03T22:47:44Z(どちらも `date -u +%FT%TZ` の出力)。委任文: scratchpad の `r3_prompt_B1.txt`。

### 着手前の表(CLAUDE.md §0.1)

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 外の記述(論文・ブログ・取引所のリサーチ・X)から、round1 で拾えていない売買の機構を案にする | L-528「**ありとあらゆる多角的な視点から戦略立案をやれと言ってもやってくれなかったこと**」/ L-019「**私が思いつけないあなたが見つけた戦略を、片っ端から検証し**」 |
| 升(参加者・段階の跡)から検索語を作り、オーナーの挙げた例の語をそのまま探さない | L-531「**この私が挙げた例をそのまま探しまーすなんて怠惰で陳腐な追加案は許しません**」 |
| 出所の URL と逐語を付け、英語の逐語に日本語の訳を付ける | L-126「**日本人に読めない英語の出力してなんの意味があるの？2度と出すな**」/ L-049「**この文章の意味が何一つわからないので全て説明してください**」 |
| 担当を P6・P7 の 12 升に限る | **(該当語なし)** — リードの委任文(r3_prompt_B1.txt)の割り当て |
| 締め切り(UTC 23:55)で止め、残りを持ち越す | L-451「**なぜあいもかわらず無限の無意味な作業を続けてるんですか？**」(I-013) |
| 案を評価せず、測れる形への設計・測定をしない | L-019「**過去の検証結果を軸にした優先度など何の意味もない**」(評価の禁止の経緯。測定をしないのは L-606・L-611 のリードの分担で、オーナーの逐語は SUPPLY_HANDOFF.md §0 の L-611「**設計と分析はあなたの担当なので、今は次のカードの設計はしなくていいですが**」) |

右が空の 1 行(担当の升の範囲)はリードの委任の割り当てで、成果物の中身をオーナーの語から外さないので、問いにせずに進めた。

### 取得の方法についての注(全案に共通)

- 検索は WebSearch、ページは WebFetch で開いた。WebFetch はページを小さなモデルで読んで答えを返す道具で、返ってきた「逐語」は原文と字句が一致するかを私が原文の生の文字列と照合していない。下の原文の欄で【照合未了】と書いたものはこの経路で取ったもの。
- 1 件(arXiv 2109.02776)だけは PDF を保存して `pdftotext` で文字にし、原文の文字列を直接写した【照合済み】。
- WebFetch が 403・404・410 を返したページは「ページ未確認」と書き、引用は検索結果の要約の文として扱った。

### 升の表

時刻の注: 検索は升をまたいで並べて打ったため、升ごとの書き始め・書き終わりを個別には取っていない。下の時刻は、この作業全体の `date -u +%FT%TZ` の実測(書き始め 22:38:12Z、検索と取得の最後 22:42:29Z、ファイルの書き終わりは末尾)。升ごとの欄には同じ値を入れた(迷った点 1)。

| 升 | 書き始め | 書き終わり | 検索語と結果 | 出た案の番号 | 在庫との重なり |
|---|---|---|---|---|---|
| P6-関心 | 2026-10-03T22:38:12Z | 2026-10-03T22:42:29Z | (1) `bitcoin ETF options open interest IBIT call skew retail sentiment signal bitcoin` → IBIT の歪み(skew)を機関の向きの読みとして使う記述(heygotrade・ambcrypto・Glassnode の IBIT Skew Index・Yahoo・marketchameleon・Saxo・SpotGamma)。<br>(2) `IBIT options put call ratio skew predicts bitcoin price analysis glassnode IBIT skew index` → Glassnode の「IBIT Options Metrics Live on Glassnode」(IBIT と Deribit の予想ボラ・歪みの乖離の記述)。ページを開いた(301 の転送先 research.glassnode.com で取得)。<br>(3) `site:x.com IBIT options skew bitcoin dealers hedging ETF` → X の投稿は結果に出ず、SpotGamma・Glassnode・Saxo などのページだけが出た。この検索で X の投稿は見つからなかった。 | X2-B-01 | 重なり無し。round1 の D1-B-1・X1-B-1 は検索量(Google Trends)で、オプションの値付けは使っていない。D1-B-9・X1-B-4(DVOL)は Deribit だけの予想ボラで、ETF 側(IBIT)との乖離は使っていない。 |
| P6-予告 | 同上 | 同上 | (1) `model portfolio allocation bitcoin ETF wirehouse advisors approval date announced inflows anticipate rebalance` → 大手 4 社の証券会社(wirehouse)が顧問に ETF を勧められるようになる見通し(The Block・Yahoo・fxstreet・etf.com ほか)。<br>(2) `BlackRock model portfolio adds IBIT allocation announcement bitcoin flows` → BlackRock がモデルポートフォリオに IBIT を 1〜2% 入れた報道(The Block・etf.com・decrypt ほか)。The Block のページを開いた。<br>(3) `bitcoin ETF quarter-end rebalancing month-end outflows pattern institutional rebalance trading` → K33 の「月末の前後 6 営業日」のフローの記述(fxstreet・tmgm・decrypt)。decrypt のページには K33 の文が無かった。<br>(4) `K33 Vetle Lunde ETF flows month-end rebalancing six trading days diverged trend bitcoin underperformed S&P 500` → tmgm の同じ記事(2026-07-01)。ページを開いた。 | X2-B-02<br>X2-B-03 | X2-B-02: round1 の D1-B-2(新商品・新機能の判断の期日と上場日)と「予定の日付で場面を切る」点で近い。違い: D1-B-2 は SEC の判断と上場の日、X2-B-02 は販売経路(モデルポートフォリオ・証券会社の顧問)への採用の発表で、注文の主が違う。<br>X2-B-03: 重なり無し(round1 の P6 に暦の月末の案は無い)。 |
| P6-移動 | 同上 | 同上 | (1) `CME bitcoin futures annualized basis compression ETF outflows hedge fund cash-and-carry unwind correlation analysis` → ベーシスの縮みと ETF の流出を結ぶ記述(dlnews 2 件・amberdata・cointelegraph ほか)。amberdata のページを開いた。<br>(2) `Coinbase premium index US session demand ETF creation buying spot bitcoin intraday indicator` → Coinbase の上乗せ(Coinbase と Binance の価格の差)を米国の需要・ETF のフローの先取りとして読む記述(bit.com・buildix・kucoin ほか)。buildix のページを開いた(求めた文の一部は無かった)。 | X2-B-04<br>X2-B-05 | X2-B-04: D1-B-3〜5・X1-B-2 は日次フローの符号・連続・大きさ・公表を使い、流出の「中身」(ベーシス取引の巻き戻しか、売り切りか)を分けていない。違い: 流出を CME のベーシスの水準で 2 つに分ける。<br>X2-B-05: D1-B-5(公表の直後の追随)と「フローの公表」を軸にする点で近い。違い: 公表の前に、立会中の取引所間の価格差からフローを先読みする。 |
| P6-約定 | 同上 | 同上 | (1) `bitcoin ETF premium discount to NAV arbitrage signal Coinbase 4pm fixing CF Benchmarks` → 16:00 ET の CF Benchmarks の値で基準価額が決まる記述、その構成取引所と他の取引所の差で AP の注文を先回りする記述(dlnews)、IBIT の基準価額への上乗せ(NYDIG)。dlnews のページを開いた。NYDIG は 404(ページ未確認)。<br>(2) `bitcoin ETF flows US market open 9:30 ET bitcoin price intraday pattern "US open" selling` → 米国の寄り付きでの下げの記述(benzinga・mexc・TheFullFX・decrypt)。benzinga は 403、mexc は 410(ページ未確認)。TheFullFX のページを開いた(出来高が 14 時・20 時 UTC に偏る記述)。<br>(3) `"10am dump" bitcoin Jane Street US open pattern` → 10 時の下げの説と反論(Yahoo・cointelegraph・beincrypto ほか)。Yahoo(2026-02-26)のページを開いた。 | X2-B-06<br>X2-B-07 | X2-B-06: D1-B-7(ETF 株と基準価額の乖離を AP の注文として使う)と、AP の設定・償還を軸にする点で近い。違い: 基準価額を決める 16:00 ET の参照価格の構成取引所と、構成外の取引所(Binance)の価格差を使い、ETF 株の価格は使わない。D1-B-6(米国の立会の内外)とは「時計の窓」で近いが、窓の根拠が基準価額の決定時刻(20 時 UTC)に絞られている。<br>X2-B-07: D1-B-6 と「米国の立会」で近い。違い: 寄り付き後の最初の 1 時間という特定の窓と、その窓の下げという向きの主張を持つ(出所の主張、反論あり)。 |
| P6-持ち高 | 同上 | 同上 | (1) `13F filings bitcoin ETF holders hedge funds basis trade unwind price impact` → 13F の届け出から見たヘッジファンドの持ち分の減少、ベーシス取引の巻き戻しの記述(itiger 経由の MarketWatch・CF Benchmarks・etftrends・ForkLog ほか)。itiger と ForkLog のページを開いた。<br>(2) `IBIT covered call overwriting ETF holders sell calls YieldMax bitcoin option income funds supply upside volatility` → IBIT の上でコールを売る ETF(YieldMax の YBIT、BlackRock の BITA)の記述。The Block の BITA の記事を開いた。 | X2-B-08<br>X2-B-09 | X2-B-08: D1-B-8(発行体別の保有の増減)・X1-B-3(保有の総量の頭打ち)は発行体の側の保有。違い: 保有者の種類(ヘッジファンド・顧問)の構成を 13F で見る。<br>X2-B-09: 重なり無し(round1 の P6 にオプションの売りの持ち高は無い)。P7-持ち高の D1-B-12・X1-B-6(ガンマの符号)と機構の後半が近い。違い: ガンマの符号の出所を「ETF の保有者のコールの売り」という構造に置く。 |
| P6-強制 | 同上 | 同上 | (1) `2x leveraged bitcoin ETF BITX daily rebalance end of day buying selling impact bitcoin futures close` → BITX が毎日、先物を売買して 2 倍に戻し、期近から期先へ毎日乗り換える記述(volatilityshares の資料)。「How BITX Works: Beyond the Basics」のページを開いた(時刻と CME の名は、そのページに無かった)。<br>(2) 上の P6-移動 (1) の検索(ベーシスの縮みと巻き戻し)の結果のうち、「価格の下落 → ベーシスの縮み → 巻き戻し → さらに下落」の輪の記述と、採算の下限(年率およそ 5%)の記述を、この升の跡(採算の下限で機械的に閉じられる持ち高)として使った。同じ検索を 2 升で使った(迷った点 2)。 | X2-B-10<br>X2-B-11 | X2-B-10: D1-B-39(レバレッジ型 ETF の日次のリバランス)と機構が同じ。違い: D1-B-39 は「銘柄の存在・規約を確認していない【仮定】」と書いた案で、この周に出所(BITX の資料)で、先物で行うこと・期近から期先へ毎日乗り換えることを確かめた。乗り換え(先物の期の間の売買)が加わる点を違いとして案にした。<br>X2-B-11: X2-B-04 と同じ跡(ベーシス)。違い: X2-B-04 は流出の分類、X2-B-11 はベーシスが採算の下限を割ったときの機械的な巻き戻しの輪。 |
| P7-関心 | 同上 | 同上 | (1) `Deribit options put-call skew 25 delta risk reversal sign flip bitcoin trading signal research` → 25 デルタのリスクリバーサル(同じデルタのプットとコールの予想ボラの差)の意味と、IBIT と Deribit の両方の百分位の記述(Anchorage Digital・Deribit Insights の週報・cryptodatadownload ほか)。Anchorage のページを開いた。<br>(2) `bitcoin options dealer short gamma "vanna" "charm" flows implied volatility drop spot rally crypto` → FlashAlpha の BTC のページ(vanna・charm の定義)。この升ではなく P7-持ち高に使った。 | X2-B-12 | D1-B-9・X1-B-4(DVOL)と「オプションの値付けを関心の跡にする」点で近い。違い: DVOL は予想ボラの水準、X2-B-12 は上下の非対称(歪み)とその符号の反転、および 2 つの場所(IBIT と Deribit)の歪みの揃い・離れ。X2-B-01 とは同じ出所の系列を使うが、X2-B-01 は 2 つの場所の差、X2-B-12 は両方の水準の百分位と符号の反転。 |
| P7-予告 | 同上 | 同上 | (1) `crypto structured products dual currency investment covered call vaults weekly auction Friday options selling bitcoin volatility supply` → DeFi のオプションの金庫(DOV)が毎週金曜にオプションを競りで売る記述(risk.net / fx-markets・themothership・bhft・amberdata ほか)。fx-markets と themothership のページを開いた。<br>(2) `option vault auction Friday implied volatility dip market makers anticipate supply weekly calls crypto Paradigm DOV auction` → Paradigm の「DOV Auctions And The Friday Problem」(2022-09-22)。ページを開いた。 | X2-B-13 | 重なり無し(round1 で案が出なかった升)。round1 の P7-予告の検索は「ディーラーがヘッジの予定を公開する」記述を探して見つからなかった。この周は、ディーラーが買う側として「毎週決まった時刻にオプションの売りが来る」と予め分かっている跡を探した。 |
| P7-移動 | 同上 | 同上 | (1) `bitcoin options roll open interest to next expiry rollover flows quarterly roll dealers hedge adjustment` → 四半期の満期での建玉の減少の報道(The Block・cryptoslate・itiger ほか)。The Block のページを開いたが、乗り換え(期先への移し替え)とディーラーのヘッジの記述は無かった。<br>(2) `options market makers hedge on Binance perpetual vs CME futures venue migration Deribit hedging venue bitcoin funding rate impact` → 資金調達率の場所ごとの差、CME の 24 時間化(2026-05-29)の記述(sharpe.ai・ledger ほか)。ディーラーのヘッジの場所の移り変わりを売買に使う記述は、この検索で見つからなかった。<br>(3) `site:x.com Deribit options expiry roll dealers delta hedge unwind weekend bitcoin` → X の投稿は出ず、decrypt・Deribit Insights のページが出た。「満期のあとヘッジが外れ、週末の大きな動きにつながることがある」という decrypt の文が検索結果の要約に出た(ページ未確認。P7-強制で使った)。 | 書けない。理由: 3 回の検索で、オプションのディーラーの「移動」(担保・建玉・ヘッジの場所の移し替え)を売買に使う記述が見つからなかった。themothership の「毎週金曜 23:00 UTC に金庫の預かり資産を担保として Opyn に入れる」という記述は担保の移動に当たるが、移動の主は金庫(オプションの売り手)でディーラーではなく、売買の機構は X2-B-13(競りの予定)と同じなので別の案にしない。 | round1 の D1-B-10(Deribit 宛ての担保の動き)と、担保の移動を跡にする点で同じ方向。案は立てていない。 |
| P7-約定 | 同上 | 同上 | (1) `Deribit options taker flow aggressor buys calls "net premium" bitcoin intraday spot lead options flow research paper` → Glassnode の「Options Premium & Taker Flow Analytics」(2025-10-02)、arXiv 2109.02776「Net Buying Pressure and the Information in Bitcoin Option Trades」、falsifylab(round1 の X1-B-5 の出所)。Glassnode のページと arXiv の要旨を開いた。<br>(2) `bitcoin option order flow predicts returns paper informed trading OTM puts Deribit "order imbalance"` → 同じ arXiv の PDF。PDF を保存して文字にし、要旨と本文の該当の文を写した。ほかに「The Quarter-Hour Effect」(arXiv 2607.09426、暗号資産の先物の 15 分ごとの現象)が出たが、P7 の升ではないので開いていない(持ち越し 2)。 | X2-B-14<br>X2-B-15 | X2-B-14: D1-B-11(ブロックの向きからヘッジの向き)・X1-B-5(ブロックのコール・プットの偏り)と「約定の向き」を使う点で近い。違い: 出所の主張は、注文の偏りが予想ボラ・実現ボラを先に示し、価格の向きは弱いというもの。案の効く先が向きではなく値動きの大きさ。<br>X2-B-15: X1-B-5 と近い。違い: ブロックの名目で絞らず、テイカー(板を取りに行った側)が払った・受け取ったプレミアムの額で、行使価格ごとの「磁石」の水準を作る。 |
| P7-持ち高 | 同上 | 同上 | (1) `bitcoin options gamma squeeze dealers short calls forced buy spot rally strike above crypto` → ディーラーのショートガンマで上昇が加速する記述(blockworks・jarvislabs・beincrypto・coindesk ほか)。jarvislabs のページを開いた。<br>(2) `IBIT options open interest by strike gamma exposure bitcoin price US hours SpotGamma IBIT positional analysis` → IBIT のガンマ(FlashAlpha・kucoin・quantwheel)。FlashAlpha の IBIT の記事を開いた。<br>(3) P7-関心 (2) の検索の FlashAlpha の BTC のページ(charm・vanna)を開いた。 | X2-B-16<br>X2-B-17 | jarvislabs の機構(ショートガンマのディーラーが上昇で買う)は round1 の D1-B-12・X1-B-6 と同じなので案にしない(在庫 = D1-B-12・X1-B-6)。<br>X2-B-16: D1-B-12・D1-B-13・X1-B-6 はガンマ(価格の変化)によるヘッジ。違い: 時間の経過(charm)と予想ボラの変化(vanna)によるヘッジの売買で、日の終わり・週の終わりに出る。<br>X2-B-17: D1-B-12 と近い。違い: ガンマの帳簿を場所(IBIT と CME・Deribit)で分け、IBIT の帳簿は保有者のコールの売りにより構造的にディーラーのロングガンマになるという出所の主張を使う。X2-B-09 と同じ機構を P7 の側から見たもの(X2-B-09 は保有者の売りの量、X2-B-17 は場所ごとのガンマの帳簿の違い)。 |
| P7-強制 | 同上 | 同上 | (1) `bitcoin options "pin risk" expiry 08:00 UTC Deribit settlement index 30-minute TWAP manipulation price before expiry` → 満期の 08:00 UTC・ピン留め・最大苦痛価格の記述(mexc・fxstreet・decrypt・Yahoo ほか)。round1 の X1-B-7 と同じ種類の記述。<br>(2) `Deribit delivery price options settlement "30 minutes" average index before 08:00 UTC` → Deribit のサポートの「Settlement」(07:30〜08:00 UTC の指数の時間加重平均)。ページは 403(ページ未確認)。<br>(3) P7-移動 (3) の検索で出た Deribit Insights の「Option Backtest – Selling Weekend Vol」(2024-09-19)。ページを開いた。 | X2-B-18<br>X2-B-19 | X2-B-18: D1-B-14(満期でヘッジが解消される)・D1-B-15・X1-B-7(最大苦痛価格)と、満期を場面にする点で近い。違い: 満期の時刻ではなく、受け渡し価格を決める 30 分の窓(07:30〜08:00 UTC)の中の値動きを場面にする。<br>X2-B-19: D1-B-14 と「満期の前後」で近い。round1 の在庫の #45(週末ギャップ)と週末で近い。違い: 日曜 08:00 UTC に満期の来る短期のオプションの売りという、週末の満期の構造を跡にする。 |

検索の回数: WebSearch 28 回(うち 2 回は site:x.com の指定で、X の投稿は結果に出なかった)。WebFetch 30 回(403 が 2、404 が 1、410 が 1、301 の転送が 1、求めた文の全部または一部が無いと返ったものが 6: decrypt・volatilityshares・The Block の満期の記事・buildix・FlashAlpha の IBIT の記事・arXiv の PDF(PDF は保存して自分で文字にした))。

### 案

#### X2-B-01(升 P6-関心)ETF 側のオプション(IBIT)と暗号資産の側のオプション(Deribit)の歪みの差を、2 種類の参加者の関心の差として読む

- 原文【照合未了】: 「Deribit's 1-month 25-delta skew remained modestly call-biased, while IBIT's comparable skew stayed materially more put-skewed, leaving an approximately 15 percentage-point gap on the same underlying BTC exposure.」「ETF-linked options investors appear to be assigning a higher premium to short-term downside protection, while crypto-native options markets remain comparatively less defensive.」「differences in term structure may indicate that TradFi participants are pricing event risk differently from crypto-native traders」
  - 訳: 「Deribit の 1 か月・25 デルタの歪みはわずかにコール寄りのままだった一方、IBIT の同じ歪みはかなりプット寄りのままで、同じ BTC の値動きに対しておよそ 15 ポイントの差が残った」「ETF に紐づくオプションの投資家は、短期の下落への備えに高い値を付けているように見え、暗号資産の側のオプション市場は比べて守りが弱い」「期間構造の違いは、伝統的な金融の参加者が出来事のリスクを暗号資産の側のトレーダーと違うように値付けしていることを示しうる」
  - 出所: https://research.glassnode.com/ibit-options-metrics-live-on-glassnode/ (Glassnode、記事の日付 2026-05-05 と取得結果にある)
- 意図の地図: 入る条件 = IBIT と Deribit の同じ期間・同じデルタの歪みの差が、一方に開いた(または閉じた)時点。向き = 未定(出所は差の意味を述べ、売買の向きの規則は書いていない)。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 差の大きさ(未定)。
- なぜ: 誰が損をしているか = 一方の場所の値付けだけを見る参加者(出所の主張では、2 つの場所の参加者は出来事のリスクを違うように値付けする)。なぜ続くか = IBIT は米国の立会時間だけ取引され、証券会社の流れに乗る参加者が中心で、Deribit の参加者と入れ替わらないため(出所の主張「IBIT is U.S.-listed, ETF-based, and embedded in traditional brokerage and institutional workflows」= 「IBIT は米国上場で ETF に基づき、伝統的な証券会社と機関の業務の流れに組み込まれている」)。何で崩れるか = 同じ参加者が両方の場所で裁定するようになったとき。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = ETF の保有者(伝統的な金融の側)の守りの売り・買いと、それを受けるディーラー。場面 = 2 つの場所の歪みが離れた期間。向き = 未定。
- 反証: 2 つの場所の歪みの差で分けた後の BTCUSD の動き(向き・大きさ)が、差の小さい期間と区別できないと測れたら、「参加者の関心の差が値動きに出る」という「なぜ」は違う。
- 段 3 の種類: (a)。
- 水準とその出所: 1 か月・25 デルタ(出所の記述)。差の閾値は未定(W4 で測る前に決める)。出所の「およそ 15 ポイント」はその時点の観測で、閾値ではない。
- 使うデータと遅れ: IBIT のオプションの歪み(Glassnode の系列 `options.IbitOptions25DeltaSkew*`。区分・料金・履歴の深さは未確認)、Deribit のオプションの値付け(round1 の区分 A、公開 API)。IBIT は米国の立会時間の値だけ。使えるようになる時刻は未確認。
- 約定の模型: 成行(未定)。

#### X2-B-02(升 P6-予告)販売経路(モデルポートフォリオ・証券会社の顧問)への ETF の採用の発表を、後から来る買いの予告として使う

- 原文【照合未了】: 「1% to 2% allocation to the $48 billion iShares Bitcoin Trust ETF ... in its target allocation portfolios that allow for alternatives」「package together funds into ready-made strategies to sell to financial advisers」「tweaks to their holdings can result in massive flows in either direction」
  - 訳: 「代替資産を認める目標配分のポートフォリオで、480 億ドルの iShares Bitcoin Trust ETF に 1〜2% を配分する」「(モデルポートフォリオは)ファンドを組み合わせて既製の戦略にし、金融の顧問に売る」「その保有の小さな変更が、どちらの向きにも巨大なフローを生みうる」
  - 出所: https://www.theblock.co/post/344030/blackrock-adds-bitcoin-etf-to-portfolio-marketed-to-financial-advisors-report (The Block、2025-02-28)
  - 補い(検索結果の要約の文。ページ未確認): 「the big four wirehouses — Merrill Lynch, Morgan Stanley, Wells Fargo and UBS — which control over $10 trillion in client assets, will be "open for business" on Bitcoin exchange-traded funds by the end of the year」(訳: 「顧客資産 10 兆ドル超を持つ大手 4 社の証券会社 — Merrill Lynch・Morgan Stanley・Wells Fargo・UBS — は、年末までに Bitcoin ETF の取り扱いを始める」)。経路: WebSearch の結果(The Block https://www.theblock.co/post/352521/bitwise-cio-big-four-wirehouses-bitcoin-etfs-record-inflows)。ページは開いていない。
- 意図の地図: 入る条件 = 販売経路への採用(モデルポートフォリオへの組み入れ・証券会社の顧問への解禁)の発表の時点。出る条件 = 未定(発表から実際の配分・リバランスの日までの間を場面にするか、発表の直後だけかは未定)。保有中の判断 = 未定。強弱の付け方 = 発表の対象の資産規模(出所の例: モデルポートフォリオの全体)× 配分の比率(出所の例 1〜2%)。向き = 採用は買い、外す発表は売り(出所の「どちらの向きにも」)。
- なぜ: 誰が損をしているか = 発表から実際の配分の売買までの間に、その売買の反対側に立つ参加者。なぜ続くか = モデルポートフォリオの配分は顧問の口座で順に執行され、1 日では終わらないなら(未確認)。何で崩れるか = 発表の時点で先回りの買いが全部入るとき、または配分の額が小さく注文として見えないとき(出所 Yahoo の要約に「incremental inflows for IBIT could be in the millions rather than billions」= 「IBIT への上乗せの流入は数十億ではなく数百万ドル程度かもしれない」とある。ページ未確認)。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = モデルポートフォリオに従う顧問の口座 → ETF の AP の設定 → 現物の買い。場面 = 発表から配分の執行まで。
- 反証: 採用の発表の後の ETF の日次フロー(P6-移動の系列)と BTCUSD が、発表の無い期間と区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 配分 1〜2%(出所の記述)。それ以外は未定。
- 使うデータと遅れ: 発行体・報道の発表の日付(区分 未確認。発表の一覧を集める経路は未確認)、ETF の日次フロー(round1 の区分 A、Farside、翌営業日)。
- 約定の模型: 成行。

#### X2-B-03(升 P6-予告)月末の前後 6 営業日を、機関のリバランスで ETF のフローがそれまでの流れと逆に出やすい窓として使う

- 原文【照合未了】: 「in nine of the past 18 months, ETF flows diverged from the prevailing trend for the rest of the month during the six trading days around month-end」「In several instances, periods when Bitcoin underperformed the S&P 500 were followed by stronger ETF inflows as investors increased their Bitcoin exposure during portfolio rebalancing.」「the relationship has not been consistent enough to be viewed as a reliable market signal」
  - 訳: 「過去 18 か月のうち 9 か月で、月末の前後 6 営業日の ETF のフローが、その月の残りの流れと逆になった」「いくつかの例では、Bitcoin が S&P 500 に負けた期間の後に、投資家がポートフォリオのリバランスで Bitcoin の比率を上げたため、ETF への流入が強まった」「この関係は、信頼できる市場の信号と見なせるほど一貫していない」(最後の文は出所自身の留保)
  - 出所: https://www.tmgm.com/en/analysis/market-news/article/bitcoin-drops-near-58k-as-etf-outflows-surge-downside-risks-persist-202607010253 (TMGM、2026-07-01。K33 Research の記述の引用)
  - 補い: X2-B-04 の出所 itiger(MarketWatch、2025-03-01)の Ledn の CIO の文「Institutions "are faster money." When they've made a profit, or when they're rebalancing...they're going to sell some of the bitcoin at month end or quarter end.」(訳: 「機関は『足の速いお金』だ。利益が出たとき、またはリバランスのときに、月末や四半期末に Bitcoin の一部を売る」)【照合未了】。https://www.itiger.com/hans/news/2516552964
- 意図の地図: 入る条件 = 月末の前後 6 営業日の窓に入った時点で、その月の Bitcoin と S&P 500 の成績の差を見る。向き = Bitcoin が負けていればリバランスの買い(ETF の流入)、勝っていれば売り(出所の機構からの読み。出所は前者の例だけを書いている)。出る条件 = 窓の終わり(未定)。保有中の判断 = 未定。強弱の付け方 = 成績の差の大きさ(未定)。
- なぜ: 誰が損をしているか = 月末のリバランスの売買の反対側に立つ参加者。なぜ続くか = 比率を決めて保有する機関は暦で比率を戻すため。何で崩れるか = ETF の保有者のうち比率で運用する機関の割合が小さいとき(出所の留保: 18 か月のうち残りの 9 か月は当てはまらなかった)。
- 期待する向きと場面: 効く項 = BTCUSD(米国の株との相対の成績で決まる注文)。場面 = 月末・四半期末の前後 6 営業日。
- 反証: 窓の内と外で、月内の成績の差で分けた ETF のフローと BTCUSD の向きが区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 月末の前後 6 営業日、18 か月のうち 9 か月(出所の記述。後者は出所の主張で、閾値ではない)。
- 使うデータと遅れ: 暦(区分 A)、BTCUSD と S&P 500 の日次の値(S&P 500 の取得の経路は未確認)、ETF の日次フロー(区分 A、翌営業日)。
- 約定の模型: 成行。

#### X2-B-04(升 P6-移動)ETF の流出を、CME のベーシス(先物の上乗せ)の水準で「ベーシス取引の巻き戻し」と「売り切り」に分ける

- 原文【照合未了】: 「When that spread collapsed below profitability thresholds, positions closed.」「Selling ETF shares and buying back futures shorts are two sides of the same unwind.」「Capitulation is indiscriminate and persistent. This was episodic and concentrated, with the two largest industry players accumulating throughout.」
  - 訳: 「その差が採算の閾値を下回ったとき、持ち高は閉じられた」「ETF 株を売ることと、先物の売りを買い戻すことは、同じ巻き戻しの両面である」「投げ売り(capitulation)は無差別で持続する。これは断続的で集中しており、最大手 2 社は期間を通じて買い増していた」
  - 出所: https://blog.amberdata.io/the-etf-exodus-decoded-basis-arbitrage-not-capitulation (Amberdata、2025-12-03)
- 意図の地図: 入る条件 = ETF の日次の流出が出た日に、同じ期間の CME の年率ベーシスが縮んでいたか(巻き戻し)、縮んでいなかったか(売り切り)で分ける。向き = 未定(出所は巻き戻しの流出を「機械的」と書き、その後の BTCUSD の向きの規則は書いていない)。出る条件 = 未定。強弱の付け方 = ベーシスの縮みの幅(未定)。
- なぜ: 誰が損をしているか = 流出を全部「売り」と読んで売る参加者(巻き戻しの流出は先物の買い戻しと対になり、方向の持ち高は増えない)。なぜ続くか = 日次フローの公表は総額だけで、中身の分け方が公表されないため。何で崩れるか = ベーシス取引の持ち高が小さくなり、流出の大半が売り切りになるとき。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = ベーシス取引のヘッジファンド(ETF 売り + CME 先物の買い戻し)と、ETF の売り切りの保有者。場面 = 流出の日。
- 反証: 流出の日をベーシスの縮みで 2 つに分けた後の BTCUSD の動きが、2 つの組で区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 「30-day annualized basis fell from 6.63% to 4.46%」(訳: 30 日の年率ベーシスが 6.63% から 4.46% に下がった)、「roughly 5% annualized as a floor」(年率およそ 5% が下限)は出所の記述【照合未了】。閾値は未定(W4 で測る前に決める)。
- 使うデータと遅れ: ETF の日次フロー(区分 A、翌営業日)、CME のビットコイン先物の価格と現物の価格から作る年率ベーシス(CME の先物の履歴の取得の経路は未確認)。
- 約定の模型: 成行。

#### X2-B-05(升 P6-移動)米国の立会中の Coinbase の上乗せ(Coinbase と Binance の価格差)で、翌営業日に公表される ETF のフローを先読みする

- 原文【照合未了】: 「If the premium turns and holds positive...it is often the earliest visible sign that US structural demand is re-engaging before ETF flow data confirms it days later.」
  - 訳: 「上乗せが正に転じてそれが続くなら、…それは多くの場合、米国の構造的な需要が戻ってきたことの最初に見える印で、ETF のフローのデータが数日後にそれを裏付ける」
  - 出所: https://www.buildix.trade/blog/coinbase-premium-index-us-demand-gauge-explained (buildix、2026-07-09)
  - 補い(検索結果の要約の文。ページ未確認): 「analysts monitoring the premium in real time had an intraday signal of accelerating US institutional buying several hours before daily ETF flow reports were published」「a premium that builds through the US afternoon and holds into close is a stronger signal than one that spikes at open and fades」(訳: 「上乗せを即時に見ていた分析者は、日次の ETF のフローの報告が公表される数時間前に、米国の機関の買いの加速の日中の信号を得た」「米国の午後に積み上がって引けまで保たれる上乗せは、寄り付きに跳ねて消える上乗せより強い信号である」)。経路: WebSearch の結果。出所の候補は bit.com・kucoin・buildix のどれかで、どのページの文かは確かめていない。buildix のページを開いたところ、この 2 文は無いと返った。
- 意図の地図: 入る条件 = 米国の立会中(出所の「9am–5pm ET」は検索結果の要約の文)の上乗せの水準と形(午後に積み上がり引けまで保つか)。向き = 上乗せが正で保たれれば買い(出所の主張)。出る条件 = 翌営業日のフローの公表(未定)。強弱の付け方 = 上乗せの大きさと継続の時間(未定)。
- なぜ: 誰が損をしているか = 日次フローの公表を待って動く参加者(round1 の D1-B-5 の追随する注文の主)。なぜ続くか = AP は設定のための BTC を Coinbase で買うことが多い(P6-約定 の検索の要約に「Coinbase serves as the sole Bitcoin Trading Party for IBIT」= 「Coinbase は IBIT の唯一の Bitcoin の取引の相手」とある。ページ未確認)ため、フローは公表より先に Coinbase の価格に出る。何で崩れるか = AP が OTC や他の取引所で買うようになったとき、現物での設定・償還(round1 の D1-B-6 の欄の 2025-09 の承認)で AP が市場で買わなくなったとき。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = AP(設定のための現物の買い)と、フローの公表に追随する参加者。場面 = 米国の立会の終わりから翌営業日の公表まで。日本時間では早朝〜翌日の公表まで。
- 反証: 立会中の上乗せで分けた翌営業日の公表フローの符号が、分けない場合と区別できない、または上乗せで分けた後の BTCUSD の動きが区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 未定(W4 で測る前に決める)。
- 使うデータと遅れ: Coinbase の BTC-USD と Binance の BTCUSDT の分足の価格(round1 の到達確認の区分は prep1 の DATA_REACH.md を見ていないので未確認)、ETF の日次フロー(区分 A、翌営業日)。USDT と USD の差を分ける要があるかは未確認。
- 約定の模型: 成行。

#### X2-B-06(升 P6-約定)基準価額を決める 16:00 ET の参照価格の構成取引所と、構成外の取引所の価格差を、AP の設定・償還の注文の先回りとして使う

- 原文【照合未了】: 「Traders can simply choose the least liquid exchange on the CF Benchmarks index and compare the price of Bitcoin on the platform against the price of Bitcoin on Binance.」「If it trades higher, they'll need to create more shares, adding supply to the market and lowering the price.」(取得結果では、トレーダーは CF Benchmarks の取引所の価格を追って「frontrun the funds creating or redeeming ETF shares」= 「ETF 株を設定・償還するファンドに先回りする」ことができる、とも返った)
  - 訳: 「トレーダーは、CF Benchmarks の指数のうち流動性の最も低い取引所を選び、そこの Bitcoin の価格を Binance の価格と比べればよい」「(ETF 株が)高く取引されれば、(AP は)株を新たに設定する要があり、市場に供給を足して価格を下げる」
  - 出所: https://www.dlnews.com/articles/snapshot/how-pro-crypto-traders-can-arb-bitcoin-etfs (DL News、2024-01-17)
  - 補い【照合未了】: 「volumes since the launch have become more concentrated in US hours with noticeable volume spikes around when equity markets open (14H UTC) and close (20H UTC).」「Bitcoin ETFs, which calculate their net asset value (NAV) against dedicated benchmarks at the US close each weekday, encouraging arbitrage and price discovery.」(訳: 「(ETF の)開始以来、出来高は米国の時間帯に集まるようになり、株式市場の寄り付き(14 時 UTC)と引け(20 時 UTC)の付近に目立つ出来高の山がある」「Bitcoin ETF は平日の米国の引けに専用の参照価格で基準価額を計算し、それが裁定と価格の発見を促す」)。出所: https://thefullfx.com/etf-flows-shift-cryptos-trading-patterns/ (The Full FX、2024-06-06)
  - 補い(ページ未確認): NYDIG「blackrocks consistent premiums」https://www.nydig.com/research/blackrocks-consistent-premiums は 404。検索結果の要約に「BlackRock's iShares Bitcoin Trust (IBIT) shows a consistent price premium to its net asset value of around 20 basis points (0.2%)」(訳: IBIT は基準価額に対しておよそ 0.2% の一貫した上乗せを示す)とあった。
- 意図の地図: 入る条件 = 16:00 ET(夏時間 20:00 UTC、冬時間 21:00 UTC)の前の時間帯に、構成取引所(出所: Coinbase・Kraken・Gemini・itBit・LMAX Digital・Bitstamp)の価格と構成外(出所: Binance)の価格の差が開いた時点。向き = 出所の記述は、差が開いた側から AP の注文で差が閉じる向き。出る条件 = 16:00 ET の参照価格の窓の終わり(未定)。強弱の付け方 = 差の大きさ(未定)。
- なぜ: 誰が損をしているか = 基準価額の決定の時刻に、構成取引所で大口の売買をしなければならない AP・発行体(出所の主張)。なぜ続くか = 参照価格の構成取引所と時刻が規約で決まっているため。何で崩れるか = 現物での設定・償還(2025-09 の承認、round1 の D1-B-6 の欄)で AP が市場で売買しなくなったとき、または参照価格の窓が長くなったとき。
- 期待する向きと場面: 効く項 = BTCUSD(構成取引所の価格)と、構成外の取引所との差。bitFlyer はどちらにも入らないので、bitFlyer の価格には BTCUSD の項として届く。場面 = 平日の 16:00 ET の前。日本時間では 05:00(夏時間)または 06:00(冬時間)の前。
- 反証: 16:00 ET の前の構成取引所と構成外の取引所の差が、他の時刻の差と区別できないと測れたら、「AP の注文が参照価格の時刻に集まる」という「なぜ」は違う。
- 段 3 の種類: (a)。
- 水準とその出所: 16:00 ET、構成取引所 6 つ(出所の記述)。IBIT の上乗せおよそ 0.2%(出所の主張、ページ未確認)。差の閾値は未定。
- 使うデータと遅れ: Coinbase・Kraken・Bitstamp などと Binance の分足の価格(区分 未確認)。CF Benchmarks の参照価格の時刻と窓の定義(未確認。規約は CF Benchmarks の文書で確かめる)。
- 約定の模型: 成行。

#### X2-B-07(升 P6-約定)米国の寄り付きの後の最初の 1 時間(9:30〜10:30 ET)を、下げの出やすい窓として場面にする(出所の主張とその反論の両方を付ける)

- 原文【照合未了】: 「a sharp decline around 10 AM ET」「use its privileged position as authorized participant to suppress the spot price, trigger liquidations, and harvest the spread」「buying Bitcoin on the spot market and selling futures...is what any other delta neutral fund does」「no regulator, exchange, or independent data source had confirmed any coordinated activity」
  - 訳: 「米東部時間 10 時ごろの急な下げ」「AP としての特別な立場を使って現物の価格を押し下げ、清算を起こさせ、差を刈り取る」(説を唱える側の文)「現物で Bitcoin を買い先物を売ることは、ほかのどのデルタ中立のファンドもしていることだ」(CryptoQuant の反論)「規制当局・取引所・独立のデータの出所のどれも、組織的な売買を裏付けていない」
  - 出所: https://finance.yahoo.com/news/10-am-bitcoin-dump-theory-093614446.html (Yahoo Finance、2026-02-26)
  - 補い(検索結果の要約の文。ページ未確認): 「since early November, Bitcoin has declined during the first hour of U.S. trading in more than 60% of sessions, typically shedding up to 3% in that window」(訳: 「11 月初めから、米国の取引の最初の 1 時間に Bitcoin が下げた日が 60% を超え、その窓で最大 3% ほど下げることが多い」)と、反論「Bitcoin recording cumulative returns of 0.9% in the 10 a.m. to 10:30 a.m. window since Jan. 1」(訳: 「1 月 1 日以降、10:00〜10:30 の窓の累積の騰落は +0.9%」、Alex Krüger)。経路: WebSearch の結果(cointelegraph https://regional-front.cointelegraph.com/news/bitcoin-10am-dump-theory-jane-street-ibit-13f-terraform-lawsuit ほか)。benzinga https://benzinga.com/crypto/cryptocurrency/25/12/49281097/why-does-bitcoin-keep-dumping-as-soon-as-the-us-trading-session-starts は 403、mexc https://www.mexc.com/news/560527 は 410。
- 意図の地図: 入る条件 = 米国の株式の寄り付き(9:30 ET)の前の夜間に BTCUSD が上げていた日の、寄り付きの時点。向き = 出所の主張は下げ。反論があり、向きは未定として扱う。出る条件 = 寄り付きから 1 時間(出所の窓)。強弱の付け方 = 夜間の上げの大きさ(未定)。
- なぜ: 誰が損をしているか = 夜間の上げを追って買った参加者(出所の主張では、寄り付きの売りで清算される)。なぜ続くか = 米国の立会で ETF 株と現物・先物の裁定が始まり、夜間に ETF の外で付いた価格に、ETF の側の売買が寄り付きで一度に当たるため【推定】。何で崩れるか = 出所の反論のとおり、窓の騰落が偏っていないとき、または ETF の夜間の取引(decrypt の「AfterDark ETF」の記事が検索結果に出た。ページ未確認)が広がって寄り付きの集中が無くなるとき。
- 期待する向きと場面: 効く項 = BTCUSD。場面 = 平日の 9:30〜10:30 ET(日本時間 22:30〜23:30 夏時間、23:30〜00:30 冬時間)。
- 反証: 寄り付きの後の 1 時間の BTCUSD の騰落が、他の 1 時間の窓と区別できないと測れたら違う(出所の反論はこの形をとっている)。
- 段 3 の種類: (a)。
- 水準とその出所: 9:30〜10:30 ET、60% 超・最大 3%(出所の主張、ページ未確認)。反論側の +0.9%(出所の主張)。
- 使うデータと遅れ: BTCUSD の分足(区分 未確認)、米国の株式市場の暦(区分 A)。
- 約定の模型: 成行。

#### X2-B-08(升 P6-持ち高)13F の届け出から見た ETF の保有者の構成(ヘッジファンドの割合)を、巻き戻しうるベーシス取引の持ち高の大きさとして場面にする

- 原文【照合未了】: 「Institutional investors filing 13F forms reduced their positions in US spot Bitcoin ETFs by 17%.」「The total assets under management by professional participants decreased from 313,000 BTC to 261,000 BTC.」「Hedge funds reduced their positions by 31,400 BTC (−39%).」
  - 訳: 「13F を届け出る機関投資家は、米国の現物 Bitcoin ETF の持ち高を 17% 減らした」「専門の参加者の運用資産は 313,000 BTC から 261,000 BTC に減った」「ヘッジファンドは持ち高を 31,400 BTC(−39%)減らした」
  - 出所: https://forklog.com/en/institutional-investors-offload-52500-btc-via-etfs/amp/ (ForkLog、2026-06-05。CoinShares の 2026 年 1〜3 月期の報告の引用)
  - 補い【照合未了】: 「The recent selling may partially result from some hedge funds unwinding their basis trades that involved bitcoin ETFs and bitcoin futures.」(訳: 「最近の売りの一部は、Bitcoin ETF と Bitcoin 先物を使ったベーシス取引を、ヘッジファンドが巻き戻したことによるかもしれない」)。出所: https://www.itiger.com/hans/news/2516552964 (MarketWatch の Frances Yue の記事、2025-03-01)
- 意図の地図: 入る条件 = 四半期ごとの 13F の集計で、ETF の保有のうちヘッジファンドの割合が大きい(または増えた)期間。向き = 未定(割合が大きい期間は、ベーシスの縮み(X2-B-11)で巻き戻される持ち高が大きい、という場面の変数で、向きそのものではない)。出る条件 = 次の四半期の集計まで(未定)。強弱の付け方 = ヘッジファンドの割合(未定)。
- なぜ: 誰が損をしているか = ベーシスの縮みが起きたときに、巻き戻しの売りの大きさを読み違える参加者。なぜ続くか = 保有者の構成は四半期ごと・期末から遅れてしか公表されないため。何で崩れるか = 13F の対象外の保有者(出所の要約の文では、個人が保有の 74%)が大半で、ヘッジファンドの割合が場面を分けるほど動かないとき。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = ベーシス取引のヘッジファンド。場面 = 四半期ごと(13F の届け出は期末から 45 日以内【13F の期限は一般の知識で、この周に出所を開いていない。未確認】)。
- 反証: ヘッジファンドの割合で分けた期間の、ベーシスの縮みの日の ETF の流出と BTCUSD の動きが、割合で区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 出所の数(313,000 → 261,000 BTC、−17%、−39%)はその四半期の観測で、閾値ではない。閾値は未定。
- 使うデータと遅れ: SEC の 13F の届け出(EDGAR。取得の経路・区分は未確認)、または CoinShares などの集計(未確認)。公表は四半期末から遅れる(未確認)。
- 約定の模型: 成行。

#### X2-B-09(升 P6-持ち高)ETF の保有者・カバードコールの ETF が IBIT の上で売るコールの量を、米国の立会中のディーラーのロングガンマ(値動きの吸収)の大きさとして場面にする

- 原文【照合未了】: 「It also sells call options on roughly 25%-35% of its IBIT holdings to generate income, which is distributed to investors.」
  - 訳: 「(BITA は)収益を得るために IBIT の保有のおよそ 25〜35% にコールを売り、その収益を投資家に配る」
  - 出所: https://www.theblock.co/post/404825/ (The Block。BlackRock の iShares Bitcoin Premium Income ETF(BITA)の開始、取得結果では 2026-06-16)
  - 補い(検索結果の要約の文。ページ未確認): YieldMax の YBIT は「writes call options on IBIT, typically on a weekly basis with expirations of one month or less」(訳: 「IBIT のコールを、通常は週ごとに、満期 1 か月以内で売る」)。経路: WebSearch の結果(https://www.yieldmaxetfs.com/ybit/summary-prospectus ほか)。
  - 補い【照合未了】: 「IBIT is not a smaller copy of the CME bitcoin book. It is structurally long dealer gamma because it is structurally overwritten」(訳: 「IBIT は CME の Bitcoin の帳簿の小さな写しではない。構造的にコールを上から売られているので、構造的にディーラーのロングガンマである」)。出所: https://flashalpha.com/articles/ibit-options-gamma-exposure-bitcoin-etf-dealer-positioning (FlashAlpha、2026-08-17、2026-09-13 更新)
- 意図の地図: 入る条件 = カバードコールの ETF の運用資産と、そのコールの売りの比率から出す「売られたコールの量」が大きい期間。向き = 向きではなく値動きの大きさの場面(ディーラーがロングガンマなら上げで売り下げで買うので、米国の立会中の値動きが吸収される、という出所の機構)。出る条件 = 未定。強弱の付け方 = 売られたコールの量(未定)。
- なぜ: 誰が損をしているか = 米国の立会中に値動きが伸びると見て順張りする参加者。なぜ続くか = カバードコールの ETF は規約でコールを売り続けるため(出所の BITA の 25〜35%)。何で崩れるか = カバードコールの ETF の資産が小さく、IBIT のオプション全体の建玉に対して売りの量が小さいとき。ディーラーが IBIT 株でヘッジし、現物・先物に注文が届かないとき(出所 FlashAlpha の「the IBIT book is hedged in ETF shares against overwriting flow」= 「IBIT の帳簿は、上から売られる流れに対して ETF 株でヘッジされる」)。
- 期待する向きと場面: 効く項 = BTCUSD(米国の立会中の値動きの大きさ)。場面 = 米国の立会中。
- 反証: 売られたコールの量の大小で分けた期間の、米国の立会中の BTCUSD の値動きの大きさが区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 25〜35%(BITA の規約、出所の記述)。それ以外は未定。
- 使うデータと遅れ: カバードコールの ETF の運用資産と保有の開示(発行体の日次の開示。区分 未確認)、IBIT のオプションの建玉(未確認)。
- 約定の模型: 成行。

#### X2-B-10(升 P6-強制)先物で運用するレバレッジ型 ETF(BITX)の日次の倍率の戻しと、期近から期先への毎日の乗り換えを、引けの前の CME 先物の注文として使う

- 原文【照合未了】: 「BITX buys or sells Bitcoin futures to reset its exposure back to 2x every day」
  - 訳: 「BITX は Bitcoin の先物を売買して、持ち高を毎日 2 倍に戻す」
  - 出所: https://www.volatilityshares.com/resource/How-BITX-Works-Beyond-the-Basics/ (Volatility Shares、2023-11-14)
  - 補い(検索結果の要約の文。上のページには無いと返った。ページ未確認): 「BITX generally rolls Bitcoin futures daily from the sooner-to-expire month one futures contract to the longer-to-expire month two futures contract. In addition to rolling futures forward, BITX also adjusts its holdings each day to maintain its daily 2x exposure, as well as adding or subtracting new futures to account for any new investments or redemptions from the fund.」(訳: 「BITX は通常、満期の近い第 1 限月から満期の遠い第 2 限月へ、Bitcoin の先物を毎日乗り換える。乗り換えに加えて、毎日 2 倍の持ち高を保つために保有を調整し、新しい投資や償還の分の先物も足し引きする」)。経路: WebSearch の結果(volatilityshares の PDF https://volatilityshares.com/ckfinder/userfiles/files/How%20BITX%20Works%2007182024.pdf ほか)。
- 意図の地図: 入る条件 = その日の BTCUSD の騰落が大きい日の、BITX の日次の調整の時刻の前(時刻は出所で確かめていない。未定)。向き = 上げた日は買い、下げた日は売り(2 倍を保つための調整の一般の算術。出所はこの向きを書いていない【推定】)。出る条件 = 調整の時刻の後(未定)。強弱の付け方 = 運用資産 × その日の騰落(未定)。
- なぜ: 誰が損をしているか = 引けの前の調整の注文の反対側に立つ参加者。なぜ続くか = 規約で毎日 2 倍に戻すため(出所の記述)。何で崩れるか = BITX の運用資産が CME の先物の出来高に対して小さいとき、または調整を 1 日の中で分散して行うとき。
- 期待する向きと場面: 効く項 = BTCUSD(CME の先物を通して)。場面 = 平日の CME の引けの前(時刻は未確認)。
- 反証: 騰落の大きい日の CME の引けの前の BTCUSD の動きが、騰落の小さい日と区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 2 倍、第 1 限月 → 第 2 限月(出所の記述)。調整の時刻は未定。
- 使うデータと遅れ: BITX の運用資産(発行体の日次の開示。区分 未確認)、BTCUSD の分足(区分 未確認)、CME の先物の暦(区分 A)。
- 約定の模型: 成行。
- round1 との違い: D1-B-39 は銘柄と規約を確かめていない仮定から導いた案。本案は出所で、先物で行うこと、乗り換え(期の間の売買)が毎日あることを足した。

#### X2-B-11(升 P6-強制)CME のベーシスが採算の下限を割ったときの、ベーシス取引の機械的な巻き戻し(ETF 売り + 先物の買い戻し)とその輪を場面にする

- 原文: 
  - 【照合未了】「Profitability requires the basis spread to exceed cost of capital plus execution costs—roughly 5% annualized as a floor.」(訳: 「採算には、ベーシスが資本の費用と執行の費用の合計を上回る要がある — 年率およそ 5% が下限」)。出所: https://blog.amberdata.io/the-etf-exodus-decoded-basis-arbitrage-not-capitulation (Amberdata、2025-12-03)
  - (検索結果の要約の文。ページ未確認)「If Bitcoin's price drops, the futures premium can also shrink, creating a problem for hedge funds which begin to unwind their trades by selling Bitcoin ETF shares and buying back short CME futures; when this happens at scale, the coordinated unwind means major selling of spot ETFs and upward pressure on futures, exacerbating Bitcoin's price declines and potentially causing a feedback loop.」(訳: 「Bitcoin の価格が下がると先物の上乗せも縮みうる。これはヘッジファンドにとって問題になり、ヘッジファンドは Bitcoin ETF 株を売り、CME 先物の売りを買い戻して取引を巻き戻し始める。これが大きな規模で起きると、現物 ETF の大きな売りと先物への上向きの圧力になり、Bitcoin の値下がりを悪化させ、輪(フィードバック)を生みうる」)。経路: WebSearch の結果(dlnews https://dlnews.com/articles/markets/bitcoin-price-slumps-as-arbitrage-strategies-falter ほか。どのページの文かは確かめていない)。
- 意図の地図: 入る条件 = CME の年率ベーシスが下限(出所の例 年率およそ 5%)を下に割った時点。向き = 出所の主張は下げの輪。出る条件 = 未定(ベーシスが下限の上に戻ったときなど)。保有中の判断 = 未定。強弱の付け方 = 下限からの割り込みの幅と、ETF の保有のうちヘッジファンドの割合(X2-B-08)。
- なぜ: 誰が損をしているか = 輪の途中で下げに逆らって買う参加者。なぜ続くか = ベーシス取引は採算の下限で機械的に閉じられ、閉じる売りがさらにベーシスを縮めるため(出所の主張)。何で崩れるか = ベーシス取引の持ち高が小さいとき、または巻き戻しが現物で一度に出ず、AP の現物での償還で市場を通らないとき。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = ベーシス取引のヘッジファンド。場面 = ベーシスが下限を割った期間。
- 反証: ベーシスが下限を割った期間の BTCUSD の動きが、割っていない期間と区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 年率およそ 5%(出所の主張)。それ以外は未定。
- 使うデータと遅れ: CME のビットコイン先物の価格と現物の価格(取得の経路は未確認)。ETF の日次フロー(区分 A、翌営業日)。
- 約定の模型: 成行。

#### X2-B-12(升 P7-関心)25 デルタのリスクリバーサルの、2 つの場所(IBIT・Deribit)での百分位の高さと、符号の反転を場面にする

- 原文【照合未了】: 「The current risk reversal at the 25 delta reading is at the 82nd percentile of IBIT's history and the 84th percentile of Deribit's five-year history, meaning both venues are at elevated defensive positioning levels.」(取得結果では、IBIT は 24 時間取引でない構造のため歴史的に Deribit より守り寄りで、今の 2 つの場所の差がゼロに近いのは「rare alignment」= 「まれな揃い」とも返った)
  - 訳: 「今の 25 デルタのリスクリバーサルは、IBIT の履歴の 82 百分位、Deribit の 5 年の履歴の 84 百分位にあり、両方の場所が高い守りの構えにあることを意味する」
  - 出所: https://www.anchorage.com/research/the-anchorage-digital-prime-signal-what-skew-wings-and-the-term-structure-are-telling-us-about-bitcoin-and-its-adjacent-markets (Anchorage Digital、2026-06-25)
  - 補い(検索結果の要約の文。ページ未確認だが同じ出所の検索結果): 「when IBIT launched during the post-election Bitcoin rally, both venues were in deep call skew ... By early 2025 both markets had flipped to put skew」(訳: 「大統領選の後の上昇の中で IBIT(のオプション)が始まったとき、両方の場所は深いコール寄りの歪みにあった … 2025 年の初めまでに両方の市場はプット寄りの歪みに反転した」)
- 意図の地図: 入る条件 = (a) 両方の場所のリスクリバーサルが自分の履歴の高い百分位にそろった時点、または (b) 両方の場所の符号がそろって反転した時点。向き = 未定(出所は「守りの構え」と状態を述べ、売買の向きを書いていない)。出る条件 = 未定。強弱の付け方 = 百分位(未定)。
- なぜ: 誰が損をしているか = 下落への備えにお金を払う参加者と、その反対側(備えを売るディーラー)のどちらかが、実際の値動きに対して払い過ぎ・受け取り過ぎている。どちらかは未定。なぜ続くか = 2 種類の参加者(伝統的な金融の側と暗号資産の側)が同じ向きに構えると、反対側に立つ参加者が少なくなるため【推定】。何で崩れるか = 歪みが値動きの後追いで、その後の動きに何も足さないとき。
- 期待する向きと場面: 効く項 = BTCUSD。場面 = 両方の場所の構えがそろった期間(X2-B-01 の差が小さい期間に当たる)。
- 反証: 百分位の高さ・符号の反転で分けた後の BTCUSD の動きが、分けない場合と区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 82・84 百分位はその時点の観測で、閾値ではない。閾値は未定。
- 使うデータと遅れ: Deribit のオプションの値付け(round1 の区分 A)、IBIT のオプションの歪み(Glassnode。区分・料金は未確認)。
- 約定の模型: 成行。

#### X2-B-13(升 P7-予告)オプションの金庫(DOV など)が毎週金曜の決まった時刻にオプションを競りで売ることが予め分かっていることを、金曜の予想ボラの下げと、ディーラーのロングガンマの増加の予告として使う

- 原文【照合未了】: 「professional market makers, on the other side, outbid each other to buy these options through an auction process that runs on fixed schedules every week, typically on Fridays.」「implied volatility consistently sells off before the auctions. In the end, the DOVs sell options at the worst levels.」「On average, the implied volatility around the auctions time on Fridays is 4 vols below the prior 24 hours.」
  - 訳: 「反対側では、専門のマーケットメイカーが、毎週決まった予定(通常は金曜)で行われる競りで、これらのオプションを買うために競り合う」「予想ボラは競りの前に決まって売られる。結局、DOV は最悪の水準でオプションを売ることになる」「平均すると、金曜の競りの時刻の付近の予想ボラは、その前の 24 時間より 4 ボラ低い」
  - 出所: https://paradigm.co/blog/paradigm-defi-options-vaults (Paradigm、2022-09-22)
  - 補い【照合未了】: 「Market-makers buying the options, on the other hand, say they need to position themselves for these flows, which some say are responsible for roughly a quarter of the entire supply of crypto options volatility.」「Implied volatilities on weekly ETH options around the time of the auction are typically about four vols below the previous 24 hours.」(訳: 「オプションを買うマーケットメイカーは、これらの流れに備えて構える要があると言う。この流れは、暗号資産のオプションのボラの供給全体のおよそ 4 分の 1 にあたると言う人もいる」「競りの時刻の付近の ETH の週物のオプションの予想ボラは、通常その前の 24 時間より 4 ボラほど低い」)。出所: https://fx-markets.com/our-take/7948387/crypto-structured-products-come-of-age (FX Markets / Risk.net、2022-11-08)
  - 補い【照合未了】: 「Every Friday at 11pm UTC, Ribbon will take the vaults deposits from the previous week and deposit those as collateral into Opyn to mint oTokens.」(訳: 「毎週金曜 23:00 UTC に、Ribbon は前の週の金庫の預かりを担保として Opyn に入れ、oToken(チェーン上のオプション)を作る」)。出所: https://themothership.substack.com/p/vaultification-of-defi-crypto-structured (2022-03-31)
  - 補い(検索結果の要約の文。ページ未確認): 「sometime between 2:00 AM and 11:00 AM UTC on Friday, most vaults will offload their positions」「DeFi option vaults sell large amounts of low delta one week covered calls and cash-secured puts every Friday around 8am UTC」(訳: 「金曜の 2:00〜11:00 UTC のどこかで、ほとんどの金庫が持ち高を売り出す」「DeFi のオプションの金庫は、毎週金曜 8:00 UTC ごろに、デルタの低い 1 週のカバードコールと現金担保のプットを大量に売る」)。経路: WebSearch の結果(Paradigm の 2 本の記事・amberdata の週報のどれかの文。ページで確かめていない)。
- 意図の地図: 入る条件 = 金曜の競りの時刻(出所: 2:00〜11:00 UTC のどこか、8:00 UTC ごろ。確かめていない)の前後。向き = 価格の向きではなく、値動きの大きさの場面(ディーラーが競りで低デルタのオプションを買うとロングガンマが増え、値動きを吸収する向き【推定】)。出る条件 = 未定(次の満期まで、など)。強弱の付け方 = その週の金庫の売りの量(未定)。
- なぜ: 誰が損をしているか = 決まった時刻にオプションを売る金庫(出所の主張「最悪の水準で売る」)。なぜ続くか = 金庫の規約が毎週の決まった予定で売ることを決めているため。何で崩れるか = 金庫の資産が小さくなったとき(出所の Ribbon の資産は記事の時点で頂点から減っていた)、または競りの時刻がばらけたとき。
- 期待する向きと場面: 効く項 = BTCUSD(値動きの大きさ)、経費(値動きが小さい場面では指値の待ちの損益が変わる【推定】)。場面 = 金曜の競りの前後から翌週の満期まで。日本時間では金曜の 11:00〜20:00 のどこか。
- 反証: 金曜の競りの後の BTCUSD の実現の値動きの大きさが、他の曜日の同じ時刻の後と区別できないと測れたら、「競りでディーラーのガンマが増えて値動きを吸収する」という「なぜ」は違う。
- 段 3 の種類: (a)。
- 水準とその出所: 4 ボラ(出所の主張)、ボラの供給の 4 分の 1(出所の「some say」= 一部の人の主張)。競りの時刻は未定(出所の間で書き方が違う)。
- 使うデータと遅れ: 暦(区分 A)、Deribit のオプションの値付け(区分 A)、金庫の資産と競りの結果(チェーン上の記録・各金庫の公表。区分 未確認)。
- 約定の模型: 成行。

#### X2-B-14(升 P7-約定)Deribit のオプションの買い・売りの注文の偏り(正味の買い圧力)を、価格の向きではなく、次の時間の値動きの大きさの場面にする

- 原文【照合済み: PDF から写した】: 「at-the-money option prices are largely driven by volatility traders and out-of-the-money options are simultaneously driven by volatility traders and those with proprietary information about the direction of future bitcoin price movements.」「we show that order imbalance is motivated more by volatility information than information about the direction of the underlying price, i.e about the sign and size of the return. And in supporting of later results, order imbalance does have predictive power for implied and realised volatilities.」
  - 訳: 「アットザマネーのオプションの価格は主にボラのトレーダーが動かし、アウトオブザマネーのオプションは、ボラのトレーダーと、将来の Bitcoin の価格の向きについて独自の情報を持つ者の両方が同時に動かす」「注文の偏りは、原資産の価格の向き(騰落の符号と大きさ)の情報よりも、ボラの情報によって動機づけられていることを示す。そして後の結果を支えるものとして、注文の偏りは予想ボラと実現ボラを予測する力を持つ」
  - 出所: https://arxiv.org/abs/2109.02776 (Carol Alexander・Jun Deng・Jianfen Feng・Huning Wan「Net Buying Pressure and the Information in Bitcoin Option Trades」、第 2 版 2022-03-25)。PDF https://arxiv.org/pdf/2109.02776 を保存して `pdftotext` で文字にした。
- 意図の地図: 入る条件 = 1 時間(出所の区切りは毎時・日次・5 日)の Deribit のオプションの買い手主導と売り手主導の約定の差(正味の買い圧力)が大きい時点。向き = 価格の向きではなく、次の区切りの実現ボラが大きい場面とみる(出所の主張)。アウトオブザマネーの側は向きの情報も含む(出所の主張)が、向きの規則は未定。出る条件 = 次の区切りの終わり(未定)。強弱の付け方 = 正味の買い圧力の大きさ、行使価格の帯(アット・アウト)で分ける(未定)。
- なぜ: 誰が損をしているか = オプションの約定の偏りを見ずに、値動きの大きさを前の値動きから読む参加者。なぜ続くか = ボラの情報を持つトレーダーはオプションで売買し、その跡は約定の偏りに先に出るため(出所の主張)。何で崩れるか = 出所の主張のとおり、Deribit が効率的になり(「rapidly evolving into a more efficient channel」= 「急速に、より効率のよい経路になっている」)、偏りが値付けに即座に吸収されるとき。
- 期待する向きと場面: 効く項 = BTCUSD(値動きの大きさ)、経費(値動きの大きい場面では板の厚みと約定の滑りが変わる【推定】)。場面 = 正味の買い圧力が大きい区切りの次の区切り。
- 反証: 正味の買い圧力で分けた次の 1 時間の BTCUSD の実現の値動きが、分けない場合と区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 区切り 毎時・日次・5 日(出所の記述)。閾値は未定。
- 使うデータと遅れ: Deribit のオプションの約定(round1 の区分 A。約定ごとに買い手・売り手のどちらが仕掛けたかの印が要る。印が API の約定の列にあるかは未確認)。
- 約定の模型: 成行。
- round1 との違い: D1-B-11・X1-B-5 は約定の偏りを価格の向きに使う案。本案は出所の主張に従って値動きの大きさに使う。

#### X2-B-15(升 P7-約定)テイカーが払った・受け取ったプレミアムの額を行使価格ごとに集め、価格の「磁石」の水準と、コール買いとプット買いの資金の比(強気・弱気の指数)を作る

- 原文【照合未了】: 「By definition, a taker is willing to pay the spread to execute immediately instead of waiting for price improvement, which signals urgency.」「By examining the distribution of net premium, you can identify key price levels that could act as magnets or zones of heightened risk.」「Options Bull–Bear Index (BBI) measures whether traders allocate more capital to call (bullish) or put (bearish) buying」
  - 訳: 「定義から、テイカーは価格の改善を待たずにすぐ約定させるために差を払う意思があり、それは急ぎを示す」「正味のプレミアムの分布を調べると、磁石として働く価格の水準や、リスクが高まる帯を見つけられる」「オプションの強気・弱気の指数(BBI)は、トレーダーがコールの買い(強気)とプットの買い(弱気)のどちらに多くの資金を回しているかを測る」(取得結果では BBI は +1 から −1 の範囲、満期で分けて短期と長期の構えを分けるとも返った)
  - 出所: https://research.glassnode.com/options-premiums-metrics/ (Glassnode、2025-10-02)
- 意図の地図: 入る条件 = (a) 現値が、正味のプレミアムの大きい行使価格(磁石)に近づいた時点、または (b) BBI の符号が変わった時点。向き = (a) は磁石の水準へ向かう(出所の「magnets」の語からの読み。向きの規則は出所に無い)、(b) は未定。出る条件 = 未定。強弱の付け方 = 正味のプレミアムの額、BBI の値(未定)。
- なぜ: 誰が損をしているか = 急ぎで差を払ったテイカーの反対側に立ち、ヘッジするディーラーの注文を読まない参加者。なぜ続くか = テイカーの売買はディーラーのヘッジを通して現物・先物に届くため【推定】。何で崩れるか = テイカーの売買がヘッジ済みの組み合わせ(スプレッド)で、ディーラーのヘッジが要らないとき。
- 期待する向きと場面: 効く項 = BTCUSD。場面 = 正味のプレミアムの偏りが大きい行使価格の付近。
- 反証: 正味のプレミアムの大きい行使価格の付近での BTCUSD の動きが、他の価格の付近と区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: BBI の範囲 +1〜−1(出所の記述)。閾値は未定。
- 使うデータと遅れ: Deribit のオプションの約定(round1 の区分 A。テイカーの向きの印が要る。API の列は未確認)。Glassnode の集計(料金・区分は未確認)。
- 約定の模型: 成行。
- round1 との違い: X1-B-5 は名目 25 万ドル超のブロックだけを 90 分の窓で集める。本案はブロックで絞らず、テイカーのプレミアムを行使価格ごとに集める。

#### X2-B-16(升 P7-持ち高)ディーラーの charm(時間の経過によるデルタの変化)と vanna(予想ボラの変化によるデルタの変化)から出るヘッジの売買を、日の終わり・週の終わりの場面にする

- 原文【照合未了】: 「CHEX shows how time decay alters dealer delta, creating predictable end-of-day and end-of-week flows.」「VEX captures how dealer delta shifts when volatility changes - a large VEX means volatility moves trigger significant hedging flows.」
  - 訳: 「CHEX(charm の露出)は、時間の経過がディーラーのデルタをどう変えるかを示し、日の終わりと週の終わりに予測できる流れを生む」「VEX(vanna の露出)は、ボラが変わったときにディーラーのデルタがどう動くかを捉える。VEX が大きいと、ボラの動きが大きなヘッジの流れを起こす」
  - 出所: https://flashalpha.com/futures/btc (FlashAlpha の BTC 先物のオプションの分析のページ。日付は取得結果に無い)
- 意図の地図: 入る条件 = (a) charm から出る、日の終わり・週の終わりのディーラーのデルタの変化の向きと大きさを、建玉から計算した時点。(b) 予想ボラ(DVOL など)が大きく動いた時点で、vanna から出るデルタの変化を計算した時点。向き = 計算されたディーラーのヘッジの売買の向き(買い・売り)に沿う(出所の機構からの読み)。出る条件 = 日の終わり・週の終わりの後(未定)。強弱の付け方 = 計算された流れの大きさ(未定)。
- なぜ: 誰が損をしているか = 価格が動かなくても時間とボラでヘッジの注文が出ることを見ない参加者。なぜ続くか = ディーラーはデルタを中立に保つ規律で動くため。何で崩れるか = ディーラーの持ち高の符号(買い持ちか売り持ちか)を建玉から正しく推せないとき(誰がディーラーかは建玉の公表に無い。round1 の X1-B-6 の欄では Glassnode はテイカーの流れから組み立てると書いた)。
- 期待する向きと場面: 効く項 = BTCUSD。場面 = Deribit の日次の満期(08:00 UTC)の前と、週末(金曜の満期)の前。日本時間では 17:00 の前。
- 反証: 計算された charm・vanna の流れの向きで分けた、日の終わり・週の終わりの前の BTCUSD の動きが区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 未定(W4 で測る前に決める)。
- 使うデータと遅れ: Deribit の行使価格・満期ごとの建玉(round1 の区分 C、今の値だけ)。履歴が要るので、建玉の履歴の取得の経路は未確認。
- 約定の模型: 成行。
- round1 との違い: D1-B-12・D1-B-13・X1-B-6 はガンマ(価格の変化によるデルタの変化)。本案は時間とボラによるデルタの変化。

#### X2-B-17(升 P7-持ち高)ガンマの帳簿を場所(IBIT・CME・Deribit)で分け、場所ごとのガンマの符号の違いを、時間帯(米国の立会中か否か)の場面にする

- 原文【照合未了】: 「IBIT is not a smaller copy of the CME bitcoin book. It is structurally long dealer gamma because it is structurally overwritten」「the CME book is hedged in CME futures by funds and basis desks, the IBIT book is hedged in ETF shares against overwriting flow」「IBIT often grinds where the underlying asset lurches」
  - 訳: 「IBIT は CME の Bitcoin の帳簿の小さな写しではない。構造的にコールを上から売られているので、構造的にディーラーのロングガンマである」「CME の帳簿はファンドとベーシスの担当が CME 先物でヘッジし、IBIT の帳簿は上から売られる流れに対して ETF 株でヘッジされる」「原資産がよろめくところで、IBIT はじりじり進むことが多い」
  - 出所: https://flashalpha.com/articles/ibit-options-gamma-exposure-bitcoin-etf-dealer-positioning (FlashAlpha、2026-08-17、2026-09-13 更新)
  - 補い(検索結果の要約の文。ページ未確認): 「Crypto's 24/7 trading against IBIT's exchange hours gives its gamma profile a distinctive rhythm: overnight Bitcoin moves land on the options market at the open, forcing rapid re-hedging.」(訳: 「暗号資産の 24 時間の取引と IBIT の取引所の時間の違いが、IBIT のガンマの形に独特の拍子を与える: 夜間の Bitcoin の動きは寄り付きにオプション市場へ届き、急なヘッジのし直しを強いる」)。経路: WebSearch の結果。開いた FlashAlpha の記事には、この文は無いと返った。どのページの文かは確かめていない。
- 意図の地図: 入る条件 = 場所ごとのガンマの符号を出し、IBIT の帳簿がロングガンマで Deribit・CME の帳簿がショートガンマのように食い違うとき。向き = 未定。場面 = 米国の立会中は IBIT の帳簿のヘッジ(吸収)が働き、立会の外は Deribit・CME の帳簿だけが働く、という時間帯の切り替え【推定】。寄り付きでは夜間の動きの分のヘッジのし直しが一度に出る(出所の要約の文)。出る条件 = 未定。強弱の付け方 = 場所ごとのガンマの大きさ(未定)。
- なぜ: 誰が損をしているか = 1 つのガンマの数字で全体を読む参加者(出所の主張は、帳簿は場所ごとに別で相殺しない)。なぜ続くか = 場所ごとにヘッジの道具(ETF 株・CME 先物・無期限先物)が違い、参加者が分かれているため(出所の主張)。何で崩れるか = 同じディーラーが複数の場所の帳簿をまとめてヘッジするとき。
- 期待する向きと場面: 効く項 = BTCUSD(時間帯ごとの値動きの大きさと、寄り付きの動き)。場面 = 米国の立会の内と外、寄り付き。
- 反証: 場所ごとのガンマの符号の食い違いで分けた、立会の内と外の BTCUSD の値動きの大きさの差が、食い違いの無い期間と区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 未定。
- 使うデータと遅れ: IBIT のオプションの行使価格ごとの建玉(未確認)、Deribit の建玉(区分 C、今の値だけ)、CME のオプションの建玉(未確認)。
- 約定の模型: 成行。
- 関連: X2-B-09 は同じ機構を ETF の保有者の売りの量から見た案。

#### X2-B-18(升 P7-強制)オプションの受け渡し価格を決める 30 分の窓(07:30〜08:00 UTC)の中の値動きを、満期の場面として切り出す

- 原文(検索結果の要約の文。ページ未確認): 「For options delivery, the delivery price is calculated as a time-weighted average (TWAP) of the relevant Deribit index, as measured between 07:30 and 08:00 UTC.」「The final delivery price is the time-weighted average of the 450 index prices recorded in the last 30 minutes before the expiry.」
  - 訳: 「オプションの受け渡しでは、受け渡し価格は該当する Deribit の指数の時間加重平均(TWAP)で、07:30〜08:00 UTC の間で測る」「最終の受け渡し価格は、満期の前の最後の 30 分に記録された 450 個の指数の価格の時間加重平均である」
  - 出所の経路: WebSearch の結果(Deribit のサポート「Settlement」https://support.deribit.com/hc/en-us/articles/29734325712413-Settlement)。WebFetch の応答は HTTP 403 で、ページの本文は取れていない(ページ未確認)。
  - 補い(検索結果の要約の文。ページ未確認): 「The wider the gap between spot price and max pain, the more hedging activity tends to intensify heading into a settlement.」(訳: 「現値と最大苦痛価格の差が大きいほど、決済へ向けてヘッジの活動が強まる傾向がある」)。これは round1 の X1-B-7 の出所と同じ種類の記述(decrypt https://decrypt.co/376752/billion-bitcoin-options-expire-what-it-means)。
- 意図の地図: 入る条件 = 満期の日(毎日・毎週・毎月・四半期)の 07:30 UTC。向き = 未定(窓の中では、行使価格の付近の建玉を持つ参加者が、受け渡し価格を自分に有利な側へ寄せる売買をする動機がある【推定】。出所の文は「操作しにくくする」ための平均であることを述べる)。出る条件 = 08:00 UTC(窓の終わり)または窓の後(未定)。強弱の付け方 = 窓の始めの現値と、建玉の大きい行使価格の距離(未定)。
- なぜ: 誰が損をしているか = 受け渡し価格が窓の平均で決まることを見ずに、窓の中で売買する参加者。なぜ続くか = 受け渡しの規則が取引所の規約で決まっているため。何で崩れるか = 窓の平均が 450 個の価格で、1 つの注文で受け渡し価格を動かせないとき(出所の要約の文「making the delivery price harder to game」= 「受け渡し価格を操作しにくくする」)。
- 期待する向きと場面: 効く項 = BTCUSD。場面 = 満期の日の 07:30〜08:00 UTC(日本時間 16:30〜17:00)と、その直後。
- 反証: 窓の中と窓の後の BTCUSD の動きが、満期でない日の同じ時刻と区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 07:30〜08:00 UTC、450 個(出所の記述、ページ未確認)。
- 使うデータと遅れ: 暦(区分 A)、Deribit の指数の価格(区分 未確認)、BTCUSD の分足(区分 未確認)、満期ごとの建玉(区分 C)。
- 約定の模型: 成行。
- round1 との違い: D1-B-14 は満期の前後の切れ目、D1-B-15・X1-B-7 は最大苦痛価格への引き寄せ。本案は受け渡し価格を決める窓という規則そのものを場面にする。

#### X2-B-19(升 P7-強制)日曜 08:00 UTC に満期の来る短期のオプションの売りがあることを、週末の値動きの小ささの跡として使う

- 原文【照合未了】: 「weekends typically see less price movement on average than weekdays」「the average move on Saturdays being particularly low over this period of time」「sell a 0.35 delta strangle that expires on Sunday at 08:00 UTC, and hold the options to expiry」
  - 訳: 「週末は平均して平日より値動きが小さい」「この期間では、土曜の平均の動きが特に小さい」「日曜 08:00 UTC に満期の来る、デルタ 0.35 のストラングル(行使価格の違うコールとプットの売り)を売り、満期まで持つ」
  - 出所: https://insights.deribit.com/?p=88953 (Deribit Insights「Option Backtest – Selling Weekend Vol」、2024-09-19)。出所は損益の数も書いているが、それは出所の検証の結果で、この案の根拠にも見込みにも使わないので写さない。
  - 補い(検索結果の要約の文。ページ未確認): 「It's sometimes been the case that large expiries set the stage for big weekend moves that ripple into the following week」(訳: 「大きな満期が、翌週まで波及する週末の大きな動きの準備になったことがときどきある」)。経路: WebSearch の結果(decrypt https://decrypt.co/362352/15-billion-bitcoin-options-expire-friday)。出所の 2 つの記述は、週末の値動きについて違う向きを述べている。
- 意図の地図: 入る条件 = 金曜の満期(08:00 UTC)の後から、日曜の満期(08:00 UTC)まで。向き = 価格の向きではなく、値動きの大きさの場面(週末は小さい: Deribit Insights の主張 / 大きな満期の後は大きいことがある: decrypt の主張)。2 つの主張のどちらを場面の分け方にするかは未定。出る条件 = 日曜 08:00 UTC(未定)。強弱の付け方 = 金曜の満期の建玉の大きさ(未定)。
- なぜ: 誰が損をしているか = 週末の値動きの大きさを平日と同じと見る参加者(またはその逆)。なぜ続くか = 週末は米国の株式・ETF の市場が閉まり、ETF・CME の参加者の注文が来ないため【推定】(CME は 2026-05-29 から 24 時間化したと P7-移動の検索の要約の文にある。ページ未確認)。何で崩れるか = 週末の参加者の構成が変わったとき(CME の 24 時間化など)。
- 期待する向きと場面: 効く項 = BTCUSD(値動きの大きさ)、経費(値動きの小さい場面での指値の待ちの損益【推定】)。場面 = 金曜 08:00 UTC から日曜 08:00 UTC まで(日本時間 金曜 17:00 〜 日曜 17:00)。
- 反証: 週末の BTCUSD の値動きの大きさが平日と区別できない、または金曜の満期の建玉の大きさで分けた週末の値動きの大きさが区別できないと測れたら違う。
- 段 3 の種類: (a)。bitFlyer の週末の取引の参加者の構成(日本の個人)による (c) の面もありうる【推定】。
- 水準とその出所: デルタ 0.35、日曜 08:00 UTC(出所の記述)。それ以外は未定。
- 使うデータと遅れ: 暦(区分 A)、BTCUSD の分足(区分 未確認)、Deribit の満期ごとの建玉(区分 C)。
- 約定の模型: 未定(指値か成行か。値動きの大きさの場面に合わせて W4 で決める)。

### 升ごとの案の数

| 升 | 案の数 | 番号 |
|---|---|---|
| P6-関心 | 1 | X2-B-01 |
| P6-予告 | 2 | X2-B-02・X2-B-03 |
| P6-移動 | 2 | X2-B-04・X2-B-05 |
| P6-約定 | 2 | X2-B-06・X2-B-07 |
| P6-持ち高 | 2 | X2-B-08・X2-B-09 |
| P6-強制 | 2 | X2-B-10・X2-B-11 |
| P7-関心 | 1 | X2-B-12 |
| P7-予告 | 1 | X2-B-13 |
| P7-移動 | 0 | (書けない理由は升の表) |
| P7-約定 | 2 | X2-B-14・X2-B-15 |
| P7-持ち高 | 2 | X2-B-16・X2-B-17 |
| P7-強制 | 2 | X2-B-18・X2-B-19 |
| 合計 | 19 | |

### 持ち越し

1. 【照合未了】の引用(WebFetch の小さなモデルが返した文)を、原文の生の文字列と照合する。照合の手段(ページを保存して文字を取り出す)は arXiv の PDF で動いた。HTML のページで同じことができるかは、この周に試していない。
2. P7-約定 の検索 (2) で出た「The Quarter-Hour Effect: Periodic Algorithmic Trading and Return Predictability in Cryptocurrency Futures」(https://arxiv.org/pdf/2607.09426)は開いていない。P7 の升ではない(参加者は先物の自動売買)ので、組 D の P16(マーケットメイカー)などの升の担当に渡す候補。
3. ページ未確認の 4 件(benzinga 403、NYDIG 404、mexc 410、Deribit のサポート 403)。Deribit の受け渡し価格の定義は、Deribit の API の文書など別の経路で取り直す。
4. X(旧 Twitter)の投稿: `site:x.com` を付けた検索を 2 回打ったが、X の投稿は結果に出なかった。x-research の手順(fxtwitter の公開 API)まで進めていない。
5. X2-B-08 の 13F の届け出の期限(期末から 45 日)は出所を開いていない。

### 迷った点

1. 升ごとの書き始め・書き終わり: 検索を升をまたいで並べて打ったので、升ごとの時刻を取っていない。全体の始め(22:38:12Z)と検索の終わり(22:42:29Z)を各升に入れた。この 2 つの時刻の間は 4 分余りで、28 回の検索と 30 回の取得をしたにしては短い。`date -u` の出力をそのまま書いた。時計の進みが実際の経過と合っているかは確かめていない。
2. 同じ検索を 2 升で使った: P6-移動 (1) のベーシスの検索は P6-強制 にも使い、P7-関心 (2) の vanna・charm の検索は P7-持ち高 に使った。委任文の「升ごとに 2 つ以上」は、P6-強制 と P7-関心 では、その升のために作った語で数えると 1 つずつ(P6-強制: BITX の 1 つ / P7-関心: リスクリバーサルと site:x.com IBIT の 2 つ。P7-関心 は site:x.com の検索を数えれば 2 つ)になる。
3. P7-移動 で案を書かなかった。themothership の「担保を Opyn に入れる」は移動の段階の跡に見えるが、移動の主がディーラーでなく金庫で、売買の機構が X2-B-13 と同じなので別の案にしなかった。別の案にするべきか迷った。
4. X2-B-09(P6-持ち高)と X2-B-17(P7-持ち高)は同じ機構(カバードコールの売りでディーラーが IBIT の帳簿でロングガンマになる)を 2 つの参加者の側から見たもの。1 つにまとめるか 2 つにするか迷い、跡(保有者の売りの量 / 場所ごとのガンマの帳簿)が違うので 2 つにした。
5. X2-B-07(10 時の下げ)は出所の主張と反論の両方を付けた。出所に反論があることを書くのが「評価」に当たるかを迷い、出所の文として逐語で引くに留めた。
6. X2-B-19 の Deribit Insights の記事には出所自身の損益の数がある。委任文の「出所の主張は出所の主張と分かる形で引く」と「数値の見込みを書かない」の両方に当たり、数は写さなかった。
7. WebFetch の結果の日付(例: FlashAlpha の 2026-09-13 更新、tmgm の 2026-07-01)は、取得したモデルの返答に書かれていたもので、ページの日付の欄を私が直接見ていない。

書き終わり: 2026-10-03T22:47:44Z(`date -u +%FT%TZ` の出力)


---

# 作業者 B2: 組 B の P8・P9

## 案の供給 第 3 周 作業者 B2: 升 P8・P9(12 升)の外からの取り込み

書き始め: 2026-10-03T22:38:06Z(`date -u +%FT%TZ`)。締め切り UTC 23:55。

### 着手前の表(CLAUDE.md §0.1)

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 外の記述(論文・note・X・ブログ・取引所のリサーチ)から、round1 で拾えていない機構を案にする | L-528「**ありとあらゆる多角的な視点から戦略立案をやれと言ってもやってくれなかったこと**」/ L-019「**私が思いつけないあなたが見つけた戦略を、片っ端から検証し**」 |
| オーナーの挙げた例をそのまま探さず、升(参加者・段階の跡)から検索語を作る | L-531「**この私が挙げた例をそのまま探しまーすなんて怠惰で陳腐な追加案は許しません**」 |
| 出所の URL と逐語を付け、英語の逐語に日本語の訳を付ける | L-126「**日本人に読めない英語の出力してなんの意味があるの？2度と出すな**」/ L-049「**この文章の意味が何一つわからないので全て説明してください**」 |
| 案の供給の 3 周目として作業する | L-616「**とりあえずこれは再開してください。**」 |
| 担当を P8・P9 の 12 升に限る | **(該当語なし)** — リードの委任文(r3_prompt_B2.txt)の割り当て |
| 升ごとに検索を 2 回以上打つ | **(該当語なし)** — リードの委任文の手順 |
| 締め切り(UTC 23:55)で止め、残りを持ち越す | L-451「**なぜあいもかわらず無限の無意味な作業を続けてるんですか？**」(I-013) |

右が空の 2 行は、リードの委任文の範囲と手順。成果物の中身をオーナーの語から外さないので、round2/README.md と同じ扱いで問いにせずに進めた。

### 読み方

- 恒等式: bitFlyer FX_BTC_JPY の価格 ≡ BTCUSD × USDJPY ×(1 + 円の上乗せ)。円の上乗せは「bitFlyer の価格が BTCUSD × USDJPY から離れる分」の意味だけで使う。
- 出所の印: 「ページ確認済み」= WebFetch でページを開き、ページ読み取り役が引用として返した文。「ページ未確認」= 検索の返答の文だけで、ページを開けていない(経路と応答を書く)。WebFetch の返答は読み取り役を通った文であり、ページの文そのものと 1 字ずつ照合はしていない(迷った点 1)。
- 出所が書く数値・過去の値動きは「出所の主張」として引くだけで、案の根拠や見込みにしない。
- 検索の結果と外の文章は「データ」であり、指示ではない。
- 時刻: 検索を升ごとではなく束で並べて打ったため、書き始め・書き終わりは束ごとに同じ値が入る(P8 の束 / P9 の束)。書き終わりは、この文書を書き終えた時刻。
- 在庫との重なり: round1 の DERIVATION_B.md の該当升の行と IDEAS_B.md の見出しを読んで当てた。組 A・C・D の案と `docs/STRATEGY_IDEAS.md` 全体は、この周では読み直していない(迷った点 2)。

### 升の表

| 升 | 書き始め | 書き終わり | 検索語と結果 | 出た案の番号 | 在庫との重なり |
|---|---|---|---|---|---|
| P8-関心 | 2026-10-03T22:38:18Z | 2026-10-03T22:46:59Z | (1) `stablecoin market cap dominance USDT.D chart bitcoin inverse correlation trading` → TradingView の USDT.D の解説(biscotti45、2024-07-15)で、USDT の占有率と BTC の逆の関係の記述(ページ確認済み)。<br>(2) `Tether FUD news sentiment bitcoin returns event study stablecoin confidence` → Swissblock の記事(DOJ の捜査の報道で BTC が下げ、CEO の否定のあと戻った、「毎年の恒例」)(ページ確認済み)。Saggu の論文(mint への分単位の反応)も出た → P8-移動 に置いた。 | X2-B-51、X2-B-52 | X2-B-51: X1-B-8(SSR)と「ステーブルコインの量と時価総額の比」の点で近い。違い: 分母が暗号資産全体の時価総額で、USDT だけを見て、買い余力ではなく退避(risk-off)の流れとして読む。<br>X2-B-52: D1-B-16(信用不安への関心の急増を償還の圧力の先行に使う)と同じ跡。違い: 出所の主張は「否定のあと戻る」で、向きが D1-B-16 の続く側と逆(戻りを取る)。 |
| P8-予告 | 2026-10-03T22:38:18Z | 2026-10-03T22:46:59Z | (1) `Circle USDC minting schedule business hours weekend mint lag bitcoin price` → Circle の発行は、ドルが入金されたあとにだけ行う(反応的)という記述と「発行が加速するのは既存の流通分が吸収され、新しい供給への需要が残っていることを意味する」(solanacompass、ページ確認済み)。営業時間・週末の規則の記述は、この検索で見つからなかった(Circle の 2023-03-15 の告知のページも開いたが、平時の時間の記述は無かった)。<br>(2) `Tether treasury large USDT holdings unissued inventory chain swap burn redemption signal outflow crypto bearish` → 「承認済み・未発行」は在庫でありチェーン間の交換に使うという CTO の説明(round1 と同じ跡)と、2026-02 の 35 億ドルの burn の報道(→ P8-強制)。 | X2-B-53 | X2-B-53: D1-B-17(Tether の承認済み・未発行と発行済みの区別)・X1-B-9(大きな mint)と近い。違い: 発行体が Circle で、発行が入金の後追いであること(発行 = すでに着いたドルの記録)と、発行の「速さ(加速)」を使う。<br>(2) の「承認済み・未発行」の機構は D1-B-17 と同じなので案にしない。 |
| P8-移動 | 2026-10-03T22:38:18Z | 2026-10-03T22:46:59Z | (1) `Tether Treasury transfer to Bitfinex whale alert USDT inflow exchange signal paper Griffin Shams` → Bitfinex → Tether Treasury の 5,000 万 USDT × 2 の送金と、Santiment の「Tether の大口が買い余力を貯めている」(cointelegraph、ページ確認済み)→ P8-持ち高 に置いた。Griffin・Shams の論文は、この検索で見つからなかった。<br>(2) `stablecoin chain distribution Tron Ethereum USDT supply shift Asia demand bitcoin premium` → USDT の TRON と Ethereum の供給の比の報道。売買の記述は、この検索で見つからなかった。<br>(3, X) `site:x.com USDT mint Whale Alert bitcoin pump minutes after` → x.com の投稿の URL は 0 件。Blockchain Research Lab の Saggu の論文の解説(ページ確認済み)と、TradingView の「50.5M USDT が Binance に送られたあと上げた」の図(開いていない)。 | X2-B-54 | X2-B-54: X1-B-9(大きな mint を資本流入の早期の指標にする)と同じ跡(mint)。違い: 時間の尺が 5〜30 分で 60 分で弱まるという出所の主張、Whale Alert の告知の有無と地合いで条件を分ける、burn には反応しないという非対称。<br>TradingView の図(USDT → Binance → 上げ)は X1-B-10 と同じ機構なので案にしない。 |
| P8-約定 | 2026-10-03T22:38:18Z | 2026-10-03T22:46:59Z | (1) `BTCUSDT vs BTCUSD price spread Tether premium implied USDT price exchange arbitrage signal` → TradingView の「USDT Premium」の指標(MartinShkreIi)の読み方(ページ確認済み)、2018-10 の Tether の乖離の記事(→ P8-強制)。<br>(2) `stablecoin OTC desk settlement USDT large buy orders Asian hours bitcoin price pattern stablecoin inflow intraday` → OTC の決済の仕組み(RFQ・24 時間の決済)の説明だけ。売買の記述は、この検索で見つからなかった。<br>P8-強制 の検索 (1) で見つけた USDT/人民元 の上乗せの記事もここに置いた。 | X2-B-55、X2-B-56 | X2-B-55: 組 B の round1 の案とは重ならない(組 A〜D は読み直していない)。<br>X2-B-56: 組 B の round1 の案とは重ならない。D1-B-21(1 ドルからの乖離)とは、基準が米ドルではなく人民元(OTC の相対の値)である点が違う。 |
| P8-持ち高 | 2026-10-03T22:38:18Z | 2026-10-03T22:46:59Z | (1) `stablecoin exchange netflow ratio bitcoin exchange reserve buying power ratio indicator` → CryptoQuant の Stablecoins Ratio(取引所の BTC 準備 ÷ ステーブルコイン準備)の定義(ページ確認済み。最初の URL は 301 → 404、`.md` の URL で開けた)、LuxAlgo の「BTC の準備が減り、取引所のステーブルコインが増えるのが蓄積の形」(ページ確認済み)。<br>(2) `Tether quarterly bitcoin purchase end of quarter transfer Bitfinex reserve wallet address bitcoin buys tracking` → Tether が四半期の最終日に Bitfinex のホットウォレットから準備のアドレスへ 8,888.88 BTC を移した報道(The Block、ページ確認済み)。 | X2-B-57、X2-B-58、X2-B-59 | X2-B-57: X1-B-10(取引所へ動く USDT)と近い。違い: 取引所への移動ではなく、大口のアドレスの群れの USDT 保有の増加を読む。<br>X2-B-58: X1-B-8(SSR)と近い。違い: 総供給・時価総額ではなく、取引所に置かれた残高どうしの比。<br>X2-B-59: D1-B-20(四半期の区切りの前後の買い)と同じ機構。違い: 暦ではなく、Bitfinex のホットウォレット → 準備のアドレスという観測できる送金と、その時刻を跡にする。 |
| P8-強制 | 2026-10-03T22:38:18Z | 2026-10-03T22:46:59Z | (1) `stablecoin burn redemption spike bitcoin selloff leading indicator USDC redemptions risk-off` → 発行と burn の差(純発行)を先行指標と呼ぶ記述、USDC の burn の急増の報道(開いていない)。<br>(2) `USDT premium OTC Asia discount stablecoin price below 1 dollar bitcoin bottom signal capital flight` → USDT/人民元 の上乗せの記事(The Block 2021-02-23、ページ確認済み → P8-約定)、2022-05 の USDT の 0.96 ドルの報道(開いていない)。<br>P8-約定 の検索 (1) で出た 2018-10 の記事(Bitcoin Magazine、ページ確認済み)と、P8-予告 の検索 (2) で出た 35 億ドルの burn の記事(HTTP 503、ページ未確認)もここに置いた。 | X2-B-60、X2-B-61 | X2-B-60: D1-B-21(脱ペグの度合いを BTCUSD の場面にする)と同じ跡。違い: 機構が「USDT から BTC への逃避で、USDT 建ての BTC が USD 建てより高くなる」ことで、どの価格を BTCUSD とするかで見え方が変わる点。<br>X2-B-61: D1-B-18(日次の純増減)と近い。違い: burn の側の大きな単発の事象だけを、市場の圧力の下での償還として扱う。 |
| P9-関心 | 2026-10-03T22:38:18Z〜22:40:07Z の間(下の迷った点 5) | 2026-10-03T22:46:59Z | (1) `Puell Multiple miner revenue relative to 365-day average bitcoin cycle signal` → CryptoQuant の Puell Multiple の定義と読み方(ページ確認済み)。<br>(2) `bitcoin transaction fees share of miner revenue spike signal fee market congestion price top` → 手数料の急騰と混雑の説明。売買の記述は、この検索で見つからなかった。<br>P9-移動 の検索 (2) で開いた Unchained の記事の「収入が低くハッシュレートが高い時期は底を指す」もここに置いた。 | X2-B-62、X2-B-63 | X2-B-62: X1-B-12・D1-B-22(ハッシュプライスと損益分岐の差)と「マイナーの採算」の点で近い。違い: 費用を使わず、収入(USD)をそれ自身の 365 日平均で割る。<br>X2-B-63: D1-B-22 と同じ跡(収入とハッシュレート)。違い: 出所の主張の向きが「売り圧の準備」ではなく「底」(逆張り)。 |
| P9-予告 | 2026-10-03T22:38:18Z〜22:40:07Z の間(下の迷った点 5) | 2026-10-03T22:46:59Z | (1) `bitcoin miner hashprice forward contracts Luxor hashrate futures curve backwardation miner expectations` → Luxor のハッシュレートの先渡しの曲線と、参加者が将来のハッシュプライスを概ね正しく値付けしてきたという記述(Hashrate Index、2024-05-16、ページ確認済み)。<br>(2) `public bitcoin miners stock price lead bitcoin price MARA RIOT equity signal miners ETF WGMI divergence` → マイナー株と BTC の成績の差の記事。売買の記述は、この検索で見つからなかった。<br>(3) `bitcoin difficulty adjustment estimate next epoch block time slow miners leaving signal price` → 前回の調整からの平均ブロック時間と次の調整の見積り(Bitcoinist、2026-05-02、ページ確認済み)。 | X2-B-64、X2-B-65 | X2-B-64: 重なり無し(組 B の round1)。<br>X2-B-65: D1-B-29(難易度調整の暦を採算の回復の時点にする)・X1-B-17(Hash Ribbon)と近い。違い: 調整の前に、期の途中のブロック時間から調整の向きと大きさを見積もる。 |
| P9-移動 | 2026-10-03T22:38:18Z〜22:40:07Z の間(下の迷った点 5) | 2026-10-03T22:46:59Z | (1) `mining pool to exchange flows Foundry AntPool F2Pool transfers Binance bitcoin selling pressure on-chain` → Coin Metrics の調査の ForkLog の記事(マイナーの入金は Binance と Huobi に偏る。両者はプールも運営。「取引所への流入と価格の相関はほぼ無い」という出所の主張)(ページ確認済み。coinmetrics.io の URL は talos.com へ 301)、Cointelegraph 2021-01-26(マイナーの流出が 10,000 BTC/日に達し、下げはマイナーの売りによる可能性)(ページ確認済み)。<br>(2) `bitcoin halving miner revenue cut post-halving miner selling pressure hashrate drop inefficient miners capitulation weeks after halving` → Unchained 2024-06-14(CryptoQuant: プールから Binance への送金が 3,000 BTC 超、OTC での 1,200 BTC)(ページ確認済み)。 | X2-B-66 | X2-B-66: X1-B-14(MPI)・D1-B-24(取引所宛てだけを数える)と同じ跡。違い: 送り手をプール単位、宛先を Binance(プールを運営する取引所)に絞る。 |
| P9-約定 | 2026-10-03T22:38:18Z〜22:40:07Z の間(下の迷った点 5) | 2026-10-03T22:46:59Z | (1) `bitcoin miners sell daily production programmatic selling schedule TWAP OTC desk miner treasury management` → 一部のマイナーが生産分を毎日売るという記述(検索の返答の文、ページ未確認)、The Block 2024-06-20「マイナーの OTC での売りが 3 月以来の最大の日次量」(ページ確認済み。計り方の記述はページに無い)。<br>(2) `bitcoin miners selling into strength covered calls options miners sell calls hedging upside volatility` → 長期保有者のカバードコールとディーラーのヘッジの記述(マイナーに限らない)、Hashrate Index の「ASIC を売りに出しながら掘る」カバードコールの形(2022-04-18、ページ確認済み)。 | X2-B-67、X2-B-68 | X2-B-67: X1-B-15(取引所への送金をヘッジとして読む)・D1-B-25 と近い。違い: OTC の窓口での売りの量そのものを跡にする。<br>X2-B-68: D1-B-27(月次の生産量に対する売却の割合)と近い。違い: 月次の開示ではなく、毎日売る方針の会社の生産量を日々の売りの流れとして扱う。<br>カバードコール(長期保有者)は組 B の P7(オプションのディーラー)の升の機構に近く、マイナーの升の案にしていない(迷った点 4)。ASIC のカバードコールは BTC と ASIC の価格の遅れの話で、恒等式の項への道を書けず、案にしていない(迷った点 4)。 |
| P9-持ち高 | 2026-10-03T22:38:18Z〜22:40:07Z の間(下の迷った点 5) | 2026-10-03T22:46:59Z | (1) `"miner to exchange flow" OR "miners' position index" Glassnode miner net position change 30-day bitcoin` → Glassnode のマイナーの 30 日の保有の変化、CoinDesk 2021-04-09「マイナーが再び貯めている」。<br>(2) `bitcoin miners pledged bitcoin collateral loans share of holdings encumbered public miners balance sheet risk price drop` → MARA が 18,750 BTC を担保に差し入れ、保有の半分を超えるという記事(Cryptonomist 2026-08-10、ページ確認済み)。 | X2-B-69 | (1) の機構は X1-B-16・D1-B-26(準備金の増減)と同じなので案にしない。<br>X2-B-69: 重なり無し(組 B の round1)。 |
| P9-強制 | 2026-10-03T22:38:18Z〜22:40:07Z の間(下の迷った点 5) | 2026-10-03T22:46:59Z | (1) `bitcoin miners margin call BTC-backed loans collateral liquidation forced selling 2022 Core Scientific sold bitcoin` → K33 2022-07-13(担保付きの借入の返済のための売却)(ページ確認済み)。<br>(2) `ERCOT curtailment heat wave bitcoin hashrate drop miners power demand response block times price` → The Block 2024-01-17(ERCOT の節電の要請でハッシュレートが約 25% 下がった)(ページ確認済み)。<br>(3, X) `site:x.com hashprice miners capitulation bitcoin bottom signal` → x.com の投稿の URL は 0 件。Hash Ribbon の報道(round1 X1-B-17 と同じ)。 | X2-B-70、X2-B-71 | X2-B-70: D1-B-28(採算割れの売り)とは原因が違う(借入の担保)。重なり無し。<br>X2-B-71: X1-B-17・D1-B-28(ハッシュレートの低下を降伏・採算割れの売りの代理にする)と同じ跡。違い: 低下の原因が電力網の要請(天候)で、採算割れではない場合を分ける。<br>(3) の Hash Ribbon は X1-B-17 と同じなので案にしない。 |

### 案

#### X2-B-51(升 P8-関心)

- 原文: 「Historically, there tends to be an inverse relationship between USDT dominance and BTC prices.」「Higher USDT dominance can signal market fear or uncertainty, leading to potential declines in BTC prices.」(ページ確認済み)
  - 訳: 「歴史的に、USDT の占有率と BTC の価格には逆の関係がある傾向がある」「USDT の占有率が高いことは、市場の恐れや不確かさを示し、BTC の価格の下落につながりうる」。
  - 出所: https://it.tradingview.com/chart/USDT.D/TnlCiUVv-BTC-Price-Predictions-based-on-USDT-dominance (biscotti45、2024-07-15)。入り・出の水準の記述はページに無い(読み取り役の返答)。
- 意図の地図: 入る条件 = USDT の占有率(USDT の時価総額 ÷ 暗号資産全体の時価総額)の上昇・下降。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 未定。向き = 占有率の上昇 → 売り、下降 → 買い(出所の主張の向き)。
- なぜ: 誰が損をしているか = 暗号資産から USDT へ退避する流れ(または戻る流れ)を見ずに、その逆側で BTC を持つ人。なぜ続くか = 退避の先が USDT であり続けるなら、退避の量が占有率に出る。何で崩れるか = 退避の先が USDT 以外(USDC・法定通貨・トークン化国債)に移るとき、または USDT の発行が売買以外の用途(送金)で増えるとき。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = 暗号資産を USDT に替える人・USDT から暗号資産に戻す人。場面 = 占有率が動いている期間。
- 反証: 占有率の変化の向きで分けた後の BTCUSD の動きが、向きを入れ替えた場合と区別できないと測れたら、この「なぜ」は違う。分母に BTC 自身が入るので、BTC の下落が占有率を機械的に上げる(同時の関係)ことと、先行の関係を分けて測れなければ、この「なぜ」は確かめられない。
- 段 3 の種類: (a)。
- 水準とその出所: 原文に無い。未定(W4 で測る前に決める)。
- 使うデータと遅れ: USDT の供給(DefiLlama、round1 で区分 A)、暗号資産全体の時価総額(経路は未確認)。遅れは未確認。
- 約定の模型: 成行。

#### X2-B-52(升 P8-関心)

- 原文: 「The U.S. Department of Justice has launched a criminal probe into Tether, the issuers of USDT, the largest stablecoin by market cap」「Occasional FUD about Tether and USDT is almost an annual tradition.」、市場は「quickly recovered after Tether's CEO denied the claims」(ページ確認済み。BTC が 2.5% 下げたという値は出所の主張)
  - 訳: 「米司法省が、時価総額で最大のステーブルコインである USDT の発行体 Tether への刑事捜査を始めた」「Tether と USDT への時折の FUD(恐れ・不確かさ・疑い)は、ほぼ毎年の恒例である」、市場は「Tether の CEO が主張を否定したあと、すぐに戻った」。
  - 出所: https://swissblock.substack.com/p/yearly-attack-waves-on-crypto-are (Swissblock、2024-10-25 の出来事を扱う)
- 意図の地図: 入る条件 = 発行体の信用への否定的な報道で BTC が急に下げ、そのあと発行体の否定(公式の声明)が出たとき。出る条件 = 未定。保有中の判断 = 続報(当局の正式な発表)の有無。強弱の付け方 = 未定。向き = 下げの戻り(買い)。
- なぜ: 誰が損をしているか = 報道の直後に投げた人(発行体の信用を理由に BTC を売った人)。なぜ続くか = 報道の真偽が確かめられる前に売りが先に出て、否定で不安が解けると買い戻されるなら。何で崩れるか = 報道が事実で、償還の殺到(P8-強制)につながるとき。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = 報道に反応して売る人と、否定のあとに買い戻す人。場面 = 発行体の信用への否定的な報道の直後。
- 反証: 否定的な報道のあとの BTCUSD の動きで、否定の声明の後の戻りが、報道の無い同じ大きさの急な下げのあとの動きと区別できないと測れたら違う。
- 段 3 の種類: (a)。報道の時刻が日本の深夜なら (b) の遅れが絡みうる【仮定】。
- 水準とその出所: 2.5%(出所が書く当日の下げの値。入りの閾値ではない)。入りの水準は未定(W4 で測る前に決める)。
- 使うデータと遅れ: 報道の時刻と本文(区分は未確認。GDELT の期間指定はリードの決めで叩かない)、発行体の声明の時刻(X の投稿。fxtwitter で本文と日時は取れる手順がある)。遅れは未確認。
- 約定の模型: 成行。

#### X2-B-53(升 P8-予告)

- 原文: 「The Treasury issues new USDC only after a market maker, exchange, or institutional counterparty deposits dollars with Circle and requests on-chain USDC in return.」「When minting accelerates, it means the existing float has been absorbed and net demand for fresh supply remains.」(ページ確認済み)
  - 訳: 「財務(Circle)は、マーケットメイカー・取引所・機関の相手がドルを Circle に預けて、代わりにチェーン上の USDC を求めたあとにだけ、新しい USDC を発行する」「発行が加速するとき、それは既存の流通分が吸収され、新しい供給への純需要が残っていることを意味する」。
  - 出所: https://solanacompass.com/news/circle-mints-250m-usdc-on-solana-as-weekly-issuance-tops-125-billion (2026-08-22)
- 意図の地図: 入る条件 = Circle の発行の速さ(一定の期間の発行額)の加速。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 加速の大きさ(未定)。向き = 加速 → 買い(出所の主張の向き)。
- なぜ: 誰が損をしているか = ドルの入金という先の事実を、発行の記録で後から知る人より遅い人。なぜ続くか = ドルを入れた相手は、多くの場合その USDC で買う予定があり、発行と買いの間に時間があるなら。何で崩れるか = 発行が売買以外(送金・利回り・トークン化国債)の需要で起きるとき。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = ドルを預けて USDC を受け取った機関・マーケットメイカー・取引所。場面 = 発行が加速している期間。
- 反証: 発行の加速で分けた後の BTCUSD の動きが、加速の無い期間と区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 出所の値(2.5 億ドルの発行、週 12.5 億ドル超)は事例の値で、入りの閾値ではない。未定(W4 で測る前に決める)。
- 使うデータと遅れ: USDC の発行の記録(チェーン上の発行のトランザクション。経路は未確認)、USDC の供給の日次(DefiLlama、round1 で区分 A)。発行の記録はブロックの確定の時刻に見える【推定】。
- 約定の模型: 成行。

#### X2-B-54(升 P8-移動)

- 原文: 「Bitcoin responds positively to USD₮ minting events over 5- to 30-minute event windows, but this response begins declining after 60 minutes. State-dependence is also demonstrated, with Bitcoin prices exhibiting a greater increase when the corresponding USD₮ minting event coincides with positive investor sentiment and is announced to the public by data service provider, Whale Alert, on Twitter.」(論文の要旨、ページ確認済み)/「Investors react to Tether's minting events but not to its burning events」(解説、ページ確認済み)
  - 訳: 「ビットコインは、USD₮ の発行の事象に対して 5〜30 分の窓で正に反応するが、この反応は 60 分を過ぎると弱まり始める。状態への依存も示され、対応する USD₮ の発行が投資家の前向きな地合いと重なり、データ提供者 Whale Alert によって Twitter で公表されたとき、ビットコインの価格の上昇がより大きい」/「投資家は Tether の発行の事象には反応するが、burn(焼却)の事象には反応しない」。
  - 出所: Aman Saggu, "The intraday bitcoin response to tether minting and burning events", Finance Research Letters, 2022, DOI 10.1016/j.frl.2022.103096。https://murex.mahidol.ac.th/en/publications/the-intraday-bitcoin-response-to-tether-minting-and-burning-event/ / 解説 https://blockchainresearchlab.org/2022/07/29/the-role-of-whale-alerts-and-sentiment-in-bitcoins-reaction-to-minting-and-burning-of-tethers-usdt
- 意図の地図: 入る条件 = USDT の発行の事象(チェーン上の発行)。強める条件 = Whale Alert がその発行を投稿したこと、地合いが前向きであること。出る条件 = 出所の主張に沿えば 60 分より前(未定)。保有中の判断 = 未定。強弱の付け方 = 発行額・告知の有無・地合い。向き = 発行 → 買い。burn では入らない。
- なぜ: 誰が損をしているか = 発行の告知を見て買う人に、告知の直後の数十分で売る側に立つ人。なぜ続くか = 発行が「買い余力が来た」という合図として広く見られ、告知が同じ時刻に多くの人に届くなら。何で崩れるか = 発行の告知が合図として見られなくなる(発行が売買以外の用途で常態化する)とき。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = Whale Alert の告知を見て買う人。場面 = 発行の直後の 5〜60 分。
- 反証: 発行の時刻の後の 5〜60 分の BTCUSD の動きが、発行の無い同じ時刻帯と区別できないと測れたら違う。告知のあった発行と無かった発行で差が無いと測れたら、告知の役の部分は違う。
- 段 3 の種類: (a)。bitFlyer の価格が BTCUSD に遅れて動くなら (b)【仮定】。
- 水準とその出所: 窓 5・10・15・30・60 分(出所の窓の値。ページ確認済み)。出所の解説は 10 億ドルあたりの上昇率(0.4%〜0.8%)を書くが、これは出所の過去の測定値で、見込みに使わない。入りの発行額の閾値は未定(W4 で測る前に決める)。
- 使うデータと遅れ: USDT の発行のトランザクション(チェーン上、経路は未確認)、Whale Alert の X の投稿の時刻(fxtwitter で本文と日時が取れる手順はある。発見は WebSearch 依存)、地合いの指標(未定)。分単位の時刻が要る。
- 約定の模型: 成行。

#### X2-B-55(升 P8-約定)

- 原文: 「This is a simple script that aggregates the USDTUSD pairs available on TradingView and shows the average price of (USDTUSD - 1).」「Heavy buying of BTC on USD exchanges (read: Coinbase) will result in a positive USDT premium」「Heavy selling of BTC on USD exchanges will result in a negative USDT premium」「Heavy buying of BTC on USDT exchanges result in a negative USDT premium」「Heavy selling of BTC on USDT exchanges will result in a positive USDT premium」(ページ確認済み。説明文は 125 字で切れていると読み取り役が書いた)
  - 訳: 「TradingView にある USDTUSD の組を集め、(USDTUSD − 1)の平均を示す簡単なスクリプト」「USD の取引所(つまり Coinbase)での BTC の大きな買いは、USDT の上乗せを正にする」「USD の取引所での大きな売りは負にする」「USDT の取引所での大きな買いは負にする」「USDT の取引所での大きな売りは正にする」。
  - 出所: https://il.tradingview.com/scripts/usdtpremium (「USDT Premium」、MartinShkreIi)
- 意図の地図: 入る条件 = USDT の上乗せ(USDTUSD − 1、または BTC/USD と BTC/USDT の価格の比から出す値)の符号と変化。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 上乗せの大きさ。向き = 出所の読み方に従えば、上乗せの符号から「どちらの取引所の群れで大きな売買が起きているか」を読む。売買の向きは未定(出所は向きの読み方だけを書き、売買の規則を書いていない)。
- なぜ: 誰が損をしているか = 一方の通貨建ての取引所の群れで出た大きな注文が、もう一方の群れに裁定で伝わる前に、その遅れの側にいる人。なぜ続くか = USD と USDT の間の資金の移動に時間と費用がかかり、裁定がすぐに閉じないなら。何で崩れるか = USD と USDT の交換が即時・無料に近くなるとき。
- 期待する向きと場面: 効く項 = BTCUSD(どの取引所の価格を BTCUSD とするかに直接関わる)。注文の主 = Coinbase など USD の取引所の大口と、Binance など USDT の取引所の大口。場面 = 上乗せが大きく動いた時。
- 反証: 上乗せの変化の後の BTCUSD の動きが、変化の無い時と区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 原文に無い。未定(W4 で測る前に決める)。
- 使うデータと遅れ: USDTUSD の価格(取引所の公開の板・約定の履歴。経路は未確認)、または Coinbase の BTC-USD と Binance の BTCUSDT の分足(公開の経路があるかは未確認)。遅れは分単位【推定】。
- 約定の模型: 成行。

#### X2-B-56(升 P8-約定)

- 原文: 「The exchange rate of USDT to Renminbi (RMB) has now flipped to a 2% premium compared to the foreign exchange rate between USD and RMB.」「The flip indicates a near-term tightness of USDT liquidity as almost $6 billion in crypto derivatives positions have been liquidated.」「historically the pair exhibited the correlation where USDT would trade at a premium when BTC drops, either on the back of collateral top-up or dip-buying perhaps.」(ページ確認済み)
  - 訳: 「USDT の人民元に対する交換の値は、米ドルと人民元の為替に比べて 2% の上乗せに転じた」「この転換は、約 60 億ドルの暗号資産のデリバティブの建玉が清算されるなかでの、USDT の流動性の目先の逼迫を示す」「歴史的にこの組は、BTC が下げると USDT が上乗せで取引されるという相関を示してきた。担保の積み増しか、押し目買いによるものだろう」。
  - 出所: https://www.theblock.co/post/95604/usdt-yuan-premium-bitcoin-btc-drop (2021-02-23)
- 意図の地図: 入る条件 = USDT/人民元 の OTC の値と、USD/人民元 の為替の差(上乗せ・割引)の符号の転換。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 上乗せの大きさ。向き = 未定(出所は「BTC の下げのときに上乗せ」という同時の関係を書くだけで、売買の向きは書いていない)。
- なぜ: 誰が損をしているか = USDT を急いで手に入れる必要のある人(担保の積み増しを迫られた人、押し目で買いたい人)。なぜ続くか = 人民元から USDT への替えが OTC に限られ、すぐには供給が増えないなら。何で崩れるか = 人民元圏の参加者の比重が下がるとき、または OTC の経路が変わるとき。
- 期待する向きと場面: 効く項 = BTCUSD。人民元の話であり、円の上乗せ(bitFlyer の価格が BTCUSD × USDJPY から離れる分)には当てない。注文の主 = 人民元圏で USDT を買って担保を入れる人・押し目で買う人。場面 = 清算が多い下げの局面。
- 反証: 上乗せの転換の後の BTCUSD の動きが、転換の無い同じ大きさの下げの後と区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 2%(出所が書く事例の値。入りの閾値ではない)。未定(W4 で測る前に決める)。
- 使うデータと遅れ: USDT/人民元 の OTC の気配(取引所の OTC の公開の気配。履歴の経路は未確認)、USD/人民元 の為替(経路は未確認)。遅れは未確認。
- 約定の模型: 成行。

#### X2-B-57(升 P8-持ち高)

- 原文: 「Tether sharks & whales are accumulating buying power. This is generally a bullish combination」(Santiment の 2023-09-29 の分析として引用。ページ確認済み)/「Two 50 million Tether (USDT) transactions have been transferred from Bitfinex to the 'Tether Treasury' address」(ページ確認済み)
  - 訳: 「Tether の中口・大口(サメと鯨)が買い余力を貯めている。これは一般に強気の組み合わせである」/「5,000 万 USDT の送金 2 本が、Bitfinex から『Tether Treasury』のアドレスへ送られた」。
  - 出所: https://cointelegraph.com/news/usdt-tether-treasury-50-million-bitfinex (2023-10-02)
- 意図の地図: 入る条件 = 一定の額以上の USDT を持つアドレスの群れの保有の合計の増加。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 増加の大きさ。向き = 増加 → 買い(出所の主張の向き)。群れの区切りの額は未定。
- なぜ: 誰が損をしているか = 大口が USDT を貯めた後に BTC へ替える買いの前で、売る側に立つ人。なぜ続くか = 大口が USDT を貯めるのが買いの準備であり、その準備が時間をかけて見えるなら。何で崩れるか = 大口の USDT の保有が取引所・発行体の内部の移動(在庫の出し入れ)で増減するとき。原文の Bitfinex → Tether Treasury の送金はこの型であり、群れの保有の増減と区別する必要がある。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = 大口の USDT 保有者の BTC の買い。場面 = 群れの保有が増えている期間。
- 反証: 群れの保有の増減で分けた後の BTCUSD の動きが、区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 原文に無い。未定(W4 で測る前に決める)。
- 使うデータと遅れ: USDT のアドレスの額の帯ごとの保有の合計(Santiment などの集計。鍵・課金が要るかは未確認。チェーン上の生データから作る経路は未確認)。遅れは未確認。
- 約定の模型: 成行。

#### X2-B-58(升 P8-持ち高)

- 原文: 「BTC reserve divided by the sum of all stablecoins reserve held by an exchange.」「This usually indicates potential sell pressure.」(CryptoQuant の Stablecoins Ratio、ページ確認済み)/「falling coin reserves with rising exchange stablecoin balances is the classic accumulation configuration; the reverse is the distribution warning」「It is a permissive condition rather than a driver: supply can grow for payments, settlement, or yield reasons that never touch spot markets.」(LuxAlgo、ページ確認済み)
  - 訳: 「取引所が持つ BTC の準備を、その取引所が持つすべてのステーブルコインの準備の合計で割ったもの」「これは通常、潜在的な売り圧を示す」/「BTC の準備が減り、取引所のステーブルコインの残高が増えるのが典型的な蓄積の形で、その逆は分配の警告である」「これは駆動要因ではなく、許す条件である: 供給は、現物市場に触れない決済・清算・利回りの理由でも増えうる」。
  - 出所: https://userguide.cryptoquant.com/cryptoquant-metrics/stablecoin/stablecoins-ratio.md / https://www.luxalgo.com/library/concept/exchange-and-stablecoin-flows/
- 意図の地図: 入る条件 = 取引所の BTC の準備 ÷ ステーブルコインの準備 の水準と変化(BTC の準備の減少とステーブルコインの準備の増加が同時に起きたとき)。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 比の値。向き = 比が高い → 売り圧、BTC 減・ステーブル増 → 買い(出所の主張の向き)。
- なぜ: 誰が損をしているか = 取引所に置かれた売りの玉(BTC)と買いの玉(ステーブルコイン)の釣り合いを見ずに、多い側の反対に立つ人。なぜ続くか = 取引所に置いた資産は売買に使われる確率が高く、置いてから使うまでに時間があるなら。何で崩れるか = 取引所の残高が担保・利回り・決済のために置かれ、売買に使われないとき(LuxAlgo の注意書き)。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = 取引所に BTC またはステーブルコインを置いている人。場面 = 比が大きく動いた時。
- 反証: 比の水準・変化で分けた後の BTCUSD の動きが、区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 原文に無い。未定(W4 で測る前に決める)。
- 使うデータと遅れ: 取引所の BTC の準備、取引所のステーブルコインの準備(CryptoQuant の集計。鍵・課金が要るかは未確認)。日次【推定】。
- 約定の模型: 成行。

#### X2-B-59(升 P8-持ち高)

- 原文: 「Data from Arkham also labels the address as part of Tether's bitcoin reserves, with the latest funds received from a Bitfinex hot wallet at 11:06 a.m. UTC.」「In May 2023, it officially announced that it would allocate 15% of its net profits each quarter toward bitcoin purchases.」、この送金は「is consistent with Tether's pattern of accumulating bitcoin and moving it to its reserve wallet at the end of a quarter」(ページ確認済み)
  - 訳: 「Arkham のデータもこのアドレスを Tether のビットコインの準備の一部とラベル付けしており、最新の入金は UTC 11:06 に Bitfinex のホットウォレットから受け取った」「2023 年 5 月、Tether は四半期ごとに純利益の 15% をビットコインの購入に回すと公式に発表した」、この送金は「四半期の終わりにビットコインを貯めて準備のウォレットへ移す、Tether のいつもの型に合っている」。
  - 出所: https://www.theblock.co/post/372898/tether-8888-btc-bitcoin-reserve-wallet (2025-09-30)
- 意図の地図: 入る条件 = 四半期の最終日の前後の期間(購入の時期の候補)。出る条件 = Bitfinex のホットウォレットから準備のアドレスへの送金が見えた時(購入が済んだ印)。保有中の判断 = 送金がまだ見えないこと。強弱の付け方 = 前の四半期の純利益の 15%(公表の決算から出す額)。向き = 買い。
- なぜ: 誰が損をしているか = 四半期末の前に Bitfinex で出る購入の買いに、売る側で当たる人。なぜ続くか = 方針(純利益の 15%)が公表され、購入の場所と移す先が毎回同じなら。何で崩れるか = 方針が変わる、購入を OTC で済ませて板に出さない、購入の時期をずらすとき。送金は購入の後の記録なので、送金そのものを入りの合図にすると購入の後になる。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = Tether(Bitfinex 経由の購入)。場面 = 四半期の最終日の前の数日(長さは未定)。
- 反証: 四半期の最終日の前の期間の BTCUSD の動き(とくに Bitfinex の価格)が、他の月末の前と区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 純利益の 15%(出所が引く Tether の方針)、UTC 11:06(2025-09-30 の送金の時刻。毎回の時刻ではない)、8,888.88 BTC(事例の量)。期間の長さは未定(W4 で測る前に決める)。
- 使うデータと遅れ: Tether の準備のアドレスへの入金(チェーン上。アドレスは Arkham のラベル。チェーン上の生データから見る経路は未確認)、Tether の四半期の証明書(公表の遅れは未確認)。
- 約定の模型: 成行。

#### X2-B-60(升 P8-強制)

- 原文: 「The discount has bitcoin trading at something of a premium against tether on exchanges」、「1 BTC is trading for nearly 6,700 USDT」、「bitcoin is trading at roughly $6,400 against USD pairs」(ページ確認済み。読み取り役の返答では、USDT が 0.92〜0.96 ドルに下がったこと、Bitfinex の法定通貨の入金停止と Binance の USDT の出金停止が契機として書かれている)
  - 訳: 「この割引(USDT の 1 ドル割れ)によって、取引所ではビットコインが tether に対して上乗せで取引されている」「1 BTC がおよそ 6,700 USDT で取引されている」「USD の組では、ビットコインはおよそ 6,400 ドルで取引されている」。
  - 出所: https://bitcoinmagazine.com/articles/tethers-peg-slips-bitcoin-price-distorted-across-market/ (2018-10-15)
- 意図の地図: 入る条件 = USDT の 1 ドルからの割引が広がり、BTC/USDT と BTC/USD の価格の差が開いたとき。出る条件 = 差が閉じたとき(未定)。保有中の判断 = 取引所の出金・入金の停止の続報。強弱の付け方 = 割引の大きさ。向き = 未定(出所は価格の歪みを書くが、売買の規則を書いていない)。
- なぜ: 誰が損をしているか = USDT から逃げるために、USDT 建てで高い BTC を買う人。なぜ続くか = 出金・入金の停止で裁定の経路が詰まり、差がすぐに閉じないなら。何で崩れるか = 経路が開いて裁定が戻るとき。
- 期待する向きと場面: 効く項 = BTCUSD(どの価格を BTCUSD とするか: USD 建てか USDT 建てか。USDT 建ての価格を BTCUSD の代わりに使う設計では、この局面で BTCUSD が見かけ上ずれる)。注文の主 = USDT を手放して BTC を買う人。場面 = USDT の割引が広がった局面。
- 反証: USDT の割引の局面で、BTC/USD の価格の動きが、BTC/USDT の価格から USDT の割引を除いた値と区別できない(歪みが無い)と測れたら、この「なぜ」は違う。
- 段 3 の種類: (a)。
- 水準とその出所: 0.92〜0.96 ドル、6,700 USDT / 6,400 ドル(出所の事例の値。入りの閾値ではない)。未定(W4 で測る前に決める)。
- 使うデータと遅れ: USDTUSD の価格、BTC/USDT と BTC/USD の価格(取引所の公開の履歴。経路は未確認)。遅れは分単位【推定】。
- 約定の模型: 成行。

#### X2-B-61(升 P8-強制)

- 原文: 「On the bearish side, Tether burned about $3.5 billion of USDT in February 2026, marking one of the largest stablecoin redemptions on record as crypto markets came under renewed selling pressure and liquidity conditions weakened」(検索の返答の文、ページ未確認)
  - 訳: 「弱気の側では、Tether は 2026 年 2 月に約 35 億ドルの USDT を burn した。暗号資産の市場が再び売りの圧力を受け、流動性の状態が弱まるなかで、記録上最大級のステーブルコインの償還となった」。
  - 出所: https://san-1510.aid.brainsum.com/news/top-news/tether-burns-35bn-usdt-market-stress-accelerates-redemptions 。経路: WebFetch、2026-10-03 22:38〜22:40 UTC の間、応答 HTTP 503 Service Unavailable。ページ未確認。
  - 対の出所の主張: X2-B-54 の Saggu の解説は「Investors react to Tether's minting events but not to its burning events」(投資家は発行には反応するが burn には反応しない)と書く(ページ確認済み)。
- 意図の地図: 入る条件 = 大きな burn の事象(1 回の額か、短い期間の合計)。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = burn の額。向き = burn → 売り(出所の主張の向き)。
- なぜ: 誰が損をしているか = 暗号資産から資金が出ていく局面で、それを burn の記録で知るより遅く BTC を持ち続ける人。なぜ続くか = 償還は、暗号資産の市場から法定通貨へ戻る資金の最後の段であり、償還の前にその資金が BTC を売っているなら。何で崩れるか = 償還が売買以外の理由(利回りの規制でトークン化国債へ移る、チェーン間の交換の調整)で起きるとき(検索の返答には 2026 年半ばの減少を利回りの規制で説明する記述があった。ページ未確認)。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = 暗号資産を売って USDT を法定通貨に戻す人。場面 = 大きな burn の前後。
- 反証: 大きな burn の後の BTCUSD の動きが、burn の無い期間と区別できないと測れたら違う(Saggu の解説はこの向きの出所の主張)。
- 段 3 の種類: (a)。
- 水準とその出所: 35 億ドル(出所の事例の値。ページ未確認)。入りの閾値は未定(W4 で測る前に決める)。
- 使うデータと遅れ: USDT の burn のトランザクション(チェーン上、経路は未確認)、USDT の供給の日次(DefiLlama、round1 で区分 A)。
- 約定の模型: 成行。

#### X2-B-62(升 P9-関心)

- 原文: 「Puell Multiple is defined as the ratio of the daily value of the issued coin in USD divided by 365 days moving average of the daily value of issued coins in USD.」「If Puell multiple rises, it indicates that price=Miner's revenue is increasing significantly compared to the cost they put in」「If the Puell multiple decreases, it indicates that price=Miner's revenue is decreasing significantly compared to the cost they put in」(ページ確認済み)
  - 訳: 「Puell Multiple は、発行された coin の日次の価値(USD)を、その 365 日の移動平均で割った比と定義される」「Puell Multiple が上がるとき、価格 = マイナーの収入が、投じた費用に比べて大きく増えていることを示す」「下がるとき、価格 = マイナーの収入が、投じた費用に比べて大きく減っていることを示す」。
  - 出所: https://userguide.cryptoquant.com/cryptoquant-metrics/network/puell-multiple
- 意図の地図: 入る条件 = Puell Multiple の水準(高い側・低い側)。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 値。向き = 高い → 売り圧(マイナーが売る誘因)、低い → 買い(マイナーが持ち続ける誘因)。読み取り役の返答は高い側を「>4」・低い側を「<0.5」と見出しに書いたが、その値がページの文にあるかは逐語で確かめていない。
- なぜ: 誰が損をしているか = 収入が平年より多いときにマイナーが売る玉の、買う側に立つ人(高い側)。なぜ続くか = マイナーの売る量が、平年に比べた収入の多さで変わるなら。何で崩れるか = マイナーの売りが市場の売りの中で小さくなる(ETF・企業の財務の流れに比べて)とき。半減期で発行量が半分になると、365 日平均との比が機械的に下がる(半減期の後の 1 年は分子と分母の基準が違う)。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = マイナーの売り。場面 = 値が極端な時。
- 反証: 値の水準で分けた後の BTCUSD の動きが、区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 365 日(定義の窓。ページ確認済み)。閾値の 4・0.5 はページの文で未確認。未定(W4 で測る前に決める)。
- 使うデータと遅れ: 日次の発行量(ブロック報酬 × ブロック数、チェーンから計算できる【推定】)× BTCUSD の日次。手数料を含むかは定義の文では「issued coin」(発行分)。日次、遅れは 1 日以内【推定】。
- 約定の模型: 成行。

#### X2-B-63(升 P9-関心)

- 原文: 「Periods when miner revenues are low and the hashrate remains high often point to potential market lows」「we might be near a price bottom」(CryptoQuant の記述として引用。ページ確認済み)
  - 訳: 「マイナーの収入が低く、ハッシュレートが高いままの期間は、しばしば市場の安値を指す」「価格の底に近いかもしれない」。
  - 出所: https://unchainedcrypto.com/bitcoin-miners-are-under-pressure-and-selling-coins-cryptoquant/ (2024-06-14)
- 意図の地図: 入る条件 = マイナーの収入(USD)が低く、ハッシュレートが高いまま(下がっていない)という 2 つの条件が同時に成り立つとき。出る条件 = 未定。保有中の判断 = ハッシュレートが下がり始めたか。強弱の付け方 = 未定。向き = 買い(出所の主張の向き)。
- なぜ: 誰が損をしているか = 採算が苦しいマイナーが売りを出し切る局面で、売り切った後の戻りの前に売る人。なぜ続くか = 苦しい局面のマイナーの売りが、価格の下げを一時的に押し広げるなら。何で崩れるか = ハッシュレートが高いままなのが、効率の良い新しい機械の導入によるもので、苦しさを表さないとき。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = 苦しい局面のマイナーの売りと、売りの後の買い戻し。場面 = 収入の低迷とハッシュレートの高止まりが重なる期間。
- 反証: 2 つの条件が重なる期間の後の BTCUSD の動きが、片方だけの期間と区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 原文に無い(出所の値 3,000 BTC・1,200 BTC は送金と OTC の事例の量で、この案の閾値ではない)。未定(W4 で測る前に決める)。
- 使うデータと遅れ: マイナーの日次の収入(発行分 + 手数料、チェーンから計算できる【推定】)、ハッシュレート(公開 API、round1 で区分 A)。日次。
- 約定の模型: 成行。

#### X2-B-64(升 P9-予告)

- 原文: 「Luxor Hashrate Forward market participants have been generally accurate at pricing future hashprice.」「Currently, hashrate forwards are trading in contango over the next six months」(ページ確認済み)。検索の返答には「In September 2024, both USD and BTC contracts were trading in backwardation.」(ページ未確認。https://hashrateindex.com/blog/weekly-hashrate-market-update-september-03-2024 の題で出た)
  - 訳: 「Luxor のハッシュレートの先渡しの市場の参加者は、将来のハッシュプライスを概ね正しく値付けしてきた」「今、ハッシュレートの先渡しは、先の 6 か月にわたって順ざや(先が高い)で取引されている」/「2024 年 9 月、USD 建てと BTC 建ての両方の契約が逆ざや(先が安い)で取引されていた」。
  - 出所: https://hashrateindex.com/blog/does-the-hashrate-forward-curve-predict-future-hashprice/ (Colin Harper・Ben Harper、2024-05-16)
- 意図の地図: 入る条件 = ハッシュレートの先渡しの曲線の形(順ざや・逆ざや)と、その変化。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 先と今の差の大きさ。向き = 未定(出所は曲線がハッシュプライスを予告することだけを書き、BTC の売買の向きを書いていない)。考えられる道: 逆ざや = 参加者が採算の悪化を見込む → マイナーの売り圧(P9-強制)の前触れ【仮定】。
- なぜ: 誰が損をしているか = マイナーとヘッジの相手が先渡しに載せた採算の見込みを、価格の側で後から知る人。なぜ続くか = マイナーが自分の採算の見込みに沿ってヘッジし、その見込みが売りの計画に先行するなら。何で崩れるか = 先渡しの市場が薄く、値付けが少数の参加者で決まるとき。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = マイナー(採算に沿った売り)。場面 = 曲線の形が変わった時。
- 反証: 曲線の形で分けた後の BTCUSD の動き(またはマイナーの取引所への送金)が、区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 6 か月(出所の時点の曲線の長さ)。未定(W4 で測る前に決める)。
- 使うデータと遅れ: Luxor のハッシュレートの先渡しの気配の履歴(Hashrate Index。鍵・課金が要るかは未確認。週次の記事にも値が載る)。CFTC の規制下のハッシュレートの先物(検索の返答の文。取引所と履歴は未確認)。
- 約定の模型: 成行。

#### X2-B-65(升 P9-予告)

- 原文: 「The average block time on the Bitcoin network has been 10.30 minutes since the last adjustment.」「The next Difficulty adjustment will occur during Friday night」、減少は「about 2.91%」(ページ確認済み)
  - 訳: 「ビットコインのネットワークの平均ブロック時間は、前回の調整から 10.30 分である」「次の難易度の調整は金曜の夜に起きる」、減少は「約 2.91%」。
  - 出所: https://bitcoinist.com/bitcoin-difficulty-set-for-another-3-drop-what-it/ (2026-05-02)
- 意図の地図: 入る条件 = 期(2016 ブロック)の途中の平均ブロック時間から見積もった次の調整の向きと大きさ(10 分より遅い = 下げの見積り = マイナーが抜けている)。出る条件 = 調整の実施(未定)。保有中の判断 = 見積りの更新。強弱の付け方 = 見積りの大きさ。向き = 未定(出所は「マイナーの退出」を書くが、売買の向きを書いていない)。
- なぜ: 誰が損をしているか = マイナーの退出(採算割れ)を、調整の実施や 30 日・60 日の移動平均の交差(X1-B-17)で後から知る人。なぜ続くか = 平均ブロック時間はブロックごとに更新され、移動平均より早く退出を映すなら。何で崩れるか = ブロック時間の揺らぎ(運)が大きく、期の前半の見積りが退出を映さないとき。電力網の要請による一時の停止(X2-B-71)も同じ形で見える。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = 退出するマイナーの売り(P9-強制)。場面 = 期の途中で見積りが大きく下げに振れた時。
- 反証: 見積りの向きで分けた後の BTCUSD の動きが、区別できないと測れたら違う。見積りの変化が、移動平均の交差より先に起きないと測れたら、「早い」の部分は違う。
- 段 3 の種類: (a)。
- 水準とその出所: 10 分(目標のブロック時間)、2016 ブロック(調整の期の長さ。プロトコルの規則)。10.30 分・2.91% は事例の値。入りの閾値は未定(W4 で測る前に決める)。
- 使うデータと遅れ: ブロックの時刻と高さ(公開のチェーンの履歴。round1 の区分 A のハッシュレートの経路と同じ系列から出せるかは未確認)。ブロックごと。
- 約定の模型: 成行。

#### X2-B-66(升 P9-移動)

- 原文: 「uptick in transfers from mining pools to crypto exchange Binance」が「over 3,000 BTC」に達した(CryptoQuant の記述として引用。Unchained、ページ確認済み)/「Huobi and Binance are the only exchanges in the sample that also operate mining pools.」(Coin Metrics の調査を伝える ForkLog、ページ確認済み)
  - 訳: 「マイニングプールから暗号資産の取引所 Binance への送金の増加」が「3,000 BTC 超」に達した / 「Huobi と Binance は、調査の標本のうち、マイニングプールも運営している唯一の取引所である」。
  - 出所: https://unchainedcrypto.com/bitcoin-miners-are-under-pressure-and-selling-coins-cryptoquant/ (2024-06-14)/ https://forklog.com/en/how-much-do-bitcoin-miners-move-the-market-part-ii/ (2021-03-04、Coin Metrics の Karim Helmi ほか)
  - 逆の出所の主張: ForkLog の記事は「The correlation between movements in Bitcoin's price and the inflows to exchanges is virtually non-existent」(ビットコインの価格の動きと取引所への流入の相関はほぼ無い)、「there is little reason to believe these market participants are driving Bitcoin's price decline」(これらの参加者が価格の下落を動かしていると考える理由はほとんど無い)と書く(ページ確認済み)。
- 意図の地図: 入る条件 = マイニングプールのアドレスから Binance への送金の量(プール別)の急増。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 送金の量。向き = 売り(Unchained の記事の向き)。
- なぜ: 誰が損をしているか = プールが Binance に入れた BTC が売られる前に、Binance(または BTCUSD を作る取引所)で買う側にいる人。なぜ続くか = プールを運営する取引所へ入金する流れが、その取引所での売りに直結するなら。何で崩れるか = 入金が売りでなく、担保・ヘッジ・プールの払い出しの内部の移動であるとき(Coin Metrics の出所の主張はこの側)。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = マイナー(プール経由)の売り。場面 = プールから Binance への送金が急増した時。
- 反証: 送金の急増の後の Binance の BTCUSDT(と BTCUSD)の動きが、急増の無い時と区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 3,000 BTC(出所の事例の値。閾値ではない)。未定(W4 で測る前に決める)。
- 使うデータと遅れ: プールのアドレス(コインベースの出力から特定できる【推定】)、Binance の入金アドレスのラベル(出所は未確認)、チェーンの送金。CryptoQuant の集計(鍵・課金が要るかは未確認)。
- 約定の模型: 成行。

#### X2-B-67(升 P9-約定)

- 原文: 「bitcoin miner over-the-counter selling has increased to its largest daily volume since March」(The Block、ページ確認済み。計り方の記述はページに無い)/「miner activity on over-the-counter (OTC) desks」が「1,200 BTC」(Unchained、ページ確認済み)
  - 訳: 「ビットコインのマイナーの店頭(OTC)での売りが、3 月以来で最大の日次の量に増えた」/「OTC の窓口でのマイナーの活動」が「1,200 BTC」。
  - 出所: https://www.theblock.co/post/301005/bitcoin-miner-otc-selling-reserves-low (2024-06-20)/ https://unchainedcrypto.com/bitcoin-miners-are-under-pressure-and-selling-coins-cryptoquant/
- 意図の地図: 入る条件 = マイナーから OTC の窓口のアドレスへの日次の送金の量の急増。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 量。向き = 未定(OTC の売りは板に直ちには出ない。窓口が板でヘッジ・処分するなら売り)【仮定】。
- なぜ: 誰が損をしているか = OTC の窓口がマイナーから買った BTC を板で処分するときに、買う側に立つ人。なぜ続くか = 窓口が在庫を長く持たず、数時間〜数日で板に流すなら。何で崩れるか = 窓口が買い手(ETF・企業の財務)と直接つなぎ、板に出さないとき。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = OTC の窓口(マイナーからの在庫の処分)。場面 = OTC への送金の急増の後。
- 反証: 急増の後の BTCUSD の動きが、急増の無い時と区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 1,200 BTC(出所の事例の値。閾値ではない)。未定(W4 で測る前に決める)。
- 使うデータと遅れ: OTC の窓口のアドレスのラベル(CryptoQuant の集計。ラベルの出所・鍵・課金は未確認)、マイナーのアドレス。日次【推定】。
- 約定の模型: 成行。

#### X2-B-68(升 P9-約定)

- 原文: 「Some Bitcoin miners now sell their Bitcoin production each day as part of their treasury management approach. Companies including CleanSpark and Iris Energy also sell a majority of their mined BTC.」(検索の返答の文、ページ未確認。検索 `bitcoin miners sell daily production programmatic selling schedule TWAP OTC desk miner treasury management` の結果。どのページの文かは返答に示されていない。候補 https://www.letsdatascience.com/news/bitcoin-miners-accelerate-selling-treasury-reserves-643f5bb0 は開いていない)
  - 訳: 「一部のビットコインのマイナーは、財務の運営のやり方として、生産したビットコインを毎日売るようになった。CleanSpark や Iris Energy などの会社も、掘った BTC の大半を売る」。
- 意図の地図: 入る条件 = 毎日売る方針の会社の日次の生産量の変化(ハッシュレートの増減・電力網の停止・難易度の調整)。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 生産量の変化の大きさ。向き = 生産量が減る → 日々の売りの流れが減る(買い)/ 増える → 売り【仮定】。
- なぜ: 誰が損をしているか = 日々のマイナーの売りの流れの量の変化を見ずに、その流れに当たる側の人。なぜ続くか = 方針が「生産分を毎日売る」で固定されているなら、売りの量は生産量で決まる。何で崩れるか = 方針が変わる(保有に切り替える。D1-B-23)とき、または OTC で売り、板に出ないとき。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = 生産分を毎日売るマイナー。場面 = 生産量が大きく変わった期間(半減期の後、電力網の停止)。
- 反証: 生産量の変化で分けた後の BTCUSD の動きが、区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 原文に無い。未定(W4 で測る前に決める)。
- 使うデータと遅れ: 上場マイナーの月次の生産報告(round1 の D1-B-23 と同じ系列)、方針の開示、プール別のブロック数(日次)。遅れは未確認。
- 約定の模型: 成行。

#### X2-B-69(升 P9-持ち高)

- 原文: 「MARA pledged 18,750 BTC as collateral, valued at approximately $1.2 billion at the time.」「Coinbase Credit supplied $450 million of the total, while Two Prime Lending contributed another $300 million.」、融資は「a roughly 50% loan-to-value ratio」、「a prolonged downturn could force MARA to post additional collateral」、最悪の場合「see lenders move to liquidate part of its pledged Bitcoin」(ページ確認済み)
  - 訳: 「MARA は 18,750 BTC を担保に差し入れた。当時の価値は約 12 億ドル」「総額のうち 4.5 億ドルを Coinbase Credit が、3 億ドルを Two Prime Lending が出した」、融資は「おおよそ 50% の担保掛け目(融資額 ÷ 担保の価値)」、「長い下げは MARA に追加の担保を差し入れさせうる」、最悪の場合「貸し手が差し入れられたビットコインの一部を清算に動く」。
  - 出所: https://en.cryptonomist.ch/2026/08/10/crypto-collateralized-loan-marathon-digital/ (2026-08-10)
- 意図の地図: 入る条件 = 上場マイナーの開示から出す「担保に入った BTC の量と掛け目」から計算した、追加の担保・清算が起きる BTCUSD の水準に価格が近づいたとき。出る条件 = 未定。保有中の判断 = 追加の担保の開示の有無。強弱の付け方 = その水準に当たる担保の量。向き = 水準の手前・割れで売り(清算の売りの前)【仮定】、清算の後の戻りは未定。
- なぜ: 誰が損をしているか = 担保の清算の売りが出る水準を知らずに、その水準の近くで買う人。なぜ続くか = 担保の量と掛け目が開示され、清算の水準が計算でき、清算が板に出るなら。何で崩れるか = 掛け目の条件(追加の担保の猶予・現金での補填)が開示より緩い、マイナーが他の資産で補填する、清算が OTC で済まされるとき。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = 貸し手(担保の清算)・マイナー(追加の担保を作るための売り)。場面 = 価格が計算した水準に近い期間。
- 反証: 計算した水準の近くでの BTCUSD の動きが、他の同じ距離の水準と区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 掛け目 約 50%(出所の値)、18,750 BTC・7.5 億ドル(出所の値)。清算が起きる掛け目の閾値は原文に無い。未定(W4 で測る前に決める)。
- 使うデータと遅れ: 上場マイナーの開示(四半期の報告・臨時の開示。公表の遅れは未確認)。
- 約定の模型: 成行。

#### X2-B-70(升 P9-強制)

- 原文: 「Core Scientific and Bitfarms had among the most significant bitcoin and machine collateralized debt positions. The plummeting bitcoin and machine prices forced these companies to sell bitcoin to pay off these loans.」「their bitcoin collateralized credit facility with Galaxy Digital became problematic, as the falling bitcoin price forced them to sell bitcoin to repay the loan」「we have now been through the worst bitcoin selling from the public miners」(K33、ページ確認済み)
  - 訳: 「Core Scientific と Bitfarms は、ビットコインと機械を担保にした借入の残高が最も大きい部類だった。ビットコインと機械の価格の急落が、これらの会社に借入を返すためにビットコインを売らせた」「Galaxy Digital とのビットコイン担保の信用枠が問題になり、ビットコインの価格の下落が、借入を返すためのビットコインの売りを強いた」「上場マイナーによる最悪のビットコインの売りは、もう通り過ぎた」。
  - 出所: https://k33.com/research/archive/articles/the-public-miners-dumped-their-bitcoin-holdings-in-june (2022-07-13)
- 意図の地図: 入る条件 = BTC と機械の価格がともに大きく下げ、担保付きの借入を持つマイナーの売りの開示(月次の生産報告での売却量が生産量を大きく超える)が出たとき。出る条件 = 売りの一巡(出所は「最悪は通り過ぎた」と書く。判定の規則は未定)。保有中の判断 = 次の月次の報告。強弱の付け方 = 売却量 ÷ 生産量。向き = 未定(売りの最中は売り、一巡の後は戻りという道があるが、出所は一巡の判定を書いていない)。
- なぜ: 誰が損をしているか = 価格に関わらず売らなければならないマイナー(返済の強制)。なぜ続くか = 借入の契約が価格の下げで返済・担保の積み増しを強いるなら。何で崩れるか = マイナーの借入が担保付きでなくなる、または株・転換社債で資金を作るとき。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = 担保付きの借入を持つマイナー。場面 = BTC と機械の価格がともに下げた局面。
- 反証: 売却量 ÷ 生産量の大きい月の後の BTCUSD の動きが、そうでない月と区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 6 月の売却 約 14,600 BTC(月次の生産の約 400%。出所の事例の値)。閾値は未定(W4 で測る前に決める)。
- 使うデータと遅れ: 上場マイナーの月次の生産報告(売却量・生産量。round1 の D1-B-23 と同じ系列)、借入の開示。月次で、公表は翌月の上旬【推定】。
- 約定の模型: 成行。

#### X2-B-71(升 P9-強制)

- 原文: 「Bitcoin's network hashrate declined by approximately 25% over the past few days amid curtailment requests from the Texas grid regulator following a recent cold snap.」「ERCOT's warning was followed by official conservation appeals on Sunday, Monday and Tuesday」(The Block、ページ確認済み。価格・マイナーの売りの記述はページに無い、と読み取り役が返した)
  - 訳: 「最近の寒波の後、テキサスの電力網の運営者からの出力削減の要請のなかで、ビットコインのネットワークのハッシュレートは数日で約 25% 下がった」「ERCOT の警告の後、日・月・火曜に公式の節電の要請が出た」。
  - 出所: https://www.theblock.co/post/273159/bitcoin-mining-hashrate-falls-texas-curtailment (2024-01-17)
- 意図の地図: 入る条件 = ハッシュレートの急な低下が、ERCOT の節電の要請・天候の警告と同じ時期に起きたとき(電力網の原因の低下)。出る条件 = 要請の解除(未定)。保有中の判断 = 未定。強弱の付け方 = 未定。向き = 未定。道は 2 つ【仮定】: (i) 電力網の原因の低下は採算割れの売り(D1-B-28・X1-B-17)を意味しないので、それらの売り・降伏の合図をこの期間だけ外す。(ii) 停止の間はマイナーの生産が減り、生産分を毎日売る会社(X2-B-68)の売りの流れも減る。
- なぜ: 誰が損をしているか = ハッシュレートの低下を採算割れの売りと読んで売る人(電力網の原因のとき)。なぜ続くか = マイナーが需要応答の契約で電力を戻す対価を得ており(検索の返答: Riot は 2023-08 に 3,170 万ドルの電力の対価。ページ未確認)、停止が採算の悪化でないなら。何で崩れるか = 電力網の要請と採算割れが同じ時期に重なるとき。
- 期待する向きと場面: 効く項 = BTCUSD。注文の主 = ハッシュレートの合図で売買する人と、生産量に沿って売るマイナー。場面 = 寒波・熱波の ERCOT の要請の期間。
- 反証: 電力網の原因の低下の後の BTCUSD の動きが、採算割れと見られる低下の後と区別できないと測れたら違う。
- 段 3 の種類: (a)。
- 水準とその出所: 約 25%、600 → 450 EH/s(出所の事例の値)。未定(W4 で測る前に決める)。
- 使うデータと遅れ: ハッシュレート(公開 API、round1 で区分 A)、ERCOT の節電の要請・警告の履歴(ERCOT の公開の告知。経路は未確認)、天候の警告。遅れは未確認。
- 約定の模型: 成行。

### 升ごとの案の数

| 升 | 案の数 | 番号 |
|---|---|---|
| P8-関心 | 2 | X2-B-51、X2-B-52 |
| P8-予告 | 1 | X2-B-53 |
| P8-移動 | 1 | X2-B-54 |
| P8-約定 | 2 | X2-B-55、X2-B-56 |
| P8-持ち高 | 3 | X2-B-57、X2-B-58、X2-B-59 |
| P8-強制 | 2 | X2-B-60、X2-B-61 |
| P9-関心 | 2 | X2-B-62、X2-B-63 |
| P9-予告 | 2 | X2-B-64、X2-B-65 |
| P9-移動 | 1 | X2-B-66 |
| P9-約定 | 2 | X2-B-67、X2-B-68 |
| P9-持ち高 | 1 | X2-B-69 |
| P9-強制 | 2 | X2-B-70、X2-B-71 |
| 計 | 21 | X2-B-51〜X2-B-71 |

検索の回数: WebSearch 27 回(うち `site:x.com` 2 回。どちらも x.com の投稿の URL は 0 件で、fxtwitter は叩いていない)。WebFetch 26 回(うち 301 の転送 2、404 1、503 1)。

### 持ち越し

- 担当の 12 升は締め切りの前に書き終えた。升の持ち越しは無い。
- ページ未確認の引用 3 件の取り直し: X2-B-61(san-1510.aid.brainsum.com、HTTP 503)、X2-B-64 の 2024-09 の逆ざやの文(hashrateindex.com の週次の記事、開いていない)、X2-B-68(検索の返答の文、どのページか不明)。X2-B-71 の Riot の電力の対価の文(decrypt.co、開いていない)。
- 開いていない候補: TradingView「50.5M USDT Transferred to Binance Prior to Bitcoin Pump」(X1-B-10 と同じ機構と見て開いていない)、CoinDesk 2022-05-12 の USDT の 0.97 ドルの記事、Glassnode のマイナーの保有の変化の図。
- X の投稿: `site:x.com` の 2 回で投稿の URL が出なかった。語を変えた発見の検索(日本語の語、利用者名を絞る語)は打っていない。

### 迷った点

1. WebFetch の返答は、ページを読んだ読み取り役の返答であり、引用符の中の文がページの文と 1 字ずつ同じかは照合していない。「ページ確認済み」はこの意味。X2-B-62 の閾値(4・0.5)は読み取り役の見出しにだけあり、引用の文の中には無かったので、水準に入れずに「ページの文で未確認」と書いた。
2. 在庫との重なりは、組 B の round1(DERIVATION_B.md の P8・P9 の行と IDEAS_B.md の見出し)だけに当てた。X2-B-55(USD と USDT の取引所の差)は、組 A・D(取引所の大口・国内と海外の差を埋める人)の round1 の案や `docs/STRATEGY_IDEAS.md` に同じ機構があるかを確かめていない。
3. 升への置き方: 検索の結果が別の升の機構だったときは、機構の升に案を置き、升の表にその旨を書いた(Saggu の論文は P8-関心 の検索で出て P8-移動 に置いた、USDT/人民元 は P8-強制 の検索で出て P8-約定 に置いた、Santiment の大口の保有は P8-移動 の検索で出て P8-持ち高 に置いた、Unchained の記事は P9-移動 の検索で出て P9-関心 にも使った)。
4. 案にしなかった機構が 2 つある。(i) 長期保有者のカバードコールとディーラーのヘッジが上値を抑える(検索の返答、マイナーに限らない記述)。参加者が P7(オプションのディーラー)の升に当たると考え、P9 の案にしなかった。P7 は担当外。(ii) Hashrate Index の「ASIC のカバードコール」(2022-04-18、ページ確認済み)は、BTC の価格と ASIC の価格の遅れを使うマイナーの資産運用の記述で、BTCUSD・USDJPY・円の上乗せ・経費のどの項への道も書けなかった。捨てたのではなく、項への道が書けないことをここに残す。
5. 時刻: 升ごとではなく束で検索を打ったので、書き始めは束ごとに同じ値。P8 の束は検索の直前の `date -u`(22:38:18Z)。P9 の束は、検索の直前に `date -u` を打たなかったため、前後に打った 2 つの値(22:38:18Z と 22:40:07Z)の間としか言えない。書き終わり(22:46:59Z)は、この文書を書き終えた後に打った `date -u`。升ごとの時刻は取れていない。
6. X2-B-55・X2-B-56・X2-B-60・X2-B-64・X2-B-65・X2-B-71 は、出所が「何を読むか」は書くが売買の向きを書いていないので、意図の地図の向きを「未定」とし、考えられる道を【仮定】の印で書いた。


---

# 作業者 C: 組 C の 7 升と組 B の P10

## 案の供給 第 3 周 作業者 C の成果物(升 P12〜P15 の 7 升 + 組 B の P10 の 6 升)

書き始め: 2026-10-03T22:38:23Z、書き終わり: 2026-10-03T22:48:39Z(どちらも `date -u +%FT%TZ`)。締め切り UTC 23:55。

### 着手前の表(CLAUDE.md §0.1)

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 外の記述(論文・note・X・ブログ・取引所の資料)から、round1 で拾えていない機構を案にする | L-528「**ありとあらゆる多角的な視点から戦略立案をやれと言ってもやってくれなかったこと**」/ L-019「**私が思いつけないあなたが見つけた戦略を、片っ端から検証し**」 |
| 升(誰の・どの段階の跡か)から検索語を作り、オーナーの挙げた例の語をそのまま探さない | L-531「**この私が挙げた例をそのまま探しまーすなんて怠惰で陳腐な追加案は許しません**」 |
| 出所の URL と逐語を付け、英語の逐語に日本語の訳を付ける | L-126「**日本人に読めない英語の出力してなんの意味があるの？2度と出すな**」/ L-049「**この文章の意味が何一つわからないので全て説明してください**」 |
| 担当を P12-関心・P12-強制・P13-移動・P13-約定・P14-移動・P14-約定・P15-持ち高・P10 の 6 升に限る | **(該当語なし)** — リードの委任文(`SUPPLY_HANDOFF.md` §2-3、round2/README.md の対象の升)の語 |
| 升ごとに検索を 2 回以上にする | **(該当語なし)** — リードの委任文の語 |
| 締め切り(UTC 23:55)で止め、残りを持ち越す | L-451「**なぜあいもかわらず無限の無意味な作業を続けてるんですか？**」(I-013) |
| 案を評価しない・数を決めない | L-019「**過去の検証結果を軸にした優先度など何の意味もない**」/(数を決めない: A-12「**もしこの h が MDE を出すために用意したものなら、本末転倒です**」L-046) |

右が空の 2 行は、リードの委任文の範囲と手順の語。成果物の中身をオーナーの語から外さないので、問いにせずに進めた(round2/README.md の表と同じ扱い)。

### 升の表

時刻の注: 検索は升をまたいで並べて打ったため、升ごとの書き始めと書き終わりを別々に取っていない。検索の全体は 2026-10-03T22:38:23Z〜22:43:26Z(`date -u` の出力。途中の確かめ: 22:40:40Z・22:42:43Z)、このファイルの書き込みは 22:43:26Z から。下の表の時刻はこの 2 つの区間を写したもの(迷った点 1)。

| 升 | 書き始め | 書き終わり | 検索語と結果 | 出た案の番号 | 在庫との重なり |
|---|---|---|---|---|---|
| P12-関心 | 2026-10-03T22:38:23Z | 2026-10-03T22:43:26Z | (1)「exchange risk limit tier open interest cap reached perpetual funding trader strategy "open interest limit"」→ Hyperliquid の `perpsAtOpenInterestCap`(建玉の上限に達した銘柄の一覧を返す経路)の文書(chainstack・goldrush)、Synthetix の建玉上限の文書、trade.xyz の建玉上限(WebFetch で 404)。見つかった。(2)「exchange market maker inventory own book trading against customers crypto exchange proprietary desk liquidation flow analysis」→ 取引所内のマーケットメイク部門の是非の記事(theblock)、在庫リスクの解説(liquidmercury)。検索の返答にあった「market makers ended up stuffed with spot inventory and unhedged」の文は liquidmercury のページで見つからなかった(WebFetch の返答「cannot find any sentence」)。取引所自身の売買の判断の跡を売買に使う記述は、この検索で見つからなかった | X2-C-01 | round1 の P12-関心 は案なし。D1-C-11(保険基金の増減)とは段階も跡も違う |
| P12-強制 | 2026-10-03T22:38:23Z | 2026-10-03T22:43:26Z | (1)「auto-deleveraging ADL event bitcoin price rebound after ADL trading insight」→ ADL の解説・arXiv の ADL の論文(2512.01112)・Substack の解説(freeportlogbook)。見つかった。(2)「liquidation engine backstop liquidity provider vault HLP Hyperliquid liquidation profits strategy」→ HLP(取引所の金庫が清算の受け皿になる)の解説(buildix・coingecko・onekey ほか)。見つかった。(3)「market makers auto-deleveraged short hedges closed left unhedged long spot October 10 2025 forced selling cascade」→ cryptoslate・cointelegraph(WebFetch で 404)・BitMEX のブログ(L-570 により開かない)。見つかった。(4)「Binance ADL indicator lights queue position traders risk warning exchange displays deleverage ranking」→ ADL の順番の表示(5 段の灯)の解説。この検索の結果は案にせず、X2-C-02 の背景にだけ使った | X2-C-02・X2-C-03・X2-C-04 | D1-C-11(保険基金の増減)・O-3c(強制決済フローの観測)に近い。違う点: 清算そのものでなく、清算の後ろの段(ADL で勝っている側の建玉が閉じられること・HLP が引き取った建玉)を見る |
| P13-移動 | 2026-10-03T22:38:23Z | 2026-10-03T22:43:26Z | (1)「Polymarket whale new wallet deposit large bet before event insider tracking bot USDC bridged」→ Bitquery の内部者の検出の文書、追跡の道具(apify ほか)。見つかった。(2)「Polymarket open interest surge crypto market sentiment indicator USDC inflows Polygon bridge bitcoin price correlation analysis」→ Polymarket の建玉の増加と USDC・Polygon への流入の報道(financemagnates・cryptometer ほか)。流入を売買に使う記述は、この検索で見つからなかった | X2-C-05 | D1-C-14(担保の総額の増減)に近い。違う点: 総額でなく、新しい財布への USDC の入金という個別の跡と、賭けた市場・時刻の組を見る |
| P13-約定 | 2026-10-03T22:38:23Z | 2026-10-03T22:43:26Z | (1)「Polymarket bitcoin "up or down" 15 minute market arbitrage Binance price latency bot」→ Polymarket の 5 分・15 分の上下の市場が Binance に遅れるとする記事(chudi.dev・indiehackers(WebFetch で 403)・beincrypto ほか)。見つかった。(2)「Polymarket bitcoin price strike markets implied probability compared to options implied distribution Deribit mispricing」→ Polymarket と option の含む確率を比べた論文(repec の 2606.19517、fc26 の論文)・Substack(podshopguy)。見つかった。(3)「Polymarket market maker hedge delta on Binance perpetual binary option hedging flow bitcoin 15 minute expiry strike pinning」→ 一般の解説のみ。ヘッジの流れの記述は、この検索で見つからなかった(benjamincup の WebFetch でも該当の文なし) | X2-C-06・X2-C-07・X2-C-08 | D1-C-15(約定の向きの偏り)とは跡が違う(価格と option の差・遅れ)。X2-C-08 は #28(Binance の先行を追う)と同じ形。違う点は案の欄に書いた |
| P14-移動 | 2026-10-03T22:38:23Z | 2026-10-03T22:43:26Z | (1)「ビットコイン 積立 購入日 毎月 給料日 アノマリー 国内 取引所 買い 集中」→ 積立の解説(diamond・monex・bitbank ほか)。給料日の集中を売買に使う記述は、この検索で見つからなかった。(2)「bitFlyer かんたん積立 購入タイミング 毎日 何時 購入 実行」→ bitFlyer のかんたん積立のページ(WebFetch で 403)。検索の返答に頻度と価格の参照の文。(3)「Japan retail crypto traders contrarian buying dips yen premium bitcoin Japanese exchanges discount during selloff」→ 円の上乗せの報道(CoinDesk の転載の yahoo・fxstreet ほか)。見つかった | X2-C-09・X2-C-10 | D1-C-20(JVCEA の月次の預託金)とは跡が違う(定時の積立・円の変動への退避)。X2-C-10 は升 P14 と P15 にまたがる(迷った点 3) |
| P14-約定 | 2026-10-03T22:38:23Z | 2026-10-03T22:43:26Z | (1)「仮想通貨 年末 損出し 確定申告 個人 売り 12月 日本 税金 雑所得 ビットコイン 売り圧」→ coinpost の税理士の寄稿(2024-12-23)・米国の年末の売り圧の記事(coinpost 2020-10-19)・国税庁の資料。見つかった。(2)「bitFlyer Lightning 板 キリ番 指値 集中 個人 逆張り 厚い板 BTC 円 節目」→ bitFlyer Lightning の一般の説明のみ。売買の記述は、この検索で見つからなかった | X2-C-11 | D1-C-21(約定の向きの偏り)に近い。違う点: 偏りの起きる時期を税の暦(年末)から決める |
| P15-持ち高 | 2026-10-03T22:38:23Z | 2026-10-03T22:43:26Z | (1)「Japan foreign reserves US Treasury holdings deposits intervention capacity "war chest" yen traders watch reserve composition」→ 外貨準備の内訳と介入の余力の記事(itiger 2026-09-07 ほか)。見つかった。(2)「日銀 当座預金 見通し 財政等要因 介入 推計 実績 前日 為替介入 観測 短資会社」→ 日銀の当座預金の見通しと短資会社の予想の差から介入額を推計する記事(newsweekjapan・sbbit ほか)。これは約定(介入の実行)の跡なので P15-約定の升に当たり、案にしなかった(迷った点 4)。(3)「Federal Reserve custody holdings for foreign official accounts weekly H.4.1 decline Japan selling Treasuries intervention signal」→ 米連銀の海外公的機関の預かり残高(毎週木曜)と介入の資金の記事(itiger 05-09・marctomarket・bnnbloomberg(本文が取れず))。見つかった | X2-C-12・X2-C-13 | round1 の P15-持ち高は案なし |
| P10-関心 | 2026-10-03T22:38:23Z | 2026-10-03T22:43:26Z | (1)「state bitcoin reserve bill legislature vote tracker bitcoin price reaction traders watch state-level SBR bills」→ 米国の州の BTC 準備法案の採決の記事(decrypt ほか)。見つかった。(2)「押収 暗号資産 国庫 売却 日本 警察 没収 ビットコイン 換金 方法 取引所」→ ロシア・ブラジルの押収 BTC の換金の報道(bitbank・coinpost)、法制審議会の資料。日本の押収 BTC の売却の方法の記述は、この検索で見つからなかった。(3)(P10-約定の検索で出た)「German government bitcoin sale Flow Traders ...」→ forklog の専門家の説明(緊急売却の規定) | X2-B-81・X2-B-82 | D1-B-30(連邦の方針の発表)に近い。違う点は案の欄 |
| P10-予告 | 2026-10-03T22:38:23Z | 2026-10-03T22:43:26Z | (1)「judge approves government sale 69,370 bitcoin Silk Road Battle Born ruling cleared to sell forfeiture order bitcoin」→ 裁判所が没収の BTC の売却を認めた記事(decrypt 2025-01-09 ほか)。見つかった。(2)「US Marshals bitcoin auction notice bidders registration date announced in advance seized bitcoin auction price effect」→ US Marshals の競売の登録の期限と日程の記事(thenextweb 2018-10-19 ほか)。見つかった。(3)「UK government 61,000 bitcoin seized Jian Wen Zhimin Qian sell decision Treasury budget holdings overhang analysts」→ 英国政府の売却の計画・保管と換金の枠組みの入札・被害者の異議(cointelegraph 2025-07-21 ほか)。見つかった | X2-B-83・X2-B-84・X2-B-85 | D1-B-31・D1-B-32(管財人の返済期限)・D1-B-37(破産の裁判所の承認)に近い。違う点は案の欄 |
| P10-移動 | 2026-10-03T22:38:23Z | 2026-10-03T22:43:26Z | (1)「Bhutan government Druk Holding bitcoin transfers to Binance sell mined bitcoin Arkham pattern」→ ブータン政府の Binance 宛ての送金の報道(theblock 複数)。見つかった。(2)「German government bitcoin sale Flow Traders Bitstamp Kraken how sold OTC market maker execution BKA 50,000 BTC」→ ドイツ政府の送金先(取引所・マーケットメイカー・OTC)の報道(theblock・forklog)。見つかった | X2-B-86・X2-B-87 | D1-B-33・D1-B-34・X1-B-18(政府の財布から取引所宛ての送金)に近い。違う点は案の欄 |
| P10-約定 | 2026-10-03T22:38:23Z | 2026-10-03T22:43:26Z | (1) 上の P10-移動 の検索 (2) と同じ語 → 送金先の種類の報道。売却の約定の時刻の記録は、この検索で見つからなかった。(2)「Mt. Gox creditors received bitcoin via Kraken did not sell held analysis on-chain creditor behavior distribution sell pressure smaller than feared」→ Mt. Gox の管財人が日本の取引所 BitPoint で売ったとする記事(theblock 2019-02-05)ほか。見つかった | X2-B-88 | round1 の P10-約定は案なし |
| P10-持ち高 | 2026-10-03T22:38:23Z | 2026-10-03T22:43:26Z | (1)「El Salvador buys one bitcoin every day government purchases wallet tracker Bukele daily buy」→ エルサルバドル政府の毎日 1 BTC の購入の報道(cointelegraph 2024-08-23 ほか。IMF は購入していないとする記事 decrypt も出た)。見つかった。(2)「UK government 61,000 bitcoin seized ...」(P10-予告 の (3) と同じ)→ 英国政府の保有と売却の計画。保有量の変化を売買に使う記述は、この検索で見つからなかった | X2-B-89 | D1-B-35・D1-B-36(売る側の保有量)に近い。違う点: 買う側の政府の保有の増え方 |
| P10-強制 | 2026-10-03T22:38:23Z | 2026-10-03T22:43:26Z | (1)「Mt. Gox creditors received bitcoin via Kraken ...」(P10-約定 の (2) と同じ)→ 配布を受けた債権者が売ったかを、取引所の売買の差(CVD)と取引所からの出金で読む記事(cointelegraph 2024-07-30 ほか)。見つかった。(2)「FTX bankruptcy creditors repaid in cash not crypto distribution reinvest into bitcoin buying pressure stablecoin payouts」→ FTX の債権者への返済が現金(ドル)である記事(nysscpa 2024-05-08 ほか)。見つかった | X2-B-90・X2-B-91 | X1-B-19(破産の財団の清算を売り圧として読む)・D1-B-37 に近い。違う点は案の欄 |

### 案

#### X2-C-01(升 P12-関心)

- 原文: 「The response is an array of perpetual contract symbols that have reached their open interest limit」(訳: 応答は、建玉の上限に達した無期限先物の銘柄の配列である)/「Contracts at cap cannot accept new positions in the dominant direction」(訳: 上限にある銘柄は、優勢な向きの新しい建玉を受け付けない)/「Existing positions can still be closed or reduced.」(訳: 既存の建玉は閉じる・減らすことはできる)/「Protects against excessive concentration risk and market manipulation.」(訳: 過度の集中のリスクと相場操縦から守る)。出所: https://docs.chainstack.com/reference/hyperliquid-info-perps-at-open-interest-cap.md (ページ確認済み。Hyperliquid の info の経路 `perpsAtOpenInterestCap` の説明)。あわせて検索の返答の文(Synthetix の文書): 「While an asset has reached its open-interest cap, orders that would increase aggregate open interest are rejected.」(訳: 銘柄が建玉の上限に達している間は、総建玉を増やす注文は拒否される。ページ未確認。経路 WebSearch、出所の URL https://docs.synthetix.io/trading/oi-limits)。
- 意図の地図: 入る条件 = 取引所が BTC の無期限先物を「建玉の上限に達した」一覧に入れた時点(取引所が集中を危ぶむ状態に入った跡)。出る条件 = 一覧から外れた時点、または未定。保有中の判断 = 未定。強弱の付け方 = 上限に達している時間の長さ・優勢な向き(未定)。向き = 未定(優勢な向きの新規が止まるので、その向きの流れがその取引所で止まる、と読むか、上限に達するほど片寄った、と読むかは未定)。
- なぜ: 誰が損をしているか = 優勢な向きに新しく建てたい人が、その取引所で建てられず、他の取引所へ移るか待つ(仮定)。なぜ続くか = 上限は取引所の守りの規則で、片寄りが大きい局面ほど掛かる(出所の主張: 集中と相場操縦から守る)。何で崩れるか = 上限が BTC のような大きい銘柄にほとんど掛からない、または他の取引所が流れをすぐ吸収する。
- 期待する向きと場面: 場面 = 取引所が建玉の上限を掛けている間。効く項 = BTCUSD(海外の無期限先物の流れの片寄り)。向きは未定。
- 反証: 上限に達した時点の前後で、BTCUSD の動きと他の取引所の建玉の増え方に、上限に達していない時点との違いが無い。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ。
- 水準とその出所: 未定(W4 で測る前に決める)。原文に値は無い。
- 使うデータと遅れ: Hyperliquid の `perpsAtOpenInterestCap`(今の状態を返す経路。過去の履歴が取れるかは未確認。取れなければ区分 C = 今日から記録)。遅れは未確認。
- 約定の模型: 未定(成行か指値かは W4 で決める)。

#### X2-C-02(升 P12-強制)

- 原文: 「The system, trying to restore solvency, ADL's you: it forcibly closes your long at or around the bankruptcy/mark price of the losing shorts.」(訳: 仕組みは支払い能力を戻そうとして、あなたを ADL する。負けている売りの破産価格・目印価格の付近で、あなたの買い建てを強制的に閉じる)/「Suddenly you're just short BTC somewhere else, right as the market is ripping, and you may have to chase a painful re-hedge.」(訳: 突然、あなたは別の場所で BTC を売り建てているだけになる。相場が急騰しているまさにその時に。そして痛いヘッジのやり直しを追いかけなければならないかもしれない)。出所: https://freeportlogbook.substack.com/p/auto-deleveraging (ページ確認済み)。あわせて「A short futures leg intended to offset spot or altcoin exposure was partially or fully closed by the venue, turning an intended hedge into realized P&L and leaving residual risk unprotected.」(訳: 現物やアルトコインの持ち高を打ち消すための先物の売りの脚が、取引所によって一部または全部閉じられ、意図したヘッジが実現損益に変わり、残りのリスクが守られないまま残った)。出所: https://cryptoslate.com/how-150-billion-was-liquidated-from-crypto-market-in-2025-driving-bitcoin-crash/ (ページ確認済み)。
- 意図の地図: 入る条件 = ある取引所で ADL が起きた時点(ADL の発生の跡の取り方は未定)。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = ADL で閉じられた建玉の量(未定)。向き = ADL が起きた向きと同じ向き(出所の主張: 閉じられた側が、急な動きの最中に、別の場所でヘッジをやり直す。買いを閉じられた人は別の場所で売りが残り、相場の上げの中で買い戻す)。
- なぜ: 誰が損をしているか = ADL で片方の脚を閉じられた、ヘッジを組んでいた人(マーケットメイカー・ベーシスの裁定をする人)。急な動きの中でヘッジをやり直すので、悪い価格で約定する。なぜ続くか = ADL は清算と保険基金で足りないときの最後の手段で、急変の局面で順番の上位(利益と倍率の大きい人)から閉じる規則が各取引所にある(検索の返答: Binance・Bybit・OKX・Hyperliquid などが何らかの ADL を使う。ページ未確認)。何で崩れるか = ヘッジのやり直しが ADL と同じ瞬間に済む、またはヘッジの脚が同じ取引所にあり、両脚が同時に閉じる。
- 期待する向きと場面: 場面 = 清算が連鎖し、ADL が起きている数分〜数十分。効く項 = BTCUSD(海外の取引所でのヘッジのやり直しの流れ)。向き = ADL が起きた時点の相場の動きと同じ向き。
- 反証: ADL の発生の直後に、BTCUSD の動きの続き方が、同じ大きさの清算で ADL が起きなかった時点と違わない。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ。
- 水準とその出所: 未定(W4 で測る前に決める)。
- 使うデータと遅れ: ADL の発生の記録(Hyperliquid の約定の記録に ADL の印があるか、取引所ごとの公開の有無は未確認)。遅れは未確認。
- 約定の模型: 成行(急変の中で追う形のため。決めるのは W4)。

#### X2-C-03(升 P12-強制)

- 原文: 「Market makers that might have stepped in at narrower spreads now faced uncertain hedge execution and the prospect of involuntary reductions.」(訳: より狭い値幅で入ったかもしれないマーケットメイカーは、ヘッジの約定が不確かになり、意図しない縮小の見込みに直面した)/「many cut back on quoting size or moved wider, further reducing visible liquidity and leaving liquidation engines to work with thinner books.」(訳: 多くは提示する量を減らすか値幅を広げ、見える流動性をさらに減らし、清算の仕組みはより薄い板で動くことになった)。出所: https://cryptoslate.com/how-150-billion-was-liquidated-from-crypto-market-in-2025-driving-bitcoin-crash/ (ページ確認済み)。
- 意図の地図: 入る条件 = ADL が起きた後の時間帯(長さは未定)。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 未定。この案は売買の向きを決める案ではなく、ADL の後に板が薄くなる場面を、他の案の約定の費用と止めの規則の場面の変数として使う。
- なぜ: 誰が損をしているか = 薄い板で成行を出す人(清算される人を含む)。なぜ続くか = 出所の主張では、ADL でヘッジを閉じられうるという見込みが、マーケットメイカーに提示の量を減らさせる。ADL の規則がある限り、その見込みは消えない。何で崩れるか = マーケットメイカーが ADL の順番の下位に留まる工夫(倍率を下げるなど)をして、提示を減らさなくなる。
- 期待する向きと場面: 場面 = ADL の後。効く項 = 経費(板の薄さ)と BTCUSD(薄い板での動きの大きさ)。向きは無し(場面の変数)。
- 反証: ADL の後の時間帯で、海外の取引所の板の厚さ・値幅が、ADL の無い同じ大きさの急変の後と違わない。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ。bitFlyer の板にも同じ時間帯に薄さが出るかは、(b) の問いとして残る。
- 水準とその出所: 未定(W4 で測る前に決める)。
- 使うデータと遅れ: ADL の発生の記録(未確認)、海外の取引所の板の深さ(過去の板の履歴が取れる経路は未確認。区分 C の可能性)。
- 約定の模型: 未定(場面の変数なので、使う案の模型による)。

#### X2-C-04(升 P12-強制)

- 原文: 「A liquidator strategy inside HLP absorbs positions that fall below two thirds of maintenance margin when the order book cannot close them cleanly.」(訳: HLP の中の清算の戦略は、維持証拠金の 3 分の 2 を下回り、板できれいに閉じられない建玉を吸収する)。出所: https://www.buildix.trade/blog/how-hyperliquid-liquidations-work-margin-hlp-adl-2026 (ページ確認済み)。検索の返答の文: 「When a trader's position falls below maintenance margin and the order book cannot absorb the full size of the close, HLP becomes the counterparty of last resort, taking over the position and unwinding it over time.」(訳: 取引をする人の建玉が維持証拠金を下回り、板が閉じる量の全部を吸収できないとき、HLP が最後の相手方になり、建玉を引き取って時間をかけて解消する。ページ未確認。経路 WebSearch。出所の候補は https://www.coingecko.com/learn/hyperliquid-hlp-vault-analysis で、WebFetch はしていない。buildix のページは「時間をかけて解消する」を書いていない(WebFetch の返答))。
- 意図の地図: 入る条件 = HLP が清算の建玉を引き取った時点(引き取った量と向きの取り方は未定)。出る条件 = HLP の引き取った建玉が解消された時点(未定)。保有中の判断 = 未定。強弱の付け方 = 引き取った量(未定)。向き = 引き取った建玉を解消する向き(清算された人が買い建てなら、HLP は買い建てを引き取り、解消のために売る、と読む。【仮定】解消が板で行われること)。
- なぜ: 誰が損をしているか = HLP に預けた人(出所の主張: 急な相場で悪い建玉を引き継ぐことがある)と、解消の流れの反対側に立つ人。なぜ続くか = 板が清算を吸収できないときの受け皿が金庫である作りが続く限り、引き取りと解消は起きる。何で崩れるか = 解消が時間をかけず一度に済む、または解消が BTCUSD の動きに比べて小さい。
- 期待する向きと場面: 場面 = 大きい清算の後、HLP が建玉を持っている間。効く項 = BTCUSD。向き = HLP の解消の向き。
- 反証: HLP が建玉を引き取った後の時間帯に、解消の向きへの BTCUSD の動きが、引き取りの無い同じ大きさの清算の後と違わない。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ。
- 水準とその出所: 原文の値は「維持証拠金の 3 分の 2」(HLP が引き取る条件)だけ。それ以外は未定(W4 で測る前に決める)。
- 使うデータと遅れ: HLP の金庫の建玉(Hyperliquid の公開の経路で金庫の建玉が見えるか、履歴が取れるかは未確認)。遅れは未確認。
- 約定の模型: 未定。

#### X2-C-05(升 P13-移動)

- 原文: 「A brand-new wallet with little or no prior activity.」(訳: 以前の活動がほとんど・全く無い、真新しい財布)/「Funded by a traceable USDC source, often shared with other suspicious wallets.」(訳: たどれる USDC の出所から資金を入れられ、その出所は他の疑わしい財布と共通であることが多い)/「Wallets sharing a funder are likely controlled by the same operator.」(訳: 資金の出し手を共有する財布は、同じ操作者が動かしている可能性が高い)/「Entered shortly before resolution, on the winning side.」(訳: 結果の確定の直前に、勝つ側に入った)/「A suspected insider leaves a specific footprint on-chain」(訳: 内部者と疑われる者は、チェーンの上に特有の足跡を残す)。出所: https://docs.bitquery.io/docs/examples/polymarket-api/polymarket-insider-detection-api/ (ページ確認済み)。
- 意図の地図: 入る条件 = BTCUSD・USDJPY に効く事象(米国の金融政策・日銀の決定・BTC の制度の決定など)の予測市場で、新しい財布に USDC が入り、すぐその市場の片方の側に大きく賭けられた時点(「新しい」「大きい」の定義は未定)。出る条件 = 事象の公表、または未定。保有中の判断 = 未定。強弱の付け方 = 同じ出し手の財布の数・賭けの量(未定)。向き = 賭けられた側の結果が BTCUSD・USDJPY に与える向き(結果と向きの対応は事象ごとに未定)。
- なぜ: 誰が損をしているか = 事象の結果を知らずに、公表の前に反対の向きの持ち高を持つ人。なぜ続くか = 出所の主張では、内部者は公表の前に新しい財布を作って賭け、その足跡がチェーンに残る。予測市場の担保の動きが公開のチェーンの上にある限り、足跡は見える。何で崩れるか = 内部者が足跡を残さない入り方(古い財布・分散)に変える、または予測市場で賭けられる量が小さく、同じ情報が BTC の市場にまだ出ていないという前提が成り立たない。
- 期待する向きと場面: 場面 = BTC・円に効く事象の公表の前。効く項 = BTCUSD(BTC・米国の事象)、USDJPY(日銀・財務省の事象)。
- 反証: 足跡の条件に当たる賭けの向きと、その後の公表の時点の BTCUSD・USDJPY の動きの向きが、足跡の無い賭けと違わない。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ。
- 水準とその出所: 未定(W4 で測る前に決める)。原文に値は無い。
- 使うデータと遅れ: Polygon の上の USDC の送金と Polymarket の約定(Bitquery の経路は鍵が要るかを確かめていない。未確認。Polymarket の Data API で財布ごとの約定が取れるかは round1 の P13-約定の行で「取れる旨の資料」まで)。遅れ = ブロックの確定まで(秒〜分。未確認)。
- 約定の模型: 未定。

#### X2-C-06(升 P13-約定)

- 原文: 「This paper provides the first option-implied benchmark test of prediction-market pricing for cryptocurrency threshold contracts. For each hour in a matched sample, we compare the Polymarket Yes price with the discounted risk-neutral binary value implied by a listed Binance call option on the same underlying, strike, and maturity, and study the gap between them.」(訳: この論文は、暗号資産の閾値の契約について、予測市場の価格付けを option の含む値を基準にして確かめる最初の検定を示す。対応付けた標本の 1 時間ごとに、Polymarket の Yes の価格と、同じ原資産・行使価格・満期の Binance の上場コール option が含む、割り引いたリスク中立の二値の価値を比べ、その差を調べる)。出所: Victoria Portnaya「Do Prediction Markets Match Option Prices? Bitcoin Threshold Evidence from Binance and Polymarket」https://ideas.repec.org/p/arx/papers/2606.19517.html (ページ確認済み。要旨の一部。続きは切れていた)。あわせて検索の返答の文: 「Mispricing is most pronounced at contract inception and near expiration, and is systematically amplified during weekends and periods of high macroeconomic uncertainty.」(訳: 価格のずれは契約の開始時と満期の近くで最も大きく、週末と、マクロの不確かさが高い期間に系統的に大きくなる。ページ未確認。経路 WebSearch。出所の候補 https://fc26.ifca.ai/defi/papers/market-efficiency-prediction-markets.pdf 、WebFetch はしていない)。
- 意図の地図: 入る条件 = BTC の閾値の予測市場の Yes の価格と、同じ閾値・満期の option の含む確率との差が、一方の向きに大きくなった時点(大きさ・時間幅は未定)。出る条件 = 差が縮んだ時点、または未定。保有中の判断 = 未定。強弱の付け方 = 差の大きさ(未定)。向き = 未定(差を「予測市場の参加者の向きの偏り」と読み、その向きに付くか逆に付くかは未定)。
- なぜ: 誰が損をしているか = 出所の主張では、予測市場の側で、option から見てずれた価格で賭ける人。なぜ続くか = 予測市場と option の参加者が別で、両方をつなぐ裁定が小さい(仮定)。何で崩れるか = 両方をつなぐ裁定が増え、差が消える。差が BTCUSD の先の動きと関係しない。
- 期待する向きと場面: 場面 = 差が開いている時(出所の主張では週末・マクロの不確かさが高い時に開く)。効く項 = BTCUSD。
- 反証: 差の向きと、その後の BTCUSD の動きの向きに、関係が無い。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ。
- 水準とその出所: 原文の値は要旨の「平均の差 5.6 パーセント点(2023 年 9 月の契約、214 時間)」で、これは出所の主張の過去の値なので水準には使わない。水準は未定(W4 で測る前に決める)。
- 使うデータと遅れ: Polymarket の価格(round1 の P13-約定の行の API。期間は未確認)、Binance・Deribit の option の価格(過去の履歴の経路は未確認)。遅れは未確認。
- 約定の模型: 未定。

#### X2-C-07(升 P13-約定)

- 原文: 「Polymarket contracts display real inefficiencies」(訳: Polymarket の契約は本当の非効率を示す)/「Polymarket is overestimating Bitcoin's forward volatility across strikes.」(訳: Polymarket は、行使価格を通して、BTC の先の変動率を過大に見積もっている)/「For $71.85, we can buy 1 of these call spreads and sell 95 Polymarket calls.」(訳: 71.85 ドルで、このコールスプレッドを 1 つ買い、Polymarket のコールを 95 売れる)。WebFetch の返答の説明: IBIT(BTC の ETF)の 3 月の 62/63 のコールスプレッドを買い、同時に 11 万ドルの行使価格の Polymarket の二値のコールを 95 売る。出所: https://podshopguy.substack.com/p/polymarket-overprices-volatility (ページ確認済み。記事の日付は WebFetch の返答に無い)。
- 意図の地図: 入る条件 = 予測市場の BTC の閾値の契約が含む変動率と、option(IBIT・Deribit)の含む変動率の差が、予測市場の側に高く開いた時点(差の定義は未定)。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 差の大きさ(未定)。向き = 未定。この案の機構は、出所の取引(予測市場を売り、option のコールスプレッドを買う)を行う裁定の人が増えると、option の側でコールスプレッドの買いが起き、それを売ったディーラーのヘッジが BTCUSD(IBIT を通して)に出る、という経路である(【仮定】ディーラーのヘッジの向きと量は出所に書かれていない)。
- なぜ: 誰が損をしているか = 出所の主張では、予測市場で変動率を高く払って二値のコールを買う人。なぜ続くか = 仮定: 予測市場の参加者が option を使わない。何で崩れるか = 裁定が増えて差が消える。ディーラーのヘッジの量が BTCUSD の動きに比べて小さい。
- 期待する向きと場面: 場面 = 差が開いた時と、出所の取引の満期・行使価格の近く。効く項 = BTCUSD。向きは未定。
- 反証: 差が開いた時点の後に、IBIT の option の建玉・BTCUSD の動きに、差の無い時点との違いが無い。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ。
- 水準とその出所: 原文の値は取引の例(62/63 のコールスプレッド、11 万ドルの行使価格、95 枚)だけで、水準ではない。水準は未定(W4 で測る前に決める)。
- 使うデータと遅れ: Polymarket の閾値の契約の価格(期間は未確認)、IBIT の option の価格と建玉(無料で過去の履歴が取れる経路は未確認)。
- 約定の模型: 未定。

#### X2-C-08(升 P13-約定)

- 原文: 「Polymarket's 5-minute BTC up/down markets lag Binance spot by 30-90 seconds on large moves.」(訳: Polymarket の 5 分の BTC の上下の市場は、大きい動きのとき、Binance の現物に 30〜90 秒遅れる)/「Detect a large BTC move on Binance, buy the corresponding YES/NO market on Polymarket before odds reprice」(訳: Binance で BTC の大きい動きを見つけ、確率が付け直される前に、Polymarket の対応する YES/NO の市場を買う)。WebFetch の返答の説明: 60 秒の窓で 0.3% 以上の動きを合図にする。出所: https://chudi.dev/blog/binance-polymarket-momentum-signal-pipeline (ページ確認済み)。
- 意図の地図: 出所の機構は「個人の多い場の価格が、大きい場の価格の大きい動きに、数十秒遅れて付け直される」。bitFlyer への当てはめ(リードの升の項に合わせた作業者の当てはめ。出所には bitFlyer は無い): 入る条件 = BTCUSD × USDJPY の大きい動き(大きさ・時間幅は未定)の直後、bitFlyer の価格がまだ付け直されていない時点。出る条件 = bitFlyer の価格が付け直された時点(未定)。保有中の判断 = 未定。強弱の付け方 = 動きの大きさ(未定)。向き = 海外の動きと同じ向き。
- なぜ: 誰が損をしているか = 付け直しの前の古い価格で約定する、個人の多い場の参加者(出所の主張では Polymarket の側)。なぜ続くか = 個人の多い場の参加者は大きい場の価格を秒単位で見ていない(仮定)。何で崩れるか = 個人の多い場で価格を付け直す速い参加者が増え、遅れが消える。
- 期待する向きと場面: 場面 = 大きい動きの直後の数十秒。効く項 = 円の上乗せ(bitFlyer の価格が BTCUSD × USDJPY から一時離れる分)と経費(速い約定が要る)。
- 反証: 大きい動きの直後に、bitFlyer の価格の付け直しの遅れが、小さい動きの時と違わない、または遅れの間の動きが経費より小さい。
- 段 3 の種類: (b) 海外と日本の違い(遅れ)を使う。
- 水準とその出所: 原文の値は「30〜90 秒」(Polymarket の遅れ)と「60 秒の窓で 0.3%」(出所の合図)。これは Polymarket についての値で、bitFlyer の水準ではない。bitFlyer の水準は未定(W4 で測る前に決める)。
- 使うデータと遅れ: BTCUSD(海外の取引所の約定。秒の粒度)、USDJPY(秒の粒度の経路は未確認)、bitFlyer の約定(秒単位の記録は封印。この周では開かない)。
- 約定の模型: 成行(遅れを使う形のため。決めるのは W4)。
- 注: 在庫の #28(Binance の先行を追う)と同じ形。違う点: 出所が「個人の多い場の遅れ」を予測市場で示した記述で、遅れが「大きい動きのとき」に限ると書く点(場面を大きい動きに限る)。
- 追記(第 4 周、リードの指示 第 3 周の受け取り 問い 4): bitFlyer への当てはめは作業者の当てはめ。出所に bitFlyer は出てこない。

#### X2-C-09(升 P14-移動)

- 原文: 検索の返答の文(bitFlyer のかんたん積立のページ): 「積立頻度は毎日1回、毎週1回、毎月2回、毎月1回から選択できます」/「積立時の購入レートは積立時刻の当社販売所の価格を参照いたします」/「積立を設定した日の翌日から設定が反映される」。ページ未確認(経路: WebFetch https://bitflyer.com/ja-jp/static/recurring-buy 、応答 HTTP 403 Forbidden。検索の返答は「公式ドキュメントには具体的な購入実行時刻は明記されていません」と書く)。
- 意図の地図: 入る条件 = 国内の取引所の積立の買いが実行される時刻(時刻は未確認)の前後。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 積立の日(毎月の積立日に当たる日か)(未定)。向き = 買い側(積立は買いだけ)。【仮定】販売所で売った分を、bitFlyer が自社の取引所(Lightning)などで買い戻してヘッジする。この仮定はこの周で確かめていない。
- なぜ: 誰が損をしているか = 積立の時刻に、販売所の価格で買う個人(値の動きを見ずに定時に買う)。なぜ続くか = 積立は一度設定すると自動で続く(検索の返答の解説: 「一度条件を決めるとほぼ自動で取引ができます」、diamond のページの語として検索の返答に出た。ページ未確認)。何で崩れるか = 積立の量が bitFlyer の板に比べて小さい。販売所の分が板に出ない(社内で相殺される)。
- 期待する向きと場面: 場面 = 積立の時刻(毎日・毎月の積立日)。効く項 = 円の上乗せ(国内の個人の買いだけで bitFlyer の価格が BTCUSD × USDJPY から離れる分)。向き = 上乗せが増える向き。
- 反証: 積立の時刻の前後で、円の上乗せの動きが他の時刻と違わない。
- 段 3 の種類: (b) 海外と日本の違い(国内の個人の定時の買い)を使う。
- 水準とその出所: 原文の値は頻度(毎日 1 回・毎週 1 回・毎月 2 回・毎月 1 回)だけ。時刻は未確認。水準は未定(W4 で測る前に決める)。
- 使うデータと遅れ: 積立の時刻(bitFlyer の規約・案内のページ。この周では 403 で開けなかった)、bitFlyer の約定(1 分足は区分 A。封印の期間は開かない)、BTCUSD、USDJPY。遅れ = 暦なので前もって分かる(時刻が確かめられれば)。
- 約定の模型: 未定。

#### X2-C-10(升 P14-移動)

- 原文: 「BTC drew a slight premium in Japanese markets on Monday as the yen swung wildly」(訳: 円が大きく振れた月曜日、BTC は日本の市場でわずかな上乗せを付けた)/「The recovery's speed and magnitude spurred talks of BOJ intervening or selling dollars」(訳: 戻りの速さと大きさが、日銀が介入した、つまりドルを売ったという話を呼んだ)/「traders diversifying into alternative assets to bypass the yen volatility」(訳: 円の変動を避けるために、取引をする人が代わりの資産に分散している)。出所: https://malaysia.news.yahoo.com/bitcoin-trades-slight-premium-yen-113159350.html (ページ確認済み。「Updated Mon, 29 April 2024 at 11:31 am UTC」)。
- 意図の地図: 入る条件 = USDJPY が短い時間で大きく動いた時点(大きさ・時間幅は未定)。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = USDJPY の動きの大きさ(未定)。向き = 出所の主張では、円が大きく振れたときに国内で BTC への退避の買いが起き、円の上乗せが増える。
- なぜ: 誰が損をしているか = 円の変動から逃げるために、上乗せの付いた価格で BTC を買う国内の個人。なぜ続くか = 国内の個人は海外の取引所で BTC を買えず、退避の買いが国内の板に集まる(仮定)。何で崩れるか = 国内と海外の差を埋める人(P19)が速く入り、上乗せがすぐ消える。
- 期待する向きと場面: 場面 = USDJPY の急な動き(介入の観測を含む)。効く項 = 円の上乗せ・USDJPY。向き = 上乗せが増える向き。
- 反証: USDJPY の急な動きの後に、円の上乗せの動きが、USDJPY が静かな時と違わない。
- 段 3 の種類: (b) 海外と日本の違い(円の上乗せ)を使う。
- 水準とその出所: 原文に値は無い(「slight premium」= わずかな上乗せ、の語だけ)。未定(W4 で測る前に決める)。
- 使うデータと遅れ: USDJPY(分足)、BTCUSD(分足)、bitFlyer の 1 分足(区分 A。封印の期間は開かない)。遅れは分。
- 約定の模型: 未定。
- 注: 跡は P14(国内の個人)の移動で、引き金は P15(介入)の約定。升 P15-約定にも当たりうる(迷った点 3)。

#### X2-C-11(升 P14-約定)

- 原文: 「含み損を確定させて、実現利益（＝所得）をゼロに近づける」/「「損益圧縮」といい、高い節税効果が期待できます。」/「利益と丁度相殺される程度まで確定し、それでも残る含み損は翌年に確定させた利益の状況を見て相殺していく」/「年内に売却して問題ないのは『実現させた利益と同じ程度の赤字分』」。出所: coinpost「利益があるほど含み損は年末までに損切りした方が節税効果も高い？納税売りのメリットとデメリットを税理士が解説｜Aerial Partners寄稿」2024-12-23 https://coinpost.jp/?p=583174 (ページ確認済み)。あわせて検索の返答の文: 「確定した利益がある程度存在する状態で、年末に保有している仮想通貨を売却して日本円に変える「納税売り」という風潮があります」(ページ未確認。経路 WebSearch。どのページの文かは返答から特定できなかった)。
- 意図の地図: 入る条件 = 12 月の年末に近い期間(何日前からかは未定)。出る条件 = 年明け、または未定。保有中の判断 = 未定。強弱の付け方 = その年の BTC の上げ幅(実現した利益の多い年ほど、損出しの売りが大きい、と読む。未定)。向き = 年末は国内の個人の売り(含み損の確定・納税売り)で円の上乗せが減る向き。年明けの買い戻しは出所に無い(この案の要素に入れない。入れるなら別の案)。
- なぜ: 誰が損をしているか = 年末に急いで売る国内の個人(税のために値を見ずに売る)。なぜ続くか = 日本の暗号資産の利益は雑所得で、1 月 1 日〜12 月 31 日の年の単位で計算されるので、年の切れ目が国内の個人だけに掛かる(出所: 検索の返答の文「1月1日~12月31日までの1年間の所得にかかる税金額を計算し」、ページ未確認)。海外の参加者には同じ暦の切れ目が掛からないか、別の制度(仮定)。何で崩れるか = 税の制度が変わる(申告分離課税への変更など)。国内の個人の売りが bitFlyer の板に比べて小さい。
- 期待する向きと場面: 場面 = 12 月の年末。効く項 = 円の上乗せ(国内の個人の売りだけで bitFlyer の価格が BTCUSD × USDJPY から離れる分)。向き = 上乗せが減る向き。
- 反証: 12 月の年末の期間に、円の上乗せの動きが他の月の月末と違わない。
- 段 3 の種類: (b) 海外と日本の違い(制度: 税の年の切れ目)を使う。
- 水準とその出所: 原文に値は無い。未定(W4 で測る前に決める)。
- 使うデータと遅れ: 暦(前もって分かる)、bitFlyer の 1 分足・日足(区分 A。封印の期間は開かない)、BTCUSD、USDJPY。
- 約定の模型: 未定。

#### X2-C-12(升 P15-持ち高)

- 原文: 「For the week ending May 6, Fed data indicated that the balance of US Treasury securities held in custody for foreign official and international accounts decreased by $8.7 billion to $2.73 trillion.」(訳: 5 月 6 日に終わる週について、米連銀の統計は、海外の公的・国際機関の口座のために預かっている米国債の残高が 87 億ドル減って 2.73 兆ドルになったことを示した)/「The changes in the custody accounts appear to align with the timing of the intervention instructed by Japan's Ministry of Finance to the Bank of Japan.」(訳: 預かりの口座の変化は、財務省が日銀に指示した介入の時期と一致しているように見える)— Rodrigo Catril。出所: https://www.itiger.com/news/1128618673 (ページ確認済み。記事の日付は「May 09」と返答にあり、年は返答に無い)。あわせて「The data is reported every Thursday.」(訳: この統計は毎週木曜に報告される)/「During this period, a number of central banks in Asia and Latam ... are believed to have sold dollars to smooth out and possible arrest the decline in their respective currencies.」(訳: この期間、アジアと中南米のいくつかの中央銀行が、自国の通貨の下落をならし、できれば止めるために、ドルを売ったと見られている)。出所: https://marctomarket.com/2011/11/draw-down-of-federal-reserves-custody.html (ページ確認済み。2011 年 11 月の記事)。
- 意図の地図: 入る条件 = 毎週木曜に公表される、米連銀の海外公的機関の預かり残高の週の変化が、減少の向きに大きい週(大きさは未定)。出る条件 = 未定。保有中の判断 = 未定(週の場面の変数)。強弱の付け方 = 減少の大きさ(未定)。向き = 減少の週は、海外の公的機関がドルを売る(介入の資金を作る)局面にある、と読む。USDJPY の向きは、減少が日本の介入の資金作りと重なるときに円高側(仮定。統計は国別ではない)。
- なぜ: 誰が損をしているか = 介入の資金作り(米国債の売り・ドル売り)が続いている局面を知らずに、円売りの持ち高を持つ人。なぜ続くか = 月次の外貨準備(round1 の P15-持ち高の行。翌月上旬の公表)より速い、週次の公的な持ち高の跡がある。何で崩れるか = 介入が預かり残高を減らさない資金で行われる(下の X2-C-13 の FIMA の repo・預金)。統計が国別ではないので、他の国の売りと区別できない。
- 期待する向きと場面: 場面 = 預かり残高が減っている週。効く項 = USDJPY。
- 反証: 預かり残高が大きく減った週の後に、USDJPY の動きが他の週と違わない。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ(USDJPY の項を通して)。
- 水準とその出所: 原文の値は「87 億ドル減って 2.73 兆ドル」(ある週の値)で、水準ではない。未定(W4 で測る前に決める)。
- 使うデータと遅れ: 米連銀 H.4.1 の「Securities held in custody for foreign official and international accounts」(週次、木曜の公表。経路と履歴の長さは未確認)。遅れ = 週の終わり(水曜)から公表(木曜)まで(未確認)。
- 約定の模型: 未定。

#### X2-C-13(升 P15-持ち高)

- 原文: 「market participants generally estimate that roughly 70% of Japan's reserves are invested in US Treasuries」(訳: 市場の参加者は、日本の外貨準備の約 70% が米国債に投じられていると見積もっている)/「foreign currency deposits — another potential funding source for market operations — declined by $6.9 billion」(訳: 外貨預金 — 市場の操作のもう一つの資金の出所 — は 69 億ドル減った)/「That mechanism would allow Japan to access up to $60 billion in daily liquidity without necessitating sales of US Treasuries」(訳: その仕組み(FIMA の repo)は、米国債を売らずに、1 日最大 600 億ドルの資金を日本が使えるようにする)/「Japanese officials assess that the remaining stockpile offers sufficient capacity for future intervention if needed」(訳: 日本の当局者は、残りの蓄えが、必要なら今後の介入に十分な余力があると見ている)。出所: https://www.itiger.com/news/1177505098 (ページ確認済み。2026-09-07 の記事)。
- 意図の地図: 入る条件 = 月次の外貨準備の公表で、内訳(証券・預金)のうち、すぐ介入に使える分(預金)が減った、または増えた月(大きさは未定)。出る条件 = 未定。保有中の判断 = 未定(月の場面の変数)。強弱の付け方 = すぐ使える分の大きさ(未定)。向き = 未定(すぐ使える分が多いほど、介入の脅しが効きやすい、と読むか、逆かは未定)。
- なぜ: 誰が損をしているか = 介入の余力を見ずに円売りの持ち高を積む人(仮定)。なぜ続くか = 介入の資金は、預金・米国債の売り・FIMA の repo のどれから出るかで、見える跡が変わる(出所の主張)。round1 の P15-持ち高の行は外貨準備の総額だけを見た。内訳と資金の出所は扱っていない。何で崩れるか = 介入の判断が余力に関係しない。
- 期待する向きと場面: 場面 = 円安が進み、介入の観測がある月。効く項 = USDJPY。
- 反証: すぐ使える分の多い月と少ない月で、介入の観測のある局面の USDJPY の動きが違わない。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ(USDJPY の項を通して)。
- 水準とその出所: 原文の値は「約 70%」「69 億ドル」「1 日最大 600 億ドル」(制度と内訳の値)で、売買の水準ではない。未定(W4 で測る前に決める)。
- 使うデータと遅れ: 財務省の外貨準備等の状況(月次。内訳の欄。翌月上旬の公表。round1 の P15-持ち高の行)。FIMA の repo の利用額(米連銀の公表。経路は未確認)。
- 約定の模型: 未定。

#### X2-B-81(升 P10-関心)

- 原文: 「The Texas House of Representatives has passed landmark legislation seeking to establish a Bitcoin reserve on its third and final reading on Wednesday」(訳: テキサス州下院は水曜日、BTC の準備を設けようとする画期的な法案を、3 回目で最後の読会で可決した)/「now awaits a concurrence vote on House amendments before heading to Governor Greg Abbott's desk to be signed into law.」(訳: 下院の修正への同意の採決を待ち、その後アボット知事の署名に回る)/「It is unknown what appropriations would be made for the reserve and the amount and value of qualifying cryptocurrency that would be purchased.」(訳: 準備にどれだけの予算が付き、対象の暗号資産をどれだけの量と価値で買うかは分からない)。出所: https://decrypt.co/321519/texas-bitcoin-reserve-final-sign-off (ページ確認済み。2025-05-22 の記事)。
- 意図の地図: 入る条件 = 州・国の議会で、BTC を政府が買う(準備に入れる)法案の採決・署名の予定日(議会の日程として前もって公開される)。出る条件 = 採決の結果の公表、または未定。保有中の判断 = 未定。強弱の付け方 = 法案が定める購入の額(多くは「分からない」と出所が書く。未定)。向き = 可決は買い側、否決は売り側(仮定)。
- なぜ: 誰が損をしているか = 採決の結果の前に、反対の向きの持ち高を持つ人。なぜ続くか = 州ごとに議会の日程が別で、採決が何度も(読会ごとに)ある。何で崩れるか = 法案の購入額が小さい・不明で、BTCUSD に効く量の買いにつながらない。
- 期待する向きと場面: 場面 = 採決・署名の予定日の前後。効く項 = BTCUSD。
- 反証: 採決の予定日の前後で、BTCUSD の動きが他の日と違わない。可決と否決で動きの向きが違わない。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ。
- 水準とその出所: 原文の値は採決の票数(105 対 23、のちに反対 42)で、水準ではない。未定(W4 で測る前に決める)。
- 使うデータと遅れ: 州議会の法案の日程と採決の記録(各州の議会のページ。一覧の経路は未確認)。遅れ = 日程は前もって公開、結果は採決の当日(未確認)。
- 約定の模型: 未定。
- 注: D1-B-30(連邦の方針の発表)と違う点: 連邦の 1 回の発表でなく、州ごとに日程が前もって分かる採決が何度もある。政府が売らないだけでなく買う側に回る。

#### X2-B-82(升 P10-関心)

- 原文: 「Seized assets are always liquidated over a certain period. This is a routine business process, albeit on a larger scale than usual.」(訳: 押収した資産は、いつも一定の期間をかけて換金される。これは、普段より規模は大きいが、決まった業務の手順である)/「In most cases, confiscated assets are transferred or sold with the proceeds going to the state budget by court decision. However, regions can initiate emergency sales, for instance, if there are risks of rapid devaluation or storage difficulties.」(訳: 多くの場合、没収した資産は裁判所の決定により移されるか売られ、代金は国の予算に入る。しかし地域(州)は、たとえば急な価値の下落の危険や保管の難しさがある場合、緊急売却を始められる)/「In the case of Bitcoin, this can be said, at least from the perspective of volatility.」(訳: BTC の場合、少なくとも変動の大きさの観点からは、そう言える)— Lennart Ante。出所: https://forklog.com/en/german-bitcoin-sales-clarified-by-expert/ (ページ確認済み。2024-07-10 の記事)。
- 意図の地図: 入る条件 = 押収した BTC を持つ地域の当局が、裁判の確定を待たずに売る判断(緊急売却)に向かう局面。出所の主張では、引き金は「急な価値の下落の危険」(BTC の変動の大きさ)と「保管の難しさ」。跡として、BTC の急落・変動の高まりと、押収した BTC を持つ当局の財布の組を見る(定義は未定)。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = その当局の保有量(未定)。向き = 売り。
- なぜ: 誰が損をしているか = 政府の売りが変動の大きい局面で出ることを見ずに買う人(仮定)。なぜ続くか = 緊急売却の規定は、価値の下落の危険で売りを許す作りで、変動の大きい局面ほど売りの判断が出やすい(出所の主張からの当てはめ)。何で崩れるか = 当局が保管の仕組みを整え、緊急売却を使わない。押収の BTC が少ない。
- 期待する向きと場面: 場面 = 押収した BTC を持つ当局がある時期の、変動の高い局面。効く項 = BTCUSD。向き = 売り。
- 反証: 変動の高い局面の後に、押収した BTC を持つ当局の財布からの送金が増えない。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ。
- 水準とその出所: 原文に値は無い。未定(W4 で測る前に決める)。
- 使うデータと遅れ: 当局に紐づく財布のラベル(Arkham。取得の経路と鍵の要否は未確認。round1 の P10-移動の行も同じ)、BTCUSD の変動。
- 約定の模型: 未定。
- 注: D1-B-30(方針の発表)・D1-B-37(裁判所の承認)と違う点: 裁判の決定を待たない売りの規定があり、その引き金が価格の変動そのものである。

#### X2-B-83(升 P10-予告)

- 原文: 「Chief U.S. District Judge Richard Seeborg denied a motion to block the forfeiture of 69,370 Bitcoin, clearing the Department of Justice to sell the $6.5 billion assets.」(訳: 連邦地裁のシーボーグ首席判事は、69,370 BTC の没収を止める申し立てを退け、司法省が 65 億ドルの資産を売れるようにした)/「The ruling alone doesn't guarantee immediate liquidation since federal asset forfeiture involves multiple administrative steps and potential appeal windows.」(訳: 連邦の資産の没収にはいくつもの事務の手順と上訴の期間があるので、判決だけで直ちに換金されるとは限らない)。出所: https://decrypt.co/300133/us-court-greenlights-sale-of-6-5b-in-seized-silk-road-bitcoin (ページ確認済み。2025-01-09 の記事)。
- 意図の地図: 入る条件 = 政府が持つ押収 BTC について、裁判所が売却を止める申し立てを退けた(売却を可能にした)時点。出る条件 = 上訴の期間の終わり、または送金(P10-移動)の発生(未定)。保有中の判断 = 未定。強弱の付け方 = 対象の量(未定)。向き = 売り(ただし、売らない方針(D1-B-30)の下では向きなし)。
- なぜ: 誰が損をしているか = 判決から売却までの手順の長さを見ずに、判決の日に売りが出ると見て売る人、または逆に売却を見ずに買う人(仮定)。なぜ続くか = 出所の主張では、判決と換金の間に事務の手順と上訴の期間がある。判決の日と売却の日がずれる作りが続く。何で崩れるか = 政府の方針が「売らない」に変わる(D1-B-30)。
- 期待する向きと場面: 場面 = 判決の日と、上訴の期間の終わりの前後。効く項 = BTCUSD。
- 反証: 判決の日と上訴の期間の終わりの前後で、BTCUSD の動きが他の日と違わない。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ。
- 水準とその出所: 原文の値は対象の量(69,370 BTC)だけ。上訴の期間の長さは原文に無い。未定(W4 で測る前に決める)。
- 使うデータと遅れ: 裁判所の記録(PACER は有料のため使わない。無料の写し(CourtListener など)で取れるかは未確認)、報道の日付。
- 約定の模型: 未定。
- 注: D1-B-37(破産の裁判所の承認 → 管財人の売却)と違う点: 売る人が政府(没収)で、判決と売却の間に上訴の期間という長さの決まった遅れがある。

#### X2-B-84(升 P10-予告)

- 原文: 「Interested bidders must register with the USMS by e-mail by midday on October 31st」(訳: 入札したい人は 10 月 31 日の正午までに US Marshals Service にメールで登録しなければならない)/「the auction will be taking place between 8am and 2pm EST on November 5th」(訳: 競売は 11 月 5 日の東部標準時 午前 8 時から午後 2 時に行われる)/「you must put down a deposit of $200,000 as a sign of intent」(訳: 意思の証として 20 万ドルの保証金を入れなければならない)。出所: https://thenextweb.com/news/us-marshals-service-auctioning-bitcoin (ページ確認済み。2018-10-19 の記事)。
- 意図の地図: 入る条件 = 政府が押収 BTC の競売の日程(登録の期限・競売の日時)を前もって公表した時点から競売の日まで。出る条件 = 競売の結果の公表、または未定。保有中の判断 = 未定。強弱の付け方 = 競売の量(未定)。向き = 未定(競売は板の外で行われるので、板への売りは出ない。落札した人がその後に板で売るか、落札のために事前に板で売り建ててヘッジするかで向きが変わる。【仮定】どちらもこの周で確かめていない)。
- なぜ: 誰が損をしているか = 競売の日程を見ずに持ち高を持つ人(仮定)。なぜ続くか = 競売の形の売却は、日程が前もって公開される(出所)。板で売る形(D1-B-33 の送金)と違い、暦が先に分かる。何で崩れるか = 政府が競売をやめ、取引所・カストディ経由の売却(round1 の P10-約定の行の Coinbase Prime)に切り替えた。
- 期待する向きと場面: 場面 = 競売の登録の期限から競売の日まで。効く項 = BTCUSD。
- 反証: 競売の日程の公表から競売の日までの BTCUSD の動きが、他の期間と違わない。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ。
- 水準とその出所: 原文の値は日程と保証金(20 万ドル)で、水準ではない。未定(W4 で測る前に決める)。
- 使うデータと遅れ: US Marshals Service の競売の告知(公開のページ。過去の告知の一覧の経路は未確認)。遅れ = 告知は競売の数週間前(原文の例では 10-19 の記事で 11-05 の競売)。
- 約定の模型: 未定。

#### X2-B-85(升 P10-予告)

- 原文: 「The Home Office and the head of the country's Treasury, Rachel Reeves, are working with law enforcement to sell off its stockpile of seized Bitcoin」(訳: 内務省と財務相のリーブスは、押収した BTC の蓄えを売り払うために、法執行機関と協力している)/「In May, the UK put out to tender a 40 million British pound ($53.7 million) 'crypto storage and realisation framework'」(訳: 5 月、英国は 4,000 万ポンド(5,370 万ドル)の「暗号資産の保管と換金の枠組み」を入札にかけた)/「The UK's bitcoin is still legally contested. Chinese authorities and victims are demanding it back. No sale can happen while that legal process is unresolved」(訳: 英国の BTC はまだ法的に争われている。中国の当局と被害者が返還を求めている。その法の手続きが決着するまで売却は起きえない)。出所: https://cointelegraph.com/news/uk-eyes-sale-7-billion-seized-bitcoin-boost-budget (ページ確認済み。2025-07-21 の記事)。
- 意図の地図: 入る条件 = 政府が押収 BTC の「保管と換金」の業者を選ぶ入札を公告した時点、入札の落札の公表、法的な争いの決着(返還の請求の判決)の時点(どれを使うかは未定)。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 対象の保有量(未定)。向き = 売り(換金の準備が進む向き)。法的な争いが返還の側で決着した場合は向きなし(政府が売らない)。
- なぜ: 誰が損をしているか = 政府の換金の準備の段階を見ずに持ち高を持つ人(仮定)。なぜ続くか = 政府の売却には、保管と換金の業者を選ぶ公的な調達の手続きが要り、調達は公告される(出所)。売却の前に必ず残る公開の跡になる(仮定)。何で崩れるか = 政府が既存の業者(Coinbase Prime など)を使い、新しい調達を経ない。
- 期待する向きと場面: 場面 = 調達の公告・落札・法的な決着の前後。効く項 = BTCUSD。
- 反証: 調達の公告・落札の後に、その政府の財布からの送金・売却が起きない、または BTCUSD の動きが他の期間と違わない。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ。
- 水準とその出所: 原文の値は入札の額(4,000 万ポンド)で、水準ではない。未定(W4 で測る前に決める)。
- 使うデータと遅れ: 英国政府の調達の公告(Find a Tender など。経路と履歴は未確認)、裁判の記録(未確認)。遅れ = 公告は公表の日。
- 約定の模型: 未定。

#### X2-B-86(升 P10-移動)

- 原文: 「The Royal Government of Bhutan transferred 512.84 BTC ($62.6 million) to a Binance crypto exchange deposit address over the past four days, coinciding with the cryptocurrency's multiple rewrites of its all-time high record.」(訳: ブータン王国政府は過去 4 日間に 512.84 BTC(6,260 万ドル)を Binance の入金アドレスへ送った。BTC が史上最高値を何度も塗り替えたのと時を同じくして)/「This may indicate a pattern of selling bitcoin during price rallies.」(訳: これは、価格の上昇の局面で BTC を売るという型を示しているかもしれない)。出所: https://www.theblock.co/news/markets/2025-07-14-bhutan-moves-bitcoin-362388 (ページ確認済み。2025-07-14 の記事)。あわせて「Unlike most nation-state holders that accumulate bitcoin through criminal seizures, Bhutan built its reserves through mining operations powered by hydroelectric energy.」(訳: 犯罪の押収で BTC を貯める多くの国家の保有者と違い、ブータンは水力の電気で動く採掘で蓄えを作った)/「The transfers were executed in multiple batches from a wallet tagged as belonging to Druk Holding & Investments, Bhutan's state investment wing, to a Binance deposit address.」(訳: 送金は、ブータンの国の投資部門 Druk Holding & Investments のものとラベルの付いた財布から、Binance の入金アドレスへ、何回にも分けて行われた)。出所: https://www.theblock.co/post/405111/bhutan-bitcoin-binance-holdings-fall-below-1750-btc-arkham (ページ確認済み。2026-06-17 の記事)。
- 意図の地図: 入る条件 = BTCUSD が高値を更新している局面で、採掘で BTC を貯めた政府の財布から取引所の入金アドレスへ送金が出た時点(「高値の更新」の定義は未定)。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 送金の量・何回に分けたか(未定)。向き = 売り(出所の主張では上昇の局面で売る型)。
- なぜ: 誰が損をしているか = 上昇の局面で買う人の相手に、政府の売りが入る(仮定)。なぜ続くか = 採掘で BTC を得る政府は、押収と違い、BTC が継続して増え、裁判の手順なしに売れる(出所の対比からの当てはめ)。売りの判断が価格(上昇)に条件づく、と出所は書く。何で崩れるか = 保有が尽きる(出所: 1,750 BTC を下回った)。売りの判断が価格に関係しなくなる。
- 期待する向きと場面: 場面 = BTCUSD の上昇の局面。効く項 = BTCUSD。向き = 売り(上昇の勢いを弱める向き)。
- 反証: 上昇の局面での政府の送金の後に、BTCUSD の動きが、送金の無い上昇の局面と違わない。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ。
- 水準とその出所: 原文の値は送金の量(512.84 BTC など)と保有の残り(1,749.96 BTC)で、水準ではない。未定(W4 で測る前に決める)。
- 使うデータと遅れ: 政府に紐づく財布のラベル(Arkham。経路と鍵の要否は未確認)、BTC のチェーンの送金(公開。遅れ = ブロックの確定まで)。
- 約定の模型: 未定。
- 注: D1-B-33・X1-B-18(押収した BTC の取引所宛ての送金)と違う点: BTC の出所が採掘で、売りの判断が価格の上昇に条件づく(出所の主張)。

#### X2-B-87(升 P10-移動)

- 原文: 「The German Federal Criminal Police Office (BKA) sent 125 BTC ($7.7 million) to each crypto exchange at around 7:52 a.m. UTC」(訳: ドイツ連邦刑事庁(BKA)は、UTC の午前 7 時 52 分ごろ、各取引所へ 125 BTC(770 万ドル)ずつ送った)/「The German Government also transferred 0.001 BTC to [market maker] Flow Traders, which may be a test transaction」(訳: ドイツ政府は、[マーケットメイカーの] Flow Traders へも 0.001 BTC を送った。これは試しの送金かもしれない)/「indicating a potential intention to sell the assets」(訳: 資産を売る意図があるかもしれないことを示す)。出所: https://www.theblock.co/post/301978/german-government-bitcoin-bitstamp-kraken (ページ確認済み。2024-06-26 の記事)。あわせて検索の返答の文: 「Authorities transferred 5,103 BTC ($299.8 million) to Kraken, Coinbase, market makers FlowTraders and Cumberland, the OTC service B2C2Group, and an unidentified address.」(訳: 当局は 5,103 BTC(2 億 9,980 万ドル)を Kraken・Coinbase・マーケットメイカーの Flow Traders と Cumberland・OTC の B2C2・不明のアドレスへ送った。ページ未確認。経路 WebSearch。出所の候補は forklog の記事)。
- 意図の地図: 入る条件 = 政府の財布から、新しい送金先(マーケットメイカー・OTC)へ少額(試しの送金)が出た時点(「少額」の定義は未定)。出る条件 = 同じ送金先へ大きい送金が出た時点、または未定。保有中の判断 = 未定。強弱の付け方 = 政府の残りの保有量(未定)。向き = 売り(試しの送金を、大きい送金と売却の前触れと読む)。送金先の種類で分ける: 取引所(板で売る)とマーケットメイカー・OTC(板の外で引き取り、引き取った側が時間をかけて板で売るかヘッジする。【仮定】)。
- なぜ: 誰が損をしているか = 大きい送金が出てから反応する人(試しの送金を見ていない)。なぜ続くか = 新しい送金先へ大きい額を送る前に、少額で試すのは、送り間違いを避ける運用の手順として続く(仮定。出所は「かもしれない」と書く)。何で崩れるか = 政府が既知の送金先だけを使い、試しの送金をしない。
- 期待する向きと場面: 場面 = 政府の財布から新しい送金先へ試しの送金が出た後。効く項 = BTCUSD。向き = 売り。
- 反証: 試しの送金の後に大きい送金が続く割合が低い、または試しの送金の後の BTCUSD の動きが他の時点と違わない。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ。
- 水準とその出所: 原文の値は「0.001 BTC」(試しの送金の例)と「125 BTC ずつ」。水準は未定(W4 で測る前に決める)。
- 使うデータと遅れ: 政府と送金先のラベル(Arkham。経路と鍵の要否は未確認)、BTC のチェーンの送金(公開)。遅れ = ブロックの確定まで。
- 約定の模型: 未定。
- 注: D1-B-33・D1-B-34・X1-B-18 と違う点: 大きい送金でなく、その前の少額の試しの送金を跡にする。D1-B-38(売却の方式)と違う点: 方式の区別を約定でなく、移動の段の送金先のラベルで行う。

#### X2-B-88(升 P10-約定)

- 原文: 「$312 million worth of their bitcoin was sold on Japanese exchange BitPoint」(訳: 彼らの BTC のうち 3 億 1,200 万ドル分が、日本の取引所 BitPoint で売られた)/「Kobayashi likely hired BitPoint to sell the Mt Gox Estate's crypto on the open market.」(訳: 小林(管財人)は、Mt. Gox の財団の暗号資産を公開の市場で売るために、BitPoint を雇ったと見られる)。WebFetch の返答の説明: 記事は、BitPoint から数十億円が動いたとされる支払いに触れる。出所: https://www.theblock.co/linked/10327/312m-in-mt-gox-crypto-allegedly-sold-by-trustee-through-bitpoint (ページ確認済み。2019-02-05 の記事。見出しに「allegedly」(とされる)とあり、出所の主張である)。
- 意図の地図: 入る条件 = 日本の管財人・当局が、BTC を日本の取引所を通して円で売っていると分かった期間(分かり方: 管財人の報告書・送金先のラベル。未定)。出る条件 = 売却の終わり(管財人の報告、または未定)。保有中の判断 = 未定。強弱の付け方 = 売却の量(未定)。向き = 日本の取引所での円建ての売りなので、円の上乗せが減る向き(【仮定】売りが国内の板に出る。出所は「open market」(公開の市場)と書くが、板か取引所を通した相対かは書かない)。
- なぜ: 誰が損をしているか = 国内の取引所で、管財人の売りの相手になる国内の買い手(仮定)。なぜ続くか = 日本の管財人・当局は、円で換金するために国内の取引所を使う(仮定)。国内の板は海外より薄い(仮定)ので、同じ量の売りでも円の上乗せの項に出る。何で崩れるか = 売却を海外の取引所・OTC で行う。国内と海外の差を埋める人(P19)がすぐ上乗せを戻す。
- 期待する向きと場面: 場面 = 日本の管財人・当局の売却の期間。効く項 = 円の上乗せ(bitFlyer の価格が BTCUSD × USDJPY から離れる分。売りが BitPoint で出ても、国内の取引所の間の裁定で bitFlyer に伝わる、と読む。【仮定】)。向き = 上乗せが減る向き。
- 反証: 日本の管財人・当局の売却の期間に、円の上乗せの動きが他の期間と違わない。
- 段 3 の種類: (b) 海外と日本の違い(円の上乗せ)を使う。
- 水準とその出所: 原文の値は売却の額(3 億 1,200 万ドル)で、水準ではない。未定(W4 で測る前に決める)。
- 使うデータと遅れ: 管財人の報告書(Mt. Gox の管財人のページ。公開の時期は売却の後。経路は未確認)、国内の取引所のチェーンのラベル(未確認)、bitFlyer の 1 分足(区分 A。封印の期間は開かない)。遅れ = 報告書は事後(遅れは未確認)。
- 約定の模型: 未定。
- 注: round1 の P10-約定は案なし(売却の約定の時刻・方式の公開の記録が見つからなかった)。この案は、約定の場所(日本の取引所)が出所にある記述から立てた。

#### X2-B-89(升 P10-持ち高)

- 原文: 「the Salvadoran government has been steadily adding to its Bitcoin reserves, purchasing one Bitcoin (BTC) every day since March 16.」(訳: エルサルバドル政府は 3 月 16 日から毎日 1 BTC を買い、BTC の準備を着実に増やしている)/「According to recent data from blockchain analytics platform Arkham Intelligence」(訳: チェーンの分析の基盤 Arkham Intelligence の最近のデータによれば)/「transferring 5,689 BTC into a cold storage wallet on March 16, 2024」(訳: 2024 年 3 月 16 日に 5,689 BTC を冷蔵の財布へ移した)。出所: https://cointelegraph.com/news/el-salvador-daily-bitcoin-purchases-bukele-strategy (ページ確認済み。2024-08-23 の記事)。あわせて、検索の返答に「IMF Insists El Salvador Isn't Buying Any More Bitcoin—So What's Going On?」(訳: IMF はエルサルバドルがもう BTC を買っていないと主張する — 何が起きているのか)という見出しの記事 https://decrypt.co/339035/imf-insists-el-salvador-not-buying-bitcoin が出た(ページ未確認。経路 WebSearch。購入が政府の新しい買いか、政府の財布の間の移し替えかに異論がある)。
- 意図の地図: 入る条件 = 政府の財布の保有が定時に一定量ずつ増える(定時の買い)の時刻(購入の時刻は未確認)。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 増える量(未定)。向き = 買い。この案は、政府を「売る人」でなく「定時に買う人」として持ち高の増え方を見る。
- なぜ: 誰が損をしているか = 定時の買いの相手(買いの時刻に売る人)。なぜ続くか = 政府の方針として毎日続く(出所の主張)。何で崩れるか = 量(1 日 1 BTC)が BTCUSD の板に比べて小さい。購入が移し替えで、新しい買いでない(IMF の主張、ページ未確認)。
- 期待する向きと場面: 場面 = 定時の買いの時刻。効く項 = BTCUSD。向き = 買い。
- 反証: 政府の財布の保有が増える時刻の前後で、BTCUSD の動きが他の時刻と違わない。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ。
- 水準とその出所: 原文の値は「毎日 1 BTC」。水準は未定(W4 で測る前に決める)。
- 使うデータと遅れ: 政府の財布のラベル(Arkham。経路と鍵の要否は未確認。エルサルバドル政府は自ら財布を公開しているという記述もある(検索の返答「the National Bitcoin Office recently reorganizing the country's holdings into 14 separate addresses」、ページ未確認))、BTC のチェーンの送金。
- 約定の模型: 未定。
- 注: D1-B-35・D1-B-36(売る側の未売却の保有量と減り方)と違う点: 買う側の政府の保有の増え方。

#### X2-B-90(升 P10-強制)

- 原文: 「Over 41.5%, or 59,000 Bitcoin (BTC), of the total of 141,686 BTC, has been redistributed to creditors」(訳: 全部で 141,686 BTC のうち 41.5% 超、59,000 BTC が債権者に配られた)/「the spot cumulative volume delta (CVD), a metric that measures the net difference between spot buying and selling trade volume on centralized exchanges」(訳: 現物の累積の出来高の差(CVD)。中央集権の取引所での現物の買いと売りの出来高の差し引きを測る指標)/「We can see a marginal uptick in sell-side pressure following the distribution. However, this remains well within typical day-to-day ranges.」(訳: 配布の後に、売り側の圧力のわずかな上向きが見える。ただし、これは普段の日々の範囲に十分収まっている)。出所: https://cointelegraph.com/news/mt-gox-creditors-hold-41-percent-bitcoin-distribution (ページ確認済み。2024-07-30 の記事)。あわせて検索の返答の文: 「more than 5,000 BTC worth approximately $329 million moved from the exchange to cold wallets」(訳: 約 3 億 2,900 万ドル相当の 5,000 BTC 超が、取引所から冷蔵の財布へ移された。ページ未確認。経路 WebSearch。出所の候補は cryptopotato・coin360 の記事)。
- 意図の地図: 入る条件 = 強制の配布(管財人から配布の担当の取引所へ)の後、配布を受けた取引所の (1) 現物の買いと売りの出来高の差(CVD)と (2) その取引所からの BTC の出金を見る(定義は未定)。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 出金の多さ・CVD の売りの大きさ(未定)。向き = 出金が多い(受け取った人が持ち続ける)なら売り圧の見込みを外す向き、CVD が売りに傾くなら売り。
- なぜ: 誰が損をしているか = 配布をそのまま「売り」と見て売る人、または逆に売りを見ずに買う人(仮定)。なぜ続くか = 配布は特定の取引所の口座へ入るので、受け取った人の行動(売るか出金するか)がその取引所の跡に集まる(出所の主張からの当てはめ)。何で崩れるか = 配布の担当の取引所が分からない。受け取った人が別の取引所へ移して売る。
- 期待する向きと場面: 場面 = 破産の財団・管財人の配布の後。効く項 = BTCUSD。
- 反証: 配布の後の出金・CVD の向きと、その後の BTCUSD の動きの向きに関係が無い。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ。日本の取引所が配布を担う場合は (b)(円の上乗せ)にもなる(Mt. Gox の配布の担当に日本の取引所が入ったかは、この周で確かめていない)。
- 水準とその出所: 原文の値は配布の量と割合(41.5%・59,000 BTC)で、水準ではない。未定(W4 で測る前に決める)。
- 使うデータと遅れ: 取引所ごとの約定(買いと売りの向き付き。経路は取引所ごと。未確認)、取引所の財布の出金(ラベルの経路は未確認)。
- 約定の模型: 未定。
- 注: X1-B-19(破産の財団の清算を段階的な売り圧として読む)と違う点: 配布を一律に売り圧とせず、受け取った人の行動(出金か売りか)を跡にして向きを分ける。

#### X2-B-91(升 P10-強制)

- 原文: 「nearly all of FTX's creditors, including hundreds of thousands of ordinary investors, would receive cash payments equivalent to 118 percent of the assets they had stored on FTX」(訳: FTX の債権者のほぼ全員が、何十万人もの普通の投資家を含め、FTX に預けていた資産の 118% に当たる現金の支払いを受ける)/「The amount owed to customers was based on the value of their holdings at the time of FTX's bankruptcy, so customers will not benefit from a recent surge in the crypto market.」(訳: 顧客への債務の額は、FTX の破産の時点の保有の価値に基づくので、顧客は最近の暗号資産の市場の急騰の恩恵を受けない)。出所: https://nysscpa.org/news/1046014-customers-of-bankrupt-ftx-to-get-all-their-money-back-2024-05-08 (ページ確認済み。2024-05-08 の記事)。あわせて検索の返答の文: 「Some crypto market observers speculated that this could result in a flood of new money entering the crypto markets if FTX creditors choose to immediately reinvest what they receive.」(訳: 暗号資産の市場を見る人の一部は、FTX の債権者が受け取ったものをすぐ再投資すれば、暗号資産の市場に新しいお金が流れ込みうると推測した。ページ未確認。経路 WebSearch。nysscpa と pymnts のページには、この文は無かった(WebFetch の返答))。
- 意図の地図: 入る条件 = 破産の財団が、債権者に BTC でなく現金(ドル・ステーブルコイン)で返す配布の日(配布の日程は裁判所の承認と財団の公表で前もって分かる)。出る条件 = 未定。保有中の判断 = 未定。強弱の付け方 = 現金の配布の額(未定)。向き = 買い(出所の推測: 受け取った人の再投資)。
- なぜ: 誰が損をしているか = 破産の財団の配布を一律に売り圧と見て売る人(仮定)。なぜ続くか = 返済の額が破産の時点の価値で決まり、債権者は急騰の恩恵を受けない(出所)ので、BTC を持ち直したい債権者は自分で買い直す(仮定)。何で崩れるか = 受け取った人が再投資しない。配布の額が BTCUSD の板に比べて小さい。
- 期待する向きと場面: 場面 = 現金の配布の日の後。効く項 = BTCUSD。向き = 買い。
- 反証: 現金の配布の日の後に、BTCUSD の動きとステーブルコインの取引所への流入が、他の期間と違わない。
- 段 3 の種類: (a) 海外で見える跡で bitFlyer を持つ。
- 水準とその出所: 原文の値は「118%」(返済の割合)で、水準ではない。未定(W4 で測る前に決める)。
- 使うデータと遅れ: 破産の財団の配布の日程(裁判所の記録・財団の公表。経路は未確認)、ステーブルコインの取引所への流入(未確認)。
- 約定の模型: 未定。
- 注: X1-B-19・D1-B-37・D1-B-35 と違う点: 強制の配布が BTC でなく現金のとき、売り圧ではなく買い側の流れになりうる、という向きの違い。

### 末尾

#### 升ごとの案の数

| 升 | 案の数 | 案の番号 |
|---|---|---|
| P12-関心 | 1 | X2-C-01 |
| P12-強制 | 3 | X2-C-02・X2-C-03・X2-C-04 |
| P13-移動 | 1 | X2-C-05 |
| P13-約定 | 3 | X2-C-06・X2-C-07・X2-C-08 |
| P14-移動 | 2 | X2-C-09・X2-C-10 |
| P14-約定 | 1 | X2-C-11 |
| P15-持ち高 | 2 | X2-C-12・X2-C-13 |
| P10-関心 | 2 | X2-B-81・X2-B-82 |
| P10-予告 | 3 | X2-B-83・X2-B-84・X2-B-85 |
| P10-移動 | 2 | X2-B-86・X2-B-87 |
| P10-約定 | 1 | X2-B-88 |
| P10-持ち高 | 1 | X2-B-89 |
| P10-強制 | 2 | X2-B-90・X2-B-91 |
| 計 | 24 | X2-C 13 案・X2-B 11 案 |

検索(WebSearch)の回数: 29 回(升の表の各行の語。複数の升に使った語は 1 回と数えた)。WebFetch: 39 回(転送の応答 1 件を含む)(うち本文が取れなかったもの: trade.xyz 404、indiehackers 403、cointelegraph(October crash)404、bitflyer.com 403、bnnbloomberg(本文なし)、bitbank 2 件(本文なし)、thedefiant(本文なし)、pymnts・nysscpa・liquidmercury・benjamincup(該当の文なし))。

#### 持ち越し

- 担当の 13 升はすべて検索を 2 回以上打ち、案を書いた。持ち越す升は無い。
- 持ち越す確かめ: (1) bitFlyer のかんたん積立の実行の時刻(ページが 403。X2-C-09 の前提)。(2) Bitquery の Polymarket の経路の鍵の要否(X2-C-05)。(3) Hyperliquid の `perpsAtOpenInterestCap`・HLP の建玉・ADL の記録の過去の履歴の有無(X2-C-01・02・04)。(4) 米連銀 H.4.1 の預かり残高の系列の経路と長さ(X2-C-12)。(5) 「ページ未確認」の引用 8 件の取り直し(Synthetix・coingecko・fc26・diamond・検索の返答の「納税売り」の文・forklog の 5,103 BTC・decrypt の IMF・cryptopotato の出金)。どれもこの周では叩いていない(期間の引数の無い bitFlyer の経路・鍵の要る経路は叩かない規則)。

#### 迷った点

1. 升ごとの時刻: 検索を升をまたいで並べて打ったため、升ごとの書き始めと書き終わりを別々に記録しなかった。表の時刻は全体の区間を写したもので、升ごとの所要時間には使えない。`date -u` の出力は 22:38:23Z・22:40:40Z・22:42:43Z・22:43:26Z(作業の実感より短い区間に見えるが、出力のまま書いた)。
2. X2-C-08 は出所が Polymarket の遅れの記述で、bitFlyer への当てはめは作業者が書いた(出所に bitFlyer は無い)。在庫の #28 と同じ形なので、案にするか重なりの欄だけにするか迷い、違う点(大きい動きに限る)があるので案にした。
3. X2-C-10 は跡が P14(国内の個人の移動)で、引き金が P15(介入)。升を P14-移動に置いたが、P15-約定にも当たる。
4. P15-持ち高の検索 (2) で、日銀の当座預金の見通しと短資会社の予想の差から介入額を推計する記述(newsweekjapan・sbbit ほか。検索の返答の文「介入金額は、短資会社による財政等要因の予想額と、日銀自身による財政等要因の予想額の差額で推計されます」、ページ未確認)が見つかった。これは介入の実行(P15-約定)の跡で担当の升の外なので、案にしなかった。round1 の P15-約定の在庫と同じかは確かめていない。
5. 出所の記事の多くは、過去の出来事(2024〜2026 年の送金・配布・介入)の報道である。案には機構の記述だけを取り、出所の過去の結果の値は「水準」に使わず「出所の主張」として書いた(L-019)。過去の結果を根拠にしていないかの線引きは、リードの読みに委ねる。
6. 升 P12-関心 の検索 (2) の返答にあった「market makers ended up stuffed with spot inventory and unhedged」は、返答が liquidmercury の文として出したが、ページに無かった。同じ趣旨の文は cryptoslate(X2-C-02・03 の原文)で確認した。
7. BitMEX のブログ(state-of-crypto-perps-2025)が P12-強制の検索 (3) に出たが、L-570 により開かなかった。

