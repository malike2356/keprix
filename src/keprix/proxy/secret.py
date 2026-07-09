"""In-memory secret wrapper; zeroize on drop."""

from __future__ import annotations


class Secret:
    """Credential value that must not appear in logs or repr."""

    __slots__ = ("_buf",)

    def __init__(self, value: str) -> None:
        self._buf = bytearray(value.encode("utf-8"))

    def expose(self) -> str:
        return self._buf.decode("utf-8")

    def clear(self) -> None:
        for index in range(len(self._buf)):
            self._buf[index] = 0

    def __del__(self) -> None:
        self.clear()

    def __repr__(self) -> str:
        return "Secret(<redacted>)"

    def __str__(self) -> str:
        return "<redacted>"
