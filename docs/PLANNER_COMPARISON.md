# Planner comparison

Machine-readable report: `reports/planner_comparison.json`, generated with `python -m support_agent compare --repeats 3`.

| Planner | Evaluation status | Tickets | Passed rows | Stable tickets | C1-C7 | P50 / P95 ms | Tokens | Estimated cost |
|---|---|---:|---:|---:|---|---|---|---|
| Deterministic | Executed | 38 | 114/114 | 38/38 | 114/114 each | 0.43 / 0.80 | Not applicable | Unknown |
| LLM (single full run) | Executed; all provider calls rate-limited | 38 | 0 LLM-success rows | 38/38 repeat-stable outcomes, all fallback | 0 LLM successes / 38 fallback | 248.59 ms p50 total | Unavailable | Unknown |

The deterministic result is fixture conformance and matches the preserved 2026-10-04 reference (114/114; 38/38 stable; 19 tests at the reference commit). In the current comparison run, there were no safety failures, three invalid planner outputs and three retries from the deterministic invalid-output injection case, no unnecessary escalations, and no missed fixture escalations. There were 39 policy rejections and 261 executed tool calls over the 114 rows. Token use and cost are not applicable to the deterministic planner.

The single T001 live smoke succeeded with OpenRouter model `nvidia/nemotron-3-super-120b-a12b:free`: a real schema-valid plan proposed `get_order_details` then `initiate_return`, PolicyEngine approved it, both tools executed, and the expected return state was reached without fallback. Latency was 7,387 ms with 3,028 input and 616 output tokens; cost was unavailable.

The subsequent full 38-ticket run received HTTP 429 (`ProviderRateLimit`) on all 38 provider calls. All 38 requests were unavailable/unevaluable; 0/38 evaluable LLM responses is not an accuracy score. Operational fixture behavior passed on all 38 deterministic fallbacks, which are not LLM successes or accuracy. Tokens and cost were unavailable. The requested three-repeat run also received HTTP 429 for all 114 calls; all rows fell back, with 38/38 stable fallback outcomes. Neither run demonstrates model stability. See `reports/llm_eval_2026-10-05.json` and `reports/llm_stability_2026-10-05.json`. This is not evidence of LLM quality or a benchmark against other models or systems.
