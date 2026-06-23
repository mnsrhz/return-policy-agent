from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from return_agent.llm_utils import _usage_to_dict
from return_agent.models import AgentDecision, PolicyChunk
from return_agent.openai_client import render_customer_answer_prompt


class DeterministicAnswerGenerator:
    model_name: Optional[str] = None
    last_token_usage: Dict[str, Any] = {}

    def generate(self, *, customer_message: str, decision: AgentDecision, retrieved_chunks: Iterable[PolicyChunk]) -> str:
        return decision.customer_answer


class OpenAIFinalAnswerGenerator:
    def __init__(self, *, client, model: str, fallback: Optional[DeterministicAnswerGenerator] = None):
        self.client = client
        self.model_name = model
        self.fallback = fallback or DeterministicAnswerGenerator()
        self.last_token_usage: Dict[str, Any] = {}

    def generate(self, *, customer_message: str, decision: AgentDecision, retrieved_chunks: Iterable[PolicyChunk]) -> str:
        prompt = render_customer_answer_prompt(customer_message, decision, retrieved_chunks)
        try:
            response = self.client.responses.create(model=self.model_name, input=prompt, temperature=0.2)
            self.last_token_usage = _usage_to_dict(getattr(response, "usage", None))
            return (getattr(response, "output_text", "") or decision.customer_answer).strip()
        except Exception:
            self.last_token_usage = {}
            return self.fallback.generate(customer_message=customer_message, decision=decision, retrieved_chunks=retrieved_chunks)
