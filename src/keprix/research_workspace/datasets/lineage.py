"""Dataset transformation lineage."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LineageStep:
    step: str
    detail: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DatasetLineage:
    dataset_id: str
    version_number: int
    steps: list[LineageStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "version_number": self.version_number,
            "steps": [step.to_dict() for step in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatasetLineage:
        return cls(
            dataset_id=str(data["dataset_id"]),
            version_number=int(data["version_number"]),
            steps=[
            LineageStep(
                step=str(item["step"]),
                detail=dict(item.get("detail") or {}),
                created_at=str(item.get("created_at") or _utcnow()),
            )
            for item in data.get("steps") or []
        ],
        )


class LineageStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, dataset_id: str, version_number: int) -> Path:
        return self.root / dataset_id / f"v{version_number}.json"

    def load(self, dataset_id: str, version_number: int) -> DatasetLineage:
        path = self.path_for(dataset_id, version_number)
        if not path.exists():
            return DatasetLineage(dataset_id=dataset_id, version_number=version_number)
        return DatasetLineage.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save(self, lineage: DatasetLineage) -> None:
        path = self.path_for(lineage.dataset_id, lineage.version_number)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(lineage.to_dict(), indent=2), encoding="utf-8")

    def append_step(self, dataset_id: str, version_number: int, step: str, **detail: Any) -> DatasetLineage:
        lineage = self.load(dataset_id, version_number)
        lineage.steps.append(LineageStep(step=step, detail=detail))
        self.save(lineage)
        return lineage
