from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Optional

from return_agent.evaluators import (
    citation_coverage,
    decision_accuracy,
    escalation_accuracy,
    missing_info_f1,
    policy_section_recall,
    reason_code_accuracy,
    schema_validity,
)
from return_agent.langsmith_tracing import load_env_file
from return_agent.llm_utils import call_responses_json
from return_agent.openai_client import build_openai_client, load_openai_settings


def local_metric_scores(prediction: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, float]:
    return {
        "decision_accuracy": decision_accuracy(prediction, expected),
        "reason_code_accuracy": reason_code_accuracy(prediction, expected),
        "missing_info_f1": missing_info_f1(prediction, expected),
        "escalation_accuracy": escalation_accuracy(prediction, expected),
        "citation_coverage": citation_coverage(prediction, expected),
        "policy_section_recall": policy_section_recall(prediction, expected),
        "schema_validity": schema_validity(prediction),
    }


def make_langsmith_evaluators(include_faithfulness: bool = True) -> List[Any]:
    load_env_file()
    evaluators = [
        _make_metric_evaluator("decision_accuracy", decision_accuracy),
        _make_metric_evaluator("reason_code_accuracy", reason_code_accuracy),
        _make_metric_evaluator("missing_info_f1", missing_info_f1),
        _make_metric_evaluator("escalation_accuracy", escalation_accuracy),
        _make_metric_evaluator("citation_coverage", citation_coverage),
        _make_metric_evaluator("policy_section_recall", policy_section_recall),
        _make_schema_evaluator(),
    ]
    if include_faithfulness and os.getenv("OPENAI_API_KEY"):
        evaluators.append(faithfulness_llm_judge)
    return evaluators


def faithfulness_llm_judge(run: Any, example: Any) -> Dict[str, Any]:
    prediction = _extract_run_outputs(run)
    expected = _extract_example_outputs(example)
    trace = prediction.get("trace", {})
    retrieved_chunks = prediction.get("retrieved_chunks") or trace.get("retrieved_chunks") or []

    prompt = render_faithfulness_prompt(
        customer_message=_extract_example_inputs(example).get("customer_message", ""),
        expected=expected,
        prediction=prediction,
        retrieved_chunks=retrieved_chunks,
    )

    load_env_file()
    settings = load_openai_settings()
    client = build_openai_client(settings.api_key)
    data, usage = call_responses_json(client, model=settings.model, prompt=prompt)
    score = float(data.get("score", 0.0))
    score = max(0.0, min(1.0, score))
    return {
        "key": "faithfulness_llm_judge",
        "score": score,
        "comment": data.get("reasoning", ""),
        "metadata": {
            "failure_type": data.get("failure_type"),
            "token_usage": usage,
        },
    }


def deterministic_faithfulness_score(prediction: Dict[str, Any]) -> float:
    answer = str(prediction.get("customer_answer", "")).lower()
    if not prediction.get("citations"):
        return 0.0
    blocked_phrases = [
        "refund approved",
        "guaranteed refund",
        "exception approved",
        "final sale return is approved",
    ]
    if any(phrase in answer for phrase in blocked_phrases):
        return 0.0
    return 1.0


def render_faithfulness_prompt(
    *,
    customer_message: str,
    expected: Dict[str, Any],
    prediction: Dict[str, Any],
    retrieved_chunks: Iterable[Dict[str, Any]],
) -> str:
    evidence = "\n\n".join(
        f"{chunk.get('source_citation')}\n{chunk.get('chunk_text', '')}"
        for chunk in retrieved_chunks
    )
    return f"""Judge whether the final customer answer is faithful to the retrieved Northstar Commerce policy evidence.

Score 1.0 if:
- The answer is fully supported by policy citations.
- The answer does not invent refund promises.
- The answer does not contradict final sale, damaged item, shipping fee, or escalation policy.

Score 0.5 if:
- The answer is mostly grounded but includes minor unsupported wording.

Score 0.0 if:
- The answer hallucinates policy.
- The answer contradicts retrieved policy.
- The answer promises a refund or exception without support.

Customer message:
{customer_message}

Expected labels:
{json.dumps(expected, indent=2)}

Predicted output:
{json.dumps(prediction, indent=2)}

Retrieved policy evidence:
{evidence}

Return JSON only:
{{
  "score": 1.0,
  "reasoning": "short explanation",
  "failure_type": null
}}
"""


def _make_metric_evaluator(name: str, metric_func):
    def evaluator(run: Any, example: Any) -> Dict[str, Any]:
        prediction = _extract_run_outputs(run)
        expected = _extract_example_outputs(example)
        return {"key": name, "score": metric_func(prediction, expected)}

    evaluator.__name__ = name
    return evaluator


def _make_schema_evaluator():
    def evaluator(run: Any, example: Any) -> Dict[str, Any]:
        prediction = _extract_run_outputs(run)
        return {"key": "schema_validity", "score": schema_validity(prediction)}

    evaluator.__name__ = "schema_validity"
    return evaluator


def _extract_run_outputs(run: Any) -> Dict[str, Any]:
    if isinstance(run, dict):
        return run.get("outputs") or run
    return getattr(run, "outputs", None) or {}


def _extract_example_outputs(example: Any) -> Dict[str, Any]:
    if isinstance(example, dict):
        return example.get("outputs") or example.get("expected") or example
    return getattr(example, "outputs", None) or {}


def _extract_example_inputs(example: Any) -> Dict[str, Any]:
    if isinstance(example, dict):
        return example.get("inputs") or example
    return getattr(example, "inputs", None) or {}
