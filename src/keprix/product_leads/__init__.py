"""Thin lead/campaign layer on Contacts + viCal (not a CRM)."""

from keprix.product_leads.store import LeadStore, get_lead_store

__all__ = ["LeadStore", "get_lead_store"]
