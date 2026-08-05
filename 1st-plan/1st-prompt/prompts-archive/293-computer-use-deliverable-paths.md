# Keprix - Prompt 293: Computer-use deliverable paths

**Pack:** Fable-class product power (292-297)  
**Master reference:** `../prompts-archive/ref-292-fable-class-product-power-master-reference.md`  
**Depends on:** **292** skill-first; existing `tools/computer_use/`

## UI entry point

Primary location: Session file attachments / present_files strip  
Secondary locations: Documents gallery, chat download chips  
Empty state: "No deliverables yet. Ask the agent to create a file."  
Discovery trigger: none  
Nav placement: Sessions / Documents (existing)

## Context

Fable's computer-use contract is simple and powerful:

1. Scratch work in a private working directory
2. Final deliverables only in an outputs directory
3. Explicit `present_files` so the user can open results
4. Short files: write once to outputs; long files: iterate in scratch, then copy

Keprix has computer_use, terminal, and file tools, but paths and "present" semantics are fragmented across providers and UIs. This prompt unifies the deliverable contract so any model feels as capable as Fable at shipping artifacts.

## What already exists (do not rebuild)

- `tools/computer_use/` (backend, cua, schema, vision routing)
- `tools/file_tools.py`, `tools/file_operations.py`, terminal / execute_code
- Workspace documents / gallery routes
- Write approval and file safety gates (**275**)

## What to build

### 1. Path contract

`src/keprix/agent/deliverable_paths.py`:

```python
@dataclass(frozen=True)
class DeliverableLayout:
    scratch_dir: Path      # agent-only scratch (session-scoped)
    uploads_dir: Path      # user uploads (read-mostly)
    outputs_dir: Path      # user-visible finals only
```

Rules:
- All intermediate work goes to `scratch_dir`.
- Only final deliverables are copied/written to `outputs_dir`.
- Uploads are never overwritten in place; copy to scratch first.
- Skills under skill roots remain read-only (copy-out to edit).

### 2. `present_files` tool

Bridge tool that:
- Accepts one or more paths under `outputs_dir`
- Registers them on the session as downloadable attachments
- Emits UI events for chat chips / Documents
- Refuses to present scratch paths (must copy first)

### 3. File-creation strategy (prompt + runtime)

Encode Fable's short vs long strategy in the execution layer:

- Short (<100 lines): write directly to outputs
- Long: outline in scratch, section by section, then copy final to outputs + `present_files`
- Prefer markdown over docx unless the user asks for Word

### 4. Artifact vs chat decision helper

`classify_deliverable_intent(user_text) -> inline | file`

Standalone blog/report/component/presentation → file.  
Strategy/summary/brainstorm → inline unless user asks to save.

### 5. Tests

- Scratch files are not presentable
- Outputs files appear in session attachments after `present_files`
- Skill-first still runs before create (**292**)

## Files to create / modify

```
src/keprix/agent/deliverable_paths.py
src/keprix/tools/present_files_tool.py
src/keprix/agent/layers/execution.py
frontend: session attachment chip for presented files (minimal)
tests/agent/test_deliverable_paths.py
docs/features/computer-use-deliverables.md
```

## Acceptance criteria

- Agent-created finals are always under outputs and presentable.
- Users never need to dig through scratch paths.
- Computer_use / write_file / execute_code honor the layout.
- Docs describe the three directories clearly for operators.

## Contact

Verlox Ltd: [contact@verlox.uk](mailto:contact@verlox.uk)
