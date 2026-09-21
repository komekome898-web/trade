# TypeSafe Jev (System One) 調査棚卸し C — 一次資料の逐語収集

判定はしない。以下は一次資料からの逐語抜き出し。既読ページ(system-one, state, noul, confidence, patterns, jev-1.13 jaggedness の一部, citation_check, llm_guardrails, consistency_noul_cookbook, agent-skill)は各節で1行要点のみ。

## 1. 入力の制約(state)

- 形: `state` は `string | object | array`。出典 https://docs.typesafe.ai/api.md 「The content to evaluate. A plain string for text, or structured data (object/array) for things like chat logs, records, or the current state of your application.」
- 大きさの上限(jev-1.13): 出典 https://docs.typesafe.ai/models.md 表「Context length | 64k tokens per request; 32k tokens for `state` plus the longest question」。本文「The 64k budget covers the `state` plus all questions combined; the 32k budget applies to the `state` plus the single longest question.」
- 言語: 「Jev accepts natural-language text. English is the primary training language and where accuracy is currently best. Other languages, including CJK scripts, are handled but not equally well; test on your own content before relying on Jev for a non-English workload」(models.md「Language support」)
- 画像等不可: 出典 models.md 表「Input | Text only. String, JSON object, or array of text values. No image, audio, or video input.」本文「Jev evaluates natural-language text. Pre-process non-text inputs (images, audio, video, binaries) into text or structured fields before sending them as `state`.」
- 大きい state の劣化: jaggedness(既読・重点再確認)「Accuracy falls as the state grows with content unrelated to the decision. Unrelated detail acts as a distractor」(model-jaggedness/jev-1.13.md §Large state full of irrelevant detail)。同ページ Info「Giving it more context in `state` than the question needs. Jev suffers from context rot, so unrelated material in the `state` costs you accuracy.」
- state 既読ページ要点(1行): concepts/state は state の形・構造化・関連情報のみを送る指針(本調査では未再読、api.md/how-to-build.md からの参照で代替)。

## 2. 問いの型 3 つ + structure。応答の全フィールド

出典: https://docs.typesafe.ai/api.md 、https://docs.typesafe.ai/primitives/choice.md 、https://docs.typesafe.ai/primitives/score.md 、https://docs.typesafe.ai/primitives/advanced.md

### Noul
- 「A yes/no question. Returns the probability the answer is yes.」type="noul" required、instructions required、criteria(true/false の説明文)は optional。
- 応答: `type`(noul固定)、`noul`(number, 「The yes/no answer on a scale from 0 (no) to 1 (yes).」)。**confidence フィールドは無い**(api.md「Choice and Score answers also carry a `confidence` between 0 to 1」— Noul は含まれない)。

### Choice
- 「Picks one option from a set you define. Returns the chosen option and the full probability distribution.」criteria は `map<string, string | null>` required「A map of option to rubric description; use null when an option needs no extra detail.」
- 応答: `type`、`choice`(「The highest-probability option.」)、`probabilities`(「Every option mapped to its probability (floats that sum to 1).」)、`confidence`(number required「How certain the model is, derived from probabilities.」)。

### Score
- 「Rates the state along a rubric you define. Returns a probability-weighted value across your levels.」criteria は array required「An ordered array of level descriptions. You must include at least two levels.」
- レベル数上限: score.md「Use as many levels as you can describe distinctly, up to 10. Three is fine. Don't add levels you can't describe distinctly.」
- 応答: `type`、`score`(「The probability-weighted answer across the levels; can land between levels.」)、`legend`(map<string,string> 「Each level number mapped back to its description.」)、`probabilities`(各レベルの確率)、`confidence`。

### 全問い共通 / リクエスト・レスポンス全体
- リクエスト: `state`(required)、`model`(required、"jev-latest" 等)、`questions`(`map<string, Question>` required)。「The key is not sent to the underlying model and is not used in inference.」
- レスポンス: `model`(string required「The model that performed the evaluation.」)、`answers`(map required)、`usage`(object required「Token usage for the request.」→ `input_tokens`, `output_tokens`)。

### Advanced: structure
- 「Every one of these fields is an `EntryType`」— 対象は `instructions`(Choice/Score/Noul、`string, object, array, or null`)、`criteria` values(Choice option descriptions、同型)、`criteria` entries(Score level descriptions、同型)、`criteria.true`/`criteria.false`(Noul、同型)。
- いつ使うか: 「When it helps with clarity. When a question has multiple parts, putting them in the form of JSON helps with clarity because the keys are labeled.」/「When question needs supporting data. A schema, a taxonomy, or a database row is already JSON. Use the JSON entirely or pass in the relevant subfields instead of serializing them into a string template.」

## 3. 「得意」と「不得意」(ベンダー自身の言葉)

出典: https://docs.typesafe.ai/model-jaggedness/jev-1.13.md(既読リストにあったが今回オーナー指定で重点再読)

総括: 「`jev-1.13` is fast, calibrated, and good at common-sense judgment but it is not perfect. `jev-1.13` does the best on System One tasks. It may struggle with tasks that require additional levels of indirection. It can be quite literal in its understanding. It struggles with tasks that require numeric precision.」

- **数える**: 「`jev-1.13` does not count reliably. This covers characters in a word, occurrences of a term in a passage, and items in a long list. The model recognizes the shape of an answer rather than tallying, and the error grows with the size of the thing being counted.」対策「count in code... iterate in code over the candidates and ask one question for each, then add up the answers yourself.」
- **比べる(数値表現)**: 「`jev-1.13` will perform better on semantic representations than numeric. For example, questions about colors using hex values will underperform compared to those using the English names. Given RGB triples or hex values it cannot reliably judge whether two values are near each other.」
- **Score を数値補間に使う禁止**: 「Please do not use score outputs (e.g., expectations and probability) to compute the exact magnitude of a number between two levels of a criterion.... `jev-1.13`'s score levels are weak in numerical calibration.」
- **日付**: 「`jev-1.13` reads dates as text, not as ordered quantities. Asking which of two dates comes first, how far apart they are, or whether one falls inside a window is unreliable. It gets worse with mixed formats, relative references and domain boundaries such as quarters, settlement windows, and accrual periods.」対策「Extraction is a judgment, so give it to the model. Arithmetic is not, so keep it in code.」
- **否定(literal reading)**: 「`jev-1.13` answers the question you wrote, not the one you meant. Scoping words, negations, and implied conditions are read at face value.」
- **矛盾する instructions/criteria**: 「a Noul where `true` maps to no and `false` maps to yes will perform worse.」
- **多段の間接(indirection)**: 「Instructions carrying double negatives or complex indirection are answered less reliably. A question about a property of a property or something that requires multiple hops of reasoning costs accuracy.」
- **敵対的入力**: 「State is data, and `jev-1.13` does not treat it as hostile by default. Content written to adversarially steer the model, whether that is an injected instruction, a deliberately misleading framing, or text that argues for its own classification, can move the answer. We expect to improve on this in the future.」対策「be explicit in the criteria. Test your integration thoroughly before deploying it to many users.」
- **生成不可**: 「`jev-1.13` is not trained to generate text. While you can force it to by chaining choices, this will not work well and will be very slow.」対策「when the answer space is bounded, turn extraction into a Choice over the options rather than asking for the value itself. If you really need to generate text... there are other models for that.」
- **構造的不変性が保証されない**(Noul vs Choice vs 否定形 Noul の数値は比較不能): 具体例(同一チケットで Noul=0.22 vs Choice probabilities yes=0.01/no=0.99/confidence=0.97)。「The comparable numbers are `noul` and `probabilities["yes"]`, and it is not obvious how to interpret either the Choice output and confidence for the Noul question or vice versa.」否定形 Noul の例(refund 0.72 / not_refund 0.47、合計1.19)。「There are many reasons that `P(noul)` and `1 - P(not noul)` may not be directly comparable.」「don't rely on expected structural invariance, and word questions to mean directly what you want. Don't carry a threshold tuned on a Noul over to a Choice, and don't hold the model to arithmetic identities between separate questions.」
- 避けるべきことの総括(Info box): 「Asking the model something code can compute exactly. / Hiding several judgments inside one question. / System Two tasks: more layers of indirections / Giving it more context in `state` than the question needs.」

## 4. 設計の原則 + cookbook 実測値

出典: https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md、各 cookbook

- **コードと模型の分担**: 「Code handles deterministic work and owns the control flow. The model appears only where the system needs programmable common sense or needs to interpret unstructured data. Each AI task is kept atomic and constrained.」(how-to-build.md「Three software architectures」タブ)
- **原子的な問い**: 「Ask the most explicit, narrow, specific, atomic questions you can. Break down complex or ill-defined questions into separate questions that each evaluate one property.」Info「This is probably the most important concept in this guide. Broad questions hide several judgments behind one answer.」
- **fan-out(並列で多問)実測**: cookbooks/parallel_questions 要旨(逐語、ページ冒頭の説明文)「Runs a 13-question regulatory briefing over the GDPR Wikipedia article, showing that batching every question into one TypeSafe call is 12.2x cheaper and 10.0x faster with no change in answers.」原則側 how-to-build.md「Ask a lot of questions」Step「Ask many narrow, independent questions about the same state in one request. This is how you maximize effectiveness and intelligence per dollar with the API」
- **しきい値の決め方(confidence routing)**: how-to-build.md「Route on uncertainty」Step「Make code take different actions for confident and unconfident answers. Escalate uncertain cases to a person or a more expensive reasoning model. Test thresholds by plotting confidence against accuracy on your data.」
  - 実測(cookbooks/classification_using_confidence、75業種分類・60件): 「forced to name a group every time      39/60 right」「of those, the 30 it was sure about  27/30 right」「and the 30 it was not           12/30 right」「letting it answer coarsely when unsure  48/60 useful answers」。本文「Where the model was sure, the group it named is right nine times in ten. Where it was not, naming a group was wrong more often than right, at 40%. Reporting those same answers as a division takes them to 70%.」
- **composite scoring(重み付き合成はコード側)**: patterns/composite-scoring.md 冒頭「Oftentimes we want to rank a set of items based on several criteria at once. Composite scoring is an easy way to think about this: break the judgment into independent dimensions, score each one separately, and combine them with weights you control in code.」/ how-to-build.md「Combine question outputs in code」Step の例コード(quality = 0.4*answers_request + 0.4*citations_are_supported + 0.2*(1-contradicts_context))。
- **intent routing**: patterns/intent-routing.md 冒頭「Not every user request needs the same kind of handler. Some can be answered with a database lookup. Some need an LLM with domain-specific context. Some need a human. TypeSafe can sit in front of all of these as a fast, cheap classifier that determines which handler to invoke.」
- **fan-out(speculative)パターン頁の冒頭**: patterns/fan-out.md「Because TypeSafe supports sending many questions in a single API call, we recommend putting all of the questions your system needs in a single request, and then using code to decide what is relevant after the fact. All questions are evaluated in parallel, so adding more questions to a call typically doesn't add any latency to the response.」
- **confidence-gated routing 頁の冒頭**: patterns/confidence-routing.md「One of TypeSafe's most powerful features is confidence. By being intentional with the way you gate decisions on confidence, you can build systems that are both reliable and safe.」
- **自己一貫性(self-consistency)**: 既読 cookbooks/consistency_noul_cookbook(1行要点): 不確実な確率を人間レビューに回しつつ元の noul 値は見える形で残す設計。how-to-build.md の Composable カード「Self-consistent | System One is designed to return stable answers across repeated evaluations.」
- **関数呼び出し実例(取引所コマンド → 型付き関数)**: cookbooks/function_calling.md 冒頭「Turns natural-language trading requests into calls to ordinary typed functions by mapping function names and closed-set arguments to confidence-aware TypeSafe questions.」本文実測「Both long commands came out as asked. ... filled four arguments from one sentence. Two of them, `symbol` and `benchmark`, draw from the same six tickers, and each ticker landed in the right argument because the questions spell out the roles」
- **再ランク(rerank)実測**: cookbooks/rerank_typesafe.md 冒頭「Builds 30-passage BM25 shortlists for 40 CLERC legal queries, then uses one TypeSafe question per query-candidate pair to raise top-1 accuracy from 5% to 18% and top-10 accuracy from 38% to 62%.」
- **階層分類(beam search)**: cookbooks/hierarchical_classification.md 冒頭「Classifies documents through deep patent, retail product, biomedical, and source-code hierarchies using parallel beam search over TypeSafe Choice probabilities.」本文の方式差「Greedy search: choose the highest-probability child and discard every alternative. One early mistake cannot be recovered. Beam search: retain `K` plausible paths and classify every frontier in parallel. Deeper evidence can repair an ambiguous early decision.」
- **RAG passage 選別**: cookbooks/classifying_rag_passages.md 冒頭「Score each retrieved passage with one TypeSafe request, then decide in code which ones reach the answering model. For example, keep and flag ones that contradict the question, and drop ones carrying a hidden instruction or prompt injection.」
- **エージェントのスキル選定**: cookbooks/skill_suggestion.md 冒頭「Picks at most one skill for an agent turn out of the 182 in Nous Research's Hermes catalog: one TypeSafe request ranks every skill and asks whether the turn needs one at all, a second reads the top three properly and can reject all of them. The winner's name goes into a single line of the agent's system prompt, and both the wrong skills it loads and the ones it loads when nothing fits drop by more than half.」
- **line-by-line 検索**: cookbooks/semantic_find.md 冒頭「Build semantic search for GitHub's Terms of Service. In one request, score 218 line ids against a plain-language query with a Choice question, and use a Noul question to check whether the document contains an answer.」
- **RLCD(訓練方式の原則的背景)**: introduction/machine-learning-primer.md「RLCD optimizes for a different output contract: The model does not generate text. It returns decisions and probabilities. Higher probability should correspond to a greater chance that the answer is correct.」「Outcomes assigned a probability of `0.2` should occur about 20% of the time.... These rates describe groups of predictions, not a guarantee about any single answer.」
- **「用途マップ」上で研究/監査/harness に近い区分**: concepts/use-case-map.md カード「Universal Verification | Verify the input prompt, extractions, reasoning traces, tool calls, or inputs of any other AI. Detect jailbreaks, citation errors, hallucinations, mistakes, or other error-modes that other AIs or LLMs make at a fraction of the cost for the actual LLM call.」「Harness Engineering | Use Jev queries to make your harness smarter - model routing, semantic context retrieval, LLM error detection and guardrails, reasoning trace classification at lightspeed and a fraction of the cost.」

## 5. ベンダーのスキル(typesafe-ai/skills)本文の要点(逐語)

出典: https://github.com/typesafe-ai/skills(clone 済み、`skills/typesafe-ai/SKILL.md`、150行、README.md 併読)。frontmatter description:「Build AI-powered software with TypeSafe: small units of AI intelligence you can use like programming primitives.... Use when a feature needs programmable common sense, when brainstorming what AI could make possible in an app, or when an LLM prompt-and-parse step could become a structured decision.」

本文逐語(該当箇所を抜粋):

「**The live TypeSafe docs are the source of truth. Read them as part of the task.** This skill gives direction; the docs carry current concepts, prompting guidance, API contracts, SDK usage, models, limits, and worked examples.」

「Start with the documentation index (https://docs.typesafe.ai/llms.txt) to discover relevant pages and cookbooks. Use targeted reads rather than loading the entire site.」

「Before writing an integration, read the current API or chosen SDK page and the question guidance relevant to the design. For a new workflow, also inspect the closest cookbook: it often shows a better decomposition than a generic classifier.」

「If the index is unavailable, use the direct links below or the site's navigation. If Markdown fetching fails, try the normal page. If live access is unavailable, use available local docs or installed SDK types, state that limitation, and avoid inventing version-dependent details.」

「Start from the behavior the user wants: what will the application show, select, change, or hand off? Work backward to the judgments it needs. Keep known rules, calculations, exact lookups, and execution in code. Preserve the user's chosen stack and scope; add TypeSafe where semantic understanding helps.」

「When brainstorming or choosing an architecture, consider more than classification. The patterns below are starting points: combine primitives around the user's goal, including ideas that do not fit an established recipe.」6分類(Route and fill known arguments / Select instead of generate / Find and judge evidence / Turn judgments into reusable data / Verify and escalate / Respond to changing state)を列挙。「**Verify and escalate.** Check specific claims or fields against their evidence; send uncertain or failing cases to a person or reasoning model.」

「For open-ended requests, offer the few directions that best serve the user's goal and recommend a starting point. For a concrete request, choose the relevant pattern and build; a brainstorm is not a mandatory detour.」

「Ask one narrow, coherent judgment per question. Split independently useful dimensions, without destroying the relationship being judged. A bounded action selection or contextual interpretation is valid; atomic does not mean literal fact extraction or a one-sentence limit.」

「Keep the needed answers available. Include a no-match outcome when nothing may fit; use a separate presence judgment when it is independently useful. For source-value selection, check candidate coverage: the model cannot choose an omitted value.」

「**Ask independent questions over the same state together**, including useful speculative questions. They run in parallel and cannot see one another's answers. State each speculative premise explicitly; code consumes the applicable answers. A second request is warranted when an earlier answer is needed to fetch evidence, construct new state, or determine the next options. Extra questions still use tokens; measure actual request budgets, cost, and end-to-end latency.」

「Use probabilities and confidence to guide behavior, with thresholds evaluated on the user's data and consequences. Choice/Score confidence summarizes distribution concentration, not overall workflow correctness or permission to act. A Noul near 0.5 means similar probability for yes and no, not medium intensity.」

「Keep policy explicit and raw judgments reusable. Weighted scores suit compensating preferences; an "any serious violation" rule needs separate conditions. Changing a weight or display filter need not rerun inference when evidence and question meanings are unchanged. **Typed output guarantees the interface, not truth. System One models are trained for calibrated decisions; validate their performance in the target domain.**」

「Test representative cases and the resulting application behavior. For failures, inspect the exact state, questions, candidates, answers, composition, and observed outcome. Separate missing evidence, model errors, code errors, and service failures. **Treat cookbook thresholds and demo results as examples to evaluate, not universal rules or permanent model limitations.** Keep API credentials server-side in web apps.」

README.md(該当箇所):「Agent skills for building with TypeSafe: typed decisions and probabilities from System One models.」インストール(Claude Code plugin): 「claude plugin marketplace add typesafe-ai/skills」「claude plugin install typesafe@typesafe-ai」。用例プロンプト: 「Use TypeSafe to route incoming support tickets by department, with human review for uncertain decisions.」

## 6. 費用・上限・契約

出典: https://docs.typesafe.ai/models.md 、https://docs.typesafe.ai/api.md 、https://typesafe.ai/legal/mca 、https://typesafe.ai/legal/data-processing 、https://typesafe.ai/legal/privacy-policy(いずれも本文は HTML、`.md` 版は Framer の 404 ページだったため HTML から逐語抽出)

- **料金**(jev-1.13.0): 表「Price (per Btok / per Mtok) | \$42 / \$0.042」。「**Price:** Charged per input token. Output tokens are free. A Btok is a billion tokens and an Mtok is a million tokens.」
- **レート制限**: 表「Rate limits | 250,000 tokens per second / 1,200 requests per minute」。Warning「**Rate limits are adjusting dynamically.** We are serving a very large volume of demand, and the limits above can change without notice while we do... Higher limits are available on custom and enterprise plans.」
- **要求あたりの上限**: 「Context length | 64k tokens per request; 32k tokens for `state` plus the longest question」
- **エラー・429**: api.md 表「429 Too Many Requests | You have exceeded your rate limit. Back off and retry after a short delay.」「529 Overloaded | TypeSafe is temporarily overloaded. Retry after a short delay.」
- **顧客ごとの Usage Limits(契約側)**: MCA(typesafe.ai/legal/mca)「TypeSafe grants to Customer a limited, non-exclusive, non-transferable, non-sublicensable license during the Term to: (a) access and use the Services in accordance with the applicable documentation... including Customer's compliance with the usage limits set forth in the Order ("Usage Limits")」— 具体的な数値は Order(個別契約)側にあり本文書には無い。禁止事項「(k) exceed any Usage Limits」。
- **公開禁止条項(f)**: MCA「(f) publish benchmarks or performance information about the Services;」(利用規約の禁止行為リストの一項、(e) 不正表示除去禁止・(g) 妨害禁止と並ぶ)
- **データ保持(Retention)**: Privacy Policy(typesafe.ai/legal/privacy-policy)見出し「Retention」本文「We retain personal data about you for as long as reasonably necessary to provide you with the Services, or otherwise in support of our business or commercial purposes. When you request that we do so, we take measures to delete your personal data or keep it in a form that does not permit identifying you when this personal data is no longer reasonably necessary for the purposes for which we process it, unless we are required by law to keep this data for a longer period.」— 具体的な日数は明記なし(未確認: DPA 本文に「retention」の語自体は見つからず、Subprocessor 異議申立ての「15 days」のみヒット)。
- **モデル訓練への不使用(customer data)**: Privacy Policy「We will not train or fine tune any artificial intelligence or machine learning models on your prompts or other Input.」/「We (1) will not train or fine tune any artificial intelligence or machine learning models on Input, and (2) will not disclose any Input to a third party other than our service providers.」models.md「Jev is not trained on customer requests or responses.」
- **テレメトリ的な収集(analytics)**: Privacy Policy「Partners. We use analytics services such as Google Analytics to collect and process analytics data. These services may also collect information about your use of other websites, apps, and online resources.」および「To generate anonymized or aggregated data that we may use for lawful purposes」
- **ゼロデータ保持(ZDR)**: legal.md「We also offer zero data retention (ZDR) for enterprise customers. Contact privacy@typesafe.ai to learn more.」models.md「See Legal for the Data Processing Agreement, the Privacy Policy, and details on zero data retention (ZDR) for enterprise customers.」— 対象条件・提供形態の詳細は未確認(コンタクト前提の個別提供)。
- **Subprocessor の変更通知**: DPA「Customer may object to the appointment of such new Subprocessor within 15 days of the date of such notice on reasonable privacy or security grounds by providing Typesafe written notice of its objection.」
- **免責条項**(出力の正確性について): MCA「CUSTOMER ACKNOWLEDGES AND AGREES THAT: (I) THE SERVICES MAY PRODUCE INACCURATE OR ERRONEOUS OUTPUT; (II) CUSTOMER IS RESPONSIBLE FOR INDEPENDENTLY EVALUATING THE OUTPUT; (III) DUE TO THE NATURE OF THE SERVICES AND ARTIFICIAL INTELLIGENCE TECHNOLOGIES GENERALLY, OUTPUT MAY NOT BE UNIQUE AND OTHER USERS OF THE SERVICES MAY RECEIVE OUTPUT FROM THE SERVICES THAT IS SIMILAR OR IDENTICAL TO THE OUTPUT」

## 対応表(やったこと ↔ オーナー原文の該当語)

| やったこと | オーナーの原文の該当語(逐語) |
|---|---|
| 未読ページ(choice/score/structure/how-to-build/ML primer/use-case-map/patterns 4本/cookbook 8本/models/api/legal)を重点的に読み逐語を抜いた | 「**まだ読んでいない次を重点的に**」 |
| GitHub typesafe-ai/skills を clone し SKILL.md を本文に近い形で抜いた | 「**これはベンダー自身が「コーディングエージェントに Jev をこう使わせろ」と書いた文書なので、本文を全文に近い形で抜く。**」 |
| 判断はせず、1〜6節の事実収集と出典・逐語付けのみ行った | 「**判定はしない。一次資料(ベンダー自身の文書)からの逐語の抜き出しだけを行う。**」
