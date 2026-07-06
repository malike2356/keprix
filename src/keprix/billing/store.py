"""File-backed billing store with optional PostgreSQL tables."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from keprix.database import Base, get_session_factory


def _billing_dir() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "billing"
    except Exception:
        root = Path.home() / ".keprix" / "billing"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat()


class BillingStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _billing_dir()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._customers_path = self._dir / "customers.json"
        self._subscriptions_path = self._dir / "subscriptions.json"
        self._invoices_path = self._dir / "invoices.json"
        self._seats_path = self._dir / "seats.json"
        self._webhook_events_path = self._dir / "webhook_events.json"
        self._stripe_map_path = self._dir / "stripe_map.json"

    def _read_map(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_map(self, path: Path, data: dict[str, Any]) -> None:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    async def get_customer(self, user_id: str) -> dict[str, Any] | None:
        customers = self._read_map(self._customers_path)
        return customers.get(user_id)

    async def save_customer(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        customers = self._read_map(self._customers_path)
        existing = customers.get(user_id, {})
        merged = {**existing, **payload, "user_id": user_id, "updated_at": _iso()}
        if "created_at" not in merged:
            merged["created_at"] = _iso()
        customers[user_id] = merged
        self._write_map(self._customers_path, customers)
        return merged

    async def get_subscription(self, user_id: str) -> dict[str, Any] | None:
        subs = self._read_map(self._subscriptions_path)
        return subs.get(user_id)

    async def save_subscription(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        subs = self._read_map(self._subscriptions_path)
        existing = subs.get(user_id, {})
        merged = {**existing, **payload, "user_id": user_id, "updated_at": _iso()}
        if "id" not in merged:
            merged["id"] = str(uuid.uuid4())
        if "created_at" not in merged:
            merged["created_at"] = _iso()
        subs[user_id] = merged
        self._write_map(self._subscriptions_path, subs)
        return merged

    async def list_invoices(self, user_id: str) -> list[dict[str, Any]]:
        invoices = self._read_map(self._invoices_path)
        return [row for row in invoices.values() if row.get("user_id") == user_id]

    async def save_invoice(self, invoice: dict[str, Any]) -> dict[str, Any]:
        invoices = self._read_map(self._invoices_path)
        invoice_id = str(invoice.get("id") or uuid.uuid4())
        row = {**invoice, "id": invoice_id, "updated_at": _iso()}
        if "created_at" not in row:
            row["created_at"] = _iso()
        invoices[invoice_id] = row
        self._write_map(self._invoices_path, invoices)
        return row

    async def get_invoice(self, invoice_id: str) -> dict[str, Any] | None:
        invoices = self._read_map(self._invoices_path)
        return invoices.get(invoice_id)

    async def list_seats(self, owner_id: str) -> list[dict[str, Any]]:
        seats = self._read_map(self._seats_path)
        return [row for row in seats.values() if row.get("owner_id") == owner_id]

    async def save_seat(self, seat: dict[str, Any]) -> dict[str, Any]:
        seats = self._read_map(self._seats_path)
        seat_id = str(seat.get("id") or uuid.uuid4())
        row = {**seat, "id": seat_id, "updated_at": _iso()}
        if "created_at" not in row:
            row["created_at"] = _iso()
        seats[seat_id] = row
        self._write_map(self._seats_path, seats)
        return row

    async def delete_seat(self, seat_id: str) -> bool:
        seats = self._read_map(self._seats_path)
        if seat_id not in seats:
            return False
        del seats[seat_id]
        self._write_map(self._seats_path, seats)
        return True

    async def update_seat(self, seat_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        seats = self._read_map(self._seats_path)
        seat = seats.get(seat_id)
        if seat is None:
            return None
        merged = {**seat, **payload, "id": seat_id, "updated_at": _iso()}
        seats[seat_id] = merged
        self._write_map(self._seats_path, seats)
        return merged

    async def webhook_seen(self, idempotency_key: str) -> bool:
        events = self._read_map(self._webhook_events_path)
        return idempotency_key in events

    async def mark_webhook(self, idempotency_key: str, payload: dict[str, Any]) -> None:
        events = self._read_map(self._webhook_events_path)
        events[idempotency_key] = {"processed_at": _iso(), "payload": payload}
        self._write_map(self._webhook_events_path, events)

    async def get_stripe_map(self) -> dict[str, Any]:
        return self._read_map(self._stripe_map_path)

    async def save_stripe_map(self, data: dict[str, Any]) -> dict[str, Any]:
        existing = await self.get_stripe_map()
        merged = {**existing, **data}
        self._write_map(self._stripe_map_path, merged)
        return merged


_store: BillingStore | None = None


def get_billing_store() -> BillingStore:
    global _store
    if _store is None:
        _store = BillingStore()
    return _store


async def ensure_billing_tables() -> None:
    from keprix.billing.models import BillingCustomerRow, BillingInvoiceRow, BillingSeatRow, BillingSubscriptionRow

    factory = get_session_factory()
    if factory is None:
        return
    async with factory() as session:
        conn = await session.connection()
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                BillingCustomerRow.__table__,
                BillingSubscriptionRow.__table__,
                BillingInvoiceRow.__table__,
                BillingSeatRow.__table__,
            ],
        )
        await session.commit()
