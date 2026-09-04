# AP — OI急増 / L-S比極値 regime pending diagnostics（Claim P2 再監査）

独立実装で再計算。予算: ツール呼び出し ~24回（上限40）。読んだファイル一覧は末尾。

## 1. Denominator（母集団・n・ギャップ）

- `paper_logs/oi_snapshots.csv`: n=1297, 2026-08-20T12:00〜2026-09-04T12:45, **span=15.03日**。
  claim文言の「30日到達でフェーズC判定」の**30日バーは未到達**（15日、達成率50%）。
  15分刻み想定に対し欠測ギャップ(>20分)131件、完全性89.9%。さらに致命的な点として
  `btc_usd`（価格）列は先頭1084行(83.6%)が空欄で、**価格が入り始めるのは2026-09-02T05:15以降の213行だけ**
  （2.3日分）。つまりこのファイル単体では1h/4h/24hの「次期実現レンジ・符号付リターン」回帰は
  ほぼ不可能（nが2〜9程度しか取れない）。
- 一方 `backtest_data/okx_btc_oi_1h_20260823.csv` / `okx_btc_lsratio_1h_20260823.csv` は
  2026-07-24T13:00〜2026-08-23T12:00の**固定30日窓**(n=720、連続、欠測0、重複0)を既に保持している。
  `backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz`（2026-01-22〜2026-08-20T11:36、302,403行）と
  時刻結合すると重複時刻647時間分の重なりが取れる（2026-07-24T13:00〜2026-08-20T11:00）。
  → **「30日到達を待つ」という前提自体が誤り**。この30日固定OKXスナップショットで診断は今すぐ可能。
- 5分足OKXファイル(`okx_btc_oi_5m_20260823.csv`/`lsratio_5m`, n=576, 2026-08-21〜08-23)はBinance 1m価格と
  **重なりが皆無**（1m価格は08-20T11:36で終了）。次期レンジ/リターン回帰には使用不能（n=0）。
- 日次: `backtest_data/regime_composite_20260901/raw/binance_metrics.csv`(OI, 2021-01-01〜2026-08-31, n=2069)
  + `raw/price_daily.csv`(Bitstamp日次OHLC, 2015-07-01〜2026-08-31)を結合しn=2067(2021-01-02〜2026-08-30)。
  `features_daily.csv`のls_ratio/toptrader_lsも2021-01-01始まりでn=2050/1754確保できた。
  ※ パケット記載の `data/binance_daily/*.csv`(2021年〜想定)は**存在しない**。実データは
  `paper_logs/binance_daily/metrics.csv`（32行、2026-08-04〜09-03のみ）と、上記regime_composite内
  `raw/binance_metrics.csv`(2021〜、こちらが本物の長期データ)の二系統があり紛らわしい。

## 2〜10 主要な再計算結果

**(a) OKX時間足 OI変化 |Δ| → 次期レンジ/符号付リターン**（n=644-599, Newey-West lag=2×horizon）

| horizon | β(range~|ΔOI|) | NW-t | shuffle p | β(ret~ΔOI) | NW-t | shuffle p |
|---|---|---|---|---|---|---|
| 1h | -0.0004 | -0.21 | 0.86 | +0.0017 | 1.13 | 0.39 |
| 4h | -0.0028 | -1.03 | 0.57 | +0.0071 | 1.22 | 0.13 |
| 24h | **+0.0556** | **3.91** | **0.028** | **-0.0452** | **-2.36** | **0.034** |

**データ検証で崩壊**: `okx_btc_oi_1h` に **OI=0.0（出来高は非ゼロ）の欠損ティックが2件**
(2026-08-19T03:00, 2026-08-22T00:00)。重なり窓に入る2026-08-19T03:00の1点が h=1h/4h/24h いずれの
|ΔOI|も理論上限の100%(=-1.0)という外れ値を生成する。線形補間で修正して再計算:

| horizon | β(range~|ΔOI|) fixed | NW-t fixed |
|---|---|---|
| 1h | +0.1114 | **2.82**(符号反転) |
| 4h | +0.0282 | 0.75 |
| 24h | **-0.0801** | **-0.67**(符号反転・有意性消失) |

24hの「有意」はこの1件のデータ欠損ティックが単独で作った人工物。1hは逆に補正後に有意化するが
標本は同一647時間の重複窓で本質的に独立情報が乏しい（後述MDE参照）。**OI変化→レンジのmagnitude
効果は頑健に再現しない。**

**(b) OKX時間足 L-S比変化 |Δ| → 次期レンジ/リターン**（L-S比自体はゼロ・外れ値なし、検証クリア）

| horizon | β(range~|Δls|) | NW-t | shuffle p | β(ret~Δls) | NW-t | shuffle p |
|---|---|---|---|---|---|---|
| 1h | +0.0515 | **2.33** | **0.002** | -0.0099 | -0.74 | 0.05 |
| 4h | +0.0325 | **2.43** | **0.002** | -0.0073 | -0.74 | 0.13 |
| 24h | -0.0087 | -1.00 | 0.11 | -0.0091 | -0.91 | 0.05 |

1h/4hでL-S比変化幅とレンジに正の関係（shuffleでも有意）。ただし24hでは消える＝短期のみ。
方向(ret)側は弱く不安定＝「magnitudeゲート、directionではない」という主張の方向は一応支持。

**(c) 日次 Binance先物OI・トップトレーダーL-S比（2021-2026, n=2067/1752/2048, 独立データ源）**

| 変数 | top10% mean_range | bottom10%/middle | 傾き(level→range) NW-t | 傾き(level→ret) NW-t |
|---|---|---|---|---|
| |ΔOI| (magnitude) | n=599(top decile), 0.1997 | — | β=+0.1997, **t=3.92**, shuffle p=0.002 | β=-0.0174, t=-0.74, ns |
| toptrader_ls (level) | top=3.46%, bottom=4.02%, mid=**4.42%** | 両極値ともmiddleより**レンジが低い**(仮説と逆符号) | β=-0.0106, **t=-3.68** | β=-0.0033, t=-1.98 |
| ls_ratio (level) | top=**5.80%**, bottom=3.49%, mid=4.27% | 上側のみ拡大・下側は縮小(非対称) | β=+0.0093, **t=5.71** | β=-0.0031, **t=-2.86** |

日次OIのmagnitude効果はこの独立系列でも有意で頑健（欠損ティックなし、クリーン）。一方
**L-S系の「極値=レンジ拡大」という対称magnitude仮説は不成立**: toptrader_lsは両極値で
レンジが**縮小**（仮説と逆）、ls_ratioは上側のみ拡大・下側は縮小という非対称＝実質は
"level/direction"効果（ls_ratioのret回帰もt=-2.86で有意）であり、"方向ではなく規模"という
claimの前提と矛盾する。さらにtoptrader_lsとls_ratioは同じ「L-S比極値」概念でありながら
**符号が逆**＝指標依存で一般化しない。

**regime条件付け（Q4）**: 24hのボラティリティ・トライアル分割（trailing 24hレンジで三分位）で
|ΔOI_24h|→レンジのβはlow=-0.26(t=-1.29,n=214), mid=+0.06(**t=8.11**,n=214), high=+0.08(t=1.50,n=171)。
効果は中ボラ帯に集中し全レジーム一様ではない＝「絶対的なmagnitude効果」ではなくvol-regime条件付き。

**コスト換算（Q3, 使用値: `config/config.yaml costs.taker_fee_pct=0.15%` + `slippage_pct=0.05%`,
往復想定 2×(0.15+0.05)=**40bps**、claim側の数値は使わずconfigから導出）**:
日次ls_ratio top-decile方式のレンジ差 (5.80%-4.27%=153bps)は40bpsコストを大きく上回るが、
同時にret方向にも-53.8bps(top) vs +12.6bps(mid)の有意差があり、これは「レンジ拡大」ではなく
方向性シグナルの副産物の可能性が高い。時間足L-S 1h/4hのレンジ差(23bps/28bps程度)は
40bpsコスト未満で、そのままでは往復コストを賄えない。

**MDE（Q10）**: 24h水平線は27日の重複窓しか無く、Newey-West有効n(lag=48)は**約6**まで縮む
（overlap補正）。この水準で検出できる最小効果は概算でレンジ標準偏差の作用として1.8%程度必要
（観測差は1.9%台で辛うじて閾値付近）＝**24h検定は事実上検出力不足**。日次系列(n≈2000)は
neff≈160-190で、range MDE≈0.6-0.7%（95%/80%）——観測された1.5%差はこの閾値を超えるため
統計的検出力は足りているが、上記の符号矛盾・方向性混入で解釈的には支持されない。

**Q8簡便代替説明**: 中ボラ帯に効果が集中する点(Q4)は「OI変化そのもの」ではなく
ボラティリティ・クラスタリングが両者(OI変化・レンジ)を同時に動かす交絡である可能性が高い
（他の代替: 同時多発清算がOIとレンジを共に動かす、など）。

## Verdict: **結論変更**

| 項目 | claim(pending diagnostic) | 再計算 |
|---|---|---|
| 30日到達 | 蓄積待ち・未到達で判定不能とされていた | oi_snapshots.csvは15日で未到達は事実。だが**既存のOKX 30日固定スナップショット＋2021年からの日次データで代替検証可能**——「判定不能」は誤り |
| OI急増→レンジ(magnitude) | 未検証(pending) | 時間足はデータ欠損ティック1件で結果が反転する非頑健な結果。日次(独立系列)は有意(t=3.92)で頑健 |
| L-S極値→レンジ(magnitude) | 未検証(pending) | 時間足1h/4hで有意な対称効果あり(shuffle p=0.002)。しかし日次では非対称・指標間で符号矛盾、方向性成分も有意で「magnitudeのみ」の前提と矛盾 |

一文: 蓄積待ちという前提を外して既存データで診断した結果、OI変化のmagnitude効果は
時間足では単一の欠損ティックに依存する人工物だが日次の独立系列では頑健に残り、
L-S比極値の対称magnitude効果は短期時間足でのみ見られ日次では方向性/指標依存に崩れる——
「規模のみ・方向は無関係」という単純化は日次データでは支持されない。

## 前提の誤り

1. premise: 30日蓄積(`paper_logs/oi_snapshots.csv`)まで判定不能 | source: パケットAP本文 |
   data: 既存の`okx_btc_oi/lsratio_1h_20260823.csv`(固定30日, 2026-07-24〜08-23)と
   `regime_composite_20260901/raw/binance_metrics.csv`(2021〜)で即時検証可能 |
   bias: 判定を不必要に先送りしている方向 | 波及: 他の「蓄積待ち」系pending診断すべて
2. premise: `data/binance_daily/*.csv`に2021年からのtop-trader L-S・OIがある | source: 監査依頼の
   DATA記載 | data: そのパスは存在せず、`paper_logs/binance_daily/metrics.csv`は32日分のみ。
   本物の2021〜長期系列は`backtest_data/regime_composite_20260901/raw/binance_metrics.csv`にある |
   bias: 中立(データ自体は別経路で発見できた) | 波及: 同じパス表記を参照する他パケット
3. premise: OKX OI時系列はクリーン | source: 暗黙 | data: `okx_btc_oi_1h`に出来高非ゼロなのに
   OI=0の欠損ティックが2件あり、うち1件が重なり窓内でh=24h回帰の有意性(t=3.91→-0.67)を単独で作っていた |
   bias: 時間足OI効果を過大評価する方向 | 波及: OI系のhの効果を引用する他の全claim
4. premise: L-S比極値は方向非依存(magnitudeのみ)の効果 | source: パケットAP本文の枠組み |
   data: 日次でls_ratioとtoptrader_lsは符号が逆、かつls_ratioのret回帰はt=-2.86で有意
   ＝方向性が混入 | bias: magnitude解釈を過信させる方向 | 波及: 「OI/L-S急増を規模ゲートとして
   使う」将来の実装案全般

## 読んだファイル
`docs/AUDIT_2026-09/PROTOCOL.md`, `docs/AUDIT_2026-09/00_packets.md`(P2/APの行のみgrep),
`paper_logs/oi_snapshots.csv`, `backtest_data/okx_btc_oi_1h_20260823.csv`,
`backtest_data/okx_btc_oi_5m_20260823.csv`, `backtest_data/okx_btc_lsratio_1h_20260823.csv`,
`backtest_data/okx_btc_lsratio_5m_20260823.csv`, `backtest_data/binance_BTCUSDT_1m_210d_20260820.csv.gz`,
`paper_logs/binance_daily/metrics.csv`, `backtest_data/regime_composite_20260901/features_daily.csv`,
`backtest_data/regime_composite_20260901/manifest.json`,
`backtest_data/regime_composite_20260901/raw/binance_metrics.csv`,
`backtest_data/regime_composite_20260901/raw/price_daily.csv`, `config/config.yaml`, `config/products.yaml`.
