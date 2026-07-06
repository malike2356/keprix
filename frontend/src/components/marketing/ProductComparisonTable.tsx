"use client";

import Box from "@mui/material/Box";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import CheckIcon from "@mui/icons-material/Check";
import { alpha } from "@mui/material/styles";
import { useMarketingColors } from "@/components/marketing/MarketingSection";

const ROWS = [
  { feature: "Self-hosted", keprix: true, n8n: true, dify: true, langchain: false, autogen: false },
  {
    feature: "Mutation Engine (self-coding tools)",
    keprix: true,
    n8n: false,
    dify: false,
    langchain: false,
    autogen: false,
  },
  { feature: "Multi-channel inbox", keprix: true, n8n: true, dify: false, langchain: false, autogen: false },
  { feature: "Playbook scheduler", keprix: true, n8n: true, dify: false, langchain: false, autogen: false },
  {
    feature: "Long-term memory (structured)",
    keprix: true,
    n8n: false,
    dify: true,
    langchain: true,
    autogen: true,
  },
  {
    feature: "Budget alerts + observability",
    keprix: true,
    n8n: false,
    dify: false,
    langchain: false,
    autogen: false,
  },
  { feature: "MIT license", keprix: true, n8n: true, dify: true, langchain: true, autogen: false },
  {
    feature: "No cloud account required",
    keprix: true,
    n8n: true,
    dify: true,
    langchain: true,
    autogen: true,
  },
] as const;

const COLUMNS = [
  { key: "keprix", label: "Keprix", highlight: true },
  { key: "n8n", label: "n8n", highlight: false },
  { key: "dify", label: "Dify", highlight: false },
  { key: "langchain", label: "LangChain", highlight: false },
  { key: "autogen", label: "AutoGen", highlight: false },
] as const;

function CellValue({ value }: { value: boolean }) {
  const c = useMarketingColors();
  return value ? (
    <CheckIcon sx={{ fontSize: 18, color: c.success }} aria-label="Yes" />
  ) : (
    <Typography component="span" sx={{ color: alpha(c.textSecondary, 0.5), fontSize: "1.1rem" }}>
      -
    </Typography>
  );
}

export function ProductComparisonTable() {
  const c = useMarketingColors();

  return (
    <Box sx={{ mt: { xs: 6, md: 8 } }}>
      <Typography
        component="h3"
        sx={{
          fontSize: { xs: "1.35rem", md: "1.65rem" },
          fontWeight: 800,
          letterSpacing: "-0.02em",
          mb: 1,
          color: c.textPrimary,
          textAlign: "center",
        }}
      >
        How Keprix compares
      </Typography>
      <Typography
        sx={{
          textAlign: "center",
          color: c.textSecondary,
          fontSize: "0.9rem",
          mb: 3,
          maxWidth: 520,
          mx: "auto",
        }}
      >
        Agent runtime with mutation and observability vs workflow builders and frameworks.
      </Typography>

      <Box sx={{ overflowX: "auto", borderRadius: 2, border: `1px solid ${alpha(c.primary, 0.15)}` }}>
        <Table size="small" sx={{ minWidth: 640, bgcolor: alpha(c.bgCard, 0.6) }}>
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 700, color: c.textSecondary, borderColor: c.divider }}>
                Capability
              </TableCell>
              {COLUMNS.map((col) => (
                <TableCell
                  key={col.key}
                  align="center"
                  sx={{
                    fontWeight: col.highlight ? 800 : 600,
                    color: col.highlight ? c.primary : c.textSecondary,
                    borderColor: c.divider,
                    bgcolor: col.highlight ? alpha(c.primary, 0.08) : "transparent",
                    borderLeft: col.highlight ? `2px solid ${alpha(c.primary, 0.35)}` : undefined,
                    borderRight: col.highlight ? `2px solid ${alpha(c.primary, 0.35)}` : undefined,
                  }}
                >
                  {col.label}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {ROWS.map((row) => (
              <TableRow key={row.feature} hover>
                <TableCell sx={{ color: c.textPrimary, borderColor: c.divider, fontSize: "0.85rem" }}>
                  {row.feature}
                </TableCell>
                {COLUMNS.map((col) => (
                  <TableCell
                    key={col.key}
                    align="center"
                    sx={{
                      borderColor: c.divider,
                      bgcolor: col.highlight ? alpha(c.primary, 0.04) : "transparent",
                    }}
                  >
                    <CellValue value={row[col.key as keyof typeof row] as boolean} />
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Box>
  );
}
