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

/** Outcome-focused benchmark: DIY glue, Keprix self-hosting, and the Verlox enterprise platform. */
const ROWS = [
  {
    job: "Stand up a private agent OS",
    diy: "Wire LLM, DB, auth, and a process manager",
    keprix: "Docker Compose; one runtime with web, CLI, TUI, and API",
    verlox: "Managed enterprise platform for teams, governance, and organizational deployments",
  },
  {
    job: "Operate from the terminal",
    diy: "Build a separate CLI, stream renderer, command palette, and diagnostics",
    keprix: "Command Center TUI with sessions, slash commands, tool cards, and runtime timeline",
    verlox: "Centralized operator consoles, audit logs, team controls, and session management",
  },
  {
    job: "Protect inbound messages",
    diy: "Bolted-on filters, quarantine scripts, and manual review",
    keprix: "Channel Shield scanning, quarantine, policy hooks, and safe summaries",
    verlox: "Enterprise gateway filters, policy enforcement, and compliance controls",
  },
  {
    job: "Run CRM and outreach with agents",
    diy: "Separate CRM, enrichment scripts, and approval spreadsheets",
    keprix: "Agentic CRM, Soft Wall, Companies House, and outreach in one workspace",
    verlox: "Enterprise CRM integration and governed multi-team outreach infrastructure",
  },
  {
    job: "Embed the agent beside another product",
    diy: "Custom microservice and auth glue per product",
    keprix: "Universal Sidecar contract: health, pairing, jobs, events, kill switch",
    verlox: "Native enterprise sidecar and API integrations across the Verlox ecosystem",
  },
  {
    job: "Need a tool that does not exist",
    diy: "Write, test, and ship a plugin yourself",
    keprix: "Mutation Engine synthesises; you approve",
    verlox: "Governed extensions, verified capabilities, and centralized team tool registry",
  },
  {
    job: "Remember across sessions",
    diy: "Roll your own store and retrieval",
    keprix: "Structured long-term memory built in",
    verlox: "Organizational knowledge graphs, cross-workspace memory, and access control",
  },
  {
    job: "Repeatable workflows",
    diy: "Cron plus scripts plus glue",
    keprix: "Playbooks with schedule and webhooks",
    verlox: "Enterprise workflow automation, scheduled compliance runs, and multi-tenant triggers",
  },
  {
    job: "Know cost and failures",
    diy: "Scatter logs across services",
    keprix: "Traces, token cost, budget alerts",
    verlox: "Real-time cost observability, enterprise audit trails, and tenant budgeting",
  },
  {
    job: "Own the stack",
    diy: "Depends on each SaaS you bolted on",
    keprix: "Self-hosted, MIT, no cloud account required",
    verlox: "Managed enterprise deployments, cloud-hosted SLAs, and direct support from Verlox Ltd",
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
        Keprix is the self-hosted open-source runtime. Verlox provides the broader
        enterprise platform for teams, products, and managed deployments. Both beat
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
                Verlox Enterprise
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
                  {row.verlox}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      <Box sx={{ display: "flex", justifyContent: "center", mt: 4 }}>
        <Button
          component="a"
          href="https://verlox.uk"
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
          Visit Verlox
        </Button>
      </Box>
    </Box>
  );
}
