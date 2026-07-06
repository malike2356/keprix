import colorTokens from "../../../../ui/design-system/tokens/colors.json";

export type ThemeMode = "light" | "dark";

export type KeprixPalette = {
  primary: string;
  primaryDark: string;
  primaryLight: string;
  secondary: string;
  secondaryDark: string;
  secondaryLight: string;
  success: string;
  warning: string;
  error: string;
  info: string;
  muted: string;
  bgDefault: string;
  bgPaper: string;
  bgCard: string;
  bgElevated: string;
  textPrimary: string;
  textSecondary: string;
  border: string;
  divider: string;
  focus: string;
};

function mapPalette(mode: ThemeMode): KeprixPalette {
  const source = colorTokens[mode];
  return {
    primary: source.primary,
    primaryDark: source.primaryDark,
    primaryLight: source.primaryLight,
    secondary: source.secondary,
    secondaryDark: source.secondaryDark,
    secondaryLight: source.secondaryLight,
    success: source.success,
    warning: source.warning,
    error: source.danger,
    info: source.info,
    muted: source.muted,
    bgDefault: source.surfaceSubtle,
    bgPaper: source.surface,
    bgCard: source.surfaceElevated,
    bgElevated: source.surfaceElevated,
    textPrimary: source.textPrimary,
    textSecondary: source.textSecondary,
  border: source.border,
  focus: source.focus,
  divider: source.border,
};
}

export const keprixColorsLight = mapPalette("light");
export const keprixColorsDark = mapPalette("dark");

export function getKeprixColors(mode: ThemeMode): KeprixPalette {
  return mode === "light" ? keprixColorsLight : keprixColorsDark;
}

// Backward-compatible default export for dark mode consumers.
export const keprixColors = keprixColorsDark;
