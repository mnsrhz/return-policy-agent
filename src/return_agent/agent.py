from __future__ import annotations

import time
from datetime import date
from typing import Any, Dict, List, Optional

from return_agent.answer_generator import DeterministicAnswerGenerator
from return_agent.citations import (
    citations_for_policy_ids,
    sections_for_policy_ids,
    validate_citations,
)
from return_agent.decision_agent import DeterministicPolicyDecisionAgent
from return_agent.guardrails import safety_precheck
from return_agent.intent_extractor import DeterministicIntentExtractor
from return_agent.langsmith_tracing import trace_function
from return_agent.models import AgentDecision, AgentTrace, IntentExtraction, OrderContext, SafetyCheckResult
from return_agent.retriever import KeywordRetriever, build_default_retriever
from return_agent.tracing import TraceTimer, build_trace
from return_agent.utils import condition_is_eligible, contains_any, days_since
from return_agent.validator import validate_and_correct_decision


class ReturnPolicyAgent:
    def __init__(
        self,
        retriever: KeywordRetriever,
        today: Optional[date] = None,
        intent_extractor=None,
        decision_agent=None,
        answer_generator=None,
    ):
        self.retriever = retriever
        self.today = today
        self.intent_extractor = intent_extractor or DeterministicIntentExtractor()
        self.decision_agent = decision_agent or DeterministicPolicyDecisionAgent()
        self.answer_generator = answer_generator
        self.last_trace: Optional[AgentTrace] = None

    @classmethod
    def from_policy_dir(
        cls,
        policy_dir: str = "policy_docs",
        intent_extractor=None,
        decision_agent=None,
        answer_generator=None,
    ) -> "ReturnPolicyAgent":
        return cls(
            build_default_retriever(policy_dir),
            intent_extractor=intent_extractor,
            decision_agent=decision_agent,
            answer_generator=answer_generator,
        )

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        timer = TraceTimer()
        errors: List[str] = []
        retrieved_chunks = []
        message = str(payload.get("customer_message", ""))
        context = OrderContext.from_dict(payload.get("order_context"))
        extracted = IntentExtraction()
        safety = SafetyCheckResult()
        query = ""
        structured_decision = {}
        validator_result = {"valid": False, "errors": ["not_validated"], "corrected": False}
        citation_validation = {"valid": False, "errors": ["not_validated"]}
        step_latency: Dict[str, float] = {}
        token_usage: Dict[str, Any] = {}
        llm_models = {
            "intent_extraction": getattr(self.intent_extractor, "model_name", None),
            "structured_decision": getattr(self.decision_agent, "model_name", None),
            "answer_generation": getattr(self.answer_generator, "model_name", None),
        }

        try:
            start = time.perf_counter()
            extracted = trace_function(
                "intent_extraction_llm",
                self.intent_extractor.extract,
                payload,
                run_type="llm" if llm_models["intent_extraction"] else "chain",
                metadata={"model": llm_models["intent_extraction"]},
            )
            step_latency["intent_extraction"] = round(time.perf_counter() - start, 6)
            token_usage["intent_extraction"] = getattr(self.intent_extractor, "last_token_usage", {})

            start = time.perf_counter()
            safety = trace_function(
                "safety_precheck",
                safety_precheck,
                run_type="chain",
                customer_message=message,
                extracted=extracted,
                order_context=context.to_dict(),
            )
            step_latency["safety_precheck"] = round(time.perf_counter() - start, 6)

            start = time.perf_counter()
            query = self._build_query(message, context, extracted, safety)
            top_k = len(self.retriever.chunks)
            retrieved_chunks = trace_function(
                "policy_retrieval",
                self.retriever.retrieve,
                query,
                top_k=top_k,
                run_type="retriever",
                metadata={"top_k": top_k},
            )
            step_latency["retrieval"] = round(time.perf_counter() - start, 6)

            start = time.perf_counter()
            decision = trace_function(
                "structured_decision_llm",
                self.decision_agent.decide,
                run_type="llm" if llm_models["structured_decision"] else "chain",
                metadata={"model": llm_models["structured_decision"]},
                customer_message=message,
                order_context=context.to_dict(),
                extracted=extracted,
                safety=safety,
                retrieved_chunks=retrieved_chunks,
                corpus_chunks=self.retriever.chunks,
            )
            structured_decision = decision.to_dict()
            step_latency["structured_decision"] = round(time.perf_counter() - start, 6)
            token_usage["structured_decision"] = getattr(self.decision_agent, "last_token_usage", {})

            start = time.perf_counter()
            decision, validation = trace_function(
                "deterministic_validator",
                validate_and_correct_decision,
                run_type="chain",
                decision=decision,
                extracted=extracted,
                safety=safety,
                order_context=context,
                retrieved_chunks=retrieved_chunks,
            )
            validator_result = validation.to_dict()
            step_latency["validation"] = round(time.perf_counter() - start, 6)

            start = time.perf_counter()
            citation_validation = trace_function(
                "citation_validation",
                validate_citations,
                decision,
                retrieved_chunks,
                run_type="chain",
            ).model_dump()
            if not citation_validation["valid"]:
                errors.extend(citation_validation["errors"])
                decision = self._citation_failure_decision(decision)
            else:
                try:
                    answer = trace_function(
                        "final_answer_llm",
                        self._generate_final_answer,
                        message,
                        decision,
                        retrieved_chunks,
                        run_type="llm" if llm_models["answer_generation"] else "chain",
                        metadata={"model": llm_models["answer_generation"]},
                    )
                    decision = decision.model_copy(update={"customer_answer": answer})
                except Exception as exc:
                    errors.append(str(exc))
            step_latency["answer_generation"] = round(time.perf_counter() - start, 6)
            token_usage["answer_generation"] = getattr(self.answer_generator, "last_token_usage", {})
        except Exception as exc:  # pragma: no cover - defensive trace path
            errors.append(str(exc))
            decision = AgentDecision(
                decision="escalate",
                reason_code="unclear",
                escalate=True,
                confidence=0.0,
                customer_answer=(
                    "I could not safely evaluate this request from the available "
                    "policy information, so it needs support review."
                ),
            )

        self.last_trace = build_trace(
            input_payload=payload,
            retrieved_chunks=retrieved_chunks,
            decision=decision,
            extracted_intent=extracted.to_dict(),
            safety_precheck=safety.to_dict(),
            retrieval_query=query,
            structured_decision=structured_decision or decision.to_dict(),
            validator_result=validator_result,
            citation_validation=citation_validation,
            final_answer=decision.customer_answer,
            step_latency=step_latency,
            llm_models=llm_models,
            token_usage=token_usage,
            latency=timer.elapsed(),
            errors=errors,
        )
        return decision.to_dict()

    def _generate_final_answer(
        self,
        message: str,
        decision: AgentDecision,
        retrieved_chunks,
    ) -> str:
        generator = self.answer_generator or DeterministicAnswerGenerator()
        return generator.generate(
            customer_message=message,
            decision=decision,
            retrieved_chunks=retrieved_chunks,
        )

    def _citation_failure_decision(self, original_decision: AgentDecision) -> AgentDecision:
        return AgentDecision(
            decision="escalate",
            reason_code="unclear",
            missing_info=original_decision.missing_info,
            escalate=True,
            confidence=0.0,
            policy_sections_used=original_decision.policy_sections_used,
            citations=original_decision.citations,
            customer_answer=(
                "I cannot safely answer this request because the required policy "
                "evidence is missing or invalid. This needs support review."
            ),
        )

    def _apply_answer_generator(
        self,
        message: str,
        decision: AgentDecision,
        retrieved_chunks,
    ) -> AgentDecision:
        if not self.answer_generator:
            return decision
        decision.customer_answer = self.answer_generator.generate(
            customer_message=message,
            decision=decision,
            retrieved_chunks=retrieved_chunks,
        )
        return decision

    def _decide(
        self,
        message: str,
        context: OrderContext,
        retrieved_chunks,
    ) -> AgentDecision:
        text = f"{message} {context.item_condition or ''}".lower()

        if self._is_exception_request(text):
            return self._decision(
                "escalate",
                "exception_request",
                ["POLICY:ESCALATION_POLICY_EXCEPTIONS"],
                retrieved_chunks,
                True,
                0.95,
                "This request needs support review because it asks for an exception to the stated policy.",
            )

        if self._is_legal_or_abuse_escalation(text):
            return self._decision(
                "escalate",
                "unclear",
                ["POLICY:ESCALATION_LEGAL_THREATS"],
                retrieved_chunks,
                True,
                0.95,
                "This message needs human support review under Northstar Commerce escalation rules.",
            )

        if context.order_value is not None and float(context.order_value) > 500:
            return self._decision(
                "escalate",
                "unclear",
                ["POLICY:ESCALATION_HIGH_VALUE_REFUNDS"],
                retrieved_chunks,
                True,
                0.9,
                "Refund requests over $500 require human support review before approval.",
            )

        if self._is_damaged_wrong_or_missing(text):
            return self._decision(
                "escalate",
                self._issue_reason_code(text),
                [
                    "POLICY:DAMAGE_WRONG_MISSING_REVIEW",
                    "POLICY:DAMAGE_WRONG_MISSING_REQUIRED_INFO",
                ],
                retrieved_chunks,
                True,
                0.9,
                "This issue needs support review. Northstar Commerce requires order details and issue evidence before approving a refund, replacement, or shipping-fee refund.",
                self._missing_issue_info(context, text),
            )

        if self._is_shipping_fee_question(text):
            return self._shipping_fee_decision(text, retrieved_chunks)

        if context.final_sale is True or "final sale" in text:
            return self._decision(
                "not_eligible",
                "final_sale",
                ["POLICY:FINAL_SALE_NO_RETURNS"],
                retrieved_chunks,
                False,
                0.95,
                "Final sale items cannot be returned or exchanged unless a separate damaged, defective, wrong-item, or missing-item issue requires support review.",
            )

        missing = self._missing_standard_info(context)
        if missing:
            return self._decision(
                "ask_for_info",
                "missing_order_number" if "delivery_date" in missing else "no_proof_of_purchase",
                [
                    "POLICY:STANDARD_RETURN_WINDOW",
                    "POLICY:PROOF_OF_PURCHASE_REQUIRED",
                    "POLICY:STANDARD_RETURN_DECISION_BOUNDARY",
                ],
                retrieved_chunks,
                False,
                0.7,
                "I need a few details before I can determine return eligibility under the Northstar Commerce policy.",
                missing,
            )

        if self._is_gift_return(text, context):
            return self._decision(
                "eligible_return",
                "gift_return",
                ["POLICY:GIFT_RETURN_REQUIREMENTS", "POLICY:GIFT_REFUND_STORE_CREDIT"],
                retrieved_chunks,
                False,
                0.86,
                "This gift return appears eligible for review under the gift return policy, and gift returns are usually refunded as store credit.",
            )

        if self._is_exchange_request(text):
            return self._decision(
                "eligible_exchange",
                "standard_30_day",
                [
                    "POLICY:EXCHANGE_SIZE_COLOR_WINDOW",
                    "POLICY:EXCHANGE_INVENTORY_AVAILABILITY",
                ],
                retrieved_chunks,
                False,
                0.86,
                "This size or color exchange appears eligible under the 30-day exchange policy, subject to inventory availability.",
            )

        return self._decision(
            "eligible_return",
            "standard_30_day",
            [
                "POLICY:STANDARD_RETURN_WINDOW",
                "POLICY:STANDARD_ITEM_CONDITION",
                "POLICY:PROOF_OF_PURCHASE_REQUIRED",
            ],
            retrieved_chunks,
            False,
            0.88,
            "This item appears eligible for a standard return because it is within 30 days of delivery, in eligible condition, and has proof of purchase.",
        )

    def _shipping_fee_decision(self, text: str, retrieved_chunks) -> AgentDecision:
        if contains_any(text, ["wrong size", "changed mind", "ordered by mistake", "buyer"]):
            return self._decision(
                "not_eligible",
                "shipping_fee",
                ["POLICY:RETURN_SHIPPING_CUSTOMER_REASONS"],
                retrieved_chunks,
                False,
                0.9,
                "Return shipping is not refunded for customer-initiated reasons such as wrong size, changed mind, buyer's remorse, or ordered by mistake.",
            )
        if self._is_damaged_wrong_or_missing(text):
            return self._decision(
                "escalate",
                "shipping_fee",
                ["POLICY:RETURN_SHIPPING_NORTHSTAR_REASONS"],
                retrieved_chunks,
                True,
                0.82,
                "Return shipping may be refunded for damaged, defective, wrong, missing, or not-as-described items after support review.",
            )
        return self._decision(
            "ask_for_info",
            "shipping_fee",
            [
                "POLICY:RETURN_SHIPPING_CUSTOMER_REASONS",
                "POLICY:RETURN_SHIPPING_NORTHSTAR_REASONS",
            ],
            retrieved_chunks,
            False,
            0.65,
            "I need the return reason before I can determine whether return shipping may be refunded.",
            ["return_reason"],
        )

    def _decision(
        self,
        decision: str,
        reason_code: str,
        policy_ids: List[str],
        retrieved_chunks,
        escalate: bool,
        confidence: float,
        answer: str,
        missing_info: Optional[List[str]] = None,
    ) -> AgentDecision:
        available_citations = citations_for_policy_ids(self.retriever.chunks, policy_ids)
        fallback_citations = citations_for_policy_ids(retrieved_chunks, policy_ids)
        citations = available_citations or fallback_citations
        return AgentDecision(
            decision=decision,
            reason_code=reason_code,
            missing_info=missing_info or [],
            escalate=escalate,
            confidence=confidence,
            policy_sections_used=sections_for_policy_ids(policy_ids),
            citations=citations,
            customer_answer=answer,
        )

    def _missing_standard_info(self, context: OrderContext) -> List[str]:
        missing: List[str] = []
        if not context.delivery_date:
            missing.append("delivery_date")
        if not context.item_condition:
            missing.append("item_condition")
        elif not condition_is_eligible(context.item_condition):
            missing.append("eligible_item_condition")
        if not context.proof_of_purchase:
            missing.append("proof_of_purchase")

        elapsed = days_since(context.delivery_date, self.today)
        if elapsed is not None and elapsed > 30:
            missing.append("support_review_for_late_return")
        return missing

    def _missing_issue_info(self, context: OrderContext, text: str) -> List[str]:
        missing: List[str] = []
        if not context.proof_of_purchase:
            missing.append("order_number_or_proof_of_purchase")
        if not contains_any(text, ["photo", "description", "cracked", "broken", "wrong", "missing", "defective", "damaged"]):
            missing.append("photo_or_description")
        if not self._is_damaged_wrong_or_missing(text):
            missing.append("issue_type")
        return missing

    def _build_query(
        self,
        message: str,
        context: OrderContext,
        extracted: Optional[IntentExtraction] = None,
        safety: Optional[SafetyCheckResult] = None,
    ) -> str:
        extracted = extracted or IntentExtraction()
        safety = safety or SafetyCheckResult()
        policy_terms: List[str] = []

        if safety.reason_code == "legal_threat":
            policy_terms.extend(["legal threats", "regulatory claims", "attorney involvement"])
        elif safety.reason_code == "fraud_concern":
            policy_terms.extend(["fraud concerns", "repeat abuse", "suspicious return patterns"])
        elif safety.reason_code == "exception_request":
            policy_terms.extend(["policy exception requests", "final sale restrictions", "override"])
        elif "high_value_refund" in safety.risk_flags:
            policy_terms.extend(["high value refunds over 500 dollars", "support review before approval"])

        if extracted.intent == "return_request":
            policy_terms.extend(["standard 30 day return window", "proof of purchase", "item condition requirements"])
        elif extracted.intent == "exchange_request":
            policy_terms.extend(["size color exchanges", "inventory availability"])
        elif extracted.intent == "shipping_fee":
            policy_terms.extend(["return shipping customer initiated reasons", "shipping fees"])
        elif extracted.intent in {"damaged_item", "wrong_item", "missing_item"}:
            policy_terms.extend(["damaged defective missing wrong item support review required"])
        elif extracted.intent == "gift_return":
            policy_terms.extend(["gift return requirements", "gift refund store credit"])

        return " ".join(
            str(part)
            for part in [
                message,
                extracted.intent,
                extracted.requested_resolution,
                extracted.extracted_facts.issue_type,
                " ".join(policy_terms),
                context.item_category,
                context.item_condition,
                "final sale" if context.final_sale else "",
                context.proof_of_purchase,
                context.order_number,
            ]
            if part
        )

    @staticmethod
    def _is_exception_request(text: str) -> bool:
        return contains_any(text, ["exception", "override", "special approval", "supervisor", "late return"])

    @staticmethod
    def _is_legal_or_abuse_escalation(text: str) -> bool:
        return contains_any(
            text,
            ["sue", "lawsuit", "lawyer", "attorney", "chargeback", "fraud", "scam", "threat"],
        )

    @staticmethod
    def _is_damaged_wrong_or_missing(text: str) -> bool:
        return contains_any(
            text,
            ["damaged", "defective", "broken", "cracked", "wrong item", "missing", "not as described"],
        )

    @staticmethod
    def _issue_reason_code(text: str) -> str:
        if contains_any(text, ["wrong item", "not as described"]):
            return "wrong_item"
        return "damaged_item"

    @staticmethod
    def _is_shipping_fee_question(text: str) -> bool:
        return contains_any(text, ["shipping", "return shipping", "shipping fee", "postage"])

    @staticmethod
    def _is_gift_return(text: str, context: OrderContext) -> bool:
        proof = (context.proof_of_purchase or "").lower()
        return "gift" in text or "gift receipt" in proof

    @staticmethod
    def _is_exchange_request(text: str) -> bool:
        return "exchange" in text or contains_any(text, ["different size", "different color"])
