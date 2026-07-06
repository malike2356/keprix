"""Natural language to ActionPlan parsing."""

from __future__ import annotations

import re
from typing import Any

from keprix.sdk.schemas import ActionPlanModel, ActionStepModel, DomainSchema, EntitySpec, OperationSpec


def _find_entity(domain: DomainSchema, name: str) -> EntitySpec | None:
    target = name.lower()
    for entity in domain.entities:
        if entity.name.lower() == target:
            return entity
    return None


def _operation_spec(entity: EntitySpec, operation: str) -> OperationSpec | None:
    target = operation.lower()
    for op in entity.operations:
        if op.name.lower() == target:
            return op
    return None


def _extract_amount(text: str) -> float | None:
    match = re.search(r"£\s*([\d,]+(?:\.\d+)?)", text)
    if match:
        return float(match.group(1).replace(",", ""))
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:gbp|usd|eur)?\b", text, re.I)
    if match:
        return float(match.group(1))
    return None


def _extract_name_after_for(text: str) -> str | None:
    match = re.search(r"\bfor\s+([A-Za-z][A-Za-z\s'-]{1,40})", text, re.I)
    if match:
        return match.group(1).strip()
    return None


def build_confirmation_prompt(steps: list[ActionStepModel]) -> str:
    parts = []
    for step in steps:
        fields = ", ".join(f"{key}={value}" for key, value in step.fields.items())
        parts.append(f"{step.operation} {step.entity}" + (f" ({fields})" if fields else ""))
    return "Please confirm: " + "; ".join(parts)


def parse_message(domain: DomainSchema, message: str, session_id: str | None = None) -> ActionPlanModel:
    text = message.strip()
    lowered = text.lower()
    steps: list[ActionStepModel] = []

    if "delete" in lowered and ("all" in lowered or "every" in lowered):
        entity_name = "Client"
        if "invoice" in lowered:
            entity_name = "Invoice"
        elif "contact" in lowered:
            entity_name = "Contact"
        elif "deal" in lowered:
            entity_name = "Deal"
        entity = _find_entity(domain, entity_name) or (domain.entities[0] if domain.entities else None)
        if entity:
            op = _operation_spec(entity, "delete") or OperationSpec(name="delete", confirmation_required=True)
            steps.append(
                ActionStepModel(
                    entity=entity.name,
                    operation="delete",
                    fields={"scope": "all"},
                    confirmation_required=True,
                    confidence=0.85,
                )
            )

    elif "create" in lowered and "invoice" in lowered:
        entity = _find_entity(domain, "Invoice")
        if entity:
            fields: dict[str, Any] = {}
            client = _extract_name_after_for(text)
            if client:
                fields["client"] = client
            amount = _extract_amount(text)
            if amount is not None:
                fields["amount"] = amount
            if "next friday" in lowered:
                fields["due_date"] = "next Friday"
            op = _operation_spec(entity, "create")
            steps.append(
                ActionStepModel(
                    entity=entity.name,
                    operation="create",
                    fields=fields,
                    confirmation_required=bool(op.confirmation_required) if op else False,
                    confidence=0.9,
                )
            )

    elif "create" in lowered and "client" in lowered:
        entity = _find_entity(domain, "Client")
        if entity:
            fields = {}
            name = _extract_name_after_for(text)
            if name:
                fields["name"] = name
            steps.append(
                ActionStepModel(
                    entity=entity.name,
                    operation="create",
                    fields=fields,
                    confirmation_required=False,
                    confidence=0.8,
                )
            )

    elif "mark" in lowered and "paid" in lowered:
        entity = _find_entity(domain, "Invoice")
        if entity:
            steps.append(
                ActionStepModel(
                    entity=entity.name,
                    operation="mark_paid",
                    fields={},
                    confirmation_required=False,
                    confidence=0.75,
                )
            )

    elif "send" in lowered and "invoice" in lowered:
        entity = _find_entity(domain, "Invoice")
        if entity:
            op = _operation_spec(entity, "send")
            steps.append(
                ActionStepModel(
                    entity=entity.name,
                    operation="send",
                    fields={},
                    confirmation_required=bool(op.confirmation_required) if op else True,
                    confidence=0.8,
                )
            )

    if not steps and domain.entities:
        entity = domain.entities[0]
        steps.append(
            ActionStepModel(
                entity=entity.name,
                operation="read",
                fields={"query": text},
                confirmation_required=False,
                confidence=0.4,
            )
        )

    requires_confirmation = any(step.confirmation_required for step in steps)
    return ActionPlanModel(
        user_input=text,
        session_id=session_id,
        steps=steps,
        requires_confirmation=requires_confirmation,
        confirmation_prompt=build_confirmation_prompt(steps) if requires_confirmation else "",
    )
