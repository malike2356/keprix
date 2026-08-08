"""Keprix Universal Sidecar HTTP client."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Iterator
from typing import Any
from urllib.parse import urljoin

import httpx


class SidecarClient:
    """Client for `/sidecar/v1` (mounted :3333 or sidecar-only :3360)."""

    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        *,
        project_key: str | None = None,
        timeout: float = 60.0,
        webhook_secret: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token or ""
        self.project_key = project_key
        self.timeout = timeout
        self.webhook_secret = webhook_secret
        self._prefix = f"{self.base_url}/sidecar/v1"

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if extra:
            headers.update(extra)
        return headers

    def _project(self, project_key: str | None = None) -> str:
        key = project_key or self.project_key
        if not key:
            raise ValueError("project_key is required")
        return key

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        stream: bool = False,
    ) -> Any:
        url = urljoin(self._prefix + "/", path.lstrip("/"))
        with httpx.Client(timeout=self.timeout) as client:
            response = client.request(
                method,
                url,
                headers=self._headers(),
                json=json_body,
            )
            if stream:
                response.raise_for_status()
                return response
            if response.status_code >= 400:
                raise RuntimeError(f"{method} {path} failed: {response.status_code} {response.text}")
            if not response.content:
                return {}
            return response.json()

    def pair_bootstrap(
        self,
        pairing_code: str,
        *,
        project_key: str | None = None,
        deployment: str = "local-dev",
        environment: str = "local",
        requested_scopes: list[str] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "pairing_code": pairing_code,
            "project_key": self._project(project_key),
            "deployment": deployment,
            "environment": environment,
        }
        if requested_scopes is not None:
            body["requested_scopes"] = requested_scopes
        result = self._request("POST", "/pair/bootstrap", json_body=body)
        token = result.get("access_token") or result.get("token")
        if isinstance(token, str) and token:
            self.token = token
        return result

    def health(self, project_key: str | None = None) -> dict[str, Any]:
        key = project_key or self.project_key
        if key:
            return self._request("GET", f"/projects/{key}/health")
        return self._request("GET", "/health")

    def capabilities(self, project_key: str | None = None) -> dict[str, Any]:
        key = self._project(project_key)
        return self._request("GET", f"/projects/{key}/capabilities")

    def session(
        self,
        *,
        purpose: str,
        tenant_id: str,
        actor_id: str,
        project_key: str | None = None,
        grants: list[str] | None = None,
    ) -> dict[str, Any]:
        key = self._project(project_key)
        body: dict[str, Any] = {
            "purpose": purpose,
            "tenant_id": tenant_id,
            "actor_id": actor_id,
        }
        if grants is not None:
            body["grants"] = grants
        return self._request("POST", f"/projects/{key}/sessions", json_body=body)

    def invoke(
        self,
        node: str,
        input: dict[str, Any] | None = None,
        *,
        purpose: str = "invoke",
        project_key: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        key = self._project(project_key)
        body: dict[str, Any] = {"node": node, "input": input or {}, "purpose": purpose}
        if session_id:
            body["session_id"] = session_id
        return self._request("POST", f"/projects/{key}/invoke", json_body=body)

    def jobs(
        self,
        node: str,
        input: dict[str, Any] | None = None,
        *,
        purpose: str = "job",
        project_key: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        key = self._project(project_key)
        body: dict[str, Any] = {"node": node, "input": input or {}, "purpose": purpose}
        if idempotency_key:
            body["idempotency_key"] = idempotency_key
        return self._request("POST", f"/projects/{key}/jobs", json_body=body)

    def get_job(self, job_id: str, *, project_key: str | None = None) -> dict[str, Any]:
        key = self._project(project_key)
        return self._request("GET", f"/projects/{key}/jobs/{job_id}")

    def cancel(self, job_id: str, *, project_key: str | None = None) -> dict[str, Any]:
        key = self._project(project_key)
        return self._request("POST", f"/projects/{key}/jobs/{job_id}/cancel", json_body={})

    def send_event(
        self,
        event: dict[str, Any],
        *,
        project_key: str | None = None,
    ) -> dict[str, Any]:
        key = self._project(project_key)
        return self._request("POST", f"/projects/{key}/events", json_body=event)

    def stream_events(
        self,
        *,
        project_key: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Iterate SSE JSON payloads from `/events/stream`."""
        key = self._project(project_key)
        url = f"{self._prefix}/projects/{key}/events/stream"
        with httpx.Client(timeout=None) as client:
            with client.stream("GET", url, headers=self._headers()) as response:
                response.raise_for_status()
                data_lines: list[str] = []
                for line in response.iter_lines():
                    if line is None:
                        continue
                    if line.startswith("data:"):
                        data_lines.append(line[5:].lstrip())
                    elif line == "" and data_lines:
                        raw = "\n".join(data_lines)
                        data_lines = []
                        try:
                            yield json.loads(raw)
                        except json.JSONDecodeError:
                            yield {"raw": raw}

    def approval_decision(
        self,
        approval_id: str,
        decision: str,
        *,
        actor_id: str,
        project_key: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        key = self._project(project_key)
        body: dict[str, Any] = {"decision": decision, "actor_id": actor_id}
        if reason:
            body["reason"] = reason
        return self._request(
            "POST",
            f"/projects/{key}/approvals/{approval_id}/decision",
            json_body=body,
        )

    def verify_webhook(
        self,
        body: bytes | str,
        signature_header: str,
        *,
        timestamp_header: str | None = None,
        max_skew_seconds: int = 300,
        secret: str | None = None,
    ) -> bool:
        """Verify HMAC-SHA256 webhook signature (`t=...,v1=...` or raw hex)."""
        secret_value = secret or self.webhook_secret
        if not secret_value:
            raise ValueError("webhook secret required")
        raw = body.encode("utf-8") if isinstance(body, str) else body
        ts = None
        provided = signature_header.strip()
        if "v1=" in provided:
            parts = dict(
                piece.split("=", 1) for piece in provided.split(",") if "=" in piece
            )
            ts = parts.get("t")
            provided = parts.get("v1", "")
        if timestamp_header and ts is None:
            ts = timestamp_header
        if ts is not None:
            try:
                if abs(int(time.time()) - int(ts)) > max_skew_seconds:
                    return False
            except ValueError:
                return False
            signed = f"{ts}.".encode("utf-8") + raw
        else:
            signed = raw
        digest = hmac.new(secret_value.encode("utf-8"), signed, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, provided.lower())

    def connector_test(
        self,
        connector_key: str,
        *,
        path_params: dict[str, Any] | None = None,
        project_key: str | None = None,
    ) -> dict[str, Any]:
        key = self._project(project_key)
        return self._request(
            "POST",
            f"/projects/{key}/connectors/{connector_key}/test",
            json_body={"path_params": path_params or {}},
        )
