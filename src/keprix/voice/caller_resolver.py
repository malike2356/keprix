"""Resolve inbound phone numbers to caller context."""

from __future__ import annotations

from dataclasses import dataclass

from keprix.voice.caller_context import CallerContext


@dataclass
class ResolvedCaller:
    phone: str
    name: str | None = None
    contact_id: str | None = None
    context: CallerContext | None = None


class CallerResolver:
    async def resolve(self, phone: str) -> ResolvedCaller:
        context = await CallerContext.from_phone(phone)
        return ResolvedCaller(phone=phone, name=context.name, contact_id=context.caller_id, context=context)
