# keprix - Prompt 15: Cron, Automation, and Scheduled Agent Tasks

## Context

Sources:
- `hermes-agent/cron/` - Hermes cron system
- `hermes-agent/hermes_cli/subcommands/` - CLI subcommands including cron management
- `odysseus/routes/task_routes.py` - agent-scheduled tasks (covered in Prompt 07)
- `core.carinaai.uk/src/` workers and scheduled jobs
Output: `keprix/backend/cron/`

## Cron System Port (from Hermes)

Port from `hermes-agent/cron/` verbatim:
```
cron/                  -> backend/cron/
  scripts/             -> backend/cron/scripts/
```

Apply standard renames (hermes -> keprix, HERMES_ -> keprix_).

## What the Cron System Does

The cron system runs scheduled agent tasks. Examples:
- "Every morning at 7am, check my email and summarize overnight messages"
- "Every Monday, create a weekly task list"
- "Every hour, check weather and alert me if rain is expected"
- "Every day at 6pm, generate a progress report and send to Telegram"

Cron jobs run the full keprix agent with a specified prompt on a schedule.
They use the same conversation loop, tools, and skills as interactive sessions.

## Cron Job Schema

```sql
CREATE TABLE cron_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    schedule TEXT NOT NULL,         -- crontab expression: "0 7 * * *"
    prompt TEXT NOT NULL,           -- agent prompt to run
    model TEXT,                     -- optional model override
    skills TEXT[] DEFAULT '{}',     -- skills to activate for this job
    tools TEXT[] DEFAULT '{}',      -- tool allowlist (empty = all)
    output_channel TEXT,            -- where to send result: telegram, discord, email, etc.
    output_channel_config JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    last_run_at TIMESTAMPTZ,
    last_run_status TEXT,           -- 'success', 'error', 'running'
    last_run_output TEXT,
    next_run_at TIMESTAMPTZ,
    run_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON cron_jobs (user_id, is_active, next_run_at);

CREATE TABLE cron_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES cron_jobs(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    output TEXT,
    tokens_used INT,
    duration_ms INT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX ON cron_runs (job_id, started_at DESC);
```

## Cron API Endpoints

```
POST   /api/cron/jobs                 - create cron job
GET    /api/cron/jobs                 - list all jobs with next/last run info
GET    /api/cron/jobs/{id}            - get job details
PUT    /api/cron/jobs/{id}            - update job
DELETE /api/cron/jobs/{id}            - delete job
POST   /api/cron/jobs/{id}/run        - trigger immediately (ignore schedule)
POST   /api/cron/jobs/{id}/enable     - enable
POST   /api/cron/jobs/{id}/disable    - disable
GET    /api/cron/jobs/{id}/runs       - history of runs (paginated)
GET    /api/cron/runs/{run_id}        - get run output
```

## Cron Runner

`backend/cron/runner.py`:
- Uses `APScheduler` (AsyncIOScheduler) for cron scheduling
- On startup: loads all active jobs from DB, schedules them
- On job trigger: creates a `cron_runs` record, runs the agent, updates record on complete
- Missed jobs (server was down): log as missed, do not retroactively run
- Max concurrent cron jobs: configurable via `keprix_CRON_MAX_CONCURRENT` (default: 3)
- Timeout per job: configurable via `keprix_CRON_TIMEOUT_MINUTES` (default: 10)

## CLI Commands

```
python -m keprix cron list          - list all cron jobs
python -m keprix cron add           - interactive cron job creator
python -m keprix cron run {id}      - trigger a job now
python -m keprix cron disable {id}  - disable job
python -m keprix cron enable {id}   - enable job
python -m keprix cron delete {id}   - delete job
python -m keprix cron logs {id}     - show last 10 run logs
```

Port the Hermes cron subcommand from `hermes_cli/subcommands/` as the basis,
then adapt to the keprix DB schema.

## Cron Delivery Channels

When a cron job completes, it can deliver output to a configured channel.
`output_channel` can be: `telegram`, `discord`, `slack`, `email`, `webhook`.
`output_channel_config` contains channel-specific settings (e.g. chat_id for Telegram).

Implement `backend/cron/delivery.py` that routes the output to the specified channel
using the gateway adapters from Prompt 06.

## Autonomous Agent Scheduling

From Aiva (commercial) workers pattern:

`backend/cron/autonomous.py` - keprix can propose cron jobs to the user:
- After completing a repetitive task, the agent may suggest: "Want me to do this
  automatically every [interval]? I can create a cron job for it."
- This appears as a suggestion card in the chat UI
- If user confirms, the agent calls `create_cron_job` tool automatically

## Task Queue

`backend/cron/queue.py` - internal task queue for non-cron async work:
- Deep Research jobs (Prompt 10)
- Email AI pipeline (Prompt 08)
- RAG indexing (Prompt 04)
- Playbook download jobs (Prompt 10)
- Push notification delivery (Prompt 11)
- All queued tasks run in asyncio background tasks
- Queue state persisted in Redis for recovery after restart
- `GET /api/admin/queue/status` - admin endpoint to view queue depth and running tasks

## Hermes Cron Scripts

Port `hermes-agent/cron/scripts/` verbatim to `backend/cron/scripts/`.
These are pre-built skill scripts that can be attached to cron jobs as templates
(e.g. "daily email summary", "weekly report", "morning briefing").

Rename any "Hermes" or "hermes" strings in these scripts to "keprix" / "keprix".

## Acceptance Criteria

- `POST /api/cron/jobs` with `{name, schedule: "0 7 * * *", prompt: "check email"}` creates job
- `POST /api/cron/jobs/{id}/run` triggers immediate run and returns run_id
- Cron runner starts automatically with `python -m keprix start`
- Job scheduled for `*/1 * * * *` runs within 65 seconds and creates a `cron_runs` record
- Output delivery to Telegram sends a message when TELEGRAM_BOT_TOKEN is set
- `GET /api/cron/jobs/{id}/runs` returns run history with status and output
- Queue status endpoint returns queue depth count
