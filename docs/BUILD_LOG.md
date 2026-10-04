# Build log

## 2026-10-03 — baseline implementation

Implemented a dependency-free modular support backend, policy retrieval, allowlisted business tools, deterministic fault injection, structured HTTP API, evaluation harness, and behavior-focused unit/integration tests. The purpose was to make every automated action traceable and application-authorized rather than prompt-authorized. Important paths: `support_agent/`, `tests/`, `.env.example`, and this documentation set. No dependencies or secrets were added. `python -m unittest discover -s tests -v` passed 7 tests. The explicit full protocol command `python -m support_agent evaluate --repeats 3` completed 114 isolated runs with 114 pass rows (100%) and 0.05 ms local p50. Health and T030 API checks also passed. Limitations: in-memory state, metadata-only attachments, and offline pincode validation.
