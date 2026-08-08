"""``keprix sidecar`` subcommand parser."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_sidecar_parser(subparsers: _SubParsersAction, *, cmd_sidecar: Callable) -> None:
    parser = subparsers.add_parser(
        "sidecar",
        help="Keprix Universal Sidecar: manifest, pair, invoke, jobs, conformance",
    )
    sub = parser.add_subparsers(dest="sidecar_command", required=True)

    init = sub.add_parser("init", help="Write a starter keprix.sidecar.yaml")
    init.add_argument("--path", default="keprix.sidecar.yaml")
    init.add_argument("--project-key", default="demo")
    init.add_argument("--base-url", default="http://127.0.0.1:8080")
    init.add_argument("--json", action="store_true")
    init.set_defaults(func=cmd_sidecar)

    validate = sub.add_parser("validate", help="Validate a project manifest")
    validate.add_argument("manifest", help="Path to keprix.sidecar.yaml or JSON")
    validate.add_argument("--json", action="store_true")
    validate.set_defaults(func=cmd_sidecar)

    diff = sub.add_parser("diff", help="Diff two manifests")
    diff.add_argument("old_manifest")
    diff.add_argument("new_manifest")
    diff.add_argument("--json", action="store_true")
    diff.set_defaults(func=cmd_sidecar)

    explain = sub.add_parser("explain", help="Explain a manifest")
    explain.add_argument("manifest")
    explain.add_argument("--json", action="store_true")
    explain.set_defaults(func=cmd_sidecar)

    doctor = sub.add_parser("doctor", help="Local sidecar doctor checks")
    doctor.add_argument("--manifest", default="")
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(func=cmd_sidecar)

    plan = sub.add_parser("plan", help="Plan apply of a manifest")
    plan.add_argument("manifest")
    plan.add_argument("--previous", default="")
    plan.add_argument("--json", action="store_true")
    plan.set_defaults(func=cmd_sidecar)

    apply = sub.add_parser("apply", help="Apply a manifest into the local registry")
    apply.add_argument("manifest")
    apply.add_argument("--confirm-risky", action="store_true")
    apply.add_argument("--json", action="store_true")
    apply.set_defaults(func=cmd_sidecar)

    export_r = sub.add_parser("export-redacted", help="Export redacted manifest for support")
    export_r.add_argument("manifest")
    export_r.add_argument("--out", default="")
    export_r.add_argument("--json", action="store_true")
    export_r.set_defaults(func=cmd_sidecar)

    start = sub.add_parser("start", help="Start sidecar-only HTTP process")
    start.add_argument("--host", default="")
    start.add_argument("--port", type=int, default=0)
    start.add_argument("--config", default="", help="Optional manifest to apply before start")
    start.add_argument("--profile", default="sidecar_only", choices=("sidecar_only", "mounted"))
    start.set_defaults(func=cmd_sidecar)

    quickstart = sub.add_parser("quickstart", help="Init + apply + print next steps")
    quickstart.add_argument("--path", default="keprix.sidecar.yaml")
    quickstart.add_argument("--project-key", default="demo")
    quickstart.add_argument("--json", action="store_true")
    quickstart.set_defaults(func=cmd_sidecar)

    pair = sub.add_parser("pair", help="Create or approve a pairing code")
    pair.add_argument("project_key")
    pair.add_argument("--approve", default="", help="Pairing code to approve")
    pair.add_argument("--scopes", default="discover,jobs,events,invoke:summarise")
    pair.add_argument("--base-url", default="")
    pair.add_argument("--json", action="store_true")
    pair.set_defaults(func=cmd_sidecar)

    capabilities = sub.add_parser("capabilities", help="List capability nodes for a project")
    capabilities.add_argument("project_key")
    capabilities.add_argument("--json", action="store_true")
    capabilities.set_defaults(func=cmd_sidecar)

    invoke = sub.add_parser("invoke", help="Invoke a safe node (local registry)")
    invoke.add_argument("project_key")
    invoke.add_argument("--node", required=True)
    invoke.add_argument("--input", default="{}", help="JSON input object")
    invoke.add_argument("--token", default="")
    invoke.add_argument("--json", action="store_true")
    invoke.set_defaults(func=cmd_sidecar)

    job = sub.add_parser("job", help="Create or inspect a job")
    job.add_argument("project_key")
    job.add_argument("--node", default="summarise")
    job.add_argument("--input", default="{}")
    job.add_argument("--idempotency-key", default="")
    job.add_argument("--job-id", default="")
    job.add_argument("--cancel", action="store_true")
    job.add_argument("--json", action="store_true")
    job.set_defaults(func=cmd_sidecar)

    watch = sub.add_parser("watch", help="Print recent SSE-style events for a project")
    watch.add_argument("project_key")
    watch.add_argument("--cursor", default="")
    watch.add_argument("--json", action="store_true")
    watch.set_defaults(func=cmd_sidecar)

    send_event = sub.add_parser("send-event", help="Ingest a CloudEvent into the local store")
    send_event.add_argument("project_key")
    send_event.add_argument("--id", default="")
    send_event.add_argument("--type", default="demo.ping")
    send_event.add_argument("--source", default="cli")
    send_event.add_argument("--data", default="{}")
    send_event.add_argument("--json", action="store_true")
    send_event.set_defaults(func=cmd_sidecar)

    verify = sub.add_parser("verify-webhook", help="Verify HMAC webhook signature")
    verify.add_argument("--body", required=True, help="Raw JSON body string")
    verify.add_argument("--signature", required=True)
    verify.add_argument("--secret", default="")
    verify.add_argument("--json", action="store_true")
    verify.set_defaults(func=cmd_sidecar)

    connector = sub.add_parser("connector-test", help="Dry-run a declared connector operation")
    connector.add_argument("project_key")
    connector.add_argument("--operation", required=True)
    connector.add_argument("--params", default="{}")
    connector.add_argument("--json", action="store_true")
    connector.set_defaults(func=cmd_sidecar)

    conformance = sub.add_parser("conformance", help="Run basic sidecar conformance suite")
    conformance.add_argument("--json", action="store_true")
    conformance.set_defaults(func=cmd_sidecar)
