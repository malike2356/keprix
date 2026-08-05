"use client";

import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import { alpha } from "@mui/material/styles";
import CodeIcon from "@mui/icons-material/Code";
import {
  MARKETING_EYEBROW_SX,
  MARKETING_HEADING_SX,
  useMarketingColors,
} from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";

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
            <Typography sx={{ ...MARKETING_EYEBROW_SX, color: c.success }}>
              MIT License - Free forever
            </Typography>
          </Box>

          <Typography
            component="h2"
            sx={{
              ...MARKETING_HEADING_SX,
              fontSize: { xs: "2.4rem", md: "3.35rem" },
              mb: 2.5,
              color: c.textPrimary,
              maxWidth: 760,
              mx: "auto",
            }}
          >
            Keprix is free and
            <br />
            open source. Forever.
          </Typography>

          <Typography
            sx={{ color: c.textSecondary, mb: 5, fontSize: "1.05rem", maxWidth: 420, mx: "auto", lineHeight: 1.7 }}
          >
            MIT license. Use it commercially. Modify it. Self-host it. No strings attached.
          </Typography>

          <Button
            component="a"
            href="https://github.com/malike2356/keprix"
            target="_blank"
            rel="noopener noreferrer"
            variant="contained"
            startIcon={<CodeIcon />}
            sx={{
              fontWeight: 700,
              borderRadius: "9999px",
              px: 3.5,
              background: `linear-gradient(135deg, ${c.primary} 0%, ${c.secondary} 100%)`,
              boxShadow: `0 4px 24px ${alpha(c.primary, 0.4)}`,
              "&:hover": {
                boxShadow: `0 6px 32px ${alpha(c.primary, 0.55)}`,
              },
            }}
          >
            View on GitHub
          </Button>
        </ScrollReveal>
      </Container>
    </Box>
  );
}
