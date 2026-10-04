# Decisions and dataset interpretations

* The standard-library modular architecture keeps the baseline inspectable and dependency-free while retaining replaceable repository, retrieval, planner, and API boundaries.
* Direct refund execution is deliberately absent. Cancellation and return initiation state that money is released by the defined cancellation/return-QC process; the result never says a refund is completed prematurely.
* Authorization is implemented in application/tool code, not text prompts. The tools validate customer ownership and lifecycle; the orchestrator applies cross-cutting account and escalation policy.
* Retrieval ranks supplied `business_rules.md` sections deterministically. Empty evidence is a fallback/escalation condition, not permission to invent a split-refund policy.
* Failure injection is explicit by evaluation scenario and is not random production behavior. State-changing cancel timeouts write once then require a state read; retries are bounded and repeated failures escalate.
* `data_note` is reviewer-only and removed at the data boundary. Attachment filenames are evidence metadata and the ticket model retains them for a later file-backed attachment service; no synthetic image is claimed.
* T036/T037/T038 are present in `tickets.json` and the evaluation plan’s “real-life” sentence mistakenly lists “T036” for locked accounts even though the locked/no-OTP ticket is T037. T036 is correctly treated as repeated redelivery failure; no dataset file was changed. The plan’s “15 of 38” escalation statement is used as narrative only; per-ticket `requires_human` is the scoring source.
* 2026-10-04: planner, policy, and tools were separated so a future LLM can only propose typed plans. The deterministic planner remains intentionally limited.
* Tool authorization is duplicated at the action boundary; orchestration/policy approval is not trusted as the final security control.
* Evaluation fixtures are isolated from normal ticket submission. The stricter evaluator intentionally may score lower than the previous action-label harness.
* Prompt-injection containment is principally typed-plan/policy/tool isolation; heuristic labeling is not treated as a security boundary.
* 2026-10-04 audit report preserves the supplied fixture data and exports each strict-evaluation failure with observed criteria, tools, state, policy summary, and taxonomy. It does not alter expected fixture fields to improve the score.
