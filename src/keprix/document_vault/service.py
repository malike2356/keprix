"""Document Vault service: content + metadata orchestration (Prompt 646)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keprix.document_vault.flags import load_flags
from keprix.document_vault.models import VaultError, format_to_kind, sha256_bytes, sha256_text
from keprix.document_vault.storage import build_locator, resolve_storage_adapter
from keprix.document_vault.store import DocumentVaultStore, get_document_vault_store


class DocumentVaultService:
    def __init__(
        self,
        store: DocumentVaultStore | None = None,
        storage: Any | None = None,
    ) -> None:
        self.store = store or get_document_vault_store()
        self.storage = storage or resolve_storage_adapter()

    def require_enabled(self) -> None:
        if not load_flags().enabled:
            raise VaultError("not_configured", "KEPRIX_DOCUMENT_VAULT_ENABLED is off")

    def create_folder(
        self,
        workspace_id: str,
        name: str,
        *,
        parent_id: str | None = None,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        return self.store.create_item(
            workspace_id,
            kind="folder",
            name=name,
            parent_id=parent_id,
            actor_id=actor_id,
        )

    def create_text_item(
        self,
        workspace_id: str,
        name: str,
        content: str,
        *,
        kind: str = "markdown",
        parent_id: str | None = None,
        actor_id: str | None = None,
        item_id: str | None = None,
    ) -> dict[str, Any]:
        data = content.encode("utf-8")
        item = self.store.create_item(
            workspace_id,
            kind=kind,
            name=name,
            parent_id=parent_id,
            actor_id=actor_id,
            item_id=item_id,
            byte_size=0,
            checksum=None,
            initial_revision=0,
        )
        return self.write_content(
            workspace_id,
            item["id"],
            data,
            expected_revision=0,
            actor_id=actor_id,
            change_summary="create",
        )

    def write_content(
        self,
        workspace_id: str,
        item_id: str,
        data: bytes,
        *,
        expected_revision: int | None = None,
        actor_id: str | None = None,
        change_summary: str | None = None,
    ) -> dict[str, Any]:
        item = self.store.get_item(workspace_id, item_id, include_trashed=False)
        if not item:
            raise VaultError("not_found")
        if item["kind"] == "folder":
            raise VaultError("unsupported_kind", "folders have no content blob")
        next_rev = int(item.get("current_revision") or 0) + 1
        locator = build_locator(workspace_id=workspace_id, item_id=item_id, revision=next_rev)
        self.storage.put(locator, data)
        return self.store.update_item(
            workspace_id,
            item_id,
            expected_revision=expected_revision,
            storage_locator=locator,
            byte_size=len(data),
            checksum=sha256_bytes(data),
            bump_revision=True,
            change_summary=change_summary or "write",
            actor_id=actor_id,
        )

    def append_text(
        self,
        workspace_id: str,
        item_id: str,
        text: str,
        *,
        expected_revision: int | None = None,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        current = self.read_bytes(workspace_id, item_id)
        merged = current + text.encode("utf-8")
        return self.write_content(
            workspace_id,
            item_id,
            merged,
            expected_revision=expected_revision,
            actor_id=actor_id,
            change_summary="append",
        )

    def read_bytes(self, workspace_id: str, item_id: str) -> bytes:
        item = self.store.get_item(workspace_id, item_id, include_trashed=True)
        if not item:
            raise VaultError("not_found")
        if item["workspace_id"] != workspace_id:
            raise VaultError("workspace_mismatch")
        locator = item.get("storage_locator")
        if not locator:
            return b""
        try:
            return self.storage.get(str(locator))
        except FileNotFoundError:
            return b""

    def read_text(self, workspace_id: str, item_id: str) -> str:
        return self.read_bytes(workspace_id, item_id).decode("utf-8", errors="replace")

    def restore_revision(
        self,
        workspace_id: str,
        item_id: str,
        revision: int,
        *,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        # Copy blob from old revision locator into a new revision via update
        revs = self.store.list_revisions(workspace_id, item_id)
        match = next((r for r in revs if int(r.get("revision") or 0) == int(revision)), None)
        if not match:
            raise VaultError("not_found", "revision not found")
        locator = match.get("storage_locator")
        data = self.storage.get(str(locator)) if locator else b""
        item = self.store.get_item(workspace_id, item_id, include_trashed=False)
        if not item:
            raise VaultError("not_found")
        return self.write_content(
            workspace_id,
            item_id,
            data,
            expected_revision=int(item.get("current_revision") or 0),
            actor_id=actor_id,
            change_summary=f"restore revision {revision}",
        )

    def import_bytes(
        self,
        workspace_id: str,
        data: bytes,
        *,
        filename: str,
        declared_mime: str = "",
        parent_id: str | None = None,
        actor_id: str | None = None,
        keep_original: bool = True,
    ) -> dict[str, Any]:
        """Import bytes. Original kept as binary_upload; derived editable item created."""
        from keprix.document_vault.formats.engines import import_bytes_to_text

        converted = import_bytes_to_text(data, filename=filename, declared_mime=declared_mime)
        original = None
        if keep_original:
            original = self.store.create_item(
                workspace_id,
                kind="binary_upload",
                name=filename or "upload.bin",
                parent_id=parent_id,
                actor_id=actor_id,
                mime_type=(converted.get("validation") or {}).get("sniff", {}).get("detected_mime"),
                metadata={
                    "role": "import_original",
                    "format_id": converted.get("format_id"),
                    "source_checksum": converted.get("source_checksum"),
                },
            )
            original = self.write_content(
                workspace_id,
                original["id"],
                data,
                expected_revision=0,
                actor_id=actor_id,
                change_summary="import_original",
            )

        if converted.get("binary") is not None and not converted.get("text"):
            # Image / binary-only: original is the item
            job = self.store.enqueue_job(
                workspace_id,
                "import_normalize",
                item_id=(original or {}).get("id"),
                idempotency_key=f"import:{converted.get('source_checksum')}",
                payload={"format_id": converted.get("format_id"), "warnings": converted.get("warnings")},
            )
            return {
                "ok": True,
                "original": original,
                "derived": original,
                "conversion": converted,
                "job": job,
            }

        derived = self.create_text_item(
            workspace_id,
            _derived_name(filename, converted.get("kind") or "markdown"),
            str(converted.get("text") or ""),
            kind=str(converted.get("kind") or "markdown"),
            parent_id=parent_id,
            actor_id=actor_id,
        )
        # Provenance on derived
        derived = self.store.update_item(
            workspace_id,
            derived["id"],
            metadata={
                **(derived.get("metadata") or {}),
                "imported_from": (original or {}).get("id"),
                "source_filename": filename,
                "format_id": converted.get("format_id"),
                "fidelity": converted.get("fidelity"),
                "converter_version": converted.get("converter_version"),
                "warnings": converted.get("warnings") or [],
                "source_checksum": converted.get("source_checksum"),
            },
            actor_id=actor_id,
        )
        if original:
            self.store.update_item(
                workspace_id,
                original["id"],
                metadata={
                    **(original.get("metadata") or {}),
                    "derived_item_id": derived["id"],
                },
                actor_id=actor_id,
            )
        job = self.store.enqueue_job(
            workspace_id,
            "import_normalize",
            item_id=derived["id"],
            idempotency_key=f"import:{converted.get('source_checksum')}:{derived['id']}",
            payload={
                "original_id": (original or {}).get("id"),
                "format_id": converted.get("format_id"),
                "warnings": converted.get("warnings"),
                "fidelity": converted.get("fidelity"),
            },
        )
        return {
            "ok": True,
            "original": original,
            "derived": derived,
            "conversion": converted,
            "job": job,
            "source_preserved": True,
        }

    def export_item(
        self,
        workspace_id: str,
        item_id: str,
        *,
        target_format: str,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        from keprix.document_vault.formats.engines import export_text

        item = self.store.get_item(workspace_id, item_id, include_trashed=False)
        if not item:
            raise VaultError("not_found")
        if item["kind"] == "folder":
            raise VaultError("unsupported_kind", "cannot export folder")
        text = self.read_text(workspace_id, item_id)
        result = export_text(
            text,
            source_kind=str(item.get("kind") or "markdown"),
            target_format=target_format,
            title=str(item.get("name") or "Export"),
        )
        job = self.store.enqueue_job(
            workspace_id,
            "export",
            item_id=item_id,
            idempotency_key=f"export:{item_id}:{target_format}:{item.get('current_revision')}",
            payload={
                "target_format": target_format,
                "source_revision": item.get("current_revision"),
                "warnings": result.get("warnings"),
                "fidelity": result.get("fidelity"),
            },
        )
        return {
            "ok": True,
            "item_id": item_id,
            "source_revision": item.get("current_revision"),
            "export": result,
            "job": job,
        }

    def generate_pdf_artifact(
        self,
        workspace_id: str,
        item_id: str,
        *,
        actor_id: str | None = None,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a PDF sibling artifact linked to source revision; never replace source."""
        from keprix.document_vault.formats.engines import render_pdf_bytes

        source = self.store.get_item(workspace_id, item_id, include_trashed=False)
        if not source:
            raise VaultError("not_found")
        if source["kind"] == "folder":
            raise VaultError("unsupported_kind", "cannot PDF a folder")
        source_revision = int(source.get("current_revision") or 0)
        text = self.read_text(workspace_id, item_id)
        pdf = render_pdf_bytes(text, title=str(source.get("name") or "Document"), source_kind=str(source["kind"]))
        artifact = self.store.create_item(
            workspace_id,
            kind="pdf",
            name=f"{source.get('name') or 'Document'}.pdf",
            parent_id=parent_id if parent_id is not None else source.get("parent_id"),
            actor_id=actor_id,
            metadata={
                "role": "generated_pdf",
                "source_item_id": item_id,
                "source_revision": source_revision,
                "converter_version": "keprix-document-vault-formats/1.0.0",
                "engine": pdf.get("engine"),
                "warnings": pdf.get("warnings") or [],
                "fidelity": pdf.get("fidelity"),
            },
        )
        artifact = self.write_content(
            workspace_id,
            artifact["id"],
            pdf["data"],
            expected_revision=0,
            actor_id=actor_id,
            change_summary="generate_pdf",
        )
        # Prove source content was not replaced by the PDF artifact.
        source_after = self.store.get_item(workspace_id, item_id)
        if not source_after or source_after.get("checksum") != source.get("checksum"):
            raise VaultError("conflict", "source checksum changed during PDF generation")
        if int(source_after.get("current_revision") or 0) != source_revision:
            raise VaultError("conflict", "source revision changed during PDF generation")
        job = self.store.enqueue_job(
            workspace_id,
            "export_pdf",
            item_id=item_id,
            idempotency_key=f"pdf:{item_id}:{source_revision}",
            payload={
                "artifact_id": artifact["id"],
                "source_revision": source_revision,
                "warnings": pdf.get("warnings"),
            },
        )
        return {
            "ok": True,
            "source": source_after,
            "artifact": artifact,
            "job": job,
            "source_unchanged": True,
        }


def _derived_name(filename: str, kind: str) -> str:
    from pathlib import Path

    stem = Path(filename or "import").stem or "import"
    ext = {
        "markdown": ".md",
        "html": ".html",
        "plain_text": ".txt",
        "spreadsheet": ".csv",
        "rich_document": ".html",
    }.get(kind, ".txt")
    return f"{stem}{ext}"


def get_document_vault_service(
    store: DocumentVaultStore | None = None,
    storage_root: Path | None = None,
) -> DocumentVaultService:
    storage = resolve_storage_adapter(root=storage_root) if storage_root else None
    return DocumentVaultService(store=store, storage=storage)
