# Keprix Prompt 346: TUI Renderer Superiority

## Goal

Build a Keprix renderer layer that surpasses Hermes renderer behavior while preserving Keprix visual identity and staying compatible with Textual. Do not replace Textual first. Build deterministic render primitives above it: cells, measurement, diffing, frame snapshots, streaming markdown, code block rendering, selection, viewport, and benchmarks.

Hermes is stronger because its custom renderer gives it tight layout and terminal control. Keprix must close and surpass that through a renderer abstraction that provides deterministic behavior, measurable performance, and terminal-aware degradation.

## Required renderer capabilities

### Cell model

Implement a terminal cell model:

```text
renderer/cells.py
```

Support:

- Character
- Style token
- Width
- Link target
- Selection state
- Cursor state
- Metadata id

### Measurement

Implement deterministic measurement:

```text
renderer/measure.py
```

Support:

- ASCII width
- CJK width
- Emoji width
- ZWJ sequence handling
- Combining marks
- ANSI-free measurement
- Rich/Textual markup stripped safely
- Terminal width constraints

### Frame diffing

Implement frame diffing:

```text
renderer/diff.py
```

Support:

- Previous frame vs next frame
- Dirty row detection
- Dirty cell ranges
- Stable cursor update
- No redraw when content unchanged
- Snapshot debugging output

### Streaming markdown

Upgrade streaming markdown:

```text
renderer/markdown.py
renderer/code_blocks.py
```

Support:

- Token-by-token rendering
- Unclosed markdown constructs during stream
- Code block language detection
- Syntax highlighting through existing dependency if available, graceful fallback otherwise
- Table rendering fallback
- Link detection
- Partial output preservation on interrupt

### Message rendering

Upgrade message rendering:

```text
renderer/messages.py
```

Support:

- Role grouping
- Timestamps
- Metadata hooks
- Tool call cards
- Tool result truncation and expansion
- Error rendering
- File and URL references
- Citations where available
- Keprix theme tokens, not Hermes visuals

### Selection and viewport

Improve:

```text
renderer/selection.py
renderer/viewport.py
```

Support:

- 10K+ message transcript
- Stable scroll on append
- Stable scroll on resize
- Search highlight
- Mouse selection
- Keyboard selection
- Copy selection

### Render profiler

Add:

```text
renderer/profiler.py
renderer/benchmarks.py
renderer/snapshots.py
```

Support:

- Frame timing
- Dirty row count
- Rendered cell count
- Memory usage snapshot
- Optional benchmark export
- CI-friendly benchmark assertions

## Superiority criteria

Keprix must not merely match Hermes. It must add:

- Renderer contract tests independent of Textual widgets
- Snapshot tests for complex terminal content
- Performance budgets for 10K message transcripts
- Dirty diff tests proving unchanged content is not redrawn
- Search highlight and selection tested together
- Terminal degradation snapshots for basic terminals

## Tests required

Add:

```text
tests/tui/test_renderer_cells.py
tests/tui/test_renderer_measure.py
tests/tui/test_renderer_diff.py
tests/tui/test_renderer_markdown_streaming.py
tests/tui/test_renderer_messages.py
tests/tui/test_renderer_viewport_selection.py
tests/tui/test_renderer_benchmarks.py
```

## Acceptance criteria

- Renderer primitives are pure and tested outside Textual.
- 10K message render benchmark stays under an explicit budget.
- Streaming markdown handles partial code blocks without crashing.
- Frame diff detects no-op renders.
- Unicode width is deterministic.
- Selection plus search highlight works.
- Keprix theme tokens are used; Hermes visual identity is not copied.
- Existing TUI tests pass.
- `bash scripts/check-tui-parity.sh` passes.

## Verification commands

```bash
python -m pytest tests/tui/test_renderer_cells.py tests/tui/test_renderer_measure.py tests/tui/test_renderer_diff.py -q
python -m pytest tests/tui/test_renderer_benchmarks.py -q
python -m pytest tests/tui -q
bash scripts/check-tui-parity.sh
```

