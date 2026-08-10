"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Container from "@mui/material/Container";
import InputAdornment from "@mui/material/InputAdornment";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";
import SearchIcon from "@mui/icons-material/Search";
import {
  MARKETING_EYEBROW_SX,
  MARKETING_HEADING_SX,
  useMarketingColors,
} from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";
import {
  countMarketingFeatures,
  MARKETING_FEATURE_CATEGORIES,
  type MarketingFeature,
  type MarketingFeatureCategory,
} from "@/lib/marketing-features-catalog";
import { docsPageUrl } from "@/lib/docs-url";
import { useThemeMode } from "@/components/providers/ThemeRegistry";

function matchesQuery(feature: MarketingFeature, query: string): boolean {
  if (!query) return true;
  const hay = `${feature.name} ${feature.description} ${feature.usedFor}`.toLowerCase();
  return hay.includes(query);
}

function FeatureRow({
  feature,
  c,
}: {
  feature: MarketingFeature;
  c: ReturnType<typeof useMarketingColors>;
}) {
  return (
    <Box
      component="article"
      sx={{
        py: 2.25,
        borderBottom: `1px solid ${alpha(c.divider, 0.9)}`,
        display: "grid",
        gridTemplateColumns: { xs: "1fr", md: "minmax(160px, 220px) 1fr" },
        gap: { xs: 1, md: 3 },
        alignItems: "start",
      }}
    >
      <Box>
        <Typography sx={{ fontWeight: 700, color: c.textPrimary, fontSize: "1rem", mb: 0.5 }}>
          {feature.name}
        </Typography>
        {feature.docsPath ? (
          <Box
            component="a"
            href={docsPageUrl(feature.docsPath)}
            sx={{
              fontSize: "0.75rem",
              color: c.primary,
              textDecoration: "none",
              "&:hover": { textDecoration: "underline" },
            }}
          >
            Docs
          </Box>
        ) : null}
      </Box>
      <Box>
        <Typography sx={{ color: c.textSecondary, fontSize: "0.9rem", lineHeight: 1.65, mb: 0.75 }}>
          {feature.description}
        </Typography>
        <Typography sx={{ color: c.textSecondary, fontSize: "0.82rem", lineHeight: 1.55 }}>
          <Box component="span" sx={{ fontWeight: 600, color: c.textPrimary }}>
            Used for:{" "}
          </Box>
          {feature.usedFor}
        </Typography>
      </Box>
    </Box>
  );
}

function CategoryBlock({
  category,
  query,
  c,
}: {
  category: MarketingFeatureCategory;
  query: string;
  c: ReturnType<typeof useMarketingColors>;
}) {
  const features = category.features.filter((f) => matchesQuery(f, query));
  if (!features.length) return null;

  return (
    <Box component="section" id={category.id} sx={{ mb: { xs: 6, md: 8 }, scrollMarginTop: 96 }}>
      <Typography
        component="h2"
        sx={{
          fontWeight: 800,
          fontSize: { xs: "1.35rem", md: "1.6rem" },
          color: c.textPrimary,
          letterSpacing: "-0.02em",
          mb: 0.75,
        }}
      >
        {category.title}
      </Typography>
      <Typography sx={{ color: c.textSecondary, fontSize: "0.9rem", mb: 2, maxWidth: 640 }}>
        {category.summary}
      </Typography>
      <Box
        sx={{
          borderTop: `1px solid ${c.divider}`,
          bgcolor: alpha(c.bgPaper, 0.35),
          borderRadius: 2,
          px: { xs: 2, md: 3 },
        }}
      >
        {features.map((feature) => (
          <FeatureRow key={feature.id} feature={feature} c={c} />
        ))}
      </Box>
    </Box>
  );
}

export function FeaturesCatalogView() {
  const c = useMarketingColors();
  const { mode } = useThemeMode();
  const isDark = mode === "dark";
  const [query, setQuery] = React.useState("");
  const normalized = query.trim().toLowerCase();
  const total = countMarketingFeatures();

  const visibleCategories = MARKETING_FEATURE_CATEGORIES.filter((cat) =>
    cat.features.some((f) => matchesQuery(f, normalized)),
  );
  const visibleCount = visibleCategories.reduce(
    (n, cat) => n + cat.features.filter((f) => matchesQuery(f, normalized)).length,
    0,
  );

  return (
    <Box sx={{ bgcolor: c.bgDefault, minHeight: "70vh", pb: { xs: 10, md: 14 } }}>
      <Box
        sx={{
          pt: { xs: 12, md: 14 },
          pb: { xs: 6, md: 8 },
          borderBottom: `1px solid ${c.divider}`,
          background: isDark
            ? `radial-gradient(ellipse at 50% 0%, ${alpha(c.primary, 0.14)} 0%, transparent 55%)`
            : `radial-gradient(ellipse at 50% 0%, ${alpha(c.primary, 0.1)} 0%, transparent 50%)`,
        }}
      >
        <Container maxWidth="lg">
          <ScrollReveal>
            <Typography component="p" sx={{ ...MARKETING_EYEBROW_SX, color: c.primary, mb: 2 }}>
              Capabilities catalog
            </Typography>
            <Typography
              component="h1"
              sx={{
                ...MARKETING_HEADING_SX,
                fontSize: { xs: "2.2rem", md: "3rem" },
                color: c.textPrimary,
                mb: 2,
                maxWidth: 720,
              }}
            >
              Full list of Keprix features
            </Typography>
            <Typography
              sx={{ color: c.textSecondary, fontSize: "1.05rem", lineHeight: 1.7, maxWidth: 640, mb: 3 }}
            >
              Name, what it does, and what it is used for. This page tracks the current self-hosted
              agent OS: workspace, Agent OS, Channel Shield, Agentic CRM, Universal Sidecar, vault,
              Soft Wall, and more. The homepage highlights only a short sample.
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5, mb: 3 }}>
              <Chip
                label={`${total} capabilities`}
                size="small"
                sx={{ bgcolor: alpha(c.primary, 0.12), color: c.primary, fontWeight: 600 }}
              />
              <Chip
                label={`${MARKETING_FEATURE_CATEGORIES.length} categories`}
                size="small"
                sx={{ bgcolor: alpha(c.secondary, 0.12), color: c.secondary, fontWeight: 600 }}
              />
            </Box>
            <TextField
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by name or use case..."
              fullWidth
              size="small"
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon sx={{ color: c.textSecondary, fontSize: 20 }} />
                  </InputAdornment>
                ),
              }}
              sx={{
                maxWidth: 480,
                "& .MuiOutlinedInput-root": {
                  bgcolor: alpha(c.bgPaper, 0.7),
                },
              }}
            />
            <Typography sx={{ mt: 1.5, fontSize: "0.8rem", color: c.textSecondary }}>
              Showing {visibleCount} of {total}
            </Typography>
          </ScrollReveal>
        </Container>
      </Box>

      <Container maxWidth="lg" sx={{ pt: { xs: 5, md: 7 } }}>
        <Box
          sx={{
            display: "flex",
            flexWrap: "wrap",
            gap: 1,
            mb: 5,
          }}
        >
          {MARKETING_FEATURE_CATEGORIES.map((cat) => (
            <Chip
              key={cat.id}
              component="a"
              href={`#${cat.id}`}
              clickable
              label={cat.title}
              size="small"
              variant="outlined"
              sx={{
                borderColor: alpha(c.divider, 1),
                color: c.textSecondary,
                "&:hover": { borderColor: c.primary, color: c.primary },
              }}
            />
          ))}
        </Box>

        {visibleCategories.length === 0 ? (
          <Typography sx={{ color: c.textSecondary }}>No capabilities match that search.</Typography>
        ) : (
          visibleCategories.map((category) => (
            <CategoryBlock key={category.id} category={category} query={normalized} c={c} />
          ))
        )}

        <Box
          sx={{
            mt: 4,
            p: { xs: 3, md: 4 },
            borderRadius: 2,
            border: `1px solid ${c.divider}`,
            bgcolor: alpha(c.bgPaper, 0.4),
            display: "flex",
            flexDirection: { xs: "column", sm: "row" },
            alignItems: { sm: "center" },
            justifyContent: "space-between",
            gap: 2,
          }}
        >
          <Box>
            <Typography sx={{ fontWeight: 700, color: c.textPrimary, mb: 0.5 }}>
              Prefer the short tour?
            </Typography>
            <Typography sx={{ color: c.textSecondary, fontSize: "0.9rem" }}>
              The homepage highlights eight flagship capabilities. Docs go deeper on each module.
            </Typography>
          </Box>
          <Box sx={{ display: "flex", gap: 1.5, flexWrap: "wrap" }}>
            <Button component="a" href="/#features" variant="outlined" sx={{ textTransform: "none" }}>
              Homepage highlights
            </Button>
            <Button component="a" href="/docs" variant="contained" sx={{ textTransform: "none" }}>
              Open docs
            </Button>
          </Box>
        </Box>
      </Container>
    </Box>
  );
}
