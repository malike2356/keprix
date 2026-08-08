"""CLI handlers for ``keprix product``."""

from __future__ import annotations

import json


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _print(payload: dict | list, *, as_json: bool, text: str = "") -> None:
    if as_json:
        print(json.dumps(payload, indent=2, default=str))
    elif text:
        print(text)
    else:
        print(json.dumps(payload, indent=2, default=str))


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

    if args.product_command == "provision":
        # Legacy clinicom readiness path preserved when --legacy-clinicom is set
        if getattr(args, "legacy_clinicom", False) or (
            args.product_id == "clinicom" and getattr(args, "status", False) and getattr(args, "use_integration", False)
        ):
            from keprix.integrations.clinicom_provision import (
                provision_clinicom,
                provision_status as clinicom_status,
            )

            receipt = clinicom_status() if args.status else provision_clinicom(write_receipt=not args.plan)
            _print(receipt, as_json=args.json, text=f"Clinicom provision status: {receipt['status']}")
            return 0 if receipt["status"] in {"ready_for_owner_review", "not_provisioned"} else 1

        if args.product_id == "xeclone":
            from keprix.integrations.xeclone_provision import (
                provision_status as xeclone_status,
                provision_xeclone,
            )

            receipt = xeclone_status() if args.status else provision_xeclone(write_receipt=not args.plan)
            if args.json:
                print(json.dumps(receipt, indent=2))
            else:
                print(f"Xeclone provision status: {receipt['status']}")
                for check in receipt.get("checks") or []:
                    print(f"- {check['name']}: {check['status']}")
                if receipt.get("receipt_path"):
                    print(f"Receipt: {receipt['receipt_path']}")
            return 0 if receipt["status"] in {"ready_for_owner_review", "not_provisioned"} else 1

        if args.product_id == "petraclus":
            from keprix.integrations.petraclus_provision import (
                provision_petraclus,
                provision_status as petraclus_status,
            )

            receipt = petraclus_status() if args.status else provision_petraclus(write_receipt=not args.plan)
            if args.json:
                print(json.dumps(receipt, indent=2))
            else:
                print(f"Petraclus provision status: {receipt['status']}")
                for check in receipt.get("checks") or []:
                    print(f"- {check['name']}: {check['status']}")
                if receipt.get("receipt_path"):
                    print(f"Receipt: {receipt['receipt_path']}")
            return 0 if receipt["status"] in {"ready_for_owner_review", "not_provisioned"} else 1

        from keprix.product_sidecar.provision import plan_provision, provision_product, provision_status

        if args.plan:
            receipt = plan_provision(args.product_id)
        elif args.status:
            receipt = provision_status(args.product_id)
        else:
            receipt = provision_product(
                args.product_id,
                dry_run=False,
                activate=bool(getattr(args, "activate", False)),
                version=str(getattr(args, "version", "1.0.0")),
            )
        _print(receipt, as_json=True)
        status = str(receipt.get("status") or "")
        return 0 if status in {"planned", "provisioned", "already_provisioned", "not_provisioned"} else 1

    if args.product_command == "plan":
        from keprix.product_sidecar.provision import plan_provision

        _print(plan_provision(args.product_id), as_json=True)
        return 0

    if args.product_command == "status":
        from keprix.product_sidecar.provision import provision_status
        from keprix.product_sidecar.registry import get_product_pack_registry

        receipt = provision_status(args.product_id)
        health = None
        try:
            health = get_product_pack_registry().health(args.product_id)
        except KeyError:
            health = {"error": "pack_missing"}
        _print({"provision": receipt, "health": health}, as_json=True)
        return 0

    if args.product_command == "upgrade":
        from keprix.product_sidecar.provision import upgrade_product

        _print(upgrade_product(args.product_id, version=args.version), as_json=True)
        return 0

    if args.product_command == "rollback":
        from keprix.product_sidecar.provision import rollback_product

        _print(rollback_product(args.product_id), as_json=True)
        return 0

    if args.product_command == "disable":
        from keprix.product_sidecar.provision import disable_product

        _print(disable_product(args.product_id), as_json=True)
        return 0

    if args.product_command == "remove":
        from keprix.product_sidecar.provision import remove_product

        _print(remove_product(args.product_id), as_json=True)
        return 0

    if args.product_command == "conformance":
        from keprix.product_sidecar.conformance import run_foundation_conformance_safe

        report = run_foundation_conformance_safe()
        _print(report, as_json=True)
        return 0 if report.get("ready") else 1

    print(json.dumps({"error": f"unknown product command: {args.product_command}"}))
    return 2
