# Strict evaluation failure matrix

Machine-readable per-row report: `reports/strict_failure_matrix.json`.

The 57 failed rows are classified from observed failed criteria, traces, final state, and policy summary—not expected outcomes supplied to runtime.

| Classification | Rows | Meaning |
|---|---:|---|
| `evaluator_bug` | 3 | Observed evaluator classification; inspect JSON row evidence. |
| `legitimate_unimplemented_behavior` | 48 | Observed evaluator classification; inspect JSON row evidence. |
| `planner_bug` | 3 | Observed evaluator classification; inspect JSON row evidence. |
| `tool_bug` | 3 | Observed evaluator classification; inspect JSON row evidence. |

The report preserves source fixtures. Classifications are provisional audit categories, not a reason to weaken safety checks.
