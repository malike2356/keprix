/** WCAG contrast helpers for theme skins that ship pastel accents. */

export function parseHex(hex: string): [number, number, number] | null {
  const raw = hex.trim().replace("#", "");
  if (!/^[0-9a-fA-F]{6}$/.test(raw)) return null;
  return [parseInt(raw.slice(0, 2), 16), parseInt(raw.slice(2, 4), 16), parseInt(raw.slice(4, 6), 16)];
}

export function toHex(r: number, g: number, b: number): string {
  const clamp = (value: number) => Math.min(255, Math.max(0, Math.round(value)));
  return `#${[clamp(r), clamp(g), clamp(b)].map((value) => value.toString(16).padStart(2, "0")).join("")}`;
}

function channelLinear(value: number): number {
  const channel = value / 255;
  return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
}

export function relativeLuminance(hex: string): number {
  const rgb = parseHex(hex);
  if (!rgb) return 0;
  const [r, g, b] = rgb;
  return 0.2126 * channelLinear(r) + 0.7152 * channelLinear(g) + 0.0722 * channelLinear(b);
}

export function contrastRatio(foreground: string, background: string): number {
  const lighter = Math.max(relativeLuminance(foreground), relativeLuminance(background));
  const darker = Math.min(relativeLuminance(foreground), relativeLuminance(background));
  return (lighter + 0.05) / (darker + 0.05);
}

export function contrastText(background: string): string {
  return contrastRatio("#ffffff", background) >= contrastRatio("#0a0a0a", background) ? "#ffffff" : "#0a0a0a";
}

function mixToward(hex: string, target: string, amount: number): string {
  const from = parseHex(hex);
  const to = parseHex(target);
  if (!from || !to) return hex;
  return toHex(
    from[0] + (to[0] - from[0]) * amount,
    from[1] + (to[1] - from[1]) * amount,
    from[2] + (to[2] - from[2]) * amount,
  );
}

/** Darken or lighten `color` until it reaches `minRatio` against `background`. */
export function ensureContrast(color: string, background: string, minRatio = 4.5): string {
  if (!parseHex(color) || !parseHex(background)) return color;
  if (contrastRatio(color, background) >= minRatio) return color;

  const towardDark = mixToward(color, "#0a0a0a", 0.08);
  const towardLight = mixToward(color, "#ffffff", 0.08);
  const preferDark = contrastRatio(towardDark, background) >= contrastRatio(towardLight, background);
  const target = preferDark ? "#0a0a0a" : "#ffffff";

  let next = color;
  for (let step = 0.06; step <= 1; step += 0.06) {
    next = mixToward(color, target, step);
    if (contrastRatio(next, background) >= minRatio) return next;
  }
  return preferDark ? "#111827" : "#f9fafb";
}

/** Interactive fill/link color that stays readable on paper and supports white label text. */
export function ensureInteractiveAccent(color: string, paper: string, mode: "light" | "dark"): string {
  const paperBg = parseHex(paper) ? paper : mode === "light" ? "#ffffff" : "#1a1d23";
  const label = mode === "light" ? "#ffffff" : "#0a0a0a";
  // First make sure accent text on paper is readable, then make sure filled buttons can use a strong label.
  let next = ensureContrast(color, paperBg, 4.5);
  next = ensureContrast(next, label, 4.5);
  return next;
}

export function ensureMutedText(color: string, paper: string, mode: "light" | "dark"): string {
  const paperBg = parseHex(paper) ? paper : mode === "light" ? "#ffffff" : "#1a1d23";
  const fallback = mode === "light" ? "#374151" : "#d1d5db";
  if (!parseHex(color)) return fallback;
  return ensureContrast(color, paperBg, 4.5);
}

export function ensurePrimaryText(color: string, paper: string, mode: "light" | "dark"): string {
  const paperBg = parseHex(paper) ? paper : mode === "light" ? "#ffffff" : "#1a1d23";
  const fallback = mode === "light" ? "#111827" : "#f3f4f6";
  if (!parseHex(color)) return fallback;
  return ensureContrast(color, paperBg, 4.5);
}

/** Soft status fill that keeps text readable in light and dark modes. */
export function softStatusColors(
  main: string,
  paper: string,
  mode: "light" | "dark",
): { backgroundColor: string; color: string } {
  const paperBg = parseHex(paper) ? paper : mode === "light" ? "#ffffff" : "#1a1d23";
  const tint = ensureContrast(main, paperBg, 4.5);
  // Approximate alpha overlay by mixing main into paper (no CSS alpha in palette helpers).
  const mixAmount = mode === "dark" ? 0.22 : 0.14;
  const backgroundColor = mixToward(paperBg, main, mixAmount);
  const color = ensureContrast(tint, backgroundColor, 4.5);
  return { backgroundColor, color };
}

/** Explicit severity light/dark/contrastText that stay usable as fills in dark mode. */
export function severityScale(main: string, mode: "light" | "dark") {
  const light =
    mode === "dark"
      ? mixToward(main, "#0a0a0a", 0.55) // dark tinted surface, not a washed pastel
      : mixToward(main, "#ffffff", 0.72);
  const dark =
    mode === "dark" ? mixToward(main, "#ffffff", 0.28) : mixToward(main, "#0a0a0a", 0.28);
  return {
    main,
    light,
    dark,
    contrastText: contrastText(main),
    // Readable label when using `.light` as a row/chip fill.
    softContrastText: contrastText(light),
  };
}
