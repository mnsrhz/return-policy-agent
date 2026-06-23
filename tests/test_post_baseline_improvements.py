from datetime import date, timedelta

from return_agent.agent import ReturnPolicyAgent
from return_agent.retriever import build_default_retriever


TODAY = date(2026, 6, 23)


def make_agent():
    return ReturnPolicyAgent(
        build_default_retriever("policy_docs"),
        today=TODAY,
    )


def context(*, days=10, condition="unused, original packaging", proof="receipt", order="NC-1", **overrides):
    data = {
        "delivery_date": (TODAY - timedelta(days=days)).isoformat() if days is not None else None,
        "item_condition": condition,
        "final_sale": False,
        "proof_of_purchase": proof,
        "order_number": order,
        "order_value": 75,
        "item_category": "item",
    }
    data.update(overrides)
    return data


def run(message, order_context):
    return make_agent().run({"customer_message": message, "order_context": order_context})


def test_changed_mind_shipping_fee_is_not_refunded_without_asking_for_reason():
    result = run(
        "If I return an eligible dress because I changed my mind, will Northstar refund return shipping?",
        context(item_category="dress"),
    )

    assert result["decision"] == "not_eligible"
    assert result["reason_code"] == "shipping_fee"
    assert result["missing_info"] == []
    assert result["escalate"] is False


def test_wrong_size_customer_return_is_standard_return_not_wrong_item_escalation():
    result = run(
        "I ordered the wrong size shirt. It is unworn. Can I return it?",
        context(condition="unused, unworn, unwashed, original packaging", item_category="shirt"),
    )

    assert result["decision"] == "eligible_return"
    assert result["reason_code"] == "standard_30_day"
    assert result["escalate"] is False
    assert "POLICY:STANDARD_RETURN_REASON" in result["policy_sections_used"]


def test_outside_return_window_is_not_eligible_with_outside_window_reason():
    result = run(
        "I received this jacket 31 days ago. Can I return it? It is unused.",
        context(days=31, condition="unused, original packaging", item_category="jacket"),
    )

    assert result["decision"] == "not_eligible"
    assert result["reason_code"] == "outside_return_window"
    assert result["missing_info"] == []


def test_missing_order_number_is_requested_when_message_says_no_order_number():
    result = run(
        "Can I return this unused item? I do not have the order number handy.",
        context(proof="receipt", order=None),
    )

    assert result["decision"] == "ask_for_info"
    assert result["reason_code"] == "missing_order_number"
    assert result["missing_info"] == ["order_number"]


def test_personalized_wrong_size_is_final_sale_denial_not_wrong_item():
    result = run(
        "Can I return a personalized hoodie because I chose the wrong size?",
        context(item_category="personalized hoodie"),
    )

    assert result["decision"] == "not_eligible"
    assert result["reason_code"] == "final_sale"
    assert result["escalate"] is False
    assert "POLICY:PERSONALIZED_CUSTOM_ITEMS" in result["policy_sections_used"]


def test_mixed_item_eligibility_asks_for_item_level_facts():
    result = run(
        "I have two items: one unused regular sweater and one final sale bag. Can I return both?",
        context(final_sale=None, item_category="mixed items"),
    )

    assert result["decision"] == "ask_for_info"
    assert result["reason_code"] == "unclear"
    assert set(result["missing_info"]) == {"item_level_final_sale_status", "item_level_condition"}


def test_high_value_missing_proof_escalates_with_missing_info_and_reason():
    result = run(
        "I want a refund for a $750 watch, but I lost the receipt and do not have the order number.",
        context(proof=None, order=None, order_value=750, item_category="watch"),
    )

    assert result["decision"] == "escalate"
    assert result["reason_code"] == "no_proof_of_purchase"
    assert set(result["missing_info"]) == {"proof_of_purchase", "order_number"}


def test_damaged_item_without_photo_or_order_number_asks_for_required_info_first():
    result = run(
        "My mirror arrived damaged, but I do not have photos and cannot find my order number.",
        context(proof=None, order=None, item_category="mirror", condition="damaged on arrival"),
    )

    assert result["decision"] == "ask_for_info"
    assert result["reason_code"] == "damaged_item"
    assert set(result["missing_info"]) == {"order_number", "proof_of_purchase", "photo_or_description"}
