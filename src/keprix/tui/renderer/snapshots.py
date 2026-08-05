"""Renderer snapshot helpers."""


def normalize_snapshot(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def terminal_degradation_snapshot(lines: list[str], *, truecolor: bool = True) -> str:
    prefix = "truecolor" if truecolor else "basic"
    return normalize_snapshot(f"[{prefix}]\n" + "\n".join(lines))


__all__ = ["normalize_snapshot", "terminal_degradation_snapshot"]
