"use client";

import DataTable, { type DataTableColumn } from "@/components/ui/DataTable";

type DatasetPreviewProps<T extends Record<string, unknown>> = {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  loading?: boolean;
  emptyMessage?: string;
};

export default function DatasetPreview<T extends Record<string, unknown>>(props: DatasetPreviewProps<T>) {
  return (
    <DataTable
      {...props}
      emptyMessage={props.emptyMessage || "No dataset rows to preview."}
    />
  );
}
