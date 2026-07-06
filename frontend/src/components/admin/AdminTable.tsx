"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TablePagination from "@mui/material/TablePagination";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";

type Column<T> = {
  id: keyof T | string;
  label: string;
  width?: number | string;
  render?: (row: T) => React.ReactNode;
};

type AdminTableProps<T extends { id: string }> = {
  title?: string;
  columns: Column<T>[];
  rows: T[];
  loading?: boolean;
  action?: React.ReactNode;
  page?: number;
  rowsPerPage?: number;
  total?: number;
  onPageChange?: (page: number) => void;
  onRowClick?: (row: T) => void;
};

export default function AdminTable<T extends { id: string }>({
  title,
  columns,
  rows,
  loading = false,
  action,
  page = 0,
  rowsPerPage = 25,
  total,
  onPageChange,
  onRowClick,
}: AdminTableProps<T>) {
  return (
    <Paper variant="outlined" sx={{ borderRadius: 2 }}>
      {title || action ? (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            px: 2.5,
            py: 1.75,
          }}
        >
          {title ? (
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              {title}
            </Typography>
          ) : (
            <span />
          )}
          {action}
        </Box>
      ) : null}
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              {columns.map((col) => (
                <TableCell key={String(col.id)} sx={{ fontWeight: 600, width: col.width }}>
                  {col.label}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {columns.map((col) => (
                    <TableCell key={String(col.id)}>
                      <Box sx={{ height: 16, bgcolor: "divider", borderRadius: 0.5, width: "70%" }} />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} sx={{ textAlign: "center", py: 4, color: "text.secondary" }}>
                  No records found.
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row) => (
                <TableRow
                  key={row.id}
                  hover
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  sx={onRowClick ? { cursor: "pointer" } : undefined}
                >
                  {columns.map((col) => (
                    <TableCell key={String(col.id)}>
                      {col.render
                        ? col.render(row)
                        : String((row as Record<string, unknown>)[String(col.id)] ?? "")}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
      {total !== undefined && onPageChange ? (
        <TablePagination
          component="div"
          count={total}
          page={page}
          rowsPerPage={rowsPerPage}
          onPageChange={(_, p) => onPageChange(p)}
          rowsPerPageOptions={[]}
        />
      ) : null}
    </Paper>
  );
}
