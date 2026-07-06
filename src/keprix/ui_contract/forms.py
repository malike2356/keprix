"""Shared form field definitions for dashboard surfaces."""

from __future__ import annotations

FORM_FIELDS: dict[str, list[dict[str, str]]] = {
    "consent": [
        {"name": "purpose", "label": "Purpose", "type": "text", "required": "true"},
        {"name": "granted", "label": "Granted", "type": "checkbox", "required": "true"},
    ],
    "dsar": [
        {"name": "request_type", "label": "Request type", "type": "select", "required": "true"},
    ],
    "governance_config": [
        {"name": "enabled", "label": "Enabled", "type": "checkbox"},
        {"name": "endpoint", "label": "API endpoint", "type": "url"},
        {"name": "workspace_id", "label": "Workspace ID", "type": "text"},
        {"name": "api_key", "label": "API key", "type": "password"},
    ],
    "dataset_import": [
        {"name": "name", "label": "Dataset name", "type": "text", "required": "true"},
        {"name": "file", "label": "CSV file", "type": "file", "required": "true"},
    ],
}
