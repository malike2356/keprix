"""Discovery job runner: durable checkpoints, cancel, retry, Soft Wall materialize."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from keprix.crm.store import CrmStore, get_crm_store
from keprix.discovery.limits import retry_delay
from keprix.discovery.materialize import materialize_candidates
from keprix.discovery.models import (
    DiscoverLimits,
    DiscoverQuery,
    JobStatus,
    LeadCandidate,
)
from keprix.discovery.registry import (
    AdapterDisabledError,
    AdapterNotConfiguredError,
    AdapterNotFoundError,
    DiscoveryRegistry,
    get_discovery_registry,
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class DiscoveryJobRunner:
    """Runs discovery adapters and persists DiscoveryJob rows on the CRM store."""

    def __init__(
        self,
        store: CrmStore | None = None,
        registry: DiscoveryRegistry | None = None,
    ) -> None:
        self._store = store or get_crm_store()
        self._registry = registry or get_discovery_registry()
        self._cancel_requested: set[str] = set()

    def create_job(
        self,
        workspace_id: str,
        adapter: str,
        *,
        query: str | dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        domain_pack: str = "generic",
        limits: dict[str, Any] | None = None,
        list_name: str | None = None,
        auto_materialize: bool = False,
        actor_type: str = "user",
        actor_id: str | None = None,
        icp_id: str | None = None,
        icp_version: int | None = None,
    ) -> dict[str, Any]:
        q_text = ""
        q_params: dict[str, Any] = dict(params or {})
        if isinstance(query, dict):
            q_text = str(query.get("text") or query.get("q") or "")
            for key, value in query.items():
                if key not in {"text", "q"}:
                    q_params.setdefault(key, value)
        elif query:
            q_text = str(query)

        # Resolve active ICP when caller did not pin one.
        if not icp_id:
            try:
                from keprix.crm import icp as icp_mod

                active = icp_mod.get_active_icp(self._store, workspace_id, pack=domain_pack)
                if active:
                    icp_id = str(active["id"])
                    icp_version = int(active.get("version") or 1)
            except Exception:
                pass
        if icp_id:
            q_params.setdefault("icp_id", icp_id)
            if icp_version is not None:
                q_params.setdefault("icp_version", icp_version)

        forecast = {"units": 0.0, "currency": "estimate", "note": "adapter unavailable"}
        try:
            ad = self._registry.require_ready(adapter)
            dq = DiscoverQuery(
                text=q_text,
                params=q_params,
                domain_pack=domain_pack,
                workspace_id=workspace_id,
            )
            forecast = ad.cost_forecast(dq, DiscoverLimits.from_dict(limits))
        except (AdapterNotFoundError, AdapterNotConfiguredError, AdapterDisabledError) as exc:
            forecast = {"units": 0.0, "error": str(exc), "status": "not_ready"}
        except Exception as exc:  # noqa: BLE001
            forecast = {"units": 0.0, "error": str(exc)}

        job = self._store.create_discovery_job(
            workspace_id,
            adapter,
            status=JobStatus.QUEUED,
            domain_pack=domain_pack,
            params={
                "query": q_text,
                "params": q_params,
                "limits": limits or {},
                "list_name": list_name,
                "auto_materialize": auto_materialize,
                "icp_id": icp_id,
                "icp_version": icp_version,
            },
            cost_estimate=float((forecast or {}).get("units") or 0),
            checkpoint={"cursor": 0, "candidates": [], "attempts": 0},
            actor_type=actor_type,
            actor_id=actor_id,
        )
        # Store forecast alongside params for UI.
        self._store.update_discovery_job(
            workspace_id,
            job["id"],
            params={
                **(job.get("params") or {}),
                "cost_forecast": forecast,
            },
            cost_estimate=float((forecast or {}).get("units") or 0),
        )
        if icp_id:
            try:
                from keprix.crm import icp as icp_mod

                icp_mod.stamp_entity_icp(
                    self._store,
                    workspace_id,
                    entity_type="discovery_job",
                    entity_id=job["id"],
                    icp_id=str(icp_id),
                    icp_version=int(icp_version or 1),
                )
            except Exception:
                pass
        return self._store.get_discovery_job(workspace_id, job["id"]) or job

    def request_cancel(self, workspace_id: str, job_id: str) -> dict[str, Any] | None:
        job = self._store.get_discovery_job(workspace_id, job_id)
        if not job:
            return None
        status = str(job.get("status") or "")
        if status in {JobStatus.DONE, JobStatus.CANCELLED, JobStatus.DEAD_LETTER}:
            return job
        self._cancel_requested.add(job_id)
        if status == JobStatus.QUEUED:
            return self._store.update_discovery_job(
                workspace_id,
                job_id,
                status=JobStatus.CANCELLED,
                finished_at=_utcnow(),
                error="cancelled before start",
            )
        return self._store.update_discovery_job(
            workspace_id,
            job_id,
            checkpoint={**(job.get("checkpoint") or {}), "cancel_requested": True},
        )

    def run_job(
        self,
        workspace_id: str,
        job_id: str,
        *,
        materialize: bool | None = None,
        approval_id: str | None = None,
        force: bool = False,
        max_retries: int = 2,
    ) -> dict[str, Any]:
        job = self._store.get_discovery_job(workspace_id, job_id)
        if not job:
            raise LookupError("discovery_job_not_found")

        status = str(job.get("status") or "")
        if status == JobStatus.CANCELLED:
            return {"job": job, "cancelled": True}
        if job_id in self._cancel_requested or (job.get("checkpoint") or {}).get("cancel_requested"):
            updated = self._store.update_discovery_job(
                workspace_id,
                job_id,
                status=JobStatus.CANCELLED,
                finished_at=_utcnow(),
                error="cancelled",
            )
            self._cancel_requested.discard(job_id)
            return {"job": updated, "cancelled": True}

        adapter_name = str(job.get("adapter") or "")
        params = dict(job.get("params") or {})
        q_text = str(params.get("query") or "")
        q_params = dict(params.get("params") or {})
        limits = DiscoverLimits.from_dict(params.get("limits") or {})
        domain_pack = str(job.get("domain_pack") or params.get("domain_pack") or "generic")
        checkpoint = dict(job.get("checkpoint") or {})
        cursor = int(checkpoint.get("cursor") or 0)
        prior_candidates = [
            LeadCandidate.from_dict(c)
            for c in (checkpoint.get("candidates") or [])
            if isinstance(c, dict)
        ]

        self._store.update_discovery_job(
            workspace_id,
            job_id,
            status=JobStatus.RUNNING,
            started_at=job.get("started_at") or _utcnow(),
            error=None,
        )

        try:
            adapter = self._registry.require_ready(adapter_name)
        except AdapterNotConfiguredError as exc:
            updated = self._fail(workspace_id, job_id, str(exc), dead_letter=False)
            return {"job": updated, "error": str(exc), "error_code": "not_configured"}
        except (AdapterDisabledError, AdapterNotFoundError) as exc:
            updated = self._fail(workspace_id, job_id, str(exc), dead_letter=False)
            return {"job": updated, "error": str(exc), "error_code": "adapter_unavailable"}

        query = DiscoverQuery(
            text=q_text,
            params=q_params,
            domain_pack=domain_pack,
            workspace_id=workspace_id,
        )

        attempts = int(checkpoint.get("attempts") or 0)
        last_error: str | None = None
        candidates = list(prior_candidates)

        while attempts <= max_retries:
            if job_id in self._cancel_requested:
                updated = self._store.update_discovery_job(
                    workspace_id,
                    job_id,
                    status=JobStatus.CANCELLED,
                    finished_at=_utcnow(),
                    error="cancelled",
                    checkpoint={**checkpoint, "cursor": cursor, "candidates": [c.to_dict() for c in candidates]},
                )
                self._cancel_requested.discard(job_id)
                return {"job": updated, "cancelled": True}

            if not self._registry.rate_limiter(adapter_name).allow():
                last_error = "rate_limited"
                attempts += 1
                time.sleep(retry_delay(attempts))
                continue

            try:
                fresh = adapter.discover(query, limits)
                self._registry.circuit(adapter_name).record_success()
                # Resume: append only beyond cursor by content_hash.
                seen = {c.content_hash for c in candidates if c.content_hash}
                for cand in fresh:
                    cand.domain_pack = cand.domain_pack or domain_pack
                    cand.ensure_hashes()
                    if cand.content_hash in seen:
                        continue
                    candidates.append(cand)
                    seen.add(cand.content_hash)
                cursor = len(candidates)
                checkpoint = {
                    "cursor": cursor,
                    "candidates": [c.to_dict() for c in candidates],
                    "attempts": attempts,
                }
                self._store.update_discovery_job(
                    workspace_id,
                    job_id,
                    checkpoint=checkpoint,
                    result_counts={"candidates": len(candidates)},
                )
                last_error = None
                break
            except Exception as exc:  # noqa: BLE001 - persist and retry
                last_error = str(exc)
                self._registry.circuit(adapter_name).record_failure()
                attempts += 1
                checkpoint = {
                    "cursor": cursor,
                    "candidates": [c.to_dict() for c in candidates],
                    "attempts": attempts,
                    "last_error": last_error,
                }
                self._store.update_discovery_job(workspace_id, job_id, checkpoint=checkpoint, error=last_error)
                if attempts <= max_retries:
                    time.sleep(retry_delay(attempts))

        if last_error:
            dead = attempts > max_retries
            updated = self._fail(workspace_id, job_id, last_error, dead_letter=dead, checkpoint=checkpoint)
            return {
                "job": updated,
                "error": last_error,
                "error_code": "dead_letter" if dead else "failed",
                "candidates": [c.to_dict() for c in candidates],
                "resumable": True,
            }

        do_materialize = params.get("auto_materialize") if materialize is None else materialize
        materialize_result: dict[str, Any] | None = None
        list_id = job.get("list_id")

        if do_materialize:
            materialize_result = materialize_candidates(
                workspace_id,
                candidates,
                list_name=params.get("list_name") or f"{adapter_name} discovery",
                domain_pack=domain_pack,
                source=adapter_name,
                job_id=job_id,
                store=self._store,
                approval_id=approval_id,
                force=force,
                actor_type=str(job.get("actor_type") or "system"),
                actor_id=job.get("actor_id"),
            )
            if materialize_result.get("blocked"):
                updated = self._store.update_discovery_job(
                    workspace_id,
                    job_id,
                    status=JobStatus.DONE,
                    finished_at=_utcnow(),
                    result_counts={
                        "candidates": len(candidates),
                        "materialize_blocked": True,
                    },
                    checkpoint={
                        **checkpoint,
                        "materialize_pending": True,
                        "candidates": [c.to_dict() for c in candidates],
                    },
                )
                return {
                    "job": updated,
                    "candidates": [c.to_dict() for c in candidates],
                    "materialize": materialize_result,
                    "deep_links": {
                        "job": f"/crm/jobs/{job_id}",
                        "approval": (materialize_result.get("approval") or {}).get("deep_link"),
                    },
                }
            list_id = materialize_result.get("list_id")

        updated = self._store.update_discovery_job(
            workspace_id,
            job_id,
            status=JobStatus.DONE,
            finished_at=_utcnow(),
            list_id=list_id,
            result_counts={
                "candidates": len(candidates),
                "created": (materialize_result or {}).get("created"),
                "reused": (materialize_result or {}).get("reused"),
                "merge_count": (materialize_result or {}).get("merge_count"),
            },
            checkpoint={
                **checkpoint,
                "candidates": [c.to_dict() for c in candidates],
                "materialize_pending": False,
            },
            error=None,
        )
        return {
            "job": updated,
            "candidates": [c.to_dict() for c in candidates],
            "materialize": materialize_result,
            "deep_links": {
                "job": f"/crm/jobs/{job_id}",
                "list": f"/crm/lists/{list_id}" if list_id else None,
                "merges": (materialize_result or {}).get("merges_deep_link"),
            },
        }

    def materialize_job(
        self,
        workspace_id: str,
        job_id: str,
        *,
        approval_id: str | None = None,
        force: bool = False,
        list_name: str | None = None,
    ) -> dict[str, Any]:
        job = self._store.get_discovery_job(workspace_id, job_id)
        if not job:
            raise LookupError("discovery_job_not_found")
        checkpoint = dict(job.get("checkpoint") or {})
        candidates = [
            LeadCandidate.from_dict(c)
            for c in (checkpoint.get("candidates") or [])
            if isinstance(c, dict)
        ]
        if not candidates:
            return {"error": "no_candidates", "job": job}
        params = dict(job.get("params") or {})
        result = materialize_candidates(
            workspace_id,
            candidates,
            list_name=list_name or params.get("list_name") or f"{job.get('adapter')} discovery",
            domain_pack=str(job.get("domain_pack") or "generic"),
            source=str(job.get("adapter") or "discovery"),
            job_id=job_id,
            store=self._store,
            approval_id=approval_id,
            force=force,
            actor_type=str(job.get("actor_type") or "user"),
            actor_id=job.get("actor_id"),
        )
        if result.get("blocked"):
            return {"job": job, "materialize": result, "blocked": True}
        updated = self._store.update_discovery_job(
            workspace_id,
            job_id,
            list_id=result.get("list_id"),
            result_counts={
                **(job.get("result_counts") or {}),
                "created": result.get("created"),
                "reused": result.get("reused"),
                "merge_count": result.get("merge_count"),
            },
            checkpoint={**checkpoint, "materialize_pending": False},
        )
        return {
            "job": updated,
            "materialize": result,
            "deep_links": {
                "job": f"/crm/jobs/{job_id}",
                "list": result.get("list_deep_link"),
                "merges": result.get("merges_deep_link"),
            },
        }

    def retry_dead_letter(self, workspace_id: str, job_id: str, **kwargs: Any) -> dict[str, Any]:
        job = self._store.get_discovery_job(workspace_id, job_id)
        if not job:
            raise LookupError("discovery_job_not_found")
        if str(job.get("status")) not in {JobStatus.DEAD_LETTER, JobStatus.FAILED}:
            return {"error": "not_retryable", "job": job}
        self._store.update_discovery_job(
            workspace_id,
            job_id,
            status=JobStatus.QUEUED,
            error=None,
            checkpoint={
                **(job.get("checkpoint") or {}),
                "attempts": 0,
                "last_error": None,
            },
        )
        return self.run_job(workspace_id, job_id, **kwargs)

    def _fail(
        self,
        workspace_id: str,
        job_id: str,
        error: str,
        *,
        dead_letter: bool,
        checkpoint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fields: dict[str, Any] = {
            "status": JobStatus.DEAD_LETTER if dead_letter else JobStatus.FAILED,
            "error": error,
            "finished_at": _utcnow(),
        }
        if checkpoint is not None:
            fields["checkpoint"] = checkpoint
        return self._store.update_discovery_job(workspace_id, job_id, **fields) or {}


def get_discovery_runner(store: CrmStore | None = None) -> DiscoveryJobRunner:
    return DiscoveryJobRunner(store=store)
