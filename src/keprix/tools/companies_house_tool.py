"""Agent tools: search and profile lookup via Companies House."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from keprix.integrations.companies_house.client import CompaniesHouseClient
from keprix.integrations.companies_house.config import is_configured, is_enabled
from keprix.integrations.companies_house.errors import CompaniesHouseError
from keprix.tools.registry import registry

TOOLSET = "companies_house"


def _check_ready() -> bool | str:
    if not is_enabled():
        return "Companies House disabled (KEPRIX_COMPANIES_HOUSE_ENABLED)"
    if not is_configured():
        return "Set COMPANIES_HOUSE_API_KEY to enable Companies House lookup"
    return True


def _run(coro: Any) -> Any:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # Nested loop (rare in tool handlers): run in a fresh loop via thread if needed.
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def _handle_search(args: dict[str, Any], **_kwargs: Any) -> str:
    query = str(args.get("query") or args.get("q") or "").strip()
    items_per_page = int(args.get("items_per_page") or 10)
    try:
        result = _run(CompaniesHouseClient().search_companies(query, items_per_page=items_per_page))
        return json.dumps(result)
    except CompaniesHouseError as exc:
        return json.dumps({"error": str(exc)})


def _handle_profile(args: dict[str, Any], **_kwargs: Any) -> str:
    number = str(args.get("company_number") or args.get("number") or "").strip()
    include_officers = bool(args.get("include_officers", True))
    try:
        result = _run(
            CompaniesHouseClient().get_company_profile(number, include_officers=include_officers)
        )
        return json.dumps(result)
    except CompaniesHouseError as exc:
        return json.dumps({"error": str(exc)})


SEARCH_SCHEMA = {
    "name": "search:companies_house",
    "description": (
        "Search UK companies on Companies House by name or number. "
        "Returns ranked matches with company_number, status, and public URL."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Company name fragment or company number",
            },
            "items_per_page": {
                "type": "integer",
                "description": "Max results (1-100, default 10)",
            },
        },
        "required": ["query"],
    },
}

PROFILE_SCHEMA = {
    "name": "get:company_profile",
    "description": (
        "Fetch a UK Companies House company profile by company_number, "
        "including status, SIC codes, registered office, and officer summary."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "company_number": {
                "type": "string",
                "description": "Companies House company number (e.g. 00000006)",
            },
            "include_officers": {
                "type": "boolean",
                "description": "Include officers list (default true)",
            },
        },
        "required": ["company_number"],
    },
}

registry.register(
    name="search:companies_house",
    toolset=TOOLSET,
    schema=SEARCH_SCHEMA,
    handler=_handle_search,
    check_fn=_check_ready,
    requires_env=["COMPANIES_HOUSE_API_KEY"],
)

registry.register(
    name="get:company_profile",
    toolset=TOOLSET,
    schema=PROFILE_SCHEMA,
    handler=_handle_profile,
    check_fn=_check_ready,
    requires_env=["COMPANIES_HOUSE_API_KEY"],
)
