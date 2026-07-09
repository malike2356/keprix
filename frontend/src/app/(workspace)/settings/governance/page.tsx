"use client";

import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import GavelIcon from "@mui/icons-material/Gavel";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import ShieldIcon from "@mui/icons-material/Shield";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import Link from "@mui/material/Link";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonDetailPanel } from "@/components/ui/loading";
import { connectGovernance, disconnectGovernance, fetchGovernanceStatus } from "@/lib/governance-api";
import { formatTimeAgo } from "@/lib/time-ago";

const SCOUT_HOME = "https://labyrinthscout.com";
const SCOUT_PRICING = "https://labyrinthscout.com/pricing";
const SCOUT_API_DEFAULT = "https://api.labyrinthscout.com";

const FEATURES = [
  "Kill switches for emergency operator control",
  "Tamper-evident audit trails streamed to Scout",
  "Operator-defined policy enforcement on tools and providers",
];

const NOT_AVAILABLE_YET = [
  'No OAuth or "Sign in with Scout"',
  "No automatic key fetch after purchase",
  "No in-app Scout signup or billing",
  "No per-agent Scout keys",
] as const;

export default function GovernancePage() {
  const { data, mutate, isLoading } = useSWR("governance-status", fetchGovernanceStatus);
  const [connectOpen, setConnectOpen] = React.useState(false);
  const [disconnectOpen, setDisconnectOpen] = React.useState(false);
  const [scoutUrl, setScoutUrl] = React.useState(SCOUT_API_DEFAULT);
  const [apiKey, setApiKey] = React.useState("");
  const [acceptResponsibility, setAcceptResponsibility] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const connected = Boolean(data?.connected);

  const onConnect = async () => {
    setBusy(true);
    setError(null);
    try {
      await connectGovernance({ provider_endpoint: scoutUrl.trim(), api_key: apiKey.trim() });
      setConnectOpen(false);
      setApiKey("");
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not connect Scout");
    } finally {
      setBusy(false);
    }
  };

  const onDisconnect = async () => {
    setBusy(true);
    setError(null);
    try {
      await disconnectGovernance(acceptResponsibility);
      setDisconnectOpen(false);
      setAcceptResponsibility(false);
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not disconnect Scout");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <PageHeader
        title="Governance and Oversight"
        description="Optional Scout governance adds kill switches, tamper-evident audit trails, and operator-defined policy enforcement to keprix."
      />

      {connected ? (
        <Box sx={{ display: "grid", gap: 2 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <CheckCircleIcon color="success" />
            <Typography variant="h6">Connected to Scout</Typography>
            <Chip size="small" label={data?.instance_id || "instance"} />
          </Box>
          <Typography variant="body2" color="text.secondary">
            Last heartbeat:{" "}
            {data?.last_heartbeat_at
              ? `${formatTimeAgo(data.last_heartbeat_at)} (${data.last_heartbeat_ok ? "ok" : "failed"})`
              : "pending"}
          </Typography>
          {data?.reporting_paused ? (
            <Typography variant="body2" color="warning.main">
              Event reporting is paused after repeated delivery failures. Check Scout connectivity in settings.
            </Typography>
          ) : null}
          <Button
            href={data?.provider_endpoint || SCOUT_HOME}
            target="_blank"
            rel="noopener noreferrer"
            startIcon={<OpenInNewIcon />}
            variant="outlined"
          >
            Open Scout dashboard
          </Button>
          <Typography variant="subtitle1">Active policies</Typography>
          {!data?.policies?.length ? (
            <Typography variant="body2" color="text.secondary">
              No active policies pushed from Scout.
            </Typography>
          ) : (
            <List dense>
              {data.policies.map((policy) => (
                <ListItem key={policy.id}>
                  <ListItemText
                    primary={policy.policy_type}
                    secondary={JSON.stringify(policy.policy_value)}
                  />
                </ListItem>
              ))}
            </List>
          )}
          <Button color="error" variant="outlined" onClick={() => setDisconnectOpen(true)}>
            Disconnect Scout
          </Button>
        </Box>
      ) : (
        <Box sx={{ display: "grid", gap: 2, maxWidth: 720 }}>
          <Typography variant="body1">
            Scout is a separate paid product. keprix does not sell or provision Scout. Connection is manual: paste the
            Scout URL and API key after purchase.
          </Typography>

          <Alert severity="info">
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              How to connect Scout
            </Typography>
            <Typography variant="body2" sx={{ mb: 1.5 }}>
              Get your API key from the Scout console after purchase, then paste it below. keprix does not create or email
              Scout keys for you.
            </Typography>
            <List dense disablePadding component="ol" sx={{ pl: 2, m: 0 }}>
              <ListItem component="li" disablePadding sx={{ display: "list-item", mb: 1 }}>
                <Typography variant="body2" component="span">
                  Purchase Scout at{" "}
                  <Link href={SCOUT_PRICING} target="_blank" rel="noopener noreferrer">
                    labyrinthscout.com/pricing
                  </Link>
                  , or bundled Scout plans from your vendor if applicable.
                </Typography>
              </ListItem>
              <ListItem component="li" disablePadding sx={{ display: "list-item", mb: 1 }}>
                <Typography variant="body2" component="span">
                  After provisioning, check your email for the Scout console URL and API key.
                </Typography>
              </ListItem>
              <ListItem component="li" disablePadding sx={{ display: "list-item", mb: 1 }}>
                <Typography variant="body2" component="span">
                  Open the Scout console and copy the API key for this deployment.
                </Typography>
              </ListItem>
              <ListItem component="li" disablePadding sx={{ display: "list-item" }}>
                <Typography variant="body2" component="span">
                  Click <strong>Connect Scout</strong> below and paste the Scout URL and API key.
                </Typography>
              </ListItem>
            </List>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
              One API key governs this entire keprix deployment. Individual agents do not get separate Scout keys.
            </Typography>
          </Alert>

          <Alert severity="warning" variant="outlined">
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Not available in keprix yet
            </Typography>
            <List dense disablePadding>
              {NOT_AVAILABLE_YET.map((item) => (
                <ListItem key={item} disablePadding sx={{ py: 0 }}>
                  <ListItemText primary={item} primaryTypographyProps={{ variant: "body2" }} />
                </ListItem>
              ))}
            </List>
          </Alert>

          <List>
            {FEATURES.map((feature) => (
              <ListItem key={feature}>
                <ListItemIcon>
                  <ShieldIcon fontSize="small" />
                </ListItemIcon>
                <ListItemText primary={feature} />
              </ListItem>
            ))}
          </List>
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            <Button variant="contained" startIcon={<GavelIcon />} onClick={() => setConnectOpen(true)}>
              Connect Scout
            </Button>
            <Button href={SCOUT_HOME} target="_blank" rel="noopener noreferrer">
              Learn more at labyrinthscout.com
            </Button>
            <Button href={SCOUT_PRICING} target="_blank" rel="noopener noreferrer">
              View pricing
            </Button>
          </Box>
          <Typography variant="caption" color="text.secondary">
            Scout is a paid service. keprix works without it.
          </Typography>
        </Box>
      )}

      {error ? (
        <Typography variant="body2" color="error" sx={{ mt: 2 }}>
          {error}
        </Typography>
      ) : null}
      {isLoading ? (
        <Box sx={{ mt: 2 }}>
          <SkeletonDetailPanel fields={5} />
        </Box>
      ) : null}

      <Dialog open={connectOpen} onClose={() => setConnectOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Connect Scout</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          <DialogContentText>
            Paste the Scout URL and API key from your provisioning email or Scout console. keprix stores the key in the
            vault; it is never saved in plain text config.
          </DialogContentText>
          <TextField
            label="Scout URL"
            value={scoutUrl}
            onChange={(event) => setScoutUrl(event.target.value)}
            helperText={`Default API endpoint is ${SCOUT_API_DEFAULT} unless your provisioning email says otherwise.`}
            fullWidth
          />
          <TextField
            label="Scout API key"
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            helperText="Paste the key from the Scout console or provisioning email. One key governs this entire keprix deployment."
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConnectOpen(false)}>Cancel</Button>
          <Button variant="contained" disabled={busy || !scoutUrl.trim() || !apiKey.trim()} onClick={() => void onConnect()}>
            Connect
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={disconnectOpen} onClose={() => setDisconnectOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Disconnect Scout</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Kill directives from Scout cannot be revoked from keprix. Disconnecting removes Scout governance controls.
          </DialogContentText>
          <FormControlLabel
            control={
              <Checkbox
                checked={acceptResponsibility}
                onChange={(event) => setAcceptResponsibility(event.target.checked)}
              />
            }
            label="I accept responsibility for ungoverned operation"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDisconnectOpen(false)}>Cancel</Button>
          <Button
            color="error"
            variant="contained"
            disabled={busy || !acceptResponsibility}
            onClick={() => void onDisconnect()}
          >
            Disconnect
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
