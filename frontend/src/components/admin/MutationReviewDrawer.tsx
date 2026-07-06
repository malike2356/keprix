"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import CloseIcon from "@mui/icons-material/Close";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import useSWR from "swr";
import CodeBlock from "@/components/workspace/blocks/CodeBlock";
import { SnackbarFeedback, useSnackbar } from "@/components/ui/SnackbarFeedback";
import { fetchMutationCode } from "@/lib/admin-pages-api";
import { approveMutation as approvePipelineMutation, rejectMutation as rejectPipelineMutation } from "@/lib/mutation-api";
import { approveMutation, rejectMutation } from "@/lib/workspace-api";

type MutationReviewDrawerProps = {
  mutationId: string | null;
  toolName: string;
  status: string;
  open: boolean;
  onClose: () => void;
  onResolved: () => void;
};

export default function MutationReviewDrawer({
  mutationId,
  toolName,
  status,
  open,
  onClose,
  onResolved,
}: MutationReviewDrawerProps) {
  const { state, show, close } = useSnackbar();
  const [busy, setBusy] = React.useState(false);

  const { data: codePayload, isLoading } = useSWR(
    mutationId && open ? `mutation-code-${mutationId}` : null,
    () => fetchMutationCode(mutationId!),
  );

  const code = codePayload?.source_code || "";
  const isStaged = status === "staged" || status === "pending";

  const handleCopy = async () => {
    if (!code) return;
    try {
      await navigator.clipboard.writeText(code);
      show("Code copied");
    } catch {
      show("Could not copy code", "error");
    }
  };

  const handleApprove = async () => {
    if (!mutationId) return;
    setBusy(true);
    try {
      try {
        await approveMutation(mutationId);
      } catch {
        await approvePipelineMutation(mutationId, "tool");
      }
      show("Mutation approved");
      onResolved();
      onClose();
    } catch (err) {
      show(err instanceof Error ? err.message : "Approve failed", "error");
    } finally {
      setBusy(false);
    }
  };

  const handleReject = async () => {
    if (!mutationId) return;
    setBusy(true);
    try {
      try {
        await rejectMutation(mutationId, "Rejected from admin review");
      } catch {
        await rejectPipelineMutation(mutationId, "tool", "Rejected from admin review");
      }
      show("Mutation rejected");
      onResolved();
      onClose();
    } catch (err) {
      show(err instanceof Error ? err.message : "Reject failed", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: "100%", sm: 520 } } }}>
        <Box sx={{ p: 3, display: "flex", flexDirection: "column", height: "100%" }}>
          <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 1 }}>
            <Box>
              <Typography variant="h6">{toolName}</Typography>
              <Chip
                size="small"
                label={status}
                color={status === "approved" ? "success" : status === "rejected" ? "error" : "warning"}
                sx={{ mt: 1 }}
              />
            </Box>
            <IconButton onClick={onClose} aria-label="Close">
              <CloseIcon />
            </IconButton>
          </Box>

          <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 2 }}>
            <Button size="small" startIcon={<ContentCopyIcon />} onClick={() => void handleCopy()} disabled={!code}>
              Copy code
            </Button>
          </Box>

          <Box sx={{ flex: 1, overflow: "auto", mt: 1 }}>
            {isLoading ? (
              <Typography variant="body2" color="text.secondary">
                Loading source code...
              </Typography>
            ) : (
              <CodeBlock language="python" content={code || "# No source code available"} />
            )}
          </Box>

          {isStaged ? (
            <Box sx={{ display: "flex", gap: 1, mt: 2 }}>
              <Button variant="outlined" color="error" fullWidth onClick={() => void handleReject()} disabled={busy}>
                Reject
              </Button>
              <Button variant="contained" color="success" fullWidth onClick={() => void handleApprove()} disabled={busy}>
                Approve
              </Button>
            </Box>
          ) : null}
        </Box>
      </Drawer>
      <SnackbarFeedback state={state} onClose={close} />
    </>
  );
}
