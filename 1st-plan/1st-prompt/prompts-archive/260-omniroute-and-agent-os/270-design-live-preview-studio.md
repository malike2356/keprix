# Keprix - Prompt 270: Design live preview studio

**Series:** Chase five tools adoption **267-272**.  
**Master reference:** `../prompts-archive/ref-266-chase-five-tools-adoption-master-reference.md`  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

**Design live preview studio**: localhost HTML/React artifact preview with component inspection (Chase "Impeccable" pattern), integrated into builder and coding workspace.

Operators can:

| Action | Result |
| --- | --- |
| Open HTML artifact | Sandboxed iframe preview at `/design/preview` |
| Pick component | Click-to-select DOM node; copy selector + snippet |
| Apply design skill | Invoke `claude-design` / optional `impeccable` skill with selection context |
| Hot reload | Watch file changes when previewing project path |

**Non-goals:**

- Fork Impeccable repo into core without license review
- Replace Figma or full design tool
- Remote URL preview without explicit allowlist

---

## 2. Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Design skills | `claude-design`, `popular-web-designs` |
| Impeccable test reference | `test_skill_commands.py` (symlink pattern) |
| Project builder | builder routes / workspace |
| Coding workspace | file tree + preview patterns if any |

---

## 3. Architecture

```text
/design/preview?path=... | ?artifact_id=...
        |
        v
preview_server.py (static file server or artifact resolver)
        |
        v
iframe sandbox + postMessage selection bridge
        |
        v
DesignStudioPanel (component tree, tokens, skill launcher)
        |
        v
Optional Hub skill: impeccable (optional-skills/design/)
```

---

## 4. Data model

```python
@dataclass
class PreviewSession:
    session_id: str
    root_path: str | None      # project-relative HTML entry
    artifact_id: str | None    # uploaded/built artifact
    entry_file: str            # index.html
    selected_selector: str | None
    selected_html_snippet: str | None
    created_at: str
```

Ephemeral sessions in memory or `{KEPRIX_HOME}/design/preview/{session_id}.json`.

---

## 5. API routes

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/design/preview/open` | `{ path or artifact_id, entry? }` |
| GET | `/api/design/preview/{session_id}` | Session state |
| POST | `/api/design/preview/{session_id}/selection` | Update from iframe bridge |
| GET | `/api/design/preview/{session_id}/url` | Preview URL for iframe |

Security: only paths under workspace root or registered artifact store.

---

## 6. Optional Hub skill: impeccable

**optional-skills/design/impeccable/**

- `SKILL.md` with design craft checklist (spacing, type scale, color contrast)
- Not a fork of upstream repo; original Keprix-authored content inspired by pattern
- Install via `keprix skills install impeccable` or Hub card

Studio "Apply impeccable" sends selection + file context to agent with skill slash command.

---

## 7. UI

`/design/preview` or split pane in coding workspace:

- Left: file picker / recent artifacts
- Center: iframe preview
- Right: Component inspector (tag, classes, bounding box), "Copy selector", "Improve with design skill"

Keyboard: `Esc` clears selection.

---

## 8. Files to create

```
src/keprix/design/
  preview_server.py
  preview_session_store.py

src/keprix/api/
  design_preview_routes.py

src/keprix/optional-skills/design/impeccable/
  SKILL.md

frontend/src/app/(workspace)/design/preview/page.tsx
frontend/src/components/design/PreviewFrame.tsx
frontend/src/components/design/ComponentInspector.tsx

docs/features/design-live-preview.md

tests/design/
  test_preview_server.py
  test_design_preview_routes.py
```

Wire nav: **Design > Live preview** (feature flag `design.preview.enabled`).

---

## 9. Acceptance criteria

- Local `index.html` fixture renders in iframe sandbox.
- Click selection posts selector + HTML snippet to API (jsdom or Playwright test acceptable).
- Path traversal outside workspace rejected with 403.
- "Improve with design skill" builds agent message including selector context (unit test on message builder).
- Optional impeccable skill installable and appears in skills list.
- Hot reload fires on file save for project path mode (debounced).

---

## 10. Dependencies

- **Uses:** `claude-design`, coding workspace file access
- **Parallel:** **271** preflight unrelated
- **Soft:** project builder artifacts
