# Week 4 Eval Plan

## Goal

The Week 4 evaluation will measure whether the Northstar Commerce Return Policy Agent makes correct, grounded, citation-backed decisions across representative return, refund, exchange, shipping fee, gift, and escalation scenarios.

This project now includes a small local seed set in `data/sample_cases.jsonl`. These 10 cases are for smoke testing only. They are not the final golden dataset.

## Evaluation Targets

The primary eval target will be the backend agent function:

```text
ReturnPolicyAgent.run(payload) -> structured decision
```

The eval should call the backend directly rather than driving the Streamlit UI. This keeps the evaluation deterministic, fast, and independent from presentation details.

## Golden Dataset Plan

The full golden dataset should expand beyond the 10 seed cases and include:

- Standard eligible returns.
- Missing delivery date, condition, and proof-of-purchase cases.
- Final sale and restricted item cases.
- Personalized item exceptions.
- Damaged, defective, wrong, missing, and not-as-described cases.
- Shipping-fee cases for customer-initiated and Northstar-caused reasons.
- Gift returns and store credit.
- Exchange requests with inventory caveats.
- High-value refunds over $500.
- Legal threats, abuse concerns, fraud concerns, and policy exception requests.
- Ambiguous or conflicting customer facts.

Each golden case should include expected decision, reason code, missing information, escalation flag, relevant policy IDs, and notes for failure analysis.

## Baseline Run

The first LangSmith run should establish a baseline using the current deterministic backend and local policy corpus.

Baseline metrics should include:

- Decision accuracy.
- Reason code accuracy.
- Missing information F1.
- Escalation accuracy.
- Citation presence.
- Citation relevance or faithfulness.
- Optional customer-answer usefulness scored by a human or LLM evaluator.

The local smoke script provides early versions of the first four metrics:

```bash
python scripts/run_smoke_tests.py
```

## LangSmith Integration In Part 2

Part 2 should add optional LangSmith code that:

1. Creates or loads a LangSmith dataset from the golden cases.
2. Wraps `ReturnPolicyAgent.run` as the target function.
3. Maps each dataset example into `customer_message` and `order_context`.
4. Stores retrieved policy chunks and citations as run metadata.
5. Runs evaluators for decision, reason code, missing info, escalation, and citations.
6. Compares baseline and post-improvement runs.

LangSmith should be optional: local smoke tests must remain runnable without API keys.

## Failure Analysis

After the baseline run, failures should be grouped by failure type:

- Retrieval miss: the right policy section was not retrieved.
- Decision rule miss: the right evidence was retrieved but the decision was wrong.
- Missing-info miss: the agent answered before collecting required facts.
- Escalation miss: the agent failed to route a support-review case.
- Citation miss: the answer cited no policy or the wrong policy.
- Answer quality issue: the structured decision was correct but customer-facing wording was unclear.

Each failure group should produce one targeted improvement. Avoid broad prompt or rule changes that make unrelated cases worse.

## Improvement Loop

Recommended Week 4 loop:

1. Run baseline eval.
2. Export or inspect failed examples.
3. Classify failures by type.
4. Make one targeted retrieval, policy, schema, or decision change.
5. Re-run local smoke tests.
6. Re-run LangSmith eval.
7. Compare baseline and post-improvement metrics.
8. Document what improved, what regressed, and what remains unresolved.

## Post-Improvement Run

The final Week 4 report should include:

- Baseline metric table.
- Post-improvement metric table.
- Top failure categories before improvement.
- Changes made.
- Examples that improved.
- Examples that still fail.
- Notes on whether failures are caused by policy ambiguity, retrieval, decision logic, or dataset design.

## Current Local Readiness

Current local eval assets:

- `data/sample_cases.jsonl`: 10 seed cases.
- `scripts/run_smoke_tests.py`: local smoke metrics.
- `src/return_agent/evaluators.py`: placeholder evaluator functions that can later be adapted to LangSmith evaluator signatures.

No LangSmith dependency or API key is required at this stage.
