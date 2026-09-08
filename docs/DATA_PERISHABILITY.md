# 消えるデータの台帳(期限付き取得の抜け防止)

作成 2026-09-08。**「取り逃すと二度と手に入らない」データを一箇所に集めた表**と、それを自動で守る仕組みの所在。
印: 事実 = 実測、推定 = 推論。判定日を必ず入れる(賞味期限つき)。

## 0. 仕組みは既にある(新設ではなく点検した)

| 部品 | 役割 | 所在 |
|---|---|---|
| **保持期間の定数** | 各ソースの上限を `measured` + `verified_on` つきで一元管理。ここが唯一の真実 | `config/constants.yaml: data_retention.*` |
| **自動スナップショット** | 各ソースを**上限の半分以下の間隔**で `backtest_data/auto_<source>_<YYYYMMDD>/` へコピー。1〜2 回失敗しても余裕が残る設計。定数と間隔の整合を起動時に検証し、緩すぎる設定は**失敗させる** | `scripts/retention_snapshot.py`(宣言的な `SOURCES` 表) |
| **実行** | オーナー PC のタスクスケジューラ → `fetch_all.bat` 36 行目で毎日実行 | `deploy/fetch_all.bat` |
| **共有** | `share_logs.bat` が `backtest_data\auto_*` を commit(I-002 の修正後) | `deploy/share_logs.bat` 74 行目 |
| **点検** | 取込台帳と品質チェック | `docs/DATA_QA_CHECKLIST.md` item 4 / 11、`data/INTAKE_latest.json` |

**結論: 仕組みは動いている。**2026-09-08 時点で届いているスナップショット =
`auto_bitflyer_executions_20260905`、`auto_oi_snapshots_20260905`、`auto_okx_long_short_ratio_20260905`、
`auto_okx_open_interest_1h_20260905`、`auto_okx_open_interest_5m_2026090{5,6,7}`、`auto_venues_20260905`。【事実】
本書の役割は**カバー漏れを見つけること**であり、仕組みの再発明ではない。

## 1. 硬い保持期間(上流が消す)

| ソース | 上限 | 仕組みでの扱い | 状態 |
|---|---|---|---|
| bitFlyer 公開約定 `/v1/getexecutions` | **31 日**(サーバが明示エラー) | `bitflyer_executions` 15 日間隔 | 保護済み。2026-09-08 の到達最古 = 2026-08-08T05:26【事実】 |
| OKX 建玉 1H | 30 日 | `okx_open_interest_1h` 14 日間隔 | 保護済み |
| OKX 建玉 5m | **2〜3 日** | `okx_open_interest_5m` **毎日** | 保護済み |
| OKX 買い持ち比率 | 60〜90 日 | `okx_long_short_ratio` 28 日間隔 | 保護済み |
| **JPX デリバティブ日報の月次索引** | **暦年**(2026-01〜は 200、2025-10 以前は 404) | **2026-09-08 に発見・登録**。`jpx_daily_report_months` を新設し、収集器が生 zip を `data/jpx_daily/raw/` に保存するよう変更 | **新規。次の消失は 2027-01-01** |

### JPX 日報について(新発見の詳細)
`scripts/fetch_jpx_daily.py` は日次の OSE 報告 zip を取得 → **日経の行だけ**を抜いて `nk225_sessions.csv` に追記し、
**zip を捨てていた**。zip には全商品(TOPIX 先物・建玉・出来高を含む)が入っており、索引ごと暦年で消える。
P2-06(NT 倍率)を始める直前にこれを捨てているのは筋が悪い。→ 生 zip を保存するよう変更(追記のみ・失敗しても収集は継続)。
索引 9 か月分(2026-01〜09)は `backtest_data/jpx_daily_report_json_20260908/` に退避済み。【事実】
**残作業(木曜以降)**: 生 zip から全商品を抽出する CSV を作る。zip 自体は 1 年で ~500MB になり git に載せられないため、
抽出した CSV を共有する設計にする。

## 2. 期限は無いが「書き換わる / 消える」もの(保持期間とは別の危険)

| 種類 | 具体例 | 対策 |
|---|---|---|
| **ベンダーが過去を遡及改変** | 株式分割で価格系列が丸ごと書き換わる。**1306 で実際に踏んだ**(Yahoo が 2015-01〜2026-03 を 1/10 に改変)。**次は 1591 が 2027-01-28**、その後 02-01 | 分割前の系列を**分割日より前に**スナップショット。1591 は `jpx_etf_daily_20260905/` に取得済み【事実】。分割後に取り直して両方を残す |
| **単一コピーの危険** | オーナー PC の生 WS 記録 `data/ws/*.jsonl.gz`(約 70MB/日)は共有対象外。抽出後のテープ(`paper_logs/tape/`)だけが git にある | 生 WS は PC 内 1 コピーのみ。**判定に使うのは抽出テープなので許容**するが、PC 故障で生は失われる前提で設計する(記録済みの決定) |
| **自前でしか作れない履歴** | OKX 建玉・Deribit DVOL・スプレッド 5 秒・ベーシス 1 分。**履歴 API が無いので、記録を止めた瞬間からその期間は永久に空白** | `fetch_all.bat` の日次収集 + 保持スナップショット。**PC が止まっている期間は復元不能**という理解を共有する |
| **清算(強制決済)** | 高レバ取引所の強制決済。**Gate.io はローリング約 90 日を 1 件ごとに公開**、OKX は約 24 時間、**Binance はストリームのみで履歴なし**(全経路の実測は `docs/DATA_SOURCES/LIQUIDATION_HISTORY_SURVEY.md`)。窓は動くので、遡れる分は**期限つき** | (1) Gate の 90 日を**取り込む**(未実施)。(2) `scripts/record_liquidations.py` を `start_all.bat` で常駐させ、履歴を持たない取引所を自前で記録(2026-09-08 追加、L-026)。`share_logs.bat` が `data/liquidations` を `git add -f`。到達確認は手順 P8。(3) OKX の 24h は**欠測の修復**に使える |
| **無料枠の変更** | Coin Metrics community、Binance Vision、bitbank は現在無料 | 恒久アーカイブ扱いだが、`NEGATIVE_FACTS` の賞味期限で定期再確認 |

## 3. 期限が無いと確認したもの(急がなくてよい)
Binance Vision(日次・月次アーカイブ、`aggTrades` / `klines` / `metrics` / `bookDepth` / `fundingRate`。**保持期限なし**)、
Coin Metrics community(日次 2015-11〜)、bitbank 約定(日付指定、2017-03〜)、Tardis 無料サンプル(毎月 1 日)、
225Labo(四半期更新。ただし**過去年の分足ファイルが差し替えられる可能性は未確認** → 次回 P3 のときに過去年もまとめて取得する)。【事実 + 推定】

## 4. 無料では取れないと再確認したもの(2026-09-08)
- Binance の**清算**(`liquidationSnapshot`)と `bookTicker`: カタログに接頭辞はあるが BTCUSDT のファイルは **GET でも 404**。
- 東証 REIT 指数の全期間四本値(N-005): stooq は bot 対策の HTML を返し使用不可。
- bitFlyer のお知らせ(SFD 料率の変遷、N-007): `web.archive.org` に続き `archive.ph`(接続リセット)・`timetravel.mementoweb.org`(名前解決不可)も到達不能。
- Glassnode / CryptoQuant / Arkham(取引所アドレスの帰属)、CoinAPI / CryptoTick(N-010)。

## 5. 方法の誤りの記録(**再発防止**)
本日、JPX の月次索引を **HEAD** で調べて「2025 年以前は消えている」と誤判定しかけた。GET で確認し直すと
2026-01〜09 はすべて 200 で、**HEAD だけが 404 を返していた**。到達確認は必ず **GET(必要なら `-r 0-999` の部分取得)**で行う。
`docs/PHASE2_TEMPLATES.md` §7 の調達票と `.claude/skills/delegated-study` §5.5 の「到達確認まで実測する」に、この方法上の注意を紐付ける。
**過去の調達票で HEAD 由来の 404 を根拠にしたものは、再確認の対象**(本日 Binance の bookTicker / liquidationSnapshot は GET で再確認済み = 本当に無い)。

## 6. 追加すべき監視(未実装、木曜以降)
`retention_snapshot.py` は「スナップショットを作る」までを担うが、**作られなかったことに誰も気付かない**。
I-002(共有されていないことに数週間気付かなかった)と同型の穴が残っている。
→ ダッシュボードに「各 `data_retention` ソースの最新スナップショットの経過日数」を出し、
**間隔の 1.5 倍を超えたら Discord に通知**する((削除済み文書) §5 の軽量版と同じ実装で足りる)。
