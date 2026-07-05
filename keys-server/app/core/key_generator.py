"""Licence key generation for Petraclus."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import string

from app.core.config import settings

_CHARS = string.ascii_uppercase + string.digits


def _random_group(length: int = 8) -> str:
    return ''.join(secrets.choice(_CHARS) for _ in range(length))


def _checksum(parts: list[str]) -> str:
    payload = '-'.join(parts).encode()
    digest = hmac.new(
        settings.key_server_checksum_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return digest[:2].upper()


def generate_petraclus_key(tier: str) -> str:
    tier_upper = tier.upper()
    g1 = _random_group()
    g2 = _random_group()
    parts = ['PETRA', tier_upper, g1, g2]
    checksum = _checksum(parts)
    return f"PETRA-{tier_upper}-{g1}-{g2}-{checksum}"


def generate_key(product: str, tier: str) -> str:
    if product == 'petraclus':
        return generate_petraclus_key(tier)
    raise ValueError(f"Unknown product: {product}. This server only issues Petraclus keys.")
