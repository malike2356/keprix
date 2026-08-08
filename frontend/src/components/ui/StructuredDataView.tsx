"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";

type StructuredDataViewProps = {
  value: unknown;
  emptyLabel?: string;
  maxDepth?: number;
  maxRows?: number;
  dense?: boolean;
};

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function formatScalar(value: unknown): string {
  if (value == null) return "-";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : "-";
  if (typeof value === "string") return value.trim() ? value : "-";
  return String(value);
}

function PrimitiveList({ items }: { items: unknown[] }) {
  if (items.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        -
      </Typography>
    );
  }
  return (
    <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
      {items.map((item, idx) => (
        <Chip key={`${formatScalar(item)}-${idx}`} size="small" label={formatScalar(item)} variant="outlined" />
      ))}
    </Stack>
  );
}

function ObjectTable({
  value,
  depth,
  maxDepth,
  dense,
}: {
  value: Record<string, unknown>;
  depth: number;
  maxDepth: number;
  dense: boolean;
}) {
  const entries = Object.entries(value);
  if (entries.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No fields
      </Typography>
    );
  }
  return (
    <Table size={dense ? "small" : "medium"}>
      <TableHead>
        <TableRow>
          <TableCell width="30%">Field</TableCell>
          <TableCell>Value</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {entries.map(([key, child]) => (
          <TableRow key={key}>
            <TableCell sx={{ verticalAlign: "top" }}>
              <Typography variant="body2" fontWeight={600}>
                {key}
              </Typography>
            </TableCell>
            <TableCell sx={{ verticalAlign: "top" }}>
              <StructuredDataViewInner value={child} depth={depth + 1} maxDepth={maxDepth} dense={dense} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function ArrayOfObjectsTable({
  rows,
  depth,
  maxDepth,
  maxRows,
  dense,
}: {
  rows: Record<string, unknown>[];
  depth: number;
  maxDepth: number;
  maxRows: number;
  dense: boolean;
}) {
  const visible = rows.slice(0, maxRows);
  const keys = Array.from(
    visible.reduce((set, row) => {
      Object.keys(row).forEach((key) => set.add(key));
      return set;
    }, new Set<string>()),
  ).slice(0, 8);

  if (keys.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        Empty list
      </Typography>
    );
  }

  return (
    <Box>
      <Table size={dense ? "small" : "medium"}>
        <TableHead>
          <TableRow>
            {keys.map((key) => (
              <TableCell key={key}>{key}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {visible.map((row, idx) => (
            <TableRow key={idx}>
              {keys.map((key) => (
                <TableCell key={key} sx={{ verticalAlign: "top" }}>
                  <StructuredDataViewInner
                    value={row[key]}
                    depth={depth + 1}
                    maxDepth={maxDepth}
                    dense={dense}
                    compact
                  />
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {rows.length > maxRows ? (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
          Showing {maxRows} of {rows.length}
        </Typography>
      ) : null}
    </Box>
  );
}

function StructuredDataViewInner({
  value,
  depth,
  maxDepth,
  dense,
  compact = false,
  emptyLabel = "-",
}: {
  value: unknown;
  depth: number;
  maxDepth: number;
  dense: boolean;
  compact?: boolean;
  emptyLabel?: string;
}): ReactNode {
  if (value == null || value === "") {
    return (
      <Typography variant="body2" color="text.secondary">
        {emptyLabel}
      </Typography>
    );
  }

  if (typeof value !== "object") {
    return (
      <Typography variant="body2" sx={compact ? { maxWidth: 280 } : undefined} noWrap={compact}>
        {formatScalar(value)}
      </Typography>
    );
  }

  if (depth >= maxDepth) {
    const summary = Array.isArray(value)
      ? `List (${value.length})`
      : `Object (${Object.keys(value as object).length} fields)`;
    return (
      <Chip size="small" label={summary} variant="outlined" />
    );
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return (
        <Typography variant="body2" color="text.secondary">
          Empty list
        </Typography>
      );
    }
    if (value.every((item) => item == null || typeof item !== "object")) {
      return <PrimitiveList items={value} />;
    }
    if (value.every((item) => isPlainObject(item))) {
      return (
        <ArrayOfObjectsTable
          rows={value as Record<string, unknown>[]}
          depth={depth}
          maxDepth={maxDepth}
          maxRows={25}
          dense={dense}
        />
      );
    }
    return (
      <Stack spacing={1}>
        {value.slice(0, 25).map((item, idx) => (
          <Box key={idx} sx={{ pl: 1, borderLeft: 2, borderColor: "divider" }}>
            <Typography variant="caption" color="text.secondary">
              Item {idx + 1}
            </Typography>
            <StructuredDataViewInner value={item} depth={depth + 1} maxDepth={maxDepth} dense={dense} />
          </Box>
        ))}
      </Stack>
    );
  }

  if (isPlainObject(value)) {
    if (compact) {
      const preview = Object.entries(value)
        .slice(0, 3)
        .map(([key, child]) => `${key}: ${formatScalar(typeof child === "object" ? "[...]" : child)}`)
        .join(", ");
      return (
        <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 280 }}>
          {preview || "-"}
        </Typography>
      );
    }
    return <ObjectTable value={value} depth={depth} maxDepth={maxDepth} dense={dense} />;
  }

  return (
    <Typography variant="body2">{formatScalar(value)}</Typography>
  );
}

export default function StructuredDataView({
  value,
  emptyLabel = "-",
  maxDepth = 3,
  maxRows = 25,
  dense = true,
}: StructuredDataViewProps) {
  void maxRows;
  return (
    <Box sx={{ overflow: "auto", maxWidth: "100%" }}>
      <StructuredDataViewInner
        value={value}
        depth={0}
        maxDepth={maxDepth}
        dense={dense}
        emptyLabel={emptyLabel}
      />
    </Box>
  );
}
