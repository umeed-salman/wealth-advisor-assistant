from __future__ import annotations

import json
import logging

from wealth_advisor.config import Settings, get_settings
from wealth_advisor.exceptions import ToolError
from wealth_advisor.models import AdvisoryDraft, AnalysisResult, ClientProfile, LLMAdvisoryOutput, Recommendation
from wealth_advisor.services.llm import AdvisorLLM, LiteLLMAdvisorLLM
from wealth_advisor.tools.financial_analysis import (
    calculate_cashflow,
    calculate_debt_to_income,
    calculate_emergency_fund_months,
    calculate_savings_rate,
    detect_anomalies,
    derive_recommendation,
)


class AnalyzerAgent:
    def __init__(self, advisor_llm: AdvisorLLM | None = None, settings: Settings | None = None) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)
        self._settings = settings or get_settings()
        self._uses_fallback_llm = False
        self._advisor_llm = advisor_llm or self._build_default_llm()

    def run(self, profile: ClientProfile) -> tuple[AnalysisResult, AdvisoryDraft]:
        client = profile.client
        self._logger.info("analyzing client client_id=%s", client.client_id)

        cashflow = calculate_cashflow(client)
        savings_rate = calculate_savings_rate(client, cashflow)
        debt_to_income = calculate_debt_to_income(client)
        emergency_fund_months = calculate_emergency_fund_months(client)
        anomalies = detect_anomalies(client)

        risk_score = self._score_risk(cashflow, savings_rate, debt_to_income, emergency_fund_months, anomalies)
        fallback_recommendation = derive_recommendation(client, cashflow, savings_rate, debt_to_income, emergency_fund_months, anomalies)

        insights = self._build_insights(cashflow, savings_rate, debt_to_income, emergency_fund_months, anomalies)
        warnings = []
        if profile.crm and profile.crm.advisor_notes:
            warnings.extend(profile.crm.advisor_notes)

        llm_output, llm_warnings = self._generate_llm_advice(
            profile=profile,
            cashflow=cashflow,
            savings_rate=savings_rate,
            debt_to_income=debt_to_income,
            emergency_fund_months=emergency_fund_months,
            anomalies=anomalies,
            fallback_recommendation=fallback_recommendation,
            warnings=warnings,
        )
        warnings.extend(llm_warnings)

        recommendation = Recommendation(
            action=llm_output.recommendation_action,
            rationale=llm_output.recommendation_rationale,
            priority=llm_output.recommendation_priority,
            next_steps=llm_output.next_steps,
            risk_flags=llm_output.risk_flags,
        )
        if not recommendation.action:
            recommendation = fallback_recommendation

        analysis = AnalysisResult(
            cashflow=cashflow,
            savings_rate=savings_rate,
            debt_to_income=debt_to_income,
            emergency_fund_months=emergency_fund_months,
            risk_score=risk_score,
            anomalies=anomalies,
            insights=llm_output.key_insights or insights,
            recommendations=[recommendation],
            fallback_used=self._uses_fallback_llm or bool(llm_warnings),
            warnings=warnings,
        )

        draft = AdvisoryDraft(
            summary=llm_output.summary or "; ".join((llm_output.key_insights or insights)[:2]) or "No notable signals detected.",
            analysis=analysis,
            recommendation=recommendation,
            requires_approval=True,
        )
        return analysis, draft

    def _build_default_llm(self) -> AdvisorLLM:
        try:
            return LiteLLMAdvisorLLM(self._settings)
        except ToolError as exc:
            self._uses_fallback_llm = True
            self._logger.warning("LLM backend unavailable, falling back to deterministic recommendation: %s", exc)

            class _FallbackAdvisorLLM:
                def generate_advice(self, analysis_context: str) -> LLMAdvisoryOutput:
                    return LLMAdvisoryOutput(
                        summary="Fallback advisory summary generated because the LLM could not be reached.",
                        key_insights=[],
                        recommendation_action="Request manual advisor review",
                        recommendation_rationale="The LLM service was unavailable, so the system fell back to a conservative internal recommendation.",
                        recommendation_priority="high",
                        next_steps=["Review the client record", "Retry after restoring the LLM service"],
                        risk_flags=["llm_unavailable"],
                    )

            return _FallbackAdvisorLLM()

    def _generate_llm_advice(
        self,
        profile: ClientProfile,
        cashflow: float,
        savings_rate: float,
        debt_to_income: float,
        emergency_fund_months: float,
        anomalies: list,
        fallback_recommendation: Recommendation,
        warnings: list[str],
    ) -> tuple[LLMAdvisoryOutput, list[str]]:
        context = self._build_analysis_context(
            profile=profile,
            cashflow=cashflow,
            savings_rate=savings_rate,
            debt_to_income=debt_to_income,
            emergency_fund_months=emergency_fund_months,
            anomalies=anomalies,
            fallback_recommendation=fallback_recommendation,
            warnings=warnings,
        )
        try:
            return self._advisor_llm.generate_advice(context), []
        except ToolError as exc:
            self._logger.exception("LLM advisory generation failed client_id=%s", profile.client.client_id)
            return (
                LLMAdvisoryOutput(
                    summary="Fallback advisory summary generated after an LLM failure.",
                    key_insights=self._build_insights(cashflow, savings_rate, debt_to_income, emergency_fund_months, anomalies),
                    recommendation_action=fallback_recommendation.action,
                    recommendation_rationale=fallback_recommendation.rationale,
                    recommendation_priority=fallback_recommendation.priority,
                    next_steps=fallback_recommendation.next_steps,
                    risk_flags=fallback_recommendation.risk_flags,
                ),
                [str(exc)],
            )

    def _build_analysis_context(
        self,
        profile: ClientProfile,
        cashflow: float,
        savings_rate: float,
        debt_to_income: float,
        emergency_fund_months: float,
        anomalies: list,
        fallback_recommendation: Recommendation,
        warnings: list[str],
    ) -> str:
        crm_summary = profile.crm.model_dump() if profile.crm else None
        payload = {
            "client": profile.client.model_dump(),
            "crm_context": crm_summary,
            "metrics": {
                "cashflow": cashflow,
                "savings_rate": savings_rate,
                "debt_to_income": debt_to_income,
                "emergency_fund_months": emergency_fund_months,
            },
            "anomalies": [anomaly.model_dump() for anomaly in anomalies],
            "warnings": warnings,
            "fallback_recommendation": fallback_recommendation.model_dump(),
        }
        return json.dumps(payload, indent=2, default=str)

    def _score_risk(self, cashflow: float, savings_rate: float, debt_to_income: float, emergency_fund_months: float, anomalies: list) -> float:
        score = 0.25
        if cashflow < 0:
            score += 0.25
        if savings_rate < 0.1:
            score += 0.15
        if debt_to_income > 0.5:
            score += 0.2
        if emergency_fund_months < 3:
            score += 0.1
        score += min(len(anomalies) * 0.08, 0.2)
        return round(min(score, 1.0), 2)

    def _build_insights(self, cashflow: float, savings_rate: float, debt_to_income: float, emergency_fund_months: float, anomalies: list) -> list[str]:
        insights = [
            f"Estimated monthly cashflow is {cashflow:.2f}.",
            f"Savings rate is {savings_rate:.1%}.",
            f"Debt-to-income ratio is {debt_to_income:.2f}.",
            f"Emergency fund covers {emergency_fund_months:.1f} months of expenses.",
        ]
        if anomalies:
            insights.append(f"Detected {len(anomalies)} anomaly signal(s) requiring review.")
        return insights
