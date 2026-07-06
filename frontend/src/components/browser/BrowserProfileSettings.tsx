"use client";

import AddIcon from "@mui/icons-material/Add";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import { createBrowserProfile, fetchBrowserProfiles } from "@/lib/browser-api";

const PROFILE_KINDS = [
  { value: "fresh", label: "Fresh isolated" },
  { value: "persistent", label: "Persistent local" },
  { value: "authenticated", label: "Authenticated (vault)" },
  { value: "read_only", label: "Read-only" },
  { value: "disposable", label: "Disposable test" },
];

export default function BrowserProfileSettings() {
  const { data, mutate } = useSWR("browser-profiles", () => fetchBrowserProfiles());
  const [name, setName] = React.useState("");
  const [kind, setKind] = React.useState("persistent");
  const [vaultId, setVaultId] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const onCreate = async () => {
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createBrowserProfile({
        name: name.trim(),
        kind,
        vault_credential_id: vaultId.trim() || undefined,
      });
      setName("");
      setVaultId("");
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create profile");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Browser profiles
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Cookies and sessions are encrypted at rest. Vault credentials are referenced by ID only.
        </Typography>
        <Box sx={{ display: "grid", gap: 2, mb: 2 }}>
          <TextField label="Profile name" value={name} onChange={(e) => setName(e.target.value)} size="small" />
          <FormControl size="small">
            <InputLabel id="browser-profile-kind">Kind</InputLabel>
            <Select labelId="browser-profile-kind" label="Kind" value={kind} onChange={(e) => setKind(e.target.value)}>
              {PROFILE_KINDS.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {kind === "authenticated" ? (
            <TextField
              label="Vault credential ID"
              value={vaultId}
              onChange={(e) => setVaultId(e.target.value)}
              size="small"
              helperText="Credentials stay in the vault; only the ID is stored on the profile."
            />
          ) : null}
          <Button startIcon={<AddIcon />} variant="contained" onClick={onCreate} disabled={busy}>
            Create profile
          </Button>
        </Box>
        {error ? (
          <Typography color="error" variant="body2" sx={{ mb: 2 }}>
            {error}
          </Typography>
        ) : null}
        {(data?.profiles ?? []).map((profile) => (
          <Box key={profile.id} sx={{ py: 1, borderTop: 1, borderColor: "divider" }}>
            <Typography variant="subtitle2">{profile.name}</Typography>
            <Typography variant="caption" color="text.secondary">
              {profile.kind}
              {profile.read_only ? " · read-only" : ""}
            </Typography>
          </Box>
        ))}
      </CardContent>
    </Card>
  );
}
