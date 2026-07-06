"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Drawer from "@mui/material/Drawer";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import BlankCard from "@/components/cards/BlankCard";
import PageContainer from "@/components/shared/PageContainer";
import {
  createApiKey,
  fetchApiKeys,
  fetchDeveloperIdentity,
  revokeApiKey,
} from "@/lib/admin-workspace-api";
import { formatTimeAgo } from "@/lib/time-ago";

export default function AdminKeysPage() {
  const { data: identity } = useSWR("developer-identity", fetchDeveloperIdentity);
  const { data: keysData, mutate } = useSWR("api-keys", fetchApiKeys);
  const [pemOpen, setPemOpen] = React.useState(false);
  const [createOpen, setCreateOpen] = React.useState(false);
  const [name, setName] = React.useState("");
  const [expiry, setExpiry] = React.useState("none");
  const [scopes, setScopes] = React.useState<string[]>(["read"]);
  const [createdSecret, setCreatedSecret] = React.useState<string | null>(null);

  const toggleScope = (scope: string) => {
    setScopes((prev) => (prev.includes(scope) ? prev.filter((item) => item !== scope) : [...prev, scope]));
  };

  return (
    <PageContainer title="API Keys" description="Developer identity and programmatic access." padded={false}>
      <BlankCard>
        <Box sx={{ p: 3, display: "grid", gap: 1 }}>
          <Typography variant="h6">Developer Identity</Typography>
          <Typography variant="body2">Installation fingerprint: {identity?.fingerprint || "..."}</Typography>
          <Typography variant="body2">Identity created: {identity?.created_at || "..."}</Typography>
          <Typography variant="body2">
            Public key:{" "}
            <Button size="small" onClick={() => setPemOpen(true)}>
              View
            </Button>
          </Typography>
          <Typography variant="body2">Config location: {identity?.config_path}</Typography>
        </Box>
      </BlankCard>

      <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 2 }}>
        <Button variant="contained" onClick={() => setCreateOpen(true)}>
          Create new key
        </Button>
      </Box>

      <BlankCard>
        <Box sx={{ p: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Key prefix</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Last used</TableCell>
                <TableCell>Expires</TableCell>
                <TableCell>Scopes</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(keysData?.keys || []).map((key) => (
                <TableRow key={key.id}>
                  <TableCell>{key.name}</TableCell>
                  <TableCell>{key.key_prefix}...</TableCell>
                  <TableCell>{key.created_at}</TableCell>
                  <TableCell>{formatTimeAgo(key.last_used_at) || "Never"}</TableCell>
                  <TableCell>{key.expires_at || "No expiry"}</TableCell>
                  <TableCell>
                    {key.scopes.map((scope) => (
                      <Chip key={scope} size="small" label={scope} sx={{ mr: 0.5 }} />
                    ))}
                  </TableCell>
                  <TableCell align="right">
                    <Button color="error" size="small" onClick={() => void revokeApiKey(key.id).then(() => mutate())}>
                      Revoke
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      </BlankCard>

      <Drawer anchor="right" open={pemOpen} onClose={() => setPemOpen(false)} PaperProps={{ sx: { width: 480 } }}>
        <Box sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Public key (PEM)
          </Typography>
          <Typography component="pre" sx={{ whiteSpace: "pre-wrap", fontFamily: "monospace", fontSize: 12 }}>
            {identity?.public_key_pem || "No public key available."}
          </Typography>
        </Box>
      </Drawer>

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create API key</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          {createdSecret ? (
            <Box sx={{ p: 2, border: 1, borderColor: "warning.main", borderRadius: 1 }}>
              <Typography variant="body2" color="warning.main">
                This key will not be shown again. Copy it now.
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: "monospace", mt: 1 }}>
                {createdSecret}
              </Typography>
            </Box>
          ) : (
            <>
              <TextField label="Key name" value={name} onChange={(event) => setName(event.target.value)} />
              <TextField select label="Expiry" value={expiry} onChange={(event) => setExpiry(event.target.value)}>
                <MenuItem value="none">No expiry</MenuItem>
                <MenuItem value="30d">30 days</MenuItem>
                <MenuItem value="90d">90 days</MenuItem>
                <MenuItem value="1y">1 year</MenuItem>
              </TextField>
              <Box>
                {["read", "write", "admin"].map((scope) => (
                  <FormControlLabel
                    key={scope}
                    control={<Checkbox checked={scopes.includes(scope)} onChange={() => toggleScope(scope)} />}
                    label={scope}
                  />
                ))}
              </Box>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>Close</Button>
          {!createdSecret ? (
            <Button
              variant="contained"
              disabled={!name.trim() || scopes.length === 0}
              onClick={() => {
                void createApiKey({ name: name.trim(), expiry, scopes }).then((created) => {
                  setCreatedSecret(created.secret);
                  void mutate();
                });
              }}
            >
              Create
            </Button>
          ) : null}
        </DialogActions>
      </Dialog>
    </PageContainer>
  );
}
