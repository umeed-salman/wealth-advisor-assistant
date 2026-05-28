from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from wealth_advisor.models import AnalysisResult, MemoryEntry


class MemoryStore:
    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._history_path = self._base_path / "history.jsonl"

    def append_summary(self, run_id: str, client_id: str, analysis: AnalysisResult, recommendation_text: str) -> MemoryEntry:
        entry = MemoryEntry(
            run_id=run_id,
            client_id=client_id,
            summary="; ".join(analysis.insights[:3]) or "No high-level insights recorded.",
            anomalies=[anomaly.title for anomaly in analysis.anomalies],
            recommendation=recommendation_text,
            created_at=datetime.now(timezone.utc),
            metadata={"risk_score": analysis.risk_score, "fallback_used": analysis.fallback_used},
        )
        with self._lock:
            with self._history_path.open("a", encoding="utf-8") as handle:
                handle.write(entry.model_dump_json() + "\n")
        return entry

    def list_recent(self, limit: int = 10) -> list[MemoryEntry]:
        if not self._history_path.exists():
            return []
        entries: list[MemoryEntry] = []
        with self._history_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                entries.append(MemoryEntry.model_validate_json(line))
        return entries[-limit:]
