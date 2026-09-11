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

### P4-N 夜間の自動 restart_all(1 回だけ登録。オーナー承認 2026-09-12、L-125)

以後、手動の P4 は不要になる。毎日 **日本時間 04:02** に `deploy\nightly_restart.bat` が
pull → 依存更新 → 停止 → 起動 を無人で行い、結果を `logs\nightly_restart.log` に追記する
(`share_logs.bat` が翌朝 06:30 にこのログも共有するので、確認はリードが行う。オーナーの作業なし)。
失敗したら残りを飛ばして旧コードのまま動く(`restart_all.bat` と同じ中断規則)。

**時刻の根拠**: 再起動で記録器が止まるのは 1 分程度で、その分のデータは毎晩失われる。04:02 を選んだのは
bitFlyer の日次メンテナンス窓(04:00〜04:10 JST)の中なら失うものが無いと見込むため。ただしこの窓は
**二次情報**(`docs/NEGATIVE_FACTS.md` N-006: 一次文書は本環境から未確認)で、**仮定**として置く。
窓がずれていても、失うのは毎晩 1 分の記録であって安全性(誤発注・二重起動)には関係しない。

**既存の 2 タスクとの重なり(推定、未実測)**: `bitflyer-start-all`(1 時間ごと)が停止と起動の間に
割り込んでも、`start_all.bat` は動いているものを飛ばすので二重起動にはならない。`bitflyer-fetch`
(15 分ごと)が pull の数秒間に当たると、その 1 回だけ失敗しうる(すべて再実行で埋まる)。

**登録の性質(推定)**: `/RU` を付けない `schtasks /Create` は「現在のユーザーで、ログオン中のみ実行」に
なる(P6 の `trade_share_logs` と同じ書き方で、P6 は実際に毎朝動いている)。git の資格情報が
オーナーのユーザーにあるため、この形でよい。資格情報の入力を求められる状態なら pull は**待たずに失敗**
して中断する(`GIT_TERMINAL_PROMPT=0`)。

**前提**: `nightly_restart.bat` がまだ PC に無いなら、先に手動で `deploy\restart_all.bat` を 1 回実行して
取り込む(清算記録の修正 = 次に渡す手順 P14 と同じ回でよい。P14 はこの文書にまだ無い)。

1. cmd または PowerShell(管理者不要)で 1 行:
   ```
   schtasks /Create /TN "trade_nightly_restart" /TR "C:\Users\ryoma\trade\deploy\nightly_restart.bat" /SC DAILY /ST 04:02 /F
   ```
2. 確認: `schtasks /Query /TN trade_nightly_restart`(登録されていれば 1 行出る)。

**未確認のまま渡すもの**: bat は Windows で実行検証していない。具体的には (a) `pause` の抑止
(環境変数 `TRADE_NONINTERACTIVE`)が Task Scheduler 下で効くこと、(b) pull で書き換わる bat を避けるための
コピー実行(`_restart_all_copy.bat`)が意図どおり動くこと、(c) 資格情報の GUI プロンプトが出ないこと、
(d) ログの 5 MB での切り替え。いずれも初回の `nightly_restart.log` でリードが確認する。

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

**なぜ急ぐか**(L-027 / L-031 で訂正済み): 遡れる分は少しある — Gate.io が**1 件ごと・約 90 日**、
OKX が約 24 時間、Coinalyze の**分足は 7 日**まで。だが **Binance と BitMEX はストリームしか無く**、
**分解能のある清算履歴はどこにも 7 日ぶんしか存在しない**。
つまり記録を始めるまでの毎日が、その 2 取引所では永久に、分解能としては全体で永久に空白になる。
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

**実施済み 2026-09-08(L-032): 4 取引所すべて「使える」**。以後この節は再実行不要
(経路が変わったとき — 回線・VPN・引っ越し — だけやり直す)。

### 2. 記録開始

`deploy\start_all.bat` に**常駐プロセスとして追加済み**なので、次に

```
deploy\restart_all.bat
```

を実行すれば動き出します(pull → install → 停止 → 起動)。
起動後、`logs\liquidations.out.log` に「接続」の行が出ていれば記録中です。

出力先は `data\liquidations\<取引所>_<日付>.jsonl.gz`。
`share_logs.bat` が毎日 06:30 に共有するので、こちらでも読めます。

### 3. 確認(**起動直後に 1 回**。翌日ではありません)

```
deploy\check_liq_recorder.bat
```

プロセスの状態・ログの末尾 20 行・書けているファイルを出します。**読むだけ**で何も変えません。
**出力をそのまま共有してください**(秘密情報は含まれません)。

**なぜ翌日ではなく直後か**: 清算だけは**止まっていた時間が永久に埋まらない**データです。
共有 (`share_logs.bat`) は毎日 06:30 に 1 回なので、それを待つと**丸一日ぶん失ってから**
気付くことになります。起動が失敗していたら、その場で分かる必要があります。

期待する中身: `1. process` が `RUNNING`、`2. log` に **4 取引所ぶんの「接続」の行**、
`3. files` に `binance_um_<日付>.jsonl.gz` など。**清算は常時起きるものではない**ので、
直後にファイルが小さい(数 KB)のは正常です。翌日には育っています。

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

**`.env` は git に乗りません。** `.gitignore` で除外してあるので、`git pull` しても降ってきません
(降ってきたのは見本の `.env.example` です)。**秘密情報を共有しないための設計であって、不具合ではありません。**
`.env` は**オーナー PC の中だけ**に存在し、そこで手で編集します。

> **`.env.example` を `.env` に上書きコピーしないでください。**
> オーナー PC の `.env` には既に bitFlyer の API キーなどが入っており、上書きすると**BOT が起動しなくなります**。
> やることは**2 行の追記**だけです。

PowerShell をリポジトリのフォルダで開いて:

```
notepad .env
```

メモ帳が開くので、**いちばん下に 2 行足して**保存します(既存の行は消さない):

```
COINALYZE_API_KEY=ここに貼る
COINGLASS_API_KEY=ここに貼る（CoinGlass を取っていないなら空のままで可）
```

`=` の後ろに**空白を入れない**でください。引用符も不要です。

> **キーをチャットに貼らないでください。** コミットにも、スクリーンショットにも入れないでください。
> 必要なのは「取得した」という事実だけで、キーそのものを私が知る必要はありません。

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

## P10 BitMEX アーカイブの丸ごと保全(**期限あり: 2026-09-23**)

**なぜ急ぐか【事実・一次情報】**: BitMEX 自身の告知(`api/v1/announcement`、2026-09-01 付)に、
**2026-09-16 12:00 UTC** に XBTUSD 等を上場廃止・清算、**2026-09-23** に**取引所そのものを閉鎖**とある。
公開アーカイブ(2014-11-22〜2025-02-22)が閉鎖後も置かれ続ける保証はどこにも無い。
**カツオの原典ベニューなので、ヒゲの機構を歴史的に検証できる唯一のデータ。**

方針はオーナー決定(L-039): **変換も間引きもせず、配布されているファイルをそのまま取る。**

### 取るもの【実測 2026-09-09】

| 系統 | ファイル | 容量 | 中身 |
|---|---|---|---|
| `trade` | 3,746 | **47.9 GB** | 約定 1 件ごと(全銘柄・全期間) |
| `quote` | 3,746 | **197.8 GB** | 板の最良気配の更新 1 件ごと |
| 合計 | | **245.7 GB** | C ドライブの空き 400 GB に収まる |

`porl`(準備金証明、85.9 GB)は**相場データではない**ので既定では取りません。
欲しければ末尾に `--include-porl` を付けてください。

### 1. まず少しだけ試す(3 分)

PowerShell をリポジトリのフォルダで開いて:

```
git pull --rebase origin claude/bitflyer-trading-bot-hhxxaf
deploy\mirror_bitmex.bat --only trade --max-files 20
```

20 本だけ取って止まります。エラーが出ずに終われば本番へ。

### 2. 本番(**数時間〜1 日**。放っておいて構いません)

```
deploy\mirror_bitmex.bat
```

- **途中で閉じてよい**です。もう一度同じものを実行すれば**続きから**進みます。
- 既にあるファイルは**サイズを照合して飛ばす**ので、二重取得も上書きもしません。
- **半端なファイルは残りません**(`.part` に書いて完了時に改名)。
- **空きが 20 GB を切ったら自分で止まります**。
- BOT には一切触れません(停止も起動も pull もしない、読むだけ)。

保存先は `data\archive\bitmex\`(git 対象外)。**リポジトリには入りません** —
246 GB を git に載せると壊れるためです。**このデータはオーナー PC の 1 コピーになります。**
外付けドライブがあるなら、終わったあとコピーを取っておくと安心です。

### 3. 確認(オーナーの作業なし)

進捗は `paper_logs\bitmex_mirror_status.json` に自動で書かれ、
毎日 06:30 の `share_logs.bat` が共有します。**リードがそれを読むので、貼り付けは不要です。**
何日か経っても進んでいなければ、こちらから声をかけます。

急ぎで見たいときだけ: `logs\bitmex_mirror.log` の末尾に速度と残り時間が出ています。

## P11 板の上位10段の毎日抽出(経費の床 E-b。オーナー承認 2026-09-11 L-098)

**何が変わるか**: `deploy\fetch_all.bat`(タスクスケジューラで15分ごと)が
`scripts\extract_tape.py --board-top 10` を実行するようになった。板WS記録
(`data\ws\*.jsonl.gz`)から板を再構成し、1秒ごとの上位10段(bid/ask 各10段の
価格・サイズ)を `data\tape\board_top10_YYYYMMDD.csv.gz` に追記する。従来の
`board_top5_*`(オンデマンド、研究窓のみ手動実行)とは別ファイルで、こちらは
**毎日・自動**。マニフェスト(`data\tape\manifest.json`)で既処理分を記憶する
差分実行なので、再実行しても重複しない。

**容量の見込み**: 実測済みの上位5段(オンデマンド、2026-08-20〜26の7日、
1秒サンプル)が平均 約2.7MB/日・最大 約3.5MB/日(gzip後)。上位10段は列数が
ほぼ倍(価格・サイズ×2段分)になるため、**約5〜7MB/日**と見込む。
10MB/日の目安(このタスクの発注条件)を下回るので、**サンプリングは変更しない**
(既に1秒間隔=1Hzのまま)。週4本(約28日)の運用でも 150〜200MB程度。

**自動で始まるか**: はい。`restart_all.bat`(pull → 依存更新 → 再起動)を
実行すれば、次の `fetch_all.bat` の定期実行(15分ごと、既存のタスク
`bitflyer-fetch`)から自動的に始まる。追加の手順・登録は不要。

**バックフィル(既に溜まっている生WS記録の分も上位10段を作る。自動。手動コマンドは原則不要)**:
オーナーPCの `data\ws\*.jsonl.gz`(板WS生記録)は共有されたことがなく
(共有していたのは抽出後の `executions_*`・`ticker_*` だけ)、これまで手元に
残っている分がそのまま残っている(台帳 `docs/DATA.md` の「WS 生ログ(オーナー PC、未共有)」の行)。
`extract_tape.py` は**毎回 `data\ws` の中身を全件スキャンする**(「今日のファイルだけ」ではない)ので、
P4(`restart_all.bat`。2026-09-11 実施済み、L-118)の後の最初の `fetch_all.bat`(15分ごと、既存タスク
`bitflyer-fetch`)が、残っている生WS記録**全期間分**の板上位10段を自動で一括生成する
(ファイルごと・行ごとのマニフェストカーソルが「未処理」のままだから)。初回は時間がかかりうるが、
途中で止まってもマニフェストのおかげで次の回が続きから進む。

**手動で `extract_tape.py` を走らせないこと(2026-09-11 監査役の指摘で改訂)**: `fetch_all.bat` の自動実行と
同時に走ると、2 つのプロセスが同じ `data\ws` を走査して同じ行を二重に書く。多重起動を止めるロックは
2026-09-11 にコードへ入れたが、オーナー PC には**次の P4 で取り込むまで無い**。手動実行が要る場合
(下の確認で 2 時間たっても何も出ないとき)は、その旨をリードに伝えて指示を待つ。

1. どの期間が残っているか確認(生WS記録のファイル名 `<商品>_YYYYMMDD_HHMMSS.jsonl.gz`
   の先頭と末尾が最古・最新の日付)。結果(最古と最新の日付)をリードに伝える:
   ```
   dir data\ws
   ```
2. 出力サイズの見込み: 残っている日数 × 約5〜7MB/日(下記の見積り)。
   例: 手順1で最古が2026-08-20と出た場合、2026-09-11時点で約3週間分 ≈
   **100〜150MB程度**(`data\tape\board_top10_YYYYMMDD.csv.gz` が日付ごとに
   分割生成される)。
3. P4 から 1〜2 時間後に `dir data\tape\board_top10_*.csv.gz` で、手順1で見えた最古の日付から
   今日まで揃っているか確認。揃っていれば自動実行が新しい分だけ増分で追記していく。
   **何も出ない場合**は `findstr "extract_tape board" logs\fetch.out.log` の末尾 20 行を送る。

**Python の版について(オーナーの問い、L-118)**: `fetch_all.bat` は `.venv\Scripts\python.exe` を
直接呼ぶので、使われる版は `.venv` を作ったときの版に固定される(`pyproject.toml` の
`requires-python = ">=3.11"`)。**P4 の `pip install -e ".[dev]"` が通った時点で版の条件は満たされている**
(満たさなければ pip がその段で止まり、restart_all が中断する)。確認したければ
`.venv\Scripts\python.exe --version` が `Python 3.11.x` 以上を出せばよい。
素の `python` や `py` は別の Python に当たりうるので、手順書では使わない。

**日々の確認**:

1. `deploy\restart_all.bat` を実行(pull と依存の更新を含む)。
2. 15〜30分待って確認:
   ```
   dir data\tape\board_top10_*.csv.gz
   ```
   その日の日付のファイルができていれば動いている。
3. ログで抽出行数を見たい場合:
   ```
   findstr "board row" logs\fetch.out.log
   ```
4. `deploy\share_logs.bat`(毎日06:30、P6)が `data\tape\*.csv.gz` を
   `paper_logs\tape\` にまとめて共有するので、`board_top10_*` も
   従来の `executions_*`・`ticker_*` と一緒にリードへ届く。個別の確認は不要。

## P12 資金調達率とベーシスの日次ログ(経費の床 E-g。オーナー承認 2026-09-11 L-098)

**何が変わるか**: `deploy\fetch_all.bat` が `scripts\record_funding_basis.py`
を実行するようになった。公開APIのみ(認証キー不要・注文系エンドポイントに
触れない)で、
- 現在の資金調達率(`/v1/getfundingrate`)と、直近の確定済み調達率
  (`/v1/getfundingratehistory`、まだ記録していない分だけ)を
  `data\funding_rate_history.csv`(既存ファイル。列: calculation_date,
  settlement_date, rate)に追記する。settlement_date で重複排除するので
  何度実行しても増殖しない。
- FX_BTC_JPY と BTC_JPY(現物)の公開ティッカーから mid-to-mid のベーシス、
  および分足ファイル(`data\candles_FX_BTC_JPY.csv` /
  `data\candles_BTC_JPY.csv`、あれば)の1分終値ベーシスを
  `data\basis_log.csv`(新規ファイル)に追記する。こちらは時系列そのものなので
  毎回追記する(重複排除はしない)。

**自動で始まるか**: はい。P11 と同じく `restart_all.bat` の後、既存の
`fetch_all.bat` の定期実行(15分ごと)から自動的に始まる。

1. `deploy\restart_all.bat` を実行。
2. 15〜30分待って確認:
   ```
   type data\basis_log.csv
   ```
   最新行の ts_utc がここ数十分以内なら動いている。`funding_rate_history.csv`
   は8時間ごとにしか新しい確定行が増えないので、行数が増えていなくても正常
   (現在の調達率の行だけは毎回試みる)。
3. `deploy\share_logs.bat`(毎日06:30)が両ファイルをそのままリードへ届ける。
4. 常駐モード(任意。fetch_all の15分ごとで十分なので通常は不要):
   ```
   .venv\Scripts\python.exe scripts\record_funding_basis.py --loop 3600
   ```
   1時間ごとに繰り返す。Ctrl+C で停止。

## P13 API応答遅延の読み取り専用プローブ(経費の床 E-h。オーナー承認 2026-09-11 L-098。1週間)

**何を測るか**: 認証つき読み取り専用エンドポイント(`getpermissions`。
`check_api.py` が既に使っているのと同じ。**注文系エンドポインではない**)1本と、
公開エンドポイント(`getticker` FX_BTC_JPY)1本を30秒ごとに叩き、往復時間を
`data\latency\api_probe.csv` に記録する。**注文応答そのものの遅延ではない**
(実弾を使わずに測れる最も近い代理量。E-h は「注文応答遅延は未測定」と明記した
まま進む)。板WS記録(`data\ws\`)が動いていれば、その最新の ticker メッセージの
受信遅れ(rts)も同じ行に併記し、両方の時計を並べられるようにする。
**LIVE_MODE では起動を拒否する**(PAPER の認証情報だけで確認済み — 読み取り
専用の権限で十分)。発注は一切しない。

### 1週間だけ動かす手順

1. `deploy\restart_all.bat` を1回実行(pull と依存の更新のため。プローブ自体は
   常駐リストには入れていないので、これ単独では起動しない)。
2. `deploy\probe_latency.bat` をダブルクリック(または PowerShell で実行)。
   最小化した別ウィンドウ(`bitflyer-latency-probe`)で168時間(1週間)・
   30秒間隔で動き始める。閉じずに1週間放置してよい(パソコンをスリープさせない
   こと)。
3. 既に動いている場合は二重起動せず「already running - skipped」と出る
   (再度ダブルクリックしても安全)。

### 動いているかの確認

```
type logs\latency_probe.out.log
```
直近の行に `public:getticker=200(…ms)` のように出ていれば正常。
```
type data\latency\api_probe.csv
```
数十行ごとに新しい行が増えていれば正常(30秒間隔なので1時間で約120行 =
公開・認証つき各1行×2)。

### 停止

- ウィンドウ(`bitflyer-latency-probe`)を閉じる、または PowerShell で:
  ```
  taskkill /FI "WINDOWTITLE eq bitflyer-latency-probe*"
  ```
- 168時間経過すると自動的に終了する(そのまま放置でよい)。
- `deploy\share_logs.bat`(毎日06:30)が `data\latency\api_probe.csv` を
  `paper_logs\latency\` へ共有するので、実行中でもリードが途中経過を読める。

## P14 清算記録の gzip 回収(2026-09-12、L-121)

**何が起きたか**: 清算(強制決済)記録器(`record_liquidations.py`)は、これまで
1つの gzip の「メンバ」を開いたまま起動し続ける作り方だった。`deploy\stop_all.bat`
での強制終了(`Stop-Process -Force`)やクラッシュでプロセスが落ちると、その
メンバは「ここで終わり」という印(終端マーカー)が付かないまま残る。次に記録器が
起動すると、そこに気づかず**新しいメンバのヘッダを直後に継ぎ足す**ため、
ファイルを読もうとすると `invalid block type` のような gzip エラーで**丸ごと
読めなくなる**。オーナー PC でこれが起きたファイルは 10 個
(`data\liquidations\{binance_cm,bitmex,bybit,okx}_20260911.jsonl.gz`、
`{bitmex,bybit,okx}_20260909.jsonl.gz`、`paper_logs\liquidations\*_20260909.jsonl.gz`)。

記録器自体は直した(メンバを開いたまま保持せず、少量ずつ完結した形で書くように
変更。詳細は `record_liquidations.py` のコード先頭のコメント)。**この修正が効くのは
次に `deploy\restart_all.bat` を実行した後から**であり、それより前に壊れた
上記 10 ファイルは直っていない。直すには下記の回収スクリプトを走らせる。

**元のファイルは一切書き換えない・削除しない。** 回収スクリプトは読むだけで、
結果は別の場所(`data\liquidations_repaired\`)に新しいファイルとして作る。
壊れた元ファイルはそのまま残るので、失敗しても何度でもやり直せる。

**なお、記録器自体が自動で治す部分もある**: 修正を配る `restart_all.bat` は、
配る前の古い記録器を強制終了させてから新しい記録器を起動する。つまり
**修正後に最初に起動した時、その日のファイルがまだ壊れていることがある** —
このケースは記録器自身が起動時に検知し、壊れたファイルを
`<取引所>_<日付>.trunc1.jsonl.gz` のような名前に自動で退避してから、
同じ名前で新しいファイルを書き始める(ログに1行出る)。**この分はオーナーが
何もする必要はない** — 退避されたファイルも下記の回収スクリプトが
そのまま拾う(`*.trunc*.jsonl.gz` も対象)。

### 手順

1. まず `deploy\restart_all.bat` を実行(pull・依存更新・記録器の再起動。
   これをやらないと直った記録器が動かない)。
2. PowerShell で、まず `--dry-run` で何が回収できるか確認(何も書き出さない):
   ```
   cd C:\Users\ryoma\trade
   .venv\Scripts\python.exe scripts\repair_liquidation_gz.py --dry-run data\liquidations paper_logs\liquidations
   ```
   (`python` を直接使わない — `.venv\Scripts\python.exe` を必ず使う。)
3. 表示された内容(各ファイルの `members` / `recovered` / `discarded` /
   `original_readable_as_is`)を見て問題なければ、実際に書き出す
   (`--dry-run` を外すだけ):
   ```
   .venv\Scripts\python.exe scripts\repair_liquidation_gz.py data\liquidations paper_logs\liquidations
   ```
   結果は `data\liquidations_repaired\` の下に、元のディレクトリ構造を保った形
   (`data\liquidations_repaired\data\liquidations\...` など)で作られる。
4. `deploy\share_logs.bat` の対象には入っていないので、回収した中身を
   リードに送るには、上記コマンドの**画面出力をそのまま貼る**か、
   `data\liquidations_repaired\` 以下のファイルを直接送る。

### 送り返してほしいもの

- 手順2・3の画面出力(各ファイルの `members` / `recovered` / `discarded` /
  `original_readable_as_is` と、末尾の合計行)。
- `logs\liquidations.out.log`(この記録器専用のログ。`share_logs.bat` には
  含まれないので `type logs\liquidations.out.log` で直接確認し、
  「不完全 -> ... へ退避」という行があれば、その行だけ貼る
  — 自動退避が実際に起きたかどうかの記録として)。

