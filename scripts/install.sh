#!/usr/bin/env bash
# Keprix Hermes-parity installer (CLI / TUI first).
#
# Pipe mode (stranger UX):
#   curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash
# When piped, BASH_SOURCE does not point at a checkout. The script clones/updates
# into ${KEPRIX_HOME:-$HOME/.keprix}/keprix and installs there.
#
# Checkout mode (contributors):
#   bash scripts/install.sh
# If this file lives in a real repo (../pyproject.toml present), install into that
# repo's .venv and symlink keprix onto PATH.
#
# Until the GitHub repo is anonymously public, the curl one-liner fails closed
# (raw URL 404). See docs/operations/public-github-checklist.md.
#
# Env overrides:
#   KEPRIX_HOME              data/config/state home (default: $HOME/.keprix)
#   KEPRIX_REPO_URL          git clone URL (default: https://github.com/malike2356/keprix.git)
#   KEPRIX_REF               branch or tag (default: main)
#   KEPRIX_NONINTERACTIVE=1  skip wizard prompts; still install CLI
#   KEPRIX_DRY_RUN=1         print planned actions only; exit 0 (tests)
#   KEPRIX_INSTALL_DOCKER=1  optionally start Compose after CLI install
set -euo pipefail

KEPRIX_HOME="${KEPRIX_HOME:-$HOME/.keprix}"
KEPRIX_REPO_URL="${KEPRIX_REPO_URL:-https://github.com/malike2356/keprix.git}"
KEPRIX_REF="${KEPRIX_REF:-main}"
KEPRIX_NONINTERACTIVE="${KEPRIX_NONINTERACTIVE:-0}"
KEPRIX_DRY_RUN="${KEPRIX_DRY_RUN:-0}"
KEPRIX_INSTALL_DOCKER="${KEPRIX_INSTALL_DOCKER:-0}"

BIN_DIR="${KEPRIX_BIN_DIR:-$HOME/.local/bin}"
STATE_FILE="$KEPRIX_HOME/install-state.json"
PYTHON="${PYTHON:-python3}"

log() { echo "==> $*"; }
warn() { echo "WARNING: $*" >&2; }
die() { echo "ERROR: $*" >&2; exit 1; }

detect_os() {
  local uname_s
  uname_s="$(uname -s 2>/dev/null || echo unknown)"
  case "$uname_s" in
    Linux)
      if grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null; then
        echo "wsl"
      else
        echo "linux"
      fi
      ;;
    Darwin) echo "macos" ;;
    *) echo "unknown" ;;
  esac
}

# Resolve install mode: checkout (local clone) vs piped (curl | bash / no checkout).
resolve_root_and_mode() {
  local src script_dir candidate
  src="${BASH_SOURCE[0]:-}"
  MODE="piped"
  ROOT=""

  # Checkout: BASH_SOURCE is a real file and repo root has pyproject.toml.
  if [[ -n "$src" && -f "$src" ]]; then
    script_dir="$(cd "$(dirname "$src")" && pwd)"
    candidate="$(cd "$script_dir/.." && pwd)"
    if [[ -f "$candidate/pyproject.toml" ]]; then
      MODE="checkout"
      ROOT="$candidate"
      return 0
    fi
  fi

  # Piped / no checkout: clone lives under KEPRIX_HOME.
  MODE="piped"
  ROOT="$KEPRIX_HOME/keprix"
}

path_has_bin_dir() {
  case ":$PATH:" in
    *":$BIN_DIR:"*) return 0 ;;
    *) return 1 ;;
  esac
}

print_dry_run() {
  echo "KEPRIX_DRY_RUN=1: planned actions (no clone, no install)"
  echo "  mode:           $MODE (piped vs checkout)"
  echo "  KEPRIX_HOME:    $KEPRIX_HOME"
  echo "  ROOT (code):    $ROOT"
  echo "  VENV:           $ROOT/.venv"
  echo "  BIN symlink:    $BIN_DIR/keprix -> $ROOT/.venv/bin/keprix"
  echo "  STATE_FILE:     $STATE_FILE"
  echo "  KEPRIX_REF:     $KEPRIX_REF"
  echo "  KEPRIX_REPO_URL:$KEPRIX_REPO_URL"
  echo "  install docker: $KEPRIX_INSTALL_DOCKER"
  echo "  noninteractive: $KEPRIX_NONINTERACTIVE"
  if [[ "$MODE" == "piped" ]]; then
    echo "  action: clone/update into $ROOT then uv/pip install -e \".[tui]\""
  else
    echo "  action: install into existing checkout ROOT .venv (no clone)"
  fi
}

ensure_home_layout() {
  mkdir -p "$KEPRIX_HOME"
  mkdir -p "$BIN_DIR"
}

clone_or_update() {
  # Idempotent: clone if missing, else fetch/pull current REF.
  if [[ -d "$ROOT/.git" ]]; then
    log "Updating existing clone at $ROOT (ref: $KEPRIX_REF)"
    git -C "$ROOT" fetch --tags --force origin "$KEPRIX_REF" 2>/dev/null \
      || git -C "$ROOT" fetch --tags --force origin || true
    if git -C "$ROOT" rev-parse --verify "refs/remotes/origin/$KEPRIX_REF" >/dev/null 2>&1; then
      git -C "$ROOT" checkout -B "$KEPRIX_REF" "origin/$KEPRIX_REF"
    elif git -C "$ROOT" rev-parse --verify "$KEPRIX_REF" >/dev/null 2>&1; then
      git -C "$ROOT" checkout "$KEPRIX_REF"
    else
      warn "Could not resolve ref $KEPRIX_REF; staying on current branch"
    fi
    git -C "$ROOT" pull --ff-only 2>/dev/null || true
    return 0
  fi

  if [[ -e "$ROOT" && ! -d "$ROOT/.git" ]]; then
    die "Path $ROOT exists but is not a git clone. Move it aside or set KEPRIX_HOME."
  fi

  log "Cloning $KEPRIX_REPO_URL (branch/tag: $KEPRIX_REF) into $ROOT"
  mkdir -p "$(dirname "$ROOT")"
  if ! git clone --branch "$KEPRIX_REF" --single-branch "$KEPRIX_REPO_URL" "$ROOT"; then
    echo ""
    echo "ERROR: git clone failed."
    echo "The Keprix GitHub repository must be publicly readable for stranger installs."
    echo "Anonymous clone/raw URLs currently fail closed until the owner publishes the repo."
    echo "See: docs/operations/public-github-checklist.md"
    echo "Until then, clone via SSH (or an allowed remote) and run:"
    echo "  bash scripts/install.sh"
    echo "from that checkout."
    exit 1
  fi
}

ensure_python_env() {
  local venv="$ROOT/.venv"
  if [[ ! -d "$ROOT" || ! -f "$ROOT/pyproject.toml" ]]; then
    die "Missing pyproject.toml under $ROOT"
  fi

  log "Creating Python env at $venv"
  if command -v uv >/dev/null 2>&1; then
    (cd "$ROOT" && uv venv "$venv")
    # shellcheck disable=SC1091
    source "$venv/bin/activate"
    (cd "$ROOT" && uv pip install -e ".[tui]")
  else
    if ! command -v "$PYTHON" >/dev/null 2>&1; then
      die "python3 not found. Install Python 3.11+ and re-run."
    fi
    "$PYTHON" -m venv "$venv"
    # shellcheck disable=SC1091
    source "$venv/bin/activate"
    pip install -U pip wheel
    (cd "$ROOT" && pip install -e ".[tui]")
  fi
}

link_keprix_bin() {
  local venv_bin="$ROOT/.venv/bin/keprix"
  local target="$BIN_DIR/keprix"

  mkdir -p "$BIN_DIR"
  if [[ ! -x "$venv_bin" ]]; then
    warn "keprix entry point missing at $venv_bin after install"
    return 1
  fi

  if [[ -L "$target" || -f "$target" ]]; then
    rm -f "$target"
  fi
  ln -s "$venv_bin" "$target"
  log "Linked $target -> $venv_bin"

  if ! path_has_bin_dir; then
    echo ""
    echo "Note: $BIN_DIR is not on your PATH."
    echo "Add it, for example:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo "Then run: hash -r   (or open a new shell)"
  fi
}

maybe_offer_docker() {
  local compose_file="$ROOT/docker/docker-compose.yml"
  local answer="n"

  if [[ "$KEPRIX_INSTALL_DOCKER" != "1" ]]; then
    return 0
  fi

  if [[ ! -f "$compose_file" ]]; then
    warn "Compose file not found at $compose_file; skipping Docker"
    return 0
  fi

  if ! command -v docker >/dev/null 2>&1; then
    warn "Docker not found; CLI install succeeded without Compose."
    echo "Install Docker later if you want the full stack:"
    echo "  https://docs.docker.com/engine/install/"
    return 0
  fi

  if ! docker compose version >/dev/null 2>&1; then
    warn "docker compose not available; skipping Compose start"
    return 0
  fi

  if [[ "$KEPRIX_NONINTERACTIVE" = "1" ]]; then
    log "KEPRIX_INSTALL_DOCKER=1 (noninteractive): starting Compose"
    (cd "$ROOT" && docker compose -f docker/docker-compose.yml up -d --build) || \
      warn "Compose start failed; CLI remains installed"
    return 0
  fi

  # Interactive: offer only when docker is present.
  if [[ -t 0 ]]; then
    read -r -p "Start Docker Compose full stack now? [y/N] " answer || answer="n"
  else
    answer="n"
    log "No TTY; skipping interactive Docker offer (set KEPRIX_INSTALL_DOCKER=1 with NONINTERACTIVE to force)"
  fi

  if [[ "$answer" =~ ^[Yy]$ ]]; then
    log "Starting Docker Compose"
    (cd "$ROOT" && docker compose -f docker/docker-compose.yml up -d --build) || \
      warn "Compose start failed; CLI remains installed"
  fi
}

write_state_file() {
  local installed_at
  installed_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date)"
  mkdir -p "$KEPRIX_HOME"
  cat > "$STATE_FILE" <<STATE
{
  "installed_at": "$installed_at",
  "root": "$ROOT",
  "ref": "$KEPRIX_REF",
  "mode": "$MODE",
  "keprix_home": "$KEPRIX_HOME"
}
STATE
  log "Wrote $STATE_FILE"
}

print_next_steps() {
  local setup_hint="keprix setup"
  if ! command -v keprix >/dev/null 2>&1 && [[ ! -x "$BIN_DIR/keprix" ]]; then
    setup_hint="python scripts/wizard.py  # via $ROOT/.venv/bin/python"
  elif [[ -x "$ROOT/.venv/bin/keprix" ]]; then
    if ! "$ROOT/.venv/bin/keprix" setup --help >/dev/null 2>&1; then
      setup_hint="$ROOT/.venv/bin/python $ROOT/scripts/wizard.py"
    fi
  fi

  echo ""
  echo "Keprix CLI install complete."
  echo ""
  echo "Next steps:"
  echo "  1. Ensure PATH includes ~/.local/bin, then: hash -r"
  echo "     (or open a new shell)"
  echo "  2. keprix --version"
  echo "  3. $setup_hint"
  echo "  4. keprix tui"
  echo ""
  echo "Docker Compose is optional and not required for CLI/TUI."
  echo "Data/config home: $KEPRIX_HOME"
  echo "Code root:        $ROOT"
}

main() {
  local os
  os="$(detect_os)"
  log "Keprix installer (OS: $os)"

  if [[ "$os" == "unknown" ]]; then
    warn "Unsupported or unrecognized OS ($(uname -s 2>/dev/null || echo unknown))."
    echo "Keprix supports Linux, macOS, and WSL2."
    echo "Native Windows is not claimed; use WSL2 and re-run this installer inside Linux."
    exit 1
  fi

  resolve_root_and_mode
  log "Mode: $MODE"
  log "KEPRIX_HOME: $KEPRIX_HOME"
  log "ROOT: $ROOT"

  if [[ "$KEPRIX_DRY_RUN" = "1" ]]; then
    print_dry_run
    exit 0
  fi

  ensure_home_layout

  if [[ "$MODE" == "piped" ]]; then
    clone_or_update
  else
    log "Checkout mode: using existing repo at $ROOT"
  fi

  ensure_python_env
  link_keprix_bin
  write_state_file

  if [[ "$KEPRIX_NONINTERACTIVE" = "1" ]]; then
    log "KEPRIX_NONINTERACTIVE=1: skipping wizard prompts"
  else
    log "Run setup when ready: keprix setup"
    log "(or: $ROOT/.venv/bin/python $ROOT/scripts/wizard.py)"
  fi

  maybe_offer_docker
  print_next_steps
}

main "$@"
