"use client";

import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";
import { useMarketingColors } from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";
import { ProductComparisonTable } from "@/components/marketing/ProductComparisonTable";

export function ProductComparison() {
  const c = useMarketingColors();

  return (
    <Box
      sx={{
        py: { xs: 10, md: 14 },
        position: "relative",
        overflow: "hidden",
        bgcolor: c.bgDefault,
      }}
    >
      {/* Separator line */}
      <Box
        aria-hidden
        sx={{
          position: "absolute",
          top: 0,
          left: "50%",
          transform: "translateX(-50%)",
          width: "60%",
          height: 1,
          background: `linear-gradient(90deg, transparent, ${alpha(c.primary, 0.3)}, transparent)`,
        }}
      />

      <Container maxWidth="md" sx={{ position: "relative" }}>
        <ScrollReveal delay={0.08}>
          <ProductComparisonTable />
        </ScrollReveal>
      </Container>
    </Box>
  );
}
