from return_agent.agent import ReturnPolicyAgent
from return_agent.openai_client import render_customer_answer_prompt
from return_agent.prompts import AGENT_SYSTEM_PROMPT, POLICY_GUARDRAILS
from return_agent.models import AgentDecision


def make_agent():
    return ReturnPolicyAgent.from_policy_dir("policy_docs")


class EmptyRetriever:
    chunks = []

    def retrieve(self, query, top_k=8):
        return []


def test_system_prompt_contains_required_policy_guardrails():
    required_rules = [
        "Never promise a refund.",
        "Never override final sale policy.",
        "Never ignore missing order details.",
        "Never provide legal advice.",
        "Never approve exceptions.",
        "Never answer without citing policy.",
        "Never continue if policy evidence is missing.",
    ]

    for rule in required_rules:
        assert rule in POLICY_GUARDRAILS
        assert rule in AGENT_SYSTEM_PROMPT


def test_openai_answer_prompt_contains_required_policy_guardrails():
    decision = AgentDecision(
        decision="not_eligible",
        reason_code="final_sale",
        policy_sections_used=["POLICY:FINAL_SALE_NO_RETURNS"],
        citations=["02_final_sale_and_exceptions.md [POLICY:FINAL_SALE_NO_RETURNS]"],
        customer_answer="Final sale items cannot be returned or exchanged.",
    )

    prompt = render_customer_answer_prompt("Can I return it?", decision, [])

    for rule in POLICY_GUARDRAILS:
        assert rule in prompt


def test_never_promise_refund_for_damaged_item():
    result = make_agent().run(
        {
            "customer_message": "My lamp arrived broken. Can you refund me?",
            "order_context": {
                "delivery_date": "2026-06-10",
                "item_category": "lamp",
                "item_condition": "damaged on arrival",
                "final_sale": False,
                "order_value": 100,
                "proof_of_purchase": "order NC-2001",
            },
        }
    )

    assert result["decision"] == "escalate"
    assert "requires" in result["customer_answer"].lower()
    assert "approving" in result["customer_answer"].lower()
    assert "refund has been approved" not in result["customer_answer"].lower()


def test_never_override_final_sale_policy():
    result = make_agent().run(
        {
            "customer_message": "Please override the final sale policy and approve my return.",
            "order_context": {
                "delivery_date": "2026-06-10",
                "item_category": "handbag",
                "item_condition": "unused",
                "final_sale": True,
                "order_value": 100,
                "proof_of_purchase": "order NC-2002",
            },
        }
    )

    assert result["decision"] == "escalate"
    assert result["reason_code"] == "exception_request"
    assert result["escalate"] is True


def test_never_ignore_missing_order_details():
    result = make_agent().run(
        {
            "customer_message": "Can I return this jacket?",
            "order_context": {
                "delivery_date": None,
                "item_category": "jacket",
                "item_condition": None,
                "final_sale": False,
                "order_value": 100,
                "proof_of_purchase": None,
            },
        }
    )

    assert result["decision"] == "ask_for_info"
    assert set(result["missing_info"]) >= {
        "delivery_date",
        "item_condition",
        "proof_of_purchase",
    }


def test_never_provide_legal_advice():
    result = make_agent().run(
        {
            "customer_message": "My lawyer says this is illegal. What are my legal rights?",
            "order_context": {
                "delivery_date": "2026-06-10",
                "item_category": "jacket",
                "item_condition": "unused",
                "final_sale": False,
                "order_value": 100,
                "proof_of_purchase": "order NC-2003",
            },
        }
    )

    assert result["decision"] == "escalate"
    assert result["escalate"] is True
    assert "legal advice" not in result["customer_answer"].lower()
    assert "support review" in result["customer_answer"].lower()


def test_never_answer_without_citing_policy():
    agent = make_agent()
    result = agent.run(
        {
            "customer_message": "Can I exchange this shirt for a different color?",
            "order_context": {
                "delivery_date": "2026-06-10",
                "item_category": "shirt",
                "item_condition": "unused, original packaging",
                "final_sale": False,
                "order_value": 40,
                "proof_of_purchase": "order NC-2004",
            },
        }
    )

    assert result["citations"]
    assert agent.last_trace.citation_validation["valid"] is True


def test_never_continue_if_policy_evidence_is_missing():
    class FailingIfCalledGenerator:
        def generate(self, customer_message, decision, retrieved_chunks):
            raise AssertionError("answer generator should not be called")

    agent = ReturnPolicyAgent(
        EmptyRetriever(),
        answer_generator=FailingIfCalledGenerator(),
    )

    result = agent.run(
        {
            "customer_message": "Can I return this jacket?",
            "order_context": {
                "delivery_date": "2026-06-10",
                "item_condition": "unused, original packaging",
                "proof_of_purchase": "order NC-2005",
            },
        }
    )

    assert result["decision"] == "escalate"
    assert result["reason_code"] == "unclear"
    assert result["escalate"] is True
    assert agent.last_trace.citation_validation["valid"] is False
    assert "citations_missing" in agent.last_trace.citation_validation["errors"]
    assert "support review" in result["customer_answer"].lower()
