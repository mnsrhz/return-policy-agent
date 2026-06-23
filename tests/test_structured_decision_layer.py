from return_agent.decision_agent import DeterministicPolicyDecisionAgent
from return_agent.guardrails import safety_precheck
from return_agent.intent_extractor import DeterministicIntentExtractor
from return_agent.retriever import build_default_retriever


def decide(customer_message, order_context):
    retriever = build_default_retriever("policy_docs")
    extracted = DeterministicIntentExtractor().extract(
        {"customer_message": customer_message, "order_context": order_context}
    )
    safety = safety_precheck(
        customer_message=customer_message,
        extracted=extracted,
        order_context=order_context,
    )
    query = " ".join(
        str(part)
        for part in [
            customer_message,
            extracted.intent,
            extracted.requested_resolution,
            order_context.get("item_category"),
            order_context.get("item_condition"),
            order_context.get("proof_of_purchase"),
        ]
        if part
    )
    retrieved = retriever.retrieve(query, top_k=12)
    return DeterministicPolicyDecisionAgent().decide(
        customer_message=customer_message,
        order_context=order_context,
        extracted=extracted,
        safety=safety,
        retrieved_chunks=retrieved,
        corpus_chunks=retriever.chunks,
    )


def test_decision_eligible_return_within_30_days():
    result = decide(
        "Can I return this jacket?",
        {
            "delivery_date": "2026-06-10",
            "item_condition": "unused, original packaging",
            "proof_of_purchase": "order NC-1",
        },
    )

    assert result.decision == "eligible_return"
    assert result.reason_code == "standard_30_day"


def test_decision_not_eligible_final_sale():
    result = decide(
        "Can I return this final sale item?",
        {
            "delivery_date": "2026-06-10",
            "item_condition": "unused",
            "final_sale": True,
            "proof_of_purchase": "order NC-2",
        },
    )

    assert result.decision == "not_eligible"
    assert result.reason_code == "final_sale"


def test_decision_asks_for_info_when_delivery_date_missing():
    result = decide(
        "Can I return this jacket?",
        {"item_condition": "unused", "proof_of_purchase": "order NC-3"},
    )

    assert result.decision == "ask_for_info"
    assert "delivery_date" in result.missing_info


def test_decision_escalates_legal_threat():
    result = decide(
        "I will sue you if you do not refund me.",
        {
            "delivery_date": "2026-06-10",
            "item_condition": "unused",
            "proof_of_purchase": "order NC-4",
        },
    )

    assert result.decision == "escalate"
    assert result.reason_code == "legal_threat"


def test_decision_escalates_policy_exception_request():
    result = decide(
        "Can you make an exception and approve my late return?",
        {
            "delivery_date": "2026-04-05",
            "item_condition": "unused",
            "proof_of_purchase": "order NC-5",
        },
    )

    assert result.decision == "escalate"
    assert result.reason_code == "exception_request"


def test_decision_eligible_exchange_within_30_days():
    result = decide(
        "Can I exchange this shirt for a different color?",
        {
            "delivery_date": "2026-06-10",
            "item_condition": "unused, original packaging",
            "proof_of_purchase": "order NC-6",
        },
    )

    assert result.decision == "eligible_exchange"
    assert result.reason_code == "standard_30_day"


def test_decision_shipping_fee_not_refunded_for_wrong_size():
    result = decide(
        "I ordered the wrong size. Will return shipping be refunded?",
        {
            "delivery_date": "2026-06-10",
            "item_condition": "unused, original packaging",
            "proof_of_purchase": "order NC-7",
        },
    )

    assert result.decision == "not_eligible"
    assert result.reason_code == "shipping_fee"
