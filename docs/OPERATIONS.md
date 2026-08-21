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

重要: Kill Switch はファイルに永続化されるため、**systemd がプロセスを再起動しても取引は再開しません**。解除は必ず原因(status.json / bot.jsonl / kill_switch.json)を確認してから行ってください。

`kill_switch.json` の `reason` は `daily_loss_limit` / `max_drawdown` /
`consecutive_losses` / `api_errors` / `order_state_unknown` /
`market_data_anomaly` / `system_error` / `unhandled_exception` / `manual` の
いずれかです。

- `unhandled_exception` — 取引ループ内で想定外の例外が出たことを示します。状態不明
  とみなしてプロセスが落ちる前に発動するため(`detail` に例外の repr)、再起動しても
  取引は再開しません。解除手順は他の理由と同じで、原因調査後に上の
  `reset(operator_confirm=True)` を人間が実行します。

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

## 4. Discord 通知(任意)

1. Discord サーバー設定 → 連携サービス → Webhook を作成し URL をコピー
2. `.env` に `DISCORD_WEBHOOK_URL=...` を設定して BOT を再起動

通知内容: BOT起動/停止、Kill Switch 発動、1時間毎のステータスレポート。

## 4.5 更新手順(重要)

コード更新は必ず**2点セット**で行うこと:

```powershell
git pull
.venv\Scripts\pip install -e ".[dev]"   # 新しい依存ライブラリを取り込む(Linuxは .venv/bin/pip)
```

`git pull` だけでは新規追加されたライブラリが入らず、該当コンポーネントが
起動直後にクラッシュする(例: websockets 追加時の板記録・スキャルパー)。

## 5. Windows PC で動かす場合

並走する3コンポーネント(メインBOT / バーストスキャルパー / 板記録)は
**`deploy\start_all.bat` が一括起動**します。起動済みのものは自動でスキップされる
(冪等)ため、同じバッチが**ウォッチドッグ**(落ちたプロセスの自動復旧)を兼ねます。
安全停止は再起動に勝ちます: Kill Switch発動中のメインBOTは取引せず、日次損失上限に
達したスキャルパーは当日中の再開を拒否します(`data\scalp_stopped_YYYYMMDD`)。

タスクスケジューラ登録(2タスクのみ):

| タスク名 | トリガー | 操作(プログラム。引数・開始は空欄) |
|---|---|---|
| bitflyer-start-all | ログオン時 + **1時間ごとに繰り返し(無期限)** | `<repo>\deploy\start_all.bat` |
| bitflyer-fetch | ログオン時 + **15分ごとに繰り返し(無期限)** | `<repo>\deploy\fetch_all.bat` |

手動操作: 一括起動 `deploy\start_all.bat` / 一括停止 `deploy\stop_all.bat` /
緊急停止はリポジトリ直下に `KILL` ファイル作成(メインBOT・スキャルパー両方が停止)。

ログ: `logs\run_paper.out.log`(メイン)/ `logs\scalp.out.log`(スキャル)/
`logs\recorder.out.log`(板記録)/ `data\scalp_paper.jsonl`(スキャル全取引)。

常時稼働の信頼性は Linux + systemd の方が高いため、Raspberry Pi 等があればそちらを推奨します。

## 6. Claude Code(この開発環境)側のネットワーク許可

開発セッションから bitFlyer API に接続してバックテスト等を行う場合(ユーザー自身で設定):

1. claude.ai/code → メッセージ入力欄の上の雲アイコン → 環境の歯車
2. Network access を **Custom** にし、Allowed domains に
   `api.bitflyer.com` と `lightning.bitflyer.com` を1行ずつ追加
3. **「Also include default list of common package managers」にチェック**(pip用)
4. 保存後、**新しいセッション**から有効

注意: この環境は一時VMのため、`data/` に貯めたデータはセッション終了で消えます。継続的なデータ蓄積は自宅マシン側で行ってください。

## 7. 次フェーズのチェックリスト

- [ ] `check_api.py` 成功(認証OK・出金権限なし・最低注文数量と手数料率の実測)
- [ ] 実測した最低注文数量で対象銘柄を確定(6,000円で発注可能なこと)
- [ ] `fetch_history.py` を1〜2週間以上稼働させ1分足を蓄積
- [ ] `run_backtest.py` で3戦略を Training/Validation/OOS 評価 → 結果をオーナーに報告
- [ ] コスト込み期待値がプラスの戦略が存在する場合のみ、ペーパートレードを1週間以上実施
- [ ] ペーパー結果をオーナーに報告 → **オーナーの明示承認があって初めて**少額実運用を検討

バックテスト・ペーパーの結果が悪ければ、その事実をそのまま報告し実運用へは進みません。
