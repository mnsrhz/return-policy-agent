# Eval Readiness Notes

## Part 1 Objective

Part 1 should produce an app architecture that is easy to evaluate later. LangSmith evals are not implemented yet, but the project should avoid patterns that make evals difficult, such as hiding agent logic inside Streamlit callbacks or returning only unstructured text.

## Eval-Ready Design Principles

- Keep Streamlit UI separate from agent decision logic.
- Keep retrieval separate from generation.
- Return structured decision objects.
- Log retrieved chunks and final citations.
- Use deterministic schema validation.
- Make prompts versioned and inspectable.
- Make policy corpus fixtures small enough for repeatable tests.
- Avoid relying on live ecommerce systems.

## Future LangSmith Eval Targets

Part 2 can introduce datasets that include:

- Customer question.
- Known case facts.
- Expected decision.
- Expected missing information.
- Expected escalation requirement.
- Relevant policy section IDs.
- Notes for human graders.

Suggested evaluator categories:

- `schema_validity`: Does the response match the decision schema?
- `decision_accuracy`: Is the eligibility decision correct?
- `missing_info_accuracy`: Does the agent ask for the right missing facts?
- `escalation_accuracy`: Does the agent escalate when policy requires it?
- `citation_relevance`: Do cited sections support the answer?
- `groundedness`: Does the answer avoid unsupported claims?
- `customer_helpfulness`: Is the response clear and actionable?

## Example Eval Cases For Part 2

| Case | Expected Behavior |
| --- | --- |
| Return within window, unused item, packaging present | Eligible with return window citation |
| Return after window | Ineligible unless an exception policy applies |
| Worn item with unclear condition rules | Needs more info or conditional based on policy |
| Final sale item | Ineligible with final sale citation |
| Damaged item on arrival | Escalate if policy requires inspection |
| Missing delivery date | Needs more info |
| Conflicting facts | Ask clarification |
| Unsupported non-return topic | Not applicable or redirect |

## Instrumentation To Add In Part 1

The implementation should prepare these data points even before LangSmith is added:

- `run_id` or local trace ID.
- User question.
- Extracted case facts.
- Retrieval query.
- Retrieved chunk IDs.
- Final cited chunk IDs.
- Structured decision output.
- Schema validation result.
- Error or fallback reason, if any.

These can initially be logged locally or stored in memory. In Part 2, they can become LangSmith metadata and evaluator inputs.

## Suggested Project Structure

```text
return-policy-agent/
  app.py
  README.md
  docs/
    01_PRD.md
    02_AGENT_SPEC.md
    03_RAG_SPEC.md
    04_POLICY_SCHEMA.md
    05_EVAL_READINESS_NOTES.md
  data/
    policies/
  src/
    return_policy_agent/
      __init__.py
      agent.py
      config.py
      models.py
      prompts.py
      rag.py
      schema.py
      tracing.py
  tests/
    test_agent_decisions.py
    test_policy_schema.py
    test_rag_retrieval.py
```

## Part 2 LangSmith Integration Plan

Part 2 should add LangSmith after the core app works locally:

1. Create a LangSmith dataset from representative return policy cases.
2. Wrap the core decision function as the eval target.
3. Add evaluators for schema validity, decision accuracy, citation relevance, and escalation behavior.
4. Store retrieval context as run metadata.
5. Compare prompt and retrieval changes across experiment runs.
6. Document how to run evals locally.

## Readiness Checklist

- Structured decision schema exists.
- Agent spec defines missing-info and escalation behavior.
- RAG spec defines citation metadata.
- Project structure keeps eval target separate from UI.
- Local traces can be mapped to LangSmith runs.
- Eval criteria are documented before implementation begins.
