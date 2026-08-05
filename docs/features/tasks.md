# Tasks

Kanban board for to-do, in progress, and done items at `/tasks`.

## Web UI

- Three-column Kanban with **drag and drop** between columns and reorder within a column
- Soft WIP limit on **In progress** (default 5; warns when over, does not block)
- Create and edit tasks (title, description, status, priority, due date, tags)
- Start / Complete / Reopen buttons as a non-drag fallback
- Search across title, description, and tags (clear search to drag)
- Overdue highlighting when a due date has passed
- Delete from the card or edit dialog

## API

| Action | Endpoint |
| --- | --- |
| List | `GET /api/workspace/tasks?status=todo` |
| Create | `POST /api/workspace/tasks` |
| Update | `PUT /api/workspace/tasks/{id}` |
| Complete | `POST /api/workspace/tasks/{id}/complete` |
| Delete | `DELETE /api/workspace/tasks/{id}` |
| Reorder | `POST /api/workspace/tasks/reorder` |

Statuses: `todo`, `in_progress`, `done`. Priorities: `low`, `normal`, `high`, `urgent`.

Drag moves call status update (when the column changes) then `reorder` so column order persists.

## Agent scheduling

Agents can create and complete tasks during long-horizon runs. Cron jobs may sweep overdue tasks. Agent-scheduled tasks show an Agent chip on the board.

## Related

- [Calendar](calendar.md)
- [Workspace overview](workspace.md)
