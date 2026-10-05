# Agentic Support / Ticket Resolution System

A **development-only deterministic support workflow baseline** for the supplied CSV/JSON dataset, with an optional OpenAI-compatible LLM planner. It is not production authenticated. It demonstrates a typed planner → policy → tool boundary: untrusted ticket text can propose no executable instruction; only a validated action plan and independently authorized tools may change state.

## Run
```bash
python -m unittest discover -s tests -v
python -m support_agent serve
python -m support_agent evaluate --repeats 3
python -m support_agent evaluate --repeats 3 --planner-type llm
python -m support_agent compare --repeats 3
```
`POST /tickets` processes the JSON supplied by the caller (it never substitutes a fixture by ID). Required JSON fields are `ticket_id`, `customer_id`, `category`, and `message`; optional fields are `order_id`, `attachments`, and `verified`. `POST /evaluations` is the separate fixture-only endpoint. Both are unauthenticated development endpoints; do not expose resolutions or traces publicly.

## Architecture
The interchangeable planner contract returns a typed, strictly validated `ActionPlan`. `DeterministicPlanner` remains the default; `LLMPlanner` can propose a plan through a provider interface and cannot access `Store`, policy, or tools. `PolicyEngine` authorizes independently, and `Tools` independently revalidate ownership, account status, lifecycle, idempotency, evidence, stock, serviceability, and action-specific rules. `PLANNER_TYPE=shadow` optionally runs the LLM for comparison while the deterministic plan remains authoritative. The CSV `Store` models action outcomes in memory. `Retriever` performs lexical ranking over `data/business_rules.md` and returns typed evidence with document/section/chunk/version/rank/score/query metadata; it is not semantic RAG.

No direct refund action exists. Returns only initiate downstream QC/refund handling. Attachment filenames are metadata only; no image is fabricated or inspected. Development principal identity is the supplied customer ID and is **not production authentication**. The optional OpenAI-compatible provider supports OpenAI or OpenRouter. It reads `LLM_PROVIDER`, the matching `OPENAI_API_KEY` or `OPENROUTER_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_TEMPERATURE`, `LLM_TIMEOUT_SECONDS`, and `LLM_MAX_OUTPUT_TOKENS` from process environment or local `.env` (gitignored). Process environment values take precedence. `.env.example` is intentionally absent. Without provider credentials, deterministic mode remains runnable. See [LLM_PLANNER.md](docs/LLM_PLANNER.md).

## Safety and reliability
Locked, unverified accounts cannot read order data regardless of category. Suspended accounts cannot perform return/replacement actions. Failure injection is accepted only by the evaluation harness, never `POST /tickets`. Ambiguous cancellation timeout causes a state re-read, not another cancellation. Traces record sanitized tool parameters, status, error type, duration, retry attempt, idempotency key, state transition, retrieval metadata, and final action. They intentionally omit messages, email, full addresses, OTPs, passwords, payment values, and raw tool output.

## Evaluation
The evaluator runs fixture tickets against a fresh store and records C1–C7: understanding, evidence retrieval attempt/evidence, tools, parameter validity, authorization, action, and actual final state. It also checks successful duplicate writes, extra write tools, and stability including final state across repeats. Results are fixture-conformance evidence, not model quality, security certification, production latency, or proof of production readiness.

## Audit result
The preserved deterministic reference is 114/114 passed, 38/38 stable, with 19 tests at commit `2c36765`; see `reports/deterministic_baseline_2026-10-04.json`. The current deterministic strict baseline remains 114/114 in the preserved comparison. `python -m support_agent compare --repeats 3` writes `reports/planner_comparison.json`. An earlier OpenAI-compatible smoke was rate limited; later OpenRouter T001 and full-evaluation results are recorded below. Fixture scores are not model-quality measures or production readiness claims.

## Latest LLM planner verification (2026-10-05)
The live provider is OpenRouter with `nvidia/nemotron-3-super-120b-a12b:free`. T001 passed once with a real structured response, local and semantic validation, PolicyEngine approval, ordered `get_order_details` → `initiate_return`, expected state, and no fallback (7,388 ms; 3,028 input and 616 output tokens; cost unavailable). The subsequent full 38-ticket LLM run was rate limited on all 38 calls (HTTP 429); it produced 0 LLM successes and 38 deterministic fallbacks. A three-repeat LLM stability command was also run: all 114 calls were rate limited and fell back, so 38/38 stable outcomes represent fallback only. See `reports/llm_eval_2026-10-05.json`, `reports/llm_stability_2026-10-05.json`, and `docs/PLANNER_COMPARISON.md`.
