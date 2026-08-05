"""Shared quota runtime objects."""

from __future__ import annotations

from keprix.quotas.fairness_scheduler import FairnessScheduler
from keprix.quotas.quota_enforcer import QuotaEnforcer
from keprix.quotas.quota_store import QuotaStore

_store = QuotaStore()
_enforcer = QuotaEnforcer(store=_store)
_scheduler = FairnessScheduler(store=_store)


def get_quota_store() -> QuotaStore:
    return _store


def get_quota_enforcer() -> QuotaEnforcer:
    return _enforcer


def get_fairness_scheduler() -> FairnessScheduler:
    return _scheduler
