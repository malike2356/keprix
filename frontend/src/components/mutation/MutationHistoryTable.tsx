"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import MutationQualityBadge from "@/components/mutation/MutationQualityBadge";
import { SkeletonTable } from "@/components/ui/loading";
import type { MutationHistoryFilters, MutationRecord } from "@/lib/mutation-api";
import { formatTimeAgo } from "@/lib/time-ago";

const STATUS_COLORS: Record<string, "default" | "success" | "warning" | "error" | "info"> = {
  approved: "success",
  staged: "warning",
  quarantined: "error",
  pruned: "default",
  expired: "default",
  rolled_back: "info",
  rejected: "error",
};

type MutationHistoryTableProps = {
  items: MutationRecord[];
  loading?: boolean;
  filters?: MutationHistoryFilters;
  onFiltersChange?: (filters: MutationHistoryFilters) => void;
  showFilters?: boolean;
  page?: number;
  total?: number;
  onPageChange?: (page: number) => void;
};

export default function MutationHistoryTable({
  items,
  loading = false,
  filters = {},
  onFiltersChange,
  showFilters = true,
  page = 1,
  total = 0,
  onPageChange,
}: MutationHistoryTableProps) {
  const updateFilter = (patch: Partial<MutationHistoryFilters>) => {
    onFiltersChange?.({ ...filters, ...patch, page: 1 });
  };

  return (
    <Box sx={{ display: "grid", gap: 2 }}>
      {showFilters ? (
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          <Select
            size="small"
            displayEmpty
            value={filters.tier ?? ""}
            onChange={(event) => updateFilter({ tier: event.target.value || undefined })}
            sx={{ minWidth: 120 }}
          >
            <MenuItem value="">All tiers</MenuItem>
            <MenuItem value="tool">Tool</MenuItem>
            <MenuItem value="prompt">Prompt</MenuItem>
            <MenuItem value="code">Code</MenuItem>
          </Select>
          <Select
            size="small"
            displayEmpty
            value={filters.status ?? ""}
            onChange={(event) => updateFilter({ status: event.target.value || undefined })}
            sx={{ minWidth: 120 }}
          >
            <MenuItem value="">All statuses</MenuItem>
            <MenuItem value="staged">Staged</MenuItem>
            <MenuItem value="approved">Approved</MenuItem>
            <MenuItem value="quarantined">Quarantined</MenuItem>
            <MenuItem value="pruned">Pruned</MenuItem>
          </Select>
          <TextField
            size="small"
            label="Trigger"
            value={filters.trigger ?? ""}
            onChange={(event) => updateFilter({ trigger: event.target.value || undefined })}
          />
          <TextField
            size="small"
            type="date"
            label="From"
            InputLabelProps={{ shrink: true }}
            value={filters.dateFrom ?? ""}
            onChange={(event) => updateFilter({ dateFrom: event.target.value || undefined })}
          />
          <TextField
            size="small"
            type="date"
            label="To"
            InputLabelProps={{ shrink: true }}
            value={filters.dateTo ?? ""}
            onChange={(event) => updateFilter({ dateTo: event.target.value || undefined })}
          />
        </Box>
      ) : null}

      {loading ? (
        <SkeletonTable rows={6} columns={7} />
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Time</TableCell>
              <TableCell>Tier</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Trigger</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Quality</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((item) => (
              <TableRow key={item.id} hover>
                <TableCell>{formatTimeAgo(item.recorded_at)}</TableCell>
                <TableCell sx={{ textTransform: "uppercase" }}>{item.tier}</TableCell>
                <TableCell>{item.name}</TableCell>
                <TableCell>{item.trigger}</TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={item.status}
                    color={STATUS_COLORS[item.status] ?? "default"}
                  />
                </TableCell>
                <TableCell>
                  <MutationQualityBadge
                    score={item.quality_score}
                    useCount={item.use_count}
                    status={item.status}
                  />
                </TableCell>
                <TableCell align="right">
                  <Button component="a" href={`/dashboard/mutation/${item.id}`} size="small">
                    View
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {onPageChange && total > 20 ? (
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Typography variant="caption" color="text.secondary">
            Page {page} of {Math.max(1, Math.ceil(total / 20))}
          </Typography>
          <Box sx={{ display: "flex", gap: 1 }}>
            <Button size="small" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
              Previous
            </Button>
            <Button
              size="small"
              disabled={page >= Math.ceil(total / 20)}
              onClick={() => onPageChange(page + 1)}
            >
              Next
            </Button>
          </Box>
        </Box>
      ) : null}
    </Box>
  );
}
