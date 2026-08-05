"""Shared empty-state copy."""

from __future__ import annotations

EMPTY_STATES: dict[str, dict[str, str]] = {
    "home": {
        "title": "Welcome to keprix.",
        "description": (
            "Your AI agent is set up and ready. "
            "Start a conversation to see what it can do."
        ),
        "primary_action": "Start your first session",
        "primary_href": "/sessions/new",
    },
    "sessions": {
        "title": "No sessions yet.",
        "description": "Sessions are conversations with your agent. Start one to get going.",
        "primary_action": "Start a session",
        "primary_href": "/sessions/new",
    },
    "brain_graph": {
        "title": "Your brain is empty.",
        "description": (
            "Start a session and keprix will remember what matters. "
            "Memories, skills, and tasks will appear here as connected nodes."
        ),
        "primary_action": "Start a session",
        "primary_href": "/sessions/new",
    },
    "skills": {
        "title": "No skills yet.",
        "description": (
            "Skills are behaviours your agent learns and reuses. "
            "You can add one manually or ask your agent to learn from a session."
        ),
        "primary_action": "Add a skill",
        "primary_href": "/skills/new",
    },
    "tasks": {
        "title": "No tasks yet.",
        "description": (
            "Tasks are things your agent does on its own, step by step. "
            "Give it a goal and it works through it while you do other things."
        ),
        "primary_action": "New task",
        "primary_href": "/tasks/new",
    },
    "tools": {
        "title": "No tools connected.",
        "description": (
            "Tools give your agent the ability to read your email, "
            "manage your calendar, look up contacts, and more."
        ),
        "primary_action": "Browse tools",
        "primary_href": "/tools",
    },
    "voice": {
        "title": "No phone number set up.",
        "description": (
            "Give your agent a phone number so clients can call it directly. "
            "It answers, books appointments, takes messages, and tells you what happened."
        ),
        "primary_action": "Set up a phone number",
        "primary_href": "/voice/setup",
    },
    "inbox": {
        "title": "Inbox is empty",
        "description": "Connect an email account or sync to load messages.",
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
