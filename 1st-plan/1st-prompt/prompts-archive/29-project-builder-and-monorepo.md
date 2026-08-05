# keprix - Prompt 29: Project Builder and Monorepo Manager

## Context

keprix must be able to build, scaffold, analyse, rebuild, and deploy any project
in the verlox monorepo at `/opt/lampp/htdocs/verlox/` (and any future project
directory the user points it at). This is not a code editor - it is a full-stack
project lifecycle manager powered by the keprix Agent.

Projects that will be BUILT ON keprix (not just built by it):
- abbis (next generation - multi-tenant SaaS; see `keprix-projects/abbis/`)
- fleetx (fleet management)
- xeclone (platform clone engine)
- tuinApp global (global garden/outdoor services marketplace)

These four projects use the keprix SDK as their AI foundation and require
Scout governance (Prompt 30).

Output: `keprix/backend/builder/`

## What the Builder Does

Natural language interface to:
- Scaffold a new project from a template
- Analyse an existing project (tech stack, status, issues)
- Add a feature to an existing project
- Fix a bug across an existing project
- Rebuild a project (full regeneration from current state analysis)
- Run, test, and deploy a project to LAMPP or Docker
- Migrate a project from one tech stack to another

Every build action goes through the keprix Agent's synthesis loop where needed.

## Project Registry

`backend/builder/registry.py` - discovers and catalogues all projects.

On startup, scans configured root directories (default: `/opt/lampp/htdocs/verlox/`)
for projects. A directory is a project if it contains any of:
`package.json`, `composer.json`, `pyproject.toml`, `requirements.txt`,
`build.gradle`, `Package.swift`, `Makefile`, `*.xcodeproj`, `wp-config.php`

```sql
CREATE TABLE builder_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    path TEXT UNIQUE NOT NULL,
    tech_stack TEXT[] NOT NULL,           -- ['php', 'mysql', 'vanilla-js']
    stack_type TEXT,                       -- 'wordpress', 'laravel', 'nextjs', 'flutter', etc.
    framework TEXT,
    status TEXT DEFAULT 'unknown',         -- 'healthy', 'broken', 'needs-update', 'wip'
    keprix_app BOOLEAN DEFAULT false,   -- built on keprix SDK
    scout_enrolled BOOLEAN DEFAULT false,  -- enrolled in Scout governance
    last_scanned_at TIMESTAMPTZ,
    last_built_at TIMESTAMPTZ,
    build_log TEXT,
    meta JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE build_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES builder_projects(id) ON DELETE CASCADE,
    job_type TEXT NOT NULL,    -- 'scaffold', 'analyse', 'add-feature', 'rebuild', 'deploy', 'fix'
    instruction TEXT NOT NULL, -- the natural language instruction
    status TEXT DEFAULT 'pending',  -- 'pending', 'running', 'done', 'failed'
    plan JSONB,                -- the agent-generated build plan (steps)
    output TEXT,               -- aggregated stdout/stderr
    diff_summary TEXT,         -- git diff summary after job
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON build_jobs (project_id, status, created_at DESC);
```

## Stack Detector

`backend/builder/stack_detector.py` - reads a project directory and returns a
`StackReport` with:
- `stack_type`: wordpress / laravel / custom-php / nextjs / nuxt / react / svelte /
  flutter / swift / kotlin / python-fastapi / python-flask / tauri / electron /
  static-html / node-express
- `languages`: [php, javascript, typescript, python, swift, kotlin, dart, rust]
- `dependencies`: key packages with versions
- `database`: mysql / postgres / sqlite / none
- `entry_points`: main files (e.g. `index.php`, `server.js`, `main.py`)
- `has_tests`: bool
- `has_docker`: bool
- `has_git`: bool
- `estimated_completeness`: 0-100 (heuristic based on presence of key files)

## Project Templates

`backend/builder/templates/` - scaffolding templates for new projects.

Templates to implement (full file-by-file scaffolds):

### PHP Templates
- `custom-php-mvc` - matches verlox custom PHP pattern (modules/, includes/, api/, database/)
- `laravel-api` - Laravel 11 REST API
- `wordpress-theme` - custom WP theme scaffold
- `wordpress-plugin` - WP plugin scaffold

### JavaScript/TypeScript Templates
- `nextjs-saas` - Next.js 14 + TypeScript + PostgreSQL + auth (matches Aiva (commercial) pattern)
- `nuxt-ssr` - Nuxt 3 SSR (matches claude_ui pattern)
- `react-spa` - React 18 + Vite SPA
- `node-express-api` - Node.js + Express + PostgreSQL REST API
- `electron-app` - Electron + React (matches Claudia pattern)
- `tauri-app` - Tauri 2.x + React + TypeScript (matches Claudia pattern)

### Mobile Templates
- `react-native` - React Native + Expo
- `flutter` - Flutter + Dart
- `swift-ios` - Swift + SwiftUI + URLSession
- `kotlin-android` - Kotlin + Jetpack Compose

### Python Templates
- `fastapi-service` - FastAPI + PostgreSQL + SQLAlchemy
- `flask-api` - Flask + MySQL + SQLAlchemy
- `python-cli` - Click-based CLI tool

### keprix App Templates (includes SDK)
- `keprix-php-app` - PHP app with `keprix-sdk` (Python) as backend
- `keprix-nextjs-app` - Next.js app using `@keprix-ai/sdk` with domain registration
- `keprix-mobile-app` - React Native app backed by keprix

Each template generates a complete runnable project. Not stubs - complete working code.

## Build Agent

`backend/builder/build_agent.py` - orchestrates build jobs using the main keprix
agent with builder-specific tools and context.

When a build instruction is received:

1. Load the target project's StackReport
2. Build a builder system prompt:
   ```
   You are a senior full-stack developer working on {project_name}.
   Tech stack: {stack_type}. Path: {path}.
   Current state: {estimated_completeness}% complete.
   
   Your task: {instruction}
   
   You have access to:
   - file_read, file_write, file_delete tools (scoped to {path})
   - bash_exec tool (sandboxed, scoped to {path})
   - git tools (for this project's repo)
   - test_runner tool
   - deploy_to_lampp tool
   
   Follow the {stack_type} conventions exactly as found in the existing code.
   Do not introduce new dependencies unless the task requires it.
   ```
3. Run the agent, streaming output to the build job's log
4. On completion, capture the git diff and store as `diff_summary`
5. If tests exist, run them and include results
6. Update `build_jobs.status` and `build_jobs.completed_at`

## Builder Tools

These tools are added to the tool registry (Prompt 05) for use during build jobs:

### `project_analyse`
Runs StackDetector + a full file tree scan + linting. Returns a comprehensive
project health report including: dead code, broken imports, missing env vars,
outdated dependencies, security vulnerabilities (via npm audit / composer audit).

### `project_scaffold`
Given a template name and project config, generates a new project at a specified
path. Calls the template engine, writes all files, runs initial `npm install` /
`composer install` / `pip install`.

### `file_write_project`
Writes a file within the current project's path. Path-confined to the project
directory. Cannot write outside it.

### `run_tests`
Runs the project's test suite (auto-detects: phpunit, jest, pytest, go test).
Returns pass/fail counts and failed test output.

### `deploy_to_lampp`
For PHP/WordPress projects: ensures the project is accessible via XAMPP/LAMPP.
Checks Apache vhost config, symlinks if needed, runs migrations.

### `deploy_to_docker`
Builds the project's Docker image (if Dockerfile present) and starts it.
Maps to an available port. Returns the URL.

### `git_project_status`
Returns the git status, recent commits, and current branch for the project.

### `add_keprix_sdk`
Installs the keprix SDK into an existing project and generates a starter
domain registration file based on the project's existing data models.

### `enrol_scout`
Enrolls the project in Scout governance (Prompt 30). Requires Scout credentials.

## Verlox Monorepo Awareness

The builder has deep awareness of the verlox monorepo structure (from CLAUDE.md):

`backend/builder/verlox_index.py` - pre-built index of all known verlox projects:
- Maps project names to paths and stacks
- Knows the launcher pattern (hub-and-spoke)
- Knows the database naming convention (`projectname_db`)
- Knows the `includes/functions.php` helper pattern
- Knows the shared IDIMS framework at root
- Knows which projects are WordPress vs custom PHP vs Node.js

When the user says "rebuild abbis" or "add a user export feature to labyrinthcms",
the builder immediately knows the path and stack without asking.

Known verlox projects pre-indexed:
- abbis3.1, abbis3.2, abbis3.3 (custom PHP MVC, MySQL)
- labyrinthcms (Laravel-style PHP, marketplace + blog modules)
- culturalsurvey (Vanilla JS + PHP API backend)
- veloxboreholes (WordPress)
- veloxboreholes_static (static HTML/PHP)
- bweh/* (school_systems, hotel_systems, spa, breeze)
- loom/bdag2.0 (MemberLoom, PHP)
- nawafs/solutionsnics (custom PHP)
- zapstree/* (forestry projects)
- claudia (Tauri + React, desktop app)
- claude_ui (Nuxt 3 SSR)
- fleetx (to be built on keprix SDK)
- xeclone (to be built on keprix SDK)
- tuinApp (to be built on keprix SDK)

## New Projects: Built on keprix

### abbis (Next Generation)

The next version of ABBIS will be built using the keprix SDK. The builder must
be able to scaffold it:

`python -m keprix builder scaffold abbis-next --template keprix-nextjs-app`

Abbis domain entities to pre-register:
- Seeker (borehole searcher): name, location, contact, subscription_tier
- Vendor (borehole products): name, products, location, verified
- Operator (borehole driller): name, license_no, location, equipment, availability
- Association (trade body): name, members, region
- Borehole: location, depth, yield_litres, owner_id, verified
- Subscription: user_id, tier, amount_ghs, paid_at, expires_at

### fleetx

Fleet management platform. Domain entities:
- Vehicle: plate, make, model, year, status, driver_id
- Driver: name, license_no, phone, status
- Trip: vehicle_id, driver_id, origin, destination, start, end, distance_km, fuel_used
- Maintenance: vehicle_id, type, cost, date, next_due
- Fuel: vehicle_id, litres, cost, station, odometer

### xeclone

Platform clone/white-label engine. Domain entities:
- Template: name, stack_type, base_platform, features
- Clone: template_id, client_name, domain, status, deployed_at
- Feature: name, category, enabled_for_clones
- Client: name, email, plan, clones_count

### tuinApp Global

Garden/outdoor services marketplace. Domain entities:
- ServiceProvider: name, specialties, location, rating, verified
- Customer: name, location, preferred_contact
- Job: customer_id, type, location, scheduled_at, status, price
- Quote: job_id, provider_id, amount, accepted
- Review: job_id, customer_id, rating, comment

## Build API Endpoints

```
GET    /api/builder/projects                 - list all discovered projects
POST   /api/builder/projects/scan            - rescan directories for projects
GET    /api/builder/projects/{id}            - project details + stack report
GET    /api/builder/projects/{id}/tree       - file tree (2 levels deep)
GET    /api/builder/projects/{id}/analyse    - full analysis report

POST   /api/builder/projects/{id}/build      - start a build job
       Body: { "instruction": str }          - natural language instruction
GET    /api/builder/jobs                     - list all build jobs
GET    /api/builder/jobs/{job_id}            - job details + log
GET    /api/builder/jobs/{job_id}/stream     - SSE stream of build log
POST   /api/builder/jobs/{job_id}/cancel     - cancel running job

POST   /api/builder/scaffold                 - scaffold a new project
       Body: { "template": str, "name": str, "path": str, "config": {} }

GET    /api/builder/templates                - list available templates
GET    /api/builder/templates/{name}         - template details + file list
```

## Frontend Pages

`frontend/src/app/(workspace)/builder/page.tsx`:
- Project grid: cards for all discovered projects, with stack badge and health indicator
- Click project: project detail view with file tree, stack report, build history
- "Build" button: opens NL instruction input, starts build job
- "New Project" button: template selector + project config form

`frontend/src/app/(workspace)/builder/jobs/[id]/page.tsx`:
- Real-time build log (SSE stream, monospace terminal style)
- Status indicator
- Git diff panel (shows files changed)
- Test results panel

## CLI

```
python -m keprix builder list               - list all projects
python -m keprix builder analyse {name}     - analyse a project
python -m keprix builder build {name} "{instruction}"  - build
python -m keprix builder scaffold {template} {name}    - new project
python -m keprix builder status {job_id}    - job status
python -m keprix builder logs {job_id}      - job logs
python -m keprix builder deploy {name}      - deploy to LAMPP/Docker
```

## Acceptance Criteria

- `GET /api/builder/projects` returns all verlox projects discovered at configured root
- Each project has correct `stack_type` and `tech_stack` from stack detector
- `POST /api/builder/projects/{id}/build` with `{instruction: "add user export CSV feature"}`
  creates a build job, streams log, and produces changed files
- `POST /api/builder/scaffold` with `{template: "keprix-nextjs-app", name: "fleetx"}`
  creates a runnable Next.js project with SDK integration pre-wired
- Scaffolded fleetx project has Vehicle, Driver, Trip entities pre-registered
- Build log streams in real-time via SSE
- `python -m keprix builder list` shows all verlox projects with their stacks
