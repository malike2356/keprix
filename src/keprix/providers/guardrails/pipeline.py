"""Guardrail pipeline: orchestrates PII masking, injection defence, vision routing."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .pii_masker import MaskRecord, PIIMasker
from .prompt_injection import InjectionResult, PromptInjectionDefence
from .vision_bridge import VisionBridge

logger = logging.getLogger(__name__)


@dataclass
class GuardrailResult:
    messages: list[dict[str, Any]]
    blocked: bool = False
    block_reason: str = ""
    pii_records: list[MaskRecord] = field(default_factory=list)
    injection: InjectionResult | None = None
    has_images: bool = False
    images_stripped: int = 0
    required_vision: bool = False


class GuardrailPipeline:
    """Run incoming messages through the full guardrail stack.

    Pipeline order:
      1. PII masking (if enabled)
      2. Prompt injection detection (blocks HIGH severity by default)
      3. Vision content detection (for provider routing hints)
    """

    def __init__(
        self,
        pii_masker: PIIMasker | None = None,
        injection_defence: PromptInjectionDefence | None = None,
        vision_bridge: VisionBridge | None = None,
        mask_pii: bool = True,
        block_injections: bool = True,
        strip_images_without_vision: bool = False,
    ) -> None:
        self._pii = pii_masker or PIIMasker()
        self._injection = injection_defence or PromptInjectionDefence()
        self._vision = vision_bridge or VisionBridge()
        self._mask_pii = mask_pii
        self._block_injections = block_injections
        self._strip_images = strip_images_without_vision

    async def run(
        self,
        messages: list[dict[str, Any]],
        available_providers: list[str] | None = None,
    ) -> GuardrailResult:
        """Process messages through all guardrail layers.

        Returns a GuardrailResult with cleaned messages and metadata.
        The caller should check ``result.blocked`` before proceeding.
        """
        result = GuardrailResult(messages=list(messages))

        # 1. PII masking
        if self._mask_pii:
            result.messages, result.pii_records = self._pii.mask_messages(result.messages)
            if result.pii_records:
                logger.debug("PII masked: %d item(s)", len(result.pii_records))

        # 2. Prompt injection detection
        blocked, detection = self._injection.scan_messages(
            result.messages, block_on_high=self._block_injections
        )
        result.injection = detection
        if blocked:
            result.blocked = True
            result.block_reason = (
                f"Prompt injection detected [{detection.label}]: {detection.match[:60]}"
            )
            logger.warning("Guardrail BLOCKED: %s", result.block_reason)
            return result

        # 3. Vision detection
        result.has_images = self._vision.has_images(result.messages)
        if result.has_images:
            providers = available_providers or []
            result.required_vision = not any(
                self._vision.is_vision_capable(p) for p in providers
            )
            if result.required_vision and self._strip_images:
                result.messages, result.images_stripped = self._vision.strip_images(
                    result.messages
                )

        return result

    def unmask_response(self, response_text: str, result: GuardrailResult) -> str:
        """Restore PII in the response text (undoes masking on outbound content)."""
        if not result.pii_records:
            return response_text
        return self._pii.unmask(response_text, result.pii_records)
