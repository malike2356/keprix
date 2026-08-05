"""Resource-scoped tool ACL package."""

from keprix.security.resource_scopes.enforce import (
    ResourceACLDecision,
    check_and_audit_resource_acl,
    check_resource_acl,
    enforce_service_resources,
)
from keprix.security.resource_scopes.extract import ExtractionResult, ResourceRef, extract_resources
from keprix.security.resource_scopes.grants import (
    ResourceGrant,
    ResourceGrantStore,
    get_resource_grant_store,
    reset_resource_grant_store_for_tests,
)
from keprix.security.resource_scopes.registry import list_services, resolve_service_for_tool

__all__ = [
    "ExtractionResult",
    "ResourceACLDecision",
    "ResourceGrant",
    "ResourceGrantStore",
    "ResourceRef",
    "check_and_audit_resource_acl",
    "check_resource_acl",
    "enforce_service_resources",
    "extract_resources",
    "get_resource_grant_store",
    "list_services",
    "reset_resource_grant_store_for_tests",
    "resolve_service_for_tool",
]
