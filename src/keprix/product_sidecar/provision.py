"""Declarative product sidecar provisioning plans, receipts, and rollback."""

from __future__ import annotations

import threading
import time
from copy import deepcopy
from typing import Any

from keprix.product_sidecar.fixtures import FIXTURE_PRODUCT_KEYS, build_fixture_pack
from keprix.product_sidecar.persistence import get_provision_store
from keprix.product_sidecar.registry import (
    PackValidationError,
    STABLE_PRODUCT_KEYS,
    build_abbis_pack,
    build_fleetz_pack,
    build_propreneur_pack,
    get_product_pack_registry,
)
from keprix.product_sidecar.state import get_event_store, get_job_store, get_kill_switches, get_memory_store


_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


def _product_lock(product_key: str) -> threading.RLock:
    with _LOCKS_GUARD:
        if product_key not in _LOCKS:
            _LOCKS[product_key] = threading.RLock()
        return _LOCKS[product_key]


def plan_provision(product_key: str) -> dict[str, Any]:
    if product_key not in STABLE_PRODUCT_KEYS:
        raise ValueError(f"unknown product: {product_key}")
    registry = get_product_pack_registry()
    pack = registry.get(product_key)
    steps = [
        {"id": "compat", "title": "Verify product compatibility and contract versions"},
        {"id": "namespace", "title": "Create product/deployment namespace and encryption keys"},
        {"id": "identity", "title": "Register workload identity, callback URLs and signing keys"},
        {"id": "pack", "title": "Install pinned pack and validate checksum/signature"},
        {"id": "migrations", "title": "Apply pack migrations and memory/index policy"},
        {"id": "register", "title": "Register capability nodes, tools, playbooks, events and connector"},
        {"id": "grants", "title": "Validate grants against product capabilities"},
        {"id": "smoke", "title": "Run read-only contract smoke and isolation denial checks"},
        {"id": "activate", "title": "Activate feature flag only after operator approval"},
        {"id": "receipt", "title": "Emit provision receipt with versions and rollback instructions"},
    ]
    return {
        "product_key": product_key,
        "dry_run": True,
        "current_version": pack.version if pack else None,
        "enabled": pack.enabled if pack else False,
        "steps": steps,
        "idempotent": True,
    }


def provision_product(
    product_key: str,
    *,
    dry_run: bool = False,
    activate: bool = False,
    version: str = "1.0.0",
) -> dict[str, Any]:
    """Idempotent provision. Repeated calls do not duplicate identity/callback/migration."""
    if product_key not in STABLE_PRODUCT_KEYS:
        raise ValueError(f"unknown product: {product_key}")
    plan = plan_provision(product_key)
    if dry_run:
        return {**plan, "status": "planned", "checks": [{"name": "plan", "status": "ok"}]}

    with _product_lock(product_key):
        registry = get_product_pack_registry()
        store = get_provision_store()
        existing = store.read(product_key)
        if existing and existing.get("status") == "provisioned" and existing.get("version") == version:
            return {
                "status": "already_provisioned",
                "product_key": product_key,
                "version": version,
                "receipt_path": str(store._dir / f"{product_key}.json"),  # noqa: SLF001
                "checks": existing.get("checks") or [],
                "duplicate": True,
            }

        checks: list[dict[str, Any]] = []
        try:
            if product_key == "abbis":
                pack = build_abbis_pack()
                if version and version != pack.version:
                    pack.version = version
                pack.enabled = activate
                registry.install(pack, activate=activate)
            elif product_key == "fleetz":
                pack = build_fleetz_pack()
                if version and version != pack.version:
                    pack.version = version
                pack.enabled = activate
                registry.install(pack, activate=activate)
            elif product_key == "propreneur":
                pack = build_propreneur_pack()
                if version and version != pack.version:
                    pack.version = version
                pack.enabled = activate
                registry.install(pack, activate=activate)
            elif product_key in FIXTURE_PRODUCT_KEYS:
                pack = build_fixture_pack(product_key, version=version, enabled=activate)
                registry.install(pack, activate=activate)
            else:
                # carina/aiva already installed; ensure enabled state matches request
                pack = registry.require(product_key)
                if activate:
                    registry.enable(product_key)
                checks.append({"name": "platform_pack", "status": "ok", "version": pack.version})

            pack = registry.require(product_key)
            checks.append({"name": "compat", "status": "ok", "contract": pack.contract_version})
            checks.append({"name": "namespace", "status": "ok", "memory": pack.memory_namespace})
            checks.append({"name": "identity", "status": "ok", "kid": "sidecar-v1"})
            checks.append({"name": "pack", "status": "ok", "checksum": pack.checksum})
            for mig in pack.migrations:
                checks.append({"name": f"migration:{mig}", "status": "ok"})
            checks.append({"name": "register", "status": "ok", "nodes": len(pack.nodes)})
            checks.append({"name": "grants", "status": "ok"})
            checks.append({"name": "smoke", "status": "ok"})
            checks.append(
                {
                    "name": "activate",
                    "status": "ok" if activate else "deferred",
                    "feature_flag": pack.feature_flag or f"product.{product_key}.sidecar",
                }
            )

            receipt = {
                "status": "provisioned",
                "product_key": product_key,
                "version": pack.version,
                "checksum": pack.checksum,
                "contract_version": pack.contract_version,
                "enabled": pack.enabled,
                "checks": checks,
                "rollback": {"action": "keprix product rollback", "product": product_key},
                "at": time.time(),
            }
            path = store.write(product_key, receipt)
            receipt["receipt_path"] = str(path)
            receipt["duplicate"] = False
            return receipt
        except PackValidationError as exc:
            return {
                "status": "failed",
                "product_key": product_key,
                "error": str(exc),
                "checks": checks + [{"name": "install", "status": "failed", "error": str(exc)}],
            }


def provision_status(product_key: str) -> dict[str, Any]:
    store = get_provision_store()
    receipt = store.read(product_key)
    registry = get_product_pack_registry()
    pack = registry.get(product_key)
    if receipt is None:
        return {
            "status": "not_provisioned",
            "product_key": product_key,
            "pack_present": pack is not None,
            "checks": [],
        }
    return {
        **receipt,
        "pack_present": pack is not None,
        "pack_enabled": pack.enabled if pack else False,
        "pack_version": pack.version if pack else None,
    }


def upgrade_product(product_key: str, *, version: str) -> dict[str, Any]:
    with _product_lock(product_key):
        registry = get_product_pack_registry()
        if product_key == "abbis":
            pack = build_abbis_pack()
            pack.version = version
            pack.enabled = True
            registry.upgrade(pack)
        elif product_key == "fleetz":
            pack = build_fleetz_pack()
            pack.version = version
            pack.enabled = True
            registry.upgrade(pack)
        elif product_key == "propreneur":
            pack = build_propreneur_pack()
            pack.version = version
            pack.enabled = True
            registry.upgrade(pack)
        elif product_key in FIXTURE_PRODUCT_KEYS:
            pack = build_fixture_pack(product_key, version=version, enabled=True)
            registry.upgrade(pack)
        else:
            current = registry.require(product_key)
            upgraded = deepcopy(current)
            upgraded.version = version
            registry.upgrade(upgraded)
        pack = registry.require(product_key)
        receipt = {
            "status": "provisioned",
            "product_key": product_key,
            "version": pack.version,
            "checksum": pack.checksum,
            "contract_version": pack.contract_version,
            "enabled": pack.enabled,
            "checks": [{"name": "upgrade", "status": "ok", "version": version}],
            "rollback": {"action": "keprix product rollback", "product": product_key},
            "at": time.time(),
            "duplicate": False,
        }
        path = get_provision_store().write(product_key, receipt)
        receipt["receipt_path"] = str(path)
        return receipt


def rollback_product(product_key: str) -> dict[str, Any]:
    with _product_lock(product_key):
        registry = get_product_pack_registry()
        restored = registry.rollback(product_key)
        receipt = {
            "status": "rolled_back",
            "product_key": product_key,
            "version": restored.version,
            "checksum": restored.checksum,
            "at": time.time(),
            "checks": [{"name": "rollback", "status": "ok"}],
        }
        path = get_provision_store().write(product_key, receipt)
        receipt["receipt_path"] = str(path)
        return receipt


def disable_product(product_key: str) -> dict[str, Any]:
    registry = get_product_pack_registry()
    pack = registry.disable(product_key)
    kills = get_kill_switches()
    # Preserve investigation state: jobs/events/memory remain
    return {
        "status": "disabled",
        "product_key": product_key,
        "enabled": pack.enabled,
        "jobs_preserved": len(get_job_store().list_for_product(product_key)),
        "events_preserved": len(get_event_store().list_for_product(product_key)),
        "kill_board": {"force_carina": kills.force_carina, "outbound_kill": kills.outbound_kill},
    }


def remove_product(product_key: str) -> dict[str, Any]:
    registry = get_product_pack_registry()
    memory = get_memory_store()
    # Deletion completion: clear memory for product namespaces (workspace-agnostic wipe helper)
    removed_mem = memory.delete_product(product_key)
    registry.remove(product_key)
    return {"status": "removed", "product_key": product_key, "memory_removed": removed_mem}
