# オーナー側の手順書(呼び出し: `/owner-procedure <P番号>`。時刻はすべて**日本時間**、曜日は平日 = 月〜金の JPX 営業日)

前提: 手順を出す前にリードは `docs/OWNER_STATUS.md` を読み、済んだ段階は飛ばして指示する。

## P1 証券口座と kabuステーション API(板寄せ実約定測定の前提)
1. 三菱UFJ eスマート証券の総合口座 — **開設済み**(2026-09-06 時点)。
2. 入金: 約 10 万円(約定実績 1 回 + ETF 測定 3 銘柄 約 60,500 円 + 余裕)。先物の証拠金(1 枚 15〜20 万円)は先物口座ができてから。
3. 約定実績を作る 1 回: 現物で **1348.T(MAXIS TOPIX ETF)を 1 口**(約 4,300 円)、**SOR 指定**で買う(手数料 0 円)。
   平日の 日本時間 09:00〜15:30 のいつでも可。約定日・約定価格・当日の終値をメモしてリードに報告(測定の手動 1 件目として記録)。売却は急がない。
4. 先物・オプション口座を申請(約定実績ができてから)。
5. 承認後、kabuステーション(Windows)をインストールし、アプリ内から **API 利用申請**。API パスワードを自分で決める(Professional プランの条件 =
   先物OP または信用口座 + 直近の約定実績 1 回)。
6. `.env` に `KABU_API_PASSWORD=(決めたパスワード)` を追加。kabuステーションを起動し**検証環境**にログイン(API ポート 18081)。
7. リードに「P1 完了」と報告 → P2 へ。

## P2 板寄せ実約定測定の dry-run(何も送信しない)
前提: P1 完了、`config\etf_measure.yaml` は `enabled: false` のまま。
1. `restart_all.bat` を実行(pull と依存の更新)。
2. 平日 **日本時間 15:10〜15:24** に PowerShell で:
   ```
   cd C:\Users\ryoma\trade
   .venv\Scripts\activate
   set PYTHONPATH=src
   python scripts\run_etf_measure_entry.py
   ```
   期待: 1343・1591・1348 の「WOULD send …」。時間外は「outside the entry window」。
3. 翌平日 **日本時間 08:30〜08:50** に `python scripts\run_etf_measure_exit.py`(同様に「WOULD send …」)。
4. いつでも: `python scripts\run_etf_measure_reconcile.py`。
5. `logs\etf_measure.out.log` と `data\etf_measure\events.jsonl` をリードに送る(share_logs には含まれない)。
6. その後の段階(検証環境 18081 への模擬発注、タスクスケジューラ登録 平日 15:20 / 08:40、実弾)は別途リードが提示し、オーナー承認で進む。

## P3 225Labo のデータ取得
1. https://225labo.com にログイン → 「各種データ 無料ダウンロード」。
2. 必要なもの: 日経225先物(四半期ごとに更新版)、**TOPIX先物**、**ミニTOPIX先物**(P2-06 用、初回)。xlsx をそのまま共有(zip でも可)。
3. 利用条件: 本人利用のみ・第三者提供禁止 → リポジトリは非公開のまま。

## P4 PC 運用(依頼があった時のみ)
- `deploy\restart_all.bat`: pull → 依存更新 → 停止 → 起動。実行後に `share_logs.bat`。
- `deploy\share_logs.bat`: コピーのみ(数分)。フリーズしたら PowerShell を閉じてよい。
- `deploy\fetch_all.bat`: 日次取得(タスクスケジューラで自動)。
- 緊急停止: リポジトリ直下に `KILL` ファイルを作る(自動復帰しない)。
- **(2026-09-06、I-002 対応後)** この修正を取り込んだら(`restart_all.bat` の pull で反映)、一度
  `share_logs.bat` を実行すること。期待結果: `backtest_data\auto_*` を含むコミットが作られる
  (`git log` の直近コミットに `backtest_data/auto_...` のファイルが入っていれば OK)。それまで PC 上に
  作成済みだった保持期限スナップショットが、この 1 回でまとめて研究環境に届く。

## P5 報告の書き方(記録漏れ防止)
何かを完了・変更・決定したら、一言でよいので「P1-3 完了(1348 を 4,255 円で約定、9/10)」のように**手順番号付き**で伝える。
リードはその回のうちに `docs/OWNER_LOG.md` に追記し、`docs/OWNER_STATUS.md` を更新する。

## P6 share_logs の定期実行(1 回だけ登録。委任表 §2)
PowerShell(管理者不要)で 1 行。毎日 **日本時間 06:30**(取引の少ない時間帯)に `share_logs.bat` を実行:
```
schtasks /Create /TN "trade_share_logs" /TR "C:\Users\ryoma\trade\deploy\share_logs.bat" /SC DAILY /ST 06:30 /F
```
確認: `schtasks /Query /TN trade_share_logs`。以後、手動の share_logs は不要(依頼があった時だけ)。

## P7 PC の時計同期(P2-08b 秒スケール研究の前提。1 回設定 + 週 1 確認)
背景: 自宅 PC の時計は 0.44 秒以上遅れ、週内に 0.8 秒ずれた実測がある((削除済み文書) (ah))。秒スケールの WS 記録は取引所刻印と受信時刻の差を使うため、PC 時計の同期が前提。
1. 管理者の PowerShell で 1 回。**先に Windows Time サービスを起動する**(ドメイン未参加の PC では既定で停止しており、
   これを飛ばすと `w32tm /config` が **0x80070426「そのサービスを開始できませんでした」** で失敗する。2026-09-07 実例 L-013):
   ```
   Set-Service w32time -StartupType Automatic
   Start-Service w32time
   Get-Service w32time          # Status が Running なら次へ
   w32tm /config /manualpeerlist:"ntp.nict.jp,0x8" /syncfromflags:manual /update
   w32tm /resync
   ```
   `Start-Service` が「無効になっているため開始できません」と出る場合は、先に `sc.exe config w32time start= auto` を実行してから再度 `Start-Service w32time`。
   それでも駄目なら GUI で代用可: 設定 → 時刻と言語 → 日付と時刻 → 「今すぐ同期」(ボタンがサービスを起動する)。ただし恒久同期のため上のコマンドを後で通すこと。
2. 確認(いつでも可、平日・休日を問わない):
   ```
   w32tm /query /status
   ```
   「最終正常同期時刻」が直近であること、「位相オフセット」の絶対値が **0.1 秒未満**なら OK。0.1 秒以上なら手順 1 の `w32tm /resync` を再実行。
   `w32tm /stripchart /computer:ntp.nict.jp` は **IPv6 経路がタイムアウトして 0x800705B4 になることがある**(2026-09-07 実例 L-014。同期自体は IPv4 で成功している)。
   stripchart を使うなら IPv4 を明示する:
   ```
   Resolve-DnsName ntp.nict.jp -Type A | Select-Object -First 1 -ExpandProperty IPAddress
   w32tm /stripchart /computer:<表示された IPv4> /samples:3 /dataonly
   ```
3. 結果を「P7 確認 +0.01s(9/8)」のように一言で報告(手順番号付き、P5)。以後は週 1 回(任意の曜日)に手順 2 のみ。

## P8 清算(強制決済)ストリームの到達確認と記録開始(1 回。**急ぐ**)

**なぜ急ぐか**: 清算フローの履歴は**どこにも売っていないし、無料アーカイブも無い**。
記録を始めた日から先しか残らないので、**始めるまでの毎日が永久に空白**になる。
価格・建玉・資金調達は後から遡れるので急がない。急ぐのはこれだけ。
(背景: 旧 bot カツオの「ロスカットの連鎖が燃料を使い切る」という機構の直接観測。L-024 / L-025)

### 1. 到達確認(3〜5 分)

PowerShell をリポジトリのフォルダで開いて:

```
.venv\Scripts\python.exe scripts\check_liquidation_feeds.py
```

4 取引所(Binance / Bybit / OKX / BitMEX)に順に GET と WebSocket 接続を試し、
**清算メッセージが実際に来るか**を各 60 秒待つ。読み取り専用・認証なし・発注なし。
終わると `data\liquidation_feed_check.json` が出来るので、**画面の「まとめ」を貼るか、
このファイルを共有**してください。

> **「清算未発生」は「届かない」ではありません。** 清算は常時起きるものではないので、
> 接続できていれば記録に使えます。表示はその 2 つを区別しています。

### 2. 記録開始

`deploy\start_all.bat` に**常駐プロセスとして追加済み**なので、次に

```
deploy\restart_all.bat
```

を実行すれば動き出します(pull → install → 停止 → 起動)。
起動後、`logs\liquidations.out.log` に「接続」の行が出ていれば記録中です。

出力先は `data\liquidations\<取引所>_<日付>.jsonl.gz`。
`share_logs.bat` が毎日 06:30 に共有するので、こちらでも読めます。

### 3. 確認(1 回だけ、翌日)

```
dir data\liquidations
```

ファイルが日付ごとに増えていれば正常です。増えていなければ
`logs\liquidations.out.log` の最後の 20 行を共有してください。

## P9 清算履歴の集計サービスの API キー取得(2 件。**P8 より先**)

**なぜ先か**: 清算履歴の入手経路を全部当たった結果、取引所側で遡れるのは
**Gate.io の約 90 日**と **OKX の約 24 時間**だけでした(`docs/DATA_SOURCES/LIQUIDATION_HISTORY_SURVEY.md`)。
集計サービスは `liquidation-history` を持っていますが**どこまで遡れるかはキーが無いと分かりません**。
**もし年単位で遡れるなら、自前記録の位置づけが変わります**(保険に降格し、設計が軽くなる)。
キー 1 本で分かることなので、記録を始める前に確かめます。

**このキーで何ができるか / できないか**: 市場データの**読み取り専用**です。
取引所の口座とは無関係で、**資金にも建玉にも一切触れません**。無くてもプロジェクトは動きます。

### 1. Coinalyze(こちらが本命)

1. https://coinalyze.net/ を**ブラウザで**開き、Sign Up(メールアドレスで無料登録)
2. ログイン後 https://coinalyze.net/api/ を開くと、API キーを生成するボタンがあります
3. 生成されたキーをコピー

> 参考: API 仕様は https://api.coinalyze.net/v1/doc/(ログイン不要で読めます)。
> 清算履歴のほか**建玉・資金調達率・ロングショート比の履歴**も同じキーで取れます
> — トリアージ #70(ポジショニング)でも使える可能性があります。
> 制限は **1 分あたり 40 回**。

### 2. CoinGlass(比較用。余力があれば)

1. https://www.coinglass.com/ で無料アカウントを作成
2. アカウント設定 / API のページでキーを発行(無料枠あり)
3. 仕様は https://docs.coinglass.com/

### 3. キーの置き場所(**ここが大事**)

リポジトリ直下の **`.env`** に**だけ**書きます。`.env` は git 管理外です。

```
COINALYZE_API_KEY=（コピーしたキー）
COINGLASS_API_KEY=（取得したなら）
```

`.env` がまだ無ければ `.env.example` をコピーして作ってください。

> **キーをチャットに貼らないでください。** コミットにも、スクリーンショットにも入れないでください。
> 必要なのは「取得した」という事実だけで、キーそのものを私が知る必要はありません。

### 4. 深さの確認(1 分)

```
.venv\Scripts\python.exe scripts\check_liquidation_history_depth.py
```

1 日前・7 日前・30 日前・90 日前・180 日前・1 年前・2 年前を順に叩いて、
**どこまでデータが返るか**を表示します。**このスクリプトはキーを表示しません**
(設定の有無と文字数だけ出します)ので、**出力はそのまま共有して構いません**。
`.env` は共有しないでください。

### 5. 共有するもの

上の出力をそのまま貼ってください。それだけで次の判断ができます:

- **年単位で遡れる** → Gate の 90 日取り込みも自前記録も、優先度が下がります
- **数か月しか遡れない / 粒度が粗い(1 時間の集計値など)** → 予定どおり
  Gate の 90 日を取り込み、P8 で記録を始めます

