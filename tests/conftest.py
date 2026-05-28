from __future__ import annotations

import json
from pathlib import Path

import pytest

from wealth_advisor.agents.analyzer import AnalyzerAgent
from wealth_advisor.agents.data_fetcher import DataFetcherAgent
from wealth_advisor.config import Settings
from wealth_advisor.models import ClientFinancialInput, LLMAdvisoryOutput
from wealth_advisor.orchestrator import OrchestratorDependencies, WealthAdvisorOrchestrator
from wealth_advisor.services.artifacts import ArtifactStore
from wealth_advisor.services.memory import MemoryStore
from wealth_advisor.services.run_store import RunStore
from wealth_advisor.tools.mock_crm import MockCRMTool


class FakeAdvisorLLM:
    def generate_advice(self, analysis_context: str) -> LLMAdvisoryOutput:
        return LLMAdvisoryOutput(
            summary="LLM-backed summary for the client.",
            key_insights=["Cashflow pressure is elevated.", "The client should review the large travel transaction."],
            recommendation_action="Review travel spend with the client",
            recommendation_rationale="The LLM interpreted the metrics as needing an immediate advisor follow-up.",
            recommendation_priority="high",
            next_steps=["Discuss the large travel charge", "Confirm budget adjustments"],
            risk_flags=["travel_spike"],
        )


@pytest.fixture()
def sample_client() -> ClientFinancialInput:
    payload = json.loads(Path("input/sample_client.json").read_text(encoding="utf-8"))
    return ClientFinancialInput.model_validate(payload)


@pytest.fixture()
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        input_dir=tmp_path / "input",
        output_dir=tmp_path / "output",
        memory_dir=tmp_path / "output" / "memory",
        data_dir=tmp_path / "input",
        approval_mode="manual",
    )


@pytest.fixture()
def orchestrator(test_settings: Settings) -> WealthAdvisorOrchestrator:
    dependencies = OrchestratorDependencies(
        settings=test_settings,
        run_store=RunStore(),
        memory_store=MemoryStore(test_settings.memory_dir),
        artifact_store=ArtifactStore(test_settings.output_dir),
        data_fetcher=DataFetcherAgent(MockCRMTool(test_settings)),
        analyzer=AnalyzerAgent(advisor_llm=FakeAdvisorLLM(), settings=test_settings),
    )
    return WealthAdvisorOrchestrator(dependencies)
