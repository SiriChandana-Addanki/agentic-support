# OpenRouter LLM readiness and deterministic comparison

The frozen deterministic reference at `2c36765` passed 114/114 strict rows (100%), with 38/38 tickets stable and 0.36 ms p50 latency. It is recorded in `reports/deterministic_baseline_2026-10-04.json`.

## Live smoke attempt

On 2026-10-05, the configured OpenRouter provider smoke command was issued once for one existing fixture:

```powershell
python -m support_agent evaluate --planner-type llm --ticket T001 --repeats 1
```

The command returned no captured stdout, exit status, or provider trace from the execution tool. Therefore there is no evidence that OpenRouter returned a model response, and no provider error category can be assigned. The smoke is unverified and is not counted as a success. No second provider request was made. The full suite was not run. The configured model is `openrouter/free`; the API key and its value are not recorded here.

## Comparison

| Metric | Deterministic reference | OpenRouter LLM |
|---|---:|---:|
| Task success | 114/114 (100%) | Not measured |
| Safety success | 114/114 | Not measured |
| Policy compliance | Not separately captured in frozen baseline | Not measured |
| Tool/escalation/final-state correctness | 114/114 strict rows | Not measured |
| Stability | 38/38 | Not measured |
| Latency | 0.36 ms p50 | Not measured |
| Tokens / cost | Not applicable | Not available |
| Retries / fallbacks | Not comparable | Not measured |
| Malformed outputs / provider failures | Not applicable | Not measured |

The full 38-ticket LLM suite was not started because the smoke result could not be verified. No differences or model-quality metrics are claimed. Intent inference, order references, lifecycle state, eligibility, restrictions, evidence, thresholds, and escalation behavior remain unassessed against OpenRouter. Existing mock-provider tests still cover prompt injection and local policy/tool boundaries.

See `reports/llm_vs_deterministic_2026-10-04.json` for the machine-readable record. The key is configured only in local `.env`, which is gitignored; `.env.example` remains deleted per the user's instruction. Required variable names are `LLM_PROVIDER`, `OPENROUTER_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_TEMPERATURE`, `LLM_TIMEOUT_SECONDS`, and `LLM_MAX_OUTPUT_TOKENS`.
