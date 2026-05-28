from __future__ import annotations

from fastapi.testclient import TestClient

from wealth_advisor.api.routes import create_app


def test_api_analysis_and_approval_flow(orchestrator):
    client = TestClient(create_app(orchestrator))
    sample_payload = {
        "client_id": "client-001",
        "full_name": "Jordan Ellis",
        "age": 41,
        "monthly_income": 12000,
        "monthly_expenses": 10800,
        "liquid_assets": 25000,
        "liabilities": 112000,
        "investment_assets": 185000,
        "risk_preference": "moderate",
        "transactions": [
            {
                "transaction_id": "tx-1001",
                "posted_date": "2026-05-01",
                "amount": 3500,
                "transaction_type": "debit",
                "category": "rent",
                "merchant": "Northside Apartments",
            },
            {
                "transaction_id": "tx-1002",
                "posted_date": "2026-05-03",
                "amount": 7800,
                "transaction_type": "debit",
                "category": "travel",
                "merchant": "Apex Travel",
            },
        ],
    }

    response = client.post("/analysis", json=sample_payload)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "awaiting_approval"
    assert payload["draft"]["analysis"]["anomalies"]

    approval = client.post(
        f"/analysis/{payload['run_id']}/approval",
        json={"decision": "approved", "reviewer": "advisor", "notes": "approved"},
    )
    assert approval.status_code == 200
    approval_payload = approval.json()
    assert approval_payload["status"] == "approved"
    assert approval_payload["final_recommendation"] is not None
