"""Safe resolution of on-disk paths for document import and folder sync."""

from __future__ import annotations

import os
from pathlib import Path


DEFAULT_EXTENSIONS = (
    ".md",
    ".markdown",
    ".txt",
    ".rst",
    ".csv",
    ".html",
    ".htm",
    ".pdf",
    ".docx",
)


def allowed_disk_roots() -> list[Path]:
    roots: list[Path] = []
    extra = os.environ.get("KEPRIX_DOCUMENTS_DISK_ROOTS", "")
    for raw in extra.split(","):
        piece = raw.strip()
        if piece:
            roots.append(Path(piece).expanduser().resolve())
    for key in ("KEPRIX_DATA_DIR", "KEPRIX_HOME"):
        value = os.environ.get(key, "").strip()
        if value:
            roots.append(Path(value).expanduser().resolve())
    try:
        from keprix_cli.config import get_keprix_home

        roots.append(Path(get_keprix_home()).resolve())
    except Exception:
        pass
    roots.extend(
        [
            (Path.home() / ".keprix").resolve(),
            Path("/data/keprix").resolve(),
            Path("/home/keprix/.keprix").resolve(),
        ]
    )
    # Unique while preserving order
    seen: set[str] = set()
    out: list[Path] = []
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        out.append(root)
    return out


def resolve_allowed_path(raw_path: str, *, must_exist: bool = True) -> Path:
    if not raw_path or not str(raw_path).strip():
        raise ValueError("Path is required")
    path = Path(str(raw_path).strip()).expanduser()
    try:
        resolved = path.resolve(strict=must_exist)
    except FileNotFoundError as exc:
        raise ValueError(f"Path does not exist: {path}") from exc
    allowed = False
    for root in allowed_disk_roots():
        try:
            resolved.relative_to(root)
            allowed = True
            break
        except ValueError:
            continue
    if not allowed:
        roots = ", ".join(str(r) for r in allowed_disk_roots()[:6])
        raise ValueError(
            f"Path must be under an allowed documents root ({roots}). "
            "Set KEPRIX_DOCUMENTS_DISK_ROOTS to add more roots."
        )
    return resolved


def iter_disk_files(
    folder: Path,
    *,
    recursive: bool = True,
    extensions: list[str] | None = None,
) -> list[Path]:
    exts = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in (extensions or DEFAULT_EXTENSIONS)}
    files: list[Path] = []
    if recursive:
        candidates = folder.rglob("*")
    else:
        candidates = folder.glob("*")
    for item in candidates:
        if not item.is_file():
            continue
        if item.suffix.lower() not in exts:
            continue
        files.append(item)
    files.sort(key=lambda p: str(p).lower())
    return files


def read_path_as_text(path: Path) -> tuple[str, str]:
    """Return (title, content) from a disk file."""
    raw = path.read_bytes()
    name = path.name
    lower = name.lower()
    title = path.stem
    if lower.endswith((".md", ".markdown", ".txt", ".rst", ".csv", ".html", ".htm")):
        return title, raw.decode("utf-8", errors="replace")
    if lower.endswith(".docx"):
        try:
            import io

            import docx  # type: ignore

            document = docx.Document(io.BytesIO(raw))
            return title, "\n".join(p.text for p in document.paragraphs)
        except Exception as exc:
            raise ValueError(f"Could not parse DOCX: {exc}") from exc
    if lower.endswith(".pdf"):
        try:
            import io

            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(raw))
            return title, "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:
            raise ValueError(f"Could not parse PDF: {exc}") from exc
    return title, raw.decode("utf-8", errors="replace")
