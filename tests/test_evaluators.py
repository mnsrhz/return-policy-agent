from return_agent.evaluators import (
    citation_present,
    citation_coverage,
    decision_accuracy,
    escalation_accuracy,
    missing_info_f1,
    policy_section_recall,
    reason_code_accuracy,
    schema_validity,
)


def test_evaluator_accuracy_helpers_return_binary_scores():
    prediction = {
        "decision": "eligible_return",
        "reason_code": "standard_30_day",
        "escalate": False,
        "citations": ["01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]"],
    }
    reference = {
        "expected_decision": "eligible_return",
        "expected_reason_code": "standard_30_day",
        "expected_escalate": False,
    }

    assert decision_accuracy(prediction, reference) == 1.0
    assert reason_code_accuracy(prediction, reference) == 1.0
    assert escalation_accuracy(prediction, reference) == 1.0
    assert citation_present(prediction) == 1.0


def test_missing_info_f1_scores_partial_overlap():
    prediction = {"missing_info": ["delivery_date", "proof_of_purchase"]}
    reference = {"expected_missing_info": ["delivery_date", "item_condition"]}

    assert missing_info_f1(prediction, reference) == 0.5


def test_missing_info_f1_scores_empty_lists_as_match():
    assert missing_info_f1({"missing_info": []}, {"expected_missing_info": []}) == 1.0


def test_citation_coverage_requires_citation_matching_retrieved_policy_section():
    prediction = {
        "citations": ["01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]"],
        "retrieved_chunks": [
            {
                "policy_id": "POLICY:STANDARD_RETURN_WINDOW",
                "source_citation": "01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]",
            }
        ],
    }

    assert citation_coverage(prediction, {}) == 1.0


def test_citation_coverage_fails_when_citation_not_retrieved():
    prediction = {
        "citations": ["02_final_sale_and_exceptions.md [POLICY:FINAL_SALE_NO_RETURNS]"],
        "retrieved_chunks": [
            {
                "policy_id": "POLICY:STANDARD_RETURN_WINDOW",
                "source_citation": "01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]",
            }
        ],
    }

    assert citation_coverage(prediction, {}) == 0.0


def test_policy_section_recall_scores_expected_policy_sections():
    prediction = {
        "policy_sections_used": [
            "POLICY:STANDARD_RETURN_WINDOW",
            "POLICY:STANDARD_ITEM_CONDITION",
        ]
    }
    reference = {
        "expected_policy_sections": [
            "POLICY:STANDARD_RETURN_WINDOW",
            "POLICY:PROOF_OF_PURCHASE_REQUIRED",
        ]
    }

    assert policy_section_recall(prediction, reference) == 0.5


def test_policy_section_recall_empty_expected_with_valid_citation_scores_one():
    prediction = {
        "citations": ["01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]"],
        "retrieved_chunks": [
            {
                "policy_id": "POLICY:STANDARD_RETURN_WINDOW",
                "source_citation": "01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]",
            }
        ],
    }

    assert policy_section_recall(prediction, {"expected_policy_sections": []}) == 1.0


def test_schema_validity_requires_agent_output_fields():
    valid_prediction = {
        "decision": "eligible_return",
        "reason_code": "standard_30_day",
        "missing_info": [],
        "escalate": False,
        "confidence": 0.88,
        "policy_sections_used": ["POLICY:STANDARD_RETURN_WINDOW"],
        "citations": ["01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]"],
        "customer_answer": "The item appears eligible. 01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]",
    }

    assert schema_validity(valid_prediction) == 1.0
    assert schema_validity({**valid_prediction, "customer_answer": None}) == 0.0
