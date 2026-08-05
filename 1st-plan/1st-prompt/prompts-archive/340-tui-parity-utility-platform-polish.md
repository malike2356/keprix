# keprix - Prompt 340: TUI Parity; Utility Library, Platform Support, and Polish

## Purpose

Hermes's TUI ships an extensive utility library that handles platform detection, terminal capability probing, emoji/math unicode, syntax highlighting, performance monitoring, and graceful degradation across operating systems and terminal emulators. keprix's TUI has minimal platform awareness.

This prompt builds the utility layer that makes the TUI work perfectly across Linux, macOS, Windows, and Android (Termux), with comprehensive terminal emulator compatibility.

## What Hermes has that keprix doesn't

### Platform detection
- **OS detection**; Linux, macOS, Windows, Termux (Android) adaptive behavior
- **Shell detection**; bash, zsh, fish, PowerShell, cmd.exe
- **Terminal emulator detection**; Kitty, WezTerm, foot, iTerm2, Windows Terminal, Alacritty, tmux, screen, VS Code terminal
- **Feature detection**; 24-bit truecolor, OSC 52 clipboard, mouse support, alternate screen, bracketed paste, synchronized output, kitty keyboard protocol

### Terminal setup
- **Truecolor force**; Environment variable to force 24-bit color on terminals that don't advertise it
- **Terminal parity mode**; Strips advanced features for basic terminals (VT100 compat)
- **Graceful degradation**; Auto-detects terminal capabilities and degrades features silently (no error spam)
- **Startup probe**; On launch, probes terminal for available features, caches results
- **Termux compatibility**; Limited colors, no alternate screen, no mouse, simplified UI

### Unicode and text
- **Emoji detection**; Detects emoji width (single vs double width characters), handles ZWJ sequences
- **Math unicode**; Renders mathematical symbols with proper spacing
- **Bidi text**; Basic bidirectional text support (RTL languages)
- **Width calculation**; `wcwidth`-style character width calculation for proper layout

### Performance
- **FPS monitoring**; Built-in FPS counter, frame time histogram, toggle with keyboard shortcut
- **Memory monitoring**; Real-time heap usage, GC hints, memory pressure indicator
- **Render budget**; Target 60fps, drops frames gracefully under load
- **Profiling**; Built-in profiling toggle, flame graph export

### Developer tools
- **Debug overlay**; Toggle with `/debug`, shows render tree, event log, state inspector
- **Log viewer**; View application logs in a panel, filter by level, search, export
- **Error boundary**; Catches render errors, shows error overlay with stack trace, doesn't crash

### Integration helpers
- **External CLI**; Launches external CLIs (keprix, nix, docker) and captures output
- **External link**; Opens URLs in browser (xdg-open, open, start)
- **Live progress**; Progress bar component for long operations
- **Input metrics**; Live character/word/token count with estimated cost display

## Tasks

1. **Platform and terminal detection**
   - Build `tui/platform_detect.py`; OS detection, shell detection, terminal emulator identification
   - Build `tui/terminal_capabilities.py`; feature detection, truecolor, OSC 52, mouse, alternate screen, bracketed paste
   - Build `tui/terminal_startup.py`; probe on launch, cache capabilities, degrade gracefully
   - Add Termux compatibility mode with simplified UI

2. **Unicode and text handling**
   - Build `tui/unicode_width.py`; proper character width calculation (wcwidth-equivalent)
   - Build `tui/emoji.py`; emoji width detection, ZWJ sequence handling
   - Build `tui/bidi.py`; basic bidirectional text support for RTL

3. **Performance monitoring**
   - Build `tui/fps_monitor.py`; FPS counter, frame time histogram, keyboard toggle
   - Build `tui/memory_monitor.py`; heap usage, GC hints, memory pressure indicator
   - Build `tui/render_budget.py`; target 60fps, frame drop detection

4. **Developer tools**
   - Build `tui/debug_overlay.py`; render tree, event log, state inspector
   - Build `tui/log_viewer.py`; application log viewer with filter, search, export
   - Build `tui/error_boundary.py`; catches render errors, shows stack trace overlay

5. **Integration helpers**
   - Build `tui/external_cli.py`; launch external CLI, capture output
   - Build `tui/external_link.py`; open URLs in browser
   - Build `tui/live_progress.py`; progress bar component
   - Build `tui/input_metrics.py`; live token count, estimated cost

## Files to create

```
src/keprix/tui/
  platform_detect.py           - OS, shell, terminal emulator detection
  terminal_capabilities.py     - feature detection and caching
  terminal_startup.py          - startup probe, graceful degradation
  unicode_width.py             - character width calculation
  emoji.py                     - emoji detection and width handling
  bidi.py                      - bidirectional text support
  fps_monitor.py               - FPS counter, frame time histogram
  memory_monitor.py            - heap usage, GC hints
  render_budget.py             - frame budget, drop detection
  debug_overlay.py             - render tree, event log, state inspector
  log_viewer.py                - application log viewer
  error_boundary.py            - render error catcher
  external_cli.py              - external CLI launcher
  external_link.py             - browser opener
  live_progress.py             - progress bar component
  input_metrics.py             - live token/cost counter

tests/tui/
  test_platform_detect.py
  test_terminal_capabilities.py
  test_unicode_width.py
  test_emoji_width.py
  test_fps_monitor.py
  test_error_boundary.py
```

## Acceptance criteria

- Terminal emulator auto-detected on launch (Kitty, WezTerm, foot, iTerm2, Windows Terminal, etc.)
- 24-bit truecolor, OSC 52, mouse, alternate screen detected and cached
- Features silently degrade on unsupported terminals (no error spam)
- Termux mode provides functional UI on Android terminals
- Emoji width properly calculated (single vs double width, ZWJ sequences)
- FPS counter toggleable, frame time histogram available
- Render errors caught by error boundary, stack trace shown in overlay
- Browser links open via xdg-open/open/start
- External CLI output captured and displayed
- keprix theme applied consistently
