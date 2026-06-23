# Golden Dataset README

## Purpose

`data/golden_dataset.jsonl` is the Week 4 golden dataset for the Northstar Commerce Return Policy Agent. It is designed to evaluate whether the agent gives accurate, policy-grounded return, refund, exchange, shipping-fee, gift-return, and escalation guidance.

The dataset is for evaluation only. It should not be used to change agent behavior directly, and it should not be edited after a baseline run unless a label is demonstrably inconsistent with the policy corpus.

## Dataset Mix

The dataset contains exactly 40 labeled cases:

| Scenario Type | Count | Purpose |
| --- | ---: | --- |
| `happy_path` | 20 | Common supported customer questions with clear policy-grounded outcomes. |
| `edge_case` | 12 | Boundary or restricted-policy cases such as final sale, missing facts, no receipt, used items, mixed items, or unsupported channels. |
| `known_failure` | 6 | Cases that are likely to expose weaknesses in rule priority, missing-info handling, high-value escalation, or conflicting facts. |
| `adversarial` | 2 | Prompt-injection or override attempts that must not bypass policy. |

## Label Definitions

### `id`

Stable case identifier in the format `RET-001`.

### `scenario_type`

One of:

- `happy_path`
- `edge_case`
- `known_failure`
- `adversarial`

This field is used for grouped metric reporting.

### `customer_message`

The customer-facing message passed into the agent.

### `order_context`

Structured facts available to the agent:

- `days_since_delivery`: Number of days since delivery, or `null` when unknown.
- `item_condition`: Known item condition, or `null`.
- `final_sale`: Boolean final-sale status, or `null` when unknown.
- `proof_of_purchase`: Receipt, gift receipt, order confirmation, or `null`.
- `order_number`: Order number, or `null`.
- `order_value`: Dollar value, or `null`.
- `item_category`: Product category.
- `issue_type`: Label describing the customer issue for eval clarity.

### `expected_decision`

The expected structured decision:

- `eligible_return`
- `not_eligible`
- `eligible_exchange`
- `ask_for_info`
- `escalate`

### `expected_reason_code`

The expected primary reason code:

- `standard_30_day`
- `outside_return_window`
- `final_sale`
- `damaged_item`
- `wrong_item`
- `missing_item`
- `missing_order_number`
- `no_proof_of_purchase`
- `shipping_fee`
- `gift_return`
- `exception_request`
- `legal_threat`
- `fraud_concern`
- `unclear`

### `expected_missing_info`

The exact missing fields the agent should request. Evaluated with set-based F1 so ordering does not matter.

### `expected_escalate`

Boolean expected escalation flag. This should match whether the case requires support or human review.

### `expected_policy_sections`

Policy IDs that should support the answer. Evaluators should check that retrieved evidence, structured decision citations, and final answer citations cover these policy IDs.

### `expected_answer_traits`

Human-readable requirements for answer-quality or LLM-judge evaluation. These traits describe what the final customer-facing answer should include or avoid.

### `notes`

Short label rationale. Use this field during failure analysis to understand why the expected output is correct.

## Evaluation Mapping

Each expected field maps to a metric:

| Field | Metric |
| --- | --- |
| `expected_decision` | `decision_accuracy` |
| `expected_reason_code` | `reason_code_accuracy` |
| `expected_missing_info` | `missing_info_f1` |
| `expected_escalate` | `escalation_accuracy` |
| `expected_policy_sections` | `citation_coverage` and retrieval/citation diagnostics |
| `expected_answer_traits` | `faithfulness_llm_judge` and manual failure analysis |

## Labeling Principles

- Labels are based on the local markdown policy corpus.
- Do not invent policies that are not in `policy_docs/`.
- If required information is missing and no conclusive disqualifier is known, label the case `ask_for_info`.
- If final sale is known and no damaged, wrong, missing, defective, or incorrect item issue exists, label the case `not_eligible`.
- If an exception request, prompt injection, legal threat, fraud concern, aggressive language, high-value missing-proof case, or unclear damage responsibility is present, label the case `escalate`.
- Never label a case as refund-approved. The policy requires inspection or support review for many refund outcomes.

## Notes On Cancellation Before Shipment

The requested happy-path coverage included cancellation before shipment if policy supports it. The current Northstar Commerce policy corpus does not define cancellation-before-shipment behavior. The golden dataset therefore does not include a cancellation approval case. Instead, it includes an ordered-by-mistake duplicate return case covered by the standard return and customer-initiated shipping-fee policies.
