"""Incident severity levels for Keprix security operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IncidentLevel(str, Enum):
    L1_INFO = "info"
    L2_WARNING = "warning"
    L3_CRITICAL = "critical"
    L4_EMERGENCY = "emergency"

    @classmethod
    def from_label(cls, raw: str) -> IncidentLevel:
        value = str(raw or "").strip().lower().replace("l", "").replace("_", "")
        mapping = {
            "1": cls.L1_INFO,
            "info": cls.L1_INFO,
            "2": cls.L2_WARNING,
            "warning": cls.L2_WARNING,
            "3": cls.L3_CRITICAL,
            "critical": cls.L3_CRITICAL,
            "4": cls.L4_EMERGENCY,
            "emergency": cls.L4_EMERGENCY,
        }
        return mapping.get(value, cls.L2_WARNING)


@dataclass(frozen=True)
class SeveritySpec:
    level: IncidentLevel
    name: str
    response_time: str
    auto_response: str


SEVERITY_MATRIX: dict[IncidentLevel, SeveritySpec] = {
    IncidentLevel.L1_INFO: SeveritySpec(
        IncidentLevel.L1_INFO,
        "INFO",
        "Review within 24h",
        "Log only",
    ),
    IncidentLevel.L2_WARNING: SeveritySpec(
        IncidentLevel.L2_WARNING,
        "WARNING",
        "Investigate within 4h",
        "Quarantine tool",
    ),
    IncidentLevel.L3_CRITICAL: SeveritySpec(
        IncidentLevel.L3_CRITICAL,
        "CRITICAL",
        "Respond within 15min",
        "Block session + alert operator",
    ),
    IncidentLevel.L4_EMERGENCY: SeveritySpec(
        IncidentLevel.L4_EMERGENCY,
        "EMERGENCY",
        "Respond immediately",
        "Full instance suspension + credential rotation",
    ),
}
