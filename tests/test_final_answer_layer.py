from return_agent.answer_generator import DeterministicAnswerGenerator
from return_agent.models import AgentDecision
from return_agent.retriever import build_default_retriever


def generate(decision):
    chunks = build_default_retriever("policy_docs").chunks[:2]
    return DeterministicAnswerGenerator().generate(
        customer_message="Can I return this?",
        decision=decision,
        retrieved_chunks=chunks,
    )


def test_final_answer_includes_citations():
    answer = generate(
        AgentDecision(
            decision="eligible_return",
            reason_code="standard_30_day",
            citations=["01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]"],
            customer_answer="Eligible return. See 01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW].",
        )
    )

    assert "01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]" in answer


def test_final_answer_does_not_invent_policy():
    answer = generate(
        AgentDecision(
            decision="not_eligible",
            reason_code="final_sale",
            citations=["02_final_sale_and_exceptions.md [POLICY:FINAL_SALE_NO_RETURNS]"],
            customer_answer="Final sale items cannot be returned or exchanged.",
        )
    )

    assert "manager coupon" not in answer.lower()
    assert "one-time courtesy refund" not in answer.lower()


def test_final_answer_does_not_promise_refund_approval():
    answer = generate(
        AgentDecision(
            decision="escalate",
            reason_code="damaged_item",
            escalate=True,
            citations=["03_damaged_wrong_missing_items.md [POLICY:DAMAGE_WRONG_MISSING_REVIEW]"],
            customer_answer="This requires support review before approving a refund or replacement.",
        )
    )

    assert "refund approved" not in answer.lower()
    assert "has been refunded" not in answer.lower()


def test_ask_for_info_answer_asks_for_required_missing_fields():
    answer = generate(
        AgentDecision(
            decision="ask_for_info",
            reason_code="missing_order_number",
            missing_info=["delivery_date", "proof_of_purchase"],
            citations=["01_standard_returns.md [POLICY:PROOF_OF_PURCHASE_REQUIRED]"],
            customer_answer="Please provide the delivery date and proof of purchase.",
        )
    )

    assert "delivery date" in answer.lower()
    assert "proof of purchase" in answer.lower()


def test_escalation_answer_routes_to_support_review():
    answer = generate(
        AgentDecision(
            decision="escalate",
            reason_code="legal_threat",
            escalate=True,
            citations=["06_escalation_rules.md [POLICY:ESCALATION_LEGAL_THREATS]"],
            customer_answer="This needs support review.",
        )
    )

    assert "support review" in answer.lower()
