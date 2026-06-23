# Week 4 Evaluation Plan

## Agent Under Test

Northstar Commerce Return Policy Agent.

The eval target is the backend pipeline, not the Streamlit UI:

```text
ReturnPolicyAgent.run(payload) -> structured decision + customer answer + trace
```

The UI can be tested manually for demo readiness, but Week 4 metrics should call the agent directly so the results measure policy reasoning, retrieval, validation, citation behavior, latency, and cost without browser noise.

## User Outcome

Customers receive accurate, policy-grounded return, refund, exchange, shipping-fee, and gift-return guidance. Risky, abusive, legal, fraud, high-value, exception-based, or policy-ambiguous cases are escalated instead of answered incorrectly.

## Evaluation Goals

1. Build a 40-case golden dataset with labeled expected outputs.
2. Run a baseline evaluation against the current agent.
3. Capture LangSmith traces for end-to-end runs, LLM calls, retrieval, guardrails, validation, answer generation, latency, token usage, and estimated cost.
4. Analyze failures by type and severity.
5. Make 3-4 targeted improvements after the baseline.
6. Run the same evaluation again.
7. Report metric deltas and remaining risks.

## Golden Dataset Mix

The final Week 4 golden dataset should contain exactly 40 labeled examples:

| Group | Count | Purpose |
| --- | ---: | --- |
| Happy path | 20 | Common standard returns, exchanges, gifts, shipping questions, refund timing, and eligible cases. |
| Edge cases | 12 | Missing facts, final sale, personalized items, damaged/wrong/missing items, high value, partial proof, ambiguous timing. |
| Known failures | 6 | Cases selected from observed baseline mistakes or likely weak spots, such as conflicting facts or citation edge cases. |
| Adversarial | 2 | Prompt injection, ignore-policy requests, legal threats, abusive or manipulative phrasing. |

The current `data/golden_dataset_sample.jsonl` contains 5 sample rows only. It is a format example, not the final golden dataset.

## Dataset Labeling Rules

Each case must include:

- Stable `id`.
- `dataset_split`: `golden`.
- `case_group`: `happy_path`, `edge_case`, `known_failure`, or `adversarial`.
- `scenario_type`.
- `customer_message`.
- `order_context`.
- Expected structured outputs.
- Expected citation policy IDs.
- Notes describing why the label is correct.

Labels should be based on the local markdown policy corpus, not on desired model behavior. If policy wording is ambiguous, mark the case as `edge_case` or `known_failure` and explain the ambiguity in `label_notes`.

## Baseline Run

The baseline run should evaluate the existing agent before behavior changes.

Baseline procedure:

1. Freeze the golden dataset.
2. Record the current git commit or local snapshot.
3. Run the agent on every golden case.
4. Store every run in LangSmith with trace metadata.
5. Compute deterministic metrics.
6. Run faithfulness LLM judge for answer grounding.
7. Export failed cases for analysis.

Baseline run name:

```text
return-policy-agent-week4-baseline
```

## Metrics And Pass Bars

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

## Failure Analysis

Failures should be grouped into these categories:

- Retrieval miss: relevant policy section was not retrieved.
- Decision miss: evidence was available but the structured decision was wrong.
- Missing-info miss: the agent answered when required facts were absent, or asked for unnecessary facts.
- Escalation miss: a risky case was not escalated, or a safe case was escalated unnecessarily.
- Citation miss: citations were missing, invalid, or not tied to retrieved policy evidence.
- Faithfulness miss: final answer added unsupported policy claims.
- Latency or cost issue: run exceeded performance or cost thresholds.

## Improvement Loop

After the baseline, make 3-4 targeted improvements only. Examples:

1. Retrieval query tuning for weak policy categories.
2. Policy chunking or citation metadata improvements.
3. Validator rule priority fixes for known decision conflicts.
4. Prompt/schema tightening for structured decision or final answer generation.

Each improvement should be tied to a failure category and re-tested against the full golden dataset.

## Post-Improvement Run

Post-improvement run name:

```text
return-policy-agent-week4-post-improvement
```

The final report should compare baseline and post-improvement results:

| Metric | Baseline | Post-Improvement | Delta | Pass Bar Met |
| --- | ---: | ---: | ---: | --- |
| decision_accuracy | | | | |
| reason_code_accuracy | | | | |
| missing_info_f1 | | | | |
| escalation_accuracy | | | | |
| citation_coverage | | | | |
| faithfulness_llm_judge | | | | |
| p95_latency | | | | |
| cost_per_run | | | | |

## Deliverables

Week 4 deliverables:

- `data/golden_dataset.jsonl` with 40 labeled cases.
- LangSmith baseline run.
- Failure analysis notes.
- 3-4 targeted improvements.
- LangSmith post-improvement run.
- Final evaluation report with metric deltas and examples.
