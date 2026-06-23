# Loom Walkthrough Script

## 2-3 Minute Script

Hi, this is my Week 4 evaluation walkthrough for the Northstar Commerce Return Policy Agent.

The agent helps customers with return, refund, exchange, gift-return, and shipping-fee questions. It uses local markdown policy documents, retrieves relevant policy sections, makes a structured decision, cites the policy evidence, asks for missing information when needed, and escalates risky cases such as legal threats, high-value missing-proof refunds, prompt injection, and policy exceptions.

For evaluation, I tested the backend agent directly rather than the Streamlit UI. The target was `ReturnPolicyAgent.run`, which returns the decision, reason code, missing information, escalation flag, citations, final answer, and trace data.

The golden dataset has 40 cases: 20 happy paths, 12 edge cases, 6 known failures, and 2 adversarial examples. The labels check decision accuracy, reason-code accuracy, missing-info F1, escalation accuracy, citation coverage, policy-section recall, and schema validity. LangSmith tracing support is implemented for the full run and each major step. I have a LangSmith baseline summary artifact, but I am leaving the actual LangSmith experiment links as placeholders: `[baseline link]` and `[post-improvement link]`.

The baseline showed the agent was strong on citation and schema validity, both at 100%, but weak on edge-case reasoning. Decision accuracy was 62.5%, reason-code accuracy was 65%, missing-info F1 was 66.25%, escalation accuracy was 87.5%, and policy-section recall was 60%. The biggest failure clusters were incorrect eligibility decisions, incorrect reason codes, missed missing-info requests, missed escalations, and missed supporting policy sections.

I then made targeted improvements only. I fixed deterministic decision and reason priority for edge cases, canonicalized missing-info handling, and improved multi-policy retrieval and citation recall. I did not change the dataset or hide failures.

After the improvements, local evaluation reached 100% on decision accuracy, reason-code accuracy, missing-info F1, escalation accuracy, citation coverage, policy-section recall, and schema validity across all 40 cases. Average local latency stayed around one millisecond because this was the deterministic local run. The available LangSmith baseline artifact also reports 100% faithfulness judge score, but a separate LangSmith post-improvement artifact was not available for a measured LangSmith delta.

The remaining limitations are important: p95 latency, cost per run, and a paired LangSmith post-improvement comparison still need to be captured. Also, because the local golden set is now fully passing, I would add a fresh holdout set before claiming production readiness. Next, I would run the OpenAI-backed flow in LangSmith, review any faithfulness failures, monitor cost and latency, and keep adding real-world failures into the golden dataset.
