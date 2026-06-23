from __future__ import annotations

import re
from typing import List

from return_agent.citations import format_citation
from return_agent.models import PolicyChunk, PolicyDocument

SECTION_RE = re.compile(r"^##\s+\[(POLICY:[A-Z0-9_]+)\]\s+(.+?)\s*$")


def chunk_policy_document(document: PolicyDocument) -> List[PolicyChunk]:
    """Chunk one policy document by stable policy heading sections."""
    chunks: List[PolicyChunk] = []
    current_policy_id = None
    current_heading = None
    current_lines: List[str] = []

    for line in document.text.splitlines():
        match = SECTION_RE.match(line)
        if match:
            _append_chunk(
                chunks,
                document,
                current_policy_id,
                current_heading,
                current_lines,
            )
            current_policy_id = match.group(1)
            current_heading = match.group(2).strip()
            current_lines = [line]
        elif current_policy_id:
            current_lines.append(line)

    _append_chunk(chunks, document, current_policy_id, current_heading, current_lines)
    return chunks


def chunk_policy_documents(documents: List[PolicyDocument]) -> List[PolicyChunk]:
    chunks: List[PolicyChunk] = []
    for document in documents:
        chunks.extend(chunk_policy_document(document))
    return chunks


def _append_chunk(
    chunks: List[PolicyChunk],
    document: PolicyDocument,
    policy_id: str,
    heading: str,
    lines: List[str],
) -> None:
    if not policy_id or not heading or not lines:
        return

    chunks.append(
        PolicyChunk(
            document_name=document.name,
            section_heading=heading,
            policy_id=policy_id,
            chunk_text="\n".join(lines).strip(),
            source_citation=format_citation(document.name, policy_id),
        )
    )
