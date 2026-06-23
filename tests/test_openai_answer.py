from return_agent.agent import ReturnPolicyAgent
from return_agent.decision_agent import OpenAIPolicyDecisionAgent
from return_agent.guardrails import safety_precheck
from return_agent.intent_extractor import OpenAIIntentExtractor
from return_agent.models import AgentDecision
from return_agent.openai_client import (
    OpenAIAnswerGenerator,
    load_openai_settings,
    render_customer_answer_prompt,
)


class FakeResponse:
    def __init__(self, output_text="Polished customer-facing answer from the model."):
        self.output_text = output_text


class FakeResponses:
    def __init__(self, output_text=None):
        self.output_text = output_text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeResponse(self.output_text or "Polished customer-facing answer from the model.")


class FakeClient:
    def __init__(self, output_text=None):
        self.responses = FakeResponses(output_text)


class EmptyRetriever:
    chunks = []

    def retrieve(self, query, top_k=8):
        return []


def test_load_openai_settings_reads_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENAI_API_KEY=sk-test\nOPENAI_MODEL=gpt-test\nUSE_OPENAI_LM=true\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("USE_OPENAI_LM", raising=False)

    settings = load_openai_settings(env_file)

    assert settings.api_key == "sk-test"
    assert settings.model == "gpt-test"
    assert settings.enabled is True


def test_openai_answer_generator_calls_responses_api_with_decision_context():
    fake_client = FakeClient()
    generator = OpenAIAnswerGenerator(
        api_key="sk-test",
        model="gpt-test",
        client=fake_client,
    )
    decision = AgentDecision(
        decision="eligible_return",
        reason_code="standard_30_day",
        citations=["01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]"],
        customer_answer="Deterministic fallback.",
    )

    answer = generator.generate(
        customer_message="Can I return this?",
        decision=decision,
        retrieved_chunks=[],
    )

    assert answer == "Polished customer-facing answer from the model."
    call = fake_client.responses.calls[0]
    assert call["model"] == "gpt-test"
    assert "eligible_return" in call["input"]
    assert "01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]" in call["input"]


def test_openai_intent_extractor_calls_responses_api_and_validates_schema():
    fake_client = FakeClient(
        output_text='{"intent":"return_request","requested_resolution":"return","extracted_facts":{"days_since_delivery":5,"item_condition":"unused","final_sale":false,"proof_of_purchase":"order NC-1","order_number_present":true,"order_value":100,"issue_type":null},"missing_info":[],"risk_flags":[],"requires_policy_lookup":true,"confidence":0.9}'
    )
    extractor = OpenAIIntentExtractor(client=fake_client, model="gpt-test")

    result = extractor.extract(
        {
            "customer_message": "Can I return this?",
            "order_context": {"proof_of_purchase": "order NC-1"},
        }
    )

    assert result.intent == "return_request"
    assert result.extracted_facts.order_number_present is True
    assert fake_client.responses.calls[0]["model"] == "gpt-test"


def test_openai_decision_agent_calls_responses_api_and_validates_schema():
    fake_client = FakeClient(
        output_text='{"decision":"eligible_return","reason_code":"standard_30_day","missing_info":[],"escalate":false,"confidence":0.9,"policy_sections_used":["POLICY:STANDARD_RETURN_WINDOW"],"citations":["01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]"],"decision_rationale":"Within policy window."}'
    )
    decision_agent = OpenAIPolicyDecisionAgent(client=fake_client, model="gpt-test")
    extractor = OpenAIIntentExtractor(
        client=FakeClient(
            output_text='{"intent":"return_request","requested_resolution":"return","extracted_facts":{"days_since_delivery":5,"item_condition":"unused","final_sale":false,"proof_of_purchase":"order NC-1","order_number_present":true,"order_value":100,"issue_type":null},"missing_info":[],"risk_flags":[],"requires_policy_lookup":true,"confidence":0.9}'
        ),
        model="gpt-test",
    )
    extracted = extractor.extract({"customer_message": "Can I return this?", "order_context": {}})
    safety = safety_precheck(
        customer_message="Can I return this?",
        extracted=extracted,
        order_context={"proof_of_purchase": "order NC-1"},
    )

    result = decision_agent.decide(
        customer_message="Can I return this?",
        order_context={"proof_of_purchase": "order NC-1"},
        extracted=extracted,
        safety=safety,
        retrieved_chunks=[],
        corpus_chunks=[],
    )

    assert result.decision == "eligible_return"
    assert result.reason_code == "standard_30_day"
    assert fake_client.responses.calls[0]["model"] == "gpt-test"


def test_agent_preserves_decision_but_replaces_customer_answer_when_generator_is_present():
    class FakeGenerator:
        def generate(self, customer_message, decision, retrieved_chunks):
            return "Model-written answer."

    agent = ReturnPolicyAgent.from_policy_dir(
        "policy_docs",
        answer_generator=FakeGenerator(),
    )

    result = agent.run(
        {
            "customer_message": "Can I return this jacket?",
            "order_context": {
                "delivery_date": None,
                "item_condition": "unused",
                "proof_of_purchase": "order NC-1",
            },
        }
    )

    assert result["decision"] == "ask_for_info"
    assert result["customer_answer"] == "Model-written answer."


def test_agent_preserves_decision_when_answer_generator_fails():
    class FailingGenerator:
        def generate(self, customer_message, decision, retrieved_chunks):
            raise RuntimeError("model unavailable")

    agent = ReturnPolicyAgent.from_policy_dir(
        "policy_docs",
        answer_generator=FailingGenerator(),
    )

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
    assert "model unavailable" in agent.last_trace.errors


def test_render_customer_answer_prompt_mentions_no_decision_changes():
    decision = AgentDecision(
        decision="not_eligible",
        reason_code="final_sale",
        citations=["02_final_sale_and_exceptions.md [POLICY:FINAL_SALE_NO_RETURNS]"],
        customer_answer="Fallback.",
    )

    prompt = render_customer_answer_prompt("Can I return it?", decision, [])

    assert "Do not change the decision" in prompt
    assert "not_eligible" in prompt
