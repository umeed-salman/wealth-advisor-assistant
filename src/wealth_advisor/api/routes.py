from __future__ import annotations

from fastapi import FastAPI, HTTPException

from wealth_advisor.config import get_settings
from wealth_advisor.models import AnalysisRequest, AnalysisResponse, ApprovalRequest, HealthResponse
from wealth_advisor.orchestrator import WealthAdvisorOrchestrator
from wealth_advisor.logging_config import configure_logging


orchestrator = WealthAdvisorOrchestrator()


def create_app(orchestrator_instance: WealthAdvisorOrchestrator | None = None) -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    active_orchestrator = orchestrator_instance or orchestrator
    app = FastAPI(title=settings.app_name, version=settings.app_version)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service=settings.app_name, version=settings.app_version)

    @app.post("/analysis", response_model=AnalysisResponse)
    def submit_analysis(payload: AnalysisRequest) -> AnalysisResponse:
        return active_orchestrator.submit(payload)

    @app.get("/analysis/{run_id}", response_model=AnalysisResponse)
    def get_analysis(run_id: str) -> AnalysisResponse:
        try:
            record = active_orchestrator.get_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="analysis run not found") from exc
        return AnalysisResponse(
            run_id=record.run_id,
            status=record.status,
            approval_state=record.approval_state,
            reviewed_by=record.reviewed_by,
            reviewer_notes=record.reviewer_notes,
            draft=record.draft,
            final_recommendation=record.final_recommendation,
            warnings=record.analysis.warnings if record.analysis else [],
            errors=record.errors,
        )

    @app.post("/analysis/{run_id}/approval", response_model=AnalysisResponse)
    def approve_analysis(run_id: str, payload: ApprovalRequest) -> AnalysisResponse:
        try:
            return active_orchestrator.approve(run_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="analysis run not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app
