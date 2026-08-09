"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Divider from "@mui/material/Divider";
import Link from "next/link";
import { alpha } from "@mui/material/styles";
import { motion } from "motion/react";
import { IconBrandGithub, IconBrandX, IconBrandDiscord } from "@tabler/icons-react";
import { KeprixLogo } from "@/components/shared/KeprixLogo";
import { DEVELOPER_ECOSYSTEM, DEVELOPER_ECOSYSTEM_LABEL } from "@/lib/developer-ecosystem";
import { getMarketingColors, MARKETING_DISPLAY_FONT } from "@/components/marketing/marketing-section";
import { useThemeMode } from "@/components/providers/ThemeRegistry";

const FOOTER_COLS = [
  {
    heading: "Product",
    links: [
      { label: "Features", href: "/#features" },
      { label: "All capabilities", href: "/features" },
      { label: "Integrations", href: "/#integrations" },
      { label: "Pricing", href: "/pricing" },
      { label: "Changelog", href: "/changelog" },
      { label: "Roadmap", href: "/docs" },
    ],
  },
  {
    heading: "Resources",
    links: [
      { label: "Documentation", href: "/docs" },
      { label: "API Reference", href: "https://github.com/malike2356/keprix/blob/main/docs/reference/api.md" },
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
] as const;

const SOCIAL_LINKS = [
  { icon: IconBrandGithub, label: "GitHub", href: "https://github.com/malike2356/keprix" },
  { icon: IconBrandX, label: "X", href: "https://x.com/keprixai" },
  { icon: IconBrandDiscord, label: "Discord", href: "https://discord.gg/keprix" },
] as const;

/** Sibling products: see frontend/src/lib/developer-ecosystem.ts and /verlox/ecosystem-links.json */

function TextHoverEffect({ text, duration = 0 }: { text: string; duration?: number }) {
  const { mode } = useThemeMode();
  const c = getMarketingColors(mode);
  const svgRef = React.useRef<SVGSVGElement>(null);
  const [cursor, setCursor] = React.useState({ x: 0, y: 0 });
  const [hovered, setHovered] = React.useState(false);
  const [maskPosition, setMaskPosition] = React.useState({ cx: "50%", cy: "50%" });

  React.useEffect(() => {
    if (!svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const cx = ((cursor.x - rect.left) / rect.width) * 100;
    const cy = ((cursor.y - rect.top) / rect.height) * 100;
    setMaskPosition({ cx: `${cx}%`, cy: `${cy}%` });
  }, [cursor]);

  const textStyle: React.CSSProperties = {
    fontSize: "4.5rem",
    fontWeight: 700,
    fontFamily: MARKETING_DISPLAY_FONT,
  };

  return (
    <svg
      ref={svgRef}
      width="100%"
      height="100%"
      viewBox="0 0 300 100"
      xmlns="http://www.w3.org/2000/svg"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onMouseMove={(e) => setCursor({ x: e.clientX, y: e.clientY })}
      style={{ userSelect: "none", textTransform: "uppercase", cursor: "pointer", display: "block" }}
    >
      <defs>
        <linearGradient id="kpxTextGradient" gradientUnits="userSpaceOnUse" cx="50%" cy="50%" r="25%">
          {hovered && (
            <>
              <stop offset="0%" stopColor={c.primary} />
              <stop offset="25%" stopColor="#ef4444" />
              <stop offset="50%" stopColor={c.secondary} />
              <stop offset="75%" stopColor="#06b6d4" />
              <stop offset="100%" stopColor={c.primary} />
            </>
          )}
        </linearGradient>

        <motion.radialGradient
          id="kpxRevealMask"
          gradientUnits="userSpaceOnUse"
          r="20%"
          initial={{ cx: "50%", cy: "50%" }}
          animate={maskPosition}
          transition={{ duration, ease: "easeOut" }}
        >
          <stop offset="0%" stopColor="white" />
          <stop offset="100%" stopColor="black" />
        </motion.radialGradient>

        <mask id="kpxTextMask">
          <rect x="0" y="0" width="100%" height="100%" fill="url(#kpxRevealMask)" />
        </mask>
      </defs>

      {/* Outline layer - visible on hover */}
      <text
        x="50%"
        y="50%"
        textAnchor="middle"
        dominantBaseline="middle"
        strokeWidth="0.3"
        style={{
          ...textStyle,
          fill: "transparent",
          stroke: alpha(c.textSecondary, 0.55),
          opacity: hovered ? 0.7 : 0,
          transition: "opacity 0.2s",
        }}
      >
        {text}
      </text>

      {/* Animated stroke draw-on layer */}
      <motion.text
        x="50%"
        y="50%"
        textAnchor="middle"
        dominantBaseline="middle"
        strokeWidth="0.3"
        style={{
          ...textStyle,
          fill: "transparent",
          stroke: alpha(c.primary, 0.55),
        }}
        initial={{ strokeDashoffset: 1000, strokeDasharray: 1000 }}
        animate={{ strokeDashoffset: 0, strokeDasharray: 1000 }}
        transition={{ duration: 4, ease: "easeInOut" }}
      >
        {text}
      </motion.text>

      {/* Colour-reveal layer - only visible under the radial mask */}
      <text
        x="50%"
        y="50%"
        textAnchor="middle"
        dominantBaseline="middle"
        stroke="url(#kpxTextGradient)"
        strokeWidth="0.3"
        mask="url(#kpxTextMask)"
        style={{ ...textStyle, fill: "transparent" }}
      >
        {text}
      </text>
    </svg>
  );
}

function FooterBg() {
  const { mode } = useThemeMode();
  const c = getMarketingColors(mode);
  return (
    <Box
      aria-hidden
      sx={{
        position: "absolute",
        inset: 0,
        zIndex: 0,
        background: `radial-gradient(125% 125% at 50% 10%, ${alpha(c.bgPaper, 0.96)} 50%, ${alpha(c.primary, 0.18)} 100%)`,
        pointerEvents: "none",
      }}
    />
  );
}

function FooterLink({ href, label }: { href: string; label: string }) {
  const { mode } = useThemeMode();
  const c = getMarketingColors(mode);
  const external = href.startsWith("http");
  return (
    <Box component="li" sx={{ listStyle: "none", mb: 1.5 }}>
      <Box
        component={external ? "a" : Link}
        href={href}
        target={external ? "_blank" : undefined}
        rel={external ? "noopener noreferrer" : undefined}
        sx={{
          color: alpha(c.textSecondary, 0.9),
          fontSize: "0.875rem",
          textDecoration: "none",
          transition: "color 0.15s",
          "&:hover": { color: c.primary },
        }}
      >
        {label}
      </Box>
    </Box>
  );
}

export function Footer() {
  const { mode } = useThemeMode();
  const c = getMarketingColors(mode);
  return (
    <Box
      component="footer"
      sx={{
        position: "relative",
        overflow: "hidden",
        bgcolor: c.bgPaper,
        color: c.textPrimary,
        borderTop: `1px solid ${c.divider}`,
        mt: "auto",
      }}
    >
      <FooterBg />

      <Box
        sx={{
          maxWidth: 1200,
          mx: "auto",
          px: { xs: 3, sm: 4, md: 7 },
          pt: { xs: 5, md: 7 },
          pb: { xs: 4, md: 5 },
          position: "relative",
          zIndex: 1,
        }}
      >
          {/* 4-col grid */}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "2fr 1fr 1fr 1fr 1fr" },
              gap: { xs: 5, md: 6 },
              mb: 5,
            }}
          >
            {/* Brand col */}
            <Box>
              <Box sx={{ mb: 2.5 }}>
                <KeprixLogo variant="full" size="sm" onDark={mode === "dark"} />
              </Box>
              <Typography
                sx={{ fontSize: "0.875rem", color: c.textSecondary, lineHeight: 1.75, mb: 2, maxWidth: 280 }}
              >
                Self-hosted, MIT-licensed AI agent OS. Agent OS, Channel Shield, Agentic CRM, Universal
                Sidecar, Soft Wall, and reviewable self-coding on your infrastructure.
              </Typography>
              <Typography sx={{ fontSize: "0.75rem", color: alpha(c.textSecondary, 0.8), lineHeight: 1.6, maxWidth: 280 }}>
                {DEVELOPER_ECOSYSTEM_LABEL}:{" "}
                {DEVELOPER_ECOSYSTEM.map((item, index) => (
                  <React.Fragment key={item.label}>
                    {index > 0 ? " · " : null}
                    <Box
                      component="a"
                      href={item.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={item.title}
                      sx={{
                        color: c.textSecondary,
                        textDecoration: "none",
                        "&:hover": { color: c.primary },
                      }}
                    >
                      {item.label}
                    </Box>
                  </React.Fragment>
                ))}
              </Typography>
            </Box>

            {/* Link cols */}
            {FOOTER_COLS.map((col) => (
              <Box key={col.heading}>
                <Typography
                  sx={{
                    fontWeight: 700,
                    fontSize: "0.75rem",
                    color: c.textSecondary,
                    textTransform: "uppercase",
                    letterSpacing: "0.1em",
                    mb: 2.5,
                  }}
                >
                  {col.heading}
                </Typography>
                <Box component="ul" sx={{ m: 0, p: 0 }}>
                  {col.links.map((link) => (
                    <FooterLink key={link.label} {...link} />
                  ))}
                </Box>
              </Box>
            ))}
          </Box>

          <Divider sx={{ borderColor: c.divider, mb: 3 }} />

          {/* Bottom bar */}
          <Box
            sx={{
              display: "flex",
              flexDirection: { xs: "column", sm: "row" },
              justifyContent: "space-between",
              alignItems: { xs: "flex-start", sm: "center" },
              gap: 2,
            }}
          >
            {/* Social icons */}
            <Box sx={{ display: "flex", gap: 2.5 }}>
              {SOCIAL_LINKS.map(({ icon: Icon, label, href }) => (
                <Box
                  key={label}
                  component="a"
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={label}
                  sx={{
                    color: c.textSecondary,
                    display: "flex",
                    transition: "color 0.15s",
                    "&:hover": { color: c.primary },
                  }}
                >
                  <Icon size={20} />
                </Box>
              ))}
            </Box>

            {/* Copyright */}
            <Typography sx={{ fontSize: "0.8rem", color: c.textSecondary }}>
              {new Date().getFullYear()} Keprix. MIT open source.
            </Typography>

            <Typography sx={{ fontSize: "0.8rem", color: c.textSecondary }}>
              Built with Keprix
            </Typography>
          </Box>
        </Box>

      {/* Large hover text effect - desktop only */}
      <Box
        sx={{
          display: { xs: "none", lg: "block" },
          height: 220,
          mt: "-140px",
          mb: "-80px",
          position: "relative",
          zIndex: 1,
          maxWidth: 1200,
          mx: "auto",
          px: { xs: 3, sm: 4, md: 7 },
        }}
      >
        <TextHoverEffect text="KEPRIX" duration={0} />
      </Box>
    </Box>
  );
}
