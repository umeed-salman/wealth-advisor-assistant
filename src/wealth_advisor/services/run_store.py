from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from wealth_advisor.models import (
    AdvisoryDraft,
    AdvisoryRunRecord,
    AdvisoryRunStatus,
    AnalysisResult,
    ApprovalDecision,
    ClientFinancialInput,
    CRMContext,
    Recommendation,
)


class RunStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._runs: dict[str, AdvisoryRunRecord] = {}

    def create(self, client: ClientFinancialInput) -> AdvisoryRunRecord:
        now = datetime.now(timezone.utc)
        normalized_client = ClientFinancialInput.model_validate(client.model_dump(mode="python"))
        run = AdvisoryRunRecord(
            run_id=str(uuid4()),
            client_id=normalized_client.client_id,
            created_at=now,
            updated_at=now,
            status=AdvisoryRunStatus.running,
            input=normalized_client,
        )
        with self._lock:
            self._runs[run.run_id] = run
        return run

    def get(self, run_id: str) -> AdvisoryRunRecord:
        with self._lock:
            return self._runs[run_id]

    def update(self, run_id: str, **changes: object) -> AdvisoryRunRecord:
        with self._lock:
            run = self._runs[run_id]
            updated = run.model_copy(update={**changes, "updated_at": datetime.now(timezone.utc)})
            self._runs[run_id] = updated
            return updated

    def set_analysis(self, run_id: str, crm_context: CRMContext, analysis: AnalysisResult, draft: AdvisoryDraft) -> AdvisoryRunRecord:
        return self.update(
            run_id,
            crm_context=crm_context,
            analysis=analysis,
            draft=draft,
            status=AdvisoryRunStatus.awaiting_approval,
            approval_state=ApprovalDecision.pending,
        )

    def approve(
        self,
        run_id: str,
        recommendation: Recommendation,
        notes: str | None = None,
        reviewer: str | None = None,
    ) -> AdvisoryRunRecord:
        return self.update(
            run_id,
            final_recommendation=recommendation,
            approval_state=ApprovalDecision.approved,
            status=AdvisoryRunStatus.approved,
            reviewed_by=reviewer,
            reviewer_notes=notes,
        )

    def reject(self, run_id: str, notes: str | None = None, reviewer: str | None = None) -> AdvisoryRunRecord:
        return self.update(
            run_id,
            approval_state=ApprovalDecision.rejected,
            status=AdvisoryRunStatus.rejected,
            reviewed_by=reviewer,
            reviewer_notes=notes,
        )

    def override(
        self,
        run_id: str,
        recommendation: Recommendation,
        notes: str | None = None,
        reviewer: str | None = None,
    ) -> AdvisoryRunRecord:
        return self.update(
            run_id,
            final_recommendation=recommendation,
            approval_state=ApprovalDecision.overridden,
            status=AdvisoryRunStatus.approved,
            reviewed_by=reviewer,
            reviewer_notes=notes,
        )
