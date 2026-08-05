"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import {
  fetchOperatorPolicy,
  setOperatorPolicy,
  type OperatorPolicyKnobs,
} from "@/lib/operator-policy-api";

const PROFILES = ["strict", "standard", "permissive"] as const;

const KNOB_LABELS: Array<{ key: keyof OperatorPolicyKnobs; label: string }> = [
  { key: "dual_use_depth", label: "Dual-use depth" },
  { key: "package_install", label: "Package install" },
  { key: "browser_unknown_hosts", label: "Unknown hosts" },
  { key: "skill_first_mode", label: "Skill-first" },
  { key: "third_party_mcp", label: "Third-party MCP" },
  { key: "child_safety_block", label: "Child safety" },
  { key: "malware_block", label: "Malware" },
  { key: "weapons_block", label: "Weapons" },
  { key: "sandboxes_enforced", label: "Sandboxes" },
  { key: "egress_enforced", label: "Egress" },
  { key: "scout_kill_switch", label: "Scout kill switch" },
];

function formatKnob(value: unknown): string {
  if (typeof value === "boolean") return value ? "always on" : "off";
  return String(value);
}

export default function OperatorPolicyPanel({ productId }: { productId?: string }) {
  const key = productId ? `operator-policy:${productId}` : "operator-policy";
  const { data, mutate, isLoading } = useSWR(key, () =>
    fetchOperatorPolicy(productId ? { product_id: productId } : undefined),
  );
  const [profile, setProfile] = React.useState<string>("standard");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (data?.policy?.profile) setProfile(data.policy.profile);
  }, [data?.policy?.profile]);

  const onSave = async () => {
    setBusy(true);
    setError(null);
    try {
      await setOperatorPolicy({
        profile,
        product_id: productId,
        workspace_id: "default",
      });
      await mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update policy");
    } finally {
      setBusy(false);
    }
  };

  const matrix = data?.knob_matrix || {};
  const current = data?.policy;

  return (
    <Box sx={{ display: "grid", gap: 2, mt: 3 }}>
      <Typography variant="h6">Operator policy profile</Typography>
      <Typography variant="body2" color="text.secondary">
        Controls refusal depth and autonomy knobs. Hard floors, sandboxes, egress, and Scout kill
        switch stay enforced under every profile.
      </Typography>

      {data?.empty_state ? (
        <Alert severity="info">{data.empty_state}</Alert>
      ) : null}

      {current ? (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
          <Chip label={`Profile: ${current.profile}`} color="primary" size="small" />
          <Chip label={`Source: ${current.source}`} size="small" variant="outlined" />
        </Box>
      ) : null}

      <Alert severity="warning">
        Permissive does not disable sandboxes, egress, hard floors, or Scout kill switch.
      </Alert>

      <Box sx={{ display: "flex", gap: 2, alignItems: "center", flexWrap: "wrap" }}>
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel id="operator-policy-profile">Profile</InputLabel>
          <Select
            labelId="operator-policy-profile"
            label="Profile"
            value={profile}
            onChange={(e) => setProfile(String(e.target.value))}
            disabled={isLoading || busy}
          >
            {PROFILES.map((p) => (
              <MenuItem key={p} value={p}>
                {p}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button variant="contained" onClick={onSave} disabled={busy || isLoading}>
          {busy ? "Saving..." : "Save profile"}
        </Button>
      </Box>

      {error ? (
        <Typography variant="body2" color="error">
          {error}
        </Typography>
      ) : null}

      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Knob</TableCell>
            {PROFILES.map((p) => (
              <TableCell key={p}>{p}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {KNOB_LABELS.map(({ key: knobKey, label }) => (
            <TableRow key={knobKey}>
              <TableCell>{label}</TableCell>
              {PROFILES.map((p) => (
                <TableCell key={p}>{formatKnob(matrix[p]?.[knobKey])}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}
