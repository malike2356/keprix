"use client";

import * as React from "react";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Toolbar from "@mui/material/Toolbar";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Drawer from "@mui/material/Drawer";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Divider from "@mui/material/Divider";
import { alpha } from "@mui/material/styles";
import MenuIcon from "@mui/icons-material/Menu";
import CloseIcon from "@mui/icons-material/Close";
import Link from "next/link";
import { KeprixLogo } from "@/components/shared/KeprixLogo";
import ThemeQuickToggle from "@/components/theme/ThemeQuickToggle";
import { useThemeMode } from "@/components/providers/ThemeRegistry";
import { getMarketingColors } from "@/components/marketing/marketing-section";
import { getCEToken } from "@/lib/ce-api";

const NAV_LINKS = [
  { label: "Features", href: "/#features" },
  { label: "How it works", href: "/#how-it-works" },
  { label: "Integrations", href: "/#integrations" },
  { label: "Runtime", href: "/#compare" },
  { label: "Proof", href: "/proof" },
  { label: "Status", href: "/status" },
  { label: "Docs", href: "/docs" },
  { label: "Blog", href: "/blog" },
] as const;

const GITHUB_LINK = {
  label: "GitHub",
  href: "https://github.com/malike2356/keprix",
} as const;

export function Navbar() {
  const { mode } = useThemeMode();
  const colors = getMarketingColors(mode);
  const isDark = mode === "dark";
  const [scrolled, setScrolled] = React.useState(false);
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const [isAuthed, setIsAuthed] = React.useState(false);

  React.useEffect(() => {
    setIsAuthed(Boolean(getCEToken()));
  }, []);

  React.useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 48);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  return (
    <>
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          bgcolor: scrolled ? alpha(colors.bgDefault, isDark ? 0.88 : 0.92) : "transparent",
          backdropFilter: scrolled ? "blur(16px)" : "none",
          boxShadow: scrolled
            ? isDark
              ? "0 1px 0 rgba(255,255,255,0.06)"
              : "0 1px 0 rgba(0,0,0,0.08)"
            : "none",
          transition: "background 0.2s, box-shadow 0.2s, backdrop-filter 0.2s",
        }}
      >
        <Toolbar sx={{ maxWidth: 1200, mx: "auto", width: "100%", px: { xs: 2, md: 4 } }}>
          <Box sx={{ flexGrow: 1 }}>
            <Link href="/" style={{ textDecoration: "none" }}>
              <KeprixLogo variant="full" size="sm" onDark={isDark} />
            </Link>
          </Box>

          <Box sx={{ display: { xs: "none", md: "flex" }, alignItems: "center", gap: 1 }}>
            {NAV_LINKS.map((link) => (
              <Button
                key={link.label}
                component="a"
                href={link.href}
                target={link.href.startsWith("http") ? "_blank" : undefined}
                rel={link.href.startsWith("http") ? "noopener noreferrer" : undefined}
                sx={{
                  color: colors.textSecondary,
                  fontWeight: 500,
                  fontSize: "0.875rem",
                  "&:hover": { color: colors.textPrimary },
                }}
              >
                {link.label}
              </Button>
            ))}
            <Button
              component="a"
              href={GITHUB_LINK.href}
              target="_blank"
              rel="noopener noreferrer"
              variant="outlined"
              size="small"
              sx={{
                ml: 0.5,
                fontWeight: 600,
                borderColor: alpha(colors.divider, 0.8),
                color: colors.textSecondary,
                "&:hover": {
                  borderColor: alpha(colors.primary, 0.5),
                  color: colors.textPrimary,
                },
              }}
            >
              {GITHUB_LINK.label}
            </Button>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                ml: 0.5,
                mr: 0.5,
                "& .MuiIconButton-root": { color: colors.textSecondary },
              }}
            >
              <ThemeQuickToggle color="inherit" />
            </Box>
            <Button
              component="a"
              href={isAuthed ? "/home" : "/auth/setup"}
              variant="contained"
              size="small"
              sx={{ ml: 1, fontWeight: 600 }}
            >
              {isAuthed ? "Open app" : "Deploy free"}
            </Button>
          </Box>

          <Box sx={{ display: { xs: "flex", md: "none" }, alignItems: "center", gap: 0.5 }}>
            <Box sx={{ "& .MuiIconButton-root": { color: colors.textSecondary } }}>
              <ThemeQuickToggle color="inherit" />
            </Box>
            <IconButton
              sx={{ color: colors.textPrimary }}
              onClick={() => setDrawerOpen(true)}
              aria-label="Open menu"
            >
              <MenuIcon />
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>

      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        PaperProps={{
          sx: {
            width: 260,
            bgcolor: colors.bgPaper,
            borderLeft: `1px solid ${colors.divider}`,
            color: colors.textPrimary,
          },
        }}
      >
        <Box sx={{ p: 2, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <KeprixLogo variant="full" size="sm" onDark={isDark} />
          <IconButton onClick={() => setDrawerOpen(false)} sx={{ color: colors.textSecondary }}>
            <CloseIcon />
          </IconButton>
        </Box>
        <Divider sx={{ borderColor: colors.divider }} />
        <List>
          {NAV_LINKS.map((link) => (
            <ListItem key={link.label} disablePadding>
              <ListItemButton
                component="a"
                href={link.href}
                target={link.href.startsWith("http") ? "_blank" : undefined}
                onClick={() => setDrawerOpen(false)}
              >
                <ListItemText
                  primary={link.label}
                  slotProps={{ primary: { sx: { color: colors.textSecondary, fontSize: "0.9rem" } } }}
                />
              </ListItemButton>
            </ListItem>
          ))}
          <ListItem disablePadding>
            <ListItemButton
              component="a"
              href={GITHUB_LINK.href}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setDrawerOpen(false)}
            >
              <ListItemText
                primary={GITHUB_LINK.label}
                slotProps={{ primary: { sx: { color: colors.textSecondary, fontSize: "0.9rem" } } }}
              />
            </ListItemButton>
          </ListItem>
        </List>
        <Divider sx={{ borderColor: colors.divider }} />
        <Box sx={{ p: 2 }}>
          <Button
            component="a"
            href={isAuthed ? "/home" : "/auth/setup"}
            variant="contained"
            fullWidth
            onClick={() => setDrawerOpen(false)}
          >
            {isAuthed ? "Open app" : "Deploy free"}
          </Button>
        </Box>
      </Drawer>
    </>
  );
}
