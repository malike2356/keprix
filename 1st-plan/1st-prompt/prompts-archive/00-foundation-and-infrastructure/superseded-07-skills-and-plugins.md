# keprix - Prompt 07: Skills and Plugin System

## Context

Sources:
- `hermes-agent/skills/` - 71+ curated skills
- `hermes-agent/optional-skills/` - optional skill packs
- `hermes-agent/agent/skill_commands.py`, `skill_utils.py`, `skill_preprocessing.py`, `skill_bundles.py`
- `hermes-agent/agent/curator.py`, `curator_backup.py`
- `hermes-agent/plugins/` - plugin architecture
- `core.carinaai.uk/src/skills/` - Carina's 96 skills, hub, auto-writer, curator
- `openclaw/skills/` - OpenClaw skill packs
Output: `keprix/backend/skills/`, `keprix/backend/plugins/`

## Skills Framework Port (from Hermes)

Port these files verbatim:
```
agent/skill_commands.py      -> backend/skills/commands.py
agent/skill_utils.py         -> backend/skills/utils.py
agent/skill_preprocessing.py -> backend/skills/preprocessing.py
agent/skill_bundles.py       -> backend/skills/bundles.py
agent/curator.py             -> backend/skills/curator.py
agent/curator_backup.py      -> backend/skills/curator_backup.py
```

## Core Skill Packs to Include

Port ALL skill packs from these directories:

### From Hermes `hermes-agent/skills/`:
```
skills/apple/             -> backend/skills/packs/apple/
skills/autonomous-ai-agents/ -> backend/skills/packs/autonomous-ai-agents/
skills/creative/          -> backend/skills/packs/creative/
skills/data-science/      -> backend/skills/packs/data-science/
skills/devops/            -> backend/skills/packs/devops/
skills/dogfood/           -> backend/skills/packs/dogfood/
skills/email/             -> backend/skills/packs/email/
skills/index-cache/       -> backend/skills/packs/index-cache/
skills/media/             -> backend/skills/packs/media/
skills/mlops/             -> backend/skills/packs/mlops/
skills/note-taking/       -> backend/skills/packs/note-taking/
skills/productivity/      -> backend/skills/packs/productivity/
skills/research/          -> backend/skills/packs/research/
skills/smart-home/        -> backend/skills/packs/smart-home/
skills/social-media/      -> backend/skills/packs/social-media/
skills/software-development/ -> backend/skills/packs/software-development/
skills/yuanbao/           -> backend/skills/packs/yuanbao/
```

### From Hermes `hermes-agent/optional-skills/`:
```
optional-skills/autonomous-ai-agents/ -> backend/skills/optional/autonomous-ai-agents/
optional-skills/blockchain/           -> backend/skills/optional/blockchain/
optional-skills/communication/        -> backend/skills/optional/communication/
optional-skills/creative/             -> backend/skills/optional/creative/
optional-skills/devops/               -> backend/skills/optional/devops/
optional-skills/dogfood/              -> backend/skills/optional/dogfood/
optional-skills/email/                -> backend/skills/optional/email/
optional-skills/finance/              -> backend/skills/optional/finance/
optional-skills/gaming/               -> backend/skills/optional/gaming/
optional-skills/health/               -> backend/skills/optional/health/
optional-skills/mcp/                  -> backend/skills/optional/mcp/
optional-skills/migration/            -> backend/skills/optional/migration/
optional-skills/mlops/                -> backend/skills/optional/mlops/
optional-skills/payments/             -> backend/skills/optional/payments/
optional-skills/productivity/         -> backend/skills/optional/productivity/
optional-skills/research/             -> backend/skills/optional/research/
optional-skills/security/             -> backend/skills/optional/security/
optional-skills/software-development/ -> backend/skills/optional/software-development/
optional-skills/web-development/      -> backend/skills/optional/web-development/
```

### From OpenClaw `.agents/skills/`:

OpenClaw organizes skills as SKILL.md files with agent instructions. Port each
as a keprix skill file at `backend/skills/packs/openclaw/`. Each SKILL.md
becomes a `.skill` file in YAML front-matter + body format. Map the SKILL.md
content into the body. Include all:
- agent-transcript
- autoreview
- channel-message-flows
- crabbox (sandbox e2e testing)
- discord-clawd / discord-user-post / discrawl
- graincrawl / notcrawl / slacrawl
- openclaw-changelog-update -> rename to carina-changelog-update
- openclaw-debugging -> rename to keprix-debugging
- openclaw-pr-maintainer -> rename to carina-pr-maintainer
- openclaw-qa-testing -> rename to carina-qa-testing
- openclaw-secret-scanning-maintainer -> rename to carina-secret-scanning
- openclaw-small-bugfix-sweep -> rename to carina-bugfix-sweep
- release skills -> rename all `openclaw-` to `keprix-`
- security-triage
- tag-duplicate-prs-issues
- technical-documentation
- telegram-crabbox-e2e-proof -> rename to carina-telegram-e2e-proof
- verify-release

### From Aiva (commercial) `core.carinaai.uk/src/skills/packs/`:

Read all 16 packs (96 skills) and port each as Python skill definitions.
For any skill already covered by a Hermes skill, compare and keep the richer
version. Add net-new skills from Aiva (commercial) that Hermes does not have.

## Skills Hub

Port the Aiva (commercial) skills hub from `core.carinaai.uk/src/skills/` hub:
- `backend/skills/hub.py` - skill discovery, search, install from registry
- `backend/skills/auto_writer.py` - auto-generate skill files from a description
- Skills Hub server command: `python -m keprix skills hub --port 4001`

## Plugin Architecture (from Hermes)

Port ALL plugins from `hermes-agent/plugins/`:
```
plugins/browser/            -> backend/plugins/browser/
plugins/context_engine/     -> backend/plugins/context_engine/
plugins/dashboard_auth/     -> backend/plugins/dashboard_auth/
plugins/disk-cleanup/       -> backend/plugins/disk_cleanup/
plugins/google_meet/        -> backend/plugins/google_meet/
plugins/hermes-achievements/ -> backend/plugins/carina-achievements/
plugins/image_gen/          -> backend/plugins/image_gen/
plugins/kanban/             -> backend/plugins/kanban/
plugins/memory/             -> backend/plugins/memory/ (already in Prompt 06)
plugins/model-providers/    -> backend/plugins/model_providers/
plugins/observability/      -> backend/plugins/observability/
plugins/platforms/          -> backend/plugins/platforms/
plugins/security-guidance/  -> backend/plugins/security_guidance/
plugins/spotify/            -> backend/plugins/spotify/
plugins/teams_pipeline/     -> backend/plugins/teams_pipeline/
plugins/video_gen/          -> backend/plugins/video_gen/
plugins/web/                -> backend/plugins/web/
```

In `plugins/hermes-achievements/` rename all internal references from
"Hermes" to "keprix".

## Plugin SDK

Port `openclaw/packages/` plugin SDK TypeScript types as a Python equivalent:
`backend/plugins/sdk.py` - defines the Plugin ABC:
```python
class CarinaPlugin(ABC):
    name: str
    version: str

    @abstractmethod
    async def on_load(self, config: dict) -> None: ...

    @abstractmethod
    async def on_unload(self) -> None: ...

    def get_tools(self) -> list[ToolDefinition]: return []
    def get_skills(self) -> list[SkillDefinition]: return []
```

## MCP Optional Servers

Port from `hermes-agent/optional-mcps/`:
```
optional-mcps/linear/  -> keprix/mcp/optional/linear/
optional-mcps/n8n/     -> keprix/mcp/optional/n8n/
```

## Skill Count Target

At startup, `python -m keprix skills list` must show at least 140 skills
(96 from Aiva (commercial) + skills from Hermes packs + OpenClaw skills,
after deduplication).

## Acceptance Criteria

- `from backend.skills.commands import SkillCommand` imports clean
- `python -m keprix skills list` outputs at least 140 skill names
- `python -m keprix skills hub` starts the hub server on port 4001
- All plugin directories have an `__init__.py` and a `plugin.py` implementing `CarinaPlugin`
- `auto_writer.py` generates a valid `.skill` file from a one-line description
