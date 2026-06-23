# Product Requirements Document

## Product Goal

`return-policy-agent` is an eval-ready Streamlit application for answering customer return, refund, and exchange questions using a local return policy corpus. The app should help a customer understand whether an item is eligible for return, what outcome is available, what information is missing, and when a human support agent must review the case.

The product is designed for an Agentic AI / AI Evals course project. Part 1 focuses on a clean, inspectable application architecture and decision behavior. Part 2 will add LangSmith evaluations without requiring a major redesign.

## Primary Users

- Customers asking about returns, refunds, exchanges, restocking fees, damaged items, final sale items, shipping costs, or return windows.
- Course evaluators reviewing agent behavior, source citations, structured outputs, and escalation decisions.
- Developers extending the project with automated evals in Part 2.

## User Journey

1. A customer opens the Streamlit app.
2. The customer asks a natural-language question, such as "Can I return shoes I wore once?"
3. The agent determines whether the question is about a return, refund, exchange, or policy clarification.
4. The agent identifies required facts, such as purchase date, delivery date, product category, condition, order status, and reason for return.
5. If enough information is present, the agent retrieves relevant policy sections from the local corpus.
6. The agent produces a structured decision with an answer, eligibility status, reasoning, citations, required next steps, and escalation state.
7. If information is missing, the agent asks a targeted follow-up question instead of guessing.
8. If the policy requires manual review, the agent explains why and escalates.

## Core Requirements

- Answer only from the local policy corpus and the customer-provided case details.
- Produce a structured decision for every response.
- Cite policy sources with document names and section identifiers.
- Ask for missing information before making eligibility decisions.
- Escalate when the policy requires human judgment or when retrieved evidence is insufficient.
- Clearly distinguish policy-backed facts from assumptions.
- Avoid legal, financial, or operational claims not present in the corpus.
- Preserve a clean interface between agent logic, retrieval, policy schema, and UI so LangSmith evals can call the same core functions later.

## Out Of Scope For Part 1

- LangSmith eval implementation.
- Production authentication.
- Real order lookup or ecommerce platform integration.
- Payment processor integrations.
- Email, ticketing, or CRM automation.
- Vector database hosting outside the local project.
- Multi-tenant policy management.

## Success Criteria

- A customer can ask common return policy questions and receive grounded answers.
- The agent refuses to decide when required facts are missing.
- The agent cites the retrieved policy sections used in its reasoning.
- Escalation behavior is explicit and consistent.
- Structured outputs are stable enough to become eval targets in Part 2.
- The codebase can later expose testable functions for LangSmith datasets and evaluators.

## Risks

- The model may over-answer without enough customer information.
- Retrieval may surface a related but non-authoritative policy section.
- Policy conflicts may occur across documents.
- The UI may hide structured decision details that evals need.
- Future eval code may become tangled with app code if boundaries are not designed early.

## Non-Goals

The agent is not a replacement for customer support judgment. It should not approve refunds, modify orders, issue labels, or promise exceptions. It should provide policy-grounded guidance and identify when a human must intervene.
