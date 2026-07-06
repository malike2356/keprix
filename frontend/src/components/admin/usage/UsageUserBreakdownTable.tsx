"use client";

import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonTable } from "@/components/ui/loading";
import type { UsageBreakdownRow } from "@/lib/usage-api";
import { formatTokenCount, formatUsdCost } from "@/lib/usage-format";

type UsageUserBreakdownTableProps = {
  rows?: UsageBreakdownRow[];
  loading?: boolean;
};

export default function UsageUserBreakdownTable({ rows, loading }: UsageUserBreakdownTableProps) {
  if (loading) {
    return (
      <DashboardCard title="By user">
        <SkeletonTable rows={6} columns={5} />
      </DashboardCard>
    );
  }

  const data = rows ?? [];

  return (
    <DashboardCard title="By user" subtitle="Instance-wide usage ranked by estimated cost">
      {!data.length ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
          No user breakdown for this period.
        </Typography>
      ) : (
        <TableContainer>
          <Table size="small" aria-label="LLM usage by user">
            <TableHead>
              <TableRow>
                <TableCell>User</TableCell>
                <TableCell align="right">Requests</TableCell>
                <TableCell align="right">Tokens</TableCell>
                <TableCell align="right">Cost</TableCell>
                <TableCell align="right">Share</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.map((row) => (
                <TableRow key={row.key}>
                  <TableCell>{row.label}</TableCell>
                  <TableCell align="right">{row.request_count.toLocaleString()}</TableCell>
                  <TableCell align="right">{formatTokenCount(row.total_tokens)}</TableCell>
                  <TableCell align="right">{formatUsdCost(row.total_cost_usd, "estimated")}</TableCell>
                  <TableCell align="right">{row.share_percent.toFixed(1)}%</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </DashboardCard>
  );
}
