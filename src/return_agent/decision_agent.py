from __future__ import annotations

from typing import Any, Dict, List, Optional

from return_agent.citations import citations_for_policy_ids, sections_for_policy_ids
from return_agent.llm_utils import call_responses_json
from return_agent.models import AgentDecision, IntentExtraction, OrderContext, PolicyChunk, SafetyCheckResult
from return_agent.utils import condition_is_eligible, contains_any, days_since


class DeterministicPolicyDecisionAgent:
    model_name: Optional[str] = None

    def decide(
        self,
        *,
        customer_message: str,
        order_context: Dict[str, Any],
        extracted: IntentExtraction,
        safety: SafetyCheckResult,
        retrieved_chunks: List[PolicyChunk],
        corpus_chunks: List[PolicyChunk],
    ) -> AgentDecision:
        context = OrderContext.from_dict(order_context)
        text = f"{customer_message} {context.item_condition or ''}".lower()

        if safety.escalate:
            policy_ids = _policy_ids_for_safety(safety)
            if (context.final_sale is True or "final sale" in text) and "POLICY:FINAL_SALE_NO_RETURNS" not in policy_ids:
                policy_ids.append("POLICY:FINAL_SALE_NO_RETURNS")
            missing_info = []
            if "high_value_missing_proof" in safety.risk_flags:
                missing_info = ["proof_of_purchase", "order_number"]
            return _decision(
                "escalate",
                safety.reason_code or "unclear",
                policy_ids,
                retrieved_chunks,
                corpus_chunks,
                True,
                0.95,
                safety.message or "This request needs support review.",
                missing_info=missing_info,
                rationale="Deterministic safety pre-check required escalation.",
            )

        if _is_mixed_item_request(text):
            return _decision(
                "ask_for_info",
                "unclear",
                ["POLICY:STANDARD_RETURN_WINDOW", "POLICY:FINAL_SALE_NO_RETURNS", "POLICY:RESTRICTED_ITEM_FACTS"],
                retrieved_chunks,
                corpus_chunks,
                False,
                0.72,
                "I need item-level eligibility facts before deciding because different items can have different return rules.",
                missing_info=["item_level_final_sale_status", "item_level_condition"],
                rationale="Multiple items with mixed eligibility require item-level facts.",
            )

        if _is_refund_timeline_question(text):
            return _decision(
                "eligible_return",
                "standard_30_day",
                ["POLICY:REFUND_TIMING_AFTER_INSPECTION", "POLICY:INSPECTION_REQUIRED_BEFORE_REFUND"],
                retrieved_chunks,
                corpus_chunks,
                False,
                0.84,
                "Approved refunds are processed 5 to 10 business days after Northstar Commerce receives and inspects the returned item.",
                rationale="Customer asked about refund timing after inspection.",
            )

        if _is_different_payment_method_question(text):
            return _decision(
                "not_eligible",
                "unclear",
                ["POLICY:REFUND_ORIGINAL_PAYMENT"],
                retrieved_chunks,
                corpus_chunks,
                False,
                0.84,
                "Approved refunds go to the original payment method, not a different card.",
                rationale="Policy requires refunds to original payment method.",
            )

        if _is_refund_method_question(text):
            policy_ids = ["POLICY:REFUND_ORIGINAL_PAYMENT", "POLICY:INSPECTION_REQUIRED_BEFORE_REFUND"]
            if "store credit" in text:
                policy_ids = ["POLICY:REFUND_ORIGINAL_PAYMENT", "POLICY:STORE_CREDIT_USE"]
            return _decision(
                "eligible_return",
                "standard_30_day",
                policy_ids,
                retrieved_chunks,
                corpus_chunks,
                False,
                0.84,
                "If the return is approved, the refund goes back to the original payment method.",
                rationale="Customer asked about refund method for an approved return.",
            )

        if _is_unsupported_channel_question(text):
            return _decision(
                "ask_for_info",
                "unclear",
                ["POLICY:STANDARD_RETURN_DECISION_BOUNDARY"],
                retrieved_chunks,
                corpus_chunks,
                False,
                0.68,
                "I need the return channel and location or region before I can safely answer because this policy set does not define that return path.",
                missing_info=["return_channel", "location_or_region"],
                rationale="Unsupported return channel requires clarification.",
            )

        if _is_personalized_or_custom(text, context):
            return _decision(
                "not_eligible",
                "final_sale",
                ["POLICY:PERSONALIZED_CUSTOM_ITEMS", "POLICY:EXCHANGE_RESTRICTED_ITEMS"],
                retrieved_chunks,
                corpus_chunks,
                False,
                0.9,
                "Personalized or customized items are not eligible for a standard return or exchange unless a damage, defect, wrong-item, or incorrect-customization issue requires support review.",
                rationale="Restricted personalized item rules apply.",
            )

        if _is_digital_nonreturnable(text, context):
            return _decision(
                "not_eligible",
                "final_sale",
                ["POLICY:DIGITAL_PRODUCTS_NONRETURNABLE", "POLICY:FINAL_SALE_NO_RETURNS"],
                retrieved_chunks,
                corpus_chunks,
                False,
                0.94,
                "Digital gift cards and downloadable products cannot be returned.",
                rationale="Digital product restriction applies.",
            )

        if _is_shipping_fee_question(text) or extracted.intent == "shipping_fee":
            if _is_northstar_shipping_reason(text):
                return _decision(
                    "escalate",
                    "wrong_item" if "wrong" in text else "shipping_fee",
                    ["POLICY:WRONG_ITEM_RECEIVED", "POLICY:RETURN_SHIPPING_NORTHSTAR_REASONS", "POLICY:DAMAGE_WRONG_MISSING_REVIEW"],
                    retrieved_chunks,
                    corpus_chunks,
                    True,
                    0.88,
                    "This fulfillment issue needs support review. Return shipping may be refunded for wrong, damaged, missing, or not-as-described items after review.",
                    rationale="Northstar-caused shipping fee issue requires support review.",
                )
            if _is_customer_shipping_reason(text):
                return _decision(
                    "not_eligible",
                    "shipping_fee",
                    ["POLICY:RETURN_SHIPPING_CUSTOMER_REASONS"],
                    retrieved_chunks,
                    corpus_chunks,
                    False,
                    0.9,
                    "Return shipping is not refunded for customer-initiated reasons such as wrong size, changed mind, buyer's remorse, or ordered by mistake.",
                    rationale="Customer-initiated shipping-fee reasons are not refunded.",
                )
            return _decision(
                "ask_for_info",
                "shipping_fee",
                ["POLICY:RETURN_SHIPPING_CUSTOMER_REASONS", "POLICY:RETURN_SHIPPING_NORTHSTAR_REASONS"],
                retrieved_chunks,
                corpus_chunks,
                False,
                0.65,
                "I need the return reason before I can determine whether return shipping may be refunded.",
                missing_info=["return_reason"],
                rationale="Shipping fee eligibility depends on the return reason.",
            )

        if extracted.intent in {"damaged_item", "wrong_item", "missing_item"} or _is_damaged_wrong_or_missing(text):
            reason = {
                "wrong_item": "wrong_item",
                "missing_item": "missing_item",
            }.get(extracted.intent, "damaged_item")
            if _is_damage_responsibility_unclear(text):
                return _decision(
                    "escalate",
                    reason,
                    ["POLICY:DAMAGE_RESPONSIBILITY_UNCLEAR", "POLICY:ESCALATION_DAMAGE_RESPONSIBILITY"],
                    retrieved_chunks,
                    corpus_chunks,
                    True,
                    0.9,
                    "This damage responsibility question needs support review before a return or refund decision.",
                    rationale="Customer-caused or unclear damage responsibility requires escalation.",
                )
            missing_info = _missing_issue_info(context, text)
            decision_value = "ask_for_info" if missing_info else "escalate"
            return _decision(
                decision_value,
                reason,
                _issue_policy_ids(reason, missing_info, text),
                retrieved_chunks,
                corpus_chunks,
                decision_value == "escalate",
                0.9,
                "This issue needs support review. Northstar Commerce requires order details and issue evidence before approving a refund, replacement, or shipping-fee refund.",
                missing_info=missing_info,
                rationale="Damaged, wrong, or missing item cases require support review.",
            )

        if context.final_sale is True or extracted.extracted_facts.final_sale is True or "final sale" in text:
            return _decision(
                "not_eligible",
                "final_sale",
                ["POLICY:FINAL_SALE_NO_RETURNS"],
                retrieved_chunks,
                corpus_chunks,
                False,
                0.95,
                "Final sale items cannot be returned or exchanged unless a separate damaged, defective, wrong-item, or missing-item issue requires support review.",
                rationale="Final sale policy blocks standard returns and exchanges.",
            )

        elapsed = days_since(context.delivery_date)
        if elapsed is not None and elapsed > 30:
            policy_ids = ["POLICY:STANDARD_RETURN_WINDOW", "POLICY:STANDARD_RETURN_DECISION_BOUNDARY"]
            if context.item_condition and not condition_is_eligible(context.item_condition):
                policy_ids.append("POLICY:STANDARD_ITEM_CONDITION")
            return _decision(
                "not_eligible",
                "outside_return_window",
                policy_ids,
                retrieved_chunks,
                corpus_chunks,
                False,
                0.88,
                "Standard returns are available within 30 days of delivery, and this request is outside that window.",
                rationale="Delivery timing is outside the standard 30-day return window.",
            )

        if context.item_condition and not condition_is_eligible(context.item_condition):
            return _decision(
                "not_eligible",
                "standard_30_day",
                ["POLICY:STANDARD_ITEM_CONDITION", "POLICY:STANDARD_RETURN_DECISION_BOUNDARY"],
                retrieved_chunks,
                corpus_chunks,
                False,
                0.86,
                "Standard returns require the item to be unused, unworn, unwashed, and in original packaging.",
                rationale="Item condition does not satisfy standard return requirements.",
            )

        if _is_gift_return(text, context) and not _has_proof(context):
            return _decision(
                "ask_for_info",
                "gift_return",
                ["POLICY:GIFT_RETURN_REQUIREMENTS", "POLICY:GIFT_REFUND_STORE_CREDIT"],
                retrieved_chunks,
                corpus_chunks,
                False,
                0.74,
                "Gift returns require a gift receipt or order number before eligibility can be confirmed.",
                missing_info=["gift_receipt_or_order_number", "proof_of_purchase", "order_number"],
                rationale="Gift return proof details are missing.",
            )

        if _explicitly_missing_order_number(text) and not _has_order_reference(context):
            return _decision(
                "ask_for_info",
                "missing_order_number",
                ["POLICY:PROOF_OF_PURCHASE_REQUIRED"],
                retrieved_chunks,
                corpus_chunks,
                False,
                0.76,
                "I need the order number before I can confirm return eligibility.",
                missing_info=["order_number"],
                rationale="Customer says order number is unavailable.",
            )

        missing = _missing_standard_info(context)
        if missing:
            reason_code = "no_proof_of_purchase"
            if "delivery_date" in missing and contains_any(text, ["not sure when", "when it was delivered", "when delivered"]):
                reason_code = "unclear"
            elif "delivery_date" in missing or "order_number" in missing:
                reason_code = "missing_order_number"
            policy_ids = ["POLICY:STANDARD_RETURN_WINDOW", "POLICY:PROOF_OF_PURCHASE_REQUIRED", "POLICY:STANDARD_RETURN_DECISION_BOUNDARY"]
            if missing == ["proof_of_purchase"]:
                policy_ids = ["POLICY:PROOF_OF_PURCHASE_REQUIRED", "POLICY:STORE_CREDIT_WITH_MISSING_PROOF"]
            return _decision(
                "ask_for_info",
                reason_code,
                policy_ids,
                retrieved_chunks,
                corpus_chunks,
                False,
                0.7,
                "I need a few details before I can determine return eligibility under the Northstar Commerce policy.",
                missing_info=missing,
                rationale="Required order details are missing.",
            )

        if extracted.intent == "gift_return" or _is_gift_return(text, context):
            policy_ids = ["POLICY:GIFT_RETURN_REQUIREMENTS", "POLICY:GIFT_REFUND_STORE_CREDIT"]
            if "store credit" in text:
                policy_ids.append("POLICY:STORE_CREDIT_USE")
            return _decision(
                "eligible_return",
                "gift_return",
                policy_ids,
                retrieved_chunks,
                corpus_chunks,
                False,
                0.86,
                "This gift return appears eligible for review under the gift return policy, and gift returns are usually refunded as store credit.",
                rationale="Gift return requirements and store credit policy apply.",
            )

        if extracted.intent == "exchange_request" or _is_exchange_request(text):
            return _decision(
                "eligible_exchange",
                "standard_30_day",
                ["POLICY:EXCHANGE_SIZE_COLOR_WINDOW", "POLICY:EXCHANGE_INVENTORY_AVAILABILITY"],
                retrieved_chunks,
                corpus_chunks,
                False,
                0.86,
                "This size or color exchange appears eligible under the 30-day exchange policy, subject to inventory availability.",
                rationale="Exchange request meets standard eligibility facts.",
            )

        return _decision(
            "eligible_return",
            "standard_30_day",
            _standard_policy_ids(text),
            retrieved_chunks,
            corpus_chunks,
            False,
            0.88,
            "This item appears eligible for a standard return because it is within 30 days of delivery, in eligible condition, and has proof of purchase.",
            rationale="Standard return facts satisfy policy requirements.",
        )


class OpenAIPolicyDecisionAgent:
    def __init__(self, *, client, model: str, fallback: Optional[DeterministicPolicyDecisionAgent] = None):
        self.client = client
        self.model_name = model
        self.fallback = fallback or DeterministicPolicyDecisionAgent()
        self.last_token_usage: Dict[str, Any] = {}

    def decide(self, **kwargs) -> AgentDecision:
        prompt = render_decision_prompt(**kwargs)
        try:
            data, usage = call_responses_json(self.client, model=self.model_name, prompt=prompt)
            self.last_token_usage = usage
            return AgentDecision.model_validate(data)
        except Exception:
            self.last_token_usage = {}
            return self.fallback.decide(**kwargs)


def render_decision_prompt(
    *,
    customer_message: str,
    order_context: Dict[str, Any],
    extracted: IntentExtraction,
    safety: SafetyCheckResult,
    retrieved_chunks: List[PolicyChunk],
    corpus_chunks: List[PolicyChunk],
) -> str:
    evidence = "\n\n".join(f"{c.source_citation}\n{c.chunk_text}" for c in retrieved_chunks)
    return f"""Make a structured policy decision using only the extracted facts, safety result, and retrieved policy context.
Return JSON only. Every decision must cite at least one retrieved policy section.

Customer message: {customer_message}
Order context: {order_context}
Extracted intent/facts: {extracted.model_dump()}
Safety pre-check: {safety.model_dump()}
Retrieved policy context:
{evidence}

Return this JSON shape:
{{
  "decision": "eligible_return | not_eligible | eligible_exchange | ask_for_info | escalate",
  "reason_code": "standard_30_day | outside_return_window | final_sale | damaged_item | wrong_item | missing_item | missing_order_number | no_proof_of_purchase | shipping_fee | gift_return | exception_request | legal_threat | fraud_concern | unclear",
  "missing_info": [],
  "escalate": false,
  "confidence": 0.0,
  "policy_sections_used": [],
  "citations": [],
  "decision_rationale": ""
}}
"""


def _decision(decision, reason_code, policy_ids, retrieved_chunks, corpus_chunks, escalate, confidence, answer, missing_info=None, rationale=""):
    retrieved_citations = citations_for_policy_ids(retrieved_chunks, policy_ids)
    fallback_citations = citations_for_policy_ids(corpus_chunks, policy_ids)
    citations = retrieved_citations or fallback_citations
    return AgentDecision(
        decision=decision,
        reason_code=reason_code,
        missing_info=missing_info or [],
        escalate=escalate,
        confidence=confidence,
        policy_sections_used=sections_for_policy_ids(policy_ids),
        citations=citations,
        decision_rationale=rationale,
        customer_answer=answer,
    )


def _policy_ids_for_safety(safety: SafetyCheckResult) -> List[str]:
    if safety.reason_code == "legal_threat":
        return ["POLICY:ESCALATION_LEGAL_THREATS"]
    if safety.reason_code == "fraud_concern":
        return ["POLICY:ESCALATION_FRAUD_ABUSE"]
    if safety.reason_code == "exception_request":
        return ["POLICY:ESCALATION_POLICY_EXCEPTIONS"]
    if "high_value_missing_proof" in safety.risk_flags:
        return [
            "POLICY:ESCALATION_HIGH_VALUE_REFUNDS",
            "POLICY:ESCALATION_MISSING_PROOF_HIGH_VALUE",
            "POLICY:STORE_CREDIT_WITH_MISSING_PROOF",
        ]
    if "high_value_refund" in safety.risk_flags:
        return ["POLICY:ESCALATION_HIGH_VALUE_REFUNDS"]
    return ["POLICY:ESCALATION_POLICY_EXCEPTIONS"]


def _missing_standard_info(context: OrderContext) -> List[str]:
    missing: List[str] = []
    if not context.delivery_date:
        missing.append("delivery_date")
    if not context.item_condition:
        missing.append("item_condition")
    if not _has_proof(context):
        missing.append("proof_of_purchase")
    return missing


def _missing_issue_info(context: OrderContext, text: str) -> List[str]:
    missing: List[str] = []
    if not _has_order_reference(context):
        missing.append("order_number")
    if not _has_proof(context):
        missing.append("proof_of_purchase")
    if _lacks_photo_or_description(text):
        missing.append("photo_or_description")
    return missing


def _is_damaged_wrong_or_missing(text: str) -> bool:
    return contains_any(text, ["damaged", "defective", "broken", "cracked", "wrong item", "missing", "not as described"]) or _is_wrong_fulfillment(text)


def _is_shipping_fee_question(text: str) -> bool:
    return contains_any(text, ["shipping", "return shipping", "shipping fee", "postage"])


def _is_gift_return(text: str, context: OrderContext) -> bool:
    return "gift" in text or "gift receipt" in (context.proof_of_purchase or "").lower()


def _is_exchange_request(text: str) -> bool:
    return "exchange" in text or contains_any(text, ["different size", "different color"])


def _is_customer_shipping_reason(text: str) -> bool:
    return contains_any(
        text,
        ["wrong size", "changed mind", "changed my mind", "ordered by mistake", "buyer's remorse", "buyer remorse", "duplicate order"],
    )


def _is_northstar_shipping_reason(text: str) -> bool:
    return contains_any(text, ["wrong color was sent", "wrong item", "sent to me", "not as described", "damaged", "defective", "missing"])


def _is_wrong_fulfillment(text: str) -> bool:
    return contains_any(text, ["wrong item", "wrong color was sent", "sent wrong color", "received the wrong color", "not as described"])


def _is_refund_timeline_question(text: str) -> bool:
    return contains_any(text, ["how long", "refund take", "refund timeline", "5 to 10", "business days"]) and "refund" in text


def _is_refund_method_question(text: str) -> bool:
    return contains_any(text, ["original card", "original payment", "paid with store credit", "how will it be refunded"])


def _is_different_payment_method_question(text: str) -> bool:
    return contains_any(text, ["different card", "another card", "different payment method"])


def _is_unsupported_channel_question(text: str) -> bool:
    return contains_any(text, ["outside the us", "international", "own international courier", "unsupported channel"])


def _is_personalized_or_custom(text: str, context: OrderContext) -> bool:
    category = (context.item_category or "").lower()
    return contains_any(f"{text} {category}", ["personalized", "customized", "custom item"])


def _is_digital_nonreturnable(text: str, context: OrderContext) -> bool:
    category = (context.item_category or "").lower()
    return contains_any(f"{text} {category}", ["digital gift card", "downloadable", "digital product"])


def _is_mixed_item_request(text: str) -> bool:
    return contains_any(text, ["two items", "multiple items", "both"]) and "final sale" in text


def _explicitly_missing_order_number(text: str) -> bool:
    return "order number" in text and contains_any(text, ["do not have", "don't have", "cannot find", "can't find", "lost"])


def _has_proof(context: OrderContext) -> bool:
    return bool(context.proof_of_purchase)


def _has_order_reference(context: OrderContext) -> bool:
    proof = (context.proof_of_purchase or "").lower()
    return bool(context.order_number or "order " in proof or proof.startswith("order"))


def _lacks_photo_or_description(text: str) -> bool:
    if contains_any(text, ["no photo", "no photos", "do not have photos", "don't have photos", "without photos"]):
        return True
    return not contains_any(text, ["photo", "photos", "description", "cracked", "broken", "wrong item", "missing item", "defective"])


def _issue_policy_ids(reason: str, missing_info: List[str], text: str) -> List[str]:
    if reason == "wrong_item":
        return ["POLICY:WRONG_ITEM_RECEIVED", "POLICY:RETURN_SHIPPING_NORTHSTAR_REASONS", "POLICY:DAMAGE_WRONG_MISSING_REVIEW"]
    if reason == "missing_item":
        return ["POLICY:MISSING_ITEMS", "POLICY:DAMAGE_WRONG_MISSING_REVIEW", "POLICY:DAMAGE_WRONG_MISSING_REQUIRED_INFO"]
    if contains_any(text, ["dropped", "after delivery", "customer caused"]):
        return ["POLICY:DAMAGE_RESPONSIBILITY_UNCLEAR", "POLICY:ESCALATION_DAMAGE_RESPONSIBILITY"]
    if missing_info:
        return ["POLICY:DAMAGE_WRONG_MISSING_REQUIRED_INFO", "POLICY:DAMAGED_DEFECTIVE_ITEMS"]
    return ["POLICY:DAMAGE_WRONG_MISSING_REVIEW", "POLICY:DAMAGE_WRONG_MISSING_REQUIRED_INFO"]


def _standard_policy_ids(text: str) -> List[str]:
    policy_ids = [
        "POLICY:STANDARD_RETURN_WINDOW",
        "POLICY:STANDARD_ITEM_CONDITION",
        "POLICY:PROOF_OF_PURCHASE_REQUIRED",
    ]
    if _is_customer_shipping_reason(text) or contains_any(text, ["duplicate", "accidentally ordered two"]):
        policy_ids = ["POLICY:STANDARD_RETURN_REASON", "POLICY:STANDARD_RETURN_WINDOW", "POLICY:RETURN_SHIPPING_CUSTOMER_REASONS"]
    if "store credit" in text and "POLICY:STORE_CREDIT_USE" not in policy_ids:
        policy_ids.append("POLICY:STORE_CREDIT_USE")
    return policy_ids


def _is_damage_responsibility_unclear(text: str) -> bool:
    return contains_any(text, ["dropped", "after delivery", "customer caused", "i broke", "broke it"])
