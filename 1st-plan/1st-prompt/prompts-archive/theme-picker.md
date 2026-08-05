# Theme picker: multi-skin switcher from UI CSS packs

## Goal

Wire the 40 named theme packs in `planning/prompts/UI/css/01-multi-theme-switching-*.css` into the Keprix Next.js frontend so users can pick a skin and light/dark mode from the top bar and Settings.

## Source of truth

- CSS packs: `/opt/lampp/htdocs/verlox/keprix/planning/prompts/UI/css/01-multi-theme-switching-{skin-id}.css`
- Each file defines `:root` (light) and `.dark` (dark) CSS custom properties (`--primary`, `--background`, `--foreground`, etc.)
- Tailwind `@theme inline` blocks are reference-only; strip them from runtime CSS (frontend uses MUI, not Tailwind)

## Architecture

1. **Build step** (`scripts/build-theme-skins.py`)
   - Read every `01-multi-theme-switching-*.css` file (skip malformed names like `*.csss`)
   - Emit `frontend/public/themes/skins.css` scoped as:
     - `html[data-skin="{id}"] { ...light vars... }`
     - `html.dark[data-skin="{id}"] { ...dark vars... }`
   - Emit `frontend/src/theme/skin-manifest.json` with `{ id, label, primary, background }` preview colors per skin

2. **Runtime**
   - `html` attributes: `data-skin="violet-bloom"`, class `dark` when dark mode
   - `localStorage`: `keprix_theme_skin`, `keprix_theme_mode` (existing)
   - Import `/themes/skins.css` in root layout
   - Extend `ThemeRegistry` with `skin`, `setSkin`, keep `mode` / `toggleMode`
   - Bridge CSS vars to MUI: `paletteFromCssVars()` reads `--primary`, `--background`, `--foreground`, `--border`, `--destructive`, `--secondary`, `--card`, `--muted-foreground` from `document.documentElement` and maps to `createKeprixTheme(mode, palette)`
   - Fallback to `ui/design-system/tokens/colors.json` when vars missing (SSR first paint)

3. **UI**
   - `ThemePickerMenu` compact control in `TopBar` (palette icon): skin grid + light/dark segmented control
   - `ThemeAppearancePanel` on Settings hub: full skin grid with labels and preview swatches
   - Default skin: `default` (from CSS pack) or `keprix` alias

## Files to create or change

| Path | Action |
|------|--------|
| `scripts/build-theme-skins.py` | Create build script |
| `frontend/public/themes/skins.css` | Generated |
| `frontend/src/theme/skin-manifest.json` | Generated |
| `frontend/src/theme/palette-from-css.ts` | CSS var to MUI palette bridge |
| `frontend/src/theme/keprix-theme.ts` | Accept optional palette override |
| `frontend/src/components/providers/ThemeRegistry.tsx` | Skin state + html attrs |
| `frontend/src/components/theme/ThemePickerMenu.tsx` | Top bar menu |
| `frontend/src/components/theme/ThemeAppearancePanel.tsx` | Settings panel |
| `frontend/src/components/shell/TopBar.tsx` | Add picker |
| `frontend/src/app/(workspace)/settings/page.tsx` | Appearance section |
| `frontend/src/app/layout.tsx` | Link skins.css, default `data-skin` on html |

## Acceptance criteria

- [ ] All valid CSS packs appear in picker (40 skins)
- [ ] Selecting a skin updates MUI colors immediately without reload
- [ ] Light/dark toggle still works and combines with selected skin
- [ ] Choice persists across reloads (`localStorage`)
- [ ] Top bar and Settings both control the same state
- [ ] No MUI Select out-of-range warnings; no hydration errors
- [ ] `python3 scripts/build-theme-skins.py` regenerates CSS after adding packs
- [ ] `pnpm exec tsc --noEmit` passes

## Non-goals

- Marketing pages hardcoded `KEPRIX_COLORS` refactor (follow-up)
- Per-user DB persistence (localStorage only for CE)
- Tailwind adoption

## Test plan

1. Run build script; verify `skins.css` size and skin count
2. Open app; default skin renders
3. Pick `violet-bloom`, `catppuccin`, `claude`; confirm sidebar, cards, buttons recolor
4. Toggle dark mode on each skin
5. Reload; selections persist
6. Change skin from Settings; Top bar reflects same skin
