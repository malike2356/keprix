"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";

type ChatErrorBannerProps = {
  message: string;
  onRetry?: () => void;
  onDismiss?: () => void;
};

export default function ChatErrorBanner({ message, onRetry, onDismiss }: ChatErrorBannerProps) {
  return (
    <Alert
      severity="error"
      sx={{ mx: { xs: 1, md: 3 }, mt: 2 }}
      action={
        onRetry ? (
          <Button color="inherit" size="small" onClick={onRetry}>
            Retry
          </Button>
        ) : onDismiss ? (
          <Button color="inherit" size="small" onClick={onDismiss}>
            Dismiss
          </Button>
        ) : undefined
      }
    >
      {message}
    </Alert>
  );
}
