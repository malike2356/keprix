# keprix - Prompt 91: Asset Factory Playbook

**Status:** Completed. Implementation in `src/keprix/opportunity/playbooks/asset_factory.py`,
`src/keprix/opportunity/templates/asset-factory-system.md` (plus landing, email, sales-deck templates),
`src/keprix/opportunity/workspace.py` (`write_opportunity_asset`), and
`tests/opportunity/test_asset_factory.py` (61 opportunity tests pass).

## Context

Build the Asset Factory playbook for Opportunity Engine.

This playbook generates the launch assets required to test or launch the offer. It creates drafts only. Publishing requires Launch Orchestrator approval.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
backend/opportunity/playbooks/asset_factory.py
backend/opportunity/templates/asset-factory-system.md
backend/opportunity/templates/landing-page-template.md
backend/opportunity/templates/email-nurture-template.md
backend/opportunity/templates/sales-deck-template.md
tests/opportunity/test_asset_factory.py
```

## Inputs

- Canonical offer doc.
- Agent memory brief.
- Validation score.
- Brand preferences, optional.
- Asset selection, optional.

## Assets To Generate

Generate the following by default:

```text
07-funnel.md
08-content-assets.md
09-ads.md
10-sales-deck.md
```

Also create an asset folder:

```text
workspace/opportunities/{slug}/assets/
  landing-page.md
  lead-magnet.md
  email-nurture-sequence.md
  linkedin-posts.md
  short-video-scripts.md
  ad-copy.md
  sales-deck.md
  logo-brief.md
  brand-brief.md
```

## Asset Requirements

Landing page:

- Hero section.
- Problem section.
- Unique mechanism.
- How it works.
- Proof section placeholder if proof is not available.
- Offer details.
- Pricing or CTA.
- FAQ.
- Compliance disclaimer if needed.

Email nurture:

- 5 to 7 emails.
- Each email has subject, preview text, body, CTA, and approval notes.

Ads:

- At least 10 ad hooks.
- At least 5 short ad scripts.
- At least 5 static ad concepts.
- No unsupported claims.

Sales deck:

- 10 to 12 slide outline.
- Speaker notes.
- Proof placeholders.
- Objection handling.

Logo and brand:

- Produce a brand brief and image generation prompt.
- Do not generate final trademark claims.

## Design And Copy Rules

- Use the exact ICP and pain language from the offer doc.
- Do not invent case studies.
- Do not invent revenue results.
- Do not use high-pressure or deceptive claims.
- Add approval notes for any asset that could create legal, financial, or compliance risk.

## Acceptance Criteria

- Generates all asset files.
- Uses the canonical offer doc as source of truth.
- Assets are drafts and not published.
- Claims are checked against allowed and forbidden claims.
- Tests cover asset file creation, unsupported claim detection, and missing offer doc handling.

