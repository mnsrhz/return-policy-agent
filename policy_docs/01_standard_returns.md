# Northstar Commerce Standard Returns Policy

## [POLICY:STANDARD_RETURN_WINDOW] Standard 30-Day Return Window

Most items purchased from Northstar Commerce can be returned within 30 days of delivery. The 30-day period begins on the date the carrier marks the item as delivered, not the order date.

Citation-friendly rule: Northstar Commerce accepts most eligible returns within 30 days of delivery.

Example: If an order was delivered on June 1, the customer may request a standard return through June 30, provided the item also meets condition and proof-of-purchase requirements.

Agent handling rule: If the customer asks whether an item can be returned and does not provide the delivery date, ask for the delivery date before making a final eligibility decision.

## [POLICY:STANDARD_ITEM_CONDITION] Item Condition Requirements

To qualify for a standard return, an item must be unused, unworn, unwashed, and in its original packaging. Original packaging includes manufacturer boxes, product tags, accessories, manuals, protective materials, and included parts when those materials were provided with the item.

Citation-friendly rule: Standard returns require the item to be unused, unworn, unwashed, and in original packaging.

Example: A jacket that still has tags attached and has not been worn outside may qualify for a standard return. A jacket that has been worn, washed, or returned without required accessories may be ineligible or require support review.

Agent handling rule: If the customer describes use, wear, washing, missing tags, missing accessories, or missing packaging, do not approve the return automatically. Ask for the item condition or route to escalation if the policy outcome is unclear.

## [POLICY:PROOF_OF_PURCHASE_REQUIRED] Proof Of Purchase Requirement

Northstar Commerce requires an order number, receipt, gift receipt, or other proof of purchase for standard returns. Proof of purchase is used to verify the purchase date, delivery date, item price, payment method, and return eligibility.

Citation-friendly rule: A standard return requires an order number or proof of purchase.

Example: A customer who provides an order number can be evaluated under the standard return policy. A customer who cannot provide any proof of purchase may still be reviewed by support, but the agent must not promise a refund.

Agent handling rule: If proof of purchase is missing, ask for an order number, receipt, or gift receipt. If the customer cannot provide proof, classify the case as needing support review rather than eligible.

## [POLICY:STANDARD_RETURN_REASON] Standard Customer-Initiated Return Reasons

Standard return reasons include wrong size, changed mind, ordered by mistake, color preference, duplicate order, or buyer's remorse. These reasons may qualify for a return only if the item is within the return window, meets condition requirements, and has proof of purchase.

Citation-friendly rule: Buyer's remorse, wrong size, changed mind, and ordered-by-mistake returns are standard customer-initiated returns subject to the 30-day window, condition rules, and proof-of-purchase requirement.

Example: A customer who ordered two sizes and wants to return one may qualify if the returned item is unused, unworn, unwashed, in original packaging, within 30 days of delivery, and supported by proof of purchase.

Agent handling rule: For standard customer-initiated reasons, check return window, condition, packaging, and proof of purchase before deciding.

## [POLICY:STANDARD_RETURN_DECISION_BOUNDARY] Decision Boundary For Standard Returns

A standard return may be marked eligible only when the customer provides facts showing that the item is within 30 days of delivery, unused, unworn, unwashed, in original packaging, and supported by proof of purchase. If any required fact is unknown, the correct decision is `needs_more_info`, not `eligible`.

Citation-friendly rule: The agent must not mark a standard return eligible unless return window, item condition, packaging, and proof of purchase are all satisfied.

Example: "I bought shoes last month. Can I return them?" is missing delivery date, condition, packaging, and proof of purchase. The correct response is to ask for those facts.

Agent handling rule: Do not infer missing eligibility facts from friendly wording or customer confidence. Ask targeted follow-up questions.
