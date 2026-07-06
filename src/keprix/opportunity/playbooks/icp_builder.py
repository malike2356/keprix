"""ICP Builder playbook for the Opportunity Engine."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from keprix.opportunity.approvals import request_approval
from keprix.opportunity.playbooks.offer_builder import detect_regulated_industry
from keprix.opportunity.safety import run_content_safety_checks
from keprix.opportunity.workspace import read_artifact, read_opportunity_json, update_opportunity_json, write_artifact

_PREDATORY_RE = re.compile(
    r"\b(target the vulnerable|exploit|predatory|deceive|mislead)\b",
    re.I,
)


class IcpProfile(BaseModel):
    name: str
    summary: str
    company_profile: str
    budget_indicator: str
    where_to_find: list[str]
    is_primary: bool = False


class IcpBuilderInput(BaseModel):
    niche: str
    offer_name: str
    who_it_is_for: str
    pains: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    messaging_angles: list[str] = Field(default_factory=list)


def validate_no_predatory_targeting(text: str) -> list[str]:
    if _PREDATORY_RE.search(text):
        return ["Predatory targeting language detected"]
    return []


def _read_optional(opportunity_id: str, filename: str) -> str:
    try:
        return read_artifact(opportunity_id, filename)
    except FileNotFoundError:
        return ""


def _extract_offer_fields(offer_md: str, meta: dict[str, Any]) -> dict[str, str]:
    offer = meta.get("offer") or {}
    name = str(offer.get("offer_name") or "")
    who = str(offer.get("who_it_is_for") or "")
    if offer_md:
        for line in offer_md.splitlines():
            if line.startswith("## Offer Name") and not name:
                continue
            if name and who:
                break
    if not name and offer_md:
        idx = offer_md.find("## Offer Name")
        if idx >= 0:
            chunk = offer_md[idx:].splitlines()
            if len(chunk) > 2:
                name = chunk[2].strip()
    if not who and offer_md:
        idx = offer_md.find("## Who It Is For")
        if idx >= 0:
            chunk = offer_md[idx:].splitlines()
            if len(chunk) > 2:
                who = chunk[2].strip()
    return {
        "offer_name": name or str(meta.get("title", "Offer")),
        "who_it_is_for": who or str(meta.get("niche", "buyers")),
    }


def build_icp_profiles(inp: IcpBuilderInput) -> tuple[IcpProfile, list[IcpProfile]]:
    primary = IcpProfile(
        name="Primary ICP",
        summary=inp.who_it_is_for,
        company_profile=f"Growth-stage operators in {inp.niche} with active pain around {inp.pains[0] if inp.pains else 'workflow friction'}",
        budget_indicator="Monthly software budget $100-$500; pilot-friendly",
        where_to_find=[
            f"Niche communities discussing {inp.niche}",
            "LinkedIn groups and public forums (no scraping behind logins)",
            "Industry newsletters and review sites",
        ],
        is_primary=True,
    )
    secondary = [
        IcpProfile(
            name="Secondary ICP: Agency partner",
            summary=f"Agencies serving {inp.niche} clients",
            company_profile="5-20 person agency with repeatable client workflows",
            budget_indicator="Per-client pass-through or $200-$800/mo tool stack",
            where_to_find=["Agency owner podcasts", "Partner marketplaces", "Freelance platforms"],
        ),
        IcpProfile(
            name="Secondary ICP: Internal ops lead",
            summary=f"Operations leader at a {inp.niche} organization",
            company_profile="Mid-market team modernizing manual processes",
            budget_indicator="Department budget; prefers ROI proof before annual commit",
            where_to_find=["Ops and RevOps communities", "Public job posts for ops roles"],
        ),
    ]
    return primary, secondary


def render_icp_doc(
    *,
    inp: IcpBuilderInput,
    primary: IcpProfile,
    secondary: list[IcpProfile],
    regulated: bool,
) -> str:
    pain_line = inp.pains[0] if inp.pains else inp.niche
    resonate = inp.messaging_angles[0] if inp.messaging_angles else f"Relief from {pain_line}"
    objections = inp.objections[:5] or [
        "Unclear ROI without pilot data",
        "Migration effort from current tools",
    ]
    disqualifiers = [
        "No budget and no timeline for pilot",
        "Requires guaranteed revenue outcomes",
        "Needs fully done-for-you outbound without approval workflow",
        "Operates outside supported compliance boundaries",
    ]
    if regulated:
        disqualifiers.append("Cannot meet sector compliance requirements")

    sec_blocks = []
    for profile in secondary:
        sec_blocks.append(
            f"### {profile.name}\n{profile.summary}\n\n"
            f"- Company: {profile.company_profile}\n"
            f"- Budget: {profile.budget_indicator}\n"
            f"- Where to find: {', '.join(profile.where_to_find)}",
        )

    compliance = ""
    if regulated:
        compliance = "\n\n> Compliance: regulated industry; obtain review before outbound campaigns.\n"

    return (
        f"# Ideal Customer Profile\n"
        f"{compliance}\n"
        f"## Primary ICP\n\n"
        f"**{primary.summary}**\n\n"
        f"- Company profile: {primary.company_profile}\n"
        f"- Budget indicators: {primary.budget_indicator}\n"
        f"- Where to find them: {', '.join(primary.where_to_find)}\n\n"
        f"## Secondary ICPs\n\n"
        f"{chr(10).join(sec_blocks)}\n\n"
        f"## Buyer Persona\n\n"
        f"Decision-oriented operator in {inp.niche}; feels {pain_line}; wants measurable validation.\n\n"
        f"## Company Profile\n\n"
        f"{primary.company_profile}\n\n"
        f"## Buying Trigger\n\n"
        f"- Urgent pain escalation or failed workaround\n"
        f"- New budget cycle or leadership mandate to modernize\n\n"
        f"## Budget Indicators\n\n"
        f"{primary.budget_indicator}\n\n"
        f"## Where To Find Them\n\n"
        + "\n".join(f"- {item}" for item in primary.where_to_find)
        + f"\n\n## Decision Makers\n\n"
        f"- Founder or GM for Starter tier\n"
        f"- Head of Operations or Revenue for Growth tier\n\n"
        f"## Influencers\n\n"
        f"- Team leads using manual workarounds\n"
        f"- Agency partners recommending tooling\n\n"
        f"## Objections\n\n"
        + "\n".join(f"- {obj}" for obj in objections)
        + f"\n\n## Message That Will Resonate\n\n"
        f"{resonate}\n\n"
        f"## Disqualification Criteria\n\n"
        + "\n".join(f"- {item}" for item in disqualifiers)
        + "\n"
    )


def build_icp_builder_input_from_meta(meta: dict[str, Any], *, offer_fields: dict[str, str]) -> IcpBuilderInput:
    pains = [str(p.get("pain", "")) for p in meta.get("top_pains", [])[:5] if p.get("pain")]
    return IcpBuilderInput(
        niche=str(meta.get("niche") or meta.get("title") or "market"),
        offer_name=offer_fields["offer_name"],
        who_it_is_for=offer_fields["who_it_is_for"],
        pains=pains,
        objections=list(meta.get("objections") or []),
        messaging_angles=list(meta.get("messaging_angles") or []),
    )


async def run_icp_builder_playbook(
    *,
    workspace_id: str,
    opportunity_id: str,
    request: IcpBuilderInput,
) -> str:
    meta = read_opportunity_json(opportunity_id)
    offer_md = _read_optional(opportunity_id, "05-offer-doc.md")
    pain_md = _read_optional(opportunity_id, "02-pain-mining.md")
    demand_md = _read_optional(opportunity_id, "01-market-demand.md")

    context = f"{request.niche} {offer_md[:400]} {pain_md[:400]} {demand_md[:400]}"
    regulated = detect_regulated_industry(context)

    primary, secondary = build_icp_profiles(request)
    icp_doc = render_icp_doc(
        inp=request,
        primary=primary,
        secondary=secondary,
        regulated=regulated,
    )

    issues = validate_no_predatory_targeting(icp_doc)
    if issues:
        icp_doc += "\n## Guardrail Notes\n" + "\n".join(f"- {i}" for i in issues) + "\n"

    run_content_safety_checks(opportunity_id=opportunity_id, text=icp_doc)
    write_artifact(opportunity_id, "03-icp.md", icp_doc)

    icp_payload = {
        "primary": primary.model_dump(),
        "secondary": [profile.model_dump() for profile in secondary],
        "disqualification_criteria": [
            "No budget and no timeline for pilot",
            "Requires guaranteed revenue outcomes",
            "Cannot meet compliance requirements" if regulated else "Outside supported niche",
        ],
    }
    update_opportunity_json(
        opportunity_id,
        {
            "phase": "icp_builder",
            "icp": icp_payload,
        },
    )
    request_approval(
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        action="send_outreach",
        reason="ICP complete; outbound campaigns require explicit approval",
    )
    return icp_doc
