"use client";

import * as React from "react";
import Alert from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";

type FeedbackState = { message: string; severity: "success" | "error" | "info" };

export function useSnackbar() {
  const [state, setState] = React.useState<FeedbackState | null>(null);

  const show = React.useCallback((message: string, severity: FeedbackState["severity"] = "success") => {
    setState({ message, severity });
  }, []);

  const close = React.useCallback(() => setState(null), []);

  return { state, show, close };
}

export function SnackbarFeedback({
  state,
  onClose,
}: {
  state: FeedbackState | null;
  onClose: () => void;
}) {
  return (
    <Snackbar
      open={Boolean(state)}
      autoHideDuration={3500}
      onClose={onClose}
      anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
    >
      <Alert onClose={onClose} severity={state?.severity ?? "info"} variant="filled" elevation={4}>
        {state?.message}
      </Alert>
    </Snackbar>
  );
}
