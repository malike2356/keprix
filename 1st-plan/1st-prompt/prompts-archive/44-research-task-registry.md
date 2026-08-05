# keprix - Prompt 44: Research Task Registry with Session Persistence

## Context

Reference: `planning/agents-to-adopt/odysseus/src/research_handler.py`.

Prompt 14 builds the deep research pipeline: web research, source ranking, claim verification, playbook runner, and research report generator. What it does not define is what happens when a research job takes 3-8 minutes, the user reloads the browser, or the connection drops mid-run.

Currently, a long research job is fire-and-forget. If the WebSocket drops, the result is lost. If the user navigates away, there is no way to retrieve progress. For a product that positions deep research as a premium feature, this is a reliability problem that users notice immediately.

This prompt adds a research task registry: a server-side store that gives every research job a persistent session ID, tracks its lifecycle (pending, running, completed, failed, cancelled), streams incremental progress events, and survives page refreshes. The registry integrates with the existing research pipeline as a wrapper - the pipeline itself does not change.

The secondary benefit: an operator can see all running research jobs in their workspace, cancel stuck ones, and retrieve completed reports from past sessions without re-running the search.

---

## File Structure

```
keprix/backend/research/
    registry.py             - ResearchTaskRegistry: CRUD, lifecycle, persistence
    runner.py               - ResearchRunner: wraps the existing pipeline with registry integration
    events.py               - progress event schema and SSE stream
    routes.py               - API endpoints (extends Prompt 14 routes)

keprix/tests/research/
    test_registry.py
    test_runner.py
    test_events.py
```

---

## Database Schema

```sql
CREATE TABLE research_tasks (
    id TEXT PRIMARY KEY,
    -- slug-safe session ID, e.g. 'rsch-a1b2c3d4'. BCP format: 'rsch-' + 8 random chars.
    workspace_id UUID NOT NULL,
    user_id UUID NOT NULL,
    query TEXT NOT NULL,
    -- the original research question as submitted
    model TEXT,
    -- LLM model used for this research job
    status TEXT NOT NULL DEFAULT 'pending',
    -- 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
    progress_pct INTEGER,
    -- 0-100; updated as the job progresses
    current_step TEXT,
    -- human-readable description of the current step, e.g. "Searching for sources..."
    result_markdown TEXT,
    -- the final research report in Markdown; null until status = 'completed'
    result_document_id UUID,
    -- FK to document store (Prompt 10) once the report is saved
    error_message TEXT,
    -- set if status = 'failed'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    -- research is retained for 30 days; cleaned up by cron
    expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '30 days'
);

CREATE INDEX ON research_tasks(workspace_id, status, created_at DESC);
CREATE INDEX ON research_tasks(user_id, created_at DESC);
CREATE INDEX ON research_tasks(expires_at);

CREATE TABLE research_task_events (
    id BIGSERIAL PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES research_tasks(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    -- 'step_start' | 'step_complete' | 'source_found' | 'claim_verified' | 'completed' | 'failed' | 'cancelled'
    payload JSONB,
    emitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ON research_task_events(task_id, emitted_at ASC);
```

---

## Task Registry

```python
# keprix/backend/research/registry.py

import re
import secrets
from uuid import UUID

TASK_ID_RE = re.compile(r"^rsch-[a-z0-9]{8}$")

class ResearchTaskRegistry:

    def _generate_id(self) -> str:
        return "rsch-" + secrets.token_hex(4)

    async def create(
        self,
        workspace_id: str,
        user_id: str,
        query: str,
        model: str | None = None,
    ) -> ResearchTask:
        task_id = self._generate_id()
        await db.execute(
            """INSERT INTO research_tasks (id, workspace_id, user_id, query, model)
               VALUES ($1, $2, $3, $4, $5)""",
            task_id, workspace_id, user_id, query, model,
        )
        return await self.get(task_id)

    async def get(self, task_id: str) -> ResearchTask:
        if not TASK_ID_RE.fullmatch(task_id):
            raise ValueError(f"Invalid task ID format: {task_id!r}")
        row = await db.fetchone("SELECT * FROM research_tasks WHERE id = $1", task_id)
        if not row:
            raise KeyError(f"Research task not found: {task_id}")
        return ResearchTask(**row)

    async def update_status(
        self,
        task_id: str,
        status: str,
        progress_pct: int | None = None,
        current_step: str | None = None,
        result_markdown: str | None = None,
        result_document_id: UUID | None = None,
        error_message: str | None = None,
    ) -> None:
        fields = {"status": status}
        if progress_pct is not None:
            fields["progress_pct"] = progress_pct
        if current_step is not None:
            fields["current_step"] = current_step
        if result_markdown is not None:
            fields["result_markdown"] = result_markdown
        if result_document_id is not None:
            fields["result_document_id"] = str(result_document_id)
        if error_message is not None:
            fields["error_message"] = error_message
        if status == "running":
            fields["started_at"] = "NOW()"
        elif status in ("completed", "failed"):
            fields["completed_at"] = "NOW()"
        elif status == "cancelled":
            fields["cancelled_at"] = "NOW()"
        await db.update("research_tasks", fields, where_id=task_id)

    async def emit_event(
        self,
        task_id: str,
        event_type: str,
        payload: dict | None = None,
    ) -> None:
        await db.execute(
            "INSERT INTO research_task_events (task_id, event_type, payload) VALUES ($1, $2, $3)",
            task_id, event_type, payload or {},
        )
        # Also push to the SSE channel so connected clients get it immediately.
        await sse_bus.publish(f"research:{task_id}", {"type": event_type, "payload": payload or {}})

    async def cancel(self, task_id: str, user_id: str) -> None:
        """
        Cancels a running or pending task.
        Sets a cancellation flag checked by the runner on every step.
        """
        task = await self.get(task_id)
        if task.user_id != str(user_id):
            raise PermissionError("Only the task owner can cancel it")
        if task.status not in ("pending", "running"):
            raise ValueError(f"Cannot cancel a task with status '{task.status}'")
        await self.update_status(task_id, "cancelled")
        await self.emit_event(task_id, "cancelled")

    async def is_cancelled(self, task_id: str) -> bool:
        row = await db.fetchone("SELECT status FROM research_tasks WHERE id = $1", task_id)
        return row and row["status"] == "cancelled"

    async def list_for_workspace(
        self,
        workspace_id: str,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ResearchTask]:
        query = "SELECT * FROM research_tasks WHERE workspace_id = $1"
        params = [workspace_id]
        if status:
            query += " AND status = $2"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT $%d OFFSET $%d" % (len(params) + 1, len(params) + 2)
        params += [limit, offset]
        rows = await db.fetchall(query, *params)
        return [ResearchTask(**r) for r in rows]

    async def get_events(self, task_id: str, since_id: int = 0) -> list[dict]:
        rows = await db.fetchall(
            "SELECT * FROM research_task_events WHERE task_id = $1 AND id > $2 ORDER BY id ASC",
            task_id, since_id,
        )
        return [dict(r) for r in rows]
```

---

## Research Runner

The runner wraps the existing deep research pipeline from Prompt 14. It adds registry integration: every step emits an event, cancellation is checked between steps, and the result is persisted.

```python
# keprix/backend/research/runner.py

class ResearchRunner:

    def __init__(self, registry: ResearchTaskRegistry, pipeline: DeepResearchPipeline):
        self.registry = registry
        self.pipeline = pipeline

    async def start(self, task_id: str) -> None:
        """
        Runs the research pipeline for task_id in a background task.
        Safe to call from an API handler - returns immediately.
        """
        asyncio.create_task(self._run(task_id))

    async def _run(self, task_id: str) -> None:
        try:
            await self.registry.update_status(task_id, "running", progress_pct=0)
            task = await self.registry.get(task_id)

            # Step 1: Query expansion
            await self._check_cancelled(task_id)
            await self.registry.update_status(task_id, "running",
                                              progress_pct=5, current_step="Expanding query...")
            await self.registry.emit_event(task_id, "step_start", {"step": "query_expansion"})
            expanded_query = await self.pipeline.expand_query(task.query)
            await self.registry.emit_event(task_id, "step_complete",
                                           {"step": "query_expansion", "queries": expanded_query})

            # Step 2: Source search
            await self._check_cancelled(task_id)
            await self.registry.update_status(task_id, "running",
                                              progress_pct=15, current_step="Searching sources...")
            sources = []
            async for source in self.pipeline.search_sources(expanded_query):
                await self._check_cancelled(task_id)
                sources.append(source)
                await self.registry.emit_event(task_id, "source_found",
                                               {"url": source.url, "title": source.title})

            # Step 3: Claim verification
            await self._check_cancelled(task_id)
            await self.registry.update_status(task_id, "running",
                                              progress_pct=50, current_step="Verifying claims...")
            verified = await self.pipeline.verify_claims(sources)
            await self.registry.emit_event(task_id, "step_complete",
                                           {"step": "claim_verification",
                                            "verified_count": len(verified)})

            # Step 4: Report generation
            await self._check_cancelled(task_id)
            await self.registry.update_status(task_id, "running",
                                              progress_pct=80, current_step="Writing report...")
            report_md = await self.pipeline.generate_report(task.query, verified)

            # Step 5: Save to document store
            doc_id = await document_store.create(
                workspace_id=task.workspace_id,
                title=f"Research: {task.query[:80]}",
                content=report_md,
                tags=["research", "auto-generated"],
                source="research_runner",
            )

            await self.registry.update_status(
                task_id, "completed",
                progress_pct=100,
                current_step="Done",
                result_markdown=report_md,
                result_document_id=doc_id,
            )
            await self.registry.emit_event(task_id, "completed",
                                           {"document_id": str(doc_id)})

        except ResearchCancelledError:
            # Already marked cancelled by registry.cancel(); nothing more to do.
            pass
        except Exception as exc:
            await self.registry.update_status(task_id, "failed", error_message=str(exc))
            await self.registry.emit_event(task_id, "failed", {"error": str(exc)})

    async def _check_cancelled(self, task_id: str) -> None:
        if await self.registry.is_cancelled(task_id):
            raise ResearchCancelledError(task_id)


class ResearchCancelledError(Exception):
    pass
```

---

## SSE Progress Stream

Clients connect once and receive all events for a task. On reconnect, they pass the last `event_id` they received and get only newer events (no events are dropped across a page refresh).

```
GET /api/research/tasks/{task_id}/events
    Headers: Accept: text/event-stream
    Query: since_id=<last_event_id>    (optional; 0 to replay from start)

Response: Server-Sent Events stream
    data: {"type": "source_found", "payload": {"url": "...", "title": "..."}, "id": 42}
    data: {"type": "completed", "payload": {"document_id": "..."}, "id": 87}
```

On page refresh, the client reconnects with `since_id=<last_id>` and catches up from the event log. If the task is already `completed` or `failed`, the server sends the final event and closes the stream immediately.

---

## API Endpoints

```
POST   /api/research/tasks
       Body: { query, model? }
       Returns: { task_id, status: "pending" }
       Starts the research job in the background.

GET    /api/research/tasks/{task_id}
       Returns: ResearchTask (status, progress_pct, current_step, result_markdown?)

GET    /api/research/tasks
       Query: status?, limit?, offset?
       Returns: paginated list of tasks for the workspace

DELETE /api/research/tasks/{task_id}
       Cancels a running or pending task.

GET    /api/research/tasks/{task_id}/events
       SSE stream of progress events. See above.

GET    /api/research/tasks/{task_id}/report
       Returns: the completed research report as Markdown or HTML.
       404 if task is not completed.
```

---

## UI Changes

**Research panel:** Replace the current "run and wait" interaction with a persistent job list. When a research job starts, show a card with status, progress bar, and current step text. The card persists across page refreshes. Clicking the card opens the report if complete, or shows live progress if still running.

**Research history:** A "Past Research" section in the left sidebar (or workspace search) lists the last 20 completed research tasks with their queries, dates, and links to the saved reports in the document store.

**Reconnect on refresh:** On mount, the client checks if there is a research task in progress for this workspace (stored in `localStorage` as `keprix_active_research_task_id`). If yes, it reconnects to the SSE stream with the last known event ID.

---

## Cleanup Cron

```python
# In cron scheduler (Prompt 15):
# Run nightly. Deletes tasks and their events older than 30 days.

async def cleanup_expired_research_tasks():
    await db.execute(
        "DELETE FROM research_tasks WHERE expires_at < NOW()"
    )
```

---

## Acceptance Criteria

- `POST /api/research/tasks` returns immediately with `{ task_id, status: "pending" }` while the job runs in the background.
- After posting, `GET /api/research/tasks/{task_id}` returns status updates reflecting real progress.
- Closing and reopening the browser, then `GET /api/research/tasks/{task_id}/events?since_id=0`, replays all events from the beginning.
- `DELETE /api/research/tasks/{task_id}` sets status to `cancelled` and the runner stops at the next step boundary.
- A cancelled task emits a `cancelled` event visible in the event stream.
- A completed task has `result_document_id` set and the document exists in the document store.
- `ResearchRunner._run` catches all exceptions and sets status to `failed` with the error message; it does not propagate uncaught exceptions into the event loop.
- `is_cancelled` is checked between every pipeline step; a cancellation request is honoured within one step (at most a few seconds delay).
- Tasks older than 30 days are deleted by the cleanup cron; the cleanup is idempotent.
- Invalid task ID format (not matching `rsch-[a-z0-9]{8}`) returns HTTP 422 with a clear error.
