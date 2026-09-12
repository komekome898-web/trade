# 文書索引(2026-09-12 全面改訂、L-131)

**増やさない規則(新しい文書を作る前に読む)**
(i) 一度きりの納品物(計画・チェックリスト・監査・提案)は `docs/` 直下に置かず、`DISCUSSIONS/` か `AUDITOR/VERDICTS/` に日付つきで置く。
(ii) 生成物(スクリプトの出力: JSON・表)は `docs/` に書かない。`results/` へ。
(iii) 「状態」は台帳 4 本(`OWNER_STATUS` / `DATA` / `DATA_CONSUMPTION_LOG` / `NEGATIVE_FACTS`)以外に作らない。
新しい文書を作る前に、どの種類か決め、既存の文書に追記できないか先に確認する(`docs/` 直下に新規作成すると
フックがこの 3 行を表示する)。

文書は 4 種類: **状態**(いま何がどうなっているか。更新され続ける)/ **記録**(起きたことの履歴。追記のみ)/
**手順**(やり方)/ **結果**(検証・研究の成果物)。

## 状態(4 本。これ以外に作らない)
- `OWNER_STATUS.md` — オーナー側の状態板(単一の真実。指示の前に読む。恒久規則もここ)
- `DATA.md` — データ登録簿(在庫・所在・範囲、守る仕組み、損失・欠損、保持期間。旧 DATA_* 系 6 本を統合)
- `DATA_CONSUMPTION_LOG.md` — 何を見て何を選んだか(消費 vs 未消費)
- `NEGATIVE_FACTS.md` — 否定的事実(賞味期限つき)
- `PROJECT_GOAL.md` — プロジェクト目標(オーナー明示 L-097。変更はオーナーのみ)

## 記録(追記のみ・削除禁止)
- `OWNER_LOG.md` — オーナー報告・決定の台帳(L-番号)
- `INCIDENTS.md` — インシデント(I-番号)
- `DISCUSSIONS/` — 議論・事故の記録・提案(日付つき。`2026-09-04_postmortem_tp_precursor.md`、`2026-09-12_docs_reorg_plan.md` など)
- `DATA/probes/` — 調達調査のプローブ生ログ / `DATA/surveys/` — 調達調査票(清算履歴・bitFlyer 履歴・ETF 代替・G2 在庫)/
  `DATA/SCAN_<date>.md` — 市場・環境調査(`research-squad` の出力。まだ 0 件)
- `AUDITOR/` — 監査役(`owner-auditor`)の検査集合と測定: `KNOWN_ANSWERS.md`・`KNOWN_ANSWERS_ADDENDUM.md`(既知解 KA-01〜)、
  `PRINCIPLES.md`(原則 P1〜)、`before/`・`answers/`(検査集合の問題と答え)、`EVAL_<date>*.md`・`COVERAGE_<date>.md`(測定)、
  `TREND.md`(週次の傾向)、`VERDICTS/`(納品ごとの監査記録)、`PROPOSED_CHANGES_<date>.md`(定義の変更提案)

## 手順(やり方)
- `OWNER_PROCEDURES.md` — オーナー側の手順(P 番号。`/owner-procedure P<n>`)
- `OPERATIONS.md` — 運用手順(暗号資産側。フック §6.6 を含む)/ `OPERATIONS_JPX.md` — JPX 側(ON1・ETF 板寄せ)
- `DELEGATION.md` — 委任表(オーナー承認 L-009)
- `AUDITOR/IMPROVEMENT.md` — 監査役の週次改良ループ(L-116)
- `PHASE2/K1/HANDOFF.md`(K1 の入口。終了と再開条件)/ `PHASE2/K1/PREFLIGHT.md`(出荷前検査 3 層)
- `.claude/skills/` — `research-protocol`(検証の規律。旧 PHASE2_SPEC / PHASE2_TEMPLATES を吸収)・`research-squad`(調査班)・
  `delegated-study`(委任)・`owner-audit`(監査役の呼び出し)・`owner-procedure`
- `.claude/agents/` — `owner-auditor.md`(本番)・`owner-auditor-candidate.md`(測定用)
- `.claude/hooks/` — 規則を読む導線(SessionStart / UserPromptSubmit / PreToolUse)。`CLAUDE.md` は全体の入口

## 結果(検証・研究の成果物。生成物は `results/` に)
- `STRATEGY_IDEAS.md` — 戦略案(判定なし)。到達点と再開条件もここ
- `PHASE2/K1/` — K1(カツオの機構。**終了、L-118**): `RESULT.md`(第 1〜18 部)、事前登録 `PREREG.md`(古い。冒頭の注記)・
  `H1/H2/H3/H3_DECOMP/ROUND5/JUDGEMENT/FRESH_BITFLYER/XVENUE_PREREG.md`、設計 `BINANCE_PLAN.md`・`DEEPDIVE_PLAN.md`、
  検査 `AUDIT_TRIAGE.md`(1・2 回目)・`binance/CHECKS.md`
- `PHASE2/EXEC/` — ④ 執行層: `EXEC_FLOOR_PREREG.md`・`RESULT.md`(経費の床)
- `results/PHASE2/**` — 上記の生成物(JSON・`*_TABLES.md`。手で編集しない)
- `legacy/` — オーナーの旧 bot の一次資料(`katsuo_v03.py`・`matilda_*.py`)と手本(`KATSUO_INTENT_MAP.md`・`KATSUO_PARAMETER_INVENTORY.md`)
