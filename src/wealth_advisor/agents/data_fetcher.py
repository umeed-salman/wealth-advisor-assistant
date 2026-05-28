from __future__ import annotations

import logging

from wealth_advisor.models import ClientFinancialInput, ClientProfile
from wealth_advisor.tools.interfaces import CRMTool


class DataFetcherAgent:
    def __init__(self, crm_tool: CRMTool) -> None:
        self._crm_tool = crm_tool
        self._logger = logging.getLogger(self.__class__.__name__)

    def run(self, client: ClientFinancialInput) -> ClientProfile:
        self._logger.info("fetching client context client_id=%s", client.client_id)
        crm_context = self._crm_tool.fetch_context(client)
        monthly_cashflow = client.monthly_income - client.monthly_expenses
        savings_rate = monthly_cashflow / client.monthly_income if client.monthly_income else 0.0
        debt_to_income = client.liabilities / (client.monthly_income * 12) if client.monthly_income else 0.0
        emergency_fund_months = client.liquid_assets / client.monthly_expenses if client.monthly_expenses else 0.0

        return ClientProfile(
            client=client,
            crm=crm_context,
            monthly_cashflow=monthly_cashflow,
            savings_rate=savings_rate,
            debt_to_income=debt_to_income,
            emergency_fund_months=emergency_fund_months,
        )
