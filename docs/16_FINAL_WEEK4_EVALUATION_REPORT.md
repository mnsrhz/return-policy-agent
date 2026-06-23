# Final Week 4 Evaluation Report

## 1. Evaluation One-Liner

Evaluate whether the Northstar Commerce Return Policy Agent gives accurate, policy-grounded return/refund/exchange guidance, asks for missing facts, cites policy evidence, and escalates risky or exception-based cases.

## 2. Agent Under Test

Agent: Northstar Commerce Return Policy Agent.

Evaluation target: `ReturnPolicyAgent.run(payload) -> structured decision + customer answer + trace`. The Streamlit UI was not the metric target; local and planned LangSmith evals call the backend directly.

## 3. User Outcome

Customers should receive clear return, refund, exchange, gift-return, and shipping-fee guidance grounded in Northstar policy. The agent should not approve unsupported refunds or exceptions, and should escalate legal, fraud, high-value, policy-exception, adversarial, or unclear responsibility cases.

## 4. Metrics And Judge Methods

| Metric | Method | Pass Bar |
| --- | --- | ---: |
| `decision_accuracy` | Exact match on structured decision. | >= 90% |
| `reason_code_accuracy` | Exact match on reason code. | >= 85% |
| `missing_info_f1` | Set-based F1 over missing information fields. | >= 85% |
| `escalation_accuracy` | Exact boolean match on escalation flag. | >= 95% |
| `citation_coverage` | Requires citations that map to retrieved policy evidence. | = 100% |
| `policy_section_recall` | Recall over expected policy sections. | Diagnostic |
| `schema_validity` | Required structured output fields are present and typed. | Diagnostic |
| `faithfulness_llm_judge` | Planned LLM judge for grounded final answers. | >= 90% |
| `p95_latency` | Planned LangSmith/runtime p95 latency. Local report uses average latency only. | < 8s |
| `cost_per_run` | Planned LangSmith/model-cost metric. | < $0.05 |

## 5. Golden Dataset Design

The golden dataset contains 40 labeled cases in `data/golden_dataset.jsonl`:

| Scenario Type | Count | Purpose |
| --- | ---: | --- |
| `happy_path` | 20 | Common supported standard returns, exchanges, gifts, refund timing, and shipping questions. |
| `edge_case` | 12 | Boundary and restricted-policy cases: final sale, no receipt, used item, mixed items, unsupported channels. |
| `known_failure` | 6 | Cases selected to expose likely weaknesses in rule priority, missing-info, escalation, and retrieval recall. |
| `adversarial` | 2 | Prompt-injection and final-sale override attempts. |

Each row includes customer message, order context, expected decision, expected reason code, expected missing info, expected escalation flag, expected policy sections, answer traits, and notes.

## 6. LangSmith Instrumentation Summary

LangSmith support was added for the full backend agent run and the major pipeline steps. The available `eval_runs/langsmith_baseline_summary.json` artifact contains 40 traced/evaluated cases with 100.00% scores on the deterministic evaluators and `faithfulness_llm_judge`. A separate `eval_runs/langsmith_post_improvement_summary.json` artifact was not available at report time, so post-improvement LangSmith values remain placeholders.

The tracing plan supports these spans:

- `top_level_agent_run`
- `intent_extraction_llm`
- `safety_precheck`
- `policy_retrieval`
- `structured_decision_llm`
- `deterministic_validator`
- `final_answer_llm`
- `citation_validation`

LangSmith baseline link: `[placeholder: add LangSmith baseline experiment URL]`
LangSmith post-improvement link: `[placeholder: add LangSmith post-improvement experiment URL]`

## 7. Baseline Results Table

Local baseline results from `eval_runs/local_baseline_summary.json`:

| Metric | Baseline | Pass Bar | Status |
| --- | ---: | ---: | --- |
| `decision_accuracy` | 62.50% | >= 90% | Fail |
| `reason_code_accuracy` | 65.00% | >= 85% | Fail |
| `missing_info_f1` | 66.25% | >= 85% | Fail |
| `escalation_accuracy` | 87.50% | >= 95% | Fail |
| `citation_coverage` | 100.00% | = 100% | Pass |
| `policy_section_recall` | 60.00% | Diagnostic | Diagnostic |
| `schema_validity` | 100.00% | Diagnostic | Diagnostic |
| `average_latency_seconds` | 0.0012s | Diagnostic | Diagnostic |
| `faithfulness_llm_judge` | N/A | >= 90% | Not measured |
| `p95_latency` | N/A | < 8s | Not measured |
| `cost_per_run` | N/A | < $0.05 | Not measured |

Available LangSmith baseline artifact from `eval_runs/langsmith_baseline_summary.json`:

| Metric | LangSmith Baseline Artifact | Pass Bar | Status |
| --- | ---: | ---: | --- |
| `decision_accuracy` | 100.00% | >= 90% | Pass |
| `reason_code_accuracy` | 100.00% | >= 85% | Pass |
| `missing_info_f1` | 100.00% | >= 85% | Pass |
| `escalation_accuracy` | 100.00% | >= 95% | Pass |
| `citation_coverage` | 100.00% | = 100% | Pass |
| `policy_section_recall` | 100.00% | Diagnostic | Diagnostic |
| `schema_validity` | 100.00% | Diagnostic | Diagnostic |
| `faithfulness_llm_judge` | 100.00% | >= 90% | Pass |
| `average_latency_seconds` | 0.0124s | Diagnostic | Diagnostic |
| `p95_latency` | N/A | < 8s | Not measured |
| `cost_per_run` | N/A | < $0.05 | Not measured |

## 8. Failure Analysis Table

| Failure Cluster | Count | Example Case | Likely Root Cause |
| --- | ---: | --- | --- |
| Incorrect eligibility decision | 15 | RET-006 | Generic ask-for-info or wrong escalation branch used instead of conclusive policy outcome. |
| Incorrect reason code | 14 | RET-009 | Reason-code priority was too coarse and confused customer wrong-size with fulfillment wrong-item. |
| Missed missing-information request | 14 | RET-034 | Missing-info field names and branch behavior did not align with golden labels. |
| Missed escalation | 5 | RET-035 | Some policy-required review cases were not escalated correctly. |
| Missing or invalid citation | 0 | none | No local citation failures observed. |
| Retrieval missed relevant policy section | 22 | RET-004 | Valid citations existed, but multi-policy expected sections were often omitted. |
| Final answer hallucinated or overpromised | 0 | not measured | No LLM-judge artifact available locally. |
| Schema violation | 0 | none | No schema failures observed. |
| Latency or cost issue | 0 | none | No local latency issue; cost was not measured without LangSmith/model usage. |

## 9. Improvements Implemented

1. Edge-case decision and reason priority: added targeted deterministic rules for shipping fees, outside-window returns, used items, restricted products, refund method questions, unsupported channels, final-sale exception context, and damage responsibility.
2. Canonical missing-info handling: aligned delivery-date/days-since-delivery evaluation, no-proof, no-order-number, gift receipt, high-value missing proof, damaged-item evidence, and mixed-item facts.
3. Multi-policy retrieval and citation recall: expanded local evidence retrieval and added supporting policy IDs for multi-policy outcomes.
4. Post-improvement eval output support: added CLI output paths so baseline and post-improvement artifacts remain separate.

## 10. Post-Improvement Results Table

Local post-improvement results from `eval_runs/local_post_improvement_summary.json`:

| Metric | Post-Improvement | Pass Bar | Status |
| --- | ---: | ---: | --- |
| `decision_accuracy` | 100.00% | >= 90% | Pass |
| `reason_code_accuracy` | 100.00% | >= 85% | Pass |
| `missing_info_f1` | 100.00% | >= 85% | Pass |
| `escalation_accuracy` | 100.00% | >= 95% | Pass |
| `citation_coverage` | 100.00% | = 100% | Pass |
| `policy_section_recall` | 100.00% | Diagnostic | Diagnostic |
| `schema_validity` | 100.00% | Diagnostic | Diagnostic |
| `average_latency_seconds` | 0.0011s | Diagnostic | Diagnostic |
| `faithfulness_llm_judge` | N/A | >= 90% | Not measured |
| `p95_latency` | N/A | < 8s | Not measured |
| `cost_per_run` | N/A | < $0.05 | Not measured |

LangSmith post-improvement results were not available as a separate artifact at report time.

## 11. Delta Table

| Metric | Baseline | Post-improvement | Delta | Pass bar | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| `decision_accuracy` | 62.50% | 100.00% | +37.50% | >= 90% | Pass |
| `reason_code_accuracy` | 65.00% | 100.00% | +35.00% | >= 85% | Pass |
| `missing_info_f1` | 66.25% | 100.00% | +33.75% | >= 85% | Pass |
| `escalation_accuracy` | 87.50% | 100.00% | +12.50% | >= 95% | Pass |
| `citation_coverage` | 100.00% | 100.00% | +0.00% | = 100% | Pass |
| `policy_section_recall` | 60.00% | 100.00% | +40.00% | Diagnostic | Diagnostic |
| `faithfulness_llm_judge` | 100.00% LangSmith artifact; N/A local | N/A post-improvement LangSmith | N/A | >= 90% | Baseline artifact pass; post not measured |
| `schema_validity` | 100.00% | 100.00% | +0.00% | Diagnostic | Diagnostic |
| `p95_latency` | N/A | N/A | N/A | < 8s | Not measured |
| `cost_per_run` | N/A | N/A | N/A | < $0.05 | Not measured |

## 12. What Improved

- Decision accuracy improved from 62.50% to 100.00%.
- Reason-code accuracy improved from 65.00% to 100.00%.
- Missing-info F1 improved from 66.25% to 100.00%.
- Escalation accuracy improved from 87.50% to 100.00%.
- Policy-section recall improved from 60.00% to 100.00%.
- Citation coverage and schema validity stayed at 100.00%.

## 13. What Did Not Improve

- A separate LangSmith post-improvement run was not available, so faithfulness delta was not measured.
- p95 latency and cost-per-run were not measured in the available artifacts.
- Citation coverage and schema validity had no room to improve because both started at 100%.
- Local eval uses deterministic agent execution, so it does not measure the full OpenAI-backed three-call path or model-cost behavior.

## 14. Remaining Failure Modes

- The local golden dataset is now fully passed, which creates risk of overfitting to the 40 labeled cases.
- Full-corpus retrieval improves recall but may make traces and the Streamlit evidence section noisier.
- Faithfulness needs a paired baseline/post-improvement LangSmith comparison to produce a true delta.
- LangSmith p95 latency and model cost need to be captured in future traced runs.
- Additional unseen adversarial, policy-conflict, and multi-item cases should be added before production use.

## 15. What I Would Do Next

1. Run or export a separate LangSmith post-improvement experiment using the same dataset.
2. Add 10-20 fresh holdout cases that were not used during improvement.
3. Run the OpenAI-backed three-call flow under LangSmith to measure model-token cost and answer faithfulness.
4. Reduce full-corpus retrieval noise with a deterministic policy-expansion layer rather than always returning every chunk.
5. Add regression tests for any failures found by LangSmith or the holdout set.

## 16. Production Monitoring Strategy

- Track decision distribution by scenario type and watch for spikes in `eligible_return` or drops in escalation.
- Monitor citation coverage, invalid citation count, and policy-section recall on sampled traffic.
- Log missing-info fields to detect repeated customer friction or schema drift.
- Track p50/p95/p99 latency and cost per run for the three LLM calls.
- Sample final answers for faithfulness review, especially final sale, damaged items, shipping fees, and high-value refunds.
- Alert on any answer containing refund-approval or exception-approval language before inspection or support review.
- Maintain a rolling golden dataset with new real-world failure cases and rerun baseline/post-improvement comparisons after policy or prompt changes.
