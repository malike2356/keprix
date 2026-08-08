"""Product pack registry: install, validate, enable, disable, upgrade, rollback."""

from __future__ import annotations

import hashlib
import json
import threading
from copy import deepcopy
from typing import Any

from keprix.product_sidecar.catalog import build_aiva_wrapper_nodes, build_carina_nodes
from keprix.product_sidecar.fixtures import FIXTURE_PRODUCT_KEYS, build_all_fixture_packs
from keprix.product_sidecar.packs.abbis import build_abbis_nodes
from keprix.product_sidecar.packs.fleetz import build_fleetz_nodes
from keprix.product_sidecar.types import ProductPackManifest

STABLE_PRODUCT_KEYS = frozenset(
    {"petraclus", "abbis", "xeclone", "fleetz", "clinicom", "carina", "aiva"}
)

_CONTRACT_VERSION = "1.0.0"


class PackValidationError(ValueError):
    """Raised when a pack fails install validation; registry must stay unchanged."""


def _checksum(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _abbis_connector() -> dict[str, Any]:
    return {
        "base_url_env": "ABBIS_PRODUCT_API_URL",
        "host_allowlist": ["127.0.0.1", "localhost", "abbis.local"],
        "routes": [
            {"method": "GET", "path": "/api/keprix/v1/health", "purpose": "liveness"},
            {"method": "GET", "path": "/api/keprix/v1/capabilities", "purpose": "negotiate"},
            {"method": "POST", "path": "/api/keprix/v1/token/exchange", "purpose": "identity"},
            {"method": "GET", "path": "/api/keprix/v1/context", "purpose": "context_slice"},
            {"method": "GET", "path": "/api/keprix/v1/context/{slice_key}", "purpose": "context_slice"},
            {"method": "POST", "path": "/api/keprix/v1/events/ack", "purpose": "event_ack", "idempotency": True},
            {"method": "GET", "path": "/api/keprix/v1/localisation", "purpose": "localisation"},
            {"method": "GET", "path": "/api/keprix/v1/reads/{resource}", "purpose": "cursor_read"},
            {
                "method": "POST",
                "path": "/api/keprix/v1/actions/{action}/preview",
                "purpose": "action_preview",
                "idempotency": True,
            },
            {
                "method": "POST",
                "path": "/api/keprix/v1/actions/{action}/apply",
                "purpose": "action_apply",
                "approval_required": True,
                "idempotency": True,
            },
        ],
        "default_deny": True,
        "no_sql": True,
        "no_ui_scrape": True,
    }


def build_abbis_pack() -> ProductPackManifest:
    nodes = build_abbis_nodes()
    payload = {"product": "abbis", "nodes": sorted(nodes.keys()), "version": "0.1.0"}
    return ProductPackManifest(
        product_key="abbis",
        pack_id="abbis-borehole-sidecar",
        version="0.1.0",
        title="ABBIS borehole industry pack",
        contract_version=_CONTRACT_VERSION,
        nodes=nodes,
        enabled=True,
        checksum=_checksum(payload),
        signature="abbis-dev",
        connector=_abbis_connector(),
        policies={
            "soft_wall_bus": "product",
            "cross_product": "deny",
            "operator": "ghanaian_operating_company",
            "association": "BDAG",
            "national_min_cell_threshold": 5,
        },
        memory_namespace="product:abbis",
        playbooks=(
            "abbis.job_setup",
            "abbis.daily_field_report",
            "abbis.quote_to_receipt",
            "abbis.association_marketplace",
        ),
        events=(
            "project.created",
            "drilling_log.submitted",
            "quotation.created",
            "payment.recorded",
            "calculator.run",
            "intelligence.fact_contributed",
        ),
        migrations=("001_abbis_ns",),
        feature_flag="product.abbis.sidecar",
    )


def _fleetz_connector() -> dict[str, Any]:
    return {
        "base_url_env": "FLEETZ_PRODUCT_API_URL",
        "host_allowlist": ["127.0.0.1", "localhost", "fleetz.local"],
        "routes": [
            {"method": "GET", "path": "/api/keprix/v1/health", "purpose": "liveness"},
            {"method": "GET", "path": "/api/keprix/v1/capabilities", "purpose": "negotiate"},
            {"method": "POST", "path": "/api/keprix/v1/token/exchange", "purpose": "identity"},
            {"method": "GET", "path": "/api/keprix/v1/context", "purpose": "context_slice"},
            {"method": "POST", "path": "/api/keprix/v1/events/ack", "purpose": "event_ack", "idempotency": True},
            {"method": "GET", "path": "/api/keprix/v1/fleets/{fleet_id}", "purpose": "fleet_read"},
            {"method": "GET", "path": "/api/keprix/v1/vehicles/{vehicle_id}", "purpose": "vehicle_read"},
            {
                "method": "GET",
                "path": "/api/keprix/v1/vehicles/{vehicle_id}/positions/summary",
                "purpose": "position_summary",
            },
            {
                "method": "GET",
                "path": "/api/keprix/v1/vehicles/{vehicle_id}/fuel/summary",
                "purpose": "fuel_summary",
            },
            {
                "method": "POST",
                "path": "/api/keprix/v1/actions/{action}/preview",
                "purpose": "action_preview",
                "idempotency": True,
            },
            {
                "method": "POST",
                "path": "/api/keprix/v1/actions/{action}/apply",
                "purpose": "action_apply",
                "approval_required": True,
                "idempotency": True,
            },
        ],
        "default_deny": True,
        "no_sql": True,
        "no_ui_scrape": True,
        "no_traccar_command_api": True,
        "no_mqtt_command_publish": True,
    }


def build_fleetz_pack() -> ProductPackManifest:
    nodes = build_fleetz_nodes()
    payload = {"product": "fleetz", "nodes": sorted(nodes.keys()), "version": "0.1.0"}
    return ProductPackManifest(
        product_key="fleetz",
        pack_id="fleetz-fleet-sidecar",
        version="0.1.0",
        title="Fleetz fleet intelligence pack",
        contract_version=_CONTRACT_VERSION,
        nodes=nodes,
        enabled=True,
        checksum=_checksum(payload),
        signature="fleetz-dev",
        connector=_fleetz_connector(),
        policies={
            "soft_wall_bus": "product",
            "cross_product": "deny",
            "advisory_default": True,
            "no_vehicle_commands": True,
            "timezone": "Africa/Accra",
            "currency": "GHS",
        },
        memory_namespace="product:fleetz",
        playbooks=(
            "fleetz.fuel_investigation",
            "fleetz.alert_triage",
            "fleetz.maintenance_workflow",
            "fleetz.daily_fleet_briefing",
            "fleetz.driver_message",
            "fleetz.route_geofence_optimisation",
        ),
        events=(
            "fleetz.vehicle.state",
            "fleetz.trip",
            "fleetz.fuel.anomaly",
            "fleetz.geofence",
            "fleetz.sensor.health",
            "fleetz.maintenance",
            "fleetz.alert",
        ),
        migrations=("001_fleetz_ns",),
        feature_flag="product.fleetz.sidecar",
    )


def _carina_connector() -> dict[str, Any]:
    return {
        "base_url_env": "CARINA_PRODUCT_API_URL",
        "host_allowlist": ["127.0.0.1", "localhost", "carina.local", "aiva.local"],
        "routes": [
            {"method": "GET", "path": "/api/keprix/v1/health", "purpose": "liveness"},
            {"method": "GET", "path": "/api/keprix/v1/capabilities", "purpose": "negotiate"},
            {"method": "POST", "path": "/api/keprix/v1/token/exchange", "purpose": "identity"},
            {"method": "GET", "path": "/api/keprix/v1/context", "purpose": "context_slice"},
            {"method": "POST", "path": "/api/keprix/v1/events/ack", "purpose": "event_ack"},
            {
                "method": "GET",
                "path": "/api/keprix/v1/soft-wall/pending",
                "purpose": "soft_wall_counts",
                "sensitivity": "internal",
            },
            {
                "method": "GET",
                "path": "/api/keprix/v1/crm/records/{id}",
                "purpose": "crm_projected_read",
                "sensitivity": "pii_minimised",
            },
            {
                "method": "POST",
                "path": "/api/keprix/v1/approvals/{id}/ack",
                "purpose": "approval_ack",
                "idempotency": True,
            },
            {
                "method": "POST",
                "path": "/api/keprix/v1/crm/propose/apply",
                "purpose": "crm_propose_apply",
                "approval_required": True,
                "idempotency": True,
            },
        ],
        "default_deny": True,
        "no_sql": True,
        "no_ui_scrape": True,
    }


def build_carina_pack() -> ProductPackManifest:
    nodes = build_carina_nodes()
    payload = {"product": "carina", "nodes": sorted(nodes.keys()), "version": "1.0.0"}
    return ProductPackManifest(
        product_key="carina",
        pack_id="carina-aiva-sidecar",
        version="1.0.0",
        title="Carina platform pack",
        contract_version=_CONTRACT_VERSION,
        nodes=nodes,
        enabled=True,
        checksum=_checksum(payload),
        signature="carina-dev",
        connector=_carina_connector(),
        policies={"soft_wall_bus": "product", "cross_product": "deny"},
        memory_namespace="product:carina",
        playbooks=("agent.default", "crm.enroll.guarded"),
        events=("keprix.capability.denied", "keprix.soft_wall.requested", "keprix.job.completed"),
        migrations=("001_carina_ns",),
        feature_flag="product.carina.sidecar",
    )


def build_aiva_pack(carina: ProductPackManifest) -> ProductPackManifest:
    nodes = build_aiva_wrapper_nodes(carina.nodes)
    payload = {"product": "aiva", "wrapper_of": "carina", "nodes": sorted(nodes.keys())}
    return ProductPackManifest(
        product_key="aiva",
        pack_id="carina-aiva-sidecar",
        version=carina.version,
        title="Aiva surface wrapper",
        contract_version=_CONTRACT_VERSION,
        nodes=nodes,
        wrapper_of="carina",
        enabled=True,
        checksum=_checksum(payload),
        signature="aiva-dev",
        connector=deepcopy(carina.connector),
        policies={**carina.policies, "surface": "aiva"},
        memory_namespace="product:aiva",
        playbooks=carina.playbooks,
        events=carina.events,
        migrations=("001_aiva_ns",),
        feature_flag="product.aiva.sidecar",
    )


def validate_pack(pack: ProductPackManifest, *, installed: dict[str, ProductPackManifest]) -> None:
    if pack.product_key not in STABLE_PRODUCT_KEYS:
        raise PackValidationError(f"unknown product_key: {pack.product_key}")
    if not pack.checksum:
        raise PackValidationError("checksum required")
    if not pack.contract_version:
        raise PackValidationError("contract_version required")
    if not pack.nodes:
        raise PackValidationError("pack must declare nodes")
    if not pack.memory_namespace.startswith(f"product:{pack.product_key}"):
        raise PackValidationError("memory_namespace must be product-scoped")
    for key, node in pack.nodes.items():
        if key != node.key:
            raise PackValidationError(f"node key mismatch: {key}")
        # Absolute separation: node.product must match pack (or carina family for aiva wrapper)
        allowed = {pack.product_key}
        if pack.wrapper_of:
            allowed.add(pack.wrapper_of)
        if node.product not in allowed:
            raise PackValidationError(f"cross_product_node:{node.key}:{node.product}")
    if pack.wrapper_of:
        parent = installed.get(pack.wrapper_of)
        if parent is None and pack.wrapper_of not in installed:
            # Parent must already exist when installing wrapper alone
            raise PackValidationError(f"wrapper parent missing: {pack.wrapper_of}")
    # Namespace collision: memory namespaces must be unique across products
    for other in installed.values():
        if other.product_key == pack.product_key:
            continue
        if other.memory_namespace == pack.memory_namespace:
            raise PackValidationError("memory_namespace_collision")


class ProductPackRegistry:
    """In-process registry with atomic install and last-known-good rollback."""

    def __init__(self, *, install_fixtures: bool = True) -> None:
        self._lock = threading.RLock()
        self._packs: dict[str, ProductPackManifest] = {}
        self._disabled_nodes: set[tuple[str, str]] = set()
        self._lkg: dict[str, ProductPackManifest] = {}
        self._history: list[dict[str, Any]] = []
        self._install_fixtures = install_fixtures
        self._install_defaults()

    def _install_defaults(self) -> None:
        carina = build_carina_pack()
        aiva = build_aiva_pack(carina)
        abbis = build_abbis_pack()
        fleetz = build_fleetz_pack()
        self._packs["carina"] = carina
        self._packs["aiva"] = aiva
        self._packs["abbis"] = abbis
        self._packs["fleetz"] = fleetz
        self._lkg["carina"] = deepcopy(carina)
        self._lkg["aiva"] = deepcopy(aiva)
        self._lkg["abbis"] = deepcopy(abbis)
        self._lkg["fleetz"] = deepcopy(fleetz)
        if self._install_fixtures:
            for key, pack in build_all_fixture_packs().items():
                if key in {"abbis", "fleetz"}:
                    # Real product packs replace foundation fixtures.
                    continue
                self._packs[key] = pack
                self._lkg[key] = deepcopy(pack)

    def reset_for_tests(self, *, install_fixtures: bool | None = None) -> None:
        with self._lock:
            if install_fixtures is not None:
                self._install_fixtures = install_fixtures
            self._packs.clear()
            self._disabled_nodes.clear()
            self._lkg.clear()
            self._history.clear()
            self._install_defaults()

    def list_packs(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "product_key": p.product_key,
                    "pack_id": p.pack_id,
                    "version": p.version,
                    "enabled": p.enabled,
                    "wrapper_of": p.wrapper_of,
                    "node_counts": p.node_status_counts(),
                    "checksum": p.checksum,
                    "memory_namespace": p.memory_namespace,
                    "feature_flag": p.feature_flag,
                }
                for p in self._packs.values()
            ]

    def known_products(self) -> frozenset[str]:
        with self._lock:
            return frozenset(self._packs.keys())

    def get(self, product_key: str) -> ProductPackManifest | None:
        with self._lock:
            return self._packs.get(product_key)

    def require(self, product_key: str) -> ProductPackManifest:
        pack = self.get(product_key)
        if pack is None:
            raise KeyError(product_key)
        return pack

    def inspect(self, product_key: str) -> dict[str, Any]:
        pack = self.require(product_key)
        return pack.to_public_dict()

    def health(self, product_key: str) -> dict[str, Any]:
        pack = self.require(product_key)
        return {
            "product": product_key,
            "enabled": pack.enabled,
            "version": pack.version,
            "contract_version": pack.contract_version,
            "checksum": pack.checksum,
            "node_counts": pack.node_status_counts(),
            "lkg_version": (self._lkg.get(product_key).version if product_key in self._lkg else None),
        }

    def enable(self, product_key: str) -> ProductPackManifest:
        with self._lock:
            pack = self.require(product_key)
            pack.enabled = True
            self._history.append({"action": "enable", "product": product_key})
            return pack

    def disable(self, product_key: str) -> ProductPackManifest:
        with self._lock:
            pack = self.require(product_key)
            pack.enabled = False
            self._history.append({"action": "disable", "product": product_key})
            return pack

    def remove(self, product_key: str) -> None:
        with self._lock:
            if product_key in {"carina", "aiva"}:
                raise PackValidationError("cannot remove platform packs")
            if product_key not in self._packs:
                raise KeyError(product_key)
            del self._packs[product_key]
            self._lkg.pop(product_key, None)
            self._disabled_nodes = {k for k in self._disabled_nodes if k[0] != product_key}
            self._history.append({"action": "remove", "product": product_key})

    def disable_node(self, product_key: str, node_key: str) -> None:
        with self._lock:
            self._disabled_nodes.add((product_key, node_key))

    def enable_node(self, product_key: str, node_key: str) -> None:
        with self._lock:
            self._disabled_nodes.discard((product_key, node_key))

    def is_node_disabled(self, product_key: str, node_key: str) -> bool:
        with self._lock:
            if (product_key, node_key) in self._disabled_nodes:
                return True
            pack = self._packs.get(product_key)
            if pack and pack.wrapper_of:
                return (pack.wrapper_of, node_key) in self._disabled_nodes
            return False

    def resolve_handler_product(self, product_key: str) -> str:
        """Aiva wrappers execute carina handlers; never Clinicom/Petraclus."""
        pack = self.require(product_key)
        if pack.wrapper_of:
            return pack.wrapper_of
        return product_key

    def assert_same_product_family(self, product_key: str, other: str) -> None:
        left = self.resolve_handler_product(product_key)
        right = self.resolve_handler_product(other)
        if left != right:
            raise PermissionError(f"cross_product:{product_key}->{other}")

    def install(self, pack: ProductPackManifest, *, activate: bool = True) -> ProductPackManifest:
        """Atomically install or replace a pack. Failed validation leaves registry unchanged."""
        with self._lock:
            snapshot = deepcopy(self._packs)
            try:
                validate_pack(pack, installed=self._packs)
                staged = deepcopy(pack)
                if not activate:
                    staged.enabled = False
                previous = self._packs.get(pack.product_key)
                if previous is not None and previous.enabled and previous.checksum:
                    self._lkg[pack.product_key] = deepcopy(previous)
                    staged.last_known_good_version = previous.version
                self._packs[pack.product_key] = staged
                # Re-validate full set for namespace collisions after swap
                for key, other in list(self._packs.items()):
                    validate_pack(other, installed={k: v for k, v in self._packs.items() if k != key})
                self._history.append(
                    {
                        "action": "install",
                        "product": pack.product_key,
                        "version": pack.version,
                        "checksum": pack.checksum,
                    }
                )
                return staged
            except Exception:
                self._packs = snapshot
                raise

    def upgrade(self, pack: ProductPackManifest) -> ProductPackManifest:
        with self._lock:
            current = self.require(pack.product_key)
            if pack.version == current.version and pack.checksum == current.checksum:
                return current
            return self.install(pack, activate=current.enabled)

    def rollback(self, product_key: str) -> ProductPackManifest:
        with self._lock:
            lkg = self._lkg.get(product_key)
            if lkg is None:
                raise PackValidationError(f"no last-known-good for {product_key}")
            restored = deepcopy(lkg)
            self._packs[product_key] = restored
            self._history.append(
                {"action": "rollback", "product": product_key, "version": restored.version}
            )
            return restored

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._history[-limit:])

    def compose_nodes(self, product_key: str, other_product: str) -> None:
        """Capability graph composition across products fails closed by default."""
        self.assert_same_product_family(product_key, other_product)


_REGISTRY: ProductPackRegistry | None = None
_REG_LOCK = threading.Lock()


def get_product_pack_registry() -> ProductPackRegistry:
    global _REGISTRY
    with _REG_LOCK:
        if _REGISTRY is None:
            _REGISTRY = ProductPackRegistry()
        return _REGISTRY


def reset_product_pack_registry_for_tests(*, install_fixtures: bool = True) -> ProductPackRegistry:
    global _REGISTRY
    with _REG_LOCK:
        _REGISTRY = ProductPackRegistry(install_fixtures=install_fixtures)
        return _REGISTRY


__all__ = [
    "FIXTURE_PRODUCT_KEYS",
    "PackValidationError",
    "ProductPackRegistry",
    "STABLE_PRODUCT_KEYS",
    "build_aiva_pack",
    "build_abbis_pack",
    "build_carina_pack",
    "build_fleetz_pack",
    "get_product_pack_registry",
    "reset_product_pack_registry_for_tests",
    "validate_pack",
]
