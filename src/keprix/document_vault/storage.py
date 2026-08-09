"""Content storage adapters for Document Vault (Prompt 646).

Local CE adapter stores blobs under a managed root. Object storage is optional.
Never treat a user-supplied host path as the storage root without sanitizing
into the managed locator scheme (``vault://…``).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote, unquote


class StorageAdapter(Protocol):
    def put(self, locator: str, data: bytes) -> str: ...

    def get(self, locator: str) -> bytes: ...

    def delete(self, locator: str) -> None: ...

    def exists(self, locator: str) -> bool: ...


def build_locator(*, workspace_id: str, item_id: str, revision: int) -> str:
    ws = quote(str(workspace_id), safe="")
    iid = quote(str(item_id), safe="")
    return f"vault://{ws}/{iid}/r{int(revision)}"


def parse_locator(locator: str) -> tuple[str, str, int]:
    if not str(locator or "").startswith("vault://"):
        raise ValueError("path_traversal")
    rest = locator[len("vault://") :]
    parts = rest.split("/")
    if len(parts) != 3 or not parts[2].startswith("r"):
        raise ValueError("path_traversal")
    ws = unquote(parts[0])
    iid = unquote(parts[1])
    rev = int(parts[2][1:])
    if ".." in ws or ".." in iid or "/" in ws or "\\" in ws:
        raise ValueError("path_traversal")
    return ws, iid, rev


class LocalStorageAdapter:
    """Community Edition filesystem blobs under a managed data directory."""

    def __init__(self, root: Path | None = None) -> None:
        if root is None:
            base = Path(
                os.environ.get("KEPRIX_DOCUMENT_VAULT_STORAGE")
                or os.environ.get("KEPRIX_DATA_DIR")
                or (Path.home() / ".keprix")
            )
            root = Path(base) / "document-vault-blobs"
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, locator: str) -> Path:
        ws, iid, rev = parse_locator(locator)
        path = (self.root / ws / iid / f"r{rev}.bin").resolve()
        if not str(path).startswith(str(self.root)):
            raise ValueError("path_traversal")
        return path

    def put(self, locator: str, data: bytes) -> str:
        path = self._path_for(locator)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return locator

    def get(self, locator: str) -> bytes:
        path = self._path_for(locator)
        if not path.is_file():
            raise FileNotFoundError(locator)
        return path.read_bytes()

    def delete(self, locator: str) -> None:
        path = self._path_for(locator)
        if path.is_file():
            path.unlink()

    def exists(self, locator: str) -> bool:
        try:
            return self._path_for(locator).is_file()
        except ValueError:
            return False


class ObjectStorageAdapter:
    """Optional S3-compatible adapter (requires boto3 + bucket env).

    Falls back to raising ``not_configured`` when credentials/bucket missing.
    """

    def __init__(self) -> None:
        self.bucket = (os.environ.get("KEPRIX_DOCUMENT_VAULT_S3_BUCKET") or "").strip()
        self.prefix = (os.environ.get("KEPRIX_DOCUMENT_VAULT_S3_PREFIX") or "vault").strip()
        self._client = None
        if self.bucket:
            try:
                import boto3  # type: ignore

                self._client = boto3.client(
                    "s3",
                    endpoint_url=os.environ.get("KEPRIX_DOCUMENT_VAULT_S3_ENDPOINT") or None,
                    region_name=os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION"),
                )
            except Exception:
                self._client = None

    def _key(self, locator: str) -> str:
        ws, iid, rev = parse_locator(locator)
        return f"{self.prefix}/{ws}/{iid}/r{rev}.bin"

    def put(self, locator: str, data: bytes) -> str:
        if not self._client or not self.bucket:
            raise RuntimeError("not_configured")
        self._client.put_object(Bucket=self.bucket, Key=self._key(locator), Body=data)
        return locator

    def get(self, locator: str) -> bytes:
        if not self._client or not self.bucket:
            raise RuntimeError("not_configured")
        obj = self._client.get_object(Bucket=self.bucket, Key=self._key(locator))
        return obj["Body"].read()

    def delete(self, locator: str) -> None:
        if not self._client or not self.bucket:
            raise RuntimeError("not_configured")
        self._client.delete_object(Bucket=self.bucket, Key=self._key(locator))

    def exists(self, locator: str) -> bool:
        if not self._client or not self.bucket:
            return False
        try:
            self._client.head_object(Bucket=self.bucket, Key=self._key(locator))
            return True
        except Exception:
            return False


def resolve_storage_adapter(*, root: Path | None = None) -> Any:
    mode = (os.environ.get("KEPRIX_DOCUMENT_VAULT_STORAGE_MODE") or "local").strip().lower()
    if mode in {"s3", "object", "object_storage"}:
        adapter = ObjectStorageAdapter()
        if adapter._client and adapter.bucket:
            return adapter
    return LocalStorageAdapter(root=root)
