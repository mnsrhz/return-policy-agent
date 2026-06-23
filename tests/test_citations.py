from return_agent.agent import ReturnPolicyAgent
from return_agent.citations import CitationValidationResult, validate_citations
from return_agent.models import AgentDecision
from return_agent.retriever import build_default_retriever
from return_agent.validator import validate_and_correct_decision
from return_agent.models import IntentExtraction, OrderContext, SafetyCheckResult


def test_validate_citations_accepts_known_policy_citations():
    retriever = build_default_retriever("policy_docs")
    decision = AgentDecision(
        decision="eligible_return",
        reason_code="standard_30_day",
        policy_sections_used=["POLICY:STANDARD_RETURN_WINDOW"],
        citations=["01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]"],
    )

    result = validate_citations(decision, retriever.chunks)

    assert result == CitationValidationResult(valid=True, errors=[])


def test_validate_citations_rejects_missing_required_citations():
    retriever = build_default_retriever("policy_docs")
    decision = AgentDecision(
        decision="eligible_return",
        reason_code="standard_30_day",
        policy_sections_used=["POLICY:STANDARD_RETURN_WINDOW"],
        citations=[],
    )

    result = validate_citations(decision, retriever.chunks)

    assert result.valid is False
    assert "citations_missing" in result.errors


def test_validate_citations_rejects_unknown_citation_strings():
    retriever = build_default_retriever("policy_docs")
    decision = AgentDecision(
        decision="not_eligible",
        reason_code="final_sale",
        policy_sections_used=["POLICY:FINAL_SALE_NO_RETURNS"],
        citations=["unknown.md [POLICY:FINAL_SALE_NO_RETURNS]"],
    )

    result = validate_citations(decision, retriever.chunks)

    assert result.valid is False
    assert "citation_not_in_corpus: unknown.md [POLICY:FINAL_SALE_NO_RETURNS]" in result.errors


def test_agent_records_citation_validation_in_trace():
    agent = ReturnPolicyAgent.from_policy_dir("policy_docs")

    agent.run(
        {
            "customer_message": "Can I return this final sale bag?",
            "order_context": {
                "delivery_date": "2026-06-05",
                "item_condition": "unused",
                "final_sale": True,
                "order_value": 80,
                "proof_of_purchase": "order NC-1002",
            },
        }
    )

    trace = agent.last_trace.to_dict()
    assert trace["citation_validation"]["valid"] is True
    assert trace["citation_validation"]["errors"] == []


def test_validator_normalizes_citations_from_retrieved_policy_sections():
    retriever = build_default_retriever("policy_docs")
    retrieved = [
        chunk
        for chunk in retriever.chunks
        if chunk.policy_id == "POLICY:STANDARD_RETURN_WINDOW"
    ]
    decision = AgentDecision(
        decision="eligible_return",
        reason_code="standard_30_day",
        policy_sections_used=["POLICY:STANDARD_RETURN_WINDOW"],
        citations=[
            "Northstar Commerce accepts most eligible returns within 30 days [POLICY:STANDARD_RETURN_WINDOW]"
        ],
        confidence=0.9,
    )

    corrected, result = validate_and_correct_decision(
        decision=decision,
        extracted=IntentExtraction(intent="return_request", confidence=0.9),
        safety=SafetyCheckResult(),
        order_context=OrderContext(
            delivery_date="2026-06-10",
            item_condition="unused, original packaging",
            proof_of_purchase="order NC-1",
        ),
        retrieved_chunks=retrieved,
    )

    assert result.valid is True
    assert result.corrected is True
    assert corrected.citations == [
        "01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]"
    ]
