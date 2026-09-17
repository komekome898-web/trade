# O-3c 必要データ収集の手段と管理の徹底方法

2026-09-17、調査班(`research-squad` モード1・調達調査)による。**戦略・データの当否は判定しない。**
需要はオーナー決定 L-189(2026-09-17)「**3件の質問全てYES。着手してください**」。生ログ:
`docs/DATA/probes/20260917_o3c_collection.log`。前提の一次資料: `docs/PHASE2/O3C/MISSING_2026-09-17.md`
(先に全文を読んだ)。

## 0.1 対応表(着手前の擦り合わせ)

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| O-3c「必要データ収集の手段と管理の徹底方法」を調べる | 「**必要データ収集の手段と管理の徹底方法**」(`docs/PHASE2/O3C/OWNER_INTENT_2026-09-12.md` §1) |
| 「必要データ」を `MISSING_2026-09-17.md` の項目 1・6・7・8・9・13(データ分類)+継続記録の穴に絞る | 「**必要データ**」= `MISSING_2026-09-17.md` で「データ」と分類した項目 1・6・7・8・9・13 と、計算・実行のために継続記録が要るもの(自前 WS 清算記録の破損ファイル 11 個の回収を含む)(L-189、3 件の質問の 1 件目) |
| 「管理の徹底」を `docs/DATA.md` の更新規則+機械的な確認の仕組みの整理と案出しにする | 「**管理の徹底**」= 台帳 `docs/DATA.md` の行の更新規則と、届いたものを機械で確かめる仕組み(既存の `paper_logs/INTAKE.jsonl` / `paper_logs/QUALITY.json` の使い方を含む)(L-189、2 件目) |
| 成果物を文書 1 本にする | 「**成果物は文書 1 本**」(L-189、3 件目) |
| 各項目に (a)〜(e) の形式(何を・粒度・期間/経路5つ/既存の仕組み/無ければ何を書くか/印)を当てる | (該当語なし) — リードの依頼文が指定した出力形式。オーナー原文には形式の指定はない。**リードの判断(2026-09-17)**: 形式は納品の中身ではなく書き方なので、`research-squad` §3 の様式(経路 5 つ・生ログ・台帳の追記案)の延長として当て、聞かなかった |
| 個別項目 1・6・7・8・9・13 とその内容(建玉欠測・bitFlyer価格・bitFlyer清算・欠落3日・レバレッジ分布・他取引所)を挙げる | 「**3件の質問全てYES**」(L-189)。**この番号はリードが 2026-09-17 の返答の対応表に「上の一覧でデータと分類した 1・6・7・8・9・13 と、計算・実行のために継続記録が要るもの(自前 WS の破損 11 個の回収を含む)」と書いて出し、オーナーが YES と答えた行**(調査班の初稿は「該当語なし」と書いていたが、リード検収で L-189 に対応させた) |
| `research-squad` モード1の固定手順(経路3つ以上・生ログ保存・DATA.md 追記案)を適用する | 「**スキルの承認をもって聞かずに当ててよい**」(L-179) |

**右が空の行は 1 行((a)〜(e) の出力形式)。**聞かなかった理由は上の表に書いた(リードの判断)。項目番号の切り方は L-189 で埋まっている。

---

## §A 必要データごとの収集の手段

各項目: (a) 何を・どの粒度・どの期間 (b) 経路5つ (c) 既存の仕組みで既に取れているか(コードを読んで) (d) 無ければ何を書けば取れるか(仕様のみ、実装しない) (e) 印。

### 1. Binance COIN-M 建玉(OI)の欠測 99 日

- **(a)** `sum_open_interest`(Binance COIN-M BTCUSD_PERP)、5 分刻み、窓 2023-06-25〜2024-10-14 のうち欠測 99 日分(単発2日+2024-03-04〜06-08 の連続97日)。
- **(b) 経路5つ**:
  1. **この環境**: `fapi.binance.com/futures/data/openInterestHist` → 本日再実測 **HTTP 451**(地域制限。`docs/DATA/probes/20260917_o3c_collection.log` 5行目、本文冒頭「Service unavailable from a restricted location according to 'b. Eligibility'...」)。
  2. **オーナーPC**: 未確認(地域制限が同じIP帯かは未測定)。
  3. **公開アーカイブ**: `data.binance.vision` の `metrics` は当該99日について404(`docs/OWNER_STATUS.md:44`、2026-09-14実測の転記)。
  4. **第三者**: Coinalyze(`api.coinalyze.net`)HTTP 401(鍵必須)、CoinGlass(`open-api-v4.coinglass.com/api/futures/open-interest/history`)HTTP 200・本文 401(鍵必須)。**どちらも 09-17 午前の実測(`docs/DATA/probes/20260917_o3c_missing.log` 8・9 行目)の転記で、今回は再プローブしていない。**調査班の初稿は生ログ 1・2 行目を「CoinGlass の再実測 = HTTP 400」と書いていたが、**1・2 行目の URL は OKX `rubik/stat/contracts/open-interest-volume`(HTTP 400、`code 50014` = パラメータ不足)であって CoinGlass ではない**(リード検収で直した。OKX のこのプローブは項目 1 の経路には入らない)。
  5. **有料**: 上記4系はいずれも鍵が要る(価格・プランは未確認)。
- **(c) 既存の仕組みで取れているか(コード読み)**: `scripts/retention_snapshot.py:139-165` の `SOURCES` リストは `bitflyer_executions` / `okx_open_interest_1h` / `okx_open_interest_5m` / `okx_long_short_ratio` / `oi_snapshots` / `venues` の6件のみで、**Binance COIN-M建玉の自動スナップショットは無い**(実測、リスト全項目を確認)。`backtest_data/binance_cm_o3c_20260913/` は日付固定の一括取得ディレクトリで、継続記録の仕組みではない。**欠測99日は過去のデータなので、リアルタイム記録では原理的に埋まらない**(継続記録の対象外)。
- **(d) 無ければ何を書けば取れるか(仕様のみ)**: 過去分は経路4(有料鍵)を取得しない限り埋まらない。今後の分は、`scripts/retention_snapshot.py` の `SOURCES` に Binance COIN-M建玉の項目を追加する仕様が要る: スクリプト名(案)`scripts/fetch_binance_cm_oi.py`、実行場所オーナーPC(`deploy/fetch_all.bat` 経由)、頻度は `openInterestHist` の遡り制約が未確認のため頻度未定(まず一次資料のURLを確認してから決める。§0.2 O-6「出所の分からない数字を出さない」に該当するため、遡り日数を仮定しない)。
- **(e) 印**: 事実(451 = 今回の生ログ 5 行目 / SOURCES リストの内容 = コード読み / 第三者 2 社の鍵必須 = `docs/DATA/probes/20260917_o3c_missing.log` 8・9 行目、09-17 午前)。

### 6. bitFlyer 側の価格(約定単位、tick)

- **(a)** bitFlyer FX_BTC_JPY の約定単位(tick)価格。窓 2023-06-25〜2024-10-14(478日)のうち、tardis標本日17日(3.6%)以外は無い。
- **(b) 経路5つ**:
  1. **この環境**: bitFlyer `getexecutions` は31日ロールオフ(`config/constants.yaml:457-469` `data_retention.bitflyer_executions_days: value: 31`、`source_type: measured`、`verified_on: "2026-09-04"`)。過去(2023-06〜2024-10)のtickは公開APIから取得不可。
  2. **オーナーPC**: bitFlyerの長期テープ保管の有無は未確認。
  3. **公開アーカイブ・API**: bitFlyer公式の長期tickアーカイブは未確認(`docs/DATA.md`に記載が無く、公式ドキュメントに言及が見当たらない、という2点だけ。「無い」とは書かない)。
  4. **第三者**: tardis(`data/tardis/`の出所、標本日以外も取れる可能性)。**有料なので提案しない**(`CLAUDE.md` §0.2 A-3)。
  5. **有料**: 未確認。
- **(c) 既存の仕組みで取れているか(コード読み)**: `scripts/retention_snapshot.py` の `SourceSpec("bitflyer_executions", 15, ...)`(139-143行目)が、31日retentionの半分以下(15日間隔)で `backtest_data/auto_bitflyer_executions_<date>/` へ自動スナップショットしている(実測、`backtest_data/auto_bitflyer_executions_20260905/` 実在)。**これは「今後」のtickを継続的に取り続ける仕組みであり、過去(2023-06〜2024-10)の欠落を埋める仕組みではない。**
- **(d) 無ければ何を書けば取れるか**: 過去分は経路4(tardis、有料)以外に埋める手段が見つかっていない。今後分は既存の自動スナップショットで継続的に埋まる(何もしなくてよい)。
- **(e) 印**: 事実(retention定数・自動スナップショットの実在)/ 未確認(公式長期tickアーカイブの有無)。

### 7. bitFlyer の清算データ【閉じた: 集めない(L-190)】

**オーナー決定 L-190(2026-09-17)**: 「**3は不要(bitFlyerCFDのレバレッジは2倍、清算などほとんど起きない)**」。FAQ の取得(下の (d))は行わない。下の記述は閉じる前の調査の記録。

- **(a)** bitFlyer自身が発する強制ロスカットイベント。粒度・期間ともに現状ゼロ(専用エンドポイントが見つかっていない)。
- **(b) 経路5つ**:
  1. **この環境**: 本日 `lightning.bitflyer.com/docs` へのHEAD再実測は今回未実施(§7の09-17午前の実測=HTTP200を転記。専用の清算エンドポイントは見当たらない)。**今回の生ログ 4 行目**(`api.bitflyer.com/v1/getboardstate` へ HEAD → HTTP 405)は、bitFlyer 公開 API 自体にこの環境から到達できることの確認(405 = HEAD を受け付けないだけで、到達はしている)。清算の項目の有無はこのプローブでは分からない。
  2. **オーナーPC**: 未確認。
  3. **公開アーカイブ・API**: 同上、専用エンドポイント無し(`docs/DATA.md:72`実測、2026-09-12)。
  4. **第三者**: bitFlyerの清算履歴を提供する第三者は見つかっていない(WebSearch、09-17実測)。
  5. **有料**: 未確認。
- **(c) 既存の仕組みで取れているか**: 無し。継続記録の仕組みも存在しない(データ自体が無いので記録対象がない)。
- **(d) 無ければ何を書けば取れるか**: 直接収集する手段は、**この環境・公開 API・第三者(検索)では見つかっていない**(方法: 公式 API リファレンスと実測スキーマの照合 09-12、WebSearch 09-17。**オーナー PC と有料は未確認**なので「全経路で無い」とは書かない。監査役の指摘 2 を受けて範囲を付けた)。代替として、bitFlyerの証拠金維持率・ロスカット閾値の一次資料(SFD FAQ等)から理論式を作る案があるが、当該FAQページ自体がこの環境からHTTP403(WAF、`docs/DATA.md:74`)で読めていない。**この項目の仕様は「一次資料の取得」までである**: FAQ 7-23 / 7-11 / 7-33 はこの環境では 403 なので、**取得経路はオーナー PC**(ブラウザで保存して共有経路に置く。手順化はオーナーの決定後、`docs/OWNER_PROCEDURES.md` に番号を付けて出す)。理論式の仕様はその後。
- **(e) 印**: 事実(専用エンドポイント無しの実測、範囲はこの環境・公開 API・第三者)/ 仮定(代替案が機能する保証は無い)/ 未確認(オーナー PC・有料の経路)。

### 8. Binance清算の欠落3日(2023-09-09 / 2023-09-23 / 2024-06-01)

- **(a)** Binance COIN-M `liquidationSnapshot` の当該3日分。
- **(b) 経路5つ**:
  1. **この環境**: `data.binance.vision` の CM(BTCUSD_PERP)は **3 日とも HTTP 404**(2026-09-14 の実測、`docs/OWNER_STATUS.md:37-44` の表「2023-09-09 / 2023-09-23 / 2024-06-01 | 清算 | 404」)。2023-09-09 だけは 09-17 午前に UM(BTCUSDT)・CM の両方を再実測して 404(`docs/DATA/probes/20260917_o3c_missing.log` 6・7 行目)。**今回(本文書)は再プローブしていない。**UM 側の 09-23・06-01 は未プローブ。CM側aggTradesは3日とも実在=「0件」か「未配信」かの区別材料が無い(監査役の指摘 3 を受けて、3 日それぞれの根拠を分けて書いた)。
  2. **オーナーPC**: 未確認。
  3. **公開アーカイブ**: 同上404。
  4. **第三者**: Coinalyze・CoinGlass(いずれも鍵必須)。鍵を取れば当日の集計値は出るが、Binance発の生イベントそのものではない。
  5. **有料**: 同上(鍵の価格・範囲未確認)。
- **(c) 既存の仕組みで取れているか**: `paper_logs/liquidations/`の自前WS記録は2026-09-08以降のみで、2023-09/2024-06には遡れない(記録開始日が窓の外)。
- **(d) 無ければ何を書けば取れるか**: 過去分は経路4(有料鍵)以外に埋める手段が無い。実務上の代替は、3日を「欠測」として除外し、日次頻度の分母から外す仕様(集計スクリプト側で該当3日をスキップするフラグを持たせる。実装しない)。
- **(e) 印**: 事実(404の実測)/ 推定(「0件」か「未配信」かの判定は未確認)/ 未確認(オーナーPC・有料)。

### 9. レバレッジ分布・ロング/ショート比

- **(a)** Binance COIN-M `metrics` の `count_toptrader_long_short_ratio` 系3列。全期間(478日)を対象にしたいが、サンプル7日・2,016行で3列とも全て空欄(実測、`MISSING_2026-09-17.md` §9)。
- **(b) 経路5つ**:
  1. **この環境**: 上記APIで空である理由(対象外か収集側の欠測か)は未確認。
  2. **オーナーPC**: 未確認。
  3. **公開アーカイブ**: 同じ空欄が全期間で続くかは、サンプル以外未確認。
  4. **第三者**: CoinGlass等はロング/ショート比の製品ページがあるが鍵必須(未確認、価格未取得)。
  5. **有料**: 未確認(鍵の価格・範囲とも)。
- **(c) 既存の仕組みで取れているか**: `backtest_data/binance_cm_o3c_20260913/metrics/` は一括取得済みの静的スナップショットで、3列が空欄なのはこのデータ自体の性質(取得の仕組みの問題ではない)。自動継続記録の対象にもなっていない(SOURCESリストに無い、§1と同じ確認)。
- **(d) 無ければ何を書けば取れるか**: 全期間478日で本当に空欄が続くかを確認する集計スクリプトが要る(仕様: `metrics`の全zipを展開して3列の非空率を数える。実装しない、下位モデルに委任できる)。空欄が続けば、この項目に「収集の手段」は無い(このAPIにレバレッジ分布が無い)という結論になる可能性がある(未確認)。
- **(e) 印**: 事実(サンプル空欄率実測)/ 推定(全期間・原因未確認)。

### 13. 他の取引所の清算データと、その取引所の約定単位の価格

- **(a)** 自前WS記録(binance_cm/bitmex/bybit/okx、2026-09-08〜09-16)に対応する、同一取引所・同一期間の約定単位価格系列。粒度は取引所ごとに異なる(下記)。
- **(b) 経路5つ**:
  1. **この環境**: Bybit・OKXの1分足は公開APIから取得可(`docs/PHASE2/O3C/DATA_AVAILABILITY.md:32・37`)。
  2. **オーナーPC**: 未確認。
  3. **公開アーカイブ・API**: Bybit約定アーカイブ(`:31`)、両取引所の1分足。
  4. **第三者**: 未確認。
  5. **有料**: 未確認。
- **(c) 既存の仕組みで取れているか(コード読み)**: `scripts/record_liquidations.py:95-122` の `VENUES` 辞書は binance_um / binance_cm / bybit / okx / bitmex の5系統をWSで継続記録している(実測、コード読み)。**ただし価格系列(約定単位)は同スクリプトの対象外**(清算イベントのみを記録し、価格は別途 `retention_snapshot.py` のOKX建玉・bitFlyer執行のみで、Bybit/OKXの価格自体の自動記録は無い)。BitMEXについては本日 `https://www.bitmex.com/api/v1/instrument?symbol=XBTUSD` を実測 → **`"state":"Settled"`、`"expiry":"2026-09-16T12:00:00.000Z"`**(`docs/DATA/probes/20260917_o3c_collection.log` 3行目)。`record_liquidations.py:118-122` のBitMEX設定は `wss://ws.bitmex.com/realtime?subscribe=liquidation:XBTUSD` に固定されており、**XBTUSDが決済済み(Settled)になった以上、この購読は今後新規の清算イベントを受け取れない**(推定。WS接続自体が拒否されるか、単に無配信が続くかは未測定)。
- **(d) 無ければ何を書けば取れるか**: Bybit・OKXの約定単位価格を継続記録するなら、仕様(案): `scripts/record_liquidations.py` と同様のWS常駐スクリプトを別途書く(価格ティック用)、実行場所オーナーPC(`deploy/start_all.bat`常駐)、保持は`paper_logs/`で継続(retentionの制約なし=WSは公開履歴に依存しないため)。BitMEXについては、XBTUSD以外の後継シンボル(あれば)への切替が必要かどうかを先に一次資料(BitMEXの上場一覧)で確認する(未確認、仕様を書く前提が欠けている)。
- **(e) 印**: 事実(WS設定コード・BitMEX instrument APIの実測)/ 推定(Settled後の購読の挙動)/ 未確認(BitMEX後継シンボルの有無)。

### 継続記録が要るもの: 自前WS清算記録の破損ファイル11個の回収

- **(a)** `paper_logs/liquidations/*.trunc1.jsonl.gz` 11個(binance_cm 09-11・09-12、bitmex/bybit/okx 各 09-09・09-11・09-12)。
- **(b) 経路5つ**: 1. **この環境**: 11 個とも `paper_logs/liquidations/` に実在(共有経路経由)/ 2. **オーナー PC**: 原本 `data/liquidations/` にある(P14 の設計。PC で数えてはいない = 未確認)/ 3. **公開アーカイブ**: 該当しない(自前の WS 記録なので外部には無い)/ 4. **第三者**・5. **有料**: 同じく該当しない。経路の問題ではなく「処理の実行」の問題(監査役の指摘 5 を受けて 5 経路の形に揃えた)。
- **(c) 既存の仕組みで取れているか(実測・実行して確認)**: `scripts/repair_liquidation_gz.py`(読み取り専用、原本を書き換えない)を11ファイル全部に対し `--dry-run` で実行した:

  ```
  binance_cm_20260911.trunc1.jsonl.gz: members=2 complete=0 recovered=9685 discarded=1 original_readable_as_is=yes
  binance_cm_20260912.trunc1.jsonl.gz: members=1 complete=0 recovered=235 discarded=0 original_readable_as_is=NO
  bitmex_20260909.trunc1.jsonl.gz: members=1 complete=1 recovered=3480 discarded=0 original_readable_as_is=yes
  bitmex_20260911.trunc1.jsonl.gz: members=1 complete=1 recovered=2548 discarded=0 original_readable_as_is=yes
  bitmex_20260912.trunc1.jsonl.gz: members=1 complete=0 recovered=50 discarded=0 original_readable_as_is=NO
  bybit_20260909.trunc1.jsonl.gz: members=1 complete=1 recovered=4952 discarded=0 original_readable_as_is=yes
  bybit_20260911.trunc1.jsonl.gz: members=1 complete=1 recovered=3957 discarded=0 original_readable_as_is=yes
  bybit_20260912.trunc1.jsonl.gz: members=1 complete=0 recovered=62 discarded=0 original_readable_as_is=NO
  okx_20260909.trunc1.jsonl.gz: members=1 complete=1 recovered=20599 discarded=0 original_readable_as_is=yes
  okx_20260911.trunc1.jsonl.gz: members=1 complete=1 recovered=14289 discarded=0 original_readable_as_is=yes
  okx_20260912.trunc1.jsonl.gz: members=1 complete=0 recovered=87 discarded=0 original_readable_as_is=NO
  11 ファイル、計 59944 行回収、1 行捨てた。dry-run(書き出しなし)
  ```

  **この環境で11個とも回収可能であることを実測した**(`docs/OWNER_PROCEDURES.md` P14「実物の10ファイルはこの環境に届いていない」は2026-09-12時点の記述で、**現在は届いている**=状況が変わっている。詳細は§Bに書く)。調査班は dry-run で止め、「A-14 には当たらない」と書いていた。**A-14 に当たるかの判断はリードがやり直した(監査役の指摘 9)**: 回収は原本を書き換えず新しいディレクトリに書くだけで、実弾・口座・資本・新市場・リスク上限のどれにも触れない → A-14 ではない。かつ「破損 11 個の回収」は L-189 でオーナーが YES と答えた行に含まれている → **リードが本実行した(下)**。
- **(d) 本実行(リード、2026-09-17)**: `python3 scripts/repair_liquidation_gz.py --out-dir backtest_data/liquidations_repaired_20260917 paper_logs/liquidations/*.trunc1.jsonl.gz` → **11 ファイル、計 59,944 行回収、1 行捨てた**(dry-run と同じ数)。出力先 `backtest_data/liquidations_repaired_20260917/paper_logs/liquidations/*.trunc1.jsonl.gz`(11 個、1.3 MB)。展開して数えた行数: binance_cm 09-11 9,685 / 09-12 235、bitmex 09-09 3,480 / 09-11 2,548 / 09-12 50、bybit 09-09 4,952 / 09-11 3,957 / 09-12 62、okx 09-09 20,599 / 09-11 14,289 / 09-12 87 = 合計 59,944。`MD5SUMS`(11 行、`./` 無しのパス)を置いた。コマンドと出力は `docs/AUDITOR/ACTION_LOG.md` 050。
- **(e) 印**: 事実(dry-run と本実行の出力、展開後の行数)。

---

## §B 継続記録の現状と穴

- **`paper_logs/liquidations/` の破損11個**: `docs/OWNER_PROCEDURES.md:403-441`(P14)によれば、修正済みの記録器(少量ずつ完結した塊で書く/起動時に壊れたファイルを`.trunc1.jsonl.gz`へ退避)は「次の`restart_all.bat`でPCに入る」設計で、回収スクリプト`scripts/repair_liquidation_gz.py`は「リードが共有された複製に対してこの環境で実行する」と書かれている。P14執筆時点(2026-09-12)は「実物の10ファイルはこの環境に届いていない(share_logsの途絶、L-128)」だったが、**本日(2026-09-17)実測した時点では11ファイルとも既にこの環境の`paper_logs/liquidations/`に実在する**(§Aのdry-run実測)。**share_logsの途絶は解消済みと見られる(推定。P14の「翌朝の共有コミットの有無で分かる」という確認自体は今回していない)。**残っている作業は、dry-runで確認した回収を本実行し、`backtest_data/`へMD5付きで退避することだけ(未実行)。
- **`paper_logs/WS_GZ_LISTING.json`(32,827バイト、2026-09-16 11:32更新)・`paper_logs/SNAPSHOT_VERIFY.json`(540,376バイト、同時刻更新)は実在する**。内容の全件精査は今回時間の都合で行っていない(未完了、§Eに明記)。
- **【リード検収で追加(2026-09-17)】`paper_logs/SNAPSHOT_VERIFY.json`(オーナー PC で 2026-09-15 08:51 UTC に生成)の要約(実物を開いた)**: `ok: false`。単位 77 のうち verified 44・verified_line_ending_only 21・**mismatch 11**、total_missing 3,645・total_extra_untracked 3,351、ledger_mismatches 0。**mismatch 11 単位に O-3c のデータそのもの `binance_cm_o3c_20260913` が入っている**: checked 2,691・matched **0**・missing 2,691・extra 1,741。**原因は 2 つあり、両立する**(監査役の指摘 4 を受けて分けて書く): **(i) パス表記の不一致(事実)**: その単位の `MD5SUMS` は各行のパスが `./README.md` のように **`./` 付き**で、検証器はそれを「listed but missing」と数え、PC に実在する同じファイルは「extra」と数えている。だから matched が 0 で、missing = 台帳の全行 2,691、extra = PC に実在する全ファイル数。**つまり検証器は O-3c の 2,691 ファイルを 1 つも照合できていない**(`head -2 backtest_data/binance_cm_o3c_20260913/MD5SUMS` で `./` を確認、`wc -l` = 2,691。この環境の実ファイル数は `MD5SUMS` 自身を除いて 2,691。**初稿の「2,692」は `MD5SUMS` を数えに入れた誤りで、リードが直した**)。**(ii) PC 側のファイル数の不足(事実 + 推定)**: extra が 1,741 なので **PC 側にこの単位のファイルは 1,741 個**(事実、検証器の数え上げ)。この環境は 2,691 なので差 950 = aggTrades の zip 475 + `.CHECKSUM` 475(**推定**。`.gitignore:53` が `binance_cm_o3c_20260913/aggTrades/**/*.zip` を除外しているので zip は git 経由で PC に渡らない。`.CHECKSUM` は未確認)。(i) が無ければ (ii) は「missing 950・matched 1,741」として正しく見えたはずで、**(i) が (ii) を隠している**。**【L-190 で直した(2026-09-17)】**`verify_snapshots.py: _parse_md5sums` が先頭の `./`(`.\` も)を剥がすようにし、この環境で再実行 → `[ok] binance_cm_o3c_20260913: 2691/2691 matched`(missing 0・extra 0)。PC 側の (ii) はこの環境では確かめられないので、次に PC で `fetch_all.bat` が走って `SNAPSHOT_VERIFY.json` が届いたときに、この単位の extra と missing を見る。
- **BitMEXについて**: `docs/PHASE2/O3C/DATA_AVAILABILITY.md:127-128`「BitMEX取引所全体閉鎖 2026-09-23」「BitMEX XBTUSD等 上場廃止・清算 2026-09-16 12:00 UTC」。本日の実測(`https://www.bitmex.com/api/v1/instrument?symbol=XBTUSD` → `"state":"Settled"`、`"expiry":"2026-09-16T12:00:00.000Z"`)で上場廃止が確定していることを確認した。`scripts/record_liquidations.py:118-122`のBitMEX設定は`liquidation:XBTUSD`の固定購読であり、**このままではBitMEXの記録器は09-16以降、新規清算イベントを受け取れない可能性が高い(推定、WS接続自体の挙動は未測定)**。09-23の取引所閉鎖後はAPI自体が落ちるため、記録器はいずれ接続エラーになる(未確認、その時の挙動=自動リトライでバックオフし続けるだけか、エラーとして目立つ通知が出るかはコード上未確認)。

---

## §C 管理の徹底

### (1) いまの機械(コードで確認した内容)

| 部品 | 何をするか(コード読み) | 出力 |
|---|---|---|
| `scripts/intake_ledger.py` | `data/INTAKE.jsonl`(append-only履歴)・`data/INTAKE_latest.json`(パス別最新インデックス)を管理する意図で書かれている(`intake_ledger.py:11-18・64・582-583`実測)。`SELF_FILES`に自分自身の出力パスを含めて自己参照ループを避ける | `data/INTAKE.jsonl`, `data/INTAKE_latest.json`(コード上の既定パス) |
| `scripts/data_quality.py` | 取り込み時の自動チェック(重複・欠測・交差板等)を実行し結果を書く(`data_quality.py:81`のコメント「run checks, write QUALITY.json」、出力パス`data_quality.py:746` `root / "data" / "QUALITY.json"`実測) | `data/QUALITY.json`(コード上の既定パス) |
| `scripts/verify_snapshots.py` | `backtest_data/`のMD5完全一致検証。改行コード差だけの不一致は`line_ending_only`として分離(`verify_snapshots.py:15-16・37`実測) | `data/SNAPSHOT_VERIFY.json`(コード上の既定パス、`:37`のdocstring) |
| `deploy/share_logs.bat` | オーナーPCの`logs\`・`data\`配下のファイルを`paper_logs\`へコピーしてcommit(`share_logs.bat:20-30`実測。コミット→sync の順)。**これが`data/*.json`と`paper_logs/*.json`が両方存在する理由**(オーナーPC側で`data/`に生成→`paper_logs/`へコピー→この環境が見るのは`paper_logs/`のコピーだけで、この環境自身の`data/`は09-08時点で止まったまま) | `paper_logs/INTAKE.jsonl`等(コピー先) |
| `docs/DATA.md` §0 の表 | 上記5部品の役割一覧(人間向けドキュメント。コードではない) | — |

**実測した食い違い**: コード上の既定出力パスは`data/*.json`だが、この環境で実際に新しい(2026-09-16更新)のは`paper_logs/*.json`側で、`data/INTAKE.jsonl`(20,283行、2026-09-08最終更新)は`paper_logs/INTAKE.jsonl`(21,975行、2026-09-16最終更新)より1,692行古い。**これは設計どおりの可能性がある**(`src/bot/monitoring/gates.py`の`shared_or_local`が「ローカルが新しい場合のみローカルを使う」ため、この環境では`paper_logs/`側=オーナーPCで生成→共有された方が新しいので優先される、と読める。**gates.pyの実装自体は今回読んでいない=未確認**)。ただし`docs/DATA.md:20`(受領台帳の行)は所在を`data/INTAKE.jsonl`とだけ書いており、**運用上「今どちらを見るべきか」が台帳の記述からは分からない**。

### (2) `docs/DATA.md` の行と実物の食い違いの実例

| 行 | 台帳の記載 | 実物 | 食い違い |
|---|---|---|---|
| `docs/DATA.md:96`(清算WSストリーム) | 「11ファイルは破損・回収待ち」「09-11時点の記載は10」 | `ls paper_logs/liquidations/*.trunc1.jsonl.gz \| wc -l` = 11(実測、本報告§A) | **無し**(2026-09-17に`MISSING_2026-09-17.md`の検収で既に10→11へ訂正済み。本報告作成時点で最新) |
| `docs/DATA.md:92`(OKX建玉OI・L/S比スナップショット) | 最終確認日「2026-09-11」 | `backtest_data/auto_okx_open_interest_5m_*`は09-05〜09-12に加え**09-15**まで実在(`ls`実測、mtimeも2026-09-16 11:32)。記録は09-11以降も継続している | **最終確認日が古い**(継続記録の性質上、日付を更新し続けるか「継続中」と書くかの運用が決まっていない) |
| `backtest_data/auto_okx_open_interest_5m_*`のディレクトリ間隔 | `docs/DATA.md`には記載なし(§0の表は仕組みの説明のみ) | 09-12の次が09-15で、**09-13・09-14の2日分のディレクトリが無い**(`ls`実測)。`scripts/retention_snapshot.py:151-154`は`okx_open_interest_5m`の`interval_days=1`を宣言し、`_validate_cadence`(`:178-197`)がこの間隔をretention(2-3日)の半分以下であることを起動時に検証する設計 | **運用上の欠落**: 2日連続で`fetch_all.bat`(または`retention_snapshot.py`)が実行されなかった形跡。OKX 5分値のretentionは2-3日(`config/constants.yaml:484-494`)なので、**3日空くとretention窓を超え、その間のデータが永久に失われている可能性がある**(未確認。09-13・09-14分がOKX側で既に消えているかは未検証) |

### (3) 更新規則の案(仕様のみ、実装しない。2〜3案。選択はリード・オーナー)

**案A: 最終確認日のN日ルール** — `docs/DATA.md`の各行の「最終確認日」が今日からN日(例: 継続記録行は7日、一括取得行は無期限)より古い行を列挙するチェックスクリプトを書く。機械で確かめられる形: `python3 scripts/check_data_md_freshness.py --max-age-days 7`のような出力で「古い行のリスト(行番号・資産名・最終確認日)」を返す。**継続記録行(状態=取得済・継続)とスナップショット行(状態=取得済・確定)を区別する列が今の表に無いので、まず列を増やす必要がある**(未実装)。

**案B: 所在パスの実在チェック** — `docs/DATA.md`の「所在」列に書かれたパス(ファイル・ディレクトリ・URL)が実在するかを機械的に確認するスクリプト。ファイルパスは`os.path.exists`、URLはHEAD/GET(小さいプローブ)。実在しない行を列挙する。**URLは外部プローブになるため実行頻度を絞る必要がある(週次程度)。**

**案C: INTAKE.jsonlとの相互参照** — `paper_logs/INTAKE.jsonl`(または`data/INTAKE.jsonl`、(1)の食い違いをどちらか決めてから)に記録されていない`backtest_data/`配下のファイルを列挙する(取り込み台帳に無い=`intake_ledger.py`を経由せず置かれたファイルの検出)。逆に`docs/DATA.md`に行が無いのに`INTAKE.jsonl`にあるパスも列挙する(台帳への追記漏れの検出)。

**共通の弱点(3案とも)**: どの案も「誰が・いつ実行するか」を決めていない。オーナーPC側で`fetch_all.bat`実行後に自動で走らせる(案として`deploy/fetch_all.bat`の末尾に追加)か、この環境でリードが週次に手動実行するかは、**リード・オーナーが選ぶ判断**として残す。

---

## §D `docs/DATA.md` への追記案(未マージ)

| 資産 | 所在 | 範囲 | 状態 | 最終確認日 | プローブのログ | 使った単位 |
|---|---|---|---|---|---|---|
| 自前WS清算記録の破損11個の回収 | `backtest_data/liquidations_repaired_20260917/paper_logs/liquidations/*.trunc1.jsonl.gz`(原本 `paper_logs/liquidations/*.trunc1.jsonl.gz` は非破壊) | 11ファイル、計59,944行(1行破棄)。MD5SUMS 11 行 | **取得済(回収済み、リード本実行 2026-09-17)** | 2026-09-17 | `docs/AUDITOR/ACTION_LOG.md` 050(コマンドと出力) | O-3c(未使用) |
| BitMEX XBTUSD 上場状態 | `https://www.bitmex.com/api/v1/instrument?symbol=XBTUSD` | — | 取得済(`"state":"Settled"`、`"expiry":"2026-09-16T12:00:00.000Z"`実測) | 2026-09-17 | `docs/DATA/probes/20260917_o3c_collection.log` | O-3c(未使用) |
| OKX建玉5分値の自動スナップショット欠落2日(09-13・09-14) | `backtest_data/auto_okx_open_interest_5m_*` | 09-12→09-15の間、2日分ディレクトリ無し | **試行して不可の可能性(未確認)**: retention2-3日を超える欠落の疑い | 2026-09-17 | 本報告(`ls`実測、専用ログ未保存) | O-3c(未使用) |
| Binance COIN-M建玉・metrics系列の自動継続記録 | `scripts/retention_snapshot.py: SOURCES`(139-165行目) | 該当なし(仕組み自体が無い) | 未試行(自動化の仕組みが存在しないことを確認) | 2026-09-17 | 本報告(コード読み) | O-3c(未使用) |

---

## §E 予算・完了状況

実時間 約24分。生ログ `docs/DATA/probes/20260917_o3c_collection.log` 5行(HTTPコード: 400/400/200/405/451。1・2 行目 = OKX rubik(§A-1 の経路には使わない)、3 行目 = BitMEX instrument(§A-13・§B)、4 行目 = bitFlyer 公開 API の到達確認(§A-7 経路 1)、5 行目 = Binance `openInterestHist`(§A-1 経路 1))。

**未完了**:
- `paper_logs/WS_GZ_LISTING.json`・`paper_logs/SNAPSHOT_VERIFY.json`の**内容の全件精査**は行っていない(実在確認のみ)。
- §Cの更新規則案は仕様の骨子のみで、`docs/DATA.md`の列追加や具体的なチェックスクリプトの疑似コードまでは書いていない。
- `src/bot/monitoring/gates.py: shared_or_local`の実装は今回読んでいない(§C(1)の「設計どおりの可能性」は未確認のまま)。
- BitMEX上場廃止後の記録器(`record_liquidations.py`)の実際の挙動(WS接続がどうなるか)はコード上未検証(未測定)。
- 項目7(bitFlyer清算)は一次資料(SFD FAQ)が読めないため、(d)の仕様を書ける段階に到達していない。

超えていないため途中で報告する必要はないが、上記5点は範囲外として明記する。

## リードの検収(2026-09-17、`research-squad` §6)

生ログ 5 行は実在し、HTTP コード(400 / 400 / 200 / 405 / 451)は本文と一致した。調査班の返した「確かめるべき数値」10 件と本文の主張を、この環境で再実行・再読して突き合わせた(コマンドと出力は `docs/AUDITOR/ACTION_LOG.md` 050):

| 項 | 調査班の記述 | リードの実測 | 処置 |
|---|---|---|---|
| §A-1 経路 4 | 「CoinGlass を本日再実測 → HTTP 400(生ログ 1-2 行目)」 | 生ログ 1・2 行目は **OKX rubik** の URL。CoinGlass は今回プローブしていない | **直した**(09-17 午前の実測の転記に改めた) |
| §A-1 (c) SOURCES | 6 件 | `bitflyer_executions` / `okx_open_interest_1h` / `okx_open_interest_5m` / `okx_long_short_ratio` / `oi_snapshots` / `venues` の 6 件 | 一致 |
| §A 破損 11 個の dry-run | 59,944 行回収・1 行破棄 | 同じコマンドで 59,944 / 1 | 一致 |
| §A-13 BitMEX | `state: Settled`、`expiry 2026-09-16T12:00:00Z` | 生ログ 3 行目に同じ本文 | 一致 |
| §B P14 の行 | `OWNER_PROCEDURES.md:403-441` | `## P14` は 403 行目 | 一致 |
| §C(1) INTAKE | `data/` 20,283 行(09-08)/ `paper_logs/` 21,975 行(09-16) | 同じ(`wc -l`、mtime 09-08 07:03 / 09-16 11:32) | 一致 |
| §C(2) `DATA.md:92` | 最終確認日 2026-09-11 | 同じ | 一致 |
| §C(2) OKX 欠落 2 日 | 09-13・09-14 のディレクトリ無し | `ls` = 0905〜0912 と 0915 の 9 個 | 一致 |
| §C(2) 保持期間 | 2〜3 日(`constants.yaml:484-494`) | `okx_open_interest_5m_days: value: [2, 3]` | 一致 |
| §B SNAPSHOT_VERIFY | 「実在確認のみ、精査せず」 | 開いた: `ok false`、mismatch 11 単位、**O-3c の単位が 0 件照合**(`./` 付きパス) | **リードが追記した**(§B) |
| 生ログ 1・4 行目の `head200` | 4 行目に前行の本文が混入(調査班が自己申告) | 1 行目の `head200` も前の呼び出しの本文(`API key missing`)が混入している(HEAD で bytes=0 なのに本文がある) | 生ログはそのまま残し、ここに注記 |

**検収していないもの**: §A-6・7・8・9 の経路は `MISSING_2026-09-17.md` の転記(そちらで検収済み)。§C(1) の `share_logs.bat:20-30`・`intake_ledger.py`・`data_quality.py`・`verify_snapshots.py` の行番号は `sed -n` で開いて内容が合うことだけ見た。§C(3) の 3 案は仕様で、実測の対象ではない。
