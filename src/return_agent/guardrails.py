from __future__ import annotations

from typing import Any, Dict, Optional

from return_agent.models import IntentExtraction, SafetyCheckResult
from return_agent.utils import contains_any


def safety_precheck(
    *,
    customer_message: str,
    extracted: Optional[IntentExtraction],
    order_context: Dict[str, Any],
) -> SafetyCheckResult:
    text = customer_message.lower()
    risk_flags = []

    if contains_any(text, ["ignore the policy", "ignore policy", "bypass policy", "override policy", "forget the rules"]):
        risk_flags.append("prompt_injection_or_policy_override")
        return SafetyCheckResult(
            escalate=True,
            refuse=True,
            reason_code="exception_request",
            risk_flags=risk_flags,
            message="The customer asked the agent to ignore or override policy.",
        )

    if contains_any(text, ["sue", "lawsuit", "lawyer", "attorney", "legal rights", "illegal", "regulator"]):
        risk_flags.append("legal_threat")
        return SafetyCheckResult(
            escalate=True,
            reason_code="legal_threat",
            risk_flags=risk_flags,
            message="Legal threats or legal claims require human support review.",
        )

    if contains_any(text, ["fraud", "scam", "chargeback", "fake receipt", "altered receipt"]):
        risk_flags.append("fraud_concern")
        return SafetyCheckResult(
            escalate=True,
            reason_code="fraud_concern",
            risk_flags=risk_flags,
            message="Fraud or chargeback concerns require human support review.",
        )

    if contains_any(text, ["idiot", "stupid", "threat", "hurt you", "kill"]):
        risk_flags.append("abusive_or_threatening_language")
        return SafetyCheckResult(
            escalate=True,
            reason_code="unclear",
            risk_flags=risk_flags,
            message="Abusive or threatening language requires human support review.",
        )

    if contains_any(text, ["exception", "override", "special approval", "late return"]):
        risk_flags.append("policy_exception_request")
        return SafetyCheckResult(
            escalate=True,
            reason_code="exception_request",
            risk_flags=risk_flags,
            message="Policy exception requests require human support review.",
        )

    order_value = order_context.get("order_value")
    proof = order_context.get("proof_of_purchase") or order_context.get("order_number")
    if order_value is not None and float(order_value) > 500 and contains_any(text, ["refund", "return"]):
        risk_flags.append("high_value_refund")
        if not proof:
            risk_flags.append("high_value_missing_proof")
        return SafetyCheckResult(
            escalate=True,
            reason_code="no_proof_of_purchase" if not proof else "unclear",
            risk_flags=risk_flags,
            message="High-value refund requests over $500 require human support review.",
        )

    return SafetyCheckResult(escalate=False, risk_flags=risk_flags)
