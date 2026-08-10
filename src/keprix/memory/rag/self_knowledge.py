"""Curated Keprix self-knowledge corpus for RAG.

Indexes product capabilities, workspace modules, toolsets, and key docs into
the shared system RAG user so every workspace can retrieve "what Keprix is".
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from keprix.memory.rag.codebase_indexer import (
    CODEBASE_SOURCE_TYPE,
    CodebaseRagIndexer,
    default_codebase_root,
)
from keprix.memory.rag.indexer import RagIndexer
from keprix.security.context_quarantine import wrap_context

if TYPE_CHECKING:
    from keprix.memory.rag.retriever import RagRetriever

SELF_KNOWLEDGE_SOURCE_TYPE = "keprix_self"
SELF_KNOWLEDGE_USER_ID = (
    os.getenv("KEPRIX_SELF_KNOWLEDGE_USER_ID", "__keprix_self__").strip()
    or "__keprix_self__"
)

# Curated docs that teach product behaviour (not the whole monorepo).
_SELF_DOC_PATHS: tuple[str, ...] = (
    "README.md",
    "AGENTS.md",
    "docs/features/agent-os-overview.md",
    "docs/features/chat.md",
    "docs/features/self-coding-agent.md",
    "docs/features/memory.md",
    "docs/features/rag-pipelines.md",
    "docs/features/workspace.md",
    "docs/features/tui.md",
    "docs/features/playbooks.md",
    "docs/features/vault.md",
    "docs/features/hub-and-packs.md",
    "docs/features/structured-workspace-memory.md",
    "docs/features/graphiti-bridge.md",
    "docs/features/skill-first-execution.md",
    "docs/features/mcp-connector-first.md",
    "docs/features/colleague-memory-continuity.md",
    "docs/features/agent-context-task-state.md",
    "docs/features/ai-transparency-sgi.md",
    "docs/features/agentic-crm.md",
    "docs/features/crm-compliance.md",
    "docs/architecture/standalone-lead-outreach-capability-matrix.md",
    "docs/architecture/standalone-lead-outreach-contract.md",
    "docs/architecture/standalone-lead-outreach-ops.md",
    "docs/architecture/standalone-lead-outreach-scheduler.md",
    "docs/architecture/standalone-lead-outreach-delivery.md",
    "docs/architecture/standalone-lead-outreach-mailbox.md",
    "docs/architecture/standalone-lead-outreach-funnel.md",
    "docs/architecture/document-vault-capability-matrix.md",
    "docs/architecture/document-vault-contract.md",
    "docs/architecture/document-vault-ownership-and-migration.md",
    "docs/architecture/document-vault-formats.md",
    "docs/architecture/document-vault-agent-tools.md",
    "docs/architecture/document-vault-channel-ops.md",
    "docs/architecture/document-vault-search-ops.md",
    "docs/architecture/document-vault-google-drive.md",
    "docs/features/document-vault.md",
    "docs/operations/document-vault-runbook.md",
    "docs/features/customer-concierge.md",
    "docs/architecture/customer-concierge-v1-baseline-audit.md",
    "docs/architecture/customer-concierge-capability-matrix.md",
    "docs/features/customer-concierge-owner-live-verification.md",
    "docs/operations/customer-concierge-runbook.md",
    "docs/operations/customer-concierge-release-manifest.md",
    "docs/features/crm-integrations.md",
    "docs/features/soft-wall-safety.md",
    "docs/features/soft-wall-enroll-vical.md",
    "docs/features/companies-house.md",
    "docs/features/email.md",
    "docs/features/navigation-and-roles.md",
    "docs/troubleshooting/index.md",
    "docs/troubleshooting/ui-navigation.md",
    "docs/troubleshooting/soft-wall-and-outreach.md",
    "docs/troubleshooting/standalone-lead-outreach.md",
    "docs/troubleshooting/agentic-crm.md",
    "docs/troubleshooting/companies-house.md",
    "docs/troubleshooting/chat-and-tools.md",
    "docs/troubleshooting/self-knowledge.md",
    "docs/troubleshooting/propreneur-sidecar.md",
    "docs/troubleshooting/known-issues.md",
    "docs/universal-sidecar/README.md",
    "docs/universal-sidecar/troubleshooting.md",
    "docs/universal-sidecar/self-knowledge-blurb.md",
    "docs/propreneur-sidecar/README.md",
    "docs/architecture/propreneur-approvals-idempotency-events.md",
    "docs/architecture/propreneur-connector-trusted-identity.md",
    "docs/architecture/propreneur-e2e-testing.md",
    "docs/architecture/propreneur-crud-remediation-gap-report.md",
    "docs/architecture/propreneur-agent-contract-compatibility.md",
    "docs/self-knowledge/propreneur-product-pack-honesty.md",
    "docs/self-knowledge/parity/agentic-crm-tools.md",
    "docs/self-knowledge/parity/agentic-crm-routes.md",
    "domain-packs/propreneur/docs/propreneur-aiva-capability-guidance.md",
    "docs/getting-started/cloud-deploy.md",
    "docs/getting-started/first-run.md",
    "src/keprix/skills/autonomous-ai-agents/keprix-agent/SKILL.md",
)


@dataclass(frozen=True)
class SelfKnowledgeIndexStats:
    docs_indexed: int = 0
    doc_chunks: int = 0
    capability_chunks: int = 0
    codebase_files: int = 0
    codebase_chunks: int = 0
    user_id: str = SELF_KNOWLEDGE_USER_ID
    root: str = ""

    @property
    def total_chunks(self) -> int:
        return self.doc_chunks + self.capability_chunks + self.codebase_chunks

    def to_dict(self) -> dict[str, int | str]:
        return {
            "docs_indexed": self.docs_indexed,
            "doc_chunks": self.doc_chunks,
            "capability_chunks": self.capability_chunks,
            "codebase_files": self.codebase_files,
            "codebase_chunks": self.codebase_chunks,
            "user_id": self.user_id,
            "root": self.root,
            "total_chunks": self.total_chunks,
        }


def resolve_self_knowledge_root() -> Path:
    try:
        from keprix.api.codebase_context import resolve_repo_root

        root = resolve_repo_root()
        if root is not None:
            return root
    except Exception:
        pass
    return default_codebase_root()


def _read_text(path: Path, *, max_chars: int = 80_000) -> str | None:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "\n\n[truncated]"
    return text


def build_capabilities_document(root: Path | None = None) -> str:
    """Snapshot of what Keprix ships: modules, toolsets, skills, surfaces."""
    base = (root or resolve_self_knowledge_root()).resolve()
    sections: list[str] = [
        "Keprix self-knowledge: product capabilities inventory",
        "",
        "Keprix is a self-hosted MIT-licensed AI agent OS.",
        "Surfaces: web chat, admin dashboard, CLI (`keprix`), TUI, messaging gateway, "
        "REST API, Python SDK.",
        "Core loop: tools, skills, memory/RAG, channels, mutation (self-coding), cron, MCP.",
        "",
    ]

    try:
        from keprix.upgrade.gui_catalog import list_gui_modules

        modules = list_gui_modules()
        sections.append("## Workspace modules")
        for module in modules[:80]:
            href = getattr(module, "gui_href", None) or "cli/api"
            status = getattr(module, "gui_status", "unknown")
            sections.append(
                f"- {module.name} ({module.id}): {module.description} "
                f"[route={href}; status={status}; category={module.category}]"
            )
        sections.append("")
    except Exception as exc:
        sections.append(f"## Workspace modules\nUnavailable ({exc}).\n")

    try:
        from keprix.toolsets import get_all_toolsets

        sections.append("## Toolsets")
        for name, meta in sorted(get_all_toolsets().items()):
            tools = meta.get("tools") if isinstance(meta, dict) else None
            desc = meta.get("description", "") if isinstance(meta, dict) else ""
            tool_list = ", ".join(tools[:25]) if isinstance(tools, list) else ""
            extra = (
                f" (+{len(tools) - 25} more)"
                if isinstance(tools, list) and len(tools) > 25
                else ""
            )
            sections.append(f"- {name}: {desc} tools=[{tool_list}{extra}]")
        sections.append("")
    except Exception as exc:
        sections.append(f"## Toolsets\nUnavailable ({exc}).\n")

    skills_root = base / "src" / "keprix" / "skills"
    if skills_root.is_dir():
        sections.append("## Bundled skills (sample)")
        count = 0
        for skill_md in sorted(skills_root.rglob("SKILL.md")):
            try:
                rel = skill_md.relative_to(base).as_posix()
            except ValueError:
                continue
            name = skill_md.parent.name
            sections.append(f"- {name}: {rel}")
            count += 1
            if count >= 120:
                sections.append("- ... additional skills omitted")
                break
        sections.append("")

    docs_features = base / "docs" / "features"
    if docs_features.is_dir():
        sections.append("## Feature docs index")
        for path in sorted(docs_features.glob("*.md"))[:100]:
            sections.append(f"- docs/features/{path.name}")
        sections.append("")

    sections.extend(
        [
            "## How to answer questions about Keprix",
            "- Prefer this inventory plus retrieved RAG chunks over guessing.",
            "- Never reveal secrets, .env values, or credential files.",
            "- Point users to Dashboard settings, CLI, or docs paths when configuration "
            "is required.",
            "- Mutation/self-coding is a real feature: synthesize tools when none fit, "
            "sandbox, owner approval.",
            "- Optional £1 Buy me a coffee donation is voluntary community support, "
            "never required.",
        ]
    )
    return "\n".join(sections).strip()


class SelfKnowledgeIndexer:
    """Index curated docs + capabilities + codebase into the shared RAG user."""

    def __init__(self, rag_indexer: RagIndexer | None = None, *, root: Path | None = None) -> None:
        self.rag_indexer = rag_indexer or RagIndexer()
        self.root = (root or resolve_self_knowledge_root()).resolve()

    async def index(
        self,
        *,
        include_codebase: bool = True,
        include_docs: bool = True,
        include_capabilities: bool = True,
        max_files: int = 2000,
        max_file_bytes: int = 250_000,
        user_id: str = SELF_KNOWLEDGE_USER_ID,
    ) -> SelfKnowledgeIndexStats:
        docs_indexed = 0
        doc_chunks = 0
        capability_chunks = 0
        codebase_files = 0
        codebase_chunks = 0

        if include_capabilities:
            capabilities = build_capabilities_document(self.root)
            capability_chunks = await self.rag_indexer.ingest(
                user_id=user_id,
                source_type=SELF_KNOWLEDGE_SOURCE_TYPE,
                source_id="capabilities/inventory",
                content=capabilities,
            )

        if include_docs:
            for rel in _SELF_DOC_PATHS:
                path = self.root / rel
                text = _read_text(path)
                if not text:
                    continue
                document = f"Keprix product doc: {rel}\n\n{text}"
                doc_chunks += await self.rag_indexer.ingest(
                    user_id=user_id,
                    source_type=SELF_KNOWLEDGE_SOURCE_TYPE,
                    source_id=f"doc/{rel}",
                    content=document,
                )
                docs_indexed += 1

        if include_codebase:
            stats = await CodebaseRagIndexer(self.rag_indexer, root=self.root).index(
                user_id=user_id,
                max_files=max_files,
                max_file_bytes=max_file_bytes,
            )
            codebase_files = stats.files_indexed
            codebase_chunks = stats.chunks

        return SelfKnowledgeIndexStats(
            docs_indexed=docs_indexed,
            doc_chunks=doc_chunks,
            capability_chunks=capability_chunks,
            codebase_files=codebase_files,
            codebase_chunks=codebase_chunks,
            user_id=user_id,
            root=str(self.root),
        )


async def retrieve_self_knowledge(
    query: str,
    *,
    limit: int = 8,
    hybrid: bool = True,
    user_id: str = SELF_KNOWLEDGE_USER_ID,
    retriever: RagRetriever | None = None,
) -> list[dict[str, Any]]:
    from keprix.memory.rag.retriever import RagRetriever

    engine = retriever or RagRetriever()
    source_types = [SELF_KNOWLEDGE_SOURCE_TYPE, CODEBASE_SOURCE_TYPE]
    if hybrid:
        return await engine.hybrid_search(user_id, query, limit=limit, source_types=source_types)
    return await engine.search(user_id, query, limit=limit, source_types=source_types)


def format_self_knowledge_context(results: list[dict[str, Any]], *, max_chars: int = 6_000) -> str:
    if not results:
        return ""
    lines = [
        "## Retrieved Keprix self-knowledge (RAG)",
        "Use these chunks when answering about Keprix capabilities, modules, or codebase.",
        "",
    ]
    used = 0
    for idx, item in enumerate(results, start=1):
        source = str(item.get("source") or "unknown")
        content = str(item.get("content") or "").strip()
        trust = str(item.get("trust") or "trusted").strip().lower()
        score = item.get("score")
        header = f"### Hit {idx}: {source}"
        if isinstance(score, int | float):
            header += f" (score={score:.3f})"
        if trust == "quarantined":
            content = wrap_context(content, source=source).to_prompt_block()
        block = f"{header}\n{content}\n"
        if used + len(block) > max_chars:
            remaining = max_chars - used
            if remaining > 200:
                lines.append(block[:remaining].rstrip() + "\n[truncated]")
            break
        lines.append(block)
        used += len(block)
    return "\n".join(lines).strip()
