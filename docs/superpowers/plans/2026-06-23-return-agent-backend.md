# Return Agent Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the eval-ready backend for the Northstar Commerce Return Policy Agent.

**Architecture:** The backend is split into local policy loading, heading-aware chunking, keyword retrieval, deterministic decision rules, citation formatting, and tracing. Streamlit remains a thin shell over the backend and is intentionally unpolished in this phase.

**Tech Stack:** Python standard library, pytest, Streamlit for the minimal app shell.

---

### Task 1: Tests First

**Files:**
- Create: `tests/test_policy_loader.py`
- Create: `tests/test_retriever.py`
- Create: `tests/test_agent_decisions.py`

- [x] Write tests for policy loading, retrieval, and required agent decisions.
- [x] Run tests and verify they fail because backend modules are missing.

### Task 2: Policy Corpus Backend

**Files:**
- Create: `src/return_agent/models.py`
- Create: `src/return_agent/policy_loader.py`
- Create: `src/return_agent/chunker.py`
- Create: `src/return_agent/citations.py`
- Create: `src/return_agent/retriever.py`

- [ ] Implement markdown loading from `policy_docs/`.
- [ ] Chunk documents by policy-heading sections.
- [ ] Preserve document name, section heading, policy ID, chunk text, and source citation.
- [ ] Implement deterministic keyword retrieval with no external service dependency.

### Task 3: Agent And Trace

**Files:**
- Create: `src/return_agent/agent.py`
- Create: `src/return_agent/tracing.py`
- Create: `src/return_agent/prompts.py`
- Create: `src/return_agent/utils.py`

- [ ] Implement structured decision output.
- [ ] Add missing-info, escalation, final-sale, return, exchange, shipping-fee, and gift-return rules.
- [ ] Include citations in every answer.
- [ ] Capture input, retrieved chunks, decision, citations, missing info, latency, and errors.

### Task 4: Project Shell

**Files:**
- Create: `src/return_agent/__init__.py`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `app.py`

- [ ] Add package exports.
- [ ] Add minimal dependencies.
- [ ] Add a simple local Streamlit shell without polished UI.

### Task 5: Verification

**Files:**
- Modify backend files as needed.

- [ ] Run `python3 -m pytest`.
- [ ] Fix failures.
- [ ] Re-run tests until the suite passes.
