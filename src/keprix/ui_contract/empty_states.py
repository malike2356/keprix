"""Shared empty-state copy."""

from __future__ import annotations

EMPTY_STATES: dict[str, dict[str, str]] = {
    "inbox": {
        "title": "Inbox is empty",
        "description": "Connect an email account or sync to load messages.",
    },
    "tasks": {
        "title": "No tasks",
        "description": "Add tasks to track work across your workspace.",
    },
    "vault_locked": {
        "title": "Vault locked",
        "description": "Unlock with your master password to view stored credentials.",
    },
    "gallery": {
        "title": "No images yet",
        "description": "Upload or generate images to build your gallery.",
    },
    "research": {
        "title": "No research runs yet",
        "description": "Submit a query to generate a cited report.",
    },
    "jobs": {
        "title": "No scheduled jobs",
        "description": "Create a cron job with a schedule, prompt, and output channel.",
    },
    "memory": {
        "title": "No memory entries",
        "description": "Memory will populate as you use chat, research, and saved notes.",
    },
    "skills": {
        "title": "No skills installed",
        "description": "Install skill packs from the hub or enable bundled skills in settings.",
    },
    "settings": {
        "title": "No instance overrides",
        "description": "Use the cards below to configure providers, channels, and workspace tools.",
    },
    "governance": {
        "title": "Governance provider not connected",
        "description": "Configure a governance provider to stream audit events and policy controls.",
    },
    "privacy": {
        "title": "No privacy requests",
        "description": "Record consent or submit a data access request from this page.",
    },
}
