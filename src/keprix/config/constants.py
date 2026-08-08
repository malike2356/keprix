"""Central constants for keprix. Import from here; never hardcode product names."""

from __future__ import annotations

from typing import TYPE_CHECKING

PRODUCT_NAME = "Keprix"
try:
    from keprix_cli import __version__ as PRODUCT_VERSION
except Exception:
    PRODUCT_VERSION = "0.16.0"
EDITION = "community"
HOMEPAGE = "https://keprixai.com"
DOCS_URL = "https://keprixai.com/docs"
GITHUB_URL = "https://github.com/malike2356/keprix"
DEVELOPER_IDENTITY_DIR = "~/.keprix/identity"
DEVELOPER_CONFIG_DIR = "~/.keprix"
DATA_DIR = "/data/keprix"

if TYPE_CHECKING:
    from keprix.extensions.registry import ExtensionManifest

# Populated at runtime when products register via keprix.extensions.registry
EXTENSION_REGISTRY: dict[str, "ExtensionManifest"] = {}

# Audit event types
AUDIT_DEVELOPER_IDENTITY_CREATED = "developer_identity_created"
AUDIT_DEVELOPER_IDENTITY_REVOKED = "developer_identity_revoked"
