"""Azure translation provider stub."""

from __future__ import annotations

from keprix.backend.localization.providers.cloud import CloudTranslationProvider


class AzureTranslationProvider(CloudTranslationProvider):
    name = "azure"
