"""Google Contacts tool wrappers."""

from typing import Any

from .bridge import GoogleWorkspaceBridge


def gws_contacts_list(query: str = "", max_results: int = 50) -> dict[str, Any]:
    return GoogleWorkspaceBridge().contacts_list(query, max_results)


def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    value = payload.get("contacts", payload.get("items", []))
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _first(value: Any) -> str | None:
    if isinstance(value, list) and value:
        value = value[0]
    if isinstance(value, dict):
        value = value.get("value") or value.get("formattedValue") or value.get("displayName")
    return str(value).strip() if value else None


def _contact_patch(contact: dict[str, Any]) -> dict[str, Any]:
    names = contact.get("names") or contact.get("name") or []
    name = names[0] if isinstance(names, list) and names else names
    if not isinstance(name, dict):
        name = {}
    given = _first(name.get("givenName") or contact.get("first_name"))
    family = _first(name.get("familyName") or contact.get("last_name"))
    display = _first(name.get("displayName") or contact.get("display_name"))
    emails = contact.get("emailAddresses") or contact.get("emails") or []
    phones = contact.get("phoneNumbers") or contact.get("phones") or []
    email_values = (
        [_first(item) for item in emails] if isinstance(emails, list) else [_first(emails)]
    )
    phone_values = (
        [_first(item) for item in phones] if isinstance(phones, list) else [_first(phones)]
    )
    patch: dict[str, Any] = {
        "emails": [v for v in email_values if v],
        "phones": [v for v in phone_values if v],
    }
    if given or family:
        patch["name"] = " ".join(part for part in (given, family) if part)
    elif display:
        patch["name"] = display
    organization = _first(contact.get("organizations") or contact.get("company_name"))
    if organization:
        patch["company_name"] = organization
    return patch


def gws_contacts_enrich(
    workspace_id: str,
    lead_id: str,
    query: str,
    *,
    actor_id: str | None = None,
    bridge: GoogleWorkspaceBridge | None = None,
    store: Any | None = None,
) -> dict[str, Any]:
    """Fill only empty CRM lead fields from the first matching Google Contact."""
    from keprix.crm.store import get_crm_store

    crm = store or get_crm_store()
    lead = crm.get_lead(workspace_id, lead_id)
    if not lead:
        return {"status": "not_found", "lead_id": lead_id}
    result = (bridge or GoogleWorkspaceBridge()).contacts_list(query, 20)
    contacts = _items(result)
    if not contacts:
        return {"status": "no_match", "lead_id": lead_id, "query": query}
    candidate = _contact_patch(contacts[0])
    patch = {key: value for key, value in candidate.items() if value and not lead.get(key)}
    custom = dict(lead.get("custom_fields") or {})
    custom["google_contact"] = contacts[0]
    patch["custom_fields"] = custom
    if actor_id:
        patch["actor_id"] = actor_id
    patch["actor_type"] = "google_contacts"
    updated = crm.update_lead(workspace_id, lead_id, **patch)
    return {"status": "enriched", "lead": updated, "source": "google_contacts"}
