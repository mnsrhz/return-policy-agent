# Failure Analysis Template

Use this template after the baseline LangSmith run and again after the post-improvement run.

## Run Metadata

| Field | Value |
| --- | --- |
| Experiment name | |
| Dataset version | |
| Agent snapshot or commit | |
| Date | |
| Evaluator version | |
| Total cases | |
| Overall pass/fail | |

## Metric Summary

| Metric | Score | Pass Bar | Pass |
| --- | ---: | ---: | --- |
| decision_accuracy | | `>= 0.90` | |
| reason_code_accuracy | | `>= 0.85` | |
| missing_info_f1 | | `>= 0.85` | |
| escalation_accuracy | | `>= 0.95` | |
| citation_coverage | | `= 1.00` | |
| faithfulness_llm_judge | | `>= 0.90` | |
| p95_latency | | `< 8 seconds` | |
| cost_per_run | | `< $0.05` | |

## Failed Case Inventory

| Case ID | Group | Scenario | Expected | Actual | Primary Failure Type | Severity | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | |

## Failure Types

Use one primary type per failed case:

- `retrieval_miss`
- `decision_miss`
- `reason_code_miss`
- `missing_info_miss`
- `escalation_miss`
- `citation_miss`
- `faithfulness_miss`
- `latency_issue`
- `cost_issue`
- `dataset_label_issue`

## Severity Rubric

| Severity | Meaning |
| --- | --- |
| High | Customer could receive incorrect eligibility, unsafe legal/fraud guidance, or missed escalation. |
| Medium | Correct broad outcome but wrong reason code, incomplete missing-info handling, or weak citation. |
| Low | Minor wording, harmless extra information, or non-blocking trace metadata issue. |

## Root Cause Notes

For each high or medium severity failure, capture:

```text
Case ID:
Observed output:
Expected output:
Retrieved policy sections:
Was correct evidence retrieved? yes/no
Did guardrails fire correctly? yes/no
Did validator correct or block output? yes/no
Root cause:
Targeted fix:
Regression test needed:
```

## Improvement Candidates

| Candidate | Failure Type Addressed | Expected Benefit | Risk | Owner |
| --- | --- | --- | --- | --- |
| | | | | |

## Selected Improvements

Choose 3-4 improvements for the post-baseline iteration.

| Improvement | Linked Cases | Files Likely Affected | Success Criteria |
| --- | --- | --- | --- |
| | | | |

## Post-Improvement Delta

| Metric | Baseline | Post-Improvement | Delta | Notes |
| --- | ---: | ---: | ---: | --- |
| decision_accuracy | | | | |
| reason_code_accuracy | | | | |
| missing_info_f1 | | | | |
| escalation_accuracy | | | | |
| citation_coverage | | | | |
| faithfulness_llm_judge | | | | |
| p95_latency | | | | |
| cost_per_run | | | | |

## Final Assessment

Answer these questions in the final report:

1. Did the agent meet every pass bar?
2. Which scenarios remain risky?
3. Which failures are caused by policy ambiguity rather than implementation?
4. Which improvements had the largest measured impact?
5. What should be evaluated next?
