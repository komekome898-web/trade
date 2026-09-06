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
