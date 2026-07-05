"""Email HTTP routes."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from keprix.email.helpers import send_smtp_message, test_imap_smtp
from keprix.email.llm import draft_reply, summarize_email
from keprix.email.pollers import sync_all_accounts
from keprix.email.schemas import (
    AiSummaryOut,
    EmailAccountCreate,
    EmailAccountOut,
    EmailAccountUpdate,
    EmailDraftCreate,
    EmailDraftOut,
    EmailDraftUpdate,
    EmailOut,
    SendEmailBody,
    SyncStatusOut,
)
from keprix.email.store import get_email_store

router = APIRouter(prefix="/api/email", tags=["email"])


def _user_id(request: Request) -> str:
    header = request.headers.get("x-user-id", "").strip()
    return header or "local"


@router.post("/accounts", status_code=201, response_model=EmailAccountOut)
async def create_account(body: EmailAccountCreate, request: Request) -> dict[str, Any]:
    store = get_email_store()
    record = await store.create_account(_user_id(request), body.model_dump())
    return record.to_public()


@router.get("/accounts", response_model=list[EmailAccountOut])
async def list_accounts(request: Request) -> list[dict[str, Any]]:
    store = get_email_store()
    return [a.to_public() for a in await store.list_accounts(_user_id(request))]


@router.put("/accounts/{account_id}", response_model=EmailAccountOut)
async def update_account(
    account_id: str, body: EmailAccountUpdate, request: Request
) -> dict[str, Any]:
    store = get_email_store()
    record = await store.update_account(
        account_id, _user_id(request), body.model_dump(exclude_unset=True)
    )
    if record is None:
        raise HTTPException(404, "Account not found")
    return record.to_public()


@router.delete("/accounts/{account_id}", status_code=200)
async def delete_account(account_id: str, request: Request) -> None:
    store = get_email_store()
    if not await store.delete_account(account_id, _user_id(request)):
        raise HTTPException(404, "Account not found")


@router.post("/accounts/{account_id}/test")
async def test_account(account_id: str, request: Request) -> dict[str, Any]:
    store = get_email_store()
    record = await store.get_account(account_id, _user_id(request))
    if record is None:
        raise HTTPException(404, "Account not found")
    try:
        return await asyncio.to_thread(test_imap_smtp, record.to_connection())
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/inbox", response_model=list[EmailOut])
async def list_inbox(
    request: Request,
    unread: bool | None = None,
    starred: bool | None = None,
    tag: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    store = get_email_store()
    rows = await store.list_emails(
        _user_id(request), unread=unread, starred=starred, tag=tag, limit=limit, offset=offset
    )
    return [r.to_dict() for r in rows]


@router.get("/search")
async def search_emails_route(
    request: Request,
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    store = get_email_store()
    rows = await store.search_emails(_user_id(request), q, limit=limit)
    return [r.to_dict() for r in rows]


@router.post("/drafts", response_model=EmailDraftOut)
async def create_draft(body: EmailDraftCreate, request: Request) -> dict[str, Any]:
    store = get_email_store()
    draft = await store.create_draft(_user_id(request), body.model_dump())
    return draft.to_dict()


@router.get("/drafts", response_model=list[EmailDraftOut])
async def list_drafts(request: Request) -> list[dict[str, Any]]:
    store = get_email_store()
    return [d.to_dict() for d in await store.list_drafts(_user_id(request))]


@router.put("/drafts/{draft_id}", response_model=EmailDraftOut)
async def update_draft(
    draft_id: str, body: EmailDraftUpdate, request: Request
) -> dict[str, Any]:
    store = get_email_store()
    draft = await store.update_draft(
        draft_id, _user_id(request), body.model_dump(exclude_unset=True)
    )
    if draft is None:
        raise HTTPException(404, "Draft not found")
    return draft.to_dict()


@router.delete("/drafts/{draft_id}", status_code=200)
async def delete_draft(draft_id: str, request: Request) -> None:
    store = get_email_store()
    if not await store.delete_draft(draft_id, _user_id(request)):
        raise HTTPException(404, "Draft not found")


@router.post("/drafts/{draft_id}/send")
async def send_draft(draft_id: str, request: Request) -> dict[str, str]:
    store = get_email_store()
    user = _user_id(request)
    draft = await store.get_draft(draft_id, user)
    if draft is None:
        raise HTTPException(404, "Draft not found")
    if not draft.account_id:
        raise HTTPException(400, "Draft has no account_id")
    account = await store.get_account(draft.account_id, user)
    if account is None:
        raise HTTPException(404, "Account not found")
    try:
        await asyncio.to_thread(
            send_smtp_message,
            account.to_connection(),
            from_addr=account.email_address,
            to_addresses=draft.to_addresses,
            cc_addresses=draft.cc_addresses,
            subject=draft.subject,
            body=draft.body,
        )
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    await store.delete_draft(draft_id, user)
    return {"status": "sent"}


@router.post("/send")
async def send_email(body: SendEmailBody, request: Request) -> dict[str, str]:
    store = get_email_store()
    user = _user_id(request)
    accounts = await store.list_accounts(user)
    account = None
    if body.account_id:
        account = await store.get_account(body.account_id, user)
    elif accounts:
        account = accounts[0]
    if account is None:
        raise HTTPException(404, "No email account configured")
    try:
        await asyncio.to_thread(
            send_smtp_message,
            account.to_connection(),
            from_addr=account.email_address,
            to_addresses=body.to_addresses,
            cc_addresses=body.cc_addresses,
            subject=body.subject,
            body=body.body,
        )
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"status": "sent"}


@router.post("/sync")
async def trigger_sync(request: Request) -> dict[str, int]:
    return await sync_all_accounts(_user_id(request))


@router.get("/sync/status", response_model=SyncStatusOut)
async def sync_status(request: Request) -> dict[str, Any]:
    store = get_email_store()
    user = _user_id(request)
    accounts = await store.list_accounts(user)
    return {
        "accounts": [
            {
                "id": a.id,
                "label": a.label,
                "last_polled_at": a.last_polled_at.isoformat() if a.last_polled_at else None,
                "is_active": a.is_active,
            }
            for a in accounts
        ]
    }


@router.get("/{email_id}", response_model=EmailOut)
async def get_email(email_id: str, request: Request) -> dict[str, Any]:
    store = get_email_store()
    record = await store.get_email(email_id, _user_id(request))
    if record is None:
        raise HTTPException(404, "Email not found")
    return record.to_dict()


@router.put("/{email_id}/read")
async def mark_read(email_id: str, request: Request) -> dict[str, str]:
    store = get_email_store()
    record = await store.update_email(email_id, _user_id(request), {"is_read": True})
    if record is None:
        raise HTTPException(404, "Email not found")
    return {"status": "ok"}


@router.put("/{email_id}/star")
async def toggle_star(email_id: str, request: Request) -> dict[str, Any]:
    store = get_email_store()
    existing = await store.get_email(email_id, _user_id(request))
    if existing is None:
        raise HTTPException(404, "Email not found")
    record = await store.update_email(
        email_id, _user_id(request), {"is_starred": not existing.is_starred}
    )
    return {"is_starred": record.is_starred if record else False}


@router.delete("/{email_id}")
async def trash_email(email_id: str, request: Request) -> dict[str, str]:
    store = get_email_store()
    record = await store.update_email(email_id, _user_id(request), {"is_trashed": True})
    if record is None:
        raise HTTPException(404, "Email not found")
    return {"status": "trashed"}


@router.post("/{email_id}/reply", response_model=EmailDraftOut)
async def create_reply_draft(email_id: str, request: Request) -> dict[str, Any]:
    store = get_email_store()
    user = _user_id(request)
    email = await store.get_email(email_id, user)
    if email is None:
        raise HTTPException(404, "Email not found")
    subject = email.subject if email.subject.lower().startswith("re:") else f"Re: {email.subject}"
    draft = await store.create_draft(
        user,
        {
            "account_id": email.account_id,
            "reply_to_email_id": email_id,
            "to_addresses": [email.from_address],
            "subject": subject,
            "body": "",
        },
    )
    return draft.to_dict()


@router.post("/{email_id}/forward", response_model=EmailDraftOut)
async def create_forward_draft(email_id: str, request: Request) -> dict[str, Any]:
    store = get_email_store()
    user = _user_id(request)
    email = await store.get_email(email_id, user)
    if email is None:
        raise HTTPException(404, "Email not found")
    subject = email.subject if email.subject.lower().startswith("fwd:") else f"Fwd: {email.subject}"
    body = f"\n\n---------- Forwarded message ----------\nFrom: {email.from_address}\nSubject: {email.subject}\n\n{email.body_text or ''}"
    draft = await store.create_draft(
        user,
        {
            "account_id": email.account_id,
            "reply_to_email_id": email_id,
            "to_addresses": [],
            "subject": subject,
            "body": body,
        },
    )
    return draft.to_dict()


@router.post("/{email_id}/ai-summary", response_model=AiSummaryOut)
async def ai_summary(email_id: str, request: Request) -> dict[str, str]:
    store = get_email_store()
    user = _user_id(request)
    email = await store.get_email(email_id, user)
    if email is None:
        raise HTTPException(404, "Email not found")
    result = await summarize_email(
        email.subject, email.body_text or email.preview or "", email.from_address
    )
    summary = str(result.get("summary", ""))
    await store.update_email(
        email_id,
        user,
        {
            "ai_summary": summary,
            "ai_tags": result.get("tags", []),
            "ai_priority": result.get("priority", "normal"),
        },
    )
    return {"summary": summary}


@router.post("/{email_id}/ai-reply-draft", response_model=EmailDraftOut)
async def ai_reply_draft(email_id: str, request: Request) -> dict[str, Any]:
    store = get_email_store()
    user = _user_id(request)
    email = await store.get_email(email_id, user)
    if email is None:
        raise HTTPException(404, "Email not found")
    body = await draft_reply(
        original_subject=email.subject,
        original_body=email.body_text or email.preview or "",
        original_sender=email.from_address,
        user_name=request.headers.get("x-user-name", "User"),
    )
    subject = email.subject if email.subject.lower().startswith("re:") else f"Re: {email.subject}"
    draft = await store.create_draft(
        user,
        {
            "account_id": email.account_id,
            "reply_to_email_id": email_id,
            "to_addresses": [email.from_address],
            "subject": subject,
            "body": body,
            "is_ai_generated": True,
        },
    )
    return draft.to_dict()


@router.get("/accounts/gmail/auth")
async def gmail_auth() -> dict[str, str]:
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    redirect = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "")
    if not client_id:
        raise HTTPException(501, "Google OAuth not configured")
    scope = "https://mail.google.com/"
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}&redirect_uri={redirect}"
        f"&response_type=code&scope={scope}&access_type=offline&prompt=consent"
    )
    return {"auth_url": url}


@router.get("/accounts/gmail/callback")
async def gmail_callback(code: str, request: Request) -> dict[str, Any]:
    if not code:
        raise HTTPException(400, "Missing authorization code")
    from keprix.oauth.tokens import exchange_google_code, store_oauth_tokens

    user = _user_id(request) if request else "local"
    tokens = await exchange_google_code(code)
    vault_id = await store_oauth_tokens(
        user, provider="google", label="Gmail", tokens=tokens
    )
    store = get_email_store()
    record = await store.create_account(
        user,
        {
            "label": "Gmail",
            "email_address": tokens.get("email") or "gmail-user@google.com",
            "imap_host": "imap.gmail.com",
            "imap_port": 993,
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "username": tokens.get("email") or "gmail-user@google.com",
            "password": "",
            "use_tls": True,
        },
    )
    record.oauth_provider = "google"
    return {"account_id": record.id, "vault_token_id": vault_id, "status": "connected"}


@router.get("/accounts/microsoft/auth")
async def microsoft_auth() -> dict[str, str]:
    client_id = os.environ.get("MICROSOFT_OAUTH_CLIENT_ID", "")
    redirect = os.environ.get("MICROSOFT_OAUTH_REDIRECT_URI", "")
    tenant = os.environ.get("MICROSOFT_OAUTH_TENANT_ID", "common")
    if not client_id:
        raise HTTPException(501, "Microsoft OAuth not configured")
    scope = "https://outlook.office.com/IMAP.AccessAsUser.All offline_access"
    url = (
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
        f"?client_id={client_id}&redirect_uri={redirect}"
        f"&response_type=code&scope={scope}"
    )
    return {"auth_url": url}


@router.get("/accounts/microsoft/callback")
async def microsoft_callback(code: str, request: Request) -> dict[str, Any]:
    if not code:
        raise HTTPException(400, "Missing authorization code")
    from keprix.oauth.tokens import exchange_microsoft_code, store_oauth_tokens

    user = _user_id(request) if request else "local"
    scope = "https://outlook.office.com/IMAP.AccessAsUser.All offline_access"
    tokens = await exchange_microsoft_code(code, scope=scope)
    vault_id = await store_oauth_tokens(
        user, provider="microsoft", label="Outlook", tokens=tokens
    )
    store = get_email_store()
    record = await store.create_account(
        user,
        {
            "label": "Outlook",
            "email_address": tokens.get("email") or "outlook-user@outlook.com",
            "imap_host": "outlook.office365.com",
            "imap_port": 993,
            "smtp_host": "smtp.office365.com",
            "smtp_port": 587,
            "username": tokens.get("email") or "outlook-user@outlook.com",
            "password": "",
            "use_tls": True,
        },
    )
    record.oauth_provider = "microsoft"
    return {"account_id": record.id, "vault_token_id": vault_id, "status": "connected"}
