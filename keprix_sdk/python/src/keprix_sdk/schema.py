from __future__ import annotations

from typing import Any

from keprix_sdk.domain import Domain


def domain_to_json(domain: Domain) -> dict[str, Any]:
    return {
        "name": domain.name,
        "entities": [
            {
                "name": entity.name,
                "fields": [
                    {
                        "name": field.name,
                        "type": field.type,
                        "required": field.required,
                        "default": field.default,
                        "entity": field.entity,
                        "values": field.values,
                    }
                    for field in entity.fields
                ],
                "operations": [
                    {
                        "name": operation.name,
                        "confirmation_required": operation.confirmation_required,
                    }
                    for operation in entity.operations
                ],
            }
            for entity in domain.entities
        ],
    }
