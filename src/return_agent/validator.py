from __future__ import annotations

from typing import List

from return_agent.citations import validate_citations
from return_agent.models import AgentDecision, DecisionValidationResult, IntentExtraction, OrderContext, PolicyChunk, SafetyCheckResult


def validate_and_correct_decision(
    *,
    decision: AgentDecision,
    extracted: IntentExtraction,
    safety: SafetyCheckResult,
    order_context: OrderContext,
    retrieved_chunks: List[PolicyChunk],
) -> tuple[AgentDecision, DecisionValidationResult]:
    errors: List[str] = []
    corrected = False
    retrieved_policy_ids = {chunk.policy_id for chunk in retrieved_chunks}
    citation_by_policy_id = {
        chunk.policy_id: chunk.source_citation for chunk in retrieved_chunks
    }

    canonical_citations = [
        citation_by_policy_id[policy_id]
        for policy_id in decision.policy_sections_used
        if policy_id in citation_by_policy_id
    ]
    if decision.citations and canonical_citations and decision.citations != canonical_citations:
        decision = decision.model_copy(update={"citations": canonical_citations})
        corrected = True

    citation_result = validate_citations(decision, retrieved_chunks)
    if not citation_result.valid:
        errors.extend(citation_result.errors)

    if safety.escalate and decision.decision != "escalate":
        errors.append("safety_escalation_not_honored")
        decision = decision.model_copy(
            update={
                "decision": "escalate",
                "escalate": True,
                "reason_code": safety.reason_code or "unclear",
            }
        )
        corrected = True

    if decision.escalate and decision.decision != "escalate":
        errors.append("escalate_flag_decision_mismatch")
        decision = decision.model_copy(update={"decision": "escalate"})
        corrected = True

    has_damage_exception = extracted.intent in {"damaged_item", "wrong_item", "missing_item"}
    final_sale = order_context.final_sale is True or extracted.extracted_facts.final_sale is True
    if final_sale and not has_damage_exception and decision.decision not in {"not_eligible", "escalate"}:
        errors.append("final_sale_blocks_eligible_or_incomplete_decision")
        decision = decision.model_copy(
            update={
                "decision": "not_eligible",
                "reason_code": "final_sale",
                "missing_info": [],
                "escalate": False,
            }
        )
        corrected = True
    elif final_sale and not has_damage_exception and decision.reason_code == "final_sale" and decision.missing_info:
        decision = decision.model_copy(update={"missing_info": []})
        corrected = True

    if decision.missing_info and decision.decision not in {"ask_for_info", "escalate"}:
        errors.append("missing_info_requires_ask_or_escalate")
        decision = decision.model_copy(update={"decision": "ask_for_info"})
        corrected = True

    if decision.confidence < 0.70 and decision.decision not in {"ask_for_info", "escalate"}:
        errors.append("low_confidence_requires_ask_or_escalate")
        decision = decision.model_copy(update={"decision": "ask_for_info"})
        corrected = True

    for policy_id in decision.policy_sections_used:
        if policy_id not in retrieved_policy_ids:
            errors.append(f"policy_section_not_in_retrieved_chunks: {policy_id}")

    if errors and not corrected:
        decision = decision.model_copy(
            update={
                "decision": "escalate",
                "reason_code": "unclear",
                "escalate": True,
                "confidence": 0.0,
                "customer_answer": "This needs support review because the policy evidence or decision validation did not pass.",
            }
        )
        corrected = True

    return decision, DecisionValidationResult(valid=not errors, errors=errors, corrected=corrected)
