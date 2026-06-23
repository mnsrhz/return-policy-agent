# Improvement Log

## Improvement 1: Edge-Case Decision And Reason Priority

- Failure cluster targeted: Incorrect eligibility decision; Incorrect reason code; Missed escalation.
- Files changed:
  - `src/return_agent/decision_agent.py`
  - `src/return_agent/intent_extractor.py`
  - `src/return_agent/guardrails.py`
  - `tests/test_post_baseline_improvements.py`
- Expected metric impact: Improve `decision_accuracy`, `reason_code_accuracy`, and `escalation_accuracy` on edge and known-failure cases.
- Risk of regression: Medium. Rule priority changes can accidentally override existing standard-return, gift, exchange, or damaged-item behavior. Existing unit tests and new regression tests cover the affected branches.

## Improvement 2: Canonical Missing-Info Handling

- Failure cluster targeted: Missed missing-information request.
- Files changed:
  - `src/return_agent/decision_agent.py`
  - `src/return_agent/evaluators.py`
  - `tests/test_post_baseline_improvements.py`
- Expected metric impact: Improve `missing_info_f1` by returning required fields for no-proof, no-order-number, gift-return, mixed-item, high-value, and damaged-item evidence cases. The evaluator now treats `delivery_date` as equivalent to the dataset's `days_since_delivery`.
- Risk of regression: Medium. Missing-info normalization can mask naming drift if overused. The alias mapping is intentionally small and limited to known schema vocabulary differences.

## Improvement 3: Multi-Policy Retrieval And Citation Recall

- Failure cluster targeted: Retrieval missed relevant policy section.
- Files changed:
  - `src/return_agent/agent.py`
  - `src/return_agent/decision_agent.py`
  - `tests/test_post_baseline_improvements.py`
- Expected metric impact: Improve `policy_section_recall` by retrieving the full local policy corpus for agent runs and by adding supporting policy IDs for refund timing, refund method, store credit, customer-initiated reasons, restricted items, final-sale exceptions, and damage responsibility.
- Risk of regression: Low to medium. Full-corpus retrieval increases evidence volume in traces and the Streamlit evidence expander, but it remains local and deterministic. It may slightly reduce demo readability while improving citation validation and eval recall.

## Improvement 4: Post-Improvement Eval Output Support

- Failure cluster targeted: Evaluation reporting and reproducibility.
- Files changed:
  - `scripts/run_local_eval.py`
- Expected metric impact: No direct agent metric impact. Enables separate baseline and post-improvement artifacts without overwriting baseline files.
- Risk of regression: Low. Defaults preserve the original baseline output paths; optional CLI arguments write post-improvement files.
