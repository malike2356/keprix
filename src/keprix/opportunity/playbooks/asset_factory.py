"""Asset Factory playbook for the Opportunity Engine."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from keprix.opportunity.approvals import request_approval
from keprix.opportunity.playbooks.offer_builder import validate_no_false_proof, validate_no_guaranteed_income
from keprix.opportunity.playbooks.offer_doc_generator import (
    CanonicalOfferDoc,
    build_canonical_offer_from_meta,
    load_agent_memory_brief,
    load_canonical_offer_doc,
)
from keprix.opportunity.playbooks.validation_score import ValidationBlockedError, can_proceed_to_assets
from keprix.opportunity.safety import run_content_safety_checks
from keprix.opportunity.workspace import read_opportunity_json, update_opportunity_json

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

MAIN_ARTIFACTS = [
    "07-funnel.md",
    "08-content-assets.md",
    "09-ads.md",
    "10-sales-deck.md",
]

DEFAULT_ASSET_FILES = [
    "landing-page.md",
    "lead-magnet.md",
    "email-nurture-sequence.md",
    "linkedin-posts.md",
    "short-video-scripts.md",
    "ad-copy.md",
    "sales-deck.md",
    "logo-brief.md",
    "brand-brief.md",
]

_HIGH_PRESSURE_RE = re.compile(
    r"\b(act now|limited time only|don't miss out|last chance|expires tonight)\b",
    re.I,
)
_INVENTED_REVENUE_RE = re.compile(
    r"\b(\$[\d,]+k? (mrr|arr|revenue)|\d+% (revenue|roi) in \d+ days)\b",
    re.I,
)

_DRAFT_BANNER = "STATUS: DRAFT - not published. Approval required before launch.\n\n"


class AssetFactoryInput(BaseModel):
    brand_preferences: dict[str, Any] = Field(default_factory=dict)
    asset_selection: list[str] = Field(default_factory=list)


class MissingOfferDocError(FileNotFoundError):
    """Raised when the canonical offer doc is not available."""


class UnsupportedClaimError(Exception):
    """Raised when generated copy violates offer doc claim rules."""

    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        super().__init__("; ".join(violations))


def _template(name: str) -> str:
    return (_TEMPLATES_DIR / name).read_text(encoding="utf-8")


def _apply_template(template: str, replacements: dict[str, str]) -> str:
    body = template
    for key, value in replacements.items():
        body = body.replace(key, value)
    return body


def _bullet_lines(items: list[str]) -> str:
    if not items:
        return "- None documented"
    return "\n".join(f"- {item}" for item in items)


def resolve_offer_context(opportunity_id: str) -> tuple[CanonicalOfferDoc, str, str, dict[str, Any]]:
    """Load canonical offer doc, memory brief, and structured offer fields."""
    meta = read_opportunity_json(opportunity_id)
    completed = meta.get("completed_phases") or []
    if "offer_doc" not in completed and not meta.get("canonical_offer"):
        raise MissingOfferDocError(
            f"Canonical offer doc not ready for {opportunity_id}; run offer_doc phase first",
        )
    offer_md = load_canonical_offer_doc(opportunity_id)
    if meta.get("canonical_offer"):
        doc = CanonicalOfferDoc(**meta["canonical_offer"])
    else:
        doc = build_canonical_offer_from_meta(meta)
    memory_brief = ""
    try:
        memory_brief = load_agent_memory_brief(opportunity_id)
    except FileNotFoundError:
        pass
    return doc, offer_md, memory_brief, meta


def _copy_for_claim_validation(text: str) -> str:
    """Strip sections that document forbidden terms (not promotional copy)."""
    lines: list[str] = []
    skip = False
    for line in text.splitlines():
        norm = line.strip().lower()
        if any(
            marker in norm
            for marker in (
                "words to avoid",
                "avoid:",
                "never make these claims",
                "claims agents must not",
                "claims forbidden",
            )
        ):
            skip = True
            continue
        if skip and norm.startswith("#"):
            skip = False
        if skip:
            continue
        lines.append(line)
    return "\n".join(lines)


def validate_asset_claims(text: str, *, meta: dict[str, Any], doc: CanonicalOfferDoc) -> list[str]:
    """Return violations when asset copy breaks offer doc claim rules."""
    check_text = _copy_for_claim_validation(text)
    violations: list[str] = []
    violations.extend(validate_no_guaranteed_income(check_text))
    violations.extend(
        validate_no_false_proof(check_text, existing_assets=list(meta.get("existing_assets") or [])),
    )
    if _HIGH_PRESSURE_RE.search(check_text):
        violations.append("High-pressure or deceptive urgency language is not allowed")
    if _INVENTED_REVENUE_RE.search(check_text):
        violations.append("Invented revenue or ROI results are not allowed")
    forbidden = meta.get("claims_forbidden") or doc.claims_forbidden
    for claim in forbidden:
        lowered = claim.lower()
        if "guaranteed income" in lowered or "guaranteed revenue" in lowered:
            if re.search(r"(?<!no )\bguaranteed (income|revenue|profit)\b", check_text, re.I):
                violations.append(f"Violates forbidden claim: {claim}")
        if "fabricated case" in lowered and re.search(r"\b(case study:|our client achieved)\b", check_text, re.I):
            violations.append(f"Violates forbidden claim: {claim}")
    return violations


def _proof_placeholder(doc: CanonicalOfferDoc) -> str:
    if doc.proof_needed:
        return (
            "[PROOF PLACEHOLDER] Add verified proof before publish:\n"
            + _bullet_lines(doc.proof_needed)
        )
    return "[PROOF PLACEHOLDER] No verified case studies on file. Do not invent customer outcomes."


def _brand_tone(brand_preferences: dict[str, Any]) -> str:
    tone = str(brand_preferences.get("tone") or "professional, evidence-led")
    colors = brand_preferences.get("colors") or []
    if colors:
        return f"{tone}; palette: {', '.join(str(c) for c in colors)}"
    return tone


def render_funnel_markdown(doc: CanonicalOfferDoc) -> str:
    return (
        f"{_DRAFT_BANNER}"
        f"# Funnel\n\n"
        f"Offer: {doc.offer_name}\n"
        f"ICP: {doc.primary_icp}\n\n"
        f"## Awareness\n"
        f"- Educational content on {doc.core_pain.lower()} for {doc.target_market}\n"
        f"- LinkedIn and short-form scripts in `assets/`\n\n"
        f"## Consideration\n"
        f"- Lead magnet: validation checklist aligned to {doc.unique_mechanism}\n"
        f"- Email nurture sequence (draft in `assets/email-nurture-sequence.md`)\n\n"
        f"## Conversion\n"
        f"- Landing page draft with CTA to review offer\n"
        f"- {doc.pricing_summary or 'Pricing review call'}\n\n"
        f"## Strategy\n{doc.funnel_strategy}\n\n"
        f"**Approval note:** Publishing landing pages, ads, or outbound requires explicit approval.\n"
    )


def render_content_assets_markdown(doc: CanonicalOfferDoc) -> str:
    return (
        f"{_DRAFT_BANNER}"
        f"# Content Assets\n\n"
        f"Target: {doc.primary_icp}\n"
        f"Pain focus: {doc.core_pain}\n\n"
        f"## Planned assets\n"
        f"{_bullet_lines(doc.deliverables)}\n\n"
        f"## Content strategy\n{doc.content_strategy}\n\n"
        f"## Folder outputs\n"
        f"{_bullet_lines([f'assets/{name}' for name in DEFAULT_ASSET_FILES])}\n\n"
        f"**Approval note:** Do not publish until proof placeholders are replaced.\n"
    )


def _ad_hooks(doc: CanonicalOfferDoc) -> list[str]:
    base = doc.core_pain.lower()
    icp = doc.primary_icp
    return [
        f"Still wrestling with {base}?",
        f"{icp}: a faster path to validation",
        f"What if {doc.unique_mechanism.lower()}?",
        f"Stop guessing in {doc.target_market}",
        f"Evidence before launch for {icp}",
        f"Draft offer review without hype",
        f"Validate {doc.target_market} demand with playbooks",
        f"Governed launch prep for {icp}",
        f"Clarity on {base} without invented proof",
        f"Pilot-ready messaging for {doc.offer_name}",
        f"Approval-gated assets for {doc.target_market}",
    ]


def render_ads_markdown(doc: CanonicalOfferDoc) -> str:
    hooks = _ad_hooks(doc)
    scripts = [
        f"Hook: {hooks[i]}\nBody: {doc.core_promise}\nCTA: Request offer review\n"
        for i in range(5)
    ]
    concepts = [
        f"Static concept {i + 1}: headline '{hooks[i]}'; visual: {doc.primary_icp} workflow; CTA: Learn more"
        for i in range(5)
    ]
    return (
        f"{_DRAFT_BANNER}"
        f"# Ads (draft)\n\n"
        f"NOTE: Ad launch requires explicit approval before publishing.\n\n"
        f"## Ad hooks (10+)\n"
        f"{_bullet_lines(hooks)}\n\n"
        f"## Short ad scripts (5)\n\n"
        + "\n".join(f"### Script {i + 1}\n{script}" for i, script in enumerate(scripts))
        + f"\n\n## Static ad concepts (5)\n{_bullet_lines(concepts)}\n\n"
        f"**Approval note:** No unsupported claims; verify copy against forbidden claims list.\n"
    )


def render_main_sales_deck_markdown(doc: CanonicalOfferDoc) -> str:
    slides = [
        ("Title", doc.offer_name, f"Present to {doc.primary_icp}"),
        ("Problem", doc.core_pain, "Use exact ICP pain language"),
        ("Market", doc.target_market, "Demand context from research"),
        ("Promise", doc.core_promise, "No invented outcomes"),
        ("Mechanism", doc.unique_mechanism, "How delivery works"),
        ("Deliverables", _bullet_lines(doc.deliverables), "Productised scope"),
        ("Differentiation", doc.differentiation, "Vs competitors"),
        ("Pricing", doc.pricing_summary or "See pricing artifact", "Confirm before external use"),
        ("Proof", _proof_placeholder(doc), "Replace before pitching"),
        ("Objections", "Budget, timing, proof", "See objection section in assets/sales-deck.md"),
        ("Next steps", "Offer review call", "Approval required for outbound"),
    ]
    body = "\n\n".join(
        f"### Slide {i + 1}: {title}\n**Content:** {content}\n**Speaker notes:** {notes}"
        for i, (title, content, notes) in enumerate(slides)
    )
    return (
        f"{_DRAFT_BANNER}"
        f"# Sales Deck Outline\n\n"
        f"Offer: {doc.offer_name}\n\n"
        f"{body}\n\n"
        f"**Approval note:** External deck use requires human approval.\n"
    )


def render_landing_page(doc: CanonicalOfferDoc, brand_preferences: dict[str, Any]) -> str:
    faq = _bullet_lines(
        [
            f"Who is this for? {doc.primary_icp}",
            f"What problem does it solve? {doc.core_pain}",
            f"How is this different? {doc.differentiation}",
            "Is there a guarantee? See offer doc; no income guarantees.",
        ],
    )
    compliance = _bullet_lines(doc.compliance_notes) if doc.compliance_notes else "- Standard marketing compliance review required"
    replacements = {
        "{{headline}}": doc.positioning[:120],
        "{{subheadline}}": f"For {doc.primary_icp} facing {doc.core_pain.lower()}",
        "{{cta}}": "Request offer review (draft)",
        "{{core_pain}}": doc.core_pain,
        "{{primary_icp}}": doc.primary_icp,
        "{{target_market}}": doc.target_market,
        "{{unique_mechanism}}": doc.unique_mechanism,
        "{{deliverables}}": _bullet_lines(doc.deliverables),
        "{{proof_section}}": _proof_placeholder(doc),
        "{{core_promise}}": doc.core_promise,
        "{{pricing_summary}}": doc.pricing_summary or "Pricing on review call",
        "{{faq}}": faq,
        "{{compliance}}": compliance,
    }
    tone_note = f"\n\nBrand tone: {_brand_tone(brand_preferences)}\n"
    return _apply_template(_template("landing-page-template.md"), replacements) + tone_note


def _email_block(index: int, *, subject: str, preview: str, body: str, cta: str, approval: str) -> str:
    return (
        f"## Email {index}\n"
        f"**Subject:** {subject}\n"
        f"**Preview:** {preview}\n"
        f"**Body:**\n{body}\n"
        f"**CTA:** {cta}\n"
        f"**Approval notes:** {approval}\n"
    )


def render_email_nurture(doc: CanonicalOfferDoc) -> str:
    emails = [
        _email_block(
            1,
            subject=f"The real cost of {doc.core_pain.lower()}",
            preview=f"For {doc.primary_icp}",
            body=f"If you are in {doc.target_market}, {doc.core_pain.lower()} slows every launch decision.",
            cta="Read the problem framing",
            approval="Low risk; educational only",
        ),
        _email_block(
            2,
            subject="Evidence before launch",
            preview=doc.unique_mechanism[:60],
            body=f"Our approach: {doc.unique_mechanism}. No invented case studies.",
            cta="See how it works",
            approval="Low risk",
        ),
        _email_block(
            3,
            subject=f"What {doc.primary_icp} should validate first",
            preview="A practical checklist",
            body=f"Validate demand, ICP fit, and offer clarity before spending on ads.",
            cta="Download checklist (draft)",
            approval="Lead magnet; consent and privacy review if live",
        ),
        _email_block(
            4,
            subject=doc.core_promise[:70],
            preview="Offer overview",
            body=f"{doc.core_promise} Deliverables: {', '.join(doc.deliverables[:3])}.",
            cta="Review offer details",
            approval="Medium risk; pricing claims must match offer doc",
        ),
        _email_block(
            5,
            subject="Common objections (answered honestly)",
            preview="Proof, pricing, timing",
            body="We use proof placeholders until verified assets exist. No revenue guarantees.",
            cta="Book offer review",
            approval="Medium risk; sales conversation",
        ),
        _email_block(
            6,
            subject="Ready for an offer review?",
            preview="Draft assets available",
            body=f"Landing page, ads, and deck drafts are ready for internal review for {doc.offer_name}.",
            cta="Request review call",
            approval="Outbound/sales; explicit approval before send",
        ),
    ]
    replacements = {
        "{{offer_name}}": doc.offer_name,
        "{{primary_icp}}": doc.primary_icp,
        "{{emails}}": "\n".join(emails),
    }
    return _apply_template(_template("email-nurture-template.md"), replacements)


def render_asset_sales_deck(doc: CanonicalOfferDoc) -> str:
    slides = "\n\n".join(
        f"### Slide {i + 1}: {title}\n{content}\n**Speaker notes:** {notes}"
        for i, (title, content, notes) in enumerate(
            [
                ("Opening", doc.offer_name, "Set expectations; draft deck"),
                ("ICP pain", doc.core_pain, "Use exact pain language"),
                ("Promise", doc.core_promise, "No fabricated outcomes"),
                ("Mechanism", doc.unique_mechanism, doc.funnel_strategy),
                ("Deliverables", _bullet_lines(doc.deliverables), ""),
                ("Competitive gap", doc.differentiation, doc.competitor_positioning),
                ("Pricing", doc.pricing_summary or "TBD", "Confirm live pricing"),
                ("Proof plan", _proof_placeholder(doc), ""),
                ("Content plan", doc.content_strategy, ""),
                ("Outreach", doc.outreach_strategy, "Approval before outbound"),
                ("Close", "Offer review + next steps", "Human approval for launch"),
            ],
        )
    )
    objections = _bullet_lines(
        [
            "We need proof: use placeholders until verified assets exist",
            "Price concern: align to pricing artifact and delivery scope",
            "Timing: emphasize validation-first launch path",
            "Compliance: route regulated claims to review",
        ],
    )
    replacements = {
        "{{offer_name}}": doc.offer_name,
        "{{primary_icp}}": doc.primary_icp,
        "{{slides}}": slides,
        "{{objections}}": objections,
    }
    return _apply_template(_template("sales-deck-template.md"), replacements)


def render_lead_magnet(doc: CanonicalOfferDoc) -> str:
    return (
        f"{_DRAFT_BANNER}"
        f"# Lead Magnet Draft\n\n"
        f"Title: {doc.target_market} validation checklist\n"
        f"Audience: {doc.primary_icp}\n"
        f"Pain: {doc.core_pain}\n\n"
        f"## Outline\n"
        f"{_bullet_lines(['Demand signals', 'ICP fit', 'Offer clarity', 'Proof plan', 'Launch approval gates'])}\n"
    )


def render_linkedin_posts(doc: CanonicalOfferDoc) -> str:
    posts = [
        f"Post {i + 1}: {hook}\n\n{doc.core_promise}\n\n#draft #approval-required"
        for i, hook in enumerate(_ad_hooks(doc)[:5])
    ]
    return f"{_DRAFT_BANNER}# LinkedIn Posts\n\n" + "\n\n---\n\n".join(posts)


def render_video_scripts(doc: CanonicalOfferDoc) -> str:
    scripts = [
        (
            f"## Script {i + 1}\n"
            f"Hook: {hook}\n"
            f"Problem: {doc.core_pain}\n"
            f"Mechanism: {doc.unique_mechanism}\n"
            f"CTA: Comment 'review' for draft offer overview (approval required before posting)"
        )
        for i, hook in enumerate(_ad_hooks(doc)[5:8])
    ]
    return f"{_DRAFT_BANNER}# Short Video Scripts\n\n" + "\n\n".join(scripts)


def render_ad_copy_file(doc: CanonicalOfferDoc) -> str:
    return render_ads_markdown(doc).replace("# Ads (draft)", "# Ad Copy Pack")


def render_logo_brief(doc: CanonicalOfferDoc, brand_preferences: dict[str, Any]) -> str:
    style = str(brand_preferences.get("logo_style") or "modern, trustworthy, minimal")
    return (
        f"{_DRAFT_BANNER}"
        f"# Logo Brief\n\n"
        f"Brand: {doc.offer_name}\n"
        f"Audience: {doc.primary_icp}\n"
        f"Tone: {_brand_tone(brand_preferences)}\n"
        f"Style direction: {style}\n"
        f"Words to reflect: {', '.join(doc.words_to_use)}\n"
        f"Avoid: {', '.join(doc.words_to_avoid)}\n\n"
        f"**Note:** No final trademark claims. Legal review required before filing.\n"
    )


def render_brand_brief(doc: CanonicalOfferDoc, brand_preferences: dict[str, Any]) -> str:
    prompt = (
        f"Create brand visuals for {doc.offer_name}, serving {doc.primary_icp}. "
        f"Tone: {_brand_tone(brand_preferences)}. "
        f"Emphasize {doc.unique_mechanism}. Avoid hype and invented proof."
    )
    return (
        f"{_DRAFT_BANNER}"
        f"# Brand Brief\n\n"
        f"## Positioning\n{doc.positioning}\n\n"
        f"## Voice\n{_brand_tone(brand_preferences)}\n\n"
        f"## Words to use\n{_bullet_lines(doc.words_to_use)}\n\n"
        f"## Words to avoid\n{_bullet_lines(doc.words_to_avoid)}\n\n"
        f"## Image generation prompt (draft)\n{prompt}\n\n"
        f"**Approval note:** No trademark or regulated claims in generated imagery.\n"
    )


def build_all_assets(
    *,
    doc: CanonicalOfferDoc,
    meta: dict[str, Any],
    brand_preferences: dict[str, Any] | None = None,
    asset_selection: list[str] | None = None,
) -> dict[str, str]:
    brand_preferences = brand_preferences or dict(meta.get("brand_preferences") or {})
    selected = set(asset_selection or DEFAULT_ASSET_FILES)
    files: dict[str, str] = {
        "07-funnel.md": render_funnel_markdown(doc),
        "08-content-assets.md": render_content_assets_markdown(doc),
        "09-ads.md": render_ads_markdown(doc),
        "10-sales-deck.md": render_main_sales_deck_markdown(doc),
    }
    asset_renderers: dict[str, Any] = {
        "landing-page.md": lambda: render_landing_page(doc, brand_preferences),
        "lead-magnet.md": lambda: render_lead_magnet(doc),
        "email-nurture-sequence.md": lambda: render_email_nurture(doc),
        "linkedin-posts.md": lambda: render_linkedin_posts(doc),
        "short-video-scripts.md": lambda: render_video_scripts(doc),
        "ad-copy.md": lambda: render_ad_copy_file(doc),
        "sales-deck.md": lambda: render_asset_sales_deck(doc),
        "logo-brief.md": lambda: render_logo_brief(doc, brand_preferences),
        "brand-brief.md": lambda: render_brand_brief(doc, brand_preferences),
    }
    for name, renderer in asset_renderers.items():
        if name in selected:
            files[f"assets/{name}"] = renderer()
    return files


def _enforce_claim_rules(files: dict[str, str], *, meta: dict[str, Any], doc: CanonicalOfferDoc) -> None:
    violations: list[str] = []
    for path, content in files.items():
        violations.extend(validate_asset_claims(content, meta=meta, doc=doc))
    if violations:
        raise UnsupportedClaimError(sorted(set(violations)))


async def run_asset_factory_playbook(
    *,
    workspace_id: str,
    opportunity_id: str,
    request: AssetFactoryInput | None = None,
) -> dict[str, str]:
    request = request or AssetFactoryInput()
    meta = read_opportunity_json(opportunity_id)
    try:
        doc, offer_md, memory_brief, meta = resolve_offer_context(opportunity_id)
    except FileNotFoundError as exc:
        raise MissingOfferDocError(str(exc)) from exc

    override = bool(meta.get("validation_override"))
    allowed, blocked = can_proceed_to_assets(opportunity_id, user_override=override)
    if not allowed and blocked is not None:
        raise ValidationBlockedError(blocked)

    files = build_all_assets(
        doc=doc,
        meta=meta,
        brand_preferences=request.brand_preferences or dict(meta.get("brand_preferences") or {}),
        asset_selection=request.asset_selection or None,
    )

    _enforce_claim_rules(files, meta=meta, doc=doc)

    combined = offer_md + memory_brief + "\n".join(files.values())
    run_content_safety_checks(opportunity_id=opportunity_id, text=combined)

    request_approval(
        workspace_id=workspace_id,
        opportunity_id=opportunity_id,
        action="create_ad",
        reason="Asset factory drafts prepared; publishing requires approval",
    )

    update_opportunity_json(
        opportunity_id,
        {
            "phase": "asset_factory",
            "assets_generated": sorted(files.keys()),
            "asset_factory_status": "draft",
        },
    )

    return files
