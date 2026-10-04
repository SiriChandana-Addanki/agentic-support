# Build log

## 2026-10-03 — baseline implementation

Implemented a dependency-free modular support backend, policy retrieval, allowlisted business tools, deterministic fault injection, structured HTTP API, evaluation harness, and behavior-focused unit/integration tests. The purpose was to make every automated action traceable and application-authorized rather than prompt-authorized. Important paths: `support_agent/`, `tests/`, `.env.example`, and this documentation set. No dependencies or secrets were added. `python -m unittest discover -s tests -v` passed 7 tests. The explicit full protocol command `python -m support_agent evaluate --repeats 3` completed 114 isolated runs with 114 pass rows (100%) and 0.05 ms local p50. Health and T030 API checks also passed. Limitations: in-memory state, metadata-only attachments, and offline pincode validation.
## 2026-10-04 — architecture hardening
Separated deterministic planning, policy approval, typed tool invocation, and execution; added tool-level authorization/state checks, API request validation, fixture-only injection, typed retrieval evidence, richer traces, state-aware evaluation, and hardening tests. No external services or persistent storage added. Full evaluation results are reported from the executed command rather than assumed from the obsolete 114/114 harness.

Verification: `python -m unittest discover -s tests -v` passed 14 tests. The stricter full three-run fixture evaluation completed 114 rows with 54 passes (47.37%), 38/38 stable tickets, and 0.62 ms local p50. This lower result is reported intentionally: it exposes unsupported fixture/tool-contract mismatches rather than treating label-only agreement as correctness.

## 2026-10-04 — strict evaluation audit
Added machine-readable `reports/strict_failure_matrix.json` and human-readable `docs/EVALUATION_FAILURE_MATRIX.md`. The full three-repeat audit measured 57/114 passes, 38 stable tickets, and classified the 57 observed failures: 48 legitimate unimplemented behavior, 3 planner, 3 tool, and 3 evaluator/final-state contract categories. This report is intentionally an audit artifact, not a benchmark claim.
