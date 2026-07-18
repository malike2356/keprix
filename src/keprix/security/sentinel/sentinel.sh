#!/usr/bin/env bash
# sentinel.sh - MVP kernel-level protection for Scout (safe defaults).
# Usage: sudo SENTINEL_ENFORCE=1 ./sentinel.sh <agent_pid>
# Without SENTINEL_ENFORCE=1 this script only prints planned actions (dry-run).
# Must run before or alongside the agent. No emojis.

set -euo pipefail

AGENT_PID="${1:-}"
if [[ -z "${AGENT_PID}" ]]; then
  echo "Usage: $0 <agent_pid>" >&2
  exit 2
fi

if [[ ! -d "/proc/${AGENT_PID}" ]]; then
  echo "ERROR: process ${AGENT_PID} not found" >&2
  exit 1
fi

AGENT_UID="$(stat -c '%u' "/proc/${AGENT_PID}")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Prefer package-relative security dir (sentinel/ is under security/)
SCOUT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENFORCE="${SENTINEL_ENFORCE:-0}"
ALLOW_KILL="${SENTINEL_ALLOW_KILL:-0}"
CGROUP="${SENTINEL_CGROUP_ROOT:-/sys/fs/cgroup/scout}"

echo "Sentinel starting: PID ${AGENT_PID} (UID ${AGENT_UID}) enforce=${ENFORCE}"

run_or_echo() {
  if [[ "${ENFORCE}" == "1" ]]; then
    "$@"
  else
    echo "  dry-run: $*"
  fi
}

echo "  Locking Scout security files (selected .py only)..."
for f in scout_control.py scout_listener.py auto_response.py sentinel_client.py; do
  if [[ -f "${SCOUT_DIR}/${f}" ]]; then
    run_or_echo chattr +i "${SCOUT_DIR}/${f}"
  fi
done

echo "  Applying cgroup limits..."
if [[ "${ENFORCE}" == "1" ]]; then
  if mkdir -p "${CGROUP}" 2>/dev/null; then
    echo $((4 * 1024 * 1024 * 1024)) > "${CGROUP}/memory.max" || echo "  WARNING: memory.max failed"
    echo 50 > "${CGROUP}/pids.max" || echo "  WARNING: pids.max failed"
    echo "50000 100000" > "${CGROUP}/cpu.max" || echo "  WARNING: cpu.max failed"
    echo "${AGENT_PID}" > "${CGROUP}/cgroup.procs" || echo "  WARNING: cgroup.procs failed"
  else
    echo "  WARNING: cgroup unavailable; continuing"
  fi
else
  echo "  dry-run: mkdir -p ${CGROUP} and write memory/pids/cpu limits for PID ${AGENT_PID}"
fi

echo "  Blocking agent network egress..."
run_or_echo iptables -A OUTPUT -m owner --uid-owner "${AGENT_UID}" -j DROP

echo "  Monitoring agent..."
while kill -0 "${AGENT_PID}" 2>/dev/null; do
  sleep 5
done

echo "Agent exited. Cleaning up..."
if [[ "${ENFORCE}" == "1" ]]; then
  iptables -D OUTPUT -m owner --uid-owner "${AGENT_UID}" -j DROP 2>/dev/null || true
  for f in scout_control.py scout_listener.py auto_response.py sentinel_client.py; do
    if [[ -f "${SCOUT_DIR}/${f}" ]]; then
      chattr -i "${SCOUT_DIR}/${f}" 2>/dev/null || true
    fi
  done
  rmdir "${CGROUP}" 2>/dev/null || true
else
  echo "  dry-run: would remove iptables rule, unlock files, and remove cgroup"
fi

echo "Sentinel shutdown complete (allow_kill was ${ALLOW_KILL})."
