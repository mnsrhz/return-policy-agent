from __future__ import annotations

import time
from typing import Any, Dict, List

from return_agent.models import AgentDecision, AgentTrace, PolicyChunk


class TraceTimer:
    def __init__(self) -> None:
        self.started_at = time.perf_counter()

    def elapsed(self) -> float:
        return round(time.perf_counter() - self.started_at, 6)


def build_trace(
    *,
    input_payload: Dict[str, Any],
    extracted_intent: Dict[str, Any],
    safety_precheck: Dict[str, Any],
    retrieval_query: str,
    retrieved_chunks: List[PolicyChunk],
    decision: AgentDecision,
    structured_decision: Dict[str, Any],
    validator_result: Dict[str, Any],
    citation_validation: Dict[str, Any],
    final_answer: str,
    step_latency: Dict[str, float],
    llm_models: Dict[str, Any],
    token_usage: Dict[str, Any],
    latency: float,
    errors: List[str],
) -> AgentTrace:
    return AgentTrace(
        raw_input=input_payload,
        input=input_payload,
        extracted_intent=extracted_intent,
        safety_precheck=safety_precheck,
        retrieval_query=retrieval_query,
        retrieved_chunks=[chunk.to_dict() for chunk in retrieved_chunks],
        structured_decision=structured_decision,
        validator_result=validator_result,
        decision=decision.decision,
        citations=decision.citations,
        citation_validation=citation_validation,
        final_answer=final_answer,
        missing_info=decision.missing_info,
        step_latency=step_latency,
        llm_models=llm_models,
        token_usage=token_usage,
        latency=latency,
        errors=errors,
    )
