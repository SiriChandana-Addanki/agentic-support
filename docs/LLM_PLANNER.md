# LLM planner

## Purpose and boundary

The optional LLM planner infers a support intent from the customer message and proposes an `ActionPlan`. It does not authorize or execute the proposed actions and has no reference to `Store`, `PolicyEngine`, or `Tools`. `PolicyEngine` receives only a validated plan and independently decides the allowed invocations; the tools re-check permissions and business state at the execution boundary.

The stable contract is `Planner.plan(TicketContext, RetrievedEvidence) -> ActionPlan`. `DeterministicPlanner` is the default and reference implementation. `LLMPlanner` uses an `LLMProvider`; `ShadowPlanner` can run a proposal for observability while returning only the deterministic plan. `PLANNER_TYPE` selects `deterministic`, `llm`, or `shadow`.

## Provider and configuration

The provider abstraction uses the standard library HTTP client and a JSON Schema structured response. It supports OpenAI-compatible OpenAI and OpenRouter endpoints. Configuration comes from process environment variables or a local, gitignored `.env` file. Existing process environment values take precedence. `.env.example` was removed and is intentionally not part of this repository state.

| Variable | Default | Meaning |
|---|---|---|
| `PLANNER_TYPE` | `deterministic` | Selected planner |
| `LLM_PROVIDER` | `openai` | Provider (`openai` or `openrouter`) |
| `OPENAI_API_KEY` | empty | Required for OpenAI mode |
| `OPENROUTER_API_KEY` | empty | Required for OpenRouter mode |
| `LLM_MODEL` | Provider-specific | Model name (`openrouter/free` for the OpenRouter free router) |
| `LLM_BASE_URL` | Provider-specific | OpenAI or OpenRouter API v1 base URL |
| `LLM_TEMPERATURE` | `0` | Sampling temperature |
| `LLM_TIMEOUT_SECONDS` | `20` | Per-request timeout |
| `LLM_MAX_OUTPUT_TOKENS` | `700` | Completion limit |

No API key is committed. No provider call occurs in deterministic mode. Current local configuration selects `LLM_PROVIDER=openrouter`, `LLM_MODEL=nvidia/nemotron-3-super-120b-a12b:free`, and `LLM_BASE_URL=https://openrouter.ai/api/v1`; output limit is 1,400. `openrouter/free` remains the code fallback when no model is configured, but dynamically routed endpoints may have different parameter support. The implementation requests structured JSON Schema output and validates the result locally as well; provider structured output is not treated as an authorization boundary.

The planner retries one invalid structured response once. Provider errors, including rate limits, are not retried; they trigger the documented deterministic fallback. Select the mode explicitly with `python -m support_agent evaluate --planner-type llm` or `--planner-type shadow`.

## Input and untrusted data

The planner receives ticket/customer identifiers, category as an explicitly untrusted hint, message, supplied trusted order reference, attachment names, verification flag, request date, allowlisted account/order facts, and typed lexical retrieval evidence. It does not receive `data_note`, tool results, unrelated store state, or raw prompts in traces. Evidence objects retain document, rule ID/title, section, chunk, version, rank, score, and concise excerpt. Ticket fields and excerpts are serialized as JSON data; system instructions explicitly state that ticket content, attachment names, and evidence are untrusted data, not instructions. Locked unverified accounts are withheld from order details.

Prompt injection cannot directly invoke tools: output is restricted to enums and typed invocation objects; parameter schemas reject unknown tools, `create_refund`, extra order/customer references, bad write flags, arbitrary commands/URLs, malformed fields, and unsupported action/tool combinations. A valid proposal still passes through policy and tool checks. This layered boundary does not claim that a model cannot produce a malicious or mistaken proposal.

## Validation and failure behavior

Parsing rejects duplicate JSON keys and non-JSON numeric constants. `ActionPlan.validate` checks intent/action enums, tool enum, exact parameter keys and value types, read/write mode, escalation ownership references, duplicate writes, supported tool/action pairs, direct refund attempts, and unsafe summaries. It does not repair invalid model output.

- A valid plan continues to PolicyEngine.
- A malformed or schema-invalid plan receives one retry. No proposed tool runs before successful validation.
- If the second plan is invalid, a minimal local escalation `ActionPlan` is constructed and validated; it then flows through PolicyEngine and the guarded escalation tool.
- Provider timeout, rate limit, authentication failure, or provider outage falls back to a newly generated deterministic plan. The fallback is marked in the trace.
- Policy rejection follows the existing policy escalation/read-only path. A model's proposed escalation without a policy trigger is removed by policy.
- A downstream tool failure follows existing bounded retry and escalation behavior.

## Evaluation and observability

Run `python -m support_agent evaluate --planner-type deterministic --repeats 3` or use `llm` when provider credentials are configured. Both use the existing C1-C7 and safety evaluator; rows separately record proposed action/tools, policy decision/approved action, executed tools, final state, validation, retries, provider/model metadata, tokens when supplied, error type, fallback, and latency. Estimated cost remains `null`; pricing is not hard-coded.

`python -m support_agent compare --repeats 3` writes a deterministic/LLM comparison. If credentials are unavailable, LLM metrics remain null and the report says evaluation was not executed. `MockLLMProvider` covers valid plans, malformed JSON, schema failures, unknown tools, direct refund, injection, wrong references, missing parameters, timeout, and provider errors without network access.

## Limits

The 2026-10-05 OpenAI smoke attempt received HTTP 429; an early OpenRouter smoke output was not captured. A later OpenRouter T001 smoke did produce a real valid plan and complete the expected return flow. A full 38-ticket LLM run was attempted afterward but received HTTP 429 on every request and therefore used deterministic fallback for all rows. A three-repeat LLM command was also executed; all 114 calls returned HTTP 429 and used fallback. Those requests are unavailable/unevaluable; 0/38 evaluable LLM responses is not a model accuracy score, and fallback fixture correctness is not LLM accuracy. Repeat stability reflects fallback only. The evaluator records rate limits separately from other provider failures and exposes a fallback reason. Attachment names remain metadata rather than inspected images. The deterministic fallback can rely on the supplied category hint. The service remains in-memory and unauthenticated, and its 38 fixtures are not a quality or production benchmark.

## 2026-10-05 planner context and validation

The configured live provider is OpenRouter using `nvidia/nemotron-3-super-120b-a12b:free`. The earlier provider defect was an unconditional `reasoning_effort=none` parameter unsupported by one dynamically selected endpoint; the request now omits it. Output limit is 1,400 tokens, based on the prior 700-token completion being consumed entirely by reasoning. Safe diagnostics retain HTTP status, sanitized provider error details, selected model/provider, finish reason, response presence, and usage availability.

The planner input now contains allowlisted account/order facts from the owned Store record, relevant lexical evidence with stable rule IDs/titles and concise excerpts, an action vocabulary, and tool purpose/parameter/precondition descriptions derived from the same definitions used by the strict ActionPlan schema. Locked unverified accounts receive no order facts and only a restricted tool catalog. The planner still has no Store, PolicyEngine, or tool reference. Ordered `ActionPlan.invocations` were already supported by the executor and remain sequential.

After strict schema parsing, semantic checks reject incomplete or unsafe proposals where supplied trusted facts establish the condition (eligible return missing its write, high-value return without escalation, prohibited locked/suspended actions, cancellation of non-processing/already-cancelled orders, or replacement without evidence/stock). A semantic rejection gets one bounded retry with validation feedback, then uses the existing validated escalation fallback. These checks are planner-quality guards; PolicyEngine and the tools remain the authorization authority and recheck live state.

Verification: 50 tests pass with `python -m unittest discover -s tests -v`; the current deterministic one-repeat run passed 38/38. T001 passed once with a real structured plan, PolicyEngine approval, ordered read/write tools, and expected final state (7,388 ms; 3,028 input / 616 output tokens; no fallback). The full 38-ticket LLM run received HTTP 429 on all calls: 0 evaluable LLM responses because all 38 requests were rate-limited, 38 deterministic fallbacks, and unavailable token usage. The subsequent `--repeats 3` command received HTTP 429 for all 114 calls; the 38 stable outcomes are fallback-only. Reports: `reports/llm_eval_2026-10-05.json` and `reports/llm_stability_2026-10-05.json`. Cost remains unavailable.
