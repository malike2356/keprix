# Keprix Prompt 312: Subtle frosted glass visual treatment

## Status: DONE

## Priority

Nice, medium effort.

## Context

Product name "glass" is a data dashboard, not frosted CSS. Optional polish: light frosted panels using existing MUI CSS variables only.

## Goal

Apply a subtle frosted / translucent panel treatment on `/agent-os/glass` panels **only if** it still matches Keprix MUI tokens (light and dark). Do not invent a second design system, purple glow theme, or glassmorphism fashion kit.

## Tasks

1. Prototype on glass Paper panels using `backdrop-filter` + tokenized background opacity.
2. Verify contrast for text/tables (WCAG-ish readability).
3. Disable or tone down when `prefers-reduced-transparency` if practical.
4. Do not apply globally to all Agent OS pages unless it still looks native.

## Acceptance criteria

- [ ] Glass page uses token-based frosted panels without new color brand.
- [ ] Tables and chips remain readable in light and dark.
- [ ] No second theme package added.
- [ ] Easy kill-switch (CSS class or flag) if it regresses.

## Dependencies

After **303** (Ship defaults panel exists) so treatment covers final layout.

## Files likely touched

- `frontend/src/app/(workspace)/agent-os/glass/page.tsx`
- Optional small CSS module or sx tokens

## Related

- Build order: `prompts-archive/ref-301-agent-os-ui-polish-build-order.md`
- Design system: `ui/design-system/README.md`
