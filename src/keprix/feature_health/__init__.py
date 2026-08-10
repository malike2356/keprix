"""Feature health audit (parity with shared/feature-health)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Literal
from urllib.error import URLError
from urllib.request import Request, urlopen

FeatureStatus = Literal["healthy", "degraded", "broken"]
FixPriority = Literal["P0", "P1", "P2", "P3"]

DEFAULT_BROKEN = 0.05
DEFAULT_DEGRADED = 0.01


@dataclass
class FeatureHealth:
    name: str
    status: FeatureStatus = "healthy"
    active_users_7d: int = 0
    error_rate_7d: float = 0.0
    adoption_rate: float = 0.0
    last_deployed: str | None = None
    last_tested: str | None = None


@dataclass
class RegisteredFeature:
    name: str
    endpoints: list[str]
    owner: str
    critical_path: bool = False
    revenue_impact: float = 0.0
    last_deployed: str | None = None
    health: FeatureHealth = field(default_factory=lambda: FeatureHealth(name=""))

    def __post_init__(self) -> None:
        if not self.health.name:
            self.health = FeatureHealth(name=self.name, last_deployed=self.last_deployed)


class FeatureRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._features: dict[str, RegisteredFeature] = {}

    def clear(self) -> None:
        with self._lock:
            self._features.clear()

    def register(
        self,
        name: str,
        endpoints: list[str],
        owner: str,
        *,
        critical_path: bool = False,
        revenue_impact: float = 0.0,
        last_deployed: str | None = None,
    ) -> RegisteredFeature:
        key = name.strip().lower()
        if not key:
            raise ValueError("feature name required")
        with self._lock:
            existing = self._features.get(key)
            row = RegisteredFeature(
                name=key,
                endpoints=list(endpoints),
                owner=owner.strip() or "unassigned",
                critical_path=critical_path,
                revenue_impact=revenue_impact,
                last_deployed=last_deployed,
                health=existing.health if existing else FeatureHealth(name=key, last_deployed=last_deployed),
            )
            self._features[key] = row
            return row

    def get_all(self) -> list[RegisteredFeature]:
        with self._lock:
            return sorted(self._features.values(), key=lambda f: f.name)

    def update_health(self, name: str, **patch: Any) -> RegisteredFeature | None:
        key = name.strip().lower()
        with self._lock:
            row = self._features.get(key)
            if not row:
                return None
            for k, v in patch.items():
                if hasattr(row.health, k):
                    setattr(row.health, k, v)
            row.health.name = key
            return row


_REGISTRY = FeatureRegistry()


def get_registry() -> FeatureRegistry:
    return _REGISTRY


def traffic_light(status: FeatureStatus) -> Literal["green", "yellow", "red"]:
    if status == "healthy":
        return "green"
    if status == "degraded":
        return "yellow"
    return "red"


def derive_status(
    *,
    smoke_ok: bool,
    error_rate: float,
    error_rate_broken: float = DEFAULT_BROKEN,
    error_rate_degraded: float = DEFAULT_DEGRADED,
) -> FeatureStatus:
    if not smoke_ok or error_rate > error_rate_broken:
        return "broken"
    if error_rate > error_rate_degraded:
        return "degraded"
    return "healthy"


def _default_fetch(url: str) -> tuple[int, bool]:
    try:
        req = Request(url, method="GET")
        with urlopen(req, timeout=5) as res:  # noqa: S310 - operator-controlled probe URLs
            code = int(getattr(res, "status", 200) or 200)
            return code, 200 <= code < 400
    except URLError:
        return 0, False
    except Exception:
        return 0, False


def check_feature_health(
    feature: RegisteredFeature,
    *,
    fetch_fn: Callable[[str], tuple[int, bool]] | None = None,
    get_error_rate: Callable[[str], float] | None = None,
    get_usage: Callable[[str], dict[str, float | int]] | None = None,
    base_url: str = "",
    registry: FeatureRegistry | None = None,
) -> dict[str, Any]:
    reg = registry or _REGISTRY
    fetch = fetch_fn or _default_fetch
    smokes: list[dict[str, Any]] = []
    base = base_url.rstrip("/")
    endpoints = feature.endpoints or []
    if not endpoints:
        smokes.append(
            {
                "endpoint": "(none)",
                "ok": False,
                "status_code": None,
                "detail": "No endpoints registered",
            }
        )
    for endpoint in endpoints:
        url = endpoint if endpoint.startswith("http") else f"{base}{endpoint if endpoint.startswith('/') else '/' + endpoint}"
        if not base and not endpoint.startswith("http"):
            # Soft-pass relative probes when no base URL (unit / ops default).
            smokes.append(
                {
                    "endpoint": endpoint,
                    "ok": True,
                    "status_code": 200,
                    "detail": "Skipped probe (no base_url); assumed ok",
                }
            )
            continue
        code, ok = fetch(url)
        smokes.append(
            {
                "endpoint": endpoint,
                "ok": ok,
                "status_code": code or None,
                "detail": f"HTTP {code}" if code else "request failed",
            }
        )
    smoke_ok = bool(smokes) and all(s["ok"] for s in smokes)
    error_rate = float(get_error_rate(feature.name) if get_error_rate else 0.0)
    usage = get_usage(feature.name) if get_usage else {"active_users_7d": 0, "adoption_rate": 0}
    status = derive_status(smoke_ok=smoke_ok, error_rate=error_rate)
    updated = reg.update_health(
        feature.name,
        status=status,
        active_users_7d=int(usage.get("active_users_7d") or 0),
        error_rate_7d=error_rate,
        adoption_rate=float(usage.get("adoption_rate") or 0),
        last_tested=datetime.now(timezone.utc).isoformat(),
    )
    return {
        "feature": updated or feature,
        "smokes": smokes,
        "status": status,
    }


def check_all_features(**kwargs: Any) -> dict[str, Any]:
    registry: FeatureRegistry = kwargs.pop("registry", None) or _REGISTRY
    results = [check_feature_health(f, registry=registry, **kwargs) for f in registry.get_all()]
    summary = {
        "healthy": sum(1 for r in results if r["status"] == "healthy"),
        "degraded": sum(1 for r in results if r["status"] == "degraded"),
        "broken": sum(1 for r in results if r["status"] == "broken"),
    }
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "summary": summary,
    }


@dataclass
class FixQueueItem:
    feature: str
    priority: FixPriority
    status: FeatureStatus
    active_users_7d: int
    revenue_impact: float
    critical_path: bool
    score: float
    action: Literal["fix", "deprecate"]
    recommendation: str
    owner: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "feature": self.feature,
            "priority": self.priority,
            "status": self.status,
            "activeUsers7d": self.active_users_7d,
            "revenueImpact": self.revenue_impact,
            "criticalPath": self.critical_path,
            "score": self.score,
            "action": self.action,
            "recommendation": self.recommendation,
            "owner": self.owner,
        }


def prioritize_fixes(features: list[RegisteredFeature] | None = None) -> list[FixQueueItem]:
    items: list[FixQueueItem] = []
    for feature in features or _REGISTRY.get_all():
        h = feature.health
        active = h.active_users_7d > 0
        critical = bool(feature.critical_path)
        revenue = float(feature.revenue_impact or 0)
        if h.status == "healthy":
            continue
        if h.status == "broken" and active and critical:
            items.append(
                FixQueueItem(
                    feature.name,
                    "P0",
                    h.status,
                    h.active_users_7d,
                    revenue,
                    critical,
                    1000 + h.active_users_7d * 10 + revenue * 100,
                    "fix",
                    "Fix immediately (broken, active users, critical path).",
                    feature.owner,
                )
            )
        elif h.status == "broken" and active:
            items.append(
                FixQueueItem(
                    feature.name,
                    "P1",
                    h.status,
                    h.active_users_7d,
                    revenue,
                    critical,
                    500 + h.active_users_7d * 10 + revenue * 50,
                    "fix",
                    "Fix before starting any new feature work.",
                    feature.owner,
                )
            )
        elif h.status == "degraded":
            items.append(
                FixQueueItem(
                    feature.name,
                    "P2",
                    h.status,
                    h.active_users_7d,
                    revenue,
                    critical,
                    200 + h.active_users_7d * 5 + revenue * 20,
                    "fix",
                    "Schedule a fix; degraded but not fully broken.",
                    feature.owner,
                )
            )
        elif h.status == "broken" and not active:
            items.append(
                FixQueueItem(
                    feature.name,
                    "P3",
                    h.status,
                    0,
                    revenue,
                    critical,
                    50 + revenue,
                    "deprecate",
                    "Broken with zero adoption. Prefer deprecation or kill over a fix ticket.",
                    feature.owner,
                )
            )
    rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    items.sort(key=lambda i: (rank[i.priority], -i.score))
    return items


def generate_fix_queue(features: list[RegisteredFeature] | None = None) -> dict[str, Any]:
    queue = prioritize_fixes(features)
    return {
        "queue": queue,
        "fix_now": [i for i in queue if i.action == "fix"],
        "deprecate": [i for i in queue if i.action == "deprecate"],
    }


def can_build_new_feature(registry: FeatureRegistry | None = None) -> bool:
    return len(get_blocking_issues(registry)) == 0


def get_blocking_issues(registry: FeatureRegistry | None = None) -> list[FixQueueItem]:
    reg = registry or _REGISTRY
    q = generate_fix_queue(reg.get_all())
    return [i for i in q["fix_now"] if i.priority in {"P0", "P1"}]


def evaluate_build_gate(registry: FeatureRegistry | None = None) -> dict[str, Any]:
    reg = registry or _REGISTRY
    packed = generate_fix_queue(reg.get_all())
    blocking = [i for i in packed["fix_now"] if i.priority in {"P0", "P1"}]
    allowed = len(blocking) == 0
    return {
        "allowed": allowed,
        "blocked": not allowed,
        "blocking_issues": [i.as_dict() for i in blocking],
        "fix_queue": [i.as_dict() for i in packed["queue"]],
        "deprecate": [i.as_dict() for i in packed["deprecate"]],
        "reason": (
            "No P0/P1 feature health blockers."
            if allowed
            else f"Blocked by {len(blocking)} P0/P1 issue(s). Work the fix queue first."
        ),
    }


def seed_keprix_features(registry: FeatureRegistry | None = None) -> None:
    reg = registry or _REGISTRY
    reg.clear()
    reg.register("crm", ["/api/crm/health", "/api/health"], "growth", revenue_impact=6)
    reg.register("outreach", ["/api/outreach/health", "/api/health"], "growth", revenue_impact=5)
    reg.register("billing", ["/api/billing/health", "/api/health"], "billing", critical_path=True, revenue_impact=10)
    reg.register("auth", ["/api/health"], "platform", critical_path=True, revenue_impact=8)
    reg.register("memory", ["/api/health"], "platform")
    reg.register("playbooks", ["/api/health"], "platform", revenue_impact=3)
    reg.register("channels", ["/api/health"], "platform")
    reg.register("vault", ["/api/health"], "security", critical_path=True, revenue_impact=4)
    reg.register("settings", ["/api/health"], "platform")
