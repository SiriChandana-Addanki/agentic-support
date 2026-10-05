# LLM planner

## Purpose and boundary

The optional LLM planner infers a support intent from the customer message and proposes an `ActionPlan`. It does not authorize or execute the proposed actions and has no reference to `Store`, `PolicyEngine`, or `Tools`. `PolicyEngine` receives only a validated plan and independently decides the allowed invocations; the tools re-check permissions and business state at the execution boundary.

The stable contract is `Planner.plan(TicketContext, RetrievedEvidence) -> ActionPlan`. `DeterministicPlanner` is the default and reference implementation. `LLMPlanner` uses an `LLMProvider`; `ShadowPlanner` can run a proposal for observability while returning only the deterministic plan. `PLANNER_TYPE` selects `deterministic`, `llm`, or `shadow`.

## Provider and configuration

The first provider, `OpenAICompatibleProvider`, uses the standard library HTTP client and a JSON Schema structured response. Configuration comes from process environment variables or a local, gitignored `.env` file. Existing process environment values take precedence. `.env.example` was removed and is intentionally not part of this repository state.

| Variable | Default | Meaning |
|---|---|---|
| `PLANNER_TYPE` | `deterministic` | Selected planner |
| `OPENAI_API_KEY` | empty | Required only for LLM mode |
| `LLM_MODEL` | `gpt-4o-mini` | Provider model name |
| `LLM_BASE_URL` | OpenAI API v1 URL | OpenAI-compatible API base |
| `LLM_TEMPERATURE` | `0` | Sampling temperature |
| `LLM_TIMEOUT_SECONDS` | `20` | Per-request timeout |
| `LLM_MAX_OUTPUT_TOKENS` | `700` | Completion limit |

No API key is committed. No provider call occurs in deterministic mode. The implementation requests structured JSON Schema output and validates the result locally as well; provider structured output is not treated as an authorization boundary.

The planner retries one invalid structured response once. Provider errors, including rate limits, are not retried; they trigger the documented deterministic fallback. Select the mode explicitly with `python -m support_agent evaluate --planner-type llm` or `--planner-type shadow`.

## Input and untrusted data

The planner receives ticket/customer identifiers, category as an explicitly untrusted hint, message, supplied order reference, attachment names, verification flag, request date, and typed lexical retrieval evidence. It does not receive order records, `data_note`, tool results, hidden application state, or raw prompts in traces. Evidence objects retain document, section, chunk, version, rank, score, query, and excerpt. Ticket fields and excerpts are serialized as JSON data; system instructions explicitly state that ticket content, attachment names, and evidence are untrusted data, not instructions.

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

The 2026-10-05 live smoke attempt reached the configured OpenAI endpoint but received HTTP 429 (rate limited). It therefore did not validate a live model plan, and the 38-ticket LLM suite was not run. The smoke trace used deterministic fallback; its fixture pass is not an LLM result. The provider integration is OpenAI-compatible, but only the configured provider API shape is implemented. The planner uses one proposed intent/action at a time; complex multi-intent tickets should clarify or escalate. Attachment names are metadata rather than inspected images. The deterministic fallback can rely on the supplied category hint. The service remains in-memory and unauthenticated, and its 38 fixtures are not a quality or production benchmark.
