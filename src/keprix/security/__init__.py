"""Security foundation for Keprix API and agent output."""

from keprix.security.audit import AuditLogger, hash_ip
from keprix.security.patterns import SECRET_PATTERNS
from keprix.security.redactor import Redactor, get_redactor
from keprix.security.validation import InputValidator, ValidationError
from keprix.security.vault_bootstrap import VaultClient, vault
from keprix.security.vault_service import VaultService, get_vault_service, reset_vault_service

__all__ = [
    "AuditLogger",
    "InputValidator",
    "Redactor",
    "SECRET_PATTERNS",
    "ValidationError",
    "VaultClient",
    "VaultService",
    "get_redactor",
    "get_vault_service",
    "hash_ip",
    "reset_vault_service",
    "vault",
]
