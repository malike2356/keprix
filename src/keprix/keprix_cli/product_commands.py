"""CLI handlers for ``keprix product``."""

from __future__ import annotations

import json


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def cmd_product(args) -> int:
    from keprix.integrations.product_registry import list_registered_products, register_product

    if args.product_command == "register":
        record = register_product(
            args.product_id,
            scout_enabled=args.scout_enabled == "true",
            personas=_split_csv(args.personas),
            tools=_split_csv(args.tools),
            security_policy=args.security_policy,
        )
        if args.json:
            print(json.dumps(record, indent=2))
        else:
            print(f"Registered product '{args.product_id}' for Scout monitoring.")
        return 0

    if args.product_command == "list":
        products = list_registered_products()
        if args.json:
            print(json.dumps(products, indent=2))
        else:
            if not products:
                print("No products registered.")
            for row in products:
                print(
                    f"- {row['product_id']}: scout={row.get('scout_enabled')} "
                    f"policy={row.get('security_policy')} tools={len(row.get('tools') or [])}"
                )
        return 0

    print(json.dumps({"error": f"unknown product command: {args.product_command}"}))
    return 2
