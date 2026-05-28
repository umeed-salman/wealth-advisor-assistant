from __future__ import annotations

from typing import Protocol

from wealth_advisor.models import CRMContext, ClientFinancialInput


class CRMTool(Protocol):
    def fetch_context(self, client: ClientFinancialInput) -> CRMContext:
        raise NotImplementedError


class AnalysisTool(Protocol):
    def calculate_cashflow(self, client: ClientFinancialInput) -> float:
        raise NotImplementedError
