"""Playbook link validation for domain packs (Prompt 30)."""

from __future__ import annotations

from urllib.parse import urlparse

from keprix.backend.domain_packs.schemas import DomainPackManifest


def validate_playbooks(pack: DomainPackManifest) -> list[str]:
    errors: list[str] = []
    for index, playbook in enumerate(pack.playbooks, start=1):
        title = str(playbook.get("title") or "").strip()
        href = str(playbook.get("href") or playbook.get("url") or "").strip()
        if not title:
            errors.append(f"playbook {index} missing title")
        if not href:
            errors.append(f"playbook {index} missing href")
            continue
        parsed = urlparse(href)
        if parsed.scheme not in {"http", "https", ""}:
            errors.append(f"playbook {index} has invalid href scheme")
        if parsed.scheme in {"http", "https"} and not parsed.netloc:
            errors.append(f"playbook {index} href missing host")
    return errors
