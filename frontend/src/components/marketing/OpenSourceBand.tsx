"use client";

import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import { alpha } from "@mui/material/styles";
import CodeIcon from "@mui/icons-material/Code";
import StarIcon from "@mui/icons-material/Star";
import { useMarketingColors } from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";

const STARS = "500+";

export function OpenSourceBand() {
  const c = useMarketingColors();

  return (
    <Box
      sx={{
        py: { xs: 12, md: 18 },
        textAlign: "center",
        borderTop: `1px solid ${c.divider}`,
        borderBottom: `1px solid ${c.divider}`,
      }}
    >
      <Container maxWidth="md">
        <ScrollReveal>
          <Box
            sx={{
              display: "inline-flex",
              alignItems: "center",
              gap: 1,
              px: 2,
              py: 0.75,
              mb: 3,
              borderRadius: 5,
              border: `1px solid ${alpha(c.success, 0.3)}`,
              bgcolor: alpha(c.success, 0.07),
            }}
          >
            <Box
              sx={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                bgcolor: c.success,
                boxShadow: `0 0 8px ${c.success}`,
              }}
            />
            <Typography sx={{ fontSize: "0.78rem", fontWeight: 700, color: c.success, letterSpacing: "0.04em" }}>
              MIT License - Free forever
            </Typography>
          </Box>

          <Typography
            component="h2"
            sx={{
              fontSize: { xs: "2.25rem", md: "3.25rem" },
              fontWeight: 800,
              letterSpacing: "-0.035em",
              lineHeight: 1.1,
              mb: 2.5,
              color: c.textPrimary,
            }}
          >
            Keprix is free and
            <br />
            open source. Forever.
          </Typography>

          <Typography
            sx={{ color: c.textSecondary, mb: 3, fontSize: "1.05rem", maxWidth: 420, mx: "auto", lineHeight: 1.7 }}
          >
            MIT license. Use it commercially. Modify it. Self-host it. No strings attached.
          </Typography>

          <Box
            sx={{
              display: "inline-flex",
              alignItems: "center",
              gap: 2,
              flexWrap: "wrap",
              justifyContent: "center",
              mb: 4,
            }}
          >
            <Box
              sx={{
                display: "inline-flex",
                alignItems: "center",
                gap: 0.75,
                px: 2,
                py: 0.75,
                borderRadius: 5,
                border: `1px solid ${alpha(c.primary, 0.25)}`,
                bgcolor: alpha(c.primary, 0.08),
              }}
            >
              <StarIcon sx={{ fontSize: 16, color: c.primary }} />
              <Typography sx={{ fontSize: "0.85rem", fontWeight: 700, color: c.textPrimary }}>
                {STARS} stars
              </Typography>
            </Box>
            <Typography sx={{ color: alpha(c.textSecondary, 0.5), fontSize: "1.1rem" }}>|</Typography>
            <Typography sx={{ fontSize: "0.85rem", fontWeight: 600, color: c.textSecondary }}>
              MIT License
            </Typography>
          </Box>

          <Box
            sx={{
              display: "inline-flex",
              alignItems: "center",
              px: 2.5,
              py: 1,
              mb: 5,
              borderRadius: 2,
              bgcolor: c.bgCard,
              border: `1px solid ${c.divider}`,
              boxShadow: "0 1px 2px rgba(24,24,30,0.06)",
            }}
          >
            <Typography
              sx={{
                fontFamily: "monospace",
                fontSize: "0.82rem",
                color: c.textPrimary,
                letterSpacing: "0.01em",
              }}
            >
              github.com/malike2356/keprix
            </Typography>
          </Box>

          <Box sx={{ display: "flex", gap: 2, justifyContent: "center", flexWrap: "wrap" }}>
            <Button
              component="a"
              href="https://github.com/malike2356/keprix"
              target="_blank"
              rel="noopener noreferrer"
              variant="outlined"
              startIcon={<CodeIcon />}
              sx={{
                fontWeight: 600,
                borderRadius: "9999px",
                px: 3,
                borderColor: c.divider,
                color: c.textPrimary,
                "&:hover": {
                  borderColor: alpha(c.primary, 0.5),
                  color: c.primary,
                  bgcolor: alpha(c.primary, 0.06),
                },
              }}
            >
              View source
            </Button>
            <Button
              component="a"
              href="https://github.com/malike2356/keprix"
              target="_blank"
              rel="noopener noreferrer"
              variant="contained"
              startIcon={<StarIcon />}
              sx={{
                fontWeight: 700,
                borderRadius: "9999px",
                px: 3,
                background: `linear-gradient(135deg, ${c.primary} 0%, ${c.secondary} 100%)`,
                boxShadow: `0 4px 24px ${alpha(c.primary, 0.4)}`,
                "&:hover": {
                  boxShadow: `0 6px 32px ${alpha(c.primary, 0.55)}`,
                },
              }}
            >
              Star on GitHub
            </Button>
          </Box>
        </ScrollReveal>
      </Container>
    </Box>
  );
}
