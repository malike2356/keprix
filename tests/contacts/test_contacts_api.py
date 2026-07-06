"""Prompt 12 MVP acceptance tests: contacts."""

from __future__ import annotations

import io

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.contacts.search import contact_search
from keprix.contacts.store import get_contact_store, reset_contact_store


@pytest.fixture(autouse=True)
def _reset_store():
    reset_contact_store()
    yield
    reset_contact_store()


async def _seed_contacts():
    store = get_contact_store()
    await store.create(
        {
            "display_name": "John Smith",
            "given_name": "John",
            "family_name": "Smith",
            "emails": [{"address": "john@example.com", "label": "work", "primary": True}],
            "phones": [],
            "organisation": "Verlox Ltd",
        },
        source="manual",
    )
    await store.create(
        {
            "display_name": "Jonathan Archer",
            "given_name": "Jonathan",
            "family_name": "Archer",
            "emails": [{"address": "jonathan@example.com", "label": "work", "primary": True}],
            "phones": [],
        },
        source="manual",
    )


@pytest.mark.asyncio
async def test_contact_search_john_before_jonathan():
    await _seed_contacts()
    results = await contact_search("John", limit=5)
    assert results
    assert results[0]["display_name"] == "John Smith"


@pytest.mark.asyncio
async def test_contact_search_phonetic_jon_finds_john():
    await _seed_contacts()
    results = await contact_search("Jon", limit=5)
    names = [r["display_name"] for r in results]
    assert "John Smith" in names


@pytest.mark.asyncio
async def test_crud_manual_contact():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/contacts",
            json={
                "display_name": "Marcus Osei",
                "given_name": "Marcus",
                "family_name": "Osei",
                "emails": [{"address": "marcus@company.com", "primary": True}],
            },
        )
        assert created.status_code == 201
        contact_id = created.json()["id"]
        updated = await client.put(
            f"/api/contacts/{contact_id}",
            json={"job_title": "Director"},
        )
        assert updated.status_code == 200
        assert updated.json()["job_title"] == "Director"
        deleted = await client.delete(f"/api/contacts/{contact_id}")
        assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_csv_import_google_format():
    csv_data = (
        "Given Name,Family Name,E-mail 1 - Value,Organization 1 - Name\n"
        "Sarah,Johnson,sarah@agency.co.uk,Agency Co\n"
    ).encode()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/contacts/import/csv",
            files={"file": ("contacts.csv", io.BytesIO(csv_data), "text/csv")},
        )
    assert response.status_code == 200
    summary = response.json()
    assert summary["added"] == 1
    results = await contact_search("Sarah", limit=5)
    assert any(r["primary_email"] == "sarah@agency.co.uk" for r in results)


@pytest.mark.asyncio
async def test_vcf_import():
    vcf = (
        "BEGIN:VCARD\nVERSION:3.0\nFN:Alex Kim\nN:Kim;Alex;;;\n"
        "EMAIL;TYPE=INTERNET:alex@kim.io\nEND:VCARD\n"
    ).encode()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/contacts/import/vcf",
            files={"file": ("contact.vcf", io.BytesIO(vcf), "text/vcard")},
        )
    assert response.status_code == 200
    assert response.json()["added"] == 1


@pytest.mark.asyncio
async def test_preferences_defaults():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/contacts/preferences")
    assert response.status_code == 200
    data = response.json()
    assert data["confirm_before_email"] is True
    assert data["read_back_draft"] is True


@pytest.mark.asyncio
async def test_synced_contact_not_editable():
    store = get_contact_store()
    record = await store.create(
        {
            "display_name": "Google Person",
            "emails": [{"address": "gp@gmail.com", "primary": True}],
            "phones": [],
        },
        source="google",
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(f"/api/contacts/{record.id}", json={"notes": "nope"})
    assert response.status_code == 400
