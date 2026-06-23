# Northstar Commerce Policy Corpus

This folder contains the local markdown policy corpus for the `return-policy-agent` RAG system. The policies describe fictional retailer Northstar Commerce and are written to support citation-friendly retrieval.

Each document uses:

- Clear Markdown headings.
- Stable policy section IDs in the format `[POLICY:SECTION_NAME]`.
- Direct, citation-friendly wording.
- Customer examples.
- Agent handling rules that describe how the return policy agent should answer, ask follow-up questions, or escalate.

## Documents

- `01_standard_returns.md`: Standard 30-day return rules, condition requirements, and proof of purchase.
- `02_final_sale_and_exceptions.md`: Final sale items, personalized items, digital gift cards, downloadable products, and exceptions.
- `03_damaged_wrong_missing_items.md`: Damaged, defective, wrong, and missing item review paths.
- `04_refunds_and_shipping_fees.md`: Refund method, refund timing, inspection, store credit, and shipping fee rules.
- `05_gifts_exchanges_and_store_credit.md`: Gift returns, exchanges, inventory limits, and store credit.
- `06_escalation_rules.md`: Human review triggers, exception requests, abuse concerns, and high-value cases.

## Retrieval Notes

The RAG pipeline should chunk these files by section heading and preserve the policy IDs as citation metadata. Agent answers should cite the specific policy ID used to support the decision.
