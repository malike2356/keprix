"""Message format translator: normalise provider-specific message shapes."""

from __future__ import annotations

from typing import Any


class MessageTranslator:
    """Convert between provider message formats.

    Different LLM APIs have subtly different message conventions:
      - OpenAI / most providers: {"role": "user", "content": "..."}
      - Anthropic (native): {"role": "user", "content": [{"type": "text", "text": "..."}]}
      - Gemini (native): {"parts": [{"text": "..."}], "role": "user"}
      - System message placement varies (OpenAI: in messages list; Anthropic: top-level param)

    The internal keprix format is OpenAI-compatible (messages list with role/content).
    This translator normalises incoming messages to the internal format and converts
    outgoing messages to whatever shape a specific provider expects.
    """

    # ------------------------------------------------------------------
    # Normalise to internal (OpenAI-compat) format
    # ------------------------------------------------------------------

    def from_anthropic(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert Anthropic native content blocks to flat string content."""
        result = []
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, list):
                text = " ".join(
                    part.get("text", "") for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                )
                result.append({**msg, "content": text})
            else:
                result.append(msg)
        return result

    def from_gemini(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert Gemini-style {parts, role} to {role, content}."""
        result = []
        for msg in messages:
            if "parts" in msg:
                text = " ".join(
                    p.get("text", "") for p in msg["parts"] if isinstance(p, dict)
                )
                result.append({"role": msg.get("role", "user"), "content": text})
            else:
                result.append(msg)
        return result

    # ------------------------------------------------------------------
    # Convert from internal format to provider-specific
    # ------------------------------------------------------------------

    def to_anthropic(
        self,
        messages: list[dict[str, Any]],
    ) -> tuple[str, list[dict[str, Any]]]:
        """Return (system_prompt, messages_without_system) for Anthropic API."""
        system_parts = []
        filtered = []
        for msg in messages:
            if msg.get("role") == "system":
                system_parts.append(str(msg.get("content", "")))
            else:
                content = msg.get("content", "")
                if isinstance(content, str):
                    filtered.append({
                        "role": msg["role"],
                        "content": [{"type": "text", "text": content}],
                    })
                else:
                    filtered.append(msg)
        return "\n".join(system_parts), filtered

    def to_gemini(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert to Gemini-style {role, parts} format."""
        result = []
        for msg in messages:
            role = msg.get("role", "user")
            # Gemini uses "model" instead of "assistant"
            if role == "assistant":
                role = "model"
            content = msg.get("content", "")
            if isinstance(content, str):
                result.append({"role": role, "parts": [{"text": content}]})
            elif isinstance(content, list):
                parts = [
                    {"text": p.get("text", "")} for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                ]
                result.append({"role": role, "parts": parts})
        return result

    def to_openai(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Ensure messages are in OpenAI format (already our internal format)."""
        result = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                text = " ".join(
                    p.get("text", "") for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                )
                result.append({**msg, "content": text})
            else:
                result.append(msg)
        return result

    def translate(
        self,
        messages: list[dict[str, Any]],
        target_provider: str,
    ) -> Any:
        """Route to the appropriate conversion method based on provider name."""
        p = target_provider.lower()
        if p in ("anthropic",):
            system, msgs = self.to_anthropic(messages)
            return {"system": system, "messages": msgs}
        if p in ("gemini", "google"):
            return self.to_gemini(messages)
        return self.to_openai(messages)
