# Architecture

## Components and flow

The HTTP API validates request shape and dispatches to `Orchestrator`. The orchestrator treats ticket fields/text as untrusted, retrieves policy evidence, reads verified customer/order state, selects only allowlisted `Tools`, and produces a validated `Resolution`. `Store` owns an in-memory copy of CSV state per run; `Retriever` ranks business-rule sections deterministically and can be swapped later.

Write tool authorization is defense in depth: tools validate lifecycle and parameters even if planning is wrong. Ownership is checked before reads/writes; locked accounts receive verification without order disclosure; `data_note` never crosses the data boundary. Escalations capture customer/order/category/reason/priority.

Failures are deterministic only through `FailureInjector`. Reads receive one retry. Three consecutive redelivery failures escalate. A cancel timeout is treated as ambiguous: the state is re-read before any possible retry. Empty policy evidence escalates rather than creating policy. Every request emits an in-memory redacted trace with IDs, timestamps, calls, retrieval metadata, retry/error/fallback/escalation, status, and latency.

`evaluation.run` builds fresh stores for every ticket/run, applies only each ticket's declared injection, and records per-run scoring fields. The API returns no chain-of-thought, secrets, OTPs, payment credentials, or unnecessary customer data.
