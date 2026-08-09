"""Document Vault security helpers (Prompt 652)."""

from __future__ import annotations

from keprix.document_vault.security.grants import KNOWN_GRANTS, require_grant
from keprix.document_vault.security.ssrf import assert_safe_fetch_url

__all__ = ["KNOWN_GRANTS", "assert_safe_fetch_url", "require_grant"]
