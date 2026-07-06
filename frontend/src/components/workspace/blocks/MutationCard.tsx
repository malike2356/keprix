"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress"; // @loading-contract-ignore button submit spinners
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import * as React from "react";
import CodeBlock from "@/components/workspace/blocks/CodeBlock";
import {
  approveMutation,
  rejectMutation,
  type MessageBlock,
  type WorkspaceMessage,
} from "@/lib/workspace-api";

type MutationCardProps = {
  block: Extract<MessageBlock, { type: "mutation" }>;
  sessionId?: string;
  canApprove?: boolean;
  onStatusChange?: (
    status: "approved" | "rejected",
    retryMessage?: string,
    message?: WorkspaceMessage,
  ) => void;
};

export default function MutationCard({
  block,
  sessionId,
  canApprove = false,
  onStatusChange,
}: MutationCardProps) {
  const [tab, setTab] = React.useState(0);
  const [busy, setBusy] = React.useState<"approve" | "reject" | null>(null);
  const [status, setStatus] = React.useState(block.status);
  const [retryText, setRetryText] = React.useState<string | null>(null);

  const borderColor =
    status === "approved" ? "success.main" : status === "rejected" ? "text.disabled" : "warning.main";

  const onApprove = async () => {
    if (!block.id) return;
    setBusy("approve");
    try {
      const response = await approveMutation(block.id, sessionId);
      setStatus("approved");
      if (response.retry_message) {
        setRetryText(response.retry_message);
      }
      const persisted = response.message
        ? {
            id: response.message.id,
            role: response.message.role,
            content: response.message.content,
            createdAt: response.message.createdAt || new Date().toISOString(),
          }
        : undefined;
      onStatusChange?.("approved", response.retry_message, persisted);
    } finally {
      setBusy(null);
    }
  };

  const onReject = async () => {
    if (!block.id) return;
    setBusy("reject");
    try {
      await rejectMutation(block.id, "Rejected from workspace");
      setStatus("rejected");
      onStatusChange?.("rejected");
    } finally {
      setBusy(null);
    }
  };

  return (
    <Box
      sx={{
        border: 2,
        borderColor,
        borderRadius: 2,
        p: 2,
        bgcolor: "background.paper",
      }}
    >
      <Typography variant="overline" color="warning.main">
        Tool synthesis request
      </Typography>
      <Typography variant="subtitle1" sx={{ fontWeight: 700, mt: 0.5 }}>
        {block.toolName}
      </Typography>
      {block.approach ? (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          Approach: {block.approach}
        </Typography>
      ) : null}

      <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 1.5 }}>
        <Tab label="Code" />
        <Tab label="Skill YAML" />
        <Tab label="Sandbox Result" />
      </Tabs>

      {tab === 0 ? <CodeBlock language="python" content={block.code} /> : null}
      {tab === 1 ? <CodeBlock language="yaml" content={block.skillYaml} /> : null}
      {tab === 2 ? (
        <Box sx={{ display: "grid", gap: 1 }}>
          <Typography variant="body2">Exit code: {block.sandboxExitCode ?? 0}</Typography>
          <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
            Stdout: {block.sandboxResult || "(empty)"}
          </Typography>
          <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
            Stderr: {block.sandboxStderr || "(empty)"}
          </Typography>
        </Box>
      ) : null}

      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mt: 2, gap: 2 }}>
        {status === "approved" ? (
          <Typography variant="body2" color="success.main">
            {retryText || "Installed. Retrying your request..."}
          </Typography>
        ) : status === "rejected" ? (
          <Typography variant="body2" color="text.secondary">
            Tool discarded.
          </Typography>
        ) : canApprove ? (
          <>
            <Button
              variant="outlined"
              color="inherit"
              disabled={busy !== null}
              onClick={onReject}
              startIcon={busy === "reject" ? <CircularProgress size={16} /> : undefined}
            >
              Reject
            </Button>
            <Button
              variant="contained"
              color="success"
              disabled={busy !== null}
              onClick={onApprove}
              startIcon={busy === "approve" ? <CircularProgress size={16} /> : undefined}
            >
              Approve and install
            </Button>
          </>
        ) : (
          <Typography variant="body2" color="text.secondary">
            Pending owner approval
          </Typography>
        )}
      </Box>
    </Box>
  );
}
