# Brand Boundary

**Status:** Authoritative for the `keprix/` workspace.
**Date:** 5 July 2026

This document defines the hard separation between the open-source stack and the
commercial Carina stack. If another doc disagrees, this file wins for `keprix/`.

## Why Keprix

In ancient Egypt, the sun did not simply rise. It was pushed.

Each morning, Keprix - the scarab - rolled the disc of the sun up through the
eastern horizon into the sky. Not because a greater god commanded it. Because
transformation was its nature.

The Egyptians gave this force a name from the verb "kheper": to come into being,
to become, to transform. Keprix was not a god who existed eternally and
unchanging. Keprix was the act of becoming itself. Every morning, the sun was
reborn. Every morning, Keprix rolled it into being again.

The scarab was chosen for this role because it appeared to create life from
nothing: rolling a ball across the desert floor, then emerging young beetles
from that ball as if from nowhere. Self-created. Self-renewing. The Egyptians
called Keprix "he who comes into being by himself."

This is exactly what this software is. Keprix is the adaptive AI operating
system that becomes the tool you need. It builds new tools when existing ones
fall short (Prompt 36: self-coding agent). It adapts its posture to each
workspace (Prompt 98: coding posture detection). It rolls its capabilities
forward with each session. Self-created, self-renewing, without ceiling.

The scarab rolled the sun across the sky. Keprix rolls intelligence forward.

## Two stacks

| Stack | Products | Licence | Audience |
| --- | --- | --- | --- |
| **Commercial** | Carina · Aiva · Scout | Proprietary / paid services | Businesses, enterprises |
| **Open source** | Keprix · Petraclus (Community) | MIT (Keprix); OSS defensive tier (Petraclus Community) | Developers, builders, security practitioners |

## Rules

### Keprix

- Product name is **Keprix**, never "Carina Keprix".
- MIT licence. No Carina trademark in user-facing copy, package names, or env vars.
- No Aiva Keys, no `keys.carinaai.uk`, no in-app upsell to Aiva.
- No "enterprise edition is Carina Aiva" messaging.
- Local **developer identity** only (`keprix init`); no remote licence server.
- Scout is an **optional third-party connector** (`labyrinthscout.com`), not bundled.
- VERLOX may show **"Sponsored by Carina"** on the Keprix website/README only. Do not use "Powered by Carina" (Keprix is a new AI agent OS, not a Carina fork).

### Petraclus

- Product name is **Petraclus**, not "Carina Petraclus".
- **Community:** open source, defensive and research tooling only.
- **Pro / Team:** commercial tiers; offensive workflows, case management, reporting, Scout integration.
- Keys validate at **`keys.petraclus.uk`** (Petraclus key server), not `keys.carinaai.uk`.
- Bundles the official **Keprix** Docker image as AI backbone via HTTP/SDK.
- Scout discount for Pro/Team is a **marketing integration**, not a Carina family bundle.

### Commercial (lives outside this workspace)

- **Carina:** managed platform runtime (private).
- **Aiva:** customer product; copy says **"Powered by Carina"**, never "built on Keprix".
- **Scout:** standalone governance product; connectors for Keprix and Petraclus, also sold to non-Verlox agent stacks.
- Aiva billing and Aiva Keys stay on the Carina commercial infrastructure.

## Integration without brand mixing

| Link | Allowed | Not allowed |
| --- | --- | --- |
| Petraclus → Keprix SDK | Yes | Petraclus forking Keprix code |
| Keprix → Scout connector | Yes (optional) | Scout bundled free in Keprix |
| Petraclus → Scout connector | Yes (Pro/Team) | Scout marketed as part of Carina in OSS repos |
| Marketing: "Works with Scout" | Yes | "Part of the Carina platform" on OSS repos |
| Marketing: "Sponsored by Carina" | Yes on Keprix site/README | "Powered by Carina" on Keprix |

## Naming reference (Keprix)

| Context | Name |
| --- | --- |
| Product name | Keprix |
| Python package | `keprix` |
| PyPI / pip | `keprix` |
| CLI | `keprix` |
| Module invocation | `python -m keprix` |
| Env prefix | `KEPRIX_` |
| Home directory | `~/.keprix` |
| Data directory | `/data/keprix` |
| GitHub repo | `malike2356/keprix` |
| Docs | `https://github.com/malike2356/keprix` (until public docs site ships) |

## Naming reference (Petraclus)

| Context | Name |
| --- | --- |
| Key server | `https://keys.petraclus.uk` |
| Key prefix | `PETRA-{TIER}-...` |
| AI backbone | Keprix at `http://keprix:3333` (internal Docker network) |

## Removed from Keprix (do not reintroduce)

- Prompt `01-aiva-key-system-and-feature-gate.md` (replaced by `01-developer-identity-and-local-access.md`)
- Prompts `47`, `48`, `49` (Aiva upsell stubs; archived)
- Cyber feature tiers in Keprix (live in Petraclus only)
