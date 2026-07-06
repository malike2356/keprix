import type { KeprixPalette } from "./tokens/colors";
import { getKeprixColors, type ThemeMode } from "./tokens/colors";

function readVar(name: string, fallback: string): string {
  if (typeof window === "undefined") {
    return fallback;
  }
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function perceivedLuminance(hex: string): number {
  const clean = hex.replace("#", "");
  if (clean.length !== 6) return 0;
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
}

function shiftColor(hex: string, amount: number): string {
  const normalized = hex.replace("#", "");
  if (normalized.length !== 6) {
    return hex;
  }
  const num = parseInt(normalized, 16);
  const r = Math.min(255, Math.max(0, ((num >> 16) & 255) + amount));
  const g = Math.min(255, Math.max(0, ((num >> 8) & 255) + amount));
  const b = Math.min(255, Math.max(0, (num & 255) + amount));
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, "0")}`;
}

export function paletteFromCssVars(mode: ThemeMode): KeprixPalette {
  const fallback = getKeprixColors(mode);
  const rawPrimary = readVar("--primary", fallback.primary);
  // Neutral/monochrome skins (e.g. the default dark skin) set --primary to near-white
  // (#fafafa). In dark mode that clashes with the Keprix brand color, so fall back
  // to the brand primary while keeping every other CSS-var override intact.
  const primary =
    mode === "dark" && perceivedLuminance(rawPrimary) > 0.7
      ? fallback.primary
      : rawPrimary;
  const secondary = readVar("--secondary", fallback.secondary);
  const background = readVar("--background", fallback.bgDefault);
  const foreground = readVar("--foreground", fallback.textPrimary);
  const card = readVar("--card", fallback.bgCard);
  const border = readVar("--border", fallback.border);
  const muted = readVar("--muted-foreground", fallback.textSecondary);
  const destructive = readVar("--destructive", fallback.error);

  return {
    primary,
    primaryDark: shiftColor(primary, mode === "dark" ? -24 : -20),
    primaryLight: shiftColor(primary, mode === "dark" ? 24 : 20),
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
