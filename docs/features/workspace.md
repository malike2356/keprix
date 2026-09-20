# Workspace overview

The Keprix **workspace** is the signed-in web application on **your machine**
(`keprix dashboard` at `http://127.0.0.1:9120/home`, or Docker Compose at
`:3000`): home launcher, sidebar navigation, and per-user data. It is not
hosted at `app.keprixai.com`.

## Home (`/launcher`)

Card grid linking to major tools (chat, research, documents, settings, etc.). Breadcrumb: **Workspace > Home**.

Navigation header in chat provides **Home** and **Dashboard** (admins).

## Sidebar groups

| Group | Examples |
| --- | --- |
| Workspace | Chat, documents, notes, tasks, calendar, email, contacts |
| Apps | Skills Hub, Hub, Project Builder, domain packs, migrate |
| Data | Local models, RAG pipelines, analytics |
| Research | Deep research, compare models, opportunities |
| Automations | Playbooks, agent teams, cron, coding, tools, MCP |
| Security | Review gateway, vault, support |
| Admin | Backup, settings, developer |

Exact items depend on `ui_contract` from the backend (feature flags, packs).

## Data model

Workspace entities are scoped per user (and instance):

- Documents, notes, tasks, calendar events
- Chat sessions and messages
- Email cache, contacts, gallery assets
- Memory documents and embeddings

CLI dashboard storage defaults to `~/.keprix` (JSON/SQLite and related local
files). Docker Compose production-style storage is PostgreSQL + Redis + vector
store (see [Data planes](../operations/data-planes.md)).

## API prefix

Most routes: `/api/workspace/*`, `/api/conversations/*`, `/api/email/*`.

## Appearance

Theme picker (light/dark + color skins) in header and **Settings > Appearance**.

## Related docs

| Tool | Doc |
| --- | --- |
| Chat | [Chat](chat.md) |
| Documents | [Documents](documents.md) |
| Notes | [Notes](notes.md) |
| Tasks | [Tasks](tasks.md) |
| Calendar | [Calendar](calendar.md) |
| Email | [Email](email.md) |
| Contacts | [Contacts](contacts.md) |
| Settings | [Settings](settings.md) |
