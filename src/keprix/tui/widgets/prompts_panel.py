"""Saved prompt library helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SavedPrompt:
    name: str
    body: str
    category: str = "General"


class PromptsPanelState:
    def __init__(self, prompts: list[SavedPrompt] | None = None) -> None:
        self.prompts = list(prompts or [])

    def search(self, query: str) -> list[SavedPrompt]:
        needle = query.lower().strip()
        if not needle:
            return list(self.prompts)
        return [prompt for prompt in self.prompts if needle in prompt.name.lower() or needle in prompt.body.lower()]

    def insert(self, name: str) -> str:
        for prompt in self.prompts:
            if prompt.name == name:
                return prompt.body
        raise KeyError(name)

