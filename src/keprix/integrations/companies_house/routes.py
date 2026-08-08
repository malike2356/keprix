"""Companies House HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from keprix.auth.dependencies import get_current_user
from keprix.integrations.companies_house.client import CompaniesHouseClient
from keprix.integrations.companies_house.config import ENV_API_KEY, ENV_ENABLED, status_payload
from keprix.integrations.companies_house.errors import (
    CompaniesHouseApiError,
    CompaniesHouseConfigError,
)
from keprix.security.validation import ValidationError, default_validator

router = APIRouter(prefix="/api/companies-house", tags=["companies-house"])


class SettingsUpdateBody(BaseModel):
    api_key: str | None = None
    enabled: bool | None = None

    @field_validator("api_key")
    @classmethod
    def validate_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        try:
            return default_validator.validate_string(value, "api_key", max_length=256)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc


def _raise_ch(exc: Exception) -> None:
    if isinstance(exc, CompaniesHouseConfigError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(exc, CompaniesHouseApiError):
        code = 502
        if exc.status_code == 404:
            code = 404
        elif exc.status_code == 401:
            code = 401
        elif exc.status_code == 429:
            code = 429
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    raise exc


def _safe_string(value: str, field: str, max_length: int) -> str:
    try:
        return default_validator.validate_string(value, field, max_length=max_length)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/status")
async def companies_house_status(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return status_payload()


@router.put("/settings")
async def companies_house_settings(
    body: SettingsUpdateBody,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    from keprix.api.provider_settings import persist_env_value

    if body.api_key:
        persist_env_value(ENV_API_KEY, body.api_key)
    if body.enabled is not None:
        persist_env_value(ENV_ENABLED, "1" if body.enabled else "0")
    return {"ok": True, **status_payload()}


@router.get("/search")
async def search_companies(
    q: str = Query(..., min_length=1, description="Company name, number, or person name"),
    mode: str = Query("companies", description="companies | officers"),
    items_per_page: int = Query(20, ge=1, le=100),
    start_index: int = Query(0, ge=0),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    query = _safe_string(q, "q", 200)
    mode_norm = (mode or "companies").strip().lower()
    officers = mode_norm in {"officers", "people", "person", "officer"}
    client = CompaniesHouseClient()
    try:
        if officers:
            return await client.search_officers(
                query, items_per_page=items_per_page, start_index=start_index
            )
        return await client.search_companies(
            query, items_per_page=items_per_page, start_index=start_index
        )
    except (CompaniesHouseConfigError, CompaniesHouseApiError) as exc:
        _raise_ch(exc)
        raise  # pragma: no cover


@router.get("/officers/{officer_id}/appointments")
async def officer_appointments(
    officer_id: str,
    max_items: int = Query(50, ge=1, le=200),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    oid = _safe_string(officer_id, "officer_id", 200)
    client = CompaniesHouseClient()
    try:
        return await client.list_officer_appointments(oid, max_items=max_items)
    except (CompaniesHouseConfigError, CompaniesHouseApiError) as exc:
        _raise_ch(exc)
        raise  # pragma: no cover


@router.get("/company/{company_number}")
async def get_company(
    company_number: str,
    include_officers: bool = Query(True),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    number = _safe_string(company_number, "company_number", 20)
    client = CompaniesHouseClient()
    try:
        return await client.get_company_profile(number, include_officers=include_officers)
    except (CompaniesHouseConfigError, CompaniesHouseApiError) as exc:
        _raise_ch(exc)
        raise  # pragma: no cover
