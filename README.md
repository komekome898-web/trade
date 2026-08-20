# bitFlyer 自動売買システム

ルールベース戦略 + 厳格なリスク管理で bitFlyer の自動売買を行うボット。
**デフォルトは PAPER MODE(仮想売買)であり、実注文は二重の明示設定がない限り送信されない。**

## 安全設計(最重要)

- **PAPER MODE がデフォルト**。`PaperExecutor` は実注文APIを呼ばない(実注文モジュールを import すらしない)。
- **LIVE MODE の有効化には二重の明示が必要**:
  1. 環境変数 `LIVE_MODE=true`(かつ `PAPER_MODE` が true でないこと)
  2. `config/config.yaml` に `live_mode_ack: "I_UNDERSTAND_REAL_MONEY"`
  どちらか欠けると起動を拒否する(`bot/settings.py: resolve_mode`)。
- **Kill Switch**(`bot/risk/kill_switch.py`): 日次損失上限 / 最大DD / 連敗 / API連続エラー / 注文状態不明 / 市場データ異常 / 手動(`KILL` ファイル設置)で発動。状態はファイルに永続化され、**プロセス再起動でも自動再開しない**。人間による `reset(operator_confirm=True)` が必要。
- **発注前チェック**(`bot/risk/pre_trade_checks.py`): 残高・ポジション・未約定・数量・価格・想定損失・各上限をすべて確認、1つでも不合格なら拒否。
- **二重注文防止**(`bot/order_management/`): 送信前にSQLiteへ永続化 → 送信 → 通信曖昧失敗時は `STATE_UNKNOWN` とし Kill Switch 発動。照会(`reconcile_unknown`)で状態確定するまで再送しない。
- **Secret管理**: APIキーは `.env` のみ(gitignore済)。ログは全行 redaction フィルタ通過。`Secret` 型は str()/repr() でマスク。出金権限付きキーは LIVE 起動を拒否。

## セットアップ

```bash
pip install -e ".[dev]"
cp .env.example .env   # APIキーを記入(参照+取引のみ。出金権限は付けない)
```

## 使い方

```bash
python scripts/check_api.py      # API疎通・認証・権限確認(read-only、注文なし)
python scripts/fetch_history.py  # 約定履歴の蓄積と1分足生成(定期実行推奨)
python scripts/run_backtest.py   # 全戦略を Training/Validation/OOS で評価
python scripts/run_paper.py      # ペーパートレード開始(強制PAPER)
python -m pytest                 # テスト(実APIには一切接続しない)
```

緊急停止: 作業ディレクトリに `KILL` という名前のファイルを作成する。

## モジュール構成

| ディレクトリ | 役割 |
|---|---|
| `src/bot/exchange/` | bitFlyer RESTクライアント(認証・レート制限・リトライ) |
| `src/bot/market_data/` | ティッカー取得・1分足生成・異常/鮮度検知 |
| `src/bot/strategy/` | 売買判断のみ(EMAクロス / RSI回帰 / ブレイクアウト)。注文APIを知らない |
| `src/bot/indicators/` | 因果的(look-aheadなし)テクニカル指標 |
| `src/bot/risk/` | 発注前チェック・上限・Kill Switch |
| `src/bot/order_management/` | 注文状態機械・SQLite永続化・重複防止・照会 |
| `src/bot/execution/` | `ExecutionGateway` 抽象 + Paper / Live 実装(完全分離) |
| `src/bot/portfolio/` | ポジション・損益・DD・連敗管理 |
| `src/bot/backtest/` | コスト込みエンジン・全指標・Walk-forward分割 |
| `src/bot/monitoring/` | status.json・Discord通知 |

## 運用フロー(厳守)

現状調査 → 要件 → 設計 → API接続確認 → データ取得 → バックテスト → ペーパートレード →
リスク管理テスト → **オーナー承認** → 少額実運用 → 安定確認 → 段階的増額

オーナーの明示的な「実運用を開始して」指示があるまで LIVE MODE は有効化しない。

## 注意

- API仕様は https://lightning.bitflyer.com/docs を正とする。`check_api.py` を接続可能な環境で実行し、最低注文数量・手数料を実測してから銘柄・サイズを確定すること。
- バックテスト成績が良いほど過学習を疑うこと。OOS(未使用期間)の結果のみを採用判断に使う。
- 本番24時間稼働は VPS + systemd を推奨(Claude Code のリモートコンテナは一時的であり不可)。
