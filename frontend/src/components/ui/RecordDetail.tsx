"use client";

import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";
import ErrorState from "@/components/ui/ErrorState";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonDetailPanel } from "@/components/ui/loading";
import StatusPill from "@/components/ui/StatusPill";
import type { StatusKey } from "@/theme/tokens/status";

export type RecordField = {
  label: string;
  value: ReactNode;
};

type RecordDetailProps = {
  title: string;
  subtitle?: string;
  status?: StatusKey;
  fields: RecordField[];
  actions?: ReactNode;
  loading?: boolean;
  error?: string;
  empty?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
};

export default function RecordDetail({
  title,
  subtitle,
  status,
  fields,
  actions,
  loading = false,
  error,
  empty = false,
  emptyTitle = "No record selected",
  emptyDescription = "Choose a record from the list to view details.",
}: RecordDetailProps) {
  if (loading) {
    return <SkeletonDetailPanel />;
  }
  if (error) {
    return <ErrorState title="Could not load record" message={error} />;
  }
  if (empty) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <Box sx={{ display: "grid", gap: 2 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, alignItems: "flex-start" }}>
        <Box>
          <Typography variant="h5" fontWeight={700}>{title}</Typography>
          {subtitle ? (
            <Typography variant="body2" color="text.secondary">{subtitle}</Typography>
          ) : null}
        </Box>
        {status ? <StatusPill status={status} /> : null}
      </Box>
      <Divider />
      <Box sx={{ display: "grid", gap: 1.25 }}>
        {fields.map((field) => (
          <Box key={field.label}>
            <Typography variant="caption" color="text.secondary">{field.label}</Typography>
            <Typography variant="body2">{field.value}</Typography>
          </Box>
        ))}
      </Box>
      {actions ? <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>{actions}</Box> : null}
    </Box>
  );
}
