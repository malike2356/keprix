"""CLI handlers for ``keprix sidecar``."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import uuid
from pathlib import Path


def _print(data, *, as_json: bool, plain: str = "") -> None:
    if as_json:
        print(json.dumps(data, indent=2, default=str))
    elif plain:
        print(plain)
    else:
        print(json.dumps(data, indent=2, default=str))


def _starter_manifest(project_key: str, base_url: str) -> dict:
    return {
        "contract_version": "1.0.0",
        "project_key": project_key,
        "display_name": project_key.replace("-", " ").title(),
        "deployment": "local",
        "environment": "local",
        "base_url": base_url,
        "auth": {"profile": "bearer", "vault_ref": "env:KEPRIX_PROJECT_TOKEN"},
        "capabilities": [
            {"node": "summarise", "version": "1.0.0"},
            {"node": "classify", "version": "1.0.0"},
            {"node": "project.read", "version": "1.0.0"},
        ],
        "egress": {
            "allow_loopback": base_url.startswith("http://127.") or "localhost" in base_url,
        },
        "memory": {"mode": "ephemeral"},
        "budgets": {"requests_per_minute": 120, "jobs_concurrent": 10},
    }


def cmd_sidecar(args) -> int:
    cmd = getattr(args, "sidecar_command", None)
    as_json = bool(getattr(args, "json", False))

    if cmd == "init":
        path = Path(args.path)
        if path.exists():
            _print({"error": "already_exists", "path": str(path)}, as_json=as_json, plain=f"Refusing to overwrite {path}")
            return 1
        manifest = _starter_manifest(args.project_key, args.base_url)
        import yaml

        path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
        _print({"ok": True, "path": str(path), "project_key": args.project_key}, as_json=as_json, plain=f"Wrote {path}")
        return 0

    if cmd == "validate":
        from keprix.universal_sidecar.manifest import validate_manifest

        result = validate_manifest(args.manifest)
        _print(result.as_dict(), as_json=True if as_json else True)
        return 0 if result.ok else 1

    if cmd == "diff":
        from keprix.universal_sidecar.manifest import diff_manifests, load_manifest

        out = diff_manifests(load_manifest(args.old_manifest), load_manifest(args.new_manifest))
        _print(out, as_json=True)
        return 0

    if cmd == "explain":
        from keprix.universal_sidecar.manifest import explain_manifest, load_manifest

        _print(explain_manifest(load_manifest(args.manifest)), as_json=True)
        return 0

    if cmd == "doctor":
        checks = []
        from keprix.universal_sidecar.contract import CONTRACT_VERSION, DEFAULT_SIDECAR_PORT

        checks.append({"name": "contract_version", "ok": True, "detail": CONTRACT_VERSION})
        checks.append({"name": "default_port", "ok": True, "detail": str(DEFAULT_SIDECAR_PORT)})
        if args.manifest:
            from keprix.universal_sidecar.manifest import validate_manifest

            result = validate_manifest(args.manifest)
            checks.append({"name": "manifest", "ok": result.ok, "detail": result.digest[:12] if result.digest else ""})
            for issue in result.issues:
                if issue.severity == "error":
                    checks.append({"name": f"issue:{issue.path}", "ok": False, "detail": issue.reason})
        host = os.environ.get("KEPRIX_SIDECAR_HOST", "127.0.0.1")
        checks.append(
            {
                "name": "bind_host",
                "ok": host in {"127.0.0.1", "localhost", "::1"}
                or os.environ.get("KEPRIX_SIDECAR_ALLOW_PUBLIC") == "1"
                or bool(os.environ.get("KEPRIX_UNIVERSAL_SIDECAR_TOKEN_SECRET")),
                "detail": host,
            }
        )
        ok = all(c["ok"] for c in checks)
        _print({"ok": ok, "checks": checks}, as_json=True)
        return 0 if ok else 1

    if cmd == "plan":
        from keprix.universal_sidecar.manifest import load_manifest, plan_apply

        previous = load_manifest(args.previous) if args.previous else None
        out = plan_apply(previous, load_manifest(args.manifest))
        _print(out, as_json=True)
        return 0 if out.get("can_apply") else 1

    if cmd == "apply":
        from keprix.universal_sidecar.registry import get_project_registry

        try:
            result = get_project_registry().load_file(args.manifest, confirm_risky=bool(args.confirm_risky))
        except PermissionError as exc:
            _print({"error": str(exc)}, as_json=True)
            return 2
        except ValueError as exc:
            _print({"error": str(exc)}, as_json=True)
            return 1
        _print(result, as_json=True)
        return 0

    if cmd == "export-redacted":
        from keprix.universal_sidecar.manifest import export_redacted, load_manifest

        data = export_redacted(load_manifest(args.manifest))
        if args.out:
            Path(args.out).write_text(json.dumps(data, indent=2), encoding="utf-8")
            _print({"ok": True, "out": args.out}, as_json=as_json, plain=f"Wrote {args.out}")
        else:
            _print(data, as_json=True)
        return 0

    if cmd == "start":
        if args.host:
            os.environ["KEPRIX_SIDECAR_HOST"] = args.host
        if args.port:
            os.environ["KEPRIX_SIDECAR_PORT"] = str(args.port)
        if args.config:
            from keprix.universal_sidecar.registry import get_project_registry

            get_project_registry().load_file(args.config, confirm_risky=True)
        if args.profile == "mounted":
            print(
                "Note: mounted profile uses the main Keprix API. "
                "Starting sidecar-only process anyway; prefer keprix gateway for mounted mode.",
                file=sys.stderr,
            )
        from keprix.universal_sidecar.app import main as sidecar_main

        sidecar_main()
        return 0

    if cmd == "quickstart":
        path = Path(args.path)
        if not path.exists():
            import yaml

            path.write_text(
                yaml.safe_dump(_starter_manifest(args.project_key, "http://127.0.0.1:8080"), sort_keys=False),
                encoding="utf-8",
            )
        from keprix.universal_sidecar.registry import get_project_registry

        result = get_project_registry().load_file(path, confirm_risky=True)
        out = {
            "ok": True,
            "applied": result,
            "next": [
                f"keprix sidecar pair {args.project_key}",
                f"keprix sidecar capabilities {args.project_key}",
                "keprix sidecar start --config " + str(path),
            ],
        }
        _print(out, as_json=True)
        return 0

    if cmd == "pair":
        from keprix.universal_sidecar.pairing import get_pairing_store
        from keprix.universal_sidecar.registry import get_project_registry

        row = get_project_registry().get(args.project_key)
        if not row:
            _print({"error": "project not applied; run sidecar apply first"}, as_json=True)
            return 1
        store = get_pairing_store()
        if args.approve:
            try:
                result = store.approve_code(args.approve)
            except (KeyError, ValueError) as exc:
                _print({"error": str(exc)}, as_json=True)
                return 1
            _print(result, as_json=True)
            return 0
        scopes = [s.strip() for s in args.scopes.split(",") if s.strip()]
        try:
            result = store.create_code(
                project_key=args.project_key,
                deployment=str(row["manifest"].get("deployment") or "local"),
                environment=str(row["manifest"].get("environment") or "local"),
                base_url=args.base_url or str(row["manifest"].get("base_url") or ""),
                callback_urls=list(row["manifest"].get("callback_urls") or []),
                requested_scopes=scopes,
            )
        except PermissionError as exc:
            _print({"error": str(exc)}, as_json=True)
            return 2
        _print(result, as_json=True)
        return 0

    if cmd == "capabilities":
        from keprix.universal_sidecar.nodes import catalog_for_project

        try:
            nodes = catalog_for_project(args.project_key)
        except KeyError:
            _print({"error": "unknown project"}, as_json=True)
            return 1
        _print({"project_key": args.project_key, "nodes": nodes}, as_json=True)
        return 0

    if cmd == "invoke":
        import asyncio

        from keprix.universal_sidecar.nodes import NodeError, invoke_safe_node
        from keprix.universal_sidecar.pairing import get_pairing_store
        from keprix.universal_sidecar.registry import get_project_registry

        try:
            grants = get_project_registry().grants_for(args.project_key)
        except KeyError:
            _print({"error": "unknown project"}, as_json=True)
            return 1
        if args.token:
            try:
                token = get_pairing_store().parse(args.token)
                grants = token.grants
            except ValueError as exc:
                _print({"error": str(exc)}, as_json=True)
                return 1
        try:
            payload = json.loads(args.input)
        except json.JSONDecodeError as exc:
            _print({"error": f"invalid input JSON: {exc}"}, as_json=True)
            return 2
        try:
            result = asyncio.run(
                invoke_safe_node(
                    project_key=args.project_key,
                    node_key=args.node,
                    input_payload=payload,
                    grants=frozenset(grants),
                    correlation_id=f"cli-{uuid.uuid4().hex[:8]}",
                )
            )
        except NodeError as exc:
            _print({"error": exc.message, "code": exc.code}, as_json=True)
            return 1
        _print(result, as_json=True)
        return 0

    if cmd == "job":
        from keprix.universal_sidecar.jobs import get_job_service

        jobs = get_job_service()
        if args.job_id and args.cancel:
            row = jobs.cancel(args.job_id, project_key=args.project_key)
            if not row:
                _print({"error": "not found"}, as_json=True)
                return 1
            _print({"job": row}, as_json=True)
            return 0
        if args.job_id:
            row = jobs.get(args.job_id, project_key=args.project_key)
            if not row:
                _print({"error": "not found"}, as_json=True)
                return 1
            _print({"job": row}, as_json=True)
            return 0
        try:
            payload = json.loads(args.input)
        except json.JSONDecodeError as exc:
            _print({"error": f"invalid input JSON: {exc}"}, as_json=True)
            return 2
        key = args.idempotency_key or f"cli-{uuid.uuid4().hex}"
        try:
            row = jobs.create(
                project_key=args.project_key,
                node_key=args.node,
                input_payload=payload,
                idempotency_key=key,
                correlation_id=f"cli-{uuid.uuid4().hex[:8]}",
            )
        except (PermissionError, ValueError, KeyError) as exc:
            _print({"error": str(exc)}, as_json=True)
            return 1
        _print({"job": row}, as_json=True)
        return 0

    if cmd == "watch":
        from keprix.universal_sidecar.events import get_event_service

        items = list(get_event_service().stream_events(args.project_key, cursor=args.cursor or None))
        _print({"events": items}, as_json=True)
        return 0

    if cmd == "send-event":
        from keprix.universal_sidecar.events import get_event_service

        try:
            data = json.loads(args.data)
        except json.JSONDecodeError as exc:
            _print({"error": f"invalid data JSON: {exc}"}, as_json=True)
            return 2
        event_id = args.id or f"evt_{uuid.uuid4().hex[:12]}"
        result = get_event_service().ingest_inbound(
            project_key=args.project_key,
            envelope={
                "id": event_id,
                "type": args.type,
                "source": args.source,
                "data": data,
                "deployment": "local",
            },
        )
        _print(result, as_json=True)
        return 0

    if cmd == "verify-webhook":
        secret = args.secret or os.environ.get("KEPRIX_SIDECAR_WEBHOOK_SECRET", "dev-webhook-secret")
        expected = hmac.new(secret.encode(), args.body.encode(), hashlib.sha256).hexdigest()
        ok = hmac.compare_digest(expected, args.signature)
        _print({"ok": ok, "expected_prefix": expected[:8]}, as_json=True)
        return 0 if ok else 1

    if cmd == "connector-test":
        from keprix.universal_sidecar.connector import ConnectorError, get_connector

        try:
            params = json.loads(args.params)
        except json.JSONDecodeError as exc:
            _print({"error": f"invalid params JSON: {exc}"}, as_json=True)
            return 2
        try:
            result = get_connector(args.project_key).read(args.operation, params)
        except (ConnectorError, KeyError) as exc:
            detail = getattr(exc, "message", str(exc))
            code = getattr(exc, "code", "error")
            _print({"error": detail, "code": code}, as_json=True)
            return 1
        _print(result, as_json=True)
        return 0

    if cmd == "conformance":
        from keprix.universal_sidecar.conformance import run_conformance

        report = run_conformance()
        _print(report, as_json=True)
        return 0 if report.get("ok") else 1

    _print({"error": f"unknown sidecar command: {cmd}"}, as_json=True)
    return 2
