# 項目 3 要件の固定 — 検証・再現・出力(統計・実行記録・指標・ダッシュボード)

資料係(要件の固定)。委任文 `docs/DATA/delegations/20260925_backtest_env_prompt.md`(指紋 `20260925_backtest_env_prompt.md@da84268e88fc`)§2・§3「要件と判定の固定」「調査結果の側の選び方」に従う。**このファイル以外は書いていない。**

## 1. 委任文 §2 の項目 3 の行(逐語)

委任文 §2 の表、項目番号 3 の行をそのまま引く(1 語も削らない):

> | 3 | 検証・再現・出力(統計・実行記録・指標・ダッシュボード = 旧 7 + 8 + 9 + 10) | `src/bot/bt/validation/`、`src/bot/bt/repro/`、`src/bot/bt/report/`、`src/bot/monitoring/backtest_view.py`・`scripts/dashboard.py` の追記 | 【旧 7 検証と統計】暦日での Train / Val / OOS、purge と embargo つきの walk-forward と CPCV、ブロック・ブートストラップ、MDE の計算、deflated Sharpe と PBO、周回数の台帳(research-protocol の ITER)。**封印区間は `load_sealed` の 4 門を通らない限り読めない** **/** 【旧 8 再現性】実行記録(git の SHA と差分のハッシュ・設定・データの sha256・種・版)。実行 ID = 内容のハッシュ。**同じ入力で 2 回回して一致を自動で確かめる**。成果物は `backtest_runs/<id>/`(gitignore)。事前登録のハッシュを実行記録に入れる **/** 【旧 9 指標と書き出し】平均で潰さず分布で出す(1 件ごとの bp・分位・負の割合)。露出あたり(bp/時)。約定率・取り逃し・逆選択の markout・費用の内訳・決済理由・ドローダウン。実行の目的(`動作確認` / `研究`)を指標の書き出しに必ず載せる(§4) **/** 【旧 10 ダッシュボード】「バックテスト」タブ。実行の一覧 → 実行ごとの項目別タブ: 概要 / 前提(約定・遅延・費用・データ)/ 損益 / 取引 / 約定の質 / 費用 / 分布 / 検証 / 再現性 / データ品質。日本語。CDN を使わない。配線の試験。目的が `動作確認` の実行は全タブに「動作確認の実行。相場の結論には使わない」を出す(§4) |

(§2 の見出し行から持ち物の共通の注記: 「1 項目 = 作業者 1 体 + 場面係 1 体(1 周目の前だけ)+ 資料係 1 体 + 批評家 1 体 + 審査員 6 体」。持ち物には `tests/bt/item_3/` を含む。)

## 2. 比較の観点(観点ごとに 1 行、測れる形)

オーナーの完了の形(逐語、L-405)「**すべてが調査結果以上の信頼性と再現性に優れたものにすること。**」をどの観点でも軸に置く。各行は「満たすか満たさないかを場面(値の場面 / 能力の場面)で判定できる」形にした。旧 7(検証と統計)・旧 8(再現性)・旧 9(指標と書き出し)・旧 10(ダッシュボード)の逐語の各要素に 1 行ずつ対応させた。

| # | 観点 | 測り方(測れる形) |
|---|---|---|
| C3-1 | 暦日 Train/Val/OOS と walk-forward | 暦日で Train/Val/OOS に切る場面(値の場面: 既知の日付範囲の入力 → 期待する 3 分割の境界日)と、walk-forward で複数回切り直して各回の評価を出す場面(能力の場面)を持つか |
| C3-2 | purge・embargo つき walk-forward と CPCV | 学習区間と評価区間の間に purge(重なりの除去)と embargo(境界の空白期間)を入れた walk-forward の場面と、CPCV(組合せ purge 付き交差検証)で複数の分割の組合せを評価する場面を持つか |
| C3-3 | ブロック・ブートストラップ | 時系列の自己相関を壊さないブロック単位の再抽出で信頼区間を出す場面(値の場面: 既知分布の合成データ → 理論値に近い CI)を持つか |
| C3-4 | MDE の計算 | 事前登録の前に、その n とその分散で検出できる最小効果量(MDE)を計算する機能を持ち、`.claude/skills/research-protocol/SKILL.md`(§4.1、行 342-345)の規則どおり「MDE を書けない主張は陰性として扱わない」を構造で強制できるか |
| C3-5 | deflated Sharpe と PBO | 試行回数(周回数の台帳)を踏まえてシャープレシオを補正する deflated Sharpe と、Probability of Backtest Overfitting(PBO)を計算する場面を持つか |
| C3-6 | 周回数の台帳(ITER)と封印区間の 4 門 | research-protocol の ITER 台帳(`.claude/skills/research-protocol/SKILL.md:60`)に周回数を累積し多重性に算入する仕組みと、封印区間へのアクセスが `src/bot/research/sealed.py: load_sealed` の 4 門(env / 承認ファイル / トークン / 項目 0 で足した 4 つ目の門)を全部通らない限り読めない構造を持つか |
| C3-7 | 実行記録の内容 | 1 回の実行ごとに git の SHA・差分のハッシュ・設定・データの sha256・乱数の種・版を実行記録に残す場面(能力の場面: 実行後、記録ファイルにこれら全部の欄が埋まっているか)を持つか |
| C3-8 | 実行 ID = 内容のハッシュ | 実行 ID が実行内容(設定・データ・コード)から決定的に導かれるハッシュであり、乱数や時刻に依存しない値であるか(値の場面: 同じ入力を 2 回渡して同じ実行 ID が出るか) |
| C3-9 | 同一入力の再現性の自動確認 | 同じ入力で 2 回実行し、結果が一致することを人手を介さず自動で確かめる仕組み(能力の場面)を持つか |
| C3-10 | 事前登録ハッシュの実行記録への組み込み | 事前登録ファイルのハッシュを実行記録に含め、どの事前登録に基づく実行かを後から機械的に特定できるか |
| C3-11 | 平均で潰さず分布で出す | 1 件ごとの bp・分位(パーセンタイル)・負の割合を、平均値 1 個に潰さずに出力できるか(値の場面: 既知の分布を持つ合成トレード列 → 期待する分位値) |
| C3-12 | 露出あたり(bp/時) | 単純な合計/平均ではなく、建玉を持っていた時間(露出)あたりの指標(bp/時)を計算できるか |
| C3-13 | 約定率・取り逃し・逆選択 markout | 約定率、指値が埋まらなかった取り逃し件数、約定後の値動き(逆選択の markout、複数の時間窓)を指標として出せるか |
| C3-14 | 費用の内訳・決済理由・ドローダウン | 費用を種類ごと(maker/taker 手数料・スプレッド・資金調達等)に内訳で出し、決済理由(TP/SL/time_exit 等)ごとの集計を持ち、ドローダウンを出せるか |
| C3-15 | 実行目的(動作確認/研究)の指標書き出しへの記載 | 指標の書き出し(ファイル・レコード)に、その実行の目的が `動作確認` か `研究` かを必ず記載する構造上の強制があるか(委任文 §4「実データから出た数値は…その実行の書き出しの全部に目的『動作確認』を載せる」) |
| C3-16 | 「バックテスト」タブと実行一覧→項目別タブの構成 | ダッシュボードに「バックテスト」タブがあり、実行の一覧から実行ごとの項目別タブ(概要/前提/損益/取引/約定の質/費用/分布/検証/再現性/データ品質)へ遷移できるか |
| C3-17 | 日本語表示・CDN 不使用 | ダッシュボードの文言が日本語で、外部 CDN からスクリプト・スタイルを読み込まずに動くか |
| C3-18 | 配線の試験 | ダッシュボードの API とタブ表示が配線どおりに繋がっていることを確認する自動試験を持つか |
| C3-19 | 動作確認実行の全タブ警告表示 | 目的が `動作確認` の実行を開いたとき、その実行のダッシュボード全タブに「動作確認の実行。相場の結論には使わない」という警告を出すか |

## 3. 調査結果の側(候補は機械で全部抜き出す。人が足し引きしない)

### 3.0 tsv に該当列は無い(確認したコマンドと出力)

まず `docs/DATA/tools_catalog.tsv` に、検証・統計・再現性・指標・ダッシュボードに対応する列があるかを確かめた。

```
head -1 docs/DATA/tools_catalog.tsv | tr '\t' '\n' | cat -n
```
出力(全 19 列):
```
 1  番号
 2  名前
 3  到達
 4  足
 5  ティック
 6  板の待ち行列
 7  イベント駆動
 8  ベクトル化
 9  市場影響と約定の模型
10  段(機構)
11  段(既定)
12  遅延
13  取り消しの扱い
14  他の区分へ
15  安全側の所見
16  尽きていない理由
17  報告書の最後の記載の行
18  段の表の行
19  遅延(原文)
20  取り消しの扱い(原文)
```
**列 9〜13(市場影響/段/遅延/取り消し)は項目 2(執行の模型)の観点であり、項目 3 のどの観点(C3-1〜C3-19)にも対応する列が無い。** `docs/DATA/TOOLS_CATALOG.md` の索引(§2.1〜§2.4)も同じく約定の埋まり方・列・遅延だけを扱い、検証・統計・再現性・指標・ダッシュボードの節は無い(`grep -n "^#\|^##" docs/DATA/TOOLS_CATALOG.md` の出力に該当節が無いことを確認済み)。**したがって C3-1〜C3-19 は全部「該当する要素の列が無い項目」であり、§3.1 以降は全部 `docs/DATA/SCAN_2026-09-21_tools.md` への grep で候補を取る。**

**この節にも段(機構)の尺度は元から存在しない**(段の尺度は道具台帳 §2.1 が約定の模型専用に定義したもの)。根拠のない尺度を新設すると A-12(根拠のない設定値)に触れるため、C3-1〜C3-19 のどの観点についても「段(機構)が最も高い機構」という形の順位は付けない。委任文 §3「調査結果の側の選び方」の「段のある観点」「段の無い観点」の場合分けに当てはめると、C3-1〜C3-19 は全部**段の無い観点**であり、動かせる候補は原則「全部を再現する」対象になる(場面係の役。ここでは候補と根拠行だけを固定する)。

### 3.1 事前にノイズを除いた SCAN の作業用コピー

`SCAN_2026-09-21_tools.md` は各回の冒頭に当方自身のファイル一覧(`### 当方の道具立て` 節、`scripts/tools_inventory.py` の出力)が挟まり、そこに `record_liquidations.py` のような当方のスクリプト名が語にマッチしてノイズになる(項目 2 の資料係が確認済みの問題と同じ)。行番号を保つため、削除ではなく空行への置換で一時ファイルを作った:

```
awk '
/^### 当方の道具立て/ {skip=1; print ""; next}
skip && /^### / {skip=0}
{ if (skip) print ""; else print }
' docs/DATA/SCAN_2026-09-21_tools.md > SCAN_clean.md
```
(置換先: `/tmp/claude-0/-home-user-trade/17c10364-8019-48da-af27-038caa7b187a/scratchpad/bt/item3_scan_clean.md`。10,694 行のまま、`### 当方の道具立て`〜次の `### ` 見出し直前を空行にした。)

### 3.2 観点ごとの grep(語を先に書いてから打った)

C3-1〜C3-19 は委任文 §2 の項目 3 行の逐語(暦日 Train/Val/OOS・purge・embargo・walk-forward・CPCV・ブロック・ブートストラップ・MDE・deflated Sharpe・PBO・実行記録・実行 ID・再現性・事前登録ハッシュ・分布・露出あたり・約定率・取り逃し・markout・費用の内訳・決済理由・ドローダウン・動作確認/研究・ダッシュボード・タブ)からそのまま語を起こした。

| # | grep 語(先に決めた) | コマンド | 当たり件数 |
|---|---|---|---|
| C3-1 | `walk.?forward\|out.?of.?sample\|OOS\|train.{0,10}(val\|test)` | `grep -inE 'walk.?forward\|out.?of.?sample\|\bOOS\b\|train.{0,10}(val\|test)' SCAN_clean.md` | 12 |
| C3-2 | `purg\|embargo\|CPCV\|combinatorial.{0,20}(cross\|purg)` | `grep -inE 'purg\|embargo\|\bCPCV\b\|combinatorial.{0,20}(cross\|purg)' SCAN_clean.md` | 3(すべて `pip cache purge` = ノイズ、後述) |
| C3-2 補助 | 片仮名表記 | `grep -inE 'ウォーク.?フォワード\|交差検証\|クロスバリデーション\|過剰最適化\|オーバーフィット' SCAN_clean.md` | 1(候補 107、C3-1 と同一) |
| C3-2 補助 | overfitting | `grep -inE 'overfit\|over.?fitting' SCAN_clean.md` | 0 |
| C3-3 | `block.{0,4}bootstrap\|bootstrap` | `grep -inE 'block.{0,4}bootstrap\|bootstrap' SCAN_clean.md` | 0 |
| C3-4 | `MDE\|minimum.{0,3}detectable` | `grep -inE '\bMDE\b\|minimum.{0,3}detectable' SCAN_clean.md` | 0 |
| C3-5 | `deflated.{0,3}sharpe\|probability of backtest overfitting\|PBO` | `grep -inE 'deflated.{0,3}sharpe\|probability of backtest overfitting\|\bPBO\b' SCAN_clean.md` | 0 |
| C3-6 | `封印\|sealed\|ITER` | `grep -inE '封印\|sealed\|\bITER\b' SCAN_clean.md` | 0 |
| C3-7/8 | `run.{0,3}id\|content.{0,3}hash\|reproduc\|determinist` | `grep -inE 'run.{0,3}id\|content.{0,3}hash\|reproduc\|determinist' SCAN_clean.md` | 11 |
| C3-9 | `seed\|random.{0,3}state` | `grep -inE '\bseed\b\|random.{0,3}state' SCAN_clean.md` | 5 |
| C3-10 | `pre.?registrat\|prereg` | `grep -inE 'pre.?registrat\|prereg' SCAN_clean.md` | 0 |
| C3-11 | `distribution\|quantile\|percentile\|histogram` | `grep -inE 'distribution\|quantile\|percentile\|histogram' SCAN_clean.md` | 2(いずれもノイズ、後述) |
| C3-12 | `exposure\|per.{0,3}hour` | `grep -inE 'exposure\|per.{0,3}hour' SCAN_clean.md` | 0 |
| C3-13 | `fill.{0,3}rate\|markout\|adverse.{0,3}selection` | `grep -inE 'fill.{0,3}rate\|markout\|adverse.{0,3}selection' SCAN_clean.md` | 2 |
| C3-14 | `drawdown\|exit.{0,3}reason\|cost.{0,3}breakdown` | `grep -inE 'drawdown\|exit.{0,3}reason\|cost.{0,3}breakdown' SCAN_clean.md` | 2 |
| C3-15 | `dry.?run\|smoke.{0,3}test\|paper.{0,3}(mode\|trading)` | `grep -inE 'dry.?run\|smoke.{0,3}test\|paper.{0,3}(mode\|trading)' SCAN_clean.md` | 11 |
| C3-16 | `dashboard\|ダッシュボード` | `grep -inE '\bdashboard\b\|ダッシュボード' SCAN_clean.md` | 3 |
| C3-17〜19 | (当方内部の制約語。§3.5 で扱う) | — | — |

### 3.3 当たった候補(候補番号は `docs/DATA/tools_catalog.tsv` の名前列と突き合わせて確認した。SCAN 内の「候補 N」の通し番号はその回のローカルな発見順であり台帳の番号と一致しない場合があるため、**必ず名前で tsv を引き直した**)

**C3-1(暦日 Train/Val/OOS と walk-forward)**:
- **候補 15 `Mendl-Labs/BacktestingCore`**(SCAN 198・819 行)。WebFetch 要約の逐語「event-driven simulation, walk-forward analysis, genetic strategy optimization」。**一次資料(README・コード)は未取得、WebFetch の要約のみ**。ライセンスは Functional Source License 1.1(OSI 非承認)。星 0・フォーク 0(SCAN 823 行)。tsv 上は `到達済み`、段既定=6(C3 の対象外である市場影響の観点での値。行 10518)。
- **候補 107 `sigc`**(`Skelf-Research/sigc`、SCAN 6689・6918 行)。追跡ファイルに `documentation/docs/backtesting/walk-forward.md` と `crates/sig_runtime/src/walk_forward.rs` が在ると記載されているが、**中身は未読**(SCAN 6689 行「中身は読んでいない」、6918 行「根拠が追跡ファイルの名前…だけで、中身は未読である」)。tsv 上は `区分4` に仕分け(区分1 の対象外候補として送られている。行 6917)。

**C3-2(purge/embargo/CPCV)**: 直接語の当たり 3 件はすべて `pip cache purge`(SCAN 2711・2817・2861 行、OctoBot 導入時のディスク容量問題)で、統計手法の purge/embargo とは無関係(**候補 0 件**)。片仮名表記・overfitting 語でも候補 107(C3-1 と同一、walk-forward 文書のみで中身未読)以外に当たりは無い。

**C3-3(ブロック・ブートストラップ)〜C3-6(MDE・deflated Sharpe・PBO・ITER・封印)**: **候補 0 件**(grep の当たりそのものが 0)。

**C3-7/C3-8(実行記録・実行 ID = 内容のハッシュ)・C3-9(再現性の自動確認)**:
- **`mlflow`(候補番号なし)**: `docs/DATA/tools_catalog.tsv` に名前の掲載が無い(`grep -n mlflow docs/DATA/tools_catalog.tsv` の当たり 0 件)。Qlib(候補 21)の必須依存として発見され(SCAN 1135 行)、8 回目の SCAN で `[深掘り]` された(SCAN 2998 行「隔離 venv に導入し、合成の約定の csv.gz で実験・パラメータ・指標・成果物・札の記録と読み戻しを鍵なしで通した」)。再現性の実測(SCAN 3049 行): 「置き場を消して同じ台本を 2 回打ち、識別子と時刻の行を除いた出力が一致(IDENTICAL_EXCEPT_TIME_AND_IDS)。実行の識別子は毎回変わる(RUN_ID_LEN 32)」。**実行 ID は乱数生成で、内容のハッシュではない**(委任文の「実行 ID = 内容のハッシュ」に一致しない設計)。安全側の所見: 既定で外部の遠隔測定サーバへ送信する(SCAN 2963 行、`MLFLOW_DISABLE_TELEMETRY` 等で止める必要がある)。道具台帳 §3 の危険な兆候の対象になりうるので、動かして候補に加えるなら §4 の安全規則を全部当てる。
- **候補 3 `PySystemtrade`**: SCAN 3505・3584 行「**この模擬は決定的で、速い。**同じ入力を 2 回走らせた約定の表が DETERMINISTIC_TWO_RUNS_IDENTICAL=True」「決定的。同じ入力で 2 回走らせた約定の表が一致し、DETERMINISTIC_TWO_RUNS_IDENTICAL=True。模擬の側に乱数は無い」(実測。docs/DATA/probes/20260922_tools_1_run10.log:637)。**範囲は指値の注文模擬(`hourly_limit_orders.py`)の 2 回実行一致であり、実行記録全体(git SHA・設定・データの sha256 等)のハッシュ化ではない**。
- **候補 98 `mihircoding/limitOrderBook`**: SCAN 9011・9148 行「遅延の模型を持つ…種を `np.random.default_rng(self.seed)` で取るので決定的に回せる」(一次資料、`latency.py` の逐語)。**遅延模型だけが種つきで決定的**という範囲の狭い実測。

**C3-10(事前登録ハッシュの組み込み)**: **候補 0 件**。

**C3-11(分布で出す)**: 直接語の当たり 2 件はいずれもノイズ(SCAN 2213 行「No matching distribution found」= pip のパッケージ配布形式の意味、SCAN 8603 行「段(既定)の分布」= 道具台帳内の集計作業の話であって候補の性質ではない)。**候補 0 件**。

**C3-12(露出あたり bp/時)**: **候補 0 件**。

**C3-13(約定率・取り逃し・逆選択 markout)**:
- **候補 95 `sacha9214/polymarket-fill-model`**(SCAN 5271・5277 行)。README からの一次資料の逐語(要約ではなく機能列挙): 「埋まったあとの値動き(markout)を 60・300・1800 の 3 つの窓で測る」。同じ節に「当方に無いもの…markout の 3 窓」と明記。tsv 上も `到達済み`(行 88)。**markout について、この SCAN の範囲で唯一具体的な実装の記述に到達した候補。**

**C3-14(費用の内訳・決済理由・ドローダウン)**:
- **候補 16 `Luczinsritter/event_driven_backtesting_engine`**(SCAN 844 行)。WebFetch 要約の逐語「trade journaling, risk metrics (Sharpe ratio, Sortino ratio, max drawdown, Kelly Criterion)」。**一次資料未取得(要約のみ)、星 0・フォーク 0・5 コミットの初期段階プロジェクト**(SCAN 830 行台の記載)。
- **候補 48 `BacktestingMax`**(SCAN 5698 行)。一次資料(料金ページの JS、逐語)「Trailing drawdown, daily loss limits, minimum trading days」「Trade Journal」。**登録前提の SaaS の UI 機能であり、コードの API・出力構造としての費用内訳/決済理由の記述は無い**(足の粒度のチャート型ツールで、板・待ち行列・滑り・市場影響の語は同じ資料に 0 件)。

**C3-15(動作確認/研究の実行目的の記載)**: `dry.?run|smoke.{0,3}test|paper.{0,3}(mode|trading)` に 11 件。**当方の「実行の目的(動作確認/研究)を指標の書き出しに必ず載せる」という具体の要素(構造上の強制フィールド)に一致する記述はどの候補にも無い。**近い概念(実弾/紙上の実行モードの切替)を持つ候補:
  - **候補 75 `Freqtrade`**(SCAN 300 行)。PyPI description 逐語「Dry-run: Run the bot without paying money」「Backtesting: Run a simulation of your buy/sell strategy」。
  - **候補 19 `Jesse`**(SCAN 1198 行)。「本体(バックテスト・最適化)は上限の記述なし。実弾・ペーパーは license が要る」(一次資料、docs.jesse.trade)。
  - **候補 8 `OpenTrader`**(SCAN 3823 行)。README 逐語「Paper Trading: Test your strategies without risking real money」。
  - **候補 12 `pybotters`(否定側の所見)**(SCAN 2785 行)。「paper や dry-run の模擬は道具の側に無い」(実測)。
  いずれも「実行モードの切替」であって、「1 回の実行の指標書き出しレコードに目的ラベルを構造的に持たせる」という当方の要求そのものとは形が違う(場面係が能力の場面として扱うかは場面係の役)。

**C3-16(バックテストタブ・実行一覧→項目別タブ)**: `dashboard|ダッシュボード` に 3 件、いずれも別区分に仕分け済みで、当方の「1 実行 → 項目別タブ(概要/前提/損益/…/データ品質)」という構成に対応する記述は無い:
  - `TradeSight`(SCAN 4672 行、`区分2・5・6・7 へ`)。「web dashboard」とだけ。
  - `braedonsaunders/homerun`(SCAN 4679 行、`区分1-足(推定)`+`区分2・3・5・6 へ`)。「real-time dashboard」とだけ。
  - `IsaacCheng9/order-book-simulator`(SCAN 4883 行、`区分1-板の待ち行列`+`区分5 へ`(表示))。「interactive dashboard」とだけ。
  **候補 0 件(区分1 の対象候補としては)**。表示専用の区分5(可視化)の候補であり、この委任(区分1 のバックテスト・シミュレーション道具のサーベイ)の主対象ではない。

### 3.4 「段(機構)が最も高い機構」の扱い(§3.0 のとおり尺度が無い)

C3-1〜C3-16 のどの観点にも道具台帳 §2.1 のような段の尺度は定義されていない。**根拠の無い順位付けを作ると A-12 に触れる**ため、この資料係の段階では候補と一次資料の行を列挙するに留め、「どれが最も強いか」は言わない。動かせる候補を「全部再現する」かどうかの判断と実行は、委任文 §3「調査結果の側の選び方」により場面係の役である。

### 3.5 内部制約の観点(C3-17〜C3-19)は SCAN 対象外

C3-17(日本語・CDN 不使用)・C3-18(配線の試験)・C3-19(動作確認実行の全タブ警告)は、当方のダッシュボード実装の**構造上の制約**(委任文 §4 の禁止・安全規則、artifact-design 由来の内部規約)であり、外部の道具の機構を比較する性質の観点ではない。SCAN の対象(区分1: バックテスト・シミュレーション道具の機構調査)にこれらの語を探しても意味が無いため、grep は打っていない(打たない理由を明記することで A-9 の「説明なく外す」を避ける)。この 3 観点は「調査結果の側」の欄を持たず、当方の実装が要件を満たすかどうかだけを直接判定する(場面集の規則 2「振る舞いを試し、作りの形を試さない」の範囲内)。

## 4. 当方の現状(該当箇所)

現行の唯一の実装は旧エンジン `src/bot/backtest/{engine,metrics,walk_forward}.py`。`src/bot/bt/` は項目 0(核)だけ着手済みで、`src/bot/bt/validation/`・`src/bot/bt/repro/`・`src/bot/bt/report/` は**未着手**(`find src/bot/bt -maxdepth 1` の実行結果に `core/` しか無い)。`src/bot/monitoring/backtest_view.py` も存在しない。

| 委任文の要素 | 当方の現状 | ファイル:行 |
|---|---|---|
| 暦日 Train/Val/OOS | 暦日ではなく**行数の割合**(`train_frac=0.6, val_frac=0.2`)で機械的に 3 分割するだけ。シャッフル無し・OOS は末尾固定という順序の規律はあるが、暦日境界の指定はできない | `src/bot/backtest/walk_forward.py:20-32`(`split_data`、docstring「Chronological split」) |
| walk-forward(複数回切り直し) | 1 回の 3 分割のみを行う `evaluate_on_splits` があるだけで、複数回のウィンドウを移動させる反復評価は無い | `src/bot/backtest/walk_forward.py:36-53`(`evaluate_on_splits`) |
| purge・embargo・CPCV | 無い(`walk_forward.py` 全体に purge/embargo/CPCV の実装・語が 0 件) | `src/bot/backtest/walk_forward.py`(該当なし) |
| ブロック・ブートストラップ | `src/bot/backtest/` 直下には無い。概念自体は `.claude/skills/research-protocol/SKILL.md:485,504` に規則として存在するが(「95% CI(ブロック・ブートストラップ)」)、これは**研究の個別スクリプト(`scripts/measure_katsuo_*.py` 等)が都度実装する規約であって、再利用可能なバックテストエンジンのモジュールではない** | `.claude/skills/research-protocol/SKILL.md:485`, `:504`(規則のみ。実装は無い) |
| MDE の計算 | 同上。`.claude/skills/research-protocol/SKILL.md:342-345` に規則としてあり、`scripts/preflight_prereg.py` など個別スクリプトが使うが、`src/bot/backtest/` にモジュールとしての MDE 計算関数は無い | `.claude/skills/research-protocol/SKILL.md:342-345`。`src/bot/backtest/`(該当なし) |
| deflated Sharpe・PBO | **無い**。`grep -rln "deflated\|\\bPBO\\b\|CPCV" --include=*.py --include=*.md .`(pycache 除く)の当たりは、この項目の委任文・監査記録自体を除けば 0 件。`docs/AUDITOR/VERDICTS/2026-09-23_backtest_env_prompt.md:155` に監査役の問い「`pyproject.toml` に scipy・statsmodels が無く pandas・numpy のみの現状で deflated Sharpe・PBO・CPCV・ブロック・ブートストラップの実装可能性を確認した上での制約か」が記録されている(未回答。作業者への制約と同じ依存禁止が委任文 §4 にもある) | `docs/AUDITOR/VERDICTS/2026-09-23_backtest_env_prompt.md:155`。`pyproject.toml`(scipy・statsmodels は無い) |
| 周回数の台帳(ITER) | `.claude/skills/research-protocol/SKILL.md:60` に規則として存在(「ループ回数は台帳(`ITER.md`)に累積し…」)。`src/bot/backtest/` にはこの仕組みへの参照・呼び出しは無い | `.claude/skills/research-protocol/SKILL.md:60` |
| 封印区間の 4 門 | `load_sealed` は実装済み(`src/bot/research/sealed.py:358`)。`src/bot/bt/` からの呼び出しは無い(項目 0 の核が未着手時点でこの項目に触れていないため) | `src/bot/research/sealed.py:358`(`def load_sealed`) |
| 実行記録(git SHA・差分ハッシュ・設定・データ sha256・種・版) | **無い**。`src/bot/backtest/` 配下に `sha256`・`git_sha`・`run_id` の文字列は 0 件(`grep -rn "sha256\|content.hash\|run_id\|git_sha" src/bot/backtest/ src/bot/research/ scripts/judge_gates.py` の当たり 0) | `src/bot/backtest/`(該当なし。実行のたびに何も記録に残らない) |
| 実行 ID = 内容のハッシュ | 無い(同上) | 同上 |
| 同一入力の再現性の自動確認 | 無い。1 度の実行で完結し、2 回走らせて一致を確かめる仕組みは無い(`engine.py` に乱数は使われていない=決定的ではあるが、それを**自動で確かめる**機構が別に無い) | `src/bot/backtest/engine.py`(該当なし) |
| 事前登録ハッシュの組み込み | 無い(実行記録の仕組み自体が無いため) | `src/bot/backtest/`(該当なし) |
| 分布で出す(1 件ごとの bp・分位・負の割合) | `Metrics` はすべてスカラー(`total_pnl_jpy`・`win_rate_pct`・`profit_factor`・`sharpe_ratio`・`max_drawdown_pct` など 12 個)で、1 件ごとの分布・分位は出力されない | `src/bot/backtest/metrics.py:10-23`(`class Metrics` のフィールド一覧) |
| 露出あたり(bp/時) | 無い(`Metrics` に露出時間・bp/時のフィールドは無い) | `src/bot/backtest/metrics.py`(該当なし) |
| 約定率・取り逃し | 無い(`compute_metrics` の入力は `trade_pnls` と `equity_curve` のみで、発注件数に対する約定件数の比率は計算されない) | `src/bot/backtest/metrics.py:29-31`(関数シグネチャ) |
| 逆選択 markout | 無い | `src/bot/backtest/metrics.py`(該当なし) |
| 費用の内訳 | `total_fees_jpy` の合計 1 個のみで、maker/taker/スプレッド別の内訳は出力されない(`CostModel` 側に個別フィールドはあるが `metrics.py` の出力には合算しか出ない) | `src/bot/backtest/metrics.py:23`(`total_fees_jpy: float`)、`src/bot/backtest/engine.py:98-103`(`CostModel` の内訳フィールド) |
| 決済理由(exit reason) | **トレードごとの記録には在る**(`close_position` が `reason` を `"signal"`/`"wick_stop"`/`"stop_loss"`/`"take_profit"`/`"maker_tp"`/`"time_exit"` のいずれかで付ける)が、`compute_metrics` はこの `reason` を受け取らず、決済理由ごとの集計・指標には反映されない(記録はあるが集計されていない = A-11 への牽制。存在だけで「持つ」と判定していない) | `src/bot/backtest/engine.py:228`(`def close_position`)、`:239`(`"reason": reason` を trade log に格納)、`:259,264,290,319,323,327,338`(各 `reason=` の呼び出し箇所)。`src/bot/backtest/metrics.py:29`(`compute_metrics` のシグネチャに `reason` の入力は無い) |
| ドローダウン | 在る(`max_drawdown_pct`)が、単一のスカラー(最大値)のみで、ドローダウンの時系列・分布は出力されない | `src/bot/backtest/metrics.py:17`(`max_drawdown_pct: float`)、`:49-50`(計算箇所) |
| 実行目的(動作確認/研究)の記載 | 無い(実行記録の仕組み自体が無く、`動作確認`/`研究`のラベルを持つフィールドも無い) | `src/bot/backtest/`(該当なし) |
| 「バックテスト」タブ | 無い。現行のダッシュボードのタブは「Botコンソール」「マーケット」の 2 つのみ | `scripts/dashboard.py:197-200`(`<nav class="tabs">` 内の `<button id="tab-console">`・`<button id="tab-market">`) |
| 実行の一覧→項目別タブ | 無い(実行という単位そのものが記録されていないため一覧化のしようがない) | `scripts/dashboard.py`(該当なし) |
| API のルーティング | `/api/status`・`/api/market`・`/`(index)の 3 つのみ。`/api/backtest` 相当のルートは無い | `scripts/dashboard.py:1353-1370`(`class Handler` の `do_GET`) |
| 日本語・CDN 不使用 | 既存の 2 タブは日本語で書かれており、CDN の外部読み込みは無い(`grep -c "cdn\." scripts/dashboard.py` の当たり 0)。新設するバックテストタブもこの慣行に従う制約であり、比較対象ではなく当方自身の規約 | `scripts/dashboard.py`(既存タブ全体が日本語。外部 CDN 読み込み 0 件) |
| 配線の試験 | 既存タブの配線試験は `tests/test_dashboard.py` にある(委任文 §1「材料」に列挙)。バックテストタブの配線試験は当然まだ無い | `tests/test_dashboard.py`(既存タブの範囲のみ) |
| 動作確認実行の警告表示 | 無い(実行目的のラベル自体が無いため、警告表示の判定材料も無い) | `scripts/dashboard.py`(該当なし) |

## 5. 提出前の吟味(委任文 §3「提出前の吟味」。最初に作る役の文)

固定した要件・§2 の観点(C3-1〜C3-19)を読み直し、「非常に厳しい監査役・批評家なら何を [止める] にするか」を観点ごとに列べ、返す前に潰した。

1. **C3-1〜C3-6・C3-10・C3-12・C3-16 は「候補 0 件」または弱い候補しかないまま出している。**「調査せずに『無い』と断定している」(O-2)と見えないか。→ **潰した対応**: すべての観点について、grep 語を先に書いてから実際にコマンドを打ち、コマンドと出力(当たり件数)をこのファイルに残した(O-3)。かつ、C3-2 の「purge」の 3 件がすべて `pip cache purge`(ディスク容量の話)であることを個別に確認し、「候補 0 件」と単純化せず何が当たったか・なぜ関係ないかを書いた。**この SCAN は区分 1(バックテスト・シミュレーション道具)のサーベイであり、統計手法・再現性の仕組み・ダッシュボード専用の道具を対象にしたサーベイではない。**したがって「候補 0 件」は「この材料の範囲では 0 件」であって「世の中に存在しない」ではないことを明記した(CLAUDE.md §5.2「無い・取れない」の規則。どこで・何を試したかを書く)。
2. **`mlflow` を候補番号なしのまま比較資料に混ぜてよいか。**→ **潰した対応**: `docs/DATA/tools_catalog.tsv` に名前が無いことを `grep -n mlflow docs/DATA/tools_catalog.tsv` の実行結果(当たり 0)で確認し、「候補番号なし」と明記した。Qlib(候補 21)の隠れた依存として発見された経緯、`[深掘り]` されて実測がある経緯、実行 ID が乱数でありハッシュではないという委任文との齟齬、既定で外部送信する安全側の所見も併記した。これを場面集に含めるかどうかは場面係の判断であり、資料係はここで隠さず全部の事実を渡した(A-9「説明なく外す」への牽制)。
3. **候補 15(BacktestingCore)・107(sigc)の walk-forward の記述はどちらも一次資料未読(WebFetch 要約・追跡ファイル名だけ)。**「動かしてもいないのに調査結果の側の代表として使うのは弱い相手を選ぶ操作(A-9 の裏返し)ではないか」との疑いがありうる。→ **潰した対応**: 委任文 §3「動かせない候補の検討と再現」は場面係の役であり、この資料係の段階では「機構が実在するかもしれない候補とその根拠行」を隠さず全部書くことが仕事である。15・107 のどちらも「一次資料未読」「中身は未読」という限界をそのまま書き、実装を確かめたと誤読されないようにした。
4. **候補 3(PySystemtrade)・98(limitOrderBook)の「決定的」の実測は、範囲が指値の注文模擬・遅延模型に限られる**のに、これを C3-9(実行全体の再現性の自動確認)の根拠として書くと、範囲を広げすぎではないか。→ **潰した対応**: それぞれの実測が「指値の注文模擬」「遅延の模型」という限定された範囲であることを本文に明記し、「実行記録全体のハッシュ化とは別物」と注記した(A-10「族・スコープを説明なく縮める」の逆パターン=範囲を広げすぎることへの牽制)。
5. **C3-15(動作確認/研究のラベル)に freqtrade・Jesse・OpenTrader の dry-run/paper モードを挙げたが、これは当方の要求(指標書き出しレコードへの目的フィールドの構造的強制)とは形が違う。**「違う概念を無理に候補に見せかけている」と疑われないか。→ **潰した対応**: 「いずれも『実行モードの切替』であって、当方の要求そのものとは形が違う」と明記し、場面係が能力の場面として採用するかどうかの判断に委ねる書き方にした(比較の観点自体を緩めたり厳しくしたりしていない)。
6. **C3-17〜C3-19 に grep を打たなかった理由が、単なる手抜きに見えないか。**→ **潰した対応**: これらが「外部道具の機構比較」ではなく当方の実装制約(委任文 §4・artifact-design 由来)であることを§3.5 に独立の節として明記し、「打たない理由」を書くことで A-9(説明なく外す)を避けた。観点表(§2)からは外していない。
7. **§4「当方の現状」で、決済理由(exit reason)が「トレードごとの記録にはある」ことを見落として「無い」と書きかけていないか。**→ **潰した対応**: `engine.py` の `close_position` の `reason` 引数と呼び出し箇所を file:line で確認し、「記録はあるが `compute_metrics` に集計されない」という正確な区別を書いた(A-11「目視・ぱっと見で判定する」への牽制。存在の有無だけでなく、実際に使われる経路まで確認した)。
8. **`grep -rln "deflated\|PBO\|CPCV" --include=*.py --include=*.md .` が大量のファイルを返したが、その多くはこの委任自体の文書(委任文・監査記録)であり実装ではない可能性がある。**「実装が見つかった」と誤読されないか。→ **潰した対応**: 実際に個別確認し、ヒットは `docs/AUDITOR/VERDICTS/2026-09-23_backtest_env_prompt.md` と委任文・設計文書だけで、`src/`・`scripts/` の実装コードには無いことを明記した。監査役の未回答の問い(scipy/statsmodels 無しでの実装可能性)もそのまま引用し、隠さず記録した。
