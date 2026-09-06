# 板寄せ実約定コストの実測 — 実装設計(リード、2026-09-06)

`docs/PHASE2/EXEC_MEASUREMENT/PREREG.md` を実行するために必要な**最小限の**コード変更。
**本書の時点で執行コードは 1 行も書いていない**。§8 のチェックリストにオーナーの承認が入るまで書かない。

設計方針は 1 つ: **`src/bot/jpx/on1_executor.py` の安全包絡をそのまま写す**。
戦略は自明で、価値があるのは包絡のほう。新しい安全機構は発明せず、証明済みのものを現物株用に翻訳する。
`on1_executor.py` は**変更しない**(ON1 と本実測は状態・ロック・設定・env・ack 句をすべて分ける)。

---

## 1. 変更の全体像

| 種別 | ファイル | 規模 |
|---|---|---|
| 新規 | `src/bot/jpx/etf_auction_executor.py` | 現物株板寄せ執行器(on1_executor の写し) |
| 追記 | `src/bot/jpx/kabu_client.py` | 現物用の 3 メソッド追加。**分類・リトライ方針は一切触らない** |
| 新規 | `config/etf_exec_live.yaml` | 実弾ゲート・ポート・時間窓・銘柄 |
| 新規 | `scripts/run_etf_exec_entry.py` / `run_etf_exec_exit.py` / `run_etf_exec_reconcile.py` | プロセス包み(既存 `run_on1_*.py` と同型) |
| 新規 | `scripts/build_etf_exec_ledger.py` / `scripts/judge_etf_exec.py` | 台帳生成 / 一発集計(**初回発注の前に凍結**) |
| 新規 | `deploy/etf_entry.bat` / `deploy/etf_exit.bat` | タスクスケジューラ用 |
| 新規 | `schema/etf_exec_measurement.json` | 台帳スキーマ |
| 追記 | `docs/OPERATIONS.md` §5.2 | 運用手順(ON1 §5.1 と同型) |
| 新規 | `tests/test_etf_exec.py` | §7 |
| 任意 | `src/bot/monitoring/gates.py` + `scripts/judge_gates.py` | 進捗バー n = 50/銘柄 を係属ゲートに登録 |

---

## 2. `src/bot/jpx/etf_auction_executor.py`

### 2.1 コードで強制するハードリミット(設定で緩められない = モジュール定数)

```
MAX_LOTS_PER_SYMBOL      = 1        # 1 "売買単位"。1 "口" ではない
MAX_ORDERS_PER_DAY_PER_SYMBOL = 2   # 建て 1 + 決済 1。ロールなし
MAX_NOTIONAL_YEN         = 60_000   # 1 銘柄 1 発注あたりの約定代金の上限
ALLOWED_SYMBOLS          = ("1343", "1591")
ALLOWED_EXCHANGES        = (9, 27)  # SOR / 東証+。1(東証)は仕様上、通常時に新規不可
EXPECTED_TRADING_UNIT    = {"1343": 10, "1591": 1}
PRICE_BAND_PCT           = 10.0     # 建てのみ。板 vs 直近印字
HARD_ENTRY_WINDOW = ("15:00", "15:24")   # 引け板寄せ 15:30 の前
HARD_EXIT_WINDOW  = ("08:00", "08:50")   # 寄付き板寄せ 9:00 の前
LIVE_ACK_PHRASE = "I_UNDERSTAND_REAL_MONEY_JPX_ETF"   # ON1 とは別の句
```

**数量は定数にしない**。`Qty = GET /symbol/{symbol}@1` の `TradingUnit` を読み、
発注前に `Qty == TradingUnit == EXPECTED_TRADING_UNIT[symbol]` を検証する。
「1 口」を決め打つと 1343 で**単位割れの発注**になり、`EXPECTED` だけを見ると
2027-01-28 の 1591 の単位変更(PREREG §0)を取りこぼす。両方を突き合わせて初めて fail-close になる。

**約定代金の上限 `MAX_NOTIONAL_YEN` が最後の砦**: `Qty × 板の現値 > 60,000 円`なら発注しない。
1591 が分割・単位変更されると 10 口 × 37,000 円 = 370,000 円となり、**この 1 行が自動的に止める**。
「設計者が期日を覚えている」ことに頼らない。

### 2.2 状態機械(ON1 と同一の形、銘柄ごと)

- 建玉は常に `{0, +1 売買単位}`。`FLAT → LONG`(買いのみ)、`LONG → FLAT`(売りのみ)。
  **売りは唯一の買い建玉の現物売としてしか組み立てられない**(`CashMargin: 1` 固定 = 信用を使わないので、
  空売りは口座の側でも構造的に不可能)。
- `data/etf_exec/state_<symbol>.json` に永続化。プロセス再起動で取引は再開しない。
- **どちらか 1 銘柄が `STATE_UNKNOWN` なら両銘柄の新規発注を止める**(PREREG §6 の S2 に合わせた fail-close)。
- 発注カウンタは**発注前**に永続化して増やす(曖昧失敗も 1 枠消費)。
- 停止フラグ `data/etf_exec/paused.json` — S1/S3/S4/S6 が立てる。**自動復帰しない**。
  解除は人間が `operator_confirm` つきで消す(Kill Switch と同じ契約)。

### 2.3 発注ペイロード(`kabu_STATION_API.yaml` v1.5 `RequestSendOrder` より)

買い(引成):
```
Symbol=<1343|1591>, Exchange=9, SecurityType=1, Side="2", CashMargin=1,
DelivType=2, FundType="02", AccountType=<config>, Qty=<TradingUnit>,
FrontOrderType=16, Price=0, ExpireDay=0
```
売り(寄成):
```
Symbol=<同一>, Exchange=9, SecurityType=1, Side="1", CashMargin=1,
DelivType=0, FundType="  ", AccountType=<config>, Qty=<買った数量>,
FrontOrderType=13, Price=0, ExpireDay=0
```
- `DelivType` / `FundType` の非対称は仕様の明文: 現物買は `DelivType` 指定必須・`FundType` 指定必須、
  現物売は `DelivType: 0`・`FundType` は**半角スペース 2 つ**。定数として書き、サニティで突き合わせる。
- `FrontOrderType` 16 = 引成（後場）/ 13 = 寄成（前場）。いずれも `Price` は 0。
- **不明として記録する 3 点**(推測で埋めない。18081 で確認してから実弾):
  1. SOR(`Exchange 9`)が引成/寄成をどこへ回送するか。仕様書に記述がない。
     `GET /orders` の `Exchange` / `ExchangeName` を毎回台帳に残し、回送先を事後に見る。
  2. `ExpireDay: 0` が 15:20 / 08:40 に「当日」と解決されるか(仕様は「引けまでの間: 当日」)。
  3. 15:20 の引成、08:40 の寄成が受理されるか(時間帯の受付可否は仕様に明記なし)。
     拒否されれば確定的な 4xx = `KabuError` になり、アラートを記録して**それ以上何も送らない**。

### 2.4 発注前サニティ(1 つでも外れたら発注しない)

`_sanity_check(job, payload, symbol_info)`:
1. `Symbol ∈ ALLOWED_SYMBOLS`
2. `symbol_info["TradingUnit"] == EXPECTED_TRADING_UNIT[Symbol]` かつ `Qty == TradingUnit`
3. `Qty × 板現値 ≤ MAX_NOTIONAL_YEN`
4. `Exchange ∈ ALLOWED_EXCHANGES`、`SecurityType == 1`、`CashMargin == 1`
5. `Price == 0`(成行系は必ず 0)
6. `(Side, DelivType, FundType, FrontOrderType)` がジョブと完全一致
   — 建て = `("2", 2, "02", 16)` / 決済 = `("1", 0, "  ", 13)`
7. `AccountType ∈ {2, 4, 12}`
8. 値幅制限に接触していない(`UpperLimit`/`LowerLimit`)
9. 建てのみ: 板現値が直近の印字終値から `PRICE_BAND_PCT` 以内
   — **決済には価格帯チェックをかけない**(診断が実弾の建玉を一晩持ち越させてはならない。ON1 と同じ規則)

### 2.5 曖昧失敗

`OrderStateUnknown` → 状態を `STATE_UNKNOWN` に park、events に記録、以後**何も送らない**。
`KabuNetworkError`(送信前と証明できる失敗)→ `order_not_sent` を記録して状態は動かさない。**再送しない**。
`KabuError`(確定的な 4xx)→ `order_rejected` を記録。**再送しない**。

### 2.6 照合(読み取り専用)

`reconcile(query: QueryOnlyKabu)`。`QueryOnlyKabu` は `orders` / `positions` しか持たないので
**構造上発注できない**。積極的証拠のみで `FLAT` / `LONG` に確定。証拠がなければ `STATE_UNKNOWN` のまま。
現物なので `product="1"` を渡す。空の `/orders` は証拠ではない(結果整合のため遅延しうる)— ON1 と同じ扱い。
人間が `scripts/run_etf_exec_reconcile.py` を実行する。**スケジュールしない**。

---

## 3. `src/bot/jpx/kabu_client.py` への追記(3 メソッド。既存挙動は不変)

```python
PRODUCT_CASH = "1"          # /orders, /positions の product = 現物

def send_cash_order(self, payload: dict) -> dict:     # POST /sendorder
def symbol_info(self, symbol: str, exchange: int) -> dict:   # GET /symbol/{symbol}@{exchange}
def order_by_id(self, order_id: str) -> list[dict]:   # GET /orders?product=1&id=... (約定明細の取得)
```

- `"/sendorder"` は既に `ORDER_PATHS` に入っている → **リトライされず、曖昧失敗は `OrderStateUnknown`** という
  既存の契約がそのまま効く。分類ロジック・タイムアウト・リダクションには手を触れない。
- `orders()` / `positions()` は既に `product` を引数に取る → 現物は `product="1"` を渡すだけ。
- `symbol_info` / `order_by_id` は読み取り専用 = `diagnostic=True` の retry 経路。
- `QueryOnlyKabu` は `**kwargs` を素通しするので変更不要。**`send_cash_order` を絶対に生やさない**
  (テストで属性の不在を固定する)。

---

## 4. `config/etf_exec_live.yaml`(秘密情報は書かない。API パスワードは `.env` のみ)

```yaml
# 実弾は三重ゲート: ここの enabled + live_ack + env ETF_EXEC_LIVE=true。
# 欠ければ DRY RUN(ペイロードを data/etf_exec/events.jsonl に書くだけで、18081 にも送らない)。
enabled: false
live_ack: ""

port: 18081            # 18081 = 検証 / 18080 = 本番
exchange: 9            # 9 = SOR / 27 = 東証+。1(東証)はコードが拒否
account_type: 4        # 2=一般 / 4=特定 / 12=法人。オーナー確認事項

symbols: ["1591", "1343"]        # コードの ALLOWED_SYMBOLS の部分集合しか書けない
max_notional_yen_per_symbol: 60000   # コード定数より小さい値にしか下げられない

entry_window: ["15:10", "15:24"]
exit_window:  ["08:30", "08:50"]

# 除外日(PREREG §3。実行前に埋めて凍結する)
skip_dates: []          # 権利落ち日とその前営業日、SQ 前日
```

規則は ON1 の `load_on1_config` と同じ: 窓は**狭める方向にしか**効かない、`enabled` は裸の bool でなければ
`config_problem` を記録して disabled、銘柄は**コードの許可集合の部分集合**、`max_notional` は**下げる方向のみ**。
違反は無視 + `config_problem` イベント。

**ON1 とは別の env 変数・別の ack 句**にする(`ETF_EXEC_LIVE` / `I_UNDERSTAND_REAL_MONEY_JPX_ETF`)。
ON1 を実弾にする操作が本実測を実弾にしてはならない。逆も同じ。

---

## 5. 台帳スキーマ `schema/etf_exec_measurement.json`

既存の `schema/on1_onr_ledgers.json` と同型(`dataset` / `description` / `path_glob` / `source` /
`retention` / `file_groups` の列辞書 / `known_defects`)。

- `path_glob`: `data/etf_exec/events.jsonl`、`data/etf_exec/state_*.json`、`data/etf_exec/ledger.csv`、
  `data/etf_exec/paused.json`
- `retention`: **恒久**。ON1/ONR の紙台帳と違い、これは**実弾の測定記録そのもの**で、入力から再生成できない
  (約定価格は取引所の事実で、後から作り直せない)。消さない・上書きしない。
- `ledger.csv` の列(PREREG §4 の全量):
  `symbol, entry_date, exit_date, trading_unit, qty, exchange, exchange_name,
   entry_order_id, exit_order_id, fill_buy, fill_sell, fill_buy_time, fill_sell_time,
   print_close, print_open, print_source, board_close_snapshot, board_open_snapshot,
   idx_close, idx_open, tick_yen, tick_bps,
   e_buy_bps, e_sell_bps, c_bps, c_ticks,
   commission_yen, commission_tax_yen, pnl_yen, cum_pnl_yen,
   counted_in_n, excluded_reason, note`
- `counted_in_n`(bool)と `excluded_reason` を**列として持つ**のが要点。除外を「行を消す」で表現すると、
  除外規則が事後に動いたことを検出できなくなる。
- `known_defects` に最初から書く項目: (a) `print_close` の出所が判定に使った日次ベンダ系列であり、
  取引所の公式終値と一致する保証がないこと(だから板スナップショットも取る)、(b) `/orders` は結果整合で
  約定明細の反映が遅れうるため、台帳生成は**翌営業日以降に再取得して確定させる**こと、
  (c) SOR の回送先が仕様上不明であること。

---

## 6. スケジューラ

| タスク名 | トリガー | 操作 |
|---|---|---|
| `etf-exec-entry` | 平日 **15:20** | `<repo>\deploy\etf_entry.bat` |
| `etf-exec-exit` | 平日 **08:40** | `<repo>\deploy\etf_exit.bat` |

- ON1 の 08:35 と**5 分ずらす**(同一 PC の kabuステーションを 2 ジョブが同時に叩かないため。必須ではないが、
  障害時に events.jsonl の時刻でどちらのジョブかを迷わなくて済む)。
- ロックファイルは ON1 と別: `data/etf_exec/{entry,exit,reconcile}.lock`。`bot/jpx/run_lock.py` を再利用。
- bat は `deploy/on1_entry.bat` の写し(`cd /d "%~dp0.."`、ログは `logs\etf_exec.out.log` に追記、`exit /b 0`)。
- `deploy/fetch_all.bat` に日次系列の取得を 2 行足す(1343/1591 の日次 + 東証REIT指数 + JPX日経400 指数)。
  台帳の `print_close` / `idx_*` はこれを参照する。
- 照合(`run_etf_exec_reconcile.py`)は**スケジュールしない**(人間が実行)。

---

## 7. 書くテスト(`tests/test_etf_exec.py`。ON1 の 53 件と同じ密度を目標)

**ゲートと設定**
1. 既定設定は disabled かつ検証ポート / 2. 三重ゲートの真理値表(8 通り) / 3. `enabled: "false"`(引用符)は起動しない /
4. 窓は狭められるが広げられない / 5. 銘柄はコードの許可集合の部分集合しか通らない / 6. `max_notional` は下げる方向のみ /
7. `ETF_EXEC_LIVE` が立っても ON1 は実弾にならない(逆も。**ack 句と env の分離を固定する**)

**数量・単位・上限**
8. `TradingUnit` 10 → `Qty` 10(1343)/ 9. `TradingUnit` 1 → `Qty` 1(1591)/
10. `TradingUnit` が事前登録値と違う → 発注しない(S6)/ 11. `TradingUnit` 100(分割後の想定)→ 約定代金上限で拒否 /
12. `Qty × 現値 > 60,000` → 拒否

**ペイロードのサニティ**
13. 買いペイロードが仕様どおり(`Side "2"`, `CashMargin 1`, `DelivType 2`, `FundType "02"`, `FrontOrderType 16`, `Price 0`)/
14. 売りペイロードが仕様どおり(`Side "1"`, `DelivType 0`, `FundType` = 半角スペース 2 つ, `FrontOrderType 13`)/
15. `Exchange 1` を設定に書いても拒否 / 16. 改竄したペイロード(数量・価格・side)は fail-close /
17. 値幅制限接触で建てない / 18. 建てのみ価格帯チェック、**決済は価格帯で止めない**

**状態機械**
19. 建て → LONG、決済 → FLAT / 20. LONG から二重に建てない / 21. FLAT から決済しない /
22. 状態は再起動をまたぐ / 23. 1 日 2 発注/銘柄の上限 / 24. 発注枠は**送信前**に消費される /
25. 決済前に `/positions` が期待どおりでなければ発注しない

**曖昧失敗と照合**
26. 曖昧失敗 → `STATE_UNKNOWN` に park / 27. `STATE_UNKNOWN` は**両銘柄**の新規発注を止める /
28. 送信前と証明できる失敗は状態を動かさない / 29. 確定的 4xx は再送しない /
30. 照合は積極的証拠でのみ確定 / 31. 空の `/orders` は証拠にならない / 32. 証拠なしなら `STATE_UNKNOWN` のまま /
33. `QueryOnlyKabu` に送信メソッドが**存在しない**ことを固定

**停止規則(PREREG §6)**
34. 3 ティック超の乖離を記録すると `paused.json` が立ち、以後の建てが止まる(S1)/
35. 停止中でも既存建玉の**決済は通る** / 36. 不成立 2 夜連続で停止(S3)/ 37. 累計損益 −15,000 円で停止(S4)/
38. `KILL` ファイル / `data/kill_switch.json` で何もしない(S5)/ 39. 停止は自動復帰しない

**暦**
40. 除外日は建てない / 41. SQ 前日は建てない / 42. 時間窓の外では何も送らない

**台帳と集計**
43. `c_bps` の既知正解テスト(合成行: 約定 = 印字 → c = 0、片側 1 ティック → c = 1 ティック相当)/
44. `counted_in_n=False` の行は集計に入らない / 45. ブロック・ブートストラップの再実行決定性(seed 固定)/
46. 合格バー 6.1 / 6.3bps が**判定案の文面と一致**していることをテストで固定(定数の重複を検出する)

**秘密**
47. `events.jsonl` にパスワード・トークンが出ない(`redact` を通ることの確認)

---

## 8. オーナー承認チェックリスト(全部埋まるまで実弾に進まない)

**口座・資金**

- [ ] 使う証券口座を特定した(kabuステーションが動いている PC の口座)
- [ ] `AccountType` を確定した(2 = 一般 / **4 = 特定** / 12 = 法人)
- [ ] 現物買付余力が **60,000 円以上**ある(1343 の 19,250 円 + 1591 の 37,000 円 + 余裕)
- [ ] この口座で ETF の現物取引が可能で、SOR 経由の手数料が 0 円であることを口座画面で確認した
- [ ] 損失の想定帯 **±10,000 円**、停止線 **−15,000 円**(PREREG §7)を了承した

**接続・ポート**

- [ ] kabuステーションが対象 PC で起動・ログイン済み、`.env` に `KABU_API_PASSWORD` がある
- [ ] **検証ポート 18081** で 3 つの「不明」を確認した(DESIGN §2.3): SOR の回送、`ExpireDay: 0` の解決、
      15:20/08:40 の受付可否
- [ ] 18081 で dry-run ではなく実際の発注テストを一巡し、`/orders` の `Details[] RecType 8` から
      約定価格・手数料が取れることを確認した
- [ ] 本番ポート **18080** に切り替える判断を明示的に行った(`config/etf_exec_live.yaml: port`)

**LIVE ゲート(3 つすべて。1 つでも欠ければ dry-run)**

- [ ] `config/etf_exec_live.yaml: enabled: true`
- [ ] `config/etf_exec_live.yaml: live_ack: "I_UNDERSTAND_REAL_MONEY_JPX_ETF"`
- [ ] env `ETF_EXEC_LIVE=true`
- [ ] これらが **ON1 のゲートとは独立**であることを確認した(ON1 を止めても本実測は動く、逆も同じ)

**事前登録**

- [ ] `PREREG.md` 付録 A(除外日一覧・開始日・想定終了日・口座種別・ポート)を埋めて凍結した
- [ ] 集計スクリプト `scripts/judge_etf_exec.py` を**初回発注の前に**書き、出力形式を凍結した
- [ ] 合格バー 6.1bps(1343)/ 6.3bps(1591)と、不合格 = 棄却という帰結を了承した
- [ ] **この 50 往復の損益はプレミアムの証拠ではない**(PREREG §1)ことを了承した
- [ ] 締切 **2027-01-27**(1591 の単位変更 2027-01-28・分割 2027-02-01)を了承した

**運用**

- [ ] タスクスケジューラ 2 件(平日 15:20 / 08:40)を登録し、「ログオンしていなくても実行する」にした
- [ ] `STATE_UNKNOWN` 時の手順(`scripts/run_etf_exec_reconcile.py` を**人間が**実行、読み取り専用、
      `unresolved` なら口座画面を目視して `state_<symbol>.json` を意図して書き換える)を読んだ
- [ ] 緊急停止(リポジトリ直下 `KILL`)が本実測にも効くことを確認した
- [ ] `docs/OPERATIONS.md` §5.2 を追記した

---

## 9. やらないこと(スコープの境界を明示)

- `on1_executor.py` の変更(共通化の誘惑がある。**しない**。安全機構の共通化は、片方のバグが両方に伝播する)
- 発注コードを本書の時点で書くこと(§8 の承認が先)
- 板の厚み・スプレッドの記録機構(`config/constants.yaml: etf_spread_bps` の TODO は別件。
  本実測は「実約定 vs 印字」であって「板の形」ではない)
- ダッシュボードへの新タイル(進捗バーを出すなら §1 の任意項目 = `gates.py` への n = 50 登録だけ)
- 1306 / 2516 / 1348 / 1305 への横展開(RESOURCES R5・R6。別単位)
