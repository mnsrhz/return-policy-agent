# Metrics And Evaluators

## Metric Summary

The eval suite should combine deterministic evaluators with one LLM-as-judge evaluator.

| Metric | Type | Source |
| --- | --- | --- |
| `decision_accuracy` | Deterministic | Compares predicted decision to expected decision. |
| `reason_code_accuracy` | Deterministic | Compares predicted reason code to expected reason code. |
| `missing_info_f1` | Deterministic | Set-based F1 over missing information fields. |
| `escalation_accuracy` | Deterministic | Compares predicted escalation flag to expected escalation flag. |
| `citation_coverage` | Deterministic | Verifies at least one valid citation and required policy IDs. |
| `faithfulness_llm_judge` | LLM judge | Scores whether final answer is grounded in policy evidence and structured decision. |
| `p95_latency` | Runtime | 95th percentile end-to-end latency. |
| `cost_per_run` | Runtime | Estimated average model cost per agent run. |

## Pass Bars

| Metric | Pass Bar |
| --- | ---: |
| `decision_accuracy` | `>= 0.90` |
| `reason_code_accuracy` | `>= 0.85` |
| `missing_info_f1` | `>= 0.85` |
| `escalation_accuracy` | `>= 0.95` |
| `citation_coverage` | `= 1.00` |
| `faithfulness_llm_judge` | `>= 0.90` |
| `p95_latency` | `< 8 seconds` |
| `cost_per_run` | `< $0.05` |

## Deterministic Evaluators

### `decision_accuracy`

Inputs:

- Expected: `expected.decision`.
- Actual: `actual.decision`.

Score:

```text
1.0 if exact match else 0.0
```

### `reason_code_accuracy`

Inputs:

- Expected: `expected.reason_code`.
- Actual: `actual.reason_code`.

Score:

```text
1.0 if exact match else 0.0
```

### `missing_info_f1`

Inputs:

- Expected: `expected.missing_info`.
- Actual: `actual.missing_info`.

Normalize values by lowercasing and stripping whitespace. Treat both empty lists as `1.0`.

Score:

```text
precision = true_positive / predicted_count
recall = true_positive / expected_count
f1 = 2 * precision * recall / (precision + recall)
```

### `escalation_accuracy`

Inputs:

- Expected: `expected.escalate`.
- Actual: `actual.escalate`.

Score:

```text
1.0 if exact boolean match else 0.0
```

### `citation_coverage`

Inputs:

- Expected: `expected.policy_ids`.
- Actual: `actual.citations` and `actual.policy_sections_used`.
- Retrieved chunks from trace.

Score `1.0` only when all are true:

- At least one citation is present.
- Every citation maps to a retrieved policy chunk.
- Every expected policy ID appears in `actual.policy_sections_used` or `actual.citations`.
- The final answer includes citations.

Otherwise score `0.0`.

## LLM Judge Evaluator

### `faithfulness_llm_judge`

Purpose:

Determine whether the customer-facing answer is faithful to:

1. Retrieved policy chunks.
2. Validated structured decision.
3. Citation list.

The judge should not score tone or helpfulness unless the answer becomes misleading. It should score whether the answer invents policy, promises refund approval, ignores inspection requirements, overrides final sale, skips escalation, or provides legal advice.

Suggested rubric:

| Score | Meaning |
| ---: | --- |
| `1.0` | Fully grounded, no unsupported claims, cites policy. |
| `0.5` | Mostly grounded but has minor unsupported wording or unclear citation tie. |
| `0.0` | Materially unsupported, contradicts policy, or promises an unsafe outcome. |

LLM judge prompt inputs:

- Customer message.
- Order context.
- Retrieved policy chunks.
- Validated structured decision.
- Final answer.
- Citations.

Judge output:

```json
{
  "score": 1.0,
  "reasoning": "The answer follows the final sale policy and cites the final sale section.",
  "failure_type": null
}
```

## Runtime Metrics

### `p95_latency`

Measure end-to-end agent runtime from request entry to final structured output.

Also record per-step latency:

- Intent extraction.
- Safety pre-check.
- Retrieval.
- Structured decision.
- Validator.
- Final answer generation.
- Citation/schema validation.

### `cost_per_run`

Estimate cost using LangSmith token metadata when available.

Include costs for exactly three intended LLM calls:

1. Intent and fact extraction.
2. Structured policy decision.
3. Final answer generation.

Deterministic retrieval, guardrails, validation, and local scoring should not add model cost.

## Aggregation

For the final report:

- Use mean score for accuracy and judge metrics.
- Use p95 for latency.
- Use mean and max for cost.
- Break down metrics by `case_group` and `scenario_type`.
- Report pass/fail against each pass bar.
