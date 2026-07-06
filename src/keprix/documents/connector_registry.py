"""Document source connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from keprix.documents.parser import parse_document


@dataclass
class ConnectorDocument:
    filename: str
    source_type: str
    text: str
    metadata: dict[str, Any]


class DocumentConnector(ABC):
    name: str

    @abstractmethod
    async def load(self, **kwargs: Any) -> ConnectorDocument:
        ...


class FileConnector(DocumentConnector):
    name = "file"

    async def load(self, **kwargs: Any) -> ConnectorDocument:
        filename = str(kwargs["filename"])
        content = kwargs["content"]
        parsed = parse_document(filename=filename, content=content)
        return ConnectorDocument(
            filename=parsed["filename"],
            source_type=parsed["source_type"],
            text=parsed["text"],
            metadata={"connector": self.name},
        )


class TextConnector(DocumentConnector):
    name = "text"

    async def load(self, **kwargs: Any) -> ConnectorDocument:
        text = str(kwargs.get("text") or "")
        return ConnectorDocument(
            filename=str(kwargs.get("filename") or "inline.txt"),
            source_type="plaintext",
            text=text,
            metadata={"connector": self.name},
        )


class UrlConnector(DocumentConnector):
    name = "url"

    async def load(self, **kwargs: Any) -> ConnectorDocument:
        url = str(kwargs["url"])
        try:
            import httpx
        except ImportError as exc:
            raise ImportError("URL connector requires httpx") from exc
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.text
        filename = url.rstrip("/").split("/")[-1] or "page.html"
        parsed = parse_document(filename=filename, content=content)
        return ConnectorDocument(
            filename=parsed["filename"],
            source_type=parsed["source_type"],
            text=parsed["text"],
            metadata={"connector": self.name, "url": url},
        )


_CONNECTORS: dict[str, DocumentConnector] = {
    "file": FileConnector(),
    "text": TextConnector(),
    "url": UrlConnector(),
}


def get_connector(name: str) -> DocumentConnector:
    connector = _CONNECTORS.get(name)
    if connector is None:
        raise KeyError(name)
    return connector


def list_connectors() -> list[str]:
    return list(_CONNECTORS.keys())
