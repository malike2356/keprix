# keprix - Prompt 26: keprix Agent Hardening

**Output directory:** `/opt/lampp/htdocs/verlox/keprix/keprix/`
**Depends on:** Prompt 28 (keprix Agent - self-coding capability), Prompt 02 (Security Foundation)
**Augments:** Prompt 28 - does NOT replace it. Apply these changes ON TOP of the base
keprix Agent built in Prompt 28.

---

## Objective

The keprix Agent synthesises new Python tools when keprix hits a capability gap.
This is the most powerful and most dangerous feature in the system. A compromised or
manipulated tool-synthesis pipeline can turn the agent's self-coding ability into an
arbitrary code execution vector for an attacker. This prompt hardens every stage of
that pipeline.

---

## Stage 1: AST Analyser Hardening

The AST analyser in Prompt 28 checks generated code before sandbox execution.
Expand the blocked node set to cover all known Python sandbox escape vectors.

### File: `keprix/keprix_agent/ast_analyser.py` (add to existing BLOCKED sets)

```python
import ast
from typing import Any

# Every symbol in this set causes immediate rejection
BLOCKED_IMPORTS: frozenset[str] = frozenset({
    # Dynamic import / introspection bypasses
    "importlib",
    "importlib.util",
    "importlib.machinery",
    "importlib.abc",
    "__import__",
    "builtins",
    "__builtins__",
    "ctypes",
    "cffi",
    "cython",

    # Network primitives (tool should use httpx via the egress filter, not raw sockets)
    "socket",
    "ssl",
    "asyncio.selector_events",
    "asyncio.proactor_events",
    "_ssl",
    "_socket",

    # OS-level shell access
    "subprocess",
    "multiprocessing",
    "threading",
    "concurrent.futures",
    "asyncio.subprocess",
    "_thread",

    # Struct/buffer manipulation (ctypes-like bypass vectors)
    "struct",
    "mmap",
    "array",

    # Unsafe serialisation
    "pickle",
    "shelve",
    "marshal",

    # Compiler/eval
    "code",
    "codeop",
    "compileall",
    "dis",
    "py_compile",
})

BLOCKED_CALLS: frozenset[str] = frozenset({
    "eval",
    "exec",
    "compile",
    "open",          # use pathlib.Path.read_text via the approved I/O helper
    "__import__",
    "getattr",       # only if used with dynamic string argument (see analyser logic)
    "setattr",
    "delattr",
    "vars",
    "locals",
    "globals",
    "dir",
    "type",          # when used to create dynamic classes
    "memoryview",
})

BLOCKED_ATTRIBUTES: frozenset[str] = frozenset({
    "__class__",
    "__bases__",
    "__subclasses__",
    "__mro__",
    "__init_subclass__",
    "__dict__",
    "__code__",
    "__globals__",
    "__builtins__",
    "__loader__",
    "__spec__",
    "f_locals",
    "f_globals",
    "f_builtins",
    "gi_frame",       # generator frame access
    "cr_frame",       # coroutine frame access
})

class AstAnalyser(ast.NodeVisitor):
    def __init__(self) -> None:
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name in BLOCKED_IMPORTS or any(
                alias.name.startswith(b + ".") for b in BLOCKED_IMPORTS
            ):
                self.violations.append(f"Blocked import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if module in BLOCKED_IMPORTS or any(
            module.startswith(b + ".") for b in BLOCKED_IMPORTS
        ):
            self.violations.append(f"Blocked import from: {module}")
        # Also block: from builtins import eval
        for alias in node.names:
            if alias.name in BLOCKED_CALLS:
                self.violations.append(f"Blocked import of: {alias.name} from {module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Direct call: eval(...), exec(...), __import__(...)
        if isinstance(node.func, ast.Name) and node.func.id in BLOCKED_CALLS:
            self.violations.append(f"Blocked call: {node.func.id}()")
        # Attribute call: obj.something(...) - check for subprocess.Popen([list])
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in {"Popen", "call", "run", "check_output", "check_call"}:
                self.violations.append(f"Blocked call: .{node.func.attr}()")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in BLOCKED_ATTRIBUTES:
            self.violations.append(f"Blocked attribute access: .{node.attr}")
        self.generic_visit(node)

def analyse(source_code: str) -> list[str]:
    """Returns list of violations. Empty list means safe."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return [f"SyntaxError: {e}"]
    analyser = AstAnalyser()
    analyser.visit(tree)
    return analyser.violations
```

---

## Stage 2: Docker Sandbox Hardening - Custom Seccomp Profile

The default Docker seccomp profile allows `socket()`, `connect()`, `bind()`, and
`sendto()` syscalls. A generated tool can use these to establish direct network
connections that bypass the Python egress filter.

### File: `keprix/keprix_agent/sandbox/seccomp-tool.json`

```json
{
  "defaultAction": "SCMP_ACT_ALLOW",
  "architectures": ["SCMP_ARCH_X86_64", "SCMP_ARCH_AARCH64"],
  "syscalls": [
    {
      "names": [
        "socket",
        "connect",
        "bind",
        "sendto",
        "sendmsg",
        "sendmmsg",
        "recvfrom",
        "recvmsg",
        "recvmmsg",
        "accept",
        "accept4",
        "listen",
        "getsockopt",
        "setsockopt",
        "socketpair",
        "shutdown",
        "getpeername",
        "getsockname"
      ],
      "action": "SCMP_ACT_ERRNO",
      "errnoRet": 1
    },
    {
      "names": ["ptrace", "process_vm_readv", "process_vm_writev"],
      "action": "SCMP_ACT_ERRNO",
      "errnoRet": 1
    },
    {
      "names": ["mount", "umount2", "pivot_root", "chroot"],
      "action": "SCMP_ACT_ERRNO",
      "errnoRet": 1
    }
  ]
}
```

### File: `keprix/keprix_agent/sandbox/runner.py` (update Docker run command)

```python
import subprocess
import json
from pathlib import Path

SECCOMP_PROFILE = Path(__file__).parent / "seccomp-tool.json"

def run_in_sandbox(code: str, timeout_seconds: int = 30) -> tuple[bool, str, str]:
    """
    Returns (success, stdout, stderr).
    Network is completely blocked via seccomp. Read-only filesystem. 256MB RAM.
    """
    result = subprocess.run(
        [
            "docker", "run",
            "--rm",
            "--network=none",
            "--memory=256m",
            "--memory-swap=256m",
            "--cpus=0.5",
            "--read-only",
            "--tmpfs", "/tmp:size=32m,noexec",
            f"--security-opt=seccomp={SECCOMP_PROFILE}",
            "--cap-drop=ALL",
            "--no-new-privileges",
            "keprix-sandbox:latest",
            "python3", "-c", code,
        ],
        capture_output=True,
        text=True,
        timeout=timeout_seconds + 5,  # outer timeout is slightly longer than container timeout
    )
    success = result.returncode == 0
    return success, result.stdout, result.stderr
```

---

## Stage 3: Mandatory 2-Channel Approval

No generated tool goes live without approval from two independent channels.
This prevents a single compromised channel from approving a malicious tool.

### File: `keprix/keprix_agent/approval_gate.py`

```python
import asyncio
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Awaitable, Callable

@dataclass
class PendingApproval:
    request_id: str
    tool_name: str
    tool_code: str
    submitted_at: float
    channel_approvals: dict[str, bool] = field(default_factory=dict)
    channel_rejections: dict[str, str] = field(default_factory=dict)
    expires_at: float = field(default_factory=lambda: time.time() + 3600)

    def is_approved(self, required_channels: frozenset[str]) -> bool:
        return required_channels.issubset(self.channel_approvals.keys())

    def is_rejected(self) -> bool:
        return len(self.channel_rejections) > 0

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

# Required channels for approval. Both must approve before a tool is installed.
# Add more channels to require broader consensus (e.g., email + telegram + web).
REQUIRED_CHANNELS: frozenset[str] = frozenset({"web_ui", "telegram"})

_PENDING: dict[str, PendingApproval] = {}

async def submit_for_approval(
    tool_name: str,
    tool_code: str,
    notifier: Callable[[PendingApproval], Awaitable[None]],
) -> str:
    request_id = str(uuid.uuid4())
    approval = PendingApproval(
        request_id=request_id,
        tool_name=tool_name,
        tool_code=tool_code,
        submitted_at=time.time(),
    )
    _PENDING[request_id] = approval
    await notifier(approval)
    return request_id

async def record_decision(request_id: str, channel: str, approved: bool, reason: str = "") -> None:
    approval = _PENDING.get(request_id)
    if not approval:
        raise ValueError(f"No pending approval for request {request_id}")
    if approved:
        approval.channel_approvals[channel] = True
    else:
        approval.channel_rejections[channel] = reason or "rejected"

async def wait_for_approval(request_id: str, timeout: float = 3600.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        approval = _PENDING.get(request_id)
        if not approval:
            return False
        if approval.is_rejected():
            del _PENDING[request_id]
            return False
        if approval.is_approved(REQUIRED_CHANNELS):
            del _PENDING[request_id]
            return True
        if approval.is_expired():
            del _PENDING[request_id]
            return False
        await asyncio.sleep(5)
    return False
```

---

## Stage 4: Tool Code Signing

All approved tools are signed with a project-level Ed25519 key before installation.
The agent verifies the signature on every load. A tool with no valid signature is
never loaded, even if it is present in the tools directory.

### File: `keprix/keprix_agent/tool_signer.py`

```python
import hashlib
import hmac
import json
import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat, PrivateFormat, NoEncryption,
    load_pem_private_key, load_pem_public_key,
)
from cryptography.exceptions import InvalidSignature

_SIGNING_KEY_PATH = Path(os.environ.get("keprix_TOOL_SIGNING_KEY", "/secrets/tool-signing-key.pem"))
_VERIFY_KEY_PATH = Path(os.environ.get("keprix_TOOL_VERIFY_KEY", "/secrets/tool-verify-key.pem"))

def sign_tool(tool_name: str, tool_code: str, metadata: dict) -> str:
    """Returns hex signature string."""
    private_key = load_pem_private_key(_SIGNING_KEY_PATH.read_bytes(), password=None)
    payload = json.dumps({"name": tool_name, "code": tool_code, "meta": metadata}, sort_keys=True).encode()
    sig_bytes = private_key.sign(payload)
    return sig_bytes.hex()

def verify_tool(tool_name: str, tool_code: str, metadata: dict, signature_hex: str) -> bool:
    try:
        public_key = load_pem_public_key(_VERIFY_KEY_PATH.read_bytes())
        payload = json.dumps({"name": tool_name, "code": tool_code, "meta": metadata}, sort_keys=True).encode()
        public_key.verify(bytes.fromhex(signature_hex), payload)
        return True
    except (InvalidSignature, Exception):
        return False
```

---

## Stage 5: Rollback Mechanism

If an installed tool causes an error rate spike (>10% of calls in 5 minutes), it
is automatically quarantined and rolled back.

### File: `keprix/keprix_agent/tool_health.py`

```python
import time
from collections import deque
from typing import Deque

class ToolHealthMonitor:
    def __init__(self, error_threshold: float = 0.10, window_seconds: int = 300):
        self.error_threshold = error_threshold
        self.window_seconds = window_seconds
        self._calls: Deque[tuple[float, bool]] = deque()

    def record(self, success: bool) -> None:
        now = time.time()
        self._calls.append((now, success))
        cutoff = now - self.window_seconds
        while self._calls and self._calls[0][0] < cutoff:
            self._calls.popleft()

    def error_rate(self) -> float:
        if not self._calls:
            return 0.0
        errors = sum(1 for _, ok in self._calls if not ok)
        return errors / len(self._calls)

    def should_quarantine(self) -> bool:
        return len(self._calls) >= 10 and self.error_rate() > self.error_threshold
```

Usage in the tool registry:
```python
if health_monitor.should_quarantine():
    await quarantine_tool(tool_name)
    await report_security_event("tool_quarantined", "high", {
        "tool": tool_name,
        "error_rate": health_monitor.error_rate(),
    })
```

---

## Namespace Isolation for Generated Tools

All generated tools are installed in a dedicated module namespace and are NEVER
allowed to import from keprix's own codebase:

```python
# keprix/keprix_agent/tool_installer.py
_GENERATED_TOOL_NAMESPACE = "keprix.generated_tools"
_FORBIDDEN_INTERNAL_PREFIXES = ("keprix.", "keprix_sdk.")

def validate_tool_imports(tool_code: str) -> list[str]:
    """Reject tools that try to import keprix internals."""
    violations = []
    for prefix in _FORBIDDEN_INTERNAL_PREFIXES:
        if prefix in tool_code:
            violations.append(f"Generated tool attempts to import internal module: {prefix}")
    return violations
```

---

## Acceptance Criteria

- `analyse("import importlib; importlib.import_module('os')")` returns at least 1 violation.
- `analyse("eval('__import__(os)')")` returns at least 1 violation.
- `analyse("import subprocess; subprocess.Popen(['ls'])")` returns at least 1 violation.
- Docker sandbox runs with `--security-opt=seccomp=seccomp-tool.json --network=none`.
- Attempting `socket.connect()` inside the sandbox fails with `OSError: [Errno 1]`.
- A tool submitted for approval cannot be installed until BOTH `web_ui` and `telegram`
  channels have recorded an approval for the same `request_id`.
- A tool with a modified source file (signature mismatch) is rejected on load.
- A tool with error rate >10% over 5 minutes is quarantined automatically.
- Generated tools cannot import `keprix.*` internal modules.
