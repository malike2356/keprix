"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { alpha } from "@mui/material/styles";
import {
  MARKETING_HEADING_SX,
  useMarketingColors,
} from "@/components/marketing/MarketingSection";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";

const FAQS = [
  {
    q: "How is Keprix different from n8n or Dify?",
    a: "n8n and Dify are workflow builders. Keprix is a self-hosted agent OS with a web workspace, Command Center TUI, long-term memory, playbooks, Channel Shield, governance, and reviewable self-coding.",
  },
  {
    q: "What channels can I connect?",
    a: "Telegram, Discord, Slack, WhatsApp (via Twilio), email (IMAP/SMTP), webhooks, and the Keprix REST API. Each channel gets its own persona and tool configuration.",
  },
  {
    q: "Is Keprix really free?",
    a: "Yes. MIT license. Use it commercially, modify it, self-host it. Optional governance connectors are separate paid add-ons.",
  },
  {
    q: "What is the Command Center TUI?",
    a: "It is the terminal interface for Keprix. Operators can chat, switch sessions, run slash commands, inspect runtime events, review tool calls, open diagnostics, and work without leaving the keyboard.",
  },
  {
    q: "What does Channel Shield do?",
    a: "Channel Shield routes inbound email and messaging through scanning, policy checks, sandboxing, and quarantine before unsafe content reaches agents or people.",
  },
  {
    q: "What does the Mutation Engine mean?",
    a: "When Keprix cannot complete a task with its existing tools, it can propose a new tool or code change, run it in a sandbox, and ask you to approve before installing it.",
  },
  {
    q: "Do I need a GPU?",
    a: "No. Keprix routes to cloud LLM APIs by default (Anthropic, OpenAI, Gemini, etc.). GPU acceleration is supported for local models via Ollama.",
  },
  {
    q: "Where is my data stored?",
    a: "On your server. PostgreSQL and Redis run inside Docker on your machine. Nothing leaves your infrastructure unless you explicitly connect a cloud LLM.",
  },
  {
    q: "Can I use Keprix with my own LLM?",
    a: "Yes. Keprix supports Ollama for local models and any OpenAI-compatible API endpoint.",
  },
  {
    q: "What is the difference between Keprix and managed SaaS?",
    a: "Keprix is the self-hosted open-source agent OS. Managed SaaS products can extend Keprix with billing, hosting, and vendor-specific features. They are separate distributions.",
  },
  {
    q: "Is there a hosted or cloud version of Keprix?",
    a: "No. Core Keprix is intentionally self-hosted. Vendors may offer managed hosting as a separate product built on the platform.",
  },
  {
    q: "How do I contribute?",
    a: "Open an issue or PR at github.com/malike2356/keprix. See CONTRIBUTING.md for the contributor guide.",
  },
] as const;

export function FAQ() {
  const c = useMarketingColors();
  const [expanded, setExpanded] = React.useState<string | false>("faq-0");

  const handleChange =
    (panel: string) => (_event: React.SyntheticEvent, isExpanded: boolean) => {
      setExpanded(isExpanded ? panel : false);
    };

  return (
    <Box
      sx={{
        py: { xs: 12, md: 16 },
        borderTop: `1px solid ${c.divider}`,
      }}
    >
      <Container maxWidth="md">
        <ScrollReveal>
          <Typography
            component="h2"
            sx={{
              ...MARKETING_HEADING_SX,
              fontSize: { xs: "2.2rem", md: "3rem" },
              mb: 8,
              textAlign: "center",
              color: c.textPrimary,
            }}
          >
            Frequently asked questions
          </Typography>
        </ScrollReveal>

        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
          {FAQS.map((faq, i) => (
            <ScrollReveal key={i} delay={i * 0.04}>
              <Accordion
                disableGutters
                expanded={expanded === `faq-${i}`}
                onChange={handleChange(`faq-${i}`)}
                sx={{
                  bgcolor: c.bgCard,
                  border: `1px solid ${c.divider}`,
                  borderRadius: "12px !important",
                  boxShadow: "0 1px 2px rgba(24,24,30,0.05)",
                  "&:before": { display: "none" },
                  "&:hover": {
                    borderColor: alpha(c.primary, 0.35),
                  },
                  "&.Mui-expanded": {
                    borderColor: alpha(c.primary, 0.45),
                    boxShadow: `0 4px 16px ${alpha(c.primary, 0.1)}`,
                  },
                  transition: "border-color 0.25s, box-shadow 0.25s",
                }}
              >
                <AccordionSummary
                  expandIcon={
                    <ExpandMoreIcon sx={{ color: c.textSecondary, fontSize: 20 }} />
                  }
                  sx={{ px: 3, py: 1.25 }}
                >
                  <Typography
                    sx={{ fontWeight: 600, color: c.textPrimary, fontSize: "0.95rem" }}
                  >
                    {faq.q}
                  </Typography>
                </AccordionSummary>
                <AccordionDetails sx={{ px: 3, pt: 0, pb: 2.5 }}>
                  <Typography
                    sx={{ color: c.textSecondary, fontSize: "0.9rem", lineHeight: 1.75 }}
                  >
                    {faq.a}
                  </Typography>
                </AccordionDetails>
              </Accordion>
            </ScrollReveal>
          ))}
        </Box>
      </Container>
    </Box>
  );
}
