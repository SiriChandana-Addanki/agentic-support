# Live LLM readiness and deterministic comparison

The frozen deterministic reference at `2c36765` passed 114/114 strict rows (100%), with 38/38 tickets stable and 0.36 ms p50 latency. It is recorded in `reports/deterministic_baseline_2026-10-04.json`.

## Live smoke attempt

On 2026-10-05, the configured OpenAI-compatible provider was invoked for one existing fixture:

```powershell
python -m support_agent evaluate --planner-type llm --ticket T001 --repeats 1
```

The endpoint returned HTTP 429, surfaced as `ProviderRateLimit`. No model response or structured `ActionPlan` was returned, so schema validation and model-proposal policy review could not be demonstrated. The orchestrator fell back to the deterministic planner; that fallback produced a passing fixture row. The fallback pass is not an LLM result. The smoke used the existing `gpt-4o-mini` configuration. The API key and its value are not recorded here.

## Comparison

| Metric | Deterministic reference | OpenAI LLM |
|---|---:|---:|
| Task success | 114/114 (100%) | Not measured |
| Safety success | 114/114 | Not measured |
| Policy compliance | Not separately captured in frozen baseline | Not measured |
| Tool/escalation/final-state correctness | 114/114 strict rows | Not measured |
| Stability | 38/38 | Not measured |
| Latency | 0.36 ms p50 | Smoke request 2040.85 ms; not a model latency because it returned HTTP 429 |
| Tokens / cost | Not applicable | Not available |
| Retries / fallbacks | Not comparable | 0 planner retries; 1 deterministic fallback in smoke |
| Malformed outputs / provider failures | Not applicable | 0 malformed responses observed; 1 provider rate-limit failure |

The full 38-ticket LLM suite was not started because the smoke test did not produce a valid model plan. No differences or model-quality metrics are claimed. The returned fixture pass demonstrates safe fallback behavior only. Whether the LLM improves intent inference, reduces dependence on category hints, or is production-worthy remains unassessed. The rate-limit response does not reveal whether the cause was request throttling or account quota; the provider error body is intentionally not logged.

See `reports/llm_vs_deterministic_2026-10-04.json` for the machine-readable record. The API key is configured only in local `.env`, which is gitignored; `.env.example` remains deleted per the user's instruction.
