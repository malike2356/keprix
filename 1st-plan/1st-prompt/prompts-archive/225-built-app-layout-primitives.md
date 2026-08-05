# Keprix - Prompt 225: Built App Layout Primitives (Content-Area Shell)

## Context

Ship reusable **in-content** navigation for products built on Keprix (Carina / ABBIS pattern). Apps own their IA inside the main column; the platform left pane stays thin.

Depends on **223**. Can run in parallel with **224**.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/frontend/`

## Deliverables

```text
frontend/src/components/built-app/
  types.ts
  BuiltAppLayout.tsx
  BuiltAppHeader.tsx
  BuiltAppSectionNav.tsx
  BuiltAppSubRail.tsx
  index.ts
frontend/src/lib/built-app-manifest.ts
```

Optional dev preview: `frontend/src/app/(workspace)/dev/built-app-shell/page.tsx` (not linked in production nav).

## Types (`types.ts`)

```typescript
export type BuiltAppNavItem = {
  id: string;
  label: string;
  href: string;
  icon?: string;
  badge?: number | string;
};

export type BuiltAppManifest = {
  id: string;
  label: string;
  description?: string;
  entry: string;
  icon?: string;
  version?: string;
  navigation?: {
    style?: "sections" | "sub_rail" | "tabs_only";
    items: BuiltAppNavItem[];
  };
};
```

Export Zod or manual validators if project already uses Zod in frontend; otherwise TypeScript types only.

## `BuiltAppLayout`

Props:

```typescript
type BuiltAppLayoutProps = {
  manifest: BuiltAppManifest;
  children: React.ReactNode;
  headerActions?: React.ReactNode;
  subRailItems?: BuiltAppNavItem[]; // when style sub_rail
};
```

Layout:

```text
BuiltAppHeader (breadcrumbs: Launcher > {label} > current section)
BuiltAppSectionNav (if navigation.items.length > 0 and style !== tabs_only)
[ BuiltAppSubRail | children ]  // flex row when sub_rail
```

- Max content width: match `AppShell` main (full width of content column, not viewport)
- Back link: "Back to Launcher" -> `/launcher` and "All apps" -> `/agent-apps` or future apps hub

## `BuiltAppSectionNav`

- MUI `Tabs` or scrollable `ToggleButtonGroup` for 4-10 items
- Active tab from `usePathname()` prefix match on `href`
- `aria-label="App sections"`
- On narrow screens: horizontal scroll, no wrap

## `BuiltAppSubRail`

- 220px column, `List` of `ListItemButton`, main content `flex: 1`
- Used when `manifest.navigation.style === "sub_rail"`

## `built-app-manifest.ts`

```typescript
export function normalizeBuiltAppManifest(raw: unknown): BuiltAppManifest;
export function activeNavItem(manifest: BuiltAppManifest, pathname: string): BuiltAppNavItem | null;
```

## Styling rules

- Use MUI theme tokens; no global Tailwind migration
- Optional `brand.primary_color` applies to `BuiltAppHeader` accent only (Chip or border), not whole workspace theme
- Match `PageHeader` typography scale

## Tests

`frontend/src/components/built-app/BuiltAppLayout.test.tsx`:

- Renders section nav from manifest
- Highlights active section for pathname `/apps/demo/finance`
- Sub-rail layout renders two columns when style is `sub_rail`

## Out of scope

- Loading manifest from API (prompt **226**)
- Real `/apps/[slug]` routes (prompt **227**)
- AbbiS pages (consumer outside core)

## Acceptance criteria

- Layout kit renders header + horizontal sections + children
- Sub-rail variant works
- Breadcrumbs and back links present
- Vitest tests pass
- Dev preview page optional but must not appear in `navigation.py`

## Manual test

Open `/dev/built-app-shell` with a hardcoded demo manifest (3 sections). Click sections; active state updates.
