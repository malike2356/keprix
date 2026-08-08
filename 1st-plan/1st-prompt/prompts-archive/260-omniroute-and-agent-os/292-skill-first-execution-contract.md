# Keprix - Prompt 292: Skill-first execution contract

**Pack:** Fable-class product power (292-297)  
**Master reference:** `../prompts-archive/ref-292-fable-class-product-power-master-reference.md`  
**Depends on:** Layered system prompt **289**, skills hub / preprocessing

## UI entry point

Primary location: Skills Hub + agent loop (no new top-level nav)  
Secondary locations: `/skills`, session tool transcript showing `view_skill` / skill reads  
Empty state: none (operator feature; skills already installed)  
Discovery trigger: none  
Nav placement: under Skills (existing)

## Context

Fable 5 requires reading relevant `SKILL.md` before writing code, creating files, or running computer tools. Skills encode environment-specific constraints that are not in model weights. Skipping the skill read lowers output quality even when the model "already knows" the format.

Keprix has skills, hubs, and preprocessing, but skill-first is not a hard execution contract. This prompt makes it structural.

## What already exists (do not rebuild)

- `tools/skills_tool.py`, `tools/skill_manager_tool.py`, `tools/skills_hub.py`
- `agent/skill_preprocessing.py`, `agent/skill_commands.py`
- Optional skills under `src/keprix/optional-skills/` and `skills/`
- Layered prompt `agent/layers/` (**289**)
- Agent OS skill proposals / promoter (archived 248/260)

## What to build

### 1. Skill-first gate

`src/keprix/agent/skill_first.py`:

```python
class SkillFirstGate:
    """
    Before file create, code execution, or computer_use, require that
    every plausibly relevant SKILL.md was viewed in this turn (or cached
    for the session with TTL).
    """

    FILE_CODE_BASH_TOOLS = frozenset({
        "write_file", "create_file", "str_replace", "execute_code",
        "terminal", "bash", "computer_use", "run_terminal_cmd",
    })

    async def before_tool(self, tool_name: str, args: dict, session) -> SkillFirstDecision:
        ...
```

Rules:
- Scan available skills (bundled + user + workspace).
- Match by task keywords, skill frontmatter `triggers`, and tool category.
- If matches exist and none were `view`ed this turn, return `REQUIRE_SKILL_READ` with the list of paths (do not invent content).
- Inject a system nudge or auto-queue `view`/`read_file` on those SKILL.md paths before allowing the gated tool.
- Operator profile `permissive` may soften to warn-once; `strict`/`standard` block until read.

### 2. Layered prompt execution clause

Extend `agent/layers/execution.py` (or add `skills_contract.py` layer):

```text
Before creating files, writing code, or running bash/computer tools:
1. Scan available skills.
2. View every plausibly relevant SKILL.md.
3. Follow environment constraints in those skills.
Skipping this step is a defect, not an optimization.
```

### 3. Audit

Log to tool audit / Scout:
- `skill_first.required`
- `skill_first.satisfied`
- `skill_first.bypassed` (profile + reason)

### 4. Tests

- Creating a pptx/docx/pdf path without skill read is blocked or auto-reads skill.
- Multiple skills can apply to one task; all matched skills must be viewed.
- Core conversational tools (chat-only) are not gated.

## Files to create / modify

```
src/keprix/agent/skill_first.py
src/keprix/agent/layers/execution.py   # or new skills_contract layer
src/keprix/tools/tool_executor.py      # hook before gated tools
tests/agent/test_skill_first.py
docs/features/skill-first-execution.md
```

## Acceptance criteria

- Gated tools cannot complete a successful write/exec path without a prior skill view when a matching skill exists.
- Skill reads appear in the session transcript.
- No stubs: gate is wired into the real tool executor path.
- Tests cover match, multi-skill, and ungated tools.

## Contact

Verlox Ltd: [contact@verlox.uk](mailto:contact@verlox.uk)
