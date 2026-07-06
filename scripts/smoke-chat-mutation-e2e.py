#!/usr/bin/env python3
"""Live smoke test: /chat mutation stream with pause-until-approve."""

from __future__ import annotations

import json
import os
import sys
import threading
import time

import httpx

BASE = os.environ.get("KEPRIX_SMOKE_BASE_URL", "http://127.0.0.1:3333").rstrip("/")
USERNAME = os.environ.get("KEPRIX_SMOKE_USER", os.environ.get("KEPRIX_ADMIN_EMAIL", "admin"))
PASSWORD = os.environ.get("KEPRIX_SMOKE_PASSWORD", os.environ.get("KEPRIX_ADMIN_PASSWORD", ""))
STREAM_TIMEOUT_S = float(os.environ.get("KEPRIX_SMOKE_STREAM_TIMEOUT", "120"))


def main() -> int:
    if not PASSWORD:
        print("Set KEPRIX_ADMIN_PASSWORD or KEPRIX_SMOKE_PASSWORD", file=sys.stderr)
        return 2

    print(f"Smoke: login at {BASE}", flush=True)
    with httpx.Client(base_url=BASE, timeout=STREAM_TIMEOUT_S) as client:
        login = client.post("/api/auth/login", json={"username": USERNAME, "password": PASSWORD})
        login.raise_for_status()
        token = login.json().get("token")
        if not token:
            print("Login failed:", login.text, file=sys.stderr)
            return 1

        headers = {"Authorization": f"Bearer {token}"}
        session = client.post("/api/conversations", headers=headers, json={"title": "Smoke mutation"})
        session.raise_for_status()
        session_id = session.json()["id"]
        print(f"Session: {session_id}", flush=True)

        events: list[dict] = []
        mutation_id: str | None = None
        approve_body: dict = {}
        stream_error: list[str] = []
        ready = threading.Event()

        def approve_worker() -> None:
            if not ready.wait(timeout=STREAM_TIMEOUT_S):
                return
            try:
                with httpx.Client(base_url=BASE, timeout=STREAM_TIMEOUT_S) as approve_client:
                    response = approve_client.post(
                        f"/api/mutations/{mutation_id}/approve",
                        headers=headers,
                        params={"session_id": session_id},
                    )
                    response.raise_for_status()
                    approve_body.update(response.json())
                    print("  approve stream_waiting:", approve_body.get("stream_waiting"), flush=True)
            except Exception as exc:
                stream_error.append(f"approve failed: {exc}")

        worker = threading.Thread(target=approve_worker, daemon=True)
        worker.start()

        started = time.time()
        try:
            with client.stream(
                "POST",
                f"/api/conversations/{session_id}/messages",
                headers={**headers, "Accept": "application/x-ndjson"},
                json={
                    "content": "fetch AAPL stock price",
                    "file_ids": [],
                    "model": "deepseek:deepseek-chat",
                },
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    event = json.loads(line)
                    events.append(event)
                    print("  event:", event.get("event"), flush=True)
                    if event.get("event") == "mutation" and event.get("id"):
                        mutation_id = str(event["id"])
                        print(f"  approving {mutation_id} while stream open...", flush=True)
                        ready.set()
        except Exception as exc:
            stream_error.append(str(exc))

        worker.join(timeout=30)
        elapsed = time.time() - started

    if stream_error:
        print("Stream error:", stream_error[0], file=sys.stderr)
        return 1
    if not mutation_id:
        print("No mutation event received", file=sys.stderr)
        return 1
    if approve_body.get("stream_waiting") is not True:
        print("Expected stream_waiting=true on approve response:", approve_body, file=sys.stderr)
        return 1

    text = "".join(event.get("content", "") for event in events if event.get("event") == "text_delta")
    if "Retrying your request now" not in text:
        print("Stream never resumed after approve. text_delta:", repr(text[:500]), file=sys.stderr)
        return 1

    if not any(event.get("event") == "message_done" for event in events):
        print("message_done missing", file=sys.stderr)
        return 1

    print(f"OK: mutation E2E in {elapsed:.1f}s ({len(events)} events)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
