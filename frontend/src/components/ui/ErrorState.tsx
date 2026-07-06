"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import type { ReactNode } from "react";

type ErrorStateProps = {
  title?: string;
  message: string;
  code?: string;
  icon?: ReactNode;
  retryLabel?: string;
  onRetry?: () => void;
};

export default function ErrorState({
  title = "Something went wrong",
  message,
  code,
  icon,
  retryLabel = "Try again",
  onRetry,
}: ErrorStateProps) {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textAlign: "center",
        py: 6,
        px: 3,
        border: 1,
        borderColor: "error.light",
        borderRadius: 1,
        bgcolor: "background.paper",
      }}
    >
      <Box sx={{ mb: 2, color: "error.main" }}>
        {icon || <ErrorOutlineIcon sx={{ fontSize: 48 }} />}
      </Box>
      <Typography variant="h6" gutterBottom>
        {title}
      </Typography>
      <Alert severity="error" sx={{ mb: 2, maxWidth: 480, width: "100%" }}>
        {message}
      </Alert>
      {code && (
        <Typography variant="caption" color="text.secondary" sx={{ mb: 2 }}>
          Code: {code}
        </Typography>
      )}
      {onRetry && (
        <Button variant="outlined" color="error" onClick={onRetry}>
          {retryLabel}
        </Button>
      )}
    </Box>
  );
}
