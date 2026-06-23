# Baseline Eval Report

## Scope

This report analyzes the baseline evaluation artifacts for the Northstar Commerce Return Policy Agent. No agent behavior was changed as part of this analysis.

Inputs reviewed:

- `eval_runs/local_baseline_predictions.jsonl`
- `eval_runs/local_baseline_summary.json`
- `eval_runs/langsmith_baseline_summary.json` was not available
- `eval_runs/langsmith_baseline_failures.jsonl` was not available

## Executive Summary

The local baseline ran 40 golden cases. Schema validity and citation coverage are strong, both at 100%. The largest gaps are decision accuracy, reason-code accuracy, missing-info F1, escalation accuracy, and policy-section recall. The agent is fast locally, with average latency of 0.0012 seconds.

The main failure pattern is not missing citations. It is rule coverage and priority: the current deterministic baseline handles many straightforward standard returns, but it overuses generic ask-for-info behavior for edge cases, misses some support-review scenarios, and often cites valid policy sections while omitting one or more expected sections for multi-policy questions.

## Baseline Metrics

| Metric | Score | Week 4 Pass Bar | Status |
| --- | ---: | ---: | --- |
| `decision_accuracy` | 62.50% | >= 90% | Fail |
| `reason_code_accuracy` | 65.00% | >= 85% | Fail |
| `missing_info_f1` | 66.25% | >= 85% | Fail |
| `escalation_accuracy` | 87.50% | >= 95% | Fail |
| `citation_coverage` | 100.00% | = 100% | Pass |
| `policy_section_recall` | 60.00% | not specified | Diagnostic |
| `schema_validity` | 100.00% | not specified | Diagnostic |
| `average_latency_seconds` | 0.0012s | p95 < 8s | Diagnostic; p95 not measured locally |

LangSmith cost and LLM-judge faithfulness were not available because no LangSmith baseline artifacts were present.

## Scenario Type Breakdown

| Scenario Type | Cases | Decision Failures | Reason Failures | Missing-Info Failures | Escalation Failures | Citation Failures | Policy Recall Failures | Schema Failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `happy_path` | 20 | 3 | 2 | 2 | 2 | 0 | 8 | 0 |
| `edge_case` | 12 | 9 | 9 | 8 | 2 | 0 | 8 | 0 |
| `known_failure` | 6 | 3 | 3 | 4 | 1 | 0 | 5 | 0 |
| `adversarial` | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |

Edge cases are the weakest group: 9 of 12 have decision failures, 9 have reason-code failures, and 8 have missing-info failures. Happy paths are mostly healthy but still show policy-recall gaps in multi-policy questions.

## Failure Clusters

### Incorrect eligibility decision

- Count: `15`
- Affected case IDs: `RET-006, RET-009, RET-014, RET-021, RET-023, RET-024, RET-026, RET-027, RET-029, RET-030, RET-031, RET-032, RET-034, RET-037, RET-038`
- Example customer message: If I return an eligible dress because I changed my mind, will Northstar refund return shipping?
- Expected output: `{"decision": "not_eligible", "escalate": false, "missing_info": [], "policy_sections": ["POLICY:RETURN_SHIPPING_CUSTOMER_REASONS"], "reason_code": "shipping_fee"}`
- Predicted output: `{"citations": ["04_refunds_and_shipping_fees.md [POLICY:RETURN_SHIPPING_CUSTOMER_REASONS]", "04_refunds_and_shipping_fees.md [POLICY:RETURN_SHIPPING_NORTHSTAR_REASONS]"], "customer_answer": "I need the return reason before I can determine whether return shipping may be refunded.", "decision": "ask_for_info", "escalate": false, "missing_info": ["return_reason"], "policy_sections_used": ["POLICY:RETURN_SHIPPING_CUSTOMER_REASONS", "POLICY:RETURN_SHIPPING_NORTHSTAR_REASONS"], "reason_code": "shipping_fee"}`
- Likely root cause: Decision logic overuses generic ask-for-info paths for outside-window, used-condition, refund-method, unsupported-channel, and damaged/wrong-item variants instead of applying conclusive policy outcomes or support-review routing.
- Recommended improvement: Add targeted deterministic decision/validator rules for outside-window, used-condition, refund-method, digital/personalized restrictions, unsupported channels, and damaged/wrong/missing review paths.
- Estimated impact: High: directly improves decision_accuracy and reduces unsafe or unhelpful outcomes across many edge/known-failure cases.

### Incorrect reason code

- Count: `14`
- Affected case IDs: `RET-009, RET-014, RET-021, RET-023, RET-024, RET-025, RET-026, RET-027, RET-030, RET-031, RET-032, RET-036, RET-037, RET-038`
- Example customer message: I ordered the wrong size shirt. It is unworn. Can I return it?
- Expected output: `{"decision": "eligible_return", "escalate": false, "missing_info": [], "policy_sections": ["POLICY:STANDARD_RETURN_REASON", "POLICY:STANDARD_RETURN_WINDOW", "POLICY:RETURN_SHIPPING_CUSTOMER_REASONS"], "reason_code": "standard_30_day"}`
- Predicted output: `{"citations": ["03_damaged_wrong_missing_items.md [POLICY:DAMAGE_WRONG_MISSING_REVIEW]", "03_damaged_wrong_missing_items.md [POLICY:DAMAGE_WRONG_MISSING_REQUIRED_INFO]"], "customer_answer": "This issue needs support review. Northstar Commerce requires order details and issue evidence before approving a refund, replacement, or shipping-fee refund.", "decision": "escalate", "escalate": true, "missing_info": [], "policy_sections_used": ["POLICY:DAMAGE_WRONG_MISSING_REVIEW", "POLICY:DAMAGE_WRONG_MISSING_REQUIRED_INFO"], "reason_code": "wrong_item"}`
- Likely root cause: Reason-code selection is too coarse: missing delivery date maps to missing_order_number, safety escalations collapse to exception_request, outside-window and used-condition cases are represented as missing info, and issue-specific refund/shipping questions are not distinguished.
- Recommended improvement: Normalize reason-code priority and map each branch to the golden taxonomy, including outside_return_window, final_sale, damaged_item, wrong_item, no_proof_of_purchase, shipping_fee, gift_return, exception_request, and unclear.
- Estimated impact: High: likely largest reason_code_accuracy gain because most decision misses also carry wrong or coarse reason codes.

### Missed missing-information request

- Count: `14`
- Affected case IDs: `RET-006, RET-014, RET-021, RET-023, RET-024, RET-025, RET-026, RET-029, RET-030, RET-032, RET-034, RET-036, RET-037, RET-038`
- Example customer message: If I return an eligible dress because I changed my mind, will Northstar refund return shipping?
- Expected output: `{"decision": "not_eligible", "escalate": false, "missing_info": [], "policy_sections": ["POLICY:RETURN_SHIPPING_CUSTOMER_REASONS"], "reason_code": "shipping_fee"}`
- Predicted output: `{"citations": ["04_refunds_and_shipping_fees.md [POLICY:RETURN_SHIPPING_CUSTOMER_REASONS]", "04_refunds_and_shipping_fees.md [POLICY:RETURN_SHIPPING_NORTHSTAR_REASONS]"], "customer_answer": "I need the return reason before I can determine whether return shipping may be refunded.", "decision": "ask_for_info", "escalate": false, "missing_info": ["return_reason"], "policy_sections_used": ["POLICY:RETURN_SHIPPING_CUSTOMER_REASONS", "POLICY:RETURN_SHIPPING_NORTHSTAR_REASONS"], "reason_code": "shipping_fee"}`
- Likely root cause: Missing-info names from the agent do not align with the golden schema, and some branches escalate immediately even when the dataset expects required facts to be requested first.
- Recommended improvement: Introduce a canonical missing-info mapper so delivery timing, proof, order number, gift receipt, item-level facts, and issue evidence use stable field names.
- Estimated impact: Medium: improves missing_info_f1 and customer follow-up quality, especially for gift/no-proof/damaged-info cases.

### Missed escalation

- Count: `5`
- Affected case IDs: `RET-009, RET-014, RET-026, RET-027, RET-034`
- Example customer message: I ordered the wrong size shirt. It is unworn. Can I return it?
- Expected output: `{"decision": "eligible_return", "escalate": false, "missing_info": [], "policy_sections": ["POLICY:STANDARD_RETURN_REASON", "POLICY:STANDARD_RETURN_WINDOW", "POLICY:RETURN_SHIPPING_CUSTOMER_REASONS"], "reason_code": "standard_30_day"}`
- Predicted output: `{"citations": ["03_damaged_wrong_missing_items.md [POLICY:DAMAGE_WRONG_MISSING_REVIEW]", "03_damaged_wrong_missing_items.md [POLICY:DAMAGE_WRONG_MISSING_REQUIRED_INFO]"], "customer_answer": "This issue needs support review. Northstar Commerce requires order details and issue evidence before approving a refund, replacement, or shipping-fee refund.", "decision": "escalate", "escalate": true, "missing_info": [], "policy_sections_used": ["POLICY:DAMAGE_WRONG_MISSING_REVIEW", "POLICY:DAMAGE_WRONG_MISSING_REQUIRED_INFO"], "reason_code": "wrong_item"}`
- Likely root cause: Escalation pre-checks do not catch some policy-required review cases, especially high-value missing proof, explicit final-sale exception phrasing after final-sale detection, and customer-caused/unclear damage responsibility.
- Recommended improvement: Strengthen deterministic guardrails for high-value missing proof, explicit exception requests, customer-caused or unclear damage responsibility, and adversarial final-sale overrides.
- Estimated impact: High: improves escalation_accuracy and safety for high-risk cases.

### Missing or invalid citation

- Count: `0`
- Affected case IDs: `none`
- Example customer message: none observed
- Expected output: none
- Predicted output: none
- Likely root cause: No citation coverage failures were observed locally. Citation validation is currently strong for retrieved citation presence.
- Recommended improvement: Keep current citation validator; add regression tests to preserve 100% citation coverage as behavior changes are made.
- Estimated impact: Low currently: already at 100% citation_coverage locally.

### Retrieval missed relevant policy section

- Count: `22`
- Affected case IDs: `RET-004, RET-007, RET-009, RET-010, RET-014, RET-015, RET-017, RET-019, RET-023, RET-024, RET-026, RET-027, RET-028, RET-030, RET-031, RET-032, RET-033, RET-034, RET-035, RET-036, RET-038, RET-040`
- Example customer message: How long does a refund take after you inspect my returned item?
- Expected output: `{"decision": "eligible_return", "escalate": false, "missing_info": [], "policy_sections": ["POLICY:REFUND_TIMING_AFTER_INSPECTION", "POLICY:INSPECTION_REQUIRED_BEFORE_REFUND"], "reason_code": "standard_30_day"}`
- Predicted output: `{"citations": ["01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]", "01_standard_returns.md [POLICY:STANDARD_ITEM_CONDITION]", "01_standard_returns.md [POLICY:PROOF_OF_PURCHASE_REQUIRED]"], "customer_answer": "This item appears eligible for a standard return because it is within 30 days of delivery, in eligible condition, and has proof of purchase.", "decision": "eligible_return", "escalate": false, "missing_info": [], "policy_sections_used": ["POLICY:STANDARD_RETURN_WINDOW", "POLICY:STANDARD_ITEM_CONDITION", "POLICY:PROOF_OF_PURCHASE_REQUIRED"], "reason_code": "standard_30_day"}`
- Likely root cause: Retrieval returns valid chunks, but top-k evidence often omits one or more expected policy sections for multi-policy cases such as exchanges, gifts, shipping fees, and restricted items.
- Recommended improvement: Tune retrieval queries with expected intent terms and add policy-section boost/expansion for multi-policy scenarios so expected support sections appear in retrieved evidence.
- Estimated impact: Medium: improves policy_section_recall and provides stronger evidence for LangSmith faithfulness judging.

### Final answer hallucinated or overpromised

- Count: `0`
- Affected case IDs: `none`
- Example customer message: none observed
- Expected output: none
- Predicted output: none
- Likely root cause: No automated faithfulness artifact is available in the local baseline. This cluster is not measured until LangSmith/LLM judge output exists.
- Recommended improvement: Run LangSmith faithfulness judge after credentials are configured; keep refund-promise and exception-approval bans in the final-answer prompt/tests.
- Estimated impact: Unknown until judged; likely medium if answer wording is evaluated strictly.

### Schema violation

- Count: `0`
- Affected case IDs: `none`
- Example customer message: none observed
- Expected output: none
- Predicted output: none
- Likely root cause: No schema violations were observed. Required output fields are present in all local predictions.
- Recommended improvement: Keep schema tests and Pydantic model validation unchanged.
- Estimated impact: Low currently: schema_validity is 100%.

### Latency or cost issue

- Count: `0`
- Affected case IDs: `none`
- Example customer message: none observed
- Expected output: none
- Predicted output: none
- Likely root cause: No latency issue was observed. Local deterministic average latency is well below the 8 second pass bar; no cost data is available without LangSmith/model usage.
- Recommended improvement: Track p95 latency and model cost once LangSmith runs are available; no local action needed now.
- Estimated impact: Low currently: local latency is roughly 0.001 seconds and no cost is incurred in deterministic baseline.

## Top 3 Improvement Opportunities

1. Fix deterministic decision and reason-code priority for edge/known-failure cases
   - Addresses: Incorrect eligibility decision, Incorrect reason code, Missed escalation
   - Affected case count estimate: 17
   - Rationale: These failures directly block decision_accuracy, reason_code_accuracy, and escalation_accuracy pass bars and include the highest-risk cases.

2. Canonicalize missing-info field names and branch behavior
   - Addresses: Missed missing-information request
   - Affected case count estimate: 14
   - Rationale: Missing-info F1 is below pass bar and several cases fail because labels and agent fields use different names or the agent answers/escalates before asking required facts.

3. Improve retrieval recall for multi-policy scenarios
   - Addresses: Retrieval missed relevant policy section
   - Affected case count estimate: 22
   - Rationale: Citation coverage is perfect, but policy_section_recall is only 60%; stronger retrieved evidence will help LangSmith faithfulness and policy-grounding evaluations.

## Recommended Next Step

Wait for approval before changing agent behavior. Once approved, start with targeted deterministic rules and validator priorities for the edge and known-failure cases, then re-run the same local eval and compare against this baseline. Keep citation/schema behavior protected with regression tests because those metrics are already passing.
