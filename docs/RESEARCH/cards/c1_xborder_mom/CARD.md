# カード 1: 今の paper bot の戦略(c1_xborder_mom)

W4 の仕様 `docs/DISCUSSIONS/2026-10-02_W4_spec.md` §1 の 1 枚目。測る前に書く(第 4 版 §3-1、W1 の仕様 C6)。
この回は測らない(リードの読みを通ってから測る。W4 の仕様 §2 の 4)。
主張の印: 【事実】= ファイル・出力で確かめた / 【推定】= 確かめていない読み / 【仮定】= 置いた前提。

## 原文(逐語)

このカードの原文は **今の paper bot のコードと設定** と、その動きを書いた段 7 の設計 §5-1 である。以下は改変なしの逐語(行番号は 2026-10-02 の作業ツリー)。

**(S1)`src/bot/strategy/xborder_momentum.py` 全文の要部(1〜11 行の docstring と 23〜52 行)**

```python
"""Cross-exchange momentum: follow strong moves on a leader market (Binance)
in the local (bitFlyer) market.

Research basis (docs/RESEARCH_REPORT): Binance XRPUSDT leads bitFlyer XRP_JPY
by 1-3 minutes (lag-1 corr +0.18). Average drift after ordinary moves is below
cost; only large leader moves (>= ~0.8% over 10-30 min) showed material
follow-through, on a statistically insufficient sample. This strategy exists
to VALIDATE that signal in paper trading; it is not proven.

The candles frame must carry a `leader_close` column; missing/stale leader
data yields HOLD.
"""
class XborderMomentumStrategy(Strategy):
    @property
    def min_history(self) -> int:
        return int(self.params.get("k", 10)) + 2

    def on_candles(self, candles: pd.DataFrame) -> Signal:
        k = int(self.params.get("k", 10))
        thr = float(self.params.get("thr_pct", 0.8)) / 100
        exit_band = float(self.params.get("exit_pct", 0.1)) / 100

        if "leader_close" not in candles.columns:
            return Signal(SignalType.HOLD, "no leader data column")
        if len(candles) < self.min_history:
            return Signal(SignalType.HOLD, "insufficient history")

        leader_now = float(candles["leader_close"].iloc[-1])
        leader_past = float(candles["leader_close"].iloc[-1 - k])
        if math.isnan(leader_now) or math.isnan(leader_past) or leader_past <= 0:
            return Signal(SignalType.HOLD, "leader data gap")

        mom = float(np.log(leader_now / leader_past))
        ind = {"leader_mom_pct": mom * 100, "leader_close": leader_now,
               "close": float(candles["close"].iloc[-1])}
        if mom > thr:
            return Signal(SignalType.BUY, f"leader +{mom*100:.2f}% over {k} bars", ind)
        if mom < -thr:
            return Signal(SignalType.SELL, f"leader {mom*100:.2f}% over {k} bars", ind)
        if abs(mom) <= exit_band:
            return Signal(SignalType.CLOSE, f"leader momentum faded ({mom*100:.2f}%)", ind)
        return Signal(SignalType.HOLD, "between exit band and threshold", ind)
```

docstring の 4〜8 行(Research basis)は過去の調べの数値である。このカードでは意図にも根拠にも使わない(全捨て L-019。CLAUDE.md §5)。

**(S2)`config/config.yaml` の該当行(3・4・13〜17・19〜23・30〜33・35〜37・39〜42 行)**

```yaml
product_code: FX_BTC_JPY     # Lightning FX: 0% taker fee, shortable, 2x leverage
candle_interval_sec: 60
# Basis-anomaly guard: refuse NEW CFD entries when |CFD-spot| divergence is
# abnormal. (The old SFD fee band no longer exists — Crypto CFD uses an 8h
# funding rate instead — but extreme divergence still signals a market you
# don't want to enter.)
sfd_guard_pct: 4.5
# Paper-trading validation target (see docs/RESEARCH_REPORT_2026-08-20*.md):
# follow Binance BTCUSDT moves on bitFlyer FX_BTC_JPY, long AND short.
# UNPROVEN — paper only. Params are set from the FX research (train/val only).
strategy:
  name: xborder_momentum     # ema_cross | rsi_reversion | breakout | xborder_momentum | composite
  params:
    k: 30                    # leader momentum window (bars)
    thr_pct: 0.8             # enter long above +thr, short below -thr (%)
    exit_pct: 0.05           # flatten when |leader momentum| fades below this (%)
# Protective stop: flatten any position losing more than this % of entry price.
# Also defines the per-trade estimated loss used by the pre-trade risk checks.
stop_loss_pct: 0.5
# Leader market feed for xborder_momentum (public Binance data, read-only)
leader:
  exchange: binance
  symbol: BTCUSDT
```

**(S3)`docs/DISCUSSIONS/2026-10-02_W5_stage7_design.md` §5-1(段 7 の設計。今の動きの説明と、kind を出す理由)**

> 今の動き【事実: `src/bot/strategy/xborder_momentum.py` 25〜52 行、`main.py` 760〜808 行、`config/config.yaml` 30〜33 行】:
> - Binance の k 本前からの値動き(対数)mom。k = 30、入る閾値 0.8%、決済の帯 0.05%。
> - mom > 0.8% で「買い」、< −0.8% で「売り」、|mom| ≤ 0.05% で「決済」、その間は「様子見」。Binance の値が無ければ「様子見」。
> - 「買い」のとき: 売りを持っていれば**決済だけ**(ドテンしない。次の足でまだ「買い」なら買う)。持っていなければ、SFD の守りが通れば買う。「売り」も向きを逆にして同じ。持っている向きと同じなら何もしない(増し玉しない)。
> - 損切り: 足が完成したときだけ、含み損が 0.5% 以上なら決済(版の判断より先)。損切りのあと「様子見」なら持たないまま。
>
> これを 2 つに分ける:
> - **カード `xborder_mom`**: e = +1(買い)/ −1(売り)/ 0(決済)/ 前の足の e(様子見)。`kind` に「買い・売り・決済・様子見」を入れる。
> - **版 X0 の合成器 `legacy_xborder`(旧互換)**: e ではなく `kind` と自分の持ち高から、上の「買い」「売り」「決済」の規則どおりに注文を出す。
>
> `kind` を出す理由: 目標の持ち高を追う合成器(target = e × 量)だと、(1) 売りを持っているときの「買い」で 1 本の足でドテンする、(2) 損切りのあとの「様子見」で e = +1 のままなので建て直す。どちらも今の bot と違う動きになる。今の動きと同じにするには、「買い」と「様子見で前が買い」を見分ける必要があり、e だけでは見分けられない【事実から導いた設計】。

同 §5-2 の T-A の場面から: 「Binance の値の抜け(2 枠前までの遡りと、それを超える抜け)」

**(S4)`src/bot/market_data/external_feed.py`(Binance の値の作り方)**

> The feed builds per-interval closes that
> main.py merges into the candles frame as a `leader_close` column. On any error
> the feed reports no data and the strategy holds — never trades on a stale or
> missing leader price.

> `def close_for(self, interval_start: int, max_age_intervals: int = 2) -> float | None:`
> """Close of the given interval, falling back to at most
> `max_age_intervals` earlier intervals; None when data is too stale."""

**(S5)`src/bot/main.py` の注記**: 764 行「`return  # decide only on completed candles`」/ 772 行「`# protective stop-loss overrides the strategy`」/ 768〜771 行「`[self.leader_feed.close_for(c.start) for c in self.candles.completed]`」

**このカードを選んだ理由(W4 の仕様 §1 の表の 1 行目、逐語)**:

> **今の paper bot の戦略 `xborder_mom`**(Binance の k 本の値動きで bitFlyer を持つ) | (a) 段 7 の橋(L-552 で案 A)は、この戦略をカードに移して新旧を同じ入力で並べるところから始まる。研究のプログラムと本番のプログラムを同じにする要求(L-540)の最初の 1 枚 (b) paper で今動いている唯一の戦略で、本番の結果と研究の測定を突き合わせる輪(計画 §2-2)を最初に回せる (c) 段 3-B の 1 行目「どちらが先に動くか」に当たる

**オーナーの原文(この種類のカードを測る理由。カードの中身ではない)**:

- L-019: 「**私が思いつく戦略と、私が思いつけないあなたが見つけた戦略を、片っ端から検証し知見を深め、最強の戦略へブラッシュアップしていく**」(CLAUDE.md §5 の逐語)
- L-536: 「**戦略の特性(強み弱み)を理解するためなら短い封印期間を使わずに大量データから学習する方が理にかなってる**」(委任文に引かれた部分。全文は `docs/OWNER_LOG.md` 545 行)
- L-539: 「**海外取引所で見つかったエッジが日本取引所で効くのか、または海外取引所と日本取引所の違いを利用したエッジを考える行動が、統合よりも前にないとこの計画は成立しません**」(委任文に引かれた部分。全文は `docs/OWNER_LOG.md` 548 行)

## 意図の地図

全文は `docs/RESEARCH/cards/c1_xborder_mom/INTENT_MAP.md`。項の一覧と印だけを写す。

| # | 意図(原文の該当語) | 印 |
|---|---|---|
| I-1 | 持つ銘柄 = bitFlyer FX_BTC_JPY | ○ |
| I-2 | 信号の市場 = Binance BTCUSDT | ○ |
| I-3 | 信号 = Binance の k 本前からの値動き(対数) | ○(k 本 = Binance の k 分) |
| I-4 | k = 30 | ○ |
| I-5 | 1 本 = 1 分 | ○ |
| I-6 | mom > 0.8% で買い | ○ |
| I-7 | mom < −0.8% で売り | ○ |
| I-8 | \|mom\| ≤ 0.05% で決済 | ○ |
| I-9 | その間は様子見 | ○ |
| I-10 | Binance の値が無ければ様子見 | ○ |
| I-11 | 抜けは 2 枠前まで遡る | ○ |
| I-12 | 足の区間の Binance の終わりの価格 | △ 代理(Binance の 1 分足の close) |
| I-13 | 判断は足が完成したときだけ | ○ |
| I-14 | 判断の足 = 毎分 | △ 代理(研究の口は約定の有る分だけで判断) |
| I-15 | e = +1 / −1 / 0 / 前の e | ○ |
| I-16 | kind(買い・売り・決済・様子見)を出す | ○ |
| I-17 | 損切り 0.5% | ✕(射程外: bot の守り、カードの外) |
| I-18 | ドテンしない・増し玉しない | ✕(射程外: 合成器 X0) |
| I-19 | SFD の守り | ✕(射程外: bot の守り) |
| ＋ | 履歴の門 k + 2 / past ≤ 0 で様子見 / 0 以下の値の −inf・NaN の扱い / `np.errstate` / 記録(mom ほか)/ 水準を引数で変えられる / コードの既定値(外した) | ＋ |

## なぜ

測る前の 3 問(第 4 版 §3-1)。原文(S1〜S5)には「なぜ」の文が無い。S1 の docstring の「Research basis」は過去の調べの数値で、全捨て(L-019)により使わない。以下はリードの読みを待つ**仮説**で、どれも【仮定】。

1. 誰が損をしているか: bitFlyer FX_BTC_JPY で、Binance の値動きが bitFlyer の板に伝わる前の値段で約定する人(更新の遅い指値を置いたままの人、Binance を見ずに成行を出す人)【仮定】。
2. なぜ続くか: BTC の値段は、出来高の大きい海外の取引所で先に決まり、bitFlyer(円建て・参加者が違う・円と USDT の間の資金の移動に時間がかかる)には少し遅れて伝わる。大きな動き(30 分で 0.8% を超える)ほど、伝わり切るまでに時間がかかる【仮定】。
3. 何で崩れるか: (a) 裁定する人が速くなり、1 分足より短い間に伝わり切る (b) bitFlyer の独自の動き(円の上乗せ・SFD の時代の価格差)が Binance の動きを打ち消す (c) 大きな動きの後に行き過ぎの戻りが来る(追いかけた側が損をする)【仮定】。

## 期待する向きと場面

- 向き: Binance が 30 分で 0.8% を超えて上げた後、bitFlyer の次の足も上げる側(持ち高 +1 の損益が正)。下げも同じで向きが逆。未測【仮定】。
- 場面: 大きな動きが起きやすい場面(局所ボラの高い時)に e ≠ 0 の足が集まる【推定: 閾値の作りから】。制度は全部 SFD の時代(W4 の仕様 §3)。
- 段 3-B の「どちらが先に動くか」(W4 の仕様 §1)に当たる。言葉の判定はしない(計画 段 2 の訂正)。区間の両端と MDE を並べる(W4 の仕様 §3)。

## 反証

- 持ち高 e_t の経費前の損益 P_t(W1 の C2)の平均の区間が 0 を含まず負にあれば、「Binance の大きな動きに bitFlyer が付いてくる」という仮説は違う。
- 区間が 0 を含み、MDE(C5 の e)が十分に小さいのに効果が見えなければ、「付いてくるとしても小さい」。MDE が大きければ「不明(検出力が足りない)」(W1 の仕様 C5 の e)。
- ずらした対照(C5 の d)の分布の中ほどにあれば、信号の時刻は効いていない。
- ドリフトを除いた損益(C5 の b)が 0 に近く、生の平均だけが正なら、効いているのは信号ではなく期間の上げ下げ。

## 関数のパス

- `src/bot/research/cards/library/c1_xborder_mom.py` の `XborderMom()`(既定値 = 今の bot の設定。kind は `last` と `kinds()`)。
- 試験: `tests/research/cards/library/test_c1_xborder_mom.py`。

## 水準とその出所

どれも今の bot が動いている値で、カードは同じ値を使う(新旧を同じ入力で並べるため。W4 の仕様 §2 の 5)。値の裏にある過去の調べ(config の注記「Params are set from the FX research」)は根拠に使わない(L-019)。出所は「今の bot がこの値で動いている」ことだけ。

| 水準 | 値 | 出所 |
|---|---|---|
| k(窓の本数) | 30 | `config/config.yaml` 31 行「k: 30」【事実】 |
| 入る閾値 | 0.8%(`thr_pct / 100`) | `config/config.yaml` 32 行「thr_pct: 0.8」【事実】 |
| 決済の帯 | 0.05%(`exit_pct / 100`)、境は ≤ | `config/config.yaml` 33 行「exit_pct: 0.05」、境はコード 50 行「`abs(mom) <= exit_band`」【事実】 |
| 1 本の長さ | 1 分 | `config/config.yaml` 4 行「candle_interval_sec: 60」(bot の足と Binance の枠の両方。main.py 146・166 行)【事実】 |
| 抜けの遡り | 2 枠 | `src/bot/market_data/external_feed.py` 50 行「max_age_intervals: int = 2」(main.py は引数を渡さないので既定値で動く)【事実】 |
| 履歴の門 | k + 2 本 | コード 26 行「`int(self.params.get("k", 10)) + 2`」【事実】 |
| 乱数・種 | 使わない | — |

コードの既定値(k 10・exit 0.1)は使わない(動いていない)。水準を変えて測るなら、別の版として記録する(第 4 版 §3-1)。

## 使うデータと遅れ

- `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2017.csv.gz`
- `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2018.csv.gz`
- `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2019.csv.gz`
- `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2020.csv.gz`
- `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2021.csv.gz`
- `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2022.csv.gz`
- `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2023.csv.gz`
- `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2017.csv.gz`
- `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2018.csv.gz`
- `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2019.csv.gz`
- `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2020.csv.gz`
- `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2021.csv.gz`
- `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2022.csv.gz`
- `backtest_data/binance_BTCUSDT_1m_20170801_20231231/binance_BTCUSDT_1m_2023.csv.gz`

役と、使えるようになる時刻:

| 系列 | 役 | 置き場の時刻の列 | このカードでの行の時刻 | 遅れ | 出所 |
|---|---|---|---|---|---|
| bitFlyer FX_BTC_JPY 1 分足 | 持つ銘柄の足(損益。カードは足の始まりの時刻と本数だけを読む) | `ts` = 1 分の始まり(UTC) | 足の終わり = `ts` + 60 秒(W1 の C2: 足の受け取り時刻 = 終わり) | 足の終わりで使える | 置き場の README「`ts` — start of the 1-minute bucket, ISO-8601 UTC」【事実】 |
| Binance BTCUSDT 1 分足の close | 参照 `binance_btcusdt_close`(`now` と `past` の値) | `open_time`(UTC) | `open_time` のまま(その分の始まり。ずらさない) | lag_ns 60,000,000,000(60 秒。その分の終わりに使える) | 置き場の README「`open_time` (ISO-8601 UTC)」と `binance_1m_index.json` の `"time_column": "open_time"`【事実】 |

- **行の時刻は置き場の `open_time` のまま(ずらさない)、遅れ 60 秒**(リードの答え、`INTENT_MAP.md` §9 の 1)。`load_reference` でそのまま読める【事実: `src/bot/bt/data/reference.py` の docstring のファイルの形に時刻の列と単位の項目がある】。カードは t で終わる分の行を、行の時刻 t − 60 秒で引く。遅れ 0 の宣言(open_time の行では close を 1 分早く読む)の系列を渡すと、カードの `requires` の遅れ(60 秒)と違うので `run_card` が拒む【事実: 試験 `test_other_lag_is_refused`】。カード 3 にもリードが同じ形を指示する(リードの答え)。
- bitFlyer 2023 年のファイルは封印の台帳に載っている(境 2023-12-18 00:00 UTC)【事実: `backtest_data/phase2_sealed/P2-08/SEALED.json`】。データ層は境より前の行だけを返す(`bot.bt.data.allowlist`)。測る期間は境の前で終わる。

## 約定の模型

- 成行。足の終わり t に出した持ち高 e_t は、次の足の始値で約定したとみなす(W1 の仕様 C2)。空の足は次の空でない足の始値(同 C2)。
- 経費は入れない(段 2 は経費前。W1 の仕様 §0)。
- 今の bot は足が完成した直後に成行で出す(main.py)。研究の「次の足の始値」はその代理【推定】。

## 測定の設定

- vr_q_bars: なし | 出所: W4 の仕様 §3「vr の q = 原文に無ければ「なし」」。原文(S1〜S5)に vr の q は無い
- day_zone: Asia/Tokyo | 出所: W4 の仕様 §3「日の境 = Asia/Tokyo(bitFlyer の日と、オーナーの時間で読むため)」
- 参照: binance_btcusdt_close | lag_ns: 60000000000 | 出所: リードの答え(2026-10-02、カード 1 の差し戻し 1 回目の 1)「行の時刻 = 置き場の open_time のまま(1 分の始まり)、lag_ns = 60 秒」。置き場の README「`open_time` (ISO-8601 UTC)」と `binance_1m_index.json` の `"time_column": "open_time"` により行の時刻は 1 分の始まりで、その分の close は 60 秒後の分の終わりに使える

## 測る期間

- 開始: 2017-08-17T15:00:00Z
- 終了: 2023-12-17T15:00:00Z

- 日の境が Asia/Tokyo なので、始まりと終わりを日本時間の日の境にそろえた(リードの答え、`INTENT_MAP.md` §9 の 3)。
- 開始 = 系列がそろう最初の日本時間の 0 時。Binance の最初の行は 2017-08-17 04:00 UTC = 日本時間 13:00(`binance_1m_index.json` の 2017 の `first`)、bitFlyer FX の 1 分足は 2015-11-28 04:54 UTC から(README)、USDJPY は 2017-08-01 から(W4 の仕様 §3。このカードは使わない)【事実】。その後の最初の日本時間の 0 時は 2017-08-18 00:00 JST = 2017-08-17T15:00:00Z。
- 窓(k = 30 分)の分の Binance の行は、開始の前(2017-08-17 04:00〜15:00 UTC)にある【事実: index の `first`】。測る足の系列を開始から始めるなら、履歴の門(k + 2 本)により最初の 31 本は「様子見」になる。開始より前の足を履歴として渡すかは、測定を組む側が決める(この回は測らない)。
- 終了 = 2023-12-17T15:00:00Z(日本時間の 2023-12-18 00:00。封印の境 2023-12-18 00:00 UTC の 9 時間前)。[開始, 終了) で、日本時間の 2017-08-18 〜 2023-12-17 の日がちょうど入る。
- 封印の境(2023-12-18 00:00 UTC。bitFlyer FX と Binance の両方)より後にかからない【事実: `scripts/check_card.py` が通る】。
