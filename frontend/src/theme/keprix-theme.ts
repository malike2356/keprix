"use client";

import { alpha, createTheme, type Theme } from "@mui/material/styles";
import type { KeprixPalette } from "./tokens/colors";
import { getKeprixColors, keprixColorsDark, type ThemeMode } from "./tokens/colors";
import { keprixTypography } from "./tokens/typography";

/** Dark palette constants for components that need fixed brand colors. */
export const KEPRIX_COLORS = {
  primary: keprixColorsDark.primary,
  primaryDark: keprixColorsDark.primaryDark,
  primaryLight: keprixColorsDark.primaryLight,
  secondary: keprixColorsDark.secondary,
  secondaryDark: keprixColorsDark.secondaryDark,
  secondaryLight: keprixColorsDark.secondaryLight,
  success: keprixColorsDark.success,
  warning: keprixColorsDark.warning,
  error: keprixColorsDark.error,
  info: keprixColorsDark.info,
  bgDefault: keprixColorsDark.bgDefault,
  bgPaper: keprixColorsDark.bgPaper,
  bgCard: keprixColorsDark.bgCard,
  textPrimary: keprixColorsDark.textPrimary,
  textSecondary: keprixColorsDark.textSecondary,
  divider: keprixColorsDark.divider,
};

function contrastFor(hex: string): string {
  const clean = hex.replace("#", "");
  if (clean.length !== 6) return "#ffffff";
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.55 ? "#0a0a0a" : "#ffffff";
}

function buildShadows(mode: ThemeMode): string[] {
  const strength = mode === "dark" ? 0.35 : 0.12;
  return [
    "none",
    `0 1px 3px ${alpha("#000", strength)}`,
    `0 2px 6px ${alpha("#000", strength + 0.05)}`,
    `0 4px 12px ${alpha("#000", strength + 0.1)}`,
    ...Array(21).fill("none"),
  ] as string[];
}

export function createKeprixTheme(mode: ThemeMode = "dark", paletteOverride?: KeprixPalette): Theme {
  const c: KeprixPalette = paletteOverride ?? getKeprixColors(mode);

  return createTheme({
    palette: {
      mode,
      primary: {
        main: c.primary,
        dark: c.primaryDark,
        light: c.primaryLight,
        contrastText: contrastFor(c.primary),
      },
      secondary: {
        main: c.secondary,
        dark: c.secondaryDark,
        light: c.secondaryLight,
        contrastText: contrastFor(c.secondary),
      },
      success: { main: c.success },
      warning: { main: c.warning },
      error: { main: c.error },
      info: { main: c.info },
      background: {
        default: c.bgDefault,
        paper: c.bgPaper,
      },
      text: {
        primary: c.textPrimary,
        secondary: c.textSecondary,
      },
      divider: c.border,
    },
    typography: {
      fontFamily: keprixTypography.fontFamily,
      h1: {
        fontFamily: keprixTypography.fontFamilyDisplay,
        fontSize: "2.5rem",
        fontWeight: 600,
        lineHeight: 1.2,
      },
      h2: {
        fontFamily: keprixTypography.fontFamilyDisplay,
        fontSize: "2rem",
        fontWeight: 600,
        lineHeight: 1.25,
      },
      h3: {
        fontFamily: keprixTypography.fontFamilyDisplay,
        fontSize: "1.5rem",
        fontWeight: 600,
        lineHeight: 1.3,
      },
      h4: {
        fontFamily: keprixTypography.fontFamilyDisplay,
        fontSize: "1.25rem",
        fontWeight: 600,
        lineHeight: 1.4,
      },
      h5: { fontFamily: keprixTypography.fontFamilyDisplay, fontSize: "1.125rem", fontWeight: 600 },
      h6: { fontFamily: keprixTypography.fontFamilyDisplay, fontSize: "1rem", fontWeight: 600 },
      body1: { fontSize: "0.9375rem", fontWeight: 400, lineHeight: 1.6 },
      body2: { fontSize: "0.875rem", fontWeight: 400, lineHeight: 1.57 },
      button: { fontWeight: 500 },
    },
    shape: { borderRadius: 8 },
    shadows: buildShadows(mode) as Theme["shadows"],
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            backgroundColor: c.bgDefault,
            color: c.textPrimary,
            fontFamily: keprixTypography.fontFamily,
          },
          code: {
            fontFamily: keprixTypography.fontFamilyMono,
          },
          pre: {
            fontFamily: keprixTypography.fontFamilyMono,
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: { textTransform: "none", fontWeight: 500, borderRadius: 8 },
          containedPrimary: {
            backgroundColor: c.primary,
            color: contrastFor(c.primary),
            "&:hover": { backgroundColor: c.primaryDark },
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
            backgroundColor: c.bgCard,
            border: `1px solid ${c.border}`,
            boxShadow: "none",
          },
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            backgroundColor: c.bgPaper,
            borderRight: `1px solid ${c.border}`,
          },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundColor: alpha(c.bgPaper, 0.92),
            backdropFilter: "blur(8px)",
            borderBottom: `1px solid ${c.border}`,
            boxShadow: "none",
            color: c.textPrimary,
          },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          head: { backgroundColor: c.bgPaper, fontWeight: 600 },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: { fontWeight: 500, fontSize: "0.75rem" },
        },
      },
      MuiListItemButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            marginBottom: 2,
            "&.Mui-selected": {
              backgroundColor: alpha(c.primary, 0.15),
              color: c.primary,
              "&:hover": { backgroundColor: alpha(c.primary, 0.2) },
            },
          },
        },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          notchedOutline: {
            "& legend": {
              boxSizing: "content-box",
            },
          },
        },
      },
      MuiInputLabel: {
        styleOverrides: {
          outlined: {
            "&.MuiInputLabel-shrink": {
              backgroundColor: c.bgCard,
              paddingInline: 4,
              marginInline: -4,
            },
          },
        },
      },
    },
  });
}

export const keprixTheme = createKeprixTheme("dark");
