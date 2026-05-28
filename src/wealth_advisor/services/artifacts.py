from __future__ import annotations

import json
from pathlib import Path

from wealth_advisor.models import AdvisoryRunRecord, AnalysisResponse


class ArtifactStore:
    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        self._runs_dir = self._output_dir / "runs"
        self._runs_dir.mkdir(parents=True, exist_ok=True)

    def write_response(self, response: AnalysisResponse) -> Path:
        artifact_path = self._runs_dir / f"{response.run_id}.json"
        payload = response.model_dump(mode="json")
        artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return artifact_path

    def write_run(self, run: AdvisoryRunRecord) -> Path:
        artifact_path = self._runs_dir / f"{run.run_id}.json"
        payload = run.model_dump(mode="json")
        artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return artifact_path