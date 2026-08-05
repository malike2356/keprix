"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import RecoveryCodesDialog from "@/components/auth/RecoveryCodesDialog";
import StepUpOtpDialog from "@/components/auth/StepUpOtpDialog";
import {
  disableTotp,
  fetchAccountProfile,
  fetchAuthConfig,
  fetchTotpQrBlobUrl,
  generateRecoveryCodes,
  setupTotp,
  verifyTotp,
} from "@/lib/account-api";
import { useCESession } from "@/lib/ce-auth";

type SetupState = {
  secret: string;
  provisioningUri: string;
  qrUrl: string;
};

export default function TwoFactorSetupPanel() {
  const { refreshUser } = useCESession();
  const { data: profile, mutate } = useSWR("account-profile", fetchAccountProfile);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [setup, setSetup] = React.useState<SetupState | null>(null);
  const [confirmCode, setConfirmCode] = React.useState("");
  const [recoveryCodes, setRecoveryCodes] = React.useState<string[]>([]);
  const [recoveryOpen, setRecoveryOpen] = React.useState(false);
  const [disableOpen, setDisableOpen] = React.useState(false);
  const [regenerateOpen, setRegenerateOpen] = React.useState(false);
  const [disablePassword, setDisablePassword] = React.useState("");
  const [disableCode, setDisableCode] = React.useState("");
  const [disableRecovery, setDisableRecovery] = React.useState("");
  const [useDisableRecovery, setUseDisableRecovery] = React.useState(false);
  const [regeneratePassword, setRegeneratePassword] = React.useState("");
  const [otpStepUpEnabled, setOtpStepUpEnabled] = React.useState(false);
  const [useEmailStepUp, setUseEmailStepUp] = React.useState(false);
  const [stepUpToken, setStepUpTokenState] = React.useState<string | null>(null);
  const [stepUpOpen, setStepUpOpen] = React.useState(false);

  React.useEffect(() => {
    fetchAuthConfig()
      .then((config) => setOtpStepUpEnabled(Boolean(config.otp_step_up_enabled)))
      .catch(() => setOtpStepUpEnabled(false));
  }, []);

  React.useEffect(() => {
    return () => {
      if (setup?.qrUrl) {
        URL.revokeObjectURL(setup.qrUrl);
      }
    };
  }, [setup?.qrUrl]);

  const totpEnabled = Boolean(profile?.totp_enabled);

  const handleStartSetup = async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await setupTotp();
      const qrUrl = await fetchTotpQrBlobUrl(result.provisioning_uri);
      setSetup({
        secret: result.secret,
        provisioningUri: result.provisioning_uri,
        qrUrl,
      });
      setConfirmCode("");
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : "Setup failed");
    } finally {
      setBusy(false);
    }
  };

  const handleConfirmSetup = async () => {
    setBusy(true);
    setError(null);
    try {
      const codes = await verifyTotp(confirmCode.trim());
      setSetup(null);
      setConfirmCode("");
      setRecoveryCodes(codes);
      setRecoveryOpen(true);
      await mutate();
      await refreshUser();
      setMessage("Two-factor authentication is enabled.");
    } catch (confirmError) {
      setError(confirmError instanceof Error ? confirmError.message : "Verification failed");
    } finally {
      setBusy(false);
    }
  };

  const handleDisable = async () => {
    setBusy(true);
    setError(null);
    try {
      await disableTotp({
        password: disablePassword,
        code: useEmailStepUp ? undefined : useDisableRecovery ? undefined : disableCode.trim(),
        recoveryCode: useEmailStepUp ? undefined : useDisableRecovery ? disableRecovery.trim() : undefined,
        stepUpToken: useEmailStepUp ? stepUpToken ?? undefined : undefined,
      });
      setDisableOpen(false);
      setDisablePassword("");
      setDisableCode("");
      setDisableRecovery("");
      await mutate();
      await refreshUser();
      setMessage("Two-factor authentication disabled.");
    } catch (disableError) {
      setError(disableError instanceof Error ? disableError.message : "Disable failed");
    } finally {
      setBusy(false);
    }
  };

  const handleRegenerate = async () => {
    setBusy(true);
    setError(null);
    try {
      const codes = await generateRecoveryCodes(regeneratePassword);
      setRegenerateOpen(false);
      setRegeneratePassword("");
      setRecoveryCodes(codes);
      setRecoveryOpen(true);
      setMessage("Recovery codes regenerated.");
    } catch (regenerateError) {
      setError(regenerateError instanceof Error ? regenerateError.message : "Regenerate failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Card variant="outlined">
        <CardContent sx={{ display: "grid", gap: 2 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
            <Typography variant="subtitle1">Authenticator app (TOTP)</Typography>
            <Chip
              size="small"
              color={totpEnabled ? "success" : "default"}
              label={totpEnabled ? "2FA enabled" : "2FA disabled"}
            />
          </Box>
          <Typography variant="body2" color="text.secondary">
            Use Google Authenticator, 1Password, or another TOTP app. You will need a 6-digit code when signing in.
          </Typography>
          {otpStepUpEnabled ? (
            <Typography variant="body2" color="text.secondary">
              Email OTP step-up is available when SMTP is configured. Authenticator apps are preferred when you can use
              them.
            </Typography>
          ) : null}

          {!totpEnabled && !setup ? (
            <Button variant="contained" onClick={() => void handleStartSetup()} disabled={busy}>
              Enable two-factor
            </Button>
          ) : null}

          {!totpEnabled && setup ? (
            <Box sx={{ display: "grid", gap: 2 }}>
              <Typography variant="body2">
                Scan this QR code with your authenticator app, or enter the secret manually.
              </Typography>
              <Box
                component="img"
                src={setup.qrUrl}
                alt="Two-factor QR code"
                sx={{ width: 200, height: 200, borderRadius: 1, border: "1px solid", borderColor: "divider" }}
              />
              <TextField label="Manual secret" value={setup.secret} fullWidth InputProps={{ readOnly: true }} />
              <TextField
                label="6-digit verification code"
                value={confirmCode}
                onChange={(event) => setConfirmCode(event.target.value)}
                inputProps={{ inputMode: "numeric", pattern: "[0-9]*", maxLength: 6 }}
                fullWidth
              />
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                <Button variant="contained" onClick={() => void handleConfirmSetup()} disabled={busy || !confirmCode}>
                  Confirm and enable
                </Button>
                <Button
                  variant="text"
                  onClick={() => {
                    if (setup.qrUrl) URL.revokeObjectURL(setup.qrUrl);
                    setSetup(null);
                  }}
                >
                  Cancel
                </Button>
              </Box>
            </Box>
          ) : null}

          {totpEnabled ? (
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
              <Button variant="outlined" onClick={() => setRegenerateOpen(true)}>
                Regenerate recovery codes
              </Button>
              <Button color="warning" variant="outlined" onClick={() => setDisableOpen(true)}>
                Disable two-factor
              </Button>
            </Box>
          ) : null}
        </CardContent>
      </Card>

      <RecoveryCodesDialog
        open={recoveryOpen}
        codes={recoveryCodes}
        onClose={() => {
          setRecoveryOpen(false);
          setRecoveryCodes([]);
        }}
      />

      <Dialog open={disableOpen} onClose={() => setDisableOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Disable two-factor authentication</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          <TextField
            label="Current password"
            type="password"
            value={disablePassword}
            onChange={(event) => setDisablePassword(event.target.value)}
            fullWidth
          />
          <FormControlLabel
            control={
              <Switch checked={useDisableRecovery} onChange={(event) => setUseDisableRecovery(event.target.checked)} />
            }
            label="Use recovery code instead of authenticator code"
          />
          {otpStepUpEnabled ? (
            <FormControlLabel
              control={
                <Switch
                  checked={useEmailStepUp}
                  onChange={(event) => {
                    setUseEmailStepUp(event.target.checked);
                    if (event.target.checked) {
                      setUseDisableRecovery(false);
                      setStepUpOpen(true);
                    } else {
                      setStepUpTokenState(null);
                    }
                  }}
                />
              }
              label="Verify by email code instead"
            />
          ) : null}
          {useEmailStepUp ? (
            <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}>
              <Typography variant="body2" color={stepUpToken ? "success.main" : "text.secondary"}>
                {stepUpToken ? "Email verification complete." : "Email verification required."}
              </Typography>
              {!stepUpToken ? (
                <Button size="small" onClick={() => setStepUpOpen(true)}>
                  Send email code
                </Button>
              ) : null}
            </Box>
          ) : null}
          {!useEmailStepUp && useDisableRecovery ? (
            <TextField
              label="Recovery code"
              value={disableRecovery}
              onChange={(event) => setDisableRecovery(event.target.value)}
              fullWidth
            />
          ) : !useEmailStepUp ? (
            <TextField
              label="Authenticator code"
              value={disableCode}
              onChange={(event) => setDisableCode(event.target.value)}
              inputProps={{ inputMode: "numeric", pattern: "[0-9]*", maxLength: 6 }}
              fullWidth
            />
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDisableOpen(false)}>Cancel</Button>
          <Button color="warning" variant="contained" onClick={() => void handleDisable()} disabled={busy}>
            Disable 2FA
          </Button>
        </DialogActions>
      </Dialog>

      <StepUpOtpDialog
        open={stepUpOpen}
        onClose={() => setStepUpOpen(false)}
        onVerified={(token) => {
          setStepUpTokenState(token);
          setStepUpOpen(false);
        }}
      />

      <Dialog open={regenerateOpen} onClose={() => setRegenerateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Regenerate recovery codes</DialogTitle>
        <DialogContent sx={{ pt: 1 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            This invalidates your previous recovery codes immediately.
          </Typography>
          <TextField
            label="Current password"
            type="password"
            value={regeneratePassword}
            onChange={(event) => setRegeneratePassword(event.target.value)}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRegenerateOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={() => void handleRegenerate()} disabled={busy || !regeneratePassword}>
            Regenerate
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
