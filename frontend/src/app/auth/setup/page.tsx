"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import MenuItem from "@mui/material/MenuItem";
import Step from "@mui/material/Step";
import StepLabel from "@mui/material/StepLabel";
import Stepper from "@mui/material/Stepper";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useRouter } from "next/navigation";
import AuthLayout from "@/components/auth/AuthLayout";
import { ceApi } from "@/lib/ce-api";

const steps = ["Welcome", "Owner account", "LLM provider", "Done"];

const providers = ["anthropic", "openai", "gemini", "groq", "ollama"];

export default function AuthSetupPage() {
  const router = useRouter();
  const [activeStep, setActiveStep] = React.useState(0);
  const [fullName, setFullName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [provider, setProvider] = React.useState("anthropic");
  const [apiKey, setApiKey] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    void ceApi("/api/setup/wizard").then(async (response) => {
      if (!response.ok) return;
      const body = (await response.json()) as { complete?: boolean };
      if (body.complete) {
        router.replace("/dashboard");
      }
    });
  }, [router]);

  const postStep = async (step: number, payload: Record<string, unknown> = {}) => {
    const response = await ceApi(`/api/setup/step/${step}`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (response.status === 403) {
      router.replace("/dashboard");
      return false;
    }
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as { detail?: string };
      throw new Error(body.detail || `Setup step ${step} failed`);
    }
    return true;
  };

  const handleNext = async () => {
    setError(null);
    if (activeStep === 0) {
      setBusy(true);
      try {
        const ok = await postStep(0);
        if (!ok) return;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Setup failed");
        setBusy(false);
        return;
      }
      setBusy(false);
    }
    if (activeStep === 1) {
      if (password !== confirmPassword) {
        setError("Passwords do not match");
        return;
      }
      setBusy(true);
      try {
        const ok = await postStep(1, { full_name: fullName, email, password });
        if (!ok) return;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Account setup failed");
        setBusy(false);
        return;
      }
      setBusy(false);
    }
    if (activeStep === 2) {
      setBusy(true);
      try {
        const ok = await postStep(2, { provider, api_key: apiKey.trim() });
        if (!ok) return;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Provider setup failed");
        setBusy(false);
        return;
      }
      setBusy(false);
    }
    if (activeStep === 3) {
      setBusy(true);
      try {
        const ok = await postStep(3);
        if (!ok) return;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not finalize setup");
        setBusy(false);
        return;
      }
      setBusy(false);
      router.push("/dashboard");
      return;
    }
    setActiveStep((prev) => prev + 1);
  };

  return (
    <AuthLayout>
      <Typography variant="h5" gutterBottom>
        Set up Keprix
      </Typography>
      <Stepper activeStep={activeStep} alternativeLabel sx={{ my: 3 }}>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>
      {error ? (
        <Typography color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      ) : null}
      {activeStep === 0 && (
        <Typography variant="body2" color="text.secondary">
          You are setting up your Keprix instance. This creates the owner (developer) account.
        </Typography>
      )}
      {activeStep === 1 && (
        <Box sx={{ display: "grid", gap: 2 }}>
          <TextField label="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
          <TextField label="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <TextField label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <TextField
            label="Confirm password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
        </Box>
      )}
      {activeStep === 2 && (
        <Box sx={{ display: "grid", gap: 2 }}>
          <TextField select label="Primary LLM" value={provider} onChange={(e) => setProvider(e.target.value)}>
            {providers.map((item) => (
              <MenuItem key={item} value={item}>
                {item}
              </MenuItem>
            ))}
          </TextField>
          <TextField label="API key" type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
        </Box>
      )}
      {activeStep === 3 && (
        <Typography variant="body2" color="text.secondary">
          Setup complete. Developer identity is stored under ~/.keprix/identity/.
        </Typography>
      )}
      <Box sx={{ display: "flex", justifyContent: "space-between", mt: 4 }}>
        <Button disabled={activeStep === 0 || busy} onClick={() => setActiveStep((prev) => prev - 1)}>
          Back
        </Button>
        <Button variant="contained" disabled={busy} onClick={handleNext}>
          {activeStep === steps.length - 1 ? "Open dashboard" : "Continue"}
        </Button>
      </Box>
    </AuthLayout>
  );
}
