# Policy Decision Schema

## Purpose

The agent must return a structured decision object for every customer response. This keeps behavior inspectable in the Streamlit app and gives Part 2 LangSmith evals stable fields to score.

## Decision Object

```json
{
  "request_type": "return_eligibility",
  "decision": "conditional",
  "customer_answer": "You may be eligible for a return if the item is unused and still within the return window.",
  "reasoning_summary": "The policy allows returns within the stated window, but item condition and delivery date are required before a final decision.",
  "known_facts": {
    "product_category": "shoes",
    "purchase_date": null,
    "delivery_date": null,
    "item_condition": "worn once",
    "reason_for_return": null,
    "proof_of_purchase": null
  },
  "missing_information": [
    "delivery_date",
    "whether the shoes show visible wear",
    "whether original packaging and tags are available"
  ],
  "required_next_steps": [
    "Confirm delivery date.",
    "Confirm item condition and packaging status."
  ],
  "citations": [
    {
      "source_title": "Standard Return Policy",
      "source_path": "data/policies/standard_return_policy.md",
      "section_id": "2.1",
      "section_heading": "Return Window",
      "supporting_text": "Returns are accepted within the stated return window when item condition requirements are met.",
      "relevance": "Defines the timing and condition requirements for return eligibility."
    }
  ],
  "escalation": {
    "required": false,
    "reason": null,
    "handoff_summary": null
  },
  "confidence": "medium"
}
```

## Field Definitions

### `request_type`

Allowed values:

- `return_eligibility`
- `refund_eligibility`
- `exchange_eligibility`
- `return_process`
- `shipping_or_fee`
- `damaged_or_defective`
- `exception_or_edge_case`
- `general_policy_question`
- `unsupported`

### `decision`

Allowed values:

- `eligible`
- `ineligible`
- `conditional`
- `needs_more_info`
- `escalate`
- `not_applicable`

### `customer_answer`

A concise, customer-facing answer. It should be understandable without exposing implementation details.

### `reasoning_summary`

A short explanation of how the agent reached the decision. It should reference policy logic but avoid hidden chain-of-thought. It must not contain unsupported assumptions.

### `known_facts`

A structured object containing facts extracted from the customer message and any prior conversation state. Unknown values should be `null`, not guessed.

### `missing_information`

A list of required facts that prevent a final decision. This should be empty only when the decision can be made or the case is escalated without needing more customer input.

### `required_next_steps`

Actions the customer or support team should take next. These should not include operational promises such as "refund issued" unless the policy corpus explicitly supports that as a hypothetical instruction.

### `citations`

Policy evidence used in the response. Required for all policy-backed answers. If no citations are available for a decision request, the agent should return `escalate`.

### `escalation`

Structured escalation state:

```json
{
  "required": true,
  "reason": "Policy requires inspection for damaged items before refund approval.",
  "handoff_summary": "Customer reports damaged glassware delivered on 2026-06-20. Needs support review and photo inspection."
}
```

### `confidence`

Allowed values:

- `high`
- `medium`
- `low`

Confidence reflects sufficiency of facts and policy support, not model certainty alone.

## Validation Rules

- `decision` must be `needs_more_info` when required facts are missing and escalation is not required.
- `decision` must be `escalate` when `escalation.required` is `true`.
- `citations` must contain at least one item for `eligible`, `ineligible`, `conditional`, and policy-backed `needs_more_info` answers.
- `known_facts` must use `null` for unknown facts.
- `customer_answer` must not contradict `decision`.
- `required_next_steps` must align with either missing information or escalation.
- `confidence` should be `low` when citations are weak, missing, or conflicting.

## Eval-Targeted Fields

Part 2 LangSmith evals should score:

- Schema validity.
- Decision correctness.
- Missing information detection.
- Escalation correctness.
- Citation presence.
- Citation support faithfulness.
- Customer answer helpfulness.
- Refusal to answer unsupported questions.
