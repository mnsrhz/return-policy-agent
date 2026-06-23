from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from return_agent.agent import ReturnPolicyAgent
from return_agent.langsmith_eval import (
    deterministic_faithfulness_score,
    faithfulness_llm_judge,
    local_metric_scores,
)
from return_agent.langsmith_tracing import load_env_file, require_langsmith, run_traced_agent
from return_agent.retriever import build_default_retriever

from run_local_eval import adapt_order_context


DATASET_NAME = "return-policy-golden-v1"
OUTPUT_DIR = ROOT / "eval_runs"
SUMMARY_PATH = OUTPUT_DIR / "langsmith_baseline_summary.json"
FAILURES_PATH = OUTPUT_DIR / "langsmith_baseline_failures.jsonl"


def run_langsmith_eval() -> Dict[str, Any]:
    load_env_file()
    require_langsmith()
    from langsmith import Client

    client = Client()
    examples = list(client.list_examples(dataset_name=DATASET_NAME))
    if not examples:
        raise RuntimeError(
            f"No examples found in LangSmith dataset `{DATASET_NAME}`. "
            "Run `scripts/upload_dataset_to_langsmith.py` first."
        )

    today = date.today()
    agent = ReturnPolicyAgent(
        build_default_retriever(str(ROOT / "policy_docs")),
        today=today,
    )

    records = [run_example(agent, example, today) for example in examples]
    summary = summarize(records)
    failures = [record for record in records if record["failed_metrics"]]
    write_outputs(summary, failures)
    print_summary(summary)
    print(f"\nFailures: {FAILURES_PATH}")
    print(f"Summary:  {SUMMARY_PATH}")
    return summary


def run_example(agent: ReturnPolicyAgent, example: Any, today: date) -> Dict[str, Any]:
    inputs = getattr(example, "inputs", {}) or {}
    expected = getattr(example, "outputs", {}) or {}
    metadata = getattr(example, "metadata", {}) or {}
    payload = {
        "customer_message": inputs["customer_message"],
        "order_context": adapt_order_context(inputs["order_context"], today),
    }

    start = time.perf_counter()
    result = run_traced_agent(
        agent,
        payload,
        metadata={
            "dataset": DATASET_NAME,
            "case_id": metadata.get("id"),
            "scenario_type": metadata.get("scenario_type"),
            "difficulty": metadata.get("difficulty"),
        },
    )
    measured_latency = time.perf_counter() - start
    trace = agent.last_trace.to_dict() if agent.last_trace else {}
    prediction = {
        **result,
        "retrieved_chunks": trace.get("retrieved_chunks", []),
        "trace": trace,
    }
    metrics = local_metric_scores(prediction, expected)
    metrics["faithfulness_llm_judge"] = faithfulness_score(prediction, expected, inputs)
    failed_metrics = {
        key: value
        for key, value in metrics.items()
        if value is not None and value < 1.0
    }

    return {
        "id": metadata.get("id"),
        "scenario_type": metadata.get("scenario_type"),
        "difficulty": metadata.get("difficulty"),
        "inputs": inputs,
        "expected": expected,
        "prediction": result,
        "retrieved_chunks": trace.get("retrieved_chunks", []),
        "metrics": metrics,
        "failed_metrics": failed_metrics,
        "latency_seconds": float(trace.get("latency") or measured_latency),
    }


def faithfulness_score(
    prediction: Dict[str, Any],
    expected: Dict[str, Any],
    inputs: Dict[str, Any],
) -> Optional[float]:
    try:
        judged = faithfulness_llm_judge(
            {"outputs": prediction},
            {"inputs": inputs, "outputs": expected},
        )
        return float(judged.get("score", 0.0))
    except Exception:
        return deterministic_faithfulness_score(prediction)


def summarize(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    metric_names = [
        "decision_accuracy",
        "reason_code_accuracy",
        "missing_info_f1",
        "escalation_accuracy",
        "citation_coverage",
        "policy_section_recall",
        "schema_validity",
        "faithfulness_llm_judge",
    ]
    summary = {}
    for metric in metric_names:
        values = [
            record["metrics"][metric]
            for record in records
            if record["metrics"].get(metric) is not None
        ]
        summary[metric] = mean(values) if values else None
    summary["average_latency_seconds"] = (
        mean(record["latency_seconds"] for record in records) if records else 0.0
    )
    summary["case_count"] = len(records)
    summary["failure_count"] = sum(1 for record in records if record["failed_metrics"])
    return summary


def write_outputs(summary: Dict[str, Any], failures: List[Dict[str, Any]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with FAILURES_PATH.open("w", encoding="utf-8") as handle:
        for failure in failures:
            handle.write(json.dumps(failure, sort_keys=True) + "\n")


def print_summary(summary: Dict[str, Any]) -> None:
    print("LangSmith Baseline Eval Results")
    print("-------------------------------")
    for key, value in summary.items():
        if isinstance(value, float):
            if key.endswith("seconds"):
                print(f"{key:24} {value:.4f}")
            else:
                print(f"{key:24} {value:.2%}")
        else:
            print(f"{key:24} {value}")


def main() -> None:
    try:
        run_langsmith_eval()
    except RuntimeError as exc:
        print(f"LangSmith setup error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
