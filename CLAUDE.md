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
- `src/bot/exchange/` — bitFlyer REST クライアント(`OrderStateUnknown` の発生源)+ `resilience.py`(失敗分類 SAFE_RETRY/AMBIGUOUS/REJECTED・リトライ方針・分割タイムアウト・取引所コンディション監視・API テレメトリ)
- `src/bot/market_data/` — bitFlyer feed / Binance 外部 feed / Realtime WS
- `src/bot/strategy/` — 戦略群(実装は残っているが、どれも**現時点では未検証**。2026-09-08 の全捨てで過去の判定は失効)。`composite.py` は同一コア信号+フェイルクローズなモジュール枠(全 OFF)+新規建玉のリスクオーバーレイ
- `src/bot/risk/` — kill switch・発注前チェック
- `src/bot/order_management/` `execution/` `portfolio/` — 注文永続化・PAPER/LIVE 執行・建玉。`reconciler.py` は曖昧失敗の**読み取り専用**自動照合(時間予算付き。送信メソッドを持たない `QueryOnlyExchange` 経由なので構造上発注できない)
- `src/bot/backtest/` — エンジン(maker執行 / TP・SL / max_hold / 決済理由記録)・指標・walk-forward
- `src/bot/monitoring/` — status.json・Discord 通知・ダッシュボード集約(`gates.py` は係属ゲートの事前登録バー(judge_gates と共有)と進捗/ETA、`decision_text.py` は判断ログの日本語ラベル)
- `src/bot/jpx/` — JPX(大阪取引所)側。kabuステーションAPI クライアント(`kabu_client.py`。発注系の曖昧失敗 = `OrderStateUnknown`・自動リトライなし)+ ON1 状態機械(`on1_executor.py`。建玉∈{0,+1}・1日4発注・発注前サニティ・二重ゲート・読み取り専用 reconcile)+ 二重起動ガード(`run_lock.py`)。`config/on1_live.yaml` 既定 `enabled: false` = dry-run
- `src/bot/radar.py` — ストームレーダー(時計窓)、`src/bot/research/board.py` — 板再構成
- `scripts/` — `run_*`(BOT・スキャルパー・バックテスト)/ `fetch_*`・`record_*`(収集)/ `build_*`(イベントライブラリ)/ `research_*`・`replay_*`(研究)/ `validate_composite.py`(composite の再現ゲート)/ `judge_gates.py`(係属ゲートの一括判定)/ `dashboard.py` / `check_api.py` / `run_on1_entry.py`・`run_on1_exit.py`(ON1実弾ジョブ)・`run_on1_reconcile.py`(読み取り専用・人間が実行)
- `deploy/` — Windows bat(`start_all` / `stop_all` / `restart_all`(pull+install+再起動) / `fetch_all`、タスクスケジューラ登録)+ ON1 用 `on1_entry.bat`・`on1_exit.bat`(平日15:35 / 8:35)+ systemd unit
- `config/` — `config.yaml`(戦略・コスト)/ `products.yaml`(商品仕様)/ `risk_limits.yaml`(ハード上限)/ `composite.yaml`(composite のコア params・モジュールゲート)/ `on1_live.yaml`(ON1 実弾ゲート・ポート・時間窓)
- `data/` — gitignore 済。**bitFlyer 公開約定履歴は31日で消える**ため長期保存先にはならない
- `backtest_data/` — 恒久スナップショット(再現用。31日制限の回避先)
- `docs/` — 運用手順・データ台帳・戦略案(`STRATEGY_IDEAS.md`)・消費台帳(`DATA_CONSUMPTION_LOG.md`)・議論記録

## 3. 運用の要点

- テスト: `PYTHONPATH=src python -m pytest -q`(現在 1,739 件。2026-09-10 実測)
- **`git pull` 後は必ず `pip install -e ".[dev]"`**。依存追加を取り込まないとコンポーネントが起動直後に落ちる → 詳細 `docs/OPERATIONS.md` §4.5(Windows は `deploy\restart_all.bat` が pull→install→停止→起動を失敗時中断つきで実行)
- Windows 運用(3プロセス並走・ウォッチドッグ・タスクスケジューラ2件)→ `docs/OPERATIONS.md` §5。ON1 実弾ジョブ(平日15:35/8:35の2タスク・二重ゲート・STATE_UNKNOWN 復帰手順)→ §5.1
- 緊急停止: リポジトリ直下に `KILL` ファイルを作成
- ダッシュボード: http://127.0.0.1:8300

## 4. プロジェクト体制

リード(仮説設計・判定基準の事前登録・結果審査)+ 下位モデルへの委任(データ収集・研究実装・実行)。
手順は `.claude/skills/delegated-study` を参照。

## 5. 研究の規律

新戦略とパラメータチューニングは**すべて** `.claude/skills/research-protocol` に従う(実行前の事前登録、検出力の事前計算、Train+Val のみで選択 → OOS は一度だけ、フレッシュデータ追試)。

### 5.1 全捨て(2026-09-08、オーナー決定。**これを破ると同じ失敗に戻る**)

**過去の検証結果・分析結果はすべて破棄した。** 相場についての主張を含む文書(KNOWLEDGE 系・全研究報告・
全事前登録・全監査・トリアージ・週次要約)は削除済みで、git 履歴にしか残っていない。
経緯と理由: `docs/DISCUSSIONS/2026-09-08_matilda_intent_vs_test.md`。

- **git 履歴から過去の結論を掘り起こして根拠に使ってはならない。** 参考に読むこともしない。
- **「既に棄却済み」と書いてはならない。** 構成要素を族から外すなら「本単位では測らない」と書く。
- 引用してよい過去の数値は**ひとつも無い**。コスト・スプレッド・逆選択・約定率は単位ごとに測り直す
  (`config/constants.yaml` の `status: discarded_2026-09-08` が付いた定数も同じ)。
- 生き残ったのは: データ、コード、手順、事故の記録、会話の記録、
  `docs/STRATEGY_IDEAS.md`(判定なしの案)、`docs/DATA_CONSUMPTION_LOG.md`(何を見たかの履歴)。

### 5.2 なぜ捨てたか(繰り返さないために)

規律(事前登録・封印・盲検監査・帰無・多重性)は**すべて偽陽性を防ぐため**に作られ、
**偽陰性を防ぐ機構が一つも無かった**。保守的な前提は誰にも攻撃されず、誤差が片方向にだけ蓄積し、
その蓄積が「確立済み知識」として次の研究の入口に置かれていた。だから:

- **陰性と不明を分ける。** 陰性 = 検出できる検出力で不在を測った。不明 = 検出力が足りなかった。
  **MDE を書けない主張は陰性として扱わない。** 事前登録に MDE を書き、欲しい効果 < MDE なら実行しない。
- **棄却方向に効く前提にも一次資料か実測を要求する。** 事前登録の前提表にバイアスの向きを明記する。
- **棄却には射程を書く。** 何を測ったかと、**何を測っていないか**を併記する。
- **測る前に、意図と実装を突き合わせる(2026-09-09 オーナー規定、L-043)。** 結果が悪いとき
  原因は「機構にエッジが無い / 機構の構築が戦略意図を反映していない / 機構のバグ」の 3 つ。
  **検証を進めてからでは分離できない**(どんな陰性も実装のせいにできてしまう)ので、
  後の 2 つは**測る前に潰す**。成果物は `INTENT_MAP.md`(意図 1 項ずつ × 実装 ×
  ○/△代理/✕未実装/＋意図に無い実装)。**無ければ事前登録を書かない。**
  △ や ✕ が残ったまま出た陰性は**陰性ではなく不明**。手順は
  `.claude/skills/research-protocol` §0.5、手本は `docs/legacy/KATSUO_INTENT_MAP.md`。
- **判定は出口ではない(2026-09-08 オーナー規定、L-020)。** 研究の既定の形は
  **「案 → 検証 → なぜそうなるのかの理解 → 改良 → 再検証」**のループであり、判定は途中経過である。
  **「なぜ」を出さずに棄却だけ返す報告は不合格 = 差し戻す。**
  ループが総当たりに堕落しないための線引き(改良は「なぜ」から導かれること、1 周 1 機構仮説、
  周回数は多重性に算入、判定は設計ごとに一度だけ、収束しなければ止めて理解できていないと報告)は
  `.claude/skills/research-protocol` §0。

### 5.3 進め方(オーナー指示 2026-09-08)

オーナーの案とリードの案を**片っ端から**検証し、知見を深め、最強の戦略へブラッシュアップする。
市場の順序は **暗号資産 → FX → 株**。案の一覧は `docs/STRATEGY_IDEAS.md`(優先順位は書かない)。

## 6. コミット規約

- 実測に基づく簡潔な英語メッセージ(何を測り、何が変わったか)
- モデル名(Claude / Opus 等)をコードにもコミットメッセージにも書かない

## 7. オーナー報告の記録義務(インシデント I-001 の再発防止)

- オーナーが状態・決定・完了を伝えたら、**その回のうちに** `docs/OWNER_LOG.md` に追記し `docs/OWNER_STATUS.md` を更新してコミットする。他の作業より先。
- オーナーに手順を指示する前に **必ず** `docs/OWNER_STATUS.md` を読む。指示は `docs/OWNER_PROCEDURES.md` の手順番号で出し、時刻は日本時間 hh:mm と曜日を明記する。
- 呼び出し: `/owner-procedure <P番号>`(`.claude/skills/owner-procedure`)。
- 文脈の要約(コンパクション)で会話が失われても、この 3 ファイルが真実。会話だけに残した指示は「無かったこと」とみなす。

## 8. 委任モデル(オーナー承認 2026-09-06、`docs/DELEGATION.md`)

- 判定の**実行**は規則で自動。ただし**枠組み(問いの立て方・族の切り方・何を検定単位にするか)はオーナーに見せてから進める** — 2026-09-08 の全捨てで、計算ではなく枠組みの誤りが最も高くついたと判明したため。オーナーが決めるのは取り返しのつかないこと(実弾・口座・資本・新市場・リスク上限)と、この枠組み。
- **問いを変えない規則**: 委任の範囲外に出たくなったら止まり、週次要約の「判断が要る項目」に載せる(最大 3 件、yes/no)。
- 報告の各主張に 事実 / 推定 / 仮定 の印を付ける。否定的事実は `docs/NEGATIVE_FACTS.md` に賞味期限つきで登録する。
- 単位の着手前に調達票とリード盲点監査。
- 議論の記録は `docs/DISCUSSIONS/` に保管し、資源として扱う。
