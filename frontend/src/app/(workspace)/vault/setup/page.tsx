"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import { ceApi, parseApiErrorMessage } from "@/lib/ce-api";

type VaultPack = {
  id: string;
  name: string;
  version: string;
  description: string;
};

type ValidationResult = {
  ok: boolean;
  errors: string[];
  manifest?: Record<string, unknown>;
};

export default function VaultSetupPage() {
  const [packs, setPacks] = React.useState<VaultPack[]>([]);
  const [pack, setPack] = React.useState("obsidian-starter");
  const [path, setPath] = React.useState("");
  const [result, setResult] = React.useState<Record<string, unknown> | null>(null);
  const [validation, setValidation] = React.useState<ValidationResult | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    ceApi("/api/vault/packs")
      .then((response) => response.json())
      .then((payload: { packs?: VaultPack[] }) => setPacks(payload.packs || []))
      .catch(() => setPacks([]));
  }, []);

  const parse = async <T,>(response: Response, fallback: string): Promise<T> => {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(parseApiErrorMessage(payload, fallback));
    }
    return payload as T;
  };

  const init = async () => {
    if (!path.trim()) {
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const payload = await parse<Record<string, unknown>>(
        await ceApi("/api/vault/init", {
          method: "POST",
          body: JSON.stringify({ pack, path: path.trim() }),
        }),
        "Vault initialization failed",
      );
      setResult(payload);
      await validate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Vault initialization failed");
    } finally {
      setBusy(false);
    }
  };

  const validate = async () => {
    if (!path.trim()) {
      return;
    }
    const payload = await parse<ValidationResult>(
      await ceApi("/api/vault/validate", {
        method: "POST",
        body: JSON.stringify({ path: path.trim() }),
      }),
      "Vault validation failed",
    );
    setValidation(payload);
  };

  return (
    <Box>
      <Typography variant="h5" component="h1" sx={{ mb: 2 }}>
        Vault setup
      </Typography>
      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Stack spacing={2}>
            <TextField select label="Pack" value={pack} onChange={(event) => setPack(event.target.value)} fullWidth>
              {(packs.length ? packs : [{ id: "obsidian-starter", name: "Obsidian vault starter", version: "1.0.0", description: "" }]).map((item) => (
                <MenuItem key={item.id} value={item.id}>
                  {item.name} {item.version ? `v${item.version}` : ""}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Vault path"
              value={path}
              onChange={(event) => setPath(event.target.value)}
              placeholder="/home/user/Documents/Vault"
              fullWidth
            />
            <Stack direction="row" spacing={1}>
              <Button variant="contained" disabled={!path.trim() || busy} onClick={() => void init()}>
                {busy ? "Initializing..." : "Initialize vault"}
              </Button>
              <Button variant="outlined" disabled={!path.trim()} onClick={() => void validate()}>
                Validate
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      {result ? <Alert severity="success" sx={{ mb: 2 }}>Vault initialized at {String(result.path || path)}.</Alert> : null}
      {validation ? (
        <Card variant="outlined">
          <CardContent>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
              <Typography variant="subtitle1">Validation</Typography>
              <Chip size="small" color={validation.ok ? "success" : "error"} label={validation.ok ? "pass" : "fail"} />
            </Stack>
            {validation.errors.length ? (
              <Box component="ul" sx={{ m: 0, pl: 2 }}>
                {validation.errors.map((item) => (
                  <li key={item}>
                    <Typography variant="body2">{item}</Typography>
                  </li>
                ))}
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">
                KEPRIX.md, folder map, templates, and manifest are present.
              </Typography>
            )}
          </CardContent>
        </Card>
      ) : null}
    </Box>
  );
}
