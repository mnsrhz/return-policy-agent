from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

from return_agent.llm_utils import call_responses_json
from return_agent.models import ExtractedFacts, IntentExtraction, OrderContext
from return_agent.utils import contains_any, days_since


class DeterministicIntentExtractor:
    model_name: Optional[str] = None

    def extract(self, payload: Dict[str, Any]) -> IntentExtraction:
        message = str(payload.get("customer_message", ""))
        context = OrderContext.from_dict(payload.get("order_context"))
        text = f"{message} {context.item_condition or ''}".lower()

        intent = "return_request"
        if contains_any(text, ["exchange", "different size", "different color"]):
            intent = "exchange_request"
        if contains_any(text, ["gift", "gift receipt"]):
            intent = "gift_return"
        if contains_any(text, ["damaged", "defective", "broken", "cracked"]):
            intent = "damaged_item"
        if contains_any(text, ["wrong item", "wrong color sent", "sent wrong color", "received the wrong color", "not as described"]):
            intent = "wrong_item"
        if contains_any(text, ["missing item", "missing from my order", "did not receive"]):
            intent = "missing_item"
        if contains_any(text, ["shipping", "return shipping", "shipping fee", "postage"]):
            intent = "shipping_fee"
        if contains_any(text, ["exception", "override", "special approval", "late return"]):
            intent = "policy_exception"
        if not message.strip():
            intent = "unclear"

        resolution = "return"
        if intent == "exchange_request":
            resolution = "exchange"
        elif contains_any(text, ["refund"]):
            resolution = "refund"
        elif contains_any(text, ["store credit"]):
            resolution = "store_credit"
        elif contains_any(text, ["replacement", "replace"]):
            resolution = "replacement"
        elif intent == "unclear":
            resolution = "unclear"

        issue_type = None
        if intent == "damaged_item":
            issue_type = "damaged"
        elif intent == "wrong_item":
            issue_type = "wrong"
        elif intent == "missing_item":
            issue_type = "missing"

        missing_info = []
        if intent in {"return_request", "exchange_request", "gift_return"}:
            if not context.delivery_date:
                missing_info.append("delivery_date")
            if not context.item_condition:
                missing_info.append("item_condition")
            if not context.proof_of_purchase and not context.order_number:
                missing_info.append("proof_of_purchase")

        risk_flags = []
        if intent == "policy_exception":
            risk_flags.append("policy_exception_request")

        return IntentExtraction(
            intent=intent,
            requested_resolution=resolution,
            extracted_facts=ExtractedFacts(
                days_since_delivery=days_since(context.delivery_date, date.today()),
                item_condition=context.item_condition,
                final_sale=context.final_sale,
                proof_of_purchase=context.proof_of_purchase,
                order_number_present=bool(context.order_number or context.proof_of_purchase),
                order_value=context.order_value,
                issue_type=issue_type,
            ),
            missing_info=missing_info,
            risk_flags=risk_flags,
            requires_policy_lookup=True,
            confidence=0.75 if intent != "unclear" else 0.3,
        )


class OpenAIIntentExtractor:
    def __init__(self, *, client, model: str, fallback: Optional[DeterministicIntentExtractor] = None):
        self.client = client
        self.model_name = model
        self.fallback = fallback or DeterministicIntentExtractor()
        self.last_token_usage: Dict[str, Any] = {}

    def extract(self, payload: Dict[str, Any]) -> IntentExtraction:
        prompt = render_intent_prompt(payload)
        try:
            data, usage = call_responses_json(self.client, model=self.model_name, prompt=prompt)
            self.last_token_usage = usage
            return IntentExtraction.model_validate(data)
        except Exception:
            self.last_token_usage = {}
            return self.fallback.extract(payload)


def render_intent_prompt(payload: Dict[str, Any]) -> str:
    return f"""Extract return-policy intent and facts as JSON only.

Allowed intent values: return_request, exchange_request, refund_status, damaged_item, wrong_item, missing_item, shipping_fee, gift_return, policy_exception, unclear.
Allowed requested_resolution values: return, exchange, refund, store_credit, replacement, unclear.

Input:
{payload}

Return exactly this JSON shape:
{{
  "intent": "...",
  "requested_resolution": "...",
  "extracted_facts": {{
    "days_since_delivery": null,
    "item_condition": null,
    "final_sale": null,
    "proof_of_purchase": null,
    "order_number_present": null,
    "order_value": null,
    "issue_type": null
  }},
  "missing_info": [],
  "risk_flags": [],
  "requires_policy_lookup": true,
  "confidence": 0.0
}}
"""
