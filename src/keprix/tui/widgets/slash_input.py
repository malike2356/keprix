"""Input widget with slash tab completion."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable

from textual.events import Key, Paste
from textual.widgets import Input


@dataclass(frozen=True)
class SlashCompletionOption:
    command: str
    description: str = ""


CompletionResult = list[str | SlashCompletionOption]
CompletionProvider = Callable[[str], Awaitable[CompletionResult]]
PasteHandler = Callable[[str], str | None]
CandidatesHandler = Callable[[list[SlashCompletionOption], int], None]


class SlashInput(Input):
    """Composer input with debounced slash tab completion."""

    def __init__(
        self,
        *,
        complete_slash: CompletionProvider | None = None,
        on_completion_hint: Callable[[str], None] | None = None,
        on_completion_candidates: CandidatesHandler | None = None,
        on_paste_text: PasteHandler | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._complete_slash = complete_slash
        self._on_completion_hint = on_completion_hint
        self._on_completion_candidates = on_completion_candidates
        self._on_paste_text = on_paste_text
        self._completion_candidates: list[SlashCompletionOption] = []
        self._completion_index = -1
        self._completion_task: asyncio.Task[None] | None = None
        self._completion_base = ""

    def _set_hint(self, hint: str) -> None:
        if self._on_completion_hint is not None:
            self._on_completion_hint(hint)

    def _set_candidates(self, candidates: list[SlashCompletionOption]) -> None:
        if self._on_completion_candidates is not None:
            self._on_completion_candidates(candidates, self._completion_index)

    def _normalize_candidates(self, candidates: CompletionResult) -> list[SlashCompletionOption]:
        normalized: list[SlashCompletionOption] = []
        seen: set[str] = set()
        for candidate in candidates:
            if isinstance(candidate, SlashCompletionOption):
                option = candidate
            else:
                option = SlashCompletionOption(command=str(candidate))
            if option.command not in seen:
                normalized.append(option)
                seen.add(option.command)
        return normalized

    async def _load_candidates(self, prefix: str) -> None:
        if self._complete_slash is None:
            self._completion_candidates = []
            self._set_candidates([])
            return
        try:
            self._completion_candidates = self._normalize_candidates(await self._complete_slash(prefix))
        except Exception:
            self._completion_candidates = []
        if self._completion_candidates:
            self._completion_index = max(0, min(self._completion_index, len(self._completion_candidates) - 1))
        else:
            self._completion_index = -1
        self._set_candidates(self._completion_candidates)

    def _schedule_candidates(self, prefix: str) -> None:
        if self._completion_task and not self._completion_task.done():
            self._completion_task.cancel()

        async def _runner() -> None:
            await asyncio.sleep(0.15)
            if prefix != self._completion_base:
                self._completion_base = prefix
                self._completion_index = 0
            await self._load_candidates(prefix)
            if self._completion_candidates and self._completion_index < 0:
                self._completion_index = 0
                self._set_hint(f"Completion: {self._completion_candidates[0].command}")
                self._set_candidates(self._completion_candidates)

        self._completion_task = asyncio.create_task(_runner())

    def _apply_candidate(self, candidate: SlashCompletionOption) -> None:
        remainder = ""
        if " " in candidate.command:
            command, remainder = candidate.command.split(" ", 1)
        else:
            command = candidate.command
        self.value = f"{command}{(' ' + remainder) if remainder else ' '}"
        self.cursor_position = len(self.value)
        self._set_hint(f"Completion: {candidate.command}")
        self._set_candidates(self._completion_candidates)

    async def cycle_completion(self, step: int = 1) -> bool:
        """Cycle slash completions without submitting or rewriting the input."""
        if not self.value.startswith("/"):
            return False
        prefix = self.value.strip()
        if not self._completion_candidates or prefix != self._completion_base:
            self._completion_base = prefix
            self._completion_index = 0
            await self._load_candidates(prefix)
        else:
            if not self._completion_candidates:
                return False
            self._completion_index = (self._completion_index + step) % len(self._completion_candidates)
        if not self._completion_candidates:
            return False
        selected = self._completion_candidates[max(0, self._completion_index)]
        self._set_hint(f"Completion: {selected.command}")
        self._set_candidates(self._completion_candidates)
        return True

    def apply_selected_completion(self) -> bool:
        """Insert the highlighted slash completion into the input."""
        if not self._completion_candidates:
            return False
        index = max(0, self._completion_index)
        if index >= len(self._completion_candidates):
            return False
        self._apply_candidate(self._completion_candidates[index])
        return True

    async def on_key(self, event: Key) -> None:
        if event.key in {"tab", "up", "down"} and self.value.startswith("/"):
            event.prevent_default()
            event.stop()
            step = -1 if event.key == "up" or bool(getattr(event, "shift", False)) else 1
            await self.cycle_completion(step)
            return
        if event.key == "enter" and self.value.startswith("/") and self._completion_candidates:
            index = max(0, self._completion_index)
            selected = self._completion_candidates[index] if index < len(self._completion_candidates) else None
            if selected and self.value.strip() != selected.command:
                event.prevent_default()
                event.stop()
                self.apply_selected_completion()
                return
            if selected and self.value.strip() == selected.command:
                self._set_candidates([])
                self._completion_candidates = []
                self._completion_index = -1
                self._completion_base = ""
                self._set_hint("")
                # Fall through to Textual so Enter submits the selected command.
            else:
                return
        base_on_key = getattr(super(), "on_key", None)
        if base_on_key is not None:
            await base_on_key(event)
        else:
            await super()._on_key(event)
        if self.value.startswith("/"):
            self._schedule_candidates(self.value.strip())
        else:
            self._completion_candidates = []
            self._completion_index = -1
            self._completion_base = ""
            self._set_hint("")
            self._set_candidates([])

    def on_paste(self, event: Paste) -> None:
        pasted = event.text
        if self._on_paste_text is not None:
            replacement = self._on_paste_text(pasted)
            if replacement is not None:
                event.text = replacement
        super().on_paste(event)
