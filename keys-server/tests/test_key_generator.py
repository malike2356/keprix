from __future__ import annotations

import re

import pytest

from app.core.key_generator import generate_key


def test_key_generation_produces_expected_prefix_and_checksum_format() -> None:
    petra = generate_key("petraclus", "TEAM")
    assert re.match(r"^PETRA-TEAM-[A-Z0-9]{8}-[A-Z0-9]{8}-[A-F0-9]{2}$", petra)


def test_keprix_keys_are_not_supported() -> None:
    with pytest.raises(ValueError, match="only issues Petraclus"):
        generate_key("keprix", "PRO")
