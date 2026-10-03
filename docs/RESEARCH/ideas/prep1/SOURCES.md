# 出所の取り直しと訳(案の供給 第 1 周)

## §1 印のある引用の取り直し

作業開始 2026-10-03 14:18 UTC。取得はすべて 2026-10-03 の UTC(各行に時刻)。入力は scratchpad の `marked.md`(23 案)。原本の `round1/IDEAS_A.md`・`IDEAS_B.md` は書き換えていない。

### 着手前の表(CLAUDE.md §0.1)

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 「ページ未確認」「照合未了」の印のある引用を、ページから取り直す | 「**この文章の意味が何一つわからないので全て説明してください**」L-049(出所の分からない文章を出さない。O-6) |
| 引用の文が、取ったページの本文に逐語であるかを確かめる。違えばページの実際の文を逐語で書く | 「**これは「データを調査せずに取れない」というあなたの悪癖そのものです**」L-105 |
| 届かなかったものは、経路と応答(HTTP の状態・エラーの文)をそのまま書く | 「**これは「データを調査せずに取れない」というあなたの悪癖そのものです**」L-105 |
| 英語の逐語に日本語の訳を付ける | 「**日本人に読めない英語の出力してなんの意味があるの？2度と出すな**」L-126 |
| 引用の中の数値(水準)がページにあるかも確かめる | 「**バー 5bp の意味と根拠は何か**」L-047(出所の分からない数字を出さない。O-6) |
| 案の評価をしない・案を消さない・BitMEX と有料のページに入らない | 「**私が思いつく戦略と、私が思いつけないあなたが見つけた戦略を、片っ端から検証し**」L-019(消さない理由) |
| 締め切り UTC 15:40 で止め、残りを持ち越す | 「**なぜあいもかわらず無限の無意味な作業を続けてるんですか？**」L-451(I-013) |
| 取得のたび、`WebFetch` が使えない・失敗したものは `curl` に切り替える | **(該当語なし)** — 手段の選び方で、結果の中身を変えない(委任文の手順 1) |

右が空の行は 1 つ(取得の手段の切り替え)。委任文の手順に書かれた手段なので、問いにせずに進めた。

### 結果の表

凡例: 「ページの逐語」の英文は、取得したページの本文から機械で探して一致した文(空白と引用符の種類は正規化して比べた)。「違い」がある場合は行内に書いた。取得は、断りがなければ `curl -sS -L --max-time 30`(User-Agent を付けた)で、本文を HTML から文字にして探した。

| 案 | 原本の行 | 印のあった引用(逐語) | 取った経路(URL)と応答 | 結果 | ページの逐語 | 日本語の訳 |
|---|---|---|---|---|---|---|
| X1-A-05 | IDEAS_A.md 161 | 「When top traders are flat or short while retail is aggressively long, fade the retail side.」(印: ページ照合は取得に失敗して未了) | https://www.sharpe.ai/futures/bitcoin/long-short-ratio を `curl`(14:19:13、14:20:21、14:20:49、14:24:09 の 4 回)と `WebFetch` で取得。どれも HTTP 429。応答ヘッダに `server: Vercel`、`x-vercel-mitigated: challenge`(自動アクセスへの確認画面)。20 秒空けて再試行しても 429 | 届かなかった | (本文を取得できず、無し) | (同左)。参考: 同じ案の amberdata のページ(https://docs.amberdata.io/data-dictionary/market/longshort-ratio、HTTP 200、14:19:12)は、印の付いていない定義 3 文が逐語で一致した。判断の水準(何倍以上など)はこの周ではページから取れていない |
| X1-A-09 | IDEAS_A.md 315 | 「A whale deposited 15.47 million USDC into Hyperliquid to open 20x leveraged BTC and 10x leveraged BNB long positions」(印: 出所は mexc.com/news/ のどれか特定できず、410 で照合未了) | WebSearch でこの文を検索。検索結果に mexc.com/news/72167・101786・72240・609680・80128・191059・163295 が出た。それぞれ `curl` で HTTP 403(`Access Denied`、14:20:41)。`WebFetch` の mexc.com/news/72167 は HTTP 410 Gone。他の候補 https://www.techflowpost.com/en-US/newsletter/99377 は HTTP 200 だが本文に 15.47 が無い(`grep` で確認)。t.me/s/cppfta/2070・2071 は HTTP 200 だが本文に 15.47 が無い | 届かなかった | (逐語を確認できず)。検索ツールの返答の文は「according to PANews reported on August 24, a whale deposited 15.47 million USDC into Hyperliquid in the past 48 hours to open 20x leveraged BTC and 10x leveraged BNB long positions, as monitored by Onchain Lens」(ページの文ではなく検索の要約) | 検索の要約の訳: 「PANews の 8 月 24 日の報道によれば、ある大口が過去 48 時間に 1547 万 USDC を Hyperliquid に入金し、レバレッジ 20 倍の BTC と 10 倍の BNB のロングを建てた。Onchain Lens の監視による」。この訳はページの確認が無い文への訳 |
| X1-A-14 | IDEAS_A.md 436 | 「Due to the excessively large liquidation size, Hyperliquid HLP took over the position and is gradually unwinding it.」(印: 照合未了。出所の候補 theblock.co) | https://www.theblock.co/amp/post/345866/hype-drop-hlp-vault-loss-hyperliquid-whale-liquidation を `curl`: HTTP 403(14:19:14)。`WebFetch` では本文が取れ、この文は無い(「HLP took over the position」「gradually unwinding」とも本文に無いと返答)。同じ事件を書いた別のページ 3 つは HTTP 200: https://coin360.com/news/hyperliquid-4m-loss-whale-liquidation-manipulation、https://ambcrypto.com/did-this-whale-manipulate-hyperliquids-liquidation-system-for-profit/(14:22 ごろ) | 文が違った | coin360 のページ: 「Designed as a risk management mechanism, the vault took over the position at $1,915 per ETH and attempted to unwind it gradually.」ambcrypto のページ: 「The vault took over the ETH position at $1,915 per ETH and began gradually selling it off.」。引用の文そのものはどのページにも逐語では無い。違い: 引用は「HLP took over the position and is gradually unwinding it」で「Due to the excessively large liquidation size」から始まるが、取れたページは「the vault took over ... and attempted to unwind it gradually」(過去形・金庫と書く) | coin360 の文の訳: 「リスク管理の仕組みとして設計された金庫は、1 ETH あたり 1,915 ドルでそのポジションを引き取り、段階的に手仕舞おうとした」。ambcrypto の文の訳: 「金庫は 1 ETH あたり 1,915 ドルで ETH のポジションを引き取り、徐々に売り始めた」。元の引用の訳(ページ未確認の文): 「清算の規模が大きすぎたため、Hyperliquid の HLP がそのポジションを引き取り、徐々に手仕舞っている」 |
| X1-A-17 | IDEAS_A.md 513 | 「major transfers of coins from personal wallets to centralized exchanges are more often than not a signal of intent to sell by the whale who made the transfer」(印: 照合未了。候補 santiment) | https://insights.santiment.net/read/using-santiment-s-whale-deposit-centralized-exchange-dashboard-8463 を `curl`。HTTP 200(14:19:16)、転送先 https://app.santiment.net/insights/read/using-santiment-s-whale-deposit-centralized-exchange-dashboard-8463 | 照合済み | 「Major transfers of coins from personal wallets to centralized exchanges are more often than not a signal of intent to sell by the whale who made the transfer」。違い: 文頭の M が大文字(引用は小文字) | 「個人のウォレットから中央集権型の取引所への大口の移動は、たいてい、その移動をした大口が売る意図を持つ印である」 |
| X1-A-18 | IDEAS_A.md 546 | 「any trade ≥ 10 BTC」を大口の約定の境とする研究(印: ページは取得できず照合未了。候補 blog.kaiko.com) | https://blog.kaiko.com/an-analysis-of-whale-and-retail-trade-size-and-direction-7db548879292 を `curl`: HTTP 200 だが転送先が https://www.kaiko.com/resources/categories/data-blog(記事一覧で本文に該当の記事が無い)。`WebFetch` は HTTP 301 を返し https://www.kaiko.com/resources/data-blog への転送を告げた。この転送先は一覧で記事の本文ではないので取らなかった。二次の報道 2 件を `curl` で取得(HTTP 200): https://cointelegraph.com/news/okex-recorded-over-8-000-whale-bitcoin-trades-in-june、https://forklog.com/en/on-which-exchanges-do-bitcoin-whales-show-the-most-activity/(14:22) | 届かなかった(原ページ)。二次の報道では大口の境の数値を確認 | 原ページの逐語は取れていない。cointelegraph の本文: 「In Kaiko's nomenclature, "whale" trades are 10 BTC and above.」forklog の本文: 「We classify a trade as "whale" if its size exceeds 10 BTC.」。違い: 引用の「any trade ≥ 10 BTC」という語は二次のどちらにも逐語では無い。cointelegraph は「10 BTC 以上」、forklog は「10 BTC を超える」と境の扱い(以上か超か)が食い違う | cointelegraph の文の訳: 「Kaiko の呼び方では、『大口』の約定は 10 BTC 以上である」。forklog の文の訳: 「約定の大きさが 10 BTC を超えるものを『大口』に分類する」 |
| X1-A-23 | IDEAS_A.md 689 | 「Stop losses get hit because they were placed where everyone else placed theirs.」「a coordinate on a liquidity map」(印: 照合未了。出所の候補は mexc.com/news/1176680、410 で取得できず) | https://www.mexc.com/news/1176680 を `curl`: HTTP 403 `Access Denied`(14:19:19、14:20:48)。`WebFetch`: HTTP 410 Gone。同じ文で検索して出た他のページ(luxalgo.com の 1 ページ、nextbull.beehiiv.com、mql5.com/en/blogs/post/772639)は HTTP 200 で取得したが、2 つの文は逐語では見つからなかった(`grep` で確認。nextbull は「we place stops where everyone else does」) | 届かなかった | (逐語を確認できず)。検索ツールの返答の文は「Stop losses get hit because they were placed where everyone else placed theirs.」(検索の要約。ページの文ではない)。取れたページの近い文: nextbull の「We crave safety, so we place stops where everyone else does.」 | 検索の要約の訳: 「損切りが当たるのは、他の全員が置いたのと同じ場所に置かれていたからだ」「流動性の地図の上の座標」(どちらもページ未確認の文への訳)。nextbull の文の訳: 「私たちは安全を求め、他の全員と同じ場所に損切りを置く」 |
| X1-A-24 | IDEAS_A.md 722 | 「a whale may transfer assets for an outright sale, portfolio rebalancing, liquidity management, or other trading activity」(印: 照合未了。候補は blockchain.news の Lookonchain の項) | WebSearch で逐語の文を検索し、https://www.cryptometer.io/news/wp-json/wp/v2/posts/19739 と https://www.cryptometer.io/news/chainlink-whale-deposits-7-6-million-in-link-to-coinbase-as-exchange-transfers-mount/ を `curl`。どちらも HTTP 200(14:22)。blockchain.news のどの項かは特定していない(blockchain.news/flashnews/Exchange%20Inflow は HTTP 200 だが、この文は無い) | 照合済み(別のページ。出所の blockchain.news の項ではない) | cryptometer の本文: 「A whale may transfer assets for an outright sale, portfolio rebalancing, liquidity management, or other trading activity.」違い: 文頭の A が大文字。直後の文は「Therefore, the transactions do not provide definitive evidence of an imminent sell-off.」 | 「大口は、完全な売却、ポートフォリオの再調整、流動性の管理、その他の取引のために資産を動かすことがある」。直後の文の訳: 「したがって、これらの移動は、差し迫った売りの確かな証拠にはならない」 |
| X1-A-26 | IDEAS_A.md 788 | 「The divergence between the top and bottom cohorts is one of the most reliable contrarian signals available on-chain」(印: 照合未了。候補 hyperdash.com) | https://hyperdash.com/learn/best-tools-trading-hyperliquid を `curl`。HTTP 200(14:19:24) | 照合済み | 「The divergence between the top and bottom cohorts is one of the most reliable contrarian signals available on-chain」(逐語で一致) | 「上位と下位のコホートの食い違いは、オンチェーンで得られる最も信頼できる逆張りの信号の 1 つである」(出所の主張で、当方の評価ではない) |
| X1-A-28 | IDEAS_A.md 854 | CoinShares の 2025 年 10 月の調査で、BTC を最も有望と見る割合が下がり Solana と Ethereum が増えた、という記述(印: 照合未了。URL は特定できず。検索結果の要約) | WebSearch で調査を特定し、https://coinshares.com/insights/research-data/digital-asset-quarterly-fund-manager-survey-10-25/ を `curl`。HTTP 200(14:21:22) | 照合済み(趣旨。引用が逐語でなく要約なので、ページの文を併記) | 「Since the July survey, Bitcoin has experienced a sharp decline in the share of investors who see it as having the most compelling growth outlook. It remains the most preferred asset overall, although investor enthusiasm for Solana and Ethereum has risen significantly at Bitcoin's expense.」と見出しの下の要旨「Bitcoin remains the most held digital asset but has lost growth appeal to Ethereum and Solana」。数値(割合)は本文の文字からは取れていない(図の中と思われる。未確認) | 「7 月の調査以降、ビットコインを最も魅力的な成長の見通しがあると見る投資家の割合は急に下がった。全体では今も最も好まれる資産だが、ソラナとイーサリアムへの熱意はビットコインを犠牲にして大きく上がった」「ビットコインは最も保有される資産のままだが、イーサリアムとソラナに成長の魅力を奪われた」 |
| X1-A-30 | IDEAS_A.md 920 | 「cash-and-carry basis trades can generate flows that appear bullish even when net delta exposure remains near zero」(印: 照合未了。候補は検索結果の複数の記事) | WebSearch を 2 回。https://cointelegraph.com/news/crypto-etp-selling-slowdown-187-million-outflows-coinshares(HTTP 200、14:19:26)・https://decrypt.co/365604/...・https://www.theblock.co/post/299701/glassnode-says-institutional-cash-and-carry-trades-are-influencing-us-spot-bitcoin-etf-flows(`curl` は HTTP 403)・https://nexusfi.com/a/cryptocurrency/spot-bitcoin-etfs-futures-traders(HTTP 403)・https://jamesbachini.com/?p=7429(HTTP 522)を取得。取れたページに、この文は逐語では無い | 届かなかった(逐語の出所のページを特定できず) | (逐語を確認できず)。検索の要約: 「Inflows can represent the spot leg of a delta-neutral basis trade」(検索ツールの要約の文。ページの文ではない) | 検索の要約の訳: 「流入は、デルタ中立のベーシス取引の現物側を表すことがある」(ページ未確認の文への訳)。引用の訳(ページ未確認): 「キャッシュ・アンド・キャリーのベーシス取引は、正味のデルタの持ち高がほぼゼロのままでも、強気に見えるフローを生むことがある」 |
| X1-A-31 | IDEAS_A.md 953 | 利回りの差が 10% のハードルを下回ると、ETF の流入は裁定のファンドではなく方向性の投資家による、という読み(印: 照合未了。候補は amberdata・fxstreet の記事) | WebSearch で検索し、https://coinspectator.com/?p=281482 を `curl`。HTTP 200(14:22)。amberdata・fxstreet のページは取っていない | 照合済み(別のページ。候補の amberdata・fxstreet ではない) | 「"When yield spreads fall below a 10% hurdle rate, Bitcoin ETF inflows are typically driven by directional investors rather than arbitrage-focused hedge funds. This dynamic often coincides with price consolidation. Currently, these spreads are down to 1.0% (perpetual futures funding rate) and ...」(記事が引用符で別の人の発言として載せている文。数値 10% は逐語で一致) | 「利回りの差が 10% のハードルを下回ると、ビットコイン ETF への流入は、たいてい、裁定を狙うヘッジファンドではなく方向性の投資家によるものになる。この動きは価格の持ち合いと重なることが多い。現在、この差は 1.0%(無期限先物の資金調達率)と…まで下がっている」 |
| X1-A-32 | IDEAS_A.md 986 | 「Leveraged funds reduced their net short position by 5,566.5 bitcoin ...」「A leveraged fund's short position can be a simple bet on falling prices. ...」「makes it hard to tell from the report alone whether the move reflects directional trading, a basis trade, a shift in maturities, or a mix of those factors」(印: 数値は出来事の値。ページ照合は未了と読める) | https://www.digitaltoday.co.kr/en/view/88211/bitcoin-futures-short-selling-eases-but-etfs-and-perpetual-futures-remain-tepid を `curl`: 1 回目は `curl: (35) Recv failure: Connection reset by peer`(14:19:32)、`User-Agent` を替えた 2 回目は HTTP 200(14:20:23) | 照合済み(3 文とも逐語で一致。数値 5,566.5 も一致) | 「Leveraged funds reduced their net short position by 5,566.5 bitcoin in bitcoin futures on the Chicago Mercantile Exchange (CME).」「A leveraged fund's short position can be a simple bet on falling prices. It can also be part of an arbitrage strategy linking spot and futures, or a hedge to defend other positions. That makes it hard to tell from the report alone whether the move reflects directional trading, a basis trade, a shift in maturities, or a mix of those factors.」。違い: 引用の 3 つ目は文の途中から(「That」を省く) | 「レバレッジをかけたファンドは、シカゴ・マーカンタイル取引所(CME)のビットコイン先物で、正味の売り持ちを 5,566.5 ビットコイン減らした」「レバレッジをかけたファンドの売り持ちは、単純な下落への賭けであることがある。現物と先物をつなぐ裁定戦略の一部や、他の持ち高を守るヘッジであることもある。そのため、報告書だけでは、その動きが方向性の取引、ベーシス取引、満期の入れ替え、またはそれらの組み合わせのどれを反映しているのか、判断しにくい」 |
| X1-B-3 | IDEAS_B.md 143 | 「a flattening or declining top line means institutional accumulation has stalled or reversed」(印: 検索の返答の文(ページ未確認)) | 候補 https://newhedge.io/product/bitcoin-etf-data を `curl` と `WebFetch` で取得: どちらも HTTP 403。https://bitcointreasuries.com/us-etfs/ を `curl`: HTTP 200 で https://bitbo.io/treasuries/us-etfs/ へ転送(14:19:34)、本文にこの文は無い。WebSearch(この文そのもの)では、検索の返答がこの文を載せたが、載っていたページは edgerater.com・tradingview.com・thearmchairtrader.com・binance.com/square・ambcrypto.com・bitcoinstrategy.substack.com の一覧で、うち thearmchairtrader.com・ambcrypto.com・bitcoinstrategy.substack.com を `curl` で取った(HTTP 200)が本文にこの文は無い | 届かなかった | (逐語を確認できず)。検索の返答の文は「A flattening or declining top line in ETF holdings means institutional accumulation has stalled or reversed, which historically has preceded or accompanied price weakness.」(検索の要約。どのページの文かは未特定) | 検索の要約の訳: 「ETF の保有量の線が頭打ちまたは減少に転じたなら、機関の蓄積が止まったか反転したことを意味し、歴史的に価格の弱さに先立つか伴ってきた」(ページ未確認の文への訳) |
| X1-B-4 | IDEAS_B.md 186 | 「Divergences between the price of Bitcoin and DVOL/BVIV can signal inflection points. Price rising with a drop in DVOL/BVIV may indicate exhaustion and a potential top. Price falling with a drop in DVOL/BVIV may indicate exhaustion and a potential bottom.」(印: 検索の返答の文(ページ未確認)。一覧ページ 2 つでは取れていなかった) | WebSearch の結果の題「How to use Implied Volatility Index to analyze Bitcoin」の個別ページ https://it.tradingview.com/chart/BTCUSD/MVeSC3Tr-How-to-use-Implied-Volatility-Index-to-analyze-Bitcoin を `curl`。HTTP 200(14:20:20) | 照合済み | 「Divergences between the price of Bitcoin and DVOL/BVIV can signal inflection points.」「Price rising with a drop in DVOL/BVIV may indicate exhaustion and a potential top.」「Price falling with a drop in DVOL/BVIV may indicate exhaustion and a potential bottom.」(3 文とも逐語で一致。各文の頭に絵文字の印 🔶 が付く。ページは TradingView の投稿で、題は「How to use Implied Volatility Index to analyze Bitcoin」) | 「ビットコインの価格と DVOL/BVIV の乖離は、転換点を知らせることがある」「価格が上がっているのに DVOL/BVIV が下がっていれば、息切れと天井の可能性を示しうる」「価格が下がっているのに DVOL/BVIV が下がっていれば、息切れと底の可能性を示しうる」 |
| X1-B-6(補足) | IDEAS_B.md 264 | 「GEX is a regime indicator: positive-gamma regimes favor mean-reverting strategies (premium-selling near established ranges); negative-gamma regimes favor momentum and breakout strategies.」(印: 補足は検索の返答の文(ページ未確認)。本文の 3 文は「ページ確認済み」で印なし) | https://research.glassnode.com/gamma-exposure は HTTP 200(転送先 .../gamma-exposure/、14:19:35)で、本文に補足の文は無い。WebSearch が返した https://flashalpha.com/articles/gex-trading-system-playbook-negative-gamma-flip-rules は HTTP 200(14:21:21)だが本文に無い。同じ検索で出た optionsanalysissuite.com の 2 ページ(/stocks/geo/gamma-exposure と /etf/xsvm/gamma-exposure)は `curl` で HTTP 429(14:22、14:24) | 届かなかった | (逐語を確認できず)。参考: Glassnode のページの実際の文は「A particularly important dynamic is the gamma flip , when net GEX around spot changes sign. For example, if price exits a positive-gamma zone and moves into a pocket of negative gamma below, the market can transition from a pinned, mean-reverting regime to one where moves begin to reinforce themselves.」(本文の 3 文のうちの 3 つ目。空白 1 つの違いだけで一致) | Glassnode の文の訳: 「特に重要な動きがガンマ反転で、現値の周りの正味の GEX の符号が変わるときである。たとえば、価格が正ガンマの帯を出て、下にある負ガンマの帯に入ると、市場は、固定されて平均回帰する場面から、値動きが自らを強める場面に移りうる」。補足の文の訳(ページ未確認): 「GEX は場面の指標であり、正ガンマの場面は平均回帰の戦略に、負ガンマの場面は順張りとブレイクアウトの戦略に向く」 |
| X1-B-7(補足) | IDEAS_B.md 304 | 「there s a huge usd14 billion bitcoin options expiry this friday and it points to usd75 000 as price magnet」(印: 検索結果の見出し、ページ未確認) | https://www.coindesk.com/markets/2026/03/25/there-s-a-huge-usd14-billion-bitcoin-options-expiry-this-friday-and-it-points-to-usd75-000-as-price-magnet を `curl`。HTTP 200(14:19:37)。`WebFetch` でも見出しを取得 | 照合済み | 見出し: 「There's a huge $14 billion bitcoin options expiry this Friday and it points to $75,000 as price magnet」。違い: 引用は URL の綴り(記号が落ちた形)で、ページの見出しは「$」「,」「'」が付く。本文に「The "max pain" level for this expiry is around $75,000, which Deribit says may act as a price magnet as market makers hedge and large option writers try to minimize payouts.」 | 見出しの訳: 「今週金曜に 140 億ドル規模のビットコインのオプションの満期があり、7 万 5,000 ドルが価格の磁石になると示している」。本文の文の訳: 「この満期の最大苦痛価格は 7 万 5,000 ドルあたりで、Deribit は、マーケットメイカーがヘッジし、大口のオプションの売り手が支払いを最小にしようとするため、価格の磁石として働きうると言う」 |
| D1-B-17 | IDEAS_B.md 350 | 機構の文「発行体の財務ウォレットへの mint は、次の期間の発行要求とチェーン間の交換のための在庫として承認されるだけで、時価総額に入らない場合がある。…」(印: Tether の CEO の説明を検索で確認、ページ未確認) | WebSearch で CEO の説明を検索し、https://cryptoslate.com/tether-mints-1b-new-non-circulating-usdt-to-replenish-inventory/ を `curl`。HTTP 200(14:21:17)。cointelegraph の候補 URL は HTTP 404 | 照合済み(CEO の発言。時価総額に入らない点は別の記述) | CEO の発言(X の投稿)の引用: 「PSA: 1B USDt inventory replenish on Ethereum Network. Note this is an authorized but not issued transaction, meaning that this amount will be used as inventory for next period issuance requests and chain swaps.」見出し下: 「Tether CEO Paolo Ardoino shared on social media that the minting was "an authorized but not issued transaction," meaning the tokens remain out of circulation for now.」。「時価総額に入らない」という文は、このページの引用部分には逐語では見つかっていない(検索の要約に「not part of the total market capitalization」とあるのみ。ページ未確認) | 「お知らせ: イーサリアムのネットワークで 10 億 USDt の在庫補充。これは『承認されたが未発行』の取引であり、この額は次の期間の発行要求とチェーン間の交換のための在庫として使われる」。見出し下の訳: 「Tether の CEO は、この mint が『承認されたが未発行の取引』であり、トークンは当面流通の外にとどまると SNS に書いた」 |
| D1-B-20 | IDEAS_B.md 417 | 方針の「利益の一部の割合」の「最大 15%」(印: 検索の返答の文(ページ未確認)) | WebSearch で検索し、https://nobsbitcoin.com/tether-ramps-up-bitcoin-investments を `curl`。HTTP 200(転送先 https://www.nobsbitcoin.com/tether-ramps-up-bitcoin-investments/、14:21:19) | 照合済み(数値 15% が逐語である)。機構の文の「四半期の証明書の基準日に沿って出る」はページで確認できていない(案の中で【仮定】と書かれたまま) | 「Today, Tether announces its commitment to use up to 15% of its newly monthly net operating profits (ie. accounting the realized dollarized profits coming from t-bill and similar investments) to purchase bitcoin as part of its excess reserves.」記事の題: 「Tether To Invest Up To 15% Of Monthly Operating Profits In Bitcoin」(2023-05-17)。違い: 出所は「月次」の純営業利益と書く(検索の返答の文は「四半期」と書いていた) | 「本日、Tether は、新たに生じる月次の純営業利益(すなわち、短期国債などの投資から生じる実現した、ドルに換算した利益を数えたもの)の最大 15% を、超過準備の一部としてビットコインの購入に充てると約束することを発表する」 |
| X1-B-10 | IDEAS_B.md 402 | 「If the new USDT moves from the treasury to intermediary wallets and then onto exchanges like Binance or Coinbase, it signals that traders are positioning to convert stablecoins into other cryptocurrencies.」(印: 検索の返答の文(ページ未確認)。https://www.mexc.com/news/241760 は 410) | https://www.mexc.com/news/241760 を `curl`: HTTP 403 `Access Denied`(14:19:37)。この文で再検索して出た mexc.com/news/635540・442168・68199・375496 は取っていない(上の mexc が全て HTTP 403 だったため)。非 mexc の候補 https://cryptobriefing.com/tether-mints-1b-usdt-treasury/ と https://cointelegraph.com/news/tether-crypto-exchanges-balance-record-high-treasury-1b を `curl`: どちらも HTTP 200(14:22)だが本文にこの文は無い(「intermediary wallets」で `grep`) | 届かなかった | (逐語を確認できず)。検索ツールの返答の文は引用と同じ(検索の要約。ページの文ではない) | 引用の訳(ページ未確認): 「新しい USDT が財務ウォレットから中間のウォレットを経て Binance や Coinbase のような取引所に動くなら、トレーダーがステーブルコインを他の暗号資産に換える準備をしていることを示す」 |
| D1-B-27 | IDEAS_B.md 579 | 「非上場のマイナー(上場の約 2 割とされる記述が検索結果にある。ページ未確認)」 | WebSearch で検索し、https://forklog.com/en/jpmorgan-expects-miners-pressure-on-bitcoin-price-to-persist/(HTTP 200、14:21:20)と https://k33.com/research/archive/articles/miners-have-started-to-dump-their-bitcoin-holdings(HTTP 200、14:21:23)を `curl` | 照合済み(ただし 2 割はハッシュレートの割合。売り圧の割合ではない) | forklog: 「According to the expert, public mining companies account for about 20% of the hashrate.」k33: 「The public miners only make up around 20% of Bitcoin's hashrate but studying their behavior can hint at what the private miners are doing.」違い: 案の文は「非上場のマイナー(上場の約 2 割)」と書くが、ページは「上場のマイナーがハッシュレートの約 2 割」と書き、非上場はその残りである。案の括弧の読みは入れ替わっている(上場が約 2 割、非上場が約 8 割と読める) | forklog の訳: 「専門家によれば、上場のマイニング企業はハッシュレートの約 20% を占める」。k33 の訳: 「上場のマイナーはビットコインのハッシュレートの約 20% を占めるにすぎないが、その行動を調べると、非上場のマイナーが何をしているかの手がかりになる」。併記された forklog の文: 「in May publicly traded mining companies for the first time sold all Bitcoin mined during the month. Typically, the share of coins sold ranged from 25% to 40%.」(訳: 「5 月に、上場のマイニング企業は初めて、その月に掘ったビットコインをすべて売った。ふだん売る割合は 25% から 40% だった」) |
| X1-B-17(補足) | IDEAS_B.md 630 | 「The buy signal fires when the 30-day MA crosses back above the 60-day MA.」(印: 検索の返答の文(ページ未確認)) | https://www.spark.money/glossary/hash-ribbon を `curl`。HTTP 200(14:19:38) | 照合済み | 「The buy signal fires when the 30-day MA crosses back above the 60-day MA.」(逐語で一致) | 「買いの信号は、30 日の移動平均が 60 日の移動平均を再び上に抜けたときに出る」 |
| D1-B-38 | IDEAS_B.md 761 | 「Institutions are likely to acquire the crypto holdings through OTC deals rather than on exchanges」(印: 検索の返答の文(ページ未確認)。FTX の清算の記事) | WebSearch で検索し、https://www.fxstreet.com/cryptocurrencies/news/ftx-exchanges-36-billion-crypto-liquidation-unlikely-to-cause-bloodbath-in-solana-ethereum-aptos-prices-202309140932 を `curl`・`WebFetch` で、amp 版 URL を `WebFetch` で取得。すべて HTTP 403 | 届かなかった | (逐語を確認できず)。検索の要約: 「Galaxy Digital is likely to sell the assets via Over-The-Counter (OTC) deals, while exchange-based selling is unlikely, according to Jeff Dorman, CIO of investment firm Arca」(検索ツールの要約。ページの文ではない) | 検索の要約の訳: 「投資会社 Arca の CIO ジェフ・ドーマンによれば、Galaxy Digital は資産を店頭(OTC)の取引で売るとみられ、取引所での売りは考えにくい」。引用の訳(ページ未確認): 「機関は、取引所でなく OTC の取引で暗号資産を取得するとみられる」 |

### 数え(この周で取り直した引用 22 行)

| 結果 | 行数 | 該当する案 |
|---|---|---|
| 照合済み | 12 | X1-A-17、X1-A-24、X1-A-26、X1-A-28、X1-A-31、X1-A-32、X1-B-4、X1-B-7、D1-B-17、D1-B-20、D1-B-27、X1-B-17 |
| 文が違った | 1 | X1-A-14 |
| 届かなかった | 9 | X1-A-05、X1-A-09、X1-A-18、X1-A-23、X1-A-30、X1-B-3、X1-B-6、X1-B-10、D1-B-38 |

注: 照合済みの 12 行のうち X1-A-24 と X1-A-31 は、案が挙げた候補のページではなく別のページで一致した。X1-A-28 は引用が要約なので趣旨の一致。X1-A-18 は原ページに届かず二次の報道で境の数値が出たため届かなかったに数えた。D1-B-17 は CEO の発言は一致、時価総額に入らない点はページの逐語では未確認。D1-B-27 は案の括弧の読みとページの内容が入れ替わっている点を表に書いた。

### 持ち越し、迷った点

持ち越し(この周で終えていないもの)。

1. X1-A-05: sharpe.ai が Vercel の自動アクセスの確認画面で HTTP 429。ブラウザ相当の経路が無いと取れない。取れていないので、判断の水準(「何倍以上」など)もページから取れていない。
2. X1-A-09・X1-A-23・X1-B-10: mexc.com は `curl` で全て HTTP 403(Access Denied)、`WebFetch` で HTTP 410。逐語の出所を mexc 以外で特定できていない。X1-A-09 の PANews の元記事、X1-A-23 の 2 文の元ページ、X1-B-10 の元ページは未特定。
3. X1-A-30・X1-B-3・D1-B-38: 検索の要約の文はあるが、逐語を載せたページを特定できていない(theblock.co、newhedge.io、fxstreet.com が 403)。
4. X1-A-14: The Block のページの本文は `WebFetch` の要約経由でしか見ておらず、`curl` は HTTP 403。引用の文が無かったのは `WebFetch` の返答による。生の本文での確認は未了。
5. X1-A-18: Kaiko の元の記事(blog.kaiko.com)は一覧ページへ転送され本文に届かない。
6. X1-A-21(「言及が価格に先行する場合は見つかっていない」という なぜ の欄の記述)・X1-A-23(公開トレーダーが損切りの価格を宣言するとフォロワーが同じ価格に置く、という記述)・X1-A-32(資産運用は長期で動きが遅く、レバレッジ勢が最も速く再配分する、という別の記事の読み)・X1-A-17(取得した文面の要約部分)は、引用の形をしていないか出所が特定できず、この周では取り直していない。
7. X1-A-28 の CoinShares の調査の割合の数値(本文の文字にはなく、図の中と思われる)。
8. 照合済みの行は、`curl` で取った HTML を文字にして一致を探した。ページの表示と一致するかはブラウザで見ていない。

迷った点。

1. 「文が違った」と「届かなかった」の境: X1-A-30・X1-B-3・X1-B-6(補足)は、ページ自体は取れたが文が無く、出所のページを特定できていない。「ページの実際の文を逐語で書く」ことができないので、届かなかったに入れた。
2. X1-A-24 と X1-A-31 は、候補のページではなく別のページで同じ文を見つけた。案の出所を書き換えるかは、リードの判断に任せる(round1 のファイルは書き換えていない)。
3. 案の英文の引用に、末尾の句読点・大文字・引用符の種類・URL の綴り(記号の脱落)の違いがあるものは、文が同じなら照合済みとして違いを行内に書いた。

## §2 英語の逐語の訳

### 着手前の表(CLAUDE.md §0.1)

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| IDEAS_A・C・D の英語の逐語(「」や "" で囲まれた英語)を機械的に全部拾う | L-126「**日本人に読めない英語の出力してなんの意味があるの？2度と出すな**」 |
| 引用ごとに、案の番号・原本の行・英語の逐語・日本語の訳を表にする(直訳寄り、要約しない、足さない) | L-126「**日本人に読めない英語の出力してなんの意味があるの？2度と出すな**」 |
| IDEAS_B で訳の無い英語の逐語が見つかれば加える | L-126(同上) |
| 件数を機械で数えて表と合わせる | L-057「**あなたの断定癖は私ですら注意していないと見過ごしてしまう**」 |
| ページの照合・取り直しはしない | (該当語なし。作業の指示書で範囲を切られている。照合は別の作業者の担当) |

右が空の行は 1 つ(ページの照合をしないこと)。指示書の範囲の切り方であり、訳の中身を変える判断ではないので、そのまま進めた。

### 拾い方

英語の逐語の定義: 「…」または "…" または “…” で囲まれ、その中に日本語の文字が無く、英字 2 文字以上の語を含む文字列。日本語の文字が混じる引用(日本語の文の引用、日本語の説明文)は英語の逐語ではないので拾わない。引用の中の入れ子の '…'(たとえば 'typically a bullish sign')は、外側の引用の一部として 1 行に入れ、単独の行にしていない。

拾ったコマンド(Python。出力の `out.json` が拾った全件。案の番号は直前の見出し `^#{2,4} (D1|X1)-<組>-<連番>`):

```
python3 ext.py IDEAS_A.md IDEAS_C.md IDEAS_D.md IDEAS_B.md
  # 正規表現: 「([^」]*)」|"([^"]*)"|“([^”]*)”  を各行に適用し、
  #   英字 2 文字以上の語を含み、日本語文字(ひらがな・カタカナ・漢字・全角記号)を含まないものを採用
  # 出力: 276 69   (英語の逐語 276 件 / 日本語が混じるため除外 69 件。4 ファイルの合計)
```

組ごとの内訳(`collections.Counter`): IDEAS_A.md 135 件、IDEAS_C.md 28 件、IDEAS_D.md 65 件、IDEAS_B.md 48 件。

IDEAS_B の 48 件のうち、直後の `- 訳:` の行または同じ行の `(訳: …)` で訳が付いているものは 40 件(各行を読んで確認した)。訳が無いのは 8 件で、この表に加えた: 9 行(凡例中の「bullish」)・40 行(検索語)・190 行(記事の題)・276 行(記事の題)・309 行(見出し)・652 行(方針の一節)・700 行(報道の一文。712 行に同じ文の訳がある)・775 行(見出し)。

IDEAS_A・C・D の 3 ファイルには、英語の逐語に付いた訳は 1 件も無かった(`grep -c "訳"` の A 11 行・C 2 行・D 2 行は「内訳」という語に当たったもので、英語の訳ではない(`grep -n "訳"` で全 15 行を読んだ))。

### 表

訳は直訳寄り。出所の語の評価(「強気」「信号」など)は出所の文であり、本組の主張ではない。表の「案の外」の行は、案ではなく凡例の文。

| 案 | 原本の行 | 英語の逐語 | 日本語の訳 |
|---|---|---|---|
| X1-A-01 | IDEAS_A.md:30 | Allocate 1% of your capital to Bitcoin on days when the index reads 20 or below, and sell 1% of your Bitcoin holdings on days when the index reaches 80 or above. | 指数が 20 以下を示す日にはあなたの資金の 1% をビットコインに配分し、指数が 80 以上に達する日にはあなたが持つビットコインの 1% を売る。 |
| X1-A-01 | IDEAS_A.md:30 | Price Volatility | 価格の変動性 |
| X1-A-01 | IDEAS_A.md:30 | Momentum and Volume | 勢いと出来高 |
| X1-A-01 | IDEAS_A.md:30 | Social Media Sentiment | SNS のセンチメント |
| X1-A-01 | IDEAS_A.md:30 | Bitcoin Dominance | ビットコインのドミナンス |
| X1-A-01 | IDEAS_A.md:30 | Google Trends | Google トレンド |
| X1-A-02 | IDEAS_A.md:52 | Quinlivan said the metric is 'typically a bullish sign' as markets 'historically move in the opposite direction of retail's expectations.' | クインリヴァン氏は、この指標は「典型的には強気の兆し」であり、市場は「歴史的に、個人の期待とは反対の方向に動く」と述べた。 |
| X1-A-02 | IDEAS_A.md:52 | The Positive vs. Negative Sentiment Ratio divides all positive sentiment comments across social media by all negative sentiment comments | ポジティブ対ネガティブのセンチメント比は、SNS 全体の肯定的なセンチメントのコメントのすべてを、否定的なセンチメントのコメントのすべてで割ったものである |
| X1-A-03 | IDEAS_A.md:85 | Net = In - Out | ネット = 流入 − 流出 |
| X1-A-03 | IDEAS_A.md:85 | we can plot our days of high inflow/outflow over the price of Bitcoin | 流入・流出が大きかった日を、ビットコインの価格の上に描くことができる |
| X1-A-03 | IDEAS_A.md:85 | if we observe a daily change in net inflow or outflow greater than 3 sigma, then it is a significant amount of flow | ネットの流入または流出の日次の変化が 3 シグマより大きいことを観測したら、それは有意な量のフローである |
| X1-A-03 | IDEAS_A.md:85 | 60 SMA and 3 sigma BB | 60 日 SMA と 3 シグマのボリンジャーバンド |
| X1-A-03 | IDEAS_A.md:85 | it takes the current algorithm a day to recognize the change in flows. By that time it is likely already too late | 現在のアルゴリズムがフローの変化を認識するのに 1 日かかる。その時点ではすでに遅すぎる可能性が高い |
| X1-A-03 | IDEAS_A.md:85 | high BitMEX outflow is typically accompanied by a sharp downturn in price | BitMEX からの大きな流出は、典型的には価格の急な下落を伴う |
| X1-A-04 | IDEAS_A.md:118 | At 15-minute horizons, directional mean reversion is far stronger and more pervasive in cryptocurrency markets than in US equities | 15 分の時間軸では、方向性のある平均回帰は、米国株式より暗号資産市場のほうがはるかに強く、広く見られる |
| X1-A-04 | IDEAS_A.md:118 | On the originating tape, the reversal concentrates after moves driven by aggressive taker flow and grows with flow intensity, while the order-book depth a move consumes conditions nothing: a conditioning consistent with compensated liquidity provision, not a test that selects it. | 元のテープでは、反転は積極的なテイカーのフローに動かされた値動きのあとに集中し、フローの強さとともに大きくなる。一方、値動きが消費した板の厚みは何も条件づけない。これは対価を得る流動性提供と整合する条件づけであって、それを選び出す検定ではない。 |
| X1-A-04 | IDEAS_A.md:118 | simply betting against the previous candle captures most of the effect | 直前のローソク足の逆に賭けるだけで、効果の大部分が捉えられる |
| X1-A-04 | IDEAS_A.md:119 | flow intensity | フローの強さ |
| X1-A-05 | IDEAS_A.md:162 | Long/short ratio across all accounts on the exchange. | 取引所の全アカウントにわたるロング/ショート比。 |
| X1-A-05 | IDEAS_A.md:162 | Long/short ratio by dollar-weighted position size among the top 20% of traders by margin balance. | 証拠金残高で上位 20% のトレーダーの、ドル加重のポジションサイズによるロング/ショート比。 |
| X1-A-05 | IDEAS_A.md:162 | The two metrics can diverge meaningfully, and that divergence itself can be a useful signal. | この 2 つの指標は大きく乖離することがあり、その乖離そのものが有用な信号になりうる。 |
| X1-A-05 | IDEAS_A.md:162 | When top traders are flat or short while retail is aggressively long, fade the retail side. | 上位のトレーダーがフラットまたはショートで、個人が積極的にロングのときは、個人の側の逆を張れ。 |
| X1-A-06 | IDEAS_A.md:206 | As price approaches these clusters, market stress intensifies, making them key zones for anticipating sharp moves. | 価格がこれらの集団に近づくと、市場のストレスが強まり、それらは急な動きを予想する重要な領域になる。 |
| X1-A-06 | IDEAS_A.md:206 | When many traders share similar liquidation thresholds, these areas become structurally fragile: once price moves into them, position unwinds can cascade and accelerate volatility. | 多くのトレーダーが似た清算の閾値を持つとき、これらの領域は構造的に脆くなる。価格がそこへ入ると、ポジションの巻き戻しが連鎖して変動を加速しうる。 |
| X1-A-06 | IDEAS_A.md:206 | For each observation, we track the largest open Bitcoin positions, which together correspond to the majority of liquidable BTC open interest on the platform | 観測ごとに、最大の建玉のビットコインのポジションを追跡する。それらは合わせて、このプラットフォームで清算されうる BTC の建玉の大部分に相当する |
| X1-A-06 | IDEAS_A.md:206 | Our metric set is built on top of Hyperliquid | 当方の指標群は Hyperliquid の上に作られている |
| X1-A-06 | IDEAS_A.md:206 | very large liquidation days often mark local exhaustion | 非常に大きい清算の日は、しばしば局所的な枯渇を示す |
| X1-A-07 | IDEAS_A.md:250 | A leveraged long has a price where the position can be forced out. If that level is visible, other traders can monitor it. | レバレッジをかけたロングには、ポジションが強制的に出される価格がある。その水準が見えるなら、他のトレーダーはそれを監視できる。 |
| X1-A-07 | IDEAS_A.md:250 | If enough traders monitor it, the level can attract more attention than it would have if the position stayed private. | 十分な数のトレーダーがそれを監視すれば、その水準は、ポジションが非公開のままだった場合より多くの注目を集めうる。 |
| X1-A-07 | IDEAS_A.md:250 | Some traders may use it as a risk marker. Others may try to fade the crowd or copy the same direction until the position becomes part of a public narrative. | それをリスクの目印として使うトレーダーもいる。群衆の逆を張ろうとする者や、ポジションが公の話題になるまで同じ方向を真似ようとする者もいる。 |
| X1-A-07 | IDEAS_A.md:250 | A liquidation level that once belonged mainly to the trader and the venue can now circulate through dashboards, screenshots, X posts, and chat rooms before the price gets there. | かつては主にトレーダーと取引所のものだった清算の水準が、価格がそこへ着く前に、ダッシュボード、スクリーンショット、X の投稿、チャットルームを巡りうるようになった。 |
| X1-A-07 | IDEAS_A.md:250 | The result is a faster feedback loop in which more traders can decide whether the level is a warning, an opportunity, or noise. | その結果、より多くのトレーダーが、その水準が警告か、機会か、ノイズかを判断できる、より速いフィードバックのループになる。 |
| X1-A-07 | IDEAS_A.md:250 | Why viral public whale liquidations are becoming a real trading signal on Hyperliquid | なぜ、公に見える大口の清算が Hyperliquid で実際の取引信号になりつつあるのか |
| X1-A-08 | IDEAS_A.md:283 | If a price approaches the wall and the wall is suddenly canceled or moved higher without being filled, it is flagged as a 'Spoof Wall.' | 価格が壁に近づいたとき、壁が約定されないまま突然取り消されるか高い側へ動かされた場合、それは「スプーフの壁」として印が付けられる。 |
| X1-A-08 | IDEAS_A.md:283 | Traders look for 'Buy Walls' at support levels to gauge if a whale is 'defending' a price or simply creating a 'fake floor' to lure in buyers before pulling the liquidity and allowing the price to dump. | トレーダーは、大口が価格を「守っている」のか、それとも買い手をおびき寄せるために「偽の床」を作り、流動性を引き上げて価格を落とさせようとしているだけなのかを測るため、支持線の水準にある「買いの壁」を探す。 |
| X1-A-08 | IDEAS_A.md:283 | on L2 you cannot tell a cancellation from a fill because both simply reduce the level | L2 では、取り消しと約定を区別できない。どちらも単にその水準を減らすからである |
| X1-A-09 | IDEAS_A.md:316 | a Hyperliquid whale has just deposited 11 million USDC, bringing total deposits over the past 24 hours to $16 million | Hyperliquid の大口が 1100 万 USDC を入金したところで、過去 24 時間の入金の合計は 1600 万ドルになった |
| X1-A-09 | IDEAS_A.md:316 | A whale deposited 15.47 million USDC into Hyperliquid to open 20x leveraged BTC and 10x leveraged BNB long positions | 大口が 1547 万 USDC を Hyperliquid に入金し、20 倍レバレッジの BTC と 10 倍レバレッジの BNB のロングを建てた |
| X1-A-10 | IDEAS_A.md:349 | Whale trade frequency increases during VPIN spikes — they ARE the informed traders. | VPIN が跳ね上がるとき、大口の取引頻度が増える。彼らこそ情報を持つトレーダーである。 |
| X1-A-10 | IDEAS_A.md:349 | VPIN spike + whale trades in one direction = strongest signal available. | VPIN の急上昇 + 大口が一方向に取引 = 得られるもっとも強い信号。 |
| X1-A-10 | IDEAS_A.md:349 | strongest signal | もっとも強い信号 |
| X1-A-11 | IDEAS_A.md:360 | A whale is placing limit buys that absorb all selling. After sellers exhaust, explosive reversal follows. | 大口が、すべての売りを吸収する指値の買いを置いている。売り手が尽きたあと、爆発的な反転が続く。 |
| X1-A-12 | IDEAS_A.md:371 | Whales enter with market orders (urgent) but exit with limit orders at higher prices (patient). | 大口は成行(緊急)で入り、より高い価格の指値(辛抱強く)で出る。 |
| X1-A-12 | IDEAS_A.md:371 | One massive market sell from a whale is likely a stop-loss — the move may continue. | 大口からの 1 回の大きな成行売りは、おそらく損切りである。値動きは続くかもしれない。 |
| X1-A-12 | IDEAS_A.md:377 | massive | 大きな |
| X1-A-13 | IDEAS_A.md:404 | A curated pool of around 80-100 Hyperliquid wallets is maintained in our database. | 厳選した約 80〜100 個の Hyperliquid のウォレットのプールが、当方のデータベースに維持されている。 |
| X1-A-13 | IDEAS_A.md:404 | The wallet must have at least $200,000 in current open notional positions on Hyperliquid (active risk capital, not equity sitting in vaults). The wallet must have between 1 and 200 fills in the last 48 hours (active trader, not a flat zombie wallet, not a high-frequency market-making bot). | ウォレットは、Hyperliquid で現在の建玉の名目額が少なくとも 20 万ドルなければならない(活動している危険資本であり、ボールトに置かれただけの資産ではない)。ウォレットは、直近 48 時間に 1 件以上 200 件以下の約定がなければならない(活動しているトレーダーであり、動かないゾンビのウォレットでも、高頻度のマーケットメイクのボットでもない)。 |
| X1-A-13 | IDEAS_A.md:404 | Long and short open interest are summed in USD across the sampled wallets at current mark prices. | ロングとショートの建玉は、サンプルのウォレット全体で、現在のマーク価格で USD に換算して合算される。 |
| X1-A-13 | IDEAS_A.md:404 | A cron job runs every 15 minutes that pulls the live position state of every active wallet through the standard Hyperliquid clearinghouseState endpoint, then aggregates by symbol with a SQL transformer. | cron のジョブが 15 分ごとに動き、標準の Hyperliquid の clearinghouseState のエンドポイントを通じてすべての活動中のウォレットの現在のポジションの状態を取得し、そのあと SQL の変換器で銘柄ごとに集計する。 |
| X1-A-13 | IDEAS_A.md:404 | When your existing momentum or breakout signal fires, check the smart money ratio. If it agrees with your direction, the trade has a tailwind. | 既存の順張りまたはブレイクアウトの信号が出たら、スマートマネー比を確認せよ。それが自分の向きと一致していれば、その取引には追い風がある。 |
| X1-A-13 | IDEAS_A.md:404 | Extreme ratios (above 2.0x or below 0.5x with strong sample) historically mark short-term exhaustion zones. | 極端な比(強いサンプルで 2.0 倍超または 0.5 倍未満)は、歴史的に短期の枯渇の領域を示す。 |
| X1-A-13 | IDEAS_A.md:404 | Track the rate of change in the long/short ratio across BTC and ETH. When the ratio starts to drift directionally over multiple refresh cycles, that often precedes regime shifts in broader crypto markets by hours or days. | BTC と ETH にわたるロング/ショート比の変化率を追え。比が複数の更新周期にわたって一方向に流れ始めるとき、それはしばしば、より広い暗号資産市場の局面の転換に数時間から数日先行する。 |
| X1-A-13 | IDEAS_A.md:404 | historically | 歴史的に |
| X1-A-13 | IDEAS_A.md:404 | precedes | 先行する |
| X1-A-14 | IDEAS_A.md:437 | For liquidatable positions larger than 100k USDC (10k USDC on testnet for easier testing), only 20% of the position will be sent as a market liquidation order to the book. | 10 万 USDC を超える清算されうるポジション(試験を容易にするためテストネットでは 1 万 USDC)については、ポジションの 20% だけが成行の清算注文として板に出される。 |
| X1-A-14 | IDEAS_A.md:437 | After a block where any position of a user is partially liquidated, there is a cooldown period of 30 seconds. | ユーザーのいずれかのポジションが部分的に清算されたブロックのあと、30 秒のクールダウン期間がある。 |
| X1-A-14 | IDEAS_A.md:437 | If the account equity drops below 2/3 of the maintenance margin without successful liquidation through the book, a backstop liquidation happens through the liquidator vault. | 板を通した清算に成功しないまま口座の資産が維持証拠金の 2/3 を下回ると、清算人のボールトを通じてバックストップの清算が行われる。 |
| X1-A-14 | IDEAS_A.md:437 | Due to the excessively large liquidation size, Hyperliquid HLP took over the position and is gradually unwinding it. | 清算の規模が過度に大きかったため、Hyperliquid の HLP がそのポジションを引き継ぎ、徐々に巻き戻している。 |
| X1-A-15 | IDEAS_A.md:459 | L1 Whale Tracker Radar script can not only simply describe the behavior trends of Whale and individuals, but also generate some simple buying and selling points. | L1 Whale Tracker Radar のスクリプトは、大口と個人の行動の傾向を単に描くだけでなく、簡単な売買のポイントも生成できる。 |
| X1-A-15 | IDEAS_A.md:459 | Dual-Sentiment Analysis: Separates whale [lime EMA] and individual [red EMA] behaviors using volatility-adjusted calculations | 二重センチメント分析: ボラティリティで調整した計算を用いて、大口[ライムの EMA]と個人[赤の EMA]の行動を分ける |
| X1-A-15 | IDEAS_A.md:459 | selradar indicates top region is reached. | selradar は天井の領域に達したことを示す。 |
| X1-A-15 | IDEAS_A.md:459 | buyradar indicates bottom region is reached. | buyradar は底の領域に達したことを示す。 |
| X1-A-15 | IDEAS_A.md:459 | Whale signal intersects/breaks below [-10] threshold | 大口の信号が [-10] の閾値と交差する/を下に抜ける |
| X1-A-15 | IDEAS_A.md:459 | Modified RSIs breach predefined 90%/25% danger zones | 修正した RSI が、あらかじめ定めた 90%/25% の危険域を超える |
| X1-A-15 | IDEAS_A.md:459 | Only use simple moving average to depict Whale behaviors so some info may be missing. | 大口の行動を描くのに単純移動平均だけを用いるため、一部の情報が欠けている可能性がある。 |
| X1-A-16 | IDEAS_A.md:481 | Reappearing liquidity: Visible size refreshes at the same level after partial execution. | 再び現れる流動性: 見えている数量が、部分的な約定のあと同じ水準で補充される。 |
| X1-A-16 | IDEAS_A.md:481 | Repeated absorption: Aggressive buyers or sellers hit the same price but fail to push through. | 繰り返しの吸収: 積極的な買い手または売り手が同じ価格を叩くが、突き抜けられない。 |
| X1-A-16 | IDEAS_A.md:481 | Stalled momentum: Price hesitates despite strong volume flow in one direction. | 失速する勢い: 一方向に強い出来高の流れがあるのに、価格がためらう。 |
| X1-A-16 | IDEAS_A.md:481 | When hidden liquidity absorbs aggressive pressure without price breaking, it signals strength. Traders can enter in the same direction, using the hidden order as confirmation. | 隠れた流動性が価格を崩さずに積極的な圧力を吸収するとき、それは強さを示す。トレーダーは、隠れた注文を確認として使い、同じ方向に入ることができる。 |
| X1-A-16 | IDEAS_A.md:481 | If an iceberg seller repeatedly absorbs buying pressure, it suggests hidden supply. In that case, short positions near that level—or exits from longs—may be justified. | アイスバーグの売り手が買い圧力を繰り返し吸収するなら、それは隠れた供給を示唆する。その場合、その水準の近くでのショート、またはロングからの撤退が正当化されうる。 |
| X1-A-16 | IDEAS_A.md:481 | signals strength | 強さを示す |
| X1-A-17 | IDEAS_A.md:514 | The total BTC amount of the top 10 transactions (in terms of total BTC sent) divided by the total BTC amount flowing into exchanges. | 総送付 BTC 量で見た上位 10 件の取引の BTC の合計を、取引所に流入する BTC の総量で割ったもの。 |
| X1-A-17 | IDEAS_A.md:514 | Looking at the relative size of the top 10 inflows to total inflows, it is possible to discover which exchanges whales use. | 上位 10 件の流入が流入の総量に占める相対的な大きさを見ることで、大口がどの取引所を使うかを発見することができる。 |
| X1-A-17 | IDEAS_A.md:514 | major transfers of coins from personal wallets to centralized exchanges are more often than not a signal of intent to sell by the whale who made the transfer | 個人のウォレットから中央集権の取引所への大きなコインの移動は、たいていの場合、その送金をした大口の売る意図の信号である |
| X1-A-18 | IDEAS_A.md:547 | Delta is the 'Net Force' being applied to the market. The buying minus the selling. | デルタは、市場に加わる「ネットの力」である。買いから売りを引いたもの。 |
| X1-A-18 | IDEAS_A.md:547 | The delta, the net of all the whales' buying and selling | デルタ、すなわちすべての大口の売買の正味 |
| X1-A-18 | IDEAS_A.md:547 | we can assume they're betting on the correct future direction of the market and their activity will be visible in the volume. | 彼らは市場の将来の向きを正しく賭けていると仮定でき、その活動は出来高に見えるだろう。 |
| X1-A-18 | IDEAS_A.md:547 | Delta indicates the current direction and provides information that can predict future direction. | デルタは現在の向きを示し、将来の向きを予測しうる情報を与える。 |
| X1-A-18 | IDEAS_A.md:547 | any trade ≥ 10 BTC | 10 BTC 以上のあらゆる取引 |
| X1-A-19 | IDEAS_A.md:580 | Whales and market makers on Binance have steadily pared back bullish exposure since Wednesday. This shift is reflected in the long-to-short ratio, which dropped to 1.20 from 1.93. | Binance の大口とマーケットメイカーは、水曜日から強気のエクスポージャーを着実に減らしてきた。この変化は、1.93 から 1.20 に下がったロング対ショート比に表れている。 |
| X1-A-19 | IDEAS_A.md:580 | the long-to-short ratio for top traders at OKX hit 1.7 on Tuesday, a sharp reversal from its 4.3 peak on Thursday. | OKX の上位トレーダーのロング対ショート比は火曜日に 1.7 となり、木曜日のピークの 4.3 からの急な反転となった。 |
| X1-A-19 | IDEAS_A.md:580 | This reading represents a 30-day low for the exchange, suggesting that demand for leveraged long positions in margin and futures markets has cooled, even with BTC hitting 15-month lows. | この読みは、この取引所の 30 日間の最低であり、BTC が 15 か月ぶりの安値をつけているにもかかわらず、証拠金・先物市場でのレバレッジをかけたロングへの需要が冷えたことを示唆する。 |
| X1-A-20 | IDEAS_A.md:602 | The single largest order was a $59.67 million BTC-USDT long unwinding on HTX. | 最大の単一の注文は、HTX での 5967 万ドルの BTC-USDT のロングの巻き戻しだった。 |
| X1-A-20 | IDEAS_A.md:602 | OI rising into a falling price, retail still leaning long, and whale accounts flipping short on OKX all point to a market that has not found a clearing level. | 価格が下がるなかでの建玉の増加、なおロングに傾く個人、OKX でショートに転じる大口のアカウントは、すべて、市場がまだ均衡する水準を見つけていないことを示す。 |
| X1-A-21 | IDEAS_A.md:635 | When they start tweeting about a certain coin more often, it's because its price has changed—not vice versa | 彼らが特定のコインについて頻繁にツイートし始めるのは、その価格が変わったからであり、その逆ではない |
| X1-A-21 | IDEAS_A.md:635 | All the charts demonstrate more or less the same thing: the 'mentions' curve follows the price curve. | すべてのチャートが、ほぼ同じことを示している。「言及」の曲線は価格の曲線に従う。 |
| X1-A-21 | IDEAS_A.md:635 | When the price fluctuates strongly, influencers tend to write about the coin more | 価格が大きく変動するとき、インフルエンサーはそのコインについてより多く書く傾向がある |
| X1-A-21 | IDEAS_A.md:635 | Influencers follow the news, not create it. | インフルエンサーはニュースに従うのであり、ニュースを作るのではない。 |
| X1-A-22 | IDEAS_A.md:646 | crypto-influencers generally recommend that investors buy or hold (rather than sell) crypto assets and that such tweets are associated with positive and significant short-run returns. | 暗号資産のインフルエンサーは、一般に投資家が暗号資産を買うか持ち続ける(売るのでなく)ことを勧めており、そのようなツイートは、短期の有意な正のリターンと関連している。 |
| X1-A-22 | IDEAS_A.md:646 | These investment gains quickly fade away. Returns begin to decline substantially in the first five days after the tweets. | これらの投資の利益はすぐに消える。リターンは、ツイートの後の最初の 5 日間で大きく下がり始める。 |
| X1-A-22 | IDEAS_A.md:646 | Our evidence is consistent with 'pump-and-dump' schemes, where promoters talk up an investment in exchange for crypto and then sell it quickly when the resulting buzz raises the price for a short time. | 当方の証拠は「パンプ・アンド・ダンプ」の仕組みと整合する。そこでは、宣伝者が暗号資産と引き換えに投資を持ち上げ、その結果の騒ぎが短期間価格を上げたときに、すぐにそれを売る。 |
| X1-A-22 | IDEAS_A.md:646 | self-described experts are even worse | 自称の専門家はさらに悪い |
| X1-A-23 | IDEAS_A.md:690 | Most traders set a stop right below a swing low | ほとんどのトレーダーは、直近の安値のすぐ下に損切りを置く |
| X1-A-23 | IDEAS_A.md:690 | A few ticks below a swing low, Just above yesterday's high, or Near round numbers. | 直近の安値の数ティック下、前日の高値のすぐ上、またはキリのよい数字の近く。 |
| X1-A-23 | IDEAS_A.md:690 | Since so many orders are there, they create liquidity in trading. Price naturally moves to these zones because: It needs volume to execute large trades and It can fill multiple orders quickly in one area. | そこにはそれだけ多くの注文があるので、取引に流動性を作る。価格は自然にこれらの領域へ動く。大きな取引を執行するのに出来高が要り、1 か所で複数の注文を素早く約定できるからである。 |
| X1-A-23 | IDEAS_A.md:690 | your stop is in the same place as thousands of others | あなたの損切りは、他の何千人もの損切りと同じ場所にある |
| X1-A-23 | IDEAS_A.md:690 | Price dips just enough to trigger your stop! In doing so, it hits many other stops too. This creates a wave of sell orders. Now, big buyers step in and absorb that liquidity. | 価格はあなたの損切りを発動させるのにちょうど足りるだけ下がる。そのとき、他の多くの損切りにも当たる。これが売り注文の波を作る。そして、大きな買い手が入って、その流動性を吸収する。 |
| X1-A-23 | IDEAS_A.md:690 | Stop losses get hit because they were placed where everyone else placed theirs. | 損切りが当たるのは、他のみんなが置いたのと同じ場所に置かれていたからだ。 |
| X1-A-23 | IDEAS_A.md:690 | a coordinate on a liquidity map | 流動性の地図上の座標 |
| X1-A-24 | IDEAS_A.md:723 | Large exchange inflows increase available spot supply and are commonly monitored as potential sell-side liquidity signals by market participants | 取引所への大きな流入は、現物の供給できる量を増やし、市場参加者に、売り側の流動性の信号になりうるものとして一般に監視されている |
| X1-A-24 | IDEAS_A.md:723 | The post does not state any purpose for the transfer (e.g., sales, custody rebalancing, or ETF operations), so only the on-chain exchange inflow is confirmed at this time | この投稿は送金の目的(たとえば売却、保管の組み替え、ETF の運用)を述べていないので、現時点で確認されているのはチェーン上の取引所への流入だけである |
| X1-A-24 | IDEAS_A.md:723 | a whale may transfer assets for an outright sale, portfolio rebalancing, liquidity management, or other trading activity | 大口は、純粋な売却、ポートフォリオの組み替え、流動性の管理、またはその他の取引活動のために資産を移すことがある |
| X1-A-25 | IDEAS_A.md:756 | Notional signal: raw USD exposure: where are winners putting the most capital? | 名目の信号: 生の USD のエクスポージャー: 勝っている者は最大の資金をどこに置いているか? |
| X1-A-25 | IDEAS_A.md:756 | Trader signal: democratic vote: each trader counts once, regardless of position size | トレーダーの信号: 民主的な投票: ポジションの大きさにかかわらず、各トレーダーは 1 票と数える |
| X1-A-25 | IDEAS_A.md:756 | Volume signal: sqrt-weighted to dampen single-whale distortion | 出来高の信号: 単一の大口の歪みを抑えるため、平方根で加重 |
| X1-A-25 | IDEAS_A.md:756 | Consensus = 2 out of 3 signals agree on direction. Confidence: HIGH (all 3 agree) · MEDIUM (2/3) · LOW (split) | 合意 = 3 つの信号のうち 2 つが向きで一致。確信度: 高(3 つすべてが一致)・中(3 分の 2)・低(割れている) |
| X1-A-25 | IDEAS_A.md:756 | Top N% of traders by PnL classified as Winners | 損益で上位 N% のトレーダーを勝者に分類 |
| X1-A-25 | IDEAS_A.md:756 | Bottom N% of traders by PnL classified as Losers | 損益で下位 N% のトレーダーを敗者に分類 |
| X1-A-26 | IDEAS_A.md:789 | Every wallet on Hyperliquid is classified into 16 behavioral segments across two dimensions. | Hyperliquid のすべてのウォレットは、2 つの次元にわたる 16 の行動の区分に分類される。 |
| X1-A-26 | IDEAS_A.md:789 | Positive bias = net long, negative = net short. | 正の偏り = 正味のロング、負 = 正味のショート。 |
| X1-A-26 | IDEAS_A.md:789 | Cohort bias (`/segments/{segmentId}/bias-history`) returns data over a rolling window. It is not suitable for multi-day backtesting. | コホートの偏り(`/segments/{segmentId}/bias-history`)は、ローリングの窓にわたるデータを返す。数日にわたるバックテストには適さない。 |
| X1-A-26 | IDEAS_A.md:789 | Alert me when two cohorts diverge on any coin | どのコインでも 2 つのコホートが乖離したら知らせて |
| X1-A-26 | IDEAS_A.md:789 | The divergence between the top and bottom cohorts is one of the most reliable contrarian signals available on-chain | 上位と下位のコホートの乖離は、チェーン上で得られるもっとも信頼できる逆張りの信号の 1 つである |
| X1-A-27 | IDEAS_A.md:822 | If the Elite Trader's position is liquidated, your corresponding copy trade position will also be closed — even if your margin is still sufficient. | エリートトレーダーのポジションが清算されると、あなたの対応するコピートレードのポジションも、あなたの証拠金がまだ十分であっても閉じられる。 |
| X1-A-27 | IDEAS_A.md:822 | When following an elite trader, you can set the stop-loss ratio and the take-profit ratio in Risk management. If the TP/SL ratio is reached, your copy trade position will be closed even when the elite trader has not closed the position. | エリートトレーダーをフォローしているとき、リスク管理で損切りの比率と利確の比率を設定できる。TP/SL の比率に達すると、エリートトレーダーがポジションを閉じていなくても、あなたのコピートレードのポジションは閉じられる。 |
| X1-A-28 | IDEAS_A.md:855 | how professional investors are allocating to Bitcoin, what risks they're monitoring, and where they think the market is heading | プロの投資家がビットコインにどう配分しているか、どんなリスクを監視しているか、市場がどこへ向かうと考えているか |
| X1-A-28 | IDEAS_A.md:855 | a monthly snapshot | 月次のスナップショット |
| X1-A-28 | IDEAS_A.md:855 | Fund managers saw the rally coming. Even before Bitcoin cleared $100K, most already expected it to reach that level or higher | ファンドマネージャーはこの上昇を予見していた。ビットコインが 10 万ドルを超える前から、ほとんどはすでにその水準かそれ以上に達すると予想していた |
| X1-A-29 | IDEAS_A.md:888 | Cryptocurrencies, they've become unstoppable...people want in ahead of time. | 暗号資産は止められなくなった……人々は先回りして入りたがっている。 |
| X1-A-29 | IDEAS_A.md:888 | If I'm right, then tomorrow very well could be the peak for crypto | 私が正しければ、明日は暗号資産の天井になってもおかしくない |
| X1-A-29 | IDEAS_A.md:888 | The markets were rallying with the mantra 'When the CME lists bitcoin futures, we're GOING TO THE MOON!!!' | 市場は「CME がビットコイン先物を上場したら、月まで行くぞ!!!」という合言葉で上がっていた。 |
| X1-A-30 | IDEAS_A.md:921 | While flows typically move in line with crypto prices, changes in the pace of outflows have historically been more informative, often signaling inflection points in investor sentiment | フローは通常、暗号資産の価格と同じ向きに動くが、流出のペースの変化のほうが、歴史的により情報量が多く、しばしば投資家心理の転換点を示す |
| X1-A-30 | IDEAS_A.md:921 | more informative | より情報量が多い |
| X1-A-30 | IDEAS_A.md:921 | signaling | 示す |
| X1-A-30 | IDEAS_A.md:921 | cash-and-carry basis trades can generate flows that appear bullish even when net delta exposure remains near zero | キャッシュ・アンド・キャリーのベーシス取引は、正味のデルタのエクスポージャーがゼロ近くにとどまっていても、強気に見えるフローを生みうる |
| X1-A-31 | IDEAS_A.md:954 | The basis premium on CME has grown by almost 1% over the past seven days, signaling increased optimism among institutional futures traders. | CME のベーシスのプレミアムは過去 7 日間で 1%近く拡大し、機関投資家の先物トレーダーの楽観が強まっていることを示している。 |
| X1-A-31 | IDEAS_A.md:954 | After its recent growth, the basis premium on CME surpassed that of Binance, which saw a major decline over the past seven days. | 最近の拡大のあと、CME のベーシスのプレミアムは Binance のものを上回った。Binance は過去 7 日間で大きく低下した。 |
| X1-A-31 | IDEAS_A.md:954 | Basis premiums are now sitting at similar levels on CME and the offshore exchanges, indicating that the market sentiment is balanced among different groups of traders. | ベーシスのプレミアムは現在 CME と海外の取引所で同程度の水準にあり、市場心理がトレーダーのさまざまな集団の間で均衡していることを示している。 |
| X1-A-31 | IDEAS_A.md:954 | optimism | 楽観 |
| X1-A-32 | IDEAS_A.md:987 | Leveraged funds reduced their net short position by 5,566.5 bitcoin in bitcoin futures on the Chicago Mercantile Exchange (CME). | レバレッジ・ファンドは、シカゴ・マーカンタイル取引所(CME)のビットコイン先物で、ネットのショートを 5,566.5 ビットコイン減らした。 |
| X1-A-32 | IDEAS_A.md:987 | A leveraged fund's short position can be a simple bet on falling prices. It can also be part of an arbitrage strategy linking spot and futures, or a hedge to defend other positions. | レバレッジ・ファンドのショートは、単純な下落への賭けでありうる。現物と先物をつなぐ裁定戦略の一部や、他のポジションを守るヘッジでもありうる。 |
| X1-A-32 | IDEAS_A.md:987 | makes it hard to tell from the report alone whether the move reflects directional trading, a basis trade, a shift in maturities, or a mix of those factors | 報告だけから、その動きが方向性の取引、ベーシス取引、期近・期先の入れ替え、またはそれらの混合のどれを反映するのかを見分けるのを難しくしている |
| X1-A-33 | IDEAS_A.md:1020 | The daily rebalancing of these ETFs magnifies volatility in MicroStrategy's stock, particularly during end-of-day trading. | これらの ETF の日次のリバランスは、とりわけ引け間際の取引で、MicroStrategy の株式のボラティリティを増幅する。 |
| X1-A-33 | IDEAS_A.md:1020 | In November, there were instances where rebalancing flows exceeded $2 billion in a single day | 11 月には、リバランスのフローが 1 日で 20 億ドルを超えた例があった |
| X1-A-33 | IDEAS_A.md:1020 | These 'price-insensitive' flows exacerbate market moves | これらの「価格に反応しない」フローは、市場の動きを悪化させる |
| X1-C-1 | IDEAS_C.md:33 | Saylor's Sunday posts once frequently preceded a disclosure of a Monday purchase, but recently, that connection has weakened. | セイラーの日曜の投稿は、かつては月曜の購入の開示にしばしば先行していたが、最近はその結びつきが弱まっている。 |
| X1-C-1 | IDEAS_C.md:33 | As The Block previously reported, a June 28 post reading 'We're gonna need more charts' was followed by a new capital framework rather than a buy, and the July 5 post preceded disclosure of the largest bitcoin sale in the company's history. | The Block が以前に報じたとおり、6 月 28 日の「もっとチャートが要りそうだ」という投稿には、購入でなく新しい資本の枠組みが続き、7 月 5 日の投稿は、同社史上最大のビットコイン売却の開示に先行した。 |
| X1-C-2 | IDEAS_C.md:57 | Substantial Bitcoin movements from identified corporate wallets typically generate immediate scrutiny within cryptocurrency circles. | 特定された企業ウォレットからの大きなビットコインの移動は、通常、暗号資産の界隈で即座に注目を集める。 |
| X1-C-2 | IDEAS_C.md:57 | However, wallet transfers don't necessarily indicate asset liquidation. Bitcoin frequently moves among cold storage solutions, third-party custodians, or different corporate-controlled addresses without any ownership changes. | しかし、ウォレットの送金が必ずしも資産の売却を意味するわけではない。ビットコインは、所有者の変更なしに、コールドストレージ、第三者のカストディアン、または企業が管理する別のアドレスの間で頻繁に動く。 |
| X1-C-2 | IDEAS_C.md:57 | "This was a routine custody operation. No bitcoin was sold, and our holdings remain 43,000 BTC," Gerovich stated. | 「これは通常のカストディの作業だった。ビットコインは売られておらず、保有は 43,000 BTC のままだ」とゲロビッチ氏は述べた。 |
| X1-C-3 | IDEAS_C.md:81 | However, negative Coinbase premiums indicated softer buying pressure in the US market. | しかし、コインベースのプレミアムがマイナスだったことは、米国市場の買い圧力が弱いことを示していた。 |
| X1-C-4 | IDEAS_C.md:105 | When a stock is trading at a premium to BTC NAV, each dollar raised through an ATM program buys more BTC per share than it dilutes. | 株式が BTC の純資産価値(NAV)に対してプレミアムで取引されているとき、ATM プログラムで調達した 1 ドルは、希薄化させる以上に 1 株あたりの BTC を多く買う。 |
| X1-C-4 | IDEAS_C.md:105 | Once you are trading at NAV, shareholder dilution is no longer strategic. It's extractive. | NAV で取引されるようになれば、株主の希薄化はもはや戦略ではない。搾取である。 |
| X1-C-4 | IDEAS_C.md:105 | once a stock price falls to levels at or near NAV, that equation reverses: equity issuance dilutes shareholder exposure to BTC rather than enhancing it. | 株価が NAV かその近くまで下がると、その式は逆転する。株式の発行は、BTC へのエクスポージャーを高めるのでなく、株主のエクスポージャーを薄める。 |
| X1-C-5 | IDEAS_C.md:129 | The convertible notes, preferred shares, and credit facilities that financed a large share of corporate Bitcoin holdings carry maturities, redemption windows, and dividend dates that determine when a company might need to sell. | 企業のビットコイン保有の大部分を賄った転換社債、優先株、与信枠には、会社がいつ売る必要が出るかを決める満期、償還の窓、配当日がある。 |
| X1-C-6 | IDEAS_C.md:153 | The update, which took effect at 08:50 UTC on the specified date, will not affect existing positions. | この更新は、指定された日の 08:50 UTC に発効し、既存のポジションには影響しない。 |
| X1-C-6 | IDEAS_C.md:153 | Binance Futures has announced updates to the leverage and margin tiers for several USDⓈ-M and COIN-M perpetual contracts, effective December 6, 2024. | Binance Futures は、いくつかの USDⓈ-M と COIN-M の無期限契約のレバレッジと証拠金の階層の更新を、2024 年 12 月 6 日付けで発表した。 |
| X1-C-6 | IDEAS_C.md:153 | At 100x leverage, a 1% move against a position equals the position's initial margin before maintenance margin and fees, leaving less room before liquidation. | 100 倍のレバレッジでは、ポジションに逆行する 1% の動きは、維持証拠金と手数料の前に、ポジションの当初証拠金に等しく、清算までの余裕が小さくなる。 |
| X1-C-7 | IDEAS_C.md:177 | The crypto exchange confirmed it purchased a final tranche of 4,545 BTC on Thursday, bringing total SAFU holdings to 15,000 BTC. Binance said the transition was completed within 30 days of its initial commitment. | この暗号資産取引所は、木曜日に 4,545 BTC の最後の分を購入したことを確認し、SAFU の保有の合計は 15,000 BTC になった。Binance は、この移行が当初の約束から 30 日以内に完了したと述べた。 |
| X1-C-7 | IDEAS_C.md:177 | If the fund's market value falls below $800 million due to BTC price fluctuations, Binance will rebalance the fund to restore its value to $1 billion. | BTC の価格の変動によりファンドの時価が 8 億ドルを下回った場合、Binance はファンドをリバランスして、価値を 10 億ドルに戻す。 |
| X1-C-7 | IDEAS_C.md:177 | Binance also published the bitcoin wallet address associated with the fund and shared the latest transaction hash reflecting the final purchase onchain. | Binance は、ファンドに関連するビットコインのウォレットアドレスも公表し、最後の購入を示す最新の取引ハッシュをオンチェーンで共有した。 |
| X1-C-8 | IDEAS_C.md:201 | When liquidating position i with quantity Δqi=−qi, the exchange executes a market order that consumes order book liquidity. | 数量 Δqi=−qi のポジション i を清算するとき、取引所は板の流動性を消費する成行注文を執行する。 |
| X1-C-8 | IDEAS_C.md:201 | When Dt>IFt, the residual Rt=max(0,Dt−IFt) triggers autodeleveraging: profitable positions are forcibly closed to cover the shortfall. | Dt>IFt のとき、残余 Rt=max(0,Dt−IFt) が自動デレバレッジを発動する。利益の出ているポジションが、不足分を賄うために強制的に閉じられる。 |
| X1-C-8 | IDEAS_C.md:201 | Slippage-at-Risk (SaR): A Forward-Looking Liquidity Risk Framework for Perpetual Futures Exchanges | Slippage-at-Risk(SaR): 無期限先物取引所のための、将来を見据えた流動性リスクの枠組み |
| X1-C-9 | IDEAS_C.md:225 | The user might have withdrawn equity from the HLP vault in a way that triggered an auto-liquidation event, with the HLP taking the opposing side of the trade and absorbing a loss — to the tune of about $4 million. | ユーザーは、自動清算の事象を引き起こす形で HLP ボールトから資産を引き出した可能性がある。HLP が取引の反対側に立ち、約 400 万ドルの損失を吸収した。 |
| X1-C-10 | IDEAS_C.md:261 | we can translate the prices of narrow call or put spreads into a space of option-implied probabilities, each tied to the event that Bitcoin touches some given price level. | 幅の狭いコールまたはプットのスプレッドの価格を、ビットコインがある価格水準に触れるという事象に結びついた、オプションから導かれる確率の空間に変換できる。 |
| X1-C-10 | IDEAS_C.md:261 | Talk: Are Decentralized Prediction Markets Efficient? Evidence from Bitcoin Options | 講演: 分散型の予測市場は効率的か? ビットコインのオプションからの証拠 |
| X1-C-11 | IDEAS_C.md:285 | Three newly created wallets profited a combined $484,575 on Polymarket betting that the US and Iran would agree to a ceasefire by Tuesday | 新しく作られた 3 つのウォレットが、米国とイランが火曜日までに停戦で合意するというポリマーケットへの賭けで、合わせて 484,575 ドルの利益を得た |
| X1-C-11 | IDEAS_C.md:285 | One Polymarket trader made their first trade on the 'US x Iran ceasefire by April 7' market at 1:59 pm UTC on Tuesday, roughly eight and a half hours before US President Donald Trump confirmed that a ceasefire agreement had been made | あるポリマーケットのトレーダーは、「US x Iran ceasefire by April 7」の市場で、火曜日の 13:59 UTC に最初の取引をした。これは、トランプ米大統領が停戦の合意がなされたことを確認する約 8 時間半前だった |
| X1-C-12 | IDEAS_C.md:333 | Compare YES vs NO holder counts: If one side has far more unique holders, it may signal retail vs. whale dynamics. | YES と NO の保有者数を比べよ: 片側のユニークな保有者がはるかに多いなら、個人対大口の力学を示している可能性がある。 |
| X1-C-13 | IDEAS_C.md:357 | Analyzing trading activity before and after Polymarket introduced the contracts in July 2024, the researchers found sharp increases in Bitcoin spot-market order flow just before settlement, followed by rapid price reversals, which were consistent with settlement-price manipulation. | ポリマーケットが 2024 年 7 月にその契約を導入する前後の取引活動を分析して、研究者らは、決済の直前にビットコイン現物市場の注文フローが急増し、その後に急速な価格の反転が続くことを見つけた。これは決済価格の操作と整合していた。 |
| X1-C-13 | IDEAS_C.md:357 | Stanford study says 5-minute Bitcoin prediction markets enable settlement manipulation | スタンフォードの研究によると、5 分のビットコイン予測市場は決済の操作を可能にする |
| X1-C-13 | IDEAS_C.md:357 | For 5-minute markets, that window is 30 seconds. For the longer 15-minute and 4-hour markets, it stretches to 60 seconds. | 5 分の市場では、その窓は 30 秒である。より長い 15 分と 4 時間の市場では、60 秒に延びる。 |
| X1-D-1 | IDEAS_D.md:39 | Passive traders can capitalize on widened spreads by providing liquidity rather than consuming it. Placing limit orders at 0.6-0.7 basis points when spreads reach 1.2 basis points positions traders to capture the temporary premium while others panic. | 受け身のトレーダーは、流動性を消費するのでなく提供することで、広がったスプレッドを活用できる。スプレッドが 1.2 ベーシスポイントに達したときに 0.6〜0.7 ベーシスポイントに指値を置くと、他の者が慌てている間、一時的なプレミアムを獲得する位置に立てる。 |
| X1-D-1 | IDEAS_D.md:39 | Market makers can't simply cancel all quotes without losing their place in the queue when markets normalize. Instead, they maintain presence but at safer distances. | マーケットメイカーは、市場が正常に戻ったときに待ち行列の順番を失わずに、すべての気配を単に取り消すことはできない。代わりに、存在は保ちつつ、より安全な距離に置く。 |
| X1-D-2 | IDEAS_D.md:67 | The violence and the speed at which this entire liquidation cascade happened made it very difficult to continue to make markets in that specific window. | この清算の連鎖の全体が起きた激しさと速さのため、その特定の時間帯にマーケットメイクを続けることは非常に難しかった。 |
| X1-D-2 | IDEAS_D.md:67 | Tremendously less liquidity in the order books | 板の流動性が途方もなく減った |
| X1-D-2 | IDEAS_D.md:67 | Our systems worked as intended: The risk engine's circuit breakers kicked in and pulled our quotes from the market...it took a bit longer to get back to full size while we worked through those issues. | 当社のシステムは意図どおりに動いた。リスクエンジンのサーキットブレーカーが作動し、市場から当社の気配を引き上げた……それらの問題に対処する間に、全量に戻すのにもう少し時間がかかった。 |
| X1-D-3 | IDEAS_D.md:95 | On Dec. 31, 2025, Wintermute moved 1,518.6 BTC to Binance while withdrawing only 305.5 BTC, a net deposit of 1,213 BTC, worth approximately $107 million at the day's prices near $88,000. | 2025 年 12 月 31 日、ウィンターミュートは 1,518.6 BTC を Binance に動かし、引き出したのは 305.5 BTC だけだった。ネットの入金は 1,213 BTC で、約 88,000 ドル近いその日の価格で約 1 億 700 万ドルに相当する。 |
| X1-D-3 | IDEAS_D.md:95 | A Bitcoin deposit could remain untraded for days or execute instantly. The blockchain cannot distinguish. | ビットコインの入金は、何日も取引されないままのこともあれば、即座に執行されることもある。ブロックチェーンは区別できない。 |
| X1-D-3 | IDEAS_D.md:95 | The timing concentrated during traditionally low-liquidity windows | 時間帯は、伝統的に流動性の低い時間帯に集中していた |
| X1-D-4 | IDEAS_D.md:137 | a negative correlation between maker fill likelihood and post-fill returns | メイカーの約定の可能性と約定後のリターンとの間の負の相関 |
| X1-D-4 | IDEAS_D.md:137 | viable maker strategies often require a contrarian approach, counter-trading the prevailing order book imbalance | 実行可能なメイカー戦略はしばしば逆張りの手法を必要とし、優勢な板の不均衡と反対側で取引する |
| X1-D-5 | IDEAS_D.md:165 | if you are net long, shift both bid and ask prices lower to encourage selling and discourage additional buying. | ネットでロングなら、売りを促し追加の買いを抑えるため、買値と売値の両方を下げよ。 |
| X1-D-5 | IDEAS_D.md:165 | Inventory risk is one of the main risks in market making. If one side keeps filling while the other does not, your position drifts away from neutral. | 在庫のリスクは、マーケットメイクの主なリスクの 1 つである。片側が約定し続け、もう片側が約定しなければ、ポジションは中立から離れていく。 |
| D1-D-8 | IDEAS_D.md:179 | If there is not enough liquidity to absorb the position cleanly, HLP can become the final backstop and take over the position. | ポジションをきれいに吸収するのに十分な流動性がなければ、HLP が最後の砦となってポジションを引き継ぐことがある。 |
| D1-D-8 | IDEAS_D.md:179 | HLP may take on a position that continues to move against it. | HLP は、逆行し続けるポジションを引き受けることがある。 |
| X1-D-6 | IDEAS_D.md:207 | simultaneously buying an asset on spot and shorting the same asset on perpetual futures | 現物で資産を買うと同時に、無期限先物で同じ資産を売る |
| X1-D-6 | IDEAS_D.md:207 | Overleveraged longs: expensive to hold, correction risk rises | 行き過ぎたレバレッジのロング: 保有は高くつき、調整のリスクが高まる |
| X1-D-6 | IDEAS_D.md:207 | Above +0.05% | +0.05% を超える |
| X1-D-6 | IDEAS_D.md:207 | extreme funding rate episodes have consistently coincided with major market turning points | 極端な資金調達率の局面は、一貫して市場の大きな転換点と重なってきた |
| X1-D-6 | IDEAS_D.md:213 | Above +0.05% | +0.05% を超える |
| X1-D-7 | IDEAS_D.md:235 | backed with crypto assets and corresponding short futures positions | 暗号資産と、それに対応する先物のショートのポジションで裏付けられている |
| X1-D-7 | IDEAS_D.md:235 | Funding rates on delta-neutral basis trades in crypto perpetual and futures markets | 暗号資産の無期限・先物市場におけるデルタ中立のベーシス取引の資金調達率 |
| X1-D-7 | IDEAS_D.md:235 | USDe entered March with roughly $5.92 billion in circulation before falling to $3.90 billion by the end of April, a decline of about one-third in two months. | USDe は 3 月に約 59.2 億ドルの流通で入り、4 月末までに 39.0 億ドルに下がった。2 か月で約 3 分の 1 の減少である。 |
| X1-D-8 | IDEAS_D.md:263 | If HL rate > BN rate: short on Hyperliquid, long on Binance | HL の率 > BN の率 なら: Hyperliquid でショート、Binance でロング |
| X1-D-8 | IDEAS_D.md:263 | The spread flips, turning a receiving position into a paying one | スプレッドが反転し、受け取るポジションが払うポジションに変わる |
| X1-D-8 | IDEAS_D.md:263 | A sharp price move forces one leg out before the other can offset | 急な価格の動きが、もう片方が相殺する前に片方の脚を追い出す |
| X1-D-8 | IDEAS_D.md:263 | The two positions need to go on at the same time. Any lag between fills exposes you to price movement that can skew your hedge | 2 つのポジションは同時に建てる必要がある。約定の間に遅れがあると、ヘッジをずらしうる価格の動きにさらされる |
| X1-D-8 | IDEAS_D.md:263 | Platform risk: Technical outage or withdrawal restrictions on either exchange | プラットフォームのリスク: どちらかの取引所での技術的な障害または出金の制限 |
| D1-D-12 | IDEAS_D.md:279 | The two positions need to go on at the same time | 2 つのポジションは同時に建てる必要がある |
| X1-D-9 | IDEAS_D.md:291 | A basis unwind means those hedged positions are being closed. Investors are exiting the futures short and reducing the paired spot exposure. That mechanical selling can weigh on price even if sentiment is not collapsing. | ベーシスの巻き戻しは、それらのヘッジされたポジションが閉じられていることを意味する。投資家は先物のショートから出て、対になる現物のエクスポージャーを減らしている。その機械的な売りは、心理が崩れていなくても価格の重しになりうる。 |
| X1-D-9 | IDEAS_D.md:291 | Futures open interest is down sharply | 先物の建玉が大きく減っている |
| X1-D-9 | IDEAS_D.md:297 | 10 billion | 100 億 |
| X1-D-10 | IDEAS_D.md:319 | a short futures position can hedge a long spot or spot ETF holding...Public CFTC totals omit links to offsetting legs, leaving directional positioning, basis hedging or a mixture of both as plausible explanations. | 先物のショートは、現物または現物 ETF のロングの保有のヘッジになりうる……公開されている CFTC の合計は相殺する脚への結びつきを省いており、方向性のポジション、ベーシスのヘッジ、またはその両方の混合を、もっともらしい説明として残す。 |
| X1-D-11 | IDEAS_D.md:347 | Friday's flash crash didn't just wipe out longs—it also hit delta-neutral funds and market makers who thought they were properly hedged using perps | 金曜日のフラッシュクラッシュは、ロングを一掃しただけではなく、無期限先物で適切にヘッジしていると考えていたデルタ中立のファンドやマーケットメイカーも直撃した |
| X1-D-11 | IDEAS_D.md:347 | Auto-Deleveraging (ADL) and oracle issues caused widespread forced liquidations | 自動デレバレッジ(ADL)とオラクルの問題が、広範な強制清算を引き起こした |
| X1-D-12 | IDEAS_D.md:375 | The impact of global news items on bitcoin volatility | 世界のニュースがビットコインのボラティリティに与える影響 |
| X1-D-12 | IDEAS_D.md:375 | bitcoin investors need approximately 45 minutes to process each news item on COVID-19 and war as information continuously flows into the market | ビットコインの投資家は、情報が市場に絶え間なく流れ込むため、COVID-19 と戦争に関する各ニュースを処理するのに約 45 分を要する |
| X1-D-12 | IDEAS_D.md:375 | investors to anticipate highly significant news on these topics up to two hours before its publication | 投資家が、これらの話題に関する非常に重要なニュースを、その公表の最大 2 時間前に先取りする |
| X1-D-12 | IDEAS_D.md:375 | inflation-related news exhibits concentrated effects around scheduled release times | インフレ関連のニュースは、予定された公表の時刻の前後に集中した影響を示す |
| X1-D-13 | IDEAS_D.md:403 | Deribit activity shows growing demand for the September 25, 2026 Bitcoin call with a $70,000 strike. | Deribit の活動は、2026 年 9 月 25 日満期の行使価格 7 万ドルのビットコインのコールへの需要が高まっていることを示している。 |
| X1-D-13 | IDEAS_D.md:403 | TDX Strategies favors December strangles on Bitcoin and Solana while implied volatility remains depressed across the options curve. | TDX Strategies は、オプションの曲線全体でインプライド・ボラティリティが低いままの間、ビットコインとソラナの 12 月のストラングルを選好している。 |
| X1-D-13 | IDEAS_D.md:403 | Some are buying upside exposure, while others are paying for volatility or maintaining defensive short positions | 上昇方向のエクスポージャーを買う者もいれば、ボラティリティに対価を払う者や、守りのショートを維持する者もいる |
| X1-D-13 | IDEAS_D.md:405 | paying for volatility | ボラティリティに対価を払う |
| X1-D-14 | IDEAS_D.md:431 | BTC inflow to exchanges has tripled over the past 24 hours, reaching new highs for this year | 取引所への BTC の流入が過去 24 時間で 3 倍になり、今年の最高値に達した |
| X1-D-14 | IDEAS_D.md:431 | over $358 million USD worth of bitcoin was transferred to exchanges in a single hour, shortly before the price dropped even further | 1 時間のうちに 3 億 5800 万米ドル超のビットコインが取引所に移され、その直後に価格はさらに下落した |
| X1-D-14 | IDEAS_D.md:431 | the inflow of Tether to exchanges also saw a massive increase, suggesting that many investors are looking to buy the dip | 取引所への Tether の流入も大きく増えており、多くの投資家が押し目を買おうとしていることを示唆する |
| X1-D-15 | IDEAS_D.md:459 | It's not uncommon to see 'guardrails' placed in the order book ahead of FED speeches and economic reports, | FRB の講演や経済報告の前に、板に「ガードレール」が置かれるのを見るのは珍しくない、 |
| X1-D-15 | IDEAS_D.md:459 | It's also not uncommon to see them get pulled at the last minute. | それらが直前に引き上げられるのを見るのも珍しくない。 |
| X1-D-16 | IDEAS_D.md:487 | Open interest in BTC and ETH perpetual futures rose by $2.1 billion and $2.2 billion, respectively, within the 24 hours following the ceasefire announcement late Tuesday | BTC と ETH の無期限先物の建玉は、火曜日遅くの停戦の発表から 24 時間のうちに、それぞれ 21 億ドルと 22 億ドル増えた |
| X1-D-16 | IDEAS_D.md:487 | Crucially, coin-denominated open interest also increased significantly for both assets, ruling out short liquidations as the primary driver and confirming that traders are opening net new long positions | 重要なことに、コイン建ての建玉も両方の資産で大きく増え、ショートの清算が主な要因である可能性を除き、トレーダーがネットで新しいロングを建てていることを裏付けた |
| X1-D-17 | IDEAS_D.md:515 | Markets rejoiced, instantly pumping over $47500. | 市場は歓喜し、即座に 47,500 ドル超まで急騰した。 |
| X1-D-17 | IDEAS_D.md:515 | The damage was sudden, with BTC dumping around 5% in just 15 mins. | 被害は突然で、BTC はわずか 15 分で約 5% 暴落した。 |
| X1-D-17 | IDEAS_D.md:515 | The double-whammy and ensuing volatility contributed to over $200M in liquidations between shorts and longs, according to CoinGlass data. | 二重の打撃とそれに続く変動が、CoinGlass のデータによると、ショートとロングの間で 2 億ドル超の清算に寄与した。 |
| X1-D-18 | IDEAS_D.md:543 | due to the lack of supply and the relatively high demand in some markets, Bitcoin is being traded at a premium in certain regions | 供給の不足と一部の市場での比較的高い需要のため、ビットコインは特定の地域でプレミアムで取引されている |
| X1-D-18 | IDEAS_D.md:543 | On BitFlyer's brokerage, the price for Bitcoin buys is estimated to be 936,621 Japanese yen, which is equivalent to $8,635 — nearly $300 higher than the global average spot price. | BitFlyer の販売所では、ビットコインの買値は 936,621 円と推定され、これは 8,635 ドルに相当する。世界の平均の現物価格より 300 ドル近く高い。 |
| X1-D-19 | IDEAS_D.md:571 | The price of Bitcoin on Binance.US is $700 more expensive than the cryptocurrency's market price on May 9. | Binance.US のビットコインの価格は、5 月 9 日の暗号資産の市場価格より 700 ドル高い。 |
| X1-D-19 | IDEAS_D.md:571 | Binance.US' Bitcoin premium comes shortly after Binance, the main global exchange, suffered major withdrawal issues on May 7. | Binance.US のビットコインのプレミアムは、世界の主要な取引所である Binance が 5 月 7 日に大きな出金の問題に見舞われた直後に出ている。 |
| X1-D-20 | IDEAS_D.md:599 | This settlement latency slows cross-exchange trading, exposing arbitrageurs to price risk. | この決済の遅延は、取引所をまたぐ取引を遅くし、裁定者を価格リスクにさらす。 |
| X1-D-20 | IDEAS_D.md:599 | Cross-exchange price differences coincide with periods of high settlement latency | 取引所間の価格差は、決済の遅延が大きい期間と重なる |
| X1-D-20 | IDEAS_D.md:599 | Reliable consensus protocols require time-consuming settlement latency, leading to arbitrage limits. | 信頼できる合意のプロトコルには時間のかかる決済の遅延が要り、それが裁定の限界につながる。 |
| X1-D-21 | IDEAS_D.md:627 | 70% of bitcoin price movements start on Binance and are then followed by the other exchanges. Only 30% start on the semi-regulated exchanges (mostly on Coinbase) with Binance following. | ビットコインの価格の動きの 70% は Binance で始まり、他の取引所がそれに続く。半規制の取引所(主に Coinbase)で始まるのは 30% だけで、そのあと Binance が続く。 |
| X1-D-21 | IDEAS_D.md:627 | Binance's leading effect on bitcoin prices in other markets is greatest during US time zones | 他の市場のビットコインの価格に対する Binance の先導の効果は、米国の時間帯にもっとも大きい |
| X1-D-22 | IDEAS_D.md:655 | Traders quickly figured out that prices would jump significantly just by sending the digital currency from an exchange in one country to one in another. | トレーダーはすぐに、デジタル通貨をある国の取引所から別の国の取引所に送るだけで、価格が大きく跳ね上がることに気づいた。 |
| X1-D-22 | IDEAS_D.md:655 | This practice of arbitrage does not get impacted by market fluctuations but by price differences between countries. | この裁定の慣行は、市場の変動の影響を受けず、国どうしの価格差の影響を受ける。 |
| X1-D-23 | IDEAS_D.md:683 | Margin trading enables arbitrageurs to exploit price discrepancies between exchanges or between spot and futures markets | 証拠金取引は、裁定者が、取引所間または現物と先物の市場間の価格差を利用することを可能にする |
| X1-D-23 | IDEAS_D.md:683 | A sharp price move forces one leg out before the other can offset | 急な価格の動きが、もう片方が相殺する前に片方の脚を追い出す |
| - | IDEAS_B.md:9 | bullish | 強気の |
| X1-B-1 | IDEAS_B.md:40 | bitcoin etf | ビットコイン ETF(検索語) |
| X1-B-4 | IDEAS_B.md:190 | How to use Implied Volatility Index to analyze Bitcoin | ビットコインを分析するためのインプライド・ボラティリティ指数の使い方 |
| X1-B-6 | IDEAS_B.md:276 | Taker-Flow-Based Gamma Exposure | テイカーのフローに基づくガンマ・エクスポージャー |
| X1-B-7 | IDEAS_B.md:309 | there s a huge usd14 billion bitcoin options expiry this friday and it points to usd75 000 as price magnet | 今週の金曜日に 140 億米ドルの巨大なビットコインのオプションの満期があり、それは価格の磁石として 7 万 5000 米ドルを指している |
| D1-B-30 | IDEAS_B.md:652 | The U.S. will not sell the Bitcoin it holds in the reserve | 米国は、備蓄に保有するビットコインを売らない |
| D1-B-34 | IDEAS_B.md:700 | Although possible, these transfers may not signal an imminent sale. | 可能性はあるが、これらの送金は差し迫った売却を示すとは限らない。 |
| X1-B-19 | IDEAS_B.md:775 | Excess Supply of Bitcoin Could Keep Pushing BTC Down, Experts Say | ビットコインの供給過剰が BTC の下げを押し続けうる、と専門家は言う |

### 機械の数え

コマンドと出力(出力ファイル作成時に実行した):

```
$ grep -c '^| ' rows.md          # 表の本体の行(見出し・区切り行を除く)
236
$ python3 gen.py                  # 訳の件数 = 表の行の数の一致を assert で確かめる(不一致なら停止)
236
$ 組ごとの表の行: {'IDEAS_A.md': 135, 'IDEAS_C.md': 28, 'IDEAS_D.md': 65, 'IDEAS_B.md': 8}
$ 拾った件数 A/C/D = 228 / 表に無い件数 = 0
$ 原本の行に逐語がそのまま含まれない件数(276 件全部): 0
```

拾った件数 228(A 135 + C 28 + D 65)+ IDEAS_B の訳の無い 8 = 236 = 表の行 236。合っている。

### 持ち越し・迷った点

- 持ち越し: 無い(期限内に全件の訳を付けた)。
- 迷った点 1: 日本語が混じる引用(69 件)は英語の逐語でないので拾っていない。その中に、日本語の文に英語の語句が混じるもの(「SFD（Swap For Difference）…」など、IDEAS_C 453 行)がある。これは日本語の引用の出所の文であり、訳は要らないと判断した。要るならリードが指示する。
- 迷った点 2: 「」や "" で囲まれていない英語(たとえば説明文の中の英語の用語、URL、記事の題を括弧なしで書いたもの)は拾っていない。指示書の「「」や "" で囲まれた英語の文」に従った。
- 迷った点 3: 1 語・2 語の短い引用(「Price Volatility」「flow intensity」「historically」「precedes」「signals strength」「optimism」など)も、囲まれた英語なので 1 行ずつ拾った。同じ文の一部が別の行で長い引用としても出る場合(例: IDEAS_A 547 行の「any trade ≥ 10 BTC」)は、原本に出てくる回数のとおり別の行にした。
- 迷った点 4: IDEAS_B の 652 行は、日本語の機構の文の中に英語の一節が括弧つきで入っている。訳は一節だけに付けた(日本語の機構の文は既に日本語なので足していない)。
- 迷った点 5: 訳語の選び方。「fade」は「逆を張る」、「whale」は「大口」、「basis」は「ベーシス」、「ATM program」は「ATM プログラム」(市場での随時売出し)とした。原文の語を変えずに訳すため、足した説明は無い。リードが別の語を指定するなら置き換える。
- 迷った点 6: 数値の表記は原文のとおり、桁だけ日本語の位取りにした(例: 「$16 million」→「1600 万ドル」、「$1 billion」→「10 億ドル」)。「10 billion」(IDEAS_D 297 行)は「100 億」。
- ページとの照合はしていない(指示書のとおり。別の作業者の担当)。出所の英語が原本の行のとおりであるかは、原本の行に逐語がそのまま含まれることだけを機械で確かめた(上の最後の行)。
