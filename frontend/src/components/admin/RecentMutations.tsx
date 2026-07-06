"use client";

import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import NextLink from "next/link";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonTable } from "@/components/ui/loading";
import { formatTimeAgo } from "@/lib/time-ago";
import type { MutationRow } from "@/lib/admin-dashboard-api";

type RecentMutationsProps = {
  rows?: MutationRow[];
  loading?: boolean;
};

function statusColor(status: string): "warning" | "success" | "error" | "default" {
  if (status === "pending" || status === "staged") return "warning";
  if (status === "approved") return "success";
  if (status === "rejected") return "error";
  return "default";
}

export default function RecentMutations({ rows = [], loading }: RecentMutationsProps) {
  return (
    <DashboardCard title="Recent tool synthesis requests">
      {loading ? (
        <SkeletonTable rows={5} columns={5} />
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Tool</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Workspace</TableCell>
              <TableCell>Requested</TableCell>
              <TableCell align="right">Action</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} sx={{ py: 4, color: "text.secondary" }}>
                  No mutation requests yet.
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row) => (
                <TableRow key={row.id} hover>
                  <TableCell>{row.tool_name}</TableCell>
                  <TableCell>
                    <Chip size="small" label={row.status} color={statusColor(row.status)} variant="outlined" />
                  </TableCell>
                  <TableCell>{row.workspace_id || "default"}</TableCell>
                  <TableCell>{row.requested_at ? formatTimeAgo(row.requested_at) : "-"}</TableCell>
                  <TableCell align="right">
                    <Button component={NextLink} href={`/admin/mutations?id=${row.id}`} size="small">
                      Review
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      )}
    </DashboardCard>
  );
}
