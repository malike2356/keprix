"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import DashboardCard from "@/components/cards/DashboardCard";

type TestRunPanelProps = {
  testCommand?: string | null;
  lintCommand?: string | null;
  testSummary?: string;
  lintSummary?: string;
  attempts?: number;
  ok?: boolean;
  loading?: boolean;
  onRun?: () => void;
};

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <Typography variant="overline" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
      {children}
    </Typography>
  );
}

export function TestRunPanel({
  testCommand = null,
  lintCommand = null,
  testSummary = "",
  lintSummary = "",
  attempts = 0,
  ok = false,
  loading = false,
  onRun,
}: TestRunPanelProps) {
  const statusLabel = ok ? "Last run passed" : attempts ? `Attempts: ${attempts}` : "No run yet";

  return (
    <DashboardCard
      title="Lint and tests"
      subtitle={statusLabel}
      action={
        onRun ? (
          <Button size="small" variant="outlined" onClick={onRun} disabled={loading}>
            {loading ? "Running..." : "Run loop"}
          </Button>
        ) : null
      }
    >
      <Stack spacing={2}>
        <Box>
          <SectionLabel>Detected commands</SectionLabel>
          <Typography variant="caption" sx={{ fontFamily: "monospace", display: "block" }}>
            Test: {testCommand || "none"}
          </Typography>
          <Typography variant="caption" sx={{ fontFamily: "monospace", display: "block" }}>
            Lint: {lintCommand || "none"}
          </Typography>
        </Box>

        {ok ? <Chip size="small" color="success" label="Passed" variant="outlined" /> : null}

        {lintSummary ? (
          <Box>
            <SectionLabel>Lint output</SectionLabel>
            <Box component="pre" sx={{ m: 0, p: 1.5, maxHeight: 160, overflow: "auto", borderRadius: 1, bgcolor: "action.hover", fontSize: "0.75rem" }}>
              {lintSummary}
            </Box>
          </Box>
        ) : null}

        {testSummary ? (
          <Box>
            <SectionLabel>Test output</SectionLabel>
            <Box component="pre" sx={{ m: 0, p: 1.5, maxHeight: 180, overflow: "auto", borderRadius: 1, bgcolor: "action.hover", fontSize: "0.75rem" }}>
              {testSummary}
            </Box>
          </Box>
        ) : null}

        {!testSummary && !lintSummary && !loading ? (
          <Typography variant="body2" color="text.secondary">
            Run a coding session to execute lint and test loops against the repo.
          </Typography>
        ) : null}
      </Stack>
    </DashboardCard>
  );
}
