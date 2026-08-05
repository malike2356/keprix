"""ToolSequenceGuard: multi-stage attack chain detection for tool calls.

A single tool call is often benign. A sequence of tool calls can reveal
an attack in progress. This guard maintains a rolling window of tool calls
per session and detects known attack chains.

Attack chains detected:
  - Read-then-exfiltrate: read a file containing credentials then make
    an outbound HTTP request (data exfiltration pattern)
  - Probe-then-escalate: probe a path, then attempt privilege escalation
  - Enumeration burst: rapid file/dir listing (>10 in 60s, recon pattern)
  - Pivot chain: list processes -> find service -> write to service config
  - Code-and-run: write a file, then immediately execute it
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum


class AttackChain(str, Enum):
    READ_THEN_EXFILTRATE = "read_then_exfiltrate"
    PROBE_THEN_ESCALATE = "probe_then_escalate"
    ENUMERATION_BURST = "enumeration_burst"
    PIVOT_CHAIN = "pivot_chain"
    CODE_AND_RUN = "code_and_run"


@dataclass
class ToolCall:
    tool_name: str
    args: dict
    timestamp: float = field(default_factory=time.time)


@dataclass
class SequenceAlert:
    chain: AttackChain
    confidence: float
    tool_calls: list[ToolCall]
    message: str


_READ_TOOLS = frozenset({"read_file", "cat_file", "view_file", "get_file"})
_WRITE_TOOLS = frozenset({"write_file", "create_file", "append_file"})
_EXEC_TOOLS = frozenset({"terminal", "bash", "run_command", "execute"})
_NET_TOOLS = frozenset({"web_request", "http_request", "fetch_url", "curl"})
_LIST_TOOLS = frozenset({"list_dir", "ls", "find_files", "glob"})
_PRIV_PATTERNS = {"sudo", "su ", "chmod", "chown", "setuid", "pkexec"}

WINDOW_SECONDS = 60
ENUMERATION_THRESHOLD = 10


class ToolSequenceGuard:
    """Per-session rolling window tool sequence analyzer.

    Usage::

        guard = ToolSequenceGuard(session_id="sess-1")
        alert = guard.record("read_file", {"path": "/etc/passwd"})
        if alert:
            raise SecurityAlert(alert.chain)
    """

    def __init__(self, session_id: str, window_seconds: float = WINDOW_SECONDS) -> None:
        self.session_id = session_id
        self._window_seconds = window_seconds
        self._calls: deque[ToolCall] = deque()

    def record(self, tool_name: str, args: dict | None = None) -> SequenceAlert | None:
        """Record a tool call and check for attack chain patterns.

        Returns a SequenceAlert if a chain is detected, else None.
        """
        now = time.time()
        call = ToolCall(tool_name=tool_name, args=args or {}, timestamp=now)
        self._calls.append(call)
        self._evict_old(now)

        return (
            self._check_read_then_exfiltrate()
            or self._check_code_and_run()
            or self._check_enumeration_burst()
            or self._check_probe_then_escalate()
            or self._check_pivot_chain()
        )

    def _evict_old(self, now: float) -> None:
        while self._calls and now - self._calls[0].timestamp > self._window_seconds:
            self._calls.popleft()

    def _window(self) -> list[ToolCall]:
        return list(self._calls)

    def _check_read_then_exfiltrate(self) -> SequenceAlert | None:
        calls = self._window()
        read_calls = [c for c in calls if c.tool_name in _READ_TOOLS]
        net_calls = [c for c in calls if c.tool_name in _NET_TOOLS]
        if read_calls and net_calls:
            last_read = max(read_calls, key=lambda c: c.timestamp)
            first_net = min(net_calls, key=lambda c: c.timestamp)
            if first_net.timestamp > last_read.timestamp:
                return SequenceAlert(
                    chain=AttackChain.READ_THEN_EXFILTRATE,
                    confidence=0.85,
                    tool_calls=[last_read, first_net],
                    message=(
                        f"File read ({last_read.tool_name}) followed by "
                        f"outbound request ({first_net.tool_name}) within {self._window_seconds}s."
                    ),
                )
        return None

    def _check_code_and_run(self) -> SequenceAlert | None:
        calls = self._window()
        for i, call in enumerate(calls):
            if call.tool_name not in _WRITE_TOOLS:
                continue
            for later in calls[i + 1:]:
                if later.tool_name in _EXEC_TOOLS:
                    written_path = str(call.args.get("path", ""))
                    cmd = str(later.args.get("command", "") or later.args.get("cmd", ""))
                    if written_path and (written_path in cmd or written_path.split("/")[-1] in cmd):
                        return SequenceAlert(
                            chain=AttackChain.CODE_AND_RUN,
                            confidence=0.90,
                            tool_calls=[call, later],
                            message=(
                                f"File written ({written_path}) then executed "
                                f"via {later.tool_name} within {self._window_seconds}s."
                            ),
                        )
        return None

    def _check_enumeration_burst(self) -> SequenceAlert | None:
        calls = self._window()
        list_calls = [c for c in calls if c.tool_name in _LIST_TOOLS]
        if len(list_calls) >= ENUMERATION_THRESHOLD:
            return SequenceAlert(
                chain=AttackChain.ENUMERATION_BURST,
                confidence=0.70,
                tool_calls=list_calls[:5],
                message=(
                    f"{len(list_calls)} directory listing calls within "
                    f"{self._window_seconds}s — recon pattern detected."
                ),
            )
        return None

    def _check_probe_then_escalate(self) -> SequenceAlert | None:
        calls = self._window()
        read_or_list = [c for c in calls if c.tool_name in (_READ_TOOLS | _LIST_TOOLS)]
        exec_calls = [c for c in calls if c.tool_name in _EXEC_TOOLS]
        for exec_call in exec_calls:
            cmd = str(exec_call.args.get("command", ""))
            if any(p in cmd for p in _PRIV_PATTERNS):
                prior_probes = [c for c in read_or_list if c.timestamp < exec_call.timestamp]
                if prior_probes:
                    return SequenceAlert(
                        chain=AttackChain.PROBE_THEN_ESCALATE,
                        confidence=0.80,
                        tool_calls=[prior_probes[-1], exec_call],
                        message=(
                            f"File probe followed by privilege escalation attempt "
                            f"({exec_call.tool_name}: {cmd[:80]})."
                        ),
                    )
        return None

    def _check_pivot_chain(self) -> SequenceAlert | None:
        calls = self._window()
        if len(calls) < 3:
            return None
        has_list = any(c.tool_name in _LIST_TOOLS for c in calls)
        has_read = any(c.tool_name in _READ_TOOLS for c in calls)
        has_write = any(c.tool_name in _WRITE_TOOLS for c in calls)
        if has_list and has_read and has_write:
            suspects = [c for c in calls if c.tool_name in (_LIST_TOOLS | _READ_TOOLS | _WRITE_TOOLS)]
            return SequenceAlert(
                chain=AttackChain.PIVOT_CHAIN,
                confidence=0.60,
                tool_calls=suspects[:4],
                message=(
                    "Directory enumeration + file read + file write sequence "
                    "within window: possible pivot chain."
                ),
            )
        return None

    def reset(self) -> None:
        self._calls.clear()
