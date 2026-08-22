# 運用手順書(自宅PC / Raspberry Pi)

このボットは **PAPER MODE(仮想売買)がデフォルト**です。本書の手順はすべて実注文を送りません。
LIVE MODE への移行はオーナーの明示承認後、別途手順を定めます。

## 1. 導入(Linux / Raspberry Pi)

```bash
git clone https://github.com/komekome898-web/trade.git
cd trade
git checkout claude/bitflyer-trading-bot-hhxxaf
bash deploy/setup.sh
```

`setup.sh` は venv 作成 → インストール → `.env` 雛形作成 → テスト実行まで行います。
その後 `.env` を編集して APIキーを設定します(**参照+取引のみ。出金権限は付けない**)。
bitFlyer 側でAPIキーに**自宅の固定IPがあればIP制限**を掛けるとより安全です(動的IPの場合は無理に設定しない)。

確認:

```bash
.venv/bin/python scripts/check_api.py      # API疎通・認証・出金権限なしの確認(read-only)
.venv/bin/python scripts/fetch_history.py  # 約定履歴の取得と1分足生成
```

## 2. 24時間稼働(systemd)

```bash
# ユニットファイル内の CHANGE_ME_USER とパス2箇所を自分の環境に書き換えてから:
sudo cp deploy/bitflyer-bot.service /etc/systemd/system/
sudo cp deploy/bitflyer-fetch.service deploy/bitflyer-fetch.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bitflyer-fetch.timer   # データ蓄積(15分毎)
sudo systemctl enable --now bitflyer-bot           # ペーパートレードBOT
```

状態確認:

```bash
systemctl status bitflyer-bot
journalctl -u bitflyer-bot -f          # ライブログ
cat logs/status.json                    # 稼働状態・価格・残高・PnL・DD・エラー数
tail -f logs/bot.jsonl                  # 全売買判断の構造化ログ
```

## 3. 停止と Kill Switch

| 操作 | コマンド |
|---|---|
| 通常停止 | `sudo systemctl stop bitflyer-bot` |
| 緊急停止(Kill Switch) | リポジトリ直下に `touch KILL` |
| Kill Switch 状態確認 | `cat data/kill_switch.json` |
| Kill Switch 解除(原因調査後のみ) | `.venv/bin/python -c "import sys; sys.path.insert(0,'src'); from bot.risk.kill_switch import KillSwitch; KillSwitch().reset(operator_confirm=True)"` |
| サイジングブレーキ状態確認 | `cat data/overlay_state.json` |
| サイジングブレーキ解除(口座を作り直した時のみ) | `rm data/overlay_state.json` |
| PAPER 帳簿の確認 | `cat data/paper_state.json` |
| PAPER 帳簿のリセット(仮想口座を作り直す時のみ) | `rm data/paper_state.json` |

重要: Kill Switch はファイルに永続化されるため、**systemd がプロセスを再起動しても取引は再開しません**。解除は必ず原因(status.json / bot.jsonl / kill_switch.json)を確認してから行ってください。

`kill_switch.json` の `reason` は `daily_loss_limit` / `max_drawdown` /
`consecutive_losses` / `api_errors` / `order_state_unknown` /
`market_data_anomaly` / `system_error` / `unhandled_exception` / `manual` の
いずれかです。

- `unhandled_exception` — 取引ループ内で想定外の例外が出たことを示します。状態不明
  とみなしてプロセスが落ちる前に発動するため(`detail` に例外の repr)、再起動しても
  取引は再開しません。解除手順は他の理由と同じで、原因調査後に上の
  `reset(operator_confirm=True)` を人間が実行します。

### data/paper_state.json(PAPER の帳簿)

PAPER モードの帳簿。約定のたび・日付が変わった時・停止時に書かれ、再起動しても
引き継がれます(**LIVE では読み書きしません**。LIVE の建玉は取引所が正で、
そちらと突き合わせます — これは方針ではなく**コードの動作**で、下記の
「LIVE 起動時の建玉照合」がその実装です)。

### LIVE 起動時の建玉照合(LIVE のみ)

LIVE の起動は `/v1/me/getpositions`(診断用タイムアウト)を1回叩き、取引所が
報告する**ネット建玉(サイズ・売買方向・平均建値)をそのまま portfolio に取り込みます**
(`src/bot/main.py: _adopt_venue_position`)。取り込んだ内容はログ1行
(`live_boot_position_adopted`)と通知
(`LIVE boot: adopted venue position ...`)に必ず出ます。

- 「LIVE は帳簿を持たない」を**フラットで起動**として実装していたため、再起動のたびに
  「取引所には建玉があるのに BOT はフラットだと思っている」状態で起動していました。
  この状態は自力では直りません(定期スイープが見るのは**この帳簿が知っている注文**だけで、
  再起動前に建った建玉にはそんな注文が無い)。結果は2つとも致命的で、
  **逆指値が armed にならない**(守る対象が無いことになっている)、
  **次のエントリーが実建玉の上に積み増す**(MAX_POSITION_SIZE が効かない)。
- **読めなかった時はフラットと仮定しません**。Kill Switch を
  `system_error` / `live boot reconciliation failed` で発動させて起動を拒否します
  (建玉があるのに平均建値が取れなかった場合も同じ扱い — 守れない建玉だからです)。
  原因を調べ、bitFlyer 側の建玉を確認してから人間が
  `reset(operator_confirm=True)` します。
- **取り込んだ建玉には、帳簿の約定がすでに含まれています**。そのため取り込みの直後に
  非終端の注文すべてについて `booked_size := filled_size` へ進めます
  (`_adopt_fill_watermarks`、ログ `live_boot_watermarks_adopted`)。前のプロセスが
  watermark を書き切れずに落ちていると、最初の定期スイープが同じ約定を
  **取り込んだ建玉の上にもう一度計上**してしまうためです(旧 sqlite 移行と同じ規則 —
  「取り込んだ = 計上済み」)。書き込めなかった時は起動を拒否します。
- **前のプロセスが残した `PENDING_SUBMIT`(acceptance id 無し)も起動時に片付けます**
  (`OrderManager.adopt_stale_pending`)。getchildorders を1回だけ読み、
  積極的証拠(商品・売買方向・数量、LIMIT なら価格)で一致すれば acceptance id と
  状態を取り込み、**一致しなければ `ABANDONED`(終端)** にします。プロセス再起動を
  跨いだレコードは、getchildorders の遅延(数秒)よりはるかに古いためです。
  取引所が**読めなかった時は触りません**(証拠が無いので)。いずれも通知
  `LIVE BOOT: UNSENT ORDER RECORDS RESOLVED` に出ます。放置すると重複注文ガードが
  これを数え、**次の注文(逆指値を含む)が黙って拒否**されていました。
- PAPER はこの経路を**一切通りません**(PAPER の正は `data/paper_state.json`)。

- `product_code` — この帳簿が属する商品。起動時の商品と**違えば復元しません**
  (サイズ・建値・残高は商品をまたぐと意味が変わるため)。古い方は
  `paper_state.<商品名>.bak` に退避し、警告1行を出して新規の帳簿で始めます。
- `realized_pnl_jpy` — 累積の実現損益(手数料込み)。ダッシュボードの
  仮想残高 = `paper_equity_jpy` + この値 + 含み損益。
- `trade_count` — 累積の約定回数(新規と決済で2回)。
- `daily_pnl_jpy` / `daily_date` — 当日の**実現**損益と、それが属する UTC 日付。
  起動時は日付が当日と一致する時だけ復元し、日付が変わっていれば 0 から始めます
  (含み損益は現在値から計算し直すので保存しません)。この2つは Portfolio の
  日付インデックスの**1回の読み取り**から作ります(日付だけ別に取り直すと、
  日をまたいだ瞬間に前日の消費枠が当日の日付で保存され得るため)。
- `position` — 建玉(`side` / `size` / `entry_price` / `opened_ts`)、無ければ null。
  ここが壊れている場合は**建玉だけ**を捨てて(警告1行・フラットで起動)、実現損益と
  当日枠は残します。

これが無かった頃は、再起動のたびに仮想残高が初期値に戻り、**建玉を持ったまま忘れ**、
さらに **MAX_DAILY_LOSS_JPY の当日枠が満額に戻っていました**(ウォッチドッグ再起動で
日中に損失上限が実質リセットされる)。当日枠は UTC 日付が変われば自然に消えるので、
引き継いでも詰みません。

一方で**連敗数と equity ピークは保存しません**。これらはハードなリスクチェック
(=Kill Switch を発動させる側)の入力で、他プロセスの履歴で発動させると、解除しても
次回起動でまた発動する詰み状態になるためです(`src/bot/strategy/composite.py` の
モジュール docstring)。

含み損を抱えた建玉を復元した時の**2つのブレーキの基準点**も同じ理由で起動時に取り直
します。どちらも「**起動後の最初の値段**」を基準にします:

- 当日損益の含み分 = (現在値 − その基準値段) × 建玉。前日までに動いた分は当日の
  MAX_DAILY_LOSS_JPY 枠から引きません(その日の枠から既に引かれています)。UTC 日付が
  変わった時も同様に、その時点の値段で取り直します。**起動後の逆行は従来どおり全額**
  当日枠から引かれます。
- equity ピーク = 起動時の**時価評価**(初期 + 復元した実現損益 + その時点の含み損益)。

これが無いと、5% 含み損の建玉を復元した瞬間に日次損失/最大DDが上限超過となり、その
建玉を閉じるはずの逆指値自体が拒否され、Kill Switch を解除しても次の起動でまた発動する
(解除不能なループ)状態になります。実現損益の当日計上は従来どおりです。

Kill Switch とは別物で、**このファイルは取引を止めません**。壊れている・存在しない
場合は警告1行を出して新規の帳簿(全部ゼロ・建玉なし)で起動します。消してよいのは
仮想口座を作り直す時だけで、その時は `data/overlay_state.json` も併せて消します。

### data/overlay_state.json(リスクオーバーレイのブレーキ)

composite 戦略のリスクオーバーレイ(新規建玉のサイズを縮小する仕組み)の状態。
決済のたびに書かれ、再起動しても引き継がれます(連敗中にクラッシュした直後こそ
サイズは小さいべきなので、プロセス再起動でリセットされてはいけない)。

- `consecutive_losses` — 連敗数。
- `dd_frac` — 保存時点の「equity ÷ ピーク equity」(≦1.0)。**相対**ドローダウンだけを
  保存し、JPY のピーク額は保存しません。額を保存すると `paper_equity_jpy` を変えた
  だけで存在しないドローダウンが復元されてしまうためです。起動時は
  `起動時 equity ÷ dd_frac` でピークを再構成します。

Kill Switch とは別物です。**このファイルは取引を止めません**(止めるのは Kill Switch
だけ)。消してもBOTは起動し、ブレーキが解除されて通常サイズに戻るだけです。壊れて
いる・存在しない場合も安全な既定値(ドローダウンなし・連敗0)で起動します。

注意: この状態は**どの戦略で走っていても蓄積されます**(champion の
`xborder_momentum` を含む)。決済のたびに書かれるのは戦略に依らず、
サイズ縮小に**使う**のが composite だけです。したがって champion で連敗した後に
composite へ切り替えると、その時点のブレーキがそのまま効きます。
現状(champion 稼働中)にこのファイルがあるのは正常で、異常ではありません。

削除してよいのは、口座を作り直した・`paper_equity_jpy` を変えた等で、蓄積された
ブレーキがもはや実態を表していない時だけです。連敗で縮小されているのを「戻したい」
という理由で消してはいけません。

`data/paper_state.json` とは役割が別です:あちらは PAPER の帳簿(残高・建玉・
当日損益)、こちらは新規建玉のサイズ縮小ブレーキだけ。ピークと連敗数はこちらにしか
無く、二重には持ちません。

### composite モジュールの効果はバックテストでは測れない

`config/composite.yaml` のモジュール(`radar_window` / `long_only` ほか)は
**バックテストエンジンからは見えません**。エンジンは `on_candles` しか呼ばず
`gate_entry` を呼ばないため、composite のエンジン実行は「コアシグナルだけ」の
再現であり、モジュールを有効にしても結果は一切変わりません
(`scripts/validate_composite.py` G1 はこの範囲を明示し、モジュールが有効なら
FAIL します)。

したがって:

- モジュールの**挙動**の検証はライブ経路で行う — `validate_composite.py` G4 が
  実際の paper TradingApp に一時的にモジュールを載せて、窓外エントリー抑止 /
  窓内エントリー通過 / 決済は常に通過、を確認します。
- モジュールの**価値**の判定は champion のペーパー取引の部分集合で行う
  (`docs/KNOWLEDGE.md` §5 の常設基準)。「モジュール入りのバックテストが勝った」
  は採用根拠になりません。

## 3.5 API 状態(取引所の劣化への備え)

2019年の失敗は「シグナルが外れた」ではなく「相場が動いた瞬間に bitFlyer が重く
なり、注文が通らず、建玉を降ろせなかった」でした。BOT はその劣化を**測って**
振る舞いを変えます。

### API状態タイル(ダッシュボード)

Bot コンソール(http://127.0.0.1:8300)のタイル列に **API状態** が出ます。

```
API状態
DEGRADED   p95 1840ms / VERY BUSY
```

- 左: `NORMAL` / `DEGRADED` / `CRITICAL` — BOT 自身の判定。**DEGRADED 以上は赤**
- `p95`: 直近15分の自分のAPI呼び出しレイテンシ95パーセンタイル
- 右端: `/v1/gethealth` の生の文字列(`NORMAL` / `BUSY` / `VERY BUSY` /
  `SUPER BUSY` / `STOP`)。**ポーリング3回分(既定90秒)更新が無いと失効**し、
  `健全度不明(◯秒前)` と表示され、判定からも外れます(古い1回の読み取りが
  いつまでも BOT を CRITICAL に縛るのを防ぐため)
- **`STOP` だけは失効しません(sticky)。** TTL のトレードオフは両側にあります:
  失効させないと古い1回の読み取りが BOT を縛り続け、失効させると
  「取引所が止まっていた、以後の消息は不明」という状態で**新規エントリーが
  再開**してしまいます。BUSY 系は「今の混み具合」の話なので失効させ、
  `STOP` は「止まっていた」という別種の事実なので、**新しい非STOPの読み取りが
  1回入るまで**エントリー抑止を続けます(それを解除するはずのポーリング自体が
  失敗している状況だからです)。抑止されるのは**新規のみ**で、決済は
  この判定を一切通りません
- `⚠️停止中の記録` が付いていたら、それは**動いている BOT の値ではなく**
  `logs/status.json` が古い(BOT停止/ハング)ため CSV 最終行を出しています

判定は「gethealth の状態(失効していなければ)」「自分の呼び出しレイテンシの
EWMA」「直近のエラー率」の3つから決まります。**悪化は即座、回復はゆっくり**
(現在より落ち着いたサンプルが数回連続し、かつ最低滞在時間を超えてから、
**その中で最も悪いレベル**まで下がる)。gethealth が BUSY と NORMAL を交互に
返し続けるような場合は DEGRADED で止まります — それが実態だからです。

### 各レベルでの挙動

| レベル | 新規エントリー | 決済(利確・損切・CLOSE) | read タイムアウト | データ鮮度しきい値 |
|---|---|---|---|---|
| NORMAL | 通常 | 通す | 設定値(既定10秒) | 設定値(既定60秒) |
| DEGRADED | 通常(既定)/ `entry_gating: true` なら**頻度半分** | 通す | ×2 | ×2 |
| CRITICAL | 通常(既定)/ `entry_gating: true` なら**全面停止** | 通す | ×3 | ×3 |
| gethealth=STOP | **常に全面停止**(フラグと無関係。失効しない) | 通す | — | — |

**エントリー抑止は既定 OFF です**(`config/config.yaml: resilience.entry_gating:
false`)。エントリー頻度を変えることは champion の**戦略変更**であり、
稼働中のペーパー標本に事前登録なしで混ぜてはいけません
(`.claude/skills/research-protocol`)。有効化するときは事前登録してから。
`gethealth=STOP` だけは常時有効です — 取引所が止まっている以上、注文は
成立しないので、これは戦略の判断ではありません。

**決済はどのレベルでも必ず通します。** 劣化でエントリーを絞るのはリスクを
減らす方向だけで、建玉を降ろせなくなる方向には一切働きません(pre_trade_checks
の `increases_exposure` と同じ考え方。`tests/test_resilience.py` が
CRITICAL 中の決済成功を明示的に検査しています)。connect タイムアウトは
広げません — 3秒で繋がらない接続は待っても注文を運びません。

**決済は自分の帳簿にも塞がれません。** 二重注文防止は「同じ商品に未終端の注文が
あれば新規作成を拒否する」規則ですが、これが**決済**に効いてしまうと、原因が
取引所ではなく自分側だというだけで「建玉を降ろせない」という2019年と同じ結末に
なります。そこで:

- ループは LIVE の未終端注文を**30秒に1回まで**、診断用タイムアウトで
  洗い直します(`event=order_sweep_failed` は best-effort の失敗で、
  失敗しても帳簿は一切変わりません)。約定済み・取消済みの注文が
  `SUBMITTED` のまま居座って次の注文を塞ぐ状態を、そもそも作らないためです
- それでも決済が塞がれたら、**板に残っている注文を取り消してから決済を1回だけ
  やり直します**(取消は冪等で、既に消えている注文を取り消しても何も起きません。
  `event=closing_order_priority`)
- 取り消しても決済が通らない/取消自体が曖昧に失敗した場合は、**黙って諦めません**:
  `🚨 CANNOT CLOSE POSITION` を urgent で送り、Kill Switch を `system_error` で
  発動します(`event=closing_order_blocked`)。ここから先は人間の持ち場です
- **決済のサイズは送信直前に取り直します。** 板を空けるための取消で確定した約定は
  その場で建玉に計上されるので、決済を決めた時点のサイズは**もう古い**からです。
  送るのは `min(要求サイズ, 現在の建玉)`、既にフラットなら**何も送りません**
  (`closing_size_reresolved` / `closing_already_satisfied`)。塞いでいた前回の決済が
  0.006 約定済みだったのに 0.01 をそのまま送ると、**逆方向に 0.006 の建玉が立ちます**
- **未解決レコードは決済を拒否しません。** `PENDING_SUBMIT` / `STATE_UNKNOWN` が
  残っていると**新規エントリー**は拒否されますが(帳簿が分からない状態で送らない)、
  決済は上の優先権ルートに回ります。取り消せない相手(acceptance id の無い
  `PENDING_SUBMIT`、`STATE_UNKNOWN`)なら上の loud path です — 黙った
  RuntimeError で逆指値が消えることはもうありません
- **リスク上限の決済免除は建玉の大きさまでです。** MAX_ORDER_SIZE /
  MAX_POSITION_SIZE / MAX_OPEN_ORDERS は「エクスポージャーを増やす注文」にだけ
  効きますが、増える分の判定は**建玉を超えた超過分**で行います
  (0.001 のロングに対する SELL 1.0 は、0.001 の決済と 0.999 の新規ショートです)
- **新規エントリーにこの優先権はありません。** 混雑や劣化でエントリーが飛ぶのは
  リスクを減らす方向なので、従来どおり単にスキップします

**照合ポーリングと gethealth ポーリングは、広げたタイムアウトを継承しません。**
診断用の固定値(connect 3秒 / read 5秒、リトライなし)で走ります。CRITICAL の
30秒 read を診断が継承すると、1回のポーリングで15秒の照合予算を食い潰し、
取引ループの1ステップがデータ鮮度の見張りより長く固まります。

### Kill Switch との関係(正直な契約)

**Kill Switch が発動している間は、決済注文も含めて全ての注文が拒否されます**
(`pre_trade_checks.py`: tripped なら無条件で reject)。これは意図的な設計です
——状態が分からなくなった BOT に取引を続けさせない——が、裏を返すと
**建玉が残ったまま発動したら、そこから先は人間の持ち場**という意味です。
そのため建玉があるときの Kill Switch 通知には、**建玉の中身と「手で閉じてくれ」
という指示**が入ります。

だからこそ「劣化そのもの」で Kill Switch が飛ばないようにしてあります:

- API連続エラーのカウンタは、**SAFE_RETRY に分類された失敗を数えません**
  (read タイムアウト / 429 / 読み取り系の 5xx。広げたタイムアウトで再送済み
  であり、本当に危ないのは「価格が古いこと」の方)。また DEGRADED 以上では
  **public エンドポイントの失敗も数えません**(それが劣化そのものだから)。
  カウンタが担当するのは、鍵の失効や署名エラーのような**確定的な拒否**です
- 「本当にデータが来ない」を捕まえるのは市場データ鮮度の見張りで、その
  しきい値は read タイムアウトと**同じ倍率**で伸びます(60秒 → ×2 / ×3)。
  自分で広げたタイムアウトが自分の見張りに追い抜かれることはありません

設定は `config/config.yaml` の `resilience:` ブロック(タイムアウト、リトライ
回数と予算、gethealth ポーリング間隔、しきい値、`entry_gating`)。
**値は起動時に検証されます** — 負値・ゼロ・しきい値の逆転(degraded ≧ critical)
は既定値に戻し、`event=resilience_config_invalid` で警告を出します。あわせて:

- `entry_gating` は**素の YAML bool のみ**を受け付けます。引用符付きの
  `"false"` は非空文字列なので `bool()` では**有効**になってしまう — YAML が
  誘発しがちな誤記で、しかも未登録の戦略変更が入る方向です。bool でない値は
  OFF に倒して警告します(`composite.yaml` の `enabled` と同じ方針)
- `reconcile_budget_sec` は **5〜60秒**の範囲で検証します。短すぎると
  `getchildorders` の列挙遅延を待ち切れず、長すぎると1回の送信で取引ループが
  1分止まります。範囲外は既定値(15秒)に戻します

### data/api_health.csv(生テレメトリ)

BOT の API 呼び出し1回につき1行、追記のみ:

```
ts,endpoint_class,endpoint,latency_ms,outcome,condition,health
1787320011.412,public,/v1/ticker,84.3,ok,NORMAL,NORMAL
```

- `endpoint_class`: `public` / `private_read` / `order`
- `outcome`: `ok` / `safe_retry` / `ambiguous` / `rejected`
- 4MB を超えると `api_health.csv.1` に退避して切り詰めます
- **書き込み失敗は握り潰します**。テレメトリが取引を止めることは絶対にありません

PAPER 稼働中に自宅PCから貯まるこのファイルが、LIVE のタイムアウトを
「勘」ではなく実測で決めるための材料です。分布を見るには:

```bash
python - <<'PY'
import csv, statistics
lat = [float(r["latency_ms"]) for r in csv.DictReader(open("data/api_health.csv"))]
lat.sort()
print(len(lat), "calls  p50", lat[len(lat)//2], " p95", lat[int(len(lat)*.95)],
      " max", lat[-1])
PY
```

### リトライの原則(破らない)

- **読み取り系**(ticker / executions / getchildorders など)は冪等なので、
  失敗したら指数バックオフ(フルジッター)で再送します
- **注文系**は、リクエスト本文が送信される**前**に失敗したことが証明できる場合
  **だけ**再送します。証明できるのは次の2つだけです:
  - `ConnectTimeout`(その試行の接続が確立していない = 1バイトも書いていない)
  - 接続エラーの文面が新規接続の失敗を名指ししているもの。判定に使う文字列は
    コードの `_PRE_SEND_MARKERS` の**3つだけ**です
    (`failed to establish a new connection` / `name or service not known` /
    `nodename nor servname`)
- **TLS/SSL エラーは、たとえハンドシェイク由来に見えても再送しません。**
  OpenSSL のアラートは小文字で出る(`tlsv1 alert internal error` /
  `sslv3 alert bad record mac`)うえ、**本文送信後**に取引所側の LB から
  飛んでくることがあります。文字列でハンドシェイク中と送信後を区別する手段は
  ありません
- **`ProxyError` も再送しません。** urllib3 1.26 はプロキシ設定下だと
  「送信後のリセット」まで ProxyError に包みます(`pyproject.toml` は
  urllib3>=2 を固定していますが、分類はその固定に依存しません)
- 送信後に失敗したもの(read タイムアウト、送信後の切断、注文系の 5xx)は
  **曖昧**として扱い、**絶対に再送しません**
- **HTTP 200 でも、本文が約束どおりでなければ「成功」ではありません。**
  `sendchildorder` の 2xx は「受付IDを含むJSON」のはずで、そうでないもの
  (メンテナンス用のHTMLページ、空ボディ、途中で切れたJSON、IDの無いオブジェクト)
  は注文系では**曖昧**として `STATE_UNKNOWN` に落とします。以前はここだけが
  分類の外にあり、`resp.json()` の ValueError が注文マネージャの
  「取引所が明確に拒否した」経路に入って**レコードを REJECTED で閉じて**
  いました — 次のシグナルが2本目の実注文を出す経路です。
  読み取り系では同じ失敗は単なる再取得(SAFE_RETRY)です。
  `cancelchildorder` は仕様上 200 + 空ボディを返すので、それは正常です

### STATE_UNKNOWN と自動照合(積極的証拠のみ)

曖昧な失敗が起きると、BOT はまず**読み取り専用**の自動照合を試みます。
確定の根拠になるのは**「取引所がその注文を実際に列挙したこと」だけ**です:

- **こちらが知らない `child_order_acceptance_id`** が、
  同じ商品・同じ売買方向・同じサイズ(指値なら価格も一致)で現れたら、
  `getchildorders` が言うとおりの状態(約定 / 板に残っている / 取消 / 拒否)を
  書き込みます。**約定サイズも約定価格もその記録から取ります**
  (判断時の気配値からは絶対に作りません)
- 予算(既定15秒)は 0.5 / 1 / 2 / 4 / 8 / 15 秒の**予算いっぱいまで**
  ポーリングします。`getchildorders` は新しい受付を数秒遅れて載せることが
  あるためです(初回だけは予算が長くても**2秒**を上限にします — すぐ列挙される
  注文を待たせないため)
- **「見つからなかった」は何の確定にもなりません。** 以前は数回きれいに空振り
  したら「そもそも出ていなかった」として注文レコードを閉じていましたが、
  それは取引所に生きた建玉があるのに BOT の帳簿がフラットになる経路です。
  現在この結末は存在しません

前提: **この口座はこの BOT だけが売買する**(単一書き手)。照合中に人間や別の
BOT が同じ口座で「商品・方向・サイズ・価格まで一致する」注文を出すと、それを
こちらの注文と誤認します。一致しないものは全て無視され、その場合は
`STATE_UNKNOWN` のまま残る(安全側)ので、LIVE 口座に2人目の書き手を入れる
ときはこの規則から見直してください。

この照合は `QueryOnlyExchange`(送信メソッドを一切持たないオブジェクト)経由
なので、**構造上、注文を出すことができません**。

**列挙されないまま15秒が過ぎたら**(=積極的証拠なし)、従来どおり:

1. 注文は `STATE_UNKNOWN` のまま(**再送しません**)
2. Kill Switch が `order_state_unknown` で発動
3. Discord に `🚨 ORDER STATE UNKNOWN` が飛びます

このアラートが来たら、オペレーターがやることは:

1. bitFlyer の画面か `getchildorders` で、その注文が実在するか確認する
2. 建玉が意図と合っているか確認する(合っていなければ**手で**解消する)
3. 原因を `logs/bot.jsonl`(`event=order_state_unknown`)で確認する
4. そのうえで Kill Switch を `reset(operator_confirm=True)` で解除する

手作業の照合(`OrderManager.reconcile_unknown`)も**同じ規則**です:
lookup が `None` を返した(=照会が空だった)場合や、状態が `UNKNOWN` /
未知の文字列だった場合は、**レコードは `STATE_UNKNOWN` のまま**です。
確定するのは取引所が実際に答えた状態(`ACTIVE` / `COMPLETED` / `CANCELED` /
`EXPIRED` / `REJECTED`)だけで、返り値には**確定したものだけ**が入ります。

**BOT に判断させないでください。** ここは人間の持ち場です。
Kill Switch が発動している間は**決済も含めて全注文が拒否される**ので、
建玉を残したくないなら 2. を BOT に任せず自分で閉じてください
(通知本文にも建玉と手仕舞い指示が入ります)。

## 4. Discord 通知(任意)

1. Discord サーバー設定 → 連携サービス → Webhook を作成し URL をコピー
2. `.env` に `DISCORD_WEBHOOK_URL=...` を設定して BOT を再起動

通知内容: BOT起動/停止、Kill Switch 発動、1時間毎のステータスレポート。

## 4.5 更新手順(重要)

### 推奨: `deploy\restart_all.bat` をダブルクリック(Windows)

更新〜再起動の4手順を1回のダブルクリックで実行する。

| | 手順 | 失敗したら |
|---|---|---|
| [1/4] | `git pull` | **中断**。何も停止しない(BOTは旧コードのまま稼働継続) |
| [2/4] | `.venv\Scripts\pip install -e ".[dev]"` | **中断**。同上 |
| [3/4] | `deploy\stop_all.bat` | 中断(タスクマネージャで python.exe を確認) |
| [4/4] | `deploy\start_all.bat` | 中断(コンポーネントは停止状態) |

各手順の成否を `[n/4] ... ok` で表示し、**失敗した時点で以降を実行しない**。
pull がコンフリクトした・pip が落ちたのに再起動してしまうと、
「新コードなのに依存が無い」半端な状態で起動することになるため、
中断してBOTを旧コードのまま走らせ続ける方が安全という設計。
出力はASCIIのみ(コンソールはcp932。日本語を出すと文字化けする)。

### 手動でやる場合

コード更新は必ず**2点セット**で行うこと:

```powershell
git pull
.venv\Scripts\pip install -e ".[dev]"   # 新しい依存ライブラリを取り込む(Linuxは .venv/bin/pip)
```

`git pull` だけでは新規追加されたライブラリが入らず、該当コンポーネントが
起動直後にクラッシュする(例: websockets 追加時の板記録・スキャルパー)。

### 旧 `data/orders.sqlite3` を引き継ぐ時の注意(1回だけ)

注文帳簿に `booked_size`(portfolio に計上済みの数量)列が追加されました。列が無い
古いファイルは起動時に自動で移行されますが、その際 **既存の約定はすべて「計上済み」
として書き込まれます**(`booked_size = filled_size`)。方向は意図的です:
計上漏れは「実建玉があるのに BOT はフラットのつもり」で済みますが、二重計上は
**実建玉を倍にする**ためです。裏を返すと、旧コードで計上されないまま残っていた約定は
この移行で切り捨てられます。

したがって LIVE 機を更新した直後は、**1回だけ手で建玉を突き合わせてください**
(bitFlyer の建玉画面 と `logs/status.json` の `position_size`)。LIVE は起動時に
`getpositions` で取引所側を正として取り込むので(§3 の「LIVE 起動時の建玉照合」)、
ズレていれば起動ログの `live_boot_position_adopted` 行にそのまま出ます。

## 5. Windows PC で動かす場合

並走する2コンポーネント(メインBOT / 板記録)は
**`deploy\start_all.bat` が一括起動**します。起動済みのものは自動でスキップされる
(冪等)ため、同じバッチが**ウォッチドッグ**(落ちたプロセスの自動復旧)を兼ねます。
安全停止は再起動に勝ちます: Kill Switch発動中のメインBOTは取引しません。
バーストスキャルパーは2026-08-21にペーパー正式判定(第16報)で棄却され**退役**しました
(スクリプトは `scripts\run_scalp_paper.py` に保存。復帰は start_all.bat に1行戻すだけ)。

タスクスケジューラ登録(2タスクのみ):

| タスク名 | トリガー | 操作(プログラム。引数・開始は空欄) |
|---|---|---|
| bitflyer-start-all | ログオン時 + **1時間ごとに繰り返し(無期限)** | `<repo>\deploy\start_all.bat` |
| bitflyer-fetch | ログオン時 + **15分ごとに繰り返し(無期限)** | `<repo>\deploy\fetch_all.bat` |

手動操作: 一括起動 `deploy\start_all.bat` / 一括停止 `deploy\stop_all.bat` /
更新して再起動 `deploy\restart_all.bat`(§4.5。pull + pip install + 停止 + 起動) /
緊急停止はリポジトリ直下に `KILL` ファイル作成(メインBOT・スキャルパー両方が停止)。

ログ: `logs\run_paper.out.log`(メイン)/ `logs\recorder.out.log`(板記録)。

常時稼働の信頼性は Linux + systemd の方が高いため、Raspberry Pi 等があればそちらを推奨します。

## 6. Claude Code(この開発環境)側のネットワーク許可

開発セッションから bitFlyer API に接続してバックテスト等を行う場合(ユーザー自身で設定):

1. claude.ai/code → メッセージ入力欄の上の雲アイコン → 環境の歯車
2. Network access を **Custom** にし、Allowed domains に
   `api.bitflyer.com` と `lightning.bitflyer.com` を1行ずつ追加
3. **「Also include default list of common package managers」にチェック**(pip用)
4. 保存後、**新しいセッション**から有効

注意: この環境は一時VMのため、`data/` に貯めたデータはセッション終了で消えます。継続的なデータ蓄積は自宅マシン側で行ってください。

## 6.5 ログを Claude に見せる手順

**簡易(コピペ、数十秒)** — 自宅PCのリポジトリで:

```
.venv\Scripts\activate
set PYTHONPATH=src
python scripts\judge_gates.py
```

出力(全係属ゲートの判定表)をそのままチャットに貼り付ける。

**完全共有(生ログを Claude が直接分析)** — `deploy\share_logs.bat` をダブルクリック。
`logs\bot.jsonl`・`data\scalp_paper.jsonl`・`status.json`・`oi_snapshots.csv`・スプレッド記録・
オーバーレイ状態を `paper_logs\` にコピーしてコミット・プッシュする(板WS記録は巨大なため一覧のみ)。
完了したらチャットで「ログを上げました」と伝えるだけでよい。
初回はgitのプッシュ認証(GitHubログイン)を求められることがある。
Claude 側は `paper_logs/` の各ファイルを `logs/`・`data/` の定位置にコピーしてから
`judge_gates.py`・各研究スクリプトを実行する。

## 7. 次フェーズのチェックリスト

- [ ] `check_api.py` 成功(認証OK・出金権限なし・最低注文数量と手数料率の実測)
- [ ] 実測した最低注文数量で対象銘柄を確定(6,000円で発注可能なこと)
- [ ] `fetch_history.py` を1〜2週間以上稼働させ1分足を蓄積
- [ ] `run_backtest.py` で3戦略を Training/Validation/OOS 評価 → 結果をオーナーに報告
- [ ] コスト込み期待値がプラスの戦略が存在する場合のみ、ペーパートレードを1週間以上実施
- [ ] ペーパー結果をオーナーに報告 → **オーナーの明示承認があって初めて**少額実運用を検討

バックテスト・ペーパーの結果が悪ければ、その事実をそのまま報告し実運用へは進みません。
