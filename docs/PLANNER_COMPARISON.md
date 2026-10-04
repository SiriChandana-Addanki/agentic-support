# Planner comparison

Machine-readable report: `reports/planner_comparison.json`, generated with `python -m support_agent compare --repeats 3`.

| Planner | Evaluation status | Tickets | Passed rows | Stable tickets | C1-C7 | P50 / P95 ms | Tokens | Estimated cost |
|---|---|---:|---:|---:|---|---|---|---|
| Deterministic | Executed | 38 | 114/114 | 38/38 | 114/114 each | 0.43 / 0.80 | Not applicable | Unknown |
| LLM | Not executed: `OPENAI_API_KEY` unavailable | — | — | — | — | — | — | Unknown |

The deterministic result is fixture conformance and matches the preserved 2026-10-04 reference (114/114; 38/38 stable; 19 tests at the reference commit). In the current comparison run, there were no safety failures, three invalid planner outputs and three retries from the deterministic invalid-output injection case, no unnecessary escalations, and no missed fixture escalations. There were 39 policy rejections and 261 executed tool calls over the 114 rows. Token use and cost are not applicable to the deterministic planner.

LLM metrics and deterministic-versus-LLM action/tool/state differences are `null`, not zero, because no live LLM run occurred. Mock-provider tests establish local contract, validation, fallback, and security behavior only; they are not represented as LLM evaluation results. Rerun the comparison with an available provider key to collect real model metrics. This report is not a benchmark against other models or systems.
