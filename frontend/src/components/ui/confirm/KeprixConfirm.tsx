"use client";

import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";

export type KeprixConfirmOptions = {
  title: string;
  description?: React.ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  destructive?: boolean;
  requireTypedMatch?: string;
  typedMatchLabel?: string;
};

type ConfirmRequest = {
  options: KeprixConfirmOptions;
  resolve: (confirmed: boolean) => void;
};

const queue: ConfirmRequest[] = [];
const listeners = new Set<() => void>();

function notifyHost() {
  listeners.forEach((listener) => listener());
}

export function keprixConfirm(options: KeprixConfirmOptions): Promise<boolean> {
  return new Promise((resolve) => {
    queue.push({ options, resolve });
    notifyHost();
  });
}

type TypeToConfirmFieldProps = {
  match: string;
  label?: string;
  value: string;
  onChange: (value: string) => void;
};

export function TypeToConfirmField({ match, label, value, onChange }: TypeToConfirmFieldProps) {
  return (
    <TextField
      autoFocus
      fullWidth
      label={label || `Type ${match} to confirm`}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      helperText={`Enter "${match}" exactly.`}
      error={Boolean(value) && value !== match}
      autoComplete="off"
    />
  );
}

type HoldToConfirmButtonProps = {
  children: React.ReactNode;
  onConfirm: () => void;
  disabled?: boolean;
  color?: "error" | "warning" | "primary";
  holdMs?: number;
};

export function HoldToConfirmButton({
  children,
  onConfirm,
  disabled = false,
  color = "error",
  holdMs = 300,
}: HoldToConfirmButtonProps) {
  const timer = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const [holding, setHolding] = React.useState(false);

  const cancelHold = React.useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    setHolding(false);
  }, []);

  const startHold = () => {
    if (disabled || timer.current) return;
    setHolding(true);
    timer.current = setTimeout(() => {
      timer.current = null;
      setHolding(false);
      onConfirm();
    }, holdMs);
  };

  React.useEffect(() => cancelHold, [cancelHold]);

  return (
    <Button
      variant="contained"
      color={color}
      disabled={disabled}
      onPointerDown={startHold}
      onPointerUp={cancelHold}
      onPointerLeave={cancelHold}
      onPointerCancel={cancelHold}
      onKeyDown={(event) => {
        if (event.key === " " || event.key === "Enter") startHold();
      }}
      onKeyUp={(event) => {
        if (event.key === " " || event.key === "Enter") cancelHold();
      }}
    >
      {holding ? "Keep holding..." : children}
    </Button>
  );
}

export function KeprixConfirmHost() {
  const [request, setRequest] = React.useState<ConfirmRequest | null>(null);
  const [typedValue, setTypedValue] = React.useState("");

  const takeNext = React.useCallback(() => {
    setRequest((current) => current || queue.shift() || null);
  }, []);

  React.useEffect(() => {
    listeners.add(takeNext);
    takeNext();
    return () => {
      listeners.delete(takeNext);
    };
  }, [takeNext]);

  React.useEffect(() => {
    setTypedValue("");
  }, [request]);

  const finish = (confirmed: boolean) => {
    if (!request) return;
    request.resolve(confirmed);
    setRequest(null);
    window.setTimeout(takeNext, 0);
  };

  const options = request?.options;
  const typedMatchSatisfied = !options?.requireTypedMatch || typedValue === options.requireTypedMatch;

  return (
    <Dialog
      open={Boolean(request)}
      onClose={(_, reason) => {
        if (reason !== "backdropClick") finish(false);
      }}
      maxWidth="sm"
      fullWidth
      aria-labelledby="keprix-confirm-title"
    >
      <DialogTitle id="keprix-confirm-title">
        <Stack direction="row" spacing={1.25} alignItems="center">
          {options?.destructive ? <WarningAmberIcon color="error" /> : null}
          <Typography component="span" variant="h6">{options?.title}</Typography>
        </Stack>
      </DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 2 }}>
        {options?.description ? <DialogContentText component="div">{options.description}</DialogContentText> : null}
        {options?.requireTypedMatch ? (
          <TypeToConfirmField
            match={options.requireTypedMatch}
            label={options.typedMatchLabel}
            value={typedValue}
            onChange={setTypedValue}
          />
        ) : null}
      </DialogContent>
      <DialogActions>
        <Button onClick={() => finish(false)}>{options?.cancelLabel || "Cancel"}</Button>
        <Button
          variant="contained"
          color={options?.destructive ? "error" : "primary"}
          disabled={!typedMatchSatisfied}
          onClick={() => finish(true)}
        >
          {options?.confirmLabel}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
