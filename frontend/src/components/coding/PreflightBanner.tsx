"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";

export type PreflightReport = {
  session_id: string;
  overall: "proceed" | "warn" | "block";
  tokens_saved_estimate: number;
  override_applied?: boolean;
  results: Array<{ gate: string; status: "pass" | "warn" | "block"; message: string }>;
};

export default function PreflightBanner({
  report,
  onOverride,
}: {
  report: PreflightReport | null;
  onOverride?: () => void;
}) {
  if (!report) return null;
  const severity = report.overall === "block" ? "error" : report.overall === "warn" ? "warning" : "success";
  return (
    <Alert
      severity={severity}
      action={
        report.overall === "block" && onOverride ? (
          <Button color="inherit" size="small" onClick={onOverride}>
            Proceed anyway
          </Button>
        ) : null
      }
    >
      <Box sx={{ display: "grid", gap: 1 }}>
        <Typography variant="body2">
          Preflight: {report.overall}. Estimated tokens saved: {report.tokens_saved_estimate}
          {report.override_applied ? " (override applied)" : ""}
        </Typography>
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          {report.results.map((result) => (
            <Chip key={result.gate} size="small" label={`${result.gate}: ${result.status}`} />
          ))}
        </Box>
      </Box>
    </Alert>
  );
}
