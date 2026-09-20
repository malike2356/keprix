#!/usr/bin/env bash
# Keprix installer (CLI first, Hermes layout).
#
# Pipe mode (stranger UX):
#   curl -fsSL https://keprixai.com/install.sh | bash
# GitHub raw still works:
#   curl -fsSL https://raw.githubusercontent.com/malike2356/keprix/main/scripts/install.sh | bash
# When piped, BASH_SOURCE does not point at a checkout. The script clones/updates
# into ${KEPRIX_HOME:-$HOME/.keprix}/keprix and installs there.
#
# Checkout mode (contributors):
#   bash scripts/install.sh
# If this file lives in a real repo (../pyproject.toml present), install into that
# repo's .venv and symlink keprix onto PATH.
#
# After install: reload the shell, type `keprix`. If no provider key exists,
# that command offers setup, then starts chatting. Dashboard is optional.
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
  # Hermes update path: stash local dirt, clear unmerged index, never abort
  # the whole install because a previous checkout was messy.

  # Interrupted clone: .git exists but HEAD is missing. Move aside and reclone.
  if [[ -d "$ROOT/.git" ]] && ! git -C "$ROOT" rev-parse --verify HEAD >/dev/null 2>&1; then
    local backup_dir
    backup_dir="${ROOT}.broken-$(date -u +%Y%m%d-%H%M%S)"
    warn "Existing checkout at $ROOT has no commits (interrupted clone)."
    warn "Moving it aside to $backup_dir before re-cloning."
    mv "$ROOT" "$backup_dir"
  fi

  if [[ -d "$ROOT/.git" ]]; then
    log "Updating existing clone at $ROOT (ref: $KEPRIX_REF)"
    local autostash_ref=""
    if [[ -n "$(git -C "$ROOT" status --porcelain 2>/dev/null || true)" ]]; then
      if [[ -n "$(git -C "$ROOT" ls-files --unmerged 2>/dev/null || true)" ]]; then
        log "Clearing unmerged index entries from a previous conflict..."
        git -C "$ROOT" reset -q || true
      fi
      local stash_name
      stash_name="keprix-install-autostash-$(date -u +%Y%m%d-%H%M%S)"
      log "Local changes detected, stashing before update..."
      if git -C "$ROOT" stash push --include-untracked -m "$stash_name"; then
        autostash_ref="stash@{0}"
      fi
    fi

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

    if [[ -n "$autostash_ref" ]]; then
      log "Restoring local changes stashed before update..."
      if git -C "$ROOT" stash apply "$autostash_ref"; then
        git -C "$ROOT" stash drop "$autostash_ref" >/dev/null 2>&1 || true
        warn "Local changes were restored on top of the updated codebase."
        warn "Review git status in $ROOT if Keprix behaves unexpectedly."
      else
        warn "Update succeeded, but restoring local changes failed."
        warn "Your changes are in git stash. Restore with: git -C $ROOT stash apply $autostash_ref"
      fi
    fi
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
    echo "Until then, clone via SSH (or an allowed remote) and run:"
    echo "  bash scripts/install.sh"
    echo "from that checkout."
    exit 1
  fi
}

ensure_python_bin() {
  # Prefer an explicit PYTHON=, then 3.12/3.11, then python3 if it is new enough.
  local candidates=()
  local bin ver major minor
  if [[ -n "${PYTHON:-}" && "$PYTHON" != "python3" ]]; then
    candidates+=("$PYTHON")
  fi
  candidates+=(python3.12 python3.11 python3)
  for bin in "${candidates[@]}"; do
    if ! command -v "$bin" >/dev/null 2>&1; then
      continue
    fi
    ver="$("$bin" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true)"
    major="${ver%%.*}"
    minor="${ver#*.}"
    if [[ "$major" =~ ^[0-9]+$ && "$minor" =~ ^[0-9]+$ ]]; then
      if (( major > 3 || (major == 3 && minor >= 11 && minor < 13) )); then
        PYTHON="$bin"
        log "Using Python $ver ($bin)"
        return 0
      fi
    fi
  done
  die "Keprix needs Python 3.11 or 3.12. Found none on PATH. Install python3.11+ and re-run (Ubuntu 22.04: sudo apt install python3.11 python3.11-venv)."
}

ensure_python_env() {
  local venv="$ROOT/.venv"
  if [[ ! -d "$ROOT" || ! -f "$ROOT/pyproject.toml" ]]; then
    die "Missing pyproject.toml under $ROOT"
  fi

  ensure_python_bin

  if [[ -d "$venv" ]]; then
    log "Virtual environment already exists, recreating..."
    rm -rf "$venv"
  fi

  log "Creating Python env at $venv"
  if command -v uv >/dev/null 2>&1; then
    (cd "$ROOT" && uv venv --python "$PYTHON" "$venv")
    # shellcheck disable=SC1091
    source "$venv/bin/activate"
    (cd "$ROOT" && uv pip install -e ".[tui]")
  else
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
    echo "Note: $BIN_DIR is not on your PATH yet. The installer will add it to your shell config."
  fi
}

ensure_local_bin_on_path() {
  # Hermes copies ~/.local/bin into bashrc/zshrc/profile so `keprix` works
  # after `source ~/.bashrc` without the user editing PATH by hand.
  local path_line='export PATH="$HOME/.local/bin:$PATH"'
  local path_comment='# Keprix — ensure ~/.local/bin is on PATH'
  local login_shell
  local -a shell_configs=()
  local is_fish=false
  local fish_config="$HOME/.config/fish/config.fish"
  local cfg

  if [[ "$BIN_DIR" != "$HOME/.local/bin" ]]; then
    export PATH="$BIN_DIR:$PATH"
    return 0
  fi

  login_shell="$(basename "${SHELL:-/bin/bash}")"
  case "$login_shell" in
    zsh)
      [[ -f "$HOME/.zshrc" ]] && shell_configs+=("$HOME/.zshrc")
      [[ -f "$HOME/.zprofile" ]] && shell_configs+=("$HOME/.zprofile")
      if [[ ${#shell_configs[@]} -eq 0 ]]; then
        touch "$HOME/.zshrc"
        shell_configs+=("$HOME/.zshrc")
      fi
      ;;
    bash)
      [[ -f "$HOME/.bashrc" ]] && shell_configs+=("$HOME/.bashrc")
      [[ -f "$HOME/.bash_profile" ]] && shell_configs+=("$HOME/.bash_profile")
      if [[ ${#shell_configs[@]} -eq 0 ]]; then
        touch "$HOME/.bashrc"
        shell_configs+=("$HOME/.bashrc")
      fi
      ;;
    fish)
      is_fish=true
      mkdir -p "$(dirname "$fish_config")"
      touch "$fish_config"
      ;;
    *)
      [[ -f "$HOME/.bashrc" ]] && shell_configs+=("$HOME/.bashrc")
      [[ -f "$HOME/.zshrc" ]] && shell_configs+=("$HOME/.zshrc")
      ;;
  esac
  if [[ "$is_fish" != true && -f "$HOME/.profile" ]]; then
    shell_configs+=("$HOME/.profile")
  fi

  for cfg in "${shell_configs[@]}"; do
    if ! grep -v '^[[:space:]]*#' "$cfg" 2>/dev/null | grep -qE 'PATH=.*\.local/bin'; then
      echo "" >> "$cfg"
      echo "$path_comment" >> "$cfg"
      echo "$path_line" >> "$cfg"
      log "Added ~/.local/bin to PATH in $cfg"
    fi
  done

  if [[ "$is_fish" == true ]]; then
    if ! grep -q 'fish_add_path.*\.local/bin' "$fish_config" 2>/dev/null; then
      echo "" >> "$fish_config"
      echo "$path_comment" >> "$fish_config"
      echo 'fish_add_path "$HOME/.local/bin"' >> "$fish_config"
      log "Added ~/.local/bin to PATH in $fish_config"
    fi
  fi

  export PATH="$BIN_DIR:$PATH"
}

run_setup_wizard() {
  local keprix_bin="$ROOT/.venv/bin/keprix"

  if [[ "$KEPRIX_NONINTERACTIVE" = "1" ]]; then
    log "KEPRIX_NONINTERACTIVE=1: skipping setup wizard"
    return 0
  fi

  # Hermes: wizard reads /dev/tty so curl | bash can still prompt.
  if ! (: </dev/tty) 2>/dev/null; then
    log "Setup wizard skipped (no terminal available). After install, run: keprix"
    return 0
  fi

  if [[ ! -x "$keprix_bin" ]]; then
    warn "keprix binary missing; skip setup. After install, run: keprix"
    return 0
  fi

  echo ""
  log "Starting setup wizard (paste one provider key, or skip and add one later)..."
  echo ""
  "$keprix_bin" setup </dev/tty || warn "Setup wizard exited early. Run 'keprix' later to finish."
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
  local login_shell
  login_shell="$(basename "${SHELL:-/bin/bash}")"

  echo ""
  echo "Keprix install complete."
  echo ""
  echo "Reload your shell, then start chatting:"
  echo ""
  case "$login_shell" in
    zsh) echo "  source ~/.zshrc" ;;
    fish) echo "  source ~/.config/fish/config.fish" ;;
    *) echo "  source ~/.bashrc" ;;
  esac
  echo "  keprix"
  echo ""
  echo "If no API key is configured yet, keprix will offer setup in the same terminal."
  echo "Dashboard is optional: keprix dashboard"
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
  # Fail before clone when the host Python is too old (common on Ubuntu 22.04).
  ensure_python_bin

  if [[ "$MODE" == "piped" ]]; then
    clone_or_update
  else
    log "Checkout mode: using existing repo at $ROOT"
  fi

  ensure_python_env
  link_keprix_bin
  ensure_local_bin_on_path
  write_state_file
  run_setup_wizard
  maybe_offer_docker
  print_next_steps
}

main "$@"
