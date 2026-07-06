"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Step from "@mui/material/Step";
import StepLabel from "@mui/material/StepLabel";
import Stepper from "@mui/material/Stepper";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import * as React from "react";
import { useRouter } from "next/navigation";
import {
  installAgentAppFromPath,
  installAgentAppUpload,
  validateAgentAppUpload,
  type AgentAppDetail,
} from "@/lib/agent-apps-api";
import { ceApi } from "@/lib/ce-api";

const STEPS = ["Choose source", "Validate", "Confirm", "Install"];

type Props = {
  allowPathInstall?: boolean;
};

export default function AgentAppInstallWizard({ allowPathInstall = false }: Props) {
  const router = useRouter();
  const [step, setStep] = React.useState(0);
  const [file, setFile] = React.useState<File | null>(null);
  const [path, setPath] = React.useState("");
  const [usePath, setUsePath] = React.useState(false);
  const [manifest, setManifest] = React.useState<AgentAppDetail | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const onPickFile = async (picked: File | null) => {
    setFile(picked);
    setManifest(null);
    setError(null);
    if (!picked) {
      setStep(0);
      return;
    }
    setUsePath(false);
    setStep(1);
    setBusy(true);
    try {
      const validation = await validateAgentAppUpload(picked);
      if (!validation.valid || !validation.manifest) {
        setError(validation.error || "Bundle validation failed");
        setStep(0);
        return;
      }
      setManifest(validation.manifest);
      setStep(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Validation failed");
      setStep(0);
    } finally {
      setBusy(false);
    }
  };

  const onValidatePath = async () => {
    if (!path.trim()) {
      setError("Enter a path to the agent app folder");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await ceApi("/api/agent-apps/validate", {
        method: "POST",
        body: JSON.stringify({ path: path.trim() }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.valid) {
        setError(
          typeof payload.detail === "string"
            ? payload.detail
            : payload.error || "Path validation failed",
        );
        return;
      }
      setManifest(payload.manifest);
      setUsePath(true);
      setFile(null);
      setStep(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Path validation failed");
    } finally {
      setBusy(false);
    }
  };

  const onInstall = async () => {
    setBusy(true);
    setError(null);
    setStep(3);
    try {
      const result = usePath
        ? await installAgentAppFromPath(path.trim())
        : file
          ? await installAgentAppUpload(file)
          : null;
      if (!result) {
        throw new Error("No install source selected");
      }
      router.push(result.redirect || `/agent-apps/${result.app.name}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Install failed");
      setStep(2);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ display: "grid", gap: 2 }}>
      <Stepper activeStep={step} alternativeLabel>
        {STEPS.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {error ? <Alert severity="error">{error}</Alert> : null}

      {step === 0 ? (
        <Stack spacing={2}>
          <Box
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              const dropped = event.dataTransfer.files?.[0];
              if (dropped) {
                void onPickFile(dropped);
              }
            }}
            sx={{
              border: "2px dashed",
              borderColor: "divider",
              borderRadius: 2,
              p: 4,
              textAlign: "center",
              cursor: "pointer",
            }}
            onClick={() => inputRef.current?.click()}
          >
            <CloudUploadIcon sx={{ fontSize: 40, color: "text.secondary", mb: 1 }} />
            <Typography variant="subtitle1">Drop a deployment bundle (.zip)</Typography>
            <Typography variant="body2" color="text.secondary">
              or click to browse (max 25 MB)
            </Typography>
            <input
              ref={inputRef}
              type="file"
              accept=".zip,application/zip"
              hidden
              onChange={(event) => void onPickFile(event.target.files?.[0] ?? null)}
            />
          </Box>

          {allowPathInstall ? (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Or install from local path (dev/admin)
              </Typography>
              <Stack direction="row" spacing={1}>
                <TextField
                  size="small"
                  fullWidth
                  label="App folder path"
                  value={path}
                  onChange={(event) => setPath(event.target.value)}
                />
                <Button variant="outlined" onClick={() => void onValidatePath()} disabled={busy}>
                  Validate
                </Button>
              </Stack>
            </Box>
          ) : null}
        </Stack>
      ) : null}

      {step >= 2 && manifest ? (
        <Box sx={{ border: "1px solid", borderColor: "divider", borderRadius: 2, p: 2 }}>
          <Typography variant="h6" gutterBottom>
            {manifest.display_name || manifest.name}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {manifest.description}
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
            <Chip label={`v${manifest.version}`} size="small" />
            <Chip label={manifest.runtime || "python"} size="small" variant="outlined" />
            {manifest.category ? (
              <Chip label={manifest.category} size="small" variant="outlined" />
            ) : null}
          </Stack>
          {manifest.required_env?.length ? (
            <Typography variant="body2" sx={{ mb: 0.5 }}>
              Required secrets: {manifest.required_env.join(", ")}
            </Typography>
          ) : null}
          {manifest.required_permissions?.length ? (
            <Typography variant="body2">
              Required permissions: {manifest.required_permissions.join(", ")}
            </Typography>
          ) : null}
        </Box>
      ) : null}

      {step === 2 ? (
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" onClick={() => setStep(0)} disabled={busy}>
            Back
          </Button>
          <Button variant="contained" onClick={() => void onInstall()} disabled={busy}>
            {busy ? "Installing..." : "Install app"}
          </Button>
        </Stack>
      ) : null}

      {step === 1 && busy ? (
        <Typography variant="body2" color="text.secondary">
          Validating bundle...
        </Typography>
      ) : null}
    </Box>
  );
}
