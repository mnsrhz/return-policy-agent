from __future__ import annotations

import json
import sys
import time
import argparse
from datetime import date, timedelta
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from return_agent.agent import ReturnPolicyAgent
from return_agent.evaluators import (
    citation_coverage,
    decision_accuracy,
    escalation_accuracy,
    missing_info_f1,
    policy_section_recall,
    reason_code_accuracy,
    schema_validity,
)
from return_agent.retriever import build_default_retriever


DATASET_PATH = ROOT / "data" / "golden_dataset.jsonl"
OUTPUT_DIR = ROOT / "eval_runs"
PREDICTIONS_PATH = OUTPUT_DIR / "local_baseline_predictions.jsonl"
SUMMARY_PATH = OUTPUT_DIR / "local_baseline_summary.json"


def load_cases(path: Path = DATASET_PATH) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def adapt_order_context(context: Dict[str, Any], today: date) -> Dict[str, Any]:
    days_since_delivery = context.get("days_since_delivery")
    delivery_date = None
    if days_since_delivery is not None:
        delivery_date = (today - timedelta(days=int(days_since_delivery))).isoformat()

    return {
        "order_date": None,
        "delivery_date": delivery_date,
        "item_category": context.get("item_category"),
        "item_condition": context.get("item_condition"),
        "final_sale": context.get("final_sale"),
        "order_value": context.get("order_value"),
        "proof_of_purchase": context.get("proof_of_purchase"),
        "order_number": context.get("order_number"),
    }


def run_case(agent: ReturnPolicyAgent, case: Dict[str, Any], today: date) -> Dict[str, Any]:
    payload = {
        "customer_message": case["customer_message"],
        "order_context": adapt_order_context(case["order_context"], today),
    }
    start = time.perf_counter()
    result = agent.run(payload)
    measured_latency = time.perf_counter() - start
    trace = agent.last_trace.to_dict() if agent.last_trace else {}

    prediction = {
        **result,
        "retrieved_chunks": trace.get("retrieved_chunks", []),
        "trace": trace,
    }
    metrics = score_prediction(prediction, case)
    latency = float(trace.get("latency") or measured_latency)

    return {
        "id": case["id"],
        "scenario_type": case["scenario_type"],
        "customer_message": case["customer_message"],
        "input": payload,
        "expected": {
            "decision": case["expected_decision"],
            "reason_code": case["expected_reason_code"],
            "missing_info": case["expected_missing_info"],
            "escalate": case["expected_escalate"],
            "policy_sections": case["expected_policy_sections"],
        },
        "prediction": result,
        "retrieved_chunks": trace.get("retrieved_chunks", []),
        "trace": trace,
        "metrics": metrics,
        "latency_seconds": latency,
    }


def score_prediction(prediction: Dict[str, Any], case: Dict[str, Any]) -> Dict[str, float]:
    return {
        "decision_accuracy": decision_accuracy(prediction, case),
        "reason_code_accuracy": reason_code_accuracy(prediction, case),
        "missing_info_f1": missing_info_f1(prediction, case),
        "escalation_accuracy": escalation_accuracy(prediction, case),
        "citation_coverage": citation_coverage(prediction, case),
        "policy_section_recall": policy_section_recall(prediction, case),
        "schema_validity": schema_validity(prediction),
    }


def summarize(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    metric_names = [
        "decision_accuracy",
        "reason_code_accuracy",
        "missing_info_f1",
        "escalation_accuracy",
        "citation_coverage",
        "policy_section_recall",
        "schema_validity",
    ]
    summary = {
        metric: mean(record["metrics"][metric] for record in records) if records else 0.0
        for metric in metric_names
    }
    summary["average_latency_seconds"] = (
        mean(record["latency_seconds"] for record in records) if records else 0.0
    )
    summary["case_count"] = len(records)
    return summary


def write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def print_metric_table(summary: Dict[str, Any]) -> None:
    print("Local Eval Results")
    print("------------------")
    for metric in [
        "decision_accuracy",
        "reason_code_accuracy",
        "missing_info_f1",
        "escalation_accuracy",
        "citation_coverage",
        "policy_section_recall",
        "schema_validity",
    ]:
        print(f"{metric:24} {summary[metric]:.2%}")
    print(f"{'average_latency_seconds':24} {summary['average_latency_seconds']:.4f}")
    print(f"{'case_count':24} {summary['case_count']}")


def run_local_eval(
    dataset_path: Path = DATASET_PATH,
    predictions_path: Path = PREDICTIONS_PATH,
    summary_path: Path = SUMMARY_PATH,
) -> Dict[str, Any]:
    today = date.today()
    cases = load_cases(dataset_path)
    agent = ReturnPolicyAgent(
        build_default_retriever(str(ROOT / "policy_docs")),
        today=today,
    )
    records = [run_case(agent, case, today) for case in cases]
    summary = summarize(records)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(predictions_path, records)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print_metric_table(summary)
    print(f"\nPredictions: {predictions_path}")
    print(f"Summary:     {summary_path}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local Return Policy Agent eval.")
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--predictions", type=Path, default=PREDICTIONS_PATH)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    args = parser.parse_args()
    run_local_eval(args.dataset, args.predictions, args.summary)


if __name__ == "__main__":
    main()
