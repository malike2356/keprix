import type { KeprixPalette } from "./tokens/colors";
import { getKeprixColors, type ThemeMode } from "./tokens/colors";
import {
  ensureInteractiveAccent,
  ensureMutedText,
  ensurePrimaryText,
  parseHex,
  relativeLuminance,
} from "./contrast";

function readVar(name: string, fallback: string): string {
  if (typeof window === "undefined") {
    return fallback;
  }
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function shiftColor(hex: string, amount: number): string {
  const rgb = parseHex(hex);
  if (!rgb) return hex;
  const [r, g, b] = rgb;
  const clamp = (value: number) => Math.min(255, Math.max(0, value + amount));
  return `#${[clamp(r), clamp(g), clamp(b)].map((value) => value.toString(16).padStart(2, "0")).join("")}`;
}

export function paletteFromCssVars(mode: ThemeMode): KeprixPalette {
  const fallback = getKeprixColors(mode);
  const rawPrimary = readVar("--primary", fallback.primary);
  // Neutral/monochrome skins (e.g. the default dark skin) set --primary to near-white
  // (#fafafa). In dark mode that clashes with the Keprix brand color, so fall back
  // to the brand primary while keeping every other CSS-var override intact.
  const resolvedPrimary =
    mode === "dark" && relativeLuminance(rawPrimary) > 0.7
      ? fallback.primary
      : rawPrimary;

  const background = readVar("--background", fallback.bgDefault);
  const card = readVar("--card", fallback.bgCard);
  const paper = card || background;
  const primary = ensureInteractiveAccent(resolvedPrimary, paper, mode);
  const secondaryRaw = readVar("--secondary", fallback.secondary);
  const secondary = ensureInteractiveAccent(
    // Some skins set secondary to a near-paper gray; fall back to brand secondary.
    relativeLuminance(secondaryRaw) > 0.85 || relativeLuminance(secondaryRaw) < 0.08
      ? fallback.secondary
      : secondaryRaw,
    paper,
    mode,
  );
  // Prefer card-foreground when skins set it; always enforce contrast on paper.
  const foregroundRaw =
    readVar("--card-foreground", "") || readVar("--foreground", fallback.textPrimary);
  const foreground = ensurePrimaryText(foregroundRaw, paper, mode);
  const border = readVar("--border", fallback.border);
  const muted = ensureMutedText(
    readVar("--muted-foreground", fallback.textSecondary),
    paper,
    mode,
  );
  const destructive = readVar("--destructive", fallback.error);

  return {
    primary,
    primaryDark: shiftColor(primary, mode === "dark" ? -24 : -28),
    primaryLight: shiftColor(primary, mode === "dark" ? 24 : 28),
    secondary,
    secondaryDark: shiftColor(secondary, -16),
    secondaryLight: shiftColor(secondary, 16),
    success: fallback.success,
    warning: fallback.warning,
    error: destructive,
    info: fallback.info,
    muted: readVar("--muted", fallback.muted),
    bgDefault: background,
    bgPaper: card,
    bgCard: card,
    bgElevated: card,
    textPrimary: foreground,
    textSecondary: muted,
    border,
    divider: border,
    focus: primary,
  };
}
