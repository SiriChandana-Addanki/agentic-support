# Agentic Support / Ticket Resolution System

A deterministic, policy-enforced backend for the supplied 38-ticket e-commerce support dataset. It separates untrusted customer text from application-enforced authorization; it is intentionally not an unrestricted LLM or tool runner.

## Quick start

```bash
python -m unittest discover -s tests -v
python -m support_agent serve
# separate shell
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/tickets -H 'content-type: application/json' -d '{"ticket_id":"T001","customer_id":"C001","message":"return my headphones"}'
python -m support_agent evaluate --ticket T001
python -m support_agent evaluate --repeats 3 # full dataset, explicit only
```

No third-party dependencies are required. Copy `.env.example` if host, port, or log directory need changing. No secret is required by this local baseline.

## Architecture and behavior

`support_agent/` contains `data` (CSV/JSON repository with ownership checks), `retrieval` (replaceable deterministic policy section retrieval), `orchestrator` (intent routing and bounded recovery), `tools` (allowlisted reads/writes), `failures`, `schemas`, `evaluation`, and a standard-library HTTP `api`.

`POST /tickets` submits a dataset ticket or validated ticket payload; `GET /resolutions/{ticket_id}` reads its validated structured result; `GET /observability/{ticket_id}` reads a redacted operational trace; `POST /evaluations` accepts `ticket_ids` and `repeats`; `GET /health` checks liveness. Results contain ticket ID, intent, concise reasoning summary, evidence, calls, action, status, escalation fields, and final response—never hidden reasoning.

Policy checks are in tools/application code: ownership, locked and suspended account gates, lifecycle, return window, returnability, refund/replacement limits, COD restrictions, delivery attempts, evidence, and escalation requirements. There is no direct refund tool: return/cancellation only starts the downstream refund process, and customer wording states QC/payment timing. `data_note` is stripped from all customer-facing order data.

Tickets, attachments, retrieved policy text, and tool output are treated as untrusted data. Injection phrases do not alter planning or permissions (T030). The agent has no shell, filesystem, SQL, HTTP, or external-service tools.

## Reliability, evaluation, and tests

Failure injection is deterministic and evaluation-only: 503, malformed response, empty retrieval, invalid planner-output scenario compatibility, repeated write failure, and post-write timeout. Read failures get one bounded retry; three write failures escalate. A state-changing timeout re-reads state and never repeats an uncertain cancellation. Each evaluation uses fresh data state and records expected/actual action/tools, escalation, errors, retries, fallback, latency, and cost (not available locally).

Actual measured results: on 2026-10-03, `python -m support_agent evaluate --repeats 3` ran all 38 tickets three times (114 isolated runs) and recorded 114/114 passing evaluator rows (100.0%) with a 0.05 ms p50 local process latency. This is a deterministic baseline harness result, not a production/LLM benchmark; cost is unavailable locally. See `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, and `docs/BUILD_LOG.md`.

## Limitations

The supplied attachment names are metadata only; no image files are invented or inspected. Address serviceability is syntactic in this offline baseline, not carrier-backed. The planning layer is deterministic, not a production LLM integration; an adapter can replace it while tools remain the authorization boundary. Full evaluation output is not committed because it is generated runtime data.
