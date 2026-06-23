# LangSmith Instrumentation Plan

## Objective

Add optional LangSmith tracing and evaluation support without changing the Return Policy Agent behavior.

LangSmith should capture:

- End-to-end agent runs.
- The three intentional LLM calls.
- Deterministic retrieval.
- Deterministic guardrails.
- Deterministic validation.
- Final answer generation.
- Latency.
- Token usage and cost when available.

## Trace Hierarchy

Recommended run tree:

```text
return_policy_agent.run
  intent_extraction.llm
  safety_precheck.deterministic
  policy_retrieval.deterministic
  structured_decision.llm
  validator.deterministic
  final_answer.llm
  citation_validation.deterministic
```

## Run Metadata

Every top-level run should include:

```json
{
  "agent_name": "Northstar Commerce Return Policy Agent",
  "dataset_case_id": "golden_001",
  "scenario_type": "standard_eligible_return",
  "case_group": "happy_path",
  "retriever_type": "local_keyword_bm25_like",
  "policy_corpus_version": "local_markdown_v1",
  "uses_openai": true,
  "llm_call_count_expected": 3
}
```

## Inputs To Capture

Top-level input:

```json
{
  "customer_message": "...",
  "order_context": {
    "order_date": null,
    "delivery_date": null,
    "item_category": null,
    "item_condition": null,
    "final_sale": null,
    "order_value": null,
    "proof_of_purchase": null,
    "order_number": null
  }
}
```

## Outputs To Capture

Top-level output:

```json
{
  "decision": "eligible_return",
  "reason_code": "standard_30_day",
  "missing_info": [],
  "escalate": false,
  "confidence": 0.92,
  "policy_sections_used": ["POLICY:STANDARD_RETURN_WINDOW"],
  "citations": ["01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]"],
  "customer_answer": "..."
}
```

## Step-Level Trace Fields

### Intent Extraction

Capture:

- Input message and order context.
- Extracted intent.
- Requested resolution.
- Extracted facts.
- Missing info.
- Risk flags.
- Model name.
- Token usage.
- Latency.
- Fallback mode when no API key is present.

### Safety Pre-Check

Capture:

- Escalation result.
- Reason code.
- Risk flags.
- Matched rule names.
- Latency.

This step must remain deterministic.

### Retrieval

Capture:

- Retrieval query.
- Top-k value.
- Retrieved chunk IDs.
- Document names.
- Policy IDs.
- Section headings.
- Scores if available.
- Latency.

This step must remain deterministic and local.

### Structured Decision

Capture:

- Extracted facts.
- Safety result.
- Retrieved policy context.
- Raw LLM structured output.
- Parsed structured decision.
- Model name.
- Token usage.
- Latency.

### Validator

Capture:

- Validation errors.
- Whether corrected.
- Corrected decision.
- Citation validation result.
- Latency.

This step must remain deterministic.

### Final Answer

Capture:

- Validated decision input.
- Citations.
- Final customer-facing answer.
- Model name.
- Token usage.
- Latency.

The final answer step must not create a new decision.

## Environment Variables

Suggested optional variables:

```text
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=return-policy-agent-week4
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

The app and local smoke tests must still run when these variables are absent.

## Dataset And Eval Run Design

LangSmith dataset name:

```text
return-policy-agent-golden-v1
```

Baseline experiment:

```text
return-policy-agent-week4-baseline
```

Post-improvement experiment:

```text
return-policy-agent-week4-post-improvement
```

## Implementation Steps

1. Add optional LangSmith dependency.
2. Create a trace adapter that wraps current trace data without changing agent decisions.
3. Add dataset upload script for `data/golden_dataset.jsonl`.
4. Add eval runner script that calls `ReturnPolicyAgent.run`.
5. Map existing evaluator functions to LangSmith evaluator signatures.
6. Add LLM judge evaluator for faithfulness.
7. Run baseline experiment.
8. Export failures for analysis.

## Guardrails

LangSmith instrumentation must not:

- Add extra LLM decision calls.
- Change retrieval behavior.
- Change validator behavior.
- Require LangSmith for local app usage.
- Log secrets such as API keys.
