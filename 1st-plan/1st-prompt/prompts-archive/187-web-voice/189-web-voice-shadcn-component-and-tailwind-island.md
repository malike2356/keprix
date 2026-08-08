# Keprix - Prompt 189: shadcn `AIVoiceInput` Component and Tailwind Island

## Context

Integrate the supplied `AIVoiceInput` React component into the Keprix Next.js frontend. The repo is **MUI-first**; this prompt adds a **minimal Tailwind + shadcn island** without migrating the whole UI.

Depends on **187**, **116** (theme tokens help dark mode).

## Working directory

`/opt/lampp/htdocs/verlox/keprix/frontend/`

## Step 0: Analyze dependencies

| Dependency | Status in frontend | Action |
| --- | --- | --- |
| TypeScript | Yes | None |
| Tailwind CSS | No | Install + configure scoped |
| shadcn/ui | No | Init CLI; only `utils` + voice component |
| `lucide-react` | No | `pnpm add lucide-react` |
| `cn()` helper | No | `frontend/src/lib/utils.ts` |
| `class-variance-authority`, `clsx`, `tailwind-merge` | No | Install for shadcn utils |

## Step 1: Install packages

From `frontend/`:

```bash
pnpm add lucide-react clsx tailwind-merge class-variance-authority
pnpm add -D tailwindcss @tailwindcss/postcss postcss autoprefixer
```

## Step 2: Tailwind scoped to voice island

**Why not global Tailwind?** MUI uses Emotion; global Tailwind preflight can break MUI baseline. Use a **prefixed scope**.

Create `frontend/tailwind.voice.config.ts`:

```ts
import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/components/ui/**/*.{ts,tsx}",
    "./src/components/workspace/ChatVoiceControl.tsx",
  ],
  important: ".kp-voice-root",
  darkMode: ["selector", '[data-mui-color-scheme="dark"]'],
  theme: { extend: {} },
  plugins: [],
} satisfies Config;
```

Create `frontend/src/styles/voice-tailwind.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

Import in `frontend/src/app/layout.tsx` **after** MUI globals:

```ts
import "@/styles/voice-tailwind.css";
```

Add PostCSS pipeline in `frontend/postcss.config.mjs` if not present (Next 15 pattern with `@tailwindcss/postcss`).

## Step 3: `cn` utility

Create `frontend/src/lib/utils.ts`:

```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

Ensure `tsconfig.json` paths include `"@/*": ["./src/*"]` (already standard).

## Step 4: Copy `AIVoiceInput` component

Create `frontend/src/components/ui/ai-voice-input.tsx` with the user-supplied component **with these edits**:

1. Remove `demoMode` default usage from production path (keep prop for Storybook/test only).
2. Fix `useEffect` dependency bug: `onStop` should not depend on `time` in the effect that resets timer (use ref for duration on stop).
3. Export props interface `AIVoiceInputProps`.
4. Add `disabled?: boolean` and `aria-label` for accessibility.
5. Replace hardcoded `text-black` / `dark:text-white` with tokens that work inside `.kp-voice-root` and MUI dark mode:

```tsx
className="text-[var(--kp-text-primary)]"
```

Use CSS vars from Prompt 116 `globals.css` where possible.

## Step 5: Wrapper for MUI integration

Create `frontend/src/components/workspace/ChatVoiceControl.tsx`:

```tsx
"use client";

import { AIVoiceInput } from "@/components/ui/ai-voice-input";

type ChatVoiceControlProps = {
  isRecording: boolean;
  elapsedSeconds: number;
  disabled?: boolean;
  onToggleRecording: () => void;
};

export default function ChatVoiceControl(props: ChatVoiceControlProps) {
  return (
    <div className="kp-voice-root">
      <AIVoiceInput
        className="py-0"
        visualizerBars={24}
        onStart={...}
        onStop={...}
      />
    </div>
  );
};
```

**Important:** The supplied `AIVoiceInput` manages its own `submitted` state. For real recording, **either**:

- (A) Refactor `AIVoiceInput` to controlled mode: `recording: boolean`, `onToggle`, `elapsedSeconds` props; or
- (B) Keep visual-only component and map `submitted` to `isRecording` from parent hook (prompt 190)

Prefer **(A)** for production; document in component JSDoc.

## Step 6: Demo page (dev only)

`frontend/src/app/(workspace)/dev/voice-input/page.tsx` (guard with `NODE_ENV === 'development'` or admin role):

Renders `AIVoiceInputDemo` from user spec for visual QA.

## Step 7: Why `/components/ui` matters

shadcn convention places primitives in `components/ui/` so:

- CLI additions land predictably
- Tailwind `content` globs stay narrow
- MUI feature components stay in `components/workspace/`

If the folder did not exist, create it; do not place shadcn files under `components/mui/`.

## Tests

`frontend/src/components/ui/ai-voice-input.test.tsx` (Vitest + Testing Library):

- Renders mic button
- Click toggles listening label
- `disabled` prevents toggle
- No `Math.random` visualizer assertions (snapshot optional)

## Acceptance criteria

- `pnpm type-check` passes in `frontend/`
- `pnpm test` passes for new component tests
- Voice Tailwind does not visibly break MUI chat layout on `/chat/*`
- `AIVoiceInput` lives at `frontend/src/components/ui/ai-voice-input.tsx`
- `lucide-react` listed in `package.json`
- No Unsplash assets required (component has no images)
