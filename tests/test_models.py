import pytest
from pydantic import ValidationError

from return_agent.models import AgentDecision, OrderContext, PolicyChunk


def test_structured_models_are_pydantic_models():
    decision = AgentDecision(decision="eligible_return", reason_code="standard_30_day")

    assert hasattr(decision, "model_dump")
    assert decision.to_dict()["decision"] == "eligible_return"


def test_agent_decision_validates_allowed_decisions():
    with pytest.raises(ValidationError):
        AgentDecision(decision="maybe", reason_code="standard_30_day")


def test_order_context_coerces_order_value_to_float():
    context = OrderContext.from_dict({"order_value": "120.50"})

    assert context.order_value == 120.50


def test_policy_chunk_to_dict_preserves_citation_fields():
    chunk = PolicyChunk(
        document_name="01_standard_returns.md",
        section_heading="Standard 30-Day Return Window",
        policy_id="POLICY:STANDARD_RETURN_WINDOW",
        chunk_text="Most items can be returned within 30 days of delivery.",
        source_citation="01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]",
    )

    assert chunk.to_dict() == {
        "document_name": "01_standard_returns.md",
        "section_heading": "Standard 30-Day Return Window",
        "policy_id": "POLICY:STANDARD_RETURN_WINDOW",
        "chunk_text": "Most items can be returned within 30 days of delivery.",
        "source_citation": "01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]",
    }
