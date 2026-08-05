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

/** Outcome-focused benchmark: DIY glue, Keprix self-hosting, and the wider Carina path. */
const ROWS = [
  {
    job: "Stand up a private agent OS",
    diy: "Wire LLM, DB, auth, and a process manager",
    keprix: "Docker Compose; one runtime with web, CLI, TUI, and API",
    carina: "Broader agent platform for teams, products, and managed deployments",
  },
  {
    job: "Operate from the terminal",
    diy: "Build a separate CLI, stream renderer, command palette, and diagnostics",
    keprix: "Command Center TUI with sessions, slash commands, tool cards, and runtime timeline",
    carina: "CLI and TUI surfaces for agent operations, Scout overlays, approvals, and sessions",
  },
  {
    job: "Protect inbound messages",
    diy: "Bolted-on filters, quarantine scripts, and manual review",
    keprix: "Channel Shield scanning, quarantine, policy hooks, and safe summaries",
    carina: "Platform-level channel protection patterns for customer-facing agent products",
  },
  {
    job: "Need a tool that does not exist",
    diy: "Write, test, and ship a plugin yourself",
    keprix: "Mutation Engine synthesises; you approve",
    carina: "Agent platform patterns for reusable capabilities, packs, and governed extensions",
  },
  {
    job: "Remember across sessions",
    diy: "Roll your own store and retrieval",
    keprix: "Structured long-term memory built in",
    carina: "Memory, profiles, and product-aware agent context across Carina-powered apps",
  },
  {
    job: "Repeatable workflows",
    diy: "Cron plus scripts plus glue",
    keprix: "Playbooks with schedule and webhooks",
    carina: "Workflow and agent orchestration for products built on the Carina platform",
  },
  {
    job: "Know cost and failures",
    diy: "Scatter logs across services",
    keprix: "Traces, token cost, budget alerts",
    carina: "Operations, usage, governance, and visibility across deployed agent surfaces",
  },
  {
    job: "Own the stack",
    diy: "Depends on each SaaS you bolted on",
    keprix: "Self-hosted, MIT, no cloud account required",
    carina: "Best when you want the broader Carina ecosystem, cloud path, or product platform",
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
        Runtime benchmark
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
        Choose the path that matches how you want to run agents.
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
        Keprix is the self-hosted mutant runtime. Carina is the broader agent
        platform path for teams, products, and managed deployments. Both beat
        stitching together fragile automation glue.
      </Typography>

      <Box
        sx={{
          overflowX: "auto",
          borderRadius: 2,
          border: `1px solid ${alpha(c.primary, 0.15)}`,
        }}
      >
        <Table size="small" sx={{ minWidth: 920, bgcolor: alpha(c.bgCard, 0.6) }}>
          <TableHead>
            <TableRow>
              <TableCell
                sx={{
                  fontWeight: 700,
                  color: c.textSecondary,
                  borderColor: c.divider,
                  width: "18%",
                }}
              >
                Job
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: 600,
                  color: c.textSecondary,
                  borderColor: c.divider,
                  width: "27%",
                }}
              >
                Piecewise stack
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: 800,
                  color: c.primary,
                  borderColor: c.divider,
                  bgcolor: alpha(c.primary, 0.08),
                  borderLeft: `2px solid ${alpha(c.primary, 0.35)}`,
                  width: "28%",
                }}
              >
                Keprix runtime
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: 800,
                  color: c.textPrimary,
                  borderColor: c.divider,
                  bgcolor: alpha(c.secondary, 0.08),
                  borderLeft: `2px solid ${alpha(c.secondary, 0.32)}`,
                  borderRight: `2px solid ${alpha(c.secondary, 0.32)}`,
                  width: "27%",
                }}
              >
                Carina platform
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
                  {row.diy}
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
                <TableCell
                  sx={{
                    color: c.textPrimary,
                    borderColor: c.divider,
                    bgcolor: alpha(c.secondary, 0.04),
                    fontSize: "0.85rem",
                    fontWeight: 600,
                    lineHeight: 1.5,
                    verticalAlign: "top",
                  }}
                >
                  {row.carina}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      <Box sx={{ display: "flex", justifyContent: "center", mt: 4 }}>
        <Button
          component="a"
          href="https://carinaai.uk"
          target="_blank"
          rel="noopener noreferrer"
          variant="outlined"
          endIcon={<OpenInNewIcon />}
          sx={{
            borderRadius: "9999px",
            px: 3,
            fontWeight: 700,
            borderColor: alpha(c.secondary, 0.38),
            color: c.textPrimary,
            bgcolor: alpha(c.secondary, 0.04),
            "&:hover": {
              borderColor: c.secondary,
              bgcolor: alpha(c.secondary, 0.09),
            },
          }}
        >
          Visit Carina
        </Button>
      </Box>
    </Box>
  );
}
