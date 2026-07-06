"""Configuration hardening for WARDEN."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from keprix.personas.warden.auditor import Severity
from keprix.personas.warden.persona import WARDEN_PERSONA
from keprix.security.headers import build_security_headers


@dataclass(slots=True)
class HardeningRecommendation:
    id: str
    title: str
    severity: str
    current: str
    recommended: str
    category: str
    needs_approval: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity,
            "current": self.current,
            "recommended": self.recommended,
            "category": self.category,
            "needs_approval": self.needs_approval,
        }


HARDENING_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "docker_no_privileged",
        "title": "Disable privileged containers",
        "severity": Severity.HIGH,
        "category": "container",
        "check_key": "docker_privileged",
        "bad_value": True,
        "recommended": "privileged: false",
    },
    {
        "id": "docker_drop_caps",
        "title": "Drop all container capabilities",
        "severity": Severity.HIGH,
        "category": "container",
        "check_key": "docker_drop_caps",
        "bad_value": False,
        "recommended": "cap_drop: [ALL]",
    },
    {
        "id": "debug_disabled",
        "title": "Disable debug mode in production",
        "severity": Severity.HIGH,
        "category": "application",
        "check_key": "debug",
        "bad_value": True,
        "recommended": "debug: false",
    },
    {
        "id": "rate_limit_enabled",
        "title": "Enable API rate limiting",
        "severity": Severity.MEDIUM,
        "category": "application",
        "check_key": "rate_limit_enabled",
        "bad_value": False,
        "recommended": "rate_limit_enabled: true",
    },
    {
        "id": "secure_cookies",
        "title": "Enable secure cookie flags",
        "severity": Severity.MEDIUM,
        "category": "application",
        "check_key": "secure_cookies",
        "bad_value": False,
        "recommended": "secure_cookies: true",
    },
    {
        "id": "env_file_permissions",
        "title": "Restrict .env file permissions",
        "severity": Severity.MEDIUM,
        "category": "os",
        "check_key": "env_file_mode",
        "bad_value": "644",
        "recommended": "chmod 600 .env",
    },
]


class WardenHardener:
    def __init__(self) -> None:
        self.persona = WARDEN_PERSONA
        self._applied: dict[str, str] = {}

    def assess(self, config: dict[str, Any]) -> list[HardeningRecommendation]:
        recommendations: list[HardeningRecommendation] = []

        for template in HARDENING_TEMPLATES:
            key = template["check_key"]
            current_value = config.get(key)
            if current_value == template["bad_value"]:
                recommendations.append(
                    HardeningRecommendation(
                        id=template["id"],
                        title=template["title"],
                        severity=template["severity"],
                        current=f"{key}={current_value!r}",
                        recommended=template["recommended"],
                        category=template["category"],
                    )
                )

        if not config.get("https_enabled") and not config.get("secure_cookies"):
            recommendations.append(
                HardeningRecommendation(
                    id="enable_hsts",
                    title="Enable HSTS for HTTPS deployments",
                    severity=Severity.MEDIUM,
                    current="https_enabled=false",
                    recommended="Enable HTTPS and Strict-Transport-Security header",
                    category="http",
                )
            )

        headers = build_security_headers(https_enabled=bool(config.get("https_enabled")))
        if "X-Frame-Options" not in headers:
            recommendations.append(
                HardeningRecommendation(
                    id="security_headers",
                    title="Enable security headers middleware",
                    severity=Severity.MEDIUM,
                    current="headers incomplete",
                    recommended="Apply SecurityHeadersMiddleware with CSP and X-Frame-Options",
                    category="http",
                )
            )

        return recommendations

    def apply(self, recommendation_id: str, config: dict[str, Any], *, approved: bool = False) -> dict[str, Any]:
        template = next((item for item in HARDENING_TEMPLATES if item["id"] == recommendation_id), None)
        if template is None:
            return {"applied": False, "reason": "unknown recommendation"}

        if not approved:
            return {
                "applied": False,
                "reason": "approval required",
                "recommendation_id": recommendation_id,
                "recommended": template["recommended"],
            }

        key = template["check_key"]
        if key == "env_file_mode":
            self._applied[recommendation_id] = "600"
            return {"applied": True, "recommendation_id": recommendation_id, "action": "chmod 600 .env"}

        inverse_values = {
            "docker_privileged": False,
            "docker_drop_caps": True,
            "debug": False,
            "rate_limit_enabled": True,
            "secure_cookies": True,
        }
        if key in inverse_values:
            config[key] = inverse_values[key]
            self._applied[recommendation_id] = template["recommended"]
            return {
                "applied": True,
                "recommendation_id": recommendation_id,
                "config_patch": {key: config[key]},
            }

        return {"applied": False, "reason": "no automatic patch available", "recommendation_id": recommendation_id}

    def list_applied(self) -> dict[str, str]:
        return dict(self._applied)
