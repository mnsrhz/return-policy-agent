from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from return_agent.agent import ReturnPolicyAgent
from return_agent.evaluators import (
    decision_accuracy,
    escalation_accuracy,
    missing_info_f1,
    reason_code_accuracy,
)


def load_cases(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def run_smoke_tests(cases_path: Path = ROOT / "data" / "sample_cases.jsonl") -> Dict[str, float]:
    cases = load_cases(cases_path)
    agent = ReturnPolicyAgent.from_policy_dir(str(ROOT / "policy_docs"))

    decision_scores = []
    reason_scores = []
    missing_scores = []
    escalation_scores = []

    for case in cases:
        prediction = agent.run(
            {
                "customer_message": case["customer_message"],
                "order_context": case["order_context"],
            }
        )
        decision_scores.append(decision_accuracy(prediction, case))
        reason_scores.append(reason_code_accuracy(prediction, case))
        missing_scores.append(missing_info_f1(prediction, case))
        escalation_scores.append(escalation_accuracy(prediction, case))

    return {
        "decision_accuracy": mean(decision_scores) if decision_scores else 0.0,
        "reason_code_accuracy": mean(reason_scores) if reason_scores else 0.0,
        "missing_info_match": mean(missing_scores) if missing_scores else 0.0,
        "escalation_accuracy": mean(escalation_scores) if escalation_scores else 0.0,
    }


def main() -> None:
    metrics = run_smoke_tests()
    print("Return Policy Agent Smoke Test Results")
    print("--------------------------------------")
    print(f"Decision accuracy:     {metrics['decision_accuracy']:.2%}")
    print(f"Reason code accuracy:  {metrics['reason_code_accuracy']:.2%}")
    print(f"Missing info match:    {metrics['missing_info_match']:.2%}")
    print(f"Escalation accuracy:   {metrics['escalation_accuracy']:.2%}")


if __name__ == "__main__":
    main()
