# RAG Pipeline Specification

## Goal

The RAG pipeline grounds return policy answers in a local corpus of policy documents. Retrieval should provide focused policy sections that the agent can cite directly and use to make structured decisions.

## Corpus Design

Policy documents should live in a local directory, for example:

```text
data/policies/
```

Each policy document should contain clear headings and stable section identifiers. Markdown is recommended for Part 1 because it is easy to inspect, chunk, cite, and update.

Example source files:

```text
data/policies/standard_return_policy.md
data/policies/refund_policy.md
data/policies/exchange_policy.md
data/policies/exceptions_and_restricted_items.md
data/policies/damaged_defective_items.md
```

## Document Metadata

Each chunk should preserve:

- `source_id`
- `source_title`
- `source_path`
- `section_id`
- `section_heading`
- `policy_type`
- `effective_date`, if known
- `jurisdiction`, if relevant
- `chunk_text`

## Chunking Strategy

Chunk policy documents by section rather than fixed token windows whenever possible. A policy section is the natural citation unit and reduces the chance of mixing unrelated rules.

Recommended chunk rules:

- Split on Markdown headings.
- Keep the heading with each chunk.
- Target 300 to 800 tokens per chunk.
- Merge very small subsections with their parent section when needed.
- Preserve source path and heading hierarchy.
- Avoid splitting lists of exceptions across chunks.

## Indexing Strategy

Part 1 can use a local vector index or lightweight local retrieval abstraction. The important design constraint is that retrieval should be wrapped behind an interface that can later be tested independently.

Suggested retrieval interface:

```text
retrieve_policy_context(query, filters=None, top_k=4) -> list[PolicyChunk]
```

The UI should not call the vector store directly. The agent should request policy context through the retrieval layer.

## Retrieval Flow

1. Normalize the user question and extracted case facts.
2. Build a retrieval query that includes the customer question and relevant structured facts.
3. Retrieve top policy chunks.
4. Optionally rerank or filter chunks by policy type.
5. Pass only the selected chunks to the agent decision step.
6. Require the final answer to cite chunks that directly support the decision.

## Source Citation Format

The agent should cite policy sections in a stable format:

```text
[source_title, section_id: section_heading]
```

Example:

```text
[Standard Return Policy, 2.1: 30-Day Return Window]
```

Each structured citation should also include:

- `source_path`
- `section_id`
- `section_heading`
- `supporting_text`

## Retrieval Quality Requirements

- Top chunks should be directly relevant to the decision.
- Exception sections should be retrieved when the item category or condition suggests restrictions.
- General return window rules should not override specific exception rules.
- If retrieved context is weak, the agent should escalate instead of guessing.
- Retrieval results should be logged in a structured way for future evals.

## Error Handling

- Missing corpus directory: show a setup error in the app and return no decision.
- Empty index: show an actionable error and prevent unsupported answers.
- Index build failure: display the failure in developer-friendly logs and a safe customer-facing message.
- No relevant chunks: return `escalate` for decision requests or a limited explanation for general questions.

## Future LangSmith Readiness

Part 2 evals should be able to inspect:

- Original query.
- Extracted facts.
- Retrieved chunks.
- Final cited chunks.
- Decision status.
- Whether the cited chunks actually support the answer.

For that reason, retrieval should return structured chunk objects rather than plain strings.
