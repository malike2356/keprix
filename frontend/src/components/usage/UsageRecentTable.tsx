"use client";

import Link from "@mui/material/Link";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonTable } from "@/components/ui/loading";
import type { UsageEventRow } from "@/lib/usage-api";
import { costTooltip, formatRecordedAt, formatTokenCount, formatUsdCost } from "@/lib/usage-format";

type UsageRecentTableProps = {
  items?: UsageEventRow[];
  loading?: boolean;
  subtitle?: string;
};

export default function UsageRecentTable({ items, loading, subtitle }: UsageRecentTableProps) {
  if (loading) {
    return (
      <DashboardCard title="Recent usage">
        <SkeletonTable rows={6} columns={6} />
      </DashboardCard>
    );
  }

  const rows = items ?? [];

  return (
    <DashboardCard
      title="Recent usage"
      subtitle={subtitle || "Latest LLM calls for your account"}
    >
      {rows.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
          No recent events in this period.
        </Typography>
      ) : (
        <TableContainer>
          <Table size="small" aria-label="Recent LLM usage events">
            <TableHead>
              <TableRow>
                <TableCell>Time</TableCell>
                <TableCell>Model</TableCell>
                <TableCell>Channel</TableCell>
                <TableCell align="right">Tokens</TableCell>
                <TableCell align="right">Cost</TableCell>
                <TableCell>Session</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => {
                const tooltip = costTooltip(row.cost_status);
                const costLabel = formatUsdCost(row.cost_usd, row.cost_status);
                return (
                  <TableRow key={row.id}>
                    <TableCell>{formatRecordedAt(row.recorded_at)}</TableCell>
                    <TableCell>{row.model || "-"}</TableCell>
                    <TableCell>{row.channel || "-"}</TableCell>
                    <TableCell align="right">{formatTokenCount(row.total_tokens)}</TableCell>
                    <TableCell align="right">
                      {tooltip ? (
                        <Tooltip title={tooltip}>
                          <span>{costLabel}</span>
                        </Tooltip>
                      ) : (
                        costLabel
                      )}
                    </TableCell>
                    <TableCell>
                      {row.session_id ? (
                        <Link component={NextLink} href={`/chat/${row.session_id}`} underline="hover">
                          {row.session_id.slice(0, 8)}
                        </Link>
                      ) : (
                        "-"
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </DashboardCard>
  );
}
