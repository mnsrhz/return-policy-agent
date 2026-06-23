# LangSmith Setup

## Purpose

This project can optionally send Week 4 evaluation traces to LangSmith. LangSmith is used for:

- End-to-end agent run traces.
- Step-level spans for intent extraction, safety pre-check, retrieval, structured decision, validation, final answer generation, and citation validation.
- Dataset-backed baseline runs.
- Failure review.
- Baseline versus post-improvement comparison.

The agent still runs locally without LangSmith.

## Create A LangSmith Project

1. Sign in to LangSmith.
2. Create or select a workspace.
3. Create a project named:

```text
return-policy-agent-eval
```

4. Create an API key from LangSmith settings.

## Required Environment Variables

Copy `.env.example` to `.env` and set:

```text
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=return-policy-agent-eval
OPENAI_API_KEY=your_openai_api_key
```

`OPENAI_API_KEY` is needed only when running the OpenAI-backed agent stages or the LLM-as-judge faithfulness evaluator. The deterministic agent and local eval still run without it.

## Install Dependencies

```bash
.venv/bin/pip install -r requirements.txt
```

The LangSmith scripts require the `langsmith` package.

## Upload The Golden Dataset

The golden dataset lives at:

```text
data/golden_dataset.jsonl
```

Upload it to LangSmith:

```bash
.venv/bin/python scripts/upload_dataset_to_langsmith.py
```

The script creates or reuses this dataset:

```text
return-policy-golden-v1
```

Each uploaded example includes:

- Inputs: `customer_message`, `order_context`.
- Expected outputs: decision, reason code, missing info, escalation flag, expected policy sections, answer traits.
- Metadata: case ID, scenario type, difficulty, expected decision, expected reason code.

## Run Baseline Eval

Run:

```bash
.venv/bin/python scripts/run_langsmith_eval.py
```

This evaluates the current agent against the LangSmith dataset and writes:

```text
eval_runs/langsmith_baseline_summary.json
eval_runs/langsmith_baseline_failures.jsonl
```

The baseline should be run before improving the agent.

## Traced Steps

When LangSmith tracing is enabled, the agent records these spans where possible:

- `top_level_agent_run`
- `intent_extraction_llm`
- `safety_precheck`
- `policy_retrieval`
- `structured_decision_llm`
- `deterministic_validator`
- `final_answer_llm`
- `citation_validation`

Each trace captures:

- Input payload.
- Retrieved policy chunks.
- Structured decision.
- Validator result.
- Final answer.
- Citations.
- Latency.
- Token usage when available.
- Errors.
- Retry count when available from model/tool metadata.

## Evaluators

The LangSmith eval runner applies:

- `decision_accuracy`
- `reason_code_accuracy`
- `missing_info_f1`
- `escalation_accuracy`
- `citation_coverage`
- `policy_section_recall`
- `schema_validity`
- `faithfulness_llm_judge`

The faithfulness judge uses this rubric:

- `1.0`: Answer is fully supported by policy citations, does not invent refund promises, and does not contradict final sale, damaged item, shipping fee, or escalation policy.
- `0.5`: Answer is mostly grounded but includes minor unsupported wording.
- `0.0`: Answer hallucinates policy, contradicts retrieved policy, or promises a refund or exception without support.

If OpenAI credentials are unavailable, the script falls back to a conservative deterministic faithfulness check so the runner can still produce output when LangSmith is available.

## Find Traces

In LangSmith:

1. Open the `return-policy-agent-eval` project.
2. Filter runs by the dataset metadata, such as:

```text
case_id = RET-001
scenario_type = edge_case
difficulty = hard
```

3. Open the `top_level_agent_run` trace.
4. Inspect child spans for retrieval, decision, validation, answer generation, and citation validation.

## Compare Baseline And Post-Improvement Runs

Recommended workflow:

1. Upload the golden dataset.
2. Run `scripts/run_langsmith_eval.py`.
3. Save `eval_runs/langsmith_baseline_summary.json`.
4. Review `eval_runs/langsmith_baseline_failures.jsonl`.
5. Make 3-4 targeted improvements.
6. Run the same eval again and save results as a post-improvement summary.
7. Compare metric deltas:

```text
decision_accuracy
reason_code_accuracy
missing_info_f1
escalation_accuracy
citation_coverage
policy_section_recall
schema_validity
faithfulness_llm_judge
```

The Week 4 report should include baseline score, post-improvement score, delta, and examples of cases that improved or regressed.
