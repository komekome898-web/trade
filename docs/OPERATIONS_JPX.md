# JPX(大阪取引所)側 運用手順

暗号資産 CFD 側の運用手順は `docs/OPERATIONS.md`。本書は ON1(先物)と現物 ETF 板寄せ実測の実弾ジョブ専用。

## 5.1 ON1(日経225マイクロ先物オーバーナイト)の自動執行

`docs/ON1_LIVE_PLAN.md` L1。**既定は dry-run**(発注ペイロードを
`data\on1_live\events.jsonl` に書くだけで、検証ポート18081にも送らない)。

### 前提

- kabuステーションが**同一PCで起動・ログイン済み**であること(APIはlocalhost)。
  起動していなければジョブは `order_not_sent` を記録して終了する(再送しない)
- `.env` に `KABU_API_PASSWORD=`(APIパスワード。YAMLには絶対に書かない)
- `data\jpx_daily\nk225_sessions.csv` が最新であること
  (`deploy\fetch_all.bat` が毎日更新。5日以上古いと中心限月が引けず**発注しない**)

### タスクスケジューラ登録(2タスク追加)

| タスク名 | トリガー | 操作(プログラム。引数・開始は空欄) |
|---|---|---|
| on1-entry | **平日 15:35**(毎週・月〜金) | `<repo>\deploy\on1_entry.bat` |
| on1-exit | **平日 08:35**(毎週・月〜金) | `<repo>\deploy\on1_exit.bat` |

両タスクとも「全般」タブで **「ログオンしていなくても実行する」** を選択し、
「最上位の特権で実行する」はチェック不要。「設定」タブの
**「タスクを停止するまでの時間: 1時間」** はそのままでよい。
二重起動は `data\on1_live\*.lock` のロックファイルで防いでいるので、
「既に実行中の場合: 新しいインスタンスを開始しない」でも「並列」でも安全。

### LIVE の二重ゲート(オーナー承認制)

3つ**すべて**が揃わなければ1件も発注しない:

1. `config\on1_live.yaml` の `enabled: true`
2. `config\on1_live.yaml` の `live_ack: "I_UNDERSTAND_REAL_MONEY_JPX"`
3. env `ON1_LIVE=true`

欠けている場合は dry-run になり、events.jsonl の各行に `live: false` と
欠けている条件が残る。ポート(`port:` 既定18081=検証)は**このゲートとは別**で、
ゲートが開いていなければ18081にも送らない。

### コードで強制しているハードリミット(設定で緩められない)

- 建玉は常に {0, +1枚}。売りは唯一の買い建玉の返済としてしか組み立てられない
- 1日の発注は最大4件(発注**前**にカウンタを永続化するので、曖昧失敗も1枠消費)
- 発注前サニティ(銘柄コードの形・SymbolNameに「マイクロ」・限月・売買方向と
  取引区分がジョブと一致・数量1・成行はPrice 0)に1つでも失敗したら**発注しない**
- SQ(第2金曜)の1週間前から**エントリーをスキップ**(限月ロールの端は fail-close)
- リポジトリ直下 `KILL` / `data\kill_switch.json` があれば何もしない

### STATE_UNKNOWN(曖昧な発注失敗)からの復帰

タイムアウト・5xx・OrderId無しの200 は `OrderStateUnknown` として
`data\on1_live\state.json` に保持され、**自動リトライしない**。以後 ON1 は
エントリーもエグジットも発注しない。復帰は人間の作業:

```
.venv\Scripts\python.exe scripts\run_on1_reconcile.py
```

これは**読み取り専用**(`/orders` と `/positions` しか持たない `QueryOnlyKabu` を
使うので構造上発注できない)。積極的証拠が取れたときだけ FLAT / LONG に確定する。
`unresolved` なら口座画面を人間が確認し、`state.json` を意図して書き換えること。

ログ: `logs\on1.out.log` / イベント: `data\on1_live\events.jsonl`。

## 5.2 現物ETF板寄せ実約定コストの実測(1343 / 1591 / 1348)

`docs/PHASE2/EXEC_MEASUREMENT/PREREG.md`(事前登録)と `DESIGN.md`(実装設計)。
**既定は dry-run**(発注ペイロードを `data\etf_measure\events.jsonl` に書き、
「WOULD send …」を標準出力に出すだけで、検証ポート18081にも送らない)。

測るのは 1 つだけ: **引成で買い、翌寄成で売ったときの実約定価格が、印字された
終値・始値からどれだけ離れるか**(往復執行コスト c)。各銘柄 50 往復。
対象銘柄は 1343(1売買単位=10口 ≈ 19,250 円)/ 1591(1口 ≈ 37,000 円)/
**1348(1口 ≈ 4,255 円。PREREG 追記 2026-09-06 のオーナー判定で追加)**。
同時に晒す資金は 3 銘柄で **約 60,500 円**。60,000 円の上限は**1発注あたり**であって合計ではない。
**この 50 往復の損益は戦略の証拠にならない**(n=50 では検出力が足りない。測るのは
執行コスト c であって戦略の期待値ではない)。

### ON1 との関係(独立。片方を実弾にしても、もう片方は動かない)

| | ON1(先物) | 本実測(現物ETF) |
|---|---|---|
| 設定 | `config\on1_live.yaml` | `config\etf_measure.yaml` |
| env | `ON1_LIVE` | **`ETF_EXEC_LIVE`** |
| ack 句 | `I_UNDERSTAND_REAL_MONEY_JPX` | **`I_UNDERSTAND_REAL_MONEY_JPX_ETF`** |
| 状態 | `data\on1_live\state.json` | `data\etf_measure\state_1343.json` / `state_1591.json` / `state_1348.json` |
| ロック | `data\on1_live\*.lock` | `data\etf_measure\*.lock` |
| ログ | `logs\on1.out.log` | `logs\etf_measure.out.log` |
| 台帳 | `paper_logs\on1_ledger.csv` | `paper_logs\etf_measure_ledger.csv`(**恒久記録**) |

`src\bot\jpx\on1_executor.py` は**変更していない**。安全機構は共通化せず、
現物用に写した(共通化すると片方のバグが両方に伝播する)。

### タスクスケジューラ登録(2タスク追加。ON1 の2件とは別)

| タスク名 | トリガー | 操作(プログラム。引数・開始は空欄) |
|---|---|---|
| etf-measure-entry | **平日 15:20**(毎週・月〜金) | `<repo>\deploy\etf_measure_entry.bat` |
| etf-measure-exit | **平日 08:40**(毎週・月〜金) | `<repo>\deploy\etf_measure_exit.bat` |

両タスクとも「ログオンしていなくても実行する」を選択する。
**08:40 は ON1 の 08:35 とわざと5分ずらしてある**(同一PCの kabuステーションを
2ジョブが同じ分に叩かないため。障害時に events.jsonl の時刻でどちらのジョブか迷わない)。
二重起動は `data\etf_measure\*.lock` で防いでいる。
照合(`run_etf_measure_reconcile.py`)は**スケジュールしない**(人間が実行)。

### LIVE の三重ゲート(オーナー承認制)

3つ**すべて**が揃わなければ1件も発注しない:

1. `config\etf_measure.yaml` の `enabled: true`
2. `config\etf_measure.yaml` の `live_ack: "I_UNDERSTAND_REAL_MONEY_JPX_ETF"`
3. env `ETF_EXEC_LIVE=true`

欠けている場合は dry-run になり、events.jsonl の各行に `live: false` と
欠けている条件が残る。ポート(`port:` 既定18081=検証)は**このゲートとは別**で、
ゲートが開いていなければ18081にも送らない。

### コードで強制しているハードリミット(設定で緩められない)

- 建玉は銘柄ごとに常に {0, +1売買単位}。`CashMargin: 1`(現物)固定なので空売りは構造上不可能
- **数量は定数ではない**。`GET /symbol` の `TradingUnit` を読み、
  `Qty == TradingUnit == 事前登録値(1343=10 / 1591=1 / 1348=1)` の**3つが一致**しなければ発注しない
- **約定代金 60,000 円/発注**が最後の砦。1591 の単位変更(2027-01-28)や分割(2027-02-01)で
  1 単位が 37 万円になれば、**この 1 行が自動的に止める**(人が期日を覚えていることに頼らない)
- 1日の発注は銘柄あたり最大2件(発注**前**にカウンタを永続化するので、曖昧失敗も1枠消費)
- 発注前サニティ(銘柄・単位・約定代金・市場・現物区分・Price 0・
  (Side, DelivType, FundType, FrontOrderType) がジョブと完全一致・口座区分・値幅制限)に
  1つでも失敗したら**発注しない**
- **建てのみ**価格帯チェック(直近印字終値から ±10%)。**決済には掛けない**
  (診断が実弾の建玉を一晩持ち越させてはならない)
- 権利落ち日とその前営業日(`skip_dates`。PREREG 付録 A で凍結。全銘柄に効く)と
  **四半期SQの前日**(コードで導出)は建てない。
  **1348 の権利落ち日は銘柄ごとに導出**する(封印済みスナップショット
  `backtest_data\jpx_etf_daily_20260906_topix_alt\1348.T.json` の配当イベントから。
  1348 の権利落ちで 1343 / 1591 の夜を落とさないよう、除外は銘柄別)。
  スナップショットは**過去の記録**なので、観測 14 年すべてが 1/16・7/16 で一致している
  ことを条件に、同じ命日を**2 年先まで延長**する(2027-01-16 が測定窓に入るため)。
  延長は**スキップを増やす方向にしか働かない**が、発行会社が実際の権利落ち日を公表したら
  `skip_dates` に凍結して書くこと(PREREG 付録 A)
- リポジトリ直下 `KILL` / `data\kill_switch.json` があれば何もしない

### 停止規則(PREREG §6。`data\etf_measure\paused.json`)

S1 片脚が印字から3ティック超ずれた(全銘柄停止)/ S2 STATE_UNKNOWN(全停止)/
S3 同一銘柄で不成立2夜連続 / S4 実現損益の累計が −15,000 円未満 /
S5 Kill Switch / S6 `TradingUnit` が事前登録値と違う(その銘柄) /
S7 手数料が0円でなかった(記録のみ、停止しない)。

**停止は自動復帰しない**。`paused.json` の削除は原因を理解しオーナーが同意してからのみ。
**停止中でも既存建玉の決済は通る**(閉じる脚は決してゲートしない)。

### STATE_UNKNOWN(曖昧な発注失敗)からの復帰

タイムアウト・5xx・OrderId無しの200 は `OrderStateUnknown` として
`data\etf_measure\state_<銘柄>.json` に保持され、**自動リトライしない**。
以後**全銘柄**のエントリーもエグジットも発注しない。復帰は人間の作業:

```
.venv\Scripts\python.exe scripts\run_etf_measure_reconcile.py
```

これは**読み取り専用**(`/orders` と `/positions` しか持たない `QueryOnlyKabu` を
使うので構造上発注できない)。積極的証拠が取れたときだけ FLAT / LONG に確定する。
空の `/orders` は証拠ではない(結果整合で遅延しうる)。
`unresolved` なら口座画面を人間が確認し、`state_<銘柄>.json` を意図して書き換えること。
同じコマンドが、約定明細が見えるようになった往復を台帳へ確定させる(これも読み取り専用)。

ログ: `logs\etf_measure.out.log` / イベント: `data\etf_measure\events.jsonl` /
台帳: `paper_logs\etf_measure_ledger.csv`(スキーマ `schema\etf_measure_ledger.json`。
**恒久記録** — 約定価格は取引所の事実で、入力から作り直せない)。

### オーナー承認チェックリスト(DESIGN §8 からの転記。全部埋まるまで実弾に進まない)

**口座・資金**

- [ ] 使う証券口座を特定した(kabuステーションが動いている PC の口座)
- [ ] `AccountType` を確定した(2 = 一般 / **4 = 特定** / 12 = 法人)
- [ ] 現物買付余力が **65,000 円以上**ある(1343 の 19,250 円 + 1591 の 37,000 円 + 1348 の 4,255 円 = 約 60,500 円 + 余裕)
- [ ] この口座で ETF の現物取引が可能で、SOR 経由の手数料が 0 円であることを口座画面で確認した
- [ ] 3 銘柄(1343 / 1591 / 1348)を同じ夜に建てることを了承した(PREREG 追記 2026-09-06)
- [ ] 損失の想定帯 **±10,000 円**、停止線 **−15,000 円**(PREREG §7)を了承した

**接続・ポート**

- [ ] kabuステーションが対象 PC で起動・ログイン済み、`.env` に `KABU_API_PASSWORD` がある
- [ ] **検証ポート 18081** で 3 つの「不明」を確認した(DESIGN §2.3): SOR の回送、`ExpireDay: 0` の解決、
      15:20/08:40 の受付可否
- [ ] 18081 で dry-run ではなく実際の発注テストを一巡し、`/orders` の `Details[] RecType 8` から
      約定価格・手数料が取れることを確認した
- [ ] 本番ポート **18080** に切り替える判断を明示的に行った(`config/etf_measure.yaml: port`)

**LIVE ゲート(3 つすべて。1 つでも欠ければ dry-run)**

- [ ] `config/etf_measure.yaml: enabled: true`
- [ ] `config/etf_measure.yaml: live_ack: "I_UNDERSTAND_REAL_MONEY_JPX_ETF"`
- [ ] env `ETF_EXEC_LIVE=true`
- [ ] これらが **ON1 のゲートとは独立**であることを確認した(ON1 を止めても本実測は動く、逆も同じ)

**事前登録**

- [ ] `PREREG.md` 付録 A(除外日一覧・開始日・想定終了日・口座種別・ポート)を埋めて凍結した
      → `config/etf_measure.yaml: skip_dates` に同じ日付を書く
- [ ] 集計の出力形式を**初回発注の前に**凍結した
      (`bot.jpx.etf_auction_executor.summarise_ledger`。seed・ブロック長・回数は定数)
- [ ] 合格バーは**未設定**(旧バーは 2026-09-08 の全捨てで失効)。測定前に新しい事前登録が要る
- [ ] **この 50 往復の損益は戦略の証拠ではない**(執行コストの測定である)ことを了承した
- [ ] 締切 **2027-01-27**(1591 の単位変更 2027-01-28・分割 2027-02-01)を了承した

**運用**

- [ ] タスクスケジューラ 2 件(平日 15:20 / 08:40)を登録し、「ログオンしていなくても実行する」にした
- [ ] `STATE_UNKNOWN` 時の手順(`scripts/run_etf_measure_reconcile.py` を**人間が**実行、読み取り専用、
      `unresolved` なら口座画面を目視して `state_<銘柄>.json` を意図して書き換える)を読んだ
- [ ] 緊急停止(リポジトリ直下 `KILL`)が本実測にも効くことを確認した
- [ ] `docs/OPERATIONS_JPX.md` §5.2(本節)を読んだ

### 検証ポート(18081)での dry-run 手順

```
.venv\Scripts\activate
set PYTHONPATH=src
python scripts\run_etf_measure_entry.py
python scripts\run_etf_measure_exit.py
python scripts\run_etf_measure_reconcile.py
```

`config\etf_measure.yaml` が既定(`enabled: false`)のままなら、これらは
**1 件も発注せず**、送るはずだったペイロードを「WOULD send …」として表示する。
時間窓(15:10〜15:24 / 08:30〜08:50)の外で実行すると `skip` になるので、
窓の中で実行するか、`entry_window` / `exit_window` を一時的に**狭める**方向で調整する。

