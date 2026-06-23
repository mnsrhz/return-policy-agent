from __future__ import annotations

from typing import Iterable, List

from pydantic import BaseModel, Field

from return_agent.models import AgentDecision, PolicyChunk


class CitationValidationResult(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)


def format_citation(document_name: str, policy_id: str) -> str:
    return f"{document_name} [{policy_id}]"


def citations_for_policy_ids(
    chunks: Iterable[PolicyChunk],
    policy_ids: Iterable[str],
) -> List[str]:
    wanted = list(policy_ids)
    citations: List[str] = []
    for policy_id in wanted:
        for chunk in chunks:
            if chunk.policy_id == policy_id and chunk.source_citation not in citations:
                citations.append(chunk.source_citation)
                break
    return citations


def sections_for_policy_ids(policy_ids: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(policy_ids))


def validate_citations(
    decision: AgentDecision,
    corpus_chunks: Iterable[PolicyChunk],
) -> CitationValidationResult:
    known_citations = {chunk.source_citation for chunk in corpus_chunks}
    known_policy_ids = {chunk.policy_id for chunk in corpus_chunks}
    errors: List[str] = []

    if _requires_citation(decision) and not decision.citations:
        errors.append("citations_missing")

    for policy_id in decision.policy_sections_used:
        if policy_id not in known_policy_ids:
            errors.append(f"policy_section_not_in_corpus: {policy_id}")

    for citation in decision.citations:
        if citation not in known_citations:
            errors.append(f"citation_not_in_corpus: {citation}")

    cited_policy_ids = {_extract_policy_id(citation) for citation in decision.citations}
    cited_policy_ids.discard(None)
    for policy_id in decision.policy_sections_used:
        if decision.citations and policy_id not in cited_policy_ids:
            errors.append(f"policy_section_not_cited: {policy_id}")

    return CitationValidationResult(valid=not errors, errors=errors)


def _requires_citation(decision: AgentDecision) -> bool:
    return decision.decision in {
        "eligible_return",
        "not_eligible",
        "eligible_exchange",
        "ask_for_info",
        "escalate",
    }


def _extract_policy_id(citation: str) -> str | None:
    if "[" not in citation or "]" not in citation:
        return None
    return citation.split("[", 1)[1].split("]", 1)[0]
