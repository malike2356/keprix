"use client";

import Chip from "@mui/material/Chip";
import DataTable, { type DataTableColumn } from "@/components/ui/DataTable";
import type { StatusKey } from "@/theme/tokens/status";
import StatusPill from "@/components/ui/StatusPill";

export type VariableRow = {
  id: string;
  name: string;
  type: string;
  label?: string;
  missingPct?: number;
  status?: StatusKey;
};

const columns: DataTableColumn<VariableRow>[] = [
  { id: "name", label: "Variable", render: (row) => row.name },
  { id: "type", label: "Type", render: (row) => row.type },
  { id: "label", label: "Label", render: (row) => row.label || "-" },
  {
    id: "missing",
    label: "Missing %",
    render: (row) => (row.missingPct !== undefined ? `${row.missingPct}%` : "-"),
  },
  {
    id: "status",
    label: "Status",
    render: (row) => (row.status ? <StatusPill status={row.status} /> : <Chip size="small" label="Ready" />),
  },
];

type VariableTableProps = {
  rows: VariableRow[];
  loading?: boolean;
  onRowClick?: (row: VariableRow) => void;
};

export default function VariableTable({ rows, loading = false, onRowClick }: VariableTableProps) {
  return (
    <DataTable
      columns={columns}
      rows={rows}
      rowKey={(row) => row.id}
      loading={loading}
      emptyMessage="No variables defined for this dataset."
      onRowClick={onRowClick}
    />
  );
}
