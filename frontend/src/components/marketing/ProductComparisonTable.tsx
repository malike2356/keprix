"use client";

import Box from "@mui/material/Box";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import { alpha } from "@mui/material/styles";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import {
  MARKETING_EYEBROW_SX,
  MARKETING_HEADING_SX,
  useMarketingColors,
} from "@/components/marketing/MarketingSection";

/** Comparison benchmark: Upstream Hermes Agent vs. Forked Keprix OS. */
const ROWS = [
  {
    job: "Stand up a private agent OS",
    hermes: "CLI agent and gateway daemon; single-user terminal and chat gateway",
    keprix: "Docker Compose; one runtime with web, CLI, TUI, and API",
  },
  {
    job: "Operate from the terminal",
    hermes: "Interactive TUI, REPL, slash commands, and multi-platform gateway",
    keprix: "Command Center TUI with sessions, slash commands, tool cards, and runtime timeline",
  },
  {
    job: "Protect inbound messages",
    hermes: "Direct messaging routing without quarantine or content scanning",
    keprix: "Channel Shield scanning, quarantine, policy hooks, and safe summaries",
  },
  {
    job: "Run CRM and outreach with agents",
    hermes: "Not included; requires custom external scripts or standalone tools",
    keprix: "Agentic CRM, Soft Wall, Companies House, and outreach in one workspace",
  },
  {
    job: "Embed the agent beside another product",
    hermes: "Standalone CLI/daemon; custom RPC or socket integration",
    keprix: "Universal Sidecar contract: health, pairing, jobs, events, kill switch",
  },
  {
    job: "Need a tool that does not exist",
    hermes: "Autonomous skill creation and manual plugin authoring",
    keprix: "Mutation Engine synthesises; you approve",
  },
  {
    job: "Remember across sessions",
    hermes: "Curated memory nudges, FTS5 session search, Honcho user modeling",
    keprix: "Structured long-term memory built in",
  },
  {
    job: "Repeatable workflows",
    hermes: "Built-in cron scheduler with natural language triggers",
    keprix: "Playbooks with schedule and webhooks",
  },
  {
    job: "Know cost and failures",
    hermes: "Terminal logs and session token tracking",
    keprix: "Traces, token cost, budget alerts",
  },
  {
    job: "Own the stack",
    hermes: "Self-hosted, MIT open-source CLI agent by Nous Research",
    keprix: "Self-hosted, MIT, no cloud account required",
  },
] as const;

export function ProductComparisonTable() {
  const c = useMarketingColors();

  return (
    <Box>
      <Typography
        component="p"
        sx={{
          ...MARKETING_EYEBROW_SX,
          color: c.primary,
          mb: 2,
          textAlign: "center",
        }}
      >
        Lineage &amp; Benchmark
      </Typography>
      <Typography
        component="h2"
        sx={{
          ...MARKETING_HEADING_SX,
          fontSize: { xs: "2.1rem", md: "2.9rem" },
          mb: 1.5,
          color: c.textPrimary,
          textAlign: "center",
        }}
      >
        Upstream Hermes Agent vs. Forked Keprix OS
      </Typography>
      <Typography
        sx={{
          textAlign: "center",
          color: c.textSecondary,
          fontSize: "0.95rem",
          mb: 4,
          maxWidth: 680,
          mx: "auto",
          lineHeight: 1.7,
        }}
      >
        Keprix is forked from Hermes Agent by Nous Research. While Hermes delivers a
        lean terminal agent and messaging gateway, Keprix expands the foundation into
        a full self-hosted agent OS with a web workspace, multi-tenancy, and enterprise tools.
      </Typography>

      <Box
        sx={{
          overflowX: "auto",
          borderRadius: 2,
          border: `1px solid ${alpha(c.primary, 0.15)}`,
        }}
      >
        <Table size="small" sx={{ minWidth: 760, bgcolor: alpha(c.bgCard, 0.6) }}>
          <TableHead>
            <TableRow>
              <TableCell
                sx={{
                  fontWeight: 700,
                  color: c.textSecondary,
                  borderColor: c.divider,
                  width: "24%",
                }}
              >
                Capability
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: 700,
                  color: c.textSecondary,
                  borderColor: c.divider,
                  width: "38%",
                }}
              >
                Hermes Agent (upstream)
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: 800,
                  color: c.primary,
                  borderColor: c.divider,
                  bgcolor: alpha(c.primary, 0.08),
                  borderLeft: `2px solid ${alpha(c.primary, 0.35)}`,
                  width: "38%",
                }}
              >
                Keprix OS (forked)
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {ROWS.map((row) => (
              <TableRow key={row.job} hover>
                <TableCell
                  sx={{
                    color: c.textPrimary,
                    borderColor: c.divider,
                    fontSize: "0.85rem",
                    fontWeight: 600,
                    verticalAlign: "top",
                  }}
                >
                  {row.job}
                </TableCell>
                <TableCell
                  sx={{
                    color: c.textSecondary,
                    borderColor: c.divider,
                    fontSize: "0.85rem",
                    lineHeight: 1.5,
                    verticalAlign: "top",
                  }}
                >
                  {row.hermes}
                </TableCell>
                <TableCell
                  sx={{
                    color: c.textPrimary,
                    borderColor: c.divider,
                    bgcolor: alpha(c.primary, 0.04),
                    fontSize: "0.85rem",
                    fontWeight: 600,
                    lineHeight: 1.5,
                    verticalAlign: "top",
                  }}
                >
                  {row.keprix}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      <Box sx={{ display: "flex", justifyContent: "center", gap: 2, flexWrap: "wrap", mt: 4 }}>
        <Button
          component="a"
          href="https://github.com/nousresearch/hermes-agent"
          target="_blank"
          rel="noopener noreferrer"
          variant="outlined"
          endIcon={<OpenInNewIcon />}
          sx={{
            borderRadius: "9999px",
            px: 3,
            fontWeight: 700,
            borderColor: alpha(c.textSecondary, 0.38),
            color: c.textPrimary,
            bgcolor: "transparent",
            "&:hover": {
              borderColor: c.textPrimary,
              bgcolor: alpha(c.textSecondary, 0.08),
            },
          }}
        >
          View Hermes Agent Upstream
        </Button>
        <Button
          component="a"
          href="https://github.com/malike2356/keprix"
          target="_blank"
          rel="noopener noreferrer"
          variant="contained"
          endIcon={<OpenInNewIcon />}
          sx={{
            borderRadius: "9999px",
            px: 3,
            fontWeight: 700,
            bgcolor: c.primary,
            color: "#fff",
            "&:hover": {
              bgcolor: alpha(c.primary, 0.88),
            },
          }}
        >
          Explore Keprix on GitHub
        </Button>
      </Box>
    </Box>
  );
}
