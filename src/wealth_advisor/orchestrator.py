from __future__ import annotations

import logging
from dataclasses import dataclass

from langgraph.graph import END, StateGraph

from wealth_advisor.agents.analyzer import AnalyzerAgent
from wealth_advisor.agents.data_fetcher import DataFetcherAgent
from wealth_advisor.config import Settings, get_settings
from wealth_advisor.exceptions import ToolError
from wealth_advisor.models import (
    AdvisoryDraft,
    AdvisoryRunRecord,
    AnalysisResponse,
    ApprovalDecision,
    ApprovalRequest,
    ClientFinancialInput,
    ClientProfile,
    Recommendation,
)
from wealth_advisor.services.artifacts import ArtifactStore
from wealth_advisor.services.memory import MemoryStore
from wealth_advisor.services.run_store import RunStore
from wealth_advisor.tools.mock_crm import MockCRMTool


@dataclass
class OrchestratorDependencies:
    settings: Settings
    run_store: RunStore
    memory_store: MemoryStore
    artifact_store: ArtifactStore
    data_fetcher: DataFetcherAgent
    analyzer: AnalyzerAgent


class WealthAdvisorOrchestrator:
    def __init__(self, dependencies: OrchestratorDependencies | None = None) -> None:
        settings = get_settings() if dependencies is None else dependencies.settings
        run_store = RunStore() if dependencies is None else dependencies.run_store
        memory_store = MemoryStore(settings.memory_dir) if dependencies is None else dependencies.memory_store
        artifact_store = ArtifactStore(settings.output_dir) if dependencies is None else dependencies.artifact_store
        data_fetcher = DataFetcherAgent(MockCRMTool(settings)) if dependencies is None else dependencies.data_fetcher
        analyzer = AnalyzerAgent() if dependencies is None else dependencies.analyzer
        self._dependencies = OrchestratorDependencies(
            settings=settings,
            run_store=run_store,
            memory_store=memory_store,
            artifact_store=artifact_store,
            data_fetcher=data_fetcher,
            analyzer=analyzer,
        )
        self._logger = logging.getLogger(self.__class__.__name__)
        self._graph = self._build_graph()

    @property
    def runs(self) -> RunStore:
        return self._dependencies.run_store

    def submit(self, client: ClientFinancialInput) -> AnalysisResponse:
        run = self._dependencies.run_store.create(client)
        final_state = self._graph.invoke({"run_id": run.run_id, "client": client, "warnings": [], "errors": []})
        record = self._dependencies.run_store.get(run.run_id)
        warnings = list(final_state.get("warnings", []))
        if record.analysis:
            warnings.extend(record.analysis.warnings)
        response = AnalysisResponse(
            run_id=record.run_id,
            status=record.status,
            approval_state=record.approval_state,
            reviewed_by=record.reviewed_by,
            reviewer_notes=record.reviewer_notes,
            draft=record.draft,
            final_recommendation=record.final_recommendation,
            warnings=warnings,
            errors=final_state.get("errors", []),
        )
        self._dependencies.artifact_store.write_run(record)
        if record.analysis and record.draft:
            self._dependencies.memory_store.append_summary(
                run_id=record.run_id,
                client_id=record.client_id,
                analysis=record.analysis,
                recommendation_text=record.draft.recommendation.action,
            )
        return response

    def approve(self, run_id: str, request: ApprovalRequest) -> AnalysisResponse:
        record = self._dependencies.run_store.get(run_id)
        if record.draft is None:
            raise ValueError("run does not have a draft to approve")

        if request.decision == "approved":
            approved = self._dependencies.run_store.approve(run_id, record.draft.recommendation, request.notes, request.reviewer)
        elif request.decision == "rejected":
            approved = self._dependencies.run_store.reject(run_id, request.notes, request.reviewer)
        else:
            recommendation = record.draft.recommendation.model_copy(
                update={
                    "action": request.override_action or record.draft.recommendation.action,
                    "rationale": request.override_rationale or record.draft.recommendation.rationale,
                    "priority": request.override_priority or record.draft.recommendation.priority,
                    "next_steps": request.override_next_steps or record.draft.recommendation.next_steps,
                    "risk_flags": request.override_risk_flags or record.draft.recommendation.risk_flags,
                }
            )
            approved = self._dependencies.run_store.override(run_id, recommendation, request.notes, request.reviewer)

        response = AnalysisResponse(
            run_id=approved.run_id,
            status=approved.status,
            approval_state=approved.approval_state,
            reviewed_by=approved.reviewed_by,
            reviewer_notes=approved.reviewer_notes,
            draft=approved.draft,
            final_recommendation=approved.final_recommendation,
            warnings=approved.analysis.warnings if approved.analysis else [],
            errors=approved.errors,
        )
        self._dependencies.artifact_store.write_run(approved)
        return response

    def get_run(self, run_id: str) -> AdvisoryRunRecord:
        return self._dependencies.run_store.get(run_id)

    def _build_graph(self):
        graph = StateGraph(dict)
        graph.add_node("fetch_context", self._fetch_context)
        graph.add_node("analyze", self._analyze)
        graph.add_node("approve_gate", self._approve_gate)
        graph.set_entry_point("fetch_context")
        graph.add_edge("fetch_context", "analyze")
        graph.add_edge("analyze", "approve_gate")
        graph.add_edge("approve_gate", END)
        return graph.compile()

    def _fetch_context(self, state: dict) -> dict:
        client = state["client"]
        run_id = state["run_id"]
        try:
            profile = self._dependencies.data_fetcher.run(client)
            self._dependencies.run_store.update(run_id, crm_context=profile.crm)
            return {**state, "profile": profile, "warnings": state.get("warnings", []), "errors": state.get("errors", [])}
        except ToolError as exc:
            message = str(exc)
            self._logger.exception("data fetch failed run_id=%s", run_id)
            state["warnings"].append(message)
            profile = ClientProfile(
                client=client,
                crm=None,
                monthly_cashflow=client.monthly_income - client.monthly_expenses,
                savings_rate=(client.monthly_income - client.monthly_expenses) / client.monthly_income if client.monthly_income else 0.0,
                debt_to_income=client.liabilities / (client.monthly_income * 12) if client.monthly_income else 0.0,
                emergency_fund_months=client.liquid_assets / client.monthly_expenses if client.monthly_expenses else 0.0,
            )
            self._dependencies.run_store.update(run_id, crm_context=None, errors=[message])
            return {**state, "profile": profile, "warnings": state["warnings"], "errors": state.get("errors", [])}

    def _analyze(self, state: dict) -> dict:
        profile = state["profile"]
        run_id = state["run_id"]
        try:
            analysis, draft = self._dependencies.analyzer.run(profile)
            record = self._dependencies.run_store.set_analysis(run_id, profile.crm, analysis, draft)
            return {**state, "analysis": analysis, "draft": draft, "record": record}
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("analysis failed run_id=%s", run_id)
            warning = f"Analysis failed: {exc}"
            state["errors"].append(warning)
            fallback_analysis = self._build_fallback_analysis(profile)
            fallback_draft = AdvisoryDraft(
                summary="Fallback analysis produced due to an internal error.",
                analysis=fallback_analysis,
                recommendation=fallback_analysis.recommendations[0],
                requires_approval=True,
            )
            self._dependencies.run_store.set_analysis(run_id, profile.crm, fallback_analysis, fallback_draft)
            return {**state, "analysis": fallback_analysis, "draft": fallback_draft}

    def _approve_gate(self, state: dict) -> dict:
        run_id = state["run_id"]
        record = self._dependencies.run_store.get(run_id)
        if record.draft is None or record.analysis is None:
            return state

        if self._dependencies.settings.approval_mode == "auto":
            approved = self._dependencies.run_store.approve(run_id, record.draft.recommendation, "auto-approved")
            self._store_memory(approved)
            return {**state, "record": approved}

        self._dependencies.run_store.update(run_id, status=record.status)
        return {**state, "record": record}

    def _build_fallback_analysis(self, profile) -> object:
        from wealth_advisor.models import AnalysisResult, Recommendation

        recommendation = Recommendation(
            action="Request manual advisor review",
            rationale="The analysis engine encountered an unexpected error.",
            priority="high",
            next_steps=["Review the client record", "Retry analysis after remediation"],
            risk_flags=["analysis_error"],
        )
        return AnalysisResult(
            cashflow=profile.monthly_cashflow or 0.0,
            savings_rate=profile.savings_rate or 0.0,
            debt_to_income=profile.debt_to_income or 0.0,
            emergency_fund_months=profile.emergency_fund_months or 0.0,
            risk_score=0.85,
            anomalies=[],
            insights=["Fallback analysis path was triggered."],
            recommendations=[recommendation],
            fallback_used=True,
            warnings=["Used fallback analysis path due to an internal failure."],
        )

    def _store_memory(self, record: AdvisoryRunRecord) -> None:
        if record.analysis and record.final_recommendation:
            self._dependencies.memory_store.append_summary(
                run_id=record.run_id,
                client_id=record.client_id,
                analysis=record.analysis,
                recommendation_text=record.final_recommendation.action,
            )
