from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st

ROOT = Path(__file__).parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from return_agent.agent import ReturnPolicyAgent
from return_agent.answer_generator import OpenAIFinalAnswerGenerator
from return_agent.decision_agent import OpenAIPolicyDecisionAgent
from return_agent.intent_extractor import OpenAIIntentExtractor
from return_agent.openai_client import build_openai_client, load_openai_settings


DECISION_LABELS = {
    "eligible_return": "Eligible return",
    "not_eligible": "Not eligible",
    "eligible_exchange": "Eligible exchange",
    "ask_for_info": "Needs more information",
    "escalate": "Escalate",
}


def build_order_context() -> Dict[str, Any]:
    with st.expander("Optional order context", expanded=True):
        left, right = st.columns(2)
        with left:
            delivery_date = st.date_input("Delivery date", value=None)
            order_number_present = st.checkbox("Order number present?")
            item_condition = st.selectbox(
                "Item condition",
                [
                    "",
                    "unused, unworn, unwashed, original packaging",
                    "unused, original packaging",
                    "worn",
                    "washed",
                    "damaged on arrival",
                    "missing packaging",
                ],
            )
            item_category = st.text_input("Item category", placeholder="jacket, shoes, gift card")
        with right:
            final_sale = st.selectbox("Final sale?", ["Unknown", "No", "Yes"])
            proof_of_purchase = st.checkbox("Proof of purchase?")
            order_value = st.number_input(
                "Order value",
                min_value=0.0,
                value=0.0,
                step=5.0,
                format="%.2f",
            )

    proof = None
    if order_number_present:
        proof = "order number provided"
    elif proof_of_purchase:
        proof = "proof of purchase provided"

    return {
        "order_date": None,
        "delivery_date": delivery_date.isoformat() if delivery_date else None,
        "item_category": item_category.strip() or None,
        "item_condition": item_condition or None,
        "final_sale": {"Yes": True, "No": False}.get(final_sale),
        "order_value": order_value if order_value > 0 else None,
        "proof_of_purchase": proof,
    }


def render_decision_card(result: Dict[str, Any]) -> None:
    decision = result.get("decision", "unknown")
    escalation = result.get("escalate", False)
    confidence = float(result.get("confidence", 0.0) or 0.0)

    st.subheader("Structured Decision")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Decision", DECISION_LABELS.get(decision, decision))
    col2.metric("Reason code", result.get("reason_code", "unclear"))
    col3.metric("Escalation", "Yes" if escalation else "No")
    col4.metric("Confidence", f"{confidence:.2f}")

    missing = result.get("missing_info") or []
    if missing:
        st.warning("Missing info: " + ", ".join(missing))
    else:
        st.success("No missing information required for this decision.")


def render_answer(result: Dict[str, Any]) -> None:
    st.subheader("Customer-Facing Answer")
    st.write(result.get("customer_answer") or "No customer-facing answer was produced.")


def render_citations(result: Dict[str, Any]) -> None:
    st.subheader("Citations")
    citations = result.get("citations") or []
    if not citations:
        st.info("No citations returned.")
        return
    for citation in citations:
        st.markdown(f"- `{citation}`")


def render_policy_evidence(trace: Optional[Dict[str, Any]]) -> None:
    with st.expander("Policy Evidence", expanded=False):
        chunks = (trace or {}).get("retrieved_chunks") or []
        if not chunks:
            st.info("Run the agent to see retrieved policy chunks.")
            return

        for index, chunk in enumerate(chunks, start=1):
            st.markdown(
                f"**{index}. {chunk['document_name']} "
                f"[{chunk['policy_id']}] - {chunk['section_heading']}**"
            )
            st.caption(chunk["source_citation"])
            st.write(chunk["chunk_text"])
            st.divider()


def render_trace(trace: Optional[Dict[str, Any]]) -> None:
    with st.expander("Agent Trace", expanded=False):
        if not trace:
            st.info("Run the agent to see trace details.")
            return
        st.json(trace)


@st.cache_resource
def get_agent(policy_dir: str, use_openai_lm: bool) -> ReturnPolicyAgent:
    intent_extractor = None
    decision_agent = None
    answer_generator = None
    if use_openai_lm:
        settings = load_openai_settings()
        client = build_openai_client(settings.api_key)
        intent_extractor = OpenAIIntentExtractor(client=client, model=settings.model)
        decision_agent = OpenAIPolicyDecisionAgent(client=client, model=settings.model)
        answer_generator = OpenAIFinalAnswerGenerator(client=client, model=settings.model)
    return ReturnPolicyAgent.from_policy_dir(
        policy_dir,
        intent_extractor=intent_extractor,
        decision_agent=decision_agent,
        answer_generator=answer_generator,
    )


def main() -> None:
    st.set_page_config(
        page_title="Northstar Commerce Return Policy Assistant",
        page_icon="N",
        layout="wide",
    )

    st.title("Northstar Commerce Return Policy Assistant")
    st.caption("Local RAG-backed return, refund, exchange, and escalation decisions.")

    policy_dir = os.getenv("POLICY_DOCS_PATH", "policy_docs")
    openai_settings = load_openai_settings()
    use_openai_lm = bool(openai_settings.enabled and openai_settings.api_key)
    agent = get_agent(policy_dir, use_openai_lm)

    if use_openai_lm:
        st.caption(f"OpenAI answer generation enabled with `{openai_settings.model}`.")
    else:
        st.caption("OpenAI answer generation disabled; using deterministic fallback answers.")

    order_context = build_order_context()

    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "last_trace" not in st.session_state:
        st.session_state.last_trace = None
    if "last_question" not in st.session_state:
        st.session_state.last_question = None

    prompt = st.chat_input("Ask a return, refund, exchange, or shipping-fee question")
    if prompt:
        st.session_state.last_question = prompt
        st.session_state.last_result = agent.run(
            {
                "customer_message": prompt,
                "order_context": order_context,
            }
        )
        st.session_state.last_trace = (
            agent.last_trace.to_dict() if agent.last_trace else None
        )

    if st.session_state.last_question:
        with st.chat_message("user"):
            st.write(st.session_state.last_question)
        with st.chat_message("assistant"):
            st.write(
                (st.session_state.last_result or {}).get(
                    "customer_answer",
                    "No answer has been generated yet.",
                )
            )
    else:
        st.info("Ask a question below to generate a structured policy decision.")

    if st.session_state.last_result:
        render_decision_card(st.session_state.last_result)
        render_answer(st.session_state.last_result)
        render_citations(st.session_state.last_result)

    render_policy_evidence(st.session_state.last_trace)
    render_trace(st.session_state.last_trace)


if __name__ == "__main__":
    main()
