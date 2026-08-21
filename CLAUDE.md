# CLAUDE.md

bitFlyer Crypto CFD(API商品コードは `FX_BTC_JPY` のまま)の自動売買BOT。PAPERで稼働中、LIVEは未承認。

## 1. 安全不変条件(破らない)

- **PAPERが既定**。LIVEには env `LIVE_MODE=true` と `config/config.yaml: live_mode_ack: "I_UNDERSTAND_REAL_MONEY"` の**両方**、さらに**オーナーの明示承認**が必要。欠ければ起動拒否(`src/bot/settings.py: resolve_mode`)
- 秘密情報をコード・ログ・コミットに書かない。APIキーは `.env` のみ(gitignore済)、`Secret` 型が str()/repr() でマスク、ログは全行 redaction フィルタ通過。出金権限付きキーは LIVE 起動を拒否
- **Kill Switch は自動復帰しない**。状態はファイルに永続化され、プロセス再起動でも取引は再開しない。解除は原因調査後に人間が `reset(operator_confirm=True)`
- `config/risk_limits.yaml` のリスク上限変更と、戦略の本番投入はオーナー承認制
- 注文系エンドポイントの曖昧な失敗は `OrderStateUnknown` → `STATE_UNKNOWN` として保持し **自動リトライしない**。`reconcile_unknown` で状態確定するまで再送禁止

## 2. 構成地図

- `src/bot/settings.py` — 設定読込・モード解決・`Secret`
- `src/bot/exchange/` — bitFlyer REST クライアント(`OrderStateUnknown` の発生源)
- `src/bot/market_data/` — bitFlyer feed / Binance 外部 feed / Realtime WS
- `src/bot/strategy/` — 戦略群(現行検証対象は `xborder_momentum`、他は棄却済みを含む)
- `src/bot/risk/` — kill switch・発注前チェック
- `src/bot/order_management/` `execution/` `portfolio/` — 注文永続化・PAPER/LIVE 執行・建玉
- `src/bot/backtest/` — エンジン(maker執行 / TP・SL / max_hold / 決済理由記録)・指標・walk-forward
- `src/bot/monitoring/` — status.json・Discord 通知
- `src/bot/radar.py` — ストームレーダー(時計窓)、`src/bot/research/board.py` — 板再構成
- `scripts/` — `run_*`(BOT・スキャルパー・バックテスト)/ `fetch_*`・`record_*`(収集)/ `build_*`(イベントライブラリ)/ `research_*`・`replay_*`(研究)/ `dashboard.py` / `check_api.py`
- `deploy/` — Windows bat(`start_all` / `stop_all` / `fetch_all`、タスクスケジューラ登録)+ systemd unit
- `config/` — `config.yaml`(戦略・コスト)/ `products.yaml`(商品仕様)/ `risk_limits.yaml`(ハード上限)
- `data/` — gitignore 済。**bitFlyer 公開約定履歴は31日で消える**ため長期保存先にはならない
- `backtest_data/` — 恒久スナップショット(再現用。31日制限の回避先)
- `docs/` — 運用手順・研究レポート b〜l・`KNOWLEDGE.md`

## 3. 運用の要点

- テスト: `PYTHONPATH=src python -m pytest -q`(現在222件)
- **`git pull` 後は必ず `pip install -e ".[dev]"`**。依存追加を取り込まないとコンポーネントが起動直後に落ちる → 詳細 `docs/OPERATIONS.md` §4.5
- Windows 運用(3プロセス並走・ウォッチドッグ・タスクスケジューラ2件)→ `docs/OPERATIONS.md` §5
- 緊急停止: リポジトリ直下に `KILL` ファイルを作成
- ダッシュボード: http://127.0.0.1:8300

## 4. プロジェクト体制

リード(仮説設計・判定基準の事前登録・結果審査)+ 下位モデルへの委任(データ収集・研究実装・実行)。
手順は `.claude/skills/delegated-study` を参照。

## 5. 研究の規律

新戦略とパラメータチューニングは**すべて** `.claude/skills/research-protocol` に従う(実行前の事前登録、Train+Val のみで選択 → OOS は一度だけ、フレッシュデータ追試)。
着手前に `docs/KNOWLEDGE.md` を読むこと — 確立済みの知識と棄却済み仮説の索引がある(同じ棄却を繰り返さない)。

## 6. コミット規約

- 実測に基づく簡潔な英語メッセージ(何を測り、何が変わったか)
- モデル名(Claude / Opus 等)をコードにもコミットメッセージにも書かない
