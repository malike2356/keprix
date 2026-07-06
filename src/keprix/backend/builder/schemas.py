"""Builder schemas (Prompt 29)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StackReport:
    stack_type: str
    languages: list[str] = field(default_factory=list)
    dependencies: dict[str, str] = field(default_factory=dict)
    database: str = "none"
    entry_points: list[str] = field(default_factory=list)
    has_tests: bool = False
    has_docker: bool = False
    has_git: bool = False
    estimated_completeness: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "stack_type": self.stack_type,
            "languages": self.languages,
            "dependencies": self.dependencies,
            "database": self.database,
            "entry_points": self.entry_points,
            "has_tests": self.has_tests,
            "has_docker": self.has_docker,
            "has_git": self.has_git,
            "estimated_completeness": self.estimated_completeness,
        }


PROJECT_MARKERS = (
    "package.json",
    "composer.json",
    "pyproject.toml",
    "requirements.txt",
    "build.gradle",
    "build.gradle.kts",
    "Package.swift",
    "Makefile",
    "wp-config.php",
)

TEMPLATE_NAMES = (
    "custom-php-mvc",
    "laravel-api",
    "wordpress-theme",
    "wordpress-plugin",
    "nextjs-saas",
    "nuxt-ssr",
    "react-spa",
    "node-express-api",
    "electron-app",
    "tauri-app",
    "react-native",
    "flutter",
    "swift-ios",
    "kotlin-android",
    "fastapi-service",
    "flask-api",
    "python-cli",
    "keprix-php-app",
    "keprix-nextjs-app",
    "keprix-mobile-app",
)

FLEETX_DOMAINS = (
    ("Vehicle", ["plate", "make", "model", "year", "status", "driver_id"]),
    ("Driver", ["name", "license_no", "phone", "status"]),
    ("Trip", ["vehicle_id", "driver_id", "origin", "destination", "start", "end", "distance_km", "fuel_used"]),
    ("Maintenance", ["vehicle_id", "type", "cost", "date", "next_due"]),
    ("Fuel", ["vehicle_id", "litres", "cost", "station", "odometer"]),
)
