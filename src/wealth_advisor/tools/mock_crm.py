from __future__ import annotations

import random

from wealth_advisor.config import Settings
from wealth_advisor.exceptions import ToolError
from wealth_advisor.models import CRMContext, ClientFinancialInput


class MockCRMTool:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch_context(self, client: ClientFinancialInput) -> CRMContext:
        if self._settings.crm_failure_rate and random.random() < self._settings.crm_failure_rate:
            raise ToolError(f"CRM API failure for client {client.client_id}")

        profile_map = {
            "client-001": CRMContext(
                client_id=client.client_id,
                relationship_status="active",
                household_size=3,
                risk_tolerance="moderate",
                lifecycle_stage="accumulation",
                last_meeting_summary="Reviewed 529 plans and emergency fund coverage.",
                advisor_notes=["Increase cash reserves before taking new credit."],
                open_tasks=["Follow up on tax-loss harvesting"],
            ),
            "client-002": CRMContext(
                client_id=client.client_id,
                relationship_status="active",
                household_size=2,
                risk_tolerance="conservative",
                lifecycle_stage="pre-retirement",
                last_meeting_summary="Client expressed concern about near-term market volatility.",
                advisor_notes=["Keep asset allocation stable.", "Watch for unusual withdrawals."],
                open_tasks=["Review beneficiary updates"],
            ),
        }

        return profile_map.get(
            client.client_id,
            CRMContext(
                client_id=client.client_id,
                relationship_status="active",
                household_size=None,
                risk_tolerance=client.risk_preference,
                lifecycle_stage="unknown",
                last_meeting_summary="No recent CRM notes available.",
                advisor_notes=[],
                open_tasks=[],
            ),
        )
