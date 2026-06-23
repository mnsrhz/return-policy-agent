from pathlib import Path

from return_agent.chunker import chunk_policy_document
from return_agent.policy_loader import load_policy_documents


def test_loads_all_policy_documents_from_policy_docs():
    docs = load_policy_documents(Path("policy_docs"))

    assert len(docs) == 6
    assert {doc.name for doc in docs} >= {
        "01_standard_returns.md",
        "02_final_sale_and_exceptions.md",
        "03_damaged_wrong_missing_items.md",
        "04_refunds_and_shipping_fees.md",
        "05_gifts_exchanges_and_store_credit.md",
        "06_escalation_rules.md",
    }


def test_chunks_preserve_policy_metadata_and_citation():
    docs = load_policy_documents(Path("policy_docs"))
    standard_doc = next(doc for doc in docs if doc.name == "01_standard_returns.md")

    chunks = chunk_policy_document(standard_doc)

    return_window = next(
        chunk for chunk in chunks if chunk.policy_id == "POLICY:STANDARD_RETURN_WINDOW"
    )
    assert return_window.document_name == "01_standard_returns.md"
    assert return_window.section_heading == "Standard 30-Day Return Window"
    assert "30 days of delivery" in return_window.chunk_text
    assert return_window.source_citation == (
        "01_standard_returns.md [POLICY:STANDARD_RETURN_WINDOW]"
    )
