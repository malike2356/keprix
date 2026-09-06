from __future__ import annotations

from keprix.discovery.packs import get_pack, list_packs, load_vertical_packs


def test_discovery_flag_is_read_from_pack_manifest() -> None:
    load_vertical_packs(force=True)
    assert get_pack("generic")["discovery"]["enabled"] is True
    listed = {item["id"]: item for item in list_packs()}
    assert listed["generic"]["has_discovery_block"] is True
