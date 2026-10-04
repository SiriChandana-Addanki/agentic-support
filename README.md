# Agentic Support / Ticket Resolution System

A **development-only deterministic support workflow baseline** for the supplied CSV/JSON dataset. It is not LLM-powered and is not production authenticated. It demonstrates a typed planner → policy → tool boundary: untrusted ticket text can propose no executable instruction; only a validated action plan and independently authorized tools may change state.

## Run
```bash
python -m unittest discover -s tests -v
python -m support_agent serve
python -m support_agent evaluate --repeats 3
```
`POST /tickets` processes the JSON supplied by the caller (it never substitutes a fixture by ID). Required JSON fields are `ticket_id`, `customer_id`, `category`, and `message`; optional fields are `order_id`, `attachments`, and `verified`. `POST /evaluations` is the separate fixture-only endpoint. Both are unauthenticated development endpoints; do not expose resolutions or traces publicly.

## Architecture
The deterministic planner produces a typed `ActionPlan`; it cannot execute tools. `PolicyEngine` validates context, account state, order state, policy evidence, and plan shape. `Tools` independently revalidate ownership, lifecycle, account status, idempotency, and action-specific rules. The CSV `Store` models action outcomes in memory. `Retriever` performs deterministic lexical ranking over `data/business_rules.md` and returns typed evidence with document/section/chunk/version/rank/score/query metadata. It is replaceable, but is not production RAG.

No direct refund action exists. Returns only initiate downstream QC/refund handling. Attachment filenames are metadata only; no image is fabricated or inspected. Development principal identity is the supplied customer ID and is **not production authentication**.

## Safety and reliability
Locked, unverified accounts cannot read order data regardless of category. Suspended accounts cannot perform return/replacement actions. Failure injection is accepted only by the evaluation harness, never `POST /tickets`. Ambiguous cancellation timeout causes a state re-read, not another cancellation. Traces record sanitized tool parameters, status, error type, duration, retry attempt, idempotency key, state transition, retrieval metadata, and final action. They intentionally omit messages, email, full addresses, OTPs, passwords, payment values, and raw tool output.

## Evaluation
The evaluator runs fixture tickets against a fresh store and records C1–C7: understanding, evidence, tools, parameter validity, authorization, action, and actual final state. It also checks write duplication/extra tools and repeat stability. Results are fixture-conformance evidence, not model quality, security certification, production latency, or proof that all policy requirements are complete. The prior 114/114 score is superseded by this stricter methodology; run the command above for the current result.
