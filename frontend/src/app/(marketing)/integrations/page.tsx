import type { Metadata } from "next";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import { IntegrationsCatalog, IntegrationsMarquee } from "@/components/marketing/Integrations";
import { MarketingSection } from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";

export const metadata: Metadata = {
  title: "Integrations",
  description:
    "LLM providers, messaging channels, and infrastructure that Keprix connects to out of the box.",
};

export default function IntegrationsPage() {
  return (
    <MarketingSection tone="dark">
      <Box sx={{ pt: { xs: 12, md: 16 }, pb: { xs: 10, md: 14 } }}>
        <Container maxWidth="lg">
          <ScrollReveal>
            <Typography
              component="h1"
              sx={{
                fontSize: { xs: "2rem", md: "2.75rem" },
                fontWeight: 800,
                letterSpacing: "-0.03em",
                mb: 2,
              }}
            >
              Integrations
            </Typography>
            <Typography
              sx={{
                maxWidth: 640,
                color: "text.secondary",
                fontSize: "1.05rem",
                lineHeight: 1.7,
                mb: 6,
              }}
            >
              Route to any major LLM API, talk to your agent on the channels you already use, and
              deploy on the stack you control.
            </Typography>
          </ScrollReveal>

          <Box sx={{ mb: 8 }}>
            <IntegrationsMarquee />
          </Box>

          <ScrollReveal>
            <IntegrationsCatalog />
          </ScrollReveal>
        </Container>
      </Box>
    </MarketingSection>
  );
}
