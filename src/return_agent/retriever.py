from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Union

from return_agent.chunker import chunk_policy_documents
from return_agent.models import PolicyChunk
from return_agent.policy_loader import load_policy_documents

TOKEN_RE = re.compile(r"[a-z0-9]+")


class KeywordRetriever:
    """Small local BM25-style retriever with no external service dependency."""

    def __init__(self, chunks: List[PolicyChunk]):
        self.chunks = chunks
        self._tokenized_chunks = [_tokenize(_chunk_search_text(chunk)) for chunk in chunks]
        self._doc_freq = self._document_frequencies(self._tokenized_chunks)
        self._avg_len = (
            sum(len(tokens) for tokens in self._tokenized_chunks) / len(chunks)
            if chunks
            else 0.0
        )

    def retrieve(self, query: str, top_k: int = 4) -> List[PolicyChunk]:
        query_tokens = _tokenize(query)
        if not query_tokens or not self.chunks:
            return []

        scored = []
        for index, chunk_tokens in enumerate(self._tokenized_chunks):
            score = self._score(query_tokens, chunk_tokens, self.chunks[index])
            if score > 0:
                scored.append((score, index))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [self.chunks[index] for _, index in scored[:top_k]]

    def _score(
        self,
        query_tokens: List[str],
        chunk_tokens: List[str],
        chunk: PolicyChunk,
    ) -> float:
        counts = Counter(chunk_tokens)
        score = 0.0
        total_docs = len(self.chunks)
        chunk_len = len(chunk_tokens) or 1
        k1 = 1.4
        b = 0.75

        for token in query_tokens:
            freq = counts[token]
            if not freq:
                continue
            doc_freq = self._doc_freq.get(token, 0)
            idf = math.log(1 + (total_docs - doc_freq + 0.5) / (doc_freq + 0.5))
            denom = freq + k1 * (1 - b + b * chunk_len / (self._avg_len or 1))
            score += idf * ((freq * (k1 + 1)) / denom)

        score += _policy_hint_boost(query_tokens, chunk)
        return score

    @staticmethod
    def _document_frequencies(tokenized_chunks: Iterable[List[str]]) -> Dict[str, int]:
        freqs: Dict[str, int] = defaultdict(int)
        for tokens in tokenized_chunks:
            for token in set(tokens):
                freqs[token] += 1
        return dict(freqs)


def build_default_retriever(policy_dir: Union[str, Path] = "policy_docs") -> KeywordRetriever:
    documents = load_policy_documents(policy_dir)
    chunks = chunk_policy_documents(documents)
    return KeywordRetriever(chunks)


def _chunk_search_text(chunk: PolicyChunk) -> str:
    return " ".join(
        [
            chunk.document_name,
            chunk.section_heading,
            chunk.policy_id.replace("POLICY:", "").replace("_", " "),
            chunk.chunk_text,
        ]
    )


def _tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text.lower())


def _policy_hint_boost(query_tokens: List[str], chunk: PolicyChunk) -> float:
    query = set(query_tokens)
    policy_id = chunk.policy_id
    boost = 0.0

    if {"final", "sale"} <= query and policy_id == "POLICY:FINAL_SALE_NO_RETURNS":
        boost += 4.0
    if {"wrong", "size"} <= query and policy_id == "POLICY:RETURN_SHIPPING_CUSTOMER_REASONS":
        boost += 4.0
    if query & {"damaged", "defective", "cracked", "broken"} and policy_id == "POLICY:DAMAGE_WRONG_MISSING_REVIEW":
        boost += 4.0
    if query & {"gift", "receipt"} and policy_id in {
        "POLICY:GIFT_RETURN_REQUIREMENTS",
        "POLICY:GIFT_REFUND_STORE_CREDIT",
    }:
        boost += 3.0
    if query & {"exchange", "size", "color"} and policy_id == "POLICY:EXCHANGE_SIZE_COLOR_WINDOW":
        boost += 3.0
    if query & {"exception", "late", "supervisor"} and policy_id == "POLICY:ESCALATION_POLICY_EXCEPTIONS":
        boost += 4.0

    return boost
