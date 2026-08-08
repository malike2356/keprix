# keprix - Prompt 10: Workspace - Documents, Notes, Tasks, Calendar

## Context

Source: `odysseus/` - self-hosted workspace features
Output: `keprix/backend/workspace/`

This prompt ports Odysseus's full workspace layer verbatim, adapted for the
keprix database schema and API conventions. Odysseus is Python (Flask); the
keprix backend is Python (FastAPI). Port the route logic; adapt the HTTP layer.

## Files to Port

Port all route files from `odysseus/routes/`:

```
routes/document_routes.py    -> backend/workspace/routes/document_routes.py
routes/document_helpers.py   -> backend/workspace/document_helpers.py
routes/note_routes.py        -> backend/workspace/routes/note_routes.py
routes/task_routes.py        -> backend/workspace/routes/task_routes.py
routes/calendar_routes.py    -> backend/workspace/routes/calendar_routes.py
routes/history_routes.py     -> backend/workspace/routes/history_routes.py
routes/editor_draft_routes.py -> backend/workspace/routes/editor_draft_routes.py
routes/personal_routes.py    -> backend/workspace/routes/personal_routes.py
routes/workspace_routes.py   -> backend/workspace/routes/workspace_routes.py
routes/prefs_routes.py       -> backend/workspace/routes/prefs_routes.py
routes/preset_routes.py      -> backend/workspace/routes/preset_routes.py
routes/session_routes.py     -> backend/workspace/routes/session_routes.py
routes/assistant_routes.py   -> backend/workspace/routes/assistant_routes.py
routes/cleanup_routes.py     -> backend/workspace/routes/cleanup_routes.py
routes/diagnostics_routes.py -> backend/workspace/routes/diagnostics_routes.py
```

Also port the Odysseus core infrastructure:
```
core/atomic_io.py         -> backend/workspace/core/atomic_io.py
core/auth.py              -> backend/workspace/core/auth.py
core/constants.py         -> backend/workspace/core/constants.py (rename Odysseus -> keprix)
core/database.py          -> backend/workspace/core/database.py
core/exceptions.py        -> backend/workspace/core/exceptions.py
core/middleware.py        -> backend/workspace/core/middleware.py
core/models.py            -> backend/workspace/core/models.py
core/platform_compat.py   -> backend/workspace/core/platform_compat.py
core/session_manager.py   -> backend/workspace/core/session_manager.py
```

## Documents Feature

The document editor supports: Markdown, HTML, plain text, CSV, syntax-highlighted code.

From `routes/document_routes.py` and `routes/document_helpers.py`, implement:

```
POST   /api/workspace/documents           - create document
GET    /api/workspace/documents           - list (paginated, filter by tag/type)
GET    /api/workspace/documents/{id}      - get with full content
PUT    /api/workspace/documents/{id}      - update content
DELETE /api/workspace/documents/{id}      - delete
POST   /api/workspace/documents/{id}/ai-edit   - AI-powered edit
POST   /api/workspace/documents/{id}/ai-suggest - AI suggestions inline
GET    /api/workspace/documents/{id}/export?format=md|html|txt|pdf
POST   /api/workspace/documents/{id}/share - generate share link
```

Documents schema (`workspace/migrations/001_workspace_schema.sql`):
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT 'Untitled',
    content TEXT NOT NULL DEFAULT '',
    format TEXT NOT NULL DEFAULT 'markdown',
    tags TEXT[] DEFAULT '{}',
    is_shared BOOLEAN DEFAULT false,
    share_token TEXT UNIQUE,
    word_count INT GENERATED ALWAYS AS (
        array_length(string_to_array(trim(content), ' '), 1)
    ) STORED,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON documents (user_id, updated_at DESC);
CREATE INDEX ON documents USING gin(to_tsvector('english', title || ' ' || content));
CREATE INDEX ON documents USING gin(tags);
```

## Notes Feature

From `routes/note_routes.py`:
```
POST   /api/workspace/notes              - create
GET    /api/workspace/notes              - list (filter: tag, search)
GET    /api/workspace/notes/{id}         - get
PUT    /api/workspace/notes/{id}         - update
DELETE /api/workspace/notes/{id}         - delete
POST   /api/workspace/notes/search       - full-text + vector search
```

Notes are lighter than documents: no editor modes, no AI edits. Just title +
content + tags. Ingest all notes into RAG (Prompt 06) automatically on save.

```sql
CREATE TABLE notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    tags TEXT[] DEFAULT '{}',
    is_pinned BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON notes (user_id, is_pinned DESC, updated_at DESC);
CREATE INDEX ON notes USING gin(to_tsvector('english', title || ' ' || content));
```

## Tasks Feature

From `routes/task_routes.py`:
```
POST   /api/workspace/tasks              - create task
GET    /api/workspace/tasks              - list (filter: status, tag, due)
GET    /api/workspace/tasks/{id}         - get
PUT    /api/workspace/tasks/{id}         - update (content, status, due date)
DELETE /api/workspace/tasks/{id}         - delete
POST   /api/workspace/tasks/{id}/complete - mark done
POST   /api/workspace/tasks/reorder      - drag-and-drop order
```

```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo','in_progress','done')),
    priority TEXT DEFAULT 'normal' CHECK (priority IN ('low','normal','high','urgent')),
    due_at TIMESTAMPTZ,
    sort_order INT DEFAULT 0,
    tags TEXT[] DEFAULT '{}',
    agent_scheduled BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON tasks (user_id, status, due_at);
```

Agent-scheduled tasks (`agent_scheduled=true`) are tasks the agent created
autonomously via the `create_task` tool. They appear with a distinct indicator
in the UI.

## Calendar Feature

From `routes/calendar_routes.py` + Odysseus CalDAV sync:
```
POST   /api/workspace/calendar/events    - create event
GET    /api/workspace/calendar/events    - list (date range)
GET    /api/workspace/calendar/events/{id} - get event
PUT    /api/workspace/calendar/events/{id} - update
DELETE /api/workspace/calendar/events/{id} - delete
POST   /api/workspace/calendar/sync      - trigger CalDAV sync
GET    /api/workspace/calendar/sources   - list CalDAV sources
POST   /api/workspace/calendar/sources   - add CalDAV source
```

CalDAV sync: use `caldav` Python package. Bidirectional. Configurable interval
(default: every 15 minutes). Credentials stored in vault (Prompt 08 vault).

```sql
CREATE TABLE calendar_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    uid TEXT UNIQUE,           -- CalDAV UID for sync
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    location TEXT DEFAULT '',
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    all_day BOOLEAN DEFAULT false,
    recurrence TEXT,           -- iCal RRULE string
    reminders INT[] DEFAULT '{15}', -- minutes before
    caldav_source_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON calendar_events (user_id, start_at);
```

## Editor Draft Autosave

From `routes/editor_draft_routes.py`:
- Autosave draft every 30 seconds when editing a document
- `PUT /api/workspace/documents/{id}/draft` - save draft
- `GET /api/workspace/documents/{id}/draft` - get draft
- `DELETE /api/workspace/documents/{id}/draft` - discard draft
- Draft is stored in Redis with 24-hour TTL (key: `draft:{user_id}:{doc_id}`)

## Sessions Feature

From `routes/session_routes.py` (Odysseus conversation sessions, not agent sessions):
- List past conversation sessions
- Rename, export, delete
- `GET /api/workspace/sessions` - list (paginated)
- `GET /api/workspace/sessions/{id}` - get with messages
- `PUT /api/workspace/sessions/{id}` - rename
- `DELETE /api/workspace/sessions/{id}` - delete
- `GET /api/workspace/sessions/{id}/export?format=json|md|txt`

## Presets Feature

From `routes/preset_routes.py`:
- Saved system prompts / persona presets
- `POST /api/workspace/presets` - create
- `GET /api/workspace/presets` - list
- `PUT /api/workspace/presets/{id}` - update
- `DELETE /api/workspace/presets/{id}` - delete
- `POST /api/workspace/presets/{id}/activate` - set as active system prompt

## Assistants Feature

From `routes/assistant_routes.py` (custom AI assistants with pinned prompts):
- Create named assistants with custom system prompts, tools, model
- `POST /api/workspace/assistants` - create
- `GET /api/workspace/assistants` - list
- `PUT /api/workspace/assistants/{id}` - update
- `DELETE /api/workspace/assistants/{id}` - delete

## Personal Data and Preferences

From `routes/personal_routes.py` and `routes/prefs_routes.py`:
- User profile: name, timezone, language
- Display preferences: theme, font size, layout density
- `GET /api/workspace/profile` - get
- `PUT /api/workspace/profile` - update
- `GET /api/workspace/prefs` - get preferences
- `PUT /api/workspace/prefs` - update preferences

## Admin: Workspace Wipe

From `routes/admin_wipe_routes.py`:
- `POST /api/admin/wipe?confirm=true` - delete all user data (messages, notes, docs, tasks, memories)
- Requires admin token header
- Logs wipe action to audit table

## Acceptance Criteria

- `POST /api/workspace/documents` with `{title, content, format}` returns 201 with id
- `GET /api/workspace/documents/{id}` returns the created document with word_count
- `POST /api/workspace/documents/{id}/ai-edit` with `{instruction}` returns modified content
- `POST /api/workspace/tasks` creates task; `PUT /{id}` updates status to 'done'
- `GET /api/workspace/calendar/events?start=2026-01-01&end=2026-01-31` returns events in range
- CalDAV sync runs without error when `CALDAV_URL` is set
- Draft autosave stores in Redis and is retrievable within the 24h TTL
