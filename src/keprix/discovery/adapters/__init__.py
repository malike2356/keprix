"""Built-in discovery adapter registration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from keprix.discovery.registry import DiscoveryRegistry


def register_builtin_adapters(registry: DiscoveryRegistry) -> None:
    from keprix.discovery.adapters.companies_house import CompaniesHouseAdapter
    from keprix.discovery.adapters.csv_import import CsvDiscoveryAdapter
    from keprix.discovery.adapters.fake import FakeDiscoveryAdapter
    from keprix.discovery.adapters.health import (
        CqcApiAdapter,
        DirectoryWebHealthAdapter,
        HealthCsvAdapter,
    )
    from keprix.discovery.adapters.property_portals import (
        PropertyCsvAdapter,
        RightmoveHttpAdapter,
        ZooplaHttpAdapter,
    )
    from keprix.discovery.adapters.social import (
        LinkedInApiAdapter,
        MetaGraphAdapter,
        SocialCsvExportAdapter,
        TikTokApiAdapter,
    )
    from keprix.discovery.adapters.web_directory import WebDirectoryAdapter

    adapters = [
        FakeDiscoveryAdapter(),
        CompaniesHouseAdapter(),
        CsvDiscoveryAdapter(),
        WebDirectoryAdapter(),
        LinkedInApiAdapter(),
        MetaGraphAdapter(),
        TikTokApiAdapter(),
        SocialCsvExportAdapter(),
        PropertyCsvAdapter(),
        RightmoveHttpAdapter(),
        ZooplaHttpAdapter(),
        CqcApiAdapter(),
        HealthCsvAdapter(),
        DirectoryWebHealthAdapter(),
    ]
    for adapter in adapters:
        try:
            registry.register(adapter, replace=True)
        except ValueError:
            pass


def bootstrap_packs() -> None:
    """Register sheet types / presets from vertical packs."""
    from keprix.discovery.packs import load_vertical_packs

    load_vertical_packs()
