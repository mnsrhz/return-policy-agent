from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from return_agent.langsmith_tracing import load_env_file, require_langsmith


DATASET_NAME = "return-policy-golden-v1"
DATASET_PATH = ROOT / "data" / "golden_dataset.jsonl"


def load_cases(path: Path = DATASET_PATH) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def difficulty_for(case: Dict[str, Any]) -> str:
    return {
        "happy_path": "easy",
        "edge_case": "medium",
        "known_failure": "hard",
        "adversarial": "hard",
    }.get(case["scenario_type"], "medium")


def expected_outputs(case: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "expected_decision": case["expected_decision"],
        "expected_reason_code": case["expected_reason_code"],
        "expected_missing_info": case["expected_missing_info"],
        "expected_escalate": case["expected_escalate"],
        "expected_policy_sections": case["expected_policy_sections"],
        "expected_answer_traits": case["expected_answer_traits"],
    }


def upload_dataset() -> None:
    load_env_file()
    require_langsmith()
    from langsmith import Client

    client = Client()
    cases = load_cases()
    dataset = _get_or_create_dataset(client)
    existing_ids = _existing_example_ids(client, dataset)
    uploaded = 0
    skipped = 0

    for case in cases:
        if case["id"] in existing_ids:
            skipped += 1
            continue
        client.create_example(
            dataset_id=dataset.id,
            inputs={
                "customer_message": case["customer_message"],
                "order_context": case["order_context"],
            },
            outputs=expected_outputs(case),
            metadata={
                "id": case["id"],
                "scenario_type": case["scenario_type"],
                "difficulty": difficulty_for(case),
                "expected_decision": case["expected_decision"],
                "expected_reason_code": case["expected_reason_code"],
            },
        )
        uploaded += 1

    print(f"Dataset: {DATASET_NAME}")
    print(f"Total local cases: {len(cases)}")
    print(f"Uploaded: {uploaded}")
    print(f"Skipped existing: {skipped}")


def _get_or_create_dataset(client: Any) -> Any:
    try:
        return client.read_dataset(dataset_name=DATASET_NAME)
    except Exception:
        return client.create_dataset(
            dataset_name=DATASET_NAME,
            description="Golden dataset for the Northstar Commerce Return Policy Agent.",
        )


def _existing_example_ids(client: Any, dataset: Any) -> set[str]:
    try:
        examples = client.list_examples(dataset_id=dataset.id)
        return {
            str((getattr(example, "metadata", None) or {}).get("id"))
            for example in examples
            if (getattr(example, "metadata", None) or {}).get("id")
        }
    except Exception:
        return set()


def main() -> None:
    try:
        upload_dataset()
    except RuntimeError as exc:
        print(f"LangSmith setup error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
