# return-policy-agent

An eval-ready eCommerce Return Policy Agent for an Agentic AI / AI Evals course project.

## Goal

Build a Streamlit app where a customer asks return, refund, and exchange questions. The agent answers using a local RAG corpus of Northstar Commerce return policy documents. It produces structured decisions, cites policy sections, asks for missing information, and escalates when policy requires human review.

The project includes local evaluation assets, a 40-case golden dataset, post-improvement reports, and optional LangSmith tracing/eval support.

## Documentation

- [Product Requirements](docs/01_PRD.md)
- [Agent Specification](docs/02_AGENT_SPEC.md)
- [RAG Specification](docs/03_RAG_SPEC.md)
- [Policy Decision Schema](docs/04_POLICY_SCHEMA.md)
- [Eval Readiness Notes](docs/05_EVAL_READINESS_NOTES.md)
- [Final Week 4 Evaluation Report](docs/16_FINAL_WEEK4_EVALUATION_REPORT.md)
- [LangSmith Setup](docs/13_LANGSMITH_SETUP.md)

## User Journey

1. Customer asks a policy question in Streamlit.
2. Agent extracts known facts and identifies missing facts.
3. RAG retrieves relevant local policy sections.
4. Agent returns a structured decision with citations.
5. Agent asks follow-up questions or escalates when needed.

## Project Structure

```text
return-policy-agent/
  app.py
  docs/
  data/
  eval_runs/
  policy_docs/
  scripts/
  src/return_agent/
  tests/
```

## Local Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Run tests:

```bash
.venv/bin/python -m pytest
```

Run the Streamlit app:

```bash
.venv/bin/streamlit run app.py
```

Run local eval:

```bash
.venv/bin/python scripts/run_local_eval.py
```

## Where the LLM is Used

OpenAI is used in exactly three places when `USE_OPENAI_LM=true` and `OPENAI_API_KEY` is configured:

1. Intent and fact extraction from the customer message and optional order context.
2. Structured policy decision using retrieved local policy context.
3. Final customer-facing answer generation from the validated structured decision.

The rest of the system is deterministic code:

- Local markdown policy loading and retrieval.
- Hard guardrails and escalation overrides.
- Missing-info validation.
- Pydantic schema validation.
- Citation validation.
- Eval and smoke-test scoring.

If no OpenAI API key is available, the app falls back to deterministic extraction, decision, and answer generation so the project still runs locally.

## OpenAI Setup

Recommended local setup:

```bash
cp .env.example .env
```

Then set:

```text
USE_OPENAI_LM=true
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

## LangSmith Setup

Optional LangSmith tracing/eval settings:

```text
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=return-policy-agent-eval
```

Upload the golden dataset:

```bash
.venv/bin/python scripts/upload_dataset_to_langsmith.py
```

Run LangSmith eval:

```bash
.venv/bin/python scripts/run_langsmith_eval.py
```

## Generating Submission Artifacts

JSONL remains the source of truth for eval runs. To generate human-readable Excel and Word files for Week 4 submission, run:

```bash
python scripts/generate_submission_artifacts.py
```

The generated files are saved under `submissions/`, including the golden dataset workbook, baseline and post-improvement eval workbooks, failure analysis workbook, improvement log workbook, final evaluation report DOCX, and Loom walkthrough script DOCX.
