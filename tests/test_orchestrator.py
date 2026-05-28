from __future__ import annotations

from pathlib import Path

from wealth_advisor.models import ApprovalRequest, AdvisoryRunStatus


def test_orchestrator_flags_anomaly_and_waits_for_approval(orchestrator, sample_client):
    response = orchestrator.submit(sample_client)

    assert response.status == AdvisoryRunStatus.awaiting_approval
    assert response.approval_state.value == "pending"
    assert response.draft is not None
    assert response.draft.analysis.anomalies
    assert any("Increase cash reserves" in warning for warning in response.warnings)


def test_orchestrator_approval_flow(orchestrator, sample_client):
    submit_response = orchestrator.submit(sample_client)
    approval = orchestrator.approve(
        submit_response.run_id,
        ApprovalRequest(decision="approved", reviewer="advisor", notes="looks good"),
    )

    assert approval.status == AdvisoryRunStatus.approved
    assert approval.final_recommendation is not None
    assert approval.final_recommendation.action == submit_response.draft.recommendation.action
    assert approval.reviewer_notes == "looks good"
    run_record = orchestrator.get_run(submit_response.run_id)
    assert run_record.reviewed_by == "advisor"
    assert run_record.reviewer_notes == "looks good"


def test_orchestrator_writes_memory_and_artifact(orchestrator, sample_client, test_settings):
    response = orchestrator.submit(sample_client)

    artifact_path = test_settings.output_dir / "runs" / f"{response.run_id}.json"
    memory_path = test_settings.memory_dir / "history.jsonl"

    assert artifact_path.exists()
    assert memory_path.exists()
    assert response.run_id in artifact_path.read_text(encoding="utf-8")
    assert response.run_id in memory_path.read_text(encoding="utf-8")


def test_orchestrator_override_flow(orchestrator, sample_client):
    submit_response = orchestrator.submit(sample_client)
    approval = orchestrator.approve(
        submit_response.run_id,
        ApprovalRequest(
            decision="overridden",
            reviewer="advisor",
            notes="override for client conversation",
            override_action="Pause travel spend",
            override_rationale="Client should address the large discretionary purchase first.",
            override_priority="high",
            override_next_steps=["Review travel budget", "Reduce discretionary spend"],
            override_risk_flags=["large discretionary transaction"],
        ),
    )

    assert approval.approval_state.value == "overridden"
    assert approval.final_recommendation is not None
    assert approval.final_recommendation.action == "Pause travel spend"
