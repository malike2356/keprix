# Keprix Prompt: Production Hardening; Agent Runtime Don't Fall Apart

## Status: PENDING

## Source
Facebook Reel: "How to build an app that ACTUALLY works when users start using it"; SWErikCodes (82K views)
Applied to Keprix agent runtime architecture.

---

## Summary

Keprix is not a web app; it's an agent runtime that spawns sub-agents, executes tools, streams model responses, and manages files on disk. The failure modes are different: runaway agents burning API credits, tool loops spawning infinite processes, memory exhaustion from large contexts, and credential leakage through agent output. Hardening Keprix means constraining the agent, not just the API.

---

## The 7 Hardening Layers (Keprix Edition)

### 1. Agent Rate Limiting; Stop Runaway Agents Before They Burn Your Wallet

```
┌──────────────────────────────────────────────────────────┐
│              AGENT GOVERNOR                                │
│                                                          │
│  Per-session limits:                                      │
│  ┌────────────────────────────────────────────────────┐  │
│  │ • Max tool calls:         50 per turn               │  │
│  │ • Max turns:              100 per session           │  │
│  │ • Max token budget:       $5 per session            │  │
│  │ • Max sub-agents:         10 concurrent             │  │
│  │ • Max terminal commands:  30 per session            │  │
│  │ • Max file writes:        20 per turn               │  │
│  │ • Cooldown on violation:  60 seconds                │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Per-product/day limits:                                  │
│  ┌────────────────────────────────────────────────────┐  │
│  │ • Carina:  $50/day total token budget               │  │
│  │ • Aiva:    $30/day total token budget               │  │
│  │ • Mutant:  $20/day total token budget               │  │
│  │ • Hard cap: STOP agent, notify operator             │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

```python
# keprix/src/keprix/security/agent_governor.py
"""Rate limits and budgets for agent sessions. Prevents runaway spending."""

import time, threading
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class SessionLimits:
    max_tool_calls_per_turn: int = 50
    max_turns: int = 100
    max_token_budget_usd: float = 5.0
    max_sub_agents: int = 10
    max_terminal_commands: int = 30
    max_file_writes_per_turn: int = 20
    cooldown_seconds: int = 60

@dataclass
class ProductDayLimits:
    max_token_budget_usd: float = 50.0
    cooldown_minutes: int = 30

PRODUCT_LIMITS = {
    "carina": ProductDayLimits(max_token_budget_usd=50.0),
    "aiva":   ProductDayLimits(max_token_budget_usd=30.0),
    "mutant": ProductDayLimits(max_token_budget_usd=20.0),
    "keprix": ProductDayLimits(max_token_budget_usd=10.0),
}

class AgentGovernor:
    """Tracks and enforces limits per session and per product."""
    
    def __init__(self):
        self._sessions: dict[str, dict] = defaultdict(lambda: {
            'tool_calls_this_turn': 0,
            'total_turns': 0,
            'total_tokens_usd': 0.0,
            'terminal_commands': 0,
            'file_writes_this_turn': 0,
            'violations': 0,
            'cooldown_until': 0,
        })
        self._product_day: dict[str, dict] = defaultdict(lambda: {
            'tokens_usd_today': 0.0,
            'day_start': time.time(),
        })
        self._lock = threading.Lock()
    
    def check_tool_call(self, session_id: str, product_id: str) -> bool:
        """Returns True if tool call is allowed."""
        with self._lock:
            s = self._sessions[session_id]
            
            # Check cooldown
            if time.time() < s['cooldown_until']:
                return False
            
            # Check turn limit
            s['tool_calls_this_turn'] += 1
            if s['tool_calls_this_turn'] > SessionLimits().max_tool_calls_per_turn:
                self._apply_violation(session_id)
                return False
            
            return True
    
    def check_token_spend(self, session_id: str, product_id: str, cost_usd: float) -> bool:
        """Returns True if spend is within limits."""
        with self._lock:
            s = self._sessions[session_id]
            p = self._product_day[product_id]
            
            # Reset day counter if new day
            if time.time() - p['day_start'] > 86400:
                p['tokens_usd_today'] = 0.0
                p['day_start'] = time.time()
            
            # Check session budget
            s['total_tokens_usd'] += cost_usd
            if s['total_tokens_usd'] > SessionLimits().max_token_budget_usd:
                return False
            
            # Check product daily budget
            p['tokens_usd_today'] += cost_usd
            limit = PRODUCT_LIMITS.get(product_id, ProductDayLimits()).max_token_budget_usd
            if p['tokens_usd_today'] > limit:
                return False
            
            return True
    
    def _apply_violation(self, session_id: str):
        s = self._sessions[session_id]
        s['violations'] += 1
        s['cooldown_until'] = time.time() + SessionLimits().cooldown_seconds
        s['tool_calls_this_turn'] = 0

# Global instance
governor = AgentGovernor()

# Hook into tool dispatch
def tool_dispatch_guard(tool_name: str, session_id: str, product_id: str):
    if session_id and not governor.check_tool_call(session_id, product_id):
        raise ToolRateLimitedError(
            f"Tool '{tool_name}' blocked: session rate limit reached. "
            f"Cooldown active."
        )
```

### 2. API Key Vault; Never Expose Keys in Config Files

```
┌──────────────────────────────────────────────────────────┐
│              CREDENTIAL VAULT                              │
│                                                          │
│  Problem: keprix.yaml contains API keys in plaintext      │
│           `git commit` → keys leaked to GitHub            │
│                                                          │
│  Solution: Vault-backed credentials                       │
│                                                          │
│  keprix.yaml:                                             │
│    providers:                                             │
│      openai:                                              │
│        api_key: ${OPENAI_API_KEY}     ← env var ref      │
│      anthropic:                                           │
│        api_key: vault://anthropic/key ← vault ref        │
│      deepseek:                                            │
│        api_key: ${DEEPSEEK_API_KEY}                       │
│                                                          │
│  Vault backends:                                          │
│    • Env vars (current, keep for dev)                     │
│    • systemd credentials (production)                     │
│    • HashiCorp Vault (enterprise)                         │
│    • Encrypted .env.asc (git-safe, GPG-encrypted)         │
│                                                          │
│  Key scanner on keprix start:                             │
│    → Scans all config files for hardcoded keys            │
│    → Warns (dev) / Refuses to start (prod)                │
└──────────────────────────────────────────────────────────┘
```

```python
# keprix/src/keprix/config/credential_vault.py
"""Resolve credentials from env vars, vault, or encrypted files."""

import os, re, subprocess
from pathlib import Path

VAULT_PATTERN = re.compile(r'\$\{(\w+)\}|vault://(.+)')

class CredentialVault:
    """Resolves credential references safely."""
    
    @staticmethod
    def resolve(value: str) -> str:
        """Resolve ${VAR} or vault://path references."""
        match = VAULT_PATTERN.match(str(value))
        if not match:
            # Plaintext value; check if it looks like a key
            if CredentialVault._looks_like_secret(str(value)):
                raise CredentialError(
                    f"Hardcoded secret detected in config. "
                    f"Use ${{ENV_VAR}} or vault://path instead."
                )
            return str(value)
        
        if match.group(1):  # ${ENV_VAR}
            var_name = match.group(1)
            val = os.environ.get(var_name)
            if val is None:
                raise CredentialError(f"Environment variable ${var_name} not set")
            return val
        
        if match.group(2):  # vault://path
            vault_path = match.group(2)
            return CredentialVault._resolve_vault(vault_path)
        
        return str(value)
    
    @staticmethod
    def _looks_like_secret(value: str) -> bool:
        """Heuristic: does this look like an API key?"""
        patterns = [
            r'^sk-[a-zA-Z0-9]{20,}$',       # OpenAI/Stripe
            r'^xai-[a-zA-Z0-9]{20,}$',       # xAI
            r'^anth[a-zA-Z0-9_-]{20,}$',     # Anthropic
            r'^[A-Za-z0-9+/]{30,}=*$',        # base64-looking
        ]
        return any(re.match(p, value) for p in patterns)
    
    @staticmethod
    def _resolve_vault(path: str) -> str:
        """Resolve from HashiCorp Vault, systemd creds, or GPG file."""
        # Systemd credentials
        cred_file = f"/run/credentials/keprix.service/{path.replace('/', '-')}"
        if os.path.exists(cred_file):
            with open(cred_file) as f:
                return f.read().strip()
        
        # GPG-encrypted .env
        enc_file = Path(f"~/.keprix/secrets/{path}.asc").expanduser()
        if enc_file.exists():
            result = subprocess.run(
                ['gpg', '--decrypt', str(enc_file)],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        
        raise CredentialError(f"Cannot resolve vault://{path}")

# Startup check
def scan_config_for_hardcoded_secrets(config_path: str):
    """Scan config file for hardcoded API keys. Refuse to start in production."""
    import yaml
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    violations = []
    def walk(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ('api_key', 'secret', 'token', 'password'):
                    if isinstance(v, str) and CredentialVault._looks_like_secret(v):
                        violations.append(f"{path}.{k}")
                walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]")
    
    walk(config)
    
    if violations:
        is_prod = os.environ.get('KEPRIX_ENV') == 'production'
        msg = f"Hardcoded secrets found in {config_path}:\n" + \
              "\n".join(f"  → {v}" for v in violations) + \
              "\nReplace with ${ENV_VAR} references."
        if is_prod:
            raise SystemExit(msg)
        else:
            import logging
            logging.warning(msg)
```

### 3. Tool Sandbox; Don't Let Agents Run Wild

```
┌──────────────────────────────────────────────────────────┐
│              TOOL SANDBOX                                  │
│                                                          │
│  Every tool call flows through a sandbox gate:            │
│                                                          │
│  Agent wants to run: rm -rf /                             │
│         │                                                 │
│         ▼                                                 │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ SANDOX GATE                                          │ │
│  │                                                      │ │
│  │  1. Is tool allowed for this session? /           │ │
│  │  2. Is path within workspace?      /              │ │
│  │  3. Is command in allowlist?        /              │ │
│  │  4. Does command match deny pattern? /            │ │
│  │  5. Is rate limit exceeded?         /              │ │
│  │  6. Does this need human approval?  /              │ │
│  │                                                      │ │
│  │   → BLOCK + log + signal Scout                      │ │
│  │   → Execute                                          │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

```python
# keprix/src/keprix/security/tool_sandbox.py
"""Tool execution sandbox. Blocks dangerous operations."""

import re, os, shlex

TERMINAL_DENY_PATTERNS = [
    r'rm\s+-rf\s+/',           # rm -rf /
    r'>\s*/dev/[sh]da',        # overwrite disk
    r'mkfs\.',                 # format filesystem
    r'dd\s+if=',              # raw disk write
    r'chmod\s+777\s+/',       # world-writable root
    r'chown\s+-R\s+\w+\s+/',  # recursive chown root
    r':\(\)\s*\{',            # fork bomb pattern
    r'wget\s+.*\|\s*(ba)?sh', # curl-pipe-bash
    r'nc\s+-[nl]',            # netcat listener
    r'python\s+-c\s+.*exec',  # Python exec injection
    r'eval\s',                 # shell eval
    r'\\x[0-9a-f]{2}',        # hex-encoded shellcode
]

FILE_WRITE_DENY_PATHS = [
    '/etc/', '/boot/', '/sys/', '/proc/', '/dev/',
    '~/.ssh/', '/root/', '/var/log/',
    # Protect Scout files
    'scout_control.py', 'scout_listener.py', 'auto_response.py',
]

class ToolSandbox:
    """Validates tool calls before execution."""
    
    @staticmethod
    def validate_terminal(command: str, workspace_root: str) -> tuple[bool, str]:
        """Check if a terminal command is safe to execute."""
        # Check deny patterns
        for pattern in TERMINAL_DENY_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Command blocked by pattern: {pattern}"
        
        # Check no absolute paths outside workspace (for write operations)
        tokens = shlex.split(command)
        for token in tokens:
            if token.startswith('/') and not token.startswith(workspace_root):
                # Only block if it looks like a write target
                if any(op in command for op in ['>', '>>', 'cp ', 'mv ', 'touch ']):
                    return False, f"Write to {token} blocked: outside workspace"
        
        return True, "OK"
    
    @staticmethod
    def validate_file_write(path: str, workspace_root: str) -> tuple[bool, str]:
        """Check if a file write is safe."""
        resolved = os.path.realpath(os.path.expanduser(path))
        
        for deny_path in FILE_WRITE_DENY_PATHS:
            deny_resolved = os.path.realpath(os.path.expanduser(deny_path))
            if resolved.startswith(deny_resolved):
                return False, f"Write to {path} blocked: protected path"
        
        if not resolved.startswith(workspace_root):
            return False, f"Write to {path} blocked: outside workspace"
        
        return True, "OK"
    
    @staticmethod
    def validate_web_request(url: str) -> tuple[bool, str]:
        """Check if a web request is safe."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        # Block internal/local network
        hostname = parsed.hostname or ''
        if hostname in ('localhost', '127.0.0.1', '0.0.0.0', '::1'):
            return False, "Blocked: localhost request"
        
        if hostname.startswith('10.') or hostname.startswith('192.168.') or \
           hostname.startswith('172.16.') or hostname.startswith('169.254.'):
            return False, "Blocked: private network request"
        
        # Block known malicious patterns
        if 'metadata.google.internal' in hostname:
            return False, "Blocked: cloud metadata endpoint"
        
        return True, "OK"

# Hook into tool execution
original_terminal_exec = None  # patched at startup

def sandboxed_terminal(command: str, **kwargs):
    workspace = os.environ.get('KEPRIX_WORKSPACE', os.path.expanduser('~/keprix-workspace'))
    allowed, reason = ToolSandbox.validate_terminal(command, workspace)
    if not allowed:
        from keprix.security.scout_integration import emit_scout_signal
        from keprix.security.scout_types import SignalCategory, SignalSeverity
        emit_scout_signal(
            SignalCategory.TOOL_ABUSE,
            SignalSeverity.HIGH,
            "tool_blocked",
            f"terminal:{command[:100]}",
            {"reason": reason, "command": command[:500]}
        )
        raise ToolBlockedError(reason)
    return original_terminal_exec(command, **kwargs)
```

### 4. Memory Budget; Don't Let Context Windows Eat the Server

```
┌──────────────────────────────────────────────────────────┐
│              MEMORY GOVERNOR                               │
│                                                          │
│  Keprix keeps conversation history, tool results,         │
│  and system prompts in memory. This grows unbounded.      │
│                                                          │
│  Hard limits:                                             │
│  ┌────────────────────────────────────────────────────┐  │
│  │ • Max context tokens:       128,000 (configurable)  │  │
│  │ • Max tool results in memory: 50                    │  │
│  │ • Max conversation turns:   200                     │  │
│  │ • Max file content in context: 50,000 chars         │  │
│  │ • Auto-summarize: at 80% token budget               │  │
│  │ • Auto-truncate: at 95% token budget (oldest first) │  │
│  │ • Process memory limit:     2GB RSS (ulimit)        │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

```python
# keprix/src/keprix/security/memory_governor.py
"""Prevents agent from consuming unbounded memory."""

import tiktoken, resource, os

MAX_CONTEXT_TOKENS = int(os.environ.get('KEPRIX_MAX_CONTEXT_TOKENS', '128000'))
MAX_TOOL_RESULTS = int(os.environ.get('KEPRIX_MAX_TOOL_RESULTS', '50'))
MAX_CONVERSATION_TURNS = int(os.environ.get('KEPRIX_MAX_TURNS', '200'))
MAX_FILE_CONTENT_CHARS = int(os.environ.get('KEPRIX_MAX_FILE_CHARS', '50000'))
AUTO_SUMMARIZE_AT = 0.80  # 80% of max tokens
AUTO_TRUNCATE_AT = 0.95   # 95% of max tokens
MAX_RSS_MB = int(os.environ.get('KEPRIX_MAX_RSS_MB', '2048'))

class MemoryGovernor:
    """Tracks and enforces memory budgets."""
    
    def __init__(self):
        self.encoder = tiktoken.get_encoding('cl100k_base')
        self.tool_results_count = 0
        self.conversation_turns = 0
        self.total_tokens = 0
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token count."""
        return len(self.encoder.encode(text))
    
    def check_before_add(self, message: str, turn_type: str = 'message') -> str:
        """
        Check if we can add this to context.
        Returns: 'OK', 'SUMMARIZE', or 'TRUNCATE'
        """
        new_tokens = self.estimate_tokens(message)
        projected = self.total_tokens + new_tokens
        
        if projected > MAX_CONTEXT_TOKENS * AUTO_TRUNCATE_AT:
            return 'TRUNCATE'
        if projected > MAX_CONTEXT_TOKENS * AUTO_SUMMARIZE_AT:
            return 'SUMMARIZE'
        return 'OK'
    
    def check_tool_result(self, result_text: str) -> bool:
        """Returns False if too many tool results in context."""
        self.tool_results_count += 1
        if self.tool_results_count > MAX_TOOL_RESULTS:
            return False
        # Also check if the result itself is too large
        if len(result_text) > MAX_FILE_CONTENT_CHARS:
            return False
        return True
    
    def check_process_memory(self) -> bool:
        """Returns False if process RSS exceeds limit."""
        import psutil
        process = psutil.Process()
        rss_mb = process.memory_info().rss / (1024 * 1024)
        return rss_mb < MAX_RSS_MB
    
    def apply_rss_limit(self):
        """Set hard OS-level memory limit."""
        limit_bytes = MAX_RSS_MB * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))

# Hook into context assembly
def context_assembly_guard(messages: list, new_message: str) -> list:
    """Trim context before sending to model."""
    gov = MemoryGovernor()
    action = gov.check_before_add(new_message)
    
    if action == 'TRUNCATE':
        # Keep system prompt + last 20% of messages
        keep = max(1, int(len(messages) * 0.2))
        system_msgs = [m for m in messages if m.get('role') == 'system']
        recent_msgs = messages[-keep:]
        return system_msgs + recent_msgs + [{'role': 'user', 'content': new_message}]
    
    if action == 'SUMMARIZE':
        # TODO: trigger background summarization of old messages
        pass
    
    return messages + [{'role': 'user', 'content': new_message}]
```

### 5. Process Isolation; Contain the Agent

```
┌──────────────────────────────────────────────────────────┐
│              PROCESS ISOLATION                             │
│                                                          │
│  keprix agent runs inside a container/namespace:          │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ KEPRIX AGENT (uid: 1001, gid: 1001)                 │  │
│  │                                                      │  │
│  │  • Workspace: /home/keprix/workspace (chroot-able)  │  │
│  │  • No sudo access                                    │  │
│  │  • No access to /home/malike                         │  │
│  │  • No access to /opt/lampp outside workspace         │  │
│  │  • cgroup: 4GB RAM, 50 procs, 50% CPU               │  │
│  │  • seccomp: only allowed syscalls                    │  │
│  │  • Network: egress-filtered via Sentinel              │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

```python
# keprix/src/keprix/security/process_isolation.py
"""Drop privileges and apply sandboxing at agent start."""

import os, grp, pwd, resource

def drop_privileges(uid_name: str = 'keprix', gid_name: str = 'keprix'):
    """Drop from root to unprivileged user."""
    if os.getuid() != 0:
        return  # Already non-root
    
    # Get target UID/GID
    pw = pwd.getpwnam(uid_name)
    gid = grp.getgrnam(gid_name).gr_gid
    
    # Clear supplementary groups
    os.setgroups([])
    os.setgid(gid)
    os.setuid(pw.pw_uid)
    
    # Verify
    if os.getuid() == 0:
        raise RuntimeError("Failed to drop privileges")

def apply_resource_limits():
    """Apply hard OS resource limits."""
    # Max file size: 100MB
    resource.setrlimit(resource.RLIMIT_FSIZE, (100 * 1024 * 1024, 100 * 1024 * 1024))
    # Max processes: 50
    resource.setrlimit(resource.RLIMIT_NPROC, (50, 50))
    # Max open files: 256
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    # Max memory: 2GB
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, 2 * 1024 * 1024 * 1024))
    # Max CPU time: 1 hour
    resource.setrlimit(resource.RLIMIT_CPU, (3600, 3600))

def restrict_filesystem(workspace: str):
    """Only allow access to workspace directory."""
    # chroot if running as root (dropped after)
    # For non-root: use bind mounts via systemd
    os.environ['HOME'] = workspace
    os.environ['PATH'] = '/usr/bin:/bin'
    os.chdir(workspace)

# Call at agent startup
def isolate():
    drop_privileges()
    apply_resource_limits()
    restrict_filesystem(os.environ.get('KEPRIX_WORKSPACE', '/home/keprix/workspace'))
```

### 6. Sub-Agent Fan-Out Control; Don't Spawn a Fork Bomb

```
┌──────────────────────────────────────────────────────────┐
│              SUB-AGENT GOVERNOR                            │
│                                                          │
│  delegate_task can spawn sub-agents. Without limits,      │
│  a recursive loop creates a fork bomb that burns tokens.  │
│                                                          │
│  Limits:                                                  │
│  ┌────────────────────────────────────────────────────┐  │
│  │ • Max concurrent sub-agents:      10               │  │
│  │ • Max delegation depth:           3                │  │
│  │ • Max total sub-agents/session:   50               │  │
│  │ • Sub-agent timeout:              5 minutes         │  │
│  │ • Auto-kill on timeout:           SIGKILL + cleanup │  │
│  │ • Parent tracks all children:     PID + status      │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

```python
# keprix/src/keprix/security/sub_agent_governor.py
"""Prevents sub-agent fork bombs and recursive delegation loops."""

import threading, time, signal, os

MAX_CONCURRENT = int(os.environ.get('KEPRIX_MAX_SUB_AGENTS', '10'))
MAX_DEPTH = int(os.environ.get('KEPRIX_MAX_DEPTH', '3'))
MAX_TOTAL = int(os.environ.get('KEPRIX_MAX_TOTAL_SUBS', '50'))
SUB_TIMEOUT = int(os.environ.get('KEPRIX_SUB_TIMEOUT', '300'))

class SubAgentGovernor:
    def __init__(self):
        self._lock = threading.Lock()
        self._active: dict[str, dict] = {}  # session_id → {count, depth, children}
        self._total_spawned: dict[str, int] = {}
    
    def can_spawn(self, session_id: str, parent_depth: int = 0) -> tuple[bool, str]:
        with self._lock:
            session = self._active.setdefault(session_id, {
                'count': 0, 'depth': parent_depth, 'children': []
            })
            
            if session['count'] >= MAX_CONCURRENT:
                return False, f"Max concurrent sub-agents ({MAX_CONCURRENT}) reached"
            
            if parent_depth >= MAX_DEPTH:
                return False, f"Max delegation depth ({MAX_DEPTH}) reached"
            
            total = self._total_spawned.get(session_id, 0)
            if total >= MAX_TOTAL:
                return False, f"Max total sub-agents ({MAX_TOTAL}) reached"
            
            return True, "OK"
    
    def register(self, session_id: str, sub_pid: int, parent_depth: int):
        with self._lock:
            session = self._active[session_id]
            session['count'] += 1
            session['depth'] = max(session['depth'], parent_depth + 1)
            session['children'].append({
                'pid': sub_pid,
                'started': time.time(),
                'depth': parent_depth + 1
            })
            self._total_spawned[session_id] = self._total_spawned.get(session_id, 0) + 1
            
            # Start timeout watcher
            threading.Thread(target=self._watch_timeout, 
                           args=(session_id, sub_pid), daemon=True).start()
    
    def _watch_timeout(self, session_id: str, sub_pid: int):
        time.sleep(SUB_TIMEOUT)
        try:
            os.kill(sub_pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        with self._lock:
            session = self._active.get(session_id)
            if session:
                session['count'] = max(0, session['count'] - 1)
    
    def unregister(self, session_id: str, sub_pid: int):
        with self._lock:
            session = self._active.get(session_id)
            if session:
                session['count'] = max(0, session['count'] - 1)
                session['children'] = [
                    c for c in session['children'] if c['pid'] != sub_pid
                ]

sub_governor = SubAgentGovernor()
```

### 7. Startup Health Check; Refuse to Run If Unsafe

```
┌──────────────────────────────────────────────────────────┐
│              STARTUP GATE                                  │
│                                                          │
│  On keprix start:                                         │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ 1. Scan config for hardcoded secrets → BLOCK        │ │
│  │ 2. Check disk space > 1GB free → WARN if low        │ │
│  │ 3. Check memory available > 512MB → BLOCK            │ │
│  │ 4. Check no other keprix instance on same workspace  │ │
│  │ 5. Check Sentinel running → WARN if not              │ │
│  │ 6. Check workspace permissions (700) → BLOCK         │ │
│  │ 7. Check .gitignore has .env → WARN if not           │ │
│  │ 8. Log startup checks to audit trail                  │ │
│  │                                                      │ │
│  │  ALL PASS → keprix starts                             │ │
│  │  ANY BLOCK → keprix refuses, prints fix instructions │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

```python
# keprix/src/keprix/security/startup_gate.py
"""Refuse to start if the environment is unsafe."""

import os, sys, shutil
from pathlib import Path

class StartupGate:
    
    @staticmethod
    def check_all(config_path: str, workspace: str) -> bool:
        checks = [
            ('Secret scan', StartupGate._check_secrets, [config_path]),
            ('Disk space', StartupGate._check_disk_space, [workspace]),
            ('Memory available', StartupGate._check_memory, []),
            ('Workspace permissions', StartupGate._check_workspace_perms, [workspace]),
            ('Gitignore has .env', StartupGate._check_gitignore, [workspace]),
            ('No duplicate instance', StartupGate._check_duplicate, [workspace]),
        ]
        
        all_pass = True
        for name, check_fn, args in checks:
            passed, msg = check_fn(*args)
            status = 'Done: ' if passed else 'Failed: '
            print(f"  {status} {name}: {msg}")
            if not passed and 'BLOCK' in msg:
                all_pass = False
        
        return all_pass
    
    @staticmethod
    def _check_secrets(config_path: str) -> tuple[bool, str]:
        from keprix.config.credential_vault import scan_config_for_hardcoded_secrets
        try:
            scan_config_for_hardcoded_secrets(config_path)
            return True, "No hardcoded secrets found"
        except SystemExit as e:
            return False, f"BLOCK: {e}"
    
    @staticmethod
    def _check_disk_space(path: str) -> tuple[bool, str]:
        stat = shutil.disk_usage(path)
        free_gb = stat.free / (1024**3)
        if free_gb < 1:
            return False, f"BLOCK: Only {free_gb:.1f}GB free. Need at least 1GB."
        if free_gb < 5:
            return True, f"Low: {free_gb:.1f}GB free"
        return True, f"{free_gb:.1f}GB free"
    
    @staticmethod
    def _check_memory() -> tuple[bool, str]:
        import psutil
        mem = psutil.virtual_memory()
        avail_mb = mem.available / (1024 * 1024)
        if avail_mb < 512:
            return False, f"BLOCK: Only {avail_mb:.0f}MB available. Need 512MB."
        return True, f"{avail_mb:.0f}MB available"
    
    @staticmethod
    def _check_workspace_perms(workspace: str) -> tuple[bool, str]:
        st = os.stat(workspace)
        mode = oct(st.st_mode)[-3:]
        if mode != '700':
            return False, f"BLOCK: Permissions are {mode}, must be 700."
        return True, "700"
    
    @staticmethod
    def _check_gitignore(workspace: str) -> tuple[bool, str]:
        gitignore = Path(workspace) / '.gitignore'
        if gitignore.exists():
            content = gitignore.read_text()
            if '.env' not in content:
                return True, "WARNING: .gitignore missing .env; secrets may leak"
            return True, ".env is gitignored"
        return True, "No .gitignore (not a git repo?)"
    
    @staticmethod
    def _check_duplicate(workspace: str) -> tuple[bool, str]:
        lockfile = Path(workspace) / '.keprix.lock'
        if lockfile.exists():
            try:
                with open(lockfile) as f:
                    pid = int(f.read().strip())
                os.kill(pid, 0)  # Check if process exists
                return True, "WARNING: Another keprix instance may be running"
            except (ProcessLookupError, ValueError):
                pass
        with open(lockfile, 'w') as f:
            f.write(str(os.getpid()))
        return True, "OK"

# Call at startup; before anything else
if __name__ == '__main__':
    # This runs before main agent loop
    config = sys.argv[1] if len(sys.argv) > 1 else 'keprix.yaml'
    workspace = os.environ.get('KEPRIX_WORKSPACE', os.path.expanduser('~/keprix-workspace'))
    
    if not StartupGate.check_all(config, workspace):
        print("\n Startup blocked. Fix the issues above and try again.")
        sys.exit(1)
    
    print("\nDone:  All checks passed. Starting keprix...")
```

---

## Implementation Order (Priority by Risk)

| Priority | What | Why First |
|----------|------|-----------|
|  P0 | **Credential vault** + secret scanner | One leaked API key = thousands in fraud. Must be day 0. |
|  P0 | **Agent governor** (rate limits + token budgets) | Runaway agent can burn $500 in an hour. |
|  P1 | **Tool sandbox** | Without this, agent can `rm -rf` the workspace. |
|  P1 | **Memory governor** | Unbounded context → OOM kill → crashed agent. |
|  P2 | **Process isolation** | Drop privileges, cgroup limits, filesystem restriction. |
|  P2 | **Sub-agent governor** | Fork bomb == wallet drain + server crash. |
|  P3 | **Startup gate** | Catch misconfigurations before they become incidents. |

---

## Files

| # | Action | File | Purpose |
|---|--------|------|---------|
| 1 | **CREATE** | `src/keprix/security/agent_governor.py` | Rate limits + token budgets |
| 2 | **CREATE** | `src/keprix/config/credential_vault.py` | Vault-backed credential resolution + secret scanner |
| 3 | **CREATE** | `src/keprix/security/tool_sandbox.py` | Tool call validation gate |
| 4 | **CREATE** | `src/keprix/security/memory_governor.py` | Context budget + RSS limits |
| 5 | **CREATE** | `src/keprix/security/process_isolation.py` | Drop privileges + resource limits |
| 6 | **CREATE** | `src/keprix/security/sub_agent_governor.py` | Fan-out control + timeout |
| 7 | **CREATE** | `src/keprix/security/startup_gate.py` | Pre-flight safety checks |
| 8 | **MODIFY** | `src/keprix/keprix_cli/main.py` | Wire startup gate + governors |

---

## Acceptance Criteria

- [ ] Hardcoded API key in keprix.yaml → keprix refuses to start in production, warns in dev
- [ ] Agent hits 50 tool calls in one turn → blocked + cooldown
- [ ] Agent hits $5 token budget → stopped, operator notified
- [ ] Product hits $50/day budget → all sessions for that product paused
- [ ] `rm -rf /` command → blocked by tool sandbox
- [ ] File write outside workspace → blocked
- [ ] Web request to localhost/private IP → blocked
- [ ] Context exceeds 128K tokens → auto-truncated, oldest messages dropped
- [ ] Process RSS exceeds 2GB → OOM prevented by OS limit
- [ ] More than 10 concurrent sub-agents → blocked
- [ ] Sub-agent runs longer than 5 minutes → SIGKILL
- [ ] Workspace permissions not 700 → keprix refuses to start
- [ ] Less than 512MB RAM → keprix refuses to start
- [ ] Less than 1GB disk → keprix warns
- [ ] All startup checks logged to audit trail
