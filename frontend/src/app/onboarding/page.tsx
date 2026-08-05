"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Step from "@mui/material/Step";
import StepLabel from "@mui/material/StepLabel";
import Stepper from "@mui/material/Stepper";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useRouter } from "next/navigation";
import * as React from "react";
import { ceApi } from "@/lib/ce-api";

const steps = [
  "Welcome",
  "Admin password",
  "LLM provider",
  "Messaging channel",
  "Test setup",
  "Done",
];

export default function OnboardingPage() {
  const router = useRouter();
  const [activeStep, setActiveStep] = React.useState(0);
  const [adminPassword, setAdminPassword] = React.useState("");
  const [apiKey, setApiKey] = React.useState("");
  const [telegramToken, setTelegramToken] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const handleNext = async () => {
    setError(null);

    if (activeStep === 1 && adminPassword.trim()) {
      setBusy(true);
      try {
        const response = await ceApi("/api/auth/register", {
          method: "POST",
          body: JSON.stringify({ username: "admin", password: adminPassword }),
        });
        if (!response.ok && response.status !== 403) {
          const payload = await response.json().catch(() => ({}));
          throw new Error((payload as { detail?: string }).detail || "Password setup failed");
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Password setup failed");
        setBusy(false);
        return;
      }
      setBusy(false);
    }

    if (activeStep === 2 && apiKey.trim()) {
      setBusy(true);
      try {
        const response = await ceApi("/api/setup/secure-input", {
          method: "POST",
          body: JSON.stringify({
            service_id: "openai",
            fields: { api_key: apiKey.trim() },
          }),
        });
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error((payload as { detail?: string }).detail || "Provider setup failed");
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Provider setup failed");
        setBusy(false);
        return;
      }
      setBusy(false);
    }

    if (activeStep === 3 && telegramToken.trim()) {
      setBusy(true);
      try {
        const response = await ceApi("/api/setup/secure-input", {
          method: "POST",
          body: JSON.stringify({
            service_id: "telegram",
            fields: { bot_token: telegramToken.trim() },
          }),
        });
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error((payload as { detail?: string }).detail || "Channel setup failed");
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Channel setup failed");
        setBusy(false);
        return;
      }
      setBusy(false);
    }

    if (activeStep === 4) {
      setBusy(true);
      try {
        const response = await ceApi("/api/setup/test", {
          method: "POST",
          body: JSON.stringify({ service_id: "openai" }),
        });
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}));
          throw new Error((payload as { detail?: string }).detail || "Setup test failed");
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Setup test failed");
        setBusy(false);
        return;
      }
      setBusy(false);
    }

    if (activeStep >= steps.length - 1) {
      router.push("/home");
      return;
    }
    setActiveStep((prev) => prev + 1);
  };

  const handleBack = () => setActiveStep((prev) => Math.max(prev - 1, 0));

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        p: 2,
        bgcolor: "background.default",
      }}
    >
      <Card sx={{ width: "100%", maxWidth: 640 }}>
        <CardContent sx={{ p: 4 }}>
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

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {activeStep === 0 && (
            <Typography variant="body1" color="text.secondary">
              Welcome to Keprix. This wizard helps you configure your local AI workspace.
            </Typography>
          )}
          {activeStep === 1 && (
            <TextField
              label="Admin password"
              type="password"
              fullWidth
              value={adminPassword}
              onChange={(e) => setAdminPassword(e.target.value)}
              helperText="Skip if already set via environment."
            />
          )}
          {activeStep === 2 && (
            <TextField
              label="LLM provider API key"
              type="password"
              fullWidth
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              helperText="OpenAI, Anthropic, or another supported provider. Skip if configured."
            />
          )}
          {activeStep === 3 && (
            <TextField
              label="Telegram bot token (optional)"
              fullWidth
              value={telegramToken}
              onChange={(e) => setTelegramToken(e.target.value)}
            />
          )}
          {activeStep === 4 && (
            <Typography variant="body1" color="text.secondary">
              Send a test message to verify your provider and channel configuration. Skip if not configured yet.
            </Typography>
          )}
          {activeStep === 5 && (
            <Typography variant="body1" color="text.secondary">
              Setup complete. Open the workspace home to start working.
            </Typography>
          )}

          <Box sx={{ display: "flex", justifyContent: "space-between", mt: 4 }}>
            <Button disabled={activeStep === 0 || busy} onClick={handleBack}>
              Back
            </Button>
            <Button variant="contained" disabled={busy} onClick={handleNext}>
              {busy ? "Saving..." : activeStep === steps.length - 1 ? "Go to workspace" : "Continue"}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
