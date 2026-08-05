# Keprix Prompt 116: UI Foundation, Theme, and Setup

**Status:** Completed 2026-07-06. Evidence: `ThemeRegistry.tsx`, `ThemeQuickToggle.tsx`, `ThemePickerMenu.tsx`, `globals.css`.

## Purpose

Establish a complete, production-quality UI foundation for Keprix: working dark/light mode toggle
with localStorage persistence, skin (accent-color) selector, Inter font, CSS custom properties for
the design system, and a ThemeToggle + SkinPicker component that appear in both the workspace TopBar
and the marketing Navbar. All subsequent UI prompts (117, 118, 136, 137) build on this.

The theme system already has significant scaffolding (ThemeRegistry, keprix-theme.ts, tokens). This
prompt fills the remaining gaps and ensures every layer is wired end-to-end.

---

## Dependencies

- `frontend/src/theme/keprix-theme.ts` (exists, createKeprixTheme factory)
- `frontend/src/theme/tokens/colors.ts` (exists, mapPalette from colors.json)
- `frontend/src/theme/skin-manifest.json` (exists, THEME_SKINS list)
- `frontend/src/components/providers/ThemeRegistry.tsx` (exists, useThemeMode hook)
- `frontend/src/components/providers/WorkspaceThemeRestore.tsx` (exists)
- `frontend/src/app/layout.tsx` (exists, inline flash-prevention script)
- `frontend/src/app/providers.tsx` (exists)
- `frontend/src/components/shell/TopBar.tsx` (exists, needs ThemeToggle)
- `frontend/src/components/marketing/Navbar.tsx` (exists, needs ThemeToggle)

---

## What to build

### 1. Design-system CSS custom properties

**`frontend/src/app/globals.css`** (EDIT - replace or extend existing)

Add a `:root` block and `[data-mui-color-scheme="dark"]` block that expose the full
token palette as CSS custom properties. This allows non-MUI elements (plain HTML, SVG,
third-party widgets) to consume brand colors without JS imports.

```css
:root {
  --kp-primary: #7c3aed;
  --kp-primary-light: #a78bfa;
  --kp-secondary: #06b6d4;
  --kp-bg: #ffffff;
  --kp-bg-paper: #f5f5f5;
  --kp-text-primary: #111827;
  --kp-text-secondary: #6b7280;
  --kp-border: rgba(0, 0, 0, 0.12);
  --kp-radius-card: 12px;
  --kp-radius-chip: 9999px;
  --font-inter: 'Inter', sans-serif;
}

[data-mui-color-scheme="dark"],
.dark {
  --kp-primary: #8b5cf6;
  --kp-primary-light: #a78bfa;
  --kp-secondary: #22d3ee;
  --kp-bg: #0a0a10;
  --kp-bg-paper: #13131c;
  --kp-text-primary: #f0f0f8;
  --kp-text-secondary: #8b8ca0;
  --kp-border: rgba(255, 255, 255, 0.1);
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  margin: 0;
  font-family: var(--font-inter), system-ui, -apple-system, sans-serif;
}

/* Suppress focus ring on mouse but keep it for keyboard nav */
:focus-visible {
  outline: 2px solid var(--kp-primary);
  outline-offset: 2px;
}

/* Thin scrollbar for webkit */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: var(--kp-border);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--kp-text-secondary);
}
```

### 2. ThemeToggle component

**`frontend/src/components/ui/ThemeToggle.tsx`** (NEW)

A compact icon button that cycles dark/light. Must work on both the marketing site (always dark
for marketing pages) and the workspace (user preference). Reads `useThemeMode()` from ThemeRegistry.

```tsx
"use client";

import * as React from "react";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import LightModeIcon from "@mui/icons-material/LightMode";
import { useThemeMode } from "@/components/providers/ThemeRegistry";

type ThemeToggleProps = {
  size?: "small" | "medium";
};

export function ThemeToggle({ size = "small" }: ThemeToggleProps) {
  const { mode, setMode } = useThemeMode();
  const isDark = mode === "dark";

  return (
    <Tooltip title={isDark ? "Switch to light mode" : "Switch to dark mode"}>
      <IconButton
        size={size}
        onClick={() => setMode(isDark ? "light" : "dark")}
        aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
        sx={{ color: "text.secondary", "&:hover": { color: "text.primary" } }}
      >
        {isDark ? <LightModeIcon fontSize="small" /> : <DarkModeIcon fontSize="small" />}
      </IconButton>
    </Tooltip>
  );
}
```

### 3. SkinPicker component

**`frontend/src/components/ui/SkinPicker.tsx`** (NEW)

Small popover with colored swatches, one per skin in `THEME_SKINS`. Saves selection to localStorage
via `useThemeMode().setSkin()`. Marketing pages ignore skin (they always use dark default).

```tsx
"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Popover from "@mui/material/Popover";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import PaletteIcon from "@mui/icons-material/Palette";
import { alpha } from "@mui/material/styles";
import { useThemeMode, THEME_SKINS } from "@/components/providers/ThemeRegistry";

export function SkinPicker() {
  const { skin, setSkin } = useThemeMode();
  const [anchor, setAnchor] = React.useState<HTMLButtonElement | null>(null);

  return (
    <>
      <Tooltip title="Accent color">
        <IconButton
          size="small"
          onClick={(e) => setAnchor(e.currentTarget)}
          aria-label="Choose accent color"
          sx={{ color: "text.secondary", "&:hover": { color: "text.primary" } }}
        >
          <PaletteIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Popover
        open={Boolean(anchor)}
        anchorEl={anchor}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        slotProps={{ paper: { sx: { p: 2, borderRadius: 2, minWidth: 220 } } }}
      >
        <Typography variant="caption" color="text.secondary" sx={{ mb: 1.5, display: "block", fontWeight: 600 }}>
          Accent color
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
          {THEME_SKINS.map((s) => (
            <Tooltip key={s.id} title={s.label}>
              <Box
                component="button"
                onClick={() => { setSkin(s.id); setAnchor(null); }}
                aria-label={s.label}
                aria-pressed={skin === s.id}
                sx={{
                  width: 28,
                  height: 28,
                  borderRadius: "50%",
                  bgcolor: s.primary,
                  border: skin === s.id
                    ? `3px solid ${s.primary}`
                    : "3px solid transparent",
                  outline: skin === s.id
                    ? `2px solid ${alpha(s.primary, 0.5)}`
                    : "2px solid transparent",
                  cursor: "pointer",
                  transition: "outline 0.15s",
                  p: 0,
                }}
              />
            </Tooltip>
          ))}
        </Box>
      </Popover>
    </>
  );
}
```

### 4. Wire ThemeToggle into the workspace TopBar

**`frontend/src/components/shell/TopBar.tsx`** (EDIT)

Import and render `<ThemeToggle />` and `<SkinPicker />` in the right section of the TopBar,
before the user avatar/menu. Locate the `actions` or `rightSection` area and add:

```tsx
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { SkinPicker } from "@/components/ui/SkinPicker";

// Inside the right section of the AppBar:
<SkinPicker />
<ThemeToggle />
```

### 5. Wire ThemeToggle into the marketing Navbar

**`frontend/src/components/marketing/Navbar.tsx`** (EDIT)

The marketing Navbar is always dark-themed on public pages. Add `<ThemeToggle />` to the nav
right section but only render it when `isMarketingPath(pathname)` is false (i.e. the user is
viewing a marketing page from an already-authed workspace context). For the public homepage,
skip the toggle to keep the marketing experience consistent.

Actually: add it unconditionally. Visitors who prefer light mode deserve the option.

```tsx
import { ThemeToggle } from "@/components/ui/ThemeToggle";

// Inside the Navbar right section after the CTA buttons:
<ThemeToggle size="small" />
```

### 6. Ensure ThemeRegistry exports useThemeMode with setSkin

**`frontend/src/components/providers/ThemeRegistry.tsx`** (EDIT if missing)

Verify the exported `useThemeMode()` hook returns `{ mode, setMode, skin, setSkin }`.
If `setSkin` is missing, add it. The full context shape must be:

```ts
type ThemeModeContextValue = {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
  skin: string;
  setSkin: (skin: string) => void;
};
```

`setMode` must persist to `localStorage.setItem("keprix_theme_mode", mode)` and update the
`<html>` class (`classList.toggle("dark", mode === "dark")`).

`setSkin` must persist to `localStorage.setItem("keprix_theme_skin", skin)` and update
`document.documentElement.dataset.skin = skin`.

### 7. Font: verify Inter is loading

**`frontend/src/app/layout.tsx`** (READ and verify)

The root layout already imports `Inter` from `next/font/google` with `variable: "--font-inter"`.
Confirm the `<html>` element receives `className={inter.variable}`. The CSS `body { font-family: var(--font-inter), system-ui, sans-serif; }` in globals.css must reference this variable.

No code change needed if already wired. Verify only.

### 8. Acceptance test (manual)

After implementing:

1. Open `http://localhost:3000` (marketing page). The page renders in dark mode with Inter font.
2. Click the ThemeToggle - the page switches to light mode with no flash. Refresh - stays light.
3. Click the SkinPicker - choosing a different accent color changes the primary color across all
   MUI components (buttons, links, focus rings) without a page reload.
4. Navigate to `/chat` (workspace). Theme preference carries over.
5. In DevTools, confirm `localStorage.getItem("keprix_theme_mode")` and
   `localStorage.getItem("keprix_theme_skin")` are set.
6. No hydration mismatch warnings in the console (the inline flash-prevention script in
   `layout.tsx` and `suppressHydrationWarning` on `<html>` prevent this).
