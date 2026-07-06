"""Runtime extension registry for products built on Keprix."""

from keprix.extensions.registry import (
    ExtensionManifest,
    get_extension,
    get_governance_router,
    list_extensions,
    load_active_extensions,
    register_extension,
    start_extension_hooks,
    stop_extension_hooks,
)

__all__ = [
    "ExtensionManifest",
    "get_extension",
    "get_governance_router",
    "list_extensions",
    "load_active_extensions",
    "register_extension",
    "start_extension_hooks",
    "stop_extension_hooks",
]
