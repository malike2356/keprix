"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import DashboardCard from "@/components/cards/DashboardCard";

type GitCommitPanelProps = {
  diff: string;
  proposedMessage: string;
  stagedFiles: string[];
  needsApproval?: boolean;
  commitHash?: string | null;
  error?: string | null;
  onStage?: () => void;
  onCommit?: () => void;
  onRevert?: () => void;
};

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <Typography variant="overline" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
      {children}
    </Typography>
  );
}

export function GitCommitPanel({
  diff,
  proposedMessage,
  stagedFiles,
  needsApproval = true,
  commitHash = null,
  error = null,
  onStage,
  onCommit,
  onRevert,
}: GitCommitPanelProps) {
  return (
    <DashboardCard
      title="Git commit review"
      subtitle={needsApproval ? "Approve before Keprix commits or reverts changes." : "Ready to commit."}
      action={commitHash ? <Chip size="small" label={commitHash.slice(0, 8)} variant="outlined" /> : null}
    >
      {error ? (
        <Typography variant="body2" color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      ) : null}

      <Stack spacing={2}>
        <Box>
          <SectionLabel>Proposed message</SectionLabel>
          <Box
            component="pre"
            sx={{
              m: 0,
              p: 1.5,
              borderRadius: 1,
              bgcolor: "action.hover",
              fontSize: "0.75rem",
              whiteSpace: "pre-wrap",
            }}
          >
            {proposedMessage || "No commit message proposed yet."}
          </Box>
        </Box>

        <Box>
          <SectionLabel>Staged files</SectionLabel>
          <Typography variant="caption" sx={{ fontFamily: "monospace", display: "block" }}>
            {stagedFiles.length ? stagedFiles.join(", ") : "None"}
          </Typography>
        </Box>

        <Box>
          <SectionLabel>Diff</SectionLabel>
          <Box
            component="pre"
            sx={{
              m: 0,
              p: 1.5,
              maxHeight: 320,
              overflow: "auto",
              borderRadius: 1,
              bgcolor: "action.hover",
              fontSize: "0.75rem",
            }}
          >
            {diff || "No diff yet. Run a coding session to generate proposed changes."}
          </Box>
        </Box>

        <Stack direction="row" spacing={1} flexWrap="wrap">
          {onStage ? (
            <Button size="small" variant="outlined" onClick={onStage}>
              Stage selected
            </Button>
          ) : null}
          {onCommit ? (
            <Button size="small" variant="contained" onClick={onCommit} disabled={needsApproval || !proposedMessage}>
              Approve commit
            </Button>
          ) : null}
          {onRevert ? (
            <Button size="small" variant="outlined" color="inherit" onClick={onRevert}>
              Revert Keprix changes
            </Button>
          ) : null}
        </Stack>
      </Stack>
    </DashboardCard>
  );
}
