"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import CodeBlock from "@/components/workspace/blocks/CodeBlock";
import MutationApprovalPanel from "@/components/mutation/MutationApprovalPanel";
import MutationQualityBadge from "@/components/mutation/MutationQualityBadge";
import type { MutationRecord } from "@/lib/mutation-api";
import { formatTimeAgo } from "@/lib/time-ago";

type GeneratedToolCardProps = {
  record: MutationRecord;
  sourcePreview?: string;
  qualitySamples?: number[];
  onAction?: () => void;
  showActions?: boolean;
};

export default function GeneratedToolCard({
  record,
  sourcePreview,
  qualitySamples = [],
  onAction,
  showActions = true,
}: GeneratedToolCardProps) {
  const preview = sourcePreview?.split("\n").slice(0, 10).join("\n") ?? "";
  const sandboxPassed = record.metadata?.sandbox_passed;
  const promoted = Boolean(record.metadata?.promoted);

  return (
    <Box sx={{ display: "grid", gap: 1.5 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, flexWrap: "wrap" }}>
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            {record.name}
            {promoted ? " *" : ""}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {record.description || "Generated tool"}
          </Typography>
        </Box>
        <MutationQualityBadge
          score={record.quality_score}
          useCount={record.use_count}
          status={record.status}
          samples={qualitySamples}
        />
      </Box>
      <Typography variant="caption" color="text.secondary">
        Last used: {record.last_used_at ? formatTimeAgo(record.last_used_at) : "never"} | Age:{" "}
        {formatTimeAgo(record.recorded_at)}
      </Typography>
      {sandboxPassed !== undefined ? (
        <Typography variant="body2">
          Sandbox: {sandboxPassed ? "passed" : "failed"}
        </Typography>
      ) : null}
      {preview ? <CodeBlock language="python" content={preview} /> : null}
      {showActions && record.status === "staged" ? (
        <MutationApprovalPanel mutationId={record.id} tier="tool" onApproved={onAction} onRejected={onAction} compact />
      ) : null}
      {showActions && record.status === "approved" ? (
        <Button size="small" variant="outlined" href={`/dashboard/mutation/${record.id}`}>
          View details
        </Button>
      ) : null}
    </Box>
  );
}
