"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import Link from "@mui/material/Link";
import Popover from "@mui/material/Popover";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import KeyIcon from "@mui/icons-material/Key";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import * as React from "react";
import {
  saveCompaniesHouseSettings,
  type CompaniesHouseStatus,
} from "@/lib/companies-house-api";

type Props = {
  status?: CompaniesHouseStatus | null;
  onSaved?: () => void | Promise<void>;
  /** Force open the editor (e.g. settings page). */
  forceOpen?: boolean;
};

export default function CompaniesHouseKeyForm({ status, onSaved, forceOpen }: Props) {
  const configured = Boolean(status?.configured);
  const [anchor, setAnchor] = React.useState<HTMLElement | null>(null);
  const [apiKey, setApiKey] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [message, setMessage] = React.useState<string | null>(null);
  const [severity, setSeverity] = React.useState<"success" | "error" | "info">("info");

  const onSave = async () => {
    if (!apiKey.trim()) {
      setSeverity("error");
      setMessage("Paste an API key from the Companies House Developer Hub.");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      await saveCompaniesHouseSettings({ api_key: apiKey.trim(), enabled: true });
      setApiKey("");
      setSeverity("success");
      setMessage("API key saved.");
      await onSaved?.();
      if (!forceOpen) {
        setAnchor(null);
      }
    } catch (err) {
      setSeverity("error");
      setMessage(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const editor = (
    <Stack spacing={1.5} sx={{ p: forceOpen ? 0 : 2, width: forceOpen ? "100%" : 360, maxWidth: "100%" }}>
      {message ? (
        <Alert severity={severity} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}
      {!configured ? (
        <Typography variant="body2" color="text.secondary">
          Add a Rest API key from the{" "}
          <Link href="https://developer.company-information.service.gov.uk/" target="_blank" rel="noreferrer">
            Developer Hub
          </Link>
          . Stored in server env only.
        </Typography>
      ) : (
        <Typography variant="body2" color="text.secondary">
          Rotate the key without editing `.env`. Current key stays set until you save a new one.
        </Typography>
      )}
      <TextField
        type="password"
        size="small"
        label="API key"
        value={apiKey}
        onChange={(e) => setApiKey(e.target.value)}
        autoComplete="off"
        fullWidth
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <KeyIcon fontSize="small" color="action" />
            </InputAdornment>
          ),
        }}
      />
      <Stack direction="row" spacing={1} justifyContent="space-between" alignItems="center">
        <Link
          href="https://developer.company-information.service.gov.uk/"
          target="_blank"
          rel="noreferrer"
          variant="caption"
          sx={{ display: "inline-flex", alignItems: "center", gap: 0.5 }}
        >
          Developer Hub <OpenInNewIcon sx={{ fontSize: 12 }} />
        </Link>
        <Button size="small" variant="contained" onClick={onSave} disabled={busy}>
          Save
        </Button>
      </Stack>
    </Stack>
  );

  if (forceOpen) {
    return <Box sx={{ mb: 2, maxWidth: 480 }}>{editor}</Box>;
  }

  return (
    <>
      <Tooltip title={configured ? "API key set. Click to rotate." : "Add Companies House API key"}>
        <IconButton
          size="small"
          color={configured ? "default" : "warning"}
          onClick={(e) => setAnchor(e.currentTarget)}
          aria-label="Companies House API key"
        >
          <KeyIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Popover
        open={Boolean(anchor)}
        anchorEl={anchor}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
      >
        {editor}
      </Popover>
    </>
  );
}
