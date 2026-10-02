カード c9(清算の連鎖)の調達票

研究手順書 §14 の表。到達確認は、データの置き場の目録(README・MD5SUMS の名前・`candles_1m_index.json`・取得の道具の docstring・`manifest.json`)と `ls` と封印の台帳の読み出しだけで行った。**データの行は開いていない**(封印の中も外も。清算の zip も解いていない。測定はまだ)。`md5sum -c` は打っていない(bitFlyer の 2023 年のファイルは封印の行を含む。清算の置き場も同じく打っていない)。
主張の印: 【事実】= この回にファイル・出力で確かめた / 【推定】/ 【未確認】= この回に叩いていない。

## 1. 主に使うデータ(CARD.md の「使うデータと遅れ」)

最小 n: 定めない。W1 の測定器が検出力(C5 の e)を出し、効果が見えないときに「不明(検出力が足りない)」と「小さい」を分ける(W1 の仕様 C5)。n を先に決めて足切りしない(A-8)。

| 必要データ(市場・粒度・期間・最小 n) | 入手経路の候補(3 つ以上) | 到達確認(日付・方法・結果) | 欠けと対処 |
|---|---|---|---|
| bitFlyer FX_BTC_JPY・1 分足(損益の始値と、時刻の確かめ。カードは値段を判断に使わない)・2023-06-25T15:00Z〜2023-12-17T15:00Z | (1) 手元 `backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/candles_1m_2023.csv.gz` (2) 手元 `backtest_data/fx_btc_jpy_1m_continuous_*/`(市場の表にある別の置き場。中身は読んでいない【未確認】)(3) bitFlyer 公開 REST の約定から組む — 約 31 日分しか遡れない(N-002)ので、この期間には使えない | 2026-10-02、`ls -la` と `candles_1m_index.json` を読んだ【事実】: `time_column: ts`、2023 年 525,600 行、`first` 2023-01-01 00:00、`last` 2023-12-31 23:59、18,962,595 バイト。README の `ts` の意味(1 分の始まり)は c7 の調達票の引用による【事実: c7 の PROCUREMENT.md §1】 | 2023 年のファイルは封印の境の後の行を含む。測る期間の終わりで切る(測定器)。約定 0 の分ではカードは呼ばれないが、清算の分は 1 分ずつ全部読む(INTENT_MAP.md ＋-10) |
| Binance COIN-M BTCUSD_PERP の強制決済(1 件ごと: 時刻ミリ秒・`side`・数量)・UTC の分に束ねる・2023-06-25〜2023-12-17 | (1) **手元 `backtest_data/binance_cm_o3c_20260913/liquidationSnapshot/BTCUSD_PERP/`**(Binance Vision の日次 zip を配信停止の前に退避したもの)(2) Binance Vision の同じ経路 — 2024-10-13 までは配っていた(N-012)。今も 2023 年の分が取れるかは【未確認】(3) Coinalyze の集計(足ごとに深さが違う。1 分足は約 7 日、日足は 1 年超。`docs/DATA/surveys/LIQUIDATION_HISTORY_SURVEY.md` §2)— 2023 年の 1 分の深さは無い(同表) (4) Binance REST `allForceOrders` — 同 §2 で「不明」(この環境は 451) | 2026-10-02、置き場の README を読み、`ls` で zip の数を数えた【事実】: README「期間: 2023-06-25 〜 2024-10-14(全478日、UTC日次)」「liquidationSnapshot: 478日中 472日 OK / 6日 欠測(404)」「欠測日: 2023-09-09, 2023-09-23, 2023-09-25, 2024-06-01, 2024-06-11, 2024-06-12」。列名 `time,side,order_type,time_in_force,original_quantity,price,average_price,order_status,last_fill_quantity,accumulated_fill_quantity`(README の見本)。`ls … \| wc -l` = 944(zip 472 + `.CHECKSUM` 472)、最初 `BTCUSD_PERP-liquidationSnapshot-2023-06-25.zip`、最後 `…-2024-10-14.zip.CHECKSUM`。`side` の意味: `SELL` = ロングの強制決済、`BUY` = ショートの強制決済(`docs/DATA/surveys/O3C_VERIFY_LIQUIDATION_SIDE_2026-09-13.md` 8・27 行) | (a) 期間の中の欠測 3 日(2023-09-09・09-23・09-25)は行を置かず、カードは 0(INTENT_MAP.md ＋-7) (b) README の見本に全く同じ行が 2 行ある。重ねて数えるかはリードが決める(CARD.md 迷った点 3) (c) **`scripts/check_card.py` の `MARKETS` にこの置き場の型が無い**。測定器が読むには表に足す必要がある(CARD.md 迷った点 1) (d) **封印の台帳に載っていない**(§2 の出力)。どう封印を掛けるかもリードが決める (e) 1 件ごとの記録が全件か(取引所が間引いていないか)は【未確認】 |

## 2. 封印の外で使える期間(封印の台帳の読み出し)

`scripts/check_card.py` の `boundaries()`(台帳 `backtest_data/phase2_sealed/*/SEALED.json` 8 単位を、市場の表で市場ごとにまとめる)を打った【事実】:

```
$ python3 -c "import sys; sys.path.insert(0,'scripts'); sys.path.insert(0,'src'); import check_card as c; ..."
jpx:n225_futures 2015-08-29 00:00:00
jpx:cash 2015-08-29 00:00:00
bitflyer:FX_BTC_JPY 2023-12-18 00:00:00
binance:BTCUSDT 2023-12-18 00:00:00
fx:USDJPY 2023-12-18 00:00:00
bitflyer:BTC_JPY 2023-12-18 00:00:00
binance_um:BTCUSDT 2026-08-23 00:00:00
[]
```

台帳に載ったファイルのうち、名前に `liq`・`cm`・`coinalyze` を含むもの: `[]`(同じ呼び出しの出力)【事実】。台帳に載った置き場の名前の一覧(同じ出力)にも清算の置き場は無い。

- 持つ銘柄(bitFlyer FX_BTC_JPY)の境が 2023-12-18 なので、清算の記録がどこまであっても、使えるのは 2023-12-17 まで。
- **使える期間 = 2023-06-25(清算の記録の始まり)〜 2023-12-17**(日本時間の 0 時にそろえて 2023-06-25T15:00Z〜2023-12-17T15:00Z。CARD.md 測る期間)。

## 3. 清算の記録の置き場ごとの期間と、この関所での扱い(調べた範囲)

| 置き場 | 何か | 期間(目録から) | 封印の外(〜2023-12-17)で使えるか |
|---|---|---|---|
| `backtest_data/binance_cm_o3c_20260913/liquidationSnapshot/` | Binance COIN-M 1 件ごと | 2023-06-25〜2024-10-14(README)【事実】 | **2023-06-25〜12-17 が使える**(§2) |
| `backtest_data/binance_cm_o3c_20260913/metrics/`・`aggTrades/`・`fundingRate/`、`binance_cm_o3c_supp_20260917/` | 建玉・約定・資金調達率(清算ではない) | 同じ期間(README) | 清算の記録ではないので、このカードの持ち高には使わない |
| `paper_logs/liquidations/`(PC の記録) | Binance COIN-M・BitMEX・Bybit・OKX の WebSocket の生の受信 | `binance_cm` 2026-09-09〜10-01(25 ファイル)、`bitmex` 2026-09-08〜09-16(12)、`bybit` 2026-09-08〜10-01(25)、`okx` 2026-09-08〜10-01(23)【事実: ファイル名】 | 使えない: 持つ銘柄 bitFlyer FX の封印の境(2023-12-18)より後。原文 A の「PC の記録 2026-09-09〜」はこの関所では測れない(開封の後の範囲) |
| `backtest_data/liquidations_repaired_20260912/`・`…_20260917/` | 上の PC の記録の壊れたファイルを直したもの | 2026-09-08〜09-12(ファイル名)【事実】 | 同上 |
| `backtest_data/gate_liquidations_20260908/` | Gate.io BTC_USDT 1 件ごと | 2026-06-10 16:00〜2026-09-08 16:00(`BTC_USDT.manifest.json` の `window_covered_utc`)【事実】 | 同上(封印の境の後) |
| `backtest_data/coinalyze_liquidations_20260921/` | Coinalyze の 1 分の集計 | 取得の窓 2026-09-14〜09-19(`raw/` のファイル名)【事実】。取得の道具の docstring「遡れるのは約 7 日」 | 同上 |
| `backtest_data/bitmex_insurance_20260912/` | BitMEX の保険基金の日次残高 | 2016-02-28〜2026-09-11(README)【事実】 | 封印の台帳に載っていない・市場の表にも無い。README「個々の清算イベントを1件ごとに特定する情報は含まれない」。清算の代わりにはならない(日次) |
| `backtest_data/bitmex_trade_1s_XBTUSD/`・BitMEX の公開約定 | 約定 | 【未確認: この回は目録を読んでいない】 | 調査の表(`LIQUIDATION_HISTORY_SURVEY.md` §2)は BitMEX の公開約定アーカイブに「清算フラグ無し」と書く。オーナーの PC の BitMEX の約 300 GB(原文 L-139)に清算が含まれるかは【未確認】 |

- 他の経路(調査の表 §2 の「取れる」「未確認」): Hyperliquid の S3 アーカイブ(中身未確認・転送料は当方負担)、CoinGlass(未取得)。2023 年の 1 件ごとの清算がこれらにあるかは【未確認】。この調査の表は 2026-09-08 のもので、Binance を「ストリームのみ、履歴なし」と書くが、その後 COIN-M の `liquidationSnapshot` が Binance Vision から取れた(上の置き場、2026-09-12 取得)。表は Binance USD-M について正しく、COIN-M については古い【推定: README の日付と表の日付からの読み】。
- 「封印の外で 2023 年の清算の記録が他に無い」とは言わない。言えるのは、**手元の置き場のうち、封印の外の期間に清算の記録があるのは Binance COIN-M の 1 つだけ**(この表の範囲)ということ。

## 4. 意図の地図の △ を切り分けるため・「なぜ」を確かめるためのデータ(このカードの持ち高には使わない)

| 必要データ | 入手経路の候補 | 到達確認 | 欠けと対処 |
|---|---|---|---|
| 清算の 1 件ごとの時刻(連鎖の切り方 I-3b の別の形、秒の束ね方) | (1) 上の zip の `time`(ミリ秒)(2) PC の記録の `raw` の中の取引所の時刻(封印の後)(3) Gate の 1 件ごと(封印の後) | 2026-10-02、README の列名で確かめた【事実】 | 持ち高の時刻は bitFlyer の 1 分足で決まるので、秒の束ね方は持ち高を変えない(INTENT_MAP.md §4-1) |
| 建玉(「燃料」の別の観測。原文 L-044「OI・出来高観測・清算履歴」) | (1) `binance_cm_o3c_20260913/metrics/`(5 分ごとの `sum_open_interest`)(2) OKX の建玉(`auto_okx_open_interest_*`、2026-09〜。封印の後)(3) Coinalyze の建玉(未測定。調査の表) | 2026-10-02、README の列名で確かめた【事実】: metrics は 2023-06-25〜2024-10-14 のうち 379 日、欠測は 2023-09-25・2023-11-19 と 2024-03-04〜06-08 | このカードは建玉を使わない。足すかはリードが決める(原文 L-044 は建玉も挙げている) |
| bitFlyer の秒の値段(I-7b) | (1) PC の記録 `paper_logs/tape/`(封印の後)(2) bitFlyer 公開 REST の約定(直近 31 日、N-002)(3) Tardis の毎月 1 日の無料分(計画 第 5 版 3-B の注「今日は 403」) | この回は叩いていない【未確認】 | 封印の外の 2023 年の秒の bitFlyer は手元に無いと計画 第 5 版 3-B の注が書く。この回は確かめていない |

## 5. 否定的事実の引用

- N-012(2026-09-19 登録、賞味 90 日 → 2026-10-02 時点で期限内): Binance Vision の `liquidationSnapshot` は COIN-M BTCUSD_PERP で 2024-10-13 まで、USD-M BTCUSDT は無い【事実: `docs/NEGATIVE_FACTS.md` 16 行】。このカードの期間(2023-06-25〜12-17)は手元の退避分の中。
- N-002(bitFlyer 公開 REST の約定は約 31 日分のみ、賞味 90 日で期限内): §1 の経路 (3) を使えない理由。

## 6. この回に打ったコマンド(到達確認)

```
ls -la backtest_data | grep -i -E "liq|coinm|cm_|force"
ls paper_logs/liquidations ; ls backtest_data/phase2_sealed/
for d in binance_cm_o3c_20260913 binance_cm_o3c_supp_20260917 coinalyze_liquidations_20260921 gate_liquidations_20260908 liquidations_repaired_20260912 liquidations_repaired_20260917; do find backtest_data/$d -maxdepth 2 | head -15; find backtest_data/$d -type f | wc -l; done
cat backtest_data/binance_cm_o3c_20260913/README.md
ls backtest_data/binance_cm_o3c_20260913/liquidationSnapshot/BTCUSD_PERP | wc -l
head -c 1500 backtest_data/gate_liquidations_20260908/BTC_USDT.manifest.json
head -5 backtest_data/coinalyze_liquidations_20260921/MD5SUMS ; ls backtest_data/coinalyze_liquidations_20260921/raw
sed -n 1,40p scripts/fetch_coinalyze_liquidations.py ; sed -n 1,50p scripts/record_liquidations.py
python3 -c "…check_card.boundaries('.', MARKETS) と SealRegistry('.').entries の名前…"(§2 の出力)
grep -n … docs/DATA/surveys/O3C_VERIFY_LIQUIDATION_SIDE_2026-09-13.md
sed -n 28,75p docs/DATA/surveys/LIQUIDATION_HISTORY_SURVEY.md
for v in binance_cm bitmex bybit okx; do ls paper_logs/liquidations | grep "^$v" | sed -n '1p;$p'; done
sed -n 16p docs/NEGATIVE_FACTS.md ; head -30 backtest_data/bitmex_insurance_20260912/README.md
ls -la backtest_data/bitflyer_lightchart_FX_BTC_JPY_1m_20260906/ ; python3 -c "…candles_1m_index.json…"
```
