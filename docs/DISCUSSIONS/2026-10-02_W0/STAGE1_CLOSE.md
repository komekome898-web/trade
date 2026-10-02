# 段 1 を閉じる報告(下書き): 測る道具 = 新しいバックテスト環境 `src/bot/bt`

作成 2026-10-02 UTC、レーン L4(計画 第 5 版 W0)。**下書きであり、リードが読んでから出す。** リポジトリのファイルは 1 つも変えていない(成果物はスクラッチパッドだけ)。封印の台帳に載ったデータは、この文書のためには開いていない(PC_OUTAGES.md の作業で開いたものはその文書の §0 に全部書いた)。

印: 【事実】= ファイルかコマンドの出力で確かめた(出所を同じ行に書く)/【推定】= 推論で、確かめていない /【未確認】= 確かめていない、または確かめられなかった。他の文書の数を引くときは「〜の記述」と書き、この回に数え直していない。

## 0. 着手前の表(CLAUDE.md §0.1)

| やろうとすること | オーナーの原文の該当語(逐語) |
|---|---|
| 部品ごとに「信頼できる部分 / できない部分 / 残る持ち越し」を分けて書く | 「測定器の信頼性が担保されている部分とそうでない部分を明確にした上で閉じてください。」(L-186) |
| バックテストの結果をダッシュボードで見られない原因(PC のブランチに無い・結果が git に無い)を書く | 「そのバックテストの内容を項目別にダッシュボードから確認できるよう」(L-405)/「バックテストの確認は未だにダッシュボードからできません。」(L-546) |
| ゴールの側からの要求(橋・帰属・複数の版・再生の記録・経費の模型)の状態を書く | 「最終目標は完全自動化です」(L-541)/「バックテスト環境を刷新し、信頼できるバックテストが可能な環境を構築してほしい。」(L-405) |
| 計画の精査の一部として段 1 の閉じ方を出す | 「改めて計画を精査してください。」(L-546) |
| 成果物をスクラッチパッドに書き、リポジトリを変えない | **(該当語なし)**(リードの委任文の指示) |
| 「信頼できる」の定義をこの文書で決める(下の §1) | **(該当語なし)**(L-186 の「担保されている」を、独立の確かめがあるか、で読んだのはこのレーンの判断。リードが違う読みなら §2 の表の列を入れ替える) |

## 1. この文書での「信頼できる」の意味(途中で変えない)

- **信頼できる(担保あり)** = 作った者以外の確かめがあり、その結果が記録に残っている部分。ここで数える確かめは 4 種: (a) 批評家の検査で [止める] 0、(b) 規則の文だけから書いた独立の参照(`bar_sim`)との全升の突き合わせ、(c) 変異(mutant)を殺せること、(d) 場面集(battery)の正解。
- **信頼できない(担保なし)** = 作った者の申告だけのもの。2026-09-26 の報告が「**未確認の印つき**」と書いた項目 1〜3(案 B で批評家を置かなかった)は、その後に別の確かめが入った箇所を除き、ここに入る【事実: `docs/DISCUSSIONS/2026-09-23_backtest_env/REPORT_2026-09-26.md` 17〜19 行(§1 の表)と 22 行「「未確認の印」の意味: 案 B で項目 1〜3 は批評家を置かなかったので、資料係と審査員の申告の裏取りは無い」】。
- **実データで使われたか** は別の列にした。K1 の段階 A・G(過去の研究と同じ入力を新しい環境で回し、違いを裁いた)で通った経路は「実データで当時の値と一致した、または違いの原因が分かった」経路である。一致は正しさの根拠にしない(DIFF.md の書き方に合わせる)。

## 2. 部品ごとの状態

出所の略: R5=READINESS.md §E(`docs/DISCUSSIONS/2026-10-02_round1_premortem/READINESS.md` 205〜228 行)/ R26=`REPORT_2026-09-26.md`/ RC=`item_4/round_3/REPORT_close_2026-09-27.md`/ EG=`docs/PHASE2/K1/NEWENV_G/ENV_DEFECTS.md`/ FG=`docs/PHASE2/K1/NEWENV_G/FIXES.md`/ EA=`docs/PHASE2/K1/NEWENV_A/ENV_DEFECTS.md`/ OS=`docs/OWNER_STATUS.md`。行番号は R5 から引いたものは R5 の記述、`src/` の行はこの回に `grep -n` で確かめたもの(付録 A)。

| 部品 | 信頼できる部分(担保) | 信頼できない・確かめていない部分 | 残る持ち越し |
|---|---|---|---|
| **core**(`core/`) | 項目 0 は場面集 46/46・審査員 6/6 でオーナーが通過と決めた(L-451。R26 §1 の表の「0 核」の行)【事実: R26】。`docs/DISCUSSIONS/2026-09-23_backtest_env/item_0/` に round_1〜round_17 のフォルダ、`tests/bt/critic/` に批評家の試験がある【事実: ls】。G-1 の直し(流れの名前 `Event.stream`、`CORE_VERSION = "core-20"` = `src/bot/bt/core/contract.py:15`、`events.py:165`)は直したと EG 27 行に、変異の確かめの方法は FG §0 にある【事実: 文書の記述】 | 事象の型は trade/quote/bar/book/funding/liquidation の 6 つ(`events.py` に `TradeEvent:206`・`BarEvent:266`・`FundingEvent:303`・`LiquidationEvent:315` ほか)。建玉・比率・CFTC など外部の系列を載せる型は無い(R5 の H-5)【事実: R5 と grep】。L3・FX の日替わり・分割・FX レートの型が無い(R26 §4)【事実: R26 の記述】 | 外部の系列の入口と公表の遅れ(H-5)。**注**: 作業ツリーに未追跡の `src/bot/bt/data/reference.py`(docstring に `available_at(row) = row time + declared lag`)がある。別のレーンの作業中のもので git に無いので、この表では数えない【事実: `git status --short` の `?? src/bot/bt/data/reference.py`】 |
| **data**(`data/`) | K1 段階 G で欠陥 G-1〜G-4・G-7 を直し、試験と変異で確かめ、批評家 [止める] 0(EG 25〜33 行、OS 43 行「欠陥の直しは第 2 回と批評家([止める] 0、[直す] 2 を当てた)で終わった」)【事実: 文書の記述】。範囲つき読み(`range_ns`、`repro/runner.py:71-84`)、`no_trade` の宣言(`data/spec.py:41-45`)、暗号資産・FX で `session` 必須(`spec.py:28`)【事実: grep】 | 項目 1 は「未確認の印つき」(R26 §1)。項目 1 の監査役の [聞く] 3 件(逆行の定義域・ハードリンクの穴・DATA.md §6 の抽出物を拒む側に足す)は 09-26 時点で「未着手」(R26 §4)。その後に手が入ったかは **【未確認】**(この回は追っていない) | 読みの遅さ G-6 の残り(核の値の検査・ISO 時刻の読み・数の読み。FG §9-1・§17-5)。1 行あたりの値は FG §5 の記述を参照(この回は測っていない) |
| **fill**(`fill/`) | 項目 2 の場面集 66/66・審査員 3/3(R26 §1)。統合の口から項目 2 の模型に繋いだ(i4-r2-06 の直し、OS 57 行)うえで、項目 4 の批評家 [止める] 0(RC §1 条件 5)【事実: 記述】。段階 A の D-1(足だけの銘柄の成行を「その足の終値」で約定)は直した(OS 45〜46 行)【事実: 記述】 | 項目 2 は「未確認の印つき」(R26 §1)。時刻で変わるスプレッドを足に当てる段は無い(R5 の fill 行)【事実: R5 の記述】 | `fixed.py` と `SimVenue` の統一(R26 §4)【事実: 記述】 |
| **latency**(`latency/`) | 4 つの遅れを必須で宣言(R5)【事実: R5 の記述】 | 項目 2 の一部で「未確認の印つき」。注文の応答遅延の実測は無い(R5「P13 で記録中」)。PC の `api_probe.csv` は認証つき読み取りと公開 ticker の往復で、注文の応答ではない(OWNER_PROCEDURES P13「注文応答そのものの遅延ではない」)【事実】 | 遅れの模型に入れる値の出所(段 5) |
| **costs**(`costs/`) | maker・taker の率と出所が必須、当たった費用は宣言しないと止まる(`costs/schedule.py:11-17`)【事実: grep】 | 項目 2 の一部で「未確認の印つき」。**spread は 1 つの定数**(`schedule.py:140-151`、float 1 つ)。**資金調達の価格は `FUNDING_PRICES = ("event_mark",)` だけ**(`schedule.py:116`)で、bitFlyer の履歴(mark price が無い)を流すには結合の手間が要る(R5 の H-6)。**レバレッジ手数料の模型は無い**(`grep -rn -i "leverage_fee\|レバレッジ手数料\|leverage_point" src/bot` の出力 0 行)。SFD の模型も無い(R5 の H-3)【事実】 | H-6(spread を時刻の表で、funding の価格に足の終値を)、レバレッジ手数料、SFD |
| **orders**(`orders/`) | 商品・規則・故障の注入・Kill Switch(自動で戻らない)を持つ(R5)。統合の口からの経路は項目 4 の批評家を通った【事実: 記述】 | 項目 2 の一部で「未確認の印つき」。本番の bot の注文の口とは別のコード(下の §4 の橋) | 本番と同じ規則を当てていることの突き合わせ(段 7 の橋の中) |
| **portfolio**(`portfolio/`) | 円建ての証拠金口座・清算・レバレッジ(`portfolio/account.py:24-37, 111-123`)【事実: grep】。統合の口で口座を包む(甲)の指示と批評家(OS 56 行)【事実: 記述】 | 項目 2 の一部で「未確認の印つき」。保有の日割りの費用(18 時のレバレッジ手数料)は勘定に無い(上の costs と同じ grep) | 段 5 の経費の模型 |
| **validation**(`validation/`) | 分割・パージとエンバーゴ・CPCV・ブロック・ブートストラップ・MDE と陰性/不明/陽性・deflated Sharpe・PBO・ITER・封印の門(`validation/__init__.py` の docstring)【事実】。日ブロックのブートストラップ(段階 A の D-3)は直した(OS 45〜46 行)【事実: 記述】 | 項目 3 は「未確認の印つき」(R26 §1)。段階 A では「環境の約定の模型・費用・口座(項目 2)と指標・検証(項目 3)は通っていない」(OS 46 行)【事実: 記述】。場面ごとの効果量と相関を出す道具は無い(R5) | W1 の測定器(場面の変数・時刻をずらした対照・検出力・合成データの検め 7 項目) |
| **repro**(`repro/`) | 内容ハッシュの run id、2 回実行の一致。段階 A で 234 升の 2 回の実行が byte 一致(OS 46 行)【事実: 記述】。G-3 で範囲が run_id と record.json に入る(EG 29 行)【事実: 記述】 | 項目 3 は「未確認の印つき」 | 1 セルにつき足ファイルを 2 回読む(EA の E-7)。実行記録の置き場と大きさ(EA の E-8: 46 升でディスクが尽きた)【事実: EA の記述】 |
| **report**(`report/`) | 1 取引あたり bp・分位・負の割合・markout・費用の内訳・DD(R5)【事実: R5 の記述】 | 項目 3 は「未確認の印つき」。場面ごとの表は無い(R5)。**エッジごとの損益の帰属は無い**(`grep -rn -i "attribution\|帰属\|contribution" src/bot/bt/report src/bot/bt/portfolio` の出力 0 行)【事実】 | 帰属の計算(段 4)。通貨の札(EA の E-10 = D-4)は直した(OS 45 行)【事実: 記述】 |
| **vector**(`vector/`) | 事象の経路とビット一致を試験で固定(R5)【事実: R5 の記述】 | 規則は SMA の 2 本だけで、測定器の規則は無い(R5) | 細かい足 → 粗い足の畳み(EA の E-1)は段階 A で回避した。直したかはこの回は追っていない【未確認】 |
| **pipeline**(`pipeline.py`) | 項目 4 を閉じた: 独立の参照との格子・全升一致、場面集 0〜4、mutant、批評家 [止める] 0、実データの動作確認(RC §1 の条件 4・5)【事実: RC の記述】。出所の偽装(i4-r2-03)・事前登録の hash が形だけ(i4-r2-05)・項目 2 に繋がっていない(i4-r2-06)は第 3 周で直した(OS 57 行)【事実: 記述】 | 数年 × 多系列の規模。1 分足の升で最大 4,619.9 MB・中央値 424 秒(EA の E-9)、4 本同時でメモリ上限により強制終了(EA の E-11)【事実: EA の記述】。RC の報告そのものは監査役を通していない(RC §1 条件 5「この報告は監査役を通していない」)【事実】 | 速さとメモリ(E-9・E-11)。消した 12 場面の行の走らせ直し(RC §3) |
| **compat**(`compat/`) | 旧の軸を消し、`RULES = ("spec",)` の 1 通りで、独立の参照 `bar_sim.py` と全升一致(RC §1)【事実: 記述】 | `rules`・`arithmetic` の引数と `model` の受け口が残る(i4-c-04)。`entry_sides` と `allow_short=False` の同値の場面が無い(i4-c-06)(RC §3)【事実: 記述】 | 上の 2 件。PineForge(70)とは比べていない(RC §3) |

### 2-1 部品をまたぐ持ち越し

| # | 何か | 状態 | 出所 |
|---|---|---|---|
| X-1 | 試験が封印・新鮮データのファイルを開いていた件 | 「これまでの全試験の実行(項目 4 を閉じたときの 20598 passed を含む)はこれらのファイルを開いていた(試験のコードで確認。どの実行で何行読んだかは未確認)」→ 第 2 回で直し、`tests/bt` は門の下で「止めた open 0」【事実: OS 44 行と 43 行の記述】。直す前の実行で何行読んだかは **【未確認】**(OS 44 行のとおり) |
| X-2 | 段階 G で境以降の行を値まで読んだ件(Binance 2023) | 封印を破ったかはオーナーに上申中(L-499d)【事実: DIFF.md §5、FG §19-1 の記述】 |
| X-3 | 第 18 部(Bybit → bitFlyer)は測らない、入力の Bybit 1 分足がディスクに無い(G-5) | 直していない(G-5 は環境の欠陥ではない)【事実: EG 31 行】 |
| X-4 | 外部の道具との直接の数の突き合わせ | 参照実装 `bar_sim` と backtesting.py 0.6.6 だけ(R26 §5)【事実: 記述】。PineForge とは比べていない |
| X-5 | 項目 1〜3 の批評家による裏取り | していない(R26 63 行「項目 1〜3 の批評家による裏取り(案 B)」)。その後 K1 段階 A・G で実データの経路として使われた部分だけが、当時の値との一致・違いの裁きを経た【事実: 記述】 |
| X-6 | 読みの遅さ・メモリ | G-6 の残り、E-9・E-11【事実: 記述】 |

### 2-2 試験の構成(件数は書かない。CLAUDE.md §3)

`tests/bt/` の下に `battery/`(場面集)・`critic/`(批評家が足した試験)・`item_0/`〜`item_4/`(項目ごと)がある【事実: `ls tests/bt`】。G-7 の試験は `tests/bt/item_1/test_i1_fix_g7_range_before_values.py`(EG 33 行)。実データを読む 2 ファイル(`tests/bt/item_2/test_i2_real_data_check.py`・`tests/bt/item_4/test_i4_real_data_smoke.py`)は段階 G の門が許さないファイルを開くので、段階 A の門の下で別に回した(FG §9-3・§14 の記述)【事実: 記述】。

## 3. ダッシュボード(L-405 の 2 文目)

1. **バックテストのタブは作業ブランチにあり、PC のブランチに無い**【事実】。PC のブランチ `origin/claude/bitflyer-trading-bot-hhxxaf`(先端 2807fdda、2026-10-02 00:32 UTC)の `src/bot/monitoring/` には `aggregate.py`・`decision_text.py`・`gates.py`・`market_view.py`・`notifier.py`・`status.py` だけで `backtest_view.py` が無く、`src/bot/bt/` のファイルは 0 本。作業ブランチの HEAD には `src/bot/monitoring/backtest_view.py` と `src/bot/bt/` の 81 本がある(付録 A)。計画 第 5 版 §8 の 1 と同じ事実をこの回に打ち直した。
2. **実行の結果は git に無い**【事実】。`git ls-files backtest_runs | wc -l` → `0`。中身は `k1_env_fixes`・`k1_newenv_a`・`k1_newenv_g`・`k1_newenv_g_close` の 4 つで(`du -sh backtest_runs` → `950M`)、`git status --short --ignored backtest_runs` → `!! backtest_runs/`(全体が無視されている)。確かめた 1 つでは、実行のフォルダの中の `.gitignore`(`*`)が理由だった(`git check-ignore -v --no-index backtest_runs/k1_newenv_a/x` → `backtest_runs/k1_newenv_a/.gitignore:2:*`。他の 3 つは確かめていない)。コードを PC に入れても、表示するものが届かない。
3. **別のレーンで直している**【事実: `git status --short`】: `M scripts/dashboard.py`・`M src/bot/monitoring/backtest_view.py`・`M tests/test_dashboard.py`・`?? scripts/share_backtest_runs.py`・`?? tests/test_share_backtest_runs.py` が作業ツリーにある(計画 第 5 版 W6「実行結果の要約(表示に要るファイルだけ)を git で共有する形を決め、封印の期間にかかる実行は除く」)。差分の中身はこのレーンでは読んでいない。PC に届くのは W7(PC のブランチを作業ブランチの先端に進める、オーナーの承認)の後【事実: 計画 第 5 版 290〜291 行】。
4. 段 1 として閉じられるのは「タブのコードがある」まで。**オーナーが PC で見られる状態は W6・W7 の後**で、それまで L-405 の 2 文目は満たしていない【推定: 上の 1〜3 からの帰結】。

## 4. ゴールの側からの要求(計画 第 5 版 段 1 の 246 行)の状態

| 要求 | どの段 | いまの状態 | 出所(コマンドと出力は付録 A) |
|---|---|---|---|
| 研究と本番を同じコードで動かす橋 | 段 7 | **無い**。本番の bot は 1 プロセスに戦略 1 つで、登録表 `STRATEGIES`(`src/bot/strategy/__init__.py:11-19`)から選ぶ(`src/bot/main.py:158` `strategy_cls = STRATEGIES[strat_name]`)。登録表に研究の口の戦略 `k1_wick`・`k1_xvenue` は無い。`k1_wick.py:39-43` は `bot.bt.core.Strategy` の上に書かれている【事実】。加えて、PC のブランチに `src/bot/bt` が無い(§3-1)ので、今は同じコードを PC で動かす前提も無い【事実】 | 計画 第 5 版 段 7・W5 |
| エッジごとの損益の帰属 | 段 4 | **無い**: `grep -rn -i "attribution\|帰属\|contribution" src/bot/bt/report src/bot/bt/portfolio` → 0 行【事実】。合成器もまだ無い | 段 4 |
| 複数の版の paper | 段 7 | **無い**: 上の 1 プロセス 1 戦略【事実】。PC 1 台で回せるかは未見積り(計画 第 5 版 §7)【未確認】 | W5 |
| 本番の期間を再生できる記録 | 段 7・8 | **一部ある**: bot の判断の記録に 1 分ごとの `indicator_values`(例: `{"leader_mom_pct": …, "leader_close": …, "close": …}`)が入る【事実: PC の共有 `paper_logs/bot.jsonl` の最終行の鍵】。PC の WS 記録(気配・約定・板)と、清算・国内の取引所の記録もある【事実: 共有の一覧】。**無いもの**: Binance の値を受け取った時刻(leader の受信の遅れ)、秒単位の Binance の流れ(計画 第 5 版 W2 の 2)。新しい環境の data 層で bot の記録をそのまま読む口(spec)は、この回は確かめていない【未確認】。再生の対象期間は封印 P2-08b にかかる(計画 第 5 版 W4 の注) | W2・W4 |
| レバレッジ手数料と資金調達の模型 | 段 5 | **新しい環境**: 資金調達は `FundingEvent` と `FundingRule(price="event_mark")` だけ(`costs/schedule.py:116-129`)、レバレッジ手数料は無い(grep 0 行)【事実】。**本番の bot の設定**: `config/products.yaml:19` の FX_BTC_JPY は `swap_daily_pct: 0.06` の 1 本(16〜17 行の注釈は「a funding rate settles every 8h」= 資金調達は 8 時間ごとに決済、とあり、それを 1 日の率 1 本で近似している)で、資金調達とレバレッジ手数料を分けていない【事実】。料率の適用範囲(売りの建玉にかかるか)は **【未確認】**(計画 第 5 版 §段5 の表) | 段 5・W2 |

## 5. 閉じ方の提案(リードが決める)

- 段 1 は「上の表で信頼できる部分を研究に使う。信頼できない部分を使う測定は、使った部品の名前を測定の記録に書く」として閉じる、が L-186 の形に一番近い【推定】。どの部品を W1 の前に作り直すか(costs の H-6、data の H-5)は計画 第 5 版の段 1「足りない部品は、要る段の前までに作る」に従う。
- 項目 1〜3 の批評家の裏取りを今からするかは、このレーンでは決めない(新しい監査の層を足さない = F6・F7 との兼ね合い)。

## 付録 A: この回に打ったコマンドと出力(要点)

```
$ git ls-tree -r --name-only origin/claude/bitflyer-trading-bot-hhxxaf -- src/bot/monitoring src/bot/bt
src/bot/monitoring/__init__.py
src/bot/monitoring/aggregate.py
src/bot/monitoring/decision_text.py
src/bot/monitoring/gates.py
src/bot/monitoring/market_view.py
src/bot/monitoring/notifier.py
src/bot/monitoring/status.py
$ git ls-tree -r --name-only origin/claude/bitflyer-trading-bot-hhxxaf | grep -c "^src/bot/bt/"
0
$ git ls-tree -r --name-only HEAD | grep -c "^src/bot/bt/"
81
$ git ls-tree --name-only HEAD src/bot/monitoring/ | grep backtest
src/bot/monitoring/backtest_view.py
$ git ls-files backtest_runs | wc -l
0
$ git status --short --ignored backtest_runs
!! backtest_runs/
$ git check-ignore -v --no-index backtest_runs/k1_newenv_a/x
backtest_runs/k1_newenv_a/.gitignore:2:*	backtest_runs/k1_newenv_a/x
$ du -sh backtest_runs
950M	backtest_runs
$ grep -rn -i "attribution\|帰属\|contribution" src/bot/bt/report src/bot/bt/portfolio
(出力なし)
$ grep -rn -i "leverage_fee\|レバレッジ手数料\|leverage point\|leverage_point" src/bot
(出力なし)
$ grep -n "FUNDING_PRICES\|class FundingRule" src/bot/bt/costs/schedule.py
116:FUNDING_PRICES = ("event_mark",)
120:class FundingRule:
$ grep -n -i "funding\|0.06" config/products.yaml
16:# SFD no longer exists; a funding rate settles every 8h (05/13/21 UTC,
17:# /v1/getfundingrate). Measured mean |rate| ~0.02%/8h; swap_daily_pct models
19:FX_BTC_JPY: {market_type: FX,   min_size: 0.001, taker_fee_pct: 0.0,  shortable: true,  leverage: 2, swap_daily_pct: 0.06}
$ grep -n "strategy_cls = STRATEGIES" src/bot/main.py
158:        strategy_cls = STRATEGIES[strat_name]
$ grep -n "CORE_VERSION" src/bot/bt/core/contract.py
15:CORE_VERSION = "core-20"  # core-20: Event.stream (G-1 of K1 stage G, 2026-10-01)
$ git status --short   (抜粋)
 M scripts/dashboard.py
 M src/bot/monitoring/aggregate.py
 M src/bot/monitoring/backtest_view.py
 M tests/test_dashboard.py
?? scripts/share_backtest_runs.py
?? src/bot/bt/data/reference.py
?? tests/test_share_backtest_runs.py
```

- `src/bot/main.py:157` という計画 第 5 版の行番号は、作業ツリーでは `strategy_cls = STRATEGIES[...]` が 158 行目【事実: 上の grep】。1 行ずれているのは作業ツリーの版の違いと読む【推定】。
