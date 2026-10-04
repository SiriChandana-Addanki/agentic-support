# Strict evaluation failure matrix

Current machine-readable result: `reports/strict_failure_matrix.json`.

The current strict three-repeat run has 114 rows, 114 passes, a 100.0% fixture pass rate, and 38/38 stable tickets. The earlier 57/114 result and its provisional row labels remain preserved in `reports/strict_failure_matrix_baseline_2026-10-04.json`.

The initial taxonomy was heuristic. Three `evaluator_bug` rows were all T031 repeated runs, where an action/state heuristic mislabeled the unavailable-order-service failure; three `tool_bug` rows were T034 repeated runs, where an injected malformed read was mistaken for a parameter error despite successful recovery. These were evaluator defects, not three distinct runtime bugs. The original 3 planner rows were T016 repeated runs, a planning gap for exception/warranty handling. The 48 legitimate behavior rows represented 16 distinct tickets, each repeated three times.

The evaluator now checks generic state transitions rather than ticket IDs, recognizes an attempted empty knowledge-base retrieval as a retrieval attempt, distinguishes malformed injected responses from parameter errors, counts only successful writes for duplicate-write checks, and includes final state in repeat stability. It still scores semantic action, actual data state, expected tools, authorization errors, forbidden writes, and safety independently; changing a fixture label alone cannot pass a state assertion.

No findings in the current run. Remaining system limits are documented in `docs/BEHAVIOR_GAP_PLAN.md` and `docs/ARCHITECTURE.md`.
