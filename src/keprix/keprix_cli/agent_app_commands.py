"""Agent app CLI commands."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from keprix.agent_apps.deployment_bundle import build_deployment_bundle
from keprix.agent_apps.eval_runner import run_eval_suite
from keprix.agent_apps.catalog import list_catalog_templates
from keprix.agent_apps.local_runner import run_local
from keprix.agent_apps.registry import get_agent_app_registry, sample_app_dir
from keprix.agent_apps.scaffold import create_agent_app


def cmd_agent_app_list(_args) -> int:
    registry = get_agent_app_registry()
    apps = registry.list_apps()
    print(json.dumps({"apps": apps, "sample": str(sample_app_dir())}, indent=2))
    return 0


def cmd_agent_app_validate(args) -> int:
    source = Path(args.path).expanduser()
    result = get_agent_app_registry().validate_only(source)
    print(json.dumps(result, indent=2))
    return 0 if result.get("valid") else 1


def cmd_agent_app_install(args) -> int:
    source = Path(args.path).expanduser()
    validation = get_agent_app_registry().validate_only(source)
    if not validation.get("valid"):
        print(json.dumps(validation, indent=2))
        return 1
    installed = get_agent_app_registry().install(source)
    print(json.dumps(installed, indent=2))
    return 0


def cmd_agent_app_run(args) -> int:
    source = Path(args.path).expanduser()
    result = run_local(source, input_text=args.input or "")
    print(json.dumps(result, indent=2))
    return 0


def cmd_agent_app_eval(args) -> int:
    source = Path(args.path).expanduser()
    result = run_eval_suite(source)
    print(json.dumps(result, indent=2))
    return 0 if result.get("success") else 1


def cmd_agent_app_bundle(args) -> int:
    source = Path(args.path).expanduser()
    output = Path(args.output).expanduser() if args.output else Path(tempfile.gettempdir()) / f"{source.name}.zip"
    result = build_deployment_bundle(source, output, target=args.target)
    print(json.dumps(result, indent=2))
    return 0


def cmd_agent_app_create(args) -> int:
    dest = Path(args.path).expanduser() if args.path else Path.cwd() / args.name
    try:
        result = create_agent_app(dest, args.name, template=args.template, force=bool(args.force))
    except (FileExistsError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0 if result.get("valid") else 1


def cmd_agent_app_catalog_list(_args) -> int:
    templates = list_catalog_templates()
    print(json.dumps({"templates": templates}, indent=2))
    return 0
