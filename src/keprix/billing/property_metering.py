"""Optional billing hook for derived property API calls.

The property API records usage before calling this hook. Billing deployments
can replace this function with the wallet meter without changing API reads.
"""

from __future__ import annotations


def meter_property_api_call(*, workspace_id: str, endpoint: str, cost: float = 1.0, connection=None, key_id: str = "", uprn: str = "", postcode: str = "", idempotency_key: str = "") -> None:
    """Delegate to the property meter while preserving the no-raise contract."""
    from keprix.property_data.billing import meter_property_api_call as meter
    meter(workspace_id=workspace_id, endpoint=endpoint, cost=cost, connection=connection, key_id=key_id, uprn=uprn, postcode=postcode, idempotency_key=idempotency_key)
