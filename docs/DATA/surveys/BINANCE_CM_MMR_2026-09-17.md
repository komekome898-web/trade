# Binance COIN-M (BTCUSD_PERP) 維持証拠金率・清算価格式 — 一次資料確認(2026-09-17)

調査班による一次資料確認(research-squad モード3)。戦略への当否は判定しない。
生ログ: `docs/DATA/probes/20260917_binance_cm_mmr.log`(全13エントリ、方法・URL・HTTPコード・バイト数・先頭200文字・UTC時刻)。

---

## 主張A: 維持証拠金率の段階表(最小段階のMMR)

### 主張(そのまま)
「Binance COIN-M 先物 BTCUSD_PERP の維持証拠金率(maintenance margin rate)は建玉の想定元本(または枚数)の段階表で決まり、最小の段階の維持証拠金率は X%(値と段階の区切りを一次資料から取る)」

### 一次資料
- URL: https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-coin-m-futures/api/rest-api/account#notional-bracket-for-symbol
  (Binance 公式 開発者ドキュメント、COIN-M Futures API リファレンス「Notional Bracket for Symbol (USER_DATA)」)
- 取得日: 2026-09-17(UTC)
- 取得方法: WebFetch(2回、独立に照会。curl では同URLが HTTP 202・0バイトで本文取得不可。ログ[3][11]参照)

### 引用(原文そのまま、WebFetchの返答から)
1回目の照会:
> ```json
> [
>   {
>     "symbol": "BTCUSD_PERP",
>     "notionalCoef": 1.5,
>     "brackets": [
>       {
>         "bracket": 1,
>         "initialLeverage": 125,
>         "qtyCap": 50,
>         "qtylFloor": 0,
>         "maintMarginRatio": 0.004,
>         "cum": 0
>       }
>     ]
>   }
> ]
> ```

2回目の照会(別セッションで再照会、値の一致確認用):
> ```json
> [
>   {
>     "symbol": "BTCUSD_PERP",
>     "notionalCoef": 1.5,
>     "brackets": [
>       {
>         "bracket": 1,
>         "initialLeverage": 125,
>         "qtyCap": 50,
>         "qtylFloor": 0,
>         "maintMarginRatio": 0.004,
>         "cum": 0
>       }
>     ]
>   }
> ]
> ```

レスポンスフィールドの説明(同ページ、原文のまま):
> `bracket`: "bracket level"
> `initialLeverage`: "the maximum leverage"
> `qtyCap`: "upper edge of base asset quantity"
> `qtylFloor`: "lower edge of base asset quantity"
> `maintMarginRatio`: "Maintenance margin ratio"
> `cum`: "Cumulative value"

### 引用の検算
**不一致の有無を文字単位で確かめる手段が無い(重要な限界)。** このURLは curl で直接叩くと HTTP 202・0バイトで、生の HTML/JSON を自分でバイト単位比較することができなかった(ログ[3])。代わりに行った検算は「WebFetch を独立に2回呼び、返ってきたJSON例が完全一致するか」であり、**2回とも同一の値(symbol=BTCUSD_PERP, notionalCoef=1.5, bracket=1, initialLeverage=125, qtyCap=50, qtylFloor=0, maintMarginRatio=0.004, cum=0)が得られた**(ログ[11])。これは「WebFetch内部モデルの要約が毎回ぶれていないこと」の確認であり、「原文バイトと一致すること」の確認ではない。**その限りでは一致。**

### 判定
**一次資料で確認(ただし範囲が限定的)。**
- 確認できたこと(事実): developers.binance.com の COIN-M `leverageBracket` 系エンドポイント(Notional Bracket for Symbol)のレスポンス例に、**symbol=BTCUSD_PERP、bracket=1(段階1)として initialLeverage=125(最大125倍)、qtyCap=50 BTC、qtylFloor=0 BTC、maintMarginRatio=0.004(0.4%)、cum=0** という値が明記されている。
- **未確認(不明。到達できず)**: これが「例」であって現在の実勢値と保証された記述ではない点、および**段階2以降の表(想定元本/枚数の区切りがどこで切り替わり、MMRがどう上がっていくか)は同ページに1件しか例示が無く、取得できなかった**(ログ[11]、"brackets" 配列の要素は1個のみ)。
- **BTCUSD_PERP の完全な段階表(全段階の想定元本区切り・最大レバレッジ・MMR)は、この環境からは取得できなかった。** 理由:
  1. 公式の表示ページ https://www.binance.com/en/futures/trading-parameters/perpetual/leverage-margin は表がクライアント側JS/APIで後から埋め込まれるSPAで、静的取得(curlもWebFetchのHTML→Markdown変換も)では「No Data」のプレースホルダしか得られない(ログ[8])。
  2. 該当FAQ(https://www.binance.com/en/support/faq/leverage-and-margin-in-coin-margined-futures-contracts-be2c7d9d95b04a7e8044ed02dd7dfe5c )は本文中で表を上記ページに誘導するだけで、表自体を含まない(ログ[9])。
  3. 公式API `GET /dapi/v1/leverageBracket`(全段階を返す)は認証必須のため、手順上使用不可(タスク指示どおり)。
  4. www.binance.com 自体は curl(この環境の $HTTPS_PROXY 経由)から叩くと HTTP 202・0バイトで応答が返る(ボット対策チャレンジと見られる)(ログ[1][2][7])。

**まとめ**: 「最小段階のMMRは0.4%(bracket 1、想定元本 0〜50 BTC、最大レバレッジ125倍)」は developers.binance.com の公式APIドキュメントの例に**その値・その区切りとして明記**されている(事実)。ただしこれが「ドキュメント上の例」である以上、**現在の実勢の段階表と完全に一致することまでは、この環境からは検算できていない(不明)**。

### 代替経路を試したか
はい。
- web.archive.org(CDX API・wayback availability API)を代替経路として試行 → **到達不能**。CDX検索は curl でタイムアウト(60秒、HTTP応答無し、ログ[4])、wayback availability API は2回とも HTTP 429(Too Many Requests、ログ[5][6])。WebFetch では明示的に「Claude Code is unable to fetch from web.archive.org」と拒否された(ログ[12])。
- Binance公式アナウンス(2024-03-05付「Updates on the Leverage & Margin Tiers of Multiple USDⓈ-M and COIN-M Perpetual Contracts」)も確認したが、対象ペア一覧に BTCUSD_PERP / BTCUSD は含まれておらず、根拠にならない(ログ[13])。
- **第2経路(オーナーPC)**: **【追記で不要になった】**公開 JSON 経路(生ログ [15][19])で段階表の全体が取れた。初稿の文: 未試行。オーナーのブラウザ(通常のCookie・JS実行が効く環境)であれば https://www.binance.com/en/futures/trading-parameters/perpetual/leverage-margin で BTCUSD_PERP を選択し、段階表がそのまま表示される可能性が高い(この環境ではSPAのAPI呼び出しが静的フェッチで見えないだけで、地域制限やHTTPコードの問題ではない)。

---

## 主張B: COIN-M 清算価格の計算式(原文引用)

### 主張(そのまま)
「COIN-M 無期限の清算価格の計算式(逆数建て: 清算価格 = 建値 × L / (L ± 1 ∓ MMR × L) の形、または公式が示す形)を原文のまま引用する」

### 一次資料
- URL: https://www.binance.com/en/support/faq/detail/ceccfcfb4e3a45e3b48b0b1bb1a8ae46
  (Binance 公式サポートFAQ「How to Calculate Liquidation Price of Coin-M Futures Contracts」)
- 取得日: 2026-09-17(UTC)
- 取得方法: WebFetch(2回照会。curlでは同URL・別URL(amp版含む)ともHTTP 202・0バイトで本文取得不可。ログ[2][7][10]参照)

### 引用(原文そのまま)
ページの導入文(原文英語のまま):
> "Below is the liquidation price formula for Coin-M Futures contracts:"

この直後に式**そのものは画像(img タグ)として埋め込まれており、alt テキストが無い**ため、式の記号列(分数・演算子の並び)をテキストとして一言一句引用することができなかった(WebFetchのHTML→Markdown変換はimgのalt属性しか式のテキストを拾えず、その属性が空だった。ログ[10])。

式の**周辺の変数定義**はテキストとして存在し、以下は原文の記述内容(WebFetchが変数名・定義として個別に返した語。地の文の完全な一文としての引用ではなく、ページ内に列挙されている変数名と定義の対応であることに注意):
- SideBOTH = 1(ロング) / SideBOTH = -1(ショート)
- B: Absolute position size(one-way mode)
- EPB: Entry price of position
- MMR_B: Maintenance margin rate
- cumB: Maintenance amount
- WB: Wallet balance
- TMM1: Maintenance margin of other contracts
- UPNL1: Unrealized PNL of other contracts
- CM: Contract size
- ヘッジモードでは L/EPL/MMR_L/cumL(ロング)、S/EPS/MMR_S/cumS(ショート)の対になる変数がある
- 「In Isolated Margin Mode, TMM = 0, UPNL = 0」という条件文

### 引用の検算
式そのものが画像であるため、**「原文のテキストと文字単位で一致するか」という検算は式の核心部分(数式)については実行不可能**(比較対象のテキストが存在しない)。変数定義の語(SideBOTH, MMR_B, cumB, WB, TMM1, UPNL1 等)については、WebFetch を2回(異なるプロンプトで)照会し、同じ変数名・同じ定義が返ってきたことを確認した(ログ[10])。一致。

### 判定
**一次資料に到達できず(方法: WebFetch、コード: 200相当で到達自体は成功。ただし清算価格の式本体はページ内で画像として提供されており、alt テキストが無いためテキストとして原文引用ができない)。**

主張が要求する「計算式を原文のまま引用する」は、この環境からは**式の記号列としては満たせなかった**。式が「逆数建て: 清算価格 = 建値 × L / (L ± 1 ∓ MMR × L)」の形であるかどうかは、**この一次資料から検算できていない(不明)**。ページが示す変数構成(SideBOTH による正負の分岐、cumB/MMR_B を使う段階的な維持証拠金の式、Isolated時 TMM=UPNL=0 とする条件)は主張の「±/∓」の構造と方向としては整合的に見えるが、**画像内の実際の分数式・分母の符号を確認できていないため、「一致」とも「矛盾」とも判定しない。**

### 代替経路を試したか
はい。
- AMP版ページ(https://www.binance.com/ph/amp/support/faq/ceccfcfb4e3a45e3b48b0b1bb1a8ae46 、静的HTMLである可能性を期待)を代替経路として試行 → curl で HTTP 202・0バイト(ログ[7])。WebFetch は同URLで HTTP 404(ログには残していないが実行済み・到達不能)。
- web.archive.org も試行したが、主張Aと同じ理由で到達不能(ログ[12]、CDX/availability APIも同様に不可)。
- **第2経路(オーナーPC)**: **【追記 2 で不要になった】**画像を CDN から取得して読んだ。初稿の文: 未試行。通常のブラウザでこのFAQページを開けば式の画像自体は表示される(ページの到達性そのものに問題は無い)。画像内の式をテキスト化するには、オーナーPCで画像を開いてOCRするか、目視で書き取る作業が別途必要。

---

## 総括(調査班としての事実の整理。当否判断は行わない)

| 副主張 | 判定 | 根拠(生ログの行) |
|---|---|---|
| 最小段階(bracket 1)のMMR = 0.4%、想定元本0〜50 BTC、最大レバレッジ125倍 | 一次資料で確認(限定付き: WebFetch の要約が 2 回一致しただけで、原文バイトとの一致は未照合。「ドキュメント例」である。段階2以降の表は**取得済(追記。公開 JSON、2026-05-11 更新の表。2023〜2024 年当時の表かは不明)**) | [11] |
| BTCUSD_PERP の完全な段階表(全段階) | 一次資料に到達できず(方法: curl/WebFetch、コード: 202/0バイト・SPAのため静的取得不可) | [1][2][7][8][9] |
| 清算価格の計算式(記号列そのもの) | **一次資料で確認(追記 2。画像 3 枚を取得し、リードが目視で転記)** | [10]、追記 [20]〜[23] |
| 清算価格の式の変数定義(WB, TMM1, UPNL1, MMR_B, cumB, SideBOTH 等) | 一次資料で確認(限定付き: WebFetch の要約、原文バイト未照合) | [10] |

**【追記で不要になった(2026-09-17)】下の「第 2 経路(オーナー PC)」の推奨は、公開 JSON 経路で段階表が取れたので取り下げる。文は記録として残す。**

**第2経路(オーナーPC)を推奨する2点**:
1. https://www.binance.com/en/futures/trading-parameters/perpetual/leverage-margin で BTCUSD_PERP を選択し、表示される段階表(全段)をコピーする。
2. https://www.binance.com/en/support/faq/detail/ceccfcfb4e3a45e3b48b0b1bb1a8ae46 の式の画像を開き、記号列を書き取る(または画像を保存してOCR)。

いずれも「有料」「地域制限(451等)」には当たっていない。到達不能の原因は、この環境の静的フェッチ手段(curl/WebFetch)が①ボット対策チャレンジ、②クライアント側JSでのデータ後埋め、③画像埋め込みの数式、に対応できないことであり、Binance側のアクセス制限そのものではない(事実として区別して記録する)。

## 追記(リード、2026-09-17、行動の監査の指摘 = この環境の経路を尽くす前にオーナー PC を挙げた)

SPA が呼ぶ公開 JSON 経路を curl で試した(生ログ [14]〜[19])。`https://www.binance.com/bapi/futures/v1/friendly/delivery/common/brackets` が HTTP 200 で全銘柄の段階表を返した(BTCUSD_PERP は 10 段階、`updateTime` 2026-05-11 UTC。抜粋 `docs/DATA/probes/20260917_binance_cm_brackets_BTCUSD_PERP.json`)。**主張 A の段階 2 以降は、この経路で「一次資料で確認(限定付き: 表の日付は 2026-05 で、2023〜2024 年当時の表かは不明。応答全体 58,186 バイトをそのまま `docs/DATA/probes/20260917_binance_cm_brackets_full.json` に保存し、BTCUSD_PERP は抜粋を再整形)」に変わる。**表の区切りは API リファレンスの例(段階 1 の `qtyCap 50`)と違う(段階 1 の上限 5 BTC)。`dapi.binance.com/dapi/v1/leverageBracket` は HTTP 451(地域制限)。オーナー PC の経路は不要になった。

## 追記 2(リード、2026-09-17): 清算価格の式は画像を取得して読んだ

行動の監査の指摘(この環境の経路を尽くす)で、FAQ ページの式の画像 3 枚を CDN から curl で取得(生ログ [20]〜[23]、HTTP 200、`docs/DATA/probes/20260917_binance_cm_liq_formula/*.png`)し、画像を開いて読んだ。**以下はリードが画像を目視で転記したもの(OCR ではない。転記の誤りはリードの責任)。**

- 画像 1(`c3b054659cea972644d9d1aec5c01694.png`):
  `LP = (B × MMR_B + L × MMR_L + S × MMR_S + sideBOTH × B + L − S) / ((WB − TMM1 + UPNL1 + cum_B + cum_L + cum_S)/CM + sideBOTH × B/EP_B + L/EP_L − S/EP_S)`
- 画像 2(`4cd2d13b2dbda229afd10b34e28cb785.png`):
  `TMM1 = MaintenanceMargin2 + MaintenanceMargin3 + … + MaintenanceMarginN`、`MaintenanceMargin2 = Position2 × CM × MMR2 / MP2 − cum2`
- 画像 3(`8a52fda995cbbf0a65ec8544412e351e.png`):
  `UPNL1 = UnrealizedPNL2 + UnrealizedPNL3 + … + UnrealizedPNLN`、`UnrealizedPNL1 = Σ Position1 × Side1 × CM × (1/EP1 − 1/MP1)`

**主張 B の判定を「一次資料で確認(画像から目視転記)」に改める。**片側 1 建玉・分離マージン(TMM1 = UPNL1 = 0、cum = 0)・証拠金 WB = B × CM / (EP × L) を入れると、ロングは LP = EP × L(1 + MMR)/(L + 1)、ショートは LP = EP × L(1 − MMR)/(L − 1)。建値からの損失率は (1 − L × MMR)/(L ± 1) で、主張の「1/L − MMR」はその近似(L = 75、MMR = 0.4% で 92.1bp 対 93.3bp、差 1.3%)。主張の形「建値 × L / (L ± 1 ∓ MMR × L)」とは書き方が違う(分子に (1 ± MMR) が付く形)が、損失率の近似としては同じ。
