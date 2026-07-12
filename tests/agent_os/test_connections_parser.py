"""Prompt 277 connections parser tests."""

from __future__ import annotations

from keprix.agent_os.connections_parser import parse_connections_md, roundtrip_connections_md


FIXTURE = """# Connections

## revenue
- label: Revenue
- status: live
- tools: [stripe, sheets]
- integration_ref: stripe
- service_account: true
- notes: bot account

## calendar
- label: Calendar
- status: configuring
- tools: [google-workspace]
- integration_ref: google-workspace
- service_account: true
- notes: group account
"""


def test_connections_parser_reads_domains() -> None:
    domains = parse_connections_md(FIXTURE)
    revenue = next(domain for domain in domains if domain.id == "revenue")

    assert revenue.status == "live"
    assert revenue.tools == ["stripe", "sheets"]
    assert revenue.service_account is True
    assert len(domains) == 7


def test_connections_roundtrip_preserves_status_and_tools() -> None:
    rendered = roundtrip_connections_md(FIXTURE)
    domains = parse_connections_md(rendered)
    calendar = next(domain for domain in domains if domain.id == "calendar")

    assert calendar.status == "configuring"
    assert calendar.tools == ["google-workspace"]
