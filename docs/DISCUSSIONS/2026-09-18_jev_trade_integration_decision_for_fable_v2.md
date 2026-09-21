# Jev 導入検討資料 — `trade` エージェント基盤の高速化・監査精度向上・監査回数削減

- 対象: `komekome898-web/trade`
- 対象ブランチ: `claude/bitflyer-trading-bot-hhxxaf`
- 作成日: 2026-09-18
- 読者: Fable（導入可否・設計方針の検討用）
- 目的: Jev を `trade` の指揮・調査・監査エージェントの補助ツールとして導入する価値があるかを判断する
- 重要: 本資料は「Jevを使うこと」自体を目的にしない。**監査精度を上げながら重い監査回数を減らし、作業速度・効率・トークン効率も改善できるか**を評価する。

---

# 0. この検討で最優先する目的

Jev 導入の目的は以下の4点である。

1. **監査精度の向上**
2. **監査回数の減少**
3. **作業速度・作業効率の向上**
4. **LLMトークン消費の削減**

特に、1と2を**同時に達成すること**を最重要条件とする。

単純に監査を増やして精度を上げる案は不採用。
単純に監査を減らしてコストを下げる案も不採用。

狙う形は次である。

```text
現状:
成果物
  ↓
重いLLM監査
  ↓
修正
  ↓
再監査
  ↓
必要ならさらに監査

目標:
作業中に deterministic checks + Jev の軽量連続チェック
  ↓
問題候補を早期検出・修正
  ↓
成果物完成
  ↓
リスクが高いものだけ重い owner-auditor
  ↓
原則 1 回で閉じる
```

つまり目標は、

> **監査を減らすために監査を弱くするのではなく、監査が必要になる前に問題を潰し、重い監査を選択的にする。**

---

# 1. Executive Decision Frame

## 1.1 現時点の暫定判断

Jev を導入候補として実験する価値はある。

ただし、

- Lead の代替
- research-squad の代替
- owner-auditor の代替

として導入するべきではない。

最も有望なのは、Jev を各Agent共通の **低コスト・低遅延・型付きの判断レイヤー**として追加すること。

```text
deterministic code
    = 絶対に機械判定できる規則

Jev
    = 狭い・頻繁・曖昧な判断
      classify / route / score / verify

LLM Agent
    = 深い推論、探索、説明、文章生成

Owner
    = 高影響・不可逆判断
```

[S1][R1][R5]

---

## 1.2 導入成功の定義

Jev導入後に、最低限次が同時に成立すること。

### MUST

- owner-auditor の**見逃し率が悪化しない**
- 納品後のOwner訂正件数が悪化しない
- 重いLLM監査の呼び出し回数が減る
- 監査の再実行回数が減る
- LLM入力トークンが減る
- agent task completion time が短くなる
- Owner approval / irreversible gateをJevが代替しない

### SHOULD

- full capture率が上がる
- false positiveが増えない
- 1成果物あたりOwnerへ到達する指摘件数が減る
- 同じミスを成果物完成前に検出できる
- research-squadの探索幅を狭めずに精読量を減らせる

---

# 2. 現行監査システムの実測ベースライン

`docs/AUDITOR/TREND.md` の現行記録では、2026-09-11の盲検評価は次の通り。

| 指標 | 現行値 |
|---|---:|
| 事例 | 28 + 対照3 |
| Full capture | 46.4% |
| Partial | 21.4% |
| Miss | 32.1% |
| Owner到達負荷 | 4.8件 / 成果物 |
| 監査コスト | $0.41 / 回 |

[R1]

重要なのは、現行監査が「十分完成している」状態ではないこと。

特に **見逃し32.1%** が残る。

したがってJev導入の目的は、

```text
$0.41 → 安くする
```

だけではない。

より重要なのは、

```text
32.1% miss
↓
低下させる
```

こと。

---

# 3. 現行プロセスに「監査回数が増えやすい理由」がある

現在のowner-auditは、成果物完成後に問題を検出する。

```text
作成
↓
audit
↓
質問
↓
修正
↓
再確認
```

になる。

実際 `owner-audit/SKILL.md` では、

- 問い1つずつに応答
- 止めるが残れば納品不可
- 直すは修正
- 聞くは上申またはLead判断

という構造。

[R4]

この方式自体は必要だが、欠陥が成果物完成後まで残るほど、

- audit run
- repair
- re-read
- second audit
- Lead response

が増えやすい。

### Jevの本当の価値候補

**最後の監査を安くすることではなく、最後の監査に問題を持ち込む件数を減らすこと。**

---

# 4. Jev について公式情報から確認できること

## 4.1 Jev の設計目的

TypeSafeはJevを、

> unstructured state → typed probabilistic decisions

として設計している。

特徴:

- 出力候補を事前定義
- typed output
- decisionごとのprobability / confidence
- 複数の独立した判断を一度に出力
- parallel sampling
- classify / route / score / branch / verify / guardrail 向け
- string generationを捨てている

[S1]

これは `trade` の、

```text
Owner approval required?
Scope drift?
Audit needed?
Primary source?
P1 risk?
Needs human review?
```

のような小判断と相性が良い。

---

## 4.2 速度と料金

TypeSafe公称:

- Input: **$0.042 / 1M tokens**
- Output: **無料**
- End-to-end: **70ms〜500ms**
- System-One-shaped queriesではLLMより大幅な速度・コスト差が出ると主張

[S1]

ただし、これはTypeSafe自身の計測である。

TypeSafe自身もworkflow evalについて、

- workflowはmodel capabilities teamが作った
- biasが存在しうる

と明記している。

[S1][S4]

したがって `trade` においてはVendor benchmarkを採用根拠とせず、private evalで判断する。

---

## 4.3 Agent Trace Observability

TypeSafeは公式workflowとして `Agent Trace Observability` を公開している。

入力:

- agent instructions
- prompt / rules
- conversation
- tool calls
- tool arguments
- tool results
- final message
- feedback

出力:

- AUTO-CLOSE
- NOT A BUG
- HUMAN REVIEW
- PRIORITY REVIEW
- FILE ISSUE
- ROUTE PAGE ON-CALL

[S2]

特にworkflowの最初に、

**不可逆操作に対するPermission確認**

を置いている。

これは `trade` の権限モデルと直接対応する。

```text
Owner
  >
Auditor
  >
Lead
  >
Subagent
```

および、

- 実弾
- 資本
- 口座
- 新市場
- risk limit

はOwnerのみ、という既存設計。

[R5]

---

# 5. Jev導入の中心仮説

## H1 — 監査精度向上

成果物完成時の1回のLLM監査だけでなく、

```text
作業開始
↓
途中判断
↓
調査終了
↓
測定終了
↓
報告生成
```

の各段で軽量チェックを行うことで、
成果物に残る欠陥数を減らせる可能性がある。

---

## H2 — 監査回数削減

Jevが常時shadow-checkを行い、単純な欠陥を成果物完成前に潰せるなら、

```text
owner-auditor
↓
修正
↓
owner-auditor
```

という再監査ループを減らせる可能性がある。

最終的には、

```text
低risk成果物
→ deterministic + Jev
→ full owner-auditorを省略可能か検証

中risk成果物
→ targeted owner-auditor

高risk成果物
→ full owner-auditor
```

というrisk-based audit routingを狙う。

**ただし、この省略はshadow evalで安全性を実証してからのみ。**

---

## H3 — 作業速度・効率

Jevが、

- routing
- source triage
- audit priority
- permission suspicion
- scope drift suspicion

を低遅延で返せば、
LLMが毎回長い規則を読み直して判断する回数を減らせる可能性がある。

---

## H4 — トークン削減

現状ではLLMが、

- 全原則
- 全成果物
- 関連台帳
- tool trace

を読む必要がある。

Jevで先に、

```text
P1 high
P2 low
P6 medium
P9 high
```

などを出し、関連箇所だけowner-auditorへ渡せれば、
LLM contextを減らせる可能性がある。

---

# 6. 監査精度向上と監査回数削減を両立する設計

ここが本提案の中核。

## 6.1 悪い設計

### A. 監査を全部Jevへ置換

```text
artifact
↓
Jev
↓
PASS
```

問題:

- repo横断探索が弱い
- 新しい問いを生成できない
- file:lineで説明できない
- 未知の失敗への対応力が弱い
- false negativeがそのまま納品へ流れる

不採用。

---

### B. 既存監査にJev監査を追加するだけ

```text
Jev audit
↓
Sonnet audit
↓
Lead audit
```

問題:

- 監査回数が増える
- トークンは減らない
- 作業時間も増える

目的と逆。

不採用。

---

## 6.2 推奨設計: Continuous Lightweight Assurance

```text
                  ┌─────────────────────────┐
                  │  作業中                  │
                  │ deterministic + Jev     │
                  │ 小さな判断を常時チェック │
                  └────────────┬────────────┘
                               │
                               ▼
                          成果物完成
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
                 low risk             elevated risk
                    │                     │
                    ▼                     ▼
          sampled / no full audit    owner-auditor
                                          │
                                          ▼
                                    one-pass closure
```

### ポイント

Jevは「監査を追加する」のではない。

**重い監査を呼ぶ必要のある成果物を減らす。**

---

# 7. どの段階でJevを使うか

## 7.1 Lead — Pre-action Decision Check

Leadが行動を決めた後、実行前にJev。

Questions:

```text
owner_approval_required?
irreversible_action?
scope_change?
research_squad_required?
owner_audit_required?
prereg_required?
external_verification_required?
```

### 期待効果

- permission missを事前検出
- scope driftを事前検出
- Agent routing高速化
- CLAUDE.md / DELEGATIONの長文読み返し回数削減

### 最終authority

Lead / Owner。

Jevはadviser。

---

# 8. research-squad — Source Triage

現行 research-squad はwidth-sweepを重視している。

[R3]

したがって、

```text
Jevで検索前に候補を減らす
```

は禁止。

正しくは、

```text
width-sweep
↓
広く取得
↓
Jevで全件分類
↓
上位候補をLLM精読
```

### Jev questions

```text
source_type:
  PRIMARY / SECONDARY / COMMUNITY / UNKNOWN

relevance:
  HIGH / MEDIUM / LOW

needs_probe:
  YES / NO

needs_alternative_route:
  YES / NO

likely_duplicate:
  YES / NO
```

### 期待効果

- 検索幅維持
- 精読件数減少
- 一次資料候補の優先
- LLM token削減
- 調査時間削減

---

# 9. delegated-study — Process Guard

研究・実装AgentにはJevを直接「判断者」にしない。

代わりにtraceから、

```text
prereg_deviation?
required_artifact_missing?
intent_map_missing?
forbidden_decision_written?
scope_changed?
unexpected_network_use?
commit_or_push_attempted?
```

を検査。

### 期待効果

成果物監査で初めて発見するのではなく、
**作業中またはrun終了直後に逸脱を検出**。

これは監査回数削減に直接効く可能性がある。

---

# 10. owner-auditor — Screening + Focused Audit

現行owner-auditorは、

- Read
- Grep
- Glob
- Bash
- repo横断照合
- line-specific question generation

を行う。

[R2]

これはJev単体では置換しない。

Jevは前段で、

```text
P1_negative_claim_scope
P2_definition_provenance
P3_family_completeness
P4_average_total
P5_counting
P6_missing_why
P7_external_options
P8_rule_execution
P9_scope_criterion
...
```

を確率で返す。

### 例

```text
P1: 0.94
P2: 0.08
P6: 0.72
P9: 0.81
```

owner-auditorは、

- P1関連箇所
- P6関連箇所
- P9関連箇所
- Jev uncertain箇所

を重点的に読む。

---

# 11. 監査回数を減らすための3段階routing

## Tier 0 — Deterministic only

例:

- count mismatch
- duplicate definition
- missing required field
- missing file
- forbidden commit/push
- Owner gateの明示的違反

コードで判定。

Jev不要。

---

## Tier 1 — Jev low-risk

条件例:

- deterministic failなし
- Jev全主要riskが低い
- unknown/uncertainなし
- 過去にhigh-risk artifact typeではない

処理:

```text
full owner-auditorを毎回呼ばない
↓
一定割合だけrandom sample audit
```

### なぜrandom sampleが必要か

JevがPASSしたものを全く監査しなくなると、
Jevのfalse negativeを測れない。

したがって、

```text
Jev PASS
↓
大部分はfast path
一部はblind sample
```

の設計を検討する。

具体率は事前に決めず、eval結果で決める。

---

## Tier 2 — Targeted audit

Jevが一部riskだけ高い場合。

```text
P1 high
P6 low
P9 low
```

なら、

owner-auditorへ全PRINCIPLESを渡すのではなく、
P1 + 周辺context +必要ファイルを中心に渡す。

目的:

- token削減
- speed向上
- false positives削減

---

## Tier 3 — Full audit

以下は従来通りフル監査。

- prereg
- final research judgement
- Owner判断に直結
- 新しい原則領域
- Jev uncertainty高
- permission concern
- hard-to-reverse change
- 過去incidentと同型
- sample auditでmissが増加

---

# 12. 「監査精度↑ + 監査回数↓」を実証する評価設計

## 12.1 比較群

### A — Current

```text
現行 owner-auditor
```

### B — Jev Added

```text
Jev
→ 全件 owner-auditor
```

これは精度確認用。
本番目標ではない。

### C — Jev Routed Hybrid

```text
deterministic
→ Jev
→ risk-based routing
→ targeted / full owner-auditor
```

これが本命。

---

## 12.2 必須KPI

### Quality

- Full capture rate
- Partial capture rate
- Miss rate
- Owner post-delivery corrections
- false positive
- unknown / abstain rate

### Audit count

新しく必ず測る。

- full owner-auditor calls / artifact
- targeted audit calls / artifact
- re-audit calls / artifact
- total heavy audits / week
- artifacts closed in one audit
- artifacts closed without full audit
- sampled PASSで後から問題が見つかった割合

### Efficiency

- Lead wall-clock completion time
- research wall-clock
- audit wall-clock
- token input/output
- upper-model token usage
- subagent token usage
- Jev input tokens
- total $ / artifact

---

# 13. 採用判定で最も重要な複合条件

監査回数だけ下がれば成功、ではない。

例えば、

```text
audits -40%
miss +10%
```

は失敗。

逆に、

```text
miss -20%
audits +50%
```

も今回の目的には失敗。

したがって採用条件は最低でも以下。

```text
Miss_new <= Miss_current
AND
OwnerCorrections_new <= OwnerCorrections_current
AND
HeavyAuditCalls_new < HeavyAuditCalls_current
```

さらに、

```text
Token_new < Token_current
TaskTime_new < TaskTime_current
```

を狙う。

最も望ましいのは、

```text
Miss ↓
Heavy audits ↓
Owner corrections ↓
Tokens ↓
Time ↓
```

の同時改善。

---

# 14. 最初の実験は `JEV-TRACE-001`

いきなり監査省略はしない。

## Phase 1 — Shadow

すべてのAgent runをJevが観測する。

```text
Lead
Research
Delegated Study
Owner Auditor
      │
      ▼
trace capture
      │
      ▼
redaction
      │
      ▼
Jev
      │
      ▼
NORMAL / REVIEW / PRIORITY / POSSIBLE_BREACH
```

本番挙動には影響ゼロ。

---

## 14.1 まず過去incidentで検証

既存の、

- I-xxx
- KA-xx
- AUDITOR before/answers
- Owner corrections

をeval datasetにする。

見るもの:

- incident前にJevがflagできたか
- normal runへのfalse positive
- probability calibration
- alert volume

---

# 15. Phase 2 — Audit Pre-screen

まだ監査回数を減らさない。

```text
Jev
↓
owner-auditor
```

で全件実施。

目的:

- Jevのrisk scoreと実際のauditor findingの相関を見る
- Jev PASS側のmissを測る
- targeted contextでowner-auditor精度が上がるか見る
- token削減量を見る

---

# 16. Phase 3 — Controlled Audit Reduction

Phase 2で十分な結果が出た場合だけ、

```text
low risk
→ full auditを一部sample化

medium
→ targeted audit

high
→ full audit
```

へ移る。

この段階で初めて「監査回数削減」を有効化する。

---

# 17. 監査回数を減らすときの安全装置

## 17.1 Random sampling

fast pathへ流した成果物の一部を、
Jev scoreをowner-auditorに見せず盲検監査。

目的:

Jev false negativeの継続測定。

---

## 17.2 Automatic fallback

以下で即座にfull auditへ戻す。

- Owner correction増加
- miss増加
- Jev API error
- schema change
- model version change
- confidence distribution shift
- unknown率増加
- new incident class
- eval regression

---

## 17.3 Model/version記録

floating aliasだけに依存しない。

利用可能ならmodel/version idを記録し、
変更前後を区別できるようにする。

---

# 18. トークン削減の設計

## 現在

owner-auditorが広いcontextを読む。

## 目標

```text
artifact
↓
deterministic extraction
↓
Jev classification
↓
relevant sections only
↓
owner-auditor
```

例えば、

```text
全2000行
↓
JevがP1/P6関連箇所をflag
↓
owner-auditorは必要context中心
```

を目指す。

ただし、context削減により跨ぎ矛盾を落とす可能性があるため、
full-context random auditを残す。

---

# 19. 作業速度向上の設計

Jevを待ち工程にしない。

可能なら、

```text
LLM作業
├── deterministic checks
└── Jev checks
```

を並行。

Jevが遅い場合でも、
LLM作業を止めない。

最終routing直前に結果を使う。

---

# 20. TypeSafe APIをhard safetyへ入れない

TypeSafe status pageでは2026-09-15更新時点の30日uptime:

- `api.typesafe.ai`: **99.858%**
- `console.typesafe.ai`: **99.985%**

[S3]

この数字は通常利用には参考になるが、

```text
Jev unavailable
↓
Owner gate failure
```

にしてはいけない。

禁止依存:

- LIVE
- Kill Switch
- risk limits
- capital
- account
- irreversible action approval
- git protection
- order state

---

# 21. Data / Privacy / Contract

## 21.1 Customer Data

TypeSafe MCAによれば、Inputはサービス提供に必要な範囲で処理される。

Customer Dataをmodel weightsのtraining datasetへ入れることは、
Customerの事前同意なしには行わない、としている。

一方でTelemetryはサービス改善等に使用可能。

[S5]

従ってAgent traceを送るなら、

- API keys
- `.env`
- secrets
- credentials
- private tokens
- unnecessary full file bodies

はredactする。

---

## 21.2 Benchmark公開制限

TypeSafe MCA §2.3(f)は、
Servicesについてbenchmark / performance informationを公開することを禁止している。

[S5]

したがって、

```text
Jev vs Sonnet
capture
latency
cost
```

のprivate evalは必要だが、
契約確認までは結果をpublic GitHubへそのままcommitしない。

これは重要。

---

# 22. 実装候補

共通wrapper:

```text
tools/jev/
├── client.py
├── redact.py
├── trace_schema.py
├── commander_schema.py
├── research_schema.py
├── audit_schema.py
└── logger.py
```

Agent側から直接SDKを呼ばせない。

例:

```text
jev_decide("trace/review", state)
jev_decide("lead/pre_action", state)
jev_decide("research/source_triage", state)
jev_decide("audit/principle_screen", state)
```

効果:

- API変更を一箇所で吸収
- version記録
- timeout統一
- redaction統一
- disable可能
- shadow / active切替
- mock test可能

---

# 23. Fableに判断してほしい核心

## 最重要

**Jevを入れることで、重い監査を増やさずに精度を上げられるか。**

具体的には、

```text
Continuous light assurance
+
Risk-based heavy audit
```

がこのプロジェクトに成立するか。

## Architecture

- trace取得点はどこが最小侵襲か
- `.claude` hooks依存にするべきか
- Python wrapperかMCP/toolか
- API failure時のbehavior
- model/version記録
- redaction
- local cache

## Audit reduction

- どの成果物ならfull owner-auditorを省略候補にできるか
- low-risk判定の最低条件
- random sample audit率
- full auditへ戻すrollback条件
- targeted auditに必要なcontext

## Evaluation

- KNOWN_ANSWERSをどうblind evalへ利用するか
- I-xxxをtrace datasetへ変換する方法
- Owner correctionをground truthとしてどう使うか
- unseen incidentへのgeneralizationをどう測るか
- miss率とaudit call数をどう同時最適化するか

---

# 24. 推奨導入順

## Step 1 — `JEV-TRACE-001`

- shadow only
- 全Agent
- no behavior change

## Step 2 — `JEV-AUD-PRESCREEN-001`

- 全audit前にJev
- full owner-auditorはまだ維持
- correlation / miss / token測定

## Step 3 — `JEV-AUD-ROUTER-001`

- low / medium / high routing
- lowはsample
- medium targeted
- high full

ここで初めて監査回数削減。

## Step 4 — `JEV-RES-001`

- source triage
- search widthは維持

## Step 5 — `JEV-CMD-001`

- Lead pre-action adviser
- authorityなし

---

# 25. 導入判断

## 導入価値: あり

ただし理由は「Jevが安いから」ではない。

最も重要な可能性は、

> **成果物完成後に重い監査を何度も回す方式から、作業中の軽量連続保証 + 必要時のみ重い監査へ移行できること。**

これが実現すれば、

- 監査精度向上
- 監査回数削減
- 作業速度向上
- 作業効率向上
- トークン削減

を同時に狙える。

---

# 26. 採用しない条件

次のどれかが起きるなら本番導入しない、またはrollback。

- Missが増える
- Owner訂正が増える
- Heavy audit回数が減らない
- Jev alert処理でLead作業が増える
- false positiveで監査量が増える
- search scopeが狭くなる
- Jev confidenceにAgentがanchoringする
- TypeSafe API障害でworkflowが止まる
- secret / trace redactionに不安が残る
- model updateの挙動変化を管理できない
- private evalを安全に保存できない

---

# 27. Fable向け最終タスク

この資料を前提に、Fableには以下を判断してほしい。

1. Jev導入で「監査精度↑ + heavy audit回数↓」が構造的に可能か
2. 現行 `trade` のどのhook / trace / skill pointへ最小変更で入れられるか
3. `JEV-TRACE-001` の具体設計
4. private eval datasetの作り方
5. audit reductionを開始できる条件
6. rollback条件
7. public repoへ残してよい情報 / 残さない情報
8. 実装前にOwner承認が必要な変更箇所
9. 導入しない方が合理的なら、その理由と代替案

**重要:**
Jev採用を前提に結論しない。
既存のdeterministic check / Sonnet owner-auditor / process metricsの改良だけで同じ目的が達成できるなら、それも比較対象にする。

---

# 28. Sources

## TypeSafe / Jev

### [S1] TypeSafe — Introducing System One Models and Jev
Published 2026-09-14.

Claims used:
- typed probabilistic decisions
- string generationを捨てる設計
- parallel sampling
- classify / route / score / verify / guardrail用途
- $0.042 / MTok
- output free
- 70ms–500ms vendor-reported latency
- vendor workflow eval limitations

https://typesafe.ai/blog/introducing-system-one-models-and-jev

### [S2] TypeSafe Evals — Agent Trace Observability
Claims used:
- instructions + conversation + tool calls + outputs + final responseを入力
- human review / priority review / on-call routing
- irreversible action permission check

https://evals.typesafe.ai/agent_trace_observability

### [S3] TypeSafe Status
Checked 2026-09-18.
Displayed 30-day uptime:
- api.typesafe.ai 99.858%
- console.typesafe.ai 99.985%

https://status.typesafe.ai/

### [S4] TypeSafe — Lies, Damned Lies, and Benchmarks
Used for:
- public/vendor benchmarksをそのまま採用根拠にせずprivate evalを重視する考え方

https://typesafe.ai/blog/antibenchmaxxing

### [S5] TypeSafe Master Customer Agreement
Last updated 2026-08-27.

Used for:
- Customer Data treatment
- no model-weight training on Customer Data without prior consent
- Telemetry provisions
- §2.3(f) benchmark/performance information publication restriction
- API updates may affect compatibility

https://typesafe.ai/legal/mca

## `trade` repository

### [R1] `docs/AUDITOR/TREND.md`
Used for:
- 2026-09-11 auditor baseline
- full capture 46.4%
- partial 21.4%
- miss 32.1%
- 4.8 findings/artifact
- $0.41/audit
- process metrics

https://github.com/komekome898-web/trade/blob/claude/bitflyer-trading-bot-hhxxaf/docs/AUDITOR/TREND.md

### [R2] `.claude/agents/owner-auditor.md`
Used for:
- owner-auditor role
- Read/Grep/Glob/Bash
- deterministic checks + judgment questions
- stop/fix/ask output
- line-specific question generation

https://github.com/komekome898-web/trade/blob/claude/bitflyer-trading-bot-hhxxaf/.claude/agents/owner-auditor.md

### [R3] `.claude/skills/research-squad/SKILL.md`
Used for:
- width-sweep
- 3+ acquisition routes
- source verification
- primary-source checks
- lead validation
- token/time budget

https://github.com/komekome898-web/trade/blob/claude/bitflyer-trading-bot-hhxxaf/.claude/skills/research-squad/SKILL.md

### [R4] `.claude/skills/owner-audit/SKILL.md`
Used for:
- audit invocation timing
- unresolved stop prevents normal delivery
- lead response requirements
- authority structure

https://github.com/komekome898-web/trade/blob/claude/bitflyer-trading-bot-hhxxaf/.claude/skills/owner-audit/SKILL.md

### [R5] `docs/DELEGATION.md`
Used for:
- Owner / Lead / Subagent decision boundaries
- irreversible decisions
- model usage policy
- token budget
- Lead vs lower-model responsibilities

https://github.com/komekome898-web/trade/blob/claude/bitflyer-trading-bot-hhxxaf/docs/DELEGATION.md

### [R6] `docs/AUDITOR/IMPROVEMENT.md`
Used for:
- current weekly auditor improvement loop
- capture / owner load / cost as existing objective function
- blind evaluation
- candidate-vs-production comparison
- deterministic scripting as a cost-reduction path

https://github.com/komekome898-web/trade/blob/claude/bitflyer-trading-bot-hhxxaf/docs/AUDITOR/IMPROVEMENT.md
