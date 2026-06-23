from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


DecisionValue = Literal[
    "eligible_return",
    "not_eligible",
    "eligible_exchange",
    "ask_for_info",
    "escalate",
]

ReasonCode = Literal[
    "standard_30_day",
    "outside_return_window",
    "final_sale",
    "damaged_item",
    "wrong_item",
    "missing_item",
    "missing_order_number",
    "no_proof_of_purchase",
    "shipping_fee",
    "gift_return",
    "exception_request",
    "legal_threat",
    "fraud_concern",
    "unclear",
]

IntentValue = Literal[
    "return_request",
    "exchange_request",
    "refund_status",
    "damaged_item",
    "wrong_item",
    "missing_item",
    "shipping_fee",
    "gift_return",
    "policy_exception",
    "unclear",
]

RequestedResolution = Literal[
    "return",
    "exchange",
    "refund",
    "store_credit",
    "replacement",
    "unclear",
]


class PolicyDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    path: str
    text: str

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class PolicyChunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_name: str
    section_heading: str
    policy_id: str
    chunk_text: str
    source_citation: str

    def to_dict(self) -> Dict[str, str]:
        return self.model_dump()


class OrderContext(BaseModel):
    order_date: Optional[str] = None
    delivery_date: Optional[str] = None
    item_category: Optional[str] = None
    item_condition: Optional[str] = None
    final_sale: Optional[bool] = None
    order_value: Optional[float] = None
    proof_of_purchase: Optional[str] = None
    order_number: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "OrderContext":
        return cls.model_validate(data or {})

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class AgentDecision(BaseModel):
    decision: DecisionValue
    reason_code: ReasonCode
    missing_info: List[str] = Field(default_factory=list)
    escalate: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    policy_sections_used: List[str] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    decision_rationale: str = ""
    customer_answer: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class AgentTrace(BaseModel):
    raw_input: Dict[str, Any] = Field(default_factory=dict)
    input: Dict[str, Any]
    extracted_intent: Dict[str, Any] = Field(default_factory=dict)
    safety_precheck: Dict[str, Any] = Field(default_factory=dict)
    retrieval_query: str = ""
    retrieved_chunks: List[Dict[str, str]]
    structured_decision: Dict[str, Any] = Field(default_factory=dict)
    validator_result: Dict[str, Any] = Field(default_factory=dict)
    final_answer: str = ""
    decision: DecisionValue
    citations: List[str]
    citation_validation: Dict[str, Any] = Field(
        default_factory=lambda: {"valid": False, "errors": ["not_validated"]}
    )
    missing_info: List[str]
    step_latency: Dict[str, float] = Field(default_factory=dict)
    llm_models: Dict[str, Optional[str]] = Field(default_factory=dict)
    token_usage: Dict[str, Any] = Field(default_factory=dict)
    latency: float
    errors: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ExtractedFacts(BaseModel):
    days_since_delivery: Optional[int] = None
    item_condition: Optional[str] = None
    final_sale: Optional[bool] = None
    proof_of_purchase: Optional[str] = None
    order_number_present: Optional[bool] = None
    order_value: Optional[float] = None
    issue_type: Optional[str] = None


class IntentExtraction(BaseModel):
    intent: IntentValue = "unclear"
    requested_resolution: RequestedResolution = "unclear"
    extracted_facts: ExtractedFacts = Field(default_factory=ExtractedFacts)
    missing_info: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    requires_policy_lookup: bool = True
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class SafetyCheckResult(BaseModel):
    escalate: bool = False
    refuse: bool = False
    reason_code: Optional[ReasonCode] = None
    risk_flags: List[str] = Field(default_factory=list)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class DecisionValidationResult(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    corrected: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
