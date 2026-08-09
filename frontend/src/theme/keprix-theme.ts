"use client";

import { alpha, createTheme, type Theme } from "@mui/material/styles";
import {
  contrastText,
  ensureContrast,
  severityScale,
} from "./contrast";
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
  return contrastText(hex);
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

function alertTone(theme: Theme, key: "success" | "info" | "warning" | "error") {
  const main = theme.palette[key].main;
  const paper = theme.palette.background.paper;
  return {
    // Tint only: keep the real paper underneath so light/dark shells stay consistent.
    backgroundColor: alpha(main, theme.palette.mode === "dark" ? 0.16 : 0.1),
    color: ensureContrast(main, paper, 4.5),
    "& .MuiAlert-icon": { color: "inherit" },
  };
}

export function createKeprixTheme(mode: ThemeMode = "dark", paletteOverride?: KeprixPalette): Theme {
  const c: KeprixPalette = paletteOverride ?? getKeprixColors(mode);
  const success = severityScale(c.success, mode);
  const warning = severityScale(c.warning, mode);
  const error = severityScale(c.error, mode);
  const info = severityScale(c.info, mode);

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
      success: {
        main: success.main,
        light: success.light,
        dark: success.dark,
        contrastText: success.contrastText,
      },
      warning: {
        main: warning.main,
        light: warning.light,
        dark: warning.dark,
        contrastText: warning.contrastText,
      },
      error: {
        main: error.main,
        light: error.light,
        dark: error.dark,
        contrastText: error.contrastText,
      },
      info: {
        main: info.main,
        light: info.light,
        dark: info.dark,
        contrastText: info.contrastText,
      },
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
          containedPrimary: ({ theme }) => ({
            backgroundColor: theme.palette.primary.main,
            color: theme.palette.primary.contrastText,
            "&:hover": { backgroundColor: theme.palette.primary.dark },
          }),
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: ({ theme }) => ({
            backgroundImage: "none",
            color: theme.palette.text.primary,
          }),
        },
      },
      MuiDialog: {
        styleOverrides: {
          paper: ({ theme }) => ({
            backgroundImage: "none",
            backgroundColor: theme.palette.background.paper,
            color: theme.palette.text.primary,
            border: `1px solid ${theme.palette.divider}`,
          }),
        },
      },
      MuiPopover: {
        styleOverrides: {
          paper: ({ theme }) => ({
            backgroundImage: "none",
            backgroundColor: theme.palette.background.paper,
            color: theme.palette.text.primary,
            border: `1px solid ${theme.palette.divider}`,
          }),
        },
      },
      MuiMenu: {
        styleOverrides: {
          paper: ({ theme }) => ({
            backgroundImage: "none",
            backgroundColor: theme.palette.background.paper,
            color: theme.palette.text.primary,
          }),
        },
      },
      MuiAccordion: {
        styleOverrides: {
          root: ({ theme }) => ({
            backgroundImage: "none",
            backgroundColor: theme.palette.background.paper,
            color: theme.palette.text.primary,
            borderColor: theme.palette.divider,
          }),
        },
      },
      MuiCard: {
        styleOverrides: {
          root: ({ theme }) => ({
            backgroundImage: "none",
            backgroundColor: theme.palette.background.paper,
            color: theme.palette.text.primary,
            border: `1px solid ${theme.palette.divider}`,
            boxShadow: "none",
          }),
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            backgroundColor: c.bgPaper,
            color: c.textPrimary,
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
          root: { color: c.textPrimary, borderColor: c.border },
          head: {
            backgroundColor: c.bgPaper,
            color: c.textPrimary,
            fontWeight: 600,
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: { fontWeight: 500, fontSize: "0.75rem" },
          filled: ({ theme }) =>
            theme.palette.mode === "dark"
              ? {
                  "&.MuiChip-colorDefault": {
                    backgroundColor: alpha(theme.palette.common.white, 0.12),
                    color: theme.palette.text.primary,
                  },
                }
              : {
                  "&.MuiChip-colorDefault": {
                    backgroundColor: alpha(theme.palette.common.black, 0.08),
                    color: theme.palette.text.primary,
                  },
                },
          outlined: ({ theme }) => ({
            "&.MuiChip-colorDefault": {
              borderColor: theme.palette.divider,
              color: theme.palette.text.primary,
            },
          }),
        },
      },
      MuiAlert: {
        styleOverrides: {
          standardSuccess: ({ theme }) => alertTone(theme, "success"),
          standardInfo: ({ theme }) => alertTone(theme, "info"),
          standardWarning: ({ theme }) => alertTone(theme, "warning"),
          standardError: ({ theme }) => alertTone(theme, "error"),
          outlinedSuccess: ({ theme }) => ({
            color: ensureContrast(theme.palette.success.main, theme.palette.background.paper),
            borderColor: alpha(theme.palette.success.main, 0.5),
          }),
          outlinedInfo: ({ theme }) => ({
            color: ensureContrast(theme.palette.info.main, theme.palette.background.paper),
            borderColor: alpha(theme.palette.info.main, 0.5),
          }),
          outlinedWarning: ({ theme }) => ({
            color: ensureContrast(theme.palette.warning.main, theme.palette.background.paper),
            borderColor: alpha(theme.palette.warning.main, 0.5),
          }),
          outlinedError: ({ theme }) => ({
            color: ensureContrast(theme.palette.error.main, theme.palette.background.paper),
            borderColor: alpha(theme.palette.error.main, 0.5),
          }),
          filledSuccess: ({ theme }) => ({
            backgroundColor: theme.palette.success.main,
            color: contrastText(theme.palette.success.main),
          }),
          filledInfo: ({ theme }) => ({
            backgroundColor: theme.palette.info.main,
            color: contrastText(theme.palette.info.main),
          }),
          filledWarning: ({ theme }) => ({
            backgroundColor: theme.palette.warning.main,
            color: contrastText(theme.palette.warning.main),
          }),
          filledError: ({ theme }) => ({
            backgroundColor: theme.palette.error.main,
            color: contrastText(theme.palette.error.main),
          }),
        },
      },
      MuiListItemButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            marginBottom: 2,
            color: c.textPrimary,
            "&.Mui-selected": {
              backgroundColor: alpha(c.primary, 0.15),
              color: ensureContrast(c.primary, c.bgPaper),
              "&:hover": { backgroundColor: alpha(c.primary, 0.2) },
            },
          },
        },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: ({ theme }) => ({
            color: theme.palette.text.primary,
            // Do not paint a forced fill; inherit paper/card from the parent surface.
            backgroundColor: "transparent",
          }),
          notchedOutline: ({ theme }) => ({
            borderColor: theme.palette.divider,
            "& legend": {
              boxSizing: "content-box",
            },
          }),
          input: ({ theme }) => ({
            color: theme.palette.text.primary,
            "&::placeholder": {
              color: theme.palette.text.secondary,
              opacity: 1,
            },
          }),
        },
      },
      MuiInputLabel: {
        styleOverrides: {
          root: ({ theme }) => ({
            color: theme.palette.text.secondary,
            "&.Mui-focused": {
              color: ensureContrast(theme.palette.primary.main, theme.palette.background.paper),
            },
          }),
          outlined: ({ theme }) => ({
            "&.MuiInputLabel-shrink": {
              backgroundColor: theme.palette.background.paper,
              color: theme.palette.text.secondary,
              paddingInline: 4,
              marginInline: -4,
            },
          }),
        },
      },
      MuiFormHelperText: {
        styleOverrides: {
          root: ({ theme }) => ({ color: theme.palette.text.secondary }),
        },
      },
      MuiMenuItem: {
        styleOverrides: {
          root: ({ theme }) => ({ color: theme.palette.text.primary }),
        },
      },
      MuiDialogTitle: {
        styleOverrides: {
          root: ({ theme }) => ({ color: theme.palette.text.primary }),
        },
      },
      MuiDialogContentText: {
        styleOverrides: {
          root: ({ theme }) => ({ color: theme.palette.text.secondary }),
        },
      },
      MuiTooltip: {
        styleOverrides: {
          tooltip: ({ theme }) => ({
            backgroundColor: theme.palette.mode === "dark" ? theme.palette.grey[100] : theme.palette.grey[900],
            color: theme.palette.mode === "dark" ? theme.palette.grey[900] : theme.palette.common.white,
          }),
        },
      },
    },
  });
}

export const keprixTheme = createKeprixTheme("dark");
