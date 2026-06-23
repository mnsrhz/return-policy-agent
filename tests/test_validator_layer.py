from return_agent.models import AgentDecision, IntentExtraction, OrderContext, SafetyCheckResult
from return_agent.retriever import build_default_retriever
from return_agent.validator import validate_and_correct_decision


def get_chunk(policy_id):
    return [
        chunk
        for chunk in build_default_retriever("policy_docs").chunks
        if chunk.policy_id == policy_id
    ]


def validate(decision, *, extracted=None, safety=None, order_context=None, chunks=None):
    return validate_and_correct_decision(
        decision=decision,
        extracted=extracted or IntentExtraction(intent="return_request", confidence=0.9),
        safety=safety or SafetyCheckResult(),
        order_context=order_context
        or OrderContext(
            delivery_date="2026-06-10",
            item_condition="unused, original packaging",
            proof_of_purchase="order NC-1",
        ),
        retrieved_chunks=chunks or get_chunk("POLICY:STANDARD_RETURN_WINDOW"),
    )


def test_empty_citations_are_blocked():
    decision = AgentDecision(
        decision="eligible_return",
        reason_code="standard_30_day",
        policy_sections_used=["POLICY:STANDARD_RETURN_WINDOW"],
        citations=[],
        confidence=0.9,
    )

    corrected, result = validate(decision)

    assert result.valid is False
    assert "citations_missing" in result.errors
    assert corrected.decision == "escalate"


def test_escalate_flag_normalizes_decision_to_escalate():
    decision = AgentDecision(
        decision="eligible_return",
        reason_code="standard_30_day",
        escalate=True,
        policy_sections_used=["POLICY:STANDARD_RETURN_WINDOW"],
        citations=["01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]"],
        confidence=0.9,
    )

    corrected, result = validate(decision)

    assert corrected.decision == "escalate"
    assert result.corrected is True


def test_missing_info_normalizes_decision_to_ask_for_info():
    decision = AgentDecision(
        decision="eligible_return",
        reason_code="standard_30_day",
        missing_info=["delivery_date"],
        policy_sections_used=["POLICY:STANDARD_RETURN_WINDOW"],
        citations=["01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]"],
        confidence=0.9,
    )

    corrected, result = validate(decision)

    assert corrected.decision == "ask_for_info"
    assert result.corrected is True


def test_low_confidence_decision_is_downgraded():
    decision = AgentDecision(
        decision="eligible_return",
        reason_code="standard_30_day",
        policy_sections_used=["POLICY:STANDARD_RETURN_WINDOW"],
        citations=["01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]"],
        confidence=0.4,
    )

    corrected, result = validate(decision)

    assert corrected.decision == "ask_for_info"
    assert result.corrected is True


def test_final_sale_cannot_be_marked_eligible_without_damage_exception():
    decision = AgentDecision(
        decision="eligible_return",
        reason_code="standard_30_day",
        policy_sections_used=["POLICY:FINAL_SALE_NO_RETURNS"],
        citations=["02_final_sale_and_exceptions.md [POLICY:FINAL_SALE_NO_RETURNS]"],
        confidence=0.9,
    )

    corrected, result = validate(
        decision,
        order_context=OrderContext(
            delivery_date="2026-06-10",
            item_condition="unused",
            final_sale=True,
            proof_of_purchase="order NC-2",
        ),
        chunks=get_chunk("POLICY:FINAL_SALE_NO_RETURNS"),
    )

    assert corrected.decision == "not_eligible"
    assert corrected.reason_code == "final_sale"
    assert result.corrected is True


def test_final_sale_denial_is_valid_even_when_other_info_is_missing():
    decision = AgentDecision(
        decision="not_eligible",
        reason_code="final_sale",
        missing_info=["delivery_date", "item_condition"],
        policy_sections_used=["POLICY:FINAL_SALE_NO_RETURNS"],
        citations=["02_final_sale_and_exceptions.md [POLICY:FINAL_SALE_NO_RETURNS]"],
        confidence=0.9,
    )

    corrected, result = validate(
        decision,
        order_context=OrderContext(final_sale=True),
        chunks=get_chunk("POLICY:FINAL_SALE_NO_RETURNS"),
    )

    assert result.valid is True
    assert corrected.decision == "not_eligible"
    assert corrected.reason_code == "final_sale"
    assert corrected.missing_info == []
