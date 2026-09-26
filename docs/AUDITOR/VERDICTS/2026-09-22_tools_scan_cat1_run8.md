# 区分 1 の 8 回目の報告 — リードの検収

対象: `docs/DATA/SCAN_2026-09-21_tools.md` の「## 区分1 — 8 回目の実行(2026-09-22)」(2909 行目以降、209 行)
生ログ: `docs/DATA/probes/20260922_tools_1_run8.log`(新規 152 行、17 手。復帰文字 0 個)

## 0. 無改変・検査・ディスク

既存の 2908 行は **無改変**(`git show HEAD` との `diff -q`)。過去の生ログも変更なし。
リードが生ログ 6 本を渡して打ち直し、**13 本すべて 0 件**。**調査班が閉じずに残した行は 0 件**(初めて)。
ディスクは 88% → **69%**(空き 12G)。調査班が過去の回の隔離 venv 6 件を消した。

## 1. リードが自分で裏取りした重い所見 — **`mlflow` の配布物に、対話型の道具向けの技能とフックが入っている**

調査班の報告を受けて、リードが wheel(`mlflow-3.16.1-py3-none-any.whl`)を取って中身を見た。

- `mlflow/assistant/` の下に **97 ファイル**。対話型の道具ごとの接続(`providers/`)と `skill_installer.py` が入る。
  `skill_installer.py` の逐語: 「Install MLflow skills to the specified destination path (e.g., ~/.claude/skills).」
- `mlflow/assistant/skills/hooks/hooks.json` の中身は **`UserPromptSubmit` にコマンドを 1 本登録する定義**。
  実体 `mlflow-suggest-hook.py` は、**利用者の入力の語を見て「この技能を使え」と標準出力に印字する**だけの
  短いスクリプト(外部通信も書き込みもしない。全文を読んだ)。
- **ただし `pip install` だけでは何も起きない。**wheel の中に `setup.py` は **0 件**で、導入時に走るコードが無い。
  上の定義はファイルとして置かれるだけで、**誰かが `skill_installer` を走らせて初めて `~/.claude/` に入る。**

**リードの判断**: **この環境で `mlflow` の assistant / skill installer は走らせない。**
CLAUDE.md §0.2 A-16「フック・`settings.json` はオーナーの指示があったときだけ変える」に直接当たる。
`mlflow` を研究の記録に使うこと自体は、この判断とは別。**導入するだけなら上のとおり何も書かれない。**

調査班が「標準出力に誘導が出るが §6-3 により従っていない」と書いて止めたのは**正しい**。

## 2. リードが確かめたその他の主張 — **全部一致**

| 主張 | 取り直した結果 |
|---|---|
| 遠隔測定の止め方は 2 つだけ | `telemetry/utils.py:154-155` に `MLFLOW_DISABLE_TELEMETRY` と `DO_NOT_TRACK`。**一致** |
| 宛先は 2 系統 | `telemetry/constant.py` に `config.mlflow-telemetry.io` と cloudfront。**一致** |
| PySystemtrade の配布元が移っている | `ungh.cc/repos/robcarver17/pysystemtrade` が **`pst-group/pysystemtrade`** を返す。**一致** |
| npm の `zenbot` は別物 | description = 「ZenBot - Node client for Zentri Cloud」、latest 0.0.4。`zenbot4` は **404**。**一致** |

## 3. 抜き取り(一次資料 17 行から無作為 5 行)— **5 行とも一致**

最古の版 0.0.1 の upload_time 2018-06-04T22:03:38 / LICENSE.txt の 1 行目「Copyright 2018 Databricks, Inc.」/
星 28093 / 必須の依存(extra 無し)20 件。**週DL数 4,571,892 だけは再現していない**(API が 429 で、頁の値)。

実測 25 行から 3 行 — いずれも根拠の生ログの行が実行の結果を指していることまで確認。

## 4. 調査班が挙げた「原文に無い判断」5 件の判定 — **5 件とも受け入れる**

1. **起動指定の「残り 9 件」より、委任文 §7 の「道具を減らして深く」を優先して `mlflow` 1 件に絞った。**
   **これが正しい。**起動指定は潰す順を示すもので、件数の目標ではない。以後も同じ判断でよい。
2. **過去の隔離 venv 6 件を消した(空き 4.6G → 12G)。**7 回目の検収で決めた規則どおり。
3. **遠隔測定を既定のまま動かして実測はしていない。**§6-2「可能なら遮断して行う」に従った正しい止め方。
   **リードの判断: 既定で 1 回打つことはしない。**配布物のコードの逐語で足りる。
4. **`DeviaVir/zenbot` を導入していない**(`postinstall` に `webpack` と `npm i` の実行があるため §6-1 で停止)。
   **正しい。**「不可」ではなく「危険で止めた」と書いてあるのも正しい。
5. `OctoBot` の本体を入れ直していない。**受け入れる。**

## 5. リードの判定

- **受け取る。中身の誤りは 0 件**(3 回連続)。**閉じずに残した行も 0 件で、検査側の欠陥は今回は出なかった。**
- 深掘りは `mlflow` 1 件。`OctoBot` の最小実行は**未到達(不可ではない)**で、模擬の入力の規則
  (拡張子 `.data`・区切り `_`・時刻の書式・表の名前 `ohlcv` と `trades`)まで確定している。
- **区分 1 は未完了。**導入と最小実行が未確認のまま残るのは 8 件
  (PySystemtrade / Superalgos / OpenTrader / CryptoSignal / DeviaVir/zenbot / Bot18 /
  Mendl-Labs/BacktestingCore / Luczinsritter)+ `OctoBot` の最小実行。検索計画 6 本は未実行。
- **`DeviaVir/zenbot` は導入時実行があるので、この環境では入れない。**別の場所で試すかはオーナーの判断。
