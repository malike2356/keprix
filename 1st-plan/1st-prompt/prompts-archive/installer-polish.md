# keprix - Prompt: Installer Polish and Zero-to-Running Refinement

## Purpose

Prompt 33 delivered a working installer. Now we make it production-grade. Every rough edge a user hits during their first five minutes with keprix is a conversion killer. This prompt addresses the friction points discovered during real-world testing and competitor analysis.

The goal: a first-time user on any supported platform goes from zero to a running keprix instance with zero confusion, zero silent failures, and clear next steps.

## Scope

Polish every surface the user touches during install:

- Install script output formatting and error handling
- Wizard UX and keyboard navigation
- Docker Compose v2 compatibility and version detection
- Bare-metal install reliability on macOS and ARM64
- Health check diagnostics when something fails
- First-run onboarding after login
- Install telemetry (opt-in, transparent)
- Offline / air-gapped install support
- Non-root Docker install guidance
- Firewall and port detection

## Output Paths

```
scripts/
  install.sh                    - refined one-command installer
  install-baremetal.sh          - polished bare-metal path
  wizard.py                     - improved interactive setup
  check-health.sh               - diagnostic health checks
  first-run.py                  - post-login onboarding
  detect-env.sh                 - environment pre-flight checks

keprix/backend/installer/
  __init__.py
  preflight.py                  - pre-install validation
  telemetry.py                  - opt-in anonymous install telemetry
  offline.py                    - air-gapped install support

keprix/docs/installer/
  troubleshooting.md            - common issues and fixes
  air-gapped.md                 - offline install guide

tests/installer/
  test_preflight.py
  test_telemetry.py
  test_offline.py
  test_wizard_ux.py
```

## Installer Output Polish

### Progress indicators

Replace raw shell output with a structured progress display:

```
keprix installer v2.1.0
-----------------------
[1/6] Checking system requirements ... OK
[2/6] Installing Docker dependencies ... SKIP (already installed)
[3/6] Downloading keprix images ... DONE (142 MB in 23s)
[4/6] Running setup wizard ... (see below)
[5/6] Starting services ... DONE
[6/6] Running health checks ... PASS (4/4)

keprix is running!
Access: http://localhost:3000
Admin:  admin / k3pr1x@1 (save this password for now.)

What next?
  - Open http://localhost:3000 in your browser
  - Run 'keprix status' to see service health
  - Run 'keprix help' to explore commands
```

If a step fails, show a clear error with the exact fix command:

```
[4/6] Running setup wizard ... FAIL
Error: Port 3000 is already in use by process 18432 (node).

Fix: Stop the conflicting process or change the port:
  keprix configure --port 3001
  Then re-run: bash scripts/install.sh --skip-checks
```

### Error taxonomy

Every error message must follow this pattern:

1. What happened (one line)
2. Why it happened (context)
3. How to fix it (actionable command)
4. Where to get more help (link to docs)

Never show raw stack traces. Log them to `install.log` and reference the log path.

### Silent failure prevention

- Every `curl`, `wget`, `docker`, `pip`, and `npm` call must be checked for exit codes.
- Network operations must have timeouts (default 30s, configurable).
- Disk space checks before downloading images.
- Memory checks before starting containers.
- Permission checks before writing to target directories.

## Wizard UX

### Keyboard navigation

- Arrow keys to move between options.
- Enter to confirm, Escape to go back.
- Tab to move between fields.
- Numbers 1-9 for quick selection in numbered lists.
- Ctrl+C exits cleanly with a summary of what was completed.

### Smart defaults

- Auto-detect available ports and suggest alternatives if the default is in use.
- Auto-detect external IP for domain setup suggestions.
- Remember previous values when re-running the wizard (only if `.env` exists).
- Validate email format, non-empty required fields, and port ranges in real time.

### Developer mode improvement

When the user answers "yes" to "Are you the owner or developer?":

- Create the identity file immediately (do not wait for service start).
- Offer to import an existing identity from `~/.keprix/identity/` if found.
- Generate and display API tokens during setup, not after.
- Pre-configure developer tools (API playground, webhook tester).

## Docker Compose v2 Compatibility

### Version detection

```bash
detect_compose() {
  if docker compose version &>/dev/null; then
    echo "v2"  # docker compose (plugin)
  elif docker-compose version &>/dev/null; then
    echo "v1"  # docker-compose (standalone, deprecated)
  else
    echo "none"
  fi
}
```

- Support both `docker compose` (v2, plugin) and `docker-compose` (v1, standalone).
- Warn if using v1 since it is deprecated.
- On v1, suggest migration: `DOCKER_COMPOSE=v1 bash install.sh` to force v1 mode.

### Compose file generation

The installer should generate `docker-compose.yml` tailored to the detected environment:

- `docker-compose.yml` for production (default).
- `docker-compose.dev.yml` when `--dev` flag is passed (mounts source, enables hot reload).
- `docker-compose.arm64.yml` when detecting ARM64 architecture (uses ARM images).

The generated file must include:

- Health checks for every service.
- Restart policies (`unless-stopped`).
- Resource limits appropriate to the detected system.
- Named volumes (not bind mounts) for data persistence.
- Proper network isolation (backend network separate from proxy network when SSL is enabled).

## Bare-Metal Install Reliability

### macOS (Homebrew)

- Detect if Homebrew is available. If not, print the install command.
- Use `brew` for Python, Node, PostgreSQL, Redis.
- macOS-specific: no systemd. Generate `launchd` plist files instead.
- Handle Apple Silicon (ARM64) vs Intel package differences.

### ARM64 / Raspberry Pi

- Detect ARM architecture.
- Use ARM-compatible Docker images where available.
- For bare metal: Python 3.11+ ARM wheels, Node.js ARM builds.
- Memory checks: minimum 4 GB for ARM (lower performance ceiling).

### Distribution-specific quirks

- Ubuntu: `apt` package names, `deadsnakes` PPA for Python 3.11+.
- Debian: same as Ubuntu but `deadsnakes` not available on older releases. Fall back to compiling Python.
- Fedora: `dnf` package names, `python3.11` from default repos.
- Arch: `pacman`, rolling release so packages are current.
- Alpine: `apk`, musl libc implications.

## Health Check Diagnostics

When health checks fail, go beyond "port not responding":

### Intelligent failure diagnosis

```
Health check failed: backend (port 3333)
  Status: Connection refused

Possible causes:
  1. Container not started -> Run: docker compose ps
  2. Port conflict -> Run: lsof -i :3333
  3. Database not ready -> Run: docker compose logs postgres | tail -20
  4. Out of memory -> Run: free -h

Full logs: install.log
```

### Progressive timeout

- First attempt: 5 seconds.
- Second attempt: 15 seconds.
- Third attempt: 30 seconds.
- After that: report failure with logs.
- Total timeout: 2 minutes (configurable via `--health-timeout`).

Between attempts, show a spinner or dot progress indicator so the user knows something is happening.

## First-Run Onboarding

After login, present a guided onboarding flow:

### Step 1: Provider setup

"keprix needs an LLM provider to work. Choose one:"

- OpenAI (enter API key)
- Anthropic (enter API key)
- Google Gemini (enter API key)
- OpenRouter (enter API key)
- Ollama (local, auto-detect)
- Skip for now

Validate the API key by making a lightweight test call. Show "Connected" or the specific error (invalid key, rate limited, network error).

### Step 2: Channel setup

"Where should keprix reach you?"

- Terminal (default, always on)
- Telegram (enter bot token)
- WhatsApp (QR code flow)
- Slack (OAuth flow)
- Email (IMAP/SMTP config)
- Skip for now

### Step 3: Quick start task

"Try sending your first message:"

Show a pre-filled prompt: "Summarise the keprix documentation and tell me three things I should know."

The user can edit and send it. This demonstrates the agent in action immediately.

### Step 4: Where to go next

Show a dashboard with:

- "Add a skill pack" -> links to hub.
- "Configure memory" -> links to memory settings.
- "Invite your team" -> links to user management.
- "Explore the API" -> links to developer docs.
- "Join the community" -> links to GitHub Discussions.

Onboarding can be skipped. Users can return via `keprix onboarding` or Settings -> Onboarding.

## Install Telemetry

### What to collect (opt-in only)

- OS and version.
- Architecture (x86_64, ARM64).
- Install method (Docker, bare metal, cloud).
- Docker Compose version (v1 or v2).
- Time to complete install.
- Steps that failed and were retried.
- Selected provider (type only, no credentials).
- Selected channels (type only, no credentials).

### What never to collect

- IP addresses.
- Domain names.
- API keys or credentials.
- Database contents.
- Any user data.

### Implementation

- Telemetry is opt-in: the wizard asks "Help us improve keprix by sending anonymous install data?" with a clear yes/no.
- Data is sent as a single POST to `https://telemetry.keprix.ai/install` (a lightweight endpoint).
- The payload is a JSON object with the fields above.
- If the endpoint is unreachable, the install continues without error (fire-and-forget).
- Users can change their preference later via `keprix configure --telemetry on|off`.

## Offline / Air-Gapped Install

For users on isolated networks or with no internet access during install:

### Pre-download bundle

```bash
# On an internet-connected machine:
keprix bundle create --output keprix-offline.tar.gz

# Transfer to air-gapped machine, then:
keprix bundle install keprix-offline.tar.gz
```

The bundle includes:

- All Docker images (saved as `.tar` files).
- Python wheels for all dependencies.
- Node.js packages (`node_modules` tarball).
- Documentation (offline-accessible).
- Default skill packs and templates.

### Air-gapped wizard

The wizard detects no internet and:

- Skips provider validation (manual key entry only).
- Skips update check.
- Shows a warning: "Some features require internet access (LLM providers, skill pack downloads, community)."
- Pre-selects Ollama as the default provider (can be local).

## Firewall and Port Detection

Before starting services, detect:

- Which ports are already in use and suggest alternatives.
- Whether a firewall is active (`ufw`, `firewalld`, `iptables`).
- Whether the install user can bind to privileged ports (<1024).

Output:

```
Port check:
  3000 (frontend)  - available
  3333 (backend)   - IN USE by process 18432 (node)
  5432 (postgres)  - available
  6379 (redis)     - available
  8080 (searxng)   - available

Firewall: ufw active
  Port 3000: DENIED -> Run: sudo ufw allow 3000
  Port 3333: DENIED -> Run: sudo ufw allow 3333
```

Offer to add the rules automatically with `sudo` (with explicit user confirmation).

## Tests

```
tests/installer/
  test_preflight.py         - OS detection, port checks, disk/memory validation
  test_wizard_ux.py         - keyboard nav, validation, smart defaults
  test_health_diagnostics.py - failure diagnosis, progressive timeout
  test_offline.py           - bundle create, bundle install, air-gapped wizard
  test_firewall.py          - port detection, firewall rule suggestions
  test_telemetry.py         - opt-in flow, payload validation, fire-and-forget
  test_onboarding.py        - provider setup, channel setup, quick start task
  test_error_messages.py    - error taxonomy, silent failure prevention
```

## Acceptance Criteria

- Running the install command on a clean Ubuntu 22.04 with Docker completes with clear progress indicators and no raw stack traces.
- A port conflict or missing dependency produces a specific, actionable error message with the fix command.
- The wizard supports keyboard navigation and validates inputs in real time.
- Health check failures produce a diagnostic report with probable causes and log paths.
- ARM64 and macOS bare-metal installs complete without architecture-specific errors.
- `keprix bundle create` produces a valid offline bundle. `keprix bundle install` restores from it on an air-gapped machine.
- Telemetry is opt-in, fire-and-forget, and never collects identifying information.
- First-run onboarding guides the user through provider setup, channel selection, and a quick-start agent task.
