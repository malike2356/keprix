"""Minimal text PDF generation without external dependencies."""

from __future__ import annotations


def _pdf_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", "")
    )


def render_text_pdf(title: str, content: str, *, max_lines: int = 500) -> bytes:
    """Render plain text as a valid PDF 1.4 document."""
    lines: list[str] = []
    if title.strip():
        lines.append(title.strip())
        lines.append("")
    for line in content.splitlines():
        if not line.strip():
            lines.append("")
            continue
        while len(line) > 96:
            lines.append(line[:96])
            line = line[96:]
        lines.append(line)
        if len(lines) >= max_lines:
            lines.append("[truncated]")
            break

    y = 780
    stream_parts = ["BT", "/F1 11 Tf", "72 780 Td"]
    for line in lines:
        if y < 72:
            break
        escaped = _pdf_escape(line) or " "
        stream_parts.append(f"({escaped}) Tj")
        stream_parts.append("0 -14 Td")
        y -= 14
    stream_parts.append("ET")
    stream = "\n".join(stream_parts).encode("latin-1", errors="replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    )
    objects.append(
        b"4 0 obj\n<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"\nendstream\nendobj\n"
    )
    objects.append(
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return bytes(pdf)
