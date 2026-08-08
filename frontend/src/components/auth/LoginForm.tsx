"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import TextField from "@mui/material/TextField";
import NextLink from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";
import { fetchAuthConfig, fetchSsoProviders, sendEmailOtp, ssoStartUrl, verifyEmailOtpLogin } from "@/lib/account-api";
import { LoginChallengeError } from "@/lib/ce-api";
import { useCESession } from "@/lib/ce-auth";

export default function LoginForm({ returnTo = "/home" }: { returnTo?: string }) {
  const router = useRouter();
  const { signIn, refreshUser } = useCESession();
  const [step, setStep] = React.useState<"credentials" | "totp" | "email_otp">("credentials");
  const [otpLoginEnabled, setOtpLoginEnabled] = React.useState(false);
  const [ssoProviders, setSsoProviders] = React.useState<Array<{ name: string; display_name: string }>>([]);
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [totpCode, setTotpCode] = React.useState("");
  const [recoveryCode, setRecoveryCode] = React.useState("");
  const [emailOtpCode, setEmailOtpCode] = React.useState("");
  const [otpChallengeId, setOtpChallengeId] = React.useState<string | null>(null);
  const [useRecoveryCode, setUseRecoveryCode] = React.useState(false);
  const [remember, setRemember] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    fetchAuthConfig()
      .then((config) => setOtpLoginEnabled(Boolean(config.otp_login_enabled)))
      .catch(() => setOtpLoginEnabled(false));
    fetchSsoProviders()
      .then((providers) => setSsoProviders(providers))
      .catch(() => setSsoProviders([]));
  }, []);

  const completeLogin = React.useCallback(
    async (options?: { totpCode?: string; recoveryCode?: string }) => {
      await signIn(email, password, options);
      router.push(returnTo.startsWith("/") ? returnTo : "/home");
    },
    [email, password, returnTo, router, signIn],
  );

  const handleEmailOtpSend = async () => {
    setError(null);
    setMessage(null);
    setSubmitting(true);
    try {
      const login = email.trim();
      if (!login) {
        setError("Enter your email or username first.");
        return;
      }
      const result = await sendEmailOtp(login, "login");
      setOtpChallengeId(result.challengeId);
      setStep("email_otp");
      setMessage(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send code");
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setSubmitting(true);
    try {
      if (step === "email_otp") {
        if (!otpChallengeId) {
          setError("Request a verification code first.");
          return;
        }
        await verifyEmailOtpLogin(otpChallengeId, emailOtpCode.trim());
        await refreshUser();
        router.push(returnTo.startsWith("/") ? returnTo : "/home");
        return;
      }
      if (step === "totp") {
        await completeLogin({
          totpCode: useRecoveryCode ? undefined : totpCode.trim(),
          recoveryCode: useRecoveryCode ? recoveryCode.trim() : undefined,
        });
        return;
      }
      await completeLogin();
    } catch (err) {
      if (err instanceof LoginChallengeError && err.code === "totp_required") {
        setStep("totp");
        setError(null);
      } else {
        setError(err instanceof Error ? err.message : "Login failed");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ display: "flex", flexDirection: "column", gap: 2.5, pt: 0.5 }}>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {message ? <Alert severity="success">{message}</Alert> : null}
      {step === "credentials" && ssoProviders.length > 0 ? (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          {ssoProviders.map((provider) => (
            <Button
              key={provider.name}
              variant="outlined"
              size="large"
              component="a"
              href={ssoStartUrl(provider.name, returnTo.startsWith("/") ? returnTo : "/home", "login")}
            >
              Continue with {provider.display_name}
            </Button>
          ))}
        </Box>
      ) : null}
      {step === "credentials" ? (
        <>
          <TextField
            label="Email or username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="username"
            fullWidth
            InputLabelProps={{ shrink: true }}
          />
          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            fullWidth
            InputLabelProps={{ shrink: true }}
          />
          <FormControlLabel
            control={<Checkbox checked={remember} onChange={(e) => setRemember(e.target.checked)} />}
            label="Remember me"
          />
        </>
      ) : null}
      {step === "totp" ? (
        <>
          <Alert severity="info">Enter the 6-digit code from your authenticator app to finish signing in.</Alert>
          {!useRecoveryCode ? (
            <TextField
              label="Authenticator code"
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value)}
              required
              inputProps={{ inputMode: "numeric", pattern: "[0-9]*", maxLength: 6 }}
              fullWidth
            />
          ) : (
            <TextField
              label="Recovery code"
              value={recoveryCode}
              onChange={(e) => setRecoveryCode(e.target.value)}
              required
              fullWidth
            />
          )}
          <FormControlLabel
            control={
              <Checkbox
                checked={useRecoveryCode}
                onChange={(e) => {
                  setUseRecoveryCode(e.target.checked);
                  setTotpCode("");
                  setRecoveryCode("");
                }}
              />
            }
            label="Use a recovery code"
          />
          <Button variant="text" onClick={() => setStep("credentials")}>
            Back to username and password
          </Button>
        </>
      ) : null}
      {step === "email_otp" ? (
        <>
          <Alert severity="info">Enter the 6-digit code sent to your email.</Alert>
          <TextField
            label="Email verification code"
            value={emailOtpCode}
            onChange={(e) => setEmailOtpCode(e.target.value)}
            required
            inputProps={{ inputMode: "numeric", pattern: "[0-9]*", maxLength: 6 }}
            fullWidth
          />
          <Button variant="text" onClick={() => setStep("credentials")}>
            Back to username and password
          </Button>
        </>
      ) : null}
      <Button type="submit" variant="contained" size="large" disabled={submitting}>
        {submitting
          ? "Signing in..."
          : step === "email_otp"
            ? "Verify and sign in"
            : step === "totp"
              ? "Verify and sign in"
              : "Sign in"}
      </Button>
      {step === "credentials" && otpLoginEnabled ? (
        <Button variant="outlined" onClick={() => void handleEmailOtpSend()} disabled={submitting || !email.trim()}>
          Email me a sign-in code
        </Button>
      ) : null}
      {step === "credentials" ? (
        <>
          <Button component={NextLink} href="/auth/forgot-password" variant="text">
            Forgot password?
          </Button>
          <Button component={NextLink} href="/auth/setup" variant="text">
            First time? Set up your instance
          </Button>
        </>
      ) : null}
    </Box>
  );
}
