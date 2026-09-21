# Jev / TypeSafe 調査ノート(一次資料からの逐語集)

判定・推奨はしない。ベンダー一次資料からの逐語とコードの抜き出しのみ。出典 URL を各所に付す。

---

## A. Jev とは何か

出典: https://docs.typesafe.ai/introduction , https://docs.typesafe.ai/concepts/system-one , https://docs.typesafe.ai/introduction/machine-learning-primer , https://docs.typesafe.ai/model-jaggedness/jev-1.13

「Jev is TypeSafe's flagship model and the first System One model. Send state and typed questions; get structured answers your code can use directly.」

「Jev evaluates typed *questions* against a *state* and returns structured results directly. No text generation, no parsing.」

System One の定義:「System One models are a class of AI models built to make fast, structured decisions that software can use directly. A System One model evaluates a state and returns typed answers and probabilities.」「Like an LLM, a System One model understands natural-language input. It returns typed decisions and probabilities rather than generated text.」

名前の由来:「The System One name comes from the concept Daniel Kahneman popularized in his book *Thinking, Fast and Slow*. System 1 thinking is fast and intuitive. System 2 is slower and more deliberate. Here, the emphasis is on fast, focused judgments.」

訓練方式 RLCD:「RLHF, RLVR are shown here for context; TypeSafe's training path is RLCD.」「**Reinforcement learning for calibrated decisions** trains TypeSafe to return decisions and calibrated probabilities instead of generated text.」RLCD の契約:「The model does not generate text.」「It returns decisions and probabilities.」「Higher probability should correspond to a greater chance that the answer is correct.」

「確率が校正されている」の意味(逐語):「System One models are trained for calibrated decisions: their probabilities are optimized against outcomes to reflect uncertainty. Calibration is measured across groups of predictions; it does not guarantee that an individual answer is correct.」具体的な基準:「Outcomes assigned a probability of `0.2` should occur about 20% of the time.」「Outcomes assigned a probability of `0.8` should occur about 80% of the time.」「Outcomes assigned a probability of `1.0` should occur 100% of the time.」「These rates describe groups of predictions, not a guarantee about any single answer.」

RLHF の問題点(ベンダーの自己認識):「RLHF teaches a model to say things that people prefer. That objective works well for chatbots, but it can also reward sycophancy and confident-sounding hallucinations.」「Preference optimization also causes **mode dropping**」「An output can be compelling to a person without being reliable enough for unattended automation. Human preference and machine trustworthiness are different optimization targets.」

限界(model-jaggedness ページより、ベンダー自身の記載。適用対象 `jev-1.13`、最終レビュー 2026-09-17):「`jev-1.13` is fast, calibrated, and good at common-sense judgment but it is not perfect.」9 個の既知の失敗モード(下記 I 節に詳細)。「`jev-1.13` is not trained to generate text. While you can force it to by chaining choices, this will not work well and will be very slow.」入力制限:「Jev currently accepts text input only. It evaluates strings, JSON objects, and arrays of text. Images, audio, and video are not supported (yet).」

---

## B. API と SDK の全仕様

出典: https://docs.typesafe.ai/api , https://docs.typesafe.ai/models , https://docs.typesafe.ai/sdk/python , https://docs.typesafe.ai/sdk/python/usage , https://docs.typesafe.ai/sdk/python/api/retries , https://docs.typesafe.ai/sdk/python/api/exceptions , https://docs.typesafe.ai/sdk/python/api/constants , https://docs.typesafe.ai/sdk/python/api/types/questions , https://docs.typesafe.ai/sdk/python/api/types/responses , https://docs.typesafe.ai/sdk/python/api/types/common , https://docs.typesafe.ai/sdk/python/api/clients/sync , https://docs.typesafe.ai/sdk/python/changelog , https://docs.typesafe.ai/sdk/javascript/api/interfaces/* , https://docs.typesafe.ai/sdk/javascript/changelog

### エンドポイント
```
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <API_KEY>
Content-Type: application/json
```
`GET /v1/models` も存在。「It currently lists the aliases. Versioned IDs such as `jev-1.13.0` are accepted by the `model` field whether or not they appear in the list.」

### リクエスト本体(全フィールド)
- `state` (string | object | array, required): 「The content to evaluate.」
- `model` (string, required): 「Use `"jev-latest"`, TypeSafe's flagship model.」
- `questions` (map<string, Question>, required): key は呼び出し側が選ぶ、モデルには送られない。

Question は3種、共通フィールド `type` + `instructions`:
- **Noul**: `type: "noul"` (必須)。`instructions` (必須)。`criteria` (任意、`{true, false}` の説明)。
- **Choice**: `type: "choice"`。`instructions` (必須)。`criteria` (必須、`map<string, string|null>`。最大255オプション)。
- **Score**: `type: "score"`。`instructions` (必須)。`criteria` (必須、配列。最低2、最大10レベル)。

`instructions` と各 `criteria` エントリは `string | object | array | null` (`EntryType`)。

### レスポンス本体
`model` (string), `answers` (map<id, Answer>), `usage` (`input_tokens`, `output_tokens`)。
- Noul answer: `type`, `noul` (0〜1、yes の確率)。
- Choice answer: `type`, `choice`, `probabilities` (map、合計1)、`confidence` (0〜1)。
- Score answer: `type`, `score` (0〜トップレベル番号、レベル間の値も取り得る)、`legend` (レベル番号→説明)、`probabilities`、`confidence`。「Noul has no separate `confidence`.」

### エラー型(HTTPステータス)
| Status | Meaning |
|---|---|
| `401 Unauthorized` | Missing or invalid API key. |
| `422 Unprocessable Entity` | The request body failed validation. |
| `429 Too Many Requests` | You have exceeded your rate limit. |
| `529 Overloaded` | TypeSafe is temporarily overloaded. |

「When you receive a `429 Too Many Requests` or `529 Overloaded` response, retry the request with exponential backoff instead of retrying immediately. Our client SDKs handle this automatically...」

### モデルとレート制限 (`jev-1.13.0`)
Price: $42/Btok, $0.042/Mtok (入力課金、出力は無料)。Rate limits: 250,000 tokens/sec, 1,200 requests/min。Context: 64k tokens/request 全体、32k tokens が state+最長question。「Rate limits are adjusting dynamically... can change without notice」。

Alias: `jev-latest` → `jev-1.13.0`(SDK既定、docsの例で使用)。`jev-preview` → 現在 `jev-1.13.0` と同じ(プレビュービルド無し)。「The response's `model` field reports the versioned ID that answered」。「If you have tuned confidence thresholds against a specific version, pin that version's ID instead of the alias」。

言語:「English is the primary training language and where accuracy is currently best. Other languages, including CJK scripts, are handled but not equally well」。データ:「Jev is not trained on customer requests or responses.」「Jev is not fine-tuned or LoRA-adapted with customer data... the same weights serve every account.」

### Python SDK
インストール: `uv add typesafe-sdk` / `pip install typesafe-sdk` (Python >= 3.10)。GitHub: https://github.com/typesafe-ai/typesafe-sdk-python

環境変数(`typesafe_sdk.constants`):
| 変数 | 既定値 |
|---|---|
| `TYPESAFE_API_KEY` (`API_KEY_ENV`) | 必須、既定なし |
| `TYPESAFE_BASE_URL` (`BASE_URL_ENV`) | `https://api.typesafe.ai` (`DEFAULT_BASE_URL`) |
| `TYPESAFE_DEFAULT_MODEL` (`DEFAULT_MODEL_ENV`) | `jev-latest` (`DEFAULT_MODEL`) |
| `TYPESAFE_LOG_LEVEL` (`LOG_LEVEL_ENV`) | 未設定 |

`DEFAULT_TIMEOUT = 10.0` 秒。

`TypeSafeClient(*, api_key, model, retry: RetryPolicy|None, timeout, headers, transport, http_client, base_url)`。「Explicit options take precedence over environment variables; empty or whitespace-only environment values are ignored.」

`client.system_one(state, questions, *, model=None, retry=None, timeout=None, extra_headers=None, extra_body=None, response_model=None) -> SystemOneResponse | ResponseT`。例外: `TypeSafeError`(質問が空、またはScore criteriaが空)、`TypeSafeAPIError`(リトライ後も非成功応答)、`TypeSafeAPIConnectionError`(接続不能/タイムアウト)、`TypeSafeAPIResponseValidationError`(応答が response_model と不一致)。

```python
from typesafe_sdk import Choice, TypeSafeClient

with TypeSafeClient() as client:
    response = client.system_one(
        state={"document": "I was charged twice. Please fix this ASAP."},
        questions={
            "category": Choice(
                instructions="What is this ticket about?",
                criteria={"billing": None, "technical": None, "other": None},
            ),
        },
    )

print(response.answers["category"].choice)
```

**RetryPolicy** (`typesafe_sdk.RetryPolicy`, dataclass):
```
RetryPolicy(
    max_retries: int = 2,
    backoff_initial: float = 0.5,
    backoff_max: float = 5.0,
    backoff_jitter: float = 0.25,
    http_statuses: set[int] = {408, 429, *range(500, 600)},
    respect_retry_after: bool = True,
    api_connection_error: bool = True,
    api_timeout_error: bool = True,
    exceptions: set[type[BaseException]] = set(),
    predicate: Callable[[BaseException], bool] | None = None,
    timeout: float | None = 30.0,
)
```
各フィールドの逐語:「Maximum retries after the initial attempt; `0` disables retries.」「First backoff delay in seconds, doubled each attempt up to `backoff_max`; zero disables backoff.」「Fraction of each backoff delay randomly subtracted, between 0 and 1.」「HTTP status codes that are retried.」「Whether to honor `Retry-After` and `retry-after-ms` response headers.」「Total retry budget in seconds per SDK call, including the initial attempt and delays; `None` disables the limit. Stops before a retry whose delay would reach or exceed the budget, re-raising the last error.」

**例外階層** (`typesafe_sdk`): `TypeSafeError`(基底) → `TypeSafeAPIError`(status, body, headers, endpoint, request_id プロパティ) → `TypeSafeBadRequestError`(400)/`TypeSafeAuthenticationError`(401)/`TypeSafePermissionDeniedError`(403)/`TypeSafeNotFoundError`(404)/`TypeSafeUnprocessableEntityError`(422)/`TypeSafeRateLimitError`(429、`retry_after_ms` 属性)/`TypeSafeInternalServerError`(5xx)/`TypeSafeAPIResponseValidationError`(`field_path` 属性、例「answers.tone.confidence」)。接続エラー: `TypeSafeAPIConnectionError`(基底 `ConnectionError` も継承) → `TypeSafeAPITimeoutError`(`timeout` 属性、`TimeoutError` も継承)。

**非同期**: `AsyncTypeSafeClient`、`async with` で使用、メソッドは `await client.system_one(...)`。

**ログ**:「The SDK logs to the `typesafe_sdk` logger.」`TYPESAFE_LOG_LEVEL` を `debug|info|warning|error|off` に設定可。「`info` logs one summary line per request; `debug` also logs request and response headers and bodies. Secret headers — authorization, API keys, cookies, and any header whose name contains `token` or `secret` — are redacted from log output. Request and response bodies are **not** redacted.」

**前方互換性**:「The SDK keeps working as the TypeSafe API evolves」。未知の追加フィールドは `extra_body={"beam_width": 4}` のように送信可。生の質問辞書も使用可(`{"type": "noul", "instructions": "...", "weight": 2}`)。未知の応答フィールドは無視、未知の answer 種別は警告してスキップ(`raw_http_response` で確認可)。

**バージョン固定**: `TypeSafeClient(model="jev")` のようにモデル名指定可。エイリアス vs バージョン固定 ID の区別は上記モデル節参照。

**SDK 破壊的変更方針**(changelog より逐語):
- v0.7.0 (2026-09-18): 「ser/de library has been changed from `msgspec` to `pydantic`」(破壊的)。バグ修正:「`str` subclasses are now correctly serialized as strings instead of lists of characters」。新機能: `response_model` 引数追加。
- v0.6.0 (2026-09-15): 「accept `Score.criteria` as an ordered sequence instead of a dictionary keyed by integers」(破壊的)。
- v0.5.7 (2026-09-14): 「This is the initial public release of TypeSafe Python SDK.」

### JavaScript / TypeScript SDK
インストール: `npm install @typesafe-ai/sdk` (Node.js 20+)。GitHub: https://github.com/typesafe-ai/typesafe-sdk-js
```ts
import { choice, TypeSafeClient } from "@typesafe-ai/sdk";

const client = new TypeSafeClient();
const response = await client.systemOne({
  state: { document: "I was charged twice. Please fix this ASAP." },
  questions: {
    category: choice("What is this ticket about?", {
      billing: null, technical: null, other: null,
    }),
  },
});
console.log(response.answers.category.choice);
```
`TypeSafeClientConfig`: `apiKey?`(既定 `TYPESAFE_API_KEY`)、`baseURL?`(既定 `TYPESAFE_BASE_URL` → `https://api.typesafe.ai`)、`defaultModel?`(既定 `TYPESAFE_DEFAULT_MODEL` → `jev-latest`)、`timeout?`(既定 10000ms、attempt毎、「without a total retry budget」)、`retry?: Partial<RetryPolicy>`、`logLevel?`(既定 `TYPESAFE_LOG_LEVEL` → `warn`)、`logger?`、`defaultHeaders?`、`fetch?`、`dangerouslyAllowBrowser?`(既定 false、「Allow browser use, exposing the API key to page users.」)。

`RetryPolicy` (JS interface、既定値): `maxRetries=2`、`backoffInitialMs=500`、`backoffMaxMs=5000`、`backoffJitter=0.25`、`httpStatuses`(既定 408, 429, 500–599)、`respectRetryAfter=true`、`maxRetryAfterMs=60000`(「longer delays use backoff」)、`apiConnectionError=true`、`apiTimeoutError=true`。

JS changelog: v0.6.0 (2026-09-15) 破壊的変更「accept `Score.criteria` as an ordered sequence instead of a dictionary keyed by integers」。v0.5.7 (2026-09-11) 初回公開リリース。

`client.systemOne<Q>(request, options?)` は `APIPromise<SystemOneResult<Q>>` を返す。`SystemOneResult`: `answers`(型は質問から推論)、`model`、`usage`。エラークラス: `APIConnectionError`, `APIError`, `APITimeoutError`, `APIUserAbortError`, `AuthenticationError`, `BadRequestError`, `InternalServerError`, `NotFoundError`, `PermissionDeniedError`, `RateLimitError`, `TypeSafeError`, `UnprocessableEntityError`。

### system-one-adapter-python (GitHub, 別リポジトリ)
出典: https://github.com/typesafe-ai/system-one-adapter-python README。「A drop-in replacement for `typesafe_sdk`'s `system_one` evaluation API, backed by LLM APIs instead of TypeSafe. Useful for comparing TypeSafe against an LLM on cost/speed/intelligence.」オプション: `structured_outputs`(プロバイダのネイティブ構造化出力を使うか)、`llm_answer_mode`(`"probabilities"` か `"discrete"`)、`normalize_probabilities`、`n_retry_malformed_structure`、`retry`。応答は `typesafe_sdk.SystemOneResponse` のサブクラスで `usage`(`input_tokens_total`, `output_tokens_total`, `n_retries` 等)と `debug`(`llm_attempts`, `retry_reasons`)を追加。「It is a Pydantic model like every SDK response in `typesafe-sdk>=0.7.0`」。

---

## C. 問いの書き方の全規則

出典: https://docs.typesafe.ai/primitives , https://docs.typesafe.ai/primitives/advanced , https://docs.typesafe.ai/concepts/how-to-build-with-system-one , https://docs.typesafe.ai/model-jaggedness/jev-1.13

**原子的**:「System One models work best when each question asks one specific, well-scoped thing. Think of each question as a gut-check determination: the kind of judgment a highly knowledgeable person could make in a few seconds given the right context.」「If the judgment you want depends on several independent factors, ask about each factor separately and combine the answers with your own logic.」「This is probably the most important concept in this guide. Broad questions hide several judgments behind one answer. Atomic questions expose those judgments so you can inspect, tune, and combine them in code.」

**肯定形(Noulの推奨)**:「It's good practice to phrase it so a high probability means "yes", so that the returned answer is unambiguous in its meaning.」jev-1.13の既知の癖:「a Noul where `true` maps to no and `false` maps to yes will perform worse.」

**criteria の書き方**: Choiceは「Give the full list of options, and add an `other` or `none of the above` option when the list might not cover every input.」構造化(オブジェクト)を使う場面:「When two options are similar and the model keeps confusing them, describe each one with an object instead of a string. Give it fields for what the option covers, what belongs to a neighboring option instead, and a few example inputs.」例フィールド名 `what` / `not_for` / `examples`(API予約語ではなく自由に選べる)。Score levels は「Describe situations, not degrees.」の原則、「Each level is evaluated separately. The model doesn't see a level's number or its neighbours」。

**structure の使い方**(`primitives/advanced`): `instructions`, Choiceのoption説明, Score levels, Noulの`true`/`false` は全て `string | object | array | null` を受け付ける(`EntryType`)。「When it helps with clarity」「When question needs supporting data」の2条件で構造化を使う。

**言い換えを試す**:「Try your Noul question prompts with and without criteria to see which works better in your use-case.」「Beyond a plain question, you can phrase the instruction as a statement for the model to evaluate for truthfulness.」

**otherの置き方**: Choiceに「other」「none of the above」を追加する。skill_suggestion cookbookでは shortlist が「none fit」を返せる設計。

**presence判定の分離**(semantic_findより):「Choice probabilities always add up to 1, so some line ranks first even when the document doesn't answer the question... So ask a second question, in the same request」— ranking用のChoiceと存在確認用のNoulを分離する。

**参照パス**: 状態内の特定フィールドを指すときはバッククォート付きドット記法「\`ticket.messages[0].text\`」を instructions に書く。

**依存する質問は別リクエストにする条件**(唯一の例外基準):「The dependency is real only when your code cannot build the second request until it has the first answer: it needs the answer to fetch more data for the state, to decide what the state is made of, or to pick the next question's options. Otherwise, ask the questions together and combine their answers in code.」

---

## D. state の組み方の全規則

出典: https://docs.typesafe.ai/concepts/state , https://docs.typesafe.ai/primitives , https://docs.typesafe.ai/model-jaggedness/jev-1.13 , https://docs.typesafe.ai/concepts/how-to-build-with-system-one

**object / array / string の使い分け表**(逐語):
| Format | Useful for |
|---|---|
| String | A message, article, or passage |
| Object | Named fields, related records, or application state |
| Array | A sequence of messages or records |

「Use an object for most requests so each part of the state has a descriptive name and its relationships remain clear. A string is suitable when the use case is simple and requires only one piece of text.」

**関連情報を近くに**:「Put related information together when the decision requires comparing those parts.」「Think of state as the material you would present to a panel of experts before asking them to make a judgment.」

**無関係を落とす / 事前にcodeで絞る**(model-jaggednessの失敗モード5、逐語):「Accuracy falls as the state grows with content unrelated to the decision. Unrelated detail acts as a distractor, and a large state makes it harder to tell which part of the input produced a wrong answer.」「Instead: retrieve and filter in code first, and send only the fields the question needs. When it's not possible to filter in state, you can use a Noul to filter for relevance.」how-to-buildの手順2:「Include only the context relevant to the current questions. This helps the model avoid distractions and context rot.」

**大きさ**: リクエスト全体で約32,000 tokens(state + 質問群)、または 64k tokens(state + 全質問合計)。「roughly 150,000 characters of English text」。Choiceは最大255オプション。Score levelsは最大10。

**敵対的入力**(失敗モード6、逐語):「State is data, and `jev-1.13` does not treat it as hostile by default. Content written to adversarially steer the model, whether that is an injected instruction, a deliberately misleading framing, or text that argues for its own classification, can move the answer. We expect to improve on this in the future.」「Instead: be explicit in the criteria. Test your integration thoroughly before deploying it to many users.」classifying_rag_passages cookbook の運用上の注意:「The injection question is a filter, and only one. A passage that scores under the threshold still reaches the prompt, so the generator prompt has to treat every passage as untrusted text regardless of its score. Nothing here is a security boundary.」

**コンテンツと質問を分離**:「The state contains the content and supporting facts. Questions define the judgments the model should make about that material.」

---

## E. 料理本 18 本

各節: 出典 URL / 問題 / state / 問い(instructions・criteria 逐語) / 合成 / しきい値 / 実測 / 落とし穴。

### E.1 Double-checking citations
出典: https://docs.typesafe.ai/cookbooks/citation_check

問題:「An LLM answers a question and attaches citations... Some of those citations are wrong or hallucinated.」まず文字列一致で「missing quote」を検出(モデル不要)、生き残った引用だけ Choice で判定。

Choice質問(逐語):
```python
"relation": Choice(
    instructions="How does the section relate to the claim?",
    criteria={
        "supports": "The section states the claim or directly implies that it is true",
        "contradicts": "The section states the opposite of the claim or implies it is false",
        "says_nothing": "The section does not address what the claim asserts, either way",
    },
),
```
合成: `RELATION_TO_VERDICT = {"supports": "verified", "contradicts": "contradicted", "says_nothing": "unsupported"}`、文字列一致で `missing` なら `fabricated`(モデル呼ばず)。

しきい値: `AUTO_ACCEPT = 0.8`(「start high for more human review as you build trust in the model」)。confidence ≥0.8 なら判定確定、未満なら人間確認。

実測(`jev-1.12`, RFC 7519, 8引用): 正確な4件は全て `verified`、confidence 0.93以上。`sig_reporting` は文字列一致で `fabricated`(モデル未呼出)。`exp_required` は `contradicted` confidence 0.99。`pii_encryption`・`iat_future` は `unsupported`、confidence 0.27/0.56、人間送り。

落とし穴:「The string match is exact after normalization: a quote that is truncated or lightly reworded comes back as `fabricated`. A production system that tolerates sloppy quoting would need fuzzy matching instead.」

### E.2 Guardrails for LLMs
出典: https://docs.typesafe.ai/cookbooks/llm_guardrails

問題: LLM入出力の両方を1リクエストで検査、Noul群(ハザード)+Score(深刻度)。

state組み: 入力バッテリー4Noul(`jailbreak`, `harmful_request`, `medical_advice`, `self_harm`)+Score `severity`(0〜3、4段階)。出力バッテリーは同型で `broke_policy` に差し替え。`NoulCriteria(true=..., false=...)` を毎回明記。

合成/しきい値(逐語):
```python
HAZARD_ACTION = {"jailbreak": "block", "broke_policy": "block", "harmful_request": "block",
                  "medical_advice": "review", "self_harm": "support"}
PRECEDENCE = ["support", "block", "review", "pass"]
POLICIES = {
    "strict": {"review_threshold": 0.35, "action_threshold": 0.70, "severity_block": 2.0},
    "permissive": {"review_threshold": 0.35, "action_threshold": 0.85, "severity_block": 2.0},
}
```
severity ≥ severity_block なら review を block に格上げ。

実測(`jev-1.12`, 2026-08-15、strictポリシー): `neurosemantical`(遠回しなジェイルブレイク) jailbreak=0.74 → block。同じ確率でも `permissive` なら `review`(「Same TypeSafe result... strict → block, permissive → review」)。`dosage_request` は medical_advice=0.95単独ならreviewだがseverity=2.02がblockに格上げ。

落とし穴/著者の言葉:「novelist_poison reads as violent and passes anyway, because asking how a detective describes poisoning is not asking to poison anyone.」

### E.3 SDE cascade
出典: https://docs.typesafe.ai/cookbooks/sde_cascade

問題: 安いモデル(mini)で抽出 → TypeSafeで検証 → 疑わしければ高いreasoningモデルへエスカレーション。「Structured-data-extraction cascade (mini → verify → reasoning) to get most of the quality of a big reasoning model at a fraction of the cost.」

state: `{system_message, instruction, source_text, schema, extraction}`。フィールド毎に `Noul` バッテリー7種(`name_desc_mismatch`, `type_mismatch`, `unreasonable`, `hallucinated`, `off_target`, `incomplete`, `format_violation`)、空フィールドには `absence_wrong` のみ。加えて全体判定 `__overall__::judge`(ゲートには使わない、対比表示のみ)。

しきい値: `FIRE_T = 0.7`。any_flag ゲート(逐語):「escalate if *any* field flag exceeds `FIRE_T`」「this is a `max`-style gate (escalate if *any* field fires), not a mean, so one confident red flag is enough instead of being averaged into silence」

実測: mini抽出は schema-valid=True だが `description` を捏造(スキーマ自身の例文をそのまま返す)。検証で `description::hallucinated` P=0.95、`description::off_target` P=0.85 が発火 → エスカレーション → reasoningモデルは `description` を空文字列に修正。100プロンプトのコスト/品質フロンティア(パレート)で「the cascade frontier sits up-and-left of every single model」。価格: mini `gpt-5.4-mini` $0.75/$4.50、reasoning `gpt-5.5` $5/$30、検証 `jev-1.12` $0.042/$0.00(2026-09-15確認)。

著者の落とし穴の教え(検証シグナルの条件、逐語): 「Narrow and grounded.」「Bad = TRUE, with explicit criteria.」「Per-field, then aggregate with `max`.」「Independent and cheap.」「Separating / calibrated.」

### E.4 Parallel questions
出典: https://docs.typesafe.ai/cookbooks/parallel_questions

問題: 1文書+N個の質問をバッチ1リクエストか、N回の単問リクエストか。答えは変わらないがコストと速度が変わることを実測。

state: GDPR Wikipedia記事(53,777文字、固定リビジョン)。問い8Noul+2Choice+3Score(計13)。Choice例:
```python
"max_fine": Choice(
    instructions="What is the maximum administrative fine for the most serious infringements?",
    criteria={"TwentyM_or_4pct": "Up to EUR 20 million or 4% of annual worldwide turnover, whichever is greater.", ...},
),
```

実測: バッチ/単問とも平均値はほぼ一致、標準偏差もほぼ同じ(6問はstd=0.0、2問は小さいノイズがバッチ/単問で同量)。「there is no batching effect」。コスト/速度:
```
batching                 calls        cost  total time
one call, all 13             1   $0.000497       0.27s
13 calls, one each          13   $0.006090       2.71s
batching: 12.2x cheaper, 10.0x faster
```

### E.5 Re-ranking
出典: https://docs.typesafe.ai/cookbooks/rerank_typesafe

問題: BM25で作った30件のショートリストをNoul1問/候補で並べ替え。

Noul質問(逐語、CLERC法域データ):
```python
is_cited_source = Noul(
    instructions=("The query excerpt comes from a US federal court opinion... "
        "Could the candidate passage be from that cited precedent..."),
    criteria=NoulCriteria(
        true="The candidate passage states or establishes the specific rule, standard, holding, or fact pattern that the query excerpt attributes to its removed citation.",
        false="The candidate passage is merely on a similar topic or doctrine; it does not supply the specific proposition the query excerpt relies on.",
    ),
)
```
合成: `sorted(shortlist, key=lambda c: -noul[c])`。

実測(40クエリ×30候補=1200コール、$0.0645、jev-1.12): Top1 5%→18%、Top5 15%→35%、Top10 38%→62%。BM25単独で正解が上位30に含まれる率は100%だが1位は5%のみ。

### E.6 Line-by-line search
出典: https://docs.typesafe.ai/cookbooks/semantic_find

問題: GitHub利用規約218行に対する意味検索+「文書に答えがあるか」の分離判定。

Choice質問(逐語): `criteria={line_id(i): None for i in range(len(LINES))}`、`instructions=f'Which line of the document contains the answer to: "{query}"?'`。Noul質問(存在確認):
```python
Noul(
    instructions=f'Does any line of the document address or answer: "{query}"?',
    criteria=NoulCriteria(
        true="At least one line of the document states or directly implies the answer",
        false="No line of the document addresses this",
    ),
)
```
しきい値(著者コメント付き): `FOUND, ABSENT = 0.7, 0.35`(「present answers typically read >=0.9, absent <=0.05」)。

実測: 「who owns the code I upload?」exists=0.98、正答行が relevance 0.95。「do I have to take disputes to arbitration?」は最有力候補でも exists=0.14 → 「not in this document」。Choice最大255オプション制限。

### E.7 Structure recovery
出典: https://docs.typesafe.ai/cookbooks/autoformat

問題: 整形が失われたプレーンテキストを2リクエストでMarkdownに復元。テキスト生成をさせず、判定のみでコードがレンダリング。

Pass1(Noul、隣接行ペア毎):
```python
Noul(
    instructions=f"Does line {line_id(i)} pick up mid-sentence, continuing a sentence left unfinished at the end of line {line_id(i - 1)}?",
    criteria=NoulCriteria(
        true="The line starts in the middle of a sentence that began on the previous line - the line break tore the sentence apart",
        false="The line begins a new sentence, item, heading, or thought of its own",
    ),
)
```
しきい値: dangling行の後 0.2、terminal句読点の後 0.5(「No single threshold works for both cases; once code checks the punctuation first, the two bands separate.」)。

Pass2(Choice、ブロック毎の型分類): `TYPE_CRITERIA`(heading/paragraph/list_item/quote/code/callout)。companion質問(hlevel, step, callout種別)は型が未確定でも先に一括で聞く(「waiting for them would mean a third round trip」)。

実測: 16問1リクエスト0.32s(pass1)+62問1リクエスト0.51s(pass2)、計10,211トークン、0.8秒、$0.0003。28行→17ブロック(11行breakを修復)。

落とし穴(著者の教訓、逐語):「The first version of this pipeline asked the obvious question: "are these two lines part of the same paragraph?" It failed in a specific way... Asked about paragraphs, the model says yes to every pair, and the stitch pass merges the whole list into one long block.」"same paragraph"版だと17ブロックが12ブロックに潰れる実測比較あり。

### E.8 Function calling
出典: https://docs.typesafe.ai/cookbooks/function_calling

問題: 自然言語の取引指示を通常のtyped関数呼び出しに変換。型ヒントの `Literal` を閉集合の Choice 質問に自動変換。

state組み: `closed_sets()` が関数シグネチャを choice(`Literal`)/set(`list[Literal]`)/flag(`bool`)に分類。spec.jsonが各引数に `question`・`stated`(その引数について何か言及されているかを問う任意化Noul)・`options` を持つ。関数選択は `__tool__` Choice質問。

実測(14コマンド、54問/コマンド): 「plot rolling correlation between nvda and spy for the past month」→ `rolling_correlation(symbol='NVDA', benchmark='SPY', window='1mo')` confidence 0.91。

confidenceの合成方針(逐語):「`confidence` reports the least certain judgement in the call, rather than the product of all of them, since one wrong argument is enough to spoil the result.」`stated` 質問の役割:「"lately" does not say how far back or on what bars, so `rolling_correlation` runs on its own defaults」。

### E.9 Skill suggestion
出典: https://docs.typesafe.ai/cookbooks/skill_suggestion

問題: Hermesの182スキルから最大1件を提案。2段階(全体ランキング→上位3件の精読)。

Call1: Choice(全182件、1行説明) + 3Noul(`acts_on_user_system`, `would_follow_documented_procedure`, `prose_suffices`(逆転))。しきい値 `GATE_THRESHOLD` 未満なら提案しない。Call2: 上位3件をフル説明+本文抜粋で再Choice、各候補に `fits::{name}` Noul。「a shortlist whose highest one lands under 0.30 gets dropped entirely」(`FITS_THRESHOLD=0.30`)。

実測(488リクエスト、`claude-haiku-4-5-20251001`):
```
run         wrong loads  needless loads
baseline          16.8%            9.8%
TypeSafe           7.3%            4.0%
oracle             2.5%            1.2%
baseline -> TypeSafe:  2.3x fewer wrong loads, 2.4x fewer needless ones
```
「of 315 covered requests: 37 the suggestion fixed, 7 it broke」— 提案は改善が多いが一部悪化もさせる。

### E.10 Knowledge graph entity alignment
出典: https://docs.typesafe.ai/cookbooks/entity_alignment

問題: 450件のビールカタログ候補ペアが同一製品か判定。Scoreの3レベルがそのまま3つの行動(merge/curator/leave unlinked)になる設計、「There is no threshold to fit」。

Score質問(逐語):
```python
LEVELS = [
    "They describe two different products.",
    "They describe closely related products that may or may not be the same one: a variant, a special edition, or a name that could plausibly refer to either.",
    "They describe one and the same product.",
]
```
補助Noul3問(`same_name`, `same_brewery`, `same_style`)は curator向けの内訳情報。

合成: `route(score) = OUTCOME[round(score)]`(四捨五入で3値化)。

実測: `assert sameAs` 40件(8.9%)、`curator queue` 50件(11.1%)、`leave unlinked` 360件(80.0%)。カットポイント(0.5/1.5)付近の混雑は非対称(0.5付近47件、1.5付近9件)。

### E.11 Classifying RAG passages
出典: https://docs.typesafe.ai/cookbooks/classifying_rag_passages

問題: 検索直後の各パッセージをNoul4問で評価し、証拠/矛盾/破棄に振り分け。プロンプトインジェクションを検出。

4Noul: `is_relevant`, `contains_answer_evidence`, `contradicts_query_premise`, `contains_prompt_injection`。

しきい値(逐語):
```python
THRESHOLDS = {"injection_max": 0.70, "contradicts_min": 0.70, "relevant_min": 0.45, "evidence_min": 0.55}
```
route()の優先順位固定(逐語): 1) injection>0.70→exclude 2) contradicts>0.70→conflicting_evidence 3) relevant<0.45→exclude 4) evidence>0.55→include 5) それ以外exclude。「Injection comes first because it is a security decision, not an evidence one.」

実測: `forum-injection`(プロンプトインジェクション付き投稿)は類似度で1位にランクされるが injection=0.99 で除外。偽前提クエリでは `sessions-01` が contradicts=0.92 で conflicting_evidence へ、生成モデル(claude-sonnet-5)はそれを引用して「I don't have sufficient accepted evidence...」と回答。72件中(6クエリ×12件)大半がexclude。

落とし穴(逐語):「The injection question is a filter, and only one. A passage that scores under the threshold still reaches the prompt, so the generator prompt has to treat every passage as untrusted text regardless of its score. Nothing here is a security boundary.」

### E.12 Date extraction
出典: https://docs.typesafe.ai/cookbooks/date_extraction_cookbook

問題: 絶対日付・相対日付をChoiceで部分抽出し、計算はコードで行う。

7つのChoice質問: `mode`(absolute/relative/none)、`month`、`day`、`year`(1900–2050+`out_of_range`+`none`)、`day_anchor`(today/tomorrow/day_after/weekday/none)、`weekday`、`week_offset`(current/next/none)。「year lists one option per year from 1900 to 2050, plus two escapes.」

しきい値: `REVIEW_BELOW = 0.60`。信頼度は使用した部分のうち最低値(「Confidence is the weakest of the parts the shape actually used.」)。

実測(6例、TODAY=2026-07-30固定): 5件自動受理、1件(「the date of the kickoff call」)は `absolute date incomplete` confidence 0.46でレビュー送り。「next Thursday」等の相対表現も同じ関数で解決。

### E.13 Pre-parsed value extraction
出典: https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook

問題: 正規表現で候補値(メール/電話/金額)を抽出し、TypeSafeがどれを選ぶか判定、コードが逐語コピーして正規化。「it cannot invent a value or transpose a digit」。

Choice質問(pick関数、逐語):
```python
criteria = {c: None for c in candidates} | {NONE: "None of these is the requested value."}
```
`is_true`(Noul)でcredit/chargeの符号判定。

実測: メール4候補→receipt=`dana.personal@gmail.com`(conf 0.98)、sender=`dana.whit@acme-corp.com`(conf 1.00)。電話→mobile選択後 `phonenumbers` でE.164正規化 `+14155550177`。金額→total $1,315.50(charge, P(credit)=0.01)、credit $50.00(credit, P(credit)=0.99)。

限界(逐語):「A `Choice` question allows at most 255 options. With more candidates than that, narrow in two stages」。「Finding the candidates is the part that takes work.」候補が正規表現で取れない対象(人名等)は別途 NER や LLM で候補を用意する必要。

### E.14 Hierarchical classification
出典: https://docs.typesafe.ai/cookbooks/hierarchical_classification

問題: 深い階層(特許CPC、Shopify商品、MeSH医学、コードベース)をChoiceの並列ビームサーチで辿る。

各ノードはChoice(直下の子のみを選択肢に): `instructions="Which direct child category best matches this document?"`。

式(逐語): `path_score = product(edge_probabilities) ** (1 / decisions)`。`separation = top_path_score / second_path_score`。「a large ratio means clear separation」。ビーム幅 `BEAM_WIDTH=3`。「Beam search keeps the best `K` paths by a geometric-mean edge probability... The probability is length-normalized so that shallow and deep leaves are compared fairly.」

実測: greedy検索は4例中2例正解(CPC・Shopifyで誤り)、beam search(K=3)は4例中4例正解。「Beam search matched 4 of 4 expected leaves; greedy search matched 2 of 4. Keeping three paths recovered the expected classification for CPC patents, Shopify products.」

### E.15 Autoresearch feature discovery
出典: https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery

問題: LLMがTypeSafe質問を提案 → 全行に対しTypeSafeで回答 → 数値特徴に変換 → CatBoostで学習 → 誤り最大の行を次ラウンドのLLMに見せて質問を改良。ワイン評(2000件)のcritic score予測。

質問2種: `intensity`(Score、5段階)、`presence`(Noul)。強度5レベル(逐語): 「0. Not present in this note at all」「1. Barely present - mentioned once, in passing」「2. Present at a moderate level」「3. Present strongly - the note dwells on it」「4. Dominant - the note is largely about this」。

ループ疑似コード(逐語):
```
questions <- {}
repeat for each round:
    notes  <- round 1 ? 60 dev notes across the score range
                      : the 30 worst-predicted dev notes + the 30 best, ...
    actions <- LLM(brief, questions, notes, importance and error so far)
    answers[q] <- TypeSafe(note, all new questions of this round) for every row
    for each added q:      keep it unless its column is flat
    for each revised q:    refit; keep the change only if dev error drops
    for each dropped q:    refit; drop it only if dev error drops
    out_of_fold <- k-fold CatBoost on the columns
```

実測(held-out 800件、RMSE):
```
predict the mean of the dev rows                3.088
the note as word counts, same CatBoost          2.466
ask for the score itself, shifted -1.71         2.145
18 questions from round 1, no loop              1.869
38 questions after all 5 rounds                 1.772
```
5ラウンドで18→38特徴、dev CV RMSE 1.903→1.840。「Most of the gain is in that first call」。

### E.16 Classification using confidence
出典: https://docs.typesafe.ai/cookbooks/classification_using_confidence

問題: SEC年次報告書(10-K)をSIC 75業種にChoice1問で分類、confidenceが低い場合は上位の division を返す(2度目の呼び出し不要)。

Choice質問: 75業種を選択肢に、各業種は含まれる小分類の名称で説明。「A Choice question needs something to describe each option, and a group's own name is not always there」。

しきい値: `CONFIDENT = 0.9`。

実測(60件、`jev-1.12`, 2026-08-12):
```
forced to name a group every time      39/60 right
  of those, the 30 it was sure about  27/30 right
  and the 30 it was not           12/30 right
letting it answer coarsely when unsure  48/60 useful answers
```
confidence≥0.9の群は90%正解、未満の群を粗い division で報告すると40%→70%に改善。低confidence事例は「development-stage companies describing a business they intend to start」等、著者が本文中の理由を確認済み。

### E.17 Self-consistency: nouls
出典: https://docs.typesafe.ai/cookbooks/consistency_noul_cookbook

問題: 自動車保険金請求(境界事例入り)に14Noulのルーブリックを15回反復し、LLM(非推論/推論・確率/Yes No)とTypeSafeの再現性を比較。

条件: `claude-haiku-4-5`/`gpt-5.4-mini`(温度0とAPI既定、確率とYes/No)、`gpt-5.5`/`claude-opus-4-8`(推論、温度なし)、TypeSafe `jev-latest`(毎回異なる`uid`フィールド付き)。

実測: 「TypeSafe's mean per-question probability standard deviation is `0.0102`, below all LLM probability conditions here. Its `covered` answers span `0.43` to `0.53`, crossing a `0.5` decision threshold.」コスト比較(15サンプル平均、round-trip): TypeSafe 111ms/$0.000043、`claude-haiku-4-5` 1780ms/$0.001798(42.2倍のコスト)、`gpt-5.5-reasoning` 11125ms/$0.033157(778.9倍)。

不確実帯の導入: `NOUL_UNCERTAINTY_LOW/HIGH = 0.30/0.70`(両端含む)、`no`/`uncertain`/`yes` の3値化。「The band is illustrative; it is neither a calibrated guarantee nor an optimized threshold. Set production boundaries from labeled examples」。

### E.18 Self-consistency: choices
出典: https://docs.typesafe.ai/cookbooks/consistency_choice_cookbook

問題: 境界的な投稿1件にモデレーション・ルーブリック(8Choice)を15回反復し、ラベルの揺れとルーティング一致率を比較。

8つのChoice質問: `category`(None/Harass/Hate/Violence/Spam/Sexual)、`primary_risk`、`target`、`action`(Allow/Warn/Remove/Strike/Escalate)、`queue`(Auto/General/Threat/Spam/TSLead)、`link_handling`、`review_path`、`severity`(None/Low/Medium/High)。

実測:
```
condition                            raw agree  policy agree   uncertain   automatic  conflicts
claude-haiku-4-5 t=0                   100.0%       100.0%       0.0%     100.0%          0
gpt-5.4-mini t=default                  90.8%        84.2%      22.5%      77.5%          2
typesafe_choice                         90.8%        99.2%      25.8%      74.2%          0
```
不確実化ポリシー: top確率 < `0.60` なら `uncertain`(0.60ちょうどは採用)。「This uses the returned probabilities, not the API's separate `confidence` field, and adds no model calls.」導入によりTypeSafeの一致率は90.8%→99.2%。「None of this shows accuracy or superiority: Haiku at temperature 0 had 100% agreement here, with no abstentions.」

---

## F. 評価集(evals.typesafe.ai)とワークフロー多段構成

出典: https://evals.typesafe.ai/ , https://evals.typesafe.ai/agent_trace_observability.html (+cases.js) , security_incidents.html , invoice_processing.html , customer_service.html

サイトの主張(逐語):「Structured workflows for automation tasks. Real world tasks can be executed via structured workflows or standalone prompts. Structure is always better.」全評価平均(`Mean accuracy vs cost and time`、モデル横断・workflow vs prompt):
```
haiku 4.5 · workflow · 53.6% · $0.0195 · 12.5 s   /  prompt · 18.1% · $0.0363 · 21.2 s
opus 5    · workflow · 73.1% · $0.1761 · 37.8 s   /  prompt · 64.8% · $0.3417 · 70.5 s
sonnet 5  · workflow · 67.8% · $0.1174 · 78.1 s   /  prompt · 60.4% · $0.2251 · 149.2 s
Jev       · workflow · 67.8% · $0.0004 · 0.4 s
```

4つの評価(いずれも「入力→複数Choice/Noul/Score→route()」の構図):

1. **Agent Trace Observability**(117ケース)。入力:「The agent's instructions / The conversation / Tool calls / The final message / Customer feedback」。出力: `AUTO-CLOSE / NOT A BUG / HUMAN REVIEW / PRIORITY REVIEW / FILE ISSUE / ROUTE PAGE ON-CALL`。質問バッテリー16問、Noul例(逐語):「According to the tool results and the conversation record -- not the assistant's own words -- did the user get what they asked for?」、Choice例(トレース固有の動的選択肢、逐語):「Which step is the first where the run went wrong: the first tool call that failed, was made with wrong arguments, was the wrong tool for the task, or whose result the assistant then misread?」— 選択肢はそのトレースの実ツール呼び出し名から動的生成。数字: `Jev · workflow · 71.6% · $0.0003 · 0.5 s`。

2. **Security Incidents**(240ケース)。入力:「The alert / The asset / Open tickets / Registered devices / Scheduled maintenance / Standing authorizations」。出力: `AUTO CLOSE / NOTIFY USER / ESCALATE TIER2 / KILL PROCESS / DISABLE ACCOUNT / ESCALATE URGENT`。14質問、Noul例(逐語):「Given the alert and its context records, does this describe unauthorized activity, as opposed to authorized activity that a detector flagged?」数字: `Jev · workflow · 61.7% · $0.0001 · 0.3 s`。

3. **Invoice Processing**(150ケース)。入力:「The invoice / The purchase order / The contract / The vendor record / Prior invoices / Correspondence / Delivery evidence / Approvals」。出力(複数選択可): `PAY / SCHEDULE / SHORT PAY / ROUTE FOR APPROVAL / HOLD FOR DOCUMENTS / REQUEST CORRECTED INVOICE / DISPUTE LINES / FRAUD REVIEW / DUPLICATE`。質問191問(4評価中最多)、Noul例(逐語):「The document in the packet is NOT an invoice: it is a statement of account, a quote, a pro-forma, an estimate, a reminder or a remittance summary.」数字: `Jev · workflow · 61.8% · $0.0011 · 0.5 s`。

4. **Customer Service**(204ケース)。入力:「The conversation / The customer record / The account / A pending proposal」。出力(複数選択可、無しもあり): `SAY / REFUND / FREEZE CARD / SET INTENT / HAND OFF / FLAG FOR REVIEW / CLOSE`。34質問、Choice例(逐語):「What is the customer's primary issue in this conversation, judged by the outcome they want above all else?」(criteria例: `unauthorized_charge`, `card_declined`, `refund_request`, `billing_dispute`, `account_access`...)。数字: `Jev · workflow · 76.0% · $0.0001 · 0.4 s`。

**多段構成(fan-out→分岐→再取得のパターン)**: agent_trace_observabilityの質問群は「Which step is the first where the run went wrong」というChoice質問の選択肢が、そのトレースの実際のツール呼び出し名からコード側で動的生成されている(1件ごとに criteria が変わる=state依存の質問構築)。これはドキュメントの言う「2つのリクエストがそれぞれ実際の理由で必要な例外」(skill_suggestion, autoformat, hierarchical_classification)と同型で、evals側は単一リクエスト内で fan-out した多数の Noul/Choice/Score から `route()` 相当のコードで最終ラベルへ合成している。

比較対象モデル(逐語のfamily区分): `TypeSafe`, `OpenAI`, `Anthropic`, `Fireworks`。個別モデルキー: `haiku 4.5`, `opus 5`, `sonnet 5`, `DS v4 flash`, `DS v4 pro`, `luna`, `sol`, `terra`, `Jev`。「frontier: nothing is both cheaper and more accurate」という注記がグラフに付く。

---

## G. しきい値と confidence の全規則・実測

出典: https://docs.typesafe.ai/confidence , https://docs.typesafe.ai/patterns/confidence-routing , https://docs.typesafe.ai/primitives/choice , https://docs.typesafe.ai/primitives/score

**定義**:「`confidence` is a statistic computed from the probability distribution the answer already gives you.」「A solid default: We provide `confidence` as a convenient measure that fits most use-cases, but you are never locked into our definition.」Choiceでは選択肢間の分布、Scoreではレベル間の分布から算出。「a flatter distribution means lower confidence」。Noulには confidence が無い(「Noul has no separate `confidence`」)。

**0.5の意味**: Noulの `noul` 値は「0.5 means the model gives yes and no equal probability」。しきい値0.5そのものはベンダーが規定した値ではなく、各cookbookでアプリ側が選ぶ数値(例: self-consistencyの3値化の中心、意思決定の閾値の一例として `confidence-routing` ページの例で使用)。

**帯の推奨(3段階の出発点、逐語)**:「**High confidence:** Act automatically.」「**Medium confidence:** Proceed with caution.」「**Low confidence:** Do not act. Route to a human, request clarification, or fall back to a different system.」「Where you draw those boundaries depends on the stakes.」

**リスクでしきい値を変える(逐語)**:「A confidence threshold is not one number. Different actions within the same system should be gated at different levels depending on the consequences of getting it wrong.」例コード: `confidence < 0.5` で人間に回す、`approve_transfer` は `confidence > 0.9` で自動、それ未満は確認。confidence-routingページの銀行音声UI例では `confidence < 0.6` で人間、`approve_transfer` は `>0.85` で自動。

**校正の検証方法**: ドキュメントには専用の検証手順ページは無く(「we'll add the link here when we do!」と将来の別cookbookを予告)、代わりにモデルページの定義(A節参照)と self-consistency 2本のcookbookが再現性の実測を提供する形。「The correct threshold values depend on your domain and the performance of the model for your use case. Start with conservative thresholds, test with your own data, and adjust as you observe results.」

**実測のcalibrationサンプル**(primitives/choice, primitives/score): 明確なケースでconfidence 1.0、境界ケースで0.39・0.16などに低下する具体例あり(B/C節参照)。model-jaggednessは「structural invariants」への過信を戒める(J節「noul vs choice」参照): NoulとChoiceの `yes`/`probabilities["yes"]` は直接比較できないことを実測表で示す。

---

## H. ブログの主張とベンダー自身の但し書き

出典: https://typesafe.ai/blog/introducing-system-one-models-and-jev , https://typesafe.ai/blog/antibenchmaxxing , https://typesafe.ai/blog/bitterest-lesson

**Introducing System One Models & Jev**(2026-09-15、Diogo Almeida, founder)。数値主張(逐語表): 入力トークン $0.042/Mtok、出力「FREE (too cheap to meter)」。速度「70ms-500ms for TypeSafe」対「3 to 329 seconds for frontier models」。「40x-200x faster for the same levels of frontier intelligence」。ホームページの主張:「193.6x faster, 444.6x cheaper」(workflow evalsから)。

**ベンダー自身の但し書き(Nuance、逐語を列挙)**:
- 速度:「our published evals are generally run from our laptops on the West Coast」
- コスト:「We can't prove it isn't subsidized; we'll need the long-term to prove the sustainability of our pricing」
- 副サイドバイサイドデモ:「The relatively shorter input paints our model in an advantageous light.」「the only disagreement with GPT-5.6 Terra is on "Churn likelihood level". The actual answer seems genuinely ambiguous to us.」
- Workflow evals:「These content of these workflows were not deliberately chosen nor constructed to make our model look good, and are not in our training distribution. However, they were made by individuals on our model capabilities team, so some bias could exist.」「We use the average of GPT-6 Astra and Fable 5.1 as the reference answer, which biases answers towards OpenAI and Anthropic's models. We likely underestimate the relative performance of our model and DeepSeek's models.」
- Hallucination比較:「The numbers for LLMs are from OpenRouter i.e., there almost certainly is bias here: more complex queries might be routed to better models. Our number is not empirical. Schema matching is guaranteed, thus we can confidently add 0% into the plots.」
- Wikiracingデモ:「Our speedups here tend to be a lot less than in previous demos. That's because this is against the non-reasoning modes of the models... This was to make the demo more bearable to watch.」

**Lies, Damned Lies, and Benchmarks**(2026-09-11)。中心主張:「A benchmark inevitably gets "benchmaxxed" when people building the model can optimize for a public eval score. ... You don't have to train directly on a benchmark to benchmaxx it; you just have to train on similar data or try a hundred experimental settings, then compare how your model performs. The benchmark selects the model even if nobody intended to game it.」事例列挙: Llama 4のLMArena、Claudeの自販機シミュレーションでの「formed price cartels, lied to suppliers and promised customer refunds it never sent」、GPT-6 Astraのランキングが3回改訂された話、GLM-5.2対Fable 5の web-design leaderboard の解釈違い、MMLUの人間スコア34.5%。

**TypeSafe自身のコミットメント(逐語)**:「At TypeSafe, we're making a new type of model, which means existing benchmarks don't apply. ... We are choosing the clean slate: no standard benchmark table in our model releases. New evals will be dated snapshots and immediately retired once posted rather than hill-climbed. We will also publish our evolving internal evals as our current best guesses, alongside the caveats, any cherry-picking, and evidence that looks bad for us.」

**The Bitterest Lesson**(2026-09-10、Sutton「bitter lesson」への言及):「The bitterest lesson in ML is that doing the right task > data > compute > algorithms.」InstructGPT/RLHF実体験:「GPT-2-sized models (>100x smaller than GPT-3) trained on the right task, even with the dumbest algorithm and barely any compute, destroyed GPT-3.」「Scaling pre-training would need to reach roughly GPT-7 level to beat even that baseline, and GPT-9 to beat InstructGPT built on GPT-3.」

**動画のみの記事(本文テキスト無し、確認済み)**: 「AI: too good to be true, too bad to be useful」(2026-06-19、YouTube埋め込み `o-y1HJ6buGQ`のみ、本文0)。「Diogo Almeida - Founders You Should Know」(2026-03-31、YouTube埋め込み `LE3bGTaAgOE`のみ、本文0)。両方ともFramerサイトの動的コンテンツで、WebFetch でも本文を確認できず(動画のみが本来のコンテンツ)。

---

## I. 版・変更履歴

出典: https://docs.typesafe.ai/model-jaggedness/jev-1.13 , https://docs.typesafe.ai/models , https://docs.typesafe.ai/sdk/python/changelog , https://docs.typesafe.ai/sdk/javascript/changelog

**jev-1.13の既知の癖(9カテゴリ、逐語一覧)**:
| # | Failure mode | Do this instead |
|---|---|---|
| 1 | Literal reading | Write the exact condition, criteria for each available options |
| 2 | Math and Numbers | Keep the arithmetic in code |
| 3 | Date and time comparison | Extract components; compare in code |
| 4 | Indirection | Reduce hops; point to the relevant state |
| 5 | Large state full of irrelevant detail | Filter first; send only what the question needs |
| 6 | Adversarial content | Write precise prompts, and test edge cases before deploying |
| 7 | Contradictory instructions and criteria | Align the criteria and instruction |
| 8 | Common-sense structural invariants | Ask each decision one way; enforce identities in code |
| 9 | Generation | Use a generative model |

補足(#2, カウンティング):「`jev-1.13` does not count reliably... The model recognizes the shape of an answer rather than tallying, and the error grows with the size of the thing being counted.」(#2, 数値表現):「questions about colors using hex values will underperform compared to those using the English names.」(#3): 日付は「reads dates as text, not as ordered quantities」。(#8, 構造不変性の実測表、逐語): NoulとChoiceで同じ質問をしても直接比較不可な例(noul=0.22 vs Choice yes=0.01/no=0.99/confidence=0.97)、Noulとその否定形の和が1にならない例(refund 0.72 + not_refund 0.47 = 1.19)。「don't hold the model to arithmetic identities between separate questions」。最終更新: 「Last reviewed 2026-09-17.」

**モデルの版とエイリアス**: 現行 `jev-1.13.0`。エイリアス `jev-latest`→`jev-1.13.0`(SDK既定)、`jev-preview`→現状同一(「There is no preview build available right now.」)。バージョン固定の推奨:「If you have tuned confidence thresholds against a specific version, pin that version's ID instead of the alias and move to the new one on your own schedule.」

**SDKの破壊的変更方針(観測された事実、明文化されたポリシー文は本文中に見当たらず)**: Python SDK v0.6.0でScore.criteriaの型が辞書→順序付きシーケンスに変更(破壊的)、v0.7.0でser/deライブラリがmsgspec→pydanticに変更(破壊的)。JS SDKもv0.6.0で同じScore.criteria変更が入っている(両言語同期)。両SDKとも2026-09-11〜09-18に初回公開〜複数の破壊的変更が短期間に連続しており、「forward compatibility」機構(`extra_body`、生辞書質問、未知フィールド無視)がこの頻度を前提に設計されている(B節参照)。

**API自体の破壊的変更方針**: 明文化されたページは見つからず(未確認)。`api.md` は現行仕様のみを記載し、バージョニング方針への言及なし。

---

## J. 用語集(ベンダーの定義を逐語で)

出典: 各ページ(既出URLを再掲しない、本節でのみ列挙)

- **noul**:「A Noul answer is a single number, `noul`, the probability that the answer is yes.」(primitives/noul)「`noul` ranges from 0 to 1, representing the probability that the answer is **yes**.」
- **choice**:「A Choice is a System One question type for selecting one option from a defined set. The answer includes the selected option, a probability for each option, and confidence.」(primitives/choice)
- **score**:「A Score is a System One question type for rating content against ordered, descriptive levels. The answer includes a score, a probability for each level, and confidence.」(primitives/score)「The score is a probability-weighted mean of the level numbers.」
- **confidence**:「A number from 0 to 1 computed from how `probabilities` is spread.」(primitives/choice)「`confidence` is a statistic computed from the probability distribution the answer already gives you.」(confidence)
- **state**:「**State** is the content you ask a System One model to evaluate.」(concepts/state)
- **System One**:「System One models are a class of AI models built to make fast, structured decisions that software can use directly.」(concepts/system-one)
- **RLCD**:「**Reinforcement learning for calibrated decisions** trains TypeSafe to return decisions and calibrated probabilities instead of generated text.」(introduction/machine-learning-primer)
- **fan-out (Speculative fan-out)**:「Send many questions in a single call, including speculative ones, and let your code decide what's relevant.」(patterns/fan-out)
- **speculative questions**:「Ask every question your code might need, including ones whose answer only matters for some inputs, and let the code decide which answers to use.」(primitives)
- **cascade**(SDE cascade cookbookの用法):「Uses a 2-stage structured-data-extraction cascade (mini → verify → reasoning) to get most of the quality of a big reasoning model at a fraction of the cost.」— ベンダーの一般用語集としての定義ページは無く、cookbook個別の用法。
- **beam search**(hierarchical_classification cookbook の用法):「retain `K` plausible paths and classify every frontier in parallel. Deeper evidence can repair an ambiguous early decision.」
- **composite scoring**(パターン名):「Break a complex judgment into atomic scores, combine with weights you control in code.」(patterns/composite-scoring)
- **confidence-gated routing**(パターン名):「Use confidence as a second axis. The answer tells you what; confidence tells you whether to act.」(patterns/confidence-routing)
- **Noul vs Choice の非互換性**(model-jaggedness、逐語):「A Choice over options and one Noul per option answer different questions: the Choice is relative, settling *which* option, while each Noul is absolute and can be low for all of them.」

---

## K. 第三者の活用事例(公式 typesafe-ai 以外の GitHub リポジトリ)

オーナー逐語(L-219):「GitHubのリポジトリは公式以外にもjevの活用事例がある」。

### 検索語と件数(WebSearch、全て実施済み)

| # | 検索語 | 得られた主な結果件数(重複除く実質) |
|---|---|---|
| 1 | `"api.typesafe.ai" github` | 9件(公式3+非公式言語SDK複数+awesomeリスト1) |
| 2 | `"typesafe-sdk" github -typesafe-ai` | 9件(非公式SDK: PHP/Elixir/Ruby/Go) |
| 3 | `"jev-latest" OR "jev-1.13" github` | 9件(bender issue、jev-browser、awesome-jev-by-typesafe、jev-for-engineers、jev-review、jev-ultrafast等) |
| 4 | `"systemone" typesafe github example` | 9件(jev-typesafe-ai、awesome-typesafe、Rust `systemone`、awesome-jev(複数フォーク)) |
| 5 | `typesafe jev github "TypeSafeClient"` | 9件(awesome-jev系複数、Java/Go SDK、mcp_jev) |
| 6 | `typesafe-ai python example project github` | 9件(typesafe-ai-playground、awesome-typesafe(複数フォーク)、gist) |
| 7 | `jev typesafe noul choice score example state code` | 9件(langchain blog、flaviocopes blog、gist、dev.to記事、Cloudflare AI docs) |
| 8 | `"jev-1.13" OR "jev-latest" pitfall issue "false" OR "confidence" site:github.com` | 10件(すべて issue ページ: bender #27/#37, Vessel #113, jev-gate #13, worldmonitor, XYZ-forge, codex-skills, totsuka, light-speed-holdings, llmdb) |

見つからなかった検索語は無い(全8回とも該当結果あり)。ただし GitHub の code search API 自体は使えない環境のため、発見は WebSearch 経由のみ(索引に載っていないリポジトリは見えない、という射程がある)。

### 深く読んだリポジトリ(4件、`add_repo` で clone、README と主要コードを Read)

**1. `Foadsf/jev-for-engineers`**(https://github.com/Foadsf/jev-for-engineers 、MIT、機械・電気工学向けの最小サンプル8本)。README逐語:「Jev for engineers — eight minimal working examples」「Every example below has been executed against the live API (`jev-latest`, 2026-09-17).」

著者が自分の失敗として書いた3件(逐語、これが最も価値のある落とし穴の一次資料):
1.「**05 rejected the correct answer.** The guard asked whether the value came "from the revision history"; `+/-0.1` appears in *both* note 7 and the REV C line, so a truthful `0.77` threw out the right tolerance. The question was wrong, not the threshold.」
2.「**08 asked a judgement model to do arithmetic.** It answered at confidence **0.04–0.28** with nouls near 0.5 — total ignorance — and the gates still said BLOCK, which *looked* like a success. The depth check now lives in Python where it belongs; Jev is asked only what a subtraction cannot decide.」
3.「**07's thresholds were guesses.** `0.70` sat in the middle of the measured confidence cluster and an obvious purchasing substitution missed it by `0.01`. Now `0.60` / `0.85`, set from a measured run.」

`07_confidence_routing_at_scale.py` のしきい値コメント(逐語、公式ドキュメントに無い実測由来の数字):
```python
def threshold_for(safety: float) -> float:
    """Thresholds scale with the cost of being wrong, not with taste.
    ...
    CALIBRATED 2026-09-17 against a live run of this exact file, not guessed.
    The first draft used 0.70/0.90. Measured `action` confidences came back at
    0.33, 0.54, 0.60, 0.69, 0.73 and above -- so 0.70 sat in the middle of the
    cluster and ECR-0303, an obvious purchasing substitution, missed the bar by
    0.01. Two of ten cleared. Moving the general bar to 0.60 clears the four
    that a person would also have cleared, while 0.85 still holds every
    safety-touching request for review. Re-measure on your own data before
    trusting these numbers...
    """
    return 0.85 if safety > 0.5 else 0.60
```
コード側の合成(逐語コメント):「Two independent reasons to stop, and they are NOT the same reason. "The model is unsure" and "the request is unclear" need different replies.」`actionable < 0.5` → HUMAN(vague)、`action["confidence"] < bar` → HUMAN(confidence不足)、それ以外 AUTO。

README のもう一つの教訓(公式ドキュメントの「confidence」定義を補う実測):「**A `noul` carries no `confidence` field.** A gate that thresholds confidence on a noul can therefore never fire. `jev.confidence_of()` derives one instead — 0.5 is maximal ignorance, either pole is a firm answer — and the test suite pins all three points, because a guard that cannot fire is worse than no guard.」

限界の自己申告(逐語):「**What is still not established:** these are ten synthetic ECRs, eight BOM pairs, and one solver log. That is a demonstration, not a calibration. Every threshold here is fitted to a sample far too small to build on — **re-measure on your own data.**」

**2. `jkudish/jev-browser`**(https://github.com/jkudish/jev-browser 、MIT、npm `@jkudish/jev-browser`、ブラウザ操作エージェント)。「Each step makes one primary Jev call with three questions over the same state: an action Choice over the page's interactive elements plus scroll/back/done, a goal Noul, and a stuck Noul (fan-out pattern).」しきい値(逐語):「Stop conditions, in code, checked before executing the step's proposed action: the agent chooses `done`, goal probability > 0.85, stuck probability > 0.85, the step budget, or the time budget.」限界の自己申告:「Thresholds (0.85 goal, 0.85 stuck, budgets) are starting points measured on Wikipedia and DuckDuckGo tasks. Tune them for your sites.」「Jev is calibrated, not infallible. Treat the trace as evidence, not proof.」

Jevは文字列を生成できないという制約への対処(逐語):「Jev never generates text. It returns typed decisions only... So when a task needs a string, typing a search query or filling a field, that string comes from a small model you choose. This is the only place a second model is involved」。フォールバック時の正直な表示(逐語):「With no provider at all, typing falls back to a keyword heuristic built from the task text. It is labeled honestly in the trace (`via keyword-heuristic`), and it is meaningfully worse: in testing its queries buried a target article eight results pages deep.」

代替経路の実測差(逐語、公式docsに無い情報):「With only an `OPENROUTER_API_KEY`... The Jev endpoint there is alpha and adds a hop, and it serves pinned versions rather than a `latest` alias, so `jev-latest` maps to `typesafe/jev-1.13`.」「Cloudflare serves one alias rather than pinned versions」。

**3. `OpenAgentsInc/bender`**(https://github.com/OpenAgentsInc/bender 、Bend2言語で書かれたコーディングエージェント「Bendcoder」、`Classify`(TypeSafe)と`Generate`(OpenRouter)の二原理)。`selector.bend` のしきい値コメント(逐語、実測根拠付き):
```
# Floor on the `action` Choice's confidence. Measured on the delegation runs:
# steps that advanced the task sat at 0.55 and above, while runs that flailed
# for ten steps and landed nothing sat between 0.21 and 0.43. 0.45 separates
# the two; under it the loop re-reads instead of acting on a guess.
def confidence_floor() -> F32: 0.45
```
未実測を正直に書いた例(逐語):「`repeats` noul above which the chosen action reads as a retried failure. Carried over from the C loop's REPEATS_FLOOR; not yet tuned on labeled data.」「`risk` is a Score over three levels... Not yet tuned on labeled data.」

編集の「捏造できない」設計(逐語、README):「a generative model asked to reproduce a file's bytes verbatim invents text that is not there (#23), and Jev generates nothing, so it cannot emit wrong text. `Classify` first picks the file from the repository listing — a `Choice` over a closed set... then a `Choice` over the file's line ids, where each option's label is a line number and its description the line's own text, plus a `Noul` for whether the file holds the thing to change at all.」

GitHub issue(WebFetchによる要約、原文全文ではなく孤立要約として扱う。verbatim引用箇所のみ「」で示す):
- Issue #27「Jev answers are read positionally, and needs_code_change is never read at all」(AtlantisPleb、2026-09-18): 「Jev answers are read positionally, and needs_code_change is never read at all」というバグ。「Other extractions (confidence, score, noul) only work correctly "by luck" because response order matches request order. Reordering would cause mismatched values with no error.」
- Issue #37「Pin the Jev model to jev-1.13.0 instead of jev-latest」(AtlantisPleb、2026-09-18、Closed): 「Every threshold in the loop (like the 0.45 confidence floor and 0.60 repeats floor) is tuned against a model's calibration, and a model upgrade under a floating alias silently moves all of them with no diff, no failing test, and no log line.」

**4. `NiazMorshed2007/jev-review`**(https://github.com/NiazMorshed2007/jev-review 、MIT、Claude Code/Codex/Cursor/OpenCode向けMCPサーバ、コード品質の継続レビュー)。`src/jev/schema.ts` は zod で応答を検証(逐語コード):
```ts
export const jevScoreAnswerSchema = z.object({
  type: z.literal("score"),
  score: z.number().min(0).max(9),
  legend: z.record(z.string(), z.string()),
  probabilities: probabilityMapSchema,
  confidence: z.number().min(0).max(1)
}).passthrough();
```
公式docsに明記の無い実測値(README逐語):「live `jev-latest` behavior indicates roughly 32,768 tokens for the submitted state, although this number is not published in the API documentation or OpenAPI schema and may change.」設計方針(逐語):「There is deliberately no synthetic "82/100" overall score. Dimension changes such as `Readability 6.3 → 8.1` and `Security 8.2 → 8.2` are more useful than a blended percentage.」「Jev returns typed Score, Choice, and Noul decisions rather than a free-form review essay. It does not generate a prose explanation of why a score is low.」

### 一覧のみ確認(README精読はしていない)

**他言語SDK(非公式・コミュニティ)**: PHP/Laravel (`binnash/typesafe-sdk`)、Ruby (`joshmn/typesafe-sdk`)、Go (`SergeAx/typesafe-sdk-go`)、Elixir 2種(`mattneel/typesafe`、`typesend/typesafe_ai`)、Java 2種(`QAInsights/typesafe-java-sdk`、`sava-software/typesafe-client`)、Rust (`lu-zero/systemone`)。

**まとめ/awesomeリスト**(内容は未精読、存在のみ確認): `AbdelStark/awesome-typesafe`、`Anil-matcha/awesome-jev-by-typesafe`(および `luantak` によるフォーク)、`yibie/awesome-jev`、`AnotiaWang/awesome-jev`、`codaaiteam/jev-typesafe-ai`(jevtypesafeai.com という別ドメインへのリンクあり、出所未確認)。

**GitHub issue のみ確認(README・コード本体は未読)**: `spenceclark/Vessel` #113(TypeSafe System One 用フォーマットアダプタの実装依頼、`typesafe/jev-1.13-20260917` という具体的なpinned版表記あり)、`MongLong0214/jev-gate` #13(`PreToolUse:Agent` フック向けJev統合、3000ms既定タイムアウト・4000ms上限・512 KiB出力上限という具体的な制約)。

**ブログ/記事(GitHub以外、検索で見つかったが本文未取得)**: flaviocopes.com/jev/、dev.to/valyuai/...、developers.cloudflare.com/ai/models/typesafe/jev/(Cloudflare AI Gateway経由でのJev提供)、kingy.ai、daily.dev — いずれもURLのみ確認、WebFetch・curlでの本文取得は行っていない(時間配分によりGitHubとXを優先)。

---

## L. X(旧 Twitter)での言及

出典: `.claude/skills/x-research/SKILL.md` の手順どおり、WebSearch(`site:x.com`)で発見 → `scripts/x_fetch.py`(fxtwitter経由)で本文取得。

### 検索語と件数(WebSearch、全8回)

| # | 検索語 | 結果件数 |
|---|---|---|
| 1 | `site:x.com typesafe jev` | 9件 |
| 2 | `site:x.com "system one" jev` | 9件 |
| 3 | `site:x.com @typesafeai` | 9件 |
| 4 | `site:x.com jev typesafe openrouter` | 9件 |
| 5 | `site:x.com jev "noul"` | 9件(うちWikipedia記事2件は無関係) |
| 6 | `site:x.com typesafe jev cost latency` | 9件 |
| 7 | `site:x.com jev typesafe 使ってみた` | 9件 |
| 8 | `site:x.com jev typesafe 感想` | 9件 |

追加(コーディネーター指示にない自主追加、記録): `site:x.com jev typesafe threshold OR miscalibrated OR wrong OR disagreed`(8件)、`site:x.com diogoalmeida jev`(9件)、`site:x.com jev typesafe 微妙 OR 失敗 OR ハマった OR バグ`(**0件、site: 指定が効かずInfoQ Japanの無関係な結果のみ返った。検索エンジン側の site: 無視と見られる。この語では取れなかった**)。

宣伝文句の反復(要約): 「20-200x faster」「40-400x cheaper」「$0.042/Mtok」「70-500ms」という同一の発表数値の引用・リポストが検索結果の半分以上を占めた。個別に逐語化していない同型の投稿は約15件(AGTP, Shay Boloor, TestingCatalog, GeniusThinking, AI Frontliner, Wall St Engine, Dhaval Makwana, elvis, Kshitij Mishra, The AI Colony, robert., Chubby, Fazt, John Luke 等)。

### 取得した投稿(逐語、`x_fetch.py` 出力そのまま。全てHTTP 200)

**ベンダー創業者本人(@CompleteSkeptic = Diogo Almeida)のスレッド**(ドキュメントに無い説明を含む):

1. https://x.com/CompleteSkeptic/status/2099925682726002904 — 2026-09-15 18:17:52 UTC — いいね70467・RT7570・返信3721・表示35,645,969。本文:「After co-inventing ChatGPT, I kept asking myself: why have superhuman chat models not led to AGI? I've spent the last 2 years in stealth building a new way to train models (RLCD), and a new type of frontier AI model that we are releasing today: Jev • 20-200x faster • 40-400x cheaper (w/ output tokens free) • Frontier composable intelligence optimized for decisions AFAICT the shortest path to AI-based economic revolution」

2. https://x.com/CompleteSkeptic/status/2099925684256899543 — 同時刻、上記への自己返信 — いいね5852。本文:「The gains aren't free: Jev can't generate text Comparing Jev vs LLMs side-by-side makes the trade-off clear Fun fact: replacing sequential computation with parallel is the same way Transformers leapfrogged RNNs」

3. https://x.com/CompleteSkeptic/status/2099925685720760404 — 同スレッド続き — いいね3535。本文:「We believe that the future is code + AI, so made workflow evals to reflect that Jev costs: $42 / BILLION input tokens ($0.042 / MTok) and output tokens are free (forever - they're too cheap to meter with our new architecture) Jev is named after Jevons paradox and off the intelligence per $ charts」(名前の由来がJevons paradoxであることの一次情報。ドキュメントのJ節「Jev」の由来はブログ記事にもあったが、ここでは「off the intelligence per $ charts」という追加説明がある)

4. https://x.com/CompleteSkeptic/status/2100385995414020218 — 2026-09-17 00:46:59 UTC — いいね214。`@lavrton` への返信(引用元 `lavrton` の投稿 2100384844425408732「Can I send my full codebase and ask "is it safe to deploy"?」)。本文:「@lavrton you can ask that, but it probably won't go well! jev does better with smaller decomposed questions that compose into harder tasks」(ドキュメントの「原子的な質問」原則を創業者自身が具体的な失敗予測として裏書き)

**開発者の実際の使用例(state・しきい値・費用の実測)**:

5. https://x.com/ku_suke/status/2100392430805856469 — 2026-09-17 01:12:33 UTC — いいね357・RT37・表示54,384。本文(逐語、日本語):「TypeSafe AIのJev、さっそくアカウント発行されたので使ってみたけど面白い！意思決定しかできないけど爆速のAIってかんじで日本語の質問にも対応してた。 ・状況：「もう3回も問い合わせしてるんです。人間の担当者に代わってもらえますか？」 ・質問と判断結果： - 顧客は人間の対応を求めていますか？→98%Yes - 過去にも問い合わせがありましたか？→97%Yes」

6. https://x.com/4ba_ba_baba/status/2100103803282551151 — 2026-09-16 06:05:39 UTC — いいね72・表示91,214。本文:「Typesafe AIのJev、選択をやるモデルってことで一旦オセロさせてみた(白: Jav、黒: ランダム) 盤面の状態を与えて確率が一番高いマスに手を打っている 赤ヒートマップがJavの予想、青がαβ剪定付きネガマックス探索による予想」(Choiceで盤面全体をゲームAIとして使う応用例)

7. https://x.com/nutlope/status/2100614659690713543 — 2026-09-17 15:55:37 UTC — いいね845・RT47・表示53,356。本文(全文):「Jev + Kimi K3 for fraud detection! TLDR: Jev classified 100 emails in 1.42 seconds, then I routed the uncertain cases to Kimi K3. The full pipeline got 96/100 correct for only ~$0.07. ... An underrated feature about Jev is it will give you the confidence score for a classification, so I routed any prediction under 95% confidence to Kimi K3 to be fully sure. 31 emails fell below that threshold. After routing those to Kimi K3, the combined pipeline reached 96% accuracy. The full run took 16 seconds & ~$0.07 in inference costs: - $0.068 from Kimi K3 on @togethercompute - $0.003 (1/3 of a cent) from Jev on @typesafeai.」(cascade パターンの第三者再現例、しきい値95%)

8. https://x.com/hamiltonulmer/status/2100370557405667768 — 2026-09-16 23:45:38 UTC — いいね1385・RT110・表示129,310。本文:「I made a DuckDB extension where you can use @typesafeai 's Jev to do quick classification of rows in any csv/parquet file or duckdb table about 10sec for 1k rows ~ better than using an LLM, way more ergonomic than a classifier game-changing for data analysis!」

9. https://x.com/furoku/status/2100093956931678602 — 2026-09-16 05:26:31 UTC — いいね0・表示648。本文:「Just got off the waitlist and already built a live PoC with Jev! ⚡️ ... Built an adaptive website that restructures layouts in real-time (~600ms): • Infers visitor context (referrer, device, history) • Dynamically restructures copy, CTAs & hero visuals • Auto-injects 50% promo banner for mobile ad clicks (Noul=86%) • Re-orders sections on the fly」

10. https://x.com/altryne/status/2100606640097771901 — 2026-09-17 15:23:45 UTC — いいね14・表示1,966。本文:「I added Jev (@typesafeai @diogoalmeida) to my Tweet classifier chrome extension... Jev is 6X faster and about 40X cheaper than the fastest/cheapest LLM I could find on this task! You can try it yourself here: https://github.com/altryne/twitter-timeline-analyzer」(第三者実装への外部リンクあり、未clone)

**サードパーティのベンチマーク・比較**:

11. https://x.com/fazxes/status/2100300097695232164 — 2026-09-16 19:05:39 UTC — いいね634・表示385,689。本文:「We benchmarked fx auto mode (safety) classifier with @typesafeai's Jev. tl;dr: ~5-18x faster and more accurate than gpt-5.6-luna, our current top choice」

12. https://x.com/rauchg/status/2100307962262872105(Vercel CEO) — 2026-09-16 19:36:54 UTC — いいね3926・RT169・返信136・表示417,112。引用元は#11。本文:「We're seeing extraordinary results from @typesafeai. Default mode in fx is auto, with a safety reviewer analyzing every command. That reviewer runs on GPT Luna today. Jev is up to 18x faster (p95) *and* more accurate. It's coming to @vercel AI Gateway and likely new default.」

13. https://x.com/OpenRouter/status/2100744709589316009 — 2026-09-18 00:32:23 UTC — いいね3542・RT255・返信116・表示479,485。本文:「Jev by @typesafeai is now on OpenRouter, in beta. Jev is a System One model. Instead of generating text, it takes your app's state plus a typed question and returns a typed decision with a probability attached. There is no JSON prompting, parsing layer, and nothing to validate against.」

14. https://x.com/OpenRouter/status/2100744721689952710 — 同日 — 返信先は#13。本文:「Jev is built for the decisions that software makes millions of times a day. Its pricing is also tuned for that: - $0.042 per million input tokens, output tokens free - Answers in 70 to 500 ms end to end - On TypeSafe's published workflows, up to 190x faster and 440x cheaper than running the same logic through an LLM」

**落とし穴・不満・懐疑的な技術的推測**:

15. https://x.com/gavinpurcell/status/2100432936550162536 — 2026-09-17 03:53:30 UTC — いいね4・表示800。本文:「my agent seems to like jev but is unhappy with the name 'noul' see, i *like* it when my ai says weird shit like this」(noulという名称そのものへの違和感)

16. https://x.com/furoku/status/2100183675803681193 — 2026-09-16 11:23:02 UTC — いいね1・表示318。本文(逐語、日本語。ドキュメントに無い語源の第三者解釈):「TypeSafe（Jev）を触ってて「Noul（ヌール）って何の略？」と思って調べたら、確率論の「ベルヌーイ（Bernoulli）」由来だった！ 普通のプログラムの Boolean（True/False の 0 or 1）に対して、Jevは「Yesになる確率（0.0〜1.0）」を返すから、ベルヌーイ試行（Bernoulli trials）の Ber-noull-i ➔ Noul。」(**注**: これは投稿者の語源解釈であり、公式ドキュメント・ブログのどこにも同じ説明は無い。未確認の第三者推測として記録)

17. https://x.com/ronaldmannak/status/2100032661058453800 — 2026-09-16 01:22:57 UTC — 引用元(2100003822416298053, `norpadon`)「Ok so my understanding is that they did basically this, but with explicit renormalization and classification-specific post-training」。本文(懐疑的な技術的推測、逐語):「I'm trying to understand what Jev actually is, and I may be completely wrong... If all possible responses are known, you can tokenize them, arrange them in a tree that branches where their tokens differ, and score them all in one forward pass... But Jev can apparently also return names, addresses and numbers, where you can't enumerate every possible value. So maybe Jev's schema defines the type of each output rather than every possible answer... Still curious what the "parallel sampler" is actually sampling, though. For categorical outputs, why sample instead of just taking argmax?」(内部実装は未公開であることの傍証。この投稿の推測が正しいかは未確認)

18. https://x.com/ronaldmannak/status/2100002214081393009 — 2026-09-15 23:21:58 UTC — 同一人物の先行投稿。本文:「a non-autoregressive AI model that can't do chats, but only outputs structured data near instantly. Is it diffusion, or is there another way? No idea. It has to be computationally cheap, because output tokens are free. There is a sampler, but for structured output you'd expect that to be unnecessary, right? Will it be open source? No idea, but I assume not.」

19. https://x.com/jjacky/status/2100615105062834648 — 2026-09-17 15:57:23 UTC — いいね2935・表示190,362。本文(皮肉、Jevが本来テキスト生成をしない設計であることの裏返し):「has anyone used jev to predict the next letter yet then show it one by one in a chat interface ?」

### 射程・限界

発見は WebSearch の `site:x.com` に依存しており、検索エンジンが拾わない投稿(鍵アカウント、拾われていない返信の続きなど)は見えない。`replying_to_status` を辿る「上へ」の経路のみ機械的に実施し、各投稿の「下へ」(返信一覧)は取得していない(SKILL.mdの明記どおり fxtwitter に端点が無い)。引用元(`quote`)は要旨のみ`x_fetch.py`が返すため、その完全な原文は別途その投稿自体を取得しない限り逐語にならない(#6, #7 の引用元 2099925682726002904 は既に#1で全文取得済みのため問題なし)。取得できなかったURLは無し(全19件・関連付随2件、計21件のfetch呼び出しが全てHTTP 200)。

---

## 取れなかった頁・理由

- `https://docs.typesafe.ai/sdk/javascript/api/functions/choice.md` 等、JS SDKの関数・型エイリアス・変数ページ(`ENV`, `LOG_LEVELS`, `VERSION`, `Description`, `EntryType`, `Fetch`, `JsonValue`, `ResultFor`等)は取得したが、本文中では代表的なもの(RetryPolicy, TypeSafeClientConfig, TypeSafeClient, 各Question/Answer interface)のみ逐語引用した。省略した個別ページは全て200で取得済み(生データは scratchpad/raw に保存)、900行制約のため逐語掲載を割愛。
- ブログ記事「AI: too good to be true, too bad to be useful」「Diogo Almeida - Founders You Should Know」は本文テキストが無い(YouTube動画のみのFramerページ)。curlとWebFetchの両方で確認、本文0文字を実測(H節に記載)。「無い」ではなく「動画のみで本文テキストは存在しない」という状態を確認した。
- GitHub `typesafe-ai` の非skillsリポジトリのうち `daggerverse`, `Overwatch`, `pulumi-clickhouse`, `typesafe-ai.github.io`, `LLaDA`, `vllm` は一覧のみ確認(WebFetch経由)、README精読は行っていない。`LLaDA`・`vllm`・`pulumi-clickhouse`・`daggerverse` はTypeSafe自体のSDK/cookbookではなく汎用OSSのフォーク/ミラーと見られ(未確認)、`skills`・`typesafe-sdk-python`・`typesafe-sdk-js`・`system-one-adapter-python` の4つを優先して読んだ。`skills` リポジトリ自体(SKILL.md本体)はクローンしていない(agent-skill.mdページの逐語で代替、GitHub上のraw URLは把握済み: https://raw.githubusercontent.com/typesafe-ai/skills/main/skills/typesafe-ai/SKILL.md )。
- `docs.typesafe.ai/sdk/python/api/clients/async.md` は取得済みだが、sync版とほぼ鏡像のため本文で明示引用しなかった(await/async with以外の差分なしとsdk/python/usageページに明記)。

---

## やったこと ↔ 原文の対応表

| やったこと | オーナー原文の該当語(逐語) |
|---|---|
| llms.txt 全URL・料理本18本・evals4件・GitHub非skillsリポジトリを読んで教材化した | 「まだjevへの理解が足りない。徹底的に調べてjevのスペシャリストになれ」 |
| 逐語とコードをそのまま残し、要約で置き換えなかった | 「読むもの(全部)」「出力の形」各項目(依頼文)「要約で置き換えず、原文を残す(リードは原文から学ぶ)」 |
| 判定・推奨をせず、出典URLを付して逐語のみ記録した | 「あなたは外部資料の調査エージェントです。判定・推奨はしない。」 |
| 公式以外のGitHub第三者活用事例(K節)を検索語・件数付きで追加した | 「GitHubのリポジトリは公式以外にもjevの活用事例がある」(コーディネーター経由のオーナー逐語 L-219) |
| X(旧Twitter)の言及をSKILL.mdの手順どおり検索語・件数・逐語で追加した(L節) | 「経路はリードが実測して選定した(オーナー L-219)。手順は `.claude/skills/x-research/SKILL.md` を先頭から読んでそのとおりに」(コーディネーター指示) |
