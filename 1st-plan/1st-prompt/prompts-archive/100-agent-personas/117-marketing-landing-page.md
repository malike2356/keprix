# Keprix Prompt 117: Marketing Landing Page

**Status:** Completed 2026-07-06. Evidence: `MetricsBar.tsx`, `FeaturesGrid.tsx`, `Navbar.tsx`, `CTABand.tsx`, `Footer.tsx`, `/blog`, `/status`.

## Purpose

Build the complete Keprix marketing site: a polished, content-complete landing page that converts
visitors into self-hosters. The `Hero` component is already fully built and animated. This prompt
fills in every other section that is currently a placeholder skeleton.

The landing page must:
- Communicate what Keprix is (self-hosted AI agent OS with Mutation Engine) in the first scroll.
- Show the Mutation Engine as the main differentiator.
- Provide social proof via metrics, comparisons, and open-source signals.
- Guide visitors to "Deploy in 2 minutes" or "View on GitHub".

---

## Dependencies

- `frontend/src/components/marketing/Hero.tsx` (done - animated terminal, CTA buttons)
- `frontend/src/components/marketing/MarketingSection.tsx` (done - light/dark tone wrapper)
- `frontend/src/components/marketing/ScrollReveal.tsx` (done)
- `frontend/src/components/ui/InfiniteSlider.tsx` (done)
- `frontend/src/app/(marketing)/layout.tsx` (done - Navbar + Footer)
- `frontend/src/app/(marketing)/page.tsx` (done - section assembly)
- `frontend/src/theme/keprix-theme.ts` - `KEPRIX_COLORS` constant
- Prompt 116 must be complete (Inter font, CSS custom properties)

All components below are scaffolded files that export a named function returning a placeholder
`<Box>`. Replace the placeholder bodies entirely.

---

## What to build

### 1. Navbar

**`frontend/src/components/marketing/Navbar.tsx`** (EDIT)

Sticky transparent navbar that gains a frosted-glass background on scroll. Contains:
- Left: `KeprixWordmark` (or logo + "Keprix" text)
- Center: navigation links - Features, How it works, Compare, Docs, Blog
- Right: "GitHub" link (opens `https://github.com/malike2356/keprix`), "Deploy free" CTA button,
  ThemeToggle (from Prompt 116)

On mobile (below `md`): hamburger menu with a full-width drawer showing all links.

Scroll detection pattern:
```tsx
const [scrolled, setScrolled] = React.useState(false);
React.useEffect(() => {
  const handler = () => setScrolled(window.scrollY > 48);
  window.addEventListener("scroll", handler, { passive: true });
  return () => window.removeEventListener("scroll", handler);
}, []);

// Apply to AppBar:
sx={{
  position: "fixed",
  top: 0,
  left: 0,
  right: 0,
  zIndex: 1200,
  transition: "background 0.2s, box-shadow 0.2s",
  bgcolor: scrolled ? "rgba(10,10,16,0.88)" : "transparent",
  backdropFilter: scrolled ? "blur(16px)" : "none",
  boxShadow: scrolled ? "0 1px 0 rgba(255,255,255,0.06)" : "none",
}}
```

### 2. MetricsBar

**`frontend/src/components/marketing/MetricsBar.tsx`** (EDIT)

Four stats displayed in a horizontal band between Hero and Features. Use real numbers from the
Keprix product story. Light-tone section background.

```tsx
const METRICS = [
  { value: "< 3 min", label: "to first running agent" },
  { value: "100%", label: "self-hosted, your data" },
  { value: "MIT", label: "open-source license" },
  { value: "0", label: "cloud accounts required" },
];
```

Layout: `display: grid; grid-template-columns: repeat(4, 1fr)` on desktop, 2x2 on tablet, 1 col
on mobile. Each metric: large bold value (3rem) in `primary.main`, smaller label in
`text.secondary`. Dividers between items. Wrap in `Container maxWidth="lg"`.

### 3. FeaturesGrid

**`frontend/src/components/marketing/FeaturesGrid.tsx`** (EDIT)

Six feature cards in a 3-column grid (2 on md, 1 on xs). Each has an icon, title, and 2-3 sentence
body. Uses the existing `GlowCard` pattern with tilt effect.

Feature cards (use the six that are already in the scaffolded file if present, otherwise replace
with these):

```tsx
const FEATURES = [
  {
    icon: AutoFixHighIcon,
    title: "Mutation Engine",
    body:
      "When the agent needs a tool that does not exist, it synthesises Python code in a sandbox, shows you the diff, and waits for your approval before installing. No manual plugin writing.",
    glowColor: "#7c3aed",
  },
  {
    icon: CodeIcon,
    title: "Self-coding workspace",
    body:
      "Give the agent a repo and a task. It plans, writes code, runs tests in an isolated container, and iterates until green. You review a PR, not a pile of instructions.",
    glowColor: "#06b6d4",
  },
  {
    icon: HubIcon,
    title: "Multi-channel inbox",
    body:
      "Connect Telegram, Discord, Slack, WhatsApp, email, and webhooks to one runtime. Each channel routes to the right agent persona with its own memory and tool set.",
    glowColor: "#10b981",
  },
  {
    icon: MemoryIcon,
    title: "Long-term memory",
    body:
      "Structured memory store backed by PostgreSQL or SQLite. Agents recall facts across sessions, namespaced by workspace. Semantic search via pgvector when available.",
    glowColor: "#f59e0b",
  },
  {
    icon: PlaybookIcon,
    title: "Playbooks",
    body:
      "Compose deterministic workflows in YAML. Chain tools, conditions, and agent calls. Schedule them with cron or trigger via webhook. No separate orchestration layer needed.",
    glowColor: "#ef4444",
  },
  {
    icon: ShieldIcon,
    title: "Full observability",
    body:
      "Every LLM call, tool execution, and mutation event is logged with latency, token cost, and trace ID. Budget alerts fire before you exceed your monthly threshold.",
    glowColor: "#8b5cf6",
  },
];
```

For icons without a direct MUI match (PlaybookIcon), substitute `ArticleIcon` or `ListAltIcon`.

### 4. HowItWorks

**`frontend/src/components/marketing/HowItWorks.tsx`** (EDIT)

Three-step numbered walkthrough. Steps already exist in the scaffolded file (Deploy, Connect,
Ask). Keep the steps but ensure the detail blocks are rendered as styled code blocks or
annotation boxes, not plain text. This section should make the Mutation Engine flow visible.

Add a fourth step specifically about Mutation:

```tsx
{
  number: "04",
  icon: AutoFixHighIcon,
  title: "Mutate",
  body: "Ask Keprix to do something it cannot yet do. It detects the gap, synthesises a tool, shows you the code, and installs it live after your approval.",
  detail: {
    type: "conversation",
    lines: [
      { role: "user", text: "Track my hours on this project" },
      { role: "agent", text: "No time-tracking tool found. Synthesising..." },
      { role: "system", text: "DIFF: keprix_tool_time_tracker.py (+47 lines)" },
      { role: "agent", text: "Sandbox passed. Approve? [Y/n]" },
      { role: "user", text: "Y" },
      { role: "agent", text: "Installed. Tracking started." },
    ],
  },
},
```

Render the `conversation` detail type as a mini chat window matching the terminal aesthetic from
Hero (dark bg, monospace, prefix-colored lines).

### 5. Integrations

**`frontend/src/components/marketing/Integrations.tsx`** (EDIT)

Replace placeholder with a grid of integration logos/pill chips showing what Keprix connects to.
Group into three columns: LLM Providers, Channels, Infrastructure.

```tsx
const GROUPS = [
  {
    label: "LLM Providers",
    items: ["Anthropic", "OpenAI", "Gemini", "Groq", "Ollama", "OpenRouter", "DeepSeek"],
  },
  {
    label: "Channels",
    items: ["Telegram", "Discord", "Slack", "WhatsApp", "Email (IMAP)", "Webhook", "REST API"],
  },
  {
    label: "Infrastructure",
    items: ["Docker", "PostgreSQL", "SQLite", "Redis", "pgvector", "MCP", "SFTP"],
  },
];
```

Each group: bold label, then a flex-wrap row of `Chip` components (outlined, small). On dark tone
section (the page uses `tone="dark"` for this section).

### 6. OpenSourceBand

**`frontend/src/components/marketing/OpenSourceBand.tsx`** (EDIT)

A simple horizontal band with GitHub stars counter, license badge, and a one-liner call to action.

```tsx
// Fetch stars from GitHub API on the server (this is a server component - no "use client" needed
// unless you need client-side interactivity)
// For now, hardcode a reasonable number and note it should be fetched server-side:
const STARS = "500+"; // update when live

// Layout:
// [GitHub star icon] 500+ stars  |  MIT License  |  "Star us on GitHub" link
```

Use `InfiniteSlider` from the Hero section if a scrolling contributor list is desired, otherwise
a static layout is fine.

### 7. ProductComparison

**`frontend/src/components/marketing/ProductComparison.tsx`** (EDIT)

A comparison table: Keprix vs n8n, Dify, LangChain, AutoGen. Rows = capabilities.

```tsx
const ROWS = [
  { feature: "Self-hosted", keprix: true, n8n: true, dify: true, langchain: false, autogen: false },
  { feature: "Mutation Engine (self-coding tools)", keprix: true, n8n: false, dify: false, langchain: false, autogen: false },
  { feature: "Multi-channel inbox", keprix: true, n8n: true, dify: false, langchain: false, autogen: false },
  { feature: "Playbook scheduler", keprix: true, n8n: true, dify: false, langchain: false, autogen: false },
  { feature: "Long-term memory (structured)", keprix: true, n8n: false, dify: true, langchain: true, autogen: true },
  { feature: "Budget alerts + observability", keprix: true, n8n: false, dify: false, langchain: false, autogen: false },
  { feature: "MIT license", keprix: true, n8n: true, dify: true, langchain: true, autogen: false },
  { feature: "No cloud account required", keprix: true, n8n: true, dify: true, langchain: true, autogen: true },
];
```

Keprix column header is visually highlighted (primary color border, bold). Use checkmarks (plain
`CheckIcon` from MUI) for true and a dash for false. No emojis.

Table wraps in a horizontally scrollable `Box` on mobile.

### 8. FAQ

**`frontend/src/components/marketing/FAQ.tsx`** (EDIT)

MUI `Accordion` list with 6-8 questions. One accordion open by default.

```tsx
const QUESTIONS = [
  {
    q: "What is the Mutation Engine?",
    a: "When you ask Keprix to do something it cannot do yet, it writes a Python tool in a sandboxed environment, shows you the full code diff, and waits for your explicit approval before installing. The tool is available immediately in the same session, no restart needed.",
  },
  {
    q: "Can I use my own LLM or a local model?",
    a: "Yes. Keprix supports Anthropic, OpenAI, Gemini, Groq, and Ollama out of the box. Point the KEPRIX_LLM_PROVIDER variable at your provider and set your API key. Ollama runs entirely on your own hardware.",
  },
  {
    q: "What database does Keprix need?",
    a: "PostgreSQL for production. SQLite for local development with zero setup. Switch by changing one environment variable.",
  },
  {
    q: "Is there a hosted version?",
    a: "Not yet. Keprix is self-hosted only. The Aiva product (keprix enterprise variant) will add managed hosting.",
  },
  {
    q: "How is Keprix different from n8n or Dify?",
    a: "n8n and Dify are workflow builders. Keprix is an agent runtime with a conversational interface, long-term memory, and the Mutation Engine. It can plan and build new capabilities at runtime, not just execute pre-built nodes.",
  },
  {
    q: "Does Keprix store my data?",
    a: "All data stays in your own PostgreSQL or SQLite database. Nothing leaves your infrastructure unless you configure an external LLM provider (whose terms apply to the prompts you send).",
  },
  {
    q: "What channels can I connect?",
    a: "Telegram, Discord, Slack, WhatsApp (via Twilio), email (IMAP/SMTP), webhooks, and the Keprix REST API. Each channel gets its own persona and tool configuration.",
  },
  {
    q: "How do I contribute?",
    a: "Open a pull request at github.com/malike2356/keprix. The repo has a CONTRIBUTING.md with setup instructions and the prompt build-order at planning/prompts/.",
  },
];
```

### 9. CTABand

**`frontend/src/components/marketing/CTABand.tsx`** (EDIT)

Full-width dark section with large heading and two buttons. Gradient background using primary colors.

```tsx
// Heading: "Deploy your own AI agent OS in under 3 minutes."
// Sub: "Self-hosted. MIT licensed. No cloud accounts required."
// Button 1 (contained, gradient): "Deploy free" -> /auth/setup
// Button 2 (outlined): "Read the docs" -> /docs
//
// Background: linear-gradient(135deg, #1a0a2e 0%, #0a1628 100%)
// with a subtle radial glow in primary color at center
```

### 10. Footer

**`frontend/src/components/marketing/Footer.tsx`** (EDIT)

Four-column footer: Product, Resources, Community, Legal.

```tsx
const COLUMNS = [
  {
    heading: "Product",
    links: [
      { label: "Features", href: "/#features" },
      { label: "Pricing", href: "/pricing" },
      { label: "Changelog", href: "/changelog" },
      { label: "Roadmap", href: "/docs/roadmap" },
    ],
  },
  {
    heading: "Resources",
    links: [
      { label: "Documentation", href: "/docs" },
      { label: "API Reference", href: "/docs/api" },
      { label: "Blog", href: "/blog" },
      { label: "Status", href: "/status" },
    ],
  },
  {
    heading: "Community",
    links: [
      { label: "GitHub", href: "https://github.com/malike2356/keprix" },
      { label: "Discord", href: "https://discord.gg/keprix" },
      { label: "Twitter / X", href: "https://x.com/keprixai" },
      { label: "Contributing", href: "https://github.com/malike2356/keprix/blob/main/CONTRIBUTING.md" },
    ],
  },
  {
    heading: "Legal",
    links: [
      { label: "Privacy policy", href: "/legal/privacy" },
      { label: "Terms of service", href: "/legal/terms" },
      { label: "MIT License", href: "https://github.com/malike2356/keprix/blob/main/LICENSE" },
    ],
  },
];
```

Bottom row: copyright line left, "Built with Keprix" right.

### 11. MarketingSection wrapper check

**`frontend/src/components/marketing/MarketingSection.tsx`** (READ and verify)

This component switches background and text color based on `tone="light"` or `tone="dark"`.
Verify that:
- `tone="light"` uses `background.default` (white in light mode, near-black in dark mode - but
  since marketing is always dark, confirm the light-tone section is visually lighter than dark-tone).
- The component accepts an `id` prop and passes it to the underlying `section` element for anchor
  navigation (e.g. `id="features"`, `id="compare"`).

If `id` prop is missing, add it.

### 12. Acceptance test (manual)

After implementing:

1. `http://localhost:3000` loads with no broken sections. All 8 sections visible on scroll.
2. Navbar sticks to top and gains glass background after scrolling 48px.
3. "Deploy free" and "View on GitHub" buttons in Hero are present and navigate correctly.
4. Features section shows 6 tilt cards with correct Keprix content.
5. How It Works shows 4 numbered steps with the Mutation Engine conversation demo.
6. Integrations shows all three groups of chips.
7. Comparison table renders on mobile with horizontal scroll.
8. FAQ accordion opens/closes without layout shift.
9. Footer has all four columns with working links.
10. No console errors. No missing images (use MUI icons, not `<img>` tags with broken paths).
