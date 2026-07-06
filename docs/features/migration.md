# Migration

This page covers migrating to Keprix from another agent platform, importing data from external sources, and upgrading between Keprix versions.

## Migrating from another platform

### From Open WebUI

Open WebUI stores conversations and settings in an SQLite database. Export and import:

1. On your Open WebUI instance, go to **Settings > Database > Export**.
2. Download the SQLite file.
3. Run the Keprix migration script:

```bash
python3 -m keprix.keprix_cli.main migrate from-open-webui \
  --source /path/to/webui-export.db \
  --import-conversations \
  --import-settings
```

Conversations are imported as read-only history. Model configurations are mapped to Keprix LLM provider entries (review and confirm mappings).

### From Flowise / LangFlow

Export your flows as JSON from the Flowise/LangFlow UI. Keprix provides a best-effort converter that maps common nodes to playbook steps:

```bash
python3 -m keprix.keprix_cli.main migrate from-flowise \
  --source flowise-export.json \
  --output .keprix/playbooks/
```

Nodes that have no Keprix equivalent are exported as `code` steps with a comment explaining what the original node did. Review the generated YAML before running.

### From n8n

Export workflows as JSON from n8n. The converter maps HTTP nodes, code nodes, and conditional nodes:

```bash
python3 -m keprix.keprix_cli.main migrate from-n8n \
  --source n8n-export.json \
  --output .keprix/playbooks/
```

### From CrewAI

CrewAI Python scripts can be converted to Keprix agent team configurations. Provide the Python file:

```bash
python3 -m keprix.keprix_cli.main migrate from-crewai \
  --source crew.py \
  --output .keprix/teams/
```

See [Agent teams](agent-teams.md) for the resulting team YAML format.

## Importing data

### Importing documents into memory

Bulk-import documents into the global memory store:

```bash
python3 -m keprix.keprix_cli.main memory import \
  --source /path/to/docs/ \
  --collection my-knowledge-base \
  --recursive
```

Supports PDF, DOCX, Markdown, plain text, and HTML.

### Importing conversations

Import conversation history from a JSON file (one object per line, each with `role` and `content`):

```bash
python3 -m keprix.keprix_cli.main conversations import \
  --file conversations.jsonl \
  --user admin@example.com
```

## Upgrading Keprix

### Minor versions (1.x.y -> 1.x.z)

```bash
git pull
docker compose -f docker/docker-compose.yml up -d --build
```

The backend applies database migrations automatically on startup.

### Minor versions (1.x -> 1.y)

Same process, but review the CHANGELOG for any breaking changes to env vars or configuration before restarting.

### Major versions (1.x -> 2.x)

Major versions may include data migrations. The process is:

1. Take a full backup: `python3 -m keprix.keprix_cli.main backup create`.
2. Review the upgrade guide in the release notes.
3. Pull the new version and run with `--build`.
4. The migration runner executes automatically on startup.
5. If migration fails, restore from backup: `python3 -m keprix.keprix_cli.main backup restore <id>`.

### Rolling back

If an upgrade breaks something:

1. Stop the stack: `docker compose -f docker/docker-compose.yml down`.
2. Check out the previous version: `git checkout v1.x.y`.
3. Restore the database backup (if schema changed): `python3 -m keprix.keprix_cli.main backup restore <id>`.
4. Restart: `docker compose -f docker/docker-compose.yml up -d --build`.

## Exporting your data

Export everything (conversations, files, memory, settings) as a ZIP:

```bash
python3 -m keprix.keprix_cli.main export full --output keprix-export.zip
```

Individual exports:

```bash
python3 -m keprix.keprix_cli.main export conversations --output conversations.jsonl
python3 -m keprix.keprix_cli.main export memory --collection all --output memory-export.json
python3 -m keprix.keprix_cli.main export settings --output settings.json
```

## Related

- [Quickstart](../getting-started/quickstart.md)
- [Security architecture](../security/architecture.md)
- [Control center](control-center.md)
- [Playbooks](playbooks.md)
- [Agent teams](agent-teams.md)
