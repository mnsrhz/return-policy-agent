# Improvement Playbook

## Purpose

Use this playbook after the baseline evaluation. Do not make broad changes because a single case failed. Each improvement should map to a failure category, include a regression test, and be measured in the post-improvement run.

## Improvement 1: Retrieval Query And Chunk Coverage

Use when:

- Relevant policy sections are not retrieved.
- Retrieved chunks are too generic.
- Citation coverage fails because the needed policy ID is absent from evidence.

Likely files:

- `src/return_agent/retriever.py`
- `src/return_agent/chunker.py`
- `policy_docs/*.md`
- Retrieval tests.

Actions:

1. Add scenario-specific query terms from extracted intent and risk flags.
2. Improve policy ID preservation in chunks if needed.
3. Add retrieval tests for failed scenarios.
4. Re-run full eval.

Success criteria:

- Failed retrieval cases now include expected policy IDs in top retrieved chunks.
- Citation coverage improves without hurting latency.

## Improvement 2: Structured Decision Prompt Or Schema Tightening

Use when:

- Correct evidence is retrieved but the LLM picks the wrong decision.
- The LLM emits unsupported reason codes.
- The LLM includes contradictory missing info.

Likely files:

- `src/return_agent/decision_agent.py`
- `src/return_agent/prompts.py`
- `src/return_agent/models.py`
- Structured decision tests.

Actions:

1. Add a focused prompt constraint for the failing rule.
2. Keep the schema narrow and explicit.
3. Add regression tests with deterministic fallback or mocked LLM output.
4. Re-run eval and check for regressions.

Success criteria:

- Decision and reason code accuracy improve.
- No increase in unsafe approvals.

## Improvement 3: Deterministic Validator Rule Priority

Use when:

- The LLM output is close but unsafe or internally inconsistent.
- Known policy hierarchy should override generic behavior.
- Safety escalation, final sale, or citation requirements are mishandled.

Likely files:

- `src/return_agent/validator.py`
- `src/return_agent/citations.py`
- Validator tests.

Actions:

1. Define the rule priority explicitly.
2. Add a failing validator test first.
3. Implement the narrowest deterministic correction.
4. Run full tests and golden eval.

Suggested rule priority:

```text
schema validity
citations available
safety escalation
escalate flag consistency
final sale hard blocker unless damaged/wrong/missing
missing-info handling
low-confidence handling
policy-section validation
```

Success criteria:

- Unsafe outcomes are blocked.
- Escalation accuracy and citation coverage remain at pass bar.

## Improvement 4: Final Answer Faithfulness

Use when:

- Structured decision is correct but the customer-facing answer invents policy.
- The answer promises refund approval before inspection.
- The answer omits citations.
- Ask-for-info answers request irrelevant fields.

Likely files:

- `src/return_agent/answer_generator.py`
- `src/return_agent/prompts.py`
- Final answer tests.

Actions:

1. Make validated decision the only source of truth.
2. Require citations in the final answer.
3. Ban refund approval language before inspection.
4. Add faithfulness test cases for failed scenarios.

Success criteria:

- Faithfulness judge score improves.
- Citation coverage remains `1.00`.

## Improvement 5: Dataset Label Corrections

Use when:

- A failure is caused by an incorrect or ambiguous expected label.
- Policy documents do not support the expected answer.
- Expected missing info is over-specified.

Likely files:

- `data/golden_dataset.jsonl`
- `docs/10_FAILURE_ANALYSIS_TEMPLATE.md`

Actions:

1. Compare expected labels to policy corpus.
2. Update labels only when policy evidence supports the change.
3. Record the reason in `label_notes`.
4. Re-run baseline if the dataset changed before improvement comparison.

Success criteria:

- Dataset labels reflect policy truth, not model preference.

## Change Control

Every improvement should include:

- Linked failed case IDs.
- One-sentence hypothesis.
- Files changed.
- Regression tests.
- Baseline score.
- Post-change score.
- Notes on regressions.

Avoid:

- Adding broad prompt text that changes many scenarios at once.
- Hiding failures by loosening evaluators.
- Editing the golden dataset after seeing results unless the label is demonstrably wrong.
