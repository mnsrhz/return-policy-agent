from return_agent.agent import ReturnPolicyAgent


def make_agent():
    return ReturnPolicyAgent.from_policy_dir("policy_docs")


def test_standard_eligible_return():
    agent = make_agent()

    result = agent.run(
        {
            "customer_message": "Can I return this jacket? It is unused and still in the original packaging.",
            "order_context": {
                "order_date": "2026-06-01",
                "delivery_date": "2026-06-10",
                "item_category": "jacket",
                "item_condition": "unused, unworn, unwashed, original packaging",
                "final_sale": False,
                "order_value": 120,
                "proof_of_purchase": "order NC-1001",
            },
        }
    )

    assert result["decision"] == "eligible_return"
    assert result["reason_code"] == "standard_30_day"
    assert result["escalate"] is False
    assert "01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]" in result["citations"]


def test_final_sale_not_eligible_without_damage_issue():
    agent = make_agent()

    result = agent.run(
        {
            "customer_message": "I changed my mind. Can I return this final sale bag?",
            "order_context": {
                "order_date": "2026-06-01",
                "delivery_date": "2026-06-05",
                "item_category": "handbag",
                "item_condition": "unused",
                "final_sale": True,
                "order_value": 80,
                "proof_of_purchase": "order NC-1002",
            },
        }
    )

    assert result["decision"] == "not_eligible"
    assert result["reason_code"] == "final_sale"
    assert result["escalate"] is False
    assert "02_final_sale_and_exceptions.md [POLICY:FINAL_SALE_NO_RETURNS]" in result["citations"]


def test_damaged_item_escalates_for_support_review():
    agent = make_agent()

    result = agent.run(
        {
            "customer_message": "My vase arrived damaged and cracked. I have photos.",
            "order_context": {
                "order_date": "2026-06-01",
                "delivery_date": "2026-06-08",
                "item_category": "vase",
                "item_condition": "damaged on arrival",
                "final_sale": False,
                "order_value": 75,
                "proof_of_purchase": "order NC-1003",
            },
        }
    )

    assert result["decision"] == "escalate"
    assert result["reason_code"] == "damaged_item"
    assert result["escalate"] is True
    assert any("POLICY:DAMAGE_WRONG_MISSING_REVIEW" in citation for citation in result["citations"])


def test_missing_order_date_asks_for_info():
    agent = make_agent()

    result = agent.run(
        {
            "customer_message": "Can I return this sweater? It is unused.",
            "order_context": {
                "order_date": None,
                "delivery_date": None,
                "item_category": "sweater",
                "item_condition": "unused",
                "final_sale": False,
                "order_value": 60,
                "proof_of_purchase": "order NC-1004",
            },
        }
    )

    assert result["decision"] == "ask_for_info"
    assert result["reason_code"] == "missing_order_number"
    assert "delivery_date" in result["missing_info"]


def test_shipping_fee_not_refunded_for_wrong_size():
    agent = make_agent()

    result = agent.run(
        {
            "customer_message": "I ordered the wrong size. Will return shipping be refunded?",
            "order_context": {
                "order_date": "2026-06-01",
                "delivery_date": "2026-06-03",
                "item_category": "shirt",
                "item_condition": "unused, original packaging",
                "final_sale": False,
                "order_value": 45,
                "proof_of_purchase": "order NC-1005",
            },
        }
    )

    assert result["decision"] == "not_eligible"
    assert result["reason_code"] == "shipping_fee"
    assert "04_refunds_and_shipping_fees.md [POLICY:RETURN_SHIPPING_CUSTOMER_REASONS]" in result["citations"]


def test_gift_return_store_credit():
    agent = make_agent()

    result = agent.run(
        {
            "customer_message": "I have a gift receipt. Can I return this gift for store credit?",
            "order_context": {
                "order_date": "2026-06-01",
                "delivery_date": "2026-06-04",
                "item_category": "scarf",
                "item_condition": "unused, original packaging",
                "final_sale": False,
                "order_value": 55,
                "proof_of_purchase": "gift receipt",
            },
        }
    )

    assert result["decision"] == "eligible_return"
    assert result["reason_code"] == "gift_return"
    assert "05_gifts_exchanges_and_store_credit.md [POLICY:GIFT_REFUND_STORE_CREDIT]" in result["citations"]


def test_policy_exception_escalation():
    agent = make_agent()

    result = agent.run(
        {
            "customer_message": "Can you make an exception and approve my late return?",
            "order_context": {
                "order_date": "2026-04-01",
                "delivery_date": "2026-04-05",
                "item_category": "shoes",
                "item_condition": "unused",
                "final_sale": False,
                "order_value": 90,
                "proof_of_purchase": "order NC-1006",
            },
        }
    )

    assert result["decision"] == "escalate"
    assert result["reason_code"] == "exception_request"
    assert result["escalate"] is True
    assert "06_escalation_rules.md [POLICY:ESCALATION_POLICY_EXCEPTIONS]" in result["citations"]


def test_agent_records_trace_for_eval_readiness():
    agent = make_agent()

    result = agent.run(
        {
            "customer_message": "Can I return this jacket? It is unused and in the original packaging.",
            "order_context": {
                "order_date": "2026-06-01",
                "delivery_date": "2026-06-10",
                "item_category": "jacket",
                "item_condition": "unused, original packaging",
                "final_sale": False,
                "order_value": 120,
                "proof_of_purchase": "order NC-1007",
            },
        }
    )

    trace = agent.last_trace.to_dict()
    assert trace["input"]["customer_message"].startswith("Can I return")
    assert trace["retrieved_chunks"]
    assert trace["decision"] == result["decision"]
    assert trace["citations"] == result["citations"]
    assert trace["missing_info"] == result["missing_info"]
    assert isinstance(trace["latency"], float)
    assert trace["errors"] == []
