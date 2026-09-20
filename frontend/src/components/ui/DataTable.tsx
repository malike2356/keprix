"use client";

import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import useMediaQuery from "@mui/material/useMediaQuery";
import type { ReactNode } from "react";
import { SkeletonTable } from "@/components/ui/loading";
import EmptyState from "@/components/ui/EmptyState";

export type DataTableColumn<T> = {
  id: string;
  label: string;
  width?: number | string;
  render?: (row: T) => ReactNode;
  numeric?: boolean;
};

type DataTableProps<T> = {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  loading?: boolean;
  emptyMessage?: ReactNode;
  onRowClick?: (row: T) => void;
  emptyActionLabel?: string;
  onEmptyAction?: () => void;
  stickyFirst?: boolean;
  responsiveStack?: boolean;
};

export default function DataTable<T>({
  columns,
  rows,
  rowKey,
  loading = false,
  emptyMessage = "No records found.",
  onRowClick,
  emptyActionLabel,
  onEmptyAction,
  stickyFirst = false,
  responsiveStack = columns.length > 4,
}: DataTableProps<T>) {
  const mobile = useMediaQuery("(max-width:699px)");

  if (loading) {
    return <SkeletonTable rows={6} columns={Math.max(columns.length, 1)} />;
  }

  if (rows.length === 0) {
    if (emptyActionLabel && onEmptyAction) {
      return (
        <EmptyState
          title="No records"
          description={typeof emptyMessage === "string" ? emptyMessage : "No records are available yet."}
          actionLabel={emptyActionLabel}
          onAction={onEmptyAction}
        />
      );
    }
    return (
      <Typography variant="body2" color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
        {emptyMessage}
      </Typography>
    );
  }

  if (mobile && responsiveStack) {
    return (
      <Box sx={{ display: "grid", gap: 1.5 }}>
        {rows.map((row) => (
          <Paper
            key={rowKey(row)}
            variant="outlined"
            onClick={onRowClick ? () => onRowClick(row) : undefined}
            sx={{ p: 2, display: "grid", gap: 1, cursor: onRowClick ? "pointer" : "default" }}
          >
            {columns.map((column) => (
              <Box key={column.id} sx={{ display: "grid", gridTemplateColumns: "minmax(100px, 40%) 1fr", gap: 1 }}>
                <Typography variant="caption" color="text.secondary">{column.label}</Typography>
                <Box sx={{ textAlign: column.numeric ? "right" : "left", fontVariantNumeric: column.numeric ? "tabular-nums" : undefined }}>
                  {column.render ? column.render(row) : String((row as Record<string, unknown>)[column.id] ?? "")}
                </Box>
              </Box>
            ))}
          </Paper>
        ))}
      </Box>
    );
  }

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            {columns.map((column, index) => (
              <TableCell
                key={column.id}
                width={column.width}
                align={column.numeric ? "right" : "left"}
                sx={stickyFirst && index === 0 ? { position: "sticky", left: 0, zIndex: 2, bgcolor: "background.paper" } : undefined}
              >
                {column.label}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <TableRow
              key={rowKey(row)}
              hover={Boolean(onRowClick)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              sx={{ cursor: onRowClick ? "pointer" : "default" }}
            >
              {columns.map((column, index) => (
                <TableCell
                  key={column.id}
                  align={column.numeric ? "right" : "left"}
                  sx={{
                    fontVariantNumeric: column.numeric ? "tabular-nums" : undefined,
                    ...(stickyFirst && index === 0 ? { position: "sticky", left: 0, zIndex: 1, bgcolor: "background.paper" } : {}),
                  }}
                >
                  {column.render ? column.render(row) : String((row as Record<string, unknown>)[column.id] ?? "")}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
