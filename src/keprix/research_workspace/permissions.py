"""Research workspace permission checks."""

from __future__ import annotations

from keprix.research_workspace.errors import PermissionDeniedError
from keprix.research_workspace.schemas import ExportPolicy, SensitivityLevel


def can_read(*, sensitivity_level: str, user_id: str, owner: str, is_admin: bool = False) -> bool:
    if is_admin:
        return True
    if sensitivity_level == SensitivityLevel.PUBLIC.value:
        return True
    if sensitivity_level == SensitivityLevel.INTERNAL.value:
        return True
    if sensitivity_level == SensitivityLevel.RESTRICTED.value:
        return user_id == owner
    return False


def assert_can_read(**kwargs: object) -> None:
    if not can_read(**kwargs):  # type: ignore[arg-type]
        raise PermissionDeniedError("Read access denied for research object")


def can_export(*, export_policy: str, user_id: str, owner: str, is_admin: bool = False) -> bool:
    if export_policy == ExportPolicy.DENY.value:
        return is_admin
    if export_policy == ExportPolicy.REDACT.value:
        return user_id == owner or is_admin
    return can_read(
        sensitivity_level=SensitivityLevel.INTERNAL.value,
        user_id=user_id,
        owner=owner,
        is_admin=is_admin,
    )


def assert_can_export(**kwargs: object) -> None:
    if not can_export(**kwargs):  # type: ignore[arg-type]
        raise PermissionDeniedError("Export denied by research export policy")
