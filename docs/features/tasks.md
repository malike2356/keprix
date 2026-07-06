# Tasks

Task board for to-do, in progress, and done items at `/tasks`.

## Web UI

- Tabs: **To do**, **In progress**, **Done**
- Create tasks with title and description
- Mark complete (moves to done or removes from active list)

## API

| Action | Endpoint |
| --- | --- |
| List | `GET /api/workspace/tasks?status=todo` |
| Create | `POST /api/workspace/tasks` |
| Update | `PUT /api/workspace/tasks/{id}` |
| Complete | `POST /api/workspace/tasks/{id}/complete` |

Statuses: `todo`, `in_progress`, `done`.

## Agent scheduling

Agents can create and complete tasks during long-horizon runs. Cron jobs may sweep overdue tasks.

## Related

- [Calendar](calendar.md)
- [Workspace overview](workspace.md)
