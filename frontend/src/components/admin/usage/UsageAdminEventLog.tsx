"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Link from "@mui/material/Link";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TablePagination from "@mui/material/TablePagination";
import TableRow from "@mui/material/TableRow";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import * as React from "react";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonTable } from "@/components/ui/loading";
import type { UsageEventRow } from "@/lib/usage-api";
import { costTooltip, formatRecordedAt, formatTokenCount, formatUsdCost } from "@/lib/usage-format";

type UsageAdminEventLogProps = {
  items?: UsageEventRow[];
  total?: number;
  loading?: boolean;
  page: number;
  rowsPerPage: number;
  onPageChange: (page: number) => void;
  onRowsPerPageChange: (rowsPerPage: number) => void;
  onExport: () => void;
  exporting?: boolean;
};

export default function UsageAdminEventLog({
  items,
  total = 0,
  loading,
  page,
  rowsPerPage,
  onPageChange,
  onRowsPerPageChange,
  onExport,
  exporting = false,
}: UsageAdminEventLogProps) {
  if (loading) {
    return (
      <DashboardCard title="Event log">
        <SkeletonTable rows={6} columns={7} />
      </DashboardCard>
    );
  }

  const rows = items ?? [];

  return (
    <DashboardCard
      title="Event log"
      subtitle="Paginated LLM usage events across the instance"
      action={
        <Button size="small" variant="outlined" disabled={exporting} onClick={onExport}>
          Export CSV
        </Button>
      }
    >
      {!rows.length ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
          No events in this period.
        </Typography>
      ) : (
        <Box>
          <TableContainer>
            <Table size="small" aria-label="Admin LLM usage event log">
              <TableHead>
                <TableRow>
                  <TableCell>Time</TableCell>
                  <TableCell>User</TableCell>
                  <TableCell>Channel</TableCell>
                  <TableCell>Model</TableCell>
                  <TableCell align="right">Tokens</TableCell>
                  <TableCell align="right">Cost</TableCell>
                  <TableCell>Session / run</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row) => {
                  const tooltip = costTooltip(row.cost_status);
                  const costLabel = formatUsdCost(row.cost_usd, row.cost_status);
                  return (
                    <TableRow key={row.id}>
                      <TableCell>{formatRecordedAt(row.recorded_at)}</TableCell>
                      <TableCell>{row.user_id || "-"}</TableCell>
                      <TableCell>{row.channel || "-"}</TableCell>
                      <TableCell>{row.model || "-"}</TableCell>
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
          <TablePagination
            component="div"
            count={total}
            page={page}
            onPageChange={(_event, nextPage) => onPageChange(nextPage)}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={(event) => onRowsPerPageChange(Number(event.target.value))}
            rowsPerPageOptions={[25, 50, 100]}
          />
        </Box>
      )}
    </DashboardCard>
  );
}
