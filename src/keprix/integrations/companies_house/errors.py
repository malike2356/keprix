"""Companies House API errors."""

from __future__ import annotations


class CompaniesHouseError(Exception):
    """Base error for Companies House integration."""


class CompaniesHouseConfigError(CompaniesHouseError):
    """Missing or invalid API configuration."""


class CompaniesHouseApiError(CompaniesHouseError):
    """Upstream Companies House API failure."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
