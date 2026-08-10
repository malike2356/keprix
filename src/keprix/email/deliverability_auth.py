"""Email authentication and deliverability helpers (parity with shared/email)."""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

DomainRole = Literal["transactional", "marketing"]
BounceClass = Literal["hard", "soft", "block"]
DeliveryEventKind = Literal[
    "delivered",
    "bounced",
    "spam",
    "complained",
    "opened",
    "clicked",
    "blocked",
    "deferred",
]
DmarcPolicy = Literal["none", "quarantine", "reject"]
SendingService = Literal["resend", "sendgrid", "ses", "mailgun", "custom"]

_POLICY_PATH = Path(__file__).with_name("deliverability_policy.json")
POLICY: dict[str, Any] = json.loads(_POLICY_PATH.read_text(encoding="utf-8"))

SPF_INCLUDES: dict[str, str | None] = {
    "resend": "include:_spf.resend.com",
    "sendgrid": "include:sendgrid.net",
    "ses": "include:amazonses.com",
    "mailgun": "include:mailgun.org",
    "custom": None,
}


def _strip_www(domain: str) -> str:
    return domain.strip().lower().removeprefix("www.").rstrip(".")


def generate_spf_record(domain: str, sending_services: list[SendingService]) -> dict[str, str]:
    includes = [SPF_INCLUDES[s] for s in sending_services if SPF_INCLUDES.get(s)]
    unique = list(dict.fromkeys(includes))
    value = f"v=spf1 {' '.join(unique)} ~all".replace("  ", " ").strip()
    return {"host": "@", "type": "TXT", "value": value, "purpose": "spf", "domain": _strip_www(domain)}


def generate_dkim_record(domain: str, selector: str = "mail") -> dict[str, Any]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    pub_b64 = "".join(
        line for line in public_pem.splitlines() if not line.startswith("-----")
    )
    value = f"v=DKIM1; k=rsa; p={pub_b64}"
    return {
        "private_key_pem": private_pem,
        "public_key_pem": public_pem,
        "record": {
            "host": f"{selector}._domainkey",
            "type": "TXT",
            "value": value,
            "purpose": "dkim",
            "domain": _strip_www(domain),
        },
    }


def generate_dmarc_record(
    domain: str,
    policy: DmarcPolicy = "none",
    *,
    rua: str | None = None,
    ruf: str | None = None,
    subdomain_policy: DmarcPolicy | None = None,
) -> dict[str, str]:
    parts = ["v=DMARC1", f"p={policy}"]
    if subdomain_policy:
        parts.append(f"sp={subdomain_policy}")
    if rua:
        parts.append(f"rua=mailto:{rua}")
    if ruf:
        parts.append(f"ruf=mailto:{ruf}")
    parts.extend(["adkim=s", "aspf=s"])
    root = _strip_www(domain)
    return {
        "host": f"_dmarc.{root}",
        "type": "TXT",
        "value": "; ".join(parts) + ";",
        "purpose": "dmarc",
        "domain": root,
    }


def _lookup_txt_doh(name: str) -> list[str]:
    url = "https://cloudflare-dns.com/dns-query"
    headers = {"Accept": "application/dns-json"}
    with httpx.Client(timeout=10.0) as client:
        res = client.get(url, params={"name": name, "type": "TXT"}, headers=headers)
        res.raise_for_status()
        data = res.json()
    answers = data.get("Answer") or []
    out: list[str] = []
    for ans in answers:
        if int(ans.get("type") or 0) != 16:
            continue
        raw = str(ans.get("data") or "")
        # DoH wraps TXT in quotes, sometimes concatenated.
        pieces = re.findall(r'"([^"]*)"', raw)
        out.append("".join(pieces) if pieces else raw.strip('"'))
    return out


def validate_dns_records(
    domain: str,
    *,
    dkim_selector: str = "mail",
    resolver: Callable[[str], list[str]] | None = None,
) -> dict[str, Any]:
    root = _strip_www(domain)
    lookup = resolver or _lookup_txt_doh
    spf_records = [r for r in lookup(root) if re.search(r"v=spf1", r, re.I)]
    dkim_records = [
        r
        for r in lookup(f"{dkim_selector}._domainkey.{root}")
        if re.search(r"v=DKIM1|p=", r, re.I)
    ]
    dmarc_records = [r for r in lookup(f"_dmarc.{root}") if re.search(r"v=DMARC1", r, re.I)]
    dmarc_policy = None
    for r in dmarc_records:
        m = re.search(r"\bp=(none|quarantine|reject)\b", r, re.I)
        if m:
            dmarc_policy = m.group(1).lower()
            break
    spf_ok = len(spf_records) > 0
    dkim_ok = any(re.search(r"p=[A-Za-z0-9+/=]+", r) for r in dkim_records)
    dmarc_ok = len(dmarc_records) > 0 and bool(dmarc_policy)
    return {
        "domain": root,
        "spf": {
            "ok": spf_ok,
            "records": spf_records,
            "detail": "SPF TXT found" if spf_ok else "No SPF TXT (v=spf1) on apex",
        },
        "dkim": {
            "ok": dkim_ok,
            "records": dkim_records,
            "detail": (
                f"DKIM TXT found for selector {dkim_selector}"
                if dkim_records
                else f"No DKIM TXT at {dkim_selector}._domainkey.{root}"
            ),
            "selector": dkim_selector,
        },
        "dmarc": {
            "ok": dmarc_ok,
            "records": dmarc_records,
            "detail": (
                f"DMARC present (p={dmarc_policy})"
                if dmarc_records
                else f"No DMARC TXT at _dmarc.{root}"
            ),
            "policy": dmarc_policy,
        },
        "all_ok": spf_ok and dkim_ok and dmarc_ok,
    }


def configure_transactional_domain(app_domain: str) -> dict[str, Any]:
    root = _strip_www(app_domain)
    sub = (POLICY.get("domainRoles") or {}).get("transactionalSubdomains", ["mail"])[0]
    sending = f"{sub}.{root}"
    return {
        "app_domain": root,
        "role": "transactional",
        "sending_domain": sending,
        "suggested_from": f"noreply@{sending}",
        "warm_up": warm_up_domain(sending),
    }


def configure_marketing_domain(app_domain: str) -> dict[str, Any]:
    root = _strip_www(app_domain)
    sub = (POLICY.get("domainRoles") or {}).get("marketingSubdomains", ["updates"])[0]
    sending = f"{sub}.{root}"
    return {
        "app_domain": root,
        "role": "marketing",
        "sending_domain": sending,
        "suggested_from": f"hello@{sending}",
        "warm_up": warm_up_domain(sending),
    }


def warm_up_domain(domain: str, target_per_day: int = 1600) -> dict[str, Any]:
    warmup = POLICY.get("warmup") or {}
    start = int(warmup.get("startPerDay", 50))
    every = int(warmup.get("doubleEveryDays", 3))
    max_days = int(warmup.get("maxDays", 28))
    days: list[dict[str, int]] = []
    cap = start
    day = 1
    while day <= max_days and cap <= target_per_day:
        days.append({"day": day, "daily_cap": min(cap, target_per_day)})
        if day % every == 0:
            cap *= 2
        day += 1
    return {
        "start_per_day": start,
        "double_every_days": every,
        "days": days,
        "note": (
            f"Warm-up plan for {domain}: start {start}/day, "
            f"double every {every} days until target {target_per_day}/day."
        ),
    }


def enforce_domain_separation(role: DomainRole, from_address: str, app_domain: str) -> None:
    plans = {
        "transactional": configure_transactional_domain(app_domain),
        "marketing": configure_marketing_domain(app_domain),
    }
    email = from_address.strip().lower()
    m = re.search(r"<([^>]+)>", email)
    host = (m.group(1) if m else email).split("@")[-1]
    if not host:
        raise ValueError("from address missing domain")
    if role == "marketing" and host == plans["transactional"]["sending_domain"]:
        raise ValueError("Marketing mail must not use the transactional sending domain")
    if role == "transactional" and host == plans["marketing"]["sending_domain"]:
        raise ValueError("Transactional mail must not use the marketing sending domain")


def classify_bounce(reason: str | None = None) -> BounceClass:
    text = (reason or "").lower()
    if not text:
        return "soft"
    if re.search(
        r"invalid|unknown user|no such user|does not exist|mailbox unavailable|550 5\.1\.1|user unknown",
        text,
    ):
        return "hard"
    if re.search(r"reputation|blocked|blacklist|denied|550 5\.7\.1|spamhaus|block list", text):
        return "block"
    return "soft"


@dataclass
class DeliveryEvent:
    email_id: str
    domain: str
    kind: DeliveryEventKind
    at: str
    bounce_class: BounceClass | None = None
    meta: dict[str, str] = field(default_factory=dict)


class DeliveryStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.events: list[DeliveryEvent] = []

    def track(
        self,
        email_id: str,
        domain: str,
        kind: DeliveryEventKind,
        *,
        at: str | None = None,
        reason: str | None = None,
        bounce_class: BounceClass | None = None,
    ) -> DeliveryEvent:
        row = DeliveryEvent(
            email_id=email_id,
            domain=_strip_www(domain),
            kind=kind,
            at=at or datetime.now(timezone.utc).isoformat(),
            bounce_class=bounce_class
            or (classify_bounce(reason) if kind in {"bounced", "blocked"} else None),
            meta={"reason": reason} if reason else {},
        )
        with self._lock:
            self.events.append(row)
            if len(self.events) > 50_000:
                self.events = self.events[-40_000:]
        return row


_STORE = DeliveryStore()


def get_delivery_store() -> DeliveryStore:
    return _STORE


def calculate_inbox_rate(
    store: DeliveryStore, domain: str, since: str, until: str
) -> dict[str, Any]:
    rows = [
        e
        for e in store.events
        if e.domain == _strip_www(domain) and since <= e.at <= until
    ]
    delivered = sum(1 for e in rows if e.kind in {"delivered", "opened"})
    spam = sum(1 for e in rows if e.kind in {"spam", "complained"})
    bounced = sum(1 for e in rows if e.kind in {"bounced", "blocked"})
    denom = delivered + spam + bounced
    return {
        "inbox_rate_pct": round((100.0 * delivered) / denom, 1) if denom else None,
        "delivered": delivered,
        "spam": spam,
        "bounced": bounced,
        "proxy_note": POLICY.get("note"),
    }


def calculate_spam_complaint_rate(
    store: DeliveryStore, domain: str, since: str, until: str
) -> dict[str, Any]:
    rows = [
        e
        for e in store.events
        if e.domain == _strip_www(domain) and since <= e.at <= until
    ]
    complaints = sum(1 for e in rows if e.kind in {"complained", "spam"})
    sent_like = sum(
        1
        for e in rows
        if e.kind
        in {"delivered", "opened", "clicked", "bounced", "spam", "complained", "blocked"}
    )
    return {
        "complaint_rate_pct": round((100.0 * complaints) / sent_like, 2) if sent_like else None,
        "complaints": complaints,
        "sent_like": sent_like,
    }


def bounce_analysis(store: DeliveryStore, domain: str | None = None) -> dict[str, Any]:
    bounced = [
        e
        for e in store.events
        if e.kind in {"bounced", "blocked"} and (domain is None or e.domain == _strip_www(domain))
    ]
    return {
        "hard": sum(1 for e in bounced if e.bounce_class == "hard"),
        "soft": sum(1 for e in bounced if e.bounce_class == "soft"),
        "block": sum(1 for e in bounced if e.bounce_class == "block" or e.kind == "blocked"),
        "samples": [
            {
                "email_id": e.email_id,
                "domain": e.domain,
                "kind": e.kind,
                "bounce_class": e.bounce_class,
                "at": e.at,
            }
            for e in bounced[-20:]
        ],
    }


def delivery_health_check(
    store: DeliveryStore, domain: str, since: str, until: str
) -> dict[str, Any]:
    thresholds = POLICY.get("thresholds") or {}
    inbox = calculate_inbox_rate(store, domain, since, until)
    spam = calculate_spam_complaint_rate(store, domain, since, until)
    bounce = bounce_analysis(store, domain)
    denom = max(int(inbox["delivered"]) + int(inbox["bounced"]), 1)
    bounce_rate = (
        round((100.0 * (bounce["hard"] + bounce["block"])) / denom, 1)
        if (inbox["delivered"] + inbox["bounced"]) > 0
        else None
    )
    alerts: list[dict[str, Any]] = []
    complaint_max = float(thresholds.get("spamComplaintRateMaxPct", 0.1))
    inbox_min = float(thresholds.get("inboxRateMinPct", 99.0))
    bounce_max = float(thresholds.get("bounceRateMaxPct", 2.0))
    if spam["complaint_rate_pct"] is not None and spam["complaint_rate_pct"] > complaint_max:
        alerts.append(
            {
                "code": "spam_complaint_high",
                "message": (
                    f"Spam complaint rate {spam['complaint_rate_pct']}% exceeds {complaint_max}%"
                ),
                "value": spam["complaint_rate_pct"],
                "threshold": complaint_max,
            }
        )
    if inbox["inbox_rate_pct"] is not None and inbox["inbox_rate_pct"] < inbox_min:
        alerts.append(
            {
                "code": "inbox_rate_low",
                "message": (
                    f"Inbox placement proxy {inbox['inbox_rate_pct']}% below {inbox_min}%"
                ),
                "value": inbox["inbox_rate_pct"],
                "threshold": inbox_min,
            }
        )
    if bounce_rate is not None and bounce_rate > bounce_max:
        alerts.append(
            {
                "code": "bounce_rate_high",
                "message": f"Hard/block bounce rate {bounce_rate}% exceeds {bounce_max}%",
                "value": bounce_rate,
                "threshold": bounce_max,
            }
        )
    return {
        "ok": len(alerts) == 0,
        "inbox_rate_pct": inbox["inbox_rate_pct"],
        "spam_complaint_rate_pct": spam["complaint_rate_pct"],
        "bounce_rate_pct": bounce_rate,
        "alerts": alerts,
        "thresholds": thresholds,
    }


def generate_setup_guide(
    *,
    domain: str,
    transactional_domain: str,
    marketing_domain: str,
    sending_services: list[SendingService] | None = None,
    dmarc_policy: DmarcPolicy = "none",
    dkim_selector: str = "mail",
    rua: str | None = None,
) -> str:
    services = sending_services or ["resend"]
    spf = generate_spf_record(transactional_domain, services)
    dkim = generate_dkim_record(transactional_domain, dkim_selector)
    dmarc = generate_dmarc_record(transactional_domain, dmarc_policy, rua=rua, subdomain_policy="none")
    return "\n".join(
        [
            f"# Email DNS setup for {domain}",
            "",
            f"Transactional sender: `{transactional_domain}`",
            f"Marketing sender: `{marketing_domain}` (separate identity)",
            "",
            "## 1. SPF",
            f"- Value: `{spf['value']}`",
            "",
            "## 2. DKIM (2048-bit)",
            f"- Host: `{dkim['record']['host']}.{transactional_domain}`",
            "- Store private key only in ESP/vault; never commit it.",
            "",
            "## 3. DMARC (start at p=none)",
            f"- Host: `{dmarc['host']}`",
            f"- Value: `{dmarc['value']}`",
            "- Progression: p=none -> p=quarantine -> p=reject after clean reports.",
            "",
            "## 4. Warm-up",
            "- Start at 50 sends/day; double every 3 days for 2-4 weeks.",
        ]
    )
