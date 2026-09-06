"""Admin-only owned property data layer tools."""

from __future__ import annotations

import json

from keprix.property_data.refresh import dataset_status, refresh_all
from keprix.property_data.api import lookup
from keprix.property_data.discovery import discover, get_config, set_config
from keprix.property_data.diligence import run_due_diligence
from keprix.property_data.saved_searches import create_saved_search, list_saved_searches, run_saved_search
from keprix.property_calculators import list_strategies
from keprix.property_calculators.service import calculator_rules, calculator_settings, run_workspace_calculator, update_calculator_settings
import asyncio
from keprix.public_api.keys import get_api_key_store
from keprix.public_api.schemas import CreateApiKeyRequest
from keprix.tools.registry import registry


def property_data_status(args: dict) -> str:
    return json.dumps(dataset_status(), default=str)


def property_data_refresh(args: dict) -> str:
    return json.dumps(refresh_all() if args.get("admin") else {"status": "admin_required"}, default=str)


def property_data_api_endpoint_test(args: dict) -> str:
    return json.dumps(lookup(uprn=str(args.get("uprn") or ""), postcode=str(args.get("postcode") or "")), default=str)


def property_data_api_key_create(args: dict) -> str:
    if not args.get("admin"):
        return json.dumps({"status": "admin_required"})
    response = get_api_key_store().create(CreateApiKeyRequest(
        name=str(args.get("name") or "property-api"),
        workspace_id=str(args.get("workspace_id") or "default"),
        permissions={"api.property.read": "read"},
    ))
    return json.dumps(response.model_dump(), default=str)


def property_discover(args: dict) -> str:
    return json.dumps(discover(str(args.get("workspace_id") or "default"), materialize=bool(args.get("materialize")),), default=str)


def property_discovery_config_get(args: dict) -> str:
    return json.dumps(get_config(str(args.get("workspace_id") or "default")), default=str)


def property_discovery_config_set(args: dict) -> str:
    if not args.get("admin"):
        return json.dumps({"status": "admin_required"})
    values = {key: args[key] for key in ("enabled_signals", "min_score", "max_results", "region_filter") if key in args}
    return json.dumps(set_config(str(args.get("workspace_id") or "default"), values), default=str)


def property_due_diligence(args: dict) -> str:
    uprn = str(args.get("uprn") or "").strip()
    if not uprn:
        return json.dumps({"status": "unavailable", "reason": "uprn is required"})
    return json.dumps(asyncio.run(run_due_diligence(uprn)), default=str)


def property_saved_search_create(args: dict) -> str:
    return json.dumps(create_saved_search(str(args.get("workspace_id") or "default"), str(args.get("name") or "Property search"), dict(args.get("criteria") or {}), run_schedule=str(args.get("run_schedule") or "weekly")), default=str)


def property_saved_search_list(args: dict) -> str:
    return json.dumps(list_saved_searches(str(args.get("workspace_id") or "default")), default=str)


def property_saved_search_run(args: dict) -> str:
    return json.dumps(run_saved_search(str(args.get("search_id") or ""), str(args.get("workspace_id") or "default")), default=str)


def calculator_list(args: dict) -> str:
    return json.dumps({"calculators": list_strategies()})


def calculator_run(args: dict) -> str:
    return json.dumps(run_workspace_calculator(str(args.get("workspace_id") or "default"), str(args.get("strategy") or ""), dict(args.get("inputs") or {})), default=str)


def calculator_rules_tool(args: dict) -> str:
    return json.dumps(calculator_rules(str(args.get("strategy") or ""), str(args.get("workspace_id") or "default")), default=str)


def calculator_settings_get(args: dict) -> str:
    return json.dumps(calculator_settings(str(args.get("workspace_id") or "default")), default=str)


def calculator_settings_update(args: dict) -> str:
    if not args.get("admin"):
        return json.dumps({"status": "admin_required"})
    return json.dumps(update_calculator_settings(str(args.get("workspace_id") or "default"), dict(args.get("overrides") or {})), default=str)


registry.register(name="property_data_status", toolset="property", schema={"name": "property_data_status", "description": "Read owned property dataset status.", "parameters": {"type": "object", "properties": {}}}, handler=property_data_status)
registry.register(name="property_data_refresh", toolset="property", schema={"name": "property_data_refresh", "description": "Refresh owned property datasets; requires admin=true.", "parameters": {"type": "object", "properties": {"admin": {"type": "boolean"}}, "required": ["admin"]}}, handler=property_data_refresh)
registry.register(name="property_data_api_endpoint_test", toolset="property", schema={"name": "property_data_api_endpoint_test", "description": "Test a derived property API lookup.", "parameters": {"type": "object", "properties": {"uprn": {"type": "string"}, "postcode": {"type": "string"}}}}, handler=property_data_api_endpoint_test)
registry.register(name="property_data_api_key_create", toolset="property", schema={"name": "property_data_api_key_create", "description": "Create a property-scoped developer API key; requires admin=true.", "parameters": {"type": "object", "properties": {"admin": {"type": "boolean"}, "name": {"type": "string"}, "workspace_id": {"type": "string"}}, "required": ["admin"]}}, handler=property_data_api_key_create)
registry.register(name="property_discover", toolset="property", schema={"name": "property_discover", "description": "Rank owned property signal candidates.", "parameters": {"type": "object", "properties": {"workspace_id": {"type": "string"}, "materialize": {"type": "boolean"}}}}, handler=property_discover)
registry.register(name="property_discovery_config_get", toolset="property", schema={"name": "property_discovery_config_get", "description": "Read property discovery configuration.", "parameters": {"type": "object", "properties": {"workspace_id": {"type": "string"}}}}, handler=property_discovery_config_get)
registry.register(name="property_discovery_config_set", toolset="property", schema={"name": "property_discovery_config_set", "description": "Update property discovery configuration; requires admin=true.", "parameters": {"type": "object", "properties": {"admin": {"type": "boolean"}, "workspace_id": {"type": "string"}, "enabled_signals": {"type": "array", "items": {"type": "string"}}, "min_score": {"type": "number"}, "max_results": {"type": "integer"}, "region_filter": {"type": "string"}}, "required": ["admin"]}}, handler=property_discovery_config_set)
registry.register(name="property_due_diligence", toolset="property", schema={"name": "property_due_diligence", "description": "Run structured property due diligence for a UPRN.", "parameters": {"type": "object", "properties": {"uprn": {"type": "string"}}, "required": ["uprn"]}}, handler=property_due_diligence)
registry.register(name="property_saved_search_create", toolset="property", schema={"name": "property_saved_search_create", "description": "Create a workspace-scoped saved property search.", "parameters": {"type": "object", "properties": {"workspace_id": {"type": "string"}, "name": {"type": "string"}, "criteria": {"type": "object"}, "run_schedule": {"type": "string"}}, "required": ["name"]}}, handler=property_saved_search_create)
registry.register(name="property_saved_search_list", toolset="property", schema={"name": "property_saved_search_list", "description": "List saved property searches for a workspace.", "parameters": {"type": "object", "properties": {"workspace_id": {"type": "string"}}}}, handler=property_saved_search_list)
registry.register(name="property_saved_search_run", toolset="property", schema={"name": "property_saved_search_run", "description": "Run a saved property search and upsert matches.", "parameters": {"type": "object", "properties": {"workspace_id": {"type": "string"}, "search_id": {"type": "string"}}, "required": ["search_id"]}}, handler=property_saved_search_run)
registry.register(name="calculator_list", toolset="property", schema={"name": "calculator_list", "description": "List all native property calculator strategies.", "parameters": {"type": "object", "properties": {}}}, handler=calculator_list)
registry.register(name="calculator_run", toolset="property", schema={"name": "calculator_run", "description": "Run a workspace-scoped pure property calculator.", "parameters": {"type": "object", "properties": {"workspace_id": {"type": "string"}, "strategy": {"type": "string"}, "inputs": {"type": "object"}}, "required": ["strategy", "inputs"]}}, handler=calculator_run)
registry.register(name="calculator_rules", toolset="property", schema={"name": "calculator_rules", "description": "Read calculator validation rules and workspace overrides.", "parameters": {"type": "object", "properties": {"workspace_id": {"type": "string"}, "strategy": {"type": "string"}}, "required": ["strategy"]}}, handler=calculator_rules_tool)
registry.register(name="calculator_settings_get", toolset="property", schema={"name": "calculator_settings_get", "description": "Read calculator overrides for a workspace.", "parameters": {"type": "object", "properties": {"workspace_id": {"type": "string"}}}}, handler=calculator_settings_get)
registry.register(name="calculator_settings_update", toolset="property", schema={"name": "calculator_settings_update", "description": "Update calculator overrides; requires admin=true.", "parameters": {"type": "object", "properties": {"admin": {"type": "boolean"}, "workspace_id": {"type": "string"}, "overrides": {"type": "object"}}, "required": ["admin", "overrides"]}}, handler=calculator_settings_update)
