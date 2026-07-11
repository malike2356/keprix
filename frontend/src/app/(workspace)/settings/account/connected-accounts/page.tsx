"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import StepUpOtpDialog from "@/components/auth/StepUpOtpDialog";
import {
  fetchSsoLinks,
  fetchSsoProviders,
  startSsoLink,
  unlinkSsoProvider,
  type SsoLink,
  type SsoProvider,
} from "@/lib/account-api";

type ProviderDef = { name: string; displayName: string; description: string; envHint: string };

const PROVIDER_DEFS: ProviderDef[] = [
  {
    name: "google",
    displayName: "Google",
    description: "Sign in with your Google account.",
    envHint: "KEPRIX_GOOGLE_CLIENT_ID and KEPRIX_GOOGLE_CLIENT_SECRET",
  },
  {
    name: "github",
    displayName: "GitHub",
    description: "Sign in with your GitHub account.",
    envHint: "KEPRIX_GITHUB_CLIENT_ID and KEPRIX_GITHUB_CLIENT_SECRET",
  },
  {
    name: "oidc",
    displayName: "OpenID Connect",
    description: "Sign in via your organisation identity provider.",
    envHint: "KEPRIX_OIDC_CLIENT_ID, KEPRIX_OIDC_CLIENT_SECRET, and KEPRIX_OIDC_ISSUER",
  },
];

function ProviderIcon({ name }: { name: string }) {
  const label = name === "oidc" ? "ID" : name.charAt(0).toUpperCase();
  const bg = name === "google" ? "#4285F4" : name === "github" ? "#24292E" : "#6B5CF6";
  return (
    <Box
      sx={{
        width: 40,
        height: 40,
        borderRadius: 1,
        bgcolor: bg,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
      }}
    >
      <Typography sx={{ color: "#fff", fontWeight: 700, fontSize: 14, lineHeight: 1 }}>
        {label}
      </Typography>
    </Box>
  );
}

export default function ConnectedAccountsPage() {
  const [configuredProviders, setConfiguredProviders] = React.useState<SsoProvider[]>([]);
  const [links, setLinks] = React.useState<SsoLink[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [unlinkTarget, setUnlinkTarget] = React.useState<string | null>(null);
  const [password, setPassword] = React.useState("");
  const [stepUpOpen, setStepUpOpen] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);

  const reload = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [providerRows, linkRows] = await Promise.all([fetchSsoProviders(), fetchSsoLinks()]);
      setConfiguredProviders(providerRows);
      setLinks(linkRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load connected accounts");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void reload();
  }, [reload]);

  const linkedMap = React.useMemo(
    () => new Map(links.map((row) => [row.provider, row])),
    [links],
  );
  const configuredSet = React.useMemo(
    () => new Set(configuredProviders.map((p) => p.name)),
    [configuredProviders],
  );
  const onlySignInMethod = links.length === 1;

  const handleLink = async (providerName: string) => {
    setError(null);
    setMessage(null);
    setSubmitting(true);
    try {
      const startUrl = await startSsoLink(providerName, "/settings/account/connected-accounts");
      window.location.href = startUrl;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start linking");
      setSubmitting(false);
    }
  };

  const handleUnlink = async (options?: { stepUpToken?: string }) => {
    if (!unlinkTarget) return;
    setError(null);
    setMessage(null);
    setSubmitting(true);
    try {
      await unlinkSsoProvider(unlinkTarget, {
        password: password.trim() || undefined,
        stepUpToken: options?.stepUpToken,
      });
      setUnlinkTarget(null);
      setPassword("");
      setMessage("Provider unlinked successfully.");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to unlink provider");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <Typography color="text.secondary">Loading connected accounts...</Typography>;
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2, maxWidth: 640 }}>
      <Box>
        <Typography variant="h6">Connected accounts</Typography>
        <Typography color="text.secondary" sx={{ mt: 0.5 }}>
          Link Google, GitHub, or OpenID Connect sign-in to this workspace account.
        </Typography>
      </Box>

      {error ? <Alert severity="error">{error}</Alert> : null}
      {message ? <Alert severity="success">{message}</Alert> : null}
      {onlySignInMethod ? (
        <Alert severity="warning">
          This is your only linked sign-in method. Set a password on the Password tab before
          unlinking, or keep at least two methods available.
        </Alert>
      ) : null}

      <Stack spacing={1.5}>
        {PROVIDER_DEFS.map((def) => {
          const link = linkedMap.get(def.name);
          const isLinked = Boolean(link);
          const isConfigured = configuredSet.has(def.name);
          const isUnlinking = unlinkTarget === def.name;

          return (
            <Box
              key={def.name}
              sx={{
                display: "flex",
                alignItems: "flex-start",
                gap: 2,
                p: 2,
                border: "1px solid",
                borderColor: isLinked ? "success.main" : "divider",
                borderRadius: 1,
                opacity: isConfigured || isLinked ? 1 : 0.6,
              }}
            >
              <ProviderIcon name={def.name} />

              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                  <Typography fontWeight={600}>{def.displayName}</Typography>
                  {isLinked ? (
                    <Chip label="Linked" size="small" color="success" variant="outlined" />
                  ) : isConfigured ? (
                    <Chip label="Available" size="small" color="default" variant="outlined" />
                  ) : (
                    <Chip label="Not configured" size="small" variant="outlined" />
                  )}
                </Box>

                {link?.email ? (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
                    {link.email}
                  </Typography>
                ) : (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
                    {def.description}
                  </Typography>
                )}

                {!isConfigured && !isLinked ? (
                  <Typography variant="caption" color="text.disabled" sx={{ mt: 0.5, display: "block" }}>
                    Admin: set {def.envHint} in the API .env to enable this provider.
                  </Typography>
                ) : null}

                <Collapse in={isUnlinking}>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1.5, flexWrap: "wrap" }}>
                    <TextField
                      label="Confirm with password"
                      type="password"
                      size="small"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                    <Button
                      variant="contained"
                      color="error"
                      size="small"
                      disabled={submitting}
                      onClick={() => void handleUnlink()}
                    >
                      Confirm unlink
                    </Button>
                    <Button size="small" onClick={() => { setUnlinkTarget(null); setPassword(""); }}>
                      Cancel
                    </Button>
                    <Button size="small" variant="outlined" onClick={() => setStepUpOpen(true)}>
                      Use email code
                    </Button>
                  </Stack>
                </Collapse>
              </Box>

              <Box sx={{ flexShrink: 0 }}>
                {isLinked && !isUnlinking ? (
                  <Button
                    variant="outlined"
                    color="error"
                    size="small"
                    onClick={() => setUnlinkTarget(def.name)}
                  >
                    Unlink
                  </Button>
                ) : isConfigured && !isLinked ? (
                  <Button
                    variant="contained"
                    size="small"
                    disabled={submitting}
                    onClick={() => void handleLink(def.name)}
                  >
                    Connect
                  </Button>
                ) : null}
              </Box>
            </Box>
          );
        })}
      </Stack>

      <StepUpOtpDialog
        open={stepUpOpen}
        onClose={() => setStepUpOpen(false)}
        onVerified={(token) => {
          setStepUpOpen(false);
          void handleUnlink({ stepUpToken: token });
        }}
      />
    </Box>
  );
}
