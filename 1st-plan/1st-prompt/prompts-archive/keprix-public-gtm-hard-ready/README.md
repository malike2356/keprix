# Keprix public GTM hard-ready (570-582)

**Status:** SUPERSEDED 2026-08-08 by prompts 600-618
**Date opened:** 2026-08-08  
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Programme **416-428** made Community self-host **soft READY** (public GitHub, curl
installer URL live, Docker docs, `keprixai.com` 200, surface GTM gate green).

Owner ask 2026-08-08: can the world download bare metal + Docker, are website
downloads correct, is Hermes-class terminal install ready, is TUI upgraded for
new modules, is desktop installable for new features, is git market-ready?

**Honest verdict today:** soft Community GTM yes; **hard / polished product GTM no**.

| # | Question | Verdict |
| --- | --- | --- |
| 1 | Bare metal download and use | PARTIAL (curl/git; no binary) |
| 2 | Self-hosted Docker | YES (docs + compose; needs clone + keys) |
| 3 | Website serves correct installable files | PARTIAL (instructions yes; binaries no) |
| 4 | Hermes-like one-command ready-to-use | PARTIAL (curl works; still setup + key) |
| 5 | TUI matches new GUI modules (CRM etc.) | NO |
| 6 | Desktop ready to install for new features | NO |
| 7 | Public git ready for strangers | PARTIAL |
| 8 | Overall market ready (polished) | NO |

Live facts (2026-08-08): GitHub anonymous 200; raw `install.sh` 200; keprixai.com
200; PyPI `keprix` 404; GitHub Releases count 0; desktop still Nous-branded.

Prior soft sign-off: `docs/architecture/public-gtm-signoff.md`  
Prior archive: `../prompts-archive/416-public-gtm-and-installer/`  
Gap map (stale vs READY; refresh in 571): `docs/architecture/public-gtm-gap-map.md`

## Relationship to worldwide distribution GTM

Sibling programme `../keprix-worldwide-distribution-gtm/` (IDs **600-618**) is the
full worldwide delivery closeout (PyPI, Docker Hub images, SBOM, canary, support).

This series **570-582** is the owner hard-questions DoD and ship gate. Execute
both without reopening 416-428. Prefer one agent owning a wave; cross-link
evidence so Release/desktop/TUI work is not duplicated blindly.

## Build order

See `ref-570-keprix-public-gtm-hard-ready-build-order.md`.

| ID | Prompt | Priority |
| --- | --- | --- |
| 570 | Overview inventory + hard GTM DoD | Must |
| 571 | Stranger docs + gap-map refresh | Must |
| 572 | Cold-VM curl install proof | Must |
| 573 | Public clone hygiene (`1st-plan` out of stranger path) | Must |
| 574 | First GitHub Release + tag + provenance | Must |
| 575 | Marketing hero CTA self-host vs hosted | Must |
| 576 | MIT SPDX / license badge accuracy | Nice |
| 577 | Desktop Verlox rebrand + download story | Must |
| 578 | Signed desktop artifacts or explicit defer | Must (owner choice) |
| 579 | TUI vs GUI honesty + Command Center scope | Must |
| 580 | TUI operator module bridges (CRM/Soft Wall deep links) | Nice |
| 581 | Optional PyPI / brew decision | Owner |
| 582 | Hard GTM ship gate + sign-off | Must |

## Done when

- [ ] Hard GTM gate script exits 0 without lying about binaries/desktop
- [ ] Cold VM curl proof logged in sign-off
- [ ] Gap map matches live HTTP facts
- [ ] Stranger clone does not require reading `1st-plan/`
- [ ] At least one GitHub Release with install notes (and desktop assets or explicit N/A)
- [ ] keprixai.com primary CTA matches self-host story
- [ ] Desktop Nous/Hermes branding removed or deferred in writing
- [ ] TUI docs honest about CRM/operator GUI scope
- [ ] `docs/architecture/public-gtm-hard-signoff.md` Verdict READY or BLOCKED with owners
