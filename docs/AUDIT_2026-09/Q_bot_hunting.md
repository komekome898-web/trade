# Packet Q — bot-hunting pick-off continuation law (claims L30, P3)

独立再現。読んだファイル: docs/AUDIT_2026-09/PROTOCOL.md, docs/AUDIT_2026-09/00_packets.md (grep 行のみ: L30, P3, セクション1.2/1.4), config/products.yaml, backtest_data/venue_survey_20260827/FINAL.txt, paper_logs/tape/ticker_*.csv.gz (16日: 20260820–20260904), paper_logs/tape/executions_*.csv.gz (同日程), backtest_data/board_round_20260904/board_round_series_5s.csv.gz (ヘッダ確認のみ)。

## 1. Denominator
- ticker/executions とも 16日分が揃っている: 20260820, 20260821, 20260822, 20260823, 20260824, 20260825, 20260826, 20260827, 20260828, 20260829, 20260830, 20260831, 20260901, 20260902, 20260903, 20260904（claim L30 は 7日/n=29,163 と主張）。
- at-best（best bid/ask で約定した print）の母集団: n=306105
- pick-off イベント（size≥表示サイズ OR 直後にレベル消失）: n=247621 （exhausted=129894, disappeared=243833, 両方=126106）
- control（best-touch だが exhaust せず存続）: n=58484
- 再現した n=29,163 との比較: 自前定義では 16日で n=247621 件。claim の 7日/29,163 件を単純比例（÷16*7）すると ≈108334 件で近い桁だが、元の7日ウィンドウがどの範囲かは docs 非開示のため厳密照合は不可。

## 2. Headline number（claim vs 再計算）
| horizon | claimed | 再計算 mean(bps) | day-clustered 95%CI | n_days | t |
|---|---|---|---|---|---|
| 30s | +0.6 | 1.138 | [1.035, 1.240] | 16 | 23.67 |
| 30m | +1.8 | 1.099 | [0.734, 1.464] | 16 | 6.42 |

全ホライズン（pick-off group, day-clustered）:
| horizon | mean(bps) | 95%CI | n_days | n_events |
|---|---|---|---|---|
| 5s | 1.073 | [0.980, 1.166] | 16 | 247621 |
| 30s | 1.138 | [1.035, 1.240] | 16 | 247621 |
| 1m | 1.134 | [1.026, 1.243] | 16 | 247621 |
| 5m | 1.164 | [0.957, 1.371] | 16 | 247621 |
| 30m | 1.099 | [0.734, 1.464] | 16 | 247621 |

## 3. Controls
Control (非exhaust best-touch print), day-clustered:
| horizon | mean(bps) | 95%CI | n_days |
|---|---|---|---|
| 5s | 0.416 | [0.361, 0.471] | 16 |
| 30s | 0.482 | [0.349, 0.615] | 16 |
| 1m | 0.503 | [0.342, 0.665] | 16 |
| 5m | 0.537 | [0.197, 0.877] | 16 |
| 30m | 0.629 | [-0.360, 1.618] | 16 |

Random-time control（直前約定の方向をtaker方向とみなす）, day-clustered:
| horizon | mean(bps) | 95%CI | n_days |
|---|---|---|---|
| 5s | 0.137 | [0.108, 0.166] | 16 |
| 30s | 0.182 | [0.139, 0.226] | 16 |
| 1m | 0.212 | [0.157, 0.267] | 16 |
| 5m | 0.224 | [0.106, 0.341] | 16 |
| 30m | 0.312 | [-0.002, 0.627] | 16 |

Sign-reversed（pick-off イベントを反対方向で測定）: 30s mean = -1.138bps （定義上、符号反転は正負が入れ替わるだけで追加情報はないが、方向規約の検算として実施）。

判定: pick-off group は 30s/30m とも control・random より系統的に大きい正の値。claim の「pick-offは逆選択」という定性的方向は controls と整合。

## 4. Regime: hour別・サイズtercile別（30s move, bps, day-clustered簡易=単純平均）
| hour(UTC) | pickoff n | mean 30s |
|---|---|---|
| 0 | 9245 | 1.135 |
| 1 | 10173 | 1.149 |
| 2 | 9213 | 1.257 |
| 3 | 8141 | 0.965 |
| 4 | 7983 | 0.970 |
| 5 | 10828 | 1.673 |
| 6 | 10051 | 1.032 |
| 7 | 10295 | 1.089 |
| 8 | 14009 | 1.141 |
| 9 | 14034 | 1.379 |
| 10 | 11458 | 1.123 |
| 11 | 11529 | 1.167 |
| 12 | 13253 | 1.177 |
| 13 | 17152 | 1.302 |
| 14 | 18414 | 1.272 |
| 15 | 14644 | 1.181 |
| 16 | 11571 | 1.200 |
| 17 | 8840 | 0.940 |
| 18 | 6330 | 1.170 |
| 19 | 4233 | 1.085 |
| 20 | 4926 | 1.132 |
| 21 | 7373 | 0.930 |
| 22 | 6810 | 1.170 |
| 23 | 7116 | 1.133 |

| size tercile (表示サイズ基準) | n | mean 30s | mean 30m |
|---|---|---|---|
| T1(small) | 99190 | 1.184 | 1.164 |
| T2(mid) | 65891 | 1.058 | 0.871 |
| T3(large) | 82540 | 1.271 | 1.307 |

## 5. Definition side-effects
- at-best 判定は price==best（±0.5JPY）の print のみ採用。複数レベルを掃くsweep注文は「exhausted」側に混入しうる（sizeが表示サイズ以上なら自動的にpickoffへ分類されるため、厚い板を素早く複数回叩く連続printは過大にpickoff側に寄る可能性）。
- disappeared 判定は「直後の次のtickerスナップショットでそのサイドの価格が変わったか」。板更新の間引き（ticker はレベル変化時のみ配信）により、無関係な反対サイドの動きでは影響しない設計。
- exhausted の閾値 0.999×表示サイズ は緩め。厳密 size>=disp_size に変えても定性的結論は不変（exhausted件数の変化: 129661 vs 129894）。
- **重要**: disappeared 単独が 117727件（pickoff全体の48%）と支配的。板が薄い（表示サイズ中央値が0.01〜0.02BTC程度）ため、ごく小さいprintでもレベル価格が動きやすく、『disappeared』基準は size≥表示サイズ という厳密な刈り取りに比べて緩い。exhausted/disappeared を分解:
  - exhausted のみ(厳密pick-off): n=3788, 30s=0.532bps[0.319,0.746], 30m=0.336bps[-1.289,1.960]
  - disappeared のみ(緩い基準): n=117727, 30s=1.089bps[0.996,1.181], 30m=1.065bps[0.460,1.670]
  - 両方満たす: n=126106, 30s=1.204bps[1.086,1.323], 30m=1.132bps[0.904,1.361]

## 6. Data validity
- bitFlyer メンテナンス窓(19:00-19:10 UTC)に該当する at-best print: 0件 / 306105
- メンテ窓除外の有無で 30s mean: 1.138 → 1.138bps（除外後）。
- executions 完全重複行: 4704件。

## 7. Selection contamination（permutation, n=500, label shuffle pickoff/control on move_30s）
- observed diff (pickoff-control) = 0.669bps; permutation null 95%range [-0.057, 0.058]bps; empirical p = 0.0020

## 8. Simplest alternative explanations
- ボラティリティクラスタリング/momentum: random-time control（直前trade方向を採用）が既に 『直近の方向に続く』一般的モメンタムのベースラインを与える。pickoff group の値が random-time control を有意に上回るかで判定（上記表参照）。
  30s: pickoff=1.138 vs control=0.482 vs random=0.182（bps）。
- bid-askバウンス: mid（(bid+ask)/2）で測定しているためbid-askバウンスそのものは相殺される設計。

## 9. Consistency（別ホライズン間の符号・大きさ）
上記セクション2の全ホライズン表を参照。5s→30mまで単調ではないが正の符号は概ね一貫。

## 10. Falsification + MDE
- falsification: 「pick-off後の30秒/30分でtaker方向へのmid移動が、非exhaustコントロールおよびrandom-timeコントロールと有意差なし、または符号が逆」なら claim は否定される。
- MDE (day-clustered, alpha=0.05, power=0.80, n_days=16) @30s: 0.144bps（観測 mean=1.138bps、SE=0.048）
- MDE @30m: 0.513bps（n_days=16）

## 3'. Translation（コスト）
- 使用コスト定数: taker_fee_pct(FX_BTC_JPY)=0.0%（config/products.yaml）。spread p50=1.835bps（venue_survey FINAL.txt bf_fxbtc, 4h窓）。
- claim が主張する pick-off後継続幅: 30s +0.6bps 〜 30m +1.8bps。再計算値: 30s 1.138bps, 30m 1.099bps。
- taker follower の net（コスト=5.8bps往復）: 30s=-4.662bps, 30m=-4.701bps（いずれも負=コスト割れあり）。
- taker follower の net（コスト=2.6bps往復）: 30s=-1.462bps, 30m=-1.501bps（いずれも負=コスト割れあり）。

## Maker re-quote after pick-off P&L
- half-spread（往路捕捉分, p50/2）= 0.917bps。pickoff直後にtouchで再クォートし、そのまま継続方向に走られて再度食われるケースを想定。
| re-quote fill 想定horizon | half-spread捕捉 | 平均continuation(向かい風) | net(bps) |
|---|---|---|---|
| 5s | 0.917 | 1.122 | -0.204 |
| 30s | 0.917 | 1.179 | -0.262 |
| 1m | 0.917 | 1.175 | -0.258 |
→ いずれのホライズンでも net が負なら「pick-off直後の即時再クォートは損」、正なら「スプレッド確保がcontinuationを上回り再クォートは損益分岐点近辺」。

## Verdict per claim
- **L30**: 数値差異(結論維持)。方向（pick-off後にtaker方向へ継続）は再現。大きさは claim の 30s+0.6/30m+1.8bps に対し 再計算(緩い定義=union) 30s+1.138/30m+1.099bps。 nは claim 29,163(7日) に対し 再計算 n=247621(16日、定義も筆者独自）。 ただし §5 の分解が示す通り、この大きさは主に緩い『disappeared』基準（薄板ゆえほぼ全printで価格が動く）由来で、厳密な size≥表示サイズ の exhausted-only（真の刈り取り, n=3788）に限ると 30s+0.532bps・30m+0.336bps[-1.289,1.960]（30mはCIが0をまたぎ有意でない）。すなわち『bot-huntingの継続幅』という定量値は採用する定義次第で claim 相当（緩い定義）から非有意（厳密定義）まで大きく振れる。 母集団・イベント定義・日数いずれも claim と厳密一致しないため大きさの一致は保証されないが、『方向は正・緩い定義でコスト割れ』という定性結論は維持。厳密定義では『継続幅がコストを上回るか』の主張自体が統計的に支持されない。
- **P3**（約定後5分回転、maker両建てTP2-3bps、新鮮データ再監査 pending）: 再計算不能。5分回転のmaker両建て戦略の損益は板の両側同時ポジションとキャンセル/約定タイミングに依存し、本監査のデータ（ticker top-of-book + executions）だけではmaker両建て両ポジションの往復約定を再構成できない（発注イベント自体が記録されていないため）。上記『maker re-quote after pick-off』は近似的代理指標に留まる。→ 未検証（元々 pending 扱いであり、この監査でも pending のまま）。

## 前提の誤り (assumption findings)
| premise | source in claim | data shows | bias direction | inherits |
|---|---|---|---|---|
| taker cost floor = 5.8bps | packet Qのcontext（judged against a 5.8bps taker floor） | venue_survey COSTFLOOR式は 2×taker_fee(=0) + spread_p50(1.835) + 2×slip(≈2.0) = 5.84bps。taker_fee自体は0（config/products.yaml）で、5.8bpsの大半はspread+slip前提の見積り。 | 5.8bpsをそのまま『taker手数料』として読むと過大に聞こえるが、実態はspread+slippage込みの往復コストであり、記載通りなら翻訳は妥当。誤りというより『taker fee』という呼称が誤解を招く。 | taker follower net を5.8bpsで判定する全claim |
| realized round trip ≈2.0-2.6bps | packet Qのcontext（KNOWN PREMISE ISSUE） | 本監査データからは往復コストを直接再現する取引ログがなく（板のtop-of-bookのみ）、2.0-2.6bpsの妥当性は検証不能。venue_survey cap+adv(5s)列 bf_fxbtc=-0.665bps(片道)は同じ桁感で符号は整合。 | 不明（過小・過大どちらの可能性も残る） | 『realized cost低めなので閾値割れ判定が変わる』とする議論 |
| n=29,163 insertions / 7日 | L30 | 本監査で使えるデータは16日分。7日サブセットの境界は非開示 （docsを開けないため）。16日全体では pick-off n=247621件。 | denominatorが違うため絶対値の一致検証不可（方向のみ検証可） | L30の絶対n・大きさを引用する下流の全claim |
| pick-off event 定義 | L30（未開示、本監査は『size≥表示サイズ OR レベル消失』で独自定義） | 定義次第でn・平均が変わりうる（selection contamination参照、p=0.0020）。 さらに厳密(exhausted-only,n=3788)では30m効果のCIが0をまたぐ。 | 緩い定義（disappeared込み）を使うほど効果が過大に見える方向のバイアス | 『pick-off』を参照する全claim（L30, Qのpending P3含む）|

budget: bash/read tool calls ≈ 12（プロトコル・grep含む）, 追加分析はこのスクリプト内で完結。