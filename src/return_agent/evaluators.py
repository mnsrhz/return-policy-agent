from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Set


def decision_accuracy(prediction: Dict[str, Any], reference: Dict[str, Any]) -> float:
    return float(prediction.get("decision") == reference.get("expected_decision"))


def reason_code_accuracy(prediction: Dict[str, Any], reference: Dict[str, Any]) -> float:
    return float(prediction.get("reason_code") == reference.get("expected_reason_code"))


def missing_info_f1(prediction: Dict[str, Any], reference: Dict[str, Any]) -> float:
    predicted = _as_set(prediction.get("missing_info", []))
    expected = _as_set(reference.get("expected_missing_info", []))

    if not predicted and not expected:
        return 1.0
    if not predicted or not expected:
        return 0.0

    true_positive = len(predicted & expected)
    precision = true_positive / len(predicted)
    recall = true_positive / len(expected)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def escalation_accuracy(prediction: Dict[str, Any], reference: Dict[str, Any]) -> float:
    return float(bool(prediction.get("escalate")) == bool(reference.get("expected_escalate")))


def citation_present(prediction: Dict[str, Any], reference: Dict[str, Any] | None = None) -> float:
    return float(bool(prediction.get("citations")))


def citation_coverage(prediction: Dict[str, Any], reference: Dict[str, Any] | None = None) -> float:
    citations = [str(citation) for citation in prediction.get("citations") or []]
    if not citations:
        return 0.0

    retrieved_policy_ids = _retrieved_policy_ids(prediction)
    if not retrieved_policy_ids:
        return 0.0

    citation_policy_ids = {
        policy_id
        for citation in citations
        for policy_id in _policy_ids_from_text(citation)
    }
    if not citation_policy_ids:
        return 0.0

    return float(citation_policy_ids.issubset(retrieved_policy_ids))


def policy_section_recall(prediction: Dict[str, Any], reference: Dict[str, Any]) -> float:
    expected = _as_set(reference.get("expected_policy_sections", []))
    predicted = _as_set(prediction.get("policy_sections_used", []))

    if not expected:
        return citation_coverage(prediction, reference)
    if not predicted:
        return 0.0

    return len(predicted & expected) / len(expected)


def schema_validity(prediction: Dict[str, Any]) -> float:
    required_fields = {
        "decision",
        "reason_code",
        "missing_info",
        "escalate",
        "confidence",
        "policy_sections_used",
        "citations",
        "customer_answer",
    }
    if not required_fields.issubset(prediction):
        return 0.0

    list_fields = ("missing_info", "policy_sections_used", "citations")
    if any(not isinstance(prediction.get(field), list) for field in list_fields):
        return 0.0
    if not isinstance(prediction.get("escalate"), bool):
        return 0.0
    if not isinstance(prediction.get("confidence"), (int, float)):
        return 0.0
    if not isinstance(prediction.get("customer_answer"), str):
        return 0.0
    return 1.0


def _as_set(values: Iterable[Any]) -> Set[str]:
    return {_canonical_missing_info(str(value).strip()) for value in values if str(value).strip()}


def _canonical_missing_info(value: str) -> str:
    aliases = {
        "delivery_date": "days_since_delivery",
        "order_number_or_proof_of_purchase": "proof_of_purchase",
        "gift_receipt": "gift_receipt_or_order_number",
    }
    return aliases.get(value, value)


def _retrieved_policy_ids(prediction: Dict[str, Any]) -> Set[str]:
    chunks = prediction.get("retrieved_chunks") or prediction.get("trace", {}).get("retrieved_chunks") or []
    policy_ids: Set[str] = set()
    for chunk in chunks:
        policy_id = str(chunk.get("policy_id", "")).strip()
        if policy_id:
            policy_ids.add(policy_id)
        policy_ids.update(_policy_ids_from_text(str(chunk.get("source_citation", ""))))
    return policy_ids


def _policy_ids_from_text(text: str) -> Set[str]:
    return {f"POLICY:{match}" for match in re.findall(r"\[POLICY:([A-Z0-9_]+)\]", text)}
