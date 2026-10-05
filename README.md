# Agentic Support / Ticket Resolution System

A portfolio demonstration of e-commerce ticket investigation and resolution with an explicit safety boundary: the LLM may propose a structured plan, while application policy authorizes actions and tools validate and execute them. The system uses synthetic customer, order, and ticket data. Its API is a development demonstration, not a production-authenticated service.

## Architecture

```text
Customer Ticket → TicketContext → Retrieval → Planner → ActionPlan
                → PolicyEngine → authorized Tools → ToolResult
                → Resolution / Escalation → Observability + Evaluation
```

**LLM proposes. PolicyEngine authorizes. Tools execute.** The deterministic and LLM planners share the typed `ActionPlan` contract. The LLM has no direct access to the store, policy engine, or tools. Proposed plans are schema and semantic validated before policy evaluation; tools independently check critical state and authorization conditions.

## Engineering features

- Deterministic planner, optional structured-output LLM planner, bounded validation retry, and deterministic fallback.
- Lexical retrieval over `data/business_rules.md`, returning concise, titled evidence with source metadata.
- Policy authorization plus allowlisted tools with customer/order ownership, account state, lifecycle, amount, evidence, stock, and idempotency checks.
- Return-window and refund/replacement limits, cancellation and delivery rules, escalation paths, and protected account handling.
- Prompt-injection defenses that treat ticket content and retrieved excerpts as untrusted data.
- Request traces for proposals, decisions, tool calls, fallback reason, and available provider/token metadata.
- Fixture evaluation checks C1–C7, safety, actual final state, tool behavior, and repeat stability.
- Existing JSON HTTP API, CLI, Docker image, and synthetic fixtures.

Retrieval is deterministic lexical ranking, not vector search. Attachment names are metadata; files and images are not inspected. Refunds are not directly issued by an agent tool; return and cancellation flows only initiate the system's downstream refund process.

## Quick start with Docker

Build from the repository root:

```bash
docker build -t agentic-support .
```

Run the API on port 8000:

```bash
docker run --rm -p 8000:8000 agentic-support
```

The image starts the existing API with the deterministic planner by default. Check its health endpoint at `http://localhost:8000/health`. To provide optional LLM configuration from a local `.env`, pass it at runtime:

```bash
docker run --rm --env-file .env -p 8000:8000 agentic-support
```

The `.env` file is not included in the build context or image. For LLM use, set `PLANNER_TYPE=llm`, `LLM_PROVIDER`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_TEMPERATURE`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_OUTPUT_TOKENS`, and the matching `OPENAI_API_KEY` or `OPENROUTER_API_KEY`. Provider credentials are optional for deterministic use. The repository intentionally has no `.env.example`; configure these values locally and never commit credentials.

Run checks using the same image:

```bash
docker run --rm agentic-support python -m unittest discover -s tests -v
docker run --rm agentic-support python -m support_agent evaluate --planner-type deterministic
```

## Local execution

Python 3.10 or newer is required. The application uses the standard library; `requirements.txt` is retained as the dependency manifest and currently has no third-party packages.

```bash
python -m unittest discover -s tests -v
python -m support_agent evaluate --planner-type deterministic
python -m support_agent serve
```

The API defaults to `127.0.0.1:8000` locally. `SUPPORT_HOST` and `SUPPORT_PORT` configure its bind address and port. `POST /tickets` uses the submitted request data; `POST /evaluations` runs the supplied fixtures. The service keeps state in memory and has no authentication, so do not expose it publicly.

## Deterministic benchmark

The reproducible baseline contains 38 scenarios: **38/38 passed and 38/38 stable** in the recorded deterministic run. The evaluator checks expected action and tools, policy and safety conditions, parameters, actual final state, and repeat stability. See [`reports/deterministic_baseline_2026-10-04.json`](reports/deterministic_baseline_2026-10-04.json).

## Live LLM validation and limits

A real OpenRouter-backed planner successfully produced a structured, valid `ActionPlan` for T001. The PolicyEngine authorized `get_order_details` followed by `initiate_return`; both tools executed, the expected return state was reached, and fallback was not used.

The full 38-ticket live LLM benchmark was **unevaluable** because all provider requests received HTTP 429 rate-limit responses. This is an external provider limitation. **Do not interpret 0/38 evaluable responses as either 0% or 100% LLM accuracy.** The deterministic fallback remained available; fallback outcomes are not LLM successes or model accuracy. Repeated fallback stability is not LLM stability. Token usage and cost were unavailable for those rate-limited requests. Details are in [`reports/llm_eval_2026-10-05.json`](reports/llm_eval_2026-10-05.json), [`reports/llm_stability_2026-10-05.json`](reports/llm_stability_2026-10-05.json), and [`docs/PLANNER_COMPARISON.md`](docs/PLANNER_COMPARISON.md).

## API and safety notes

The interchangeable planner contract is `Planner.plan(TicketContext, RetrievedEvidence) -> ActionPlan`. The LLM receives allowlisted planning context and retrieval evidence, never store access or execution capability. `PolicyEngine` authorizes independently; tools revalidate ownership and action-specific rules at execution. Traces omit raw ticket messages, secrets, and raw tool output. The service uses in-memory synthetic data and is intended for local demonstration and evaluation, not production deployment.
