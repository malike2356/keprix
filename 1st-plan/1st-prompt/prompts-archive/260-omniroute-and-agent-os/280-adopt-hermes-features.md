# Prompt 90; Adopt Hermes Features: Checkpoint, MoA, X Search, Progressive Disclosure

## 0. Context

Hermes Agent v0.17.0 has 4 features Keprix lacks. None are in Julian Goldie's hype video; those are already in Keprix. These are actual gaps found during codebase audit.

| # | Feature | Hermes Source | Priority |
|---|---------|--------------|----------|
| 1 | Checkpoint Manager | `tools/checkpoint_manager.py` | HIGH; security |
| 2 | Mixture of Agents (MoA) | `tools/mixture_of_agents_tool.py` | MEDIUM; reasoning |
| 3 | X/Twitter Search | `tools/x_search_tool.py` | LOW; niche tool |
| 4 | Progressive Tool Disclosure | `tools/tool_search.py` | MEDIUM; scaling |

---

## 1. Checkpoint Manager; Filesystem Snapshots & Rollback

### What Hermes Has

Transparent git-based filesystem checkpointing. Before any file-mutating operation (`write_file`, `patch`, `terminal` writes), a snapshot is taken. If the agent corrupts files, roll back to the last checkpoint.

### What Keprix Builds

```python
# keprix/security/checkpoint_manager.py

"""
Git-based filesystem checkpointing integrated with Prompt 87 sandbox.

Every file-mutating tool call creates a checkpoint BEFORE execution.
If governance rules trigger BLOCK after a write, auto-rollback.
Operator can manually rollback to any checkpoint.
Scout can trigger rollback via kill switch command.

Integration points:
- write_file → pre_write checkpoint
- patch → pre_patch checkpoint  
- terminal (writes) → pre_exec checkpoint
- skill_manage (write_file) → pre_write checkpoint
- Governance BLOCK on write → auto-rollback
- Scout command ROLLBACK_TO_CHECKPOINT → execute rollback
"""

import os
import subprocess
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field


@dataclass
class Checkpoint:
    checkpoint_id: str
    timestamp: str
    triggered_by: str          # "tool:write_file", "tool:terminal", "scout_command"
    tool_name: str
    tool_args_preview: str     # First 200 chars (redacted)
    git_hash: str
    files_changed: List[str]
    parent_checkpoint_id: Optional[str] = None


class CheckpointManager:
    """
    Git-based filesystem checkpointing for agent safety.

    Uses a shadow git repo in .keprix/checkpoints/ to track
    all file mutations. Every write is versioned. Every checkpoint
    is a git commit. Rollback is `git checkout <hash>`.

    Design:
    - Shadow repo lives at .keprix/checkpoints/git/
    - Worktree covers allowed_paths from sandbox policy
    - Pre-write: commit current state → return checkpoint_id
    - Post-write: if governance BLOCKs → auto-rollback
    - Manual: `keprix checkpoint list | rollback <id> | diff <id>`
    - Scout: ROLLBACK_TO_CHECKPOINT command → execute
    """

    MAX_CHECKPOINTS = 100       # Auto-prune oldest beyond this
    CHECKPOINT_DIR = ".keprix/checkpoints"

    def __init__(self, workspace_root: Path, sandbox_policy):
        self.workspace_root = workspace_root
        self.sandbox_policy = sandbox_policy
        self.shadow_dir = workspace_root / self.CHECKPOINT_DIR / "git"
        self.state_file = workspace_root / self.CHECKPOINT_DIR / "state.json"
        self._init_shadow_repo()

    def _init_shadow_repo(self):
        """Initialise shadow git repo in .keprix/checkpoints/git/."""
        self.shadow_dir.mkdir(parents=True, exist_ok=True)

        if not (self.shadow_dir / ".git").exists():
            subprocess.run(
                ["git", "init"],
                cwd=self.shadow_dir,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Keprix Checkpoint Manager"],
                cwd=self.shadow_dir,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "checkpoint@keprix.internal"],
                cwd=self.shadow_dir,
                capture_output=True,
            )

        # Initialise gitignore to track only allowed paths
        gitignore = self.shadow_dir / ".gitignore"
        gitignore.write_text("*\n")  # Ignore everything by default
        # Allow only sandbox-policy paths
        for path in self.sandbox_policy.allowed_paths:
            rel = os.path.relpath(path, self.workspace_root)
            with open(gitignore, "a") as f:
                f.write(f"!{rel}/**\n")

    def create_checkpoint(
        self, tool_name: str, tool_args: dict, triggered_by: str = "tool"
    ) -> Checkpoint:
        """
        Create a checkpoint before a file-mutating operation.

        Returns checkpoint_id for later rollback.
        Emits Scout signal: checkpoint.created
        """
        # Stage all tracked files
        subprocess.run(
            ["git", "add", "-A"],
            cwd=self.shadow_dir,
            capture_output=True,
        )

        # Get list of changed files
        diff_result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=self.shadow_dir,
            capture_output=True,
            text=True,
        )
        files_changed = [
            f for f in diff_result.stdout.strip().split("\n") if f
        ]

        # Commit
        timestamp = datetime.now(timezone.utc).isoformat()
        args_preview = json.dumps(tool_args, default=str)[:200]
        commit_msg = f"[{triggered_by}] {tool_name}: {args_preview}"

        commit_result = subprocess.run(
            ["git", "commit", "-m", commit_msg, "--allow-empty"],
            cwd=self.shadow_dir,
            capture_output=True,
            text=True,
        )

        # Get commit hash
        hash_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.shadow_dir,
            capture_output=True,
            text=True,
        )
        git_hash = hash_result.stdout.strip()

        # Load previous checkpoint for chain
        parent_id = None
        state = self._load_state()
        if state.get("checkpoints"):
            parent_id = state["checkpoints"][-1]["checkpoint_id"]

        checkpoint = Checkpoint(
            checkpoint_id=f"ckpt-{git_hash[:12]}",
            timestamp=timestamp,
            triggered_by=triggered_by,
            tool_name=tool_name,
            tool_args_preview=args_preview,
            git_hash=git_hash,
            files_changed=files_changed,
            parent_checkpoint_id=parent_id,
        )

        # Save state
        self._save_checkpoint(checkpoint)

        # Auto-prune if over limit
        self._prune_old_checkpoints()

        # Emit Scout signal
        from keprix.security.scout_client import scout_client, SignalCategory, SignalSeverity
        scout_client.send(
            category=SignalCategory.GOVERNANCE,
            severity=SignalSeverity.INFO,
            action="checkpoint_created",
            target=f"workspace:{self.workspace_root}",
            details={
                "checkpoint_id": checkpoint.checkpoint_id,
                "tool_name": tool_name,
                "files_changed": len(files_changed),
                "git_hash": git_hash,
            },
        )

        return checkpoint

    def rollback(self, checkpoint_id: str) -> bool:
        """
        Rollback filesystem to a specific checkpoint.

        Uses git checkout to restore state.
        Emits Scout signal: checkpoint.rollback
        """
        state = self._load_state()
        target = None
        for cp in state.get("checkpoints", []):
            if cp["checkpoint_id"] == checkpoint_id:
                target = cp
                break

        if not target:
            return False

        # Git checkout to target hash
        result = subprocess.run(
            ["git", "checkout", target["git_hash"], "--", "."],
            cwd=self.shadow_dir,
            capture_output=True,
            text=True,
        )

        success = result.returncode == 0

        # Emit Scout signal
        from keprix.security.scout_client import scout_client, SignalCategory, SignalSeverity
        scout_client.send(
            category=SignalCategory.GOVERNANCE,
            severity=SignalSeverity.WARNING if not success else SignalSeverity.INFO,
            action="checkpoint_rollback",
            target=f"checkpoint:{checkpoint_id}",
            details={
                "checkpoint_id": checkpoint_id,
                "success": success,
                "triggered_by": "manual",
            },
        )

        return success

    def list_checkpoints(self, limit: int = 20) -> List[dict]:
        """List recent checkpoints."""
        state = self._load_state()
        return state.get("checkpoints", [])[-limit:]

    def diff_checkpoint(self, checkpoint_id: str) -> str:
        """Show diff between a checkpoint and current state."""
        state = self._load_state()
        target = None
        for cp in state.get("checkpoints", []):
            if cp["checkpoint_id"] == checkpoint_id:
                target = cp
                break

        if not target:
            return "Checkpoint not found"

        result = subprocess.run(
            ["git", "diff", target["git_hash"], "HEAD", "--", "."],
            cwd=self.shadow_dir,
            capture_output=True,
            text=True,
        )
        return result.stdout[:5000]  # Truncate for context window

    def _save_checkpoint(self, checkpoint: Checkpoint):
        """Append checkpoint to state file."""
        state = self._load_state()
        state.setdefault("checkpoints", []).append({
            "checkpoint_id": checkpoint.checkpoint_id,
            "timestamp": checkpoint.timestamp,
            "triggered_by": checkpoint.triggered_by,
            "tool_name": checkpoint.tool_name,
            "git_hash": checkpoint.git_hash,
            "files_changed": checkpoint.files_changed,
            "parent_checkpoint_id": checkpoint.parent_checkpoint_id,
        })
        self.state_file.write_text(json.dumps(state, indent=2))

    def _load_state(self) -> dict:
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())
        return {}

    def _prune_old_checkpoints(self):
        """Remove oldest checkpoints beyond MAX_CHECKPOINTS."""
        state = self._load_state()
        checkpoints = state.get("checkpoints", [])
        if len(checkpoints) > self.MAX_CHECKPOINTS:
            excess = len(checkpoints) - self.MAX_CHECKPOINTS
            # Keep the most recent MAX_CHECKPOINTS
            state["checkpoints"] = checkpoints[excess:]
            self.state_file.write_text(json.dumps(state, indent=2))


# ── Integration into tool execution ──────────────────────

# In keprix/tools/write_file.py (and patch, terminal):
def write_file_with_checkpoint(path, content):
    """Write file with pre-write checkpoint."""
    checkpoint_mgr = get_checkpoint_manager()

    # Create pre-write checkpoint
    cp = checkpoint_mgr.create_checkpoint(
        tool_name="write_file",
        tool_args={"path": str(path), "content_length": len(content)},
    )

    try:
        # Perform the write
        path.write_text(content)

        # Run governance check
        from keprix.security.governance import governance_engine, Verdict
        verdict, msg, _ = governance_engine.evaluate(
            action="write_file",
            context={"path": str(path), "checkpoint_id": cp.checkpoint_id},
        )

        if verdict == Verdict.BLOCK:
            # Auto-rollback on governance block
            checkpoint_mgr.rollback(cp.checkpoint_id)
            raise PermissionError(f"Write blocked by governance: {msg}")

        return True

    except Exception:
        # Rollback on any write failure
        checkpoint_mgr.rollback(cp.checkpoint_id)
        raise
```

### Scout Integration

| Event | Scout Signal |
|-------|-------------|
| Checkpoint created | `checkpoint.created`; tool name, files changed |
| Rollback executed | `checkpoint.rollback`; source checkpoint, success |
| Auto-rollback (governance block) | `checkpoint.auto_rollback`; rule triggered |

### Scout Command

```
Scout → Keprix: ROLLBACK_TO_CHECKPOINT { checkpoint_id: "ckpt-a1b2c3d4e5f6" }
  → CheckpointManager.rollback("ckpt-a1b2c3d4e5f6")
  → Filesystem restored to that point
  → Scout ACK: "executed"
```

### CLI

```bash
keprix checkpoint list                    # Show recent checkpoints
keprix checkpoint rollback <id>           # Restore to checkpoint
keprix checkpoint diff <id>               # Show what changed since checkpoint
keprix checkpoint prune --keep 50         # Keep only last 50
```

### Files

| File | Purpose |
|------|---------|
| `keprix/security/checkpoint_manager.py` | Core checkpoint engine |
| `keprix/cli/checkpoint.py` | CLI: list, rollback, diff, prune |
| `keprix/tools/write_file.py` | Add pre-write checkpoint + governance rollback |
| `keprix/tools/patch_tool.py` | Add pre-patch checkpoint + governance rollback |
| `keprix/tools/terminal_tool.py` | Add pre-exec checkpoint for write commands |
| `tests/security/test_checkpoint_manager.py` | Tests |

---

## 2. Mixture of Agents (MoA); Multi-LLM Reasoning

### What Hermes Has

Multi-LLM synthesis based on arXiv:2406.04692v1. Parallel reference models generate responses. An aggregator model synthesises a final answer. Improves accuracy on complex reasoning tasks.

### What Keprix Builds

```python
# keprix/tools/mixture_of_agents_tool.py

"""
Mixture of Agents (MoA) tool.

Runs multiple LLMs in parallel on the same prompt.
Reference models provide diverse perspectives.
Aggregator model synthesises a final answer.

Uses Keprix's existing provider routing (Prompt 79) to select models.
Respects credential vault for API keys.
Emits Scout signals for usage tracking.

Security: each model call goes through input sanitizer + output guard.
          aggregator output is scanned for injection before returning.
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Optional
import json

from keprix.providers.router import ProviderRouter
from keprix.security.input_sanitizer import InputSanitizer
from keprix.security.output_guard import OutputGuard


@dataclass
class MoAResult:
    prompt: str
    reference_responses: List[dict]  # [{model, response, tokens, cost}]
    aggregated_response: str
    aggregator_model: str
    total_tokens: int
    total_cost: float
    duration_seconds: float


class MixtureOfAgents:
    """
    Multi-LLM reasoning via parallel reference models + aggregator synthesis.

    Configuration:
    - reference_models: list of model IDs (default: 3 diverse models)
    - aggregator_model: model ID for synthesis (default: strongest available)
    - max_parallel: max concurrent reference calls (default: 3)
    - timeout: per-model timeout (default: 60s)
    """

    DEFAULT_REFERENCE_MODELS = [
        "openai/gpt-4o",
        "anthropic/claude-sonnet-4",
        "google/gemini-2.5-pro",
    ]
    DEFAULT_AGGREGATOR = "anthropic/claude-sonnet-4"

    def __init__(self, router: ProviderRouter):
        self.router = router
        self.input_sanitizer = InputSanitizer()
        self.output_guard = OutputGuard()

    async def synthesise(
        self,
        prompt: str,
        reference_models: List[str] = None,
        aggregator_model: str = None,
        max_parallel: int = 3,
    ) -> MoAResult:
        """
        Run MoA synthesis on a prompt.

        1. Sanitise input
        2. Send prompt to all reference models in parallel
        3. Collect responses
        4. Send responses + original prompt to aggregator
        5. Sanitise aggregator output
        6. Return result
        """
        import time
        start = time.time()

        # Sanitise input
        sanitized = self.input_sanitizer.sanitize(prompt, source="moa_input")
        if sanitized.threat_level.value == "malicious":
            from keprix.security.scout_client import scout_client, SignalCategory, SignalSeverity
            scout_client.send(
                category=SignalCategory.PROMPT_INJECTION,
                severity=SignalSeverity.CRITICAL,
                action="moa_injection_blocked",
                target="moa_input",
                details={"threats": sanitized.threats_detected},
            )
            raise ValueError("Prompt injection detected in MoA input")

        ref_models = reference_models or self.DEFAULT_REFERENCE_MODELS
        agg_model = aggregator_model or self.DEFAULT_AGGREGATOR

        # ── Phase 1: Parallel reference model calls ─────
        ref_responses = await asyncio.gather(*[
            self._call_model(model, sanitized.sanitized, "reference")
            for model in ref_models[:max_parallel]
        ], return_exceptions=True)

        # Filter out failures
        valid_responses = []
        for i, resp in enumerate(ref_responses):
            if isinstance(resp, Exception):
                valid_responses.append({
                    "model": ref_models[i],
                    "response": f"[ERROR: {resp}]",
                    "tokens": 0,
                    "cost": 0,
                })
            else:
                valid_responses.append(resp)

        # ── Phase 2: Aggregator synthesis ───────────────
        aggregation_prompt = self._build_aggregation_prompt(
            original_prompt=sanitized.sanitized,
            reference_responses=valid_responses,
        )

        agg_result = await self._call_model(agg_model, aggregation_prompt, "aggregator")

        # Sanitise aggregator output
        cleaned, output_alerts = self.output_guard.scan(agg_result["response"])
        if output_alerts:
            from keprix.security.scout_client import scout_client, SignalCategory, SignalSeverity
            scout_client.send(
                category=SignalCategory.GOVERNANCE,
                severity=SignalSeverity.WARNING,
                action="moa_output_sanitized",
                target="moa_aggregator",
                details={"alerts": output_alerts},
            )

        # Compute totals
        total_tokens = sum(r["tokens"] for r in valid_responses) + agg_result["tokens"]
        total_cost = sum(r["cost"] for r in valid_responses) + agg_result["cost"]

        result = MoAResult(
            prompt=sanitized.sanitized[:500],
            reference_responses=valid_responses,
            aggregated_response=cleaned,
            aggregator_model=agg_model,
            total_tokens=total_tokens,
            total_cost=total_cost,
            duration_seconds=time.time() - start,
        )

        # Emit Scout signal
        from keprix.security.scout_client import scout_client, SignalCategory, SignalSeverity
        scout_client.send(
            category=SignalCategory.GOVERNANCE,
            severity=SignalSeverity.INFO,
            action="moa_synthesis_complete",
            target=f"moa:{len(ref_models)}_models",
            details={
                "reference_models": ref_models[:max_parallel],
                "aggregator_model": agg_model,
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "duration_seconds": result.duration_seconds,
            },
        )

        return result

    async def _call_model(self, model: str, prompt: str, role: str) -> dict:
        """Call a single model. Returns {model, response, tokens, cost}."""
        result = await self.router.call(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        return {
            "model": model,
            "response": result.content,
            "tokens": result.usage.total_tokens if result.usage else 0,
            "cost": result.cost or 0,
        }

    def _build_aggregation_prompt(
        self, original_prompt: str, reference_responses: List[dict]
    ) -> str:
        """Build the aggregation prompt for the final synthesis."""
        responses_text = "\n\n---\n\n".join(
            f"### Model: {r['model']}\n{r['response']}"
            for r in reference_responses
        )

        return f"""You are a synthesis engine. Below are responses from multiple AI models to the same prompt. Your job is to produce a single, high-quality answer that:

1. Identifies areas of agreement across models
2. Resolves contradictions where they exist
3. Incorporates unique insights from individual models
4. Is more accurate and comprehensive than any single response

## ORIGINAL PROMPT:
{original_prompt}

## REFERENCE MODEL RESPONSES:
{responses_text}

## SYNTHESIS INSTRUCTIONS:
- Start with the areas where models agree
- Address contradictions directly: "Model A says X, Model B says Y. X is more accurate because..."
- Include unique valuable insights from individual models
- Produce a final answer that is better than any individual response
- Be concise but comprehensive
"""
```

### Files

| File | Purpose |
|------|---------|
| `keprix/tools/mixture_of_agents_tool.py` | MoA synthesis engine |
| `keprix/toolsets.py` | Register MoA in `_KEPRIX_CORE_TOOLS` (already defined in toolsets) |
| `tests/tools/test_mixture_of_agents.py` | MoA tests |

### Governance Rules

| Rule | Condition | Verdict |
|------|-----------|---------|
| `MOA-001` | MoA call would exceed session spend limit | BLOCK |
| `MOA-002` | Aggregator output contains credential pattern | BLOCK + redact |
| `MOA-003` | More than 5 MoA calls in 10 minutes | RATE LIMIT |

---

## 3. X/Twitter Search

### What Hermes Has

Search X/Twitter via xAI Responses API + SuperGrok OAuth. File: `tools/x_search_tool.py`.

### What Keprix Builds

```python
# keprix/tools/x_search_tool.py

"""
X/Twitter search tool.

Uses xAI API for X/Twitter content search.
API key from credential vault (Prompt 87).
Domain added to egress filter allowlist.
Results sanitised through InputSanitizer before reaching agent.

Security:
- API key never in agent context (credential vault token)
- xAI domain in egress allowlist
- Results scanned for injection patterns
- Rate limited: 10/min, 100/hour
"""

from keprix.security.credential_vault import CredentialVault
from keprix.security.input_sanitizer import InputSanitizer
from keprix.security.egress_filter import EgressFilter
import httpx


class XSearchTool:
    """
    Search X/Twitter for posts, trends, and profiles.

    Uses xAI API with credential from vault.
    Results are sanitised before returning to agent.
    """

    XAI_API = "https://api.x.ai/v1/search"

    def __init__(self, vault: CredentialVault, egress_filter: EgressFilter):
        self.vault = vault
        self.egress_filter = egress_filter
        self.input_sanitizer = InputSanitizer()

        # Ensure xAI domain is in egress allowlist
        egress_filter.ensure_allowed("api.x.ai", [443])

    async def search(
        self, query: str, limit: int = 10, result_type: str = "recent"
    ) -> list[dict]:
        """
        Search X/Twitter.

        Args:
            query: Search query (supports X advanced search operators)
            limit: Max results (1-100)
            result_type: "recent", "top", or "mixed"

        Returns:
            List of {id, text, author, created_at, metrics}
        """
        # Sanitise query
        sanitized = self.input_sanitizer.sanitize(query, source="x_search_query")
        if sanitized.threat_level.value == "malicious":
            raise ValueError("Injection detected in search query")

        # Get API key from vault (token, never raw key)
        api_key = self.vault.retrieve("xai_api_key")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.XAI_API,
                json={
                    "query": sanitized.sanitized,
                    "limit": min(limit, 100),
                    "result_type": result_type,
                },
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

        # Sanitise each result before returning
        results = []
        for item in data.get("results", []):
            sanitized_text = self.input_sanitizer.sanitize(
                item.get("text", ""), source="x_search_result"
            )
            results.append({
                "id": item.get("id"),
                "text": sanitized_text.sanitized,
                "author": item.get("author", {}).get("username"),
                "created_at": item.get("created_at"),
                "metrics": {
                    "likes": item.get("public_metrics", {}).get("like_count", 0),
                    "retweets": item.get("public_metrics", {}).get("retweet_count", 0),
                    "replies": item.get("public_metrics", {}).get("reply_count", 0),
                },
            })

        # Scout signal
        from keprix.security.scout_client import scout_client, SignalCategory, SignalSeverity
        scout_client.send(
            category=SignalCategory.GOVERNANCE,
            severity=SignalSeverity.INFO,
            action="x_search_executed",
            target="tool:x_search",
            details={"query_hash": sanitized.hash, "results": len(results)},
        )

        return results
```

### Files

| File | Purpose |
|------|---------|
| `keprix/tools/x_search_tool.py` | X/Twitter search tool |
| `keprix/toolsets.py` | Register in `_KEPRIX_CORE_TOOLS` (already defined) |
| `tests/tools/test_x_search.py` | Tests |

### Egress Filter

Add to domain allowlist: `api.x.ai:443`

### Rate Limits

- 10 searches per minute per agent
- 100 searches per hour per agent
- Scout signal on rate limit breach

---

## 4. Progressive Tool Disclosure

### What Hermes Has

When context window is too full to include all tool schemas, `tool_search`, `tool_describe`, and `tool_call` bridge tools defer MCP/plugin tools. The agent searches for tools it needs rather than receiving all at once.

### What Keprix Builds

```python
# keprix/tools/progressive_disclosure.py

"""
Progressive tool disclosure for context-window management.

When the system prompt + tools + conversation exceed a threshold
(typically 80% of context window), switch from full tool schemas
to bridge tools: tool_search, tool_describe, tool_call.

Benefits:
- Agents with many tools (Petraclus: 854) don't overflow context
- Tool schemas only loaded when needed
- Search is semantic, not keyword-based
- Transparent to the agent; same behavior, smaller context

Security:
- tool_search results filtered by governance policy
- tool_call validated against governance before execution
- Scout signals emitted for all bridge tool usage
"""

import json
from typing import List, Optional
from dataclasses import dataclass

from keprix.tools.registry import ToolRegistry
from keprix.security.governance import GovernanceEngine, Verdict


@dataclass
class ToolSearchResult:
    name: str
    description: str
    category: str
    relevance_score: float


class ProgressiveDisclosure:
    """
    Manages progressive tool disclosure based on context budget.

    Threshold: when estimated context usage exceeds TOOL_THRESHOLD,
    replace full tool schemas with bridge tools.
    """

    CONTEXT_THRESHOLD = 0.80    # 80% of context window
    TOKEN_ESTIMATE_CHARS_PER_TOKEN = 4

    def __init__(self, registry: ToolRegistry, governance: GovernanceEngine):
        self.registry = registry
        self.governance = governance

    def should_use_bridge_tools(
        self, context_window_tokens: int, estimated_usage_tokens: int
    ) -> bool:
        """Return True if we should switch to bridge tools to save context."""
        usage_ratio = estimated_usage_tokens / context_window_tokens
        return usage_ratio >= self.CONTEXT_THRESHOLD

    def build_bridge_tool_schemas(self) -> List[dict]:
        """Return only the 3 bridge tool schemas (instead of all tools)."""
        return [
            {
                "name": "tool_search",
                "description": "Search for available tools by name or capability. Use this to find the right tool when you know what you want to do but don't know the tool name.",
                "parameters": {
                    "query": "What you want to do (e.g., 'search the web', 'read a file', 'run a command')",
                    "limit": "Max results (default 5)",
                },
            },
            {
                "name": "tool_describe",
                "description": "Get the full parameter schema for a specific tool. Use this after tool_search when you've found the right tool.",
                "parameters": {
                    "tool_name": "Name of the tool from tool_search results",
                },
            },
            {
                "name": "tool_call",
                "description": "Execute a tool with the given arguments. Use this after tool_describe when you know the parameters.",
                "parameters": {
                    "tool_name": "Name of the tool to execute",
                    "arguments": "JSON object with tool parameters",
                },
            },
        ]

    def search_tools(self, query: str, limit: int = 5) -> List[ToolSearchResult]:
        """
        Semantic search for tools matching a capability description.

        Governance: only returns tools the agent is allowed to use.
        """
        all_tools = self.registry.list_all()
        results = []

        for tool in all_tools:
            # Governance check; only show allowed tools
            verdict, _, _ = self.governance.evaluate(
                action="tool_call",
                context={"tool_name": tool.name},
            )
            if verdict == Verdict.BLOCK:
                continue

            # Simple relevance scoring (in production: use embeddings)
            score = self._relevance_score(query, tool)
            if score > 0:
                results.append(ToolSearchResult(
                    name=tool.name,
                    description=tool.description[:200],
                    category=tool.category or "general",
                    relevance_score=score,
                ))

        # Sort by relevance, return top N
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:limit]

    def describe_tool(self, tool_name: str) -> Optional[dict]:
        """Return full parameter schema for a tool."""
        tool = self.registry.get(tool_name)
        if not tool:
            return None

        # Governance check
        verdict, _, _ = self.governance.evaluate(
            action="tool_call",
            context={"tool_name": tool_name},
        )
        if verdict == Verdict.BLOCK:
            return {"error": "Tool is blocked by governance policy"}

        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters_schema,
        }

    def execute_tool(self, tool_name: str, arguments: dict) -> dict:
        """Execute a tool with validation."""
        tool = self.registry.get(tool_name)
        if not tool:
            return {"error": f"Unknown tool: {tool_name}"}

        # Governance check
        verdict, msg, rules = self.governance.evaluate(
            action="tool_call",
            context={"tool_name": tool_name, "arguments": arguments},
        )
        if verdict == Verdict.BLOCK:
            return {"error": f"Tool blocked by governance: {msg}"}
        if verdict == Verdict.CONFIRM:
            return {"error": "Tool requires confirmation. Please ask the user."}

        # Scout signal
        from keprix.security.scout_client import scout_client, SignalCategory, SignalSeverity
        scout_client.send(
            category=SignalCategory.GOVERNANCE,
            severity=SignalSeverity.INFO,
            action="bridge_tool_call",
            target=f"tool:{tool_name}",
            details={"bridge": True, "governance_rules": rules},
        )

        # Execute
        return tool.execute(**arguments)

    def _relevance_score(self, query: str, tool) -> float:
        """Simple keyword overlap scoring. Replace with embeddings in production."""
        query_words = set(query.lower().split())
        tool_text = f"{tool.name} {tool.description}".lower()
        tool_words = set(tool_text.split())
        overlap = query_words & tool_words
        return len(overlap) / max(len(query_words), 1)
```

### Integration

In the agent loop, before building the system prompt:

```python
# In keprix/agent/prompt_builder.py

from keprix.tools.progressive_disclosure import ProgressiveDisclosure

disclosure = ProgressiveDisclosure(tool_registry, governance_engine)

if disclosure.should_use_bridge_tools(context_window, estimated_usage):
    # Use bridge tools instead of full schemas
    tool_schemas = disclosure.build_bridge_tool_schemas()
    system_prompt += "\n\n## Available Tools\n"
    system_prompt += "You have MANY tools available. Use tool_search to find the right one.\n"
else:
    # Full tool schemas as normal
    tool_schemas = [tool.schema for tool in tool_registry.list_allowed()]
```

### Files

| File | Purpose |
|------|---------|
| `keprix/tools/progressive_disclosure.py` | Bridge tools + context threshold logic |
| `keprix/agent/prompt_builder.py` | Add context threshold check + bridge tool switch |
| `tests/tools/test_progressive_disclosure.py` | Tests |

---

## 5. Acceptance Criteria

### Checkpoint Manager
- [ ] Pre-write checkpoint created before every `write_file`, `patch`, terminal write
- [ ] Governance BLOCK on write triggers auto-rollback
- [ ] `keprix checkpoint list` shows checkpoint history
- [ ] `keprix checkpoint rollback <id>` restores filesystem
- [ ] `keprix checkpoint diff <id>` shows changes
- [ ] Scout command ROLLBACK_TO_CHECKPOINT works
- [ ] Auto-prunes beyond 100 checkpoints
- [ ] Checkpoint directory is git-based, .gitignore restricts to allowed paths

### Mixture of Agents
- [ ] MoA synthesises better answers than any single model (measured by eval)
- [ ] Reference models run in parallel within timeout
- [ ] Input sanitizer runs on prompt before any model call
- [ ] Output guard scans aggregator response
- [ ] Scout signals emitted for synthesis completion
- [ ] Spend limits enforced

### X/Twitter Search
- [ ] Search returns sanitised results
- [ ] API key from credential vault, never in agent context
- [ ] xAI domain in egress allowlist
- [ ] Rate limits enforced (10/min, 100/hour)
- [ ] Scout signals on execution

### Progressive Disclosure
- [ ] Bridge tools activate at 80% context threshold
- [ ] tool_search returns only governance-allowed tools
- [ ] tool_describe returns full schema with governance check
- [ ] tool_call validates against governance before execution
- [ ] Scout signals for all bridge tool usage
- [ ] Transparent to agent; same behavior, smaller context

---

## 6. Summary

| # | Feature | Value | Security Impact |
|---|---------|-------|----------------|
| 1 | Checkpoint Manager | Auto-rollback on bad writes. Operator can undo any agent action. |  Direct; prevents file corruption |
| 2 | Mixture of Agents | Better reasoning on complex tasks. Multi-model consensus. |  Indirect; more model calls = more exposure. Input/output sanitization mitigates. |
| 3 | X/Twitter Search | Search social media. Useful for AbbiS (social selling) and Petraclus (threat intel). |  Direct; another API surface. Credential vault + egress filter mitigate. |
| 4 | Progressive Disclosure | Agents with 854 tools (Petraclus) don't overflow context window. |  Indirect; smaller prompt = harder to inject. Governance gates on every bridge call. |
