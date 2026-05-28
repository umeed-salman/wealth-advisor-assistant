from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    debit = "debit"
    credit = "credit"


class Transaction(BaseModel):
    transaction_id: str
    posted_date: date
    amount: float = Field(gt=0)
    transaction_type: TransactionType = TransactionType.debit
    category: str
    merchant: str
    description: str | None = None


class ClientFinancialInput(BaseModel):
    client_id: str
    full_name: str
    age: int = Field(ge=18)
    monthly_income: float = Field(ge=0)
    monthly_expenses: float = Field(ge=0)
    liquid_assets: float = Field(ge=0)
    liabilities: float = Field(ge=0)
    investment_assets: float = Field(ge=0, default=0)
    risk_preference: Literal["conservative", "moderate", "growth"] = "moderate"
    transactions: list[Transaction] = Field(default_factory=list)


class CRMContext(BaseModel):
    client_id: str
    relationship_status: str
    household_size: int | None = None
    risk_tolerance: str | None = None
    lifecycle_stage: str | None = None
    last_meeting_summary: str | None = None
    advisor_notes: list[str] = Field(default_factory=list)
    open_tasks: list[str] = Field(default_factory=list)


class ClientProfile(BaseModel):
    client: ClientFinancialInput
    crm: CRMContext | None = None
    monthly_cashflow: float | None = None
    savings_rate: float | None = None
    debt_to_income: float | None = None
    emergency_fund_months: float | None = None


class AnomalyFinding(BaseModel):
    severity: Literal["low", "medium", "high"]
    title: str
    details: str
    metric_name: str
    observed_value: float | int | None = None
    threshold: float | int | None = None


class Recommendation(BaseModel):
    action: str
    rationale: str
    priority: Literal["low", "medium", "high"]
    next_steps: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class LLMAdvisoryOutput(BaseModel):
    summary: str
    key_insights: list[str] = Field(default_factory=list)
    recommendation_action: str
    recommendation_rationale: str
    recommendation_priority: Literal["low", "medium", "high"]
    next_steps: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    cashflow: float
    savings_rate: float
    debt_to_income: float
    emergency_fund_months: float
    risk_score: float
    anomalies: list[AnomalyFinding] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    fallback_used: bool = False
    warnings: list[str] = Field(default_factory=list)


class ApprovalDecision(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    overridden = "overridden"


class AdvisoryDraft(BaseModel):
    summary: str
    analysis: AnalysisResult
    recommendation: Recommendation
    requires_approval: bool = True


class AdvisoryRunStatus(str, Enum):
    running = "running"
    awaiting_approval = "awaiting_approval"
    approved = "approved"
    rejected = "rejected"
    failed = "failed"


class AdvisoryRunRecord(BaseModel):
    run_id: str
    client_id: str
    created_at: datetime
    updated_at: datetime
    status: AdvisoryRunStatus
    approval_state: ApprovalDecision = ApprovalDecision.pending
    reviewed_by: str | None = None
    reviewer_notes: str | None = None
    input: ClientFinancialInput
    crm_context: CRMContext | None = None
    analysis: AnalysisResult | None = None
    draft: AdvisoryDraft | None = None
    final_recommendation: Recommendation | None = None
    errors: list[str] = Field(default_factory=list)


class AnalysisRequest(ClientFinancialInput):
    pass


class ApprovalRequest(BaseModel):
    decision: Literal["approved", "rejected", "overridden"]
    reviewer: str = "advisor"
    notes: str | None = None
    override_action: str | None = None
    override_rationale: str | None = None
    override_priority: Literal["low", "medium", "high"] | None = None
    override_next_steps: list[str] | None = None
    override_risk_flags: list[str] | None = None


class AnalysisResponse(BaseModel):
    run_id: str
    status: AdvisoryRunStatus
    approval_state: ApprovalDecision
    reviewed_by: str | None = None
    reviewer_notes: str | None = None
    draft: AdvisoryDraft | None = None
    final_recommendation: Recommendation | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class MemoryEntry(BaseModel):
    run_id: str
    client_id: str
    summary: str
    anomalies: list[str] = Field(default_factory=list)
    recommendation: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
