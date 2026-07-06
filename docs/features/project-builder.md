# Project builder

Project builder is a scoped workspace for long-horizon tasks: software projects, research initiatives, reports, or any work that spans multiple sessions and needs persistent context, files, and a structured activity log.

## What a project contains

| Item | Description |
| --- | --- |
| **Goal** | A written objective the agent uses to orient all work in the project |
| **Files** | Uploaded or agent-generated files, versioned within the project |
| **Notes** | Structured notes attached to the project, searchable |
| **Conversations** | All chat threads scoped to the project |
| **Tasks** | Sub-tasks with status tracking |
| **Memory scope** | Vector memory indexed per-project (separate from global memory) |
| **Activity log** | Timestamped record of all agent actions taken in the project |

## Creating a project

### Web UI (`/projects`)

1. Click **New project**.
2. Enter a name and goal. The goal is a natural-language statement of the project's purpose. Example: "Build a Python CLI tool that processes CSV files and generates summary charts."
3. Choose a **project type** (optional):
   - **Software**: adds a coding workspace and repository link
   - **Research**: adds a research run launcher
   - **Report**: adds a document editor
   - **Blank**: no type-specific UI
4. Click **Create project**.

### Via API

```http
POST /api/projects
{
  "name": "CSV chart tool",
  "goal": "Build a Python CLI tool that processes CSV files and generates summary charts.",
  "type": "software"
}
```

## Working in a project

All conversations started from the project page are automatically scoped to the project. The agent:

- Reads the project goal at the start of each turn.
- Indexes and retrieves project files and notes for context.
- Logs every tool call and file change to the activity log.
- Creates sub-tasks automatically when it plans multi-step work.

### Uploading files

Drag files onto the project page or use the file panel. Uploaded files are immediately available to the agent as context.

### Linking a repository

Software projects can link a GitHub repository:

1. Open the project, go to **Settings > Repository**.
2. Authenticate with GitHub.
3. Select or create a repository.

Once linked, the [self-coding agent](self-coding-agent.md) can open branches, commit code, and create pull requests within the project.

## Sub-tasks

The agent decomposes work into sub-tasks automatically. You can also add them manually:

```http
POST /api/projects/{project_id}/tasks
{"title": "Implement CSV parser", "status": "pending"}
```

Sub-tasks appear in the project's task list with status: `pending`, `in_progress`, `done`, `blocked`.

## Memory scope

Each project has its own vector memory collection. Documents uploaded or indexed within a project are only searched in the context of that project (unless you explicitly search the global memory).

This prevents cross-project contamination: a file in your "client A" project won't surface in your "client B" project's searches.

## Activity log

Every agent action is written to the activity log with:

- Timestamp
- User and session
- Tool called
- Input/output summary (not full content)
- Status (success/failure)

View the log in **Project > Activity** or query it:

```http
GET /api/projects/{project_id}/activity?limit=50&tool=write_file
```

## Project templates

Save a project as a template to reuse its structure:

```http
POST /api/projects/{project_id}/save-as-template
{"name": "Python CLI project"}
```

Create a new project from a template:

```http
POST /api/projects
{"name": "New CLI tool", "template_id": "python-cli-project"}
```

## Archiving and export

Archive a completed project to hide it from the active list:

```http
POST /api/projects/{project_id}/archive
```

Export a project (files, notes, conversation history, activity log) as a ZIP:

```http
GET /api/projects/{project_id}/export
```

## API

| Action | Method | Endpoint |
| --- | --- | --- |
| List projects | GET | `/api/projects` |
| Create project | POST | `/api/projects` |
| Get project | GET | `/api/projects/{id}` |
| Update project | PUT | `/api/projects/{id}` |
| Delete project | DELETE | `/api/projects/{id}` |
| Archive | POST | `/api/projects/{id}/archive` |
| Export | GET | `/api/projects/{id}/export` |
| List tasks | GET | `/api/projects/{id}/tasks` |
| Create task | POST | `/api/projects/{id}/tasks` |
| Update task | PATCH | `/api/projects/{id}/tasks/{task_id}` |
| Activity log | GET | `/api/projects/{id}/activity` |

## Related

- [Self-coding agent](self-coding-agent.md)
- [Memory and RAG](memory.md)
- [Playbooks](playbooks.md)
- [Agent teams](agent-teams.md)
