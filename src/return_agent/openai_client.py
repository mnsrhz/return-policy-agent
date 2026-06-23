from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from return_agent.models import AgentDecision, PolicyChunk
from return_agent.prompts import POLICY_GUARDRAILS


@dataclass(frozen=True)
class OpenAISettings:
    api_key: Optional[str]
    model: str
    enabled: bool


class OpenAIAnswerGenerator:
    """Uses OpenAI only to write the customer-facing answer.

    The deterministic backend still owns the decision, reason code, missing info,
    escalation flag, policy sections, and citations.
    """

    def __init__(self, api_key: str, model: str, client=None):
        self.model = model
        self.client = client or _build_openai_client(api_key)

    def generate(
        self,
        *,
        customer_message: str,
        decision: AgentDecision,
        retrieved_chunks: Iterable[PolicyChunk],
    ) -> str:
        prompt = render_customer_answer_prompt(
            customer_message,
            decision,
            retrieved_chunks,
        )
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=0.2,
        )
        return (getattr(response, "output_text", "") or decision.customer_answer).strip()


def build_answer_generator_from_env(
    env_path: str | Path = ".env",
) -> Optional[OpenAIAnswerGenerator]:
    settings = load_openai_settings(env_path)
    if not settings.enabled or not settings.api_key:
        return None
    return OpenAIAnswerGenerator(api_key=settings.api_key, model=settings.model)


def load_openai_settings(env_path: str | Path = ".env") -> OpenAISettings:
    values = _read_env_file(Path(env_path))
    example_values = _read_env_file(Path(".env.example"))

    api_key = (
        os.getenv("OPENAI_API_KEY")
        or values.get("OPENAI_API_KEY")
        or example_values.get("OPENAI_API_KEY")
    )
    model = (
        os.getenv("OPENAI_MODEL")
        or values.get("OPENAI_MODEL")
        or example_values.get("OPENAI_MODEL")
        or "gpt-4.1-mini"
    )
    enabled_value = (
        os.getenv("USE_OPENAI_LM")
        or values.get("USE_OPENAI_LM")
        or example_values.get("USE_OPENAI_LM")
        or "false"
    )
    enabled = enabled_value.lower() in {"1", "true", "yes", "on"}
    return OpenAISettings(api_key=api_key, model=model, enabled=enabled)


def render_customer_answer_prompt(
    customer_message: str,
    decision: AgentDecision,
    retrieved_chunks: Iterable[PolicyChunk],
) -> str:
    evidence = "\n\n".join(
        f"{chunk.source_citation}\n{chunk.chunk_text}" for chunk in retrieved_chunks
    )
    return f"""You are writing a concise customer-facing response for Northstar Commerce.

Do not change the decision, reason code, escalation status, missing information, or citations.
Do not promise refunds, exchanges, store credit, shipping reimbursement, or exceptions unless the structured decision already supports it.
Use only the structured decision and policy evidence below.

Mandatory guardrails:
{chr(10).join(f"- {rule}" for rule in POLICY_GUARDRAILS)}

Customer message:
{customer_message}

Structured decision:
- decision: {decision.decision}
- reason_code: {decision.reason_code}
- missing_info: {decision.missing_info}
- escalate: {decision.escalate}
- confidence: {decision.confidence}
- citations: {decision.citations}

Deterministic fallback answer:
{decision.customer_answer}

Policy evidence:
{evidence or "No retrieved chunks were provided."}

Write the final answer in 2-4 sentences. Include citation strings exactly as provided when relevant.
"""


def _build_openai_client(api_key: str):
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError(
            "The openai package is not installed. Run `pip install -r requirements.txt`."
        ) from exc
    return OpenAI(api_key=api_key)


def build_openai_client(api_key: str):
    return _build_openai_client(api_key)


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values
