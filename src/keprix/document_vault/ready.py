"""Document Vault programme readiness (Prompt 653).

``document_vault_ready`` is True after the 645-653 programme closes.
Runtime use still requires ``KEPRIX_DOCUMENT_VAULT_ENABLED=1``.
Set ``KEPRIX_DOCUMENT_VAULT_READY=0`` only for emergency rollback of the ready claim.
"""

from __future__ import annotations

import os


# Programme close constant (Prompt 653). Do not set False without owner decision.
PROGRAMME_CLOSED = True


def document_vault_ready() -> bool:
    """Return True when the Document Vault programme is closed and ready to enable."""
    if not PROGRAMME_CLOSED:
        return False
    raw = os.environ.get("KEPRIX_DOCUMENT_VAULT_READY")
    if raw is None:
        return True
    return str(raw).strip().lower() not in {"0", "false", "no", "off"}


__all__ = ["PROGRAMME_CLOSED", "document_vault_ready"]
